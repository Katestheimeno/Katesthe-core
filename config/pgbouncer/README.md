# PgBouncer configuration

Connection pooler for PostgreSQL. App and Celery connect to PgBouncer; PgBouncer connects to the `db` service.

**Run compose with your env file** so variable substitution uses it:

```bash
docker compose --env-file .env.local up -d
```

## .env.local changes

Point the app at PgBouncer instead of Postgres by updating these in `.env.local`:

```diff
 # Database Configuration (PostgreSQL)
 POSTGRES_USER=postgres
 POSTGRES_PASSWORD=postgres
-POSTGRES_HOST=db
-POSTGRES_PORT=5432
+POSTGRES_HOST=pgbouncer
+POSTGRES_PORT=6432
 POSTGRES_DB=drf_starter
```

And set `DATABASE_URL` to use PgBouncer (used by Celery and any code that reads `DATABASE_URL` from env):

```diff
-DATABASE_URL=postgresql://postgres:postgres@db:5432/drf_starter
+DATABASE_URL=postgresql://postgres:postgres@pgbouncer:6432/drf_starter
```

Optional: expose PgBouncer port on the host (default 6432):

```env
PGBOUNCER_PORT=6432
```

## Summary: replace these lines in .env.local

| Variable        | Before              | After                    |
|----------------|---------------------|--------------------------|
| `POSTGRES_HOST` | `db`                | `pgbouncer`              |
| `POSTGRES_PORT` | `5432`              | `6432`                   |
| `DATABASE_URL`  | `...@db:5432/...`   | `...@pgbouncer:6432/...` |

## Flow

```
web / celery_worker / celery_beat  →  pgbouncer:6432  →  db:5432 (PostgreSQL)
```

## Config files

- `pgbouncer.ini` – listen port 6432, `pool_mode=transaction`, backend `db:5432`.
- `userlist.txt` – credentials must match `POSTGRES_USER` / `POSTGRES_PASSWORD` from `.env.local`.

If you change the DB user or password, update `config/pgbouncer/userlist.txt` to match.
