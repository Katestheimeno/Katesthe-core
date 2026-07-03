# 001 — Error Catalog + AppAPIError

**Status:** [PENDING]
**Phase:** 1
**Group:** A (sequential core chain — this is the HEAD)
**Risk:** LOW
**Effort:** 25m
**Dependencies:** none

## Goal
Create the `errors/` package: a flat registry of universal error-code constants and the `AppAPIError` exception carrying a catalog code + HTTP status + details.

## Context
Every later pattern (envelope helpers, DRF normalization, exception handler, throttling) references catalog codes and/or raises `AppAPIError`. This is the foundation of the whole Phase 1 chain. The project error-code convention (`.claude/rules/api.md`): `UPPER_SNAKE_CASE`, `DOMAIN__ERROR_NAME`, max one `__`, verb-last.

## SRC reference to adapt from
- `SRC:errors/catalog.py` — flat module-level constants. **DO NOT copy the full 130+/200 codes.** Take ONLY the ~20 universal codes listed below.
- `SRC:errors/exceptions.py` — single polymorphic `AppAPIError(Exception)`.
- `SRC:errors/__init__.py` — re-exports `AppAPIError`.

## Files Owned
- `errors/__init__.py` (C)
- `errors/catalog.py` (C)
- `errors/exceptions.py` (C)
- `errors/apps.py` (C)
- `utils/tests/test_errors.py` (C)

> Do NOT edit `config/settings/apps_middlewares.py`. Registering `'errors'` in `PROJECT_APPS` is handled by subtask 005 (the settings owner). This subtask only creates the importable package.
> **Test placement:** the test file lives at `utils/tests/test_errors.py` (NOT `errors/tests/`) because `pytest.ini`'s explicit `testpaths` lists `utils/tests` but not an `errors/tests` dir — placing it under `utils/tests/` guarantees it is collected by the gate without touching `pytest.ini`.

## Implementation Steps

### Step 1 — `errors/catalog.py`
Define these constants (string value == constant name). Provide an `E` accessor alias so callers can do `from errors.catalog import E; E.RESOURCE__NOT_FOUND`. Implement `E` as a lightweight namespace (e.g. a class with class-level string attributes, or `types.SimpleNamespace`) exposing the same names. Codes:
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
Each constant value is exactly its name as a string, e.g. `AUTH__UNAUTHENTICATED = "AUTH__UNAUTHENTICATED"`.

> Some of these are **forward-looking** — defined for the catalog contract but not yet emitted by any Phase-1/2/3 subtask (`AUTH__TOKEN_EXPIRED`, `AUTH__ACCOUNT_INACTIVE`, `AUTH__PASSWORD_RESET_DISABLED`, `AUTH__EMAIL_VERIFICATION_DISABLED`, `RESOURCE__ALREADY_EXISTS`, `PERMISSION__INSUFFICIENT_ROLE`, `INTERNAL__SERVICE_UNAVAILABLE`, `NOTIFICATION__EMAIL_DELIVERY_FAILED`). Define them; do not write tests asserting they are produced by a live response.

### Step 2 — `errors/exceptions.py`
```python
class AppAPIError(Exception):
    def __init__(self, code: str, status_code: int = 400, details: dict | None = None):
        self.code = code
        self.status_code = status_code
        self.details = details or {}
        super().__init__(code)
```

### Step 3 — `errors/__init__.py`
Re-export `AppAPIError` and `E`: `from errors.exceptions import AppAPIError` and `from errors.catalog import E`.

### Step 4 — `errors/apps.py`
Minimal `AppConfig`: `class ErrorsConfig(AppConfig): name = "errors"; default_auto_field = "django.db.models.BigAutoField"`. (Needed because 005 registers `errors` in `PROJECT_APPS`.)

## Tests (`utils/tests/test_errors.py`)
- `AppAPIError("RESOURCE__NOT_FOUND", status_code=404, details={"x": 1})` sets `.code`, `.status_code`, `.details` correctly; `.details` defaults to `{}` when None.
- `str(AppAPIError("X"))` contains the code.
- `E.RESOURCE__NOT_FOUND == "RESOURCE__NOT_FOUND"` and every listed code is a self-named string.
- No test needs the DB.

## Validation
```bash
uv run python -c "from errors.catalog import E; from errors.exceptions import AppAPIError; print('OK')"
uv run pytest utils/tests/test_errors.py -x -v --ds=config.django.test
```

## Acceptance Criteria
- [ ] `from errors.catalog import E` and `from errors.exceptions import AppAPIError` both succeed.
- [ ] Exactly the ~20 universal codes exist; no Depadrive domain codes.
- [ ] `AppAPIError` matches the specified signature.
- [ ] `errors/apps.py` provides a valid `AppConfig`.
- [ ] Tests pass; no `apps_middlewares.py` edit here; `test_errors.py` lives under `utils/tests/`.
