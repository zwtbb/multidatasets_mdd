# Phase 4 Symptom Ontology And Label Contract

Generated: `2026-08-09T05:16:45+00:00`

## Purpose

This artifact defines the cross-scale symptom constructs that are safe to use before minimal method validation. It maps PHQ-8, PHQ-9, HAMD-17, and SDS items to shared or scale-specific constructs, then audits which datasets actually expose item-level labels.

The mapping avoids long questionnaire wording. It uses item codes and short paraphrased labels only.

## Source Anchors

- PHQ-9: Kroenke, Spitzer, and Williams, 2001, Journal of General Internal Medicine (https://pmc.ncbi.nlm.nih.gov/articles/PMC1495268/)
- PHQ-8: Kroenke et al., 2009, Journal of Affective Disorders (https://www.sciencedirect.com/science/article/abs/pii/S0165032708002826)
- HAMD-17: Hamilton, 1960, Journal of Neurology, Neurosurgery and Psychiatry (https://dcf.psychiatry.ufl.edu/files/2011/05/HAMILTON-DEPRESSION.pdf)
- SDS: Zung, 1965, Archives of General Psychiatry (https://integrationacademy.ahrq.gov/sites/default/files/2020-07/Zung_Self_Rating_Depression_Scale.pdf)

## Construct Summary

- Constructs defined: `15`.
- Core PHQ/HAMD-overlap construct IDs: `C01;C02;C03;C04;C05;C06;C07;C08`.
- Project item-level supervision currently available for: `edaic:PHQ-8;cmdc:PHQ-9;cmdc:HAMD-17;pdch:HAMD-17`.
- Project total-only supervision currently available for: `modma:PHQ-9;eatd:SDS;mpdd_avg_2026:PHQ-9`.

## Key Mapping Decisions

- PHQ-8 and PHQ-9 share eight direct symptom constructs. PHQ-9 adds death/self-harm (C09), while PHQ-8 intentionally omits it.
- HAMD-17 can bridge many core constructs, but anxiety, somatic, and insight items should remain auxiliary or scale-specific heads rather than forced into PHQ-like supervision.
- SDS has a useful theoretical item map, but the current EATD manifest exposes SDS total/severity only, so EATD cannot train item-level constructs in the current project state.
- Death/self-harm (C09) is safety-sensitive. Treat it as explicit scale/text evidence only; do not infer it from weak acoustic, video, or gait cues.
- Gait should be used as psychomotor/context validation for C04/C08/C12, not as direct item supervision.

## Dataset Label Contract Caveats

- `edaic:PHQ-8`: PHQ-8 item labels cover 219 of 275 total-labeled subjects.
- `cmdc:HAMD-17`: HAMD-17 labels cover 25 of 78 CMDC subjects.
- `modma:PHQ-9`: no item-level construct supervision; PHQ-9 item labels cover 0 of 52 total-labeled subjects; controlled task stress-test dataset; no PHQ-9 item fields.
- `eatd:SDS`: no item-level construct supervision; SDS total/severity only; valence tasks are stress tests.
- `mpdd_avg_2026:PHQ-9`: no item-level construct supervision; PHQ-9 item labels cover 0 of 175 total-labeled subjects; PHQ-9 total/severity repeated over modality/task rows; no item fields.

## Minimal Validation Gate

Proceed to minimal method-validation planning with the six experiments in `minimal_validation_matrix.csv`. Do not build the full model until those experiments are specified with dataset/protocol/task/subgroup controls from the Phase 3 synthesis.

## Output Files

- `scale_item_catalog.csv`
- `construct_scale_map.csv`
- `dataset_label_contract.csv`
- `minimal_validation_matrix.csv`
- `scale_source_refs.csv`
- `phase4_symptom_ontology_audit.json`

## Planned Minimal Validation Rows

- `MV01` `phq8_phq9_core_construct_bridge`: shared construct supervision for the eight PHQ-overlap constructs with scale-specific output heads
- `MV02` `hamd17_bridge_to_core_constructs`: map HAMD items into shared constructs where defensible and keep anxiety/somatic/insight as auxiliary scale-specific heads
- `MV03` `sds_total_weak_bridge`: use EATD as external total/severity and valence stress test, not as an item-level construct trainer
- `MV04` `protocol_task_robust_validation`: evaluate minimal method under protocol, question-position, task, and valence slices before pooled reporting
- `MV05` `mpdd_context_calibration_validation`: test calibration/context conditioning separately from naive AVP concatenation
- `MV06` `construct_evidence_localization`: localize predicted constructs to observable text/audio/video evidence with scale-specific caveats
