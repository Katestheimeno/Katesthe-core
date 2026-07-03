"""
Tests for config/exception_handler.py — custom_exception_handler.
Path: config/tests/test_exception_handler.py
"""

from unittest.mock import patch

from django.core.exceptions import PermissionDenied as DjangoPermissionDenied
from django.http import Http404
from rest_framework.exceptions import (
    AuthenticationFailed,
    ErrorDetail,
    NotAuthenticated,
    NotFound,
    PermissionDenied as DRFPermissionDenied,
    Throttled,
    ValidationError as DRFValidationError,
)
from rest_framework.response import Response
from rest_framework.test import APIRequestFactory
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
from rest_framework_simplejwt.views import TokenObtainPairView

from config.exception_handler import custom_exception_handler
from errors.exceptions import AppAPIError

factory = APIRequestFactory()


def _build_request(request_id="req_test123"):
    request = factory.get("/")
    if request_id is not None:
        request.request_id = request_id
    return request


class _FakeTokenObtainPairView(TokenObtainPairView):
    """Throwaway TokenObtainPairView subclass to exercise the login special-case."""


def _context(view=None, request=None):
    return {"request": request or _build_request(), "view": view}


class TestAppAPIErrorBranch:
    """`AppAPIError` -> its own code/status/details, before any other branch."""

    def test_maps_to_its_own_code_status_and_details(self):
        exc = AppAPIError("RESOURCE__NOT_FOUND", status_code=404, details={"pk": 1})

        response = custom_exception_handler(exc, _context())

        assert response.status_code == 404
        assert response.data["error"]["code"] == "RESOURCE__NOT_FOUND"
        assert response.data["error"]["details"] == {"pk": 1}


class TestLoginSpecialCase:
    """Locked decision #7 — login `ValidationError` detail-shape split."""

    def test_non_field_detail_on_token_obtain_view_maps_to_401_invalid_credentials(
        self,
    ):
        exc = DRFValidationError("Invalid credentials.")
        view = _FakeTokenObtainPairView()

        response = custom_exception_handler(exc, _context(view=view))

        assert response.status_code == 401
        assert response.data["error"]["code"] == "AUTH__INVALID_CREDENTIALS"

    def test_field_keyed_detail_on_token_obtain_view_falls_through_to_422(self):
        exc = DRFValidationError(
            {
                "password": [
                    ErrorDetail("This field is required.", code="required")
                ]
            }
        )
        view = _FakeTokenObtainPairView()

        response = custom_exception_handler(exc, _context(view=view))

        assert response.status_code == 422
        assert response.data["errors"][0]["code"] == "VALIDATION__MISSING_FIELD"

    def test_non_field_dict_detail_on_token_obtain_view_maps_to_401(self):
        # Mirrors what `as_serializer_error` produces when `.validate()` raises
        # a plain `ValidationError(<string>)`: `{"non_field_errors": [<string>]}`.
        exc = DRFValidationError({"non_field_errors": ["Invalid credentials."]})
        view = _FakeTokenObtainPairView()

        response = custom_exception_handler(exc, _context(view=view))

        assert response.status_code == 401
        assert response.data["error"]["code"] == "AUTH__INVALID_CREDENTIALS"

    def test_non_field_detail_on_non_login_view_does_not_get_special_cased(self):
        exc = DRFValidationError("Some non-field error.")

        response = custom_exception_handler(exc, _context(view=None))

        assert response.status_code == 422


class TestSimpleJwtInvalidTokenBranch:
    """SimpleJWT `InvalidToken`/`TokenError` -> explicit `AUTH__TOKEN_INVALID` branch."""

    def test_invalid_token_maps_to_401_auth_token_invalid(self):
        exc = InvalidToken()

        response = custom_exception_handler(exc, _context())

        assert response.status_code == 401
        assert response.data["error"]["code"] == "AUTH__TOKEN_INVALID"

    def test_token_error_maps_to_401_auth_token_invalid(self):
        exc = TokenError("bad token")

        response = custom_exception_handler(exc, _context())

        assert response.status_code == 401
        assert response.data["error"]["code"] == "AUTH__TOKEN_INVALID"


class TestNonLoginAuthenticationFailedBranch:
    """Non-login `AuthenticationFailed` -> `AUTH__TOKEN_INVALID` (401)."""

    def test_maps_to_401_auth_token_invalid(self):
        exc = AuthenticationFailed("bad credentials")

        response = custom_exception_handler(exc, _context(view=None))

        assert response.status_code == 401
        assert response.data["error"]["code"] == "AUTH__TOKEN_INVALID"


class TestNotAuthenticatedBranch:
    def test_maps_to_401_auth_unauthenticated(self):
        exc = NotAuthenticated()

        response = custom_exception_handler(exc, _context())

        assert response.status_code == 401
        assert response.data["error"]["code"] == "AUTH__UNAUTHENTICATED"


class TestNotFoundBranches:
    def test_django_http404_maps_to_404_resource_not_found(self):
        exc = Http404()

        response = custom_exception_handler(exc, _context())

        assert response.status_code == 404
        assert response.data["error"]["code"] == "RESOURCE__NOT_FOUND"

    def test_drf_notfound_maps_to_404_resource_not_found(self):
        exc = NotFound()

        response = custom_exception_handler(exc, _context())

        assert response.status_code == 404
        assert response.data["error"]["code"] == "RESOURCE__NOT_FOUND"


class TestPermissionDeniedBranches:
    def test_drf_permission_denied_maps_to_403(self):
        exc = DRFPermissionDenied()

        response = custom_exception_handler(exc, _context())

        assert response.status_code == 403
        assert response.data["error"]["code"] == "PERMISSION__DENIED"

    def test_django_permission_denied_maps_to_403(self):
        exc = DjangoPermissionDenied()

        response = custom_exception_handler(exc, _context())

        assert response.status_code == 403
        assert response.data["error"]["code"] == "PERMISSION__DENIED"


class TestThrottledBranch:
    def test_maps_to_429_with_retry_after_in_details(self):
        exc = Throttled(wait=30)

        response = custom_exception_handler(exc, _context())

        assert response.status_code == 429
        assert response.data["error"]["code"] == "RATE_LIMIT__EXCEEDED"
        assert response.data["error"]["details"]["retry_after"] == 30


class TestValidationErrorBranch:
    def test_non_login_field_keyed_error_maps_to_422(self):
        exc = DRFValidationError(
            {"email": [ErrorDetail("This field is required.", code="required")]}
        )

        response = custom_exception_handler(exc, _context(view=None))

        assert response.status_code == 422
        assert response.data["errors"][0]["code"] == "VALIDATION__MISSING_FIELD"
        assert response.data["errors"][0]["details"]["field"] == "email"


class TestUnhandledExceptionBranch:
    def test_generic_exception_maps_to_500_internal_error(self):
        exc = Exception("boom")

        response = custom_exception_handler(exc, _context())

        assert response.status_code == 500
        assert response.data["error"]["code"] == "INTERNAL__ERROR"

    def test_generic_exception_logs_a_traceback(self):
        exc = Exception("boom")

        with patch("config.exception_handler.logger") as mock_logger:
            custom_exception_handler(exc, _context())

            mock_logger.bind.assert_called_once()
            mock_logger.bind.return_value.exception.assert_called_once_with(
                "internal.unhandled_exception"
            )


class _RaisingView(APIView):
    """Throwaway view used to exercise the handler through real DRF dispatch."""

    permission_classes = []
    authentication_classes = []

    def get(self, request):
        raise AppAPIError("RESOURCE__NOT_FOUND", status_code=404, details={"pk": 7})


class TestIntegrationThroughDrfDispatch:
    """End-to-end: a view raising `AppAPIError`, routed through real DRF dispatch."""

    def test_view_raising_app_api_error_returns_enveloped_404(self):
        request = factory.get("/whatever/")

        response = _RaisingView.as_view()(request)

        assert response.status_code == 404
        assert response.data["success"] is False
        assert response.data["error"]["code"] == "RESOURCE__NOT_FOUND"
        assert response.data["error"]["details"] == {"pk": 7}
