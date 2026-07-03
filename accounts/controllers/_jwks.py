"""
JWKS (JSON Web Key Set) endpoint for public key distribution.
Path: accounts/controllers/_jwks.py

Serves the RSA public signing key so that external consumers (e.g. Next.js
Edge middleware) can verify JWT signatures without the private key.
"""

from django.conf import settings
from django.http import JsonResponse
from rest_framework.permissions import AllowAny
from rest_framework.views import APIView

from config.jwt_keys import build_jwks
from utils.throttles import PublicListThrottle

__all__ = ["JWKSView"]


class JWKSView(APIView):
    """
    Public JWKS endpoint (RFC 7517).

    Resolved absolute URL: ``/api/v1/.well-known/jwks.json``.

    Returns the current RSA public key(s) in standard JWKS format. During a
    key-rotation window (``JWT_PREVIOUS_PUBLIC_KEY_OBJ`` set), the previous
    public key is published too, each entry with its own ``kid``.

    The response is cache-friendly — consumers should cache based on the
    ``Cache-Control`` header and refresh only when a ``kid`` mismatch occurs.

    Response shape (no private material — only ``n`` and ``e``)::

        {"keys": [{"kty": "RSA", "kid": "...", "use": "sig",
                   "alg": "RS256", "n": "...", "e": "..."}]}
    """
    permission_classes = [AllowAny]
    authentication_classes = []
    throttle_classes = [PublicListThrottle]
    # Deliberately excluded from OpenAPI schema generation — the JWKS
    # contract is the RFC 7517 standard itself, documented in this
    # docstring, not in the OpenAPI schema.
    schema = None

    def get(self, request):
        jwks = build_jwks(
            settings.JWT_RSA_PRIVATE_KEY_OBJ,
            settings.JWT_KID,
            algorithm=settings.SIMPLE_JWT["ALGORITHM"],
            previous_public_key=getattr(settings, "JWT_PREVIOUS_PUBLIC_KEY_OBJ", None),
            previous_kid=getattr(settings, "JWT_PREVIOUS_KID", None),
        )

        response = JsonResponse(jwks)
        response["Cache-Control"] = "public, max-age=3600"
        return response
