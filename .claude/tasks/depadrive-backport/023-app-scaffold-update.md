# 023 — App Scaffold Update

**Status:** [PENDING]
**Phase:** 3
**Group:** A (concurrent with 017–022)
**Risk:** LOW
**Effort:** 20m
**Dependencies:** Phase 2 complete (mirrors the Celery task template from subtask 013)

## Goal
Update the app scaffold under `static/exp_app/` so `starttemplateapp`-generated apps include a standard Celery `tasks.py` template and a task test directory.

## Context
`static/exp_app/` is the layered template that the app-generator copies. New apps should start with the hardened Celery task decorator pattern established in subtask 013. Current scaffold has `models/`, `services/`, `controllers/`, `tests/...` but no `tasks.py` or `tests/tasks/`.

## SRC reference to adapt from
The task-decorator shape from subtask 013 (`accounts/tasks.py`) and `.claude/rules/layers.md` §6. No direct SRC file — mirror the in-repo pattern.

## Files Owned
- `static/exp_app/tasks.py` (C)
- `static/exp_app/tests/tasks/__init__.py` (C)

## Implementation Steps

### Step 1 — `static/exp_app/tasks.py`
Add a commented, copy-ready example (kept inert so a freshly-generated app has no live beat entry until edited):
```python
"""
Celery tasks for this app.
Follow the standard pattern: idempotent, auto-retrying, enqueued from a service via transaction.on_commit.
"""
# from celery import shared_task
# from config.logger import logger
#
# @shared_task(
#     name="<app_label>.tasks.example_task",
#     autoretry_for=(Exception,),
#     max_retries=3,
#     retry_backoff=True,
#     retry_backoff_max=300,
#     retry_jitter=True,
# )
# def example_task():
#     """Idempotent by design. Persist correlation state in the DB, not in task args."""
#     logger.info("<app_label>.example_task.done")
```

### Step 2 — `static/exp_app/tests/tasks/__init__.py`
Create the empty package so generated apps have a `tests/tasks/` home mirroring `tests/services/`, `tests/controllers/`, etc.

## Tests
The scaffold is a static template, not executed code — no unit tests. Verify the files exist and are syntactically valid Python.

## Validation
```bash
uv run python -c "import ast; ast.parse(open('static/exp_app/tasks.py').read()); ast.parse(open('static/exp_app/tests/tasks/__init__.py').read()); print('scaffold ok')"
ls static/exp_app/tasks.py static/exp_app/tests/tasks/__init__.py
```

## Acceptance Criteria
- [ ] `static/exp_app/tasks.py` present with the commented standard task template.
- [ ] `static/exp_app/tests/tasks/__init__.py` present.
- [ ] Both parse as valid Python; scaffold structure consistent with existing layers.
