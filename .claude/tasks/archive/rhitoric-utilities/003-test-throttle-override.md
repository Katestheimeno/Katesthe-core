# 003 — Test throttle-rate override (6.3)

**Status:** [PENDING]
**Phase:** 1
**Group:** A
**Risk:** LOW
**Effort:** 15m
**Dependencies:** none

## Goal
Override all DRF throttle rates to a very high value under test settings so throttling never causes flaky test failures — regardless of which throttle scopes are defined.

## Context
`config/django/test.py` inherits `REST_FRAMEWORK` from base via `from .base import *`. Tests that hit rate-limited endpoints must not trip throttles. This is a robust one-liner that works even before/after the `rhitoric-auth-core` plan adds its 28 throttle scopes.

## Cross-plan note
The `DEFAULT_THROTTLE_RATES` keys are *defined* by the separate **rhitoric-auth-core** plan (Phase 4). Using a dict-comprehension over whatever keys exist means this override is correct both before and after that plan lands (no-op if the dict is empty). Soft dependency only — do NOT hardcode key names.

## Existing pattern to follow
- `config/django/test.py` (this repo) — existing overrides like `CELERY_TASK_ALWAYS_EAGER = True`, `PASSWORD_HASHERS = [...]`. Append the throttle override in the same flat style, after `from .base import *`.
- `SRC:config/django/test.py` — throttle-override section.

## Files Owned
- `config/django/test.py`
- `config/tests/test_throttle_override.py`

## Implementation Steps

### Step 1 — Add override to `config/django/test.py`
After the existing overrides, add:
```python
# Neutralize throttling in tests — high rate for every configured scope.
# Dict-comprehension is robust to whichever throttle scopes are registered.
REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"] = {
    k: "9999/min" for k in REST_FRAMEWORK.get("DEFAULT_THROTTLE_RATES", {})
}
```
Do NOT enumerate scope names. `REST_FRAMEWORK` is already imported into module namespace via `from .base import *`.

## Tests
Create `config/tests/test_throttle_override.py`:
- **All configured rates are neutralized:** `from django.conf import settings`; assert every value in `settings.REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"].values()` equals `"9999/min"`.
- **Empty-safe:** the comprehension does not raise when the base dict is empty (this is implicitly covered; optionally assert the key exists and is a dict).

(No `django_db` marker needed — reads settings only.)

## Validation
```bash
uv run pytest config/tests/test_throttle_override.py -x -v --ds=config.django.test
```

## Acceptance Criteria
- [ ] Override uses the dict-comprehension form (no hardcoded scope names).
- [ ] Every value in test `DEFAULT_THROTTLE_RATES` is `"9999/min"`.
- [ ] Works whether or not `rhitoric-auth-core` throttle scopes are present.
