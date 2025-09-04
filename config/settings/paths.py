"""
Static, media, locale, and SQLite paths for the project.
Path: config/settings/paths.py
"""

from pathlib import Path
from config.settings.config import settings
BASE_DIR = Path(__file__).resolve().parent.parent.parent

imports = ["BASE_DIR"]

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
