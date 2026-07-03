# 019 — CSV/XLSX Export Helpers

**Status:** [PENDING]
**Phase:** 3
**Group:** A (concurrent with 017, 018, 020–023)
**Risk:** LOW
**Effort:** 30m
**Dependencies:** Phase 2 complete

## Goal
Add `utils/export.py` with `csv_response()` and `xlsx_response()` that stream tabular data as downloads, with formula-injection sanitization. Add `openpyxl` to runtime deps.

## Context
Admin/analytics exports. Spreadsheet cells beginning with `=`, `+`, `@`, or TAB are a CSV/XLSX injection vector — neutralize by prefixing a single quote.

## SRC reference to adapt from
`SRC:utils/export.py` — `csv_response(filename, headers, rows)`, `xlsx_response(filename, headers, rows)`; `_sanitize_csv_field()` prefixes dangerous cells with `'` (but leaves numeric literals alone); sanitizes filename; sets `Content-Disposition`.

## Files Owned
- `utils/export.py` (C)
- `utils/tests/test_export.py` (C)
- `pyproject.toml` (M — Phase-3 owner)

> `pyproject.toml` was edited by 016 (Phase 2, sentry optional extra) — different phase, safe. Add `openpyxl` to `[project].dependencies` (runtime).

## Implementation Steps

### Step 1 — sanitizer
```python
_DANGEROUS_PREFIXES = ("=", "+", "@", "\t", "\r")
def _sanitize_cell(value):
    s = "" if value is None else str(value)
    if s and s[0] in _DANGEROUS_PREFIXES:
        return "'" + s
    # leading "-" that is not a numeric literal is also dangerous
    if s.startswith("-") and not _is_number(s):
        return "'" + s
    return s
```
Implement `_is_number(s)` (int/float parse). Add `_sanitize_filename(name)` keeping `[A-Za-z0-9._-]`.

### Step 2 — `csv_response(filename, headers, rows)`
`rows` is a list of dicts (or lists). Build an `HttpResponse(content_type="text/csv")`, write with `csv.writer`, apply `_sanitize_cell` to every value, set `Content-Disposition: attachment; filename="<sanitized>.csv"`. Return the response.

### Step 3 — `xlsx_response(filename, headers, rows)`
Use `openpyxl.Workbook`; write header row + sanitized data rows; save to a `BytesIO`; return `HttpResponse(content, content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")` with the attachment disposition.

### Step 4 — `pyproject.toml`
Add to `[project].dependencies`: `"openpyxl>=3.1.0"`.

## Tests (`utils/tests/test_export.py`)
- `csv_response("report", ["a","b"], [{"a":"=SUM(1)","b":"x"}])` → response content-type `text/csv`, body contains `'=SUM(1)` (quote-prefixed), `Content-Disposition` filename `report.csv`.
- Numeric cell `"-5"` is NOT quote-prefixed; `"-abc"` IS.
- `xlsx_response(...)` returns the xlsx content-type and a non-empty body; load it back with `openpyxl.load_workbook(BytesIO(resp.content))` and assert the injected cell is quote-prefixed.
- Filename sanitization strips `../` and spaces.
- No DB required.

## Validation
```bash
uv run pytest utils/tests/test_export.py -x -v --ds=config.django.test
```

## Acceptance Criteria
- [ ] `csv_response` / `xlsx_response` produce correct content-types + attachment dispositions.
- [ ] Formula-injection cells neutralized; numeric literals preserved.
- [ ] `openpyxl` added to runtime deps.
- [ ] Tests pass.
