"""
WebSocket per-connection message rate limiter.
Path: utils/websocket/rate_limit.py

Usage in any AsyncWebsocketConsumer / AsyncJsonWebsocketConsumer:

    from utils.websocket.rate_limit import MessageRateLimiter

    class MyConsumer(AsyncJsonWebsocketConsumer):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self._rate_limiter = MessageRateLimiter()

        async def receive(self, text_data):
            if self._rate_limiter.is_throttled():
                await self.send_json({"type": "error", "code": "RATE_LIMIT__EXCEEDED"})
                return
            ...
"""
from collections import deque
from time import monotonic


class MessageRateLimiter:
    """Sliding-window rate limiter (per-connection, no shared state)."""

    __slots__ = ("_max_messages", "_window_seconds", "_timestamps")

    def __init__(self, max_messages: int = 15, window_seconds: float = 1.0):
        self._max_messages = max_messages
        self._window_seconds = window_seconds
        self._timestamps: deque[float] = deque(maxlen=max_messages)

    def is_throttled(self) -> bool:
        now = monotonic()
        # Evict timestamps outside the window
        while self._timestamps and now - self._timestamps[0] > self._window_seconds:
            self._timestamps.popleft()
        if len(self._timestamps) >= self._max_messages:
            return True
        self._timestamps.append(now)
        return False
