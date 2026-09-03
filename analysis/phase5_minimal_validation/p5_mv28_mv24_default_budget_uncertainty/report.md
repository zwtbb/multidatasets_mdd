# P5 MV28 Target-Label Budget And Uncertainty

Generated: `2026-09-03T02:28:39+00:00`

## Scope

MV28 tests whether source-plus-target calibrated adaptation still improves over target-only training when the labeled target budget is matched. It also replaces five-seed superiority language with repeated subject-level calibration/evaluation splits and participant-bootstrap paired uncertainty.

## Design

- Transfer directions: `edaic_to_cmdc_phq_shared;cmdc_to_edaic_phq_shared`.
- Target budgets: `mv24_default`.
- Repeated splits per direction-budget: `30`.
- Participant bootstrap draws per split: `200`.
- Methods: `target_only_direct_mlp;target_only_ordinal;direct_target_finetune;direct_multitask_shared_head;shared_head_joint_adaptation;generic_target_mlp_head;full_without_mmd`.

## Label-Budget Curve

**CMDC -> E-DAIC.**

| k | eval n | method | regime | macro item MAE | total MAE | binned item calibration MAE | abs CITL | abs slope error |
| ---: | ---: | --- | --- | ---: | ---: | ---: | ---: | ---: |
| 66 | 153 | Target-only direct MLP | target_only | 0.840 [0.786, 0.889] | 5.426 [4.910, 5.910] | 0.460 [0.362, 0.541] | 1.266 [0.202, 2.389] | 0.770 [0.610, 0.919] |
| 66 | 153 | Target-only ordinal | target_only | 0.855 [0.804, 0.902] | 5.653 [5.238, 6.047] | 0.531 [0.445, 0.616] | 1.698 [0.635, 2.700] | 0.797 [0.680, 0.948] |
| 66 | 153 | Source warm-start target fine-tune | source_plus_target_calibrated | 0.862 [0.789, 0.927] | 5.602 [4.950, 6.329] | 0.475 [0.306, 0.612] | 0.895 [0.183, 1.935] | 0.774 [0.566, 0.957] |
| 66 | 153 | Source+target direct multitask | source_plus_target_calibrated | 0.890 [0.825, 0.954] | 5.836 [5.299, 6.547] | 0.514 [0.413, 0.607] | 0.587 [0.051, 1.608] | 0.819 [0.684, 0.974] |
| 66 | 153 | Shared ordinal head | source_plus_target_calibrated | 0.875 [0.811, 0.948] | 5.723 [5.144, 6.364] | 0.516 [0.403, 0.627] | 1.063 [0.179, 1.970] | 0.789 [0.627, 0.927] |
| 66 | 153 | Generic target MLP head | source_plus_target_calibrated | 0.870 [0.787, 0.921] | 5.692 [5.101, 6.261] | 0.489 [0.363, 0.591] | 0.699 [0.029, 1.892] | 0.805 [0.622, 0.960] |
| 66 | 153 | Measurement-aware ordinal | source_plus_target_calibrated | 0.873 [0.809, 0.955] | 5.714 [5.111, 6.358] | 0.517 [0.398, 0.634] | 1.080 [0.217, 2.119] | 0.787 [0.630, 0.923] |

**E-DAIC -> CMDC.**

| k | eval n | method | regime | macro item MAE | total MAE | binned item calibration MAE | abs CITL | abs slope error |
| ---: | ---: | --- | --- | ---: | ---: | ---: | ---: | ---: |
| 24 | 20 | Target-only direct MLP | target_only | 0.645 [0.549, 0.779] | 3.759 [2.934, 4.928] | 0.423 [0.329, 0.548] | 1.560 [0.311, 3.040] | 0.149 [0.003, 0.385] |
| 24 | 20 | Target-only ordinal | target_only | 0.660 [0.559, 0.803] | 3.905 [3.011, 5.367] | 0.463 [0.358, 0.603] | 1.590 [0.271, 3.476] | 0.191 [0.028, 0.420] |
| 24 | 20 | Source warm-start target fine-tune | source_plus_target_calibrated | 0.658 [0.562, 0.786] | 3.714 [2.833, 5.138] | 0.414 [0.302, 0.537] | 1.259 [0.079, 2.682] | 0.142 [0.004, 0.343] |
| 24 | 20 | Source+target direct multitask | source_plus_target_calibrated | 0.660 [0.549, 0.795] | 3.728 [2.779, 5.226] | 0.422 [0.295, 0.535] | 1.270 [0.105, 2.837] | 0.151 [0.017, 0.358] |
| 24 | 20 | Shared ordinal head | source_plus_target_calibrated | 0.673 [0.563, 0.826] | 3.828 [2.929, 5.324] | 0.444 [0.318, 0.570] | 1.393 [0.149, 2.905] | 0.167 [0.019, 0.422] |
| 24 | 20 | Generic target MLP head | source_plus_target_calibrated | 0.654 [0.542, 0.790] | 3.734 [2.716, 5.223] | 0.392 [0.260, 0.507] | 1.184 [0.083, 2.416] | 0.149 [0.006, 0.388] |
| 24 | 20 | Measurement-aware ordinal | source_plus_target_calibrated | 0.674 [0.563, 0.826] | 3.832 [2.933, 5.334] | 0.442 [0.318, 0.571] | 1.395 [0.144, 2.909] | 0.168 [0.020, 0.426] |

## Source-Plus-Target Versus Target-Only

Negative deltas mean the source-plus-target method has lower error than the target-only direct MLP under the same target-label budget.

**CMDC -> E-DAIC.**

| k | method | metric | delta method - target-only | split fraction | splits |
| ---: | --- | --- | ---: | ---: | ---: |
| 66 | Source+target direct multitask | target_binned_item_calibration_mae | 0.055 [-0.085, 0.164] | 0.20 | 30 |
| 66 | Source+target direct multitask | target_macro_item_mae | 0.050 [-0.024, 0.123] | 0.13 | 30 |
| 66 | Source+target direct multitask | target_total_mae | 0.410 [-0.254, 1.073] | 0.13 | 30 |
| 66 | Source warm-start target fine-tune | target_binned_item_calibration_mae | 0.015 [-0.104, 0.126] | 0.43 | 30 |
| 66 | Source warm-start target fine-tune | target_macro_item_mae | 0.022 [-0.044, 0.086] | 0.33 | 30 |
| 66 | Source warm-start target fine-tune | target_total_mae | 0.176 [-0.335, 0.800] | 0.43 | 30 |
| 66 | Measurement-aware ordinal | target_binned_item_calibration_mae | 0.057 [-0.045, 0.177] | 0.20 | 30 |
| 66 | Measurement-aware ordinal | target_macro_item_mae | 0.033 [-0.038, 0.105] | 0.27 | 30 |
| 66 | Measurement-aware ordinal | target_total_mae | 0.288 [-0.225, 0.861] | 0.27 | 30 |
| 66 | Generic target MLP head | target_binned_item_calibration_mae | 0.029 [-0.070, 0.138] | 0.33 | 30 |
| 66 | Generic target MLP head | target_macro_item_mae | 0.030 [-0.042, 0.113] | 0.17 | 30 |
| 66 | Generic target MLP head | target_total_mae | 0.266 [-0.305, 0.825] | 0.20 | 30 |
| 66 | Shared ordinal head | target_binned_item_calibration_mae | 0.056 [-0.033, 0.185] | 0.13 | 30 |
| 66 | Shared ordinal head | target_macro_item_mae | 0.036 [-0.030, 0.110] | 0.17 | 30 |
| 66 | Shared ordinal head | target_total_mae | 0.297 [-0.233, 0.888] | 0.20 | 30 |
| 66 | Target-only ordinal | target_binned_item_calibration_mae | 0.071 [0.004, 0.129] | 0.03 | 30 |
| 66 | Target-only ordinal | target_macro_item_mae | 0.015 [-0.014, 0.047] | 0.17 | 30 |
| 66 | Target-only ordinal | target_total_mae | 0.226 [-0.002, 0.506] | 0.03 | 30 |

**E-DAIC -> CMDC.**

| k | method | metric | delta method - target-only | split fraction | splits |
| ---: | --- | --- | ---: | ---: | ---: |
| 24 | Source+target direct multitask | target_binned_item_calibration_mae | -0.001 [-0.071, 0.055] | 0.43 | 30 |
| 24 | Source+target direct multitask | target_macro_item_mae | 0.015 [-0.031, 0.059] | 0.23 | 30 |
| 24 | Source+target direct multitask | target_total_mae | -0.031 [-0.606, 0.418] | 0.57 | 30 |
| 24 | Source warm-start target fine-tune | target_binned_item_calibration_mae | -0.008 [-0.086, 0.050] | 0.53 | 30 |
| 24 | Source warm-start target fine-tune | target_macro_item_mae | 0.012 [-0.032, 0.054] | 0.37 | 30 |
| 24 | Source warm-start target fine-tune | target_total_mae | -0.045 [-0.531, 0.376] | 0.53 | 30 |
| 24 | Measurement-aware ordinal | target_binned_item_calibration_mae | 0.019 [-0.079, 0.086] | 0.30 | 30 |
| 24 | Measurement-aware ordinal | target_macro_item_mae | 0.028 [-0.026, 0.106] | 0.20 | 30 |
| 24 | Measurement-aware ordinal | target_total_mae | 0.072 [-0.399, 0.597] | 0.37 | 30 |
| 24 | Generic target MLP head | target_binned_item_calibration_mae | -0.031 [-0.108, 0.033] | 0.83 | 30 |
| 24 | Generic target MLP head | target_macro_item_mae | 0.009 [-0.047, 0.064] | 0.33 | 30 |
| 24 | Generic target MLP head | target_total_mae | -0.026 [-0.565, 0.516] | 0.53 | 30 |
| 24 | Shared ordinal head | target_binned_item_calibration_mae | 0.021 [-0.080, 0.085] | 0.30 | 30 |
| 24 | Shared ordinal head | target_macro_item_mae | 0.028 [-0.026, 0.105] | 0.20 | 30 |
| 24 | Shared ordinal head | target_total_mae | 0.068 [-0.397, 0.590] | 0.37 | 30 |
| 24 | Target-only ordinal | target_binned_item_calibration_mae | 0.041 [-0.038, 0.101] | 0.13 | 30 |
| 24 | Target-only ordinal | target_macro_item_mae | 0.015 [-0.014, 0.047] | 0.23 | 30 |
| 24 | Target-only ordinal | target_total_mae | 0.146 [-0.117, 0.458] | 0.27 | 30 |

## Measurement-Aware Pairwise Deltas

Positive deltas mean the measurement-aware ordinal model has lower error than the comparison method.

**CMDC -> E-DAIC.**

| k | method | metric | delta method - measurement-aware | split fraction | splits |
| ---: | --- | --- | ---: | ---: | ---: |
| 66 | Source+target direct multitask | target_binned_item_calibration_mae | -0.003 [-0.099, 0.059] | 0.53 | 30 |
| 66 | Source+target direct multitask | target_macro_item_mae | 0.017 [-0.050, 0.071] | 0.77 | 30 |
| 66 | Source+target direct multitask | target_total_mae | 0.122 [-0.424, 0.659] | 0.67 | 30 |
| 66 | Source warm-start target fine-tune | target_binned_item_calibration_mae | -0.042 [-0.139, 0.058] | 0.27 | 30 |
| 66 | Source warm-start target fine-tune | target_macro_item_mae | -0.011 [-0.097, 0.042] | 0.53 | 30 |
| 66 | Source warm-start target fine-tune | target_total_mae | -0.112 [-0.697, 0.370] | 0.37 | 30 |
| 66 | Generic target MLP head | target_binned_item_calibration_mae | -0.029 [-0.126, 0.088] | 0.27 | 30 |
| 66 | Generic target MLP head | target_macro_item_mae | -0.003 [-0.060, 0.063] | 0.43 | 30 |
| 66 | Generic target MLP head | target_total_mae | -0.023 [-0.449, 0.518] | 0.47 | 30 |
| 66 | Shared ordinal head | target_binned_item_calibration_mae | -0.001 [-0.029, 0.027] | 0.47 | 30 |
| 66 | Shared ordinal head | target_macro_item_mae | 0.002 [-0.008, 0.018] | 0.57 | 30 |
| 66 | Shared ordinal head | target_total_mae | 0.008 [-0.108, 0.114] | 0.53 | 30 |
| 66 | Target-only ordinal | target_binned_item_calibration_mae | 0.013 [-0.096, 0.119] | 0.60 | 30 |
| 66 | Target-only ordinal | target_macro_item_mae | -0.018 [-0.076, 0.046] | 0.33 | 30 |
| 66 | Target-only ordinal | target_total_mae | -0.062 [-0.680, 0.502] | 0.47 | 30 |

**E-DAIC -> CMDC.**

| k | method | metric | delta method - measurement-aware | split fraction | splits |
| ---: | --- | --- | ---: | ---: | ---: |
| 24 | Source+target direct multitask | target_binned_item_calibration_mae | -0.020 [-0.073, 0.061] | 0.23 | 30 |
| 24 | Source+target direct multitask | target_macro_item_mae | -0.013 [-0.053, 0.024] | 0.27 | 30 |
| 24 | Source+target direct multitask | target_total_mae | -0.103 [-0.405, 0.165] | 0.33 | 30 |
| 24 | Source warm-start target fine-tune | target_binned_item_calibration_mae | -0.028 [-0.080, 0.037] | 0.27 | 30 |
| 24 | Source warm-start target fine-tune | target_macro_item_mae | -0.016 [-0.048, 0.019] | 0.17 | 30 |
| 24 | Source warm-start target fine-tune | target_total_mae | -0.118 [-0.340, 0.111] | 0.17 | 30 |
| 24 | Generic target MLP head | target_binned_item_calibration_mae | -0.050 [-0.142, 0.042] | 0.13 | 30 |
| 24 | Generic target MLP head | target_macro_item_mae | -0.020 [-0.085, 0.029] | 0.30 | 30 |
| 24 | Generic target MLP head | target_total_mae | -0.098 [-0.528, 0.362] | 0.23 | 30 |
| 24 | Shared ordinal head | target_binned_item_calibration_mae | 0.002 [-0.002, 0.017] | 0.37 | 30 |
| 24 | Shared ordinal head | target_macro_item_mae | -0.000 [-0.002, 0.001] | 0.33 | 30 |
| 24 | Shared ordinal head | target_total_mae | -0.004 [-0.016, 0.014] | 0.23 | 30 |
| 24 | Target-only ordinal | target_binned_item_calibration_mae | 0.022 [-0.077, 0.120] | 0.67 | 30 |
| 24 | Target-only ordinal | target_macro_item_mae | -0.014 [-0.070, 0.035] | 0.27 | 30 |
| 24 | Target-only ordinal | target_total_mae | 0.073 [-0.467, 0.470] | 0.60 | 30 |

## Calibration Metrics

CITL is observed shared-PHQ total minus predicted shared-PHQ total; ideal CITL is 0 and ideal slope is 1.

**CMDC -> E-DAIC.**

| k | method | CITL | abs CITL | slope | abs slope error | binned item calibration MAE |
| ---: | --- | ---: | ---: | ---: | ---: | ---: |
| 66 | Target-only direct MLP | 1.266 [0.202, 2.389] | 1.266 [0.202, 2.389] | 0.230 [0.081, 0.390] | 0.770 [0.610, 0.919] | 0.460 [0.362, 0.541] |
| 66 | Source+target direct multitask | 0.438 [-0.831, 1.608] | 0.587 [0.051, 1.608] | 0.181 [0.026, 0.316] | 0.819 [0.684, 0.974] | 0.514 [0.413, 0.607] |
| 66 | Shared ordinal head | 1.032 [-0.048, 1.970] | 1.063 [0.179, 1.970] | 0.211 [0.073, 0.373] | 0.789 [0.627, 0.927] | 0.516 [0.403, 0.627] |
| 66 | Measurement-aware ordinal | 1.051 [-0.106, 2.119] | 1.080 [0.217, 2.119] | 0.213 [0.077, 0.370] | 0.787 [0.630, 0.923] | 0.517 [0.398, 0.634] |

**E-DAIC -> CMDC.**

| k | method | CITL | abs CITL | slope | abs slope error | binned item calibration MAE |
| ---: | --- | ---: | ---: | ---: | ---: | ---: |
| 24 | Target-only direct MLP | 1.330 [-1.005, 3.040] | 1.560 [0.311, 3.040] | 0.896 [0.615, 1.172] | 0.149 [0.003, 0.385] | 0.423 [0.329, 0.548] |
| 24 | Source+target direct multitask | 0.943 [-1.336, 2.837] | 1.270 [0.105, 2.837] | 0.907 [0.642, 1.232] | 0.151 [0.017, 0.358] | 0.422 [0.295, 0.535] |
| 24 | Shared ordinal head | 1.189 [-1.015, 2.905] | 1.393 [0.149, 2.905] | 0.842 [0.578, 1.047] | 0.167 [0.019, 0.422] | 0.444 [0.318, 0.570] |
| 24 | Measurement-aware ordinal | 1.193 [-1.006, 2.909] | 1.395 [0.144, 2.909] | 0.841 [0.574, 1.047] | 0.168 [0.020, 0.426] | 0.442 [0.318, 0.571] |

## Interpretation Handle

Across repeated label-budget splits, source-plus-target calibrated rows beat the target-only direct MLP on mean macro item MAE in 0/10 method-budget-direction cells. The measurement-aware ordinal row beats its matched alternatives on mean macro item MAE in 2/10 cells. Use these counts as reviewer-facing uncertainty evidence, not as a universal architecture superiority claim.
