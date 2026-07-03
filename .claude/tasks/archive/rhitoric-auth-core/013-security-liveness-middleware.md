# 013 — Security-headers + liveness middleware (2.3 + 2.6)

**Status:** [PENDING]
**Phase:** 2
**Group:** mw
**Risk:** MEDIUM
**Effort:** 40m
**Dependencies:** none within Phase 2 (independent)

## Goal
Add two middlewares — `SecurityHeadersMiddleware` (Referrer-Policy + Permissions-Policy) and `LivenessProbeMiddleware` (DB-independent `/api/v1/liveness/`) — and wire both into `MIDDLEWARE`.

## Context
Merged because both edit the single shared `config/settings/apps_middlewares.py` (sacred rule: one owner per file). Current `MIDDLEWARE` order (in `apps_middlewares.py`): `SecurityMiddleware` → `DBConsistencyMiddleware` → `SessionMiddleware` → `CorsMiddleware` → `RequestIdMiddleware` → `AccessLogMiddleware` → `CommonMiddleware` → `CsrfViewMiddleware` → `AuthenticationMiddleware` → `MessageMiddleware` → `XFrameOptionsMiddleware`.

## Existing pattern to follow
`SRC:config/middleware/security_headers.py`, `SRC:config/middleware/liveness_probe.py`. Existing middlewares in `config/middleware/` (`request_id.py`, `access_log.py`) show the callable-middleware style.

## Files Owned
- `config/middleware/security_headers.py` (C)
- `config/middleware/liveness_probe.py` (C)
- `config/tests/test_security_headers.py` (C)
- `config/tests/test_liveness_probe.py` (C)
- `config/settings/apps_middlewares.py` (M)

## Implementation Steps

### Step 1 — `SecurityHeadersMiddleware`
On each response, `response.setdefault(...)`:
- `Referrer-Policy` = `getattr(settings, "SECURE_REFERRER_POLICY", "strict-origin-when-cross-origin")`.
- `Permissions-Policy` = `accelerometer=(), camera=(), display-capture=(), fullscreen=(self), geolocation=(), gyroscope=(), magnetometer=(), microphone=(), payment=(), usb=()`.

### Step 2 — `LivenessProbeMiddleware`
- Constant `LIVENESS_PATH = "/api/v1/liveness/"`.
- In `__call__`, if `request.method == "GET"` and `request.path == LIVENESS_PATH`, short-circuit with `JsonResponse({"status": "alive", "service": settings.PROJECT_NAME}, status=200)` (use `settings.PROJECT_NAME`, NOT a hardcoded name). Otherwise call `get_response`.

### Step 3 — wire `MIDDLEWARE`
- Insert `"config.middleware.security_headers.SecurityHeadersMiddleware"` immediately AFTER `SecurityMiddleware`.
- Insert `"config.middleware.liveness_probe.LivenessProbeMiddleware"` immediately BEFORE `SessionMiddleware` (so the probe answers even when the session/DB layer is down).

## Tests
`test_security_headers.py`: hit any endpoint; assert `Referrer-Policy` and `Permissions-Policy` present with expected values; assert `setdefault` does not clobber a pre-set header.
`test_liveness_probe.py`: `GET /api/v1/liveness/` → 200 `{"status":"alive","service":<PROJECT_NAME>}`; a non-liveness path passes through; POST to the liveness path is NOT short-circuited.

## Validation
```bash
uv run pytest config/tests/test_security_headers.py config/tests/test_liveness_probe.py -x -v --ds=config.django.test
```

## Acceptance Criteria
- [ ] Both middlewares created and correctly positioned in `MIDDLEWARE`.
- [ ] Liveness uses `settings.PROJECT_NAME`; survives without DB/session.
- [ ] Security headers set via `setdefault`. Tests pass.
