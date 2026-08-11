# P5_MV12 Latent-Target Trade-Off Analysis

Generated: `2026-08-11T15:15:42+00:00`

## Scope

This artifact reads aggregate MV07-MV12 summaries only. It decomposes the MV12 gate result and extends the accuracy-identity trade-off table without reading row-level predictions or learned parameters.

## Decision

- Analysis status: `complete_freeze_current_mv12_latent_target_line`.
- Freeze current latent-target line: `True`.
- Full method allowed: `False`.
- Artifact hygiene passed: `True`.

Aggregate-only MV12 analysis recommends freezing the current latent-target line: latent theta utility and conditional identity improve, but observed-scale safety and external theta transfer remain the decisive blockers.

## Gate Decomposition

| gate | passed | value | interpretation |
| --- | --- | --- | --- |
| G0_measurement_optimization | `True` | True | Label-only target generation is numerically usable. |
| G1_same_dataset_theta_utility | `True` | edaic -0.078; cmdc -0.146 | The latent target is predictable within each PHQ dataset. |
| G2_same_dataset_observed_scale_safety | `False` | edaic 0.004; cmdc 0.067 | This is the primary failure: theta gains do not safely map back to observed PHQ item scales. |
| G3_external_theta_transfer | `False` | False | The latent target has not shown external theta transfer. |
| G4_external_observed_scale_safety | `True` | True | Observed transfer is not the limiting gate, but this does not rescue failed theta transfer. |
| G5_conditional_shared_latent_identity | `True` | 0.602 | The shared-latent prediction layer is less dataset-identifiable after legitimate conditioning. |
| G6_leakage_boundary | `True` | True | The aggregate result is release-compatible. |
| G7_artifact_hygiene | `True` | True | No public artifact hygiene issue was detected. |

## Failure Modes

| mode | status | evidence | interpretation |
| --- | --- | --- | --- |
| latent_target_predictable_same_dataset | `use_as_positive_subfinding` | M12a theta MAE deltas vs train mean are E-DAIC -0.078 and CMDC -0.146. | The PHQ latent target is learnable from audited BGE features within each dataset. |
| theta_to_observed_mapping_loss | `primary_blocker` | M12a observed macro deltas vs direct itemwise Ridge are E-DAIC 0.004 and CMDC 0.067. | A cleaner latent output does not yet preserve dataset-specific item-scale information well enough. |
| external_theta_transfer_gap | `primary_blocker` | cross_cmdc_to_edaic_phq delta_theta_vs_B0 0.037; cross_edaic_to_cmdc_phq delta_theta_vs_B0 0.077 | The current source-only measurement target does not transfer as a theta target across E-DAIC and CMDC. |
| conditional_latent_identity_gain | `use_as_positive_subfinding` | M12a conditional predicted-theta identity BA is 0.602; MV09 conditional feature-identity reference is 0.991. | The shared latent prediction layer is less dataset-identifiable than the upstream feature space. |
| post_mapping_identity_remains_scale_specific | `interpret_with_caution` | M12a post-mapping conditional item identity BA is 0.992. | High identity after mapping to observed items should be described as scale-specific output structure, not as the same hard shared-latent failure. |
| measurement_target_reliability_not_main_blocker | `supporting_context` | Primary-item Cronbach alpha averages train 0.923 and eval 0.925. | Aggregate reliability is high enough that the main blocker is prediction/mapping/transfer, not an obviously unusable PHQ target. |

## Trade-Off Frontier

| source | model | scope | observed macro MAE | prediction identity BA | conditional latent BA | frontier |
| --- | --- | --- | ---: | ---: | ---: | --- |
| P5_MV08 | M0_total_score_floor | cross_scale_pooled_active_slice_mean | 0.683 | 1.000 | NA | `True` |
| P5_MV08 | M1_fixed_construct_map | cross_scale_pooled_active_slice_mean | 0.703 | 0.983 | NA | `False` |
| P5_MV08 | M0_train_mean_items | cross_scale_pooled_active_slice_mean | 0.761 | 1.000 | NA | `False` |
| P5_MV08 | M2_partial_invariance_ordinal | cross_scale_pooled_active_slice_mean | 0.824 | 0.900 | NA | `True` |
| P5_MV08b | B1_total_score_floor | cross_scale_pooled_active_slice_mean | 0.683 | 1.000 | NA | `True` |
| P5_MV08b | M2b_total_anchored_residual_measurement | cross_scale_pooled_active_slice_mean | 0.683 | 0.979 | NA | `True` |
| P5_MV08b | B2_fixed_construct_map | cross_scale_pooled_active_slice_mean | 0.703 | 0.983 | NA | `False` |
| P5_MV08b | B0_train_mean_items | cross_scale_pooled_active_slice_mean | 0.761 | 1.000 | NA | `False` |
| P5_MV07b | bge_logit_projection_k1_itemwise_ridge | pooled_phq_edaic_cmdc_mean | 0.686 | 0.827 | NA | `True` |
| P5_MV07b | bge_logit_projection_k3_itemwise_ridge | pooled_phq_edaic_cmdc_mean | 0.686 | 0.778 | NA | `True` |
| P5_MV07b | bge_logit_projection_k5_itemwise_ridge | pooled_phq_edaic_cmdc_mean | 0.691 | 0.721 | NA | `False` |
| P5_MV07b | bge_logit_projection_k10_itemwise_ridge | pooled_phq_edaic_cmdc_mean | 0.691 | 0.684 | NA | `False` |
| P5_MV07b | bge_itemwise_ridge_raw | pooled_phq_edaic_cmdc_mean | 0.692 | 0.994 | NA | `False` |
| P5_MV07c | cvselected_projected_total_anchor_itemwise | pooled_phq_edaic_cmdc_mean | 0.689 | 0.664 | NA | `True` |
| P5_MV07c | cvselected_projected_total_alloc_ridge | pooled_phq_edaic_cmdc_mean | 0.689 | NA | NA | `False` |
| P5_MV07c | raw_bge_itemwise_ridge | pooled_phq_edaic_cmdc_mean | 0.692 | NA | NA | `False` |
| P5_MV07c | raw_total_alloc_ridge | pooled_phq_edaic_cmdc_mean | 0.692 | NA | NA | `False` |
| P5_MV07c | train_mean | pooled_phq_edaic_cmdc_mean | 0.795 | NA | NA | `False` |
| P5_MV12 | B3_direct_itemwise_ridge | pooled_shared_phq_edaic_cmdc_mean | 0.692 | 0.574 | 0.579 | `True` |
| P5_MV12 | B2_direct_total_allocation_ridge | pooled_shared_phq_edaic_cmdc_mean | 0.692 | NA | NA | `False` |
| P5_MV12 | M12a_BGE_Ridge_X_to_theta | pooled_shared_phq_edaic_cmdc_mean | 0.701 | 0.641 | 0.602 | `False` |
| P5_MV12 | M12b_projected_BGE_X_to_theta | pooled_shared_phq_edaic_cmdc_mean | 0.702 | 0.590 | 0.608 | `False` |
| P5_MV12 | B1_train_mean_observed_total | pooled_shared_phq_edaic_cmdc_mean | 0.795 | NA | NA | `False` |
| P5_MV12 | B0_train_mean_theta | pooled_shared_phq_edaic_cmdc_mean | 0.796 | NA | NA | `False` |

## Recommendations

| rank | decision | action |
| ---: | --- | --- |
| 1 | `recommended` | Freeze MV12 as bounded measurement-shift evidence before manuscript drafting. |
| 2 | `recommended` | Use the extended trade-off table as the paper-facing accuracy-invariance/measurement-shift result. |
| 3 | `required` | Keep full M0/M1/M2/M3 blocked. |
| 4 | `recommended` | Prefer manuscript drafting or E-DAIC MV06 agreement strengthening over another shallow BGE head iteration. |

## Interpretation Boundary

- The MV12 latent layer is a useful diagnostic signal, but the full method remains blocked.
- Do not treat post-mapping item identity as the same hard gate as shared-latent identity because observed outputs are intentionally scale-specific.
- The current model line should be frozen unless a future predeclared change directly targets observed-scale mapping and external theta transfer.
- Pareto frontier rows reported in this aggregate table: `8`.
