"""
Tests for accounts utils module.
Path: accounts/tests/test_utils.py
"""

import pytest
from django.test import RequestFactory
from accounts.utils import jwt_only_logout_user


class TestUtils:
    """Test utility functions."""
    
    def test_jwt_only_logout_user(self):
        """Test that jwt_only_logout_user does nothing (as expected)."""
        factory = RequestFactory()
        request = factory.post('/')
        
        # The function should not raise any exceptions and should do nothing
        result = jwt_only_logout_user(request)
        
        # Should return None (implicit return)
        assert result is None
    
    def test_jwt_only_logout_user_with_auth(self):
        """Test jwt_only_logout_user with authenticated request."""
        factory = RequestFactory()
        request = factory.post('/')
        
        # Mock an authenticated request
        request.user = type('User', (), {'id': 1, 'username': 'testuser'})()
        request.auth = type('Token', (), {'token': 'test-token'})()
        
        # Should still do nothing
        result = jwt_only_logout_user(request)
        assert result is None
    
    def test_jwt_only_logout_user_with_data(self):
        """Test jwt_only_logout_user with request data."""
        factory = RequestFactory()
        request = factory.post('/', data={'refresh_token': 'test-token'})
        
        # Should still do nothing regardless of request data
        result = jwt_only_logout_user(request)
        assert result is None
