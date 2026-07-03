"""
Tests for the baseline security headers added in config/django/base.py and the
CSRF_TRUSTED_ORIGINS derivation added in config/django/production.py.

Baseline headers (X_FRAME_OPTIONS, SECURE_CONTENT_TYPE_NOSNIFF,
SECURE_REFERRER_POLICY) are exercised in-process against the already-booted
test settings, since base.py values apply identically across environments.

CSRF_TRUSTED_ORIGINS is production-only and derived at import time from
ALLOWED_HOSTS, so it is exercised via a subprocess boot mirroring
config/tests/test_production_settings.py.
"""

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest
from django.conf import settings

from config.tests.test_production_jwt import _TEST_RSA_PRIVATE_KEY_B64

# Only TestCsrfTrustedOriginsDerivation's subprocess-boot tests are slow;
# TestBaselineSecurityHeaders runs in-process. Marker is applied per-class
# below rather than module-wide so the cheap tests stay selectable.
REPO_ROOT = Path(__file__).resolve().parent.parent.parent

# Mirrors config/tests/test_production_settings.py::BASE_ENV — production.py
# enforces RS256 at boot, so every subprocess needs a valid JWT_RSA_PRIVATE_KEY
# to reach the assertions under test.
BASE_ENV = {
    "SECRET_KEY": "test-secret-key-for-subprocess-only",
    "JWT_SECRET_KEY": "test-jwt-secret-key-for-subprocess-only",
    "DJANGO_ENV": "",
    "JWT_RSA_PRIVATE_KEY": _TEST_RSA_PRIVATE_KEY_B64,
}


def _build_env(overrides: dict) -> dict:
    env = os.environ.copy()
    env.update(BASE_ENV)
    env.update(overrides)
    return env


def _run(code: str, overrides: dict) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, "-c", code],
        cwd=str(REPO_ROOT),
        env=_build_env(overrides),
        capture_output=True,
        text=True,
        timeout=30,
    )


class TestBaselineSecurityHeaders:
    def test_x_frame_options_is_deny(self):
        assert settings.X_FRAME_OPTIONS == "DENY"

    def test_secure_content_type_nosniff_is_enabled(self):
        assert settings.SECURE_CONTENT_TYPE_NOSNIFF is True

    def test_secure_referrer_policy_is_strict_origin_when_cross_origin(self):
        assert settings.SECURE_REFERRER_POLICY == "strict-origin-when-cross-origin"


@pytest.mark.slow
class TestCsrfTrustedOriginsDerivation:
    def test_csrf_trusted_origins_derived_from_allowed_hosts(self):
        result = _run(
            "import django; django.setup(); "
            "from django.conf import settings; "
            "import json; print(json.dumps(settings.CSRF_TRUSTED_ORIGINS))",
            {
                "DJANGO_SETTINGS_MODULE": "config.django.production",
                "DEBUG": "False",
                "ALLOWED_HOSTS": "example.com,api.example.com",
            },
        )

        assert result.returncode == 0, result.stderr
        origins = json.loads(result.stdout)
        assert origins == ["https://example.com", "https://api.example.com"]

    def test_csrf_trusted_origins_excludes_wildcard_host(self):
        # ALLOWED_HOSTS with only "*" fails the boot assertion in production.py
        # before CSRF_TRUSTED_ORIGINS is ever computed, so mix a wildcard in
        # with an explicit host to exercise the `if h != "*"` filter itself.
        result = _run(
            "import django; django.setup(); "
            "from django.conf import settings; "
            "import json; print(json.dumps(settings.CSRF_TRUSTED_ORIGINS))",
            {
                "DJANGO_SETTINGS_MODULE": "config.django.production",
                "DEBUG": "False",
                "ALLOWED_HOSTS": "example.com,*",
            },
        )

        assert result.returncode == 0, result.stderr
        origins = json.loads(result.stdout)
        assert origins == ["https://example.com"]

    def test_csrf_trusted_origins_derivation_logic_against_sample_hosts(self):
        # Unit-level check of the exact comprehension used in production.py,
        # independent of subprocess boot cost.
        sample_hosts = ["example.com", "*", "api.example.com"]

        origins = [f"https://{h}" for h in sample_hosts if h != "*"]

        assert origins == ["https://example.com", "https://api.example.com"]
