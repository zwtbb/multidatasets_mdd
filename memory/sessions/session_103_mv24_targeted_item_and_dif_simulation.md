# Session Memory: MV24 Targeted Item And DIF Simulation

Status: complete
Last updated: 2026-09-02 UTC
Thread/task: main-agent continuation after MV24 fair-ablation major concern

## Scope

This session owns the follow-up to the MV24 fair-ablation result: test whether
corpus-specific ordinal heads benefit the measurement-gate `C02/C06`
threshold-shift items, and add a bounded fixed-latent simulation to connect the
measurement audit to the model mechanism. It should not tune MV24 until average
MAE wins, add broad new architecture variants, or revive full M0/M1/M2/M3
cross-scale construction.

## Current State

The official MV24 runner now writes targeted item-level diagnostics comparing
`shared_head_joint_adaptation` against the corpus-specific
`measurement_aware` ordinal head. The analysis covers all shared PHQ items,
measurement-gate anchors `C01/C04/C05/C07`, threshold-shift items `C02/C06`,
other shared items `C03/C08`, and single-item rows.

Real data does not support an independent corpus-specific-head performance
claim. Shared ordinal and corpus-specific ordinal heads are near tied overall
and on the targeted `C02/C06` item set:

- CMDC-to-E-DAIC: all-item MAE `0.819` vs `0.818`; `C02/C06` delta
  `0.004` with interval `[-0.019, 0.027]`.
- E-DAIC-to-CMDC: all-item MAE `0.644` vs `0.645`; `C02/C06` delta
  `0.002` with interval `[-0.004, 0.007]`.

The new fixed-latent companion simulation uses the official MV24
E-DAIC/CMDC label-feature intersection sizes and target calibration split
rule. Under scalar invariance, corpus-specific heads do not help and can hurt
with the smaller CMDC target split. Under planted `C02/C06` threshold DIF, they
show weak item-local mechanism consistency on the `C02/C06` item set:
`0.002` delta for CMDC-to-E-DAIC and `0.011` for E-DAIC-to-CMDC, with
`301/500` and `311/500` lower-error draws. Anchors do not improve.

## Key Decisions

- Keep the robust MV24 conclusion as target calibration plus shared-layer
  adaptation, not corpus-specific-head superiority.
- Describe ordinal target modeling as competitive and direction-dependent.
- Treat corpus-specific ordinal heads as a constructive instantiation whose
  value must be checked empirically against shared heads.
- Use the fixed-latent simulation only as bounded audit-to-model sanity
  checking: it shows the parameterization can respond locally when the shift is
  planted, but it does not overturn the real-data near-tie.
- Continue presenting five-seed paired compact-score tests as descriptive
  stress checks rather than primary superiority evidence.

## Files Owned Or Touched

- `/root/autodl-tmp/scripts/phase5_run_mv24_measurement_aware_ordinal_model.py`
- `/root/autodl-tmp/scripts/phase5_run_mv24_measurement_head_dif_simulation.py`
- `/root/autodl-tmp/analysis/diagnostic_measurement_audit_paper/manuscript_reframed_rq_draft.md`
- `/root/autodl-tmp/analysis/diagnostic_measurement_audit_paper/foundation_backbone_measurement_aware_validation_contract.md`
- `/root/autodl-tmp/README.md`
- `/root/autodl-tmp/docs/experiment_issue_log.md`
- `/root/autodl-tmp/MEMORY.md`
- `/root/autodl-tmp/memory/ACTIVE_HANDOFF.md`

## Generated Artifacts

MV24 targeted item outputs:

- `/root/autodl-tmp/analysis/phase5_minimal_validation/p5_mv24_measurement_aware_ordinal_model/targeted_item_analysis_by_seed.csv`
- `/root/autodl-tmp/analysis/phase5_minimal_validation/p5_mv24_measurement_aware_ordinal_model/targeted_item_analysis_summary.csv`
- `/root/autodl-tmp/analysis/phase5_minimal_validation/p5_mv24_measurement_aware_ordinal_model/targeted_item_analysis_table.csv`
- `/root/autodl-tmp/analysis/phase5_minimal_validation/p5_mv24_measurement_aware_ordinal_model/targeted_item_analysis_table.md`

Regeneration command already completed:

```bash
python scripts/phase5_run_mv24_measurement_aware_ordinal_model.py --clean
```

Companion simulation outputs:

- `/root/autodl-tmp/analysis/phase5_minimal_validation/p5_mv24_measurement_head_dif_simulation/head_comparison_table.md`
- `/root/autodl-tmp/analysis/phase5_minimal_validation/p5_mv24_measurement_head_dif_simulation/head_comparison_summary.csv`
- `/root/autodl-tmp/analysis/phase5_minimal_validation/p5_mv24_measurement_head_dif_simulation/gate_recommendations.csv`
- `/root/autodl-tmp/analysis/phase5_minimal_validation/p5_mv24_measurement_head_dif_simulation/report.md`
- `/root/autodl-tmp/analysis/phase5_minimal_validation/p5_mv24_measurement_head_dif_simulation/run_summary.json`
- `/root/autodl-tmp/analysis/phase5_minimal_validation/p5_mv24_measurement_head_dif_simulation/artifact_hygiene_audit.json`

Regeneration command already completed:

```bash
OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1 python scripts/phase5_run_mv24_measurement_head_dif_simulation.py --clean
```

## Blockers And Risks

- Real-data targeted item analysis does not rescue the corpus-specific
  measurement-head claim.
- The fixed-latent simulation is a mechanism sanity check, not evidence that
  the real multimodal representation plus corpus-specific heads is superior.
- The E-DAIC-to-CMDC target evaluation split remains small, so avoid presenting
  tiny shared-vs-corpus-specific differences as robust architecture evidence.
- Feishu has not yet been synced for the fair-ablation plus targeted-item
  manuscript revision. The latest verified Feishu sync before these local
  changes was revision 211.

## Next Handoff

Use the local Markdown and Word drafts as the current manuscript source of
truth. The next reviewer concern should be handled from this bounded claim
state: Table 3 supports target calibration/shared-layer adaptation, while
corpus-specific ordinal heads remain a tested but not independently supported
parameterization in the current real-data transfer results.
