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

**What to add:** 22 patterns across 5 phases. Phases are ordered by dependency — Phase 1 (RS256 JWT) must be complete before Phase 2 (Cookie auth) which must be complete before Phase 3 (WebSocket auth).

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

## What NOT to Do

1. **Do not copy game, AI, or elearning domain logic.** Only extract generic infrastructure patterns.
2. **Do not copy domain-specific throttle classes** (GameActionThrottle, AIMessageThrottle, QuizAttemptThrottle, etc.). Start with ~14 universal throttles. Projects add domain-specific ones later.
3. **Do not copy domain-specific permissions** (IsClubFounder, IsAIServiceAuthenticated, CanVoteAvA, etc.). The template should include only `IsSuperUserOnly` and `CurrentUserOrSuperUser` as examples.
4. **Do not copy CacheOps configuration.** That's project-specific caching policy, not a template pattern.
5. **Do not copy notification type registry.** The template's notification system (from Depadrive backport) is simpler and sufficient for bootstrapping.
6. **Do not copy the admin_api app.** Admin panel patterns are project-specific.
7. **Do not break existing tests.** The RS256 migration will change token format — update test assertions accordingly.
8. **Do not make `cryptography` optional.** RS256 is the new default — it's a required dependency.
9. **Do not copy the `SameSite=None` pattern for production.** The template should default to `Lax`. Projects doing cross-origin auth change it themselves.
10. **Do not add `JWT_RSA_PREVIOUS_PUBLIC_KEY` to `.env.local.example`.** Key rotation is a production concern — don't clutter the dev setup.
