"""
This file configures paths for serving static and media files.

MEDIA_* is used for user-uploaded content.
STATIC_* is used for serving CSS, JavaScript, and other static assets.

Notes:
- MEDIA_ROOT: Local directory where uploaded media will be stored.
- STATICFILES_DIRS: Extra directories where static files will be collected from (during development).
- STATIC_ROOT: Directory where all static files are collected to (used by collectstatic in production).

Remember to run `python manage.py collectstatic` before deploying.
"""

from pathlib import Path
from config.env import BASE_DIR

imports = []
# media directory configuration
imports += ["MEDIA_URL"]
MEDIA_URL = "/media/"
imports += ["MEDIA_ROOT"]
MEDIA_ROOT = BASE_DIR / "media"

# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/5.1/howto/static-files/

imports += ["STATIC_URL"]
STATIC_URL = "/static/"
imports += ["STATIC_ROOT"]
STATIC_ROOT = BASE_DIR / "staticfiles"
imports += ["STATICFILES_DIRS"]
STATICFILES_DIRS = [
    BASE_DIR / "static",
]

imports += ["LOCALE_PATHS"]
LOCALE_PATHS = [
    BASE_DIR / "locale",
]

imports += ["SQLITE_DATABASE_PATH"]
SQLITE_DATABASE_PATH = BASE_DIR / 'database'

__all__ = imports

