# In this file we override the base django settings
# if needed for the development environment
from config.django.base import *


if DEBUG:
    INSTALLED_APPS += DEV_APPS
    MIDDLEWARE += ["silk.middleware.SilkyMiddleware"]
