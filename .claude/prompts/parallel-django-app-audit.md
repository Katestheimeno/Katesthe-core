# Parallel multi-agent Django audit (by app)

---

## Shared orchestration

This prompt follows the **agent orchestration protocol** (`.claude/rules/workflow.md`):
1. **Clarification gate** — after reading the codebase and understanding scope, ask the user if anything is ambiguous. If clear, proceed immediately.
2. **Parallel execution** — Phase 1 agents launch simultaneously. Independent work never waits.
3. **Confirmation gate** — after Phase 2 consolidation, present the summary and ask the user for confirmation before generating an implementation plan.
4. **Plan generation** — on confirmation, create `.claude/tasks/<feature>/MASTER_TASKS.md` with parallel groups, dependency graph, and subtask files per the task template.
5. **Parallel implementation + cross-review** — remediation subtasks that don’t conflict get their own agent. When an agent finishes, a fresh review agent checks its work.

---

## Purpose

Run a **read-only / audit-first** pass over the backend: **one parallel subagent per Django application package** (your project’s domain apps under version control). Each agent works **independently** and reports **bugs, inconsistencies, security issues, and performance problems** inside its assigned app (and tightly coupled shared code only when necessary for context).

---

## Hard constraints (non-negotiable)

1. **Do not change public API contracts** under any circumstances:
   - HTTP routes, methods, and path shapes
   - Status codes for existing success and error paths
   - Request and response JSON shapes (field names, nesting, enums) as consumed by clients
   - Pagination, filtering, and sorting **semantics** as documented or clearly relied upon in production
   - WebSocket message contracts where applicable
   - OpenAPI / schema descriptions must remain accurate; **do not “fix” drift by changing the live API** in an audit — report drift instead

2. **Do not change observable behavior** except to **fix a verified bug** (incorrect logic, crash, data corruption risk, security vulnerability, clear spec violation). Refactors, style-only edits, or “cleanups” are **out of scope** unless they are the **minimal** fix for such a bug.

3. **No drive-by edits** outside the finding’s minimal fix. If unsure whether something is a bug, **report it as a finding** with evidence; do not ship a behavioral change.

---

## User prompt for Claude Code (copy from here)

```markdown
You are orchestrating a **parallel, multi-agent audit** of this Django repository.

### Phase 0 — Discover apps (orchestrator only, fast)
1. Open the Django settings and list **project-owned apps** (e.g. `PROJECT_APPS`, `LOCAL_APPS`, or equivalent — exclude pure third-party packages).
2. Treat **`config/`** (settings, URLs, middleware, DB router) as a **separate audit scope** if it is not already an installed app: assign one agent to **`config` + repo-root integration** (Celery, ASGI, Docker entrypoints) as needed.
3. Treat **`utils/`** (or similarly shared libraries) either as **its own agent** or fold into **“cross-cutting”** only if it has no `models/` — choose one strategy and assign exactly one agent so nothing is double-owned.

### Phase 1 — Spawn parallel audit agents
For **each** project app from Phase 0, spawn **one dedicated subagent** in parallel. Each subagent:

**Scope**
- Primary: `<app_label>/` tree (models, managers, selectors, services, controllers/views, serializers, permissions, handlers, tasks, admin, URLs).
- Secondary (read-only context): Only follow imports into other apps **to explain a finding**, not to rewrite them.

**Mission**
Systematically look for:
- **Bugs:** incorrect conditions, races, null/`DoesNotExist` handling, wrong transaction boundaries, double writes, stale reads after write (replica issues if applicable), broken invariants.
- **Inconsistencies:** layering violations (ORM in views when selectors exist), duplicated logic, naming drift, mismatch vs documented flows.
- **Security:** authn/authz gaps, IDOR, mass assignment, unsafe queryset filters, secrets in code, injection (SQL/raw ORM misuse), unsafe uploads, PII in logs, missing throttling on sensitive endpoints.
- **Performance:** N+1 queries, unbounded querysets on list endpoints, missing `select_related`/`prefetch_related`, heavy work in hot paths, missing indexes when clearly needed, inefficient loops hitting DB.

**Out of scope**
- Changing **any** public API contract (see parent instructions).
- Behavior changes unless fixing a **proven** bug with a **minimal** patch (if a subagent proposes a code fix, it must label it **BUGFIX** with repro reasoning).

**Deliverable (per app, from each subagent)**
Produce a structured report:
1. **App:** `<name>`
2. **Summary:** 2–5 bullets
3. **Findings table:** `ID | Severity (Critical/High/Medium/Low) | Category (Bug/Security/Perf/Consistency) | Location (path:line or symbol) | Evidence | Recommendation (audit-only OR minimal BUGFIX)`
4. **Contract / schema drift:** items where **docs or OpenAPI disagree with code** — **report only**, no silent API change.

### Phase 2 — Orchestrator merge
When all subagents return:
1. **Deduplicate** findings that touch the same root cause.
2. **Sort** by severity and risk.
3. **Single summary** for humans: top 10 risks and suggested order of remediation.
4. **Do not** apply fixes yet — present the summary and **ask the user for confirmation** (per workflow protocol §3).

### Phase 3 — Plan generation (on user confirmation)
Follow workflow protocol §4:
1. Create `.claude/tasks/<audit_remediation>/MASTER_TASKS.md` from the prioritized findings.
2. Group independent fixes into **parallel groups** — fixes targeting different apps or files run concurrently.
3. Create numbered subtask files (`001-*.md`, ...) with scope, steps, and validation commands.
4. Update `MASTER_PLAN.md` to set the remediation feature as Active.

### Phase 4 — Parallel implementation + cross-review
Follow workflow protocol §5–§6:
- Spawn **one implementation agent per subtask** within each parallel group.
- When an agent completes, spawn a **fresh review agent** to re-read the changed files, check for bugs, layering violations, and regressions, and verify the subtask's validation passes.
- Serialize subtasks that share files. Parallelize everything else.

### Execution notes
- Maximize **parallelism**: launch all app agents together after Phase 0.
- Keep findings **evidence-based** (file references, short snippets, or test names).
- If an app is large, the subagent may prioritize **controllers → services → selectors → models → tasks** and **permission boundaries** first.

Begin with Phase 0, then Phase 1 in parallel, then Phase 2, then Phase 3 (on confirmation), then Phase 4.
```

---

## Optional tweaks (edit before paste)

- **Include tests:** Add to each subagent: “Mirror `tests/` paths for this app; flag uncovered critical branches.”
- **Strictly no code changes:** Append: “All subagents: **reports only**; zero file edits in this session.”
- **CI / SAST:** Append: “First agent runs `manage.py check`, linters, or security tools if configured; others assume baseline green unless findings say otherwise.”

---

## Related project files

- App list: `config/settings/apps_middlewares.py` (or your settings module) — `PROJECT_APPS` / `INSTALLED_APPS`
- Workflow entrypoint: `.claude/CLAUDE_ENTRYPOINT.md`
- Context snapshot: `.claude/CONTEXT_MAP.md`
