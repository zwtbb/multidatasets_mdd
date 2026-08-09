# Phase 3 Dataset/Protocol Identity Probe

Generated: `2026-08-04T16:36:29+00:00`

## Technical Summary

This diagnostic trains lightweight, grouped cross-validated logistic probes on cached Phase 2 frozen/lightweight features to estimate how much dataset, protocol, task, or valence identity remains in the representations. High identity-probe performance is diagnostic evidence that direct pooled training can exploit dataset/protocol signatures and therefore cannot be interpreted as learning a shared depression construct by itself.

All code, reports, and outputs are written under the current worktree. The probe reads existing Phase 2 feature-cache CSVs as read-only inputs and does not open raw text, audio, video, or path-valued manifest columns.

Canonical experiment order is treated as a hard constraint: data audit -> task/hypothesis freeze -> unified baselines -> failure-mode diagnostics -> minimal method validation -> full method -> cross-dataset experiments -> statistics/writing. This report is only the Phase 3 failure-mode diagnostic step; it does not implement a full model or method module.

## Key Findings

- `dataset_id_text_bge_cmdc_pdch`: balanced accuracy 1.000 [1.000, 1.000], macro-F1 1.000, n=176 rows / 176 groups.
- `dataset_id_video_openface_edaic_cmdc_common`: balanced accuracy 1.000 [1.000, 1.000], macro-F1 1.000, n=263 rows / 263 groups.
- `dataset_id_audio_wav2vec2_3way`: balanced accuracy 0.994 [0.979, 1.000], macro-F1 0.996, n=348 rows / 348 groups.
- `dataset_id_audio_wavlm_6way`: balanced accuracy 0.990 [0.980, 0.996], macro-F1 0.988, n=784 rows / 784 groups.
- `dataset_id_audio_egemaps_cmdc_pdch_modma`: balanced accuracy 0.989 [0.973, 1.000], macro-F1 0.989, n=228 rows / 228 groups.
- `protocol_modma_task_type_wavlm`: balanced accuracy 0.841 [0.788, 0.885], macro-F1 0.843, n=208 rows / 52 groups.
- `protocol_eatd_valence_wavlm`: balanced accuracy 0.553 [0.512, 0.595], macro-F1 0.554, n=486 rows / 162 groups.

## Scope And Definitions

- Dataset identity target: `dataset_id` over the datasets that share a comparable cached feature space.
- Protocol/task targets: available cached labels such as MODMA `task_type` and EATD `valence`, always grouped by subject.
- Metrics: accuracy, macro-F1, balanced accuracy, and bootstrap 95% CI over subject groups.
- Split rule: subject-level rows use stratified subject CV; repeated task/valence rows use grouped CV so the same subject cannot appear in train and validation folds.
- Classifier: fixed balanced multinomial logistic regression with median imputation and standard scaling inside each fold.

## Completed Probe Summary

| probe_id | target_name | n_rows | n_groups | n_classes | n_features_common | accuracy | macro_f1 | balanced_accuracy | majority_class_accuracy |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| dataset_id_audio_wavlm_6way | dataset identity | 784 | 784 | 6 | 768 | 0.990 | 0.988 | 0.990 | 0.279 |
| dataset_id_audio_wav2vec2_3way | dataset identity | 348 | 348 | 3 | 768 | 0.997 | 0.996 | 0.994 | 0.629 |
| dataset_id_audio_egemaps_cmdc_pdch_modma | dataset identity | 228 | 228 | 3 | 352 | 0.991 | 0.989 | 0.989 | 0.434 |
| dataset_id_text_bge_cmdc_pdch | dataset identity | 176 | 176 | 2 | 512 | 1.000 | 1.000 | 1.000 | 0.562 |
| dataset_id_video_openface_edaic_cmdc_common | dataset identity | 263 | 263 | 2 | 204 | 1.000 | 1.000 | 1.000 | 0.833 |
| protocol_modma_task_type_wavlm | MODMA task type | 208 | 52 | 4 | 768 | 0.841 | 0.843 | 0.841 | 0.250 |
| protocol_eatd_valence_wavlm | EATD valence | 486 | 162 | 3 | 768 | 0.553 | 0.554 | 0.553 | 0.333 |

## Comparability Caveats

- Cross-dataset results are only interpreted when cached feature columns are shared across the included datasets.
- Text frozen embeddings are comparable for CMDC versus PDCH because both use the same BGE feature space. E-DAIC text uses English DeBERTa/ModernBERT caches, and EATD/MODMA/MPDD have no cached subject-level text embedding in Phase 2, so a six-dataset text identity probe is not supported.
- Audio WavLM is the strongest six-dataset comparable probe because all six datasets have cached WavLM subject features.
- Audio eGeMAPS is pooled only for CMDC, PDCH, and MODMA because those caches share the same subject-level eGeMAPSv02 functional-statistic columns. E-DAIC uses a different low-level eGeMAPS summary, EATD stores valence-expanded columns, and MPDD has no Phase 2 eGeMAPS cache.
- Video OpenFace is pooled only for E-DAIC and CMDC after stripping CMDC segment-aggregation suffixes to recover common OpenFace statistic names. MPDD OpenFace is numeric-indexed and not safely joinable by semantic feature name; ResNet/TimeSformer video caches use different feature contracts.

## Stop/Go Implication

- **Stop:** direct joint training alone is not acceptable evidence of a shared depression representation, because dataset identity is almost perfectly recoverable from multiple frozen representation families.
- **Go:** proceed only to minimal method validation designs that explicitly control, penalize, stratify, or report dataset/protocol identity effects before any full method or cross-dataset experiment stage.
- **Design implication:** dataset/protocol robustness should be a required diagnostic gate in later method validation, especially for pooled WavLM/audio, CMDC-PDCH text, and OpenFace video experiments.

## Outputs

- `probe_metric_summary.csv`: metrics and bootstrap CIs.
- `probe_predictions.csv`: local-only out-of-fold predictions with subject/group identifiers only; ignored by default.
- `confusion_matrices_long.csv`: long-form confusion matrices.
- `feature_probe_inventory.csv`: completed and skipped probe inventory.
- `figures/probe_balanced_accuracy.png`: summary figure.
- `figures/confusion_*.png`: row-normalized confusion matrices.
