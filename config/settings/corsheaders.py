
"""
CORS (Cross-Origin Resource Sharing) configuration.
Path: config/settings/corsheaders.py

Defines allowed headers, origins, and credentials for cross-origin API calls
via django-cors-headers.
"""

from urllib.parse import urlparse

from corsheaders.defaults import default_headers
from config.settings.config import settings

# List of symbols to be exported when doing `from settings.cors import *`
# We build this dynamically as we define variables.
imports = []


def _is_loopback_origin(origin: str) -> bool:
    """Return True when `origin`'s host is localhost/127.0.0.1 (or a *.localhost
    subdomain). Used to strip dev-only origins from production CORS config."""
    host = (urlparse(origin).hostname or "").lower()
    return host in {"localhost", "127.0.0.1"} or host.endswith(".localhost")

# ---------------------------------------------------------------------
# Allowed HTTP headers
# ---------------------------------------------------------------------
# Extend the default CORS headers to allow extra headers that clients
# might send when making requests to the API.
# 
# - 'authorization': required for sending JWT tokens or Bearer tokens.
# - 'content-type':   (defines
#                    the media type of the request (JSON, form-data, etc).
# ---------------------------------------------------------------------
imports += ["CORS_ALLOW_HEADERS"]
CORS_ALLOW_HEADERS = list(default_headers) + [
    "authorization",
    "content-type",
]

# ---------------------------------------------------------------------
# Credentials support
# ---------------------------------------------------------------------
# Allow cookies, Authorization headers, and TLS client certificates
# to be included in cross-origin requests.
#
# This is required if:
# - You are using JWTs or session authentication with cookies
# - You want the frontend to send credentials along with requests
# ---------------------------------------------------------------------
imports += ["CORS_ALLOW_CREDENTIALS"]
CORS_ALLOW_CREDENTIALS = True

# ---------------------------------------------------------------------
# Allowed origins (domains / ports)
# ---------------------------------------------------------------------
# Define which domains are allowed to make cross-origin requests.
# In development, this typically includes localhost and custom dev ports
# (React/Vue dev servers, Flutter web, Dockerized apps, etc).
#
# In production, you must replace this list with your actual frontend URLs.
# ---------------------------------------------------------------------
imports += ["CORS_ALLOWED_ORIGINS"]
CORS_ALLOWED_ORIGINS = [
    "http://localhost:8080",   # e.g. Vue / React dev server
    f"http://127.0.0.1:{settings.WEB_PORT}",   # Django dev server
]

# Production must never accept loopback origins — they only make sense for local
# development. Gate on the resolved pydantic DJANGO_DEBUG flag (NOT the pydantic
# `settings.DEBUG`-style attribute); dev behavior above is left untouched.
if not settings.DJANGO_DEBUG:
    CORS_ALLOWED_ORIGINS = [
        origin for origin in CORS_ALLOWED_ORIGINS if not _is_loopback_origin(origin)
    ]

# Expose only the explicitly defined symbols
__all__ = imports
