"""
Tests for cookie-based JWT authentication (login/refresh/logout cookie
transport + CSRF enforcement).
Path: accounts/tests/controllers/test_cookie_auth.py
"""

import time

import pytest
from django.conf import settings as django_settings
from django.core.cache import cache
from django.middleware.csrf import get_token
from django.test import RequestFactory
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient
from rest_framework_simplejwt.token_blacklist.models import (
    BlacklistedToken,
    OutstandingToken,
)
from rest_framework_simplejwt.tokens import RefreshToken

from accounts.tests.factories import UserFactory
from accounts.tokens import KidRefreshToken

ACCESS_COOKIE = django_settings.SIMPLE_JWT["AUTH_COOKIE_ACCESS"]
REFRESH_COOKIE = django_settings.SIMPLE_JWT["AUTH_COOKIE_REFRESH"]
LOGIN_PASSWORD = "testpass123"


def _make_loginable_user(**kwargs):
    """
    Create a user with a real, persisted password.

    ``UserFactory`` sets ``skip_postgeneration_save = True``, so the
    ``set_password`` post-generation hook never gets saved to the DB. Any
    test that actually authenticates by username/password must redo the
    save explicitly.
    """
    user = UserFactory(**kwargs)
    user.set_password(LOGIN_PASSWORD)
    user.save(update_fields=["password"])
    return user


def _csrf_pair():
    """Generate a matching (cookie_value, header_token) CSRF pair."""
    request = RequestFactory().get("/")
    header_token = get_token(request)
    cookie_value = request.META["CSRF_COOKIE"]
    return cookie_value, header_token


def _client(enforce_csrf: bool = False) -> APIClient:
    """Local cookie/CSRF-aware test client helper (kept in this file only)."""
    return APIClient(enforce_csrf_checks=enforce_csrf)


@pytest.mark.django_db
class TestLoginCookieTransport:
    """Login sets HttpOnly cookies and honors the X-Token-Delivery opt-out."""

    def test_login_without_token_delivery_header_sets_httponly_cookies_and_omits_body_tokens(self):
        user = _make_loginable_user()
        url = reverse("jwt-create")

        response = _client().post(
            url, {"username": user.username, "password": LOGIN_PASSWORD}
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.data["success"] is True
        assert "access" not in response.data["data"]
        assert "refresh" not in response.data["data"]

        access_cookie = response.cookies[ACCESS_COOKIE]
        refresh_cookie = response.cookies[REFRESH_COOKIE]
        assert access_cookie.value
        assert access_cookie["httponly"] is True
        assert refresh_cookie.value
        assert refresh_cookie["httponly"] is True

    def test_login_with_bearer_token_delivery_header_returns_body_tokens(self):
        user = _make_loginable_user()
        url = reverse("jwt-create")

        response = _client().post(
            url,
            {"username": user.username, "password": LOGIN_PASSWORD},
            HTTP_X_TOKEN_DELIVERY="bearer",
        )

        assert response.status_code == status.HTTP_200_OK
        assert "access" in response.data["data"]
        assert "refresh" in response.data["data"]


@pytest.mark.django_db
class TestCookieAuthenticationSafeMethods:
    """A safe (GET) request authenticates via the access cookie, no CSRF."""

    def test_cookie_authenticated_safe_get_succeeds_without_csrf(self, user):
        client = _client(enforce_csrf=True)
        access = str(RefreshToken.for_user(user).access_token)
        client.cookies[ACCESS_COOKIE] = access

        response = client.get(reverse("user-me"))

        assert response.status_code == status.HTTP_200_OK
        assert response.data["data"]["id"] == user.id


@pytest.mark.django_db
class TestCookieAuthenticationCsrfEnforcement:
    """Cookie-transported mutations require CSRF; header auth never does."""

    def test_cookie_authenticated_mutation_without_csrf_token_is_denied(self, user):
        client = _client(enforce_csrf=True)
        access = str(RefreshToken.for_user(user).access_token)
        client.cookies[ACCESS_COOKIE] = access

        response = client.post(reverse("jwt-destroy"), {"refresh": "irrelevant"})

        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert response.data["success"] is False
        assert response.data["error"]["code"] == "PERMISSION__DENIED"

    def test_cookie_authenticated_mutation_with_valid_csrf_token_is_allowed(self, user):
        client = _client(enforce_csrf=True)
        access = str(RefreshToken.for_user(user).access_token)
        refresh = RefreshToken.for_user(user)
        client.cookies[ACCESS_COOKIE] = access
        cookie_value, header_token = _csrf_pair()
        client.cookies["csrftoken"] = cookie_value

        response = client.post(
            reverse("jwt-destroy"),
            {"refresh": str(refresh)},
            HTTP_X_CSRFTOKEN=header_token,
        )

        assert response.status_code != status.HTTP_403_FORBIDDEN
        assert response.status_code == status.HTTP_204_NO_CONTENT

    def test_bearer_header_mutation_succeeds_without_csrf(self, user):
        client = _client(enforce_csrf=True)
        access = str(RefreshToken.for_user(user).access_token)
        refresh = RefreshToken.for_user(user)
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")

        response = client.post(reverse("jwt-destroy"), {"refresh": str(refresh)})

        assert response.status_code != status.HTTP_403_FORBIDDEN
        assert response.status_code == status.HTTP_204_NO_CONTENT


@pytest.mark.django_db
class TestCookieAuthenticationGracefulDowngrade:
    """A bad access cookie must not block a valid Authorization header."""

    def test_malformed_access_cookie_falls_back_to_bearer_header_auth(self, user):
        client = _client(enforce_csrf=False)
        client.cookies[ACCESS_COOKIE] = "not-a-valid-jwt"
        access = str(RefreshToken.for_user(user).access_token)
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")

        response = client.get(reverse("user-me"))

        assert response.status_code == status.HTTP_200_OK
        assert response.data["data"]["id"] == user.id


@pytest.mark.django_db
class TestLogout:
    """Logout blacklists the refresh token and clears both auth cookies."""

    def test_logout_blacklists_refresh_token(self, user):
        client = _client(enforce_csrf=True)
        access = str(RefreshToken.for_user(user).access_token)
        refresh = RefreshToken.for_user(user)
        client.cookies[ACCESS_COOKIE] = access
        cookie_value, header_token = _csrf_pair()
        client.cookies["csrftoken"] = cookie_value

        response = client.post(
            reverse("jwt-destroy"),
            {"refresh": str(refresh)},
            HTTP_X_CSRFTOKEN=header_token,
        )

        assert response.status_code == status.HTTP_204_NO_CONTENT
        outstanding = OutstandingToken.objects.get(jti=refresh["jti"])
        assert BlacklistedToken.objects.filter(token=outstanding).exists()

    def test_logout_clears_auth_cookies(self, user):
        client = _client(enforce_csrf=True)
        access = str(RefreshToken.for_user(user).access_token)
        refresh = RefreshToken.for_user(user)
        client.cookies[ACCESS_COOKIE] = access
        cookie_value, header_token = _csrf_pair()
        client.cookies["csrftoken"] = cookie_value

        response = client.post(
            reverse("jwt-destroy"),
            {"refresh": str(refresh)},
            HTTP_X_CSRFTOKEN=header_token,
        )

        assert response.status_code == status.HTTP_204_NO_CONTENT
        access_cookie = response.cookies.get(ACCESS_COOKIE)
        refresh_cookie = response.cookies.get(REFRESH_COOKIE)
        assert access_cookie is not None and access_cookie.value == ""
        assert refresh_cookie is not None and refresh_cookie.value == ""


@pytest.mark.django_db
class TestRefreshCookieTransport:
    """Refresh reads the refresh token from the cookie and enforces CSRF."""

    def test_refresh_reads_refresh_token_from_cookie_and_sets_fresh_access_cookie(self, user):
        client = _client(enforce_csrf=True)
        refresh = KidRefreshToken.for_user(user)
        client.cookies[REFRESH_COOKIE] = str(refresh)
        cookie_value, header_token = _csrf_pair()
        client.cookies["csrftoken"] = cookie_value

        response = client.post(
            reverse("jwt-refresh"), {}, HTTP_X_CSRFTOKEN=header_token
        )

        assert response.status_code == status.HTTP_200_OK
        access_cookie = response.cookies.get(ACCESS_COOKIE)
        assert access_cookie is not None and access_cookie.value
        assert access_cookie["httponly"] is True

    def test_cookie_transport_refresh_without_csrf_token_is_denied(self, user):
        client = _client(enforce_csrf=True)
        refresh = KidRefreshToken.for_user(user)
        client.cookies[REFRESH_COOKIE] = str(refresh)

        response = client.post(reverse("jwt-refresh"), {})

        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert response.data["success"] is False
        assert response.data["error"]["code"] == "PERMISSION__DENIED"

    def test_cookie_transport_refresh_with_valid_csrf_token_is_allowed(self, user):
        client = _client(enforce_csrf=True)
        refresh = KidRefreshToken.for_user(user)
        client.cookies[REFRESH_COOKIE] = str(refresh)
        cookie_value, header_token = _csrf_pair()
        client.cookies["csrftoken"] = cookie_value

        response = client.post(
            reverse("jwt-refresh"), {}, HTTP_X_CSRFTOKEN=header_token
        )

        assert response.status_code == status.HTTP_200_OK


@pytest.mark.django_db
class TestHttpSessionRevocationEnforcement:
    """
    A previously issued access token must be rejected on the HTTP path once
    ``auth:revoked_after:{user_id}`` is set — both via the Bearer-header
    fallback and the cookie path (finding #1: this was previously only
    enforced on the WebSocket side).

    The ``revoked_after`` timestamp is set directly on the cache rather than
    driven through the real logout-all/password-change endpoints, to avoid
    same-wall-clock-second flakiness against the token's ``iat`` (both use
    integer-second resolution).
    """

    def test_bearer_header_access_token_rejected_after_revocation(self, user):
        access = str(RefreshToken.for_user(user).access_token)
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")

        cache.set(f"auth:revoked_after:{user.id}", int(time.time()) + 1)

        response = client.get(reverse("user-me"))

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_cookie_access_token_rejected_after_revocation(self, user):
        access = str(RefreshToken.for_user(user).access_token)
        client = _client(enforce_csrf=False)
        client.cookies[ACCESS_COOKIE] = access

        cache.set(f"auth:revoked_after:{user.id}", int(time.time()) + 1)

        response = client.get(reverse("user-me"))

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_access_token_still_valid_when_no_revocation_is_on_record(self, user):
        """Cache miss (no revocation ever recorded) must not reject — same
        fail-open-on-miss contract as the WebSocket middleware."""
        access = str(RefreshToken.for_user(user).access_token)
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")

        response = client.get(reverse("user-me"))

        assert response.status_code == status.HTTP_200_OK

    def test_access_token_issued_after_revocation_still_works(self, user):
        """A token issued *after* the revocation timestamp is not caught by
        it — only tokens whose iat predates the revocation are rejected."""
        cache.set(f"auth:revoked_after:{user.id}", int(time.time()) - 3600)
        access = str(RefreshToken.for_user(user).access_token)
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")

        response = client.get(reverse("user-me"))

        assert response.status_code == status.HTTP_200_OK
