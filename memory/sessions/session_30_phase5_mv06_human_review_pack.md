# Session Memory: Phase 5 MV06 Human Review Pack

Status: complete
Last updated: 2026-08-13 UTC
Thread/task: main agent MV06 human review acceleration

## Scope

This session prepares a local-only human review pack for MV06 evidence
localization. It joins the ignored human annotation workbench with the ignored
AI preannotation workbook, adds deterministic review priority ranks, and writes
tracked aggregate summaries.

It does not modify the original human workbench, complete annotations, create
agreement evidence, make RQ4 evidence-localization claims, or export raw
clinical text/source locators in tracked files.

## Current State

- Implemented `scripts/phase5_prepare_mv06_human_review_pack.py`.
- Generated
  `analysis/phase5_minimal_validation/p5_mv06_human_review_pack/`.
- The script reads:
  - ignored human workbook:
    `analysis/phase5_minimal_validation/p5_mv06_evidence_annotation_workbench/p5_mv06_local_annotation_workbook_predictions.csv`;
  - ignored AI preannotation workbook:
    `analysis/phase5_minimal_validation/p5_mv06_ai_preannotation_triage/p5_mv06_local_ai_preannotation_workbook_predictions.csv`.
- It writes an ignored local review pack with 288 annotation rows and an ignored
  local candidate index with 144 candidates.
- Tracked outputs contain only aggregate review-pack counts, priority summaries,
  progress summaries, schema, local artifact manifest, report, run summary, and
  hygiene audit.
- Artifact hygiene passed with zero violations.
- The review pack status remains `ready_for_human_review_pack_not_claimable`;
  after importing the updated human workbook, the pack progress aggregates now
  reflect completed human annotations.
- Aggregate review-pack counts:
  - 144 candidates;
  - 288 annotation rows;
  - 79 AI keyword-match candidates;
  - 4 AI protocol-artifact candidates;
  - 82 priority-1/2 candidates;
  - 143 completed human candidates;
  - 143 double-completed human candidates.
- `scripts/phase5_summarize_mv06_evidence_annotations.py` was updated to
  compute dataset-stratified agreement and rerun. It now reports
  `ready_for_aggregate_evidence_review`.
- `scripts/phase5_full_method_gate_audit.py` was updated and rerun. It then
  read 21 Phase 5 run summaries, included `P5_MV06_review_pack`, passed
  artifact hygiene, and remained `blocked_but_publishable_diagnostic_direction`.
  Later MV08 work expanded the current gate to 23 evidence rows.

## Key Decisions

- Treat the review pack as a reviewer-facing convenience layer only.
- Human decisions must still be entered into the original ignored MV06 human
  workbench before rerunning the summary gate.
- AI suggestion fields must not be copied into evidence fields without human
  verification.
- The local review pack and candidate index may contain subject-level rows,
  local text locators, and local excerpts; they stay ignored local-only under
  the Phase 5 `*predictions*.csv` Git rule.
- Tracked outputs must remain aggregate-only and cannot be used as RQ4 evidence
  until the human summary gate passes.

## Files Owned Or Touched

- `scripts/phase5_prepare_mv06_human_review_pack.py`
- `scripts/phase5_full_method_gate_audit.py`
- `analysis/phase5_minimal_validation/p5_mv06_human_review_pack/`
- `analysis/phase5_minimal_validation/p5_mv06_evidence_annotation_summary/`
- `analysis/phase5_minimal_validation/full_method_gate_audit/`
- `MEMORY.md`
- `docs/master_experiment_plan.md`
- `docs/experiment_issue_log.md`
- `memory/sessions/session_22_phase5_full_method_gate_audit.md`
- `memory/sessions/session_master_orchestration.md`
- `memory/sessions/session_30_phase5_mv06_human_review_pack.md`

## Generated Artifacts

Regeneration commands:

```bash
python scripts/phase5_prepare_mv06_human_review_pack.py --overwrite
python scripts/phase5_summarize_mv06_evidence_annotations.py
python scripts/phase5_full_method_gate_audit.py
```

Versionable artifacts:

- `analysis/phase5_minimal_validation/p5_mv06_human_review_pack/report.md`
- `analysis/phase5_minimal_validation/p5_mv06_human_review_pack/run_summary.json`
- `analysis/phase5_minimal_validation/p5_mv06_human_review_pack/artifact_hygiene_audit.json`
- `analysis/phase5_minimal_validation/p5_mv06_human_review_pack/review_pack_schema.csv`
- `analysis/phase5_minimal_validation/p5_mv06_human_review_pack/aggregate_review_pack_summary.csv`
- `analysis/phase5_minimal_validation/p5_mv06_human_review_pack/aggregate_priority_summary.csv`
- `analysis/phase5_minimal_validation/p5_mv06_human_review_pack/aggregate_human_review_progress_summary.csv`
- `analysis/phase5_minimal_validation/p5_mv06_human_review_pack/local_artifact_manifest.csv`

Ignored local-only artifacts:

- `analysis/phase5_minimal_validation/p5_mv06_human_review_pack/p5_mv06_local_human_review_pack_predictions.csv`
- `analysis/phase5_minimal_validation/p5_mv06_human_review_pack/p5_mv06_local_human_review_candidate_index_predictions.csv`

## Blockers And Risks

- One CMDC candidate remains incomplete after the latest workbook import because
  the attachment omitted its two annotator rows.
- The review pack contains AI suggestions that can be wrong, especially for
  negation, time status, protocol artifacts, and C09/HAMD03 safety-sensitive
  evidence. Every row requires human verification.
- E-DAIC evidence-presence agreement is now computable with 24 double pairs and
  kappa `0.846`; field-specific degenerate marginal statuses remain in
  `agreement_summary.csv`.
- The full method remains blocked. The review pack and first-round annotation
  summary improve RQ4 credibility but do not resolve the RQ1 measurement gate.

## Next Handoff

Use the ignored local review pack if adding another annotation pass, especially
to expand E-DAIC double annotation. After editing the local workbook, rerun:

```bash
python scripts/phase5_summarize_mv06_evidence_annotations.py
python scripts/phase5_full_method_gate_audit.py
```

Use MV06 evidence in writing only as aggregate, dataset-stratified first-round
credibility evidence unless the annotation set is expanded.
