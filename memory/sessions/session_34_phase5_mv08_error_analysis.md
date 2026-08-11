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

## Key Decisions

- Freeze the current MV08 contract as negative evidence unless a predeclared
  MV08b changes the measurement mechanism.
- A credible MV08b should be total-anchored, model item residual structure only
  after severity is controlled, pool or collapse sparse ordinal thresholds, and
  keep HAMD as a separate clinical measurement stress test unless it beats
  simple floors.
- MV08b success gate, if pursued: beat total-score and fixed-map floors on at
  least two pooled active slices without increasing prediction identity.
- If MV08b is not pursued, the paper should continue as a diagnostic and
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
- MV08b is not automatically justified; it needs a predeclared design contract
  that changes the mechanism rather than retuning a shallow BGE head.
- E-DAIC MV06 agreement remains underpowered if stronger RQ4 claims are needed.
- Public remote history rewrite remains optional and requires explicit user
  approval.

## Next Handoff

Decide whether to write a `P5_MV08b` total-anchored residual measurement design
or freeze MV08 as negative evidence and pivot writing toward a diagnostic,
measurement-audit paper. Keep all row-level predictions, learned thresholds,
latent scores, and private review material local-only.
