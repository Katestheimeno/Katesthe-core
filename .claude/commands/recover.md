---
description: Reconstruct in-flight work after a session ended without finishing — inventory the drift and propose how to resume, plan, commit, or triage
argument-hint: "[--triage]"
---

# Recover

Bridge a session that ended badly. A process kill, IDE crash, or manual `git checkout`
can leave uncommitted work with no clear anchor: dirty files, a subtask stuck
`[IN_PROGRESS]`, or changes that don't map to any plan. Restarting fresh would either lose
intent (commit blindly) or stall (paralyzed by drift). `/recover` inventories the drift and
proposes concrete next moves. It **never** commits or resets without your choice.

## Usage

```
/recover            Inventory drift and propose recovery options
/recover --triage   Print the inventory only, then stop (no options, no changes)
```

## Procedure

### 1. Inventory the drift

```bash
git status --porcelain          # path-by-path
git diff --stat HEAD            # line counts per file
git diff --stat --cached HEAD   # already staged
```

Group into untracked (`??`), modified (` M`/`MM`), and deleted (` D`/`D `). Exclude
`.claude/` bookkeeping from the "source drift" count (note it separately).

### 2. Reconcile against task state

- Read `.claude/tasks/MASTER_PLAN.md` `## Active` and find any `[IN_PROGRESS]` subtask in
  the active feature's `MASTER_TASKS.md` (and scan other features — there should be at most
  one in-progress subtask total).
- For each `[IN_PROGRESS]` subtask, read its `## Scope` (`Allowed:`/`Forbidden:`) and compare
  to the dirty paths. Does the drift **match** the subtask's scope, **exceed** it, or is it
  **unrelated** (no active subtask at all)?
- Read the top ~10 modified files by churn and infer the theme(s): one coherent task, two
  tasks, or scattered changes?

Emit a **Recovery Inventory** block:

```
RECOVERY INVENTORY
------------------
Source drift:   <N modified> + <N untracked> + <N deleted>   (.claude/ bookkeeping: <N>)
Lines changed:  +<add> / -<del>
Active feature: <name or none>
[IN_PROGRESS]:  <subtask id+title or none>
Scope match:    matches / exceeds scope / no active subtask

Inferred themes:
  1. <theme> — files: <count>, lines: <sum>
Top paths by churn:
  1. <path>: <lines>
  …
```

If invoked as `/recover --triage`, stop here. Modify nothing.

### 3. Propose options (wait for the user's choice)

```
+--------------------------------------------------------------+
|  RECOVERY OPTIONS                                            |
+--------------------------------------------------------------+
|  A — Resume the in-flight subtask                            |
|      Drift matches an [IN_PROGRESS] subtask. Continue with   |
|      /flow impl <feature> — the orchestrator picks up the    |
|      first incomplete subtask and finishes it (audit-loop +  |
|      review + validation).                                   |
|                                                              |
|  B — Reconstruct a plan                                      |
|      Drift is coherent but has no plan (or exceeds the       |
|      current one). Run /flow pln to retro-fit a MASTER_TASKS |
|      plan around the existing changes, then /flow impl.      |
|                                                              |
|  C — Clean commit                                            |
|      Drift is shippable as-is. Run /commit to generate a     |
|      grouped commit script. Confirm first — do not commit    |
|      if any inferred theme has unresolved risk (missing      |
|      tests, failing validation).                             |
|                                                              |
|  D — Manual triage                                           |
|      Print the inventory and stop. You split + commit by     |
|      hand.                                                   |
+--------------------------------------------------------------+
```

### 4. Act on the choice

- **A** — confirm the active feature name, then hand off to `/flow impl <feature>`. Do not
  auto-run it; let the user review the inventory first.
- **B** — hand off to `/flow pln` with a one-line description synthesized from the inferred
  themes. The plan's subtasks should cover *remaining* work to bring the drift to done.
- **C** — confirm shippability (no failing validation, tests present for new branches), then
  hand off to `/commit`. Never bundle unrelated themes into one commit without saying so.
- **D** — already printed; stop.

## Anti-patterns

- Auto-committing without the user. Recovery commits are team-visible and may bundle
  unrelated work — always confirm.
- Skipping the diff read in step 2 — "I'll just commit it" mislabels the work.
- Marking a subtask `[COMPLETED]` during recovery without running its validation.
- Splitting drift into multiple commits without explicit approval — that rewrites intended history.
