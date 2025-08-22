
imports = []

imports += ["REST_FRAMEWORK"]


REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.BasicAuthentication',
        # 'rest_framework_simplejwt.authentication.JWTAuthentication',
        'rest_framework.authentication.SessionAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
}

imports += ["SPECTACULAR_SETTINGS"]

SPECTACULAR_SETTINGS = {
    'TITLE': 'DRF-Starter API',
    'DESCRIPTION': 'serves as a django rest_framework starting point',
    'VERSION': '1.0.0',
    'SERVE_INCLUDE_SCHEMA': False,
}

__all__ = imports
