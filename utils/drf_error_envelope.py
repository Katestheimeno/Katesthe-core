"""Normalize DRF's native error shapes into the project response envelope.

DRF raises ``ValidationError`` with a ``{field: [errors]}`` detail and
returns plain ``{"detail": "..."}`` bodies for 404/401/403/405/406/409/415/
429 and other built-in exceptions. This module converts both shapes into the
standard envelope (`.claude/rules/api.md`) so the exception handler (004)
stays thin.
"""

from __future__ import annotations

from typing import Any

from rest_framework import status
from rest_framework.response import Response

from errors.catalog import (
    AUTH__UNAUTHENTICATED,
    INTERNAL__ERROR,
    PERMISSION__DENIED,
    RATE_LIMIT__EXCEEDED,
    RESOURCE__CONFLICT,
    RESOURCE__NOT_FOUND,
    VALIDATION__INVALID_FORMAT,
    VALIDATION__INVALID_VALUE,
    VALIDATION__MISSING_FIELD,
)
from utils.api_response import err_single, meta_for_request

# DRF ErrorDetail.code -> catalog VALIDATION__* code.
# NOTE: domain-specific entries (e.g. "image_too_large" / "image_invalid_type")
# belong to Phase 3 subtask 018 and are intentionally NOT added here — this
# map stays generic.
_FIELD_CODE_MAP: dict[str, str] = {
    "required": VALIDATION__MISSING_FIELD,
    "null": VALIDATION__MISSING_FIELD,
    "blank": VALIDATION__MISSING_FIELD,
    "invalid": VALIDATION__INVALID_FORMAT,
    "invalid_choice": VALIDATION__INVALID_VALUE,
}

# Explicit status -> catalog code map for DRF's built-in `{"detail": ...}`
# responses. Never route a 4xx to INTERNAL__ERROR — that code is 5xx-only
# per `.claude/rules/api.md`.
_STATUS_CODE_MAP: dict[int, str] = {
    400: VALIDATION__INVALID_FORMAT,
    401: AUTH__UNAUTHENTICATED,
    403: PERMISSION__DENIED,
    404: RESOURCE__NOT_FOUND,
    405: VALIDATION__INVALID_FORMAT,
    406: VALIDATION__INVALID_FORMAT,
    409: RESOURCE__CONFLICT,
    415: VALIDATION__INVALID_FORMAT,
    429: RATE_LIMIT__EXCEEDED,
}


def _field_error_code(err: Any) -> str:
    """Map a single DRF ``ErrorDetail`` to a catalog code. Unknown/missing code falls back to ``VALIDATION__INVALID_VALUE``."""
    code = getattr(err, "code", None)
    if isinstance(code, str) and code in _FIELD_CODE_MAP:
        return _FIELD_CODE_MAP[code]
    return VALIDATION__INVALID_VALUE


def normalize_validation_detail(detail: Any) -> list[dict[str, Any]]:
    """Flatten a DRF validation ``detail`` into a list of catalog-coded errors.

    Accepts the three shapes DRF can raise a ``ValidationError`` with:
    - ``dict`` — ``{field: [ErrorDetail, ...]}`` (or ``{field: ErrorDetail}``).
    - ``list`` — non-field errors (e.g. list serializer / plain list raise).
    - scalar — a single ``ErrorDetail`` or string.
    """
    out: list[dict[str, Any]] = []

    if isinstance(detail, dict):
        for field, msgs in detail.items():
            items = msgs if isinstance(msgs, list) else [msgs]
            for msg in items:
                out.append(
                    {"code": _field_error_code(msg), "details": {"field": field}}
                )
        return out

    if isinstance(detail, list):
        for item in detail:
            out.append(
                {
                    "code": _field_error_code(item),
                    "details": {"field": "non_field_errors"},
                }
            )
        return out

    return [
        {
            "code": _field_error_code(detail),
            "details": {"field": "non_field_errors"},
        }
    ]


def validation_error_response(errors_list: list[dict[str, Any]], request) -> Response:
    """Wrap a list of field-level errors in the multi-error failure envelope (HTTP 422)."""
    return Response(
        {
            "success": False,
            "errors": errors_list,
            "meta": meta_for_request(request),
        },
        status=status.HTTP_422_UNPROCESSABLE_ENTITY,
    )


def _status_to_code(status_code: int) -> str:
    """Map an HTTP status code to a catalog error code. Never maps a 4xx to ``INTERNAL__ERROR``."""
    if status_code in _STATUS_CODE_MAP:
        return _STATUS_CODE_MAP[status_code]
    if status_code >= 500:
        return INTERNAL__ERROR
    return VALIDATION__INVALID_VALUE


def coerce_drf_error_response(request, response: Response) -> Response:
    """Rewrap a raw DRF ``{"detail": ...}`` error response into the standard envelope.

    Idempotent: if the response body is already enveloped (has a ``success``
    key), it is returned unchanged.
    """
    data = response.data
    if (
        isinstance(data, dict)
        and "detail" in data
        and "success" not in data
    ):
        code = _status_to_code(response.status_code)
        return err_single(
            code,
            request,
            status=response.status_code,
            details={},
        )
    return response
