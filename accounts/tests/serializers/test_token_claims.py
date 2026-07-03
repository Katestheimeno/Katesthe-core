"""
Tests for custom JWT claims in CustomTokenObtainPairSerializer.get_token().
Path: accounts/tests/serializers/test_token_claims.py
"""

import pytest
from django.contrib.auth.models import Permission

from accounts.serializers.auth import CustomTokenObtainPairSerializer
from accounts.tests.factories import StaffUserFactory, SuperUserFactory, UserFactory


@pytest.mark.django_db
class TestTokenPermissionsClaim:
    """Verify the `permissions` claim is populated per role and `is_superuser` never leaks into the JWT."""

    def test_superuser_token_has_system_admin_permission(self):
        """A superuser's token gets a single `system_admin` sentinel permission."""
        user = SuperUserFactory()

        token = CustomTokenObtainPairSerializer.get_token(user)

        assert token["permissions"] == ["system_admin"]

    def test_superuser_token_does_not_expose_is_superuser_claim(self):
        """`is_superuser` must never appear in the JWT payload (SEC-001)."""
        user = SuperUserFactory()

        token = CustomTokenObtainPairSerializer.get_token(user)

        assert "is_superuser" not in token.payload

    def test_staff_user_token_contains_assigned_permission_codename(self):
        """A staff user's token lists the codenames of their assigned Django permissions."""
        user = StaffUserFactory()
        permission = Permission.objects.first()
        user.user_permissions.add(permission)

        token = CustomTokenObtainPairSerializer.get_token(user)

        assert permission.codename in token["permissions"]

    def test_regular_user_token_has_empty_permissions(self):
        """A non-staff, non-superuser user gets an empty permissions claim."""
        user = UserFactory()

        token = CustomTokenObtainPairSerializer.get_token(user)

        assert token["permissions"] == []

    def test_existing_claims_are_still_present(self):
        """The pre-existing username/email/is_verified/is_staff claims remain untouched."""
        user = UserFactory()

        token = CustomTokenObtainPairSerializer.get_token(user)

        assert token["username"] == user.username
        assert token["email"] == user.email
        assert token["is_verified"] == user.is_verified
        assert token["is_staff"] == user.is_staff
