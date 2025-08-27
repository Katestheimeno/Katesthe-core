"""
Authentication-related URLs for the accounts app.
Path: accounts/urls/_auth.py
Custom JWT endpoints and standard Djoser endpoints.
"""

from django.urls import path, include
from rest_framework_simplejwt.views import TokenRefreshView, TokenVerifyView
from accounts.controllers import CustomJWTTokenCreateView, CustomJWTLogoutView, CustomActivationView

urlpatterns = [
    # Custom activation endpoint (renders HTML page)
    path('auth/users/activation/<str:uid>/<str:token>/', CustomActivationView.as_view(), name='user-activation'),
    
    # Custom JWT authentication endpoints (no duplicate paths)
    path('auth/jwt/create/', CustomJWTTokenCreateView.as_view(), name='jwt-create'),
    path('auth/jwt/refresh/', TokenRefreshView.as_view(), name='jwt-refresh'),
    path('auth/jwt/verify/', TokenVerifyView.as_view(), name='jwt-verify'),
    path('auth/jwt/destroy/', CustomJWTLogoutView.as_view(), name='jwt-destroy'),

    # Standard Djoser endpoints (user create, retrieve, delete, password reset, etc.)
    path('auth/', include('djoser.urls')),
]
