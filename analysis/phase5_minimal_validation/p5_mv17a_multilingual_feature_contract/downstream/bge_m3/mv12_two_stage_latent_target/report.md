# P5_MV12 Two-Stage Latent-Target Validation

Generated: `2026-08-21T18:01:23+00:00`

## Scope

MV12 fits label-only PHQ theta targets locally, trains shallow BGE X-to-theta predictors, compares direct/floor baselines, and exports aggregate diagnostics only.

## Verdict

- Pass-rule status: `blocked_theta_gain_not_observed_scale_safe`.
- Same-dataset theta gate passed: `True`.
- Same-dataset observed-scale gate passed: `False`.
- External theta transfer gate passed: `True`.
- External observed-scale transfer gate passed: `True`.
- Conditional identity BA for M12a: `0.495`.
- Conditional identity improved versus MV09: `True`.
- Preferred conditional identity threshold passed: `True`.
- Leakage gate passed: `True`.
- Artifact hygiene passed: `True`.

MV12 runs the predeclared two-stage PHQ latent-target test. A pass requires theta utility, observed-scale safety, external transfer, conditional shared-latent identity, leakage control, and artifact hygiene; design or same-dataset gains alone are not enough.

## Key Comparisons

| protocol | dataset | model | theta MAE | delta theta vs B0 | observed macro MAE | delta observed vs B3 | observed total MAE |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: |
| cmdc_subject_cv_phq | cmdc | B0_train_mean_theta | 0.805 | 0.000 | 0.848 | 0.234 | 6.229 |
| cmdc_subject_cv_phq | cmdc | B1_train_mean_observed_total | 0.805 | 0.000 | 0.848 | 0.234 | 6.229 |
| cmdc_subject_cv_phq | cmdc | B2_direct_total_allocation_ridge | 0.589 | -0.216 | 0.626 | 0.012 | 3.682 |
| cmdc_subject_cv_phq | cmdc | B3_direct_itemwise_ridge | 0.590 | -0.215 | 0.614 | 0.000 | 3.452 |
| cmdc_subject_cv_phq | cmdc | M12a_BGE_Ridge_X_to_theta | 0.612 | -0.193 | 0.661 | 0.047 | 4.008 |
| cross_cmdc_to_edaic_phq | edaic | B0_train_mean_theta | 0.692 | 0.000 | 0.743 | -0.065 | 4.742 |
| cross_cmdc_to_edaic_phq | edaic | B1_train_mean_observed_total | 0.692 | 0.000 | 0.743 | -0.065 | 4.742 |
| cross_cmdc_to_edaic_phq | edaic | B2_direct_total_allocation_ridge | 0.652 | -0.040 | 0.713 | -0.095 | 4.400 |
| cross_cmdc_to_edaic_phq | edaic | B3_direct_itemwise_ridge | 0.733 | 0.041 | 0.807 | 0.000 | 4.688 |
| cross_cmdc_to_edaic_phq | edaic | M12a_BGE_Ridge_X_to_theta | 0.670 | -0.022 | 0.754 | -0.053 | 4.690 |
| cross_edaic_to_cmdc_phq | cmdc | B0_train_mean_theta | 0.965 | 0.000 | 0.865 | -0.011 | 6.415 |
| cross_edaic_to_cmdc_phq | cmdc | B1_train_mean_observed_total | 0.965 | 0.000 | 0.865 | -0.011 | 6.415 |
| cross_edaic_to_cmdc_phq | cmdc | B2_direct_total_allocation_ridge | 0.914 | -0.051 | 0.874 | -0.002 | 6.126 |
| cross_edaic_to_cmdc_phq | cmdc | B3_direct_itemwise_ridge | 0.987 | 0.022 | 0.876 | 0.000 | 6.131 |
| cross_edaic_to_cmdc_phq | cmdc | M12a_BGE_Ridge_X_to_theta | 0.998 | 0.033 | 0.931 | 0.054 | 6.629 |
| edaic_same_dataset_phq | edaic | B0_train_mean_theta | 0.813 | 0.000 | 0.735 | 0.017 | 4.780 |
| edaic_same_dataset_phq | edaic | B1_train_mean_observed_total | 0.813 | 0.000 | 0.735 | 0.017 | 4.780 |
| edaic_same_dataset_phq | edaic | B2_direct_total_allocation_ridge | 0.719 | -0.095 | 0.698 | -0.020 | 4.223 |
| edaic_same_dataset_phq | edaic | B3_direct_itemwise_ridge | 0.707 | -0.107 | 0.718 | 0.000 | 4.212 |
| edaic_same_dataset_phq | edaic | M12a_BGE_Ridge_X_to_theta | 0.704 | -0.109 | 0.681 | -0.036 | 4.082 |
| pooled_shared_phq | cmdc | B0_train_mean_theta | 0.891 | 0.000 | 0.859 | 0.209 | 6.462 |
| pooled_shared_phq | cmdc | B1_train_mean_observed_total | 0.891 | 0.000 | 0.857 | 0.207 | 6.364 |
| pooled_shared_phq | cmdc | B2_direct_total_allocation_ridge | 0.628 | -0.263 | 0.651 | -0.000 | 3.880 |
| pooled_shared_phq | cmdc | B3_direct_itemwise_ridge | 0.630 | -0.261 | 0.651 | 0.000 | 3.873 |
| pooled_shared_phq | cmdc | M12a_BGE_Ridge_X_to_theta | 0.631 | -0.260 | 0.664 | 0.013 | 4.051 |
| pooled_shared_phq | cmdc | M12b_projected_BGE_X_to_theta | 0.630 | -0.261 | 0.680 | 0.030 | 4.212 |
| pooled_shared_phq | edaic | B0_train_mean_theta | 0.760 | 0.000 | 0.732 | 0.008 | 4.763 |
| pooled_shared_phq | edaic | B1_train_mean_observed_total | 0.760 | 0.000 | 0.732 | 0.009 | 4.769 |
| pooled_shared_phq | edaic | B2_direct_total_allocation_ridge | 0.694 | -0.066 | 0.710 | -0.014 | 4.366 |
| pooled_shared_phq | edaic | B3_direct_itemwise_ridge | 0.683 | -0.077 | 0.724 | 0.000 | 4.361 |
| pooled_shared_phq | edaic | M12a_BGE_Ridge_X_to_theta | 0.680 | -0.080 | 0.697 | -0.026 | 4.252 |
| pooled_shared_phq | edaic | M12b_projected_BGE_X_to_theta | 0.685 | -0.075 | 0.693 | -0.031 | 4.265 |

## Transfer Summary

| protocol | target dataset | theta delta vs B0 | theta delta vs B3 | observed delta vs B3 |
| --- | --- | ---: | ---: | ---: |
| cross_cmdc_to_edaic_phq | edaic | -0.022 | -0.063 | -0.053 |
| cross_edaic_to_cmdc_phq | cmdc | 0.033 | 0.010 | 0.054 |

## Identity Probes

| probe | model | conditioning | BA mean | std |
| --- | --- | --- | ---: | ---: |
| ID0_unconditional_predicted_theta_identity | B3_direct_itemwise_ridge | none | 0.438 | 0.131 |
| ID0_unconditional_predicted_theta_identity | M12a_BGE_Ridge_X_to_theta | none | 0.510 | 0.124 |
| ID0_unconditional_predicted_theta_identity | M12b_projected_BGE_X_to_theta | none | 0.440 | 0.079 |
| ID1_conditional_predicted_theta_identity | B3_direct_itemwise_ridge | theta_true_and_observed_total | 0.494 | 0.094 |
| ID1_conditional_predicted_theta_identity | M12a_BGE_Ridge_X_to_theta | theta_true_and_observed_total | 0.495 | 0.145 |
| ID1_conditional_predicted_theta_identity | M12b_projected_BGE_X_to_theta | theta_true_and_observed_total | 0.476 | 0.101 |
| ID2_conditional_post_mapping_identity | B3_direct_itemwise_ridge | theta_true_observed_total_and_true_items | 0.834 | 0.054 |
| ID2_conditional_post_mapping_identity | M12a_BGE_Ridge_X_to_theta | theta_true_observed_total_and_true_items | 0.977 | 0.013 |
| ID2_conditional_post_mapping_identity | M12b_projected_BGE_X_to_theta | theta_true_observed_total_and_true_items | 0.962 | 0.029 |

## Interpretation Boundary

- MV12 is still a minimal-validation row, not full M0/M1/M2/M3 construction.
- If it fails any primary gate, use it as diagnostic evidence for measurement shift rather than a positive shared-latent method claim.
- The ignored local row prediction file can support later aggregate error analysis, but it is not part of the public release.
