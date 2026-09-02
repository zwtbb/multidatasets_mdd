# Session Memory: manuscript_mmd_core_and_claim_tone

Status: complete
Last updated: 2026-08-30 UTC
Thread/task: main paper precision polishing

## Scope

This session owns the manuscript-level response to the user's critique that the
formal model should not bind MMD into the default "full" method and that the
paper had too much defensive or clinical-safety language. It does not own new
experiments, MV27 inclusion decisions, or Git publishing.

## Current State

The current manuscript now defines `Measurement-aware` as the core method:
frozen Qwen3+WavLM+OpenFace representations, a trainable projector, a shared
eight-dimensional PHQ symptom layer, corpus-specific cumulative-logit ordinal
heads, source ordinal reconstruction, target calibration ordinal
reconstruction, and symptom-layer L2 regularization. `Measurement-aware + MMD`
is an auxiliary distribution-matching variant, not the default method
definition.

The local Markdown manuscript, both Word exports, README, issue log, active
handoff, master memory, and supporting writing notes were updated to use the
new naming and to replace broad "safety" phrasing with
validity/comparability/transfer-validity wording. The main manuscript keyword
scan has no matches for the old row names or the defensive phrases flagged by
the user.

The Feishu wiki document at
`https://tcn9unqodkum.feishu.cn/wiki/FeR4wSHOdiydQJkiQsBcqShcn0d` was updated
with targeted `docs +update` operations, not whole-document overwrite. Sections
3.2, 5.3, 6.3, and 7 were replaced from the local manuscript using
paragraph-joined Markdown; Introduction, Related Work, and Validity Gates had
small `str_replace` edits. Final Feishu verification was revision `185`, with
no matches for the old MMD/full wording, defensive phrases, or hard `<br/>`
artifacts in the fetched Markdown.

## Key Decisions

- Core method wording: `Measurement-aware` means the shared symptom layer plus
  target-calibrated corpus-specific ordinal measurement pathway.
- Auxiliary variant wording: `Measurement-aware + MMD` is reported separately;
  the near-tie with the core model is evidence that the gain should be
  attributed to the target-calibrated ordinal pathway rather than MMD.
- Primary metric wording: Macro Item MAE and Calibration MAE remain co-primary;
  the reconstruction-plus-calibration sum is only a compact summary.
- Claim tone: avoid "this is how we package negative results" style language.
  Write bounded results as diagnostic evidence about representation-side versus
  target-side failure modes.
- Terminology: use benchmark validity, measurement comparability,
  observed-scale validity, and transfer validity instead of broad clinical
  safety language, unless referring to historical artifact gate names.

## Files Owned Or Touched

- `/root/autodl-tmp/analysis/diagnostic_measurement_audit_paper/manuscript_reframed_rq_draft.md`
- `/root/autodl-tmp/analysis/diagnostic_measurement_audit_paper/manuscript_reframed_rq_draft.docx`
- `/root/autodl-tmp/analysis/diagnostic_measurement_audit_paper/论文撰写_修订版.docx`
- `/root/autodl-tmp/README.md`
- `/root/autodl-tmp/docs/diagnostic_measurement_audit_paper_outline.md`
- `/root/autodl-tmp/docs/experiment_issue_log.md`
- `/root/autodl-tmp/analysis/diagnostic_measurement_audit_paper/foundation_backbone_measurement_aware_validation_contract.md`
- `/root/autodl-tmp/analysis/diagnostic_measurement_audit_paper/work_report_ppt_outline_script.md`
- `/root/autodl-tmp/analysis/diagnostic_measurement_audit_paper/measurement_aware_framework_literature.md`
- `/root/autodl-tmp/analysis/diagnostic_measurement_audit_paper/closest_related_work_gap_analysis.md`
- `/root/autodl-tmp/MEMORY.md`
- `/root/autodl-tmp/memory/ACTIVE_HANDOFF.md`

## Generated Artifacts

Word drafts regenerated with:

```bash
pandoc --filter pandoc-citeproc \
  --bibliography=analysis/diagnostic_measurement_audit_paper/references.bib \
  --resource-path=.:analysis/diagnostic_measurement_audit_paper \
  analysis/diagnostic_measurement_audit_paper/manuscript_reframed_rq_draft.md \
  -o analysis/diagnostic_measurement_audit_paper/manuscript_reframed_rq_draft.docx

pandoc --filter pandoc-citeproc \
  --bibliography=analysis/diagnostic_measurement_audit_paper/references.bib \
  --resource-path=.:analysis/diagnostic_measurement_audit_paper \
  analysis/diagnostic_measurement_audit_paper/manuscript_reframed_rq_draft.md \
  -o analysis/diagnostic_measurement_audit_paper/论文撰写_修订版.docx
```

## Blockers And Risks

No new experimental blocker was introduced. MV27 remains local-only negative or
diagnostic stress-test evidence unless the user explicitly approves including
or publishing it.

## Next Handoff

Continue precision editing from the local Markdown manuscript and sync Feishu
with targeted block updates. Do not revive "Full w/o MMD" or "Full
measurement-aware" naming in manuscript-facing text. Do not commit or push
MV27 artifacts without explicit user approval.
