"""
Tests for the generate_jwt_keys management command.
Path: accounts/tests/test_generate_jwt_keys.py
"""

import base64
from io import StringIO

from cryptography.hazmat.primitives.asymmetric import rsa
from django.core.management import call_command

from config.jwt_keys import load_rsa_private_key


class TestGenerateJwtKeysCommand:
    """Test the generate_jwt_keys management command."""

    def test_command_output_contains_jwt_rsa_private_key_line(self):
        """Command output includes a JWT_RSA_PRIVATE_KEY= line."""
        buf = StringIO()
        call_command("generate_jwt_keys", stdout=buf)

        output = buf.getvalue()

        assert "JWT_RSA_PRIVATE_KEY=" in output

    def test_command_output_key_roundtrips_to_valid_private_key(self):
        """The base64 value printed loads back into a valid RSA private key."""
        buf = StringIO()
        call_command("generate_jwt_keys", stdout=buf)

        output = buf.getvalue()
        key_line = next(
            line for line in output.splitlines() if line.startswith("JWT_RSA_PRIVATE_KEY=")
        )
        b64_value = key_line.split("=", 1)[1]

        # Sanity: value is valid base64.
        base64.b64decode(b64_value)

        loaded_key = load_rsa_private_key(b64_value)

        assert isinstance(loaded_key, rsa.RSAPrivateKey)
        assert loaded_key.key_size == 2048
