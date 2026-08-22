# Active Handoff

Last updated: 2026-08-22 UTC

This file is the short working-memory entrypoint for the main-agent thread.
It does not replace `MEMORY.md` or session memories. Read order for future
work should be:

1. `MEMORY.md`
2. This file
3. Only the task-relevant session memory files listed below
4. Source artifacts cited by the task

Do not copy long metric tables here. Generated reports and run summaries remain
the numeric source of truth.

## Current Objective

Act as the main orchestration agent for the cross-scale depression modeling
project: manage experiment planning, progress, issue logging, versioning, and
subtasks until the project reaches bounded publishable results.

The paper direction is now target measurement validity, not a positive full
shared-symptom model or generic robust multimodal model. Full M0/M1/M2/M3
method construction remains blocked by the Phase 5 full-method gate.

## Current Gate

- Active gate source:
  `/root/autodl-tmp/analysis/phase5_minimal_validation/full_method_gate_audit/`
- Gate status: `blocked_but_publishable_diagnostic_direction`
- `full_method_allowed=false`
- Use the gate as the claim boundary before drafting, adding experiments, or
  making public-facing claims.

Allowed current framing:

- Label-only PHQ measurement evidence: substantial common structure and
  repeated C02/C06 threshold-shift signals, with MV19 finite-sample downgrade
  at the observed E-DAIC/CMDC N.
- Dataset/protocol/population identity evidence as diagnostic shortcut risk.
- Negative or bounded multimodal results under the legacy BGE/lightweight-head
  contract, now supported by MV17a multilingual feature-contract sensitivity
  for the MV07/MV12/MV15 chain.
- First-round aggregate evidence-localization credibility from MV06, with
  sampling and one-candidate incompleteness caveats.

Blocked claims:

- Full M0/M1/M2/M3 construction.
- Transferable shared-symptom representation from current BGE/WavLM contracts.
- Positive feature-invariance claims from current MV07/MV12/MV15/MV16
  BGE-linked evidence; MV17a reproduces the blocked pattern under multilingual
  encoders rather than authorizing the claim.
- Positive EATD SDS generalization.
- Valence-adversarial method from current EATD evidence.
- Naive personality/context conditioning as a supported RQ3 method.
- Strong RQ4 evidence-localization claims until the remaining MV06 candidate is
  resolved or explicitly bounded.

## Active Next Task

Main next task:

- Continue manuscript review after the MV17a claim calibration: C02/C06 are
  repeated but finite-sample-bounded dataset-group threshold-shift signals, not
  robust standalone DIF, and MV17a makes BGE-M3 the primary feature-contract
  consequence layer with multilingual-E5 as encoder sensitivity.
- Use the active evidence bundle at
  `/root/autodl-tmp/analysis/phase5_minimal_validation/experiment_consolidation/`
  as the default Phase 5 experiment index. Do not revive retired historical MV
  rows unless a new mechanism-changing contract is written.
- Decide whether MV20 criterion-contamination stress is still needed after the
  MV17a-calibrated manuscript pass; if run, predeclare it narrowly before
  touching raw interview/question content.
- Do not rerun MV16 unless the multilingual MV17a results are explicitly
  reviewed and a new need is identified.
- Continue manuscript editing only within the target-measurement-validity frame.

Useful inputs:

- `/root/autodl-tmp/analysis/diagnostic_measurement_audit_paper/references.bib`
- `/root/autodl-tmp/analysis/diagnostic_measurement_audit_paper/citation_registry.csv`
- `/root/autodl-tmp/analysis/diagnostic_measurement_audit_paper/citation_source_map.csv`
- `/root/autodl-tmp/analysis/diagnostic_measurement_audit_paper/manuscript_traceability_matrix.csv`
- `/root/autodl-tmp/analysis/diagnostic_measurement_audit_paper/manuscript_open_items.csv`
- `/root/autodl-tmp/analysis/phase5_minimal_validation/p5_mv17a_multilingual_feature_contract/`
- `/root/autodl-tmp/analysis/phase5_minimal_validation/p5_mv17_postreview_measurement_validity_route/`
- `/root/autodl-tmp/analysis/phase5_minimal_validation/p5_mv18_cmdc_pdch_hamd_same_scale_control/`
- `/root/autodl-tmp/analysis/phase5_minimal_validation/p5_mv19_phq_finite_sample_psychometric_simulation/`
- `/root/autodl-tmp/analysis/phase5_minimal_validation/experiment_consolidation/`
- `/root/autodl-tmp/memory/sessions/session_56_diagnostic_manuscript_draft.md`
- `/root/autodl-tmp/memory/sessions/session_57_diagnostic_bibliography_handoff.md`
- `/root/autodl-tmp/memory/sessions/session_59_postreview_measurement_validity_triage.md`
- `/root/autodl-tmp/memory/sessions/session_60_mv17a_multilingual_feature_contract.md`
- `/root/autodl-tmp/memory/sessions/session_61_mv18_cmdc_pdch_hamd_same_scale_control.md`
- `/root/autodl-tmp/memory/sessions/session_62_mv19_phq_finite_sample_simulation.md`
- `/root/autodl-tmp/memory/sessions/session_63_experiment_consolidation_cleanup.md`
- `/root/autodl-tmp/memory/sessions/session_64_mv17a_manuscript_claim_calibration.md`

Secondary optional task:

- Resolve the one incomplete local CMDC MV06 candidate if the missing workbook
  rows become available, then rerun the aggregate MV06 summary gate.
- MV20 criterion-contamination stress remains optional after manuscript review,
  only if still needed for protocol-label overlap support.

## Critical Current Results

- MV06 aggregate agreement is ready for bounded evidence review:
  143 completed candidates and 143 double-annotated candidates out of 144.
  Evidence-presence kappa is `0.965` overall, `0.967` CMDC, `0.846` E-DAIC,
  and `1.000` PDCH. Bootstrap 95 percent CIs are `0.922-1.000` overall,
  `0.885-1.000` CMDC, `0.595-1.000` E-DAIC, and `1.000-1.000` PDCH.
- MV10/MV11/MV13/MV14 support item-level PHQ measurement-shift wording:
  anchors `C01/C04/C05/C07`, threshold DIF concentrated on `C02/C06`, sparse
  loading DIF, and uncertain global model selection.
- MV12 is frozen as bounded legacy diagnostic evidence from the old
  Chinese-BGE chain. Same-dataset theta utility improves, but observed-scale
  safety and old-chain source-calibrated external theta transfer fail; the B3
  direct itemwise Ridge comparison remains a dimension-matched severity-control
  caveat, not the canonical MV17a feature-contract conclusion.
- MV15 blocks theta-specific BGE feature-invariance wording: raw, total,
  predicted-total, B3, and theta-conditioned feature identity BA all remain
  `1.000`.
- MV16 is bounded/negative calibration evidence:
  `blocked_no_dif_guided_small_k_gain`. The best supported row is
  E-DAIC to CMDC, `M16d_global_plus_C02_C06`, k=`10`, but the both-direction
  small-k DIF-guided mechanism gate fails and output identity remains high.
- MV17a multilingual feature-contract sensitivity is complete and now owns the
  canonical prediction-consequence wording. BGE-M3 is the primary feature
  contract and multilingual-E5 is the sensitivity encoder. Both reproduce the
  blocked MV07/MV12/MV15 gate pattern; both pass same-dataset theta utility,
  fail observed-scale safety, and keep theta-conditioned feature identity BA at
  `1.000`. External theta transfer is encoder-dependent: BGE-M3 passes and
  multilingual-E5 fails. B3 Pareto dominance is also encoder-dependent: false
  for BGE-M3, true for multilingual-E5. The stable claim is lower output-level
  identity without observed-scale-safe or feature-invariant cross-corpus
  prediction.
- MV18 CMDC-HAMD vs PDCH-HAMD same-scale exploratory control is complete. It
  uses 25 CMDC HAMD subjects and 99 PDCH HAMD subjects, with 25 CMDC and 73
  PDCH subjects in the mild/moderate overlap. In that overlap it flags 4
  severity-conditioned residual item shifts (`HAMD08`, `HAMD11`, `HAMD04`,
  `HAMD09`), 7 threshold shifts, and weak primary bidirectional transfer under
  the current frozen-feature contract. Status:
  `complete_exploratory_same_scale_context_shift_supported`; interpretation is
  exploratory context-shift support, not formal HAMD invariance.
- MV19 finite-sample PHQ psychometric simulation is complete. It uses 500
  simulations per world under observed E-DAIC/CMDC PHQ N and severity
  distributions. Status:
  `complete_mv19_high_false_localization_downgrade_c02_c06`. H0 C02/C06
  both-flag false rate is `0.208`; H0 top-two false-localization is `0.034`;
  H1 C02/C06 both-flag recovery is `0.662`; H1 top-two recovery is `0.222`;
  H1 anchor subset recovery is `0.178`. Treat this as a finite-sample
  downgrade: C02/C06 are repeated localized dataset-group threshold-shift
  signals, not robust standalone DIF at the observed N.
- Experiment consolidation is complete. The active paper bundle has 15 rows:
  5 paper-core PHQ psychometric rows (`MV10/MV11/MV13/MV14/MV19`) and 10
  support rows (`MV02/MV04c/MV06/MV09/MV12/MV15/MV16/MV17a/MV18`). Twenty-eight
  earlier rows are retained only as retired historical diagnostics,
  predeclaration contracts, or local workflow boundaries. Tracked aggregate
  outputs should not be physically deleted by default.

## Versioning State

- Use `/root/autodl-tmp/scripts/publish_clean_github_snapshot.py` for GitHub
  updates.
- Do not push the old local `main` history directly.
- Current local working branch: `codex/mv19-phq-finite-sample`.
- MV19 experiment-content local commit: `6def05240bbd5e5d068e8b1bca8bb9eb738f08f2`
  (`Run MV19 finite-sample PHQ simulation`).
- MV19 experiment-content clean remote `main` publish:
  `ab54aabab7b3b29fb157667892a7157639be980e`.
- A later version-state-only bookkeeping commit may exist after this MV19
  content publish; it should not change experiment artifacts.
- GitHub authentication should use token or `gh` auth. Never write or use
  plaintext passwords in Git, scripts, memory, shell history, or logs.
- Current cleanup policy: interpreter/notebook caches may be deleted without
  further approval; deleting local predictions, features, Phase 2 outputs,
  MV06 workbooks, raw datasets, environment caches, or the local original-plan
  note requires a separate user-approved storage cleanup.

Track:

- Code, configs, docs, schemas/examples, memory files, lightweight aggregate
  reports, paper-critical summaries.

Keep local-only:

- Raw datasets, clinical text, local workbooks with subject rows or locators,
  row-level manifests, splits, integrity tables, prompts/responses, features,
  embeddings, predictions, bootstrap draws, fitted parameters, theta scores,
  model objects, weights, caches, media, archives, and generated Phase 2 result
  artifacts.

## Issue Pointers

- Main issue log:
  `/root/autodl-tmp/docs/experiment_issue_log.md`
- Most relevant open issues now:
  - I040: public Git history row-level-data caveat. Latest-tree mitigation is
    complete; remote history rewrite/recreation is optional and requires
    explicit approval.
  - I057: MV06 one incomplete CMDC candidate. Bound RQ4 unless resolved.
  - I059: optional larger corrected MV14 bootstrap only if reviewer-facing
    interval precision becomes necessary.
  - I062: manuscript editing and citation-key insertion continue as paper-side
    work after the post-review frame correction.
  - I064: bibliography metadata must be verified against primary sources before
    submission.
  - I066: MV17a, MV18, and MV19 are complete; next work is MV17a-calibrated
    manuscript review and citation verification, then optional MV20 only if
    still needed.
  - I070: MV17a manuscript claim calibration is complete; keep old
    Chinese-BGE MV12/MV15/MV16 outputs legacy/supporting and keep external
    theta transfer plus B3 dominance encoder-dependent.

## Fast Verification Commands

```bash
git status --short
python scripts/build_diagnostic_paper_bibliography.py
python scripts/phase5_run_mv17a_multilingual_feature_contract.py
python scripts/phase5_run_mv18_cmdc_pdch_hamd_same_scale_control.py
python scripts/phase5_run_mv19_phq_finite_sample_simulation.py
python scripts/phase5_consolidate_experiment_inventory.py
python scripts/build_diagnostic_paper_manuscript_draft.py
python scripts/phase5_full_method_gate_audit.py
```
