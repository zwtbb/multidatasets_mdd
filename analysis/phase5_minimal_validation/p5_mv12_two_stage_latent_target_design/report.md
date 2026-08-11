# P5_MV12 Two-Stage Latent-Target Design

Generated: `2026-08-11T14:28:40+00:00`

## Scope

This is a predeclared design contract. It does not train a multimodal model, fit public measurement parameters, export theta scores, read row-level predictions, or authorize full-method construction.

## Decision

- Readiness status: `ready_to_implement_mv12_two_stage_latent_target`.
- Recommended next action: `implement_scripts_phase5_run_mv12_two_stage_latent_target`.
- Full method allowed: `False`.
- Artifact hygiene passed: `True`.

MV12 is predeclared as a two-stage measurement-target experiment: fit Y_to_theta locally, train audited X_to_theta predictors, compare against direct/floor baselines, and gate on conditional identity plus external transfer.

## Source Evidence

| source | status | observation | implication |
| --- | --- | --- | --- |
| MV11_formal_label_measurement | `complete_formal_partial_invariance_supported_with_bic_caveat` | confirmed_mv10_anchors=4; loading_DIF_flags=0; threshold_DIF_flags=2; AIC_BIC_split=True | Use MV11 as the label-only measurement target source, with a BIC caveat and no public subject scores or fitted parameters. |
| MV11_anchor_map | `partial_anchor_map_confirmed` | primary_anchors=C01;C04;C05;C07; threshold_DIF_items=C02;C06; loading_DIF_items=none; sensitivity_candidates=C03;C08 | Primary target uses C01/C04/C05/C07 anchors; C02/C06 keep threshold-free/DIF-aware treatment; C03/C08 are sensitivity-only unless predeclared otherwise. |
| MV11_gate_recommendation | `ready_to_predeclare_two_stage_latent_target_with_bic_caveat` | MV11 status complete_formal_partial_invariance_supported_with_bic_caveat; confirmed MV10 anchors 4/3 required. | If proceeding, predeclare Y->theta measurement fitting separately from X->theta multimodal prediction and compare against direct X->Y floors. |
| MV09_conditional_identity | `complete_identity_gate_revision_needed` | E-DAIC_CMDC_raw_BA=1.000; E-DAIC_CMDC_item_conditioned_BA=0.991; CMDC_PDCH_severity_conditioned_BA=1.000; three_way_severity_conditioned_BA=1.000 | Use conditional identity as the shared-latent gate; post-head scale-specific prediction identity stays diagnostic only. |
| MV07_aligned_BGE_negative | `blocked_not_better_than_total_allocation_bge_contract` | aligned BGE direct itemwise heads did not consistently beat total-allocation floors; feature BA=1.000 and prediction BA=0.980. | Direct X_to_Y BGE heads stay mandatory baselines, not the target method. |
| MV07b_identity_projection_tradeoff | `partial_identity_reduced_not_total_floor_beating_bge_projection` | best_feature_BA_after=0.709; best_prediction_BA_after=0.684; CMDC_delta_vs_total_allocation=0.018 | Identity projection may be a secondary X_to_theta variant only after the unprojected latent baseline and floors are reported. |
| MV07c_total_anchor_tradeoff | `blocked_not_better_than_raw_total_allocation_bge_total_anchor` | prediction_BA=0.664; E-DAIC_delta_vs_raw_total=-0.018; CMDC_delta_vs_raw_total=0.012 | Total anchoring informs direct-floor comparisons, but MV12 must predict the psychometric latent target rather than retune itemwise heads. |
| MV08b_negative_head_sequence | `blocked_prediction_identity_increased_vs_mv08` | M2b_beats_both_floors_slices=2/3; prediction_BA=0.979 | Do not create MV08c; change the target to a separately fitted measurement latent variable. |
| MV10_label_screen_context | `complete_partial_invariance_supported_approx` | loading_congruence=0.998; metric_items=7/8; threshold_items=4/8 | MV10 supplies the approximate screen that MV11 formalizes; keep both in manuscript context. |
| full_method_gate_next_action | `NEXT_IMPLEMENT_TWO_STAGE_LATENT_TARGET_RUN` | full_gate_status=blocked_but_publishable_diagnostic_direction; full_method_allowed=False; top_action=NEXT_IMPLEMENT_TWO_STAGE_LATENT_TARGET_RUN | MV12 can close the predeclaration gap only; full method stays blocked until the actual X_to_theta run passes. |

## Target Generation

| stage | scope | target policy | tracked output | pass condition |
| --- | --- | --- | --- | --- |
| Y_THETA_PRIMARY_MEASUREMENT_TARGET | E-DAIC PHQ-8 and CMDC PHQ-9 shared C01-C08 labels | Fit a train-fold label-only graded-response measurement model; primary anchors are C01,C04,C05,C07. | Export aggregate target coverage, fold reliability, distribution bins, and reconstruction metrics only. | Train-fold target generation succeeds with confirmed anchors and no public score or parameter export. |
| DIF_AWARE_ITEM_POLICY | PHQ C01-C08 item response functions | Keep C02 and C06 threshold-DIF-aware; no loading-DIF item is primary-blocking because MV11 flags zero strong loading DIF items. | Export aggregate counts of anchor, threshold-free, and sensitivity items. | Target contract uses the same predeclared item roles across seeds and folds. |
| SENSITIVITY_TARGETS | Stable non-MV10 items C03 and C08 | Use C03/C08 as sensitivity-only target variants, not as primary anchors, unless a later predeclared contract upgrades them. | Export aggregate sensitivity deltas versus the primary MV11 target. | Primary conclusion is unchanged or explicitly downgraded if sensitivity targets conflict. |
| THETA_TO_OBSERVED_MAPPING | Dataset-specific PHQ observed item and total reconstructions | Map predicted theta back to dataset-specific expected PHQ item/total summaries for comparison with direct X_to_Y baselines. | Export aggregate observed-scale MAE/RMSE/correlation and calibration summaries. | Theta-space gains also translate into non-degraded observed-scale reconstruction relative to direct floors. |

## Local-Only Boundary

| artifact class | reason | tracked surrogate | git policy |
| --- | --- | --- | --- |
| measurement_fit_parameters | Fitted item discriminations, thresholds, and DIF offsets define the private scoring transform. | aggregate fit status, anchor counts, DIF role counts, and target reliability summaries | ignored local-only; never force-add |
| latent_targets | Per-participant latent severity targets are subject-level clinical derivatives. | aggregate theta distribution bins and fold reliability metrics | ignored local-only; never force-add |
| row_predictions | Needed for local error analysis but contains subject-grain prediction traces. | dataset-stratified metrics, transfer deltas, calibration bins, and identity summaries | ignored local-only; never force-add |
| feature_transforms_and_models | Projection directions, fitted regressors, and transformed features can reconstruct sensitive dataset/subject information. | aggregate selected model family, fold counts, hyperparameter ranges, and leakage audit booleans | ignored local-only; never force-add |
| diagnostic_workbooks | Any manual review packet could link model errors back to private local records. | aggregate error taxonomy counts only if a later review is approved | ignored local-only; never force-add |

## Model Ladder

| model | family | target | role | pass gate |
| --- | --- | --- | --- | --- |
| B0_train_mean_theta | floor | theta | latent target sanity floor | Every X_to_theta candidate must beat this floor on same-dataset and cross-dataset aggregate theta error. |
| B1_train_mean_observed_total | floor | observed item/total reconstruction | observed-scale severity floor | Theta models must not look successful only in latent space while failing observed-scale floors. |
| B2_direct_X_to_Y_total_allocation | direct baseline | observed PHQ item proxies allocated from predicted total severity | strong simple direct floor from MV07/MV07c sequence | MV12 must beat or clearly contextualize this direct floor before any positive shared-latent wording. |
| B3_direct_X_to_Y_itemwise | direct baseline | observed PHQ C01-C08 item scores | direct symptom-head comparator from MV07 | X_to_theta must outperform this direct itemwise path on primary theta and non-degraded observed reconstruction. |
| M12a_BGE_Ridge_X_to_theta | primary MV12 candidate | train-fold local-only MV11 theta | first real two-stage test | Beat B0/B1/B2/B3 on predeclared aggregate metrics with subject-level folds and hygiene pass. |
| M12b_identity_projected_BGE_X_to_theta | secondary MV12 candidate | train-fold local-only MV11 theta | accuracy-invariance trade-off candidate | Allowed as secondary pass only if M12a is reported and conditional latent identity improves without losing more than 5 percent relative theta utility. |
| M12c_theta_to_dataset_specific_Y | measurement mapping evaluation | dataset-specific expected PHQ item and total summaries | checks whether latent gains survive observed-scale interpretation | Observed-scale reconstruction must be non-degraded versus direct floors or the latent result is downgraded to diagnostic. |

## Identity And Transfer Gates

| gate | type | conditioning | future rule |
| --- | --- | --- | --- |
| ID0_unconditional_screen | diagnostic_screen | none | Report as shortcut-risk context; do not use as the only hard failure criterion. |
| ID1_shared_latent_conditional_identity | primary_identity_gate | condition on observed severity, available aligned PHQ items, and legitimate covariates where available | Must be below the MV09 conditional feature identity baselines and preferably <=0.700; otherwise only diagnostic wording is allowed. |
| ID2_post_mapping_prediction_identity | diagnostic_identity_gate | same conditioning as ID1 when feasible | Do not treat scale-specific post-mapping identity as the same hard gate as shared-latent identity. |
| TR0_same_dataset_subject_folds | predictive_utility | train-fold target generation only | M12a must beat train-mean theta and direct X_to_Y floors on both E-DAIC and CMDC same-dataset evaluations. |
| TR1_external_transfer | external_transfer | no target-domain labels for training or model selection | At least one transfer direction must beat both train-mean and direct X_to_Y floors; if only same-dataset passes, claim is diagnostic only. |
| TR2_no_official_test_tuning | leakage_control | not applicable | No official test labels or private target labels may be used for target fitting, model selection, or nuisance projection. |

## Pass/Fail Gates

| gate | current status | future run rule | full-method effect |
| --- | --- | --- | --- |
| G0_design_completeness | `pass` | All required aggregate outputs exist and artifact hygiene passes. | Design pass alone does not authorize full method. |
| G1_psychometric_target_stability | `pass_with_bic_caveat` | Future runner must report fold/bootstrap target reliability and anchor stability; instability downgrades all X_to_theta claims. | Needed before any shared-latent method claim. |
| G2_predictive_utility | `predeclared_pending_run` | M12a must beat train-mean theta, observed-total floors, direct X_to_Y total-allocation, and direct itemwise baselines on primary aggregate metrics. | If failed, MV12 becomes another diagnostic negative result. |
| G3_external_transfer | `predeclared_pending_run` | At least one source-to-target PHQ transfer direction must beat direct/floor baselines without target-domain model selection. | Without transfer, same-dataset success is not enough for transferable shared-latent claims. |
| G4_conditional_identity | `predeclared_pending_run` | Shared-latent conditional identity must improve versus MV09 conditional baselines and preferably be <=0.700. | If identity remains high, wording is limited to measurement-target diagnostic evidence. |
| G5_artifact_hygiene | `pass_for_design` | No public fitted parameters, latent scores, row predictions, features, model files, private workbooks, or source locators. | Any hygiene failure blocks GitHub publication and manuscript use until fixed. |

## Implementation Queue

| rank | action | success gate |
| ---: | --- | --- |
| 1 | Create scripts/phase5_run_mv12_two_stage_latent_target.py. | Runner produces local-only measurement targets and aggregate X_to_theta, direct X_to_Y, identity, transfer, and leakage summaries. |
| 2 | Fit train-fold MV11-style label-only measurement targets for E-DAIC and CMDC. | Confirmed anchors are used consistently; C02/C06 are DIF-aware; target reliability and coverage are exported only in aggregate. |
| 3 | Run B0/B1/B2/B3 floors in the same subject-level split contract. | Direct X_to_Y and train-mean floors exist before any M12a/M12b interpretation. |
| 4 | Run M12a BGE Ridge X_to_theta and optional M12b identity-projected X_to_theta. | M12a is always reported; M12b is framed as an accuracy-invariance trade-off if projection is used. |
| 5 | Audit same-dataset folds, external E-DAIC/CMDC transfer, theta_to_observed mapping, and conditional identity. | Full-method gate can decide from aggregate utility, transfer, identity, leakage, and hygiene tables. |
| 6 | Rerun full-method gate and diagnostic paper table generator after the MV12 runner. | Claim boundaries state whether MV12 changes full-method authorization or remains diagnostic. |

## Interpretation Boundary

- MV12 is the next minimal-validation design, not a positive method result.
- A future pass requires predictive utility, external transfer, conditional shared-latent identity, leakage control, and artifact hygiene.
- If X_to_theta fails the floors or conditional identity remains high, the result supports the measurement-shift paper as diagnostic evidence only.
