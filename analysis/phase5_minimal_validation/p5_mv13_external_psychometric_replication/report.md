# P5 MV13 External Psychometric Replication

Generated: `2026-08-11T16:36:00+00:00`

## Scope

MV13 uses R `mirt::multipleGroup` to externally replicate the E-DAIC PHQ-8 / CMDC PHQ-9 C01-C08 measurement-invariance conclusion from MV10/MV11. It reads only manifest-governed item labels and writes aggregate outputs.

## Verdict

- Status: `complete_external_mirt_with_convergence_warnings`.
- External engine: `R mirt::multipleGroup`.
- Core fits converged: `False`.
- Best AIC model: `partial_mv10`.
- Best BIC model: `scalar`.
- Confirmed MV10 anchors: `4/3` required.
- Loading DIF flagged items: `0`.
- Threshold DIF flagged items: `2`.
- Parameter CI status: `available_aggregate_only`.
- Item-fit status: `available`.
- Artifact hygiene passed: `True`.

## Core Model Fits

| model | parameters | log-likelihood | AIC | BIC | converged | iterations |
| --- | ---: | ---: | ---: | ---: | --- | ---: |
| configural | 64 | -2028.091 | 4184.182 | 4420.365 | `False` | 3000 |
| metric | 56 | -2037.535 | 4187.070 | 4393.730 | `True` | 223 |
| partial_mv10 | 45 | -2040.981 | 4171.962 | 4338.028 | `True` | 86 |
| scalar | 32 | -2064.964 | 4193.928 | 4312.020 | `True` | 69 |

## Invariance Comparisons

| comparison | decision | LR | df | p | delta BIC restricted-minus-full |
| --- | --- | ---: | ---: | ---: | ---: |
| metric_vs_configural | `no_strong_evidence_against_restriction` | 18.888 | 8 | 0.0155 | -26.635 |
| scalar_vs_metric | `restricted_model_rejected_lrt_only` | 54.858 | 24 | 0.0003 | -81.710 |
| partial_mv10_vs_scalar | `restricted_model_rejected_lrt_only` | 47.966 | 13 | 0.0000 | -26.008 |
| partial_mv10_vs_configural | `no_strong_evidence_against_restriction` | 25.780 | 19 | 0.1364 | -82.337 |
| partial_mv10_vs_metric_nonnested | `nonnested_bic_prefers_partial_mv10_aic_prefers_partial_mv10` | NA |  | NA | -55.702 |

## External Anchor Map

| item | MV10 role | external role | loading DIF | threshold DIF |
| --- | --- | --- | --- | --- |
| C01 depressed_mood | `anchor_candidate` | `external_anchor_supported` | `False` | `False` |
| C02 anhedonia | `metric_only_threshold_free` | `external_metric_only_threshold_free` | `False` | `True` |
| C03 sleep | `metric_only_threshold_free` | `external_anchor_supported` | `False` | `False` |
| C04 fatigue | `anchor_candidate` | `external_anchor_supported` | `False` | `False` |
| C05 appetite | `anchor_candidate` | `external_anchor_supported` | `False` | `False` |
| C06 self_worth | `metric_only_threshold_free` | `external_metric_only_threshold_free` | `False` | `True` |
| C07 concentration | `anchor_candidate` | `external_anchor_supported` | `False` | `False` |
| C08 psychomotor | `free_loading_or_threshold` | `external_anchor_supported` | `False` | `False` |

## MV11 Alignment

| check | MV11 | MV13 | aligned |
| --- | --- | --- | --- |
| anchor_set_overlap | C01;C04;C05;C07 | C01;C04;C05;C07 | `True` |
| loading_dif_overlap | none | none | `True` |
| threshold_dif_overlap | C02;C06 | C02;C06 | `True` |
| metric_vs_configural | no_strong_evidence_against_restriction | no_strong_evidence_against_restriction | `True` |
| scalar_vs_metric | restricted_model_rejected_lrt_only | restricted_model_rejected_lrt_only | `True` |
| partial_mv10_vs_configural | no_strong_evidence_against_restriction | no_strong_evidence_against_restriction | `True` |

## Gate Recommendations

| recommendation | status | evidence |
| --- | --- | --- |
| external_replication_boundary | `complete_external_mirt_with_convergence_warnings` | MV13 status complete_external_mirt_with_convergence_warnings. |
| parameter_ci_boundary | `available_aggregate_only` | Finite SE count in aggregate audit: 45. |
| mv14_measurement_uncertainty | `review_external_mirt_before_bootstrap` | CMDC has 77 PHQ item-labeled subjects, so item-level DIF wording needs uncertainty estimates. |
| full_method_gate | `keep_blocked` | MV13 checks the Y->theta measurement layer, not X->theta prediction or cross-dataset calibration. |

## Interpretation Boundary

- MV13 is an external label-only psychometric replication, not multimodal prediction evidence.
- The local item response matrix is ignored and does not include subject IDs, but still remains local-only because it is participant-grain label data.
- Full item parameters, CI values, fitted mirt objects, factor scores, theta scores, and row diagnostics are not tracked.
- Full method construction remains blocked; the next planned step is MV14 measurement-uncertainty bootstrap.
