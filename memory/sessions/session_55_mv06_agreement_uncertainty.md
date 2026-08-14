# Session Memory: Phase 5 MV06 Agreement Uncertainty

Status: complete
Last updated: 2026-08-14 UTC
Thread/task: main agent MV06 aggregate agreement uncertainty

## Scope

This session adds aggregate-only agreement uncertainty to the existing MV06
human annotation summary gate, refreshes the full-method claim boundary and
paper scaffolds, and updates memory/docs. It does not read raw clinical text,
source locators, local snippets, local notes, row-level predictions, or
subject-level candidate rows beyond the ignored local annotation workbook
already required by the MV06 summary gate.

## Current State

- `scripts/phase5_summarize_mv06_evidence_annotations.py` now writes
  `agreement_uncertainty_summary.csv` alongside the existing
  `agreement_summary.csv`.
- The uncertainty table uses deterministic nonparametric percentile bootstrap
  over double-annotated candidate pairs with seed `20260814` and `2000`
  resamples.
- MV06 status remains `ready_for_aggregate_evidence_review`, with 143 completed
  and 143 double-annotated candidates over the 144-candidate local workbench.
- Evidence-presence kappa with 95 percent bootstrap CI:
  - ALL: `0.965`, CI `0.922-1.000`, 143 pairs.
  - CMDC: `0.967`, CI `0.885-1.000`, 59 pairs.
  - E-DAIC: `0.846`, CI `0.595-1.000`, 24 pairs.
  - PDCH: `1.000`, CI `1.000-1.000`, 60 pairs.
- Artifact hygiene passes for MV06 summary, full-method gate, and the
  diagnostic paper scaffolds.
- The full-method gate remains
  `blocked_but_publishable_diagnostic_direction` and
  `full_method_allowed=false`. RQ4 remains `allowed_limited`.

## Key Decisions

- Treat MV06 agreement uncertainty as sufficient for first-round aggregate
  credibility wording only. It does not authorize strong evidence-localization
  validity, feature-invariance, or full-method claims.
- Stronger RQ4 wording should still resolve the one incomplete local CMDC
  candidate if available and explicitly discuss sampling limits, especially the
  E-DAIC 24-pair CI width.
- Keep MV06 raw text, source locators, notes, local workbooks, review packs,
  and subject-level annotation rows local-only.

## Files Owned Or Touched

- `scripts/phase5_summarize_mv06_evidence_annotations.py`
- `scripts/phase5_full_method_gate_audit.py`
- `scripts/build_diagnostic_paper_claim_tables.py`
- `scripts/build_diagnostic_paper_results_sections.py`
- `analysis/phase5_minimal_validation/p5_mv06_evidence_annotation_summary/`
- `analysis/phase5_minimal_validation/full_method_gate_audit/`
- `analysis/diagnostic_measurement_audit_paper/`
- `MEMORY.md`
- `docs/master_experiment_plan.md`
- `docs/experiment_issue_log.md`
- `docs/diagnostic_measurement_audit_paper_outline.md`
- `memory/sessions/session_17_phase5_mv06_evidence_annotation_summary_gate.md`
- `memory/sessions/session_48_mv06_annotation_import_round2.md`
- `memory/sessions/session_55_mv06_agreement_uncertainty.md`

## Generated Artifacts

Regeneration commands:

```bash
python scripts/phase5_summarize_mv06_evidence_annotations.py
python scripts/phase5_full_method_gate_audit.py
python scripts/build_diagnostic_paper_claim_tables.py
python scripts/build_diagnostic_paper_results_sections.py
```

New or refreshed versionable outputs:

- `analysis/phase5_minimal_validation/p5_mv06_evidence_annotation_summary/agreement_uncertainty_summary.csv`
- `analysis/phase5_minimal_validation/p5_mv06_evidence_annotation_summary/report.md`
- `analysis/phase5_minimal_validation/p5_mv06_evidence_annotation_summary/run_summary.json`
- `analysis/phase5_minimal_validation/p5_mv06_evidence_annotation_summary/artifact_hygiene_audit.json`
- `analysis/phase5_minimal_validation/full_method_gate_audit/*`
- `analysis/diagnostic_measurement_audit_paper/*`

Verification commands:

```bash
python -m py_compile scripts/phase5_summarize_mv06_evidence_annotations.py scripts/phase5_full_method_gate_audit.py scripts/build_diagnostic_paper_claim_tables.py scripts/build_diagnostic_paper_results_sections.py
python scripts/phase5_summarize_mv06_evidence_annotations.py
python scripts/phase5_full_method_gate_audit.py
python scripts/build_diagnostic_paper_claim_tables.py
python scripts/build_diagnostic_paper_results_sections.py
```

## Blockers And Risks

- One CMDC sampled candidate remains incomplete because the user's uploaded
  workbook omitted its two annotator rows.
- E-DAIC evidence-presence uncertainty is wide because the completed E-DAIC
  double-annotation set has 24 pairs.
- Krippendorff alpha remains optional; current paper scaffolds use kappa plus
  bootstrap CIs.

## Next Handoff

Manuscript consolidation has since produced aggregate-only draft v0.1. Continue
with human manuscript editing, bibliography conversion, and cross-reference
cleanup. If RQ4 becomes manuscript-critical, resolve the remaining local CMDC
candidate if the annotator rows become available, then rerun the MV06 summary
gate and downstream paper/gate scripts.
