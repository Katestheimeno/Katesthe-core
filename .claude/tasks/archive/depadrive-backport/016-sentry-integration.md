# 016 — Sentry Integration

**Status:** [PENDING]
**Phase:** 2
**Group:** A (concurrent with 010–015)
**Risk:** LOW
**Effort:** 30m
**Dependencies:** Phase 1 complete

## Goal
Add `configure_sentry()` (no-op without `SENTRY_DSN`), call it from production settings, add the two Sentry settings fields, and add `sentry-sdk` as an OPTIONAL dependency (not runtime).

## Context
Error monitoring for production. Must be completely inert in dev/test/CI (no DSN → no init, no import cost required at runtime).

## SRC reference to adapt from
`SRC:config/settings/monitoring.py` — `configure_sentry()` reads `SENTRY_DSN`; if present and `sentry_sdk` importable, `sentry_sdk.init(...)` with Django + Celery integrations, `traces_sample_rate`, `environment`, `release`; returns True/False; safe to call anywhere.

## Files Owned
- `config/settings/monitoring.py` (C)
- `config/tests/test_monitoring.py` (C)
- `config/django/production.py` (M — Phase-2 owner)
- `config/settings/config.py` (M — Phase-2 owner)
- `pyproject.toml` (M — Phase-2 owner)

> `production.py` was edited by 007 (Phase 1); `config.py` will be edited by 017 (Phase 3); `pyproject.toml` by 019 (Phase 3). All different phases — safe.

## Implementation Steps

### Step 1 — `config/settings/monitoring.py`
```python
def configure_sentry() -> bool:
    from config.settings.config import settings
    dsn = getattr(settings, "SENTRY_DSN", "") or ""
    if not dsn:
        return False
    try:
        import sentry_sdk
        from sentry_sdk.integrations.django import DjangoIntegration
        from sentry_sdk.integrations.celery import CeleryIntegration
    except ImportError:
        return False
    sentry_sdk.init(
        dsn=dsn,
        integrations=[DjangoIntegration(), CeleryIntegration()],
        traces_sample_rate=getattr(settings, "SENTRY_TRACES_SAMPLE_RATE", 0.1),
        environment=__import__("os").getenv("DJANGO_ENV", "production"),
        release=getattr(settings.project, "VERSION", None) if hasattr(settings, "project") else None,
        send_default_pii=False,
    )
    return True
```
Keep it defensive: never raise on missing DSN or missing sdk.

### Step 2 — `config/django/production.py`
Append (after 007's hardening block):
```python
from config.settings.monitoring import configure_sentry
configure_sentry()
```

### Step 3 — `config/settings/config.py`
Add to `MainSettings` (near the other direct env fields):
```python
SENTRY_DSN: str = Field(default="", description="Sentry DSN; empty disables Sentry")
SENTRY_TRACES_SAMPLE_RATE: float = Field(default=0.1, description="Sentry traces sample rate")
```
(`Field` is already imported in that file.)

### Step 4 — `pyproject.toml`
Add `sentry-sdk[django,celery]` as an OPTIONAL extra, NOT a runtime dependency. Create/extend `[project.optional-dependencies]`:
```toml
[project.optional-dependencies]
production = ["sentry-sdk[django,celery]>=2.0.0"]
```
Do NOT add it to `[project].dependencies`.

## Tests (`config/tests/test_monitoring.py`)
- With no `SENTRY_DSN` (default), `configure_sentry()` returns `False` and does not raise.
- Patch `settings.SENTRY_DSN` to a fake value AND patch `sentry_sdk.init` (mock the import) → `configure_sentry()` returns `True` and calls `init` once with `send_default_pii=False`. If `sentry_sdk` is not installed in the test env, assert the ImportError path returns `False` instead.
- `SENTRY_DSN` and `SENTRY_TRACES_SAMPLE_RATE` exist on the settings object with correct defaults.

## Validation
```bash
uv run pytest config/tests/test_monitoring.py -x -v --ds=config.django.test
```

## Acceptance Criteria
- [ ] `configure_sentry()` is a no-op without a DSN and never raises.
- [ ] Production settings call it; `SENTRY_DSN` + `SENTRY_TRACES_SAMPLE_RATE` added to `MainSettings`.
- [ ] `sentry-sdk` is an optional extra, not a runtime dependency.
- [ ] Tests pass.
