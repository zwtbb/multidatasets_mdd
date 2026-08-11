# P5 MV14 Measurement-Uncertainty Bootstrap Design

Generated: `2026-08-11T16:58:06+00:00`

## Decision

- Design status: `ready_to_implement_mv14_measurement_uncertainty_bootstrap`.
- MV14 runtime ready: `True`.
- Full method allowed: `False`.
- Artifact hygiene passed: `True`.

MV14 is predeclared as a measurement-stability audit for the PHQ E-DAIC/CMDC anchor and DIF story. It is not a multimodal model and it does not authorize the full method.

## Source Evidence

| source | status | observation |
| --- | --- | --- |
| MV10_approximate_phq_screen | `complete_partial_invariance_supported_approx` | loading_congruence=0.998; metric_items=7/8; threshold_items=4/8; candidate_anchors=C01;C04;C05;C07 |
| MV11_formal_phq_confirmation | `complete_formal_partial_invariance_supported_with_bic_caveat` | confirmed_anchors=4; loading_DIF_flags=0; threshold_DIF_flags=2; AIC_BIC_split=True |
| MV13_external_mirt_replication | `complete_external_mirt_with_convergence_warnings` | subjects_edaic=219; subjects_cmdc=77; confirmed_anchors=C01;C04;C05;C07; loading_DIF=none; threshold_DIF=C02;C06 |
| MV13_convergence_caveat | `needs_uncertainty_context` | configural_fit_success=True; configural_converged=False; configural_iterations=3000; core_converged=False |
| MV13_model_selection | `single_fit_reference` | best_AIC=partial_mv10; best_BIC=scalar; core_models=4 |
| MV13_parameter_and_itemfit_availability | `available_aggregate_only` | se_fit_success=True; finite_SE_count=45; itemfit_status=available |
| MV13_input_counts | `groupwise_resampling_basis` | edaic=219; cmdc=77 |
| full_method_gate_next_action | `NEXT_IMPLEMENT_MV14_MEASUREMENT_UNCERTAINTY_BOOTSTRAP` | full_gate_status=blocked_but_publishable_diagnostic_direction; full_method_allowed=False; top_next_action=NEXT_IMPLEMENT_MV14_MEASUREMENT_UNCERTAINTY_BOOTSTRAP |
| runtime_preflight | `pass` | runtime=ready |

## Bootstrap Ladder

| tier | R | role | models |
| --- | ---: | --- | --- |
| MV14_A_smoke_runtime | 10 | not_claimable_smoke | configural;metric;scalar;partial_mv10 |
| MV14_B_core_model_stability | 200 | primary_core_stability | configural;metric;scalar;partial_mv10 |
| MV14_C_item_DIF_stability | 100 | primary_anchor_and_DIF_stability | core_ladder_plus_loading_free_one_item_and_threshold_free_one_item_models |
| MV14_D_boot_mirt_SE_availability | 100 | optional_parameter_uncertainty_availability | partial_mv10_with_boot_fun_returning_aggregate_counts_only |
| MV14_E_parametric_LR_sensitivity | 100 | optional_nested_LRT_uncertainty | metric_vs_configural;scalar_vs_metric;partial_mv10_vs_configural_where_valid |

## Stability Metrics

| metric | tier | interpretation rule |
| --- | --- | --- |
| core_convergence_frequency | MV14_B_core_model_stability | Low or uneven convergence downgrades item-level wording before any anchor/DIF interpretation. |
| model_selection_frequency | MV14_B_core_model_stability | Report AIC/BIC disagreement as part of the result; do not force a single winner. |
| anchor_support_frequency | MV14_C_item_DIF_stability | MV10 anchors C01/C04/C05/C07 need high support before being described as stable anchors. |
| loading_DIF_flag_frequency | MV14_C_item_DIF_stability | Loading DIF should remain sparse; diffuse loading DIF downgrades the common-metric claim. |
| threshold_DIF_flag_frequency | MV14_C_item_DIF_stability | Strong wording about C02/C06 is allowed only if threshold-DIF frequency remains concentrated there. |
| CI_or_SE_availability | MV14_D_boot_mirt_SE_availability | Use as uncertainty availability, not as a public parameter appendix unless separately approved. |
| itemfit_flag_frequency | MV14_C_item_DIF_stability | Item-fit instability is a caveat on item-level DIF interpretation. |
| mv11_mv13_mv14_alignment | MV14_B_core_model_stability;MV14_C_item_DIF_stability | Disagreement revises manuscript wording rather than being hidden. |

## Gates

| gate | status | future execution rule |
| --- | --- | --- |
| G0_predeclaration_complete | `pass` | Execution must either follow this contract or supersede it with a newer dated predeclaration before running. |
| G1_runtime_ready | `pass` | Any missing optional function must be replaced by the MV13 one-free refit ladder or documented as skipped aggregate-only. |
| G2_local_only_boundary | `pass_for_design` | Artifact hygiene must fail if these artifacts enter tracked outputs. |
| G3_convergence_visibility | `pending_bootstrap_run` | Report convergence frequency for every core model and use effective R after convergence filters. |
| G4_anchor_stability | `pending_bootstrap_run` | All four MV10 anchors should show support frequency >=0.70 for stable-anchor wording; any anchor <0.60 requires downgrade. |
| G5_loading_DIF_sparsity | `pending_bootstrap_run` | No more than one item should exceed loading-DIF frequency 0.50; MV10 anchors should remain below 0.30. |
| G6_threshold_DIF_localization | `pending_bootstrap_run` | C02 and C06 should be the top two threshold-DIF frequencies or both exceed 0.50 while non-target items remain clearly lower. |
| G7_model_selection_uncertainty | `pending_bootstrap_run` | Report AIC and BIC selection frequencies separately; do not require them to agree. |
| G8_no_full_method_authorization | `pass_for_design` | MV14 can support measurement uncertainty language only; it cannot start M0/M1/M2/M3 by itself. |

## Implementation Queue

| rank | action | success gate |
| ---: | --- | --- |
| 1 | Create a Python orchestration runner plus R bootstrap script reusing the MV13 item loader and model syntax. | Smoke tier completes with aggregate-only outputs and no local-only artifacts tracked. |
| 2 | Run MV14_A with R=10 to verify deterministic seeds, timeouts, and warning categorization. | Runtime status is pass; smoke results produce only aggregate diagnostics and hygiene passes. |
| 3 | Run MV14_B with default R=200 for core convergence and model-selection frequencies. | Core stability table reports attempted R, effective R, convergence rates, AIC/BIC frequencies, and uncertainty intervals. |
| 4 | Run MV14_C with default R=100 for anchor, loading-DIF, and threshold-DIF selection frequencies. | Item-level stability table reports support frequencies and explicitly downgrades unstable items. |
| 5 | Run MV14_D/E only if runtime permits and functions are available; otherwise record aggregate skip reasons. | Optional tiers either finish with aggregate availability summaries or are skipped with predeclared reasons. |
| 6 | After MV14 run, refresh full-method gate, issue log, memory, README, and paper scaffolds. | Next action moves from MV14 implementation to MV15/MV16 only if uncertainty wording is coherent. |

## Interpretation Boundary

- Track only aggregate convergence, selection-frequency, stability, and hygiene outputs.
- Keep bootstrap inputs, draw indices, fitted parameters, model objects, scores, and detailed logs local-only.
- If anchor or DIF stability is weak, downgrade item-level DIF language before manuscript drafting.
- Even a successful MV14 keeps full method work blocked until later predeclared MV15/MV16 gates change the boundary.
