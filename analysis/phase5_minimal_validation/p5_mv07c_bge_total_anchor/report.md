# P5_MV07c BGE Total Anchor

Generated: `2026-08-09T10:19:22+00:00`

## Scope

This row tests a train-fold-selected total anchor for identity-projected BGE itemwise PHQ C01-C08 heads. Projection depth and blend weight are selected by inner CV on the outer training fold only.

## Verdict

- Pass-rule status: `blocked_not_better_than_raw_total_allocation_bge_total_anchor`.
- E-DAIC delta vs raw total allocation: `-0.018`.
- CMDC delta vs raw total allocation: `0.012`.
- E-DAIC delta vs projected total allocation: `-0.003`.
- CMDC delta vs projected total allocation: `0.002`.
- Binary feature identity BA raw/projected: `1.000` -> `0.738`.
- Prediction identity BA: `0.664`.
- Selected component counts: `1, 10`.
- Selected blend weights: `0.00, 0.20, 0.40, 0.60, 0.90`.
- Artifact hygiene passed: `True`.

MV07c tests whether identity-projected BGE itemwise heads add construct value after a train-fold-selected total anchor. It is a shallow validation row, not the full method.

## Key Macro MAE Comparisons

| dataset | model | macro MAE | delta vs train mean | delta vs raw total alloc | delta vs projected total alloc |
| --- | --- | ---: | ---: | ---: | ---: |
| cmdc | cvselected_projected_total_alloc_ridge | 0.686 | -0.172 | 0.010 | 0.000 |
| cmdc | cvselected_projected_total_anchor_itemwise | 0.688 | -0.170 | 0.012 | 0.002 |
| cmdc | raw_bge_itemwise_ridge | 0.679 | -0.178 | 0.003 | -0.007 |
| cmdc | raw_total_alloc_ridge | 0.676 | -0.181 | 0.000 | -0.010 |
| cmdc | train_mean | 0.857 | 0.000 | 0.181 | 0.172 |
| edaic | cvselected_projected_total_alloc_ridge | 0.692 | -0.040 | -0.015 | 0.000 |
| edaic | cvselected_projected_total_anchor_itemwise | 0.690 | -0.043 | -0.018 | -0.003 |
| edaic | raw_bge_itemwise_ridge | 0.704 | -0.028 | -0.003 | 0.012 |
| edaic | raw_total_alloc_ridge | 0.708 | -0.025 | 0.000 | 0.015 |
| edaic | train_mean | 0.732 | 0.000 | 0.025 | 0.040 |

## Selection Audit

| seed | selected k | selected blend weight | inner-CV Macro MAE |
| ---: | ---: | ---: | ---: |
| 0 | 10 | 0.90 | 0.731 |
| 1 | 10 | 0.40 | 0.732 |
| 2 | 1 | 0.60 | 0.742 |
| 3 | 10 | 0.20 | 0.746 |
| 4 | 10 | 0.00 | 0.742 |

## Identity Probes

| probe | layer | representation | BA mean | seed count |
| --- | --- | --- | ---: | ---: |
| edaic_vs_cmdc_identity_train_fold_to_eval_fold | feature | cvselected_projected_bge_features | 0.738 | 5 |
| edaic_vs_cmdc_identity_train_fold_to_eval_fold | feature | raw_bge_features | 1.000 | 5 |
| edaic_vs_cmdc_identity_train_fold_to_eval_fold | prediction | cvselected_total_anchor_predictions | 0.664 | 5 |
| feature_identity_cv_edaic_cmdc_pdch | feature | cvselected_projected_bge_features | 0.702 | 5 |
| feature_identity_cv_edaic_cmdc_pdch | feature | raw_bge_features | 1.000 | 5 |

## Boundary

- This row is a shallow total-anchor diagnostic, not the full method.
- Row-level predictions are local-only and ignored.
- Projection directions, transformed features, encoder weights, and model checkpoints are not written.
