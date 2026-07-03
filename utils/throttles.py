"""
Named scoped throttles for universal sensitive endpoints.

Each throttle class sets a fixed ``scope`` resolved against
``REST_FRAMEWORK['DEFAULT_THROTTLE_RATES']`` at init time via
``SimpleRateThrottle``.

Controlled by the ``THROTTLE_ENABLED`` setting (default ``True``). When
``False``, the base classes below unconditionally return ``None`` from
``get_cache_key`` so no throttling occurs.

NOTE: All classes use ``SimpleRateThrottle`` (not ``ScopedRateThrottle``,
which silently overrides ``self.scope`` from ``view.throttle_scope`` in
``allow_request()`` and would bypass a class-level ``scope``).

Path: utils/throttles.py
"""

import hashlib

from rest_framework.throttling import SimpleRateThrottle


def _throttle_enabled():
    from django.conf import settings

    return getattr(settings, "THROTTLE_ENABLED", True)


class _UserOrIPThrottle(SimpleRateThrottle):
    """
    Base throttle: keyed by user PK (authenticated) or client IP (anonymous).
    Subclasses only need to set ``scope``.
    """

    def get_cache_key(self, request, view):
        if not _throttle_enabled():
            return None
        if request.user and request.user.is_authenticated:
            ident = request.user.pk
        else:
            ident = self.get_ident(request)
        return self.cache_format % {"scope": self.scope, "ident": ident}


class _IPOnlyThrottle(SimpleRateThrottle):
    """
    Base throttle: always keyed by client IP, even for authenticated users.
    Use for public/pre-auth endpoints where per-IP limiting is desired
    regardless of authentication state.
    """

    def get_cache_key(self, request, view):
        if not _throttle_enabled():
            return None
        return self.cache_format % {"scope": self.scope, "ident": self.get_ident(request)}


class DefaultAnonThrottle(_IPOnlyThrottle):
    """Global fallback for anonymous requests on views without explicit throttle."""

    scope = "default_anon"


class DefaultUserThrottle(_UserOrIPThrottle):
    """Global fallback for authenticated requests on views without explicit throttle."""

    scope = "default_user"


class AuthLoginThrottle(_IPOnlyThrottle):
    """Rate limit for login. Scope: auth_login."""

    scope = "auth_login"


class AuthLoginAccountThrottle(SimpleRateThrottle):
    """
    Per-credential brute-force guard.

    Keyed by a SHA-256 hash of the normalised credential so that an
    attacker with many IPs cannot enumerate passwords for a specific
    account. Returns ``None`` (no throttling) when disabled globally or
    when no credential was submitted.
    """

    scope = "auth_login_account"

    def get_cache_key(self, request, view):
        if not _throttle_enabled():
            return None
        credential = (
            request.data.get("username") or request.data.get("email") or ""
        ).lower().strip()
        if not credential:
            return None
        digest = hashlib.sha256(credential.encode()).hexdigest()[:24]
        return self.cache_format % {"scope": self.scope, "ident": digest}


class AuthRegisterThrottle(_IPOnlyThrottle):
    """Rate limit for registration. Scope: auth_register."""

    scope = "auth_register"


class AuthResetThrottle(_IPOnlyThrottle):
    """Rate limit for password/username reset requests. Scope: auth_reset."""

    scope = "auth_reset"


class AuthSetPasswordThrottle(_UserOrIPThrottle):
    """
    Rate limit for password/username *change* (user already authenticated,
    knows their current credential). Keyed by user PK so limits apply
    per-account rather than per-IP. Scope: auth_set_password.
    """

    scope = "auth_set_password"


class AuthRefreshThrottle(_IPOnlyThrottle):
    """Rate limit for JWT token refresh. Scope: auth_refresh."""

    scope = "auth_refresh"


class AuthActivationThrottle(_IPOnlyThrottle):
    """
    Rate limit for account activation endpoints (uid/token in path).
    Keyed by IP to prevent UID enumeration via brute-force.
    Scope: auth_activation.
    """

    scope = "auth_activation"


class PublicListThrottle(_IPOnlyThrottle):
    """Rate limit for public list endpoints. Scope: public_list."""

    scope = "public_list"


class SearchThrottle(_UserOrIPThrottle):
    """Rate limit for global search (public endpoint). Scope: search."""

    scope = "search"


class WebhookThrottle(_IPOnlyThrottle):
    """Rate limit for webhook endpoints. Scope: webhook."""

    scope = "webhook"


class ExternalAPIThrottle(SimpleRateThrottle):
    """Rate limit for external API endpoints. Keyed by the X-API-Key header."""

    scope = "external_api"

    def get_cache_key(self, request, view):
        if not _throttle_enabled():
            return None
        api_key = request.headers.get("X-API-Key") or request.headers.get("x-api-key")
        if api_key:
            return self.cache_format % {"scope": self.scope, "ident": api_key[:64]}
        # Fall back to IP-based throttling when no API key is present, so
        # requests without the header cannot bypass rate limiting.
        return self.cache_format % {"scope": self.scope, "ident": self.get_ident(request)}


class UserMutationThrottle(_UserOrIPThrottle):
    """Per-user rate limit for account mutation endpoints. Scope: user_mutation."""

    scope = "user_mutation"


class PasswordResetThrottle(_IPOnlyThrottle):
    """
    Legacy compat alias — original password-reset throttle name/scope,
    kept so pre-existing importers do not break. New code should use
    ``AuthResetThrottle`` (scope ``auth_reset``) instead.
    """

    scope = "auth_password_reset"
