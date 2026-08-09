# P5_MV06 Evidence Annotation Workbench

Generated: `2026-08-09T07:58:51+00:00`

## Scope

This workbench prepares local-only files for human MV06 evidence annotation. It does not read raw clinical text, copy snippets, train a model, or export subject-level rows to tracked artifacts.

## Local Files

- Annotation workbook: `p5_mv06_local_annotation_workbook_predictions.csv`.
- Review index: `p5_mv06_local_review_index_predictions.csv`.
- Both local files are ignored by Git through the Phase 5 predictions rule.
- The workbook can be passed to the aggregate gate with `--annotation-packet` after local review is filled.

## Workbook Summary

- Candidate count: `144`.
- Workbook rows: `288`.
- Annotator codes: `2`.
- Candidates with local text locators: `144`.

## Annotation Rules

- Use only the allowed categorical values recorded in `annotation_decision_rules.csv`.
- Keep optional excerpts and reviewer notes inside the ignored local workbook only.
- Treat death/self-harm targets as explicit-evidence-only.
- Mark prompt-driven or fixed-task evidence as protocol artifact instead of symptom evidence.

## Next Command

After local annotation is filled, run:

```bash
python scripts/phase5_summarize_mv06_evidence_annotations.py --annotation-packet analysis/phase5_minimal_validation/p5_mv06_evidence_annotation_workbench/p5_mv06_local_annotation_workbook_predictions.csv
```

## Decision

- Workbench status: `ready_for_local_human_annotation`.
- This is annotation infrastructure only. RQ4 evidence-localization claims remain blocked until the aggregate summary gate passes.

## Hygiene

- Artifact hygiene passed: `True`.
- Tracked files contain no raw text, no local source locators, and no subject-level annotation rows.
