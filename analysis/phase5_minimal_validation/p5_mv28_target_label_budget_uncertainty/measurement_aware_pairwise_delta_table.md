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
