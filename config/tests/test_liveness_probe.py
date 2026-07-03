"""
Tests for config/middleware/liveness_probe.py — LivenessProbeMiddleware.
Path: config/tests/test_liveness_probe.py
"""

import json

import pytest
from django.conf import settings
from django.http import HttpResponse
from django.test import RequestFactory

from config.middleware.liveness_probe import LIVENESS_PATH, LivenessProbeMiddleware


@pytest.fixture
def rf():
    return RequestFactory()


@pytest.fixture
def downstream_called():
    """Track whether `get_response` was invoked (i.e. no short-circuit)."""
    calls = []

    def get_response(request):
        calls.append(request)
        return HttpResponse(status=200)

    return calls, get_response


class TestLivenessPath:
    def test_get_on_liveness_path_returns_200_alive_payload(self, rf, downstream_called):
        _, get_response = downstream_called
        middleware = LivenessProbeMiddleware(get_response=get_response)
        request = rf.get(LIVENESS_PATH)

        response = middleware(request)

        assert response.status_code == 200
        assert json.loads(response.content) == {
            "status": "alive",
            "service": settings.PROJECT_NAME,
        }

    def test_get_on_liveness_path_short_circuits_and_skips_downstream(
        self, rf, downstream_called
    ):
        calls, get_response = downstream_called
        middleware = LivenessProbeMiddleware(get_response=get_response)
        request = rf.get(LIVENESS_PATH)

        middleware(request)

        assert calls == []


class TestNonLivenessPath:
    def test_passes_through_to_downstream_for_other_paths(self, rf, downstream_called):
        calls, get_response = downstream_called
        middleware = LivenessProbeMiddleware(get_response=get_response)
        request = rf.get("/api/v1/users/")

        response = middleware(request)

        assert calls == [request]
        assert response.status_code == 200


class TestNonGetMethod:
    def test_post_to_liveness_path_is_not_short_circuited(self, rf, downstream_called):
        calls, get_response = downstream_called
        middleware = LivenessProbeMiddleware(get_response=get_response)
        request = rf.post(LIVENESS_PATH)

        middleware(request)

        assert calls == [request]
