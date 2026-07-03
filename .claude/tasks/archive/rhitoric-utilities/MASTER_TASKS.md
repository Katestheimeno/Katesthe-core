# Rhitoric Utilities Backport

Priority: P1
Status: done
**Date:** 2026-07-03
**Source:** `RHITORIC_BACKPORT_PLAN.md` — Phases 6, 7, 8, 9, 10, 11 + "App Scaffold Update"
**Goal:** Backport generic operational utilities (safe Celery dispatch, external-API health-check skeleton, test throttle override, Pydantic↔drf-spectacular bridge, keep-warm task, admin click-to-copy mixin, Celery priority queues/routing, enhanced SoftDelete/BooleanChoices mixins, scaffold auth+permissions) into this template — generic patterns only, no domain logic.

---

## Locked decisions

1. **Source of truth:** SRC = `/home/tmpusr/Documents/github/Rhitoric-core`, DST = this repo. Extract the GENERIC pattern only. Obey the plan's "What NOT to Do" section: no domain logic (game/AI/elearning), strip `console.log` from `copy-field.js`, ship only `keep-warm` + `flush-expired-jwt-tokens` beat entries + the 3-queue skeleton with 2 starter routes, no domain mixins (e.g. MuxPlaybackMixin) / domain task routes / domain beat entries.
2. `INSTALLED_APPS` lives in `config/settings/apps_middlewares.py` (`PROJECT_APPS`). There is NO `config/settings/django.py`. `utils` is already an installed app (its `AppDirectoriesFinder` static dir is auto-discovered).
3. New settings module → `config/settings/<name>.py` + wire in `config/settings/__init__.py`. New env-var fields → Pydantic `MainSettings` in `config/settings/config.py`. **`HEALTH_PING_URL` is read directly via `os.getenv` in the keep-warm task (matches SRC) — it is NOT a Pydantic field**, so no `config.py`/`__init__.py` change is required for it.
4. Django entry: `config/django/base.py` → `from config.settings import *`; env overrides in `config/django/{local,production,test}.py`.
5. `.env.local.example`, `.env.prod.example`, `.env.test.example` all EXIST — modify, never create.
6. Tests live in `<app>/tests/...`; factory-boy; run `uv run pytest --ds=config.django.test`; coverage floor 75%.
7. File ownership across subtasks is STRICTLY DISJOINT. Every subtask file is self-contained.
8. `config/settings/celery.py` uses an `imports` list + `__all__ = imports` pattern — any new setting name added must be appended to `imports`.

---

## Priority queue

| ID | Subtask | Phase | Group | Risk | Effort | Scope |
|----|---------|-------|-------|------|--------|-------|
| 001 | Celery task helpers (6.1) | 1 | A | LOW | 30m | `safe_task_delay` / `_with_countdown` / `safe_send_task` |
| 002 | External-API health-check command skeleton (6.2) | 1 | A | MED | 45m | generic probe command, empty `SERVICES` |
| 003 | Test throttle-rate override (6.3) | 1 | A | LOW | 15m | high rates in `config/django/test.py` |
| 004 | Pydantic→drf-spectacular bridge (7.1) | 1 | A | MED | 35m | 4 schema helper functions |
| 005 | Keep-warm Celery task (8.1 task) | 1 | A | LOW | 30m | `utils/tasks.py::keep_warm` + env example |
| 006 | Celery queues, routing, beat, kombu (8.1 beat + 10.1 + 10.2) | 1 | A | MED | 30m | 3-queue setup, routes, 2 beat entries, kombu dep |
| 007 | Admin CopyableFieldMixin + css/js (9.1) | 1 | A | MED | 45m | mixin + assets, strip `console.log` |
| 008 | Enhanced SoftDelete + BooleanChoices mixins (11.1 + 11.2) | 1 | A | MED | 45m | manager/queryset + `BooleanChoices` |
| 009 | App scaffold: authentication + permissions | 1 | A | LOW | 15m | `static/exp_app/` placeholders |

---

## Subtasks

<!-- Canonical status list. Status token: PENDING | IN_PROGRESS | BLOCKED | COMPLETED | SKIPPED | DEFERRED -->
- [COMPLETED] [001-celery-task-helpers.md](001-celery-task-helpers.md) — Celery task helpers (6.1)
- [COMPLETED] [002-check-external-apis-command.md](002-check-external-apis-command.md) — External-API health-check command skeleton (6.2)
- [COMPLETED] [003-test-throttle-override.md](003-test-throttle-override.md) — Test throttle-rate override (6.3)
- [COMPLETED] [004-spectacular-pydantic-bridge.md](004-spectacular-pydantic-bridge.md) — Pydantic→drf-spectacular bridge (7.1)
- [COMPLETED] [005-keep-warm-task.md](005-keep-warm-task.md) — Keep-warm Celery task (8.1 task)
- [COMPLETED] [006-celery-queues-routing-beat.md](006-celery-queues-routing-beat.md) — Celery queues, routing, beat, kombu (8.1 beat + 10.1 + 10.2)
- [COMPLETED] [007-admin-copyable-mixin.md](007-admin-copyable-mixin.md) — Admin CopyableFieldMixin + css/js (9.1)
- [COMPLETED] [008-model-mixins.md](008-model-mixins.md) — Enhanced SoftDelete + BooleanChoices mixins (11.1 + 11.2)
- [COMPLETED] [009-app-scaffold-auth-permissions.md](009-app-scaffold-auth-permissions.md) — App scaffold auth + permissions placeholders

---

## Dependency graph

```
Phase 1 — Group A (all 9 run concurrently; file sets are disjoint):

  001 ─┐
  002 ─┤
  003 ─┤
  004 ─┤
  005 ─┼──► Phase 2: full-suite gate + cross-review
  006 ─┤
  007 ─┤
  008 ─┤
  009 ─┘
```

- **No intra-plan hard edges.** The two shared-file hazards were resolved by bundling, not sequencing:
  - `config/settings/celery.py` — owned ENTIRELY by **006** (keep-warm beat + `flush-expired-jwt-tokens` beat + 3-queue setup + routes + kombu). The keep-warm TASK itself (005) lives in `utils/tasks.py`; 006 references it only by the string `"utils.tasks.keep_warm"`, so there is no import coupling and no ordering requirement (Celery routes/beat by name string).
  - `utils/models/__init__.py` — owned ENTIRELY by **008** (SoftDelete re-exports already present via `from ._softdelete import *`; 008 adds `from .choices import *`). Both `_softdelete.py` and `choices.py` are created/edited inside 008.
- **Soft ordering (non-blocking):** 005 (creates `utils/tasks.py`) ideally lands before or with 006, but is not required — the beat entry is a string reference and Celery beat does not run under eager test settings.

---

## File ownership (strictly disjoint)

### 001 (Group A)
- `utils/celery_helpers.py`
- `utils/tests/test_celery_helpers.py`

### 002 (Group A)
- `utils/management/commands/check_external_apis.py`
- `utils/tests/test_check_external_apis.py`

### 003 (Group A)
- `config/django/test.py`
- `config/tests/test_throttle_override.py`

### 004 (Group A)
- `config/spectacular_pydantic.py`
- `config/tests/test_spectacular_pydantic.py`

### 005 (Group A)
- `utils/tasks.py`
- `utils/tests/test_tasks.py`
- `.env.prod.example`

### 006 (Group A)
- `config/settings/celery.py`
- `pyproject.toml`
- `config/tests/test_celery_config.py`

### 007 (Group A)
- `utils/admin/__init__.py`
- `utils/admin/mixins.py`
- `utils/admin/css/copy-field.css`
- `utils/admin/js/copy-field.js`
- `utils/tests/test_admin_mixins.py`

### 008 (Group A)
- `utils/models/_softdelete.py`
- `utils/models/choices.py`
- `utils/models/__init__.py`
- `utils/tests/test_softdelete.py`
- `utils/tests/test_choices.py`

### 009 (Group A)
- `static/exp_app/authentication.py`
- `static/exp_app/permissions/__init__.py`

**No file appears in more than one subtask.** Note: `config/django/test.py` (003), `config/settings/celery.py` (006), and `pyproject.toml` (006) are the only shared-infra files touched; each has exactly one owner.

---

## Cross-plan dependencies (document; do NOT block)

- **003 (throttle override)** overrides `DEFAULT_THROTTLE_RATES` keys that are *defined* by the separate **rhitoric-auth-core** plan (Phase 4). Use the robust dict-comprehension `{k: "9999/min" for k in REST_FRAMEWORK.get("DEFAULT_THROTTLE_RATES", {})}` so it works regardless of which keys exist today. Soft dependency only — the comprehension is a no-op if the keys are absent.
- **006 (celery routing/beat)** references `accounts.tasks.flush_expired_jwt_tokens` (created by **rhitoric-auth-core** Phase 3.2) and `accounts.tasks.process_permanent_deletions` (**NOT created by any phase in any plan**). Celery routes/beat by name string, so referencing a not-yet-registered task is harmless. Rules:
  - `flush-expired-jwt-tokens` beat entry + its `→ slow` route: **ship live** (string reference is safe).
  - `process_permanent_deletions → slow` route: **ship COMMENTED** with a note that no plan creates this task. Do NOT route a task that does not and will not exist.
  - This satisfies "2 starter routes" (one live, one commented example).

---

## Active feature conflicts

Two sibling features are concurrently **Active** in `MASTER_PLAN.md`: **rhitoric-auth-core** and **rhitoric-notification-system**. Ownership is disjoint EXCEPT one shared file that must be **serialized** across features:

- **`pyproject.toml`** — this plan's **006** adds `kombu`; **rhitoric-auth-core/001** adds `cryptography`. Disjoint lines (both append to `[project].dependencies`), but the SAME file — the orchestrator MUST serialize the two writers (either order; the second rebases onto the untouched region). `rhitoric-auth-core/MASTER_TASKS.md` documents the same lock.
  - **RESOLVED (2026-07-03):** `rhitoric-auth-core` has COMPLETED and been archived — `cryptography>=45.0.7` is already in `pyproject.toml`. There was no live co-writer when **006** ran; it appended `kombu>=5.5.4` onto the untouched region with no serialization needed. Lock is now moot.

Otherwise disjoint: this plan owns `utils/{celery_helpers.py,tasks.py,admin/*,models/*}`, `config/settings/celery.py`, `config/django/test.py`, `config/spectacular_pydantic.py`, `static/exp_app/*`; auth-core owns `accounts/*`, `config/settings/{restframework,config}.py`, `config/django/production.py`, WS/cookie/JWT files; notification-system owns the new `notification_system/` app + its wiring. The only other adjacency is soft (Phase 6.3 throttle-key override + Phase 10 celery task-name routing reference auth-core scopes/tasks by string — non-blocking). **No other hard conflicts.**

---

## Validation gate (Definition of Done)

```bash
# 1. Full suite green (coverage floor 75%)
uv run pytest --ds=config.django.test

# 2. Phase 6.1 — celery helpers import
uv run python -c "from utils.celery_helpers import safe_task_delay, safe_task_delay_with_countdown, safe_send_task; print('6.1 OK')"

# 3. Phase 6.2 — health-check command runs with empty SERVICES (exit 0)
uv run python manage.py check_external_apis --settings=config.django.test

# 4. Phase 7 — pydantic bridge smoke test
uv run python -c "
from config.spectacular_pydantic import pydantic_schema, pydantic_array_schema, pydantic_one_of_schema, as_openapi_response
from pydantic import BaseModel
class Dummy(BaseModel):
    name: str
    value: int
print(pydantic_schema(Dummy)); print(pydantic_array_schema(Dummy)); print('7 OK')
"

# 5. Phase 8 — keep-warm task import
uv run python -c "from utils.tasks import keep_warm; print('8 OK')"

# 6. Phase 9 — admin mixin import + no console.log shipped
uv run python -c "from utils.admin.mixins import CopyableFieldMixin; print('9 OK')"
! grep -q "console.log" utils/static/utils/admin/js/copy-field.js && echo "9 no console.log OK"

# 7. Phase 10 — celery config imports (kombu Queue) + settings load
uv run python -c "
import django, os
os.environ.setdefault('DJANGO_SETTINGS_MODULE','config.django.test'); django.setup()
from django.conf import settings
assert settings.CELERY_TASK_DEFAULT_QUEUE == 'default'
assert {q.name for q in settings.CELERY_TASK_QUEUES} == {'realtime','default','slow'}
assert settings.CELERY_TASK_ROUTES['accounts.tasks.flush_expired_jwt_tokens']['queue'] == 'slow'
assert 'keep-warm' in settings.CELERY_BEAT_SCHEDULE
print('10 OK')
"

# 8. Phase 11 — model mixins import
uv run python -c "from utils.models import SoftDeleteModel, SoftDeleteManager, SoftDeleteQuerySet, BooleanChoices; print('11 OK')"

# 9. OpenAPI still validates (7.1 touches spectacular helpers)
uv run python manage.py spectacular --validate --fail-on-warn --settings=config.django.test

# 10. App scaffold files are valid Python
uv run python -m py_compile static/exp_app/authentication.py static/exp_app/permissions/__init__.py && echo "scaffold OK"
```
