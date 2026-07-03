"""
Answer GET /api/v1/liveness/ before SessionMiddleware so probes work with an
empty/unreachable DB.

Path: config/middleware/liveness_probe.py
"""

from django.conf import settings
from django.http import JsonResponse

LIVENESS_PATH = "/api/v1/liveness/"


class LivenessProbeMiddleware:
    """Short-circuit the liveness probe path before session/DB middleware runs."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.method == "GET" and request.path == LIVENESS_PATH:
            return JsonResponse(
                {"status": "alive", "service": settings.PROJECT_NAME},
                status=200,
            )
        return self.get_response(request)
