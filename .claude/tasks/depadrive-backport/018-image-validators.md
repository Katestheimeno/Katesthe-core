# 018 — Image Validators

**Status:** [PENDING]
**Phase:** 3
**Group:** A (concurrent with 017, 019–023)
**Risk:** LOW
**Effort:** 20m
**Dependencies:** Phase 2 complete

## Goal
Append `validate_image_size` and `validate_image_mime` to `utils/validators.py` for image upload fields.

## Context
Reusable field validators for size and MIME whitelisting. Codes align with the DRF error map so failures surface as clean envelope errors.

## SRC reference to adapt from
`SRC:utils/validators.py` (image validators only) — `validate_image_size(file)` (≤5MB, code `image_too_large`), `validate_image_mime(file)` (jpeg/png/webp, code `image_invalid_type`); both skip silently when file/size/content_type absent.

## Files Owned
- `utils/validators.py` (M — append only; leave `validate_moroccan_phone_number` untouched)
- `utils/tests/test_image_validators.py` (C)

## Implementation Steps

### Step 1 — append validators
```python
MAX_IMAGE_UPLOAD_BYTES = 5 * 1024 * 1024  # 5MB
ALLOWED_IMAGE_MIME = frozenset({"image/jpeg", "image/png", "image/webp"})

def validate_image_size(file, max_bytes: int = MAX_IMAGE_UPLOAD_BYTES):
    size = getattr(file, "size", None)
    if not file or size is None:
        return
    if size > max_bytes:
        raise ValidationError(_("Image exceeds the maximum allowed size."), code="image_too_large")

def validate_image_mime(file, allowed=ALLOWED_IMAGE_MIME):
    content_type = getattr(file, "content_type", None)
    if not file or not content_type:
        return
    if content_type not in allowed:
        raise ValidationError(_("Unsupported image type."), code="image_invalid_type")
```
Reuse the existing `ValidationError` / `_` imports at the top of the file.

### Step 2 (optional link) — note for maintainers
Add a code comment noting that `image_too_large` / `image_invalid_type` map to `VALIDATION__*` in `utils/drf_error_envelope.py::_FIELD_CODE_MAP` if a project wants coded envelope errors (do NOT edit that file here — it is owned by 003; a future task can extend the map).

## Tests (`utils/tests/test_image_validators.py`)
Use a fake file object (`types.SimpleNamespace(size=..., content_type=...)` or `django.core.files.uploadedfile.SimpleUploadedFile`).
- Size under limit → no error; size over `max_bytes` → `ValidationError` with `code == "image_too_large"`.
- Allowed MIME (`image/png`) → no error; disallowed (`application/pdf`) → `ValidationError` `code == "image_invalid_type"`.
- `None` file or missing size/content_type → returns silently (no error).
- No DB required.

## Validation
```bash
uv run pytest utils/tests/test_image_validators.py -x -v --ds=config.django.test
```

## Acceptance Criteria
- [ ] Both validators appended; existing phone validator untouched.
- [ ] Correct codes (`image_too_large`, `image_invalid_type`) and 5MB / jpeg-png-webp defaults.
- [ ] Silent skip on missing file/metadata; tests pass.
