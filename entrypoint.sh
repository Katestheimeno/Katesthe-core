#!/bin/sh
set -e

echo "Running migrations..."
uv run python manage.py migrate

echo "Starting Django server..."
exec uv run daphne -b 0.0.0.0 -p ${WEB_PORT:-8000} config.asgi:application
