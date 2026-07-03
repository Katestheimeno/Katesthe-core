"""
Tests for privilege-change session revocation: routing fix, set_password /
set_username / account-deletion revocation, logout-all, and refresh-reuse
detection.
Path: accounts/tests/controllers/test_session_revocation.py
"""

import pytest
from django.core.cache import cache
from django.urls import resolve, reverse
from rest_framework import status
from rest_framework.test import APIClient
from rest_framework_simplejwt.token_blacklist.models import (
    BlacklistedToken,
    OutstandingToken,
)
from rest_framework_simplejwt.tokens import RefreshToken

from accounts.controllers import CustomUserViewSet
from accounts.tests.factories import UserFactory

LOGIN_PASSWORD = "testpass123"


def _make_loginable_user(**kwargs):
    """
    Create a user with a real, persisted password.

    ``UserFactory`` sets ``skip_postgeneration_save = True``, so the
    ``set_password`` post-generation hook never gets saved to the DB.
    """
    user = UserFactory(**kwargs)
    user.set_password(LOGIN_PASSWORD)
    user.save(update_fields=["password"])
    return user


def _bearer_client(user) -> APIClient:
    """API client authenticated via Bearer header (no CSRF involved)."""
    client = APIClient()
    access = str(RefreshToken.for_user(user).access_token)
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")
    return client


@pytest.mark.django_db
class TestUserRoutesResolveToCustomUserViewSet:
    """The routing fix: /auth/users/* must resolve to CustomUserViewSet."""

    def test_set_password_route_resolves_to_custom_user_viewset(self):
        match = resolve("/api/v1/auth/users/set_password/")
        assert match.func.cls is CustomUserViewSet

    def test_me_route_resolves_to_custom_user_viewset(self):
        match = resolve("/api/v1/auth/users/me/")
        assert match.func.cls is CustomUserViewSet


@pytest.mark.django_db
class TestPasswordChangeRevocation:
    """Changing the password revokes every outstanding session."""

    def test_password_change_blacklists_prior_refresh_tokens_and_sets_revoked_after(self):
        user = _make_loginable_user()
        prior_refresh = RefreshToken.for_user(user)
        client = _bearer_client(user)

        response = client.post(
            reverse("user-set-password"),
            {"current_password": LOGIN_PASSWORD, "new_password": "newpass456"},
        )

        assert response.status_code == status.HTTP_204_NO_CONTENT
        outstanding = OutstandingToken.objects.get(jti=prior_refresh["jti"])
        assert BlacklistedToken.objects.filter(token=outstanding).exists()
        assert cache.get(f"auth:revoked_after:{user.id}") is not None


@pytest.mark.django_db
class TestUsernameChangeRevocation:
    """Changing the username revokes every outstanding session."""

    def test_username_change_blacklists_prior_refresh_tokens(self):
        user = _make_loginable_user()
        prior_refresh = RefreshToken.for_user(user)
        client = _bearer_client(user)

        response = client.post(
            reverse("user-set-username"),
            {"current_password": LOGIN_PASSWORD, "new_username": "brandnewname"},
        )

        assert response.status_code == status.HTTP_204_NO_CONTENT
        outstanding = OutstandingToken.objects.get(jti=prior_refresh["jti"])
        assert BlacklistedToken.objects.filter(token=outstanding).exists()


@pytest.mark.django_db
class TestLogoutAll:
    """logout-all revokes sessions and clears both auth cookies."""

    def test_logout_all_revokes_sessions_and_clears_cookies(self):
        user = UserFactory()
        prior_refresh = RefreshToken.for_user(user)
        client = _bearer_client(user)

        response = client.post(reverse("user-logout-all"))

        assert response.status_code == status.HTTP_204_NO_CONTENT
        outstanding = OutstandingToken.objects.get(jti=prior_refresh["jti"])
        assert BlacklistedToken.objects.filter(token=outstanding).exists()

        from django.conf import settings as django_settings

        access_cookie_name = django_settings.SIMPLE_JWT["AUTH_COOKIE_ACCESS"]
        refresh_cookie_name = django_settings.SIMPLE_JWT["AUTH_COOKIE_REFRESH"]
        access_cookie = response.cookies.get(access_cookie_name)
        refresh_cookie = response.cookies.get(refresh_cookie_name)
        assert access_cookie is not None and access_cookie.value == ""
        assert refresh_cookie is not None and refresh_cookie.value == ""


@pytest.mark.django_db
class TestAccountDeletionRevocation:
    """Deleting the account revokes every outstanding session."""

    def test_account_deletion_revokes_sessions(self):
        user = _make_loginable_user()
        prior_refresh = RefreshToken.for_user(user)
        client = _bearer_client(user)

        response = client.delete(
            reverse("user-me"), {"current_password": LOGIN_PASSWORD}
        )

        assert response.status_code == status.HTTP_204_NO_CONTENT
        outstanding = OutstandingToken.objects.get(jti=prior_refresh["jti"])
        assert BlacklistedToken.objects.filter(token=outstanding).exists()


@pytest.mark.django_db
class TestRefreshReuseDetection:
    """Replaying a rotated (already-blacklisted) refresh token revokes the family."""

    def test_replaying_rotated_refresh_token_revokes_sibling_tokens(self):
        user = UserFactory()
        original_refresh = RefreshToken.for_user(user)
        sibling_refresh = RefreshToken.for_user(user)
        client = APIClient()

        # Rotate the original token once — this blacklists its jti.
        first_response = client.post(
            reverse("jwt-refresh"), {"refresh": str(original_refresh)}
        )
        assert first_response.status_code == status.HTTP_200_OK

        # Replay the now-rotated (blacklisted) original token.
        replay_response = client.post(
            reverse("jwt-refresh"), {"refresh": str(original_refresh)}
        )
        assert replay_response.status_code == status.HTTP_401_UNAUTHORIZED

        # The reuse must have revoked every other outstanding session too.
        sibling_outstanding = OutstandingToken.objects.get(
            jti=sibling_refresh["jti"]
        )
        assert BlacklistedToken.objects.filter(token=sibling_outstanding).exists()
        assert cache.get(f"auth:revoked_after:{user.id}") is not None
