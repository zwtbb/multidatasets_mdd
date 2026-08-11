# Session Memory: Phase 5 MV12 Two-Stage Latent-Target Design

Status: active
Last updated: 2026-08-11 UTC
Thread/task: main agent continuation

## Scope

This session owns the P5_MV12 design/predeclaration task after MV11. It defines
how the next experiment will separate label-only measurement target generation
from multimodal prediction. It should not run the multimodal model or export
subject-level theta scores, fitted measurement parameters, row predictions,
transformed features, projection directions, or model artifacts.

## Current State

- MV12 design is complete at
  `/root/autodl-tmp/analysis/phase5_minimal_validation/p5_mv12_two_stage_latent_target_design/`.
- The script reads only aggregate Phase 5 artifacts from MV07, MV07b, MV07c,
  MV08b, MV09, MV10, MV11, and the full-method gate.
- It does not read raw data, multimodal features, row-level predictions,
  private review material, fitted measurement parameters, or subject theta
  scores.
- Artifact hygiene passed across the tracked MV12 design outputs.
- The refreshed full-method gate now reads 30 Phase 5 evidence rows and keeps
  `full_method_allowed=false`.
- The rank-1 next action is now `NEXT_IMPLEMENT_TWO_STAGE_LATENT_TARGET_RUN`.

## Key Decisions

- Treat MV12 as `ready_to_implement_mv12_two_stage_latent_target`.
- The primary measurement target is an MV11-style train-fold label-only
  `Y_to_theta` target over E-DAIC PHQ-8 and CMDC PHQ-9 shared C01-C08 labels.
- Primary anchors are `C01`, `C04`, `C05`, and `C07`.
- `C02` and `C06` require threshold-DIF-aware treatment.
- `C03` and `C08` are sensitivity-only target variants unless a later
  predeclared contract upgrades them.
- The future runner must compare train-mean theta, observed-total floors,
  direct `X_to_Y` total-allocation/itemwise baselines, primary BGE
  `X_to_theta`, optional identity-projected `X_to_theta`, and
  `theta_to_observed` mapping.
- Full-method construction remains blocked until the actual MV12 run passes
  predictive utility, external transfer, conditional shared-latent identity,
  leakage, and artifact-hygiene gates.

## Files Owned Or Touched

- `scripts/phase5_plan_mv12_two_stage_latent_target.py`
- `analysis/phase5_minimal_validation/p5_mv12_two_stage_latent_target_design/`
- `scripts/phase5_full_method_gate_audit.py`
- `scripts/build_diagnostic_paper_claim_tables.py`
- `analysis/phase5_minimal_validation/full_method_gate_audit/`
- `analysis/diagnostic_measurement_audit_paper/`
- `analysis/phase5_minimal_validation/experiment_matrix.csv`
- `README.md`
- `docs/diagnostic_measurement_audit_paper_outline.md`
- `docs/experiment_issue_log.md`
- `MEMORY.md`
- `memory/sessions/session_master_orchestration.md`
- `memory/sessions/session_42_mv12_two_stage_latent_target_design.md`

## Generated Artifacts

Regenerate MV12 design with:

```bash
python scripts/phase5_plan_mv12_two_stage_latent_target.py --overwrite
```

Key aggregate outputs:

- `target_generation_contract.csv`
- `local_only_boundary_contract.csv`
- `model_ladder_contract.csv`
- `identity_transfer_gate_contract.csv`
- `pass_fail_gate_contract.csv`
- `source_evidence_summary.csv`
- `implementation_queue.csv`
- `method_source_refs.csv`
- `report.md`
- `run_summary.json`
- `artifact_hygiene_audit.json`

Refresh downstream gates and paper tables with:

```bash
python scripts/phase5_full_method_gate_audit.py
python scripts/build_diagnostic_paper_claim_tables.py
```

## Blockers And Risks

- MV12 is design evidence only. It provides no positive `X_to_theta` result yet.
- MV11 has an AIC/BIC caveat, so target wording must remain partial-invariance
  and conservative.
- The future runner must keep latent targets, fitted item parameters, row
  predictions, transformed features, projection directions, and model artifacts
  local-only.
- Conditional identity remains a hard shared-latent diagnostic; MV09 baselines
  are high, so MV12 must improve them rather than rely on unconditional identity
  wording.

## Next Handoff

Implement `scripts/phase5_run_mv12_two_stage_latent_target.py` under the MV12
contract. The runner should generate local-only `Y_to_theta` targets, run
direct and floor baselines, train primary BGE `X_to_theta` and optional
identity-projected variants, audit same-dataset and E-DAIC/CMDC transfer,
export only aggregate metrics and hygiene summaries, then refresh the full
method gate and paper tables.
