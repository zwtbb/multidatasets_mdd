# Session Memory: Phase 5 P5_MV04b Source-Agnostic Identity Projection

Status: complete
Last updated: 2026-08-05 UTC
Thread/task: main agent Phase 5 P5_MV04 follow-up

## Scope

This session owns a P5_MV04 follow-up that tests whether identity control can be
made more inference-compatible than the prior train-fold dataset-centering
diagnostic. It reuses the P5_MV01/P5_MV04 E-DAIC/CMDC PHQ C01-C08 label
mapping, frozen WavLM subject features, and subject-level split contract. It
does not implement a full method, fine-tune encoders, scan raw directories,
write transformed features, write learned embeddings, or persist projection
directions/model weights.

## Current State

- Implemented and ran
  `scripts/phase5_run_mv04_source_agnostic_identity_projection.py`.
- Generated
  `analysis/phase5_minimal_validation/p5_mv04_source_agnostic_identity_projection/`.
- The run completed with `status=complete`, `artifact_hygiene_passed=true`,
  and zero subject-overlap violations.
- Tested iterative logistic nuisance projection with component counts
  `1`, `3`, `5`, and `10`.
- The projection uses only training-fold dataset labels. It uses no evaluation
  target labels and no evaluation dataset labels.
- Best control by prediction identity was
  `source_agnostic_logit_projection_k10_shared_ridge`.
- Feature-layer identity BA changed from `1.000` before control to `0.925` for
  the best-control setting.
- Prediction-layer identity BA changed from `0.961` for the baseline pooled
  Ridge predictions to `0.777` for the best source-agnostic projection.
- Dataset-stratified Macro Construct MAE stayed within the P5_MV04 5 percent
  relative tolerance versus baseline:
  - CMDC: baseline `0.615`, best source-agnostic control `0.593`;
  - E-DAIC: baseline `0.762`, best source-agnostic control `0.774`.
- Worst-slice Macro Construct MAE changed from `0.762` to `0.774`, relative
  delta `0.015`.
- P5_MV04b pass-rule status is
  `partial_pass_identity_reduced_not_removed`.

## Key Decisions

- Treat source-agnostic projection as useful but incomplete. It reduces
  prediction-layer identity and preserves main-task MAE, but feature-layer
  identity remains high.
- Keep full method construction blocked. This result supports exploring
  stronger inference-compatible identity controls, alternative feature
  contracts, or task/protocol-slice extensions.
- Keep row-level predictions local-only and ignored.
- Do not write transformed feature matrices, projection directions, learned
  representations, model weights, raw snippets, prompt/response text, audio, or
  video.

## Files Owned Or Touched

- `scripts/phase5_run_mv04_source_agnostic_identity_projection.py`
- `memory/sessions/session_10_phase5_mv04_source_agnostic_identity_projection.md`
- `MEMORY.md`
- `docs/master_experiment_plan.md`
- `docs/experiment_issue_log.md`
- `memory/sessions/session_master_orchestration.md`
- `analysis/phase5_minimal_validation/p5_mv04_source_agnostic_identity_projection/report.md`
- `analysis/phase5_minimal_validation/p5_mv04_source_agnostic_identity_projection/run_summary.json`
- `analysis/phase5_minimal_validation/p5_mv04_source_agnostic_identity_projection/artifact_hygiene_audit.json`
- `analysis/phase5_minimal_validation/p5_mv04_source_agnostic_identity_projection/metric_summary.csv`
- `analysis/phase5_minimal_validation/p5_mv04_source_agnostic_identity_projection/metrics_by_seed.csv`
- `analysis/phase5_minimal_validation/p5_mv04_source_agnostic_identity_projection/comparison_summary.csv`
- `analysis/phase5_minimal_validation/p5_mv04_source_agnostic_identity_projection/worst_slice_summary.csv`
- `analysis/phase5_minimal_validation/p5_mv04_source_agnostic_identity_projection/worst_slice_by_seed.csv`
- `analysis/phase5_minimal_validation/p5_mv04_source_agnostic_identity_projection/dataset_identity_probe_summary.csv`
- `analysis/phase5_minimal_validation/p5_mv04_source_agnostic_identity_projection/dataset_identity_probe_by_seed.csv`
- `analysis/phase5_minimal_validation/p5_mv04_source_agnostic_identity_projection/feature_availability.csv`
- `analysis/phase5_minimal_validation/p5_mv04_source_agnostic_identity_projection/model_split_audit.csv`
- `analysis/phase5_minimal_validation/p5_mv04_source_agnostic_identity_projection/projection_audit.csv`
- `analysis/phase5_minimal_validation/p5_mv04_source_agnostic_identity_projection/construct_target_map.csv`

## Generated Artifacts

Regeneration command:

```bash
python scripts/phase5_run_mv04_source_agnostic_identity_projection.py
```

Versionable/import-suitable files:

- `scripts/phase5_run_mv04_source_agnostic_identity_projection.py`
- `memory/sessions/session_10_phase5_mv04_source_agnostic_identity_projection.md`
- all non-local-only files under
  `analysis/phase5_minimal_validation/p5_mv04_source_agnostic_identity_projection/`.

Local-only/ignored files:

- `analysis/phase5_minimal_validation/p5_mv04_source_agnostic_identity_projection/p5_mv04b_local_predictions.csv`

## Blockers And Risks

- Feature-layer E-DAIC/CMDC identity remains high after source-agnostic
  projection (`0.925`), so direct pooled representation claims remain blocked.
- This run only covers E-DAIC/CMDC PHQ C01-C08 frozen WavLM features. It does
  not test MODMA task slices, EATD valence slices, MPDD context calibration, or
  alternative text/audio feature contracts.
- The control improves CMDC Macro MAE but still leaves E-DAIC worse than
  train-mean, consistent with P5_MV01/P5_MV04 caution.

## Next Handoff

Continue Phase 5 with either stronger inference-compatible identity controls,
protocol/task-slice P5_MV04 extensions, or another minimal-validation row such
as `P5_MV03` SDS total external stress or `P5_MV05` MPDD context calibration.
Full method work should remain blocked until evidence is stronger across more
than this partial identity-control result.
