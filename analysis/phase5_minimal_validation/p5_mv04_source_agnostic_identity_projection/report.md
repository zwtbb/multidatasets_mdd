# P5_MV04b Source-Agnostic Identity Projection

Generated: `2026-08-05T04:09:10+00:00`

## Scope

This follow-up targets the remaining P5_MV04 caveat: train-fold dataset centering reduced identity but used known evaluation dataset labels. Here, iterative logistic nuisance directions are fitted on training-fold dataset labels and applied to held-out subjects without using evaluation dataset labels or targets. No encoder fine-tuning, raw-directory scan, transformed feature export, learned representation export, or model checkpoint export is used.

## Feature And Split Contract

- Common frozen WavLM columns: `768`.
- E-DAIC subjects joined: `219`; official train/dev only.
- CMDC subjects joined: `77`; Phase 2 subject CV folds.
- Subject-overlap violations: `0`.
- Control uses eval target labels: `False`.
- Control uses eval dataset labels: `False`.
- Projection component counts tested: `1, 3, 5, 10`.

## Dataset-Stratified Macro MAE

| model | dataset | macro MAE | seed count |
| --- | --- | ---: | ---: |
| baseline_pooled_shared_ridge | cmdc | 0.615 | 5 |
| baseline_pooled_shared_ridge | edaic | 0.762 | 5 |
| source_agnostic_logit_projection_k10_shared_ridge | cmdc | 0.593 | 5 |
| source_agnostic_logit_projection_k10_shared_ridge | edaic | 0.774 | 5 |
| source_agnostic_logit_projection_k1_shared_ridge | cmdc | 0.593 | 5 |
| source_agnostic_logit_projection_k1_shared_ridge | edaic | 0.772 | 5 |
| source_agnostic_logit_projection_k3_shared_ridge | cmdc | 0.593 | 5 |
| source_agnostic_logit_projection_k3_shared_ridge | edaic | 0.774 | 5 |
| source_agnostic_logit_projection_k5_shared_ridge | cmdc | 0.591 | 5 |
| source_agnostic_logit_projection_k5_shared_ridge | edaic | 0.774 | 5 |
| total_alloc_ridge | cmdc | 0.600 | 5 |
| total_alloc_ridge | edaic | 0.764 | 5 |
| train_mean | cmdc | 0.857 | 5 |
| train_mean | edaic | 0.732 | 5 |

## Deltas

Negative MAE deltas are improvements. Relative delta is versus the raw pooled shared Ridge baseline.

| dataset | model | delta vs train_mean | delta vs total_alloc | delta vs baseline | relative delta vs baseline |
| --- | --- | ---: | ---: | ---: | ---: |
| cmdc | baseline_pooled_shared_ridge | -0.242 | 0.015 | 0.000 | 0.000 |
| cmdc | source_agnostic_logit_projection_k10_shared_ridge | -0.263 | -0.006 | -0.021 | -0.035 |
| cmdc | source_agnostic_logit_projection_k1_shared_ridge | -0.264 | -0.006 | -0.021 | -0.035 |
| cmdc | source_agnostic_logit_projection_k3_shared_ridge | -0.264 | -0.007 | -0.022 | -0.036 |
| cmdc | source_agnostic_logit_projection_k5_shared_ridge | -0.266 | -0.009 | -0.024 | -0.039 |
| cmdc | total_alloc_ridge | -0.257 | 0.000 | -0.015 | -0.024 |
| cmdc | train_mean | 0.000 | 0.257 | 0.242 | 0.394 |
| edaic | baseline_pooled_shared_ridge | 0.030 | -0.002 | 0.000 | 0.000 |
| edaic | source_agnostic_logit_projection_k10_shared_ridge | 0.041 | 0.010 | 0.012 | 0.015 |
| edaic | source_agnostic_logit_projection_k1_shared_ridge | 0.040 | 0.008 | 0.010 | 0.013 |
| edaic | source_agnostic_logit_projection_k3_shared_ridge | 0.041 | 0.010 | 0.012 | 0.015 |
| edaic | source_agnostic_logit_projection_k5_shared_ridge | 0.042 | 0.010 | 0.012 | 0.016 |
| edaic | total_alloc_ridge | 0.031 | 0.000 | 0.002 | 0.002 |
| edaic | train_mean | 0.000 | -0.031 | -0.030 | -0.039 |

## Worst Slice

| model | worst-slice Macro MAE | delta vs baseline | relative delta vs baseline |
| --- | ---: | ---: | ---: |
| baseline_pooled_shared_ridge | 0.762 | 0.000 | 0.000 |
| source_agnostic_logit_projection_k10_shared_ridge | 0.774 | 0.012 | 0.015 |
| source_agnostic_logit_projection_k1_shared_ridge | 0.772 | 0.010 | 0.013 |
| source_agnostic_logit_projection_k3_shared_ridge | 0.774 | 0.012 | 0.015 |
| source_agnostic_logit_projection_k5_shared_ridge | 0.774 | 0.012 | 0.016 |
| total_alloc_ridge | 0.764 | 0.002 | 0.002 |
| train_mean | 0.857 | 0.095 | 0.124 |

## Dataset Identity Probes

| layer | representation | identity balanced accuracy | seed count |
| --- | --- | ---: | ---: |
| feature | raw_frozen_wavlm_before_control | 1.000 | 5 |
| feature | source_agnostic_logit_projection_k10_after_control | 0.925 | 5 |
| feature | source_agnostic_logit_projection_k1_after_control | 0.914 | 5 |
| feature | source_agnostic_logit_projection_k3_after_control | 0.934 | 5 |
| feature | source_agnostic_logit_projection_k5_after_control | 0.937 | 5 |
| prediction | baseline_pooled_shared_ridge_predictions | 0.961 | 5 |
| prediction | source_agnostic_logit_projection_k10_shared_ridge_predictions | 0.777 | 5 |
| prediction | source_agnostic_logit_projection_k1_shared_ridge_predictions | 0.854 | 5 |
| prediction | source_agnostic_logit_projection_k3_shared_ridge_predictions | 0.811 | 5 |
| prediction | source_agnostic_logit_projection_k5_shared_ridge_predictions | 0.815 | 5 |

## Verdict

- Pass-rule status: `partial_pass_identity_reduced_not_removed`.
- Best control model: `source_agnostic_logit_projection_k10_shared_ridge`.
- Feature identity BA before/best-after: `1.000` -> `0.925`.
- Prediction identity BA baseline/best-control: `0.961` -> `0.777`.
- Residual feature identity remains high: `True`.

The source-agnostic projection reduces held-out prediction identity and preserves PHQ C01-C08 Macro MAE within tolerance, but feature-layer dataset identity remains high; treat it as a partial diagnostic control and keep full-method claims blocked.

## Hygiene

- Artifact hygiene passed: `True`.
- Row-level predictions are written as a local-only ignored CSV.
- Transformed features, learned projection directions, model weights, source snippets, prompt/response text, audio, and video are not written.
