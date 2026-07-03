# Source / Attribution

- **Upstream repo:** https://github.com/Leonxlnx/taste-skill
- **Path in upstream:** `skills/taste-skill/SKILL.md`
- **Author:** Leonxlnx
- **License:** MIT © 2026 Leonxlnx
- **Imported on:** 2026-05-25
- **Folder name rationale:** `design-taste-frontend` matches the `name:` field in
  the skill's YAML frontmatter (the upstream repo folder is just `taste-skill`).
- **Local modifications:** none — SKILL.md is verbatim from upstream.

## Variants NOT imported
The upstream repo ships 10 sibling skills under `skills/`:
- `brandkit`, `brutalist-skill`, `gpt-tasteskill`, `image-to-code-skill`,
  `imagegen-frontend-mobile`, `imagegen-frontend-web`, `minimalist-skill`,
  `output-skill`, `redesign-skill`, `soft-skill`, `stitch-skill`

Only the general-purpose `taste-skill` (frontmatter `name: design-taste-frontend`) was
imported. To add a sibling variant later, fetch from
`https://raw.githubusercontent.com/Leonxlnx/taste-skill/main/skills/<variant>/SKILL.md`
and drop it under `.claude/skills/<variant>/`.
