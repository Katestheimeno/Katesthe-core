# PgBouncer configuration

Connection pooler for PostgreSQL. The **web** and **Celery** services connect to PgBouncer; PgBouncer connects to the **db** service. This reduces connection churn and supports many concurrent clients.

**Django** does not use `DATABASE_URL`: it uses explicit `DB_PRIMARY_*` variables (see `config/settings/database.py`). The **edoburu/pgbouncer** container still uses a `DATABASE_URL` **internally** in `docker-compose.yml` to point at the Postgres `db` service — that URL is for the pooler only, not for Django.

**Run compose with your env file** so variable substitution uses it:

```bash
docker compose --env-file .env.local up -d
```

## Default Docker setup

The project’s **`env.docker.example`** is set up for PgBouncer. Copy it to `.env.local` and use it with Docker:

- **Inside the Docker network:** PgBouncer listens on port **5432**. The app and Celery use:
  - `DB_PRIMARY_HOST=pgbouncer`
  - `DB_PRIMARY_PORT=5432`
  - `DB_PRIMARY_NAME`, `DB_PRIMARY_USER`, `DB_PRIMARY_PASSWORD` matching the Postgres container
- **On the host:** The PgBouncer port is mapped to **6432** (`PGBOUNCER_PORT`). Use `localhost:6432` only if you run tools (e.g. a GUI client) on your machine and want to go through the pooler.

So: **in-container** → `pgbouncer:5432`; **from host** → `localhost:6432` (optional).

## If you start from a non-PgBouncer .env

Point the app at PgBouncer by updating `.env.local`:

| Variable           | Without PgBouncer | With PgBouncer (in Docker) |
| ------------------ | ----------------- | -------------------------- |
| `DB_PRIMARY_HOST`  | `db`              | `pgbouncer`                |
| `DB_PRIMARY_PORT`  | `5432`            | `5432` (inside network)    |

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
- The PgBouncer **image** is configured via environment variables (`DATABASE_URL` for its backend, `PGBOUNCER_POOL_MODE`, etc.). The **`config/pgbouncer/`** directory holds reference files:
  - **`pgbouncer.ini`** – pool mode, listen port, backend.
  - **`userlist.txt`** – credentials; must match `DB_PRIMARY_USER` / `DB_PRIMARY_PASSWORD` (and Postgres) if you use a custom userlist.

If you change the DB user or password, update `config/pgbouncer/userlist.txt` when using a custom userlist.
