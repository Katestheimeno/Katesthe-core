# 006 — Initial migration (0001_initial)

**Status:** [PENDING]
**Phase:** 1b
**Group:** —
**Risk:** MEDIUM
**Effort:** 15m
**Dependencies:** 002

## Goal
Generate the single initial migration for all four `notification_system` tables with their indexes and constraints.

## Context
DST is greenfield for this app, so a fresh `0001_initial` is correct — do NOT copy Rhitoric's incremental migration chain (`0001_add_unique...` → `0004_alter...`); those are historical deltas against an already-existing schema. Generate one clean migration from the final model state.

## Existing pattern to follow
- Standard Django `makemigrations` output. Compare against SRC final schema (SRC models + its 4 migrations collapsed) to confirm the dedupe partial `UniqueConstraint`, the `unique_user_category_pref` constraint, and all 5 `Notification` indexes are present.

## Files Owned
- `notification_system/migrations/__init__.py`
- `notification_system/migrations/0001_initial.py`

## Implementation Steps

### Step 1 — create the migrations package
Add empty `notification_system/migrations/__init__.py`.

### Step 2 — generate
```bash
uv run python manage.py makemigrations notification_system --settings=config.django.test
```

### Step 3 — verify contents
The generated `0001_initial.py` must contain:
- 4 `CreateModel` operations (`Notification`, `UserNotificationPreference`, `UserNotificationCategoryPreference`, `NotificationDeliveryLog`).
- 5 indexes on `Notification`.
- Partial `UniqueConstraint(... condition=Q(dedupe_key__isnull=False) ..., name="unique_user_dedupe_key")`.
- `unique_together` on `UserNotificationPreference` and `UniqueConstraint name="unique_user_category_pref"` on the category preference.

Do not hand-edit beyond what makemigrations produces (unless a deterministic ordering fix is needed).

## Tests
No dedicated test file. The migration is exercised by every DB test in downstream subtasks and by the `--check` gate.

## Validation
```bash
uv run python manage.py makemigrations notification_system --check --dry-run --settings=config.django.test
uv run python manage.py migrate notification_system --settings=config.django.test
```

## Acceptance Criteria
- [ ] Exactly one migration file: `0001_initial.py`.
- [ ] `makemigrations --check --dry-run` reports no changes after generation.
- [ ] All 4 tables, 5 indexes, and 3 constraints present.
- [ ] `migrate` applies cleanly.
