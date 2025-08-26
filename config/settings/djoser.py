imports = []

imports += ["DJOSER"]
DJOSER = {
    # ──────────────────────────────────────────────
    # USER CREATION & ACCOUNT FLOW
    # ──────────────────────────────────────────────

    # Require password retyping on registration
    'USER_CREATE_PASSWORD_RETYPE': False,

    # Send an activation email after registration
    'SEND_ACTIVATION_EMAIL': False,

    # Send confirmation email after successful activation
    'SEND_CONFIRMATION_EMAIL': False,

    # URL that the user clicks in the activation email
    # Note: {uid} and {token} are placeholders replaced by Djoser
    'ACTIVATION_URL': 'api/auth/activate/{uid}/{token}',

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
        # "password_reset": "accounts.emails.CustomPasswordResetEmail",
        # "activation": "accounts.emails.CustomActivationEmail",
    },


    # ──────────────────────────────────────────────
    # SERIALIZERS (customized to your project)
    # ──────────────────────────────────────────────

    'SERIALIZERS': {
        # # Used when creating a new user
        # 'user_create': 'accounts.serializers.auth.UserCreateSerializer',
        #
        # # Used when fetching user data (admin views / general use)
        # 'user': 'accounts.serializers.auth.UserSerializer',
        #
        # # Used for /me endpoint (current user)
        # 'current_user': 'accounts.serializers.auth.CurrentUserSerializer',
        #
        # # Custom token serializer for JWT handling
        # # Both endpoints (token & token_create) point to the same class
        # 'token': 'accounts.serializers.token.CustomTokenObtainPairSerializer',
        # 'token_create': 'accounts.serializers.token.CustomTokenObtainPairSerializer',
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
}


__all__ = imports
