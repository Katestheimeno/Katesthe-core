"""Log request/response bodies for local debugging, with secrets redacted.

Path: config/middleware/debug_payload.py

Opt-in via the ``REQUEST_RESPONSE_DEBUG`` feature flag (pydantic settings).
Refuses to activate unless Django's resolved ``DEBUG`` is ``True`` — never
wire this into production.
"""

import json

from django.conf import settings as dj_settings
from django.core.exceptions import ImproperlyConfigured
from django.utils.deprecation import MiddlewareMixin

from config.logger import logger
from config.settings.config import settings as app_settings

# Case-insensitive key names whose values are always redacted.
_REDACT_KEYS = {
    "password",
    "token",
    "access",
    "refresh",
    "secret",
    "otp",
    "api_key",
    "apikey",
    "authorization",
    "auth",
    "client_secret",
    "private_key",
    "card",
    "cvv",
    "pin",
    "session",
    "cookie",
    "signature",
    "credentials",
    "jwt",
}

# Path prefixes that are never logged (noise / not useful / large payloads).
_SKIP_PREFIXES = ("/admin", "/static", "/media", "/health", "/ready", "/api/schema", "/silk/")

_MAX_BODY_BYTES = 4096


def _redact(value):
    """Recursively return a new structure with sensitive dict values replaced.

    Does not mutate the input. Lists are walked item-by-item; scalars are
    returned unchanged.
    """
    if isinstance(value, dict):
        redacted = {}
        for key, item in value.items():
            if isinstance(key, str) and key.lower() in _REDACT_KEYS:
                redacted[key] = "[REDACTED]"
            else:
                redacted[key] = _redact(item)
        return redacted
    if isinstance(value, list):
        return [_redact(item) for item in value]
    return value


class DebugPayloadMiddleware(MiddlewareMixin):
    """Log JSON request/response bodies (redacted) when explicitly enabled.

    Enabled only when the ``REQUEST_RESPONSE_DEBUG`` flag is set AND Django's
    resolved ``DEBUG`` is ``True`` — otherwise construction raises
    ``ImproperlyConfigured`` to prevent accidental activation in production.
    """

    def __init__(self, get_response=None):
        super().__init__(get_response)
        enabled = bool(getattr(app_settings, "REQUEST_RESPONSE_DEBUG", False))
        if enabled and not dj_settings.DEBUG:
            raise ImproperlyConfigured("REQUEST_RESPONSE_DEBUG requires DEBUG=True")
        self.enabled = enabled

    def _skip(self, path):
        return path.startswith(_SKIP_PREFIXES)

    def process_request(self, request):
        if not self.enabled:
            return None
        if self._skip(request.path):
            return None

        content_type = request.META.get("CONTENT_TYPE", "")
        if "application/json" not in content_type:
            return None

        try:
            body = request.body[:_MAX_BODY_BYTES]
            if not body:
                return None
            parsed = json.loads(body.decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError):
            return None

        logger.bind(path=request.path, method=request.method, body=_redact(parsed)).debug(
            "debug.request"
        )
        return None

    def process_response(self, request, response):
        if not self.enabled:
            return response
        if self._skip(request.path):
            return response

        content_type = response.get("Content-Type", "") if hasattr(response, "get") else ""
        if "application/json" not in content_type:
            return response
        if getattr(response, "streaming", False):
            return response
        if not hasattr(response, "content"):
            return response

        try:
            body = response.content[:_MAX_BODY_BYTES]
            if not body:
                return response
            parsed = json.loads(body.decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError):
            return response

        logger.bind(
            path=request.path, status=response.status_code, body=_redact(parsed)
        ).debug("debug.response")
        return response
