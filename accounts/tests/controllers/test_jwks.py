"""
Tests for the public JWKS endpoint.
Path: accounts/tests/controllers/test_jwks.py
"""

import pytest
from django.conf import settings
from django.test import override_settings
from django.urls import reverse

from config.jwt_keys import compute_kid_from_public, generate_rsa_private_key


class TestJWKSView:
    """Test JWKSView functionality."""

    def test_jwks_endpoint_returns_200_unauthenticated(self, api_client):
        """Unauthenticated GET to the JWKS endpoint succeeds."""
        url = reverse('jwks')

        response = api_client.get(url)

        assert response.status_code == 200

    def test_jwks_endpoint_sets_cache_control_header(self, api_client):
        """Response advertises a public, hour-long cache lifetime."""
        url = reverse('jwks')

        response = api_client.get(url)

        assert response['Cache-Control'] == 'public, max-age=3600'

    def test_jwks_endpoint_body_has_keys_list(self, api_client):
        """Response body contains a `keys` list."""
        url = reverse('jwks')

        response = api_client.get(url)

        assert 'keys' in response.json()
        assert isinstance(response.json()['keys'], list)

    def test_jwks_first_key_kid_matches_settings_jwt_kid(self, api_client):
        """The first published key's kid matches the active signing kid."""
        url = reverse('jwks')

        response = api_client.get(url)

        first_key = response.json()['keys'][0]
        assert first_key['kid'] == settings.JWT_KID

    def test_jwks_first_key_contains_public_material_only(self, api_client):
        """Published key exposes `n`/`e` but never the private exponent `d`."""
        url = reverse('jwks')

        response = api_client.get(url)

        first_key = response.json()['keys'][0]
        assert 'n' in first_key
        assert 'e' in first_key
        assert 'd' not in first_key

    def test_jwks_endpoint_requires_no_authentication(self, api_client):
        """No Authorization header is needed — the view has no auth classes."""
        url = reverse('jwks')

        response = api_client.get(url)

        assert response.status_code != 401

    def test_jwks_returns_two_keys_during_rotation_window(self, api_client):
        """When a previous public key is configured, both keys are published."""
        previous_private_key = generate_rsa_private_key()
        previous_public_key = previous_private_key.public_key()
        previous_kid = compute_kid_from_public(previous_public_key)

        with override_settings(
            JWT_PREVIOUS_PUBLIC_KEY_OBJ=previous_public_key,
            JWT_PREVIOUS_KID=previous_kid,
        ):
            url = reverse('jwks')
            response = api_client.get(url)

        keys = response.json()['keys']
        assert len(keys) == 2
        assert {key['kid'] for key in keys} == {settings.JWT_KID, previous_kid}
