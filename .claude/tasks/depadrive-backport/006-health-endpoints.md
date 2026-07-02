# 006 — Health / Readiness Endpoints

**Status:** [PENDING]
**Phase:** 1
**Group:** C (fully independent — concurrent from the start)
**Risk:** LOW
**Effort:** 35m
**Dependencies:** none

## Goal
Add `GET /health/` (liveness, plain `200 "ok"`) and `GET /ready/` (readiness — probes DB, Redis, Celery broker; `200` JSON when all pass, `503` when any fails).

## Context
Container/orchestrator probes and the smoke script (021) depend on these. Liveness must be dependency-free; readiness reports per-check results.

## SRC reference to adapt from
`SRC:config/health.py` — `liveness(request)` → `HttpResponse("ok")`; `readiness(request)` → `JsonResponse` with `_check_db()`, `_check_redis()`, `_check_celery()` each returning `(ok: bool, detail: str)`; 503 if any fails; **Celery eager mode counts as OK**.

## Files Owned
- `config/health.py` (C)
- `config/urls.py` (M)
- `Dockerfile` (M)
- `config/tests/test_health.py` (C)

## Two settings objects — READ THIS
This subtask reads from **two different settings objects**; using the wrong one causes an `AttributeError`:
- **Pydantic** `from config.settings.config import settings` → app config values like `settings.REDIS_URL`. It has NO Django runtime flags (`CELERY_TASK_ALWAYS_EAGER`, `DEBUG` resolved, etc.).
- **Django** `from django.conf import settings as dj_settings` → resolved Django globals like `dj_settings.CELERY_TASK_ALWAYS_EAGER` (set in `config/django/test.py`) and `dj_settings.DEBUG`.

## Implementation Steps

### Step 1 — `config/health.py`
```python
from django.conf import settings as dj_settings
from config.settings.config import settings as app_settings  # pydantic
```
- `liveness(request)`: return `HttpResponse("ok", content_type="text/plain", status=200)`. No auth, no deps.
- `_check_db()`: run `SELECT 1` via `django.db.connection.cursor()`; return `(True, "ok")` or `(False, str(e))`.
- `_check_redis()`: PING using the configured Redis URL from the **pydantic** settings (`app_settings.REDIS_URL`) with a short timeout; return tuple. Tolerate absence gracefully.
- `_check_celery()`: if `getattr(dj_settings, "CELERY_TASK_ALWAYS_EAGER", False)` (test/eager) → return `(True, "eager")` WITHOUT pinging. Else `from config.celery import app; app.control.ping(timeout=1)` and return the tuple. **Use `django.conf.settings` here, NOT the pydantic settings** — the pydantic `MainSettings` has no `CELERY_TASK_ALWAYS_EAGER` field and would raise `AttributeError`.
- `readiness(request)`: assemble `{"db": ..., "redis": ..., "celery": ...}` (each `{"ok": bool, "detail": str}`); status = 200 if all ok else 503; return `JsonResponse(payload, status=...)`. These are plain Django views (not DRF), so they are NOT wrapped by the exception handler — decorate with `@csrf_exempt` and allow unauthenticated access explicitly.

### Step 2 — `config/urls.py`
Add near the top of `urlpatterns`:
```python
from config.health import liveness, readiness
...
path("health/", liveness),
path("ready/", readiness),
```
Keep the existing admin/redirect/v1 routes intact.

### Step 3 — `Dockerfile`
Add a `HEALTHCHECK` (curl is already installed):
```dockerfile
HEALTHCHECK --interval=30s --timeout=3s --start-period=20s --retries=3 \
  CMD curl -f http://localhost:8000/health/ || exit 1
```
Place before the final `CMD`.

## Tests (`config/tests/test_health.py`) — `@pytest.mark.django_db` where DB is hit
- `GET /health/` → 200, body `b"ok"`.
- `GET /ready/` with a working DB and eager Celery → 200; JSON has `db`, `redis`, `celery` keys. In test settings `CELERY_TASK_ALWAYS_EAGER = True`, so `_check_celery` returns `("eager")` without a broker — assert `celery.ok is True` and detail `eager`. Mock Redis PING to succeed (or accept a graceful failure path — see below).
- Failure path: patch `_check_db` to return `(False, "down")` → `/ready/` returns 503 and `db.ok is False`.
- Use `config.urls_test` (the test URLConf) — ensure the health routes are reachable there; if `urls_test` does not include them, the readiness views can be tested by calling the view functions directly with a `RequestFactory` request. (Do NOT modify `urls_test` — call views directly if needed.)

## Validation
```bash
uv run pytest config/tests/test_health.py -x -v --ds=config.django.test
```

## Acceptance Criteria
- [ ] `/health/` returns plaintext `ok` 200 with no dependency probing.
- [ ] `/ready/` probes db/redis/celery and returns 200 all-ok / 503 on any failure with per-check detail.
- [ ] `_check_celery` reads `django.conf.settings.CELERY_TASK_ALWAYS_EAGER` (NOT the pydantic settings) — no `AttributeError`; `_check_redis` reads `REDIS_URL` from the pydantic settings.
- [ ] Routes registered in `config/urls.py`; `HEALTHCHECK` added to `Dockerfile`.
- [ ] Eager Celery treated as OK; tests pass without a live Redis (mock or graceful).
