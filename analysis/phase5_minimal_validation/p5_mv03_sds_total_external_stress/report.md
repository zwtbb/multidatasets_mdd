# P5_MV03 SDS Total External Stress

Generated: `2026-08-05T04:19:50+00:00`

## Scope

This row tests the EATD SDS total/severity-only contract. It uses existing manifest labels and cached frozen audio features, trains shallow SDS total heads on official train subjects, and evaluates validation subjects stratified by positive, neutral, and negative valence. It does not use SDS item labels, fine-tune encoders, scan raw audio, or train a full method.

## Feature And Split Contract

- Train subjects: `83`.
- Validation subjects: `79`.
- Subject-overlap violations: `0`.
- EATD valences: `positive, neutral, negative`.
- WavLM feature columns: `768`.
- eGeMAPS feature columns: `88`.

## SDS Total MAE

| valence | model | MAE | delta vs train_mean | seed count |
| --- | --- | ---: | ---: | ---: |
| all_valences | egemaps_valence_segment_svr | 7.341 | 0.140 | 5 |
| all_valences | train_mean_sds_total | 7.201 | 0.000 | 5 |
| all_valences | wavlm_subject_mean_ridge | 7.637 | 0.436 | 5 |
| all_valences | wavlm_valence_segment_ridge | 8.783 | 1.582 | 5 |
| negative | egemaps_valence_segment_svr | 7.425 | 0.224 | 5 |
| negative | train_mean_sds_total | 7.201 | 0.000 | 5 |
| negative | wavlm_subject_mean_ridge | 7.637 | 0.436 | 5 |
| negative | wavlm_valence_segment_ridge | 9.216 | 2.015 | 5 |
| neutral | egemaps_valence_segment_svr | 7.329 | 0.128 | 5 |
| neutral | train_mean_sds_total | 7.201 | 0.000 | 5 |
| neutral | wavlm_subject_mean_ridge | 7.637 | 0.436 | 5 |
| neutral | wavlm_valence_segment_ridge | 8.445 | 1.245 | 5 |
| positive | egemaps_valence_segment_svr | 7.270 | 0.069 | 5 |
| positive | train_mean_sds_total | 7.201 | 0.000 | 5 |
| positive | wavlm_subject_mean_ridge | 7.637 | 0.436 | 5 |
| positive | wavlm_valence_segment_ridge | 8.686 | 1.485 | 5 |

## Regression Metrics

| valence | model | metric | mean | ci95 low | ci95 high |
| --- | --- | --- | ---: | ---: | ---: |
| all_valences | egemaps_valence_segment_svr | MAE | 7.341 | 6.163 | 8.681 |
| all_valences | train_mean_sds_total | MAE | 7.201 | 6.051 | 8.484 |
| all_valences | wavlm_subject_mean_ridge | MAE | 7.637 | 6.294 | 9.202 |
| all_valences | wavlm_valence_segment_ridge | MAE | 8.783 | 7.225 | 10.598 |
| negative | egemaps_valence_segment_svr | MAE | 7.425 | 6.261 | 8.744 |
| negative | train_mean_sds_total | MAE | 7.201 | 6.051 | 8.484 |
| negative | wavlm_subject_mean_ridge | MAE | 7.637 | 6.294 | 9.202 |
| negative | wavlm_valence_segment_ridge | MAE | 9.216 | 7.546 | 11.133 |
| neutral | egemaps_valence_segment_svr | MAE | 7.329 | 6.134 | 8.690 |
| neutral | train_mean_sds_total | MAE | 7.201 | 6.051 | 8.484 |
| neutral | wavlm_subject_mean_ridge | MAE | 7.637 | 6.294 | 9.202 |
| neutral | wavlm_valence_segment_ridge | MAE | 8.445 | 6.799 | 10.326 |
| positive | egemaps_valence_segment_svr | MAE | 7.270 | 6.093 | 8.598 |
| positive | train_mean_sds_total | MAE | 7.201 | 6.051 | 8.484 |
| positive | wavlm_subject_mean_ridge | MAE | 7.637 | 6.294 | 9.202 |
| positive | wavlm_valence_segment_ridge | MAE | 8.686 | 7.085 | 10.469 |

## Valence Gap

| model | metric | mean | seed count |
| --- | --- | ---: | ---: |
| egemaps_valence_segment_svr | negative_highest_rate | 0.291 | 5 |
| egemaps_valence_segment_svr | negative_minus_nonnegative | -0.155 | 5 |
| egemaps_valence_segment_svr | valence_prediction_std | 0.485 | 5 |
| train_mean_sds_total | negative_highest_rate | 0.000 | 5 |
| train_mean_sds_total | negative_minus_nonnegative | 0.000 | 5 |
| train_mean_sds_total | valence_prediction_std | 0.000 | 5 |
| wavlm_subject_mean_ridge | negative_highest_rate | 0.000 | 5 |
| wavlm_subject_mean_ridge | negative_minus_nonnegative | 0.000 | 5 |
| wavlm_subject_mean_ridge | valence_prediction_std | 0.000 | 5 |
| wavlm_valence_segment_ridge | negative_highest_rate | 0.215 | 5 |
| wavlm_valence_segment_ridge | negative_minus_nonnegative | -1.029 | 5 |
| wavlm_valence_segment_ridge | valence_prediction_std | 2.309 | 5 |

## Healthy Negative Check

| model | metric | mean | seed count |
| --- | --- | ---: | ---: |
| egemaps_valence_segment_svr | healthy_negative_highest_rate | 0.279 | 5 |
| egemaps_valence_segment_svr | healthy_negative_mean_pred | 43.372 | 5 |
| egemaps_valence_segment_svr | healthy_negative_minus_nonnegative | -0.186 | 5 |
| egemaps_valence_segment_svr | healthy_nonnegative_mean_pred | 43.558 | 5 |
| train_mean_sds_total | healthy_negative_highest_rate | 0.000 | 5 |
| train_mean_sds_total | healthy_negative_mean_pred | 46.355 | 5 |
| train_mean_sds_total | healthy_negative_minus_nonnegative | 0.000 | 5 |
| train_mean_sds_total | healthy_nonnegative_mean_pred | 46.355 | 5 |
| wavlm_subject_mean_ridge | healthy_negative_highest_rate | 0.000 | 5 |
| wavlm_subject_mean_ridge | healthy_negative_mean_pred | 42.533 | 5 |
| wavlm_subject_mean_ridge | healthy_negative_minus_nonnegative | 0.000 | 5 |
| wavlm_subject_mean_ridge | healthy_nonnegative_mean_pred | 42.533 | 5 |
| wavlm_valence_segment_ridge | healthy_negative_highest_rate | 0.206 | 5 |
| wavlm_valence_segment_ridge | healthy_negative_mean_pred | 39.552 | 5 |
| wavlm_valence_segment_ridge | healthy_negative_minus_nonnegative | -1.112 | 5 |
| wavlm_valence_segment_ridge | healthy_nonnegative_mean_pred | 40.665 | 5 |

## Verdict

- Pass-rule status: `blocked_no_sds_generalization`.
- Best model: `egemaps_valence_segment_svr`.
- Best all-valence MAE: `7.341`.
- Delta vs train-mean MAE: `0.140`.
- Healthy negative minus nonnegative, best model: `-0.186`.
- Phase 3 healthy negative minus nonnegative reference: `-0.061`.

The EATD SDS total heads are runnable, but none beat the train-mean floor on validation MAE; treat this as weak external stress evidence.

## Hygiene

- Artifact hygiene passed: `True`.
- Row-level predictions are written as a local-only ignored CSV.
- Cached feature matrices are read but not copied into this output directory.
- Raw audio, source paths, model weights, learned embeddings, prompts, and responses are not written.
