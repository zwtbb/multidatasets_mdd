# Session Memory: Phase 5 MV06 Local AI Preannotation Triage

Status: complete
Last updated: 2026-08-09 UTC
Thread/task: main agent MV06 local AI preannotation support

## Scope

This session creates a local-only AI triage helper for MV06 evidence
localization. It reads the ignored MV06 workbench and raw clinical text through
local text locators, then writes an ignored preannotation workbook to speed
human review.

It does not replace human annotation, does not produce annotator agreement, and
does not unblock RQ4 evidence-localization claims.

## Current State

- Implemented `scripts/phase5_run_mv06_local_ai_preannotation.py`.
- Generated
  `analysis/phase5_minimal_validation/p5_mv06_ai_preannotation_triage/`.
- The script read the ignored human workbench with 288 rows over 144 unique
  candidates.
- It scanned local text through ignored locators and wrote
  `p5_mv06_local_ai_preannotation_workbook_predictions.csv` as an ignored
  local-only file.
- AI triage filled one preannotation row per candidate using deterministic
  construct keyword rules. It found keyword evidence for 79/144 candidates.
- Tracked outputs contain only aggregate counts, a local artifact manifest,
  a report, run summary, and hygiene audit.
- Artifact hygiene passed with zero violations.
- The default MV06 human summary gate was rerun and remains
  `blocked_no_completed_annotations`.
- The full-method gate was rerun and remains
  `blocked_but_publishable_diagnostic_direction`.

## Key Decisions

- Treat the AI preannotation status as
  `ready_for_human_review_not_claimable`.
- AI triage can help a reviewer prioritize and correct local annotations, but
  it must not be counted as human annotation, double annotation, agreement
  evidence, or RQ4 validity evidence.
- Local preannotation rows may contain raw excerpts and source locators only
  because they are ignored local-only artifacts.
- Tracked outputs must never include raw snippets, source locators,
  subject-level rationales, or private reviewer notes.

## Files Owned Or Touched

- `scripts/phase5_run_mv06_local_ai_preannotation.py`
- `scripts/phase5_full_method_gate_audit.py`
- `analysis/phase5_minimal_validation/p5_mv06_ai_preannotation_triage/`
- `analysis/phase5_minimal_validation/p5_mv06_evidence_annotation_summary/`
- `analysis/phase5_minimal_validation/full_method_gate_audit/`
- `MEMORY.md`
- `docs/master_experiment_plan.md`
- `docs/experiment_issue_log.md`
- `memory/sessions/session_master_orchestration.md`
- `memory/sessions/session_17_phase5_mv06_evidence_annotation_summary_gate.md`
- `memory/sessions/session_22_phase5_full_method_gate_audit.md`
- `memory/sessions/session_23_phase5_mv06_annotation_workbench.md`
- `memory/sessions/session_27_phase5_mv06_local_ai_preannotation.md`

## Generated Artifacts

Regeneration commands:

```bash
python scripts/phase5_run_mv06_local_ai_preannotation.py --overwrite
python scripts/phase5_summarize_mv06_evidence_annotations.py
python scripts/phase5_full_method_gate_audit.py
```

Versionable artifacts:

- `analysis/phase5_minimal_validation/p5_mv06_ai_preannotation_triage/report.md`
- `analysis/phase5_minimal_validation/p5_mv06_ai_preannotation_triage/run_summary.json`
- `analysis/phase5_minimal_validation/p5_mv06_ai_preannotation_triage/artifact_hygiene_audit.json`
- `analysis/phase5_minimal_validation/p5_mv06_ai_preannotation_triage/preannotation_summary.csv`
- `analysis/phase5_minimal_validation/p5_mv06_ai_preannotation_triage/aggregate_preannotation_presence_summary.csv`
- `analysis/phase5_minimal_validation/p5_mv06_ai_preannotation_triage/aggregate_preannotation_source_summary.csv`
- `analysis/phase5_minimal_validation/p5_mv06_ai_preannotation_triage/local_artifact_manifest.csv`

Ignored local-only artifact:

- `analysis/phase5_minimal_validation/p5_mv06_ai_preannotation_triage/p5_mv06_local_ai_preannotation_workbook_predictions.csv`

## Blockers And Risks

- Human annotation remains incomplete: 0 completed candidates and 0
  double-annotated candidates in the default MV06 summary gate.
- Keyword triage can miss symptom evidence, overmatch protocol text, or
  misread negation/time status. Every row requires human review.
- C09/HAMD03 death/self-harm rows remain explicit-evidence-only and should be
  reviewed conservatively.

## Next Handoff

Use the ignored AI preannotation workbook as a local review aid while filling
the ignored human annotation workbook. After at least 30 candidates have
complete human annotations and at least 20 candidates are double annotated,
rerun:

```bash
python scripts/phase5_summarize_mv06_evidence_annotations.py
python scripts/phase5_full_method_gate_audit.py
```

Only use MV06 evidence in writing if the aggregate human summary gate reaches
`ready_for_aggregate_evidence_review` and artifact hygiene passes.
