# Session Memory: Phase 5 MV11 Formal Psychometric Confirmation

Status: active
Last updated: 2026-08-11 UTC
Thread/task: main agent continuation

## Scope

This session owns the P5_MV11 label-only formal psychometric confirmation
following MV10. It fits an in-repository multi-group graded-response IRT
confirmation over E-DAIC PHQ-8 and CMDC PHQ-9 shared C01-C08 item labels, then
updates the full-method gate, paper scaffolds, experiment matrix, issue log,
and memory. It should not start a multimodal method run or export subject-level
factor scores, posterior scores, fitted item parameters, or row diagnostics.

## Current State

- MV11 is complete at
  `/root/autodl-tmp/analysis/phase5_minimal_validation/p5_mv11_formal_psychometric_confirmation/`.
- The script uses the same manifest-governed PHQ item labels as MV10: E-DAIC
  PHQ-8 train/dev item-labeled subjects and CMDC PHQ-9 valid item-labeled
  subjects.
- It reads no raw text/media, multimodal features, private review material, or
  row-level predictions.
- It fits 20 aggregate multi-group graded-response IRT models with marginal
  maximum likelihood and Gauss-Hermite quadrature: configural, metric, scalar,
  MV10 partial-anchor, eight loading-free item diagnostics, and eight
  threshold-free item diagnostics.
- Artifact hygiene passed. No fitted item parameters or subject scores are
  written.

## Key Decisions

- Treat MV11 as `complete_formal_partial_invariance_supported_with_bic_caveat`.
- All four MV10 anchors are confirmed: `C01`, `C04`, `C05`, and `C07`.
- No loading-DIF items are strongly flagged.
- Threshold DIF is strongly flagged for `C02` anhedonia and `C06` self-worth.
- Core model selection has an AIC/BIC split: AIC prefers the MV10 partial model,
  while BIC prefers scalar. This supports a cautious partial-invariance target
  design, not a full scalar-invariance claim.
- Full method remains blocked. The next RQ1 step is `P5_MV12` two-stage
  latent-target design: fit `Y -> theta` targets locally, train audited
  `X -> theta` predictors, and compare with direct/floor baselines plus
  conditional identity and external transfer checks.

## Files Owned Or Touched

- `scripts/phase5_run_mv11_formal_psychometric_confirmation.py`
- `analysis/phase5_minimal_validation/p5_mv11_formal_psychometric_confirmation/`
- `scripts/phase5_full_method_gate_audit.py`
- `scripts/build_diagnostic_paper_claim_tables.py`
- `analysis/phase5_minimal_validation/full_method_gate_audit/`
- `analysis/diagnostic_measurement_audit_paper/`
- `analysis/phase5_minimal_validation/experiment_matrix.csv`
- `README.md`
- `docs/diagnostic_measurement_audit_paper_outline.md`
- `docs/experiment_issue_log.md`
- `MEMORY.md`
- `memory/sessions/session_master_orchestration.md`
- `memory/sessions/session_41_mv11_formal_psychometric_confirmation.md`

## Generated Artifacts

Regenerate MV11 with:

```bash
python scripts/phase5_run_mv11_formal_psychometric_confirmation.py
```

Key aggregate outputs:

- `fit_model_summary.csv`
- `invariance_comparison_summary.csv`
- `item_dif_lrt_summary.csv`
- `anchor_confirmation_summary.csv`
- `gate_recommendations.csv`
- `method_context_formal_irt.csv`
- `report.md`
- `run_summary.json`
- `artifact_hygiene_audit.json`

Regenerate downstream claim and paper tables with:

```bash
python scripts/phase5_full_method_gate_audit.py
python scripts/build_diagnostic_paper_claim_tables.py
```

## Blockers And Risks

- MV11 is a self-contained in-repository graded-response IRT implementation,
  not an external `lavaan` or `mirt` runtime. It is suitable as a reproducible
  confirmation layer, but an external package replication may still be useful
  before final manuscript submission.
- The AIC/BIC split means manuscript wording should say partial invariance is
  supported with a conservative model-selection caveat.
- The next two-stage experiment must not commit subject-level factor scores,
  posterior scores, fitted item parameters, row predictions, transformed
  features, or model artifacts.

## External Source Context

- Samejima graded-response model:
  https://www.psychometricsociety.org/sites/main/files/file-attachments/mn17.pdf
- PHQ-9 measurement invariance:
  https://pmc.ncbi.nlm.nih.gov/articles/PMC5655879/
- PHQ-9 sociodemographic invariance:
  https://pmc.ncbi.nlm.nih.gov/articles/PMC6736700/
- IRT likelihood-ratio DIF testing:
  https://www.frontiersin.org/journals/education/articles/10.3389/feduc.2017.00051/full

## Next Handoff

Implement `P5_MV12` as a design/predeclaration task before any multimodal run.
The design must define target-generation boundaries, local-only score and
parameter storage, direct `X -> Y` and floor baselines, conditional dataset
identity probes, external transfer checks, pass/fail thresholds, and publishable
aggregate outputs.
