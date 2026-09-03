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
