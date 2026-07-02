# Snapshot

Produce a concise, navigable **project state snapshot** — a single living architecture directory that
captures, as of today: an **overview** of the project, **what's built vs. in-progress vs. planned**, the
**architecture** (layers, components, data flow), and a **current-state audit** (health, gaps, risks).

Where `/sweep` deep-analyzes one slice for *defects* and `/retro` narrates *a period of change*,
`/snapshot` answers **"what is this project, and where does it stand right now?"** in one place you can
hand to a new engineer or a stakeholder.

It is built the way the kit builds everything: an **orchestrator** (you, the main loop) partitions the
codebase into domains, dispatches one **`snapshot-cartographer`** per domain in parallel, and a single
fresh **`snapshot-reviewer`** verifies their findings and fills gaps before you synthesize the
top-level docs.

## Usage

```
/snapshot                    Build the snapshot, or amend the existing one (default)
/snapshot --new              Force a brand-new snapshot, ignoring any existing one
/snapshot <focus>            Frame the snapshot around a theme (free text) — never filters, only frames
```

**Re-running amends by default.** If `docs/architecture/` already exists, `/snapshot` **re-reads it,
re-checks the project as a whole, and amends** — it refreshes the domains that changed since the last
run, adds pages for new domains, updates which features are now complete, re-runs the audit, advances
the watermark, and **preserves every human-added note**. It does not rebuild unchanged pages from
scratch. Use `--new` to start over.

Anything in `$ARGUMENTS` that isn't `--new` is a **focus hint** — free text used to frame the overview
and weight the audit (e.g. "readiness for the v2 launch"). It never excludes parts of the project from
the snapshot; the snapshot is always whole-project.

## Instructions

You are the **orchestrator** preparing a project state snapshot. You think, partition, delegate, and
synthesize — you do **not** map domains yourself (that's the cartographers) and you do **not** modify
production code. Keep the output **tight**: a snapshot is a scannable map, not a manual.

### Input

```
$ARGUMENTS
```

### Phase 0 — Resolve mode and output location

1. **Parse `$ARGUMENTS`:** strip `--new` if present; whatever remains is the **focus hint** (may be
   empty).
2. **Decide new vs. amend.** Check whether `docs/architecture/README.md` exists.
   - **`--new`, or it doesn't exist** → this is a **fresh** snapshot. Create `docs/architecture/` and
     `docs/architecture/domains/`. Establish the watermark with `git rev-parse --short HEAD`.
   - **It exists and no `--new`** → this is an **amend** (the default re-run path). Read the existing
     `README.md`, note its `Commit:` watermark and `Generated:` date, then go to **Phase 1b** before
     re-mapping.
3. Capture today's date and the current commit:
   ```bash
   date +%F
   git rev-parse --short HEAD
   git status --short        # note uncommitted work; the snapshot reflects the working tree
   ```

### Phase 1 — Orient and partition into domains (orchestrator, before dispatching)

Do this yourself in the main loop; it's cheap and it makes the parallel dispatch clean.

1. **Read the project's own map first:** `README.md`, `.claude/CONTEXT_MAP.md`, `.claude/rules/*.md`,
   and `.claude/tasks/MASTER_PLAN.md`. These tell you the intended architecture, the active feature,
   the completed features, and the conventions. Note the language(s), framework(s), and major libraries.
2. **Survey the layout** — top-level packages/modules, entry points, and how the code is grouped:
   ```bash
   git ls-files | sed 's#/[^/]*$##' | sort -u | head -80   # directory shape
   ```
3. **Partition the codebase into domains** — bounded contexts that map to modules/packages (e.g.
   `auth`, `billing`, `api`, `worker`, `web`, `infra`). Aim for **3–8 domains** so the snapshot stays
   legible; merge trivially small areas into a neighbor, and split a domain only if it's genuinely two
   concerns. Every meaningful part of the codebase must belong to exactly one domain — no overlaps, no
   orphans.
4. **Write the partition** to `docs/architecture/domains/_orientation.md`: the stack summary, the domain
   list with the paths each owns, and any area you deliberately excluded (with why). This is the
   contract the cartographers and the reviewer share.

### Phase 1b — Amend path (only when an existing snapshot is being re-run)

When amending, don't rebuild what hasn't moved:

1. **Read the existing snapshot** — `README.md`, `01-features.md`, `02-architecture.md`, `03-audit.md`,
   and every `domains/*.md`. Note the watermark commit.
2. **Find what changed** since the watermark:
   ```bash
   git diff --name-only {watermark}..HEAD     # files touched since last snapshot
   git log --oneline {watermark}..HEAD        # the narrative of change
   ```
   If nothing changed and the working tree is clean, report "Snapshot already current as of
   `{watermark}`" and stop without rewriting anything.
3. **Re-partition lightly.** Keep the existing domains. Map each changed file to its domain. Add a new
   domain (and its `_orientation.md` entry) only if new code introduced a genuinely new bounded context;
   retire a domain only if its code was deleted.
4. **Re-map only what moved.** In Phase 2, dispatch a cartographer **only** for domains with changed
   files (and any brand-new domain). Leave untouched domain pages as-is — the reviewer still validates
   them for staleness in Phase 3.
5. **Always refresh the cross-cutting docs.** `01-features.md` and `03-audit.md` are whole-project
   views — recompute them in Phase 4 regardless of which domains moved.
6. **Preserve manual context.** Never delete human-added notes, corrections, or sections in any file.

### Phase 2 — Dispatch domain cartographers (parallel)

Per the agent orchestration protocol (`.claude/rules/workflow.md`), launch the domain mappers
concurrently — they write to disjoint files so there are no conflicts.

1. **Spawn one `snapshot-cartographer` agent per domain** (in a fresh snapshot, all of them; when
   amending, only the changed/new domains) — **in a single message** so they run in parallel.
2. Each agent's prompt must include:
   - The **domain name** and the **exact paths/modules it owns** (from `_orientation.md`).
   - Its **output path**: `docs/architecture/domains/<domain>.md`.
   - The **focus hint**, if any, so it weights the relevant parts of its page.
   - A reminder to follow its agent spec: evidence-backed, concise, read-only, completeness judged from
     code (not optimism), and `UNVERIFIED:` for anything it can't confirm.
3. **Wait for all cartographers to return** before the review pass.

### Phase 3 — Review and gap-fill (one fresh agent)

1. **Dispatch a single `snapshot-reviewer` agent.** It re-reads the code from scratch, verifies every
   domain page against the actual codebase, corrects errors, fills gaps, resolves `UNVERIFIED` items,
   checks cross-domain dependency edges, and flags any area no page covers. It **edits the domain pages
   directly** and writes `docs/architecture/domains/_review.md`.
2. **Read `_review.md`** when it returns. If it reports **coverage gaps** (an area no domain owns) or a
   **major inaccuracy**, dispatch a cartographer for the missing/affected domain and re-review just that
   page before synthesizing. One review round is the default; a second runs only if the first surfaced
   structural gaps.

### Phase 4 — Synthesize the top-level snapshot (orchestrator)

With the domain pages verified, write (or, when amending, update) the four top-level docs. Pull facts
**from the corrected domain pages and `_review.md`** — don't re-derive from raw code. Keep each doc
scannable.

```
docs/architecture/
├── README.md              # entry point: overview + navigation + at-a-glance + watermark
├── 01-features.md         # what's complete / in-progress / planned
├── 02-architecture.md     # layers, component map, data flow, stack, cross-domain graph
├── 03-audit.md            # current-state audit: health, gaps, tech debt, risks, next actions
└── domains/
    ├── _orientation.md    # the partition (Phase 1)
    ├── _review.md         # reviewer summary (Phase 3)
    └── <domain>.md        # one verified page per domain
```

#### `README.md` — entry point

```markdown
# Project Snapshot — {project name}

**Generated:** {YYYY-MM-DD}  ·  **Commit:** `{short hash}`  ·  **Branch:** `{branch}`
**Focus:** {focus hint, or "whole-project"}

## Overview
{6–10 sentences: what the project is and does; the stack; the high-level shape (the domains and how
they fit); the single most important thing to know about its current state.}

## Navigate
- ✅ [Features](01-features.md) — {N} complete · {N} in progress · {N} planned
- 🏗 [Architecture](02-architecture.md) — {N} domains
- 🩺 [Audit](03-audit.md) — {N} risks ({N} high)
- 🗂 Domains: {links to each domains/<domain>.md}

## At a glance
| | |
|---|---|
| Domains | {N} |
| Features complete / total | {N} / {N} |
| Top risks | {N} ({N} high) |
| Test posture | {one phrase from the audit} |
| Snapshot taken | {YYYY-MM-DD} @ `{short hash}` |
```

#### `01-features.md` — feature state

Derive from the domain pages' `Completeness` sections, cross-checked against
`.claude/tasks/MASTER_PLAN.md` (active/completed features) and recent git history. One row per feature.

```markdown
# Features — {YYYY-MM-DD}

| Feature | Status | Domain(s) | Evidence |
|---|---|---|---|
| {name} | COMPLETE | {domain} | {path / test / commit} |
| {name} | IN PROGRESS | {domain} | {what's done, what's left} |
| {name} | PLANNED | {domain} | {where it's referenced} |

## Completed
{Short bullets — the capabilities a user can rely on today.}

## In progress
{What's partially built, and the concrete remaining gap for each.}

## Planned / not yet built
{Referenced or intended but not implemented. Cite where the intent lives.}
```

#### `02-architecture.md` — the architecture

```markdown
# Architecture — {YYYY-MM-DD}

## Stack
{Languages, frameworks, datastores, major libs, runtime/infra — from orientation.}

## Domains & layers
{The domain map: each domain, its responsibility, and which layer it sits in. A table or short list.}

## Component map
{The load-bearing components across domains and how requests/data flow through them — entry point →
business logic → data/state. A small diagram-in-text or ordered flow is enough.}

## Cross-domain dependencies
{The dependency graph between domains, reconciled by the reviewer. Call out any circular edges.}

## Conventions in force
{The layering/quality rules the project holds itself to — summarize from `.claude/rules/*` and note
where the code diverges, linking to the relevant domain page.}
```

#### `03-audit.md` — current-state audit

```markdown
# Current-State Audit — {YYYY-MM-DD}

**Overall health:** {one-line verdict} · **Snapshot:** `{short hash}`

## Health by domain
| Domain | Completeness | Test coverage | Risk |
|---|---|---|---|
| {name} | {DONE/PARTIAL/…} | {sense of coverage} | LOW/MED/HIGH |

## Top risks
{Ranked. Each: what it is, where (cite the domain page), impact, and that it's HIGH/MED/LOW.}

## Technical debt
{The real debt surfaced across domains — grouped, each linking to its domain page.}

## Test & quality posture
{Honest read on coverage and quality gates across the project.}

## Recommended next actions
{3–7 concrete, prioritized actions to move the project forward or de-risk it. Each maps to a domain.}
```

Every top-level doc cross-links to the relevant `domains/<domain>.md` so a reader can drill in. No file
is an orphan; `README.md` is the single entry point.

### Phase 5 — Report

Tell the user:
- The output directory, and whether this was a **fresh** snapshot or an **amend** (and if amended: which
  domains were re-mapped, which were left untouched, and the old → new watermark).
- A tree of the files created/updated.
- Counts: domains, features (complete / total), top risks (and how many high).
- The single most important takeaway about the project's current state (one or two sentences).
- Anything the reviewer flagged under "Needs human input."
- If amending found no changes: that the snapshot was already current.

### Principles

- **Whole-project, always.** The snapshot covers the entire codebase; the focus hint only frames
  emphasis, it never excludes a domain.
- **Evidence over optimism.** "Complete" requires implementing code (and ideally a test). Stubs and
  TODOs are PARTIAL. The reviewer exists to kill completeness theater.
- **Concise by design.** This is a map, not documentation of every function. If a domain page or a
  top-level doc balloons, cut to the load-bearing facts. Not too extensive — by design.
- **Amend, don't rebuild.** Re-running refreshes what changed and preserves human notes. `--new` is the
  only way to start over.
- **Orchestrator delegates; agents map; the reviewer verifies.** You partition and synthesize; you never
  map a domain yourself or skip the review pass.
- **Read-only.** `/snapshot` produces documentation only — it never modifies production code, runs
  migrations, or opens PRs.
