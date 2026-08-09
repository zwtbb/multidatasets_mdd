# P5_MV02 HAMD-17 Auxiliary Bridge

Generated: `2026-08-09T05:38:02+00:00`

## Scope

This row runs the first HAMD-17 auxiliary bridge in PDCH-only mode. It uses manifest HAMD total/item labels and cached frozen BGE, WavLM, and eGeMAPS subject features, trains shallow Ridge heads only, and evaluates PDCH with subject-level 5-fold CV over five seeds. CMDC is reported only as a small 25-subject sanity subset.

## Label And Feature Contract

- PDCH HAMD subjects: `99`.
- CMDC HAMD sanity subjects: `25`.
- PDCH HAMD code-9 subjects: `7`; code `9` is excluded from item-derived total scoring.
- PDCH CV subject-overlap violations: `0`.
- Feature spaces: `text_bge, audio_wavlm, audio_egemaps, early_fusion_all`.

## PDCH CV Summary

| summary target | feature space | model | MAE | seed count | target count |
| --- | --- | --- | ---: | ---: | ---: |
| hamd_total_direct | early_fusion_all | direct_total_ridge | 5.794 | 5 | 1 |
| hamd_total_direct | text_bge | direct_total_ridge | 5.970 | 5 | 1 |
| hamd_total_direct | audio_wavlm | direct_total_ridge | 6.446 | 5 | 1 |
| hamd_total_direct | audio_egemaps | direct_total_ridge | 6.128 | 5 | 1 |
| hamd_total_direct | none | train_mean_total | 6.181 | 5 | 1 |
| hamd_total_from_items | early_fusion_all | itemwise_ridge | 5.693 | 5 | 1 |
| hamd_total_from_items | text_bge | itemwise_ridge | 5.887 | 5 | 1 |
| hamd_total_from_items | audio_wavlm | itemwise_ridge | 6.190 | 5 | 1 |
| hamd_total_from_items | none | train_mean_items | 6.183 | 5 | 1 |
| hamd_total_from_items | audio_egemaps | itemwise_ridge | 6.112 | 5 | 1 |
| macro_hamd_item_mae | early_fusion_all | itemwise_ridge | 0.727 | 5 | 17 |
| macro_hamd_item_mae | text_bge | itemwise_ridge | 0.731 | 5 | 17 |
| macro_hamd_item_mae | audio_egemaps | itemwise_ridge | 0.742 | 5 | 17 |
| macro_hamd_item_mae | none | train_mean_items | 0.747 | 5 | 17 |
| macro_hamd_item_mae | audio_wavlm | itemwise_ridge | 0.750 | 5 | 17 |

## CMDC Sanity Summary

| summary target | feature space | model | MAE | seed count | target count |
| --- | --- | --- | ---: | ---: | ---: |
| hamd_total_direct | none | train_mean_total | 3.595 | 5 | 1 |
| hamd_total_direct | text_bge | direct_total_ridge | 3.856 | 5 | 1 |
| hamd_total_direct | audio_wavlm | direct_total_ridge | 4.848 | 5 | 1 |
| hamd_total_direct | audio_egemaps | direct_total_ridge | 21.754 | 5 | 1 |
| hamd_total_direct | early_fusion_all | direct_total_ridge | 24.206 | 5 | 1 |
| hamd_total_from_items | text_bge | itemwise_ridge | 3.776 | 5 | 1 |
| hamd_total_from_items | none | train_mean_items | 3.597 | 5 | 1 |
| hamd_total_from_items | audio_wavlm | itemwise_ridge | 3.824 | 5 | 1 |
| hamd_total_from_items | early_fusion_all | itemwise_ridge | 12.488 | 5 | 1 |
| hamd_total_from_items | audio_egemaps | itemwise_ridge | 13.502 | 5 | 1 |
| macro_hamd_item_mae | none | train_mean_items | 0.620 | 5 | 17 |
| macro_hamd_item_mae | text_bge | itemwise_ridge | 0.688 | 5 | 17 |
| macro_hamd_item_mae | audio_wavlm | itemwise_ridge | 0.776 | 5 | 17 |
| macro_hamd_item_mae | early_fusion_all | itemwise_ridge | 1.409 | 5 | 17 |
| macro_hamd_item_mae | audio_egemaps | itemwise_ridge | 1.459 | 5 | 17 |

## Deltas

Negative deltas are improvements in MAE. CMDC rows are sanity checks only.

| eval scope | summary target | feature space | model | delta vs train mean | delta vs best direct total |
| --- | --- | --- | --- | ---: | ---: |
| cmdc_sanity | hamd_total_direct | audio_egemaps | direct_total_ridge | 18.159 | 17.898 |
| cmdc_sanity | hamd_total_direct | audio_wavlm | direct_total_ridge | 1.253 | 0.992 |
| cmdc_sanity | hamd_total_direct | early_fusion_all | direct_total_ridge | 20.611 | 20.350 |
| cmdc_sanity | hamd_total_direct | none | train_mean_total | 0.000 | -0.262 |
| cmdc_sanity | hamd_total_direct | text_bge | direct_total_ridge | 0.262 | 0.000 |
| cmdc_sanity | hamd_total_from_items | audio_egemaps | itemwise_ridge | 9.906 | NA |
| cmdc_sanity | hamd_total_from_items | audio_wavlm | itemwise_ridge | 0.228 | NA |
| cmdc_sanity | hamd_total_from_items | early_fusion_all | itemwise_ridge | 8.891 | NA |
| cmdc_sanity | hamd_total_from_items | none | train_mean_items | 0.000 | NA |
| cmdc_sanity | hamd_total_from_items | text_bge | itemwise_ridge | 0.179 | NA |
| cmdc_sanity | macro_hamd_item_mae | audio_egemaps | itemwise_ridge | 0.840 | NA |
| cmdc_sanity | macro_hamd_item_mae | audio_wavlm | itemwise_ridge | 0.156 | NA |
| cmdc_sanity | macro_hamd_item_mae | early_fusion_all | itemwise_ridge | 0.789 | NA |
| cmdc_sanity | macro_hamd_item_mae | none | train_mean_items | 0.000 | NA |
| cmdc_sanity | macro_hamd_item_mae | text_bge | itemwise_ridge | 0.069 | NA |
| pdch_cv | hamd_total_direct | audio_egemaps | direct_total_ridge | -0.053 | 0.334 |
| pdch_cv | hamd_total_direct | audio_wavlm | direct_total_ridge | 0.265 | 0.652 |
| pdch_cv | hamd_total_direct | early_fusion_all | direct_total_ridge | -0.387 | 0.000 |
| pdch_cv | hamd_total_direct | none | train_mean_total | 0.000 | 0.387 |
| pdch_cv | hamd_total_direct | text_bge | direct_total_ridge | -0.211 | 0.176 |
| pdch_cv | hamd_total_from_items | audio_egemaps | itemwise_ridge | -0.071 | NA |
| pdch_cv | hamd_total_from_items | audio_wavlm | itemwise_ridge | 0.008 | NA |
| pdch_cv | hamd_total_from_items | early_fusion_all | itemwise_ridge | -0.489 | NA |
| pdch_cv | hamd_total_from_items | none | train_mean_items | 0.000 | NA |
| pdch_cv | hamd_total_from_items | text_bge | itemwise_ridge | -0.296 | NA |
| pdch_cv | macro_hamd_item_mae | audio_egemaps | itemwise_ridge | -0.006 | NA |
| pdch_cv | macro_hamd_item_mae | audio_wavlm | itemwise_ridge | 0.002 | NA |
| pdch_cv | macro_hamd_item_mae | early_fusion_all | itemwise_ridge | -0.021 | NA |
| pdch_cv | macro_hamd_item_mae | none | train_mean_items | 0.000 | NA |
| pdch_cv | macro_hamd_item_mae | text_bge | itemwise_ridge | -0.016 | NA |

## Verdict

- Pass-rule status: `pass_pdch_only_diagnostic`.
- Best PDCH direct-total MAE: `5.794` from `early_fusion_all`.
- Best PDCH item-derived total MAE: `5.693` from `early_fusion_all`.
- Best PDCH macro item MAE: `0.727` from `early_fusion_all`.

MV02 is a useful PDCH-only diagnostic: shallow frozen-feature heads beat train-mean severity baselines and provide item-level HAMD summaries. This supports running a bounded HAMD auxiliary bridge, but it is not yet a cross-dataset shared-symptom claim because CMDC HAMD coverage is only a 25-subject sanity subset.

## Hygiene

- Artifact hygiene passed: `True`.
- Row-level predictions are written as a local-only ignored CSV.
- Raw clinical text, media paths, learned embeddings, model weights, prompts, and responses are not written.
