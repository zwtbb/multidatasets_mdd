# Session Memory: Phase 5 Minimal Validation Protocol

Status: complete
Last updated: 2026-08-09 UTC
Thread/task: main agent minimal validation protocol specification

## Scope

This session turns the Phase 3 Stop/Go synthesis and Phase 4 symptom ontology
into a minimal method-validation protocol. It does not implement or train the
minimal model, and it explicitly keeps full method construction blocked.

## Current State

- Implemented `scripts/phase5_build_minimal_validation_protocol.py`.
- Generated `analysis/phase5_minimal_validation/` with:
  - six protocol rows;
  - seven required metric/diagnostic rows;
  - three output-policy rows;
  - a readiness audit with `full_method_allowed=false`;
  - artifact hygiene passing with zero violations.
- Recommended first runnable row is `P5_MV01`
  `phq_core_construct_bridge`, because E-DAIC PHQ-8 and CMDC PHQ-9 provide the
  cleanest item-level bridge for C01-C08.
- `P5_MV02` HAMD bridge is now complete as a PDCH-only diagnostic pass. CMDC
  HAMD remains limited to a 25-subject sanity subset and does not support
  transfer claims in the current frozen-feature contract.

## Key Decisions

- Minimal validation must use subject-level splits and existing audited/frozen
  feature contracts by default.
- Every pooled or cross-dataset claim must include dataset-stratified metrics
  and a dataset/protocol identity probe.
- Protocol/task/subgroup metrics are mandatory, not optional robustness
  appendices.
- Row-level predictions, learned embeddings, checkpoints, raw snippets, raw
  prompts, and raw model responses remain local-only unless separately reviewed.
- C09 death/self-harm remains explicit-evidence-only.
- MV02 should use PDCH subject-level folds for the first HAMD-17 auxiliary
  bridge and apply the official PDCH convention that HAMD item code `9` is
  excluded from total scoring.
- MV02 result: best PDCH item-derived total MAE was `5.693` versus train-mean
  items `6.183`, but CMDC sanity feature heads were worse than train mean.

## Files Owned Or Touched

- `scripts/phase5_build_minimal_validation_protocol.py`
- `analysis/phase5_minimal_validation/`
- `memory/sessions/session_07_phase5_minimal_validation_protocol.md`

## Generated Artifacts

Regeneration command:

```bash
python scripts/phase5_build_minimal_validation_protocol.py
```

Artifacts:

- `analysis/phase5_minimal_validation/minimal_validation_protocol.md`
- `analysis/phase5_minimal_validation/experiment_matrix.csv`
- `analysis/phase5_minimal_validation/metric_contract.csv`
- `analysis/phase5_minimal_validation/output_policy.csv`
- `analysis/phase5_minimal_validation/readiness_audit.json`

## Blockers And Risks

- The protocol is a planning contract. Only minimal-validation rows with
  audited scripts/results should be treated as evidence.
- Joint CMDC/PDCH HAMD claims remain blocked because CMDC has only 25 usable
  HAMD total+full-item subjects.
- If `P5_MV01` requires a new common text feature space, that feature
  extraction must be treated as a versioned feature-contract decision and large
  embeddings must stay local-only.

## Next Handoff

`P5_MV01`, `P5_MV02`, `P5_MV03`, `P5_MV04`, and `P5_MV05` have been
implemented or audited as minimal rows. `P5_MV06` readiness is complete and
can proceed only as a local raw-text annotation workflow with tracked aggregate
summaries. Continue identity/protocol-control validation, evidence-localization
annotation, or audited text-feature variants before any broad full-model
implementation.
