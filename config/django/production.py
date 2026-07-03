"""
Production settings entry.
Path: config/django/production.py
"""

from django.core.exceptions import ImproperlyConfigured

from config.django.base import *  # noqa: F401,F403
from config.settings.config import settings as app_settings

# Boot-time assertions — fail fast on misconfiguration rather than serving an
# insecure production deployment. `DEBUG` and `ALLOWED_HOSTS` here are the
# resolved Django globals exported by base.py (`from config.settings import *`),
# not the pydantic settings object.
assert not DEBUG, "DEBUG must be False in production"
assert ALLOWED_HOSTS and ALLOWED_HOSTS != ["*"], "ALLOWED_HOSTS must be explicit"

# JWT RS256 enforcement — production MUST sign tokens with an RSA key pair
# (dev/local may fall back to a transient auto-generated key). `app_settings`
# is the pydantic `MainSettings` singleton, not the Django settings object —
# `JWT_RSA_PRIVATE_KEY`/`JWT_ISSUER` are never exposed on Django `settings`.
if not app_settings.JWT_RSA_PRIVATE_KEY:
    raise ImproperlyConfigured(
        "JWT_RSA_PRIVATE_KEY is required in production. "
        "Run `python manage.py generate_jwt_keys` to create one."
    )
if not app_settings.JWT_ISSUER:
    import warnings

    warnings.warn("JWT_ISSUER not set — tokens will not carry an 'iss' claim.")

# Security headers
# SECURE_CONTENT_TYPE_NOSNIFF, SECURE_REFERRER_POLICY, and X_FRAME_OPTIONS are
# baseline values set in base.py and inherited here — single source of truth.
SECURE_HSTS_SECONDS = 31536000  # 1 year
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True

# Respect proxy TLS termination (PaaS)
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

# CSRF must trust the same explicit hosts ALLOWED_HOSTS enforces above.
CSRF_TRUSTED_ORIGINS = [f"https://{h}" for h in ALLOWED_HOSTS if h != "*"]

# Error monitoring (no-op unless SENTRY_DSN is set and sentry-sdk is installed)
from config.settings.monitoring import configure_sentry  # noqa: E402
configure_sentry()
