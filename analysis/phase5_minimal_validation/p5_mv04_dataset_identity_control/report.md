# P5_MV04 Dataset Identity Control Ablation

Generated: `2026-08-05T04:02:11+00:00`

## Scope

This first runnable P5_MV04 row directly targets the P5_MV01 blocker: E-DAIC vs CMDC dataset identity is perfectly recoverable from frozen WavLM subject features. It reuses the P5_MV01 PHQ C01-C08 mapping and subject-level split contract, then compares a pooled shared Ridge baseline with a train-fold dataset-centering control. No encoder fine-tuning, raw-directory scan, learned representation export, or model checkpoint export is used.

## Feature And Split Contract

- Common frozen WavLM columns: `768`.
- E-DAIC subjects joined: `219`; official train/dev only.
- CMDC subjects joined: `77`; Phase 2 subject CV folds.
- Subject-overlap violations: `0`.
- Control uses eval target labels: `False`.
- Control uses known eval dataset labels for centering: `True`.

## Dataset-Stratified Macro MAE

| model | dataset | macro MAE | seed count |
| --- | --- | ---: | ---: |
| baseline_pooled_shared_ridge | cmdc | 0.615 | 5 |
| baseline_pooled_shared_ridge | edaic | 0.762 | 5 |
| dataset_centered_shared_ridge | cmdc | 0.621 | 5 |
| dataset_centered_shared_ridge | edaic | 0.764 | 5 |
| total_alloc_ridge | cmdc | 0.600 | 5 |
| total_alloc_ridge | edaic | 0.764 | 5 |
| train_mean | cmdc | 0.857 | 5 |
| train_mean | edaic | 0.732 | 5 |

## Deltas

Negative MAE deltas are improvements. Relative delta is versus the raw pooled shared Ridge baseline.

| dataset | model | delta vs train_mean | delta vs total_alloc | delta vs baseline | relative delta vs baseline |
| --- | --- | ---: | ---: | ---: | ---: |
| cmdc | baseline_pooled_shared_ridge | -0.242 | 0.015 | 0.000 | 0.000 |
| cmdc | dataset_centered_shared_ridge | -0.236 | 0.021 | 0.006 | 0.010 |
| cmdc | total_alloc_ridge | -0.257 | 0.000 | -0.015 | -0.024 |
| cmdc | train_mean | 0.000 | 0.257 | 0.242 | 0.394 |
| edaic | baseline_pooled_shared_ridge | 0.030 | -0.002 | 0.000 | 0.000 |
| edaic | dataset_centered_shared_ridge | 0.032 | 0.000 | 0.002 | 0.003 |
| edaic | total_alloc_ridge | 0.031 | 0.000 | 0.002 | 0.002 |
| edaic | train_mean | 0.000 | -0.031 | -0.030 | -0.039 |

## Worst Slice

| model | worst-slice Macro MAE | delta vs baseline | relative delta vs baseline |
| --- | ---: | ---: | ---: |
| baseline_pooled_shared_ridge | 0.762 | 0.000 | 0.000 |
| dataset_centered_shared_ridge | 0.764 | 0.002 | 0.003 |
| total_alloc_ridge | 0.764 | 0.002 | 0.002 |
| train_mean | 0.857 | 0.095 | 0.124 |

## Dataset Identity Probes

| layer | representation | identity balanced accuracy | seed count |
| --- | --- | ---: | ---: |
| feature | raw_frozen_wavlm_before_control | 1.000 | 5 |
| feature | train_fold_dataset_centered_after_control | 0.500 | 5 |
| prediction | baseline_pooled_shared_ridge_predictions | 0.961 | 5 |
| prediction | dataset_centered_shared_ridge_predictions | 0.476 | 5 |

## Verdict

- Pass-rule status: `pass_minimal_control`.
- Feature identity BA before/after: `1.000` -> `0.500`.
- Baseline/control prediction identity BA: `0.961` -> `0.476`.
- Main task within 5 percent on all dataset slices: `True`.

The train-fold dataset-centering control reduces held-out E-DAIC-vs-CMDC identity probe balanced accuracy while preserving PHQ C01-C08 Macro MAE within the 5 percent relative tolerance versus the pooled shared baseline.

## Hygiene

- Artifact hygiene passed: `True`.
- Row-level predictions are written as a local-only ignored CSV.
- Transformed features, learned representations, model weights, source snippets, prompt/response text, audio, and video are not written.
