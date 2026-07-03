"""
Shared WebSocket protocol utilities.
Path: utils/websocket/protocol.py

Standalone async functions that any Django Channels consumer can call for
common protocol operations: auth rotation, ACK/NACK responses, and
idempotency checks.

No base class or mixin -- each function takes the consumer instance as its
first argument and calls consumer.send_json() to respond. Generic only --
no domain-specific handlers live here (see plan "What NOT to Do" #17).
"""

import re

from asgiref.sync import sync_to_async
from django.core.cache import cache

from config.logger import logger
from errors.catalog import AUTH__TOKEN_INVALID

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

IDEMPOTENCY_TTL = 300  # 5 minutes

# message_id: alphanumeric + hyphens, max 128 chars
_MESSAGE_ID_RE = re.compile(r"^[a-zA-Z0-9\-]{1,128}$")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _is_valid_message_id(message_id: object) -> bool:
    """Validate that message_id is a string of 1-128 alphanumeric/hyphen chars."""
    if not isinstance(message_id, str):
        return False
    return bool(_MESSAGE_ID_RE.match(message_id))


# ---------------------------------------------------------------------------
# 1. handle_auth_rotate
# ---------------------------------------------------------------------------


async def handle_auth_rotate(consumer, data: dict) -> None:
    """
    Validate a new JWT and hot-swap the authenticated user on the connection.

    Client sends:  {"type": "auth_rotate", "token": "<jwt>"}
    Server replies: {"type": "auth_rotated", "user_id": "<id>"}
    On failure:     {"type": "auth_rotate_failed", "code": "AUTH__TOKEN_INVALID"}

    Reuses the existing get_user_from_token() from jwt_websocket_auth.py which
    handles token decode, expiry check, user lookup, and inactive-user rejection.
    A missing token is treated the same as an invalid one -- there is no
    dedicated "token missing" code in the catalog.
    """
    # Lazy import to avoid circular imports at module level
    from utils.middleware.jwt_websocket_auth import get_user_from_token

    token = data.get("token")
    user = await get_user_from_token(token) if token else None

    if user is None or user.is_anonymous:
        await consumer.send_json(
            {"type": "auth_rotate_failed", "code": AUTH__TOKEN_INVALID}
        )
        return

    consumer.scope["user"] = user
    consumer.user = user
    await consumer.send_json(
        {
            "type": "auth_rotated",
            "user_id": str(user.pk),
        }
    )
    logger.bind(user_id=str(user.pk)).info("ws.auth_rotate.success")


# ---------------------------------------------------------------------------
# 2. send_ack
# ---------------------------------------------------------------------------


async def send_ack(consumer, message_id: str, data: dict | None = None) -> None:
    """
    Send an ACK response correlated to message_id.

    Payload: {"type": "ack", "message_id": "<id>", "data": {...}}
    The ``data`` key is omitted when None.
    """
    payload: dict = {"type": "ack", "message_id": message_id}
    if data is not None:
        payload["data"] = data
    await consumer.send_json(payload)


# ---------------------------------------------------------------------------
# 3. send_nack
# ---------------------------------------------------------------------------


async def send_nack(
    consumer, message_id: str, code: str, detail: str | None = None
) -> None:
    """
    Send a NACK (negative acknowledgement) correlated to message_id.

    Payload: {"type": "nack", "message_id": "<id>", "code": "<CODE>", "detail": "..."}
    The ``detail`` key is omitted when None.
    """
    payload: dict = {"type": "nack", "message_id": message_id, "code": code}
    if detail is not None:
        payload["detail"] = detail
    await consumer.send_json(payload)


# ---------------------------------------------------------------------------
# 4. check_idempotency
# ---------------------------------------------------------------------------


async def check_idempotency(channel_name: str, message_id: str) -> bool:
    """
    Redis-backed duplicate detection for WebSocket messages.

    Returns True  if message_id is a duplicate (already processed) -- caller
                  should skip processing.
    Returns False if message_id is new -- and atomically marks it as seen
                  with a 5 minute TTL.

    Invalid message_ids (wrong type, too long, bad characters) return True
    so the caller safely no-ops rather than processing a malformed request.

    Uses django.core.cache (Redis-backed in production) with cache.add() for
    atomic set-if-not-exists (SETNX) semantics.
    """
    if not _is_valid_message_id(message_id):
        logger.bind(
            channel_name=channel_name,
            message_id=repr(message_id),
        ).warning("ws.idempotency.invalid_message_id")
        return True  # Treat invalid IDs as "already processed" to safely no-op

    key = f"ws:msgid:{channel_name}:{message_id}"

    # cache.add() returns True if the key was set (new), False if it already
    # existed (duplicate). This is atomic in Redis (SETNX semantics).
    was_set = await sync_to_async(cache.add)(key, "1", IDEMPOTENCY_TTL)

    return not was_set  # True = duplicate (key already existed)
