#!/usr/bin/env bash
# Shared helpers for workflow-kit hooks. Sourced, not executed directly.

wk_find_root() {
  if [[ -n "${CLAUDE_PROJECT_DIR:-}" && -f "${CLAUDE_PROJECT_DIR}/.claude/CLAUDE_ENTRYPOINT.md" ]]; then
    echo "${CLAUDE_PROJECT_DIR}"
    return 0
  fi
  local d="$PWD"
  while [[ "$d" != "/" && -n "$d" ]]; do
    if [[ -f "$d/.claude/CLAUDE_ENTRYPOINT.md" ]]; then
      echo "$d"
      return 0
    fi
    d="$(dirname "$d")"
  done
  return 1
}

wk_strict() {
  [[ "${WORKFLOW_KIT_STRICT:-0}" == "1" ]]
}

# Print a warning to stderr. In strict mode, also exit 2 (blocks the tool call).
wk_warn() {
  echo "workflow-kit: $1" >&2
  if wk_strict; then
    exit 2
  fi
}

# Echo the active feature name, or return 1 if none.
wk_active_feature() {
  local plan="$1/.claude/tasks/MASTER_PLAN.md"
  [[ -f "$plan" ]] || return 1
  local v
  v="$(awk '
    /^## Active$/ {flag=1; next}
    /^## / {flag=0}
    flag && /^→/ {
      sub(/^→[[:space:]]*/, "")
      sub(/[[:space:]]*$/, "")
      print
      exit
    }
  ' "$plan")"
  [[ -z "$v" || "$v" == "none" ]] && return 1
  echo "$v"
}

wk_today() { date -u +%Y-%m-%d; }
