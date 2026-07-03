#!/bin/sh
set -e

# Ensure .venv exists in the container volume (avoids host .venv permission issues)
echo "Syncing dependencies..."
uv sync --frozen

echo "Running migrations..."
# Retry: DNS for compose service names (e.g. pgbouncer) can lag right after containers start.
attempt=1
while [ "$attempt" -le 30 ]; do
  if uv run python manage.py migrate; then
    break
  fi
  if [ "$attempt" -eq 30 ]; then
    echo "migrate failed after 30 attempts"
    exit 1
  fi
  echo "migrate failed (attempt $attempt/30), retrying in 2s..."
  attempt=$((attempt + 1))
  sleep 2
done

echo "Collecting static files..."
uv run python manage.py collectstatic --noinput

echo "Starting Django server..."
# ── Determine worker count ──
# WEB_WORKERS: 2 * CPU + 1 is the standard formula.
# os.cpu_count() on containerised platforms returns the HOST CPU count,
# not the allocated vCPU. Cap at 4 cores to prevent spawning too many
# workers on a small container (~100 MB each → OOM).
WEB_WORKERS="${WEB_WORKERS:-0}"
if [ "$WEB_WORKERS" = "0" ]; then
    CPU_COUNT=$(uv run python -c "import os; print(min(os.cpu_count() or 2, 4))")
    WEB_WORKERS=$((CPU_COUNT * 2 + 1))
fi

CONTAINER_PORT="${WEB_PORT:-8000}"

if [ "${DJANGO_DEBUG:-False}" = "True" ]; then
    echo "DEBUG mode — starting Uvicorn with auto-reload (single worker)..."
    exec uv run uvicorn config.asgi:application \
        --host 0.0.0.0 \
        --port "${CONTAINER_PORT}" \
        --reload \
        --reload-dir /app \
        --reload-exclude 'logs' \
        --reload-exclude 'media' \
        --reload-exclude 'staticfiles' \
        --reload-exclude 'static' \
        --reload-exclude '.venv'
else
    echo "Production — starting Gunicorn + Uvicorn workers (${WEB_WORKERS} workers)..."
    exec uv run gunicorn config.asgi:application \
        --bind "0.0.0.0:${CONTAINER_PORT}" \
        --workers "${WEB_WORKERS}" \
        --worker-class uvicorn.workers.UvicornWorker \
        --max-requests 1000 \
        --max-requests-jitter 50 \
        --graceful-timeout 30 \
        --timeout 120 \
        --keep-alive 5 \
        --access-logfile - \
        --error-logfile - \
        --log-level warning
fi
