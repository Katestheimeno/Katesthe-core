# 003 — Notification type registry (EMPTY)

**Status:** [PENDING]
**Phase:** 1
**Group:** A
**Risk:** LOW
**Effort:** 25m
**Dependencies:** 001

## Goal
Create the top-level `registry.py` with `NotificationTypeConfig`, an EMPTY `CATEGORIES = {}`, and `NotificationTypeRegistry` — shipping zero registered types.

## Context
The registry is the source of truth for type metadata (priority, defaults, critical, visible_to_roles, category). Selectors import it directly (top-level, to avoid a selector→service boundary crossing). The services shim (`services/_registry.py`, owned by 007) re-exports from here.

## Existing pattern to follow
- SRC reference: `SRC:notification_system/registry.py`. **This is the file to strip most aggressively.**

## Files Owned
- `notification_system/registry.py`
- `notification_system/tests/test_registry.py`

## Implementation Steps

### Step 1 — copy structure, strip domain content
From `SRC:notification_system/registry.py` keep:
- `NotificationTypeConfig` dataclass: `key`, `priority` (default `Priority.NORMAL`), `default_in_app=True`, `default_email=False`, `critical=False`, `visible_to_roles: Optional[List[str]]=None`, `category`, `label`.
  - **STRIP the `category` default of `"elearning"`.** Use a neutral default such as `"general"` (or make it required). Do NOT default to a domain category.
- `NotificationTypeRegistry` classmethods: `register(...)`, `get(key)`, `get_or_default(key)`, `all_keys()`, `get_types_by_category()`.
  - In `register(...)`, the SRC derives `category` from the type-key prefix with hardcoded `elearning`/`clubs` mappings — **STRIP that domain mapping.** Fallback should be neutral (e.g. use the prefix as-is, or `"general"` when no `.` present). Label derivation from the key is fine to keep.

### Step 2 — empty CATEGORIES
```python
CATEGORIES: Dict[str, str] = {}
```
(SRC ships 4 entries: `elearning`, `clubs`, `game`, `tickets` — remove all.)

### Step 3 — remove `register_core_types()`
If SRC defines `register_core_types()` and the 35 type registrations in this file (or the shim), DELETE them entirely. The registry ships with `_types = {}`.

### Step 4 — docstring example
Add the docstring block from plan §12.3 showing how a project registers its own types + updates `CATEGORIES` in its `AppConfig.ready()`.

### Step 5 — `get_or_default`
Ensure `get_or_default(key)` returns a safe fallback `NotificationTypeConfig` for unknown keys (used by dispatch for unregistered types) — with `in_app=True`, `email=False`, neutral category.

## Tests
`test_registry.py`:
- `CATEGORIES == {}` and `NotificationTypeRegistry.all_keys() == []` on a fresh import.
- `register()` then `get()` round-trips; `all_keys()` reflects it.
- `get()` on unknown key returns `None`; `get_or_default()` returns a config with sane defaults.
- `get_types_by_category()` groups registered types correctly.
- **Isolation:** clear the class-level `_types` (and `CATEGORIES`) in teardown so tests don't leak registry state. Define a **file-local** `reset_registry` fixture INSIDE `test_registry.py` (save/clear/restore `_types` + `CATEGORIES`) — do NOT rely on the app-conftest fixture (owned by 002, which runs concurrently in Group A, so it may not exist when 003's scoped gate runs). A test-file-local fixture safely shadows the conftest one once both are present; later phases (007/013/014) use the conftest copy.

## Validation
```bash
uv run pytest notification_system/tests/test_registry.py -x -v --no-cov --ds=config.django.test
```

## Acceptance Criteria
- [ ] `CATEGORIES == {}`.
- [ ] Zero registered types on import; `all_keys() == []`.
- [ ] No `register_core_types()` and no game/AI/elearning/club/tickets type registrations.
- [ ] `NotificationTypeConfig.category` default is neutral (not `"elearning"`).
- [ ] `register`/`get`/`get_or_default`/`all_keys`/`get_types_by_category` all covered by tests with registry-state isolation.
