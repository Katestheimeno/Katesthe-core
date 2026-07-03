"""
Tests for the JWT RS256 boot-time enforcement in config/django/production.py.

Mirrors config/tests/test_production_settings.py: `production.py` runs its
assertions at *import* time (`django.setup()`), so the only reliable way to
exercise both the success and failure paths is a real subprocess with a
controlled environment.
"""

import os
import subprocess
import sys
from pathlib import Path

import pytest

pytestmark = pytest.mark.slow

REPO_ROOT = Path(__file__).resolve().parent.parent.parent

# Note: BASE_ENV sets JWT_SECRET_KEY (legacy HS256 secret) but intentionally
# does NOT set JWT_RSA_PRIVATE_KEY, so the RS256 enforcement fires unless a
# test overrides it.
BASE_ENV = {
    "SECRET_KEY": "test-secret-key-for-subprocess-only",
    "JWT_SECRET_KEY": "test-jwt-secret-key-for-subprocess-only",
    "DJANGO_ENV": "",
}

# A real (test-only) base64-encoded PKCS8 PEM RSA private key. Needed because
# `config/settings/restframework.py` loads and parses `JWT_RSA_PRIVATE_KEY`
# during `config.settings` import (before production.py's own enforcement
# runs) — an arbitrary placeholder string would fail base64/PEM decoding
# with an unrelated error instead of exercising the enforcement block.
_TEST_RSA_PRIVATE_KEY_B64 = (
    "LS0tLS1CRUdJTiBQUklWQVRFIEtFWS0tLS0tCk1JSUV2Z0lCQURBTkJna3Foa2lHOXcwQkFRRUZBQVND"
    "Qktnd2dnU2tBZ0VBQW9JQkFRRHh1b1QwWThadWI2U0EKQ1pzaEM4V2RicENramJIVDArblNIVWJadGwr"
    "Q0ZQU0ZjUHNDSTlKUHFhOG1QTFI5Z1FSOVE3V3pmaS9GZG1hegovRWtlYTZZblViV3VvK2lMTmI5TWZa"
    "M293SnFMN1VrVi9SSUZKelhac2ZVamZxMFE3QUlVMGkyc0FNSWpzSVgvCkJsS3VlWFpDOStwZ21yK3pH"
    "U3F3eW4xcnN2bzQ0UG8vY3NBTUNON2lZYldjWEp4WXJyc2huK2JCdVFYcTFZeW4KcGJBU2hPYzR1bXRi"
    "TURRMlJhOXVIOTFPMGRzRUxrTlZTNFNwSGl5NXVNc1RDVnVjeSs5cGovc29xUXU1S0lkeQo5eS9Mc2Jr"
    "Rmw1MG0yUzFoblVjSzJidHZrM1IvWXBEVWZrL2VXWWJIT2JiNWIyVnpUMk9SQ0lLUWp3WnMyaERnCmNt"
    "ZlNqbnRGQWdNQkFBRUNnZ0VBRUtDZjNKK3dXcEJiWkdORXhIVW0xcmx3UWFGdGhnQ2hxTTVTdlU4S0tz"
    "eCsKTlYrY0pIMktUZWlDSDhNMU54elV6amtHR3A2bmNwRytac3NIekl2akZmbE00Z0pzVUljVjdaRUdk"
    "NmduK1ZBTgpJdklSZDBGSE52NUN1bnBRTlVYR3J0LzJQRXFoRUF0b2JDNW5LWkU1VFVuNFdVVEx3dW9N"
    "UWJUc0E2aUFCY0Z4CnU3WWlMRjVUVHRUU082VndvbkJZNkx4NVJTaTFSOHRBYkpNZURvQ2NXNi9uT3px"
    "MkcwVG5tbi9DNDFoR3pFU1cKUmRHZFhCdURFdnZ3S3phaytVR1lQSXdXbG1JR1hOeWFtdDdGc1VQTE4z"
    "eEgwc09CbDd3Umw3RU1MN3VHREFaQgpmT0xnQVpMcG40OGltWEpHTURBVkJFK0QyZ3ZBOWYydThaZzU4"
    "OEQ5QVFLQmdRRDdWOE9Ka0V3SWVMM25vZFE5Cjc4eUd1RDZKWVZGakJtcXZNbFBCaGVCR0dKMGNJNnBN"
    "bE81Mmd1R0pJV0Z0bWdVdWxOd3BHTTNLcnBLR3NpaWkKb2NoMldHNFhRNHJxaGhWUUtyOWVuTStRbEhi"
    "L3ozYld6T1hONjJkSUNmRC9WaEprVkJ1dStmQm5DZll0WFVCaQptTWRzUyt6NTZocmFSWXE5dkh3RzhY"
    "WWg4UUtCZ1FEMk5TYVdiU3Z1NFIxRk5PM2p3VENiN21tbnlpVXJZY1psCkUrWGlwVUJMQkoxQjNUdkhD"
    "UHBobk9tRnYxRnB2OVRrQVMzOEQreDdrZWdUWEtFY0JqbXRhdGJBaTgveWVEQVkKTVRLUGlNQkk5eXpy"
    "aVNzZXZxVTV3dGl0REp1S3hEYWxuMEhlTXB5N3B2VzZwRSs5NHdpeFNQQmRvVUJ3TXpMZwpzbThGa0w1"
    "YWxRS0JnUURIRFFSZ3A1UnZpUi9zbDY3OHRqS2w1cmd3R0pCWitqVDNOc1k2RndvOHVUV0RtWU0vClR4"
    "dGpZOWUxd0dmbVl2b0RvQVNUejM3N0t6SUQxb2h6OCtoTVFWQSt3RkQ5MXQ1K05MeUY4MjQydEQxaDdp"
    "M1IKZzBmandyQnl6dHk3ZXJEcUgrb2tzdkIreWRiYXFtVlpNR0dQRkxwQ1dmS1dOa2pnWnF0YTNGT1FJ"
    "UUtCZ0ExNAp4dzNBRjRGUXJBdFhaQlRzUXo2bEF2NzlYcDlMRUZJRGpyYWlHQ3lDcWlBcWZOVGROdVlV"
    "Y2VxeGwwRFVFRkFSCmlIU2NZbkk0ZjV4Zm15a3ZaZ1NKTGdzSEcyL0hCOHFyRm5zb0htMWZxUU9TVTl1"
    "d3p0V2tSYnJpVDdoK0dBZGoKK1hTeERFWndVazNPSTliZUQyR3ovZ01CaWNjWjVoVEpicTI5UjgwcEFv"
    "R0JBSkdNNlJuZTNFWVRkRXpZdkZTagplUnFMcko4MDVEcUZUdVZlQVFtejJyb0hwZC9xVEtVWHdOemZL"
    "NGU4ellFbndqbitDM25kYVZ5UmVKZVFHYTN0CndLZjVOR0tvZ2NKMm5rUktOQ3EyVmJxalplSXladGJ4"
    "U2I4dDBlelRYVnVxV3FRa1ViU3VJM2U4VElxakdCRXQKN2hzV3lxMCs1dDUxSXlLZlNUaUVQZnpaCi0t"
    "LS0tRU5EIFBSSVZBVEUgS0VZLS0tLS0K"
)


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


class TestProductionJwtEnforcement:
    def test_boot_raises_improperly_configured_when_jwt_rsa_private_key_missing(self):
        result = _run(
            "import django; django.setup()",
            {
                "DJANGO_SETTINGS_MODULE": "config.django.production",
                "DEBUG": "False",
                "ALLOWED_HOSTS": "example.com",
            },
        )

        assert result.returncode != 0
        assert "ImproperlyConfigured" in result.stderr
        assert "JWT_RSA_PRIVATE_KEY is required in production" in result.stderr

    def test_boot_succeeds_when_jwt_rsa_private_key_and_issuer_are_set(self):
        result = _run(
            "import django; django.setup()",
            {
                "DJANGO_SETTINGS_MODULE": "config.django.production",
                "DEBUG": "False",
                "ALLOWED_HOSTS": "example.com",
                "JWT_RSA_PRIVATE_KEY": _TEST_RSA_PRIVATE_KEY_B64,
                "JWT_ISSUER": "https://example.com",
            },
        )

        assert result.returncode == 0, result.stderr

    def test_boot_warns_but_does_not_crash_when_jwt_issuer_missing(self):
        result = _run(
            "import warnings; import django; "
            "warnings.simplefilter('always'); django.setup()",
            {
                "DJANGO_SETTINGS_MODULE": "config.django.production",
                "DEBUG": "False",
                "ALLOWED_HOSTS": "example.com",
                "JWT_RSA_PRIVATE_KEY": _TEST_RSA_PRIVATE_KEY_B64,
            },
        )

        assert result.returncode == 0, result.stderr
        assert "JWT_ISSUER not set" in result.stderr
