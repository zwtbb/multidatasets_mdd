# Session Memory: Phase 5 P5_MV04 Dataset Identity Control

Status: complete
Last updated: 2026-08-05 UTC
Thread/task: delegated Phase 5 minimal validation row P5_MV04

## Scope

This session owns the first runnable P5_MV04
`dataset_protocol_control_ablation` focused on the P5_MV01 blocker: frozen
WavLM E-DAIC vs CMDC dataset identity balanced accuracy was `1.000`.
It reuses the P5_MV01 PHQ C01-C08 label mapping and frozen WavLM subject
features. It does not implement a full method, fine-tune encoders, scan raw
directories, write transformed features, write learned embeddings, or persist
model weights.

## Current State

- Implemented and ran `scripts/phase5_run_mv04_dataset_identity_control.py`.
- Generated
  `analysis/phase5_minimal_validation/p5_mv04_dataset_identity_control/`.
- The run completed with `status=complete`, `artifact_hygiene_passed=true`,
  and zero subject-overlap violations.
- The model contract compares:
  - `train_mean`;
  - `total_alloc_ridge`;
  - `baseline_pooled_shared_ridge`;
  - `dataset_centered_shared_ridge`.
- The control is train-fold dataset centering over frozen WavLM features. It
  uses no eval target labels, but it does use known eval dataset labels for the
  diagnostic centering transform.
- Feature-layer identity BA changed from `1.000` before control to `0.500`
  after control.
- Prediction-layer identity BA changed from `0.961` for the baseline pooled
  Ridge predictions to `0.476` for the dataset-centered Ridge predictions.
- Dataset-stratified Macro Construct MAE stayed within the P5_MV04 5 percent
  relative tolerance versus baseline:
  - CMDC: baseline `0.615`, control `0.621`;
  - E-DAIC: baseline `0.762`, control `0.764`.
- Worst-slice Macro Construct MAE changed from `0.762` to `0.764`, relative
  delta `0.003`.
- P5_MV04 pass-rule status is `pass_minimal_control`.

## Key Decisions

- Treat this result as a successful diagnostic identity-control ablation, not
  as a finished deployment/inference contract, because dataset labels are used
  as control variables for centering at transform time.
- Keep row-level predictions local-only and ignored.
- Do not write transformed feature matrices, learned representations, model
  weights, raw snippets, prompt/response text, audio, or video.

## Files Owned Or Touched

- `scripts/phase5_run_mv04_dataset_identity_control.py`
- `memory/sessions/session_09_phase5_mv04_dataset_identity_control.md`
- `MEMORY.md`
- `analysis/phase5_minimal_validation/p5_mv04_dataset_identity_control/report.md`
- `analysis/phase5_minimal_validation/p5_mv04_dataset_identity_control/run_summary.json`
- `analysis/phase5_minimal_validation/p5_mv04_dataset_identity_control/artifact_hygiene_audit.json`
- `analysis/phase5_minimal_validation/p5_mv04_dataset_identity_control/metric_summary.csv`
- `analysis/phase5_minimal_validation/p5_mv04_dataset_identity_control/metrics_by_seed.csv`
- `analysis/phase5_minimal_validation/p5_mv04_dataset_identity_control/comparison_summary.csv`
- `analysis/phase5_minimal_validation/p5_mv04_dataset_identity_control/worst_slice_summary.csv`
- `analysis/phase5_minimal_validation/p5_mv04_dataset_identity_control/worst_slice_by_seed.csv`
- `analysis/phase5_minimal_validation/p5_mv04_dataset_identity_control/dataset_identity_probe_summary.csv`
- `analysis/phase5_minimal_validation/p5_mv04_dataset_identity_control/dataset_identity_probe_by_seed.csv`
- `analysis/phase5_minimal_validation/p5_mv04_dataset_identity_control/feature_availability.csv`
- `analysis/phase5_minimal_validation/p5_mv04_dataset_identity_control/model_split_audit.csv`
- `analysis/phase5_minimal_validation/p5_mv04_dataset_identity_control/construct_target_map.csv`

## Generated Artifacts

Regeneration command:

```bash
python scripts/phase5_run_mv04_dataset_identity_control.py
```

Versionable/import-suitable files:

- `scripts/phase5_run_mv04_dataset_identity_control.py`
- `MEMORY.md`
- `memory/sessions/session_09_phase5_mv04_dataset_identity_control.md`
- all non-local-only files under
  `analysis/phase5_minimal_validation/p5_mv04_dataset_identity_control/`.

Local-only/ignored files:

- `analysis/phase5_minimal_validation/p5_mv04_dataset_identity_control/p5_mv04_local_predictions.csv`

## Blockers And Risks

- The control answers the immediate P5_MV01 identity blocker for known
  E-DAIC/CMDC dataset labels, but it is not sufficient evidence for an
  unknown-source inference setting.
- This first P5_MV04 run only covers the E-DAIC/CMDC PHQ C01-C08 frozen WavLM
  setting. MODMA task slices, EATD valence slices, and broader protocol labels
  remain future P5_MV04 extensions.
- Baseline and controlled models still do not turn frozen WavLM into strong
  shared symptom evidence: E-DAIC Macro MAE remains worse than train-mean, and
  CMDC total-allocation remains slightly better than the pooled shared Ridge.

## Next Handoff

Import the lightweight script, report, summaries, audits, and this session
memory into the main checkout. Keep the local prediction CSV out of Git. Future
Phase 5 work should either add an inference-compatible identity residualization
variant, extend P5_MV04 to protocol/task slices, or proceed to the next
minimal-validation row while preserving the same identity and hygiene audits.
