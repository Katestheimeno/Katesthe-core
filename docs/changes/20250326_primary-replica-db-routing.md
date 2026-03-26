# Change: Primary/replica DB routing and removal of DATABASE_URL

**Date:** 2025-03-26  
**Prompt scope:** Implement primary/replica routing; migrate off `DATABASE_URL` / `dj-database-url` to explicit `DB_PRIMARY_*` / `DB_REPLICA_*`.

## Summary

Django `DATABASES` are built from explicit environment variables. `PrimaryReplicaRouter` sends writes to `default` and reads to healthy replicas when `DB_ROUTING_ENABLED` is true. `read_from_primary()` and `DBConsistencyMiddleware` support read-after-write consistency. The `dj-database-url` dependency was removed.

## Files modified / added

| Path | Nature of change |
|------|------------------|
| `config/settings/config.py` | `DB_PRIMARY_*`, `DB_REPLICA_*`, `USE_SQLITE`, `DB_ROUTING_ENABLED`; removed `DatabaseSettings` / `DATABASE_URL` |
| `config/settings/database.py` | Explicit Postgres/SQLite config, replicas, router registration |
| `config/settings/__init__.py` | Removed `DATABASE_URL` export |
| `config/db_router.py` | New |
| `config/db_utils.py` | New |
| `config/middleware/db_consistency.py` | New |
| `config/settings/apps_middlewares.py` | `DBConsistencyMiddleware` |
| `config/django/test.py` | Routing disabled for tests |
| `config/tests/test_db_router.py` | New |
| `pyproject.toml` / `uv.lock` | Removed `dj-database-url` |
| `docker-compose.yml`, `.env*.example`, `env.docker.example` | `DB_PRIMARY_*`; PgBouncer `DATABASE_URL` uses `DB_PRIMARY_*` substitution |
| `README.md`, `config/pgbouncer/README.md`, `docs/db-primary-replica.md` | Documentation |
| `.cursor/rules/00-django-security.mdc` | Env variable reference |

## Related tests

| File | Coverage |
|------|----------|
| `config/tests/test_db_router.py` | Router, `read_from_primary`, middleware |

## Application audit (read-after-write)

No controller/service changes were required: Djoser/DRF flows return updated instances without an immediate ORM re-fetch to a replica after write under typical paths.
