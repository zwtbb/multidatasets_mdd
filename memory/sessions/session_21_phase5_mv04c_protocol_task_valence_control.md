# Session Memory: Phase 5 MV04c Protocol Task/Valence Control

Status: complete
Last updated: 2026-08-09 UTC
Thread/task: main agent MV04c protocol/task/valence control

## Scope

This session owns `P5_MV04c protocol_task_valence_control`, an extension of
the P5_MV04 dataset/protocol control row to MODMA task slices and EATD valence
slices. It tests train-fold nuisance projection over protocol labels using
local Phase 3 eGeMAPS feature caches.

It does not train a full symptom-aligned model, fine-tune encoders, rescan raw
audio, export transformed features, export projection parameters, or commit
row-level predictions.

## Current State

- Implemented `scripts/phase5_run_mv04c_protocol_task_valence_control.py`.
- Generated
  `analysis/phase5_minimal_validation/p5_mv04c_protocol_task_valence_control/`.
- The run used:
  - MODMA 52 subjects, 208 subject-task rows, 352 eGeMAPS feature columns;
  - EATD 162 subjects, 486 subject-valence rows, 88 eGeMAPS feature columns;
  - five seeds;
  - subject-level MODMA 5-fold CV and EATD official train/validation split;
  - train-fold protocol-label nuisance projection with component counts
    `1`, `2`, `3`, `5`, and `8`;
  - no evaluation target labels or evaluation protocol labels at transform
    time.
- Artifact hygiene passed and subject-overlap violations were zero.
- Row-level predictions are local-only in
  `p5_mv04c_local_predictions.csv`.

## Key Decisions

- Result status: `mixed_protocol_control`.
- MODMA task control passes diagnostically:
  - raw eGeMAPS task identity BA `0.762`;
  - best `task_projection_k8_logistic` task identity BA `0.570`;
  - pooled Balanced Accuracy remains essentially preserved
    (`0.688` raw vs `0.686` controlled);
  - all task-slice Balanced Accuracy and Macro-F1 metrics remain within the
    5 percent preservation tolerance.
- EATD valence control is blocked:
  - raw feature valence identity BA is already below/near chance (`0.283`) and
    projection does not reduce it (`0.321` at k=8);
  - the raw SDS total Ridge head is far below the train-mean floor
    (`28.810` pooled MAE vs train mean `7.201`);
  - therefore EATD does not provide a positive valence-control or SDS
    generalization signal under this feature contract.
- Treat MV04c as useful mixed evidence: MODMA supports an
  inference-compatible task nuisance-control component, while EATD remains a
  negative stress test and should not motivate a valence-adversarial component
  from current eGeMAPS/Ridge evidence.
- Full-method work remains blocked because the overall Phase 5 evidence is
  still partial/mixed and cross-dataset shared-symptom evidence remains weak.

## Files Owned Or Touched

- `scripts/phase5_run_mv04c_protocol_task_valence_control.py`
- `analysis/phase5_minimal_validation/p5_mv04c_protocol_task_valence_control/`
- `scripts/phase5_build_minimal_validation_protocol.py`
- `analysis/phase5_minimal_validation/experiment_matrix.csv`
- `analysis/phase5_minimal_validation/minimal_validation_protocol.md`
- `analysis/phase5_minimal_validation/readiness_audit.json`
- `MEMORY.md`
- `docs/master_experiment_plan.md`
- `docs/experiment_issue_log.md`
- `memory/sessions/session_master_orchestration.md`
- `memory/sessions/session_21_phase5_mv04c_protocol_task_valence_control.md`

## Generated Artifacts

Regeneration commands:

```bash
python scripts/phase5_run_mv04c_protocol_task_valence_control.py
python scripts/phase5_build_minimal_validation_protocol.py
```

Versionable artifacts:

- `analysis/phase5_minimal_validation/p5_mv04c_protocol_task_valence_control/report.md`
- `analysis/phase5_minimal_validation/p5_mv04c_protocol_task_valence_control/run_summary.json`
- `analysis/phase5_minimal_validation/p5_mv04c_protocol_task_valence_control/artifact_hygiene_audit.json`
- `analysis/phase5_minimal_validation/p5_mv04c_protocol_task_valence_control/metric_summary.csv`
- `analysis/phase5_minimal_validation/p5_mv04c_protocol_task_valence_control/metrics_by_seed.csv`
- `analysis/phase5_minimal_validation/p5_mv04c_protocol_task_valence_control/comparison_summary.csv`
- `analysis/phase5_minimal_validation/p5_mv04c_protocol_task_valence_control/identity_probe_summary.csv`
- `analysis/phase5_minimal_validation/p5_mv04c_protocol_task_valence_control/identity_probe_by_seed.csv`
- `analysis/phase5_minimal_validation/p5_mv04c_protocol_task_valence_control/model_split_audit.csv`
- `analysis/phase5_minimal_validation/p5_mv04c_protocol_task_valence_control/projection_audit.csv`
- `analysis/phase5_minimal_validation/p5_mv04c_protocol_task_valence_control/feature_contract.csv`

Local-only artifact:

- `analysis/phase5_minimal_validation/p5_mv04c_protocol_task_valence_control/p5_mv04c_local_predictions.csv`

## Blockers And Risks

- MODMA positive control evidence is task/protocol-specific and still uses
  lightweight eGeMAPS features, not a full shared symptom representation.
- EATD SDS total remains below train mean for the current feature/model
  contract, so EATD should remain a negative/blocked stress result.
- MV06 evidence localization remains blocked until local human annotation is
  completed and summarized.

## Next Handoff

Next useful work is either local MV06 annotation and summary-gate rerun, or a
revised cross-dataset/shared-symptom feature contract that can beat simple
floors while preserving identity/protocol controls. Do not start the full
method solely from MV04c.
