# 009 — Serializers (notification + preferences)

**Status:** [PENDING]
**Phase:** 2
**Group:** B
**Risk:** LOW
**Effort:** 30m
**Dependencies:** 002

## Goal
Create the DRF serializers for notification list/detail and preference read/update shapes.

## Context
Standard DRF `ModelSerializer`s and plain `Serializer`s — no domain content. Consumed by the controllers (012).

## Existing pattern to follow
- SRC references: `SRC:notification_system/serializers/{_notification.py,_preference.py,_category_preference.py}`.
- Existing DST serializer style under `accounts/serializers/`.

## Files Owned
- `notification_system/serializers/__init__.py`
- `notification_system/serializers/_notification.py`
- `notification_system/serializers/_preference.py`
- `notification_system/serializers/_category_preference.py`
- `notification_system/tests/serializers/__init__.py`
- `notification_system/tests/serializers/test_serializers.py`

## Implementation Steps

### Step 1 — `_notification.py`
`NotificationListSerializer` (compact fields for list rows) and `NotificationDetailSerializer` (full detail). Copy field sets from SRC. Expose only client-safe fields (no internal soft-delete plumbing unless SRC intentionally does).

### Step 2 — `_preference.py`
`UserNotificationPreferenceSerializer` (ModelSerializer over `UserNotificationPreference`) and `NotificationPreferencesGroupedSerializer` (the grouped-by-category read shape produced by `get_grouped_preferences`). Copy from SRC.

### Step 3 — `_category_preference.py`
`NotificationPreferencesUpdateSerializer` (input for the PUT update endpoint: category + type preference lists) and `NotificationTypePreferenceSerializer`. Copy from SRC. Keep validation (`validate_*`) methods.

### Step 4 — `serializers/__init__.py`
Re-export: `NotificationListSerializer`, `NotificationDetailSerializer`, `UserNotificationPreferenceSerializer`, `NotificationPreferencesGroupedSerializer`, `NotificationPreferencesUpdateSerializer`, `NotificationTypePreferenceSerializer`.

## Tests
`test_serializers.py`:
- `NotificationListSerializer` / `NotificationDetailSerializer` serialize a factory `Notification` with expected keys; no sensitive/internal fields leak.
- `NotificationPreferencesUpdateSerializer` validates a well-formed payload and rejects malformed input (every `validate_*` branch covered).
- Grouped serializer round-trips the grouped structure.

## Validation
```bash
uv run pytest notification_system/tests/serializers/ -x -v --no-cov --ds=config.django.test
```

## Acceptance Criteria
- [ ] All six serializers importable from `notification_system.serializers`.
- [ ] List vs detail field sets are distinct and client-safe.
- [ ] Update serializer validation covered (happy + failure).
- [ ] No domain-specific fields.
