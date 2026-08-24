# Session Memory: MV18 CMDC-PDCH HAMD Same-Scale Control

Status: complete
Last updated: 2026-08-21 UTC
Thread/task: Continue post-review measurement-validity route; run MV18

## Scope

This session owns MV18: an exploratory same-language/same-HAMD control between
CMDC and PDCH. It asks whether dataset/context differences remain visible when
the target family is HAMD-17 in both datasets.

It does not claim formal HAMD invariance, does not train a full method, does
not fine-tune encoders, and does not export raw text, media paths, source
locators, feature matrices, learned embeddings, fitted model parameters, or
row-level predictions.

## Current State

MV18 is complete at
`analysis/phase5_minimal_validation/p5_mv18_cmdc_pdch_hamd_same_scale_control/`.

The run used:

- 25 CMDC HAMD subjects;
- 99 PDCH HAMD subjects;
- 25 CMDC and 73 PDCH subjects in the mild/moderate HAMD overlap;
- the MV02 HAMD code-9 policy: code `9` is excluded from item
  training/evaluation and item-derived total scoring;
- existing MV02 Phase 2 frozen subject features: `text_bge`, `audio_wavlm`,
  `audio_egemaps`, and `early_fusion_all`;
- five seeds and subject-level CV for same-dataset scopes;
- bidirectional frozen-feature transfer scopes:
  `pdch_overlap_to_cmdc_overlap` and `cmdc_overlap_to_pdch_overlap`, plus
  all-subject sensitivity scopes.

Artifact hygiene passed. Subject-overlap violations are zero. Row-level
predictions are local-only and ignored by Git.

The Phase 5 full-method gate was refreshed after MV18. It remains
`blocked_but_publishable_diagnostic_direction` with `full_method_allowed=false`;
the next action queue now points to MV19 finite-sample PHQ psychometric
simulation.

## Key Decisions

- Result status:
  `complete_exploratory_same_scale_context_shift_supported`.
- In the mild/moderate HAMD overlap, MV18 flags 4 predeclared
  severity-conditioned residual item shifts:
  `HAMD08`, `HAMD11`, `HAMD04`, and `HAMD09`.
- It flags 7 threshold-shift rows in the same overlap.
- Primary bidirectional transfer is weak under the current frozen-feature
  contract:
  - `pdch_overlap_to_cmdc_overlap` best item-derived total is `text_bge`
    itemwise Ridge, MAE `3.629`, delta vs source train-mean items `+0.029`;
  - `cmdc_overlap_to_pdch_overlap` best item-derived total is
    `early_fusion_all` itemwise Ridge, MAE `4.292`, delta vs source train-mean
    items `+0.220`, and delta vs target same-feature CV `+0.341`.
- Interpret MV18 as exploratory same-HAMD context-shift support. Do not use it
  as formal HAMD invariance or broad HAMD transfer evidence because CMDC HAMD
  supervision is only 25 subjects.

## Files Owned Or Touched

- `scripts/phase5_run_mv18_cmdc_pdch_hamd_same_scale_control.py`
- `scripts/phase5_plan_mv17_postreview_measurement_validity_route.py`
- `scripts/phase5_full_method_gate_audit.py`
- `scripts/build_diagnostic_paper_claim_tables.py`
- `scripts/build_diagnostic_paper_bibliography.py`
- `scripts/build_diagnostic_paper_manuscript_draft.py`
- `analysis/phase5_minimal_validation/p5_mv18_cmdc_pdch_hamd_same_scale_control/`
- `analysis/phase5_minimal_validation/p5_mv17_postreview_measurement_validity_route/`
- `analysis/phase5_minimal_validation/full_method_gate_audit/`
- `analysis/diagnostic_measurement_audit_paper/`
- `MEMORY.md`
- `memory/ACTIVE_HANDOFF.md`
- `docs/experiment_issue_log.md`
- `docs/master_experiment_plan.md`
- `docs/diagnostic_measurement_audit_paper_outline.md`
- `README.md`
- `memory/sessions/session_61_mv18_cmdc_pdch_hamd_same_scale_control.md`

## Generated Artifacts

Regeneration commands:

```bash
python scripts/phase5_run_mv18_cmdc_pdch_hamd_same_scale_control.py
python scripts/phase5_plan_mv17_postreview_measurement_validity_route.py --overwrite
python scripts/phase5_full_method_gate_audit.py
python scripts/build_diagnostic_paper_claim_tables.py
python scripts/build_diagnostic_paper_bibliography.py
python scripts/build_diagnostic_paper_manuscript_draft.py
```

Versionable MV18 artifacts:

- `report.md`
- `run_summary.json`
- `artifact_hygiene_audit.json`
- `label_scope_audit.csv`
- `item_distribution_summary.csv`
- `item_shift_summary.csv`
- `threshold_shift_summary.csv`
- `label_feature_audit.csv`
- `metrics_by_seed.csv`
- `metric_summary.csv`
- `macro_summary.csv`
- `transfer_comparison_summary.csv`
- `model_split_audit.csv`
- `construct_proxy_map.csv`

Local-only MV18 artifact:

- `p5_mv18_local_predictions.csv`

## Blockers And Risks

- CMDC HAMD supervision remains small: 25 subjects. MV18 cannot prove formal
  HAMD measurement invariance or authorize HAMD cross-dataset method claims.
- Same-scale control reduces language/scale confounding but does not remove
  protocol, clinical setting, population, and severity-composition differences.
- Model metric bootstrap is intentionally disabled for transfer metrics; label
  item/threshold shifts retain 500 stratified bootstrap resamples.

## Next Handoff

Next research step: predeclare and run MV19 finite-sample PHQ psychometric
simulation if manuscript support still needs an observed-N uncertainty layer.
Keep MV20 criterion-contamination stress optional unless manuscript review
requires it.
