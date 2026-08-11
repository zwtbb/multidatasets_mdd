# Session Memory: MV13 External Psychometric Replication

Status: complete
Last updated: 2026-08-11 UTC
Thread/task: main agent continuation

## Scope

This session owns the MV13 external psychometric replication design and run for
the label-only E-DAIC/CMDC PHQ C01-C08 measurement model. It installs and
version-captures the external R psychometric runtime, runs an aggregate-only
R `mirt::multipleGroup` model ladder, refreshes the Phase 5 full-method gate,
and updates orchestration docs and memory.

It does not train multimodal models, read raw text/media/gait files, export
subject-level item rows, export theta/factor scores, export fitted item
parameters or parameter CI values, save fitted model objects, or authorize full
M0/M1/M2/M3 method construction.

## Current State

- R 4.1.2, lavaan 0.6.10, archived R-compatible Deriv 4.1.3, and archived
  mirt 1.35.1 are installed and version-captured.
- MV13 design is complete at
  `/root/autodl-tmp/analysis/phase5_minimal_validation/p5_mv13_external_psychometric_replication_design/`
  with `design_status=ready_for_external_replication_run`.
- MV13 run is complete at
  `/root/autodl-tmp/analysis/phase5_minimal_validation/p5_mv13_external_psychometric_replication/`
  with `status=complete_external_mirt_with_convergence_warnings`.
- External `mirt::multipleGroup` qualitatively replicates MV11:
  - confirmed MV10 anchors: `C01`, `C04`, `C05`, `C07`;
  - loading-DIF flags: `0`;
  - threshold-DIF flags: `C02`, `C06`;
  - best AIC core model: `partial_mv10`;
  - best BIC core model: `scalar`;
  - MV11/MV13 alignment rows: `6/6`.
- The configural core model did not converge within 3000 EM cycles. Metric,
  scalar, and MV10 partial models converged. Keep this as a manuscript caveat.
- Parameter CI availability is aggregate-only: the partial model SE refit
  converged with 45 finite SEs, but CI values and parameter tables are not
  tracked.
- The refreshed full-method gate reads 34 Phase 5 summaries, keeps
  `full_method_allowed=false`, and ranks
  `NEXT_PREDECLARE_MV14_MEASUREMENT_UNCERTAINTY_BOOTSTRAP` first.

## Key Decisions

- Treat MV13 as external label-only measurement replication, not multimodal
  method success.
- Do not hide the configural convergence warning. It strengthens the rationale
  for MV14 uncertainty/stability analysis.
- Keep the local R item-response matrix ignored, even though subject IDs are
  not included, because it is participant-grain label data.
- Keep full parameter values, theta/factor scores, fitted model objects,
  bootstrap samples, and any subject-level psychometric rows local-only.
- Future R package updates should be version-captured. Current server R is
  4.1.2, so archived package versions may be needed when current CRAN packages
  require newer R APIs.

## Files Owned Or Touched

- `.gitignore`
- `scripts/phase5_plan_mv13_external_psychometric_replication.py`
- `scripts/phase5_run_mv13_external_psychometric_replication.py`
- `scripts/phase5_run_mv13_external_psychometric_replication.R`
- `scripts/phase5_full_method_gate_audit.py`
- `analysis/phase5_minimal_validation/experiment_matrix.csv`
- `analysis/phase5_minimal_validation/p5_mv13_external_psychometric_replication_design/`
- `analysis/phase5_minimal_validation/p5_mv13_external_psychometric_replication/`
- `analysis/phase5_minimal_validation/full_method_gate_audit/`
- `README.md`
- `docs/diagnostic_measurement_audit_paper_outline.md`
- `docs/experiment_issue_log.md`
- `MEMORY.md`
- `memory/sessions/session_37_diagnostic_paper_claim_tables.md`
- `memory/sessions/session_master_orchestration.md`
- `memory/sessions/session_45_diagnostic_paper_results_sections.md`
- `memory/sessions/session_46_mv13_external_psychometric_replication.md`

## Generated Artifacts

Regenerate design:

```bash
python scripts/phase5_plan_mv13_external_psychometric_replication.py --overwrite
```

Regenerate run:

```bash
python scripts/phase5_run_mv13_external_psychometric_replication.py
```

Refresh gate:

```bash
python scripts/phase5_full_method_gate_audit.py
```

Refresh paper scaffolds:

```bash
python scripts/build_diagnostic_paper_claim_tables.py
python scripts/build_diagnostic_paper_results_sections.py
```

Tracked MV13 aggregate outputs include model fit, invariance comparisons, item
DIF LRT summaries, anchor confirmation, item-fit summaries, parameter-CI
availability, runtime versions, MV11/MV13 alignment, gate recommendations,
reports, run summaries, and hygiene audits.

The diagnostic paper claim tables now include 13 key findings and 17
literature-positioning rows, including MV13 and external mirt references.

Ignored local-only output:

- `/root/autodl-tmp/analysis/phase5_minimal_validation/p5_mv13_external_psychometric_replication/local_mirt_phq_response_matrix.csv`

## Blockers And Risks

- CMDC has only 77 PHQ item-labeled subjects, so item-level threshold/DIF
  wording needs MV14 uncertainty/stability evidence.
- The configural mirt model reached the 3000-cycle limit without convergence;
  this does not overturn the qualitative replication, but it must remain in
  reports and manuscript caveats.
- MV13 checks `Y -> theta` measurement only. It does not test feature
  prediction, cross-dataset theta calibration, or observed-scale safety.
- Full method remains blocked by the Phase 5 gate.

## Next Handoff

Predeclare MV14 measurement-uncertainty/bootstrap. It should quantify anchor
support, loading-DIF and threshold-DIF selection stability, fit-model selection
stability, convergence frequency, and SE/CI availability under the same
local-only item-response boundary. Track only aggregate stability summaries and
hygiene outputs.
