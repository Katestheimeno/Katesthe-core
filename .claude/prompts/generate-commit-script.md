# Generate commit-all.sh

Create a `commit-all.sh` bash script in the repo root that commits all currently uncommitted changes (staged, unstaged, and untracked) as a series of grouped, well-organized git commits.

## Steps

1. Run `git diff --name-only HEAD` to get all modified tracked files.
2. Run `git status --short | grep "^?"` to get all untracked files.
3. Read the diff (`git diff HEAD`) to understand what each file's changes are about.
4. Check `git log --oneline -5` for the repo's commit message style (conventional commits, scope in parens, etc.).
5. Group the files into logical commits by:
   - **Module / package** (keep changes to one area together).
   - **Type of change** (security fixes separate from feature work, docs separate from code).
   - **Dependency order** — infrastructure/config changes before app-level changes that depend on them.
   - Keep each commit focused on one concern — if a file touches two concerns, put it in the primary one.
   - Separate test files from implementation when they're standalone; co-locate when they test a specific fix.
6. Write the script with:
   - `#!/usr/bin/env bash` + `set -euo pipefail`.
   - Section comments (`# ─── 1. Description ───`) for readability.
   - Explicit `git add` per commit (list specific files, never `git add -A` or `git add .`).
   - Multi-line commit messages via heredoc: `git commit -m "$(cat <<'EOF' ... EOF)"`.
   - Commit messages following the repo's existing convention (check git log).
   - Each commit message: first line is the subject, blank line, then body explaining WHY.
   - A trailer line crediting the AI assistant if that's the repo's convention (match existing commits).
   - A final echo summarizing how many commits were created.
7. Do NOT run the script — just create it. The user will run it themselves.
8. Do NOT include any secret/credential file or anything in `.gitignore`.
9. Exclude `commit-all.sh` itself from the commits.

## Grouping heuristics

- Config/infrastructure changes first (settings, middleware, shared utilities).
- Security fixes grouped by severity (critical first).
- Per-module groups when a module has 3+ files changed.
- Cross-cutting changes (shared constants, error catalog, shared types) go with the primary consumer.
- Docs, changelogs, and task-tracking files always last.
- Untracked new files go with their related modified files (e.g., a new test file with the code it tests).

## Output

A single file `commit-all.sh` at the repo root, executable, ready to run.
