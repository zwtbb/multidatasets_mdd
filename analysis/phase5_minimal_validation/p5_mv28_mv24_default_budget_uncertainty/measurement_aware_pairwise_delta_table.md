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
