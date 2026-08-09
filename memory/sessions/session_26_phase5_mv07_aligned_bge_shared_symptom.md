# Session Memory: Phase 5 MV07 Aligned-BGE Shared-Symptom Validation

Status: complete
Last updated: 2026-08-09 UTC
Thread/task: main agent MV07 aligned BGE shallow validation

## Scope

This session owns the shallow aligned-BGE MV07 shared-symptom validation row. It
uses existing manifest-governed labels and cached subject-level BGE features. It
does not scan raw text/media, fine-tune encoders, write raw snippets, or start
the full symptom-aligned method.

## Current State

- Implemented `scripts/phase5_run_mv07_aligned_bge_shared_symptom.py`.
- Generated
  `analysis/phase5_minimal_validation/p5_mv07_aligned_bge_shared_symptom/`.
- Inputs were aligned frozen BGE subject features for E-DAIC, CMDC, and PDCH:
  512 common `bge_*` model-input columns.
- Label coverage in this run:
  - E-DAIC: 219 train/dev PHQ-8 item-labeled subjects.
  - CMDC: 77 PHQ-9 item-labeled subjects.
  - PDCH: 99 HAMD-labeled subjects for internal HAMD-proxy sanity.
- Models were shallow only: `train_mean`, `total_alloc_ridge`, and
  `bge_itemwise_ridge`.
- Subject-overlap violations: `0`.
- Artifact hygiene passed with zero violations.
- Row-level predictions are ignored local-only in
  `p5_mv07_local_predictions.csv`.

## Key Decisions

- MV07 is complete but blocked as positive shared-symptom evidence:
  `blocked_not_better_than_total_allocation_bge_contract`.
- Pooled PHQ BGE itemwise heads improve over train mean on both E-DAIC and
  CMDC, but they do not consistently beat the total-allocation Ridge floor:
  - E-DAIC delta vs train mean `-0.028`, delta vs total allocation `-0.003`.
  - CMDC delta vs train mean `-0.178`, delta vs total allocation `0.003`.
- PDCH HAMD-proxy sanity is internal only:
  - delta vs train mean `-0.017`;
  - it is not cross-dataset HAMD generalization.
- Identity remains a severe shortcut blocker:
  - BGE feature identity balanced accuracy `1.000`;
  - pooled PHQ prediction identity balanced accuracy `0.980`.
- Do not claim transferable shared symptom representation from the current BGE
  feature contract. Use this as diagnostic/negative evidence and keep the full
  method gate blocked.

## Files Owned Or Touched

- `scripts/phase5_run_mv07_aligned_bge_shared_symptom.py`
- `scripts/phase5_build_minimal_validation_protocol.py`
- `scripts/phase5_full_method_gate_audit.py`
- `analysis/phase5_minimal_validation/p5_mv07_aligned_bge_shared_symptom/`
- `analysis/phase5_minimal_validation/`
- `analysis/phase5_minimal_validation/full_method_gate_audit/`
- `MEMORY.md`
- `docs/master_experiment_plan.md`
- `docs/experiment_issue_log.md`
- `memory/sessions/session_master_orchestration.md`
- `memory/sessions/session_07_phase5_minimal_validation_protocol.md`
- `memory/sessions/session_22_phase5_full_method_gate_audit.md`
- `memory/sessions/session_26_phase5_mv07_aligned_bge_shared_symptom.md`

## Generated Artifacts

Regeneration commands:

```bash
python scripts/phase5_run_mv07_aligned_bge_shared_symptom.py
python scripts/phase5_build_minimal_validation_protocol.py
python scripts/phase5_full_method_gate_audit.py
```

Versionable MV07 artifacts:

- `analysis/phase5_minimal_validation/p5_mv07_aligned_bge_shared_symptom/report.md`
- `analysis/phase5_minimal_validation/p5_mv07_aligned_bge_shared_symptom/run_summary.json`
- `analysis/phase5_minimal_validation/p5_mv07_aligned_bge_shared_symptom/artifact_hygiene_audit.json`
- `analysis/phase5_minimal_validation/p5_mv07_aligned_bge_shared_symptom/metric_summary.csv`
- `analysis/phase5_minimal_validation/p5_mv07_aligned_bge_shared_symptom/metrics_by_seed.csv`
- `analysis/phase5_minimal_validation/p5_mv07_aligned_bge_shared_symptom/comparison_summary.csv`
- `analysis/phase5_minimal_validation/p5_mv07_aligned_bge_shared_symptom/identity_probe_by_seed.csv`
- `analysis/phase5_minimal_validation/p5_mv07_aligned_bge_shared_symptom/identity_probe_summary.csv`
- `analysis/phase5_minimal_validation/p5_mv07_aligned_bge_shared_symptom/model_split_audit.csv`
- `analysis/phase5_minimal_validation/p5_mv07_aligned_bge_shared_symptom/label_feature_audit.csv`
- `analysis/phase5_minimal_validation/p5_mv07_aligned_bge_shared_symptom/construct_target_map.csv`

Local-only MV07 artifact:

- `analysis/phase5_minimal_validation/p5_mv07_aligned_bge_shared_symptom/p5_mv07_local_predictions.csv`

## Blockers And Risks

- High dataset identity means aligned BGE features still carry dataset,
  protocol, language, and population signals. Direct pooled training remains
  unsafe as shared-symptom evidence.
- The total-allocation floor is a strong comparator; itemwise BGE must beat it
  consistently before the project can argue that learned itemwise evidence adds
  shared-construct value.
- PDCH HAMD-proxy results are useful sanity evidence only and should not be
  framed as external HAMD transfer.

## Next Handoff

Keep the full-method gate blocked. The next useful path is either:

1. Fill the ignored local MV06 annotation workbook and rerun the aggregate
   evidence-localization summary gate.
2. Design a stronger shared-symptom feature/identity-control contract that can
   beat train-mean and total-allocation floors while reducing feature and
   prediction identity.
