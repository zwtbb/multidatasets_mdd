# Session Memory: MV28/MV29/MV30 Reviewer-Response Supplements

Status: complete
Last updated: 2026-09-03 UTC
Thread/task: current main-agent reviewer-response continuation

## Scope

This session executed the user-approved reviewer-response supplements for the
ACM-style framework paper: target-label budget uncertainty, PHQ measurement
sensitivity, representation-control sensitivity, related-work gap tightening,
and manuscript claim recalibration. It does not include MV27 in the main paper.

## Current State

- Referenced Codex task `01a031c9-4c78-7510-a50c-578607fc5a7d` and ChatGPT
  conversation `6a97c8da-5be0-83e8-9d15-a945412f9be8` were read before use.
- MV28 completed on CUDA with 8 workers, 30 repeated subject-level
  calibration/evaluation splits, target budgets `k=4,8,12,16,24`, all
  calibrated baselines, and 200 participant-bootstrap draws per split. Hygiene
  passed. Target-only direct MLP is the lowest Macro Item MAE row in all ten
  direction-by-budget cells; source-plus-target calibrated rows beat it in
  `0/50` Macro Item MAE method-budget-direction cells. Source-plus-target rows
  often improve absolute calibration-in-the-large (`46/50` cells), so the
  result is a reconstruction-calibration tradeoff, not a simple source-label
  failure.
- A separate MV28 default-budget extension completed on CUDA with 8 workers,
  30 splits, all calibrated baselines, and 200 participant-bootstrap draws. At
  the MV24 default budgets, target-only direct MLP is also the lowest Macro
  Item MAE row: `0.840` for CMDC-to-E-DAIC at `k=66` and `0.645` for
  E-DAIC-to-CMDC at `k=24`. Measurement-aware is `0.873` and `0.674`,
  respectively. Bootstrap intervals do not support a source-plus-target or
  measurement-aware Macro Item MAE advantage.
- MV29 completed the PHQ measurement-sensitivity grid over loading tolerances
  `0.15,0.20,0.25`, threshold tolerances `0.25,0.35,0.45`, and minimum anchors
  `3,4,5`. Hygiene passed. Stable anchors are `C01,C04,C05,C07`, stable
  threshold-shift signals are `C02,C06`, the default anchor set is exact in
  `1/3` of grid rows and retained in `2/3`, and C02/C06 are retained as
  threshold-shift items in all grid rows.
- MV30 completed the representation-control sensitivity. Hygiene passed.
  Linear E-DAIC/CMDC identity drops near chance after aligned length/acquisition
  controls, severity-only does not explain the drop, shuffled controls restore
  raw identity, and nonlinear random-forest probing still recovers high Qwen3
  text identity (`0.987`) after the same controls.
- Related work was updated with construct-validity benchmark references by
  Alaa et al. 2025, Bean et al. 2025, and Freiesleben and Zezulka 2025.

## Key Decisions

- Main paper positioning is framework/benchmark-validity, not architecture SOTA.
- The original large gain over frozen `Corpus-specific head` must be written as
  a target-calibration/adaptation-regime effect, not as proof that
  corpus-specific ordinal heads drive the improvement.
- Corpus-specific cumulative-logit heads remain a constructive framework
  instance and an audit-to-model sanity check, but they are not an independently
  supported overall performance source in the real E-DAIC/CMDC setting.
- MMD remains auxiliary; the lambda sensitivity is nearly flat and should not
  be presented as a contribution.

## Files Owned Or Touched

- `scripts/phase5_run_mv28_target_label_budget_uncertainty.py`
- `scripts/phase5_run_mv29_phq_measurement_sensitivity.py`
- `scripts/phase5_run_mv30_representation_control_sensitivity.py`
- `scripts/build_diagnostic_paper_bibliography.py`
- `scripts/build_diagnostic_paper_bibliography_verification.py`
- `analysis/diagnostic_measurement_audit_paper/manuscript_reframed_rq_draft.md`
- `analysis/diagnostic_measurement_audit_paper/manuscript_reframed_rq_draft.docx`
- `analysis/diagnostic_measurement_audit_paper/论文撰写_修订版.docx`
- `analysis/diagnostic_measurement_audit_paper/closest_related_work_gap_analysis.md`
- `analysis/diagnostic_measurement_audit_paper/figure_table_integration_guide.md`
- `analysis/diagnostic_measurement_audit_paper/work_report_ppt_outline_script.md`
- Bibliography outputs under `analysis/diagnostic_measurement_audit_paper/`

## Generated Artifacts

- `/root/autodl-tmp/analysis/phase5_minimal_validation/p5_mv28_target_label_budget_uncertainty/`
  - Regenerate with:
    `python scripts/phase5_run_mv28_target_label_budget_uncertainty.py --clean --split-count 30 --target-budgets 4 8 12 16 24 --no-include-mv24-default-budget --participant-bootstrap-draws 200 --direct-epochs 300 --ordinal-epochs 300 --full-epochs 1200 --target-only-epochs 1500 --head-epochs 300 --device cuda --parallel-workers 8`
- `/root/autodl-tmp/analysis/phase5_minimal_validation/p5_mv28_mv24_default_budget_uncertainty/`
  - Regenerate with:
    `python scripts/phase5_run_mv28_target_label_budget_uncertainty.py --clean --out-dir analysis/phase5_minimal_validation/p5_mv28_mv24_default_budget_uncertainty --split-count 30 --target-budgets --participant-bootstrap-draws 200 --direct-epochs 300 --ordinal-epochs 300 --full-epochs 1200 --target-only-epochs 1500 --head-epochs 300 --device cuda --parallel-workers 8`
- `/root/autodl-tmp/analysis/phase5_minimal_validation/p5_mv29_phq_measurement_sensitivity/`
  - Regenerate with:
    `python scripts/phase5_run_mv29_phq_measurement_sensitivity.py --clean`
- `/root/autodl-tmp/analysis/phase5_minimal_validation/p5_mv30_representation_control_sensitivity/`
  - Regenerate with:
    `python scripts/phase5_run_mv30_representation_control_sensitivity.py --clean`
- Word manuscript regenerated with:
  `pandoc --filter pandoc-citeproc --bibliography=analysis/diagnostic_measurement_audit_paper/references.bib analysis/diagnostic_measurement_audit_paper/manuscript_reframed_rq_draft.md -o analysis/diagnostic_measurement_audit_paper/manuscript_reframed_rq_draft.docx`

## Blockers And Risks

- The revised manuscript is claim-consistent with MV28/MV29/MV30, but still
  needs a final ACM formatting and supplement-pass before submission.
- MV28 row-level predictions are intentionally not stored. Published artifacts
  are aggregate-only.
- Feishu sync was not performed in this session.

## Next Handoff

Run final formatting checks, decide whether to add a compact supplementary
MV28 table to the manuscript package, and publish the clean GitHub snapshot
only after `scripts/publish_clean_github_snapshot.py --dry-run` passes.
