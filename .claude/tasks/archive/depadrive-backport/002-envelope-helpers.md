# 002 — API Response Envelope Helpers

**Status:** [PENDING]
**Phase:** 1
**Group:** A (sequential core chain)
**Risk:** LOW
**Effort:** 25m
**Dependencies:** 001

## Goal
Create `utils/api_response.py` with `ok()` and `err_single()` that wrap payloads in the project success/error envelope, always including `meta.request_id` and `meta.version`.

## Context
The envelope is the API contract (`.claude/rules/api.md`): every response carries `meta` with `request_id` + `version`; **no `message` field** (frontend owns i18n). These helpers are consumed by the DRF normalization (003) and the exception handler (004).

## SRC reference to adapt from
`SRC:utils/api_response.py`. Public functions there:
- `meta_for_request(request) -> dict` → `{"request_id": <rid or fallback>, "version": "v1"}`
- `ok(data, request, status=200, meta_extra=None) -> Response`
- `err_single(code, request, *, status=400, details=None) -> Response` (keyword-only `status`, default 400)
**Strip** the domain constant `ABLY_TOKEN_REFRESH`.

## Files Owned
- `utils/api_response.py` (C)
- `utils/tests/test_api_response.py` (C)

## Implementation Steps

### Step 1 — `meta_for_request(request)`
Return `{"request_id": getattr(request, "request_id", None) or _fallback(), "version": "v1"}`. The request-id middleware (005) sets `request.request_id`; when absent (middleware not installed / non-DRF request / None), generate a fallback `req_<uuid.uuid4().hex[:24]>` so `meta.request_id` is never null. Accept `request=None` gracefully.

### Step 2 — `ok(data, request, status=200, meta_extra=None)`
Return DRF `Response({"success": True, "data": data, "meta": {**meta_for_request(request), **(meta_extra or {})}}, status=status)`.

### Step 3 — `err_single(code, request, *, status=400, details=None)`
Keyword-only `status` (default 400) — matches the SRC-ref signature above; all callers pass `status=` explicitly. Return DRF `Response({"success": False, "error": {"code": code, "details": details or {}}, "meta": meta_for_request(request)}, status=status)`.

Import `Response` from `rest_framework.response`.

## Tests (`utils/tests/test_api_response.py`)
Use `rest_framework.test.APIRequestFactory` to build a request; set `request.request_id = "req_test123"` to simulate the middleware.
- `ok({"a": 1}, request)` → `.data["success"] is True`, `.data["data"] == {"a": 1}`, `.data["meta"]["request_id"] == "req_test123"`, `meta["version"] == "v1"`, status 200.
- `ok(..., status=201)` sets status 201; `meta_extra` merges into meta.
- `err_single("RESOURCE__NOT_FOUND", request, status=404, details={"pk": 5})` → `.data["success"] is False`, `.data["error"]["code"] == "RESOURCE__NOT_FOUND"`, `.data["error"]["details"] == {"pk": 5}`, status 404.
- With a request lacking `request_id`, `meta.request_id` is a non-empty `req_...` fallback (never None).
- No `message` key anywhere in the payload.
- No DB needed.

## Validation
```bash
uv run pytest utils/tests/test_api_response.py -x -v --ds=config.django.test
uv run python -c "from utils.api_response import ok, err_single; print('OK')"
```

## Acceptance Criteria
- [ ] `ok` and `err_single` return the exact envelope shapes above; `err_single` uses keyword-only `status=400` default.
- [ ] `meta.request_id` and `meta.version` always present; fallback id when middleware absent.
- [ ] No `message` field; no Ably/domain constants.
- [ ] Tests pass.
