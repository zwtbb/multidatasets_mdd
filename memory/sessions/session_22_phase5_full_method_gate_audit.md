# Session Memory: Phase 5 Full-Method Gate Audit

Status: complete
Last updated: 2026-08-10 UTC
Thread/task: main agent Phase 5 claim/gate synthesis

## Scope

This session owns the Phase 5 full-method gate audit. It turns completed
minimal-validation rows into claim-level decisions about what the project can
and cannot claim before starting the full symptom-aligned method.

It does not train a model, modify raw data, inspect raw text/media, or replace
the numeric source artifacts from each MV row.

## Current State

- Implemented `scripts/phase5_full_method_gate_audit.py`.
- Generated `analysis/phase5_minimal_validation/full_method_gate_audit/`.
- The audit reads 21 Phase 5 run summaries:
  - MV01 PHQ bridge;
  - MV02 readiness, MV02 PDCH HAMD bridge, MV02b PDCH text probe;
  - MV03/MV03b EATD SDS audio/text stress;
  - MV04/MV04b/MV04c identity and protocol controls;
  - MV05 MPDD context calibration;
  - MV06 readiness, pilot, annotation workbench, annotation summary gate, and
    local AI preannotation triage;
  - MV06 human review pack;
  - MV07 E-DAIC BGE generation, shared-feature-contract readiness,
    aligned-BGE shallow shared-symptom validation, MV07b BGE
    identity-projection follow-up, and MV07c BGE total-anchor follow-up.
- Artifact hygiene passed with zero violations.

## Key Decisions

- Gate status: `blocked_but_publishable_diagnostic_direction`.
- `full_method_allowed=false`.
- Blocked claims:
  - starting the full M0/M1/M2/M3 symptom-aligned method;
  - claiming a transferable direct shared-symptom representation;
  - using EATD SDS total as positive external cross-scale evidence;
  - adding an EATD-driven valence-adversarial component;
  - claiming positive MPDD context conditioning/calibration.
- Allowed limited/reframed claims:
  - PDCH-only HAMD diagnostic evidence;
  - dataset/protocol identity controls as diagnostics;
  - MODMA task nuisance projection as bounded protocol-control evidence;
  - first-round aggregate MV06 evidence localization with dataset-stratified
    agreement;
  - a publishable diagnostic/audit-driven paper direction if claims are
    reframed away from broad SOTA/full-method claims.
- Ranked next actions:
  1. Audit and reduce public row-level manifest exposure before further GitHub
     publishing.
  2. Freeze shallow BGE/WavLM rows as negative/partial baselines and design the
     multi-scale psychometric partial-invariance measurement row.
  3. Use the dataset-stratified MV06 agreement summary as first-round RQ4
     evidence and optionally expand E-DAIC double annotation.
  4. Recover or create speaker/protocol labels for E-DAIC controls if feasible.
  5. Recover MPDD gender/health metadata and official test labels if available.

## Files Owned Or Touched

- `scripts/phase5_full_method_gate_audit.py`
- `analysis/phase5_minimal_validation/full_method_gate_audit/`
- `analysis/phase5_minimal_validation/p5_mv06_human_review_pack/`
- `MEMORY.md`
- `docs/master_experiment_plan.md`
- `docs/experiment_issue_log.md`
- `memory/sessions/session_master_orchestration.md`
- `memory/sessions/session_22_phase5_full_method_gate_audit.md`

## Generated Artifacts

Regeneration command:

```bash
python scripts/phase5_full_method_gate_audit.py
```

Versionable artifacts:

- `analysis/phase5_minimal_validation/full_method_gate_audit/report.md`
- `analysis/phase5_minimal_validation/full_method_gate_audit/run_summary.json`
- `analysis/phase5_minimal_validation/full_method_gate_audit/artifact_hygiene_audit.json`
- `analysis/phase5_minimal_validation/full_method_gate_audit/claim_gate.csv`
- `analysis/phase5_minimal_validation/full_method_gate_audit/evidence_inventory.csv`
- `analysis/phase5_minimal_validation/full_method_gate_audit/next_action_queue.csv`

## Blockers And Risks

- The audit is conservative and intentionally blocks full method construction
  while evidence remains mixed/negative.
- MV06 has first-round aggregate evidence, but E-DAIC has too few double pairs
  for stable dataset-specific kappa in this pass.
- Public row-level manifests were identified as a data-governance risk; latest
  tree mitigation can remove them, but remote history rewrite requires explicit
  user approval.
- A revised measurement contract must beat simple floors and preserve
  identity/protocol controls before broad cross-scale measurement claims.
- MV07 aligned-BGE shallow validation is blocked:
  `blocked_not_better_than_total_allocation_bge_contract`, with feature
  identity BA `1.000` and prediction identity BA `0.980`. eGeMAPS requires
  aligned regeneration, and WavLM requires stronger identity control.
- MV07b BGE identity projection reduces identity but remains partial:
  `partial_identity_reduced_not_total_floor_beating_bge_projection`. Best k=10
  reduced feature/prediction identity BA to `0.709`/`0.684`, but CMDC remains
  worse than total allocation by `0.018` Macro MAE.
- MV07c BGE total anchoring reduces prediction identity further to `0.664`, but
  remains blocked: `blocked_not_better_than_raw_total_allocation_bge_total_anchor`.
  CMDC is worse than raw total allocation by `0.012` Macro MAE and worse than
  projected total allocation by `0.002`.

## Next Handoff

Use the full-method gate audit as the authoritative Phase 5 claim boundary.
The next implementation session should handle public manifest governance, then
define a partial-invariance psychometric measurement row after reframing the
shallow BGE sequence as negative/partial evidence. Do not start the full method
until the gate changes from blocked.
