# MV21 Measurement-Discrepancy Gradient

- Run id: `P5_MV21_measurement_discrepancy_gradient`
- Generated: `2026-08-24T03:54:50+00:00`
- Status: `complete_descriptive_measurement_gradient_reinforcement`

## Scope

This is a label-only descriptive reinforcement. It does not run HAMD MIM/IRT,
does not fit a new formal psychometric model, and does not treat DAIC-WOZ as
an independent corpus. Severity-conditioned tables use pooled item-excluded
total-score tertiles to avoid the strongest part-whole artifact.

## Input Counts

| Analysis | Dataset | Scale | Complete subjects | Split/filter |
| --- | --- | --- | ---: | --- |
| phq_shared_item | edaic | PHQ-8 | 219 | dev;train |
| phq_shared_item | cmdc | PHQ-9 | 77 | all_valid |
| hamd_same_scale_exploratory | cmdc | HAMD-17 | 25 | all_valid |
| hamd_same_scale_exploratory | pdch | HAMD-17 | 99 | all_valid |
| daicwoz_edaic_same_phq8_lineage_control | daicwoz/edaic | PHQ-8 | 141 paired overlap | train/dev item labels |

## PHQ Shared Items

Top non-sparse severity-conditioned E-DAIC minus CMDC item-mean deltas:

| Item | Bin | n min | Mean delta | P>=2 delta |
| --- | --- | ---: | ---: | ---: |
| C02 anhedonia | high | 25 | -0.834 | -0.408 |
| C08 psychomotor | high | 24 | -0.623 | -0.197 |
| C06 self_worth | middle | 9 | 0.618 | 0.159 |
| C01 depressed_mood | high | 24 | -0.486 | -0.236 |
| C04 fatigue | middle | 19 | 0.457 | 0.088 |
| C06 self_worth | high | 25 | 0.333 | 0.087 |
| C07 concentration | high | 25 | -0.262 | -0.066 |
| C07 concentration | middle | 8 | 0.250 | 0.074 |

## HAMD Same-Scale Control

Top non-sparse severity-conditioned CMDC minus PDCH item-mean deltas:

| Scope | Item | Bin | n min | Mean delta | P>=2 delta |
| --- | --- | --- | ---: | ---: | ---: |
| all_subjects | HAMD07 | high | 6 | -0.967 | -0.100 |
| all_subjects | HAMD11 | high | 7 | -0.911 | -0.161 |
| all_subjects | HAMD01 | low | 8 | 0.895 | 0.533 |
| overlap_mild_moderate | HAMD07 | high | 7 | -0.882 | -0.099 |
| overlap_mild_moderate | HAMD08 | middle | 7 | 0.877 | 0.286 |
| all_subjects | HAMD03 | low | 9 | 0.848 | 0.392 |
| all_subjects | HAMD01 | high | 6 | -0.769 | 0.032 |
| overlap_mild_moderate | HAMD03 | low | 9 | 0.694 | 0.361 |

Top descriptive HAMD correlation-structure deltas:

| Scope | Pair | CMDC rho | PDCH rho | Abs delta |
| --- | --- | ---: | ---: | ---: |
| all_subjects | HAMD07-HAMD09 | -0.456 | 0.256 | 0.712 |
| all_subjects | HAMD06-HAMD17 | -0.394 | 0.257 | 0.651 |
| all_subjects | HAMD09-HAMD10 | -0.090 | 0.551 | 0.641 |
| all_subjects | HAMD01-HAMD11 | -0.197 | 0.433 | 0.630 |
| all_subjects | HAMD01-HAMD13 | -0.098 | 0.456 | 0.553 |
| all_subjects | HAMD14-HAMD17 | 0.386 | -0.164 | 0.550 |
| all_subjects | HAMD04-HAMD11 | -0.290 | 0.258 | 0.548 |
| all_subjects | HAMD04-HAMD05 | -0.140 | 0.403 | 0.543 |

## DAIC-WOZ/E-DAIC Control

DAIC-WOZ and E-DAIC are treated as a same-lineage benchmark/control, not two independent corpora. Across paired train/dev overlapping subjects, minimum item exact-match rate is 0.986 and maximum mean absolute item difference is 0.014. The maximum non-sparse severity-conditioned DAIC-WOZ minus E-DAIC project-contract item-mean delta is 0.118.

## Output Files

- `artifact_hygiene_audit.json`
- `daicwoz_edaic_conditioned_deltas.csv`
- `daicwoz_edaic_contract_distribution.csv`
- `daicwoz_edaic_paired_item_differences.csv`
- `daicwoz_edaic_scope_audit.csv`
- `daicwoz_edaic_severity_conditioned_response.csv`
- `hamd_conditioned_deltas.csv`
- `hamd_item_category_proportions.csv`
- `hamd_item_correlation_delta_summary.csv`
- `hamd_item_correlation_summary.csv`
- `hamd_item_distribution.csv`
- `hamd_scope_audit.csv`
- `hamd_severity_conditioned_response.csv`
- `phq_shared_conditioned_deltas.csv`
- `phq_shared_item_category_proportions.csv`
- `phq_shared_item_distribution.csv`
- `phq_shared_scope_audit.csv`
- `phq_shared_severity_conditioned_response.csv`
- `phq_shared_total_band_summary.csv`
- `report.md`
- `run_summary.json`
