# Backport Plan: Depadrive-core patterns into Katesthe-core

**Source project:** `/home/tmpusr/Documents/github/dp/Depadrive-core`
**Target project:** `/home/tmpusr/dev/Katesthe-core`
**Date:** 2026-07-02
**Author:** AI-assisted

---

## Overview

Katesthe-core is a Django bootstrap template. Depadrive-core was built on top of it and evolved production-hardened patterns over ~1 year. This plan backports those patterns into the template so future projects start with them.

**What already exists (do NOT recreate):** Pydantic settings, primary/replica DB routing (`config/db_router.py`, `config/db_utils.py`, `config/middleware/db_consistency.py`), Unfold admin, Factory Boy factories, layered app scaffold (`starttemplateapp`), Loguru logging (`config/logger.py`), Celery infrastructure (app + beat + worker docker services).

**What to add:** 23 patterns across 3 phases. Phases are ordered by dependency — Phase 1 must be complete before Phase 2, as later patterns depend on the error catalog, envelope helpers, and exception handler.

---

## Reference Convention

Throughout this plan, source files are referenced as:
- `SRC:path` = `/home/tmpusr/Documents/github/dp/Depadrive-core/path`
- `DST:path` = `/home/tmpusr/dev/Katesthe-core/path`

**Do NOT copy files verbatim.** Depadrive-core has domain-specific logic (assistance, depanneurs, reviews, etc.). Extract only the generic pattern and adapt it to a clean template context. Strip all domain-specific error codes, keep only universal ones.

---

## Phase 1 — Core Infrastructure

These are foundational. Everything in Phase 2+ depends on them. Implement in this exact order.

### 1.1 Error Catalog + AppAPIError

**Create:**
| File | Purpose |
|------|---------|
| `DST:errors/__init__.py` | Package init, re-export `E` alias and `AppAPIError` |
| `DST:errors/catalog.py` | Error code string constants |
| `DST:errors/exceptions.py` | `AppAPIError(Exception)` class |

**Reference:** `SRC:errors/catalog.py`, `SRC:errors/exceptions.py`

**`errors/catalog.py` — starter codes only (not the full 130 from Depadrive):**
```
# Auth
AUTH__UNAUTHENTICATED
AUTH__TOKEN_EXPIRED
AUTH__TOKEN_INVALID
AUTH__INVALID_CREDENTIALS
AUTH__ACCOUNT_INACTIVE
AUTH__PASSWORD_RESET_DISABLED
AUTH__EMAIL_VERIFICATION_DISABLED

# Validation
VALIDATION__MISSING_FIELD
VALIDATION__INVALID_FORMAT
VALIDATION__INVALID_VALUE

# Permission
PERMISSION__DENIED
PERMISSION__INSUFFICIENT_ROLE

# Resource
RESOURCE__NOT_FOUND
RESOURCE__ALREADY_EXISTS
RESOURCE__CONFLICT

# Rate limit
RATE_LIMIT__EXCEEDED

# Internal
INTERNAL__ERROR
INTERNAL__SERVICE_UNAVAILABLE

# Notification
NOTIFICATION__EMAIL_DELIVERY_FAILED
```

**`errors/exceptions.py` — class signature:**
```python
class AppAPIError(Exception):
    def __init__(self, code: str, status_code: int = 400, details: dict | None = None):
        self.code = code
        self.status_code = status_code
        self.details = details or {}
        super().__init__(code)
```

**Modify:** `DST:config/settings/apps_middlewares.py` — add `'errors'` to `PROJECT_APPS`.

**Validation:** `python -c "from errors.catalog import E; from errors.exceptions import AppAPIError; print('OK')"` via `uv run`.

---

### 1.2 API Response Envelope Helpers

**Create:**
| File | Purpose |
|------|---------|
| `DST:utils/api_response.py` | `ok()` and `err_single()` functions |

**Reference:** `SRC:utils/api_response.py`

**Envelope shape (this is the contract):**
```json
// Success
{"success": true, "data": {...}, "meta": {"request_id": "req_...", "version": "v1"}}

// Error
{"success": false, "error": {"code": "DOMAIN__CONDITION", "details": {}}, "meta": {"request_id": "req_...", "version": "v1"}}

// Validation errors (multiple)
{"success": false, "errors": [...], "meta": {...}}
```

**Functions:**
- `ok(data, request, status=200)` — wraps `data` in success envelope with `request_id` from `request` (falls back to generated ID if middleware not yet installed).
- `err_single(code, request, status=400, details=None)` — wraps error code in failure envelope.

**Validation:** Import from `utils.api_response` succeeds.

---

### 1.3 DRF Error Envelope Normalization

**Create:**
| File | Purpose |
|------|---------|
| `DST:utils/drf_error_envelope.py` | `normalize_validation_detail()`, `validation_error_response()`, `coerce_drf_error_response()` |

**Reference:** `SRC:utils/drf_error_envelope.py`

**What it does:** Converts DRF's native validation error format (`{"field": ["error msg"]}`) into the project envelope format with `VALIDATION__*` codes. Also coerces DRF's built-in error responses (404, 401, etc.) from `{"detail": "Not found."}` into the envelope format.

---

### 1.4 Custom Exception Handler

**Create:**
| File | Purpose |
|------|---------|
| `DST:config/exception_handler.py` | `custom_exception_handler(exc, context)` |

**Reference:** `SRC:config/exception_handler.py`

**Must handle these exception types → envelope mapping:**
| Exception | Catalog Code | HTTP Status |
|-----------|-------------|-------------|
| `AppAPIError` | `exc.code` | `exc.status_code` |
| `Http404` / DRF `NotFound` | `RESOURCE__NOT_FOUND` | 404 |
| `NotAuthenticated` | `AUTH__UNAUTHENTICATED` | 401 |
| JWT `InvalidToken` | `AUTH__TOKEN_INVALID` | 401 |
| `PermissionDenied` | `PERMISSION__DENIED` | 403 |
| `Throttled` | `RATE_LIMIT__EXCEEDED` | 429 (include `retry_after` in details) |
| `DRFValidationError` | `VALIDATION__*` per field | 422 |
| Unhandled `Exception` | `INTERNAL__ERROR` | 500 (log the traceback) |

**Modify:** `DST:config/settings/restframework.py` — add:
```python
REST_FRAMEWORK = {
    ...
    'EXCEPTION_HANDLER': 'config.exception_handler.custom_exception_handler',
}
```

**Validation:** Existing tests still pass. A view that raises `AppAPIError(E.RESOURCE__NOT_FOUND, status_code=404)` returns the correct envelope.

---

### 1.5 Request ID Middleware

**Create:**
| File | Purpose |
|------|---------|
| `DST:config/middleware/request_id.py` | `RequestIdMiddleware` |

**Reference:** `SRC:config/middleware/request_id.py`

**Behavior:**
1. Read `X-Request-ID` header from incoming request, or generate `req_<uuid.hex[:24]>`.
2. Store on `request.request_id`.
3. Set a `ContextVar` so Loguru picks it up in every log line.
4. Add `X-Request-ID` response header.

**Modify:** `DST:config/settings/apps_middlewares.py` — add `'config.middleware.request_id.RequestIdMiddleware'` to `MIDDLEWARE` after `CorsMiddleware`.

**Modify:** `DST:config/logger.py` — update the log format to include the request_id ContextVar when available.

**Validation:** Hit any endpoint, check that the response has `X-Request-ID` header and `meta.request_id` in the envelope body.

---

### 1.6 Health / Readiness Endpoints

**Create:**
| File | Purpose |
|------|---------|
| `DST:config/health.py` | `liveness` and `readiness` views |

**Reference:** `SRC:config/health.py`

**Endpoints:**
- `GET /health/` — returns `200 "ok"` (plain text). No deps probed. Used as liveness check.
- `GET /ready/` — probes DB (`SELECT 1`), Redis (`PING`), Celery broker (`control.ping`). Returns `200` JSON with per-check results when all pass, `503` when any fails.

**Modify:** `DST:config/urls.py` — add:
```python
from config.health import liveness, readiness

urlpatterns = [
    path("health/", liveness),
    path("ready/", readiness),
    ...
]
```

**Modify:** `DST:Dockerfile` — add `HEALTHCHECK CMD curl -f http://localhost:8000/health/ || exit 1`.

**Validation:** `curl http://localhost:8000/health/` returns 200. `curl http://localhost:8000/ready/` returns 200 JSON with `db`, `redis`, `celery` checks.

---

### 1.7 Production Security Hardening

**Modify:**
| File | Change |
|------|--------|
| `DST:config/django/production.py` | Add security settings and boot assertions |

**Reference:** `SRC:config/django/production.py`

**Add these to production.py:**
```python
# Boot-time assertions
assert not DEBUG, "DEBUG must be False in production"
assert ALLOWED_HOSTS and ALLOWED_HOSTS != ["*"], "ALLOWED_HOSTS must be explicit"

# Security headers
SECURE_HSTS_SECONDS = 31536000  # 1 year
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = "same-origin"
X_FRAME_OPTIONS = "DENY"
```

**Also remove any localhost origins from CORS in production** — gate CORS_ALLOWED_ORIGINS on the env.

**Validation:** `DJANGO_SETTINGS_MODULE=config.django.production uv run python -c "import django; django.setup()"` with DEBUG=False and valid ALLOWED_HOSTS succeeds. With DEBUG=True it crashes with AssertionError.

---

### 1.8 CI Workflow (GitHub Actions)

**Create:**
| File | Purpose |
|------|---------|
| `DST:.github/workflows/ci.yml` | Automated test + lint pipeline |

**Reference:** `SRC:.github/workflows/ci.yml`

**Job steps:**
1. Checkout
2. Set up Python 3.12
3. Install uv
4. `uv sync`
5. Start Postgres service container (postgres:15)
6. Run `uv run pytest --ds=config.django.test` (coverage gate from pytest.ini)
7. Run `uv run python manage.py spectacular --validate --fail-on-warn --settings=config.django.test` (OpenAPI validation)

**Trigger:** push and PR to `main`.

**Adapt for template:** Use env vars for DB connection to the service container. Don't include PostGIS (that's Depadrive-specific).

---

## Phase 2 — Production-Ready Patterns

These depend on Phase 1 (error catalog, envelope helpers, exception handler).

### 2.1 Throttling / Rate Limiting

**Create:**
| File | Purpose |
|------|---------|
| `DST:utils/throttles.py` | Named `UserRateThrottle` subclasses |

**Reference:** `SRC:utils/throttles.py`, `SRC:config/settings/restframework.py`

**Modify:** `DST:config/settings/restframework.py` — add:
```python
REST_FRAMEWORK = {
    ...
    'DEFAULT_THROTTLE_CLASSES': [
        'rest_framework.throttling.AnonRateThrottle',
        'rest_framework.throttling.UserRateThrottle',
    ],
    'DEFAULT_THROTTLE_RATES': {
        'anon': '100/hour',
        'user': '1000/hour',
        'auth_login': '10/minute',
        'auth_password_reset': '5/hour',
    },
}
```

**Keep it minimal** — only 4-5 universal rates. Projects add domain-specific rates later.

---

### 2.2 Pagination Utility

**Create:**
| File | Purpose |
|------|---------|
| `DST:utils/pagination.py` | `paginate_or_ok()` helper |

**Reference:** `SRC:utils/pagination.py`

**Key behavior:** Fetches N+1 rows to detect `has_next` without a `COUNT(*)` query. Default 20 per page, max 100. If no `?page` param, returns full list capped at 100. Embeds `meta.pagination` in the envelope.

---

### 2.3 Access Log Middleware

**Create:**
| File | Purpose |
|------|---------|
| `DST:config/middleware/access_log.py` | One-line HTTP access logging |

**Reference:** `SRC:config/middleware/access_log.py`

**Behavior:** Logs method, path, status, duration_ms, response_size, user_id, request_id. Skips health/static/media paths on 200. Enriches 4xx+ with IP and user-agent. Uses Loguru.

**Modify:** `DST:config/settings/apps_middlewares.py` — add `'config.middleware.access_log.AccessLogMiddleware'` to `MIDDLEWARE` (after RequestIdMiddleware).

---

### 2.4 Celery Task Template (Example)

**Create:**
| File | Purpose |
|------|---------|
| `DST:accounts/tasks.py` | Example task with full retry/idempotency pattern |

**Reference:** `SRC:notifications/tasks.py` (for the decorator pattern), `SRC:config/settings/celery.py` (for beat schedule + security settings)

**The example task should demonstrate:**
```python
@shared_task(
    name="accounts.tasks.example_cleanup_task",
    autoretry_for=(Exception,),
    max_retries=3,
    retry_backoff=True,
    retry_backoff_max=300,
    retry_jitter=True,
)
def example_cleanup_task():
    """Example: delete unverified users older than 30 days. Idempotent by design."""
    ...
```

**Modify:** `DST:config/settings/celery.py` — add:
```python
# Task serialization security
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_ACCEPT_CONTENT = ["json"]

# Worker tuning
CELERY_WORKER_MAX_TASKS_PER_CHILD = 500
CELERY_WORKER_MAX_MEMORY_PER_CHILD = 256_000  # 256MB

# Time limits
CELERY_TASK_TIME_LIMIT = 600       # hard: 10min
CELERY_TASK_SOFT_TIME_LIMIT = 540  # soft: 9min

# Prefetch
CELERY_WORKER_PREFETCH_MULTIPLIER = 1

# Example beat schedule
CELERY_BEAT_SCHEDULE = {
    "example-cleanup": {
        "task": "accounts.tasks.example_cleanup_task",
        "schedule": 86400,  # daily
    },
}
```

---

### 2.5 Root conftest.py

**Create:**
| File | Purpose |
|------|---------|
| `DST:conftest.py` | Project-wide pytest configuration |

**Reference:** `SRC:conftest.py`

**Contents:**
1. Call `django.setup()` before pytest_plugins load.
2. Register `accounts.tests.conftest` as a pytest plugin (makes its fixtures available project-wide).
3. Add `clear_cache_between_tests` autouse fixture that calls `cache.clear()` before and after each test (prevents throttle rate bleed between tests).

---

### 2.6 OpenAPI Envelope Serializers

**Create:**
| File | Purpose |
|------|---------|
| `DST:utils/openapi_serializers.py` | `ApiEnvelopeJsonListSerializer` shim for drf-spectacular |
| `DST:utils/schemas/__init__.py` | Package init |
| `DST:utils/schemas/envelope.py` | Pydantic models for OpenAPI annotations (`ApiMeta`, `ApiErrorEnvelope`, etc.) |
| `DST:utils/api_openapi.py` | Pre-built `OpenApiExample` instances and response type dicts |

**Reference:** `SRC:utils/openapi_serializers.py`, `SRC:utils/schemas/envelope.py`, `SRC:utils/api_openapi.py`

**Why this exists:** drf-spectacular's list heuristic wraps non-shim schemas in an extra array. The `ApiEnvelopeJsonListSerializer` with `@extend_schema_serializer(many=False)` prevents this. The Pydantic envelope models provide correct OpenAPI schema for the `{success, data, meta}` shape.

**Strip domain-specific examples.** Keep only universal ones (auth, validation, 404, 500).

---

### 2.7 Sentry Integration

**Create:**
| File | Purpose |
|------|---------|
| `DST:config/settings/monitoring.py` | `configure_sentry()` function |

**Reference:** `SRC:config/settings/monitoring.py`

**Behavior:** No-op when `SENTRY_DSN` is absent. When present, initializes `sentry_sdk` with Django and Celery integrations, sets traces_sample_rate from env, attaches release version.

**Modify:** `DST:config/django/production.py` — add `from config.settings.monitoring import configure_sentry; configure_sentry()`.
**Modify:** `DST:config/settings/config.py` — add `SENTRY_DSN: str = ""` and `SENTRY_TRACES_SAMPLE_RATE: float = 0.1` to `MainSettings`.
**Modify:** `DST:pyproject.toml` — add `sentry-sdk[django,celery]` to dependencies.

---

## Phase 3 — Specialized Patterns

Add these when a project actually needs them. Lower priority for the template.

### 3.1 Debug Payload Middleware

**Create:** `DST:config/middleware/debug_payload.py`
**Reference:** `SRC:config/middleware/debug_payload.py`
**Behavior:** Gated by `REQUEST_RESPONSE_DEBUG` env var. Raises `ImproperlyConfigured` if activated with `DEBUG=False`. Redacts ~20 sensitive field names (password, token, secret, otp, api_key, etc.). Logs request body on entry, response body on exit.
**Modify:** `DST:config/django/local.py` — conditionally add to MIDDLEWARE.
**Modify:** `DST:config/settings/config.py` — add `REQUEST_RESPONSE_DEBUG: bool = False`.

### 3.2 Image Validators

**Modify:** `DST:utils/validators.py` — add `validate_image_size(file, max_bytes=5*1024*1024)` and `validate_image_mime(file, allowed=("image/jpeg","image/png","image/webp"))`.
**Reference:** `SRC:utils/validators.py`

### 3.3 CSV/XLSX Export Helpers

**Create:** `DST:utils/export.py`
**Reference:** `SRC:utils/export.py`
**Provides:** `csv_response(filename, headers, rows)` and `xlsx_response(filename, headers, rows)`. Includes formula injection sanitization (prefixes `=`, `+`, `@`, TAB cells with single-quote).
**Modify:** `DST:pyproject.toml` — add `openpyxl` to dependencies.

### 3.4 Upload Path Helpers

**Create:** `DST:utils/models/_upload_paths.py`
**Reference:** `SRC:utils/models/_upload_paths.py`
**Provides:** `make_upload_path(subdir: str)` factory that returns an `upload_to` callable producing `subdir/YYYY/MM/DD/name_HHMMSS.ext` paths.
**Modify:** `DST:utils/models/__init__.py` — re-export `make_upload_path`.

### 3.5 Transactional Outbox (Abstract)

**Create:**
- `DST:utils/models/_outbox.py` — abstract `BaseOutbox` model with `event_type`, `payload` (JSON), `status` (pending/processed/failed), `created_at`, `processed_at`, `error_message`.
- `DST:utils/outbox.py` — `process_outbox_entry(entry, publisher_fn)` generic processor.

**Reference:** `SRC:assistance/models/_outbox.py`, `SRC:assistance/flow.py`
**Modify:** `DST:utils/models/__init__.py` — re-export `BaseOutbox`.

### 3.6 Smoke Test Script

**Create:** `DST:scripts/smoke.sh`
**Reference:** `SRC:scripts/smoke_mvp.sh`
**Provides:** Parameterized `BASE_URL` (default `http://localhost:8000`). Probes `/health/` and `/ready/`. Optionally probes an authenticated endpoint with `SMOKE_JWT` env var. Tabulated pass/fail output. Exits 0/1 for CI.

### 3.7 .coveragerc Refinement

**Modify:** `DST:.coveragerc`
**Reference:** `SRC:.coveragerc`
**Add omissions for:** `*/settings/*`, `config/django/*`, `manage.py`, `config/wsgi.py`, `config/asgi.py`, `utils/consumers.py` (dev-only). Add exclude lines for: `pragma: no cover`, `if TYPE_CHECKING:`, `if __name__`, `def __repr__`, `raise NotImplementedError`.

### 3.8 Celery Worker/Beat Run Scripts

**Create:**
- `DST:docker/scripts/run-celery-worker.sh` — configurable `CELERY_CONCURRENCY` (default 2), `--max-memory-per-child=256000`, `--max-tasks-per-child=500`, optional `DEV_AUTORELOAD` via watchfiles.
- `DST:docker/scripts/run-celery-beat.sh` — `DatabaseScheduler`, optional `DEV_AUTORELOAD`.

**Reference:** `SRC:docker/scripts/run-celery-worker.sh`, `SRC:docker/scripts/run-celery-beat.sh`
**Modify:** `DST:docker-compose.yml` — update celery_worker and celery_beat services to use the new scripts.

### 3.9 Transactional Email Service

**Create a new `notifications` app:**
```
DST:notifications/
  __init__.py
  apps.py
  services/
    __init__.py
    transactional_email.py    # event-code registry, template rendering, on_commit dispatch
  tasks.py                    # send_transactional_email_task with autoretry
  templates/
    emails/
      base.html               # base email template with header/footer
```

**Reference:** `SRC:notifications/services/transactional_email.py`, `SRC:notifications/tasks.py`, `SRC:notifications/templates/emails/`

**Strip OneSignal-specific logic.** Use Django's standard `EMAIL_BACKEND` only. Keep the async dispatch pattern: service builds the email context, enqueues via `transaction.on_commit`, task sends with autoretry.

**Modify:** `DST:config/settings/apps_middlewares.py` — add `'notifications'` to `PROJECT_APPS`.

---

## App Scaffold Update

After all patterns are implemented, update the app template so `starttemplateapp` generates apps that follow the new conventions:

**Modify:** `DST:static/exp_app/`

Add to the scaffold:
- `tasks.py` with the standard Celery task decorator template (commented example).
- `tests/tasks/__init__.py` for task test directory.

---

## Dependency Graph

```
Phase 1 (sequential):
  1.1 Error Catalog ──→ 1.2 Envelope Helpers ──→ 1.3 DRF Error Normalization ──→ 1.4 Exception Handler
  1.5 Request ID Middleware (independent, can parallel with 1.1-1.4)
  1.6 Health Endpoints (independent)
  1.7 Production Hardening (independent)
  1.8 CI Workflow (independent, but should run after 1.1-1.7 to validate them)

Phase 2 (after Phase 1 complete):
  2.1 Throttling (needs exception handler for RATE_LIMIT__EXCEEDED)
  2.2 Pagination (needs envelope helpers for paginate_or_ok)
  2.3 Access Log Middleware (needs request_id middleware)
  2.4 Celery Task Template (independent)
  2.5 Root conftest.py (independent)
  2.6 OpenAPI Envelope Serializers (needs envelope helpers + Pydantic schemas)
  2.7 Sentry (independent)

Phase 3 (all independent, any order):
  3.1-3.9 all independent of each other
```

---

## Validation Gate

After each phase, run:

```bash
# Tests pass
uv run pytest --ds=config.django.test

# OpenAPI validates
uv run python manage.py spectacular --validate --fail-on-warn --settings=config.django.test

# Import smoke test
uv run python -c "
from errors.catalog import E
from errors.exceptions import AppAPIError
from utils.api_response import ok, err_single
from config.exception_handler import custom_exception_handler
print('All imports OK')
"
```

After Phase 1 is complete, the existing `accounts/tests/controllers/test_auth.py` tests will likely need updates since the response format changes from raw DRF to the envelope format. **Update tests to expect the envelope shape** — this is expected and correct.

---

## What NOT to Do

1. **Do not copy Depadrive domain apps** (assistance, depanneurs, reviews, etc.). Only extract generic patterns.
2. **Do not copy the full 130-code error catalog.** Start with ~20 universal codes. Projects add domain-specific codes later.
3. **Do not add OneSignal, Ably, or Mapbox integrations.** Those are Depadrive-specific.
4. **Do not recreate DB routing** — it already exists and works.
5. **Do not add PostGIS** to the CI workflow — that's Depadrive-specific.
6. **Do not break existing tests.** If the envelope format changes response shapes, update the test assertions.
7. **Do not change the existing User model** (integer PK is fine for a template).
8. **Do not add `sentry-sdk` to runtime deps** — add it as optional or in production extras only.
