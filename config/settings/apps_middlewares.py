"""
Application & Middleware Configuration

This file centralizes the definition of:
- Django’s built-in apps
- Third-party packages
- Project-specific apps
- Middleware stack

It also includes configuration for the Unfold admin package and 
optional development-only apps.
"""

# ------------------------------------------------------------
# Imports Collector
# ------------------------------------------------------------
# We collect all exported variables into `__all__` at the bottom.
imports = []


# ------------------------------------------------------------
# Unfold (Admin UI Enhancements)
# ------------------------------------------------------------
# Unfold provides a modernized Django admin interface.
# Each contrib submodule can be enabled/disabled as needed.
UNFOLD_APP = [
    "unfold",                      # must come before django.contrib.admin
    "unfold.contrib.filters",      # optional: advanced filters
    "unfold.contrib.forms",        # optional: custom form widgets
    "unfold.contrib.inlines",      # optional: inline enhancements
    "unfold.contrib.import_export",  # optional: requires django-import-export
    "unfold.contrib.guardian",     # optional: requires django-guardian
    "unfold.contrib.simple_history",  # optional: requires django-simple-history
    "unfold.contrib.location_field",  # optional: requires django-location-field
    "unfold.contrib.constance",    # optional: requires django-constance
]


# ------------------------------------------------------------
# Django Default Apps
# ------------------------------------------------------------
DJANGO_APPS = [
    *UNFOLD_APP,
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
]


# ------------------------------------------------------------
# Third-Party Packages
# ------------------------------------------------------------
# These are external Django/DRF-related dependencies.
THIRD_PARTY_PACKAGES = [
    "rest_framework",     # Django REST Framework for APIs
    # Developer utilities (shell_plus, graph_models, etc.)
    "django_extensions",
    "corsheaders",        # Handle CORS in APIs
    'drf_spectacular',  # Auto Documentation for the APIs
    'django_filters',  # Django filters
    'rest_framework_extensions',  # Models and fields tools
    'rest_framework_simplejwt',  # JWT Auth
    'djoser',  # Auth package
    'django_celery_beat',  # Celery Schedules
]


# ------------------------------------------------------------
# Project Apps
# ------------------------------------------------------------
# Internal apps developed as part of the project.
PROJECT_APPS = [
    'accounts',
    "utils",
]


# ------------------------------------------------------------
# Installed Apps (final composition)
# ------------------------------------------------------------
imports += ["INSTALLED_APPS"]

INSTALLED_APPS = [
    *DJANGO_APPS,
    *THIRD_PARTY_PACKAGES,
    *PROJECT_APPS,
]


# ------------------------------------------------------------
# Development-only Apps
# ------------------------------------------------------------
# These should only be enabled in a dev environment.
imports += ["DEV_APPS"]

DEV_APPS = [
    "rosetta",  # Translation management
    "silk",     # Profiling & performance analysis
]


# ------------------------------------------------------------
# Middleware Configuration
# ------------------------------------------------------------
# The order of middleware is important.
# Notes:
# - `CorsMiddleware` must appear *before* `CommonMiddleware`.
# - Security, session, CSRF, authentication, and message handling
#   are included by default.
imports += ["MIDDLEWARE"]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "corsheaders.middleware.CorsMiddleware",  # must come before CommonMiddleware
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]


# ------------------------------------------------------------
# Explicit Exports
# ------------------------------------------------------------
__all__ = imports
