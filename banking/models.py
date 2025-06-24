from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator
import random
import string
from decimal import Decimal

def generate_card_number():
    return ''.join(random.choices(string.digits, k=16))

def generate_cvv():
    return ''.join(random.choices(string.digits, k=3))

class BankAccount(models.Model):
    ACCOUNT_TYPES = [
        ('CHECKING', 'Checking Account'),
        ('SAVINGS', 'Savings Account'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='accounts')
    account_type = models.CharField(max_length=10, choices=ACCOUNT_TYPES, default='CHECKING')
    account_number = models.CharField(max_length=20, unique=True)
    balance = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])
    interest_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0.00, help_text='Annual interest rate (%) for savings accounts')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_primary = models.BooleanField(default=False, help_text='Designates whether this is the primary account for the user')

    class Meta:
        unique_together = ['user', 'account_type']

    def __str__(self):
        return f"{self.user.username}'s {self.get_account_type_display()} ({self.account_number})"

class SavingsAccount(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    account_number = models.CharField(max_length=20, unique=True)
    balance = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])
    interest_rate = models.DecimalField(max_digits=4, decimal_places=2, default=2.50)  # Default 2.50% interest rate
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def calculate_interest(self):
        """Calculate monthly interest"""
        monthly_rate = self.interest_rate / Decimal('12') / Decimal('100')
        interest = self.balance * monthly_rate
        return interest

    def __str__(self):
        return f"{self.user.username}'s Savings ({self.account_number})"

class CreditCard(models.Model):
    STATUS_CHOICES = [
        ('ACTIVE', 'Active'),
        ('INACTIVE', 'Inactive'),
        ('BLOCKED', 'Blocked'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='credit_cards')
    card_number = models.CharField(max_length=16, unique=True, default=generate_card_number)
    expiration_date = models.DateField()
    cvv = models.CharField(max_length=3, default=generate_cvv)
    credit_limit = models.DecimalField(max_digits=10, decimal_places=2)
    current_balance = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    available_credit = models.DecimalField(max_digits=10, decimal_places=2)
    apr = models.DecimalField(max_digits=5, decimal_places=2, help_text='Annual Percentage Rate (%)')
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='ACTIVE')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.username}'s Credit Card (ending in {self.card_number[-4:]})"
    
    def save(self, *args, **kwargs):
        # Calculate available credit when saving
        self.available_credit = self.credit_limit - self.current_balance
        super().save(*args, **kwargs)

class Transaction(models.Model):
    TRANSACTION_TYPES = [
        ('DEPOSIT', 'Deposit'),
        ('WITHDRAWAL', 'Withdrawal'),
        ('TRANSFER', 'Transfer'),
        ('INTEREST', 'Interest'),
    ]
    
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('COMPLETED', 'Completed'),
        ('FAILED', 'Failed'),
        ('CANCELLED', 'Cancelled'),
    ]

    account = models.ForeignKey(BankAccount, on_delete=models.CASCADE, related_name='transactions', null=True, blank=True)
    savings_account = models.ForeignKey(SavingsAccount, on_delete=models.CASCADE, related_name='transactions', null=True, blank=True)
    transaction_type = models.CharField(max_length=10, choices=TRANSACTION_TYPES)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    timestamp = models.DateTimeField(auto_now_add=True)
    description = models.CharField(max_length=200)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='COMPLETED')

    def __str__(self):
        account = self.account or self.savings_account
        return f"{self.transaction_type} of {self.amount} on {self.timestamp} ({self.status})"

class ScheduledPayment(models.Model):
    PAYMENT_STATUS = [
        ('PENDING', 'Pending'),
        ('COMPLETED', 'Completed'),
        ('CANCELLED', 'Cancelled'),
        ('FAILED', 'Failed')
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    credit_card = models.ForeignKey(CreditCard, on_delete=models.CASCADE)
    source_account = models.ForeignKey(BankAccount, on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    scheduled_date = models.DateField()
    status = models.CharField(max_length=20, choices=PAYMENT_STATUS, default='PENDING')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-scheduled_date']
    
    def __str__(self):
        return f"Scheduled payment of ${self.amount} for card ending in {self.credit_card.card_number[-4:]} on {self.scheduled_date}"
