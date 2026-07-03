"""Emit one structured access-log line per request via Loguru.

Path: config/middleware/access_log.py
"""

import time

from django.utils.deprecation import MiddlewareMixin

from config.logger import logger

# 200-status paths that are pure noise (health checks, static/media serving).
_SKIP_PREFIXES = ("/health", "/ready", "/static", "/media")
_SKIP_EXACT = ("/favicon.ico",)


class AccessLogMiddleware(MiddlewareMixin):
    """Log method/path/status/duration/size/user/request_id for every request.

    Health/static/media 200s are skipped to keep logs signal-only; 4xx/5xx
    responses are additionally enriched with client IP and user-agent.
    """

    def process_request(self, request):
        request._access_start = time.monotonic()

    def process_response(self, request, response):
        start = getattr(request, "_access_start", None)
        duration_ms = round((time.monotonic() - start) * 1000, 2) if start is not None else 0.0

        path = request.path
        method = request.method
        status = response.status_code
        size = (
            len(response.content)
            if hasattr(response, "content") and not getattr(response, "streaming", False)
            else 0
        )
        user = getattr(request, "user", None)
        user_id = getattr(user, "id", None)
        request_id = getattr(request, "request_id", "-")

        if status == 200 and (path.startswith(_SKIP_PREFIXES) or path in _SKIP_EXACT):
            return response

        log = logger.bind(
            method=method,
            path=path,
            status=status,
            duration_ms=duration_ms,
            size=size,
            user_id=user_id,
            request_id=request_id,
            access=True,
        )

        if status >= 400:
            xff = request.META.get("HTTP_X_FORWARDED_FOR")
            ip = xff.split(",")[0].strip() if xff else request.META.get("REMOTE_ADDR")
            user_agent = request.META.get("HTTP_USER_AGENT", "")[:256]
            log = log.bind(ip=ip, user_agent=user_agent)

        if status >= 500:
            log.warning("http.access")
        else:
            log.info("http.access")

        return response
