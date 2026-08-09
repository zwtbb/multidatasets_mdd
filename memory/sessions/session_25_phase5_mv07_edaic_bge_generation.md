# Session Memory: Phase 5 MV07 E-DAIC BGE Generation

Status: complete
Last updated: 2026-08-09 UTC
Thread/task: main agent Phase 5 MV07 E-DAIC BGE feature-contract preparation

## Scope

This session owns the local-only E-DAIC BGE subject-feature generation needed
to unblock the MV07 aligned text feature contract. It prepares features only;
it does not train a model, write predictions, tune hyperparameters, export raw
transcript text, or write source locators to tracked outputs.

## Current State

- Implemented `scripts/phase5_generate_mv07_edaic_bge_features.py`.
- Generated the ignored local cache
  `analysis/phase2_baselines/edaic_text_bge/edaic_bge_subject_features.csv`.
- The cache covers 219 E-DAIC train/dev subjects with complete PHQ-8 C01-C08
  item payloads: 163 train and 56 dev.
- The cache has 512 `bge_*` model-input columns and no path-like columns.
- The generation uses the same frozen `BAAI/bge-small-zh-v1.5` model family as
  the existing CMDC/PDCH BGE caches.
- Tracked audit outputs live under
  `analysis/phase5_minimal_validation/p5_mv07_edaic_bge_generation/` and pass
  artifact hygiene with zero violations.
- Rerunning `scripts/phase5_audit_mv07_shared_feature_contract_readiness.py`
  now sets MV07 readiness to `ready_to_run_minimal_validation`.

## Key Decisions

- Keep `edaic_bge_subject_features.csv` local-only and ignored by Git.
- Commit only the generation script and aggregate audit artifacts.
- Treat MV07 readiness as authorization to run the next shallow aligned-BGE
  validation row, not as evidence for a shared-symptom representation.
- Keep eGeMAPS and WavLM caveats separate: eGeMAPS still needs one aligned
  schema, and WavLM still needs stronger inference-compatible identity control.

## Files Owned Or Touched

- `scripts/phase5_generate_mv07_edaic_bge_features.py`
- `analysis/phase5_minimal_validation/p5_mv07_edaic_bge_generation/`
- `analysis/phase5_minimal_validation/p5_mv07_shared_feature_contract_readiness/`
- `scripts/phase5_audit_mv07_shared_feature_contract_readiness.py`
- `scripts/phase5_build_minimal_validation_protocol.py`
- `scripts/phase5_full_method_gate_audit.py`
- `MEMORY.md`
- `docs/master_experiment_plan.md`
- `docs/experiment_issue_log.md`
- `memory/sessions/session_25_phase5_mv07_edaic_bge_generation.md`

## Generated Artifacts

Regeneration commands:

```bash
python scripts/phase5_generate_mv07_edaic_bge_features.py
python scripts/phase5_audit_mv07_shared_feature_contract_readiness.py
python scripts/phase5_build_minimal_validation_protocol.py
python scripts/phase5_full_method_gate_audit.py
```

Tracked artifacts:

- `analysis/phase5_minimal_validation/p5_mv07_edaic_bge_generation/report.md`
- `analysis/phase5_minimal_validation/p5_mv07_edaic_bge_generation/run_summary.json`
- `analysis/phase5_minimal_validation/p5_mv07_edaic_bge_generation/artifact_hygiene_audit.json`
- `analysis/phase5_minimal_validation/p5_mv07_edaic_bge_generation/local_artifact_manifest.csv`
- `analysis/phase5_minimal_validation/p5_mv07_edaic_bge_generation/subject_coverage_summary.csv`

Ignored local-only artifact:

- `analysis/phase2_baselines/edaic_text_bge/edaic_bge_subject_features.csv`

## Blockers And Risks

- BGE-small-zh is shared with CMDC/PDCH for feature-contract alignment, but it
  is still a Chinese BGE encoder applied to English E-DAIC transcripts. MV07
  must therefore compare against simple floors and identity/protocol probes
  before any semantic transfer claim.
- The aligned BGE cache makes the next MV07 validation runnable, but no model
  result exists yet.
- Generated feature CSVs, row predictions, transformed features, and model
  artifacts must remain local-only.

## Next Handoff

Run the aligned-BGE MV07 shallow shared-symptom validation row over E-DAIC,
CMDC, and PDCH. It should use subject-level splits, PHQ C01-C08 heads for
E-DAIC/CMDC, PDCH HAMD mapped constructs as auxiliary sanity, simple
train-mean/total-allocation floors, and dataset/protocol identity probes.
