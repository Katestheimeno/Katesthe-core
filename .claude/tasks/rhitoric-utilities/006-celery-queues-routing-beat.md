# 006 — Celery queues, routing, beat, kombu (8.1 beat + 10.1 + 10.2)

**Status:** [PENDING]
**Phase:** 1
**Group:** A
**Risk:** MEDIUM
**Effort:** 30m
**Dependencies:** none (references task names by string only)

## Goal
Replace the placeholder Celery queue/route config with a production-ready three-queue architecture, add the `keep-warm` and `flush-expired-jwt-tokens` beat entries, and declare `kombu` explicitly in `pyproject.toml`.

## Context
This subtask **owns `config/settings/celery.py` entirely** to keep file ownership disjoint. It bundles: Phase 8.1's `keep-warm` beat entry, Phase 10.1's three-queue setup + routes, and Phase 10.2's kombu declaration. The current file has commented-out `CELERY_TASK_QUEUES` / `CELERY_TASK_ROUTES` dict placeholders and a `CELERY_BEAT_SCHEDULE` with a single `example-cleanup` entry. It uses an `imports` list + `__all__ = imports` pattern — any new setting name MUST be appended to `imports`.

## Cross-plan note (IMPORTANT)
- `accounts.tasks.flush_expired_jwt_tokens` is created by the **rhitoric-auth-core** plan (Phase 3.2). Celery routes/beat by NAME STRING, so referencing it now is harmless even though the task does not yet exist. Ship its beat entry + `→ slow` route LIVE.
- `accounts.tasks.process_permanent_deletions` is **NOT created by any phase in any plan**. Ship its route ONLY as a COMMENTED example with a note. Do NOT route a live task that will never exist.

## Existing pattern to follow
- Current `config/settings/celery.py` (this repo) — preserve its `imports` list / `__all__` mechanism and the existing serializer/worker-tuning/time-limit blocks.
- `SRC:config/settings/celery.py` — three-queue setup shape.

## Files Owned
- `config/settings/celery.py`
- `pyproject.toml`
- `config/tests/test_celery_config.py`

## Implementation Steps

### Step 1 — Beat schedule (`CELERY_BEAT_SCHEDULE`)
Add two entries alongside the existing `example-cleanup`:
```python
"keep-warm": {
    "task": "utils.tasks.keep_warm",
    "schedule": 240.0,  # every 4 minutes
},
"flush-expired-jwt-tokens": {
    "task": "accounts.tasks.flush_expired_jwt_tokens",
    "schedule": 86400,  # daily; task provided by the auth-core plan (routed by name)
},
```

### Step 2 — Queues + default queue
Replace the commented `CELERY_TASK_QUEUES` dict placeholder with the kombu tuple, and add `CELERY_TASK_DEFAULT_QUEUE`:
```python
from kombu import Queue   # add at top of file with the other imports

CELERY_TASK_DEFAULT_QUEUE = "default"
CELERY_TASK_QUEUES = (
    Queue("realtime", routing_key="realtime"),
    Queue("default", routing_key="default"),
    Queue("slow", routing_key="slow"),
)
```
Append `"CELERY_TASK_DEFAULT_QUEUE"` to the `imports` list (so `__all__` exports it). `CELERY_TASK_QUEUES` is already in `imports`.

### Step 3 — Routes
Replace the commented `CELERY_TASK_ROUTES` placeholder with:
```python
CELERY_TASK_ROUTES = {
    # Nightly maintenance → slow queue (don't block default workers)
    "accounts.tasks.flush_expired_jwt_tokens": {"queue": "slow"},

    # Example (no plan creates this task yet — keep commented until it exists):
    # "accounts.tasks.process_permanent_deletions": {"queue": "slow"},

    # Everything else → default (projects add routes as they add tasks).
}
```

### Step 4 — Worker comments
Add a comment block documenting per-queue worker invocation:
```python
# Run workers per queue:
#   celery -A config.celery.app worker -Q realtime --concurrency=4
#   celery -A config.celery.app worker -Q default  --concurrency=8
#   celery -A config.celery.app worker -Q slow     --concurrency=2
# Or a single worker consuming all:
#   celery -A config.celery.app worker -Q realtime,default,slow --concurrency=8
```

### Step 5 — `pyproject.toml`
Add `"kombu>=5.3.0"` (or the version already resolved transitively by Celery — check `uv.lock`) to `[project].dependencies`, keeping the list alphabetically consistent with the existing ordering. This is a self-documenting explicit declaration; kombu is already installed transitively, so no reinstall is required.

## Tests
Create `config/tests/test_celery_config.py` (reads settings only):
- `settings.CELERY_TASK_DEFAULT_QUEUE == "default"`.
- `{q.name for q in settings.CELERY_TASK_QUEUES} == {"realtime", "default", "slow"}`.
- `settings.CELERY_TASK_ROUTES["accounts.tasks.flush_expired_jwt_tokens"]["queue"] == "slow"`.
- `"process_permanent_deletions"` NOT present as a live route key (it is commented).
- `"keep-warm" in settings.CELERY_BEAT_SCHEDULE` and its `task == "utils.tasks.keep_warm"` and `schedule == 240.0`.
- `"flush-expired-jwt-tokens" in settings.CELERY_BEAT_SCHEDULE`.
- `from kombu import Queue` succeeds.

## Validation
```bash
uv run pytest config/tests/test_celery_config.py -x -v --ds=config.django.test
uv run python -c "
import django, os
os.environ.setdefault('DJANGO_SETTINGS_MODULE','config.django.test'); django.setup()
from django.conf import settings
assert settings.CELERY_TASK_DEFAULT_QUEUE == 'default'
assert {q.name for q in settings.CELERY_TASK_QUEUES} == {'realtime','default','slow'}
print('OK')
"
```

## Acceptance Criteria
- [ ] `config/settings/celery.py` defines `CELERY_TASK_DEFAULT_QUEUE`, kombu-based `CELERY_TASK_QUEUES` (realtime/default/slow), and `CELERY_TASK_ROUTES`.
- [ ] `CELERY_TASK_DEFAULT_QUEUE` appended to `imports`/`__all__`.
- [ ] `keep-warm` (240s) and `flush-expired-jwt-tokens` (daily) beat entries present.
- [ ] `process_permanent_deletions` route ships COMMENTED with a note.
- [ ] `kombu` declared in `pyproject.toml`.
- [ ] Settings load cleanly; no domain-specific queues/routes added.
