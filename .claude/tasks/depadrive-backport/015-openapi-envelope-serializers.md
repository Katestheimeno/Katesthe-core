# 015 — OpenAPI Envelope Serializers

**Status:** [PENDING]
**Phase:** 2
**Group:** A (concurrent with 010–014, 016)
**Risk:** MEDIUM
**Effort:** 45m
**Dependencies:** Phase 1 complete (mirrors the envelope shapes from 002/003)

## Goal
Add drf-spectacular helpers so the `{success, data, meta}` envelope documents correctly: a list shim serializer, Pydantic envelope models, and reusable `OpenApiExample`/response-dict fragments.

## Context
drf-spectacular's list heuristic wraps non-shim schemas in an extra array. `ApiEnvelopeJsonListSerializer` with `@extend_schema_serializer(many=False)` prevents that. The Pydantic models give correct OpenAPI schema for the envelope. These are documentation-only (no runtime behavior).

## SRC reference to adapt from
`SRC:utils/openapi_serializers.py`, `SRC:utils/schemas/envelope.py`, `SRC:utils/api_openapi.py`. **Strip domain examples** — keep only universal ones (auth 401, permission 403, not-found 404, validation 422, ok 200/201).

## Files Owned
- `utils/openapi_serializers.py` (C)
- `utils/schemas/__init__.py` (C)
- `utils/schemas/envelope.py` (C)
- `utils/api_openapi.py` (C)
- `utils/tests/test_openapi_serializers.py` (C)

## Implementation Steps

### Step 1 — `utils/openapi_serializers.py`
```python
from drf_spectacular.utils import extend_schema_serializer
from rest_framework import serializers

@extend_schema_serializer(many=False)
class ApiEnvelopeJsonListSerializer(serializers.Serializer):
    success = serializers.BooleanField()
    data = serializers.ListField(child=serializers.JSONField())
    meta = serializers.JSONField()
```
(Optionally a `...UserListSerializer` variant with `data` as a dict — only if needed; keep minimal.)

### Step 2 — `utils/schemas/envelope.py` (Pydantic)
```python
from typing import Any, Literal, Optional
from pydantic import BaseModel

class ApiMeta(BaseModel):
    request_id: str
    version: str

class ApiErrorBody(BaseModel):
    code: str
    details: Optional[dict[str, Any]] = None

class ApiErrorEnvelope(BaseModel):
    success: Literal[False]
    error: ApiErrorBody
    meta: ApiMeta

class ApiValidationErrorItem(BaseModel):
    code: str
    details: Optional[dict[str, Any]] = None

class ApiValidationErrorsEnvelope(BaseModel):
    success: Literal[False]
    errors: list[ApiValidationErrorItem]
    meta: ApiMeta

class ApiSuccessEnvelope(BaseModel):
    success: Literal[True]
    data: Any
    meta: ApiMeta
```
`utils/schemas/__init__.py`: re-export these.

### Step 3 — `utils/api_openapi.py`
Provide `EXAMPLE_META = {"request_id": "req_example", "version": "v1"}` and universal `OpenApiExample` instances (ok, single-error 401/403/404, validation 422) plus reusable response dicts, e.g. `AUTHENTICATED_READ_RESPONSES = {401: ..., 403: ..., 404: ...}`. Keep examples generic (no assistance/depanneur data). Use `drf_spectacular.utils.OpenApiExample`.

## Tests (`utils/tests/test_openapi_serializers.py`)
- Import all symbols successfully.
- `ApiEnvelopeJsonListSerializer` instantiates; its fields include `success`, `data`, `meta`.
- Pydantic: `ApiErrorEnvelope(success=False, error={"code":"X"}, meta={"request_id":"r","version":"v1"})` validates; `success=True` on the error envelope raises `ValidationError`.
- `EXAMPLE_META["version"] == "v1"`.
- Schema generation smoke: `drf_spectacular` can be imported and the shim's `@extend_schema_serializer` is applied (assert the attribute exists) — full schema generation is covered by the feature validation gate (024).

## Validation
```bash
uv run pytest utils/tests/test_openapi_serializers.py -x -v --ds=config.django.test
uv run python manage.py spectacular --validate --fail-on-warn --settings=config.django.test
```

## Acceptance Criteria
- [ ] List shim uses `@extend_schema_serializer(many=False)`.
- [ ] Pydantic envelope models mirror the `{success,data,meta}` / error / validation shapes.
- [ ] Universal-only examples + response dicts; no domain data.
- [ ] `spectacular --validate --fail-on-warn` still exits 0; tests pass.
