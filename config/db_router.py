"""
Primary / read-replica database router.

Writes always use ``default`` (primary). Reads use a healthy replica when routing
is enabled; otherwise primary. Thread-local flag forces reads to primary for
read-after-write consistency.
"""

from __future__ import annotations

import random
import threading
import time
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from django.db.models import Model

_local = threading.local()

# Short TTL cache so we do not run SELECT 1 on every ORM read.
_HEALTH_TTL_SEC = 5.0
_replica_health_cache: dict[str, tuple[float, bool]] = {}


def force_primary_for_request() -> None:
    """Pin subsequent reads in this thread to the primary until released."""
    _local.primary_forced = True


def release_primary_for_request() -> None:
    """Clear primary pin for this thread."""
    _local.primary_forced = False


def is_primary_forced() -> bool:
    return bool(getattr(_local, "primary_forced", False))


def _replica_is_healthy(alias: str) -> bool:
    from django.db import connections

    now = time.monotonic()
    cached = _replica_health_cache.get(alias)
    if cached is not None:
        ts, ok = cached
        if now - ts < _HEALTH_TTL_SEC:
            return ok
    try:
        conn = connections[alias]
        conn.ensure_connection()
        with conn.cursor() as cursor:
            cursor.execute("SELECT 1")
        ok = True
    except Exception:
        ok = False
    _replica_health_cache[alias] = (now, ok)
    return ok


def _get_healthy_replica() -> str | None:
    from django.conf import settings

    if not getattr(settings, "DB_ROUTING_ENABLED", False):
        return None
    aliases = getattr(settings, "REPLICA_DATABASE_ALIASES", None) or []
    if not aliases:
        return None
    healthy = [a for a in aliases if _replica_is_healthy(a)]
    if not healthy:
        return None
    return random.choice(healthy)


class PrimaryReplicaRouter:
    """Route writes to primary and reads to a healthy replica when enabled."""

    def db_for_read(self, model: type[Model], **hints: Any) -> str | None:
        from django.conf import settings

        if hints.get("primary"):
            return "default"
        if is_primary_forced():
            return "default"
        if not getattr(settings, "DB_ROUTING_ENABLED", False):
            return "default"
        replica = _get_healthy_replica()
        return replica if replica else "default"

    def db_for_write(self, model: type[Model], **hints: Any) -> str | None:
        return "default"

    def allow_relation(self, obj1: Any, obj2: Any, **hints: Any) -> bool:
        return True

    def allow_migrate(
        self,
        db: str,
        app_label: str,
        model_name: str | None = None,
        **hints: Any,
    ) -> bool:
        return db == "default"
