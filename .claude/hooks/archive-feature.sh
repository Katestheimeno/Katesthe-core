#!/usr/bin/env bash
# Archive a completed feature atomically:
#   - writes a summary to .claude/tasks/completed/<feature>.md
#   - moves .claude/tasks/<feature>/ to .claude/tasks/archive/<feature>/
#   - rewrites MASTER_PLAN.md Active (→ none) and Completed (append entry)
#   - rewrites CONTEXT_MAP.md Active Feature and Completed Features
# Usage: archive-feature.sh [--force] [--dry-run] <feature>
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=_lib.sh
source "${SCRIPT_DIR}/_lib.sh"

FORCE=0
DRY=0
FEATURE=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --force)   FORCE=1; shift ;;
    --dry-run) DRY=1; shift ;;
    -h|--help)
      sed -n '2,9p' "$0"
      exit 0
      ;;
    -*)
      echo "archive-feature: unknown flag: $1" >&2
      exit 1
      ;;
    *)
      if [[ -n "$FEATURE" ]]; then
        echo "archive-feature: only one feature name expected." >&2
        exit 1
      fi
      FEATURE="$1"
      shift
      ;;
  esac
done

if [[ -z "$FEATURE" ]]; then
  echo "archive-feature: missing <feature> argument." >&2
  exit 1
fi

ROOT="$(wk_find_root)" || { echo "archive-feature: could not locate .claude/ (run inside a workflow-kit project)." >&2; exit 1; }
TASKS="${ROOT}/.claude/tasks"
FDIR="${TASKS}/${FEATURE}"
MT="${FDIR}/MASTER_TASKS.md"

if [[ ! -d "$FDIR" ]]; then
  echo "archive-feature: no such feature: ${FDIR}" >&2
  exit 1
fi
if [[ ! -f "$MT" ]]; then
  echo "archive-feature: no MASTER_TASKS.md in ${FDIR}" >&2
  exit 1
fi

TOTAL="$(grep -cE '^- \[(PENDING|IN_PROGRESS|BLOCKED|COMPLETED|SKIPPED|DEFERRED)\]' "$MT" || true)"
DONE="$(grep -cE '^- \[(COMPLETED|SKIPPED)\]' "$MT" || true)"

if [[ "$FORCE" -eq 0 ]]; then
  if [[ "${TOTAL:-0}" -eq 0 ]]; then
    echo "archive-feature: no recognizable subtasks in ${MT}. Use --force to archive anyway." >&2
    exit 1
  fi
  if [[ "${DONE:-0}" -ne "${TOTAL:-0}" ]]; then
    echo "archive-feature: ${DONE}/${TOTAL} subtasks [COMPLETED] or [SKIPPED]. Finish them or pass --force." >&2
    grep -nE '^- \[(PENDING|IN_PROGRESS|BLOCKED|DEFERRED)\]' "$MT" >&2 || true
    exit 1
  fi
fi

TODAY="$(wk_today)"
COMPLETED_DIR="${TASKS}/completed"
ARCHIVE_DIR="${TASKS}/archive"
SUMMARY="${COMPLETED_DIR}/${FEATURE}.md"
ARCHIVED="${ARCHIVE_DIR}/${FEATURE}"

if [[ -e "$SUMMARY" ]]; then
  echo "archive-feature: refusing to overwrite ${SUMMARY}" >&2
  exit 1
fi
if [[ -e "$ARCHIVED" ]]; then
  echo "archive-feature: refusing to overwrite ${ARCHIVED}" >&2
  exit 1
fi

# Build summary body.
PRIORITY="$(grep -m1 '^Priority:' "$MT" | sed 's/^Priority:[[:space:]]*//' || true)"
STATUS_LINE="$(grep -m1 '^Status:' "$MT" | sed 's/^Status:[[:space:]]*//' || true)"

TMP_SUMMARY="$(mktemp)"
{
  echo "# Completed: ${FEATURE}"
  echo "Archived: ${TODAY}"
  [[ -n "$PRIORITY" ]] && echo "Priority: ${PRIORITY}"
  [[ -n "$STATUS_LINE" ]] && echo "Status at archive: ${STATUS_LINE}"
  echo "Subtasks: ${DONE}/${TOTAL}"
  echo ""
  echo "## Subtasks"
  grep -E '^- \[(COMPLETED|SKIPPED|PENDING|IN_PROGRESS|BLOCKED|DEFERRED)\]' "$MT" || true
  echo ""
  echo "## Full record"
  echo "Original folder archived at: \`.claude/tasks/archive/${FEATURE}/\`"
} > "$TMP_SUMMARY"

squeeze_blanks() {
  awk 'BEGIN{blank=0} /^[[:space:]]*$/{if(blank)next; blank=1; print; next} {blank=0; print}'
}

# Removes a single blank line when it sits between two consecutive "- " bullets.
tighten_bullets() {
  awk '
    /^[[:space:]]*$/ { held=1; next }
    {
      if (held) {
        if (prev ~ /^- / && $0 ~ /^- /) { } else { print "" }
        held=0
      }
      print
      prev=$0
    }
    END { if (held) print "" }
  '
}

plan_rewrite() {
  local plan="$1"
  awk -v feat="$FEATURE" -v today="$TODAY" '
    function inject() {
      if (!injected) {
        printf("- %s — %s — see [.claude/tasks/completed/%s.md](completed/%s.md)\n", feat, today, feat, feat)
        print ""
        injected = 1
      }
    }
    BEGIN { section=""; injected=0 }
    /^Last Updated:/ { print "Last Updated: " today; next }
    /^## / {
      if (section == "## Completed" && !injected) inject()
      section = $0
      print
      next
    }
    section == "## Active" && /^→/ {
      rest = $0
      sub(/^→[[:space:]]*/, "", rest)
      sub(/[[:space:]]*$/, "", rest)
      if (rest == feat) { print "→ none"; next }
    }
    section == "## Completed" && /^\(none yet\)[[:space:]]*$/ {
      inject()
      next
    }
    { print }
    END {
      if (section == "## Completed" && !injected) inject()
    }
  ' "$plan" | squeeze_blanks | tighten_bullets
}

map_rewrite() {
  local map="$1"
  awk -v feat="$FEATURE" -v today="$TODAY" '
    function inject() {
      if (!injected) {
        printf("- %s — %s — see [completed/%s.md](tasks/completed/%s.md)\n", feat, today, feat, feat)
        print ""
        injected = 1
      }
    }
    BEGIN { section=""; injected=0 }
    /^Last Updated:/ { print "Last Updated: " today; next }
    /^## / {
      if (section ~ /^## Completed Features/ && !injected) inject()
      section = $0
      print
      next
    }
    section == "## Active Feature" && /^→/ {
      if (index($0, feat) > 0) { print "→ none"; next }
    }
    { print }
    END {
      if (section ~ /^## Completed Features/ && !injected) inject()
    }
  ' "$map" | squeeze_blanks | tighten_bullets
}

announce() {
  if [[ "$DRY" -eq 1 ]]; then
    echo "[dry-run] $*"
  else
    echo "$*"
  fi
}

PLAN="${TASKS}/MASTER_PLAN.md"
MAP="${ROOT}/.claude/CONTEXT_MAP.md"

TMP_PLAN=""
TMP_MAP=""
if [[ -f "$PLAN" ]]; then
  TMP_PLAN="$(mktemp)"
  plan_rewrite "$PLAN" > "$TMP_PLAN"
fi
if [[ -f "$MAP" ]]; then
  TMP_MAP="$(mktemp)"
  map_rewrite "$MAP" > "$TMP_MAP"
fi

announce "mkdir -p ${COMPLETED_DIR} ${ARCHIVE_DIR}"
announce "write   ${SUMMARY}"
announce "move    ${FDIR} -> ${ARCHIVED}"
[[ -n "$TMP_PLAN" ]] && announce "update  ${PLAN}"
[[ -n "$TMP_MAP"  ]] && announce "update  ${MAP}"

if [[ "$DRY" -eq 1 ]]; then
  [[ -n "$TMP_PLAN" ]] && rm -f "$TMP_PLAN"
  [[ -n "$TMP_MAP"  ]] && rm -f "$TMP_MAP"
  rm -f "$TMP_SUMMARY"
  echo "[dry-run] done."
  exit 0
fi

mkdir -p "$COMPLETED_DIR" "$ARCHIVE_DIR"
mv "$TMP_SUMMARY" "$SUMMARY"
mv "$FDIR" "$ARCHIVED"
[[ -n "$TMP_PLAN" ]] && mv "$TMP_PLAN" "$PLAN"
[[ -n "$TMP_MAP"  ]] && mv "$TMP_MAP"  "$MAP"

echo "archive-feature: archived '${FEATURE}'"
echo "  summary: ${SUMMARY}"
echo "  folder:  ${ARCHIVED}"
[[ -f "$PLAN" ]] && echo "  updated: ${PLAN}"
[[ -f "$MAP"  ]] && echo "  updated: ${MAP}"
