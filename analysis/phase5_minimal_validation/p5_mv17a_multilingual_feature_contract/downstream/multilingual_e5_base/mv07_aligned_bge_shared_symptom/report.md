# P5_MV07 Aligned-BGE Shared-Symptom Validation

Generated: `2026-08-21T18:02:46+00:00`

## Scope

This row uses frozen aligned BGE subject features and shallow Ridge heads only. It is a minimal validation row, not the full symptom-aligned method.

## Verdict

- Pass-rule status: `blocked_not_better_than_total_allocation_bge_contract`.
- Pooled E-DAIC delta vs train mean: `-0.052`.
- Pooled CMDC delta vs train mean: `-0.169`.
- Pooled E-DAIC delta vs total allocation: `-0.004`.
- Pooled CMDC delta vs total allocation: `0.001`.
- PDCH HAMD-proxy delta vs train mean: `-0.035`.
- Feature identity BA: `1.000`.
- Prediction identity BA: `0.993`.
- Artifact hygiene passed: `True`.

Aligned BGE MV07 is a shallow validation result. Interpret it through pooled PHQ gains, PDCH HAMD-proxy sanity, and identity probes; readiness alone is not a shared-symptom claim.

## Key Macro MAE Comparisons

| protocol | target | dataset | model | macro MAE | delta vs train mean | delta vs total allocation |
| --- | --- | --- | --- | ---: | ---: | ---: |
| pdch_hamd_internal_cv | hamd_proxy | pdch | bge_itemwise_ridge | 0.637 | -0.035 | -0.012 |
| pdch_hamd_internal_cv | hamd_proxy | pdch | total_alloc_ridge | 0.649 | -0.023 | 0.000 |
| pdch_hamd_internal_cv | hamd_proxy | pdch | train_mean | 0.672 | 0.000 | 0.023 |
| pooled_shared_phq | phq_core | cmdc | bge_itemwise_ridge | 0.688 | -0.169 | 0.001 |
| pooled_shared_phq | phq_core | cmdc | total_alloc_ridge | 0.687 | -0.170 | 0.000 |
| pooled_shared_phq | phq_core | cmdc | train_mean | 0.857 | 0.000 | 0.170 |
| pooled_shared_phq | phq_core | edaic | bge_itemwise_ridge | 0.681 | -0.052 | -0.004 |
| pooled_shared_phq | phq_core | edaic | total_alloc_ridge | 0.685 | -0.047 | 0.000 |
| pooled_shared_phq | phq_core | edaic | train_mean | 0.732 | 0.000 | 0.047 |

## Identity Probes

| probe | metric | mean | std |
| --- | --- | ---: | ---: |
| feature_identity_bge_edaic_cmdc_pdch | Balanced Accuracy | 1.000 | 0.000 |
| prediction_identity_pooled_phq_edaic_cmdc | Balanced Accuracy | 0.993 | 0.004 |

## Interpretation Boundary

- A positive same-dataset or pooled metric is not sufficient if dataset identity remains high.
- PDCH HAMD proxy results are internal sanity evidence only, not cross-dataset HAMD generalization.
- Row-level predictions are local-only and are not part of the tracked artifact set.
