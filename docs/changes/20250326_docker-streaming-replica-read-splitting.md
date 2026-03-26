# Change: Docker streaming replica + read-after-write routing

**Date:** 2025-03-26  
**Prompt scope:** Enable read-replica traffic splitting in Docker and route ORM reads correctly after writes where needed.

---

## Summary

Added a `db_replica` Postgres standby (streaming replication) to `docker-compose.yml`, primary **`pg_hba.conf`** mounted via `hba_file` (replication cannot use `database` = `all` rules), primary init scripts under `docker/postgres/primary/`, and a replica entrypoint that **ensures `replicator` on the primary** (idempotent `CREATE`/`ALTER`) then runs `pg_basebackup`. Default env examples set `DB_REPLICA_HOSTS=db_replica` so Django exposes `replica_0` and `PrimaryReplicaRouter` sends reads to the replica when healthy. `CustomUserViewSet` calls `force_primary_for_request()` after `perform_create` / `perform_update` / `perform_destroy`; user activation uses `read_from_primary()` for activation reads; `HistoryModel._track_changes` loads the prior row inside `read_from_primary()`.

## Files Modified

| File | Nature of change |
|------|------------------|
| `docker-compose.yml` | `db_replica` service, primary `wal_level` + init mount, `postgres_replica_data`, web/celery depend on replica healthy |
| `docker/postgres/primary/*.sh` | Replication user + `pg_hba` for replication |
| `docker/postgres/replica/docker-entrypoint-replica.sh` | Standby bootstrap |
| `.env.local`, `.env.local.example`, `env.docker.example` | `DB_REPLICA_HOSTS`, `REPLICATOR_PASSWORD` |
| `accounts/controllers/_auth.py` | `perform_*` + activation `read_from_primary` |
| `utils/models/_history.py` | `_track_changes` + `read_from_primary` |
| `accounts/tests/controllers/test_auth.py` | `TestCustomUserViewSetReadAfterWritePrimaryPin` |
| `README.md`, `docs/db-primary-replica.md`, `CHANGELOG.md` | Documentation |

## Related Tests

| Test | Coverage |
|------|----------|
| `accounts/tests/controllers/test_auth.py::TestCustomUserViewSetReadAfterWritePrimaryPin::*` | `force_primary_for_request` after `perform_*` |

## Documentation Updated

- `README.md` (database / Docker replica section)
- `docs/db-primary-replica.md` (Docker `db_replica` subsection)
- `CHANGELOG.md`
