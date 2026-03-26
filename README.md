## Katesthe-core

A production-ready Django REST Framework starter with an opinionated, domain-driven file architecture, JWT authentication (Djoser + SimpleJWT), Celery background jobs, Redis cache/broker, OpenAPI docs (drf-spectacular), CORS, and a modern Unfold-powered admin.

### Features at a glance
- **Authentication**: Djoser + SimpleJWT (access/refresh), custom `accounts.User`
- **API**: DRF with sensible defaults, filtering (`django-filter`), extensions
- **Docs**: OpenAPI schema + Swagger/Redoc UIs
- **Background jobs**: Celery worker + beat
- **Realtime**: Django Channels + Redis (WebSockets)
- **Storage**: Postgres via explicit `DB_PRIMARY_*` (optional read replicas); SQLite when `USE_SQLITE=true` or when `DB_PRIMARY_HOST` is unset
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

## 🚀 Quick Start

1. **Install the template** from the canonical GitHub repo ([`Katestheimeno/Katesthe-core`](https://github.com/Katestheimeno/Katesthe-core)).

   **What it does:** `setup.sh` clones this repository into your **current directory** (start from an **empty folder**), removes `.git`, applies your project name and metadata, updates `pyproject.toml`, and runs `uv lock` when `uv` is available.

   **Requirements on your machine:** **bash**, **git**, **perl**, and **Python 3**. Run the script with **`bash`**, not **`sh`** (on many Linux systems `sh` is `dash`). The script targets **bash 3.2+** (including macOS `/bin/bash`).

   **Interactive install (default)** — create an **empty** directory, then either:

   **Option A (recommended):** download the script, then run it so prompts use your terminal (avoids stdin issues when piping):

   ```bash
   mkdir my-project && cd my-project
   curl -LsSf https://raw.githubusercontent.com/Katestheimeno/Katesthe-core/main/setup.sh -o setup.sh
   bash setup.sh
   ```

   **Option B:** pipe straight to bash — `setup.sh` reads prompts from `/dev/tty`, so this is safe for interactive use:

   ```bash
   mkdir my-project && cd my-project
   curl -LsSf https://raw.githubusercontent.com/Katestheimeno/Katesthe-core/main/setup.sh | bash
   ```

   You will be prompted for display name, pyproject package name, contact fields, and description.

   **Non-interactive** (CI or scripting): set `SETUP_NONINTERACTIVE=1` and at least `SETUP_PROJECT_NAME`. Optional: `SETUP_REPO_URL`, `SETUP_PYPROJECT_NAME`, `SETUP_PYPROJECT_DESCRIPTION`, `SETUP_CONTACT_*`, `SETUP_PROFILING_EMAIL`, or pass flags after `--`:

   ```bash
   curl -LsSf https://raw.githubusercontent.com/Katestheimeno/Katesthe-core/main/setup.sh | bash -s -- --non-interactive \
     --project-name "My API" \
     --pyproject-name "my-api" \
     --repo-url "https://github.com/myorg/my-api.git"
   ```

   Equivalent with environment variables:

   ```bash
   SETUP_NONINTERACTIVE=1 \
   SETUP_PROJECT_NAME="My API" \
   SETUP_PYPROJECT_NAME="my-api" \
   SETUP_REPO_URL="https://github.com/myorg/my-api.git" \
   curl -LsSf https://raw.githubusercontent.com/Katestheimeno/Katesthe-core/main/setup.sh | bash
   ```

   Full options: `curl ... | bash -s -- --help`, or `./setup.sh --help` after downloading or cloning the repo.

2) **Create environment configuration**
```bash
# For local development
cp .env.local.example .env.local

# For production (optional)
cp .env.prod.example .env.prod

# For testing (optional)
cp .env.test.example .env.test
```

3) **Set secrets for your environment**
```bash
# Generate strong values for production
openssl rand -base64 48 | tr -d '\n'
```

4) **Start the stack**
```bash
# Local development (uses .env.local by default)
docker compose up --build

# Or specify environment explicitly
ENV_FILE=.env.local docker compose up --build
```

**Docker stack (services):** `db` (PostgreSQL 15), `redis`, **pgbouncer** (connection pooler), `web` (Django + Daphne), `celery_worker`, `celery_beat`. The web and Celery services connect to Postgres **via PgBouncer**; PgBouncer connects to `db`. Use `env.docker.example` as the basis for `.env.local` (it points the app at `pgbouncer:5432` inside the network). For PgBouncer config and optional host access, see **`config/pgbouncer/README.md`**.

## Environment Configuration

The project uses environment-specific configuration files for better separation of concerns:

### Environment Files

- **`.env.local`** - Local development environment
- **`.env.prod`** - Production environment  
- **`.env.test`** - Testing environment

### Auto-Detection Logic

The system automatically detects which environment file to use based on:

1. **`DJANGO_ENV`** environment variable (`local`, `prod`, `test`)
2. **`DJANGO_SETTINGS_MODULE`** environment variable (contains `local`, `production`, or `test`)
3. **Default** to `.env.local` if neither is set

### Docker Compose Integration

Docker Compose uses the `ENV_FILE` environment variable to specify which `.env` file to load:

```bash
# Use local environment (default)
docker compose up

# Use production environment
ENV_FILE=.env.prod docker compose up

# Use test environment
ENV_FILE=.env.test docker compose up
```

### Manual Setup

Copy the appropriate example file and customize:

```bash
# For local development
cp .env.local.example .env.local

# For production
cp .env.prod.example .env.prod

# For testing
cp .env.test.example .env.test
```

4) **Web container startup** (`entrypoint.sh`)

   When the `web` service starts, it runs in order:
   - `uv sync --frozen` — install/sync dependencies
   - `migrate` — apply database migrations
   - `collectstatic --noinput` — gather static files into `STATIC_ROOT` for serving
   - **Daphne** ASGI server on `${WEB_PORT:-8000}` with `--application-close-timeout 30` (reduces "took too long to shut down" warnings when the browser cancels static requests, e.g. on refresh or redirect)

   You do not need to run `collectstatic` manually for normal Docker runs.

5) Run management commands inside the web container
```bash
# migrations (also run automatically at startup)
docker compose exec web uv run python manage.py migrate

# superuser
docker compose exec web uv run python manage.py createsuperuser

# makemigrations
docker compose exec web uv run python manage.py makemigrations

# shell
docker compose exec web uv run python manage.py shell
```

6) Access services
- Web: `http://127.0.0.1:${WEB_PORT:-8000}`
- Admin: `http://127.0.0.1:${WEB_PORT:-8000}/admin/`
- Swagger: `http://127.0.0.1:${WEB_PORT:-8000}/api/schema/docs/`
- Redoc: `http://127.0.0.1:${WEB_PORT:-8000}/api/schema/redoc/`


## Alternative: Host mode (advanced)
If you prefer running Django on your host (outside Docker), you must point your environment file to services reachable from your host, not the Docker DNS names.

Two options:
- Use the Dockerized Postgres/Redis but connect via localhost (ports are published by compose). To talk to Postgres directly (no PgBouncer): use port 5432; to use the pooler from the host: use port 6432 (see `config/pgbouncer/README.md`).
  ```env
  # .env.local overrides for HOST MODE (direct Postgres)
  USE_SQLITE=false
  DB_PRIMARY_HOST=localhost
  DB_PRIMARY_PORT=5432
  DB_PRIMARY_NAME=drf_starter
  DB_PRIMARY_USER=postgres
  DB_PRIMARY_PASSWORD=postgres
  REDIS_URL=redis://localhost:6379/0
  ```
  Then:
  ```bash
  # Ensure db and redis are up (pgbouncer optional if you use localhost:6432 from host)
  docker compose up -d db redis

  # Host virtualenv using uv
  uv venv .venv && source .venv/bin/activate  # Windows: .venv\Scripts\activate
  uv sync && uv sync --group dev

  uv run python manage.py migrate
  uv run python manage.py runserver 0.0.0.0:${WEB_PORT:-8000}
  ```

- Or install Postgres/Redis locally and set `DB_PRIMARY_*`/`REDIS_URL` accordingly.

Important:
- Do not use `db`, `pgbouncer`, or `redis` hostnames from your host; those names only resolve inside Docker networks. Use `localhost` with the published ports (Postgres: 5432, PgBouncer: 6432, Redis: 6379).


## Configuration (Environment)
The project centralizes env handling in `config/env.py`. Key variables:

### **Core Settings**
- `SECRET_KEY`: Django secret key
- `JWT_SECRET_KEY`: JWT signing key (used by SimpleJWT)
- `DJANGO_DEBUG`: `True|False` (Django's `DEBUG`)
- `DJANGO_ENV`: `local|production` (informational)
- `ALLOWED_HOSTS`: CSV list; required in production
- `WEB_PORT`: Django development server port (default: 8000)

### **Project Branding**
- `PROJECT_NAME`: Project name used in API docs, admin interface, etc. (default: "Katesthe-core")
- `PROJECT_DESCRIPTION`: Project description for API documentation (default: "A Django REST Framework starter project...")
- `PROJECT_VERSION`: API version (default: "1.0.0")

### **Contact Information**
- `CONTACT_NAME`: Contact name for API documentation (default: "Katesthe-core Dev Team")
- `CONTACT_EMAIL`: Contact email for API documentation (default: "support@katesthe-core.com")
- `CONTACT_URL`: Contact URL/GitHub repository (default: "https://github.com/katesthe-core")

### **Email Configuration**
- `EMAIL_HOST`: SMTP host (default: "localhost")
- `EMAIL_PORT`: SMTP port (default: 1025)
- `EMAIL_USE_TLS`: Use TLS for email (default: False)
- `EMAIL_HOST_USER`: SMTP username (default: "")
- `EMAIL_HOST_PASSWORD`: SMTP password (default: "")
- `EMAIL_FRONTEND_DOMAIN`: Frontend domain for email links (default: "")

### **Theme Colors**
- `THEME_PRIMARY_COLOR`: Primary theme color in hex format (default: "#6a0dad")
- `THEME_ACCENT_COLOR`: Accent theme color in hex format (default: "#4b0082")

### **Database**
- `USE_SQLITE`: when `true`, Django uses SQLite (file under `database/`); takes precedence over Postgres.
- `DB_PRIMARY_HOST`, `DB_PRIMARY_PORT`, `DB_PRIMARY_NAME`, `DB_PRIMARY_USER`, `DB_PRIMARY_PASSWORD`: primary Postgres connection (no `DATABASE_URL`).
- `DB_REPLICA_HOSTS`: comma-separated replica hostnames; optional `DB_REPLICA_PORT`, `DB_REPLICA_USER`, `DB_REPLICA_PASSWORD`, `DB_REPLICA_NAME` (default to primary when empty).
- `DB_ROUTING_ENABLED`: defaults to **`true`** — registers `PrimaryReplicaRouter`. **Reads** go to replicas only when `DB_REPLICA_HOSTS` lists hosts; if empty, reads stay on the primary. Set to `false` to disable the router entirely. See `docs/db-primary-replica.md` and `config/db_router.py`.
- `REPLICATOR_PASSWORD`: used only by Docker Compose for Postgres streaming replication (`db` + `db_replica`); must match between primary init and replica `pg_basebackup` (default in examples: `replicator_dev`).
- In Docker, use `DB_PRIMARY_HOST=db` and `DB_PRIMARY_PORT=5432` for direct Postgres; optional PgBouncer is `pgbouncer` — see `env.docker.example` and `config/pgbouncer/README.md`. For **read traffic splitting**, set `DB_REPLICA_HOSTS=db_replica` to use the bundled streaming standby (`docker-compose.yml`). If you add replication **after** an existing primary volume was created, run `docker compose down -v` once so the primary runs init scripts that create the `replicator` role (or add that user manually).

**Check routing in a running container**:

```bash
docker compose exec web uv run python manage.py shell -c "from django.conf import settings; print('DATABASES:', list(settings.DATABASES.keys())); print('DATABASE_ROUTERS:', settings.DATABASE_ROUTERS); print('DB_ROUTING_ENABLED:', settings.DB_ROUTING_ENABLED); print('REPLICA_DATABASE_ALIASES:', settings.REPLICA_DATABASE_ALIASES)"
```

With `DB_REPLICA_HOSTS=db_replica` (default in `env.docker.example`): expect `DATABASES` to include `default` and `replica_0`, `REPLICA_DATABASE_ALIASES: ['replica_0']`, and reads to use the replica when healthy. With no replicas: `REPLICA_DATABASE_ALIASES: []` — reads stay on the primary. Set `DB_ROUTING_ENABLED=false` to unregister the router.

### **Cache/Broker**
- `REDIS_URL`: e.g. `redis://localhost:6379/0`

**Notes:**
- `manage.py` defaults to `config.django.local` settings; Production can use `DJANGO_SETTINGS_MODULE=config.django.production`.
- Database configuration uses explicit `DB_PRIMARY_*` in `config/settings/database.py`.
- Use `DJANGO_DEBUG` (boolean) for Django's debug toggle. The example environment files include `DEBUG` for Compose convenience; prefer `DJANGO_DEBUG`.
- All branding and theme variables can be customized via environment variables for easy project personalization.


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
curl -X POST http://127.0.0.1:${WEB_PORT:-8000}/api/v1/auth/users/ \
  -H 'Content-Type: application/json' \
  -d '{"username":"demo","email":"demo@example.com","password":"Passw0rd!"}'

# Obtain JWT tokens
curl -X POST http://127.0.0.1:${WEB_PORT:-8000}/api/v1/auth/jwt/create \
  -H 'Content-Type: application/json' \
  -d '{"username":"demo","password":"Passw0rd!"}'

# Authorized request
curl http://127.0.0.1:${WEB_PORT:-8000}/api/v1/auth/users/me/ \
  -H "Authorization: Bearer <ACCESS_TOKEN>"
```


## Background jobs (Celery)
- App: `config/celery.py`
- Settings: `config/settings/celery.py` (beat schedule, queues, routes placeholders)

With Docker Compose, `celery_worker` and `celery_beat` run automatically.

Useful commands:
```bash
# Tail logs
docker compose logs -f celery_worker
docker compose logs -f celery_beat

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
│  ├─ pgbouncer/              # PgBouncer config (ini, userlist); see README there
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
├─ entrypoint.sh              # web startup: uv sync, migrate, collectstatic, daphne
├─ docker-compose.yml        # db, redis, pgbouncer, web, celery_worker, celery_beat
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
  docker compose exec web uv run python manage.py managefile blog --layer controllers --suffix list
  ```

- Add/remove an app from settings lists:
  ```bash
  # add to project apps
  docker compose exec web uv run python manage.py manageprojectapp blog --type project

  # remove from third-party packages (soft-remove as a comment)
  docker compose exec web uv run python manage.py manageprojectapp somepackage --type third-party --remove --soft-remove
  ```

## Management Commands Reference

This project includes several custom management commands to streamline development and maintenance tasks. All commands can be run either locally (with proper environment setup) or inside Docker containers.

### 🚀 `dockerexec` - Execute Django Commands in Docker

**Purpose**: Run Django management commands inside Docker containers from your local machine, ensuring consistent database connections and environment variables.

**Use Cases**:
- Running migrations when your local environment isn't configured for the Docker database
- Executing any Django command that requires database access
- Maintaining consistency between local development and containerized environments
- Interactive commands like shell, createsuperuser, and runserver

**Features**:
- **Smart Interactive Mode**: Automatically detects when commands need interactive mode (TTY allocation)
- **Real-time Output Streaming**: Non-interactive commands stream output as it happens
- **Dry Run Support**: Preview commands before execution
- **Flexible Service Selection**: Choose which Docker service to use
- **Auto Docker Compose Discovery**: Automatically finds docker-compose.yml files in multiple locations
- **Custom Docker Compose Files**: Specify different compose files with intelligent path resolution
- **Keyboard Interrupt Handling**: Graceful handling of Ctrl+C

**Examples**:
```bash
# Run database migrations
uv run python manage.py dockerexec migrate

# Make migrations for specific app
uv run python manage.py dockerexec makemigrations accounts

# Create a superuser (automatically interactive)
uv run python manage.py dockerexec createsuperuser

# Run Django shell (automatically interactive)
uv run python manage.py dockerexec shell

# Run tests
uv run python manage.py dockerexec test

# Dry run to see what would be executed
uv run python manage.py dockerexec migrate --dry-run

# Use different Docker service
uv run python manage.py dockerexec migrate --service=web-dev

# Force interactive mode for any command
uv run python manage.py dockerexec collectstatic --interactive

# Force non-interactive mode
uv run python manage.py dockerexec createsuperuser --no-interactive

# Use different Docker compose file (auto-detected)
uv run python manage.py dockerexec migrate --compose-file=docker-compose.prod.yml

# Use absolute path to compose file
uv run python manage.py dockerexec migrate --compose-file=/path/to/docker-compose.yml

# Run shell with specific settings
uv run python manage.py dockerexec shell --settings=config.django.test
```

**Interactive Commands** (automatically get TTY allocation):
- `createsuperuser` - User creation prompts
- `shell` - Interactive Python shell
- `dbshell` - Database shell access
- `runserver` - Development server

**Non-Interactive Commands** (stream output):
- `migrate`, `makemigrations` - Database operations
- `test` - Test execution
- `collectstatic` - Static file collection
- `check` - Django system checks

**Docker Compose Auto-Discovery**: The command automatically searches for docker-compose files in multiple locations:

1. **Absolute paths** - Used as-is if the file exists
2. **Current directory** - Relative to where you run the command
3. **Service directory** - Where manage.py is located
4. **Project root** - One level up from service directory
5. **Fallback** - Looks for `docker-compose.yml` in project root

This means you can run the command from anywhere in your project structure and it will find the correct compose file automatically. If no compose file is found, the command will provide a clear error message showing all the locations it searched.

**Configuration**: Customize behavior by defining these settings in your Django settings:
```python
# Commands that should use Docker
DOCKEREXEC_COMMANDS = [
    'migrate', 'makemigrations', 'createsuperuser', 'shell',
    'dbshell', 'collectstatic', 'runserver', 'test', 'flush',
    'loaddata', 'dumpdata', 'showmigrations', 'sqlmigrate',
    'check', 'compilemessages', 'makemessages'
]

# Commands that always need interactive mode
DOCKEREXEC_INTERACTIVE_COMMANDS = [
    'createsuperuser', 'shell', 'dbshell', 'runserver'
]
```

---

### 📁 `managefile` - File Management with Nested Scope Support

**Purpose**: Add suffix files to app layers with automatic import management and nested scope support. This command helps maintain the domain-driven architecture by creating properly structured files with correct imports.

**Use Cases**:
- Creating new controllers, serializers, models, or other layer files
- Organizing code into nested scopes (e.g., `controllers/user/`, `serializers/auth/`)
- Managing imports automatically across the nested structure
- Enabling/disabling files by commenting/uncommenting imports
- Cleaning up empty directories and unused imports

**Examples**:
```bash
# Create a user controller
uv run python manage.py managefile accounts --layer controllers --suffix user

# Create a nested auth serializer
uv run python manage.py managefile accounts --layer serializers --suffix auth --scope user

# Create a review controller inside shop feature
uv run python manage.py managefile shops --layer controllers --suffix review --scope shop

# Disable an existing handler (comment out import)
uv run python manage.py managefile bookings --layer handlers --suffix cancel --disable

# Re-enable a disabled handler
uv run python manage.py managefile bookings --layer handlers --suffix cancel --enable

# Clean up empty directories in a layer
uv run python manage.py managefile accounts --layer controllers --cleanup

# Delete a specific file and clean up imports
uv run python manage.py managefile accounts --layer controllers --cleanup user

# Preview actions without making changes
uv run python manage.py managefile accounts --layer controllers --suffix user --dry-run
```

**Features**:
- **Automatic imports**: Adds default imports based on layer type (controllers get DRF imports, models get Django imports, etc.)
- **Nested scopes**: Supports creating files in subdirectories with proper import chains
- **Import management**: Automatically updates `__init__.py` files throughout the nested structure
- **Enable/disable**: Comment/uncomment imports to temporarily disable files
- **Cleanup**: Remove empty directories and unused imports

---

### 🏗️ `starttemplateapp` - Create Apps from Template

**Purpose**: Scaffold a new Django app from the template in `static/exp_app` with placeholder replacement and automatic settings integration.

**Use Cases**:
- Creating new domain apps following the project's architecture
- Ensuring consistent app structure across the project
- Automatically adding new apps to Django settings
- Customizing app templates for different use cases

**Examples**:
```bash
# Create a new blog app
uv run python manage.py starttemplateapp blog

# Create app and automatically add to PROJECT_APPS
uv run python manage.py starttemplateapp blog --add-to-settings

# Create app in a specific directory
uv run python manage.py starttemplateapp blog --dir apps

# Use a custom template
uv run python manage.py starttemplateapp blog --template custom_template

# Force overwrite if directory exists
uv run python manage.py starttemplateapp blog --force

# Preview actions without creating files
uv run python manage.py starttemplateapp blog --dry-run
```

**Features**:
- **Template-based**: Uses `static/exp_app` as the template
- **Placeholder replacement**: Replaces `{{app_name}}` placeholders throughout the template
- **Settings integration**: Can automatically add the new app to `PROJECT_APPS`
- **Directory flexibility**: Create apps in custom directories
- **Safety features**: Dry-run mode and force overwrite options

---

### ⚙️ `manageprojectapp` - Manage Apps in Settings

**Purpose**: Add or remove apps from Django settings lists (`PROJECT_APPS`, `DEV_APPS`, `THIRD_PARTY_PACKAGES`) with intelligent handling of different app types.

**Use Cases**:
- Adding new project apps to settings
- Managing third-party package dependencies
- Soft-removing apps (commenting out instead of deleting)
- Organizing apps by type in settings files
- Maintaining clean settings files

**Examples**:
```bash
# Add a project app to PROJECT_APPS
uv run python manage.py manageprojectapp blog --type project

# Add a third-party package to THIRD_PARTY_PACKAGES
uv run python manage.py manageprojectapp rest_framework --type third-party

# Add a development tool to DEV_APPS
uv run python manage.py manageprojectapp django_extensions --type dev

# Soft-remove a project app (comment out instead of deleting)
uv run python manage.py manageprojectapp blog --remove --soft-remove

# Hard-remove a third-party package (delete the line)
uv run python manage.py manageprojectapp somepackage --type third-party --remove

# Force add an app without checking if its folder exists
uv run python manage.py manageprojectapp some_missing_app --force

# Preview changes without modifying files
uv run python manage.py manageprojectapp blog --type project --dry-run
```

**Features**:
- **App type handling**: Different logic for project apps vs third-party packages
- **Soft removal**: Comment out apps instead of deleting them
- **Validation**: Checks if app directories exist (unless forced)
- **Settings organization**: Maintains clean, organized settings files
- **Safety**: Dry-run mode for previewing changes

---

### 🧹 `cleanuppycache` - Remove Python Cache Files

**Purpose**: Remove all `__pycache__` directories from all Django apps in the project to clean up compiled Python bytecode files.

**Use Cases**:
- Cleaning up before deployment
- Resolving import issues caused by stale bytecode
- Reducing project size
- Ensuring fresh Python imports
- Maintenance tasks

**Examples**:
```bash
# Remove all __pycache__ directories
uv run python manage.py cleanuppycache

# Preview what would be removed without deleting
uv run python manage.py cleanuppycache --dry-run

# Verbose output showing each directory as it's removed
uv run python manage.py cleanuppycache --verbose

# Combine dry-run with verbose for detailed preview
uv run python manage.py cleanuppycache --dry-run --verbose
```

**Features**:
- **Comprehensive cleanup**: Finds and removes all `__pycache__` directories
- **Safety**: Dry-run mode to preview actions
- **Verbose output**: Shows each directory being processed
- **Project-wide**: Covers all Django apps in the project


## Tech stack and main packages
- Core: `django`, `djangorestframework`, `django-filter`, `drf-extensions`
- Auth: `djangorestframework-simplejwt`, `djoser`
- Jobs: `celery`, `django-celery-beat`, `redis`
- DB/Config: `psycopg2-binary`, `pydantic-settings`
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

## Testing

This project uses a comprehensive testing setup with **pytest**, **django-pytest**, **factory-boy**, and **coverage** for robust test coverage.

### Test Structure

Tests follow the same structure as the application code, mirroring the domain-driven architecture:

```
accounts/tests/
├── factories/                 # Factory-boy factories for test data
│   ├── __init__.py
│   └── _user.py              # User model factories
├── models/
│   └── test_user.py          # User model tests
├── admin/
│   └── test_user_admin.py    # Admin interface tests
├── serializers/
│   └── test_auth.py          # Serializer tests
├── controllers/
│   └── test_auth.py          # View/controller tests
├── test_emails.py            # Email functionality tests
├── conftest.py               # Pytest fixtures
└── README.md                 # Detailed test documentation
```

### Running Tests

#### Accounts App Tests
```bash
# Run all accounts app tests with coverage
uv run pytest accounts/tests/ --cov=accounts --cov-report=term-missing

# Run specific test files
uv run pytest accounts/tests/controllers/test_auth.py
uv run pytest accounts/tests/serializers/test_auth.py

# Run specific test classes
uv run pytest accounts/tests/controllers/test_auth.py::TestCustomUserViewSet

# Run specific test methods
uv run pytest accounts/tests/controllers/test_auth.py::TestCustomUserViewSet::test_user_profile_access
```

#### Full Project Tests
```bash
# Run all project tests with coverage
uv run pytest --ds=config.django.test --cov=. --cov-report=term-missing

# Run tests with HTML coverage report
uv run pytest --ds=config.django.test --cov=. --cov-report=html
```

#### Docker Environment

```bash
# Run tests inside Docker container
docker compose exec web uv run pytest

# Run tests with coverage in Docker
docker compose exec web uv run pytest --cov=accounts --cov-report=term-missing
```

### Test Configuration

- **Settings**: Tests use `config.django.test` settings with in-memory SQLite database
- **Database**: SQLite in-memory for fast test execution
- **Coverage**: Configured in `.coveragerc` to exclude test files and migrations
- **Factories**: Located in `accounts/tests/factories/` for generating test data

### Test Data with Factory-Boy

The project uses Factory-Boy to create test data efficiently:

```python
from accounts.tests.factories import UserFactory, SuperUserFactory

# Create a basic user
user = UserFactory()

# Create a superuser
admin = SuperUserFactory()

# Create user with specific attributes
user = UserFactory(username="testuser", email="test@example.com")
```

Available factories:
- `UserFactory`: Basic user with default values
- `InactiveUserFactory`: User with `is_active=False`
- `UnverifiedUserFactory`: User with `is_verified=False`
- `StaffUserFactory`: Staff user
- `SuperUserFactory`: Superuser

### Test Coverage

The test suite provides comprehensive coverage for:

- **Models**: User model, custom manager, field validation
- **Admin**: UserAdmin configuration, list views, search functionality
- **Serializers**: Authentication, user creation, profile updates
- **Controllers**: JWT authentication, user management endpoints
- **Emails**: Custom email templates and integration

### Writing New Tests

When adding new functionality, follow these patterns:

1. **Create factories** in `accounts/tests/factories/` for your models
2. **Add model tests** in `accounts/tests/models/`
3. **Add admin tests** in `accounts/tests/admin/`
4. **Add serializer tests** in `accounts/tests/serializers/`
5. **Add controller tests** in `accounts/tests/controllers/`
6. **Use `@pytest.mark.django_db`** for tests requiring database access

Example test structure:
```python
import pytest
from accounts.tests.factories import UserFactory

@pytest.mark.django_db
class TestMyFeature:
    def test_something(self):
        user = UserFactory()
        # Test logic here
        assert True
```

### Test Best Practices

- Use `@pytest.mark.django_db` for database tests
- Leverage factories for consistent test data
- Test both success and failure scenarios
- Use descriptive test names and docstrings
- Group related tests in classes
- Mock external dependencies when appropriate


## CORS and security
- CORS defaults allow `http://localhost:8080` and `http://127.0.0.1:${WEB_PORT:-8000}`. Update `config/settings/corsheaders.py` for your frontend origins.
- Always set `ALLOWED_HOSTS` and secure secrets in production.


## Production notes
- Switch settings: `DJANGO_SETTINGS_MODULE=config.django.production`
- Use a real DB and Redis service. Static files are collected automatically when the web container starts (see `entrypoint.sh`). If you deploy without that entrypoint (e.g. custom image or CI), run:
  ```bash
  docker compose exec web uv run python manage.py collectstatic --noinput
  ```
- The web service runs **Daphne** (ASGI) with `--application-close-timeout 30`. For production, put Daphne (or gunicorn/uvicorn) behind a reverse proxy (e.g. Nginx, Caddy).


## Troubleshooting
- Commands failing on host: run them inside containers (`docker compose exec web ...`), or switch to Host mode with correct `DB_PRIMARY_*`/`REDIS_URL`.
- Database connection errors: verify `DB_PRIMARY_HOST`, credentials, and port. For SQLite (`USE_SQLITE=true`), ensure the `database/` directory exists.
- 401 Unauthorized: obtain/refresh JWT via Djoser endpoints and send `Authorization: Bearer <token>`.
- Celery not picking tasks: ensure worker and beat are running and `REDIS_URL` is reachable.
