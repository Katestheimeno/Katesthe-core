"""
Modular settings aggregator. Imports per-concern modules into Django settings.
Path: config/settings/__init__.py
"""

from config.settings.config import settings

# Import all settings from the centralized config
DEBUG = settings.DEBUG
SECRET_KEY = settings.SECRET_KEY
JWT_SECRET_KEY = settings.JWT_SECRET_KEY
ALLOWED_HOSTS = [host.strip() for host in settings.ALLOWED_HOSTS.split(',') if host.strip()]
DATABASE_URL = settings.database.DATABASE_URL
REDIS_URL = settings.REDIS_URL
CELERY_BROKER_URL = settings.CELERY_BROKER_URL
WEB_PORT = settings.WEB_PORT

# Project branding and configuration
PROJECT_NAME = settings.PROJECT_NAME
PROJECT_DESCRIPTION = settings.PROJECT_DESCRIPTION
PROJECT_VERSION = settings.PROJECT_VERSION

# Contact information
CONTACT_NAME = settings.CONTACT_NAME
CONTACT_EMAIL = settings.CONTACT_EMAIL
CONTACT_URL = settings.CONTACT_URL

# Email configuration
EMAIL_HOST = settings.email.HOST
EMAIL_PORT = settings.email.PORT
EMAIL_USE_TLS = settings.email.USE_TLS
EMAIL_HOST_USER = settings.email.HOST_USER
EMAIL_HOST_PASSWORD = settings.email.HOST_PASSWORD
EMAIL_FRONTEND_DOMAIN = settings.email.FRONTEND_DOMAIN

# Theme colors
THEME_PRIMARY_COLOR = settings.THEME_PRIMARY_COLOR
THEME_ACCENT_COLOR = settings.THEME_ACCENT_COLOR

# Import other settings modules
from config.settings.apps_middlewares import *
from config.settings.paths import *
from config.settings.auth import *
from config.settings.lang_time import *
from config.settings.database import *
from config.settings.unfold import *
from config.settings.corsheaders import *
from config.settings.restframework import *
from config.settings.djoser import *
from config.settings.spectacular import *
from config.settings.celery import *
from config.settings.channels import *
