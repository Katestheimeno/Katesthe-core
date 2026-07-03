"""
Custom JWT token serializers for authentication.
Path: accounts/serializers/token.py
"""

from rest_framework_simplejwt.serializers import (
    TokenObtainPairSerializer,
    TokenRefreshSerializer,
)
from rest_framework import serializers
from django.contrib.auth import authenticate
from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import check_password
from accounts.tokens import KidRefreshToken
from config.logger import logger

User = get_user_model()

# Valid-format dummy encoded hash used to burn a real hash computation when no
# user matches the submitted credentials (timing-oracle defence). The value
# itself is never a real password hash — only its format matters so that
# check_password() runs the full pbkdf2_sha256 iteration count.
_DUMMY_PASSWORD_HASH = (
    "pbkdf2_sha256$720000$dummy$0000000000000000000000000000000000000000000="
)

imports = []


imports += ["CustomTokenObtainPairSerializer", "KidTokenRefreshSerializer"]


class KidTokenRefreshSerializer(TokenRefreshSerializer):
    """
    Override the default refresh serializer to use KidRefreshToken so that
    rotated tokens (and the derived access tokens) include the ``kid``
    header required for JWKS-based verification.
    """
    token_class = KidRefreshToken


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    """
    Custom JWT token serializer that handles both username and email login.
    Extends SimpleJWT's TokenObtainPairSerializer with custom claims.
    """
    token_class = KidRefreshToken

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
        logger.debug(f"Generating JWT token for user_id={user.id}, username={user.username}")
        token = super().get_token(user)

        # Add custom claims
        token['username'] = user.username
        token['email'] = user.email
        token['is_verified'] = user.is_verified
        token['is_staff'] = user.is_staff

        # SEC-001: is_superuser intentionally NOT in the JWT — check server-side.
        if user.is_superuser:
            token["permissions"] = ["system_admin"]
        elif user.is_staff:
            token["permissions"] = list(user.user_permissions.values_list("codename", flat=True))
        else:
            token["permissions"] = []

        logger.debug(f"JWT token generated with claims for user_id={user.id}")
        return token

    def validate(self, attrs):
        """
        Custom validation to allow login with either username or email.
        """
        username_or_email = attrs.get('username')
        password = attrs.get('password')

        logger.info(f"Token validation attempt for username/email: {username_or_email}")

        if not username_or_email or not password:
            logger.warning(f"Token validation failed - missing credentials for: {username_or_email}")
            raise serializers.ValidationError(
                'Must include username/email and password.')

        # Try to find user by username first, then by email
        user = None
        try:
            # First try username
            user = User.objects.get(username=username_or_email)
            logger.debug(f"User found by username: user_id={user.id}, username={user.username}")
        except User.DoesNotExist:
            try:
                # Then try email
                user = User.objects.get(email=username_or_email)
                logger.debug(f"User found by email: user_id={user.id}, username={user.username}")
            except User.DoesNotExist:
                logger.warning(f"User not found for username/email: {username_or_email}")
                pass

        if user is None:
            # Burn a real password hash computation so the not-found branch
            # takes the same time as a real password check (timing-oracle
            # defence) — otherwise response latency leaks account existence.
            check_password(password, _DUMMY_PASSWORD_HASH)
            logger.warning(f"Token validation failed - user not found: {username_or_email}")
            raise serializers.ValidationError(
                'No user found with this username or email.')

        # Check if user is active
        if not user.is_active:
            # Same timing-oracle defence as the not-found branch above.
            check_password(password, _DUMMY_PASSWORD_HASH)
            logger.warning(f"Token validation failed - inactive user: user_id={user.id}, username={user.username}")
            raise serializers.ValidationError('User account is disabled.')

        # Authenticate with the found user's username (since that's what Django expects)
        authenticated_user = authenticate(
            request=self.context.get('request'),
            username=user.username,  # Use the actual username for authentication
            password=password
        )

        if authenticated_user is None:
            logger.warning(f"Token validation failed - invalid credentials for user_id={user.id}, username={user.username}")
            raise serializers.ValidationError('Invalid credentials.')

        logger.info(f"Token validation successful for user_id={authenticated_user.id}, username={authenticated_user.username}")

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