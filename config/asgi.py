"""
ASGI configuration for Django Channels (WebSocket + HTTP support).
Path: config/asgi.py
"""

from config.routing import websocket_urlpatterns
import os
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
from channels.security.websocket import AllowedHostsOriginValidator
from django.core.asgi import get_asgi_application
from django.urls import path

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.django.local')

# Initialize Django ASGI application early to ensure AppRegistry is populated
# before importing consumers or routing
django_asgi_app = get_asgi_application()

# JWTAuthMiddleware pulls in rest_framework_simplejwt -> django.contrib.auth
# models, so it must be imported after get_asgi_application() has populated
# the AppRegistry (importing it at module top raises AppRegistryNotReady).
from utils.middleware.jwt_websocket_auth import JWTAuthMiddleware  # noqa: E402

application = ProtocolTypeRouter({
    # Handle traditional HTTP requests
    "http": django_asgi_app,

    # Handle WebSocket connections.
    # AllowedHostsOriginValidator rejects cross-origin handshakes; inside it,
    # JWTAuthMiddleware authenticates via subprotocol/cookie JWT and falls
    # back to AuthMiddlewareStack's session auth when no token is presented.
    "websocket": AllowedHostsOriginValidator(
        AuthMiddlewareStack(JWTAuthMiddleware(URLRouter(websocket_urlpatterns)))
    ),
})
