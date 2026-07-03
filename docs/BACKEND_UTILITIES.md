# Backend utilities

Ops- and developer-facing capabilities that ship with the template but are not part of the public HTTP contract (see `docs/API_CONTRACT.md` for that).

## Transactional email (`notifications/`)

A minimal `notifications` app (registered in `PROJECT_APPS`) sends transactional emails through Django's standard `EMAIL_BACKEND` — no OneSignal/Ably/third-party push.

```python
from notifications.services.transactional_email import send_transactional_email

send_transactional_email(
    event_code="ACCOUNT__ACTIVATION",  # or "ACCOUNT__PASSWORD_RESET"
    recipient=user,                     # a User instance or a raw email string
    context={"activation_url": url},    # merged with {"project_name": ...} for template rendering
)
```

- `_EVENT_REGISTRY` maps an `event_code` to a template stem under `notifications/templates/` (currently `ACCOUNT__ACTIVATION` → `emails/activation`, `ACCOUNT__PASSWORD_RESET` → `emails/password_reset`); `_SUBJECTS` maps the same codes to a subject line (falls back to a generic `"{project_name} — {event_code}"`).
- The service **never raises** — an unresolvable recipient, unregistered event, or missing template is logged (`notifications.email.no_recipient` / `.unknown_event` / `.template_missing`) and the call returns `None`.
- Delivery is deferred to `transaction.on_commit`, so the email is only enqueued once the triggering DB transaction actually commits, then sent by `notifications.tasks.send_transactional_email_task` (`autoretry_for=(Exception,)`, `max_retries=3`, `retry_backoff=True`). Recipient addresses are redacted before logging (`j***@example.com`).
- To add a new transactional email: add a template under `notifications/templates/emails/<stem>.html`, register `"YOUR__EVENT_CODE": "emails/<stem>"` in `_EVENT_REGISTRY` (and a subject in `_SUBJECTS` if you don't want the generic fallback).

## CSV / XLSX export (`utils/export.py`)

```python
from utils.export import csv_response, xlsx_response

return csv_response("users_export", headers=["id", "email"], rows=queryset.values_list("id", "email"))
return xlsx_response("users_export", headers=["id", "email"], rows=[{"id": u.id, "email": u.email} for u in users])
```

- `rows` may be an iterable of dicts (looked up by `headers`) or lists/tuples (written positionally).
- Every cell is passed through formula-injection sanitization: values starting with `=`, `+`, `@`, TAB, or CR are quote-prefixed; a leading `-` is quote-prefixed unless the whole value is numeric. This prevents a user-controlled field (e.g. a name) from executing a formula when the export is opened in Excel/LibreOffice/Sheets.
- `xlsx_response` requires `openpyxl` (declared as a runtime dependency in `pyproject.toml`).

## Upload paths (`utils/models/_upload_paths.py`, re-exported from `utils.models`)

```python
from utils.models import make_upload_path

class Photo(models.Model):
    image = models.ImageField(upload_to=make_upload_path("photos"))
```

`make_upload_path(subdir)` returns an `upload_to` callable producing `<subdir>/YYYY/MM/DD/<name>_HHMMSS.<ext>` — the filename is basename-stripped first (removes client path components / traversal attempts).

## Transactional outbox (`utils/models/_outbox.py`, `utils/outbox.py`)

For external side effects (webhooks, third-party publishes) that must survive the triggering write even if the immediate publish fails:

```python
from utils.models import BaseOutbox
from utils.outbox import process_outbox_entry

class WebhookOutbox(BaseOutbox):
    pass  # event_type, payload (JSON), status, created_at, processed_at, error_message inherited

# inside the same DB transaction as the write that needs the side effect:
WebhookOutbox.objects.create(event_type="order.created", payload={...})

# later (Celery task / worker): 
process_outbox_entry(entry, publisher_fn=lambda e: send_webhook(e.payload))
```

`BaseOutbox` is abstract (`event_type: CharField`, `payload: JSONField`, `status: pending|processed|failed`, `created_at`, `processed_at`, `error_message`). `process_outbox_entry(entry, publisher_fn)` calls `publisher_fn(entry)`, marks the entry `processed` on success or `failed` (with `error_message`) on exception, and **re-raises** so the calling Celery task's own retry/autoretry logic still fires.

## Image upload validators (`utils/validators.py`)

```python
from utils.validators import validate_image_size, validate_image_mime

class PhotoSerializer(serializers.ModelSerializer):
    def validate_image(self, file):
        validate_image_size(file)   # default max 5MB (MAX_IMAGE_UPLOAD_BYTES)
        validate_image_mime(file)   # default {"image/jpeg", "image/png", "image/webp"} (ALLOWED_IMAGE_MIME)
        return file
```

Both are silent no-ops if the file or the relevant attribute (`size`/`content_type`) is absent — they only reject on an actual size/type violation, raising Django's `ValidationError` with `code="image_too_large"` / `code="image_invalid_type"` respectively. These codes are not yet wired into `utils/drf_error_envelope.py`'s `_FIELD_CODE_MAP`; a project that wants coded envelope errors for image validation failures needs to extend that map.

## Celery task template (`accounts/tasks.py`)

`example_cleanup_task` is the reference pattern for new tasks: idempotent by construction (state-based filter, not payload-based), with the standard retry decorator:

```python
@shared_task(
    name="accounts.tasks.example_cleanup_task",
    autoretry_for=(Exception,),
    max_retries=3,
    retry_backoff=True,
    retry_backoff_max=300,
    retry_jitter=True,
)
def example_cleanup_task():
    ...
```

Worker/broker settings added in `config/settings/celery.py`: `CELERY_TASK_SERIALIZER`/`CELERY_RESULT_SERIALIZER`/`CELERY_ACCEPT_CONTENT` pinned to `json` (no pickle), `CELERY_WORKER_MAX_TASKS_PER_CHILD=500`, `CELERY_WORKER_MAX_MEMORY_PER_CHILD=256_000` (KB), `CELERY_TASK_TIME_LIMIT=600` / `CELERY_TASK_SOFT_TIME_LIMIT=540` (seconds), `CELERY_WORKER_PREFETCH_MULTIPLIER=1`. Worker/beat now start via `docker/scripts/run-celery-worker.sh` / `run-celery-beat.sh` (parameterized, `DatabaseScheduler` for beat) rather than inline `docker-compose.yml` commands.

The `starttemplateapp` app scaffold (`static/exp_app/`) now includes a `tasks.py` template and a `tests/tasks/` stub so newly generated apps follow this convention from the start.

## Optional Sentry integration (`config/settings/monitoring.py`)

```python
from config.settings.monitoring import configure_sentry
configure_sentry()  # already called from config/django/production.py
```

`configure_sentry()` is a safe no-op (returns `False`, never raises) when `SENTRY_DSN` (pydantic setting, default `""`) is empty or the `sentry_sdk` package is not installed. `sentry-sdk[django,celery]` is declared as an **optional** `production` dependency group in `pyproject.toml` (`uv sync --extra production`), never a default runtime dependency. When configured, it sets `traces_sample_rate` from `SENTRY_TRACES_SAMPLE_RATE` (default `0.1`) and `send_default_pii=False`.

## Debug-payload middleware (`config/middleware/debug_payload.py`)

Opt-in, local-development-only request/response body logger, gated by the `REQUEST_RESPONSE_DEBUG` pydantic setting (default `False`) **and** wired only under `config/django/local.py`'s `if DEBUG:` block. Instantiation raises `django.core.exceptions.ImproperlyConfigured` if `REQUEST_RESPONSE_DEBUG` is truthy while Django's resolved `DEBUG` is `False` — this prevents accidentally shipping it to production. Skips `/admin`, `/static`, `/media`, `/health`, `/ready`, `/api/schema`, `/silk/`. Redacts ~20 sensitive key names (`password`, `token`, `secret`, `otp`, `api_key`, `authorization`, `jwt`, `cvv`, `pin`, etc., case-insensitive) before logging; caps logged body size at 4096 bytes; only logs JSON content types.

## Access log (`config/middleware/access_log.py`)

Emits one structured Loguru line per request (`http.access`): `method`, `path`, `status`, `duration_ms`, `size`, `user_id`, `request_id`. Skips 200s on `/health`, `/ready`, `/static`, `/media`, `/favicon.ico` to keep logs signal-only; 4xx/5xx responses are additionally enriched with client IP (`X-Forwarded-For` first hop, else `REMOTE_ADDR`) and a truncated `User-Agent`. 5xx logs at `warning`, everything else at `info`.
