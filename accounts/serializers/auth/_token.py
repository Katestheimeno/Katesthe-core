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
from django.contrib.auth.models import Permission
from django.db.models import Q
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
        bound_logger = logger.bind(user_id=user.id)
        bound_logger.debug("auth.jwt_token_generating")
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
            # Q(user=user): permissions assigned directly via user_permissions.
            # Q(group__user=user): permissions inherited from the user's groups.
            # Bare codenames are kept (not "app_label.codename") to match the
            # pre-existing claim shape — an additive-only API contract.
            token["permissions"] = list(
                Permission.objects.filter(Q(user=user) | Q(group__user=user))
                .distinct()
                .values_list("codename", flat=True)
            )
        else:
            token["permissions"] = []

        bound_logger.debug("auth.jwt_token_generated")
        return token

    def validate(self, attrs):
        """
        Custom validation to allow login with either username or email.
        """
        username_or_email = attrs.get('username')
        password = attrs.get('password')

        logger.info("auth.token_validate_attempt")

        if not username_or_email or not password:
            logger.warning("auth.token_validate_missing_credentials")
            raise serializers.ValidationError(
                'Must include username/email and password.')

        # Look up by username and by email independently (rather than
        # username-first-then-email) so a collision — one user's username
        # equal to a different user's email — is detected instead of
        # silently letting the username match win.
        username_match = User.objects.filter(username=username_or_email).first()
        email_match = User.objects.filter(email=username_or_email).first()

        if username_match and email_match and username_match.id != email_match.id:
            check_password(password, _DUMMY_PASSWORD_HASH)
            logger.warning("auth.token_validate_identifier_collision")
            raise serializers.ValidationError(
                'No user found with this username or email.')

        user = username_match or email_match

        if user is None:
            # Burn a real password hash computation so the not-found branch
            # takes the same time as a real password check (timing-oracle
            # defence) — otherwise response latency leaks account existence.
            check_password(password, _DUMMY_PASSWORD_HASH)
            logger.warning("auth.token_validate_user_not_found")
            raise serializers.ValidationError(
                'No user found with this username or email.')

        # Check if user is active
        if not user.is_active:
            # Same timing-oracle defence as the not-found branch above.
            check_password(password, _DUMMY_PASSWORD_HASH)
            logger.bind(user_id=user.id).warning("auth.token_validate_inactive_user")
            raise serializers.ValidationError('User account is disabled.')

        # Authenticate with the found user's username (since that's what Django expects)
        authenticated_user = authenticate(
            request=self.context.get('request'),
            username=user.username,  # Use the actual username for authentication
            password=password
        )

        if authenticated_user is None:
            logger.bind(user_id=user.id).warning("auth.token_validate_invalid_credentials")
            raise serializers.ValidationError('Invalid credentials.')

        logger.bind(user_id=authenticated_user.id).info("auth.token_validate_success")

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