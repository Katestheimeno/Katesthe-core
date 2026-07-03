# 007 — Production RS256 enforcement + env examples (1.7)

**Status:** [PENDING]
**Phase:** 1
**Group:** prod
**Risk:** LOW
**Effort:** 25m
**Dependencies:** 002 (settings fields)

## Goal
Fail fast in production when `JWT_RSA_PRIVATE_KEY` is missing; warn when `JWT_ISSUER` is unset. Document the new env vars.

## Context
`config/django/production.py` already sets boot assertions (DEBUG/ALLOWED_HOSTS), HSTS, `SECURE_PROXY_SSL_HEADER`, `X_FRAME_OPTIONS`, `SECURE_CONTENT_TYPE_NOSNIFF`, `SECURE_REFERRER_POLICY`. It does NOT yet enforce JWT keys. This is the **Phase-1 owner** of `production.py` (chain 007 → 014). Add ONLY the JWT enforcement block; leave `CSRF_TRUSTED_ORIGINS` / referrer reconciliation to 014. All three `.env.*.example` files already exist — modify, don't create.

## Existing pattern to follow
`SRC:config/django/production.py` (JWT enforcement block). Match the existing assertion/`ImproperlyConfigured` style already in this file.

## Files Owned
- `config/django/production.py` (M — owner #1)
- `.env.prod.example` (M)
- `.env.local.example` (M)
- `config/tests/test_production_jwt.py` (C)

## Implementation Steps

### Step 1 — enforcement (`production.py`)
```python
from django.core.exceptions import ImproperlyConfigured
from config.settings.config import settings as app_settings

if not app_settings.JWT_RSA_PRIVATE_KEY:
    raise ImproperlyConfigured(
        "JWT_RSA_PRIVATE_KEY is required in production. "
        "Run `python manage.py generate_jwt_keys` to create one."
    )
if not app_settings.JWT_ISSUER:
    import warnings
    warnings.warn("JWT_ISSUER not set — tokens will not carry an 'iss' claim.")
```
**`JWT_RSA_PRIVATE_KEY`/`JWT_ISSUER` are Pydantic fields on the `MainSettings` singleton, NOT Django settings.** `config/django/production.py` does NOT `from django.conf import settings` (it inherits a bare `settings` name from `base.py`'s `from config.settings import *`, which is actually the Pydantic singleton), and 003 only exposes `JWT_RSA_PRIVATE_KEY_OBJ`/`JWT_KID` to Django settings — never the raw key string. To be unambiguous, read the fields via an explicit `from config.settings.config import settings as app_settings` rather than relying on the inherited name (consistent with MASTER_TASKS Assumptions note #1).

### Step 2 — `.env.prod.example`
Add placeholders: `JWT_RSA_PRIVATE_KEY=`, `JWT_ISSUER=`, `JWT_AUDIENCE=` (with a comment: generate the key via `manage.py generate_jwt_keys`). Per plan "What NOT to Do" #10 you MAY add `JWT_RSA_PREVIOUS_PUBLIC_KEY=` here (rotation is a prod concern) but MUST NOT add it to `.env.local.example`.

### Step 3 — `.env.local.example`
Add a comment only: dev auto-generates a transient RSA key when `JWT_RSA_PRIVATE_KEY` is empty (tokens reset on restart). Do NOT add `JWT_RSA_PREVIOUS_PUBLIC_KEY`.

## Tests (`config/tests/test_production_jwt.py`)
- Subprocess/`importlib` test: booting `config.django.production` with `JWT_RSA_PRIVATE_KEY` empty raises `ImproperlyConfigured`. Mirror the existing production-settings boot test (`config/tests/test_production_settings.py`) approach (subprocess with env overrides). If the module cannot be reimported cleanly in-process, assert via a subprocess as that test does.

## Validation
```bash
uv run pytest config/tests/test_production_jwt.py -x -v --ds=config.django.test
```

## Acceptance Criteria
- [ ] Missing `JWT_RSA_PRIVATE_KEY` in production → `ImproperlyConfigured` at boot.
- [ ] Missing `JWT_ISSUER` → warning, not crash.
- [ ] Env examples updated (prod gets JWT vars; local gets only the comment). Tests pass.
