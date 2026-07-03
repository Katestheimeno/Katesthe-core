"""
Tests for the API response envelope helpers.
Path: utils/tests/test_api_response.py
"""

from rest_framework.test import APIRequestFactory

from utils.api_response import err_single, ok

factory = APIRequestFactory()


def _build_request(request_id="req_test123"):
    request = factory.get("/")
    if request_id is not None:
        request.request_id = request_id
    return request


class TestOk:
    """Behavior of the `ok` success envelope helper."""

    def test_wraps_data_with_success_true(self):
        request = _build_request()

        response = ok({"a": 1}, request)

        assert response.data["success"] is True
        assert response.data["data"] == {"a": 1}

    def test_meta_carries_request_id_and_version(self):
        request = _build_request()

        response = ok({"a": 1}, request)

        assert response.data["meta"]["request_id"] == "req_test123"
        assert response.data["meta"]["version"] == "v1"

    def test_default_status_is_200(self):
        request = _build_request()

        response = ok({"a": 1}, request)

        assert response.status_code == 200

    def test_custom_status_is_honored(self):
        request = _build_request()

        response = ok({"a": 1}, request, status=201)

        assert response.status_code == 201

    def test_meta_extra_merges_into_meta(self):
        request = _build_request()

        response = ok({"a": 1}, request, meta_extra={"count": 5})

        assert response.data["meta"]["count"] == 5
        assert response.data["meta"]["request_id"] == "req_test123"
        assert response.data["meta"]["version"] == "v1"

    def test_no_message_key_in_payload(self):
        request = _build_request()

        response = ok({"a": 1}, request)

        assert "message" not in response.data
        assert "message" not in response.data["meta"]


class TestErrSingle:
    """Behavior of the `err_single` failure envelope helper."""

    def test_wraps_error_with_success_false(self):
        request = _build_request()

        response = err_single(
            "RESOURCE__NOT_FOUND", request, status=404, details={"pk": 5}
        )

        assert response.data["success"] is False
        assert response.data["error"]["code"] == "RESOURCE__NOT_FOUND"
        assert response.data["error"]["details"] == {"pk": 5}
        assert response.status_code == 404

    def test_details_defaults_to_empty_dict_when_none(self):
        request = _build_request()

        response = err_single("INTERNAL__ERROR", request, status=500)

        assert response.data["error"]["details"] == {}

    def test_status_defaults_to_400(self):
        request = _build_request()

        response = err_single("VALIDATION__INVALID_VALUE", request)

        assert response.status_code == 400

    def test_status_is_keyword_only(self):
        request = _build_request()

        try:
            err_single("VALIDATION__INVALID_VALUE", request, 404)
            raised = False
        except TypeError:
            raised = True

        assert raised is True

    def test_meta_carries_request_id_and_version(self):
        request = _build_request()

        response = err_single("RESOURCE__NOT_FOUND", request, status=404)

        assert response.data["meta"]["request_id"] == "req_test123"
        assert response.data["meta"]["version"] == "v1"

    def test_no_message_key_in_payload(self):
        request = _build_request()

        response = err_single("RESOURCE__NOT_FOUND", request, status=404)

        assert "message" not in response.data
        assert "message" not in response.data["error"]
        assert "message" not in response.data["meta"]


class TestMetaFallback:
    """Behavior of the request-id fallback when the middleware is absent."""

    def test_request_without_request_id_gets_non_empty_fallback(self):
        request = _build_request(request_id=None)

        response = ok({"a": 1}, request)

        request_id = response.data["meta"]["request_id"]
        assert request_id
        assert request_id.startswith("req_")

    def test_request_none_gets_non_empty_fallback(self):
        response = ok({"a": 1}, None)

        request_id = response.data["meta"]["request_id"]
        assert request_id
        assert request_id.startswith("req_")

    def test_fallback_ids_are_unique_per_call(self):
        first = ok({"a": 1}, None)
        second = ok({"a": 1}, None)

        assert first.data["meta"]["request_id"] != second.data["meta"]["request_id"]
