# Active Handoff

Last updated: 2026-08-21 UTC

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

- Label-only PHQ measurement evidence: substantial common structure, stable
  anchors, sparse loading DIF, localized threshold non-equivalence.
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

- Predeclare and run MV18 CMDC-HAMD vs PDCH-HAMD same-scale exploratory
  control. The goal is to separate scale/measurement differences from
  dataset/protocol/population differences under a same HAMD-17 target family.
- After MV18, run MV19 finite-sample PHQ psychometric simulation if the
  manuscript still needs a small-sample uncertainty support layer.
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
- `/root/autodl-tmp/memory/sessions/session_56_diagnostic_manuscript_draft.md`
- `/root/autodl-tmp/memory/sessions/session_57_diagnostic_bibliography_handoff.md`
- `/root/autodl-tmp/memory/sessions/session_59_postreview_measurement_validity_triage.md`
- `/root/autodl-tmp/memory/sessions/session_60_mv17a_multilingual_feature_contract.md`

Secondary optional task:

- Resolve the one incomplete local CMDC MV06 candidate if the missing workbook
  rows become available, then rerun the aggregate MV06 summary gate.
- MV20 criterion-contamination stress remains optional after MV18/MV19, only if
  still needed for the manuscript.

## Critical Current Results

- MV06 aggregate agreement is ready for bounded evidence review:
  143 completed candidates and 143 double-annotated candidates out of 144.
  Evidence-presence kappa is `0.965` overall, `0.967` CMDC, `0.846` E-DAIC,
  and `1.000` PDCH. Bootstrap 95 percent CIs are `0.922-1.000` overall,
  `0.885-1.000` CMDC, `0.595-1.000` E-DAIC, and `1.000-1.000` PDCH.
- MV10/MV11/MV13/MV14 support item-level PHQ measurement-shift wording:
  anchors `C01/C04/C05/C07`, threshold DIF concentrated on `C02/C06`, sparse
  loading DIF, and uncertain global model selection.
- MV12 is frozen as bounded diagnostic evidence. Same-dataset theta utility
  improves, but observed-scale safety and zero-shot external theta transfer
  fail. B3 direct itemwise Ridge compressed to theta Pareto-dominates M12a on
  pooled observed macro MAE and conditional identity.
- MV15 blocks theta-specific BGE feature-invariance wording: raw, total,
  predicted-total, B3, and theta-conditioned feature identity BA all remain
  `1.000`.
- MV16 is bounded/negative calibration evidence:
  `blocked_no_dif_guided_small_k_gain`. The best supported row is
  E-DAIC to CMDC, `M16d_global_plus_C02_C06`, k=`10`, but the both-direction
  small-k DIF-guided mechanism gate fails and output identity remains high.
- MV17a multilingual feature-contract sensitivity is complete. BGE-M3 and
  multilingual-E5 both reproduce the blocked feature-level pattern over
  MV07/MV12/MV15: MV07 remains
  `blocked_not_better_than_total_allocation_bge_contract`, MV12 remains
  `blocked_theta_gain_not_observed_scale_safe`, and MV15 remains
  `blocked_theta_conditioned_feature_identity_high`. Feature identity BA is
  `1.000` for both encoders; MV15 theta-conditioned feature identity BA is also
  `1.000` for both. The old Chinese-BGE chain remains legacy/diagnostic, but
  the core negative feature-level conclusion now has multilingual sensitivity
  support. MV10/MV11/MV13/MV14 are label-only and unaffected.

## Versioning State

- Use `/root/autodl-tmp/scripts/publish_clean_github_snapshot.py` for GitHub
  updates.
- Do not push the old local `main` history directly.
- Latest known local commit before this handoff: `0ea684f`
  (`Add active context handoff`).
- Latest known clean remote `main` before this handoff:
  `7b789c6951caf5fd7ef54479f8ab2ba24f8e1f16`.
- GitHub authentication should use token or `gh` auth. Never write or use
  plaintext passwords in Git, scripts, memory, shell history, or logs.

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
  - I066: next bounded experiments are MV18, MV19, then optional MV20.

## Fast Verification Commands

```bash
git status --short
python scripts/build_diagnostic_paper_bibliography.py
python scripts/phase5_run_mv17a_multilingual_feature_contract.py
python scripts/build_diagnostic_paper_manuscript_draft.py
python scripts/phase5_full_method_gate_audit.py
```
