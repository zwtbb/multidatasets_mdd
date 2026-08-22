# Session Memory: MV20 Criterion-Overlap Stress

Status: complete
Last updated: 2026-08-22 UTC
Thread/task: main-agent continuation after post-review MV20 request

## Scope

This session owns the final bounded MV20 criterion-overlap stress test and the
follow-on synchronization of gates, consolidation outputs, paper scaffolds,
README/docs, issue log, and memory. It should not add another prediction model,
threshold search, insertion variant, or contamination-aware architecture.

## Current State

MV20 is complete at
`/root/autodl-tmp/analysis/phase5_minimal_validation/p5_mv20_criterion_overlap_stress/`.
The run uses existing ignored MV17a segment-embedding caches, BGE-M3 as the
primary encoder, and multilingual-E5-base as sensitivity. CMDC is the only
included dataset because it has stable Q1-Q12 question-position segment units.
PDCH is excluded because available units are coarse consultation segments.
E-DAIC is excluded because the available transcript contract lacks true
prompt/speaker units and position proxies were disallowed.

Primary BGE-M3 CMDC PHQ-9 top-20 results: all/minus-high/minus-random/high-only
MAE is `3.571`/`3.918`/`3.768`/`4.215`. Criterion excess loss versus matched
random deletion is `0.150` with 95 percent CI `-0.320` to `0.671`. The primary
gate is `no_excess_criterion_overlap_evidence`. Multilingual-E5 sensitivity has
the same no-excess gate. The MV20 pass rule status is
`complete_mv20_no_primary_criterion_overlap_excess`.

## Key Decisions

- Treat MV20 as a negative/bounded stress test, not positive evidence for
  criterion contamination as the dominant shortcut.
- Stop further criterion-overlap threshold tuning, insertion variants, and
  contamination-aware model work. The predeclared stop rule freezes experiments
  after MV20 regardless of result.
- Keep row predictions local-only as
  `/root/autodl-tmp/analysis/phase5_minimal_validation/p5_mv20_criterion_overlap_stress/mv20_predictions.csv`.
  The tracked MV20 artifacts are aggregate summaries, reports, contracts, and
  hygiene outputs only.
- Paper wording should say MV20 closes a protocol-label-overlap gap with a
  CMDC-only negative stress test. It must also state the feasibility boundary:
  no PDCH clean question units and no E-DAIC true prompt/speaker units.

## Files Owned Or Touched

- `/root/autodl-tmp/scripts/phase5_run_mv20_criterion_overlap_stress.py`
- `/root/autodl-tmp/scripts/phase5_full_method_gate_audit.py`
- `/root/autodl-tmp/scripts/phase5_consolidate_experiment_inventory.py`
- `/root/autodl-tmp/scripts/phase5_plan_mv17_postreview_measurement_validity_route.py`
- `/root/autodl-tmp/scripts/build_diagnostic_paper_claim_tables.py`
- `/root/autodl-tmp/scripts/build_diagnostic_paper_results_sections.py`
- `/root/autodl-tmp/scripts/build_diagnostic_paper_manuscript_draft.py`
- `/root/autodl-tmp/scripts/build_diagnostic_paper_bibliography.py`
- `/root/autodl-tmp/README.md`
- `/root/autodl-tmp/docs/master_experiment_plan.md`
- `/root/autodl-tmp/docs/diagnostic_measurement_audit_paper_outline.md`
- `/root/autodl-tmp/docs/experiment_issue_log.md`
- `/root/autodl-tmp/MEMORY.md`
- `/root/autodl-tmp/memory/ACTIVE_HANDOFF.md`

## Generated Artifacts

Regenerate MV20 with:

```bash
python scripts/phase5_run_mv20_criterion_overlap_stress.py
```

Regenerate downstream gates and paper scaffolds with:

```bash
python scripts/phase5_plan_mv17_postreview_measurement_validity_route.py --overwrite
python scripts/phase5_full_method_gate_audit.py
python scripts/phase5_consolidate_experiment_inventory.py
python scripts/build_diagnostic_paper_bibliography.py
python scripts/build_diagnostic_paper_claim_tables.py
python scripts/build_diagnostic_paper_results_sections.py
python scripts/build_diagnostic_paper_manuscript_draft.py
```

Key tracked outputs include MV20 `run_summary.json`, `metric_summary.csv`,
`criterion_effect_summary.csv`, `feasibility_audit.csv`,
`overlap_position_summary.csv`, `pass_fail_gate_results.csv`, refreshed
full-method gate outputs, refreshed experiment consolidation outputs, refreshed
paper claim/results/manuscript/bibliography outputs, and hygiene audits.

## Blockers And Risks

- MV20 is CMDC-only. This is a design boundary, not a missing execution step:
  PDCH and E-DAIC do not expose clean question/prompt units under the current
  manifest/transcript contract.
- The primary excess-loss estimate is directionally positive but uncertain
  because the bootstrap interval crosses zero. Do not spin this into a positive
  criterion-contamination claim.
- Bibliography rows still require full primary-source verification before
  submission, even though the current registry/source map is generated and
  hygiene-checked.
- MV06 still has one incomplete CMDC local candidate. Resolve it only if
  stronger RQ4 wording is needed.

## Next Handoff

Finish manuscript finalization and citation verification within the
target-measurement-validity frame. Do not start additional experiments unless a
new design contract genuinely changes the gate.
