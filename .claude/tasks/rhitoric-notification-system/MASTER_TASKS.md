# Rhitoric Notification System (backport)

Priority: P1
Status: active
**Date:** 2026-07-03
**Source:** Phase 12 (12.1–12.20) of `RHITORIC_BACKPORT_PLAN.md` — generic-infrastructure extraction from `SRC:/home/tmpusr/Documents/github/Rhitoric-core`.
**Goal:** A new self-contained `notification_system` Django app (in-app + email notifications, WebSocket delivery, type/category registry, two-level user preferences, deduplication, delivery logging, role-based visibility, full REST API, management command) shipping an EMPTY type registry, coexisting with the existing `notifications` app.

---

## Locked decisions

1. **SRC = `/home/tmpusr/Documents/github/Rhitoric-core`; DST = this repo.** Read SRC reference files, extract GENERIC patterns only. Obey ALL 18 "What NOT to Do" items in the plan.
2. **Empty registry.** `CATEGORIES = {}`. No `register_core_types()`. None of Rhitoric's 35 type registrations. Strip the SRC 4-entry `CATEGORIES` and the `NotificationTypeConfig.category` default of `"elearning"` (make the fallback neutral, e.g. `"general"`, and derive-from-prefix logic must not hardcode `elearning`/`clubs`).
3. **Adapters ship neutral.** `should_skip_notification_for_user()` returns `False` (strip `_AI_NOTIFICATION_TYPES` + the elearning AI import). `get_user_roles(user)` returns Django group names ONLY (strip the `accounts.models.ClubMembership` import/query).
4. **Consumer** handles ONLY `notification_new`, `auth_rotate`, `ping`/heartbeat, `connection_established`. STRIP the 5 game no-op handlers (`player_joined`, `player_left_game`, `game_abandoned`, `game_completed`, `vote_cast`). Keep close codes `4401` (auth failed) and `4001` (unauthenticated) only.
5. **Consumer WS-auth deps are ABSENT in DST** (`utils/middleware/jwt_websocket_auth.py`, `utils/websocket/rate_limit.py`, `utils/websocket/protocol.py` — they belong to the SEPARATE `rhitoric-auth-core` Phase 5, not yet backported). GUARD those imports so the app builds standalone: fall back to Channels `AuthMiddlewareStack` `scope["user"]` when absent, skipping subprotocol/`auth_rotate` gracefully. Do NOT hard-depend on `rhitoric-auth-core`.
6. **Email task** uses `settings.DEFAULT_FROM_EMAIL` (STRIP the `"noreply@rhitoric.com"` fallback and the `EMAIL_HOST_USER` fallback). Keep `autoretry_for=(Exception,), max_retries=3, retry_backoff=True, retry_jitter=True`.
7. **`parse_page_params` does NOT exist in DST** (only `paginate_or_ok` in `utils/pagination.py`). Locked-decision #7 in the brief was inaccurate. The controllers subtask ADDS `parse_page_params(request) -> (page, page_size)` to `utils/pagination.py`.
8. **Throttles:** DST has `utils/throttles.py` (NOT `utils/throttling.py`) with no Notification throttle classes. STRIP `NotificationActionThrottle` / `NotificationBulkThrottle` imports and `throttle_classes` from controllers (projects add later).
9. **Response envelope:** controllers MUST return the DST standard envelope via `utils.api_response.ok` / `err_single` (per `.claude/rules/api.md`), NOT the raw `{"count","next",...}` dict the SRC controllers use. Adapt on copy. All views `IsAuthenticated`, IDOR-scoped to `request.user`, with `@extend_schema`.
10. **Wiring locations:** `INSTALLED_APPS` → `config/settings/apps_middlewares.py` `PROJECT_APPS` (there is NO `config/settings/django.py`). New settings → `config/settings/notification_system.py` + `from config.settings.notification_system import *` in `config/settings/__init__.py`. URL include → `config/urls.py` (`path(v1_url(""), include("notification_system.urls"))`). Error code → `errors/catalog.py` (module constant + class `E`). ASGI route → `config/routing.py` (a commented-out `NotificationConsumer` placeholder already exists there).
11. **COEXISTS with `notifications/`** — do NOT modify or delete the existing `notifications` app.
12. Reuse existing DST infra: `TimeStampedModel` (`utils/models/_timestamp.py`), `config.logger.logger`, `config.db_utils.read_from_primary`, `utils.api_response.{ok,err_single}`, Channels (installed). Tests: factory-boy, `uv run pytest --ds=config.django.test`, coverage floor **80%** (`--cov-fail-under=80` in `pytest.ini`; aspire 100% new-code). Scoped per-subtask runs use `--no-cov`; coverage is enforced only in the full-suite gate (014).

---

## Priority queue

| ID | Subtask | Phase | Group | Risk | Effort | Scope |
|----|---------|-------|-------|------|--------|-------|
| 001 | Bootstrap: package, apps.py, constants, settings, INSTALLED_APPS, error code | 0 | — | MED | 25m | wiring so the app is installed & importable |
| 002 | Models (4) + factories + model tests | 1 | A | MED | 45m | core tables, indexes, constraints |
| 003 | Registry (empty) + tests | 1 | A | LOW | 25m | `NotificationTypeRegistry`, `CATEGORIES={}` |
| 004 | Adapters (neutral) + tests | 1 | A | LOW | 20m | `get_user_roles`, `should_skip…` |
| 005 | WebSocket utils + tests | 1 | A | LOW | 20m | `send_notification_to_user`, serialize |
| 006 | Initial migration | 1b | — | MED | 15m | `0001_initial.py` (4 tables) |
| 008 | Selectors (3) + tests | 2 | B1 | MED | 45m | reads, retention, role visibility |
| 009 | Serializers (3) + tests | 2 | B1 | LOW | 30m | list/detail/preference shapes |
| 010 | WebSocket consumer (guarded auth) + tests | 2 | B1 | HIGH | 45m | ASGI consumer + routing |
| 011 | Email Celery task + tests | 2 | B1 | MED | 30m | `send_notification_email_task` |
| 007 | Services (dispatch/actions/preferences/broadcast) + tests | 2 | B2 | HIGH | 60m | dispatch engine; after B1 (imports 008 + 011) |
| 012 | Controllers + URLs + `parse_page_params` + URL wiring | 3 | C | MED | 55m | 8 REST endpoints, envelope, IDOR |
| 013 | Management command + tests | 3 | C | LOW | 30m | `bootstrap_notification_preferences` |
| 014 | Integration tests + feature validation gate | 4 | — | MED | 45m | dispatch pipeline E2E + REST smoke + gate |

---

## Subtasks

<!-- Canonical status list. Status token: PENDING | IN_PROGRESS | BLOCKED | COMPLETED | SKIPPED | DEFERRED -->
- [PENDING] [001-bootstrap-app-and-wiring.md](001-bootstrap-app-and-wiring.md) — Bootstrap package, apps.py, constants, settings, INSTALLED_APPS, error code
- [PENDING] [002-models-and-factories.md](002-models-and-factories.md) — Four models + factories + model tests
- [PENDING] [003-registry.md](003-registry.md) — Empty notification type registry
- [PENDING] [004-adapters.md](004-adapters.md) — Neutral pluggable adapters
- [PENDING] [005-websocket-utils.md](005-websocket-utils.md) — WebSocket delivery utils
- [PENDING] [006-initial-migration.md](006-initial-migration.md) — 0001_initial migration
- [PENDING] [007-services.md](007-services.md) — Dispatch/action/preference/broadcast services
- [PENDING] [008-selectors.md](008-selectors.md) — Notification/preference/role selectors
- [PENDING] [009-serializers.md](009-serializers.md) — Notification & preference serializers
- [PENDING] [010-consumer.md](010-consumer.md) — WebSocket consumer + ASGI routing
- [PENDING] [011-email-task.md](011-email-task.md) — Email delivery Celery task
- [PENDING] [012-controllers-and-urls.md](012-controllers-and-urls.md) — REST controllers, URLs, parse_page_params
- [PENDING] [013-management-command.md](013-management-command.md) — bootstrap_notification_preferences command
- [PENDING] [014-integration-and-gate.md](014-integration-and-gate.md) — Integration tests + validation gate

---

## Dependency graph

```
001 (Phase 0 — bootstrap; app installed & importable; must pass import before Phase 1)
 │
 ├────────────► Group A (Phase 1, parallel)
 │               002 models      003 registry     004 adapters     005 ws-utils
 │                 │
 │                 ▼
 │               006 migration (Phase 1b, after 002)
 │
 ▼
Group B1 (Phase 2a, parallel — after their deps in Phase 1/1b complete)
  008 selectors  (needs 002,003)
  009 serializers(needs 002)
  010 consumer   (needs 002; guarded imports; edits config/routing.py)
  011 email task (needs 002,006)
 │
 ▼
Group B2 (Phase 2b, after B1)
  007 services   (needs 002,003,004,005,006 AND 008 + 011 — dispatch imports the
                  selector `is_category_enabled_for_user` and the email task at run time)
 │
 ▼
Group C (Phase 3, parallel)
  012 controllers+urls (needs 007,008,009)   013 mgmt command (needs 003,006,007)
 │
 ▼
014 integration + validation gate (needs ALL)
```

- **Phase 0:** 001 runs alone. Gate: `python -c "import notification_system, notification_system.constants"` under `--ds=config.django.test` succeeds and app appears in `INSTALLED_APPS`.
- **Phase 1 Group A:** 002/003/004/005 run concurrently (disjoint files). 006 migration serializes after 002.
- **Phase 2a Group B1:** 008/009/010/011 run concurrently (disjoint files).
- **Phase 2b Group B2:** 007 (services/dispatch) runs after B1 — it `import`s the preference selector (008) and enqueues the email task (011), so both modules must exist before 007's tests run under `-x`.
- **Phase 3 Group C:** 012/013 run concurrently.
- **Phase 4:** 014 runs last.

---

## File ownership (strictly disjoint)

### 001 (Phase 0)
- `notification_system/__init__.py`
- `notification_system/apps.py`
- `notification_system/constants.py`
- `config/settings/notification_system.py`
- `config/settings/__init__.py` *(add one import line)*
- `config/settings/apps_middlewares.py` *(add `"notification_system"` to `PROJECT_APPS`)*
- `errors/catalog.py` *(add `NOTIFICATION__NOT_FOUND` to module + class `E`)*

### 002 (Group A)
- `notification_system/models/__init__.py`
- `notification_system/models/_notification.py`
- `notification_system/models/_notification_preference.py`
- `notification_system/models/_category_preference.py`
- `notification_system/models/_delivery_log.py`
- `notification_system/tests/__init__.py`
- `notification_system/tests/conftest.py`
- `notification_system/tests/factories.py`
- `notification_system/tests/models/__init__.py`
- `notification_system/tests/models/test_notification.py`
- `notification_system/tests/models/test_preferences.py`

### 003 (Group A)
- `notification_system/registry.py`
- `notification_system/tests/test_registry.py`

### 004 (Group A)
- `notification_system/adapters.py`
- `notification_system/tests/test_adapters.py`

### 005 (Group A)
- `notification_system/utils.py`
- `notification_system/tests/test_ws_utils.py`

### 006 (Phase 1b)
- `notification_system/migrations/__init__.py`
- `notification_system/migrations/0001_initial.py`

### 007 (Group B2)
- `notification_system/services/__init__.py`
- `notification_system/services/_registry.py`
- `notification_system/services/_dispatch.py`
- `notification_system/services/_actions.py`
- `notification_system/services/_preferences.py`
- `notification_system/services/_broadcast.py`
- `notification_system/tests/services/__init__.py`
- `notification_system/tests/services/test_dispatch.py`
- `notification_system/tests/services/test_actions.py`
- `notification_system/tests/services/test_preferences.py`

### 008 (Group B1)
- `notification_system/selectors/__init__.py`
- `notification_system/selectors/_notification.py`
- `notification_system/selectors/_preference.py`
- `notification_system/selectors/_user_roles.py`
- `notification_system/tests/selectors/__init__.py`
- `notification_system/tests/selectors/test_notification.py`
- `notification_system/tests/selectors/test_preference.py`

### 009 (Group B1)
- `notification_system/serializers/__init__.py`
- `notification_system/serializers/_notification.py`
- `notification_system/serializers/_preference.py`
- `notification_system/serializers/_category_preference.py`
- `notification_system/tests/serializers/__init__.py`
- `notification_system/tests/serializers/test_serializers.py`

### 010 (Group B1)
- `notification_system/consumers.py`
- `config/routing.py` *(add `ws/notifications/` route)*
- `notification_system/tests/consumers/__init__.py`
- `notification_system/tests/consumers/test_notification_consumer.py`

### 011 (Group B1)
- `notification_system/tasks/__init__.py`
- `notification_system/tasks/_email.py`
- `notification_system/tests/tasks/__init__.py`
- `notification_system/tests/tasks/test_email.py`

### 012 (Group C)
- `notification_system/controllers/__init__.py`
- `notification_system/controllers/_list.py`
- `notification_system/controllers/_actions.py`
- `notification_system/controllers/_preferences.py`
- `notification_system/urls/__init__.py`
- `utils/pagination.py` *(ADD `parse_page_params`; do not alter `paginate_or_ok`)*
- `config/urls.py` *(add the URL include)*
- `notification_system/tests/controllers/__init__.py`
- `notification_system/tests/controllers/test_list.py`
- `notification_system/tests/controllers/test_actions.py`
- `notification_system/tests/controllers/test_preferences.py`

### 013 (Group C)
- `notification_system/management/__init__.py`
- `notification_system/management/commands/__init__.py`
- `notification_system/management/commands/bootstrap_notification_preferences.py`
- `notification_system/tests/management/__init__.py`
- `notification_system/tests/management/test_bootstrap.py`

### 014 (Phase 4)
- `notification_system/tests/integration/__init__.py`
- `notification_system/tests/integration/test_dispatch_pipeline.py`
- `notification_system/tests/integration/test_rest_api.py`

> **Disjointness note:** `utils/pagination.py`, `config/urls.py`, `config/routing.py`, `config/settings/*`, and `errors/catalog.py` are each owned by exactly ONE subtask (012, 012, 010, 001, 001 respectively). No two subtasks touch the same file. Every per-layer `__init__.py` re-export is bundled with its sibling modules in a single subtask.

---

## Affected files inventory (42 plan files + 3 discovered)

| # | File | Owner | Action |
|---|------|-------|--------|
| 1 | `notification_system/__init__.py` | 001 | Create |
| 2 | `notification_system/apps.py` | 001 | Create |
| 3 | `notification_system/constants.py` | 001 | Create |
| 4 | `notification_system/registry.py` | 003 | Create |
| 5 | `notification_system/adapters.py` | 004 | Create |
| 6 | `notification_system/utils.py` | 005 | Create |
| 7 | `notification_system/consumers.py` | 010 | Create |
| 8 | `notification_system/models/__init__.py` | 002 | Create |
| 9 | `notification_system/models/_notification.py` | 002 | Create |
| 10 | `notification_system/models/_notification_preference.py` | 002 | Create |
| 11 | `notification_system/models/_category_preference.py` | 002 | Create |
| 12 | `notification_system/models/_delivery_log.py` | 002 | Create |
| 13 | `notification_system/services/__init__.py` | 007 | Create |
| 14 | `notification_system/services/_registry.py` | 007 | Create |
| 15 | `notification_system/services/_dispatch.py` | 007 | Create |
| 16 | `notification_system/services/_actions.py` | 007 | Create |
| 17 | `notification_system/services/_preferences.py` | 007 | Create |
| 18 | `notification_system/services/_broadcast.py` | 007 | Create |
| 19 | `notification_system/selectors/__init__.py` | 008 | Create |
| 20 | `notification_system/selectors/_notification.py` | 008 | Create |
| 21 | `notification_system/selectors/_preference.py` | 008 | Create |
| 22 | `notification_system/selectors/_user_roles.py` | 008 | Create |
| 23 | `notification_system/serializers/__init__.py` | 009 | Create |
| 24 | `notification_system/serializers/_notification.py` | 009 | Create |
| 25 | `notification_system/serializers/_preference.py` | 009 | Create |
| 26 | `notification_system/serializers/_category_preference.py` | 009 | Create |
| 27 | `notification_system/controllers/__init__.py` | 012 | Create |
| 28 | `notification_system/controllers/_list.py` | 012 | Create |
| 29 | `notification_system/controllers/_actions.py` | 012 | Create |
| 30 | `notification_system/controllers/_preferences.py` | 012 | Create |
| 31 | `notification_system/urls/__init__.py` | 012 | Create |
| 32 | `notification_system/tasks/__init__.py` | 011 | Create |
| 33 | `notification_system/tasks/_email.py` | 011 | Create |
| 34 | `notification_system/management/__init__.py` | 013 | Create |
| 35 | `notification_system/management/commands/__init__.py` | 013 | Create |
| 36 | `notification_system/management/commands/bootstrap_notification_preferences.py` | 013 | Create |
| 37 | `notification_system/migrations/0001_initial.py` | 006 | Generate |
| 38 | `config/settings/notification_system.py` | 001 | Create |
| 39 | `config/settings/__init__.py` | 001 | Modify (add import) |
| 40 | `config/settings/apps_middlewares.py` | 001 | Modify (`PROJECT_APPS`) — plan said `django.py`; that file does not exist |
| 41 | `config/urls.py` | 012 | Modify (URL include) |
| 42 | `errors/catalog.py` | 001 | Modify (add `NOTIFICATION__NOT_FOUND`) |
| +1 | `notification_system/migrations/__init__.py` | 006 | Create (implicit) |
| +2 | `config/routing.py` | 010 | Modify (ASGI `ws/notifications/` route) |
| +3 | `utils/pagination.py` | 012 | Modify (ADD `parse_page_params`) — NOT pre-existing in DST |

---

## Validation gate (Definition of Done)

```bash
# 1. Import smoke test (Phase 12 plan) — bare `python -c` ignores `--ds`, so EXPORT the settings module
DJANGO_SETTINGS_MODULE=config.django.test uv run python -c "
from notification_system.registry import NotificationTypeRegistry, CATEGORIES
from notification_system.models import Notification, UserNotificationPreference
from notification_system.services._dispatch import dispatch
from notification_system.services._actions import mark_notification_read
from notification_system.services._preferences import bootstrap_notification_preferences
from notification_system.selectors._notification import get_user_notifications_queryset
from notification_system.consumers import NotificationConsumer
print('Phase 12 imports OK')
print(f'Registered types: {len(NotificationTypeRegistry.all_keys())}')
print(f'Categories: {len(CATEGORIES)}')
"

# 2. No missing migrations
uv run python manage.py makemigrations notification_system --check --dry-run --settings=config.django.test

# 3. Management command dry-run (empty registry => "Nothing to bootstrap")
uv run python manage.py bootstrap_notification_preferences --dry-run --settings=config.django.test

# 4. OpenAPI schema valid (controllers touched)
uv run python manage.py spectacular --validate --fail-on-warn --settings=config.django.test

# 5. Full suite; enforces the repo coverage floor (--cov-fail-under=80 in pytest.ini) with
#    notification_system included in --cov (wired in 001). First run may need --create-db.
uv run pytest --ds=config.django.test
```

**Test-command convention:** the repo's `pytest.ini` `addopts` carries `--cov=... --cov-fail-under=80`, so any SCOPED per-subtask run (`pytest notification_system/tests/<layer>/ ...`) would compute coverage over the whole project and false-fail. Every scoped subtask command therefore appends **`--no-cov`**; coverage is enforced ONLY by the full-suite gate (#5 above / subtask 014). The first DB-backed run after the new models land also needs a one-time **`--create-db`** (repo uses `--reuse-db --nomigrations`).

**Done when:** all 5 commands exit 0; registry reports 0 types / 0 categories; existing `notifications` app untouched; no domain (game/AI/elearning/club) references anywhere in `notification_system/`.

---

## Active feature conflicts

Two sibling features are concurrently **Active** in `MASTER_PLAN.md`: `rhitoric-utilities` and `rhitoric-auth-core`. Ownership is disjoint EXCEPT one shared file that must be **serialized** across features:

- **`config/settings/apps_middlewares.py`** — this plan's **001** adds `"notification_system"` to `PROJECT_APPS`; `rhitoric-auth-core/013` adds two `MIDDLEWARE` entries (security-headers + liveness). Disjoint regions (`PROJECT_APPS` vs `MIDDLEWARE`), but the SAME file — the orchestrator MUST serialize the two writers (either order; the second rebases onto the untouched region). `rhitoric-auth-core/MASTER_TASKS.md` documents the same lock.

Otherwise disjoint: `pytest.ini` is owned here by 001 (`rhitoric-utilities`/`rhitoric-auth-core` do not touch it); this plan deliberately does NOT edit `pyproject.toml` (010 uses `asgiref.async_to_sync`, no new dependency), which `rhitoric-auth-core/001` (cryptography) and `rhitoric-utilities/006` (kombu) do. The only other adjacency is the *consumer's* runtime reuse of `rhitoric-auth-core` Phase 5 WS helpers (guarded imports; see below), touching none of this plan's files.

## Cross-plan dependency (documented, non-blocking)

Subtask 010 (consumer) full JWT/subprotocol/`auth_rotate` auth reuses `utils/middleware/jwt_websocket_auth.py`, `utils/websocket/rate_limit.py`, and `utils/websocket/protocol.py` from the SEPARATE `rhitoric-auth-core` plan (Phase 5). **These are absent in DST today.** 010 GUARDS these imports and degrades gracefully (Channels `AuthMiddlewareStack` `scope["user"]`, no subprotocol, `auth_rotate` becomes a no-op/`error`) so this app builds and tests standalone. When `rhitoric-auth-core` Phase 5 lands, the guards activate the richer path with no further change required here.
