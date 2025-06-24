from django.contrib import admin
from django.urls import path, include
from django.shortcuts import redirect
from django.contrib.auth import views as auth_views

urlpatterns = [
    path('', lambda request: redirect('banking:login'), name='home'),
    path('admin/', admin.site.urls),
    path('banking/', include('banking.urls')),
    path('logout/', auth_views.LogoutView.as_view(next_page='banking:login'), name='logout'),
]
