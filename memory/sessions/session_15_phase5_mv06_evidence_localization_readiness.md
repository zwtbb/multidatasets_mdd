# Session Memory: Phase 5 MV06 Evidence Localization Readiness

Status: complete
Last updated: 2026-08-09 UTC
Thread/task: main agent MV06 readiness audit

## Scope

This session audits whether RQ4 construct evidence localization can start from
existing minimal-validation predictions and manifest text availability. It does
not read raw clinical text, export snippets, write source paths, annotate
evidence, or train a model.

## Current State

- Implemented `scripts/phase5_audit_mv06_evidence_localization_inputs.py`.
- Generated
  `analysis/phase5_minimal_validation/p5_mv06_evidence_localization_readiness/`.
- Linked local-only MV01 PHQ construct predictions and MV02 HAMD
  item/construct predictions to aggregate text availability in E-DAIC, CMDC,
  and PDCH manifests.
- Wrote `p5_mv06_local_candidate_predictions.csv` as a local-only ignored
  candidate queue. It may contain subject-level candidate rows and must not be
  committed by default.
- Tracked artifacts contain only aggregate counts, readiness labels, candidate
  bucket summaries, and an annotation protocol.
- Artifact hygiene passed with zero violations.

## Key Decisions

- MV06 readiness status: `ready_for_local_evidence_annotation`.
- E-DAIC readiness is limited to 56 prediction-text-overlap subjects from MV01
  dev predictions and C01-C08 constructs.
- CMDC readiness covers 77 prediction-text-overlap subjects with MV01 PHQ
  constructs and MV02 limited HAMD sanity predictions.
- PDCH readiness covers 99 prediction-text-overlap subjects with MV02 HAMD
  construct/item predictions.
- Any raw snippet review, source paths, and per-subject rationales must remain
  local-only unless separately deidentified and approved.
- Future tracked MV06 outputs should be aggregate evidence agreement,
  prompt-artifact rate, evidence-source distribution, and construct coverage,
  not raw text.

## Files Owned Or Touched

- `scripts/phase5_audit_mv06_evidence_localization_inputs.py`
- `scripts/phase5_build_minimal_validation_protocol.py`
- `analysis/phase5_minimal_validation/p5_mv06_evidence_localization_readiness/`
- `analysis/phase5_minimal_validation/experiment_matrix.csv`
- `analysis/phase5_minimal_validation/minimal_validation_protocol.md`
- `analysis/phase5_minimal_validation/readiness_audit.json`
- `MEMORY.md`
- `docs/experiment_issue_log.md`
- `memory/sessions/session_07_phase5_minimal_validation_protocol.md`
- `memory/sessions/session_15_phase5_mv06_evidence_localization_readiness.md`
- `memory/sessions/session_master_orchestration.md`

## Generated Artifacts

Regeneration commands:

```bash
python scripts/phase5_audit_mv06_evidence_localization_inputs.py
python scripts/phase5_build_minimal_validation_protocol.py
```

Versionable artifacts:

- `analysis/phase5_minimal_validation/p5_mv06_evidence_localization_readiness/report.md`
- `analysis/phase5_minimal_validation/p5_mv06_evidence_localization_readiness/run_summary.json`
- `analysis/phase5_minimal_validation/p5_mv06_evidence_localization_readiness/artifact_hygiene_audit.json`
- `analysis/phase5_minimal_validation/p5_mv06_evidence_localization_readiness/annotation_protocol.md`
- `analysis/phase5_minimal_validation/p5_mv06_evidence_localization_readiness/text_manifest_coverage.csv`
- `analysis/phase5_minimal_validation/p5_mv06_evidence_localization_readiness/prediction_source_summary.csv`
- `analysis/phase5_minimal_validation/p5_mv06_evidence_localization_readiness/evidence_readiness_summary.csv`
- `analysis/phase5_minimal_validation/p5_mv06_evidence_localization_readiness/candidate_queue_summary.csv`

Local-only artifact:

- `analysis/phase5_minimal_validation/p5_mv06_evidence_localization_readiness/p5_mv06_local_candidate_predictions.csv`

## Blockers And Risks

- No evidence snippets have been annotated yet; this is only a readiness and
  sampling-policy pass.
- E-DAIC evidence localization is currently dev-prediction scoped, not all
  item-labeled E-DAIC subjects.
- C09/death/self-harm evidence must remain explicit-evidence-only and should
  not be inferred from weak modality cues.
- Tracked outputs must not include raw clinical text, source paths, or
  subject-level rationales.

## Next Handoff

Run a local-only annotation pass over a small balanced candidate subset from
`p5_mv06_local_candidate_predictions.csv`. Commit only aggregate evidence
agreement statistics, prompt-artifact rates, evidence-source distributions, and
construct coverage after checking artifact hygiene.
