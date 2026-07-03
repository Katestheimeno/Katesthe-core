# 007 — Services layer (dispatch engine, actions, preferences, broadcast)

**Status:** [PENDING]
**Phase:** 2
**Group:** B2 (Phase 2, after B1 — services sit above the layers they import)
**Risk:** HIGH
**Effort:** 60m
**Dependencies:** 002, 003, 004, 005, 006, 008 (selector `is_category_enabled_for_user` imported by dispatch), 011 (email task imported by dispatch's enqueue path)

## Goal
Create the full services layer in one subtask (the `services/__init__.py` re-export forces all service modules to share an owner): the registry shim, the core `dispatch()` engine, action services, preference services, and the broadcast service.

## Context
`dispatch()` is the single entry point for creating + delivering a notification. It is fully generic — no domain logic. It coordinates registry lookup, dedupe, atomic creation, delivery logging, preference checks, WebSocket delivery, and email enqueue.

## Existing pattern to follow
- SRC references: `SRC:notification_system/services/{__init__.py,_registry.py,_dispatch.py,_actions.py,_preferences.py,_broadcast.py}`.
- Transaction discipline: `transaction.atomic()` + `transaction.on_commit(...)` for the email enqueue (per `.claude/rules/layers.md` §6).

## Files Owned
- `notification_system/services/__init__.py`
- `notification_system/services/_registry.py`
- `notification_system/services/_dispatch.py`
- `notification_system/services/_actions.py`
- `notification_system/services/_preferences.py`
- `notification_system/services/_broadcast.py`
- `notification_system/tests/services/__init__.py`
- `notification_system/tests/services/test_dispatch.py`
- `notification_system/tests/services/test_actions.py`
- `notification_system/tests/services/test_preferences.py`

## Implementation Steps

### Step 1 — `_registry.py` shim
Backward-compat re-export from the top-level `notification_system.registry`:
```python
from notification_system.registry import (
    NotificationTypeRegistry, NotificationTypeConfig, CATEGORIES,
)
```
**STRIP `register_core_types`** — do NOT re-export or define it (the SRC `services/__init__.py` re-exports it; remove from the shim and from `services/__init__.py`).

### Step 2 — `_dispatch.py`
Copy `SRC:notification_system/services/_dispatch.py`. Behavior (plan §12.5), in order:
1. Resolve user via `get_user_model()` (raise/return early if not found).
2. Call the pluggable `should_skip_notification_for_user()` (resolved via `import_string(settings.NOTIFICATION_SHOULD_SKIP_FOR_USER)`); return `None` if it returns True.
3. `registry.get_or_default(notification_type)`.
4. Dedupe: if `dedupe_key` given, check for an existing `Notification` within `NOTIFICATION_DEDUPE_WINDOW_MINUTES` (default 5); return `None` if duplicate. Handle the `IntegrityError` race from the partial unique constraint gracefully.
5. `transaction.atomic()`: `_serialize_payload_for_storage(payload)`, create `Notification`.
6. Create `NotificationDeliveryLog` for IN_APP.
7. Check category preference (enabled?) + type preference (`in_app?`, `email?`) via selectors.
8. If in_app: `send_notification_to_user(user_id, notification)` (fire-and-forget, logged).
9. If email: enqueue `send_notification_email_task` via `transaction.on_commit`. Import the task lazily inside the function to avoid an import cycle with `tasks/_email.py`.
10. Return the `Notification` (or `None`).
- Keep `NotificationService` class if SRC exposes one; `services/__init__.py` re-exports both `NotificationService` and `dispatch`.
- Verify the import path for `send_notification_to_user` is `notification_system.utils`.

**STRIP the `utils.celery_helpers` dependency (CRITICAL).** `SRC:_dispatch.py` enqueues email via `from utils.celery_helpers import safe_task_delay; safe_task_delay(send_notification_email_task, nid)`. `utils/celery_helpers.py` does NOT exist in DST (it is owned by the separate `rhitoric-utilities` feature and may not be present). Do NOT copy that import. Replace the enqueue with a DST-native, commit-safe call:
```python
transaction.on_commit(lambda: send_notification_email_task.delay(notification.id))
```
(Same treatment as stripping `register_core_types` — a documented deviation from SRC.)

### Step 3 — `_actions.py`
Copy `mark_notification_read(user, pk)`, `mark_all_notifications_read(user)`, `soft_delete_notification(user, pk)`. All scoped to `user` (IDOR-safe: filter `user=user` before mutate). Copy as-is.

### Step 4 — `_preferences.py`
Copy `update_notification_preferences(user, category_preferences, type_preferences)` (bulk upsert via `bulk_create(update_conflicts=True)`, validated against registered categories/types) and `bootstrap_notification_preferences(user)` (creates registry-default prefs, idempotent via `ignore_conflicts=True`). Registry-driven — with an empty registry, bootstrap creates nothing.

### Step 5 — `_broadcast.py`
Copy `broadcast_notifications(...)` — loops user IDs, calls `dispatch()` per user. Copy as-is.

### Step 6 — `services/__init__.py`
Re-export: `NotificationService`, `dispatch`, `NotificationTypeRegistry`, `NotificationTypeConfig`, `mark_notification_read`, `mark_all_notifications_read`, `soft_delete_notification`, `update_notification_preferences`, `bootstrap_notification_preferences`, `broadcast_notifications`. **Do NOT re-export `register_core_types`.**

## Tests
- `test_dispatch.py`: happy path creates a `Notification` + IN_APP delivery log; `should_skip` returning True → `None`; unknown type uses `get_or_default`; dedupe within window → second call returns `None` (mock/patch time or use `freezegun`); email preference True → `send_notification_email_task.delay` enqueued on commit; in_app True → `send_notification_to_user` called (mock it); user-not-found path. Mock the WS util and the Celery task — do NOT hit real channels/broker.
  - **Patch the preference selector.** `dispatch()` imports `is_category_enabled_for_user` from `notification_system.selectors._preference` (subtask 008 — a hard dependency; 007 runs in Group B2 after 008/011 exist, so the import resolves). For deterministic unit tests, `patch("notification_system.services._dispatch.is_category_enabled_for_user", return_value=True)` (and the type-preference lookup). The real selector is exercised end-to-end in subtask 014.
  - **On-commit assertions need capture.** pytest-django's default `django_db` is non-transactional, so `transaction.on_commit` callbacks never fire on their own. Wrap the email-enqueue assertion in `django_capture_on_commit_callbacks(execute=True)` and then assert `send_notification_email_task.delay` was called.
- `test_actions.py`: mark read sets `read`/`read_at`; mark_all_read scoped to user (user A cannot affect user B — IDOR); soft delete sets `deleted_at`; acting on another user's pk is a no-op/None.
- `test_preferences.py`: `bootstrap_notification_preferences` with empty registry creates nothing; with a registered type creates the default prefs and is idempotent; `update_notification_preferences` upserts and rejects/ignores unregistered categories/types. Use the `reset_registry` fixture (defined in `notification_system/tests/conftest.py`, owned by 002) for isolation.

## Validation
```bash
uv run pytest notification_system/tests/services/ -x -v --no-cov --ds=config.django.test
```

## Acceptance Criteria
- [ ] `dispatch()` executes the 10-step pipeline; returns `Notification` or `None`.
- [ ] Dedupe honored within `NOTIFICATION_DEDUPE_WINDOW_MINUTES`; race `IntegrityError` handled.
- [ ] Email enqueued via `transaction.on_commit`, never from `save()`.
- [ ] Action + preference services are user-scoped (IDOR-safe).
- [ ] No `register_core_types` anywhere; no domain logic.
- [ ] WS util + Celery task mocked in tests; no external calls.
