"""
Tests for named throttle scopes and rate-limit registration.
Path: utils/tests/test_throttles.py
"""

import pytest
from django.conf import settings
from django.core.cache import cache
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.test import APIRequestFactory
from rest_framework.views import APIView

from utils.throttles import AuthLoginThrottle, PasswordResetThrottle


class TestThrottleScopes:
    """Named throttle classes declare the expected scope."""

    def test_auth_login_throttle_has_auth_login_scope(self):
        assert AuthLoginThrottle.scope == "auth_login"

    def test_password_reset_throttle_has_auth_password_reset_scope(self):
        assert PasswordResetThrottle.scope == "auth_password_reset"


class TestThrottleRatesRegistered:
    """`DEFAULT_THROTTLE_RATES` registers the four universal scopes."""

    def test_default_throttle_rates_contains_expected_scopes(self):
        rates = settings.REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"]

        assert {"anon", "user", "auth_login", "auth_password_reset"}.issubset(
            rates.keys()
        )


class _ThrottledPingView(APIView):
    """Throwaway view exercising `AuthLoginThrottle` end to end."""

    permission_classes = [AllowAny]
    throttle_classes = [AuthLoginThrottle]

    def get(self, request):
        return Response({"pong": True})


@pytest.mark.django_db
class TestAuthLoginThrottleIntegration:
    """A client exceeding `AuthLoginThrottle`'s rate is rejected with 429."""

    def test_third_request_is_throttled_with_rate_limit_envelope(self, monkeypatch):
        cache.clear()
        monkeypatch.setattr(
            AuthLoginThrottle, "THROTTLE_RATES", {"auth_login": "2/minute"}
        )

        factory = APIRequestFactory()
        view = _ThrottledPingView.as_view()

        first = view(factory.get("/", REMOTE_ADDR="10.0.0.1"))
        second = view(factory.get("/", REMOTE_ADDR="10.0.0.1"))
        third = view(factory.get("/", REMOTE_ADDR="10.0.0.1"))

        assert first.status_code == 200
        assert second.status_code == 200
        assert third.status_code == 429
        assert third.data["error"]["code"] == "RATE_LIMIT__EXCEEDED"
