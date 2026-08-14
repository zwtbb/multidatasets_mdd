# Session Memory: MV16 DIF-Guided Calibration Run

Status: complete
Last updated: 2026-08-14 UTC
Thread/task: main agent continuation

## Scope

This session owns implementation, execution, and aggregate reporting for the
predeclared P5_MV16 DIF-guided few-shot PHQ measurement-calibration runner.

It does not start full M0/M1/M2/M3 method construction, change the MV16 design
contract after seeing results, export calibration subject maps, export row-level
predictions, export theta tables, export fitted measurement parameters, export
calibration parameter values, or claim BGE feature invariance.

## Current State

- `scripts/phase5_run_mv16_dif_guided_calibration.py` now implements the
  predeclared E-DAIC->CMDC and CMDC->E-DAIC calibration directions at
  k=`0/5/10/20/40`.
- The runner uses manifest-governed PHQ labels and frozen BGE subject features
  only.
- Target calibration/evaluation splits are subject-disjoint:
  E-DAIC->CMDC uses E-DAIC train as source, CMDC train-fold subjects as target
  calibration candidates, and CMDC validation-fold subjects as target
  evaluation.
- CMDC->E-DAIC uses CMDC train-fold subjects as source, E-DAIC train subjects
  as target calibration candidates, and E-DAIC dev subjects as target
  evaluation.
- L0-L6 and B1/B2 comparators are reported where feasible; k=`0` target-label
  calibration rows are explicitly skipped.
- MV16 status is `blocked_no_dif_guided_small_k_gain`.
- Subject-overlap, ladder-completeness, anchor-safety, direct-baseline,
  output-identity-reporting, and artifact-hygiene gates pass.
- The DIF-guided small-k mechanism gate fails because support is not present in
  both directions for k<=20.
- Best supported row is
  `D1_edaic_source_cmdc_target`/`M16d_global_plus_C02_C06` at k=`10`.
- Best L4 small-k delta theta MAE versus L0 is `-0.227`.
- L4 small-k output identity BA remains high at `0.984`.
- Full method remains blocked.

## Key Decisions

- Treat MV16 as a bounded/negative calibration stress test. It is useful for
  showing that localized C02/C06 DIF diagnosis alone does not yield a robust
  both-direction parameter-efficient adaptation result under the current BGE
  predictor contract.
- Do not use MV16 as a positive method claim, feature-invariance evidence, or
  full-method authorization.
- Manuscript consolidation has since produced aggregate-only draft v0.1 around
  measurement shift, measurement validity, conditional identity, and bounded
  negative evidence.
- MV06 agreement uncertainty has since been added. The remaining optional
  evidence step is completion of the one incomplete local candidate before
  stronger RQ4 wording.

## Files Owned Or Touched

- `scripts/phase5_run_mv16_dif_guided_calibration.py`
- `scripts/phase5_full_method_gate_audit.py`
- `scripts/build_diagnostic_paper_claim_tables.py`
- `scripts/build_diagnostic_paper_results_sections.py`
- `analysis/phase5_minimal_validation/p5_mv16_dif_guided_calibration/`
- `analysis/phase5_minimal_validation/full_method_gate_audit/`
- `analysis/diagnostic_measurement_audit_paper/`
- `README.md`
- `docs/experiment_direction.md`
- `docs/master_experiment_plan.md`
- `docs/experiment_issue_log.md`
- `docs/diagnostic_measurement_audit_paper_outline.md`
- `MEMORY.md`
- `memory/sessions/session_54_mv16_dif_guided_calibration_run.md`

## Generated Artifacts

Regenerate this session and downstream aggregate artifacts with:

```bash
python scripts/phase5_run_mv16_dif_guided_calibration.py
python scripts/phase5_full_method_gate_audit.py
python scripts/build_diagnostic_paper_claim_tables.py
python scripts/build_diagnostic_paper_results_sections.py
```

Primary checked outputs:

- `analysis/phase5_minimal_validation/p5_mv16_dif_guided_calibration/run_summary.json`
- `analysis/phase5_minimal_validation/p5_mv16_dif_guided_calibration/pass_fail_gate_results.csv`
- `analysis/phase5_minimal_validation/p5_mv16_dif_guided_calibration/model_comparison_summary.csv`
- `analysis/phase5_minimal_validation/p5_mv16_dif_guided_calibration/output_identity_summary.csv`
- `analysis/phase5_minimal_validation/p5_mv16_dif_guided_calibration/report.md`
- `analysis/phase5_minimal_validation/full_method_gate_audit/run_summary.json`
- `analysis/diagnostic_measurement_audit_paper/key_numeric_findings.csv`
- `analysis/diagnostic_measurement_audit_paper/baselines_failure_modes_measurement_results.md`

## Blockers And Risks

- Full method remains blocked.
- MV16 target reference theta is an evaluation construct derived from target
  labels and is not used for calibration/training; this should be described as
  an evaluation reference, not as deployable target-side scoring.
- Output identity remains high, so low-dimensional calibration should not be
  confused with upstream feature invariance.
- CMDC PHQ item-labeled N remains small, so few-shot direction asymmetry should
  be interpreted cautiously.

## Next Handoff

Use the generated manuscript draft v0.1 for human editing, bibliography
conversion, and cross-reference cleanup around a
measurement-shift/measurement-validity diagnostic paper. Optional follow-up:
resolve the one incomplete local MV06 candidate while keeping workbooks,
snippets, locators, subject-level rows, and notes local-only.
