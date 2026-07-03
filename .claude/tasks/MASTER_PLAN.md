# Master Plan
Last Updated: 2026-07-03

## Active
- [rhitoric-notification-system](rhitoric-notification-system/MASTER_TASKS.md) — New self-contained `notification_system` app (in-app + email + WebSocket delivery, type/category registry shipped EMPTY, two-level preferences, dedup, delivery logging, role visibility, full REST API, bootstrap command). Backport of RHITORIC_BACKPORT_PLAN Phase 12 (12.1–12.20), generic infrastructure only. 14 subtasks across 5 phases (P1).

> **Cross-feature build order (2026-07-03):** `rhitoric-auth-core` and `rhitoric-utilities` are both COMPLETE and archived; only `rhitoric-notification-system` remains active. Its consumer guard-imports auth-core's now-landed Phase 5 WS helpers.
> - **Remaining shared-file lock:** `config/settings/apps_middlewares.py` — notification-system/001 appends to `PROJECT_APPS`; auth-core/013's `MIDDLEWARE` edit already landed on a disjoint region, so notification-system rebases cleanly. The `pyproject.toml` lock is retired (both prior writers landed).

## Queue
(empty)

## Completed
- [depadrive-backport](depadrive-backport/MASTER_TASKS.md) — Backport 23 Depadrive-core production patterns + app-scaffold update into this template (P1). All 24 subtasks across 4 phases COMPLETED. Final gate: 480 passed / 1 skipped, 85.24% coverage, OpenAPI valid, prod boot assertions pass.
- depadrive-backport — 2026-07-03 — see [.claude/tasks/completed/depadrive-backport.md](completed/depadrive-backport.md)
- rhitoric-auth-core — 2026-07-03 — see [.claude/tasks/completed/rhitoric-auth-core.md](completed/rhitoric-auth-core.md)
- rhitoric-utilities — 2026-07-03 — 9/9 subtasks COMPLETED (Phases 6-11 + app-scaffold). Final gate: 737 passed / 1 skipped, 88.10% coverage, OpenAPI valid, all validation-gate smoke checks green.
- rhitoric-utilities — 2026-07-03 — see [.claude/tasks/completed/rhitoric-utilities.md](completed/rhitoric-utilities.md)

## Deferred / On Hold
(none)
