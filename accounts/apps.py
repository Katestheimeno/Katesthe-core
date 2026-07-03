"""
AppConfig for the accounts application.
Path: accounts/apps.py
"""

from django.apps import AppConfig


class AccountsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'accounts'

    def ready(self):
        # Register the drf-spectacular auth extension at app-ready time (after settings are fully configured).
        import config.spectacular_auth  # noqa: F401
