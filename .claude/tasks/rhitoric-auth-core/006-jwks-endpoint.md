# 006 — JWKS endpoint (1.6)

**Status:** [PENDING]
**Phase:** 1
**Group:** tail
**Risk:** MEDIUM
**Effort:** 35m
**Dependencies:** 003 (key objects on settings), 004 (kid tokens), 008 (`PublicListThrottle`)

## Goal
Public RFC 7517 JWKS endpoint that serves the current (and, during rotation, previous) RSA public key(s).

## Context
JWKS lets external verifiers fetch the public keys by `kid`. Reads `JWT_RSA_PRIVATE_KEY_OBJ`, `JWT_KID`, `JWT_PREVIOUS_PUBLIC_KEY_OBJ`, `JWT_PREVIOUS_KID` (all exposed by 003) and `SIMPLE_JWT["ALGORITHM"]`. Throttled by `PublicListThrottle` from subtask 008.

## Existing pattern to follow
`SRC:accounts/controllers/_jwks.py`. Existing controllers in `accounts/controllers/_auth.py` show the view/import style and how `__init__.py` re-exports (`from ._auth import *`).

## Files Owned
- `accounts/controllers/_jwks.py` (C)
- `accounts/tests/controllers/test_jwks.py` (C)
- `accounts/urls/_auth.py` (M — add JWKS route; owner)
- `accounts/controllers/__init__.py` (M — add `from ._jwks import *`)

## Implementation Steps

### Step 1 — `JWKSView`
```python
class JWKSView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []
    throttle_classes = [PublicListThrottle]   # from utils.throttles
    schema = None                              # exclude from OpenAPI

    def get(self, request):
        from django.conf import settings
        jwks = build_jwks(
            settings.JWT_RSA_PRIVATE_KEY_OBJ,
            settings.JWT_KID,
            algorithm=settings.SIMPLE_JWT["ALGORITHM"],
            previous_public_key=getattr(settings, "JWT_PREVIOUS_PUBLIC_KEY_OBJ", None),
            previous_kid=getattr(settings, "JWT_PREVIOUS_KID", None),
        )
        resp = JsonResponse(jwks)
        resp["Cache-Control"] = "public, max-age=3600"
        return resp
```
Import `build_jwks` from `config.jwt_keys`, `PublicListThrottle` from `utils.throttles`.

### Step 2 — route (`accounts/urls/_auth.py`)
Add a path serving the JWKS view. Prefer a well-known path (e.g. `path(".well-known/jwks.json", JWKSView.as_view(), name="jwks")`) consistent with the existing `auth/` includes; document the resolved absolute URL in the view docstring.

### Step 3 — export (`accounts/controllers/__init__.py`)
Add `from ._jwks import *` (and an `__all__ = ["JWKSView"]` in `_jwks.py`).

## Tests (`accounts/tests/controllers/test_jwks.py`)
- `GET` the JWKS URL (via `reverse("jwks")`) unauthenticated → 200, `Cache-Control: public, max-age=3600`.
- Body has `keys` list; first key `kid == settings.JWT_KID`; contains `n`/`e`; NO `d`.
- No auth required (empty `authentication_classes`). 
- (Rotation) with a `JWT_PREVIOUS_PUBLIC_KEY` configured via override, two keys are returned.

## Validation
```bash
uv run pytest accounts/tests/controllers/test_jwks.py -x -v --ds=config.django.test
```

## Acceptance Criteria
- [ ] Public, unauthenticated, throttled JWKS endpoint returning only public material.
- [ ] `Cache-Control` header set; excluded from OpenAPI (`schema = None`).
- [ ] Route registered; `JWKSView` re-exported. Tests pass.
