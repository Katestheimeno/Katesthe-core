"""
Tests for config/spectacular_auth.py — CookieJWTAuthenticationExtension.
"""

import pytest
from drf_spectacular.generators import SchemaGenerator

from accounts.authentication import CookieJWTAuthentication
from config.spectacular_auth import CookieJWTAuthenticationExtension


class TestCookieJWTAuthenticationExtensionDefinition:
    def test_target_class_points_to_cookie_jwt_authentication(self):
        # drf-spectacular's OpenApiGeneratorExtension._load_class() resolves
        # target_class from a dotted-path string to the actual class object
        # in place, process-wide, the first time schema generation runs.
        # Depending on test execution order, target_class may already be
        # resolved here — accept either form.
        target = CookieJWTAuthenticationExtension.target_class

        if isinstance(target, str):
            assert target == "accounts.authentication.CookieJWTAuthentication"
        else:
            assert target is CookieJWTAuthentication

    def test_name_is_cookie_jwt_auth(self):
        assert CookieJWTAuthenticationExtension.name == "CookieJWTAuth"

    def test_get_security_definition_returns_bearer_jwt_scheme(self):
        extension = CookieJWTAuthenticationExtension.__new__(
            CookieJWTAuthenticationExtension
        )

        definition = extension.get_security_definition(None)

        assert definition == {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT",
            "description": (
                "JWT via HttpOnly cookie (primary) or Authorization header (fallback). "
                "Cookie: access_token."
            ),
        }


@pytest.mark.django_db
class TestSchemaGeneration:
    def test_generated_schema_includes_cookie_jwt_auth_security_scheme(self):
        generator = SchemaGenerator()

        schema = generator.get_schema(request=None, public=True)

        security_schemes = schema["components"]["securitySchemes"]
        assert "CookieJWTAuth" in security_schemes
        assert security_schemes["CookieJWTAuth"] == {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT",
            "description": (
                "JWT via HttpOnly cookie (primary) or Authorization header (fallback). "
                "Cookie: access_token."
            ),
        }
