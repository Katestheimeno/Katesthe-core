"""
Environment variables loader using django-environ.
Path: config/env.py

Reads `.env` from project root and exposes commonly used settings variables.
Usage: `from config.env import env, BASE_DIR`
"""
from pathlib import Path
import environ

# Exportable symbols list for `from env import *` usage
imports = []

# Initialize the environment reader
imports += ["env"]
env = environ.Env()

# Define the base directory of the project (2 levels up from this file)
imports += ["BASE_DIR"]
BASE_DIR = Path(__file__).resolve().parent.parent

# Load environment variables from a .env file located at the project root
env_file = BASE_DIR / ".env"
env.read_env(env_file)


imports += ["DEBUG"]
DEBUG = env.bool('DJANGO_DEBUG', default=True)

imports += ["SECRET_KEY"]
SECRET_KEY = env("SECRET_KEY")

imports += ["JWT_SECRET_KEY"]
JWT_SECRET_KEY = env("JWT_SECRET_KEY")

imports += ["ALLOWED_HOSTS"]
ALLOWED_HOSTS = env.list("ALLOWED_HOSTS", default=['*'])

# ------------------------------------------------------------
# Database URL construction
# ------------------------------------------------------------
POSTGRES_USER = env("POSTGRES_USER", default="postgres")
POSTGRES_PASSWORD = env("POSTGRES_PASSWORD", default="postgres")
POSTGRES_HOST = env("POSTGRES_HOST", default="db")
POSTGRES_PORT = env("POSTGRES_PORT", default=5432)
POSTGRES_DB = env("POSTGRES_DB", default="drf_starter")

imports += ["DATABASE_URL"]
DATABASE_URL = f"postgresql://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{
    POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}"

imports += ["REDIS_URL"]
REDIS_URL = env('REDIS_URL', default='redis://localhost:6379/0')

imports += ["CELERY_BROKER_URL"]
CELERY_BROKER_URL = REDIS_URL

imports += ["WEB_PORT"]
WEB_PORT = env.int("WEB_PORT", default=8000)

# Project branding and configuration
imports += ["PROJECT_NAME"]
PROJECT_NAME = env("PROJECT_NAME", default="Katesthe-core")

imports += ["PROJECT_DESCRIPTION"]
PROJECT_DESCRIPTION = env("PROJECT_DESCRIPTION", default="A Django REST Framework starter project with ready-to-use authentication, custom user management, and modular app structure.")

imports += ["PROJECT_VERSION"]
PROJECT_VERSION = env("PROJECT_VERSION", default="1.0.0")

# Contact information
imports += ["CONTACT_NAME"]
CONTACT_NAME = env("CONTACT_NAME", default="Katesthe-core Dev Team")

imports += ["CONTACT_EMAIL"]
CONTACT_EMAIL = env("CONTACT_EMAIL", default="support@katesthe-core.com")

imports += ["CONTACT_URL"]
CONTACT_URL = env("CONTACT_URL", default="https://github.com/katesthe-core")

# Email configuration
imports += ["EMAIL_HOST"]
EMAIL_HOST = env("EMAIL_HOST", default="localhost")

imports += ["EMAIL_PORT"]
EMAIL_PORT = env.int("EMAIL_PORT", default=1025)

imports += ["EMAIL_USE_TLS"]
EMAIL_USE_TLS = env.bool("EMAIL_USE_TLS", default=False)

imports += ["EMAIL_HOST_USER"]
EMAIL_HOST_USER = env("EMAIL_HOST_USER", default="")

imports += ["EMAIL_HOST_PASSWORD"]
EMAIL_HOST_PASSWORD = env("EMAIL_HOST_PASSWORD", default="")

imports += ["EMAIL_FRONTEND_DOMAIN"]
EMAIL_FRONTEND_DOMAIN = env("EMAIL_FRONTEND_DOMAIN", default="")

# Theme colors (primary color in hex format)
imports += ["THEME_PRIMARY_COLOR"]
THEME_PRIMARY_COLOR = env("THEME_PRIMARY_COLOR", default="#6a0dad")

imports += ["THEME_ACCENT_COLOR"]
THEME_ACCENT_COLOR = env("THEME_ACCENT_COLOR", default="#4b0082")

__all__ = imports
