# P5_MV15 Latent-Conditioned Dataset Identity

MV15 audits whether E-DAIC/CMDC dataset identity remains recoverable from aligned BGE features after conditioning on PHQ theta and dimension-matched severity controls. It is aggregate-only diagnostic evidence.

## Verdict

- Status: `blocked_theta_conditioned_feature_identity_high`.
- Full method allowed: `False`.
- Raw feature identity BA: `1.000`.
- Total-conditioned feature identity BA: `1.000`.
- Predicted-total-conditioned feature identity BA: `1.000`.
- B3 itemwise-theta-conditioned feature identity BA: `1.000`.
- Theta-conditioned feature identity BA: `1.000`.
- Theta-only identity BA: `0.576`.

## Primary Feature Identity

| ladder | representation | conditioning | mean BA | std | completed rows |
| --- | --- | --- | ---: | ---: | ---: |
| L0_D_given_Z_raw | Z_bge_raw | none | 1.000 | 0.000 | 5 |
| L1_D_given_Z_and_total | residualized_Z_bge | normalized_total | 1.000 | 0.000 | 5 |
| L2_D_given_Z_and_predicted_total | residualized_Z_bge | predicted_total | 1.000 | 0.000 | 5 |
| L3_D_given_Z_and_items | residualized_Z_bge | C01-C08 | 0.980 | 0.030 | 5 |
| L4_D_given_Z_and_b3_itemwise_theta | residualized_Z_bge | B3_itemwise_theta | 1.000 | 0.000 | 5 |
| L5_D_given_Z_and_theta | residualized_Z_bge | theta_label | 1.000 | 0.000 | 5 |
| L6_D_given_Z_theta_covariates | residualized_Z_bge | theta_label_plus_shared_covariates | 1.000 | 0.000 | 5 |
| L7_D_given_theta_only | theta_label | none | 0.576 | 0.018 | 5 |

## Output Identity

| output | conditioning | representation | mean BA | std |
| --- | --- | --- | ---: | ---: |
| B3_itemwise_theta | none | b3_itemwise_theta | 0.529 | 0.066 |
| B3_itemwise_theta | theta_label_and_total | b3_itemwise_theta_residual | 0.500 | 0.064 |
| predicted_total | none | predicted_total_norm | 0.564 | 0.062 |
| predicted_total | theta_label_and_total | predicted_total_norm_residual | 0.513 | 0.087 |
| psychometric_predicted_theta | none | theta_pred | 0.584 | 0.065 |
| psychometric_predicted_theta | theta_label_and_total | theta_pred_residual | 0.528 | 0.077 |

## Output Fidelity

| output | metric | mean | std |
| --- | --- | ---: | ---: |
| B3_itemwise_theta | Observed Macro Item MAE | 0.708 | 0.017 |
| B3_itemwise_theta | Observed Total MAE | 4.257 | 0.144 |
| B3_itemwise_theta | Theta MAE | 0.672 | 0.030 |
| predicted_total | Normalized Total MAE | 0.178 | 0.006 |
| predicted_total | Raw Total MAE | 4.261 | 0.138 |
| psychometric_predicted_theta | Observed Macro Item MAE | 0.690 | 0.015 |
| psychometric_predicted_theta | Observed Total MAE | 4.209 | 0.118 |
| psychometric_predicted_theta | Theta MAE | 0.669 | 0.028 |

## External Sensitivity

| scope | ladder | representation | conditioning | mean BA | std |
| --- | --- | --- | --- | ---: | ---: |
| S3_cmdc_pdch_total_sensitivity | L0_D_given_Z_raw | raw_bge_unconditional | none | 1.000 | 0.000 |
| S3_cmdc_pdch_total_sensitivity | L9_severity_only_sensitivity | normalized_total_residualized_bge | normalized_total | 1.000 | 0.000 |
| S3_cmdc_pdch_total_sensitivity | L9_severity_only_sensitivity | severity_only_control | normalized_total | 0.613 | 0.085 |
| S4_three_way_total_norm_sensitivity | L0_D_given_Z_raw | raw_bge_unconditional | none | 1.000 | 0.000 |
| S4_three_way_total_norm_sensitivity | L9_severity_only_sensitivity | normalized_total_residualized_bge | normalized_total | 1.000 | 0.000 |
| S4_three_way_total_norm_sensitivity | L9_severity_only_sensitivity | severity_only_control | normalized_total | 0.400 | 0.028 |

## Boundaries

- Theta scores, fitted item parameters, residualized feature matrices, row predictions, nuisance directions, split maps, and model artifacts are not written to tracked outputs.
- MV15 cannot authorize PHQ-HAMD latent claims; CMDC/PDCH and three-way rows are severity-only sensitivity diagnostics.
