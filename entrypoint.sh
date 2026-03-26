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
# Give app tasks more time to shut down after client disconnect (avoids "took too long to shut down" warnings when browser cancels static requests)
exec uv run daphne -b 0.0.0.0 -p ${WEB_PORT:-8000} --application-close-timeout 30 config.asgi:application
