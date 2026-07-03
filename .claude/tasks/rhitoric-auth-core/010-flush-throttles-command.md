# 010 — Flush-throttles management command (4.3)

**Status:** [PENDING]
**Phase:** 4
**Group:** thr
**Risk:** LOW
**Effort:** 20m
**Dependencies:** none

## Goal
Add `python manage.py flush_throttles` to clear DRF throttle counters from the cache.

## Context
`utils/management/commands/` already exists. Redis-aware: delete only `*throttle_*` keys when the backend supports pattern deletion; otherwise fall back to `cache.clear()`.

## Existing pattern to follow
`SRC:utils/management/commands/flush_throttles.py`. Match the command style of the sibling commands in `utils/management/commands/`.

## Files Owned
- `utils/management/commands/flush_throttles.py` (C)
- `utils/tests/test_flush_throttles.py` (C)

## Implementation Steps

### Step 1 — command
`handle()`:
- Try Redis pattern delete: access the underlying client (`cache.client.get_client()` for `django-redis`) and `delete` keys matching `*throttle_*`; report the count.
- On any `AttributeError`/`NotImplementedError`/import failure, fall back to `cache.clear()` and note the fallback in output.
- Wrap the Redis path in try/except; never crash on a non-Redis backend (LocMem in tests).

## Tests (`utils/tests/test_flush_throttles.py`)
- With LocMemCache (test settings): seed a throttle-like cache key, run `call_command("flush_throttles")`, assert it completes and (fallback path) the cache is cleared. Assert no exception on the non-Redis backend.

## Validation
```bash
uv run pytest utils/tests/test_flush_throttles.py -x -v --ds=config.django.test
```

## Acceptance Criteria
- [ ] Command clears throttle counters; graceful fallback on non-Redis backends.
- [ ] Tests pass.
