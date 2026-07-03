# Authentication

RS256 JWT with HttpOnly-cookie transport, session revocation, and JWT-authenticated
WebSocket connections. All endpoints live under `accounts/` (`accounts/controllers/_auth.py`,
`accounts/controllers/_jwks.py`) and are routed at `accounts/urls/_auth.py`.

## JWT signing (RS256)

Tokens are signed with an RSA private key (`config/jwt_keys.py`), not a shared secret.
Every issued token carries a `kid` (key id) header (`accounts/tokens.KidAccessToken` /
`KidRefreshToken`) so JWKS consumers know which public key to verify against.

- **Local/dev:** `uv run python manage.py generate_jwt_keys` prints a
  `JWT_RSA_PRIVATE_KEY=` line to paste into `.env.local`. If unset, a transient key is
  generated at boot (tokens won't survive a restart — dev-only).
- **Production:** booting `config.django.production` without `JWT_RSA_PRIVATE_KEY` raises
  `ImproperlyConfigured`. There is no fallback.
- **`GET /.well-known/jwks.json`** — public, unauthenticated (`AllowAny`), RFC 7517 JWKS.
  Publishes the current public key and, during a rotation window
  (`JWT_PREVIOUS_PUBLIC_KEY_OBJ` set), the previous one too, each under its own `kid`.
  Deliberately excluded from the OpenAPI schema — the contract is the RFC itself.

## Cookie transport + CSRF

`accounts.authentication.CookieJWTAuthentication` reads the access token from an HttpOnly
cookie first, falling back to `Authorization: Bearer <token>` — existing Bearer clients
keep working unchanged.

- **Login (`POST /auth/jwt/create/`)** sets HttpOnly `access_token`/`refresh_token`
  cookies by default and omits `access`/`refresh` from the response body (`{"data": {"user": {...}}}`).
  Send `X-Token-Delivery: bearer` to get the tokens in the body instead (cross-domain /
  non-cookie clients).
- **Refresh (`POST /auth/jwt/refresh/`)** reads the refresh token from the request body
  first, then falls back to the `refresh_token` cookie. Cookie-sourced refresh requires a
  valid CSRF token; a body-supplied refresh does not.
- **CSRF bootstrap (`GET /auth/csrf/`)** — sets the `csrftoken` cookie. Cross-origin SPAs
  call this once before their first mutating request so `document.cookie` has a value to
  echo back as `X-CSRFToken`.
- Cookie-transported mutations that fail CSRF return `403 PERMISSION__DENIED`. Bearer-header
  auth is never CSRF-checked (no cookie involved).
- Cookie attributes (`secure`, `samesite`, `domain`, paths) come from the Pydantic
  `AUTH_COOKIE_*` settings (`config/settings/config.py`); cookie *names* and token
  lifetimes come from Django's `SIMPLE_JWT`.

## Session revocation

`accounts.services.session` (`revoke_all_sessions`, `detect_refresh_reuse`) backs:

- `POST /auth/users/logout-all/` — revokes every outstanding refresh token for the user.
- Password change, username change, account deletion — each revokes all sessions.
- **Refresh-token reuse detection:** replaying an already-rotated (blacklisted) refresh
  token revokes the entire session family, not just the replayed token — a rotated token
  being reused is a signal the old token leaked.

All of the above share one cache key: `auth:revoked_after:{user_id}` (a Unix timestamp,
7-day TTL). A token issued before that timestamp is rejected. The WebSocket auth
middleware (below) reads the **same** key — keep the template string identical if you
touch either side.

`accounts.tasks.token_tasks.flush_expired_jwt_tokens` is a Celery task for periodic
cleanup of expired blacklist/outstanding-token rows; wire its beat schedule where your
project's Celery beat config lives.

## WebSocket authentication

`utils.middleware.jwt_websocket_auth.JWTAuthMiddleware` (wired in `config/asgi.py`)
authenticates a Channels connection via the `Sec-WebSocket-Protocol` subprotocol or a
cookie token, checks the token against `auth:revoked_after:{user_id}`, and attaches
`scope["user"]`. On failure it closes the socket with a catalog-coded reason
(`jwt_auth_failed`, e.g. `AUTH__TOKEN_INVALID`).

`utils.websocket.protocol` provides consumer-agnostic helpers any `AsyncWebsocketConsumer`
can call: `handle_auth_rotate` (hot-swap the authenticated user on an open connection),
`send_ack`/`send_nack` (catalog-coded), `check_idempotency` (dedupes retried `message_id`s,
5-minute TTL). `utils.websocket.rate_limit.MessageRateLimiter` is a per-connection sliding
window (default 15 msgs/sec) — instantiate one per consumer instance, not shared.

## Error codes used

No new namespaces — auth failures reuse the existing catalog (`errors/catalog.py`,
documented fully in `API_CONTRACT.md`): `AUTH__UNAUTHENTICATED`, `AUTH__TOKEN_INVALID`,
`AUTH__INVALID_CREDENTIALS`, `PERMISSION__DENIED` (CSRF failure), `VALIDATION__*`
(activation link / missing fields), `RESOURCE__NOT_FOUND` (activation target user).

## What's generic vs. project-specific

Everything on this page is domain-agnostic — no game/AI/elearning logic, no
project-specific throttle scopes or permission classes. If you're extending this for a
specific product, add domain logic in your own app; don't grow `accounts/` past what's
documented here.
