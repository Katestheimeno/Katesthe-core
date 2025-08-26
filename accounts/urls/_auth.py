"""
Authentication-related URLs for the accounts app.
Path: accounts/urls/_auth.py
Delegates routes to Djoser for JWT and standard endpoints.
"""

from django.urls import path, include

urlpatterns = [
    # JWT authentication endpoints (token obtain, refresh, verify)
    path('auth/', include('djoser.urls.jwt')),

    # Standard Djoser endpoints (user create, retrieve, delete, password reset, etc.)
    path('auth/', include('djoser.urls')),
]
