# 001 — Bootstrap app package, constants, settings & wiring

**Status:** [PENDING]
**Phase:** 0
**Group:** —
**Risk:** MEDIUM
**Effort:** 25m
**Dependencies:** none

## Goal
Create the `notification_system` app package + `constants.py`, register it in `INSTALLED_APPS`, add its settings module, and add the `NOTIFICATION__NOT_FOUND` error code — so the app is installed, importable, and every downstream subtask can run tests under `--ds=config.django.test`.

## Context
Greenfield app. Nothing depends on WS-auth or models yet. This subtask does the minimal wiring that must land before any model/service work. It deliberately does NOT touch `config/urls.py` (that include requires `notification_system.urls`, created in 012) nor `config/routing.py` (created in 010).

## Existing pattern to follow
- App config style: any existing `*/apps.py` in this repo (e.g. `accounts/apps.py`).
- Settings sub-module + `config/settings/__init__.py` import block (lines ~40–51 already import `apps_middlewares`, `channels`, etc.).
- `errors/catalog.py`: module-level `DOMAIN__ERROR = "DOMAIN__ERROR"` constants mirrored inside `class E:` (starts line 44). `NOTIFICATION__EMAIL_DELIVERY_FAILED` already exists there — follow its exact placement/style.
- SRC reference: `SRC:notification_system/{__init__.py,apps.py,constants.py}`, `SRC:config/settings/notification_system.py`.

## Files Owned
- `notification_system/__init__.py`
- `notification_system/apps.py`
- `notification_system/constants.py`
- `config/settings/notification_system.py`
- `config/settings/__init__.py`  (add one import line only)
- `config/settings/apps_middlewares.py`  (add to `PROJECT_APPS` only)
- `errors/catalog.py`  (add one constant in two places)
- `pytest.ini`  (add the new app to `testpaths` + `--cov`)

## Implementation Steps

### Step 1 — `constants.py`
Copy `SRC:notification_system/constants.py` verbatim. Provides:
- `Priority(IntegerChoices)` — `LOW`, `NORMAL`, `HIGH`, `CRITICAL`, with `MEDIUM = NORMAL` backward-compat alias.
- `Channel(TextChoices)` — `IN_APP`, `EMAIL`.
- `DeliveryStatus(TextChoices)` — `PENDING`, `SENT`, `FAILED`.
No domain content — copy as-is.

### Step 2 — `apps.py`
Copy `SRC:notification_system/apps.py` but STRIP any `register_core_types()` call from `ready()`. Final form per plan §12.17:
```python
from django.apps import AppConfig

class NotificationSystemConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "notification_system"
    verbose_name = "Notification System"

    def ready(self):
        # Projects register their notification types in their own app's ready().
        pass
```

### Step 3 — `notification_system/__init__.py`
Package init. If SRC sets `default_app_config`, omit it (deprecated). Empty file or a short docstring is fine.

### Step 4 — `config/settings/notification_system.py`
Copy the four settings from `SRC:config/settings/notification_system.py`:
```python
NOTIFICATION_RETENTION_DAYS = 90
NOTIFICATION_DEDUPE_WINDOW_MINUTES = 5
NOTIFICATION_GET_USER_ROLES = "notification_system.adapters.get_user_roles"
NOTIFICATION_SHOULD_SKIP_FOR_USER = "notification_system.adapters.should_skip_notification_for_user"
```
Keep the explanatory docstrings/comments (they document the pluggable override contract).

### Step 5 — `config/settings/__init__.py`
Add, alongside the other `from config.settings.* import *` lines (~40–51):
```python
from config.settings.notification_system import *
```

### Step 6 — `config/settings/apps_middlewares.py`
Add `"notification_system",` to the `PROJECT_APPS` list (starts line 79). Do NOT create `config/settings/django.py` — the plan's file inventory says `django.py` but that file does not exist in this repo; `PROJECT_APPS` is the correct target (locked decision #10).

### Step 7 — `errors/catalog.py`
Add, next to the existing `NOTIFICATION__EMAIL_DELIVERY_FAILED` block:
- Module constant: `NOTIFICATION__NOT_FOUND = "NOTIFICATION__NOT_FOUND"`
- Mirror inside `class E:`: `NOTIFICATION__NOT_FOUND = NOTIFICATION__NOT_FOUND`

First VERIFY it is not already present (only `NOTIFICATION__EMAIL_DELIVERY_FAILED` exists as of planning). Add only what is missing.

### Step 8 — `pytest.ini` (CRITICAL — without this the entire new test suite is silently skipped)
The suite runs `uv run pytest --ds=config.django.test` with NO path argument, so it collects only `testpaths`. As of planning, `pytest.ini` `testpaths` (lines ~21-25) lists only `accounts/tests config/tests utils/tests notifications/tests` and `--cov` (lines ~10-17) covers only `accounts,config,utils,notifications`. Make TWO edits together (doing only one skews coverage):
- Add `notification_system/tests` to `testpaths`.
- Add `--cov=notification_system` to the `--cov` list in `addopts`.
Do NOT change the existing `--cov-fail-under` value. (Note: the enforced floor is `--cov-fail-under=80` in this repo, not 75 — the new app's tests must clear it in the final gate.)

## Tests
No dedicated test file for this subtask. Verification is the import/boot check below; the models subtask (002) adds the first real tests.

## Validation
```bash
DJANGO_SETTINGS_MODULE=config.django.test uv run python -c "import notification_system; from notification_system.constants import Priority, Channel, DeliveryStatus; from errors.catalog import NOTIFICATION__NOT_FOUND; print('bootstrap OK')"
uv run python manage.py check --settings=config.django.test
# Confirm the new test path is collectable (0 tests now is fine; proves it is NOT skipped):
uv run pytest notification_system --collect-only --no-cov --ds=config.django.test
```

## Acceptance Criteria
- [ ] `notification_system` appears in `INSTALLED_APPS` (via `PROJECT_APPS`).
- [ ] `Priority.MEDIUM == Priority.NORMAL`.
- [ ] `manage.py check` passes (no `config/urls.py` / `config/routing.py` edits here).
- [ ] `NOTIFICATION__NOT_FOUND` present as both module constant and `E.NOTIFICATION__NOT_FOUND`.
- [ ] `apps.py.ready()` contains NO `register_core_types()` call.
- [ ] `pytest.ini` `testpaths` includes `notification_system/tests` AND `addopts` includes `--cov=notification_system` (both — verified so the gate actually runs and measures the new suite).
- [ ] Existing `notifications` app untouched.
