"""
URL configuration for the project.

This module defines the URL routing for the Django project. It includes:
- Core admin panel.
- Authentication routes (via Django REST Framework).
- Optional developer/debugging tools and API documentation when DEBUG is enabled.

Conditional Routes (DEBUG only):
- Silk: Profiling and query analysis UI.
- Rosetta: Translation interface for managing i18n.
- Spectacular: OpenAPI schema and documentation UIs (Swagger / ReDoc).

Note:
- Routes behind DEBUG should not be exposed in production for security reasons.
"""

from django.conf import settings as cfg
from django.contrib import admin
from django.urls import path, include, re_path
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularRedocView,
    SpectacularSwaggerView,
)


urlpatterns = [
    # Django Admin
    path("admin/", admin.site.urls),
    path("api/v1/", include("accounts.urls")),
]

if cfg.DEBUG:
    urlpatterns += [
        # Silk: database and request profiling
        path("silk/", include("silk.urls", namespace="silk")),

        # Rosetta: translation management
        re_path(r"^rosetta/", include("rosetta.urls")),

        # API Schema (OpenAPI)
        path("api/schema/", SpectacularAPIView.as_view(), name="schema"),

        # Swagger UI (interactive API docs)
        path(
            "api/schema/docs/",
            SpectacularSwaggerView.as_view(url_name="schema"),
            name="swagger-ui",
        ),

        # ReDoc UI (alternative API docs)
        path(
            "api/schema/redoc/",
            SpectacularRedocView.as_view(url_name="schema"),
            name="redoc",
        ),
    ]
