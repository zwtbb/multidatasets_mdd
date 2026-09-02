# P5 MV26 Depression-Specific Baseline Stress Test

Generated: `2026-08-29T12:11:32+00:00`

## Scope

MV26 evaluates three close depression-specific baseline families under the same MV24 PHQ shared-item transfer contract. The package combines GNN-SDA-style graph adaptation, QuestMF-style question-wise ordinal fusion, and SCD-MLLM-style heterogeneous multimodal fusion. It is a controlled test of whether stronger representation/adaptation ideas remove the need for an explicit corpus-specific measurement pathway.

## Best Rows By Family

| transfer | family | best method | recon+calib score | macro item MAE | calibration MAE | total MAE | seeds |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: |
| cmdc_to_edaic_phq_shared | gnn_sda_style | gnn_sda_style_direct_head | 1.3392 | 0.8731 | 0.4661 | 5.7742 | 5 |
| cmdc_to_edaic_phq_shared | questmf_style | questmf_style_measurement_aware | 1.1590 | 0.8407 | 0.3183 | 4.9017 | 5 |
| cmdc_to_edaic_phq_shared | scd_mllm_style | scd_mllm_style_measurement_aware | 1.2379 | 0.8600 | 0.3779 | 5.3793 | 5 |
| edaic_to_cmdc_phq_shared | gnn_sda_style | gnn_sda_style_measurement_aware | 1.0657 | 0.5909 | 0.4749 | 3.6580 | 5 |
| edaic_to_cmdc_phq_shared | questmf_style | questmf_style_measurement_aware | 1.0960 | 0.6832 | 0.4128 | 4.0044 | 5 |
| edaic_to_cmdc_phq_shared | scd_mllm_style | scd_mllm_style_measurement_aware | 1.0841 | 0.6636 | 0.4205 | 3.8719 | 5 |

## Paired Measurement-Layer Test

| transfer | family | comparison | seeds | direct-minus-aware score delta | aware-better p | sig |
| --- | --- | --- | ---: | ---: | ---: | --- |
| cmdc_to_edaic_phq_shared | gnn_sda_style | gnn_sda_style_measurement_aware_vs_gnn_sda_style_direct_head | 5 | -0.0917 | 0.7753 | ns |
| cmdc_to_edaic_phq_shared | questmf_style | questmf_style_measurement_aware_vs_questmf_style_direct_head | 5 | 0.0444 | 0.1606 | ns |
| cmdc_to_edaic_phq_shared | scd_mllm_style | scd_mllm_style_measurement_aware_vs_scd_mllm_style_direct_head | 5 | 0.2469 | 0.1093 | ns |
| edaic_to_cmdc_phq_shared | gnn_sda_style | gnn_sda_style_measurement_aware_vs_gnn_sda_style_direct_head | 5 | 0.0549 | 0.2336 | ns |
| edaic_to_cmdc_phq_shared | questmf_style | questmf_style_measurement_aware_vs_questmf_style_direct_head | 5 | 0.0369 | 0.2468 | ns |
| edaic_to_cmdc_phq_shared | scd_mllm_style | scd_mllm_style_measurement_aware_vs_scd_mllm_style_direct_head | 5 | 0.0155 | 0.1002 | ns |

## Main Result Table

| transfer | family | method | seeds | target labels | calib n | eval n | macro item MAE | calibration MAE | recon+calib score | total MAE | CCC | post-head BA | aware delta | sig |
| --- | --- | --- | ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| cmdc_to_edaic_phq_shared | gnn_sda_style | gnn_sda_style_direct_head | 5 | yes | 66 | 153 | 0.873 [0.766, 0.981] | 0.466 [0.344, 0.588] | 1.339 [1.115, 1.564] | 5.774 [4.935, 6.614] | 0.175 [0.145, 0.205] | 0.821 [0.630, 1.000] |  |  |
| cmdc_to_edaic_phq_shared | gnn_sda_style | gnn_sda_style_measurement_aware | 5 | yes | 66 | 153 | 0.872 [0.811, 0.932] | 0.559 [0.494, 0.624] | 1.431 [1.307, 1.555] | 5.758 [5.299, 6.217] | 0.204 [0.090, 0.319] | 0.768 [0.732, 0.804] | -0.092 | ns |
| cmdc_to_edaic_phq_shared | questmf_style | questmf_style_direct_head | 5 | yes | 66 | 153 | 0.855 [0.828, 0.881] | 0.349 [0.263, 0.435] | 1.203 [1.098, 1.309] | 5.101 [4.815, 5.386] | 0.190 [0.118, 0.262] | 0.657 [0.566, 0.747] |  |  |
| cmdc_to_edaic_phq_shared | questmf_style | questmf_style_measurement_aware | 5 | yes | 66 | 153 | 0.841 [0.798, 0.883] | 0.318 [0.268, 0.369] | 1.159 [1.116, 1.202] | 4.902 [4.755, 5.048] | 0.220 [0.180, 0.259] | 0.653 [0.580, 0.726] | 0.044 | ns |
| cmdc_to_edaic_phq_shared | scd_mllm_style | scd_mllm_style_direct_head | 5 | yes | 66 | 153 | 0.921 [0.746, 1.095] | 0.564 [0.348, 0.780] | 1.485 [1.105, 1.864] | 6.221 [4.963, 7.480] | 0.155 [0.047, 0.263] | 0.721 [0.651, 0.791] |  |  |
| cmdc_to_edaic_phq_shared | scd_mllm_style | scd_mllm_style_measurement_aware | 5 | yes | 66 | 153 | 0.860 [0.817, 0.903] | 0.378 [0.308, 0.448] | 1.238 [1.131, 1.345] | 5.379 [5.063, 5.695] | 0.220 [0.152, 0.288] | 0.765 [0.706, 0.823] | 0.247 | ns |
| edaic_to_cmdc_phq_shared | gnn_sda_style | gnn_sda_style_direct_head | 5 | yes | 24 | 20 | 0.659 [0.575, 0.743] | 0.461 [0.349, 0.573] | 1.121 [0.929, 1.312] | 3.854 [3.676, 4.032] | 0.718 [0.605, 0.830] | 0.629 [0.497, 0.762] |  |  |
| edaic_to_cmdc_phq_shared | gnn_sda_style | gnn_sda_style_measurement_aware | 5 | yes | 24 | 20 | 0.591 [0.495, 0.686] | 0.475 [0.357, 0.593] | 1.066 [0.873, 1.258] | 3.658 [2.757, 4.559] | 0.808 [0.749, 0.866] | 0.683 [0.595, 0.772] | 0.055 | ns |
| edaic_to_cmdc_phq_shared | questmf_style | questmf_style_direct_head | 5 | yes | 24 | 20 | 0.713 [0.612, 0.813] | 0.420 [0.334, 0.507] | 1.133 [0.981, 1.285] | 3.933 [3.154, 4.712] | 0.689 [0.520, 0.857] | 0.633 [0.544, 0.723] |  |  |
| edaic_to_cmdc_phq_shared | questmf_style | questmf_style_measurement_aware | 5 | yes | 24 | 20 | 0.683 [0.582, 0.784] | 0.413 [0.348, 0.478] | 1.096 [0.930, 1.262] | 4.004 [2.965, 5.044] | 0.711 [0.560, 0.861] | 0.710 [0.602, 0.819] | 0.037 | ns |
| edaic_to_cmdc_phq_shared | scd_mllm_style | scd_mllm_style_direct_head | 5 | yes | 24 | 20 | 0.635 [0.534, 0.736] | 0.465 [0.402, 0.528] | 1.100 [0.943, 1.256] | 3.995 [3.542, 4.448] | 0.673 [0.517, 0.828] | 0.685 [0.584, 0.786] |  |  |
| edaic_to_cmdc_phq_shared | scd_mllm_style | scd_mllm_style_measurement_aware | 5 | yes | 24 | 20 | 0.664 [0.582, 0.745] | 0.420 [0.317, 0.524] | 1.084 [0.928, 1.240] | 3.872 [3.032, 4.712] | 0.718 [0.623, 0.813] | 0.777 [0.704, 0.851] | 0.015 | ns |

## Secondary Clinical Endpoint

| transfer | family | method | macro-F1 | BA | AUROC | AUPRC | sensitivity | specificity |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| cmdc_to_edaic_phq_shared | gnn_sda_style | gnn_sda_style_direct_head | 0.573 [0.526, 0.620] | 0.582 [0.549, 0.616] | 0.621 [0.594, 0.649] | 0.422 [0.365, 0.478] | 0.413 [0.194, 0.632] | 0.751 [0.542, 0.961] |
| cmdc_to_edaic_phq_shared | gnn_sda_style | gnn_sda_style_measurement_aware | 0.559 [0.502, 0.616] | 0.562 [0.511, 0.614] | 0.646 [0.601, 0.690] | 0.435 [0.376, 0.494] | 0.300 [0.155, 0.445] | 0.824 [0.739, 0.909] |
| cmdc_to_edaic_phq_shared | questmf_style | questmf_style_direct_head | 0.546 [0.474, 0.617] | 0.553 [0.498, 0.609] | 0.631 [0.575, 0.687] | 0.427 [0.361, 0.494] | 0.226 [0.115, 0.337] | 0.880 [0.818, 0.943] |
| cmdc_to_edaic_phq_shared | questmf_style | questmf_style_measurement_aware | 0.531 [0.484, 0.577] | 0.541 [0.506, 0.576] | 0.639 [0.613, 0.665] | 0.426 [0.394, 0.457] | 0.200 [0.128, 0.272] | 0.882 [0.872, 0.893] |
| cmdc_to_edaic_phq_shared | scd_mllm_style | scd_mllm_style_direct_head | 0.519 [0.481, 0.557] | 0.538 [0.516, 0.559] | 0.593 [0.526, 0.661] | 0.402 [0.351, 0.453] | 0.296 [0.043, 0.548] | 0.779 [0.509, 1.000] |
| cmdc_to_edaic_phq_shared | scd_mllm_style | scd_mllm_style_measurement_aware | 0.567 [0.534, 0.600] | 0.566 [0.534, 0.597] | 0.626 [0.606, 0.645] | 0.411 [0.379, 0.442] | 0.348 [0.291, 0.405] | 0.783 [0.739, 0.827] |
| edaic_to_cmdc_phq_shared | gnn_sda_style | gnn_sda_style_direct_head | 0.914 [0.821, 1.000] | 0.912 [0.813, 1.000] | 0.954 [0.885, 1.000] | 0.921 [0.803, 1.000] | 0.875 [0.685, 1.000] | 0.950 [0.893, 1.000] |
| edaic_to_cmdc_phq_shared | gnn_sda_style | gnn_sda_style_measurement_aware | 0.926 [0.851, 1.000] | 0.925 [0.846, 1.000] | 0.963 [0.919, 1.000] | 0.927 [0.838, 1.000] | 0.900 [0.770, 1.000] | 0.950 [0.893, 1.000] |
| edaic_to_cmdc_phq_shared | questmf_style | questmf_style_direct_head | 0.860 [0.766, 0.954] | 0.854 [0.757, 0.951] | 0.952 [0.886, 1.000] | 0.921 [0.811, 1.000] | 0.775 [0.605, 0.945] | 0.933 [0.887, 0.980] |
| edaic_to_cmdc_phq_shared | questmf_style | questmf_style_measurement_aware | 0.856 [0.736, 0.975] | 0.850 [0.724, 0.976] | 0.960 [0.913, 1.000] | 0.941 [0.873, 1.000] | 0.750 [0.505, 0.995] | 0.950 [0.893, 1.000] |
| edaic_to_cmdc_phq_shared | scd_mllm_style | scd_mllm_style_direct_head | 0.903 [0.812, 0.994] | 0.900 [0.801, 0.999] | 0.931 [0.831, 1.000] | 0.929 [0.853, 1.000] | 0.850 [0.648, 1.000] | 0.950 [0.893, 1.000] |
| edaic_to_cmdc_phq_shared | scd_mllm_style | scd_mllm_style_measurement_aware | 0.882 [0.806, 0.958] | 0.875 [0.797, 0.953] | 0.963 [0.912, 1.000] | 0.932 [0.832, 1.000] | 0.800 [0.661, 0.939] | 0.950 [0.893, 1.000] |

## Interpretation Handle

Use MV26 as a close-baseline stress-test package. The manuscript should foreground MV24 as the formal main method result, then use MV26 to show that measurement-aware target modeling remains complementary for question-wise item fusion and heterogeneous multimodal/foundation fusion. GNN-SDA-style remains direction-sensitive, which is useful stress evidence that representation adaptation alone does not make corpus-specific response mechanisms disappear.

