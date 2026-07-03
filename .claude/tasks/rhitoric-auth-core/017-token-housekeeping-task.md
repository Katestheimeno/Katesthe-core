# 017 — Token housekeeping task + tasks package (3.2)

**Status:** [PENDING]
**Phase:** 3
**Group:** task
**Risk:** MEDIUM
**Effort:** 35m
**Dependencies:** none within Phase 3 (independent)

## Goal
Convert `accounts/tasks.py` (single module) into an `accounts/tasks/` package and add the `flush_expired_jwt_tokens` task.

## Context
`accounts/tasks.py` currently holds `example_cleanup_task` (name `"accounts.tasks.example_cleanup_task"`). Callers: `config/settings/celery.py` (beat) and `accounts/tests/tasks/test_example.py` (via `from accounts.tasks import ...`). Preserve every task NAME so beat/routes keep working.

> **CROSS-FEATURE OWNERSHIP:** `config/settings/celery.py` is owned EXCLUSIVELY by the ACTIVE sibling feature **rhitoric-utilities / subtask 006** (it adds the 3-queue setup, routes, `kombu`, AND the `flush-expired-jwt-tokens` beat entry — referencing this task by the string `"accounts.tasks.flush_expired_jwt_tokens"`). **Do NOT edit `config/settings/celery.py` in this subtask.** This subtask only creates the task with the exact name below so utilities/006's by-string beat entry resolves at runtime. No import coupling → no hard ordering. Verify no double-add of the beat entry with utilities/006.

## Existing pattern to follow
`SRC:accounts/tasks/token_tasks.py`. The existing `example_cleanup_task` decorator config shows the `@shared_task(name=..., autoretry_for=..., ...)` house style.

## Files Owned
- `accounts/tasks/__init__.py` (C — re-exports)
- `accounts/tasks/_example.py` (C — moved `example_cleanup_task`)
- `accounts/tasks/token_tasks.py` (C)
- `accounts/tests/tasks/test_token_tasks.py` (C)
- `accounts/tasks.py` (DELETE)

## Implementation Steps

### Step 1 — package
- Create `accounts/tasks/` package. Move `example_cleanup_task` verbatim into `accounts/tasks/_example.py` (keep `name="accounts.tasks.example_cleanup_task"`).
- `accounts/tasks/__init__.py`: `from ._example import example_cleanup_task` and `from .token_tasks import flush_expired_jwt_tokens` (+ `__all__`). This keeps `from accounts.tasks import example_cleanup_task` working for the existing test AND for utilities/006's existing `example-cleanup` beat entry.
- Delete the old `accounts/tasks.py`.

### Step 2 — `token_tasks.py`
```python
@shared_task(name="accounts.tasks.flush_expired_jwt_tokens", autoretry_for=(Exception,),
             max_retries=3, retry_backoff=True, retry_backoff_max=300, retry_jitter=True,
             time_limit=60, soft_time_limit=50, ignore_result=True)
def flush_expired_jwt_tokens():
    ...
```
Delete expired `OutstandingToken` rows (`expires_at__lt=now()`) — cascades to `BlacklistedToken`. Log `jwt.flush_expired_tokens` with counts. Return the OutstandingToken delete count.

### Step 3 — DO NOT touch celery.py
The beat schedule entry is added by rhitoric-utilities/006 (see cross-feature note). This subtask exposes the task by name only.

## Tests (`accounts/tests/tasks/test_token_tasks.py`)
- `@pytest.mark.django_db`: create expired + non-expired OutstandingTokens; run `flush_expired_jwt_tokens()` (eager) → only expired removed; count returned.
- Assert the task name is `"accounts.tasks.flush_expired_jwt_tokens"`.
- Assert `from accounts.tasks import example_cleanup_task, flush_expired_jwt_tokens` both import (package re-export intact).

## Validation
```bash
uv run pytest accounts/tests/tasks/ -x -v --ds=config.django.test
```

## Acceptance Criteria
- [ ] `accounts/tasks/` package; old module deleted; existing task name/import preserved.
- [ ] `flush_expired_jwt_tokens` deletes only expired tokens; exposed under the exact name.
- [ ] `config/settings/celery.py` NOT modified here (owned by rhitoric-utilities/006).
- [ ] Existing `test_example.py` still passes. Tests pass.
