"""
Tests for the test-settings throttle override in config/django/test.py.
Path: config/tests/test_throttle_override.py
"""

from django.conf import settings


class TestThrottleRatesNeutralizedInTests:
    """`DEFAULT_THROTTLE_RATES` is overridden to a very high rate for every scope."""

    def test_every_configured_rate_is_neutralized(self):
        rates = settings.REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"]

        assert all(rate == "9999/min" for rate in rates.values())

    def test_default_throttle_rates_key_is_a_dict(self):
        rates = settings.REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"]

        assert isinstance(rates, dict)
