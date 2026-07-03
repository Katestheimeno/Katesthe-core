# 007 — Admin CopyableFieldMixin + css/js (9.1)

**Status:** [PENDING]
**Phase:** 1
**Group:** A
**Risk:** MEDIUM
**Effort:** 45m
**Dependencies:** none

## Goal
Add a reusable `CopyableFieldMixin` for Unfold admin that renders click-to-copy fields, plus the CSS and JS assets — with `console.log` debug statements stripped from the JS.

## Context
Extracted from `SRC:utils/admin/{mixins.py,css/copy-field.css,js/copy-field.js}`. The mixin is already generic.

**Static-asset placement (CRITICAL — do not repeat the SRC source-tree layout):** `AppDirectoriesFinder` only scans `<app>/static/**`, i.e. `utils/static/…`. It does NOT scan files placed directly under `utils/admin/css|js/`. DST's only `STATICFILES_DIRS` root is `<repo>/static/` (`config/settings/paths.py:36-38`), which also would not see `utils/admin/…`. In SRC the *served* copies actually live under a `STATICFILES_DIRS` root (`.../static/utils/admin/…`); `utils/admin/css|js/` is only source. Therefore in DST the assets MUST be created at **`utils/static/utils/admin/css/copy-field.css`** and **`utils/static/utils/admin/js/copy-field.js`** so `AppDirectoriesFinder` discovers them. The `Media` class string paths stay `utils/admin/css/copy-field.css` / `utils/admin/js/copy-field.js` because those are the static-relative URLs (i.e. relative to the `utils/static/` root). No `STATICFILES_DIRS`/`paths.py` change is required.

## Existing pattern to follow
- `SRC:.../utils/admin/mixins.py` — copy the mixin verbatim (generic).
- `SRC:.../utils/admin/css/copy-field.css` — copy verbatim.
- `SRC:.../utils/admin/js/copy-field.js` — copy but STRIP every `console.log(...)` (and keep `console.error` only if you prefer; per plan, remove the noisy debug logs — safest is remove all `console.log`, keep the functional clipboard/toast logic).
- Existing admin usage: `utils/permissions/` and any `admin/` module in the repo for Unfold `ModelAdmin` conventions.

## Files Owned
- `utils/admin/__init__.py`
- `utils/admin/mixins.py`
- `utils/static/utils/admin/css/copy-field.css`
- `utils/static/utils/admin/js/copy-field.js`
- `utils/tests/test_admin_mixins.py`

## Implementation Steps

### Step 1 — Package init
Create `utils/admin/__init__.py` (may be empty or re-export: `from .mixins import CopyableFieldMixin`).

### Step 2 — `utils/admin/mixins.py`
Copy `CopyableFieldMixin` from SRC. Methods:
- `copyable_field(self, value, field_name=None, css_class='copy-field', default_display='-', copy_success_message=None)` — returns `default_display` when value is falsy; otherwise `format_html('<span class="{}" data-code="{}" title="Click to copy {}">{}</span>', css_class, value, field_name or 'value', value)`.
- `copyable_email(self, obj, field_name='email', field_label=None)` — reads `getattr(obj, field_name, None)`, uses `css_class='copy-field'`.
- `copyable_text(self, obj, field_name, field_label=None)` — `css_class='copy-field'`.
- `copyable_code(self, obj, field_name, field_label=None)` — `css_class='code-copy'`.
- Inner `class Media:` with `css = {'all': ('utils/admin/css/copy-field.css',)}` and `js = ('utils/admin/js/copy-field.js',)`.
Imports: `from django.utils.html import format_html`.

### Step 3 — `utils/static/utils/admin/css/copy-field.css`
Copy verbatim from SRC (`SRC:utils/admin/css/copy-field.css`). Key selectors: `.copy-field`, `.code-copy`, `.copy-field[data-code*="@"]` (email tint), `.copied` (success), `.error` (failure).

### Step 4 — `utils/static/utils/admin/js/copy-field.js`
Copy from SRC (`SRC:utils/admin/js/copy-field.js`) but REMOVE all `console.log(...)` lines. Preserve: `DOMContentLoaded` wiring over `.copy-field, .code-copy` elements, click handler reading `data-code`, `navigator.clipboard.writeText()` primary with `fallbackCopy()` (textarea + `execCommand('copy')`) fallback, the `.copied` "✓ Copied!" 1.5s feedback, the `.error` "✗ Failed" state, and `showToast()` (bottom-right, auto-dismiss ~2s).

## Tests
Create `utils/tests/test_admin_mixins.py` (no DB):
- Instantiate a throwaway class mixing in `CopyableFieldMixin`; call `copyable_field("abc@x.com", "Email")` → assert output contains `data-code="abc@x.com"` and `class="copy-field"`.
- `copyable_field("", "X")` → returns `'-'` (default_display branch).
- `copyable_code(obj, "token")` where `obj.token = "TKN123"` → output contains `class="code-copy"` and `data-code="TKN123"`.
- `copyable_email(obj)` where `obj.email = "u@x.com"` → output contains `data-code="u@x.com"`.
- `Media.css` and `Media.js` reference the static-relative `utils/admin/...` paths (NOT `utils/static/...`).
- **No console.log shipped:** read `utils/static/utils/admin/js/copy-field.js` and assert `"console.log"` not in its contents.

## Validation
```bash
uv run pytest utils/tests/test_admin_mixins.py -x -v --ds=config.django.test
uv run python -c "from utils.admin.mixins import CopyableFieldMixin; print('OK')"
! grep -q "console.log" utils/static/utils/admin/js/copy-field.js && echo "no console.log OK"
# Assets are actually discoverable by the staticfiles finders (guards the 404 regression):
uv run python manage.py findstatic utils/admin/css/copy-field.css --settings=config.django.test
uv run python manage.py findstatic utils/admin/js/copy-field.js --settings=config.django.test
```

## Acceptance Criteria
- [ ] `CopyableFieldMixin` importable from `utils.admin.mixins` with all four methods + `Media`.
- [ ] CSS + JS assets present under `utils/static/utils/admin/css|js/` and RESOLVED by `manage.py findstatic` (proves the `Media` URLs are served, not 404).
- [ ] Zero `console.log` in the shipped JS.
- [ ] Empty-value returns `default_display`; email/code variants apply correct css class.
- [ ] No `STATICFILES_DIRS`/settings change required (assets live under `utils/static/` so `AppDirectoriesFinder` finds them).
