# Session Memory: Phase 5 MV08 Partial-Invariance Pilot

Status: active
Last updated: 2026-08-11 UTC
Thread/task: main agent P5_MV08 implementation and gate refresh

## Scope

This session implements and runs the bounded `P5_MV08` partial-invariance
ordinal measurement pilot, refreshes the full-method gate, and records how the
new result changes the experiment plan. It does not start full M0/M1/M2/M3
method construction and does not export row-level predictions, latent scores,
learned parameters, raw text, or source locators to Git.

## Current State

- Implemented `scripts/phase5_run_mv08_partial_invariance_measurement.py`.
- Ran the pilot over aligned frozen BGE subject features and item labels:
  - E-DAIC PHQ-8: 219 joined item-labeled subjects;
  - CMDC PHQ-9: 77 joined item-labeled subjects;
  - PDCH HAMD-17: 92 joined item-labeled subjects after excluding incomplete or
    invalid item payloads for the MV08 contract.
- Compared:
  - `M0_train_mean_items`;
  - `M0_total_score_floor`;
  - `M1_fixed_construct_map`;
  - `M2_partial_invariance_ordinal`.
- Protocols/slices:
  - `edaic_train_dev`;
  - `cmdc_phq_subject_cv`;
  - `pdch_hamd_subject_cv`;
  - `pooled_partial_invariance`.
- Current MV08 verdict:
  `blocked_not_better_than_total_score_floor`.
- Pooled MV08 result:
  - M2 improved over the total-score floor on 0 of 3 active dataset slices;
  - worst pooled M2 delta vs total-score floor: `+0.152` macro item MAE;
  - worst pooled M2 delta vs fixed construct map: `+0.140` macro item MAE;
  - feature identity BA: `1.000`;
  - M2 prediction identity BA: `0.900`;
  - maximum train/eval subject overlap: `0`;
  - artifact hygiene passed.
- Reran `scripts/phase5_full_method_gate_audit.py` after adding `P5_MV08` as a
  full evidence row. The gate remains
  `blocked_but_publishable_diagnostic_direction`, with
  `full_method_allowed=false`.

## Key Decisions

- MV08 is a negative minimal-validation result, not positive RQ1 evidence.
- The partial measurement-invariance framing remains scientifically useful, but
  the current frozen-BGE/lightweight ordinal-head implementation is not enough.
- The next ranked action is MV08 error analysis or a predeclared measurement
  revision. If no credible revision is identified, freeze MV08 as negative
  evidence and continue a diagnostic/measurement-audit paper framing.
- Row-level MV08 predictions are local-only:
  `analysis/phase5_minimal_validation/p5_mv08_partial_invariance_measurement/p5_mv08_local_row_predictions.csv`.

## Files Owned Or Touched

- `scripts/phase5_run_mv08_partial_invariance_measurement.py`
- `scripts/phase5_full_method_gate_audit.py`
- `analysis/phase5_minimal_validation/p5_mv08_partial_invariance_measurement/`
- `analysis/phase5_minimal_validation/full_method_gate_audit/`
- `MEMORY.md`
- `docs/master_experiment_plan.md`
- `docs/experiment_issue_log.md`
- `memory/sessions/session_master_orchestration.md`
- `memory/sessions/session_33_phase5_mv08_partial_invariance_pilot.md`

## Generated Artifacts

Regeneration commands:

```bash
python scripts/phase5_run_mv08_partial_invariance_measurement.py --overwrite
python scripts/phase5_full_method_gate_audit.py
```

Versionable MV08 outputs:

- `analysis/phase5_minimal_validation/p5_mv08_partial_invariance_measurement/run_summary.json`
- `analysis/phase5_minimal_validation/p5_mv08_partial_invariance_measurement/report.md`
- `analysis/phase5_minimal_validation/p5_mv08_partial_invariance_measurement/comparison_summary.csv`
- `analysis/phase5_minimal_validation/p5_mv08_partial_invariance_measurement/metric_summary.csv`
- `analysis/phase5_minimal_validation/p5_mv08_partial_invariance_measurement/metrics_by_seed.csv`
- `analysis/phase5_minimal_validation/p5_mv08_partial_invariance_measurement/identity_probe_summary.csv`
- `analysis/phase5_minimal_validation/p5_mv08_partial_invariance_measurement/identity_probe_by_seed.csv`
- `analysis/phase5_minimal_validation/p5_mv08_partial_invariance_measurement/model_split_audit.csv`
- `analysis/phase5_minimal_validation/p5_mv08_partial_invariance_measurement/label_feature_audit.csv`
- `analysis/phase5_minimal_validation/p5_mv08_partial_invariance_measurement/construct_target_map.csv`
- `analysis/phase5_minimal_validation/p5_mv08_partial_invariance_measurement/dif_sparsity_summary.csv`
- `analysis/phase5_minimal_validation/p5_mv08_partial_invariance_measurement/artifact_hygiene_audit.json`

Ignored local-only artifacts:

- `analysis/phase5_minimal_validation/p5_mv08_partial_invariance_measurement/p5_mv08_local_row_predictions.csv`

## Blockers And Risks

- MV08 underperforms the total-score floor on all pooled active slices, so it
  does not support a transferable shared-measurement claim.
- The ordinal head likely needs error analysis before any revision: possible
  causes include weak latent targets, scale-specific item imbalance, threshold
  fitting instability, or insufficient constraint sharing.
- Public remote history may still contain older row-level dataset tables unless
  the user explicitly approves a history rewrite or repository recreation.

## Next Handoff

Run a focused MV08 error analysis against aggregate outputs and, if needed,
inspect the ignored local row predictions without exporting subject-level data.
Decide whether a stronger psychometric measurement revision is justified or
whether MV08 should be frozen as negative evidence in a diagnostic/audit paper.
