# 009 — Update accounts tests → envelope shape

**Status:** [PENDING]
**Phase:** 1
**Group:** A (sequential core chain — TAIL; after 004)
**Risk:** HIGH
**Effort:** 60m
**Dependencies:** 004 (and transitively 001–003)

## Goal
Reconcile the existing `accounts/tests/` with the new exception-handler behavior: error responses now use the envelope shape; login bad-credentials → **401 `AUTH__INVALID_CREDENTIALS`**; other DRF validation failures → **422**. Update every affected assertion.

## Context
`config/exception_handler.py` (004) is now DRF's `EXCEPTION_HANDLER`. This changes error responses that flow THROUGH the handler (i.e. that raise a DRF/Django exception): (a) bodies from `{"detail": ...}` / `{field: [...]}` to `{"success": false, "error": {...}}` / `{"success": false, "errors": [...]}`; (b) status codes — login credential failure → **401**, login missing-field / other validation → **422** (LOCKED decision #7, see MASTER_TASKS). `accounts/tests/controllers/test_auth.py` (1931 lines, coverage-driven) asserts many `HTTP_400_BAD_REQUEST` on login/validation paths. Views that return an **explicit `Response(...)` without raising** are NOT touched by the handler and likely need no change (see Step 3). Success-body assertions (`response.data['access']`, `['username']`, `'id' in response.data`) generally stay valid because success responses are NOT auto-wrapped.

## Files Owned
- `accounts/tests/controllers/test_auth.py` (M)
- `accounts/tests/serializers/test_auth.py` (M)
- `accounts/tests/test_basic.py` (M)

> These are the ONLY files this subtask touches. Do not modify production code — if a test reveals a genuine handler bug, report it for a 004 follow-up rather than editing 004's files.

## Implementation Steps

### Step 1 — Run the suite first to enumerate breakage
```bash
uv run pytest accounts/tests/ --ds=config.django.test -q
```
Collect every ACTUAL failure. Do NOT preemptively edit tests that still pass. Expect two failure classes: (a) status mismatch 400→422/401, (b) body-shape mismatch on error responses that raise through the handler.

### Step 2 — Reconcile status codes (LOCKED mapping)
For each failing case that submits invalid/missing input to a DRF endpoint and asserted `HTTP_400_BAD_REQUEST`:
- **Login bad credentials** (JWT/token-obtain `jwt-create` with wrong/nonexistent username or password) → assert **`HTTP_401_UNAUTHORIZED`** and, when checking the body, `data['error']['code'] == "AUTH__INVALID_CREDENTIALS"`. The handler special-cases the login path on a non-field `ValidationError` (004 Step 1a).
- **Login/serializer missing field** (e.g. missing `password`, missing body fields → field-keyed `ValidationError`) → assert `HTTP_422_UNPROCESSABLE_ENTITY` with `data['errors'][0]['code']` in the `VALIDATION__*` set. (Missing-field is field-keyed validation → 422, NOT 401.)
- **Other serializer/validation errors** → assert `HTTP_422_UNPROCESSABLE_ENTITY`.
- Keep `HTTP_401_UNAUTHORIZED` assertions where the endpoint requires auth and none was provided (permission layer runs before the body is parsed) — body code there is `AUTH__UNAUTHENTICATED`.
- When in doubt between 401/422 for a specific case, RUN it and match the handler's actual output rather than guessing — but the login-credentials vs missing-field split above is the intended contract.

### Step 3 — Reconcile error bodies (only for handler-routed responses)
For any FAILING assertion reading an error body of an exception-routed response:
- Replace `{"detail": ...}` / field-dict expectations with the envelope: `data['success'] is False` and either `data['error']['code']` (single) or `data['errors'][0]['code']` (validation).
- **The activation view does NOT go through the handler — likely leave it UNCHANGED.** `accounts/controllers/_auth.py:396-483` returns an explicit non-raising `JsonResponse({"success": False, "message": ...}, status=400)` (a Django response, not routed through DRF), so the custom handler never touches it. The test at `test_auth.py:1287` (`assert 'Invalid activation link.' in data['message']`) **still passes unchanged**. Do NOT preemptively rewrite it — verify by running the suite first; only touch it if Step 1 shows it actually failing (it should not).
- **Do NOT assert forward-looking catalog codes that no subtask emits** (`AUTH__TOKEN_EXPIRED`, `AUTH__ACCOUNT_INACTIVE`, `RESOURCE__ALREADY_EXISTS`, `PERMISSION__INSUFFICIENT_ROLE`, `INTERNAL__SERVICE_UNAVAILABLE`, `NOTIFICATION__EMAIL_DELIVERY_FAILED`, `AUTH__PASSWORD_RESET_DISABLED`, `AUTH__EMAIL_VERIFICATION_DISABLED`). Only assert codes actually produced by the handler on the exercised path (`AUTH__INVALID_CREDENTIALS`, `AUTH__UNAUTHENTICATED`, `AUTH__TOKEN_INVALID`, `VALIDATION__*`, `RESOURCE__NOT_FOUND`, `PERMISSION__DENIED`, `RATE_LIMIT__EXCEEDED`, `INTERNAL__ERROR`).

### Step 4 — Keep success assertions intact
Do not change assertions on successful responses (200 token bodies, `/me` GET/PATCH) unless they actually fail. If a success path now returns an envelope (only if a view was changed to call `ok()` — it was not in Phase 1), adapt; otherwise leave as-is.

### Step 5 — Re-run until green
```bash
uv run pytest accounts/tests/ --ds=config.django.test
```

## Tests
This subtask edits tests; it adds no new production code. Preserve the intent/coverage of each existing test — only update expected status/shape on cases that actually broke. Do not delete tests to make them pass; if a test is genuinely obsolete (asserts a removed behavior), convert it to assert the new behavior.

## Validation
```bash
uv run pytest accounts/tests/ -q --ds=config.django.test
uv run pytest --ds=config.django.test   # full suite must be green after this subtask
```

## Acceptance Criteria
- [ ] `accounts/tests/` passes against the new exception handler.
- [ ] Login bad-credentials assertions expect **401 `AUTH__INVALID_CREDENTIALS`**; login missing-field expects 422 `VALIDATION__*`.
- [ ] The activation-view test is left unchanged if it still passes (it returns a non-handler-routed custom body); no passing test preemptively edited.
- [ ] No assertion asserts an unemitted forward-looking code.
- [ ] Validation-failure statuses updated to the handler's actual output (422/401 as specified/observed).
- [ ] Test intent/coverage preserved; no tests deleted merely to pass.
- [ ] Full suite green.
