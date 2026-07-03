# 005 — Keep-warm Celery task (8.1 task)

**Status:** [PENDING]
**Phase:** 1
**Group:** A
**Risk:** LOW
**Effort:** 30m
**Dependencies:** none

## Goal
Add a `keep_warm` periodic Celery task that prevents PaaS cold-start latency by warming the worker DB pool and (optionally) pinging the API health endpoint — stdlib only, no external dependency.

## Context
Extracted from `SRC:utils/tasks.py` (already generic). The task runs `SELECT 1` and, if `HEALTH_PING_URL` is set, GETs `<url>/api/v1/health/` via `urllib.request`. The **celery.py beat entry for this task is owned by subtask 006**, not here — this subtask creates only the task file, its test, and the env-example doc. 006 references it by the string `"utils.tasks.keep_warm"`.

## Locked decision
`HEALTH_PING_URL` is read via `os.getenv("HEALTH_PING_URL", "")` at module import (matching SRC) — it is NOT a Pydantic `MainSettings` field. Do not modify `config/settings/config.py` or `config/settings/__init__.py`.

## Existing pattern to follow
- `SRC:/home/tmpusr/Documents/github/Rhitoric-core/utils/tasks.py` — copy the `keep_warm` task as-is.
- Task style / logger: `accounts/tasks.py` and `static/exp_app/tasks.py` for `@shared_task` conventions in this repo; `from config.logger import logger`.

## Files Owned
- `utils/tasks.py`
- `utils/tests/test_tasks.py`
- `.env.prod.example`

## Implementation Steps

### Step 1 — Create `utils/tasks.py`
```python
import os, urllib.request, urllib.error
from celery import shared_task
from django.db import connection
from config.logger import logger

_HEALTH_PING_URL = os.getenv("HEALTH_PING_URL", "").rstrip("/")

@shared_task(name="utils.tasks.keep_warm", time_limit=15, soft_time_limit=12, ignore_result=True)
def keep_warm():
    with connection.cursor() as cursor:
        cursor.execute("SELECT 1")
    logger.debug("keep_warm.db_ok")
    if not _HEALTH_PING_URL:
        return
    url = f"{_HEALTH_PING_URL}/api/v1/health/"
    try:
        req = urllib.request.Request(url, method="GET")
        with urllib.request.urlopen(req, timeout=10) as resp:
            status = resp.getcode()
        logger.info("keep_warm.ping_ok", extra={"url": url, "status": status})
    except urllib.error.HTTPError as exc:
        logger.warning("keep_warm.ping_http_error", extra={"url": url, "status": exc.code})
    except Exception as exc:
        logger.warning("keep_warm.ping_failed", extra={"url": url, "error": str(exc)})
```
Keep the module + function docstrings describing the two warm-up steps and the short time limits.

### Step 2 — Document env var in `.env.prod.example`
Append (near the bottom, after the existing Email/Theme blocks — do NOT create the file, it exists):
```
# Optional: ping the API process to prevent cold starts (keep-warm task)
# HEALTH_PING_URL=https://your-app.railway.app
```

## Tests
Create `utils/tests/test_tasks.py` (`@pytest.mark.django_db` for the DB cursor):
- **DB warm only (no ping):** with `_HEALTH_PING_URL` empty (default under test — env unset), call `keep_warm()`; assert it returns `None` and does not attempt any HTTP call (`patch("utils.tasks.urllib.request.urlopen")` and assert not called).
- **Ping success:** `patch("utils.tasks._HEALTH_PING_URL", "http://x")` (module-level constant) and `patch("utils.tasks.urllib.request.urlopen")` returning a context-manager mock whose `getcode()` returns 200; call task; assert `urlopen` called with the `/api/v1/health/` URL.
- **HTTPError branch:** `urlopen` side_effect `urllib.error.HTTPError(url, 503, "err", {}, None)`; assert task does not raise (warning path).
- **Generic error branch:** `urlopen` side_effect `Exception("boom")`; assert task does not raise.

Note: since `_HEALTH_PING_URL` is bound at import, patch the module attribute directly (`patch.object(utils.tasks, "_HEALTH_PING_URL", "http://x")`) rather than the env var.

## Validation
```bash
uv run pytest utils/tests/test_tasks.py -x -v --ds=config.django.test
uv run python -c "from utils.tasks import keep_warm; print('OK')"
```

## Acceptance Criteria
- [ ] `keep_warm` task registered under name `utils.tasks.keep_warm` with 15s/12s limits and `ignore_result=True`.
- [ ] Uses stdlib `urllib` only — no `requests`/`httpx`.
- [ ] HTTP failures logged as warnings, never raised.
- [ ] `.env.prod.example` documents `HEALTH_PING_URL` (commented).
- [ ] No change to `config/settings/celery.py` (that is 006's file).
