"""
Tests for config/settings/restframework.py — DEFAULT_THROTTLE_CLASSES and
DEFAULT_THROTTLE_RATES registration.
"""

import importlib

import pytest
from django.conf import settings

from config.settings import restframework as rf_settings

# `config.django.test` neutralizes throttling by mutating
# `REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"]` *in place* on the very same dict
# object that `config.settings.restframework.REST_FRAMEWORK` refers to — the
# object is aliased, not copied, through the `import *` chain
# (`restframework.py` -> `config/settings/__init__.py` -> `config/django/base.py`
# -> `config/django/test.py`). Reading `rf_settings.REST_FRAMEWORK` as-is under
# test settings therefore still returns the neutralized "9999/min" rates.
# Re-importing the module (`reload`) re-executes its top-level code and
# rebinds `REST_FRAMEWORK` to a brand new dict, independent of the one
# `config.django.test` already mutated, giving us the rates the module
# actually declares in source.
_PRODUCTION_REST_FRAMEWORK = importlib.reload(rf_settings).REST_FRAMEWORK

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
    """`DEFAULT_THROTTLE_RATES` registers all 14 scopes with their exact rate.

    Read from a freshly re-imported `config.settings.restframework` module
    rather than effective Django settings — `config.django.test` overrides
    `DEFAULT_THROTTLE_RATES` to a permissive rate for every scope so
    throttle-dependent tests don't flake, which would otherwise mask the
    production rates this test is meant to verify.
    """

    @pytest.mark.parametrize("scope, expected_rate", list(EXPECTED_RATES.items()))
    def test_scope_has_expected_rate(self, scope, expected_rate):
        rates = _PRODUCTION_REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"]

        assert rates[scope] == expected_rate

    def test_rates_contains_exactly_the_fourteen_expected_scopes(self):
        rates = _PRODUCTION_REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"]

        assert set(rates.keys()) == set(EXPECTED_RATES.keys())
