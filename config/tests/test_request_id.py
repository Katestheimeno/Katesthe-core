"""
Tests for config/middleware/request_id.py — RequestIdMiddleware.
Path: config/tests/test_request_id.py
"""

import pytest
from django.test import RequestFactory

from config.middleware.request_id import RequestIdMiddleware, request_id_ctx


@pytest.fixture
def rf():
    return RequestFactory()


@pytest.fixture
def middleware():
    return RequestIdMiddleware(get_response=lambda request: None)


class TestProcessRequest:
    def test_generates_request_id_when_no_header_present(self, rf, middleware):
        request = rf.get("/health/")

        middleware.process_request(request)

        assert request.request_id.startswith("req_")

    def test_uses_incoming_header_when_present(self, rf, middleware):
        request = rf.get("/health/", HTTP_X_REQUEST_ID="req_from_caller")

        middleware.process_request(request)

        assert request.request_id == "req_from_caller"

    def test_sets_context_var_to_request_id(self, rf, middleware):
        request = rf.get("/health/")

        middleware.process_request(request)

        assert request_id_ctx.get() == request.request_id


class TestProcessResponse:
    def test_sets_x_request_id_header_equal_to_request_id(self, rf, middleware):
        request = rf.get("/health/")
        middleware.process_request(request)
        response = middleware.process_response(request, HttpResponseStub())

        assert response["X-Request-ID"] == request.request_id

    def test_resets_context_var_after_response(self, rf, middleware):
        # Capture the baseline instead of asserting the ContextVar default
        # ("-") directly: pytest runs tests sequentially in the same thread
        # context, so an un-reset `set()` from another test could leak here.
        baseline = request_id_ctx.get()
        request = rf.get("/health/")
        middleware.process_request(request)

        middleware.process_response(request, HttpResponseStub())

        assert request_id_ctx.get() == baseline

    def test_uses_dash_when_request_id_missing(self, rf, middleware):
        request = rf.get("/health/")

        response = middleware.process_response(request, HttpResponseStub())

        assert response["X-Request-ID"] == "-"


class HttpResponseStub(dict):
    """Minimal stand-in for an HttpResponse supporting item assignment."""


@pytest.mark.django_db
class TestIntegration:
    def test_client_response_carries_x_request_id_header(self, client):
        response = client.get("/")

        assert "X-Request-ID" in response
        assert response["X-Request-ID"].startswith("req_")

    def test_client_response_echoes_incoming_request_id_header(self, client):
        response = client.get("/", HTTP_X_REQUEST_ID="req_caller_supplied")

        assert response["X-Request-ID"] == "req_caller_supplied"
