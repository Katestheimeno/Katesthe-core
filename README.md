## KKatesthe-core

A production-ready Django REST Framework starter with an opinionated, domain-driven file architecture, JWT authentication (Djoser + SimpleJWT), Celery background jobs, Redis cache/broker, OpenAPI docs (drf-spectacular), CORS, and a modern Unfold-powered admin.

### Features at a glance
- **Authentication**: Djoser + SimpleJWT (access/refresh), custom `accounts.User`
- **API**: DRF with sensible defaults, filtering (`django-filter`), extensions
- **Docs**: OpenAPI schema + Swagger/Redoc UIs
- **Background jobs**: Celery worker + beat; Flower dashboard
- **Storage**: Postgres via `dj-database-url` (SQLite supported via `DATABASE_URL`)
- **Cache/Broker**: Redis
- **Admin**: Unfold (modern UI) + structured logging via Loguru
- **Dev UX**: uv for env/deps, `django-extensions`, `silk`, `rosetta`, pytest stack


## Requirements
- **Python**: 3.12+
- **uv**: package/dependency manager and venv tool by Astral
  - Install on Linux/macOS:
    ```bash
    curl -LsSf https://astral.sh/uv/install.sh | sh
    ```
  - On Windows (PowerShell):
    ```powershell
    iwr https://astral.sh/uv/install.ps1 -useb | iex
    ```
  - See: `https://astral.sh/uv`
- For full stack locally (optional if you use SQLite):
  - **PostgreSQL** 15+
  - **Redis** 7+
- Or use **Docker** and **docker compose** (ships with `Dockerfile` and `docker-compose.yml`).


## Quickstart (Docker — default)
Because this project is fully dockerized, run Django and management commands inside containers. Running them directly on your host will fail unless you reconfigure `.env` (see Host mode below).

1) Clone and enter the project
```bash
git clone <your-fork-or-origin> drf-starter && cd drf-starter
```

2) Create `.env`
```bash
cp .env.example .env
```
Set secrets:
```bash
# generate a strong value; reuse for SECRET_KEY and JWT_SECRET_KEY (or generate two)
openssl rand -base64 48 | tr -d '\n'
```

3) Start the stack
```bash
docker compose up --build
```

4) Run management commands inside the web container
```bash
# migrations
docker compose exec web uv run python manage.py migrate

# superuser
docker compose exec web uv run python manage.py createsuperuser

# makemigrations
docker compose exec web uv run python manage.py makemigrations

# shell
docker compose exec web uv run python manage.py shell
```

5) Access services
- Web: `http://127.0.0.1:8000`
- Admin: `http://127.0.0.1:8000/admin/`
- Swagger: `http://127.0.0.1:8000/api/schema/docs/`
- Redoc: `http://127.0.0.1:8000/api/schema/redoc/`
- Flower: `http://127.0.0.1:5555`


## Alternative: Host mode (advanced)
If you prefer running Django on your host (outside Docker), you must point your `.env` to services reachable from your host, not the Docker DNS names.

Two options:
- Use the Dockerized Postgres/Redis but connect via localhost (ports are published by compose):
  ```env
  # .env overrides for HOST MODE
  DATABASE_URL=postgresql://postgres:postgres@localhost:5432/drf_starter
  REDIS_URL=redis://localhost:6379/0
  ```
  Then:
  ```bash
  # Ensure db and redis are up
  docker compose up -d db redis

  # Host virtualenv using uv
  uv venv .venv && source .venv/bin/activate  # Windows: .venv\Scripts\activate
  uv sync && uv sync --group dev

  uv run python manage.py migrate
  uv run python manage.py runserver 0.0.0.0:8000
  ```

- Or install Postgres/Redis locally and set `DATABASE_URL`/`REDIS_URL` accordingly.

Important:
- Do not use `db` or `redis` hostnames from your host; those names only resolve inside Docker networks. Use `localhost` with the published ports.


## Configuration (Environment)
The project centralizes env handling in `config/env.py`. Key variables:
- **Core**
  - `SECRET_KEY`: Django secret
  - `JWT_SECRET_KEY`: JWT signing key (used by SimpleJWT)
  - `DJANGO_DEBUG`: `True|False` (Django’s `DEBUG`)
  - `DJANGO_ENV`: `local|production` (informational)
  - `ALLOWED_HOSTS`: CSV list; required in production
- **Database**
  - `DATABASE_URL`: e.g. `postgresql://user:pass@host:5432/dbname` or `sqlite:///database/db.sqlite3`
  - `POSTGRES_*`: used to build `DATABASE_URL` if not set
- **Cache/Broker**
  - `REDIS_URL`: e.g. `redis://localhost:6379/0`

Notes:
- `manage.py` defaults to `config.django.local` settings; Production can use `DJANGO_SETTINGS_MODULE=config.django.production`.
- Database configuration uses `dj-database-url`.
- Use `DJANGO_DEBUG` (boolean) for Django’s debug toggle. The example `.env` includes `DEBUG` for Compose convenience; prefer `DJANGO_DEBUG`.


## API and Authentication
- Base API path: `api/v1/`
- Auth routes: included from `accounts/urls/_auth.py` via Djoser
  - JWT: `POST /api/v1/auth/jwt/create`, `POST /api/v1/auth/jwt/refresh`, `POST /api/v1/auth/jwt/verify`
  - Users: `POST /api/v1/auth/users/` (register), `GET /api/v1/auth/users/me/` (profile), etc.
- DRF defaults (`config/settings/restframework.py`):
  - `IsAuthenticated` globally; add `AllowAny` per-view as needed
  - Auth classes: JWT + Session
  - Filtering via `django-filter`
- OpenAPI docs (`drf-spectacular`):
  - Schema: `/api/schema/`
  - Swagger UI: `/api/schema/docs/`
  - Redoc: `/api/schema/redoc/`

Example auth flow (host mode):
```bash
# Register
curl -X POST http://127.0.0.1:8000/api/v1/auth/users/ \
  -H 'Content-Type: application/json' \
  -d '{"username":"demo","email":"demo@example.com","password":"Passw0rd!"}'

# Obtain JWT tokens
curl -X POST http://127.0.0.1:8000/api/v1/auth/jwt/create \
  -H 'Content-Type: application/json' \
  -d '{"username":"demo","password":"Passw0rd!"}'

# Authorized request
curl http://127.0.0.1:8000/api/v1/auth/users/me/ \
  -H "Authorization: Bearer <ACCESS_TOKEN>"
```


## Background jobs (Celery)
- App: `config/celery.py`
- Settings: `config/settings/celery.py` (beat schedule, queues, routes placeholders)

With Docker Compose, `celery_worker`, `celery_beat`, and `flower` run automatically.

Useful commands:
```bash
# Tail logs
docker compose logs -f celery_worker
docker compose logs -f celery_beat
docker compose logs -f flower

# (Advanced) run a one-off Celery command inside web
docker compose exec web uv run celery -A config.celery.app inspect active
```


## Project structure (opinionated)
This starter uses an opinionated, domain-driven layout that encourages separation of concerns and scalability.

```text
.
├─ config/
│  ├─ django/                 # env-specific entry settings (local, production)
│  ├─ settings/               # modular settings split by concerns
│  │  ├─ apps_middlewares.py  # INSTALLED_APPS, middleware, dev apps
│  │  ├─ auth.py              # password validators, AUTH_USER_MODEL
│  │  ├─ corsheaders.py       # CORS config
│  │  ├─ database.py          # DATABASES, CACHES (Redis)
│  │  ├─ lang_time.py         # i18n/l10n, timezone
│  │  ├─ paths.py             # static/media paths, sqlite location
│  │  ├─ restframework.py     # DRF + SimpleJWT + Djoser config import
│  │  ├─ spectacular.py       # drf-spectacular settings
│  │  ├─ unfold.py            # Unfold admin UI config
│  │  └─ __init__.py          # imports the modular settings
│  ├─ env.py                  # environment loader (django-environ)
│  ├─ celery.py               # Celery app setup
│  ├─ urls.py                 # root URLs (admin, api, docs)
│  ├─ asgi.py / wsgi.py
│  └─ logger.py               # Loguru-based structured logging
│
├─ accounts/                  # domain app (auth/user)
│  ├─ models/                 # domain models (custom User)
│  ├─ serializers/            # DRF serializers
│  ├─ controllers/            # HTTP controllers (views)
│  ├─ services/               # write logic, side-effects, orchestration
│  ├─ selectors/              # read/query logic
│  ├─ handlers/               # integration or workflow handlers
│  ├─ permissions/            # DRF permissions
│  ├─ filters/                # DRF/django-filter integration
│  ├─ urls/                   # app-level routes (Djoser mounted here)
│  └─ admin/                  # admin registrations (Unfold ModelAdmin)
│
├─ utils/
│  ├─ models/                 # reusable base models: TimeStamped, UUID, SoftDelete, Trackable, Slugged
│  └─ management/commands/    # developer tooling
│     ├─ starttemplateapp.py  # scaffold a new app from a template
│     ├─ manageprojectapp.py  # add/remove apps in settings lists
│     └─ addfile.py           # add actions/files to app sections
│
├─ static/exp_app/            # template app used by starttemplateapp
├─ database/                  # sqlite db path (if used)
├─ Dockerfile                 # uv-based image
├─ docker-compose.yml         # db, redis, web, worker, beat, flower
├─ pyproject.toml             # deps + dev deps + python version
├─ uv.lock                    # locked dependency versions
└─ manage.py                  # CLI entry
```

Why this layout?
- **Explicit boundaries**: reads (`selectors`) vs writes (`services`) vs transport (`controllers`)
- **Composable apps**: each app contains the same predictable sections
- **Testability**: thin views, test core logic in services/selectors
- **Scaffolding**: management commands accelerate adding apps/files consistently


## Scaffolding and maintenance commands
All commands run inside containers by default:

- Create a new app from the template and add it to settings:
  ```bash
  docker compose exec web uv run python manage.py starttemplateapp blog --add-to-settings
  ```

- Add an action/file to a section (e.g., a controller):
  ```bash
  docker compose exec web uv run python manage.py addfile blog --section controllers --action list
  ```

- Add/remove an app from settings lists:
  ```bash
  # add to project apps
  docker compose exec web uv run python manage.py manageprojectapp blog --type project

  # remove from third-party packages (soft-remove as a comment)
  docker compose exec web uv run python manage.py manageprojectapp somepackage --type third-party --remove --soft-remove
  ```


## Tech stack and main packages
- Core: `django`, `djangorestframework`, `django-filter`, `drf-extensions`
- Auth: `djangorestframework-simplejwt`, `djoser`
- Jobs: `celery`, `django-celery-beat`, `redis`
- DB/Config: `dj-database-url`, `psycopg2-binary`, `django-environ`
- Admin/UI: `django-unfold`, `django-cors-headers`
- Docs: `drf-spectacular`
- Logging/Debug: `loguru`, `icecream`
- Dev tools: `django-extensions`, `pytest`, `pytest-django`, `factory-boy`, `coverage`, `black`, `isort`, `mypy`, `ipython`, `werkzeug`, `django-silk`, `django-rosetta`, `pydantic`

Defined in `pyproject.toml` with Python `>=3.12`. Locked versions live in `uv.lock`.


## Running tests and quality tools
Container-first:
```bash
# install dev deps (already installed in image; re-run if needed)
 docker compose exec web uv sync --group dev

# run tests
 docker compose exec web uv run pytest -q

# coverage
 docker compose exec web uv run coverage run -m pytest && \
 docker compose exec web uv run coverage html

# format & lint
 docker compose exec web uv run black .
 docker compose exec web uv run isort .

# type check
 docker compose exec web uv run mypy .
```
Host mode: use the same commands without `docker compose exec web`.


## CORS and security
- CORS defaults allow `http://localhost:8080` and `http://127.0.0.1:8000`. Update `config/settings/corsheaders.py` for your frontend origins.
- Always set `ALLOWED_HOSTS` and secure secrets in production.


## Production notes
- Switch settings: `DJANGO_SETTINGS_MODULE=config.django.production`
- Use a real DB and Redis service; run `collectstatic` when serving static assets:
  ```bash
  docker compose exec web uv run python manage.py collectstatic --noinput
  ```
- Configure a proper ASGI/WSGI server (e.g., `gunicorn`, `uvicorn`) behind a reverse proxy.


## Troubleshooting
- Commands failing on host: run them inside containers (`docker compose exec web ...`), or switch to Host mode with correct `DATABASE_URL`/`REDIS_URL`.
- Database connection errors: verify `DATABASE_URL`. For SQLite, prefer `sqlite:///database/db.sqlite3` and ensure the directory exists (Host mode).
- 401 Unauthorized: obtain/refresh JWT via Djoser endpoints and send `Authorization: Bearer <token>`.
- Celery not picking tasks: ensure worker and beat are running and `REDIS_URL` is reachable. Check Flower at `:5555`.
