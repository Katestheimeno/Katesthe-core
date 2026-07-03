# Caveman mode (token-compressed output)

The bundle vendors the [caveman](https://github.com/JuliusBrussee/caveman) skill family
(`skills/caveman*`, `skills/cavecrew`, `agents/cavecrew-*`, `hooks/caveman-*`). When
active, Claude answers in compressed "caveman speak" — drops articles, filler, and
pleasantries while keeping all technical substance — cutting ~65–75% of output tokens.
This rule defines how that interacts with the rest of the kit. It is **opt-in but
auto-on**: the hooks turn it on from message one unless you disable it.

---

## Activation

Wired in `settings.json.example` (Node ≥18 required for the hooks, stdlib only):

- `SessionStart` → `hooks/caveman-activate.js` writes the mode flag at
  `${CLAUDE_CONFIG_DIR:-~/.claude}/.caveman-active` and injects the active intensity
  level from `skills/caveman/SKILL.md` (the single source of truth) as context.
- `UserPromptSubmit` → `hooks/caveman-mode-tracker.js` updates the flag on `/caveman …`
  or natural-language triggers ("talk like caveman", "be brief", "normal mode") and
  reinforces the rules each turn.
- `statusLine` → `hooks/caveman-statusline.sh` renders `[CAVEMAN] ⛏` while active.

Default level is `full`. Switch with `/caveman lite|full|ultra|wenyan`. Turn off with
`/caveman off`, "stop caveman", or "normal mode". Pin a per-project default with a
checked-in `.caveman/config.json` (`{"defaultMode": "lite"}`); pin a per-user default
with `CAVEMAN_DEFAULT_MODE` or `~/.config/caveman/config.json`. The flag is **per user,
not per project** — caveman is on across all your projects once wired, until disabled.

If you do **not** want caveman on by default, leave the two caveman hook entries and the
`statusLine` block out of your merged `.claude/settings.json`; the skills still load
on demand when you type `/caveman`.

## Precedence over output-standards.md

`output-standards.md` mandates a verbose response anatomy (assumptions block, plan,
step banners, prose commentary, a trailing **Next actions** block). Caveman's terse
fragment style directly contradicts that. **When caveman mode is active, caveman wins**
for prose: drop the decorative anatomy, write fragments, no filler.

Caveman compresses *style*, never *substance*. The following survive verbatim regardless
of level, per the caveman skill's own Auto-Clarity / Boundaries sections:

- **Code, commits, PRs, diffs** — written normally, never compressed.
- **Exact error strings, API names, CLI commands, paths, symbols** — verbatim.
- **Safety-critical prose** — security warnings, irreversible/destructive-action
  confirmations, and multi-step sequences where fragment order risks misreading drop
  caveman for that part, then resume. This dovetails with the kit's clarification gate
  in `workflow.md` and the assumption/conflict surfacing in `assumptions.md` — those
  *decisions* still happen; only their wording compresses.
- **The Next actions block** stays (it is actionable substance), but rendered terse —
  a tight numbered list, not prose.

In short: caveman changes how the kit *talks*, not what the kit *does*. The workflow,
audit-loop, quality gates, and conflict detection all still run.

## Anti-patterns

- Compressing code, error strings, or commit bodies "to save tokens" — substance only
  ever shrinks in prose, never in the technical payload.
- Staying terse through a destructive-action confirmation or security warning.
- Announcing the mode ("caveman mode on", "me caveman think") — never self-reference.
- Dropping the Next actions block entirely because "caveman is terse" — keep it, tighten
  it.
