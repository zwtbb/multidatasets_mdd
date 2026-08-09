# P5_MV08 Partial-Invariance Measurement Design

Generated: `2026-08-09T16:52:36+00:00`

## Scope

This design audit turns the RQ1 pivot into a concrete minimal-validation row. It does not train a model, read raw text, or export row-level examples.

## Decision

- Readiness status: `ready_to_implement_partial_invariance_validation`.
- Recommended next action: `IMPLEMENT_MV08_TRAINER`.
- Artifact hygiene passed: `True`.

MV08 is ready to implement as a minimal-validation row: active item supervision exists for E-DAIC PHQ-8, CMDC PHQ-9, and PDCH HAMD-17. The row should compare total-score, fixed-map, and partial-invariance ordinal latent measurement heads before any full-method claim.

## Active Label Coverage

| dataset | scale | role | total subjects | item subjects | status |
| --- | --- | --- | ---: | ---: | --- |
| edaic | PHQ-8 | primary_phq_anchor | 219 | 219 | item_level_available |
| cmdc | PHQ-9 | cross_language_phq_anchor | 77 | 77 | item_level_available |
| cmdc | HAMD-17 | limited_hamd_sanity | 25 | 25 | limited_hamd_sanity_subset |
| pdch | HAMD-17 | primary_hamd_validation | 99 | 99 | item_level_available |

## Anchor Constructs

| construct | label | role | PHQ-8 | PHQ-9 | HAMD-17 |
| --- | --- | --- | --- | --- | --- |
| C01 | depressed_mood_negative_affect | core_anchor_partial_hamd | PHQ8_2 | PHQ9_2 | HAMD01 |
| C02 | anhedonia_low_positive_affect | core_anchor_partial_hamd | PHQ8_1 | PHQ9_1 | HAMD07 |
| C03 | sleep_disturbance | core_anchor_partial_hamd | PHQ8_3 | PHQ9_3 | HAMD04;HAMD05;HAMD06 |
| C04 | fatigue_low_energy | core_anchor_partial_hamd | PHQ8_4 | PHQ9_4 | HAMD07;HAMD13 |
| C05 | appetite_weight_change | core_anchor_partial_hamd | PHQ8_5 | PHQ9_5 | HAMD12;HAMD16 |
| C06 | self_worth_guilt_failure | core_anchor_partial_hamd | PHQ8_6 | PHQ9_6 | HAMD02 |
| C07 | cognition_concentration_decision | core_anchor_partial_hamd | PHQ8_7 | PHQ9_7 | HAMD08 |
| C08 | psychomotor_change | core_anchor_partial_hamd | PHQ8_8 | PHQ9_8 | HAMD08;HAMD09 |
| C09 | death_suicidality | safety_anchor_phq9_hamd_explicit_only |  | PHQ9_9 | HAMD03 |

## Model Ladder

| model | family | comparison role | DIF policy |
| --- | --- | --- | --- |
| M0_total_score_floor | baseline | must_beat_or_explain_failure | not_modeled |
| M1_fixed_construct_map | fixed_mapping | tests_the_old_hypothesis | no_free_dataset_dif |
| M2_partial_invariance_ordinal_latent | target_mv08 | next_rq1_candidate | allow_shrunk_dataset_or_scale_DIF_for_predeclared_items |
| M3_measurement_heterogeneity_moderators | later_extension | later_RQ3_RQ2_bridge | moderator_DIF_only_after_M2_passes |

## Readiness Gate

| gate | status | evidence | required next |
| --- | --- | --- | --- |
| G_LABEL_ACTIVE_DATASETS | `pass` | edaic_phq8_items=219;cmdc_phq9_items=77;pdch_hamd_items=99 | Use E-DAIC/CMDC/PDCH as active MV08 datasets; keep CMDC HAMD as sanity only. |
| G_CMDC_HAMD_SANITY_ONLY | `pass_limited` | cmdc_hamd_items=25 | Do not treat CMDC HAMD as a full HAMD external validation set. |
| G_PRIOR_FIXED_MAP_NEGATIVE | `pass` | analysis/phase5_minimal_validation/p5_mv07c_bge_total_anchor/run_summary.json | Use MV07/MV07b/MV07c as the negative/partial baseline sequence that justifies changing the measurement contract. |
| G_RQ4_SUPPORT_LIMITED | `pass_limited` | analysis/phase5_minimal_validation/p5_mv06_evidence_annotation_summary/run_summary.json | Use MV06 only as first-round aggregate credibility evidence; strengthen E-DAIC agreement later. |
| G_NO_FULL_METHOD_AUTHORIZATION | `blocked_full_method` | MV08 is a minimal-validation row design, not a full M0/M1/M2/M3 start. | Implement and audit MV08 before changing the full-method gate. |

## Implementation Queue

| rank | action | success gate |
| ---: | --- | --- |
| 1 | Create scripts/phase5_run_mv08_partial_invariance_measurement.py using aligned BGE features and subject-level folds. | Outputs compare M0 total, M1 fixed map, and M2 partial-invariance ordinal heads with dataset-stratified metrics. |
| 2 | Turn dif_parameter_contract.csv into a checked config that names exactly which loadings or thresholds may deviate. | No post-hoc item freeing without an issue-log entry and rerun of the design audit. |
| 3 | Run the first MV08 pilot on E-DAIC PHQ-8, CMDC PHQ-9, and PDCH HAMD-17 labels only. | Subject-level split checks pass, no raw text/media read, and artifact hygiene passes. |
| 4 | After MV08 results exist, rerun the full-method gate and decide whether RQ1 remains blocked or becomes a bounded method claim. | The gate changes only from measured evidence, not from design intent. |

## Interpretation Boundary

- MV08 design readiness does not authorize full M0/M1/M2/M3 construction.
- A future MV08 result must beat or explain failure against both total-score and fixed-map baselines.
- Any DIF finding must be reported as measurement heterogeneity, not hidden as a generic domain-adaptation residual.
