# 018 — Custom JWT claims: is_superuser exclusion (3.3)

**Status:** [PENDING]
**Phase:** 3
**Group:** tok
**Risk:** MEDIUM
**Effort:** 30m
**Dependencies:** 004 (kid tokens), 015 (Phase-2 owner of `_token.py`; edit after 015)

## Goal
Add a `permissions` claim to `get_token()` while intentionally EXCLUDING `is_superuser` from the JWT (SEC-001).

## Context
`CustomTokenObtainPairSerializer.get_token()` already sets `username`, `email`, `is_verified`, `is_staff`. Embedding `is_superuser` in a JWT lets a stolen/trusted token assert superuser client-side → privilege escalation; superuser must be checked server-side. This is the **Phase-3 owner** of `accounts/serializers/auth/_token.py` (chain 004→015→018).

## Existing pattern to follow
`SRC:accounts/serializers/auth/_token.py` `get_token`. **Strip** the Rhitoric `admin_api.`-prefix stripping — use plain `codename`s.

## Files Owned
- `accounts/serializers/auth/_token.py` (M)
- `accounts/tests/serializers/test_token_claims.py` (C)

## Implementation Steps

### Step 1 — extend `get_token`
Keep existing claims. Add (per plan §3.3):
```python
# SEC-001: is_superuser intentionally NOT in the JWT — check server-side.
if user.is_superuser:
    token["permissions"] = ["system_admin"]
elif user.is_staff:
    token["permissions"] = list(user.user_permissions.values_list("codename", flat=True))
else:
    token["permissions"] = []
```
Do NOT add `is_superuser` to the token. Leave `token_class` (set by 004) and the timing defense (015) untouched.

## Tests (`accounts/tests/serializers/test_token_claims.py`)
- `@pytest.mark.django_db`: decode a superuser's access token → `permissions == ["system_admin"]`, and `"is_superuser"` NOT in the claims.
- Staff user with an assigned permission → `permissions` contains that `codename`.
- Regular user → `permissions == []`.
- `username`/`email`/`is_verified`/`is_staff` still present.

> New file; do NOT modify `accounts/tests/serializers/test_auth.py` (owned by 023).

## Validation
```bash
uv run pytest accounts/tests/serializers/test_token_claims.py -x -v --ds=config.django.test
```

## Acceptance Criteria
- [ ] `permissions` claim populated per role; `is_superuser` absent from the JWT.
- [ ] No `admin_api.` prefix logic ported. Tests pass.
