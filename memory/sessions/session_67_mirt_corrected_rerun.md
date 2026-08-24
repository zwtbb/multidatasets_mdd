# Session Memory: session_67_mirt_corrected_rerun

Status: complete
Last updated: 2026-08-22 UTC
Thread/task: main orchestration - corrected MV13/MV14 mirt rerun

## Scope

This session owns the narrow statistical-correctness rerun requested after
session 66: fix MV13/MV14 anchor-linked focal mean/variance handling, rerun the
existing aggregate artifacts, refresh gates and manuscript scaffolds, and update
memory/docs. It does not open new experiment queues or add new feature/model
variants.

Raw clinical data, local item-response matrices, fitted parameters, factor
scores, bootstrap draw rows, model objects, feature matrices, and row
predictions remain local-only.

## Current State

The corrected rerun is complete. MV13/MV14 threshold-constrained
`mirt::multipleGroup` models now pass anchor item names plus `free_means` and
`free_var` through the `invariance` contract, so E-DAIC remains the reference
group, CMDC remains the focal group, anchors/threshold constraints stay
explicit, and focal mean/variance are freed under anchor linking.

Current audit:

- Source:
  `/root/autodl-tmp/analysis/phase5_minimal_validation/p5_mirt_parameterization_correctness_audit/run_summary.json`
- Status: `complete_mirt_parameterization_consistent`
- `statistical_correctness_blocker=false`
- Short read: MV13/MV14 match the audited anchor-linked measurement-invariance
  contract.

Corrected MV13:

- Source:
  `/root/autodl-tmp/analysis/phase5_minimal_validation/p5_mv13_external_psychometric_replication/run_summary.json`
- Status: `complete_external_mirt_with_convergence_warnings`
- Parameterization contract: `anchor_linked_focal_mean_variance_free`
- Best AIC/BIC: `partial_mv10` / `scalar`
- Confirmed MV10 anchors: 4
- Loading/threshold DIF flags: 0 / 2
- Threshold DIF remains localized to `C02/C06`
- Core configural convergence warning remains.

Corrected MV14:

- Source:
  `/root/autodl-tmp/analysis/phase5_minimal_validation/p5_mv14_measurement_uncertainty_bootstrap/run_summary.json`
- Status: `complete_mv14_convergence_safe_item_level_measurement_shift`
- Parameterization contract: `anchor_linked_focal_mean_variance_free`
- Core effective draws: `120/200`
- Fit-success core draws: `185/200`
- Configural converged draws: `120/200`
- Stable-ladder effective draws: `198`
- DIF minimum anchor-support effective draws: `77/100`
- Stable anchors: `C01/C04/C05/C07`
- Top threshold-DIF items: `C02/C06`

## Key Decisions

- Do not free focal mean/variance for configural or metric-only models without
  threshold anchors; use `free_means/free_var` only when threshold anchors are
  present.
- Current manuscript wording may use MV13/MV14 as corrected external
  anchor-linked mirt corroboration.
- Keep the claim conservative: MV13 retains a configural convergence warning,
  MV14 uses the predeclared `200/100` core/DIF tiers, and MV19 still downgrades
  C02/C06 to repeated but finite-sample-bounded dataset-group threshold-shift
  evidence.
- I072 is closed. The next rank-1 gate action is manuscript finalization after
  correctness gates, not another experiment.

## Files Owned Or Touched

- `/root/autodl-tmp/scripts/phase5_run_mv13_external_psychometric_replication.R`
- `/root/autodl-tmp/scripts/phase5_run_mv13_external_psychometric_replication.py`
- `/root/autodl-tmp/scripts/phase5_run_mv14_measurement_uncertainty_bootstrap.R`
- `/root/autodl-tmp/scripts/phase5_run_mv14_measurement_uncertainty_bootstrap.py`
- `/root/autodl-tmp/scripts/phase5_audit_mirt_parameterization_contract.py`
- `/root/autodl-tmp/scripts/phase5_full_method_gate_audit.py`
- `/root/autodl-tmp/scripts/phase5_consolidate_experiment_inventory.py`
- `/root/autodl-tmp/scripts/build_diagnostic_paper_claim_tables.py`
- `/root/autodl-tmp/scripts/build_diagnostic_paper_results_sections.py`
- `/root/autodl-tmp/scripts/build_diagnostic_paper_manuscript_draft.py`
- `/root/autodl-tmp/analysis/phase5_minimal_validation/p5_mv13_external_psychometric_replication/`
- `/root/autodl-tmp/analysis/phase5_minimal_validation/p5_mv14_measurement_uncertainty_bootstrap/`
- `/root/autodl-tmp/analysis/phase5_minimal_validation/p5_mirt_parameterization_correctness_audit/`
- `/root/autodl-tmp/analysis/phase5_minimal_validation/full_method_gate_audit/`
- `/root/autodl-tmp/analysis/phase5_minimal_validation/experiment_consolidation/`
- `/root/autodl-tmp/analysis/diagnostic_measurement_audit_paper/`
- `/root/autodl-tmp/docs/experiment_issue_log.md`
- `/root/autodl-tmp/docs/experiment_direction.md`
- `/root/autodl-tmp/docs/master_experiment_plan.md`
- `/root/autodl-tmp/docs/diagnostic_measurement_audit_paper_outline.md`
- `/root/autodl-tmp/README.md`
- `/root/autodl-tmp/MEMORY.md`
- `/root/autodl-tmp/memory/ACTIVE_HANDOFF.md`

## Generated Artifacts

Main rerun and refresh commands:

```bash
python scripts/phase5_run_mv13_external_psychometric_replication.py
python scripts/phase5_run_mv14_measurement_uncertainty_bootstrap.py
python scripts/phase5_audit_mirt_parameterization_contract.py
python scripts/phase5_full_method_gate_audit.py
python scripts/phase5_consolidate_experiment_inventory.py
python scripts/build_diagnostic_paper_claim_tables.py
python scripts/build_diagnostic_paper_results_sections.py
python scripts/build_diagnostic_paper_bibliography.py
python scripts/build_diagnostic_paper_manuscript_draft.py
```

Verification commands run:

```bash
python -m py_compile scripts/phase5_run_mv13_external_psychometric_replication.py scripts/phase5_run_mv14_measurement_uncertainty_bootstrap.py scripts/phase5_audit_mirt_parameterization_contract.py scripts/phase5_full_method_gate_audit.py scripts/phase5_consolidate_experiment_inventory.py scripts/build_diagnostic_paper_claim_tables.py scripts/build_diagnostic_paper_results_sections.py scripts/build_diagnostic_paper_manuscript_draft.py
OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 Rscript -e "invisible(parse(file='scripts/phase5_run_mv13_external_psychometric_replication.R')); invisible(parse(file='scripts/phase5_run_mv14_measurement_uncertainty_bootstrap.R')); cat('R parse OK\n')"
```

## Blockers And Risks

- Full M0/M1/M2/M3 method construction remains blocked by the full-method gate.
- MV13/MV14 parameterization is no longer a blocker, but MV13 keeps a
  configural convergence warning.
- MV19 remains binding for C02/C06 wording: repeated localized
  dataset-group threshold-shift evidence, not robust standalone DIF.
- Optional larger MV14 bootstrap is only a precision sensitivity if
  reviewer-facing interval precision becomes critical.
- MV06 still has one incomplete CMDC candidate for stronger RQ4 wording.

## Next Handoff

Continue manuscript finalization and primary-source citation verification.
Use the three-layer frame:

1. representation/protocol shift in `X`;
2. target measurement shift in `Y` given latent severity and dataset/group;
3. prediction consequences for `X -> theta`.

The new writing task created from this session should draft Introduction,
Related Work, Problem Definition, Dataset/Protocol, and Methods framework from
the frozen evidence layer. It should not run experiments or alter MV13/MV14.
