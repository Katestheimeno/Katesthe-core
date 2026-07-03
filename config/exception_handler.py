"""DRF exception handler producing machine-readable error envelopes.

Maps raised exceptions to the project's response envelope
(`.claude/rules/api.md`). Explicit `isinstance` branches are evaluated in a
fixed order (see the branch table below) before falling back to DRF's
default handler + `coerce_drf_error_response`. The fallback is a safety net
only — distinct-code branches (e.g. `InvalidToken` -> `AUTH__TOKEN_INVALID`,
`Throttled` -> `retry_after`) MUST stay explicit here because
`coerce_drf_error_response` keys only on HTTP status and cannot produce
those codes/details.
"""

from __future__ import annotations

from typing import Any

from django.core.exceptions import PermissionDenied as DjangoPermissionDenied
from django.http import Http404
from rest_framework.exceptions import (
    AuthenticationFailed,
    NotAuthenticated,
    NotFound,
    PermissionDenied as DRFPermissionDenied,
    Throttled,
    ValidationError as DRFValidationError,
)
from rest_framework.settings import api_settings
from rest_framework.views import exception_handler as drf_exception_handler
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
from rest_framework_simplejwt.views import TokenObtainPairView

from config.logger import logger
from errors.catalog import (
    AUTH__INVALID_CREDENTIALS,
    AUTH__TOKEN_INVALID,
    AUTH__UNAUTHENTICATED,
    INTERNAL__ERROR,
    PERMISSION__DENIED,
    RATE_LIMIT__EXCEEDED,
    RESOURCE__NOT_FOUND,
)
from errors.exceptions import AppAPIError
from utils.api_response import err_single
from utils.drf_error_envelope import (
    coerce_drf_error_response,
    normalize_validation_detail,
    validation_error_response,
)


def _is_login_non_field_validation_error(exc: Exception, view: Any) -> bool:
    """True for a token-obtain `ValidationError` whose detail is non-field.

    Locked decision #7: `CustomJWTTokenCreateView(TokenObtainPairView)`'s
    serializer raises a plain DRF `ValidationError` for every auth failure
    (never `AuthenticationFailed`). The detail shape distinguishes real
    credential rejection (non-field) from a missing/invalid field (field-
    keyed, which stays on the normal 422 path). Keep this narrow: only
    `TokenObtainPairView` subclasses trigger the special case.
    """
    if not isinstance(exc, DRFValidationError):
        return False
    if not isinstance(view, TokenObtainPairView):
        return False

    detail = exc.detail
    if isinstance(detail, (list, str)):
        return True
    if isinstance(detail, dict):
        return set(detail.keys()) == {api_settings.NON_FIELD_ERRORS_KEY}
    return False


def custom_exception_handler(exc: Exception, context: dict[str, Any]):
    """Map `exc` to the standard envelope response.

    Branch order (see `.claude/tasks/depadrive-backport/004-exception-handler.md`
    Step 1, items 1-12) is significant and MUST NOT be reordered:
    `AppAPIError` -> login non-field `ValidationError` -> SimpleJWT
    `InvalidToken`/`TokenError` -> non-login `AuthenticationFailed` ->
    `NotAuthenticated` -> `Http404`/`NotFound` -> `PermissionDenied` ->
    `Throttled` -> other `ValidationError` -> DRF default handler + coerce
    -> unhandled (log + 500).
    """
    request = context.get("request")
    view = context.get("view")

    if isinstance(exc, AppAPIError):
        return err_single(
            exc.code,
            request,
            status=exc.status_code,
            details=exc.details,
        )

    if _is_login_non_field_validation_error(exc, view):
        return err_single(AUTH__INVALID_CREDENTIALS, request, status=401)

    if isinstance(exc, (InvalidToken, TokenError)):
        return err_single(AUTH__TOKEN_INVALID, request, status=401)

    if isinstance(exc, AuthenticationFailed):
        return err_single(AUTH__TOKEN_INVALID, request, status=401)

    if isinstance(exc, NotAuthenticated):
        return err_single(AUTH__UNAUTHENTICATED, request, status=401)

    if isinstance(exc, (Http404, NotFound)):
        return err_single(RESOURCE__NOT_FOUND, request, status=404)

    if isinstance(exc, (DRFPermissionDenied, DjangoPermissionDenied)):
        return err_single(PERMISSION__DENIED, request, status=403)

    if isinstance(exc, Throttled):
        return err_single(
            RATE_LIMIT__EXCEEDED,
            request,
            status=429,
            details={"retry_after": getattr(exc, "wait", None)},
        )

    if isinstance(exc, DRFValidationError):
        return validation_error_response(
            normalize_validation_detail(exc.detail), request
        )

    response = drf_exception_handler(exc, context)
    if response is not None:
        return coerce_drf_error_response(request, response)

    logger.bind(exc_type=type(exc).__name__).exception(
        "internal.unhandled_exception"
    )
    return err_single(INTERNAL__ERROR, request, status=500)
