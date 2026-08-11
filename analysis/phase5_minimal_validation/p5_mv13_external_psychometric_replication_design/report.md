# P5 MV13 External Psychometric Replication Design

Generated: `2026-08-11T16:35:31+00:00`

## Decision

- Design status: `ready_for_external_replication_run`.
- External runtime ready: `True`.
- Artifact hygiene passed: `True`.
- MV13 is an external replication contract, not a new psychometric result.

## Runtime Preflight

| check | status | observed |
| --- | --- | --- |
| Rscript_on_path | `pass` | available |
| mirt_package | `pass` | 1.35.1 |
| lavaan_package | `pass` | 0.6.10 |
| external_runtime_ready | `pass` | ready |

## Claim Boundary

MV13 should strengthen or downgrade the MV10/MV11 measurement evidence, not authorize the full multimodal method by itself. A successful external replication means the qualitative conclusion holds in a mature external workflow: broad one-factor/metric PHQ structure, partial threshold/scalar equivalence, and broadly preserved anchors with model-selection caveats.

## Next Step

Prepare the external R/mirt runtime, then implement the execution runner against this contract. Keep local R inputs, fitted objects, full parameter tables, theta scores, and participant-grain rows local-only.
