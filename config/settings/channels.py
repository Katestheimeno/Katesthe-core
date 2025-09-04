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
            "prefix": "channels",  # Prefix to avoid conflicts with other Redis data
            "expiry": 60,  # Messages expire after 60 seconds if not consumed
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
