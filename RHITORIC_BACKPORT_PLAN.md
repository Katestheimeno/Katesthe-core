# Backport Plan: Rhitoric-core patterns into Katesthe-core

**Source project:** `/home/tmpusr/Documents/github/Rhitoric-core`
**Target project:** `/home/tmpusr/dev/Katesthe-core`
**Date:** 2026-07-03
**Author:** AI-assisted
**Prerequisite:** The Depadrive backport plan (`BACKPORT_PLAN.md`) has been fully executed. This plan covers patterns discovered in Rhitoric-core that go beyond what Depadrive contributed.

---

## Overview

Rhitoric-core was the second production project built on Katesthe-core. Over ~6 months of production hardening, it developed patterns in three main areas that the Depadrive project never needed:

1. **RS256 JWT + Cookie-based auth** — asymmetric signing, JWKS key rotation, HttpOnly cookie auth with CSRF, session revocation, replay detection
2. **Advanced throttle architecture** — 28 scopes with base class hierarchy, per-credential brute-force defense, global toggle
3. **WebSocket auth infrastructure** — JWT middleware for Channels, protocol utilities (ACK/NACK, idempotency, auth rotation), rate limiting

**What already exists (do NOT recreate):** Everything from the Depadrive backport plan — error catalog, envelope helpers, exception handler, request ID middleware, health endpoints, production hardening (basic), CI workflow, basic throttling, pagination, access log, Celery task template, conftest.py, OpenAPI helpers, Sentry, debug payload, image validators, CSV/XLSX export, upload paths, outbox, smoke test, coveragerc, Celery scripts, notifications app.

**What to add:** 42 patterns across 12 phases. Phases 1-3 are sequential (RS256 → Cookie auth → Session management). Phases 4-11 are all independent and can run in parallel with each other. Phase 12 (Notification System) is independent and replaces the existing simple `notifications` app.

---

## Reference Convention

Throughout this plan, source files are referenced as:
- `SRC:path` = `/home/tmpusr/Documents/github/Rhitoric-core/path`
- `DST:path` = `/home/tmpusr/dev/Katesthe-core/path`

**Do NOT copy files verbatim.** Rhitoric-core has domain-specific logic (game, AI, elearning). Extract only the generic pattern and adapt it to a clean template context.

---

## Phase 1 — RS256 JWT Foundation

These are foundational. Cookie auth, JWKS, WebSocket auth, and session revocation all depend on the RSA key infrastructure.

### 1.1 RSA Key Management Module

**Create:**
| File | Purpose |
|------|---------|
| `DST:config/jwt_keys.py` | RSA key loading, kid computation, JWKS builder |

**Reference:** `SRC:config/jwt_keys.py`

**Functions:**
- `load_rsa_private_key(pem_b64: str)` — Load RSA private key from base64-encoded PEM
- `load_rsa_public_key(pem_b64: str)` — Load RSA public key from base64-encoded PEM
- `generate_rsa_private_key()` — Generate 2048-bit RSA key (dev-only fallback)
- `private_key_to_pem(key)` / `public_key_to_pem(key)` — Serialize to PEM
- `compute_kid(key)` — SHA-256 fingerprint of public key DER, truncated to 16 hex chars
- `build_jwks(key, kid, algorithm, previous_public_key, previous_kid)` — RFC 7517 JWKS response dict with optional key-rotation support

**Modify:** `DST:pyproject.toml` — add `cryptography` to dependencies.

**Validation:** `uv run python -c "from config.jwt_keys import generate_rsa_private_key, compute_kid; k = generate_rsa_private_key(); print(compute_kid(k))"` succeeds.

---

### 1.2 Pydantic Settings — JWT & Cookie Fields

**Modify:** `DST:config/settings/config.py`

**Add to `MainSettings`:**
```python
# JWT RS256
JWT_RSA_PRIVATE_KEY: str = Field(
    default="",
    description="Base64-encoded PEM of the RSA private key for JWT RS256 signing",
)
JWT_RSA_PREVIOUS_PUBLIC_KEY: str = Field(
    default="",
    description="Base64-encoded PEM of the previous public key (for JWKS rotation window)",
)
JWT_ISSUER: Optional[str] = Field(default=None, description="JWT iss claim")
JWT_AUDIENCE: Optional[str] = Field(default=None, description="JWT aud claim")

# Auth cookies
AUTH_COOKIE_DOMAIN: str = Field(default="", description="Domain for auth cookies")
AUTH_COOKIE_REFRESH_PATH: str = Field(
    default="/api/v1/auth/jwt/",
    description="Path scope for the refresh-token cookie",
)
AUTH_COOKIE_SECURE: Optional[bool] = Field(
    default=None, description="Secure flag for auth cookies (None = auto from DEBUG)"
)
AUTH_COOKIE_SAMESITE: Literal["Lax", "Strict", "None"] = Field(
    default="Lax", description="SameSite attribute for auth cookies"
)

# Throttle toggle
THROTTLE_ENABLED: bool = Field(
    default=True,
    description="Global toggle for all throttle classes. Set False for load testing.",
)
```

**Add `model_validator`:**
```python
@model_validator(mode="after")
def _validate_cookie_samesite(self):
    if self.AUTH_COOKIE_SAMESITE == "None":
        secure = self.AUTH_COOKIE_SECURE if self.AUTH_COOKIE_SECURE is not None else not self.DEBUG
        if not secure:
            raise ValueError(
                "AUTH_COOKIE_SAMESITE='None' requires secure cookies. "
                "Set AUTH_COOKIE_SECURE=true or use 'Lax'/'Strict'."
            )
    return self
```

**Reference:** `SRC:config/settings/config.py` (lines 615-740)

---

### 1.3 SimpleJWT RS256 Configuration

**Modify:** `DST:config/settings/restframework.py`

**Replace HS256 config with RS256:**
```python
from config.jwt_keys import load_rsa_private_key, generate_rsa_private_key, compute_kid, private_key_to_pem, public_key_to_pem

# Load or generate RSA key
if settings.JWT_RSA_PRIVATE_KEY:
    _rsa_private_key = load_rsa_private_key(settings.JWT_RSA_PRIVATE_KEY)
else:
    import warnings
    warnings.warn(
        "JWT_RSA_PRIVATE_KEY not set — generating a transient RSA key. "
        "Tokens will not survive restarts and multi-worker setups will 401.",
        stacklevel=2,
    )
    _rsa_private_key = generate_rsa_private_key()

_rsa_signing_pem = private_key_to_pem(_rsa_private_key)
_rsa_verifying_pem = public_key_to_pem(_rsa_private_key)
_rsa_kid = compute_kid(_rsa_private_key)
```

**Update SIMPLE_JWT dict:**
```python
SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=15),  # shorter for RS256
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
    "UPDATE_LAST_LOGIN": True,
    "ALGORITHM": "RS256",
    "SIGNING_KEY": _rsa_signing_pem,
    "VERIFYING_KEY": _rsa_verifying_pem,
    "ISSUER": settings.JWT_ISSUER,
    "AUDIENCE": settings.JWT_AUDIENCE,
    "KID": _rsa_kid,
    "AUTH_HEADER_TYPES": ("Bearer",),
    "AUTH_TOKEN_CLASSES": ("rest_framework_simplejwt.tokens.AccessToken",),
    # HttpOnly cookie transport
    "AUTH_COOKIE_ACCESS": "access_token",
    "AUTH_COOKIE_REFRESH": "refresh_token",
    "AUTH_COOKIE_HTTP_ONLY": True,
    "AUTH_COOKIE_PATH": "/",
    "AUTH_COOKIE_REFRESH_PATH": settings.AUTH_COOKIE_REFRESH_PATH,
}
```

**Also expose key objects on Django settings for the JWKS view:**
```python
JWT_RSA_PRIVATE_KEY_OBJ = _rsa_private_key
JWT_KID = _rsa_kid
```

**Reference:** `SRC:config/settings/restframework.py` (lines 23-136)

---

### 1.4 Custom Token Classes with kid Header

**Create:**
| File | Purpose |
|------|---------|
| `DST:accounts/tokens.py` | `KidAccessToken`, `KidRefreshToken` with kid in JWT header |

**Reference:** `SRC:accounts/tokens.py`

**What it does:** Overrides `__str__()` to inject the `kid` from settings into the JWT header via `pyjwt.encode(... headers={"kid": kid})`. This enables external JWKS consumers (e.g. Next.js Edge middleware) to select the correct public key for verification.

**Modify:** `DST:pyproject.toml` — ensure `PyJWT` is in dependencies (usually pulled in by `djangorestframework-simplejwt` already).

---

### 1.5 JWT Key Generation Management Command

**Create:**
| File | Purpose |
|------|---------|
| `DST:accounts/management/commands/generate_jwt_keys.py` | Generate RSA-2048 key and print base64 for .env |

**Reference:** `SRC:accounts/management/commands/generate_jwt_keys.py`

**Usage:** `python manage.py generate_jwt_keys` — outputs `JWT_RSA_PRIVATE_KEY=<base64>` for the .env file.

---

### 1.6 JWKS Endpoint

**Create:**
| File | Purpose |
|------|---------|
| `DST:accounts/controllers/_jwks.py` | Public RFC 7517 JWKS endpoint |

**Reference:** `SRC:accounts/controllers/_jwks.py`

**Behavior:**
- `GET /.well-known/jwks.json` (or configured path) — returns current RSA public key(s) in JWKS format
- During key rotation: serves both current and previous public keys, each with its own `kid`
- `Cache-Control: public, max-age=3600`
- `permission_classes = [AllowAny]`, `authentication_classes = []`
- Throttled by `PublicListThrottle`
- Only public material (`n`, `e`) — no private key data

**Modify:** `DST:accounts/urls/_auth.py` — add JWKS route.
**Modify:** `DST:accounts/controllers/__init__.py` — re-export `JWKSView`.

---

### 1.7 Production RS256 Enforcement

**Modify:** `DST:config/django/production.py`

**Add:**
```python
from django.core.exceptions import ImproperlyConfigured

if not settings.JWT_RSA_PRIVATE_KEY:
    raise ImproperlyConfigured(
        "JWT_RSA_PRIVATE_KEY is required in production. "
        "Run `python manage.py generate_jwt_keys` to create one."
    )

if not settings.JWT_ISSUER:
    import warnings
    warnings.warn("JWT_ISSUER not set — tokens will not carry an 'iss' claim.")
```

**Modify:** `DST:.env.prod.example` — add `JWT_RSA_PRIVATE_KEY=`, `JWT_ISSUER=`, `JWT_AUDIENCE=` placeholders.
**Modify:** `DST:.env.local.example` — add comment explaining transient key is auto-generated in dev.

**Validation:** `DJANGO_SETTINGS_MODULE=config.django.production uv run python -c "import django; django.setup()"` without `JWT_RSA_PRIVATE_KEY` crashes with `ImproperlyConfigured`.

---

## Phase 2 — Cookie-Based Auth & Security Hardening

Depends on Phase 1 (RS256 key infrastructure).

### 2.1 Cookie JWT Authentication Backend

**Create:**
| File | Purpose |
|------|---------|
| `DST:accounts/authentication.py` | `CookieJWTAuthentication` + `enforce_csrf()` |

**Reference:** `SRC:accounts/authentication.py`

**Behavior:**
1. Reads access token from HttpOnly `access_token` cookie (primary)
2. Enforces CSRF when authenticating via cookie (prevents CSRF on mutation endpoints)
3. Falls back to `Authorization: Bearer <token>` header (no CSRF — safe by design)
4. Graceful fallback: a bad/expired cookie falls back to header auth; CSRF failures are NOT caught (CSRF rejection never downgrades)

**Modify:** `DST:config/settings/restframework.py` — change `DEFAULT_AUTHENTICATION_CLASSES`:
```python
"DEFAULT_AUTHENTICATION_CLASSES": [
    "accounts.authentication.CookieJWTAuthentication",
],
```

**Modify:** `DST:accounts/controllers/_auth.py` — update login view to set HttpOnly cookies on successful auth, update logout to clear cookies, update refresh to read from cookie with CSRF enforcement.

---

### 2.2 OpenAPI Auth Extension for Spectacular

**Create:**
| File | Purpose |
|------|---------|
| `DST:config/spectacular_auth.py` | Register `CookieJWTAuthentication` with drf-spectacular |

**Reference:** `SRC:config/spectacular_auth.py`

**What it does:** `OpenApiAuthenticationExtension` that tells drf-spectacular how to represent `CookieJWTAuthentication` in the OpenAPI schema (type: http, scheme: bearer, bearerFormat: JWT).

**Note:** drf-spectacular auto-discovers extensions in modules listed in `INSTALLED_APPS`. Place the file where it will be found, or register it via `SPECTACULAR_SETTINGS["EXTENSIONS"]`.

---

### 2.3 Security Headers Middleware

**Create:**
| File | Purpose |
|------|---------|
| `DST:config/middleware/security_headers.py` | `SecurityHeadersMiddleware` |

**Reference:** `SRC:config/middleware/security_headers.py`

**Adds headers not covered by Django's built-in `SecurityMiddleware`:**
- `Referrer-Policy: strict-origin-when-cross-origin`
- `Permissions-Policy: accelerometer=(), camera=(), display-capture=(), fullscreen=(self), geolocation=(), gyroscope=(), magnetometer=(), microphone=(), payment=(), usb=()`

**Modify:** `DST:config/settings/apps_middlewares.py` — add `'config.middleware.security_headers.SecurityHeadersMiddleware'` to `MIDDLEWARE` after `SecurityMiddleware`.

---

### 2.4 Enhanced Production Security

**Modify:** `DST:config/django/production.py`

**Add beyond what the Depadrive backport already set:**
```python
# Reverse proxy header for SSL detection
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

# CSRF trusted origins derived from ALLOWED_HOSTS
CSRF_TRUSTED_ORIGINS = [
    f"https://{host}" for host in ALLOWED_HOSTS if host != "*"
]
```

**Modify:** `DST:config/django/base.py` — add:
```python
X_FRAME_OPTIONS = "DENY"
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = "strict-origin-when-cross-origin"
```

---

### 2.5 Timing-Oracle Defense in Login

**Modify:** `DST:accounts/serializers/auth/_token.py`

**Add to `CustomTokenObtainPairSerializer.validate()`:**
When no user is found for the given credentials, burn a dummy `check_password()` call against a known hash so that the response time does not leak whether the username/email exists:

```python
from django.contrib.auth.hashers import check_password

# ... in the except User.DoesNotExist branch:
check_password(password, "pbkdf2_sha256$720000$dummy$salt=")
```

**Reference:** `SRC:accounts/serializers/auth/_token.py` (timing-oracle defense section)

**Why:** Without this, an attacker can distinguish "user exists, wrong password" from "user does not exist" by measuring response latency, enabling username enumeration.

---

### 2.6 Liveness Probe Middleware

**Create:**
| File | Purpose |
|------|---------|
| `DST:config/middleware/liveness_probe.py` | `LivenessProbeMiddleware` |

**Reference:** `SRC:config/middleware/liveness_probe.py`

**Behavior:** Intercepts `GET /api/v1/liveness/` before `SessionMiddleware` so health probes work even when the DB is down (no session table required). Returns `{"status": "alive", "service": "<project_name>"}`.

**Modify:** `DST:config/settings/apps_middlewares.py` — add before `SessionMiddleware` in the `MIDDLEWARE` list.

**Note:** This complements the existing `config/health.py` endpoints which run after the full middleware stack. The liveness probe is lighter and survives DB outages.

---

## Phase 3 — Session Management & Account Lifecycle

Depends on Phase 2 (Cookie auth must be in place).

### 3.1 Session Revocation Service

**Create:**
| File | Purpose |
|------|---------|
| `DST:accounts/services/session.py` | `revoke_all_sessions()` + `detect_refresh_reuse()` |

**Reference:** `SRC:accounts/services/session.py`

**`revoke_all_sessions(user_id, event)`:**
- Blacklists all outstanding, non-expired refresh tokens for the user via `bulk_create(ignore_conflicts=True)`
- Sets `auth:revoked_after:{user_id}` cache key (unix timestamp, 7-day TTL) for WebSocket middleware to reject pre-revocation access tokens
- Returns count of newly blacklisted tokens
- Used by: logout-all, password change, username change, account deletion

**`detect_refresh_reuse(raw_token)`:**
- Token-family revocation: if a blacklisted JTI is replayed (valid signature but already blacklisted), all sessions for that user are revoked
- Guards: garbage/forged/expired tokens are NOT treated as reuse — payload only trusted after full signature+expiry verification
- This is defense against token theft (attacker replays a rotated refresh token)

---

### 3.2 Token Housekeeping Task

**Create:**
| File | Purpose |
|------|---------|
| `DST:accounts/tasks/token_tasks.py` | `flush_expired_jwt_tokens` periodic task |

**Reference:** `SRC:accounts/tasks/token_tasks.py`

**What it does:** Deletes expired `OutstandingToken` rows (cascades to `BlacklistedToken`). Equivalent to `manage.py flushexpiredtokens` but runs as a scheduled Celery task.

**Modify:** `DST:config/settings/celery.py` — add to `CELERY_BEAT_SCHEDULE`:
```python
"flush-expired-jwt-tokens": {
    "task": "accounts.tasks.flush_expired_jwt_tokens",
    "schedule": 86400,  # daily
},
```

---

### 3.3 Custom JWT Claims — is_superuser Exclusion

**Modify:** `DST:accounts/serializers/auth/_token.py`

**In `get_token()` custom claims, add `permissions` list but intentionally exclude `is_superuser`:**
```python
@classmethod
def get_token(cls, user):
    token = super().get_token(user)
    token["username"] = user.username
    token["email"] = user.email
    token["is_verified"] = user.is_verified
    token["is_staff"] = user.is_staff
    # SEC-001: is_superuser intentionally NOT in JWT.
    # Superuser status must be checked server-side.
    if user.is_superuser:
        token["permissions"] = ["system_admin"]
    elif user.is_staff:
        token["permissions"] = list(
            user.user_permissions.values_list("codename", flat=True)
        )
    else:
        token["permissions"] = []
    return token
```

**Why:** Embedding `is_superuser=True` in a JWT means anyone with the token has a client-side claim of superuser status. If the token is stolen or the frontend trusts this claim, it enables privilege escalation. Superuser checks must always hit the server.

---

### 3.4 Privilege-Change Session Revocation

**Modify:** `DST:accounts/controllers/_auth.py`

**Wire `revoke_all_sessions()` into:**
- `set_password` action — after successful password change
- `set_username` action — after successful username change
- `destroy` action — on account deletion (soft delete)
- `logout_all` action — new endpoint for "log out all sessions"

**Reference:** `SRC:accounts/controllers/_auth.py` (CustomUserViewSet actions)

---

## Phase 4 — Advanced Throttle Architecture

Independent of Phases 1-3. Can be implemented in parallel.

### 4.1 Throttle Base Classes

**Modify:** `DST:utils/throttles.py` — replace the simple two-class throttle setup with the full base class hierarchy.

**Reference:** `SRC:utils/throttling.py`

**Base classes (generic, keep all of these):**
```python
def _throttle_enabled():
    from django.conf import settings
    return getattr(settings, "THROTTLE_ENABLED", True)

class _UserOrIPThrottle(SimpleRateThrottle):
    """Keyed by user PK (authenticated) or client IP (anonymous)."""
    # ... with _throttle_enabled() check

class _IPOnlyThrottle(SimpleRateThrottle):
    """Always keyed by client IP, even for authenticated users."""
    # ... with _throttle_enabled() check
```

**Starter throttle classes (universal — keep these):**
- `DefaultAnonThrottle(_IPOnlyThrottle)` — scope: `default_anon` (60/min)
- `DefaultUserThrottle(_UserOrIPThrottle)` — scope: `default_user` (120/min)
- `AuthLoginThrottle(_IPOnlyThrottle)` — scope: `auth_login` (10/min per IP)
- `AuthLoginAccountThrottle(SimpleRateThrottle)` — scope: `auth_login_account` (5/hour per credential SHA-256 hash)
- `AuthRegisterThrottle(_IPOnlyThrottle)` — scope: `auth_register` (5/hour per IP)
- `AuthResetThrottle(_IPOnlyThrottle)` — scope: `auth_reset` (3/hour per IP)
- `AuthSetPasswordThrottle(_UserOrIPThrottle)` — scope: `auth_set_password` (10/hour per user)
- `AuthRefreshThrottle(_IPOnlyThrottle)` — scope: `auth_refresh` (20/min per IP)
- `AuthActivationThrottle(_IPOnlyThrottle)` — scope: `auth_activation` (10/hour per IP)
- `PublicListThrottle(_IPOnlyThrottle)` — scope: `public_list` (120/min per IP)
- `SearchThrottle(_UserOrIPThrottle)` — scope: `search` (60/min)
- `WebhookThrottle(_IPOnlyThrottle)` — scope: `webhook` (200/min per IP)
- `ExternalAPIThrottle(SimpleRateThrottle)` — scope: `external_api` (300/min per X-API-Key)
- `UserMutationThrottle(_UserOrIPThrottle)` — scope: `user_mutation` (30/min per user)

**Strip domain-specific throttles** (GameActionThrottle, AIMessageThrottle, QuizAttemptThrottle, etc.). Projects add those when they need them.

### 4.2 Throttle Rates in REST_FRAMEWORK

**Modify:** `DST:config/settings/restframework.py` — update `DEFAULT_THROTTLE_RATES` to match the starter throttle classes:

```python
"DEFAULT_THROTTLE_CLASSES": [
    "utils.throttles.DefaultAnonThrottle",
    "utils.throttles.DefaultUserThrottle",
],
"DEFAULT_THROTTLE_RATES": {
    "default_anon": "60/min",
    "default_user": "120/min",
    "auth_login": "10/min",
    "auth_login_account": "5/hour",
    "auth_register": "5/hour",
    "auth_reset": "3/hour",
    "auth_set_password": "10/hour",
    "auth_refresh": "20/min",
    "auth_activation": "10/hour",
    "public_list": "120/min",
    "search": "60/min",
    "webhook": "200/min",
    "external_api": "300/min",
    "user_mutation": "30/min",
},
```

### 4.3 Flush Throttles Management Command

**Create:**
| File | Purpose |
|------|---------|
| `DST:utils/management/commands/flush_throttles.py` | Clear all DRF throttle counters from cache |

**Reference:** `SRC:utils/management/commands/flush_throttles.py`

**Behavior:** Redis-aware: deletes only `*throttle_*` keys when possible, falls back to `cache.clear()`.

---

## Phase 5 — WebSocket Auth Infrastructure

Depends on Phase 1 (RS256 JWT) and Phase 3 (session revocation cache keys).

### 5.1 JWT WebSocket Auth Middleware

**Create:**
| File | Purpose |
|------|---------|
| `DST:utils/middleware/__init__.py` | Package init |
| `DST:utils/middleware/jwt_websocket_auth.py` | `JWTAuthMiddleware` for Django Channels |

**Reference:** `SRC:utils/middleware/jwt_websocket_auth.py`

**Token extraction priority:**
1. `Sec-WebSocket-Protocol` header: `new WebSocket(url, ["access_token", jwt])` — preferred (keeps token out of URL/logs)
2. `access_token` cookie — fallback

**Validation pipeline:**
1. Signature + expiry via SimpleJWT `AccessToken()`
2. Session-revocation check: `auth:revoked_after:{user_id}` cache key (set by `revoke_all_sessions()`). Tokens whose `iat` predates the timestamp are rejected. Cache miss fails open.
3. User lookup with `is_active` check. User cached for 300s per token hash.

**Helper functions (export from the module):**
- `jwt_auth_failed(scope)` — True when a token WAS presented but failed validation. Consumers close with 4401.
- `get_accepted_subprotocol(scope)` — RFC 6455 compliance: echo `"access_token"` back to the client.
- `extract_token_from_scope(scope)` — Token extraction logic.
- `get_user_from_token(token_string)` — Full async validation pipeline.

**All cache operations wrapped in try/except** — Redis down = fail open (auth falls back to DB lookup).

**Modify:** `DST:config/asgi.py` — update WebSocket stack:
```python
from utils.middleware.jwt_websocket_auth import JWTAuthMiddleware

application = ProtocolTypeRouter({
    "http": get_asgi_application(),
    "websocket": AllowedHostsOriginValidator(
        AuthMiddlewareStack(
            JWTAuthMiddleware(
                URLRouter(websocket_urlpatterns)
            )
        )
    ),
})
```

---

### 5.2 WebSocket Protocol Utilities

**Create:**
| File | Purpose |
|------|---------|
| `DST:utils/websocket/__init__.py` | Package init |
| `DST:utils/websocket/protocol.py` | Shared protocol functions for any consumer |

**Reference:** `SRC:utils/websocket/protocol.py`

**Functions (all async, take `consumer` as first argument):**

- **`handle_auth_rotate(consumer, data)`** — Hot-swap the authenticated user on an existing WebSocket connection. Client sends `{"type": "auth_rotate", "token": "<jwt>"}`. Server validates, updates `scope["user"]`, responds with `auth_rotated` or `auth_rotate_failed`.

- **`send_ack(consumer, message_id, data)`** — ACK response correlated to `message_id`. Payload: `{"type": "ack", "message_id": "<id>", "data": {...}}`.

- **`send_nack(consumer, message_id, code, detail)`** — NACK (negative acknowledgement) with error code.

- **`check_idempotency(channel_name, message_id)`** — Redis-backed duplicate detection using `cache.add()` (SETNX) with 5-minute TTL. Returns `True` if duplicate (caller should skip). Invalid message IDs treated as duplicates (safe no-op).

---

### 5.3 WebSocket Rate Limiter

**Create:**
| File | Purpose |
|------|---------|
| `DST:utils/websocket/rate_limit.py` | Per-connection sliding-window rate limiter |

**Reference:** `SRC:utils/websocket/rate_limit.py`

**Class: `MessageRateLimiter`**
- Sliding-window rate limiter (per-connection, no shared state)
- Default: 15 messages per 1 second
- Uses `collections.deque` with `time.monotonic()`
- `is_throttled()` returns True when rate exceeded

**Usage in any consumer:**
```python
from utils.websocket.rate_limit import MessageRateLimiter

class MyConsumer(AsyncJsonWebsocketConsumer):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._rate_limiter = MessageRateLimiter()

    async def receive(self, text_data):
        if self._rate_limiter.is_throttled():
            await self.send_json({"type": "error", "message": "Rate limited"})
            return
```

---

### 5.4 CORS X-Token-Delivery Header

**Modify:** `DST:config/settings/corsheaders.py` — add `"x-token-delivery"` to `CORS_ALLOW_HEADERS`.

**Why:** Cross-domain SPAs can send `X-Token-Delivery: bearer` to opt out of cookie-based auth and receive tokens in the response body instead. The login view checks this header.

---

## Phase 6 — Operational Utilities

All independent. Can be implemented in any order.

### 6.1 Celery Task Helpers

**Create:**
| File | Purpose |
|------|---------|
| `DST:utils/celery_helpers.py` | `safe_task_delay()`, `safe_task_delay_with_countdown()`, `safe_send_task()` |

**Reference:** `SRC:utils/celery_helpers.py`

**`safe_task_delay(task, *args, **kwargs)`:**
- In test mode (`CELERY_TASK_ALWAYS_EAGER`): uses `.apply()` (no broker connection needed)
- In production: uses `.delay()` with error logging (doesn't crash the app if broker is down)

**`safe_task_delay_with_countdown(task, countdown_seconds, *args, **kwargs)`:**
- Same pattern but with `.apply_async(countdown=...)` for delayed execution

**`safe_send_task(celery_app, task_name, args, kwargs)`:**
- By-name task dispatch for cross-app task invocation
- In test mode: looks up task from registry, falls back to dynamic import
- In production: uses `celery_app.send_task()` (guarantees correct registered name routing)

---

### 6.2 External API Health-Check Command (Skeleton)

**Create:**
| File | Purpose |
|------|---------|
| `DST:utils/management/commands/check_external_apis.py` | Template for probing external API dependencies |

**Reference:** `SRC:utils/management/commands/check_external_apis.py` (extract the generic skeleton)

**Generic pattern to keep:**
- `ProbeResult` and `ConfigCheck` dataclasses
- `ThreadPoolExecutor` for parallel probe execution
- Latency measurement with `time.perf_counter()`
- `ProbeStatus` enum (PASS / FAIL / SKIP / MOCK)
- Colored output with status formatting
- Exit code 1 on any failure (CI-friendly)
- `--service`, `--verbose`, `--timeout` flags

**Strip:** All Rhitoric-specific service definitions (PvA, RhiAI, tutor, events). The template ships with an empty `SERVICES` dict and a docstring explaining how to add services.

---

### 6.3 Test Settings — Throttle Override

**Modify:** `DST:config/django/test.py` — override all throttle rates to high values so throttling never interferes with tests:

```python
REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"] = {
    k: "9999/min" for k in REST_FRAMEWORK.get("DEFAULT_THROTTLE_RATES", {})
}
```

**Reference:** `SRC:config/django/test.py`

---

## App Scaffold Update

After all patterns are implemented, update the app template so `starttemplateapp` generates apps that follow the new conventions:

**Modify:** `DST:static/exp_app/`

Add to the scaffold:
- `authentication.py` placeholder (commented example for custom auth backends)
- `permissions/` directory with `__init__.py` containing a commented `IsOwner` example

---

## Dependency Graph

```
Phase 1 (sequential):
  1.1 RSA Key Module ──→ 1.2 Pydantic Settings ──→ 1.3 RS256 Config ──→ 1.4 Kid Tokens
  1.5 Key Generation Command (independent, after 1.1)
  1.6 JWKS Endpoint (after 1.3 + 1.4)
  1.7 Production Enforcement (after 1.2)

Phase 2 (after Phase 1 complete):
  2.1 Cookie JWT Auth (needs RS256 config)
  2.2 Spectacular Auth Extension (needs 2.1)
  2.3 Security Headers Middleware (independent)
  2.4 Enhanced Production Security (independent)
  2.5 Timing-Oracle Defense (independent)
  2.6 Liveness Probe Middleware (independent)

Phase 3 (after Phase 2 complete):
  3.1 Session Revocation Service (needs cookie auth for logout flow)
  3.2 Token Housekeeping Task (needs token_blacklist app)
  3.3 Custom JWT Claims (needs 1.4 kid tokens)
  3.4 Privilege-Change Revocation (needs 3.1)

Phase 4 (independent of Phases 1-3):
  4.1 Throttle Base Classes (independent)
  4.2 Throttle Rates (after 4.1)
  4.3 Flush Throttles Command (independent)

Phase 5 (after Phase 1 + Phase 3):
  5.1 JWT WebSocket Auth Middleware (needs RS256 + revocation cache key)
  5.2 WebSocket Protocol Utilities (independent)
  5.3 WebSocket Rate Limiter (independent)
  5.4 CORS Header (independent)

Phase 6 (all independent):
  6.1-6.3 all independent of each other
```

---

## Validation Gate

After each phase, run:

```bash
# Tests pass
uv run pytest --ds=config.django.test

# OpenAPI validates
uv run python manage.py spectacular --validate --fail-on-warn --settings=config.django.test

# Phase 1 smoke test
uv run python -c "
from config.jwt_keys import generate_rsa_private_key, compute_kid, build_jwks
from accounts.tokens import KidAccessToken, KidRefreshToken
print('Phase 1 imports OK')
"

# Phase 2 smoke test
uv run python -c "
from accounts.authentication import CookieJWTAuthentication, enforce_csrf
from config.middleware.security_headers import SecurityHeadersMiddleware
print('Phase 2 imports OK')
"

# Phase 3 smoke test
uv run python -c "
from accounts.services.session import revoke_all_sessions, detect_refresh_reuse
print('Phase 3 imports OK')
"

# Phase 5 smoke test
uv run python -c "
from utils.middleware.jwt_websocket_auth import JWTAuthMiddleware, jwt_auth_failed
from utils.websocket.protocol import handle_auth_rotate, send_ack, send_nack, check_idempotency
from utils.websocket.rate_limit import MessageRateLimiter
print('Phase 5 imports OK')
"
```

After Phase 1 is complete, existing auth tests will need updates since the JWT algorithm changes from HS256 to RS256. **Update test factories to generate RS256 tokens** — this is expected and correct.

---

## Phase 7 — Pydantic-Spectacular Bridge

Independent of all other phases.

### 7.1 Pydantic-to-Spectacular Helpers

**Create:**
| File | Purpose |
|------|---------|
| `DST:config/spectacular_pydantic.py` | Bridge Pydantic models to drf-spectacular OpenAPI annotations |

**Reference:** `SRC:config/spectacular_pydantic.py`

**Functions:**
- `pydantic_schema(model)` — Returns OpenAPI/JSON Schema dict from a Pydantic `BaseModel`. Use in `extend_schema(responses={200: OpenApiResponse(response=pydantic_schema(MyResponse))})`.
- `pydantic_array_schema(model)` — Returns `{"type": "array", "items": <model_schema>}` for `list[MyResponse]`.
- `pydantic_one_of_schema(*models)` — Returns `{"oneOf": [...]}` for `Union[ModelA, ModelB]`.
- `as_openapi_response(hint, *, description="")` — Auto-detects Pydantic model vs. `list[Pydantic]` vs. DRF serializer and wraps appropriately in `OpenApiResponse`. Non-Pydantic hints pass through unchanged.

**Why:** drf-spectacular does not natively resolve Pydantic `BaseModel` in `responses=...`. Without this bridge, Pydantic schemas produce broken OpenAPI docs or require manual schema dict construction at every call site.

**Validation:** Import all four functions and confirm they produce valid JSON Schema dicts:
```bash
uv run python -c "
from config.spectacular_pydantic import pydantic_schema, pydantic_array_schema, pydantic_one_of_schema, as_openapi_response
from pydantic import BaseModel

class Dummy(BaseModel):
    name: str
    value: int

print(pydantic_schema(Dummy))
print(pydantic_array_schema(Dummy))
print('OK')
"
```

---

## Phase 8 — Keep-Warm Infrastructure Task

Independent of all other phases.

### 8.1 Keep-Warm Celery Task

**Create:**
| File | Purpose |
|------|---------|
| `DST:utils/tasks.py` | `keep_warm` periodic task for PaaS cold-start prevention |

**Reference:** `SRC:utils/tasks.py`

**What it does:**
1. Runs `SELECT 1` on the default DB connection — warms the Celery worker's DB pool
2. If `HEALTH_PING_URL` env var is set, GETs `<url>/api/v1/health/` — warms the API process and its DB connection too
3. Short time limits (15s hard, 12s soft) — never blocks a worker slot

**Behavior:**
- Uses `urllib.request` (no external dependency) instead of `requests`/`httpx`
- Logs success/failure via structured logging
- HTTP errors (4xx/5xx) logged as warnings, not failures — the ping is a side effect, not a health gate
- No external dependency — only stdlib + Django ORM

**Modify:** `DST:config/settings/celery.py` — add to `CELERY_BEAT_SCHEDULE`:
```python
"keep-warm": {
    "task": "utils.tasks.keep_warm",
    "schedule": 240.0,  # Every 4 minutes
},
```

**Modify:** `DST:.env.prod.example` — add:
```
# Optional: ping the API process to prevent cold starts
# HEALTH_PING_URL=https://your-app.railway.app
```

---

## Phase 9 — Admin UX: Click-to-Copy Fields

Independent of all other phases.

### 9.1 CopyableFieldMixin

**Create:**
| File | Purpose |
|------|---------|
| `DST:utils/admin/__init__.py` | Package init |
| `DST:utils/admin/mixins.py` | `CopyableFieldMixin` for click-to-copy in Unfold admin |
| `DST:utils/admin/css/copy-field.css` | Styles for copyable fields |
| `DST:utils/admin/js/copy-field.js` | Click-to-copy JS with clipboard API + fallback |

**Reference:** `SRC:utils/admin/mixins.py`, `SRC:utils/admin/css/copy-field.css`, `SRC:utils/admin/js/copy-field.js`

**Mixin methods:**
- `copyable_field(value, field_name, css_class, default_display, copy_success_message)` — Base method: renders a `<span>` with `data-code` attribute
- `copyable_email(obj, field_name, field_label)` — Shortcut for email fields (special blue styling via CSS `[data-code*="@"]` selector)
- `copyable_code(obj, field_name, field_label)` — Shortcut for codes/tokens (monospace font via `.code-copy` class)
- `copyable_text(obj, field_name, field_label)` — Shortcut for general text fields

**JS features:**
- `navigator.clipboard.writeText()` primary, textarea `execCommand('copy')` fallback
- Visual feedback: element shows "✓ Copied!" for 1.5s with green background
- Toast notification (bottom-right, auto-dismiss 2s)
- Error state: "✗ Failed" with red background

**CSS features:**
- `.copy-field` — standard copyable (subtle border, hover highlight, cursor pointer)
- `.code-copy` — monospace variant for codes/tokens
- `.copy-field[data-code*="@"]` — auto-detected email styling (blue tint)
- `.copied` / `.error` — success/failure state classes

**Usage in any admin class:**
```python
from unfold.admin import ModelAdmin
from utils.admin.mixins import CopyableFieldMixin

@admin.register(User)
class UserAdmin(CopyableFieldMixin, ModelAdmin):
    list_display = ["username", "display_email"]

    @admin.display(description="Email")
    def display_email(self, obj):
        return self.copyable_email(obj)
```

**Static files:** The mixin's `Media` class references `utils/admin/css/copy-field.css` and `utils/admin/js/copy-field.js`. These must be placed where Django's `collectstatic` can find them. Two options:
1. Place in `DST:utils/admin/css/` and `DST:utils/admin/js/` with `utils` listed in `INSTALLED_APPS` (already the case) — Django finds them via the app's own directory
2. Or place in `DST:static/utils/admin/css/` and `DST:static/utils/admin/js/` as project-level static files

Option 1 is cleaner — the assets live next to the mixin that declares them.

**Modify:** `DST:config/settings/paths.py` — ensure `STATICFILES_FINDERS` includes `django.contrib.staticfiles.finders.AppDirectoriesFinder` (likely already present).

**Note:** Strip the `console.log` debug statements from the JS before committing to the template. They're useful during development but noisy in production.

---

## Phase 10 — Celery Priority Queues & Task Routing

Independent of all other phases.

### 10.1 Three-Queue Architecture

**Modify:** `DST:config/settings/celery.py` — replace the commented-out placeholder queues with the production-ready three-queue setup.

**Reference:** `SRC:config/settings/celery.py`

**Replace the `CELERY_TASK_QUEUES` section with:**
```python
from kombu import Queue

CELERY_TASK_DEFAULT_QUEUE = 'default'

CELERY_TASK_QUEUES = (
    Queue('realtime', routing_key='realtime'),
    Queue('default', routing_key='default'),
    Queue('slow', routing_key='slow'),
)
```

**Queue purpose:**
| Queue | SLA | Use for |
|-------|-----|---------|
| `realtime` | < 1s | WebSocket-triggered work, game timers, phase transitions, anything the user is actively waiting on |
| `default` | < 30s | Notifications, membership events, general background work |
| `slow` | minutes | Video processing, bulk stats, exports, heavy analytics, nightly cleanups |

**Starter task routes (template-appropriate only):**
```python
CELERY_TASK_ROUTES = {
    # Nightly maintenance → slow queue (don't block default workers)
    'accounts.tasks.flush_expired_jwt_tokens': {'queue': 'slow'},
    'accounts.tasks.process_permanent_deletions': {'queue': 'slow'},

    # Everything else → default (projects add routes as they add tasks)
}
```

**Add to worker comments in the file:**
```python
# Run workers per queue:
#   celery -A config.celery.app worker -Q realtime --concurrency=4
#   celery -A config.celery.app worker -Q default  --concurrency=8
#   celery -A config.celery.app worker -Q slow     --concurrency=2
#
# Or a single worker consuming all:
#   celery -A config.celery.app worker -Q realtime,default,slow --concurrency=8
```

**Modify:** `DST:docker/docker-compose.prod.yml` (if it exists) — split the single Celery worker into two services:
- `celery-worker`: consumes `default,slow` with higher concurrency
- `celery-realtime`: consumes `realtime` with lower concurrency, separate process so slow tasks never block real-time work

---

### 10.2 Add `kombu` to Dependencies

**Modify:** `DST:pyproject.toml` — add `kombu` to dependencies (it's a Celery dependency already installed, but declaring it explicitly makes the `Queue` import self-documenting).

**Note:** `kombu` is already installed as a transitive dependency of Celery. The explicit dependency declaration is for import clarity, not installation.

---

## Phase 11 — Enhanced Model Mixins

Independent of all other phases.

### 11.1 SoftDeleteModel Upgrade

**Modify:** `DST:utils/models/_softdelete.py` — replace the minimal implementation with the full `SoftDeleteQuerySet` + `SoftDeleteManager` + enhanced `SoftDeleteModel`.

**Reference:** `SRC:utils/models/_softdelete.py`

**Current Katesthe version (minimal):**
- `SoftDeleteModel` with `is_deleted` flag and overridden `delete()`
- No custom manager, no queryset, no `hard_delete()`, no `alive_objects`

**Upgrade to:**
- `SoftDeleteQuerySet` with `.alive()`, `.dead()`, bulk soft-delete via `.delete()`, `.hard_delete()`
- `SoftDeleteManager` that returns only non-deleted rows via `get_queryset().alive()`
- `SoftDeleteModel` with:
  - `objects = models.Manager()` — default manager returns ALL rows (admin-safe)
  - `alive_objects = SoftDeleteManager()` — explicit opt-in to filtered queryset
  - `delete()` — soft-delete via `save(update_fields=["is_deleted"])` (efficient, no full-model save)
  - `hard_delete()` — permanent deletion bypass
  - Returns `(count, {label: count})` matching Django's `delete()` return signature

**Key design decision:** The default `objects` manager is intentionally NOT filtered. This prevents:
- Admin breaking (admin uses `objects` by default)
- Migration issues
- Surprise missing rows in existing code

Code that wants only alive rows explicitly uses `MyModel.alive_objects.all()`.

**Update exports in:** `DST:utils/models/__init__.py` — add `SoftDeleteQuerySet` and `SoftDeleteManager` to re-exports.

**Validation:** Existing tests that use `SoftDeleteModel` must still pass — the default `objects` manager behavior is unchanged (returns all rows).

### 11.2 BooleanChoices Base Class

**Create:**
| File | Purpose |
|------|---------|
| `DST:utils/models/choices.py` | `BooleanChoices` base class for boolean-valued TextChoices |

**Reference:** `SRC:utils/models/choices.py`

**What it does:** A `models.Choices` subclass for boolean-valued members. Provides a clean pattern for Yes/No, True/False, Active/Inactive select fields:

```python
class YesNoChoices(BooleanChoices):
    YES = True, "Yes"
    NO = False, "No"
```

**Update:** `DST:utils/models/__init__.py` — add `BooleanChoices` to re-exports.

---

## Phase 12 — Notification System Engine

Replaces the existing simple `notifications` app (email-only, event-code registry, 2 templates) with a full notification system engine. The existing app has a `transactional_email.py` service and a single Celery task — the new system adds in-app notifications with WebSocket delivery, a type/category registry, two-level user preferences, deduplication, delivery logging, role-based visibility, and a full REST API.

**Migration path:** The existing `notifications` app's transactional email capability is preserved as a standalone utility. The new `notification_system` app runs alongside it. The existing `notifications` app can be deprecated once all email events are migrated to the new system's dispatch pipeline.

### 12.1 Constants Module

**Create:**
| File | Purpose |
|------|---------|
| `DST:notification_system/__init__.py` | App package |
| `DST:notification_system/constants.py` | Priority, Channel, DeliveryStatus enums |

**Reference:** `SRC:notification_system/constants.py`

**What it provides:**
- `Priority` — `LOW`, `NORMAL`, `HIGH`, `CRITICAL` (IntegerChoices with `MEDIUM = NORMAL` backward-compat alias)
- `Channel` — `IN_APP`, `EMAIL` (TextChoices)
- `DeliveryStatus` — `PENDING`, `SENT`, `FAILED` (TextChoices)

These are referenced by models, dispatch service, and delivery logging. No domain-specific content — copy as-is.

---

### 12.2 Models — Four Tables

**Create:**
| File | Purpose |
|------|---------|
| `DST:notification_system/models/__init__.py` | Re-exports |
| `DST:notification_system/models/_notification.py` | Core `Notification` model |
| `DST:notification_system/models/_notification_preference.py` | Per-type user preference |
| `DST:notification_system/models/_category_preference.py` | Per-category user preference |
| `DST:notification_system/models/_delivery_log.py` | Delivery attempt logging |

**Reference:**
- `SRC:notification_system/models/_notification.py`
- `SRC:notification_system/models/_notification_preference.py`
- `SRC:notification_system/models/_category_preference.py`
- `SRC:notification_system/models/_delivery_log.py`

#### 12.2a `Notification` model

Fields: `user` (FK), `notification_type` (CharField 100), `title`, `message` (TextField), `payload` (JSONField), `action_url`, `action_text`, `priority` (IntegerField from Priority), `read` (bool), `read_at` (DateTimeField null), `deleted_at` (DateTimeField null — soft delete), `expires_at` (DateTimeField null), `actor_id` (IntegerField null), `content_type` (CharField null — generic relation target type), `object_id` (IntegerField null — generic relation target PK), `email_failed` (bool), `dedupe_key` (CharField null).

Inherits from `TimeStampedModel` (already in Katesthe `utils/models/`).

**Indexes (5):** `(user, read, deleted_at)`, `(user, notification_type)`, `(user, created)`, `(notification_type,)`, `(expires_at,)`.

**Constraint:** `UniqueConstraint(fields=["user", "dedupe_key"], condition=Q(dedupe_key__isnull=False), name="unique_user_dedupe_key")` — enables deduplication window.

#### 12.2b `UserNotificationPreference` model

Fields: `user` (FK), `notification_type` (CharField 100), `in_app` (BooleanField default True), `email` (BooleanField default False).

**Constraint:** `unique_together = ("user", "notification_type")`.

Related name: `notification_preferences` on User.

#### 12.2c `UserNotificationCategoryPreference` model

Fields: `user` (FK), `category` (CharField 50), `enabled` (BooleanField default True).

**Constraint:** `UniqueConstraint(fields=["user", "category"], name="unique_user_category_pref")`.

Related name: `notification_category_preferences` on User.

#### 12.2d `NotificationDeliveryLog` model

Fields: `notification` (FK), `channel` (CharField from Channel choices), `status` (CharField from DeliveryStatus), `created_at` (auto_now_add), `sent_at` (DateTimeField null), `error_message` (TextField blank), `metadata` (JSONField default dict).

Tracks per-channel delivery attempts (IN_APP sent, EMAIL sent/failed with error). Essential for debugging and monitoring.

---

### 12.3 Notification Type Registry

**Create:**
| File | Purpose |
|------|---------|
| `DST:notification_system/registry.py` | `NotificationTypeRegistry` class + `CATEGORIES` dict |
| `DST:notification_system/services/_registry.py` | Backward-compat re-export shim |

**Reference:** `SRC:notification_system/registry.py`, `SRC:notification_system/services/_registry.py`

**What it provides:**
- `NotificationTypeConfig` — dataclass with: `key`, `priority`, `default_in_app`, `default_email`, `critical`, `visible_to_roles` (list), `category`, `label`
- `CATEGORIES` — `dict[str, str]` mapping category IDs to display labels. **Ship empty:** `CATEGORIES = {}`. Projects populate this when they register their types.
- `NotificationTypeRegistry` — class-level registry with:
  - `register(config: NotificationTypeConfig)` — add a type
  - `get(key: str) -> NotificationTypeConfig | None`
  - `get_or_default(key: str) -> NotificationTypeConfig` — returns a safe fallback for unknown types
  - `all_keys() -> list[str]`
  - `get_types_by_category() -> dict[str, list[NotificationTypeConfig]]`

**What to strip from Rhitoric:**
- Remove `register_core_types()` function and all 35 type registrations (game, elearning, account, AI types). Ship with zero registered types.
- Add a docstring example showing how to register project-specific types:
  ```python
  # In your app's apps.py ready():
  from notification_system.registry import NotificationTypeRegistry, NotificationTypeConfig, CATEGORIES
  
  CATEGORIES.update({"account": "Account", "billing": "Billing"})
  
  NotificationTypeRegistry.register(NotificationTypeConfig(
      key="account.welcome",
      priority="normal",
      default_in_app=True,
      default_email=True,
      critical=False,
      visible_to_roles=[],
      category="account",
      label="Welcome notification",
  ))
  ```

---

### 12.4 Pluggable Adapters

**Create:**
| File | Purpose |
|------|---------|
| `DST:notification_system/adapters.py` | Default `should_skip_notification_for_user()` and `get_user_roles()` |

**Reference:** `SRC:notification_system/adapters.py`

**What to strip:**
- Remove `_AI_NOTIFICATION_TYPES` frozenset and the elearning AI preference check from `should_skip_notification_for_user()`. The default implementation should return `False` (never skip). Add a docstring explaining how to override via `NOTIFICATION_SHOULD_SKIP_FOR_USER` setting.
- Remove `ClubMembership` import from `get_user_roles()`. The default implementation returns Django group names only:
  ```python
  def get_user_roles(user) -> list:
      if not user or not user.is_authenticated:
          return []
      return list(user.groups.values_list("name", flat=True))
  ```
  Add a docstring explaining how to override via `NOTIFICATION_GET_USER_ROLES` setting to add project-specific role sources.

Both adapters are resolved at runtime via `import_string()` from settings, so projects override them by pointing the setting to their own function — zero coupling.

---

### 12.5 Dispatch Service (Core Engine)

**Create:**
| File | Purpose |
|------|---------|
| `DST:notification_system/services/__init__.py` | Re-exports |
| `DST:notification_system/services/_dispatch.py` | `dispatch()` — the main notification entry point |

**Reference:** `SRC:notification_system/services/_dispatch.py`

**What `dispatch()` does (in order):**
1. Verify user exists (get_user_model lookup — raises early if not found)
2. Call pluggable `should_skip_notification_for_user()` adapter
3. Look up `NotificationTypeConfig` from registry (`get_or_default` for unknown types)
4. Check deduplication — if `dedupe_key` provided, check for existing notification within `NOTIFICATION_DEDUPE_WINDOW_MINUTES` (default 5). Skip if duplicate found.
5. Create `Notification` in `transaction.atomic()`
6. Create `NotificationDeliveryLog` for IN_APP channel
7. Check category preference (enabled?) and type preference (in_app? email?)
8. If in_app enabled: fire WebSocket delivery via `send_notification_to_user()` (fire-and-forget, logged but not blocking)
9. If email enabled: enqueue `send_notification_email_task` via `transaction.on_commit`
10. Return the `Notification` instance (or `None` if skipped/deduped)

**What to strip:** Nothing domain-specific in the dispatch logic itself — it's fully generic. Copy as-is, just ensure the import path for `send_notification_to_user` matches the template layout.

---

### 12.6 Action Services

**Create:**
| File | Purpose |
|------|---------|
| `DST:notification_system/services/_actions.py` | `mark_notification_read()`, `mark_all_notifications_read()`, `soft_delete_notification()` |

**Reference:** `SRC:notification_system/services/_actions.py`

Three simple service functions — all scoped to `user` for IDOR safety. Copy as-is, no domain-specific content.

---

### 12.7 Preference Services

**Create:**
| File | Purpose |
|------|---------|
| `DST:notification_system/services/_preferences.py` | `update_notification_preferences()`, `bootstrap_notification_preferences()` |

**Reference:** `SRC:notification_system/services/_preferences.py`

- `update_notification_preferences(user, category_preferences, type_preferences)` — bulk upsert via `bulk_create(update_conflicts=True)`. Validates against registered categories and types.
- `bootstrap_notification_preferences(user)` — creates all default preferences for a new user (called from signal or management command). Idempotent via `ignore_conflicts=True`.

Copy as-is — logic is registry-driven, no hardcoded domain types.

---

### 12.8 Broadcast Service

**Create:**
| File | Purpose |
|------|---------|
| `DST:notification_system/services/_broadcast.py` | `broadcast_notifications()` — admin bulk-create |

**Reference:** `SRC:notification_system/services/_broadcast.py`

Loops over user IDs and calls `dispatch()` for each. Used by admin actions to send notifications to multiple users. Copy as-is.

---

### 12.9 WebSocket Utilities

**Create:**
| File | Purpose |
|------|---------|
| `DST:notification_system/utils.py` | `send_notification_to_user()`, `_serialize_payload_for_storage()` |

**Reference:** `SRC:notification_system/utils.py`

- `send_notification_to_user(user_id, notification)` — sends `notification_new` event to `user_{id}` channel group via `channel_layer.group_send()`. Returns bool. Catches exceptions to avoid blocking dispatch.
- `_serialize_payload_for_storage(payload)` — converts UUID and datetime objects to strings for JSONField storage. Used by dispatch before creating the Notification.

**Dependency:** Requires Django Channels (`channels`) in the project. If the template doesn't include Channels, guard the import and degrade gracefully (in-app delivery skipped, email-only).

---

### 12.10 WebSocket Consumer

**Create:**
| File | Purpose |
|------|---------|
| `DST:notification_system/consumers.py` | `NotificationConsumer` for WebSocket delivery |

**Reference:** `SRC:notification_system/consumers.py`

**What it provides:**
- JWT authentication on connect (reuses the WebSocket JWT middleware from Phase 5)
- Joins `user_{id}` channel group
- Heartbeat every 30 seconds (keepalive)
- Rate limiting (10 messages/sec)
- `auth_rotate` handler (token refresh mid-connection)
- `notification_new` event handler — forwards notification payload to the WebSocket client with whitelisted keys only

**What to strip:**
- Remove all domain-specific no-op handlers: `player_joined`, `player_left_game`, `game_abandoned`, `game_completed`, `vote_cast`. These are Rhitoric game events routed through the consumer that it ignores — they should not exist in the template.
- Close codes: keep `4401` (auth failed), `4001` (unauthenticated). Remove any game-specific close codes if present.

**Routing:** Add to the project's ASGI routing:
```python
# config/asgi.py or config/routing.py
websocket_urlpatterns = [
    path("ws/notifications/", NotificationConsumer.as_asgi()),
]
```

---

### 12.11 Email Task

**Create:**
| File | Purpose |
|------|---------|
| `DST:notification_system/tasks/__init__.py` | Package init |
| `DST:notification_system/tasks/_email.py` | `send_notification_email_task` |

**Reference:** `SRC:notification_system/tasks/_email.py`

**What it does:**
- Reads the Notification from the DB (using `read_from_primary()` if DB routing is configured — already in Katesthe)
- Sends email via Django's `EmailMultiAlternatives`
- Updates `NotificationDeliveryLog` with SENT/FAILED status
- PII redaction in error messages

**What to strip:**
- Replace hardcoded `from_email` fallback from `"noreply@rhitoric.com"` to `settings.DEFAULT_FROM_EMAIL`
- The task uses `autoretry_for=(Exception,), max_retries=3, retry_backoff=True, retry_jitter=True` — keep this pattern.

---

### 12.12 Selectors

**Create:**
| File | Purpose |
|------|---------|
| `DST:notification_system/selectors/__init__.py` | Re-exports |
| `DST:notification_system/selectors/_notification.py` | `get_user_notifications_queryset()`, `get_unread_count()`, `get_notification_for_user()`, `get_visible_notification_type_keys()` |
| `DST:notification_system/selectors/_preference.py` | `get_user_preferences()`, `is_category_enabled_for_user()`, `get_effective_preference()`, `get_grouped_preferences()` |
| `DST:notification_system/selectors/_user_roles.py` | `get_user_roles()` — pluggable role resolver with cache |

**Reference:**
- `SRC:notification_system/selectors/_notification.py`
- `SRC:notification_system/selectors/_preference.py`
- `SRC:notification_system/selectors/_user_roles.py`

Key features:
- **Retention-based filtering:** `_retention_cutoff()` uses `NOTIFICATION_RETENTION_DAYS` setting (default 90). Old notifications excluded from list/count.
- **Role-based visibility:** `_visible_type_keys_for_user()` filters notification types by `visible_to_roles`. Fail-closed — empty registry = empty set.
- **Grouped preferences:** `get_grouped_preferences()` returns all types organized by category with effective (in_app, email) per type, incorporating per-type overrides and registry defaults. Ready-to-render for a preferences UI.
- **User role caching:** `get_user_roles()` in `_user_roles.py` caches per-user roles for 60s via Django cache, preventing repeated DB queries within the same request cycle.

Copy all as-is — all logic is registry-driven. The pluggable `NOTIFICATION_GET_USER_ROLES` setting path is already handled.

---

### 12.13 Serializers

**Create:**
| File | Purpose |
|------|---------|
| `DST:notification_system/serializers/__init__.py` | Re-exports |
| `DST:notification_system/serializers/_notification.py` | `NotificationListSerializer`, `NotificationDetailSerializer` |
| `DST:notification_system/serializers/_preference.py` | `UserNotificationPreferenceSerializer`, `NotificationPreferencesGroupedSerializer` |
| `DST:notification_system/serializers/_category_preference.py` | `NotificationPreferencesUpdateSerializer`, `NotificationTypePreferenceSerializer` |

**Reference:**
- `SRC:notification_system/serializers/_notification.py`
- `SRC:notification_system/serializers/_preference.py`
- `SRC:notification_system/serializers/_category_preference.py`

Standard DRF ModelSerializers and plain Serializers. No domain-specific content — copy as-is.

---

### 12.14 Controllers (REST API)

**Create:**
| File | Purpose |
|------|---------|
| `DST:notification_system/controllers/__init__.py` | Package init |
| `DST:notification_system/controllers/_list.py` | `NotificationListView`, `NotificationDetailView`, `UnreadCountView` |
| `DST:notification_system/controllers/_actions.py` | `MarkReadView`, `MarkAllReadView`, `NotificationSoftDeleteView` |
| `DST:notification_system/controllers/_preferences.py` | `NotificationPreferencesListView`, `NotificationPreferencesUpdateView` |

**Reference:**
- `SRC:notification_system/controllers/_list.py`
- `SRC:notification_system/controllers/_actions.py`
- `SRC:notification_system/controllers/_preferences.py`

**8 API endpoints:**

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/notifications/` | Paginated list with filters (type, read, retention_days) |
| GET | `/notifications/{pk}/` | Single notification detail |
| GET | `/notifications/unread_count/` | Unread count for badge UI |
| POST | `/notifications/{pk}/mark_read/` | Mark one as read |
| POST | `/notifications/mark_all_read/` | Mark all as read |
| DELETE | `/notifications/{pk}/delete/` | Soft delete |
| GET | `/notifications/preferences/` | Grouped preferences by category |
| PUT | `/notifications/preferences/update/` | Update category + type preferences |

All views use `IsAuthenticated` permission. IDOR protection is built into the selectors (scope to `request.user`). All have `@extend_schema` OpenAPI annotations.

**What to strip:**
- Remove `NotificationActionThrottle` and `NotificationBulkThrottle` imports if those throttle classes don't exist in the template yet. Replace with the template's generic throttle classes or remove `throttle_classes` and let the project add them.
- Remove `from errors.catalog import NOTIFICATION__NOT_FOUND` if the error catalog doesn't have this code yet. Add the error code to the template's error catalog, or use a plain string until it's registered.
- The `parse_page_params` utility from `utils.pagination` should already exist in Katesthe (from Depadrive backport). Verify before implementation.

---

### 12.15 URL Configuration

**Create:**
| File | Purpose |
|------|---------|
| `DST:notification_system/urls/__init__.py` | URL patterns |

**Reference:** `SRC:notification_system/urls/__init__.py`

**Mount in project URLs:**
```python
# config/urls.py
urlpatterns = [
    ...
    path("api/v1/", include("notification_system.urls")),
]
```

---

### 12.16 Management Command

**Create:**
| File | Purpose |
|------|---------|
| `DST:notification_system/management/__init__.py` | Package |
| `DST:notification_system/management/commands/__init__.py` | Package |
| `DST:notification_system/management/commands/bootstrap_notification_preferences.py` | Backfill preferences for existing users |

**Reference:** `SRC:notification_system/management/commands/bootstrap_notification_preferences.py`

**What it does:** For users created before the notification system was added, creates `UserNotificationPreference` and `UserNotificationCategoryPreference` rows with registry defaults. Features:
- `--dry-run` flag
- `--batch-size` for large user bases
- Batch-level `bulk_create(ignore_conflicts=True)` for idempotency
- Efficient: single query to find users needing preferences, batch fetch existing prefs

Copy as-is — logic is registry-driven. If no types are registered, it exits with "Nothing to bootstrap."

---

### 12.17 App Configuration

**Create:**
| File | Purpose |
|------|---------|
| `DST:notification_system/apps.py` | Django AppConfig |

**Reference:** `SRC:notification_system/apps.py`

```python
from django.apps import AppConfig

class NotificationSystemConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "notification_system"
    verbose_name = "Notification System"

    def ready(self):
        # Projects register their notification types in their own app's ready().
        # Example: from myapp.notifications import register_types; register_types()
        pass
```

**What to strip:** Remove `register_core_types()` call — the template ships with an empty registry.

**Add to** `DST:config/settings/django.py` `INSTALLED_APPS`:
```python
INSTALLED_APPS = [
    ...
    "notification_system",
]
```

---

### 12.18 Settings Module

**Create:**
| File | Purpose |
|------|---------|
| `DST:config/settings/notification_system.py` | Notification system settings |

**Reference:** `SRC:config/settings/notification_system.py`

**Settings:**
```python
NOTIFICATION_RETENTION_DAYS = 90
NOTIFICATION_DEDUPE_WINDOW_MINUTES = 5
NOTIFICATION_GET_USER_ROLES = "notification_system.adapters.get_user_roles"
NOTIFICATION_SHOULD_SKIP_FOR_USER = "notification_system.adapters.should_skip_notification_for_user"
```

All four are overridable. The dotted paths resolve at runtime via `import_string()`, so projects swap in their own implementations without touching the notification system code.

**Import in** `DST:config/settings/__init__.py`:
```python
from config.settings.notification_system import *
```

---

### 12.19 Error Catalog Entry

**Modify:** `DST:errors/catalog.py`

**Add:**
```python
NOTIFICATION__NOT_FOUND = "NOTIFICATION__NOT_FOUND"
```

Follows the `DOMAIN__ERROR_NAME` convention from `api.md`.

---

### 12.20 Migrations

**Create:** `DST:notification_system/migrations/0001_initial.py`

Run `uv run python manage.py makemigrations notification_system` after all models are in place. This generates a single initial migration with all four tables and their indexes/constraints.

---

### Phase 12 — Validation

```bash
# Import smoke test
uv run python -c "
from notification_system.registry import NotificationTypeRegistry, CATEGORIES
from notification_system.models import Notification, UserNotificationPreference
from notification_system.services._dispatch import dispatch
from notification_system.services._actions import mark_notification_read
from notification_system.services._preferences import bootstrap_notification_preferences
from notification_system.selectors._notification import get_user_notifications_queryset
from notification_system.consumers import NotificationConsumer
print('Phase 12 imports OK')
print(f'Registered types: {len(NotificationTypeRegistry.all_keys())}')
print(f'Categories: {len(CATEGORIES)}')
"

# Migration check
uv run python manage.py makemigrations notification_system --check --dry-run

# Management command exists
uv run python manage.py bootstrap_notification_preferences --dry-run
```

### Phase 12 — File Inventory

| # | File | Status |
|---|------|--------|
| 1 | `notification_system/__init__.py` | Create |
| 2 | `notification_system/apps.py` | Create |
| 3 | `notification_system/constants.py` | Create |
| 4 | `notification_system/registry.py` | Create |
| 5 | `notification_system/adapters.py` | Create |
| 6 | `notification_system/utils.py` | Create |
| 7 | `notification_system/consumers.py` | Create |
| 8 | `notification_system/models/__init__.py` | Create |
| 9 | `notification_system/models/_notification.py` | Create |
| 10 | `notification_system/models/_notification_preference.py` | Create |
| 11 | `notification_system/models/_category_preference.py` | Create |
| 12 | `notification_system/models/_delivery_log.py` | Create |
| 13 | `notification_system/services/__init__.py` | Create |
| 14 | `notification_system/services/_registry.py` | Create |
| 15 | `notification_system/services/_dispatch.py` | Create |
| 16 | `notification_system/services/_actions.py` | Create |
| 17 | `notification_system/services/_preferences.py` | Create |
| 18 | `notification_system/services/_broadcast.py` | Create |
| 19 | `notification_system/selectors/__init__.py` | Create |
| 20 | `notification_system/selectors/_notification.py` | Create |
| 21 | `notification_system/selectors/_preference.py` | Create |
| 22 | `notification_system/selectors/_user_roles.py` | Create |
| 23 | `notification_system/serializers/__init__.py` | Create |
| 24 | `notification_system/serializers/_notification.py` | Create |
| 25 | `notification_system/serializers/_preference.py` | Create |
| 26 | `notification_system/serializers/_category_preference.py` | Create |
| 27 | `notification_system/controllers/__init__.py` | Create |
| 28 | `notification_system/controllers/_list.py` | Create |
| 29 | `notification_system/controllers/_actions.py` | Create |
| 30 | `notification_system/controllers/_preferences.py` | Create |
| 31 | `notification_system/urls/__init__.py` | Create |
| 32 | `notification_system/tasks/__init__.py` | Create |
| 33 | `notification_system/tasks/_email.py` | Create |
| 34 | `notification_system/management/__init__.py` | Create |
| 35 | `notification_system/management/commands/__init__.py` | Create |
| 36 | `notification_system/management/commands/bootstrap_notification_preferences.py` | Create |
| 37 | `notification_system/migrations/0001_initial.py` | Generate |
| 38 | `config/settings/notification_system.py` | Create |
| 39 | `config/settings/__init__.py` | Modify (add import) |
| 40 | `config/settings/django.py` | Modify (add to INSTALLED_APPS) |
| 41 | `config/urls.py` | Modify (add URL include) |
| 42 | `errors/catalog.py` | Modify (add NOTIFICATION__NOT_FOUND) |

---

## Updated Dependency Graph

```
Phase 1-6: (unchanged — see original graph above)

Phase 7 (Pydantic-Spectacular Bridge): independent
Phase 8 (Keep-Warm Task): independent
Phase 9 (Admin Copy Mixin): independent
Phase 10 (Celery Queues): independent
Phase 11 (Model Mixins): independent
Phase 12 (Notification System): independent
  └─ Optional dep on Phase 5 (WebSocket auth) for consumer JWT auth
     Without Phase 5: consumer can use simpler auth or be excluded

Phases 7-12 can all run in parallel with each other and with Phase 4.
```

---

## Updated Validation Gate

Add to the existing validation commands:

```bash
# Phase 7 smoke test
uv run python -c "
from config.spectacular_pydantic import pydantic_schema, as_openapi_response
print('Phase 7 imports OK')
"

# Phase 8 smoke test
uv run python -c "
from utils.tasks import keep_warm
print('Phase 8 imports OK')
"

# Phase 9 smoke test
uv run python -c "
from utils.admin.mixins import CopyableFieldMixin
print('Phase 9 imports OK')
"

# Phase 11 smoke test
uv run python -c "
from utils.models import SoftDeleteModel, SoftDeleteManager, SoftDeleteQuerySet
from utils.models.choices import BooleanChoices
print('Phase 11 imports OK')
"

# Phase 12 smoke test
uv run python -c "
from notification_system.registry import NotificationTypeRegistry, CATEGORIES
from notification_system.models import Notification, UserNotificationPreference
from notification_system.services._dispatch import dispatch
from notification_system.services._actions import mark_notification_read
from notification_system.services._preferences import bootstrap_notification_preferences
from notification_system.selectors._notification import get_user_notifications_queryset
from notification_system.consumers import NotificationConsumer
print('Phase 12 imports OK')
print(f'Registered types: {len(NotificationTypeRegistry.all_keys())}')
print(f'Categories: {len(CATEGORIES)}')
"
```

---

## What NOT to Do

1. **Do not copy game, AI, or elearning domain logic.** Only extract generic infrastructure patterns.
2. **Do not copy domain-specific throttle classes** (GameActionThrottle, AIMessageThrottle, QuizAttemptThrottle, etc.). Start with ~14 universal throttles. Projects add domain-specific ones later.
3. **Do not copy domain-specific permissions** (IsClubFounder, IsAIServiceAuthenticated, CanVoteAvA, etc.). The template should include only `IsSuperUserOnly` and `CurrentUserOrSuperUser` as examples.
4. **Do not copy CacheOps configuration.** That's project-specific caching policy, not a template pattern.
5. **Do not copy Rhitoric's 35 notification type registrations.** The template ships with an empty registry. Projects register their own types in their app's `AppConfig.ready()`.
6. **Do not copy the admin_api app.** Admin panel patterns are project-specific.
7. **Do not break existing tests.** The RS256 migration will change token format — update test assertions accordingly.
8. **Do not make `cryptography` optional.** RS256 is the new default — it's a required dependency.
9. **Do not copy the `SameSite=None` pattern for production.** The template should default to `Lax`. Projects doing cross-origin auth change it themselves.
10. **Do not add `JWT_RSA_PREVIOUS_PUBLIC_KEY` to `.env.local.example`.** Key rotation is a production concern — don't clutter the dev setup.
11. **Do not copy MuxPlaybackMixin.** It's domain-specific to video hosting. Projects add it when they integrate Mux.
12. **Do not copy domain-specific Celery beat entries.** The template should ship with only `keep-warm` and `flush-expired-jwt-tokens`. Projects add domain-specific periodic tasks as they build features.
13. **Do not copy domain-specific task routes.** The template provides the three-queue skeleton and 2 starter routes. Projects map their own tasks to queues.
14. **Do not leave `console.log` in production JS.** Strip debug statements from `copy-field.js` before committing.
15. **Do not copy Rhitoric's `should_skip_notification_for_user()` elearning/AI logic.** The template adapter returns `False` (never skip). Projects override via the `NOTIFICATION_SHOULD_SKIP_FOR_USER` setting.
16. **Do not copy `ClubMembership` role resolution into the template's `get_user_roles()`.** The template adapter uses Django groups only. Projects add domain-specific role sources via the `NOTIFICATION_GET_USER_ROLES` setting.
17. **Do not copy domain-specific WebSocket consumer handlers** (`player_joined`, `game_abandoned`, `vote_cast`, etc.). The template consumer handles only `notification_new`, `auth_rotate`, and heartbeat.
18. **Do not hardcode `noreply@rhitoric.com`** in the email task. Use `settings.DEFAULT_FROM_EMAIL`.
