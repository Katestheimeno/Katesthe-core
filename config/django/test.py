"""
Test-specific Django settings.
Path: config/django/test.py
"""

from .base import *

# Use SQLite for testing
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': ':memory:',  # Use in-memory database for faster tests
    }
}

# Disable logging during tests
LOGGING = {
    'version': 1,
    'disable_existing_loggers': True,
    'handlers': {
        'null': {
            'class': 'logging.NullHandler',
        },
    },
    'root': {
        'handlers': ['null'],
    },
}

# Use faster password hasher for tests
PASSWORD_HASHERS = [
    'django.contrib.auth.hashers.MD5PasswordHasher',
]

# Disable debug toolbar and other development tools
DEBUG = False
TEMPLATES[0]['OPTIONS']['debug'] = False

# Use console email backend for tests
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

# Disable Celery tasks during tests
CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True

# Use simple cache for tests
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
    }
}

# Disable Silk for tests
SILK_ENABLED = False
SILK_PYTHON_PROFILER = False

# Remove Silk from middleware for tests
MIDDLEWARE = [mw for mw in MIDDLEWARE if 'silk' not in mw.lower()]

# Remove Silk from INSTALLED_APPS for tests
INSTALLED_APPS = [app for app in INSTALLED_APPS if 'silk' not in app.lower()]

# Use test-specific URL configuration
ROOT_URLCONF = 'config.urls_test'
