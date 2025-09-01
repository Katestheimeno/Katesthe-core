"""
WebSocket URL routing configuration.
Path: config/routing.py
"""

from django.urls import re_path
from utils.consumers import ExampleConsumer

# Define your WebSocket URL patterns here
websocket_urlpatterns = [
    # Example WebSocket route
    re_path(r'^ws/test/$', ExampleConsumer.as_asgi()),

    # Add more WebSocket routes as needed:
    # re_path(r'ws/chat/(?P<room_name>\w+)/$', ChatConsumer.as_asgi()),
    # re_path(r'ws/notifications/$', NotificationConsumer.as_asgi()),
]
