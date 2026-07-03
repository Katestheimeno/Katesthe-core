"""
Tests for config/settings/restframework.py — RS256 SIMPLE_JWT configuration.
"""

import pytest
from django.conf import settings as dj

from accounts.tests.factories._user import UserFactory
from config.jwt_keys import compute_kid


class TestSimpleJwtAlgorithm:
    def test_simple_jwt_algorithm_is_rs256(self):
        assert dj.SIMPLE_JWT["ALGORITHM"] == "RS256"


class TestSimpleJwtSigningAndVerifyingKeys:
    def test_signing_key_is_a_private_pem_string(self):
        signing_key = dj.SIMPLE_JWT["SIGNING_KEY"]

        assert isinstance(signing_key, str)
        assert "BEGIN PRIVATE KEY" in signing_key

    def test_verifying_key_is_a_public_pem_string(self):
        verifying_key = dj.SIMPLE_JWT["VERIFYING_KEY"]

        assert isinstance(verifying_key, str)
        assert "BEGIN PUBLIC KEY" in verifying_key


class TestJwtKid:
    def test_jwt_kid_is_a_16_character_hex_string(self):
        kid = dj.JWT_KID

        assert len(kid) == 16
        assert all(c in "0123456789abcdef" for c in kid)

    def test_jwt_kid_matches_compute_kid_of_the_exposed_private_key(self):
        assert dj.JWT_KID == compute_kid(dj.JWT_RSA_PRIVATE_KEY_OBJ)


class TestAccessTokenRoundTrip:
    @pytest.mark.django_db
    def test_access_token_for_user_round_trips_under_rs256(self):
        from rest_framework_simplejwt.tokens import AccessToken

        user = UserFactory()

        token = AccessToken.for_user(user)
        decoded = AccessToken(str(token))

        assert str(decoded[dj.SIMPLE_JWT["USER_ID_CLAIM"]]) == str(user.id)


class TestAuthCookieAccessKey:
    def test_auth_cookie_access_is_access_token(self):
        assert dj.SIMPLE_JWT["AUTH_COOKIE_ACCESS"] == "access_token"
