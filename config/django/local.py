"""
Local development settings entry.
Path: config/django/local.py
Inherit from base and enable dev-only apps/middleware when DEBUG is True.
"""
from config.django.base import *


if DEBUG:
    INSTALLED_APPS += DEV_APPS
    MIDDLEWARE += ["silk.middleware.SilkyMiddleware"]

    from config.settings.config import settings as _cfg
    if getattr(_cfg, "REQUEST_RESPONSE_DEBUG", False):
        MIDDLEWARE += ["config.middleware.debug_payload.DebugPayloadMiddleware"]
