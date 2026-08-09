# P5_MV06 Evidence Localization Readiness

Generated: `2026-08-09T05:48:54+00:00`

## Scope

This audit prepares RQ4 evidence localization without exporting raw snippets or source paths. It links only aggregate text availability, local prediction availability, and candidate sampling policy.

## Dataset Coverage

| dataset | text subjects existing | prediction subjects | overlap | constructs | readiness |
| --- | ---: | ---: | ---: | ---: | --- |
| edaic | 275 | 56 | 56 | 8 | ready_text_localization_core_c01_c08 |
| cmdc | 77 | 77 | 77 | 13 | ready_limited_text_localization |
| pdch | 99 | 99 | 99 | 13 | ready_hamd_text_localization |

## Candidate Queue Summary

| dataset | target family | bucket | candidate rows | candidate subjects | targets |
| --- | --- | --- | ---: | ---: | ---: |
| cmdc | construct | high_prediction_error | 56 | 20 | 8 |
| cmdc | construct | high_true_severity | 45 | 18 | 8 |
| cmdc | construct | low_prediction_error | 64 | 26 | 8 |
| cmdc | hamd_construct_proxy | high_prediction_error | 38 | 13 | 13 |
| cmdc | hamd_construct_proxy | high_true_severity | 37 | 15 | 13 |
| cmdc | hamd_construct_proxy | low_prediction_error | 45 | 22 | 13 |
| cmdc | hamd_item | high_prediction_error | 87 | 21 | 17 |
| cmdc | hamd_item | high_true_severity | 60 | 18 | 17 |
| cmdc | hamd_item | low_prediction_error | 95 | 24 | 17 |
| edaic | construct | high_prediction_error | 64 | 29 | 8 |
| edaic | construct | high_true_severity | 34 | 13 | 8 |
| edaic | construct | low_prediction_error | 79 | 31 | 8 |
| pdch | hamd_construct_proxy | high_prediction_error | 22 | 13 | 13 |
| pdch | hamd_construct_proxy | high_true_severity | 48 | 29 | 13 |
| pdch | hamd_construct_proxy | low_prediction_error | 115 | 65 | 13 |
| pdch | hamd_item | high_prediction_error | 42 | 25 | 17 |
| pdch | hamd_item | high_true_severity | 93 | 52 | 17 |
| pdch | hamd_item | low_prediction_error | 133 | 67 | 17 |

## Decision

- MV06 readiness status: `ready_for_local_evidence_annotation`.
- Local candidate file written: `local_only_ignored_predictions_csv`.
- Raw snippets written: `not_written`.
- Source paths written to tracked artifacts: `not_written`.

MV06 can proceed as a local-only evidence annotation workflow for datasets with prediction-text overlap. The next step should sample candidates from the local queue, inspect raw snippets locally, and commit only aggregate evidence agreement statistics.

## Hygiene

- Artifact hygiene passed: `True`.
- Tracked artifacts contain aggregate counts and policy only.
