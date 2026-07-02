# Daily work journal entry

---

## Purpose

Generate (or update) today's detailed commit-based work journal for the **current project**. It analyzes git history and writes a comprehensive daily entry.

> Paths below use `$HOME` — substitute your real home directory. Adjust the journal
> root if your setup keeps it elsewhere.

---

## Instructions

```markdown
You are generating a daily work journal entry. Follow these steps exactly:

### Step 1 — Identify project and date

1. **Project name:** derive from the git remote origin URL (strip `.git`, take the repo name, lowercase it). If no remote, use the working directory's basename, lowercased.
2. **Date:** use today's date as `YYYY/MM/DD`.
3. **Target file:** `$HOME/.work_journal/<YYYY>/<MM>/<DD>/<project>.md`

### Step 2 — Gather today's commits

Run:
```bash
git log --since="midnight" --format="%H %h %s (%ar)" --reverse
```

If there are **no commits today**, check for uncommitted changes with `git status` and `git diff --stat`. If there is still nothing, report "No recorded work today" and stop.

### Step 3 — Analyze each commit

For each commit hash from Step 2:

1. `git show --stat <hash>` — get files changed, insertions, deletions.
2. `git show <hash>` — read the actual diff to understand **what** changed and **why**.
3. Group related commits if they form a logical unit of work.

### Step 4 — Write the journal entry

Use this template:

```markdown
# Work Journal — <YYYY-MM-DD>

**Project:** <project name>
**Branch:** <current branch>
**Commits:** <count> | **Files changed:** <total unique files> | **Lines:** +<added> / -<removed>

---

## Summary

<2-3 sentence high-level summary of the day's theme>

---

## Changes

### <N>. <Short title> (<HH:MM>)

`<short_hash>` — <commit message>

**What changed:**
- <file> — <what was done and why>
- ...

**Impact:** <one line: what this enables, fixes, or unblocks>

---
<repeat for each commit or logical group>
```

### Step 5 — Append uncommitted work (if any)

If `git status` shows staged or unstaged changes not yet committed, add a section:

```markdown
## In Progress (uncommitted)

- <file> — <brief description of changes>
```

### Step 6 — Write the file

1. Create directories if they don't exist: `mkdir -p $HOME/.work_journal/<YYYY>/<MM>/<DD>/`
2. If the target file **already has content**, read it first. Merge new commits that aren't already documented rather than overwriting. Append new sections and update the header stats.
3. If the file is empty or doesn't exist, write fresh.

### Step 7 — Update the monthly index

Check if `$HOME/.work_journal/<YYYY>/<MM>/index.md` exists.
- If not, create it with a header and today's entry.
- If it exists, append today's entry if not already listed.

Format:
```markdown
# <Month Name> <YYYY>

| Day | Project | Commits | Summary |
|-----|---------|---------|---------|
| <DD> | <project> | <commit count> | <one-line summary> |
```

### Output

After writing, confirm:
- File path written
- Number of commits documented
- One-line summary of the day's work
```

---

## Related

- Journal root: `$HOME/.work_journal/`
