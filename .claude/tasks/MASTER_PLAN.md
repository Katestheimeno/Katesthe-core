# Master Plan
Last Updated: 2026-07-03

## Active
- [rhitoric-auth-core](rhitoric-auth-core/MASTER_TASKS.md) — Backport RS256 JWT + JWKS/`kid`, HttpOnly-cookie auth with CSRF + `X-Token-Delivery` opt-out, session revocation/refresh-reuse detection, the ~14-class throttle architecture with a global toggle, and WebSocket JWT auth infrastructure. RHITORIC_BACKPORT_PLAN Phases 1–5, generic patterns only; RS256 is an approved breaking change (auth tests rewritten). 24 subtasks across phases 1/4/2/3/5 + gate (P1). Cross-feature serialization hazards on `pyproject.toml` and `config/settings/apps_middlewares.py`; `config/settings/celery.py` ceded to rhitoric-utilities/006 (see its Active feature conflicts).
- [rhitoric-utilities](rhitoric-utilities/MASTER_TASKS.md) — Backport generic operational utilities (Phases 6-11 + app-scaffold) from Rhitoric-core: safe Celery dispatch, external-API health-check skeleton, test throttle override, Pydantic↔spectacular bridge, keep-warm task, admin click-to-copy mixin, Celery priority queues/routing, enhanced SoftDelete/BooleanChoices mixins (P1). 9 subtasks, one parallel group.
- [rhitoric-notification-system](rhitoric-notification-system/MASTER_TASKS.md) — New self-contained `notification_system` app (in-app + email + WebSocket delivery, type/category registry shipped EMPTY, two-level preferences, dedup, delivery logging, role visibility, full REST API, bootstrap command). Backport of RHITORIC_BACKPORT_PLAN Phase 12 (12.1–12.20), generic infrastructure only. 14 subtasks across 5 phases (P1).

> **Cross-feature build order (all three split from one backport plan):**
> - **Recommended sequence:** `rhitoric-auth-core` first (throttles + WS infra are consumed by the others), then `rhitoric-notification-system` (its consumer guard-imports auth-core's Phase 5 WS helpers) and `rhitoric-utilities` (its Phase 10 celery routing references auth-core's `flush_expired_jwt_tokens` task by name). All soft — each plan builds standalone via guarded imports / by-name routing.
> - **Two hard shared-file locks the orchestrator MUST serialize** (disjoint regions, same file): `pyproject.toml` (auth-core/001 `cryptography` ↔ utilities/006 `kombu`); `config/settings/apps_middlewares.py` (auth-core/013 `MIDDLEWARE` ↔ notification-system/001 `PROJECT_APPS`). `config/settings/celery.py` is owned solely by utilities/006 (auth-core references its task by name only).

## Queue
(empty)

## Completed
- [depadrive-backport](depadrive-backport/MASTER_TASKS.md) — Backport 23 Depadrive-core production patterns + app-scaffold update into this template (P1). All 24 subtasks across 4 phases COMPLETED. Final gate: 480 passed / 1 skipped, 85.24% coverage, OpenAPI valid, prod boot assertions pass.
- depadrive-backport — 2026-07-03 — see [.claude/tasks/completed/depadrive-backport.md](completed/depadrive-backport.md)

## Deferred / On Hold
(none)
