"""
Tests for the throttle base-class hierarchy and universal throttle scopes.
Path: utils/tests/test_throttles_backport.py
"""

import pytest
from django.core.cache import cache
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.test import APIRequestFactory
from rest_framework.views import APIView

from utils.throttles import (
    AuthActivationThrottle,
    AuthLoginAccountThrottle,
    AuthLoginThrottle,
    AuthRefreshThrottle,
    AuthRegisterThrottle,
    AuthResetThrottle,
    AuthSetPasswordThrottle,
    DefaultAnonThrottle,
    DefaultUserThrottle,
    ExternalAPIThrottle,
    PasswordResetThrottle,
    PublicListThrottle,
    SearchThrottle,
    UserMutationThrottle,
    WebhookThrottle,
    _IPOnlyThrottle,
    _UserOrIPThrottle,
)


class TestThrottleScopes:
    """Every universal throttle class exposes its exact documented scope."""

    @pytest.mark.parametrize(
        "throttle_class, expected_scope",
        [
            (DefaultAnonThrottle, "default_anon"),
            (DefaultUserThrottle, "default_user"),
            (AuthLoginThrottle, "auth_login"),
            (AuthLoginAccountThrottle, "auth_login_account"),
            (AuthRegisterThrottle, "auth_register"),
            (AuthResetThrottle, "auth_reset"),
            (AuthSetPasswordThrottle, "auth_set_password"),
            (AuthRefreshThrottle, "auth_refresh"),
            (AuthActivationThrottle, "auth_activation"),
            (PublicListThrottle, "public_list"),
            (SearchThrottle, "search"),
            (WebhookThrottle, "webhook"),
            (ExternalAPIThrottle, "external_api"),
            (UserMutationThrottle, "user_mutation"),
            (PasswordResetThrottle, "auth_password_reset"),
        ],
    )
    def test_throttle_class_has_expected_scope(self, throttle_class, expected_scope):
        assert throttle_class.scope == expected_scope


class TestThrottleEnabledToggle:
    """`THROTTLE_ENABLED = False` short-circuits every base class to no-op."""

    def test_ip_only_throttle_returns_none_when_disabled(self, settings):
        settings.THROTTLE_ENABLED = False

        class _ConcreteIPThrottle(_IPOnlyThrottle):
            scope = "default_anon"
            THROTTLE_RATES = {"default_anon": "5/min"}

        throttle = _ConcreteIPThrottle()
        factory = APIRequestFactory()
        request = factory.get("/", REMOTE_ADDR="10.0.0.1")

        assert throttle.get_cache_key(request, view=None) is None

    def test_user_or_ip_throttle_returns_none_when_disabled(self, settings):
        settings.THROTTLE_ENABLED = False

        class _ConcreteUserOrIPThrottle(_UserOrIPThrottle):
            scope = "default_user"
            THROTTLE_RATES = {"default_user": "5/min"}

        throttle = _ConcreteUserOrIPThrottle()
        factory = APIRequestFactory()
        django_request = factory.get("/", REMOTE_ADDR="10.0.0.1")

        class _AnonUser:
            is_authenticated = False

        django_request.user = _AnonUser()

        assert throttle.get_cache_key(django_request, view=None) is None

    def test_auth_login_account_throttle_returns_none_when_disabled(self, settings, monkeypatch):
        settings.THROTTLE_ENABLED = False
        monkeypatch.setattr(
            AuthLoginAccountThrottle, "THROTTLE_RATES", {"auth_login_account": "5/hour"}
        )
        throttle = AuthLoginAccountThrottle()
        factory = APIRequestFactory()
        request = factory.post("/", {"username": "alice"})
        request.data = {"username": "alice"}

        assert throttle.get_cache_key(request, view=None) is None


class TestUserOrIPThrottleKeying:
    """`_UserOrIPThrottle` keys by user PK for authenticated requests, IP otherwise."""

    def test_authenticated_and_anonymous_requests_produce_different_keys(self):
        class _ConcreteUserOrIPThrottle(_UserOrIPThrottle):
            scope = "default_user"
            THROTTLE_RATES = {"default_user": "5/min"}

        throttle = _ConcreteUserOrIPThrottle()
        factory = APIRequestFactory()

        anon_request = factory.get("/", REMOTE_ADDR="10.0.0.1")

        class _AnonUser:
            is_authenticated = False

        anon_request.user = _AnonUser()

        auth_request = factory.get("/", REMOTE_ADDR="10.0.0.1")

        class _AuthUser:
            is_authenticated = True
            pk = 42

        auth_request.user = _AuthUser()

        anon_key = throttle.get_cache_key(anon_request, view=None)
        auth_key = throttle.get_cache_key(auth_request, view=None)

        assert anon_key != auth_key
        assert "42" in auth_key


class TestAuthLoginAccountThrottleKeying:
    """`AuthLoginAccountThrottle` keys by a hash of the submitted credential."""

    @pytest.fixture(autouse=True)
    def _registered_rate(self, monkeypatch):
        monkeypatch.setattr(
            AuthLoginAccountThrottle, "THROTTLE_RATES", {"auth_login_account": "5/hour"}
        )

    def test_same_credential_produces_the_same_key(self):
        throttle = AuthLoginAccountThrottle()
        factory = APIRequestFactory()

        request_one = factory.post("/", {"username": "Alice@Example.com"})
        request_one.data = {"username": "Alice@Example.com"}
        request_two = factory.post("/", {"username": "alice@example.com "})
        request_two.data = {"username": "alice@example.com "}

        key_one = throttle.get_cache_key(request_one, view=None)
        key_two = throttle.get_cache_key(request_two, view=None)

        assert key_one == key_two

    def test_different_credentials_produce_different_keys(self):
        throttle = AuthLoginAccountThrottle()
        factory = APIRequestFactory()

        request_one = factory.post("/", {"username": "alice"})
        request_one.data = {"username": "alice"}
        request_two = factory.post("/", {"username": "bob"})
        request_two.data = {"username": "bob"}

        key_one = throttle.get_cache_key(request_one, view=None)
        key_two = throttle.get_cache_key(request_two, view=None)

        assert key_one != key_two

    def test_returns_none_when_no_credential_present(self):
        throttle = AuthLoginAccountThrottle()
        factory = APIRequestFactory()
        request = factory.post("/", {})
        request.data = {}

        assert throttle.get_cache_key(request, view=None) is None


class TestExternalAPIThrottleKeying:
    """`ExternalAPIThrottle` keys by the X-API-Key header, falling back to IP."""

    @pytest.fixture(autouse=True)
    def _registered_rate(self, monkeypatch):
        monkeypatch.setattr(
            ExternalAPIThrottle, "THROTTLE_RATES", {"external_api": "300/min"}
        )

    def test_returns_none_when_disabled(self, settings):
        settings.THROTTLE_ENABLED = False
        throttle = ExternalAPIThrottle()
        factory = APIRequestFactory()
        request = factory.get("/", REMOTE_ADDR="10.0.0.1", HTTP_X_API_KEY="secret-key")

        assert throttle.get_cache_key(request, view=None) is None

    def test_keys_by_api_key_header_when_present(self):
        throttle = ExternalAPIThrottle()
        factory = APIRequestFactory()
        request = factory.get("/", REMOTE_ADDR="10.0.0.1", HTTP_X_API_KEY="secret-key")

        key = throttle.get_cache_key(request, view=None)

        assert "secret-key" in key

    def test_falls_back_to_ip_when_api_key_header_is_absent(self):
        throttle = ExternalAPIThrottle()
        factory = APIRequestFactory()
        request = factory.get("/", REMOTE_ADDR="10.0.0.1")

        key = throttle.get_cache_key(request, view=None)

        assert key is not None
        assert "secret-key" not in key


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

        first = view(factory.get("/", REMOTE_ADDR="10.0.0.2"))
        second = view(factory.get("/", REMOTE_ADDR="10.0.0.2"))
        third = view(factory.get("/", REMOTE_ADDR="10.0.0.2"))

        assert first.status_code == 200
        assert second.status_code == 200
        assert third.status_code == 429
        assert third.data["error"]["code"] == "RATE_LIMIT__EXCEEDED"
