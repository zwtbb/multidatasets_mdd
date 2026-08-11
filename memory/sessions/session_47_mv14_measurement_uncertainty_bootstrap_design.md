# Session Memory: MV14 Measurement-Uncertainty Bootstrap Design

Status: complete
Last updated: 2026-08-11 UTC
Thread/task: main agent continuation

## Scope

This session owns the MV14 measurement-uncertainty/bootstrap predeclaration for
the label-only E-DAIC/CMDC PHQ C01-C08 psychometric measurement line. It reads
master memory, MV13 session memory, MV13 aggregate outputs, the full-method
gate, and official/primary mirt documentation, then writes a design contract
for the future bootstrap run.

It does not run the bootstrap, train multimodal models, read raw text/media,
export item-response rows, export resampling draws, export fitted parameters,
export confidence-interval values, export factor/theta scores, or authorize
full M0/M1/M2/M3 method construction.

## Current State

- MV14 design is complete at
  `/root/autodl-tmp/analysis/phase5_minimal_validation/p5_mv14_measurement_uncertainty_bootstrap_design/`
  with `design_status=ready_to_implement_mv14_measurement_uncertainty_bootstrap`.
- Runtime preflight passes for Rscript, mirt 1.35.1, `multipleGroup`, `DIF`,
  `boot.mirt`, and `boot.LR`.
- The design exports 5 bootstrap tiers:
  - smoke runtime tier, R=10, not claimable;
  - core model stability tier, R=200;
  - item-DIF stability tier, R=100;
  - optional `boot.mirt` SE-availability sensitivity, R=100;
  - optional `boot.LR` parametric LRT sensitivity, R=100.
- Stability metrics are predeclared for convergence frequency, AIC/BIC
  selection frequency, anchor support, loading-DIF frequency, threshold-DIF
  frequency, SE/CI availability, item-fit flag frequency, and MV11/MV13/MV14
  alignment.
- Full-method gate now reads 35 evidence rows and keeps
  `full_method_allowed=false`, `gate_status=blocked_but_publishable_diagnostic_direction`.
- The ranked next action is now
  `NEXT_IMPLEMENT_MV14_MEASUREMENT_UNCERTAINTY_BOOTSTRAP`.

## Key Decisions

- MV14 is uncertainty evidence only. It can strengthen or downgrade
  item-level PHQ anchor/DIF wording, but it cannot authorize full multimodal
  method work.
- Bootstrap resampling unit is subject row within dataset group, preserving the
  E-DAIC and CMDC group sizes.
- Stable-anchor wording requires all four MV10/MV11/MV13 anchors
  `C01/C04/C05/C07` to show support frequency at least `0.70`; any anchor below
  `0.60` requires a downgrade.
- Loading DIF should remain sparse: no more than one item above frequency
  `0.50`, and MV10 anchors should remain below `0.30`.
- Threshold DIF wording for `C02`/`C06` is allowed only if the bootstrap
  frequency remains concentrated there.
- AIC/BIC disagreement is an expected reportable uncertainty dimension, not a
  reason to force one winner.
- Bootstrap inputs, draw indices, fitted parameters, full CI values,
  factor/theta scores, model objects, and detailed logs remain local-only.

## Files Owned Or Touched

- `scripts/phase5_plan_mv14_measurement_uncertainty_bootstrap.py`
- `scripts/phase5_full_method_gate_audit.py`
- `analysis/phase5_minimal_validation/experiment_matrix.csv`
- `analysis/phase5_minimal_validation/p5_mv14_measurement_uncertainty_bootstrap_design/`
- `analysis/phase5_minimal_validation/full_method_gate_audit/`
- `README.md`
- `docs/diagnostic_measurement_audit_paper_outline.md`
- `docs/experiment_issue_log.md`
- `docs/master_experiment_plan.md`
- `MEMORY.md`
- `memory/sessions/session_master_orchestration.md`
- `memory/sessions/session_47_mv14_measurement_uncertainty_bootstrap_design.md`

## Generated Artifacts

Regenerate MV14 design:

```bash
python scripts/phase5_plan_mv14_measurement_uncertainty_bootstrap.py --overwrite
```

Refresh full-method gate:

```bash
python scripts/phase5_full_method_gate_audit.py
```

Tracked MV14 design outputs:

- `bootstrap_ladder_contract.csv`
- `stability_metric_contract.csv`
- `local_only_boundary_contract.csv`
- `input_boundary_contract.csv`
- `pass_fail_gate_contract.csv`
- `implementation_queue.csv`
- `method_source_refs.csv`
- `source_evidence_summary.csv`
- `runtime_preflight.csv`
- `report.md`
- `run_summary.json`
- `artifact_hygiene_audit.json`

## Blockers And Risks

- The future bootstrap run may be computationally expensive because the item-DIF
  tier can require up to 20 mirt refits per bootstrap draw.
- MV13's configural model did not converge within 3000 EM cycles; MV14 must
  report convergence frequencies rather than hiding failures.
- CMDC has only 77 PHQ item-labeled subjects, so wide or unstable bootstrap
  intervals are possible and should lead to conservative manuscript wording.
- Full method remains blocked.

## Next Handoff

Implement the MV14 Python/R bootstrap runner against the design contract. Start
with the smoke tier, verify hygiene, then run the core and item-DIF tiers.
After the run, refresh the full-method gate, README, issue log, master memory,
paper outline/scaffolds, and clean-publish only aggregate outputs.
