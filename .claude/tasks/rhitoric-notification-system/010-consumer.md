# 010 — WebSocket consumer + ASGI routing (guarded auth)

**Status:** [PENDING]
**Phase:** 2
**Group:** B
**Risk:** HIGH
**Effort:** 45m
**Dependencies:** 002

## Goal
Create `NotificationConsumer` handling ONLY `notification_new`, `auth_rotate`, `ping`/heartbeat, and register the `ws/notifications/` route — with WS-auth imports GUARDED so the app builds standalone.

## Context
The SRC consumer imports three helpers that DO NOT EXIST in DST today:
`utils.middleware.jwt_websocket_auth` (`get_accepted_subprotocol`, `jwt_auth_failed`), `utils.websocket.rate_limit` (`MessageRateLimiter`), `utils.websocket.protocol` (`handle_auth_rotate`). These belong to the SEPARATE `rhitoric-auth-core` plan (Phase 5). This subtask MUST NOT hard-depend on them — guard the imports and degrade gracefully so `from notification_system.consumers import NotificationConsumer` always succeeds (required by the Phase 12 smoke test).

## Existing pattern to follow
- SRC reference: `SRC:notification_system/consumers.py` (read it — it has the 5 game no-op handlers to STRIP).
- DST `config/routing.py` already contains a commented-out `NotificationConsumer` placeholder and uses `re_path`; `utils/consumers.py::ExampleConsumer` shows the DST consumer style. Channels default `AuthMiddlewareStack` populates `scope["user"]`.

## Files Owned
- `notification_system/consumers.py`
- `config/routing.py`  (add the `ws/notifications/` route)
- `notification_system/tests/consumers/__init__.py`
- `notification_system/tests/consumers/test_notification_consumer.py`

## Implementation Steps

### Step 1 — guarded imports
At module top, attempt the `rhitoric-auth-core` imports; on `ImportError` provide safe fallbacks:
```python
try:
    from utils.middleware.jwt_websocket_auth import get_accepted_subprotocol, jwt_auth_failed
    from utils.websocket.protocol import handle_auth_rotate
    _WS_AUTH_AVAILABLE = True
except ImportError:  # rhitoric-auth-core Phase 5 not backported yet
    _WS_AUTH_AVAILABLE = False
    def get_accepted_subprotocol(scope): return None
    def jwt_auth_failed(scope): return False
    async def handle_auth_rotate(consumer, data): ...  # no-op / send {"type":"error"}

try:
    from utils.websocket.rate_limit import MessageRateLimiter
except ImportError:
    class MessageRateLimiter:  # minimal no-op fallback
        def __init__(self, *a, **k): ...
        def is_throttled(self): return False
```
Document clearly that when `rhitoric-auth-core` Phase 5 lands, the real implementations take over automatically.

### Step 2 — consumer body
Copy the SRC `NotificationConsumer` connect/disconnect/receive/heartbeat/`notification_new`/`send_json` logic. Keep:
- `connect`: reads `scope["user"]`; if `jwt_auth_failed(scope)` → `close(4401)`; if user missing/`AnonymousUser` → `close(4001)`; else accept (with `subprotocol=get_accepted_subprotocol(scope)`), join `user_{id}`, send `connection_established`, start heartbeat.
- `receive`: `ping` → `pong`; `auth_rotate` → `handle_auth_rotate(self, data)`; rate-limit guard.
- `notification_new`: forward only the whitelisted `_NOTIFICATION_ALLOWED_KEYS`.
- Heartbeat every 30s.
- Close codes: keep `4401` and `4001` only.

### Step 3 — STRIP game handlers
DELETE the 5 no-op methods: `player_joined`, `player_left_game`, `game_abandoned`, `game_completed`, `vote_cast`.

### Step 4 — routing
In `config/routing.py` add:
```python
from notification_system.consumers import NotificationConsumer
websocket_urlpatterns += [
    re_path(r"^ws/notifications/$", NotificationConsumer.as_asgi()),
]
```
Keep the existing `ExampleConsumer` route. Uncomment/replace the placeholder comment line.

## Tests
`test_notification_consumer.py` (use `channels.testing.WebsocketCommunicator` + `InMemoryChannelLayer`):
- unauthenticated (`AnonymousUser`) connection → closed with `4001`.
- authenticated user connects → receives `connection_established`; a `notification_new` group event is forwarded with only whitelisted keys.
- `ping` → `pong`.
- module import succeeds even with the auth helpers absent (the guarded-fallback path) — this is the critical standalone-build assertion.

**Async-test harness (IMPORTANT — do NOT use `@pytest.mark.asyncio`).** This repo has NO `pytest-asyncio` dependency and runs pytest with `--strict-markers`, so an `asyncio` marker is a hard collection error (there is also no existing async-test convention). Do NOT add `pytest-asyncio` or edit `pyproject.toml`/`pytest.ini` (both are outside this subtask's ownership and `pyproject.toml` is concurrently edited by `rhitoric-utilities`). Instead drive the async `WebsocketCommunicator` coroutines from plain sync tests via `asgiref.sync.async_to_sync` (already available — Channels depends on `asgiref`):
```python
from asgiref.sync import async_to_sync
from channels.testing import WebsocketCommunicator

@pytest.mark.django_db
def test_unauthenticated_closes_4001():
    async def scenario():
        comm = WebsocketCommunicator(app, "/ws/notifications/")
        comm.scope["user"] = AnonymousUser()
        connected, code = await comm.connect()
        assert connected is False and code == 4001
        await comm.disconnect()
    async_to_sync(scenario)()
```
Inject the user by setting `communicator.scope["user"]` before `connect()`; wrap the notification-forward test in the InMemoryChannelLayer group_send. The import-with-helpers-absent assertion is a normal sync test.

## Validation
```bash
uv run python -c "from notification_system.consumers import NotificationConsumer; print('consumer import OK')"
uv run pytest notification_system/tests/consumers/ -x -v --no-cov --ds=config.django.test
```

## Acceptance Criteria
- [ ] `from notification_system.consumers import NotificationConsumer` succeeds with the auth helpers ABSENT (guarded).
- [ ] Only `notification_new`, `auth_rotate`, `ping`/heartbeat, `connection_established` handled; 5 game handlers removed.
- [ ] Close codes limited to `4401` / `4001`.
- [ ] `ws/notifications/` route registered without breaking the existing `ws/test/` route.
- [ ] No game/domain event handling.
