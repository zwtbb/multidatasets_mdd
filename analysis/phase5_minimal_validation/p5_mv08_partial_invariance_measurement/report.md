# P5_MV08 Partial-Invariance Measurement Pilot

Generated: `2026-08-11T11:39:55+00:00`

## Decision

- Pass-rule status: `blocked_not_better_than_total_score_floor`.
- Full-method allowed: `False`.
- Artifact hygiene passed: `True`.

MV08 tests whether an explicitly partial measurement-invariance contract improves over total-score and fixed-map floors. Treat a pass as bounded RQ1 measurement evidence only, not full-method authorization.

## Pooled Protocol Macro Item MAE

| dataset | scale | model | macro item MAE | delta vs total | delta vs fixed |
| --- | --- | --- | ---: | ---: | ---: |
| cmdc | PHQ-9 | M0_total_score_floor | 0.613 | 0.000 | -0.026 |
| cmdc | PHQ-9 | M1_fixed_construct_map | 0.638 | 0.026 | 0.000 |
| cmdc | PHQ-9 | M2_partial_invariance_ordinal | 0.738 | 0.125 | 0.100 |
| edaic | PHQ-8 | M0_total_score_floor | 0.696 | 0.000 | -0.007 |
| edaic | PHQ-8 | M1_fixed_construct_map | 0.703 | 0.007 | 0.000 |
| edaic | PHQ-8 | M2_partial_invariance_ordinal | 0.842 | 0.147 | 0.140 |
| pdch | HAMD-17 | M0_total_score_floor | 0.740 | 0.000 | -0.027 |
| pdch | HAMD-17 | M1_fixed_construct_map | 0.767 | 0.027 | 0.000 |
| pdch | HAMD-17 | M2_partial_invariance_ordinal | 0.892 | 0.152 | 0.125 |

## Identity Probes

| probe | model | mean BA | seeds |
| --- | --- | ---: | ---: |
| feature_identity_bge_edaic_cmdc_pdch | feature_bge | 1.000 | 5 |
| prediction_identity_pooled_eval_dataset | M0_total_score_floor | 1.000 | 5 |
| prediction_identity_pooled_eval_dataset | M0_train_mean_items | 1.000 | 5 |
| prediction_identity_pooled_eval_dataset | M1_fixed_construct_map | 0.983 | 5 |
| prediction_identity_pooled_eval_dataset | M2_partial_invariance_ordinal | 0.900 | 5 |

## Split Audit

| protocol | train subjects | eval subjects | overlap |
| --- | ---: | ---: | ---: |
| cmdc_phq_subject_cv | 61.6 | 15.4 | 0 |
| edaic_train_dev | 163.0 | 56.0 | 0 |
| pdch_hamd_subject_cv | 73.6 | 18.4 | 0 |
| pooled_partial_invariance | 298.2 | 89.8 | 0 |

## Interpretation Boundary

- This is a minimal-validation pilot over frozen BGE features and shallow measurement heads.
- A positive result would support only a bounded partial-invariance RQ1 claim.
- Row predictions and any latent or learned-parameter details remain local-only.
