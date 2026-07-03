# 002 — External-API health-check command skeleton (6.2)

**Status:** [PENDING]
**Phase:** 1
**Group:** A
**Risk:** MEDIUM
**Effort:** 45m
**Dependencies:** none

## Goal
Ship a generic `check_external_apis` management command: a CI-friendly template for probing external API dependencies in parallel, with an EMPTY `SERVICES` registry and a docstring explaining how projects add their own probes.

## Context
`SRC:utils/management/commands/check_external_apis.py` is 884 lines and heavily Rhitoric-specific (pva / rhiai / tutor / events probes, `config.settings.ai_endpoints` imports, `game.services._external_api_client`). Extract ONLY the generic scaffolding; strip every domain probe and service definition.

## Existing pattern to follow
- Generic scaffolding to KEEP (from `SRC:.../check_external_apis.py`): `ProbeStatus(str, Enum)` (PASS/FAIL/SKIP/MOCK), `@dataclass ProbeResult`, `@dataclass ConfigCheck`, `_timed_post` / `_timed_get` helpers using `time.perf_counter()`, `_build_headers`, `ThreadPoolExecutor(max_workers=5)` in `_run_probes`, the `Command(BaseCommand)` with `add_arguments` (`--service`, `--verbose`, `--timeout`) and `handle()` returning exit code 1 on any failure, and the `_print_banner` / `_print_*_section` helpers using `self.style.SUCCESS/WARNING/ERROR`.
- Existing command style: `utils/management/commands/starttemplateapp.py` for `BaseCommand` conventions in this repo.

## Files Owned
- `utils/management/commands/check_external_apis.py`
- `utils/tests/test_check_external_apis.py`

## Implementation Steps

### Step 1 — Create the command with an empty SERVICES registry
Module docstring: explain the command probes external dependencies with no DB side effects and reports config status, HTTP code, latency, and shape; document how to register a service. Imports: `sys, time, uuid`, `from concurrent.futures import ThreadPoolExecutor, as_completed`, `from dataclasses import dataclass, field`, `from enum import Enum`, `from typing import ...`, `import requests`, `from django.core.management.base import BaseCommand`, and `from django.conf import settings` (required — `_print_banner` reads `settings.PROJECT_NAME`). Do NOT import `config.settings.ai_endpoints` or any `game`/domain module.

Define:
- `SERVICES: dict = {}` at module level, with a docstring/comment block showing the expected shape, e.g.:
  ```python
  # SERVICES maps a service key to a probe callable, e.g.:
  #   SERVICES = {"my_api": _probe_my_api}
  # where a probe callable has signature (timeout: int, verbose: bool) -> list[ProbeResult].
  # Ships EMPTY — projects register their own probes.
  ```
- `ProbeStatus(str, Enum)` with PASS/FAIL/SKIP/MOCK.
- `@dataclass ProbeResult` (service, endpoint, status, duration_ms=0.0, http_status=None, response_preview="", error_message="", warnings=field(default_factory=list)).
- `@dataclass ConfigCheck` (service, base_url="", base_url_ok=False, api_key_ok=False, enabled=False, flag_name="", warnings=field(default_factory=list)). Drop the domain-specific `hf_token_ok` if you like, or keep as `api_key_ok` only — keep it generic.
- Generic helpers `_build_headers(api_key: str)`, `_timed_post(url, payload, headers, timeout)`, `_timed_get(url, headers, timeout)` (returns `(resp_or_none, duration_ms, error_str)` with `requests.exceptions.Timeout` / `ConnectionError` / generic branches).

### Step 2 — Command class
- `add_arguments`: `--service` (choices derived from `list(SERVICES) + ["all"]`, default `"all"`), `--verbose` (store_true), `--timeout` (int, default 10).
- `handle`: resolve requested services (empty registry ⇒ nothing to probe), run config checks + probes via `ThreadPoolExecutor`, print banner/sections, and `sys.exit(1)` only if any `ProbeResult.status == ProbeStatus.FAIL`. With an empty `SERVICES`, it prints "no services registered" and exits 0.
- `_run_probes(services, timeout, verbose)`: `ThreadPoolExecutor(max_workers=5)`, submit each service's probe callable, collect results, wrap probe exceptions into a `ProbeResult(status=FAIL)`.
- `_print_banner` / `_print_config_section` / `_print_results_section`: use `self.stdout.write(self.style....())`. Use a generic banner title from `settings.PROJECT_NAME` (available in this repo) instead of hardcoding "Rhitoric".

## Tests
Create `utils/tests/test_check_external_apis.py` (no DB needed):

- **Empty registry runs clean:** `from django.core.management import call_command`; `call_command("check_external_apis")` completes without raising and does not `sys.exit(1)` (catch `SystemExit` and assert code 0 or no exit).
- **`--verbose` / `--timeout` flags parse:** `call_command("check_external_apis", "--verbose", "--timeout", "5")` runs clean.
- **Dataclass defaults:** construct `ProbeResult(service="x", endpoint="y", status=ProbeStatus.PASS)` and assert `duration_ms == 0.0`, `warnings == []`.
- **`ProbeStatus` values:** assert the four members equal their string values.
- **A FAIL result triggers exit 1:** temporarily register a probe in `SERVICES` (via `monkeypatch.setitem`) that returns `[ProbeResult(..., status=ProbeStatus.FAIL)]`; assert `call_command` raises `SystemExit` with code 1. (Use `capsys` to swallow output.)
- **`_timed_get` timeout branch:** `patch("utils.management.commands.check_external_apis.requests.get", side_effect=requests.exceptions.Timeout)`; assert returns `(None, <float>, "Timeout...")`.

## Validation
```bash
uv run pytest utils/tests/test_check_external_apis.py -x -v --ds=config.django.test
uv run python manage.py check_external_apis --settings=config.django.test   # exits 0 with empty SERVICES
```

## Acceptance Criteria
- [ ] `SERVICES = {}` ships empty with a documented registration shape.
- [ ] No `ai_endpoints`, `game`, or any domain import remains.
- [ ] `--service`, `--verbose`, `--timeout` flags work; command exits 0 on no-failures, 1 on any FAIL.
- [ ] `ThreadPoolExecutor`, `ProbeStatus`, `ProbeResult`, `ConfigCheck`, and `_timed_*` helpers preserved.
