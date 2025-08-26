"""
Local development settings entry.
Path: config/django/local.py
Inherit from base and enable dev-only apps/middleware when DEBUG is True.
"""
from config.django.base import *


if DEBUG:
    INSTALLED_APPS += DEV_APPS
    MIDDLEWARE += ["silk.middleware.SilkyMiddleware"]
