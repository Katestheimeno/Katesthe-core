#!/bin/sh
set -e

# Ensure .venv exists in the container volume (avoids host .venv permission issues)
echo "Syncing dependencies..."
uv sync --frozen

echo "Running migrations..."
uv run python manage.py migrate

echo "Collecting static files..."
uv run python manage.py collectstatic --noinput

echo "Starting Django server..."
# Give app tasks more time to shut down after client disconnect (avoids "took too long to shut down" warnings when browser cancels static requests)
exec uv run daphne -b 0.0.0.0 -p ${WEB_PORT:-8000} --application-close-timeout 30 config.asgi:application
