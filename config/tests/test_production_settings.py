"""
Tests for config/django/production.py boot-time hardening and the CORS
loopback gate in config/settings/corsheaders.py.

`production.py` runs its assertions and sets security constants at *import*
time (`django.setup()`), so the only reliable way to exercise both the
success and failure paths is a real subprocess with a controlled
environment — importing it in-process would poison the current process'
already-configured Django settings.
"""

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

pytestmark = pytest.mark.slow

REPO_ROOT = Path(__file__).resolve().parent.parent.parent

# Minimal env every subprocess needs: pydantic-required fields (SECRET_KEY,
# JWT_SECRET_KEY) plus DJANGO_SETTINGS_MODULE. DJANGO_ENV is intentionally
# blanked so `get_env_file_path()` falls back to the (nonexistent) .env.prod
# file instead of silently picking up repo dotenv values — every setting
# under test is then fully controlled by the env we pass in.
BASE_ENV = {
    "SECRET_KEY": "test-secret-key-for-subprocess-only",
    "JWT_SECRET_KEY": "test-jwt-secret-key-for-subprocess-only",
    "DJANGO_ENV": "",
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


class TestProductionBootAssertions:
    def test_boot_succeeds_with_debug_false_and_explicit_allowed_hosts(self):
        result = _run(
            "import django; django.setup()",
            {
                "DJANGO_SETTINGS_MODULE": "config.django.production",
                "DEBUG": "False",
                "ALLOWED_HOSTS": "example.com",
            },
        )

        assert result.returncode == 0, result.stderr

    def test_boot_raises_assertion_error_when_debug_true(self):
        result = _run(
            "import django; django.setup()",
            {
                "DJANGO_SETTINGS_MODULE": "config.django.production",
                "DEBUG": "True",
                "ALLOWED_HOSTS": "example.com",
            },
        )

        assert result.returncode != 0
        assert "AssertionError" in result.stderr
        assert "DEBUG must be False in production" in result.stderr

    def test_boot_raises_assertion_error_when_allowed_hosts_is_wildcard(self):
        result = _run(
            "import django; django.setup()",
            {
                "DJANGO_SETTINGS_MODULE": "config.django.production",
                "DEBUG": "False",
                "ALLOWED_HOSTS": "*",
            },
        )

        assert result.returncode != 0
        assert "AssertionError" in result.stderr
        assert "ALLOWED_HOSTS must be explicit" in result.stderr

    def test_boot_raises_assertion_error_when_allowed_hosts_is_empty(self):
        result = _run(
            "import django; django.setup()",
            {
                "DJANGO_SETTINGS_MODULE": "config.django.production",
                "DEBUG": "False",
                "ALLOWED_HOSTS": "",
            },
        )

        assert result.returncode != 0
        assert "AssertionError" in result.stderr
        assert "ALLOWED_HOSTS must be explicit" in result.stderr


class TestProductionSecurityConstants:
    def test_security_headers_have_expected_values(self):
        script = (
            "import django; django.setup(); "
            "from django.conf import settings; "
            "import json; "
            "print(json.dumps({\n"
            "    'SECURE_HSTS_SECONDS': settings.SECURE_HSTS_SECONDS,\n"
            "    'SECURE_HSTS_INCLUDE_SUBDOMAINS': settings.SECURE_HSTS_INCLUDE_SUBDOMAINS,\n"
            "    'SECURE_HSTS_PRELOAD': settings.SECURE_HSTS_PRELOAD,\n"
            "    'SECURE_SSL_REDIRECT': settings.SECURE_SSL_REDIRECT,\n"
            "    'SESSION_COOKIE_SECURE': settings.SESSION_COOKIE_SECURE,\n"
            "    'CSRF_COOKIE_SECURE': settings.CSRF_COOKIE_SECURE,\n"
            "    'SECURE_CONTENT_TYPE_NOSNIFF': settings.SECURE_CONTENT_TYPE_NOSNIFF,\n"
            "    'SECURE_REFERRER_POLICY': settings.SECURE_REFERRER_POLICY,\n"
            "    'X_FRAME_OPTIONS': settings.X_FRAME_OPTIONS,\n"
            "    'SECURE_PROXY_SSL_HEADER': list(settings.SECURE_PROXY_SSL_HEADER),\n"
            "}))"
        )

        result = _run(
            script,
            {
                "DJANGO_SETTINGS_MODULE": "config.django.production",
                "DEBUG": "False",
                "ALLOWED_HOSTS": "example.com",
            },
        )

        assert result.returncode == 0, result.stderr
        values = json.loads(result.stdout)
        assert values == {
            "SECURE_HSTS_SECONDS": 31536000,
            "SECURE_HSTS_INCLUDE_SUBDOMAINS": True,
            "SECURE_HSTS_PRELOAD": True,
            "SECURE_SSL_REDIRECT": True,
            "SESSION_COOKIE_SECURE": True,
            "CSRF_COOKIE_SECURE": True,
            "SECURE_CONTENT_TYPE_NOSNIFF": True,
            "SECURE_REFERRER_POLICY": "same-origin",
            "X_FRAME_OPTIONS": "DENY",
            "SECURE_PROXY_SSL_HEADER": ["HTTP_X_FORWARDED_PROTO", "https"],
        }


class TestCorsLoopbackGate:
    def test_cors_allowed_origins_excludes_loopback_when_debug_false(self):
        result = _run(
            "import config.settings.corsheaders as c; "
            "import json; print(json.dumps(c.CORS_ALLOWED_ORIGINS))",
            {"DEBUG": "False"},
        )

        assert result.returncode == 0, result.stderr
        origins = json.loads(result.stdout)
        assert not any("localhost" in o or "127.0.0.1" in o for o in origins)

    def test_cors_allowed_origins_includes_loopback_when_debug_true(self):
        result = _run(
            "import config.settings.corsheaders as c; "
            "import json; print(json.dumps(c.CORS_ALLOWED_ORIGINS))",
            {"DEBUG": "True"},
        )

        assert result.returncode == 0, result.stderr
        origins = json.loads(result.stdout)
        assert any("localhost" in o or "127.0.0.1" in o for o in origins)
