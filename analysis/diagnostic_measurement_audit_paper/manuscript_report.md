# Diagnostic Paper Manuscript Draft Report

Generated: `2026-08-22T10:19:35+00:00`

## Decision

- Manuscript draft status: `ready_for_human_manuscript_editing_v0_1`.
- Traceability rows: `18`.
- Open editing items: `7`.
- Artifact hygiene passed: `True`.

A full manuscript draft has been assembled from aggregate, hygiene-passing paper artifacts; full-method claims remain blocked.

## Outputs

- `manuscript_artifact_hygiene_audit.json`
- `manuscript_draft.md`
- `manuscript_open_items.csv`
- `manuscript_report.md`
- `manuscript_run_summary.json`
- `manuscript_traceability_matrix.csv`

## Regeneration

```bash
python scripts/build_diagnostic_paper_claim_tables.py
python scripts/build_diagnostic_paper_data_governance_section.py
python scripts/build_diagnostic_paper_results_sections.py
python scripts/build_diagnostic_paper_bibliography.py
python scripts/build_diagnostic_paper_manuscript_draft.py
```
