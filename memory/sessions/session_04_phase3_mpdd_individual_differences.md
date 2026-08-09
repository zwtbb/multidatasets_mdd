# Session Memory: Phase 3 MPDD Individual Differences Diagnostics

Status: complete
Last updated: 2026-08-05 UTC
Thread/task: Phase 3 MPDD individual differences, shortcuts, and subgroup calibration

## Scope

This session owns MPDD-AVG-2026 Phase 3 failure-mode diagnostics for
age/personality moderation, shortcut risk, subgroup performance/calibration, and
gait psychomotor context. It intentionally does not implement the final method,
minimal method validation, or cross-dataset experiments.

All code, reports, session memory, and Phase 3 outputs were written under the
current worktree. Raw MPDD data and large missing Phase 2 caches were read only
as sources; nothing was written to the main checkout.

## Current State

- Implemented `scripts/phase3_mpdd_individual_differences.py`.
- Default command completed successfully:

```bash
python scripts/phase3_mpdd_individual_differences.py
```

- Subject-level repeated 5-fold OOF over 5 seeds was used on the 175 locally
  labeled MPDD train subjects. No test labels were used.
- Default CI mode is lightweight for interactive diagnostics:
  - run-level subject bootstrap CIs are computed for Phase 3 diagnostic models;
  - subgroup CIs are computed for age/severity core metrics;
  - personality-bin subgroup rows retain point estimates and cross-seed spread.
  Command-line bootstrap arguments can be increased for paper-final
  sensitivity checks.
- Large Phase 2 MPDD feature/prediction CSVs are absent from this worktree and
  were read from the main checkout as a read-only cache. Phase 3 outputs stayed
  in the current worktree.
- Output hygiene audit passed: no raw personality text, raw paths, raw arrays,
  raw audio/video/IMU indicators, or source-path leakage were detected in
  generated text/CSV/JSON artifacts.
- The completed script, session memory, report, figures, hygiene audit, and
  lightweight summaries were imported into the main checkout by the master
  agent on 2026-08-05. Large recomputable prediction/detail files remain
  local-only in the source worktree.

## Key Results

- Personality-only TF-IDF carried a real diagnostic signal versus shuffled
  personality:
  - Macro-F1: 0.4217 vs 0.3055, delta +0.1162.
  - QWK: 0.2302 vs -0.0414, delta +0.2716.
  - Ordinal MAE: 0.5097 vs 0.7623, delta -0.2526.
- Personality age-swap counterfactuals were sensitive:
  - Personality actual vs counterfactual age-swap Macro-F1 delta +0.1231.
  - Counterfactual changed-prediction rate: elder 0.5977, young 0.6841.
  - Mean expected-severity shift: elder +0.1234, young -0.1117.
- Audio-video + personality early fusion did not materially improve over
  audio-video only:
  - Macro-F1 delta +0.0014.
  - QWK delta +0.0012.
  - Shuffling personality inside AVP did not hurt performance.
- Age-only was weak as a standalone shortcut:
  - age-only vs shuffled-age QWK delta -0.0134.
  - age-only Macro-F1 delta +0.0558 but near-zero QWK.
- Subgroup calibration/performance gaps are real enough to track:
  - largest age ECE gap recorded in run summary: 0.1322.
  - largest personality-bin ECE gap recorded in run summary: 0.2888.
  - severe class remains hardest; several ordinal models have severity-2
    accuracy near 0.10-0.13 and large severity-wise MAE gaps.
- Gait statistics show modest psychomotor context signal:
  - top absolute Spearman with PHQ-9: 0.2690 for a channel-0 motion-change
    statistic.
  - Gait remains context evidence only, not a fourth fused modality here.

## Key Decisions

- Stop on generic AVP personality concatenation for now: adding personality to
  A/V did not improve Phase 3 early-fusion performance.
- Go on personality shortcut/moderation diagnostics: personality-only,
  shuffled-personality, and counterfactual swap checks show strong sensitivity.
- Go on subgroup calibration audit: personality-bin and severity subgroup gaps
  are large enough to justify calibration-aware analysis before method design.
- Weak-go or stop on age-only shortcut: age alone has weak QWK despite some
  Macro-F1 lift; treat age as a subgroup/calibration axis rather than a direct
  predictive shortcut.
- Go on gait psychomotor context validation, but do not concatenate gait as a
  fourth modality in this Phase 3 task.
- Gender and health diagnostics are blocked until structured metadata exists.

## Files Owned Or Touched

- `.gitignore`
- `scripts/phase3_mpdd_individual_differences.py`
- `memory/sessions/session_04_phase3_mpdd_individual_differences.md`
- `analysis/phase3_diagnostics/mpdd_individual_differences/`

## Generated Artifacts

Primary lightweight artifacts:

- `analysis/phase3_diagnostics/mpdd_individual_differences/mpdd_individual_differences_report.md`
- `analysis/phase3_diagnostics/mpdd_individual_differences/phase3_run_summary.json`
- `analysis/phase3_diagnostics/mpdd_individual_differences/artifact_hygiene_audit.json`
- `analysis/phase3_diagnostics/mpdd_individual_differences/phase3_metric_summary.csv`
- `analysis/phase3_diagnostics/mpdd_individual_differences/phase3_metric_deltas.csv`
- `analysis/phase3_diagnostics/mpdd_individual_differences/subgroup_metric_summary.csv`
- `analysis/phase3_diagnostics/mpdd_individual_differences/subgroup_gap_summary.csv`
- `analysis/phase3_diagnostics/mpdd_individual_differences/personality_counterfactual_summary.csv`
- `analysis/phase3_diagnostics/mpdd_individual_differences/gait_psychomotor_top_correlations.csv`
- `analysis/phase3_diagnostics/mpdd_individual_differences/cohort_profile.csv`
- `analysis/phase3_diagnostics/mpdd_individual_differences/diagnostic_availability.csv`
- `analysis/phase3_diagnostics/mpdd_individual_differences/phase2_feature_cache_inventory.csv`
- `analysis/phase3_diagnostics/mpdd_individual_differences/phase2_reference_prediction_inventory.csv`
- `analysis/phase3_diagnostics/mpdd_individual_differences/*.png`

Local-only ignored recomputable details:

- `analysis/phase3_diagnostics/mpdd_individual_differences/phase3_model_predictions.csv`
- `analysis/phase3_diagnostics/mpdd_individual_differences/phase3_all_predictions_for_metrics.csv`
- `analysis/phase3_diagnostics/mpdd_individual_differences/subgroup_metrics_by_seed.csv`
- `analysis/phase3_diagnostics/mpdd_individual_differences/personality_counterfactual_sensitivity.csv`
- `analysis/phase3_diagnostics/mpdd_individual_differences/phase3_fold_summaries.csv`

## Blockers And Risks

- Structured `gender` and `health_condition` are empty in the current MPDD
  manifest, blocking gender-only, health-only, and gender/health subgroup
  calibration diagnostics.
- Personality bins are derived from numeric/descriptor cues inside personality
  descriptions and are diagnostic bins, not official labels.
- Default bootstrap counts are intentionally light for completion speed; rerun
  with higher `--bootstrap-resamples`, `--subgroup-bootstrap-resamples`, and
  `--gait-bootstrap-resamples` before using intervals as final paper evidence.
- Large Phase 2 feature/prediction caches used by this diagnostic are local
  generated artifacts and remain local-only by default.

## Next Handoff

Proceed to other Phase 3 failure-mode diagnostics in canonical order. Do not
start minimal method validation or full method design until Phase 3 diagnostics
across the planned sessions have been reviewed together.
