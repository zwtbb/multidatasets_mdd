# P5_MV04c Protocol Task/Valence Control

Generated: `2026-08-09T07:29:41+00:00`

## Scope

This extension of P5_MV04 tests whether protocol-label nuisance directions learned on training subjects can reduce MODMA task identity and EATD valence identity while preserving the main depression/severity task. The control uses training-fold protocol labels only; evaluation protocol labels are used only for stratified reporting and identity probes. No transformed features, projection parameters, or row-level predictions are exported.

## Inputs

- MODMA rows: `208`; subjects: `52`; feature columns: `352`.
- EATD rows: `486`; subjects: `162`; feature columns: `88`.
- Subject-overlap violations: `0`.

## Primary Slice Metrics

| domain | target | metric | slice | model | mean | seed count |
| --- | --- | --- | --- | --- | ---: | ---: |
| EATD | sds_total | MAE | negative | raw_pooled_valence_ridge | 12.644 | 5 |
| EATD | sds_total | MAE | negative | train_mean | 7.201 | 5 |
| EATD | sds_total | MAE | negative | valence_projection_k1_ridge | 12.466 | 5 |
| EATD | sds_total | MAE | negative | valence_projection_k2_ridge | 12.451 | 5 |
| EATD | sds_total | MAE | negative | valence_projection_k3_ridge | 12.584 | 5 |
| EATD | sds_total | MAE | negative | valence_projection_k5_ridge | 12.761 | 5 |
| EATD | sds_total | MAE | negative | valence_projection_k8_ridge | 13.144 | 5 |
| EATD | sds_total | MAE | neutral | raw_pooled_valence_ridge | 18.713 | 5 |
| EATD | sds_total | MAE | neutral | train_mean | 7.201 | 5 |
| EATD | sds_total | MAE | neutral | valence_projection_k1_ridge | 18.565 | 5 |
| EATD | sds_total | MAE | neutral | valence_projection_k2_ridge | 18.582 | 5 |
| EATD | sds_total | MAE | neutral | valence_projection_k3_ridge | 18.548 | 5 |
| EATD | sds_total | MAE | neutral | valence_projection_k5_ridge | 18.630 | 5 |
| EATD | sds_total | MAE | neutral | valence_projection_k8_ridge | 19.281 | 5 |
| EATD | sds_total | MAE | positive | raw_pooled_valence_ridge | 55.074 | 5 |
| EATD | sds_total | MAE | positive | train_mean | 7.201 | 5 |
| EATD | sds_total | MAE | positive | valence_projection_k1_ridge | 55.000 | 5 |
| EATD | sds_total | MAE | positive | valence_projection_k2_ridge | 54.869 | 5 |
| EATD | sds_total | MAE | positive | valence_projection_k3_ridge | 54.506 | 5 |
| EATD | sds_total | MAE | positive | valence_projection_k5_ridge | 53.436 | 5 |
| EATD | sds_total | MAE | positive | valence_projection_k8_ridge | 54.790 | 5 |
| EATD | sds_total | Spearman | negative | raw_pooled_valence_ridge | 0.046 | 5 |
| EATD | sds_total | Spearman | negative | train_mean | NA | 5 |
| EATD | sds_total | Spearman | negative | valence_projection_k1_ridge | 0.053 | 5 |
| EATD | sds_total | Spearman | negative | valence_projection_k2_ridge | 0.054 | 5 |
| EATD | sds_total | Spearman | negative | valence_projection_k3_ridge | 0.035 | 5 |
| EATD | sds_total | Spearman | negative | valence_projection_k5_ridge | 0.038 | 5 |
| EATD | sds_total | Spearman | negative | valence_projection_k8_ridge | 0.055 | 5 |
| EATD | sds_total | Spearman | neutral | raw_pooled_valence_ridge | -0.093 | 5 |
| EATD | sds_total | Spearman | neutral | train_mean | NA | 5 |
| EATD | sds_total | Spearman | neutral | valence_projection_k1_ridge | -0.092 | 5 |
| EATD | sds_total | Spearman | neutral | valence_projection_k2_ridge | -0.093 | 5 |
| EATD | sds_total | Spearman | neutral | valence_projection_k3_ridge | -0.094 | 5 |
| EATD | sds_total | Spearman | neutral | valence_projection_k5_ridge | -0.099 | 5 |
| EATD | sds_total | Spearman | neutral | valence_projection_k8_ridge | -0.078 | 5 |
| EATD | sds_total | Spearman | positive | raw_pooled_valence_ridge | -0.006 | 5 |
| EATD | sds_total | Spearman | positive | train_mean | NA | 5 |
| EATD | sds_total | Spearman | positive | valence_projection_k1_ridge | -0.009 | 5 |
| EATD | sds_total | Spearman | positive | valence_projection_k2_ridge | -0.011 | 5 |
| EATD | sds_total | Spearman | positive | valence_projection_k3_ridge | -0.018 | 5 |
| EATD | sds_total | Spearman | positive | valence_projection_k5_ridge | -0.012 | 5 |
| EATD | sds_total | Spearman | positive | valence_projection_k8_ridge | -0.012 | 5 |
| MODMA | binary_label | Balanced Accuracy | affective_task | raw_pooled_task_logistic | 0.739 | 5 |
| MODMA | binary_label | Balanced Accuracy | affective_task | task_projection_k1_logistic | 0.746 | 5 |
| MODMA | binary_label | Balanced Accuracy | affective_task | task_projection_k2_logistic | 0.753 | 5 |
| MODMA | binary_label | Balanced Accuracy | affective_task | task_projection_k3_logistic | 0.744 | 5 |
| MODMA | binary_label | Balanced Accuracy | affective_task | task_projection_k5_logistic | 0.736 | 5 |
| MODMA | binary_label | Balanced Accuracy | affective_task | task_projection_k8_logistic | 0.745 | 5 |
| MODMA | binary_label | Balanced Accuracy | affective_task | train_prior | 0.500 | 5 |
| MODMA | binary_label | Balanced Accuracy | interview | raw_pooled_task_logistic | 0.690 | 5 |
| MODMA | binary_label | Balanced Accuracy | interview | task_projection_k1_logistic | 0.690 | 5 |
| MODMA | binary_label | Balanced Accuracy | interview | task_projection_k2_logistic | 0.693 | 5 |
| MODMA | binary_label | Balanced Accuracy | interview | task_projection_k3_logistic | 0.673 | 5 |
| MODMA | binary_label | Balanced Accuracy | interview | task_projection_k5_logistic | 0.699 | 5 |
| MODMA | binary_label | Balanced Accuracy | interview | task_projection_k8_logistic | 0.692 | 5 |
| MODMA | binary_label | Balanced Accuracy | interview | train_prior | 0.500 | 5 |
| MODMA | binary_label | Balanced Accuracy | picture_description | raw_pooled_task_logistic | 0.676 | 5 |
| MODMA | binary_label | Balanced Accuracy | picture_description | task_projection_k1_logistic | 0.665 | 5 |
| MODMA | binary_label | Balanced Accuracy | picture_description | task_projection_k2_logistic | 0.665 | 5 |
| MODMA | binary_label | Balanced Accuracy | picture_description | task_projection_k3_logistic | 0.672 | 5 |
| MODMA | binary_label | Balanced Accuracy | picture_description | task_projection_k5_logistic | 0.673 | 5 |
| MODMA | binary_label | Balanced Accuracy | picture_description | task_projection_k8_logistic | 0.663 | 5 |
| MODMA | binary_label | Balanced Accuracy | picture_description | train_prior | 0.500 | 5 |
| MODMA | binary_label | Balanced Accuracy | reading | raw_pooled_task_logistic | 0.647 | 5 |
| MODMA | binary_label | Balanced Accuracy | reading | task_projection_k1_logistic | 0.635 | 5 |
| MODMA | binary_label | Balanced Accuracy | reading | task_projection_k2_logistic | 0.635 | 5 |
| MODMA | binary_label | Balanced Accuracy | reading | task_projection_k3_logistic | 0.650 | 5 |
| MODMA | binary_label | Balanced Accuracy | reading | task_projection_k5_logistic | 0.638 | 5 |
| MODMA | binary_label | Balanced Accuracy | reading | task_projection_k8_logistic | 0.645 | 5 |
| MODMA | binary_label | Balanced Accuracy | reading | train_prior | 0.500 | 5 |
| MODMA | binary_label | Macro-F1 | affective_task | raw_pooled_task_logistic | 0.733 | 5 |
| MODMA | binary_label | Macro-F1 | affective_task | task_projection_k1_logistic | 0.740 | 5 |
| MODMA | binary_label | Macro-F1 | affective_task | task_projection_k2_logistic | 0.747 | 5 |
| MODMA | binary_label | Macro-F1 | affective_task | task_projection_k3_logistic | 0.739 | 5 |
| MODMA | binary_label | Macro-F1 | affective_task | task_projection_k5_logistic | 0.729 | 5 |
| MODMA | binary_label | Macro-F1 | affective_task | task_projection_k8_logistic | 0.739 | 5 |
| MODMA | binary_label | Macro-F1 | affective_task | train_prior | 0.358 | 5 |
| MODMA | binary_label | Macro-F1 | interview | raw_pooled_task_logistic | 0.678 | 5 |
| MODMA | binary_label | Macro-F1 | interview | task_projection_k1_logistic | 0.677 | 5 |
| MODMA | binary_label | Macro-F1 | interview | task_projection_k2_logistic | 0.681 | 5 |
| MODMA | binary_label | Macro-F1 | interview | task_projection_k3_logistic | 0.663 | 5 |
| MODMA | binary_label | Macro-F1 | interview | task_projection_k5_logistic | 0.688 | 5 |
| MODMA | binary_label | Macro-F1 | interview | task_projection_k8_logistic | 0.681 | 5 |
| MODMA | binary_label | Macro-F1 | interview | train_prior | 0.358 | 5 |
| MODMA | binary_label | Macro-F1 | picture_description | raw_pooled_task_logistic | 0.668 | 5 |
| MODMA | binary_label | Macro-F1 | picture_description | task_projection_k1_logistic | 0.657 | 5 |
| MODMA | binary_label | Macro-F1 | picture_description | task_projection_k2_logistic | 0.657 | 5 |
| MODMA | binary_label | Macro-F1 | picture_description | task_projection_k3_logistic | 0.666 | 5 |
| MODMA | binary_label | Macro-F1 | picture_description | task_projection_k5_logistic | 0.665 | 5 |
| MODMA | binary_label | Macro-F1 | picture_description | task_projection_k8_logistic | 0.655 | 5 |
| MODMA | binary_label | Macro-F1 | picture_description | train_prior | 0.358 | 5 |
| MODMA | binary_label | Macro-F1 | reading | raw_pooled_task_logistic | 0.639 | 5 |
| MODMA | binary_label | Macro-F1 | reading | task_projection_k1_logistic | 0.623 | 5 |
| MODMA | binary_label | Macro-F1 | reading | task_projection_k2_logistic | 0.624 | 5 |
| MODMA | binary_label | Macro-F1 | reading | task_projection_k3_logistic | 0.639 | 5 |
| MODMA | binary_label | Macro-F1 | reading | task_projection_k5_logistic | 0.630 | 5 |
| MODMA | binary_label | Macro-F1 | reading | task_projection_k8_logistic | 0.640 | 5 |
| MODMA | binary_label | Macro-F1 | reading | train_prior | 0.358 | 5 |

## Main-Task Preservation

| domain | metric | slice | model | baseline | delta | relative loss | within 5pct |
| --- | --- | --- | --- | ---: | ---: | ---: | --- |
| EATD | MAE | negative | raw_pooled_valence_ridge | 12.644 | 0.000 | 0.000 | `True` |
| EATD | MAE | negative | train_mean | 12.644 | -5.443 | 0.000 | `True` |
| EATD | MAE | negative | valence_projection_k1_ridge | 12.644 | -0.178 | 0.000 | `True` |
| EATD | MAE | negative | valence_projection_k2_ridge | 12.644 | -0.193 | 0.000 | `True` |
| EATD | MAE | negative | valence_projection_k3_ridge | 12.644 | -0.059 | 0.000 | `True` |
| EATD | MAE | negative | valence_projection_k5_ridge | 12.644 | 0.117 | 0.009 | `True` |
| EATD | MAE | negative | valence_projection_k8_ridge | 12.644 | 0.501 | 0.040 | `True` |
| EATD | MAE | neutral | raw_pooled_valence_ridge | 18.713 | 0.000 | 0.000 | `True` |
| EATD | MAE | neutral | train_mean | 18.713 | -11.512 | 0.000 | `True` |
| EATD | MAE | neutral | valence_projection_k1_ridge | 18.713 | -0.149 | 0.000 | `True` |
| EATD | MAE | neutral | valence_projection_k2_ridge | 18.713 | -0.132 | 0.000 | `True` |
| EATD | MAE | neutral | valence_projection_k3_ridge | 18.713 | -0.166 | 0.000 | `True` |
| EATD | MAE | neutral | valence_projection_k5_ridge | 18.713 | -0.084 | 0.000 | `True` |
| EATD | MAE | neutral | valence_projection_k8_ridge | 18.713 | 0.567 | 0.030 | `True` |
| EATD | MAE | positive | raw_pooled_valence_ridge | 55.074 | 0.000 | 0.000 | `True` |
| EATD | MAE | positive | train_mean | 55.074 | -47.873 | 0.000 | `True` |
| EATD | MAE | positive | valence_projection_k1_ridge | 55.074 | -0.074 | 0.000 | `True` |
| EATD | MAE | positive | valence_projection_k2_ridge | 55.074 | -0.205 | 0.000 | `True` |
| EATD | MAE | positive | valence_projection_k3_ridge | 55.074 | -0.568 | 0.000 | `True` |
| EATD | MAE | positive | valence_projection_k5_ridge | 55.074 | -1.637 | 0.000 | `True` |
| EATD | MAE | positive | valence_projection_k8_ridge | 55.074 | -0.284 | 0.000 | `True` |
| EATD | Spearman | negative | raw_pooled_valence_ridge | 0.046 | 0.000 | 0.000 | `True` |
| EATD | Spearman | negative | train_mean | 0.046 | NA | 0.000 | `True` |
| EATD | Spearman | negative | valence_projection_k1_ridge | 0.046 | 0.006 | 0.000 | `True` |
| EATD | Spearman | negative | valence_projection_k2_ridge | 0.046 | 0.008 | 0.000 | `True` |
| EATD | Spearman | negative | valence_projection_k3_ridge | 0.046 | -0.011 | 0.240 | `False` |
| EATD | Spearman | negative | valence_projection_k5_ridge | 0.046 | -0.008 | 0.172 | `False` |
| EATD | Spearman | negative | valence_projection_k8_ridge | 0.046 | 0.008 | 0.000 | `True` |
| EATD | Spearman | neutral | raw_pooled_valence_ridge | -0.093 | 0.000 | 0.000 | `True` |
| EATD | Spearman | neutral | train_mean | -0.093 | NA | 0.000 | `True` |
| EATD | Spearman | neutral | valence_projection_k1_ridge | -0.093 | 0.001 | 0.000 | `True` |
| EATD | Spearman | neutral | valence_projection_k2_ridge | -0.093 | -0.001 | 0.006 | `True` |
| EATD | Spearman | neutral | valence_projection_k3_ridge | -0.093 | -0.001 | 0.014 | `True` |
| EATD | Spearman | neutral | valence_projection_k5_ridge | -0.093 | -0.007 | 0.071 | `False` |
| EATD | Spearman | neutral | valence_projection_k8_ridge | -0.093 | 0.015 | 0.000 | `True` |
| EATD | Spearman | positive | raw_pooled_valence_ridge | -0.006 | 0.000 | 0.000 | `True` |
| EATD | Spearman | positive | train_mean | -0.006 | NA | 0.000 | `True` |
| EATD | Spearman | positive | valence_projection_k1_ridge | -0.006 | -0.003 | 0.569 | `False` |
| EATD | Spearman | positive | valence_projection_k2_ridge | -0.006 | -0.006 | 1.028 | `False` |
| EATD | Spearman | positive | valence_projection_k3_ridge | -0.006 | -0.012 | 2.133 | `False` |
| EATD | Spearman | positive | valence_projection_k5_ridge | -0.006 | -0.006 | 1.124 | `False` |
| EATD | Spearman | positive | valence_projection_k8_ridge | -0.006 | -0.006 | 1.094 | `False` |
| MODMA | Balanced Accuracy | affective_task | raw_pooled_task_logistic | 0.739 | 0.000 | 0.000 | `True` |
| MODMA | Balanced Accuracy | affective_task | task_projection_k1_logistic | 0.739 | 0.007 | 0.000 | `True` |
| MODMA | Balanced Accuracy | affective_task | task_projection_k2_logistic | 0.739 | 0.014 | 0.000 | `True` |
| MODMA | Balanced Accuracy | affective_task | task_projection_k3_logistic | 0.739 | 0.005 | 0.000 | `True` |
| MODMA | Balanced Accuracy | affective_task | task_projection_k5_logistic | 0.739 | -0.003 | 0.005 | `True` |
| MODMA | Balanced Accuracy | affective_task | task_projection_k8_logistic | 0.739 | 0.006 | 0.000 | `True` |
| MODMA | Balanced Accuracy | affective_task | train_prior | 0.739 | -0.239 | 0.324 | `False` |
| MODMA | Balanced Accuracy | interview | raw_pooled_task_logistic | 0.690 | 0.000 | 0.000 | `True` |
| MODMA | Balanced Accuracy | interview | task_projection_k1_logistic | 0.690 | 0.000 | 0.000 | `True` |
| MODMA | Balanced Accuracy | interview | task_projection_k2_logistic | 0.690 | 0.003 | 0.000 | `True` |
| MODMA | Balanced Accuracy | interview | task_projection_k3_logistic | 0.690 | -0.017 | 0.025 | `True` |
| MODMA | Balanced Accuracy | interview | task_projection_k5_logistic | 0.690 | 0.009 | 0.000 | `True` |
| MODMA | Balanced Accuracy | interview | task_projection_k8_logistic | 0.690 | 0.002 | 0.000 | `True` |
| MODMA | Balanced Accuracy | interview | train_prior | 0.690 | -0.190 | 0.275 | `False` |
| MODMA | Balanced Accuracy | picture_description | raw_pooled_task_logistic | 0.676 | 0.000 | 0.000 | `True` |
| MODMA | Balanced Accuracy | picture_description | task_projection_k1_logistic | 0.676 | -0.012 | 0.017 | `True` |
| MODMA | Balanced Accuracy | picture_description | task_projection_k2_logistic | 0.676 | -0.012 | 0.017 | `True` |
| MODMA | Balanced Accuracy | picture_description | task_projection_k3_logistic | 0.676 | -0.004 | 0.006 | `True` |
| MODMA | Balanced Accuracy | picture_description | task_projection_k5_logistic | 0.676 | -0.003 | 0.004 | `True` |
| MODMA | Balanced Accuracy | picture_description | task_projection_k8_logistic | 0.676 | -0.013 | 0.019 | `True` |
| MODMA | Balanced Accuracy | picture_description | train_prior | 0.676 | -0.176 | 0.261 | `False` |
| MODMA | Balanced Accuracy | reading | raw_pooled_task_logistic | 0.647 | 0.000 | 0.000 | `True` |
| MODMA | Balanced Accuracy | reading | task_projection_k1_logistic | 0.647 | -0.012 | 0.019 | `True` |
| MODMA | Balanced Accuracy | reading | task_projection_k2_logistic | 0.647 | -0.012 | 0.019 | `True` |
| MODMA | Balanced Accuracy | reading | task_projection_k3_logistic | 0.647 | 0.003 | 0.000 | `True` |
| MODMA | Balanced Accuracy | reading | task_projection_k5_logistic | 0.647 | -0.009 | 0.014 | `True` |
| MODMA | Balanced Accuracy | reading | task_projection_k8_logistic | 0.647 | -0.002 | 0.003 | `True` |
| MODMA | Balanced Accuracy | reading | train_prior | 0.647 | -0.147 | 0.227 | `False` |
| MODMA | Macro-F1 | affective_task | raw_pooled_task_logistic | 0.733 | 0.000 | 0.000 | `True` |
| MODMA | Macro-F1 | affective_task | task_projection_k1_logistic | 0.733 | 0.007 | 0.000 | `True` |
| MODMA | Macro-F1 | affective_task | task_projection_k2_logistic | 0.733 | 0.014 | 0.000 | `True` |
| MODMA | Macro-F1 | affective_task | task_projection_k3_logistic | 0.733 | 0.006 | 0.000 | `True` |
| MODMA | Macro-F1 | affective_task | task_projection_k5_logistic | 0.733 | -0.004 | 0.005 | `True` |
| MODMA | Macro-F1 | affective_task | task_projection_k8_logistic | 0.733 | 0.005 | 0.000 | `True` |
| MODMA | Macro-F1 | affective_task | train_prior | 0.733 | -0.375 | 0.512 | `False` |
| MODMA | Macro-F1 | interview | raw_pooled_task_logistic | 0.678 | 0.000 | 0.000 | `True` |
| MODMA | Macro-F1 | interview | task_projection_k1_logistic | 0.678 | -0.001 | 0.001 | `True` |
| MODMA | Macro-F1 | interview | task_projection_k2_logistic | 0.678 | 0.003 | 0.000 | `True` |
| MODMA | Macro-F1 | interview | task_projection_k3_logistic | 0.678 | -0.015 | 0.023 | `True` |
| MODMA | Macro-F1 | interview | task_projection_k5_logistic | 0.678 | 0.010 | 0.000 | `True` |
| MODMA | Macro-F1 | interview | task_projection_k8_logistic | 0.678 | 0.003 | 0.000 | `True` |
| MODMA | Macro-F1 | interview | train_prior | 0.678 | -0.320 | 0.472 | `False` |
| MODMA | Macro-F1 | picture_description | raw_pooled_task_logistic | 0.668 | 0.000 | 0.000 | `True` |
| MODMA | Macro-F1 | picture_description | task_projection_k1_logistic | 0.668 | -0.012 | 0.017 | `True` |
| MODMA | Macro-F1 | picture_description | task_projection_k2_logistic | 0.668 | -0.011 | 0.016 | `True` |
| MODMA | Macro-F1 | picture_description | task_projection_k3_logistic | 0.668 | -0.002 | 0.003 | `True` |
| MODMA | Macro-F1 | picture_description | task_projection_k5_logistic | 0.668 | -0.003 | 0.004 | `True` |
| MODMA | Macro-F1 | picture_description | task_projection_k8_logistic | 0.668 | -0.013 | 0.020 | `True` |
| MODMA | Macro-F1 | picture_description | train_prior | 0.668 | -0.310 | 0.464 | `False` |
| MODMA | Macro-F1 | reading | raw_pooled_task_logistic | 0.639 | 0.000 | 0.000 | `True` |
| MODMA | Macro-F1 | reading | task_projection_k1_logistic | 0.639 | -0.016 | 0.025 | `True` |
| MODMA | Macro-F1 | reading | task_projection_k2_logistic | 0.639 | -0.015 | 0.024 | `True` |
| MODMA | Macro-F1 | reading | task_projection_k3_logistic | 0.639 | 0.000 | 0.000 | `True` |
| MODMA | Macro-F1 | reading | task_projection_k5_logistic | 0.639 | -0.009 | 0.014 | `True` |
| MODMA | Macro-F1 | reading | task_projection_k8_logistic | 0.639 | 0.000 | 0.000 | `True` |
| MODMA | Macro-F1 | reading | train_prior | 0.639 | -0.281 | 0.440 | `False` |

## Protocol Identity Probes

| domain | layer | representation | balanced accuracy | seed count |
| --- | --- | --- | ---: | ---: |
| EATD | feature | raw_egemaps_before_control | 0.283 | 5 |
| EATD | feature | valence_projection_k1_after_control | 0.333 | 5 |
| EATD | feature | valence_projection_k2_after_control | 0.342 | 5 |
| EATD | feature | valence_projection_k3_after_control | 0.354 | 5 |
| EATD | feature | valence_projection_k5_after_control | 0.363 | 5 |
| EATD | feature | valence_projection_k8_after_control | 0.321 | 5 |
| EATD | prediction | raw_pooled_valence_ridge_predictions | 0.354 | 5 |
| EATD | prediction | valence_projection_k1_ridge_predictions | 0.350 | 5 |
| EATD | prediction | valence_projection_k2_ridge_predictions | 0.346 | 5 |
| EATD | prediction | valence_projection_k3_ridge_predictions | 0.350 | 5 |
| EATD | prediction | valence_projection_k5_ridge_predictions | 0.350 | 5 |
| EATD | prediction | valence_projection_k8_ridge_predictions | 0.342 | 5 |
| MODMA | feature | raw_egemaps_before_control | 0.762 | 5 |
| MODMA | feature | task_projection_k1_after_control | 0.702 | 5 |
| MODMA | feature | task_projection_k2_after_control | 0.698 | 5 |
| MODMA | feature | task_projection_k3_after_control | 0.623 | 5 |
| MODMA | feature | task_projection_k5_after_control | 0.601 | 5 |
| MODMA | feature | task_projection_k8_after_control | 0.570 | 5 |
| MODMA | prediction | raw_pooled_task_logistic_predictions | 0.260 | 5 |
| MODMA | prediction | task_projection_k1_logistic_predictions | 0.263 | 5 |
| MODMA | prediction | task_projection_k2_logistic_predictions | 0.266 | 5 |
| MODMA | prediction | task_projection_k3_logistic_predictions | 0.266 | 5 |
| MODMA | prediction | task_projection_k5_logistic_predictions | 0.271 | 5 |
| MODMA | prediction | task_projection_k8_logistic_predictions | 0.279 | 5 |

## Verdict

- Pass-rule status: `mixed_protocol_control`.
- Short read: P5_MV04c tests train-fold protocol-label nuisance projection on MODMA task slices and EATD valence slices. Treat passing rows as diagnostic controls only; no transformed features, projection parameters, or row-level predictions are exported.

| domain | best model | feature identity before -> after | prediction identity before -> after | main signal beats floor | main task within 5pct | status |
| --- | --- | ---: | ---: | --- | --- | --- |
| MODMA | task_projection_k8_logistic | 0.762 -> 0.570 | 0.260 -> 0.279 | `True` | `True` | `pass_protocol_identity_control` |
| EATD | valence_projection_k8_ridge | 0.283 -> 0.321 | 0.354 -> 0.342 | `False` | `True` | `blocked_main_task_below_floor` |

## Interpretation Boundary

This is still a diagnostic control, not the full symptom-aligned model. A passing result means the lightweight feature contract can reduce some protocol identity without eval-protocol-label transforms; it does not prove task- or valence-invariant depression representation by itself.
