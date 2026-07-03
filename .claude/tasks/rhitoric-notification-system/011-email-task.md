# 011 — Email delivery Celery task

**Status:** [PENDING]
**Phase:** 2
**Group:** B
**Risk:** MEDIUM
**Effort:** 30m
**Dependencies:** 002, 006

## Goal
Create `send_notification_email_task` — reads a `Notification`, sends the email, and records the delivery outcome in `NotificationDeliveryLog`.

## Context
Enqueued by `dispatch()` via `transaction.on_commit` when the email channel is enabled. Idempotent-friendly, auto-retrying.

## Existing pattern to follow
- SRC reference: `SRC:notification_system/tasks/_email.py` (has the `noreply@rhitoric.com` fallback to STRIP).
- DST: `config.db_utils.read_from_primary`, `config.logger.logger`, existing Celery task decorators in `accounts/tasks.py`.

## Files Owned
- `notification_system/tasks/__init__.py`
- `notification_system/tasks/_email.py`
- `notification_system/tests/tasks/__init__.py`
- `notification_system/tests/tasks/test_email.py`

## Implementation Steps

### Step 1 — `_email.py`
Copy SRC with these changes:
- Decorator keeps: `@shared_task(name="notification_system.tasks.send_notification_email_task", autoretry_for=(Exception,), max_retries=3, retry_backoff=True, retry_jitter=True)` (confirm/keep the SRC name or set this one).
- Read the `Notification` inside `with read_from_primary():` (import `from config.db_utils import read_from_primary`).
- Build + send via `django.core.mail.EmailMultiAlternatives`.
- **STRIP** `from_email = getattr(settings, "EMAIL_HOST_USER", None) or "noreply@rhitoric.com"`. Replace with:
  ```python
  from_email = settings.DEFAULT_FROM_EMAIL
  ```
- On success: update/create the EMAIL `NotificationDeliveryLog` with `status=SENT`, `sent_at=now`.
- On failure: set `status=FAILED`, store a **PII-redacted** `error_message`, set `Notification.email_failed=True`; let `autoretry_for` handle retries.

### Step 2 — `tasks/__init__.py`
Re-export `send_notification_email_task` so `from notification_system.tasks import send_notification_email_task` works (dispatch imports it lazily).

## Tests
`test_email.py` (mock `EmailMultiAlternatives.send` — never hit SMTP):
- success path: email "sent" → EMAIL delivery log `SENT` with `sent_at`.
- failure path: `send` raises → delivery log `FAILED`, `error_message` set (redacted, no raw PII/token), `Notification.email_failed=True`.
- `from_email` equals `settings.DEFAULT_FROM_EMAIL` (assert the sent message's from address).
- missing notification id → task exits gracefully (no crash loop).

## Validation
```bash
uv run pytest notification_system/tests/tasks/ -x -v --no-cov --ds=config.django.test
```

## Acceptance Criteria
- [ ] `from_email` is `settings.DEFAULT_FROM_EMAIL`; NO `noreply@rhitoric.com` / `EMAIL_HOST_USER` fallback.
- [ ] Retry config `autoretry_for/max_retries=3/retry_backoff/retry_jitter` present.
- [ ] Reads via `read_from_primary()`; writes delivery log for SENT and FAILED.
- [ ] Error messages redacted; SMTP mocked in tests.
