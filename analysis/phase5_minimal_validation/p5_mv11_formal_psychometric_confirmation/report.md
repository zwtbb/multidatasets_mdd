# P5 MV11 Formal Psychometric Confirmation

Generated: `2026-08-11T14:05:00+00:00`

## Scope

MV11 is a label-only multi-group graded-response IRT confirmation over E-DAIC PHQ-8 and CMDC PHQ-9 shared C01-C08 items. It does not read multimodal features, raw text/media, row-level predictions, or private review material.

## Verdict

- Status: `complete_formal_partial_invariance_supported_with_bic_caveat`.
- Model family: `multi_group_graded_response_mml`.
- Optimizer all success: `True`.
- Best BIC model: `scalar`.
- Best AIC model: `partial_mv10`.
- Confirmed MV10 anchors: `4/3` required.
- Loading DIF flagged items: `0`.
- Threshold DIF flagged items: `2`.
- Artifact hygiene passed: `True`.

## Core Model Fits

| model | parameters | log-likelihood | AIC | BIC | optimizer | boundary count |
| --- | ---: | ---: | ---: | ---: | --- | ---: |
| configural | 64 | -2030.024 | 4188.047 | 4424.230 | `True` | 1 |
| metric | 56 | -2037.776 | 4187.551 | 4394.212 | `True` | 0 |
| partial_mv10 | 45 | -2041.374 | 4172.748 | 4338.814 | `True` | 0 |
| scalar | 32 | -2066.193 | 4196.387 | 4314.478 | `True` | 0 |

## Invariance Comparisons

| comparison | decision | LR | df | p | delta BIC restricted-minus-full |
| --- | --- | ---: | ---: | ---: | ---: |
| metric_vs_configural | `no_strong_evidence_against_restriction` | 15.504 | 8 | 0.0501 | -30.019 |
| scalar_vs_metric | `restricted_model_rejected_lrt_only` | 56.835 | 24 | 0.0002 | -79.733 |
| partial_mv10_vs_scalar | `restricted_model_rejected_lrt_only` | 49.639 | 13 | 0.0000 | -24.336 |
| partial_mv10_vs_configural | `no_strong_evidence_against_restriction` | 22.701 | 19 | 0.2508 | -85.416 |
| partial_mv10_vs_metric_nonnested | `nonnested_bic_prefers_partial_mv10_aic_prefers_partial_mv10` | NA |  | NA | -55.398 |

## Anchor Confirmation

| item | MV10 role | MV11 formal role | loading DIF | threshold DIF |
| --- | --- | --- | --- | --- |
| C01 depressed_mood | `anchor_candidate` | `formal_anchor_supported` | `False` | `False` |
| C02 anhedonia | `metric_only_threshold_free` | `formal_metric_only_threshold_free` | `False` | `True` |
| C03 sleep | `metric_only_threshold_free` | `formal_anchor_supported` | `False` | `False` |
| C04 fatigue | `anchor_candidate` | `formal_anchor_supported` | `False` | `False` |
| C05 appetite | `anchor_candidate` | `formal_anchor_supported` | `False` | `False` |
| C06 self_worth | `metric_only_threshold_free` | `formal_metric_only_threshold_free` | `False` | `True` |
| C07 concentration | `anchor_candidate` | `formal_anchor_supported` | `False` | `False` |
| C08 psychomotor | `free_loading_or_threshold` | `formal_anchor_supported` | `False` | `False` |

## Gate Recommendations

| recommendation | status | evidence |
| --- | --- | --- |
| formal_irt_boundary | `formal_grm_mml_completed` | 20 model fits completed; optimizer_all_success=True. |
| partial_anchor_map | `complete_formal_partial_invariance_supported_with_bic_caveat` | Confirmed MV10 anchors: C01;C04;C05;C07; revised/free items: C02;C06. |
| two_stage_latent_target | `ready_to_predeclare_two_stage_latent_target_with_bic_caveat` | MV11 status complete_formal_partial_invariance_supported_with_bic_caveat; confirmed MV10 anchors 4/3 required. |
| full_method_gate | `keep_blocked` | MV11 is label-only; it does not test multimodal prediction, feature identity, or external transfer. |

## Interpretation Boundary

- MV11 is a formal label-only graded-response IRT confirmation, not an external lavaan/mirt run.
- No fitted item parameters, subject-level factor scores, posterior scores, or row diagnostics are exported.
- Full method construction remains blocked until a two-stage latent-target predictor is predeclared, run, and conditionally identity-audited.
