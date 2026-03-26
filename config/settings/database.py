"""
Database and cache configuration.
Path: config/settings/database.py

Builds DATABASES from explicit DB_PRIMARY_* / DB_REPLICA_* (no DATABASE_URL).
Configures Redis cache.
"""

import logging

from config.settings import SQLITE_DATABASE_PATH
from config.settings.config import settings

logger = logging.getLogger(__name__)

# ------------------------------------------------------------
# Imports Collector
# ------------------------------------------------------------
imports = []


def _use_postgres() -> bool:
    if settings.USE_SQLITE:
        return False
    return bool(settings.DB_PRIMARY_HOST and settings.DB_PRIMARY_HOST.strip())


def _primary_postgres() -> dict:
    """PgBouncer-friendly primary connection (transaction pooling)."""
    return {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": settings.DB_PRIMARY_NAME,
        "USER": settings.DB_PRIMARY_USER,
        "PASSWORD": settings.DB_PRIMARY_PASSWORD,
        "HOST": settings.DB_PRIMARY_HOST.strip(),
        "PORT": settings.DB_PRIMARY_PORT,
        "CONN_MAX_AGE": 0,
        "DISABLE_SERVER_SIDE_CURSORS": True,
        "CONN_HEALTH_CHECKS": True,
    }


def _replica_postgres(host: str) -> dict:
    cfg = _primary_postgres()
    cfg["HOST"] = host.strip()
    port = settings.DB_REPLICA_PORT if settings.DB_REPLICA_PORT is not None else settings.DB_PRIMARY_PORT
    cfg["PORT"] = port
    cfg["USER"] = settings.DB_REPLICA_USER or settings.DB_PRIMARY_USER
    cfg["PASSWORD"] = (
        settings.DB_REPLICA_PASSWORD
        if settings.DB_REPLICA_PASSWORD
        else settings.DB_PRIMARY_PASSWORD
    )
    cfg["NAME"] = settings.DB_REPLICA_NAME or settings.DB_PRIMARY_NAME
    cfg["TEST"] = {"MIRROR": "default"}
    return cfg


# ------------------------------------------------------------
# Database Settings
# ------------------------------------------------------------
imports += ["DATABASES"]

if _use_postgres():
    DATABASES: dict = {"default": _primary_postgres()}
    hosts = [h.strip() for h in settings.DB_REPLICA_HOSTS.split(",") if h.strip()]
    REPLICA_DATABASE_ALIASES: list[str] = []
    for i, host in enumerate(hosts):
        alias = f"replica_{i}"
        DATABASES[alias] = _replica_postgres(host)
        REPLICA_DATABASE_ALIASES.append(alias)

    # Mirrors env flag: router is active when True; with no replicas, reads still resolve to primary.
    DB_ROUTING_ENABLED: bool = bool(settings.DB_ROUTING_ENABLED)
    if DB_ROUTING_ENABLED:
        DATABASE_ROUTERS = ["config.db_router.PrimaryReplicaRouter"]
    else:
        DATABASE_ROUTERS = []
    imports += ["REPLICA_DATABASE_ALIASES", "DB_ROUTING_ENABLED", "DATABASE_ROUTERS"]
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": str(SQLITE_DATABASE_PATH / "db.sqlite3"),
        }
    }
    REPLICA_DATABASE_ALIASES = []
    DB_ROUTING_ENABLED = False
    DATABASE_ROUTERS = []
    imports += ["REPLICA_DATABASE_ALIASES", "DB_ROUTING_ENABLED", "DATABASE_ROUTERS"]

# ------------------------------------------------------------
# Default Primary Key Field Type
# ------------------------------------------------------------
imports += ["DEFAULT_AUTO_FIELD"]

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

imports += ["CACHES"]
# Cache configuration (Redis with fallback to local memory)
try:
    CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.redis.RedisCache",
            "LOCATION": settings.REDIS_URL,
            "KEY_PREFIX": "django_cache",
            "TIMEOUT": 300,
        }
    }
except Exception as e:
    logger.warning("Redis cache configuration failed: %s — using locmem", e)
    CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
            "LOCATION": "unique-snowflake",
        }
    }

# ------------------------------------------------------------
# Explicit Exports
# ------------------------------------------------------------
__all__ = imports
