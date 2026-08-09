# Phase 3 Protocol-Control Diagnostics

Generated: `2026-08-04T16:41:35+00:00`

## Scope

- Datasets: E-DAIC and CMDC.
- Inputs: `datasets/registry.yaml`, `datasets/manifests/`, and `datasets/splits/phase2_subject_splits.csv`.
- Models: fixed TF-IDF Ridge/Logistic controls, reusing Phase 2 metric helpers.
- Bootstrap resamples: `200`; rerun with `--bootstrap-resamples 1000` for tighter CIs.
- No test labels are used for fitting, model choice, or tuning.
- Raw text, raw prompt text, raw audio/video, and source paths are not written to artifacts.

## Completed Controls

- E-DAIC: full available transcript, front 25%, middle 50%, back 25%, train repeated-turn removal, and train repeated-turn-only proxy.
- CMDC: all questions, Q1-Q12 individual question-position probes, and Q1-Q4/Q5-Q8/Q9-Q12 question-block probes.

## Blockers

- E-DAIC participant-only and interviewer-only controls are blocked because neither the manifest speaker field nor the transcript CSV column sets expose speaker identity.
- CMDC interviewer/prompt-only controls are blocked because the manifest has no populated speaker/prompt text fields; question-position probes were run instead.

## Primary Metric Snapshot

| dataset | target | control_id | primary_metric | metric_mean | delta_vs_full_control |
| --- | --- | --- | --- | --- | --- |
| E-DAIC | phq8_total | full_dialogue | MAE | 4.7452 | 0.0000 |
| E-DAIC | phq8_total | front_25 | MAE | 4.7515 | 0.0063 |
| E-DAIC | phq8_total | middle_50 | MAE | 4.7135 | -0.0317 |
| E-DAIC | phq8_total | back_25 | MAE | 4.7735 | 0.0283 |
| E-DAIC | binary_label | full_dialogue | Macro-F1 | 0.4400 | 0.0000 |
| E-DAIC | binary_label | front_25 | Macro-F1 | 0.5492 | 0.1092 |
| E-DAIC | binary_label | middle_50 | Macro-F1 | 0.4343 | -0.0057 |
| E-DAIC | binary_label | back_25 | Macro-F1 | 0.4343 | -0.0057 |
| CMDC | binary_label | all_questions | Macro-F1 | 0.8504 | 0.0000 |
| CMDC | binary_label | q01_only | Macro-F1 | 0.7425 | -0.1079 |
| CMDC | binary_label | q06_only | Macro-F1 | 0.5266 | -0.3238 |
| CMDC | binary_label | q12_only | Macro-F1 | 0.6177 | -0.2327 |
| CMDC | phq9_total | all_questions | MAE | 6.4281 | 0.0000 |
| CMDC | phq9_total | q01_only | MAE | 6.4111 | -0.0170 |
| CMDC | phq9_total | q06_only | MAE | 6.5295 | 0.1015 |
| CMDC | phq9_total | q12_only | MAE | 6.5693 | 0.1412 |
| CMDC | hamd17_total | all_questions | MAE | 3.7139 | 0.0000 |
| CMDC | hamd17_total | q01_only | MAE | 3.6671 | -0.0467 |
| CMDC | hamd17_total | q06_only | MAE | 3.7381 | 0.0242 |
| CMDC | hamd17_total | q12_only | MAE | 3.6045 | -0.1094 |

## Artifact Inventory

- `protocol_control_predictions.csv` (local-only row-level artifact; ignored by default)
- `phase3_metrics_by_seed.csv`
- `phase3_metric_summary.csv`
- `protocol_control_metric_deltas.csv`
- `protocol_feasibility_audit.csv`
- `dataset_slice_summary.csv`
- `protocol_model_status.csv`
- `protocol_controls_run_summary.json`
