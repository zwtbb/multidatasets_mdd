# Session Memory: MV14 Correction And MV15 Latent-Conditioned Identity Design

Status: complete
Last updated: 2026-08-13 UTC
Thread/task: main agent continuation

## Scope

This session owns the user-requested MV14 convergence-safe correction, the
MV12 interpretation downgrade, the MV15 latent-conditioned identity
predeclaration update, and the refreshed full-method gate / manuscript
scaffolds.

It does not run an MV15 identity probe, train a full method, export theta
scores, export residualized features, export row-level predictions, export
fitted psychometric parameters, or rewrite GitHub history directly.

## Current State

- MV14 bootstrap inference was corrected so AIC/BIC model selection and LRT
  decisions require `fit_success && converged`.
- Corrected MV14 run summary:
  `/root/autodl-tmp/analysis/phase5_minimal_validation/p5_mv14_measurement_uncertainty_bootstrap/run_summary.json`.
- MV14 convergence-safe full-ladder effective R is `120/200`; `185/200` is the
  fit-success count, not the effective model-selection count.
- MV14 configural convergence is `120/200`; stable metric/partial/scalar
  ladder effective R is `197`; DIF effective R is `100`.
- Stable anchors remain `C01/C04/C05/C07`; loading DIF remains sparse; top
  threshold-DIF items remain `C02/C06`.
- MV14 manuscript interpretation is downgraded to item-level measurement-shift
  evidence with global invariance-model selection uncertainty.
- MV12 aggregate tradeoff analysis now records the dimension-matched B3 caveat:
  M12a is lower-identity than upstream BGE features, but B3 direct itemwise
  Ridge compressed to theta has lower pooled observed macro MAE and lower
  conditional identity than M12a.
- MV12 external theta failure is now described as zero-shot source-calibrated
  latent transfer failure, because source measurement scoring on target
  subjects mixes predictor transfer error with measurement-function mismatch.
- MV15 design is complete at
  `/root/autodl-tmp/analysis/phase5_minimal_validation/p5_mv15_latent_conditioned_identity_design/`.
- MV15 design has 10 conditioning ladder rows, 7 identity-probe rows, and 8
  pass/fail gates, including raw, total, predicted-total, observed-item, B3
  itemwise-theta, psychometric-theta, covariate, predicted-output, and
  severity-only controls.
- Full-method gate remains
  `blocked_but_publishable_diagnostic_direction`,
  `full_method_allowed=false`, and now reads 37 Phase 5 summaries.

## Key Decisions

- Do not summarize MV14 as bootstrap-confirmed global partial invariance.
- Use MV10/MV11/MV13/MV14 as label-only common-structure, stable-anchor,
  sparse-loading-DIF, localized-threshold-DIF, and convergence/model-selection
  uncertainty evidence.
- Do not use MV12's `0.991 -> 0.602` identity reduction alone as evidence that
  psychometric theta is uniquely invariant.
- The next active experiment is the MV15 runner. It must answer whether
  `I(Z;D|theta)` is lower than `I(Z;D|total)`, `I(Z;D|predicted_total)`, and
  `I(Z;D|B3_itemwise_theta)` under subject-level folds.
- MV16 should be predeclared as DIF-guided few-shot measurement calibration,
  comparing zero-shot source measurement, global affine theta calibration,
  `C02/C06` threshold calibration, all-threshold calibration, and direct
  target-domain adaptation at k=`0/5/10/20/40`.

## Files Owned Or Touched

- `scripts/phase5_run_mv14_measurement_uncertainty_bootstrap.R`
- `scripts/phase5_run_mv14_measurement_uncertainty_bootstrap.py`
- `scripts/phase5_analyze_mv12_latent_target_tradeoffs.py`
- `scripts/phase5_plan_mv15_latent_conditioned_identity.py`
- `scripts/phase5_full_method_gate_audit.py`
- `scripts/build_diagnostic_paper_claim_tables.py`
- `scripts/build_diagnostic_paper_results_sections.py`
- `analysis/phase5_minimal_validation/p5_mv14_measurement_uncertainty_bootstrap/`
- `analysis/phase5_minimal_validation/p5_mv12_latent_target_tradeoff_analysis/`
- `analysis/phase5_minimal_validation/p5_mv15_latent_conditioned_identity_design/`
- `analysis/phase5_minimal_validation/full_method_gate_audit/`
- `analysis/diagnostic_measurement_audit_paper/`
- `README.md`
- `docs/master_experiment_plan.md`
- `docs/experiment_issue_log.md`
- `docs/diagnostic_measurement_audit_paper_outline.md`
- `MEMORY.md`
- `memory/sessions/session_master_orchestration.md`
- `memory/sessions/session_49_mv14_measurement_uncertainty_bootstrap_run.md`
- `memory/sessions/session_50_mv15_latent_conditioned_identity_design.md`

## Generated Artifacts

Regenerate the corrected artifacts with:

```bash
python scripts/phase5_run_mv14_measurement_uncertainty_bootstrap.py
python scripts/phase5_analyze_mv12_latent_target_tradeoffs.py
python scripts/phase5_plan_mv15_latent_conditioned_identity.py --overwrite
python scripts/phase5_full_method_gate_audit.py
python scripts/build_diagnostic_paper_claim_tables.py
python scripts/build_diagnostic_paper_results_sections.py
```

Tracked aggregate outputs include corrected MV14 model-selection/LRT summaries,
`stable_ladder_model_selection_frequency.csv`, MV12 failure-mode summaries,
MV15 design contracts, refreshed full-method gate outputs, and refreshed
diagnostic paper claim/results scaffolds.

## Blockers And Risks

- Full method remains blocked.
- MV15 is not yet run; it is only a design contract.
- MV14 remains limited by CMDC N=77 and configural convergence sensitivity.
- Larger corrected MV14 bootstrap tiers can be run later for interval precision,
  but should not displace the immediate MV15/MV16 route unless needed.
- MV06 still has one incomplete local candidate and lacks agreement uncertainty
  intervals for stronger RQ4 wording.

## Next Handoff

Implement and run `scripts/phase5_run_mv15_latent_conditioned_identity.py`
under the design contract. Track only aggregate identity summaries, reports,
gates, docs, and memory. Keep theta scores, row predictions, residualized
features, nuisance directions, split maps, fitted measurement parameters, and
model artifacts local-only.
