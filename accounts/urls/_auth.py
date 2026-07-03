"""
Authentication-related URLs for the accounts app.
Path: accounts/urls/_auth.py
Custom JWT endpoints and standard Djoser endpoints.
"""

from django.urls import path
from accounts.controllers import (
    CustomJWTTokenCreateView,
    CustomJWTTokenRefreshView,
    CustomJWTTokenVerifyView,
    CustomJWTLogoutView,
    CustomActivationView,
    CustomUserViewSet,
    CSRFTokenView,
    JWKSView,
)

urlpatterns = [
    # Public JWKS endpoint (RFC 7517). Resolved absolute URL:
    # /api/v1/.well-known/jwks.json. Placed before the djoser include so it
    # is not shadowed by any auth/ catch-all patterns.
    path('.well-known/jwks.json', JWKSView.as_view(), name='jwks'),

    # Custom activation endpoint (only the specific pattern to avoid conflicts)
    path('auth/users/activation/<str:uid>/<str:token>/', CustomActivationView.as_view(), name='user-activation'),

    # Custom JWT authentication endpoints (no duplicate paths)
    path('auth/jwt/create/', CustomJWTTokenCreateView.as_view(), name='jwt-create'),
    path('auth/jwt/refresh/', CustomJWTTokenRefreshView.as_view(), name='jwt-refresh'),
    path('auth/jwt/verify/', CustomJWTTokenVerifyView.as_view(), name='jwt-verify'),
    path('auth/jwt/destroy/', CustomJWTLogoutView.as_view(), name='jwt-destroy'),

    # Standard Djoser endpoints, routed explicitly to CustomUserViewSet.
    # (Subtask 019: djoser has no ``VIEWS`` setting, so ``include('djoser.urls')``
    # would resolve these to djoser's own UserViewSet, making every override
    # on CustomUserViewSet dead code. Binding explicitly here fixes that.)
    path('auth/users/', CustomUserViewSet.as_view({'get': 'list', 'post': 'create'}), name='user-list'),
    path('auth/users/me/', CustomUserViewSet.as_view({'get': 'me', 'put': 'me', 'patch': 'me', 'delete': 'me'}), name='user-me'),
    path('auth/users/set_password/', CustomUserViewSet.as_view({'post': 'set_password'}), name='user-set-password'),
    path('auth/users/set_username/', CustomUserViewSet.as_view({'post': 'set_username'}), name='user-set-username'),
    path('auth/users/resend_activation/', CustomUserViewSet.as_view({'post': 'resend_activation'}), name='user-resend-activation'),
    path('auth/users/reset_password/', CustomUserViewSet.as_view({'post': 'reset_password'}), name='user-reset-password'),
    path('auth/users/reset_password_confirm/', CustomUserViewSet.as_view({'post': 'reset_password_confirm'}), name='user-reset-password-confirm'),
    path('auth/users/reset_username/', CustomUserViewSet.as_view({'post': 'reset_username'}), name='user-reset-username'),
    path('auth/users/reset_username_confirm/', CustomUserViewSet.as_view({'post': 'reset_username_confirm'}), name='user-reset-username-confirm'),
    path('auth/users/logout-all/', CustomUserViewSet.as_view({'post': 'logout_all'}), name='user-logout-all'),
    path('auth/users/<int:pk>/', CustomUserViewSet.as_view({'get': 'retrieve', 'put': 'update', 'patch': 'partial_update', 'delete': 'destroy'}), name='user-detail'),
    path('auth/csrf/', CSRFTokenView.as_view(), name='auth-csrf'),
]
