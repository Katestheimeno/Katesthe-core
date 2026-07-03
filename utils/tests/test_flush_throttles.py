"""
Tests for the `flush_throttles` management command.
Path: utils/tests/test_flush_throttles.py
"""

from django.core.cache import cache
from django.core.management import call_command


class TestFlushThrottlesCommand:
    """`flush_throttles` clears throttle counters without crashing on LocMemCache."""

    def test_completes_without_exception_on_non_redis_backend(self):
        cache.set("throttle_auth_login_1.2.3.4", 2, timeout=60)

        call_command("flush_throttles")

    def test_falls_back_to_full_cache_clear_on_non_redis_backend(self):
        cache.set("throttle_auth_login_1.2.3.4", 2, timeout=60)
        cache.set("unrelated_key", "value", timeout=60)

        call_command("flush_throttles")

        assert cache.get("throttle_auth_login_1.2.3.4") is None
        assert cache.get("unrelated_key") is None

    def test_writes_fallback_notice_to_stdout(self, capsys):
        cache.set("throttle_auth_login_1.2.3.4", 2, timeout=60)

        call_command("flush_throttles")

        captured = capsys.readouterr()
        assert "fallback" in captured.out.lower()
