# P5 MV20 Criterion-Overlap Intervention

Generated: `2026-08-22T11:10:19+00:00`

## Scope

MV20 is a bounded stress test for target-scale semantic overlap. It does not train a new architecture, tune overlap thresholds by outcome, or use E-DAIC position proxies as prompt units.

## Design

- Primary dataset: CMDC.
- Primary encoder: BGE-M3.
- Sensitivity encoder: multilingual-E5-base.
- Primary threshold: top 20 percent criterion-overlap question-position units.
- Sensitivity thresholds: top 10 percent and top 30 percent.
- Main contrast: deletion of high-overlap units versus equal-count random non-high-overlap deletion.
- Stop rule: freeze experiments after MV20 regardless of positive, negative, or encoder-dependent result.

## Feasibility Boundary

- CMDC is included because it exposes stable Q1-Q12 question-position units.
- PDCH is excluded because its available text units are coarse consultation segments rather than clean question units.
- E-DAIC is excluded because the available transcript contract does not expose true prompt/speaker units.

## Primary Gate

| gate | status | excess loss | ci low | ci high | high-only power | retained fraction |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| `primary_bge_m3_cmdc_phq9_top20` | `no_excess_criterion_overlap_evidence` | 0.150 | -0.320 | 0.671 | 0.790 | 0.250 |
| `sensitivity_multilingual_e5_cmdc_phq9_top20` | `no_excess_criterion_overlap_evidence` | 0.353 | -0.017 | 0.725 | 0.788 | 0.250 |

## Top-20 PHQ Snapshot

| encoder | all MAE | minus-high MAE | minus-random MAE | high-only MAE | excess loss | status |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| `bge_m3` | 3.571 | 3.918 | 3.768 | 4.215 | 0.150 | `no_excess_criterion_overlap_evidence` |
| `multilingual_e5_base` | 3.642 | 4.080 | 3.727 | 4.276 | 0.353 | `no_excess_criterion_overlap_evidence` |

## Decision

- Status: `complete_mv20_no_primary_criterion_overlap_excess`.
- Primary gate: `no_excess_criterion_overlap_evidence`.
- Sensitivity gate: `no_excess_criterion_overlap_evidence`.
- Artifact hygiene passed: `True`.

## Output Boundary

- `mv20_predictions.csv` is local-only and ignored by Git.
- Tracked outputs contain aggregate overlap ranks, contracts, metrics, gates, and hygiene only.
