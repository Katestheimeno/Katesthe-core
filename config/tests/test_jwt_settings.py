"""
Tests for the JWT-RS256 / auth-cookie / throttle-toggle fields on
`config.settings.config.MainSettings`, including the `SameSite=None` guard.

`MainSettings` is constructed directly with explicit kwargs so the tests are
hermetic and do not depend on `.env` file contents. Required fields with no
default (`SECRET_KEY`, `JWT_SECRET_KEY`) are always supplied.
"""

import pytest
from pydantic import ValidationError

from config.settings.config import MainSettings

REQUIRED_KWARGS = {
    "SECRET_KEY": "test-secret-key",
    "JWT_SECRET_KEY": "test-jwt-secret-key",
}


class TestJwtCookieThrottleDefaults:
    def test_default_auth_cookie_samesite_is_lax(self):
        settings = MainSettings(**REQUIRED_KWARGS)

        assert settings.AUTH_COOKIE_SAMESITE == "Lax"

    def test_default_throttle_enabled_is_true(self):
        settings = MainSettings(**REQUIRED_KWARGS)

        assert settings.THROTTLE_ENABLED is True

    def test_default_jwt_rsa_private_key_is_empty_string(self):
        settings = MainSettings(**REQUIRED_KWARGS)

        assert settings.JWT_RSA_PRIVATE_KEY == ""


class TestAuthCookieSamesiteValidator:
    def test_samesite_none_without_secure_raises_validation_error(self):
        with pytest.raises(ValidationError):
            MainSettings(
                **REQUIRED_KWARGS,
                AUTH_COOKIE_SAMESITE="None",
                AUTH_COOKIE_SECURE=False,
            )

    def test_samesite_none_with_secure_is_accepted(self):
        settings = MainSettings(
            **REQUIRED_KWARGS,
            AUTH_COOKIE_SAMESITE="None",
            AUTH_COOKIE_SECURE=True,
        )

        assert settings.AUTH_COOKIE_SAMESITE == "None"
        assert settings.AUTH_COOKIE_SECURE is True
