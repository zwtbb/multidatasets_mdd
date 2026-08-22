# mirt Parameterization Correctness Audit

Generated: `2026-08-22T11:56:52+00:00`

## Decision

- Audit status: `complete_mirt_parameterization_mismatch`.
- Statistical correctness blocker: `True`.
- Short read: MV13/MV14 correctly set E-DAIC as reference, manually link anchors through CONSTRAINB, and use graded d1-d3 threshold/intercept constraints; however, the actual multipleGroup calls do not free CMDC latent mean/variance, so current mirt results must be treated as fixed-hyperparameter qualitative screens until corrected or explicitly limited.

## Key Finding

MV13/MV14 multipleGroup calls omit the invariance argument; mirt design check shows CMDC MEAN_1 and COV_11 fixed under the actual call.

Current mirt outputs are fixed-group-hyperparameter qualitative screens, not final anchor-linked DIF evidence separated from latent distribution shifts.

## Checks

| check | status | effect |
| --- | --- | --- |
| reference_focal_group_order | pass | Reference/focal naming in reports is code-consistent. |
| focal_latent_mean_variance | fail | Current mirt outputs are fixed-group-hyperparameter qualitative screens, not final anchor-linked DIF evidence separated from latent distribution shifts. |
| anchor_linking_partial_mv10 | pass | Manual anchor item linking is internally consistent, apart from the missing focal hyperparameter release. |
| graded_threshold_parameterization | pass | Manuscript should call these mirt graded d-parameter threshold/intercept constraints, not exported raw cutpoint values. |

## Regeneration

```bash
python scripts/phase5_audit_mirt_parameterization_contract.py
python scripts/build_diagnostic_paper_claim_tables.py
python scripts/build_diagnostic_paper_results_sections.py
python scripts/build_diagnostic_paper_manuscript_draft.py
```
