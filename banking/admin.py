from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import User
from .models import BankAccount, Transaction, CreditCard

class BankAccountInline(admin.TabularInline):
    model = BankAccount
    extra = 0
    verbose_name_plural = 'Bank Accounts'
    fields = ('account_type', 'account_number', 'balance', 'interest_rate', 'is_primary')

class CreditCardInline(admin.TabularInline):
    model = CreditCard
    extra = 0
    verbose_name_plural = 'Credit Cards'
    fields = ('card_number', 'expiration_date', 'credit_limit', 'current_balance', 'available_credit', 'apr', 'status')

class CustomUserAdmin(UserAdmin):
    inlines = (BankAccountInline, CreditCardInline)
    list_display = ('username', 'email', 'first_name', 'last_name', 'is_staff', 'get_checking_account', 'get_savings_account', 'get_credit_card')
    
    def get_checking_account(self, obj):
        try:
            account = obj.accounts.filter(account_type='CHECKING').first()
            return f"{account.account_number} (${account.balance})" if account else '-'
        except:
            return '-'
    get_checking_account.short_description = 'Checking Account'
    
    def get_savings_account(self, obj):
        try:
            account = obj.accounts.filter(account_type='SAVINGS').first()
            return f"{account.account_number} (${account.balance})" if account else '-'
        except:
            return '-'
    get_savings_account.short_description = 'Savings Account'
    
    def get_credit_card(self, obj):
        try:
            card = obj.credit_cards.first()
            return f"...{card.card_number[-4:]} (${card.current_balance}/{card.credit_limit})" if card else '-'
        except:
            return '-'
    get_credit_card.short_description = 'Credit Card'

class BankAccountAdmin(admin.ModelAdmin):
    list_display = ('account_number', 'user', 'account_type', 'balance', 'interest_rate', 'is_primary', 'created_at')
    list_filter = ('account_type', 'is_primary', 'created_at')
    search_fields = ('account_number', 'user__username', 'user__email')
    readonly_fields = ('created_at', 'updated_at')

class CreditCardAdmin(admin.ModelAdmin):
    list_display = ('card_number_masked', 'user', 'credit_limit', 'current_balance', 'available_credit', 'status', 'created_at')
    list_filter = ('status', 'created_at')
    search_fields = ('card_number', 'user__username', 'user__email')
    readonly_fields = ('available_credit', 'created_at', 'updated_at')
    
    def card_number_masked(self, obj):
        return f"**** **** **** {obj.card_number[-4:]}"
    card_number_masked.short_description = 'Card Number'

class TransactionAdmin(admin.ModelAdmin):
    list_display = ('get_account_info', 'transaction_type', 'amount', 'status', 'timestamp', 'description')
    list_filter = ('transaction_type', 'status', 'timestamp')
    search_fields = ('account__account_number', 'credit_card__card_number', 'description')
    readonly_fields = ('timestamp',)
    
    def get_account_info(self, obj):
        if obj.account:
            return f"{obj.account.account_type}: {obj.account.account_number}"
        elif obj.credit_card:
            return f"Credit Card: **** {obj.credit_card.card_number[-4:]}"
        return "-"
    get_account_info.short_description = 'Account'

# Unregister the default UserAdmin and register our custom one
admin.site.unregister(User)
admin.site.register(User, CustomUserAdmin)
admin.site.register(BankAccount, BankAccountAdmin)
admin.site.register(CreditCard, CreditCardAdmin)
admin.site.register(Transaction, TransactionAdmin)
