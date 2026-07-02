# Sweep — Deep Analysis Prompt

> **Usage:** `@.claude/prompts/sweep.md <domain | free-text context>`
> **Skill shortcut:** `/sweep <domain | free-text context>`
> **Example:** `/sweep auth`, or `/sweep race conditions in the game consumers`
>
> A sweep runs in one of two modes, resolved by the `/sweep` command before this prompt runs:
> - **Domain mode** — `$LABEL` is a bounded context that maps to Django apps (e.g. `auth`,
>   `game`, `elearning`), and `$CONTEXT` is empty. `$LABEL` ≡ `$DOMAIN`.
> - **Context mode** — `$CONTEXT` is a free-text theme that drives the whole sweep (a
>   concern, pattern, or cross-cutting question), and `$LABEL` is just a short slug naming
>   the output folder.
>
> All output lives under `.claude/sweep/$LABEL/`.

---

## 0 — Bootstrap

1. Determine the inputs from the `/sweep` command:
   - `$LABEL` — the output-folder slug (in domain mode this is the domain name).
   - `$CONTEXT` — the free-text theme in context mode; empty in domain mode.
   - In domain mode, set `$DOMAIN = $LABEL`. In context mode, there is no single domain —
     the **scope** is "every file relevant to `$CONTEXT`".
2. Create the output tree **before** writing anything:

```
.claude/sweep/$LABEL/
  bugs/
  performance/
  security/
  code_quality/
  architecture/
  raw_notes/
```

3. Remind yourself: you are a **first-pass analyst**, not a fixer. Your job is to
   observe, document, and hand off — not to change production code.
4. Record the sweep start time, the mode (domain vs context), and `$LABEL`/`$CONTEXT` in `raw_notes/00_project_orientation.md`.

---

## 1 — Understand the Project Layout

Before touching `$DOMAIN`-specific code, orient yourself:

- Read `README.md`, `docs/README.md`, any ADR files, and `.claude/CONTEXT_MAP.md`.
- Read `.claude/rules/foundations.md` to understand architecture conventions:
  - `selectors.py` / `services.py` / `controllers/` separation
  - `filters.py`, `serializers.py`, `admin.py` patterns
  - Where business logic is expected to live vs. where it must **not** live
    (e.g. logic must not leak into serializers or views).
- Note the Django version, DRF version, auth backends, and permission framework
  from `config/settings/` files.
- Identify the DB routing strategy (`config/db_router.py`, `config/db_utils.py`).
- Write a 10–20 line orientation summary to `.claude/sweep/$LABEL/raw_notes/00_project_orientation.md`.

---

## 2 — Map the Scope

Locate every file in scope.

**Domain mode** — every file that belongs to or is consumed by `$DOMAIN`:

- Django apps whose name or purpose is directly related to `$DOMAIN`.
- Any cross-cutting files that reference `$DOMAIN` models, signals, tasks, or constants
  (search imports, string literals, `related_name` references).
- URL confs, middleware, and settings blocks tied to this domain.
- Celery tasks and beat schedules for this domain.
- WebSocket consumers, routing, and channel layers.
- Tests: unit, integration, e2e — note coverage gaps immediately.
- Migrations: flag any with `RunPython`, schema changes to sensitive tables,
  or missing `db_index` / `unique_together` on high-traffic fields.
- Admin registrations and custom admin actions.

**Context mode** — every file relevant to `$CONTEXT`:

- Extract the key models, patterns, and symbols named or implied by `$CONTEXT`, then
  grep/trace for them across the apps (call sites, definitions, related abstractions).
- Cast a wide net first, then prune to files that genuinely bear on the theme. When in
  doubt, include the file and note why it's in scope.
- Include the same cross-cutting Django surfaces as domain mode (URLs, Celery tasks,
  consumers, tests, migrations, admin) wherever they intersect the theme.
- If the theme is genuinely project-wide, partition the scope into coherent areas so the
  analysis passes stay focused rather than skimming everything shallowly.

Write the full file list to `.claude/sweep/$LABEL/raw_notes/01_domain_map.md`, organized by layer:
```
## Models
## Services
## Selectors
## Controllers / Views
## Serializers / Schemas
## Permissions
## Filters
## Handlers / Signals
## Tasks
## Admin
## URLs
## Tests
## Migrations
## Cross-cutting references (other apps importing from $DOMAIN)
```

---

## 3 — Bug Pass

Read every file in the domain map **line by line**. For each potential bug, create a
**separate file** inside `.claude/sweep/$LABEL/bugs/` named:

```
BUG-<NNN>_<short-slug>.md
```

Each bug file **must** contain:

```markdown
# BUG-<NNN>: <one-line title>

## Severity
<!-- CRITICAL | HIGH | MEDIUM | LOW -->

## File & Line(s)
<!-- exact path(s) and line range -->

## Code Snapshot
<!-- paste the relevant snippet verbatim — do NOT paraphrase -->

## Context
<!-- Explain what the surrounding code is trying to do, what invariants
     are expected, and what architectural layer this lives in. -->

## Observed Problem
<!-- What is wrong. Be specific: wrong query, missing null-check,
     race condition, incorrect ORM usage, etc. -->

## Reproduction Path
<!-- How a caller would trigger this. Step by step if possible. -->

## Why This Is NOT a False Positive
<!-- Pre-argue your case for the reviewer. Cite Django/DRF/Python docs
     or known CVEs where applicable. -->

## Impact
<!-- What breaks or leaks if this fires in production. -->

## Confidence
<!-- HIGH | MEDIUM | LOW — how sure are you this is real? -->
```

Categories to hunt in the bug pass (not exhaustive — use judgment):

- Incorrect ORM queries (`.filter()` vs `.get()`, missing `.select_related`,
  N+1 producing wrong data, not just slowness).
- Missing atomicity (`@transaction.atomic` absent on multi-step writes).
- Signal handlers that silently swallow exceptions.
- Celery tasks that are not idempotent but are retried without guards.
- Serializer `validate_*` methods that have incorrect logic or bypass field validation.
- Permission checks that are present in the view but missing in the service layer
  (direct service calls from other services or management commands).
- Missing `select_for_update()` on objects updated concurrently.
- Hardcoded secrets, tokens, or environment-specific strings in source files.
- Exception handlers that catch `Exception` broadly and hide real errors.
- Django `Q` object logic errors (wrong operator precedence).
- Model `save()` overrides with side-effects that bypass `update()` calls.
- Race conditions between read-check-write sequences.
- Stale reads after writes on replica databases (missing `read_from_primary`).
- WebSocket handlers that don't validate incoming message shapes.
- Celery tasks enqueued outside `transaction.on_commit` (can fire before the transaction commits).
- `DoesNotExist` / `MultipleObjectsReturned` unhandled in services.
- Incorrect use of `bulk_create` / `bulk_update` (missing `update_fields`, ignoring return values).

---

## 4 — Performance Pass

For each performance issue found, create a file in `.claude/sweep/$LABEL/performance/`
named `PERF-<NNN>_<short-slug>.md` with this structure:

```markdown
# PERF-<NNN>: <one-line title>

## Impact Estimate
<!-- HIGH (blocking) | MEDIUM (noticeable) | LOW (minor) -->

## File & Line(s)

## Code Snapshot

## Context

## Problem
<!-- N+1, missing index, full-table scan, unbounded queryset, sync I/O
     in request cycle, large serialization payload, etc. -->

## Evidence / Reasoning
<!-- Why this will be slow at real-world data volumes.
     Include estimated row counts or query patterns if possible. -->

## Suggested Direction
<!-- One sentence — do not write the fix, just point the way. -->

## Confidence
<!-- HIGH | MEDIUM | LOW -->
```

Areas to inspect:

- `select_related` / `prefetch_related` usage on querysets that traverse FK/M2M.
- Querysets inside loops (classic N+1).
- Missing database indexes on fields used in `filter()`, `order_by()`, `annotate()`.
- Synchronous external HTTP calls inside view/service without background task offload.
- Unbounded list endpoints (no pagination or very high default page size).
- Heavy aggregations run in the request cycle instead of pre-computed.
- Django ORM `.values()` vs full model hydration — unnecessary column fetching.
- Cache misuse: no cache where one is warranted; stale cache where invalidation is missing.
- Large `JSONField` reads where only a subset is needed.
- Inefficient serializer nesting (deep `SerializerMethodField` chains hitting the DB).
- Missing `only()` / `defer()` on large text/JSON columns in list views.

---

## 5 — Security Pass

For each security issue found, create a file in `.claude/sweep/$LABEL/security/`
named `SEC-<NNN>_<short-slug>.md` with this structure:

```markdown
# SEC-<NNN>: <one-line title>

## CVSS-like Severity
<!-- CRITICAL | HIGH | MEDIUM | LOW | INFORMATIONAL -->

## CWE / OWASP Reference
<!-- e.g. CWE-89, OWASP A01:2021 -->

## File & Line(s)

## Code Snapshot

## Context

## Vulnerability Description

## Attack Scenario
<!-- Concrete, step-by-step. Assume a motivated attacker with a valid account. -->

## Proof of Concept (if applicable)
<!-- curl command, API call sequence, or test pseudocode -->

## Recommended Direction

## Confidence
<!-- HIGH | MEDIUM | LOW -->
```

Security checklist for Django/DRF projects:

- Authentication & session: JWT expiry, refresh token rotation, session fixation,
  `HttpOnly` / `Secure` cookie flags, `SECURE_*` settings in production.
- Authorization: IDOR (object-level permission missing in service layer),
  horizontal privilege escalation, missing `IsAuthenticated` on non-public endpoints.
- Input validation: SQL injection via raw queries, unvalidated `order_by` parameters
  accepting arbitrary field names, mass assignment via `fields = '__all__'`.
- Password handling: PBKDF2/Argon2 usage, minimum complexity enforcement,
  password exposed in logs or serializer output.
- Secrets: `SECRET_KEY` rotation, API keys in source, `.env` committed.
- File uploads: unrestricted MIME types, path traversal in file names,
  serving user uploads via Django (should be behind CDN/nginx).
- CSRF: exemptions on mutation endpoints without a compensating auth check.
- Rate limiting: brute-force on login/password-reset/OTP endpoints.
  Check `throttle_classes` on every write endpoint.
- Dependency CVEs: flag known-vulnerable packages found in `requirements*.txt` / `pyproject.toml`.
- WebSocket auth: JWT validation on connect, no anonymous consumers for protected data.
- Serializer field exposure: `read_only_fields` missing for privileged fields (`is_staff`, `is_superuser`, etc.).
- Admin actions: staff-only operations that don't verify superuser status for superuser-affecting actions.
- Celery task argument injection: tasks that accept user-controlled payloads without validation.

---

## 6 — Code Quality Pass

Create files in `.claude/sweep/$LABEL/code_quality/` named
`CQ-<NNN>_<short-slug>.md` using this template:

```markdown
# CQ-<NNN>: <one-line title>

## Category
<!-- ARCH_VIOLATION | DEAD_CODE | DUPLICATION | TEST_GAP |
     ERROR_HANDLING | TYPING | NAMING | COMPLEXITY -->

## File & Line(s)

## Code Snapshot

## Context

## Issue Description

## Convention Violated (if applicable)
<!-- Reference the specific convention from .claude/rules/:
     e.g. "Business logic must live in services.py, not in serializers."
     or "Selectors own reads, services own writes (foundations.md §2)" -->

## Suggested Direction

## Confidence
<!-- HIGH | MEDIUM | LOW -->
```

Quality areas to inspect:

- Business logic leaking into views, serializers, or signals (belongs in services).
- Selectors performing writes or calling services (wrong direction).
- Dead code: unused imports, unreachable branches, commented-out blocks.
- Duplicated logic that should be extracted to a shared service/selector/utility.
- Missing test coverage for critical branches (new `if/else`, `try/except`, early returns).
- Bare `except Exception` or `except:` blocks that swallow context.
- Missing type hints on public function signatures.
- Inconsistent naming patterns within the domain.
- Overly complex functions (high cyclomatic complexity, deeply nested).
- Models with business logic in `save()` that should be in services.

---

## 7 — Architecture Pass

Create files in `.claude/sweep/$LABEL/architecture/`
named `ARCH-<NNN>_<short-slug>.md`:

```markdown
# ARCH-<NNN>: <one-line title>

## Severity
<!-- STRUCTURAL | MODERATE | MINOR -->

## Affected Layer(s)
<!-- e.g. service ↔ selector boundary, domain ↔ domain coupling -->

## Description

## Concrete Example (file + line)

## Downstream Risk
<!-- What breaks or becomes unmaintainable if left alone. -->

## Suggested Direction

## Confidence
<!-- HIGH | MEDIUM | LOW -->
```

Look for:

- Business logic leaking into views, serializers, or signals.
- Selectors calling services (wrong direction — foundations.md §2).
- Circular imports between domain apps.
- God services / god models doing too much.
- Domains importing directly from other domain internals instead of
  using public service/selector interfaces.
- Missing or incorrectly scoped `AppConfig.ready()` signal connections.
- Transaction boundaries at the wrong layer (in views instead of services).
- Direct `request` object access in services (HTTP coupling).
- Missing abstraction boundaries for external API integrations.

---

## 8 — Verification by Fresh Agent

When all finding files are written, hand off to a **new subagent** with this exact
instruction block (fill in `$DOMAIN`):

---

**REVIEWER SUBAGENT INSTRUCTIONS**

You are a senior Django engineer performing a quality gate on automated findings.
Your job is to **verify**, **dismiss false positives**, and **promote real issues**.

1. Read `.claude/sweep/$LABEL/raw_notes/00_project_orientation.md` and
   `.claude/sweep/$LABEL/raw_notes/01_domain_map.md` to orient yourself.

2. For every finding file across `bugs/`, `performance/`, `security/`,
   `code_quality/`, and `architecture/`:
   - Re-read the **Code Snapshot** against the **actual file on disk** at the cited line numbers.
   - Verify the code actually does what the finding claims.
   - Check if the issue has already been mitigated elsewhere (middleware, base class, decorator).
   - Decide: **CONFIRMED** | **FALSE_POSITIVE** | **NEEDS_MORE_INFO**.
   - Append a `## Reviewer Verdict` section to the file:

     ```markdown
     ## Reviewer Verdict
     **Status:** CONFIRMED | FALSE_POSITIVE | NEEDS_MORE_INFO
     **Reasoning:** <one paragraph — cite code or docs, explain WHY you agree or disagree>
     **Adjusted Severity (if changed):** <new severity or "unchanged">
     **Confidence Override (if changed):** <new confidence or "unchanged">
     ```

3. Write a summary to `.claude/sweep/$LABEL/raw_notes/02_reviewer_summary.md`:
   - Total findings by category.
   - Confirmed vs. dismissed vs. needs-more-info counts.
   - Top 5 most critical confirmed findings (ranked by severity × confidence).
   - Any patterns or systemic issues noticed across multiple findings.
   - False positive rate and what caused them.
   - Recommendations for the remediation plan.

4. Stop. Do not fix anything. Do not modify production code.

---

## 9 — Task Generation

After the reviewer subagent completes `02_reviewer_summary.md`, read:

- All **CONFIRMED** finding files across all categories.
- `02_reviewer_summary.md`.

Then generate execution plans for all confirmed findings:

1. **Create** `.claude/tasks/$LABEL-sweep-remediation/MASTER_TASKS.md` in the canonical
   format produced by `/flow pln`:
   - `Priority:`/`Status:` header lines, goal, and locked decisions
   - Priority queue table: `ID | Subtask | Phase | Parallel group | Findings` (no status column)
   - The machine-readable `## Subtasks` bullet list — `- [PENDING] [NNN-slug.md](NNN-slug.md) — title`
     (status token: `PENDING | IN_PROGRESS | BLOCKED | COMPLETED | SKIPPED | DEFERRED`).
     This is what the orchestrator and `/flow cmplt` consume, so it is mandatory.
   - Execution dependency graph showing which subtasks can run concurrently
   - File ownership table (strictly disjoint — no two subtasks touch the same file)
   - Validation gate (Definition of Done for the remediation)

2. **Group findings** into logical work packages where fixes are related:
   - Same file → same subtask
   - Same layer/concern → same subtask (unless files conflict)
   - Security fixes grouped by endpoint or permission boundary
   - Keep each subtask focused: 1–5 findings per subtask

3. **Order by risk-adjusted priority:**
   CRITICAL security > CRITICAL bugs > HIGH bugs > HIGH security >
   MEDIUM everything else > LOW/CQ/ARCH

4. **Create numbered subtask files** (`001-*.md`, `002-*.md`, ...) with:
   ```markdown
   # NNN — <title>

   **Status:** [PENDING]
   **Phase:** <N>
   **Group:** <letter>
   **Findings:** <list of finding IDs this subtask addresses>

   ## Problem
   <what's wrong, citing finding files>

   ## Files Owned
   <exact paths this subtask may modify — disjoint with other subtasks>

   ## Fixes
   ### Fix 1 — <description>
   <what to change and where>

   ## Tests
   <what tests to add or modify>

   ## Validation
   ```bash
   <specific test commands to verify this subtask>
   ```
   ```

5. **Review the plan.** Dispatch the `plan-reviewer` agent at
   `.claude/tasks/$LABEL-sweep-remediation/` and apply its amendments — this is what
   enforces the strictly-disjoint file-ownership gate this sweep promises. One round is the
   minimum; run a second if the first surfaces blocking items.
6. **Update** `.claude/tasks/MASTER_PLAN.md` — add the new remediation feature as Active.

---

## 10 — Stop

Once the task plan has been generated and `MASTER_PLAN.md` updated, **stop**.

Do not implement fixes. Do not open PRs. Do not modify any production file.
Your deliverables are:
- The finding files (with code snapshots and evidence)
- The reviewer verdict annotations
- The reviewer summary
- The task plan with numbered subtask files
- The updated MASTER_PLAN.md

Everything else is out of scope for this sweep.

---

*Prompt version: 2.0 — enhanced with confidence scoring, reviewer quality gate, structured task generation, and file ownership disjointness*
