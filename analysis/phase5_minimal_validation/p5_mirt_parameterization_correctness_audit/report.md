# mirt Parameterization Correctness Audit

Generated: `2026-08-22T13:22:45+00:00`

## Decision

- Audit status: `complete_mirt_parameterization_consistent`.
- Statistical correctness blocker: `False`.
- Short read: MV13/MV14 mirt parameterization matches the audited anchor-linked measurement-invariance contract: E-DAIC is reference, CMDC is focal, anchor/threshold linking is explicit, and focal mean/variance are freed for threshold-constrained models.

## Key Finding

MV13/MV14 scripts provide mirt invariance terms with free_means/free_var for threshold-constrained models; synthetic mirt design check confirms CMDC MEAN_1 and COV_11 are estimated under anchor items plus free focal hyperparameters.

Corrected mirt outputs can support anchor-linked qualitative external DIF evidence, subject to convergence and finite-sample caveats.

## Checks

| check | status | effect |
| --- | --- | --- |
| reference_focal_group_order | pass | Reference/focal naming in reports is code-consistent. |
| focal_latent_mean_variance | pass | Corrected mirt outputs can support anchor-linked qualitative external DIF evidence, subject to convergence and finite-sample caveats. |
| anchor_linking_partial_mv10 | pass | Manual anchor item linking is internally consistent. |
| graded_threshold_parameterization | pass | Manuscript should call these mirt graded d-parameter threshold/intercept constraints, not exported raw cutpoint values. |

## Regeneration

```bash
python scripts/phase5_audit_mirt_parameterization_contract.py
python scripts/build_diagnostic_paper_claim_tables.py
python scripts/build_diagnostic_paper_results_sections.py
python scripts/build_diagnostic_paper_manuscript_draft.py
```
