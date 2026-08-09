# P5_MV01 PHQ Core Construct Bridge

Generated: `2026-08-05T03:45:55+00:00`

## Scope

This is the first runnable Phase 5 minimal-validation row. It maps E-DAIC PHQ-8 and CMDC PHQ-9 item labels to C01-C08, uses cached frozen WavLM subject features, and trains only shallow Ridge or mean baselines. No encoder fine-tuning, source-data scan, transcript export, or full-method component is used.

## Feature And Split Contract

- Common frozen WavLM columns: `768`.
- E-DAIC subjects joined: `219`; official train/dev only.
- CMDC subjects joined: `77`; Phase 2 5-fold subject CV.
- Subject-overlap violations: `0`.
- Frozen feature dataset identity risk, E-DAIC vs CMDC WavLM balanced accuracy: `1.000`.

## Macro MAE

| protocol | dataset | model | macro MAE | seed count |
| --- | --- | --- | ---: | ---: |
| cmdc_subject_cv | cmdc | dataset_specific_ridge | 0.572 | 5 |
| cmdc_subject_cv | cmdc | total_alloc_ridge | 0.547 | 5 |
| cmdc_subject_cv | cmdc | train_mean | 0.847 | 5 |
| cross_cmdc_to_edaic | edaic | cross_dataset_ridge | 0.998 | 5 |
| cross_cmdc_to_edaic | edaic | total_alloc_ridge | 0.933 | 5 |
| cross_cmdc_to_edaic | edaic | train_mean | 0.743 | 5 |
| cross_edaic_to_cmdc | cmdc | cross_dataset_ridge | 0.805 | 5 |
| cross_edaic_to_cmdc | cmdc | total_alloc_ridge | 0.801 | 5 |
| cross_edaic_to_cmdc | cmdc | train_mean | 0.865 | 5 |
| edaic_same_dataset | edaic | dataset_specific_ridge | 0.751 | 5 |
| edaic_same_dataset | edaic | total_alloc_ridge | 0.746 | 5 |
| edaic_same_dataset | edaic | train_mean | 0.735 | 5 |
| pooled_shared | cmdc | pooled_shared_ridge | 0.615 | 5 |
| pooled_shared | cmdc | total_alloc_ridge | 0.600 | 5 |
| pooled_shared | cmdc | train_mean | 0.857 | 5 |
| pooled_shared | edaic | pooled_shared_ridge | 0.762 | 5 |
| pooled_shared | edaic | total_alloc_ridge | 0.764 | 5 |
| pooled_shared | edaic | train_mean | 0.732 | 5 |

## Deltas

Negative deltas are improvements in MAE.

| protocol | dataset | model | delta vs train_mean | delta vs total_alloc_ridge |
| --- | --- | --- | ---: | ---: |
| cmdc_subject_cv | cmdc | dataset_specific_ridge | -0.275 | 0.025 |
| cmdc_subject_cv | cmdc | total_alloc_ridge | -0.300 | 0.000 |
| cmdc_subject_cv | cmdc | train_mean | 0.000 | 0.300 |
| cross_cmdc_to_edaic | edaic | cross_dataset_ridge | 0.255 | 0.065 |
| cross_cmdc_to_edaic | edaic | total_alloc_ridge | 0.190 | 0.000 |
| cross_cmdc_to_edaic | edaic | train_mean | 0.000 | -0.190 |
| cross_edaic_to_cmdc | cmdc | cross_dataset_ridge | -0.060 | 0.004 |
| cross_edaic_to_cmdc | cmdc | total_alloc_ridge | -0.064 | 0.000 |
| cross_edaic_to_cmdc | cmdc | train_mean | 0.000 | 0.064 |
| edaic_same_dataset | edaic | dataset_specific_ridge | 0.016 | 0.006 |
| edaic_same_dataset | edaic | total_alloc_ridge | 0.011 | 0.000 |
| edaic_same_dataset | edaic | train_mean | 0.000 | -0.011 |
| pooled_shared | cmdc | pooled_shared_ridge | -0.242 | 0.015 |
| pooled_shared | cmdc | total_alloc_ridge | -0.257 | 0.000 |
| pooled_shared | cmdc | train_mean | 0.000 | 0.257 |
| pooled_shared | edaic | pooled_shared_ridge | 0.030 | -0.002 |
| pooled_shared | edaic | total_alloc_ridge | 0.031 | 0.000 |
| pooled_shared | edaic | train_mean | 0.000 | -0.031 |

## Interpretation

The PHQ core bridge is runnable but weak and asymmetric: pooled Ridge helps only selectively, while frozen WavLM dataset identity remains perfectly recoverable, so this row is a diagnostic baseline rather than evidence of a shared symptom representation.

The result should not be read as evidence of a shared symptom representation on its own. The frozen WavLM identity probe remains high, so any pooled improvement is treated as a narrow bridge signal requiring later identity/protocol controls.

## Hygiene

- Artifact hygiene passed: `True`.
- Row-level predictions are written as a local-only ignored CSV.
