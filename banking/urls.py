from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

app_name = 'banking'

urlpatterns = [
    path('', views.homepage, name='homepage'),
    path('login/', views.CustomLoginView.as_view(), name='login'),
    path('register/', views.RegisterView.as_view(), name='register'),
    path('dashboard/', views.DashboardView.as_view(), name='dashboard'),
    path('transactions/', views.transaction_history, name='transaction_history'),
    path('send-money/', views.send_money, name='send_money'),
    path('logout/', auth_views.LogoutView.as_view(next_page='banking:login'), name='logout'),
    path('open-savings/', views.open_savings_account, name='open_savings_account'),
    path('setup-direct-deposit/', views.setup_direct_deposit, name='setup_direct_deposit'),
    path('apply-credit-card/', views.apply_for_credit_card, name='apply_credit_card'),
    path('transfer/', views.transfer_between_accounts, name='transfer'),
    path('transfer-to-savings/', views.transfer_to_savings, name='transfer_to_savings'),
    path('transfer-from-savings/', views.transfer_from_savings, name='transfer_from_savings'),
    path('deposit/', views.deposit, name='deposit'),
    path('order-checks/', views.order_checks, name='order_checks'),
    path('admin_dashboard/', views.admin_dashboard, name='admin_dashboard'),
    path('admin/approve-transaction/<int:transaction_id>/', views.admin_approve_transaction, name='admin_approve_transaction'),
    path('admin/reject-transaction/<int:transaction_id>/', views.admin_reject_transaction, name='admin_reject_transaction'),
    path('pay-balance/<int:card_id>/', views.pay_balance, name='pay_balance'),
    path('scheduled-payments/', views.scheduled_payments, name='scheduled_payments'),
]