# Session Memory: MV16 DIF-Guided Calibration Design

Status: complete
Last updated: 2026-08-14 UTC
Thread/task: main agent continuation

## Scope

This session owns the predeclaration/design contract for `P5_MV16`
DIF-guided few-shot measurement calibration, the refreshed full-method gate,
and the related docs/memory updates.

It does not run MV16 calibration, start full M0/M1/M2/M3 construction, export
target-shot sampling maps, export participant-grain theta tables, export row
predictions, export calibration parameters, export fitted measurement
parameters, export feature matrices, or claim PHQ-HAMD latent scale linking.

## Current State

- MV16 design script is implemented at
  `/root/autodl-tmp/scripts/phase5_plan_mv16_dif_guided_calibration.py`.
- MV16 design artifacts are at
  `/root/autodl-tmp/analysis/phase5_minimal_validation/p5_mv16_dif_guided_calibration_design/`.
- MV16 design status is `ready_to_implement_mv16_dif_guided_calibration`.
- Artifact hygiene passed.
- Primary calibration directions are E-DAIC->CMDC and CMDC->E-DAIC over PHQ
  C01-C08 common constructs.
- k-shot target-label budgets are `0/5/10/20/40`.
- Locked anchors are `C01/C04/C05/C07`.
- Primary localized threshold-DIF items are `C02/C06`.
- The calibration ladder compares zero-shot source measurement, global affine
  theta calibration, global monotonic theta calibration, DIF-guided C02/C06
  threshold calibration, joint global+C02/C06 calibration, all-threshold target
  calibration, and direct target-domain adaptation.
- At design time, the full-method gate read `39` Phase 5 summaries and moved
  the ranked next action to MV16 implementation. This has now been superseded
  by the completed MV16 run in session 54.

## Key Decisions

- MV16 is a target measurement-calibration test, not a new shallow RQ1 head and
  not a feature-invariance test.
- MV16 cannot override MV15's feature-identity blocker; any low output identity
  or improved target calibration must be reported separately from upstream BGE
  feature invariance.
- Primary MV16 support requires a small-k DIF-guided gain: L3 or L4 must
  improve target theta MAE by at least `0.03` versus zero-shot source
  measurement and improve C02/C06 MAE versus global calibration in both
  directions for at least one k<=20.
- Anchor safety is mandatory: C01/C04/C05/C07 anchor-item MAE may not degrade
  by more than 5 percent relative to global calibration at the same k and
  direction.
- Direct itemwise and direct target-domain adaptation baselines are mandatory
  dimension-matched/practical comparators.

## Files Owned Or Touched

- `scripts/phase5_plan_mv16_dif_guided_calibration.py`
- `scripts/phase5_full_method_gate_audit.py`
- `analysis/phase5_minimal_validation/p5_mv16_dif_guided_calibration_design/`
- `analysis/phase5_minimal_validation/full_method_gate_audit/`
- `README.md`
- `docs/master_experiment_plan.md`
- `docs/experiment_issue_log.md`
- `docs/diagnostic_measurement_audit_paper_outline.md`
- `MEMORY.md`
- `memory/sessions/session_master_orchestration.md`
- `memory/sessions/session_52_mv16_dif_guided_calibration_design.md`

## Generated Artifacts

Regenerate this session's aggregate artifacts with:

```bash
python scripts/phase5_plan_mv16_dif_guided_calibration.py --overwrite
python scripts/phase5_full_method_gate_audit.py
python scripts/build_diagnostic_paper_claim_tables.py
python scripts/build_diagnostic_paper_results_sections.py
```

Tracked MV16 design outputs include dataset-direction, k-shot sampling,
item-role, calibration-ladder, model-comparison, metric, pass/fail,
input-boundary, local-only-boundary, implementation-queue, method-source,
source-evidence, report, run summary, and artifact-hygiene files.

## Blockers And Risks

- Full method remains blocked.
- Superseded by
  `memory/sessions/session_54_mv16_dif_guided_calibration_run.md`: MV16 has now
  been implemented and run as bounded/negative calibration evidence.
- E-DAIC/CMDC BGE feature identity remains high from MV15, so MV16 must keep
  calibration claims separate from representation-invariance claims.
- CMDC item-labeled N is small, so k=40 and reverse-direction analyses require
  explicit skipped-row/coverage reporting if folds become sparse.
- PDCH/HAMD remains deferred for PHQ-HAMD linking; MV16 design does not
  authorize cross-scale latent linking.

## Next Handoff

Superseded by
`memory/sessions/session_54_mv16_dif_guided_calibration_run.md`. Use the
completed MV16 aggregate outputs and refreshed full-method gate for future
interpretation. Keep target-shot maps, theta tables, calibration parameters,
fitted measurement parameters, row predictions, feature matrices, and model
artifacts local-only.
