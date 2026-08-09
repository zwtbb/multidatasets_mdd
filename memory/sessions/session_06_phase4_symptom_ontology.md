# Session Memory: Phase 4 Symptom Ontology

Status: complete
Last updated: 2026-08-09 UTC
Thread/task: main agent Phase 4 ontology and label-contract pass

## Scope

This session owns the first Phase 4 artifact: a cross-scale symptom ontology
and dataset label contract for PHQ-8, PHQ-9, HAMD-17, and SDS. It does not
train a model, implement the final method, or run cross-dataset experiments.

## Current State

- Implemented `scripts/phase4_build_symptom_ontology.py`.
- Generated `analysis/phase4_symptom_ontology/` with item catalog, construct
  map, dataset label contract, minimal validation matrix, source references,
  report, and audit JSON.
- The ontology defines 15 constructs and 54 short item-code mappings without
  storing long questionnaire wording.
- The label-contract audit now counts item-level coverage only when item
  payloads contain valid numeric labels. Placeholder NaN payloads are ignored.
- Core cross-scale PHQ/HAMD-overlap constructs are C01-C08: depressed mood,
  anhedonia, sleep, fatigue/energy, appetite/weight, self-worth/guilt,
  cognition/concentration, and psychomotor change.
- Death/self-harm is C09 and is safety-sensitive. It should rely only on
  explicit scale or clinical-text evidence, not weak audio/video/gait cues.
- Artifact hygiene passed with zero violations.

## Key Decisions

- Use PHQ-8/PHQ-9 overlap items as the cleanest shared construct bridge.
- Keep HAMD-17 anxiety, somatic, functioning, and insight items as auxiliary or
  scale-specific heads when they do not map cleanly to PHQ constructs.
- Treat SDS as theoretically mappable but project-total-only for now because
  EATD exposes SDS total/severity rather than SDS item labels.
- Use MPDD gait as psychomotor/context validation for C04/C08/C12, not direct
  item-level supervision.
- Use the six rows in
  `analysis/phase4_symptom_ontology/minimal_validation_matrix.csv` as the next
  planning input before any full method work.
- Treat CMDC HAMD as limited coverage: valid HAMD total+full-item labels cover
  25 of 78 subjects after placeholder filtering.
- Treat E-DAIC PHQ-8 item coverage as 219 item-labeled subjects out of 275
  total-labeled subjects; item-level PHQ construct work should not use current
  official test total-only labels.

## Files Owned Or Touched

- `scripts/phase4_build_symptom_ontology.py`
- `analysis/phase4_symptom_ontology/`
- `memory/sessions/session_06_phase4_symptom_ontology.md`

## Generated Artifacts

Regeneration command:

```bash
python scripts/phase4_build_symptom_ontology.py
```

Artifacts:

- `analysis/phase4_symptom_ontology/scale_item_catalog.csv`
- `analysis/phase4_symptom_ontology/construct_scale_map.csv`
- `analysis/phase4_symptom_ontology/dataset_label_contract.csv`
- `analysis/phase4_symptom_ontology/minimal_validation_matrix.csv`
- `analysis/phase4_symptom_ontology/scale_source_refs.csv`
- `analysis/phase4_symptom_ontology/phase4_symptom_ontology_report.md`
- `analysis/phase4_symptom_ontology/phase4_symptom_ontology_audit.json`

## Blockers And Risks

- CMDC HAMD is aligned for the 25 subjects with valid total+full-item labels,
  but coverage is too small for complete HAMD bridge claims.
- MODMA and MPDD have PHQ-9 total/severity labels but no PHQ-9 item fields, so
  they cannot provide item-level construct supervision in the current state.
- EATD has SDS total/severity only; SDS item-level constructs remain
  theoretical unless item labels are recovered.
- The mapping is a research engineering ontology and should receive a final
  clinical/theoretical review before manuscript claims.

## Next Handoff

Minimal method-validation protocol has been specified in
`analysis/phase5_minimal_validation/`. `P5_MV01` is complete, and `P5_MV02` is
now ready only in PDCH-only mode with CMDC held as a 25-subject sanity subset.
Keep full method work blocked until minimal validation produces stronger
positive evidence.
