#!/usr/bin/env bash
# SessionStart hook: prints current task-checkpoint state so Claude starts aligned.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=_lib.sh
source "${SCRIPT_DIR}/_lib.sh"

ROOT="$(wk_find_root)" || exit 0
PLAN="${ROOT}/.claude/tasks/MASTER_PLAN.md"
MAP="${ROOT}/.claude/CONTEXT_MAP.md"

echo "── workflow-kit: task-checkpoint state ─────────"
if [[ -f "$PLAN" ]]; then
  echo "MASTER_PLAN.md: $PLAN"
  plan_updated="$(grep -m1 '^Last Updated:' "$PLAN" | sed 's/^Last Updated:[[:space:]]*//' || true)"
  [[ -n "$plan_updated" ]] && echo "  Last Updated: $plan_updated"
  feat="$(wk_active_feature "$ROOT" 2>/dev/null || true)"
  if [[ -n "$feat" ]]; then
    echo "Active feature: $feat"
    mt="${ROOT}/.claude/tasks/${feat}/MASTER_TASKS.md"
    if [[ -f "$mt" ]]; then
      ip="$(grep -n '\[IN_PROGRESS\]' "$mt" || true)"
      if [[ -n "$ip" ]]; then
        echo "In-progress subtask(s) in ${mt}:"
        echo "$ip" | sed 's/^/  /'
      else
        pend="$(grep -nm1 '\[PENDING\]' "$mt" || true)"
        if [[ -n "$pend" ]]; then
          echo "No [IN_PROGRESS]; next [PENDING] in ${mt}:"
          echo "  $pend"
        else
          echo "Feature has no pending subtasks — consider archiving:"
          echo "  ${ROOT}/.claude/hooks/archive-feature.sh ${feat}"
        fi
      fi
    else
      echo "⚠ MASTER_TASKS.md missing for active feature '${feat}'"
    fi
  else
    echo "Active feature: none"
  fi
else
  echo "No MASTER_PLAN.md at ${PLAN}"
fi
[[ -f "$MAP" ]] && echo "CONTEXT_MAP.md: $MAP"
if wk_strict; then
  echo "Strict mode: ON (WORKFLOW_KIT_STRICT=1) — drift will block tool calls."
fi
echo "────────────────────────────────────────────────"
