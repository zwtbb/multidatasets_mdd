**Panel A. CMDC -> E-DAIC.**

| method | regime | n_cal | macro item MAE | calibration MAE | total MAE |
| --- | --- | ---: | ---: | ---: | ---: |
| **Zero-target-label context** |  |  |  |  |  |
| ERM | zero-label | 0 | 1.039 [0.983, 1.094] | 0.734 [0.673, 0.795] | 5.724 [5.436, 6.012] |
| CORAL | zero-label | 0 | 1.014 [0.970, 1.057] | 0.677 [0.619, 0.735] | 6.498 [5.977, 7.019] |
| MMD | zero-label | 0 | 1.044 [0.735, 1.354] | 1.030 [0.728, 1.333] | 5.870 [4.921, 6.820] |
| DANN | zero-label | 0 | 1.438 [1.382, 1.494] | 0.744 [0.674, 0.815] | 7.346 [7.025, 7.667] |
| Strongest foundation | zero-label | 0 | 0.949 [0.900, 0.998] | 0.588 [0.510, 0.666] | 6.118 [5.740, 6.497] |
| Latent-only | zero-label | 0 | 1.055 [1.006, 1.105] | 0.735 [0.691, 0.780] | 6.751 [6.260, 7.241] |
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
| **Zero-target-label context** |  |  |  |  |  |
| ERM | zero-label | 0 | 1.151 [0.970, 1.331] | 0.911 [0.794, 1.029] | 7.469 [6.070, 8.867] |
| CORAL | zero-label | 0 | 0.950 [0.899, 1.001] | 0.462 [0.361, 0.564] | 6.858 [6.402, 7.313] |
| MMD | zero-label | 0 | 0.980 [0.904, 1.057] | 0.451 [0.350, 0.552] | 6.164 [5.625, 6.704] |
| DANN | zero-label | 0 | 1.264 [1.037, 1.491] | 0.910 [0.684, 1.137] | 8.599 [6.651, 10.547] |
| Strongest foundation | zero-label | 0 | 1.738 [1.626, 1.849] | 1.625 [1.476, 1.774] | 13.143 [12.027, 14.258] |
| Latent-only | zero-label | 0 | 1.861 [1.763, 1.959] | 1.802 [1.684, 1.920] | 14.469 [13.547, 15.392] |
| **Target-calibrated comparison** |  |  |  |  |  |
| Corpus-specific head | calibrated | 24 | 1.346 [1.195, 1.497] | 1.059 [0.892, 1.227] | 9.665 [8.408, 10.921] |
| Direct target fine-tune | calibrated | 24 | 0.607 [0.531, 0.684] | 0.358 [0.268, 0.449] | 3.220 [2.811, 3.629] |
| Direct source+target multitask | calibrated | 24 | 0.607 [0.534, 0.679] | 0.340 [0.284, 0.396] | 3.194 [2.731, 3.656] |
| Shared ordinal head | calibrated | 24 | 0.644 [0.564, 0.725] | 0.343 [0.267, 0.419] | 3.239 [2.562, 3.915] |
| Generic target MLP head | calibrated | 24 | 0.622 [0.547, 0.698] | 0.361 [0.292, 0.429] | 3.363 [2.745, 3.980] |
| Measurement-aware | calibrated | 24 | 0.645 [0.566, 0.723] | 0.342 [0.271, 0.413] | 3.255 [2.588, 3.922] |
| Measurement-aware + MMD | calibrated | 24 | 0.645 [0.566, 0.723] | 0.342 [0.271, 0.413] | 3.255 [2.588, 3.922] |
