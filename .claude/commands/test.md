---
description: Discover and run the project test suite, then gate /commit on the result
argument-hint: "[optional test command override]"
---

# Test

Run the project's tests as an explicit gate between finishing code and `/commit`. It
auto-detects the test command, runs it, and reports a clear pass/fail — a failing run
must block the commit, and "no tests found" is a documented skip, never a silent pass.

If an argument is given, use it verbatim as the test command (skip discovery).

---

## 1. Discover the test command

Check in priority order; stop at the first match.

| # | Source | How to check |
|---|--------|--------------|
| 1 | `.claude/config.yml` → `test_command` | non-empty after parsing |
| 2 | `package.json` → `scripts.test` | `jq -r '.scripts.test' package.json` — skip the `"test"` placeholder |
| 3 | `Makefile` | `grep -q '^test:' Makefile` |
| 4 | `pyproject.toml` / `pytest.ini` | file has `[tool.pytest` or `[pytest]` → `pytest` (prefer `uv run pytest` if `uv.lock` exists) |
| 5 | `go.mod` present | `go test ./...` |
| 6 | `Cargo.toml` present | `cargo test` |
| 7 | none found | emit `NO_TEST_SUITE` (see Skip protocol) |

Print before running:

```
TEST COMMAND : <command>
Source       : <config / package.json / Makefile / auto-detected / argument>
```

If nothing is found, offer:

```
TEST COMMAND : none detected

  A — Skip and document (set test_command: "" in .claude/config.yml)
  B — Tell me the command to run
```

Wait for the choice before proceeding.

## 2. Run

Execute the command, stream output, capture the exit code. If the binary doesn't exist,
emit `TEST ERROR: command not found — <cmd>` and stop.

## 3. Evaluate

**Exit 0 — pass:**

```
✅ TESTS PASSED
Command : <cmd>
Output  : <last 5 lines, or "no output">
```

Tell the user: "Run `/commit`."

**Non-zero — fail:**

```
❌ TESTS FAILED
Command   : <cmd>
Exit code : <N>
Output (last 30 lines):
<output>
```

Do **not** advance to `/commit`. Tell the user: "Fix the failures and re-run `/test`."
If a subtask is active (`[IN_PROGRESS]`), note the failure in its `## Validation Log`.

## Skip protocol

When `/test` is skipped (no suite, or the user chose to skip), the `/commit` entry or
the active subtask **must** record it:

```
## Test coverage
no test suite — /test skipped explicitly
```

If a suite exists but the user skipped it, record the reason.

## Don't

- Auto-advance to `/commit` after a failing run.
- Treat "no tests found" as a pass — it is a skip that must be documented.
- Modify test files here — that's implementation work; do it before `/test`.
