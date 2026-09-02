# Session Memory: Figure and Table Integration

Status: complete
Last updated: 2026-08-25 UTC
Thread/task: Figure/table integration and captions after manuscript rewrite

## Scope

This session owns the first main-text integration of figures and tables into
the RQ-reframed manuscript. It should follow the selected writing templates,
keep the visual story tight, and avoid turning the manuscript into an
experiment-inventory appendix.

## Current State

The manuscript now embeds six main figures and two main tables:

- Figure 1: framework overview, currently programmatic and intended as a
  replaceable slot for the user's hand-drawn total figure.
- Figure 2: dataset relationship map.
- Figure 3: representation identity heatmap.
- Figure 4: PHQ shared-item response analysis.
- Figure 5: same-lineage control and measurement-discrepancy gradient.
- Figure 6: latent-target prediction tradeoff.
- Table 1: dataset/view roles.
- Table 2: validity gates, main evidence, and modeling implications.

The generated Word draft confirms six embedded media files.

## Key Decisions

- Keep Figure 7 generated but out of the main text for now. It is useful as a
  supplement or backup discussion summary, but the main text already carries
  the claim boundary clearly.
- The user can hand-draw Figure 1. The current programmatic Figure 1 remains
  in the manuscript as a temporary/fallback overview.
- Programmatic figure titles were made more neutral and publication-like, while
  the narrative takeaways moved into captions and surrounding prose.
- The figure-generation script now strips SVG trailing whitespace and writes
  CSV manifests with Unix line endings, so `git diff --check` passes after
  regeneration.

## Files Owned Or Touched

- `/root/autodl-tmp/analysis/diagnostic_measurement_audit_paper/manuscript_reframed_rq_draft.md`
- `/root/autodl-tmp/analysis/diagnostic_measurement_audit_paper/manuscript_reframed_rq_draft.docx`
- `/root/autodl-tmp/scripts/build_paper_core7_figures.py`
- `/root/autodl-tmp/analysis/diagnostic_measurement_audit_paper/figures_core7/`
- `/root/autodl-tmp/analysis/diagnostic_measurement_audit_paper/figure_table_integration_guide.md`
- `/root/autodl-tmp/MEMORY.md`
- `/root/autodl-tmp/memory/ACTIVE_HANDOFF.md`
- `/root/autodl-tmp/memory/sessions/session_85_figure_table_integration.md`

## Generated Artifacts

Regenerated core7 figures with:

```bash
python scripts/build_paper_core7_figures.py
```

Regenerated Word draft with:

```bash
pandoc --filter pandoc-citeproc --bibliography=analysis/diagnostic_measurement_audit_paper/references.bib analysis/diagnostic_measurement_audit_paper/manuscript_reframed_rq_draft.md -o analysis/diagnostic_measurement_audit_paper/manuscript_reframed_rq_draft.docx
```

Validation:

```bash
git diff --check
pandoc analysis/diagnostic_measurement_audit_paper/manuscript_reframed_rq_draft.docx -t markdown | rg -n "Figure 1|Figure 2|Figure 3|Figure 4|Figure 5|Figure 6|Table 1|Table 2"
```

The docx contains six embedded media files.

## Blockers And Risks

The final hand-drawn Figure 1 is not yet available. When the user provides it,
replace the current programmatic Figure 1 image while keeping the same caption
logic unless the drawing changes the visual emphasis.

## Next Handoff

Recommended next step:

1. Review the figure placement in the exported Word document.
2. Build final supplement table/figure list if needed.
3. Run a reference verification pass before submission-grade formatting.
