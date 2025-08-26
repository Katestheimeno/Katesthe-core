"""
Accounts app URL router.
Path: accounts/urls/__init__.py
Aggregates sub-URL patterns (currently authentication).
"""

from ._auth import urlpatterns as auth_urlpatterns  # Import auth URLs

# Combine all URL patterns for this app
urlpatterns = [
    *auth_urlpatterns,
]
