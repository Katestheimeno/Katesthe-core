# 023 — Update existing auth tests/factories → RS256 + cookies

**Status:** [PENDING]
**Phase:** 3
**Group:** test
**Risk:** HIGH
**Effort:** 60m
**Dependencies:** 011 (cookie login), 015 (timing), 018 (claims), 019 (revocation) — run LAST in Phase 3

## Goal
Reconcile the pre-existing auth test suite and fixtures/factories to the RS256 + HttpOnly-cookie world so the full suite is green.

## Context
RS256 is transparent to `RefreshToken.for_user()` (fixtures keep producing valid tokens), and `CookieJWTAuthentication` still accepts `Authorization: Bearer` with no CSRF — so existing Bearer fixtures largely keep working. What BREAKS: (a) the **login response body** no longer includes `access`/`refresh` unless `X-Token-Delivery: bearer` is sent (locked decision 7); (b) `get_token` **claims** changed (new `permissions` list; `is_superuser` never present); (c) any test asserting HS256/`JWT_SECRET_KEY`; (d) the **`/auth/users/*` routing change** — subtask 019 replaces `include('djoser.urls')` with explicit `CustomUserViewSet.as_view({...})` bindings (the djoser include made the custom viewset dead). URL *paths* are preserved, but the serving view class changes from `djoser.views.UserViewSet` to `accounts.controllers.CustomUserViewSet`; any pre-existing `test_auth.py` test that exercised `/auth/users/`, `/auth/users/me/`, `/auth/users/set_password/`, `/auth/users/reset_*`, etc. may shift behavior (e.g. now revokes sessions after password change) and must be reconciled here. This is the SINGLE owner of the pre-existing auth test files — code subtasks wrote their NEW tests in separate files.

## Existing pattern to follow
The current assertions in `accounts/tests/controllers/test_auth.py` and `accounts/tests/serializers/test_auth.py`; the fixtures in `accounts/tests/conftest.py`.

## Files Owned
- `accounts/tests/controllers/test_auth.py` (M)
- `accounts/tests/serializers/test_auth.py` (M)
- `accounts/tests/conftest.py` (M)
- `accounts/tests/factories/_user.py` (M — add a token/cookie helper if useful)

## Implementation Steps

### Step 1 — login-body assertions
For every login test that reads `response.data["access"]`/`["refresh"]`, either (a) add the `X-Token-Delivery: bearer` header to the request so the body still carries tokens, OR (b) assert tokens now arrive as `Set-Cookie` (`access_token`, `refresh_token`) and adjust the body assertion. Pick one approach consistently.

### Step 2 — claim assertions
Update `test_get_token_with_custom_claims` (and siblings) to expect the new `permissions` claim and to assert `is_superuser` is NOT in the token.

### Step 3 — fixtures
Keep `authenticated_client`/`staff_client`/`superuser_client` working. They use Bearer headers, which still authenticate via the fallback path — verify they pass. If any now hit CSRF (they should not, on Bearer), add a note. Where a cookie-based client is useful, add a helper fixture (do not remove the Bearer ones — other new-file tests may use them).

### Step 4 — algorithm assumptions
Remove/replace any assertion tied to HS256 or `settings.JWT_SECRET_KEY` signing.

## Tests
No new test files — this subtask MODIFIES the existing ones. Success = the full auth suite passes under RS256 + cookies.

## Validation
```bash
uv run pytest accounts/tests/ -x -v --ds=config.django.test
uv run pytest --ds=config.django.test    # full suite must be green after this subtask
```

## Acceptance Criteria
- [ ] Login-body/cookie assertions reconciled; `X-Token-Delivery` opt-out honored where used.
- [ ] Claim tests expect `permissions` and the absence of `is_superuser`.
- [ ] No HS256/`JWT_SECRET_KEY` signing assumptions remain.
- [ ] `accounts/tests/` and the full suite pass.
