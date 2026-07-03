"""
Tests for config/settings/restframework.py — DEFAULT_THROTTLE_CLASSES and
DEFAULT_THROTTLE_RATES registration.
"""

import pytest
from django.conf import settings

EXPECTED_RATES = {
    "default_anon": "60/min",
    "default_user": "120/min",
    "auth_login": "10/min",
    "auth_login_account": "5/hour",
    "auth_register": "5/hour",
    "auth_reset": "3/hour",
    "auth_set_password": "10/hour",
    "auth_refresh": "20/min",
    "auth_activation": "10/hour",
    "public_list": "120/min",
    "search": "60/min",
    "webhook": "200/min",
    "external_api": "300/min",
    "user_mutation": "30/min",
}


class TestDefaultThrottleClasses:
    """`DEFAULT_THROTTLE_CLASSES` points at the two `utils.throttles` defaults."""

    def test_default_throttle_classes_lists_utils_throttles_defaults(self):
        throttle_classes = settings.REST_FRAMEWORK["DEFAULT_THROTTLE_CLASSES"]

        assert throttle_classes == [
            "utils.throttles.DefaultAnonThrottle",
            "utils.throttles.DefaultUserThrottle",
        ]


class TestDefaultThrottleRates:
    """`DEFAULT_THROTTLE_RATES` registers all 14 scopes with their exact rate."""

    @pytest.mark.parametrize("scope, expected_rate", list(EXPECTED_RATES.items()))
    def test_scope_has_expected_rate(self, scope, expected_rate):
        rates = settings.REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"]

        assert rates[scope] == expected_rate

    def test_rates_contains_exactly_the_fourteen_expected_scopes(self):
        rates = settings.REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"]

        assert set(rates.keys()) == set(EXPECTED_RATES.keys())
