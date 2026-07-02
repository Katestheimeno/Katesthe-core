#!/usr/bin/env bash
# Ensure the task-tracking data scaffolding exists under .claude/tasks/.
# Idempotent: creates only what's missing, never overwrites existing files.
# This heals the common case where the kit is installed but .claude/tasks/ is
# empty or partially deleted, so /flow (pln|impl|cmplt) has the dirs and the
# MASTER_PLAN.md registry it depends on.
#
# It does NOT install agents or hooks — those are kit-owned files that only
# install.sh can place. If the kit itself is not installed (no
# CLAUDE_ENTRYPOINT.md), this exits non-zero so the caller can tell the user.
#
# Usage: ensure-tasks.sh [--dry-run] [--quiet]
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=_lib.sh
source "${SCRIPT_DIR}/_lib.sh"

DRY=0
QUIET=0
while [[ $# -gt 0 ]]; do
  case "$1" in
    --dry-run) DRY=1; shift ;;
    --quiet)   QUIET=1; shift ;;
    -h|--help) sed -n '2,12p' "$0"; exit 0 ;;
    *) echo "ensure-tasks: unknown flag: $1" >&2; exit 1 ;;
  esac
done

ROOT="$(wk_find_root)" || {
  echo "ensure-tasks: could not locate .claude/CLAUDE_ENTRYPOINT.md." >&2
  echo "  The workflow-kit is not installed here. Run install.sh first." >&2
  exit 1
}

TASKS="${ROOT}/.claude/tasks"
PLAN="${TASKS}/MASTER_PLAN.md"
LOG="${TASKS}/general/SESSION_LOG.md"

CREATED=()

note() { CREATED+=("$1"); }

ensure_dir() {
  local d="$1" rel="$2"
  [[ -d "$d" ]] && return 0
  if [[ "$DRY" -eq 1 ]]; then note "[dry-run] mkdir ${rel}"; else mkdir -p "$d"; note "created ${rel}/"; fi
}

ensure_file() {
  local f="$1" rel="$2" body="$3"
  [[ -f "$f" ]] && return 0
  if [[ "$DRY" -eq 1 ]]; then
    note "[dry-run] write ${rel}"
  else
    mkdir -p "$(dirname "$f")"
    printf '%s' "$body" > "$f"
    note "created ${rel}"
  fi
}

ensure_dir "${TASKS}"                 "tasks"
ensure_dir "${TASKS}/completed"       "tasks/completed"
ensure_dir "${TASKS}/archive"         "tasks/archive"
ensure_dir "${TASKS}/general"         "tasks/general"

# Keep the otherwise-empty bucket dirs tracked in git.
ensure_file "${TASKS}/completed/.gitkeep" "tasks/completed/.gitkeep" ""
ensure_file "${TASKS}/archive/.gitkeep"   "tasks/archive/.gitkeep"   ""

ensure_file "${PLAN}" "tasks/MASTER_PLAN.md" '# Master Plan
Last Updated: (set when you edit)

## Active
→ none

## Queue
(empty)

## Completed
(none yet)

## Deferred / On Hold
(none)
'

ensure_file "${LOG}" "tasks/general/SESSION_LOG.md" '# Session Log
Date: (optional)

## Tasks
<!-- Append-only. Example: - [COMPLETED] YYYY-MM-DD — one-line description -->

## Notes
<!-- Freeform session notes. -->
'

if [[ "${QUIET}" -eq 1 ]]; then
  exit 0
fi

if [[ "${#CREATED[@]}" -eq 0 ]]; then
  echo "ensure-tasks: task architecture already present at ${TASKS}"
else
  echo "ensure-tasks: bootstrapped task architecture at ${TASKS}"
  for c in "${CREATED[@]}"; do echo "  + ${c}"; done
fi
