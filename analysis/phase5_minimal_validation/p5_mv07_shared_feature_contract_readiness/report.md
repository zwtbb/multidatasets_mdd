# P5_MV07 Shared Feature Contract Readiness

Generated: `2026-08-09T08:48:12+00:00`

## Scope

This audit checks whether existing cached subject-level features are aligned enough to run a revised shared-symptom minimal-validation row. It does not train a model and does not scan raw text, audio, video, or gait files.

## Decision

- Readiness status: `ready_to_run_minimal_validation`.
- Recommended next contract: `MV07_TEXT_BGE_ALIGNED_run_shallow_shared_symptom_validation`.
- Artifact hygiene passed: `True`.

The aligned BGE text contract is ready: E-DAIC, CMDC, and PDCH now share 512 BGE model-input columns. This authorizes the next MV07 shallow validation row, not a shared-symptom claim yet.

## Contract Readiness

| contract | status | required datasets | common columns | next step |
| --- | --- | --- | ---: | --- |
| MV07_TEXT_BGE_ALIGNED | `ready_to_run_minimal_validation` | edaic;cmdc;pdch | 512 | Run subject-level shallow-head MV07 with identity/protocol probes and local-only row predictions. |
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

## Recommended Next Actions

| rank | action | success gate |
| ---: | --- | --- |
| 1 | Run the MV07 shallow shared-symptom validation row on aligned E-DAIC/CMDC/PDCH BGE features. | subject-level PHQ/HAMD construct heads beat simple floors where applicable and include dataset/protocol identity probes with local-only predictions. |
| 2 | Regenerate aligned eGeMAPS subject features with one extractor/schema for E-DAIC, CMDC, PDCH, and EATD. | all required datasets share nonzero common model-input columns and pass artifact hygiene. |
| 3 | Specify a stronger WavLM identity-control variant before rerunning shared-symptom validation on WavLM. | feature identity is reduced in an inference-compatible setting while construct metrics stay within tolerance. |

## Interpretation Boundary

- Readiness means the feature contract is available; it is not model evidence.
- WavLM remains usable only as a controlled diagnostic because identity remains high.
- The cleanest next implementation is the aligned BGE MV07 shallow shared-symptom validation row with identity/protocol probes.
