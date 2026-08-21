# Session Memory: MV19 PHQ Finite-Sample Simulation

Status: complete
Last updated: 2026-08-21 UTC
Thread/task: Continue post-review measurement-validity route; run MV19

## Scope

This session owns MV19: a label-only observed-N simulation for the E-DAIC/CMDC
PHQ C01-C08 measurement line. It quantifies whether the current MV10/MV14
decision screen can falsely localize C02/C06 threshold DIF under a
scalar-invariant H0 and recover C02/C06 plus the predeclared anchor set under
an observed-like C02/C06 threshold-DIF H1.

It does not train multimodal models, read raw text/media, export real
participant identifiers, export fitted psychometric parameters, export theta
scores, export simulated participant-grain response rows, or authorize full
M0/M1/M2/M3 construction.

## Current State

MV19 is complete at
`analysis/phase5_minimal_validation/p5_mv19_phq_finite_sample_psychometric_simulation/`.

The run used:

- the MV10 manifest-governed PHQ item loader;
- observed complete-item sample sizes: E-DAIC `219`, CMDC `77`;
- dataset-specific empirical shared-PHQ total severity distributions;
- 500 simulations per world with seed `20260822`;
- scalar-invariant H0;
- C02/C06 threshold-DIF H1 using observed MV10 C02/C06 dataset-logit
  coefficients as the H1 offsets;
- the MV10 approximate loading, threshold, and partial-anchor screen as the
  simulated decision pipeline.

Artifact hygiene passed. Per-draw simulation diagnostics are local-only and
ignored by Git.

## Key Decisions

- Result status:
  `complete_mv19_high_false_localization_downgrade_c02_c06`.
- H0 C02/C06 both-flag false rate is `0.208`; H0 C02/C06 top-two
  false-localization is `0.034`.
- H1 C02/C06 both-flag recovery is `0.662`, but H1 top-two recovery is only
  `0.222`.
- H1 C01/C04/C05/C07 anchor subset recovery is only `0.178`; exact anchor-set
  recovery is `0.036`.
- Use MV19 as a finite-sample downgrade: C02/C06 remain repeated localized
  dataset-group threshold-shift signals across MV10/MV11/MV13/MV14, but should
  not be written as robust standalone DIF at the observed E-DAIC/CMDC N.
- Full-method gate remains
  `blocked_but_publishable_diagnostic_direction` with
  `full_method_allowed=false`.

## Files Owned Or Touched

- `.gitignore`
- `scripts/phase5_run_mv19_phq_finite_sample_simulation.py`
- `scripts/phase5_plan_mv17_postreview_measurement_validity_route.py`
- `scripts/phase5_full_method_gate_audit.py`
- `scripts/build_diagnostic_paper_claim_tables.py`
- `scripts/build_diagnostic_paper_results_sections.py`
- `scripts/build_diagnostic_paper_manuscript_draft.py`
- `analysis/phase5_minimal_validation/p5_mv19_phq_finite_sample_psychometric_simulation/`
- `analysis/phase5_minimal_validation/p5_mv17_postreview_measurement_validity_route/`
- `analysis/phase5_minimal_validation/full_method_gate_audit/`
- `analysis/diagnostic_measurement_audit_paper/`
- `README.md`
- `docs/master_experiment_plan.md`
- `docs/diagnostic_measurement_audit_paper_outline.md`
- `docs/experiment_issue_log.md`
- `MEMORY.md`
- `memory/ACTIVE_HANDOFF.md`
- `memory/sessions/session_62_mv19_phq_finite_sample_simulation.md`

## Generated Artifacts

Regeneration commands:

```bash
python scripts/phase5_run_mv19_phq_finite_sample_simulation.py
python scripts/phase5_plan_mv17_postreview_measurement_validity_route.py --overwrite
python scripts/phase5_full_method_gate_audit.py
python scripts/build_diagnostic_paper_claim_tables.py
python scripts/build_diagnostic_paper_results_sections.py
python scripts/build_diagnostic_paper_bibliography.py
python scripts/build_diagnostic_paper_manuscript_draft.py
```

Versionable MV19 artifacts:

- `report.md`
- `run_summary.json`
- `artifact_hygiene_audit.json`
- `observed_input_audit.csv`
- `observed_response_category_support.csv`
- `effect_size_contract.csv`
- `simulation_design_contract.csv`
- `input_boundary_contract.csv`
- `simulation_world_summary.csv`
- `item_flag_rate_summary.csv`
- `anchor_recovery_summary.csv`
- `gate_recommendations.csv`

Local-only MV19 artifact:

- `local_mv19_draw_level_decisions.csv`

## Blockers And Risks

- MV19 uses the MV10 approximate screen for finite-sample simulation, not a
  full external `mirt` refit per simulated draw. Interpret it as an observed-N
  sensitivity layer for wording, not as a replacement for MV13/MV14.
- The high H0 any-threshold-flag rate means the current screen is sensitive to
  small-N category noise. The safer paper claim is repeated, localized, and
  finite-sample-bounded C02/C06 threshold-shift evidence.
- Bibliography rows still require full primary-source verification before
  submission.
- The one incomplete local MV06 candidate still bounds stronger RQ4 wording
  unless explicitly left as a sampling limitation.

## Next Handoff

Next main task: consolidate the manuscript around MV19-downgraded PHQ wording
and decide whether optional MV20 criterion-contamination stress is still needed
for protocol-label overlap support. Do not start another shallow BGE head,
projection dimension, MV16 calibration variant, personality gate, or EATD
valence method without a new predeclared mechanism-changing contract.
