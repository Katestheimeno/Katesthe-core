FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    libjpeg-dev \
    zlib1g-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /usr/local/bin/

WORKDIR /app

# Copy dependency files first to leverage cache
COPY pyproject.toml uv.lock* ./

# Install dependencies
RUN uv sync --frozen

# Copy project code
COPY . .

# Create non-root user and writable dirs (logs, media, static) so no permission issues when running as django
RUN useradd -m -u 1000 django && \
    mkdir -p /app/service/data /var/log/app /var/app/media /var/app/staticfiles && \
    chown -R django:django /app /var/log/app /var/app

ENV LOG_DIR=/var/log/app \
    MEDIA_ROOT=/var/app/media \
    STATIC_ROOT=/var/app/staticfiles

USER django

EXPOSE ${WEB_PORT:-8000}

HEALTHCHECK --interval=30s --timeout=10s --start-period=5s CMD curl -f http://localhost:${WEB_PORT:-8000}/ || exit 1

# only run this in development
# RUN uv run manage.py collectstatic --no-input

CMD ["uv", "run", "daphne", "-b", "0.0.0.0", "-p", "8000", "config.asgi:application"]
