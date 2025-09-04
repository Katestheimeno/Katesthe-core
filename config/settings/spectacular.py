"""
drf-spectacular settings for OpenAPI schema and UIs.
Path: config/settings/spectacular.py
"""

from config.settings.config import settings

imports = []

imports += ["SPECTACULAR_SETTINGS"]

SPECTACULAR_SETTINGS = {
    # Basic info
    'TITLE': f'{settings.PROJECT_NAME} API',
    'DESCRIPTION': f'''
    # {settings.PROJECT_NAME} Backend API Documentation

    {settings.PROJECT_DESCRIPTION}

    ## Features
    - JWT authentication
    - Custom User model
    - Modular app structure
    - {settings.PROJECT_NAME} conventions
    ''',
    'VERSION': settings.PROJECT_VERSION,

    # Serve settings
    'SERVE_INCLUDE_SCHEMA': False,  # do not expose /schema.json
    'SERVE_PUBLIC': True,            # accessible without auth

    # Swagger UI settings
    'SWAGGER_UI_SETTINGS': {
        'deepLinking': True,
        'persistAuthorization': True,
        'displayOperationId': True,
        'defaultModelsExpandDepth': 2,
        'defaultModelExpandDepth': 1,
        'displayRequestDuration': True,
        'docExpansion': 'list',
        'filter': True,
        'showExtensions': True,
        'showCommonExtensions': True,
        'syntaxHighlight': True,
        'syntaxHighlight.theme': 'obsidian',  # dark theme
    },

    # ReDoc settings
    'REDOC_UI_SETTINGS': {
        'hideDownloadButton': False,
        'hideHostname': False,
        'hideLoading': False,
        'nativeScrollbars': False,
        'pathInMiddlePanel': True,
        'requiredPropsFirst': True,
        'scrollYOffset': 0,
        'showExtensions': True,
        'sortPropsAlphabetically': True,
        'suppressWarnings': False,
                    'theme': {
                'colors': {
                    'primary': {'main': settings.THEME_PRIMARY_COLOR},       # configurable primary color
                    'accent': {'main': settings.THEME_ACCENT_COLOR},        # configurable accent color
                    'success': {'main': '#28a745'},
                    'error': {'main': '#dc3545'},
                },
            'typography': {
                'fontSize': '14px',
                'fontFamily': 'Roboto, sans-serif',
            },
        },
    },

    # JWT Security
    'SECURITY': [
        {
            'Bearer': []
        }
    ],

    # Schema splitting and prefix
    'COMPONENT_SPLIT_REQUEST': True,
    'SCHEMA_PATH_PREFIX': '/api/v1/',
    'SCHEMA_PATH_PREFIX_TRIM': False,
    
    # Operation ID generation
    'OPERATION_ID_GENERATOR': 'drf_spectacular.generators.operation_id_generator',
    'GENERATE_OPERATION_ID': True,
    
    # Reduce warnings
    'SERVE_AUTHENTICATION': None,
    'SWAGGER_UI_OAUTH2_REDIRECT_URL': None,

    # Tags to organize endpoints
    'TAGS': [
        # {'name': 'Authentication', 'description': 'User auth and token management'},
        # {'name': 'Users', 'description': 'User profile and management'},
    ],

    # Contact and license info
    'CONTACT': {
        'name': settings.CONTACT_NAME,
        'email': settings.CONTACT_EMAIL,
        'url': settings.CONTACT_URL,
    },
    'LICENSE': {
        'name': 'MIT License',
        'url': 'https://opensource.org/licenses/MIT',
    },
    # 'EXTERNAL_DOCS': {
    #     'description': f'{PROJECT_NAME} Docs',
    #     'url': f'{CONTACT_URL}/docs',
    # },
}


__all__ = imports
