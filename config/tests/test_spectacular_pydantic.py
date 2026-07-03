"""
Tests for config/spectacular_pydantic.py — Pydantic to drf-spectacular bridge.
"""

from drf_spectacular.utils import OpenApiResponse
from pydantic import BaseModel

from config.spectacular_pydantic import (
    as_openapi_response,
    pydantic_array_schema,
    pydantic_one_of_schema,
    pydantic_schema,
)


class Dummy(BaseModel):
    name: str
    value: int


class OtherDummy(BaseModel):
    label: str


class TestPydanticSchema:
    def test_returns_dict_with_declared_properties(self):
        schema = pydantic_schema(Dummy)

        assert "name" in schema["properties"]
        assert "value" in schema["properties"]


class TestPydanticArraySchema:
    def test_returns_array_schema_wrapping_model_schema(self):
        schema = pydantic_array_schema(Dummy)

        assert schema == {"type": "array", "items": Dummy.model_json_schema()}


class TestPydanticOneOfSchema:
    def test_returns_one_of_schema_with_two_models(self):
        schema = pydantic_one_of_schema(Dummy, OtherDummy)

        assert len(schema["oneOf"]) == 2
        assert schema["oneOf"][0] == Dummy.model_json_schema()
        assert schema["oneOf"][1] == OtherDummy.model_json_schema()


class TestAsOpenapiResponsePydanticBranch:
    def test_pydantic_model_returns_openapi_response_matching_pydantic_schema(self):
        result = as_openapi_response(Dummy)

        assert isinstance(result, OpenApiResponse)
        assert result.response == pydantic_schema(Dummy)


class TestAsOpenapiResponseListBranch:
    def test_list_of_pydantic_model_returns_openapi_response_with_array_schema(self):
        result = as_openapi_response(list[Dummy])

        assert isinstance(result, OpenApiResponse)
        assert result.response == pydantic_array_schema(Dummy)


class TestAsOpenapiResponsePassthroughBranch:
    def test_plain_string_hint_returns_hint_unchanged(self):
        result = as_openapi_response("SomeDrfSerializer")

        assert result == "SomeDrfSerializer"

    def test_none_hint_returns_none_unchanged(self):
        result = as_openapi_response(None)

        assert result is None
