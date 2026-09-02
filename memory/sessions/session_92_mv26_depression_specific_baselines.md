# Session Memory: MV26 Depression-Specific Baselines

Status: complete
Last updated: 2026-08-29 UTC
Thread/task: GNN-SDA, QuestMF, and SCD-MLLM-style close-baseline experiments

## Scope

This session adds targeted depression-specific baseline stress tests to the
MV24 PHQ shared-item method story. It does not reproduce external leaderboard
numbers, run WavLM Large/HuBERT Large/VideoMAE, or reopen full cross-scale
M0/M1/M2/M3 construction.

## Current State

MV26 is complete at
`/root/autodl-tmp/analysis/phase5_minimal_validation/p5_mv26_depression_specific_baselines/`.
It uses the official MV24 Qwen3+WavLM+OpenFace subject-level representation,
the same E-DAIC<->CMDC PHQ shared-item transfer contract, the same target
calibration fraction/minimum, and five seeds. All MV26 rows use target
calibration labels, so the comparison is within each baseline family: direct
ordinal item head versus the paper's shared symptom layer plus corpus-specific
cumulative ordinal measurement heads.

QuestMF-style measurement-aware improves the primary
reconstruction-plus-calibration score in both directions:

- CMDC-to-E-DAIC: `1.203 -> 1.159`.
- E-DAIC-to-CMDC: `1.133 -> 1.096`.

GNN-SDA-style is direction-sensitive:

- E-DAIC-to-CMDC: `1.121 -> 1.066`.
- CMDC-to-E-DAIC: `1.339 -> 1.431`, driven by worse calibration.

The result should be framed as a close-baseline stress test. It supports a
clearer complementarity claim for question-wise ordinal fusion and shows that
graph/domain-adapted representations still leave a measurement-pathway
question.

The MV26 artifact folder was later consolidated to include the SCD-MLLM-style
heterogeneous multimodal adapter/fusion stress test. The canonical MV26 folder
now contains 60 seed-level rows and 12 summary rows. SCD-MLLM-style
measurement-aware improves reconstruction-plus-calibration in both directions
(`1.485 -> 1.238`, `1.100 -> 1.084`). Use SCD-MLLM-style as the cleanest
foundation/fusion baseline reinforcement.

## Key Decisions

- The GNN-SDA row is named `GNN-SDA-style` because no official runnable code was
  found in the setup pass. The implementation keeps the closest relevant
  ingredients: static kNN graph propagation, adversarial domain alignment,
  target calibration labels, unlabeled-target pseudo-labeling, and an
  uncertainty-guided loss.
- The QuestMF row is named `QuestMF-style` because the public UKPLab code is
  E-DAIC-only and raw-session oriented. MV26 adapts the paper's question-wise
  modality fusion and ImbOLL idea to the existing subject-level frozen-feature
  contract.
- Do not write MV26 as a universal superiority claim. The useful sentence is:
  measurement-aware target modeling gives complementary gains for
  QuestMF-style item-wise fusion and SCD-MLLM-style heterogeneous
  multimodal/foundation fusion, while the GNN-SDA-style graph-adaptation result
  is direction-sensitive.

## Files Owned Or Touched

- `scripts/phase5_run_mv26_depression_specific_baselines.py`
- `analysis/phase5_minimal_validation/p5_mv26_depression_specific_baselines/`
- `analysis/diagnostic_measurement_audit_paper/manuscript_reframed_rq_draft.md`
- `analysis/diagnostic_measurement_audit_paper/manuscript_reframed_rq_draft.docx`
- `analysis/diagnostic_measurement_audit_paper/references.bib`
- `docs/experiment_issue_log.md`
- `README.md`
- `MEMORY.md`
- `memory/ACTIVE_HANDOFF.md`

## Generated Artifacts

Regeneration command:

```bash
python scripts/phase5_run_mv26_depression_specific_baselines.py --clean
```

Key outputs:

- `baseline_contract.md`
- `baseline_contract.csv`
- `feature_asset_coverage.csv`
- `metrics_by_seed.csv`
- `summary_by_method.csv`
- `main_result_table.md`
- `main_result_table.csv`
- `secondary_clinical_metrics_table.md`
- `secondary_clinical_metrics_table.csv`
- `paired_measurement_layer_significance.csv`
- `report.md`
- `run_summary.json`
- `artifact_hygiene_audit.json`

The helper command for the SCD-MLLM-style component is:

```bash
python scripts/phase5_run_mv26_scd_mllm_baseline.py --clean
```

Artifact hygiene passes. Outputs are aggregate-only.

## Blockers And Risks

- MV26 is not an exact reproduction of GNN-SDA or QuestMF original benchmark
  settings; it is an adapted, controlled target-pathway stress test under the
  MV24 data and feature contract.
- Paired significance over five seeds is non-significant for the MV26
  direct-versus-aware comparisons. Use the results as close-baseline
  reinforcement and stress evidence, not as the main statistical claim.
- The CMDC target eval size remains small in E-DAIC-to-CMDC after the official
  video-feature intersection, so confidence intervals are wide.

## Next Handoff

Use MV24 as the main formal method table and MV26 as an optional supplementary
or short main-text stress-test paragraph. If the manuscript needs a compact
table, use the six-row reconstruction-plus-calibration summary now inserted
into the local Markdown draft as Supplementary Table S2.
