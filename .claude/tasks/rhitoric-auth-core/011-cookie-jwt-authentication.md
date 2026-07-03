# 011 — Cookie JWT authentication (2.1)

**Status:** [PENDING]
**Phase:** 2
**Group:** auth
**Risk:** HIGH
**Effort:** 55m
**Dependencies:** Phase 1 complete; 009 (shares `restframework.py`, edit after 009); 004 (P1 owner of `_auth.py`)

## Goal
Add `CookieJWTAuthentication` + `enforce_csrf()`; make it the default auth class; set/clear HttpOnly cookies on login/logout/refresh with a `X-Token-Delivery: bearer` body opt-out.

## Context
Reads the access token from the HttpOnly `access_token` cookie (primary) and enforces CSRF on cookie-auth; falls back to `Authorization: Bearer` (no CSRF — safe by design). A bad/expired cookie downgrades to header auth; a CSRF failure NEVER downgrades. This is the **third owner** of `restframework.py` (chain 003→009→011) and the **Phase-2 owner** of `_auth.py` (chain 004→011→019). Cookie name keys live in Django `SIMPLE_JWT` (`AUTH_COOKIE_ACCESS`, `AUTH_COOKIE_REFRESH`, `AUTH_COOKIE_REFRESH_PATH`, `AUTH_COOKIE_HTTP_ONLY`, `AUTH_COOKIE_PATH`); the cookie `secure`/`samesite`/`domain` values come from the Pydantic fields `AUTH_COOKIE_SECURE`/`AUTH_COOKIE_SAMESITE`/`AUTH_COOKIE_DOMAIN` (added by 002).

**⚠ `settings` is shadowed in `_auth.py`.** This file does `from config.settings.config import settings` at the top (line ~45) — so `settings` here is the **Pydantic `MainSettings` singleton**, which has NO `SIMPLE_JWT` and NO `DEBUG` (its field is `DJANGO_DEBUG`). In the cookie helpers you MUST:
- `from django.conf import settings as django_settings` and read the `SIMPLE_JWT[...]` cookie-name keys from `django_settings`;
- read `AUTH_COOKIE_SECURE/SAMESITE/DOMAIN/REFRESH_PATH` from the Pydantic `settings`;
- compute `secure = AUTH_COOKIE_SECURE if AUTH_COOKIE_SECURE is not None else (not django_settings.DEBUG)`.
The new `accounts/authentication.py` is a fresh module — import Django `settings` normally there.

## Existing pattern to follow
`SRC:accounts/authentication.py` (CookieJWTAuthentication + `enforce_csrf` + `_CSRFCheck`). `accounts/controllers/_auth.py` shows the existing login/logout/refresh views to modify.

## Files Owned
- `accounts/authentication.py` (C)
- `accounts/tests/controllers/test_cookie_auth.py` (C)
- `config/settings/restframework.py` (M — owner #3)
- `accounts/controllers/_auth.py` (M — Phase-2 owner)

## Implementation Steps

### Step 1 — `accounts/authentication.py`
- `enforce_csrf(request)` — run a `CsrfViewMiddleware` subclass whose `_reject` returns the reason string; raise DRF `PermissionDenied("CSRF Failed")` on failure (maps to `PERMISSION__DENIED`). Log at DEBUG (never log token/PII).
- `CookieJWTAuthentication(JWTAuthentication)`:
  1. Read `request.COOKIES.get(settings.SIMPLE_JWT["AUTH_COOKIE_ACCESS"])`.
  2. If present: `validate_token`; on success call `enforce_csrf(request)` then return `(user, token)`. If token validation fails (InvalidToken/TokenError), fall through to header auth. If `enforce_csrf` raises, let it propagate (do NOT catch).
  3. Else fall back to `super().authenticate(request)` (Bearer header, no CSRF).

### Step 2 — default auth class (`restframework.py`)
Set `DEFAULT_AUTHENTICATION_CLASSES` to `["accounts.authentication.CookieJWTAuthentication"]` (drop the plain simplejwt class + SessionAuthentication). Do NOT touch `SIMPLE_JWT` or throttle keys.

### Step 3 — reusable cookie helpers + CSRF bootstrap (`_auth.py`)
Create module-level helpers in `accounts/controllers/_auth.py` (mirror `SRC:accounts/controllers/_auth.py` `_set_auth_cookies`/`_clear_auth_cookies`) so login/logout AND subtask 019's `logout_all` share ONE implementation:
- `_set_auth_cookies(response, access, refresh=None)` — sets the access cookie (path `/`) and, when given, the refresh cookie (path = `AUTH_COOKIE_REFRESH_PATH`), both `HttpOnly`, with `secure`/`samesite`/`domain` per settings (secure = `AUTH_COOKIE_SECURE` if not None else `not settings.DEBUG`).
- `_clear_auth_cookies(response)` — `response.delete_cookie(...)` for both cookies with matching path/domain.
These are imported by 019 (`from accounts.controllers._auth import _clear_auth_cookies`).

Also add a small **`CSRFTokenView`** (GET, `permission_classes=[AllowAny]`, `authentication_classes=[]`, decorated with `@method_decorator(ensure_csrf_cookie)`) that returns `{"detail": "CSRF cookie set"}` inside the standard envelope — so cross-origin SPAs using cookie auth can obtain the `csrftoken` cookie before a mutation. Its route (`auth/csrf/`) is bound by 019 (URL owner). Mirror `SRC` `CSRFTokenView`.

### Step 4 — cookie transport in views (`_auth.py`)
- **Login (`CustomJWTTokenCreateView.post`)**: on success call `_set_auth_cookies(response, access, refresh)` (access path `/`, refresh path = `AUTH_COOKIE_REFRESH_PATH`). Return body tokens ONLY when `request.headers.get("X-Token-Delivery") == "bearer"`; otherwise return the user payload without `access`/`refresh`.
- **Refresh (`CustomJWTTokenRefreshView`)**: read the refresh token from the cookie when the body omits it; enforce CSRF (cookie transport); set a fresh access cookie (and refresh cookie if rotated) via `_set_auth_cookies`. Keep `serializer_class = KidTokenRefreshSerializer` (set by 004).
- **Logout (`CustomJWTLogoutView` / `CustomTokenDestroyView`)**: blacklist the refresh token, then `_clear_auth_cookies(response)`.

## Tests (`accounts/tests/controllers/test_cookie_auth.py`)
- Login without `X-Token-Delivery` → 200, sets `access_token` + `refresh_token` HttpOnly cookies, body has NO `access`/`refresh`.
- Login with `X-Token-Delivery: bearer` → body includes `access`/`refresh`.
- A protected endpoint authenticates via the access cookie for a **safe** GET (no CSRF needed).
- A cookie-auth **mutation** (POST) without a CSRF token → 403 `PERMISSION__DENIED`; with a valid CSRF token → allowed.
- Bearer-header auth on a mutation works WITHOUT CSRF (fallback path).
- A malformed access cookie + valid Bearer header → authenticates via header (graceful downgrade).
- Logout deletes both cookies and blacklists the refresh token.

> Define any cookie-based test client helper locally in THIS file — do NOT modify `accounts/tests/conftest.py` (owned by 023).

## Validation
```bash
uv run pytest accounts/tests/controllers/test_cookie_auth.py -x -v --ds=config.django.test
```

## Acceptance Criteria
- [ ] Cookie-primary, header-fallback auth; CSRF enforced only on cookie transport and never downgraded.
- [ ] Login sets HttpOnly cookies; `X-Token-Delivery: bearer` opt-out returns body tokens.
- [ ] Refresh reads cookie + CSRF; logout clears cookies. Tests pass.
- [ ] Module-level `_set_auth_cookies`/`_clear_auth_cookies` helpers exist and are importable (019 reuses `_clear_auth_cookies`).
- [ ] `CSRFTokenView` (AllowAny, `ensure_csrf_cookie`) defined for SPA CSRF bootstrap (route bound by 019).
