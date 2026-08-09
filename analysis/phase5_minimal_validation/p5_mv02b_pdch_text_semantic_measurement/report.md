# P5_MV02b PDCH Text Semantic Measurement

Generated: `2026-08-09T06:52:46+00:00`

## Scope

This bounded variant tests whether PDCH clinical text, read only through the audited manifest, can support HAMD-17 total, item, and construct-proxy measurement with fold-local character hashing Ridge heads. It is a PDCH-only measurement audit, not a full method and not a cross-dataset HAMD generalization result.

## Text And Split Contract

- PDCH HAMD text subjects: `99`.
- PDCH text segments: `165`.
- PDCH HAMD code-9 subjects: `7`; code `9` is excluded from item training/evaluation and item-derived total scoring.
- Subject-overlap violations: `0`.
- Feature spaces: `text_char_hash_subject_concat`.
- Ridge alpha policy: `fixed_train_only_alpha_100`.

## PDCH CV Summary

| summary target | feature space | model | MAE | seed count | target count |
| --- | --- | --- | ---: | ---: | ---: |
| hamd_total_direct | text_char_hash_subject_concat | direct_total_ridge | 6.173 | 5 | 1 |
| hamd_total_direct | none | train_mean_total | 6.181 | 5 | 1 |
| hamd_total_from_items | text_char_hash_subject_concat | itemwise_ridge | 6.175 | 5 | 1 |
| hamd_total_from_items | none | train_mean_items | 6.183 | 5 | 1 |
| macro_hamd_construct_proxy_mae | text_char_hash_subject_concat | itemwise_ridge | 0.684 | 5 | 13 |
| macro_hamd_construct_proxy_mae | none | train_mean_items | 0.684 | 5 | 13 |
| macro_hamd_item_mae | text_char_hash_subject_concat | itemwise_ridge | 0.747 | 5 | 17 |
| macro_hamd_item_mae | none | train_mean_items | 0.747 | 5 | 17 |

## Deltas

Negative deltas are improvements in MAE.

| summary target | feature space | model | delta vs train mean | delta vs best text |
| --- | --- | --- | ---: | ---: |
| hamd_total_direct | none | train_mean_total | 0.000 | 0.008 |
| hamd_total_direct | text_char_hash_subject_concat | direct_total_ridge | -0.008 | 0.000 |
| hamd_total_from_items | none | train_mean_items | 0.000 | 0.008 |
| hamd_total_from_items | text_char_hash_subject_concat | itemwise_ridge | -0.008 | 0.000 |
| macro_hamd_item_mae | none | train_mean_items | 0.000 | 0.000 |
| macro_hamd_item_mae | text_char_hash_subject_concat | itemwise_ridge | -0.000 | 0.000 |

## MV02 Reference

These rows are references from the earlier frozen-feature MV02 run, not re-estimated in MV02b.

| summary target | feature space | model | MAE |
| --- | --- | --- | ---: |
| hamd_total_direct | early_fusion_all | direct_total_ridge | 5.794 |
| hamd_total_direct | text_bge | direct_total_ridge | 5.970 |
| hamd_total_direct | none | train_mean_total | 6.181 |
| hamd_total_from_items | early_fusion_all | itemwise_ridge | 5.693 |
| hamd_total_from_items | text_bge | itemwise_ridge | 5.887 |
| hamd_total_from_items | none | train_mean_items | 6.183 |
| macro_hamd_item_mae | early_fusion_all | itemwise_ridge | 0.727 |
| macro_hamd_item_mae | text_bge | itemwise_ridge | 0.731 |
| macro_hamd_item_mae | none | train_mean_items | 0.747 |

## Verdict

- Pass-rule status: `blocked_weak_pdch_text_measurement_signal`.
- Best text direct-total MAE: `6.173` from `text_char_hash_subject_concat`.
- Best text item-derived total MAE: `6.175` from `text_char_hash_subject_concat`.
- Best text macro item MAE: `0.747` from `text_char_hash_subject_concat`.
- Item-total delta vs train mean: `-0.008`.
- Macro-item delta vs train mean: `-0.000`.

PDCH text hashing is runnable but weak: the best item-derived HAMD total gain is below the predefined meaningful-improvement threshold. Keep it as a diagnostic result.

## Hygiene

- Artifact hygiene passed: `True`.
- Row-level predictions are written as a local-only ignored CSV.
- Raw clinical text, source paths, vectorizers, learned features, model weights, prompts, and responses are not written.
