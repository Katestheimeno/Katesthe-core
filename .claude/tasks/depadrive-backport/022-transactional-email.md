# 022 — Transactional Email Service (notifications app)

**Status:** [PENDING]
**Phase:** 3
**Group:** A (concurrent with 017–021, 023)
**Risk:** MEDIUM
**Effort:** 55m
**Dependencies:** Phase 2 complete

## Goal
Create a new `notifications` app with an event-code → template registry, an async dispatch service (enqueue on `transaction.on_commit`), and a Celery task that sends via Django's standard `EMAIL_BACKEND`. Register the app AND wire its tests + coverage into `pytest.ini`.

## Context
Standard transactional-email pattern: services build context and enqueue; the task sends with autoretry. **Strip all OneSignal/domain logic** — Django `EMAIL_BACKEND` only. **This subtask is the sole Phase-3 owner of `apps_middlewares.py` AND of `pytest.ini`** (no other subtask touches `pytest.ini` → disjoint/safe).

## SRC reference to adapt from
- `SRC:notifications/services/transactional_email.py` — registry (`_EVENT_REGISTRY` of event → template stem), locale fallback, `transaction.on_commit` enqueue, never-raise-in-caller.
- `SRC:notifications/tasks.py` — `send_transactional_email_task` with `autoretry_for`, `max_retries=3`, backoff. **Remove** the OneSignal branch; keep only the Django-send path + idempotency-friendly logging.
- `SRC:notifications/templates/emails/base.html` — base template (header/main/footer). **De-brand** (generic project name from settings, not "DepaDrive").

## Files Owned
- `notifications/__init__.py` (C)
- `notifications/apps.py` (C)
- `notifications/services/__init__.py` (C)
- `notifications/services/transactional_email.py` (C)
- `notifications/tasks.py` (C)
- `notifications/templates/emails/base.html` (C)
- `notifications/tests/__init__.py`, `notifications/tests/conftest.py` (C, minimal), `notifications/tests/services/__init__.py`, `notifications/tests/services/test_transactional_email.py`, `notifications/tests/tasks/__init__.py`, `notifications/tests/tasks/test_send.py` (C)
- `config/settings/apps_middlewares.py` (M — Phase-3 owner)
- `pytest.ini` (M — sole owner across the whole feature)

## Implementation Steps

### Step 1 — app skeleton
- `notifications/apps.py`: `class NotificationsConfig(AppConfig): name = "notifications"; default_auto_field = "django.db.models.BigAutoField"`.
- Register `'notifications'` in `PROJECT_APPS` in `config/settings/apps_middlewares.py`.

### Step 2 — `notifications/services/transactional_email.py`
- A small `_EVENT_REGISTRY` mapping ~2 universal events to template stems, e.g. `ACCOUNT__ACTIVATION -> "emails/activation"`, `ACCOUNT__PASSWORD_RESET -> "emails/password_reset"` (create only `base.html`; note the stems as placeholders — the service must handle a missing template gracefully by logging and returning, not raising).
- `send_transactional_email(*, event_code, recipient, context=None, from_email=None, reply_to=None)`:
  - Resolve recipient email (string, or object with `.email`); if none → log warning, return.
  - Look up the event; unknown → log warning, return.
  - Build subject + rendered bodies (guard template-miss with try/except → log + return).
  - `from django.db import transaction`; `transaction.on_commit(lambda: send_transactional_email_task.delay(subject=..., to_email=..., text_body=..., html_body=..., event_code=event_code, from_email=..., reply_to=...))`.
  - Never raise into the caller path.

### Step 3 — `notifications/tasks.py`
```python
@shared_task(
    name="notifications.tasks.send_transactional_email",
    autoretry_for=(Exception,), max_retries=3, retry_backoff=True,
    retry_backoff_max=300, retry_jitter=True, ignore_result=True,
)
def send_transactional_email_task(*, subject, to_email, text_body, html_body, event_code, from_email=None, reply_to=None):
    from django.core.mail import EmailMultiAlternatives
    msg = EmailMultiAlternatives(subject=subject, body=text_body, from_email=from_email, to=[to_email], reply_to=reply_to)
    if html_body:
        msg.attach_alternative(html_body, "text/html")
    msg.send()
    logger.bind(event_code=event_code, to=_redact(to_email)).info("notifications.email.sent")
```
Add a `_redact(email)` helper (keep first char of local part). Use `from config.logger import logger`.

### Step 4 — `notifications/templates/emails/base.html`
Generic responsive base template with `{% block body %}`; header/footer pull the project name from context (pass it in, or from settings) — no "DepaDrive" branding.

### Step 5 — wire `pytest.ini` (REQUIRED — collection + coverage)
`pytest.ini` currently has explicit `testpaths = accounts/tests, config/tests, utils/tests` and `--cov=accounts --cov=config --cov=utils`. Without this edit, `notifications/tests` is NEVER collected and `notifications/` is NEVER coverage-measured. Edit `pytest.ini`:
- Add `notifications/tests` to the `testpaths` list.
- Add `--cov=notifications` to `addopts` (alongside the existing `--cov=` entries).
Do not change other keys (markers, `--cov-fail-under=80`, `--nomigrations`, etc.).

## Tests
- Service: `send_transactional_email(event_code="ACCOUNT__ACTIVATION", recipient=user, context={...})` — with `django.test.override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")` and `@pytest.mark.django_db`, wrap in a committed transaction (or use `django_capture_on_commit_callbacks`) and assert one message lands in `django.core.mail.outbox` with the right recipient/subject. Unknown event → no send, no raise. Missing recipient → no send, no raise.
- Task: call `send_transactional_email_task(...)` directly (eager) → assert `mail.outbox` has 1 message; assert decorator `max_retries == 3` and task `name == "notifications.tasks.send_transactional_email"`.
- Use `pytest`'s `django_capture_on_commit_callbacks` fixture to flush `on_commit` in the service test.
- `notifications/tests/conftest.py` should be minimal (or empty) — the root `conftest.py` (014) already exposes the shared `user`/`api_client` fixtures project-wide.

## Validation
```bash
uv run pytest notifications/tests/ -x -v --ds=config.django.test
uv run pytest --ds=config.django.test   # confirm notifications/tests are now collected by testpaths and coverage includes notifications/
uv run python manage.py makemigrations notifications --check --dry-run --settings=config.django.test  # expect no model migrations (no models)
```

## Acceptance Criteria
- [ ] `notifications` app created + registered in `PROJECT_APPS`.
- [ ] `pytest.ini` includes `notifications/tests` in `testpaths` and `--cov=notifications` in `addopts` (collection + coverage confirmed by the full-suite run).
- [ ] Service enqueues via `transaction.on_commit`, never raises into the caller, handles unknown event / missing recipient / template-miss gracefully.
- [ ] Task sends via Django `EMAIL_BACKEND` with full autoretry decorator; email redacted in logs.
- [ ] No OneSignal/Ably/domain branding; base template de-branded.
- [ ] Tests pass; message lands in `mail.outbox`.
