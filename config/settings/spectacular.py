"""
drf-spectacular settings for OpenAPI schema and UIs.
Path: config/settings/spectacular.py
"""

from config.env import PROJECT_NAME, PROJECT_DESCRIPTION, PROJECT_VERSION, CONTACT_NAME, CONTACT_EMAIL, CONTACT_URL, THEME_PRIMARY_COLOR, THEME_ACCENT_COLOR

imports = []

imports += ["SPECTACULAR_SETTINGS"]

SPECTACULAR_SETTINGS = {
    # Basic info
    'TITLE': f'{PROJECT_NAME} API',
    'DESCRIPTION': f'''
    # {PROJECT_NAME} Backend API Documentation

    {PROJECT_DESCRIPTION}

    ## Features
    - JWT authentication
    - Custom User model
    - Modular app structure
    - {PROJECT_NAME} conventions
    ''',
    'VERSION': PROJECT_VERSION,

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
                    'primary': {'main': THEME_PRIMARY_COLOR},       # configurable primary color
                    'accent': {'main': THEME_ACCENT_COLOR},        # configurable accent color
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

    # Tags to organize endpoints
    'TAGS': [
        # {'name': 'Authentication', 'description': 'User auth and token management'},
        # {'name': 'Users', 'description': 'User profile and management'},
    ],

    # Contact and license info
    'CONTACT': {
        'name': CONTACT_NAME,
        'email': CONTACT_EMAIL,
        'url': CONTACT_URL,
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
