"""
Djoser configuration for authentication endpoints and serializers.
Path: config/settings/djoser.py
"""
imports = []
imports += ["DJOSER"]
DJOSER = {
    # ──────────────────────────────────────────────
    # USER CREATION & ACCOUNT FLOW
    # ──────────────────────────────────────────────
    # Require password retyping on registration
    'USER_CREATE_PASSWORD_RETYPE': False,
    # Send an activation email after registration
    'SEND_ACTIVATION_EMAIL': True,
    # Send confirmation email after successful activation
    'SEND_CONFIRMATION_EMAIL': True,
    # URL that the user clicks in the activation email
    # Note: {uid} and {token} are placeholders replaced by Djoser
    'ACTIVATION_URL': 'api/v1/auth/users/activation/{uid}/{token}/',
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
    # "EMAIL_FRONTEND_DOMAIN": "test",
    # Delete behavior - IMPORTANT: Set these to False for JWT
    "LOGOUT_ON_PASSWORD_CHANGE": False,
    "LOGOUT_ON_USER_DELETE": False,      # This prevents the Token.objects error
    "USER_DELETE_PASSWORD_RETYPE": False,  # keep password confirmation on delete
}

# Email Backend (for development)
imports += ["EMAIL_BACKEND"]
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

# Email settings for development
imports += ["EMAIL_HOST", "EMAIL_PORT", "EMAIL_USE_TLS", "EMAIL_HOST_USER", "EMAIL_HOST_PASSWORD"]
EMAIL_HOST = 'localhost'
EMAIL_PORT = 1025
EMAIL_USE_TLS = False
EMAIL_HOST_USER = ''
EMAIL_HOST_PASSWORD = ''


__all__ = imports
