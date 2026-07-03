# Post-implementation audit loop

A structured self-audit the **implementer** runs after writing code, **before** reporting
back to the orchestrator and before the `code-reviewer` agent sees it. Two-gate model:

1. **Audit loop (this file)** — structured, exhaustive self-correction by the author, in
   the same context that wrote the code. Catches what you can check against a checklist.
2. **`code-reviewer` agent** — independent fresh eyes with no implementation context.
   Catches what the author rationalized.

They are **not** redundant. The audit loop runs first; only after it reports `✅ READY`
should the implementer report completion. Assume your first draft contains at least one
violation — overconfidence is itself a violation.

This is **stack-agnostic**. Stack-specific checks (framework layering, ORM patterns,
component rules) live in `.claude/rules/` and `.claude/CONTEXT_MAP.md` — fold them into
the matching iteration below.

---

## Step 0 — Compute the tier

Run `git diff --shortstat HEAD` (or `--cached` if staged). Capture files-changed and
lines added+deleted. The tier is a deterministic function of diff size — **never
downgrade to skip work**:

| Tier    | Condition                        | Sweeps                                                       |
| ------- | -------------------------------- | ------------------------------------------------------------ |
| Micro   | files ≤ 1 AND lines ≤ 20         | **1 combined sweep** — Iter 1+2+3 merged; skip Iter 4        |
| Small   | files ≤ 5 AND lines ≤ 100        | **2 sweeps** — Iter 1, then Iter 2+3 merged; skip Iter 4     |
| Medium+ | files > 5 OR lines > 100         | **Full 4 sweeps** — 1 → 2 → 3 → 4, sequential, never merged  |

Print before the first iteration:

```
AUDIT TIER — <Micro|Small|Medium+>  (files=<N>, lines=±<N>)
```

If `git diff` fails (no repo/commits) or returns empty, assume **Medium+** — the safest
default. Run iterations **sequentially**; fix inline, never defer; don't advance until the
current iteration is clean.

---

## Iteration 1 — Architecture & design

- [ ] **BOUNDARIES** — imports respect the project's layer/module direction (no upward or
      illegal lateral imports). See `.claude/rules/*.md` for the project's specific layering.
- [ ] **REUSE** — could this new code be replaced by extending something that already
      exists? You read neighboring code before writing — confirm you didn't duplicate it.
- [ ] **PUBLIC SURFACE** — cross-module access goes through the intended public entrypoint,
      not deep internal paths.
- [ ] **SINGLE RESPONSIBILITY** — each new unit does one thing; no grab-bag modules.
- [ ] **NO DEAD ENDS** — new control paths terminate correctly (no unreachable branches,
      no half-wired features).

## Iteration 2 — Size, complexity & performance

- [ ] **FILE LENGTH** — every touched file ≤ 250 lines (`.claude/rules/file-architecture.md`).
- [ ] **FUNCTION LENGTH** — every function/method ≤ 60 lines.
- [ ] **COMPLEXITY** — no function juggling more than one concern; extract helpers.
- [ ] **HOT PATHS** — no N+1, no repeated work in loops, no unbounded result sets, no
      synchronous external calls on a hot path.
- [ ] **PERF NOTES** — any non-obvious optimization carries a one-line rationale comment.

## Iteration 3 — Types, validation & data safety

- [ ] **INPUT VALIDATION** — caller-supplied data validated at the boundary before it
      reaches business logic.
- [ ] **ERROR HANDLING** — every async/fallible op handles errors (no silent swallow); the
      project's error convention (codes, types, messages) is followed.
- [ ] **TYPES** — no escape hatches (`any`, unchecked casts, non-null assertions) without
      an inline proof comment. Non-trivial functions have explicit return types where the
      language supports them.
- [ ] **NO SUPPRESSION** — no `@ts-ignore` / `# type: ignore` / `eslint-disable` / lint
      suppressions without a single-line justification + tracked issue.
- [ ] **SECRETS** — no secrets in code or logs; no PII in logs.

## Iteration 4 — Dependency & import hygiene (Medium+ only)

- [ ] **UNUSED IMPORTS** — no imported name that never appears in the file body.
- [ ] **CIRCULAR DEPS** — no module imports something that (transitively) imports it back.
- [ ] **INTERNAL IMPORTS** — import from package public APIs, not vendored internal paths.
- [ ] **GENERATED ARTIFACTS** — migrations/schema/codegen/lockfiles regenerated if their
      inputs changed.

---

### Tier overrides

- **Micro** — walk the union of Iter 1+2+3 in one pass; skip Iter 4; print one combined
  line. **Small** — Iter 1, then a merged Iter 2+3; skip Iter 4. **Medium+** — all four.

## Required final block (all tiers)

```
┌─────────────────────────────────────────────────────────┐
│  POST-IMPLEMENTATION AUDIT SUMMARY                        │
├──────────────────┬────────────────────────────────────────┤
│  Iter 1 Arch     │  found [n] / fixed [n] — [list|none]   │
│  Iter 2 Size/Perf│  found [n] / fixed [n] — [list|none]   │
│  Iter 3 Types    │  found [n] / fixed [n] — [list|none]   │
│  Iter 4 Deps     │  found [n] / fixed [n]  | N/A (tier)   │
│  Final status    │  ✅ READY  |  ⚠️ NEEDS REVIEW          │
└──────────────────┴────────────────────────────────────────┘
```

Never fabricate findings. If the final status is `⚠️ NEEDS REVIEW`, **stop** — do not
report the subtask done, do not let it advance to the code-reviewer; fix and re-run first.

## Anti-patterns

- Skipping the audit because the change felt small.
- Choosing a lower tier than the diff dictates.
- Running iterations out of order or merging them outside the Micro/Small tiers.
- Fabricating a zero-issue report.
- Advancing to review/completion before `✅ READY`.
