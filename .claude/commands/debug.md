---
description: Structured bug investigation — Reproduce → Isolate → Hypothesize → Test → Fix → Verify
argument-hint: "[bug description or error message]"
---

# Debug

A disciplined investigation loop for bugs whose cause is not obvious. It forces you to
reproduce and isolate *before* changing code, so you fix the root cause instead of a
symptom. The compiled debug log drops straight into `/commit` (or the active subtask)
as the record of what was wrong and why.

Run this when a bug is reported or observed and the cause isn't immediately clear. Skip
straight to a fix only when the root cause is already confirmed.

---

## Phase 1 — Reproduce

Confirm the bug is real and find its exact boundary.

1. **Gather the failure signal** — full error/stack trace (not truncated), steps to
   reproduce, environment (OS, runtime/version, browser/device), and when it started
   (last known-good commit or recent change).
2. **Confirm reproducibility** — can you reproduce it locally? Deterministic or flaky?
3. **Minimize** — strip context until the bug still occurs with the smallest input.

```
REPRO
Signal : <error or symptom>
Steps  : <minimal numbered steps>
Rate   : <always / N% / flaky>
Env    : <OS, runtime, versions>
```

If you cannot reproduce after reasonable effort: stop, report `CANNOT REPRODUCE`, ask
for more context. Never guess-fix an unconfirmed bug.

## Phase 2 — Isolate

Narrow to the smallest code region that must contain the bug.

1. **Trace the call path** from the signal backward — stack trace from the top frame;
   wrong data backward from use to production; missing output forward from last-good state.
2. **Binary-search the code** — split the suspect region, test which half fails, recurse
   to a single function/block.
3. **`git bisect`** if the regression is recent:
   ```bash
   git bisect start && git bisect bad HEAD && git bisect good <last-good-commit>
   # run the repro at each step until git names the commit
   ```

```
ISOLATION
Region    : <file:line-range or function>
Method    : <stack trace / binary search / git bisect>
Ruled out : <regions confirmed clean>
```

## Phase 3 — Hypothesize

Generate a ranked list of causes *before* testing any.

1. List every plausible cause — don't filter yet.
2. Rank by confidence (HIGH/MED/LOW) with a one-line "why likely".
3. Ordering: Occam's razor (simplest first), recent changes first, nearest cause to the
   signal, known-bad patterns (race, off-by-one, null deref, type coercion).
4. State what each predicts: "If H1 holds, a log at line 42 shows X."

## Phase 4 — Test hypotheses

Confirm or eliminate each, highest-confidence first.

1. Design the **minimal** test that confirms/refutes it (targeted log, unit test, a
   temporary hard-coded value to remove a variable).
2. Run it against the repro case.
3. Record: Confirmed → go to Phase 5; Refuted → eliminate, next; Inconclusive → sharpen.
4. **Stop at the first confirmed hypothesis.** If all are refuted, return to Phase 2.

```
HYPOTHESIS TESTS
H1: <desc> → CONFIRMED — <evidence>
H2: <desc> → REFUTED — <evidence>
```

## Phase 5 — Fix

1. Fix the **root cause**, not a symptom (a symptom fix hides the bug; it returns).
2. Keep the change minimal — easier to review and revert.
3. **Grep for related instances** — if the cause is a pattern (e.g. a missing null
   check), the same bug likely exists elsewhere.
4. Comment only where the reason is non-obvious (hidden constraint, subtle invariant).

```
FIX
Root cause : <one sentence — WHY it happened>
Change     : <file:line — what changed>
Pattern    : <N other instances fixed / none found>
```

## Phase 6 — Verify

1. Re-run the repro — confirm the original symptom is gone.
2. Check edge cases around the fix (empty/null, boundaries 0/max/-1, concurrency).
3. Run the test suite (`/test` or the project's validation command).
4. Read the diff once more for side effects.

```
VERIFY
Repro      : ✅ resolved
Edge cases : <tested — pass / issues>
Suite      : ✅ N pass / ⚠️ N fail
Diff       : ✅ clean / ⚠️ <concern>
```

---

## Debug log (feeds `/commit`)

After all six phases, compile the log below. It becomes the body of the `/commit` entry
(or the `## Resolution` of the active subtask) — no need to rewrite it.

```
DEBUG LOG — <short bug description>
REPRO       : <signal / minimal steps / rate>
ISOLATION   : <file:function:line — how isolated>
ROOT CAUSE  : <one paragraph — what was wrong and why, at the code level>
FIX         : <path:line — what changed and why it fixes the cause, not the symptom>
VERIFY      : repro resolved · suite ✅/⚠️ · related areas checked
```

## Anti-patterns

- **Guess-and-check** — random changes hoping one sticks. Reproduce and isolate first.
- **Symptom fixes** — wrapping the crash in try/catch without understanding it. The bug
  is now hidden; it will return.
- **Fixing the first hypothesis** because it feels right. Rank all, test in order.
- **Skipping verify** — declaring it fixed without re-running the repro.
- **Over-engineering** — rewriting a module for a two-line bug. Match fix scope to cause scope.
- **Not grepping for siblings** — fixing one instance while five identical ones remain.
