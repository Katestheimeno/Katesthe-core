# 021 — Ops scripts & coverage config

**Status:** [PENDING]
**Phase:** 3
**Group:** A (concurrent with 017–020, 022, 023)
**Risk:** LOW
**Effort:** 35m
**Dependencies:** Phase 2 complete (smoke script probes 006's health endpoints)

## Goal
Bundle three no-test ops/config items that share no files with any other subtask: the smoke-test script (spec 3.6), the Celery worker/beat run scripts (spec 3.8, incl. `docker-compose.yml`), and the `.coveragerc` refinement (spec 3.7 — MINUS the `config/django/*` omit, which subtask 007 already added in Phase 1).

## Context
These are small, test-free config/shell items. Grouping avoids three sub-15-minute subtasks while keeping file ownership disjoint from everything else. Justification for grouping: no Python, no unit tests, and none of these files are touched by any other same-phase subtask.

## SRC references to adapt from
- `SRC:scripts/smoke_mvp.sh` → generic `scripts/smoke.sh`.
- `SRC:docker/scripts/run-celery-worker.sh`, `SRC:docker/scripts/run-celery-beat.sh`.
- `SRC:.coveragerc`.

## Files Owned
- `scripts/smoke.sh` (C)
- `docker/scripts/run-celery-worker.sh` (C)
- `docker/scripts/run-celery-beat.sh` (C)
- `docker-compose.yml` (M — sole owner)
- `.coveragerc` (M — Phase-3 co-owner: adds `utils/consumers.py` omit ONLY, if not already present)

> `.coveragerc` is co-owned across phases: **007 (Phase 1)** already added the single `config/django/*` omit line. **This subtask (021, Phase 3)** must NOT re-add `config/django/*`. Different phases → sequential → safe.

## Implementation Steps

### Step 1 — `scripts/smoke.sh`
- `BASE_URL="${BASE_URL:-http://localhost:8000}"`.
- Probe `GET $BASE_URL/health/` (expect 200) and `GET $BASE_URL/ready/` (expect 200) with `curl -sS -m 10 -o /dev/null -w "%{http_code}"`.
- If `SMOKE_JWT` set, probe an authenticated endpoint (e.g. `/api/v1/auth/users/me/` — verify actual path from `accounts/urls`) with `Authorization: Bearer $SMOKE_JWT`.
- Tabulated pass/fail output; `exit 0` if all pass, `exit 1` on any failure. `set -euo pipefail`. `chmod +x`.

### Step 2 — `docker/scripts/run-celery-worker.sh`
```bash
#!/usr/bin/env bash
set -euo pipefail
CONCURRENCY="${CELERY_CONCURRENCY:-2}"
LOGLEVEL="${CELERY_LOG_LEVEL:-info}"
if [ "${DEV_AUTORELOAD:-0}" = "1" ]; then
  exec uv run watchfiles "celery -A config.celery.app worker -l ${LOGLEVEL} -c ${CONCURRENCY} --max-memory-per-child=256000 --max-tasks-per-child=500" .
else
  exec uv run celery -A config.celery.app worker -l "${LOGLEVEL}" -c "${CONCURRENCY}" \
    --max-memory-per-child=256000 --max-tasks-per-child=500
fi
```

### Step 3 — `docker/scripts/run-celery-beat.sh`
Same style; run `celery -A config.celery.app beat -l ${LOGLEVEL} --scheduler django_celery_beat.schedulers:DatabaseScheduler`, with the `DEV_AUTORELOAD` watchfiles branch. `chmod +x` both.

### Step 4 — `docker-compose.yml`
Update the `celery_worker` service `command:` to `["/app/docker/scripts/run-celery-worker.sh"]` and `celery_beat` to `["/app/docker/scripts/run-celery-beat.sh"]`. Preserve every other key (build, volumes, env_file, depends_on, restart, healthcheck.disable) exactly as-is. Ensure the scripts are on the image (they are, via `COPY . .`) and executable.

### Step 5 — `.coveragerc` (minimal — most of spec 3.7 is ALREADY present)
The current `.coveragerc` already contains nearly everything spec 3.7 lists. Before adding anything, OPEN the file and confirm — the existing `[run] omit` already has `*/settings/*`, `manage.py`, `*/wsgi.py`, `*/asgi.py`, `*/urls.py`, `*/celery.py`; the existing `[report] exclude_lines` already has `pragma: no cover`, `def __repr__`, `raise NotImplementedError`, `if __name__ == .__main__.:`, `if TYPE_CHECKING:`. And `config/django/*` was added by 007.
- **The ONLY genuinely-new entry is `utils/consumers.py`** (dev-only Channels consumer) → add it to `[run] omit`.
- For every other spec-3.7 entry, verify it is already absent before adding — do NOT duplicate an existing line, and do NOT re-add `config/django/*`.

## Tests
No unit tests. Validate scripts parse and `docker-compose.yml` stays valid.

## Validation
```bash
bash -n scripts/smoke.sh && bash -n docker/scripts/run-celery-worker.sh && bash -n docker/scripts/run-celery-beat.sh && echo "scripts ok"
python -c "import yaml; yaml.safe_load(open('docker-compose.yml')); print('compose ok')"
uv run python -c "import configparser; c=configparser.ConfigParser(); c.read('.coveragerc'); print('coveragerc ok')"
test "$(grep -c 'config/django/\*' .coveragerc)" = "1"   # 007's line present exactly once, not duplicated
grep -q 'utils/consumers.py' .coveragerc && echo "consumers omit ok"
# Optional end-to-end (needs a running server):
# BASE_URL=http://localhost:8000 bash scripts/smoke.sh
```

## Acceptance Criteria
- [ ] `scripts/smoke.sh` probes `/health/` + `/ready/`, optional JWT endpoint, exits 0/1, executable.
- [ ] Celery run scripts support `CELERY_CONCURRENCY`, memory/task limits, `DEV_AUTORELOAD`; DatabaseScheduler for beat.
- [ ] `docker-compose.yml` celery services call the new scripts; all other keys preserved.
- [ ] `.coveragerc` gains `utils/consumers.py` only; `config/django/*` appears exactly once (not duplicated); no existing entry dropped or re-added.
- [ ] All parse checks pass.
