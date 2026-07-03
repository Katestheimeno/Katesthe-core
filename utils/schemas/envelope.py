"""Pydantic models mirroring the API response envelope.
Path: utils/schemas/envelope.py

These models exist for OpenAPI documentation purposes only (drf-spectacular
schema generation). They mirror the envelope shapes produced at runtime by
`utils/api_response.py`. There is intentionally no ``message`` field
anywhere — the frontend owns i18n and only consumes machine-readable codes
(`.claude/rules/api.md`).
"""

from typing import Any, Literal, Optional

from pydantic import BaseModel


class ApiMeta(BaseModel):
    """The ``meta`` block attached to every envelope."""

    request_id: str
    version: str


class ApiErrorBody(BaseModel):
    """The ``error`` object for a single-error failure envelope."""

    code: str
    details: Optional[dict[str, Any]] = None


class ApiErrorEnvelope(BaseModel):
    """Failure envelope carrying a single error."""

    success: Literal[False]
    error: ApiErrorBody
    meta: ApiMeta


class ApiValidationErrorItem(BaseModel):
    """A single entry inside a validation-errors envelope."""

    code: str
    details: Optional[dict[str, Any]] = None


class ApiValidationErrorsEnvelope(BaseModel):
    """Failure envelope carrying multiple validation errors."""

    success: Literal[False]
    errors: list[ApiValidationErrorItem]
    meta: ApiMeta


class ApiSuccessEnvelope(BaseModel):
    """Success envelope carrying arbitrary ``data``."""

    success: Literal[True]
    data: Any
    meta: ApiMeta
