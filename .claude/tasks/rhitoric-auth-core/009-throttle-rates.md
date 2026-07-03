# 009 — Throttle rates in REST_FRAMEWORK (4.2)

**Status:** [PENDING]
**Phase:** 4
**Group:** thr
**Risk:** LOW
**Effort:** 15m
**Dependencies:** 008 (classes), 003 (shares `restframework.py` — must edit after 003)

## Goal
Point the DRF defaults at the new default throttles and register the 14 scope rates.

## Context
This is the **second of three owners** of `config/settings/restframework.py` (chain 003 → 009 → 011). Only edit the `DEFAULT_THROTTLE_CLASSES` and `DEFAULT_THROTTLE_RATES` keys inside the existing `REST_FRAMEWORK` dict. Do NOT touch `SIMPLE_JWT` (003) or `DEFAULT_AUTHENTICATION_CLASSES` (011).

## Existing pattern to follow
`SRC:config/settings/restframework.py` throttle block. The current file already has a `DEFAULT_THROTTLE_RATES` dict with 4 keys — replace it.

## Files Owned
- `config/settings/restframework.py` (M — owner #2)
- `config/tests/test_throttle_rates.py` (C)

## Implementation Steps

### Step 1 — update `REST_FRAMEWORK`
```python
'DEFAULT_THROTTLE_CLASSES': [
    'utils.throttles.DefaultAnonThrottle',
    'utils.throttles.DefaultUserThrottle',
],
'DEFAULT_THROTTLE_RATES': {
    'default_anon': '60/min', 'default_user': '120/min',
    'auth_login': '10/min', 'auth_login_account': '5/hour',
    'auth_register': '5/hour', 'auth_reset': '3/hour',
    'auth_set_password': '10/hour', 'auth_refresh': '20/min',
    'auth_activation': '10/hour', 'public_list': '120/min',
    'search': '60/min', 'webhook': '200/min',
    'external_api': '300/min', 'user_mutation': '30/min',
},
```
Remove the old `anon`/`user`/`auth_password_reset` keys (the DRF built-in defaults are replaced by the `default_*` scopes).

## Tests (`config/tests/test_throttle_rates.py`)
- `from django.conf import settings`: `DEFAULT_THROTTLE_CLASSES` lists the two `utils.throttles` defaults.
- All 14 scope keys present in `DEFAULT_THROTTLE_RATES` with the exact rates above.

## Validation
```bash
uv run pytest config/tests/test_throttle_rates.py -x -v --ds=config.django.test
```

## Acceptance Criteria
- [ ] Defaults reference `DefaultAnonThrottle`/`DefaultUserThrottle`.
- [ ] All 14 rates registered; stale keys removed; `EXCEPTION_HANDLER`/`SIMPLE_JWT` untouched.
- [ ] Tests pass.
