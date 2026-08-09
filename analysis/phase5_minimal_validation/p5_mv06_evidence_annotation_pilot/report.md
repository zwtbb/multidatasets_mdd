# P5_MV06 Evidence Annotation Pilot

Generated: `2026-08-09T06:03:37+00:00`

## Scope

This pilot prepares a bounded local annotation packet for RQ4 evidence localization. It samples from the local MV06 candidate queue and writes subject-level review files only to ignored local artifacts. Tracked outputs contain aggregate sampling, annotation-field policy, and hygiene checks only.

## Local Packet

- Local annotation packet: `p5_mv06_local_annotation_packet_predictions.csv`.
- Local locator map: `p5_mv06_local_annotation_source_map_predictions.csv`.
- Raw clinical text read: `false`.
- Raw clinical text written: `false`.
- Local file locators in tracked artifacts: `false`.

## Dataset Text Access

| dataset | selected rows | selected subjects | rows with existing text | subjects with existing text | safety-sensitive rows |
| --- | ---: | ---: | ---: | ---: | ---: |
| cmdc | 60 | 19 | 60 | 19 | 6 |
| edaic | 24 | 14 | 24 | 14 | 0 |
| pdch | 60 | 27 | 60 | 27 | 6 |

## Sampling Summary

| dataset | target family | bucket | rows | subjects | targets | with text |
| --- | --- | --- | ---: | ---: | ---: | ---: |
| cmdc | construct | high_prediction_error | 5 | 3 | 5 | 5 |
| cmdc | construct | high_true_severity | 8 | 6 | 8 | 8 |
| cmdc | construct | low_prediction_error | 6 | 3 | 6 | 6 |
| cmdc | hamd_construct_proxy | high_prediction_error | 7 | 5 | 7 | 7 |
| cmdc | hamd_construct_proxy | high_true_severity | 7 | 2 | 7 | 7 |
| cmdc | hamd_construct_proxy | low_prediction_error | 9 | 7 | 9 | 9 |
| cmdc | hamd_item | high_prediction_error | 8 | 5 | 8 | 8 |
| cmdc | hamd_item | high_true_severity | 5 | 2 | 5 | 5 |
| cmdc | hamd_item | low_prediction_error | 5 | 5 | 5 | 5 |
| edaic | construct | high_prediction_error | 8 | 3 | 8 | 8 |
| edaic | construct | high_true_severity | 8 | 7 | 8 | 8 |
| edaic | construct | low_prediction_error | 8 | 7 | 8 | 8 |
| pdch | hamd_construct_proxy | high_prediction_error | 10 | 5 | 10 | 10 |
| pdch | hamd_construct_proxy | high_true_severity | 9 | 8 | 9 | 9 |
| pdch | hamd_construct_proxy | low_prediction_error | 13 | 10 | 13 | 13 |
| pdch | hamd_item | high_prediction_error | 10 | 8 | 10 | 10 |
| pdch | hamd_item | high_true_severity | 11 | 10 | 11 | 11 |
| pdch | hamd_item | low_prediction_error | 7 | 6 | 7 | 7 |

## Decision

- Pilot status: `ready_for_manual_local_annotation`.
- Use this as a manual evidence-review packet, not as model-training supervision.
- C09/HAMD03 rows are marked explicit-evidence-only.
- Do not make evidence-localization claims until local annotations are completed and aggregated agreement/error summaries pass hygiene review.

## Hygiene

- Artifact hygiene passed: `True`.
- Versionable files contain no raw snippets, no local source locators, and no subject-level candidate rows.
