# Session Memory: Context Token Management

Status: complete
Last updated: 2026-08-21 UTC
Thread/task: main agent active context compression

## Scope

This session creates a compact active handoff layer for the long-running main
agent thread. It preserves the existing layered memory hierarchy and avoids
moving or deleting prior detailed session memories.

It does not alter experiment results, rerun models, read raw datasets, read raw
clinical text, modify local-only workbooks, or change the Phase 5 claim gate.

## Current State

- The main goal has accumulated very high token usage, so future turns need a
  shorter active context entrypoint.
- `MEMORY.md` remains the master memory and must still be read first at the
  start of future sessions.
- A new short file, `/root/autodl-tmp/memory/ACTIVE_HANDOFF.md`, now records the
  current objective, active gate, next manuscript task, critical recent results,
  versioning state, file-boundary rules, and open issue pointers.
- The active research state remains unchanged:
  `blocked_but_publishable_diagnostic_direction`,
  `full_method_allowed=false`, and next work is citation-key insertion plus
  manuscript editing.

## Key Decisions

- Use `memory/ACTIVE_HANDOFF.md` as the short working-memory entrypoint after
  `MEMORY.md`.
- Keep full details in session memories under `memory/sessions/`; do not
  duplicate long histories or full metric tables in the active handoff.
- Update the active handoff whenever a cross-session decision, active next task,
  versioning boundary, or claim gate changes.
- Do not use token management as a reason to discard unresolved blockers,
  versioning policy, data governance rules, or claim-boundary constraints.

## Files Owned Or Touched

- `/root/autodl-tmp/memory/ACTIVE_HANDOFF.md`
- `/root/autodl-tmp/memory/sessions/session_58_context_token_management.md`
- `/root/autodl-tmp/MEMORY.md`
- `/root/autodl-tmp/README.md`

## Generated Artifacts

No experiment artifacts were generated.

Verification commands:

```bash
git diff --check
git status --short
```

## Blockers And Risks

- The project still has many detailed session memories. Future turns should
  resist reading all of them unless the active task needs them.
- The active handoff can become stale if future experiment gates, paper tasks,
  or versioning decisions change and it is not updated.

## Next Handoff

Use this read order:

1. `/root/autodl-tmp/MEMORY.md`
2. `/root/autodl-tmp/memory/ACTIVE_HANDOFF.md`
3. The specific session memory files named by the active task

For the current paper task, read:

- `/root/autodl-tmp/memory/sessions/session_56_diagnostic_manuscript_draft.md`
- `/root/autodl-tmp/memory/sessions/session_57_diagnostic_bibliography_handoff.md`
