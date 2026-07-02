# 007 — Production Security Hardening

**Status:** [PENDING]
**Phase:** 1
**Group:** D (fully independent — concurrent from the start)
**Risk:** MEDIUM
**Effort:** 40m
**Dependencies:** none

## Goal
Turn `config/django/production.py` (currently a bare `from config.django.base import *`) into a hardened production entry: boot-time assertions + security headers + CORS loopback gating. Also add the single `config/django/*` coverage-omit line (in Phase 1, so the subprocess-only production lines don't sink the coverage floor).

## Context
The template's production settings currently apply no hardening. Ship secure-by-default: fail fast on misconfiguration, force HTTPS/HSTS/secure cookies, and forbid loopback CORS origins in prod. The ~15 lines added to `production.py` are exercised only via subprocess `django.setup()` (item test), which contributes NO line coverage — so the `config/django/*` omit must be present from Phase 1, not deferred to Phase 3.

## SRC reference to adapt from
`SRC:config/django/production.py` — boot guards (DEBUG must be False; ALLOWED_HOSTS explicit; no loopback CORS; `SECURE_PROXY_SSL_HEADER` for PaaS proxies) + HSTS/secure-cookie block. Adapt to this repo (settings come from `config.settings.config.settings` via `base.py`'s `from config.settings import *`).

## DEBUG flag — READ THIS
The **pydantic** `MainSettings` field is named `DJANGO_DEBUG` (env alias `DEBUG`); there is NO pydantic attribute called `settings.DEBUG` (`config/settings/config.py:109`). Rules:
- In `production.py`, `assert not DEBUG` is fine — that bare `DEBUG` is the **resolved Django global** exported by `base.py` (`from config.settings import *`), not the pydantic object.
- In `corsheaders.py` (which imports the pydantic settings), branch on **`settings.DJANGO_DEBUG`** (or import `from django.conf import settings as dj; dj.DEBUG`). **Never** reference pydantic `settings.DEBUG` — it raises `AttributeError`.

## Files Owned
- `config/django/production.py` (M)
- `config/settings/corsheaders.py` (M — only this subtask touches it)
- `.coveragerc` (M — Phase-1 owner of the single `config/django/*` omit line ONLY)
- `config/tests/test_production_settings.py` (C)

> `.coveragerc` is co-owned across phases: **007 (Phase 1)** adds ONLY the `config/django/*` omit line; **021 (Phase 3)** adds the remaining omits + exclude-lines and MUST NOT re-add `config/django/*`. Different phases → sequential → safe.
> Subtask 016 (Phase 2) also edits `production.py` to add the `configure_sentry()` call — different phase, safe.

## Implementation Steps

### Step 1 — `config/django/production.py`
After `from config.django.base import *`, add:
```python
# Boot-time assertions
assert not DEBUG, "DEBUG must be False in production"
assert ALLOWED_HOSTS and ALLOWED_HOSTS != ["*"], "ALLOWED_HOSTS must be explicit"

# Security headers
SECURE_HSTS_SECONDS = 31536000  # 1 year
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = "same-origin"
X_FRAME_OPTIONS = "DENY"

# Respect proxy TLS termination (PaaS)
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
```
Note: `ALLOWED_HOSTS` in `base.py` is derived from `settings.ALLOWED_HOSTS` (a comma string, default `"*"`). Ensure the assertion compares the resolved list. If `base.py` stores it as a string, split on comma there or normalize here before asserting — verify the actual `base.py`/settings shape and assert against the resolved `list`.

### Step 2 — CORS loopback gate (`config/settings/corsheaders.py`)
Read the current CORS config. In production, remove/forbid loopback origins (`localhost`, `127.0.0.1`). Implement a helper that filters `CORS_ALLOWED_ORIGINS` to drop loopback hosts when not in debug, OR gate the allowed origins on an env var. Determine "production" via **`settings.DJANGO_DEBUG`** (pydantic) or `django.conf.settings.DEBUG` — NOT pydantic `settings.DEBUG`. Keep local/dev behavior unchanged (only production filters). If `corsheaders.py` currently hardcodes localhost, make it conditional on the debug flag.

### Step 3 — `.coveragerc` (single line)
Add exactly one omit entry under the existing `[run] omit =` list:
```
config/django/*
```
Do NOT touch any other omit or `exclude_lines` entry — those are subtask 021's (Phase 3). This one line lands in Phase 1 so the production-settings lines (subprocess-only) are excluded before the Phase-1/Phase-2 gates and CI evaluate the 80% floor.

## Tests (`config/tests/test_production_settings.py`)
Because `production.py` runs assertions at import, test via subprocess `django.setup()` with controlled env:
- With `DEBUG=False` and an explicit `ALLOWED_HOSTS` (e.g. `example.com`), `DJANGO_SETTINGS_MODULE=config.django.production python -c "import django; django.setup()"` exits 0.
- With `DEBUG=True`, the same import raises `AssertionError` (assert non-zero exit / captured stderr contains the message).
- Assert the security constants have the expected values by importing the module in the valid-env subprocess and printing them, or by a lightweight settings-override test.
- Loopback filter: given `CORS_ALLOWED_ORIGINS` containing `http://localhost:3000`, the production-resolved list excludes it.
Use `subprocess.run([...], env={...})` with `.env`-style overrides (include `SECRET_KEY`/`JWT_SECRET_KEY` which pydantic requires); mark `slow` if needed.

## Validation
```bash
uv run pytest config/tests/test_production_settings.py -x -v --ds=config.django.test
uv run python -c "import configparser; c=configparser.ConfigParser(); c.read('.coveragerc'); print('coveragerc ok')"
# Manual sanity (needs valid prod env vars):
# DEBUG=False ALLOWED_HOSTS=example.com SECRET_KEY=x JWT_SECRET_KEY=y uv run python -c "import os; os.environ['DJANGO_SETTINGS_MODULE']='config.django.production'; import django; django.setup(); print('prod ok')"
```

## Acceptance Criteria
- [ ] Production import fails fast on `DEBUG=True` or wildcard/empty `ALLOWED_HOSTS`.
- [ ] HSTS, SSL redirect, secure cookies, nosniff, referrer-policy, X-Frame-Options DENY, proxy SSL header all set.
- [ ] Loopback CORS origins excluded in production, unchanged in dev; the CORS gate uses `DJANGO_DEBUG`/`django.conf.settings.DEBUG`, never pydantic `settings.DEBUG`.
- [ ] `.coveragerc` gains exactly the `config/django/*` omit line (no other change here).
- [ ] Tests pass.
