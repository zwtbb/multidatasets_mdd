# P5_MV06 Evidence Annotation Summary Gate

Generated: `2026-08-09T09:22:18+00:00`

## Scope

This gate validates the local MV06 annotation packet and exports only aggregate annotation completion, evidence-field, prompt-artifact, and agreement summaries. It does not read raw clinical text, local source locators, or raw snippets.

## Decision

- Annotation summary status: `blocked_no_completed_annotations`.
- Completed candidates: `0`.
- Double-annotated candidates: `0`.
- Artifact hygiene passed: `True`.

The local annotation workbook has not been filled yet; only completion and field-contract gates are meaningful.

## Completion By Dataset

| dataset | target family | bucket | candidates | complete rows | candidates complete | candidates double-complete |
| --- | --- | --- | ---: | ---: | ---: | ---: |
| cmdc | construct | high_prediction_error | 5 | 0 | 0 | 0 |
| cmdc | construct | high_true_severity | 8 | 0 | 0 | 0 |
| cmdc | construct | low_prediction_error | 6 | 0 | 0 | 0 |
| cmdc | hamd_construct_proxy | high_prediction_error | 7 | 0 | 0 | 0 |
| cmdc | hamd_construct_proxy | high_true_severity | 7 | 0 | 0 | 0 |
| cmdc | hamd_construct_proxy | low_prediction_error | 9 | 0 | 0 | 0 |
| cmdc | hamd_item | high_prediction_error | 8 | 0 | 0 | 0 |
| cmdc | hamd_item | high_true_severity | 5 | 0 | 0 | 0 |
| cmdc | hamd_item | low_prediction_error | 5 | 0 | 0 | 0 |
| edaic | construct | high_prediction_error | 8 | 0 | 0 | 0 |
| edaic | construct | high_true_severity | 8 | 0 | 0 | 0 |
| edaic | construct | low_prediction_error | 8 | 0 | 0 | 0 |
| pdch | hamd_construct_proxy | high_prediction_error | 10 | 0 | 0 | 0 |
| pdch | hamd_construct_proxy | high_true_severity | 9 | 0 | 0 | 0 |
| pdch | hamd_construct_proxy | low_prediction_error | 13 | 0 | 0 | 0 |
| pdch | hamd_item | high_prediction_error | 10 | 0 | 0 | 0 |
| pdch | hamd_item | high_true_severity | 11 | 0 | 0 | 0 |
| pdch | hamd_item | low_prediction_error | 7 | 0 | 0 | 0 |

## Field Issues

| issue type | field | rows | release policy |
| --- | --- | ---: | --- |
| missing_value | evidence_presence | 288 | not_claimable_until_completed |
| missing_value | evidence_source | 288 | not_claimable_until_completed |
| missing_value | evidence_strength | 288 | not_claimable_until_completed |
| missing_value | time_status | 288 | not_claimable_until_completed |
| missing_value | prompt_artifact | 288 | not_claimable_until_completed |

## Agreement

| field | pair count | observed agreement | pairwise kappa | status |
| --- | ---: | ---: | ---: | --- |
| evidence_presence | 0 |  |  | insufficient_pair_annotations |
| evidence_source | 0 |  |  | insufficient_pair_annotations |
| evidence_strength | 0 |  |  | insufficient_pair_annotations |
| time_status | 0 |  |  | insufficient_pair_annotations |
| prompt_artifact | 0 |  |  | insufficient_pair_annotations |

## Release Rule

- Do not claim RQ4 evidence-localization validity while status is blocked.
- Commit only aggregate outputs from this directory.
- Keep local snippets, local notes, local source locators, and subject-level candidate rows out of Git.
