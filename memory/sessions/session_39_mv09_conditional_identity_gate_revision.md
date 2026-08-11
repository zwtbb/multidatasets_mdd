# Session Memory: P5 MV09 Conditional Identity Gate Revision

Status: complete
Last updated: 2026-08-11 UTC
Thread/task: main agent MV09 conditional identity and paper-pivot update

## Scope

This session converts the post-MV08b review into an aggregate-only Phase 5
conditional dataset-identity audit and updates the claim boundary. It does not
train a deployable model, read raw text/media, export row-level predictions,
write learned features, or authorize full M0/M1/M2/M3 method construction.

## Current State

- Added and ran
  `scripts/phase5_run_mv09_conditional_identity_audit.py`.
- Generated aggregate outputs at
  `analysis/phase5_minimal_validation/p5_mv09_conditional_identity_audit/`.
- Updated `scripts/phase5_full_method_gate_audit.py` so the gate reads 27
  Phase 5 summaries including `P5_MV09`.
- Current full-method gate remains
  `blocked_but_publishable_diagnostic_direction` with
  `full_method_allowed=false`.
- MV09 artifact hygiene passed with zero violations.

## Key Results

- E-DAIC/CMDC raw BGE identity BA: `1.000`.
- E-DAIC/CMDC PHQ C01-C08 item-residualized BGE identity BA: `0.991`.
- E-DAIC/CMDC severity-residualized BGE identity BA: `1.000`.
- CMDC/PDCH normalized-severity residualized BGE identity BA: `1.000`.
- E-DAIC/CMDC/PDCH three-way normalized-severity residualized identity BA:
  `1.000`.
- Control-only severity identity is lower (`0.542` for E-DAIC/CMDC and
  `0.613` for CMDC/PDCH), so the high conditional identity is not explained by
  target severity alone.

## Key Decisions

- Unconditional dataset identity is a shortcut-risk screen, not a standalone
  hard-failure criterion.
- Future shared-latent claims must report dataset identity after conditioning
  on target severity, aligned item labels where available, and legitimate
  covariates.
- Post-head prediction identity should be treated as diagnostic when outputs
  are scale-specific; reserve hard identity gates for explicitly shared latent
  or prediction spaces.
- MV08b should not be rescued as positive RQ1 evidence because it has only tiny
  gains and lacks an independent psychometric latent target.
- The paper direction is now measurement shift / measurement invariance, not a
  generic diagnostic audit.
- The next active experiment should be a classical PHQ-8/PHQ-9 psychometric
  invariance baseline before any MV08c-like multimodal head iteration.

## Files Owned Or Touched

- `scripts/phase5_run_mv09_conditional_identity_audit.py`
- `scripts/phase5_full_method_gate_audit.py`
- `scripts/build_diagnostic_paper_claim_tables.py`
- `analysis/phase5_minimal_validation/p5_mv09_conditional_identity_audit/`
- `analysis/phase5_minimal_validation/full_method_gate_audit/`
- `analysis/phase5_minimal_validation/experiment_matrix.csv`
- `analysis/diagnostic_measurement_audit_paper/`
- `README.md`
- `docs/diagnostic_measurement_audit_paper_outline.md`
- `docs/experiment_issue_log.md`
- `MEMORY.md`
- `memory/sessions/session_master_orchestration.md`
- `memory/sessions/session_39_mv09_conditional_identity_gate_revision.md`

## Generated Artifacts

Regeneration commands:

```bash
python scripts/phase5_run_mv09_conditional_identity_audit.py
python scripts/phase5_full_method_gate_audit.py
python scripts/build_diagnostic_paper_claim_tables.py
```

Versionable MV09 outputs:

- `conditional_identity_by_seed.csv`
- `conditional_identity_summary.csv`
- `conditional_identity_within_severity_bin.csv`
- `condition_balance_summary.csv`
- `gate_revision_recommendations.csv`
- `accuracy_invariance_pareto_summary.csv`
- `source_context_conditional_identity.csv`
- `report.md`
- `run_summary.json`
- `artifact_hygiene_audit.json`

## Sources Checked

- Ishikawa and Duke 2026 multi-probe depression benchmark audit:
  `https://arxiv.org/abs/2605.23977`
- Zhou et al. 2026 depression scale linking:
  `https://www.jclinepi.com/article/S0895-4356(26)00082-X/abstract`
- Galenkamp et al. 2017 PHQ-9 measurement invariance:
  `https://pmc.ncbi.nlm.nih.gov/articles/PMC5655879/`
- Nguyen et al. 2022 questionnaire-grounded depression detection:
  `https://aclanthology.org/2022.acl-long.578/`
- Zhang and Poellabauer 2025 interviewer-bias diagnostic:
  `https://aclanthology.org/2025.findings-emnlp.650/`
- Ma et al. 2021 PHQ/HAMD IRT comparison:
  `https://www.frontiersin.org/journals/psychiatry/articles/10.3389/fpsyt.2021.747139/full`

## Next Handoff

Implement `P5_MV10 classical_psychometric_invariance_baseline` as a label-only
baseline over E-DAIC PHQ-8 and CMDC PHQ-9 item labels, with PDCH HAMD as a
separate clinical stress track if useful. Track scripts and aggregate fit/DIF
summaries only; keep subject-level factor scores, fitted parameters, row
diagnostics, and bootstraps local-only unless separately approved.
