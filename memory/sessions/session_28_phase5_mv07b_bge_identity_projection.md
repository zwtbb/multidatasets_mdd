# Session Memory: Phase 5 MV07b BGE Identity Projection

Status: complete
Last updated: 2026-08-09 UTC
Thread/task: main agent MV07b BGE identity-control follow-up

## Scope

This session owns the MV07b follow-up to the blocked aligned-BGE MV07 row. It
tests an inference-compatible E-DAIC/CMDC dataset-label nuisance projection over
frozen BGE subject features for the pooled PHQ C01-C08 contract.

It does not scan clinical source content, fine-tune encoders, write transformed
features, save projection directions, save model weights, or start the full
symptom-aligned method.

## Current State

- Implemented `scripts/phase5_run_mv07b_bge_identity_projection.py`.
- Generated
  `analysis/phase5_minimal_validation/p5_mv07b_bge_identity_projection/`.
- Inputs were manifest-governed E-DAIC/CMDC PHQ C01-C08 labels plus frozen BGE
  subject features for E-DAIC, CMDC, and PDCH identity probing.
- Feature contract: 512 shared `bge_*` model-input columns.
- Label/feature coverage:
  - E-DAIC: 219 train/dev PHQ-8 item-labeled subjects.
  - CMDC: 77 PHQ-9 item-labeled subjects.
  - PDCH: 99 feature subjects used for three-way BGE feature-identity probing.
- Subject-overlap violations: `0`.
- Artifact hygiene passed with zero violations.
- Row-level predictions are ignored local-only in
  `p5_mv07b_local_predictions.csv`.
- Full-method gate was rerun and now reads 19 Phase 5 run summaries.

## Key Decisions

- MV07b is complete but only a partial diagnostic result:
  `partial_identity_reduced_not_total_floor_beating_bge_projection`.
- Best control was `bge_logit_projection_k10_itemwise_ridge`.
- Identity reduction is meaningful:
  - E-DAIC/CMDC feature identity BA `1.000 -> 0.709`.
  - E-DAIC/CMDC prediction identity BA `0.994 -> 0.684`.
  - E-DAIC/CMDC/PDCH feature identity BA `1.000 -> 0.687`.
- Main PHQ Macro MAE stayed within 5 percent of raw BGE on both E-DAIC and
  CMDC, and beat train mean on both slices.
- The blocker remains the total-allocation floor:
  - Best E-DAIC delta vs total allocation: `-0.019`.
  - Best CMDC delta vs total allocation: `0.018`.
- Do not claim transferable shared symptom representation from MV07b. It shows
  that identity can be reduced under the BGE contract, but the identity-reduced
  model still does not beat the simple total-allocation floor on CMDC.

## Files Owned Or Touched

- `scripts/phase5_run_mv07b_bge_identity_projection.py`
- `scripts/phase5_full_method_gate_audit.py`
- `analysis/phase5_minimal_validation/p5_mv07b_bge_identity_projection/`
- `analysis/phase5_minimal_validation/full_method_gate_audit/`
- `MEMORY.md`
- `docs/experiment_issue_log.md`
- `memory/sessions/session_28_phase5_mv07b_bge_identity_projection.md`

## Generated Artifacts

Regeneration commands:

```bash
python scripts/phase5_run_mv07b_bge_identity_projection.py
python scripts/phase5_full_method_gate_audit.py
```

Versionable MV07b artifacts:

- `analysis/phase5_minimal_validation/p5_mv07b_bge_identity_projection/report.md`
- `analysis/phase5_minimal_validation/p5_mv07b_bge_identity_projection/run_summary.json`
- `analysis/phase5_minimal_validation/p5_mv07b_bge_identity_projection/artifact_hygiene_audit.json`
- `analysis/phase5_minimal_validation/p5_mv07b_bge_identity_projection/metric_summary.csv`
- `analysis/phase5_minimal_validation/p5_mv07b_bge_identity_projection/metrics_by_seed.csv`
- `analysis/phase5_minimal_validation/p5_mv07b_bge_identity_projection/comparison_summary.csv`
- `analysis/phase5_minimal_validation/p5_mv07b_bge_identity_projection/best_control_summary.csv`
- `analysis/phase5_minimal_validation/p5_mv07b_bge_identity_projection/identity_probe_by_seed.csv`
- `analysis/phase5_minimal_validation/p5_mv07b_bge_identity_projection/identity_probe_summary.csv`
- `analysis/phase5_minimal_validation/p5_mv07b_bge_identity_projection/model_split_audit.csv`
- `analysis/phase5_minimal_validation/p5_mv07b_bge_identity_projection/projection_audit.csv`
- `analysis/phase5_minimal_validation/p5_mv07b_bge_identity_projection/label_feature_audit.csv`
- `analysis/phase5_minimal_validation/p5_mv07b_bge_identity_projection/construct_target_map.csv`
- `analysis/phase5_minimal_validation/p5_mv07b_bge_identity_projection/worst_slice_summary.csv`
- `analysis/phase5_minimal_validation/p5_mv07b_bge_identity_projection/worst_slice_by_seed.csv`

Local-only MV07b artifact:

- `analysis/phase5_minimal_validation/p5_mv07b_bge_identity_projection/p5_mv07b_local_predictions.csv`

## Blockers And Risks

- The identity-controlled BGE variant still fails the CMDC total-allocation
  comparator. This blocks RQ1 shared-symptom representation claims.
- Feature identity is reduced but not eliminated; residual feature identity BA
  remains around `0.709` for E-DAIC/CMDC and `0.687` for E-DAIC/CMDC/PDCH.
- The projection is learned from E-DAIC/CMDC train-fold dataset labels only; it
  is a diagnostic identity-control contract, not yet a clinically deployable
  representation-learning method.

## Next Handoff

Keep the full-method gate blocked. The next useful paths are:

1. Review the ignored MV06 AI preannotation, complete human annotations, and
   rerun the MV06 aggregate summary gate.
2. Resolve the MV07b BGE floor gap with a separately audited identity-controlled
   shared-symptom variant, or demote MV07b to partial diagnostic evidence in the
   paper framing.
