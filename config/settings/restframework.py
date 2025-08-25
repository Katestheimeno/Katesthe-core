from config.env import JWT_SECRET_KEY
from datetime import timedelta

# Keep track of which settings we’re exporting in __all__
imports = []

# --- JWT CONFIGURATION ---
imports += ["SIMPLE_JWT"]

SIMPLE_JWT = {
    # Access token lifetime (short-lived, to limit damage if leaked)
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=60),
    # Refresh token lifetime (longer-lived, used to get new access tokens)
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),
    # Whether a new refresh token is issued on refresh (stateless if False)
    "ROTATE_REFRESH_TOKENS": False,
    # If rotation is enabled, blacklist old refresh tokens
    "BLACKLIST_AFTER_ROTATION": False,
    # Update last_login field when a user logs in via JWT
    "UPDATE_LAST_LOGIN": True,
    # Secret key used for signing the JWTs (keep it out of VCS!)
    "SIGNING_KEY": JWT_SECRET_KEY,
    # Algorithm for signing tokens
    "ALGORITHM": "HS256",
}

# --- DRF CONFIGURATION ---
imports += ["REST_FRAMEWORK"]

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        # Default DRF auth classes (BasicAuth disabled here)
        'rest_framework_simplejwt.authentication.JWTAuthentication',  # <-- JWT via SimpleJWT
        'rest_framework.authentication.SessionAuthentication',        # <-- For browsable API / dev
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        # By default, require authentication on all views
        'rest_framework.permissions.IsAuthenticated',
    ],
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',  # OpenAPI schema generator
    'DEFAULT_FILTER_BACKENDS': [
        'django_filters.rest_framework.DjangoFilterBackend',          # Enable query filtering
    ],
}

# --- OPENAPI / API DOCS CONFIGURATION ---
imports += ["SPECTACULAR_SETTINGS"]

SPECTACULAR_SETTINGS = {
    'TITLE': 'DRF-Starter API',
    'DESCRIPTION': 'serves as a django rest_framework starting point',
    'VERSION': '1.0.0',
    'SERVE_INCLUDE_SCHEMA': False,  # Don’t include schema endpoint in docs
}

# --- DJ-REST-AUTH CONFIGURATION ---
imports += ["REST_USE_JWT"]

# Tell dj-rest-auth to use SimpleJWT instead of default TokenAuthentication
REST_USE_JWT = True

# Make all these settings importable if someone does: from settings import *
__all__ = imports

