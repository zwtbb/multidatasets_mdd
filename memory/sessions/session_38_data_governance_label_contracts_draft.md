# Session Memory: Data Governance and Label Contracts Draft

Status: complete
Last updated: 2026-08-11 UTC
Thread/task: main agent diagnostic paper data-governance scaffold

## Scope

This session creates a paper-facing Data Governance and Label Contracts draft
for the diagnostic measurement-audit manuscript. It uses only registry fields,
aggregate dataset audit summaries, Phase 4 label-contract/construct-map
artifacts, and web-checked source context. It does not run models, scan raw
datasets, read row-level manifests for experiment input, inspect private MV06
review workbooks, export learned parameters, or authorize full method work.

## Current State

- Added and ran
  `scripts/build_diagnostic_paper_data_governance_section.py`.
- Generated aggregate paper scaffolds under
  `analysis/diagnostic_measurement_audit_paper/`.
- Current section status: `ready_for_manuscript_drafting`.
- Artifact hygiene passed with zero violations over 8 tracked output files.
- Also normalized the paper-facing claim-table wording from "raw snippets" to
  "verbatim excerpts" and strengthened that generator's artifact-hygiene check.
- Output row counts:
  - 6 dataset-governance rows;
  - 7 label-contract rows;
  - 4 construct-coverage rows;
  - 5 release-boundary rows;
  - 9 source-context rows.

## Key Decisions

- Treat the public data-governance tables as manuscript scaffolding only. They
  do not replace the registry/manifest layer for running experiments.
- Keep the release boundary conservative: real row-level tables, identifiers,
  local file references, raw transcripts, media, private evidence workbooks,
  row predictions, learned parameters, embeddings, and verbatim evidence
  excerpts remain local-only by default.
- The label-contract section should state that E-DAIC PHQ-8, CMDC PHQ-9, and
  PDCH HAMD-17 are the main item-level sources; CMDC HAMD is a small sanity
  subset; MODMA, EATD, and MPDD are total/severity stress or context datasets
  under the current manifest.
- Literature/source context is a writing aid. Re-check sources and convert them
  to formal bibliography entries before final submission.

## Files Owned Or Touched

- `scripts/build_diagnostic_paper_data_governance_section.py`
- `scripts/build_diagnostic_paper_claim_tables.py`
- `analysis/diagnostic_measurement_audit_paper/paper_claim_boundary.csv`
- `analysis/diagnostic_measurement_audit_paper/report.md`
- `analysis/diagnostic_measurement_audit_paper/run_summary.json`
- `analysis/diagnostic_measurement_audit_paper/artifact_hygiene_audit.json`
- `analysis/diagnostic_measurement_audit_paper/dataset_governance_summary.csv`
- `analysis/diagnostic_measurement_audit_paper/label_contract_summary.csv`
- `analysis/diagnostic_measurement_audit_paper/construct_coverage_summary.csv`
- `analysis/diagnostic_measurement_audit_paper/release_boundary_summary.csv`
- `analysis/diagnostic_measurement_audit_paper/source_context_data_governance.csv`
- `analysis/diagnostic_measurement_audit_paper/data_governance_label_contracts.md`
- `analysis/diagnostic_measurement_audit_paper/data_governance_report.md`
- `analysis/diagnostic_measurement_audit_paper/data_governance_run_summary.json`
- `analysis/diagnostic_measurement_audit_paper/data_governance_artifact_hygiene_audit.json`
- `docs/diagnostic_measurement_audit_paper_outline.md`
- `docs/experiment_issue_log.md`
- `MEMORY.md`
- `memory/sessions/session_38_data_governance_label_contracts_draft.md`
- `memory/sessions/session_master_orchestration.md`

## Generated Artifacts

Regeneration command:

```bash
python scripts/build_diagnostic_paper_data_governance_section.py
```

Validation commands used:

```bash
python -m py_compile scripts/build_diagnostic_paper_data_governance_section.py
python scripts/build_diagnostic_paper_data_governance_section.py
```

Versionable outputs:

- `analysis/diagnostic_measurement_audit_paper/dataset_governance_summary.csv`
- `analysis/diagnostic_measurement_audit_paper/label_contract_summary.csv`
- `analysis/diagnostic_measurement_audit_paper/construct_coverage_summary.csv`
- `analysis/diagnostic_measurement_audit_paper/release_boundary_summary.csv`
- `analysis/diagnostic_measurement_audit_paper/source_context_data_governance.csv`
- `analysis/diagnostic_measurement_audit_paper/data_governance_label_contracts.md`
- `analysis/diagnostic_measurement_audit_paper/data_governance_report.md`
- `analysis/diagnostic_measurement_audit_paper/data_governance_run_summary.json`
- `analysis/diagnostic_measurement_audit_paper/data_governance_artifact_hygiene_audit.json`

## Blockers And Risks

- The section is not a final manuscript. It still needs prose editing,
  bibliography integration, and cross-reference cleanup.
- E-DAIC MV06 agreement remains underpowered for stronger RQ4 claims.
- Full method construction remains blocked by the Phase 5 gate.

## Next Handoff

Draft the Baselines and Failure-Mode Diagnostics section from Phase 2 and Phase
3 aggregate summaries. If a stronger evidence-localization section is desired,
expand E-DAIC MV06 double annotation before strengthening RQ4 language.
