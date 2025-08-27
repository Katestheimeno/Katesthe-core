"""
DRF and SimpleJWT configuration.
Path: config/settings/restframework.py
"""

from config.env import JWT_SECRET_KEY
from datetime import timedelta

# Keep track of which settings we’re exporting in __all__
imports = []

# --- JWT CONFIGURATION ---
imports += ["SIMPLE_JWT"]


SIMPLE_JWT = {
    # --------------------------
    # Token lifetimes
    # --------------------------
    # short-lived access token
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=60),
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
    # JWT signing / validation
    # --------------------------
    "ALGORITHM": "HS256",
    "SIGNING_KEY": JWT_SECRET_KEY,  # or a dedicated JWT_SECRET_KEY
    "VERIFYING_KEY": None,
    "AUDIENCE": None,                    # set if you issue tokens to multiple clients
    "ISSUER": None,                      # set if you want issuer validation

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
}

# --- DRF CONFIGURATION ---
imports += ["REST_FRAMEWORK"]

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        # Default DRF auth classes (BasicAuth disabled here)
        'rest_framework_simplejwt.authentication.JWTAuthentication',  # <-- JWT via SimpleJWT
        # <-- For browsable API / dev
        'rest_framework.authentication.SessionAuthentication',
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
}


# Make all these settings importable if someone does: from settings import *
__all__ = imports
