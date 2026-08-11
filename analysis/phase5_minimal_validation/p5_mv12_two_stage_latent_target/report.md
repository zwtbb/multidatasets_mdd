# P5_MV12 Two-Stage Latent-Target Validation

Generated: `2026-08-11T14:44:55+00:00`

## Scope

MV12 fits label-only PHQ theta targets locally, trains shallow BGE X-to-theta predictors, compares direct/floor baselines, and exports aggregate diagnostics only.

## Verdict

- Pass-rule status: `blocked_theta_gain_not_observed_scale_safe`.
- Same-dataset theta gate passed: `True`.
- Same-dataset observed-scale gate passed: `False`.
- External theta transfer gate passed: `False`.
- External observed-scale transfer gate passed: `True`.
- Conditional identity BA for M12a: `0.602`.
- Conditional identity improved versus MV09: `True`.
- Preferred conditional identity threshold passed: `True`.
- Leakage gate passed: `True`.
- Artifact hygiene passed: `True`.

MV12 runs the predeclared two-stage PHQ latent-target test. A pass requires theta utility, observed-scale safety, external transfer, conditional shared-latent identity, leakage control, and artifact hygiene; design or same-dataset gains alone are not enough.

## Key Comparisons

| protocol | dataset | model | theta MAE | delta theta vs B0 | observed macro MAE | delta observed vs B3 | observed total MAE |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: |
| cmdc_subject_cv_phq | cmdc | B0_train_mean_theta | 0.805 | 0.000 | 0.848 | 0.202 | 6.229 |
| cmdc_subject_cv_phq | cmdc | B1_train_mean_observed_total | 0.805 | 0.000 | 0.848 | 0.202 | 6.229 |
| cmdc_subject_cv_phq | cmdc | B2_direct_total_allocation_ridge | 0.645 | -0.160 | 0.692 | 0.045 | 4.409 |
| cmdc_subject_cv_phq | cmdc | B3_direct_itemwise_ridge | 0.624 | -0.181 | 0.646 | 0.000 | 4.073 |
| cmdc_subject_cv_phq | cmdc | M12a_BGE_Ridge_X_to_theta | 0.659 | -0.146 | 0.713 | 0.067 | 4.615 |
| cross_cmdc_to_edaic_phq | edaic | B0_train_mean_theta | 0.692 | 0.000 | 0.743 | -0.277 | 4.742 |
| cross_cmdc_to_edaic_phq | edaic | B1_train_mean_observed_total | 0.692 | 0.000 | 0.743 | -0.277 | 4.742 |
| cross_cmdc_to_edaic_phq | edaic | B2_direct_total_allocation_ridge | 0.725 | 0.033 | 0.756 | -0.264 | 4.803 |
| cross_cmdc_to_edaic_phq | edaic | B3_direct_itemwise_ridge | 0.894 | 0.202 | 1.020 | 0.000 | 5.924 |
| cross_cmdc_to_edaic_phq | edaic | M12a_BGE_Ridge_X_to_theta | 0.729 | 0.037 | 0.760 | -0.260 | 4.818 |
| cross_edaic_to_cmdc_phq | cmdc | B0_train_mean_theta | 0.965 | 0.000 | 0.865 | -0.104 | 6.415 |
| cross_edaic_to_cmdc_phq | cmdc | B1_train_mean_observed_total | 0.965 | 0.000 | 0.865 | -0.104 | 6.415 |
| cross_edaic_to_cmdc_phq | cmdc | B2_direct_total_allocation_ridge | 0.901 | -0.064 | 0.804 | -0.166 | 5.565 |
| cross_edaic_to_cmdc_phq | cmdc | B3_direct_itemwise_ridge | 0.902 | -0.063 | 0.970 | 0.000 | 5.775 |
| cross_edaic_to_cmdc_phq | cmdc | M12a_BGE_Ridge_X_to_theta | 1.042 | 0.077 | 0.759 | -0.210 | 5.490 |
| edaic_same_dataset_phq | edaic | B0_train_mean_theta | 0.813 | 0.000 | 0.735 | 0.044 | 4.780 |
| edaic_same_dataset_phq | edaic | B1_train_mean_observed_total | 0.813 | 0.000 | 0.735 | 0.044 | 4.780 |
| edaic_same_dataset_phq | edaic | B2_direct_total_allocation_ridge | 0.741 | -0.073 | 0.696 | 0.005 | 4.206 |
| edaic_same_dataset_phq | edaic | B3_direct_itemwise_ridge | 0.742 | -0.072 | 0.691 | 0.000 | 4.216 |
| edaic_same_dataset_phq | edaic | M12a_BGE_Ridge_X_to_theta | 0.735 | -0.078 | 0.695 | 0.004 | 4.321 |
| pooled_shared_phq | cmdc | B0_train_mean_theta | 0.891 | 0.000 | 0.859 | 0.180 | 6.462 |
| pooled_shared_phq | cmdc | B1_train_mean_observed_total | 0.891 | 0.000 | 0.857 | 0.178 | 6.364 |
| pooled_shared_phq | cmdc | B2_direct_total_allocation_ridge | 0.672 | -0.220 | 0.676 | -0.003 | 4.259 |
| pooled_shared_phq | cmdc | B3_direct_itemwise_ridge | 0.680 | -0.211 | 0.679 | 0.000 | 4.252 |
| pooled_shared_phq | cmdc | M12a_BGE_Ridge_X_to_theta | 0.681 | -0.211 | 0.692 | 0.013 | 4.411 |
| pooled_shared_phq | cmdc | M12b_projected_BGE_X_to_theta | 0.701 | -0.190 | 0.709 | 0.030 | 4.632 |
| pooled_shared_phq | edaic | B0_train_mean_theta | 0.760 | 0.000 | 0.732 | 0.028 | 4.763 |
| pooled_shared_phq | edaic | B1_train_mean_observed_total | 0.760 | 0.000 | 0.732 | 0.028 | 4.769 |
| pooled_shared_phq | edaic | B2_direct_total_allocation_ridge | 0.715 | -0.045 | 0.708 | 0.003 | 4.459 |
| pooled_shared_phq | edaic | B3_direct_itemwise_ridge | 0.722 | -0.038 | 0.704 | 0.000 | 4.459 |
| pooled_shared_phq | edaic | M12a_BGE_Ridge_X_to_theta | 0.718 | -0.042 | 0.711 | 0.007 | 4.520 |
| pooled_shared_phq | edaic | M12b_projected_BGE_X_to_theta | 0.702 | -0.058 | 0.694 | -0.010 | 4.347 |

## Transfer Summary

| protocol | target dataset | theta delta vs B0 | theta delta vs B3 | observed delta vs B3 |
| --- | --- | ---: | ---: | ---: |
| cross_cmdc_to_edaic_phq | edaic | 0.037 | -0.165 | -0.260 |
| cross_edaic_to_cmdc_phq | cmdc | 0.077 | 0.140 | -0.210 |

## Identity Probes

| probe | model | conditioning | BA mean | std |
| --- | --- | --- | ---: | ---: |
| ID0_unconditional_predicted_theta_identity | B3_direct_itemwise_ridge | none | 0.574 | 0.180 |
| ID0_unconditional_predicted_theta_identity | M12a_BGE_Ridge_X_to_theta | none | 0.641 | 0.147 |
| ID0_unconditional_predicted_theta_identity | M12b_projected_BGE_X_to_theta | none | 0.590 | 0.139 |
| ID1_conditional_predicted_theta_identity | B3_direct_itemwise_ridge | theta_true_and_observed_total | 0.579 | 0.131 |
| ID1_conditional_predicted_theta_identity | M12a_BGE_Ridge_X_to_theta | theta_true_and_observed_total | 0.602 | 0.109 |
| ID1_conditional_predicted_theta_identity | M12b_projected_BGE_X_to_theta | theta_true_and_observed_total | 0.608 | 0.135 |
| ID2_conditional_post_mapping_identity | B3_direct_itemwise_ridge | theta_true_observed_total_and_true_items | 0.975 | 0.020 |
| ID2_conditional_post_mapping_identity | M12a_BGE_Ridge_X_to_theta | theta_true_observed_total_and_true_items | 0.992 | 0.014 |
| ID2_conditional_post_mapping_identity | M12b_projected_BGE_X_to_theta | theta_true_observed_total_and_true_items | 0.997 | 0.005 |

## Interpretation Boundary

- MV12 is still a minimal-validation row, not full M0/M1/M2/M3 construction.
- If it fails any primary gate, use it as diagnostic evidence for measurement shift rather than a positive shared-latent method claim.
- The ignored local row prediction file can support later aggregate error analysis, but it is not part of the public release.
