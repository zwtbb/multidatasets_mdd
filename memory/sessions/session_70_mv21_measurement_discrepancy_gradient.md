# Session Memory: MV21 Measurement Discrepancy Gradient

Status: complete
Last updated: 2026-08-24 UTC
Thread/task: User-directed experiment reinforcement for manuscript writing

## Scope

This session owns the bounded MV21 reinforcement requested by the user:
PHQ shared-item descriptive and severity-conditioned analysis, exploratory
CMDC-HAMD vs PDCH-HAMD same-scale analysis, and DAIC-WOZ/E-DAIC same-lineage
PHQ-8 control. It must not expand into full HAMD MIM, HAMD IRT, or formal HAMD
measurement-invariance/DIF modeling.

## Current State

- MV21 is complete under
  `/root/autodl-tmp/analysis/phase5_minimal_validation/p5_mv21_measurement_discrepancy_gradient/`.
- Artifact hygiene passed with aggregate-only exports. No subject identifiers,
  raw text/audio/video paths, predictions, features, theta, or fitted
  parameter tables were exported.
- PHQ shared-item analysis compares E-DAIC PHQ-8 (`n=219`) and CMDC PHQ-9
  shared PHQ items (`n=77`) with item distributions, category proportions,
  shared-total severity bands, and item-excluded severity-conditioned response
  summaries.
- HAMD same-scale analysis compares CMDC-HAMD (`n=25`) and PDCH-HAMD (`n=99`)
  with item distributions, category proportions, item-excluded
  severity-conditioned response summaries, and aggregate Spearman item-pair
  correlation deltas. Codes `9` are treated as missing.
- DAIC-WOZ/E-DAIC control uses DAIC-WOZ official train/dev PHQ-8 item rows:
  142 train/dev rows, 141 complete item subjects, 1 incomplete item row, and
  141 paired DAIC-WOZ/E-DAIC overlap subjects.

## Key Decisions

- Use MV21 to support a measurement-discrepancy gradient:
  same-scale/same-lineage DAIC-WOZ to E-DAIC, PHQ-family but different
  language/protocol E-DAIC to CMDC, and same clinical scale but different
  corpus/population CMDC to PDCH.
- Correct DAIC-WOZ wording: DAIC-WOZ is an AVEC2017 Wizard-of-Oz
  benchmark/control from the DAIC lineage; E-DAIC is the extended DAIC dataset.
  DAIC-WOZ is not a fully independent corpus for pooled evidence because the
  locally used 300-492 subjects overlap heavily with E-DAIC.
- Treat PHQ shared-item results as descriptive and severity-conditioned
  evidence, not as a replacement for MV10/MV11/MV13/MV14/MV19 psychometric
  claims.
- Treat CMDC-HAMD vs PDCH-HAMD results as exploratory same-scale support only,
  not as formal HAMD invariance, MIM, IRT, or DIF evidence.

## Files Owned Or Touched

- `/root/autodl-tmp/scripts/phase5_run_mv21_measurement_discrepancy_gradient.py`
- `/root/autodl-tmp/scripts/build_diagnostic_paper_claim_tables.py`
- `/root/autodl-tmp/scripts/build_diagnostic_paper_results_sections.py`
- `/root/autodl-tmp/scripts/build_diagnostic_paper_manuscript_draft.py`
- `/root/autodl-tmp/MEMORY.md`
- `/root/autodl-tmp/memory/ACTIVE_HANDOFF.md`
- `/root/autodl-tmp/memory/sessions/session_68_daicwoz_benchmark_view.md`
- `/root/autodl-tmp/memory/sessions/session_69_main_takeover_manuscript_orchestration.md`
- `/root/autodl-tmp/memory/sessions/session_70_mv21_measurement_discrepancy_gradient.md`
- `/root/autodl-tmp/datasets/registry.yaml`
- `/root/autodl-tmp/datasets/README.md`
- `/root/autodl-tmp/datasets/DAIC-WOZ/README.md`
- `/root/autodl-tmp/analysis/diagnostic_measurement_audit_paper/manuscript_front_matter_working_draft.md`

## Generated Artifacts

Regenerate MV21 with:

```bash
python /root/autodl-tmp/scripts/phase5_run_mv21_measurement_discrepancy_gradient.py
```

Primary MV21 outputs:

- `/root/autodl-tmp/analysis/phase5_minimal_validation/p5_mv21_measurement_discrepancy_gradient/run_summary.json`
- `/root/autodl-tmp/analysis/phase5_minimal_validation/p5_mv21_measurement_discrepancy_gradient/report.md`
- `/root/autodl-tmp/analysis/phase5_minimal_validation/p5_mv21_measurement_discrepancy_gradient/phq_shared_item_distribution.csv`
- `/root/autodl-tmp/analysis/phase5_minimal_validation/p5_mv21_measurement_discrepancy_gradient/phq_shared_conditioned_deltas.csv`
- `/root/autodl-tmp/analysis/phase5_minimal_validation/p5_mv21_measurement_discrepancy_gradient/hamd_item_distribution.csv`
- `/root/autodl-tmp/analysis/phase5_minimal_validation/p5_mv21_measurement_discrepancy_gradient/hamd_conditioned_deltas.csv`
- `/root/autodl-tmp/analysis/phase5_minimal_validation/p5_mv21_measurement_discrepancy_gradient/hamd_item_correlation_delta_summary.csv`
- `/root/autodl-tmp/analysis/phase5_minimal_validation/p5_mv21_measurement_discrepancy_gradient/daicwoz_edaic_paired_item_differences.csv`
- `/root/autodl-tmp/analysis/phase5_minimal_validation/p5_mv21_measurement_discrepancy_gradient/daicwoz_edaic_conditioned_deltas.csv`
- `/root/autodl-tmp/analysis/phase5_minimal_validation/p5_mv21_measurement_discrepancy_gradient/artifact_hygiene_audit.json`

Key aggregate results:

- DAIC-WOZ/E-DAIC same-lineage PHQ-8 control: paired overlap `n=141`,
  minimum item exact-match rate `0.986`, maximum mean absolute paired item
  difference `0.014`, and maximum non-sparse severity-conditioned item-mean
  delta `0.118`.
- E-DAIC/CMDC PHQ shared items: top non-sparse item-excluded severity-conditioned
  deltas include C02 high-bin mean delta `-0.834`, C08 high-bin delta `-0.623`,
  C06 middle-bin delta `0.618`, and C01 high-bin delta `-0.486`.
- CMDC/PDCH HAMD: top non-sparse item-excluded severity-conditioned deltas
  include HAMD07 high-bin delta `-0.967`, HAMD11 high-bin delta `-0.911`,
  HAMD01 low-bin delta `0.895`, and HAMD08 overlap-mild-moderate middle-bin
  delta `0.877`.
- HAMD item-pair correlation deltas are exploratory; largest aggregate
  Spearman deltas include HAMD07-HAMD09 `0.712`, HAMD06-HAMD17 `0.651`, and
  HAMD09-HAMD10 `0.641`.

## Blockers And Risks

- CMDC-HAMD has only 25 subjects, so HAMD claims must stay exploratory and
  descriptive.
- DAIC-WOZ and E-DAIC have heavy subject/source overlap. DAIC-WOZ is only a
  same-lineage control, not an independent third corpus.
- MV21 does not unlock the full method gate; the paper remains a bounded
  diagnostic target-measurement-validity paper.

## Next Handoff

Regenerate the paper claim tables, results sections, bibliography artifacts,
and manuscript draft so MV21 appears in the current writing bundle. Keep the
experiment queue frozen after this user-directed reinforcement unless a future
reviewer-critical need is explicitly predeclared.
