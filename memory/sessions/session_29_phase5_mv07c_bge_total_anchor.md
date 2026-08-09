# Session Memory: Phase 5 MV07c BGE Total Anchor

Status: complete
Last updated: 2026-08-09 UTC
Thread/task: main agent MV07c total-anchor follow-up

## Scope

This session owns the MV07c follow-up to MV07b's remaining total-allocation
floor gap. It tests whether identity-projected BGE itemwise PHQ C01-C08 heads
can add construct value after a train-fold-selected total anchor.

It does not scan clinical source content, fine-tune encoders, write transformed
features, save projection directions, save model weights, or start the full
symptom-aligned method.

## Current State

- Implemented `scripts/phase5_run_mv07c_bge_total_anchor.py`.
- Generated
  `analysis/phase5_minimal_validation/p5_mv07c_bge_total_anchor/`.
- Inputs were manifest-governed E-DAIC/CMDC PHQ C01-C08 labels plus frozen BGE
  subject features for E-DAIC, CMDC, and PDCH identity probing.
- Feature contract: 512 shared `bge_*` model-input columns.
- For each outer seed, projection depth `k` and the total-anchor blend weight
  were selected by inner CV on the outer training fold only.
- Subject-overlap violations: `0`.
- Artifact hygiene passed with zero violations.
- Row-level predictions are ignored local-only in
  `p5_mv07c_local_predictions.csv`.
- Full-method gate was rerun and now reads 20 Phase 5 run summaries.

## Key Decisions

- MV07c is complete and blocked:
  `blocked_not_better_than_raw_total_allocation_bge_total_anchor`.
- The total-anchor row reduces prediction identity further than MV07b:
  prediction identity BA is `0.664`.
- Feature identity is reduced but residual identity remains:
  - E-DAIC/CMDC feature identity BA `1.000 -> 0.738`.
  - E-DAIC/CMDC/PDCH feature identity BA `1.000 -> 0.702`.
- The selected total-anchor model beats train mean on E-DAIC and CMDC, and
  improves E-DAIC over raw total allocation by `-0.018` Macro MAE.
- The blocker remains CMDC raw total allocation:
  - CMDC delta vs raw total allocation: `+0.012`.
  - CMDC delta vs projected total allocation: `+0.002`.
- Do not continue iterating small shallow BGE-head variants. MV07b and MV07c
  together show that BGE identity can be reduced, but current shallow
  itemwise/total-anchor contracts do not add enough shared-construct value over
  simple total-allocation floors.

## Files Owned Or Touched

- `scripts/phase5_run_mv07c_bge_total_anchor.py`
- `scripts/phase5_full_method_gate_audit.py`
- `analysis/phase5_minimal_validation/p5_mv07c_bge_total_anchor/`
- `analysis/phase5_minimal_validation/full_method_gate_audit/`
- `MEMORY.md`
- `docs/master_experiment_plan.md`
- `docs/experiment_issue_log.md`
- `memory/sessions/session_22_phase5_full_method_gate_audit.md`
- `memory/sessions/session_29_phase5_mv07c_bge_total_anchor.md`

## Generated Artifacts

Regeneration commands:

```bash
python scripts/phase5_run_mv07c_bge_total_anchor.py
python scripts/phase5_full_method_gate_audit.py
```

Versionable MV07c artifacts:

- `analysis/phase5_minimal_validation/p5_mv07c_bge_total_anchor/report.md`
- `analysis/phase5_minimal_validation/p5_mv07c_bge_total_anchor/run_summary.json`
- `analysis/phase5_minimal_validation/p5_mv07c_bge_total_anchor/artifact_hygiene_audit.json`
- `analysis/phase5_minimal_validation/p5_mv07c_bge_total_anchor/metric_summary.csv`
- `analysis/phase5_minimal_validation/p5_mv07c_bge_total_anchor/metrics_by_seed.csv`
- `analysis/phase5_minimal_validation/p5_mv07c_bge_total_anchor/comparison_summary.csv`
- `analysis/phase5_minimal_validation/p5_mv07c_bge_total_anchor/identity_probe_by_seed.csv`
- `analysis/phase5_minimal_validation/p5_mv07c_bge_total_anchor/identity_probe_summary.csv`
- `analysis/phase5_minimal_validation/p5_mv07c_bge_total_anchor/model_split_audit.csv`
- `analysis/phase5_minimal_validation/p5_mv07c_bge_total_anchor/projection_selection_audit.csv`
- `analysis/phase5_minimal_validation/p5_mv07c_bge_total_anchor/inner_cv_selection_summary.csv`
- `analysis/phase5_minimal_validation/p5_mv07c_bge_total_anchor/label_feature_audit.csv`
- `analysis/phase5_minimal_validation/p5_mv07c_bge_total_anchor/construct_target_map.csv`

Local-only MV07c artifact:

- `analysis/phase5_minimal_validation/p5_mv07c_bge_total_anchor/p5_mv07c_local_predictions.csv`

## Blockers And Risks

- CMDC remains worse than raw and projected total-allocation floors after
  train-fold-selected total anchoring.
- Additional shallow BGE head variants now risk p-hacking more than they reduce
  uncertainty unless the feature contract or measurement contract changes.
- The strongest immediate route to credibility is MV06 human annotation; the
  strongest RQ1 route would require a genuinely different audited feature or
  measurement design, not another small BGE post-processing variant.

## Next Handoff

Keep the full-method gate blocked. Next useful paths:

1. Complete MV06 human annotations and rerun the aggregate evidence summary
   gate.
2. Reframe the shallow BGE shared-symptom sequence as negative/partial evidence
   in the paper plan.
3. Only revisit RQ1 method validation with a changed feature or measurement
   contract that is specified before evaluation.
