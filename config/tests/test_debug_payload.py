"""
Tests for config/middleware/debug_payload.py — DebugPayloadMiddleware.
Path: config/tests/test_debug_payload.py
"""

import json

import pytest
from django.core.exceptions import ImproperlyConfigured
from django.http import HttpResponse
from django.test import RequestFactory, override_settings

from config.logger import logger
from config.middleware.debug_payload import DebugPayloadMiddleware, _redact
from config.settings.config import settings as app_settings


@pytest.fixture
def rf():
    return RequestFactory()


@pytest.fixture
def records():
    """Capture Loguru records emitted during the test via a temporary sink."""
    captured = []
    sink_id = logger.add(lambda message: captured.append(message.record), level="DEBUG")
    try:
        yield captured
    finally:
        logger.remove(sink_id)


def _json_request(rf, path="/api/v1/things/", payload=None, method="post"):
    body = json.dumps(payload or {}).encode("utf-8")
    request = getattr(rf, method)(path, data=body, content_type="application/json")
    return request


class TestRedact:
    def test_redacts_sensitive_keys_and_preserves_others(self):
        source = {"password": "x", "email": "a@b.c", "nested": {"token": "t"}}

        result = _redact(source)

        assert result["password"] == "[REDACTED]"
        assert result["nested"]["token"] == "[REDACTED]"
        assert result["email"] == "a@b.c"

    def test_does_not_mutate_input(self):
        source = {"password": "x", "nested": {"token": "t"}}

        _redact(source)

        assert source["password"] == "x"
        assert source["nested"]["token"] == "t"

    def test_redacts_dicts_nested_inside_lists(self):
        source = {"items": [{"secret": "s"}, {"keep": "v"}]}

        result = _redact(source)

        assert result["items"][0]["secret"] == "[REDACTED]"
        assert result["items"][1]["keep"] == "v"

    def test_scalars_returned_as_is(self):
        assert _redact("plain") == "plain"
        assert _redact(42) == 42
        assert _redact(None) is None

    def test_redacts_sensitive_keys_case_insensitively(self):
        source = {"Password": "x", "TOKEN": "y", "Nested": {"AuthoriZation": "z"}}

        result = _redact(source)

        assert result["Password"] == "[REDACTED]"
        assert result["TOKEN"] == "[REDACTED]"
        assert result["Nested"]["AuthoriZation"] == "[REDACTED]"


class TestConstructionGuard:
    def test_raises_improperly_configured_when_enabled_without_debug(self, monkeypatch):
        monkeypatch.setattr(app_settings, "REQUEST_RESPONSE_DEBUG", True)

        with override_settings(DEBUG=False):
            with pytest.raises(ImproperlyConfigured):
                DebugPayloadMiddleware(lambda r: r)

    def test_does_not_raise_when_enabled_with_debug_true(self, monkeypatch):
        monkeypatch.setattr(app_settings, "REQUEST_RESPONSE_DEBUG", True)

        with override_settings(DEBUG=True):
            middleware = DebugPayloadMiddleware(lambda r: r)

        assert middleware.enabled is True

    def test_does_not_raise_when_disabled_regardless_of_debug(self, monkeypatch):
        monkeypatch.setattr(app_settings, "REQUEST_RESPONSE_DEBUG", False)

        with override_settings(DEBUG=False):
            middleware = DebugPayloadMiddleware(lambda r: r)

        assert middleware.enabled is False


@pytest.fixture
def enabled_middleware(monkeypatch):
    monkeypatch.setattr(app_settings, "REQUEST_RESPONSE_DEBUG", True)
    with override_settings(DEBUG=True):
        yield DebugPayloadMiddleware(lambda r: r)


class TestExcludedPaths:
    def test_admin_path_produces_no_debug_log(self, rf, enabled_middleware, records):
        request = _json_request(rf, path="/admin/", payload={"password": "supersecret"})

        enabled_middleware.process_request(request)

        debug_records = [r for r in records if r["message"] == "debug.request"]
        assert debug_records == []

    def test_health_path_produces_no_debug_log(self, rf, enabled_middleware, records):
        request = _json_request(rf, path="/health/", payload={"password": "supersecret"})

        enabled_middleware.process_request(request)

        debug_records = [r for r in records if r["message"] == "debug.request"]
        assert debug_records == []


class TestRequestBodyRedaction:
    def test_logs_redacted_request_body_without_plaintext_secret(
        self, rf, enabled_middleware, records
    ):
        request = _json_request(
            rf, path="/api/v1/things/", payload={"password": "supersecret", "x": 1}
        )

        enabled_middleware.process_request(request)

        debug_records = [r for r in records if r["message"] == "debug.request"]
        assert len(debug_records) == 1
        body = debug_records[0]["extra"]["body"]
        assert body["password"] == "[REDACTED]"
        assert "supersecret" not in json.dumps(body)

    def test_no_log_when_disabled(self, rf, records, monkeypatch):
        monkeypatch.setattr(app_settings, "REQUEST_RESPONSE_DEBUG", False)
        with override_settings(DEBUG=True):
            middleware = DebugPayloadMiddleware(lambda r: r)
        request = _json_request(rf, payload={"password": "supersecret"})

        middleware.process_request(request)

        debug_records = [r for r in records if r["message"] == "debug.request"]
        assert debug_records == []

    def test_non_json_content_type_is_ignored(self, rf, enabled_middleware, records):
        request = rf.post("/api/v1/things/", data="not json", content_type="text/plain")

        enabled_middleware.process_request(request)

        debug_records = [r for r in records if r["message"] == "debug.request"]
        assert debug_records == []

    def test_malformed_json_body_does_not_raise(self, rf, enabled_middleware, records):
        request = rf.post(
            "/api/v1/things/", data=b"{not-json", content_type="application/json"
        )

        enabled_middleware.process_request(request)

        debug_records = [r for r in records if r["message"] == "debug.request"]
        assert debug_records == []

    def test_empty_body_is_ignored(self, rf, enabled_middleware, records):
        request = rf.post("/api/v1/things/", data=b"", content_type="application/json")

        enabled_middleware.process_request(request)

        debug_records = [r for r in records if r["message"] == "debug.request"]
        assert debug_records == []


class TestResponseBodyRedaction:
    def test_logs_redacted_response_body(self, rf, enabled_middleware, records):
        request = _json_request(rf)
        response = HttpResponse(
            json.dumps({"token": "abc123", "ok": True}).encode("utf-8"),
            content_type="application/json",
        )

        result = enabled_middleware.process_response(request, response)

        assert result is response
        debug_records = [r for r in records if r["message"] == "debug.response"]
        assert len(debug_records) == 1
        body = debug_records[0]["extra"]["body"]
        assert body["token"] == "[REDACTED]"
        assert "abc123" not in json.dumps(body)

    def test_non_json_response_is_ignored(self, rf, enabled_middleware, records):
        request = _json_request(rf)
        response = HttpResponse(b"plain text", content_type="text/plain")

        enabled_middleware.process_response(request, response)

        debug_records = [r for r in records if r["message"] == "debug.response"]
        assert debug_records == []

    def test_streaming_response_is_skipped(self, rf, enabled_middleware, records):
        from django.http import StreamingHttpResponse

        request = _json_request(rf)
        response = StreamingHttpResponse(
            iter([b'{"a": 1}']), content_type="application/json"
        )

        result = enabled_middleware.process_response(request, response)

        assert result is response
        debug_records = [r for r in records if r["message"] == "debug.response"]
        assert debug_records == []

    def test_excluded_path_response_is_skipped(self, rf, enabled_middleware, records):
        request = _json_request(rf, path="/health/")
        response = HttpResponse(
            json.dumps({"status": "ok"}).encode("utf-8"), content_type="application/json"
        )

        enabled_middleware.process_response(request, response)

        debug_records = [r for r in records if r["message"] == "debug.response"]
        assert debug_records == []

    def test_disabled_middleware_skips_response_logging(self, rf, records, monkeypatch):
        monkeypatch.setattr(app_settings, "REQUEST_RESPONSE_DEBUG", False)
        with override_settings(DEBUG=True):
            middleware = DebugPayloadMiddleware(lambda r: r)
        request = _json_request(rf)
        response = HttpResponse(
            json.dumps({"token": "abc123"}).encode("utf-8"), content_type="application/json"
        )

        result = middleware.process_response(request, response)

        assert result is response
        debug_records = [r for r in records if r["message"] == "debug.response"]
        assert debug_records == []
