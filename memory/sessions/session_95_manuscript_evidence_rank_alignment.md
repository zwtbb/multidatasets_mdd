# Session Memory: manuscript_evidence_rank_alignment

Status: complete
Last updated: 2026-08-30 UTC
Thread/task: main-agent manuscript polish

## Scope

This session owns a writing-level claim-alignment pass for the current
measurement-aware cross-corpus depression detection manuscript. It does not add
or rerun experiments.

## Current State

The user's evidence-rank critique was accepted as correct. The manuscript now
treats RQ1 as: raw corpus identity is strong, but residual identity after
length and severity controls is contrast-dependent. E-DAIC/CMDC is no longer
described as retaining strong residual representation heterogeneity after
controls. The over-specific sentence attributing raw identity to language and
protocol was removed because the controlled probe residualizes length and
severity, not language or protocol.

RQ2 remains the central empirical section. DAIC-WOZ/E-DAIC is compressed to a
same-lineage provenance sanity control. CMDC/PDCH HAMD is downgraded to a
bounded exploratory check whose role is only to show that the measurement
concern is not obviously a PHQ-8 versus PHQ-9 artifact. The E-DAIC/CMDC PHQ
shared-item result remains the main measurement evidence.

The MV24 primary metric language now treats Macro Item MAE and Calibration MAE
as co-primary metrics. The summed reconstruction-plus-calibration score remains
as a compact summary, but the manuscript no longer depends on a claimed 1:1
clinical trade-off between item reconstruction error and calibration gap.

## Key Decisions

- Present RQ1 as a representation audit, not a universal strong-shift claim.
- Keep DAIC-WOZ/E-DAIC and CMDC/PDCH visually and textually secondary to the
  E-DAIC/CMDC PHQ shared-item analysis.
- Use the co-primary metric wording consistently in Abstract, Methods, Results,
  Discussion, and Conclusion.
- Preserve the strategic writing stance: strengthen the supported claims while
  keeping weaker evidence as bounded scope/support, not as centered defects.

## Files Owned Or Touched

- `/root/autodl-tmp/analysis/diagnostic_measurement_audit_paper/manuscript_reframed_rq_draft.md`
- `/root/autodl-tmp/analysis/diagnostic_measurement_audit_paper/manuscript_reframed_rq_draft.docx`
- `/root/autodl-tmp/analysis/diagnostic_measurement_audit_paper/论文撰写_修订版.docx`
- Feishu document revision verified at revision 166:
  `https://tcn9unqodkum.feishu.cn/wiki/FeR4wSHOdiydQJkiQsBcqShcn0d`

## Generated Artifacts

Regenerated Word drafts from the Markdown source:

```bash
pandoc --filter pandoc-citeproc \
  --bibliography=analysis/diagnostic_measurement_audit_paper/references.bib \
  --resource-path=.:analysis/diagnostic_measurement_audit_paper \
  analysis/diagnostic_measurement_audit_paper/manuscript_reframed_rq_draft.md \
  -o analysis/diagnostic_measurement_audit_paper/manuscript_reframed_rq_draft.docx
```

The same command was run again with output
`analysis/diagnostic_measurement_audit_paper/论文撰写_修订版.docx`.

## Blockers And Risks

No experiment blocker was introduced. MV27 remains local/uncommitted negative
binary stress-test evidence from the prior session unless the user explicitly
decides to include or submit it.

## Next Handoff

Continue manuscript polish from the new evidence-rank framing. Avoid reverting
to "strong representation heterogeneity" as a blanket RQ1 conclusion, and keep
Macro Item MAE plus Calibration MAE as co-primary in future result prose.
