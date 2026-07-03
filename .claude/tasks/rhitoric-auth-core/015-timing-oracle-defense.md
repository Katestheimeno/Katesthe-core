# 015 — Timing-oracle defense in login (2.5)

**Status:** [PENDING]
**Phase:** 2
**Group:** tok
**Risk:** LOW
**Effort:** 20m
**Dependencies:** 004 (Phase-1 owner of `_token.py`; edit after 004)

## Goal
Burn a dummy password check when no user matches the submitted credentials, so response latency does not leak account existence.

## Context
`CustomTokenObtainPairSerializer.validate()` looks up a user by username OR email and raises when not found. Without a constant-time path, an attacker distinguishes "user exists, wrong password" from "no such user" by timing → username enumeration. This is the **Phase-2 owner** of `accounts/serializers/auth/_token.py` (chain 004→015→018). Touch only the `validate()` not-found/inactive branch.

## Existing pattern to follow
`SRC:accounts/serializers/auth/_token.py` (timing-oracle section). **Strip** the Rhitoric deleted-user / `days_remaining` branch — do not port it.

## Files Owned
- `accounts/serializers/auth/_token.py` (M)
- `accounts/tests/serializers/test_token_timing.py` (C)

## Implementation Steps

### Step 1 — dummy hash on not-found
In the `User.DoesNotExist` (and inactive-user) branch of `validate()`, before raising the auth error, run:
```python
from django.contrib.auth.hashers import check_password
check_password(password, "pbkdf2_sha256$720000$dummy$0000000000000000000000000000000000000000000=")
```
Use a valid-format dummy encoded hash so `check_password` performs a real hash computation. Keep the raised error identical to the existing behavior (same code/status) so nothing else changes.

## Tests (`accounts/tests/serializers/test_token_timing.py`)
- `@pytest.mark.django_db`: patch `check_password` (or `django.contrib.auth.hashers.check_password` where imported) and assert it IS called when authenticating a non-existent username/email.
- Assert the not-found path still raises the same auth error as before (unchanged status/code).
- Assert a valid credential still authenticates successfully.

> Add the new test in THIS new file; do NOT modify `accounts/tests/serializers/test_auth.py` (owned by 023).

## Validation
```bash
uv run pytest accounts/tests/serializers/test_token_timing.py -x -v --ds=config.django.test
```

## Acceptance Criteria
- [ ] Dummy `check_password` runs on unknown/inactive credentials.
- [ ] Error contract unchanged; Rhitoric deleted-user branch NOT ported. Tests pass.
