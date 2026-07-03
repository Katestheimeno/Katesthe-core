# 024 — Feature validation gate

**Status:** [PENDING]
**Phase:** 6
**Group:** —
**Risk:** LOW
**Effort:** 20m
**Dependencies:** ALL of 001–023

## Goal
Run the feature-level Definition of Done: full suite (80% floor), OpenAPI validation, all phase smoke tests, and production RS256 enforcement. Add last-mile `.coveragerc` omits only for genuinely untestable glue.

## Context
Final gate for the feature. `.coveragerc` is owned here so any coverage adjustments needed for glue code (ASGI wiring, management-command edge branches, the spectacular extension) are made in one place after seeing the real coverage report — do NOT pre-omit testable modules.

## Files Owned
- `.coveragerc` (M — only if the 80% floor requires omitting untestable glue such as `config/asgi.py`, `accounts/management/*`, `config/spectacular_auth.py`)

## Implementation Steps

### Step 1 — run the gate
```bash
uv run pytest --ds=config.django.test
uv run python manage.py spectacular --validate --fail-on-warn --settings=config.django.test
```

### Step 2 — smoke tests (from MASTER_TASKS §Validation gate)
Run the Phase 1/2/3/5 import smoke commands and the production-enforcement boot check.

### Step 3 — coverage last-mile
If coverage < 80%, first check whether a missing test belongs to a specific subtask (flag it, don't paper over). Only add `.coveragerc` omits for code that is genuinely not unit-testable (e.g. `config/asgi.py` ASGI assembly). Do NOT re-add omits already present.

## Validation
```bash
uv run pytest --ds=config.django.test
uv run python manage.py spectacular --validate --fail-on-warn --settings=config.django.test
```

## Acceptance Criteria
- [ ] Full suite green at ≥80% coverage.
- [ ] OpenAPI validates with `--fail-on-warn`.
- [ ] All phase smoke imports succeed; production boot without `JWT_RSA_PRIVATE_KEY` raises `ImproperlyConfigured`.
- [ ] `MASTER_PLAN.md` status updated on completion.
