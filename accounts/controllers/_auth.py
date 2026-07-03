"""
Custom authentication views for Djoser integration.
Path: accounts/controllers/_auth.py
"""

from typing import Optional

from rest_framework import status
from rest_framework.decorators import api_view, permission_classes, action
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework_simplejwt.views import TokenRefreshView as BaseTokenRefreshView
from rest_framework_simplejwt.views import TokenVerifyView as BaseTokenVerifyView
from django.conf import settings as django_settings
from django.db import transaction
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt, ensure_csrf_cookie
from django.utils.decorators import method_decorator
from djoser import views as djoser_views
from djoser.conf import settings
from djoser.utils import ActionViewMixin
from accounts.authentication import enforce_csrf
from errors.catalog import E
from errors.exceptions import AppAPIError
from accounts.serializers.auth import (
    CustomTokenObtainPairSerializer,
    KidTokenRefreshSerializer,
)
from accounts.services.session import detect_refresh_reuse, revoke_all_sessions
from accounts.schemas._user import (
    CurrentUserResponse,
    UserCreateRequest,
    UserDeleteRequest,
    UserDetailResponse,
    UserListResponse,
    UserUpdateRequest,
)
from accounts.schemas._token import (
    ActivationResponse,
    JWTLogoutRequest,
    JWTRefreshRequest,
    JWTRefreshResponse,
    JWTTokenCreateRequest,
    JWTTokenCreateResponse,
    JWTVerifyRequest,
)
from django.contrib.auth import get_user_model
from config.db_router import force_primary_for_request
from config.db_utils import read_from_primary
from config.settings.config import settings
from config.logger import logger
from drf_spectacular.utils import (
    extend_schema,
    extend_schema_view,
    OpenApiParameter,
    OpenApiExample,
)
from utils.api_response import meta_for_request, ok

User = get_user_model()


# ---------------------------------------------------------------------------
# Cookie helpers
#
# NOTE: ``settings`` above (line 50) is the Pydantic ``MainSettings``
# singleton (config.settings.config), not Django's settings — it has no
# ``SIMPLE_JWT`` and no ``DEBUG`` (its field is ``DJANGO_DEBUG``). Cookie
# *names* / lifetimes come from Django's ``SIMPLE_JWT`` (via
# ``django_settings``); cookie *transport* attributes (secure/samesite/
# domain/refresh path) come from the Pydantic ``settings`` singleton.
# ---------------------------------------------------------------------------

def _jwt_cfg() -> dict:
    return django_settings.SIMPLE_JWT


def _cookie_transport_kwargs() -> dict:
    """Shared ``secure``/``samesite``/``domain`` kwargs for auth cookies."""
    secure = (
        settings.AUTH_COOKIE_SECURE
        if settings.AUTH_COOKIE_SECURE is not None
        else not django_settings.DEBUG
    )
    return dict(
        httponly=_jwt_cfg()["AUTH_COOKIE_HTTP_ONLY"],
        secure=secure,
        samesite=settings.AUTH_COOKIE_SAMESITE,
        domain=settings.AUTH_COOKIE_DOMAIN or None,
    )


def _set_auth_cookies(response, access: str, refresh: Optional[str] = None) -> None:
    """
    Set the HttpOnly access cookie and, when provided, the refresh cookie.

    Shared by login, refresh, and (subtask 019) logout-all so cookie
    transport is defined exactly once.
    """
    cfg = _jwt_cfg()
    common = _cookie_transport_kwargs()
    response.set_cookie(
        key=cfg["AUTH_COOKIE_ACCESS"],
        value=access,
        max_age=int(cfg["ACCESS_TOKEN_LIFETIME"].total_seconds()),
        path=cfg["AUTH_COOKIE_PATH"],
        **common,
    )
    if refresh is not None:
        response.set_cookie(
            key=cfg["AUTH_COOKIE_REFRESH"],
            value=refresh,
            max_age=int(cfg["REFRESH_TOKEN_LIFETIME"].total_seconds()),
            path=settings.AUTH_COOKIE_REFRESH_PATH,
            **common,
        )


def _clear_auth_cookies(response) -> None:
    """Clear both auth cookies using the same path/domain they were set with."""
    cfg = _jwt_cfg()
    domain = settings.AUTH_COOKIE_DOMAIN or None
    for name, path in (
        (cfg["AUTH_COOKIE_ACCESS"], cfg["AUTH_COOKIE_PATH"]),
        (cfg["AUTH_COOKIE_REFRESH"], settings.AUTH_COOKIE_REFRESH_PATH),
    ):
        response.delete_cookie(
            key=name,
            path=path,
            domain=domain,
            samesite=settings.AUTH_COOKIE_SAMESITE,
        )


@extend_schema_view(
    list=extend_schema(
        tags=["Authentication"],
        summary="List users",
        responses={200: UserListResponse},
    ),
    create=extend_schema(
        tags=["Authentication"],
        summary="Register user",
        request=UserCreateRequest,
        responses={201: UserDetailResponse},
    ),
    retrieve=extend_schema(
        tags=["Authentication"],
        summary="Get user detail",
        responses={200: UserDetailResponse},
    ),
    update=extend_schema(
        tags=["Authentication"],
        summary="Update user",
        request=UserUpdateRequest,
        responses={200: UserDetailResponse},
    ),
    partial_update=extend_schema(
        tags=["Authentication"],
        summary="Partial update user",
        request=UserUpdateRequest,
        responses={200: UserDetailResponse},
    ),
    destroy=extend_schema(
        tags=["Authentication"],
        summary="Delete user",
        request=UserDeleteRequest,
        responses={204: None},
    ),
)
class CustomUserViewSet(djoser_views.UserViewSet):
    """
    Custom User ViewSet that extends Djoser's UserViewSet.
    Handles user CRUD operations with JWT-specific logout logic.
    """

    def finalize_response(self, request, response, *args, **kwargs):
        """Wrap successful bodies in the standard envelope.

        Djoser's ``list``/``create``/``retrieve``/``update``/``partial_update``
        (reached directly and via ``me``) return raw ``serializer.data`` with
        no override point short of this hook. Failures already carry the
        envelope — either raised (via ``custom_exception_handler``) or a
        bodyless 204 — so only a successful, non-empty body needs wrapping.
        """
        response = super().finalize_response(request, response, *args, **kwargs)
        if response.exception or response.data is None:
            return response
        if isinstance(response.data, dict) and "success" in response.data:
            return response
        response.data = {
            "success": True,
            "data": response.data,
            "meta": meta_for_request(request),
        }
        return response

    def perform_create(self, serializer):
        super().perform_create(serializer)
        force_primary_for_request()

    def perform_update(self, serializer):
        super().perform_update(serializer)
        force_primary_for_request()

    def perform_destroy(self, instance):
        super().perform_destroy(instance)
        force_primary_for_request()

    def destroy(self, request, *args, **kwargs):
        """
        Custom user deletion that properly handles JWT tokens.
        Fixes the Token model error by implementing JWT-specific logout.

        Deliberately does NOT call ``super().destroy()``: Djoser's default
        ``destroy()`` unconditionally calls ``djoser.utils.logout_user()``
        for a self-delete, which touches ``rest_framework.authtoken.Token``
        — an app that is not installed here, so that call would raise.

        Subtask 019: revokes every outstanding session (refresh token) for
        the deleted user via ``revoke_all_sessions``, in addition to the
        best-effort single-token blacklist below. The user id is captured
        before deletion because ``instance.delete()`` clears the in-memory
        primary key on the instance.
        """
        instance = self.get_object()
        user_id = instance.id
        logger.info(f"User deletion requested for user_id={user_id}, username={instance.username}")

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
                    logger.debug(f"Successfully blacklisted refresh token for user_id={user_id}")
            except (TokenError, AttributeError) as e:
                # If blacklisting fails or isn't available, just continue
                # The token will expire naturally
                logger.warning(f"Failed to blacklist token for user_id={user_id}: {e}")

        # Revoke sessions BEFORE deleting the user, then perform the deletion
        # in the same transaction (roll back both together on failure).
        # Ordering matters: ``OutstandingToken.user`` is ``on_delete=SET_NULL``,
        # so deleting the user first would null the FK and make the
        # user_id-scoped lookup inside ``revoke_all_sessions`` find nothing.
        with transaction.atomic():
            revoke_all_sessions(user_id, event="account_deletion")
            self.perform_destroy(instance)

        logger.info(f"User successfully deleted: user_id={user_id}")
        return Response(status=status.HTTP_204_NO_CONTENT)

    @extend_schema(
        tags=["Authentication"],
        summary="Current user (me)",
        methods=["GET"],
        responses={200: CurrentUserResponse},
    )
    @extend_schema(
        tags=["Authentication"],
        summary="Update current user",
        methods=["PUT", "PATCH"],
        request=UserUpdateRequest,
        responses={200: CurrentUserResponse},
    )
    @extend_schema(
        tags=["Authentication"],
        summary="Delete current user",
        methods=["DELETE"],
        request=UserDeleteRequest,
        responses={204: None},
    )
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

    def set_password(self, request, *args, **kwargs):
        """Revoke every outstanding session after a successful password change."""
        response = super().set_password(request, *args, **kwargs)
        if response.status_code in (status.HTTP_200_OK, status.HTTP_204_NO_CONTENT):
            revoke_all_sessions(request.user.id, event="password_change")
        return response

    def set_username(self, request, *args, **kwargs):
        """Revoke every outstanding session after a successful username change."""
        response = super().set_username(request, *args, **kwargs)
        if response.status_code in (status.HTTP_200_OK, status.HTTP_204_NO_CONTENT):
            revoke_all_sessions(request.user.id, event="username_change")
        return response

    @extend_schema(tags=["Authentication"], summary="Logout all sessions", responses={204: None})
    @action(detail=False, methods=["post"], url_path="logout-all")
    def logout_all(self, request):
        """Revoke every outstanding session for the current user and clear auth cookies."""
        revoke_all_sessions(request.user.id, event="logout_all")
        response = Response(status=status.HTTP_204_NO_CONTENT)
        _clear_auth_cookies(response)
        return response


from rest_framework_simplejwt.views import TokenObtainPairView

class CustomJWTTokenCreateView(TokenObtainPairView):
    """
    Custom JWT token creation view that uses our custom serializer.
    """
    serializer_class = CustomTokenObtainPairSerializer

    @extend_schema(
        tags=["Authentication"],
        summary="JWT Login",
        request=JWTTokenCreateRequest,
        responses={200: JWTTokenCreateResponse},
    )
    def post(self, request, *args, **kwargs):
        """
        Handle JWT token creation, setting HttpOnly auth cookies by default.

        By default the response body carries the user payload only — no
        ``access``/``refresh``. Clients that need Bearer-style body tokens
        (cross-domain, non-cookie clients) opt in with the
        ``X-Token-Delivery: bearer`` request header.
        """
        username = request.data.get('username', 'unknown')
        logger.info(f"JWT token creation attempt for username/email: {username}")

        response = super().post(request, *args, **kwargs)
        if response.status_code != 200:
            logger.warning(f"JWT token creation failed for username/email: {username}, status={response.status_code}")
            return response

        logger.info(f"JWT token created successfully for username/email: {username}")
        access = response.data.get('access')
        refresh = response.data.get('refresh')
        if access and refresh:
            _set_auth_cookies(response, access, refresh)

        bearer_only = request.headers.get('X-Token-Delivery', '').lower() == 'bearer'
        body = response.data
        if not bearer_only:
            body = {key: value for key, value in body.items() if key not in ('access', 'refresh')}

        response.data = {"success": True, "data": body, "meta": meta_for_request(request)}
        return response


@extend_schema(
    tags=["Authentication"],
    summary="JWT Token Refresh",
    request=JWTRefreshRequest,
    responses={200: JWTRefreshResponse},
)
class CustomJWTTokenRefreshView(BaseTokenRefreshView):
    """
    JWT token refresh view.

    Reads the refresh token from the request body first; when the body omits
    it, falls back to the ``refresh_token`` HttpOnly cookie. Cookie transport
    requires a valid CSRF token. On success, sets a fresh access cookie (and
    a fresh refresh cookie when rotation returned a new one).
    """
    serializer_class = KidTokenRefreshSerializer

    def post(self, request, *args, **kwargs):
        cookie_name = _jwt_cfg()["AUTH_COOKIE_REFRESH"]
        data = request.data.copy() if hasattr(request.data, "copy") else dict(request.data)

        using_cookie = False
        if not data.get("refresh"):
            refresh_from_cookie = request.COOKIES.get(cookie_name)
            if refresh_from_cookie:
                data["refresh"] = refresh_from_cookie
                using_cookie = True

        if using_cookie:
            enforce_csrf(request)

        refresh_value = data.get("refresh")
        if refresh_value:
            detect_refresh_reuse(refresh_value)

        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)

        response = Response(status=status.HTTP_200_OK)
        access = serializer.validated_data.get("access")
        if access:
            _set_auth_cookies(response, access, serializer.validated_data.get("refresh"))
        response.data = {
            "success": True,
            "data": serializer.validated_data,
            "meta": meta_for_request(request),
        }
        return response


# ---------------------------------------------------------------------------
# CSRF Bootstrap (cross-origin SPA support)
# ---------------------------------------------------------------------------

@method_decorator(ensure_csrf_cookie, name="dispatch")
class CSRFTokenView(APIView):
    """
    Set the ``csrftoken`` cookie for cross-origin SPAs using cookie auth.

    Cross-origin single-page apps authenticate via HttpOnly cookies and must
    send a CSRF token on mutating requests. Before the SPA has ever received
    the cookie (e.g. before login), it has no ``csrftoken`` to read and no
    token to send. Hitting this endpoint once — decorated with
    ``ensure_csrf_cookie`` so it always sets the cookie regardless of session
    state — lets the SPA obtain ``csrftoken`` up front. The route
    (``auth/csrf/``) is bound by subtask 019.
    """
    permission_classes = [AllowAny]
    authentication_classes = []

    @extend_schema(
        tags=["Authentication"],
        summary="Get CSRF cookie",
        description=(
            "Sets the csrftoken cookie on the response. Cross-origin SPAs "
            "using cookie auth should call this once before a mutating "
            "request so document.cookie has a value to send back as "
            "X-CSRFToken."
        ),
        responses={200: None},
    )
    def get(self, request, *args, **kwargs):
        return ok({"detail": "CSRF cookie set"}, request)


@extend_schema(
    tags=["Authentication"],
    summary="JWT Token Verify",
    request=JWTVerifyRequest,
    responses={200: None},
)
class CustomJWTTokenVerifyView(BaseTokenVerifyView):
    """JWT token verification view with Pydantic schema documentation."""

    def post(self, request, *args, **kwargs):
        response = super().post(request, *args, **kwargs)
        response.data = {"success": True, "data": {}, "meta": meta_for_request(request)}
        return response


@extend_schema(
    tags=["Authentication"],
    summary="JWT Logout",
    description="Logout and blacklist the refresh token",
    request=JWTLogoutRequest,
    responses={
        204: None,
        400: {
            "description": "Bad request - refresh token required or invalid",
            "type": "object",
            "properties": {
                "detail": {"type": "string", "example": "Refresh token is required."}
            },
        },
    },
    examples=[
        OpenApiExample(
            "Logout Request",
            value={"refresh": "your_refresh_token_here"},
            request_only=True,
        )
    ],
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

        refresh_token = request.data.get('refresh') or request.COOKIES.get(
            _jwt_cfg()["AUTH_COOKIE_REFRESH"]
        )

        if not refresh_token:
            logger.warning(f"JWT logout failed - no refresh token provided for user_id={user_id}")
            raise AppAPIError(E.VALIDATION__MISSING_FIELD, status_code=400)

        try:
            token = RefreshToken(refresh_token)
            token.blacklist()
        except Exception as e:
            logger.error(f"JWT logout error for user_id={user_id}: {e}")
            raise AppAPIError(E.AUTH__TOKEN_INVALID, status_code=400)

        logger.info(f"JWT logout successful - token blacklisted for user_id={user_id}")
        response = Response(status=status.HTTP_204_NO_CONTENT)
        _clear_auth_cookies(response)
        return response


@extend_schema(
    tags=["Authentication"],
    summary="User Activation",
    description="Activate user account with UID and token",
    parameters=[
        OpenApiParameter(
            name="uid",
            location=OpenApiParameter.PATH,
            description="User ID for activation",
            required=True,
            type=str,
        ),
        OpenApiParameter(
            name="token",
            location=OpenApiParameter.PATH,
            description="Activation token",
            required=True,
            type=str,
        ),
    ],
    request=None,
    responses={
        200: ActivationResponse,
        400: ActivationResponse,
    },
)
@method_decorator(csrf_exempt, name="dispatch")
class CustomActivationView(ActionViewMixin, APIView):
    """
    Custom activation view that renders an HTML page with activation button.
    """
    permission_classes = [AllowAny]
    serializer_class = None  # No serializer needed for activation
    
    @extend_schema(operation_id="auth_users_custom_activation_page")
    def get(self, request, uid, token):
        """Render the activation page."""
        logger.info(f"User activation page accessed for uid={uid}")
        context = {
            'uid': uid,
            'token': token,
            'activation_url': f'/api/v1/auth/users/activation/{uid}/{token}/',
            'app_name': settings.PROJECT_NAME
        }
        return render(request, 'accounts/activation.html', context)

    @extend_schema(operation_id="auth_users_custom_activation")
    def post(self, request, uid, token):
        """Handle the actual activation."""
        from djoser.utils import decode_uid
        from django.contrib.auth.tokens import default_token_generator
        from django.contrib.auth import get_user_model

        User = get_user_model()
        logger.info(f"User activation attempt for uid={uid}")

        try:
            # Reuses PrimaryReplicaRouter: activation reads must see rows on primary (replica can lag).
            with read_from_primary():
                try:
                    decoded_uid = decode_uid(uid)
                except Exception as e:
                    logger.warning(f"UID decode failed for uid={uid}: {e}")
                    raise AppAPIError(E.VALIDATION__INVALID_FORMAT, status_code=400)

                try:
                    user = User.objects.get(pk=decoded_uid)
                except User.DoesNotExist:
                    logger.warning(f"User not found for activation: decoded_uid={decoded_uid}")
                    raise AppAPIError(E.RESOURCE__NOT_FOUND, status_code=400)

                if user.is_active:
                    logger.info(f"User already activated: user_id={user.id}")
                    return ok({"detail": "Account is already activated."}, request)

                if not default_token_generator.check_token(user, token):
                    logger.warning(f"Invalid activation token for user_id={user.id}")
                    raise AppAPIError(E.AUTH__TOKEN_INVALID, status_code=400)

                user.is_active = True
                user.save()
                logger.info(f"User successfully activated: user_id={user.id}")
                return ok(
                    {"detail": "Account activated successfully. You can now log in."},
                    request,
                )

        except AppAPIError:
            raise
        except Exception as e:
            logger.error(f"User activation error for uid={uid}: {e}")
            raise AppAPIError(E.INTERNAL__ERROR, status_code=500)
