"""
OpenApiAuthenticationExtension for CookieJWTAuthentication.

Registers the project's cookie-based JWT auth class with drf-spectacular
so the generated OpenAPI schema includes the correct security scheme.
Path: config/spectacular_auth.py
"""
from drf_spectacular.extensions import OpenApiAuthenticationExtension


class CookieJWTAuthenticationExtension(OpenApiAuthenticationExtension):
    target_class = "accounts.authentication.CookieJWTAuthentication"
    name = "CookieJWTAuth"

    def get_security_definition(self, auto_schema):
        return {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT",
            "description": (
                "JWT via HttpOnly cookie (primary) or Authorization header (fallback). "
                "Cookie: access_token."
            ),
        }
