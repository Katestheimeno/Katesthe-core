# 014 — Enhanced production security (2.4)

**Status:** [PENDING]
**Phase:** 2
**Group:** prod
**Risk:** LOW
**Effort:** 25m
**Dependencies:** 007 (shares `production.py`, edit after 007)

## Goal
Add `CSRF_TRUSTED_ORIGINS` (derived from `ALLOWED_HOSTS`) in production, and set the baseline security headers in `base.py`, reconciling the referrer policy to a single value.

## Context
`production.py` already sets `SECURE_PROXY_SSL_HEADER`, HSTS, `X_FRAME_OPTIONS`, `SECURE_CONTENT_TYPE_NOSNIFF`, and `SECURE_REFERRER_POLICY="same-origin"`. It does NOT set `CSRF_TRUSTED_ORIGINS`. This is the **Phase-2 owner** of `production.py` (chain 007→014). `base.py` does `from config.settings import *`. Avoid duplicating what production already has.

## Existing pattern to follow
`SRC:config/django/production.py` (`CSRF_TRUSTED_ORIGINS` derivation) and `SRC:config/django/base.py` (baseline security constants).

## Files Owned
- `config/django/production.py` (M — owner #2)
- `config/django/base.py` (M)
- `config/tests/test_enhanced_security.py` (C)

## Implementation Steps

### Step 1 — `production.py`
```python
CSRF_TRUSTED_ORIGINS = [f"https://{h}" for h in ALLOWED_HOSTS if h != "*"]
```
`ALLOWED_HOSTS` is already resolved in the settings this file inherits. Do NOT re-declare `SECURE_PROXY_SSL_HEADER`/HSTS (already present).

### Step 2 — `base.py` (baseline, all environments)
Add:
```python
X_FRAME_OPTIONS = "DENY"
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = "strict-origin-when-cross-origin"
```
**Referrer reconciliation:** `base.py` now sets `SECURE_REFERRER_POLICY = "strict-origin-when-cross-origin"`. Update the existing `production.py` line that sets `SECURE_REFERRER_POLICY = "same-origin"` to remove the duplicate so there is a single source of truth (production inherits the base value). This also matches what `SecurityHeadersMiddleware` (013) reads via `getattr(settings, "SECURE_REFERRER_POLICY", ...)`.

## Tests (`config/tests/test_enhanced_security.py`)
- Under test settings (inherits base): `settings.X_FRAME_OPTIONS == "DENY"`, `settings.SECURE_CONTENT_TYPE_NOSNIFF is True`, `settings.SECURE_REFERRER_POLICY == "strict-origin-when-cross-origin"`.
- Production `CSRF_TRUSTED_ORIGINS` derivation: assert the list-comprehension logic (e.g. via a small subprocess boot of production with a set `ALLOWED_HOSTS`, mirroring `config/tests/test_production_settings.py`), or unit-test the comprehension against a sample host list.

## Validation
```bash
uv run pytest config/tests/test_enhanced_security.py -x -v --ds=config.django.test
```

## Acceptance Criteria
- [ ] `CSRF_TRUSTED_ORIGINS` derived from `ALLOWED_HOSTS` (excludes `*`).
- [ ] Baseline security headers in `base.py`; single `SECURE_REFERRER_POLICY` value.
- [ ] No duplicate/conflicting referrer policy. Tests pass.
