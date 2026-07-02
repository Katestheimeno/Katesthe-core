# 024 — Feature validation gate

**Status:** [PENDING]
**Phase:** 4 (final)
**Group:** — (runs after ALL of Phase 3)
**Risk:** LOW
**Effort:** 20m
**Dependencies:** 001–023 (every subtask complete)

## Goal
Run the feature-level Definition-of-Done gate across the whole backport and confirm green: full suite, OpenAPI validation, import smoke, and production boot assertions.

## Context
This is the closing gate for the feature. It writes no production code — it validates the aggregate result and surfaces any remaining breakage (coverage floor, schema warnings). Note: subtask 022 now owns `pytest.ini` and adds `notifications/tests` to `testpaths` + `--cov=notifications`, so `notifications/tests` IS collected by the standard gate command — there is no longer a testpaths follow-up to flag.

## Files Owned
- none (validation only). If the aggregate run reveals a genuine defect, report it to the owning subtask for a fix-forward rather than editing production code here.

## Steps

### Step 1 — full suite (coverage gate 80%)
```bash
uv run pytest --ds=config.django.test
```
Confirm `notifications/tests` (subtask 022) IS collected (via 022's `pytest.ini testpaths` edit) and `notifications/` appears in the coverage report (via 022's `--cov=notifications`). If either is missing, that is a defect in 022 — report it, do not patch `pytest.ini` here.

### Step 2 — OpenAPI schema validation
```bash
uv run python manage.py spectacular --validate --fail-on-warn --settings=config.django.test
```

### Step 3 — import smoke test
```bash
uv run python -c "
from errors.catalog import E
from errors.exceptions import AppAPIError
from utils.api_response import ok, err_single
from config.exception_handler import custom_exception_handler
from utils.drf_error_envelope import validation_error_response
from utils.pagination import paginate_or_ok
from utils.throttles import AuthLoginThrottle
from config.health import liveness, readiness
from utils.models import make_upload_path, BaseOutbox
print('All imports OK')
"
```

### Step 4 — production boot assertions
```bash
# Valid prod config boots:
DEBUG=False ALLOWED_HOSTS=example.com SECRET_KEY=x JWT_SECRET_KEY=y \
  uv run python -c "import os; os.environ['DJANGO_SETTINGS_MODULE']='config.django.production'; import django; django.setup(); print('prod boot ok')"
# Invalid (DEBUG True) must fail — expect non-zero exit:
DEBUG=True ALLOWED_HOSTS=example.com SECRET_KEY=x JWT_SECRET_KEY=y \
  uv run python -c "import os; os.environ['DJANGO_SETTINGS_MODULE']='config.django.production'; import django; django.setup()" || echo "correctly rejected DEBUG=True"
```

### Step 5 — report
Summarize: suite result + coverage %, schema validation result, any coverage-floor shortfalls, and confirm the envelope shape on a live error response (spot check one endpoint — e.g. a 401 login-failure returns `error.code == "AUTH__INVALID_CREDENTIALS"`).

### Step 6 — catalog-code sanity
Do NOT add assertions that forward-looking, unemitted catalog codes appear in responses (`AUTH__TOKEN_EXPIRED`, `AUTH__ACCOUNT_INACTIVE`, `RESOURCE__ALREADY_EXISTS`, `PERMISSION__INSUFFICIENT_ROLE`, `INTERNAL__SERVICE_UNAVAILABLE`, `NOTIFICATION__EMAIL_DELIVERY_FAILED`, `AUTH__PASSWORD_RESET_DISABLED`, `AUTH__EMAIL_VERIFICATION_DISABLED`). They are defined for the contract but not produced by any current path.

## Acceptance Criteria
- [ ] `uv run pytest --ds=config.django.test` green, coverage ≥ 80%, `notifications/tests` collected and `notifications/` coverage-measured.
- [ ] `spectacular --validate --fail-on-warn` exits 0.
- [ ] Import smoke prints `All imports OK`.
- [ ] Production boots with valid config and fails fast with `DEBUG=True`.
- [ ] A live login-failure returns 401 `AUTH__INVALID_CREDENTIALS`; no unemitted codes asserted.
