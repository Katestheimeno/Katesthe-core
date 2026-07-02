# Example feature layout

For multi-step work, create a directory under `.claude/tasks/{feature_name}/`:

- `MASTER_TASKS.md` — feature context, priority, and list of subtasks (see [MASTER_TASKS.md](MASTER_TASKS.md) in this folder for a minimal example)
- `001-subtask.md`, `002-subtask.md`, … — one file per subtask; see [001-example-subtask.md](001-example-subtask.md) for a filled template

**Do not** commit this `example-feature/` folder to your feature branch unless you are documenting the pattern; you can delete it after copying the idea.

See `.claude/CLAUDE_ENTRYPOINT.md` for the full protocol.
