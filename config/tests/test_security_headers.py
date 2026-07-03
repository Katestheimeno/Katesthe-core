"""
Tests for config/middleware/security_headers.py — SecurityHeadersMiddleware.
Path: config/tests/test_security_headers.py
"""

import pytest
from django.http import HttpResponse
from django.test import RequestFactory, override_settings

from config.middleware.security_headers import SecurityHeadersMiddleware


@pytest.fixture
def rf():
    return RequestFactory()


def _middleware(response):
    return SecurityHeadersMiddleware(get_response=lambda request: response)


class TestSetsDefaultHeaders:
    def test_sets_referrer_policy_to_default_when_setting_absent(self, rf):
        request = rf.get("/api/v1/users/")
        middleware = _middleware(HttpResponse())

        response = middleware(request)

        assert response["Referrer-Policy"] == "strict-origin-when-cross-origin"

    def test_sets_permissions_policy_header(self, rf):
        request = rf.get("/api/v1/users/")
        middleware = _middleware(HttpResponse())

        response = middleware(request)

        assert response["Permissions-Policy"] == (
            "accelerometer=(),"
            "camera=(),"
            "display-capture=(),"
            "fullscreen=(self),"
            "geolocation=(),"
            "gyroscope=(),"
            "magnetometer=(),"
            "microphone=(),"
            "payment=(),"
            "usb=()"
        )

    @override_settings(SECURE_REFERRER_POLICY="no-referrer")
    def test_uses_secure_referrer_policy_setting_when_present(self, rf):
        request = rf.get("/api/v1/users/")
        middleware = _middleware(HttpResponse())

        response = middleware(request)

        assert response["Referrer-Policy"] == "no-referrer"


class TestDoesNotClobberPresetHeaders:
    def test_setdefault_does_not_override_existing_referrer_policy(self, rf):
        preset = HttpResponse()
        preset["Referrer-Policy"] = "same-origin"
        request = rf.get("/api/v1/users/")
        middleware = _middleware(preset)

        response = middleware(request)

        assert response["Referrer-Policy"] == "same-origin"

    def test_setdefault_does_not_override_existing_permissions_policy(self, rf):
        preset = HttpResponse()
        preset["Permissions-Policy"] = "camera=(self)"
        request = rf.get("/api/v1/users/")
        middleware = _middleware(preset)

        response = middleware(request)

        assert response["Permissions-Policy"] == "camera=(self)"


@pytest.mark.django_db
class TestIntegration:
    def test_client_response_carries_security_headers(self, client):
        response = client.get("/")

        assert response["Referrer-Policy"] == "strict-origin-when-cross-origin"
        assert "Permissions-Policy" in response
