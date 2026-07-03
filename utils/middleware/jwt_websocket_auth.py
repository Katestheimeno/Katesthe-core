"""
JWT WebSocket Authentication Middleware for Django Channels.
Path: utils/middleware/jwt_websocket_auth.py

This middleware authenticates WebSocket connections using JWT tokens
from subprotocols or cookies.

Supports authentication via:
1. Sec-WebSocket-Protocol header: new WebSocket(url, ["access_token", JWT])
2. Cookie: 'access_token' cookie (if set by HTTP requests)
3. Falls back to session authentication via AuthMiddlewareStack

Session revocation (defense-in-depth):
    The accounts app writes ``auth:revoked_after:{user_id}`` (a unix
    timestamp) to the cache on logout-all / password change / account
    deletion. Tokens whose ``iat`` claim predates that timestamp are
    rejected. A cache miss (or unreachable Redis) fails open — signature
    and expiry validation remain the primary gate; this check only
    shortens the window during which a retained access token stays usable.
    The cache key string is the only contract shared with accounts — do
    NOT import from accounts here.

Auth-failure signaling:
    When a token WAS presented but failed validation, the middleware sets
    ``scope["jwt_auth_failed"] = True``. Consumers should check
    ``jwt_auth_failed(scope)`` in ``connect()`` and close with code 4401
    so clients know to refresh their token and reconnect (vs. a plain
    anonymous connection, which keeps the existing generic close code).
"""

import hashlib

from asgiref.sync import sync_to_async
from channels.db import database_sync_to_async
from channels.middleware import BaseMiddleware
from django.contrib.auth import get_user_model
from django.core.cache import cache
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
from rest_framework_simplejwt.tokens import AccessToken

from config.logger import logger

User = get_user_model()

# Cache authenticated users to reduce DB queries on every WS frame dispatch.
# Tradeoff: shorter TTL = more DB hits per long-lived WS connection;
# longer TTL = deactivated/banned users stay connected longer before eviction.
# The ``auth:revoked_after`` session-revocation cache key (see
# REVOKED_AFTER_CACHE_KEY_TEMPLATE below) mitigates the staleness risk for
# *new* connections after a logout-all / password change, but does NOT
# invalidate already-cached entries for in-flight connections. 300 s is a
# reasonable middle ground for an admin panel / game lobby.
USER_CACHE_TTL = 300

# Session-revocation cache key — CONTRACT with the accounts app
# (accounts' revoke_all_sessions() writes it; this middleware only reads it).
REVOKED_AFTER_CACHE_KEY_TEMPLATE = "auth:revoked_after:{user_id}"


@database_sync_to_async
def get_user_by_id(user_id):
    """Fetch user from database by ID."""
    try:
        return User.objects.get(id=user_id)
    except User.DoesNotExist:
        return None


def _validate_token_sync(token_string):
    """
    Validate a JWT token string synchronously.

    Returns:
        AccessToken instance if valid, None otherwise.
    Raises:
        TokenError, InvalidToken on validation failure.
    """
    return AccessToken(token_string)


async def _safe_cache_get(key):
    """Cache get that returns None on failure instead of crashing."""
    try:
        return await sync_to_async(cache.get)(key)
    except Exception as e:
        logger.warning("Cache get failed (Redis down?): %s", e)
        return None


async def _safe_cache_set(key, value, ttl):
    """Cache set that silently degrades on failure."""
    try:
        await sync_to_async(cache.set)(key, value, ttl)
    except Exception as e:
        logger.warning("Cache set failed (Redis down?): %s", e)


async def _safe_cache_delete(key):
    """Cache delete that silently degrades on failure."""
    try:
        await sync_to_async(cache.delete)(key)
    except Exception as e:
        logger.warning("Cache delete failed (Redis down?): %s", e)


async def _is_token_revoked(access_token, user_id):
    """
    Check the session-revocation cache (contract with the accounts app).

    Returns True only when a revocation timestamp exists for the user AND
    the token's ``iat`` claim predates it. A cache miss — including Redis
    being down — fails open (returns False): this is defense-in-depth on
    top of signature/expiry validation, not the primary gate.
    """
    revoked_after = await _safe_cache_get(
        REVOKED_AFTER_CACHE_KEY_TEMPLATE.format(user_id=user_id)
    )
    if revoked_after is None:
        # No revocation recorded (or cache unreachable) — allow.
        logger.bind(user_id=user_id).debug("ws.auth.revocation_cache_miss")
        return False

    iat = access_token.get("iat")
    if iat is None:
        # A revocation exists but the token carries no iat claim — we cannot
        # prove it was issued after the revocation, so reject it.
        logger.bind(user_id=user_id).warning("ws.auth.token_missing_iat")
        return True

    try:
        revoked = int(iat) < int(revoked_after)
    except (TypeError, ValueError):
        # Malformed cache value — treat like a cache miss (fail open),
        # but make the corruption visible.
        logger.bind(user_id=user_id).warning("ws.auth.revocation_value_malformed")
        return False

    if revoked:
        logger.bind(user_id=user_id).warning("ws.auth.token_revoked")
        return True

    return False


async def get_user_from_token(token_string):
    """
    Get user from JWT token with caching.

    Validation order:
    1. Signature / expiry via SimpleJWT ``AccessToken``.
    2. Session-revocation check: tokens whose ``iat`` predates the cached
       ``auth:revoked_after:{user_id}`` timestamp are rejected (cache miss
       fails open — see ``_is_token_revoked``).
    3. User lookup (cached for ``USER_CACHE_TTL``), requiring ``is_active``.

    ``cache.get``/``cache.set`` and ``AccessToken()`` are synchronous and
    are therefore run via ``sync_to_async`` to avoid blocking the event loop.

    Cache operations degrade gracefully — if Redis is unreachable, auth
    falls back to a direct DB lookup so WebSocket connections still work.

    Args:
        token_string: JWT access token string

    Returns:
        User instance if token is valid, None otherwise
    """
    # --- Always validate the token first (signature / expiry check) ---
    try:
        access_token = await sync_to_async(_validate_token_sync)(token_string)
    except (TokenError, InvalidToken) as e:
        logger.warning("JWT token validation failed: %s", type(e).__name__)
        token_hash = hashlib.sha256(token_string.encode()).hexdigest()
        cache_key = f"ws_jwt_user:{token_hash}"
        await _safe_cache_delete(cache_key)
        return None
    except Exception as e:
        logger.error("Unexpected error validating JWT token: %s", type(e).__name__)
        return None

    user_id = access_token.get("user_id")
    if not user_id:
        logger.warning("JWT token missing user_id claim")
        return None

    # --- Session-revocation check (contract with accounts; fails open) ---
    if await _is_token_revoked(access_token, user_id):
        token_hash = hashlib.sha256(token_string.encode()).hexdigest()
        await _safe_cache_delete(f"ws_jwt_user:{token_hash}")
        return None

    # --- Check cache (using sha256 - consistent across workers) ---
    token_hash = hashlib.sha256(token_string.encode()).hexdigest()
    cache_key = f"ws_jwt_user:{token_hash}"
    cached_user_id = await _safe_cache_get(cache_key)

    if cached_user_id:
        user = await get_user_by_id(cached_user_id)
        if user and user.is_active:
            logger.debug(f"Retrieved cached user {cached_user_id}")
            return user
        await _safe_cache_delete(cache_key)

    # --- Fresh DB lookup ---
    user = await get_user_by_id(user_id)

    if user:
        if not user.is_active:
            logger.warning(f"User {user_id} is inactive, denying WebSocket auth")
            return None
        await _safe_cache_set(cache_key, user_id, USER_CACHE_TTL)
        logger.debug(f"Successfully authenticated user {user_id} via JWT token")
        return user
    else:
        logger.warning(f"User {user_id} not found for valid token")

    return None


def extract_token_from_scope(scope):
    """
    Extract JWT token from WebSocket scope.

    Priority: Sec-WebSocket-Protocol header > cookie.

    When the token is found in subprotocols, ``scope["_auth_via_subprotocol"]``
    is set so that consumers can echo the accepted subprotocol on accept().

    Args:
        scope: ASGI WebSocket scope dictionary

    Returns:
        Token string if found, None otherwise
    """
    # 1. Sec-WebSocket-Protocol header (preferred — keeps token out of URL/logs)
    subprotocols = scope.get("subprotocols", [])
    if "access_token" in subprotocols:
        idx = subprotocols.index("access_token")
        if idx + 1 < len(subprotocols):
            scope["_auth_via_subprotocol"] = True
            logger.debug("JWT token found in Sec-WebSocket-Protocol header")
            return subprotocols[idx + 1]

    # 2. Cookie fallback
    headers = dict(scope.get("headers", []))
    cookie_header = headers.get(b"cookie")

    if cookie_header:
        cookie_string = cookie_header.decode()
        for cookie in cookie_string.split(";"):
            cookie = cookie.strip()
            if cookie.startswith("access_token="):
                token = cookie.split("=", 1)[1]
                logger.debug("JWT token found in cookies")
                return token

    return None


def get_accepted_subprotocol(scope):
    """
    Return the subprotocol to echo on accept(), or None.

    RFC 6455 requires the server to select one of the client-offered
    subprotocols or none — and browsers abort the handshake when they
    offered a protocol and the server selected none. The ``access_token``
    marker is therefore echoed whenever the client offered it, regardless
    of authentication outcome (a missing or invalid token is handled
    separately: the consumer closes with 4401 after accept).
    Foreign-only offers (e.g. ``graphql-ws``) are never echoed.
    """
    if scope.get("_auth_via_subprotocol"):
        return "access_token"
    if "access_token" in scope.get("subprotocols", []):
        return "access_token"
    return None


def jwt_auth_failed(scope) -> bool:
    """
    True when a JWT WAS presented on this connection but failed validation
    (invalid, expired, revoked, or its user is inactive/missing).

    Consumers should close with code 4401 in ``connect()`` when this is
    set — the client should refresh its token and reconnect. A plain
    anonymous connection (no token presented) returns False.
    """
    return bool(scope.get("jwt_auth_failed"))


class JWTAuthMiddleware(BaseMiddleware):
    """
    JWT Authentication middleware for WebSocket connections.

    This middleware authenticates WebSocket connections by:
    1. Checking Sec-WebSocket-Protocol header for ["access_token", JWT]
    2. Checking for 'access_token' cookie
    3. Validating the token (signature, expiry, session-revocation cache)
       and setting the user in scope
    4. If a token was presented but failed validation, setting
       scope["jwt_auth_failed"] = True so consumers can close with 4401
       (the existing auth from AuthMiddlewareStack, if any, is kept)
    5. If no token was presented, leaving the existing auth untouched
       (AuthMiddlewareStack will then try session authentication)

    Usage:
        Wrap your WebSocket routing with this middleware:

            application = ProtocolTypeRouter({
                "websocket": AllowedHostsOriginValidator(
                    AuthMiddlewareStack(JWTAuthMiddleware(URLRouter(...)))
                ),
            })
    """

    async def __call__(self, scope, receive, send):
        # Only process WebSocket connections
        if scope["type"] != "websocket":
            return await super().__call__(scope, receive, send)

        # Extract token from request
        token = extract_token_from_scope(scope)

        # Authenticate user if token found
        if token:
            user = await get_user_from_token(token)
            if user:
                scope["user"] = user
                scope["jwt_auth_failed"] = False
                logger.debug(f"WebSocket authenticated: user_id={user.id}")
            else:
                # A token WAS presented but failed validation — flag it so
                # consumers can distinguish "auth failed" (close 4401) from
                # "no auth" (generic close). Never log token contents.
                scope["jwt_auth_failed"] = True
                logger.bind(path=scope.get("path", "")).warning(
                    "ws.auth.token_rejected"
                )
        else:
            logger.debug("No JWT token found, keeping existing auth (if any)")

        return await super().__call__(scope, receive, send)
