# Source / Attribution

- **Upstream repo:** https://github.com/JuliusBrussee/caveman
- **Author:** Julius Brussee (@JuliusBrussee)
- **License:** MIT
- **Imported on:** 2026-06-24
- **Local modifications:** none — `SKILL.md` and `README.md` are verbatim from upstream `skills/caveman/`.

## The caveman family in this bundle

This is the **core** skill of a set vendored together from the same upstream repo:

| Vendored as | Upstream path | Role |
|---|---|---|
| `skills/caveman/` | `skills/caveman/` | The `/caveman [lite\|full\|ultra\|wenyan]` compression toggle (this folder) |
| `skills/caveman-commit/` | `skills/caveman-commit/` | Terse Conventional Commit messages |
| `skills/caveman-review/` | `skills/caveman-review/` | One-line PR review comments |
| `skills/caveman-stats/` | `skills/caveman-stats/` | Session token usage + lifetime savings |
| `skills/caveman-compress/` | `skills/caveman-compress/` | Rewrite memory files (e.g. `CLAUDE.md`) into caveman-speak (Python scripts vendored) |
| `skills/caveman-help/` | `skills/caveman-help/` | In-session help for the caveman commands |
| `skills/cavecrew/` | `skills/cavecrew/` | Caveman subagents — paired with `agents/cavecrew-*.md` |
| `hooks/caveman-config.js` | `src/hooks/caveman-config.js` | Shared config resolver + symlink-safe flag I/O |
| `hooks/caveman-activate.js` | `src/hooks/caveman-activate.js` | `SessionStart` hook — writes the mode flag, injects this `SKILL.md` as context |
| `hooks/caveman-mode-tracker.js` | `src/hooks/caveman-mode-tracker.js` | `UserPromptSubmit` hook — tracks `/caveman` toggles, per-turn reinforcement, `/caveman-stats` |
| `hooks/caveman-stats.js` | `src/hooks/caveman-stats.js` | Reads the session log, counts tokens saved |
| `hooks/caveman-statusline.{sh,ps1}` | `src/hooks/` | Statusline badge `[CAVEMAN] ⛏` reading the mode flag |
| `agents/cavecrew-{investigator,builder,reviewer}.md` | `agents/` | The three cavecrew subagents |

## How it activates in this kit

The hooks are wired in `settings.json.example`:

- `SessionStart` → `caveman-activate.js` reads `__dirname/../skills/caveman/SKILL.md`
  (i.e. this file) and injects the active intensity level's rules as context. The
  kit's `.claude/hooks/` + `.claude/skills/` sibling layout matches that lookup, so
  the skill is the single source of truth — no duplicated ruleset.
- `UserPromptSubmit` → `caveman-mode-tracker.js` updates the mode flag on `/caveman …`
  or natural-language triggers, and reinforces the rules every turn.
- The mode flag lives at `${CLAUDE_CONFIG_DIR:-~/.claude}/.caveman-active` — **per user,
  not per project**. Default mode is `full`; override with `CAVEMAN_DEFAULT_MODE`, a
  user config, or a repo-local `.caveman/config.json` / `.caveman.json`.

**Requires Node ≥18** for the hooks (stdlib only, no `npm install`).
The `caveman-compress` scripts require Python 3 (stdlib only).

## Precedence vs the kit's output standards

Auto-on caveman deliberately overrides the verbose response anatomy in
`rules/output-standards.md`. The reconciliation rule lives in `rules/caveman.md`.

## What was NOT imported

- The standalone installer (`install.sh`, `install.ps1`, `bin/install.js`) and the
  multi-agent harness configs — the kit's own `install.sh` copies these skills/hooks/
  agents instead.
- `caveman-shrink` (the MCP middleware that compresses tool descriptions) — published
  separately on npm (`caveman-shrink`); install it directly if you want it.
- `benchmarks/`, `evals/`, `tests/`, `docs/`, and the OpenClaw / Codex / Gemini
  install paths — not relevant to a Claude Code bundle.
