# Session Memory: MV26 SCD-MLLM-Style Baseline

Status: complete
Last updated: 2026-08-29 UTC
Thread/task: SCD-MLLM-style close-baseline experiment

## Scope

This session adds the SCD-MLLM-style heterogeneous multimodal/foundation fusion
stress test to the canonical MV26 package. It adapts the relevant modeling
idea to the existing subject-level frozen-feature and PHQ shared-item target
contract; it is not a full external leaderboard reproduction, raw MLLM
training run, WavLM Large/HuBERT Large/VideoMAE experiment, or end-to-end
multimodal fine-tuning claim.

## Current State

The SCD-MLLM-style rows are complete and merged into the canonical MV26 folder:
`/root/autodl-tmp/analysis/phase5_minimal_validation/p5_mv26_depression_specific_baselines/`.
The package now contains three public close-baseline families:
GNN-SDA-style, QuestMF-style, and SCD-MLLM-style. It uses the official MV24
Qwen3+WavLM+OpenFace subject-level representation, the same E-DAIC<->CMDC PHQ
shared-item transfer contract, the same target calibration fraction/minimum,
and five seeds.

SCD-MLLM-style measurement-aware improves the primary
reconstruction-plus-calibration score in both directions:

- CMDC-to-E-DAIC: `1.485 -> 1.238`.
- E-DAIC-to-CMDC: `1.100 -> 1.084`.

## Key Decisions

- Name the row `SCD-MLLM-style` because MV26 adapts the heterogeneous
  adapter/fusion idea under our frozen subject-level feature contract rather
  than claiming exact reproduction of the original external benchmark setting.
- Use SCD-MLLM-style as the cleanest foundation/fusion baseline reinforcement:
  even after a stronger heterogeneous multimodal fusion baseline, the
  measurement-aware target pathway still improves the primary
  reconstruction-plus-calibration score in both transfer directions.
- Do not broaden the claim into depression-detection SOTA or a universal
  full-vs-all result; MV24 remains the main formal method table and MV26 is a
  close-baseline stress test.

## Files Owned Or Touched

- `scripts/phase5_run_mv26_depression_specific_baselines.py`
- `scripts/phase5_run_mv26_scd_mllm_baseline.py`
- `analysis/phase5_minimal_validation/p5_mv26_depression_specific_baselines/`
- `analysis/diagnostic_measurement_audit_paper/manuscript_reframed_rq_draft.md`
- `analysis/diagnostic_measurement_audit_paper/manuscript_reframed_rq_draft.docx`
- `docs/experiment_issue_log.md`
- `README.md`
- `MEMORY.md`
- `memory/ACTIVE_HANDOFF.md`

## Generated Artifacts

Canonical regeneration command:

```bash
python scripts/phase5_run_mv26_depression_specific_baselines.py --clean
```

SCD-only component command for debugging:

```bash
python scripts/phase5_run_mv26_scd_mllm_baseline.py --clean
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

Artifact hygiene passes. Outputs are aggregate-only.

## Blockers And Risks

- MV26 is not a full SCD-MLLM reproduction; it is a controlled target-pathway
  stress test under the paper's data and feature contract.
- Paired significance over five seeds is non-significant for the positive
  SCD-MLLM-style measurement-aware deltas. Use it as reinforcement, not as the
  main statistical claim.

## Next Handoff

Use MV24 as the main formal method table, the combined MV26 folder as an
optional close-baseline stress-test supplement, and SCD-MLLM-style MV26 as the
best answer to the foundation/fusion baseline critique. If Feishu needs
updating, sync only the compact MV26 paragraph/table with targeted block edits.
