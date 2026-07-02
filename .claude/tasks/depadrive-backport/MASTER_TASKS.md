# Depadrive → Katesthe Backport

Priority: P1
Status: active
**Date:** 2026-07-02
**Source:** `BACKPORT_PLAN.md` (repo root) — backport 23 production-hardened patterns + app-scaffold update from `Depadrive-core` (SRC) into this clean bootstrap template (DST).
**Goal:** This template ships with the error catalog, response envelope, exception handler, request-id + access-log middleware, health probes, production hardening, CI, throttling, pagination, Celery task template, root conftest, OpenAPI envelope schemas, Sentry hook, and the Phase-3 specialized utilities — all generic (no Depadrive domain logic), all tested, full suite + OpenAPI validation green.

**Reference convention:** `SRC:path` = `/home/tmpusr/Documents/github/dp/Depadrive-core/path`; `DST:path` = `/home/tmpusr/dev/Katesthe-core/path`.

---

## Locked decisions

1. **Full scope.** Phase 1 (1.1–1.8), Phase 2 (2.1–2.7), Phase 3 (3.1–3.9), and the App Scaffold Update are all IN scope. Phase 3 is lower priority but not optional.
2. **Tests co-located per subtask.** Every subtask that adds code writes its own tests in the same subtask. Updating the existing `accounts/tests/` (auth/controller tests) to the new envelope response shape is REQUIRED and is its own subtask (009), sequenced after the exception handler (004).
3. **Phase ordering is a hard dependency chain.** Phase 1 completes before Phase 2; Phase 2 before Phase 3. Within Phase 1 the core chain is strictly sequential: 001 Error Catalog → 002 Envelope Helpers → 003 DRF Error Normalization → 004 Exception Handler. 005/006/007 are independent; 008 CI runs last in Phase 1.
4. **Do NOT copy files verbatim.** Extract the generic pattern; strip ALL Depadrive domain logic (assistance, depanneurs, reviews, OneSignal, Ably, Mapbox, PostGIS). Start the error catalog with ONLY the ~20 universal codes in subtask 001 — not the full 130/200.
5. **Do NOT recreate what exists:** Pydantic settings, primary/replica DB routing (`config/db_router.py`, `config/db_utils.py`, `config/middleware/db_consistency.py`), Unfold admin, Factory Boy, Loguru (`config/logger.py`), Celery infra (`config/celery.py` + docker services). Confirmed present.
6. **Do NOT change the User model** (integer PK is fine). **Do NOT add `sentry-sdk` to runtime deps** — optional/production extras only.
7. **Login bad credentials → 401 `AUTH__INVALID_CREDENTIALS`, NOT 422.** The exception handler (004) special-cases authentication failure on the token-obtain / login path to return **401 `AUTH__INVALID_CREDENTIALS`**, rather than letting the token-obtain serializer's non-field `ValidationError` fall through to the blanket 422 VALIDATION mapping. (Non-login `AuthenticationFailed`/`InvalidToken` map to 401 `AUTH__TOKEN_INVALID`, a separate branch — not 422.) A login request that fails on a *missing field* (e.g. no `password`) is still 422 `VALIDATION__*` — only the credentials-authentication failure is 401. Every other DRF `ValidationError` remains 422. This makes the catalog's `AUTH__INVALID_CREDENTIALS` code actually emitted. Subtask 009 asserts 401 + `AUTH__INVALID_CREDENTIALS` on login-failure paths.

---

## Priority queue

| ID | Subtask | Phase | Group | Risk | Effort | Scope |
|----|---------|-------|-------|------|--------|-------|
| 001 | Error Catalog + AppAPIError | 1 | A | LOW | 25m | `errors/` package (catalog, exceptions) |
| 002 | API Response Envelope Helpers | 1 | A | LOW | 25m | `utils/api_response.py` |
| 003 | DRF Error Envelope Normalization | 1 | A | MED | 40m | `utils/drf_error_envelope.py` |
| 004 | Custom Exception Handler + DRF wiring | 1 | A | HIGH | 50m | `config/exception_handler.py`, `restframework.py` |
| 005 | Request ID Middleware + settings wiring | 1 | B | MED | 40m | `config/middleware/request_id.py`, `logger.py`, `apps_middlewares.py` |
| 006 | Health / Readiness Endpoints | 1 | C | LOW | 35m | `config/health.py`, `urls.py`, `Dockerfile` |
| 007 | Production Security Hardening | 1 | D | MED | 40m | `config/django/production.py`, `corsheaders.py`, `.coveragerc` (1 line) |
| 008 | CI Workflow (GitHub Actions) | 1 | — | LOW | 30m | `.github/workflows/ci.yml` — numbered before 009 but EXECUTES after it (Phase-1 closing gate) |
| 009 | Update accounts tests → envelope shape | 1 | A | HIGH | 60m | `accounts/tests/controllers/test_auth.py` (+siblings) |
| 010 | Throttling / Rate Limiting | 2 | A | MED | 30m | `utils/throttles.py`, `restframework.py` |
| 011 | Pagination Utility | 2 | A | MED | 35m | `utils/pagination.py` |
| 012 | Access Log Middleware | 2 | A | MED | 35m | `config/middleware/access_log.py`, `apps_middlewares.py` |
| 013 | Celery Task Template + settings | 2 | A | LOW | 35m | `accounts/tasks.py`, `config/settings/celery.py` |
| 014 | Root conftest.py | 2 | A | MED | 25m | `conftest.py` |
| 015 | OpenAPI Envelope Serializers | 2 | A | MED | 45m | `utils/openapi_serializers.py`, `utils/schemas/`, `utils/api_openapi.py` |
| 016 | Sentry Integration | 2 | A | LOW | 30m | `config/settings/monitoring.py`, `production.py`, `config.py`, `pyproject.toml` |
| 017 | Debug Payload Middleware | 3 | A | LOW | 30m | `config/middleware/debug_payload.py`, `local.py`, `config.py` |
| 018 | Image Validators | 3 | A | LOW | 20m | `utils/validators.py` |
| 019 | CSV/XLSX Export Helpers | 3 | A | LOW | 30m | `utils/export.py`, `pyproject.toml` |
| 020 | Upload Paths + Transactional Outbox | 3 | A | MED | 50m | `utils/models/_upload_paths.py`, `_outbox.py`, `utils/outbox.py`, `models/__init__.py` |
| 021 | Ops scripts & coverage config | 3 | A | LOW | 35m | `scripts/smoke.sh`, `docker/scripts/*`, `docker-compose.yml`, `.coveragerc` |
| 022 | Transactional Email Service (notifications app) | 3 | A | MED | 55m | `notifications/` app, `apps_middlewares.py`, `pytest.ini` |
| 023 | App Scaffold Update | 3 | A | LOW | 20m | `static/exp_app/tasks.py`, scaffold test dirs |
| 024 | Feature validation gate (full suite + OpenAPI) | 4 | — | LOW | 20m | no code — runs the DoD gate |

---

## Subtasks

<!-- Canonical status list. Orchestrator flips to [COMPLETED]; archive reads these. -->
<!-- Status token: PENDING | IN_PROGRESS | BLOCKED | COMPLETED | SKIPPED | DEFERRED -->
- [PENDING] [001-error-catalog.md](001-error-catalog.md) — Error Catalog + AppAPIError
- [PENDING] [002-envelope-helpers.md](002-envelope-helpers.md) — API Response Envelope Helpers
- [PENDING] [003-drf-error-normalization.md](003-drf-error-normalization.md) — DRF Error Envelope Normalization
- [PENDING] [004-exception-handler.md](004-exception-handler.md) — Custom Exception Handler + DRF wiring
- [PENDING] [005-request-id-middleware.md](005-request-id-middleware.md) — Request ID Middleware + settings wiring
- [PENDING] [006-health-endpoints.md](006-health-endpoints.md) — Health / Readiness Endpoints
- [PENDING] [007-production-hardening.md](007-production-hardening.md) — Production Security Hardening
- [PENDING] [008-ci-workflow.md](008-ci-workflow.md) — CI Workflow (GitHub Actions)
- [PENDING] [009-update-accounts-tests.md](009-update-accounts-tests.md) — Update accounts tests → envelope shape
- [PENDING] [010-throttling.md](010-throttling.md) — Throttling / Rate Limiting
- [PENDING] [011-pagination.md](011-pagination.md) — Pagination Utility
- [PENDING] [012-access-log-middleware.md](012-access-log-middleware.md) — Access Log Middleware
- [PENDING] [013-celery-task-template.md](013-celery-task-template.md) — Celery Task Template + settings
- [PENDING] [014-root-conftest.md](014-root-conftest.md) — Root conftest.py
- [PENDING] [015-openapi-envelope-serializers.md](015-openapi-envelope-serializers.md) — OpenAPI Envelope Serializers
- [PENDING] [016-sentry-integration.md](016-sentry-integration.md) — Sentry Integration
- [PENDING] [017-debug-payload-middleware.md](017-debug-payload-middleware.md) — Debug Payload Middleware
- [PENDING] [018-image-validators.md](018-image-validators.md) — Image Validators
- [PENDING] [019-export-helpers.md](019-export-helpers.md) — CSV/XLSX Export Helpers
- [PENDING] [020-upload-paths-outbox.md](020-upload-paths-outbox.md) — Upload Paths + Transactional Outbox
- [PENDING] [021-ops-scripts-coverage.md](021-ops-scripts-coverage.md) — Ops scripts & coverage config
- [PENDING] [022-transactional-email.md](022-transactional-email.md) — Transactional Email Service (notifications app)
- [PENDING] [023-app-scaffold-update.md](023-app-scaffold-update.md) — App Scaffold Update
- [PENDING] [024-validation-gate.md](024-validation-gate.md) — Feature validation gate

---

## Dependency graph

```
PHASE 1 (must finish before Phase 2)
  Group A (sequential core chain):
     001 ─→ 002 ─→ 003 ─→ 004 ─→ 009
  Group B:  005 (starts after 001; concurrent with 002/003/004)
  Group C:  006 (fully independent — concurrent from the start)
  Group D:  007 (fully independent — concurrent from the start)
  008 CI: runs LAST in Phase 1, after 001–007 (and 009) are green.
          NOTE: 008 is numbered before 009 for readability but EXECUTES after 009.

     001
      ├──────────────► 005 (Group B)
      ▼
     002 ─► 003 ─► 004 ─► 009
     006 (Group C) ─┐
     007 (Group D) ─┼──► 008 (Phase-1 gate)
     005 ───────────┘

PHASE 2 (after ALL Phase 1 complete) — Group A, all concurrent (disjoint files):
     010  011  012  013  014  015  016
  (each depends only on Phase 1 outputs; none depend on each other)

PHASE 3 (after ALL Phase 2 complete) — Group A, all concurrent (disjoint files):
     017  018  019  020  021  022  023
  (all mutually independent)

PHASE 4 (final gate):
     024  (after all of Phase 3)
```

**Concurrency summary**
- Phase 1: 4 lanes (A sequential chain of 5; B/C/D single subtasks) + 008 as the closing gate (executes after 009). Peak concurrency = 4 (001-era: A=001, B waits, C=006, D=007 → 006/007 run while 001 runs; once 001 done, 002 and 005 run concurrently with 006/007).
- Phase 2: 1 group of 7 fully-parallel subtasks.
- Phase 3: 1 group of 7 fully-parallel subtasks.
- Phase 4: 1 closing subtask.

---

## File ownership (strictly disjoint within each phase)

### Shared-file resolutions (READ THIS)
These files are written by more than one pattern. Resolution below guarantees **no two subtasks in the same phase touch the same file**; cross-phase edits are safe because phases run sequentially.

| File | Editors (spec) | Resolution |
|------|----------------|------------|
| `config/settings/apps_middlewares.py` | 1.1, 1.5, 2.3, 3.9 | **Phase-1 owner = 005** (does BOTH the `'errors'` PROJECT_APPS line — reassigned from 001 — AND the `RequestIdMiddleware` MIDDLEWARE line). 001 therefore creates ONLY the `errors/` package and never touches settings; 005 depends on 001. **Phase-2 owner = 012** (AccessLogMiddleware). **Phase-3 owner = 022** (`'notifications'` app). Three different phases → sequential → safe. |
| `config/settings/restframework.py` | 1.4, 2.1 | **Phase-1 owner = 004** (`EXCEPTION_HANDLER`). **Phase-2 owner = 010** (throttle classes + rates). Different phases → safe. The `REST_FRAMEWORK` dict already exists in this repo — both subtasks EDIT it in place, they do not create it. |
| `config/django/production.py` | 1.7, 2.7 | **Phase-1 owner = 007** (hardening). **Phase-2 owner = 016** (`configure_sentry()` call). Different phases → safe. File is currently a bare `from config.django.base import *`. |
| `config/settings/config.py` | 2.7, 3.1 | **Phase-2 owner = 016** (`SENTRY_DSN`, `SENTRY_TRACES_SAMPLE_RATE`). **Phase-3 owner = 017** (`REQUEST_RESPONSE_DEBUG`). Different phases → safe. Add fields to the `MainSettings` class. |
| `pyproject.toml` | 2.7, 3.3 | **Phase-2 owner = 016** (`sentry-sdk[django,celery]` as OPTIONAL extra, not runtime dep). **Phase-3 owner = 019** (`openpyxl`, runtime). Different phases → safe. |
| `.coveragerc` | 1.7 (partial), 3.7 | **Co-owned across phases.** **Phase-1 owner = 007** adds ONLY the single `config/django/*` omit line (needed early because 007's production-settings lines are subprocess-only, contributing zero coverage — deferring the omit to Phase 3 would sink the Phase-1/Phase-2 gates + CI against the 80% floor). **Phase-3 owner = 021** adds the remaining omits + `exclude_lines` and MUST NOT re-add `config/django/*`. Different phases → sequential → safe. |
| `pytest.ini` | 3.9 | **Owner = 022** only (adds `notifications/tests` to `testpaths` and `--cov=notifications` to `addopts`, so the notifications app is both collected and coverage-measured). No other subtask touches `pytest.ini`. |
| `config/settings/celery.py` | 2.4 | **Owner = 013** only. |
| `config/logger.py` | 1.5 | **Owner = 005** only. |
| `config/urls.py` | 1.6 | **Owner = 006** only. |
| `Dockerfile` | 1.6 | **Owner = 006** only. |
| `docker-compose.yml` | 3.8 | **Owner = 021** only. |
| `config/django/local.py` | 3.1 | **Owner = 017** only. |
| `utils/validators.py` | 3.2 | **Owner = 018** only (appends image validators; leaves the Moroccan-phone validator intact). |
| `utils/models/__init__.py` | 3.4, 3.5 | **Same-phase collision → MERGED.** Spec items 3.4 (upload paths) and 3.5 (outbox) both re-export from `utils/models/__init__.py`. They are merged into **subtask 020**, the single owner of that file. |
| `accounts/tests/controllers/test_auth.py` | (test update) | **Owner = 009** only. 004 writes ONLY its own new test file (`config/tests/test_exception_handler.py`) — it never touches `accounts/tests/`. |

### Per-subtask owned paths (create = C, modify = M)

- **001**: C `errors/__init__.py`, `errors/catalog.py`, `errors/exceptions.py`, `errors/apps.py`; C `utils/tests/test_errors.py`
- **002**: C `utils/api_response.py`, `utils/tests/test_api_response.py`
- **003**: C `utils/drf_error_envelope.py`, `utils/tests/test_drf_error_envelope.py`
- **004**: C `config/exception_handler.py`; M `config/settings/restframework.py`; C `config/tests/test_exception_handler.py`
- **005**: C `config/middleware/request_id.py`; M `config/logger.py`, `config/settings/apps_middlewares.py`; C `config/tests/test_request_id.py`
- **006**: C `config/health.py`; M `config/urls.py`, `Dockerfile`; C `config/tests/test_health.py`
- **007**: M `config/django/production.py`, `config/settings/corsheaders.py`, `.coveragerc` (only the `config/django/*` omit line); C `config/tests/test_production_settings.py`
- **008**: C `.github/workflows/ci.yml`
- **009**: M `accounts/tests/controllers/test_auth.py`, `accounts/tests/serializers/test_auth.py`, `accounts/tests/test_basic.py`
- **010**: C `utils/throttles.py`, `utils/tests/test_throttles.py`; M `config/settings/restframework.py`
- **011**: C `utils/pagination.py`, `utils/tests/test_pagination.py`
- **012**: C `config/middleware/access_log.py`, `config/tests/test_access_log.py`; M `config/settings/apps_middlewares.py`
- **013**: C `accounts/tasks.py`, `accounts/tests/tasks/__init__.py`, `accounts/tests/tasks/test_example.py`; M `config/settings/celery.py`
- **014**: C `conftest.py`
- **015**: C `utils/openapi_serializers.py`, `utils/schemas/__init__.py`, `utils/schemas/envelope.py`, `utils/api_openapi.py`, `utils/tests/test_openapi_serializers.py`
- **016**: C `config/settings/monitoring.py`, `config/tests/test_monitoring.py`; M `config/django/production.py`, `config/settings/config.py`, `pyproject.toml`
- **017**: C `config/middleware/debug_payload.py`, `config/tests/test_debug_payload.py`; M `config/django/local.py`, `config/settings/config.py`
- **018**: M `utils/validators.py`; C `utils/tests/test_image_validators.py`
- **019**: C `utils/export.py`, `utils/tests/test_export.py`; M `pyproject.toml`
- **020**: C `utils/models/_upload_paths.py`, `utils/models/_outbox.py`, `utils/outbox.py`, `utils/tests/test_upload_paths.py`, `utils/tests/test_outbox.py`; M `utils/models/__init__.py`
- **021**: C `scripts/smoke.sh`, `docker/scripts/run-celery-worker.sh`, `docker/scripts/run-celery-beat.sh`; M `docker-compose.yml`, `.coveragerc` (remaining omits + exclude-lines, NOT `config/django/*`)
- **022**: C `notifications/**` (app: `__init__.py`, `apps.py`, `services/`, `tasks.py`, `templates/emails/base.html`, `tests/`); M `config/settings/apps_middlewares.py`, `pytest.ini`
- **023**: C `static/exp_app/tasks.py`, `static/exp_app/tests/tasks/__init__.py`
- **024**: no owned files (runs the validation gate)

> Note: several subtasks add new files under the shared `utils/tests/` and `config/tests/` directories. Directory sharing is fine — each subtask creates ONLY its own uniquely-named `test_*.py` and MUST NOT modify the existing `__init__.py` of those test packages (they already exist).

---

## Validation gate (Definition of Done)

Run after each phase and at the end (subtask 024):

```bash
# 1. Full test suite (coverage gate 80% per pytest.ini; 022 wires notifications into testpaths + coverage)
uv run pytest --ds=config.django.test

# 2. OpenAPI schema validates
uv run python manage.py spectacular --validate --fail-on-warn --settings=config.django.test

# 3. Import smoke test
uv run python -c "
from errors.catalog import E
from errors.exceptions import AppAPIError
from utils.api_response import ok, err_single
from config.exception_handler import custom_exception_handler
print('All imports OK')
"

# 4. Production boot assertions (subtask 007) — must succeed with DEBUG=False + explicit ALLOWED_HOSTS,
#    and crash with AssertionError when DEBUG=True.
```

Phase gates:
- **After Phase 1:** commands 1–4 green; envelope shape verified on an error response; login-failure returns 401 `AUTH__INVALID_CREDENTIALS`; `X-Request-ID` header present; `/health/` and `/ready/` reachable.
- **After Phase 2:** throttling returns `RATE_LIMIT__EXCEEDED` (429), pagination meta present, access log emits one line/request, Sentry no-ops without DSN.
- **After Phase 3:** all specialized utilities import and pass their tests; `notifications` app migrates cleanly and its tests are collected + coverage-measured; scaffold generates `tasks.py`.

---

## Active feature conflicts

`.claude/tasks/MASTER_PLAN.md` Active = none; queue empty. **No conflicts with active features.** This is the only active feature — set it Active in MASTER_PLAN.md on kickoff.

## Assumptions & notes for implementers

1. **DRF `ValidationError` → HTTP 422; login bad-credentials → 401 (locked decision 7).** The exception handler (004) maps generic DRF validation errors to **422**, but **special-cases login/token-obtain authentication failure to 401 `AUTH__INVALID_CREDENTIALS`**. So: login wrong-password/unknown-user → **401 `AUTH__INVALID_CREDENTIALS`**; login *missing field* and all other validation → **422 `VALIDATION__*`**; missing token on an auth-required endpoint → **401 `AUTH__UNAUTHENTICATED`**. Many existing `accounts/tests/controllers/test_auth.py` cases assert **400** — subtask **009** owns reconciling every assertion to the new envelope + status per this split. Treat 009 as HIGH risk (dozens of assertions). One existing test asserts `data['message']` (activation, ~line 1286) — the envelope has **no `message` field**; 009 rewrites it to `error.code` / `success is False`. 009 must NOT assert forward-looking catalog codes that no path emits.
2. **`errors/` as an installed app.** The `errors/` package is registered in `PROJECT_APPS` (per spec) but contains no models — a minimal `apps.py` with an `AppConfig` (name=`errors`) keeps Django's app registry happy. Registration is performed by **005** (the `apps_middlewares.py` owner), not 001.
3. **Outbox has NO SRC reference.** `SRC:assistance/models/_outbox.py` and `SRC:utils/outbox.py` do **not exist** in the source project (confirmed by recon). Subtask **020** must build `BaseOutbox` and `process_outbox_entry()` from the spec text alone (abstract model: `event_type`, `payload` JSON, `status` pending/processed/failed, `created_at`, `processed_at`, `error_message`).
4. **Success responses are NOT auto-wrapped.** The envelope is applied to ERROR responses by the exception handler and, for successes, only where a view explicitly calls `ok()`. Djoser/JWT success bodies (`{access, refresh}`, `/me`) stay raw unless a later task opts them in. So most success-body assertions in 009 remain valid; only error-body/status assertions change.
5. **Two settings objects.** The pydantic `MainSettings` (`from config.settings.config import settings`) exposes app config (`REDIS_URL`, `DJANGO_DEBUG`, `REQUEST_RESPONSE_DEBUG`, `SENTRY_DSN`) and has **no** `DEBUG` attribute (the field is `DJANGO_DEBUG`) and **no** Django runtime flags. The Django global (`from django.conf import settings`) exposes resolved `DEBUG`, `CELERY_TASK_ALWAYS_EAGER`, etc. Rule: read `CELERY_TASK_ALWAYS_EAGER` and resolved `DEBUG` from `django.conf.settings`; read `REDIS_URL`/feature flags from the pydantic settings; **never** reference pydantic `settings.DEBUG` (AttributeError). Affects 006 (`_check_celery`), 007 (CORS gate), 017 (debug middleware).
6. **Test DB is SQLite in-memory** (`config/django/test.py`); Celery runs eager (`CELERY_TASK_ALWAYS_EAGER = True`); caches are LocMemCache. Health-readiness tests (006) treat eager Celery as OK and either mock Redis or assert graceful 503 — never require a live Redis.
7. **CI Postgres, not PostGIS.** Subtask 008 strips all GIS/GDAL/GEOS steps from `SRC:.github/workflows/ci.yml`; use plain `postgres:15` service with env-var DB config.
8. **`spectacular` is a dev dependency** — the OpenAPI validation command runs under `--settings=config.django.test`.
9. **`INTERNAL__ERROR` is 5xx-only.** Per `.claude/rules/api.md`, the `coerce_drf_error_response` map (003) and the handler (004) must never route a 4xx to `INTERNAL__ERROR`; 409 → `RESOURCE__CONFLICT`, 405/406/415/400 → a client-error `VALIDATION__*` code, only genuine 5xx → INTERNAL.
