# Session Memory: MV15 Latent-Conditioned Identity Run

Status: complete
Last updated: 2026-08-13 UTC
Thread/task: main agent continuation

## Scope

This session owns the implementation and execution of the predeclared MV15
latent-conditioned dataset identity runner, the refreshed full-method gate, the
paper-facing aggregate scaffold refresh, and the related memory/docs updates.

It does not start the full M0/M1/M2/M3 method, export participant-grain theta
scores, export row predictions, export residualized feature matrices, export
nuisance directions, export split maps, export fitted measurement parameters,
or claim PHQ-HAMD latent scale linking.

## Current State

- MV15 runner is implemented at
  `/root/autodl-tmp/scripts/phase5_run_mv15_latent_conditioned_identity.py`.
- MV15 aggregate outputs are at
  `/root/autodl-tmp/analysis/phase5_minimal_validation/p5_mv15_latent_conditioned_identity/`.
- MV15 status is `blocked_theta_conditioned_feature_identity_high`.
- Artifact hygiene passed and subject-overlap violations are zero.
- Primary E-DAIC/CMDC raw BGE feature identity BA is `1.000`.
- Theta-conditioned BGE feature identity BA remains `1.000`.
- Total-, predicted-total-, and B3 itemwise-theta-conditioned BGE feature
  identity BA are all `1.000`.
- PHQ C01-C08 item-conditioned feature identity BA is `0.974`.
- Theta-only identity BA is `0.576`.
- Predicted-theta output identity BA is `0.646`.
- B3 direct itemwise-theta output identity BA is `0.571`, and B3 still
  Pareto-dominates predicted theta on output identity plus observed macro MAE.
- CMDC/PDCH and three-way severity-only sensitivity rows complete; residualized
  BGE feature identity remains `1.000` in both sensitivity scopes.
- The full-method gate now reads `38` Phase 5 summaries and remains
  `blocked_but_publishable_diagnostic_direction`.
- Ranked next action is now `NEXT_PREDECLARE_MV16_DIF_GUIDED_CALIBRATION`.

## Key Decisions

- Treat MV15 as negative feature-invariance evidence under the current aligned
  BGE contract.
- Do not interpret low one-dimensional theta or predicted-theta output identity
  as upstream BGE feature invariance.
- Freeze the current latent-conditioned BGE feature-identity line as
  diagnostic/negative evidence.
- MV16 should be predeclared as a DIF-guided few-shot measurement-calibration
  test, comparing zero-shot source measurement, global affine or monotonic
  calibration, C02/C06 threshold calibration, all-threshold calibration, and
  direct target adaptation at k=`0/5/10/20/40`.
- Full-method construction remains blocked.

## Files Owned Or Touched

- `scripts/phase5_run_mv15_latent_conditioned_identity.py`
- `scripts/phase5_full_method_gate_audit.py`
- `scripts/build_diagnostic_paper_claim_tables.py`
- `scripts/build_diagnostic_paper_results_sections.py`
- `analysis/phase5_minimal_validation/p5_mv15_latent_conditioned_identity/`
- `analysis/phase5_minimal_validation/full_method_gate_audit/`
- `analysis/diagnostic_measurement_audit_paper/`
- `README.md`
- `docs/master_experiment_plan.md`
- `docs/experiment_issue_log.md`
- `docs/diagnostic_measurement_audit_paper_outline.md`
- `MEMORY.md`
- `memory/sessions/session_master_orchestration.md`
- `memory/sessions/session_51_mv15_latent_conditioned_identity_run.md`

## Generated Artifacts

Regenerate this session's aggregate artifacts with:

```bash
python scripts/phase5_run_mv15_latent_conditioned_identity.py
python scripts/phase5_full_method_gate_audit.py
python scripts/build_diagnostic_paper_claim_tables.py
python scripts/build_diagnostic_paper_results_sections.py
```

Tracked aggregate MV15 outputs include conditioning/output/external identity
summaries, aggregate output fidelity summaries, split-overlap audit, input and
covariate coverage summaries, pass/fail gate results, report, run summary, and
artifact-hygiene audit.

## Blockers And Risks

- Full method remains blocked.
- Current BGE feature identity remains perfectly recoverable after theta and
  severity conditioning.
- MV15 uses the MV12 local partial PHQ measurement scorer for fold-local theta
  targets; this is consistent with MV12 but remains diagnostic rather than a
  final psychometric model.
- E-DAIC age coverage is absent in the manifest, so MV15 covariate sensitivity
  uses theta plus gender where coverage permits; this limitation is exported in
  aggregate coverage summaries.
- MV06 still has one incomplete local candidate and lacks agreement uncertainty
  intervals for stronger RQ4 wording.

## Next Handoff

Predeclare `P5_MV16` DIF-guided few-shot measurement calibration. Keep all
calibration parameters, theta tables, subject rows, split maps, fitted
artifacts, and row predictions local-only. Track only the design contract,
aggregate future curves/summaries, refreshed gates, docs, and memory.
