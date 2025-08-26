"""
drf-spectacular settings for OpenAPI schema and UIs.
Path: config/settings/spectacular.py
"""

imports = []

imports += ["SPECTACULAR_SETTINGS"]

SPECTACULAR_SETTINGS = {
    # Basic info
    'TITLE': 'DRF-Starter API',
    'DESCRIPTION': '''
    # DRF-Starter Backend API Documentation

    This is a **Django REST Framework starter project** with ready-to-use authentication,
    custom user management, and modular app structure.

    ## Features
    - JWT authentication
    - Custom User model
    - Modular app structure
    - DRF-Starter conventions
    ''',
    'VERSION': '1.0.0',

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
                'primary': {'main': '#6a0dad'},       # purple
                'accent': {'main': '#4b0082'},        # dark purple
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
    # 'CONTACT': {
    #     'name': 'DRF-Starter Dev Team',
    #     'email': 'support@drf-starter.com',
    #     'url': 'https://github.com/your-repo/drf-starter',
    # },
    # 'LICENSE': {
    #     'name': 'MIT License',
    #     'url': 'https://opensource.org/licenses/MIT',
    # },
    # 'EXTERNAL_DOCS': {
    #     'description': 'DRF-Starter Docs',
    #     'url': 'https://drf-starter-docs.com',
    # },
}


__all__ = imports
