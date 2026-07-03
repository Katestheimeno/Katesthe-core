# 005 — WebSocket delivery utilities

**Status:** [PENDING]
**Phase:** 1
**Group:** A
**Risk:** LOW
**Effort:** 20m
**Dependencies:** 001

## Goal
Create `utils.py` with `send_notification_to_user()` (channel-layer group send) and `_serialize_payload_for_storage()` (JSON-safe payload conversion).

## Context
`dispatch()` (subtask 007) calls both: `_serialize_payload_for_storage` before creating the `Notification`, and `send_notification_to_user` for fire-and-forget in-app delivery. Django Channels IS installed in DST, so the channel-layer import is safe — but the function must still catch exceptions so a missing/broken channel layer never blocks dispatch.

## Existing pattern to follow
- SRC reference: `SRC:notification_system/utils.py` (copy essentially as-is — it is already domain-free and game-independent, per its own docstring).

## Files Owned
- `notification_system/utils.py`
- `notification_system/tests/test_ws_utils.py`

## Implementation Steps

### Step 1 — `_serialize_payload_for_storage(payload)` / `_serialize(value)`
Copy from SRC: recursively converts `UUID`, `datetime`, `date` to strings so the payload is JSON-serializable for the `JSONField`. Empty/None payload → `{}`.

### Step 2 — `send_notification_to_user(user_id, notification)`
Copy from SRC: `async_to_sync(channel_layer.group_send)("user_{id}", {"type": "notification_new", ...whitelisted keys...})`. Wrap in try/except; log via `config.logger.logger` and return `bool` (True on success, False on failure). Must never raise into the caller.
- Guard `get_channel_layer()` returning `None` (no configured layer) → log + return `False`.
- Use `from config.logger import logger`.

## Tests
`test_ws_utils.py`:
- `_serialize_payload_for_storage` converts a `datetime`, a `UUID`, and nested dict/list values to JSON-serializable output; `None`/empty → `{}`.
- `send_notification_to_user` returns `True` when the channel layer accepts the send (mock `get_channel_layer`/`async_to_sync`), `False` when it raises or the layer is `None` — and does NOT propagate the exception.

## Validation
```bash
uv run pytest notification_system/tests/test_ws_utils.py -x -v --no-cov --ds=config.django.test
```

## Acceptance Criteria
- [ ] `_serialize_payload_for_storage` handles UUID/datetime/date + nesting; returns JSON-safe dict.
- [ ] `send_notification_to_user` never raises; returns bool; logs failures.
- [ ] Sends only whitelisted keys under event type `notification_new` to group `user_{id}`.
- [ ] No game/domain imports.
