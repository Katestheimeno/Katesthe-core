"""
Custom authentication views for Djoser integration.
Path: accounts/controllers/_auth.py
"""

from rest_framework import status
from rest_framework.decorators import api_view, permission_classes, action
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.views import TokenObtainPairView
from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from djoser import views as djoser_views
from djoser.conf import settings
from djoser.utils import ActionViewMixin
from accounts.serializers.auth import CustomTokenObtainPairSerializer
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


from rest_framework_simplejwt.views import TokenObtainPairView

class CustomJWTTokenCreateView(TokenObtainPairView):
    """
    Custom JWT token creation view that uses our custom serializer.
    """
    serializer_class = CustomTokenObtainPairSerializer


class CustomJWTLogoutView(APIView):
    """
    Custom JWT logout view that blacklists the refresh token.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            refresh_token = request.data.get('refresh')
            if refresh_token:
                token = RefreshToken(refresh_token)
                token.blacklist()
                return Response(
                    {'detail': 'Successfully logged out.'},
                    status=status.HTTP_204_NO_CONTENT
                )
            else:
                return Response(
                    {'detail': 'Refresh token is required.'},
                    status=status.HTTP_400_BAD_REQUEST
                )
        except Exception as e:
            return Response(
                {'detail': 'Invalid token.'},
                status=status.HTTP_400_BAD_REQUEST
            )


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


@method_decorator(csrf_exempt, name='dispatch')
class CustomActivationView(ActionViewMixin, APIView):
    """
    Custom activation view that renders an HTML page with activation button.
    """
    permission_classes = [AllowAny]
    
    def get(self, request, uid, token):
        """Render the activation page."""
        context = {
            'uid': uid,
            'token': token,
            'activation_url': f'/api/v1/auth/users/activation/{uid}/{token}/',
            'app_name': 'Your App Name'
        }
        return render(request, 'accounts/activation.html', context)
    
    def post(self, request, uid, token):
        """Handle the actual activation."""
        try:
            from djoser.utils import decode_uid
            from django.contrib.auth.tokens import default_token_generator
            from django.contrib.auth import get_user_model
            
            User = get_user_model()
            
            # Decode the UID
            try:
                decoded_uid = decode_uid(uid)
            except Exception:
                return JsonResponse({
                    'success': False,
                    'message': 'Invalid activation link.'
                }, status=400)
            
            # Get the user
            try:
                user = User.objects.get(pk=decoded_uid)
            except User.DoesNotExist:
                return JsonResponse({
                    'success': False,
                    'message': 'User not found.'
                }, status=400)
            
            # Check if user is already active
            if user.is_active:
                return JsonResponse({
                    'success': True,
                    'message': 'Account is already activated!'
                })
            
            # Verify the token
            if not default_token_generator.check_token(user, token):
                return JsonResponse({
                    'success': False,
                    'message': 'Invalid or expired activation token.'
                }, status=400)
            
            # Activate the user
            user.is_active = True
            user.save()
            
            return JsonResponse({
                'success': True,
                'message': 'Account activated successfully! You can now log in.'
            })
                
        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': 'Activation failed. Please check your link or contact support.'
            }, status=400)
