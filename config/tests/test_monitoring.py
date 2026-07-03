"""
Tests for config/settings/monitoring.py.
"""

import importlib.util
from unittest import mock

from config.settings.config import settings
from config.settings.monitoring import configure_sentry


class TestConfigureSentryNoOp:
    def test_configure_sentry_returns_false_and_does_not_raise_when_dsn_is_empty(self):
        assert settings.SENTRY_DSN == ""

        assert configure_sentry() is False


class TestConfigureSentryWithDsn:
    def test_configure_sentry_initializes_sentry_when_dsn_and_sdk_present(self, monkeypatch):
        monkeypatch.setattr(settings, "SENTRY_DSN", "https://fake@example.com/1")

        has_sdk = importlib.util.find_spec("sentry_sdk") is not None

        if has_sdk:
            with mock.patch("sentry_sdk.init") as m_init:
                result = configure_sentry()

            assert result is True
            m_init.assert_called_once()
            assert m_init.call_args.kwargs.get("send_default_pii") is False
        else:
            assert configure_sentry() is False


class TestSentrySettingsFields:
    def test_sentry_dsn_defaults_to_empty_string(self):
        assert settings.SENTRY_DSN == ""

    def test_sentry_traces_sample_rate_defaults_to_point_one(self):
        assert settings.SENTRY_TRACES_SAMPLE_RATE == 0.1
