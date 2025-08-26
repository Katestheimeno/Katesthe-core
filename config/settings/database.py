"""
Database and cache configuration.
Path: config/settings/database.py

Uses dj-database-url to parse DATABASE_URL and configures Redis cache.
"""

from config.settings import SQLITE_DATABASE_PATH
from config.env import DATABASE_URL, REDIS_URL
from icecream import ic
import dj_database_url


# ------------------------------------------------------------
# Imports Collector
# ------------------------------------------------------------
imports = []


# ------------------------------------------------------------
# Database Settings
# ------------------------------------------------------------
# SQLite is lightweight and ideal for local development and testing.
# For production, replace this with PostgreSQL, MySQL, or another RDBMS.
imports += ["DATABASES"]

DATABASES = {
    'default': dj_database_url.config(
        default=DATABASE_URL,
        conn_max_age=600,
        conn_health_checks=True,
    )
}

# if DATABASE_URL:
#     # Try to use PostgreSQL from environment
#     try:
#         DATABASES = {
#             'default': dj_database_url.config(
#                 default=DATABASE_URL,
#                 conn_max_age=600,
#                 conn_health_checks=True,
#             )
#         }
#         # Test the connection
#         import psycopg2
#         conn = psycopg2.connect(DATABASE_URL)
#         conn.close()
#         ic("✅ Connected to PostgreSQL")
#     except Exception as e:
#         ic(f"⚠️  PostgreSQL connection failed: {e}")
#         ic("🔄 Falling back to SQLite")
#         DATABASES = {
#             'default': {
#                 'ENGINE': 'django.db.backends.sqlite3',
#                 'NAME': SQLITE_DATABASE_PATH / 'db.sqlite3',
#             }
#         }
# else:
#     # Default to SQLite
#     ic("📦 Using SQLite (no DATABASE_URL found)")
#     DATABASES = {
#         'default': {
#             'ENGINE': 'django.db.backends.sqlite3',
#             'NAME': SQLITE_DATABASE_PATH / 'db.sqlite3',
#         }
#     }


# ------------------------------------------------------------
# Default Primary Key Field Type
# ------------------------------------------------------------
# By default, Django uses BigAutoField for primary keys.
# This avoids issues with ID limits on large tables.
imports += ["DEFAULT_AUTO_FIELD"]

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

imports += ["CACHES"]
# Cache configuration (Redis)
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.redis.RedisCache',
        'LOCATION': REDIS_URL,
        'KEY_PREFIX': 'django_cache',
        'TIMEOUT': 300,
    }
}
# ------------------------------------------------------------
# Explicit Exports
# ------------------------------------------------------------
__all__ = imports
