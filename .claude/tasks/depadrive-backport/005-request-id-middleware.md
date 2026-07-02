# 005 — Request ID Middleware + settings wiring

**Status:** [PENDING]
**Phase:** 1
**Group:** B (independent of the core chain; starts after 001)
**Risk:** MEDIUM
**Effort:** 40m
**Dependencies:** 001 (the `errors/` package must exist before this subtask registers it in `PROJECT_APPS`)

## Goal
Add `RequestIdMiddleware` that assigns a stable `request.request_id`, propagates it to Loguru via a `ContextVar`, and echoes `X-Request-ID` on the response. Also perform the two Phase-1 edits to `apps_middlewares.py` (register `errors` app + register this middleware).

## Context
`meta.request_id` in the envelope (002) relies on `request.request_id`. Correlation IDs must flow request → logs (`.claude/rules/django.md` §7). **This subtask is the sole Phase-1 owner of `apps_middlewares.py`** — it makes BOTH the `errors` app registration (reassigned from 001) and the middleware registration, so the two edits never collide.

## SRC reference to adapt from
`SRC:config/middleware/request_id.py` — `class RequestIdMiddleware(MiddlewareMixin)`, header `HTTP_X_REQUEST_ID`, generated id format `req_<uuid.hex>`. The ContextVar + Loguru wiring is spec-specific (SRC uses a similar `request_id_ctx`).

## Files Owned
- `config/middleware/request_id.py` (C)
- `config/logger.py` (M)
- `config/settings/apps_middlewares.py` (M — Phase-1 sole owner)
- `config/tests/test_request_id.py` (C)

> Existing `config/middleware/__init__.py` and `config/middleware/db_consistency.py` are present — do not modify them.

## Implementation Steps

### Step 1 — `config/middleware/request_id.py`
- Define `request_id_ctx: ContextVar[str] = ContextVar("request_id", default="-")` at module level (importable by `logger.py`).
- `class RequestIdMiddleware(MiddlewareMixin)`:
  - `process_request(request)`: `rid = request.META.get("HTTP_X_REQUEST_ID") or f"req_{uuid.uuid4().hex[:24]}"`; set `request.request_id = rid`; `request.request_id_token = request_id_ctx.set(rid)`.
  - `process_response(request, response)`: set `response["X-Request-ID"] = getattr(request, "request_id", "-")`; reset the ContextVar in a `finally` (`request_id_ctx.reset(token)` if a token was stored); return response.

### Step 2 — `config/logger.py`
Import `request_id_ctx` from `config.middleware.request_id` and add the request id to log records. Prefer a Loguru `patcher`/`configure` that injects `record["extra"]["request_id"] = request_id_ctx.get()`, and add `request_id={extra[request_id]}` to `console_format` and `file_format`. **Guard the import** against circular import (import inside the patcher function, or wrap in try/except) since `logger.py` loads very early. Do not break existing sinks/format lines beyond adding the request-id field.

### Step 3 — `config/settings/apps_middlewares.py`
- Add `'errors'` to `PROJECT_APPS`.
- Add `"config.middleware.request_id.RequestIdMiddleware"` to `MIDDLEWARE` immediately **after** `"corsheaders.middleware.CorsMiddleware"`.

## Tests (`config/tests/test_request_id.py`)
- Middleware unit: build a request via `RequestFactory`, run `process_request`; assert `request.request_id` starts with `req_` when no header; when `HTTP_X_REQUEST_ID` provided, `request.request_id` equals it.
- `process_response` sets the `X-Request-ID` header equal to `request.request_id`.
- ContextVar: after `process_request`, `request_id_ctx.get()` equals the id; after `process_response`, it resets.
- Integration (optional, `@pytest.mark.django_db`): GET an existing endpoint through the test client and assert the response carries an `X-Request-ID` header.

## Validation
```bash
uv run pytest config/tests/test_request_id.py -x -v --ds=config.django.test
# whole suite still boots with errors app + middleware registered:
uv run pytest accounts/tests/test_basic.py -x --ds=config.django.test
```

## Acceptance Criteria
- [ ] `request.request_id` set (honoring incoming header, else `req_<hex>`).
- [ ] `X-Request-ID` present on responses; ContextVar set and reset per request.
- [ ] Loguru records include the request id without breaking existing sinks.
- [ ] `errors` in `PROJECT_APPS`; `RequestIdMiddleware` after `CorsMiddleware`.
- [ ] Suite boots; tests pass.
