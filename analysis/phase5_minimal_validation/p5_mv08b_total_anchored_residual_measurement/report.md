# P5_MV08b Total-Anchored Residual Measurement Pilot

Generated: `2026-08-11T12:34:39+00:00`

## Decision

- Pass-rule status: `blocked_prediction_identity_increased_vs_mv08`.
- Full-method allowed: `False`.
- Artifact hygiene passed: `True`.

MV08b tests whether item residuals add construct information after a total-severity anchor. Treat a pass as bounded RQ1 measurement evidence only, not full-method authorization.

## Pooled Protocol Macro Item MAE

| dataset | scale | model | macro item MAE | delta vs B1 total | delta vs B2 fixed |
| --- | --- | --- | ---: | ---: | ---: |
| cmdc | PHQ-9 | B1_total_score_floor | 0.613 | 0.000 | -0.026 |
| cmdc | PHQ-9 | B2_fixed_construct_map | 0.638 | 0.026 | 0.000 |
| cmdc | PHQ-9 | M2b_total_anchored_residual_measurement | 0.620 | 0.007 | -0.018 |
| edaic | PHQ-8 | B1_total_score_floor | 0.696 | 0.000 | -0.007 |
| edaic | PHQ-8 | B2_fixed_construct_map | 0.703 | 0.007 | 0.000 |
| edaic | PHQ-8 | M2b_total_anchored_residual_measurement | 0.693 | -0.003 | -0.010 |
| pdch | HAMD-17 | B1_total_score_floor | 0.740 | 0.000 | -0.027 |
| pdch | HAMD-17 | B2_fixed_construct_map | 0.767 | 0.027 | 0.000 |
| pdch | HAMD-17 | M2b_total_anchored_residual_measurement | 0.736 | -0.004 | -0.031 |

## Identity Probes

| probe | model | mean BA | seeds |
| --- | --- | ---: | ---: |
| feature_identity_bge_edaic_cmdc_pdch | feature_bge | 1.000 | 5 |
| prediction_identity_pooled_eval_dataset | B0_train_mean_items | 1.000 | 5 |
| prediction_identity_pooled_eval_dataset | B1_total_score_floor | 1.000 | 5 |
| prediction_identity_pooled_eval_dataset | B2_fixed_construct_map | 0.983 | 5 |
| prediction_identity_pooled_eval_dataset | M2b_total_anchored_residual_measurement | 0.979 | 5 |

## Split Audit

| protocol | train subjects | eval subjects | overlap |
| --- | ---: | ---: | ---: |
| cmdc_phq_subject_cv | 61.6 | 15.4 | 0 |
| edaic_train_dev | 163.0 | 56.0 | 0 |
| pdch_hamd_subject_cv | 73.6 | 18.4 | 0 |
| pooled_partial_invariance | 298.2 | 89.8 | 0 |

## Interpretation Boundary

- This is a minimal-validation pilot over frozen BGE features and shallow measurement heads.
- A positive result would support only a bounded total-anchored residual RQ1 claim.
- Row predictions, residual predictions, thresholds, and learned-parameter details remain local-only.
