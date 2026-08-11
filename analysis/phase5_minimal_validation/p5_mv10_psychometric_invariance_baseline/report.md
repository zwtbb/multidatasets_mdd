# P5 MV10 Psychometric Invariance Baseline

Generated: `2026-08-11T13:51:08+00:00`

## Scope

MV10 is a label-only PHQ-8/PHQ-9 measurement screen. It does not read multimodal features, raw text/media, row-level predictions, or private review material.

## Verdict

- Status: `complete_partial_invariance_supported_approx`.
- Configural screen pass: `True`.
- Loading congruence: `0.998`.
- Metric invariant items: `7/8`.
- Threshold invariant items: `4/8`.
- Anchor candidate items: `4/8`.
- Artifact hygiene passed: `True`.

## Reliability and Dimensionality

| dataset | alpha | eig1/eig2 | min loading | status |
| --- | ---: | ---: | ---: | --- |
| edaic | 0.910 | 6.605 | 0.642 | `configural_screen_pass` |
| cmdc | 0.956 | 10.784 | 0.830 | `configural_screen_pass` |

## Loading Invariance

| item | label | E-DAIC loading | CMDC loading | delta | status |
| --- | --- | ---: | ---: | ---: | --- |
| C01 | depressed_mood | 0.845 | 0.887 | 0.041 | `metric_anchor_candidate` |
| C02 | anhedonia | 0.823 | 0.933 | 0.110 | `metric_anchor_candidate` |
| C03 | sleep | 0.763 | 0.830 | 0.067 | `metric_anchor_candidate` |
| C04 | fatigue | 0.791 | 0.857 | 0.065 | `metric_anchor_candidate` |
| C05 | appetite | 0.791 | 0.886 | 0.095 | `metric_anchor_candidate` |
| C06 | self_worth | 0.817 | 0.877 | 0.060 | `metric_anchor_candidate` |
| C07 | concentration | 0.804 | 0.904 | 0.100 | `metric_anchor_candidate` |
| C08 | psychomotor | 0.642 | 0.848 | 0.206 | `metric_dif_flag` |

## Partial Anchor Candidates

| item | role | max threshold delta |
| --- | --- | ---: |
| C01 depressed_mood | `anchor_candidate` | 0.311 |
| C02 anhedonia | `metric_only_threshold_free` | 1.377 |
| C03 sleep | `metric_only_threshold_free` | 0.370 |
| C04 fatigue | `anchor_candidate` | 0.348 |
| C05 appetite | `anchor_candidate` | 0.331 |
| C06 self_worth | `metric_only_threshold_free` | 1.022 |
| C07 concentration | `anchor_candidate` | 0.172 |
| C08 psychomotor | `free_loading_or_threshold` | 0.599 |

## Stage Summary

| stage | status | evidence |
| --- | --- | --- |
| configural_screen | `pass` | Both datasets pass one-factor screen; loading congruence=0.998. |
| metric_loading_screen | `metric_screen_pass` | 7/8 items within loading delta tolerance 0.2; mean delta=0.093, max delta=0.206. |
| threshold_scalar_screen | `threshold_screen_partial_or_flagged` | 4/8 items within threshold-location tolerance 0.35; mean threshold delta=0.382, max=1.377. |
| partial_invariance_screen | `partial_invariance_screen_pass` | 4/8 items are anchor candidates with both metric and threshold support. |
| next_model_target | `plan_two_stage_latent_target` | Overall MV10 status is complete_partial_invariance_supported_approx. |
| edaic_score_distribution | `complete` | n=219, core total mean=6.639, median=5.000, full total mean=6.639. |
| cmdc_score_distribution | `complete` | n=77, core total mean=6.130, median=2.000, full total mean=6.429. |

## Interpretation Boundary

- This is not a formal multi-group ordinal CFA/IRT result.
- Use the anchor set as a candidate measurement map only after formal psychometric confirmation.
- Keep subject-level factor scores, fitted parameters, row diagnostics, and bootstraps local-only.
- Current candidate anchors: `C01;C04;C05;C07`.
