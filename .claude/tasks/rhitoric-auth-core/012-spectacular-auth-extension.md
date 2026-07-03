# 012 — Spectacular auth extension (2.2)

**Status:** [PENDING]
**Phase:** 2
**Group:** auth
**Risk:** LOW
**Effort:** 20m
**Dependencies:** 011 (targets `CookieJWTAuthentication`)

## Goal
Register `CookieJWTAuthentication` with drf-spectacular so the OpenAPI schema documents it as HTTP bearer JWT.

## Context
Without this extension, drf-spectacular cannot represent the custom auth class and `--fail-on-warn` may complain. The OpenAPI validation gate must stay green.

## Existing pattern to follow
`SRC:config/spectacular_auth.py` (`OpenApiAuthenticationExtension` subclass). `config/settings/spectacular.py` holds `SPECTACULAR_SETTINGS`.

## Files Owned
- `config/spectacular_auth.py` (C)
- `config/tests/test_spectacular_auth.py` (C)
- `config/settings/spectacular.py` (M — ensure the extension is discovered)

## Implementation Steps

### Step 1 — extension
```python
from drf_spectacular.extensions import OpenApiAuthenticationExtension

class CookieJWTAuthenticationExtension(OpenApiAuthenticationExtension):
    target_class = "accounts.authentication.CookieJWTAuthentication"
    name = "CookieJWTAuth"
    def get_security_definition(self, auto_schema):
        return {"type": "http", "scheme": "bearer", "bearerFormat": "JWT",
                "description": "JWT via HttpOnly cookie (primary) or Authorization header (fallback). Cookie: access_token."}
```

### Step 2 — discovery
drf-spectacular auto-discovers extensions imported at startup. Ensure `config/spectacular_auth.py` is imported — either add it to `SPECTACULAR_SETTINGS["EXTENSIONS"]` if that mechanism is used here, or import it from an already-loaded module (e.g. reference in `config/settings/spectacular.py`). Confirm by running the validate command.

## Tests (`config/tests/test_spectacular_auth.py`)
- Import the extension; assert `target_class` / `name` / `get_security_definition(None)` shape.
- Generate the schema (`SchemaGenerator().get_schema(request=None, public=True)`) and assert `components.securitySchemes` contains a bearer-JWT scheme (or at least that generation succeeds without warnings).

## Validation
```bash
uv run pytest config/tests/test_spectacular_auth.py -x -v --ds=config.django.test
uv run python manage.py spectacular --validate --fail-on-warn --settings=config.django.test
```

## Acceptance Criteria
- [ ] Extension registered and discovered; schema documents CookieJWTAuth as bearer JWT.
- [ ] `spectacular --validate --fail-on-warn` exits 0. Tests pass.
