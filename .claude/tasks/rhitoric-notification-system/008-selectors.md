# 008 — Selectors (notification, preference, user-roles)

**Status:** [PENDING]
**Phase:** 2
**Group:** B
**Risk:** MEDIUM
**Effort:** 45m
**Dependencies:** 002, 003

## Goal
Create the read layer: notification list/count/detail + role-visibility, grouped preferences, and the cached role resolver.

## Context
All reads for the feature live here. Selectors are registry-driven and scope to the user for IDOR safety. They import the registry from the top-level `notification_system.registry` (not the service shim) to respect the selector→service boundary.

## Existing pattern to follow
- SRC references: `SRC:notification_system/selectors/{_notification.py,_preference.py,_user_roles.py}`.
- N+1 discipline: `select_related`/`prefetch_related` inside each selector (`.claude/rules/layers.md` §3).

## Files Owned
- `notification_system/selectors/__init__.py`
- `notification_system/selectors/_notification.py`
- `notification_system/selectors/_preference.py`
- `notification_system/selectors/_user_roles.py`
- `notification_system/tests/selectors/__init__.py`
- `notification_system/tests/selectors/test_notification.py`
- `notification_system/tests/selectors/test_preference.py`

## Implementation Steps

### Step 1 — `_notification.py`
Copy SRC. Functions: `get_user_notifications_queryset(user_id, *, notification_type, read, retention_days, user_for_roles)`, `get_unread_count(user_id, *, user_for_roles)`, `get_notification_for_user(pk, user_id)`, `get_visible_notification_type_keys(user)`.
- `_retention_cutoff()` uses `NOTIFICATION_RETENTION_DAYS` (default 90); excludes older + soft-deleted rows.
- `_visible_type_keys_for_user()` filters by `visible_to_roles` — **fail-closed**: an empty registry yields an empty visible set.
- All querysets scoped to `user_id` (IDOR).

### Step 2 — `_preference.py`
Copy SRC. Functions: `get_user_preferences(user)`, `is_category_enabled_for_user(user_id, category)`, `get_effective_preference(user, type_key)`, `get_grouped_preferences(user)` — the last returns all types organized by category with effective `(in_app, email)` merging per-type overrides + registry defaults, ready for a preferences UI.

### Step 3 — `_user_roles.py`
Copy SRC. `get_user_roles(user)` resolves via `import_string(settings.NOTIFICATION_GET_USER_ROLES)` and caches per-user in Django cache for 60s (key includes user id). Guards unauthenticated/None.

### Step 4 — `selectors/__init__.py`
Re-export the functions the controllers import: `get_user_notifications_queryset`, `get_unread_count`, `get_notification_for_user`, `get_visible_notification_type_keys`, `get_user_preferences`, `is_category_enabled_for_user`, `get_effective_preference`, `get_grouped_preferences`, `get_user_roles`.

## Tests
- `test_notification.py`: list scoped to user (A cannot see B); `read` filter; `notification_type` filter; retention cutoff excludes old + soft-deleted; unread count matches; **empty registry ⇒ `get_visible_notification_type_keys` returns empty set** (fail-closed); with a registered visible type + matching user role it becomes visible. N+1 sanity via `django_assert_num_queries` on the list path.
- `test_preference.py`: `get_grouped_preferences` merges defaults + overrides; `is_category_enabled_for_user` default True when no row; `get_user_roles` caches (second call does not re-invoke the adapter — patch + assert call count). Use the `reset_registry` fixture.

## Validation
```bash
uv run pytest notification_system/tests/selectors/ -x -v --no-cov --ds=config.django.test
```

## Acceptance Criteria
- [ ] All selectors scoped to the user; no cross-user leakage.
- [ ] Retention filtering + soft-delete exclusion correct.
- [ ] Role visibility fail-closed on empty registry.
- [ ] `get_user_roles` caches for ~60s.
- [ ] Selectors import registry from `notification_system.registry` (not the service shim); no writes; no service calls.
