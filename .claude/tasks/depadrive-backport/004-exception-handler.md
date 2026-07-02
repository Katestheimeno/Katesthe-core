# 004 — Custom Exception Handler + DRF wiring

**Status:** [PENDING]
**Phase:** 1
**Group:** A (sequential core chain)
**Risk:** HIGH
**Effort:** 50m
**Dependencies:** 001, 002, 003

## Goal
Create `config/exception_handler.py::custom_exception_handler(exc, context)` mapping exceptions to the project envelope, and wire it into DRF via `EXCEPTION_HANDLER` in `restframework.py`.

## Context
This is the switchboard that turns raised exceptions into enveloped error responses. It changes response shapes and some status codes project-wide — hence HIGH risk. **This subtask writes ONLY its own test file**; the churn to `accounts/tests/` is owned by subtask 009 (runs right after this).

## SRC reference to adapt from
`SRC:config/exception_handler.py` (SRC name is `exception_handler`; **rename to `custom_exception_handler`**). It calls DRF's default handler first, then maps.

## Files Owned
- `config/exception_handler.py` (C)
- `config/settings/restframework.py` (M — Phase-1 owner)
- `config/tests/test_exception_handler.py` (C)

> Do NOT touch `accounts/tests/`. Subtask 010 (Phase 2) also edits `restframework.py` but in a later phase — safe.

## Implementation Steps

### Step 1 — `custom_exception_handler(exc, context)`
Order of handling (return a DRF `Response` — envelope shape):
| Exception | Code | Status |
|-----------|------|--------|
| `errors.exceptions.AppAPIError` | `exc.code` | `exc.status_code` (details = `exc.details`) |
| **Login/token-obtain `ValidationError` with non-field detail** (see Step 1a) | `AUTH__INVALID_CREDENTIALS` | **401** |
| SimpleJWT `InvalidToken` / `TokenError` | `AUTH__TOKEN_INVALID` | 401 |
| DRF `AuthenticationFailed` (non-login) | `AUTH__TOKEN_INVALID` | 401 |
| DRF `NotAuthenticated` | `AUTH__UNAUTHENTICATED` | 401 |
| `django.http.Http404` / DRF `NotFound` | `RESOURCE__NOT_FOUND` | 404 |
| DRF `PermissionDenied` / Django `PermissionDenied` | `PERMISSION__DENIED` | 403 |
| DRF `Throttled` | `RATE_LIMIT__EXCEEDED` | 429, `details={"retry_after": exc.wait}` |
| DRF `ValidationError` (other, incl. login field errors) | per-field `VALIDATION__*` via `normalize_validation_detail` | **422** |
| any other `Exception` | `INTERNAL__ERROR` | 500 (log traceback) |

**Implementation shape — explicit `isinstance` branches evaluated in THIS order, BEFORE any fallback to `drf_exception_handler` + `coerce`.** `coerce_drf_error_response` (003) keys ONLY on HTTP status: it maps `401 → AUTH__UNAUTHENTICATED` and cannot produce `AUTH__TOKEN_INVALID`, nor attach `details["retry_after"]` for throttling. Therefore the distinct-code branches must be handled explicitly here — do NOT rely on `coerce` for them:
1. `request = context.get("request")`; `view = context.get("view")`.
2. `isinstance(exc, AppAPIError)` → `err_single(exc.code, request, status=exc.status_code, details=exc.details)`.
3. **Login special-case (Step 1a)** — token-obtain view + `ValidationError` with non-field detail → `err_single(AUTH__INVALID_CREDENTIALS, request, status=401)`.
4. `isinstance(exc, (InvalidToken, TokenError))` → `err_single(AUTH__TOKEN_INVALID, request, status=401)`.
5. `isinstance(exc, AuthenticationFailed)` (reached only for non-login, since login is caught at step 3 and returns a `ValidationError` not `AuthenticationFailed`) → `err_single(AUTH__TOKEN_INVALID, request, status=401)`.
6. `isinstance(exc, NotAuthenticated)` → `err_single(AUTH__UNAUTHENTICATED, request, status=401)`.
7. `isinstance(exc, (Http404, NotFound))` → `err_single(RESOURCE__NOT_FOUND, request, status=404)`.
8. `isinstance(exc, (DRFPermissionDenied, DjangoPermissionDenied))` → `err_single(PERMISSION__DENIED, request, status=403)`.
9. `isinstance(exc, Throttled)` → `err_single(RATE_LIMIT__EXCEEDED, request, status=429, details={"retry_after": getattr(exc, "wait", None)})`.
10. `isinstance(exc, DRFValidationError)` → `validation_error_response(normalize_validation_detail(exc.detail), request)` (422).
11. Fallback: `response = drf_exception_handler(exc, context)`. If not None → `return coerce_drf_error_response(request, response)` (safety net for anything the branches above missed; 003's explicit status map keeps 4xx out of INTERNAL).
12. If `response is None` (unhandled) → `logger.bind(...).exception("internal.unhandled_exception")` (`from config.logger import logger`), then `err_single(INTERNAL__ERROR, request, status=500)`.

Import helpers from `utils.api_response` and `utils.drf_error_envelope`; codes from `errors.catalog`; JWT exceptions (`InvalidToken`, `TokenError`) from `rest_framework_simplejwt.exceptions`; DRF exceptions (`NotFound`, `NotAuthenticated`, `AuthenticationFailed`, `PermissionDenied as DRFPermissionDenied`, `Throttled`, `ValidationError as DRFValidationError`) from `rest_framework.exceptions`; `Http404` from `django.http`; `PermissionDenied as DjangoPermissionDenied` from `django.core.exceptions`.

### Step 1a — LOCKED: login bad-credentials → 401 `AUTH__INVALID_CREDENTIALS` (keyed on the REAL mechanism)
The real login path is `CustomJWTTokenCreateView(TokenObtainPairView)` (`accounts/controllers/_auth.py:190`) using `CustomTokenObtainPairSerializer`, whose `validate()` (`accounts/serializers/auth/_token.py:50-98`) raises a plain **DRF `serializers.ValidationError`** for EVERY auth failure (invalid creds, unknown user, disabled account, and its own missing-creds branch). It **NEVER raises `AuthenticationFailed`** — so keying the special case on `AuthenticationFailed` would make it dead code and silently break locked decision #7.

**Key the split on the `ValidationError` DETAIL SHAPE when the view is a `TokenObtainPairView` subclass:**
- `context["view"]` is (a subclass of) `rest_framework_simplejwt.views.TokenObtainPairView` **AND** `isinstance(exc, DRFValidationError)`, then:
  - detail is a **non-field error** (a list, a string, or a dict whose only key is `"non_field_errors"` / DRF's `NON_FIELD_ERRORS`) → **401 `AUTH__INVALID_CREDENTIALS`**.
  - detail has **field keys** (e.g. `{"password": ["This field is required."]}`) → fall through to the normal **422** validation path (step 10).
- Note: the 401/422 split rides on "non-field detail vs field-keyed detail." A truly-absent field usually fires DRF **field** validation first (→ field-keyed detail → 422), so the serializer's own missing-creds non-field branch is effectively unreachable in practice — that is fine; both "missing field" outcomes correctly land on 422, and only genuine credential rejection (non-field) becomes 401.
- Keep the detection this narrow — do not broaden to all `ValidationError`s or all views.

### Step 2 — wire into DRF
In `config/settings/restframework.py`, inside the existing `REST_FRAMEWORK` dict (it already exists — do NOT recreate), add:
```python
'EXCEPTION_HANDLER': 'config.exception_handler.custom_exception_handler',
```

## Tests (`config/tests/test_exception_handler.py`)
Build `context = {"request": <APIRequestFactory request with request_id>, "view": <view or None>}` and call the handler directly (unit) plus at least one integration test via a throwaway `APIView`.
- `AppAPIError("RESOURCE__NOT_FOUND", status_code=404, details={"pk": 1})` → 404, `error.code == "RESOURCE__NOT_FOUND"`, `error.details == {"pk": 1}`.
- `Http404()` → 404 `RESOURCE__NOT_FOUND`.
- `NotAuthenticated()` → 401 `AUTH__UNAUTHENTICATED`.
- `InvalidToken()` → 401 `AUTH__TOKEN_INVALID` (verifies the explicit branch, NOT `coerce`).
- Non-login `AuthenticationFailed()` (view = None or a plain `APIView`) → 401 `AUTH__TOKEN_INVALID` (closes the non-login auth-failure branch).
- `PermissionDenied()` → 403 `PERMISSION__DENIED`.
- `Throttled(wait=30)` → 429 `RATE_LIMIT__EXCEEDED`, `details["retry_after"] == 30` (verifies the explicit branch attaches `retry_after`, which `coerce` cannot).
- **Login credential failure:** `ValidationError("Invalid credentials.")` (non-field) with `context["view"]` = a `TokenObtainPairView` subclass instance → **401 `AUTH__INVALID_CREDENTIALS`**.
- **Login missing field:** `ValidationError({"password": ["This field is required."]})` (field-keyed) with the same token-obtain view → **422**, `errors[0].code == "VALIDATION__MISSING_FIELD"`.
- Non-login `ValidationError({"email": ["This field is required."]})` (view = None or a plain `APIView`) → **422**.
- Generic `Exception("boom")` → 500 `INTERNAL__ERROR`; assert traceback logging invoked (patch `config.logger.logger`).
- Integration: an `APIView` whose `get` raises `AppAPIError(...)`, routed through DRF, returns the envelope with correct status.

## Validation
```bash
uv run pytest config/tests/test_exception_handler.py -x -v --ds=config.django.test
uv run python -c "from config.exception_handler import custom_exception_handler; print('OK')"
```

## Acceptance Criteria
- [ ] Distinct-code exceptions (`InvalidToken`→`AUTH__TOKEN_INVALID`, `Throttled`→`retry_after`) are produced by explicit `isinstance` branches, NOT by the status-only `coerce` fallback.
- [ ] **Login `ValidationError` with non-field detail on a `TokenObtainPairView` → 401 `AUTH__INVALID_CREDENTIALS`**; login field-keyed detail → 422; the special case keys on the ValidationError detail shape (no `AuthenticationFailed` reliance).
- [ ] Non-login `ValidationError` → 422; other exceptions map per the table.
- [ ] `EXCEPTION_HANDLER` registered in the existing `REST_FRAMEWORK` dict.
- [ ] Unhandled exceptions log a traceback via `config.logger.logger` and return 500 `INTERNAL__ERROR`.
- [ ] No edits to `accounts/tests/` (that is subtask 009).
- [ ] Own tests pass (incl. both login split cases).
