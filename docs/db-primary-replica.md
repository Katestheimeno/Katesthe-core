
# Django primary vs replica database routing — implementation guide

**Katesthe-core:** Django is configured with explicit `DB_PRIMARY_*` / `DB_REPLICA_*` environment variables only — there is **no** `DATABASE_URL` or `dj-database-url` for the application. `DB_ROUTING_ENABLED` defaults to **true** (router registered); with an empty `DB_REPLICA_HOSTS`, reads remain on the primary. See `config/settings/database.py` and `config/settings/config.py`.

### Docker Compose: streaming replica (`db_replica`)

The repo ships `docker-compose.yml` with a **second Postgres service** (`db_replica`) built via `pg_basebackup` from the primary (`db`). Set `DB_REPLICA_HOSTS=db_replica` (and keep `REPLICATOR_PASSWORD` aligned) so Django registers `replica_0` and the router sends **reads** to the standby.

- **Primary `pg_hba.conf`:** The primary uses a **mounted** `docker/postgres/primary/pg_hba.conf` and `hba_file` in the Postgres command. In PostgreSQL, **`database` = `all` does not match replication connections**, so replication from the Docker network must be allowed explicitly (see file comments).
- **Replication user:** `docker/postgres/primary/02-replication-user.sh` creates `replicator` on first DB init. **Existing** `postgres_data` volumes may predate that; the replica entrypoint (`docker/postgres/replica/docker-entrypoint-replica.sh`) runs **idempotent** `CREATE`/`ALTER` as the superuser (`DB_PRIMARY_*`) so `replicator` exists and its password matches `REPLICATOR_PASSWORD` before `pg_basebackup`.

This document describes the **production-style** primary + read-replica setup used in Rhitoric-core: writes always hit the primary (`default`), reads go to a **healthy** replica when routing is enabled, with explicit escape hatches for **read-after-write** consistency.

**Audience:** New projects that follow the **same structure and philosophy** as this repo: a `config/` package for Django settings and cross-cutting infrastructure, domain apps (`accounts/`, `game/`, etc.) for product code, services/selectors/controllers layering, and Cursor rules under `.cursor/rules/`. Copy the files below verbatim (or symlink from this repo), wire settings as described, and routing behaves the same way.

---

## 1. Alignment with Rhitoric-core

| Area | Convention |
|------|------------|
| **Settings package** | `config/` — not `settings.py` at repo root only; split modules under `config/settings/` (e.g. `database.py`, `apps_middlewares.py`) composed into `config/django/base.py`. |
| **Router utilities** | `config/db_router.py`, `config/db_utils.py` — import paths used everywhere: `from config.db_utils import read_from_primary`. |
| **Middleware** | `config/middleware/db_consistency.py` — `DBConsistencyMiddleware` registered in `config/settings/apps_middlewares.py`. |
| **Tests** | `config/tests/test_db_router.py` mirrors router behavior; app tests use `--ds=config.django.test` which forces SQLite and **disables** replica routing (see below). |
| **Docs / AI rules** | `.cursor/rules/12-db-routing-primary-replica.mdc` — read-after-write rules for contributors; keep in sync when behavior changes. |

**Source of truth in this repo:** Prefer reading the live files over duplicating logic here:

- `config/db_router.py`
- `config/db_utils.py`
- `config/middleware/db_consistency.py`
- `config/settings/database.py`
- `config/settings/apps_middlewares.py` (`MIDDLEWARE` order)
- `config/django/test.py` (routing off for tests)
- `config/tests/test_db_router.py`

---

## 2. Behavior summary

| Operation | Destination |
|-----------|-------------|
| Writes (`save`, `create`, `update`, `delete`, migrations) | Primary `default` |
| Reads (default) | A **healthy** replica from `REPLICA_DATABASE_ALIASES`, else primary |
| Reads after `force_primary_for_request()` or `read_from_primary()` | Primary |
| Reads with router hint `hints={"primary": True}` | Primary |

**PgBouncer (transaction pooling):** Routing uses **thread-local flags only**, not connection stickiness or `SET` session state. Rhitoric-core uses `CONN_MAX_AGE = 0` and PgBouncer-safe `OPTIONS` when `DB_PRIMARY_HOST` is set (see `config/settings/database.py`).

---

## 3. Files (under `config/`)

These modules are **canonical** in Rhitoric-core; a new project with the same layout should place them at identical paths so imports and `DATABASE_ROUTERS` stay `config.db_router.PrimaryReplicaRouter`.

### 3.1 `config/db_router.py`

Implements `PrimaryReplicaRouter`, `force_primary_for_request`, `release_primary_for_request`, `is_primary_forced`, and `_get_healthy_replica()` (cached health check + random replica selection). **Do not paste a truncated copy here — copy the file from the repo** or keep it identical to [`config/db_router.py`](../../config/db_router.py).

### 3.2 `config/db_utils.py`

```python
"""Utilities for explicit primary-database routing.

WHEN TO USE read_from_primary():
- Immediately after any write where a subsequent read must see that write.
- In background tasks (Celery) that run after a write and need consistency.
- In API endpoints that create/update and then return the updated object.
"""

from contextlib import contextmanager

from config.db_router import force_primary_for_request, release_primary_for_request


@contextmanager
def read_from_primary():
    force_primary_for_request()
    try:
        yield
    finally:
        release_primary_for_request()


def queryset_on_primary(queryset):
    return queryset.using("default")
```

### 3.3 `config/middleware/db_consistency.py`

Clears thread-local primary pinning at **start and end** of each HTTP request so gunicorn/uWSGI workers do not leak state across requests. **Copy from [`config/middleware/db_consistency.py`](../../config/middleware/db_consistency.py)** — it only imports `release_primary_for_request` from `config.db_router`.

---

## 4. Django settings wiring

### 4.1 `config/settings/database.py` (primary + replica mode)

Rhitoric-core enables the multi-DB block when:

- `USE_POSTGRES` is true, and  
- `DB_PRIMARY_HOST` is set (see `_USE_PRIMARY_REPLICA`).

Then it:

1. Builds `DATABASES['default']` from `DB_PRIMARY_*`.
2. Splits `DB_REPLICA_HOSTS` (comma-separated) and adds `replica_0`, `replica_1`, …
3. Sets `REPLICA_DATABASE_ALIASES = ['replica_0', ...]`.
4. Sets `DB_ROUTING_ENABLED` from env (`DB_ROUTING_ENABLED=true`).
5. When routing is enabled and aliases exist, sets `DATABASE_ROUTERS = ['config.db_router.PrimaryReplicaRouter']`.

Each `replica_*` entry uses the same PgBouncer-friendly options as primary (`CONN_MAX_AGE`, `DISABLE_SERVER_SIDE_CURSORS`, `OPTIONS` without `statement_timeout` in transaction mode if PgBouncer rejects it). Replica definitions include `'TEST': {'MIRROR': 'default'}` so Django tests can point replicas at the same DB as primary when you run Postgres-backed tests with mirrors.

**For a new project:** replicate this file’s structure — env var names and `IMPORTS`/`__all__` pattern can match your existing `config/settings` style.

### 4.2 `config/django/test.py` — routing off

Fast tests use **SQLite in-memory** and explicitly disable routing:

```python
REPLICA_DATABASE_ALIASES = []
DB_ROUTING_ENABLED = False
```

So most of the suite does not need real replicas. Router unit tests in `config/tests/test_db_router.py` use `@override_settings` with SQLite `DATABASES` and mocked `_get_healthy_replica` instead.

### 4.3 `config/settings/apps_middlewares.py` — middleware order

Register `DBConsistencyMiddleware` **early**, immediately after `SecurityMiddleware`:

```python
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "config.middleware.db_consistency.DBConsistencyMiddleware",
    # whitenoise, sessions, cors, common, csrf, auth, ...
]
```

### 4.4 Required settings symbols (names matter)

| Symbol | Role |
|--------|------|
| `DATABASES['default']` | Primary |
| `DATABASES['replica_N']` | Read replicas (same schema via replication) |
| `REPLICA_DATABASE_ALIASES` | List of keys, e.g. `['replica_0']` |
| `DB_ROUTING_ENABLED` | `True` only when router should send reads to replicas |
| `DATABASE_ROUTERS` | `['config.db_router.PrimaryReplicaRouter']` when enabled |

---

## 5. Usage patterns

### 5.1 Default (replica OK)

Ordinary list/detail reads — no code change; router sends reads to a healthy replica.

### 5.2 Read-after-write (scoped) — preferred

```python
from config.db_utils import read_from_primary

obj = MyModel.objects.create(...)
with read_from_primary():
    obj = MyModel.objects.get(pk=obj.pk)
```

Evaluate querysets **inside** `read_from_primary()`. Do not build a queryset outside the block and evaluate later after the context exits.

### 5.3 Read-after-write (whole request)

```python
from config.db_router import force_primary_for_request

# after a write, many reads must see new state
force_primary_for_request()
```

`DBConsistencyMiddleware` clears the flag at request boundaries.

### 5.4 Pin a queryset

```python
from config.db_utils import queryset_on_primary

qs = queryset_on_primary(MyModel.objects.filter(owner=user))
```

### 5.5 Router hint

```python
MyModel.objects.db_manager(hints={"primary": True}).get(pk=pk)
```

### 5.6 Celery / non-request workers

Middleware does not run. Wrap post-write reads in `read_from_primary()` or pair `force_primary_for_request()` / `release_primary_for_request()` in a `finally` block if you cannot use the context manager.

### 5.7 Migrations

Only `default` is migrated (`allow_migrate`). Replicas receive DDL via PostgreSQL replication, not `migrate`.

---

## 6. What not to do

- Do **not** use `.using("replica_0")` in domain code — bypasses health checks and policy.
- Do **not** read from a replica immediately after a write on the primary without `read_from_primary()` / `force_primary_for_request()` (replication lag).
- Do **not** set `DATABASE_ROUTERS` without `REPLICA_DATABASE_ALIASES` and matching `DATABASES` entries.

---

## 7. Tests

Follow `config/tests/test_db_router.py`:

1. `db_for_read` → replica when `_get_healthy_replica` is patched to return an alias.
2. `db_for_read` → `default` when `force_primary_for_request()` or `primary` hint.
3. `db_for_write` → always `default`.
4. `allow_migrate` → `True` only for `default`.
5. `read_from_primary()` restores flag after normal exit and after exception.
6. `DBConsistencyMiddleware` clears the flag around the request.

Run tests: `uv run pytest config/tests/test_db_router.py --ds=config.django.test` (or your project’s equivalent).

---

## 8. Environment variables (Rhitoric-core)

| Variable | Purpose |
|----------|---------|
| `USE_POSTGRES` | Must be enabled for Postgres + primary/replica path |
| `DB_PRIMARY_HOST` | Triggers primary+replica mode when set (with `USE_POSTGRES`) |
| `DB_PRIMARY_PORT` / `DB_PRIMARY_NAME` / `DB_PRIMARY_USER` / `DB_PRIMARY_PASSWORD` | Primary connection |
| `DB_REPLICA_HOSTS` | Comma-separated replica hosts |
| `DB_REPLICA_PORT` / `DB_REPLICA_NAME` / `DB_REPLICA_USER` / `DB_REPLICA_PASSWORD` | Optional; default to primary’s values where applicable |
| `DB_ROUTING_ENABLED` | `true` to register `PrimaryReplicaRouter` |

---

## 9. New-project checklist (same layout as Rhitoric-core)

1. Add `config/db_router.py`, `config/db_utils.py`, `config/middleware/db_consistency.py` (copy from this repo or keep a submodule).
2. Extend `config/settings/database.py` (or equivalent) with the `DB_PRIMARY_*` / `DB_REPLICA_*` block, `REPLICA_DATABASE_ALIASES`, `DB_ROUTING_ENABLED`, `DATABASE_ROUTERS`.
3. Register `config.middleware.db_consistency.DBConsistencyMiddleware` in `config/settings/apps_middlewares.py` after `SecurityMiddleware`.
4. In `config/django/test.py`, keep `REPLICA_DATABASE_ALIASES = []` and `DB_ROUTING_ENABLED = False` for the default SQLite test DB.
5. Copy `.cursor/rules/12-db-routing-primary-replica.mdc` (or merge its rules) so contributors use `read_from_primary()` after writes.
6. Audit write-then-read paths in services, controllers, tasks, and handlers; add `read_from_primary()` or `force_primary_for_request()` as needed.
7. Port `config/tests/test_db_router.py` and run it in CI.

---

## 10. Further reading

- Django: [Multiple databases — automatic routing](https://docs.djangoproject.com/en/stable/topics/db/multi-db/#automatic-database-routing)
- This repo: `.cursor/rules/12-db-routing-primary-replica.mdc`
