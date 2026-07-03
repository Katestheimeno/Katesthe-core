#!/usr/bin/env bash
set -euo pipefail
CONCURRENCY="${CELERY_CONCURRENCY:-2}"
LOGLEVEL="${CELERY_LOG_LEVEL:-info}"
if [ "${DEV_AUTORELOAD:-0}" = "1" ]; then
  exec uv run watchfiles "celery -A config.celery.app worker -l ${LOGLEVEL} -c ${CONCURRENCY} --max-memory-per-child=256000 --max-tasks-per-child=500" .
else
  exec uv run celery -A config.celery.app worker -l "${LOGLEVEL}" -c "${CONCURRENCY}" \
    --max-memory-per-child=256000 --max-tasks-per-child=500
fi
