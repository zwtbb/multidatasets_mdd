# Session Memory: Phase 5 MV06 Human Review Pack

Status: complete
Last updated: 2026-08-09 UTC
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
- The review pack status is `ready_for_human_review_pack_not_claimable`.
- Aggregate counts:
  - 144 candidates;
  - 288 annotation rows;
  - 79 AI keyword-match candidates;
  - 4 AI protocol-artifact candidates;
  - 82 priority-1/2 candidates;
  - 0 completed human candidates;
  - 0 double-completed human candidates.
- `scripts/phase5_summarize_mv06_evidence_annotations.py` was rerun and remains
  `blocked_no_completed_annotations`.
- `scripts/phase5_full_method_gate_audit.py` was updated and rerun. It now
  reads 21 Phase 5 run summaries, includes `P5_MV06_review_pack`, passes
  artifact hygiene, and remains `blocked_but_publishable_diagnostic_direction`.

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

- Human annotation remains incomplete: 0 completed candidates and 0
  double-completed candidates.
- The review pack contains AI suggestions that can be wrong, especially for
  negation, time status, protocol artifacts, and C09/HAMD03 safety-sensitive
  evidence. Every row requires human verification.
- The full method remains blocked. The review pack improves workflow readiness
  but does not change the claim gate.

## Next Handoff

Use the ignored local review pack to prioritize manual review, then enter
verified human annotations into the original ignored MV06 human workbook. After
at least 30 candidates have complete annotations and at least 20 candidates are
double annotated, rerun:

```bash
python scripts/phase5_summarize_mv06_evidence_annotations.py
python scripts/phase5_full_method_gate_audit.py
```

Only use MV06 evidence in writing after the aggregate summary gate reaches
`ready_for_aggregate_evidence_review` and artifact hygiene passes.
