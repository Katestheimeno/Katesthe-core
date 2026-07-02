# Documentation discipline

## Migration Notes

**Source files merged (4):** `docs/adr-and-living-docs.mdc`, `docs/docs-and-schema.mdc`, `docs/docs-core-front-obsidian-sync.mdc`, `django/00-django-docs-changelog.mdc`.

**Conflicts resolved (C4, C9):** the changelog/traceability policy was restated across all four sources. Merged into one §1 traceability table. The OpenAPI gate rule lives here; the concrete command lives in `.claude/skills/openapi-validate-skill.md`.

**Deliberately removed:** none. Obsidian wiki-link guidance moved to §6 (optional vault).

---

## 1. Three-layer documentation map

The project maintains several document kinds. Touch whatever applies for a given change.

| Layer | Where | Who reads it | When you write it |
|---|---|---|---|
| **Living docs** | **`docs/README.md`** (index), topical files under **`docs/*.md`**, frontend guides under **`docs/front/**`**, domain folders (e.g. `docs/ai_core/`) | Frontend devs, integrators, contributors | When behavior, APIs, or flows change |
| **Traceability** | **`docs/changes/YYYYMMDD_*_<slug>.md`** (and similar dated slugs already in tree) | Release / PR audit | On substantive changes (see §2) |
| **Changelog** | **`CHANGELOG/`** (dated entry files per repo convention) | Release engineering | Paired with traceability for shipped work |
| **Session handoff** | **`.cursor/changes/`** (optional; see `.claude/skills/session-handoff-skill.md`) | The next agent session | For continuity on long tasks |

**Note:** Some projects use an Obsidian **`docs/core/`** vault with wiki-links; **Rhitoric currently does not ship that tree** — follow `.cursor/rules/docs-and-schema.mdc` if it adds one. Until then, prefer plain Markdown links from `docs/README.md`.

## 2. Traceability file — required template

`docs/changes/YYYYMMDD_HHMMSS_<slug>.md`:

```markdown
# Change: <Short Title>

**Date:** YYYY-MM-DD HH:MM
**Author:** AI-assisted / <name>
**Prompt Scope:** <one sentence>

## Summary
<2-4 sentences>

## Reason for Change
<feature request / bug fix / refactor / tech debt>

## Files Modified
| File | Lines | Change |
|------|-------|--------|
| app/services/x.py | 45-89 | Added `invite_user()` |

## Refactors Performed
- <list or "None">

## Reused Logic
- <list or "None">

## Related Tests Added
| File | Test | Covers |
|------|------|--------|
| tests/.../test_x.py | test_invite_sends_email | Email dispatch |

## Documentation Updated
- `/docs/services/user.md` — added invite_user section
```

## 3. CHANGELOG

- Follows Keep-a-Changelog sections: **Added / Changed / Fixed / Refactored / Removed / Security**.
- One concise line per item. Max two lines.
- Link to the traceability file for complex changes: `See: docs/changes/20260415_140000_next-steps.md`.
- Inspect recent entries before writing new ones — **match this repo's existing cadence and tone**; don't invent a new format.

## 4. OpenAPI schema

- **`@extend_schema`** on DRF views where responses, bodies, or status codes are non-obvious. Use tags that match the product (`Game`, `Accounts`, `E-learning`, `AI Core`, `Notifications`, …) — mirror existing `extend_schema` usage in each app.
- **List/detail schema quirks:** follow patterns already in the repo (`config/spectacular*.py`, existing controllers). Do not invent envelope serializers unless the codebase already uses them.
- **422 examples are per-operation.** Do not copy-paste an unrelated validation body onto a different endpoint.
- **Validation gate:** `python manage.py spectacular --validate --fail-on-warn` must exit 0 before merge when schema is touched (`.claude/skills/openapi-validate-skill.md`).

## 5. ADRs — Architecture Decision Records

**Write one when:** introducing a new pattern, major design choice, performance tradeoff, or security decision worth remembering.

**Location:** Prefer `docs/architecture/` or a new `docs/architecture/decisions/` folder with **`ADR-NNN-<kebab-title>.md`** naming — **create the folder if the team adopts ADRs here**; many Rhitoric decisions today live inline in `docs/*.md` and `docs/changes/`.

**Template:**

```markdown
# ADR-NNN: <Title>

- **Status:** Proposed | Accepted | Superseded
- **Date:** YYYY-MM-DD

## Context
<Why this decision exists. What constraint drove it.>

## Decision
<What we are doing.>

## Consequences
**Positive:** <gains>
**Negative:** <cost>
**Trade-offs:** <alternatives considered>

## Related docs
- `docs/README.md`
- `docs/central-arch.md` (or other topical docs)
```

**Supersession:** never delete an ADR. Mark `Status: Superseded by ADR-NNN` and add a link.

## 6. Deep documentation hubs (optional)

If the team introduces **`docs/core/`** as an Obsidian vault, use wiki-links inside that vault and keep **`docs/core/README.md`** as the hub. **Rhitoric today** uses flat / grouped Markdown under `docs/` instead; do not block work on a vault that is not present.

## 7. Frontend contract sync

- Changes to **client-visible HTTP or WebSocket behavior** should update the relevant file under **`docs/front/`** and any overview in **`docs/README.md`** (e.g. `docs/front/AUTH_FLOW.md`, `docs/GAME_FRONTEND_ENDPOINTS_AND_FLOW.md`, `docs/front/Learning/*`).
- Contract drift between backend behavior and documented flows is a merge blocker for API-facing work.

## 8. Documentation gate (enforced)

Before marking any change "done":

1. Scan `docs/` for impacted sections (start at `docs/README.md`).
2. Update or rewrite any outdated page.
3. No public API, permission class, or model surface is left undocumented without team agreement.
4. Create the **`docs/changes/...`** traceability file when the team requires it for the change class.
5. Add a **`CHANGELOG/`** entry matching existing filename conventions.
6. Optionally write **`.cursor/changes/...`** for session continuity.
