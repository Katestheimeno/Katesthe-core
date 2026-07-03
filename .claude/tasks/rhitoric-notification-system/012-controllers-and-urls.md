# 012 — REST controllers, URLs, `parse_page_params`, URL wiring

**Status:** [PENDING]
**Phase:** 3
**Group:** C
**Risk:** MEDIUM
**Effort:** 55m
**Dependencies:** 007, 008, 009

## Goal
Create the 8 REST endpoints, their URL config, add the missing `parse_page_params` pagination helper, and mount the app under `/api/v1/`.

## Context
Controllers are thin HTTP layers over selectors/services/serializers. They MUST use the DST standard response envelope (not the SRC raw dict) and be IDOR-scoped via the selectors.

## Existing pattern to follow
- SRC references: `SRC:notification_system/controllers/{_list.py,_actions.py,_preferences.py}`, `SRC:notification_system/urls/__init__.py`.
- DST envelope: `utils.api_response.ok(data, request, meta_extra=...)` and `err_single(...)` — see `utils/pagination.py::paginate_or_ok` for how `ok` is called and how `meta.pagination` is embedded.
- DST error code: `from errors.catalog import NOTIFICATION__NOT_FOUND` (added in 001).
- `@extend_schema` usage in `accounts/controllers/`.

## Files Owned
- `notification_system/controllers/__init__.py`
- `notification_system/controllers/_list.py`
- `notification_system/controllers/_actions.py`
- `notification_system/controllers/_preferences.py`
- `notification_system/urls/__init__.py`
- `utils/pagination.py`  (ADD `parse_page_params`; DO NOT alter `paginate_or_ok`)
- `config/urls.py`  (add the URL include)
- `notification_system/tests/controllers/__init__.py`
- `notification_system/tests/controllers/test_list.py`
- `notification_system/tests/controllers/test_actions.py`
- `notification_system/tests/controllers/test_preferences.py`

## Implementation Steps

### Step 1 — add `parse_page_params` to `utils/pagination.py`
**`parse_page_params` does NOT exist in DST** (only `paginate_or_ok`). The SRC controllers do `from utils.pagination import parse_page_params`. Add:
```python
def parse_page_params(request) -> tuple[int, int]:
    """Return (page, page_size) from query params, clamped to sane bounds.

    page >= 1 (default 1); page_size in [1, _MAX_PAGE_SIZE] (default _DEFAULT_PAGE_SIZE).
    """
    # reuse module constants _DEFAULT_PAGE_SIZE / _MAX_PAGE_SIZE; defensive int() parsing
```
Model it on the parsing already inside `paginate_or_ok`. Do not modify `paginate_or_ok` itself.

### Step 2 — `_list.py`
`NotificationListView`, `NotificationDetailView`, `UnreadCountView` (all `IsAuthenticated`, `@extend_schema` tag `Notifications`). Adapt from SRC:
- **STRIP** `from utils.throttling import NotificationActionThrottle` and all `throttle_classes = [...]` (those classes do not exist in DST; locked decision #8).
- **Envelope:** replace the raw `Response({"count","next","previous","results"})` with the DST envelope — return `ok(results_data, request, meta_extra={"pagination": {...}})`. For 404 use `err_single(NOTIFICATION__NOT_FOUND, request, status=404)` (or the DST equivalent — mirror how existing controllers raise coded errors).
- List uses `parse_page_params(request)` + the selector `get_user_notifications_queryset(...)` with `retention_days` clamped to `settings.NOTIFICATION_RETENTION_DAYS` (the default retention window, defined in `config/settings/notification_system.py` by 001 — do NOT hardcode a `90` literal).
- Detail uses `get_notification_for_user(pk, request.user.id)`; `None` → 404 envelope.

### Step 3 — `_actions.py`
`MarkReadView`, `MarkAllReadView`, `NotificationSoftDeleteView` — call the action services (007), return envelope responses, strip throttles, `@extend_schema`.

### Step 4 — `_preferences.py`
`NotificationPreferencesListView` (GET grouped) and `NotificationPreferencesUpdateView` (PUT) — call preference selector/service, use the update serializer for input validation, envelope + `@extend_schema`.

### Step 5 — `urls/__init__.py`
Copy the SRC URL patterns verbatim (`app_name = "notification_system"`, the 8 paths). Order matters: specific paths (`unread_count/`, `mark_all_read/`, `preferences/…`) BEFORE `<int:pk>/` variants — preserve the SRC ordering.

### Step 6 — `controllers/__init__.py`
Package init (may re-export the views for convenience; the urls module imports from the `_list`/`_actions`/`_preferences` modules directly per SRC).

### Step 7 — mount in `config/urls.py`
Add to `urlpatterns` (after the `accounts.urls` include):
```python
path(v1_url(""), include("notification_system.urls")),
```
`v1_url` helper already exists in `config/urls.py`.

## Tests
Per view: unauthenticated → 401; authenticated happy path returns the envelope (`success: true`, `meta.request_id`/`version`); **IDOR** — user A cannot read/mark/delete user B's notification (404/empty); list filters (`read`, `notification_type`, `retention_days`) work; `mark_all_read` scoped to caller; unread_count correct; preferences GET grouped + PUT validation (invalid payload → coded 4xx envelope). Use DRF `APIClient` with forced auth.

## Validation
```bash
uv run pytest notification_system/tests/controllers/ -x -v --no-cov --ds=config.django.test
uv run python manage.py spectacular --validate --fail-on-warn --settings=config.django.test
```

## Acceptance Criteria
- [ ] `parse_page_params` added to `utils/pagination.py`; `paginate_or_ok` unchanged.
- [ ] All 8 endpoints live under `/api/v1/notifications/...`; app mounted in `config/urls.py`.
- [ ] Responses use the standard envelope; 404 uses `NOTIFICATION__NOT_FOUND`.
- [ ] No `NotificationActionThrottle`/`NotificationBulkThrottle` imports.
- [ ] `IsAuthenticated` + IDOR verified on every view; `@extend_schema` on all.
- [ ] `spectacular --validate --fail-on-warn` exits 0.
