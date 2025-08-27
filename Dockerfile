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

# Create non-root user
RUN useradd -m -u 1000 django && \
    mkdir -p /app/service/data && \
    chown -R django:django /app

USER django

EXPOSE ${WEB_PORT:-8000}

HEALTHCHECK --interval=30s --timeout=10s --start-period=5s CMD curl -f http://localhost:${WEB_PORT:-8000}/ || exit 1

CMD ["uv", "run", "python", "manage.py", "runserver_plus", "0.0.0.0:${WEB_PORT:-8000}"]

