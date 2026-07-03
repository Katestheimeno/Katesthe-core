"""
Tests for the WebSocket per-connection sliding-window rate limiter.
Path: utils/tests/test_ws_rate_limit.py
"""

from unittest.mock import patch

from django.conf import settings

from utils.websocket.rate_limit import MessageRateLimiter


class TestMessageRateLimiterWithinWindow:
    def test_first_fifteen_calls_are_not_throttled(self):
        limiter = MessageRateLimiter()

        results = [limiter.is_throttled() for _ in range(15)]

        assert results == [False] * 15

    def test_sixteenth_call_within_window_is_throttled(self):
        limiter = MessageRateLimiter()
        for _ in range(15):
            limiter.is_throttled()

        assert limiter.is_throttled() is True


class TestMessageRateLimiterAfterWindowElapses:
    def test_limiter_allows_messages_again_after_window_elapses(self):
        limiter = MessageRateLimiter(max_messages=1, window_seconds=1.0)
        with patch("utils.websocket.rate_limit.monotonic", return_value=0.0):
            assert limiter.is_throttled() is False
            assert limiter.is_throttled() is True

        with patch("utils.websocket.rate_limit.monotonic", return_value=2.0):
            assert limiter.is_throttled() is False


class TestCorsAllowHeaders:
    def test_x_token_delivery_header_is_allow_listed(self):
        assert "x-token-delivery" in settings.CORS_ALLOW_HEADERS
