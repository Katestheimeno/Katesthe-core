"""
Basic tests to verify test setup is working.
Path: accounts/tests/test_basic.py
"""

import pytest
from django.test import TestCase
from django.contrib.auth import get_user_model
from accounts.tests.factories import UserFactory

User = get_user_model()


class TestBasicSetup:
    """Basic tests to verify the test environment is working."""
    
    def test_django_is_configured(self):
        """Test that Django is properly configured."""
        from django.conf import settings
        assert settings.DEBUG is not None
    
    @pytest.mark.django_db
    def test_user_factory_works(self):
        """Test that the UserFactory works correctly."""
        user = UserFactory()
        assert user.username is not None
        assert user.email is not None
        assert user.is_active is True
    
    @pytest.mark.django_db
    def test_database_connection(self):
        """Test that database connection works."""
        user = UserFactory()
        user.save()
        
        # Try to retrieve the user
        retrieved_user = User.objects.get(id=user.id)
        assert retrieved_user.username == user.username


class TestBasicTestCase(TestCase):
    """Test that Django TestCase works."""
    
    def test_django_testcase_works(self):
        """Test that Django TestCase is working."""
        user = UserFactory()
        self.assertEqual(user.username, user.username)
    
    def test_database_operations(self):
        """Test basic database operations."""
        user = UserFactory()
        user.save()
        
        # Count users
        user_count = User.objects.count()
        self.assertGreater(user_count, 0)
        
        # Get user by username
        retrieved_user = User.objects.get(username=user.username)
        self.assertEqual(retrieved_user.email, user.email)
