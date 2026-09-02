# P5 MV24 Measurement-Head DIF Simulation

Generated: `2026-09-02T02:20:17+00:00`

## Scope

This companion simulation fixes the latent input seen by the measurement head and compares a shared ordinal head against a corpus-specific ordinal threshold-offset head. It is designed to isolate measurement parameterization from representation adaptation.

## Observed MV24 Input Boundary

| dataset | scale | n | default n_cal | default n_eval | mean total | sd total |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| edaic | PHQ-8 | 219 | 66 | 153 | 6.639 | 6.000 |
| cmdc | PHQ-9 | 44 | 24 | 20 | 7.455 | 7.556 |

## Head Comparison

Positive delta means the corpus-specific ordinal head has lower item MAE than the shared ordinal head.

**H0_scalar_invariant.**

CMDC -> E-DAIC; n_cal=66, n_eval=153.

| item set | role | shared ordinal MAE | corpus-specific ordinal MAE | delta shared - corpus-specific | corpus-specific lower-error draws |
| --- | --- | ---: | ---: | ---: | ---: |
| C01-C08 | all shared PHQ items | 0.417 [0.415, 0.418] | 0.418 [0.416, 0.419] | -0.001 [-0.001, -0.000] | 207/500 |
| C01/C04/C05/C07 | measurement-gate anchor items | 0.418 [0.417, 0.420] | 0.419 [0.418, 0.421] | -0.001 [-0.001, -0.000] | 218/500 |
| C02/C06 | measurement-gate threshold-shift items | 0.413 [0.411, 0.415] | 0.414 [0.411, 0.416] | -0.001 [-0.002, -0.000] | 231/500 |
| C02 | threshold_shift | 0.380 [0.377, 0.383] | 0.381 [0.378, 0.385] | -0.001 [-0.002, -0.000] | 244/500 |
| C06 | threshold_shift | 0.446 [0.442, 0.449] | 0.446 [0.443, 0.450] | -0.001 [-0.002, 0.000] | 237/500 |

E-DAIC -> CMDC; n_cal=24, n_eval=20.

| item set | role | shared ordinal MAE | corpus-specific ordinal MAE | delta shared - corpus-specific | corpus-specific lower-error draws |
| --- | --- | ---: | ---: | ---: | ---: |
| C01-C08 | all shared PHQ items | 0.398 [0.394, 0.401] | 0.411 [0.407, 0.414] | -0.013 [-0.015, -0.012] | 91/500 |
| C01/C04/C05/C07 | measurement-gate anchor items | 0.395 [0.391, 0.399] | 0.408 [0.404, 0.412] | -0.013 [-0.015, -0.011] | 138/500 |
| C02/C06 | measurement-gate threshold-shift items | 0.398 [0.392, 0.403] | 0.411 [0.405, 0.417] | -0.013 [-0.016, -0.010] | 179/500 |
| C02 | threshold_shift | 0.382 [0.375, 0.389] | 0.397 [0.389, 0.405] | -0.015 [-0.019, -0.011] | 212/500 |
| C06 | threshold_shift | 0.414 [0.407, 0.421] | 0.424 [0.416, 0.433] | -0.010 [-0.014, -0.007] | 208/500 |

**H1_C02_C06_threshold_DIF.**

CMDC -> E-DAIC; n_cal=66, n_eval=153.

| item set | role | shared ordinal MAE | corpus-specific ordinal MAE | delta shared - corpus-specific | corpus-specific lower-error draws |
| --- | --- | ---: | ---: | ---: | ---: |
| C01-C08 | all shared PHQ items | 0.415 [0.413, 0.416] | 0.415 [0.413, 0.416] | 0.000 [-0.000, 0.000] | 252/500 |
| C01/C04/C05/C07 | measurement-gate anchor items | 0.417 [0.415, 0.418] | 0.417 [0.415, 0.419] | -0.001 [-0.001, -0.000] | 222/500 |
| C02/C06 | measurement-gate threshold-shift items | 0.411 [0.409, 0.414] | 0.409 [0.407, 0.411] | 0.002 [0.001, 0.003] | 301/500 |
| C02 | threshold_shift | 0.386 [0.383, 0.389] | 0.377 [0.374, 0.379] | 0.010 [0.008, 0.011] | 390/500 |
| C06 | threshold_shift | 0.437 [0.433, 0.440] | 0.442 [0.438, 0.445] | -0.005 [-0.006, -0.004] | 171/500 |

E-DAIC -> CMDC; n_cal=24, n_eval=20.

| item set | role | shared ordinal MAE | corpus-specific ordinal MAE | delta shared - corpus-specific | corpus-specific lower-error draws |
| --- | --- | ---: | ---: | ---: | ---: |
| C01-C08 | all shared PHQ items | 0.395 [0.392, 0.399] | 0.401 [0.398, 0.405] | -0.006 [-0.008, -0.005] | 178/500 |
| C01/C04/C05/C07 | measurement-gate anchor items | 0.391 [0.387, 0.395] | 0.402 [0.398, 0.407] | -0.011 [-0.013, -0.009] | 139/500 |
| C02/C06 | measurement-gate threshold-shift items | 0.401 [0.395, 0.406] | 0.390 [0.384, 0.396] | 0.011 [0.008, 0.014] | 311/500 |
| C02 | threshold_shift | 0.408 [0.401, 0.416] | 0.418 [0.410, 0.426] | -0.010 [-0.014, -0.005] | 218/500 |
| C06 | threshold_shift | 0.393 [0.387, 0.400] | 0.362 [0.354, 0.369] | 0.032 [0.027, 0.037] | 369/500 |

## Recommendations

| recommendation | status | evidence |
| --- | --- | --- |
| mechanism_sanity_check | `weak_item_local_mechanism_consistent_but_small` | H0 max abs C02/C06-set delta=0.013; H1 min C02/C06-set delta=0.002; H1 min lower-error rate=0.602. |
| real_data_claim_boundary | `keep_bounded` | This simulation fixes the latent input and plants a known response-process shift; real MV24 still estimates latent representations from frozen multimodal features. |
| paper_positioning | `framework_instantiation_not_sota_claim` | The intended claim is audit-to-model coherence, not universal architecture superiority. |

## Interpretation Boundary

- This simulation may support the conceptual link between threshold-DIF audits and corpus-specific measurement heads when the response-process shift is known.
- It does not overturn MV24's real-data result: the shared ordinal head and corpus-specific measurement-aware head are nearly tied on overall and C02/C06 item-set MAE.
- It does not test feature invariance, target-supervised representation adaptation, or clinical endpoint superiority.
