"""
Tests for config/middleware/access_log.py — AccessLogMiddleware.
Path: config/tests/test_access_log.py
"""

import pytest
from django.contrib.auth.models import AnonymousUser
from django.http import HttpResponse
from django.test import RequestFactory

from config.logger import logger
from config.middleware.access_log import AccessLogMiddleware


@pytest.fixture
def rf():
    return RequestFactory()


@pytest.fixture
def middleware():
    return AccessLogMiddleware(get_response=lambda request: None)


@pytest.fixture
def records():
    """Capture Loguru records emitted during the test via a temporary sink."""
    captured = []
    sink_id = logger.add(lambda message: captured.append(message.record), level="INFO")
    try:
        yield captured
    finally:
        logger.remove(sink_id)


def _request(rf, path="/api/v1/users/", method="get", **extra):
    request = getattr(rf, method)(path, **extra)
    request.user = AnonymousUser()
    return request


class TestProcessRequest:
    def test_sets_access_start_timer(self, rf, middleware):
        request = _request(rf)

        middleware.process_request(request)

        assert hasattr(request, "_access_start")


class TestProcessResponseLogsNormalRequest:
    def test_logs_one_http_access_record_for_200_api_path(self, rf, middleware, records):
        request = _request(rf, path="/api/v1/users/")
        middleware.process_request(request)
        response = HttpResponse(b"hello", status=200)

        middleware.process_response(request, response)

        access_records = [r for r in records if r["message"] == "http.access"]
        assert len(access_records) == 1

    def test_logged_record_has_expected_bound_fields(self, rf, middleware, records):
        request = _request(rf, path="/api/v1/users/")
        middleware.process_request(request)
        response = HttpResponse(b"hello", status=200)

        middleware.process_response(request, response)

        extra = records[0]["extra"]
        assert extra["method"] == "GET"
        assert extra["path"] == "/api/v1/users/"
        assert extra["status"] == 200
        assert extra["size"] == len(b"hello")
        assert extra["user_id"] is None
        assert extra["request_id"] == "-"
        assert extra["access"] is True
        assert isinstance(extra["duration_ms"], float)


class TestProcessResponseSkipsNoise:
    def test_skips_logging_for_health_check_200(self, rf, middleware, records):
        request = _request(rf, path="/health/")
        middleware.process_request(request)
        response = HttpResponse(status=200)

        middleware.process_response(request, response)

        access_records = [r for r in records if r["message"] == "http.access"]
        assert access_records == []

    def test_does_not_skip_health_path_when_status_is_not_200(self, rf, middleware, records):
        request = _request(rf, path="/health/")
        middleware.process_request(request)
        response = HttpResponse(status=503)

        middleware.process_response(request, response)

        access_records = [r for r in records if r["message"] == "http.access"]
        assert len(access_records) == 1


class TestProcessResponseErrorEnrichment:
    def test_logs_at_warning_level_for_500_and_includes_ip_and_user_agent(
        self, rf, middleware, records
    ):
        request = _request(
            rf,
            path="/api/v1/boom/",
            HTTP_USER_AGENT="pytest-agent",
            REMOTE_ADDR="10.0.0.5",
        )
        middleware.process_request(request)
        response = HttpResponse(status=500)

        middleware.process_response(request, response)

        access_records = [r for r in records if r["message"] == "http.access"]
        assert len(access_records) == 1
        record = access_records[0]
        assert record["level"].name == "WARNING"
        assert record["extra"]["ip"] == "10.0.0.5"
        assert record["extra"]["user_agent"] == "pytest-agent"

    def test_uses_first_hop_of_x_forwarded_for_when_present(self, rf, middleware, records):
        request = _request(
            rf,
            path="/api/v1/boom/",
            HTTP_X_FORWARDED_FOR="203.0.113.5, 10.0.0.1",
            REMOTE_ADDR="10.0.0.1",
        )
        middleware.process_request(request)
        response = HttpResponse(status=404)

        middleware.process_response(request, response)

        access_records = [r for r in records if r["message"] == "http.access"]
        assert access_records[0]["extra"]["ip"] == "203.0.113.5"

    def test_logs_at_info_level_for_4xx(self, rf, middleware, records):
        request = _request(rf, path="/api/v1/missing/")
        middleware.process_request(request)
        response = HttpResponse(status=404)

        middleware.process_response(request, response)

        access_records = [r for r in records if r["message"] == "http.access"]
        assert access_records[0]["level"].name == "INFO"


class TestDurationMs:
    def test_duration_ms_is_non_negative_float(self, rf, middleware, records):
        request = _request(rf)
        middleware.process_request(request)
        response = HttpResponse(status=200)

        middleware.process_response(request, response)

        duration_ms = records[0]["extra"]["duration_ms"]
        assert isinstance(duration_ms, float)
        assert duration_ms >= 0

    def test_missing_access_start_does_not_crash_and_yields_zero_duration(
        self, rf, middleware, records
    ):
        request = _request(rf)
        response = HttpResponse(status=200)

        middleware.process_response(request, response)

        assert records[0]["extra"]["duration_ms"] == 0.0


class TestStreamingResponseGuard:
    def test_streaming_response_reports_zero_size(self, rf, middleware, records):
        from django.http import StreamingHttpResponse

        request = _request(rf)
        middleware.process_request(request)
        response = StreamingHttpResponse(iter([b"a", b"b"]), status=200)

        middleware.process_response(request, response)

        assert records[0]["extra"]["size"] == 0
