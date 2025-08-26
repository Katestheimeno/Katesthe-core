"""
Project URL routing.
Path: config/urls.py

Includes admin, app API routes, and dev-only docs/tools under DEBUG.
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
