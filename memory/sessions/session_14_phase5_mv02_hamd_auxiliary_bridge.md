# Session Memory: Phase 5 MV02 HAMD Auxiliary Bridge

Status: complete
Last updated: 2026-08-09 UTC
Thread/task: main agent MV02 PDCH-only run

## Scope

This session owns the `P5_MV02 hamd17_auxiliary_bridge` minimal validation run.
It uses PDCH as the primary HAMD-17 training/evaluation source and CMDC only as
a limited 25-subject sanity subset. It does not train a full method, fine-tune
encoders, scan raw clinical text/media, export model weights, or make
cross-dataset HAMD claims.

## Current State

- Implemented `scripts/phase5_run_mv02_hamd_auxiliary_bridge.py`.
- Generated
  `analysis/phase5_minimal_validation/p5_mv02_hamd_auxiliary_bridge/`.
- The run used 99 PDCH HAMD-labeled subjects and five seeds with 5-fold
  subject-level stratified CV.
- It used cached frozen BGE text, WavLM audio, eGeMAPS audio, and
  early-fusion subject features.
- HAMD item code `9` was excluded from item-head training/evaluation and from
  item-derived total scoring, matching the official PDCH convention.
- CMDC was evaluated only as a 25-subject sanity subset and was not used for
  hyperparameter selection.
- Artifact hygiene passed and row-level predictions are local-only.

## Key Decisions

- Result status: `pass_pdch_only_diagnostic`.
- Best PDCH CV item-derived HAMD total MAE was `5.693` from early-fusion
  itemwise Ridge versus train-mean items `6.183`.
- Best PDCH CV direct-total MAE was `5.794` from early-fusion direct-total
  Ridge versus train-mean total `6.181`.
- Best PDCH macro HAMD item MAE was `0.727` from early-fusion itemwise Ridge
  versus train-mean items `0.747`.
- CMDC sanity did not support cross-dataset transfer: train-mean total MAE
  `3.595` beat text BGE `3.856`, WavLM `4.848`, eGeMAPS `21.754`, and
  early fusion `24.206` for direct-total heads.
- Interpret MV02 as evidence that a bounded HAMD auxiliary bridge can run
  inside PDCH, not evidence that the current frozen-feature HAMD bridge
  generalizes across datasets.

## Files Owned Or Touched

- `scripts/phase5_run_mv02_hamd_auxiliary_bridge.py`
- `scripts/phase5_build_minimal_validation_protocol.py`
- `analysis/phase5_minimal_validation/p5_mv02_hamd_auxiliary_bridge/`
- `analysis/phase5_minimal_validation/experiment_matrix.csv`
- `analysis/phase5_minimal_validation/minimal_validation_protocol.md`
- `analysis/phase5_minimal_validation/readiness_audit.json`
- `MEMORY.md`
- `docs/experiment_issue_log.md`
- `memory/sessions/session_07_phase5_minimal_validation_protocol.md`
- `memory/sessions/session_14_phase5_mv02_hamd_auxiliary_bridge.md`
- `memory/sessions/session_master_orchestration.md`

## Generated Artifacts

Regeneration commands:

```bash
python scripts/phase5_run_mv02_hamd_auxiliary_bridge.py
python scripts/phase5_build_minimal_validation_protocol.py
```

Versionable artifacts:

- `analysis/phase5_minimal_validation/p5_mv02_hamd_auxiliary_bridge/report.md`
- `analysis/phase5_minimal_validation/p5_mv02_hamd_auxiliary_bridge/run_summary.json`
- `analysis/phase5_minimal_validation/p5_mv02_hamd_auxiliary_bridge/artifact_hygiene_audit.json`
- `analysis/phase5_minimal_validation/p5_mv02_hamd_auxiliary_bridge/metric_summary.csv`
- `analysis/phase5_minimal_validation/p5_mv02_hamd_auxiliary_bridge/metrics_by_seed.csv`
- `analysis/phase5_minimal_validation/p5_mv02_hamd_auxiliary_bridge/macro_summary.csv`
- `analysis/phase5_minimal_validation/p5_mv02_hamd_auxiliary_bridge/comparison_summary.csv`
- `analysis/phase5_minimal_validation/p5_mv02_hamd_auxiliary_bridge/model_split_audit.csv`
- `analysis/phase5_minimal_validation/p5_mv02_hamd_auxiliary_bridge/label_feature_audit.csv`
- `analysis/phase5_minimal_validation/p5_mv02_hamd_auxiliary_bridge/construct_proxy_map.csv`

Local-only artifact:

- `analysis/phase5_minimal_validation/p5_mv02_hamd_auxiliary_bridge/p5_mv02_local_predictions.csv`

## Blockers And Risks

- CMDC HAMD coverage is only 25/78 subjects, so CMDC cannot support a complete
  HAMD bridge.
- CMDC sanity results are worse than train mean for feature heads, especially
  eGeMAPS and early fusion; this argues against current cross-dataset HAMD
  claims.
- The PDCH pass is still based on frozen subject-level feature caches and
  shallow heads; it is a diagnostic step, not a full symptom-evidence model.

## Next Handoff

Do not start a broad full method from MV02 alone. Next useful work is either a
stronger inference-compatible identity/protocol control, a carefully bounded
evidence-localization pass over existing minimal outputs, or an audited
text/semantic feature variant for PDCH/EATD that keeps raw text local-only.
