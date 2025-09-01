"""
WebSocket consumers for handling real-time connections.
Path: utils/consumers.py
"""

import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async


class ExampleConsumer(AsyncWebsocketConsumer):
    """
    Example WebSocket consumer demonstrating basic functionality.

    This consumer shows how to:
    - Handle connection/disconnection
    - Send/receive messages
    - Access authenticated user
    - Join/leave channel groups
    """

    async def connect(self):
        """Called when WebSocket connection is opened."""
        # Get user from scope (set by AuthMiddlewareStack)
        self.user = self.scope["user"]

        # Join a group (optional - useful for broadcasting)
        self.group_name = f"user_{self.user.id}"
        await self.channel_layer.group_add(
            self.group_name,
            self.channel_name
        )

        # Accept the WebSocket connection
        await self.accept()

        # Send welcome message
        await self.send(text_data=json.dumps({
            'type': 'connection_established',
            'message': f'Connected as {self.user.username}'
        }))

    async def disconnect(self, close_code):
        """Called when WebSocket connection is closed."""
        # Leave the group
        if hasattr(self, 'group_name'):
            await self.channel_layer.group_discard(
                self.group_name,
                self.channel_name
            )

    async def receive(self, text_data):
        """Called when we receive a message from WebSocket."""
        try:
            data = json.loads(text_data)
            message_type = data.get('type', 'unknown')

            if message_type == 'ping':
                await self.send(text_data=json.dumps({
                    'type': 'pong',
                    'message': 'Connection is alive'
                }))

            elif message_type == 'echo':
                # Echo the message back
                await self.send(text_data=json.dumps({
                    'type': 'echo_response',
                    'original_message': data.get('message', ''),
                    'user': self.user.username
                }))

            else:
                await self.send(text_data=json.dumps({
                    'type': 'error',
                    'message': f'Unknown message type: {message_type}'
                }))

        except json.JSONDecodeError:
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': 'Invalid JSON format'
            }))
        except Exception as e:
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': f'Server error: {str(e)}'
            }))

    # Group message handlers (for broadcasting)
    async def broadcast_message(self, event):
        """Handle broadcast messages sent to the group."""
        await self.send(text_data=json.dumps({
            'type': 'broadcast',
            'message': event['message'],
            'sender': event.get('sender', 'system')
        }))


class BaseConsumer(AsyncWebsocketConsumer):
    """
    Base consumer class with common functionality.

    Extend this class for your specific consumers to get:
    - User authentication
    - Error handling
    - Basic group management
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = None
        self.group_name = None

    async def connect(self):
        """Base connection handler - override in subclasses."""
        self.user = self.scope["user"]

        # Optional: require authentication
        if self.require_auth and isinstance(self.user, AnonymousUser):
            await self.close()
            return

        await self.accept()

    async def disconnect(self, close_code):
        """Base disconnection handler."""
        if self.group_name:
            await self.channel_layer.group_discard(
                self.group_name,
                self.channel_name
            )

    async def send_error(self, message):
        """Helper method to send error messages."""
        await self.send(text_data=json.dumps({
            'type': 'error',
            'message': message
        }))

    async def send_success(self, message, data=None):
        """Helper method to send success messages."""
        payload = {
            'type': 'success',
            'message': message
        }
        if data:
            payload['data'] = data

        await self.send(text_data=json.dumps(payload))

    @property
    def require_auth(self):
        """Override this to require authentication (default: False)."""
        return False
