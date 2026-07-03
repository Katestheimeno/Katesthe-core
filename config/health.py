"""Liveness and readiness endpoints.

- /health/  -> `liveness`: process-is-up, no dependencies probed. Load-balancer / k8s liveness.
- /ready/   -> `readiness`: probes DB, Redis, Celery broker. Returns 503 when any dep is down.

Two settings objects are involved here:
- `django.conf.settings` (Django runtime globals) — used for `CELERY_TASK_ALWAYS_EAGER`.
- `config.settings.config.settings` (pydantic app config) — used for `REDIS_URL`.
Using the wrong one for `CELERY_TASK_ALWAYS_EAGER` raises `AttributeError`, since the
pydantic `MainSettings` model has no such field.
"""
from __future__ import annotations

import redis
from django.conf import settings as dj_settings
from django.db import connection
from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt

from config.logger import logger
from config.settings.config import settings as app_settings

_REDIS_TIMEOUT_S = 1.0
_CELERY_PING_TIMEOUT_S = 1.0


@csrf_exempt
def liveness(request):
    """Return 200 plain text — no DB, no deps; safe for GET /health/."""
    return HttpResponse("ok", content_type="text/plain", status=200)


def _check_db() -> tuple[bool, str]:
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
        return True, "ok"
    except Exception as exc:  # pragma: no cover - error path exercised via mock
        return False, f"fail:{exc.__class__.__name__}"


def _check_redis() -> tuple[bool, str]:
    client = None
    try:
        client = redis.from_url(app_settings.REDIS_URL, socket_timeout=_REDIS_TIMEOUT_S)
        client.ping()
        return True, "ok"
    except Exception as exc:
        return False, f"fail:{exc.__class__.__name__}"
    finally:
        if client is not None:
            client.close()


def _check_celery() -> tuple[bool, str]:
    # In tests / eager mode there is no worker pool; treat as OK. Read this flag from
    # the Django settings — the pydantic settings object has no such field.
    if getattr(dj_settings, "CELERY_TASK_ALWAYS_EAGER", False):
        return True, "eager"
    try:
        from config.celery import app as celery_app

        replies = celery_app.control.ping(timeout=_CELERY_PING_TIMEOUT_S)
        if not replies:
            return False, "fail:no_workers"
        return True, "ok"
    except Exception as exc:
        return False, f"fail:{exc.__class__.__name__}"


@csrf_exempt
def readiness(request):
    """Probe DB + Redis + Celery broker; 200 when all green, 503 otherwise."""
    db_ok, db_detail = _check_db()
    redis_ok, redis_detail = _check_redis()
    celery_ok, celery_detail = _check_celery()

    payload = {
        "db": {"ok": db_ok, "detail": db_detail},
        "redis": {"ok": redis_ok, "detail": redis_detail},
        "celery": {"ok": celery_ok, "detail": celery_detail},
    }
    all_ok = db_ok and redis_ok and celery_ok
    if not all_ok:
        logger.bind(**payload).warning("health.readiness.fail")
    return JsonResponse(payload, status=200 if all_ok else 503)
