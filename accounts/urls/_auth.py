"""
Authentication-related URLs for the accounts app.
Path: accounts/urls/_auth.py
Custom JWT endpoints and standard Djoser endpoints.
"""

from django.urls import path, include
from accounts.controllers import (
    CustomJWTTokenCreateView,
    CustomJWTTokenRefreshView,
    CustomJWTTokenVerifyView,
    CustomJWTLogoutView,
    CustomActivationView,
)

urlpatterns = [
    # Custom activation endpoint (only the specific pattern to avoid conflicts)
    path('auth/users/activation/<str:uid>/<str:token>/', CustomActivationView.as_view(), name='user-activation'),
    
    # Custom JWT authentication endpoints (no duplicate paths)
    path('auth/jwt/create/', CustomJWTTokenCreateView.as_view(), name='jwt-create'),
    path('auth/jwt/refresh/', CustomJWTTokenRefreshView.as_view(), name='jwt-refresh'),
    path('auth/jwt/verify/', CustomJWTTokenVerifyView.as_view(), name='jwt-verify'),
    path('auth/jwt/destroy/', CustomJWTLogoutView.as_view(), name='jwt-destroy'),

    # Standard Djoser endpoints (user create, retrieve, delete, password reset, etc.)
    path('auth/', include('djoser.urls')),
]
