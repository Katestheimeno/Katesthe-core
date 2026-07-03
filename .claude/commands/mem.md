---
description: Persistent cross-session memory — save/apply/list/delete project facts, preferences, and constraints under .claude/memory/
argument-hint: "[save <note> | apply | list | delete <slug>]"
---

# Mem

Persistent, per-project memory. Survives across sessions so the kit stops re-deriving
the same preferences, decisions, and constraints every chat.

`/mem` is a small router: the first word of `$ARGUMENTS` selects a subcommand; everything
after it is that subcommand's input.

## Usage

```
/mem save <note>      Record a fact/preference/decision now (or scan the session if no note)
/mem apply            Load every memory, classify it, emit the Active Constraints block
/mem list             Show all saved memories grouped by type
/mem delete <slug>    Remove one memory (asks for confirmation)
```

`apply` runs automatically at session start (the `session-start.sh` hook surfaces the
index and directs Claude here). `save` runs automatically at `/flow cmplt`. Both also run
on explicit invocation.

### Storage

All memory lives in `.claude/memory/` (per-project, committable):
- `MEMORY.md` — the index, read in full at every session start. Keep it under 200 lines.
- `<type>_<slug>.md` — one fact per file, where `<type>` ∈ `feedback | project | user | reference`.

If `.claude/memory/` or `MEMORY.md` does not exist, create them before writing (the
`ensure-tasks.sh` hook also bootstraps them):

```bash
mkdir -p .claude/memory
[ -f .claude/memory/MEMORY.md ] || printf '# Project Memory\n\n<!-- One line per memory: - [Title](file.md) — hook -->\n' > .claude/memory/MEMORY.md
```

### Router

1. Read the first whitespace-delimited token of `$ARGUMENTS` (lowercased) as the subcommand.
2. Everything after the first token is that subcommand's input (`$REST`).
3. If the first token is none of `save|apply|list|delete`, treat the **entire** `$ARGUMENTS`
   as a note for `save` (e.g. `/mem we deploy from main only` ⇒ `save we deploy from main only`).
4. Empty `$ARGUMENTS` ⇒ run `apply`.

---

## Subcommand: save

### What qualifies for saving

| Type | Save when | File naming |
|------|-----------|-------------|
| `feedback` | User corrects an approach, states a preference, or validates a non-obvious choice | `feedback_<slug>.md` |
| `project` | Architectural decision, constraint, or context that affects future tasks | `project_<slug>.md` |
| `user` | Role, expertise level, or communication preference that shapes collaboration | `user_<slug>.md` |
| `reference` | External resource (URL, dashboard, ticket tracker) and its purpose | `reference_<slug>.md` |

**Triggers (case-insensitive):**
- Corrections — "don't", "do not", "stop", "avoid", "no, not that"
- Preferences — "prefer", "instead of", "use X instead", "always use", "never use"
- Validations — "perfect, keep doing that", "yes exactly", "that's correct"
- Rules — "from now on", "always", "never"
- Project — "we use X not Y because…", "can't do X because of Y", a pattern to carry forward

**Do NOT save:** code patterns/architecture/file paths (derivable from the codebase),
ephemeral task details, anything already in `CLAUDE.md` / `CONTEXT_MAP.md` / rules /
the feature's `MASTER_TASKS.md`, or git "who changed what".

### Procedure

1. **Gather candidates.** If `$REST` is non-empty, that note is the single candidate.
   Otherwise scan the current session for saveable content using the triggers above.
2. For each candidate:
   - **a. Duplicate check** — read `MEMORY.md`, look for a related entry. If one exists,
     **update** that file (add a bullet or revise the rule); never create a duplicate.
   - **b. Write `.claude/memory/<type>_<slug>.md`:**
     ```
     ---
     name: <short-kebab-case-slug>
     description: <one-line summary — used to judge relevance in future sessions>
     metadata:
       type: <user|feedback|project|reference>
       saved: YYYY-MM-DD
       source: <feature-name or "explicit">
     ---

     <Lead sentence: the rule / fact / profile note / resource pointer.>

     # feedback & project also add:
     **Why:** <reason the user gave, or the incident that surfaced it>
     **How to apply:** <when/where this kicks in; how to judge edge cases>

     # reference adds:
     **Purpose:** <what it tracks / what it's used for>
     ```
   - **c. Update `MEMORY.md`** — add or refresh a one-line entry (under 150 chars):
     `- [Title](file.md) — one-line hook`
3. **Report:**
   ```
   MEM SAVED  : [N] new — <slugs>
   MEM UPDATED: [N] updated — <slugs>
   MEM SKIPPED: [N] already recorded
   ```
   If nothing qualified: `MEM: nothing new to record this session.`

---

## Subcommand: apply

1. Read `MEMORY.md`. If empty/missing → emit nothing and stop.
2. For each index entry, read the referenced `.claude/memory/*.md` file.
3. Classify each:
   - **Active constraint** — `feedback` type, or any entry with a `**How to apply:**` line
   - **Context** — `project` type; informs planning and suggestions
   - **User profile** — `user` type; calibrates communication style and detail
   - **Reference** — `reference` type; held for lookup
4. Hold active constraints in mind for the whole session. Before any technical decision,
   check whether a constraint applies. If a proposed action would violate one, surface a
   **CONFLICT DETECTED** block before proceeding.
5. Emit the **Active Constraints** block (omit entirely if there are no entries; for a
   missing file, print a warning line instead of a row):
   ```
   +----------------------------------------------------------+
   |  ACTIVE MEMORY CONSTRAINTS                                |
   +----------------------------------------------------------+
   |  Loaded: [N] entr(y/ies)                                  |
   |                                                           |
   |  [feedback] <one-line rule>                               |
   |             → <file.md>                                   |
   |  [project]  <one-line fact>                               |
   |             → <file.md>                                   |
   +----------------------------------------------------------+
   ```

---

## Subcommand: list

1. Read `MEMORY.md`. If no entries → `MEM LIST: no memories saved yet in this project.` and stop.
2. For each entry, read the file and extract `metadata.type` + the lead sentence.
3. Print a table grouped by type (`feedback`, `project`, `user`, `reference`), one bullet
   per memory (`• <slug> — <lead sentence>`), ending with `Total: <N> in .claude/memory/`.
4. Offer: "Run `/mem save <note>` to add one, or `/mem delete <slug>` to remove one."

---

## Subcommand: delete

1. Resolve `.claude/memory/<slug>.md`, trying prefixes `feedback_`, `project_`, `user_`,
   `reference_`, then the bare `<slug>.md`.
2. If not found → `MEM DELETE: no memory file matching '<slug>' found.` and stop.
3. Read it, print the lead sentence, and ask: "Delete `<filename>`? (yes/no)".
4. On **yes**: delete the file, remove its line from `MEMORY.md`, print `MEM DELETED: <filename>`.
5. On **no**: `MEM DELETE: cancelled.`

---

## Anti-patterns

- Saving code/architecture/paths already derivable from the repo.
- Creating a duplicate file when an existing memory covers the topic — always update.
- Saving session ephemera that won't matter next session.
- Applying constraints silently — always surface conflicts before acting.
- Skipping the duplicate check (bloats the index).
- Letting `MEMORY.md` grow past 200 lines — keep entries concise, prune stale ones.
