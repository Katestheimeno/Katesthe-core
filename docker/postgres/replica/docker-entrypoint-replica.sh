#!/bin/bash
# Streaming standby: ensure replication role on primary, pg_basebackup once, then postgres (recovery).
set -euo pipefail
export PGDATA="${PGDATA:-/var/lib/postgresql/data}"
export PGSSLMODE="${PGSSLMODE:-disable}"

PRIMARY_USER="${DB_PRIMARY_USER:-postgres}"
PRIMARY_PASS="${DB_PRIMARY_PASSWORD:?DB_PRIMARY_PASSWORD must be set for replication bootstrap}"

if [ ! -f "${PGDATA}/standby.signal" ] && [ ! -s "${PGDATA}/PG_VERSION" ]; then
  echo "Waiting for primary to accept connections..."
  until PGPASSWORD="${PRIMARY_PASS}" pg_isready -h db -p 5432 -U "${PRIMARY_USER}"; do
    sleep 2
  done

  # Existing postgres_data volumes may predate init scripts; sync password + REPLICATION privilege.
  echo "Ensuring replication role on primary (idempotent)..."
  PGPASSWORD="${PRIMARY_PASS}" psql -h db -p 5432 -U "${PRIMARY_USER}" -d postgres -v ON_ERROR_STOP=0 -c \
    "CREATE USER replicator WITH REPLICATION ENCRYPTED PASSWORD '${REPLICATOR_PASSWORD}';" 2>/dev/null || true
  PGPASSWORD="${PRIMARY_PASS}" psql -h db -p 5432 -U "${PRIMARY_USER}" -d postgres -v ON_ERROR_STOP=1 -c \
    "ALTER USER replicator WITH REPLICATION PASSWORD '${REPLICATOR_PASSWORD}';"

  echo "Initializing replica from primary (pg_basebackup)..."
  until PGPASSWORD="${REPLICATOR_PASSWORD}" pg_basebackup \
    -h db -p 5432 -U replicator -D "${PGDATA}" -Fp -Xs -P -R; do
    echo "Waiting for primary..."
    sleep 2
  done
fi

exec /usr/local/bin/docker-entrypoint.sh postgres
