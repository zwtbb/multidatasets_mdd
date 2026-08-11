# Session Memory: Phase 5 MV12 Two-Stage Latent-Target Run

Status: active
Last updated: 2026-08-11 UTC
Thread/task: main agent continuation

## Scope

This session owns the implemented P5_MV12 two-stage latent-target experiment.
It runs the predeclared PHQ `Y_to_theta` then BGE `X_to_theta` validation and
refreshes downstream full-method gate, paper scaffold, issue log, and memory.
It should not publish subject-level theta scores, fitted measurement
parameters, row predictions, transformed features, projection directions, or
model artifacts.

## Current State

- MV12 run is complete at
  `/root/autodl-tmp/analysis/phase5_minimal_validation/p5_mv12_two_stage_latent_target/`.
- Status is `blocked_theta_gain_not_observed_scale_safe`.
- Artifact hygiene passed.
- The runner fits train-fold label-only graded-response-style PHQ measurement
  targets over E-DAIC/CMDC, using `C01`, `C02`, `C04`, `C05`, `C06`, and `C07`
  as primary theta items.
- Primary anchors are `C01`, `C04`, `C05`, and `C07`; `C02` and `C06` remain
  threshold-DIF-aware; `C03` and `C08` remain sensitivity-only.
- M12a improves same-dataset theta MAE versus the train-mean theta floor on
  E-DAIC (`-0.078`) and CMDC (`-0.146`).
- M12a fails observed-scale safety versus direct itemwise Ridge on E-DAIC
  (`+0.004` observed macro MAE) and CMDC (`+0.067`).
- External theta transfer does not beat the train-mean theta floor in either
  direction.
- Conditional shared-latent identity BA for M12a is `0.602`, improving over the
  MV09 E-DAIC/CMDC conditional feature-identity reference `0.991` and passing
  the preferred `0.700` threshold.
- Full-method gate now reads 31 Phase 5 evidence rows and remains
  `blocked_but_publishable_diagnostic_direction` with
  `full_method_allowed=false`.
- Diagnostic paper tables now contain 11 key numeric findings, including the
  MV12 run.

## Key Decisions

- Treat MV12 as bounded measurement-shift evidence, not as a positive
  shared-latent method.
- The interesting positive signal is at the latent identity layer, not the
  observed item-output layer.
- Do not start full M0/M1/M2/M3 construction from this result.
- Next decision: either run an aggregate-only MV12 error/Pareto analysis, or
  freeze the latent-target line and draft with MV12 as a diagnostic result.

## Files Owned Or Touched

- `scripts/phase5_run_mv12_two_stage_latent_target.py`
- `analysis/phase5_minimal_validation/p5_mv12_two_stage_latent_target/`
- `scripts/phase5_full_method_gate_audit.py`
- `scripts/build_diagnostic_paper_claim_tables.py`
- `analysis/phase5_minimal_validation/full_method_gate_audit/`
- `analysis/diagnostic_measurement_audit_paper/`
- `analysis/phase5_minimal_validation/experiment_matrix.csv`
- `README.md`
- `docs/diagnostic_measurement_audit_paper_outline.md`
- `docs/experiment_issue_log.md`
- `MEMORY.md`
- `memory/sessions/session_master_orchestration.md`
- `memory/sessions/session_43_mv12_two_stage_latent_target_run.md`

## Generated Artifacts

Regenerate MV12 run with:

```bash
python scripts/phase5_run_mv12_two_stage_latent_target.py
```

Key tracked aggregate outputs:

- `comparison_summary.csv`
- `metric_summary.csv`
- `metrics_by_seed.csv`
- `target_generation_summary.csv`
- `target_reliability_summary.csv`
- `identity_probe_by_seed.csv`
- `identity_probe_summary.csv`
- `transfer_summary.csv`
- `leakage_audit.csv`
- `model_split_audit.csv`
- `label_feature_audit.csv`
- `construct_target_map.csv`
- `local_artifact_manifest.csv`
- `report.md`
- `run_summary.json`
- `artifact_hygiene_audit.json`

Ignored local-only output:

- `p5_mv12_local_predictions.csv`

Refresh downstream gates and paper tables with:

```bash
python scripts/phase5_full_method_gate_audit.py
python scripts/build_diagnostic_paper_claim_tables.py
```

## Blockers And Risks

- MV12 does not pass observed-scale safety; theta improvements do not reliably
  translate back to better PHQ item-scale predictions.
- MV12 does not pass external theta transfer; E-DAIC-to-CMDC and
  CMDC-to-E-DAIC theta transfer are worse than train-mean theta floors.
- Conditional post-mapping item identity remains high, which is expected for
  scale-specific observed outputs but must be described carefully.
- The local prediction table is useful for later aggregate error analysis but
  must remain ignored and untracked.

## Next Handoff

Decide whether to implement an aggregate-only MV12 error/Pareto analysis that
compares theta utility, observed-scale safety, transfer, and identity trade-offs
across MV07/MV07b/MV07c/MV08/MV08b/MV12. If not, freeze MV12 as the current
latent-target diagnostic result and continue manuscript drafting from the
updated claim boundaries.
