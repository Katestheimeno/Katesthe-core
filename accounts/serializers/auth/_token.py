"""
Custom JWT token serializers for authentication.
Path: accounts/serializers/token.py
"""

from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework import serializers
from django.contrib.auth import authenticate
from django.contrib.auth import get_user_model

User = get_user_model()

imports = []


imports += ["CustomTokenObtainPairSerializer"]

class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    """
    Custom JWT token serializer that handles both username and email login.
    Extends SimpleJWT's TokenObtainPairSerializer with custom claims.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Change the username field label to be more generic
        self.fields['username'] = serializers.CharField(
            label='Username or Email',
            help_text='Enter your username or email address'
        )

    @classmethod
    def get_token(cls, user):
        """
        Add custom claims to the JWT token.
        """
        token = super().get_token(user)

        # Add custom claims
        token['username'] = user.username
        token['email'] = user.email
        token['is_verified'] = user.is_verified
        token['is_staff'] = user.is_staff

        return token

    def validate(self, attrs):
        """
        Custom validation to allow login with either username or email.
        """
        username_or_email = attrs.get('username')
        password = attrs.get('password')

        if not username_or_email or not password:
            raise serializers.ValidationError(
                'Must include username/email and password.')

        # Try to find user by username first, then by email
        user = None
        try:
            # First try username
            user = User.objects.get(username=username_or_email)
        except User.DoesNotExist:
            try:
                # Then try email
                user = User.objects.get(email=username_or_email)
            except User.DoesNotExist:
                pass

        if user is None:
            raise serializers.ValidationError(
                'No user found with this username or email.')

        # Check if user is active
        if not user.is_active:
            raise serializers.ValidationError('User account is disabled.')

        # Authenticate with the found user's username (since that's what Django expects)
        authenticated_user = authenticate(
            request=self.context.get('request'),
            username=user.username,  # Use the actual username for authentication
            password=password
        )

        if authenticated_user is None:
            raise serializers.ValidationError('Invalid credentials.')

        # Set the user for token generation
        attrs['user'] = authenticated_user

        # Get the token pair
        refresh = self.get_token(authenticated_user)

        return {
            'refresh': str(refresh),
            'access': str(refresh.access_token),
            'user': {
                'id': authenticated_user.id,
                'username': authenticated_user.username,
                'email': authenticated_user.email,
                'is_verified': authenticated_user.is_verified,
            }
        }


__all__ = imports