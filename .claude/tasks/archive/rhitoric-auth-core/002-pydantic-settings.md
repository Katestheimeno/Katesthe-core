# 002 — Pydantic settings: JWT / Cookie / Throttle fields (1.2)

**Status:** [PENDING]
**Phase:** 1
**Group:** core
**Risk:** LOW
**Effort:** 25m
**Dependencies:** 001 (conceptual — fields feed the RS256 config)

## Goal
Add JWT-RS256, auth-cookie, and throttle-toggle fields to `MainSettings`, plus a `model_validator` guarding `SameSite=None`.

## Context
`config/settings/config.py` holds the Pydantic `MainSettings` (singleton `settings = MainSettings()` at end of file). `restframework.py`, the JWKS view, cookie auth, and throttles read these fields. `JWT_SECRET_KEY` already exists (line ~111); keep it (still used until 003 removes the HS256 reference). Imports present: `Optional`, `Field`, `BaseSettings`, `SettingsConfigDict`. `DJANGO_DEBUG` exists (aliased `DEBUG`).

## Existing pattern to follow
`SRC:config/settings/config.py` (lines ~615–740) — the JWT/cookie/throttle field block + the SameSite validator. Existing `EmailSettings`/`MainSettings` fields in this file show the `Field(default=..., description=...)` style to match.

## Files Owned
- `config/settings/config.py` (M)
- `config/tests/test_jwt_settings.py` (C)

## Implementation Steps

### Step 1 — imports
Add to the pydantic import line: `Literal` (from `typing`) and `model_validator` (from `pydantic`).

### Step 2 — add fields to `MainSettings` (exact plan spec)
```python
# JWT RS256
JWT_RSA_PRIVATE_KEY: str = Field(default="", description="Base64-encoded PEM of the RSA private key for JWT RS256 signing")
JWT_RSA_PREVIOUS_PUBLIC_KEY: str = Field(default="", description="Base64-encoded PEM of the previous public key (JWKS rotation window)")
JWT_ISSUER: Optional[str] = Field(default=None, description="JWT iss claim")
JWT_AUDIENCE: Optional[str] = Field(default=None, description="JWT aud claim")
# Auth cookies
AUTH_COOKIE_DOMAIN: str = Field(default="", description="Domain for auth cookies")
AUTH_COOKIE_REFRESH_PATH: str = Field(default="/api/v1/auth/jwt/", description="Path scope for the refresh-token cookie")
AUTH_COOKIE_SECURE: Optional[bool] = Field(default=None, description="Secure flag for auth cookies (None = auto from DEBUG)")
AUTH_COOKIE_SAMESITE: Literal["Lax", "Strict", "None"] = Field(default="Lax", description="SameSite attribute for auth cookies")
# Throttle toggle
THROTTLE_ENABLED: bool = Field(default=True, description="Global toggle for all throttle classes. Set False for load testing.")
```

### Step 3 — `model_validator`
Add the `@model_validator(mode="after")` `_validate_cookie_samesite` exactly as specified in the plan (§1.2): if `AUTH_COOKIE_SAMESITE == "None"` and effective secure (falling back to `not self.DEBUG` when `AUTH_COOKIE_SECURE is None`) is falsy, raise `ValueError`. Use the pydantic settings' DEBUG-equivalent field name (`self.DJANGO_DEBUG` if that is the attribute; confirm by reading the class).

## Tests (`config/tests/test_jwt_settings.py`)
- Instantiate `MainSettings(...)` with defaults → `AUTH_COOKIE_SAMESITE == "Lax"`, `THROTTLE_ENABLED is True`, `JWT_RSA_PRIVATE_KEY == ""`.
- `MainSettings(AUTH_COOKIE_SAMESITE="None", AUTH_COOKIE_SECURE=False, ...)` raises `ValidationError`.
- `MainSettings(AUTH_COOKIE_SAMESITE="None", AUTH_COOKIE_SECURE=True, ...)` is accepted.

> Construct `MainSettings` directly with explicit kwargs (bypass `.env`) so the test is hermetic. Provide any required fields (e.g. `SECRET_KEY`, `JWT_SECRET_KEY`) that lack defaults.

## Validation
```bash
uv run pytest config/tests/test_jwt_settings.py -x -v --ds=config.django.test
```

## Acceptance Criteria
- [ ] All nine fields added with plan-exact defaults.
- [ ] SameSite=None without secure raises at settings construction.
- [ ] Django still boots (`uv run python -c "import django; django.setup()"` under test settings).
- [ ] Tests pass.
