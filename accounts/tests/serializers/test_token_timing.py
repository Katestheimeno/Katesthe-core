"""
Tests for the timing-oracle defence in CustomTokenObtainPairSerializer.validate().
Path: accounts/tests/serializers/test_token_timing.py
"""

from unittest.mock import patch

import pytest
from rest_framework import serializers
from rest_framework.test import APIRequestFactory

from accounts.serializers.auth import CustomTokenObtainPairSerializer
from accounts.serializers.auth._token import _DUMMY_PASSWORD_HASH
from accounts.tests.factories import InactiveUserFactory, UserFactory


class TestTokenTimingOracleDefense:
    """Verify a dummy password hash is burned when credentials do not resolve to an active user."""

    @pytest.mark.django_db
    def test_dummy_check_password_runs_when_username_does_not_exist(self):
        """A non-existent username still triggers a real hash computation."""
        factory = APIRequestFactory()
        request = factory.post('/')

        serializer = CustomTokenObtainPairSerializer(context={'request': request})

        with patch('accounts.serializers.auth._token.check_password') as mocked_check_password:
            with pytest.raises(serializers.ValidationError):
                serializer.validate({
                    'username': 'no-such-user',
                    'password': 'irrelevant-password',
                })

        mocked_check_password.assert_called_once_with(
            'irrelevant-password', _DUMMY_PASSWORD_HASH,
        )

    @pytest.mark.django_db
    def test_dummy_check_password_runs_when_email_does_not_exist(self):
        """A non-existent email still triggers a real hash computation."""
        factory = APIRequestFactory()
        request = factory.post('/')

        serializer = CustomTokenObtainPairSerializer(context={'request': request})

        with patch('accounts.serializers.auth._token.check_password') as mocked_check_password:
            with pytest.raises(serializers.ValidationError):
                serializer.validate({
                    'username': 'no-such-user@example.com',
                    'password': 'irrelevant-password',
                })

        mocked_check_password.assert_called_once()

    @pytest.mark.django_db
    def test_dummy_check_password_runs_for_inactive_user(self):
        """An inactive user's login attempt still burns a dummy hash check."""
        user = InactiveUserFactory()
        factory = APIRequestFactory()
        request = factory.post('/')

        serializer = CustomTokenObtainPairSerializer(context={'request': request})

        with patch('accounts.serializers.auth._token.check_password') as mocked_check_password:
            with pytest.raises(serializers.ValidationError):
                serializer.validate({
                    'username': user.username,
                    'password': 'testpass123',
                })

        mocked_check_password.assert_called_once()

    @pytest.mark.django_db
    def test_user_not_found_error_is_unchanged(self):
        """The not-found branch still raises the same error contract as before."""
        factory = APIRequestFactory()
        request = factory.post('/')

        serializer = CustomTokenObtainPairSerializer(context={'request': request})

        with pytest.raises(serializers.ValidationError) as exc_info:
            serializer.validate({
                'username': 'no-such-user',
                'password': 'irrelevant-password',
            })

        assert 'No user found with this username or email.' in str(exc_info.value)

    @pytest.mark.django_db
    def test_inactive_user_error_is_unchanged(self):
        """The inactive-user branch still raises the same error contract as before."""
        user = InactiveUserFactory()
        factory = APIRequestFactory()
        request = factory.post('/')

        serializer = CustomTokenObtainPairSerializer(context={'request': request})

        with pytest.raises(serializers.ValidationError) as exc_info:
            serializer.validate({
                'username': user.username,
                'password': 'testpass123',
            })

        assert 'User account is disabled.' in str(exc_info.value)

    @pytest.mark.django_db
    def test_valid_credentials_still_authenticate_successfully(self):
        """A real user with the correct password still authenticates and gets a token pair."""
        user = UserFactory()
        # UserFactory declares `skip_postgeneration_save = True`, so the
        # `set_password` post-generation hook never persists to the DB.
        # Save explicitly here so `authenticate()` can find the hashed
        # password — this is a pre-existing factory quirk unrelated to the
        # timing-oracle defence under test, worked around locally rather
        # than touching the shared factory (owned elsewhere).
        user.set_password('testpass123')
        user.save(update_fields=['password'])

        factory = APIRequestFactory()
        request = factory.post('/')

        serializer = CustomTokenObtainPairSerializer(context={'request': request})

        result = serializer.validate({
            'username': user.username,
            'password': 'testpass123',
        })

        assert 'access' in result
        assert 'refresh' in result
        assert result['user']['id'] == user.id
