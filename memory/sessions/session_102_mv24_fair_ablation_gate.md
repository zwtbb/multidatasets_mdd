# Session Memory: MV24 Fair Shared-Layer Calibrated Ablation Gate

Status: complete
Last updated: 2026-09-02 UTC
Thread/task: main-agent continuation after reviewer major concern on Table 3

## Scope

This session owns the reviewer-facing fairness concern that the original MV24
target-calibrated Table 3 could not identify the contribution of the
measurement-aware target pathway. It should not reopen broad full-method
M0/M1/M2/M3 construction, tune new thresholds, or add speculative architecture
variants beyond the requested fair calibrated baselines.

## Current State

MV24 now includes four fair target-calibrated baselines in addition to the
legacy frozen corpus-specific-head row: direct target fine-tuning, direct
source+target multitask, shared ordinal head joint adaptation, and generic
target MLP head. All use the official frozen Qwen3+WavLM+OpenFace subject
representation, the same target calibration split, five seeds, and no target
evaluation labels.

The fair shared-layer calibrated ablation gate is
`not_passed_uniform_measurement_pathway_superiority`. The core
measurement-aware model passes only 2 of 8 fair shared-layer comparisons on the
paired compact reconstruction-plus-calibration score at one-sided p<0.05. In
CMDC-to-E-DAIC it significantly beats direct target fine-tuning and generic
target MLP, trends against direct source+target multitask, and ties the shared
ordinal head. In E-DAIC-to-CMDC, direct target fine-tuning and direct
source+target multitask match or slightly beat measurement-aware, while shared
ordinal head and generic target MLP are effectively tied/nearby.

## Key Decisions

- The old large improvement over `corpus_specific_head` is no longer written as
  evidence that measurement-aware target modeling caused the gain, because that
  baseline freezes the source-trained shared symptom layer.
- The robust manuscript claim is target calibration/shared-layer adaptation
  matters under the official frozen foundation representation.
- The corpus-specific cumulative-logit ordinal pathway remains a principled,
  competitive, direction-dependent target-contract mechanism, but not a
  uniformly superior architecture under the current evidence.
- MMD remains an auxiliary variant with a nearly flat sensitivity profile.

## Files Owned Or Touched

- `/root/autodl-tmp/scripts/phase5_run_mv24_measurement_aware_ordinal_model.py`
- `/root/autodl-tmp/analysis/phase5_minimal_validation/p5_mv24_measurement_aware_ordinal_model/run_summary.json`
- `/root/autodl-tmp/analysis/phase5_minimal_validation/p5_mv24_measurement_aware_ordinal_model/report.md`
- `/root/autodl-tmp/analysis/phase5_minimal_validation/p5_mv24_measurement_aware_ordinal_model/architecture_contract.json`
- `/root/autodl-tmp/analysis/phase5_minimal_validation/p5_mv24_measurement_aware_ordinal_model/architecture_contract.md`
- `/root/autodl-tmp/analysis/phase5_minimal_validation/p5_mv24_measurement_aware_ordinal_model/main_result_table.md`
- `/root/autodl-tmp/analysis/phase5_minimal_validation/p5_mv24_measurement_aware_ordinal_model/target_calibrated_result_table.md`
- `/root/autodl-tmp/analysis/diagnostic_measurement_audit_paper/manuscript_reframed_rq_draft.md`
- `/root/autodl-tmp/analysis/diagnostic_measurement_audit_paper/manuscript_reframed_rq_draft.docx`
- `/root/autodl-tmp/analysis/diagnostic_measurement_audit_paper/论文撰写_修订版.docx`
- `/root/autodl-tmp/analysis/diagnostic_measurement_audit_paper/foundation_backbone_measurement_aware_validation_contract.md`
- `/root/autodl-tmp/README.md`
- `/root/autodl-tmp/docs/experiment_issue_log.md`
- `/root/autodl-tmp/MEMORY.md`
- `/root/autodl-tmp/memory/ACTIVE_HANDOFF.md`

## Generated Artifacts

Primary numeric source of truth:

- `/root/autodl-tmp/analysis/phase5_minimal_validation/p5_mv24_measurement_aware_ordinal_model/metrics_by_seed.csv`
- `/root/autodl-tmp/analysis/phase5_minimal_validation/p5_mv24_measurement_aware_ordinal_model/summary_by_method.csv`
- `/root/autodl-tmp/analysis/phase5_minimal_validation/p5_mv24_measurement_aware_ordinal_model/paired_significance.csv`
- `/root/autodl-tmp/analysis/phase5_minimal_validation/p5_mv24_measurement_aware_ordinal_model/run_summary.json`

Full rerun command already completed before this memory write:

```bash
python scripts/phase5_run_mv24_measurement_aware_ordinal_model.py --clean
```

Post-run report/contract refresh used existing aggregate CSVs and did not
retrain models.

Word exports regenerated from the current Markdown source:

```bash
pandoc --filter pandoc-citeproc --bibliography=analysis/diagnostic_measurement_audit_paper/references.bib analysis/diagnostic_measurement_audit_paper/manuscript_reframed_rq_draft.md -o analysis/diagnostic_measurement_audit_paper/manuscript_reframed_rq_draft.docx
pandoc --filter pandoc-citeproc --bibliography=analysis/diagnostic_measurement_audit_paper/references.bib analysis/diagnostic_measurement_audit_paper/manuscript_reframed_rq_draft.md -o analysis/diagnostic_measurement_audit_paper/论文撰写_修订版.docx
```

## Blockers And Risks

- Table 3 no longer supports the strong statement that target-side measurement
  modeling has empirical value beyond target-supervised representation
  adaptation in both directions.
- The E-DAIC-to-CMDC target-calibrated evaluation set is small (20 held-out
  CMDC subjects), so use the result as a claim-boundary/fairness stress test,
  not as a new broad negative theorem.
- Feishu has not yet been synced for this specific fair-ablation revision.
  The latest verified Feishu sync before this session was revision 211.

## Next Handoff

Use the current local Markdown and Word files as the formal source for the next
review concern. If syncing Feishu, update only the Abstract contribution,
Section 5.3, Section 6.3 Table 3 and interpretation paragraphs, Discussion,
Scope, and Conclusion blocks touched by this fair-ablation revision.
