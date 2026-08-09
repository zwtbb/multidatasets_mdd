# P5_MV05 MPDD Context Calibration

Generated: `2026-08-05T04:43:17+00:00`

## Scope

This row tests MPDD RQ3 context calibration on labeled train subjects only. The baseline is a frozen WavLM-audio plus ResNet-video ordinal severity classifier. The proposed mechanism is a second-stage calibrator whose primary inputs are fold-local AV probabilities/logits; age group and personality bins are allowed only as calibration context. It is not generic AVP concatenation: raw AV features train the baseline only, and raw personality text is never a model input or output.

## Feature And Split Contract

- Labeled MPDD train subjects: `175`.
- Repeated OOF policy: `5 seeds x stratified 5-fold over labeled MPDD train subjects`.
- Subject-overlap violations: `0`.
- MPDD test labels used: `False`.
- AV feature columns: `768` WavLM + `2000` ResNet.
- Context columns: `age_group, extraversion_bin, agreeableness_bin, openness_bin, neuroticism_bin, conscientiousness_bin, financial_stress_bin`.

## Main Metrics

| model | Brier Score | ECE | Macro-F1 | Ordinal MAE | QWK |
| --- | --- | --- | --- | --- | --- |
| av_baseline_logistic | 0.7884 | 0.3421 | 0.3919 | 0.5737 | 0.0996 |
| av_probability_recalibrated | 0.5679 | 0.0579 | 0.2865 | 0.5234 | 0.0290 |
| av_context_calibrated_age_personality_bins | 0.5964 | 0.1180 | 0.3678 | 0.5463 | 0.0981 |
| av_context_calibrated_shuffled_personality_bins | 0.6281 | 0.1491 | 0.3583 | 0.5646 | 0.0548 |
| av_context_calibrated_shuffled_age | 0.6097 | 0.1584 | 0.3739 | 0.5669 | 0.0805 |
| context_only_age_personality_bins | 0.5788 | 0.1003 | 0.3552 | 0.5497 | 0.0546 |

## Context Controls

| summary_type | model | metric | value | delta_vs_av_baseline | delta_vs_av_probability_recalibrated | delta_vs_proposed_context |
| --- | --- | --- | --- | --- | --- | --- |
| overall_metric | av_baseline_logistic | ECE | 0.3421 | 0.0000 | 0.2842 | 0.2240 |
| overall_metric | av_baseline_logistic | Brier Score | 0.7884 | 0.0000 | 0.2204 | 0.1919 |
| overall_metric | av_probability_recalibrated | ECE | 0.0579 | -0.2842 | 0.0000 | -0.0602 |
| overall_metric | av_probability_recalibrated | Brier Score | 0.5679 | -0.2204 | 0.0000 | -0.0285 |
| overall_metric | av_context_calibrated_age_personality_bins | ECE | 0.1180 | -0.2240 | 0.0602 | 0.0000 |
| overall_metric | av_context_calibrated_age_personality_bins | Brier Score | 0.5964 | -0.1919 | 0.0285 | 0.0000 |
| overall_metric | av_context_calibrated_shuffled_personality_bins | ECE | 0.1491 | -0.1929 | 0.0913 | 0.0311 |
| overall_metric | av_context_calibrated_shuffled_personality_bins | Brier Score | 0.6281 | -0.1603 | 0.0602 | 0.0317 |
| overall_metric | av_context_calibrated_shuffled_age | ECE | 0.1584 | -0.1837 | 0.1005 | 0.0404 |
| overall_metric | av_context_calibrated_shuffled_age | Brier Score | 0.6097 | -0.1787 | 0.0417 | 0.0133 |
| overall_metric | context_only_age_personality_bins | ECE | 0.1003 | -0.2418 | 0.0424 | -0.0178 |
| overall_metric | context_only_age_personality_bins | Brier Score | 0.5788 | -0.2095 | 0.0109 | -0.0176 |
| subgroup_ece_gap | av_baseline_logistic | age_group_ECE_gap | 0.0487 | 0.0000 | 0.0439 | -0.0197 |
| subgroup_ece_gap | av_probability_recalibrated | age_group_ECE_gap | 0.0048 | -0.0439 | 0.0000 | -0.0636 |
| subgroup_ece_gap | av_context_calibrated_age_personality_bins | age_group_ECE_gap | 0.0684 | 0.0197 | 0.0636 | 0.0000 |
| subgroup_ece_gap | av_context_calibrated_shuffled_personality_bins | age_group_ECE_gap | 0.0397 | -0.0090 | 0.0349 | -0.0287 |
| subgroup_ece_gap | av_context_calibrated_shuffled_age | age_group_ECE_gap | 0.0513 | 0.0025 | 0.0465 | -0.0172 |
| subgroup_ece_gap | context_only_age_personality_bins | age_group_ECE_gap | 0.0215 | -0.0272 | 0.0167 | -0.0469 |
| subgroup_ece_gap | av_baseline_logistic | personality_neuroticism_bin_ECE_gap | 0.2819 | 0.0000 | 0.1417 | 0.1764 |
| subgroup_ece_gap | av_probability_recalibrated | personality_neuroticism_bin_ECE_gap | 0.1402 | -0.1417 | 0.0000 | 0.0347 |
| subgroup_ece_gap | av_context_calibrated_age_personality_bins | personality_neuroticism_bin_ECE_gap | 0.1055 | -0.1764 | -0.0347 | 0.0000 |
| subgroup_ece_gap | av_context_calibrated_shuffled_personality_bins | personality_neuroticism_bin_ECE_gap | 0.2449 | -0.0370 | 0.1047 | 0.1394 |
| subgroup_ece_gap | av_context_calibrated_shuffled_age | personality_neuroticism_bin_ECE_gap | 0.1008 | -0.1811 | -0.0395 | -0.0047 |
| subgroup_ece_gap | context_only_age_personality_bins | personality_neuroticism_bin_ECE_gap | 0.1225 | -0.1594 | -0.0178 | 0.0170 |
| subgroup_ece_gap | av_baseline_logistic | personality_conscientiousness_bin_ECE_gap | 0.1483 | 0.0000 | 0.0634 | 0.0641 |
| subgroup_ece_gap | av_probability_recalibrated | personality_conscientiousness_bin_ECE_gap | 0.0849 | -0.0634 | 0.0000 | 0.0007 |
| subgroup_ece_gap | av_context_calibrated_age_personality_bins | personality_conscientiousness_bin_ECE_gap | 0.0841 | -0.0641 | -0.0007 | 0.0000 |
| subgroup_ece_gap | av_context_calibrated_shuffled_personality_bins | personality_conscientiousness_bin_ECE_gap | 0.0616 | -0.0867 | -0.0233 | -0.0226 |
| subgroup_ece_gap | av_context_calibrated_shuffled_age | personality_conscientiousness_bin_ECE_gap | 0.1093 | -0.0390 | 0.0244 | 0.0251 |
| subgroup_ece_gap | context_only_age_personality_bins | personality_conscientiousness_bin_ECE_gap | 0.0843 | -0.0640 | -0.0006 | 0.0001 |
| subgroup_ece_gap | av_baseline_logistic | financial_stress_bin_ECE_gap | 0.3310 | 0.0000 | 0.0137 | -0.1339 |
| subgroup_ece_gap | av_probability_recalibrated | financial_stress_bin_ECE_gap | 0.3173 | -0.0137 | 0.0000 | -0.1476 |
| subgroup_ece_gap | av_context_calibrated_age_personality_bins | financial_stress_bin_ECE_gap | 0.4649 | 0.1339 | 0.1476 | 0.0000 |
| subgroup_ece_gap | av_context_calibrated_shuffled_personality_bins | financial_stress_bin_ECE_gap | 0.3484 | 0.0174 | 0.0311 | -0.1166 |
| subgroup_ece_gap | av_context_calibrated_shuffled_age | financial_stress_bin_ECE_gap | 0.5165 | 0.1855 | 0.1991 | 0.0515 |
| subgroup_ece_gap | context_only_age_personality_bins | financial_stress_bin_ECE_gap | 0.3585 | 0.0274 | 0.0411 | -0.1065 |

## Subgroup ECE Gaps

| model | group_type | min_group | max_group | absolute_gap |
| --- | --- | --- | --- | --- |
| av_context_calibrated_age_personality_bins | financial_stress_bin | none | mentioned_unclear | 0.4649 |
| av_baseline_logistic | financial_stress_bin | none | mentioned_unclear | 0.3310 |
| av_probability_recalibrated | financial_stress_bin | unknown | mentioned_unclear | 0.3173 |
| av_baseline_logistic | personality_neuroticism_bin | unknown | high | 0.2819 |
| av_baseline_logistic | personality_conscientiousness_bin | unknown | low | 0.1483 |
| av_baseline_logistic | personality_extraversion_bin | high | low | 0.1479 |
| av_probability_recalibrated | personality_neuroticism_bin | low | high | 0.1402 |
| av_baseline_logistic | personality_openness_bin | mid | high | 0.1075 |
| av_context_calibrated_age_personality_bins | personality_neuroticism_bin | low | high | 0.1055 |
| av_probability_recalibrated | personality_agreeableness_bin | high | low | 0.1022 |
| av_baseline_logistic | personality_agreeableness_bin | unknown | low | 0.1000 |
| av_probability_recalibrated | personality_extraversion_bin | unknown | high | 0.0879 |
| av_probability_recalibrated | personality_conscientiousness_bin | high | unknown | 0.0849 |
| av_context_calibrated_age_personality_bins | personality_conscientiousness_bin | high | low | 0.0841 |
| av_context_calibrated_age_personality_bins | age_group | elder | young | 0.0684 |
| av_probability_recalibrated | personality_openness_bin | low | unknown | 0.0610 |
| av_context_calibrated_age_personality_bins | personality_extraversion_bin | high | unknown | 0.0582 |
| av_context_calibrated_age_personality_bins | personality_agreeableness_bin | unknown | low | 0.0558 |
| av_context_calibrated_age_personality_bins | personality_openness_bin | mid | high | 0.0554 |
| av_baseline_logistic | age_group | elder | young | 0.0487 |
| av_probability_recalibrated | age_group | elder | young | 0.0048 |

## Counterfactual Sensitivity

| counterfactual_type | age_group | metric | mean | std | seed_count | subject_count_mean |
| --- | --- | --- | --- | --- | --- | --- |
| age_group_swap | elder | changed_pred_rate | 0.4644 | 0.0707 | 5 | 87.0000 |
| age_group_swap | elder | mean_abs_delta_expected_severity | 0.3841 | 0.0260 | 5 | 87.0000 |
| age_group_swap | elder | mean_delta_expected_severity | 0.3841 | 0.0260 | 5 | 87.0000 |
| age_group_swap | young | changed_pred_rate | 0.3000 | 0.0491 | 5 | 88.0000 |
| age_group_swap | young | mean_abs_delta_expected_severity | 0.3000 | 0.0073 | 5 | 88.0000 |
| age_group_swap | young | mean_delta_expected_severity | -0.3000 | 0.0073 | 5 | 88.0000 |
| personality_bin_swap | elder | changed_pred_rate | 0.2161 | 0.0211 | 5 | 87.0000 |
| personality_bin_swap | elder | mean_abs_delta_expected_severity | 0.2898 | 0.0184 | 5 | 87.0000 |
| personality_bin_swap | elder | mean_delta_expected_severity | -0.0964 | 0.0217 | 5 | 87.0000 |
| personality_bin_swap | young | changed_pred_rate | 0.5250 | 0.0396 | 5 | 88.0000 |
| personality_bin_swap | young | mean_abs_delta_expected_severity | 0.3690 | 0.0281 | 5 | 88.0000 |
| personality_bin_swap | young | mean_delta_expected_severity | 0.2130 | 0.0562 | 5 | 88.0000 |

## Gait Psychomotor Context

| summary_type | metric | feature | value | subject_count |
| --- | --- | --- | --- | --- |
| gait_prediction_diagnostic | av_baseline_logistic_expected_severity_spearman | channel_05_q25 | 0.3795 | 175 |
| gait_prediction_diagnostic | av_baseline_logistic_expected_severity_spearman | sequence_length | 0.3302 | 175 |
| gait_prediction_diagnostic | av_baseline_logistic_expected_severity_spearman | channel_04_q25 | 0.3300 | 175 |
| gait_prediction_diagnostic | av_baseline_logistic_expected_severity_spearman | channel_09_mean_abs | 0.3054 | 175 |
| gait_prediction_diagnostic | av_baseline_logistic_abs_error_spearman | channel_05_iqr | -0.3052 | 175 |
| gait_prediction_diagnostic | av_baseline_logistic_expected_severity_spearman | channel_09_min | -0.2977 | 175 |
| gait_target_correlation | spearman_with_severity_label | channel_00_mean_abs_diff | -0.2953 | 175 |
| gait_prediction_diagnostic | av_baseline_logistic_expected_severity_spearman | channel_10_min | -0.2940 | 175 |
| gait_prediction_diagnostic | av_baseline_logistic_expected_severity_spearman | channel_09_rms | 0.2897 | 175 |
| gait_prediction_diagnostic | av_baseline_logistic_expected_severity_spearman | channel_05_median | 0.2890 | 175 |
| gait_prediction_diagnostic | av_baseline_logistic_abs_error_spearman | channel_05_mean_abs | -0.2853 | 175 |
| gait_target_correlation | spearman_with_binary_label | channel_00_mean_abs_diff | -0.2817 | 175 |

## Verdict

- Pass-rule status: `blocked_no_context_calibration_gain`.
- Baseline/proposed ECE: `0.3421` -> `0.1180`.
- Baseline/proposed QWK: `0.0996` -> `0.0981`.
- Age ECE gap baseline/proposed: `0.0487` -> `0.0684`.
- Personality ECE gap max baseline/proposed: `0.3310` -> `0.4649`.

The MPDD context-calibration row is runnable, but the proposed AV-probability-plus-context calibrator does not improve age/personality subgroup ECE gaps over the AV baseline strongly enough for a positive RQ3 claim.

## Hygiene

- Artifact hygiene passed: `True`.
- Subject-level prediction and counterfactual prediction rows are local-only ignored CSVs.
- Cached feature matrices are read but not copied into this output directory.
- Source media, source paths, personality descriptions, learned embeddings, model weights, and motion arrays are not written.
