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
from config.logger import logger
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiExample

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
        logger.info(f"User deletion requested for user_id={instance.id}, username={instance.username}")

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
                    logger.debug(f"Successfully blacklisted refresh token for user_id={instance.id}")
            except (TokenError, AttributeError) as e:
                # If blacklisting fails or isn't available, just continue
                # The token will expire naturally
                logger.warning(f"Failed to blacklist token for user_id={instance.id}: {e}")

        # Perform the actual user deletion
        self.perform_destroy(instance)
        logger.info(f"User successfully deleted: user_id={instance.id}, username={instance.username}")
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(["get", "put", "patch", "delete"], detail=False)
    def me(self, request, *args, **kwargs):
        """
        Custom /me endpoint with proper JWT handling.
        Overrides Djoser's me method to fix the Token model issue.
        """
        self.get_object = self.get_instance
        logger.debug(f"User profile access: user_id={request.user.id}, method={request.method}")
        
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

    def post(self, request, *args, **kwargs):
        """Handle JWT token creation with logging."""
        username = request.data.get('username', 'unknown')
        logger.info(f"JWT token creation attempt for username/email: {username}")
        
        try:
            response = super().post(request, *args, **kwargs)
            if response.status_code == 200:
                logger.info(f"JWT token created successfully for username/email: {username}")
            else:
                logger.warning(f"JWT token creation failed for username/email: {username}, status={response.status_code}")
            return response
        except Exception as e:
            logger.error(f"JWT token creation error for username/email: {username}, error: {e}")
            raise


@extend_schema(
    tags=['Authentication'],
    summary='JWT Logout',
    description='Logout and blacklist the refresh token',
    request=None,
    responses={
        204: {
            'description': 'Successfully logged out',
            'type': 'object',
            'properties': {
                'detail': {'type': 'string', 'example': 'Successfully logged out.'}
            }
        },
        400: {
            'description': 'Bad request - refresh token required or invalid',
            'type': 'object',
            'properties': {
                'detail': {'type': 'string', 'example': 'Refresh token is required.'}
            }
        }
    },
    examples=[
        OpenApiExample(
            'Logout Request',
            value={'refresh': 'your_refresh_token_here'},
            request_only=True
        )
    ]
)
class CustomJWTLogoutView(APIView):
    """
    Custom JWT logout view that blacklists the refresh token.
    """
    permission_classes = [IsAuthenticated]
    serializer_class = None  # No serializer needed for logout

    def post(self, request):
        user_id = request.user.id
        username = request.user.username
        logger.info(f"JWT logout requested for user_id={user_id}, username={username}")
        
        try:
            refresh_token = request.data.get('refresh')
            if refresh_token:
                token = RefreshToken(refresh_token)
                token.blacklist()
                logger.info(f"JWT logout successful - token blacklisted for user_id={user_id}")
                return Response(
                    {'detail': 'Successfully logged out.'},
                    status=status.HTTP_204_NO_CONTENT
                )
            else:
                logger.warning(f"JWT logout failed - no refresh token provided for user_id={user_id}")
                return Response(
                    {'detail': 'Refresh token is required.'},
                    status=status.HTTP_400_BAD_REQUEST
                )
        except Exception as e:
            logger.error(f"JWT logout error for user_id={user_id}: {e}")
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
        user_id = getattr(request.user, 'id', 'anonymous')
        username = getattr(request.user, 'username', 'anonymous')
        logger.info(f"Token destruction requested for user_id={user_id}, username={username}")
        
        try:
            # Try to get refresh token from request data
            refresh_token = request.data.get(
                'refresh_token') or request.data.get('refresh')

            if refresh_token:
                try:
                    token = RefreshToken(refresh_token)
                    token.blacklist()
                    logger.info(f"Token destruction successful - token blacklisted for user_id={user_id}")
                    return Response(
                        {'detail': 'Successfully logged out.'},
                        status=status.HTTP_204_NO_CONTENT
                    )
                except TokenError as e:
                    logger.warning(f"Token destruction failed - invalid token for user_id={user_id}: {e}")
                    return Response(
                        {'detail': 'Invalid token.'},
                        status=status.HTTP_400_BAD_REQUEST
                    )
            else:
                # If no refresh token provided, just return success
                # The access token will expire naturally
                logger.info(f"Token destruction successful - no refresh token provided for user_id={user_id}")
                return Response(
                    {'detail': 'Logged out successfully.'},
                    status=status.HTTP_204_NO_CONTENT
                )

        except Exception as e:
            logger.error(f"Token destruction error for user_id={user_id}: {e}")
            return Response(
                {'detail': 'Logout failed.'},
                status=status.HTTP_400_BAD_REQUEST
            )


@extend_schema(
    tags=['Authentication'],
    summary='User Activation',
    description='Activate user account with UID and token',
    parameters=[
        OpenApiParameter(
            name='uid',
            location=OpenApiParameter.PATH,
            description='User ID for activation',
            required=True,
            type=str
        ),
        OpenApiParameter(
            name='token',
            location=OpenApiParameter.PATH,
            description='Activation token',
            required=True,
            type=str
        )
    ],
    request=None,
    responses={
        200: {
            'description': 'Activation successful or already activated',
            'type': 'object',
            'properties': {
                'success': {'type': 'boolean'},
                'message': {'type': 'string'}
            }
        },
        400: {
            'description': 'Activation failed',
            'type': 'object',
            'properties': {
                'success': {'type': 'boolean'},
                'message': {'type': 'string'}
            }
        }
    }
)
@method_decorator(csrf_exempt, name='dispatch')
class CustomActivationView(ActionViewMixin, APIView):
    """
    Custom activation view that renders an HTML page with activation button.
    """
    permission_classes = [AllowAny]
    serializer_class = None  # No serializer needed for activation
    
    def get(self, request, uid, token):
        """Render the activation page."""
        logger.info(f"User activation page accessed for uid={uid}")
        context = {
            'uid': uid,
            'token': token,
            'activation_url': f'/api/v1/auth/users/activation/{uid}/{token}/',
            'app_name': 'Your App Name'
        }
        return render(request, 'accounts/activation.html', context)
    
    def post(self, request, uid, token):
        """Handle the actual activation."""
        logger.info(f"User activation attempt for uid={uid}")
        
        try:
            from djoser.utils import decode_uid
            from django.contrib.auth.tokens import default_token_generator
            from django.contrib.auth import get_user_model
            
            User = get_user_model()
            
            # Decode the UID
            try:
                decoded_uid = decode_uid(uid)
                logger.debug(f"UID decoded successfully: {uid} -> {decoded_uid}")
            except Exception as e:
                logger.warning(f"UID decode failed for uid={uid}: {e}")
                return JsonResponse({
                    'success': False,
                    'message': 'Invalid activation link.'
                }, status=400)
            
            # Get the user
            try:
                user = User.objects.get(pk=decoded_uid)
                logger.debug(f"User found for activation: user_id={user.id}, username={user.username}")
            except User.DoesNotExist:
                logger.warning(f"User not found for activation: decoded_uid={decoded_uid}")
                return JsonResponse({
                    'success': False,
                    'message': 'User not found.'
                }, status=400)
            
            # Check if user is already active
            if user.is_active:
                logger.info(f"User already activated: user_id={user.id}, username={user.username}")
                return JsonResponse({
                    'success': True,
                    'message': 'Account is already activated!'
                })
            
            # Verify the token
            if not default_token_generator.check_token(user, token):
                logger.warning(f"Invalid activation token for user_id={user.id}, username={user.username}")
                return JsonResponse({
                    'success': False,
                    'message': 'Invalid or expired activation token.'
                }, status=400)
            
            # Activate the user
            user.is_active = True
            user.save()
            logger.info(f"User successfully activated: user_id={user.id}, username={user.username}")
            
            return JsonResponse({
                'success': True,
                'message': 'Account activated successfully! You can now log in.'
            })
                
        except Exception as e:
            logger.error(f"User activation error for uid={uid}: {e}")
            return JsonResponse({
                'success': False,
                'message': 'Activation failed. Please check your link or contact support.'
            }, status=400)
