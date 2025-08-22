"""
Database Configuration

This file defines the database connection settings for the Django project.

- Default database: SQLite (local development and testing)
- Auto field: BigAutoField is set as the default primary key type
"""

from config.settings import SQLITE_DATABASE_PATH


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
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": SQLITE_DATABASE_PATH / "db.sqlite3",
    }
}


# ------------------------------------------------------------
# Default Primary Key Field Type
# ------------------------------------------------------------
# By default, Django uses BigAutoField for primary keys.
# This avoids issues with ID limits on large tables.
imports += ["DEFAULT_AUTO_FIELD"]

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"


# ------------------------------------------------------------
# Explicit Exports
# ------------------------------------------------------------
__all__ = imports
