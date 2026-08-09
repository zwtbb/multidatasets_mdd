# P5_MV07 Shared Feature Contract Readiness

Generated: `2026-08-09T08:09:34+00:00`

## Scope

This audit checks whether existing cached subject-level features are aligned enough to run a revised shared-symptom minimal-validation row. It does not train a model and does not scan raw text, audio, video, or gait files.

## Decision

- Readiness status: `blocked_current_cached_features_insufficient_for_mv07`.
- Recommended next contract: `MV07_TEXT_BGE_ALIGNED_after_generating_EDAIC_BGE`.
- Artifact hygiene passed: `True`.

Current caches are not sufficient for a fair new shared-symptom row: WavLM is aligned but identity-blocked, BGE text lacks E-DAIC, and eGeMAPS schemas are mismatched. Generate aligned E-DAIC BGE text features first.

## Contract Readiness

| contract | status | required datasets | common columns | next step |
| --- | --- | --- | ---: | --- |
| MV07_TEXT_BGE_ALIGNED | `blocked_missing_required_feature_cache` | edaic;cmdc;pdch | 0 | Generate text_bge subject features for: edaic. |
| MV07_AUDIO_EGEMAPS_ALIGNED | `blocked_schema_mismatch` | edaic;cmdc;pdch;eatd | 0 | Regenerate audio_egemaps with one shared schema/extractor across: edaic, cmdc, pdch, eatd. |
| MV07_AUDIO_WAVLM_CONTROLLED | `available_but_identity_blocked_current_contract` | edaic;cmdc;pdch | 768 | Only rerun WavLM after a stronger inference-compatible identity control is specified; current WavLM evidence is not enough. |

## Label Coverage

| dataset | label contract | usable subjects | note |
| --- | --- | ---: | --- |
| edaic | PHQ8_C01_C08_item_supervision | 219 | train_dev_only_no_official_test_item_labels |
| cmdc | PHQ9_C01_C08_item_supervision | 77 | clinical_interview_subjects |
| cmdc | HAMD17_limited_sanity_subset | 25 | coverage_limited_sanity_only |
| pdch | HAMD17_item_total_supervision | 99 | primary_hamd_internal_validation |
| eatd | SDS_total_only_external_stress | 162 | no_sds_item_supervision_current_manifest |

## Recommended Generation Queue

| rank | action | success gate |
| ---: | --- | --- |
| 1 | Generate E-DAIC subject-level BGE text features from manifest-governed transcripts. | edaic text_bge cache exists with bge_* columns, subject-level rows, no path-like columns, no raw text export. |
| 2 | Regenerate aligned eGeMAPS subject features with one extractor/schema for E-DAIC, CMDC, PDCH, and EATD. | all required datasets share nonzero common model-input columns and pass artifact hygiene. |
| 3 | Specify a stronger WavLM identity-control variant before rerunning shared-symptom validation on WavLM. | feature identity is reduced in an inference-compatible setting while construct metrics stay within tolerance. |

## Interpretation Boundary

- Current cached features do not yet authorize a new shared-symptom training row.
- WavLM remains usable only as a controlled diagnostic because identity remains high.
- The cleanest next implementation is to generate aligned E-DAIC BGE text features so E-DAIC, CMDC, and PDCH share one text feature family.
