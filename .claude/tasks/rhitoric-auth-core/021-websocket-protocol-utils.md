# 021 — WebSocket protocol utilities (5.2)

**Status:** [PENDING]
**Phase:** 5
**Group:** ws
**Risk:** MEDIUM
**Effort:** 40m
**Dependencies:** 020 (uses `get_user_from_token`) — soft; may be developed in parallel but tests import from 020's module

## Goal
Shared async protocol helpers usable by any consumer: auth rotation, ACK/NACK, and idempotency.

## Context
Generic consumer plumbing (no domain handlers — plan "What NOT to Do" #17). `handle_auth_rotate` reuses `get_user_from_token` from the WS middleware (020). Idempotency uses `cache.add()` (SETNX) with a 5-minute TTL.

## Existing pattern to follow
`SRC:utils/websocket/protocol.py` — generic, port as-is.

## Files Owned
- `utils/websocket/__init__.py` (C)
- `utils/websocket/protocol.py` (C)
- `utils/tests/test_websocket_protocol.py` (C)

## Implementation Steps

### Step 1 — functions (all async, `consumer` first arg where applicable)
- `handle_auth_rotate(consumer, data)` — validate `data["token"]` via `get_user_from_token`; on success swap `consumer.scope["user"]` (+ `consumer.user`) and send `{"type":"auth_rotated","user_id":...}`; on failure send `{"type":"auth_rotate_failed","code":"AUTH__TOKEN_INVALID"}` (reuse existing catalog code — no new codes).
- `send_ack(consumer, message_id, data=None)` — send `{"type":"ack","message_id":...,"data":...}` (omit `data` if `None`).
- `send_nack(consumer, message_id, code, detail=None)` — send `{"type":"nack","message_id":...,"code":...,"detail":...}` (omit `detail` if `None`).
- `check_idempotency(channel_name, message_id) -> bool` — validate `message_id` against `^[a-zA-Z0-9\-]{1,128}$`; invalid → return `True` (safe no-op skip). Use `cache.add(key, 1, IDEMPOTENCY_TTL)` where `IDEMPOTENCY_TTL = 300`; return `True` if the key already existed (duplicate → skip), `False` if newly set.

## Tests (`utils/tests/test_websocket_protocol.py`)
- `send_ack`/`send_nack` produce the exact payload shapes (use a fake consumer capturing `send_json`); `data`/`detail` omitted when `None`.
- `check_idempotency`: first call for a fresh id → `False`; immediate second call → `True`; an invalid id → `True`.
- `handle_auth_rotate` (async, `@pytest.mark.django_db`): valid token swaps `scope["user"]` and sends `auth_rotated`; invalid token sends `auth_rotate_failed`.

## Validation
```bash
uv run pytest utils/tests/test_websocket_protocol.py -x -v --ds=config.django.test
```

## Acceptance Criteria
- [ ] ACK/NACK, auth-rotate, and idempotency helpers implemented; no domain handlers.
- [ ] Idempotency uses SETNX semantics with 5-min TTL. Tests pass.
