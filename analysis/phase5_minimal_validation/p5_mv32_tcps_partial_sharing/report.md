# P5 MV32 TCPS Partial Sharing

Generated: `2026-09-04T08:23:26+00:00`

## Scope

MV32 evaluates Target-Contract Partial Sharing: a sparse partially shared ordinal measurement head that learns which PHQ item threshold parameters should remain shared and which need target-specific residuals.

## Real-Data Main Table

| transfer_id | budget_id | k | eval_n | method | lambda_group | macro_item_mae | total_mae | ordinal_nll | rps | abs_citl | abs_slope_error | specificity_ratio |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| cmdc_to_edaic_phq_shared | mv24_default | 66 | 153 | Target-only direct MLP |  | 0.796 [0.762, 0.852] | 5.123 [4.754, 5.524] |  |  | 2.009 [0.344, 2.919] | 0.670 [0.433, 0.855] |  |
| cmdc_to_edaic_phq_shared | mv24_default | 66 | 153 | Target-only ordinal |  | 0.812 [0.773, 0.867] | 5.310 [4.999, 5.738] | 3.003 [2.666, 3.380] | 0.232 [0.221, 0.243] | 2.371 [0.820, 3.371] | 0.715 [0.493, 0.862] |  |
| cmdc_to_edaic_phq_shared | mv24_default | 66 | 153 | Direct source+target multitask |  | 0.806 [0.776, 0.858] | 5.106 [4.712, 5.396] |  |  | 1.316 [0.220, 2.159] | 0.645 [0.413, 0.763] |  |
| cmdc_to_edaic_phq_shared | mv24_default | 66 | 153 | Shared ordinal head |  | 0.814 [0.771, 0.854] | 4.955 [4.586, 5.302] | 1.905 [1.656, 2.739] | 0.207 [0.191, 0.222] | 0.511 [0.024, 1.696] | 0.570 [0.252, 0.745] |  |
| cmdc_to_edaic_phq_shared | mv24_default | 66 | 153 | Fully corpus-specific ordinal |  | 0.816 [0.782, 0.851] | 4.966 [4.575, 5.385] | 1.934 [1.730, 2.792] | 0.209 [0.196, 0.231] | 0.408 [0.006, 1.492] | 0.572 [0.254, 0.790] |  |
| cmdc_to_edaic_phq_shared | mv24_default | 66 | 153 | Generic target MLP head |  | 0.795 [0.763, 0.839] | 4.991 [4.671, 5.363] |  |  | 0.865 [0.060, 1.475] | 0.609 [0.397, 0.766] |  |
| cmdc_to_edaic_phq_shared | mv24_default | 66 | 153 | TCPS threshold residual | 1 | 0.814 [0.774, 0.859] | 4.999 [4.569, 5.577] | 2.042 [1.796, 3.085] | 0.211 [0.198, 0.235] | 0.575 [0.010, 2.924] | 0.563 [0.243, 0.804] | 0.996 [0.966, 1.000] |
| cmdc_to_edaic_phq_shared | mv24_default | 66 | 153 | TCPS threshold+slope residual | 1 | 0.817 [0.784, 0.873] | 4.993 [4.568, 5.543] | 2.041 [1.798, 2.897] | 0.212 [0.198, 0.240] | 0.457 [0.018, 1.750] | 0.576 [0.244, 0.802] | 0.992 [0.875, 1.000] |
| cmdc_to_edaic_phq_shared | mv24_default | 66 | 153 | Audit-weighted TCPS threshold | 1 | 0.818 [0.773, 0.869] | 5.000 [4.577, 5.546] | 2.006 [1.776, 2.782] | 0.211 [0.198, 0.236] | 0.489 [0.024, 1.865] | 0.569 [0.247, 0.792] | 0.375 [0.125, 0.750] |
| edaic_to_cmdc_phq_shared | mv24_default | 24 | 20 | Target-only direct MLP |  | 0.651 [0.554, 0.765] | 3.826 [2.814, 4.800] |  |  | 1.483 [0.016, 3.183] | 0.187 [0.033, 0.391] |  |
| edaic_to_cmdc_phq_shared | mv24_default | 24 | 20 | Target-only ordinal |  | 0.654 [0.559, 0.773] | 3.945 [2.737, 4.970] | 2.650 [2.057, 3.625] | 0.188 [0.155, 0.229] | 1.377 [0.218, 3.009] | 0.224 [0.028, 0.421] |  |
| edaic_to_cmdc_phq_shared | mv24_default | 24 | 20 | Direct source+target multitask |  | 0.650 [0.554, 0.770] | 3.789 [2.727, 4.683] |  |  | 1.647 [0.159, 3.438] | 0.153 [0.005, 0.377] |  |
| edaic_to_cmdc_phq_shared | mv24_default | 24 | 20 | Shared ordinal head |  | 0.666 [0.572, 0.793] | 3.576 [2.710, 4.455] | 1.712 [1.416, 2.048] | 0.174 [0.146, 0.211] | 1.329 [0.238, 3.017] | 0.139 [0.015, 0.393] |  |
| edaic_to_cmdc_phq_shared | mv24_default | 24 | 20 | Fully corpus-specific ordinal |  | 0.665 [0.571, 0.793] | 3.577 [2.697, 4.468] | 1.713 [1.406, 2.055] | 0.174 [0.145, 0.212] | 1.332 [0.181, 3.065] | 0.137 [0.012, 0.390] |  |
| edaic_to_cmdc_phq_shared | mv24_default | 24 | 20 | Generic target MLP head |  | 0.659 [0.561, 0.792] | 3.800 [2.764, 4.670] |  |  | 1.235 [0.148, 2.952] | 0.166 [0.009, 0.376] |  |
| edaic_to_cmdc_phq_shared | mv24_default | 24 | 20 | TCPS threshold residual | 1 | 0.665 [0.573, 0.791] | 3.596 [2.790, 4.522] | 1.754 [1.461, 2.073] | 0.175 [0.149, 0.212] | 1.366 [0.215, 3.021] | 0.148 [0.009, 0.465] | 0.954 [0.750, 1.000] |
| edaic_to_cmdc_phq_shared | mv24_default | 24 | 20 | TCPS threshold+slope residual | 1 | 0.665 [0.573, 0.791] | 3.595 [2.790, 4.524] | 1.756 [1.464, 2.077] | 0.175 [0.149, 0.213] | 1.365 [0.217, 3.023] | 0.147 [0.010, 0.466] | 0.954 [0.750, 1.000] |
| edaic_to_cmdc_phq_shared | mv24_default | 24 | 20 | Audit-weighted TCPS threshold | 1 | 0.664 [0.572, 0.791] | 3.591 [2.777, 4.495] | 1.747 [1.461, 2.076] | 0.174 [0.148, 0.212] | 1.354 [0.267, 3.007] | 0.140 [0.008, 0.448] | 0.496 [0.250, 0.750] |

## TCPS Lambda Sensitivity

| transfer_id | budget_id | k | lambda_group | macro_item_mae | ordinal_nll | rps | abs_citl | specificity_ratio |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| cmdc_to_edaic_phq_shared | mv24_default | 66 | 0 | 0.797 [0.771, 0.844] | 2.439 [2.181, 3.341] | 0.215 [0.204, 0.243] | 0.477 [0.060, 1.754] | 1.000 [1.000, 1.000] |
| cmdc_to_edaic_phq_shared | mv24_default | 66 | 0.3 | 0.800 [0.742, 0.858] | 2.264 [2.027, 3.159] | 0.212 [0.197, 0.240] | 0.505 [0.068, 1.966] | 1.000 [1.000, 1.000] |
| cmdc_to_edaic_phq_shared | mv24_default | 66 | 1 | 0.814 [0.774, 0.859] | 2.042 [1.796, 3.085] | 0.211 [0.198, 0.235] | 0.575 [0.010, 2.924] | 0.996 [0.966, 1.000] |
| cmdc_to_edaic_phq_shared | mv24_default | 66 | 10 | 0.820 [0.786, 0.866] | 1.966 [1.739, 2.888] | 0.211 [0.197, 0.237] | 0.434 [0.035, 1.502] | 0.000 [0.000, 0.000] |
| cmdc_to_edaic_phq_shared | mv24_default | 66 | 3 | 0.820 [0.786, 0.866] | 1.954 [1.739, 2.710] | 0.210 [0.197, 0.235] | 0.426 [0.035, 1.465] | 0.000 [0.000, 0.000] |
| edaic_to_cmdc_phq_shared | mv24_default | 24 | 0 | 0.664 [0.584, 0.783] | 2.062 [1.746, 2.437] | 0.181 [0.158, 0.217] | 1.627 [0.233, 3.226] | 1.000 [1.000, 1.000] |
| edaic_to_cmdc_phq_shared | mv24_default | 24 | 0.3 | 0.664 [0.580, 0.781] | 1.958 [1.649, 2.329] | 0.179 [0.155, 0.214] | 1.536 [0.097, 3.158] | 1.000 [1.000, 1.000] |
| edaic_to_cmdc_phq_shared | mv24_default | 24 | 1 | 0.665 [0.573, 0.791] | 1.754 [1.461, 2.073] | 0.175 [0.149, 0.212] | 1.366 [0.215, 3.021] | 0.954 [0.750, 1.000] |
| edaic_to_cmdc_phq_shared | mv24_default | 24 | 10 | 0.666 [0.571, 0.794] | 1.714 [1.422, 2.018] | 0.174 [0.147, 0.213] | 1.324 [0.235, 2.988] | 0.000 [0.000, 0.000] |
| edaic_to_cmdc_phq_shared | mv24_default | 24 | 3 | 0.666 [0.571, 0.794] | 1.714 [1.422, 2.018] | 0.174 [0.147, 0.213] | 1.324 [0.235, 2.988] | 0.000 [0.000, 0.000] |

## Participant Bootstrap

| transfer_id | budget_id | k | eval_n | method | reference_method | metric | delta | tcps_lower_error_fraction |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| cmdc_to_edaic_phq_shared | mv24_default | 66 | 153 | Audit-weighted TCPS threshold | Fully corpus-specific ordinal | ordinal_nll | -0.072 [-0.841, 0.887] | 0.07 |
| cmdc_to_edaic_phq_shared | mv24_default | 66 | 153 | Audit-weighted TCPS threshold | Fully corpus-specific ordinal | ranked_probability_score | -0.002 [-0.034, 0.015] | 0.26 |
| cmdc_to_edaic_phq_shared | mv24_default | 66 | 153 | Audit-weighted TCPS threshold | Fully corpus-specific ordinal | target_macro_item_mae | -0.002 [-0.066, 0.036] | 0.62 |
| cmdc_to_edaic_phq_shared | mv24_default | 66 | 153 | Audit-weighted TCPS threshold | Fully corpus-specific ordinal | total_calibration_in_the_large_abs | -0.073 [-1.326, 0.278] | 0.49 |
| cmdc_to_edaic_phq_shared | mv24_default | 66 | 153 | Audit-weighted TCPS threshold | Generic target MLP head | target_macro_item_mae | -0.023 [-0.066, 0.035] | 0.13 |
| cmdc_to_edaic_phq_shared | mv24_default | 66 | 153 | Audit-weighted TCPS threshold | Generic target MLP head | total_calibration_in_the_large_abs | 0.285 [-1.621, 1.491] | 0.64 |
| cmdc_to_edaic_phq_shared | mv24_default | 66 | 153 | Audit-weighted TCPS threshold | Shared ordinal head | ordinal_nll | -0.101 [-1.067, 0.417] | 0.08 |
| cmdc_to_edaic_phq_shared | mv24_default | 66 | 153 | Audit-weighted TCPS threshold | Shared ordinal head | ranked_probability_score | -0.004 [-0.045, 0.009] | 0.27 |
| cmdc_to_edaic_phq_shared | mv24_default | 66 | 153 | Audit-weighted TCPS threshold | Shared ordinal head | target_macro_item_mae | -0.004 [-0.066, 0.013] | 0.67 |
| cmdc_to_edaic_phq_shared | mv24_default | 66 | 153 | Audit-weighted TCPS threshold | Shared ordinal head | total_calibration_in_the_large_abs | 0.006 [-0.840, 0.687] | 0.57 |
| cmdc_to_edaic_phq_shared | mv24_default | 66 | 153 | TCPS threshold residual | Fully corpus-specific ordinal | ordinal_nll | -0.108 [-0.556, -0.000] | 0.03 |
| cmdc_to_edaic_phq_shared | mv24_default | 66 | 153 | TCPS threshold residual | Fully corpus-specific ordinal | ranked_probability_score | -0.002 [-0.022, 0.003] | 0.24 |
| cmdc_to_edaic_phq_shared | mv24_default | 66 | 153 | TCPS threshold residual | Fully corpus-specific ordinal | target_macro_item_mae | 0.002 [-0.037, 0.032] | 0.72 |
| cmdc_to_edaic_phq_shared | mv24_default | 66 | 153 | TCPS threshold residual | Fully corpus-specific ordinal | total_calibration_in_the_large_abs | -0.159 [-3.326, 0.667] | 0.47 |
| cmdc_to_edaic_phq_shared | mv24_default | 66 | 153 | TCPS threshold residual | Generic target MLP head | target_macro_item_mae | -0.019 [-0.065, 0.041] | 0.18 |
| cmdc_to_edaic_phq_shared | mv24_default | 66 | 153 | TCPS threshold residual | Generic target MLP head | total_calibration_in_the_large_abs | 0.199 [-3.475, 1.487] | 0.64 |
| cmdc_to_edaic_phq_shared | mv24_default | 66 | 153 | TCPS threshold residual | Shared ordinal head | ordinal_nll | -0.137 [-0.705, -0.035] | 0.00 |
| cmdc_to_edaic_phq_shared | mv24_default | 66 | 153 | TCPS threshold residual | Shared ordinal head | ranked_probability_score | -0.004 [-0.035, 0.002] | 0.28 |
| cmdc_to_edaic_phq_shared | mv24_default | 66 | 153 | TCPS threshold residual | Shared ordinal head | target_macro_item_mae | -0.001 [-0.069, 0.028] | 0.78 |
| cmdc_to_edaic_phq_shared | mv24_default | 66 | 153 | TCPS threshold residual | Shared ordinal head | total_calibration_in_the_large_abs | -0.080 [-3.149, 1.016] | 0.53 |
| edaic_to_cmdc_phq_shared | mv24_default | 24 | 20 | Audit-weighted TCPS threshold | Fully corpus-specific ordinal | ordinal_nll | -0.035 [-0.139, 0.059] | 0.26 |
| edaic_to_cmdc_phq_shared | mv24_default | 24 | 20 | Audit-weighted TCPS threshold | Fully corpus-specific ordinal | ranked_probability_score | 0.000 [-0.008, 0.009] | 0.50 |
| edaic_to_cmdc_phq_shared | mv24_default | 24 | 20 | Audit-weighted TCPS threshold | Fully corpus-specific ordinal | target_macro_item_mae | 0.001 [-0.025, 0.028] | 0.52 |
| edaic_to_cmdc_phq_shared | mv24_default | 24 | 20 | Audit-weighted TCPS threshold | Fully corpus-specific ordinal | total_calibration_in_the_large_abs | -0.014 [-0.290, 0.320] | 0.44 |
| edaic_to_cmdc_phq_shared | mv24_default | 24 | 20 | Audit-weighted TCPS threshold | Generic target MLP head | target_macro_item_mae | -0.006 [-0.097, 0.077] | 0.45 |
| edaic_to_cmdc_phq_shared | mv24_default | 24 | 20 | Audit-weighted TCPS threshold | Generic target MLP head | total_calibration_in_the_large_abs | -0.052 [-1.409, 1.228] | 0.48 |
| edaic_to_cmdc_phq_shared | mv24_default | 24 | 20 | Audit-weighted TCPS threshold | Shared ordinal head | ordinal_nll | -0.036 [-0.144, 0.059] | 0.24 |
| edaic_to_cmdc_phq_shared | mv24_default | 24 | 20 | Audit-weighted TCPS threshold | Shared ordinal head | ranked_probability_score | -0.000 [-0.008, 0.008] | 0.49 |
| edaic_to_cmdc_phq_shared | mv24_default | 24 | 20 | Audit-weighted TCPS threshold | Shared ordinal head | target_macro_item_mae | 0.001 [-0.023, 0.027] | 0.54 |
| edaic_to_cmdc_phq_shared | mv24_default | 24 | 20 | Audit-weighted TCPS threshold | Shared ordinal head | total_calibration_in_the_large_abs | -0.016 [-0.289, 0.315] | 0.43 |
| edaic_to_cmdc_phq_shared | mv24_default | 24 | 20 | TCPS threshold residual | Fully corpus-specific ordinal | ordinal_nll | -0.041 [-0.145, 0.050] | 0.21 |
| edaic_to_cmdc_phq_shared | mv24_default | 24 | 20 | TCPS threshold residual | Fully corpus-specific ordinal | ranked_probability_score | -0.000 [-0.009, 0.008] | 0.46 |
| edaic_to_cmdc_phq_shared | mv24_default | 24 | 20 | TCPS threshold residual | Fully corpus-specific ordinal | target_macro_item_mae | 0.000 [-0.025, 0.027] | 0.50 |
| edaic_to_cmdc_phq_shared | mv24_default | 24 | 20 | TCPS threshold residual | Fully corpus-specific ordinal | total_calibration_in_the_large_abs | -0.028 [-0.319, 0.270] | 0.42 |
| edaic_to_cmdc_phq_shared | mv24_default | 24 | 20 | TCPS threshold residual | Generic target MLP head | target_macro_item_mae | -0.006 [-0.095, 0.077] | 0.45 |
| edaic_to_cmdc_phq_shared | mv24_default | 24 | 20 | TCPS threshold residual | Generic target MLP head | total_calibration_in_the_large_abs | -0.067 [-1.442, 1.208] | 0.46 |
| edaic_to_cmdc_phq_shared | mv24_default | 24 | 20 | TCPS threshold residual | Shared ordinal head | ordinal_nll | -0.043 [-0.144, 0.052] | 0.19 |
| edaic_to_cmdc_phq_shared | mv24_default | 24 | 20 | TCPS threshold residual | Shared ordinal head | ranked_probability_score | -0.001 [-0.008, 0.008] | 0.45 |
| edaic_to_cmdc_phq_shared | mv24_default | 24 | 20 | TCPS threshold residual | Shared ordinal head | target_macro_item_mae | 0.001 [-0.022, 0.025] | 0.52 |
| edaic_to_cmdc_phq_shared | mv24_default | 24 | 20 | TCPS threshold residual | Shared ordinal head | total_calibration_in_the_large_abs | -0.031 [-0.306, 0.269] | 0.41 |

## Residual Support

| transfer_id | budget_id | k | method | item_id | audit_role | residual_norm | nonzero_split_fraction | audit_weight_mean |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| cmdc_to_edaic_phq_shared | mv24_default | 66 | Audit-weighted TCPS threshold | C01 | anchor | 0.847 [0.014, 1.677] | 0.93 | 0.830 |
| cmdc_to_edaic_phq_shared | mv24_default | 66 | Audit-weighted TCPS threshold | C02 | threshold_shift | 0.141 [0.000, 0.766] | 0.30 | 1.244 |
| cmdc_to_edaic_phq_shared | mv24_default | 66 | Audit-weighted TCPS threshold | C03 | other | 0.030 [0.000, 0.316] | 0.13 | 1.388 |
| cmdc_to_edaic_phq_shared | mv24_default | 66 | Audit-weighted TCPS threshold | C04 | anchor | 0.013 [0.000, 0.113] | 0.03 | 1.375 |
| cmdc_to_edaic_phq_shared | mv24_default | 66 | Audit-weighted TCPS threshold | C05 | anchor | 0.053 [0.000, 0.554] | 0.17 | 1.321 |
| cmdc_to_edaic_phq_shared | mv24_default | 66 | Audit-weighted TCPS threshold | C06 | threshold_shift | 1.654 [1.408, 1.774] | 1.00 | 0.508 |
| cmdc_to_edaic_phq_shared | mv24_default | 66 | Audit-weighted TCPS threshold | C07 | anchor | 0.004 [0.000, 0.034] | 0.03 | 1.404 |
| cmdc_to_edaic_phq_shared | mv24_default | 66 | Audit-weighted TCPS threshold | C08 | other | 0.180 [0.000, 0.791] | 0.40 | 1.200 |
| cmdc_to_edaic_phq_shared | mv24_default | 66 | TCPS threshold residual | C01 | anchor | 0.429 [0.360, 0.512] | 1.00 | 1.000 |
| cmdc_to_edaic_phq_shared | mv24_default | 66 | TCPS threshold residual | C02 | threshold_shift | 0.442 [0.381, 0.540] | 1.00 | 1.000 |
| cmdc_to_edaic_phq_shared | mv24_default | 66 | TCPS threshold residual | C03 | other | 0.430 [0.254, 0.541] | 1.00 | 1.000 |
| cmdc_to_edaic_phq_shared | mv24_default | 66 | TCPS threshold residual | C04 | anchor | 0.435 [0.326, 0.546] | 1.00 | 1.000 |
| cmdc_to_edaic_phq_shared | mv24_default | 66 | TCPS threshold residual | C05 | anchor | 0.441 [0.351, 0.585] | 1.00 | 1.000 |
| cmdc_to_edaic_phq_shared | mv24_default | 66 | TCPS threshold residual | C06 | threshold_shift | 0.452 [0.363, 0.595] | 1.00 | 1.000 |
| cmdc_to_edaic_phq_shared | mv24_default | 66 | TCPS threshold residual | C07 | anchor | 0.428 [0.261, 0.508] | 0.97 | 1.000 |
| cmdc_to_edaic_phq_shared | mv24_default | 66 | TCPS threshold residual | C08 | other | 0.445 [0.382, 0.618] | 1.00 | 1.000 |
| cmdc_to_edaic_phq_shared | mv24_default | 66 | TCPS threshold+slope residual | C01 | anchor | 0.426 [0.355, 0.488] | 1.00 | 1.000 |
| cmdc_to_edaic_phq_shared | mv24_default | 66 | TCPS threshold+slope residual | C02 | threshold_shift | 0.435 [0.350, 0.502] | 1.00 | 1.000 |
| cmdc_to_edaic_phq_shared | mv24_default | 66 | TCPS threshold+slope residual | C03 | other | 0.421 [0.123, 0.521] | 0.97 | 1.000 |
| cmdc_to_edaic_phq_shared | mv24_default | 66 | TCPS threshold+slope residual | C04 | anchor | 0.427 [0.282, 0.502] | 1.00 | 1.000 |
| cmdc_to_edaic_phq_shared | mv24_default | 66 | TCPS threshold+slope residual | C05 | anchor | 0.432 [0.175, 0.527] | 1.00 | 1.000 |
| cmdc_to_edaic_phq_shared | mv24_default | 66 | TCPS threshold+slope residual | C06 | threshold_shift | 0.443 [0.291, 0.524] | 1.00 | 1.000 |
| cmdc_to_edaic_phq_shared | mv24_default | 66 | TCPS threshold+slope residual | C07 | anchor | 0.425 [0.180, 0.521] | 0.97 | 1.000 |
| cmdc_to_edaic_phq_shared | mv24_default | 66 | TCPS threshold+slope residual | C08 | other | 0.441 [0.330, 0.559] | 1.00 | 1.000 |
| edaic_to_cmdc_phq_shared | mv24_default | 24 | Audit-weighted TCPS threshold | C01 | anchor | 0.761 [0.161, 1.624] | 0.97 | 0.873 |
| edaic_to_cmdc_phq_shared | mv24_default | 24 | Audit-weighted TCPS threshold | C02 | threshold_shift | 0.135 [0.000, 0.613] | 0.37 | 1.227 |
| edaic_to_cmdc_phq_shared | mv24_default | 24 | Audit-weighted TCPS threshold | C03 | other | 0.316 [0.000, 1.321] | 0.57 | 1.105 |
| edaic_to_cmdc_phq_shared | mv24_default | 24 | Audit-weighted TCPS threshold | C04 | anchor | 0.351 [0.000, 1.486] | 0.53 | 1.119 |
| edaic_to_cmdc_phq_shared | mv24_default | 24 | Audit-weighted TCPS threshold | C05 | anchor | 0.100 [0.000, 0.734] | 0.23 | 1.257 |
| edaic_to_cmdc_phq_shared | mv24_default | 24 | Audit-weighted TCPS threshold | C06 | threshold_shift | 1.625 [1.570, 1.651] | 1.00 | 0.502 |
| edaic_to_cmdc_phq_shared | mv24_default | 24 | Audit-weighted TCPS threshold | C07 | anchor | 0.032 [0.000, 0.262] | 0.03 | 1.392 |
| edaic_to_cmdc_phq_shared | mv24_default | 24 | Audit-weighted TCPS threshold | C08 | other | 0.054 [0.000, 0.406] | 0.27 | 1.312 |
| edaic_to_cmdc_phq_shared | mv24_default | 24 | TCPS threshold residual | C01 | anchor | 0.441 [0.378, 0.466] | 1.00 | 1.000 |
| edaic_to_cmdc_phq_shared | mv24_default | 24 | TCPS threshold residual | C02 | threshold_shift | 0.397 [0.000, 0.450] | 0.93 | 1.000 |
| edaic_to_cmdc_phq_shared | mv24_default | 24 | TCPS threshold residual | C03 | other | 0.426 [0.374, 0.455] | 1.00 | 1.000 |
| edaic_to_cmdc_phq_shared | mv24_default | 24 | TCPS threshold residual | C04 | anchor | 0.423 [0.408, 0.441] | 1.00 | 1.000 |
| edaic_to_cmdc_phq_shared | mv24_default | 24 | TCPS threshold residual | C05 | anchor | 0.391 [0.000, 0.432] | 0.93 | 1.000 |
| edaic_to_cmdc_phq_shared | mv24_default | 24 | TCPS threshold residual | C06 | threshold_shift | 0.396 [0.363, 0.416] | 1.00 | 1.000 |
| edaic_to_cmdc_phq_shared | mv24_default | 24 | TCPS threshold residual | C07 | anchor | 0.403 [0.260, 0.443] | 0.97 | 1.000 |
| edaic_to_cmdc_phq_shared | mv24_default | 24 | TCPS threshold residual | C08 | other | 0.341 [0.000, 0.450] | 0.80 | 1.000 |
| edaic_to_cmdc_phq_shared | mv24_default | 24 | TCPS threshold+slope residual | C01 | anchor | 0.446 [0.384, 0.472] | 1.00 | 1.000 |
| edaic_to_cmdc_phq_shared | mv24_default | 24 | TCPS threshold+slope residual | C02 | threshold_shift | 0.399 [0.000, 0.453] | 0.93 | 1.000 |
| edaic_to_cmdc_phq_shared | mv24_default | 24 | TCPS threshold+slope residual | C03 | other | 0.429 [0.377, 0.458] | 1.00 | 1.000 |
| edaic_to_cmdc_phq_shared | mv24_default | 24 | TCPS threshold+slope residual | C04 | anchor | 0.426 [0.411, 0.446] | 1.00 | 1.000 |
| edaic_to_cmdc_phq_shared | mv24_default | 24 | TCPS threshold+slope residual | C05 | anchor | 0.394 [0.000, 0.434] | 0.93 | 1.000 |
| edaic_to_cmdc_phq_shared | mv24_default | 24 | TCPS threshold+slope residual | C06 | threshold_shift | 0.398 [0.364, 0.419] | 1.00 | 1.000 |
| edaic_to_cmdc_phq_shared | mv24_default | 24 | TCPS threshold+slope residual | C07 | anchor | 0.405 [0.261, 0.444] | 0.97 | 1.000 |
| edaic_to_cmdc_phq_shared | mv24_default | 24 | TCPS threshold+slope residual | C08 | other | 0.343 [0.000, 0.453] | 0.80 | 1.000 |

## Targeted Item Error

| transfer_id | budget_id | k | eval_n | method | reference_method | item | audit_role | delta_item_mae | tcps_lower_error_split_fraction |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| cmdc_to_edaic_phq_shared | mv24_default | 66 | 153 | TCPS threshold residual | Fully corpus-specific ordinal | C02 | threshold_shift | -0.001 [-0.054, 0.024] | 0.60 |
| cmdc_to_edaic_phq_shared | mv24_default | 66 | 153 | TCPS threshold residual | Fully corpus-specific ordinal | C06 | threshold_shift | 0.006 [-0.015, 0.035] | 0.73 |
| cmdc_to_edaic_phq_shared | mv24_default | 66 | 153 | TCPS threshold residual | Fully corpus-specific ordinal | C01/C04/C05/C07 | measurement-gate anchor items | 0.003 [-0.037, 0.036] | 0.73 |
| cmdc_to_edaic_phq_shared | mv24_default | 66 | 153 | TCPS threshold residual | Fully corpus-specific ordinal | C02/C06 | measurement-gate threshold-shift items | 0.002 [-0.022, 0.026] | 0.70 |
| cmdc_to_edaic_phq_shared | mv24_default | 66 | 153 | TCPS threshold residual | Shared ordinal head | C02 | threshold_shift | -0.001 [-0.097, 0.040] | 0.77 |
| cmdc_to_edaic_phq_shared | mv24_default | 66 | 153 | TCPS threshold residual | Shared ordinal head | C06 | threshold_shift | 0.008 [-0.025, 0.072] | 0.70 |
| cmdc_to_edaic_phq_shared | mv24_default | 66 | 153 | TCPS threshold residual | Shared ordinal head | C01/C04/C05/C07 | measurement-gate anchor items | -0.003 [-0.057, 0.017] | 0.77 |
| cmdc_to_edaic_phq_shared | mv24_default | 66 | 153 | TCPS threshold residual | Shared ordinal head | C02/C06 | measurement-gate threshold-shift items | 0.004 [-0.044, 0.035] | 0.77 |
| cmdc_to_edaic_phq_shared | mv24_default | 66 | 153 | Audit-weighted TCPS threshold | Fully corpus-specific ordinal | C02 | threshold_shift | -0.003 [-0.051, 0.023] | 0.53 |
| cmdc_to_edaic_phq_shared | mv24_default | 66 | 153 | Audit-weighted TCPS threshold | Fully corpus-specific ordinal | C06 | threshold_shift | 0.003 [-0.080, 0.061] | 0.77 |
| cmdc_to_edaic_phq_shared | mv24_default | 66 | 153 | Audit-weighted TCPS threshold | Fully corpus-specific ordinal | C01/C04/C05/C07 | measurement-gate anchor items | -0.003 [-0.057, 0.021] | 0.60 |
| cmdc_to_edaic_phq_shared | mv24_default | 66 | 153 | Audit-weighted TCPS threshold | Fully corpus-specific ordinal | C02/C06 | measurement-gate threshold-shift items | 0.000 [-0.066, 0.035] | 0.70 |
| cmdc_to_edaic_phq_shared | mv24_default | 66 | 153 | Audit-weighted TCPS threshold | Shared ordinal head | C02 | threshold_shift | -0.002 [-0.073, 0.037] | 0.53 |
| cmdc_to_edaic_phq_shared | mv24_default | 66 | 153 | Audit-weighted TCPS threshold | Shared ordinal head | C06 | threshold_shift | 0.005 [-0.068, 0.039] | 0.77 |
| cmdc_to_edaic_phq_shared | mv24_default | 66 | 153 | Audit-weighted TCPS threshold | Shared ordinal head | C01/C04/C05/C07 | measurement-gate anchor items | -0.009 [-0.077, 0.010] | 0.57 |
| cmdc_to_edaic_phq_shared | mv24_default | 66 | 153 | Audit-weighted TCPS threshold | Shared ordinal head | C02/C06 | measurement-gate threshold-shift items | 0.002 [-0.055, 0.021] | 0.77 |
| edaic_to_cmdc_phq_shared | mv24_default | 24 | 20 | TCPS threshold residual | Fully corpus-specific ordinal | C02 | threshold_shift | 0.005 [-0.051, 0.050] | 0.60 |
| edaic_to_cmdc_phq_shared | mv24_default | 24 | 20 | TCPS threshold residual | Fully corpus-specific ordinal | C06 | threshold_shift | 0.002 [-0.028, 0.026] | 0.53 |
| edaic_to_cmdc_phq_shared | mv24_default | 24 | 20 | TCPS threshold residual | Fully corpus-specific ordinal | C01/C04/C05/C07 | measurement-gate anchor items | -0.002 [-0.024, 0.025] | 0.47 |
| edaic_to_cmdc_phq_shared | mv24_default | 24 | 20 | TCPS threshold residual | Fully corpus-specific ordinal | C02/C06 | measurement-gate threshold-shift items | 0.003 [-0.024, 0.028] | 0.53 |
| edaic_to_cmdc_phq_shared | mv24_default | 24 | 20 | TCPS threshold residual | Shared ordinal head | C02 | threshold_shift | 0.006 [-0.042, 0.050] | 0.60 |
| edaic_to_cmdc_phq_shared | mv24_default | 24 | 20 | TCPS threshold residual | Shared ordinal head | C06 | threshold_shift | 0.002 [-0.025, 0.025] | 0.57 |
| edaic_to_cmdc_phq_shared | mv24_default | 24 | 20 | TCPS threshold residual | Shared ordinal head | C01/C04/C05/C07 | measurement-gate anchor items | -0.000 [-0.020, 0.024] | 0.47 |
| edaic_to_cmdc_phq_shared | mv24_default | 24 | 20 | TCPS threshold residual | Shared ordinal head | C02/C06 | measurement-gate threshold-shift items | 0.004 [-0.019, 0.027] | 0.53 |
| edaic_to_cmdc_phq_shared | mv24_default | 24 | 20 | Audit-weighted TCPS threshold | Fully corpus-specific ordinal | C02 | threshold_shift | 0.007 [-0.041, 0.049] | 0.63 |
| edaic_to_cmdc_phq_shared | mv24_default | 24 | 20 | Audit-weighted TCPS threshold | Fully corpus-specific ordinal | C06 | threshold_shift | 0.012 [-0.023, 0.047] | 0.73 |
| edaic_to_cmdc_phq_shared | mv24_default | 24 | 20 | Audit-weighted TCPS threshold | Fully corpus-specific ordinal | C01/C04/C05/C07 | measurement-gate anchor items | -0.002 [-0.025, 0.023] | 0.47 |
| edaic_to_cmdc_phq_shared | mv24_default | 24 | 20 | Audit-weighted TCPS threshold | Fully corpus-specific ordinal | C02/C06 | measurement-gate threshold-shift items | 0.010 [-0.017, 0.032] | 0.70 |
| edaic_to_cmdc_phq_shared | mv24_default | 24 | 20 | Audit-weighted TCPS threshold | Shared ordinal head | C02 | threshold_shift | 0.007 [-0.034, 0.049] | 0.60 |
| edaic_to_cmdc_phq_shared | mv24_default | 24 | 20 | Audit-weighted TCPS threshold | Shared ordinal head | C06 | threshold_shift | 0.013 [-0.020, 0.046] | 0.73 |
| edaic_to_cmdc_phq_shared | mv24_default | 24 | 20 | Audit-weighted TCPS threshold | Shared ordinal head | C01/C04/C05/C07 | measurement-gate anchor items | -0.001 [-0.020, 0.023] | 0.47 |
| edaic_to_cmdc_phq_shared | mv24_default | 24 | 20 | Audit-weighted TCPS threshold | Shared ordinal head | C02/C06 | measurement-gate threshold-shift items | 0.010 [-0.012, 0.030] | 0.73 |

## Fixed-Latent Simulation

| world_id | transfer_id | method | macro_item_mae | ordinal_nll | rps | abs_citl | specificity_ratio | draw_count |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| H0_invariant | cmdc_to_edaic_phq_shared | Shared ordinal head | 0.917 [0.872, 0.953] | 1.220 [1.171, 1.259] | 0.188 [0.179, 0.196] | 0.250 [0.008, 0.610] |  | 120 |
| H0_invariant | cmdc_to_edaic_phq_shared | Fully corpus-specific ordinal | 0.918 [0.871, 0.953] | 1.222 [1.174, 1.262] | 0.188 [0.179, 0.196] | 0.255 [0.012, 0.657] |  | 120 |
| H0_invariant | cmdc_to_edaic_phq_shared | TCPS threshold residual | 0.917 [0.872, 0.953] | 1.220 [1.171, 1.260] | 0.188 [0.179, 0.196] | 0.250 [0.011, 0.619] | 0.327 [0.122, 0.625] | 120 |
| H0_invariant | edaic_to_cmdc_phq_shared | Shared ordinal head | 0.874 [0.764, 0.995] | 1.191 [1.035, 1.302] | 0.181 [0.153, 0.212] | 0.607 [0.024, 1.567] |  | 120 |
| H0_invariant | edaic_to_cmdc_phq_shared | Fully corpus-specific ordinal | 0.876 [0.765, 0.996] | 1.198 [1.037, 1.313] | 0.182 [0.154, 0.213] | 0.621 [0.028, 1.657] |  | 120 |
| H0_invariant | edaic_to_cmdc_phq_shared | TCPS threshold residual | 0.874 [0.764, 0.995] | 1.193 [1.036, 1.305] | 0.181 [0.153, 0.213] | 0.608 [0.017, 1.561] | 0.497 [0.125, 0.875] | 120 |
| H_dense_threshold_DIF | cmdc_to_edaic_phq_shared | Shared ordinal head | 0.916 [0.882, 0.949] | 1.219 [1.178, 1.252] | 0.188 [0.180, 0.195] | 0.256 [0.020, 0.716] |  | 120 |
| H_dense_threshold_DIF | cmdc_to_edaic_phq_shared | Fully corpus-specific ordinal | 0.917 [0.882, 0.952] | 1.222 [1.180, 1.254] | 0.188 [0.180, 0.196] | 0.268 [0.018, 0.734] |  | 120 |
| H_dense_threshold_DIF | cmdc_to_edaic_phq_shared | TCPS threshold residual | 0.916 [0.882, 0.949] | 1.220 [1.178, 1.253] | 0.188 [0.180, 0.195] | 0.256 [0.033, 0.733] | 0.474 [0.125, 0.750] | 120 |
| H_dense_threshold_DIF | edaic_to_cmdc_phq_shared | Shared ordinal head | 0.852 [0.732, 0.953] | 1.146 [0.972, 1.312] | 0.174 [0.145, 0.203] | 0.564 [0.024, 1.575] |  | 120 |
| H_dense_threshold_DIF | edaic_to_cmdc_phq_shared | Fully corpus-specific ordinal | 0.852 [0.733, 0.952] | 1.152 [0.978, 1.321] | 0.175 [0.145, 0.205] | 0.565 [0.030, 1.620] |  | 120 |
| H_dense_threshold_DIF | edaic_to_cmdc_phq_shared | TCPS threshold residual | 0.851 [0.731, 0.953] | 1.148 [0.976, 1.323] | 0.174 [0.145, 0.204] | 0.564 [0.032, 1.540] | 0.497 [0.125, 0.750] | 120 |
| H_sparse_C02_C06_threshold_DIF | cmdc_to_edaic_phq_shared | Shared ordinal head | 0.919 [0.881, 0.955] | 1.222 [1.181, 1.264] | 0.188 [0.180, 0.197] | 0.278 [0.027, 0.862] |  | 120 |
| H_sparse_C02_C06_threshold_DIF | cmdc_to_edaic_phq_shared | Fully corpus-specific ordinal | 0.919 [0.882, 0.956] | 1.224 [1.185, 1.267] | 0.189 [0.180, 0.197] | 0.285 [0.007, 0.874] |  | 120 |
| H_sparse_C02_C06_threshold_DIF | cmdc_to_edaic_phq_shared | TCPS threshold residual | 0.919 [0.881, 0.955] | 1.222 [1.182, 1.265] | 0.189 [0.180, 0.197] | 0.279 [0.019, 0.851] | 0.401 [0.125, 0.625] | 120 |
| H_sparse_C02_C06_threshold_DIF | edaic_to_cmdc_phq_shared | Shared ordinal head | 0.851 [0.751, 0.958] | 1.178 [1.041, 1.301] | 0.175 [0.150, 0.201] | 0.529 [0.010, 1.589] |  | 120 |
| H_sparse_C02_C06_threshold_DIF | edaic_to_cmdc_phq_shared | Fully corpus-specific ordinal | 0.852 [0.753, 0.958] | 1.184 [1.046, 1.312] | 0.176 [0.151, 0.202] | 0.538 [0.014, 1.609] |  | 120 |
| H_sparse_C02_C06_threshold_DIF | edaic_to_cmdc_phq_shared | TCPS threshold residual | 0.851 [0.751, 0.957] | 1.180 [1.043, 1.305] | 0.176 [0.150, 0.201] | 0.531 [0.013, 1.610] | 0.511 [0.125, 0.875] | 120 |

## Go/No-Go

| gate | status | recommendation |
| --- | --- | --- |
| real_data_tcps_vs_extremes | `real_data_partial_support` | Use real data to bound performance and avoid claiming universal MAE superiority. |
| participant_bootstrap_tcps_vs_extremes | `bootstrap_partial_not_interval_stable` | Use participant bootstrap deltas as the main uncertainty check for superiority wording. |
| fixed_latent_simulation_pattern | `simulation_mechanism_supported` | Use simulation to validate the partial-sharing mechanism under known measurement heterogeneity. |
| overall_icassp_positioning | `borderline_audit_guided_algorithm_candidate` | Use TCPS as an audit-guided algorithmic instantiation; do not claim stable real-data superiority without stronger participant-level uncertainty. |

## Interpretation Boundary

- TCPS should be claimed as learning partial measurement sharing only where it beats shared/full-specific extremes under matched target-label exposure.
- Real-data performance support is bounded: TCPS is competitive on MAE, but the shared ordinal head remains stronger on held-out ordinal NLL/RPS in these runs.
- Participant bootstrap deltas do not provide stable interval-level superiority for the primary TCPS row, so superiority wording should be avoided.
- The audit-weighted variant gives the cleanest real-data residual sparsity signal and should be discussed as mechanism evidence, not as uniform superiority.
- The fixed-latent simulation tests mechanism behavior under known measurement heterogeneity; it does not replace real E-DAIC/CMDC evidence.
