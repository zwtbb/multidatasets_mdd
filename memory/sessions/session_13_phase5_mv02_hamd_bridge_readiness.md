# Session Memory: Phase 5 MV02 HAMD Bridge Readiness

Status: complete
Last updated: 2026-08-09 UTC
Thread/task: main agent MV02 readiness audit

## Scope

This session audits whether `P5_MV02 hamd17_auxiliary_bridge` can start from
current manifests and cached frozen features. It does not train a model, write
subject-level labels, export predictions, or change raw data.

## Current State

- Implemented `scripts/phase5_audit_mv02_hamd_bridge_inputs.py`.
- Generated
  `analysis/phase5_minimal_validation/p5_mv02_hamd_bridge_readiness/`.
- CMDC has 78 manifest subjects, but only 25 subjects have valid HAMD total
  plus full HAMD-17 item payloads after placeholder NaN item payloads are
  filtered. Those 25 have no item-total scoring mismatch.
- PDCH has 100 manifest subjects, 99 HAMD total+full-item subjects, and
  subject `034A` remains missing HAMD annotation.
- PDCH has 7 subjects with HAMD item code `9`. Raw item sums are `+9` above
  manifest totals for those subjects, but official PDCH scoring treats `9` as
  not sure/not applicable and excludes it from total scoring, so scored item
  sums match manifest totals for 99/99 labeled subjects.
- Cached reusable subject-level feature families are available for both PDCH
  and the limited CMDC subset: BGE text, WavLM audio, and eGeMAPS audio.
- Artifact hygiene passed with zero violations.

## Key Decisions

- `P5_MV02` is now `ready_pdch_only_mode`.
- First MV02 run should use PDCH subject-level folds as the main HAMD-17
  auxiliary bridge experiment.
- CMDC HAMD may be used only as a small 25-subject sanity subset or reported as
  limited coverage, not as a broad joint HAMD bridge.
- Use manifest HAMD total as the primary severity target. When deriving totals
  from item heads, apply the official PDCH `9 -> 0 for total` scoring
  convention.
- Full-method construction remains blocked; this audit only opens a bounded
  minimal-validation row.
- The bounded MV02 row was implemented later in
  `memory/sessions/session_14_phase5_mv02_hamd_auxiliary_bridge.md`.

## Files Owned Or Touched

- `scripts/phase5_audit_mv02_hamd_bridge_inputs.py`
- `scripts/phase4_build_symptom_ontology.py`
- `scripts/phase5_build_minimal_validation_protocol.py`
- `analysis/phase4_symptom_ontology/`
- `analysis/phase5_minimal_validation/`
- `memory/sessions/session_13_phase5_mv02_hamd_bridge_readiness.md`
- `MEMORY.md`
- `docs/experiment_issue_log.md`

## Generated Artifacts

Regeneration commands:

```bash
python scripts/phase4_build_symptom_ontology.py
python scripts/phase5_build_minimal_validation_protocol.py
python scripts/phase5_audit_mv02_hamd_bridge_inputs.py
```

Artifacts:

- `analysis/phase5_minimal_validation/p5_mv02_hamd_bridge_readiness/report.md`
- `analysis/phase5_minimal_validation/p5_mv02_hamd_bridge_readiness/run_summary.json`
- `analysis/phase5_minimal_validation/p5_mv02_hamd_bridge_readiness/artifact_hygiene_audit.json`
- `analysis/phase5_minimal_validation/p5_mv02_hamd_bridge_readiness/hamd_label_coverage.csv`
- `analysis/phase5_minimal_validation/p5_mv02_hamd_bridge_readiness/hamd_total_item_consistency.csv`
- `analysis/phase5_minimal_validation/p5_mv02_hamd_bridge_readiness/feature_availability.csv`
- `analysis/phase5_minimal_validation/p5_mv02_hamd_bridge_readiness/readiness_decision.csv`

## Blockers And Risks

- MV02 is ready only in PDCH-only mode; complete CMDC/PDCH HAMD bridge claims
  remain unsupported because CMDC HAMD coverage is 25/78 subjects.
- PDCH code `9` must be handled consistently in item-derived total scoring.
- The audit reused Phase 2 feature caches but did not stage generated Phase 2
  baseline artifacts; those remain local-only by policy.

## Next Handoff

The MV02 run is complete in
`analysis/phase5_minimal_validation/p5_mv02_hamd_auxiliary_bridge/`. Continue
from `session_14_phase5_mv02_hamd_auxiliary_bridge.md` for result-level
interpretation and next steps.
