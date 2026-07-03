# Daphne → Uvicorn Migration Plan

**Scope:** Replace `daphne` with `uvicorn` + `gunicorn` as the ASGI server in Katesthe-core.
**Source:** Rhitoric-core's production setup (battle-tested since 2026-02).
**Effort:** ~1 hour. 5 files changed, no code changes to views/consumers/middleware.
**Risk:** Low — `config/asgi.py` is unchanged, Channels works identically under uvicorn.

---

## Why

| | Daphne | Uvicorn |
|---|---|---|
| **Architecture** | Twisted event loop | uvloop (libuv-based) |
| **Performance** | Adequate | ~2-3x faster on benchmarks |
| **Multi-worker** | Must run behind a supervisor | `gunicorn --worker-class uvicorn.workers.UvicornWorker` (built-in) |
| **Hot reload** | `--verbosity 2` (limited) | `--reload` with file watching via `watchfiles` |
| **Maintenance** | Low activity, channels team recommends uvicorn | Active development |
| **Production pattern** | `daphne` standalone | `gunicorn` process manager + `uvicorn` async workers |

**Bottom line:** Daphne works but is effectively maintenance-mode. Uvicorn is the
recommended ASGI server for Django Channels going forward. The migration is a
dependency swap — zero application code changes.

---

## File inventory

| # | File | Change type |
|---|------|-------------|
| 1 | `pyproject.toml` | Swap dep: `daphne` → `uvicorn[standard]` + `gunicorn` |
| 2 | `entrypoint.sh` | Replace daphne command with uvicorn/gunicorn |
| 3 | `Dockerfile` | Update CMD, comments, healthcheck (no structural change) |
| 4 | `docker-compose.yml` | No change (entrypoint.sh handles everything) |
| 5 | `config/asgi.py` | No change (works identically) |
| 6 | `config/settings/channels.py` | Optional: add capacity/group_expiry tuning |

---

## Step-by-step changes

### 1. `pyproject.toml` — swap dependencies

```diff
 dependencies = [
     "aiohttp>=3.12.15",
     "celery>=5.5.3",
     "channels>=4.3.1",
     "channels-redis>=4.3.0",
     "cryptography>=45.0.7",
-    "daphne>=4.2.1",
     "django>=5.2.5",
     ...
+    "gunicorn>=23.0.0",
     ...
+    "uvicorn[standard]>=0.34.0",
     "watchfiles>=1.1.0",
 ]
```

**Notes:**
- `uvicorn[standard]` includes `uvloop`, `httptools`, and `watchfiles` for optimal performance
- `watchfiles` is already a dep — `uvicorn[standard]` will use it for `--reload`
- `gunicorn` is the production process manager (handles worker lifecycle, restarts, graceful shutdown)
- `daphne` is fully removed — no need to keep it

**Run after editing:**
```bash
uv lock
uv sync
```

---

### 2. `entrypoint.sh` — replace server command

Replace the final line (line 29):

**Before:**
```bash
exec uv run daphne -b 0.0.0.0 -p ${WEB_PORT:-8000} --application-close-timeout 30 config.asgi:application
```

**After:**
```bash
# ── Determine worker count ──
# WEB_WORKERS: 2 * CPU + 1 is the standard formula.
# os.cpu_count() on containerised platforms returns the HOST CPU count,
# not the allocated vCPU. Cap at 4 cores to prevent spawning too many
# workers on a small container (~100 MB each → OOM).
WEB_WORKERS="${WEB_WORKERS:-0}"
if [ "$WEB_WORKERS" = "0" ]; then
    CPU_COUNT=$(uv run python -c "import os; print(min(os.cpu_count() or 2, 4))")
    WEB_WORKERS=$((CPU_COUNT * 2 + 1))
fi

CONTAINER_PORT="${WEB_PORT:-8000}"

if [ "${DEBUG:-False}" = "True" ]; then
    echo "DEBUG mode — starting Uvicorn with auto-reload (single worker)..."
    exec uv run uvicorn config.asgi:application \
        --host 0.0.0.0 \
        --port "${CONTAINER_PORT}" \
        --reload \
        --reload-dir /app \
        --reload-exclude 'logs' \
        --reload-exclude 'media' \
        --reload-exclude 'staticfiles' \
        --reload-exclude 'static' \
        --reload-exclude '.venv'
else
    echo "Production — starting Gunicorn + Uvicorn workers (${WEB_WORKERS} workers)..."
    exec uv run gunicorn config.asgi:application \
        --bind "0.0.0.0:${CONTAINER_PORT}" \
        --workers "${WEB_WORKERS}" \
        --worker-class uvicorn.workers.UvicornWorker \
        --max-requests 1000 \
        --max-requests-jitter 50 \
        --graceful-timeout 30 \
        --timeout 120 \
        --keep-alive 5 \
        --access-logfile - \
        --error-logfile - \
        --log-level warning
fi
```

**Key production flags explained:**

| Flag | Value | Why |
|------|-------|-----|
| `--workers` | `2 * CPU + 1` (capped at 4 cores) | Standard formula; cap prevents OOM on small containers |
| `--worker-class` | `uvicorn.workers.UvicornWorker` | Async ASGI workers (handles WS + HTTP) |
| `--max-requests` | `1000` | Recycle workers after 1000 requests (prevents memory leaks) |
| `--max-requests-jitter` | `50` | Staggers recycling so all workers don't restart simultaneously |
| `--graceful-timeout` | `30` | Seconds to wait for in-flight requests during shutdown |
| `--timeout` | `120` | Kill worker if it doesn't respond in 120s (long uploads/exports) |
| `--keep-alive` | `5` | HTTP keep-alive between requests |

**Dev mode flags:**

| Flag | Why |
|------|-----|
| `--reload` | Auto-restart on file changes |
| `--reload-dir /app` | Watch only the app directory |
| `--reload-exclude` | Skip logs, media, static, .venv (reduces inotify watches) |

---

### 3. `Dockerfile` — update CMD and comments

```diff
-# Daphne listens on WEB_PORT from entrypoint (default 8000). Health checks belong in docker-compose.yml
-# (web only). Celery worker/beat inherit this image and must not curl :8000.
+# Uvicorn/Gunicorn listens on WEB_PORT from entrypoint (default 8000). Health checks belong in
+# docker-compose.yml (web only). Celery worker/beat inherit this image and must not curl :8000.
 EXPOSE 8000

 HEALTHCHECK --interval=30s --timeout=3s --start-period=20s --retries=3 \
   CMD curl -f http://localhost:8000/health/ || exit 1

-CMD ["uv", "run", "daphne", "-b", "0.0.0.0", "-p", "8000", "config.asgi:application"]
+CMD ["/app/entrypoint.sh"]
```

**Why change CMD to entrypoint.sh?**
The entrypoint now has conditional logic (debug vs production, worker count
calculation). Hardcoding `daphne` in CMD was simpler but the uvicorn/gunicorn
setup benefits from the shell logic. The `CMD` becomes a fallback — `docker-compose.yml`
already overrides with `command: ["/app/entrypoint.sh"]`.

---

### 4. `config/settings/channels.py` — optional tuning

Add production-grade capacity settings (from Rhitoric):

```diff
 CHANNEL_LAYERS = {
     'default': {
         'BACKEND': 'channels_redis.core.RedisChannelLayer',
         'CONFIG': {
             "hosts": [settings.REDIS_URL],
-            "prefix": "channels",  # Prefix to avoid conflicts with other Redis data
-            "expiry": 60,  # Messages expire after 60 seconds if not consumed
+            "prefix": "channels",
+            "expiry": 120,
+            "capacity": 1500,
+            "group_expiry": 86400,
         },
     },
 }
```

| Setting | Before | After | Why |
|---------|--------|-------|-----|
| `expiry` | 60 | 120 | More headroom for slow consumers |
| `capacity` | default (100) | 1500 | Prevents dropped messages under load |
| `group_expiry` | default (86400) | 86400 (explicit) | User groups persist for 24h |

---

### 5. `config/asgi.py` — NO CHANGES

The file is identical between Katesthe-core and Rhitoric-core (same
`ProtocolTypeRouter`, same middleware stack). Uvicorn loads `config.asgi:application`
exactly like daphne did — the ASGI interface is standardized.

---

## Validation

After making changes:

```bash
# 1. Lock and sync
uv lock && uv sync

# 2. Verify daphne is gone
uv run python -c "import daphne" 2>&1 | grep -q "ModuleNotFoundError" && echo "PASS: daphne removed"

# 3. Verify uvicorn is installed
uv run python -c "import uvicorn; print(f'uvicorn {uvicorn.__version__}')"

# 4. Verify gunicorn is installed
uv run python -c "import gunicorn; print(f'gunicorn {gunicorn.__version__}')"

# 5. Verify ASGI app loads
uv run python -c "
import django; import os
os.environ['DJANGO_SETTINGS_MODULE'] = 'config.django.test'
django.setup()
from config.asgi import application
print(f'ASGI app: {type(application).__name__}')
"

# 6. Start dev server manually (smoke test)
DEBUG=True /app/entrypoint.sh
# → Should print "DEBUG mode — starting Uvicorn with auto-reload..."
# → Should listen on :8000
# → Ctrl+C to stop

# 7. Docker full stack
docker compose down && docker compose up --build -d
docker compose logs web --tail 50
# → Should show "Production — starting Gunicorn + Uvicorn workers..."
# → Health check should pass

# 8. WebSocket smoke test (requires wscat or websocat)
wscat -c ws://localhost:8000/ws/test/
# → Should connect (ExampleConsumer)
```

---

## Rollback

If something breaks, revert is trivial:

```bash
# Re-add daphne, remove uvicorn/gunicorn in pyproject.toml
# Revert entrypoint.sh to single daphne line
# Revert Dockerfile CMD
uv lock && uv sync
docker compose up --build -d
```

---

## Environment variables

| Variable | Default | Purpose |
|----------|---------|---------|
| `DEBUG` | `False` | `True` = uvicorn with `--reload`; `False` = gunicorn + uvicorn workers |
| `WEB_PORT` | `8000` | Port to listen on |
| `WEB_WORKERS` | auto (`2 * min(CPU, 4) + 1`) | Override worker count; set to `1` for debugging |

---

## What does NOT change

- `config/asgi.py` — identical, ASGI is standardized
- `config/routing.py` — WebSocket routing unchanged
- `config/settings/channels.py` — optional tuning only
- All consumers — they speak ASGI, not daphne
- All middleware — `JWTAuthMiddleware`, `AuthMiddlewareStack` work identically
- `docker-compose.yml` — already delegates to `entrypoint.sh`
- Tests — nothing tests the server binary; all tests use Django test client

---

## Production considerations

### Memory per worker

Each gunicorn+uvicorn worker uses ~80-120 MB. Formula:

```
Total memory needed = WEB_WORKERS × 120 MB + overhead (~200 MB)
```

| Container RAM | Recommended workers | Why |
|--------------|-------------------|-----|
| 512 MB | 2 | `2 × 120 + 200 = 440 MB` |
| 1 GB | 3-4 | `4 × 120 + 200 = 680 MB` |
| 2 GB | 5-9 | Auto-detect usually picks correctly |

Override: `WEB_WORKERS=2` in `.env` for small containers.

### Graceful shutdown

Gunicorn handles SIGTERM gracefully:
1. Stops accepting new connections
2. Waits up to `--graceful-timeout` (30s) for in-flight requests
3. Kills remaining workers after timeout
4. WebSocket connections get a clean close frame

Docker's `stop_grace_period: 30s` in `docker-compose.yml` already aligns with this.

### WebSocket connection limits

Uvicorn has no hard WebSocket connection limit. The practical limit is:
- Redis channel layer `capacity` (set to 1500)
- File descriptor limit (`ulimit -n`, usually 65536 in containers)
- Memory per connection (~1-5 KB)

For the template, these defaults handle hundreds of concurrent WS connections comfortably.
