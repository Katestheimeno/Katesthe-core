"""
Development-only URL routing.
Path: config/urls_dev.py

This file contains routes that should only be available
when DEBUG = True. These include:
- Static & media file serving (for local dev only, never in production).
- Profiling/debugging tools like Silk.
- Translation management with Rosetta.
- Interactive API docs with DRF Spectacular.
"""

from django.conf import settings as cfg
from django.views.static import serve
from django.urls import path, include, re_path
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularRedocView,
    SpectacularSwaggerView,
)

urlpatterns = [

    # Serve uploaded media files in development
    # In production, media should be served by Nginx or a CDN (e.g., S3 + CloudFront).
    re_path(r"^media/(?P<path>.*)$", serve, {"document_root": cfg.MEDIA_ROOT}),

    # Serve static files (JS, CSS, images) in development
    # In production, handled by collectstatic + Whitenoise or a CDN.
    re_path(r"^static/(?P<path>.*)$", serve,
            {"document_root": cfg.STATIC_ROOT}),

    # Silk: Django application profiling (SQL queries, cache, requests, etc.)
    # Useful to debug performance during development.
    path("silk/", include("silk.urls", namespace="silk")),

    # Rosetta: Web-based interface for translating Django apps.
    # Helps manage i18n/l10n in development.
    re_path(r"^rosetta/", include("rosetta.urls")),

    # API schema endpoint (OpenAPI 3.0)
    # Exposes machine-readable API schema used by tools/docs.
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),

    # Swagger UI: Interactive API documentation
    # Lets developers test endpoints directly in the browser.
    path(
        "api/schema/docs/",
        SpectacularSwaggerView.as_view(url_name="schema"),
        name="swagger-ui",
    ),

    # ReDoc UI: Alternative API documentation
    # Provides a cleaner, more structured API reference view.
    path(
        "api/schema/redoc/",
        SpectacularRedocView.as_view(url_name="schema"),
        name="redoc",
    ),
]
