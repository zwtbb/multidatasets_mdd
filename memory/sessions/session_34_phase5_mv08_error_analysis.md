# Session Memory: Phase 5 MV08 Error Analysis

Status: complete
Last updated: 2026-08-11 UTC
Thread/task: main agent MV08 aggregate error analysis and gate refresh

## Scope

This session analyzes why the completed `P5_MV08` partial-invariance ordinal
measurement pilot failed its positive RQ1 gate. It may read ignored local MV08
row predictions, but it exports only aggregate diagnostics and does not train a
new model, start full M0/M1/M2/M3 construction, or write subject-level rows,
latent scores, learned parameters, raw text, or source locators.

## Current State

- Implemented and ran `scripts/phase5_analyze_mv08_error_modes.py`.
- Generated aggregate outputs under
  `analysis/phase5_minimal_validation/p5_mv08_error_analysis/`.
- Current error-analysis status:
  `complete_current_mv08_not_claimable_revision_or_freeze`.
- The analysis confirms current MV08 is not claimable positive RQ1 evidence:
  - pooled M2 is worse than both total-score and fixed-map floors on all 3
    active dataset slices;
  - pooled M2 shows systematic positive bias:
    - CMDC PHQ-9: `+0.422`;
    - E-DAIC PHQ-8: `+0.417`;
    - PDCH HAMD-17: `+0.225`;
  - largest pooled item delta is CMDC PHQ9_8/C08 psychomotor:
    `+0.698` MAE versus total-score floor;
  - HAMD scale/item-specific DIF heads have threshold sparsity:
    `0.318` constant-threshold fraction.
- Artifact hygiene passed; no private identifiers, raw paths, raw text, or
  source locators are exported.
- Updated the full-method gate to include `P5_MV08_error_analysis` as the 24th
  evidence row. Gate status remains
  `blocked_but_publishable_diagnostic_direction`, with
  `full_method_allowed=false`.
- Follow-up design is now recorded in
  `memory/sessions/session_35_phase5_mv08b_total_anchored_residual_design.md`.

## Key Decisions

- Freeze the current MV08 contract as negative evidence unless the predeclared
  MV08b follow-up changes the mechanism and passes.
- The MV08b design is now recorded in session_35: it is total-anchored, models
  item residual structure only after severity is controlled, pools or collapses
  sparse ordinal thresholds, and keeps HAMD as a separate clinical measurement
  stress test.
- MV08b success gate: beat total-score and fixed-map floors on at least two
  pooled active slices without increasing prediction identity.
- If MV08b fails, the paper should continue as a diagnostic and
  measurement-audit contribution rather than a broad shared-measurement method
  claim.

## Files Owned Or Touched

- `scripts/phase5_analyze_mv08_error_modes.py`
- `scripts/phase5_full_method_gate_audit.py`
- `analysis/phase5_minimal_validation/p5_mv08_error_analysis/`
- `analysis/phase5_minimal_validation/full_method_gate_audit/`
- `MEMORY.md`
- `docs/master_experiment_plan.md`
- `docs/experiment_issue_log.md`
- `memory/sessions/session_33_phase5_mv08_partial_invariance_pilot.md`
- `memory/sessions/session_34_phase5_mv08_error_analysis.md`
- `memory/sessions/session_master_orchestration.md`

## Generated Artifacts

Regeneration commands:

```bash
python scripts/phase5_analyze_mv08_error_modes.py --overwrite
python scripts/phase5_full_method_gate_audit.py
```

Versionable outputs:

- `analysis/phase5_minimal_validation/p5_mv08_error_analysis/run_summary.json`
- `analysis/phase5_minimal_validation/p5_mv08_error_analysis/report.md`
- `analysis/phase5_minimal_validation/p5_mv08_error_analysis/slice_error_diagnostics.csv`
- `analysis/phase5_minimal_validation/p5_mv08_error_analysis/item_error_diagnostics.csv`
- `analysis/phase5_minimal_validation/p5_mv08_error_analysis/construct_error_diagnostics.csv`
- `analysis/phase5_minimal_validation/p5_mv08_error_analysis/error_bin_summary.csv`
- `analysis/phase5_minimal_validation/p5_mv08_error_analysis/threshold_sparsity_diagnostics.csv`
- `analysis/phase5_minimal_validation/p5_mv08_error_analysis/revision_queue.csv`
- `analysis/phase5_minimal_validation/p5_mv08_error_analysis/artifact_hygiene_audit.json`
- refreshed `analysis/phase5_minimal_validation/full_method_gate_audit/`

Ignored local-only input:

- `analysis/phase5_minimal_validation/p5_mv08_partial_invariance_measurement/p5_mv08_local_row_predictions.csv`

## Blockers And Risks

- Current MV08 remains a negative result and does not authorize full method
  work.
- The MV08b design contract now exists. Its remaining risk is empirical:
  the actual run may still fail total-score/fixed-map/identity gates.
- E-DAIC MV06 agreement remains underpowered if stronger RQ4 claims are needed.
- Public remote history rewrite remains optional and requires explicit user
  approval.

## Next Handoff

This error-analysis handoff is complete. Continue with session_35: implement
and run the predeclared `P5_MV08b` total-anchored residual measurement row, or
freeze MV08/MV08b as negative evidence if the run fails. Keep all row-level
predictions, learned thresholds, latent scores, and private review material
local-only.
