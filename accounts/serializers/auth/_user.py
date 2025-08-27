"""
Custom authentication serializers for Djoser integration.
Path: accounts/serializers/auth.py
"""

from rest_framework import serializers
from djoser.serializers import (
    UserCreateSerializer as DjoserUserCreateSerializer, 
    UserSerializer as DjoserUserSerializer,
    UserDeleteSerializer as DjoserUserDeleteSerializer
)
from django.contrib.auth import get_user_model

User = get_user_model()

imports = []



imports += ["UserCreateSerializer"]

class UserCreateSerializer(DjoserUserCreateSerializer):
    """
    Custom user creation serializer.
    Extends Djoser's base serializer with any custom fields or validation.
    """

    class Meta(DjoserUserCreateSerializer.Meta):
        model = User
        fields = ('id', 'username', 'email', 'password')
        extra_kwargs = {
            'password': {'write_only': True}
        }

    def validate_email(self, value):
        """Custom email validation if needed."""
        return value.lower()

    def validate_username(self, value):
        """Custom username validation if needed."""
        return value.lower()

imports += ["UserDeleteSerializer"]
class UserDeleteSerializer(DjoserUserDeleteSerializer):
    """
    Custom user deletion serializer.
    Properly handles the current_password field for Swagger documentation.
    """
    
    current_password = serializers.CharField(
        write_only=True,
        required=True,
        help_text="Current password is required to delete the account"
    )

    class Meta:
        model = User
        fields = ('current_password',)

imports += ["UserSerializer"]
class UserSerializer(DjoserUserSerializer):
    """
    General user serializer for admin views and general use.
    """

    class Meta(DjoserUserSerializer.Meta):
        model = User
        fields = (
            'id',
            'username',
            'email',
            'is_active',
            'is_staff',
            'is_verified',
            'date_joined',
            'last_login',
            'updated_at'
        )
        read_only_fields = ('id', 'date_joined', 'last_login', 'updated_at')

imports += ["CurrentUserSerializer"]
class CurrentUserSerializer(DjoserUserSerializer):
    """
    Serializer for /me endpoint (current authenticated user).
    Can include additional fields that only the user themselves should see.
    """

    class Meta(DjoserUserSerializer.Meta):
        model = User
        fields = (
            'id',
            'username',
            'email',
            'is_active',
            'is_verified',
            'date_joined',
            'last_login',
            'updated_at'
        )
        read_only_fields = ('id', 'is_active', 'date_joined',
                            'last_login', 'updated_at')

    def update(self, instance, validated_data):
        """Custom update logic for current user."""
        # Handle email changes - you might want to re-verify email
        if 'email' in validated_data and validated_data['email'] != instance.email:
            instance.is_verified = False

        return super().update(instance, validated_data)


__all__ = imports
