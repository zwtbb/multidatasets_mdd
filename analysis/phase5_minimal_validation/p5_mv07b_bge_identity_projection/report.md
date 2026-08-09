# P5_MV07b BGE Identity Projection

Generated: `2026-08-09T10:09:34+00:00`

## Scope

This follow-up tests train-fold E-DAIC/CMDC dataset-label nuisance projection over frozen aligned BGE subject features. Projection directions are learned only from training-fold features and dataset labels, then applied to held-out subjects without evaluation target labels or evaluation dataset labels.

## Verdict

- Pass-rule status: `partial_identity_reduced_not_total_floor_beating_bge_projection`.
- Best control model: `bge_logit_projection_k10_itemwise_ridge`.
- Binary feature identity BA before/best-after: `1.000` -> `0.709`.
- Binary prediction identity BA before/best-after: `0.994` -> `0.684`.
- Three-way feature identity BA before/best-after: `1.000` -> `0.687`.
- Best E-DAIC delta vs total allocation: `-0.019`.
- Best CMDC delta vs total allocation: `0.018`.
- Subject-overlap violations: `0`.
- Artifact hygiene passed: `True`.

MV07b tests an inference-compatible BGE identity projection for the pooled E-DAIC/CMDC PHQ C01-C08 contract. A positive claim requires preserved construct MAE, gains over simple floors, and reduced feature/prediction identity.

## Key Macro MAE Comparisons

| dataset | model | macro MAE | delta vs train mean | delta vs total allocation | delta vs raw BGE |
| --- | --- | ---: | ---: | ---: | ---: |
| cmdc | bge_itemwise_ridge_raw | 0.679 | -0.178 | 0.003 | 0.000 |
| cmdc | bge_logit_projection_k10_itemwise_ridge | 0.694 | -0.164 | 0.018 | 0.015 |
| cmdc | total_alloc_ridge | 0.676 | -0.181 | 0.000 | -0.003 |
| cmdc | train_mean | 0.857 | 0.000 | 0.181 | 0.178 |
| edaic | bge_itemwise_ridge_raw | 0.704 | -0.028 | -0.003 | 0.000 |
| edaic | bge_logit_projection_k10_itemwise_ridge | 0.689 | -0.043 | -0.019 | -0.015 |
| edaic | total_alloc_ridge | 0.708 | -0.025 | 0.000 | 0.003 |
| edaic | train_mean | 0.732 | 0.000 | 0.025 | 0.028 |

## Control Summary

| model | within 5pct | beats mean | beats total alloc | feature BA | prediction BA | three-way BA |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| bge_logit_projection_k1_itemwise_ridge | `True` | `True` | `False` | 0.856 | 0.827 | 0.783 |
| bge_logit_projection_k3_itemwise_ridge | `True` | `True` | `False` | 0.796 | 0.778 | 0.736 |
| bge_logit_projection_k5_itemwise_ridge | `True` | `True` | `False` | 0.813 | 0.721 | 0.723 |
| bge_logit_projection_k10_itemwise_ridge | `True` | `True` | `False` | 0.709 | 0.684 | 0.687 |

## Identity Probes

| probe | layer | representation | BA mean | seed count |
| --- | --- | --- | ---: | ---: |
| edaic_vs_cmdc_identity_train_fold_to_eval_fold | feature | bge_logit_projection_k10_features | 0.709 | 5 |
| edaic_vs_cmdc_identity_train_fold_to_eval_fold | feature | bge_logit_projection_k1_features | 0.856 | 5 |
| edaic_vs_cmdc_identity_train_fold_to_eval_fold | feature | bge_logit_projection_k3_features | 0.796 | 5 |
| edaic_vs_cmdc_identity_train_fold_to_eval_fold | feature | bge_logit_projection_k5_features | 0.813 | 5 |
| edaic_vs_cmdc_identity_train_fold_to_eval_fold | feature | raw_bge_features | 1.000 | 5 |
| edaic_vs_cmdc_identity_train_fold_to_eval_fold | prediction | bge_logit_projection_k10_predictions | 0.684 | 5 |
| edaic_vs_cmdc_identity_train_fold_to_eval_fold | prediction | bge_logit_projection_k1_predictions | 0.827 | 5 |
| edaic_vs_cmdc_identity_train_fold_to_eval_fold | prediction | bge_logit_projection_k3_predictions | 0.778 | 5 |
| edaic_vs_cmdc_identity_train_fold_to_eval_fold | prediction | bge_logit_projection_k5_predictions | 0.721 | 5 |
| edaic_vs_cmdc_identity_train_fold_to_eval_fold | prediction | raw_bge_predictions | 0.994 | 5 |
| feature_identity_cv_edaic_cmdc_pdch | feature | bge_logit_projection_k10_features | 0.687 | 5 |
| feature_identity_cv_edaic_cmdc_pdch | feature | bge_logit_projection_k1_features | 0.783 | 5 |
| feature_identity_cv_edaic_cmdc_pdch | feature | bge_logit_projection_k3_features | 0.736 | 5 |
| feature_identity_cv_edaic_cmdc_pdch | feature | bge_logit_projection_k5_features | 0.723 | 5 |
| feature_identity_cv_edaic_cmdc_pdch | feature | raw_bge_features | 1.000 | 5 |

## Boundary

- This row is a shallow identity-control diagnostic, not full method evidence.
- Row-level predictions are local-only and ignored.
- Projection directions, transformed features, encoder weights, and model checkpoints are not written.
