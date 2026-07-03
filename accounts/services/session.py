"""
Session management service — JWT session revocation.
Path: accounts/services/session.py
"""
from django.core.cache import cache
from django.db import transaction
from django.utils import timezone
from rest_framework_simplejwt.exceptions import TokenBackendError
from rest_framework_simplejwt.settings import api_settings as simplejwt_settings
from rest_framework_simplejwt.state import token_backend
from rest_framework_simplejwt.token_blacklist.models import (
    BlacklistedToken,
    OutstandingToken,
)

from config.logger import logger

# Cache key used to invalidate access tokens issued before a revocation
# event. CONTRACT with the WS auth middleware (subtask 020): the value
# stored here MUST be an integer unix-seconds timestamp — the middleware
# compares the integer `iat` claim from the access token against this value
# via `token_iat < revoked_after`. Do not switch this to a float
# (`time.time()`); always normalize with `int(...)`.
REVOKED_AFTER_TTL_SECONDS = 60 * 60 * 24 * 7  # 7 days — matches refresh-token lifetime


def revoke_all_sessions(user_id: int, event: str) -> int:
    """
    Blacklist all outstanding, non-expired JWT refresh tokens for a user.

    Also sets ``auth:revoked_after:{user_id}`` in the cache so the WebSocket
    auth middleware can reject access tokens whose ``iat`` predates the
    revocation — access tokens are short-lived and not stored in
    OutstandingToken, so the blacklist alone does not cover them.

    Returns the count of newly blacklisted tokens.
    """
    now = timezone.now()
    outstanding_tokens = list(
        OutstandingToken.objects.filter(user_id=user_id, expires_at__gt=now)
    )
    already_blacklisted_ids = set(
        BlacklistedToken.objects.filter(
            token__in=outstanding_tokens
        ).values_list("token_id", flat=True)
    )
    to_create = [
        BlacklistedToken(token=token)
        for token in outstanding_tokens
        if token.id not in already_blacklisted_ids
    ]

    with transaction.atomic():
        if to_create:
            BlacklistedToken.objects.bulk_create(to_create, ignore_conflicts=True)
    count = len(to_create)

    cache.set(
        f"auth:revoked_after:{user_id}",
        int(now.timestamp()),
        timeout=REVOKED_AFTER_TTL_SECONDS,
    )

    logger.bind(event=event, user_id=user_id, tokens_revoked=count).info(
        "auth.sessions_revoked"
    )
    return count


def detect_refresh_reuse(raw_token: str) -> None:
    """
    Refresh-token reuse detection (token-family revocation).

    With ROTATE_REFRESH_TOKENS + BLACKLIST_AFTER_ROTATION, a refresh token
    that still passes signature + expiry verification but whose jti is
    already blacklisted means it was rotated and is now being replayed —
    the classic signature of token theft. Revoke every session for that
    user.

    Guard: garbage, forged, or expired tokens are NOT treated as reuse —
    the payload is only trusted after a full signature + expiry
    verification.

    Implementation note: this deliberately decodes via the shared
    ``token_backend`` rather than instantiating ``RefreshToken(raw_token)``.
    ``RefreshToken.verify()`` (via ``BlacklistMixin``) checks the blacklist
    *before* signature/expiry checks and raises ``TokenError`` for exactly
    the case this function exists to detect (an already-blacklisted jti) —
    that would make the reuse branch below unreachable. Decoding with the
    backend directly performs signature + expiry verification only, without
    the blacklist short-circuit.
    """
    if not raw_token:
        return

    try:
        payload = token_backend.decode(raw_token, verify=True)
    except TokenBackendError:
        # Invalid signature / expired / malformed — not a rotation replay.
        return

    jti = payload.get(simplejwt_settings.JTI_CLAIM)
    user_id = int(payload.get(simplejwt_settings.USER_ID_CLAIM))
    if not jti or not user_id:
        return

    if BlacklistedToken.objects.filter(token__jti=jti).exists():
        logger.bind(user_id=user_id).warning("refresh.reuse_detected")
        revoke_all_sessions(user_id, event="refresh_reuse")
