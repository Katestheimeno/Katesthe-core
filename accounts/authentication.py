"""
Cookie-based JWT authentication for DRF.
Path: accounts/authentication.py

Reads the access token from an HttpOnly cookie (primary) or the
``Authorization`` header (fallback for backward compatibility / non-browser
clients). When authenticating via cookie, CSRF is enforced to prevent
cross-site request forgery on cookie-transported mutations.
"""

from django.conf import settings
from django.middleware.csrf import CsrfViewMiddleware
from rest_framework import exceptions
from rest_framework_simplejwt.authentication import JWTAuthentication

from accounts.services.session import is_token_revoked
from config.logger import logger


class _CSRFCheck(CsrfViewMiddleware):
    """Thin wrapper that returns the rejection reason instead of an HttpResponse."""

    def _reject(self, request, reason):
        return reason


def enforce_csrf(request) -> None:
    """
    Manually enforce CSRF for cookie-based auth on mutation endpoints.

    Reusable by any view that needs to enforce CSRF outside the middleware
    pipeline (e.g. the token refresh view when the refresh token comes from a
    cookie). Never catch the resulting exception here — a CSRF rejection must
    never be downgraded to another auth path.
    """
    check = _CSRFCheck(lambda req: None)
    check.process_request(request)
    reason = check.process_view(request, None, (), {})
    if reason:
        logger.debug("csrf.check_failed", reason=reason)
        raise exceptions.PermissionDenied("CSRF Failed")


class CookieJWTAuthentication(JWTAuthentication):
    """
    Authenticates via, in order:

    1. HttpOnly access-token cookie (``SIMPLE_JWT["AUTH_COOKIE_ACCESS"]``) —
       CSRF is enforced.
    2. ``Authorization: Bearer <token>`` header — no CSRF, safe by design.

    A bad/expired access cookie gracefully downgrades to header auth. A CSRF
    failure on a valid cookie token NEVER downgrades — it always raises.

    Both paths reject a token issued before the user's last session
    revocation (logout-all, password change, username change, account
    deletion) — see ``accounts.services.session.is_token_revoked``.
    """

    def authenticate(self, request):
        cookie_name = settings.SIMPLE_JWT["AUTH_COOKIE_ACCESS"]
        raw_token = request.COOKIES.get(cookie_name)

        if raw_token is None:
            return self._reject_if_revoked(super().authenticate(request))

        try:
            validated_token = self.get_validated_token(raw_token)
        except exceptions.AuthenticationFailed:
            # Graceful fallback: a bad/expired access cookie must not block a
            # valid Authorization: Bearer header (e.g. logout right after the
            # access token expired). CSRF failures below are NOT caught here.
            logger.debug("auth.cookie_token_invalid_falling_back_to_header")
            return self._reject_if_revoked(super().authenticate(request))

        enforce_csrf(request)
        if is_token_revoked(validated_token):
            raise exceptions.AuthenticationFailed("Session revoked")
        user = self.get_user(validated_token)
        return (user, validated_token)

    @staticmethod
    def _reject_if_revoked(result):
        """Apply the same revocation check to the header-auth fallback path."""
        if result is None:
            return None
        user, validated_token = result
        if is_token_revoked(validated_token):
            raise exceptions.AuthenticationFailed("Session revoked")
        return (user, validated_token)
