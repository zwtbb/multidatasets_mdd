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

- Label-only MV10/MV11/MV19 PHQ measurement evidence: substantial common
  structure and repeated C02/C06 threshold-shift signals, with MV19
  finite-sample downgrade at the observed E-DAIC/CMDC N.
- MV13/MV14 external `mirt` outputs only as fixed-hyperparameter qualitative
  screens until the focal latent mean/variance parameterization is corrected
  and rerun, or the manuscript explicitly limits them.
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
- Final anchor-linked `mirt` DIF or bootstrap-stability claims from MV13/MV14
  until the focal latent mean/variance issue is resolved.
- Positive EATD SDS generalization.
- Valence-adversarial method from current EATD evidence.
- Naive personality/context conditioning as a supported RQ3 method.
- Strong RQ4 evidence-localization claims until the remaining MV06 candidate is
  resolved or explicitly bounded.

## Active Next Task

Main next task:

- Resolve the MV13/MV14 `mirt` parameterization blocker before submission:
  either correct/rerun the anchor-linked focal mean/variance specification, or
  explicitly limit manuscript wording to the current fixed-hyperparameter
  qualitative screen.
- Then finalize manuscript review after the MV17a/MV18/MV19/MV20 completion
  line:
  C02/C06 are repeated but finite-sample-bounded dataset-group threshold-shift
  signals, not robust standalone DIF; MV17a makes BGE-M3 the primary
  feature-contract consequence layer with multilingual-E5 as encoder
  sensitivity; MV20 is a bounded negative CMDC-only criterion-overlap stress
  test.
- Use the active evidence bundle at
  `/root/autodl-tmp/analysis/phase5_minimal_validation/experiment_consolidation/`
  as the default Phase 5 experiment index. Do not revive retired historical MV
  rows unless a new mechanism-changing contract is written.
- Experiments are frozen after MV20. Do not tune criterion-overlap thresholds,
  add insertion variants, or design contamination-aware architectures from the
  negative MV20 result.
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
- `/root/autodl-tmp/analysis/phase5_minimal_validation/p5_mv20_criterion_overlap_stress/`
- `/root/autodl-tmp/analysis/phase5_minimal_validation/p5_mirt_parameterization_correctness_audit/`
- `/root/autodl-tmp/analysis/phase5_minimal_validation/experiment_consolidation/`
- `/root/autodl-tmp/memory/sessions/session_56_diagnostic_manuscript_draft.md`
- `/root/autodl-tmp/memory/sessions/session_57_diagnostic_bibliography_handoff.md`
- `/root/autodl-tmp/memory/sessions/session_59_postreview_measurement_validity_triage.md`
- `/root/autodl-tmp/memory/sessions/session_60_mv17a_multilingual_feature_contract.md`
- `/root/autodl-tmp/memory/sessions/session_61_mv18_cmdc_pdch_hamd_same_scale_control.md`
- `/root/autodl-tmp/memory/sessions/session_62_mv19_phq_finite_sample_simulation.md`
- `/root/autodl-tmp/memory/sessions/session_63_experiment_consolidation_cleanup.md`
- `/root/autodl-tmp/memory/sessions/session_64_mv17a_manuscript_claim_calibration.md`
- `/root/autodl-tmp/memory/sessions/session_65_mv20_criterion_overlap_stress.md`
- `/root/autodl-tmp/memory/sessions/session_66_mirt_parameterization_correctness_audit.md`

Secondary optional task:

- Resolve the one incomplete local CMDC MV06 candidate if the missing workbook
  rows become available, then rerun the aggregate MV06 summary gate.
- MV20 is complete; no further protocol-label-overlap stress variants should be
  run unless a genuinely new design contract changes the gate.

## Critical Current Results

- MV06 aggregate agreement is ready for bounded evidence review:
  143 completed candidates and 143 double-annotated candidates out of 144.
  Evidence-presence kappa is `0.965` overall, `0.967` CMDC, `0.846` E-DAIC,
  and `1.000` PDCH. Bootstrap 95 percent CIs are `0.922-1.000` overall,
  `0.885-1.000` CMDC, `0.595-1.000` E-DAIC, and `1.000-1.000` PDCH.
- MV10/MV11/MV19 are the primary item-level PHQ measurement-shift evidence:
  anchors `C01/C04/C05/C07`, threshold DIF concentrated on `C02/C06`, sparse
  loading DIF, uncertain global model selection, and observed-N finite-sample
  downgrade.
- MV13/MV14 `mirt` outputs are fixed-hyperparameter qualitative screens only.
  Code-level audit passes reference/focal group order, anchor linking, and
  graded `d1-d3` threshold/intercept constraints, but fails focal latent
  mean/variance handling because the actual `multipleGroup` calls omit the
  `invariance` argument that would free CMDC mean/variance under anchor
  linking. Status: `complete_mirt_parameterization_mismatch`.
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
- MV20 criterion-overlap stress is complete. It used CMDC because Q1-Q12
  question-position units are available; PDCH was excluded because available
  units are coarse consultation segments; E-DAIC was excluded because true
  prompt/speaker units are unavailable. BGE-M3 primary CMDC PHQ-9 top-20
  all/minus-high/minus-random/high-only MAE is `3.571`/`3.918`/`3.768`/`4.215`;
  criterion excess loss versus matched random is `0.150`, 95 percent CI
  `-0.320` to `0.671`, and the gate status is
  `no_excess_criterion_overlap_evidence`. Multilingual-E5 sensitivity has the
  same no-excess gate. Treat MV20 as a bounded negative stress test and stop
  overlap-threshold tuning or contamination-aware model work.
- Experiment consolidation is complete. The active paper bundle has 17 rows:
  5 paper-core PHQ rows (`MV10/MV11/MV19` primary plus `MV13/MV14` limited
  `mirt` screens), 11 support rows
  (`MV02/MV04c/MV06/MV09/MV12/MV15/MV16/MV17a/MV18/MV20`), and 1 paper
  guardrail (`P5_mirt_parameterization_audit`). Twenty-eight earlier rows are
  retained only as retired historical diagnostics, predeclaration contracts,
  or local workflow boundaries. Tracked aggregate outputs should not be
  physically deleted by default.

## Versioning State

- Use `/root/autodl-tmp/scripts/publish_clean_github_snapshot.py` for GitHub
  updates.
- Do not push the old local `main` history directly.
- Current local working branch: `codex/mv19-phq-finite-sample`; current HEAD
  is the MV13/MV14 `mirt` parameterization audit and claim-boundary snapshot.
- MV19 experiment-content local commit: `6def05240bbd5e5d068e8b1bca8bb9eb738f08f2`
  (`Run MV19 finite-sample PHQ simulation`).
- MV19 experiment-content clean remote `main` publish:
  `ab54aabab7b3b29fb157667892a7157639be980e`.
- The next clean remote publish should use
  `/root/autodl-tmp/scripts/publish_clean_github_snapshot.py` from the current
  committed source tree rather than pushing this old local branch history.
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
  - I066: closed after MV17a, MV18, MV19, and MV20 completed the post-review
    bounded experiment line; experiments are frozen.
  - I070: MV17a manuscript claim calibration is complete; keep old
    Chinese-BGE MV12/MV15/MV16 outputs legacy/supporting and keep external
    theta transfer plus B3 dominance encoder-dependent.
  - I071: closed by MV20 criterion-overlap stress; no clear high-overlap excess
    over matched random deletion under BGE-M3 primary or multilingual-E5
    sensitivity.
  - I072: open MV13/MV14 `mirt` parameterization blocker. Current outputs fix
    CMDC latent mean/variance in the actual calls; resolve by corrected rerun
    or explicit manuscript limitation before submission.

## Fast Verification Commands

```bash
git status --short
python scripts/phase5_audit_mirt_parameterization_contract.py
python scripts/build_diagnostic_paper_bibliography.py
python scripts/phase5_run_mv17a_multilingual_feature_contract.py
python scripts/phase5_run_mv18_cmdc_pdch_hamd_same_scale_control.py
python scripts/phase5_run_mv19_phq_finite_sample_simulation.py
python scripts/phase5_run_mv20_criterion_overlap_stress.py
python scripts/phase5_consolidate_experiment_inventory.py
python scripts/build_diagnostic_paper_manuscript_draft.py
python scripts/phase5_full_method_gate_audit.py
```
