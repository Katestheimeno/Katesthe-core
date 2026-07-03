"""
Tests for DRF error envelope normalization helpers.
Path: utils/tests/test_drf_error_envelope.py
"""

from rest_framework.exceptions import ErrorDetail
from rest_framework.response import Response
from rest_framework.test import APIRequestFactory

from utils.drf_error_envelope import (
    coerce_drf_error_response,
    normalize_validation_detail,
    validation_error_response,
)

factory = APIRequestFactory()


def _build_request(request_id="req_test123"):
    request = factory.get("/")
    if request_id is not None:
        request.request_id = request_id
    return request


class TestNormalizeValidationDetail:
    """Behavior of `normalize_validation_detail` for DRF field-error shapes."""

    def test_required_code_maps_to_missing_field(self):
        detail = {"email": [ErrorDetail("This field is required.", code="required")]}

        errors = normalize_validation_detail(detail)

        assert len(errors) == 1
        assert errors[0]["code"] == "VALIDATION__MISSING_FIELD"
        assert errors[0]["details"]["field"] == "email"

    def test_null_code_maps_to_missing_field(self):
        detail = {"name": [ErrorDetail("This field may not be null.", code="null")]}

        errors = normalize_validation_detail(detail)

        assert errors[0]["code"] == "VALIDATION__MISSING_FIELD"

    def test_blank_code_maps_to_missing_field(self):
        detail = {"name": [ErrorDetail("This field may not be blank.", code="blank")]}

        errors = normalize_validation_detail(detail)

        assert errors[0]["code"] == "VALIDATION__MISSING_FIELD"

    def test_invalid_code_maps_to_invalid_format(self):
        detail = {"age": [ErrorDetail("A valid integer is required.", code="invalid")]}

        errors = normalize_validation_detail(detail)

        assert errors[0]["code"] == "VALIDATION__INVALID_FORMAT"

    def test_invalid_choice_code_maps_to_invalid_value(self):
        detail = {
            "status": [ErrorDetail("Not a valid choice.", code="invalid_choice")]
        }

        errors = normalize_validation_detail(detail)

        assert errors[0]["code"] == "VALIDATION__INVALID_VALUE"

    def test_unknown_code_defaults_to_invalid_value(self):
        detail = {"field": [ErrorDetail("Something odd.", code="some_weird_code")]}

        errors = normalize_validation_detail(detail)

        assert errors[0]["code"] == "VALIDATION__INVALID_VALUE"

    def test_missing_code_attribute_defaults_to_invalid_value(self):
        detail = {"field": ["plain string, no ErrorDetail"]}

        errors = normalize_validation_detail(detail)

        assert errors[0]["code"] == "VALIDATION__INVALID_VALUE"

    def test_dict_with_multiple_errors_per_field_produces_multiple_entries(self):
        detail = {
            "email": [
                ErrorDetail("required", code="required"),
                ErrorDetail("invalid format", code="invalid"),
            ]
        }

        errors = normalize_validation_detail(detail)

        assert len(errors) == 2
        assert {e["code"] for e in errors} == {
            "VALIDATION__MISSING_FIELD",
            "VALIDATION__INVALID_FORMAT",
        }

    def test_non_field_list_detail_uses_non_field_errors_key(self):
        detail = [ErrorDetail("Passwords do not match.", code="invalid")]

        errors = normalize_validation_detail(detail)

        assert errors[0]["details"]["field"] == "non_field_errors"
        assert errors[0]["code"] == "VALIDATION__INVALID_FORMAT"

    def test_scalar_detail_uses_non_field_errors_key(self):
        detail = ErrorDetail("Something went wrong.", code="required")

        errors = normalize_validation_detail(detail)

        assert errors[0]["details"]["field"] == "non_field_errors"
        assert errors[0]["code"] == "VALIDATION__MISSING_FIELD"


class TestValidationErrorResponse:
    """Behavior of `validation_error_response`."""

    def test_returns_422_with_errors_list_and_meta(self):
        request = _build_request()
        errors_list = [
            {"code": "VALIDATION__MISSING_FIELD", "details": {"field": "email"}}
        ]

        response = validation_error_response(errors_list, request)

        assert response.status_code == 422
        assert response.data["success"] is False
        assert response.data["errors"] == errors_list
        assert response.data["meta"]["version"] == "v1"
        assert response.data["meta"]["request_id"] == "req_test123"


class TestCoerceDrfErrorResponse:
    """Behavior of `coerce_drf_error_response`."""

    def test_404_detail_response_becomes_resource_not_found(self):
        request = _build_request()
        raw = Response({"detail": "Not found."}, status=404)

        response = coerce_drf_error_response(request, raw)

        assert response.status_code == 404
        assert response.data["success"] is False
        assert response.data["error"]["code"] == "RESOURCE__NOT_FOUND"

    def test_401_detail_response_becomes_unauthenticated(self):
        request = _build_request()
        raw = Response(
            {"detail": "Authentication credentials were not provided."}, status=401
        )

        response = coerce_drf_error_response(request, raw)

        assert response.data["error"]["code"] == "AUTH__UNAUTHENTICATED"

    def test_403_detail_response_becomes_permission_denied(self):
        request = _build_request()
        raw = Response({"detail": "Permission denied."}, status=403)

        response = coerce_drf_error_response(request, raw)

        assert response.data["error"]["code"] == "PERMISSION__DENIED"

    def test_409_detail_response_becomes_resource_conflict_not_internal_error(self):
        request = _build_request()
        raw = Response({"detail": "Conflict."}, status=409)

        response = coerce_drf_error_response(request, raw)

        assert response.data["error"]["code"] == "RESOURCE__CONFLICT"
        assert response.data["error"]["code"] != "INTERNAL__ERROR"

    def test_405_detail_response_becomes_client_error_never_internal_error(self):
        request = _build_request()
        raw = Response({"detail": "Method not allowed."}, status=405)

        response = coerce_drf_error_response(request, raw)

        assert response.data["error"]["code"] == "VALIDATION__INVALID_FORMAT"
        assert response.data["error"]["code"] != "INTERNAL__ERROR"

    def test_429_detail_response_becomes_rate_limit_exceeded(self):
        request = _build_request()
        raw = Response({"detail": "Request was throttled."}, status=429)

        response = coerce_drf_error_response(request, raw)

        assert response.data["error"]["code"] == "RATE_LIMIT__EXCEEDED"

    def test_unlisted_4xx_status_defaults_to_invalid_value(self):
        request = _build_request()
        raw = Response({"detail": "I'm a teapot."}, status=418)

        response = coerce_drf_error_response(request, raw)

        assert response.data["error"]["code"] == "VALIDATION__INVALID_VALUE"

    def test_500_detail_response_falls_through_to_internal_error(self):
        request = _build_request()
        raw = Response({"detail": "Server error."}, status=500)

        response = coerce_drf_error_response(request, raw)

        assert response.data["error"]["code"] == "INTERNAL__ERROR"

    def test_coerced_response_does_not_leak_drf_detail_prose(self):
        request = _build_request()
        raw = Response({"detail": "Not found."}, status=404)

        response = coerce_drf_error_response(request, raw)

        assert response.data["error"]["code"] == "RESOURCE__NOT_FOUND"
        assert response.data["error"]["details"] == {}
        assert "Not found." not in str(response.data["error"])

    def test_already_enveloped_response_is_returned_unchanged(self):
        request = _build_request()
        enveloped = Response(
            {
                "success": False,
                "error": {"code": "RESOURCE__NOT_FOUND", "details": {}},
                "meta": {"request_id": "req_test123", "version": "v1"},
            },
            status=404,
        )

        response = coerce_drf_error_response(request, enveloped)

        assert response is enveloped

    def test_response_without_detail_key_is_returned_unchanged(self):
        request = _build_request()
        other = Response({"count": 5, "results": []}, status=200)

        response = coerce_drf_error_response(request, other)

        assert response is other
