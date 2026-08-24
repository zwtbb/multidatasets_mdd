# P5 MV19 PHQ Finite-Sample Psychometric Simulation

Generated: `2026-08-21T19:10:57+00:00`

## Scope

MV19 is a label-only observed-N simulation for the E-DAIC/CMDC PHQ C01-C08 measurement line. It retains dataset-specific sample sizes and severity composition, then compares a scalar-invariant world with an observed-like C02/C06 threshold-DIF world.

## Verdict

- Status: `complete_mv19_high_false_localization_downgrade_c02_c06`.
- H0 C02/C06 both-flag false rate: `0.208`.
- H0 C02/C06 top-two false-localization rate: `0.034`.
- H1 C02/C06 both-flag recovery rate: `0.662`.
- H1 C02/C06 top-two recovery rate: `0.222`.
- H1 anchor subset recovery rate for C01/C04/C05/C07: `0.178`.
- Artifact hygiene passed: `True`.

## World Summary

| world | simulations | any threshold flag | C02/C06 both flagged | C02/C06 top-two | anchor subset |
| --- | ---: | ---: | ---: | ---: | ---: |
| `H0_scalar_invariant` | 500 | 0.988 | 0.208 | 0.034 | 0.116 |
| `H1_C02_C06_threshold_DIF` | 500 | 0.998 | 0.662 | 0.222 | 0.178 |

## Item Flag Rates

| world | item | target | anchor | threshold flag | anchor candidate | top-two delta |
| --- | --- | --- | --- | ---: | ---: | ---: |
| `H0_scalar_invariant` | C01 depressed_mood | `False` | `True` | 0.432 | 0.568 | 0.208 |
| `H0_scalar_invariant` | C02 anhedonia | `True` | `False` | 0.416 | 0.584 | 0.224 |
| `H0_scalar_invariant` | C03 sleep | `False` | `False` | 0.466 | 0.534 | 0.268 |
| `H0_scalar_invariant` | C04 fatigue | `False` | `True` | 0.428 | 0.572 | 0.214 |
| `H0_scalar_invariant` | C05 appetite | `False` | `True` | 0.386 | 0.614 | 0.176 |
| `H0_scalar_invariant` | C06 self_worth | `True` | `False` | 0.498 | 0.502 | 0.300 |
| `H0_scalar_invariant` | C07 concentration | `False` | `True` | 0.388 | 0.612 | 0.200 |
| `H0_scalar_invariant` | C08 psychomotor | `False` | `False` | 0.600 | 0.396 | 0.410 |
| `H1_C02_C06_threshold_DIF` | C01 depressed_mood | `False` | `True` | 0.374 | 0.626 | 0.102 |
| `H1_C02_C06_threshold_DIF` | C02 anhedonia | `True` | `False` | 0.800 | 0.200 | 0.530 |
| `H1_C02_C06_threshold_DIF` | C03 sleep | `False` | `False` | 0.474 | 0.526 | 0.178 |
| `H1_C02_C06_threshold_DIF` | C04 fatigue | `False` | `True` | 0.380 | 0.620 | 0.104 |
| `H1_C02_C06_threshold_DIF` | C05 appetite | `False` | `True` | 0.346 | 0.654 | 0.102 |
| `H1_C02_C06_threshold_DIF` | C06 self_worth | `True` | `False` | 0.808 | 0.192 | 0.560 |
| `H1_C02_C06_threshold_DIF` | C07 concentration | `False` | `True` | 0.408 | 0.592 | 0.110 |
| `H1_C02_C06_threshold_DIF` | C08 psychomotor | `False` | `False` | 0.636 | 0.364 | 0.314 |

## Gate Recommendations

| recommendation | status | evidence |
| --- | --- | --- |
| finite_sample_boundary | `complete_mv19_high_false_localization_downgrade_c02_c06` | H0 C02/C06 both-flag false rate 0.208; H1 C02/C06 both-flag recovery 0.662. |
| c02_c06_wording | `downgrade_or_hypothesis_generating` | False-localization gate=False; target-recovery gate=False. |
| anchor_wording | `downgrade` | H1 anchor subset recovery 0.178. |
| full_method_gate | `keep_blocked` | MV19 is a label-only measurement-sensitivity analysis; it reads no multimodal features. |

## Interpretation Boundary

- MV19 tests finite-sample behavior of the current label-only MV10 screen; it is not a full external mirt bootstrap and not a multimodal method result.
- The PHQ result should remain dataset-group measurement-shift wording, not a clean PHQ-8 versus PHQ-9 scale-specific claim.
- Participant-grain observed rows, simulated rows, generation coefficients, and per-draw diagnostics remain local-only or in-memory.
