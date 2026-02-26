# PgBouncer configuration

Connection pooler for PostgreSQL. The **web** and **Celery** services connect to PgBouncer; PgBouncer connects to the **db** service. This reduces connection churn and supports many concurrent clients.

**Run compose with your env file** so variable substitution uses it:

```bash
docker compose --env-file .env.local up -d
```

## Default Docker setup

The project’s **`env.docker.example`** is already set up for PgBouncer. Copy it to `.env.local` and use it with Docker:

- **Inside the Docker network:** PgBouncer listens on port **5432**. The app and Celery use:
  - `POSTGRES_HOST=pgbouncer`
  - `POSTGRES_PORT=5432`
  - `DATABASE_URL=postgresql://postgres:postgres@pgbouncer:5432/drf_starter`
- **On the host:** The PgBouncer port is mapped to **6432** (`PGBOUNCER_PORT`). Use `localhost:6432` only if you run tools (e.g. a GUI client) on your machine and want to go through the pooler.

So: **in-container** → `pgbouncer:5432`; **from host** → `localhost:6432` (optional).

## If you start from a non-PgBouncer .env

Point the app at PgBouncer by updating `.env.local`:

| Variable         | Without PgBouncer   | With PgBouncer (in Docker)   |
|------------------|---------------------|-----------------------------|
| `POSTGRES_HOST`  | `db`                | `pgbouncer`                 |
| `POSTGRES_PORT`  | `5432`              | `5432` (inside network)     |
| `DATABASE_URL`   | `...@db:5432/...`   | `...@pgbouncer:5432/...`     |

Optional: expose PgBouncer on the host (default 6432):

```env
PGBOUNCER_PORT=6432
```

## Flow

```
web / celery_worker / celery_beat  →  pgbouncer:5432  →  db:5432 (PostgreSQL)
                                       (inside network)
```

## Compose and image

- **`docker-compose.yml`** runs the **edoburu/pgbouncer** image. The **db** service uses `password_encryption=md5` so PgBouncer’s MD5 userlist can authenticate. After changing the DB password, recreate the DB volume so it is stored as MD5: `docker compose down -v && docker compose up -d`.
- PgBouncer is configured via environment variables (`DATABASE_URL`, `PGBOUNCER_POOL_MODE`, etc.). The **`config/pgbouncer/`** directory holds reference files:
  - **`pgbouncer.ini`** – pool mode, listen port, backend.
  - **`userlist.txt`** – credentials; must match `POSTGRES_USER` / `POSTGRES_PASSWORD` in `.env.local` if you use a custom userlist.

If you change the DB user or password, update `config/pgbouncer/userlist.txt` when using a custom userlist.
