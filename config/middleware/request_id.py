"""Attach a stable request id for tracing (meta.request_id) and propagate it to logs.

Path: config/middleware/request_id.py
"""

import uuid
from contextvars import ContextVar

from django.utils.deprecation import MiddlewareMixin

# Importable by config.logger to inject the current request id into log records.
request_id_ctx: ContextVar[str] = ContextVar("request_id", default="-")


class RequestIdMiddleware(MiddlewareMixin):
    """Assign/propagate a request id and echo it back as `X-Request-ID`."""

    header_name = "HTTP_X_REQUEST_ID"

    def process_request(self, request):
        rid = request.META.get(self.header_name) or f"req_{uuid.uuid4().hex[:24]}"
        request.request_id = rid
        request.request_id_token = request_id_ctx.set(rid)

    def process_response(self, request, response):
        token = getattr(request, "request_id_token", None)
        try:
            response["X-Request-ID"] = getattr(request, "request_id", "-")
        finally:
            if token is not None:
                request_id_ctx.reset(token)
        return response
