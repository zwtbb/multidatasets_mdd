# P5 MV29 PHQ Measurement Sensitivity

Generated: `2026-09-02T17:22:06+00:00`

## Scope

MV29 checks whether the E-DAIC/CMDC PHQ anchor and threshold-shift interpretation depends on one hand-picked heuristic threshold. It reads only MV10 and MV14 aggregate outputs.

## Anchor Grid

| loading tol | threshold tol | min anchors | anchor count | anchor set | C02/C06 retained as threshold-shift | pass |
| ---: | ---: | ---: | ---: | --- | --- | --- |
| 0.150 | 0.250 | 3 | 1 | C07 | yes | no |
| 0.150 | 0.250 | 4 | 1 | C07 | yes | no |
| 0.150 | 0.250 | 5 | 1 | C07 | yes | no |
| 0.150 | 0.350 | 3 | 4 | C01;C04;C05;C07 | yes | yes |
| 0.150 | 0.350 | 4 | 4 | C01;C04;C05;C07 | yes | yes |
| 0.150 | 0.350 | 5 | 4 | C01;C04;C05;C07 | yes | no |
| 0.150 | 0.450 | 3 | 5 | C01;C03;C04;C05;C07 | yes | yes |
| 0.150 | 0.450 | 4 | 5 | C01;C03;C04;C05;C07 | yes | yes |
| 0.150 | 0.450 | 5 | 5 | C01;C03;C04;C05;C07 | yes | yes |
| 0.200 | 0.250 | 3 | 1 | C07 | yes | no |
| 0.200 | 0.250 | 4 | 1 | C07 | yes | no |
| 0.200 | 0.250 | 5 | 1 | C07 | yes | no |
| 0.200 | 0.350 | 3 | 4 | C01;C04;C05;C07 | yes | yes |
| 0.200 | 0.350 | 4 | 4 | C01;C04;C05;C07 | yes | yes |
| 0.200 | 0.350 | 5 | 4 | C01;C04;C05;C07 | yes | no |
| 0.200 | 0.450 | 3 | 5 | C01;C03;C04;C05;C07 | yes | yes |
| 0.200 | 0.450 | 4 | 5 | C01;C03;C04;C05;C07 | yes | yes |
| 0.200 | 0.450 | 5 | 5 | C01;C03;C04;C05;C07 | yes | yes |
| 0.250 | 0.250 | 3 | 1 | C07 | yes | no |
| 0.250 | 0.250 | 4 | 1 | C07 | yes | no |
| 0.250 | 0.250 | 5 | 1 | C07 | yes | no |
| 0.250 | 0.350 | 3 | 4 | C01;C04;C05;C07 | yes | yes |
| 0.250 | 0.350 | 4 | 4 | C01;C04;C05;C07 | yes | yes |
| 0.250 | 0.350 | 5 | 4 | C01;C04;C05;C07 | yes | no |
| 0.250 | 0.450 | 3 | 5 | C01;C03;C04;C05;C07 | yes | yes |
| 0.250 | 0.450 | 4 | 5 | C01;C03;C04;C05;C07 | yes | yes |
| 0.250 | 0.450 | 5 | 5 | C01;C03;C04;C05;C07 | yes | yes |

## Item-Level Robustness

| item | MV10 role | grid anchor freq | grid threshold-free freq | MV14 threshold DIF freq | MV14 anchor support | min category count | reading |
| --- | --- | ---: | ---: | ---: | ---: | ---: | --- |
| C01 | anchor_candidate | 0.667 | 0.333 | 0.000 [0.000, 0.037] | 0.959 [0.900, 0.984] | 8 | stable anchor with strict-threshold caveat |
| C02 | metric_only_threshold_free | 0.000 | 1.000 | 0.800 [0.711, 0.867] | 0.143 [0.082, 0.238] | 8 | stable threshold-shift signal |
| C03 | metric_only_threshold_free | 0.333 | 0.667 | 0.020 [0.006, 0.070] | 0.980 [0.929, 0.994] | 9 | tolerance-sensitive item |
| C04 | anchor_candidate | 0.667 | 0.333 | 0.030 [0.010, 0.085] | 0.939 [0.873, 0.972] | 8 | stable anchor with strict-threshold caveat |
| C05 | anchor_candidate | 0.667 | 0.333 | 0.020 [0.006, 0.070] | 0.969 [0.913, 0.989] | 8 | stable anchor with strict-threshold caveat |
| C06 | metric_only_threshold_free | 0.000 | 1.000 | 0.740 [0.646, 0.816] | 0.268 [0.190, 0.364] | 3 | stable threshold-shift signal |
| C07 | anchor_candidate | 1.000 | 0.000 | 0.000 [0.000, 0.037] | 0.969 [0.912, 0.989] | 6 | stable anchor with strict-threshold caveat |
| C08 | free_loading_or_threshold | 0.000 | 0.333 | 0.020 [0.006, 0.070] | 0.796 [0.706, 0.864] | 4 | unstable or free item |

## Interpretation Handle

Gate status: `supports_bounded_anchor_shift_interpretation`.

The default anchors are exact in 0.33 of tolerance-grid rows, while C02/C06 remain threshold-free in 1.00 of rows. MV14 bootstrap support identifies stable anchors C01;C04;C05;C07 and stable threshold-shift signals C02;C06. This supports bounded item-level target-contract heterogeneity, with category-sparsity and MV19 finite-sample limits still foregrounded.

Use this as sensitivity support for a bounded measurement-validity claim. It does not remove the observed-N finite-sample caveat from MV19.
