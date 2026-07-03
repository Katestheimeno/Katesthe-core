# 003 — DRF Error Envelope Normalization

**Status:** [PENDING]
**Phase:** 1
**Group:** A (sequential core chain)
**Risk:** MEDIUM
**Effort:** 40m
**Dependencies:** 001, 002

## Goal
Create `utils/drf_error_envelope.py` that converts DRF's native validation format (`{"field": ["msg"]}`) into the project envelope with `VALIDATION__*` codes, and coerces DRF's built-in error responses (404/401/etc. `{"detail": "..."}`) into the envelope.

## Context
DRF raises `ValidationError` with a `{field: [errors]}` detail and returns `{"detail": "..."}` for 404/401/403/throttle. The exception handler (004) delegates the conversion of these shapes to this module so the handler stays thin. Field-error codes map to the catalog's `VALIDATION__*`.

## SRC reference to adapt from
`SRC:utils/drf_error_envelope.py`. Public functions:
- `normalize_validation_detail(detail) -> list[dict]` — flatten DRF detail into `[{"code": VALIDATION__*, "details": {"field": name}}, ...]`, using a `_FIELD_CODE_MAP` from DRF error codes → catalog codes. Mapping: `"required"`/`"null"`/`"blank"` → `VALIDATION__MISSING_FIELD`; `"invalid"` → `VALIDATION__INVALID_FORMAT`; fallback → `VALIDATION__INVALID_VALUE`.
- `validation_error_response(errors_list, request) -> Response` — HTTP **422** `{"success": False, "errors": [...], "meta": ...}`.
- `coerce_drf_error_response(request, response) -> Response` — idempotent: if a DRF response body has `{"detail": ...}`, rewrap into the single-error envelope; if already an envelope, return unchanged.

## Files Owned
- `utils/drf_error_envelope.py` (C)
- `utils/tests/test_drf_error_envelope.py` (C)

## Implementation Steps

### Step 1 — `_FIELD_CODE_MAP`
Map DRF `ErrorDetail.code` values to catalog codes. A **blank/null required field is a missing-value condition**, so it maps to `VALIDATION__MISSING_FIELD` — the header prose above and this map MUST agree (no `"blank"` contradiction):
```
"required"        -> VALIDATION__MISSING_FIELD
"null"            -> VALIDATION__MISSING_FIELD
"blank"           -> VALIDATION__MISSING_FIELD
"invalid"         -> VALIDATION__INVALID_FORMAT
"invalid_choice"  -> VALIDATION__INVALID_VALUE
(default)         -> VALIDATION__INVALID_VALUE
```
(Import codes from `errors.catalog`.) Reserve special-case entries `image_too_large` / `image_invalid_type` as comments — they belong to Phase 3 subtask 018 and can be added then; keep the map generic now.

### Step 2 — `normalize_validation_detail(detail)`
Accept a dict (`{field: [ErrorDetail,...]}`), a list, or a scalar. Produce a list of `{"code": <mapped>, "details": {"field": <field-name>}}`. For non-field errors use field name `"non_field_errors"` (or omit the field key). Read each `ErrorDetail.code` when available (`getattr(err, "code", None)`), else default.

### Step 3 — `validation_error_response(errors_list, request)`
Return `Response({"success": False, "errors": errors_list, "meta": meta_for_request(request)}, status=422)` (reuse `meta_for_request` from `utils.api_response`).

### Step 4 — `coerce_drf_error_response(request, response)`
If `isinstance(response.data, dict)` and `"detail" in response.data` and it is not already an envelope (`"success" not in response.data`), rebuild via `err_single(code, request, status=response.status_code, details=...)`. Choose `code` from an **explicit** status→code map. **Never route a 4xx to `INTERNAL__ERROR`** — that code is 5xx-only per `.claude/rules/api.md`:
```
400 -> VALIDATION__INVALID_FORMAT    # malformed body / parse error
401 -> AUTH__UNAUTHENTICATED
403 -> PERMISSION__DENIED
404 -> RESOURCE__NOT_FOUND
405 -> VALIDATION__INVALID_FORMAT    # method not allowed
406 -> VALIDATION__INVALID_FORMAT    # not acceptable
409 -> RESOURCE__CONFLICT
415 -> VALIDATION__INVALID_FORMAT    # unsupported media type
429 -> RATE_LIMIT__EXCEEDED
```
Any other status `< 500` not listed → default to a client-error code `VALIDATION__INVALID_VALUE`. Only genuine `>= 500` falls through to `INTERNAL__ERROR`. Return the original response if already enveloped (idempotent).

## Tests (`utils/tests/test_drf_error_envelope.py`)
Use `APIRequestFactory`; set `request.request_id`.
- `normalize_validation_detail({"email": [ErrorDetail("This field is required.", code="required")]})` → one item with `code == "VALIDATION__MISSING_FIELD"`, `details["field"] == "email"`.
- `code="blank"` → `VALIDATION__MISSING_FIELD`; `code="invalid"` → `VALIDATION__INVALID_FORMAT`; unknown code → `VALIDATION__INVALID_VALUE`.
- `validation_error_response([...], request)` → status 422, `data["success"] is False`, `data["errors"]` is the list, `meta.version == "v1"`.
- `coerce_drf_error_response(request, Response({"detail": "Not found."}, status=404))` → enveloped with `error.code == "RESOURCE__NOT_FOUND"`, status 404.
- `coerce_drf_error_response(request, Response({"detail": "Conflict."}, status=409))` → `error.code == "RESOURCE__CONFLICT"` (explicitly NOT `INTERNAL__ERROR`).
- A 405 response coerces to a client-error code (`VALIDATION__INVALID_FORMAT`), never `INTERNAL__ERROR`.
- A 500 response falls through to `INTERNAL__ERROR`.
- Idempotency: passing an already-enveloped response returns it unchanged.
- No DB needed.

## Validation
```bash
uv run pytest utils/tests/test_drf_error_envelope.py -x -v --ds=config.django.test
```

## Acceptance Criteria
- [ ] Validation errors normalize to `VALIDATION__*` codes with field context; `"blank"` → `VALIDATION__MISSING_FIELD` in BOTH prose and map (contradiction removed).
- [ ] `validation_error_response` returns 422 envelope with `errors` (plural).
- [ ] `coerce_drf_error_response` maps status→code explicitly; 409 → `RESOURCE__CONFLICT`; no 4xx routed to `INTERNAL__ERROR`; only 5xx falls through to INTERNAL; idempotent.
- [ ] No domain-specific mappings; tests pass.
