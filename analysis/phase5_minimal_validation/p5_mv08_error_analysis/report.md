# P5_MV08 Error Analysis

Generated: `2026-08-11T11:54:39+00:00`

## Decision

- Error-analysis status: `complete_current_mv08_not_claimable_revision_or_freeze`.
- Current MV08 claimable as positive RQ1 evidence: `False`.
- Artifact hygiene passed: `True`.

MV08 error analysis confirms the current partial-invariance ordinal head should be frozen as negative evidence unless a predeclared MV08b revision changes the measurement mechanism. The total-score floor remains the key comparator.

## Pooled Slice Failures

| dataset | scale | M2 row-weighted MAE | delta vs total | delta vs fixed | M2 bias | rounded within 1 |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| cmdc | PHQ-9 | 0.743 | 0.128 | 0.103 | 0.422 | 0.838 |
| edaic | PHQ-8 | 0.842 | 0.147 | 0.140 | 0.417 | 0.850 |
| pdch | HAMD-17 | 0.892 | 0.152 | 0.125 | 0.225 | 0.849 |

## Largest Pooled Item Deltas

| dataset | item | construct | policy | delta vs total | M2 bias | true mean | M2 pred mean |
| --- | --- | --- | --- | ---: | ---: | ---: | ---: |
| cmdc | PHQ9_8 | C08 | shared_phq_anchor | 0.698 | 1.103 | 0.481 | 1.584 |
| cmdc | PHQ9_1 | C02 | shared_phq_anchor | 0.233 | 0.604 | 0.922 | 1.526 |
| cmdc | PHQ9_9 | C09 | scale_specific_safety | 0.200 | 0.316 | 0.299 | 0.614 |
| cmdc | PHQ9_2 | C01 | shared_phq_anchor | 0.105 | 0.537 | 0.857 | 1.394 |
| cmdc | PHQ9_5 | C05 | shared_phq_anchor | 0.098 | 0.346 | 0.805 | 1.152 |
| cmdc | PHQ9_7 | C07 | shared_phq_anchor | 0.069 | 0.471 | 0.701 | 1.173 |
| cmdc | PHQ9_6 | C06 | shared_phq_anchor | -0.027 | 0.092 | 0.558 | 0.650 |
| cmdc | PHQ9_4 | C04 | shared_phq_anchor | -0.109 | 0.185 | 0.922 | 1.107 |

## Threshold Sparsity

| protocol | DIF policy | heads | constant threshold fraction | mean M2 delta vs total |
| --- | --- | ---: | ---: | ---: |
| pdch_hamd_subject_cv | scale_or_item_specific_dif | 17 | 0.318 | 0.118 |
| pooled_partial_invariance | scale_or_item_specific_dif | 17 | 0.318 | 0.152 |
| cmdc_phq_subject_cv | scale_specific_safety | 1 | 0.067 | 0.114 |
| pooled_partial_invariance | scale_specific_safety | 1 | 0.067 | 0.200 |
| cmdc_phq_subject_cv | shared_phq_anchor | 8 | 0.000 | 0.019 |
| edaic_train_dev | shared_phq_anchor | 8 | 0.000 | 0.147 |

## Revision Queue

| priority | action | success gate |
| ---: | --- | --- |
| 1 | Do not claim partial-invariance measurement success from the current frozen-BGE ordinal head. | Use MV08 as negative diagnostic evidence unless a new predeclared MV08b contract changes the measurement mechanism. |
| 2 | If revising, predeclare a total-anchored measurement model that predicts severity first and models item residual structure only when it beats the total floor. | MV08b must beat total-score and fixed-map floors on at least two pooled active slices and avoid higher prediction identity. |
| 3 | Pool thresholds more aggressively, collapse rare score levels, or fit ordinal thresholds jointly instead of independent one-vs-threshold logistic heads. | Threshold diagnostics show fewer constant thresholds and improved item MAE without losing rounded-within-one accuracy. |
| 4 | Keep HAMD as a separate clinical measurement stress test unless a stronger HAMD-compatible feature/measurement contract is introduced. | Any HAMD revision must improve PDCH item and item-derived total metrics beyond total-score and train-mean floors. |

## Interpretation Boundary

- This analysis reads a local ignored row-prediction file but exports only aggregate diagnostics.
- It does not authorize full-method construction or a positive shared-measurement claim.
- Any MV08b revision must be predeclared and compared against the same simple floors.
