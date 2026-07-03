# 001 — Celery task helpers (6.1)

**Status:** [PENDING]
**Phase:** 1
**Group:** A
**Risk:** LOW
**Effort:** 30m
**Dependencies:** none

## Goal
Add safe Celery-dispatch helpers that work in both eager (test) and production (broker) modes without crashing the app when the broker is down.

## Context
Callers currently invoke `.delay()` directly, which raises if the broker is unavailable and misroutes by-name dispatch in non-worker processes. This module centralizes safe dispatch. Pattern extracted verbatim (generic already) from `SRC:utils/celery_helpers.py`.

## Existing pattern to follow
- `SRC:/home/tmpusr/Documents/github/Rhitoric-core/utils/celery_helpers.py` — copy the generic pattern as-is (it has no domain logic).
- Logger import convention: `from config.logger import logger` (see any file under `config/` or `utils/`).

## Files Owned
- `utils/celery_helpers.py`
- `utils/tests/test_celery_helpers.py`

## Implementation Steps

### Step 1 — Create `utils/celery_helpers.py`
Implement three module-level functions (no classes):

- `safe_task_delay(task, *args, **kwargs)`:
  - `is_eager = getattr(settings, 'CELERY_TASK_ALWAYS_EAGER', False)`
  - Eager: `return task.apply(args=args, kwargs=kwargs)` inside try/except; on exception `logger.debug(...)` and `return None`.
  - Production: `return task.delay(*args, **kwargs)` inside try/except; on exception `logger.error(..., exc_info=True, extra={...})` and `return None`.
- `safe_task_delay_with_countdown(task, countdown_seconds: int, *args, **kwargs)`:
  - Same eager branch (countdown ignored in eager). Production branch uses `task.apply_async(args=args, kwargs=kwargs, countdown=countdown_seconds)`.
- `safe_send_task(celery_app, task_name: str, args: tuple = (), kwargs: dict = None)`:
  - Default `kwargs = {}` when None.
  - Eager: look up `celery_app.tasks.get(task_name)`; if found `return task_obj.apply(args=args, kwargs=kwargs)`; else try `celery_app.send_task(...)`, and on failure `rsplit('.', 1)` + `importlib.import_module` + `getattr` + `.apply(...)`, re-raising if it still fails.
  - Production: `return celery_app.send_task(task_name, args=args, kwargs=kwargs)` inside try/except; on exception `logger.error(..., exc_info=True, extra={...})` and `return None`.

Use `from django.conf import settings` and `from config.logger import logger`. Keep the module docstring and function docstrings (they document eager-vs-prod behavior).

## Tests
Create `utils/tests/test_celery_helpers.py` using `unittest.mock` (no DB needed — no `django_db` marker):

- **safe_task_delay eager:** with `settings.CELERY_TASK_ALWAYS_EAGER=True` (it is True under test settings), pass a `Mock()` task; assert `task.apply` called with `args`/`kwargs`, and `task.delay` NOT called.
- **safe_task_delay eager error → None:** task whose `.apply` raises → returns `None`.
- **safe_task_delay production:** `@override_settings(CELERY_TASK_ALWAYS_EAGER=False)`; mock task; assert `task.delay` called; returns its value.
- **safe_task_delay production broker error → None:** `.delay` raises → returns `None` (assert `logger.error` path not raising).
- **safe_task_delay_with_countdown production:** `@override_settings(...=False)`; assert `task.apply_async` called with `countdown=<n>`.
- **safe_send_task eager registry hit:** mock `celery_app` with `tasks.get` returning a mock task; assert `task_obj.apply` called.
- **safe_send_task production:** `@override_settings(...=False)`; assert `celery_app.send_task` called with the name.

Prefer `patch("utils.celery_helpers.logger")` where you assert logging, and `django.test.override_settings` for the mode toggle.

## Validation
```bash
uv run pytest utils/tests/test_celery_helpers.py -x -v --ds=config.django.test
uv run python -c "from utils.celery_helpers import safe_task_delay, safe_task_delay_with_countdown, safe_send_task; print('OK')"
```

## Acceptance Criteria
- [ ] All three functions importable from `utils.celery_helpers`.
- [ ] Eager and production branches both covered by tests (100% branch on new code).
- [ ] No broker connection attempted under test settings.
- [ ] No domain-specific imports (no `game`, `accounts`, etc.).
