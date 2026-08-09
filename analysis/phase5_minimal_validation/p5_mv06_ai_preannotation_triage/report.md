# P5_MV06 Local AI Preannotation Triage

Generated: `2026-08-09T09:21:27+00:00`

## Scope

This helper creates local-only AI triage annotations for the MV06 evidence-localization workbench. It is a review accelerator, not human annotation, not agreement evidence, and not an RQ4 claim.

## Decision

- Preannotation status: `ready_for_human_review_not_claimable`.
- Candidate count: `144`.
- Rows with keyword match: `79`.
- Text files scanned locally: `854`.
- Artifact hygiene passed: `True`.

AI triage filled a local-only preannotation workbook. It can accelerate human review, but it does not satisfy MV06 human annotation or agreement gates.

## Dataset Summary

| dataset | target family | bucket | candidates | rows with keyword match |
| --- | --- | --- | ---: | ---: |
| cmdc | construct | high_prediction_error | 5 | 1 |
| cmdc | construct | high_true_severity | 8 | 5 |
| cmdc | construct | low_prediction_error | 6 | 5 |
| cmdc | hamd_construct_proxy | high_prediction_error | 7 | 1 |
| cmdc | hamd_construct_proxy | high_true_severity | 7 | 2 |
| cmdc | hamd_construct_proxy | low_prediction_error | 9 | 5 |
| cmdc | hamd_item | high_prediction_error | 8 | 1 |
| cmdc | hamd_item | high_true_severity | 5 | 1 |
| cmdc | hamd_item | low_prediction_error | 5 | 1 |
| edaic | construct | high_prediction_error | 8 | 6 |
| edaic | construct | high_true_severity | 8 | 5 |
| edaic | construct | low_prediction_error | 8 | 3 |
| pdch | hamd_construct_proxy | high_prediction_error | 10 | 9 |
| pdch | hamd_construct_proxy | high_true_severity | 9 | 8 |
| pdch | hamd_construct_proxy | low_prediction_error | 13 | 11 |
| pdch | hamd_item | high_prediction_error | 10 | 4 |
| pdch | hamd_item | high_true_severity | 11 | 7 |
| pdch | hamd_item | low_prediction_error | 7 | 4 |

## Interpretation Boundary

- The local preannotation CSV may contain raw excerpts and source locators; it is ignored by Git.
- Human reviewers must confirm or correct every AI triage row before MV06 evidence can be used.
- The default MV06 human-annotation summary gate remains the claim boundary.
