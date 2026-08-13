# Project Instructions

## Session Memory

- `MEMORY.md` is the master memory for this experiment project. It records
  only current global status, cross-session decisions, active gates, and the
  session-memory index.
- Detailed histories belong in per-session files under
  `memory/sessions/` in the current repository checkout.
- At the start of every new session, read `MEMORY.md` completely before making
  plans, edits, audit claims, or experiment decisions. Then read only the
  relevant session memory file(s) listed there for the task being resumed or
  extended.
- Each new focused task/session should create or update its own session memory
  file under `memory/sessions/` in its current checkout, using
  `memory/templates/session_memory_template.md` as the shape.
- Update the master `MEMORY.md` only with stable cross-session facts, final
  decisions, current blockers, and next orchestration steps. Do not put long
  per-run logs or full metric tables in the master memory.
- Generated manifests, audit reports, matrix status files, and final tables
  remain the local numeric source of truth; memory files should cite their paths
  instead of duplicating large generated tables. This does not mean every
  generated artifact is Git-tracked. Phase 2 baseline result artifacts are
  local-only by default.
- In Codex worktree sessions, code, docs, session memory, and generated outputs
  should be written under the current worktree root. Raw data paths may still
  point to the canonical server dataset roots declared in `datasets/registry.yaml`;
  do not write experiment outputs back into `/root/autodl-tmp` from a worktree.

## Research Objective

The main goal of this experiment project is to systematically study label,
protocol, and population differences across depression-detection datasets, and
to propose a symptom-construct aligned framework. Model predictions should be
grounded in transferable symptom evidence rather than dataset protocol shortcuts
or population-specific spurious correlations.

## Research And Network Access

- It is allowed to browse the internet whenever useful for checking papers,
  code, documentation, datasets, benchmark definitions, dataset licenses,
  official repositories, or related technical details.
- Prefer primary sources for factual claims: official dataset pages, papers,
  code repositories, documentation, and challenge pages.

## Agent Behavior Guardrails

- Do not guess. Do not hide uncertainty, blockers, or tradeoffs. Surface them
  early with concrete evidence and current best options.
- Write the smallest code that directly solves the current verified problem.
  Do not add speculative features, speculative branches, or future-proofing
  that is not required by the active experiment contract.
- Modify only what must change for the task, and clean up issues introduced by
  the current work.
- Define the success condition before claiming completion, then keep iterating
  until verification passes or a real blocker is recorded.
- Trust internal code, framework contracts, and project invariants unless
  current evidence contradicts them.
- Validate at system boundaries: user inputs, files from outside the current
  controlled pipeline, external APIs, network calls, installed tools, datasets,
  and repository publishing boundaries.
- Do not add defensive checks, fallbacks, empty/default handling, or validation
  for states that the local contract makes impossible. Let impossible internal
  states fail loudly.
- Do not swallow errors with broad `catch`/`except`, silent defaults, `nil` or
  empty fallbacks, or vague warning-only behavior. Prefer fast failure with a
  useful error message.
- Do not create helper functions, tool classes, abstractions, or frameworks for
  one-off operations unless they remove real repeated complexity or match an
  established local pattern.

## Dataset Governance

- Use `/root/autodl-tmp/datasets/registry.yaml` as the source of truth for
  dataset paths, roles, label types, protocols, modalities, and status.
- Use generated manifests under `/root/autodl-tmp/datasets/manifests/` as the
  experiment input interface.
- Do not train from ad hoc raw-directory scans unless the registry and manifest
  layer is being intentionally updated.
- Keep all splits subject-level. Do not split segments, modalities, tasks, or
  sessions from the same subject across train/dev/test.
- Raw datasets, large features, archives, audio, video, model weights, and local
  runtime files must stay out of Git.

## Audit And File Hygiene

- Regenerate dataset audit artifacts with:

```bash
python /root/autodl-tmp/scripts/audit_datasets.py
```

- The current audit source of truth is `/root/autodl-tmp/datasets/audit/`.
- Static or stale governance files that duplicate generated audit output should
  be updated or deleted immediately.
- Do not keep obsolete conclusions around as extra Markdown files.
