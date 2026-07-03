#!/usr/bin/env bash
set -euo pipefail
LOGLEVEL="${CELERY_LOG_LEVEL:-info}"
if [ "${DEV_AUTORELOAD:-0}" = "1" ]; then
  exec uv run watchfiles "celery -A config.celery.app beat -l ${LOGLEVEL} --scheduler django_celery_beat.schedulers:DatabaseScheduler" .
else
  exec uv run celery -A config.celery.app beat -l "${LOGLEVEL}" --scheduler django_celery_beat.schedulers:DatabaseScheduler
fi
