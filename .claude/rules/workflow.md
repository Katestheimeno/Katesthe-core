# Agent orchestration protocol

## Migration Notes

**New file.** Defines the shared workflow that all prompts and multi-step tasks follow: clarification gate, parallel execution, confirmation, plan generation, parallel agents, and cross-review.

---

## 1. Clarification gate — ask before you build

After reading context and understanding the task:

1. **Identify unknowns.** List anything ambiguous: scope boundaries, naming choices, architectural decisions, dependencies on unfinished work, unclear acceptance criteria.
2. **If unknowns exist:** ask the user concise, specific questions. Do not guess. Do not proceed until answers are in.
3. **If everything is clear:** state your understanding in 2-3 sentences and move to parallel execution immediately. Do not ask for permission to start — clarity is the gate, not approval.

## 2. Parallel-first execution

Once the task is understood:

- **Identify independent work streams.** Any reads, audits, analyses, or implementations that touch different files or domains can run simultaneously.
- **Spawn one agent per independent stream.** Use `subagent_type` appropriate to the work (Explore for search, general-purpose for mixed, Plan for architecture).
- **Never serialize what can parallelize.** If three apps need auditing, three agents launch in one message. If models and admin can be built without conflict, they get separate agents.
- **Agents that share write targets must be serialized.** Two agents editing the same file is a conflict — queue them.

## 3. Confirmation gate — present findings, get go-ahead

After parallel work completes (audit, research, analysis):

1. **Consolidate results** into a brief summary for the user: key findings, decisions needed, proposed approach.
2. **Ask for confirmation** before generating the implementation plan. The user may want to adjust scope, reprioritize, or skip items.
3. **Do not auto-generate a plan without confirmation.** The transition from "understanding" to "building" requires explicit user approval.

## 4. Plan generation — `.claude/tasks/` pattern

On user confirmation, generate a plan following the established task structure:

1. **Create** `.claude/tasks/<feature>/MASTER_TASKS.md` with:
   - `Priority:`/`Status:` header lines, goal, and locked decisions
   - Priority queue table: `ID | Subtask | Phase | Parallel group` (no status column)
   - The machine-readable `## Subtasks` bullet list — `- [PENDING] [NNN-slug.md](NNN-slug.md) — title`
     (status token: `PENDING | IN_PROGRESS | BLOCKED | COMPLETED | SKIPPED | DEFERRED`).
     This is the canonical status source the orchestrator, the progress hooks, and
     `/flow cmplt` all read — it is mandatory.
   - Execution dependency graph showing which subtasks can run concurrently
   - Affected files inventory
   - Validation gate (Definition of Done for the feature)
2. **Create subtask files** (`001-*.md`, `002-*.md`, ...) per the subtask template in `CLAUDE_ENTRYPOINT.md` (or via the `/flow pln` command).
3. **Update** `.claude/tasks/MASTER_PLAN.md` — set the new feature as Active.
4. **Maximize parallel groups.** Every subtask that does not depend on another's output belongs in a concurrent group. Label groups (A, B, C, ...) and document the dependency edges.

## 5. Parallel implementation agents

During execution of the plan:

- **Each parallel group** spawns one agent per subtask (or per logical cluster if subtasks share a file).
- **Agents receive** their subtask file path, the MASTER_TASKS context, and any locked decisions they need.
- **On completion**, each agent updates its subtask status to `[COMPLETED]` and reports what it changed.
- **Serialized subtasks** wait for their dependency to complete before spawning.

## 6. Cross-review agents

After each parallel group's implementation agents finish:

1. **Spawn a review agent per completed subtask.** The reviewer is a fresh agent that:
   - Re-reads the changed files from scratch (does not inherit the implementer's context).
   - Checks for bugs, logic errors, layering violations, missing edge cases, and consistency with project rules (`.claude/rules/*`).
   - Verifies the subtask's validation command passes.
   - Reports: `PASS` (no issues) or `ISSUES FOUND` with specific file:line references and fix descriptions.
2. **If issues are found:** fix them inline (if minor) or flag to the user (if architectural). Then re-run the subtask's validation.
3. **Review agents can run in parallel** when reviewing different subtasks that don't share files.
4. **One review round is the default.** A second round happens only if the first review triggered non-trivial fixes. Cap at 2 review rounds per subtask.

## 7. Completion

After all subtasks pass implementation + review:

1. Run the feature-level validation gate from MASTER_TASKS.md.
2. Update MASTER_PLAN.md status.
3. Report the final state to the user.
