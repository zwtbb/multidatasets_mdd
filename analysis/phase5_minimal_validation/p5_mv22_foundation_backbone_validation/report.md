# P5 MV22 Foundation Backbone Measurement-Aware Validation

Generated: `2026-08-24T12:34:57+00:00`

## Scope

MV22 adds a frozen Qwen3 text embedding backbone and reruns the MV07/MV12/MV15 measurement-aware diagnostic chain. It also adds a lightweight feature-adaptation baseline suite over PHQ shared items and records available WavLM audio proxy coverage.

## Qwen Feature Contract

| encoder | model | pooling | max length | dimensions | rows | chunks |
| --- | --- | --- | ---: | ---: | ---: | ---: |
| cmdc | Qwen/Qwen3-Embedding-0.6B | last_token | 2048 | 1024 | 77 | 908 |
| edaic | Qwen/Qwen3-Embedding-0.6B | last_token | 2048 | 1024 | 219 | 269 |
| pdch | Qwen/Qwen3-Embedding-0.6B | last_token | 2048 | 1024 | 99 | 293 |

## Audio Proxy Coverage

| view | dataset | model | status | rows | dimensions |
| --- | --- | --- | --- | ---: | ---: |
| wavlm_base_plus_audio_proxy | cmdc | microsoft/wavlm-base-plus | available_as_audio_foundation_proxy | 77 | 768 |
| wavlm_base_plus_audio_proxy | edaic | microsoft/wavlm-base-plus | available_as_audio_foundation_proxy | 219 | 768 |
| wavlm_base_plus_audio_proxy | pdch | microsoft/wavlm-base-plus | available_as_audio_foundation_proxy | 99 | 768 |
| wavlm_large_audio | edaic_cmdc_pdch | microsoft/wavlm-large | not_executed_in_mv22_first_slice_compute_scope | 0 | 0 |

## Downstream Diagnostic Extract

| encoder | experiment | metric | value | status |
| --- | --- | --- | ---: | --- |
| bge_m3 | mv07 | feature_identity_ba | 1.0000 | blocked_not_better_than_total_allocation_bge_contract |
| bge_m3 | mv07 | prediction_identity_ba | 0.9324 | blocked_not_better_than_total_allocation_bge_contract |
| bge_m3 | mv12 | conditional_identity_ba_m12a | 0.4948 | blocked_theta_gain_not_observed_scale_safe |
| bge_m3 | mv12 | m12a_pooled_theta_mae | 0.6692 | blocked_theta_gain_not_observed_scale_safe |
| bge_m3 | mv15 | psychometric_predicted_theta_output_identity_ba | 0.5844 | blocked_theta_conditioned_feature_identity_high |
| bge_m3 | mv15 | raw_feature_identity_ba | 1.0000 | blocked_theta_conditioned_feature_identity_high |
| bge_m3 | mv15 | theta_conditioned_feature_identity_ba | 1.0000 | blocked_theta_conditioned_feature_identity_high |
| multilingual_e5_base | mv07 | feature_identity_ba | 1.0000 | blocked_not_better_than_total_allocation_bge_contract |
| multilingual_e5_base | mv07 | prediction_identity_ba | 0.9929 | blocked_not_better_than_total_allocation_bge_contract |
| multilingual_e5_base | mv12 | conditional_identity_ba_m12a | 0.4883 | blocked_theta_gain_not_observed_scale_safe |
| multilingual_e5_base | mv12 | m12a_pooled_theta_mae | 0.6704 | blocked_theta_gain_not_observed_scale_safe |
| multilingual_e5_base | mv15 | psychometric_predicted_theta_output_identity_ba | 0.5630 | blocked_theta_conditioned_feature_identity_high |
| multilingual_e5_base | mv15 | raw_feature_identity_ba | 1.0000 | blocked_theta_conditioned_feature_identity_high |
| multilingual_e5_base | mv15 | theta_conditioned_feature_identity_ba | 1.0000 | blocked_theta_conditioned_feature_identity_high |
| qwen3_embedding_0_6b | mv07 | feature_identity_ba | 1.0000 | blocked_not_better_than_total_allocation_bge_contract |
| qwen3_embedding_0_6b | mv07 | prediction_identity_ba | 0.9785 | blocked_not_better_than_total_allocation_bge_contract |
| qwen3_embedding_0_6b | mv12 | conditional_identity_ba_m12a | 0.5539 | blocked_theta_gain_not_observed_scale_safe |
| qwen3_embedding_0_6b | mv12 | m12a_pooled_theta_mae | 0.6867 | blocked_theta_gain_not_observed_scale_safe |
| qwen3_embedding_0_6b | mv15 | psychometric_predicted_theta_output_identity_ba | 0.5428 | blocked_theta_conditioned_feature_identity_high |
| qwen3_embedding_0_6b | mv15 | raw_feature_identity_ba | 1.0000 | blocked_theta_conditioned_feature_identity_high |
| qwen3_embedding_0_6b | mv15 | theta_conditioned_feature_identity_ba | 1.0000 | blocked_theta_conditioned_feature_identity_high |

## Adaptation Baseline Suite

| feature view | transfer | method | macro item MAE | total MAE | domain BA | seeds |
| --- | --- | --- | ---: | ---: | ---: | ---: |
| bge_m3_text | cmdc_to_edaic_phq_shared | coral_itemwise_ridge | 0.8576 | 5.4733 | 0.2317 | 3 |
| bge_m3_text | cmdc_to_edaic_phq_shared | groupdro_severity_proxy | 0.9511 | 5.2743 | 1.0000 | 3 |
| bge_m3_text | cmdc_to_edaic_phq_shared | irm_severity_env_proxy | 1.0118 | 5.5667 | 1.0000 | 3 |
| bge_m3_text | cmdc_to_edaic_phq_shared | dann_itemwise_mlp | 1.0518 | 5.8295 | 0.9985 | 3 |
| bge_m3_text | edaic_to_cmdc_phq_shared | mmd_mean_itemwise_ridge | 0.7120 | 4.6651 | 0.2154 | 3 |
| bge_m3_text | edaic_to_cmdc_phq_shared | coral_itemwise_ridge | 0.7917 | 5.2837 | 0.2157 | 3 |
| bge_m3_text | edaic_to_cmdc_phq_shared | groupdro_severity_proxy | 0.7942 | 4.5313 | 1.0000 | 3 |
| bge_m3_text | edaic_to_cmdc_phq_shared | dann_itemwise_mlp | 0.8165 | 4.6344 | 1.0000 | 3 |
| multilingual_e5_base_text | cmdc_to_edaic_phq_shared | coral_itemwise_ridge | 0.8620 | 5.5633 | 0.2391 | 3 |
| multilingual_e5_base_text | cmdc_to_edaic_phq_shared | groupdro_severity_proxy | 0.9315 | 5.1873 | 1.0000 | 3 |
| multilingual_e5_base_text | cmdc_to_edaic_phq_shared | dann_itemwise_mlp | 0.9889 | 5.6733 | 1.0000 | 3 |
| multilingual_e5_base_text | cmdc_to_edaic_phq_shared | irm_severity_env_proxy | 0.9963 | 5.4730 | 1.0000 | 3 |
| multilingual_e5_base_text | edaic_to_cmdc_phq_shared | mmd_mean_itemwise_ridge | 0.7296 | 4.3025 | 0.2424 | 3 |
| multilingual_e5_base_text | edaic_to_cmdc_phq_shared | coral_itemwise_ridge | 0.8233 | 5.6508 | 0.2252 | 3 |
| multilingual_e5_base_text | edaic_to_cmdc_phq_shared | groupdro_severity_proxy | 0.8927 | 5.0058 | 1.0000 | 3 |
| multilingual_e5_base_text | edaic_to_cmdc_phq_shared | dann_itemwise_mlp | 1.1082 | 6.1497 | 1.0000 | 3 |
| qwen3_embedding_0_6b_plus_wavlm_audio_proxy | cmdc_to_edaic_phq_shared | coral_itemwise_ridge | 0.9336 | 5.9686 | 0.2205 | 3 |
| qwen3_embedding_0_6b_plus_wavlm_audio_proxy | cmdc_to_edaic_phq_shared | groupdro_severity_proxy | 1.0517 | 5.3068 | 0.9992 | 3 |
| qwen3_embedding_0_6b_plus_wavlm_audio_proxy | cmdc_to_edaic_phq_shared | dann_itemwise_mlp | 1.1132 | 5.6866 | 0.9985 | 3 |
| qwen3_embedding_0_6b_plus_wavlm_audio_proxy | cmdc_to_edaic_phq_shared | irm_severity_env_proxy | 1.1172 | 5.6478 | 0.9985 | 3 |
| qwen3_embedding_0_6b_plus_wavlm_audio_proxy | edaic_to_cmdc_phq_shared | coral_itemwise_ridge | 0.9326 | 6.5923 | 0.2026 | 3 |
| qwen3_embedding_0_6b_plus_wavlm_audio_proxy | edaic_to_cmdc_phq_shared | mmd_mean_itemwise_ridge | 0.9910 | 7.0666 | 0.2213 | 3 |
| qwen3_embedding_0_6b_plus_wavlm_audio_proxy | edaic_to_cmdc_phq_shared | groupdro_severity_proxy | 1.2603 | 8.4718 | 0.9972 | 3 |
| qwen3_embedding_0_6b_plus_wavlm_audio_proxy | edaic_to_cmdc_phq_shared | irm_severity_env_proxy | 1.3023 | 8.8231 | 0.9972 | 3 |
| qwen3_embedding_0_6b_text | cmdc_to_edaic_phq_shared | coral_itemwise_ridge | 0.8698 | 5.4554 | 0.2219 | 3 |
| qwen3_embedding_0_6b_text | cmdc_to_edaic_phq_shared | groupdro_severity_proxy | 1.0446 | 5.3839 | 1.0000 | 3 |
| qwen3_embedding_0_6b_text | cmdc_to_edaic_phq_shared | irm_severity_env_proxy | 1.1153 | 5.9786 | 1.0000 | 3 |
| qwen3_embedding_0_6b_text | cmdc_to_edaic_phq_shared | dann_itemwise_mlp | 1.1480 | 6.3444 | 0.9931 | 3 |
| qwen3_embedding_0_6b_text | edaic_to_cmdc_phq_shared | mmd_mean_itemwise_ridge | 0.7946 | 5.3912 | 0.2589 | 3 |
| qwen3_embedding_0_6b_text | edaic_to_cmdc_phq_shared | coral_itemwise_ridge | 0.8178 | 5.4867 | 0.2140 | 3 |
| qwen3_embedding_0_6b_text | edaic_to_cmdc_phq_shared | groupdro_severity_proxy | 0.8582 | 5.2274 | 1.0000 | 3 |
| qwen3_embedding_0_6b_text | edaic_to_cmdc_phq_shared | dann_itemwise_mlp | 1.0017 | 6.2521 | 1.0000 | 3 |

## Measurement-Aware References

| feature view | transfer | method | macro item MAE | total MAE | theta MAE |
| --- | --- | --- | ---: | ---: | ---: |
| bge_m3_text | cmdc_to_edaic_phq_shared | measurement_aware_mv12_reference | 0.7541 | 4.6897 | 0.6704 |
| bge_m3_text | cmdc_to_edaic_phq_shared | mv12_direct_itemwise_reference | 0.8074 | 4.6879 | 0.7333 |
| bge_m3_text | edaic_to_cmdc_phq_shared | measurement_aware_mv12_reference | 0.9306 | 6.6286 | 0.9976 |
| bge_m3_text | edaic_to_cmdc_phq_shared | mv12_direct_itemwise_reference | 0.8762 | 6.1309 | 0.9871 |
| multilingual_e5_base_text | cmdc_to_edaic_phq_shared | measurement_aware_mv12_reference | 0.8616 | 5.3591 | 0.7375 |
| multilingual_e5_base_text | cmdc_to_edaic_phq_shared | mv12_direct_itemwise_reference | 1.1815 | 6.9883 | 1.0838 |
| multilingual_e5_base_text | edaic_to_cmdc_phq_shared | measurement_aware_mv12_reference | 0.9588 | 6.8701 | 1.0334 |
| multilingual_e5_base_text | edaic_to_cmdc_phq_shared | mv12_direct_itemwise_reference | 1.0153 | 7.2688 | 1.0285 |
| qwen3_embedding_0_6b_text | cmdc_to_edaic_phq_shared | measurement_aware_mv12_reference | 0.7333 | 4.5940 | 0.7239 |
| qwen3_embedding_0_6b_text | cmdc_to_edaic_phq_shared | mv12_direct_itemwise_reference | 0.8690 | 4.7069 | 0.7290 |
| qwen3_embedding_0_6b_text | edaic_to_cmdc_phq_shared | measurement_aware_mv12_reference | 0.8551 | 6.1210 | 0.9166 |
| qwen3_embedding_0_6b_text | edaic_to_cmdc_phq_shared | mv12_direct_itemwise_reference | 0.8827 | 6.1510 | 0.9043 |

## Interpretation Boundary

- This is a foundation-backbone stress test, not a depression-detection leaderboard.
- Feature alignment baselines use target features without target labels; MV12 references use their predeclared downstream aggregate contracts.
- WavLM base-plus is included as an audio foundation proxy in the first MV22 slice; WavLM Large is recorded as a separate compute-scope item.
- No feature cache, participant-level score, prediction row, learned parameter, or clinical content is part of the tracked artifact set.

## Decision

- Status: `complete`.
- Artifact hygiene passed: `True`.
- Qwen downstream executed: `True`.
- Adaptation baseline suite executed: `True`.
