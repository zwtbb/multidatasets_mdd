# P5 MV14 Measurement-Uncertainty Bootstrap

Generated: `2026-08-13T06:45:37+00:00`

## Scope

MV14 uses group-wise subject bootstrap over the E-DAIC/CMDC PHQ C01-C08 item-response boundary to quantify measurement-model uncertainty. It writes aggregate stability summaries only.

## Verdict

- Status: `complete_mv14_uncertainty_supports_cautious_phq_partial_invariance`.
- Requested R: smoke `10`, core `200`, DIF `100`.
- Core effective draws: `185`.
- DIF minimum effective anchor draws: `100`.
- Best AIC model: `configural`.
- Best BIC model: `scalar`.
- Stable anchors: `C01;C04;C05;C07`.
- Top threshold-DIF items: `C02;C06`.
- Artifact hygiene passed: `True`.

## Runtime

| tier | requested R | effective draws | seconds | claim status |
| --- | ---: | ---: | ---: | --- |
| MV14_A_smoke_runtime | 10 | 10 | 28.5 | `not_claimable_smoke` |
| MV14_B_core_model_stability | 200 | 185 | 685.9 | `primary_core_stability` |
| MV14_C_item_DIF_stability | 100 | 100 | 885.9 | `primary_anchor_and_DIF_stability` |

## Core Stability

| tier | model | fit success | convergence | warnings | errors |
| --- | --- | ---: | ---: | ---: | ---: |
| MV14_A_smoke_runtime | configural | 1.000 | 0.900 | 0 | 0 |
| MV14_A_smoke_runtime | metric | 1.000 | 1.000 | 0 | 0 |
| MV14_A_smoke_runtime | scalar | 1.000 | 1.000 | 0 | 0 |
| MV14_A_smoke_runtime | partial_mv10 | 1.000 | 1.000 | 0 | 0 |
| MV14_B_core_model_stability | configural | 0.925 | 0.600 | 0 | 15 |
| MV14_B_core_model_stability | metric | 1.000 | 0.990 | 0 | 0 |
| MV14_B_core_model_stability | scalar | 1.000 | 1.000 | 0 | 0 |
| MV14_B_core_model_stability | partial_mv10 | 1.000 | 0.995 | 0 | 0 |
| MV14_C_item_DIF_stability | metric | 1.000 | 0.980 | 0 | 0 |
| MV14_C_item_DIF_stability | scalar | 1.000 | 1.000 | 0 | 0 |

## Model Selection

| tier | criterion | model | frequency | effective draws |
| --- | --- | --- | ---: | ---: |
| MV14_A_smoke_runtime | aic | configural | 0.300 | 10 |
| MV14_A_smoke_runtime | aic | partial_mv10 | 0.700 | 10 |
| MV14_A_smoke_runtime | bic | scalar | 0.700 | 10 |
| MV14_A_smoke_runtime | bic | partial_mv10 | 0.300 | 10 |
| MV14_B_core_model_stability | aic | configural | 0.708 | 185 |
| MV14_B_core_model_stability | aic | metric | 0.076 | 185 |
| MV14_B_core_model_stability | aic | partial_mv10 | 0.216 | 185 |
| MV14_B_core_model_stability | bic | scalar | 0.811 | 185 |
| MV14_B_core_model_stability | bic | partial_mv10 | 0.189 | 185 |

## Item Stability

| item | MV10 role | loading DIF freq | threshold DIF freq | anchor support freq | threshold rank |
| --- | --- | ---: | ---: | ---: | ---: |
| C01 depressed_mood | `anchor_candidate` | 0.040 | 0.000 | 0.960 | 7 |
| C02 anhedonia | `metric_only_threshold_free` | 0.090 | 0.800 | 0.160 | 1 |
| C03 sleep | `metric_only_threshold_free` | 0.000 | 0.020 | 0.980 | 4 |
| C04 fatigue | `anchor_candidate` | 0.030 | 0.040 | 0.930 | 3 |
| C05 appetite | `anchor_candidate` | 0.020 | 0.020 | 0.960 | 4 |
| C06 self_worth | `metric_only_threshold_free` | 0.000 | 0.760 | 0.240 | 2 |
| C07 concentration | `anchor_candidate` | 0.040 | 0.000 | 0.960 | 7 |
| C08 psychomotor | `free_loading_or_threshold` | 0.180 | 0.020 | 0.800 | 4 |

## Gate Recommendations

| recommendation | status | evidence |
| --- | --- | --- |
| measurement_uncertainty_boundary | `complete_mv14_uncertainty_supports_cautious_phq_partial_invariance` | Core effective R 185; DIF effective R 100. |
| anchor_wording | `stable` | Stable anchors: C01;C04;C05;C07. |
| dif_wording | `localized` | Top threshold-DIF items: C02;C06. |
| full_method_gate | `keep_blocked` | MV14 checks Y-layer measurement uncertainty, not X-to-theta prediction or cross-dataset calibration. |

## Interpretation Boundary

- MV14 is label-only measurement uncertainty evidence, not multimodal method evidence.
- Public outputs contain aggregate counts, frequencies, intervals, version rows, and bounded warning categories only.
- Local item-response matrices, resampling draws, fitted parameters, CI values, factor/theta scores, model objects, and detailed logs are not tracked.
- Full method construction remains blocked pending later predeclared MV15/MV16-style evidence.
