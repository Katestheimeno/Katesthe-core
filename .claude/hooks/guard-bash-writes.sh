#!/usr/bin/env bash
# PostToolUse(Bash): catch in-place writes that bypass the Edit/Write hook
# (sed -i, awk -i inplace, tee, truncate, > redirection) and enforce the 250-line
# size cap (rules/file-architecture.md) on the files they touch. Best-effort path
# parser — progress-heartbeat.sh covers the Edit|Write|MultiEdit path; this closes
# the gap where shell commands rewrite a file without going through those tools.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=_lib.sh
source "${SCRIPT_DIR}/_lib.sh"

ROOT="$(wk_find_root)" || exit 0

INPUT="$(cat || true)"
[[ -z "$INPUT" ]] && exit 0

CMD=""
if command -v jq >/dev/null 2>&1; then
  CMD="$(printf '%s' "$INPUT" | jq -r '.tool_input.command // empty' 2>/dev/null || true)"
fi
if [[ -z "$CMD" ]]; then
  CMD="$(printf '%s' "$INPUT" | grep -oE '"command"[[:space:]]*:[[:space:]]*"[^"]+"' | head -n1 | sed 's/.*"\([^"]*\)"$/\1/')"
fi
[[ -z "$CMD" ]] && exit 0

# Quick-reject if no in-place write indicators are present.
if ! grep -qE '(sed[[:space:]]+-i|awk[[:space:]]+-i[[:space:]]+inplace|(^|[[:space:]|;&])tee[[:space:]]|truncate[[:space:]]|>[>]?[[:space:]]*[^|&;[:space:]])' <<< "$CMD"; then
  exit 0
fi

# Extract candidate file paths (any token with a file extension). Non-existent
# paths and exempt files are filtered by wk_over_cap, so over-matching is harmless.
candidates="$(grep -oE '[A-Za-z0-9_./-]+\.[A-Za-z0-9_]+' <<< "$CMD" | sort -u)"
[[ -z "$candidates" ]] && exit 0

while IFS= read -r rel; do
  [[ -z "$rel" ]] && continue
  case "$rel" in
    /*) abs="$rel" ;;
    *)  abs="${ROOT}/${rel}" ;;
  esac
  lines="$(wk_over_cap "$ROOT" "$abs")"
  if [[ -n "$lines" ]]; then
    wk_warn "Size cap (via Bash): ${rel} is ${lines} lines (>250). See rules/file-architecture.md — split before continuing."
  fi
done <<< "$candidates"

exit 0
