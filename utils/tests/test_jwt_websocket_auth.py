"""
Tests for utils/middleware/jwt_websocket_auth.py — JWT WebSocket auth middleware.
Path: utils/tests/test_jwt_websocket_auth.py
"""
from datetime import timedelta

import pytest
from asgiref.sync import async_to_sync
from django.core.cache import cache
from rest_framework_simplejwt.tokens import AccessToken

from accounts.tests.factories._user import InactiveUserFactory, UserFactory
from utils.middleware.jwt_websocket_auth import (
    JWTAuthMiddleware,
    extract_token_from_scope,
    get_accepted_subprotocol,
    get_user_from_token,
    jwt_auth_failed,
)


@pytest.fixture(autouse=True)
def _clear_cache():
    """Ensure the LocMemCache is isolated between tests."""
    cache.clear()
    yield
    cache.clear()


class TestExtractTokenFromScope:
    def test_finds_token_in_subprotocols_and_flags_the_scope(self):
        scope = {"subprotocols": ["access_token", "the.jwt.token"]}

        token = extract_token_from_scope(scope)

        assert token == "the.jwt.token"
        assert scope["_auth_via_subprotocol"] is True

    def test_subprotocol_marker_with_no_following_value_returns_none(self):
        scope = {"subprotocols": ["access_token"]}

        assert extract_token_from_scope(scope) is None

    def test_finds_token_in_cookie_header_when_no_subprotocol_offered(self):
        scope = {
            "subprotocols": [],
            "headers": [(b"cookie", b"other=1; access_token=cookie.jwt.token; more=2")],
        }

        token = extract_token_from_scope(scope)

        assert token == "cookie.jwt.token"
        assert "_auth_via_subprotocol" not in scope

    def test_subprotocol_takes_priority_over_cookie(self):
        scope = {
            "subprotocols": ["access_token", "subprotocol.jwt.token"],
            "headers": [(b"cookie", b"access_token=cookie.jwt.token")],
        }

        assert extract_token_from_scope(scope) == "subprotocol.jwt.token"

    def test_returns_none_when_no_token_present_anywhere(self):
        scope = {"subprotocols": [], "headers": []}

        assert extract_token_from_scope(scope) is None


class TestGetAcceptedSubprotocol:
    def test_returns_access_token_when_offered_in_subprotocols(self):
        scope = {"subprotocols": ["access_token", "some.jwt"]}

        assert get_accepted_subprotocol(scope) == "access_token"

    def test_returns_access_token_when_auth_via_subprotocol_flag_set(self):
        scope = {"subprotocols": [], "_auth_via_subprotocol": True}

        assert get_accepted_subprotocol(scope) == "access_token"

    def test_returns_none_when_access_token_not_offered(self):
        scope = {"subprotocols": ["graphql-ws"]}

        assert get_accepted_subprotocol(scope) is None

    def test_returns_none_when_no_subprotocols_present(self):
        scope = {}

        assert get_accepted_subprotocol(scope) is None


class TestJwtAuthFailed:
    def test_true_when_scope_flag_set(self):
        assert jwt_auth_failed({"jwt_auth_failed": True}) is True

    def test_false_when_scope_flag_unset(self):
        assert jwt_auth_failed({}) is False

    def test_false_when_scope_flag_explicitly_false(self):
        assert jwt_auth_failed({"jwt_auth_failed": False}) is False


@pytest.mark.django_db
class TestGetUserFromToken:
    def test_valid_token_returns_the_matching_active_user(self):
        user = UserFactory()
        token = str(AccessToken.for_user(user))

        result = async_to_sync(get_user_from_token)(token)

        assert result == user

    def test_garbage_token_returns_none(self):
        result = async_to_sync(get_user_from_token)("garbage.not.a.token")

        assert result is None

    def test_expired_token_returns_none(self):
        user = UserFactory()
        token = AccessToken.for_user(user)
        token.set_exp(lifetime=timedelta(seconds=-1))

        result = async_to_sync(get_user_from_token)(str(token))

        assert result is None

    def test_token_with_iat_before_revoked_after_timestamp_returns_none(self):
        user = UserFactory()
        token = AccessToken.for_user(user)
        iat = token["iat"]
        cache.set(f"auth:revoked_after:{user.id}", iat + 100, timeout=60)

        result = async_to_sync(get_user_from_token)(str(token))

        assert result is None

    def test_token_with_iat_after_revoked_after_timestamp_still_authenticates(self):
        user = UserFactory()
        cache.set(f"auth:revoked_after:{user.id}", 1, timeout=60)
        token = AccessToken.for_user(user)

        result = async_to_sync(get_user_from_token)(str(token))

        assert result == user

    def test_inactive_user_returns_none(self):
        user = InactiveUserFactory()
        token = str(AccessToken.for_user(user))

        result = async_to_sync(get_user_from_token)(token)

        assert result is None

    def test_revocation_cache_unavailable_fails_open_and_still_authenticates(
        self, monkeypatch
    ):
        user = UserFactory()
        token = str(AccessToken.for_user(user))

        def _raise(*args, **kwargs):
            raise ConnectionError("Redis unreachable")

        monkeypatch.setattr(cache, "get", _raise)

        result = async_to_sync(get_user_from_token)(token)

        assert result == user


@pytest.mark.django_db
class TestJWTAuthMiddleware:
    async def _inner(self, scope, receive, send):
        self.captured_scope = scope
        return "inner-called"

    def _run(self, scope):
        middleware = JWTAuthMiddleware(self._inner)
        async_to_sync(middleware)(scope, None, None)
        return self.captured_scope

    def test_non_websocket_scope_passes_through_untouched(self):
        scope = {"type": "http"}

        result_scope = self._run(scope)

        assert "jwt_auth_failed" not in result_scope
        assert "user" not in result_scope

    def test_valid_token_sets_user_and_clears_auth_failed_flag(self):
        user = UserFactory()
        token = str(AccessToken.for_user(user))
        scope = {"type": "websocket", "subprotocols": ["access_token", token]}

        result_scope = self._run(scope)

        assert result_scope["user"] == user
        assert result_scope["jwt_auth_failed"] is False

    def test_invalid_token_sets_auth_failed_flag_and_leaves_user_unset(self):
        scope = {
            "type": "websocket",
            "subprotocols": ["access_token", "garbage.not.a.token"],
        }

        result_scope = self._run(scope)

        assert result_scope["jwt_auth_failed"] is True
        assert "user" not in result_scope

    def test_no_token_leaves_scope_untouched_for_session_fallback(self):
        scope = {"type": "websocket", "subprotocols": [], "headers": []}

        result_scope = self._run(scope)

        assert "jwt_auth_failed" not in result_scope
        assert "user" not in result_scope
