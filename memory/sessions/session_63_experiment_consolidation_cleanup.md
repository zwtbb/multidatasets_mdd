# Session Memory: session_63_experiment_consolidation_cleanup

Status: complete
Last updated: 2026-08-22 UTC
Thread/task: Main-agent experiment consolidation and cleanup

## Scope

This session owns Phase 5 experiment consolidation, conservative cleanup of
redundant local byproducts, and updating docs/memory so future work uses an
active evidence bundle rather than the full historical MV list.

It should not delete raw datasets, local predictions, feature caches, MV06
workbooks, Phase 2 local outputs, or tracked aggregate experiment artifacts
without a separate user-approved storage cleanup decision.

## Current State

Phase 5 accumulated 44 evidence/route rows when the post-review route reached
MV19. The full-method gate remains blocked but publishable as a diagnostic
measurement-validity paper. Many early minimal validations are negative or
superseded and should no longer invite new model iterations.

`scripts/phase5_consolidate_experiment_inventory.py` now generates the active
consolidation layer under:

- `analysis/phase5_minimal_validation/experiment_consolidation/`

Historical generated counts from this session, superseded by session 66:

- 44 evidence/route rows.
- 15 paper-active rows.
- 5 historical paper-core rows, now interpreted as `MV10/MV11/MV19` primary
  PHQ psychometric evidence plus `MV13/MV14` limited `mirt` screens.
- 10 paper-support rows: `MV02/MV04c/MV06/MV09/MV12/MV15/MV16/MV17a/MV18`.
- 28 retired/frozen rows: historical diagnostics, predeclaration contracts, or
  local workflow boundaries.

Current bundle counts are in `MEMORY.md`, `memory/ACTIVE_HANDOFF.md`, and
`analysis/phase5_minimal_validation/experiment_consolidation/run_summary.json`.

## Key Decisions

- Do not physically delete tracked aggregate experiment outputs. They are small
  traceability records used by the full-method gate and manuscript claim
  boundary.
- Retire early weak or superseded MV rows from the active experiment queue:
  `MV01`, `MV02b`, `MV03/MV03b`, `MV04/MV04b`, `MV05`,
  `MV07/MV07b/MV07c`, and `MV08/MV08b`.
- Keep readiness/design outputs as predeclaration contracts, not standalone
  results.
- Keep MV06 local workflow outputs as schema/hygiene boundaries; local
  workbooks and candidate details stay ignored.
- Interpreter bytecode caches and notebook checkpoint directories are safe to
  delete without further user input. They were deleted in this session.
- Local predictions, local features, Phase 2 local outputs, raw datasets, MV06
  workbooks/backups, environment caches, and `untitled.md` require explicit
  storage-cleanup approval before deletion.

## Files Owned Or Touched

- `scripts/phase5_consolidate_experiment_inventory.py`
- `analysis/phase5_minimal_validation/experiment_consolidation/`
- `README.md`
- `docs/experiment_direction.md`
- `docs/master_experiment_plan.md`
- `docs/diagnostic_measurement_audit_paper_outline.md`
- `docs/experiment_issue_log.md`
- `MEMORY.md`
- `memory/ACTIVE_HANDOFF.md`
- `memory/sessions/session_63_experiment_consolidation_cleanup.md`

## Generated Artifacts

Regenerate with:

```bash
python scripts/phase5_full_method_gate_audit.py
python scripts/phase5_consolidate_experiment_inventory.py
```

Tracked outputs:

- `analysis/phase5_minimal_validation/experiment_consolidation/experiment_consolidation_inventory.csv`
- `analysis/phase5_minimal_validation/experiment_consolidation/active_evidence_bundle.csv`
- `analysis/phase5_minimal_validation/experiment_consolidation/retired_or_frozen_experiments.csv`
- `analysis/phase5_minimal_validation/experiment_consolidation/local_cleanup_inventory.csv`
- `analysis/phase5_minimal_validation/experiment_consolidation/report.md`
- `analysis/phase5_minimal_validation/experiment_consolidation/run_summary.json`
- `analysis/phase5_minimal_validation/experiment_consolidation/artifact_hygiene_audit.json`

Local cleanup performed:

- Removed ignored `__pycache__` directories.
- Removed ignored `.ipynb_checkpoints` directories.

## Blockers And Risks

- Aggressive deletion of ignored local predictions/features would save space but
  could make reruns or audits slower. Ask the user before deleting them.
- MV06 still has one incomplete local candidate; keep local workbooks/backups
  until this is resolved or formally bounded.
- `untitled.md` is an ignored local copy of the original experiment plan, not an
  empty scratch file. Do not delete it without confirming that the master plan
  fully absorbs it for the user's purposes.

## Next Handoff

Use `analysis/phase5_minimal_validation/experiment_consolidation/active_evidence_bundle.csv`
as the default Phase 5 evidence entrypoint. Continue manuscript consolidation
with the MV19-downgraded PHQ wording. Consider MV20 only after manuscript
review shows that protocol-label overlap support is still needed.
