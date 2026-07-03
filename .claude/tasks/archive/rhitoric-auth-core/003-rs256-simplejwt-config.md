# 003 — SimpleJWT RS256 configuration (1.3)

**Status:** [PENDING]
**Phase:** 1
**Group:** core
**Risk:** HIGH
**Effort:** 40m
**Dependencies:** 001 (key functions), 002 (settings fields)

## Goal
Replace the HS256 `SIMPLE_JWT` config with RS256: load/generate an RSA key, wire signing/verifying PEMs + `kid`, add cookie-transport keys, and expose key objects on Django settings for the JWKS view.

## Context
`config/settings/restframework.py` currently sets `ALGORITHM="HS256"`, `SIGNING_KEY=settings.JWT_SECRET_KEY`. It imports the pydantic `settings` (`from config.settings.config import settings`) and appends exported names to `imports`/`__all__`. This is the **first of three owners** of this file (chain: 003 → 009 → 011). Only touch the SIMPLE_JWT block + add the two exposed objects; do NOT add throttle or auth-class keys (those belong to 009 and 011).

## Existing pattern to follow
`SRC:config/settings/restframework.py` (lines ~23–136).

## Files Owned
- `config/settings/restframework.py` (M — owner #1)
- `config/tests/test_jwt_config.py` (C)

## Implementation Steps

### Step 1 — load or generate the key
At module top (after existing imports):
```python
from config.jwt_keys import (
    load_rsa_private_key, load_rsa_public_key, generate_rsa_private_key,
    compute_kid, compute_kid_from_public, private_key_to_pem, public_key_to_pem,
)
import warnings

if settings.JWT_RSA_PRIVATE_KEY:
    _rsa_private_key = load_rsa_private_key(settings.JWT_RSA_PRIVATE_KEY)
else:
    warnings.warn(
        "JWT_RSA_PRIVATE_KEY not set — generating a transient RSA key. "
        "Tokens will not survive restarts and multi-worker setups will 401.",
        stacklevel=2,
    )
    _rsa_private_key = generate_rsa_private_key()

_rsa_signing_pem = private_key_to_pem(_rsa_private_key)
_rsa_verifying_pem = public_key_to_pem(_rsa_private_key)
_rsa_kid = compute_kid(_rsa_private_key)

# Optional rotation window (previous public key for JWKS)
_rsa_previous_public_key = None
_rsa_previous_kid = None
if settings.JWT_RSA_PREVIOUS_PUBLIC_KEY:
    _rsa_previous_public_key = load_rsa_public_key(settings.JWT_RSA_PREVIOUS_PUBLIC_KEY)
    _rsa_previous_kid = compute_kid_from_public(_rsa_previous_public_key)
```

### Step 2 — replace the `SIMPLE_JWT` dict
Keep lifetimes short (`ACCESS_TOKEN_LIFETIME = timedelta(minutes=15)`, `REFRESH = timedelta(days=7)`), keep `ROTATE_REFRESH_TOKENS`/`BLACKLIST_AFTER_ROTATION`/`UPDATE_LAST_LOGIN` True. Set `ALGORITHM="RS256"`, `SIGNING_KEY=_rsa_signing_pem`, `VERIFYING_KEY=_rsa_verifying_pem`, `ISSUER=settings.JWT_ISSUER`, `AUDIENCE=settings.JWT_AUDIENCE`, `KID=_rsa_kid`, `AUTH_HEADER_TYPES=("Bearer",)`, `AUTH_TOKEN_CLASSES=("rest_framework_simplejwt.tokens.AccessToken",)`, and the cookie-transport keys: `AUTH_COOKIE_ACCESS="access_token"`, `AUTH_COOKIE_REFRESH="refresh_token"`, `AUTH_COOKIE_HTTP_ONLY=True`, `AUTH_COOKIE_PATH="/"`, `AUTH_COOKIE_REFRESH_PATH=settings.AUTH_COOKIE_REFRESH_PATH`. Preserve `USER_ID_FIELD`/`USER_ID_CLAIM`.

### Step 3 — expose key objects for JWKS
```python
JWT_RSA_PRIVATE_KEY_OBJ = _rsa_private_key
JWT_KID = _rsa_kid
JWT_PREVIOUS_PUBLIC_KEY_OBJ = _rsa_previous_public_key
JWT_PREVIOUS_KID = _rsa_previous_kid
```
Add `"JWT_RSA_PRIVATE_KEY_OBJ"`, `"JWT_KID"`, `"JWT_PREVIOUS_PUBLIC_KEY_OBJ"`, `"JWT_PREVIOUS_KID"` to the `imports` list so they land in `__all__` (and thus on Django settings). Remove the now-unused HS256 signing reference.

## Tests (`config/tests/test_jwt_config.py`)
- `from django.conf import settings as dj; dj.SIMPLE_JWT["ALGORITHM"] == "RS256"`.
- `dj.SIMPLE_JWT["SIGNING_KEY"]` is a private PEM string; `VERIFYING_KEY` a public PEM.
- `dj.JWT_KID` is a 16-char hex string equal to `compute_kid(dj.JWT_RSA_PRIVATE_KEY_OBJ)`.
- Issue a token and verify it decodes under RS256: `AccessToken.for_user(user)` round-trips (use `@pytest.mark.django_db` + a user factory).
- `dj.SIMPLE_JWT["AUTH_COOKIE_ACCESS"] == "access_token"`.

## Validation
```bash
uv run pytest config/tests/test_jwt_config.py -x -v --ds=config.django.test
```

## Acceptance Criteria
- [ ] RS256 algorithm; signing/verifying PEMs derived from the loaded/generated key.
- [ ] Transient-key warning fires when `JWT_RSA_PRIVATE_KEY` empty.
- [ ] `JWT_RSA_PRIVATE_KEY_OBJ`, `JWT_KID`, and the previous-key objects exposed on Django settings.
- [ ] Cookie-transport keys present. Tests pass.
