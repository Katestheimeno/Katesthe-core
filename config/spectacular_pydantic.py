"""
Helpers to use Pydantic models in drf-spectacular extend_schema.

drf-spectacular does not resolve Pydantic BaseModel in responses=...
Use these helpers to produce OpenAPI schema dicts and pass them via OpenApiResponse.
Path: config/spectacular_pydantic.py
"""
from __future__ import annotations

from typing import Any, get_args, get_origin

from pydantic import BaseModel


def pydantic_schema(model: type[BaseModel]) -> dict[str, Any]:
    """
    Return an OpenAPI/JSON Schema dict for a Pydantic model for use in
    extend_schema(responses={...}) with OpenApiResponse(response=...).

    Usage:
        from drf_spectacular.utils import OpenApiResponse
        responses={200: OpenApiResponse(response=pydantic_schema(MyResponse))}
    """
    return model.model_json_schema()


def pydantic_array_schema(model: type[BaseModel]) -> dict[str, Any]:
    """
    Return an OpenAPI array schema whose items are the given Pydantic model.
    Use for list[MyResponse] in extend_schema.
    """
    item_schema = model.model_json_schema()
    return {"type": "array", "items": item_schema}


def pydantic_one_of_schema(*models: type[BaseModel]) -> dict[str, Any]:
    """
    Return an OpenAPI oneOf schema for a Union of Pydantic models.
    Use for Union[ModelA, ModelB] in extend_schema.
    """
    return {"oneOf": [m.model_json_schema() for m in models]}


def _is_pydantic_model(t: Any) -> bool:
    try:
        return isinstance(t, type) and issubclass(t, BaseModel)
    except TypeError:
        return False


def as_openapi_response(
    hint: Any,
    *,
    description: str = "",
) -> Any:
    """
    Convert a type hint used in extend_schema(responses=...) to something
    drf-spectacular can resolve. Use for Pydantic models and list[Pydantic].

    - Pydantic model class -> OpenApiResponse(response=schema_dict)
    - list[Pydantic] (e.g. list[VoteResponse]) -> OpenApiResponse(response=array_schema_dict)

    For non-Pydantic types (e.g. DRF serializers), returns the hint unchanged.
    """
    from drf_spectacular.utils import OpenApiResponse

    origin = get_origin(hint)
    if origin is list:
        args = get_args(hint)
        if args and _is_pydantic_model(args[0]):
            return OpenApiResponse(
                response=pydantic_array_schema(args[0]),
                description=description or "",
            )
    if _is_pydantic_model(hint):
        return OpenApiResponse(
            response=pydantic_schema(hint),
            description=description or "",
        )
    return hint
