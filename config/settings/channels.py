"""
Django Channels configuration for WebSocket support.
Path: config/settings/channels.py
"""

from config.settings.config import settings

# Keep track of which settings we're exporting
imports = []

# -----------------------------------------------------------------------------
# CHANNEL LAYERS CONFIGURATION
# -----------------------------------------------------------------------------
# Uses Redis as the channel layer backend (same Redis instance as Celery)
imports += ["CHANNEL_LAYERS"]

CHANNEL_LAYERS = {
    'default': {
        'BACKEND': 'channels_redis.core.RedisChannelLayer',
        'CONFIG': {
            "hosts": [settings.REDIS_URL],
            "prefix": "channels",
            "expiry": 120,
            "capacity": 1500,
            "group_expiry": 86400,
        },
    },
}

# -----------------------------------------------------------------------------
# ASGI APPLICATION
# -----------------------------------------------------------------------------
# Point Django to the ASGI application
imports += ["ASGI_APPLICATION"]
ASGI_APPLICATION = 'config.asgi.application'

# -----------------------------------------------------------------------------
# EXPORT SETTINGS
# -----------------------------------------------------------------------------
__all__ = imports
