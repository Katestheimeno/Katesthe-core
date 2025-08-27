# ------------------------------------------------------------
# Third-party imports
# ------------------------------------------------------------
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes, action
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.views import TokenObtainPairView
from drf_spectacular.utils import extend_schema, extend_schema_view

# ------------------------------------------------------------
# Django imports
# ------------------------------------------------------------
from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.contrib.auth import get_user_model

# ------------------------------------------------------------
# Djoser imports
# ------------------------------------------------------------
from djoser import views as djoser_views
from djoser.conf import settings
from djoser.utils import ActionViewMixin

# ------------------------------------------------------------
# Project-level imports
# ------------------------------------------------------------
from accounts.serializers.auth import CustomTokenObtainPairSerializer
from config.logger import logger  # Centralised Loguru logger

# ------------------------------------------------------------
# User management
# ------------------------------------------------------------


@extend_schema_view(
    destroy=extend_schema(summary="Delete user", description="Deletes the authenticated user and blacklists their JWT refresh token if provided."),
    me=extend_schema(summary="Retrieve or modify authenticated user", description="Endpoint to GET/PUT/PATCH/DELETE the current authenticated user with proper JWT handling."),
)
class CustomUserViewSet(djoser_views.UserViewSet):
    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()

        logger.info("User deletion requested for id=%s", instance.pk)

        # Instead of using Djoser's logout_user (which tries to use Token model),
        # we'll implement JWT-specific cleanup.
        if hasattr(request, "auth") and request.auth:
            try:
                # Blacklist provided refresh token so it cannot be reused.
                refresh_token = request.data.get("refresh_token")
                if refresh_token:
                    token = RefreshToken(refresh_token)
                    token.blacklist()
                    logger.debug("Refresh token blacklisted for user id=%s", instance.pk)
            except (TokenError, AttributeError):
                # Blacklisting failed or not enabled – token will expire on its own.
                logger.warning("Failed to blacklist refresh token for user id=%s", instance.pk)

        # Perform the actual user deletion
        self.perform_destroy(instance)
        logger.info("User id=%s successfully deleted", instance.pk)
        return Response(status=status.HTTP_204_NO_CONTENT)

    def get_object(self):
        # Route "me" requests to corresponding handlers while keeping JWT intact.
        self.get_object = self.get_instance  # type: ignore
        return super().get_object()

    def get_serializer(self, *args, **kwargs):
        if self.action == "me":
            kwargs["context"] = {"request": self.request}
        return super().get_serializer(*args, **kwargs)

    def get_permissions(self):
        if self.action == "me":
            return [IsAuthenticated()]
        return super().get_permissions()

    def get_queryset(self):
        if self.action == "me":
            return get_user_model().objects.filter(pk=self.request.user.pk)
        return super().get_queryset()

    def get_instance(self):
        return self.request.user

    def list(self, request, *args, **kwargs):
        if request.method == "GET":
            return super().list(request, *args, **kwargs)
        elif request.method == "DELETE":
            # Use our custom destroy method
            return self.destroy(request, *args, **kwargs)
        return Response(status=status.HTTP_405_METHOD_NOT_ALLOWED)

# ------------------------------------------------------------
# JWT token handling views
# ------------------------------------------------------------


@extend_schema(summary="Obtain JWT token pair", description="Returns an access and refresh JWT token for valid credentials.")
class CustomJWTTokenCreateView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer

# ------------------------------------------------------------
# Logout endpoints
# ------------------------------------------------------------


@extend_schema(summary="Logout by blacklisting refresh token", description="Takes a refresh token and blacklists it so it can no longer be used.")
class CustomJWTLogoutView(APIView):
    def post(self, request):
        """Blacklist provided refresh token so the user is effectively logged out."""

        refresh_token = request.data.get("refresh")
        logger.debug("Logout attempt with refresh=%s", bool(refresh_token))

        if not refresh_token:
            return Response(
                {"detail": "Refresh token is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            token = RefreshToken(refresh_token)
            token.blacklist()
            logger.info("Refresh token successfully blacklisted")
            return Response(
                {"detail": "Successfully logged out."},
                status=status.HTTP_204_NO_CONTENT,
            )
        except TokenError:
            logger.exception("Invalid refresh token supplied during logout")
            return Response(
                {"detail": "Invalid token."},
                status=status.HTTP_400_BAD_REQUEST,
            )

# ------------------------------------------------------------
# Djoser token destruction override – handles JWT blacklist
# ------------------------------------------------------------


@extend_schema(summary="Logout (Djoser style)", description="Destroys user session by blacklisting refresh token if provided.")
class CustomTokenDestroyView(djoser_views.TokenDestroyView):
    def post(self, request, *args, **kwargs):
        try:
            # Extract refresh token from possible keys.
            refresh_token = request.data.get("refresh_token") or request.data.get("refresh")
            logger.debug("TokenDestroyView called with refresh provided=%s", bool(refresh_token))

            if refresh_token:
                try:
                    token = RefreshToken(refresh_token)
                    token.blacklist()
                    logger.info("Refresh token blacklisted via TokenDestroyView")
                    return Response({"detail": "Successfully logged out."}, status=status.HTTP_204_NO_CONTENT)
                except TokenError:
                    logger.warning("Invalid refresh token supplied to TokenDestroyView")
                    return Response({"detail": "Invalid token."}, status=status.HTTP_400_BAD_REQUEST)

            # If no refresh token, rely on natural expiry but still report success.
            return Response({"detail": "Logged out successfully."}, status=status.HTTP_204_NO_CONTENT)

        except Exception:
            logger.exception("Unexpected error during logout in TokenDestroyView")
            return Response({"detail": "Logout failed."}, status=status.HTTP_400_BAD_REQUEST)

# ------------------------------------------------------------
# Account activation
# ------------------------------------------------------------


@method_decorator(csrf_exempt, name="dispatch")
@extend_schema(summary="Account activation page", description="Renders an HTML activation page on GET and activates user on POST.")
class CustomActivationView(ActionViewMixin, APIView):
    def get(self, request, uid, token):
        """Render an activation confirmation page with activation button."""

        context = {
            "uid": uid,
            "token": token,
            "activation_url": f"/api/v1/auth/users/activation/{uid}/{token}/",
            "app_name": "Your App Name",
        }
        logger.debug("Rendering activation page for uid=%s", uid)
        return render(request, "accounts/activation.html", context)

    def post(self, request, uid, token):
        """Activate the user account."""

        try:
            # Decode the UID safely; may raise ValueError if malformed
            uid = self.decode_uid(uid)
            # Retrieve user instance from DB
            user = get_user_model().objects.get(pk=uid)
            # Check if user is already active
            if user.is_active:
                logger.warning("User with uid=%s is already active.", uid)
                return JsonResponse({
                    "success": True,
                    "message": "User already activated.",
                }, status=200)
            # Verify activation token validity
            if not self.activate_user(request, user, token):
                logger.warning("Activation failed for uid=%s", uid)
                return JsonResponse({
                    "success": False,
                    "message": "Activation failed. Please check your link or contact support.",
                }, status=400)
            # Activate the user account
            logger.info("User with uid=%s successfully activated", uid)
            return JsonResponse({
                "success": True,
                "message": "Activation successful!",
            }, status=200)
        except ValueError:
            logger.exception("Invalid UID or token format for activation.")
            return JsonResponse({
                "success": False,
                "message": "Invalid activation link or token.",
            }, status=400)
        except get_user_model().DoesNotExist:
            logger.exception("User with uid=%s not found for activation.", uid)
            return JsonResponse({
                "success": False,
                "message": "User not found.",
            }, status=404)
        except Exception:
            logger.exception("Unexpected error during activation for uid=%s", uid)
            return JsonResponse({
                "success": False,
                "message": "Activation failed. Please check your link or contact support.",
            }, status=500)