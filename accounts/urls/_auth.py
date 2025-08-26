# accounts/urls/_auth.py
# This file defines authentication-related URLs for the "accounts" app.
# It delegates the routes to Djoser, which handles JWT and standard user endpoints.

from django.urls import path, include

urlpatterns = [
    # JWT authentication endpoints (token obtain, refresh, verify)
    path('auth/', include('djoser.urls.jwt')),

    # Standard Djoser endpoints (user create, retrieve, delete, password reset, etc.)
    path('auth/', include('djoser.urls')),
]
