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
