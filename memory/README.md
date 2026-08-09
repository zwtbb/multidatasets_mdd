# Memory Layout

This project uses layered memory so future sessions do not need to parse a
single sprawling log.

- `../MEMORY.md` is the master memory. It records current global status,
  decisions, active blockers, and next orchestration steps.
- `sessions/` contains detailed memory for individual Codex tasks.
- `templates/session_memory_template.md` is the starting shape for new session
  memory files.

Rules:

- At the start of every new session, read `../MEMORY.md` completely.
- Then read the relevant file(s) in `sessions/` for the task being resumed or
  extended.
- A new independent task should create or update one session memory file.
- Generated audit outputs, final tables, and metrics remain the local numerical
  source of truth; memory should cite them instead of duplicating long tables.
  Phase 2 baseline result artifacts are local-only by default and are not
  Git-tracked unless we make an explicit exception later.
- Update the master only when a fact is stable and useful across sessions.
- In worktree tasks, write code, docs, session memory, and generated outputs
  under the current worktree root. Use the registry's canonical raw dataset
  paths only for reading data.
