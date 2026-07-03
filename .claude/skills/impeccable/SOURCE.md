# Source / Attribution

- **Upstream repo:** https://github.com/pbakaus/impeccable
- **Path in upstream:** `.agents/skills/impeccable/`
- **Author:** Paul Bakaus (@pbakaus)
- **License:** Apache 2.0
- **Imported on:** 2026-05-25
- **Local modifications:** none — `SKILL.md` and all 36 `reference/*.md` files are verbatim from upstream.

## What was NOT imported
- `scripts/` (50+ Node.js files) — these power the optional `npx impeccable` CLI for
  static anti-pattern detection and the `live` browser-iteration mode. They require
  `npm install` of the standalone package and were intentionally skipped.
- `agents/openai.yaml` — OpenAI-specific harness config; not relevant for Claude Code.

## Consequences of the omission
The skill still works for in-conversation design work: the design laws, command table,
and all 36 `reference/*.md` files load normally. What WILL break:
- `node .agents/skills/impeccable/scripts/load-context.mjs` — instead, manually load
  `PRODUCT.md` / `DESIGN.md` from project root with the Read tool.
- `node .agents/skills/impeccable/scripts/pin.mjs <pin|unpin> <command>` — pin/unpin
  shortcuts cannot be created.
- `$impeccable live` — browser visual-variant mode is unavailable.

For the full CLI, the user can install separately: `npx impeccable --help`.
