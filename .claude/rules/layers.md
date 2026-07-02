# Layers — per-component patterns

## Migration Notes

**Source files merged (8):** `layers/naming-structure-rules.mdc`, `layers/00-pydantic-schemas-pattern.mdc`, `layers/06-selectors-pattern.mdc`, `layers/07-permissions-pattern.mdc`, `layers/08-handlers-signals.mdc`, `layers/09-tasks-pattern.mdc`, `layers/10-filters-pattern.mdc`, `layers/11-admin-organization.mdc`.

**Conflicts resolved (C6):** layer files are cohesive per-layer; merged behind one index. Layer cross-talk bans and import direction live in `foundations.md` — not repeated here.

**Deliberately removed:** none. Every pattern section preserved verbatim in intent.

---

## Index

1. [File layout & naming](#1-file-layout--naming)
2. [Serializers & Pydantic schemas](#2-serializers--pydantic-schemas)
3. [Selectors](#3-selectors)
4. [Permissions](#4-permissions)
5. [Signals & handlers](#5-signals--handlers)
6. [Celery tasks](#6-celery-tasks)
7. [Filters (`django-filter`)](#7-filters-django-filter)
8. [Admin organization](#8-admin-organization)

---

## 1. File layout & naming

Per-app layout. Use `_name.py` (underscore prefix) for a single-file domain; a `name/` sub-package once a layer has more than one file.

```
<app>/
  models/
    __init__.py          # re-export
    _user.py             # primary domain
    _profile.py          # secondary
  controllers/           # or views.py
    __init__.py
    auth.py
    profile.py
  services/
    __init__.py
    registration.py
    profile.py
  selectors/
    __init__.py
    user.py              # all reads
  serializers/
    __init__.py
    _user.py             # UserCreateSerializer, UserListSerializer, ...
  schemas/               # Pydantic — complex validation / OpenAPI
    __init__.py
    _user.py
  permissions/
    __init__.py
    _user.py             # IsOwner, HasActiveSubscription
  filters/
    __init__.py
    _user.py
  handlers/              # signal handlers (lightweight)
    __init__.py
    _user.py
  tasks/                 # or tasks.py
    __init__.py
  admin/
    <domain>/
      admin.py           # @admin.register
      actions.py
      filters.py
  urls/
    __init__.py
    _user.py
  migrations/
  tests/
    models/
    controllers/
    services/
    selectors/
    serializers/
    factories/
  templates/
```

### Naming

| Thing | Convention | Example |
|---|---|---|
| Classes | `PascalCase` | `User`, `UserProfile`, `UserCreateSerializer` |
| Functions, modules | `snake_case` | `get_user_by_email`, `registration.py` |
| Serializers | `<Model><Action>Serializer` | `UserCreateSerializer`, `UserListSerializer`, `UserDetailSerializer` |
| Selectors | verb-first, state in the name | `get_user_by_email`, `list_active_users`, `user_exists`, `count_pending_requests` |
| Services | `<Domain>Service` class **or** module-level functions | `UserService.register_user`, or `registration.py::register_user` |
| Permissions | `Is<Condition>` | `IsOwner`, `IsAdmin`, `HasActiveSubscription`, `ClientPhoneVerified` |
| FilterSets | `<Model>Filter` | `UserFilter`, `GameSessionFilter` |
| Celery tasks | verb_object, `<domain>.<verb>_<object>` task name | e.g. `game.tasks.cleanup_stale_waiting_games` |

---

## 2. Serializers & Pydantic schemas

- **DRF serializers** for all write paths and most reads — they're what the router/DRF viewset already integrates with.
- **Pydantic schemas** are used in this project for:
  - Complex domain validation where DRF is clumsy (nested envelopes, discriminated unions).
  - OpenAPI documentation of envelope responses.
- **Never** use Pydantic for DB writes. Services do writes.
- **Action-specific serializer classes** — `UserCreateSerializer` ≠ `UserListSerializer` ≠ `UserDetailSerializer`. A write payload is a different shape than a read response; name them that way.
- **Envelope list responses** — when this codebase uses a documented OpenAPI shim for list envelopes, match the existing pattern in `config/spectacular*` and sibling views. **This repo may not use a separate `ApiEnvelope*` serializer** — verify before copying patterns from other projects.

---

## 3. Selectors

- **All** non-trivial reads live in `<app>/selectors/`. If a view or service runs `Model.objects.filter(...)` for more than a trivial PK lookup, extract it.
- **Pre-tune N+1 inside the selector.** Every `get_*` / `list_*` function includes its own `select_related` / `prefetch_related`.
- **Read-only.** Selectors never write. Selectors never call services.
- **Scope to the caller** — `list_client_requests(user)` not `list_requests()`.
- **Name says the filter.** `list_joinable_games_for_player(player)` beats `list_games(status, user)`.

---

## 4. Permissions

- **One `Is<Condition>` class per predicate.** Compose at the viewset: `permission_classes = [IsAuthenticated, IsOwner, ClientPhoneVerified]`.
- **`has_permission` gates the whole view.** `has_object_permission` gates the row.
- **Re-check permissions at the service layer** for any write touched by multiple entry points (admin + API).
- **IDOR:** the permission class must verify the user can see the object, not just "is authenticated".

---

## 5. Signals & handlers

- **Handlers live in `<app>/handlers/`**, imported from `AppConfig.ready()` (not at module import time — circular risk).
- **Use signals for:** cross-app cache invalidation, audit logs, lightweight side effects.
- **Do NOT use signals for:** core business logic, transactional guarantees, critical paths. Services do those.
- **Handler body is tiny.** If work is non-trivial, enqueue a Celery task inside the handler.
- **`post_save` + `created=True`** is the common idiom for "on new row".

---

## 6. Celery tasks

- **Design for at-least-once delivery.** Tasks MUST be idempotent — use `select_for_update`, unique constraints, or state machines.
- **Auto-retry on transient failures:**
  ```python
  @shared_task(
      name="game.tasks.example_periodic_task",
      autoretry_for=(Exception,),
      max_retries=3,
      retry_backoff=True,
      retry_backoff_max=300,
      retry_jitter=True,
  )
  def example_periodic_task(): ...
  ```
- **Persist correlation state** — the task picks up its context from the DB, not from task-argument payloads. Payload drift is a bug waiting to happen.
- **Enqueue from a service, via `transaction.on_commit`** — never from a model `save()`, never before the transaction commits.
- **Transactional outbox pattern** for external publishes (webhooks, third parties): write an outbox row inside the DB transaction, enqueue the publish task in `on_commit`, fallback-queue on Redis if Celery enqueue fails. Follow an existing app that already uses outbox in this repo, if any; otherwise document a new ADR before introducing it.

---

## 7. Filters (`django-filter`)

- **One `FilterSet` per exposed list endpoint.** Named `<Model>Filter`.
- **Whitelist filterable fields** on the FilterSet `Meta.fields` — never expose all model fields implicitly.
- **Declare ordering + pagination at the viewset**; filters don't own those.
- **Avoid filter parameters that leak schema** (e.g., internal status codes exposed to clients).

---

## 8. Admin organization

- **Per-domain sub-packages:** `<app>/admin/<domain>/{admin.py,actions.py,filters.py}`.
- **One `@admin.register(Model)` per admin class.** No implicit registrations.
- **Bulk actions** live in `actions.py`; admin class imports from its sibling.
- **Custom filters** (`SimpleListFilter`) live in `filters.py`.
- **Use Unfold** (already configured) — no ad-hoc templates. Rely on `@admin.display`, `list_filter`, `list_display`, `search_fields`, `readonly_fields`.
- **Staff-only mutations** (e.g., dépanneur verification) are implemented as **admin actions first** — HTTP APIs only if ops need automation (ADR-001 Phase 5).
