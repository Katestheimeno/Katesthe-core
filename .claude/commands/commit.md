# Generate Commit Script

Create (or regenerate) a `commit-all.sh` bash script in the repo root that commits all currently uncommitted changes as a series of grouped, well-organized git commits.

## Usage

```
/commit
```

No arguments needed — it reads `git status` and `git diff` to determine what to commit.

## Instructions

### Input

```
$ARGUMENTS
```

If `$ARGUMENTS` is not empty, treat it as additional context for grouping or commit message guidance (e.g., `/commit security fixes only`).

### Phase 0 — Gather state

Run these commands to understand the current working tree:

```bash
git status --short
git diff --name-only HEAD
git status --short | grep "^?"
git diff HEAD --stat
git log --oneline -5
```

If there are no uncommitted changes (no modified, no untracked), tell the user "Nothing to commit" and stop.

### Phase 1 — Analyze changes

1. Read the diff (`git diff HEAD`) to understand what each file's changes are about.
2. Check `git log --oneline -5` for the repo's commit message style (conventional commits, scope in parens, etc.).
3. Read the content of untracked files to understand their purpose.

### Phase 2 — Group into commits

Group the files into logical commits by:

- **Domain/app** (e.g., all `accounts/` auth changes together, all `game/` changes together)
- **Type of change** (security fixes separate from feature work, docs separate from code)
- **Dependency order** — infrastructure/config changes before app-level changes that depend on them
- Keep each commit focused on one concern
- If a file touches two concerns, put it in the primary one
- Separate test files from implementation when they're standalone; co-locate when they test a specific fix

### Phase 3 — Write the script

If `commit-all.sh` already exists in the repo root, **overwrite it completely** with fresh content based on current state.

Write the script with:

- `#!/usr/bin/env bash` + `set -euo pipefail`
- Section comments (`# ─── 1. Description ───`) for readability
- Explicit `git add` per commit (list specific files, never `git add -A` or `git add .`)
- Multi-line commit messages via heredoc:
  ```bash
  git commit -m "$(cat <<'EOF'
  commit message here
  EOF
  )"
  ```
- Commit messages following the repo's existing convention (check git log)
- Each commit message: first line is the subject, blank line, then body explaining WHY
- **NO Co-Authored-By line** — do not add any co-author attribution
- A final block that:
  1. Echoes how many commits were created
  2. **Self-deletes** the script: `rm -f "$0"`
  3. Echoes confirmation that the script cleaned up after itself

### Phase 4 — Make executable

```bash
chmod +x commit-all.sh
```

### Grouping heuristics

- Config/infrastructure changes first (settings, middleware, shared utilities)
- Security fixes grouped by severity (critical first)
- Per-app groups when an app has 3+ files changed
- Cross-cutting changes (error catalog, shared types) go with the primary consumer
- Docs, changelogs, and task tracking files always last
- Untracked new files go with their related modified files (e.g., new test file with the code it tests)
- `.claude/` task/sweep files grouped separately from production code

### What NOT to commit

- `.env`, credentials, or any file in `.gitignore`
- `commit-all.sh` itself (excluded from all commits)
- Exclude the script from git tracking entirely

### Output

A single file `commit-all.sh` at the repo root, executable, ready to run. When the user runs it:
1. All changes are committed in logical groups
2. The script deletes itself on success
3. If any commit fails (`set -e`), the script stops and remains on disk for debugging

### Self-deletion mechanism

The script must end with:
```bash
echo ""
echo "═══ Done: N commits created ═══"
rm -f "$0"
echo "commit-all.sh cleaned up."
```

This ensures the script never lingers in the working tree after a successful run.
