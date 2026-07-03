# 009 — App scaffold auth + permissions placeholders

**Status:** [PENDING]
**Phase:** 1
**Group:** A
**Risk:** LOW
**Effort:** 15m
**Dependencies:** none

## Goal
Update the `starttemplateapp` scaffold template so generated apps follow the new conventions: add an `authentication.py` placeholder and a commented `IsOwner` example in `permissions/__init__.py`.

## Context
`static/exp_app/` is the template copied by the `starttemplateapp` management command. It already has `permissions/` (empty `__init__.py`), `services/`, `selectors/`, etc. It is NOT an installed app (lives under `static/`), so these files are template stubs, not runtime code. Add generic, commented placeholders only — no domain logic, no active auth backend.

## Existing pattern to follow
- Existing scaffold stubs: `static/exp_app/tasks.py`, `static/exp_app/handlers/__init__.py` for the commented-placeholder tone used in this scaffold.
- Layer conventions: `.claude/rules/layers.md` §4 (Permissions — `Is<Condition>` classes, `has_object_permission` for IDOR) and the auth-backend shape in `.claude/rules/django.md` §1.

## Files Owned
- `static/exp_app/authentication.py`  (new)
- `static/exp_app/permissions/__init__.py`  (modify — currently empty)

## Implementation Steps

### Step 1 — Create `static/exp_app/authentication.py`
A module docstring + a fully commented example of a custom DRF authentication backend, e.g.:
```python
"""
Custom authentication backends for this app.

Uncomment and adapt when you need app-specific auth. Wire into a view via
`authentication_classes = [ExampleTokenAuthentication]` or globally in
`config/settings/restframework.py` DEFAULT_AUTHENTICATION_CLASSES.
"""

# from rest_framework.authentication import BaseAuthentication
# from rest_framework.exceptions import AuthenticationFailed
#
#
# class ExampleTokenAuthentication(BaseAuthentication):
#     """Authenticate via a custom header. Return (user, auth) or None."""
#
#     def authenticate(self, request):
#         token = request.headers.get("X-Example-Token")
#         if not token:
#             return None
#         # ... resolve the user from the token ...
#         # raise AuthenticationFailed("Invalid token") on failure
#         return None
```
Keep it entirely commented below the docstring so the file imports cleanly and generates no runtime behavior.

### Step 2 — Edit `static/exp_app/permissions/__init__.py`
Add a module docstring + a commented `IsOwner` example:
```python
"""
Permission classes for this app.

One `Is<Condition>` class per predicate; compose at the viewset:
    permission_classes = [IsAuthenticated, IsOwner]
`has_object_permission` gates the row (IDOR defense).
"""

# from rest_framework.permissions import BasePermission
#
#
# class IsOwner(BasePermission):
#     """Object-level permission: only the owner may access the object."""
#
#     def has_object_permission(self, request, view, obj):
#         return getattr(obj, "owner_id", None) == request.user.id
```

## Tests
No pytest tests — `static/exp_app/` is a template, not an installed/collected app. Validation is a Python syntax check.

## Validation
```bash
uv run python -m py_compile static/exp_app/authentication.py static/exp_app/permissions/__init__.py && echo "scaffold OK"
```

## Acceptance Criteria
- [ ] `static/exp_app/authentication.py` exists with a docstring + commented custom-auth example.
- [ ] `static/exp_app/permissions/__init__.py` has a docstring + commented `IsOwner` example.
- [ ] Both files are valid Python (py_compile passes).
- [ ] No active/runtime auth or permission logic introduced (all example code commented).
