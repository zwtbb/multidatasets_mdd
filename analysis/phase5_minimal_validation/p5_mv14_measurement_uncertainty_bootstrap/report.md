# P5 MV14 Measurement-Uncertainty Bootstrap

Generated: `2026-08-13T08:07:49+00:00`

## Scope

MV14 uses group-wise subject bootstrap over the E-DAIC/CMDC PHQ C01-C08 item-response boundary to quantify measurement-model uncertainty. It writes aggregate stability summaries only.

## Verdict

- Status: `complete_mv14_convergence_safe_item_level_measurement_shift`.
- Requested R: smoke `10`, core `200`, DIF `100`.
- Core convergence-safe full-ladder draws: `120` / `200`.
- Core full-ladder fit-success/converged draws: `185` / `120`.
- Configural fit-success/converged draws: `185` / `120`.
- DIF minimum effective anchor draws: `100`.
- Best full-ladder AIC/BIC model: `configural` / `scalar`.
- Best stable-ladder AIC/BIC model: `partial_mv10` / `scalar`.
- Stable anchors: `C01;C04;C05;C07`.
- Top threshold-DIF items: `C02;C06`.
- Artifact hygiene passed: `True`.

## Runtime

| tier | requested R | effective draws | seconds | claim status |
| --- | ---: | ---: | ---: | --- |
| MV14_A_smoke_runtime | 10 | 9 | 28.5 | `not_claimable_smoke` |
| MV14_B_core_model_stability | 200 | 120 | 704.0 | `primary_core_stability` |
| MV14_C_item_DIF_stability | 100 | 100 | 900.9 | `primary_anchor_and_DIF_stability` |

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

## Full-Ladder Model Selection

| tier | criterion | model | frequency | attempted | fit-success | converged | effective |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: |
| MV14_A_smoke_runtime | aic | configural | 0.333 | 10 | 10 | 9 | 9 |
| MV14_A_smoke_runtime | aic | partial_mv10 | 0.667 | 10 | 10 | 9 | 9 |
| MV14_A_smoke_runtime | bic | scalar | 0.667 | 10 | 10 | 9 | 9 |
| MV14_A_smoke_runtime | bic | partial_mv10 | 0.333 | 10 | 10 | 9 | 9 |
| MV14_B_core_model_stability | aic | configural | 0.683 | 200 | 185 | 120 | 120 |
| MV14_B_core_model_stability | aic | metric | 0.108 | 200 | 185 | 120 | 120 |
| MV14_B_core_model_stability | aic | partial_mv10 | 0.208 | 200 | 185 | 120 | 120 |
| MV14_B_core_model_stability | bic | scalar | 0.817 | 200 | 185 | 120 | 120 |
| MV14_B_core_model_stability | bic | partial_mv10 | 0.183 | 200 | 185 | 120 | 120 |

## Stable-Ladder Sensitivity

| tier | criterion | model | frequency | attempted | fit-success | converged | effective |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: |
| MV14_A_smoke_runtime | aic | metric | 0.100 | 10 | 10 | 10 | 10 |
| MV14_A_smoke_runtime | aic | partial_mv10 | 0.900 | 10 | 10 | 10 | 10 |
| MV14_A_smoke_runtime | bic | scalar | 0.700 | 10 | 10 | 10 | 10 |
| MV14_A_smoke_runtime | bic | partial_mv10 | 0.300 | 10 | 10 | 10 | 10 |
| MV14_B_core_model_stability | aic | metric | 0.355 | 200 | 200 | 197 | 197 |
| MV14_B_core_model_stability | aic | scalar | 0.020 | 200 | 200 | 197 | 197 |
| MV14_B_core_model_stability | aic | partial_mv10 | 0.624 | 200 | 200 | 197 | 197 |
| MV14_B_core_model_stability | bic | scalar | 0.812 | 200 | 200 | 197 | 197 |
| MV14_B_core_model_stability | bic | partial_mv10 | 0.188 | 200 | 200 | 197 | 197 |

## LRT Decision Stability

| tier | comparison | decision | attempted freq | valid freq | attempted | valid | failed |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: |
| MV14_A_smoke_runtime | metric_vs_configural | `comparison_failed_nonconverged_fit` | 0.100 | NA | 10 | 9 | 1 |
| MV14_A_smoke_runtime | metric_vs_configural | `no_strong_evidence_against_restriction` | 0.200 | 0.222 | 10 | 9 | 1 |
| MV14_A_smoke_runtime | metric_vs_configural | `restricted_model_rejected_lrt_only` | 0.700 | 0.778 | 10 | 9 | 1 |
| MV14_A_smoke_runtime | scalar_vs_metric | `restricted_model_rejected_lrt_only` | 1.000 | 1.000 | 10 | 10 | 0 |
| MV14_A_smoke_runtime | partial_mv10_vs_scalar | `restricted_model_rejected_lrt_and_bic` | 0.200 | 0.200 | 10 | 10 | 0 |
| MV14_A_smoke_runtime | partial_mv10_vs_scalar | `restricted_model_rejected_lrt_only` | 0.800 | 0.800 | 10 | 10 | 0 |
| MV14_A_smoke_runtime | partial_mv10_vs_configural | `comparison_failed_nonconverged_fit` | 0.100 | NA | 10 | 9 | 1 |
| MV14_A_smoke_runtime | partial_mv10_vs_configural | `no_strong_evidence_against_restriction` | 0.300 | 0.333 | 10 | 9 | 1 |
| MV14_A_smoke_runtime | partial_mv10_vs_configural | `restricted_model_rejected_lrt_only` | 0.600 | 0.667 | 10 | 9 | 1 |
| MV14_B_core_model_stability | metric_vs_configural | `comparison_failed_fit_error` | 0.075 | NA | 200 | 120 | 80 |
| MV14_B_core_model_stability | metric_vs_configural | `comparison_failed_nonconverged_fit` | 0.325 | NA | 200 | 120 | 80 |
| MV14_B_core_model_stability | metric_vs_configural | `no_strong_evidence_against_restriction` | 0.165 | 0.275 | 200 | 120 | 80 |
| MV14_B_core_model_stability | metric_vs_configural | `restricted_model_rejected_lrt_and_bic` | 0.020 | 0.033 | 200 | 120 | 80 |
| MV14_B_core_model_stability | metric_vs_configural | `restricted_model_rejected_lrt_only` | 0.415 | 0.692 | 200 | 120 | 80 |
| MV14_B_core_model_stability | scalar_vs_metric | `comparison_failed_nonconverged_fit` | 0.010 | NA | 200 | 198 | 2 |
| MV14_B_core_model_stability | scalar_vs_metric | `no_strong_evidence_against_restriction` | 0.030 | 0.030 | 200 | 198 | 2 |
| MV14_B_core_model_stability | scalar_vs_metric | `restricted_model_rejected_lrt_only` | 0.960 | 0.970 | 200 | 198 | 2 |
| MV14_B_core_model_stability | partial_mv10_vs_scalar | `comparison_failed_nonconverged_fit` | 0.005 | NA | 200 | 199 | 1 |
| MV14_B_core_model_stability | partial_mv10_vs_scalar | `no_strong_evidence_against_restriction` | 0.030 | 0.030 | 200 | 199 | 1 |
| MV14_B_core_model_stability | partial_mv10_vs_scalar | `restricted_model_rejected_lrt_and_bic` | 0.180 | 0.181 | 200 | 199 | 1 |
| MV14_B_core_model_stability | partial_mv10_vs_scalar | `restricted_model_rejected_lrt_only` | 0.785 | 0.789 | 200 | 199 | 1 |
| MV14_B_core_model_stability | partial_mv10_vs_configural | `comparison_failed_fit_error` | 0.075 | NA | 200 | 120 | 80 |
| MV14_B_core_model_stability | partial_mv10_vs_configural | `comparison_failed_nonconverged_fit` | 0.325 | NA | 200 | 120 | 80 |
| MV14_B_core_model_stability | partial_mv10_vs_configural | `no_strong_evidence_against_restriction` | 0.135 | 0.225 | 200 | 120 | 80 |
| MV14_B_core_model_stability | partial_mv10_vs_configural | `restricted_model_rejected_lrt_only` | 0.465 | 0.775 | 200 | 120 | 80 |

## Item Stability

| item | MV10 role | loading DIF freq | threshold DIF freq | anchor support freq | threshold rank |
| --- | --- | ---: | ---: | ---: | ---: |
| C01 depressed_mood | `anchor_candidate` | 0.040 | 0.000 | 0.960 | 7 |
| C02 anhedonia | `metric_only_threshold_free` | 0.050 | 0.800 | 0.180 | 1 |
| C03 sleep | `metric_only_threshold_free` | 0.000 | 0.020 | 0.980 | 4 |
| C04 fatigue | `anchor_candidate` | 0.030 | 0.040 | 0.930 | 3 |
| C05 appetite | `anchor_candidate` | 0.010 | 0.020 | 0.970 | 4 |
| C06 self_worth | `metric_only_threshold_free` | 0.000 | 0.760 | 0.240 | 2 |
| C07 concentration | `anchor_candidate` | 0.030 | 0.000 | 0.970 | 7 |
| C08 psychomotor | `free_loading_or_threshold` | 0.180 | 0.020 | 0.800 | 4 |

## Gate Recommendations

| recommendation | status | evidence |
| --- | --- | --- |
| measurement_uncertainty_boundary | `complete_mv14_convergence_safe_item_level_measurement_shift` | Full-ladder convergence-safe R 120/200; DIF effective R 100. |
| anchor_wording | `stable` | Stable anchors: C01;C04;C05;C07. |
| dif_wording | `localized` | Top threshold-DIF items: C02;C06. |
| global_invariance_wording | `downgrade_to_uncertain` | Configural converged 120/200; stable-ladder effective R 197. |
| full_method_gate | `keep_blocked` | MV14 checks Y-layer measurement uncertainty, not X-to-theta prediction or cross-dataset calibration. |

## Interpretation Boundary

- MV14 is label-only measurement uncertainty evidence, not multimodal method evidence.
- Model-selection and LRT summaries are convergence-safe: non-converged fits remain visible in attempted/failed denominators and do not enter AIC/BIC or LRT decisions.
- Do not summarize MV14 as a global partial-invariance win; use item-level wording around stable anchors, sparse loading DIF, localized C02/C06 threshold non-equivalence, and global model-selection uncertainty.
- Public outputs contain aggregate counts, frequencies, intervals, version rows, and bounded warning categories only.
- Local item-response matrices, resampling draws, fitted parameters, CI values, factor/theta scores, model objects, and detailed logs are not tracked.
- Full method construction remains blocked pending later predeclared MV15/MV16-style evidence.
