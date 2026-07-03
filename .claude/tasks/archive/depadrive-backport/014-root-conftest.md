# 014 — Root conftest.py

**Status:** [PENDING]
**Phase:** 2
**Group:** A (concurrent with 010–013, 015, 016)
**Risk:** MEDIUM
**Effort:** 25m
**Dependencies:** Phase 1 complete

## Goal
Add a project-root `conftest.py` that ensures Django is configured before plugins load, exposes the accounts fixtures project-wide, and clears the Django cache around every test (prevents throttle-counter bleed).

## Context
Phase-2 throttling tests (010) rely on cache isolation. A root conftest centralizes setup so any app's tests can use the shared fixtures. The existing `accounts/tests/conftest.py` already calls `django.setup()` and defines fixtures (`api_client`, `user`, `authenticated_client`, tokens, etc.).

## SRC reference to adapt from
`SRC:conftest.py` (root) — sets Django settings before plugins, registers the accounts fixtures plugin, autouse cache-clear. **Strip** the spatial/PostGIS skip logic (`@pytest.mark.spatial`) — not applicable.

## Files Owned
- `conftest.py` (C — project root)

> Do NOT modify `accounts/tests/conftest.py`; reference it as a plugin. `pytest.ini` already sets `DJANGO_SETTINGS_MODULE = config.django.test`.

## Implementation Steps

### Step 1 — Django bootstrap (guarded)
```python
import os
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.django.test")
import django
django.setup()
```
Keep this idempotent — `accounts/tests/conftest.py` also calls `django.setup()`; calling twice is safe.

### Step 2 — expose accounts fixtures project-wide
```python
pytest_plugins = ["accounts.tests.conftest"]
```
This makes `api_client`, `user`, `authenticated_client`, `superuser`, token fixtures, etc. available to `config/tests`, `utils/tests`, and future apps without re-import.

### Step 3 — cache-clear autouse fixture
```python
import pytest
from django.core.cache import cache

@pytest.fixture(autouse=True)
def clear_cache_between_tests():
    cache.clear()
    yield
    cache.clear()
```

## Tests
No dedicated test file (a conftest is validated by the suite using it). Verify by:
- Running a `config/tests` or `utils/tests` test that consumes a fixture defined only in `accounts/tests/conftest.py` (e.g. `api_client`) — it should resolve via the plugin.
- Confirming throttle tests (010) pass deterministically when the full suite runs (no counter bleed).

## Validation
```bash
uv run pytest --ds=config.django.test -q
# Confirm fixtures are visible outside accounts:
uv run pytest utils/tests -q --ds=config.django.test
```

## Acceptance Criteria
- [ ] Root `conftest.py` bootstraps Django before plugins load (no `AppRegistryNotReady`).
- [ ] `accounts.tests.conftest` registered as a plugin; its fixtures usable project-wide.
- [ ] Autouse cache-clear runs before and after each test.
- [ ] Full suite passes; no double-`django.setup()` breakage.
