# P5 MV24 Measurement-Aware Ordinal Main Table

Generated: `2026-09-02T02:07:33+00:00`

## Scope

This run replaces earlier measurement-aware proxies with a single formal architecture: a shared symptom layer and corpus-specific cumulative-logit ordinal heads. The main comparison uses the same official Qwen3 + WavLM + OpenFace subject-level representation for all methods, but target-label supervision is reported in two explicit regimes. The target-calibrated regime now includes fair ablations that let target calibration labels update the same shared layers, so the corpus-specific-head baseline is no longer treated as the identifying comparator for the measurement pathway. The co-primary metrics are ordinal symptom reconstruction and calibration; secondary clinical-reader metrics convert the shared-PHQ total into a thresholded endpoint.

## Feature View

| asset | dataset | modality | rows | columns |
| --- | --- | --- | ---: | ---: |
| audio_wavlm_base_plus | cmdc | audio | 77 | 768 |
| audio_wavlm_base_plus | edaic | audio | 219 | 768 |
| text_qwen3 | cmdc | text | 77 | 1024 |
| text_qwen3 | edaic | text | 219 | 1024 |
| video_openface_common | cmdc | video | 44 | 204 |
| video_openface_common | edaic | video | 219 | 204 |

## Best Primary-Score Rows By Supervision Regime

| transfer | regime | best method | score | macro item MAE | calibration MAE | seeds |
| --- | --- | --- | ---: | ---: | ---: | ---: |
| cmdc_to_edaic_phq_shared | target_calibrated | full_measurement_aware | 1.2434 | 0.8179 | 0.4256 | 5 |
| cmdc_to_edaic_phq_shared | zero_target_label | strongest_foundation_baseline | 1.5367 | 0.9489 | 0.5878 | 5 |
| edaic_to_cmdc_phq_shared | target_calibrated | direct_multitask_shared_head | 0.9467 | 0.6066 | 0.3402 | 5 |
| edaic_to_cmdc_phq_shared | zero_target_label | coral | 1.4126 | 0.9502 | 0.4624 | 5 |

## Zero-Target-Label Table

**Panel A. CMDC -> E-DAIC.**

| method | regime | n_cal | macro item MAE | calibration MAE | total MAE |
| --- | --- | ---: | ---: | ---: | ---: |
| **Zero-target-label context** |  |  |  |  |  |
| ERM | zero-label | 0 | 1.039 [0.983, 1.094] | 0.734 [0.673, 0.795] | 5.724 [5.436, 6.012] |
| CORAL | zero-label | 0 | 1.014 [0.970, 1.057] | 0.677 [0.619, 0.735] | 6.498 [5.977, 7.019] |
| MMD | zero-label | 0 | 1.044 [0.735, 1.354] | 1.030 [0.728, 1.333] | 5.870 [4.921, 6.820] |
| DANN | zero-label | 0 | 1.438 [1.382, 1.494] | 0.744 [0.674, 0.815] | 7.346 [7.025, 7.667] |
| Strongest foundation | zero-label | 0 | 0.949 [0.900, 0.998] | 0.588 [0.510, 0.666] | 6.118 [5.740, 6.497] |
| Latent-only | zero-label | 0 | 1.055 [1.006, 1.105] | 0.735 [0.691, 0.780] | 6.751 [6.260, 7.241] |

**Panel B. E-DAIC -> CMDC.**

| method | regime | n_cal | macro item MAE | calibration MAE | total MAE |
| --- | --- | ---: | ---: | ---: | ---: |
| **Zero-target-label context** |  |  |  |  |  |
| ERM | zero-label | 0 | 1.151 [0.970, 1.331] | 0.911 [0.794, 1.029] | 7.469 [6.070, 8.867] |
| CORAL | zero-label | 0 | 0.950 [0.899, 1.001] | 0.462 [0.361, 0.564] | 6.858 [6.402, 7.313] |
| MMD | zero-label | 0 | 0.980 [0.904, 1.057] | 0.451 [0.350, 0.552] | 6.164 [5.625, 6.704] |
| DANN | zero-label | 0 | 1.264 [1.037, 1.491] | 0.910 [0.684, 1.137] | 8.599 [6.651, 10.547] |
| Strongest foundation | zero-label | 0 | 1.738 [1.626, 1.849] | 1.625 [1.476, 1.774] | 13.143 [12.027, 14.258] |
| Latent-only | zero-label | 0 | 1.861 [1.763, 1.959] | 1.802 [1.684, 1.920] | 14.469 [13.547, 15.392] |

## Target-Calibrated Table

**Panel A. CMDC -> E-DAIC.**

| method | regime | n_cal | macro item MAE | calibration MAE | total MAE |
| --- | --- | ---: | ---: | ---: | ---: |
| **Target-calibrated comparison** |  |  |  |  |  |
| Corpus-specific head | calibrated | 66 | 0.967 [0.923, 1.010] | 0.599 [0.561, 0.637] | 6.296 [5.992, 6.600] |
| Direct target fine-tune | calibrated | 66 | 0.851 [0.823, 0.879] | 0.482 [0.401, 0.562] | 5.579 [5.255, 5.903] |
| Direct source+target multitask | calibrated | 66 | 0.869 [0.809, 0.929] | 0.475 [0.390, 0.559] | 5.707 [5.327, 6.086] |
| Shared ordinal head | calibrated | 66 | 0.819 [0.799, 0.840] | 0.433 [0.394, 0.472] | 5.297 [5.133, 5.461] |
| Generic target MLP head | calibrated | 66 | 0.884 [0.862, 0.906] | 0.455 [0.401, 0.509] | 5.618 [5.406, 5.829] |
| Measurement-aware | calibrated | 66 | 0.818 [0.810, 0.827] | 0.433 [0.384, 0.482] | 5.304 [5.160, 5.448] |
| Measurement-aware + MMD | calibrated | 66 | 0.818 [0.795, 0.840] | 0.426 [0.371, 0.480] | 5.331 [5.093, 5.568] |

**Panel B. E-DAIC -> CMDC.**

| method | regime | n_cal | macro item MAE | calibration MAE | total MAE |
| --- | --- | ---: | ---: | ---: | ---: |
| **Target-calibrated comparison** |  |  |  |  |  |
| Corpus-specific head | calibrated | 24 | 1.346 [1.195, 1.497] | 1.059 [0.892, 1.227] | 9.665 [8.408, 10.921] |
| Direct target fine-tune | calibrated | 24 | 0.607 [0.531, 0.684] | 0.358 [0.268, 0.449] | 3.220 [2.811, 3.629] |
| Direct source+target multitask | calibrated | 24 | 0.607 [0.534, 0.679] | 0.340 [0.284, 0.396] | 3.194 [2.731, 3.656] |
| Shared ordinal head | calibrated | 24 | 0.644 [0.564, 0.725] | 0.343 [0.267, 0.419] | 3.239 [2.562, 3.915] |
| Generic target MLP head | calibrated | 24 | 0.622 [0.547, 0.698] | 0.361 [0.292, 0.429] | 3.363 [2.745, 3.980] |
| Measurement-aware | calibrated | 24 | 0.645 [0.566, 0.723] | 0.342 [0.271, 0.413] | 3.255 [2.588, 3.922] |
| Measurement-aware + MMD | calibrated | 24 | 0.645 [0.566, 0.723] | 0.342 [0.271, 0.413] | 3.255 [2.588, 3.922] |

## Targeted Item Analysis

Positive delta means Measurement-aware has lower item MAE than the Shared ordinal head. This is a descriptive targeted analysis, not a five-seed superiority test.

**CMDC -> E-DAIC.**

| item set | audit role | shared ordinal MAE | measurement-aware MAE | delta shared - measurement-aware | MA lower-error seeds | reading |
| --- | --- | ---: | ---: | ---: | ---: | --- |
| C01-C08 | all shared PHQ items | 0.819 [0.799, 0.840] | 0.818 [0.810, 0.827] | 0.001 [-0.019, 0.021] | 3/5 | near tie |
| C01/C04/C05/C07 | measurement-gate anchor items | 0.863 [0.850, 0.876] | 0.862 [0.851, 0.873] | 0.001 [-0.018, 0.019] | 2/5 | near tie |
| C01 | anchor | 0.737 [0.654, 0.820] | 0.718 [0.636, 0.800] | 0.018 [-0.005, 0.042] | 5/5 | measurement-aware lower error |
| C04 | anchor | 0.951 [0.907, 0.995] | 0.929 [0.887, 0.971] | 0.022 [-0.005, 0.049] | 4/5 | measurement-aware lower error |
| C05 | anchor | 0.966 [0.898, 1.034] | 0.997 [0.943, 1.051] | -0.031 [-0.090, 0.028] | 1/5 | shared ordinal lower error |
| C07 | anchor | 0.798 [0.773, 0.823] | 0.804 [0.771, 0.838] | -0.006 [-0.024, 0.012] | 1/5 | near tie |
| C02/C06 | measurement-gate threshold-shift items | 0.846 [0.792, 0.899] | 0.841 [0.808, 0.875] | 0.004 [-0.019, 0.027] | 4/5 | near tie |
| C02 | threshold_shift | 0.822 [0.760, 0.884] | 0.809 [0.764, 0.854] | 0.013 [-0.010, 0.035] | 4/5 | measurement-aware lower error |
| C06 | threshold_shift | 0.869 [0.808, 0.931] | 0.873 [0.830, 0.917] | -0.004 [-0.029, 0.021] | 3/5 | near tie |
| C03/C08 | non-anchor non-primary-shift items | 0.706 [0.693, 0.720] | 0.708 [0.689, 0.727] | -0.002 [-0.025, 0.021] | 3/5 | near tie |

**E-DAIC -> CMDC.**

| item set | audit role | shared ordinal MAE | measurement-aware MAE | delta shared - measurement-aware | MA lower-error seeds | reading |
| --- | --- | ---: | ---: | ---: | ---: | --- |
| C01-C08 | all shared PHQ items | 0.644 [0.564, 0.725] | 0.645 [0.566, 0.723] | -0.000 [-0.004, 0.004] | 2/5 | near tie |
| C01/C04/C05/C07 | measurement-gate anchor items | 0.652 [0.564, 0.739] | 0.652 [0.567, 0.737] | -0.001 [-0.006, 0.004] | 1/5 | near tie |
| C01 | anchor | 0.724 [0.572, 0.876] | 0.724 [0.573, 0.875] | -0.001 [-0.005, 0.004] | 2/5 | near tie |
| C04 | anchor | 0.543 [0.426, 0.661] | 0.544 [0.432, 0.656] | -0.001 [-0.007, 0.005] | 2/5 | near tie |
| C05 | anchor | 0.697 [0.626, 0.769] | 0.696 [0.628, 0.764] | 0.001 [-0.009, 0.011] | 4/5 | near tie |
| C07 | anchor | 0.643 [0.512, 0.774] | 0.645 [0.510, 0.780] | -0.002 [-0.011, 0.007] | 1/5 | near tie |
| C02/C06 | measurement-gate threshold-shift items | 0.618 [0.509, 0.727] | 0.616 [0.510, 0.722] | 0.002 [-0.004, 0.007] | 3/5 | near tie |
| C02 | threshold_shift | 0.759 [0.615, 0.904] | 0.757 [0.616, 0.897] | 0.003 [-0.003, 0.008] | 4/5 | near tie |
| C06 | threshold_shift | 0.476 [0.395, 0.558] | 0.476 [0.396, 0.556] | 0.000 [-0.005, 0.006] | 3/5 | near tie |
| C03/C08 | non-anchor non-primary-shift items | 0.657 [0.591, 0.722] | 0.658 [0.599, 0.716] | -0.001 [-0.010, 0.008] | 1/5 | near tie |

## Secondary Severity And Binary Endpoint Metrics

| transfer | regime | method | target labels | labeled target calib n | total MAE | total CCC | macro-F1 | BA | AUROC | AUPRC | sensitivity | specificity |
| --- | --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| cmdc_to_edaic_phq_shared | zero_target_label | erm | no | 0 | 5.724 [5.436, 6.012] | 0.034 [-0.035, 0.104] | 0.455 [0.428, 0.482] | 0.470 [0.446, 0.495] | 0.514 [0.459, 0.569] | 0.311 [0.286, 0.337] | 0.139 [0.087, 0.192] | 0.802 [0.745, 0.858] |
| cmdc_to_edaic_phq_shared | zero_target_label | coral | no | 0 | 6.498 [5.977, 7.019] | 0.201 [0.123, 0.279] | 0.521 [0.483, 0.559] | 0.529 [0.489, 0.568] | 0.540 [0.473, 0.606] | 0.351 [0.300, 0.402] | 0.439 [0.375, 0.504] | 0.619 [0.568, 0.670] |
| cmdc_to_edaic_phq_shared | zero_target_label | mmd | no | 0 | 5.870 [4.921, 6.820] | 0.007 [-0.005, 0.020] | 0.410 [0.409, 0.412] | 0.497 [0.494, 0.500] | 0.497 [0.494, 0.500] | 0.302 [0.299, 0.305] | 0.000 [0.000, 0.000] | 0.994 [0.988, 1.000] |
| cmdc_to_edaic_phq_shared | zero_target_label | dann | no | 0 | 7.346 [7.025, 7.667] | 0.020 [-0.092, 0.131] | 0.449 [0.379, 0.518] | 0.500 [0.403, 0.598] | 0.511 [0.419, 0.603] | 0.333 [0.305, 0.362] | 0.617 [0.433, 0.802] | 0.383 [0.340, 0.427] |
| cmdc_to_edaic_phq_shared | zero_target_label | strongest_foundation_baseline | no | 0 | 6.118 [5.740, 6.497] | 0.062 [-0.022, 0.146] | 0.479 [0.442, 0.516] | 0.485 [0.449, 0.521] | 0.507 [0.470, 0.545] | 0.331 [0.294, 0.368] | 0.191 [0.151, 0.231] | 0.779 [0.730, 0.828] |
| cmdc_to_edaic_phq_shared | zero_target_label | latent_only | no | 0 | 6.751 [6.260, 7.241] | 0.050 [-0.045, 0.145] | 0.507 [0.466, 0.549] | 0.508 [0.466, 0.549] | 0.515 [0.461, 0.569] | 0.321 [0.281, 0.362] | 0.309 [0.247, 0.370] | 0.707 [0.649, 0.764] |
| cmdc_to_edaic_phq_shared | target_calibrated | corpus_specific_head | yes | 66 | 6.296 [5.992, 6.600] | 0.059 [-0.033, 0.150] | 0.492 [0.457, 0.527] | 0.493 [0.459, 0.527] | 0.517 [0.461, 0.573] | 0.323 [0.279, 0.367] | 0.265 [0.207, 0.324] | 0.721 [0.671, 0.772] |
| cmdc_to_edaic_phq_shared | target_calibrated | direct_target_finetune | yes | 66 | 5.579 [5.255, 5.903] | 0.103 [0.016, 0.191] | 0.502 [0.441, 0.562] | 0.523 [0.491, 0.555] | 0.579 [0.536, 0.621] | 0.370 [0.339, 0.402] | 0.170 [0.040, 0.300] | 0.877 [0.804, 0.950] |
| cmdc_to_edaic_phq_shared | target_calibrated | direct_multitask_shared_head | yes | 66 | 5.707 [5.327, 6.086] | 0.092 [-0.006, 0.190] | 0.516 [0.458, 0.574] | 0.532 [0.499, 0.565] | 0.564 [0.532, 0.596] | 0.357 [0.312, 0.403] | 0.191 [0.075, 0.308] | 0.873 [0.791, 0.954] |
| cmdc_to_edaic_phq_shared | target_calibrated | shared_head_joint_adaptation | yes | 66 | 5.297 [5.133, 5.461] | 0.179 [0.150, 0.207] | 0.547 [0.525, 0.569] | 0.554 [0.534, 0.573] | 0.615 [0.579, 0.651] | 0.442 [0.396, 0.488] | 0.217 [0.184, 0.250] | 0.890 [0.855, 0.924] |
| cmdc_to_edaic_phq_shared | target_calibrated | generic_target_mlp_head | yes | 66 | 5.618 [5.406, 5.829] | 0.114 [0.065, 0.163] | 0.528 [0.478, 0.579] | 0.537 [0.504, 0.570] | 0.578 [0.545, 0.611] | 0.376 [0.329, 0.423] | 0.248 [0.112, 0.384] | 0.826 [0.750, 0.903] |
| cmdc_to_edaic_phq_shared | target_calibrated | full_without_mmd | yes | 66 | 5.304 [5.160, 5.448] | 0.162 [0.095, 0.229] | 0.544 [0.512, 0.576] | 0.554 [0.528, 0.579] | 0.604 [0.548, 0.660] | 0.432 [0.359, 0.506] | 0.204 [0.145, 0.263] | 0.903 [0.861, 0.944] |
| cmdc_to_edaic_phq_shared | target_calibrated | full_measurement_aware | yes | 66 | 5.331 [5.093, 5.568] | 0.155 [0.102, 0.207] | 0.530 [0.494, 0.566] | 0.541 [0.514, 0.567] | 0.612 [0.560, 0.663] | 0.431 [0.363, 0.500] | 0.196 [0.138, 0.253] | 0.886 [0.856, 0.916] |
| edaic_to_cmdc_phq_shared | zero_target_label | erm | no | 0 | 7.469 [6.070, 8.867] | 0.079 [-0.023, 0.180] | 0.429 [0.284, 0.573] | 0.529 [0.455, 0.604] | 0.621 [0.521, 0.720] | 0.597 [0.524, 0.670] | 0.475 [0.000, 1.000] | 0.583 [0.000, 1.000] |
| edaic_to_cmdc_phq_shared | zero_target_label | coral | no | 0 | 6.858 [6.402, 7.313] | 0.163 [0.051, 0.274] | 0.552 [0.459, 0.644] | 0.575 [0.496, 0.654] | 0.515 [0.455, 0.574] | 0.561 [0.499, 0.622] | 0.250 [0.140, 0.360] | 0.900 [0.787, 1.000] |
| edaic_to_cmdc_phq_shared | zero_target_label | mmd | no | 0 | 6.164 [5.625, 6.704] | 0.252 [0.079, 0.426] | 0.653 [0.528, 0.779] | 0.654 [0.538, 0.771] | 0.675 [0.572, 0.778] | 0.628 [0.515, 0.742] | 0.525 [0.323, 0.727] | 0.783 [0.691, 0.876] |
| edaic_to_cmdc_phq_shared | zero_target_label | dann | no | 0 | 8.599 [6.651, 10.547] | 0.109 [-0.008, 0.227] | 0.399 [0.191, 0.607] | 0.521 [0.401, 0.641] | 0.633 [0.519, 0.748] | 0.632 [0.456, 0.808] | 0.825 [0.590, 1.000] | 0.217 [0.000, 0.608] |
| edaic_to_cmdc_phq_shared | zero_target_label | strongest_foundation_baseline | no | 0 | 13.143 [12.027, 14.258] | 0.038 [0.010, 0.066] | 0.286 [0.286, 0.286] | 0.500 [0.500, 0.500] | 0.706 [0.623, 0.789] | 0.700 [0.594, 0.805] | 1.000 [1.000, 1.000] | 0.000 [0.000, 0.000] |
| edaic_to_cmdc_phq_shared | zero_target_label | latent_only | no | 0 | 14.469 [13.547, 15.392] | 0.026 [-0.003, 0.054] | 0.286 [0.286, 0.286] | 0.500 [0.500, 0.500] | 0.692 [0.586, 0.797] | 0.686 [0.572, 0.801] | 1.000 [1.000, 1.000] | 0.000 [0.000, 0.000] |
| edaic_to_cmdc_phq_shared | target_calibrated | corpus_specific_head | yes | 24 | 9.665 [8.408, 10.921] | 0.093 [0.017, 0.168] | 0.303 [0.255, 0.352] | 0.508 [0.485, 0.531] | 0.654 [0.551, 0.758] | 0.641 [0.511, 0.770] | 1.000 [1.000, 1.000] | 0.017 [0.000, 0.063] |
| edaic_to_cmdc_phq_shared | target_calibrated | direct_target_finetune | yes | 24 | 3.220 [2.811, 3.629] | 0.798 [0.702, 0.893] | 0.913 [0.809, 1.000] | 0.908 [0.798, 1.000] | 0.988 [0.971, 1.000] | 0.982 [0.957, 1.000] | 0.850 [0.648, 1.000] | 0.967 [0.910, 1.000] |
| edaic_to_cmdc_phq_shared | target_calibrated | direct_multitask_shared_head | yes | 24 | 3.194 [2.731, 3.656] | 0.801 [0.704, 0.898] | 0.914 [0.811, 1.000] | 0.912 [0.804, 1.000] | 0.983 [0.964, 1.000] | 0.975 [0.942, 1.000] | 0.875 [0.685, 1.000] | 0.950 [0.893, 1.000] |
| edaic_to_cmdc_phq_shared | target_calibrated | shared_head_joint_adaptation | yes | 24 | 3.239 [2.562, 3.915] | 0.784 [0.667, 0.902] | 0.880 [0.777, 0.983] | 0.875 [0.765, 0.985] | 0.981 [0.964, 0.998] | 0.972 [0.947, 0.998] | 0.800 [0.592, 1.000] | 0.950 [0.893, 1.000] |
| edaic_to_cmdc_phq_shared | target_calibrated | generic_target_mlp_head | yes | 24 | 3.363 [2.745, 3.980] | 0.786 [0.659, 0.912] | 0.925 [0.821, 1.000] | 0.925 [0.814, 1.000] | 0.988 [0.971, 1.000] | 0.982 [0.957, 1.000] | 0.900 [0.698, 1.000] | 0.950 [0.893, 1.000] |
| edaic_to_cmdc_phq_shared | target_calibrated | full_without_mmd | yes | 24 | 3.255 [2.588, 3.922] | 0.784 [0.670, 0.899] | 0.890 [0.803, 0.977] | 0.883 [0.787, 0.979] | 0.983 [0.966, 1.000] | 0.975 [0.949, 1.000] | 0.800 [0.592, 1.000] | 0.967 [0.910, 1.000] |
| edaic_to_cmdc_phq_shared | target_calibrated | full_measurement_aware | yes | 24 | 3.255 [2.588, 3.922] | 0.784 [0.670, 0.899] | 0.890 [0.803, 0.977] | 0.883 [0.787, 0.979] | 0.983 [0.966, 1.000] | 0.975 [0.949, 1.000] | 0.800 [0.592, 1.000] | 0.967 [0.910, 1.000] |

## Lambda-MMD Sensitivity

| transfer | lambda_mmd | seeds | recon+calib score | macro item MAE | calibration MAE | total MAE | binary macro-F1 | binary BA |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| cmdc_to_edaic_phq_shared | 0 | 5 | 1.251 [1.194, 1.309] | 0.818 [0.810, 0.827] | 0.433 [0.384, 0.482] | 5.304 [5.160, 5.448] | 0.544 [0.512, 0.576] | 0.554 [0.528, 0.579] |
| cmdc_to_edaic_phq_shared | 0.0001 | 5 | 1.251 [1.207, 1.294] | 0.821 [0.808, 0.834] | 0.430 [0.390, 0.469] | 5.307 [5.187, 5.427] | 0.546 [0.508, 0.584] | 0.552 [0.520, 0.584] |
| cmdc_to_edaic_phq_shared | 0.001 | 5 | 1.243 [1.170, 1.317] | 0.818 [0.795, 0.840] | 0.426 [0.371, 0.480] | 5.331 [5.093, 5.568] | 0.530 [0.494, 0.566] | 0.541 [0.514, 0.567] |
| cmdc_to_edaic_phq_shared | 0.01 | 5 | 1.243 [1.173, 1.313] | 0.825 [0.803, 0.846] | 0.418 [0.362, 0.474] | 5.287 [5.046, 5.527] | 0.544 [0.531, 0.558] | 0.551 [0.538, 0.564] |
| cmdc_to_edaic_phq_shared | 0.1 | 5 | 1.250 [1.214, 1.285] | 0.819 [0.815, 0.823] | 0.431 [0.395, 0.466] | 5.266 [5.154, 5.379] | 0.557 [0.535, 0.578] | 0.561 [0.545, 0.577] |
| edaic_to_cmdc_phq_shared | 0 | 5 | 0.987 [0.863, 1.111] | 0.645 [0.566, 0.723] | 0.342 [0.271, 0.413] | 3.255 [2.588, 3.922] | 0.890 [0.803, 0.977] | 0.883 [0.787, 0.979] |
| edaic_to_cmdc_phq_shared | 0.0001 | 5 | 0.987 [0.863, 1.111] | 0.645 [0.566, 0.723] | 0.342 [0.271, 0.413] | 3.255 [2.588, 3.922] | 0.890 [0.803, 0.977] | 0.883 [0.787, 0.979] |
| edaic_to_cmdc_phq_shared | 0.001 | 5 | 0.987 [0.863, 1.111] | 0.645 [0.566, 0.723] | 0.342 [0.271, 0.413] | 3.255 [2.588, 3.922] | 0.890 [0.803, 0.977] | 0.883 [0.787, 0.979] |
| edaic_to_cmdc_phq_shared | 0.01 | 5 | 0.987 [0.863, 1.111] | 0.645 [0.566, 0.723] | 0.342 [0.271, 0.413] | 3.256 [2.586, 3.925] | 0.890 [0.803, 0.977] | 0.883 [0.787, 0.979] |
| edaic_to_cmdc_phq_shared | 0.1 | 5 | 0.988 [0.863, 1.114] | 0.647 [0.567, 0.727] | 0.341 [0.270, 0.413] | 3.263 [2.579, 3.947] | 0.890 [0.803, 0.977] | 0.883 [0.787, 0.979] |

## Supervision-Aware Main Result Table

**Panel A. CMDC -> E-DAIC.**

| method | regime | n_cal | macro item MAE | calibration MAE | total MAE |
| --- | --- | ---: | ---: | ---: | ---: |
| **Zero-target-label context** |  |  |  |  |  |
| ERM | zero-label | 0 | 1.039 [0.983, 1.094] | 0.734 [0.673, 0.795] | 5.724 [5.436, 6.012] |
| CORAL | zero-label | 0 | 1.014 [0.970, 1.057] | 0.677 [0.619, 0.735] | 6.498 [5.977, 7.019] |
| MMD | zero-label | 0 | 1.044 [0.735, 1.354] | 1.030 [0.728, 1.333] | 5.870 [4.921, 6.820] |
| DANN | zero-label | 0 | 1.438 [1.382, 1.494] | 0.744 [0.674, 0.815] | 7.346 [7.025, 7.667] |
| Strongest foundation | zero-label | 0 | 0.949 [0.900, 0.998] | 0.588 [0.510, 0.666] | 6.118 [5.740, 6.497] |
| Latent-only | zero-label | 0 | 1.055 [1.006, 1.105] | 0.735 [0.691, 0.780] | 6.751 [6.260, 7.241] |
| **Target-calibrated comparison** |  |  |  |  |  |
| Corpus-specific head | calibrated | 66 | 0.967 [0.923, 1.010] | 0.599 [0.561, 0.637] | 6.296 [5.992, 6.600] |
| Direct target fine-tune | calibrated | 66 | 0.851 [0.823, 0.879] | 0.482 [0.401, 0.562] | 5.579 [5.255, 5.903] |
| Direct source+target multitask | calibrated | 66 | 0.869 [0.809, 0.929] | 0.475 [0.390, 0.559] | 5.707 [5.327, 6.086] |
| Shared ordinal head | calibrated | 66 | 0.819 [0.799, 0.840] | 0.433 [0.394, 0.472] | 5.297 [5.133, 5.461] |
| Generic target MLP head | calibrated | 66 | 0.884 [0.862, 0.906] | 0.455 [0.401, 0.509] | 5.618 [5.406, 5.829] |
| Measurement-aware | calibrated | 66 | 0.818 [0.810, 0.827] | 0.433 [0.384, 0.482] | 5.304 [5.160, 5.448] |
| Measurement-aware + MMD | calibrated | 66 | 0.818 [0.795, 0.840] | 0.426 [0.371, 0.480] | 5.331 [5.093, 5.568] |

**Panel B. E-DAIC -> CMDC.**

| method | regime | n_cal | macro item MAE | calibration MAE | total MAE |
| --- | --- | ---: | ---: | ---: | ---: |
| **Zero-target-label context** |  |  |  |  |  |
| ERM | zero-label | 0 | 1.151 [0.970, 1.331] | 0.911 [0.794, 1.029] | 7.469 [6.070, 8.867] |
| CORAL | zero-label | 0 | 0.950 [0.899, 1.001] | 0.462 [0.361, 0.564] | 6.858 [6.402, 7.313] |
| MMD | zero-label | 0 | 0.980 [0.904, 1.057] | 0.451 [0.350, 0.552] | 6.164 [5.625, 6.704] |
| DANN | zero-label | 0 | 1.264 [1.037, 1.491] | 0.910 [0.684, 1.137] | 8.599 [6.651, 10.547] |
| Strongest foundation | zero-label | 0 | 1.738 [1.626, 1.849] | 1.625 [1.476, 1.774] | 13.143 [12.027, 14.258] |
| Latent-only | zero-label | 0 | 1.861 [1.763, 1.959] | 1.802 [1.684, 1.920] | 14.469 [13.547, 15.392] |
| **Target-calibrated comparison** |  |  |  |  |  |
| Corpus-specific head | calibrated | 24 | 1.346 [1.195, 1.497] | 1.059 [0.892, 1.227] | 9.665 [8.408, 10.921] |
| Direct target fine-tune | calibrated | 24 | 0.607 [0.531, 0.684] | 0.358 [0.268, 0.449] | 3.220 [2.811, 3.629] |
| Direct source+target multitask | calibrated | 24 | 0.607 [0.534, 0.679] | 0.340 [0.284, 0.396] | 3.194 [2.731, 3.656] |
| Shared ordinal head | calibrated | 24 | 0.644 [0.564, 0.725] | 0.343 [0.267, 0.419] | 3.239 [2.562, 3.915] |
| Generic target MLP head | calibrated | 24 | 0.622 [0.547, 0.698] | 0.361 [0.292, 0.429] | 3.363 [2.745, 3.980] |
| Measurement-aware | calibrated | 24 | 0.645 [0.566, 0.723] | 0.342 [0.271, 0.413] | 3.255 [2.588, 3.922] |
| Measurement-aware + MMD | calibrated | 24 | 0.645 [0.566, 0.723] | 0.342 [0.271, 0.413] | 3.255 [2.588, 3.922] |

## Interpretation Handle

Fair calibrated pathway gate: `not_passed_uniform_measurement_pathway_superiority`.

Large gains over the frozen corpus-specific-head baseline cannot be attributed uniquely to the measurement-aware target pathway. The improvement over `corpus_specific_head` remains useful, but that row freezes the source-trained shared symptom layer and therefore does not identify the measurement-aware target pathway by itself. The manuscript claim should foreground target calibration/shared-layer adaptation as the robust finding and describe the corpus-specific ordinal pathway as competitive and direction-dependent unless the fair gate passes in a future rerun. Standard binary endpoint metrics are reported as secondary clinical orientation, not as the paper's primary objective.
