# MPDD Phase 3 Individual-Difference Diagnostics

Generated: `2026-08-04T17:27:36+00:00`

## Executive Summary

- Labeled train subjects: `175`; seeds: `[0, 1, 2, 3, 4]`; split policy: subject-level repeated 5-fold OOF.
- Gender-only and health-only diagnostics are blocked because the current structured manifest fields are empty.
- Stop/Go evidence: `{"age_shortcut_or_moderation": {"demographics_minus_shuffled_age_qwk": -0.013380337121173279, "max_age_ece_gap": 0.13219653848124466, "recommendation": "weak_age_only_signal"}, "gait_psychomotor_context": {"interpretation": "Gait remains a diagnostic context axis, not a fourth fused modality in this session.", "recommendation": "go_context_validation", "top_abs_spearman_with_phq9": 0.2690028964862473}, "gender_health": {"reason": "structured gender and health_condition metadata are empty in the current manifest", "recommendation": "blocked"}, "individual_difference_conditioning": {"avp_minus_av_macro_f1": 0.0013568171693500441, "avp_minus_av_qwk": 0.0012269305579059864, "interpretation": "Use as evidence for or against adding personality/context conditioning after Phase 3.", "recommendation": "stop_or_weak_gain"}, "personality_bin_calibration": {"max_personality_bin_ece_gap": 0.28877840255592024, "recommendation": "go_calibration_audit"}, "personality_shortcut_risk": {"counterfactual_macro_f1": 0.29858413668725914, "personality_minus_shuffled_macro_f1": 0.11618625253188952, "recommendation": "go_shortcut_or_moderator_signal"}}`

## Protocol

- Scope: personality-only, demographics-only, audio-video only, audio-video + personality, shuffled controls, personality age-swap counterfactuals, subgroup performance/calibration, and gait psychomotor context.
- The unlabeled MPDD test split is not used.
- Fold-local feature learning is used for all TF-IDF personality features and shuffled/counterfactual controls.
- Cached Phase 2 WavLM audio and ResNet video subject features are reused when available; no encoder fine-tuning is performed.
- Default CI mode is lightweight: run-level subject bootstrap CIs are computed for Phase 3 diagnostic models; subgroup CIs are computed for age/severity core metrics; personality-bin subgroup rows retain point estimates and cross-seed spread unless rerun with higher/fuller settings.
- Gait statistics are analyzed only as psychomotor context, not concatenated into AVP.
- Output hygiene: raw personality text, raw audio/video/IMU, raw arrays, and manifest source paths are not written.

## Main Model Diagnostics

| run_id | QWK | Ordinal MAE | Macro-F1 | ECE | Brier Score |
| --- | --- | --- | --- | --- | --- |
| mpdd_demographics_age_severity_logistic | 0.0037 | 0.6674 | 0.3547 | 0.0819 | 0.6576 |
| mpdd_demographics_shuffled_age_severity_logistic | 0.0171 | 0.9360 | 0.2989 | 0.0726 | 0.6719 |
| mpdd_personality_severity_tfidf_logistic_phase3 | 0.2302 | 0.5097 | 0.4217 | 0.1217 | 0.5847 |
| mpdd_personality_shuffled_severity_tfidf_logistic | -0.0414 | 0.7623 | 0.3055 | 0.0466 | 0.6507 |
| mpdd_personality_counterfactual_age_swap | -0.0484 | 0.7406 | 0.2986 | 0.1327 | 0.6921 |
| mpdd_av_severity_early_fusion | 0.0996 | 0.5737 | 0.3919 | 0.3421 | 0.7884 |
| mpdd_avp_severity_early_fusion_phase3 | 0.1009 | 0.5726 | 0.3933 | 0.3395 | 0.7881 |
| mpdd_avp_shuffled_personality_early_fusion | 0.1046 | 0.5714 | 0.3933 | 0.3406 | 0.7884 |

## Key Deltas

| comparison | metric | left_run_id | right_run_id | left_mean | right_mean | delta_left_minus_right |
| --- | --- | --- | --- | --- | --- | --- |
| avp_minus_av | Brier Score | mpdd_avp_severity_early_fusion_phase3 | mpdd_av_severity_early_fusion | 0.7881 | 0.7884 | -0.0003 |
| avp_minus_av | ECE | mpdd_avp_severity_early_fusion_phase3 | mpdd_av_severity_early_fusion | 0.3395 | 0.3421 | -0.0026 |
| avp_minus_av | Macro-F1 | mpdd_avp_severity_early_fusion_phase3 | mpdd_av_severity_early_fusion | 0.3933 | 0.3919 | 0.0014 |
| avp_minus_av | Ordinal MAE | mpdd_avp_severity_early_fusion_phase3 | mpdd_av_severity_early_fusion | 0.5726 | 0.5737 | -0.0011 |
| avp_minus_av | QWK | mpdd_avp_severity_early_fusion_phase3 | mpdd_av_severity_early_fusion | 0.1009 | 0.0996 | 0.0012 |
| personality_minus_shuffled_personality | Brier Score | mpdd_personality_severity_tfidf_logistic_phase3 | mpdd_personality_shuffled_severity_tfidf_logistic | 0.5847 | 0.6507 | -0.0660 |
| personality_minus_shuffled_personality | ECE | mpdd_personality_severity_tfidf_logistic_phase3 | mpdd_personality_shuffled_severity_tfidf_logistic | 0.1217 | 0.0466 | 0.0752 |
| personality_minus_shuffled_personality | Macro-F1 | mpdd_personality_severity_tfidf_logistic_phase3 | mpdd_personality_shuffled_severity_tfidf_logistic | 0.4217 | 0.3055 | 0.1162 |
| personality_minus_shuffled_personality | Ordinal MAE | mpdd_personality_severity_tfidf_logistic_phase3 | mpdd_personality_shuffled_severity_tfidf_logistic | 0.5097 | 0.7623 | -0.2526 |
| personality_minus_shuffled_personality | QWK | mpdd_personality_severity_tfidf_logistic_phase3 | mpdd_personality_shuffled_severity_tfidf_logistic | 0.2302 | -0.0414 | 0.2716 |
| avp_minus_avp_shuffled_personality | Brier Score | mpdd_avp_severity_early_fusion_phase3 | mpdd_avp_shuffled_personality_early_fusion | 0.7881 | 0.7884 | -0.0004 |
| avp_minus_avp_shuffled_personality | ECE | mpdd_avp_severity_early_fusion_phase3 | mpdd_avp_shuffled_personality_early_fusion | 0.3395 | 0.3406 | -0.0012 |
| avp_minus_avp_shuffled_personality | Macro-F1 | mpdd_avp_severity_early_fusion_phase3 | mpdd_avp_shuffled_personality_early_fusion | 0.3933 | 0.3933 | 0.0000 |
| avp_minus_avp_shuffled_personality | Ordinal MAE | mpdd_avp_severity_early_fusion_phase3 | mpdd_avp_shuffled_personality_early_fusion | 0.5726 | 0.5714 | 0.0011 |
| avp_minus_avp_shuffled_personality | QWK | mpdd_avp_severity_early_fusion_phase3 | mpdd_avp_shuffled_personality_early_fusion | 0.1009 | 0.1046 | -0.0038 |
| demographics_minus_shuffled_age | Brier Score | mpdd_demographics_age_severity_logistic | mpdd_demographics_shuffled_age_severity_logistic | 0.6576 | 0.6719 | -0.0142 |
| demographics_minus_shuffled_age | ECE | mpdd_demographics_age_severity_logistic | mpdd_demographics_shuffled_age_severity_logistic | 0.0819 | 0.0726 | 0.0093 |
| demographics_minus_shuffled_age | Macro-F1 | mpdd_demographics_age_severity_logistic | mpdd_demographics_shuffled_age_severity_logistic | 0.3547 | 0.2989 | 0.0558 |
| demographics_minus_shuffled_age | Ordinal MAE | mpdd_demographics_age_severity_logistic | mpdd_demographics_shuffled_age_severity_logistic | 0.6674 | 0.9360 | -0.2686 |
| demographics_minus_shuffled_age | QWK | mpdd_demographics_age_severity_logistic | mpdd_demographics_shuffled_age_severity_logistic | 0.0037 | 0.0171 | -0.0134 |
| personality_minus_counterfactual_age_swap | Brier Score | mpdd_personality_severity_tfidf_logistic_phase3 | mpdd_personality_counterfactual_age_swap | 0.5847 | 0.6921 | -0.1073 |
| personality_minus_counterfactual_age_swap | ECE | mpdd_personality_severity_tfidf_logistic_phase3 | mpdd_personality_counterfactual_age_swap | 0.1217 | 0.1327 | -0.0109 |
| personality_minus_counterfactual_age_swap | Macro-F1 | mpdd_personality_severity_tfidf_logistic_phase3 | mpdd_personality_counterfactual_age_swap | 0.4217 | 0.2986 | 0.1231 |
| personality_minus_counterfactual_age_swap | Ordinal MAE | mpdd_personality_severity_tfidf_logistic_phase3 | mpdd_personality_counterfactual_age_swap | 0.5097 | 0.7406 | -0.2309 |
| personality_minus_counterfactual_age_swap | QWK | mpdd_personality_severity_tfidf_logistic_phase3 | mpdd_personality_counterfactual_age_swap | 0.2302 | -0.0484 | 0.2786 |

## Subgroup Gaps

| run_id | group_type | metric | min_group | min_mean | max_group | max_mean | absolute_gap |
| --- | --- | --- | --- | --- | --- | --- | --- |
| mpdd_av_severity_early_fusion | true_severity | Ordinal MAE | 0 | 0.3538 | 2 | 1.4381 | 1.0842 |
| mpdd_avp_severity_early_fusion_phase3 | true_severity | Ordinal MAE | 0 | 0.3538 | 2 | 1.4381 | 1.0842 |
| mpdd_personality_severity_tfidf_logistic_phase3 | true_severity | Ordinal MAE | 0 | 0.3192 | 2 | 1.3905 | 1.0712 |
| mpdd_personality_severity_tfidf_logistic_phase3 | true_severity | Accuracy | 2 | 0.0952 | 0 | 0.7212 | 0.6259 |
| mpdd_av_severity_early_fusion | true_severity | Accuracy | 2 | 0.1333 | 0 | 0.7019 | 0.5686 |
| mpdd_avp_severity_early_fusion_phase3 | true_severity | Accuracy | 2 | 0.1333 | 0 | 0.7019 | 0.5686 |
| mpdd_avp_severity_early_fusion_phase3 | true_severity | ECE | 0 | 0.1868 | 2 | 0.7142 | 0.5275 |
| mpdd_av_severity_early_fusion | true_severity | ECE | 0 | 0.1990 | 2 | 0.7038 | 0.5048 |
| mpdd_personality_severity_tfidf_logistic_phase3 | financial_stress_bin | Ordinal MAE | moderate | 0.3714 | high_or_severe | 0.8000 | 0.4286 |
| mpdd_personality_severity_tfidf_logistic_phase3 | financial_stress_bin | Macro-F1 | mentioned_unclear | 0.2222 | moderate | 0.6396 | 0.4174 |
| mpdd_personality_severity_tfidf_logistic_phase3 | personality_extraversion_bin | Ordinal MAE | high | 0.2462 | low | 0.6560 | 0.4098 |
| mpdd_personality_severity_tfidf_logistic_phase3 | personality_extraversion_bin | Accuracy | low | 0.3960 | high | 0.8000 | 0.4040 |

## Personality Counterfactual Sensitivity

| age_group | metric | mean | std | seed_count | subject_count_mean |
| --- | --- | --- | --- | --- | --- |
| elder | changed_pred_rate | 0.5977 | 0.0634 | 5 | 87.0000 |
| elder | mean_delta_expected_severity | 0.1234 | 0.0122 | 5 | 87.0000 |
| elder | mean_abs_delta_expected_severity | 0.2113 | 0.0072 | 5 | 87.0000 |
| young | changed_pred_rate | 0.6841 | 0.0045 | 5 | 88.0000 |
| young | mean_delta_expected_severity | -0.1117 | 0.0179 | 5 | 88.0000 |
| young | mean_abs_delta_expected_severity | 0.2551 | 0.0109 | 5 | 88.0000 |

## Gait Psychomotor Context

| feature | spearman | ci95_low | ci95_high | subject_count |
| --- | --- | --- | --- | --- |
| channel_00_mean_abs_diff | -0.2690 | -0.3749 | -0.1455 | 175 |
| channel_00_diff_std | -0.2613 | -0.3927 | -0.0895 | 175 |
| channel_00_rms | -0.2472 | -0.3860 | -0.1188 | 175 |
| channel_00_std | -0.2340 | -0.3501 | -0.0951 | 175 |
| channel_04_median | 0.2210 | 0.0873 | 0.4006 | 175 |
| channel_04_q25 | 0.2131 | 0.1283 | 0.3380 | 175 |
| channel_01_std | -0.2083 | -0.3431 | -0.0814 | 175 |
| channel_05_q25 | 0.2080 | 0.0425 | 0.3510 | 175 |

## Plots

- `model_comparison_macro_f1_qwk.png`
- `age_group_ece.png`
- `gait_top_phq9_correlations.png`

## Blockers And Caveats

- Structured gender and health metadata are unavailable, so gender/health subgroup calibration and health-only baselines cannot be interpreted.
- Personality bins are derived from structured numeric/descriptor cues in the personality descriptions; they are diagnostic bins, not official labels.
- Some Phase 2 feature/prediction caches are read from the read-only main checkout because large generated CSVs are not present in this worktree.
- These diagnostics do not justify final architecture choices by themselves; they decide whether individual-difference conditioning deserves Phase 4/5 design work.

## Regeneration

```bash
python scripts/phase3_mpdd_individual_differences.py
```

## Output Files

- `phase3_model_predictions.csv`
- `phase3_all_predictions_for_metrics.csv`
- `phase3_metrics_by_seed.csv`
- `phase3_metric_summary.csv`
- `phase3_metric_deltas.csv`
- `subgroup_metrics_by_seed.csv`
- `subgroup_metric_summary.csv`
- `subgroup_gap_summary.csv`
- `personality_counterfactual_sensitivity.csv`
- `personality_counterfactual_summary.csv`
- `gait_psychomotor_top_correlations.csv`
- `cohort_profile.csv`
- `diagnostic_availability.csv`
- `phase3_run_summary.json`
- `artifact_hygiene_audit.json`
