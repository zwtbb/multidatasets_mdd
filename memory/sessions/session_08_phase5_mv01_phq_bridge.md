# Session Memory: Phase 5 P5_MV01 PHQ Bridge

Status: complete
Last updated: 2026-08-05 UTC
Thread/task: delegated Phase 5 minimal validation row P5_MV01

## Scope

This session owns the first runnable P5_MV01 minimal-validation experiment:
mapping E-DAIC PHQ-8 and CMDC PHQ-9 item labels to C01-C08 and testing a
narrow shared construct bridge over existing frozen WavLM subject features.
It must not implement a full method, fine-tune encoders, scan raw audio, or
write large feature/model artifacts.

## Current State

- Read the required master memory, Phase 4 ontology memory, Phase 5 protocol
  memory, Phase 3 Stop/Go synthesis, construct map, dataset label contract,
  and Phase 5 experiment matrix.
- Confirmed E-DAIC and CMDC frozen WavLM subject feature caches have a common
  768-column `wavlm_0000` to `wavlm_0767` feature space.
- Implemented and ran `scripts/phase5_run_mv01_phq_bridge.py`.
- Generated
  `analysis/phase5_minimal_validation/p5_mv01_phq_core_bridge/` with report,
  run summary, hygiene audit, metric summaries, split audit, feature
  availability, and a local-only row-level prediction file.
- `run_summary.json` reports `status=complete`,
  `artifact_hygiene_passed=true`, 768 common frozen WavLM feature columns,
  219 joined E-DAIC subjects, 77 joined CMDC subjects, no E-DAIC official test
  use, and zero subject-overlap violations.
- The frozen WavLM E-DAIC-vs-CMDC dataset identity probe has balanced accuracy
  `1.000`, so this row cannot be interpreted as proof of a shared symptom
  representation.
- The script and lightweight artifacts were imported into the main checkout and
  rerun there on 2026-08-05. The main rerun reproduced `status=complete`,
  `artifact_hygiene_passed=true`, zero subject-overlap violations, and the same
  local-only row-level prediction policy.
- Macro construct MAE highlights:
  - CMDC same-dataset: `train_mean=0.847`,
    `dataset_specific_ridge=0.572`, `total_alloc_ridge=0.547`.
  - E-DAIC same-dataset: `train_mean=0.735`,
    `dataset_specific_ridge=0.751`, `total_alloc_ridge=0.746`.
  - E-DAIC -> CMDC: `train_mean=0.865`,
    `cross_dataset_ridge=0.805`, `total_alloc_ridge=0.801`.
  - CMDC -> E-DAIC: `train_mean=0.743`,
    `cross_dataset_ridge=0.998`, `total_alloc_ridge=0.933`.
  - Pooled shared: CMDC `pooled_shared_ridge=0.615` versus
    `train_mean=0.857` and `total_alloc_ridge=0.600`; E-DAIC
    `pooled_shared_ridge=0.762` versus `train_mean=0.732` and
    `total_alloc_ridge=0.764`.

## Key Decisions

- Use E-DAIC official train/dev only; official test labels are not used.
- Use CMDC Phase 2 `cmdc_binary_subject_cv` subject folds for the five-seed
  validation loop.
- Use only shallow Ridge and train-mean heads over frozen subject features.
- Keep row-level predictions local-only and ignored.
- Treat the first result as a weak, asymmetric bridge signal: useful on CMDC
  and E-DAIC-to-CMDC relative to train-mean, but not consistently better than
  total-allocation and worse on E-DAIC versus train-mean.

## Files Owned Or Touched

- `scripts/phase5_run_mv01_phq_bridge.py`
- `memory/sessions/session_08_phase5_mv01_phq_bridge.md`
- `MEMORY.md`
- `.gitignore`
- `analysis/phase5_minimal_validation/p5_mv01_phq_core_bridge/report.md`
- `analysis/phase5_minimal_validation/p5_mv01_phq_core_bridge/run_summary.json`
- `analysis/phase5_minimal_validation/p5_mv01_phq_core_bridge/artifact_hygiene_audit.json`
- `analysis/phase5_minimal_validation/p5_mv01_phq_core_bridge/metric_summary.csv`
- `analysis/phase5_minimal_validation/p5_mv01_phq_core_bridge/metrics_by_seed.csv`
- `analysis/phase5_minimal_validation/p5_mv01_phq_core_bridge/comparison_summary.csv`
- `analysis/phase5_minimal_validation/p5_mv01_phq_core_bridge/dataset_identity_probe_by_seed.csv`
- `analysis/phase5_minimal_validation/p5_mv01_phq_core_bridge/dataset_identity_probe_summary.csv`
- `analysis/phase5_minimal_validation/p5_mv01_phq_core_bridge/feature_availability.csv`
- `analysis/phase5_minimal_validation/p5_mv01_phq_core_bridge/model_split_audit.csv`
- `analysis/phase5_minimal_validation/p5_mv01_phq_core_bridge/construct_target_map.csv`

## Generated Artifacts

Regeneration command:

```bash
python scripts/phase5_run_mv01_phq_bridge.py
```

Versionable/import-suitable files:

- `scripts/phase5_run_mv01_phq_bridge.py`
- `MEMORY.md`
- `.gitignore`
- `memory/sessions/session_08_phase5_mv01_phq_bridge.md`
- `analysis/phase5_minimal_validation/p5_mv01_phq_core_bridge/report.md`
- `analysis/phase5_minimal_validation/p5_mv01_phq_core_bridge/run_summary.json`
- `analysis/phase5_minimal_validation/p5_mv01_phq_core_bridge/artifact_hygiene_audit.json`
- `analysis/phase5_minimal_validation/p5_mv01_phq_core_bridge/metric_summary.csv`
- `analysis/phase5_minimal_validation/p5_mv01_phq_core_bridge/metrics_by_seed.csv`
- `analysis/phase5_minimal_validation/p5_mv01_phq_core_bridge/comparison_summary.csv`
- `analysis/phase5_minimal_validation/p5_mv01_phq_core_bridge/dataset_identity_probe_by_seed.csv`
- `analysis/phase5_minimal_validation/p5_mv01_phq_core_bridge/dataset_identity_probe_summary.csv`
- `analysis/phase5_minimal_validation/p5_mv01_phq_core_bridge/feature_availability.csv`
- `analysis/phase5_minimal_validation/p5_mv01_phq_core_bridge/model_split_audit.csv`
- `analysis/phase5_minimal_validation/p5_mv01_phq_core_bridge/construct_target_map.csv`

Local-only/ignored files:

- `analysis/phase5_minimal_validation/p5_mv01_phq_core_bridge/p5_mv01_local_predictions.csv`
- `scripts/__pycache__/`

## Blockers And Risks

- Frozen WavLM features carry severe dataset identity risk
  (`balanced_accuracy=1.000`), so pooled gains cannot be interpreted as a
  shared symptom representation unless identity/protocol controls improve in
  later rows.
- Ridge heads do not consistently outperform the total-allocation baseline,
  especially on CMDC same-dataset and E-DAIC-to-CMDC, so the first bridge
  evidence is limited.

## Next Handoff

Next Phase 5 work should either run the planned identity/protocol-control row
or revise P5_MV01 with a stronger audited feature/control contract before any
full-method claim.
