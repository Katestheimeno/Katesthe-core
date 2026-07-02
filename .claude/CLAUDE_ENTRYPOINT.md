
# ⚠️ MANDATORY ENTRYPOINT — READ THIS FIRST

**Before ANY action** (code, files, packages, commands), Claude MUST execute the Task Checkpoint Protocol. Non-negotiable. No exceptions.

## Checkpoint Protocol (runs before every request)

1. **Read `.claude/CONTEXT_MAP.md`** — fastest path to full project state. One read = complete context.
2. **Read `.claude/tasks/MASTER_PLAN.md`** — identify active feature. If none + user has new request → Plan Creation.
3. **Read active feature's `.claude/tasks/{feature}/MASTER_TASKS.md`** — find `[IN_PROGRESS]` subtask. If exists: resume it. If none: mark first `[PENDING]` as `[IN_PROGRESS]`.
4. **Heartbeat rule** — after every 3 bash commands or 1 file write, verify:
   - Still within subtask Scope?
   - Unplanned file modified?
   - MASTER_PLAN.md reflects reality?
   - If scope creep detected → flag in subtask `⚠ Drift Log`, re-align before continuing.

## Task Classification

- **Simple task**: one-step, minor fix, config tweak, single-file edit → log in `.claude/tasks/general/SESSION_LOG.md`. No feature folder.
- **Feature**: multi-step, architectural, spans files, user-facing, has dependencies → create full plan in `.claude/tasks/{feature}/`.

When in doubt: default to simple task. Promote to feature only if subtask spawns >2 dependent steps.

## Definition of Done

Subtask cannot be `[COMPLETED]` until its `Validation:` block passes (exit code 0 or expected output). If validation fails → document in `Validation Log:`, keep working.

## Anti-Patterns (Never Do)

- Start code before checkpoint protocol
- Mark `[COMPLETED]` without passing validation
- Modify files outside subtask `Scope:` without updating scope first
- Create feature plan for simple task
- Allow two `[IN_PROGRESS]` subtasks simultaneously
- Skip updating CONTEXT_MAP.md after feature completes

**Full protocol details**: see `.claude/tasks/` structure and templates below in this file.

---

## Task Management System

### Directory Structure
```
.claude/tasks/
  MASTER_PLAN.md              # Roadmap, active feature pointer, queue
  general/SESSION_LOG.md      # Simple tasks (append-only)
  {feature}/
    MASTER_TASKS.md           # Feature context, priority, task list
    001-subtask.md            # Scope, Validation, Breadcrumbs
    002-subtask.md
    ...
  completed/                  # Feature summaries (readable)
  archive/                    # Post-mortems (IGNORED unless explicit)
```

### Status Tags
- `[PENDING]` — not started
- `[IN_PROGRESS]` — active (only one per feature)
- `[BLOCKED]` — waiting on dependency (include reason + blocker ref)
- `[COMPLETED]` — validation passed
- `[SKIPPED]` — bypassed (include justification)
- `[DEFERRED]` — moved to future (include target)

### Subtask Template
```markdown
# Subtask: {description}
Status: [PENDING]
Feature: {feature_name}
Created: {date}
Updated: {date}

## Breadcrumb
Parent: .claude/tasks/{feature}/MASTER_TASKS.md
Previous: .claude/tasks/{feature}/00{N-1}-*.md
Next: .claude/tasks/{feature}/00{N+1}-*.md

## Context
One paragraph: what, why, how it fits.

## Scope
Allowed:
- /path/to/file.py
Forbidden:
- /other/path/*

## Steps
1. ...

## Validation
Command returning exit 0 before [COMPLETED].

## Validation Log
- [ ] Run 1: ...

## ⚠ Drift Log
(If scope creep detected)
```

### Priority Rules
- **P0** — critical: pre-empts after current subtask
- **P1** — high: top of queue after current feature
- **P2** — normal: standard queue position
- **P3** — low: queue bottom

---

## Orchestration layer (optional)

If this repo was installed with the kit's content dirs, you also have a multi-agent
orchestration layer built on top of the checkpoint protocol:

- **`.claude/agents/`** — role agents: `orchestrator`, `planner`, `plan-reviewer`,
  `implementer`, `explorer`, `code-reviewer`, `test-writer`, `doc-writer`,
  `security-auditor`, `sweep-analyzer`, `sweep-reviewer`. The orchestrator dispatches the
  others in parallel groups with disjoint file ownership, then cross-reviews.
- **`.claude/commands/`** — `/flow` is a router with three subcommands: `pln [context]`
  builds a parallelized `MASTER_TASKS` plan and has `plan-reviewer` critique/amend it ≥2×
  before presenting; `impl <plan> [rules]` dispatches the orchestrator to execute it (rules
  like "stop after each phase" become checkpoints); `cmplt <plan>` archives a finished plan
  via the `archive-feature.sh` hook. `/sweep <domain | free-text context>` runs a deep
  analysis sweep and generates a verified remediation plan.
- **`.claude/rules/`** — conventions the agents read as source of truth. `workflow.md` is
  the agent orchestration protocol; add your own `foundations.md`/layering rules so agents
  match your stack. (A Django overlay ships these pre-filled — see the kit's
  `bundle/overlays/`.)
- **`.claude/prompts/`** — `sweep.md` (the engine behind `/sweep`),
  `generate-commit-script.md`, `work-journal.md`.

These are **stack-agnostic** by default: they describe *how* work flows through agents,
deferring stack-specific conventions to `.claude/rules/` and `.claude/CONTEXT_MAP.md`.

## Kit version (optional)

If this repository was set up with workflow-kit (`git@github.com:Katestheimeno/workflow-kit.git`), the file **`.claude/WORKFLOW_KIT`** records the installed kit version and install time. It is safe to commit so the team can see which protocol revision a repo uses. Re-run the kit’s `install.sh` or `install.sh --only-protocol` to refresh the entrypoint after upgrading the kit clone.
