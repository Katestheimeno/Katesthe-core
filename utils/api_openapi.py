"""Reusable, domain-agnostic OpenAPI examples and response fragments.
Path: utils/api_openapi.py

Universal building blocks for `@extend_schema(...)` calls across the
project. Every example here mirrors the runtime envelope produced by
`utils/api_response.py` and uses only codes registered in
`errors/catalog.py`. No domain-specific payloads live here — apps compose
these fragments with their own `data` shapes.
"""

from drf_spectacular.utils import OpenApiExample, OpenApiResponse

from errors.catalog import (
    AUTH__UNAUTHENTICATED,
    PERMISSION__DENIED,
    RESOURCE__NOT_FOUND,
    VALIDATION__MISSING_FIELD,
)

EXAMPLE_META = {"request_id": "req_example", "version": "v1"}


OK_EXAMPLE = OpenApiExample(
    name="OK",
    summary="Successful response",
    description="Generic success envelope.",
    value={"success": True, "data": {}, "meta": EXAMPLE_META},
    status_codes=["200"],
    response_only=True,
)

CREATED_EXAMPLE = OpenApiExample(
    name="Created",
    summary="Resource created",
    description="Generic success envelope for a creation response.",
    value={"success": True, "data": {}, "meta": EXAMPLE_META},
    status_codes=["201"],
    response_only=True,
)

UNAUTHENTICATED_EXAMPLE = OpenApiExample(
    name="Unauthenticated",
    summary="Missing or invalid credentials",
    description="Generic single-error envelope for an unauthenticated request.",
    value={
        "success": False,
        "error": {"code": AUTH__UNAUTHENTICATED, "details": {}},
        "meta": EXAMPLE_META,
    },
    status_codes=["401"],
    response_only=True,
)

PERMISSION_DENIED_EXAMPLE = OpenApiExample(
    name="PermissionDenied",
    summary="Authenticated but not authorized",
    description="Generic single-error envelope for a forbidden request.",
    value={
        "success": False,
        "error": {"code": PERMISSION__DENIED, "details": {}},
        "meta": EXAMPLE_META,
    },
    status_codes=["403"],
    response_only=True,
)

NOT_FOUND_EXAMPLE = OpenApiExample(
    name="NotFound",
    summary="Resource not found",
    description="Generic single-error envelope for a missing resource.",
    value={
        "success": False,
        "error": {"code": RESOURCE__NOT_FOUND, "details": {}},
        "meta": EXAMPLE_META,
    },
    status_codes=["404"],
    response_only=True,
)

VALIDATION_ERROR_EXAMPLE = OpenApiExample(
    name="ValidationError",
    summary="Semantically invalid input",
    description="Generic validation-errors envelope with a single item.",
    value={
        "success": False,
        "errors": [
            {"code": VALIDATION__MISSING_FIELD, "details": {"field": "email"}},
        ],
        "meta": EXAMPLE_META,
    },
    status_codes=["422"],
    response_only=True,
)


UNAUTHENTICATED_RESPONSE = OpenApiResponse(
    description="Unauthenticated — missing or invalid credentials.",
    examples=[UNAUTHENTICATED_EXAMPLE],
)

PERMISSION_DENIED_RESPONSE = OpenApiResponse(
    description="Authenticated but not authorized to perform this action.",
    examples=[PERMISSION_DENIED_EXAMPLE],
)

NOT_FOUND_RESPONSE = OpenApiResponse(
    description="Requested resource does not exist.",
    examples=[NOT_FOUND_EXAMPLE],
)

VALIDATION_ERROR_RESPONSE = OpenApiResponse(
    description="Input failed semantic validation.",
    examples=[VALIDATION_ERROR_EXAMPLE],
)


# Reusable response-dict fragments for `@extend_schema(responses={...})`.
AUTHENTICATED_READ_RESPONSES = {
    401: UNAUTHENTICATED_RESPONSE,
    403: PERMISSION_DENIED_RESPONSE,
    404: NOT_FOUND_RESPONSE,
}

AUTHENTICATED_WRITE_RESPONSES = {
    401: UNAUTHENTICATED_RESPONSE,
    403: PERMISSION_DENIED_RESPONSE,
    404: NOT_FOUND_RESPONSE,
    422: VALIDATION_ERROR_RESPONSE,
}
