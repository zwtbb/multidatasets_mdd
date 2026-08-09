# Session Memory: Phase 5 MV06 Annotation Workbench

Status: complete
Last updated: 2026-08-09 UTC
Thread/task: main agent MV06 annotation workflow support

## Scope

This session prepares the local-only human annotation workbench needed to
unblock MV06 evidence localization. It does not complete the annotations, make
RQ4 evidence claims, read raw clinical text, or export snippets.

## Current State

- Implemented `scripts/phase5_prepare_mv06_annotation_workbench.py`.
- Generated
  `analysis/phase5_minimal_validation/p5_mv06_evidence_annotation_workbench/`.
- The workbench reads the ignored MV06 pilot packet and ignored source map,
  then writes:
  - a 288-row ignored local annotation workbook for two annotator codes;
  - a 144-row ignored local review index with local text locators;
  - tracked schema, annotation rules, manifest, report, run summary, and
    hygiene audit.
- Local workbench files are ignored by the Phase 5 `*predictions*.csv` rule.
- No raw clinical text is read or copied. Local file locators appear only in
  ignored local files.
- `scripts/phase5_summarize_mv06_evidence_annotations.py` now defaults to the
  workbench file, while still accepting `--annotation-packet` for overrides.
- The summary gate was rerun from the workbench and remains
  `blocked_no_completed_annotations`: 0 completed candidates and 0
  double-annotated candidates.
- The full-method gate was rerun and now inventories 14 Phase 5 evidence rows,
  including `P5_MV06_workbench`; full method remains blocked.

## Key Decisions

- Treat the workbench as annotation infrastructure only.
- Use stable local annotator codes such as `ann_a` and `ann_b`; do not store
  personal identity in tracked outputs.
- Optional excerpts and reviewer notes must stay inside ignored local files.
- C09/HAMD03 remains explicit-evidence-only.
- RQ4 evidence-localization claims remain blocked until enough local
  annotations are completed, enough candidates are double annotated, agreement
  is summarized, prompt-artifact rates are reported, and tracked aggregate
  hygiene passes.

## Files Owned Or Touched

- `scripts/phase5_prepare_mv06_annotation_workbench.py`
- `scripts/phase5_summarize_mv06_evidence_annotations.py`
- `scripts/phase5_full_method_gate_audit.py`
- `analysis/phase5_minimal_validation/p5_mv06_evidence_annotation_workbench/`
- `analysis/phase5_minimal_validation/p5_mv06_evidence_annotation_summary/`
- `analysis/phase5_minimal_validation/full_method_gate_audit/`
- `MEMORY.md`
- `docs/master_experiment_plan.md`
- `docs/experiment_issue_log.md`
- `memory/sessions/session_17_phase5_mv06_evidence_annotation_summary_gate.md`
- `memory/sessions/session_22_phase5_full_method_gate_audit.md`
- `memory/sessions/session_master_orchestration.md`
- `memory/sessions/session_23_phase5_mv06_annotation_workbench.md`

## Generated Artifacts

Regeneration commands:

```bash
python scripts/phase5_prepare_mv06_annotation_workbench.py --overwrite
python scripts/phase5_summarize_mv06_evidence_annotations.py
python scripts/phase5_full_method_gate_audit.py
```

Versionable artifacts:

- `analysis/phase5_minimal_validation/p5_mv06_evidence_annotation_workbench/report.md`
- `analysis/phase5_minimal_validation/p5_mv06_evidence_annotation_workbench/run_summary.json`
- `analysis/phase5_minimal_validation/p5_mv06_evidence_annotation_workbench/artifact_hygiene_audit.json`
- `analysis/phase5_minimal_validation/p5_mv06_evidence_annotation_workbench/annotation_decision_rules.csv`
- `analysis/phase5_minimal_validation/p5_mv06_evidence_annotation_workbench/local_workbook_schema.csv`
- `analysis/phase5_minimal_validation/p5_mv06_evidence_annotation_workbench/local_artifact_manifest.csv`

Ignored local-only files:

- `analysis/phase5_minimal_validation/p5_mv06_evidence_annotation_workbench/p5_mv06_local_annotation_workbook_predictions.csv`
- `analysis/phase5_minimal_validation/p5_mv06_evidence_annotation_workbench/p5_mv06_local_review_index_predictions.csv`

## Blockers And Risks

- No annotation has been completed yet; this is the remaining MV06 blocker.
- Local workbook rows contain subject-level metadata and local text locators,
  so they must remain ignored and server-local.
- The summary gate can validate fields and summarize agreement, but it cannot
  replace human review.

## Next Handoff

Fill the ignored local workbook with at least 30 completed candidates and at
least 20 double-annotated candidates, then rerun:

```bash
python scripts/phase5_summarize_mv06_evidence_annotations.py
python scripts/phase5_full_method_gate_audit.py
```

Only use MV06 evidence in writing after the summary gate reaches
`ready_for_aggregate_evidence_review` and artifact hygiene passes.
