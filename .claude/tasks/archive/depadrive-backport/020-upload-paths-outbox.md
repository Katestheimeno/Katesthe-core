# 020 — Upload Paths + Transactional Outbox

**Status:** [PENDING]
**Phase:** 3
**Group:** A (concurrent with 017–019, 021–023)
**Risk:** MEDIUM
**Effort:** 50m
**Dependencies:** Phase 2 complete

## Goal
Two related `utils/models` additions that SHARE `utils/models/__init__.py` (hence one subtask): (a) `make_upload_path()` factory for dated upload paths; (b) abstract `BaseOutbox` model + generic `process_outbox_entry()` processor.

## Context
Spec items 3.4 and 3.5 both re-export from `utils/models/__init__.py`. Per the file-ownership rule, edits to one file live in one subtask — so they are merged here. `utils/models/__init__.py` currently re-exports the existing abstract models (`_timestamp`, `_softdelete`, etc.).

## SRC reference to adapt from
- `SRC:utils/models/_upload_paths.py` — module-level `upload_to` callables producing `<subdir>/YYYY/MM/DD/<name>_HHMMSS.<ext>`, using `os.path.basename` to strip client path components. **Generalize** the domain-specific callables into a single `make_upload_path(subdir)` factory.
- **Outbox has NO SRC file** (`SRC:assistance/models/_outbox.py` and `SRC:utils/outbox.py` do NOT exist). Build `BaseOutbox` + `process_outbox_entry()` from this spec alone.

## Files Owned
- `utils/models/_upload_paths.py` (C)
- `utils/models/_outbox.py` (C)
- `utils/outbox.py` (C)
- `utils/models/__init__.py` (M — sole owner)
- `utils/tests/test_upload_paths.py` (C)
- `utils/tests/test_outbox.py` (C)

## Implementation Steps

### Step 1 — `utils/models/_upload_paths.py`
```python
import os
from django.utils import timezone

def make_upload_path(subdir: str):
    """Return an `upload_to` callable → '<subdir>/YYYY/MM/DD/<name>_HHMMSS.<ext>'."""
    def _upload_to(instance, filename: str) -> str:
        base = os.path.basename(filename)          # strip path traversal
        name, ext = os.path.splitext(base)
        now = timezone.now()
        stamped = f"{name}_{now:%H%M%S}{ext.lower()}"
        return f"{subdir}/{now:%Y}/{now:%m}/{now:%d}/{stamped}"
    return _upload_to
```
Note: the returned callable is module-referenced via the factory; for `makemigrations` serializability, document that fields should assign `upload_to=make_upload_path("avatars")` at class-definition time (Django serializes the resulting partial-like callable acceptably because it is a closure returned at import — if migration serialization complains, provide named top-level callables instead; keep the factory as the primary API and note this tradeoff).

### Step 2 — `utils/models/_outbox.py`
```python
from django.db import models

class BaseOutbox(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        PROCESSED = "processed", "Processed"
        FAILED = "failed", "Failed"

    event_type = models.CharField(max_length=100)
    payload = models.JSONField(default=dict)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.PENDING)
    created_at = models.DateTimeField(auto_now_add=True)
    processed_at = models.DateTimeField(null=True, blank=True)
    error_message = models.TextField(blank=True, default="")

    class Meta:
        abstract = True
        ordering = ["created_at"]

    def __str__(self) -> str:
        return f"{self.event_type} [{self.status}]"
```
(Abstract → no migration is generated for it.)

### Step 3 — `utils/outbox.py`
```python
from django.utils import timezone

def process_outbox_entry(entry, publisher_fn):
    """Generic processor: call publisher_fn(entry); mark processed/failed. Idempotent-friendly."""
    try:
        publisher_fn(entry)
    except Exception as exc:
        entry.status = entry.Status.FAILED
        entry.error_message = str(exc)
        entry.processed_at = timezone.now()
        entry.save(update_fields=["status", "error_message", "processed_at"])
        raise
    else:
        entry.status = entry.Status.PROCESSED
        entry.error_message = ""
        entry.processed_at = timezone.now()
        entry.save(update_fields=["status", "error_message", "processed_at"])
```

### Step 4 — `utils/models/__init__.py`
Append (one edit, both re-exports):
```python
from ._upload_paths import *
from ._outbox import *
```
Ensure each new module defines `__all__` (`["make_upload_path"]`, `["BaseOutbox"]`).

## Tests
`utils/tests/test_upload_paths.py`:
- `make_upload_path("avatars")(instance=None, "photo.PNG")` → matches `avatars/YYYY/MM/DD/photo_HHMMSS.png` (freeze time with `freezegun` if available, else assert the regex/prefix); extension lowercased; a filename like `../../etc/passwd` reduces to `passwd` (basename).

`utils/tests/test_outbox.py`:
- **Field-set assertion (structural):** assert `BaseOutbox` declares exactly the six specified concrete fields by inspecting `{f.name for f in BaseOutbox._meta.get_fields()}` ⊇ `{"event_type", "payload", "status", "created_at", "processed_at", "error_message"}`. Also assert `BaseOutbox._meta.abstract is True` and that `Status` has `PENDING/PROCESSED/FAILED`.
- **Behavior (`process_outbox_entry`):** use a lightweight fake exposing `Status` (point it at `BaseOutbox.Status`), `save`, and the attributes — avoids creating a concrete DB model. Verify: successful `publisher_fn` → status `processed`, `processed_at` set, `error_message` empty; raising `publisher_fn` → status `failed`, `error_message` populated, and the exception re-raised.
- If a concrete model is easier for behavior, define one inside the test module inheriting `BaseOutbox` with `@pytest.mark.django_db` — but note `--nomigrations` builds the schema from models, so a test-only model must be registered before DB setup; the fake-object approach is simpler and preferred. The `_meta.get_fields()` assertion needs NO DB and runs on `BaseOutbox` directly.

## Validation
```bash
uv run pytest utils/tests/test_upload_paths.py utils/tests/test_outbox.py -x -v --ds=config.django.test
uv run python -c "from utils.models import make_upload_path, BaseOutbox; from utils.outbox import process_outbox_entry; print('OK')"
```

## Acceptance Criteria
- [ ] `make_upload_path(subdir)` returns a callable producing dated, basename-stripped, lowercased-ext paths.
- [ ] `BaseOutbox` abstract model has exactly the six specified fields (asserted via `_meta.get_fields()`) + status choices; `_meta.abstract is True`.
- [ ] `process_outbox_entry` marks processed/failed correctly and re-raises on failure.
- [ ] Both re-exported from `utils/models` (single `__init__.py` edit); tests pass.
