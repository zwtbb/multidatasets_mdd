# Phase 3 Task And Valence Diagnostics

Generated: `2026-08-04T17:07:29+00:00`

## Protocol

- MODMA: task-specific and cross-task binary classification over subject-task eGeMAPS aggregates.
- EATD: valence-specific binary and SDS prediction over positive, neutral, and negative eGeMAPS rows.
- Splits: existing subject-level Phase 2 MODMA split layer and EATD official train/validation subjects.
- Seeds: five fixed seeds (`0, 1, 2, 3, 4`).
- Bootstrap: `200` subject-level resamples for metric and diagnostic intervals; rerun with `--bootstrap-resamples 1000` for tighter CIs.
- Models: fixed simple heads only; no encoder fine-tuning and no new method design.
- Formal artifacts omit raw text, raw audio, source audio/text paths, and file names.

## MODMA Result Snapshot

- Tasks evaluated: `['interview', 'reading', 'picture_description', 'affective_task']`.
- Manifest-invalid audio rows excluded before modeling: `5`.
- Overall Balanced Accuracy within-task mean: `0.6467391304347826`.
- Overall Balanced Accuracy cross-task mean: `0.5477886056971514`.
- Overall Balanced Accuracy drop: `0.09895052473763116` with CI `-0.04437045822694672` to `0.24370820996015838`.

## EATD Result Snapshot

- Validation subjects: `79`.
- Healthy negative mean depressed-probability score: `0.1426031644328509`.
- Healthy negative minus nonnegative mean score: `-0.061078521318583615`.
- Healthy negative predicted-depressed rate: `0.11764705882352941`.

## Output Files

- `modma_egemaps_segment_features.csv` (local-only feature cache; ignored by default)
- `modma_egemaps_subject_task_features.csv` (local-only feature cache; ignored by default)
- `modma_task_transfer_predictions.csv` (local-only row-level artifact; ignored by default)
- `modma_task_transfer_metrics_by_seed.csv`
- `modma_task_transfer_metric_summary.csv`
- `modma_task_transfer_matrix.csv`
- `modma_task_transfer_drops_by_seed.csv`
- `modma_task_transfer_drop_summary.csv`
- `eatd_egemaps_valence_features.csv` (local-only feature cache; ignored by default)
- `eatd_valence_predictions.csv` (local-only row-level artifact; ignored by default)
- `eatd_valence_metrics_by_seed.csv`
- `eatd_valence_metric_summary.csv`
- `eatd_valence_subject_stability.csv`
- `eatd_valence_stability_summary.csv`
- `eatd_healthy_negative_confusion_by_seed.csv`
- `eatd_healthy_negative_confusion_summary.csv`
- `phase3_task_valence_run_summary.json`
- `artifact_hygiene_audit.json`
