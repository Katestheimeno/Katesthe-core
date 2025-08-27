"""
Celery application instance used by worker/beat/flower.
Path: config/celery.py
"""

from celery import Celery
from django.conf import settings
import os

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.django.local")
app = Celery("drf_starter")

# Using a string here means the worker doesn't have to serialize
# the configuration object to child processes.
app.config_from_object('django.conf:settings', namespace='CELERY')

# Load task modules from all registered Django apps.
app.autodiscover_tasks()

# Celery Beat Schedule (for periodic tasks)
app.config_from_object('django.conf:settings', namespace='CELERY')

app.conf.timezone = 'UTC'
