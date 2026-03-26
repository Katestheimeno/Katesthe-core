# Changelog

## [Unreleased]

### Fixed

- Docker `db_replica`: primary now uses a mounted `pg_hba.conf` (`hba_file`) so replication connections from the Docker network match `host replication` / `hostnossl` rules (PostgreSQL’s `all` does not match replication DB). Replica entrypoint creates/updates `replicator` with `REPLICATOR_PASSWORD` before `pg_basebackup` so existing primary volumes work without manual SQL.

### Changed

- `DB_ROUTING_ENABLED` now defaults to `true` and registers `PrimaryReplicaRouter` whenever Postgres is used; with no `DB_REPLICA_HOSTS`, reads still use the primary. Set `DB_ROUTING_ENABLED=false` to disable the router.

### Added

- Docker Compose streaming read replica (`db_replica`): primary init scripts under `docker/postgres/primary/`, replica entrypoint `docker/postgres/replica/docker-entrypoint-replica.sh`, `REPLICATOR_PASSWORD`, and example `DB_REPLICA_HOSTS=db_replica` for local read traffic splitting.
- Primary/read-replica database routing: `config/db_router.PrimaryReplicaRouter`, `config/db_utils.read_from_primary`, `config.middleware.db_consistency.DBConsistencyMiddleware`, and settings symbols `REPLICA_DATABASE_ALIASES`, `DB_ROUTING_ENABLED`, `DATABASE_ROUTERS` when replicas are enabled.
- Environment variables `DB_PRIMARY_*`, `DB_REPLICA_*`, `USE_SQLITE`, and `DB_ROUTING_ENABLED` in `config/settings/config.py` (replaces app-level `DATABASE_URL`).

### Changed

- Database configuration is built from explicit `DB_PRIMARY_*` fields instead of `dj-database-url` / `DATABASE_URL`.

### Removed

- `dj-database-url` dependency.

See: `docs/changes/20250326_primary-replica-db-routing.md`, `docs/changes/20250326_docker-streaming-replica-read-splitting.md`
