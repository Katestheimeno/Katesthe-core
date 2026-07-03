# 012 — Access Log Middleware

**Status:** [PENDING]
**Phase:** 2
**Group:** A (concurrent with 010, 011, 013–016)
**Risk:** MEDIUM
**Effort:** 35m
**Dependencies:** Phase 1 complete (uses request_id from 005's middleware)

## Goal
Add `AccessLogMiddleware` emitting one structured log line per request (method, path, status, duration_ms, size, user_id, request_id), skipping health/static/media noise on 200 and enriching 4xx+ with IP + user-agent.

## Context
Structured access logging via Loguru (`.claude/rules/django.md` §7). Correlates with the request_id set by 005. **This subtask is the sole Phase-2 owner of `apps_middlewares.py`.**

## SRC reference to adapt from
`SRC:config/middleware/access_log.py` — `AccessLogMiddleware(MiddlewareMixin)` with `process_request` (start timer) + `process_response` (log). Uses the request_id contextvar. **Strip** any Depadrive-specific fields.

## Files Owned
- `config/middleware/access_log.py` (C)
- `config/tests/test_access_log.py` (C)
- `config/settings/apps_middlewares.py` (M — Phase-2 owner)

> `apps_middlewares.py` was edited by 005 (Phase 1) and will be edited by 022 (Phase 3) — all different phases, safe.

## Implementation Steps

### Step 1 — `config/middleware/access_log.py`
- `process_request(request)`: `request._access_start = time.monotonic()`.
- `process_response(request, response)`:
  - `duration_ms = round((time.monotonic() - getattr(request, "_access_start", now)) * 1000, 2)`.
  - Compute `path`, `method`, `status = response.status_code`, `size = len(getattr(response, "content", b""))` (guard streaming responses), `user_id = getattr(getattr(request, "user", None), "id", None)`, `request_id = getattr(request, "request_id", "-")`.
  - **Skip** logging when `status == 200` and path starts with `/health`, `/ready`, `/static`, `/media`, or is `/favicon.ico`.
  - Build a bound logger: `from config.logger import logger`; `log = logger.bind(method=..., path=..., status=..., duration_ms=..., size=..., user_id=..., request_id=..., access=True)`.
  - For `status >= 400`, also bind `ip=<client ip from X-Forwarded-For / REMOTE_ADDR>` and `user_agent=<truncated HTTP_USER_AGENT>`.
  - Emit at `warning` for 5xx, `info` for 4xx, `info` for others: `log.info("http.access")` (event name `http.access`).
  - Return `response`.

### Step 2 — register middleware
In `config/settings/apps_middlewares.py`, add `"config.middleware.access_log.AccessLogMiddleware"` to `MIDDLEWARE` immediately **after** `"config.middleware.request_id.RequestIdMiddleware"` (so request_id is set before logging).

## Tests (`config/tests/test_access_log.py`)
- Patch `config.logger.logger` (or capture via a loguru sink) and drive the middleware with a `RequestFactory` request + a dummy `HttpResponse`:
  - A normal 200 API path logs one `http.access` line with the expected bound fields.
  - `GET /health/` 200 is skipped (no log call).
  - A 500 response logs at warning and includes `ip` / `user_agent` bindings.
  - `duration_ms` is a non-negative float; missing `_access_start` doesn't crash.
- No DB strictly needed (use `AnonymousUser` → `user_id` None).

## Validation
```bash
uv run pytest config/tests/test_access_log.py -x -v --ds=config.django.test
uv run pytest accounts/tests/test_basic.py -x --ds=config.django.test   # suite still boots
```

## Acceptance Criteria
- [ ] One `http.access` line per request with method/path/status/duration_ms/size/user_id/request_id.
- [ ] Health/static/media 200s skipped; 4xx+ enriched with ip + user-agent.
- [ ] Middleware registered after `RequestIdMiddleware`.
- [ ] Tests pass; suite boots.
