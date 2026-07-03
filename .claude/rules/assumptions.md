# Assumption transparency & conflict detection

Every assumption the user did not explicitly state must be surfaced — before or during
the work, never hidden. This is a behavioral rule the orchestrator, planner, and
implementer all read; it is stack-agnostic.

---

## Classification

| Type | Action | Example |
|------|--------|---------|
| **A** | **Blocking** — stop and ask | Unclear data model, ambiguous requirement, two valid interpretations |
| **B** | **Directional** — state it, proceed | Choosing one valid approach over another equally valid one |
| **C** | **Conventional** — note it, proceed | Following an established project pattern |
| **D** | **Trivial** — no disclosure needed | Standard language idioms, obvious defaults |

**Never misclassify a Type A as B/C to avoid asking.** When genuinely unsure which
tier an assumption is, treat it as one level more blocking.

## Disclosure block

When any Type B or C assumption applies, open the response with:

```
ASSUMPTIONS
-> [Label]: [what you assumed] — [why]
   Alternative considered: [what you did not choose]
   If wrong: [what to change and where]
```

Keep it tight — one entry per real assumption, not hedging filler.

## Recording

Type A and B assumptions that shape the work get recorded where the work lives:

- **Feature work:** under a `## Assumptions` section in the active subtask file
  (`.claude/tasks/<feature>/NNN-*.md`).
- **Simple tasks:** in the `.claude/tasks/general/SESSION_LOG.md` entry.

So the next session (or `/recover`) can see what was assumed, not just what was done.

## Conflict detection

At session start and before any action, check the request against prior locked
decisions (MASTER_TASKS `## Locked decisions`, `completed/*.md` summaries, persisted
`/mem` memories). When the request contradicts one, surface it before proceeding:

```
CONFLICT DETECTED
Current request: [what is being asked]
Prior decision:  [what was decided before]
Source:          [file + where]

  A — Honor the prior decision
  B — Override it (record the reversal in MASTER_TASKS ## Locked decisions)
  C — Merge both approaches
```

Never proceed past a conflict until it is resolved. On override, record a one-line
reversal note so the history stays honest.

## "I don't know" protocol

When you lack the information to be confident, say so plainly: "I don't have enough
information to be confident about X" + what you'd need to proceed reliably. Never
fabricate confidence; never bury real uncertainty under hedging language.

## Anti-patterns

- Proceeding silently on a blocking (Type A) assumption.
- Overriding a logged decision without surfacing the conflict.
- Presenting one approach as "the only way" when alternatives exist.
- Fabricating confidence, or the reverse — excessive hedging that obscures the actual assumption.
