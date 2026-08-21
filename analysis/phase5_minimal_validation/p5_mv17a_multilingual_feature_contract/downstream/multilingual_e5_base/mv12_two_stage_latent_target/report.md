# P5_MV12 Two-Stage Latent-Target Validation

Generated: `2026-08-21T18:03:16+00:00`

## Scope

MV12 fits label-only PHQ theta targets locally, trains shallow BGE X-to-theta predictors, compares direct/floor baselines, and exports aggregate diagnostics only.

## Verdict

- Pass-rule status: `blocked_theta_gain_not_observed_scale_safe`.
- Same-dataset theta gate passed: `True`.
- Same-dataset observed-scale gate passed: `False`.
- External theta transfer gate passed: `False`.
- External observed-scale transfer gate passed: `True`.
- Conditional identity BA for M12a: `0.488`.
- Conditional identity improved versus MV09: `True`.
- Preferred conditional identity threshold passed: `True`.
- Leakage gate passed: `True`.
- Artifact hygiene passed: `True`.

MV12 runs the predeclared two-stage PHQ latent-target test. A pass requires theta utility, observed-scale safety, external transfer, conditional shared-latent identity, leakage control, and artifact hygiene; design or same-dataset gains alone are not enough.

## Key Comparisons

| protocol | dataset | model | theta MAE | delta theta vs B0 | observed macro MAE | delta observed vs B3 | observed total MAE |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: |
| cmdc_subject_cv_phq | cmdc | B0_train_mean_theta | 0.805 | 0.000 | 0.848 | 0.233 | 6.229 |
| cmdc_subject_cv_phq | cmdc | B1_train_mean_observed_total | 0.805 | 0.000 | 0.848 | 0.233 | 6.229 |
| cmdc_subject_cv_phq | cmdc | B2_direct_total_allocation_ridge | 0.581 | -0.224 | 0.642 | 0.027 | 3.827 |
| cmdc_subject_cv_phq | cmdc | B3_direct_itemwise_ridge | 0.567 | -0.238 | 0.615 | 0.000 | 3.514 |
| cmdc_subject_cv_phq | cmdc | M12a_BGE_Ridge_X_to_theta | 0.615 | -0.190 | 0.678 | 0.062 | 4.148 |
| cross_cmdc_to_edaic_phq | edaic | B0_train_mean_theta | 0.692 | 0.000 | 0.743 | -0.439 | 4.742 |
| cross_cmdc_to_edaic_phq | edaic | B1_train_mean_observed_total | 0.692 | 0.000 | 0.743 | -0.439 | 4.742 |
| cross_cmdc_to_edaic_phq | edaic | B2_direct_total_allocation_ridge | 0.721 | 0.029 | 0.834 | -0.347 | 5.195 |
| cross_cmdc_to_edaic_phq | edaic | B3_direct_itemwise_ridge | 1.084 | 0.392 | 1.181 | 0.000 | 6.988 |
| cross_cmdc_to_edaic_phq | edaic | M12a_BGE_Ridge_X_to_theta | 0.737 | 0.045 | 0.862 | -0.320 | 5.359 |
| cross_edaic_to_cmdc_phq | cmdc | B0_train_mean_theta | 0.965 | 0.000 | 0.865 | -0.150 | 6.415 |
| cross_edaic_to_cmdc_phq | cmdc | B1_train_mean_observed_total | 0.965 | 0.000 | 0.865 | -0.150 | 6.415 |
| cross_edaic_to_cmdc_phq | cmdc | B2_direct_total_allocation_ridge | 1.077 | 0.112 | 1.010 | -0.006 | 7.269 |
| cross_edaic_to_cmdc_phq | cmdc | B3_direct_itemwise_ridge | 1.029 | 0.064 | 1.015 | 0.000 | 7.269 |
| cross_edaic_to_cmdc_phq | cmdc | M12a_BGE_Ridge_X_to_theta | 1.033 | 0.068 | 0.959 | -0.056 | 6.870 |
| edaic_same_dataset_phq | edaic | B0_train_mean_theta | 0.813 | 0.000 | 0.735 | 0.055 | 4.780 |
| edaic_same_dataset_phq | edaic | B1_train_mean_observed_total | 0.813 | 0.000 | 0.735 | 0.055 | 4.780 |
| edaic_same_dataset_phq | edaic | B2_direct_total_allocation_ridge | 0.714 | -0.099 | 0.681 | 0.001 | 3.965 |
| edaic_same_dataset_phq | edaic | B3_direct_itemwise_ridge | 0.716 | -0.097 | 0.680 | 0.000 | 3.965 |
| edaic_same_dataset_phq | edaic | M12a_BGE_Ridge_X_to_theta | 0.724 | -0.090 | 0.689 | 0.009 | 4.131 |
| pooled_shared_phq | cmdc | B0_train_mean_theta | 0.891 | 0.000 | 0.859 | 0.171 | 6.462 |
| pooled_shared_phq | cmdc | B1_train_mean_observed_total | 0.891 | 0.000 | 0.857 | 0.169 | 6.364 |
| pooled_shared_phq | cmdc | B2_direct_total_allocation_ridge | 0.655 | -0.236 | 0.687 | -0.001 | 4.240 |
| pooled_shared_phq | cmdc | B3_direct_itemwise_ridge | 0.657 | -0.234 | 0.688 | 0.000 | 4.242 |
| pooled_shared_phq | cmdc | M12a_BGE_Ridge_X_to_theta | 0.661 | -0.231 | 0.701 | 0.013 | 4.389 |
| pooled_shared_phq | cmdc | M12b_projected_BGE_X_to_theta | 0.672 | -0.219 | 0.718 | 0.030 | 4.575 |
| pooled_shared_phq | edaic | B0_train_mean_theta | 0.760 | 0.000 | 0.732 | 0.051 | 4.763 |
| pooled_shared_phq | edaic | B1_train_mean_observed_total | 0.760 | 0.000 | 0.732 | 0.052 | 4.769 |
| pooled_shared_phq | edaic | B2_direct_total_allocation_ridge | 0.664 | -0.096 | 0.685 | 0.004 | 4.068 |
| pooled_shared_phq | edaic | B3_direct_itemwise_ridge | 0.668 | -0.092 | 0.681 | 0.000 | 4.063 |
| pooled_shared_phq | edaic | M12a_BGE_Ridge_X_to_theta | 0.673 | -0.087 | 0.692 | 0.011 | 4.205 |
| pooled_shared_phq | edaic | M12b_projected_BGE_X_to_theta | 0.665 | -0.096 | 0.682 | 0.001 | 4.100 |

## Transfer Summary

| protocol | target dataset | theta delta vs B0 | theta delta vs B3 | observed delta vs B3 |
| --- | --- | ---: | ---: | ---: |
| cross_cmdc_to_edaic_phq | edaic | 0.045 | -0.346 | -0.320 |
| cross_edaic_to_cmdc_phq | cmdc | 0.068 | 0.005 | -0.056 |

## Identity Probes

| probe | model | conditioning | BA mean | std |
| --- | --- | --- | ---: | ---: |
| ID0_unconditional_predicted_theta_identity | B3_direct_itemwise_ridge | none | 0.475 | 0.144 |
| ID0_unconditional_predicted_theta_identity | M12a_BGE_Ridge_X_to_theta | none | 0.475 | 0.146 |
| ID0_unconditional_predicted_theta_identity | M12b_projected_BGE_X_to_theta | none | 0.459 | 0.100 |
| ID1_conditional_predicted_theta_identity | B3_direct_itemwise_ridge | theta_true_and_observed_total | 0.459 | 0.122 |
| ID1_conditional_predicted_theta_identity | M12a_BGE_Ridge_X_to_theta | theta_true_and_observed_total | 0.488 | 0.141 |
| ID1_conditional_predicted_theta_identity | M12b_projected_BGE_X_to_theta | theta_true_and_observed_total | 0.506 | 0.097 |
| ID2_conditional_post_mapping_identity | B3_direct_itemwise_ridge | theta_true_observed_total_and_true_items | 0.940 | 0.047 |
| ID2_conditional_post_mapping_identity | M12a_BGE_Ridge_X_to_theta | theta_true_observed_total_and_true_items | 0.981 | 0.011 |
| ID2_conditional_post_mapping_identity | M12b_projected_BGE_X_to_theta | theta_true_observed_total_and_true_items | 0.976 | 0.015 |

## Interpretation Boundary

- MV12 is still a minimal-validation row, not full M0/M1/M2/M3 construction.
- If it fails any primary gate, use it as diagnostic evidence for measurement shift rather than a positive shared-latent method claim.
- The ignored local row prediction file can support later aggregate error analysis, but it is not part of the public release.
