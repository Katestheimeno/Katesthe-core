# 010 — Throttling / Rate Limiting

**Status:** [PENDING]
**Phase:** 2
**Group:** A (concurrent with 011–016)
**Risk:** MEDIUM
**Effort:** 30m
**Dependencies:** Phase 1 complete (needs the exception handler → `RATE_LIMIT__EXCEEDED` envelope)

## Goal
Add named `UserRateThrottle` subclasses in `utils/throttles.py` and register minimal default throttle classes + rates in `restframework.py`.

## Context
Throttled requests raise DRF `Throttled`, which the exception handler (004) maps to 429 `RATE_LIMIT__EXCEEDED`. Keep rates minimal and universal — projects add domain scopes later.

## SRC reference to adapt from
`SRC:utils/throttles.py` (named `UserRateThrottle` subclasses declaring a `scope`) and `SRC:config/settings/restframework.py` (throttle config). **Strip domain scopes** (`photo_upload`, `depanneur_location_update`).

## Files Owned
- `utils/throttles.py` (C)
- `utils/tests/test_throttles.py` (C)
- `config/settings/restframework.py` (M — Phase-2 owner)

> `restframework.py` was edited by 004 (Phase 1) — different phase, safe. Edit the existing `REST_FRAMEWORK` dict in place; do not remove 004's `EXCEPTION_HANDLER` key.

## Implementation Steps

### Step 1 — `utils/throttles.py`
Define named scoped throttles for the universal sensitive endpoints:
```python
from rest_framework.throttling import UserRateThrottle

class AuthLoginThrottle(UserRateThrottle):
    scope = "auth_login"

class PasswordResetThrottle(UserRateThrottle):
    scope = "auth_password_reset"
```
(Anon/user defaults use DRF's built-in `AnonRateThrottle`/`UserRateThrottle` — no subclass needed.)

### Step 2 — `config/settings/restframework.py`
Add to the existing `REST_FRAMEWORK` dict:
```python
'DEFAULT_THROTTLE_CLASSES': [
    'rest_framework.throttling.AnonRateThrottle',
    'rest_framework.throttling.UserRateThrottle',
],
'DEFAULT_THROTTLE_RATES': {
    'anon': '100/hour',
    'user': '1000/hour',
    'auth_login': '10/minute',
    'auth_password_reset': '5/hour',
},
```

## Tests (`utils/tests/test_throttles.py`)
- Assert `AuthLoginThrottle.scope == "auth_login"` and `PasswordResetThrottle.scope == "auth_password_reset"`.
- Integration (`@pytest.mark.django_db`): build a throwaway `APIView` with `throttle_classes = [AuthLoginThrottle]` and a rate of e.g. `2/minute` (override via settings), hit it 3× with the same client, assert the 3rd returns 429 with envelope `error.code == "RATE_LIMIT__EXCEEDED"`. Clear cache before the test (LocMemCache holds throttle counters) — `from django.core.cache import cache; cache.clear()`.
- Assert `DEFAULT_THROTTLE_RATES` contains the four keys.

## Validation
```bash
uv run pytest utils/tests/test_throttles.py -x -v --ds=config.django.test
```

## Acceptance Criteria
- [ ] Named throttles with `auth_login` / `auth_password_reset` scopes exist.
- [ ] Default throttle classes + the four rates registered without clobbering `EXCEPTION_HANDLER`.
- [ ] A throttled request returns 429 with the `RATE_LIMIT__EXCEEDED` envelope.
- [ ] Tests pass (cache cleared to avoid counter bleed).
