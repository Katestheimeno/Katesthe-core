#!/usr/bin/env bash
# Stop hook: verifies task-checkpoint invariants before Claude stops.
#   - At most one [IN_PROGRESS] subtask across all features.
#   - MASTER_PLAN.md Active matches the feature that actually has in-progress work.
#   - MASTER_PLAN.md Active points at a feature folder that exists.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=_lib.sh
source "${SCRIPT_DIR}/_lib.sh"

ROOT="$(wk_find_root)" || exit 0
TASKS="${ROOT}/.claude/tasks"
[[ -d "$TASKS" ]] || exit 0

ip_total=0
ip_features=()
shopt -s nullglob
for mt in "$TASKS"/*/MASTER_TASKS.md; do
  n="$(grep -c '\[IN_PROGRESS\]' "$mt" || true)"
  if [[ "${n:-0}" -gt 0 ]]; then
    ip_total=$((ip_total + n))
    ip_features+=("$(basename "$(dirname "$mt")"):${n}")
  fi
done
shopt -u nullglob

if [[ "$ip_total" -gt 1 ]]; then
  wk_warn "Multiple [IN_PROGRESS] subtasks (${ip_total} total): ${ip_features[*]}. Collapse to one before continuing."
fi

plan_active="$(wk_active_feature "$ROOT" 2>/dev/null || true)"

actual_feat=""
if [[ ${#ip_features[@]} -gt 0 ]]; then
  actual_feat="${ip_features[0]%%:*}"
fi

if [[ -n "$actual_feat" && "$plan_active" != "$actual_feat" ]]; then
  wk_warn "MASTER_PLAN.md Active='${plan_active:-none}' but [IN_PROGRESS] work lives under '${actual_feat}'. Sync MASTER_PLAN.md."
fi

if [[ -n "$plan_active" && ! -d "${TASKS}/${plan_active}" ]]; then
  wk_warn "MASTER_PLAN.md Active='${plan_active}' but ${TASKS}/${plan_active}/ does not exist."
fi

exit 0
