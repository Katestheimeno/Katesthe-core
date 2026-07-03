# Source / Attribution

- **Upstream repo:** https://github.com/nextlevelbuilder/ui-ux-pro-max-skill
- **Upstream path:** `.claude/skills/brand/`
- **Author:** nextlevelbuilder
- **License:** MIT
- **Plugin:** ui-ux-pro-max v2.5.0 (this skill is one of 7 shipped together)
- **Imported on:** 2026-05-25
- **Local modifications:** none — verbatim from upstream.

## Part of the ui-ux-pro-max plugin family
This skill ships alongside 6 sibling skills from the same plugin:
- `ui-ux-pro-max` (master — UI/UX design intelligence, searchable CSV databases)
- `banner-design`, `brand`, `design`, `design-system`, `slides`, `ui-styling`

All seven were imported in one batch; sibling SOURCE.md files mirror this one.

## Canvas fonts NOT imported
The `ui-styling/canvas-fonts/` directory in upstream ships 60+ TTF files (5.3 MB)
used for canvas/slide image rendering. These were intentionally skipped because:
1. Image rendering is rarely used in Claude Code chat workflows.
2. They bloat the workflow-kit repo by ~5 MB.
3. They can be re-added later if canvas/slide features are exercised — fetch from
   `https://github.com/nextlevelbuilder/ui-ux-pro-max-skill/tree/main/.claude/skills/ui-styling/canvas-fonts`.

