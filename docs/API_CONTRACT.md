# API contract

Canonical convention rules live in `.claude/rules/api.md`. This page documents the concrete implementation shipped in this template.

## Response envelope

Every error response (and any success response a view builds via `utils.api_response.ok`) follows:

```json
// Success — utils.api_response.ok(data, request, status=200, meta_extra=None)
{"success": true, "data": {...}, "meta": {"request_id": "req_...", "version": "v1"}}

// Single error — utils.api_response.err_single(code, request, status=400, details=None)
{"success": false, "error": {"code": "AUTH__INVALID_CREDENTIALS", "details": {}}, "meta": {"request_id": "req_...", "version": "v1"}}

// Multiple validation errors — utils.drf_error_envelope.validation_error_response (always HTTP 422)
{"success": false, "errors": [{"code": "VALIDATION__MISSING_FIELD", "details": {"field": "email"}}], "meta": {...}}
```

- `meta.request_id` comes from `request.request_id`, set by `config.middleware.request_id.RequestIdMiddleware` from the incoming `X-Request-ID` header (or generated as `req_<uuid hex[:24]>`); the same value is echoed back in the `X-Request-ID` response header and injected into every Loguru log line via the `request_id` extra field.
- There is no `message` field anywhere — clients consume `error.code` / `errors[].code` only.
- **Error responses are auto-wrapped everywhere** (via the custom exception handler below, for anything a view `raise`s). **Success responses are enveloped where a view explicitly wraps them** — either directly via `ok()`/`paginate_or_ok()`, or via a `finalize_response()` override on a viewset (see `accounts.controllers._auth.CustomUserViewSet`, which wraps every djoser-inherited CRUD action this way). As of the `accounts` auth-core backport, the entire `accounts` API surface — user CRUD (list/create/retrieve/update/partial_update/me), login, refresh, verify, logout, activation — is enveloped on both success and failure; see `docs/AUTH.md`. A new app that reuses djoser/SimpleJWT views directly should add the same `finalize_response()` pattern rather than leaving success bodies raw.

## Exception handler

`config.exception_handler.custom_exception_handler` is wired via `REST_FRAMEWORK['EXCEPTION_HANDLER']` (`config/settings/restframework.py`). Branch order is fixed and must not be reordered (see the module docstring):

| Exception | Code | Status |
|---|---|---|
| `errors.exceptions.AppAPIError` | `exc.code` | `exc.status_code` |
| Login (`TokenObtainPairView`) `ValidationError` with non-field detail | `AUTH__INVALID_CREDENTIALS` | 401 |
| SimpleJWT `InvalidToken` / `TokenError` | `AUTH__TOKEN_INVALID` | 401 |
| `AuthenticationFailed` (non-login) | `AUTH__TOKEN_INVALID` | 401 |
| `NotAuthenticated` | `AUTH__UNAUTHENTICATED` | 401 |
| `Http404` / DRF `NotFound` | `RESOURCE__NOT_FOUND` | 404 |
| DRF/Django `PermissionDenied` | `PERMISSION__DENIED` | 403 |
| `Throttled` | `RATE_LIMIT__EXCEEDED` (with `details.retry_after`) | 429 |
| DRF `ValidationError` (all other cases) | `VALIDATION__*` per field (see mapping below) | 422 |
| Other DRF built-in responses (`{"detail": ...}` for 400/401/403/404/405/406/409/415/429) | coerced via `utils.drf_error_envelope.coerce_drf_error_response` | unchanged status |
| Unhandled `Exception` | `INTERNAL__ERROR` (logged) | 500 |

**Login 401/422 split (locked decision):** a login request with bad credentials (wrong password/unknown user) returns **401 `AUTH__INVALID_CREDENTIALS`**. A login request with a *missing field* (e.g. no `password` submitted) still returns **422 `VALIDATION__MISSING_FIELD`** — only the credentials-authentication failure is special-cased to 401.

`INTERNAL__ERROR` is 5xx-only; no 4xx status is ever mapped to it (`.claude/rules/api.md`).

## Error catalog (`errors/catalog.py`)

Universal codes shipped in the template (accessible as string constants or via the `E` namespace, e.g. `E.RESOURCE__NOT_FOUND`):

| Code | Namespace |
|---|---|
| `AUTH__UNAUTHENTICATED`, `AUTH__TOKEN_EXPIRED`, `AUTH__TOKEN_INVALID`, `AUTH__INVALID_CREDENTIALS`, `AUTH__ACCOUNT_INACTIVE`, `AUTH__PASSWORD_RESET_DISABLED`, `AUTH__EMAIL_VERIFICATION_DISABLED` | AUTH |
| `VALIDATION__MISSING_FIELD`, `VALIDATION__INVALID_FORMAT`, `VALIDATION__INVALID_VALUE` | VALIDATION |
| `PERMISSION__DENIED`, `PERMISSION__INSUFFICIENT_ROLE` | PERMISSION |
| `RESOURCE__NOT_FOUND`, `RESOURCE__ALREADY_EXISTS`, `RESOURCE__CONFLICT` | RESOURCE |
| `RATE_LIMIT__EXCEEDED` | RATE_LIMIT |
| `INTERNAL__ERROR`, `INTERNAL__SERVICE_UNAVAILABLE` | INTERNAL |
| `NOTIFICATION__EMAIL_DELIVERY_FAILED` | NOTIFICATION |

Some codes (e.g. `AUTH__ACCOUNT_INACTIVE`, `AUTH__PASSWORD_RESET_DISABLED`, `AUTH__EMAIL_VERIFICATION_DISABLED`, `INTERNAL__SERVICE_UNAVAILABLE`, `NOTIFICATION__EMAIL_DELIVERY_FAILED`) are forward-looking — defined for the catalog contract but not yet emitted by any live endpoint. New namespaces must be discussed before use (`.claude/rules/api.md`).

## Throttling (`utils/throttles.py`, `config/settings/restframework.py`)

```python
DEFAULT_THROTTLE_CLASSES = [AnonRateThrottle, UserRateThrottle]
DEFAULT_THROTTLE_RATES = {
    "anon": "100/hour",
    "user": "1000/hour",
    "auth_login": "10/minute",
    "auth_password_reset": "5/hour",
}
```

Named scoped throttle classes for opting individual views in: `utils.throttles.AuthLoginThrottle` (scope `auth_login`), `utils.throttles.PasswordResetThrottle` (scope `auth_password_reset`). A throttled request returns 429 `RATE_LIMIT__EXCEEDED` with `error.details.retry_after` (seconds).

## Pagination (`utils/pagination.py`)

`paginate_or_ok(viewset, queryset, serializer_class, request)` — for non-`ModelViewSet` list endpoints:

- No `?page` query param → returns up to 100 rows (`_MAX_PAGE_SIZE`), no pagination metadata.
- `?page=<n>` → returns a page (default `page_size=20`, clamped to `[1, 100]` via `?page_size=`) plus `meta.pagination = {page, page_size, has_next, has_previous}`.
- `has_next` is detected by over-fetching one extra row per page — no `COUNT(*)` query.

## Health / readiness (`config/health.py`)

| Endpoint | Behavior |
|---|---|
| `GET /health/` | Liveness. No dependency probes. Always `200 "ok"` (plain text) if the process is up. |
| `GET /ready/` | Readiness. Probes DB (`SELECT 1`), Redis (`PING`), Celery broker (`control.ping`, or treated as OK when `CELERY_TASK_ALWAYS_EAGER` is set — e.g. under tests). Returns `200` JSON `{"db": {...}, "redis": {...}, "celery": {...}}` when all pass, `503` with per-check detail when any fails. |

Both routes are registered at the root in `config/urls.py` (no `/api/` prefix, no auth). The `Dockerfile` adds `HEALTHCHECK CMD curl -f http://localhost:8000/health/`. `scripts/smoke.sh` probes both plus (optionally, with `SMOKE_JWT` set) an authenticated endpoint.

## Production hardening (`config/django/production.py`)

Boot-time assertions (raise `AssertionError` on misconfiguration): `DEBUG` must be `False`; `ALLOWED_HOSTS` must be set and not `["*"]`. Security settings applied: `SECURE_HSTS_SECONDS=31536000` (+ subdomains + preload), `SECURE_SSL_REDIRECT`, `SESSION_COOKIE_SECURE`, `CSRF_COOKIE_SECURE`, `SECURE_CONTENT_TYPE_NOSNIFF`, `SECURE_REFERRER_POLICY="same-origin"`, `X_FRAME_OPTIONS="DENY"`, `SECURE_PROXY_SSL_HEADER` (for PaaS TLS termination). `config/settings/corsheaders.py` strips loopback origins (`localhost`, `127.0.0.1`, `*.localhost`) from `CORS_ALLOWED_ORIGINS` whenever `settings.DJANGO_DEBUG` is false.

## OpenAPI schema

`SPECTACULAR_SETTINGS['OAS_VERSION'] = '3.1.0'` (`config/settings/spectacular.py`). Reusable envelope-shaped schema building blocks for `@extend_schema(...)`:

- `utils.openapi_serializers.ApiEnvelopeJsonListSerializer` — list-response shim (`many=False`) to stop drf-spectacular's list heuristic from double-wrapping envelope `data`.
- `utils.schemas.envelope` — Pydantic models (`ApiMeta`, `ApiErrorEnvelope`, `ApiValidationErrorsEnvelope`, `ApiSuccessEnvelope`) for OpenAPI documentation only (no runtime validation).
- `utils.api_openapi` — pre-built `OpenApiExample`/`OpenApiResponse` fragments (`AUTHENTICATED_READ_RESPONSES`, `AUTHENTICATED_WRITE_RESPONSES`, and individual `UNAUTHENTICATED_RESPONSE` / `PERMISSION_DENIED_RESPONSE` / `NOT_FOUND_RESPONSE` / `VALIDATION_ERROR_RESPONSE`) using only catalog codes — compose these into `@extend_schema(responses={...})` rather than inventing new example payloads.

Validate with `uv run python manage.py spectacular --validate --fail-on-warn --settings=config.django.test` before merging any schema-affecting change.
