# File architecture & size caps

Stack-agnostic limits that keep files reviewable and functions testable. The
`progress-heartbeat.sh` hook warns (and, in strict mode, blocks) when the file cap is
exceeded; the function cap is enforced by the audit loop (Iteration 2).

## Caps

- **File:** 250 lines max.
- **Function / method / component:** 60 lines max.

Exceeding either is a stop-and-split signal, not a license to keep going. Splitting after
the fact is cheaper than reviewing a 600-line file, but cheaper still is splitting at ~200.

### Legitimately exempt

Generated or vendored files are not subject to the cap: lockfiles, migrations, generated
clients/schema, `*.min.*`, snapshots, and anything your build emits. If your project has a
`.claude/config.yml` with an `exclude_line_cap:` list, the hook honors it; otherwise the
hook skips a built-in set of generated-file patterns.

## Split procedure (when a file crosses 250 lines)

1. **Identify the seams** — group the file's contents by concern (e.g. the public
   shell/entrypoint, the core logic, pure helpers, types/interfaces, constants/config).
2. **Extract the largest independent concern first** into a sibling file, preserving the
   public surface — callers should not need to change beyond their import path.
3. **Keep the entrypoint dumb** — the original file becomes a thin shell that wires the
   extracted pieces together; business logic moves out.
4. **Move constants** out of the logic and into a colocated constants file; replace magic
   numbers/strings with named references.
5. **Re-export** if the language/module system expects a stable path, so external imports
   keep working.
6. **Verify**: the project's validation command still passes, every extracted unit is
   ≤ 60 lines, and no new circular import was introduced.

Adapt names to the language idiom: `feature.ext` (shell) + `feature.logic.ext` +
`feature.utils.ext` + `feature.types.ext` + `feature.constants.ext`, or the closest
convention the codebase already uses. **Match what's there — don't invent a new layout.**

## Anti-patterns

- Letting a file grow past 250 lines because "it's almost done".
- Inlining business logic into a presentational/entrypoint shell.
- Magic numbers/strings scattered instead of named constants.
- Suppressing the size warning instead of splitting.
- A "split" that just moves lines around without separating concerns.
