# 011 — Pagination Utility

**Status:** [PENDING]
**Phase:** 2
**Group:** A (concurrent with 010, 012–016)
**Risk:** MEDIUM
**Effort:** 35m
**Dependencies:** Phase 1 complete (uses `utils.api_response.ok` / envelope meta)

## Goal
Add `utils/pagination.py::paginate_or_ok()` — a helper for manually-serialized (non-ModelViewSet) list endpoints that embeds `meta.pagination` in the success envelope and avoids a `COUNT(*)`.

## Context
Lists must be paginated (`.claude/rules/django.md` §2). This helper returns the envelope with pagination metadata, detecting `has_next` by over-fetching one row instead of counting.

## SRC reference to adapt from
`SRC:utils/pagination.py` — `paginate_or_ok(_viewset, queryset, serializer_class, request)`. Behavior: no `?page` → full list capped at 100; with `?page` → page (default size 20, max 100), fetch `page_size + 1` to compute `has_next`; `meta.pagination = {page, page_size, has_next, has_previous}` (no `count`/`total_pages`).

## Files Owned
- `utils/pagination.py` (C)
- `utils/tests/test_pagination.py` (C)

## Implementation Steps

### Step 1 — constants + signature
```python
_DEFAULT_PAGE_SIZE = 20
_MAX_PAGE_SIZE = 100

def paginate_or_ok(_viewset, queryset, serializer_class, request):
    ...
```
`_viewset` is accepted for signature parity (serializer context) but may be unused; pass `context={"request": request}` to the serializer.

### Step 2 — logic
- Read `page = request.query_params.get("page")`. If absent/None: serialize `queryset[:_MAX_PAGE_SIZE]`, return `ok(data, request)` with NO pagination meta (or `meta.pagination = None`).
- If present: parse `page` (int ≥ 1; invalid → 1) and `page_size = min(int(request.query_params.get("page_size", _DEFAULT_PAGE_SIZE)), _MAX_PAGE_SIZE)` (≥ 1).
- `offset = (page - 1) * page_size`; fetch `rows = list(queryset[offset : offset + page_size + 1])`; `has_next = len(rows) > page_size`; trim to `page_size`; `has_previous = page > 1`.
- Serialize the trimmed rows; return `ok(data, request, meta_extra={"pagination": {"page": page, "page_size": page_size, "has_next": has_next, "has_previous": has_previous}})`.

Guard against non-integer query params (fall back to defaults, never 500).

## Tests (`utils/tests/test_pagination.py`) — `@pytest.mark.django_db`
Use the existing `UserFactory` (`accounts.tests.factories`) to create rows and a trivial `ModelSerializer` (or `accounts` serializer) over `User`.
- No `?page`: returns all rows (≤100), `meta` has no pagination or `pagination is None`, `success is True`.
- `?page=1&page_size=2` with 5 rows: returns 2 rows, `has_next True`, `has_previous False`.
- `?page=3&page_size=2` with 5 rows: returns 1 row, `has_next False`, `has_previous True`.
- Over-fetch count: assert only `page_size` rows returned even though a 6th exists.
- Invalid `page_size=abc` falls back to default without error; `page_size=9999` capped at 100.

## Validation
```bash
uv run pytest utils/tests/test_pagination.py -x -v --ds=config.django.test
```

## Acceptance Criteria
- [ ] `paginate_or_ok` returns the success envelope with `meta.pagination` when paging.
- [ ] `has_next` computed by over-fetch (no `.count()`), default 20 / max 100.
- [ ] No `?page` → full list capped at 100.
- [ ] Invalid params degrade gracefully; tests pass.
