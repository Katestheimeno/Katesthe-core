"""
Djoser configuration for authentication endpoints and serializers.
Path: config/settings/djoser.py
"""
from config.settings.config import settings

imports = []
imports += ["DJOSER"]
DJOSER = {
    # ──────────────────────────────────────────────
    # USER CREATION & ACCOUNT FLOW
    # ──────────────────────────────────────────────
    # Require password retyping on registration
    'USER_CREATE_PASSWORD_RETYPE': False,
    # Send an activation email after registration
    'SEND_ACTIVATION_EMAIL': False,  # Completely disabled to avoid conflicts
    # Send confirmation email after successful activation
    'SEND_CONFIRMATION_EMAIL': False,  # Completely disabled to avoid conflicts
    # URL that the user clicks in the activation email
    # Note: {uid} and {token} are placeholders replaced by Djoser
    # This is used for email generation, not endpoint registration
    'ACTIVATION_URL': 'api/v1/auth/users/activation/{uid}/{token}/',
    # Completely disable default activation endpoints to avoid conflicts
    'ACTIVATION_URL_CONFIRM': False,
    'ACTIVATION_URL_ACTIVATE': False,
    # URL used in password reset emails
    # Commonly links to frontend reset password form
    "PASSWORD_RESET_CONFIRM_URL": "reset-password?uid={uid}&token={token}",
    # URL used in username reset confirmation
    "USERNAME_RESET_CONFIRM_URL": "reset-username-confirm/{uid}/{token}/",
    # ──────────────────────────────────────────────
    # EMAIL NOTIFICATIONS
    # ──────────────────────────────────────────────
    # Send email confirmation after password change
    'PASSWORD_CHANGED_EMAIL_CONFIRMATION': False,
    # Custom email classes for password reset and activation
    "EMAIL": {
        "password_reset": "accounts.emails.CustomPasswordResetEmail",
        "activation": "accounts.emails.CustomActivationEmail",
        "password_changed_confirmation": "accounts.emails.CustomPasswordChangedConfirmationEmail",
    },
    # ──────────────────────────────────────────────
    # SERIALIZERS (customized to your project)
    # ──────────────────────────────────────────────
    'SERIALIZERS': {
        # Used when creating a new user
        'user_create': 'accounts.serializers.auth.UserCreateSerializer',

        # Used when fetching user data (admin views / general use)
        'user': 'accounts.serializers.auth.UserSerializer',

        # Used for /me endpoint (current user)
        'current_user': 'accounts.serializers.auth.CurrentUserSerializer',

        # Used for user deletion
        'user_delete': 'accounts.serializers.auth.UserDeleteSerializer',
    },
    # ──────────────────────────────────────────────
    # VIEWS (Custom views to handle JWT properly)
    # ──────────────────────────────────────────────
    'VIEWS': {
        'user': 'accounts.controllers.CustomUserViewSet',
        'token_create': 'accounts.controllers.CustomTokenCreateView',
        'token_destroy': 'accounts.controllers.CustomTokenDestroyView',
        # Completely override activation views to avoid conflicts
        'activation': 'accounts.controllers.CustomActivationView',
        'activation_confirm': 'accounts.controllers.CustomActivationView',
        'activation_activate': 'accounts.controllers.CustomActivationView',
        'activation_resend': 'accounts.controllers.CustomActivationView',
    },
    # ──────────────────────────────────────────────
    # PERMISSIONS (granular per endpoint)
    # ──────────────────────────────────────────────
    'PERMISSIONS': {
        'user': ['rest_framework.permissions.IsAuthenticated'],   # /users/{id}
        'user_list': ['rest_framework.permissions.IsAdminUser'],  # /users/
        'user_create': ['rest_framework.permissions.AllowAny'],  # registration
        'user_delete': ['rest_framework.permissions.IsAuthenticated'],
        'token_create': ['rest_framework.permissions.AllowAny'],  # login
        # logout
        'token_destroy': ['rest_framework.permissions.IsAuthenticated'],
    },
    # ──────────────────────────────────────────────
    # USER MODEL CONFIG
    # ──────────────────────────────────────────────
    # Field used as ID (UUID in your case)
    'USER_ID_FIELD': 'id',
    # Field used for login (can be 'username' or 'email')
    'LOGIN_FIELD': 'username',
    # Hide /users/ endpoint unless explicitly needed
    'HIDE_USERS': True,
    # Optional: domain used in email templates for frontend redirection
    "EMAIL_FRONTEND_DOMAIN": settings.email.FRONTEND_DOMAIN if settings.email.FRONTEND_DOMAIN else None,
    # Delete behavior - IMPORTANT: Set these to False for JWT
    "LOGOUT_ON_PASSWORD_CHANGE": False,
    "LOGOUT_ON_USER_DELETE": False,      # This prevents the Token.objects error
    "USER_DELETE_PASSWORD_RETYPE": False,  # keep password confirmation on delete
    # API documentation settings
    'SERIALIZER_OPTIONS': {
        'activation': {
            'serializer_class': None,  # No serializer needed for activation
        },
        'activation_confirm': {
            'serializer_class': None,  # No serializer needed for activation
        },
        'token_destroy': {
            'serializer_class': None,  # No serializer needed for logout
        },
    },
    
    # Completely disable default activation endpoints
    'ACTIVATION_URL_CONFIRM': False,
    'ACTIVATION_URL_ACTIVATE': False,
    'ACTIVATION_URL_RESEND': False,
    
    # Disable all activation-related endpoints to avoid conflicts
    'ACTIVATION_URL': False,
    'ACTIVATION_URL_ACTIVATE': False,
    'ACTIVATION_URL_CONFIRM': False,
    'ACTIVATION_URL_RESEND': False,
    
    # Completely disable activation functionality
    'ACTIVATION_REQUIRED': False,
    'ACTIVATION_URL': False,
    'ACTIVATION_URL_ACTIVATE': False,
    'ACTIVATION_URL_CONFIRM': False,
    'ACTIVATION_URL_RESEND': False,
    'ACTIVATION_URL_ACTIVATE': False,
    

}

# Email Backend (for development)
imports += ["EMAIL_BACKEND"]
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

# Email settings for development
imports += ["EMAIL_HOST", "EMAIL_PORT", "EMAIL_USE_TLS", "EMAIL_HOST_USER", "EMAIL_HOST_PASSWORD"]
EMAIL_HOST = settings.email.HOST
EMAIL_PORT = settings.email.PORT
EMAIL_USE_TLS = settings.email.USE_TLS
EMAIL_HOST_USER = settings.email.HOST_USER
EMAIL_HOST_PASSWORD = settings.email.HOST_PASSWORD


__all__ = imports
