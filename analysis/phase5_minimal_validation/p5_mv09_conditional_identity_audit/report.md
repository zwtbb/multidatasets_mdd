# P5 MV09 Conditional Dataset-Identity Audit

Generated: `2026-08-11T13:26:48+00:00`

## Scope

MV09 checks whether dataset identifiability remains after conditioning on available severity, aligned item labels, and usable covariates. It is a diagnostic audit of the identity gate, not a deployable method.

## Headline Conditional Identity

| probe | strategy | BA | condition | interpretation |
| --- | --- | ---: | --- | --- |
| cmdc_pdch_same_language_total | normalized_total_residualized_bge | 1.000 | severity_norm | conditional identity diagnostic |
| cmdc_pdch_same_language_total | raw_bge_unconditional | 1.000 | none | screen only |
| cmdc_pdch_same_language_total | severity_common_support_raw_bge | 1.000 | none | conditional identity diagnostic |
| edaic_cmdc_pdch_total_norm | normalized_total_residualized_bge | 1.000 | severity_norm | conditional identity diagnostic |
| edaic_cmdc_pdch_total_norm | raw_bge_unconditional | 1.000 | none | screen only |
| edaic_cmdc_pdch_total_norm | severity_common_support_raw_bge | 1.000 | none | conditional identity diagnostic |
| edaic_cmdc_phq_core | phq_core_items_residualized_bge | 0.991 | C01;C02;C03;C04;C05;C06;C07;C08 | conditional identity diagnostic |
| edaic_cmdc_phq_core | raw_bge_unconditional | 1.000 | none | screen only |
| edaic_cmdc_phq_core | severity_common_support_raw_bge | 1.000 | none | conditional identity diagnostic |
| edaic_cmdc_phq_core | severity_residualized_bge | 1.000 | severity_norm | conditional identity diagnostic |

## Gate Recommendations

| recommendation | status | evidence |
| --- | --- | --- |
| identity_gate_scope | `revise_future_gate` | E-DAIC/CMDC raw BA=1.000; item-conditioned BA=0.991; severity-conditioned BA=1.000. |
| conditional_identity_gate | `conditional_identity_remains_high` | CMDC/PDCH raw BA=1.000 and severity-conditioned BA=1.000; three-way raw BA=1.000 and severity-conditioned BA=1.000. |
| prediction_identity_gate | `demote_post_head_hard_gate` | MV08/MV08b prediction probes operate after scale-specific measurement heads, so their identity BA should not be interpreted the same way as shared-latent identity. |
| mv08b_interpretation | `still_not_positive_rq1` | MV08b should be reframed as a measurement-gate diagnostic result, not as a transferable shared-measurement success. |
| next_experiment | `plan_psychometric_baseline` | PHQ/HAMD psychometric and scale-linking literature supports separating measurement model Y->theta from multimodal prediction X->theta. |

## Accuracy-Invariance Trade-Off

| source | model | mean macro MAE | feature identity BA | prediction identity BA |
| --- | --- | ---: | ---: | ---: |
| P5_MV07 | raw_bge_itemwise_ridge | 0.692 | 1.000 | 0.980 |
| P5_MV07b | bge_itemwise_ridge_raw | 0.692 | 1.000 | 0.994 |
| P5_MV07b | bge_logit_projection_k1_itemwise_ridge | 0.686 | 0.856 | 0.827 |
| P5_MV07b | bge_logit_projection_k3_itemwise_ridge | 0.686 | 0.796 | 0.778 |
| P5_MV07b | bge_logit_projection_k5_itemwise_ridge | 0.691 | 0.813 | 0.721 |
| P5_MV07b | bge_logit_projection_k10_itemwise_ridge | 0.691 | 0.709 | 0.684 |
| P5_MV07c | cvselected_projected_total_alloc_ridge | 0.689 | 0.738 | NA |
| P5_MV07c | cvselected_projected_total_anchor_itemwise | 0.689 | 0.738 | 0.664 |
| P5_MV07c | raw_bge_itemwise_ridge | 0.692 | 1.000 | NA |
| P5_MV07c | raw_total_alloc_ridge | 0.692 | 1.000 | NA |
| P5_MV07c | train_mean | 0.795 | 1.000 | NA |
| P5_MV08 | M0_total_score_floor | 0.683 | 1.000 | 1.000 |
| P5_MV08 | M0_train_mean_items | 0.761 | 1.000 | 1.000 |
| P5_MV08 | M1_fixed_construct_map | 0.703 | 1.000 | 0.983 |
| P5_MV08 | M2_partial_invariance_ordinal | 0.824 | 1.000 | 0.900 |
| P5_MV08b | B0_train_mean_items | 0.761 | 1.000 | 1.000 |
| P5_MV08b | B1_total_score_floor | 0.683 | 1.000 | 1.000 |
| P5_MV08b | B2_fixed_construct_map | 0.703 | 1.000 | 0.983 |
| P5_MV08b | M2b_total_anchored_residual_measurement | 0.683 | 1.000 | 0.979 |

## Release Rule

- Tracked outputs are aggregate only.
- No subject-level predictions, learned parameters, local source locators, media paths, or raw text are exported.
- Future full-method gates should distinguish unconditional feature identity, conditional shared-latent identity, and scale-specific post-head prediction identity.
