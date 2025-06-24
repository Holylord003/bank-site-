from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.views import LoginView
from django.views.generic import TemplateView, CreateView, ListView, DetailView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.contrib.auth.models import User
from django.urls import reverse_lazy
from django.db import transaction, models
from django.utils import timezone
from datetime import timedelta
from .models import BankAccount, Transaction, CreditCard, ScheduledPayment
import random
import string
import datetime
import re
from decimal import Decimal

def generate_account_number():
    return ''.join(random.choices(string.digits, k=10))

class CustomLoginView(LoginView):
    template_name = 'banking/login.html'
    redirect_authenticated_user = True

    def form_invalid(self, form):
        messages.error(self.request, 'Invalid username or password.')
        return super().form_invalid(form)

class RegisterView(CreateView):
    model = User
    template_name = 'banking/register.html'
    fields = ['username', 'email', 'password', 'first_name', 'last_name']
    success_url = reverse_lazy('banking:login')

    def form_valid(self, form):
        user = form.save(commit=False)
        user.set_password(form.cleaned_data['password'])
        user.save()
        
        # Create checking account for the new user
        BankAccount.objects.create(
            user=user,
            account_type='CHECKING',
            account_number=generate_account_number(),
            balance=0.00,
            is_primary=True
        )
        
        messages.success(self.request, 'Account created successfully! Please login.')
        return super().form_valid(form)

class DashboardView(LoginRequiredMixin, TemplateView):
    template_name = 'banking/dashboard.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        
        # Get all accounts for the user
        checking_account = BankAccount.objects.filter(user=user, account_type='CHECKING').first()
        savings_account = BankAccount.objects.filter(user=user, account_type='SAVINGS').first()
        credit_cards = CreditCard.objects.filter(user=user)
        
        # Get primary account for transactions display
        primary_account = BankAccount.objects.filter(user=user, is_primary=True).first() or checking_account
        
        if primary_account:
            accounts = BankAccount.objects.filter(user=user)
            recent_transactions = Transaction.objects.filter(
                account__in=accounts
            ).order_by('-timestamp')[:5]
        else:
            recent_transactions = []
        
        # Calculate total balances
        total_deposit_balance = sum(account.balance for account in [checking_account, savings_account] if account)
        total_credit_used = sum(card.current_balance for card in credit_cards)
        total_credit_available = sum(card.available_credit for card in credit_cards)
        
        context.update({
            'checking_account': checking_account,
            'savings_account': savings_account,
            'credit_cards': credit_cards,
            'primary_account': primary_account,
            'recent_transactions': recent_transactions,
            'total_deposit_balance': total_deposit_balance,
            'total_credit_used': total_credit_used,
            'total_credit_available': total_credit_available
        })
        
        return context

@login_required
def transaction_history(request):
    user = request.user
    account_id = request.GET.get('account_id')
    
    if account_id:
        account = get_object_or_404(BankAccount, id=account_id, user=user)
        transactions = account.transactions.all()
        account_name = f"{account.get_account_type_display()} ({account.account_number})"
    else:
        # Get all transactions for all accounts
        accounts = BankAccount.objects.filter(user=user)
        transactions = Transaction.objects.filter(account__in=accounts)
        account_name = "All Accounts"
    
    transactions = transactions.order_by('-timestamp')
    
    # Add filtering options
    transaction_type = request.GET.get('type')
    if transaction_type:
        transactions = transactions.filter(transaction_type=transaction_type)
        
    # Add date range filtering
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    if start_date:
        transactions = transactions.filter(timestamp__gte=start_date)
    if end_date:
        transactions = transactions.filter(timestamp__lte=end_date)
    
    # Get all accounts for the filter dropdown
    all_accounts = BankAccount.objects.filter(user=user)
    
    return render(request, 'banking/transaction_history.html', {
        'transactions': transactions,
        'account_name': account_name,
        'transaction_types': Transaction.TRANSACTION_TYPES,
        'accounts': all_accounts,
        'selected_account_id': account_id
    })

@login_required
@transaction.atomic
def send_money(request):
    if request.method == 'POST':
        try:
            account_id = request.POST.get('from_account')
            recipient_account_number = request.POST.get('account_number')
            amount = float(request.POST.get('amount', 0))
            description = request.POST.get('description', '')
            
            if amount <= 0:
                messages.error(request, 'Please enter a valid amount.')
                return redirect('banking:send_money')
            
            # Get sender account
            sender_account = get_object_or_404(BankAccount, id=account_id, user=request.user)
            
            # Check if sender has sufficient funds
            if sender_account.balance < amount:
                messages.error(request, 'Insufficient funds.')
                return redirect('banking:send_money')
            
            # Find recipient account
            # Try to get an internal account first
            recipient_account_internal = BankAccount.objects.filter(account_number=recipient_account_number).first()

            if recipient_account_internal:
                # This is an internal transfer
                # Create withdrawal transaction for sender
                Transaction.objects.create(
                    account=sender_account,
                    transaction_type='WITHDRAWAL',
                    amount=amount,
                    status='PENDING',
                    description=f'Pending internal transfer from {sender_account.account_number} to {recipient_account_internal.account_number}: {description}'
                )
                
                # Create deposit transaction for recipient (also pending)
                Transaction.objects.create(
                    account=recipient_account_internal,
                    transaction_type='DEPOSIT',
                    amount=amount,
                    status='PENDING',
                    description=f'Pending internal transfer to {recipient_account_internal.account_number} from {sender_account.account_number}: {description}'
                )
                messages.success(request, 'Your internal transfer request has been submitted and is pending approval.')

            else:
                # This is an external transfer (recipient account not found in our bank)
                # Create withdrawal transaction for sender (still pending, needs admin approval for external payout)
                Transaction.objects.create(
                    account=sender_account,
                    transaction_type='WITHDRAWAL',
                    amount=amount,
                    status='PENDING',
                    description=f'Pending external transfer from {sender_account.account_number} to {recipient_account_number}: {description}'
                )
                messages.warning(request, f'Your transfer request to external account {recipient_account_number} has been submitted and is pending approval for external processing.')

            # Do not update balances here; it will happen upon admin approval for internal transfers
            # For external transfers, only the sender's balance will be updated upon admin approval.
            return redirect('banking:dashboard')
            
        except (ValueError, BankAccount.DoesNotExist):
            messages.error(request, 'Invalid transaction details (e.g., sender account not found or invalid amount). Transfer failed.')
            return redirect('banking:send_money')
    
    # Get user's accounts for the dropdown
    accounts = BankAccount.objects.filter(user=request.user)
    
    return render(request, 'banking/send_money.html', {
        'accounts': accounts
    })

@login_required
def open_savings_account(request):
    user = request.user
    
    # Check if user already has a savings account
    if BankAccount.objects.filter(user=user, account_type='SAVINGS').exists():
        messages.info(request, 'You already have a savings account.')
        return redirect('banking:dashboard')
    
    if request.method == 'POST':
        # Create a new savings account
        BankAccount.objects.create(
            user=user,
            account_type='SAVINGS',
            account_number=generate_account_number(),
            balance=0.00,
            interest_rate=1.50,  # 1.5% interest rate
            is_primary=False
        )
        
        messages.success(request, 'Savings account created successfully!')
        return redirect('banking:dashboard')
    
    return render(request, 'banking/open_savings_account.html')

@login_required
def apply_for_credit_card(request):
    user = request.user
    
    if request.method == 'POST':
        # Simple credit card application logic
        credit_limit = 1000.00  # Default credit limit
        
        # Create a new credit card with 1-year expiration
        expiration_date = timezone.now().date() + timedelta(days=365)
        
        CreditCard.objects.create(
            user=user,
            expiration_date=expiration_date,
            credit_limit=credit_limit,
            current_balance=0.00,
            available_credit=credit_limit,
            apr=18.99  # Default APR
        )
        
        messages.success(request, 'Credit card application approved!')
        return redirect('banking:dashboard')
    
    return render(request, 'banking/apply_credit_card.html')

@login_required
@transaction.atomic
def transfer_between_accounts(request):
    user = request.user
    accounts = BankAccount.objects.filter(user=user)
    
    if accounts.count() < 2:
        messages.error(request, 'You need at least two accounts to make a transfer.')
        return redirect('banking:dashboard')
    
    if request.method == 'POST':
        from_account_id = request.POST.get('from_account')
        to_account_id = request.POST.get('to_account')
        amount = float(request.POST.get('amount', 0))
        
        if from_account_id == to_account_id:
            messages.error(request, 'Cannot transfer to the same account.')
            return redirect('banking:transfer')
        
        if amount <= 0:
            messages.error(request, 'Please enter a valid amount.')
            return redirect('banking:transfer')
        
        from_account = get_object_or_404(BankAccount, id=from_account_id, user=user)
        to_account = get_object_or_404(BankAccount, id=to_account_id, user=user)
        
        if from_account.balance < amount:
            messages.error(request, 'Insufficient funds.')
            return redirect('banking:transfer')
        
        # Create transactions
        Transaction.objects.create(
            account=from_account,
            transaction_type='TRANSFER',
            amount=amount,
            status='COMPLETED',
            description=f'Transfer to {to_account.get_account_type_display()}'
        )
        
        Transaction.objects.create(
            account=to_account,
            transaction_type='TRANSFER',
            amount=amount,
            status='COMPLETED',
            description=f'Transfer from {from_account.get_account_type_display()}'
        )
        
        # Update balances
        from_account.balance -= amount
        to_account.balance += amount
        from_account.save()
        to_account.save()
        
        messages.success(request, 'Transfer completed successfully.')
        return redirect('banking:dashboard')
    
    return render(request, 'banking/transfer.html', {
        'accounts': accounts
    })

@login_required
def admin_dashboard(request):
    if not request.user.is_staff:
        messages.error(request, 'You do not have permission to access the admin dashboard.')
        return redirect('banking:dashboard')
    
    # Get pending transactions
    pending_transactions = Transaction.objects.filter(status='PENDING').order_by('-timestamp')
    
    # Get recent transactions
    recent_transactions = Transaction.objects.all().order_by('-timestamp')[:10]
    
    # Get account statistics
    total_accounts = BankAccount.objects.count()
    total_checking = BankAccount.objects.filter(account_type='CHECKING').count()
    total_savings = BankAccount.objects.filter(account_type='SAVINGS').count()
    total_credit_cards = CreditCard.objects.count()
    
    # Get user statistics
    total_users = User.objects.count()
    active_users = User.objects.filter(is_active=True).count()
    
    # Get transaction statistics
    total_transactions = Transaction.objects.count()
    pending_count = Transaction.objects.filter(status='PENDING').count()
    completed_count = Transaction.objects.filter(status='COMPLETED').count()
    rejected_count = Transaction.objects.filter(status='REJECTED').count()
    
    context = {
        'pending_transactions': pending_transactions,
        'recent_transactions': recent_transactions,
        'total_accounts': total_accounts,
        'total_checking': total_checking,
        'total_savings': total_savings,
        'total_credit_cards': total_credit_cards,
        'total_users': total_users,
        'active_users': active_users,
        'total_transactions': total_transactions,
        'pending_count': pending_count,
        'completed_count': completed_count,
        'rejected_count': rejected_count,
    }
    
    return render(request, 'banking/admin_dashboard.html', context)

@login_required
@transaction.atomic
def transfer_to_savings(request):
    if request.method == 'POST':
        try:
            amount = float(request.POST.get('amount', 0))
            
            if amount <= 0:
                messages.error(request, 'Please enter a valid amount.')
                return redirect('banking:transfer_to_savings')
            
            # Get user's accounts
            checking_account = BankAccount.objects.get(user=request.user, account_type='CHECKING')
            savings_account = BankAccount.objects.get(user=request.user, account_type='SAVINGS')
            
            if checking_account.balance < amount:
                messages.error(request, 'Insufficient funds in checking account.')
                return redirect('banking:transfer_to_savings')
            
            # Create withdrawal transaction for checking account
            Transaction.objects.create(
                account=checking_account,
                transaction_type='WITHDRAWAL',
                amount=amount,
                status='COMPLETED',
                description=f'Transfer to savings account'
            )
            
            # Create deposit transaction for savings account
            Transaction.objects.create(
                account=savings_account,
                transaction_type='DEPOSIT',
                amount=amount,
                status='COMPLETED',
                description=f'Transfer from checking account'
            )
            
            # Update balances
            checking_account.balance -= amount
            savings_account.balance += amount
            checking_account.save()
            savings_account.save()
            
            messages.success(request, 'Transfer to savings completed successfully.')
            return redirect('banking:dashboard')
            
        except (ValueError, BankAccount.DoesNotExist):
            messages.error(request, 'Invalid transaction details.')
            return redirect('banking:transfer_to_savings')
    
    return render(request, 'banking/transfer_to_savings.html')

@login_required
@transaction.atomic
def transfer_from_savings(request):
    if request.method == 'POST':
        try:
            amount = float(request.POST.get('amount', 0))
            
            if amount <= 0:
                messages.error(request, 'Please enter a valid amount.')
                return redirect('banking:transfer_from_savings')
            
            # Get user's accounts
            checking_account = BankAccount.objects.get(user=request.user, account_type='CHECKING')
            savings_account = BankAccount.objects.get(user=request.user, account_type='SAVINGS')
            
            if savings_account.balance < amount:
                messages.error(request, 'Insufficient funds in savings account.')
                return redirect('banking:transfer_from_savings')
            
            # Create withdrawal transaction for savings account
            Transaction.objects.create(
                account=savings_account,
                transaction_type='WITHDRAWAL',
                amount=amount,
                status='COMPLETED',
                description=f'Transfer to checking account'
            )
            
            # Create deposit transaction for checking account
            Transaction.objects.create(
                account=checking_account,
                transaction_type='DEPOSIT',
                amount=amount,
                status='COMPLETED',
                description=f'Transfer from savings account'
            )
            
            # Update balances
            savings_account.balance -= amount
            checking_account.balance += amount
            savings_account.save()
            checking_account.save()
            
            messages.success(request, 'Transfer from savings completed successfully.')
            return redirect('banking:dashboard')
            
        except (ValueError, BankAccount.DoesNotExist):
            messages.error(request, 'Invalid transaction details.')
            return redirect('banking:transfer_from_savings')
    
    return render(request, 'banking/transfer_from_savings.html')

@login_required
@user_passes_test(lambda u: u.is_staff) # Only staff can approve transactions
@transaction.atomic
def admin_approve_transaction(request, transaction_id):
    transaction_obj = get_object_or_404(Transaction, id=transaction_id)

    if request.method == 'POST':
        action = request.POST.get('action')

        if transaction_obj.status == 'PENDING':
            if action == 'approve':
                # Try to extract account numbers for internal transfer
                internal_match = re.search(r'Pending internal transfer from (\d+) to (\d+):', transaction_obj.description)
                
                # Try to extract sender account number for external transfer
                external_match = re.search(r'Pending external transfer from (\d+) to (\d+):', transaction_obj.description)

                if internal_match:
                    # Handle Internal Transfer Approval
                    sender_acc_num = internal_match.group(1)
                    recipient_acc_num = internal_match.group(2)
                    
                    if transaction_obj.transaction_type == 'WITHDRAWAL':
                        try:
                            sender_account = BankAccount.objects.get(account_number=sender_acc_num)
                            recipient_account = BankAccount.objects.get(account_number=recipient_acc_num)
                            
                            recipient_transaction = Transaction.objects.filter(
                                account=recipient_account,
                                transaction_type='DEPOSIT',
                                amount=transaction_obj.amount,
                                status='PENDING',
                                description__contains=f'from {sender_acc_num}'
                            ).exclude(id=transaction_obj.id).first()

                            if recipient_transaction:
                                sender_account.balance -= transaction_obj.amount
                                recipient_account.balance += transaction_obj.amount
                                sender_account.save()
                                recipient_account.save()

                                transaction_obj.status = 'COMPLETED'
                                transaction_obj.save()
                                recipient_transaction.status = 'COMPLETED'
                                recipient_transaction.save()

                                messages.success(request, 'Internal transfer approved and balances updated.')
                            else:
                                messages.error(request, 'Corresponding deposit transaction not found for internal transfer. Approval failed.')
                        except BankAccount.DoesNotExist:
                            messages.error(request, 'One or both internal accounts not found. Approval failed.')
                    
                    elif transaction_obj.transaction_type == 'DEPOSIT':
                        try:
                            sender_account = BankAccount.objects.get(account_number=sender_acc_num)
                            recipient_account = BankAccount.objects.get(account_number=recipient_acc_num)

                            sender_transaction = Transaction.objects.filter(
                                account=sender_account,
                                transaction_type='WITHDRAWAL',
                                amount=transaction_obj.amount,
                                status='PENDING',
                                description__contains=f'to {recipient_acc_num}'
                            ).exclude(id=transaction_obj.id).first()

                            if sender_transaction:
                                sender_account.balance -= transaction_obj.amount
                                recipient_account.balance += transaction_obj.amount
                                sender_account.save()
                                recipient_account.save()

                                transaction_obj.status = 'COMPLETED'
                                transaction_obj.save()
                                sender_transaction.status = 'COMPLETED'
                                sender_transaction.save()

                                messages.success(request, 'Internal transfer approved and balances updated.')
                            else:
                                messages.error(request, 'Corresponding withdrawal transaction not found for internal transfer. Approval failed.')
                        except BankAccount.DoesNotExist:
                            messages.error(request, 'One or both internal accounts not found. Approval failed.')
                    else:
                        messages.error(request, 'Invalid transaction type for internal transfer approval.')

                elif external_match:
                    # Handle External Transfer Approval
                    sender_acc_num = external_match.group(1)
                    external_recipient_acc_num = external_match.group(2) # This is just for logging/description

                    if transaction_obj.transaction_type == 'WITHDRAWAL':
                        try:
                            sender_account = BankAccount.objects.get(account_number=sender_acc_num)
                            
                            # Update sender's balance
                            sender_account.balance -= transaction_obj.amount
                            sender_account.save()

                            # Mark transaction as completed
                            transaction_obj.status = 'COMPLETED'
                            transaction_obj.save()

                            messages.success(request, f'External transfer to {external_recipient_acc_num} approved and sender\'s balance updated.')
                        except BankAccount.DoesNotExist:
                            messages.error(request, 'Sender account not found for external transfer. Approval failed.')
                    else:
                        messages.error(request, 'Only withdrawal transactions can be approved for external transfers.')

                else:
                    messages.error(request, 'Could not parse account numbers from description. Unknown transfer type.')

            elif action == 'reject':
                transaction_obj.status = 'CANCELLED'
                transaction_obj.save()
                messages.info(request, 'Transfer request rejected.')
            else:
                messages.error(request, 'Invalid action.')
        else:
            messages.warning(request, 'Transaction is not pending.')

    return redirect('banking:admin_dashboard')

@login_required
@user_passes_test(lambda u: u.is_staff)
@transaction.atomic
def admin_reject_transaction(request, transaction_id):
    transaction_obj = get_object_or_404(Transaction, id=transaction_id)
    
    if transaction_obj.status == 'PENDING':
        transaction_obj.status = 'REJECTED'
        transaction_obj.save()
        messages.info(request, 'Transaction has been rejected.')
    else:
        messages.warning(request, 'Transaction is not pending.')
    
    return redirect('banking:admin_dashboard')

@login_required
@transaction.atomic
def deposit(request):
    user = request.user
    accounts = []
    if hasattr(user, 'bankaccount'):
        accounts.append(user.bankaccount)
    if hasattr(user, 'savingsaccount'):
        accounts.append(user.savingsaccount)

    if request.method == 'POST':
        account_type = request.POST.get('account_type')
        amount = request.POST.get('amount')
        try:
            amount = float(amount)
            if amount <= 0:
                messages.error(request, 'Please enter a valid amount.')
                return redirect('banking:deposit')
        except (ValueError, TypeError):
            messages.error(request, 'Invalid amount.')
            return redirect('banking:deposit')

        if account_type == 'checking' and hasattr(user, 'bankaccount'):
            account = user.bankaccount
            Transaction.objects.create(
                account=account,
                transaction_type='DEPOSIT',
                amount=amount,
                status='COMPLETED',
                description='Deposit to checking account'
            )
            account.balance += amount
            account.save()
            messages.success(request, f'Successfully deposited ${amount:.2f} to your checking account.')
        elif account_type == 'savings' and hasattr(user, 'savingsaccount'):
            account = user.savingsaccount
            Transaction.objects.create(
                savings_account=account,
                transaction_type='DEPOSIT',
                amount=amount,
                status='COMPLETED',
                description='Deposit to savings account'
            )
            account.balance += amount
            account.save()
            messages.success(request, f'Successfully deposited ${amount:.2f} to your savings account.')
        else:
            messages.error(request, 'Invalid account selection.')
            return redirect('banking:deposit')
        return redirect('banking:dashboard')

    return render(request, 'banking/deposit.html', {
        'has_checking': hasattr(user, 'bankaccount'),
        'has_savings': hasattr(user, 'savingsaccount'),
        'checking_balance': user.bankaccount.balance if hasattr(user, 'bankaccount') else None,
        'savings_balance': user.savingsaccount.balance if hasattr(user, 'savingsaccount') else None,
    })

@login_required
def setup_direct_deposit(request):
    user = request.user
    checking_account = BankAccount.objects.filter(user=user, account_type='CHECKING').first()
    
    if not checking_account:
        messages.error(request, 'You need a checking account to set up direct deposit.')
        return redirect('banking:dashboard')
    
    if request.method == 'POST':
        employer_name = request.POST.get('employer_name')
        account_number = checking_account.account_number
        routing_number = '123456789'  # This would be your bank's routing number
        
        context = {
            'employer_name': employer_name,
            'account_number': account_number,
            'routing_number': routing_number,
            'checking_account': checking_account,
        }
        return render(request, 'banking/direct_deposit_success.html', context)
    
    return render(request, 'banking/setup_direct_deposit.html', {
        'checking_account': checking_account
    })

@login_required
def order_checks(request):
    user = request.user
    checking_account = BankAccount.objects.filter(user=user, account_type='CHECKING').first()
    
    if not checking_account:
        messages.error(request, 'You need a checking account to order checks.')
        return redirect('banking:dashboard')
    
    if request.method == 'POST':
        # Get form data
        quantity = request.POST.get('quantity')
        style = request.POST.get('style')
        address = request.POST.get('address')
        city = request.POST.get('city')
        state = request.POST.get('state')
        zip_code = request.POST.get('zip_code')
        
        # Calculate cost (example pricing)
        base_price = 15.99
        quantity_price = float(quantity) * 0.25
        style_price = 5.99 if style == 'premium' else 0
        total_cost = base_price + quantity_price + style_price
        
        context = {
            'checking_account': checking_account,
            'quantity': quantity,
            'style': style,
            'address': address,
            'city': city,
            'state': state,
            'zip_code': zip_code,
            'total_cost': total_cost,
            'base_price': base_price,
            'quantity_price': quantity_price,
            'style_price': style_price,
        }
        return render(request, 'banking/order_checks_success.html', context)
    
    return render(request, 'banking/order_checks.html', {
        'checking_account': checking_account
    })

@login_required
def pay_balance(request, card_id):
    try:
        credit_card = CreditCard.objects.get(id=card_id, user=request.user)
        checking_account = BankAccount.objects.filter(user=request.user, account_type='CHECKING').first()
        savings_account = BankAccount.objects.filter(user=request.user, account_type='SAVINGS').first()
        
        if request.method == 'POST':
            amount = Decimal(request.POST.get('amount', 0))
            payment_method = request.POST.get('payment_method')
            payment_date = request.POST.get('payment_date')
            scheduled_date = request.POST.get('scheduled_date')
            
            # Validate amount
            if amount <= 0 or amount > credit_card.current_balance:
                messages.error(request, 'Invalid payment amount.')
                return redirect('banking:pay_balance', card_id=card_id)
            
            # Get source account
            source_account = None
            if payment_method == 'checking' and checking_account:
                source_account = checking_account
            elif payment_method == 'savings' and savings_account:
                source_account = savings_account
            
            if not source_account:
                messages.error(request, 'Invalid payment method.')
                return redirect('banking:pay_balance', card_id=card_id)
            
            # Check sufficient funds
            if source_account.balance < amount:
                messages.error(request, 'Insufficient funds in selected account.')
                return redirect('banking:pay_balance', card_id=card_id)
            
            # Process payment
            with transaction.atomic():
                if payment_date == 'today':
                    # Deduct from source account
                    source_account.balance -= amount
                    source_account.save()
                    
                    # Update credit card balance
                    credit_card.current_balance -= amount
                    credit_card.available_credit += amount
                    credit_card.save()
                    
                    # Create transaction record
                    Transaction.objects.create(
                        user=request.user,
                        amount=amount,
                        transaction_type='PAYMENT',
                        status='COMPLETED',
                        description=f'Credit card payment for card ending in {credit_card.card_number[-4:]}',
                        source_account=source_account,
                        destination_account=None,
                        credit_card=credit_card
                    )
                    
                    messages.success(request, 'Payment processed successfully.')
                else:
                    # Schedule payment
                    ScheduledPayment.objects.create(
                        user=request.user,
                        amount=amount,
                        scheduled_date=scheduled_date,
                        status='PENDING',
                        source_account=source_account,
                        credit_card=credit_card
                    )
                    messages.success(request, 'Payment scheduled successfully.')
            
            return redirect('banking:dashboard')
        
        context = {
            'credit_card': credit_card,
            'checking_account': checking_account,
            'savings_account': savings_account,
            'today': timezone.now()
        }
        return render(request, 'banking/pay_balance.html', context)
        
    except CreditCard.DoesNotExist:
        messages.error(request, 'Credit card not found.')
        return redirect('banking:dashboard')

@login_required
def scheduled_payments(request):
    user = request.user
    scheduled_payments = ScheduledPayment.objects.filter(user=user).order_by('scheduled_date')
    
    if request.method == 'POST':
        payment_id = request.POST.get('payment_id')
        action = request.POST.get('action')
        
        try:
            payment = ScheduledPayment.objects.get(id=payment_id, user=user)
            
            if action == 'cancel' and payment.status == 'PENDING':
                payment.status = 'CANCELLED'
                payment.save()
                messages.success(request, 'Payment cancelled successfully.')
            elif action == 'process' and payment.status == 'PENDING':
                with transaction.atomic():
                    # Check if source account has sufficient funds
                    if payment.source_account.balance < payment.amount:
                        payment.status = 'FAILED'
                        payment.save()
                        messages.error(request, 'Insufficient funds for scheduled payment.')
                        return redirect('banking:scheduled_payments')
                    
                    # Process the payment
                    payment.source_account.balance -= payment.amount
                    payment.source_account.save()
                    
                    payment.credit_card.current_balance -= payment.amount
                    payment.credit_card.available_credit += payment.amount
                    payment.credit_card.save()
                    
                    # Create transaction record
                    Transaction.objects.create(
                        user=user,
                        amount=payment.amount,
                        transaction_type='PAYMENT',
                        status='COMPLETED',
                        description=f'Scheduled credit card payment for card ending in {payment.credit_card.card_number[-4:]}',
                        source_account=payment.source_account,
                        destination_account=None,
                        credit_card=payment.credit_card
                    )
                    
                    payment.status = 'COMPLETED'
                    payment.save()
                    messages.success(request, 'Scheduled payment processed successfully.')
            
        except ScheduledPayment.DoesNotExist:
            messages.error(request, 'Payment not found.')
        
        return redirect('banking:scheduled_payments')
    
    context = {
        'scheduled_payments': scheduled_payments,
        'today': timezone.now().date()
    }
    return render(request, 'banking/scheduled_payments.html', context)
