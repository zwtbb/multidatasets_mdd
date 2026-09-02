# MV24 Measurement-Aware Ordinal Architecture

MV24 fixes the measurement-aware framework to one official design: frozen foundation representations feed a shared eight-dimensional symptom layer, and observed PHQ shared-item responses are reconstructed by corpus-specific cumulative-logit ordinal heads.

## Architecture

- Input: frozen subject-level foundation representation from Qwen3 text, WavLM speech, and OpenFace video statistics.
- Projector: Linear-PCA(128) -> Linear(256) -> GELU -> Dropout(0.08) -> LayerNorm -> Linear(256) -> GELU.
- Shared symptom layer: Linear(hidden_dim, 8) mapped to the eight PHQ shared symptom items.
- Measurement heads: one corpus-specific cumulative-logit ordinal head per corpus; each item has a positive discrimination slope and three ordered thresholds.
- Training protocol: source warm-start of projector, shared symptom layer, and source ordinal head; source head initialization of the target ordinal head; core measurement-aware adaptation with source and target-calibration ordinal reconstruction; optional MMD evaluated as an auxiliary variant.

## Loss

`L_MA = NLL_src + lambda_cal*NLL_tgt_cal + lambda_l2*(||S_src||^2+||S_tgt||^2); L_MA+MMD = L_MA + lambda_mmd*MMD(S_src,S_tgt)`

| weight | value |
| --- | ---: |
| lambda_cal | 16.0000 |
| lambda_mmd_auxiliary | 0.0010 |
| lambda_l2 | 0.0001 |

## Main Metric

The co-primary metrics are `target_macro_item_mae` and `target_calibration_mae`. The reconstruction-plus-calibration score remains a supplementary compact summary rather than a new clinical scale.

## Supervision Regimes

- `zero_target_label`: ERM, CORAL, MMD, DANN, strongest foundation baseline, and latent-only use no target clinical labels.
- `target_calibrated`: corpus-specific-head, direct target fine-tuning, direct source+target multitask, shared ordinal head, generic target MLP head, measurement-aware core (`full_without_mmd`), and measurement-aware + MMD (`full_measurement_aware`) use the same target calibration split and the same labeled target budget.
- Measurement-aware target-pathway claims must be judged against calibrated baselines that also allow target labels to update shared layers; corpus-specific-head alone is retained only as a weak legacy comparator.
- The current fair-ablation gate is recorded in `run_summary.json`; if it is not passed, report target calibration/shared-layer adaptation as the robust finding and keep measurement-parameterization claims bounded.
- Direct significance claims are restricted to methods within the same target-label budget and matched target-label exposure.

## Secondary Clinical Endpoint

The secondary classification endpoint thresholds the observed and predicted shared-PHQ total at `10` and reports macro-F1, balanced accuracy, AUROC, AUPRC, sensitivity, and specificity. These metrics are for clinical-reader orientation and do not replace the ordinal reconstruction/calibration primary metric.
