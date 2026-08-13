# P5_MV06 Evidence Annotation Summary Gate

Generated: `2026-08-13T05:19:02+00:00`

## Scope

This gate validates the local MV06 annotation packet and exports only aggregate annotation completion, evidence-field, prompt-artifact, and agreement summaries. It does not read raw clinical text, local source locators, or raw snippets.

## Decision

- Annotation summary status: `ready_for_aggregate_evidence_review`.
- Completed candidates: `143`.
- Double-annotated candidates: `143`.
- Artifact hygiene passed: `True`.

Aggregate annotation counts and pairwise agreement are ready for human review; raw snippets and subject-level rows remain local-only.

## Completion By Dataset

| dataset | target family | bucket | candidates | complete rows | candidates complete | candidates double-complete |
| --- | --- | --- | ---: | ---: | ---: | ---: |
| cmdc | construct | high_prediction_error | 5 | 10 | 5 | 5 |
| cmdc | construct | high_true_severity | 8 | 14 | 7 | 7 |
| cmdc | construct | low_prediction_error | 6 | 12 | 6 | 6 |
| cmdc | hamd_construct_proxy | high_prediction_error | 7 | 14 | 7 | 7 |
| cmdc | hamd_construct_proxy | high_true_severity | 7 | 14 | 7 | 7 |
| cmdc | hamd_construct_proxy | low_prediction_error | 9 | 18 | 9 | 9 |
| cmdc | hamd_item | high_prediction_error | 8 | 16 | 8 | 8 |
| cmdc | hamd_item | high_true_severity | 5 | 10 | 5 | 5 |
| cmdc | hamd_item | low_prediction_error | 5 | 10 | 5 | 5 |
| edaic | construct | high_prediction_error | 8 | 16 | 8 | 8 |
| edaic | construct | high_true_severity | 8 | 16 | 8 | 8 |
| edaic | construct | low_prediction_error | 8 | 16 | 8 | 8 |
| pdch | hamd_construct_proxy | high_prediction_error | 10 | 20 | 10 | 10 |
| pdch | hamd_construct_proxy | high_true_severity | 9 | 18 | 9 | 9 |
| pdch | hamd_construct_proxy | low_prediction_error | 13 | 26 | 13 | 13 |
| pdch | hamd_item | high_prediction_error | 10 | 20 | 10 | 10 |
| pdch | hamd_item | high_true_severity | 11 | 22 | 11 | 11 |
| pdch | hamd_item | low_prediction_error | 7 | 14 | 7 | 7 |

## Field Issues

| issue type | field | rows | release policy |
| --- | --- | ---: | --- |
| missing_value | evidence_presence | 2 | not_claimable_until_completed |
| missing_value | evidence_source | 2 | not_claimable_until_completed |
| missing_value | evidence_strength | 2 | not_claimable_until_completed |
| missing_value | time_status | 2 | not_claimable_until_completed |
| missing_value | prompt_artifact | 2 | not_claimable_until_completed |

## Agreement

| dataset | field | pair count | observed agreement | pairwise kappa | status |
| --- | --- | ---: | ---: | ---: | --- |
| ALL | evidence_presence | 143 | 0.979 | 0.965 | computed_pairwise_kappa |
| ALL | evidence_source | 143 | 0.986 | 0.973 | computed_pairwise_kappa |
| ALL | evidence_strength | 143 | 0.965 | 0.933 | computed_pairwise_kappa |
| ALL | time_status | 143 | 0.979 | 0.968 | computed_pairwise_kappa |
| ALL | prompt_artifact | 143 | 0.986 | 0.978 | computed_pairwise_kappa |
| cmdc | evidence_presence | 59 | 0.983 | 0.967 | computed_pairwise_kappa |
| cmdc | evidence_source | 59 | 0.966 | 0.929 | computed_pairwise_kappa |
| cmdc | evidence_strength | 59 | 0.966 | 0.929 | computed_pairwise_kappa |
| cmdc | time_status | 59 | 1.000 | 1.000 | computed_pairwise_kappa |
| cmdc | prompt_artifact | 59 | 0.966 | 0.931 | computed_pairwise_kappa |
| edaic | evidence_presence | 24 | 0.917 | 0.846 | computed_pairwise_kappa |
| edaic | evidence_source | 24 | 1.000 |  | undefined_degenerate_marginals |
| edaic | evidence_strength | 24 | 0.917 | 0.833 | computed_pairwise_kappa |
| edaic | time_status | 24 | 0.958 | 0.932 | computed_pairwise_kappa |
| edaic | prompt_artifact | 24 | 1.000 | 1.000 | computed_pairwise_kappa |
| pdch | evidence_presence | 60 | 1.000 | 1.000 | computed_pairwise_kappa |
| pdch | evidence_source | 60 | 1.000 | 1.000 | computed_pairwise_kappa |
| pdch | evidence_strength | 60 | 0.983 | 0.960 | computed_pairwise_kappa |
| pdch | time_status | 60 | 0.967 | 0.951 | computed_pairwise_kappa |
| pdch | prompt_artifact | 60 | 1.000 | 1.000 | computed_pairwise_kappa |

## Release Rule

- Do not claim RQ4 evidence-localization validity while status is blocked.
- Commit only aggregate outputs from this directory.
- Keep local snippets, local notes, local source locators, and subject-level candidate rows out of Git.
