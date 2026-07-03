---
description: Generate a PR description or CHANGELOG entry from completed-feature summaries and branch git history
argument-hint: "[last N | since YYYY-MM-DD | changelog]"
---

# PR Notes

Turn the work this branch has shipped into a ready-to-paste PR description or CHANGELOG
entry. It reads the kit's own records — `completed/*.md` feature summaries plus git history —
so it costs almost nothing and never fabricates.

Distinct from the kit's other summarizers: `/commit` builds a commit *script*; `/retro`
builds a stakeholder retrospective *package*; `/weekly-summary` builds a weekly journal.
`/pr-notes` produces the **PR body / release notes** for the current change set.

## Usage

```
/pr-notes                   Default: this branch vs the base branch, PR-description format
/pr-notes last 3            The 3 most recent completed features
/pr-notes since 2026-06-01  All completed features archived on/after the date
/pr-notes changelog         CHANGELOG.md entry format instead of a PR description
```

## Procedure

### 1. Determine scope

- **Completed features:** list `.claude/tasks/completed/*.md`. Default to the 5 most recent
  by `Archived:` date (or `last N` / `since DATE`).
- **Branch commits:** `git log --no-merges --pretty='%s' <base>..HEAD`, where `<base>` is the
  repo's default branch (`main`/`master`) — fall back to `git log -30` if no base is found.
- List the completed-summary files and the commit range in scope before proceeding.

### 2. Extract

From each `completed/<feature>.md`: the feature title (`# Completed: <feature>`), the
`Archived:` date, and the `## Subtasks` list (what was done). From git: subjects grouped by
conventional-commit type (`feat`/`fix`/`refactor`/`docs`/`chore`). Collect touched paths from
`git diff --name-only <base>..HEAD` for the "Files touched" list (cap at 20).

### 3. Render

**Default — PR description:**

```markdown
## Summary
- <one type-prefixed line per feature/theme: feat: / fix: / refactor: / docs:>

## Changes
### Features
- …
### Fixes
- …
### Refactors
- …

## Files touched
<deduplicated paths, at most 20 — summarize the rest as "+N more">

## Test plan
- [ ] <actionable check derived from the features' validation/acceptance>
- [ ] Existing tests still pass
```

**CHANGELOG (`/pr-notes changelog`):**

```markdown
## [Unreleased] — YYYY-MM-DD

### Added
- <feat items, one line each>

### Changed
- <refactor items>

### Fixed
- <fix items>
```

### 4. Output and offer

Print the generated text, then offer:

```
─────────────────────────────────────────────
Generated from: <N> completed features + <M> commits (<range>)
Format: PR description | CHANGELOG entry

  A — Write to CHANGELOG.md (prepend above the first ## [ header)
  B — Print again, clean (for copy/paste)
  C — Done
─────────────────────────────────────────────
```

If writing to `CHANGELOG.md`: prepend above the first `## [Unreleased]` / `## [` header;
create the file with a `# Changelog` header if it doesn't exist. Prepend only — never
rewrite existing entries.

## Anti-patterns

- Including secrets, tokens, or internal IDs from summaries/commits.
- Listing every file — summarize by feature, not by path.
- Fabricating content not present in the summaries or commits.
- Reading more than ~10 completed summaries without explicit instruction — output bloats.
