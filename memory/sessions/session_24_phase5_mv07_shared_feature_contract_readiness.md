# Session Memory: Phase 5 MV07 Shared Feature Contract Readiness

Status: complete
Last updated: 2026-08-09 UTC
Thread/task: main agent Phase 5 MV07 readiness audit

## Scope

This session owns the MV07 readiness audit for the next revised
cross-dataset/shared-symptom feature contract. It checks existing cached
subject-level feature families and manifest label coverage. It does not train a
model, read raw clinical text, scan raw audio/video/gait files, write
predictions, or create new feature embeddings.

## Current State

- Implemented `scripts/phase5_audit_mv07_shared_feature_contract_readiness.py`.
- Generated
  `analysis/phase5_minimal_validation/p5_mv07_shared_feature_contract_readiness/`.
- Current status is `blocked_current_cached_features_insufficient_for_mv07`.
- BGE text is the preferred next aligned contract because CMDC and PDCH already
  have 512-column subject-level BGE caches, but E-DAIC BGE is missing.
- Current eGeMAPS caches are not schema-aligned across E-DAIC, CMDC, PDCH, and
  EATD; common model-input columns across all required datasets are zero.
- Current WavLM caches have 768 common model-input columns across E-DAIC, CMDC,
  and PDCH, but prior MV01/MV04 evidence leaves WavLM identity-blocked unless a
  stronger inference-compatible identity-control variant is specified.
- Label coverage check confirms E-DAIC has 219 PHQ-8 C01-C08 item-labeled
  train/dev subjects, CMDC has 77 PHQ-9 C01-C08 item-labeled subjects, PDCH has
  99 HAMD item+total subjects, CMDC HAMD is only a 25-subject sanity subset,
  and EATD has 162 SDS-total-only subjects.
- Artifact hygiene passed with zero violations.

## Key Decisions

- Do not run a new shared-symptom training row from the current cached features.
- Generate E-DAIC subject-level BGE text features next, using
  manifest-governed transcripts and the same BGE feature contract as CMDC/PDCH.
- Keep generated E-DAIC BGE feature CSVs local-only; track only scripts and
  aggregate readiness/model summaries.
- Treat aligned eGeMAPS as a later regeneration task requiring one extractor
  and one shared schema across datasets.
- Treat WavLM as diagnostic-only until feature-level identity can be reduced in
  an inference-compatible setting while construct metrics are preserved.

## Files Owned Or Touched

- `scripts/phase5_audit_mv07_shared_feature_contract_readiness.py`
- `analysis/phase5_minimal_validation/p5_mv07_shared_feature_contract_readiness/`
- `scripts/phase5_build_minimal_validation_protocol.py`
- `scripts/phase5_full_method_gate_audit.py`
- `analysis/phase5_minimal_validation/`
- `memory/sessions/session_24_phase5_mv07_shared_feature_contract_readiness.md`
- `MEMORY.md`
- `docs/master_experiment_plan.md`
- `docs/experiment_issue_log.md`

## Generated Artifacts

Regeneration commands:

```bash
python scripts/phase5_audit_mv07_shared_feature_contract_readiness.py
python scripts/phase5_build_minimal_validation_protocol.py
python scripts/phase5_full_method_gate_audit.py
```

Versionable artifacts:

- `analysis/phase5_minimal_validation/p5_mv07_shared_feature_contract_readiness/report.md`
- `analysis/phase5_minimal_validation/p5_mv07_shared_feature_contract_readiness/run_summary.json`
- `analysis/phase5_minimal_validation/p5_mv07_shared_feature_contract_readiness/artifact_hygiene_audit.json`
- `analysis/phase5_minimal_validation/p5_mv07_shared_feature_contract_readiness/feature_cache_inventory.csv`
- `analysis/phase5_minimal_validation/p5_mv07_shared_feature_contract_readiness/feature_contract_readiness.csv`
- `analysis/phase5_minimal_validation/p5_mv07_shared_feature_contract_readiness/label_coverage_summary.csv`
- `analysis/phase5_minimal_validation/p5_mv07_shared_feature_contract_readiness/recommended_feature_generation_queue.csv`

## Blockers And Risks

- E-DAIC BGE subject-level features are missing, blocking the preferred
  E-DAIC/CMDC/PDCH aligned text contract.
- eGeMAPS caches were generated with incompatible schemas and should not be
  pooled for shared-symptom evidence.
- WavLM is dimension-aligned but identity-blocked by earlier diagnostics.
- Generating E-DAIC BGE may require reading manifest-governed transcripts, so
  no raw text, snippets, source paths, or embeddings should be committed.

## Next Handoff

Generate aligned E-DAIC BGE subject-level text features locally, rerun MV07
readiness, and only then implement a shallow shared-symptom MV07 training row
with subject-level splits, identity/protocol probes, simple floors, and
local-only row predictions/features.
