# 019 — Privilege-change session revocation (3.4)

**Status:** [PENDING]
**Phase:** 3
**Group:** sess
**Risk:** HIGH
**Effort:** 60m
**Dependencies:** 011 (Phase-2 owner of `_auth.py`; edit after 011), 016 (session service), 006 (Phase-1 owner of `accounts/urls/_auth.py`; edit after 006)

## Goal
Revoke all sessions on password change, username change, and account deletion; add a `logout_all` endpoint; wire refresh-reuse detection into the refresh flow. **Route the user endpoints to `CustomUserViewSet` explicitly** (the current `include('djoser.urls')` makes the overrides dead code).

## Context — CRITICAL routing fix
The DST `accounts/urls/_auth.py` currently does `path('auth/', include('djoser.urls'))`. djoser 2.2's `djoser/urls/base.py` hard-registers `djoser.views.UserViewSet`, so `/auth/users/me/`, `/auth/users/set_password/`, `/auth/users/reset_username/` etc. resolve to **djoser's** viewset, NOT `accounts.controllers.CustomUserViewSet`. djoser has **no `VIEWS` setting** — the `'VIEWS': {'user': ...}` entry in `config/settings/djoser.py` is dead config. Therefore overriding actions on `CustomUserViewSet` (and adding a `logout_all` `@action`) has ZERO effect on the live endpoints unless the routes are bound explicitly. `SRC:accounts/urls/_auth.py` confirms this: it does NOT `include('djoser.urls')` — it binds every user route to `CustomUserViewSet.as_view({...})` explicitly, and `SRC:accounts/controllers/_auth.py:945` documents that `DJOSER['VIEWS']` is not a real setting.

This subtask is the **Phase-3 owner** of `accounts/controllers/_auth.py` (chain 004→011→019) AND a **second owner of `accounts/urls/_auth.py`** (serialized after 006, the JWKS-route owner — 006 is Phase 1, 019 is Phase 3, never concurrent). `revoke_all_sessions()`/`detect_refresh_reuse()` live in `accounts/services/session.py` (016).

## Existing pattern to follow
`SRC:accounts/urls/_auth.py` (the explicit `CustomUserViewSet.as_view({...})` bindings — mirror the user-route block) and `SRC:accounts/controllers/_auth.py` (`CustomUserViewSet` actions calling the session service).

## Files Owned
- `accounts/controllers/_auth.py` (M — Phase-3 owner)
- `accounts/urls/_auth.py` (M — second owner, after 006; rewrite the user-routes section)
- `accounts/tests/controllers/test_session_revocation.py` (C)

## Implementation Steps

### Step 1 — replace `include('djoser.urls')` with explicit `CustomUserViewSet` routes (`accounts/urls/_auth.py`)
Remove `path('auth/', include('djoser.urls'))` and bind the user routes explicitly to `CustomUserViewSet` (which subclasses djoser's `UserViewSet`, so it retains every standard action) — mirror `SRC:accounts/urls/_auth.py`. **Preserve the exact existing URL paths** so no client contract changes: `auth/users/` (`{'post':'create','get':'list'}`), `auth/users/me/` (`{'get':'me','put':'me','patch':'me','delete':'me'}`), `auth/users/set_password/`, `auth/users/set_username/`, `auth/users/reset_password/`, `auth/users/reset_password_confirm/`, `auth/users/reset_username/`, `auth/users/reset_username_confirm/`, plus `auth/users/logout-all/` (`{'post':'logout_all'}`) and `auth/csrf/` (the `CSRFTokenView` created by 011). Keep the existing custom activation + `auth/jwt/*` routes and the JWKS route (added by 006) untouched. Do NOT bind SRC-only domain routes (`set_email`, `restore-account`) — those views don't exist here.

### Step 2 — revoke on privilege changes (`_auth.py`)
On `CustomUserViewSet`, override the djoser actions:
- After a successful `set_password` → `revoke_all_sessions(request.user.id, event="password_change")`.
- After a successful `set_username` → `revoke_all_sessions(request.user.id, event="username_change")`.
- On `destroy`/`me` DELETE (soft delete) → `revoke_all_sessions(instance.id, event="account_deletion")`.
Call `super().<action>()` first, then revoke; wrap in `transaction.atomic()` where the change + revoke must be consistent.

### Step 3 — `logout_all`
Add `@action(detail=False, methods=["post"], url_path="logout-all")` `def logout_all(self, request)` → `revoke_all_sessions(request.user.id, event="logout_all")`, then clear auth cookies via the `_clear_auth_cookies(response)` helper created by 011 (import it), return 204. Route bound explicitly in Step 1 (djoser's router is no longer included).

### Step 4 — refresh-reuse wiring
In the refresh view flow (`CustomJWTTokenRefreshView`), call `detect_refresh_reuse(raw_refresh_token)` before/around rotation so a replayed rotated token triggers family revocation. Keep the existing cookie-refresh + CSRF behavior added by 011.

## Tests (`accounts/tests/controllers/test_session_revocation.py`)
- The `/auth/users/*` endpoints resolve to `CustomUserViewSet` (assert `resolve(...).func.cls is CustomUserViewSet` for `set_password` + `me`), proving the routing fix.
- Password change → prior refresh tokens are blacklisted (old token can no longer refresh); `auth:revoked_after` set.
- Username change → sessions revoked.
- `logout_all` → 204, sessions revoked, cookies cleared.
- Account deletion → sessions revoked.
- Replaying a rotated refresh token → family revoked (subsequent refresh with a sibling token fails).

> New file; do NOT modify `accounts/tests/controllers/test_auth.py` (owned by 023). The routing change WILL shift which view class serves `/auth/users/*` — 023 reconciles the pre-existing tests (its context notes this).

## Validation
```bash
uv run pytest accounts/tests/controllers/test_session_revocation.py -x -v --ds=config.django.test
uv run python manage.py check --settings=config.django.test   # URLconf still imports cleanly
```

## Acceptance Criteria
- [ ] `/auth/users/*` routes resolve to `CustomUserViewSet` (djoser include removed); all existing paths preserved.
- [ ] Password/username change, deletion, and `logout_all` all revoke sessions.
- [ ] `logout_all` explicitly routed at `auth/users/logout-all/`; `_clear_auth_cookies` reused.
- [ ] Refresh-reuse detection wired into refresh. Tests pass.
