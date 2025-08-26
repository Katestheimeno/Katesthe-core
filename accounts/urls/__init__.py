# accounts/urls/__init__.py
# This file acts as the central URL router for the "accounts" app.
# It imports and exposes all sub-URL patterns (currently only auth-related).

from ._auth import urlpatterns as auth_urlpatterns  # Import auth URLs

# Combine all URL patterns for this app
urlpatterns = [
    *auth_urlpatterns,  # Spread operator to include all auth URLs
]
