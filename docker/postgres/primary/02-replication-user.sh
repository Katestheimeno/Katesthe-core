#!/bin/bash
# Runs once on empty primary data dir (docker-entrypoint-initdb.d).
# Creates a replication role for pg_basebackup / streaming standby (db_replica service).
set -e
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
CREATE USER replicator WITH REPLICATION ENCRYPTED PASSWORD '${REPLICATOR_PASSWORD}';
EOSQL
