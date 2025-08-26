
"""
CORS (Cross-Origin Resource Sharing) configuration.
Path: config/settings/corsheaders.py

Defines allowed headers, origins, and credentials for cross-origin API calls
via django-cors-headers.
"""

from corsheaders.defaults import default_headers

# List of symbols to be exported when doing `from settings.cors import *`
# We build this dynamically as we define variables.
imports = []

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
    "http://127.0.0.1:8000",   # Django dev server
]

# Expose only the explicitly defined symbols
__all__ = imports
