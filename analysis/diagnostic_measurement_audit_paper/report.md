# Diagnostic Measurement-Audit Paper Tables

Generated: `2026-08-11T13:28:34+00:00`

## Scope

This writing-prep artifact converts existing aggregate gates into paper-facing claim, evidence, and positioning tables. It does not read private review material or row-level model outputs.

## Claim Boundary

- Allowed or reframed claim rows: `5`.
- Blocked claim rows: `5`.
- Key finding rows: `7`.
- Literature-positioning rows: `12`.
- Artifact hygiene passed: `True`.

## Key Findings

| finding | interpretation |
| --- | --- |
| Full gate reads 27 Phase 5 summaries; status blocked_but_publishable_diagnostic_direction; full_method_allowed=False. | Full method construction remains blocked; measurement-shift paper framing is allowed with bounded claims. |
| MV08 improves over total-score floor on 0/3 pooled active slices with prediction identity BA 0.900. MV08b improves over both floors on 2/3 slices, but prediction identity BA 0.979 exceeds gate 0.900. MV09 revises the gate semantics: E-DAIC/CMDC item-conditioned feature identity BA remains 0.991. | Partial-invariance and residual measurement are diagnostic negative evidence under current features. |
| MV09 conditional identity audit: E-DAIC/CMDC raw BA 1.000, PHQ-item residualized BA 0.991; CMDC/PDCH severity-residualized BA 1.000; three-way severity-residualized BA 1.000. | Unconditional identity should not be the only hard gate, but conditional BGE identity remains high enough to block a shared-latent claim. |
| PDCH item-derived total MAE 5.693; direct total MAE 5.794; macro item MAE 0.727; status pass_pdch_only_diagnostic. | PDCH supports bounded internal HAMD measurement evidence only. |
| MODMA task projection reduces feature task identity BA 0.762 -> 0.570 while preserving main task signal (0.688). | MODMA provides bounded task-control evidence. |
| EATD valence/SDS remains blocked: raw primary MAE 28.810 versus train-mean floor 7.201; status blocked_main_task_below_floor. | EATD should remain a negative stress test, not a method component driver. |
| MV06 has 30 completed and 20 double-annotated candidates. Evidence-presence kappa: ALL 0.808 (20 pairs), CMDC 0.643 (10), PDCH 1.000 (8), E-DAIC NA (2, degenerate/underpowered if NA). | MV06 can support first-round aggregate credibility; E-DAIC agreement needs strengthening for stronger claims. |

## Release Rule

- Use these tables as manuscript scaffolding, not as a replacement for the source artifacts.
- Keep private review material, learned parameters, and row-level model outputs local-only.
- Any stronger RQ4 claim should first improve E-DAIC double-annotation agreement stability.
