# 008 — CI Workflow (GitHub Actions)

**Status:** [PENDING]
**Phase:** 1
**Group:** — (runs LAST in Phase 1, after 001–007 and 009 are green)
**Risk:** LOW
**Effort:** 30m
**Dependencies:** 001–007, 009 (the workflow validates their combined result)

## Goal
Add `.github/workflows/ci.yml`: a push/PR pipeline that installs deps, runs the test suite, and validates the OpenAPI schema — with a plain Postgres service (NO PostGIS).

## Context
Locks in the Phase-1 quality gate for every future push. Must mirror the repo's `pytest.ini` (coverage gate 80) and the OpenAPI validation command from `.claude/rules/docs.md`.

## SRC reference to adapt from
`SRC:.github/workflows/ci.yml`. **STRIP all GIS**: no GDAL/GEOS/PROJ system packages, no PostGIS image, no spatial DB template. Use `postgres:15` and env-var DB config.

## Files Owned
- `.github/workflows/ci.yml` (C)

## Implementation Steps

### Step 1 — workflow skeleton
```yaml
name: CI
on:
  push: { branches: [main] }
  pull_request: { branches: [main] }
jobs:
  test:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:15
        env:
          POSTGRES_USER: postgres
          POSTGRES_PASSWORD: postgres
          POSTGRES_DB: drf_starter
        ports: ["5432:5432"]
        options: >-
          --health-cmd "pg_isready -U postgres"
          --health-interval 10s --health-timeout 5s --health-retries 5
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: "3.12" }
      - name: Install uv
        uses: astral-sh/setup-uv@v3
      - run: uv sync
      - name: Run tests
        env:
          DB_PRIMARY_HOST: localhost
          DB_PRIMARY_PORT: "5432"
          DB_PRIMARY_NAME: drf_starter
          DB_PRIMARY_USER: postgres
          DB_PRIMARY_PASSWORD: postgres
          SECRET_KEY: ci-secret
          JWT_SECRET_KEY: ci-jwt-secret
        run: uv run pytest --ds=config.django.test
      - name: Validate OpenAPI schema
        env:
          SECRET_KEY: ci-secret
          JWT_SECRET_KEY: ci-jwt-secret
        run: uv run python manage.py spectacular --validate --fail-on-warn --settings=config.django.test
```

Notes:
- The test suite uses SQLite in-memory (`config/django/test.py`), so the Postgres service is a safety net / parity check — keep it but the tests themselves may not need it. Do not add migration steps that require Postgres unless the suite needs them.
- Provide `SECRET_KEY`/`JWT_SECRET_KEY` because pydantic settings require them (no defaults).

## Tests
No unit tests (YAML workflow). Validate by `yamllint`/`actionlint` if available, else a manual review that keys are valid.

## Validation
```bash
# Lint the workflow if a linter is available:
command -v actionlint >/dev/null && actionlint .github/workflows/ci.yml || python -c "import yaml,sys; yaml.safe_load(open('.github/workflows/ci.yml')); print('yaml ok')"
```

## Acceptance Criteria
- [ ] `.github/workflows/ci.yml` triggers on push + PR to `main`.
- [ ] Steps: checkout → Python 3.12 → uv → `uv sync` → pytest → spectacular validate.
- [ ] Plain `postgres:15` service; NO PostGIS/GDAL anywhere.
- [ ] YAML parses; required secrets/env provided.
