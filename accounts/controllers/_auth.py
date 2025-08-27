"""
Custom authentication views extending Djoser's functionality.
Path: accounts/views/auth.py
"""

from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response
from djoser import views as djoser_views
from djoser import utils
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.exceptions import TokenError
from django.contrib.auth import get_user_model

User = get_user_model()


class CustomUserViewSet(djoser_views.UserViewSet):
    """
    Custom User ViewSet that extends Djoser's UserViewSet.
    Handles user CRUD operations with JWT-specific logout logic.
    """

    def destroy(self, request, *args, **kwargs):
        """
        Custom user deletion that properly handles JWT tokens.
        Fixes the Token model error by implementing JWT-specific logout.
        """
        instance = self.get_object()

        # Instead of using Djoser's logout_user (which tries to use Token model),
        # we'll implement JWT-specific cleanup
        if hasattr(request, 'auth') and request.auth:
            try:
                # Try to blacklist the current refresh token if available
                # This requires the token blacklist feature to be enabled
                refresh_token = request.data.get('refresh_token')
                if refresh_token:
                    token = RefreshToken(refresh_token)
                    token.blacklist()
            except (TokenError, AttributeError):
                # If blacklisting fails or isn't available, just continue
                # The token will expire naturally
                pass

        # Perform the actual user deletion
        self.perform_destroy(instance)
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(["get", "put", "patch", "delete"], detail=False)
    def me(self, request, *args, **kwargs):
        """
        Custom /me endpoint with proper JWT handling.
        Overrides Djoser's me method to fix the Token model issue.
        """
        self.get_object = self.get_instance
        if request.method == "GET":
            return self.retrieve(request, *args, **kwargs)
        elif request.method == "PUT":
            return self.update(request, *args, **kwargs)
        elif request.method == "PATCH":
            return self.partial_update(request, *args, **kwargs)
        elif request.method == "DELETE":
            # Use our custom destroy method
            return self.destroy(request, *args, **kwargs)


class CustomTokenCreateView(djoser_views.TokenCreateView):
    """
    Custom token creation view.
    You can override this if you need custom login behavior.
    """
    pass


class CustomTokenDestroyView(djoser_views.TokenDestroyView):
    """
    Custom token destruction (logout) view.
    Handles JWT token blacklisting instead of Token model deletion.
    """

    def post(self, request):
        """
        Custom logout that handles JWT tokens properly.
        """
        try:
            # Try to get refresh token from request data
            refresh_token = request.data.get(
                'refresh_token') or request.data.get('refresh')

            if refresh_token:
                try:
                    token = RefreshToken(refresh_token)
                    token.blacklist()
                    return Response(
                        {'detail': 'Successfully logged out.'},
                        status=status.HTTP_204_NO_CONTENT
                    )
                except TokenError:
                    return Response(
                        {'detail': 'Invalid token.'},
                        status=status.HTTP_400_BAD_REQUEST
                    )
            else:
                # If no refresh token provided, just return success
                # The access token will expire naturally
                return Response(
                    {'detail': 'Logged out successfully.'},
                    status=status.HTTP_204_NO_CONTENT
                )

        except Exception as e:
            return Response(
                {'detail': 'Logout failed.'},
                status=status.HTTP_400_BAD_REQUEST
            )
