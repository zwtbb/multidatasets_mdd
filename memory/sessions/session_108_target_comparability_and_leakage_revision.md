# Session Memory: target_comparability_and_leakage_revision

Status: complete
Last updated: 2026-09-04 UTC
Thread/task: main-agent response to target-validity scope, RQ2 finite-sample, local-independence, and leakage concerns

## Scope

This session owns the manuscript and bounded-experiment response to the latest
major concerns: target-validity scope, low-sample PHQ GRM/DIF inference,
theoretical local-independence wording, and criterion-contamination or
interviewer-leakage sensitivity. It does not revive MV27 or add a new
architecture-development line.

## Current State

- The concerns are judged valid. The paper should be framed as a
  cross-corpus score-comparability / target-contract audit, not as proof of
  PHQ/HAMD/SDS construct, criterion, or clinical validity.
- The title is now `Audit Target Comparability Before Aligning
  Representations: A Cross-Corpus Measurement Audit of Depression Detection`.
- Section 3.2 now treats $P_D(X|\theta)$ and $P_D(Y|\theta)$ as an analytical
  decomposition. The factorization $P_D(X,Y|\theta)=P_D(X|\theta)P_D(Y|\theta)$
  is explicitly a local-independence approximation, not a verified
  data-generating identity.
- RQ2 now cites GRM/MGRM sample-size literature and uses the multi-group GRM
  only as bounded confirmation. C02/C06 are hypothesis-generating localized
  threshold-shift candidates, not definitive item-level DIF discoveries.
- MV31 is complete. E-DAIC speaker-resolved controls remain blocked because
  neither the manifest nor transcript CSV files expose populated speaker roles.
  The Qwen3 repeated-turn prompt-proxy sensitivity reports no clear excess
  PHQ-8 severity loss from repeated-turn removal: full MAE 4.801,
  repeated-turn-only 4.806, repeated-turn-removed 4.577. Binary Macro-F1 is
  full 0.665, repeated-turn-only 0.576, repeated-turn-removed 0.614.
- MV20 remains the bounded CMDC criterion-overlap stress: high-overlap
  deletion is not clearly worse than matched random deletion under BGE-M3
  primary (excess MAE 0.150, 95 percent interval -0.320 to 0.671).
- The user Feishu wiki manuscript was synced with targeted block-level updates
  and verified at revision 235. The no-match scan covered the old
  target-validity, same-budget, five-seed, and target-pathway-superiority
  phrases; the positive scan confirmed the new target-comparability title,
  local-independence caveat, RQ2 sample-size caveat, leakage boundary, and
  target-calibrated Table 3 wording.

## Key Decisions

- Do not write `target validity` as the main manuscript identity unless it is
  locally defined as cross-corpus score interpretation/comparability. The safer
  paper identity is `target comparability` or `measurement-contract audit`.
- Do not write C02/C06 as confirmed DIF. The robust RQ2 conclusion is that
  exact observed-score interchangeability is unsupported.
- Do not claim absence of criterion contamination. Report the prompt-proxy and
  overlap-deletion checks as useful but incomplete stress tests.
- Do not claim strictly matched optimization exposure for calibrated
  baselines. The manuscript now says matched target-label budget and
  trainable shared-layer access under fixed, comparable schedules.

## Files Owned Or Touched

- `/root/autodl-tmp/analysis/diagnostic_measurement_audit_paper/manuscript_reframed_rq_draft.md`
- `/root/autodl-tmp/analysis/diagnostic_measurement_audit_paper/manuscript_reframed_rq_draft.docx`
- `/root/autodl-tmp/analysis/diagnostic_measurement_audit_paper/论文撰写_修订版.docx`
- `/root/autodl-tmp/scripts/phase5_run_mv31_qwen_prompt_proxy_sensitivity.py`
- `/root/autodl-tmp/scripts/build_diagnostic_paper_bibliography.py`
- `/root/autodl-tmp/scripts/build_diagnostic_paper_bibliography_verification.py`
- `/root/autodl-tmp/memory/ACTIVE_HANDOFF.md`
- `/root/autodl-tmp/MEMORY.md`

## Generated Artifacts

- MV31 report and run summary:
  `/root/autodl-tmp/analysis/phase5_minimal_validation/p5_mv31_qwen_prompt_proxy_sensitivity/`
- Regeneration command:
  `python scripts/phase5_run_mv31_qwen_prompt_proxy_sensitivity.py --device auto`
- Bibliography regenerated with:
  `python scripts/build_diagnostic_paper_bibliography.py`
- Bibliography verification regenerated with:
  `python scripts/build_diagnostic_paper_bibliography_verification.py`
- Word exports regenerated with:
  `pandoc --filter pandoc-citeproc --bibliography=analysis/diagnostic_measurement_audit_paper/references.bib analysis/diagnostic_measurement_audit_paper/manuscript_reframed_rq_draft.md -o analysis/diagnostic_measurement_audit_paper/manuscript_reframed_rq_draft.docx`

## Blockers And Risks

- True E-DAIC participant-only and interviewer-only transcript controls remain
  blocked without speaker-role labels or a new, validated speaker-segmentation
  source.
- The current PHQ GRM/DIF layer remains low-sample and should be treated as
  bounded measurement-audit evidence.

## Next Handoff

- Keep the local manuscript, Word exports, and Feishu revision 235 as the
  current formal paper sources.
- For future Feishu edits, fetch the document first and apply targeted
  block-level edits; do not whole-document overwrite.
- Next paper-side work should be ACM style/length polish and final
  current-prose citation coverage, not new model tuning.
