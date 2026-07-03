# 004 — Pydantic→drf-spectacular bridge (7.1)

**Status:** [PENDING]
**Phase:** 1
**Group:** A
**Risk:** MEDIUM
**Effort:** 35m
**Dependencies:** none

## Goal
Add helpers that let Pydantic `BaseModel` types be used directly in `extend_schema(responses=...)`, since drf-spectacular does not natively resolve Pydantic models.

## Context
Extracted verbatim (already generic) from `SRC:config/spectacular_pydantic.py`. Produces JSON Schema dicts via `model.model_json_schema()` and wraps them in `OpenApiResponse`.

## Existing pattern to follow
- `SRC:/home/tmpusr/Documents/github/Rhitoric-core/config/spectacular_pydantic.py` — copy as-is (no domain logic).
- Existing spectacular usage in this repo: `config/settings/spectacular.py`, `utils/openapi_serializers.py`, `utils/api_openapi.py`.

## Files Owned
- `config/spectacular_pydantic.py`
- `config/tests/test_spectacular_pydantic.py`

## Implementation Steps

### Step 1 — Create `config/spectacular_pydantic.py`
Implement four public functions plus one private predicate:
- `pydantic_schema(model: type[BaseModel]) -> dict` → `return model.model_json_schema()`.
- `pydantic_array_schema(model) -> dict` → `{"type": "array", "items": model.model_json_schema()}`.
- `pydantic_one_of_schema(*models) -> dict` → `{"oneOf": [m.model_json_schema() for m in models]}`.
- `_is_pydantic_model(t) -> bool` → `isinstance(t, type) and issubclass(t, BaseModel)` guarded by try/except `TypeError`.
- `as_openapi_response(hint, *, description="") -> Any`:
  - Import `OpenApiResponse` lazily inside the function (`from drf_spectacular.utils import OpenApiResponse`) so the module imports even where drf-spectacular is a dev-only dep.
  - `origin = get_origin(hint)`; if `origin is list` and `get_args(hint)[0]` is a Pydantic model → `OpenApiResponse(response=pydantic_array_schema(args[0]), description=description or "")`.
  - If `_is_pydantic_model(hint)` → `OpenApiResponse(response=pydantic_schema(hint), description=description or "")`.
  - Otherwise return `hint` unchanged (DRF serializers, `None`, etc. pass through).

Use `from __future__ import annotations`, `from typing import Any, get_origin, get_args`, `from pydantic import BaseModel`. NOTE: `drf-spectacular` is a dev-group dependency in `pyproject.toml`; keep its import lazy inside `as_openapi_response` so the other three functions work without it.

## Tests
Create `config/tests/test_spectacular_pydantic.py` (no DB). Define a small local `class Dummy(BaseModel): name: str; value: int`.
- `pydantic_schema(Dummy)` returns a dict with `"properties"` containing `name` and `value`.
- `pydantic_array_schema(Dummy)` returns `{"type": "array", "items": {...}}`.
- `pydantic_one_of_schema(Dummy, OtherDummy)` returns a dict with `"oneOf"` of length 2.
- `as_openapi_response(Dummy)` returns an `OpenApiResponse` whose `.response` equals `pydantic_schema(Dummy)`.
- `as_openapi_response(list[Dummy])` returns an `OpenApiResponse` with an array schema.
- `as_openapi_response(SomeDrfSerializerClass)` (or a plain `str`/`None`) returns the hint unchanged (passthrough branch).

## Validation
```bash
uv run pytest config/tests/test_spectacular_pydantic.py -x -v --ds=config.django.test
uv run python -c "
from config.spectacular_pydantic import pydantic_schema, pydantic_array_schema, pydantic_one_of_schema, as_openapi_response
from pydantic import BaseModel
class D(BaseModel):
    name: str
print(pydantic_schema(D)); print('OK')
"
uv run python manage.py spectacular --validate --fail-on-warn --settings=config.django.test
```

## Acceptance Criteria
- [ ] All four public functions importable and produce valid JSON Schema dicts.
- [ ] `as_openapi_response` covers all three branches (pydantic, list[pydantic], passthrough).
- [ ] `OpenApiResponse` import is lazy (module imports without drf-spectacular installed).
- [ ] OpenAPI schema still validates.
