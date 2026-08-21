# P5 MV17a Multilingual Feature Contract Sensitivity

Generated: `2026-08-21T18:03:31+00:00`

## Scope

MV17a regenerates the shared text-feature contract with multilingual encoders and reruns only MV07, MV12, and MV15. MV16 remains paused until this sensitivity chain is reviewed.

## Feature Contract

| encoder | model | pooling | prefix | max length | dimensions |
| --- | --- | --- | --- | ---: | ---: |
| bge_m3 | BAAI/bge-m3 | cls | False | 512 | 1024 |
| multilingual_e5_base | intfloat/multilingual-e5-base | average | True | 512 | 768 |

## Feature Coverage

| encoder | dataset | rows | dimensions | text units | chunks | status |
| --- | --- | ---: | ---: | ---: | ---: | --- |
| bge_m3 | cmdc | 77 | 1024 | 908 | 913 | generated |
| bge_m3 | edaic | 219 | 1024 | 219 | 795 | cache_complete |
| bge_m3 | pdch | 99 | 1024 | 165 | 980 | generated |
| multilingual_e5_base | cmdc | 77 | 768 | 908 | 913 | generated |
| multilingual_e5_base | edaic | 219 | 768 | 219 | 797 | generated |
| multilingual_e5_base | pdch | 99 | 768 | 165 | 987 | generated |

## Downstream Chain

| encoder | experiment | status | pass rule | hygiene |
| --- | --- | --- | --- | --- |
| bge_m3 | mv07 | complete | blocked_not_better_than_total_allocation_bge_contract | True |
| bge_m3 | mv12 | complete | blocked_theta_gain_not_observed_scale_safe | True |
| bge_m3 | mv15 | complete | blocked_theta_conditioned_feature_identity_high | True |
| multilingual_e5_base | mv07 | complete | blocked_not_better_than_total_allocation_bge_contract | True |
| multilingual_e5_base | mv12 | complete | blocked_theta_gain_not_observed_scale_safe | True |
| multilingual_e5_base | mv15 | complete | blocked_theta_conditioned_feature_identity_high | True |

## Output Boundary

- Feature caches stay under ignored Phase 2 local artifacts.
- Tracked outputs contain aggregate coverage, contracts, downstream status, and hygiene only.
- Clinical content, source locators, row predictions, learned parameters, and embedding matrices are not tracked.

## Decision

- Status: `complete`.
- Artifact hygiene passed: `True`.
- Downstream chain executed: `True`.
