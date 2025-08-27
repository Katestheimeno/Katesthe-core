"""
Test-specific URL routing.
Path: config/urls_test.py

This file contains routes that should be available during testing.
It excludes development-only routes like Silk profiling.
"""

from django.contrib import admin
from django.urls import path, include
from django.views.generic.base import RedirectView


# Prefix for API versioning
API_PREFIX = "api/"
V1_PREFIX = f"{API_PREFIX}v1/"


def v1_url(url: str) -> str:
    """Helper to prepend v1 prefix to given url string."""
    return V1_PREFIX + url


urlpatterns = [
    # Django Admin
    path("admin/", admin.site.urls),
    path('', RedirectView.as_view(url='admin/')),
    path(v1_url(""), include("accounts.urls")),
]
