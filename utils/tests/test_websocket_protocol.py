"""
Tests for utils/websocket/protocol.py — generic WebSocket protocol helpers.
Path: utils/tests/test_websocket_protocol.py
"""

import pytest
from asgiref.sync import async_to_sync
from django.core.cache import cache
from rest_framework_simplejwt.tokens import AccessToken

from accounts.tests.factories._user import InactiveUserFactory, UserFactory
from errors.catalog import AUTH__TOKEN_INVALID
from utils.websocket.protocol import (
    check_idempotency,
    handle_auth_rotate,
    send_ack,
    send_nack,
)


@pytest.fixture(autouse=True)
def _clear_cache():
    """Ensure the LocMemCache is isolated between tests."""
    cache.clear()
    yield
    cache.clear()


class _FakeConsumer:
    """Minimal consumer double capturing send_json() calls."""

    def __init__(self, user=None):
        self.scope = {"user": user}
        self.user = user
        self.sent: list[dict] = []

    async def send_json(self, payload):
        self.sent.append(payload)


class TestSendAck:
    def test_omits_data_key_when_data_is_none(self):
        consumer = _FakeConsumer()

        async_to_sync(send_ack)(consumer, "msg-1")

        assert consumer.sent == [{"type": "ack", "message_id": "msg-1"}]

    def test_includes_data_key_when_data_is_provided(self):
        consumer = _FakeConsumer()

        async_to_sync(send_ack)(consumer, "msg-1", data={"foo": "bar"})

        assert consumer.sent == [
            {"type": "ack", "message_id": "msg-1", "data": {"foo": "bar"}}
        ]


class TestSendNack:
    def test_omits_detail_key_when_detail_is_none(self):
        consumer = _FakeConsumer()

        async_to_sync(send_nack)(consumer, "msg-1", "VALIDATION__INVALID_VALUE")

        assert consumer.sent == [
            {
                "type": "nack",
                "message_id": "msg-1",
                "code": "VALIDATION__INVALID_VALUE",
            }
        ]

    def test_includes_detail_key_when_detail_is_provided(self):
        consumer = _FakeConsumer()

        async_to_sync(send_nack)(
            consumer, "msg-1", "VALIDATION__INVALID_VALUE", detail="bad field"
        )

        assert consumer.sent == [
            {
                "type": "nack",
                "message_id": "msg-1",
                "code": "VALIDATION__INVALID_VALUE",
                "detail": "bad field",
            }
        ]


class TestCheckIdempotency:
    def test_fresh_message_id_returns_false(self):
        result = async_to_sync(check_idempotency)("chan-1", "abc-123")

        assert result is False

    def test_immediate_second_call_with_same_id_returns_true(self):
        async_to_sync(check_idempotency)("chan-1", "abc-123")

        result = async_to_sync(check_idempotency)("chan-1", "abc-123")

        assert result is True

    def test_same_message_id_on_different_channel_is_not_a_duplicate(self):
        async_to_sync(check_idempotency)("chan-1", "abc-123")

        result = async_to_sync(check_idempotency)("chan-2", "abc-123")

        assert result is False

    @pytest.mark.parametrize(
        "invalid_id",
        [
            "",
            "a" * 129,
            "bad id with spaces",
            "bad/slash",
            None,
            123,
        ],
    )
    def test_invalid_message_id_returns_true(self, invalid_id):
        result = async_to_sync(check_idempotency)("chan-1", invalid_id)

        assert result is True


@pytest.mark.django_db
class TestHandleAuthRotate:
    def test_valid_token_swaps_scope_user_and_sends_auth_rotated(self):
        old_user = UserFactory()
        new_user = UserFactory()
        token = str(AccessToken.for_user(new_user))
        consumer = _FakeConsumer(user=old_user)

        async_to_sync(handle_auth_rotate)(consumer, {"token": token})

        assert consumer.scope["user"] == new_user
        assert consumer.user == new_user
        assert consumer.sent == [
            {"type": "auth_rotated", "user_id": str(new_user.pk)}
        ]

    def test_invalid_token_sends_auth_rotate_failed_and_leaves_scope_untouched(self):
        old_user = UserFactory()
        consumer = _FakeConsumer(user=old_user)

        async_to_sync(handle_auth_rotate)(consumer, {"token": "garbage.not.a.token"})

        assert consumer.scope["user"] == old_user
        assert consumer.user == old_user
        assert consumer.sent == [
            {"type": "auth_rotate_failed", "code": AUTH__TOKEN_INVALID}
        ]

    def test_missing_token_sends_auth_rotate_failed(self):
        consumer = _FakeConsumer()

        async_to_sync(handle_auth_rotate)(consumer, {})

        assert consumer.sent == [
            {"type": "auth_rotate_failed", "code": AUTH__TOKEN_INVALID}
        ]

    def test_inactive_user_token_sends_auth_rotate_failed(self):
        inactive_user = InactiveUserFactory()
        token = str(AccessToken.for_user(inactive_user))
        consumer = _FakeConsumer()

        async_to_sync(handle_auth_rotate)(consumer, {"token": token})

        assert consumer.sent == [
            {"type": "auth_rotate_failed", "code": AUTH__TOKEN_INVALID}
        ]
