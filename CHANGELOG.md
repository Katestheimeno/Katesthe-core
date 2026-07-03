# Changelog

## [Unreleased]

### Fixed

- Docker `db_replica`: primary now uses a mounted `pg_hba.conf` (`hba_file`) so replication connections from the Docker network match `host replication` / `hostnossl` rules (PostgreSQL’s `all` does not match replication DB). Replica entrypoint creates/updates `replicator` with `REPLICATOR_PASSWORD` before `pg_basebackup` so existing primary volumes work without manual SQL.

### Changed

- `DB_ROUTING_ENABLED` now defaults to `true` and registers `PrimaryReplicaRouter` whenever Postgres is used; with no `DB_REPLICA_HOSTS`, reads still use the primary. Set `DB_ROUTING_ENABLED=false` to disable the router.

### Added

- Docker Compose streaming read replica (`db_replica`): primary init scripts under `docker/postgres/primary/`, replica entrypoint `docker/postgres/replica/docker-entrypoint-replica.sh`, `REPLICATOR_PASSWORD`, and example `DB_REPLICA_HOSTS=db_replica` for local read traffic splitting.
- Primary/read-replica database routing: `config/db_router.PrimaryReplicaRouter`, `config/db_utils.read_from_primary`, `config.middleware.db_consistency.DBConsistencyMiddleware`, and settings symbols `REPLICA_DATABASE_ALIASES`, `DB_ROUTING_ENABLED`, `DATABASE_ROUTERS` when replicas are enabled.
- Environment variables `DB_PRIMARY_*`, `DB_REPLICA_*`, `USE_SQLITE`, and `DB_ROUTING_ENABLED` in `config/settings/config.py` (replaces app-level `DATABASE_URL`).

### Changed

- Database configuration is built from explicit `DB_PRIMARY_*` fields instead of `dj-database-url` / `DATABASE_URL`.

### Removed

- `dj-database-url` dependency.

See: `docs/changes/20250326_primary-replica-db-routing.md`, `docs/changes/20250326_docker-streaming-replica-read-splitting.md`

### Added

- Error catalog + `AppAPIError`: `errors/catalog.py` (`E.*` namespaced codes — `AUTH__*`, `VALIDATION__*`, `PERMISSION__*`, `RESOURCE__*`, `RATE_LIMIT__EXCEEDED`, `INTERNAL__*`, `NOTIFICATION__EMAIL_DELIVERY_FAILED`), `errors/exceptions.py`.
- Response envelope + exception handler: `utils/api_response.ok`/`err_single`, `utils/drf_error_envelope.py`, `config/exception_handler.custom_exception_handler` (wired via `REST_FRAMEWORK.EXCEPTION_HANDLER`).
- Request-id + access-log middleware: `config.middleware.request_id.RequestIdMiddleware` (`X-Request-ID` header, `meta.request_id`), `config.middleware.access_log.AccessLogMiddleware`.
- Health/readiness probes: `GET /health/` (liveness), `GET /ready/` (DB/Redis/Celery probes, 503 on failure) — `config/health.py`.
- Throttling defaults (`utils/throttles.AuthLoginThrottle`, `PasswordResetThrottle`; `DEFAULT_THROTTLE_RATES`: `anon` 100/hour, `user` 1000/hour, `auth_login` 10/minute, `auth_password_reset` 5/hour) and a pagination helper (`utils/pagination.paginate_or_ok`).
- Celery task template (`accounts/tasks.example_cleanup_task`) and worker/beat settings (JSON-only serialization, memory/task-count recycling, time limits, prefetch=1); ops entrypoints `docker/scripts/run-celery-worker.sh`, `run-celery-beat.sh`.
- OpenAPI envelope serializers (`utils/openapi_serializers.ApiEnvelopeJsonListSerializer`), Pydantic envelope schemas (`utils/schemas/envelope.py`), reusable OpenAPI examples (`utils/api_openapi.py`).
- Optional Sentry integration: `config.settings.monitoring.configure_sentry()` (no-op unless `SENTRY_DSN` set and `sentry-sdk` installed as the `production` extra).
- CSV/XLSX export helpers with formula-injection sanitization (`utils/export.py`), upload-path factory (`utils/models.make_upload_path`), abstract transactional-outbox model + processor (`utils/models.BaseOutbox`, `utils/outbox.process_outbox_entry`).
- `notifications` app: transactional email dispatch (`notifications.services.transactional_email.send_transactional_email`, event-code → template registry) sent via `transaction.on_commit` + autoretry Celery task, Django `EMAIL_BACKEND` only (no OneSignal/Ably).
- Debug-payload middleware (`config.middleware.debug_payload.DebugPayloadMiddleware`, opt-in via `REQUEST_RESPONSE_DEBUG`, dev-only) and image upload validators (`utils.validators.validate_image_size`, `validate_image_mime`).
- CI workflow (`.github/workflows/ci.yml`): Postgres service container, `pytest` + `spectacular --validate --fail-on-warn`. Smoke-test script `scripts/smoke.sh`.
- Root `conftest.py`: project-wide fixture registration + `clear_cache_between_tests` autouse fixture (prevents throttle-counter bleed between tests).
- App scaffold (`starttemplateapp`) now generates a `tasks.py` template and `tests/tasks/` stub.

### Changed

- API error responses now use the `{success, error, meta}` / `{success, errors, meta}` envelope with machine-readable codes instead of raw DRF bodies; login failure on bad credentials returns **401 `AUTH__INVALID_CREDENTIALS`** (missing-field login input and all other validation failures remain 422 `VALIDATION__*`).
- OpenAPI schema now generates as OAS 3.1.0 (`SPECTACULAR_SETTINGS['OAS_VERSION']`), so nullable fields validate natively under `spectacular --validate --fail-on-warn`.
- Coverage floor is now enforced at 80% (`pytest.ini` `[tool:pytest]` header corrected to `[pytest]` — the previous header silently disabled `addopts`/`testpaths`/the coverage gate).
- Production settings (`config/django/production.py`) now assert `DEBUG=False` and explicit `ALLOWED_HOSTS` at boot, set HSTS/secure-cookie/`X-Frame-Options` headers, and strip loopback origins from CORS.
- `celery_worker`/`celery_beat` Docker Compose services now run through parameterized entrypoint scripts instead of inline `uv run celery ...` commands.

### Fixed

- Undeclared `phonenumbers` dependency used by `utils/validators.validate_moroccan_phone_number` — now declared in `pyproject.toml`.

### Security

- Production hardening: HSTS (1yr, subdomains, preload), `SECURE_SSL_REDIRECT`, secure session/CSRF cookies, `X_FRAME_OPTIONS=DENY`, boot-time assertions against `DEBUG=True`/wildcard `ALLOWED_HOSTS` in production.
- Debug-payload middleware refuses to activate unless Django's resolved `DEBUG` is `True` (raises `ImproperlyConfigured` otherwise) and redacts ~20 sensitive field names before logging request/response bodies.
- CSV/XLSX export helpers sanitize cells against formula injection (`=`, `+`, `@`, TAB, leading `-` on non-numeric values).

See: `docs/changes/20260702_172848_depadrive-backport.md`
