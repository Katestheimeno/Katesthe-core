# Weekly Summary

Generate or update a structured weekly work summary based on git history and project state.

## Usage

```
/weekly-summary                  This week (default)
/weekly-summary last week        The previous week
/weekly-summary week before      Two weeks ago
/weekly-summary 2 weeks ago      N weeks ago (any N)
/weekly-summary 2026-06-09       The week containing a specific date
/weekly-summary June 9           The week containing a natural-language date
```

Pass **either** a date within the target week **or** a relative week reference
(`last week`, `week before`, `previous week`, `N weeks ago`) to generate/update that
week's summary instead of the current week. With no argument, the current week is used.

## Instructions

You are a weekly summary generator. Your job is to produce a comprehensive, structured work summary for a given week, organized in a date-based directory hierarchy.

### Input

```
$ARGUMENTS
```

### Phase 0 — Determine the target week

1. **Parse arguments.** Resolve `$ARGUMENTS` to a single calendar date inside the target week:
   - **Empty** → use today's date.
   - **Relative week reference** → resolve against today, then pick any date in that week:
     - `this week` / `current week` → today
     - `last week` / `previous week` → today minus 7 days
     - `week before` / `the week before last` → today minus 14 days
     - `N weeks ago` (e.g. `2 weeks ago`, `3 weeks back`) → today minus `N × 7` days
   - **Explicit date** (any format: `YYYY-MM-DD`, `June 9`, `9 June 2026`) → use it directly.

   Resolve relative references with the shell so they are unambiguous, e.g.:
   ```bash
   date +%F                          # today (this week)
   date -d "7 days ago" +%F          # last week
   date -d "14 days ago" +%F         # week before
   date -d "21 days ago" +%F         # 3 weeks ago
   ```
   If `$ARGUMENTS` is ambiguous (e.g. you cannot tell whether it is a date or a relative
   reference), state your interpretation in the final report so the user can correct it.

2. **Calculate week boundaries.** Weeks run **Monday–Sunday**. From the resolved date:
   - Find the Monday of that week (week start)
   - Find the Sunday of that week (week end)
   - Determine the **week number** within the month (1-indexed):
     - Week 1: days 1–7
     - Week 2: days 8–14
     - Week 3: days 15–21
     - Week 4: days 22–end of month

3. **Build the file path:**
   ```
   docs/changes/{YYYY}/{MM}/week{N}.md
   ```
   Example: June 9, 2026 (Monday, day 9) → `docs/changes/2026/06/week2.md`

4. **Check if the file exists.** This determines whether you CREATE or UPDATE.

### Phase 1 — Gather git data

Run the following to collect all changes for the target week:

```bash
# All commits on the current branch within the week (Mon 00:00 → Sun 23:59)
git log --after="{monday_date}" --before="{sunday_date} 23:59:59" --format="%H|%h|%ai|%s" --no-merges

# Detailed file stats per commit
git log --after="{monday_date}" --before="{sunday_date} 23:59:59" --stat --no-merges

# Summary of all changes (insertions/deletions)
git diff --stat $(git log --after="{monday_date}" --before="{sunday_date} 23:59:59" --format="%H" --no-merges | tail -1)^..$(git log --after="{monday_date}" --before="{sunday_date} 23:59:59" --format="%H" --no-merges | head -1) 2>/dev/null

# Uncommitted changes (if target week is current week)
git status --short
git diff --stat
```

Also check:
- `.claude/tasks/MASTER_PLAN.md` — active features and their progress
- `.claude/tasks/*/MASTER_TASKS.md` — subtask completion status for any active feature
- `docs/changes/` — any traceability files dated within the target week
- `CHANGELOG/` — any changelog entries dated within the target week

### Phase 2 — Analyze and categorize

Group the gathered data into:

1. **Commits by day** — cluster commits by date, identify the focus area for each day
2. **Features/initiatives** — group related commits into logical work streams (e.g., "R6 audit remediation", "auth hardening", "bug fixes")
3. **Files changed by area** — categorize modified files by app/domain (accounts, game, elearning, config, etc.)
4. **Impact metrics** — total commits, files changed, insertions/deletions, tests added/modified
5. **Task progress** — any `.claude/tasks/` subtasks that moved to `[COMPLETED]` during the week

### Phase 3 — Write or update the file

#### If CREATING a new file:

Ensure the directory exists (`docs/changes/{YYYY}/{MM}/`), then write the file with this template:

```markdown
# Week {N} — {Month YYYY}

**Period:** {Monday date} → {Sunday date}
**Branch:** `{current branch}`
**Last updated:** {now, YYYY-MM-DD HH:MM}

---

## Overview

{2-4 sentence summary of the week's work — what was the main focus, what was accomplished}

| Day | Focus | Commits | Key changes |
|-----|-------|---------|-------------|
| Mon {date} | {focus} | {count} | {brief} |
| Tue {date} | {focus} | {count} | {brief} |
| ... | ... | ... | ... |

---

## Daily breakdown

### {Day, Month DD}

#### Commits

| Hash | Time | Description |
|------|------|-------------|
| `{short_hash}` | {HH:MM} | {commit message} |

#### Changes
{narrative of what was done, grouped by concern — not just a commit list}

---

{repeat for each day with commits}

## Active initiatives

{For each feature/initiative that had work this week:}

### {Initiative name}
- **Source:** {where this work came from — task plan, user request, audit}
- **Progress:** {X/Y subtasks complete, or narrative}
- **Key changes:** {bullet list}

---

## Impact summary

| Metric | Value |
|--------|-------|
| Total commits | {N} |
| Files changed | {N} |
| Insertions | +{N} |
| Deletions | -{N} |
| Tests added/modified | {N files} |
| Task plan subtasks completed | {N} |
| Apps touched | {list} |

---

## Documentation produced

| File | Purpose |
|------|---------|
| {path} | {one-line description} |

---

## Uncommitted work

{If there are uncommitted changes at the time of generation, list them here. Otherwise: "None — all work committed."}

---

## Next steps

{What's next based on task plans, uncommitted work, or stated goals. Be specific — link to task files or docs.}
```

#### If UPDATING an existing file:

1. **Read the existing file** to understand what's already documented.
2. **Find new commits** that are not yet in the file (compare commit hashes).
3. **Update the following sections:**
   - **Overview** — revise the summary to reflect the full week so far
   - **Daily breakdown** — add new days or append commits to existing days
   - **Active initiatives** — update progress numbers and add new key changes
   - **Impact summary** — recalculate all metrics for the full week
   - **Documentation produced** — add any new traceability/changelog files
   - **Uncommitted work** — refresh from current `git status`
   - **Next steps** — update based on current state
   - **Last updated** — set to current timestamp
4. **Do not duplicate** commits already documented. Match by short hash.
5. **Preserve manually added context.** If someone edited the file to add notes or context that isn't from git, keep it.

### Phase 4 — Report

After writing/updating, report to the user:
- The file path that was created/updated
- How many new commits were added (if updating)
- A brief summary of the week so far
- Whether there are uncommitted changes that should be committed before the next summary

### Principles

- **Git is the source of truth.** Every claim in the summary must trace to a commit hash, a file diff, or a task status.
- **Structure over narrative.** Tables and bullet lists over paragraphs. The summary should be scannable.
- **Idempotent updates.** Running the command twice in a row should produce the same file (no duplicate entries).
- **No invented context.** If you can't determine what a commit did from its message and diff, say so — don't guess.
- **Week boundaries are strict.** A commit from Sunday 23:59 belongs to this week. A commit from Monday 00:00 belongs to next week.
- **Preserve history.** Never delete content from a previous update — only add or revise.
