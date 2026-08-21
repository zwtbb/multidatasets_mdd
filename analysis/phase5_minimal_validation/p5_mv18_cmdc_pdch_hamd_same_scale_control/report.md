# P5_MV18 CMDC-PDCH HAMD Same-Scale Control

Generated: `2026-08-21T18:39:32+00:00`

## Scope

MV18 is an exploratory same-language/same-HAMD control. It compares CMDC and PDCH HAMD-17 label behavior and shallow frozen-feature transfer while keeping source text content, media paths, feature arrays, and row-level predictions out of tracked artifacts.

## Label Coverage

| label scope | dataset | subjects | total mean | total sd | severity bins | code-9 subjects |
| --- | --- | ---: | ---: | ---: | --- | ---: |
| all_subjects | cmdc | 25 | 15.760 | 4.275 | {"mild": 16, "moderate": 9} | 0 |
| all_subjects | pdch | 99 | 15.869 | 7.601 | {"mild": 48, "moderate": 25, "normal": 14, "severe": 12} | 7 |
| overlap_mild_moderate | cmdc | 25 | 15.760 | 4.275 | {"mild": 16, "moderate": 9} | 0 |
| overlap_mild_moderate | pdch | 73 | 15.959 | 4.843 | {"mild": 48, "moderate": 25} | 3 |

## Severity-Conditioned Item Shifts

Positive values mean CMDC is higher than PDCH. The residualized comparison uses linear total-excluding-item conditioning.

| item | residual diff | CI low | CI high | flagged | raw diff |
| --- | ---: | ---: | ---: | --- | ---: |
| HAMD08 | 0.574 | 0.356 | 0.804 | True | 0.562 |
| HAMD11 | -0.480 | -0.861 | -0.106 | True | -0.460 |
| HAMD04 | 0.468 | 0.108 | 0.804 | True | 0.453 |
| HAMD09 | -0.348 | -0.549 | -0.095 | True | -0.348 |
| HAMD03 | 0.349 | -0.117 | 0.791 | False | 0.324 |
| HAMD07 | -0.317 | -0.681 | 0.053 | False | -0.305 |
| HAMD16 | -0.279 | -0.522 | 0.006 | False | -0.278 |
| HAMD15 | -0.257 | -0.572 | 0.108 | False | -0.258 |

## Threshold Shifts

| item | threshold | rate diff | CI low | CI high | flagged | CMDC rate | PDCH rate |
| --- | ---: | ---: | ---: | ---: | --- | ---: | ---: |
| HAMD08 | 1 | 0.524 | 0.350 | 0.672 | True | 0.880 | 0.356 |
| HAMD09 | 1 | -0.347 | -0.523 | -0.171 | True | 0.160 | 0.507 |
| HAMD03 | 1 | 0.282 | 0.068 | 0.509 | True | 0.720 | 0.438 |
| HAMD07 | 3 | -0.275 | -0.385 | -0.152 | True | 0.040 | 0.315 |
| HAMD11 | 2 | -0.244 | -0.459 | -0.009 | True | 0.400 | 0.644 |
| HAMD04 | 1 | 0.243 | 0.014 | 0.453 | True | 0.640 | 0.397 |
| HAMD04 | 2 | 0.210 | 0.016 | 0.412 | True | 0.320 | 0.110 |
| HAMD15 | 1 | -0.198 | -0.401 | 0.002 | False | 0.240 | 0.438 |

## Transfer Summary

Negative deltas versus source train mean are improvements. Positive deltas versus target CV indicate cross-dataset degradation relative to same-dataset CV for the same feature/model.

| eval scope | summary target | feature | model | MAE | delta vs source mean | delta vs target CV |
| --- | --- | --- | --- | ---: | ---: | ---: |
| cmdc_cv_overlap | hamd_total_direct | none | train_mean_total | 3.619 | 0.000 | NA |
| cmdc_cv_overlap | hamd_total_direct | text_bge | direct_total_ridge | 3.887 | 0.268 | NA |
| cmdc_cv_overlap | hamd_total_direct | audio_wavlm | direct_total_ridge | 3.973 | 0.354 | NA |
| cmdc_cv_overlap | hamd_total_direct | early_fusion_all | direct_total_ridge | 4.261 | 0.642 | NA |
| cmdc_cv_overlap | hamd_total_from_items | none | train_mean_items | 3.619 | 0.000 | NA |
| cmdc_cv_overlap | hamd_total_from_items | text_bge | itemwise_ridge | 3.699 | 0.080 | NA |
| cmdc_cv_overlap | hamd_total_from_items | audio_wavlm | itemwise_ridge | 3.831 | 0.211 | NA |
| cmdc_cv_overlap | hamd_total_from_items | audio_egemaps | itemwise_ridge | 4.165 | 0.546 | NA |
| cmdc_cv_overlap | macro_hamd_item_mae | none | train_mean_items | 0.581 | 0.000 | NA |
| cmdc_cv_overlap | macro_hamd_item_mae | text_bge | itemwise_ridge | 0.600 | 0.019 | NA |
| cmdc_cv_overlap | macro_hamd_item_mae | audio_egemaps | itemwise_ridge | 0.608 | 0.028 | NA |
| cmdc_cv_overlap | macro_hamd_item_mae | audio_wavlm | itemwise_ridge | 0.613 | 0.033 | NA |
| cmdc_overlap_to_pdch_overlap | hamd_total_direct | none | train_mean_total | 4.072 | 0.000 | -0.013 |
| cmdc_overlap_to_pdch_overlap | hamd_total_direct | text_bge | direct_total_ridge | 4.518 | 0.446 | 0.532 |
| cmdc_overlap_to_pdch_overlap | hamd_total_direct | audio_wavlm | direct_total_ridge | 4.959 | 0.887 | 0.852 |
| cmdc_overlap_to_pdch_overlap | hamd_total_direct | early_fusion_all | direct_total_ridge | 5.116 | 1.044 | 1.129 |
| cmdc_overlap_to_pdch_overlap | hamd_total_from_items | none | train_mean_items | 4.072 | 0.000 | -0.015 |
| cmdc_overlap_to_pdch_overlap | hamd_total_from_items | early_fusion_all | itemwise_ridge | 4.292 | 0.220 | 0.341 |
| cmdc_overlap_to_pdch_overlap | hamd_total_from_items | audio_wavlm | itemwise_ridge | 4.336 | 0.264 | 0.254 |
| cmdc_overlap_to_pdch_overlap | hamd_total_from_items | text_bge | itemwise_ridge | 4.518 | 0.446 | 0.614 |
| cmdc_overlap_to_pdch_overlap | macro_hamd_item_mae | audio_wavlm | itemwise_ridge | 0.717 | -0.006 | 0.011 |
| cmdc_overlap_to_pdch_overlap | macro_hamd_item_mae | none | train_mean_items | 0.724 | 0.000 | 0.021 |
| cmdc_overlap_to_pdch_overlap | macro_hamd_item_mae | text_bge | itemwise_ridge | 0.743 | 0.019 | 0.051 |
| cmdc_overlap_to_pdch_overlap | macro_hamd_item_mae | early_fusion_all | itemwise_ridge | 0.790 | 0.066 | 0.096 |
| pdch_cv_overlap | hamd_total_direct | text_bge | direct_total_ridge | 3.986 | -0.099 | NA |
| pdch_cv_overlap | hamd_total_direct | early_fusion_all | direct_total_ridge | 3.987 | -0.098 | NA |
| pdch_cv_overlap | hamd_total_direct | audio_egemaps | direct_total_ridge | 4.081 | -0.004 | NA |
| pdch_cv_overlap | hamd_total_direct | none | train_mean_total | 4.085 | 0.000 | NA |
| pdch_cv_overlap | hamd_total_from_items | text_bge | itemwise_ridge | 3.904 | -0.183 | NA |
| pdch_cv_overlap | hamd_total_from_items | early_fusion_all | itemwise_ridge | 3.951 | -0.135 | NA |
| pdch_cv_overlap | hamd_total_from_items | audio_egemaps | itemwise_ridge | 4.058 | -0.029 | NA |
| pdch_cv_overlap | hamd_total_from_items | audio_wavlm | itemwise_ridge | 4.082 | -0.005 | NA |
| pdch_cv_overlap | macro_hamd_item_mae | text_bge | itemwise_ridge | 0.692 | -0.011 | NA |
| pdch_cv_overlap | macro_hamd_item_mae | early_fusion_all | itemwise_ridge | 0.695 | -0.008 | NA |
| pdch_cv_overlap | macro_hamd_item_mae | audio_egemaps | itemwise_ridge | 0.697 | -0.006 | NA |
| pdch_cv_overlap | macro_hamd_item_mae | none | train_mean_items | 0.702 | 0.000 | NA |
| pdch_overlap_to_cmdc_overlap | hamd_total_direct | text_bge | direct_total_ridge | 3.528 | -0.070 | -0.359 |
| pdch_overlap_to_cmdc_overlap | hamd_total_direct | audio_wavlm | direct_total_ridge | 3.540 | -0.058 | -0.433 |
| pdch_overlap_to_cmdc_overlap | hamd_total_direct | none | train_mean_total | 3.598 | 0.000 | -0.021 |
| pdch_overlap_to_cmdc_overlap | hamd_total_direct | early_fusion_all | direct_total_ridge | 13.575 | 9.976 | 9.314 |
| pdch_overlap_to_cmdc_overlap | hamd_total_from_items | none | train_mean_items | 3.599 | 0.000 | -0.020 |
| pdch_overlap_to_cmdc_overlap | hamd_total_from_items | text_bge | itemwise_ridge | 3.629 | 0.029 | -0.071 |
| pdch_overlap_to_cmdc_overlap | hamd_total_from_items | audio_wavlm | itemwise_ridge | 3.861 | 0.261 | 0.030 |
| pdch_overlap_to_cmdc_overlap | hamd_total_from_items | audio_egemaps | itemwise_ridge | 7.022 | 3.423 | 2.857 |
| pdch_overlap_to_cmdc_overlap | macro_hamd_item_mae | none | train_mean_items | 0.622 | 0.000 | 0.041 |
| pdch_overlap_to_cmdc_overlap | macro_hamd_item_mae | text_bge | itemwise_ridge | 0.695 | 0.073 | 0.095 |
| pdch_overlap_to_cmdc_overlap | macro_hamd_item_mae | audio_wavlm | itemwise_ridge | 0.787 | 0.165 | 0.173 |
| pdch_overlap_to_cmdc_overlap | macro_hamd_item_mae | early_fusion_all | itemwise_ridge | 1.167 | 0.545 | 0.538 |

## Verdict

- Pass-rule status: `complete_exploratory_same_scale_context_shift_supported`.
- CMDC overlap HAMD subjects: `25`.
- PDCH overlap HAMD subjects: `73`.
- Flagged overlap residual item shifts: `4`.
- Flagged overlap threshold shifts: `7`.
- Weak primary transfer directions: `2`.

MV18 remains exploratory because CMDC HAMD has only 25 subjects, but the same-scale control still shows dataset/context sensitivity through flagged HAMD item/threshold shifts or weak bidirectional transfer.

## Hygiene

- Artifact hygiene passed: `True`.
- Row-level predictions are written as a local-only ignored CSV.
- Text content, media paths, file locators, feature arrays, learned embeddings, and fitted parameter files are not written.
