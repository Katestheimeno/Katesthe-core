"""
Tests for User admin configuration.
Path: accounts/tests/admin/test_user_admin.py
"""

import pytest
from django.contrib import admin
from django.contrib.admin.sites import AdminSite
from django.test import TestCase
from django.core.exceptions import PermissionDenied
from accounts.admin import UserAdmin
from accounts.models import User
from accounts.tests.factories import UserFactory


class TestUserAdmin:
    """Test UserAdmin configuration."""
    
    @pytest.mark.django_db
    def test_user_admin_list_display(self):
        """Test that UserAdmin has correct list_display."""
        admin = UserAdmin(UserFactory(), AdminSite())
        
        expected_fields = ['id', 'username', 'email', 'is_active', 'is_verified', 'is_staff', 'date_joined']
        for field in expected_fields:
            assert field in admin.list_display
    
    @pytest.mark.django_db
    def test_user_admin_list_filter(self):
        """Test that UserAdmin has correct list_filter."""
        admin = UserAdmin(UserFactory(), AdminSite())
        
        expected_filters = ['is_active', 'is_verified', 'is_staff', 'is_superuser', 'date_joined']
        for filter_field in expected_filters:
            assert filter_field in admin.list_filter
    
    @pytest.mark.django_db
    def test_user_admin_search_fields(self):
        """Test that UserAdmin has correct search_fields."""
        admin = UserAdmin(UserFactory(), AdminSite())
        
        expected_search_fields = ['username', 'email']
        for search_field in expected_search_fields:
            assert search_field in admin.search_fields
    
    @pytest.mark.django_db
    def test_user_admin_ordering(self):
        """Test that UserAdmin has correct ordering."""
        admin = UserAdmin(UserFactory(), AdminSite())
        
        # ordering is a tuple, not a list
        assert admin.ordering == ('-date_joined',)
    
    @pytest.mark.django_db
    def test_user_admin_readonly_fields(self):
        """Test that UserAdmin has correct readonly_fields."""
        admin = UserAdmin(UserFactory(), AdminSite())
        
        expected_readonly = ['date_joined', 'last_login', 'updated_at']
        for readonly_field in expected_readonly:
            assert readonly_field in admin.readonly_fields
    
    @pytest.mark.django_db
    def test_user_admin_fieldsets(self):
        """Test that UserAdmin has correct fieldsets."""
        admin = UserAdmin(UserFactory(), AdminSite())
        
        # Check that fieldsets are defined
        assert hasattr(admin, 'fieldsets')
        assert admin.fieldsets is not None
        
        # Check that required sections exist
        fieldset_titles = [fieldset[0] for fieldset in admin.fieldsets if fieldset[0] is not None]
        expected_sections = ['Status', 'Important dates', 'Permissions']
        
        for section in expected_sections:
            assert section in fieldset_titles
    
    @pytest.mark.django_db
    def test_user_admin_unfold_configuration(self):
        """Test that UserAdmin has Unfold-specific configuration."""
        admin = UserAdmin(UserFactory(), AdminSite())
        
        # Check for Unfold-specific attributes
        assert hasattr(admin, 'unfold_list_display')
        assert 'default_columns' in admin.unfold_list_display
        assert 'collapse_filters' in admin.unfold_list_display


class TestUserAdminIntegration(TestCase):
    """Integration tests for UserAdmin with Django admin site."""
    
    @pytest.mark.django_db
    def setUp(self):
        """Set up test data."""
        self.admin_site = AdminSite()
        self.user_admin = UserAdmin(User, self.admin_site)
        self.regular_user = UserFactory()
        self.staff_user = UserFactory(is_staff=True)
    
    @pytest.mark.django_db
    def test_user_admin_registration(self):
        """Test that UserAdmin is properly registered."""
        # Check that UserAdmin is registered
        assert User in admin.site._registry
        
        # Check that it's registered with the correct admin class
        registered_admin = admin.site._registry[User]
        assert isinstance(registered_admin, UserAdmin)
    
    @pytest.mark.django_db
    def test_user_admin_list_view_fields(self):
        """Test that list view displays correct fields."""
        # Create a request and get the changelist view
        from django.test import RequestFactory
        from django.contrib.auth.models import AnonymousUser
        
        request = RequestFactory().get('/admin/accounts/user/')
        request.user = AnonymousUser()
        
        # Get the changelist view - expect PermissionDenied for anonymous user
        with pytest.raises(PermissionDenied):
            self.user_admin.changelist_view(request)
    
    @pytest.mark.django_db
    def test_user_admin_search_functionality(self):
        """Test that search functionality works."""
        # Create users with different usernames
        user1 = UserFactory(username='testuser1')
        user2 = UserFactory(username='testuser2')
        
        # Test search by username
        queryset, use_distinct = self.user_admin.get_search_results(None, User.objects.all(), 'testuser1')
        assert user1 in queryset
        assert user2 not in queryset
    
    @pytest.mark.django_db
    def test_user_admin_filter_functionality(self):
        """Test that filter functionality works."""
        # Create users with different statuses
        active_user = UserFactory(is_active=True)
        inactive_user = UserFactory(is_active=False)
        
        # Test filter by is_active
        queryset = self.user_admin.get_queryset(None)
        active_users = queryset.filter(is_active=True)
        
        assert active_user in active_users
        assert inactive_user not in active_users
    
    @pytest.mark.django_db
    def test_user_admin_readonly_functionality(self):
        """Test that readonly fields are properly handled."""
        # Check that readonly fields are set
        readonly_fields = self.user_admin.get_readonly_fields(None, self.regular_user)
        
        expected_readonly = ['date_joined', 'last_login', 'updated_at']
        for field in expected_readonly:
            assert field in readonly_fields
    
    @pytest.mark.django_db
    def test_user_string_representation_in_admin(self):
        """Test that user string representation works in admin."""
        # The string representation should be the username
        assert str(self.regular_user) == self.regular_user.username
