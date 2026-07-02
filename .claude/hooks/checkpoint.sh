#!/bin/bash
# Checkpoint protocol reminder — injected before every user prompt.
# Reads MASTER_PLAN.md to surface the active feature name dynamically.

TASKS_DIR="$CLAUDE_PROJECT_DIR/.claude/tasks"
MASTER_PLAN="$TASKS_DIR/MASTER_PLAN.md"

# Extract active feature (line after "## Active")
ACTIVE_FEATURE=""
if [ -f "$MASTER_PLAN" ]; then
  ACTIVE_FEATURE=$(awk '/^## Active/{found=1; next} found && /\S/{print; exit}' "$MASTER_PLAN" | sed 's/^[→\*[:space:]]*//')
fi

if [ -n "$ACTIVE_FEATURE" ] && [ "$ACTIVE_FEATURE" != "(none)" ]; then
  FEATURE_LINE="Active feature: $ACTIVE_FEATURE → read .claude/tasks/$ACTIVE_FEATURE/MASTER_TASKS.md, find [IN_PROGRESS] subtask (or mark first [PENDING] as [IN_PROGRESS])."
else
  FEATURE_LINE="No active feature. If user requests a new feature, create a plan in .claude/tasks/{feature}/."
fi

cat <<EOF
{
  "continue": true,
  "additionalContext": "CHECKPOINT PROTOCOL (mandatory before acting):\n1. Read .claude/CONTEXT_MAP.md — full project state.\n2. Read .claude/tasks/MASTER_PLAN.md — active feature and queue.\n3. $FEATURE_LINE\n4. Update subtask Status: [IN_PROGRESS] when starting, [COMPLETED] when done (validation must pass first).\n5. When a feature completes: update MASTER_TASKS.md status, create .claude/tasks/completed/{feature}.md summary, move feature folder to .claude/tasks/archive/, update MASTER_PLAN.md (Active → none, add to Completed), update .claude/CONTEXT_MAP.md."
}
EOF
