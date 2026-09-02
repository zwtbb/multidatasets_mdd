# Session Memory: MV24 Measurement-Aware Ordinal Model

Status: complete
Last updated: 2026-08-28 UTC
Thread/task: formal measurement-aware architecture and clean main-result table

## Scope

This session implemented the user-approved mechanism-changing PHQ shared-item
method route. It does not reopen full HAMD MIM/IRT, WavLM Large, HuBERT Large,
VideoMAE, or end-to-end multimodal fine-tuning.

## Current State

MV24 is complete. The architecture is fixed as frozen Qwen3 text, WavLM speech,
and OpenFace video subject features, followed by a trainable projector, a
shared eight-dimensional PHQ symptom layer, and corpus-specific cumulative-logit
ordinal heads for the eight shared PHQ items. Training uses source warm-start,
source-head initialization of the target ordinal head, target calibration
ordinal reconstruction, and shared-symptom MMD. The DIL-MDD result style has
now been adopted for presentation rather than task definition: keep
direction-specific results visible and add class-imbalance-sensitive binary
endpoint metrics as secondary clinical readouts.

The cleaned main table now separates target-label budgets. ERM, CORAL, MMD,
DANN, strongest direct foundation baseline, and latent-only are
zero-target-label rows. Corpus-specific-head, Full w/o MMD, and full
measurement-aware use the same labeled target calibration split. The
measurement-aware ordinal family improves over the same-budget
corpus-specific-head ablation in both directions on the primary
`reconstruction_calibration_score = target_macro_item_mae + target_calibration_mae`
and is the direct same-budget paired-significance comparison:

- CMDC-to-E-DAIC: full score `1.243 [1.170, 1.317]`.
- E-DAIC-to-CMDC: full score `0.987 [0.863, 1.111]`, effectively tied with
  Full w/o MMD.

MV24 now also reports secondary total-score and binary endpoint metrics:
total MAE/CCC and shared-PHQ total >=10 Macro-F1, Balanced Accuracy, AUROC,
AUPRC, Sensitivity, and Specificity. The lambda-MMD sweep
`0/1e-4/1e-3/1e-2/1e-1` is nearly flat, so the manuscript should treat MMD as a
mild regularizer while emphasizing the target-calibrated ordinal measurement
pathway.

Artifact hygiene passes. Outputs are aggregate-only.

## Key Decisions

- The formal model is no longer described as a menu of calibration, IRT,
  regression, or classification heads. The official manuscript method should
  use cumulative-logit ordinal heads.
- Do not write MV24 as "full beats every cross-domain baseline" without
  qualification. Full, Full w/o MMD, and corpus-specific-head use target
  calibration labels; ERM/CORAL/MMD/DANN/foundation/latent-only do not. The
  fair superiority claim is the measurement-aware ordinal family versus
  corpus-specific-head under the same target-calibration label budget.
- MV22/MV23 should be described as foundation-era stress tests. MV24 is the
  current main method table.
- Old M0/M1/M2/M3 cross-scale full-method construction remains blocked, but
  that historical gate should not suppress the now-completed MV24 PHQ
  shared-item method claim.

## Files Owned Or Touched

- `scripts/phase5_run_mv24_measurement_aware_ordinal_model.py`
- `analysis/phase5_minimal_validation/p5_mv24_measurement_aware_ordinal_model/`
- `analysis/diagnostic_measurement_audit_paper/foundation_backbone_measurement_aware_validation_contract.md`
- `docs/diagnostic_measurement_audit_paper_outline.md`
- `docs/experiment_issue_log.md`
- `README.md`
- `MEMORY.md`
- `memory/ACTIVE_HANDOFF.md`

## Generated Artifacts

Regeneration command:

```bash
python scripts/phase5_run_mv24_measurement_aware_ordinal_model.py --clean
```

Primary artifact directory:

```text
analysis/phase5_minimal_validation/p5_mv24_measurement_aware_ordinal_model/
```

Key files:

- `architecture_contract.md`
- `architecture_contract.json`
- `main_result_table.md`
- `main_result_table.csv`
- `secondary_clinical_metrics_table.md`
- `secondary_clinical_metrics_table.csv`
- `mmd_sensitivity_table.md`
- `mmd_sensitivity_table.csv`
- `mmd_sensitivity_plot.png`
- `mmd_sensitivity_by_seed.csv`
- `mmd_sensitivity_summary.csv`
- `zero_target_label_result_table.md`
- `zero_target_label_result_table.csv`
- `target_calibrated_result_table.md`
- `target_calibrated_result_table.csv`
- `label_budget_contract.csv`
- `summary_by_method.csv`
- `metrics_by_seed.csv`
- `paired_significance.csv`
- `artifact_hygiene_audit.json`

## Blockers And Risks

- MV24 uses existing frozen subject-level feature caches. It is not a WavLM
  Large/HuBERT Large/VideoMAE/end-to-end fine-tuning claim.
- Target calibration labels are used by the corpus-specific-head, Full w/o MMD,
  and full measurement-aware rows; the manuscript should present this as
  measurement adaptation rather than zero-shot transfer.
- DANN does not currently export post-head source predictions, so its
  post-head domain identity column is blank. Its prediction and feature-level
  domain identity metrics remain usable.

## Next Handoff

MV24 is integrated into the manuscript Method/Experiment/Results flow:

- Section 3/7: fixed shared symptom layer plus corpus-specific cumulative-logit
  ordinal heads are the official architecture language.
- Section 6: MV24 main table, secondary endpoint table, and lambda-MMD
  sensitivity are now integrated into the reframed manuscript draft. Keep
  MV22/MV23 as supporting foundation-era stress tests.
- The Feishu wiki manuscript has also been refreshed to revision 97 with the
  DIL-MDD Related Work update, Table 3, Table 4, and the sensitivity figure.
- Figure/table pass: the user will hand-draw the total figure; keep the
  programmatic sensitivity plot as a supplement/backup unless layout needs a
  compact main-text ablation panel.
