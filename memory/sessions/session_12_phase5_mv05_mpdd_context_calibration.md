# Session Memory: Phase 5 MV05 MPDD Context Calibration

Status: complete
Last updated: 2026-08-05 UTC
Thread/task: focused subtask for `P5_MV05 mpdd_context_calibration`

## Scope

This session owns the Phase 5 minimal-validation row `P5_MV05
mpdd_context_calibration`. It implements, runs, audits, and records the MPDD
context-calibration experiment only. It does not revise the Phase 5 protocol,
start a full method, use MPDD test labels, or turn personality/age/gait into a
generic fourth-modality predictor.

## Current State

- Implemented `scripts/phase5_run_mv05_mpdd_context_calibration.py`.
- Default command completed successfully:

```bash
python scripts/phase5_run_mv05_mpdd_context_calibration.py
```

- The run used 175 labeled MPDD train subjects from
  `datasets/manifests/mpdd_avg_2026_subjects.csv`.
- Split policy was subject-level repeated 5-fold OOF over 5 seeds.
- Cached Phase 2 MPDD WavLM audio subject features and ResNet video subject
  features were read from the main checkout as read-only caches; no encoder
  features were re-extracted.
- MPDD test labels were not used; the local manifest has zero labeled test
  subjects available.
- Raw personality descriptions were parsed in memory into trait bins, but no
  raw descriptions or hashes were written.
- Gait summaries were used only for psychomotor context validation and were not
  model inputs.
- Artifact hygiene passed with no raw personality text, source paths, raw
  arrays/media, embeddings, weights, or row-level predictions in tracked
  outputs.

## Key Decisions

- Record `P5_MV05` as a runnable negative row:
  `blocked_no_context_calibration_gain`.
- The proposed calibrator improved overall ECE versus the raw AV baseline
  (`0.3421` to `0.1180`) while preserving QWK approximately (`0.0996` to
  `0.0981`), but it did not improve required subgroup calibration gaps.
- Age ECE gap worsened from `0.0487` to `0.0684`.
- Maximum personality/financial-stress bin ECE gap worsened from `0.3310` to
  `0.4649`.
- The AV-probability-only recalibrator had lower overall ECE (`0.0579`) and
  much lower age ECE gap (`0.0048`) than the proposed context calibrator.
- Do not claim positive RQ3 context-calibration evidence from this row.

## Files Owned Or Touched

- `scripts/phase5_run_mv05_mpdd_context_calibration.py`
- `analysis/phase5_minimal_validation/p5_mv05_mpdd_context_calibration/`
- `memory/sessions/session_12_phase5_mv05_mpdd_context_calibration.md`
- `MEMORY.md`

## Generated Artifacts

Regeneration command:

```bash
python scripts/phase5_run_mv05_mpdd_context_calibration.py
```

Versionable artifacts:

- `analysis/phase5_minimal_validation/p5_mv05_mpdd_context_calibration/report.md`
- `analysis/phase5_minimal_validation/p5_mv05_mpdd_context_calibration/run_summary.json`
- `analysis/phase5_minimal_validation/p5_mv05_mpdd_context_calibration/artifact_hygiene_audit.json`
- `analysis/phase5_minimal_validation/p5_mv05_mpdd_context_calibration/metric_summary.csv`
- `analysis/phase5_minimal_validation/p5_mv05_mpdd_context_calibration/metrics_by_seed.csv`
- `analysis/phase5_minimal_validation/p5_mv05_mpdd_context_calibration/subgroup_metric_summary.csv`
- `analysis/phase5_minimal_validation/p5_mv05_mpdd_context_calibration/subgroup_metrics_by_seed.csv`
- `analysis/phase5_minimal_validation/p5_mv05_mpdd_context_calibration/subgroup_gap_summary.csv`
- `analysis/phase5_minimal_validation/p5_mv05_mpdd_context_calibration/context_control_summary.csv`
- `analysis/phase5_minimal_validation/p5_mv05_mpdd_context_calibration/counterfactual_sensitivity_summary.csv`
- `analysis/phase5_minimal_validation/p5_mv05_mpdd_context_calibration/cohort_context_summary.csv`
- `analysis/phase5_minimal_validation/p5_mv05_mpdd_context_calibration/gait_psychomotor_context_summary.csv`
- `analysis/phase5_minimal_validation/p5_mv05_mpdd_context_calibration/diagnostic_availability.csv`
- `analysis/phase5_minimal_validation/p5_mv05_mpdd_context_calibration/feature_availability.csv`
- `analysis/phase5_minimal_validation/p5_mv05_mpdd_context_calibration/model_split_audit.csv`

Local-only ignored artifacts:

- `analysis/phase5_minimal_validation/p5_mv05_mpdd_context_calibration/p5_mv05_local_predictions.csv`
- `analysis/phase5_minimal_validation/p5_mv05_mpdd_context_calibration/p5_mv05_local_counterfactual_predictions.csv`

## Blockers And Risks

- Gender and health subgroup calibration remain blocked because structured
  `gender` and `health_condition` fields are empty in the MPDD manifest.
- Personality bins are derived from description cues and are diagnostic bins,
  not official labels.
- The proposed context calibrator worsened the largest subgroup ECE gaps, so it
  should not be used as positive method evidence.
- Context-only calibration has nontrivial calibration performance, reinforcing
  the need to avoid direct context shortcut claims.

## Next Handoff

Treat MV05 as complete and negative. Continue Phase 5 with other
minimal-validation rows or a clearly revised calibration design only if it
preserves the AV-probability-first mechanism and improves subgroup gaps against
the AV-probability-only control.
