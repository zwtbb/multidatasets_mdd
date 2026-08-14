# P5_MV16 DIF-Guided Few-Shot Measurement Calibration

Generated: `2026-08-14T05:48:09+00:00`

## Scope

MV16 evaluates E-DAIC->CMDC and CMDC->E-DAIC PHQ calibration at k=0/5/10/20/40. It uses BGE feature caches, manifest PHQ labels, and local measurement scoring, and exports aggregate results only.

## Verdict

- Pass-rule status: `blocked_no_dif_guided_small_k_gain`.
- Full method allowed: `False`.
- DIF-guided small-k gate passed: `False`.
- Anchor safety gate passed: `True`.
- Direct-baseline gate passed: `True`.
- Output identity reported: `True`.
- Artifact hygiene passed: `True`.

MV16 completes the predeclared few-shot calibration ladder but does not satisfy the DIF-guided small-k mechanism gate; keep it as negative or bounded diagnostic evidence.

## Gate Summary

| gate | status | interpretation |
| --- | --- | --- |
| G1_input_scope | `pass` | Runner used manifest-governed PHQ labels and BGE feature caches only. |
| G2_subject_level_fewshot_splits | `pass` | All source/calibration/evaluation overlap counts are zero. |
| G3_ladder_completeness | `pass` | All L0-L6 rows are complete where feasible; k=0 target-label rows are explicitly skipped. |
| G4_dif_guided_small_k_gain | `fail` | Requires L3 or L4 theta gain >=0.03 vs L0 and C02/C06 gain vs L1 in both directions for k<=20. |
| G5_anchor_safety | `pass` | L3/L4 anchor MAE must not degrade more than 5 percent versus L1. |
| G6_dimension_matched_baseline | `pass` | Direct B2/L6 baselines do not dominate every preferred DIF-guided row on both theta and observed MAE. |
| G7_identity_boundary | `pass` | Output identity BA is reported separately from upstream BGE feature invariance. |
| G8_artifact_hygiene | `pass` | Tracked outputs are aggregate-only and pass the hygiene scanner. |

## Key Calibration Rows

| direction | k | model | theta MAE | delta theta vs L0 | C02/C06 MAE | delta C02/C06 vs L1 | anchor rel change | observed macro MAE |
| --- | ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| D1_edaic_source_cmdc_target | 0 | M16_B0_zero_shot_source | 1.093 | 0.000 | 0.779 | NA | NA | 0.765 |
| D1_edaic_source_cmdc_target | 5 | M16_B0_zero_shot_source | 1.093 | 0.000 | 0.779 | -0.330 | -0.285 | 0.765 |
| D1_edaic_source_cmdc_target | 5 | M16_B2_direct_itemwise_target | 0.838 | -0.256 | 0.849 | -0.260 | -0.227 | 0.835 |
| D1_edaic_source_cmdc_target | 5 | M16a_global_affine | 1.543 | 0.450 | 1.109 | 0.000 | 0.000 | 1.076 |
| D1_edaic_source_cmdc_target | 5 | M16c_dif_guided_C02_C06 | 1.093 | 0.000 | 0.925 | -0.184 | -0.285 | 0.801 |
| D1_edaic_source_cmdc_target | 5 | M16d_global_plus_C02_C06 | 1.543 | 0.450 | 1.064 | -0.045 | 0.000 | 1.064 |
| D1_edaic_source_cmdc_target | 5 | M16f_direct_target_theta | 0.846 | -0.247 | 0.761 | -0.348 | -0.255 | 0.774 |
| D1_edaic_source_cmdc_target | 10 | M16_B0_zero_shot_source | 1.093 | 0.000 | 0.779 | -0.110 | -0.123 | 0.765 |
| D1_edaic_source_cmdc_target | 10 | M16_B2_direct_itemwise_target | 0.756 | -0.338 | 0.799 | -0.090 | -0.085 | 0.812 |
| D1_edaic_source_cmdc_target | 10 | M16a_global_affine | 0.868 | -0.225 | 0.889 | 0.000 | 0.000 | 0.881 |
| D1_edaic_source_cmdc_target | 10 | M16c_dif_guided_C02_C06 | 1.093 | 0.000 | 0.925 | 0.036 | -0.123 | 0.801 |
| D1_edaic_source_cmdc_target | 10 | M16d_global_plus_C02_C06 | 0.868 | -0.225 | 0.871 | -0.018 | 0.000 | 0.876 |
| D1_edaic_source_cmdc_target | 10 | M16f_direct_target_theta | 0.760 | -0.333 | 0.699 | -0.190 | -0.117 | 0.749 |
| D1_edaic_source_cmdc_target | 20 | M16_B0_zero_shot_source | 1.093 | 0.000 | 0.779 | -0.135 | -0.117 | 0.765 |
| D1_edaic_source_cmdc_target | 20 | M16_B2_direct_itemwise_target | 0.684 | -0.409 | 0.773 | -0.141 | -0.151 | 0.755 |
| D1_edaic_source_cmdc_target | 20 | M16a_global_affine | 0.867 | -0.227 | 0.914 | 0.000 | 0.000 | 0.871 |
| D1_edaic_source_cmdc_target | 20 | M16c_dif_guided_C02_C06 | 1.093 | 0.000 | 0.874 | -0.040 | -0.117 | 0.789 |
| D1_edaic_source_cmdc_target | 20 | M16d_global_plus_C02_C06 | 0.867 | -0.227 | 0.901 | -0.014 | 0.000 | 0.868 |
| D1_edaic_source_cmdc_target | 20 | M16f_direct_target_theta | 0.763 | -0.330 | 0.716 | -0.198 | -0.157 | 0.721 |
| D2_cmdc_source_edaic_target | 0 | M16_B0_zero_shot_source | 0.801 | 0.000 | 0.766 | NA | NA | 0.752 |
| D2_cmdc_source_edaic_target | 5 | M16_B0_zero_shot_source | 0.801 | 0.000 | 0.766 | -0.053 | -0.071 | 0.752 |
| D2_cmdc_source_edaic_target | 5 | M16_B2_direct_itemwise_target | 0.890 | 0.089 | 0.786 | -0.033 | -0.042 | 0.784 |
| D2_cmdc_source_edaic_target | 5 | M16a_global_affine | 0.928 | 0.127 | 0.819 | 0.000 | 0.000 | 0.808 |
| D2_cmdc_source_edaic_target | 5 | M16c_dif_guided_C02_C06 | 0.801 | 0.000 | 0.745 | -0.074 | -0.071 | 0.746 |
| D2_cmdc_source_edaic_target | 5 | M16d_global_plus_C02_C06 | 0.928 | 0.127 | 0.803 | -0.016 | 0.000 | 0.804 |
| D2_cmdc_source_edaic_target | 5 | M16f_direct_target_theta | 0.904 | 0.103 | 0.773 | -0.046 | -0.076 | 0.755 |
| D2_cmdc_source_edaic_target | 10 | M16_B0_zero_shot_source | 0.801 | 0.000 | 0.766 | -0.024 | -0.021 | 0.752 |
| D2_cmdc_source_edaic_target | 10 | M16_B2_direct_itemwise_target | 0.858 | 0.057 | 0.801 | 0.011 | 0.046 | 0.811 |
| D2_cmdc_source_edaic_target | 10 | M16a_global_affine | 0.871 | 0.070 | 0.790 | 0.000 | 0.000 | 0.770 |
| D2_cmdc_source_edaic_target | 10 | M16c_dif_guided_C02_C06 | 0.801 | 0.000 | 0.739 | -0.051 | -0.021 | 0.745 |
| D2_cmdc_source_edaic_target | 10 | M16d_global_plus_C02_C06 | 0.871 | 0.070 | 0.861 | 0.071 | 0.000 | 0.788 |
| D2_cmdc_source_edaic_target | 10 | M16f_direct_target_theta | 0.860 | 0.059 | 0.787 | -0.003 | -0.031 | 0.761 |
| D2_cmdc_source_edaic_target | 20 | M16_B0_zero_shot_source | 0.801 | 0.000 | 0.766 | 0.033 | 0.038 | 0.752 |
| D2_cmdc_source_edaic_target | 20 | M16_B2_direct_itemwise_target | 0.769 | -0.032 | 0.724 | -0.009 | 0.001 | 0.737 |
| D2_cmdc_source_edaic_target | 20 | M16a_global_affine | 0.788 | -0.013 | 0.733 | 0.000 | 0.000 | 0.725 |
| D2_cmdc_source_edaic_target | 20 | M16c_dif_guided_C02_C06 | 0.801 | 0.000 | 0.738 | 0.005 | 0.038 | 0.745 |
| D2_cmdc_source_edaic_target | 20 | M16d_global_plus_C02_C06 | 0.788 | -0.013 | 0.783 | 0.050 | 0.000 | 0.738 |
| D2_cmdc_source_edaic_target | 20 | M16f_direct_target_theta | 0.786 | -0.015 | 0.722 | -0.012 | -0.052 | 0.701 |

## Output Identity

| k | model | output identity BA | seeds |
| ---: | --- | ---: | ---: |
| 0 | M16_B0_zero_shot_source | 0.993 | 5 |
| 5 | M16_B0_zero_shot_source | 0.993 | 5 |
| 5 | M16_B2_direct_itemwise_target | 0.988 | 5 |
| 5 | M16c_dif_guided_C02_C06 | 0.993 | 5 |
| 5 | M16d_global_plus_C02_C06 | 0.963 | 5 |
| 5 | M16f_direct_target_theta | 0.998 | 5 |
| 10 | M16_B0_zero_shot_source | 0.993 | 5 |
| 10 | M16_B2_direct_itemwise_target | 0.969 | 5 |
| 10 | M16c_dif_guided_C02_C06 | 0.993 | 5 |
| 10 | M16d_global_plus_C02_C06 | 0.998 | 5 |
| 10 | M16f_direct_target_theta | 0.993 | 5 |
| 20 | M16_B0_zero_shot_source | 0.993 | 5 |
| 20 | M16_B2_direct_itemwise_target | 0.975 | 5 |
| 20 | M16c_dif_guided_C02_C06 | 0.993 | 5 |
| 20 | M16d_global_plus_C02_C06 | 0.992 | 5 |
| 20 | M16f_direct_target_theta | 0.995 | 5 |
| 40 | M16_B0_zero_shot_source | 0.993 | 5 |
| 40 | M16_B2_direct_itemwise_target | 0.950 | 5 |
| 40 | M16c_dif_guided_C02_C06 | 0.993 | 5 |
| 40 | M16d_global_plus_C02_C06 | 1.000 | 5 |
| 40 | M16f_direct_target_theta | 0.987 | 5 |

## Boundary

MV16 may update target-measurement calibration evidence only. It must not be described as BGE feature invariance, external HAMD transfer, or authorization to start the full M0/M1/M2/M3 method.
