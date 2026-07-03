"""
Security response headers not covered by Django's built-in SecurityMiddleware.

- Referrer-Policy    — limit referer header leakage across origins
- Permissions-Policy — opt out of browser features the app never uses
  (camera, microphone, geolocation, payment, etc.)

Path: config/middleware/security_headers.py
"""

from django.conf import settings

# The Permissions-Policy value is a single header controlling which browser
# APIs this origin may use. Locking down features we don't need reduces the
# attack surface for XSS payloads trying to exfiltrate data via sensors.
_PERMISSIONS_POLICY = (
    "accelerometer=(),"
    "camera=(),"
    "display-capture=(),"
    "fullscreen=(self),"
    "geolocation=(),"
    "gyroscope=(),"
    "magnetometer=(),"
    "microphone=(),"
    "payment=(),"
    "usb=()"
)


class SecurityHeadersMiddleware:
    """Add security headers that Django's SecurityMiddleware doesn't provide."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        response.setdefault(
            "Referrer-Policy",
            getattr(settings, "SECURE_REFERRER_POLICY", "strict-origin-when-cross-origin"),
        )
        response.setdefault("Permissions-Policy", _PERMISSIONS_POLICY)
        return response
