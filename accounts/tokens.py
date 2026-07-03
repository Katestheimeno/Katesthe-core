"""
Custom JWT token classes that inject `kid` into the JWT header.
Path: accounts/tokens.py

MAINTENANCE NOTE: `_KidMixin.__str__` deliberately MIRRORS
``rest_framework_simplejwt.backends.TokenBackend.encode`` (payload copy +
aud/iss injection + pyjwt encode) because SimpleJWT exposes no hook for
custom JWT headers — the only addition here is ``headers={"kid": ...}``.
This file MUST be re-audited against ``TokenBackend.encode`` on every
SimpleJWT upgrade: if upstream adds claims or changes encode behavior, this
copy silently drifts. Decode/verification is untouched (SimpleJWT ignores
the kid header); the kid only serves external JWKS consumers.
"""

import jwt as pyjwt
from django.conf import settings as django_settings
from rest_framework_simplejwt.tokens import AccessToken, RefreshToken


class _KidMixin:
    """
    Overrides __str__ to include `kid` in the JWT header for JWKS-based
    verification by external consumers (e.g. Next.js Edge middleware).
    """

    def __str__(self) -> str:
        kid = django_settings.SIMPLE_JWT.get("KID")
        backend = self.token_backend

        payload = self.payload.copy()
        if backend.audience is not None:
            payload["aud"] = backend.audience
        if backend.issuer is not None:
            payload["iss"] = backend.issuer

        headers = {"kid": kid} if kid else {}

        token = pyjwt.encode(
            payload,
            backend.signing_key,
            algorithm=backend.algorithm,
            headers=headers,
        )
        return token if isinstance(token, str) else token.decode("utf-8")


class KidAccessToken(_KidMixin, AccessToken):
    pass


class KidRefreshToken(_KidMixin, RefreshToken):
    # RefreshToken.access_token is a property that instantiates
    # `self.access_token_class()` — overriding the class attribute is
    # sufficient in this simplejwt version to make rotated access tokens
    # carry the kid header too (no property override needed).
    access_token_class = KidAccessToken
