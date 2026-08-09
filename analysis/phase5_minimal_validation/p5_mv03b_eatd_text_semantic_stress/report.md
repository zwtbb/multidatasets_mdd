# P5_MV03b EATD Text Semantic Stress

Generated: `2026-08-09T06:26:58+00:00`

## Scope

This variant tests whether manifest-governed EATD text content can support SDS total validation better than the audio-only MV03 row. It reads text only through the audited manifest, trains shallow character TF-IDF Ridge heads on official train subjects, and evaluates official validation subjects by valence. It does not use SDS item labels, fine-tune encoders, save vectorizers, export raw text, or train a full method.

## Feature And Split Contract

- Train subjects: `83`.
- Validation subjects: `79`.
- Subject-overlap violations: `0`.
- EATD valences: `positive, neutral, negative`.
- Raw text read through manifest: `True`.
- Raw text written: `not_written`.

## SDS Total MAE

| valence | model | MAE | delta vs train_mean | seed count |
| --- | --- | ---: | ---: | ---: |
| all_valences | text_char_tfidf_subject_concat_ridge | 7.200 | -0.001 | 5 |
| all_valences | text_char_tfidf_valence_segment_ridge | 7.200 | -0.001 | 5 |
| all_valences | train_mean_sds_total | 7.201 | 0.000 | 5 |
| negative | text_char_tfidf_subject_concat_ridge | 7.200 | -0.001 | 5 |
| negative | text_char_tfidf_valence_segment_ridge | 7.200 | -0.001 | 5 |
| negative | train_mean_sds_total | 7.201 | 0.000 | 5 |
| neutral | text_char_tfidf_subject_concat_ridge | 7.200 | -0.001 | 5 |
| neutral | text_char_tfidf_valence_segment_ridge | 7.201 | -0.000 | 5 |
| neutral | train_mean_sds_total | 7.201 | 0.000 | 5 |
| positive | text_char_tfidf_subject_concat_ridge | 7.200 | -0.001 | 5 |
| positive | text_char_tfidf_valence_segment_ridge | 7.200 | -0.001 | 5 |
| positive | train_mean_sds_total | 7.201 | 0.000 | 5 |

## Regression Metrics

| valence | model | metric | mean | ci95 low | ci95 high |
| --- | --- | --- | ---: | ---: | ---: |
| all_valences | text_char_tfidf_subject_concat_ridge | MAE | 7.200 | 6.018 | 8.436 |
| all_valences | text_char_tfidf_valence_segment_ridge | MAE | 7.200 | 6.018 | 8.436 |
| all_valences | train_mean_sds_total | MAE | 7.201 | 6.018 | 8.437 |
| negative | text_char_tfidf_subject_concat_ridge | MAE | 7.200 | 6.018 | 8.436 |
| negative | text_char_tfidf_valence_segment_ridge | MAE | 7.200 | 6.018 | 8.436 |
| negative | train_mean_sds_total | MAE | 7.201 | 6.018 | 8.437 |
| neutral | text_char_tfidf_subject_concat_ridge | MAE | 7.200 | 6.018 | 8.436 |
| neutral | text_char_tfidf_valence_segment_ridge | MAE | 7.201 | 6.018 | 8.436 |
| neutral | train_mean_sds_total | MAE | 7.201 | 6.018 | 8.437 |
| positive | text_char_tfidf_subject_concat_ridge | MAE | 7.200 | 6.018 | 8.436 |
| positive | text_char_tfidf_valence_segment_ridge | MAE | 7.200 | 6.018 | 8.436 |
| positive | train_mean_sds_total | MAE | 7.201 | 6.018 | 8.437 |

## Valence Gap

| model | metric | mean | seed count |
| --- | --- | ---: | ---: |
| text_char_tfidf_subject_concat_ridge | negative_highest_rate | 0.000 | 5 |
| text_char_tfidf_subject_concat_ridge | negative_minus_nonnegative | 0.000 | 5 |
| text_char_tfidf_subject_concat_ridge | valence_prediction_std | 0.000 | 5 |
| text_char_tfidf_valence_segment_ridge | negative_highest_rate | 0.215 | 5 |
| text_char_tfidf_valence_segment_ridge | negative_minus_nonnegative | -0.002 | 5 |
| text_char_tfidf_valence_segment_ridge | valence_prediction_std | 0.004 | 5 |
| train_mean_sds_total | negative_highest_rate | 0.000 | 5 |
| train_mean_sds_total | negative_minus_nonnegative | 0.000 | 5 |
| train_mean_sds_total | valence_prediction_std | 0.000 | 5 |

## Healthy Negative Check

| model | metric | mean | seed count |
| --- | --- | ---: | ---: |
| text_char_tfidf_subject_concat_ridge | healthy_negative_highest_rate | 0.000 | 5 |
| text_char_tfidf_subject_concat_ridge | healthy_negative_mean_pred | 46.355 | 5 |
| text_char_tfidf_subject_concat_ridge | healthy_negative_minus_nonnegative | 0.000 | 5 |
| text_char_tfidf_subject_concat_ridge | healthy_nonnegative_mean_pred | 46.355 | 5 |
| text_char_tfidf_valence_segment_ridge | healthy_negative_highest_rate | 0.235 | 5 |
| text_char_tfidf_valence_segment_ridge | healthy_negative_mean_pred | 46.354 | 5 |
| text_char_tfidf_valence_segment_ridge | healthy_negative_minus_nonnegative | -0.002 | 5 |
| text_char_tfidf_valence_segment_ridge | healthy_nonnegative_mean_pred | 46.356 | 5 |
| train_mean_sds_total | healthy_negative_highest_rate | 0.000 | 5 |
| train_mean_sds_total | healthy_negative_mean_pred | 46.355 | 5 |
| train_mean_sds_total | healthy_negative_minus_nonnegative | 0.000 | 5 |
| train_mean_sds_total | healthy_nonnegative_mean_pred | 46.355 | 5 |

## Verdict

- Pass-rule status: `blocked_no_meaningful_text_sds_generalization`.
- Best model: `text_char_tfidf_subject_concat_ridge`.
- Best all-valence MAE: `7.200`.
- Delta vs train-mean MAE: `-0.001`.
- Meaningful-improvement threshold: `MAE <= -0.1` and relative gain `>= 0.01`.
- Meaningful improvement: `False`.
- Healthy negative minus nonnegative, best model: `0.000`.
- Phase 3 healthy negative minus nonnegative reference: `-0.061`.

The EATD text semantic heads are runnable, but the best validation MAE gain over train mean is below the predefined meaningful-improvement threshold; treat this as weak/negative SDS text evidence.

## Hygiene

- Artifact hygiene passed: `True`.
- Row-level predictions are written as a local-only ignored CSV.
- Raw text is read through manifest paths but is not exported.
- Text paths, vectorizers, learned features, model weights, prompts, and responses are not written.
