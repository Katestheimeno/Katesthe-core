# 020 — JWT WebSocket auth middleware (5.1)

**Status:** [PENDING]
**Phase:** 5
**Group:** ws
**Risk:** HIGH
**Effort:** 55m
**Dependencies:** 003 (RS256/AccessToken), 016 (revocation cache key contract)

## Goal
Add `JWTAuthMiddleware` for Django Channels (token from subprotocol or cookie, signature+expiry validation, session-revocation check, fail-open cache) and wrap the ASGI WebSocket stack with it — without breaking the example consumer.

## Context
`config/asgi.py` currently wraps `URLRouter(websocket_urlpatterns)` in `AuthMiddlewareStack`. `config/routing.py` routes `ws/test/` → `ExampleConsumer`. The revocation cache key `auth:revoked_after:{user_id}` is written by `revoke_all_sessions()` (016) — read the SAME key here. All cache ops fail open (Redis down → fall back to DB / accept).

## Existing pattern to follow
`SRC:utils/middleware/jwt_websocket_auth.py` — generic, port as-is.

## Files Owned
- `utils/middleware/__init__.py` (C)
- `utils/middleware/jwt_websocket_auth.py` (C)
- `utils/tests/test_jwt_websocket_auth.py` (C)
- `config/asgi.py` (M)

## Implementation Steps

### Step 1 — module helpers + middleware
Constants: `USER_CACHE_TTL = 300`, `REVOKED_AFTER_CACHE_KEY_TEMPLATE = "auth:revoked_after:{user_id}"`. Implement:
- `extract_token_from_scope(scope)` — priority 1: `scope["subprotocols"]` shaped `["access_token", <jwt>]` (set `scope["_auth_via_subprotocol"]=True`); priority 2: parse the `Cookie` header for `access_token=`. Return token or `None`.
- `get_accepted_subprotocol(scope)` — return `"access_token"` if the client offered it, else `None` (never echo foreign protocols).
- `get_user_from_token(token_string)` — async: (1) `AccessToken(token_string)` (signature+expiry); (2) revocation check via `_is_token_revoked` (reject if `iat` < cached revoked_after; cache miss/Redis down → not revoked); (3) `@database_sync_to_async` user lookup requiring `is_active`, cached 300s by token hash. Return `User` or `None`. Never log token contents.
- `jwt_auth_failed(scope)` — return `scope.get("jwt_auth_failed", False)`.
- `_is_token_revoked(access_token, user_id)` — async; wrap all cache access in try/except → fail open (`False`).
- `class JWTAuthMiddleware`: async `__call__(scope, receive, send)` — only WebSocket scopes; extract token; on success set `scope["user"]` + `scope["jwt_auth_failed"]=False`; on validation failure set only `scope["jwt_auth_failed"]=True` (leave `scope["user"]` for the downstream `AuthMiddlewareStack` to fill for session fallback); if no token, pass through untouched.

### Step 2 — wire ASGI (`config/asgi.py`)
```python
from utils.middleware.jwt_websocket_auth import JWTAuthMiddleware
from channels.security.websocket import AllowedHostsOriginValidator
...
"websocket": AllowedHostsOriginValidator(
    AuthMiddlewareStack(JWTAuthMiddleware(URLRouter(websocket_urlpatterns)))
),
```
Keep the existing `django_asgi_app` for `http`. The example consumer must still connect.

## Tests (`utils/tests/test_jwt_websocket_auth.py`)
- `extract_token_from_scope` finds a token in subprotocols and in the cookie header; returns `None` when absent.
- `get_accepted_subprotocol` echoes `"access_token"` only when offered.
- `get_user_from_token` (async, `@pytest.mark.django_db`): valid token → the user; expired/garbage → `None`; a token whose `iat` predates a set `auth:revoked_after:{uid}` → `None`; inactive user → `None`.
- Cache/Redis unavailable (LocMem) → revocation check fails open (valid token still authenticates).
- `jwt_auth_failed` reflects `scope["jwt_auth_failed"]`.

> Note: 020 adds `AllowedHostsOriginValidator` around the WS stack in `config/asgi.py` (it did not wrap it before). These helper-level tests don't drive the full ASGI app, so they're unaffected; but any test (here or in dependent features) that connects a `WebsocketCommunicator` through the top-level app must use an allowed Host/Origin header (test settings' `ALLOWED_HOSTS`).

## Validation
```bash
uv run pytest utils/tests/test_jwt_websocket_auth.py -x -v --ds=config.django.test
```

## Acceptance Criteria
- [ ] Token from subprotocol (preferred) or cookie; RS256 validation; revocation check; fail-open cache.
- [ ] ASGI wrapped with `AllowedHostsOriginValidator` + `JWTAuthMiddleware`; example consumer unaffected.
- [ ] No token contents logged. Tests pass.
