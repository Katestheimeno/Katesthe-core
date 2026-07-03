# Changelog

## [Unreleased]

### Added

- RS256 (asymmetric) JWT signing: `config/jwt_keys.py` (RSA key generation/loading, `kid` fingerprinting, JWKS building), `accounts/tokens.py` (`KidAccessToken`/`KidRefreshToken` — kid-headed tokens for JWKS-based verification), `accounts/management/commands/generate_jwt_keys.py`, public JWKS endpoint `GET /.well-known/jwks.json` (`accounts/controllers/_jwks.py`, RFC 7517).
- HttpOnly cookie JWT authentication with CSRF enforcement: `accounts/authentication.py` (`CookieJWTAuthentication`, falls back to `Authorization: Bearer`), `auth/csrf/` cookie-bootstrap endpoint for cross-origin SPAs. Cookie-transported mutations require CSRF; bearer-header auth never does.
- Session revocation: `accounts/services/session.py` (`revoke_all_sessions`, `detect_refresh_reuse`), wired into `logout-all`, password/username change, account deletion, and refresh-token-reuse detection — all keyed on the shared cache key `auth:revoked_after:{user_id}` (also read by the WebSocket auth middleware below).
- `accounts.tasks.token_tasks.flush_expired_jwt_tokens` Celery task; `accounts/tasks.py` is now a package (`accounts/tasks/`).
- Universal throttle class hierarchy (~14 scopes: auth, password/username reset, public list, etc.) behind a single `THROTTLE_ENABLED` toggle (`utils/throttles.py`); `flush_throttles` management command.
- JWT WebSocket authentication: `utils/middleware/jwt_websocket_auth.py` (subprotocol/cookie token auth, wired in `config/asgi.py`), shared protocol helpers `utils/websocket/protocol.py` (auth-rotate, ack/nack, idempotency — catalog-coded), per-connection `utils.websocket.rate_limit.MessageRateLimiter`.
- `config.middleware.security_headers.SecurityHeadersMiddleware` and `config.middleware.liveness_probe.LivenessProbeMiddleware`.
- OpenAPI `CookieJWTAuth` security scheme (`config/spectacular_auth.py`), registered from `AccountsConfig.ready()`.

### Changed

- **Breaking:** JWT signing switched HS256 → RS256. Booting `config.django.production` without `JWT_RSA_PRIVATE_KEY` now raises `ImproperlyConfigured` instead of falling back to a transient key.
- **Breaking:** Login (`POST /auth/jwt/create/`) now sets HttpOnly cookies by default and omits `access`/`refresh` from the response body; send `X-Token-Delivery: bearer` to get the previous body-token behavior.
- JWT claims no longer include a raw `is_superuser` flag; `CustomTokenObtainPairSerializer.get_token()` now emits a `permissions` list instead.
- The response envelope now covers the full `accounts` API surface, not just error responses. Previously only explicit `ok()`/error-handler paths were enveloped and several endpoints returned raw or ad-hoc bodies; now `CustomUserViewSet` (list/create/retrieve/update/partial_update/me and the password/username reset actions), login, refresh, verify, logout, and activation all wrap their success/error bodies in `{success, data|error, meta}` with `errors/catalog.py` codes.
- WebSocket example consumer (`utils/consumers.py`) error frames now carry a catalog `code` field instead of a raw `message` string, and no longer echo raw exception text back to the client.

### Removed

- Dead djoser Token-model views `CustomTokenCreateView`/`CustomTokenDestroyView` — unrouted (`rest_framework.authtoken` isn't installed) and superseded by the JWT views.

### Security

- RS256 lets the public verification key be published via JWKS without exposing the signing secret.
- Timing-oracle defense in the login serializer: a dummy password-hash computation runs on the user-not-found/inactive-user branches so response latency can't be used to enumerate accounts.
- Refresh-token replay (reuse of an already-rotated token) revokes every outstanding session for that user, not just the replayed token.

See: `docs/changes/20260703_172451_rhitoric-auth-core-and-envelope-unification.md`

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
