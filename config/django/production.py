"""
Production settings entry.
Path: config/django/production.py
"""

from config.django.base import *  # noqa: F401,F403

# Boot-time assertions — fail fast on misconfiguration rather than serving an
# insecure production deployment. `DEBUG` and `ALLOWED_HOSTS` here are the
# resolved Django globals exported by base.py (`from config.settings import *`),
# not the pydantic settings object.
assert not DEBUG, "DEBUG must be False in production"
assert ALLOWED_HOSTS and ALLOWED_HOSTS != ["*"], "ALLOWED_HOSTS must be explicit"

# Security headers
SECURE_HSTS_SECONDS = 31536000  # 1 year
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = "same-origin"
X_FRAME_OPTIONS = "DENY"

# Respect proxy TLS termination (PaaS)
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

# Error monitoring (no-op unless SENTRY_DSN is set and sentry-sdk is installed)
from config.settings.monitoring import configure_sentry  # noqa: E402
configure_sentry()
