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
