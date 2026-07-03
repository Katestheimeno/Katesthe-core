"""
Base settings entry point loaded by env-specific modules (local/production).
Path: config/django/base.py
"""

from config.settings import *
from config.logger import setup_django_logging

setup_django_logging()

ROOT_URLCONF = 'config.urls'

WSGI_APPLICATION = 'config.wsgi.application'

X_FRAME_OPTIONS = "DENY"
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = "strict-origin-when-cross-origin"

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]
