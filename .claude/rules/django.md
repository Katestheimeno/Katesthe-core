# Django — security, performance, DB routing, observability

## Migration Notes

**Source files merged (6):** `django/00-django-security.mdc`, `django/00-django-performance.mdc`, `django/02-model-context.mdc`, `django/05-django-best-practices.mdc`, `django/12-db-routing-primary-replica.mdc`, `django/observability.mdc`.

**Conflicts resolved:** `django/00-django-patterns-decision-guide.mdc` moved to `foundations.md` (layering canon). `django/00-django-docs-changelog.mdc` moved to `docs.md`. The layer-level rules themselves (import direction, transactions, read-after-write) live in `foundations.md`; this file is Django-runtime specifics.

**Deliberately removed:** none — all content survives, consolidated per-topic.

---

## 1. Security — hard requirements

- **Every view declares `permission_classes`.** No `AllowAny` without a documented reason. Public endpoints (registration, token obtain) are the only permitted exceptions and must be explicit.
- **Object-level authorization (IDOR).** Scope queries to `request.user` before `.get(pk=pk)`:
  ```python
  review = Review.objects.filter(client=request.user).get(pk=pk)
  ```
- **Validate all input through serializers / schemas.** Never `MyModel.objects.create(**request.data)`.
- **Secrets via environment.** `django-environ` / pydantic settings. Never hardcode. `.env.*.example` in git; real `.env*` in `.gitignore`.
- **Never log PII, passwords, tokens, or raw `request.data` / `request.query_params`.**
- **Dangerous builtins banned on user input:** `eval`, `exec`, `pickle.loads`.
- **Rate-limit sensitive endpoints** (auth, OTP, AI ingest, expensive list endpoints). Declare throttle classes on the view or scope in DRF settings—follow existing examples in `accounts/` / `game/` / `ai_core/`.
- **Run the threat checklist** on every auth, payment, or PII endpoint before merge.

## 2. Performance — hard requirements

- **List endpoints MUST be paginated.** No unbounded querysets to the wire.
- **No N+1.** Push `select_related` (FK / O2O) and `prefetch_related` (M2M / reverse FK) into manager or selector methods so every caller benefits.
- **Prefer DB-side aggregation.** `Count`, `Sum`, `F`, `Subquery`. Python aggregation over large QuerySets is a bug.
- **`.exists()`, never `.count() > 0`.**
- **Trim columns.** `.only()` / `.defer()` on heavy fields (long text, JSON blobs).
- **Declare a query budget per endpoint** (~10 is a sensible default). Anything higher needs a written justification.
- **Cache explicitly.** Never infinite TTL. Document invalidation.

## 3. Models — read first, then use

- **Open the model file** before referencing a model — fields, relationships, custom methods, `clean()`, `__str__`.
- **Prefer existing model methods** over duplicating logic.
- **Every model implements `__str__`.**
- **Business logic, email, external API calls MUST NOT live in `Model.save()`.** Put them in a service; call them explicitly.
- **Use `clean()` for single-aggregate invariants** — things the row can validate on its own.

## 4. Managers & QuerySets

- **Custom managers** for chainable QuerySet operations reused across selectors.
- **Model methods** for instance-level logic (one row's business rules).
- **Include `select_related` / `prefetch_related` inside the manager method** so every caller is N+1-safe by default.

## 5. Signals — scope and discipline

- **Use for:** cross-app cache invalidation, audit logging, lightweight side effects that don't need transaction guarantees.
- **Do NOT use for:** business logic, critical operations, anything that must be transactional (use a service).
- **Signal handlers are lightweight.** Delegate heavy work to a Celery task inside the handler.
- **Document signal dependencies** in the app's `handlers/__init__.py` docstring.

## 6. DB routing — primary / replica

**Router:** `config/db_router.py` (`PrimaryReplicaRouter`). Controlled by `DB_ROUTING_ENABLED` (default `true`).

- Default reads → replica (if configured); writes → primary.
- **After writes, use** `with read_from_primary(): ...` (from `config/db_utils.py`) to avoid stale replica reads.
- **Never hardcode** `.using("primary")` or `.using("replica_0")`. Let the router decide.
- **Migrations** always run against primary — no router override needed.

## 7. Observability — structured logging

- **Import logger from** `config.logger` — `from config.logger import logger`. Never `logging.getLogger`.
- **Structured context via `.bind()`:**
  ```python
  logger.bind(user_id=uid, order_id=oid).info("order.created")
  ```
- **Correlation IDs propagate** across request → Celery task headers → log records. Include in every service-level log.
- **Never log** passwords, tokens, full PII, full `request.data`. Redact aggressively.
- **Event-name convention:** `<domain>.<action>` — lower_snake with dot separator (`ably.publish_ok`, `auth.login_failed`).
