"""
Infrastructure tasks — keep-warm, health probes.
Path: utils/tasks.py
"""

import os
import urllib.request
import urllib.error

from celery import shared_task
from django.db import connection

from config.logger import logger

_HEALTH_PING_URL = os.getenv("HEALTH_PING_URL", "").rstrip("/")


@shared_task(
    name="utils.tasks.keep_warm",
    time_limit=15,
    soft_time_limit=12,
    ignore_result=True,
)
def keep_warm():
    """
    Periodic ping that prevents cold-start latency on PaaS deployments.

    1. Runs SELECT 1 on the default DB (warms the worker's connection pool).
    2. If HEALTH_PING_URL is set, GETs <url>/api/v1/health/ to keep the
       API process and its DB connection warm too.

    Never raises — HTTP failures are logged as warnings so a flaky ping
    never fails the periodic task.
    """
    with connection.cursor() as cursor:
        cursor.execute("SELECT 1")
    logger.debug("keep_warm.db_ok")

    if not _HEALTH_PING_URL:
        return

    url = f"{_HEALTH_PING_URL}/api/v1/health/"
    try:
        req = urllib.request.Request(url, method="GET")
        with urllib.request.urlopen(req, timeout=10) as resp:
            status = resp.getcode()
        logger.bind(url=url, status=status).info("keep_warm.ping_ok")
    except urllib.error.HTTPError as exc:
        logger.bind(url=url, status=exc.code).warning("keep_warm.ping_http_error")
    except Exception as exc:
        logger.bind(url=url, error=str(exc)).warning("keep_warm.ping_failed")
