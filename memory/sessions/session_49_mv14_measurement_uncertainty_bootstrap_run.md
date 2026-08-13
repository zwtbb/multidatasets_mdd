# Session Memory: MV14 Measurement-Uncertainty Bootstrap Run

Status: complete
Last updated: 2026-08-13 UTC
Thread/task: main agent continuation

## Scope

This session owns implementation and execution of the predeclared MV14
measurement-uncertainty/bootstrap run for the label-only E-DAIC/CMDC PHQ
C01-C08 psychometric measurement line.

It does not train multimodal models, export subject-level item rows, export
bootstrap draw indices, export fitted mirt model objects, export fitted
parameters or CI values, export factor/theta scores, authorize M0/M1/M2/M3 full
method construction, or rewrite public Git history.

## Current State

- MV14 run is complete at
  `/root/autodl-tmp/analysis/phase5_minimal_validation/p5_mv14_measurement_uncertainty_bootstrap/`.
- The run used the manifest-governed MV10 PHQ item loader and R
  `mirt::multipleGroup`.
- Requested tiers were smoke/core/DIF R=`10/200/100`.
- Core model stability effective R is `185/200`; the 15 non-effective core
  draws came from configural fit errors categorized as nonfinite or missing
  numeric runtime messages.
- DIF tier effective R is `100/100`.
- Bootstrap-stable MV10 anchors are `C01`, `C04`, `C05`, and `C07`.
- Loading DIF remains sparse: no item exceeds loading-DIF frequency `0.50`.
- Threshold DIF remains concentrated on `C02` and `C06`, with frequencies
  `0.80` and `0.76`.
- AIC/BIC model selection remains an uncertainty caveat: AIC most often selects
  `configural`, while BIC most often selects `scalar`.
- Artifact hygiene passed. The ignored local input is
  `analysis/phase5_minimal_validation/p5_mv14_measurement_uncertainty_bootstrap/local_mv14_phq_response_matrix.csv`.

## Key Decisions

- Treat MV14 as cautious PHQ partial-invariance uncertainty evidence, not as a
  full-method pass.
- The MV10/MV11/MV13 anchor map can be described as bootstrap-stable with
  conservative wording.
- C02/C06 threshold-DIF wording is strengthened by bootstrap localization, but
  full scalar invariance remains unsupported.
- Keep model-selection uncertainty visible: MV14 changes AIC preference from
  MV13's single-fit partial model to bootstrap-most-frequent configural, while
  BIC remains scalar.
- Optional `boot.mirt` and `boot.LR` tiers were skipped as runtime-bounded
  optional sensitivities; the tracked output records skip reasons aggregate-only.
- The full-method gate remains
  `blocked_but_publishable_diagnostic_direction`; next primary work is MV15
  latent-conditioned dataset identity predeclaration.

## Files Owned Or Touched

- `.gitignore`
- `scripts/phase5_run_mv14_measurement_uncertainty_bootstrap.py`
- `scripts/phase5_run_mv14_measurement_uncertainty_bootstrap.R`
- `scripts/phase5_full_method_gate_audit.py`
- `scripts/build_diagnostic_paper_claim_tables.py`
- `scripts/build_diagnostic_paper_results_sections.py`
- `analysis/phase5_minimal_validation/p5_mv14_measurement_uncertainty_bootstrap/`
- `analysis/phase5_minimal_validation/full_method_gate_audit/`
- `analysis/diagnostic_measurement_audit_paper/`
- `README.md`
- `docs/master_experiment_plan.md`
- `docs/experiment_issue_log.md`
- `docs/diagnostic_measurement_audit_paper_outline.md`
- `MEMORY.md`
- `memory/sessions/session_master_orchestration.md`
- `memory/sessions/session_49_mv14_measurement_uncertainty_bootstrap_run.md`

## Generated Artifacts

Regenerate MV14:

```bash
python scripts/phase5_run_mv14_measurement_uncertainty_bootstrap.py
```

Tracked MV14 aggregate outputs:

- `bootstrap_ladder_realization.csv`
- `bootstrap_runtime_summary.csv`
- `core_model_stability_summary.csv`
- `model_selection_frequency.csv`
- `invariance_decision_frequency.csv`
- `item_dif_stability_summary.csv`
- `itemfit_stability_summary.csv`
- `warning_failure_summary.csv`
- `optional_sensitivity_summary.csv`
- `runtime_versions.csv`
- `r_execution_summary.csv`
- `input_boundary_contract.csv`
- `input_response_category_support.csv`
- `psychometric_input_audit.csv`
- `mv11_mv13_mv14_alignment_summary.csv`
- `pass_fail_gate_assessment.csv`
- `gate_recommendations.csv`
- `report.md`
- `run_summary.json`
- `artifact_hygiene_audit.json`

Refresh downstream gates and manuscript scaffolds:

```bash
python scripts/phase5_full_method_gate_audit.py
python scripts/build_diagnostic_paper_claim_tables.py
python scripts/build_diagnostic_paper_results_sections.py
```

## Blockers And Risks

- Full method remains blocked; MV14 is label-only measurement uncertainty.
- Configural model stability remains imperfect: fit success `185/200` and
  convergence `120/200` in the core tier.
- CMDC still has only 77 PHQ item-labeled subjects, so wording should remain
  cautious even where bootstrap stability supports the anchor/DIF pattern.
- MV06 still has one incomplete local candidate and no agreement uncertainty
  interval layer, which matters only for stronger RQ4 wording.

## Next Handoff

Predeclare `P5_MV15 latent_conditioned_dataset_identity`: compare dataset
identity conditioned on available labels, label-derived theta, and legitimate
covariates using aggregate-only outputs. Keep theta tables, residualized
features, nuisance directions, row predictions, fitted parameters, and model
artifacts local-only.
