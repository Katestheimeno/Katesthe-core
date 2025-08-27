"""
User factory for creating test user instances.
Path: accounts/tests/factories/_user.py
"""

import factory
from factory.django import DjangoModelFactory
from django.contrib.auth import get_user_model
from django.utils import timezone

User = get_user_model()


class UserFactory(DjangoModelFactory):
    """
    Factory for creating User instances for testing.
    """
    
    class Meta:
        model = User
        skip_postgeneration_save = True
    
    # Core fields
    username = factory.Sequence(lambda n: f'user{n}')
    email = factory.Sequence(lambda n: f'user{n}@example.com')
    password = factory.PostGenerationMethodCall('set_password', 'testpass123')
    
    # Status fields
    is_active = True
    is_staff = False
    is_superuser = False
    is_verified = True
    
    # Timestamps
    date_joined = factory.LazyFunction(timezone.now)
    last_login = None
    updated_at = factory.LazyFunction(timezone.now)


class InactiveUserFactory(UserFactory):
    """Factory for creating inactive users."""
    is_active = False


class UnverifiedUserFactory(UserFactory):
    """Factory for creating unverified users."""
    is_verified = False


class StaffUserFactory(UserFactory):
    """Factory for creating staff users."""
    is_staff = True


class SuperUserFactory(UserFactory):
    """Factory for creating superusers."""
    is_staff = True
    is_superuser = True
