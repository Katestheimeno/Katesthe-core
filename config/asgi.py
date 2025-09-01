"""
ASGI configuration for Django Channels (WebSocket + HTTP support).
Path: config/asgi.py
"""

from config.routing import websocket_urlpatterns
import os
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
from django.core.asgi import get_asgi_application
from django.urls import path

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.django.local')

# Initialize Django ASGI application early to ensure AppRegistry is populated
# before importing consumers or routing
django_asgi_app = get_asgi_application()

# Import your WebSocket routing after Django is initialized
# This prevents Django app loading issues

application = ProtocolTypeRouter({
    # Handle traditional HTTP requests
    "http": django_asgi_app,

    # Handle WebSocket connections
    "websocket": AuthMiddlewareStack(
        URLRouter(websocket_urlpatterns)
    ),
})
