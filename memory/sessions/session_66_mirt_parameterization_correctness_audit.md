# Session Memory: session_66_mirt_parameterization_correctness_audit

Status: complete
Last updated: 2026-08-22 UTC
Thread/task: main orchestration - mirt parameterization correctness audit

## Scope

This session owns a code-level statistical correctness audit of the MV13/MV14
R `mirt::multipleGroup` parameterization and the downstream claim-boundary
updates. It is not a new exploratory experiment and does not authorize new
model variants.

It should not touch raw clinical data, row-level item-response matrices,
fitted parameters, factor scores, bootstrap draw rows, model objects, feature
matrices, or prediction rows. Those remain local-only.

## Current State

The audit is complete at
`/root/autodl-tmp/analysis/phase5_minimal_validation/p5_mirt_parameterization_correctness_audit/`.
Status is `complete_mirt_parameterization_mismatch`;
`statistical_correctness_blocker=true`; artifact hygiene passed.

The code-level findings are:

- MV13/MV14 set `group <- factor(..., levels = c("edaic", "cmdc"))`, so
  E-DAIC is the reference group and CMDC is the focal group.
- The manual `CONSTRAINB` anchor syntax matches MV10 roles:
  `C01/C04/C05/C07` constrain loadings and `d1-d3`; `C02/C03/C06` constrain
  loadings only; `C08` is free.
- The scripts use `itemtype = "graded"` and constrain `d1`, `d2`, and `d3`,
  so manuscript wording should call these `mirt` graded d-parameter
  threshold/intercept constraints rather than exported raw cutpoints.
- The actual MV13/MV14 `multipleGroup` calls omit `invariance`. A synthetic
  `pars = "values"` design check confirms CMDC `MEAN_1` and `COV_11` are fixed
  under the actual call, but estimated when anchor items plus
  `free_means/free_var` are supplied.

Current manuscript boundary:

- MV10/MV11/MV19 are the primary PHQ psychometric evidence.
- MV13/MV14 are retained only as fixed-hyperparameter `mirt` qualitative
  screens until corrected/rerun or explicitly limited.
- Do not present MV13/MV14 as final anchor-linked `mirt` DIF evidence or
  identification-robust bootstrap stability.

## Key Decisions

- Treat the finding as a statistical correctness blocker for final manuscript
  wording, not as a reason to open broad new experiments.
- Keep the experiment queue frozen after MV20 except for a narrowly scoped
  correctness rerun of MV13/MV14 if chosen.
- Track only the audit script, lightweight aggregate audit outputs, refreshed
  gate/paper/consolidation artifacts, docs, and memory. Keep item-response
  matrices, fitted parameters, theta scores, bootstrap draw rows, and model
  objects local-only.

## Files Owned Or Touched

- `/root/autodl-tmp/scripts/phase5_audit_mirt_parameterization_contract.py`
- `/root/autodl-tmp/scripts/phase5_full_method_gate_audit.py`
- `/root/autodl-tmp/scripts/phase5_consolidate_experiment_inventory.py`
- `/root/autodl-tmp/scripts/build_diagnostic_paper_claim_tables.py`
- `/root/autodl-tmp/scripts/build_diagnostic_paper_results_sections.py`
- `/root/autodl-tmp/scripts/build_diagnostic_paper_manuscript_draft.py`
- `/root/autodl-tmp/scripts/phase5_plan_mv17_postreview_measurement_validity_route.py`
- `/root/autodl-tmp/docs/experiment_direction.md`
- `/root/autodl-tmp/docs/master_experiment_plan.md`
- `/root/autodl-tmp/docs/diagnostic_measurement_audit_paper_outline.md`
- `/root/autodl-tmp/docs/experiment_issue_log.md`
- `/root/autodl-tmp/README.md`
- `/root/autodl-tmp/MEMORY.md`
- `/root/autodl-tmp/memory/ACTIVE_HANDOFF.md`
- `/root/autodl-tmp/memory/sessions/session_66_mirt_parameterization_correctness_audit.md`

## Generated Artifacts

Primary audit:

```bash
python scripts/phase5_audit_mirt_parameterization_contract.py
```

Outputs:

- `/root/autodl-tmp/analysis/phase5_minimal_validation/p5_mirt_parameterization_correctness_audit/report.md`
- `/root/autodl-tmp/analysis/phase5_minimal_validation/p5_mirt_parameterization_correctness_audit/run_summary.json`
- `/root/autodl-tmp/analysis/phase5_minimal_validation/p5_mirt_parameterization_correctness_audit/parameterization_contract_check.csv`
- `/root/autodl-tmp/analysis/phase5_minimal_validation/p5_mirt_parameterization_correctness_audit/latent_hyperparameter_design_check.csv`
- `/root/autodl-tmp/analysis/phase5_minimal_validation/p5_mirt_parameterization_correctness_audit/anchor_linking_audit.csv`
- `/root/autodl-tmp/analysis/phase5_minimal_validation/p5_mirt_parameterization_correctness_audit/mirt_call_audit.csv`
- `/root/autodl-tmp/analysis/phase5_minimal_validation/p5_mirt_parameterization_correctness_audit/claim_impact_assessment.csv`

Refresh commands:

```bash
python scripts/phase5_full_method_gate_audit.py
python scripts/phase5_consolidate_experiment_inventory.py
python scripts/build_diagnostic_paper_claim_tables.py
python scripts/build_diagnostic_paper_results_sections.py
python scripts/build_diagnostic_paper_bibliography.py
python scripts/build_diagnostic_paper_manuscript_draft.py
python scripts/phase5_plan_mv17_postreview_measurement_validity_route.py --overwrite
```

Current refreshed state:

- Full-method gate remains `blocked_but_publishable_diagnostic_direction`.
- Gate reads 45 Phase 5 summaries.
- Next action rank 1 is
  `NEXT_RESOLVE_MIRT_PARAMETERIZATION_BEFORE_SUBMISSION`.
- Experiment consolidation has 46 rows, 17 active paper rows, 5 paper-core
  rows, 11 paper-support rows, and 1 paper-guardrail row.
- Manuscript open item `M011` is blocking for submission.

## Blockers And Risks

- I072 is open: MV13/MV14 currently fix CMDC latent mean/variance in the
  actual `mirt` calls. This blocks final anchor-linked `mirt` DIF or
  bootstrap-stability wording.
- Corrected rerun may change full, partial, or unsupported invariance
  conclusions because measurement-invariance results are identification
  sensitive.
- Existing MV13/MV14 aggregate outputs remain useful only as
  fixed-hyperparameter qualitative screens.

## Next Handoff

Choose one of two narrow paths before submission:

- Preferred statistical path: patch MV13/MV14 R scripts to use anchor items
  plus `free_means/free_var` in the `invariance` contract, rerun the corrected
  aggregate summaries, then refresh gate, consolidation, paper scaffolds, docs,
  and memory.
- If no rerun is desired: keep the current results and explicitly limit all
  manuscript language to fixed-hyperparameter qualitative `mirt` screens.

Do not broaden the experiment queue or add new feature/model variants from
this audit.
