# 013 — Celery Task Template + settings

**Status:** [PENDING]
**Phase:** 2
**Group:** A (concurrent with 010–012, 014–016)
**Risk:** LOW
**Effort:** 35m
**Dependencies:** Phase 1 complete

## Goal
Add an example Celery task demonstrating the standard retry/idempotency decorator, and add task-security + worker-tuning + an example beat entry to `config/settings/celery.py`.

## Context
`.claude/rules/layers.md` §6 mandates idempotent, auto-retrying tasks enqueued from services via `on_commit`. This gives the template a canonical example and the hardened Celery settings. Celery infra (`config/celery.py`, worker/beat docker services) already exists — only add settings + an example task.

## SRC reference to adapt from
`SRC:notifications/tasks.py` (decorator pattern) and `SRC:config/settings/celery.py` (security + worker + beat). **Strip** OneSignal/domain logic — the example task is self-contained.

## Files Owned
- `accounts/tasks.py` (C)
- `accounts/tests/tasks/__init__.py` (C)
- `accounts/tests/tasks/test_example.py` (C)
- `config/settings/celery.py` (M — sole owner)

## Implementation Steps

### Step 1 — `accounts/tasks.py`
```python
from celery import shared_task
from config.logger import logger

@shared_task(
    name="accounts.tasks.example_cleanup_task",
    autoretry_for=(Exception,),
    max_retries=3,
    retry_backoff=True,
    retry_backoff_max=300,
    retry_jitter=True,
)
def example_cleanup_task():
    """Example: delete unverified users older than 30 days. Idempotent by design."""
    from django.utils import timezone
    from datetime import timedelta
    from django.contrib.auth import get_user_model
    User = get_user_model()
    cutoff = timezone.now() - timedelta(days=30)
    # Idempotent: filtering by state means re-running deletes nothing new.
    qs = User.objects.filter(is_active=False, date_joined__lt=cutoff)
    count = qs.count()
    qs.delete()
    logger.bind(deleted=count).info("accounts.example_cleanup_task.done")
    return count
```
Adjust the field names to the actual User model (verify `date_joined` / `is_active` / verification field exist; use `is_verified` if that is the intended "unverified" flag — read `accounts/models`). Keep it a realistic but harmless example.

### Step 2 — `config/settings/celery.py`
Append (register each new name in the `imports` list so `__all__` exports it):
```python
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_WORKER_MAX_TASKS_PER_CHILD = 500
CELERY_WORKER_MAX_MEMORY_PER_CHILD = 256_000  # 256MB
CELERY_TASK_TIME_LIMIT = 600
CELERY_TASK_SOFT_TIME_LIMIT = 540
CELERY_WORKER_PREFETCH_MULTIPLIER = 1
```
Add the example beat entry to the existing `CELERY_BEAT_SCHEDULE` dict:
```python
CELERY_BEAT_SCHEDULE = {
    "example-cleanup": {
        "task": "accounts.tasks.example_cleanup_task",
        "schedule": 86400,  # daily
    },
}
```
Follow the file's existing `imports += [...]` / `__all__ = imports` convention.

## Tests (`accounts/tests/tasks/test_example.py`) — `@pytest.mark.django_db`
Celery runs eager in tests (`CELERY_TASK_ALWAYS_EAGER = True`).
- Create 2 inactive users older than 30 days (via `UserFactory`, set `date_joined`) and 1 recent/active user; call `example_cleanup_task()` (or `.delay().get()`); assert it returns/deletes 2 and leaves the recent/active one.
- Idempotency: calling the task twice does not error and the second call deletes 0.
- Assert the decorator config: `example_cleanup_task.max_retries == 3` and `example_cleanup_task.name == "accounts.tasks.example_cleanup_task"`.
Create `accounts/tests/tasks/__init__.py` (empty) so pytest discovers the package.

## Validation
```bash
uv run pytest accounts/tests/tasks/ -x -v --ds=config.django.test
```

## Acceptance Criteria
- [ ] `example_cleanup_task` uses the full autoretry/backoff decorator and is idempotent.
- [ ] Celery security + worker-tuning + time-limit + prefetch settings added and exported.
- [ ] Example beat entry present.
- [ ] Task field references match the real User model; tests pass.
