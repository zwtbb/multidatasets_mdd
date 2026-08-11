# Session Memory: Phase 5 MV08b Total-Anchored Residual Run

Status: complete
Last updated: 2026-08-11 UTC
Thread/task: main agent MV08b implementation and full-gate refresh

## Scope

This session implements and runs the predeclared `P5_MV08b`
total-anchored residual measurement row. It compares simple floors and a
total-anchored residual item head over the same subject-level E-DAIC, CMDC, and
PDCH slices used by MV08. It does not read raw clinical text/media, fine-tune
encoders, export learned parameters, export latent scores, or authorize full
M0/M1/M2/M3 method construction.

## Current State

- Implemented
  `scripts/phase5_run_mv08b_total_anchored_residual_measurement.py` by reusing
  the audited MV08 data interface, aligned frozen BGE features, item labels,
  subject-level splits, identity probes, and artifact-hygiene checks.
- Generated outputs under
  `analysis/phase5_minimal_validation/p5_mv08b_total_anchored_residual_measurement/`.
- MV08b compares:
  - `B0_train_mean_items`;
  - `B1_total_score_floor`;
  - `B2_fixed_construct_map`;
  - `M2b_total_anchored_residual_measurement`.
- Current result status:
  `blocked_prediction_identity_increased_vs_mv08`.
- Artifact hygiene passed; max train/eval subject overlap is `0`.
- The local row/residual prediction file
  `p5_mv08b_local_row_predictions.csv` is ignored local-only.
- Full-method gate was refreshed and now reads 26 Phase 5 summaries. Current
  gate status remains `blocked_but_publishable_diagnostic_direction`, with
  `full_method_allowed=false`.
- The top-ranked gate action is now
  `NEXT_FREEZE_MV08_SEQUENCE_AND_FRAME_DIAGNOSTIC_PAPER`.
- A diagnostic measurement-audit paper outline was initialized at
  `docs/diagnostic_measurement_audit_paper_outline.md`.

## Key Results

- Predeclared MV08b pass rule:
  - beat total-score and fixed-map floors on at least 2 pooled active slices;
  - keep prediction identity BA no higher than current MV08 M2
    (`0.9002020202020201`).
- M2b beats both total-score and fixed-map floors on `2/3` pooled active
  slices.
- M2b fails the identity gate: prediction identity BA is
  `0.9788888888888889`, above the MV08 M2 gate.
- Feature identity BA remains `1.000`.
- Pooled active slice summary:
  - E-DAIC PHQ-8: M2b macro item MAE `0.693`, better than total-score floor
    by `-0.003` and fixed map by `-0.010`.
  - CMDC PHQ-9: M2b macro item MAE `0.620`, worse than total-score floor by
    `+0.007` but better than fixed map by `-0.018`.
  - PDCH HAMD-17: M2b macro item MAE `0.736`, better than total-score floor by
    `-0.004` and fixed map by `-0.031`.

## Key Decisions

- MV08b is a useful diagnostic result but not positive transferable
  shared-measurement evidence.
- Freeze the current MV08/MV08b frozen-BGE shallow RQ1 modeling sequence as
  negative diagnostic evidence.
- Do not start another small shallow RQ1 head iteration unless a genuinely new
  data, feature, or measurement source is introduced.
- Paper direction should emphasize a bounded diagnostic measurement-audit
  contribution rather than claiming full symptom-aligned method success.
- MV06 first-round aggregate evidence is now usable only as bounded RQ4
  credibility evidence; stronger cross-dataset RQ4 claims need more stable
  E-DAIC agreement.

## Files Owned Or Touched

- `scripts/phase5_run_mv08b_total_anchored_residual_measurement.py`
- `scripts/phase5_full_method_gate_audit.py`
- `analysis/phase5_minimal_validation/p5_mv08b_total_anchored_residual_measurement/`
- `analysis/phase5_minimal_validation/full_method_gate_audit/`
- `docs/diagnostic_measurement_audit_paper_outline.md`
- `docs/experiment_direction.md`
- `docs/master_experiment_plan.md`
- `docs/experiment_issue_log.md`
- `MEMORY.md`
- `memory/sessions/session_22_phase5_full_method_gate_audit.md`
- `memory/sessions/session_35_phase5_mv08b_total_anchored_residual_design.md`
- `memory/sessions/session_36_phase5_mv08b_total_anchored_residual_run.md`
- `memory/sessions/session_master_orchestration.md`

## Generated Artifacts

Regeneration commands:

```bash
python scripts/phase5_run_mv08b_total_anchored_residual_measurement.py --overwrite
python scripts/phase5_full_method_gate_audit.py
```

Versionable MV08b outputs:

- `analysis/phase5_minimal_validation/p5_mv08b_total_anchored_residual_measurement/artifact_hygiene_audit.json`
- `analysis/phase5_minimal_validation/p5_mv08b_total_anchored_residual_measurement/comparison_summary.csv`
- `analysis/phase5_minimal_validation/p5_mv08b_total_anchored_residual_measurement/construct_target_map.csv`
- `analysis/phase5_minimal_validation/p5_mv08b_total_anchored_residual_measurement/identity_probe_by_seed.csv`
- `analysis/phase5_minimal_validation/p5_mv08b_total_anchored_residual_measurement/identity_probe_summary.csv`
- `analysis/phase5_minimal_validation/p5_mv08b_total_anchored_residual_measurement/label_feature_audit.csv`
- `analysis/phase5_minimal_validation/p5_mv08b_total_anchored_residual_measurement/metric_summary.csv`
- `analysis/phase5_minimal_validation/p5_mv08b_total_anchored_residual_measurement/metrics_by_seed.csv`
- `analysis/phase5_minimal_validation/p5_mv08b_total_anchored_residual_measurement/model_split_audit.csv`
- `analysis/phase5_minimal_validation/p5_mv08b_total_anchored_residual_measurement/report.md`
- `analysis/phase5_minimal_validation/p5_mv08b_total_anchored_residual_measurement/residual_model_audit.csv`
- `analysis/phase5_minimal_validation/p5_mv08b_total_anchored_residual_measurement/run_summary.json`
- `analysis/phase5_minimal_validation/p5_mv08b_total_anchored_residual_measurement/threshold_sparsity_summary.csv`

Ignored local-only artifacts:

- `analysis/phase5_minimal_validation/p5_mv08b_total_anchored_residual_measurement/p5_mv08b_local_row_predictions.csv`
- row/residual predictions, learned parameters, learned thresholds, latent
  scores, raw snippets, and source locators.

## Blockers And Risks

- RQ1 transferable shared-symptom representation remains blocked.
- The diagnostic paper must present MV08/MV08b honestly as negative or bounded
  measurement evidence, not as a method pass.
- E-DAIC MV06 agreement is underpowered in the first annotation pass.
- Full method construction remains blocked until the full-method gate changes.

## Next Handoff

Use the diagnostic measurement-audit paper outline as the next writing frame.
If additional experiment work is needed before drafting, prioritize either
E-DAIC MV06 double-annotation strengthening or a genuinely new
feature/measurement source; do not iterate another shallow BGE RQ1 head.
