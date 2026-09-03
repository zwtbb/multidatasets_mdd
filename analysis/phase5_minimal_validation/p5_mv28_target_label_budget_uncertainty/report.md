# P5 MV28 Target-Label Budget And Uncertainty

Generated: `2026-09-03T02:19:36+00:00`

## Scope

MV28 tests whether source-plus-target calibrated adaptation still improves over target-only training when the labeled target budget is matched. It also replaces five-seed superiority language with repeated subject-level calibration/evaluation splits and participant-bootstrap paired uncertainty.

## Design

- Transfer directions: `edaic_to_cmdc_phq_shared;cmdc_to_edaic_phq_shared`.
- Target budgets: `k4;k8;k12;k16;k24`.
- Repeated splits per direction-budget: `30`.
- Participant bootstrap draws per split: `200`.
- Methods: `target_only_direct_mlp;target_only_ordinal;direct_target_finetune;direct_multitask_shared_head;shared_head_joint_adaptation;generic_target_mlp_head;full_without_mmd`.

## Label-Budget Curve

**CMDC -> E-DAIC.**

| k | eval n | method | regime | macro item MAE | total MAE | binned item calibration MAE | abs CITL | abs slope error |
| ---: | ---: | --- | --- | ---: | ---: | ---: | ---: | ---: |
| 4 | 215 | Target-only direct MLP | target_only | 0.801 [0.759, 0.872] | 5.157 [4.888, 5.727] | 0.479 [0.301, 0.663] | 2.712 [0.855, 4.930] | 0.768 [0.416, 1.170] |
| 4 | 215 | Target-only ordinal | target_only | 0.819 [0.777, 0.897] | 5.378 [4.846, 6.118] | 0.590 [0.381, 0.782] | 3.411 [1.280, 5.733] | 0.785 [0.497, 1.159] |
| 4 | 215 | Source warm-start target fine-tune | source_plus_target_calibrated | 0.826 [0.779, 0.919] | 5.340 [4.998, 5.970] | 0.531 [0.384, 0.700] | 2.572 [0.169, 5.057] | 0.769 [0.521, 1.037] |
| 4 | 215 | Source+target direct multitask | source_plus_target_calibrated | 0.839 [0.791, 0.931] | 5.502 [5.187, 5.948] | 0.516 [0.376, 0.647] | 2.313 [0.217, 4.193] | 0.836 [0.722, 1.006] |
| 4 | 215 | Shared ordinal head | source_plus_target_calibrated | 0.877 [0.804, 0.998] | 5.688 [5.246, 6.118] | 0.568 [0.407, 0.693] | 2.045 [0.413, 3.924] | 0.867 [0.756, 0.974] |
| 4 | 215 | Generic target MLP head | source_plus_target_calibrated | 0.818 [0.778, 0.876] | 5.362 [4.949, 6.099] | 0.512 [0.345, 0.703] | 2.636 [0.125, 5.500] | 0.769 [0.439, 0.920] |
| 4 | 215 | Measurement-aware ordinal | source_plus_target_calibrated | 0.883 [0.810, 1.001] | 5.691 [5.233, 6.125] | 0.568 [0.376, 0.686] | 1.882 [0.256, 3.503] | 0.867 [0.754, 0.977] |
| 8 | 211 | Target-only direct MLP | target_only | 0.810 [0.748, 0.882] | 5.169 [4.866, 5.560] | 0.430 [0.294, 0.531] | 2.080 [0.714, 3.905] | 0.851 [0.429, 1.259] |
| 8 | 211 | Target-only ordinal | target_only | 0.840 [0.762, 0.946] | 5.467 [4.991, 5.931] | 0.551 [0.402, 0.648] | 2.762 [1.096, 4.753] | 0.884 [0.473, 1.218] |
| 8 | 211 | Source warm-start target fine-tune | source_plus_target_calibrated | 0.882 [0.811, 1.041] | 5.722 [5.136, 6.581] | 0.542 [0.389, 0.701] | 1.712 [0.432, 3.845] | 0.875 [0.752, 1.102] |
| 8 | 211 | Source+target direct multitask | source_plus_target_calibrated | 0.896 [0.814, 1.078] | 5.892 [5.387, 6.745] | 0.554 [0.422, 0.733] | 1.653 [0.236, 3.822] | 0.891 [0.799, 1.007] |
| 8 | 211 | Shared ordinal head | source_plus_target_calibrated | 0.934 [0.837, 1.119] | 6.113 [5.459, 7.068] | 0.607 [0.453, 0.790] | 1.274 [0.044, 3.346] | 0.909 [0.781, 1.024] |
| 8 | 211 | Generic target MLP head | source_plus_target_calibrated | 0.844 [0.793, 0.971] | 5.500 [4.950, 6.160] | 0.492 [0.339, 0.639] | 1.655 [0.127, 3.794] | 0.848 [0.705, 1.037] |
| 8 | 211 | Measurement-aware ordinal | source_plus_target_calibrated | 0.933 [0.846, 1.092] | 6.100 [5.472, 7.072] | 0.599 [0.432, 0.763] | 1.169 [0.113, 3.020] | 0.907 [0.782, 1.034] |
| 12 | 207 | Target-only direct MLP | target_only | 0.833 [0.770, 0.911] | 5.294 [4.801, 5.804] | 0.394 [0.260, 0.497] | 0.947 [0.039, 2.711] | 0.857 [0.552, 1.144] |
| 12 | 207 | Target-only ordinal | target_only | 0.873 [0.790, 0.957] | 5.625 [5.014, 6.233] | 0.522 [0.399, 0.626] | 1.306 [0.126, 3.459] | 0.906 [0.658, 1.167] |
| 12 | 207 | Source warm-start target fine-tune | source_plus_target_calibrated | 0.927 [0.832, 1.063] | 6.073 [5.178, 7.217] | 0.578 [0.381, 0.771] | 1.137 [0.041, 3.492] | 0.883 [0.722, 1.004] |
| 12 | 207 | Source+target direct multitask | source_plus_target_calibrated | 0.936 [0.845, 1.044] | 6.191 [5.584, 6.908] | 0.590 [0.471, 0.688] | 1.015 [0.027, 2.696] | 0.902 [0.830, 0.979] |
| 12 | 207 | Shared ordinal head | source_plus_target_calibrated | 0.966 [0.860, 1.087] | 6.391 [5.724, 7.138] | 0.627 [0.464, 0.755] | 0.842 [0.022, 2.704] | 0.921 [0.817, 1.010] |
| 12 | 207 | Generic target MLP head | source_plus_target_calibrated | 0.883 [0.814, 0.971] | 5.705 [5.227, 6.286] | 0.491 [0.323, 0.624] | 0.895 [0.055, 2.637] | 0.886 [0.736, 1.014] |
| 12 | 207 | Measurement-aware ordinal | source_plus_target_calibrated | 0.967 [0.870, 1.098] | 6.383 [5.716, 7.136] | 0.624 [0.469, 0.754] | 0.843 [0.017, 3.053] | 0.920 [0.814, 1.010] |
| 16 | 203 | Target-only direct MLP | target_only | 0.811 [0.758, 0.864] | 5.258 [4.814, 5.729] | 0.396 [0.211, 0.593] | 1.662 [0.021, 3.845] | 0.832 [0.516, 1.065] |
| 16 | 203 | Target-only ordinal | target_only | 0.840 [0.771, 0.908] | 5.622 [4.995, 6.252] | 0.532 [0.381, 0.690] | 2.546 [0.665, 4.713] | 0.869 [0.606, 1.082] |
| 16 | 203 | Source warm-start target fine-tune | source_plus_target_calibrated | 0.890 [0.806, 1.027] | 5.925 [5.322, 6.709] | 0.550 [0.348, 0.708] | 1.521 [0.095, 3.580] | 0.886 [0.745, 1.051] |
| 16 | 203 | Source+target direct multitask | source_plus_target_calibrated | 0.915 [0.829, 1.038] | 6.111 [5.605, 6.800] | 0.573 [0.477, 0.684] | 1.179 [0.114, 2.700] | 0.900 [0.845, 0.967] |
| 16 | 203 | Shared ordinal head | source_plus_target_calibrated | 0.928 [0.830, 1.037] | 6.181 [5.553, 6.927] | 0.600 [0.462, 0.732] | 1.271 [0.129, 2.839] | 0.906 [0.810, 0.983] |
| 16 | 203 | Generic target MLP head | source_plus_target_calibrated | 0.854 [0.789, 0.929] | 5.623 [5.254, 6.065] | 0.484 [0.362, 0.650] | 1.427 [0.080, 3.126] | 0.877 [0.748, 1.006] |
| 16 | 203 | Measurement-aware ordinal | source_plus_target_calibrated | 0.925 [0.838, 1.019] | 6.153 [5.481, 6.791] | 0.591 [0.463, 0.729] | 1.218 [0.188, 2.635] | 0.905 [0.798, 0.986] |
| 24 | 195 | Target-only direct MLP | target_only | 0.814 [0.769, 0.865] | 5.230 [4.844, 5.820] | 0.387 [0.270, 0.509] | 1.455 [0.216, 3.133] | 0.796 [0.625, 1.025] |
| 24 | 195 | Target-only ordinal | target_only | 0.836 [0.783, 0.912] | 5.542 [5.138, 6.253] | 0.506 [0.401, 0.633] | 2.332 [0.540, 3.983] | 0.839 [0.654, 1.063] |
| 24 | 195 | Source warm-start target fine-tune | source_plus_target_calibrated | 0.882 [0.799, 1.018] | 5.811 [5.091, 6.725] | 0.519 [0.344, 0.644] | 1.274 [0.168, 2.951] | 0.864 [0.690, 1.023] |
| 24 | 195 | Source+target direct multitask | source_plus_target_calibrated | 0.908 [0.821, 1.014] | 6.022 [5.338, 6.735] | 0.546 [0.411, 0.658] | 1.070 [0.210, 2.443] | 0.869 [0.767, 0.956] |
| 24 | 195 | Shared ordinal head | source_plus_target_calibrated | 0.918 [0.816, 1.054] | 6.089 [5.352, 7.175] | 0.578 [0.417, 0.765] | 1.354 [0.118, 3.586] | 0.875 [0.731, 0.973] |
| 24 | 195 | Generic target MLP head | source_plus_target_calibrated | 0.863 [0.796, 0.951] | 5.651 [5.175, 6.288] | 0.472 [0.363, 0.578] | 1.015 [0.127, 2.379] | 0.867 [0.712, 1.140] |
| 24 | 195 | Measurement-aware ordinal | source_plus_target_calibrated | 0.917 [0.816, 1.051] | 6.069 [5.307, 7.137] | 0.571 [0.428, 0.759] | 1.275 [0.069, 3.406] | 0.872 [0.734, 0.960] |

**E-DAIC -> CMDC.**

| k | eval n | method | regime | macro item MAE | total MAE | binned item calibration MAE | abs CITL | abs slope error |
| ---: | ---: | --- | --- | ---: | ---: | ---: | ---: | ---: |
| 4 | 40 | Target-only direct MLP | target_only | 0.761 [0.617, 1.054] | 4.462 [2.937, 6.892] | 0.526 [0.367, 0.727] | 2.009 [0.040, 4.980] | 0.206 [0.020, 0.550] |
| 4 | 40 | Target-only ordinal | target_only | 0.784 [0.650, 1.056] | 4.491 [3.010, 6.637] | 0.606 [0.453, 0.832] | 2.162 [0.053, 5.071] | 0.200 [0.004, 0.530] |
| 4 | 40 | Source warm-start target fine-tune | source_plus_target_calibrated | 0.783 [0.655, 1.097] | 4.669 [3.584, 7.438] | 0.507 [0.357, 0.785] | 1.901 [0.120, 5.339] | 0.188 [0.007, 0.506] |
| 4 | 40 | Source+target direct multitask | source_plus_target_calibrated | 0.784 [0.655, 1.105] | 4.676 [3.540, 7.424] | 0.508 [0.349, 0.801] | 1.883 [0.203, 5.313] | 0.193 [0.017, 0.517] |
| 4 | 40 | Shared ordinal head | source_plus_target_calibrated | 0.806 [0.671, 1.043] | 4.651 [3.813, 6.810] | 0.562 [0.399, 0.758] | 1.488 [0.023, 4.229] | 0.203 [0.008, 0.481] |
| 4 | 40 | Generic target MLP head | source_plus_target_calibrated | 0.775 [0.620, 1.176] | 4.758 [3.593, 8.026] | 0.447 [0.318, 0.822] | 1.861 [0.266, 5.989] | 0.201 [0.008, 0.629] |
| 4 | 40 | Measurement-aware ordinal | source_plus_target_calibrated | 0.809 [0.675, 1.048] | 4.669 [3.821, 6.824] | 0.571 [0.412, 0.764] | 1.495 [0.056, 4.254] | 0.205 [0.007, 0.480] |
| 8 | 36 | Target-only direct MLP | target_only | 0.663 [0.571, 0.775] | 3.769 [2.871, 5.022] | 0.407 [0.314, 0.521] | 1.169 [0.086, 3.212] | 0.173 [0.009, 0.373] |
| 8 | 36 | Target-only ordinal | target_only | 0.682 [0.573, 0.824] | 3.877 [2.918, 5.224] | 0.473 [0.364, 0.611] | 1.319 [0.170, 3.903] | 0.209 [0.032, 0.420] |
| 8 | 36 | Source warm-start target fine-tune | source_plus_target_calibrated | 0.680 [0.582, 0.804] | 3.851 [3.157, 4.886] | 0.406 [0.304, 0.500] | 1.113 [0.207, 2.454] | 0.177 [0.039, 0.365] |
| 8 | 36 | Source+target direct multitask | source_plus_target_calibrated | 0.681 [0.592, 0.805] | 3.830 [3.047, 4.903] | 0.402 [0.311, 0.515] | 1.098 [0.107, 2.513] | 0.177 [0.044, 0.381] |
| 8 | 36 | Shared ordinal head | source_plus_target_calibrated | 0.706 [0.588, 0.826] | 3.918 [3.030, 4.975] | 0.438 [0.292, 0.557] | 1.069 [0.029, 2.186] | 0.186 [0.005, 0.397] |
| 8 | 36 | Generic target MLP head | source_plus_target_calibrated | 0.677 [0.574, 0.796] | 3.902 [3.142, 4.869] | 0.366 [0.266, 0.510] | 1.114 [0.089, 2.592] | 0.178 [0.032, 0.364] |
| 8 | 36 | Measurement-aware ordinal | source_plus_target_calibrated | 0.707 [0.588, 0.827] | 3.922 [3.030, 4.996] | 0.440 [0.294, 0.562] | 1.075 [0.027, 2.198] | 0.186 [0.008, 0.399] |
| 12 | 32 | Target-only direct MLP | target_only | 0.640 [0.551, 0.776] | 3.604 [2.827, 4.950] | 0.396 [0.311, 0.531] | 1.252 [0.050, 2.961] | 0.178 [0.009, 0.368] |
| 12 | 32 | Target-only ordinal | target_only | 0.658 [0.560, 0.803] | 3.773 [2.971, 5.054] | 0.454 [0.332, 0.590] | 1.420 [0.088, 3.081] | 0.214 [0.013, 0.416] |
| 12 | 32 | Source warm-start target fine-tune | source_plus_target_calibrated | 0.659 [0.582, 0.791] | 3.718 [2.954, 4.993] | 0.390 [0.294, 0.531] | 1.148 [0.099, 2.735] | 0.190 [0.026, 0.359] |
| 12 | 32 | Source+target direct multitask | source_plus_target_calibrated | 0.657 [0.570, 0.785] | 3.682 [2.849, 4.946] | 0.384 [0.272, 0.539] | 1.180 [0.182, 2.788] | 0.180 [0.018, 0.346] |
| 12 | 32 | Shared ordinal head | source_plus_target_calibrated | 0.677 [0.589, 0.817] | 3.766 [2.905, 5.002] | 0.429 [0.324, 0.565] | 1.252 [0.104, 2.923] | 0.197 [0.027, 0.358] |
| 12 | 32 | Generic target MLP head | source_plus_target_calibrated | 0.656 [0.578, 0.789] | 3.711 [2.874, 4.959] | 0.356 [0.282, 0.481] | 1.138 [0.116, 2.418] | 0.180 [0.044, 0.348] |
| 12 | 32 | Measurement-aware ordinal | source_plus_target_calibrated | 0.677 [0.589, 0.817] | 3.768 [2.908, 5.014] | 0.429 [0.324, 0.566] | 1.255 [0.078, 2.927] | 0.197 [0.026, 0.358] |
| 16 | 28 | Target-only direct MLP | target_only | 0.648 [0.562, 0.781] | 3.777 [2.947, 5.079] | 0.403 [0.292, 0.547] | 1.143 [0.148, 2.919] | 0.223 [0.006, 0.424] |
| 16 | 28 | Target-only ordinal | target_only | 0.663 [0.571, 0.814] | 3.916 [2.887, 5.323] | 0.450 [0.337, 0.611] | 1.186 [0.188, 3.020] | 0.268 [0.037, 0.470] |
| 16 | 28 | Source warm-start target fine-tune | source_plus_target_calibrated | 0.668 [0.570, 0.786] | 3.810 [2.970, 4.998] | 0.399 [0.263, 0.553] | 1.008 [0.082, 2.666] | 0.211 [0.013, 0.372] |
| 16 | 28 | Source+target direct multitask | source_plus_target_calibrated | 0.669 [0.573, 0.790] | 3.800 [2.853, 5.006] | 0.400 [0.267, 0.557] | 1.004 [0.058, 2.697] | 0.207 [0.039, 0.374] |
| 16 | 28 | Shared ordinal head | source_plus_target_calibrated | 0.687 [0.586, 0.833] | 3.906 [2.992, 5.326] | 0.448 [0.334, 0.588] | 1.040 [0.038, 2.920] | 0.238 [0.039, 0.422] |
| 16 | 28 | Generic target MLP head | source_plus_target_calibrated | 0.665 [0.561, 0.801] | 3.808 [2.670, 5.114] | 0.365 [0.232, 0.503] | 0.997 [0.005, 2.404] | 0.198 [0.038, 0.362] |
| 16 | 28 | Measurement-aware ordinal | source_plus_target_calibrated | 0.687 [0.587, 0.833] | 3.907 [2.995, 5.330] | 0.447 [0.334, 0.582] | 1.042 [0.043, 2.914] | 0.238 [0.040, 0.423] |
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
| 4 | Source+target direct multitask | target_binned_item_calibration_mae | 0.037 [-0.116, 0.154] | 0.33 | 30 |
| 4 | Source+target direct multitask | target_macro_item_mae | 0.038 [-0.011, 0.117] | 0.13 | 30 |
| 4 | Source+target direct multitask | target_total_mae | 0.344 [-0.140, 0.796] | 0.17 | 30 |
| 4 | Source warm-start target fine-tune | target_binned_item_calibration_mae | 0.052 [-0.033, 0.180] | 0.23 | 30 |
| 4 | Source warm-start target fine-tune | target_macro_item_mae | 0.025 [-0.014, 0.113] | 0.23 | 30 |
| 4 | Source warm-start target fine-tune | target_total_mae | 0.183 [-0.286, 0.551] | 0.23 | 30 |
| 4 | Measurement-aware ordinal | target_binned_item_calibration_mae | 0.089 [-0.113, 0.275] | 0.20 | 30 |
| 4 | Measurement-aware ordinal | target_macro_item_mae | 0.081 [0.012, 0.200] | 0.00 | 30 |
| 4 | Measurement-aware ordinal | target_total_mae | 0.533 [-0.229, 1.064] | 0.10 | 30 |
| 4 | Generic target MLP head | target_binned_item_calibration_mae | 0.034 [-0.151, 0.133] | 0.27 | 30 |
| 4 | Generic target MLP head | target_macro_item_mae | 0.017 [-0.041, 0.057] | 0.23 | 30 |
| 4 | Generic target MLP head | target_total_mae | 0.205 [-0.407, 0.698] | 0.20 | 30 |
| 4 | Shared ordinal head | target_binned_item_calibration_mae | 0.090 [-0.117, 0.283] | 0.20 | 30 |
| 4 | Shared ordinal head | target_macro_item_mae | 0.076 [0.016, 0.195] | 0.00 | 30 |
| 4 | Shared ordinal head | target_total_mae | 0.531 [-0.197, 1.001] | 0.10 | 30 |
| 4 | Target-only ordinal | target_binned_item_calibration_mae | 0.111 [0.034, 0.253] | 0.00 | 30 |
| 4 | Target-only ordinal | target_macro_item_mae | 0.018 [-0.005, 0.060] | 0.03 | 30 |
| 4 | Target-only ordinal | target_total_mae | 0.220 [-0.047, 0.709] | 0.10 | 30 |
| 8 | Source+target direct multitask | target_binned_item_calibration_mae | 0.124 [0.035, 0.290] | 0.00 | 30 |
| 8 | Source+target direct multitask | target_macro_item_mae | 0.086 [-0.013, 0.212] | 0.07 | 30 |
| 8 | Source+target direct multitask | target_total_mae | 0.723 [0.204, 1.603] | 0.00 | 30 |
| 8 | Source warm-start target fine-tune | target_binned_item_calibration_mae | 0.113 [0.013, 0.212] | 0.03 | 30 |
| 8 | Source warm-start target fine-tune | target_macro_item_mae | 0.072 [-0.012, 0.190] | 0.10 | 30 |
| 8 | Source warm-start target fine-tune | target_total_mae | 0.553 [0.016, 1.388] | 0.03 | 30 |
| 8 | Measurement-aware ordinal | target_binned_item_calibration_mae | 0.169 [0.038, 0.327] | 0.00 | 30 |
| 8 | Measurement-aware ordinal | target_macro_item_mae | 0.123 [0.040, 0.255] | 0.00 | 30 |
| 8 | Measurement-aware ordinal | target_total_mae | 0.931 [0.392, 1.879] | 0.00 | 30 |
| 8 | Generic target MLP head | target_binned_item_calibration_mae | 0.062 [-0.031, 0.186] | 0.13 | 30 |
| 8 | Generic target MLP head | target_macro_item_mae | 0.034 [-0.026, 0.111] | 0.13 | 30 |
| 8 | Generic target MLP head | target_total_mae | 0.331 [-0.168, 0.934] | 0.10 | 30 |
| 8 | Shared ordinal head | target_binned_item_calibration_mae | 0.177 [0.057, 0.345] | 0.00 | 30 |
| 8 | Shared ordinal head | target_macro_item_mae | 0.124 [0.032, 0.255] | 0.00 | 30 |
| 8 | Shared ordinal head | target_total_mae | 0.943 [0.382, 1.927] | 0.00 | 30 |
| 8 | Target-only ordinal | target_binned_item_calibration_mae | 0.121 [0.079, 0.174] | 0.00 | 30 |
| 8 | Target-only ordinal | target_macro_item_mae | 0.030 [-0.005, 0.076] | 0.10 | 30 |
| 8 | Target-only ordinal | target_total_mae | 0.298 [0.064, 0.565] | 0.00 | 30 |
| 12 | Source+target direct multitask | target_binned_item_calibration_mae | 0.196 [0.059, 0.370] | 0.00 | 30 |
| 12 | Source+target direct multitask | target_macro_item_mae | 0.102 [-0.009, 0.225] | 0.07 | 30 |
| 12 | Source+target direct multitask | target_total_mae | 0.897 [0.304, 1.895] | 0.00 | 30 |
| 12 | Source warm-start target fine-tune | target_binned_item_calibration_mae | 0.184 [0.059, 0.441] | 0.00 | 30 |
| 12 | Source warm-start target fine-tune | target_macro_item_mae | 0.094 [-0.010, 0.242] | 0.07 | 30 |
| 12 | Source warm-start target fine-tune | target_total_mae | 0.779 [0.097, 2.205] | 0.03 | 30 |
| 12 | Measurement-aware ordinal | target_binned_item_calibration_mae | 0.230 [0.105, 0.394] | 0.00 | 30 |
| 12 | Measurement-aware ordinal | target_macro_item_mae | 0.133 [0.035, 0.249] | 0.00 | 30 |
| 12 | Measurement-aware ordinal | target_total_mae | 1.089 [0.261, 2.010] | 0.00 | 30 |
| 12 | Generic target MLP head | target_binned_item_calibration_mae | 0.097 [-0.072, 0.233] | 0.10 | 30 |
| 12 | Generic target MLP head | target_macro_item_mae | 0.050 [-0.016, 0.144] | 0.10 | 30 |
| 12 | Generic target MLP head | target_total_mae | 0.411 [-0.302, 1.250] | 0.10 | 30 |
| 12 | Shared ordinal head | target_binned_item_calibration_mae | 0.233 [0.115, 0.398] | 0.00 | 30 |
| 12 | Shared ordinal head | target_macro_item_mae | 0.133 [0.028, 0.239] | 0.00 | 30 |
| 12 | Shared ordinal head | target_total_mae | 1.098 [0.210, 2.032] | 0.00 | 30 |
| 12 | Target-only ordinal | target_binned_item_calibration_mae | 0.128 [0.070, 0.213] | 0.00 | 30 |
| 12 | Target-only ordinal | target_macro_item_mae | 0.040 [0.009, 0.075] | 0.00 | 30 |
| 12 | Target-only ordinal | target_total_mae | 0.331 [0.049, 0.578] | 0.03 | 30 |
| 16 | Source+target direct multitask | target_binned_item_calibration_mae | 0.176 [0.018, 0.306] | 0.03 | 30 |
| 16 | Source+target direct multitask | target_macro_item_mae | 0.104 [0.034, 0.187] | 0.00 | 30 |
| 16 | Source+target direct multitask | target_total_mae | 0.853 [0.120, 1.418] | 0.00 | 30 |
| 16 | Source warm-start target fine-tune | target_binned_item_calibration_mae | 0.154 [-0.020, 0.363] | 0.07 | 30 |
| 16 | Source warm-start target fine-tune | target_macro_item_mae | 0.079 [0.008, 0.181] | 0.00 | 30 |
| 16 | Source warm-start target fine-tune | target_total_mae | 0.668 [0.026, 1.381] | 0.00 | 30 |
| 16 | Measurement-aware ordinal | target_binned_item_calibration_mae | 0.194 [0.041, 0.346] | 0.00 | 30 |
| 16 | Measurement-aware ordinal | target_macro_item_mae | 0.114 [0.048, 0.200] | 0.00 | 30 |
| 16 | Measurement-aware ordinal | target_total_mae | 0.896 [0.287, 1.581] | 0.00 | 30 |
| 16 | Generic target MLP head | target_binned_item_calibration_mae | 0.087 [-0.050, 0.231] | 0.13 | 30 |
| 16 | Generic target MLP head | target_macro_item_mae | 0.043 [-0.012, 0.110] | 0.10 | 30 |
| 16 | Generic target MLP head | target_total_mae | 0.365 [-0.085, 0.768] | 0.07 | 30 |
| 16 | Shared ordinal head | target_binned_item_calibration_mae | 0.203 [0.048, 0.380] | 0.00 | 30 |
| 16 | Shared ordinal head | target_macro_item_mae | 0.117 [0.053, 0.210] | 0.00 | 30 |
| 16 | Shared ordinal head | target_total_mae | 0.923 [0.325, 1.687] | 0.00 | 30 |
| 16 | Target-only ordinal | target_binned_item_calibration_mae | 0.136 [0.064, 0.200] | 0.00 | 30 |
| 16 | Target-only ordinal | target_macro_item_mae | 0.029 [0.002, 0.066] | 0.00 | 30 |
| 16 | Target-only ordinal | target_total_mae | 0.364 [0.029, 0.607] | 0.03 | 30 |
| 24 | Source+target direct multitask | target_binned_item_calibration_mae | 0.158 [-0.011, 0.300] | 0.03 | 30 |
| 24 | Source+target direct multitask | target_macro_item_mae | 0.095 [-0.004, 0.175] | 0.10 | 30 |
| 24 | Source+target direct multitask | target_total_mae | 0.793 [-0.338, 1.573] | 0.07 | 30 |
| 24 | Source warm-start target fine-tune | target_binned_item_calibration_mae | 0.131 [-0.009, 0.318] | 0.03 | 30 |
| 24 | Source warm-start target fine-tune | target_macro_item_mae | 0.068 [0.000, 0.177] | 0.03 | 30 |
| 24 | Source warm-start target fine-tune | target_total_mae | 0.582 [-0.222, 1.553] | 0.13 | 30 |
| 24 | Measurement-aware ordinal | target_binned_item_calibration_mae | 0.183 [0.032, 0.408] | 0.00 | 30 |
| 24 | Measurement-aware ordinal | target_macro_item_mae | 0.103 [-0.001, 0.241] | 0.03 | 30 |
| 24 | Measurement-aware ordinal | target_total_mae | 0.839 [0.002, 1.903] | 0.03 | 30 |
| 24 | Generic target MLP head | target_binned_item_calibration_mae | 0.084 [-0.077, 0.243] | 0.17 | 30 |
| 24 | Generic target MLP head | target_macro_item_mae | 0.049 [-0.007, 0.124] | 0.07 | 30 |
| 24 | Generic target MLP head | target_total_mae | 0.422 [-0.228, 1.050] | 0.13 | 30 |
| 24 | Shared ordinal head | target_binned_item_calibration_mae | 0.191 [0.041, 0.413] | 0.00 | 30 |
| 24 | Shared ordinal head | target_macro_item_mae | 0.105 [0.003, 0.247] | 0.00 | 30 |
| 24 | Shared ordinal head | target_total_mae | 0.860 [0.053, 2.007] | 0.03 | 30 |
| 24 | Target-only ordinal | target_binned_item_calibration_mae | 0.119 [0.064, 0.180] | 0.00 | 30 |
| 24 | Target-only ordinal | target_macro_item_mae | 0.023 [-0.005, 0.053] | 0.07 | 30 |
| 24 | Target-only ordinal | target_total_mae | 0.312 [0.107, 0.537] | 0.00 | 30 |

**E-DAIC -> CMDC.**

| k | method | metric | delta method - target-only | split fraction | splits |
| ---: | --- | --- | ---: | ---: | ---: |
| 4 | Source+target direct multitask | target_binned_item_calibration_mae | -0.018 [-0.110, 0.112] | 0.63 | 30 |
| 4 | Source+target direct multitask | target_macro_item_mae | 0.023 [-0.026, 0.091] | 0.23 | 30 |
| 4 | Source+target direct multitask | target_total_mae | 0.214 [-0.324, 0.955] | 0.37 | 30 |
| 4 | Source warm-start target fine-tune | target_binned_item_calibration_mae | -0.019 [-0.126, 0.130] | 0.63 | 30 |
| 4 | Source warm-start target fine-tune | target_macro_item_mae | 0.021 [-0.020, 0.101] | 0.43 | 30 |
| 4 | Source warm-start target fine-tune | target_total_mae | 0.207 [-0.341, 1.070] | 0.27 | 30 |
| 4 | Measurement-aware ordinal | target_binned_item_calibration_mae | 0.045 [-0.113, 0.193] | 0.30 | 30 |
| 4 | Measurement-aware ordinal | target_macro_item_mae | 0.048 [-0.052, 0.142] | 0.13 | 30 |
| 4 | Measurement-aware ordinal | target_total_mae | 0.207 [-0.529, 1.241] | 0.33 | 30 |
| 4 | Generic target MLP head | target_binned_item_calibration_mae | -0.079 [-0.181, 0.096] | 0.87 | 30 |
| 4 | Generic target MLP head | target_macro_item_mae | 0.014 [-0.080, 0.128] | 0.40 | 30 |
| 4 | Generic target MLP head | target_total_mae | 0.296 [-0.561, 1.324] | 0.23 | 30 |
| 4 | Shared ordinal head | target_binned_item_calibration_mae | 0.036 [-0.138, 0.191] | 0.33 | 30 |
| 4 | Shared ordinal head | target_macro_item_mae | 0.044 [-0.056, 0.141] | 0.13 | 30 |
| 4 | Shared ordinal head | target_total_mae | 0.188 [-0.532, 1.250] | 0.33 | 30 |
| 4 | Target-only ordinal | target_binned_item_calibration_mae | 0.080 [0.028, 0.142] | 0.00 | 30 |
| 4 | Target-only ordinal | target_macro_item_mae | 0.023 [-0.031, 0.065] | 0.23 | 30 |
| 4 | Target-only ordinal | target_total_mae | 0.028 [-0.760, 0.551] | 0.40 | 30 |
| 8 | Source+target direct multitask | target_binned_item_calibration_mae | -0.005 [-0.077, 0.061] | 0.47 | 30 |
| 8 | Source+target direct multitask | target_macro_item_mae | 0.018 [-0.031, 0.061] | 0.20 | 30 |
| 8 | Source+target direct multitask | target_total_mae | 0.060 [-0.530, 0.555] | 0.47 | 30 |
| 8 | Source warm-start target fine-tune | target_binned_item_calibration_mae | -0.001 [-0.075, 0.089] | 0.57 | 30 |
| 8 | Source warm-start target fine-tune | target_macro_item_mae | 0.017 [-0.043, 0.076] | 0.27 | 30 |
| 8 | Source warm-start target fine-tune | target_total_mae | 0.081 [-0.616, 0.685] | 0.43 | 30 |
| 8 | Measurement-aware ordinal | target_binned_item_calibration_mae | 0.032 [-0.090, 0.109] | 0.23 | 30 |
| 8 | Measurement-aware ordinal | target_macro_item_mae | 0.044 [-0.025, 0.094] | 0.07 | 30 |
| 8 | Measurement-aware ordinal | target_total_mae | 0.153 [-0.678, 0.917] | 0.27 | 30 |
| 8 | Generic target MLP head | target_binned_item_calibration_mae | -0.041 [-0.133, 0.089] | 0.83 | 30 |
| 8 | Generic target MLP head | target_macro_item_mae | 0.014 [-0.048, 0.066] | 0.33 | 30 |
| 8 | Generic target MLP head | target_total_mae | 0.133 [-0.657, 0.697] | 0.30 | 30 |
| 8 | Shared ordinal head | target_binned_item_calibration_mae | 0.030 [-0.088, 0.106] | 0.23 | 30 |
| 8 | Shared ordinal head | target_macro_item_mae | 0.043 [-0.026, 0.094] | 0.07 | 30 |
| 8 | Shared ordinal head | target_total_mae | 0.149 [-0.680, 0.918] | 0.27 | 30 |
| 8 | Target-only ordinal | target_binned_item_calibration_mae | 0.066 [0.025, 0.129] | 0.00 | 30 |
| 8 | Target-only ordinal | target_macro_item_mae | 0.019 [-0.016, 0.049] | 0.07 | 30 |
| 8 | Target-only ordinal | target_total_mae | 0.108 [-0.119, 0.532] | 0.30 | 30 |
| 12 | Source+target direct multitask | target_binned_item_calibration_mae | -0.013 [-0.069, 0.053] | 0.63 | 30 |
| 12 | Source+target direct multitask | target_macro_item_mae | 0.017 [-0.017, 0.072] | 0.20 | 30 |
| 12 | Source+target direct multitask | target_total_mae | 0.078 [-0.354, 0.623] | 0.40 | 30 |
| 12 | Source warm-start target fine-tune | target_binned_item_calibration_mae | -0.006 [-0.064, 0.070] | 0.57 | 30 |
| 12 | Source warm-start target fine-tune | target_macro_item_mae | 0.019 [-0.016, 0.062] | 0.20 | 30 |
| 12 | Source warm-start target fine-tune | target_total_mae | 0.114 [-0.372, 0.659] | 0.37 | 30 |
| 12 | Measurement-aware ordinal | target_binned_item_calibration_mae | 0.033 [-0.040, 0.113] | 0.33 | 30 |
| 12 | Measurement-aware ordinal | target_macro_item_mae | 0.037 [0.001, 0.088] | 0.03 | 30 |
| 12 | Measurement-aware ordinal | target_total_mae | 0.164 [-0.296, 0.726] | 0.33 | 30 |
| 12 | Generic target MLP head | target_binned_item_calibration_mae | -0.040 [-0.121, 0.047] | 0.87 | 30 |
| 12 | Generic target MLP head | target_macro_item_mae | 0.016 [-0.021, 0.082] | 0.30 | 30 |
| 12 | Generic target MLP head | target_total_mae | 0.107 [-0.457, 0.755] | 0.47 | 30 |
| 12 | Shared ordinal head | target_binned_item_calibration_mae | 0.033 [-0.037, 0.113] | 0.33 | 30 |
| 12 | Shared ordinal head | target_macro_item_mae | 0.037 [0.001, 0.088] | 0.03 | 30 |
| 12 | Shared ordinal head | target_total_mae | 0.162 [-0.301, 0.729] | 0.37 | 30 |
| 12 | Target-only ordinal | target_binned_item_calibration_mae | 0.057 [0.016, 0.111] | 0.00 | 30 |
| 12 | Target-only ordinal | target_macro_item_mae | 0.018 [-0.008, 0.051] | 0.13 | 30 |
| 12 | Target-only ordinal | target_total_mae | 0.169 [-0.010, 0.459] | 0.07 | 30 |
| 16 | Source+target direct multitask | target_binned_item_calibration_mae | -0.003 [-0.066, 0.070] | 0.53 | 30 |
| 16 | Source+target direct multitask | target_macro_item_mae | 0.021 [-0.026, 0.067] | 0.13 | 30 |
| 16 | Source+target direct multitask | target_total_mae | 0.023 [-0.419, 0.581] | 0.53 | 30 |
| 16 | Source warm-start target fine-tune | target_binned_item_calibration_mae | -0.005 [-0.077, 0.087] | 0.60 | 30 |
| 16 | Source warm-start target fine-tune | target_macro_item_mae | 0.019 [-0.015, 0.067] | 0.20 | 30 |
| 16 | Source warm-start target fine-tune | target_total_mae | 0.033 [-0.420, 0.657] | 0.53 | 30 |
| 16 | Measurement-aware ordinal | target_binned_item_calibration_mae | 0.044 [-0.037, 0.124] | 0.17 | 30 |
| 16 | Measurement-aware ordinal | target_macro_item_mae | 0.038 [-0.001, 0.088] | 0.03 | 30 |
| 16 | Measurement-aware ordinal | target_total_mae | 0.130 [-0.217, 0.768] | 0.30 | 30 |
| 16 | Generic target MLP head | target_binned_item_calibration_mae | -0.038 [-0.115, 0.062] | 0.77 | 30 |
| 16 | Generic target MLP head | target_macro_item_mae | 0.017 [-0.029, 0.093] | 0.30 | 30 |
| 16 | Generic target MLP head | target_total_mae | 0.031 [-0.515, 0.832] | 0.57 | 30 |
| 16 | Shared ordinal head | target_binned_item_calibration_mae | 0.045 [-0.037, 0.128] | 0.17 | 30 |
| 16 | Shared ordinal head | target_macro_item_mae | 0.038 [-0.002, 0.088] | 0.03 | 30 |
| 16 | Shared ordinal head | target_total_mae | 0.129 [-0.223, 0.773] | 0.33 | 30 |
| 16 | Target-only ordinal | target_binned_item_calibration_mae | 0.047 [-0.004, 0.092] | 0.03 | 30 |
| 16 | Target-only ordinal | target_macro_item_mae | 0.015 [-0.005, 0.039] | 0.17 | 30 |
| 16 | Target-only ordinal | target_total_mae | 0.139 [-0.177, 0.455] | 0.17 | 30 |
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
| 4 | Source+target direct multitask | target_binned_item_calibration_mae | -0.052 [-0.155, 0.060] | 0.23 | 30 |
| 4 | Source+target direct multitask | target_macro_item_mae | -0.044 [-0.102, -0.003] | 0.03 | 30 |
| 4 | Source+target direct multitask | target_total_mae | -0.189 [-0.562, 0.137] | 0.17 | 30 |
| 4 | Source warm-start target fine-tune | target_binned_item_calibration_mae | -0.037 [-0.172, 0.086] | 0.33 | 30 |
| 4 | Source warm-start target fine-tune | target_macro_item_mae | -0.057 [-0.137, -0.001] | 0.03 | 30 |
| 4 | Source warm-start target fine-tune | target_total_mae | -0.351 [-0.885, 0.112] | 0.13 | 30 |
| 4 | Generic target MLP head | target_binned_item_calibration_mae | -0.056 [-0.186, 0.095] | 0.30 | 30 |
| 4 | Generic target MLP head | target_macro_item_mae | -0.065 [-0.144, 0.003] | 0.07 | 30 |
| 4 | Generic target MLP head | target_total_mae | -0.329 [-0.814, 0.188] | 0.07 | 30 |
| 4 | Shared ordinal head | target_binned_item_calibration_mae | 0.000 [-0.047, 0.048] | 0.47 | 30 |
| 4 | Shared ordinal head | target_macro_item_mae | -0.006 [-0.022, 0.011] | 0.33 | 30 |
| 4 | Shared ordinal head | target_total_mae | -0.003 [-0.111, 0.123] | 0.50 | 30 |
| 4 | Target-only ordinal | target_binned_item_calibration_mae | 0.021 [-0.191, 0.203] | 0.63 | 30 |
| 4 | Target-only ordinal | target_macro_item_mae | -0.064 [-0.186, 0.014] | 0.13 | 30 |
| 4 | Target-only ordinal | target_total_mae | -0.313 [-1.051, 0.492] | 0.27 | 30 |
| 8 | Source+target direct multitask | target_binned_item_calibration_mae | -0.045 [-0.142, 0.082] | 0.20 | 30 |
| 8 | Source+target direct multitask | target_macro_item_mae | -0.038 [-0.099, 0.039] | 0.10 | 30 |
| 8 | Source+target direct multitask | target_total_mae | -0.208 [-0.758, 0.313] | 0.20 | 30 |
| 8 | Source warm-start target fine-tune | target_binned_item_calibration_mae | -0.057 [-0.162, 0.030] | 0.23 | 30 |
| 8 | Source warm-start target fine-tune | target_macro_item_mae | -0.051 [-0.115, 0.035] | 0.10 | 30 |
| 8 | Source warm-start target fine-tune | target_total_mae | -0.378 [-0.944, 0.006] | 0.07 | 30 |
| 8 | Generic target MLP head | target_binned_item_calibration_mae | -0.107 [-0.261, -0.001] | 0.03 | 30 |
| 8 | Generic target MLP head | target_macro_item_mae | -0.089 [-0.186, -0.028] | 0.00 | 30 |
| 8 | Generic target MLP head | target_total_mae | -0.600 [-1.355, -0.112] | 0.03 | 30 |
| 8 | Shared ordinal head | target_binned_item_calibration_mae | 0.008 [-0.026, 0.046] | 0.60 | 30 |
| 8 | Shared ordinal head | target_macro_item_mae | 0.001 [-0.033, 0.029] | 0.47 | 30 |
| 8 | Shared ordinal head | target_total_mae | 0.012 [-0.151, 0.226] | 0.53 | 30 |
| 8 | Target-only ordinal | target_binned_item_calibration_mae | -0.048 [-0.190, 0.080] | 0.27 | 30 |
| 8 | Target-only ordinal | target_macro_item_mae | -0.093 [-0.212, 0.013] | 0.07 | 30 |
| 8 | Target-only ordinal | target_total_mae | -0.633 [-1.637, 0.020] | 0.03 | 30 |
| 12 | Source+target direct multitask | target_binned_item_calibration_mae | -0.033 [-0.126, 0.059] | 0.30 | 30 |
| 12 | Source+target direct multitask | target_macro_item_mae | -0.031 [-0.091, 0.025] | 0.27 | 30 |
| 12 | Source+target direct multitask | target_total_mae | -0.192 [-0.690, 0.346] | 0.30 | 30 |
| 12 | Source warm-start target fine-tune | target_binned_item_calibration_mae | -0.046 [-0.154, 0.071] | 0.23 | 30 |
| 12 | Source warm-start target fine-tune | target_macro_item_mae | -0.039 [-0.113, 0.048] | 0.17 | 30 |
| 12 | Source warm-start target fine-tune | target_total_mae | -0.310 [-0.844, 0.441] | 0.13 | 30 |
| 12 | Generic target MLP head | target_binned_item_calibration_mae | -0.133 [-0.250, -0.001] | 0.03 | 30 |
| 12 | Generic target MLP head | target_macro_item_mae | -0.083 [-0.149, -0.020] | 0.00 | 30 |
| 12 | Generic target MLP head | target_total_mae | -0.678 [-1.190, -0.157] | 0.00 | 30 |
| 12 | Shared ordinal head | target_binned_item_calibration_mae | 0.003 [-0.030, 0.038] | 0.57 | 30 |
| 12 | Shared ordinal head | target_macro_item_mae | -0.000 [-0.024, 0.023] | 0.53 | 30 |
| 12 | Shared ordinal head | target_total_mae | 0.008 [-0.202, 0.224] | 0.57 | 30 |
| 12 | Target-only ordinal | target_binned_item_calibration_mae | -0.101 [-0.202, 0.028] | 0.10 | 30 |
| 12 | Target-only ordinal | target_macro_item_mae | -0.093 [-0.192, -0.001] | 0.03 | 30 |
| 12 | Target-only ordinal | target_total_mae | -0.758 [-1.605, 0.011] | 0.03 | 30 |
| 16 | Source+target direct multitask | target_binned_item_calibration_mae | -0.018 [-0.125, 0.091] | 0.37 | 30 |
| 16 | Source+target direct multitask | target_macro_item_mae | -0.010 [-0.082, 0.069] | 0.40 | 30 |
| 16 | Source+target direct multitask | target_total_mae | -0.043 [-0.659, 0.514] | 0.43 | 30 |
| 16 | Source warm-start target fine-tune | target_binned_item_calibration_mae | -0.041 [-0.222, 0.106] | 0.33 | 30 |
| 16 | Source warm-start target fine-tune | target_macro_item_mae | -0.035 [-0.107, 0.036] | 0.17 | 30 |
| 16 | Source warm-start target fine-tune | target_total_mae | -0.228 [-0.946, 0.406] | 0.37 | 30 |
| 16 | Generic target MLP head | target_binned_item_calibration_mae | -0.107 [-0.228, -0.009] | 0.03 | 30 |
| 16 | Generic target MLP head | target_macro_item_mae | -0.071 [-0.133, 0.004] | 0.03 | 30 |
| 16 | Generic target MLP head | target_total_mae | -0.531 [-1.057, 0.004] | 0.03 | 30 |
| 16 | Shared ordinal head | target_binned_item_calibration_mae | 0.009 [-0.023, 0.042] | 0.67 | 30 |
| 16 | Shared ordinal head | target_macro_item_mae | 0.003 [-0.011, 0.022] | 0.60 | 30 |
| 16 | Shared ordinal head | target_total_mae | 0.028 [-0.107, 0.173] | 0.63 | 30 |
| 16 | Target-only ordinal | target_binned_item_calibration_mae | -0.059 [-0.223, 0.098] | 0.23 | 30 |
| 16 | Target-only ordinal | target_macro_item_mae | -0.085 [-0.166, -0.021] | 0.00 | 30 |
| 16 | Target-only ordinal | target_total_mae | -0.532 [-1.305, 0.177] | 0.17 | 30 |
| 24 | Source+target direct multitask | target_binned_item_calibration_mae | -0.025 [-0.125, 0.075] | 0.37 | 30 |
| 24 | Source+target direct multitask | target_macro_item_mae | -0.009 [-0.069, 0.049] | 0.40 | 30 |
| 24 | Source+target direct multitask | target_total_mae | -0.046 [-0.685, 0.485] | 0.50 | 30 |
| 24 | Source warm-start target fine-tune | target_binned_item_calibration_mae | -0.052 [-0.193, 0.067] | 0.27 | 30 |
| 24 | Source warm-start target fine-tune | target_macro_item_mae | -0.035 [-0.100, 0.042] | 0.23 | 30 |
| 24 | Source warm-start target fine-tune | target_total_mae | -0.258 [-0.844, 0.349] | 0.23 | 30 |
| 24 | Generic target MLP head | target_binned_item_calibration_mae | -0.099 [-0.255, 0.037] | 0.10 | 30 |
| 24 | Generic target MLP head | target_macro_item_mae | -0.054 [-0.133, 0.038] | 0.10 | 30 |
| 24 | Generic target MLP head | target_total_mae | -0.417 [-1.084, 0.198] | 0.10 | 30 |
| 24 | Shared ordinal head | target_binned_item_calibration_mae | 0.007 [-0.036, 0.052] | 0.73 | 30 |
| 24 | Shared ordinal head | target_macro_item_mae | 0.002 [-0.013, 0.016] | 0.50 | 30 |
| 24 | Shared ordinal head | target_total_mae | 0.020 [-0.116, 0.166] | 0.53 | 30 |
| 24 | Target-only ordinal | target_binned_item_calibration_mae | -0.064 [-0.266, 0.097] | 0.27 | 30 |
| 24 | Target-only ordinal | target_macro_item_mae | -0.080 [-0.191, 0.009] | 0.03 | 30 |
| 24 | Target-only ordinal | target_total_mae | -0.527 [-1.633, 0.375] | 0.23 | 30 |

**E-DAIC -> CMDC.**

| k | method | metric | delta method - measurement-aware | split fraction | splits |
| ---: | --- | --- | ---: | ---: | ---: |
| 4 | Source+target direct multitask | target_binned_item_calibration_mae | -0.063 [-0.171, 0.049] | 0.13 | 30 |
| 4 | Source+target direct multitask | target_macro_item_mae | -0.026 [-0.083, 0.046] | 0.23 | 30 |
| 4 | Source+target direct multitask | target_total_mae | 0.007 [-0.405, 0.534] | 0.40 | 30 |
| 4 | Source warm-start target fine-tune | target_binned_item_calibration_mae | -0.064 [-0.162, 0.055] | 0.10 | 30 |
| 4 | Source warm-start target fine-tune | target_macro_item_mae | -0.027 [-0.095, 0.048] | 0.20 | 30 |
| 4 | Source warm-start target fine-tune | target_total_mae | 0.001 [-0.411, 0.571] | 0.47 | 30 |
| 4 | Generic target MLP head | target_binned_item_calibration_mae | -0.124 [-0.271, 0.058] | 0.07 | 30 |
| 4 | Generic target MLP head | target_macro_item_mae | -0.034 [-0.133, 0.127] | 0.23 | 30 |
| 4 | Generic target MLP head | target_total_mae | 0.089 [-0.703, 1.475] | 0.50 | 30 |
| 4 | Shared ordinal head | target_binned_item_calibration_mae | -0.009 [-0.047, 0.006] | 0.13 | 30 |
| 4 | Shared ordinal head | target_macro_item_mae | -0.004 [-0.011, 0.002] | 0.10 | 30 |
| 4 | Shared ordinal head | target_total_mae | -0.018 [-0.099, 0.020] | 0.17 | 30 |
| 4 | Target-only ordinal | target_binned_item_calibration_mae | 0.035 [-0.087, 0.198] | 0.70 | 30 |
| 4 | Target-only ordinal | target_macro_item_mae | -0.025 [-0.123, 0.062] | 0.33 | 30 |
| 4 | Target-only ordinal | target_total_mae | -0.178 [-1.222, 0.935] | 0.40 | 30 |
| 8 | Source+target direct multitask | target_binned_item_calibration_mae | -0.037 [-0.128, 0.054] | 0.23 | 30 |
| 8 | Source+target direct multitask | target_macro_item_mae | -0.026 [-0.065, 0.011] | 0.17 | 30 |
| 8 | Source+target direct multitask | target_total_mae | -0.093 [-0.453, 0.162] | 0.33 | 30 |
| 8 | Source warm-start target fine-tune | target_binned_item_calibration_mae | -0.034 [-0.105, 0.063] | 0.30 | 30 |
| 8 | Source warm-start target fine-tune | target_macro_item_mae | -0.027 [-0.078, 0.011] | 0.13 | 30 |
| 8 | Source warm-start target fine-tune | target_total_mae | -0.071 [-0.414, 0.196] | 0.50 | 30 |
| 8 | Generic target MLP head | target_binned_item_calibration_mae | -0.073 [-0.154, 0.060] | 0.17 | 30 |
| 8 | Generic target MLP head | target_macro_item_mae | -0.030 [-0.081, 0.025] | 0.13 | 30 |
| 8 | Generic target MLP head | target_total_mae | -0.020 [-0.480, 0.393] | 0.50 | 30 |
| 8 | Shared ordinal head | target_binned_item_calibration_mae | -0.002 [-0.012, 0.006] | 0.13 | 30 |
| 8 | Shared ordinal head | target_macro_item_mae | -0.001 [-0.004, 0.001] | 0.13 | 30 |
| 8 | Shared ordinal head | target_total_mae | -0.004 [-0.028, 0.021] | 0.43 | 30 |
| 8 | Target-only ordinal | target_binned_item_calibration_mae | 0.033 [-0.062, 0.193] | 0.67 | 30 |
| 8 | Target-only ordinal | target_macro_item_mae | -0.025 [-0.082, 0.069] | 0.23 | 30 |
| 8 | Target-only ordinal | target_total_mae | -0.045 [-0.841, 1.210] | 0.40 | 30 |
| 12 | Source+target direct multitask | target_binned_item_calibration_mae | -0.045 [-0.114, 0.022] | 0.07 | 30 |
| 12 | Source+target direct multitask | target_macro_item_mae | -0.020 [-0.056, 0.013] | 0.10 | 30 |
| 12 | Source+target direct multitask | target_total_mae | -0.086 [-0.388, 0.264] | 0.27 | 30 |
| 12 | Source warm-start target fine-tune | target_binned_item_calibration_mae | -0.039 [-0.103, 0.023] | 0.07 | 30 |
| 12 | Source warm-start target fine-tune | target_macro_item_mae | -0.018 [-0.050, 0.018] | 0.13 | 30 |
| 12 | Source warm-start target fine-tune | target_total_mae | -0.050 [-0.382, 0.271] | 0.40 | 30 |
| 12 | Generic target MLP head | target_binned_item_calibration_mae | -0.073 [-0.166, 0.016] | 0.10 | 30 |
| 12 | Generic target MLP head | target_macro_item_mae | -0.021 [-0.058, 0.032] | 0.13 | 30 |
| 12 | Generic target MLP head | target_total_mae | -0.057 [-0.434, 0.389] | 0.43 | 30 |
| 12 | Shared ordinal head | target_binned_item_calibration_mae | -0.000 [-0.004, 0.010] | 0.43 | 30 |
| 12 | Shared ordinal head | target_macro_item_mae | -0.000 [-0.003, 0.002] | 0.50 | 30 |
| 12 | Shared ordinal head | target_total_mae | -0.002 [-0.021, 0.012] | 0.47 | 30 |
| 12 | Target-only ordinal | target_binned_item_calibration_mae | 0.025 [-0.048, 0.100] | 0.70 | 30 |
| 12 | Target-only ordinal | target_macro_item_mae | -0.019 [-0.079, 0.032] | 0.23 | 30 |
| 12 | Target-only ordinal | target_total_mae | 0.006 [-0.660, 0.548] | 0.50 | 30 |
| 16 | Source+target direct multitask | target_binned_item_calibration_mae | -0.047 [-0.127, 0.042] | 0.10 | 30 |
| 16 | Source+target direct multitask | target_macro_item_mae | -0.018 [-0.043, 0.007] | 0.13 | 30 |
| 16 | Source+target direct multitask | target_total_mae | -0.107 [-0.352, 0.186] | 0.30 | 30 |
| 16 | Source warm-start target fine-tune | target_binned_item_calibration_mae | -0.049 [-0.139, 0.034] | 0.13 | 30 |
| 16 | Source warm-start target fine-tune | target_macro_item_mae | -0.019 [-0.049, 0.011] | 0.13 | 30 |
| 16 | Source warm-start target fine-tune | target_total_mae | -0.098 [-0.405, 0.254] | 0.30 | 30 |
| 16 | Generic target MLP head | target_binned_item_calibration_mae | -0.082 [-0.159, 0.007] | 0.07 | 30 |
| 16 | Generic target MLP head | target_macro_item_mae | -0.021 [-0.078, 0.031] | 0.10 | 30 |
| 16 | Generic target MLP head | target_total_mae | -0.099 [-0.557, 0.308] | 0.50 | 30 |
| 16 | Shared ordinal head | target_binned_item_calibration_mae | 0.001 [-0.002, 0.010] | 0.43 | 30 |
| 16 | Shared ordinal head | target_macro_item_mae | -0.000 [-0.002, 0.001] | 0.43 | 30 |
| 16 | Shared ordinal head | target_total_mae | -0.002 [-0.016, 0.012] | 0.33 | 30 |
| 16 | Target-only ordinal | target_binned_item_calibration_mae | 0.003 [-0.074, 0.086] | 0.53 | 30 |
| 16 | Target-only ordinal | target_macro_item_mae | -0.024 [-0.084, 0.020] | 0.20 | 30 |
| 16 | Target-only ordinal | target_total_mae | 0.009 [-0.868, 0.637] | 0.57 | 30 |
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
| 4 | Target-only direct MLP | 2.616 [-0.586, 4.930] | 2.712 [0.855, 4.930] | 0.232 [-0.170, 0.584] | 0.768 [0.416, 1.170] | 0.479 [0.301, 0.663] |
| 4 | Source+target direct multitask | 2.095 [-1.185, 4.193] | 2.313 [0.217, 4.193] | 0.164 [-0.006, 0.278] | 0.836 [0.722, 1.006] | 0.516 [0.376, 0.647] |
| 4 | Shared ordinal head | 1.735 [-1.858, 3.924] | 2.045 [0.413, 3.924] | 0.133 [0.026, 0.244] | 0.867 [0.756, 0.974] | 0.568 [0.407, 0.693] |
| 4 | Measurement-aware ordinal | 1.526 [-1.844, 3.503] | 1.882 [0.256, 3.503] | 0.133 [0.023, 0.246] | 0.867 [0.754, 0.977] | 0.568 [0.376, 0.686] |
| 8 | Target-only direct MLP | 1.977 [-0.732, 3.905] | 2.080 [0.714, 3.905] | 0.149 [-0.259, 0.571] | 0.851 [0.429, 1.259] | 0.430 [0.294, 0.531] |
| 8 | Source+target direct multitask | 0.919 [-3.395, 3.031] | 1.653 [0.236, 3.822] | 0.109 [-0.007, 0.201] | 0.891 [0.799, 1.007] | 0.554 [0.422, 0.733] |
| 8 | Shared ordinal head | 0.600 [-3.346, 2.645] | 1.274 [0.044, 3.346] | 0.091 [-0.024, 0.219] | 0.909 [0.781, 1.024] | 0.607 [0.453, 0.790] |
| 8 | Measurement-aware ordinal | 0.510 [-3.020, 2.375] | 1.169 [0.113, 3.020] | 0.093 [-0.034, 0.218] | 0.907 [0.782, 1.034] | 0.599 [0.432, 0.763] |
| 12 | Target-only direct MLP | 0.439 [-1.558, 2.711] | 0.947 [0.039, 2.711] | 0.143 [-0.144, 0.448] | 0.857 [0.552, 1.144] | 0.394 [0.260, 0.497] |
| 12 | Source+target direct multitask | -0.193 [-2.696, 2.049] | 1.015 [0.027, 2.696] | 0.098 [0.021, 0.170] | 0.902 [0.830, 0.979] | 0.590 [0.471, 0.688] |
| 12 | Shared ordinal head | -0.360 [-2.704, 1.485] | 0.842 [0.022, 2.704] | 0.079 [-0.010, 0.183] | 0.921 [0.817, 1.010] | 0.627 [0.464, 0.755] |
| 12 | Measurement-aware ordinal | -0.431 [-3.053, 1.241] | 0.843 [0.017, 3.053] | 0.080 [-0.010, 0.186] | 0.920 [0.814, 1.010] | 0.624 [0.469, 0.754] |
| 16 | Target-only direct MLP | 1.646 [-0.066, 3.845] | 1.662 [0.021, 3.845] | 0.168 [-0.065, 0.484] | 0.832 [0.516, 1.065] | 0.396 [0.211, 0.593] |
| 16 | Source+target direct multitask | 0.609 [-1.993, 2.700] | 1.179 [0.114, 2.700] | 0.100 [0.033, 0.155] | 0.900 [0.845, 0.967] | 0.573 [0.477, 0.684] |
| 16 | Shared ordinal head | 0.732 [-1.804, 2.738] | 1.271 [0.129, 2.839] | 0.094 [0.017, 0.190] | 0.906 [0.810, 0.983] | 0.600 [0.462, 0.732] |
| 16 | Measurement-aware ordinal | 0.753 [-1.592, 2.635] | 1.218 [0.188, 2.635] | 0.095 [0.014, 0.202] | 0.905 [0.798, 0.986] | 0.591 [0.463, 0.729] |
| 24 | Target-only direct MLP | 1.325 [-0.612, 3.133] | 1.455 [0.216, 3.133] | 0.204 [-0.025, 0.375] | 0.796 [0.625, 1.025] | 0.387 [0.270, 0.509] |
| 24 | Source+target direct multitask | 0.358 [-2.015, 2.195] | 1.070 [0.210, 2.443] | 0.131 [0.044, 0.233] | 0.869 [0.767, 0.956] | 0.546 [0.411, 0.658] |
| 24 | Shared ordinal head | 0.706 [-2.308, 3.295] | 1.354 [0.118, 3.586] | 0.125 [0.027, 0.269] | 0.875 [0.731, 0.973] | 0.578 [0.417, 0.765] |
| 24 | Measurement-aware ordinal | 0.652 [-2.152, 3.142] | 1.275 [0.069, 3.406] | 0.128 [0.040, 0.266] | 0.872 [0.734, 0.960] | 0.571 [0.428, 0.759] |

**E-DAIC -> CMDC.**

| k | method | CITL | abs CITL | slope | abs slope error | binned item calibration MAE |
| ---: | --- | ---: | ---: | ---: | ---: | ---: |
| 4 | Target-only direct MLP | 0.426 [-4.211, 4.430] | 2.009 [0.040, 4.980] | 0.916 [0.450, 1.301] | 0.206 [0.020, 0.550] | 0.526 [0.367, 0.727] |
| 4 | Source+target direct multitask | -0.118 [-5.313, 3.488] | 1.883 [0.203, 5.313] | 0.877 [0.483, 1.274] | 0.193 [0.017, 0.517] | 0.508 [0.349, 0.801] |
| 4 | Shared ordinal head | -0.131 [-4.229, 2.935] | 1.488 [0.023, 4.229] | 0.835 [0.519, 1.188] | 0.203 [0.008, 0.481] | 0.562 [0.399, 0.758] |
| 4 | Measurement-aware ordinal | -0.165 [-4.254, 2.920] | 1.495 [0.056, 4.254] | 0.832 [0.520, 1.184] | 0.205 [0.007, 0.480] | 0.571 [0.412, 0.764] |
| 8 | Target-only direct MLP | 0.590 [-1.554, 3.212] | 1.169 [0.086, 3.212] | 0.861 [0.627, 1.184] | 0.173 [0.009, 0.373] | 0.407 [0.314, 0.521] |
| 8 | Source+target direct multitask | 0.235 [-1.788, 2.513] | 1.098 [0.107, 2.513] | 0.857 [0.619, 1.112] | 0.177 [0.044, 0.381] | 0.402 [0.311, 0.515] |
| 8 | Shared ordinal head | 0.301 [-1.671, 2.186] | 1.069 [0.029, 2.186] | 0.823 [0.603, 1.055] | 0.186 [0.005, 0.397] | 0.438 [0.292, 0.557] |
| 8 | Measurement-aware ordinal | 0.304 [-1.645, 2.198] | 1.075 [0.027, 2.198] | 0.823 [0.601, 1.054] | 0.186 [0.008, 0.399] | 0.440 [0.294, 0.562] |
| 12 | Target-only direct MLP | 0.708 [-1.872, 2.961] | 1.252 [0.050, 2.961] | 0.851 [0.632, 1.143] | 0.178 [0.009, 0.368] | 0.396 [0.311, 0.531] |
| 12 | Source+target direct multitask | 0.369 [-2.127, 2.788] | 1.180 [0.182, 2.788] | 0.846 [0.654, 1.175] | 0.180 [0.018, 0.346] | 0.384 [0.272, 0.539] |
| 12 | Shared ordinal head | 0.534 [-2.237, 2.923] | 1.252 [0.104, 2.923] | 0.814 [0.642, 1.069] | 0.197 [0.027, 0.358] | 0.429 [0.324, 0.565] |
| 12 | Measurement-aware ordinal | 0.537 [-2.239, 2.927] | 1.255 [0.078, 2.927] | 0.815 [0.642, 1.067] | 0.197 [0.026, 0.358] | 0.429 [0.324, 0.566] |
| 16 | Target-only direct MLP | 0.522 [-1.721, 2.919] | 1.143 [0.148, 2.919] | 0.809 [0.595, 1.135] | 0.223 [0.006, 0.424] | 0.403 [0.292, 0.547] |
| 16 | Source+target direct multitask | 0.232 [-1.966, 2.697] | 1.004 [0.058, 2.697] | 0.821 [0.626, 1.133] | 0.207 [0.039, 0.374] | 0.400 [0.267, 0.557] |
| 16 | Shared ordinal head | 0.438 [-1.831, 2.920] | 1.040 [0.038, 2.920] | 0.772 [0.578, 1.024] | 0.238 [0.039, 0.422] | 0.448 [0.334, 0.588] |
| 16 | Measurement-aware ordinal | 0.443 [-1.810, 2.914] | 1.042 [0.043, 2.914] | 0.772 [0.577, 1.024] | 0.238 [0.040, 0.423] | 0.447 [0.334, 0.582] |
| 24 | Target-only direct MLP | 1.330 [-1.005, 3.040] | 1.560 [0.311, 3.040] | 0.896 [0.615, 1.172] | 0.149 [0.003, 0.385] | 0.423 [0.329, 0.548] |
| 24 | Source+target direct multitask | 0.943 [-1.336, 2.837] | 1.270 [0.105, 2.837] | 0.907 [0.642, 1.232] | 0.151 [0.017, 0.358] | 0.422 [0.295, 0.535] |
| 24 | Shared ordinal head | 1.189 [-1.015, 2.905] | 1.393 [0.149, 2.905] | 0.842 [0.578, 1.047] | 0.167 [0.019, 0.422] | 0.444 [0.318, 0.570] |
| 24 | Measurement-aware ordinal | 1.193 [-1.006, 2.909] | 1.395 [0.144, 2.909] | 0.841 [0.574, 1.047] | 0.168 [0.020, 0.426] | 0.442 [0.318, 0.571] |

## Interpretation Handle

Across repeated label-budget splits, source-plus-target calibrated rows beat the target-only direct MLP on mean macro item MAE in 0/50 method-budget-direction cells. The measurement-aware ordinal row beats its matched alternatives on mean macro item MAE in 3/50 cells. Use these counts as reviewer-facing uncertainty evidence, not as a universal architecture superiority claim.
