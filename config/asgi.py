"""
ASGI entry for Django.
Path: config/asgi.py
"""

import os

from django.core.asgi import get_asgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.django.local')

application = get_asgi_application()
