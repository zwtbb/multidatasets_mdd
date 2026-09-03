# Session Memory: target_validity_audit_revision

Status: complete
Last updated: 2026-09-03 UTC
Thread/task: main-agent manuscript revision after target-only reviewer critique

## Scope

This session owns the manuscript-level response to the review that requested a
full shift from method-superiority framing to target-validity audit framing. It
does not create new experiments; it integrates completed MV28/MV29/MV30
evidence into the formal manuscript and bibliography artifacts.

## Current State

- The main manuscript title is now `Validate the Target Before Aligning
  Representations: A Target-Validity Audit of Cross-Corpus Depression
  Detection`.
- Abstract, Contribution 3, Section 3 heading, Methods, Results, Discussion,
  Scope, and Conclusion now state that target calibration and shared-layer
  adaptation are the robust empirical effects.
- The main RQ3 Table 3 now uses repeated subject-level target-calibration
  splits, with target-only direct/ordinal, source warm-start target fine-tune,
  source+target direct multitask, generic target MLP head, shared ordinal head,
  and measurement-aware ordinal rows. Zero-target-label and old fixed-split
  rows are supplementary context.
- Calibration-in-the-large and calibration slope are defined in Methods as the
  main calibration audit quantities; binned calibration MAE is now a secondary
  calibration-curve summary.
- RQ2 terminology now calls the Cronbach/eigen/loading/congruence layer a
  structural compatibility screen. Formal configural/metric/scalar terminology
  is reserved for the multi-group graded-response ladder.
- C02/C06 are now described as recurrent threshold-shift candidates with
  finite-sample uncertainty, not stable threshold-shift signals.
- RQ1 wording now says length-associated directions account for most linear
  E-DAIC/CMDC separability, while nonlinear Qwen3 probing still recovers
  substantial residual corpus information.

## Key Decisions

- Treat the paper identity as a target-validity audit / benchmark-validity
  contribution rather than a SOTA-style architecture paper.
- Do not claim corpus-specific ordinal heads independently improve the main
  real-data results. Shared ordinal and corpus-specific ordinal heads are near
  tied overall and on the C02/C06 targeted item set.
- Do not use five-seed fixed-split p-values or the compact
  reconstruction-plus-calibration score as main superiority evidence. Use the
  repeated-split tables and participant-bootstrap paired deltas for calibrated
  architecture claims.
- Keep MV27 out of the main paper, per the user's current decision.

## Files Owned Or Touched

- `/root/autodl-tmp/analysis/diagnostic_measurement_audit_paper/manuscript_reframed_rq_draft.md`
- `/root/autodl-tmp/analysis/diagnostic_measurement_audit_paper/manuscript_reframed_rq_draft.docx`
- `/root/autodl-tmp/analysis/diagnostic_measurement_audit_paper/论文撰写_修订版.docx`
- `/root/autodl-tmp/scripts/build_diagnostic_paper_bibliography.py`
- `/root/autodl-tmp/scripts/build_diagnostic_paper_bibliography_verification.py`
- Generated bibliography artifacts under
  `/root/autodl-tmp/analysis/diagnostic_measurement_audit_paper/`

## Generated Artifacts

- Regenerated BibTeX, citation registry, bibliography reports, and verification
  ledger with `python scripts/build_diagnostic_paper_bibliography.py` and
  `python scripts/build_diagnostic_paper_bibliography_verification.py`.
- Regenerated Word draft with:
  `pandoc --filter pandoc-citeproc --bibliography=analysis/diagnostic_measurement_audit_paper/references.bib analysis/diagnostic_measurement_audit_paper/manuscript_reframed_rq_draft.md -o analysis/diagnostic_measurement_audit_paper/manuscript_reframed_rq_draft.docx`

## Blockers And Risks

- The local manuscript is updated, but Feishu sync has not been performed in
  this session.
- The main remaining writing risk is tone discipline: future edits must not
  drift back to claiming that corpus-specific measurement heads drive the main
  improvement.

## Next Handoff

- Review the revised main manuscript for ACM length/style and human readability.
- If the user wants Feishu updated, fetch the target document first and apply
  targeted block-level updates rather than whole-document overwrite.
- Prepare the next reviewer-response pass around participant-level uncertainty
  and final table/figure placement if requested.
