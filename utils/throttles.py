"""
Named scoped throttles for universal sensitive endpoints.
Path: utils/throttles.py
"""

from rest_framework.throttling import UserRateThrottle


class AuthLoginThrottle(UserRateThrottle):
    """Throttle applied to login endpoints."""

    scope = "auth_login"


class PasswordResetThrottle(UserRateThrottle):
    """Throttle applied to password-reset request endpoints."""

    scope = "auth_password_reset"
