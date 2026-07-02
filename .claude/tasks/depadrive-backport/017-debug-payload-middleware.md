# 017 — Debug Payload Middleware

**Status:** [PENDING]
**Phase:** 3
**Group:** A (concurrent with 018–023)
**Risk:** LOW
**Effort:** 30m
**Dependencies:** Phase 2 complete

## Goal
Add `DebugPayloadMiddleware` (opt-in via `REQUEST_RESPONSE_DEBUG`) that logs request/response bodies with sensitive fields redacted, and refuses to run when `DEBUG=False`.

## Context
Local debugging aid. Must never activate in production and must never leak secrets.

## SRC reference to adapt from
`SRC:config/middleware/debug_payload.py` — gated by env; `ImproperlyConfigured` if activated with `DEBUG=False`; recursive `_redact()` over ~20 key names; skips `/admin`, `/static`, `/media`, `/health*`, `/api/schema*`, `/silk/`; caps body ~4KB, UA 120 chars.

## DEBUG flag — READ THIS
The **pydantic** `MainSettings` field is `DJANGO_DEBUG` (env alias `DEBUG`); there is NO pydantic `settings.DEBUG` (`config/settings/config.py:109`) — referencing it raises `AttributeError`. Rules for this subtask:
- Read the feature flag `REQUEST_RESPONSE_DEBUG` from the **pydantic** settings (`from config.settings.config import settings`).
- Read the resolved DEBUG state from **`django.conf.settings.DEBUG`** (the resolved Django global) OR pydantic `settings.DJANGO_DEBUG` — **never** pydantic `settings.DEBUG`.

## Files Owned
- `config/middleware/debug_payload.py` (C)
- `config/tests/test_debug_payload.py` (C)
- `config/django/local.py` (M — sole owner)
- `config/settings/config.py` (M — Phase-3 owner)

> `config.py` was edited by 016 (Phase 2) — different phase, safe. Add the new field to `MainSettings`.

## Implementation Steps

### Step 1 — `config/settings/config.py`
Add to `MainSettings`:
```python
REQUEST_RESPONSE_DEBUG: bool = Field(default=False, description="Log request/response bodies (dev only)")
```

### Step 2 — `config/middleware/debug_payload.py`
- Redaction key set (~20): `password, token, access, refresh, secret, otp, api_key, apikey, authorization, auth, client_secret, private_key, card, cvv, pin, session, cookie, signature, credentials, jwt`.
- `_redact(value)`: recursively deep-copy dict/list, replacing any key in the set with `"[REDACTED]"`.
- `class DebugPayloadMiddleware(MiddlewareMixin)`:
  - Imports: `from django.conf import settings as dj_settings` and `from config.settings.config import settings as app_settings`.
  - In `__init__`/first call: if `app_settings.REQUEST_RESPONSE_DEBUG` is truthy AND `not dj_settings.DEBUG` → raise `django.core.exceptions.ImproperlyConfigured`. (Use `dj_settings.DEBUG`, the resolved Django global — NOT pydantic `settings.DEBUG`.)
  - `process_request`: if not enabled, no-op. Else skip excluded paths; parse JSON body (cap ~4KB), redact, `logger.bind(...).debug("debug.request")`.
  - `process_response`: if enabled and not skipped, parse/redact response body (JSON only, cap size), `logger.debug("debug.response")`; return response.
  - Use `from config.logger import logger`.

### Step 3 — `config/django/local.py`
Conditionally add the middleware when the flag is on. The file currently appends silk middleware under `if DEBUG:`. Extend:
```python
from config.settings.config import settings as _cfg
if getattr(_cfg, "REQUEST_RESPONSE_DEBUG", False) and DEBUG:
    MIDDLEWARE += ["config.middleware.debug_payload.DebugPayloadMiddleware"]
```
Here the bare `DEBUG` is the resolved Django global from `base.py` (valid); `_cfg.REQUEST_RESPONSE_DEBUG` is the pydantic flag. Keep the existing silk block intact.

## Tests (`config/tests/test_debug_payload.py`)
- `_redact({"password": "x", "email": "a@b.c", "nested": {"token": "t"}})` → password/token become `[REDACTED]`, email preserved.
- Enabling the middleware with `DEBUG=False` raises `ImproperlyConfigured` (use `django.test.override_settings(DEBUG=False)` + patch the pydantic flag True, or construct the middleware directly).
- Excluded paths (`/admin/`, `/health/`) produce no debug log (patch logger).
- A JSON request body with a `password` key is logged redacted (patch logger; assert `[REDACTED]` in the emitted payload, plaintext secret absent).
- No DB required.

## Validation
```bash
uv run pytest config/tests/test_debug_payload.py -x -v --ds=config.django.test
```

## Acceptance Criteria
- [ ] `REQUEST_RESPONSE_DEBUG` field added to `MainSettings`.
- [ ] Middleware refuses to run when `DEBUG=False` (raises `ImproperlyConfigured`), checking `django.conf.settings.DEBUG` — never pydantic `settings.DEBUG`.
- [ ] ~20 sensitive keys redacted recursively; excluded paths skipped.
- [ ] Registered in `local.py` only under the flag + DEBUG; tests pass.
