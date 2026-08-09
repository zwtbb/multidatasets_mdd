# P5_MV06 Human Review Pack

Generated: `2026-08-09T16:38:54+00:00`

This helper joins the local human annotation workbench with the local AI triage workbook. It is a review accelerator only; AI suggestions are not human annotation or agreement evidence.

## Summary

- Review pack status: `ready_for_human_review_pack_not_claimable`.
- Candidate count: `144`.
- Annotation rows: `288`.
- AI keyword-match candidates: `79`.
- Completed human candidates currently visible in source workbook: `30`.
- Double-completed human candidates currently visible in source workbook: `20`.
- Artifact hygiene passed: `True`.

A local review pack now combines AI suggestions, human annotation fields, and priority ranks. It can speed manual review but does not satisfy MV06 annotation, agreement, or RQ4 evidence gates.

## Aggregate Review Summary

| dataset | target family | bucket | candidates | priority 1/2 | AI keyword | AI protocol artifact | complete once | double complete |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| cmdc | construct | high_prediction_error | 5 | 5 | 1 | 0 | 3 | 2 |
| cmdc | construct | high_true_severity | 8 | 5 | 5 | 1 | 0 | 0 |
| cmdc | construct | low_prediction_error | 6 | 0 | 5 | 1 | 3 | 2 |
| cmdc | hamd_construct_proxy | high_prediction_error | 7 | 7 | 1 | 1 | 0 | 0 |
| cmdc | hamd_construct_proxy | high_true_severity | 7 | 3 | 2 | 0 | 3 | 2 |
| cmdc | hamd_construct_proxy | low_prediction_error | 9 | 1 | 5 | 1 | 0 | 0 |
| cmdc | hamd_item | high_prediction_error | 8 | 8 | 1 | 0 | 3 | 2 |
| cmdc | hamd_item | high_true_severity | 5 | 2 | 1 | 0 | 0 | 0 |
| cmdc | hamd_item | low_prediction_error | 5 | 1 | 1 | 0 | 2 | 2 |
| edaic | construct | high_prediction_error | 8 | 8 | 6 | 0 | 1 | 0 |
| edaic | construct | high_true_severity | 8 | 5 | 5 | 0 | 3 | 2 |
| edaic | construct | low_prediction_error | 8 | 0 | 3 | 0 | 0 | 0 |
| pdch | hamd_construct_proxy | high_prediction_error | 10 | 10 | 9 | 0 | 3 | 2 |
| pdch | hamd_construct_proxy | high_true_severity | 9 | 8 | 8 | 0 | 2 | 1 |
| pdch | hamd_construct_proxy | low_prediction_error | 13 | 1 | 11 | 0 | 3 | 2 |
| pdch | hamd_item | high_prediction_error | 10 | 10 | 4 | 0 | 1 | 1 |
| pdch | hamd_item | high_true_severity | 11 | 7 | 7 | 0 | 3 | 2 |
| pdch | hamd_item | low_prediction_error | 7 | 1 | 4 | 0 | 0 | 0 |

## Priority Bands

| priority band | dataset | candidates | mean abs error | AI keyword |
| --- | --- | ---: | ---: | ---: |
| priority_1_immediate | cmdc | 15 | 3.1954 | 3 |
| priority_1_immediate | edaic | 6 | 3.0000 | 6 |
| priority_1_immediate | pdch | 17 | 2.7001 | 17 |
| priority_2_high | cmdc | 17 | 2.7658 | 8 |
| priority_2_high | edaic | 7 | 2.7003 | 5 |
| priority_2_high | pdch | 20 | 2.2833 | 13 |
| priority_3_balanced | cmdc | 21 | 1.3153 | 11 |
| priority_3_balanced | edaic | 6 | 1.1353 | 3 |
| priority_3_balanced | pdch | 18 | 0.6380 | 13 |
| priority_4_holdout | cmdc | 7 | 0.0150 | 0 |
| priority_4_holdout | edaic | 5 | 0.0000 | 0 |
| priority_4_holdout | pdch | 5 | 0.0001 | 0 |

## Use Policy

- Fill or correct human decisions in the original ignored workbench before running the summary gate.
- Do not copy AI suggestion fields into evidence fields without human verification.
- Commit only aggregate summaries; keep the local pack, candidate index, snippets, and source locators out of Git.
