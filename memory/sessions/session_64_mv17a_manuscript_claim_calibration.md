# Session Memory: session_64_mv17a_manuscript_claim_calibration

Status: complete
Last updated: 2026-08-22 UTC
Thread/task: Main-agent MV17a manuscript claim calibration

## Scope

This session owns the paper-level claim calibration requested after the latest
main-branch review: make MV17a the canonical prediction-consequence layer,
demote the old Chinese-BGE MV12/MV15/MV16 chain to legacy/supporting
diagnostics, update the SCD-MLLM citation to its final Pattern Recognition
article metadata, and keep MV18/MV19 wording within their bounded scopes.

It should not add new experiments, rerun MV16, create new model variants, or
promote feature-invariance/shared-symptom claims beyond the full-method gate.

## Current State

MV17a is now the manuscript-facing feature contract:

- BGE-M3 is the primary multilingual encoder.
- multilingual-E5 is the sensitivity encoder.
- Both encoders regenerate E-DAIC/CMDC/PDCH subject-level features and rerun
  MV07/MV12/MV15.
- Both keep MV07/MV12/MV15 blocked.
- Both pass same-dataset theta utility, fail observed-scale safety, and keep
  theta-conditioned feature identity BA at `1.000`.
- External theta transfer is encoder-dependent: BGE-M3 passes and
  multilingual-E5 fails.
- B3 Pareto dominance is encoder-dependent: false for BGE-M3 and true for
  multilingual-E5.

The stable manuscript claim is that psychometric harmonization can reduce
output-level dataset identity, but current features do not establish
observed-scale-safe or feature-invariant cross-corpus prediction.

## Key Decisions

- Do not claim universal external theta transfer failure from MV17a.
- Do not claim universal B3 Pareto dominance from MV17a.
- Treat old Chinese-BGE MV12/MV15/MV16 outputs as legacy/supporting evidence
  and appendix/historical context, not the canonical feature contract.
- Treat MV18 same-HAMD results as exploratory threshold/context-shift flags,
  not formal HAMD DIF or invariance.
- Treat MV19 as finite-sample calibration of the current PHQ item-level
  screening/localization procedure, not a formal IRT power simulation.
- Keep the full-method gate blocked unless a genuinely new data, feature, or
  measurement mechanism changes the contract.

## Files Owned Or Touched

- `scripts/build_diagnostic_paper_results_sections.py`
- `scripts/build_diagnostic_paper_claim_tables.py`
- `scripts/build_diagnostic_paper_manuscript_draft.py`
- `scripts/build_diagnostic_paper_bibliography.py`
- `scripts/phase5_full_method_gate_audit.py`
- `analysis/diagnostic_measurement_audit_paper/`
- `analysis/phase5_minimal_validation/full_method_gate_audit/`
- `analysis/phase5_minimal_validation/experiment_consolidation/`
- `README.md`
- `docs/diagnostic_measurement_audit_paper_outline.md`
- `docs/master_experiment_plan.md`
- `docs/experiment_issue_log.md`
- `MEMORY.md`
- `memory/ACTIVE_HANDOFF.md`
- `memory/sessions/session_64_mv17a_manuscript_claim_calibration.md`

## Generated Artifacts

Regenerate the calibrated paper/gate artifacts with:

```bash
python scripts/phase5_full_method_gate_audit.py
python scripts/build_diagnostic_paper_claim_tables.py
python scripts/build_diagnostic_paper_results_sections.py
python scripts/build_diagnostic_paper_bibliography.py
python scripts/build_diagnostic_paper_manuscript_draft.py
python scripts/phase5_consolidate_experiment_inventory.py
```

Tracked outputs are aggregate-only reports, claim tables, citation tables,
run summaries, traceability matrices, and hygiene audits under:

- `analysis/diagnostic_measurement_audit_paper/`
- `analysis/phase5_minimal_validation/full_method_gate_audit/`
- `analysis/phase5_minimal_validation/experiment_consolidation/`

## Blockers And Risks

- E-DAIC transcript CSVs still do not expose speaker roles, so MV17a fixes the
  language-encoder caveat but not interviewer/question contamination.
- MV06 still has one incomplete local CMDC candidate; stronger RQ4 wording
  requires resolving or explicitly bounding it.
- Bibliography rows now include the final SCD-MLLM Pattern Recognition DOI
  metadata, but full primary-source verification remains required before
  submission.
- Historical handoff superseded by session 65: MV20 criterion-overlap stress is
  complete and negative/bounded; do not run threshold variants or
  contamination-aware architecture work from this result.

## Next Handoff

Continue manuscript editing inside the target measurement-validity frame. This
handoff is superseded by session 66 for the PHQ psychometric boundary:
MV10/MV11/MV19 are now the primary PHQ measurement evidence, while MV13/MV14
are fixed-hyperparameter `mirt` qualitative screens until corrected or
explicitly limited. Use MV02/MV04c/MV06/MV09/MV12/MV15/MV16/MV17a/MV18 as
bounded support. Do not revive retired small-head or projection experiments
unless a new predeclared mechanism changes the full-method gate.
