"""
AppConfig for the notifications application.
Path: notifications/apps.py
"""

from django.apps import AppConfig


class NotificationsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "notifications"
