"""
Pytest configuration and fixtures for accounts app tests.
Path: accounts/tests/conftest.py
"""

import os
import pytest
import django

# Configure Django settings before importing any Django components
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.django.test')

django.setup()

from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken
from accounts.tests.factories import UserFactory, SuperUserFactory

User = get_user_model()


@pytest.fixture
def api_client():
    """Return an API client for testing."""
    return APIClient()


@pytest.fixture
def user():
    """Return a regular user for testing."""
    return UserFactory()


@pytest.fixture
def inactive_user():
    """Return an inactive user for testing."""
    return UserFactory(is_active=False)


@pytest.fixture
def unverified_user():
    """Return an unverified user for testing."""
    return UserFactory(is_verified=False)


@pytest.fixture
def staff_user():
    """Return a staff user for testing."""
    return UserFactory(is_staff=True)


@pytest.fixture
def superuser():
    """Return a superuser for testing."""
    return SuperUserFactory()


@pytest.fixture
def authenticated_client(api_client, user):
    """Return an authenticated API client."""
    refresh = RefreshToken.for_user(user)
    api_client.credentials(HTTP_AUTHORIZATION=f'Bearer {refresh.access_token}')
    return api_client


@pytest.fixture
def staff_client(api_client, staff_user):
    """Return an authenticated API client with staff user."""
    refresh = RefreshToken.for_user(staff_user)
    api_client.credentials(HTTP_AUTHORIZATION=f'Bearer {refresh.access_token}')
    return api_client


@pytest.fixture
def superuser_client(api_client, superuser):
    """Return an authenticated API client with superuser."""
    refresh = RefreshToken.for_user(superuser)
    api_client.credentials(HTTP_AUTHORIZATION=f'Bearer {refresh.access_token}')
    return api_client


@pytest.fixture
def user_tokens(user):
    """Return JWT tokens for a user."""
    refresh = RefreshToken.for_user(user)
    return {
        'access': str(refresh.access_token),
        'refresh': str(refresh),
    }


@pytest.fixture
def staff_tokens(staff_user):
    """Return JWT tokens for a staff user."""
    refresh = RefreshToken.for_user(staff_user)
    return {
        'access': str(refresh.access_token),
        'refresh': str(refresh),
    }
