# P5_MV06 Evidence Annotation Summary Gate

Generated: `2026-08-11T11:30:25+00:00`

## Scope

This gate validates the local MV06 annotation packet and exports only aggregate annotation completion, evidence-field, prompt-artifact, and agreement summaries. It does not read raw clinical text, local source locators, or raw snippets.

## Decision

- Annotation summary status: `ready_for_aggregate_evidence_review`.
- Completed candidates: `30`.
- Double-annotated candidates: `20`.
- Artifact hygiene passed: `True`.

Aggregate annotation counts and pairwise agreement are ready for human review; raw snippets and subject-level rows remain local-only.

## Completion By Dataset

| dataset | target family | bucket | candidates | complete rows | candidates complete | candidates double-complete |
| --- | --- | --- | ---: | ---: | ---: | ---: |
| cmdc | construct | high_prediction_error | 5 | 5 | 3 | 2 |
| cmdc | construct | high_true_severity | 8 | 0 | 0 | 0 |
| cmdc | construct | low_prediction_error | 6 | 5 | 3 | 2 |
| cmdc | hamd_construct_proxy | high_prediction_error | 7 | 0 | 0 | 0 |
| cmdc | hamd_construct_proxy | high_true_severity | 7 | 5 | 3 | 2 |
| cmdc | hamd_construct_proxy | low_prediction_error | 9 | 0 | 0 | 0 |
| cmdc | hamd_item | high_prediction_error | 8 | 5 | 3 | 2 |
| cmdc | hamd_item | high_true_severity | 5 | 0 | 0 | 0 |
| cmdc | hamd_item | low_prediction_error | 5 | 4 | 2 | 2 |
| edaic | construct | high_prediction_error | 8 | 1 | 1 | 0 |
| edaic | construct | high_true_severity | 8 | 5 | 3 | 2 |
| edaic | construct | low_prediction_error | 8 | 0 | 0 | 0 |
| pdch | hamd_construct_proxy | high_prediction_error | 10 | 5 | 3 | 2 |
| pdch | hamd_construct_proxy | high_true_severity | 9 | 3 | 2 | 1 |
| pdch | hamd_construct_proxy | low_prediction_error | 13 | 5 | 3 | 2 |
| pdch | hamd_item | high_prediction_error | 10 | 2 | 1 | 1 |
| pdch | hamd_item | high_true_severity | 11 | 5 | 3 | 2 |
| pdch | hamd_item | low_prediction_error | 7 | 0 | 0 | 0 |

## Field Issues

| issue type | field | rows | release policy |
| --- | --- | ---: | --- |
| missing_value | evidence_presence | 238 | not_claimable_until_completed |
| missing_value | evidence_source | 238 | not_claimable_until_completed |
| missing_value | evidence_strength | 238 | not_claimable_until_completed |
| missing_value | time_status | 238 | not_claimable_until_completed |
| missing_value | prompt_artifact | 238 | not_claimable_until_completed |

## Agreement

| dataset | field | pair count | observed agreement | pairwise kappa | status |
| --- | --- | ---: | ---: | ---: | --- |
| ALL | evidence_presence | 20 | 0.900 | 0.808 | computed_pairwise_kappa |
| ALL | evidence_source | 20 | 1.000 | 1.000 | computed_pairwise_kappa |
| ALL | evidence_strength | 20 | 1.000 | 1.000 | computed_pairwise_kappa |
| ALL | time_status | 20 | 1.000 | 1.000 | computed_pairwise_kappa |
| ALL | prompt_artifact | 20 | 0.950 | 0.925 | computed_pairwise_kappa |
| cmdc | evidence_presence | 10 | 0.800 | 0.643 | computed_pairwise_kappa |
| cmdc | evidence_source | 10 | 1.000 | 1.000 | computed_pairwise_kappa |
| cmdc | evidence_strength | 10 | 1.000 | 1.000 | computed_pairwise_kappa |
| cmdc | time_status | 10 | 1.000 | 1.000 | computed_pairwise_kappa |
| cmdc | prompt_artifact | 10 | 1.000 | 1.000 | computed_pairwise_kappa |
| edaic | evidence_presence | 2 | 1.000 |  | undefined_degenerate_marginals |
| edaic | evidence_source | 2 | 1.000 |  | undefined_degenerate_marginals |
| edaic | evidence_strength | 2 | 1.000 |  | undefined_degenerate_marginals |
| edaic | time_status | 2 | 1.000 |  | undefined_degenerate_marginals |
| edaic | prompt_artifact | 2 | 1.000 |  | undefined_degenerate_marginals |
| pdch | evidence_presence | 8 | 1.000 | 1.000 | computed_pairwise_kappa |
| pdch | evidence_source | 8 | 1.000 | 1.000 | computed_pairwise_kappa |
| pdch | evidence_strength | 8 | 1.000 | 1.000 | computed_pairwise_kappa |
| pdch | time_status | 8 | 1.000 | 1.000 | computed_pairwise_kappa |
| pdch | prompt_artifact | 8 | 0.875 | 0.692 | computed_pairwise_kappa |

## Release Rule

- Do not claim RQ4 evidence-localization validity while status is blocked.
- Commit only aggregate outputs from this directory.
- Keep local snippets, local notes, local source locators, and subject-level candidate rows out of Git.
