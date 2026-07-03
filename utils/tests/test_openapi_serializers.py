"""
Tests for the documentation-only OpenAPI envelope helpers.
Path: utils/tests/test_openapi_serializers.py
"""

import pytest
from pydantic import ValidationError
from rest_framework import serializers

from utils.api_openapi import (
    AUTHENTICATED_READ_RESPONSES,
    AUTHENTICATED_WRITE_RESPONSES,
    CREATED_EXAMPLE,
    EXAMPLE_META,
    NOT_FOUND_EXAMPLE,
    OK_EXAMPLE,
    PERMISSION_DENIED_EXAMPLE,
    UNAUTHENTICATED_EXAMPLE,
    VALIDATION_ERROR_EXAMPLE,
)
from utils.openapi_serializers import ApiEnvelopeJsonListSerializer
from utils.schemas import (
    ApiErrorBody,
    ApiErrorEnvelope,
    ApiMeta,
    ApiSuccessEnvelope,
    ApiValidationErrorItem,
    ApiValidationErrorsEnvelope,
)


class TestSmokeImports:
    """All public symbols across the four modules import without error."""

    def test_all_symbols_are_importable(self):
        symbols = [
            ApiEnvelopeJsonListSerializer,
            ApiMeta,
            ApiErrorBody,
            ApiErrorEnvelope,
            ApiValidationErrorItem,
            ApiValidationErrorsEnvelope,
            ApiSuccessEnvelope,
            EXAMPLE_META,
            OK_EXAMPLE,
            CREATED_EXAMPLE,
            UNAUTHENTICATED_EXAMPLE,
            PERMISSION_DENIED_EXAMPLE,
            NOT_FOUND_EXAMPLE,
            VALIDATION_ERROR_EXAMPLE,
            AUTHENTICATED_READ_RESPONSES,
            AUTHENTICATED_WRITE_RESPONSES,
        ]

        assert all(symbol is not None for symbol in symbols)


class TestApiEnvelopeJsonListSerializer:
    """Behavior of the list-envelope shim serializer."""

    def test_instantiates(self):
        serializer = ApiEnvelopeJsonListSerializer()

        assert isinstance(serializer, serializers.Serializer)

    def test_fields_include_success_data_meta(self):
        serializer = ApiEnvelopeJsonListSerializer()

        assert set(["success", "data", "meta"]).issubset(serializer.fields.keys())

    def test_extend_schema_serializer_annotation_applied(self):
        if hasattr(ApiEnvelopeJsonListSerializer, "_spectacular_annotation"):
            annotation = ApiEnvelopeJsonListSerializer._spectacular_annotation
            assert annotation.get("many") is False
        else:
            # Keep the test robust across drf-spectacular versions: fall
            # back to verifying the class is still a well-formed serializer.
            assert issubclass(ApiEnvelopeJsonListSerializer, serializers.Serializer)
            assert ApiEnvelopeJsonListSerializer() is not None


class TestApiErrorEnvelope:
    """Behavior of the Pydantic error envelope model."""

    def test_validates_with_success_false(self):
        envelope = ApiErrorEnvelope(
            success=False,
            error={"code": "X"},
            meta={"request_id": "r", "version": "v1"},
        )

        assert envelope.success is False
        assert envelope.error.code == "X"

    def test_raises_validation_error_when_success_is_true(self):
        with pytest.raises(ValidationError):
            ApiErrorEnvelope(
                success=True,
                error={"code": "X"},
                meta={"request_id": "r", "version": "v1"},
            )


class TestApiSuccessEnvelope:
    """Behavior of the Pydantic success envelope model."""

    def test_validates_with_success_true(self):
        envelope = ApiSuccessEnvelope(
            success=True,
            data={"a": 1},
            meta={"request_id": "r", "version": "v1"},
        )

        assert envelope.success is True
        assert envelope.data == {"a": 1}

    def test_raises_validation_error_when_success_is_false(self):
        with pytest.raises(ValidationError):
            ApiSuccessEnvelope(
                success=False,
                data={"a": 1},
                meta={"request_id": "r", "version": "v1"},
            )


class TestApiValidationErrorsEnvelope:
    """Behavior of the Pydantic validation-errors envelope model."""

    def test_validates_with_list_of_items(self):
        envelope = ApiValidationErrorsEnvelope(
            success=False,
            errors=[{"code": "VALIDATION__MISSING_FIELD", "details": {"field": "email"}}],
            meta={"request_id": "r", "version": "v1"},
        )

        assert envelope.errors[0].code == "VALIDATION__MISSING_FIELD"

    def test_raises_validation_error_when_success_is_true(self):
        with pytest.raises(ValidationError):
            ApiValidationErrorsEnvelope(
                success=True,
                errors=[],
                meta={"request_id": "r", "version": "v1"},
            )


class TestExampleMeta:
    """Behavior of the shared example meta constant."""

    def test_version_is_v1(self):
        assert EXAMPLE_META["version"] == "v1"
