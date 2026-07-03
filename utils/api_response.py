"""Standard success/error JSON envelopes for API responses.

Every response body follows the project envelope contract (`.claude/rules/api.md`):
``meta`` always carries ``request_id`` and ``version``; there is never a
``message`` field — the frontend owns i18n and only consumes machine-readable
error codes.
"""

from __future__ import annotations

import uuid
from typing import Any

from rest_framework.response import Response


def _fallback_request_id() -> str:
    """Generate a request id when none was attached to the request."""
    return f"req_{uuid.uuid4().hex[:24]}"


def meta_for_request(request) -> dict[str, Any]:
    """Build the ``meta`` block for a response, always including a request id."""
    request_id = getattr(request, "request_id", None) or _fallback_request_id()
    return {"request_id": request_id, "version": "v1"}


def ok(
    data: Any,
    request,
    status: int = 200,
    meta_extra: dict[str, Any] | None = None,
) -> Response:
    """Wrap ``data`` in the success envelope."""
    meta = {**meta_for_request(request), **(meta_extra or {})}
    return Response(
        {"success": True, "data": data, "meta": meta},
        status=status,
    )


def err_single(
    code: str,
    request,
    *,
    status: int = 400,
    details: dict | None = None,
) -> Response:
    """Wrap a single error ``code`` in the failure envelope."""
    body: dict[str, Any] = {
        "success": False,
        "error": {"code": code, "details": details or {}},
        "meta": meta_for_request(request),
    }
    return Response(body, status=status)
