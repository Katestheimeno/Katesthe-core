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
from config.logger import logger

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
        logger.debug(f"Email validation: {value}")
        return value.lower()

    def validate_username(self, value):
        """Custom username validation if needed."""
        logger.debug(f"Username validation: {value}")
        return value.lower()

    def create(self, validated_data):
        """Create user with logging."""
        logger.info(f"Creating new user with username: {validated_data.get('username')}, email: {validated_data.get('email')}")
        user = super().create(validated_data)
        logger.info(f"User created successfully: user_id={user.id}, username={user.username}")
        return user

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

    def validate_current_password(self, value):
        """Validate current password with logging."""
        user = self.context['request'].user
        logger.info(f"Password validation for user deletion: user_id={user.id}, username={user.username}")
        
        if not user.check_password(value):
            logger.warning(f"Invalid password for user deletion: user_id={user.id}, username={user.username}")
            raise serializers.ValidationError("Invalid password.")
        
        logger.debug(f"Password validation successful for user deletion: user_id={user.id}")
        return value

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

    def to_representation(self, instance):
        """Log user data access."""
        logger.debug(f"User data accessed: user_id={instance.id}, username={instance.username}")
        return super().to_representation(instance)

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

    def to_representation(self, instance):
        """Log current user profile access."""
        logger.debug(f"Current user profile accessed: user_id={instance.id}, username={instance.username}")
        return super().to_representation(instance)

    def update(self, instance, validated_data):
        """Custom update logic for current user with logging."""
        logger.info(f"Current user profile update: user_id={instance.id}, username={instance.username}")
        
        # Handle email changes - you might want to re-verify email
        if 'email' in validated_data and validated_data['email'] != instance.email:
            old_email = instance.email
            new_email = validated_data['email']
            logger.info(f"Email change detected: user_id={instance.id}, old_email={old_email}, new_email={new_email}")
            instance.is_verified = False

        updated_user = super().update(instance, validated_data)
        logger.info(f"Current user profile updated successfully: user_id={updated_user.id}, username={updated_user.username}")
        return updated_user


__all__ = imports
