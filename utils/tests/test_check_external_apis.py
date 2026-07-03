"""
Tests for the `check_external_apis` management command scaffold.
Path: utils/tests/test_check_external_apis.py
"""

from unittest.mock import patch

import pytest
import requests
from django.core.management import call_command

from utils.management.commands.check_external_apis import (
    ProbeResult,
    ProbeStatus,
    SERVICES,
)


class TestCheckExternalApisCommand:
    """`check_external_apis` behaves correctly with an empty SERVICES registry."""

    def test_empty_registry_runs_clean_without_raising(self):
        call_command("check_external_apis")

    def test_empty_registry_prints_no_services_registered_message(self, capsys):
        call_command("check_external_apis")

        captured = capsys.readouterr()
        assert "no services registered" in captured.out.lower()

    def test_verbose_and_timeout_flags_parse_and_run_clean(self, capsys):
        call_command("check_external_apis", "--verbose", "--timeout", "5")

        captured = capsys.readouterr()
        assert "no services registered" in captured.out.lower()

    def test_a_fail_result_triggers_exit_code_1(self, monkeypatch, capsys):
        def _fail_probe(timeout, verbose):
            return [ProbeResult(service="x", endpoint="/y", status=ProbeStatus.FAIL)]

        monkeypatch.setitem(SERVICES, "x", _fail_probe)

        with pytest.raises(SystemExit) as exc_info:
            call_command("check_external_apis", "--service", "x")

        assert exc_info.value.code == 1
        capsys.readouterr()

    def test_a_passing_result_does_not_raise_system_exit(self, monkeypatch, capsys):
        def _pass_probe(timeout, verbose):
            return [ProbeResult(service="x", endpoint="/y", status=ProbeStatus.PASS)]

        monkeypatch.setitem(SERVICES, "x", _pass_probe)

        call_command("check_external_apis", "--service", "x")
        capsys.readouterr()


class TestProbeResultDataclass:
    """`ProbeResult` carries its documented defaults."""

    def test_defaults_are_zero_duration_and_empty_warnings(self):
        result = ProbeResult(service="x", endpoint="y", status=ProbeStatus.PASS)

        assert result.duration_ms == 0.0
        assert result.warnings == []


class TestProbeStatusEnum:
    """`ProbeStatus` members equal their expected string values."""

    @pytest.mark.parametrize(
        "member,expected",
        [
            (ProbeStatus.PASS, "PASS"),
            (ProbeStatus.FAIL, "FAIL"),
            (ProbeStatus.SKIP, "SKIP"),
            (ProbeStatus.MOCK, "MOCK"),
        ],
    )
    def test_member_equals_its_string_value(self, member, expected):
        assert member == expected


class TestTimedGetHelper:
    """`_timed_get` handles the timeout branch without raising."""

    def test_timeout_returns_none_response_with_duration_and_error_message(self):
        from utils.management.commands.check_external_apis import _timed_get

        with patch(
            "utils.management.commands.check_external_apis.requests.get",
            side_effect=requests.exceptions.Timeout,
        ):
            resp, duration_ms, error = _timed_get("https://example.test", {}, 1)

        assert resp is None
        assert isinstance(duration_ms, float)
        assert "timeout" in error.lower()
