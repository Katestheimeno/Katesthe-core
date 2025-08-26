"""
WSGI entry for Django.
Path: config/wsgi.py
"""

import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.django.local')

application = get_wsgi_application()
