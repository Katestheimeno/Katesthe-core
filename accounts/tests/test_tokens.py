"""
Tests for accounts/tokens.py — KidAccessToken / KidRefreshToken.
Path: accounts/tests/test_tokens.py
"""

import jwt as pyjwt
import pytest
from django.conf import settings

from accounts.tests.factories._user import UserFactory
from accounts.tokens import KidAccessToken, KidRefreshToken


@pytest.mark.django_db
class TestKidAccessToken:
    def test_str_encodes_a_jwt_header_with_the_configured_kid(self):
        user = UserFactory()

        token = str(KidAccessToken.for_user(user))
        header = pyjwt.get_unverified_header(token)

        assert header["kid"] == settings.SIMPLE_JWT["KID"]

    def test_signature_validates_under_rs256_with_the_verifying_key(self):
        user = UserFactory()

        token = str(KidAccessToken.for_user(user))
        decoded = pyjwt.decode(
            token,
            key=settings.SIMPLE_JWT["VERIFYING_KEY"],
            algorithms=["RS256"],
            audience=settings.SIMPLE_JWT["AUDIENCE"],
            issuer=settings.SIMPLE_JWT["ISSUER"],
        )

        assert str(decoded[settings.SIMPLE_JWT["USER_ID_CLAIM"]]) == str(user.id)


@pytest.mark.django_db
class TestKidRefreshToken:
    def test_access_token_property_returns_a_kid_access_token_instance(self):
        user = UserFactory()

        refresh = KidRefreshToken.for_user(user)

        assert isinstance(refresh.access_token, KidAccessToken)

    def test_derived_access_token_header_carries_the_configured_kid(self):
        user = UserFactory()

        refresh = KidRefreshToken.for_user(user)
        header = pyjwt.get_unverified_header(str(refresh.access_token))

        assert header["kid"] == settings.SIMPLE_JWT["KID"]


@pytest.mark.django_db
class TestKidMixinParityWithTokenBackendEncode:
    """
    Regression guard for the maintenance note in accounts/tokens.py:
    ``_KidMixin.__str__`` reimplements ``TokenBackend.encode`` (payload copy
    + aud/iss injection) because SimpleJWT exposes no hook for custom
    headers. A SimpleJWT upgrade that changes ``encode()``'s claim handling
    should fail this test before the drift reaches production (finding #6).
    """

    def test_kid_access_token_payload_matches_token_backend_encode(self):
        user = UserFactory()
        token = KidAccessToken.for_user(user)

        ours = pyjwt.decode(
            str(token),
            key=settings.SIMPLE_JWT["VERIFYING_KEY"],
            algorithms=["RS256"],
            audience=settings.SIMPLE_JWT["AUDIENCE"],
            issuer=settings.SIMPLE_JWT["ISSUER"],
        )
        upstream_encoded = token.token_backend.encode(token.payload)
        upstream = pyjwt.decode(
            upstream_encoded,
            key=settings.SIMPLE_JWT["VERIFYING_KEY"],
            algorithms=["RS256"],
            audience=settings.SIMPLE_JWT["AUDIENCE"],
            issuer=settings.SIMPLE_JWT["ISSUER"],
        )

        assert ours == upstream
