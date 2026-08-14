# Session Memory: MV14 DIF Effective-Denominator Correction

Status: complete
Last updated: 2026-08-14 UTC
Thread/task: main agent continuation

## Scope

This session owns the narrow MV14b correction that makes item-DIF effective
draw counts convergence-safe at the per-comparison layer.

It does not change the MV14 bootstrap design, lower bootstrap R, start MV16,
train multimodal models, export row-level PHQ item responses, export fitted
IRT parameters, export theta/factor scores, or authorize full M0/M1/M2/M3
method construction.

## Current State

- `scripts/phase5_run_mv14_measurement_uncertainty_bootstrap.R` now sets item
  DIF `effective` from `comparison_valid == TRUE`, not from a narrower
  "not missing fit" check.
- `item_dif_stability_summary.csv` now records attempted, effective, and
  failed draw counts separately for loading, threshold, and anchor-support
  summaries.
- `scripts/phase5_run_mv14_measurement_uncertainty_bootstrap.py` now reports
  DIF effective counts as `effective/attempted` in the MV14 verdict, gate
  recommendations, and report tables.
- The formal MV14 run was rerun with smoke/core/DIF R=`10/200/100`.
- MV14 status remains
  `complete_mv14_convergence_safe_item_level_measurement_shift`.
- Convergence-safe full-ladder effective R remains `120/200` after `185/200`
  fit-success draws; configural convergence remains `120/200`; stable
  metric/partial/scalar ladder effective R remains `197`.
- DIF tier minimum anchor-support effective R is now `77/100`. Threshold-DIF
  comparisons remain `100/100` effective.
- Top threshold-DIF items remain `C02` and `C06`, with threshold-DIF
  frequencies `0.80` and `0.76`.
- Artifact hygiene passed.

## Key Decisions

- MV14 item-level wording remains supportable, but all future summaries should
  distinguish anchor-support effective R from threshold-DIF comparison
  effective R.
- The stricter denominator does not weaken the primary localized threshold-DIF
  evidence because C02/C06 threshold comparisons remain fully effective.
- Global invariance-model wording remains downgraded: MV14 supports stable
  anchors, sparse loading DIF, localized C02/C06 threshold non-equivalence, and
  uncertain global model selection, not a global partial-invariance win.
- MV16 remains the next active experiment, but it should cite the corrected
  MV14 effective-denominator artifacts.

## Files Owned Or Touched

- `scripts/phase5_run_mv14_measurement_uncertainty_bootstrap.R`
- `scripts/phase5_run_mv14_measurement_uncertainty_bootstrap.py`
- `scripts/phase5_full_method_gate_audit.py`
- `scripts/build_diagnostic_paper_claim_tables.py`
- `analysis/phase5_minimal_validation/p5_mv14_measurement_uncertainty_bootstrap/`
- `analysis/phase5_minimal_validation/p5_mv16_dif_guided_calibration_design/`
- `analysis/phase5_minimal_validation/full_method_gate_audit/`
- `analysis/diagnostic_measurement_audit_paper/`
- `README.md`
- `docs/master_experiment_plan.md`
- `docs/experiment_issue_log.md`
- `docs/diagnostic_measurement_audit_paper_outline.md`
- `MEMORY.md`
- `memory/sessions/session_master_orchestration.md`
- `memory/sessions/session_49_mv14_measurement_uncertainty_bootstrap_run.md`
- `memory/sessions/session_50_mv15_latent_conditioned_identity_design.md`
- `memory/sessions/session_53_mv14_dif_effective_denominator_correction.md`

## Generated Artifacts

Regenerate the corrected MV14 and downstream aggregate artifacts with:

```bash
python scripts/phase5_run_mv14_measurement_uncertainty_bootstrap.py
python scripts/phase5_plan_mv16_dif_guided_calibration.py --overwrite
python scripts/phase5_full_method_gate_audit.py
python scripts/build_diagnostic_paper_claim_tables.py
python scripts/build_diagnostic_paper_results_sections.py
```

Primary checked outputs:

- `analysis/phase5_minimal_validation/p5_mv14_measurement_uncertainty_bootstrap/run_summary.json`
- `analysis/phase5_minimal_validation/p5_mv14_measurement_uncertainty_bootstrap/item_dif_stability_summary.csv`
- `analysis/phase5_minimal_validation/p5_mv14_measurement_uncertainty_bootstrap/report.md`
- `analysis/phase5_minimal_validation/full_method_gate_audit/run_summary.json`
- `analysis/diagnostic_measurement_audit_paper/results_section_run_summary.json`

## Blockers And Risks

- Full method remains blocked.
- CMDC PHQ item-labeled N remains small (`77` subjects), so reviewer-facing
  intervals and global model-selection wording should stay cautious.
- Optional larger MV14 bootstrap tiers may still be useful later for interval
  precision, but only after this corrected effective-denominator logic.

## Next Handoff

Superseded by
`memory/sessions/session_54_mv16_dif_guided_calibration_run.md`: MV16 has now
been implemented and run. Future work should use the refreshed full-method gate
and paper scaffolds, keeping target-shot maps, theta tables, calibration
parameters, fitted measurement parameters, row predictions, feature matrices,
and model artifacts local-only.
