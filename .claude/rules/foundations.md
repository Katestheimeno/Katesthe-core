# Foundations

## Migration Notes

**Source files merged (9):** `foundations/00-universal-django-architecture.mdc`, `foundations/architecture-boundaries.mdc`, `foundations/design-philosophy.mdc`, `foundations/context-awareness-rule.mdc`, `foundations/07-context-references.mdc`, `foundations/00-django-reuse-awareness.mdc`, `foundations/00-stop-and-ask-scenarios.mdc`, `foundations/01-planning-workflow.mdc`, `django/00-django-patterns-decision-guide.mdc`.

**Conflicts resolved:**
- **C1** (layering restated in foundations + django best-practices + patterns guide): one canonical import-direction table lives here; `django.md` cross-references.
- **C2** (three overlapping "read before you act" files): consolidated into a single *Context & reuse* section; all three checklists preserved, dedup only wording.
- **C3** (three "when to pause" files): unified list of 15 stop-triggers under *Planning & stop-triggers*; the audit-loop loop itself is extracted to `.claude/skills/audit-loop-skill.md`, the rule that you **must** run the loop stays here.

**Deliberately removed:** `00-README-universal-rules.mdc` (its role is superseded by `CLAUDE.md`'s Rule & Skill Index); Cursor frontmatter (`description`, `globs`, `alwaysApply`) stripped from all sources.

---

## 1. Core principles

1. **Distrust all input.** Validate at the boundary via serializers / Pydantic schemas — never pass `request.data` straight to `.create()` / `.update()`.
2. **Authorize before you query.** IDOR first, data second. Scope `.filter(owner=request.user)` before `.get(pk=pk)`.
3. **Expose the minimum.** No sensitive fields leak into responses. No prose in error bodies — frontend owns i18n.
4. **Layers are inviolable.** If a shortcut tempts you, the design is wrong. Import direction flows inward only.
5. **Selectors own reads. Services own writes + transactions.** Models own aggregate invariants (`clean()`), not side effects.
6. **N+1 is a bug. Pagination is mandatory.** Declare query budget per endpoint; verify in dev.
7. **Side effects are auditable.** Every log, signal, task is traceable by `correlation_id`.
8. **API evolution is additive.** Within a major version, you MUST NOT remove or rename published fields, narrow enums, or change types.
9. **Tests verify behavior, not decoration.** Cover every branch you add (100% for new code; repo floor 75%).
10. **Docs ship with the code.** Stale docs are lies — refactor docs in the same PR as the code.

## 2. Architecture — strict layering

Import direction flows **inward only**.

| Layer | Owns | May import | MUST NOT |
|---|---|---|---|
| **Controllers** (`*/views.py`, `*/controllers/`) | DRF views/viewsets, routing, HTTP response shape, permission checks | services, selectors, serializers, permissions, schemas | raw ORM writes, business logic, data transformation beyond API contract |
| **Services** (`*/services/`) | orchestration, transactions, external API calls, event dispatch, Celery task enqueues | selectors, models, tasks, cache, external clients, domain helpers | views, serializers, `request` objects (no HTTP coupling) |
| **Selectors** (`*/selectors/`) | **all** read queries, `select_related` / `prefetch_related` tuning, query reuse | models, ORM, helpers | writes, business rules, view/controller code |
| **Models** (`*/models/`) | single-aggregate invariants, `clean()`, instance methods, custom managers | fields, relationships | services, views, email, external APIs, Celery enqueues inside `save()` |
| **Serializers / Schemas** (`*/serializers/`, `*/schemas/`) | DRF input/output shaping; Pydantic for complex validation | validators | DB writes — services do that |

**Transactions:** wrap multi-step writes in `transaction.atomic()` at the **service layer**, not in views.

**Read-after-write:** replica reads can be stale right after a write. Use `with read_from_primary():` (from `config/db_utils.py`) when you need to re-read what you just wrote. Never hardcode `.using("replica_0")` / `.using("primary")`.

## 3. Context & reuse — read before you add

Before writing any non-trivial code:

1. **Read the current state.** Open the model, service, or view you are about to touch. Do not assume from the filename.
2. **Search for reuse.** If you are about to write "get user by X" or "send notification for Y", `Grep` the repo first — it probably exists as a selector or in `notifications.services.notify_dispatch`.
3. **Check project references.** Domain facts (error codes, event codes, valid enum values) live in `errors/catalog.py`, `notifications/services/push.py`, `notifications/services/notify_dispatch.py`, and the matching tracker entries. Use them, don't restate them.
4. **Respect `.cursor/changes/`.** Every session log records decisions that are already made. Do not re-litigate (payments = cash MVP; client REST deferred; dual envelope representation; Ably outbox pipeline).
5. **Honor CLAUDE.md's "Do Not" list.** It is the fast cache of past mistakes.

## 4. Planning & stop-triggers

Before coding, pause and ask when any of these are unclear — the cost of a wrong assumption is high:

1. **New app vs. new module in existing app.**
2. Introducing a **new pattern** vs. following an existing one.
3. **Model relationship cardinality** (FK / M2M / O2O) and field types (CharField vs. TextField vs. JSONField; expected size and query pattern).
4. **Where logic lives** — service vs. model method vs. manager vs. selector.
5. **Serializer shape** — new action serializer vs. reuse/extend existing.
6. **Permission model** — authenticated / owner / admin / custom predicate.
7. **Caching** — what / TTL / invalidation strategy.
8. **Sync vs. async** — background task vs. inline request.
9. **Code duplication** — extract to shared utility or keep separate.
10. **Naming** — does this match existing patterns?
11. **Test placement + coverage** — what branches need tests?
12. **Security-sensitive endpoints** (auth, payment, PII) — threat checklist.
13. **External integrations** — credentials configured? failure mode? retry?
14. **Breaking change** — is this additive or does it change existing contracts?
15. **Idempotency** — needed for payments, notifications, external state changes?

For every non-trivial task: understand context → discover reuse → validate layer placement → implement → run the **audit loop** (`.claude/skills/audit-loop-skill.md`).

## 5. Decision guide — where does this code go?

| Operation | Lives in | Example |
|---|---|---|
| "Get active users by email" | selector | `accounts/selectors/user.py::get_active_user_by_email` |
| "Send welcome email after signup" | service | `accounts/services/` (or equivalent) calling notification utilities |
| "Validate debate topic slug uniqueness" | serializer `validate_*` / model constraint | `game/` serializers or models |
| "User can only see own game history" | permission + selector filter | scope queryset to `request.user` |
| "Expire abandoned PvP waiting games" | Celery task + beat | `game/flow.py` + Celery beat entry (see game flow docs) |
| "Broadcast game phase change over websocket" | Channels consumer / signal → async send | `game/` websocket handlers |
| "Refresh derived stats after vote" | service call | `game/services/` (or dedicated analytics service) |
| "Cross-app side effect (cache invalidation)" | signal handler | `*/handlers/`, delegate heavy work to a task |

**If you can't place an operation in the table above, stop and ask.**
