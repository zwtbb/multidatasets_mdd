# Session Memory: session_66_mirt_parameterization_correctness_audit

Status: complete
Last updated: 2026-08-22 UTC
Thread/task: main orchestration - mirt parameterization correctness audit

Superseded by
`/root/autodl-tmp/memory/sessions/session_67_mirt_corrected_rerun.md`: the
parameterization issue identified here has now been corrected and rerun.

## Scope

This session owns a code-level statistical correctness audit of the MV13/MV14
R `mirt::multipleGroup` parameterization and the downstream claim-boundary
updates. It is not a new exploratory experiment and does not authorize new
model variants.

It should not touch raw clinical data, row-level item-response matrices,
fitted parameters, factor scores, bootstrap draw rows, model objects, feature
matrices, or prediction rows. Those remain local-only.

## Current State

This session identified the original blocker. The audit snapshot from that
point was complete at
`/root/autodl-tmp/analysis/phase5_minimal_validation/p5_mirt_parameterization_correctness_audit/`.
It was later superseded by a corrected rerun with status
`complete_mirt_parameterization_consistent`; artifact hygiene passed in both
snapshots.

The code-level findings are:

- MV13/MV14 set `group <- factor(..., levels = c("edaic", "cmdc"))`, so
  E-DAIC is the reference group and CMDC is the focal group.
- The manual `CONSTRAINB` anchor syntax matches MV10 roles:
  `C01/C04/C05/C07` constrain loadings and `d1-d3`; `C02/C03/C06` constrain
  loadings only; `C08` is free.
- The scripts use `itemtype = "graded"` and constrain `d1`, `d2`, and `d3`,
  so manuscript wording should call these `mirt` graded d-parameter
  threshold/intercept constraints rather than exported raw cutpoints.
- The original MV13/MV14 `multipleGroup` calls omitted `invariance`. A
  synthetic `pars = "values"` design check confirmed CMDC `MEAN_1` and
  `COV_11` were fixed under that original call, but estimated when anchor
  items plus `free_means/free_var` were supplied.

Current manuscript boundary:

- MV10/MV11/MV19 are the primary PHQ psychometric evidence.
- Session 67 corrected/reran MV13/MV14. Current manuscript wording should use
  the corrected anchor-linked external `mirt` corroboration with configural
  convergence and MV19 finite-sample caveats.
- Do not present MV13/MV14 as robust standalone `mirt` DIF evidence or
  identification-robust bootstrap stability without the caveats.

## Key Decisions

- The original finding was treated as a statistical correctness blocker for
  final manuscript wording, not as a reason to open broad new experiments.
- The narrow correctness rerun was completed in session 67. Keep the experiment
  queue frozen after MV20.
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

Historical refreshed state before session 67:

- Full-method gate remains `blocked_but_publishable_diagnostic_direction`.
- Gate reads 45 Phase 5 summaries.
- Next action rank 1 was the MV13/MV14 parameterization fix.
- Experiment consolidation has 46 rows, 17 active paper rows, 5 paper-core
  rows, 11 paper-support rows, and 1 paper-guardrail row.
- A manuscript open item was blocking for submission before session 67.

## Blockers And Risks

- I072 was opened here and closed by session 67 after the corrected rerun.
- Corrected rerun may change full, partial, or unsupported invariance
  conclusions because measurement-invariance results are identification
  sensitive.
- Current MV13/MV14 aggregate outputs are corrected, but still bounded by
  convergence and finite-sample caveats.

## Next Handoff

The path chosen after this audit was the preferred statistical path: patch and
rerun MV13/MV14 with anchor items plus `free_means/free_var`, then refresh the
aggregate summaries, gate, consolidation, paper scaffolds, docs, and memory.

Do not broaden the experiment queue or add new feature/model variants from
this audit.
