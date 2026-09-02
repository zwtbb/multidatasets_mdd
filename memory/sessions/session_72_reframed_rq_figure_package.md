# Session Memory: session_72_reframed_rq_figure_package

Status: active
Last updated: 2026-08-24 UTC
Thread/task: main-agent paper figure recommendation and generation

## Scope

This session owns the figure recommendation package for the current
target-measurement-validity manuscript narrative. It should not change raw
datasets, subject-level manifests, row-level predictions, features, theta
scores, fitted parameters, workbooks, or the MV21 aggregate source artifacts.

## Current State

The user asked which figures should be placed in the current manuscript after
adding DAIC-WOZ and whether Codex could draw them directly. A lightweight figure
builder now generates a main/supplement figure package from aggregate artifacts
only.

Generated figures are under:

- `/root/autodl-tmp/analysis/diagnostic_measurement_audit_paper/figures_reframed_rq/`

The package includes PNG previews and SVG vector versions for:

- `fig1_benchmark_validity_framework`
- `fig2_dataset_view_role_map`
- `fig3_measurement_discrepancy_gradient`
- `fig4_prediction_consequence_gate_matrix`
- `supp_fig_phq_shared_item_conditioned_deltas`
- `supp_fig_hamd_same_scale_exploratory`

## Key Decisions

- Main-text priority:
  1. Figure 3 measurement-discrepancy gradient: strongest new figure for the
     DAIC-WOZ/E-DAIC, E-DAIC/CMDC, CMDC/PDCH RQ2 story.
  2. Figure 1 benchmark-validity framework: conceptual opening figure if space
     allows.
  3. Figure 4 prediction-consequence gate matrix: compact RQ3 negative-result
     summary.
  4. Figure 2 dataset/view role map: use in the dataset/design section only if
     space allows; otherwise keep as supplement/table.
- Supplement priority:
  - PHQ shared-item severity-conditioned deltas.
  - HAMD exploratory same-scale item/correlation deltas.
- DAIC-WOZ is shown as a benchmark-control view from the DAIC lineage, not as a
  fully independent PHQ corpus.
- The HAMD supplement is explicitly exploratory and uses all-subjects item
  deltas for the left panel; it does not imply formal HAMD MIM/IRT or
  invariance testing.

## Files Owned Or Touched

- `/root/autodl-tmp/scripts/build_paper_reframed_rq_figures.py`
- `/root/autodl-tmp/memory/sessions/session_72_reframed_rq_figure_package.md`
- `/root/autodl-tmp/MEMORY.md`
- `/root/autodl-tmp/memory/ACTIVE_HANDOFF.md`

## Generated Artifacts

Regenerate with:

```bash
python /root/autodl-tmp/scripts/build_paper_reframed_rq_figures.py
```

Generated recommendation metadata:

- `/root/autodl-tmp/analysis/diagnostic_measurement_audit_paper/figures_reframed_rq/figure_recommendation_manifest.csv`
- `/root/autodl-tmp/analysis/diagnostic_measurement_audit_paper/figures_reframed_rq/figure_recommendation_manifest.json`
- `/root/autodl-tmp/analysis/diagnostic_measurement_audit_paper/figures_reframed_rq/figure_recommendations.md`

## Blockers And Risks

- Figure 2 is a useful design map but may be too space-consuming for the main
  paper depending on page limits.
- Final manuscript captions still need to be written and should keep the same
  claim boundary: diagnostic benchmark-validity audit, not a solved full method
  or universal measurement-shift claim.
- Figure aesthetics are draft-quality but usable; a final camera-ready version
  can be hand-polished in Illustrator/Inkscape from the SVGs.

## Next Handoff

If continuing manuscript writing, insert or cite the figure package as:

- Main: Figures 1, 3, and 4.
- Optional main or supplement: Figure 2.
- Supplement: S1 PHQ shared-item deltas and S2 HAMD exploratory deltas.

Write captions directly against the generated SVG/PNG files and MV21/MV17a
source artifacts, not against memory prose.
