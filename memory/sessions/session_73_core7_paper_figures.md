# Session Memory: session_73_core7_paper_figures

Status: active
Last updated: 2026-08-24 UTC
Thread/task: user-requested seven core manuscript figures

## Scope

This session owns the user-requested seven-figure manuscript package for the
cross-corpus depression benchmark validity audit. It uses existing aggregate
project artifacts and should not touch raw datasets, subject-row outputs,
features, predictions, theta scores, fitted parameters, workbooks, or local-only
row-level experiment payloads.

## Current State

The user supplied a seven-figure recommendation and asked Codex to draw the
figures using existing data rather than direct image generation. A new script
now generates the canonical seven core figures from registry/audit metadata and
aggregate Phase 3/MV16/MV17a/MV21 outputs.

Output directory:

- `/root/autodl-tmp/analysis/diagnostic_measurement_audit_paper/figures_core7/`

Regeneration command:

```bash
python /root/autodl-tmp/scripts/build_paper_core7_figures.py
```

## Key Decisions

- `figures_core7` is the default figure package for current manuscript layout.
  The earlier `figures_reframed_rq` package remains a backup/alternative set.
- The seven figures are:
  1. Framework overview.
  2. Dataset relationship map.
  3. Representation identity heatmap.
  4. PHQ shared-item measurement analysis.
  5. DAIC-WOZ/E-DAIC controlled comparison.
  6. Latent target tradeoff.
  7. Evidence summary.
- Figure 3 repeats each probe's grouped-CV balanced accuracy across the
  datasets covered by that comparable feature-space contract; grey cells mean
  no comparable probe was run for that corpus.
- Figure 4 uses E-DAIC/CMDC PHQ shared-item distribution and item-excluded
  severity-conditioned endorsement probabilities for C02 and C06.
- Figure 5 anchors the DAIC-WOZ/E-DAIC same-lineage control with paired item
  exact-match rates and then shows the MV21 discrepancy gradient.
- Figure 6 frames latent targets as a tradeoff: lower output-level identity does
  not consistently produce transfer or observed-scale safety gains.
- Figure 7 includes calibration only as summary evidence that target-side
  calibration remains insufficient alone; it is not a separate method-success
  figure.

## Files Owned Or Touched

- `/root/autodl-tmp/scripts/build_paper_core7_figures.py`
- `/root/autodl-tmp/analysis/diagnostic_measurement_audit_paper/figures_core7/`
- `/root/autodl-tmp/memory/sessions/session_73_core7_paper_figures.md`
- `/root/autodl-tmp/MEMORY.md`
- `/root/autodl-tmp/memory/ACTIVE_HANDOFF.md`

## Generated Artifacts

The output directory contains PNG/SVG for all seven figures plus:

- `core7_figure_manifest.csv`
- `core7_figure_manifest.json`
- `core7_figure_recommendations.md`

## Blockers And Risks

- Figures are manuscript-draft quality and data-backed. For camera-ready
  submission, the SVGs can still be lightly polished in a vector editor.
- Figure 1 and Figure 2 are structured diagrams driven by project registry and
  audit metadata rather than numerical experiment plots, which is appropriate
  for their role but should be described as design/framework figures.
- Captions still need to be written and must preserve the bounded audit claim:
  evidence for representation discrepancy and potential measurement
  heterogeneity, not universal construct divergence or a solved full method.

## Next Handoff

Use `/root/autodl-tmp/analysis/diagnostic_measurement_audit_paper/figures_core7/core7_figure_recommendations.md`
as the figure index for manuscript layout and caption writing. Validation
passed with:

```bash
python -m py_compile /root/autodl-tmp/scripts/build_paper_core7_figures.py
git diff --check
```
