"""
This file configures paths for serving static and media files in Django.

MEDIA_* → Used for user-uploaded content (e.g., profile pictures, documents).
STATIC_* → Used for serving CSS, JavaScript, and other static assets.

Key Notes:
- MEDIA_ROOT: Local directory where uploaded media files will be stored.
- STATICFILES_DIRS: Extra directories where static files will be collected from (useful during development).
- STATIC_ROOT: Directory where all static files are collected into when running `collectstatic` (mainly for production).
- LOCALE_PATHS: Directories where Django will look for translation files.
- SQLITE_DATABASE_PATH: Centralized location for the SQLite database file.

Remember:
- In production, always run `python manage.py collectstatic` so STATIC_ROOT is populated.
- MEDIA files should be served via a dedicated storage service (e.g., S3, GCP, or mounted volume), not Django directly.
"""

from pathlib import Path
from config.env import BASE_DIR

imports = []

# ---------------------------
# Media configuration
# ---------------------------
imports += ["MEDIA_URL"]
MEDIA_URL = "/media/"  # Public URL to access uploaded media

imports += ["MEDIA_ROOT"]
MEDIA_ROOT = BASE_DIR / "media"  # Local directory to store uploaded media


# ---------------------------
# Static files configuration
# ---------------------------
# https://docs.djangoproject.com/en/5.1/howto/static-files/

imports += ["STATIC_URL"]
STATIC_URL = "/static/"  # Public URL to access static files

imports += ["STATIC_ROOT"]
STATIC_ROOT = BASE_DIR / "staticfiles"
# Directory where Django will copy all static files when running `collectstatic`

imports += ["STATICFILES_DIRS"]
STATICFILES_DIRS = [
    BASE_DIR / "static",  # Additional static files during development
]


# ---------------------------
# Localization
# ---------------------------
imports += ["LOCALE_PATHS"]
LOCALE_PATHS = [
    BASE_DIR / "locale",  # Directory for Django translation files
]


# ---------------------------
# Database path
# ---------------------------
imports += ["SQLITE_DATABASE_PATH"]
SQLITE_DATABASE_PATH = BASE_DIR / "database"
# Directory to store SQLite database file(s)


# ---------------------------
# Exported settings
# ---------------------------
__all__ = imports
