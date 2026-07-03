"""
Tests for the errors package (catalog constants + AppAPIError).
Path: utils/tests/test_errors.py
"""

import pytest

from errors.catalog import E
from errors.exceptions import AppAPIError

ALL_CODES = [
    # Auth
    "AUTH__UNAUTHENTICATED",
    "AUTH__TOKEN_EXPIRED",
    "AUTH__TOKEN_INVALID",
    "AUTH__INVALID_CREDENTIALS",
    "AUTH__ACCOUNT_INACTIVE",
    "AUTH__PASSWORD_RESET_DISABLED",
    "AUTH__EMAIL_VERIFICATION_DISABLED",
    # Validation
    "VALIDATION__MISSING_FIELD",
    "VALIDATION__INVALID_FORMAT",
    "VALIDATION__INVALID_VALUE",
    # Permission
    "PERMISSION__DENIED",
    "PERMISSION__INSUFFICIENT_ROLE",
    # Resource
    "RESOURCE__NOT_FOUND",
    "RESOURCE__ALREADY_EXISTS",
    "RESOURCE__CONFLICT",
    # Rate limit
    "RATE_LIMIT__EXCEEDED",
    # Internal
    "INTERNAL__ERROR",
    "INTERNAL__SERVICE_UNAVAILABLE",
    # Notification
    "NOTIFICATION__EMAIL_DELIVERY_FAILED",
]


class TestAppAPIError:
    """Behavior of the AppAPIError exception."""

    def test_sets_code_status_code_and_details(self):
        error = AppAPIError("RESOURCE__NOT_FOUND", status_code=404, details={"x": 1})

        assert error.code == "RESOURCE__NOT_FOUND"
        assert error.status_code == 404
        assert error.details == {"x": 1}

    def test_details_defaults_to_empty_dict_when_none(self):
        error = AppAPIError("RESOURCE__NOT_FOUND", status_code=404, details=None)

        assert error.details == {}

    def test_status_code_defaults_to_400(self):
        error = AppAPIError("INTERNAL__ERROR")

        assert error.status_code == 400

    def test_str_contains_the_code(self):
        error = AppAPIError("X")

        assert "X" in str(error)


class TestErrorCatalog:
    """Behavior of the flat catalog constants and the E namespace."""

    @pytest.mark.parametrize("code_name", ALL_CODES)
    def test_each_catalog_code_is_self_named_string(self, code_name):
        assert getattr(E, code_name) == code_name

    def test_e_resource_not_found_matches_expected_value(self):
        assert E.RESOURCE__NOT_FOUND == "RESOURCE__NOT_FOUND"

    def test_catalog_exposes_exactly_the_universal_codes(self):
        import errors.catalog as catalog_module

        exported_codes = {
            name
            for name in vars(catalog_module)
            if name.isupper() and "__" in name and isinstance(getattr(catalog_module, name), str)
        }

        assert exported_codes == set(ALL_CODES)
