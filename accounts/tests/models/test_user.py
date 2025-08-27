"""
Tests for User model and related functionality.
Path: accounts/tests/models/test_user.py
"""

import pytest
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.db import IntegrityError
from django.utils import timezone
from accounts.tests.factories import (
    UserFactory, 
    InactiveUserFactory, 
    UnverifiedUserFactory
)

User = get_user_model()


class TestUserModel:
    """Test User model functionality."""
    
    @pytest.mark.django_db
    def test_user_creation(self):
        """Test basic user creation."""
        user = UserFactory()
        
        assert user.username is not None
        assert user.email is not None
        assert user.is_active is True  # Factory sets this to True
        assert user.is_verified is True  # Factory sets this to True
        assert user.is_staff is False
        assert user.is_superuser is False
    
    @pytest.mark.django_db
    def test_user_string_representation(self):
        """Test user string representation."""
        user = UserFactory()
        
        # The string representation should be the username
        assert str(user) == user.username
    
    @pytest.mark.django_db
    def test_user_manager_create_user(self):
        """Test custom user manager create_user method."""
        user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        assert user.username == 'testuser'
        assert user.email == 'test@example.com'
        assert user.is_active is False  # Model default is False
        assert user.is_staff is False
        assert user.is_superuser is False
        assert user.check_password('testpass123')
    
    @pytest.mark.django_db
    def test_user_manager_create_superuser(self):
        """Test custom user manager create_superuser method."""
        user = User.objects.create_superuser(
            username='adminuser',
            email='admin@example.com',
            password='adminpass123'
        )
        
        assert user.username == 'adminuser'
        assert user.email == 'admin@example.com'
        assert user.is_active is True  # Superuser sets this to True
        assert user.is_staff is True
        assert user.is_superuser is True
        assert user.check_password('adminpass123')
    
    @pytest.mark.django_db
    def test_user_unique_username(self):
        """Test that username must be unique."""
        UserFactory(username='uniqueuser')
        
        # Try to create another user with the same username
        with pytest.raises(IntegrityError):
            UserFactory(username='uniqueuser')
    
    @pytest.mark.django_db
    def test_user_unique_email(self):
        """Test that email must be unique."""
        UserFactory(email='unique@example.com')
        
        # Try to create another user with the same email
        with pytest.raises(IntegrityError):
            UserFactory(email='unique@example.com')
    
    @pytest.mark.django_db
    def test_user_email_normalization(self):
        """Test that email is normalized to lowercase when using manager."""
        # Test normalization through the manager (not factory)
        user = User.objects.create_user(
            username='testuser',
            email='TEST@EXAMPLE.COM',
            password='testpass123'
        )
        
        # Only the domain part should be normalized to lowercase
        assert user.email == 'TEST@example.com'
    
    @pytest.mark.django_db
    def test_user_ordering(self):
        """Test that users are ordered by date_joined descending."""
        user1 = UserFactory()
        user2 = UserFactory()
        
        # Get users in default ordering
        users = User.objects.all()
        
        # Should be ordered by date_joined descending (newest first)
        assert users[0].date_joined >= users[1].date_joined


class TestUserStatus:
    """Test user status-related functionality."""
    
    @pytest.mark.django_db
    def test_inactive_user(self):
        """Test inactive user creation and properties."""
        user = InactiveUserFactory()
        
        assert user.is_active is False
        assert user.is_verified is True  # Can be verified but inactive
    
    @pytest.mark.django_db
    def test_unverified_user(self):
        """Test unverified user creation and properties."""
        user = UnverifiedUserFactory()
        
        assert user.is_active is True
        assert user.is_verified is False
    
    @pytest.mark.django_db
    def test_user_activation(self):
        """Test user activation process."""
        user = InactiveUserFactory()
        
        # Activate the user
        user.is_active = True
        user.save()
        
        user.refresh_from_db()
        assert user.is_active is True
    
    @pytest.mark.django_db
    def test_user_verification(self):
        """Test user verification process."""
        user = UnverifiedUserFactory()
        
        # Verify the user
        user.is_verified = True
        user.save()
        
        user.refresh_from_db()
        assert user.is_verified is True


class TestUserTimestamps:
    """Test user timestamp functionality."""
    
    @pytest.mark.django_db
    def test_user_date_joined_auto_set(self):
        """Test that date_joined is automatically set."""
        user = UserFactory()
        
        assert user.date_joined is not None
        assert isinstance(user.date_joined, timezone.datetime)
    
    @pytest.mark.django_db
    def test_user_updated_at_auto_update(self):
        """Test that updated_at is automatically updated."""
        user = UserFactory()
        original_updated_at = user.updated_at
        
        # Update the user
        user.username = 'newusername'
        user.save()
        
        user.refresh_from_db()
        assert user.updated_at > original_updated_at
    
    @pytest.mark.django_db
    def test_user_last_login_manual_set(self):
        """Test that last_login can be manually set."""
        user = UserFactory()
        now = timezone.now()
        
        # Set last_login
        user.last_login = now
        user.save()
        
        user.refresh_from_db()
        assert user.last_login == now


class TestUserManagerErrors:
    """Test user manager error cases."""
    
    @pytest.mark.django_db
    def test_create_user_without_email(self):
        """Test that creating a user without email raises an error."""
        with pytest.raises(ValueError, match="You must provide an email address"):
            User.objects.create_user(
                username='testuser',
                email='',
                password='testpass123'
            )
    
    @pytest.mark.django_db
    def test_create_user_without_username(self):
        """Test that creating a user without username raises an error."""
        with pytest.raises(ValueError, match="You must provide a username"):
            User.objects.create_user(
                username='',
                email='test@example.com',
                password='testpass123'
            )
    
    @pytest.mark.django_db
    def test_create_superuser_invalid_staff_flag(self):
        """Test that creating superuser with invalid staff flag raises error."""
        with pytest.raises(ValueError, match="Superuser must be assigned to is_staff=True"):
            User.objects.create_superuser(
                username='admin',
                email='admin@example.com',
                password='adminpass123',
                is_staff=False
            )
    
    @pytest.mark.django_db
    def test_create_superuser_invalid_superuser_flag(self):
        """Test that creating superuser with invalid superuser flag raises error."""
        with pytest.raises(ValueError, match="Superuser must be assigned to is_superuser=True"):
            User.objects.create_superuser(
                username='admin',
                email='admin@example.com',
                password='adminpass123',
                is_superuser=False
            )
