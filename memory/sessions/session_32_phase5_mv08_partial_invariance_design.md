# Session Memory: Phase 5 MV08 Partial-Invariance Design

Status: complete
Last updated: 2026-08-11 UTC
Thread/task: main agent P5_MV08 design/readiness audit

## Scope

This session turns the RQ1 method pivot into a script-generated Phase 5
minimal-validation design contract. It does not train a model, read raw
text/media, or authorize full M0/M1/M2/M3 construction.

## Current State

- This design session has been superseded by implementation/result session
  `memory/sessions/session_33_phase5_mv08_partial_invariance_pilot.md`.
- Added and ran
  `scripts/phase5_plan_mv08_partial_invariance_measurement.py`.
- Generated
  `analysis/phase5_minimal_validation/p5_mv08_partial_invariance_measurement_design/`.
- Current MV08 design status:
  `ready_to_implement_partial_invariance_validation`.
- Active item-supervised MV08 datasets:
  - E-DAIC PHQ-8: 219 item-labeled train/dev subjects;
  - CMDC PHQ-9: 77 item-labeled subjects;
  - PDCH HAMD-17: 99 item-labeled subjects.
- CMDC HAMD-17 has only 25 item-labeled subjects and is limited to sanity
  checking.
- EATD SDS and MPDD PHQ-9 remain total-only and are not active item-level MV08
  training sources.
- The full-method gate includes `P5_MV08_design` as design evidence. The
  actual MV08 pilot has now been run and is recorded in session_33.

## Key Decisions

- P5_MV08 must compare three levels before any RQ1 claim changes:
  total-score floors, fixed construct-map heads, and partial-invariance ordinal
  latent measurement heads.
- DIF is treated as the target measurement heterogeneity signal, not as a
  hidden nuisance residual.
- The first MV08 pilot should use E-DAIC/CMDC/PDCH only; moderator DIF for
  age/personality/protocol belongs to a later row after MV08 evidence exists.
- Raw row predictions, latent scores, learned loadings/thresholds, learned
  model files, and transformed features remain local-only.

## Files Owned Or Touched

- `scripts/phase5_plan_mv08_partial_invariance_measurement.py`
- `scripts/phase5_build_minimal_validation_protocol.py`
- `scripts/phase5_full_method_gate_audit.py`
- `analysis/phase5_minimal_validation/p5_mv08_partial_invariance_measurement_design/`
- `analysis/phase5_minimal_validation/experiment_matrix.csv`
- `analysis/phase5_minimal_validation/metric_contract.csv`
- `analysis/phase5_minimal_validation/minimal_validation_protocol.md`
- `analysis/phase5_minimal_validation/readiness_audit.json`
- `analysis/phase5_minimal_validation/full_method_gate_audit/`
- `MEMORY.md`
- `docs/master_experiment_plan.md`
- `docs/experiment_issue_log.md`
- `memory/sessions/session_master_orchestration.md`
- `memory/sessions/session_32_phase5_mv08_partial_invariance_design.md`

## Generated Artifacts

Regeneration commands:

```bash
python scripts/phase5_plan_mv08_partial_invariance_measurement.py
python scripts/phase5_build_minimal_validation_protocol.py
python scripts/phase5_full_method_gate_audit.py
```

Versionable MV08 design outputs:

- `report.md`
- `run_summary.json`
- `artifact_hygiene_audit.json`
- `label_contract_coverage.csv`
- `construct_anchor_matrix.csv`
- `measurement_model_contract.csv`
- `dif_parameter_contract.csv`
- `readiness_gate.csv`
- `implementation_queue.csv`
- `method_source_refs.csv`

## Blockers And Risks

- The MV08 trainer/pilot now exists and has run; see session_33 for result
  details.
- The first MV08 design can be underpowered for HAMD transfer because CMDC
  HAMD has only 25 usable subjects.
- E-DAIC MV06 agreement remains underpowered if a stronger RQ4 claim is needed.
- Remote history rewrite for older row-level dataset tables remains optional
  and requires explicit user approval.

## Next Handoff

The original implementation handoff is complete. Future work should use
session_33: analyze why the first MV08 implementation underperformed the
total-score floor, then decide whether to predeclare a stronger measurement
revision or freeze the row as diagnostic/negative evidence.
