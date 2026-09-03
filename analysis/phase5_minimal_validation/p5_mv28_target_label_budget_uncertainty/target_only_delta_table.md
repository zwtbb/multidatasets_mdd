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
