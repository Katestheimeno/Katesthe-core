"""
Tests for accounts/services/session.py — session revocation service.
Path: accounts/tests/services/test_session.py
"""
from datetime import timedelta

import pytest
from django.core.cache import cache
from rest_framework_simplejwt.token_blacklist.models import (
    BlacklistedToken,
    OutstandingToken,
)
from rest_framework_simplejwt.tokens import RefreshToken

from accounts.services.session import detect_refresh_reuse, revoke_all_sessions
from accounts.tests.factories._user import UserFactory


@pytest.fixture(autouse=True)
def _clear_cache():
    """Ensure the LocMemCache is isolated between tests."""
    cache.clear()
    yield
    cache.clear()


@pytest.mark.django_db
class TestRevokeAllSessions:
    def test_blacklists_every_outstanding_token_and_returns_the_count(self):
        user = UserFactory()
        RefreshToken.for_user(user)
        RefreshToken.for_user(user)
        RefreshToken.for_user(user)

        count = revoke_all_sessions(user.id, event="logout_all")

        assert count == 3
        outstanding_ids = set(
            OutstandingToken.objects.filter(user_id=user.id).values_list("id", flat=True)
        )
        blacklisted_ids = set(
            BlacklistedToken.objects.filter(token_id__in=outstanding_ids).values_list(
                "token_id", flat=True
            )
        )
        assert blacklisted_ids == outstanding_ids

    def test_sets_the_revoked_after_cache_key_to_a_plausible_integer_timestamp(self):
        import time

        user = UserFactory()
        RefreshToken.for_user(user)

        before = int(time.time())
        revoke_all_sessions(user.id, event="logout_all")
        after = int(time.time())

        cached_value = cache.get(f"auth:revoked_after:{user.id}")
        assert isinstance(cached_value, int)
        assert before <= cached_value <= after

    def test_calling_again_is_idempotent_and_revokes_nothing_new(self):
        user = UserFactory()
        RefreshToken.for_user(user)
        RefreshToken.for_user(user)
        revoke_all_sessions(user.id, event="logout_all")

        second_count = revoke_all_sessions(user.id, event="logout_all")

        assert second_count == 0


@pytest.mark.django_db
class TestDetectRefreshReuse:
    def test_forged_or_garbage_token_is_a_no_op(self):
        detect_refresh_reuse("garbage.not.a.token")

        assert BlacklistedToken.objects.count() == 0

    def test_expired_token_is_a_no_op(self):
        user = UserFactory()
        token = RefreshToken.for_user(user)
        token.set_exp(lifetime=timedelta(seconds=-1))
        expired_raw = str(token)

        detect_refresh_reuse(expired_raw)

        assert cache.get(f"auth:revoked_after:{user.id}") is None
        assert BlacklistedToken.objects.filter(token__user_id=user.id).count() == 0

    def test_empty_token_is_a_no_op(self):
        detect_refresh_reuse("")

        assert BlacklistedToken.objects.count() == 0

    def test_valid_but_already_blacklisted_token_triggers_full_session_revocation(self):
        user = UserFactory()
        reused_refresh = RefreshToken.for_user(user)
        sibling_refresh = RefreshToken.for_user(user)
        raw_reused = str(reused_refresh)
        outstanding = OutstandingToken.objects.get(jti=reused_refresh["jti"])
        BlacklistedToken.objects.create(token=outstanding)

        detect_refresh_reuse(raw_reused)

        assert cache.get(f"auth:revoked_after:{user.id}") is not None
        sibling_outstanding = OutstandingToken.objects.get(jti=sibling_refresh["jti"])
        assert BlacklistedToken.objects.filter(token=sibling_outstanding).exists()
