# Subtask: (example) Short description
Status: [PENDING]
Feature: {feature_name}
Created: YYYY-MM-DD
Updated: YYYY-MM-DD

## Breadcrumb
Parent: .claude/tasks/{feature_name}/MASTER_TASKS.md
Previous: (none)
Next: .claude/tasks/{feature_name}/002-next-subtask.md

## Context
One paragraph: what, why, how it fits the feature.

## Scope
Allowed:
- /path/allowed/one
- /path/allowed/two
Forbidden:
- /path/out/of/scope

## Steps
1. First step
2. Second step

## Validation
Command that must exit 0 before marking [COMPLETED], e.g.:
`true`

## Validation Log
- [ ] Run 1: (date / result)

## Drift Log
(If scope creep is detected, note it here and re-align MASTER_TASKS or Scope.)
