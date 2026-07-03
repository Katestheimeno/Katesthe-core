# 014 — Integration tests + feature validation gate

**Status:** [PENDING]
**Phase:** 4
**Group:** —
**Risk:** MEDIUM
**Effort:** 45m
**Dependencies:** 001, 002, 003, 004, 005, 006, 007, 008, 009, 010, 011, 012, 013

## Goal
End-to-end tests for the dispatch pipeline and the REST API, then run the full feature validation gate.

## Context
Unit subtasks verify layers in isolation (mostly with mocks). This subtask wires a registered type through the real stack (dispatch → DB → selector → REST) to catch integration seams, then runs the Phase 12 gate.

## Existing pattern to follow
- Integration test style: any `*/tests/` E2E test in this repo using `APIClient` + `django_db`.
- Registry isolation: the `reset_registry` fixture from `notification_system/tests/conftest.py` (owned by 002).

## Files Owned
- `notification_system/tests/integration/__init__.py`
- `notification_system/tests/integration/test_dispatch_pipeline.py`
- `notification_system/tests/integration/test_rest_api.py`

## Implementation Steps

### Step 1 — dispatch pipeline E2E (`test_dispatch_pipeline.py`)
Register a temporary type (via `reset_registry`), then:
- `dispatch(user, "test.event", ...)` creates a `Notification` + IN_APP `NotificationDeliveryLog`; with `default_email=True` asserts `send_notification_email_task` enqueued on commit (mock the task; use `django_capture_on_commit_callbacks`); with in_app enabled asserts `send_notification_to_user` invoked (mock).
- dedupe: two `dispatch()` calls with the same `dedupe_key` inside the window → one `Notification`.
- `should_skip` override via settings → `dispatch` returns `None`.
- category disabled → in-app suppressed per pipeline rules.

### Step 2 — REST API smoke (`test_rest_api.py`)
With a dispatched notification: `GET /api/v1/notifications/` returns it in the envelope; `GET .../unread_count/`; `POST .../{pk}/mark_read/` flips read; `POST .../mark_all_read/`; `DELETE .../{pk}/delete/` soft-deletes (excluded from subsequent list); `GET .../preferences/` grouped; `PUT .../preferences/update/` persists. IDOR spot-check: user B gets 404 on user A's pk.

### Step 3 — run the feature validation gate
Run the five commands from MASTER_TASKS "Validation gate" and confirm all pass:
1. Phase 12 import smoke test (0 types, 0 categories) — run with `DJANGO_SETTINGS_MODULE=config.django.test` exported (a bare `python -c` ignores `--ds`, and `DJANGO_SETTINGS_MODULE` is otherwise unset outside pytest → `ImproperlyConfigured`).
2. `makemigrations notification_system --check --dry-run` → no changes.
3. `bootstrap_notification_preferences --dry-run` → "Nothing to bootstrap."
4. `spectacular --validate --fail-on-warn` → exit 0.
5. `uv run pytest --ds=config.django.test` → green, coverage clears the repo floor (`--cov-fail-under=80` in `pytest.ini`), with `notification_system` included in `--cov` (wired in 001).

## Tests
This subtask IS the integration tests. Use real DB + real selectors/services; mock only the WS channel layer and the Celery broker (`.delay`). The full-suite gate below is the ONE place coverage is enforced (scoped per-subtask runs use `--no-cov`).

## Validation
```bash
uv run pytest notification_system/tests/integration/ -x -v --no-cov --ds=config.django.test
# Then the full feature gate:
DJANGO_SETTINGS_MODULE=config.django.test uv run python -c "
from notification_system.registry import NotificationTypeRegistry, CATEGORIES
from notification_system.models import Notification, UserNotificationPreference
from notification_system.services._dispatch import dispatch
from notification_system.selectors._notification import get_user_notifications_queryset
from notification_system.consumers import NotificationConsumer
print('Phase 12 imports OK', len(NotificationTypeRegistry.all_keys()), len(CATEGORIES))
"
uv run python manage.py makemigrations notification_system --check --dry-run --settings=config.django.test
uv run python manage.py bootstrap_notification_preferences --dry-run --settings=config.django.test
uv run python manage.py spectacular --validate --fail-on-warn --settings=config.django.test
uv run pytest --ds=config.django.test   # full suite; enforces --cov-fail-under=80 across the --cov set incl. notification_system
```

## Acceptance Criteria
- [ ] Dispatch pipeline E2E passes (create, dedupe, skip, email/in-app routing).
- [ ] All 8 REST endpoints pass E2E incl. IDOR.
- [ ] `makemigrations --check` clean; bootstrap dry-run says "Nothing to bootstrap."; OpenAPI validates.
- [ ] Full suite green, total coverage ≥ 80% (repo floor) with the new app measured.
- [ ] Registry reports 0 types / 0 categories; existing `notifications` app untouched; no game/AI/elearning/club references in `notification_system/`.
