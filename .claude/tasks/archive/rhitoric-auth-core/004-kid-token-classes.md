# 004 — Kid token classes + issuance wiring (1.4)

**Status:** [PENDING]
**Phase:** 1
**Group:** core
**Risk:** MEDIUM
**Effort:** 35m
**Dependencies:** 003 (needs `settings.SIMPLE_JWT["KID"]`)

## Goal
Create `accounts/tokens.py` (`KidAccessToken`, `KidRefreshToken`) that inject the `kid` into the JWT header, and wire them into the issuance path so login/refresh emit `kid`-headed tokens.

## Context
External JWKS consumers (e.g. Next.js Edge) select the verifying key by the token header `kid`. SimpleJWT does not emit `kid` by default. This subtask is the **Phase-1 owner** of `accounts/serializers/auth/_token.py` and `accounts/controllers/_auth.py` (chains: `_token.py` 004→015→018; `_auth.py` 004→011→019). Touch ONLY the kid-wiring lines described here; leave the rest for later owners. `PyJWT` already ships with `djangorestframework-simplejwt` — do NOT edit `pyproject.toml`.

## Existing pattern to follow
`SRC:accounts/tokens.py` (the `_KidMixin.__str__` that mirrors `TokenBackend.encode` and injects `headers={"kid": kid}`) and `SRC:accounts/serializers/auth/_token.py` (`KidTokenRefreshSerializer.token_class = KidRefreshToken`).

## Files Owned
- `accounts/tokens.py` (C)
- `accounts/tests/test_tokens.py` (C)
- `accounts/serializers/auth/_token.py` (M — P1 lines only)
- `accounts/controllers/_auth.py` (M — P1 line only)

## Implementation Steps

### Step 1 — `accounts/tokens.py`
Define `_KidMixin` overriding `__str__()` to encode the token with `kid` in the JWT header, reading `kid` from `settings.SIMPLE_JWT.get("KID")`. Mirror SimpleJWT's `TokenBackend.encode` path (jwt.encode with the configured algorithm/signing key and `headers={"kid": kid}`). Add a module docstring noting this mirrors SimpleJWT internals and must be re-audited on every simplejwt upgrade. Then:
```python
class KidAccessToken(_KidMixin, AccessToken): ...
class KidRefreshToken(_KidMixin, RefreshToken):
    access_token_class = KidAccessToken  # ensure rotated access tokens also carry kid
```
(Confirm the correct attribute name for the access-token class on `RefreshToken` in the installed simplejwt version; if it uses a property, override `access_token` to return a `KidAccessToken`.)

### Step 2 — wire into obtain serializer (`_token.py`)
On `CustomTokenObtainPairSerializer`, set `token_class = KidRefreshToken`. Add a `KidTokenRefreshSerializer(TokenRefreshSerializer)` with `token_class = KidRefreshToken` so rotated refresh tokens keep the `kid`.
- **Re-export it.** `_token.py` uses the `imports`/`__all__ = imports` idiom and the package `__init__.py` does `from ._token import *`. Append `"KidTokenRefreshSerializer"` to `imports` (and confirm `"CustomTokenObtainPairSerializer"` is already there) — otherwise `from accounts.serializers.auth import KidTokenRefreshSerializer` in `_auth.py` (Step 3) fails at import.

### Step 3 — wire into refresh view (`_auth.py`)
On `CustomJWTTokenRefreshView`, set `serializer_class = KidTokenRefreshSerializer` (import from the serializers module). Change nothing else.

## Tests (`accounts/tests/test_tokens.py`)
- `@pytest.mark.django_db`: `str(KidAccessToken.for_user(user))` decodes with a JWT header containing `kid == settings.SIMPLE_JWT["KID"]` (use `jwt.get_unverified_header`).
- `KidRefreshToken.for_user(user).access_token` is a `KidAccessToken` and its header carries `kid`.
- Signature still validates under RS256 (decode with the verifying key).

## Validation
```bash
uv run pytest accounts/tests/test_tokens.py -x -v --ds=config.django.test
```

## Acceptance Criteria
- [ ] `KidAccessToken`/`KidRefreshToken` emit `kid` in the JWT header.
- [ ] Obtain serializer uses `KidRefreshToken`; `KidTokenRefreshSerializer` exists; refresh view uses it.
- [ ] No `pyproject.toml` change. Tests pass.
