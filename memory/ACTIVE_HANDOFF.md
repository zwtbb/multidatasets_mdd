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

The paper direction is now measurement shift / measurement validity, not a
positive full shared-symptom model. Full M0/M1/M2/M3 method construction remains
blocked by the Phase 5 full-method gate.

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
- Negative or bounded multimodal results under the frozen BGE/lightweight-head
  contract.
- First-round aggregate evidence-localization credibility from MV06, with
  sampling and one-candidate incompleteness caveats.

Blocked claims:

- Full M0/M1/M2/M3 construction.
- Transferable shared-symptom representation from current BGE/WavLM contracts.
- Positive EATD SDS generalization.
- Valence-adversarial method from current EATD evidence.
- Naive personality/context conditioning as a supported RQ3 method.
- Strong RQ4 evidence-localization claims until the remaining MV06 candidate is
  resolved or explicitly bounded.

## Active Next Task

Main next task:

- Insert generated citation keys into
  `/root/autodl-tmp/analysis/diagnostic_measurement_audit_paper/manuscript_draft.md`.
- Adapt references to the selected or provisional venue style.
- Continue human manuscript editing while preserving the full-method claim
  boundary.

Useful inputs:

- `/root/autodl-tmp/analysis/diagnostic_measurement_audit_paper/references.bib`
- `/root/autodl-tmp/analysis/diagnostic_measurement_audit_paper/citation_registry.csv`
- `/root/autodl-tmp/analysis/diagnostic_measurement_audit_paper/citation_source_map.csv`
- `/root/autodl-tmp/analysis/diagnostic_measurement_audit_paper/manuscript_traceability_matrix.csv`
- `/root/autodl-tmp/analysis/diagnostic_measurement_audit_paper/manuscript_open_items.csv`
- `/root/autodl-tmp/memory/sessions/session_56_diagnostic_manuscript_draft.md`
- `/root/autodl-tmp/memory/sessions/session_57_diagnostic_bibliography_handoff.md`

Secondary optional task:

- Resolve the one incomplete local CMDC MV06 candidate if the missing workbook
  rows become available, then rerun the aggregate MV06 summary gate.

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

## Versioning State

- Use `/root/autodl-tmp/scripts/publish_clean_github_snapshot.py` for GitHub
  updates.
- Do not push the old local `main` history directly.
- Latest known local commit before this handoff: `78567d2`
  (`Add diagnostic paper bibliography`).
- Latest known clean remote `main` before this handoff:
  `5ce777c2570250b2e743faf29c4147852b664d65`.
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
  - I062: manuscript editing and citation-key insertion are active.

## Fast Verification Commands

```bash
git status --short
python scripts/build_diagnostic_paper_bibliography.py
python scripts/build_diagnostic_paper_manuscript_draft.py
python scripts/phase5_full_method_gate_audit.py
```

