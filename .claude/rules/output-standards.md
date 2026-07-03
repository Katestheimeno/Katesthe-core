# Output presentation standards

How responses that produce code or plans are structured, so the user can follow the
reasoning and act on the result without re-asking. Stack-agnostic. Calibrate to task
size — Micro/Small tasks use the short form; Medium+ tasks use the full anatomy.

---

## Response anatomy (Medium+ tasks, in order)

1. **Assumptions block** — if any non-trivial assumption exists (see `assumptions.md`).
2. **Plan** — for Medium+ work, before implementing.
3. **Step announcements** — `-- STEP N OF M --` so progress is legible.
4. **Implementation** — code blocks with commentary between them.
5. **Audit result** — the implementer's self-audit outcome (see `audit-loop.md`).
6. **Next actions** — always last (see below).

Micro/Small tasks skip the empty sections — match length to complexity, don't pad.

> **Caveman mode override.** When the optional caveman compression mode is active
> (see `caveman.md`), it supersedes this verbose anatomy for *prose*: drop the
> decorative blocks, write fragments, keep the Next actions block but render it terse.
> Code, error strings, and safety-critical confirmations are never compressed.

## Code block rules

- Label every block with its **file path** and whether it's new or modified:
  `// NEW: src/auth/login.ts` / `// MODIFIED: src/auth/login.ts`.
- For modified files, show the change in context, not a bare fragment with no anchor.
- Respect the 250-line file / 60-line function caps (`file-architecture.md`) — split if exceeded.
- After each block or logical group, note: *what it does / why this approach / what to watch*.

## Progressive delivery

For multi-file work, deliver step by step with commentary between steps — no wall of
code, and never "I'll continue in the next message." Finish the file you started.

## Decision rationale

Document non-trivial decisions: an inline `// DECISION:` comment for local choices, or a
short named block for larger ones — chosen approach vs the alternative, and why.

## Next actions block (end of every substantive response)

```
NEXT ACTIONS
1. <specific, actionable without further clarification>

OPEN QUESTIONS
- <unresolved item, or "none">
```

If nothing remains: "No remaining tasks in this sequence. Awaiting new direction."

## Anti-patterns

- Filler ("Great question!", restating the request back).
- Placeholder code (`// TODO: implement`, `// add logic here`) presented as done.
- Partial files, or deferring the rest to a later message.
- Walls of code with no step-by-step commentary.
- Overconfident claims with no rationale.
- Omitting the Next actions block on substantive work.
