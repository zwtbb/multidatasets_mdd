# Session Memory: Post-Review Measurement-Validity Triage

Status: complete
Last updated: 2026-08-21 UTC
Thread/task: main agent post-review triage after MV16 manuscript review

## Scope

This session owns the post-review route correction after the external-style
review of the current manuscript, BGE feature generation contract, bibliography,
and MV10-MV16 evidence. It updates paper framing, issue tracking, bibliography
metadata, manuscript generators, and the next experiment queue.

It does not rerun BGE features, MV07, MV12, MV15, or MV16. It does not read raw
clinical text, row-level predictions, feature matrices, local annotation
workbooks, fitted psychometric parameters, theta scores, or private source
locators.

## Current State

- Local code audit confirmed that `scripts/phase5_generate_mv07_edaic_bge_features.py`
  defaults to `BAAI/bge-small-zh-v1.5` for E-DAIC and concatenates available
  transcript `Text` rows without speaker filtering.
- The available E-DAIC transcript CSV contract lacks a speaker-role field, so
  participant/interviewer filtering is not available from that source.
- Primary-source checks confirmed that `BAAI/bge-small-zh-v1.5` is documented
  as Chinese, BGE-M3 is documented as multilingual, and multilingual-E5-base is
  a suitable second multilingual encoder sensitivity.
- Primary-source checks also confirmed bibliography metadata errors for P3HF,
  Multi-Probe Audit, and the EMNLP interviewer-bias paper.

## Key Decisions

- Treat the current MV07 -> MV12 -> MV15 -> MV16 BGE-linked feature-level chain
  as legacy/diagnostic until multilingual feature-contract sensitivity is run.
- MV10/MV11/MV13/MV14 label-only psychometric results are unaffected and remain
  the core positive evidence for substantial common PHQ structure plus
  localized C02/C06 threshold non-equivalence.
- Do not write the PHQ result as PHQ-8 versus PHQ-9 scale-specific DIF. The
  safe wording is E-DAIC/CMDC dataset-group localized threshold
  non-equivalence among shared PHQ items, with global model-selection
  uncertainty.
- Reframe the manuscript around target measurement validity:
  representation/protocol shift, target measurement shift, and prediction
  shift.
- Demote Phase 3 to motivating shortcut evidence, MPDD/RQ3 to population
  stress test, and MV06/RQ4 to measurement-interpretation credibility support.
- Next prioritized route:
  MV17a multilingual BGE-M3 plus multilingual-E5 feature-contract sensitivity,
  then MV18 CMDC-HAMD vs PDCH-HAMD same-scale exploratory control, MV19 PHQ
  finite-sample psychometric simulation, and MV20 criterion-contamination
  stress if needed.
- Stop extra shallow BGE heads, projection dimensions, MV16 calibration
  variants, personality gating/calibrators, and EATD valence-adversarial
  modules unless a new predeclared contract changes the gate.

## Files Owned Or Touched

- `/root/autodl-tmp/scripts/build_diagnostic_paper_bibliography.py`
- `/root/autodl-tmp/scripts/build_diagnostic_paper_claim_tables.py`
- `/root/autodl-tmp/scripts/build_diagnostic_paper_manuscript_draft.py`
- `/root/autodl-tmp/scripts/phase5_plan_mv17_postreview_measurement_validity_route.py`
- `/root/autodl-tmp/docs/experiment_issue_log.md`
- `/root/autodl-tmp/docs/diagnostic_measurement_audit_paper_outline.md`
- `/root/autodl-tmp/docs/master_experiment_plan.md`
- `/root/autodl-tmp/README.md`
- `/root/autodl-tmp/MEMORY.md`
- `/root/autodl-tmp/memory/ACTIVE_HANDOFF.md`
- `/root/autodl-tmp/memory/sessions/session_59_postreview_measurement_validity_triage.md`

## Generated Artifacts

Generation command used:

```bash
python scripts/phase5_plan_mv17_postreview_measurement_validity_route.py --overwrite
python scripts/build_diagnostic_paper_claim_tables.py
python scripts/build_diagnostic_paper_data_governance_section.py
python scripts/build_diagnostic_paper_results_sections.py
python scripts/build_diagnostic_paper_bibliography.py
python scripts/build_diagnostic_paper_manuscript_draft.py
```

Expected new/updated aggregate outputs:

- `/root/autodl-tmp/analysis/phase5_minimal_validation/p5_mv17_postreview_measurement_validity_route/`
- `/root/autodl-tmp/analysis/diagnostic_measurement_audit_paper/literature_positioning.csv`
- `/root/autodl-tmp/analysis/diagnostic_measurement_audit_paper/key_numeric_findings.csv`
- `/root/autodl-tmp/analysis/diagnostic_measurement_audit_paper/references.bib`
- `/root/autodl-tmp/analysis/diagnostic_measurement_audit_paper/citation_registry.csv`
- `/root/autodl-tmp/analysis/diagnostic_measurement_audit_paper/manuscript_draft.md`
- `/root/autodl-tmp/analysis/diagnostic_measurement_audit_paper/manuscript_open_items.csv`

Generation status:

- MV17 post-review route status: `ready_for_mv17a_design`.
- Bibliography status: `ready_for_manuscript_citation_editing`.
- Bibliography rows: 28 references, 34 source-context rows, zero unmapped rows.
- Manuscript status: `ready_for_human_manuscript_editing_v0_1`.
- Artifact hygiene passed for MV17 route, bibliography, and manuscript outputs.

## Blockers And Risks

- MV17a may require model download/runtime setup for BGE-M3 and multilingual-E5.
- Current E-DAIC transcript contract still lacks speaker roles; MV17a can fix
  language mismatch but not participant/interviewer mixing unless another
  speaker-resolved source is found.
- CMDC HAMD supervision is only a small sanity subset, so MV18 must be
  exploratory and cannot support formal same-scale invariance by itself.
- Bibliography generator corrections do not replace full submission-grade
  verification of all references against primary sources.

## Next Handoff

Next session should start MV17a design rather than rerunning MV16 or adding
another shallow model variant. Use
`analysis/phase5_minimal_validation/p5_mv17_postreview_measurement_validity_route/`
as the route contract.
