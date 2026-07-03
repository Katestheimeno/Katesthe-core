# Change: Depadrive-core Production-Pattern Backport

**Date:** 2026-07-02 17:28 (approximate — derived from `git log -1 --format=%cd`, the latest committed timestamp; this change itself is uncommitted at doc-writing time)
**Author:** AI-assisted
**Prompt Scope:** Backport 23 production-hardened patterns (error catalog, response envelope, exception handler, request-id/access-log middleware, health probes, production hardening, CI, throttling, pagination, Celery task template, root conftest, OpenAPI envelope schemas, Sentry hook, and Phase-3 specialized utilities) plus an app-scaffold update from `Depadrive-core` into this clean bootstrap template, per `BACKPORT_PLAN.md` and `.claude/tasks/depadrive-backport/MASTER_TASKS.md`.

## Summary

Katesthe-core (a Django bootstrap template) gains the set of production patterns that `Depadrive-core` evolved on top of it over ~1 year: a namespaced machine-readable error catalog + `AppAPIError`, a `{success, data, meta}` / `{success, error, meta}` response envelope with a custom DRF exception handler, request-id + access-log middleware, `/health/` + `/ready/` probes, production security hardening (HSTS, secure cookies, boot asserts), a GitHub Actions CI workflow, throttling defaults, a manual pagination helper, a Celery task template with retry/idempotency conventions, a project-wide `conftest.py`, OpenAPI envelope serializers/schemas, an optional Sentry hook, and Phase-3 utilities (debug-payload middleware, image validators, CSV/XLSX export, upload-path + transactional-outbox helpers, ops scripts, a `notifications` app for transactional email). All patterns are generic — no Depadrive domain logic (assistance, depanneurs, reviews, OneSignal, Ably, Mapbox, PostGIS) was copied.

All work is implemented in the working tree per the 24-subtask plan in `.claude/tasks/depadrive-backport/MASTER_TASKS.md`; full suite green (480 tests, 85.24% coverage against an 80% floor) and `spectacular --validate --fail-on-warn` passes under OAS 3.1.0.

## Reason for Change

Feature backport — the template previously lacked production-hardening patterns that every downstream project ended up re-implementing. Backporting them into the template means new projects start with these already in place.

## Files Modified

Grouped by phase (see `BACKPORT_PLAN.md` for the full per-pattern spec and `.claude/tasks/depadrive-backport/MASTER_TASKS.md` for subtask-level file ownership).

| Group | Files | Change |
|---|---|---|
| Phase 1 — error catalog & envelope | `errors/__init__.py`, `errors/catalog.py`, `errors/exceptions.py`, `errors/apps.py` (new) | `AppAPIError` + namespaced `E.*` catalog codes (`AUTH__*`, `VALIDATION__*`, `PERMISSION__*`, `RESOURCE__*`, `RATE_LIMIT__EXCEEDED`, `INTERNAL__*`, `NOTIFICATION__EMAIL_DELIVERY_FAILED`) |
| Phase 1 — envelope helpers | `utils/api_response.py` (new) | `ok()`, `err_single()`, `meta_for_request()` |
| Phase 1 — DRF normalization | `utils/drf_error_envelope.py` (new) | `normalize_validation_detail()`, `validation_error_response()`, `coerce_drf_error_response()` |
| Phase 1 — exception handler | `config/exception_handler.py` (new); `config/settings/restframework.py` (modified) | `custom_exception_handler()` wired via `EXCEPTION_HANDLER`; fixed branch order incl. login 401 split (locked decision 7) |
| Phase 1 — request-id middleware | `config/middleware/request_id.py` (new); `config/logger.py`, `config/settings/apps_middlewares.py` (modified) | `RequestIdMiddleware`, `X-Request-ID` header, Loguru `request_id` context patch |
| Phase 1 — health probes | `config/health.py` (new); `config/urls.py`, `Dockerfile` (modified) | `/health/` liveness, `/ready/` readiness (DB/Redis/Celery), Docker `HEALTHCHECK` |
| Phase 1 — production hardening | `config/django/production.py`, `config/settings/corsheaders.py`, `.coveragerc` (modified) | Boot asserts (`DEBUG`, `ALLOWED_HOSTS`), HSTS/secure-cookie/X-Frame settings, loopback-origin stripping from prod CORS |
| Phase 1 — CI | `.github/workflows/ci.yml` (new) | Postgres-service test + OpenAPI-validate pipeline (no PostGIS) |
| Phase 1 — envelope test migration | `accounts/tests/controllers/test_auth.py` (modified, ~191 line diff) | Reconciled assertions to envelope shape + 401/422 login split |
| Phase 2 — throttling | `utils/throttles.py` (new); `config/settings/restframework.py` (modified) | `AuthLoginThrottle`, `PasswordResetThrottle`; `DEFAULT_THROTTLE_RATES` |
| Phase 2 — pagination | `utils/pagination.py` (new) | `paginate_or_ok()` — N+1-row-overfetch pagination, envelope `meta.pagination` |
| Phase 2 — access log | `config/middleware/access_log.py` (new); `config/settings/apps_middlewares.py` (modified) | One-line structured access log per request |
| Phase 2 — Celery template | `accounts/tasks.py` (new) | `example_cleanup_task` (autoretry/backoff/jitter template); `config/settings/celery.py` (modified) — serializer/worker/time-limit/prefetch settings + beat schedule |
| Phase 2 — root conftest | `conftest.py` (new) | Global registration of `accounts/tests/conftest.py` fixtures + `clear_cache_between_tests` autouse fixture |
| Phase 2 — OpenAPI envelope | `utils/openapi_serializers.py`, `utils/schemas/__init__.py`, `utils/schemas/envelope.py`, `utils/api_openapi.py` (new) | `ApiEnvelopeJsonListSerializer` shim, Pydantic envelope models, reusable `OpenApiExample`/`OpenApiResponse` fragments |
| Phase 2 — Sentry | `config/settings/monitoring.py` (new); `config/django/production.py`, `config/settings/config.py`, `pyproject.toml` (modified) | `configure_sentry()` no-op-safe bootstrap; `sentry-sdk` as an optional `production` extra |
| Phase 3 — debug payload | `config/middleware/debug_payload.py` (new); `config/django/local.py` (modified) | Opt-in request/response body logging with key-based redaction, dev-only guard |
| Phase 3 — image validators | `utils/validators.py` (modified, +28 lines) | `validate_image_size()`, `validate_image_mime()` |
| Phase 3 — export helpers | `utils/export.py` (new); `pyproject.toml` (modified) | `csv_response()`, `xlsx_response()` with formula-injection sanitization |
| Phase 3 — upload paths + outbox | `utils/models/_upload_paths.py`, `utils/models/_outbox.py`, `utils/outbox.py` (new); `utils/models/__init__.py` (modified) | `make_upload_path()`, abstract `BaseOutbox`, `process_outbox_entry()` |
| Phase 3 — ops scripts | `scripts/smoke.sh`, `docker/scripts/run-celery-worker.sh`, `docker/scripts/run-celery-beat.sh` (new); `docker-compose.yml`, `.coveragerc` (modified) | Smoke probe script; parameterized Celery worker/beat entrypoints; remaining coverage omits/excludes |
| Phase 3 — transactional email | `notifications/` app (new: `apps.py`, `services/transactional_email.py`, `tasks.py`, `templates/emails/*.html`, `tests/**`); `config/settings/apps_middlewares.py`, `pytest.ini` (modified) | Event-code → template registry, `transaction.on_commit`-deferred dispatch, autoretry send task |
| App scaffold | `static/exp_app/tasks.py` (new), `static/exp_app/tests/tasks/__init__.py` (new) | Adds a Celery task template + test-dir stub to `starttemplateapp`'s generated scaffold |
| Supporting | `pyproject.toml`, `uv.lock` (modified) | `openpyxl`, `phonenumbers` (runtime); `sentry-sdk[django,celery]` (optional `production` extra) |
| Test-infra fix | `pytest.ini` (modified) | `[tool:pytest]` → `[pytest]` (the old header silently disabled `addopts`/`testpaths`/coverage floor); `--cov=notifications` + `notifications/tests` added |
| Test-infra fix | `config/settings/spectacular.py` (modified, +1 line) | `OAS_VERSION = '3.1.0'` so nullable fields validate natively |

## Refactors Performed

- `pytest.ini`'s `[tool:pytest]` section header corrected to `[pytest]` — the previous header meant the 80% coverage gate, `testpaths`, and `addopts` were never actually active on a bare `uv run pytest` invocation.
- `accounts/controllers/_auth.py`: added explicit per-method `operation_id`s on `CustomActivationView.get`/`post` to resolve an OpenAPI operationId collision with djoser's built-in activation routes (schema-only change, no behavior change).
- `docker-compose.yml` celery_worker/celery_beat `command:` changed from inline `uv run celery ...` to the new parameterized `docker/scripts/run-celery-*.sh` entrypoints.

## Reused Logic

- Did not recreate: Pydantic settings, primary/replica DB routing (`config/db_router.py`, `config/db_utils.py`, `config/middleware/db_consistency.py`), Unfold admin, Factory Boy factories, layered app scaffold (`starttemplateapp`), Loguru logging base (`config/logger.py`), existing Celery infrastructure (app + beat + worker docker services) — confirmed present per `BACKPORT_PLAN.md` "What already exists" and left untouched except for the additive settings listed above.
- `config/logger.py`'s existing Loguru sink setup was extended (patched), not replaced.

## Related Tests Added

| File | Test(s) | Covers |
|------|---------|--------|
| `utils/tests/test_errors.py` | catalog/exception shape | Error catalog + `AppAPIError` |
| `utils/tests/test_api_response.py` | envelope shape | `ok()` / `err_single()` |
| `utils/tests/test_drf_error_envelope.py` | field/status mapping | DRF error normalization |
| `config/tests/test_exception_handler.py` | branch-by-branch | Exception handler mapping incl. login 401 split |
| `config/tests/test_request_id.py` | header propagation | `RequestIdMiddleware` |
| `config/tests/test_health.py` | liveness/readiness incl. failure paths | `/health/`, `/ready/` |
| `config/tests/test_production_settings.py` | boot asserts | Production hardening |
| `config/tests/test_access_log.py` | skip/enrich paths | `AccessLogMiddleware` |
| `config/tests/test_monitoring.py` | no-op / configured paths | `configure_sentry()` |
| `config/tests/test_debug_payload.py` | redaction, dev-only guard | `DebugPayloadMiddleware` |
| `utils/tests/test_throttles.py` | scope assertions | `AuthLoginThrottle`, `PasswordResetThrottle` |
| `utils/tests/test_pagination.py` | page/no-page/edge cases | `paginate_or_ok()` |
| `utils/tests/test_openapi_serializers.py` | schema shape | `ApiEnvelopeJsonListSerializer` |
| `utils/tests/test_export.py` | formula-injection sanitization | `csv_response()`, `xlsx_response()` |
| `utils/tests/test_upload_paths.py` | path shape | `make_upload_path()` |
| `utils/tests/test_outbox.py` | success/failure paths | `process_outbox_entry()` |
| `utils/tests/test_image_validators.py` | size/mime edge cases | `validate_image_size()`, `validate_image_mime()` |
| `accounts/tests/tasks/test_example.py` | task idempotency | `example_cleanup_task` |
| `notifications/tests/services/test_transactional_email.py` | dispatch/unknown-event/missing-template paths | `send_transactional_email()` |
| `notifications/tests/tasks/test_send.py` | send + redaction | `send_transactional_email_task` |
| `accounts/tests/controllers/test_auth.py` (rewritten) | envelope + status assertions | Login 401/422 split, activation, etc. |

Full suite: 480 tests passing, 85.24% coverage (floor 80%). `python manage.py spectacular --validate --fail-on-warn` exits 0 under OAS 3.1.0.

## Documentation Updated

- `docs/README.md` — created as the docs index (none existed previously)
- `docs/API_CONTRACT.md` — created: response envelope, error-code catalog, HTTP status mapping, throttling defaults, pagination usage, health/readiness endpoints
- `docs/BACKEND_UTILITIES.md` — created: transactional email pattern, export helpers, upload-path/outbox utilities, Celery task template, Sentry hook, debug-payload middleware
- `CHANGELOG.md` — Added/Changed/Fixed/Security entries for this backport
