# 002 — Models (4 tables) + factories + model tests

**Status:** [PENDING]
**Phase:** 1
**Group:** A
**Risk:** MEDIUM
**Effort:** 45m
**Dependencies:** 001

## Goal
Create the four notification models with their indexes and constraints, the app-scoped test fixtures/factories, and model tests. Migration generation is a separate subtask (006).

## Context
These tables are the storage layer for the whole feature. All services, selectors, serializers, and tasks depend on them. `Notification` inherits `TimeStampedModel` (already in `utils/models/_timestamp.py`, exposes `created`/`modified`).

## Existing pattern to follow
- `utils/models/_timestamp.py::TimeStampedModel` — base class to inherit.
- Any existing app's `models/__init__.py` re-export pattern.
- Factory-boy usage: existing `*/tests/factories/` in this repo; SRC `SRC:notification_system/tests/factories.py`.
- SRC references: `SRC:notification_system/models/{_notification,_notification_preference,_category_preference,_delivery_log}.py`.

## Files Owned
- `notification_system/models/__init__.py`  (re-export all 4 models)
- `notification_system/models/_notification.py`
- `notification_system/models/_notification_preference.py`
- `notification_system/models/_category_preference.py`
- `notification_system/models/_delivery_log.py`
- `notification_system/tests/__init__.py`
- `notification_system/tests/conftest.py`  (app-scoped fixtures: user, notification factories, `reset_registry`)
- `notification_system/tests/factories.py`
- `notification_system/tests/models/__init__.py`
- `notification_system/tests/models/test_notification.py`
- `notification_system/tests/models/test_preferences.py`

## Implementation Steps

### Step 1 — `_notification.py`
`Notification(TimeStampedModel)` with fields (plan §12.2a): `user` (FK → `settings.AUTH_USER_MODEL`, `related_name="notifications"`), `notification_type` (CharField 100), `title`, `message` (TextField), `payload` (JSONField default dict), `action_url`, `action_text`, `priority` (IntegerField, choices from `Priority`, default `Priority.NORMAL`), `read` (bool default False), `read_at` (DateTimeField null), `deleted_at` (DateTimeField null — soft delete), `expires_at` (DateTimeField null), `actor_id` (IntegerField null), `content_type` (CharField null), `object_id` (IntegerField null), `email_failed` (bool default False), `dedupe_key` (CharField null).
- **Indexes (5):** `(user, read, deleted_at)`, `(user, notification_type)`, `(user, created)`, `(notification_type,)`, `(expires_at,)`.
- **Constraint:** `UniqueConstraint(fields=["user", "dedupe_key"], condition=Q(dedupe_key__isnull=False), name="unique_user_dedupe_key")`.
- Implement `__str__`.

### Step 2 — `_notification_preference.py`
`UserNotificationPreference`: `user` (FK, `related_name="notification_preferences"`), `notification_type` (CharField 100), `in_app` (bool default True), `email` (bool default False). `Meta.unique_together = ("user", "notification_type")`. `__str__`.

### Step 3 — `_category_preference.py`
`UserNotificationCategoryPreference`: `user` (FK, `related_name="notification_category_preferences"`), `category` (CharField 50), `enabled` (bool default True). Constraint `UniqueConstraint(fields=["user", "category"], name="unique_user_category_pref")`. `__str__`.

### Step 4 — `_delivery_log.py`
`NotificationDeliveryLog`: `notification` (FK, `related_name="delivery_logs"`), `channel` (CharField, choices from `Channel`), `status` (CharField, choices from `DeliveryStatus`), `created_at` (auto_now_add), `sent_at` (DateTimeField null), `error_message` (TextField blank), `metadata` (JSONField default dict). `__str__`.

### Step 5 — `models/__init__.py`
Re-export `Notification`, `UserNotificationPreference`, `UserNotificationCategoryPreference`, `NotificationDeliveryLog`.

### Step 6 — factories + conftest
`tests/factories.py`: factory-boy factories for a user (reuse an existing accounts user factory if present — check `accounts/tests/factories/`) and for each model. `tests/conftest.py`: fixtures exposing a `user` and a `notification_factory`. Keep generic — no domain types (use a placeholder `notification_type="test.event"`).

Also define the shared **`reset_registry`** fixture here (it lives in the app conftest so subtasks 007/013/014 can all use it — a module-local fixture in 003 would be invisible to them). Use a LAZY import inside the fixture body to avoid import-time coupling with the concurrently-built registry (003):
```python
@pytest.fixture
def reset_registry():
    from notification_system.registry import NotificationTypeRegistry, CATEGORIES
    saved_types = dict(NotificationTypeRegistry._types)
    saved_categories = dict(CATEGORIES)
    NotificationTypeRegistry._types.clear()
    CATEGORIES.clear()
    yield NotificationTypeRegistry
    NotificationTypeRegistry._types.clear()
    NotificationTypeRegistry._types.update(saved_types)
    CATEGORIES.clear()
    CATEGORIES.update(saved_categories)
```
(Match the actual class-level attribute name used by 003 — verify it is `_types`.)

### Step 7 — model tests
`test_notification.py`: field defaults, `__str__`, the dedupe `UniqueConstraint` (creating two rows with same `(user, dedupe_key)` raises `IntegrityError`; two with `dedupe_key=None` do NOT), soft-delete field settable. `test_preferences.py`: `unique_together` on preference, `unique_user_category_pref` constraint, defaults (`in_app=True`, `email=False`, `enabled=True`).

## Tests
Cover: every model `__str__`, all defaults, both unique constraints (positive + negative), the partial dedupe constraint edge (multiple NULLs allowed). Use `@pytest.mark.django_db`. Constraint tests need `transaction.atomic()` wrapping to catch `IntegrityError`.

## Validation
```bash
uv run pytest notification_system/tests/models/ -x -v --no-cov --ds=config.django.test
```
- `--no-cov` is required on this scoped run: `pytest.ini` `addopts` carries `--cov=... --cov-fail-under=80`, so a scoped subset would compute coverage over the whole project and false-fail; coverage is enforced only in the full-suite gate (014).
- This repo runs `--reuse-db --nomigrations` (`pytest.ini`), which builds tables from current model state and caches the DB. The FIRST run after these new models are added must rebuild that cache — append `--create-db` once: `uv run pytest notification_system/tests/models/ --create-db --no-cov --ds=config.django.test`. (Under `--nomigrations`, migration 006 is not needed for DB tests — tables come from model state — but 006 is still required for the `makemigrations --check` gate.)

## Acceptance Criteria
- [ ] All 4 models importable from `notification_system.models`.
- [ ] `Notification` has exactly the 5 indexes and the partial unique dedupe constraint.
- [ ] Category preference has `unique_user_category_pref`; type preference has `unique_together`.
- [ ] Every model implements `__str__`.
- [ ] Factories create valid rows with generic (non-domain) type strings.
- [ ] No game/AI/elearning/club field or import anywhere.
