---
description: Intentionally suspend mid-task — write a resume checkpoint into the active subtask so the next session picks up cleanly
argument-hint: "[reason]"
---

# Pause

Suspend in-flight work on purpose: context switch, end of session, or waiting on external
information. Use this instead of just closing the tab — it leaves a resumption trail the
next session's checkpoint protocol will surface.

Run `/flow cmplt` instead if the work is actually **done**. Run `/commit` if you want the
changes committed. `/pause` neither commits nor completes — it only records where you are.

## Usage

```
/pause              Checkpoint the active subtask (reason: "intentional suspend")
/pause <reason>     Checkpoint with an explicit reason / blocker
```

## Pre-flight

Find the active `[IN_PROGRESS]` subtask: read `.claude/tasks/MASTER_PLAN.md` `## Active`,
then the feature's `MASTER_TASKS.md`. If there is no `[IN_PROGRESS]` subtask, there is
nothing to pause — tell the user (offer `/flow pln` if they have new work, or `/recover` if
the tree is dirty without a plan).

## Procedure

### 1. Locate position

- Identify the active feature + `[IN_PROGRESS]` subtask file.
- From the subtask's `## Steps` (and any `## Validation Log` / progress notes), determine the
  last completed step and the next pending step.

### 2. Write the pause checkpoint into the subtask file

Append (or replace, if one already exists) a `## ⏸ Pause checkpoint` section in the
`[IN_PROGRESS]` subtask file. Do **not** change its `Status:` — it stays `[IN_PROGRESS]` so
`/flow impl` resumes it:

```
## ⏸ Pause checkpoint
Paused at     : YYYY-MM-DD HH:MM
Last step done: <step N of M — description, or "none yet">
Next step     : <step N+1 of M — description>
Blocker/reason: <reason, or "intentional suspend">
```

### 3. Log it

Append one line to `.claude/tasks/general/SESSION_LOG.md` under `## Notes`:

```
- [PAUSED] YYYY-MM-DD — <feature>/<subtask id>: next is <step N+1 — description>. <reason>
```

### 4. Emit the pause summary

```
PAUSE SUMMARY
─────────────────────────────────────────────────────────
Feature   : <name>
Subtask   : <id — title>  (Status unchanged: [IN_PROGRESS])
Last step : <step N of M — description, or "none yet">
Next step : <step N+1 — description>
Reason    : <reason or "intentional suspend">
Resume    : /flow impl <feature>  (picks up from the checkpoint)
─────────────────────────────────────────────────────────
Checkpoint written to: <subtask file> (## ⏸ Pause checkpoint)
```

## On resume

`session-start.sh` surfaces the `[IN_PROGRESS]` subtask; the checkpoint protocol reads that
subtask file, where the `## ⏸ Pause checkpoint` section names the next step. Run
`/flow impl <feature>` to continue — the orchestrator resumes the first incomplete subtask.

## Anti-patterns

- Using `/pause` when `/flow cmplt` is the right action (work is complete).
- Pausing without recording the next step — the next session has no anchor.
- Changing the subtask `Status:` — it must stay `[IN_PROGRESS]` so resume works.
- Calling `/pause` repeatedly without resuming — keep a single, current checkpoint per subtask.
