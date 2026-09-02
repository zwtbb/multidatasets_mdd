# P5_MV12 Two-Stage Latent-Target Validation

Generated: `2026-08-24T12:34:12+00:00`

## Scope

MV12 fits label-only PHQ theta targets locally, trains shallow BGE X-to-theta predictors, compares direct/floor baselines, and exports aggregate diagnostics only.

## Verdict

- Pass-rule status: `blocked_theta_gain_not_observed_scale_safe`.
- Same-dataset theta gate passed: `True`.
- Same-dataset observed-scale gate passed: `False`.
- External theta transfer gate passed: `True`.
- External observed-scale transfer gate passed: `True`.
- Conditional identity BA for M12a: `0.554`.
- Conditional identity improved versus MV09: `True`.
- Preferred conditional identity threshold passed: `True`.
- Leakage gate passed: `True`.
- Artifact hygiene passed: `True`.

MV12 runs the predeclared two-stage PHQ latent-target test. A pass requires theta utility, observed-scale safety, external transfer, conditional shared-latent identity, leakage control, and artifact hygiene; design or same-dataset gains alone are not enough.

## Key Comparisons

| protocol | dataset | model | theta MAE | delta theta vs B0 | observed macro MAE | delta observed vs B3 | observed total MAE |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: |
| cmdc_subject_cv_phq | cmdc | B0_train_mean_theta | 0.805 | 0.000 | 0.848 | 0.271 | 6.229 |
| cmdc_subject_cv_phq | cmdc | B1_train_mean_observed_total | 0.805 | 0.000 | 0.848 | 0.271 | 6.229 |
| cmdc_subject_cv_phq | cmdc | B2_direct_total_allocation_ridge | 0.569 | -0.236 | 0.617 | 0.040 | 3.527 |
| cmdc_subject_cv_phq | cmdc | B3_direct_itemwise_ridge | 0.561 | -0.244 | 0.577 | 0.000 | 2.999 |
| cmdc_subject_cv_phq | cmdc | M12a_BGE_Ridge_X_to_theta | 0.603 | -0.202 | 0.655 | 0.079 | 3.883 |
| cross_cmdc_to_edaic_phq | edaic | B0_train_mean_theta | 0.692 | 0.000 | 0.743 | -0.126 | 4.742 |
| cross_cmdc_to_edaic_phq | edaic | B1_train_mean_observed_total | 0.692 | 0.000 | 0.743 | -0.126 | 4.742 |
| cross_cmdc_to_edaic_phq | edaic | B2_direct_total_allocation_ridge | 0.709 | 0.017 | 0.718 | -0.151 | 4.579 |
| cross_cmdc_to_edaic_phq | edaic | B3_direct_itemwise_ridge | 0.729 | 0.037 | 0.869 | 0.000 | 4.707 |
| cross_cmdc_to_edaic_phq | edaic | M12a_BGE_Ridge_X_to_theta | 0.724 | 0.032 | 0.733 | -0.136 | 4.594 |
| cross_edaic_to_cmdc_phq | cmdc | B0_train_mean_theta | 0.965 | 0.000 | 0.865 | -0.018 | 6.415 |
| cross_edaic_to_cmdc_phq | cmdc | B1_train_mean_observed_total | 0.965 | 0.000 | 0.865 | -0.018 | 6.415 |
| cross_edaic_to_cmdc_phq | cmdc | B2_direct_total_allocation_ridge | 0.923 | -0.042 | 0.861 | -0.022 | 6.151 |
| cross_edaic_to_cmdc_phq | cmdc | B3_direct_itemwise_ridge | 0.904 | -0.061 | 0.883 | 0.000 | 6.151 |
| cross_edaic_to_cmdc_phq | cmdc | M12a_BGE_Ridge_X_to_theta | 0.917 | -0.048 | 0.855 | -0.028 | 6.121 |
| edaic_same_dataset_phq | edaic | B0_train_mean_theta | 0.813 | 0.000 | 0.735 | 0.036 | 4.780 |
| edaic_same_dataset_phq | edaic | B1_train_mean_observed_total | 0.813 | 0.000 | 0.735 | 0.036 | 4.780 |
| edaic_same_dataset_phq | edaic | B2_direct_total_allocation_ridge | 0.754 | -0.060 | 0.703 | 0.004 | 4.310 |
| edaic_same_dataset_phq | edaic | B3_direct_itemwise_ridge | 0.750 | -0.064 | 0.699 | 0.000 | 4.294 |
| edaic_same_dataset_phq | edaic | M12a_BGE_Ridge_X_to_theta | 0.743 | -0.070 | 0.692 | -0.006 | 4.272 |
| pooled_shared_phq | cmdc | B0_train_mean_theta | 0.891 | 0.000 | 0.859 | 0.165 | 6.462 |
| pooled_shared_phq | cmdc | B1_train_mean_observed_total | 0.891 | 0.000 | 0.857 | 0.163 | 6.364 |
| pooled_shared_phq | cmdc | B2_direct_total_allocation_ridge | 0.658 | -0.234 | 0.692 | -0.003 | 4.272 |
| pooled_shared_phq | cmdc | B3_direct_itemwise_ridge | 0.669 | -0.222 | 0.695 | 0.000 | 4.273 |
| pooled_shared_phq | cmdc | M12a_BGE_Ridge_X_to_theta | 0.671 | -0.220 | 0.708 | 0.013 | 4.479 |
| pooled_shared_phq | cmdc | M12b_projected_BGE_X_to_theta | 0.667 | -0.225 | 0.722 | 0.028 | 4.654 |
| pooled_shared_phq | edaic | B0_train_mean_theta | 0.760 | 0.000 | 0.732 | 0.040 | 4.763 |
| pooled_shared_phq | edaic | B1_train_mean_observed_total | 0.760 | 0.000 | 0.732 | 0.040 | 4.769 |
| pooled_shared_phq | edaic | B2_direct_total_allocation_ridge | 0.697 | -0.063 | 0.693 | 0.001 | 4.215 |
| pooled_shared_phq | edaic | B3_direct_itemwise_ridge | 0.693 | -0.067 | 0.692 | 0.000 | 4.190 |
| pooled_shared_phq | edaic | M12a_BGE_Ridge_X_to_theta | 0.691 | -0.069 | 0.682 | -0.010 | 4.228 |
| pooled_shared_phq | edaic | M12b_projected_BGE_X_to_theta | 0.708 | -0.052 | 0.681 | -0.011 | 4.316 |

## Transfer Summary

| protocol | target dataset | theta delta vs B0 | theta delta vs B3 | observed delta vs B3 |
| --- | --- | ---: | ---: | ---: |
| cross_cmdc_to_edaic_phq | edaic | 0.032 | -0.005 | -0.136 |
| cross_edaic_to_cmdc_phq | cmdc | -0.048 | 0.012 | -0.028 |

## Identity Probes

| probe | model | conditioning | BA mean | std |
| --- | --- | --- | ---: | ---: |
| ID0_unconditional_predicted_theta_identity | B3_direct_itemwise_ridge | none | 0.464 | 0.079 |
| ID0_unconditional_predicted_theta_identity | M12a_BGE_Ridge_X_to_theta | none | 0.488 | 0.107 |
| ID0_unconditional_predicted_theta_identity | M12b_projected_BGE_X_to_theta | none | 0.537 | 0.044 |
| ID1_conditional_predicted_theta_identity | B3_direct_itemwise_ridge | theta_true_and_observed_total | 0.470 | 0.093 |
| ID1_conditional_predicted_theta_identity | M12a_BGE_Ridge_X_to_theta | theta_true_and_observed_total | 0.554 | 0.077 |
| ID1_conditional_predicted_theta_identity | M12b_projected_BGE_X_to_theta | theta_true_and_observed_total | 0.600 | 0.049 |
| ID2_conditional_post_mapping_identity | B3_direct_itemwise_ridge | theta_true_observed_total_and_true_items | 0.902 | 0.054 |
| ID2_conditional_post_mapping_identity | M12a_BGE_Ridge_X_to_theta | theta_true_observed_total_and_true_items | 0.981 | 0.016 |
| ID2_conditional_post_mapping_identity | M12b_projected_BGE_X_to_theta | theta_true_observed_total_and_true_items | 0.974 | 0.021 |

## Interpretation Boundary

- MV12 is still a minimal-validation row, not full M0/M1/M2/M3 construction.
- If it fails any primary gate, use it as diagnostic evidence for measurement shift rather than a positive shared-latent method claim.
- The ignored local row prediction file can support later aggregate error analysis, but it is not part of the public release.
