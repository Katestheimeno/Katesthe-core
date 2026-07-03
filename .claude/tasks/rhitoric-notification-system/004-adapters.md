# 004 — Pluggable adapters (neutral defaults)

**Status:** [PENDING]
**Phase:** 1
**Group:** A
**Risk:** LOW
**Effort:** 20m
**Dependencies:** 001

## Goal
Create `adapters.py` with the two default pluggable functions, stripped of all Rhitoric domain logic.

## Context
Both adapters are resolved at runtime via `import_string()` from the `NOTIFICATION_SHOULD_SKIP_FOR_USER` / `NOTIFICATION_GET_USER_ROLES` settings (already added in 001). Projects override them by pointing the setting to their own function — zero coupling.

## Existing pattern to follow
- SRC reference: `SRC:notification_system/adapters.py` (contains the domain logic to remove).

## Files Owned
- `notification_system/adapters.py`
- `notification_system/tests/test_adapters.py`

## Implementation Steps

### Step 1 — `should_skip_notification_for_user`
STRIP the `_AI_NOTIFICATION_TYPES` frozenset and the `from elearning.selectors.ai import get_user_ai_preference` block. Default implementation:
```python
def should_skip_notification_for_user(user_id: int, notification_type: str) -> bool:
    """Return True to skip creating this notification for the user.

    Default: never skip. Override via the NOTIFICATION_SHOULD_SKIP_FOR_USER
    setting (dotted path) to add project-specific opt-out logic.
    """
    return False
```

### Step 2 — `get_user_roles`
STRIP the `from accounts.models import ClubMembership` import and the club-membership query. Default implementation (plan §12.4):
```python
def get_user_roles(user) -> list:
    """Return role identifiers for visible_to_roles filtering.

    Default: Django group names only. Override via the NOTIFICATION_GET_USER_ROLES
    setting to add project-specific role sources (staff flag, memberships, etc.).
    """
    if not user or not user.is_authenticated:
        return []
    return list(user.groups.values_list("name", flat=True))
```
Keep the `get_user_model()` import only if actually used; otherwise drop it.

## Tests
`test_adapters.py`:
- `should_skip_notification_for_user(uid, "anything")` returns `False`.
- `get_user_roles(None)` → `[]`; unauthenticated user → `[]`.
- authenticated user with two groups → both group names returned.
- No import of `elearning` or `accounts.models.ClubMembership` (grep-assert or simply ensure the module imports without those apps).

## Validation
```bash
uv run pytest notification_system/tests/test_adapters.py -x -v --no-cov --ds=config.django.test
```

## Acceptance Criteria
- [ ] `should_skip_notification_for_user` always returns `False`.
- [ ] `get_user_roles` returns Django group names only.
- [ ] No `elearning` / `ClubMembership` / AI imports remain.
- [ ] Both docstrings explain the override setting.
