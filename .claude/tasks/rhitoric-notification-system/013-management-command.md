# 013 — `bootstrap_notification_preferences` management command

**Status:** [PENDING]
**Phase:** 3
**Group:** C
**Risk:** LOW
**Effort:** 30m
**Dependencies:** 003, 006, 007

## Goal
Create the management command that backfills default notification preferences for existing users, driven by the registry.

## Context
For users created before the notification system existed, this creates `UserNotificationPreference` + `UserNotificationCategoryPreference` rows with registry defaults. With the EMPTY registry it must exit cleanly with "Nothing to bootstrap."

## Existing pattern to follow
- SRC reference: `SRC:notification_system/management/commands/bootstrap_notification_preferences.py`.
- Reuses `bootstrap_notification_preferences(user)` service (007) and/or batch `bulk_create(ignore_conflicts=True)` per SRC.

## Files Owned
- `notification_system/management/__init__.py`
- `notification_system/management/commands/__init__.py`
- `notification_system/management/commands/bootstrap_notification_preferences.py`
- `notification_system/tests/management/__init__.py`
- `notification_system/tests/management/test_bootstrap.py`

## Implementation Steps

### Step 1 — command
Copy SRC. Features (plan §12.16):
- `--dry-run` flag (report, no writes).
- `--batch-size` option for large user bases.
- Single query to find users needing preferences; batch-fetch existing prefs; batch `bulk_create(ignore_conflicts=True)` for idempotency.
- If the registry has no types/categories → print "Nothing to bootstrap." and exit 0.
- Registry-driven only — no hardcoded domain types.

### Step 2 — package inits
Empty `management/__init__.py` and `management/commands/__init__.py`.

## Tests
`test_bootstrap.py` (use `django.core.management.call_command`):
- empty registry → outputs "Nothing to bootstrap.", creates zero rows.
- with a registered type/category (via `reset_registry` fixture) + N users → creates the expected preference rows; re-running is idempotent (no duplicates).
- `--dry-run` writes nothing.
- `--batch-size` path exercised (small batch over multiple users).

## Validation
```bash
uv run pytest notification_system/tests/management/ -x -v --no-cov --ds=config.django.test
uv run python manage.py bootstrap_notification_preferences --dry-run --settings=config.django.test
```

## Acceptance Criteria
- [ ] Command runs; `--dry-run` and `--batch-size` supported.
- [ ] Empty registry → "Nothing to bootstrap.", zero writes.
- [ ] Idempotent via `ignore_conflicts=True`.
- [ ] No hardcoded domain types.
