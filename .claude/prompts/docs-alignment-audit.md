# Documentation alignment audit (parallel, per-app, with verification loop)

---

## Shared orchestration

This prompt follows the **agent orchestration protocol** (`.claude/rules/workflow.md`):
1. **Clarification gate** — after reading the codebase and understanding scope, ask the user if anything is ambiguous (e.g., which doc categories to prioritize, whether to create missing docs or just report gaps). If clear, proceed immediately.
2. **Parallel execution** — Phase 1 agents launch simultaneously. Independent work never waits.
3. **Confirmation gate** — after Phase 3 consolidation, present the summary and ask the user for confirmation before generating an implementation plan for any remaining gaps.
4. **Plan generation** — on confirmation, create `.claude/tasks/<feature>/MASTER_TASKS.md` with parallel groups and subtask files for doc creation, structural improvements, or bug fixes surfaced during the audit.
5. **Parallel implementation + cross-review** — new doc subtasks that don't conflict get their own agent. When an agent finishes, a fresh review agent checks its work.

---

## Purpose

Run a **parallel, multi-agent documentation audit** across the backend. Source code is the **single source of truth** — documentation must reflect actual behavior. Each Django app gets a dedicated agent that reads the code, cross-references all relevant docs, and updates any misaligned documentation. A **verification loop** ensures convergence: after updates, a fresh agent re-checks, and the cycle repeats until docs and code agree.

Documentation is split into two categories:

- **Core docs** — backend architecture, models, services, internal APIs, system behavior (audience: backend developers, operators).
- **Front docs** — endpoint contracts, request/response shapes, WebSocket messages, flows (audience: frontend developers implementing against the API).

---

## Hard constraints (non-negotiable)

1. **Source code is truth.** If docs and code disagree, the docs are wrong — unless the code exhibits a clear bug (wrong logic, crash, security hole, broken invariant). Bugs are **listed in findings**, never patched by this audit.
2. **No code changes.** This audit modifies documentation only.
3. **Doc updates are scoped per app.** Each agent updates docs relevant to its app's domain. Cross-app docs (`docs/README.md`, `docs/central-arch.md`) are handled by the orchestrator after all agents report.
4. **Preserve doc structure.** Update content within existing files. Don't reorganize, rename, or delete doc files unless they describe entirely removed features.
5. **Front docs speak to frontend devs.** They describe what to call, what to send, what to expect back — not internal implementation details.

---

## User prompt for Claude Code (copy from here)

```markdown
You are orchestrating a **parallel documentation alignment audit** of this Django repository.

**Principle:** Source code is the single source of truth. Documentation must match actual behavior.

### Phase 0 — Discover apps and map docs (orchestrator only, fast)
1. Open Django settings and list **project-owned apps** (e.g. `PROJECT_APPS`, `LOCAL_APPS` — exclude pure third-party packages).
2. Map documentation files to apps. A doc file may be relevant to multiple apps — each agent checks its own scope within shared docs.
   - **Core docs**: `docs/*.md`, `docs/<app>/`, `docs/api/`, `docs/deploy/`, `docs/changes/`, `docs/reference_migrations/`, `docs/testing/`, `docs/lessons/`
   - **Front docs**: `docs/front/**/*.md`, plus top-level frontend guides (e.g. `docs/GAME_FRONTEND_ENDPOINTS_AND_FLOW.md`, `docs/REACT_GAME_FLOW_INTEGRATION.md`, `docs/FRONTEND_INTEGRATION_GUIDE.md`, `docs/VOTING_FLOW_FRONTEND.md`, `docs/PVA_FRONTEND_INTEGRATION_GUIDE.md`)
3. Include **`config/`** as its own audit scope: settings, URL routing, middleware, ASGI/WSGI, Celery config, DB routing — mapped against deployment and architecture docs.
4. Include **`utils/`** as its own scope if it is a registered Django app.
5. Output the mapping: `{ app_label: [list of relevant doc files] }`.

### Phase 1 — Spawn parallel doc-audit agents (one per app)
For **each** project app from Phase 0, spawn **one subagent** in parallel. Each subagent receives its app label and the list of relevant doc files.

**Step 1 — Read the source code thoroughly**
Understand the app's actual behavior:
- **Models**: fields, types, relationships, constraints, `clean()`, custom methods, managers
- **Services**: business logic, transaction boundaries, side effects, external calls
- **Selectors**: read queries, filters, prefetch/select tuning
- **Controllers/views**: endpoints (method + path + permissions), request/response shapes, status codes, error codes
- **Serializers**: input/output field names and types, validation rules, nested shapes
- **WebSocket consumers**: message types, event sequences, auth requirements
- **Tasks**: periodic tasks, async operations, retry config, idempotency
- **URLs**: actual route patterns, names, nesting
- **Permissions**: classes, predicates, object-level checks
- **Signals/handlers**: side effects, cache invalidation triggers

**Step 2 — Read and verify every relevant doc file**
For each doc file assigned to this app, cross-reference against the source code:
- Do described endpoints exist? Are HTTP methods, paths, permissions, and throttling correct?
- Do request/response examples match actual serializer fields (names, types, required/optional)?
- Are model fields, relationships, and constraints accurately described?
- Are flows (game flow, auth flow, etc.) consistent with service/controller logic and state transitions?
- Are WebSocket message shapes and event sequences correct?
- Are error codes and HTTP status codes accurate?
- Are listed features actually implemented?
- Are there implemented features or behaviors not mentioned in any doc?

**Step 3 — Identify bugs in source code (do NOT fix)**
While reading code, note any clear bugs:
- Incorrect conditions, dead code paths, security gaps, broken invariants, race conditions
- List each with: location (`path:line`), description, severity

**Step 4 — Update misaligned docs**
- **Core docs**: fix to match actual backend behavior (architecture, models, services, internal APIs, config)
- **Front docs**: fix to match actual endpoint contracts, WebSocket messages, auth flows — write from a frontend developer's perspective
- When a documented feature no longer exists, remove or mark it clearly
- When an undocumented feature exists, note it in the report (new docs are deferred to the user)

**Step 5 — Do NOT update** docs about features owned by other apps, even if you notice issues. Note them as cross-app issues for the orchestrator.

**Deliverable (per app, from each subagent)**
```
## App: <name>

### Bugs found in code (not fixed — for human review)
| Location | Description | Severity |
|----------|-------------|----------|
| path:line | ... | Critical/High/Medium/Low |

### Documentation changes made
| Doc file | What changed | Category |
|----------|-------------|----------|
| docs/... | Updated endpoint X to reflect actual method/path/fields | Front |
| docs/... | Corrected model field descriptions for Y | Core |

### Missing documentation (implemented but undocumented)
| Feature/Behavior | Where in code | Suggested doc location |
|-----------------|---------------|----------------------|
| ... | path:line | docs/... or docs/front/... |

### Cross-app doc issues (for orchestrator)
| Doc file | Issue | Involves apps |
|----------|-------|--------------|
| docs/... | Section about X references stale Y from <other_app> | this_app, other_app |
```

### Phase 2 — Verification loop
After all Phase 1 agents complete:

1. **Orchestrator** resolves cross-app doc issues:
   - Collect all cross-app issues from Phase 1 reports
   - Update shared docs (`docs/README.md`, `docs/central-arch.md`, etc.) using findings from all agents
   - Deduplicate where multiple agents flagged the same shared doc

2. For **each app that had documentation changes** in Phase 1 (or in a prior verification round), spawn a **verification agent** in parallel:
   - **Re-read the app's source code** from scratch (do not trust the prior agent's understanding)
   - **Re-read the updated documentation files**
   - Check every factual claim in the docs against the code
   - If fully aligned: report `✅ ALIGNED` — no edits needed
   - If misaligned: fix the remaining gaps and report what was changed

3. If any verification agent made additional fixes in this round, spawn **another round of verification agents** for those apps only.

4. **Loop terminates** when all verification agents report `✅ ALIGNED` with zero edits.

5. **Safety cap:** maximum **3 verification rounds** per app. If still misaligned after round 3, report remaining gaps to the user as `⚠️ UNRESOLVED`.

### Phase 3 — Final consolidated report
```
# Documentation Alignment Audit — Final Report

## Per-app status
| App | Status | Verification rounds | Docs modified |
|-----|--------|--------------------:|---------------|
| game | ✅ Aligned | 1 | 4 |
| accounts | ✅ Aligned (round 2) | 2 | 2 |
| ai_core | ⚠️ Gaps remain | 3 | 6 |

## Bugs found across all apps (sorted by severity)
| App | Location | Description | Severity |
|-----|----------|-------------|----------|
| ... | ... | ... | ... |

## All documentation files modified
| File | Apps involved | Changes summary |
|------|--------------|----------------|
| ... | ... | ... |

## Undocumented features (need new docs)
| App | Feature | Code location | Suggested doc |
|-----|---------|--------------|---------------|
| ... | ... | ... | ... |

## Unresolved gaps (if any, after safety cap)
| App | Doc file | Remaining issue |
|-----|----------|----------------|
| ... | ... | ... |

## Recommendations
- <structural improvements, missing doc files to create, stale docs to retire>
```

### Phase 4 — Confirmation + plan generation (workflow protocol §3–§4)
After presenting the Phase 3 report:
1. **Ask the user for confirmation** — do they want to proceed with creating missing docs, fixing remaining gaps, or addressing code bugs found during the audit?
2. On confirmation, create `.claude/tasks/<doc_remediation>/MASTER_TASKS.md`:
   - Group independent doc-creation tasks into **parallel groups** (different doc files = different agents).
   - Create subtask files with scope, steps, and validation.
   - Update `MASTER_PLAN.md`.
3. **Execute with parallel agents + cross-review** (workflow protocol §5–§6): implementation agents write docs, review agents verify accuracy against source code.

### Execution notes
- Maximize **parallelism**: all Phase 1 agents launch together; all Phase 2 verifiers for a given round launch together.
- Verification agents **always re-read source code fresh** — never inherit the prior agent's mental model.
- Front docs must be actionable for a frontend developer who has **no access to the backend code**.
- Core docs target backend developers and operators who **do** read the code.
- Preserve each doc file's existing style, formatting, and structure conventions.
- If a doc file covers multiple apps, each app's agent updates only the sections relevant to its domain.

Begin with Phase 0, then Phase 1 in parallel, then Phase 2 verification loop, then Phase 3, then Phase 4 (on confirmation).
```

---

## Optional tweaks (edit before paste)

- **Read-only mode (report only, no edits):** Append to the prompt: `"All subagents produce reports only — zero file edits. Output findings for human review before any changes are made."`
- **Single app focus:** Replace Phase 0 with: `"Audit only the <app_name> app and its related documentation. Skip all other apps."`
- **Front docs only:** Add to each agent: `"Skip core docs. Only audit and update docs/front/ files and top-level frontend guides."`
- **Core docs only:** Add to each agent: `"Skip front docs. Only audit and update backend/architecture documentation."`
- **Update docs/README.md index:** Append to Phase 3: `"Update docs/README.md to reflect any new, removed, or renamed doc files discovered during the audit."`
- **Strict single-round (no loop):** Replace Phase 2 with: `"Run one verification pass. Report remaining gaps without further edits."`

---

## Related project files

- App list: `config/settings/apps_middlewares.py` — `PROJECT_APPS` / `INSTALLED_APPS`
- Doc index: `docs/README.md`
- Frontend docs: `docs/front/`
- Core docs: `docs/*.md`, `docs/<domain>/`
- Code audit prompt: `.claude/prompts/parallel-django-app-audit.md`
- Context snapshot: `.claude/CONTEXT_MAP.md`
