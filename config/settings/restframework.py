"""
DRF and SimpleJWT configuration.
Path: config/settings/restframework.py
"""

import warnings
from datetime import timedelta

from config.jwt_keys import (
    compute_kid,
    compute_kid_from_public,
    generate_rsa_private_key,
    load_rsa_private_key,
    load_rsa_public_key,
    private_key_to_pem,
    public_key_to_pem,
)
from config.settings.config import settings

# Keep track of which settings we’re exporting in __all__
imports = []

# --- RSA key loading (RS256) ---
if settings.JWT_RSA_PRIVATE_KEY:
    _rsa_private_key = load_rsa_private_key(settings.JWT_RSA_PRIVATE_KEY)
else:
    warnings.warn(
        "JWT_RSA_PRIVATE_KEY not set — generating a transient RSA key. "
        "Tokens will not survive restarts and multi-worker setups will 401.",
        stacklevel=2,
    )
    _rsa_private_key = generate_rsa_private_key()

_rsa_signing_pem = private_key_to_pem(_rsa_private_key)
_rsa_verifying_pem = public_key_to_pem(_rsa_private_key)
_rsa_kid = compute_kid(_rsa_private_key)

# Optional rotation window (previous public key for JWKS)
_rsa_previous_public_key = None
_rsa_previous_kid = None
if settings.JWT_RSA_PREVIOUS_PUBLIC_KEY:
    _rsa_previous_public_key = load_rsa_public_key(settings.JWT_RSA_PREVIOUS_PUBLIC_KEY)
    _rsa_previous_kid = compute_kid_from_public(_rsa_previous_public_key)

# Expose key objects for the JWKS endpoint and other consumers
imports += [
    "JWT_RSA_PRIVATE_KEY_OBJ",
    "JWT_KID",
    "JWT_PREVIOUS_PUBLIC_KEY_OBJ",
    "JWT_PREVIOUS_KID",
]
JWT_RSA_PRIVATE_KEY_OBJ = _rsa_private_key
JWT_KID = _rsa_kid
JWT_PREVIOUS_PUBLIC_KEY_OBJ = _rsa_previous_public_key
JWT_PREVIOUS_KID = _rsa_previous_kid

# --- JWT CONFIGURATION ---
imports += ["SIMPLE_JWT"]


SIMPLE_JWT = {
    # --------------------------
    # Token lifetimes
    # --------------------------
    # short-lived access token
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=15),
    # longer-lived refresh token
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),

    # --------------------------
    # Rotation / Blacklisting
    # --------------------------
    # set True if you want new refresh tokens each time
    "ROTATE_REFRESH_TOKENS": True,
    # needs django-rest-framework-simplejwt[token_blacklist]
    "BLACKLIST_AFTER_ROTATION": True,

    # --------------------------
    # User handling
    # --------------------------
    "UPDATE_LAST_LOGIN": True,          # keep track of last_login automatically
    "USER_ID_FIELD": "id",              # default User model PK
    "USER_ID_CLAIM": "user_id",         # how the claim appears in the JWT payload

    # --------------------------
    # JWT signing / validation (RS256 asymmetric)
    # --------------------------
    "ALGORITHM": "RS256",
    "SIGNING_KEY": _rsa_signing_pem,
    "VERIFYING_KEY": _rsa_verifying_pem,
    "AUDIENCE": settings.JWT_AUDIENCE,   # set if you issue tokens to multiple clients
    "ISSUER": settings.JWT_ISSUER,       # set if you want issuer validation
    "KID": _rsa_kid,                     # injected into JWT headers

    # --------------------------
    # HTTP integration
    # --------------------------
    "AUTH_HEADER_TYPES": ("Bearer",),   # or ("JWT",) if you prefer
    "AUTH_HEADER_NAME": "HTTP_AUTHORIZATION",

    # --------------------------
    # Token classes
    # --------------------------
    "AUTH_TOKEN_CLASSES": ("rest_framework_simplejwt.tokens.AccessToken",),
    "TOKEN_TYPE_CLAIM": "token_type",

    # --------------------------
    # Cookie transport
    # --------------------------
    "AUTH_COOKIE_ACCESS": "access_token",
    "AUTH_COOKIE_REFRESH": "refresh_token",
    "AUTH_COOKIE_HTTP_ONLY": True,
    "AUTH_COOKIE_PATH": "/",
    "AUTH_COOKIE_REFRESH_PATH": settings.AUTH_COOKIE_REFRESH_PATH,
}

# --- DRF CONFIGURATION ---
imports += ["REST_FRAMEWORK"]

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        # Cookie-primary, header-fallback JWT auth (CSRF enforced on cookie
        # transport only). See accounts/authentication.py.
        'accounts.authentication.CookieJWTAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        # By default, require authentication on all views
        'rest_framework.permissions.IsAuthenticated',
    ],
    # OpenAPI schema generator
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
    'DEFAULT_FILTER_BACKENDS': [
        'django_filters.rest_framework.DjangoFilterBackend',          # Enable query filtering
    ],
    'EXCEPTION_HANDLER': 'config.exception_handler.custom_exception_handler',
    'DEFAULT_THROTTLE_CLASSES': [
        'utils.throttles.DefaultAnonThrottle',
        'utils.throttles.DefaultUserThrottle',
    ],
    'DEFAULT_THROTTLE_RATES': {
        'default_anon': '60/min',
        'default_user': '120/min',
        'auth_login': '10/min',
        'auth_login_account': '5/hour',
        'auth_register': '5/hour',
        'auth_reset': '3/hour',
        'auth_set_password': '10/hour',
        'auth_refresh': '20/min',
        'auth_activation': '10/hour',
        'public_list': '120/min',
        'search': '60/min',
        'webhook': '200/min',
        'external_api': '300/min',
        'user_mutation': '30/min',
    },
}


# Make all these settings importable if someone does: from settings import *
__all__ = imports
