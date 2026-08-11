# Session Memory: Phase 5 MV08b Total-Anchored Residual Design

Status: complete
Last updated: 2026-08-11 UTC
Thread/task: main agent MV08b predeclared measurement revision design

## Scope

This session predeclares the only allowed mechanism-changing follow-up to the
negative `P5_MV08` partial-invariance pilot. It does not train a model, read raw
text/media, read row-level predictions, export subject-level rows, or authorize
full M0/M1/M2/M3 construction.

## Current State

- Implemented and ran
  `scripts/phase5_plan_mv08b_total_anchored_residual_measurement.py`.
- Generated design outputs under
  `analysis/phase5_minimal_validation/p5_mv08b_total_anchored_residual_measurement_design/`.
- Current design status:
  `ready_to_implement_mv08b_total_anchored_residual_measurement`.
- Updated the Phase 5 protocol matrix so `P5_MV08b` is now a formal
  minimal-validation row.
- Updated the full-method gate to include `P5_MV08b_design` as the 25th
  evidence row. Gate status remains
  `blocked_but_publishable_diagnostic_direction`, with
  `full_method_allowed=false`.
- At design time, the top-ranked gate action was
  `NEXT_IMPLEMENT_MV08B_TOTAL_ANCHORED_RESIDUAL_MEASUREMENT`.
- Follow-up implementation/run is complete in
  `memory/sessions/session_36_phase5_mv08b_total_anchored_residual_run.md`.
  MV08b failed its identity gate and should now be frozen with MV08 as negative
  RQ1 diagnostic evidence under the current frozen-BGE/shallow-measurement
  contract.

## Key Decisions

- The current MV08 contract remains negative evidence unless MV08b later
  passes its predeclared gates.
- MV08b changes the mechanism rather than retuning a shallow BGE item head:
  first predict total or latent severity, then model sparse item residuals only
  after severity anchoring.
- MV08b must compare:
  - `B0_train_mean_items`;
  - `B1_total_score_floor`;
  - `B2_fixed_construct_map`;
  - `M2b_total_anchored_residual_measurement`.
- MV08b passes only if it beats the total-score and fixed-map floors on at
  least two pooled active dataset slices and keeps prediction identity balanced
  accuracy no higher than current MV08 M2 (`0.900`).
- HAMD remains a separate clinical measurement stress test. HAMD improvement
  alone cannot authorize a shared PHQ-core RQ1 claim.
- Sparse ordinal thresholds must be pooled or collapsed before allowing
  item/scale-specific threshold offsets. Learned thresholds and parameters
  remain local-only.
- If MV08b fails, freeze MV08/MV08b as negative RQ1 diagnostic evidence and
  pivot writing toward a measurement-audit paper rather than another shallow
  feature-head iteration.

## Files Owned Or Touched

- `scripts/phase5_plan_mv08b_total_anchored_residual_measurement.py`
- `scripts/phase5_build_minimal_validation_protocol.py`
- `scripts/phase5_full_method_gate_audit.py`
- `analysis/phase5_minimal_validation/p5_mv08b_total_anchored_residual_measurement_design/`
- `analysis/phase5_minimal_validation/full_method_gate_audit/`
- `analysis/phase5_minimal_validation/experiment_matrix.csv`
- `analysis/phase5_minimal_validation/metric_contract.csv`
- `analysis/phase5_minimal_validation/minimal_validation_protocol.md`
- `analysis/phase5_minimal_validation/readiness_audit.json`
- `MEMORY.md`
- `docs/master_experiment_plan.md`
- `docs/experiment_issue_log.md`
- `memory/sessions/session_22_phase5_full_method_gate_audit.md`
- `memory/sessions/session_34_phase5_mv08_error_analysis.md`
- `memory/sessions/session_35_phase5_mv08b_total_anchored_residual_design.md`
- `memory/sessions/session_master_orchestration.md`

## Generated Artifacts

Regeneration commands:

```bash
python scripts/phase5_plan_mv08b_total_anchored_residual_measurement.py --overwrite
python scripts/phase5_build_minimal_validation_protocol.py
python scripts/phase5_full_method_gate_audit.py
```

Versionable MV08b design outputs:

- `analysis/phase5_minimal_validation/p5_mv08b_total_anchored_residual_measurement_design/run_summary.json`
- `analysis/phase5_minimal_validation/p5_mv08b_total_anchored_residual_measurement_design/report.md`
- `analysis/phase5_minimal_validation/p5_mv08b_total_anchored_residual_measurement_design/source_evidence_summary.csv`
- `analysis/phase5_minimal_validation/p5_mv08b_total_anchored_residual_measurement_design/model_ladder_contract.csv`
- `analysis/phase5_minimal_validation/p5_mv08b_total_anchored_residual_measurement_design/residual_target_contract.csv`
- `analysis/phase5_minimal_validation/p5_mv08b_total_anchored_residual_measurement_design/threshold_policy_contract.csv`
- `analysis/phase5_minimal_validation/p5_mv08b_total_anchored_residual_measurement_design/design_decision_gate.csv`
- `analysis/phase5_minimal_validation/p5_mv08b_total_anchored_residual_measurement_design/implementation_queue.csv`
- `analysis/phase5_minimal_validation/p5_mv08b_total_anchored_residual_measurement_design/method_source_refs.csv`
- `analysis/phase5_minimal_validation/p5_mv08b_total_anchored_residual_measurement_design/artifact_hygiene_audit.json`

## Blockers And Risks

- This design session alone is not result evidence; the result evidence now
  lives in session 36.
- Full method work remains blocked because MV08b has been implemented and did
  not pass the total-score/fixed-map/identity gate bundle.
- The most likely failure mode is that severity anchoring explains nearly all
  stable item signal, leaving residual heads unable to beat the simple floors.
- E-DAIC MV06 agreement remains underpowered if a stronger RQ4 claim is needed.
- Public remote history rewrite remains optional and requires explicit user
  approval.

## Next Handoff

This design handoff has been consumed by the MV08b run session. Future work
should cite session 36 for result evidence, freeze MV08/MV08b as negative RQ1
diagnostic evidence, and keep row-level residual predictions, latent scores,
learned thresholds, learned parameters, model files, and private review
material local-only.
