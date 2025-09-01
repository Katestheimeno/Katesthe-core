#!/bin/sh
set -e

uv run python manage.py migrate
exec uv run daphne -b 0.0.0.0 -p ${WEB_PORT:-8000} config.asgi:application
