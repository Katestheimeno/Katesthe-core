# 008 — Throttle base classes (4.1)

**Status:** [PENDING]
**Phase:** 4
**Group:** thr
**Risk:** MEDIUM
**Effort:** 45m
**Dependencies:** none (may start immediately, concurrent with Phase 1)

## Goal
Replace the two-class `utils/throttles.py` with the base-class hierarchy + the ~14 universal throttle classes, all honoring the `THROTTLE_ENABLED` global toggle.

## Context
Current `utils/throttles.py` has only `AuthLoginThrottle` + `PasswordResetThrottle` (subclasses of `UserRateThrottle`). `PublicListThrottle` (defined here) is consumed by the JWKS view (006). Keep ONLY universal throttles — strip every domain-specific one (Game/AI/Quiz/etc.).

## Existing pattern to follow
`SRC:utils/throttling.py` (base classes + universal throttles). Strip domain scopes.

## Files Owned
- `utils/throttles.py` (M — full rewrite of contents)
- `utils/tests/test_throttles_backport.py` (C)

## Implementation Steps

### Step 1 — helpers + base classes
```python
from rest_framework.throttling import SimpleRateThrottle

def _throttle_enabled():
    from django.conf import settings
    return getattr(settings, "THROTTLE_ENABLED", True)

class _UserOrIPThrottle(SimpleRateThrottle):
    """Keyed by user PK (authenticated) or client IP (anonymous)."""
    def get_cache_key(self, request, view):
        if not _throttle_enabled():
            return None
        if request.user and request.user.is_authenticated:
            ident = request.user.pk
        else:
            ident = self.get_ident(request)
        return self.cache_format % {"scope": self.scope, "ident": ident}

class _IPOnlyThrottle(SimpleRateThrottle):
    """Always keyed by client IP, even for authenticated users."""
    def get_cache_key(self, request, view):
        if not _throttle_enabled():
            return None
        return self.cache_format % {"scope": self.scope, "ident": self.get_ident(request)}
```

### Step 2 — universal throttle classes (scopes exact)
Define, each with its `scope`:
`DefaultAnonThrottle`(_IPOnly, `default_anon`), `DefaultUserThrottle`(_UserOrIP, `default_user`), `AuthLoginThrottle`(_IPOnly, `auth_login`), `AuthLoginAccountThrottle`(SimpleRateThrottle, `auth_login_account` — key by SHA-256 of the submitted credential; return `None` when `_throttle_enabled()` is False or no credential present), `AuthRegisterThrottle`(_IPOnly, `auth_register`), `AuthResetThrottle`(_IPOnly, `auth_reset`), `AuthSetPasswordThrottle`(_UserOrIP, `auth_set_password`), `AuthRefreshThrottle`(_IPOnly, `auth_refresh`), `AuthActivationThrottle`(_IPOnly, `auth_activation`), `PublicListThrottle`(_IPOnly, `public_list`), `SearchThrottle`(_UserOrIP, `search`), `WebhookThrottle`(_IPOnly, `webhook`), `ExternalAPIThrottle`(SimpleRateThrottle, `external_api` — key by the `X-API-Key` header), `UserMutationThrottle`(_UserOrIP, `user_mutation`).

> `AuthLoginAccountThrottle`: read the credential from `request.data.get("username")`/`email` in `get_cache_key`, hash with `hashlib.sha256`, return `None` if absent. Preserve the existing `PasswordResetThrottle` name as an alias for `AuthResetThrottle` OR keep it (the old scope `auth_password_reset` is replaced by `auth_reset` in 009 — if other code imports `PasswordResetThrottle`, keep a thin subclass to avoid breakage; grep first).

## Tests (`utils/tests/test_throttles_backport.py`)
- Each class exposes the exact `scope` string above.
- With `settings.THROTTLE_ENABLED = False` (override), `_IPOnlyThrottle`/`_UserOrIPThrottle`/`AuthLoginAccountThrottle`.get_cache_key returns `None` (never throttles).
- `_UserOrIPThrottle` keys differ for authenticated vs anonymous requests (build a `RequestFactory` request + set `.user`).
- `AuthLoginAccountThrottle` produces the same key for the same credential and different keys for different credentials; returns `None` when no credential.
- Integration: an `APIView` with `throttle_classes=[AuthLoginThrottle]` at a low override rate returns 429 (`RATE_LIMIT__EXCEEDED` envelope) after the limit. Clear `cache` first.

## Validation
```bash
uv run pytest utils/tests/test_throttles_backport.py -x -v --ds=config.django.test
```

## Acceptance Criteria
- [ ] Base classes with `THROTTLE_ENABLED` short-circuit; all 14 scopes present.
- [ ] No domain-specific throttles. `PublicListThrottle` importable for 006.
- [ ] Tests pass.
