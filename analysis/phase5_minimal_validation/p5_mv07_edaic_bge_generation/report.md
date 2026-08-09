# P5 MV07 E-DAIC BGE Feature Generation

Generated: `2026-08-09T08:48:04+00:00`

## Scope

This step generates the local-only E-DAIC subject-level BGE cache needed by the MV07 aligned text contract. It is not a model-training run.

## Decision

- Status: `complete_local_feature_cache_generated`.
- Model: `BAAI/bge-small-zh-v1.5`.
- Feature subjects: `219`.
- Model input columns: `512`.
- Subject-overlap violations: `0`.
- Artifact hygiene passed: `True`.

## Output Boundary

- The generated BGE cache is local-only and ignored by Git.
- Tracked outputs contain only aggregate coverage, run summary, artifact manifest, and hygiene audit.
- No transcript text, source locators, row predictions, learned weights, or model responses are written to tracked outputs.

## Next Handoff

Rerun MV07 readiness. If the BGE contract becomes ready, run the shallow shared-symptom MV07 validation row with identity/protocol probes and local-only predictions.
