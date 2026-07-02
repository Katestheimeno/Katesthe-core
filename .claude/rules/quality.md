# Quality gates

## Migration Notes

**Source files merged (2):** `quality/06-code-review-checklist.mdc`, `quality/definition-of-done.mdc`.

**Conflicts resolved:** the two sources had 70 % overlap. Merged into one DoD matrix; the code-review checklist is restated as a pre-review subset.

**Deliberately removed:** none.

---

## 1. Definition of Done (DoD)

A change is **done** when **every applicable row** is green. Rows apply conditionally by change class.

### Always

- [ ] Functionality matches acceptance criteria
- [ ] No debug code (`print`, `pdb`, `breakpoint()`)
- [ ] No `TODO` / `FIXME` without a tracked issue link
- [ ] No silent exception swallow — every `except` either logs or re-raises with context
- [ ] Tests added for every new branch (`testing.md`)
- [ ] `uv run pytest --ds=config.django.test` green (see `.claude/skills/run-tests-skill.md`)
- [ ] Docs updated (`docs.md`) — traceability file + `CHANGELOG.md` entry for substantive work
- [ ] `.cursor/changes/YYYY-MM-DD-<slug>.md` session log written (`.claude/skills/session-handoff-skill.md`)

### Changes to HTTP / auth / payment / PII endpoints

- [ ] Object-level authorization verified (IDOR test present)
- [ ] `permission_classes` explicit; no `AllowAny` without rationale
- [ ] No secrets in code or logs
- [ ] Threat checklist completed (`django.md` §1)

### Changes to list / query-heavy code

- [ ] List endpoint paginated
- [ ] No N+1 (debug toolbar or `CaptureQueriesContext` check)
- [ ] Caching applied or intentionally omitted with a written reason
- [ ] Query budget (~10 per endpoint) verified

### Changes to public API (schema, fields, enums, response shapes)

- [ ] OpenAPI schema updated (`@extend_schema` annotations)
- [ ] `uv run python manage.py spectacular --validate --fail-on-warn --settings=config.django.test` exits 0 (`.claude/skills/openapi-validate-skill.md`)
- [ ] Error codes follow `api.md` convention and are registered in `errors/catalog.py`
- [ ] Deprecations marked in schema + `CHANGELOG.md`
- [ ] Additive-only check (no field removal / rename / type change within major version)

### Changes to services, Celery tasks, external-API integrations

- [ ] Important outcomes logged via `config.logger` with structured context
- [ ] Correlation ID propagated (request → task → log)
- [ ] No PII / secrets in logs
- [ ] Idempotency analyzed (payments, notifications, external state)
- [ ] Celery tasks configured with `autoretry_for` / `max_retries` / `retry_backoff`
- [ ] Transactional outbox used for external publishes that must not be lost

### Architecture

- [ ] Layer boundaries respected (no views in services, no services in models — `foundations.md`)
- [ ] Transactions scoped at the service layer
- [ ] Selectors own the reads; services own the writes

### Merge readiness

- [ ] PR title + description clear (`why`, not just `what`)
- [ ] Linked to issue / tracker entry
- [ ] Review feedback addressed or deferred with a written reason

---

## 2. Pre-review checklist (what you verify before you hand off)

Run this against your own diff **before** requesting review. It's the "Always" + the relevant conditional subsets from §1.

If any row is red, fix it rather than flagging it in the PR description.

---

## 3. What makes a PR easy to review

- **Small.** One concern per PR. Refactor-only changes separated from behavior changes.
- **Diff-readable.** Rename → same file. Move → separate commit from edit.
- **Tests alongside the change** — not a follow-up PR.
- **Doc updates in the same PR** — not a follow-up PR.
- **CHANGELOG / traceability** entry in the same PR — this is the only record a release cares about.
