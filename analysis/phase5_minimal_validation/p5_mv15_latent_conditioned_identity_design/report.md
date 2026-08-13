# P5_MV15 Latent-Conditioned Dataset Identity Design

Generated: `2026-08-13T08:24:25+00:00`

## Scope

This is a predeclared design contract. It does not run identity probes, train a multimodal model, fit public theta scores, export residualized features, or authorize full-method construction.

## Decision

- Design status: `ready_to_implement_mv15_latent_conditioned_identity`.
- Recommended next action: `implement_scripts_phase5_run_mv15_latent_conditioned_identity`.
- Full method allowed: `False`.
- Artifact hygiene passed: `True`.

MV15 is predeclared as a latent-conditioned identity audit: compare dataset identity from BGE features and low-dimensional outputs after conditioning on observed labels, total severity, predicted-total severity, direct-itemwise-theta severity, label-derived theta, common-support bins, and legitimate covariates. It is diagnostic only.

## Source Evidence

| source | status | observation | implication |
| --- | --- | --- | --- |
| full_method_gate_after_mv14 | `blocked_but_publishable_diagnostic_direction` | evidence_rows=37; full_method_allowed=False; top_next_action=NEXT_IMPLEMENT_MV15_LATENT_CONDITIONED_IDENTITY_RUNNER | MV15 is the next required predeclaration before any further latent-identity or scale-linking claim. |
| MV09_feature_identity_after_label_conditioning | `complete_identity_gate_revision_needed` | E-DAIC/CMDC raw BGE BA=1.000; PHQ-item residualized BGE BA=0.991; severity residualized BA=1.000 | Observed totals or item labels alone do not explain away BGE dataset identity; label-derived theta must be audited separately. |
| MV10_MV11_label_measurement_screen | `complete_formal_partial_invariance_supported_with_bic_caveat` | MV10 loading congruence=0.998; MV11 anchors=4; loading_DIF_flags=0; threshold_DIF_flags=2 | Conditioning on theta should use the partial-invariance PHQ measurement map, not a naive sum-only target. |
| MV12_predicted_theta_identity_tradeoff | `blocked_theta_gain_not_observed_scale_safe` | M12a conditional predicted-theta identity BA=0.602; B3 conditional predicted-theta identity BA=0.579; post-mapping item residual identity BA=0.992; observed-scale safety=False; external theta transfer=False | M12a reduces identity versus upstream BGE but not versus B3 direct itemwise theta; MV15 must include dimension-matched severity controls. |
| MV12_dimension_matched_baseline_caveat | `complete_freeze_current_mv12_latent_target_line` | B3 observed macro MAE=0.692; B3 conditional identity BA=0.579; M12a observed macro MAE=0.701; M12a conditional identity BA=0.602; B3 unconditional identity BA=0.574 | A low-dimensional output alone can lower dataset identity; psychometric theta must be compared with total and direct-item severity controls. |
| MV12_tradeoff_freeze | `complete_freeze_current_mv12_latent_target_line` | freeze_current_latent_target_line=True; tradeoff_rows=25; failure_mode_rows=7 | MV15 may audit the identity gate but must not become another shallow-head retuning pass. |
| MV14_bootstrap_stability | `complete_mv14_convergence_safe_item_level_measurement_shift` | stable_anchors=C01;C04;C05;C07; top_threshold_DIF=C02;C06; core_convergence_safe_R=120/200; stable_ladder_R=197; DIF_effective_R=100 | Use item-level wording: stable anchors and localized C02/C06 threshold non-equivalence, with global model-selection uncertainty visible. |
| MV13_external_replication_caveat | `complete_external_mirt_with_convergence_warnings` | AIC/BIC=partial_mv10/scalar; core_converged=False; aligned_decisions=6/6 | Keep convergence/model-selection caveats visible when using locally generated theta as an identity-conditioning variable. |
| MV12_design_boundary | `ready_to_implement_mv12_two_stage_latent_target` | full_method_allowed=False; theta targets, fitted parameters, row predictions, and transformed features are local-only. | Reuse the same local-only latent-score and residualization boundary for MV15. |

## Dataset Scopes

| scope | datasets | status | interpretation |
| --- | --- | --- | --- |
| S1_primary_edaic_cmdc_phq | edaic;cmdc | `primary_ready_to_implement` | Primary MV15 identity evidence; still diagnostic, not a deployable method. |
| S2_predicted_theta_output_identity | edaic;cmdc | `secondary_ready_to_implement` | Tests whether a latent output is less dataset-identifiable than observed-scale outputs. |
| S3_cmdc_pdch_total_sensitivity | cmdc;pdch | `severity_sensitivity_only` | Report as severity-conditioned diagnostic only; do not mix with primary PHQ theta claims. |
| S4_three_way_total_norm_sensitivity | edaic;cmdc;pdch | `diagnostic_sensitivity_only` | Tracks broad dataset identity risk but cannot authorize cross-scale latent claims. |

## Variables

| variable | role | allowed use | tracked policy |
| --- | --- | --- | --- |
| D_dataset | identity_target | Diagnostic target only; never an input to deployable depression prediction. | Aggregate class counts and balanced-accuracy summaries only. |
| Z_bge | feature_representation | Identity-probe input after train-fold residualization or common-support restriction. | Aggregate feature-family and column-count summaries only. |
| Y_items | observed_label_condition | Diagnostic conditioning variable and theta-generation input. | Aggregate item coverage and response-support summaries only. |
| theta_label | latent_condition | Primary MV15 conditioning variable for D\|Z,theta and theta-only controls. | Aggregate theta coverage, distribution bins, reliability, and identity metrics only. |
| T_total | dimension_matched_observed_severity_condition | Primary comparator to theta conditioning; answers whether identity reduction is more than low-dimensional severity compression. | Aggregate distribution bins, common-support counts, and identity metrics only. |
| S_pred_total | dimension_matched_predicted_total_output | Output identity comparator for predicted theta. | Aggregate utility and identity metrics only. |
| S_b3_itemwise_theta | dimension_matched_direct_itemwise_severity_output | Critical comparator because MV12 B3 has lower identity and better observed fidelity than M12a in aggregate. | Aggregate utility and identity metrics only. |
| theta_pred | predicted_latent_output | Secondary identity target/output diagnostic. | Aggregate identity and utility summaries only. |
| C_covariates | legitimate_covariate_condition | Sensitivity conditioning only when coverage and missingness are reported. | Aggregate coverage and missingness summaries only. |

## Conditioning Ladder

| ladder | estimand | variables | rule |
| --- | --- | --- | --- |
| L0_D_given_Z_raw | D\|Z | none | Report balanced accuracy by seed and aggregate mean/std. |
| L1_D_given_Z_and_total | D\|residual(Z ~ normalized_total) | normalized PHQ total | Residualizer fitted on train fold only; evaluation covariates can be used only for diagnostic residualization. |
| L2_D_given_Z_and_predicted_total | D\|residual(Z ~ predicted_total) | fold-generated predicted total score | Generate predicted total inside the same subject-level folds; export aggregate identity only. |
| L3_D_given_Z_and_items | D\|residual(Z ~ C01-C08) | observed PHQ C01-C08 items | Repeat MV09 item-conditioned residualization as the direct comparator. |
| L4_D_given_Z_and_b3_itemwise_theta | D\|residual(Z ~ theta_from_direct_itemwise_predictions) | direct itemwise Ridge predictions compressed to theta | Regenerate B3-like direct itemwise predictions locally under the same folds; no row predictions exported. |
| L5_D_given_Z_and_theta | D\|residual(Z ~ theta_label) | label-derived PHQ theta | Theta must be generated within the fold or from a predeclared local-only measurement fit; no theta scores exported. |
| L6_D_given_Z_theta_covariates | D\|residual(Z ~ theta_label + legitimate_covariates) | theta_label;available shared covariates | Run only for covariates with coverage in both datasets; otherwise export a skipped aggregate row. |
| L7_D_given_theta_only | D\|theta_label | theta_label only | Train classifier on theta or theta-bin only and report common-support bins. |
| L8_D_given_predicted_outputs | D\|theta_pred and residual(theta_pred ~ theta_label,total) | predicted total;B3 direct-item theta;psychometric predicted theta;true theta;observed total | Regenerate local predicted total, B3 itemwise-compressed theta, and M12a-like theta under the same split audit; export aggregate identity only. |
| L9_severity_only_sensitivity | D\|residual(Z ~ normalized_total) | normalized total severity | No shared theta wording; report as sensitivity while MV16 is pending. |

## Identity Probes

| probe | scope | representation | future rule |
| --- | --- | --- | --- |
| P1_primary_feature_identity_given_theta | S1_primary_edaic_cmdc_phq | residualized_Z_bge | Preferred pass only if theta-conditioned BA <= 0.70 and is at least 0.03 lower than total-, predicted-total-, and B3-itemwise-theta-conditioned BA; partial support if BA <= 0.75 and not worse than all dimension-matched controls; blocked if BA > 0.80 or B3/total dominates. |
| P2_theta_distribution_identity | S1_primary_edaic_cmdc_phq | theta_label_or_theta_bins | Report-only diagnostic; high BA means dataset populations differ along latent severity. |
| P3_feature_identity_given_total_items_b3_vs_theta_delta | S1_primary_edaic_cmdc_phq | residualized_Z_bge | Theta conditioning must be reported against MV09 item-conditioned BA plus total, predicted-total, and B3 itemwise-theta controls. |
| P4_predicted_theta_output_identity | S2_predicted_theta_output_identity | predicted_total;B3_itemwise_theta;theta_pred | M12a-like theta output must be compared with MV12 B3 conditional BA around 0.579 and M12a around 0.602; it cannot be called theta-specific identity reduction if B3 or predicted total is lower. |
| P5_dimension_matched_severity_identity_controls | S1_primary_edaic_cmdc_phq;S2_predicted_theta_output_identity | one_dimensional_observed_or_predicted_severity | Report whether theta is Pareto-dominated by total/predicted-total/B3 controls on identity BA and observed macro MAE. |
| P6_covariate_sensitivity | S1_primary_edaic_cmdc_phq | residualized_Z_bge | Run only for covariates with enough coverage in both datasets; otherwise skipped with reason. |
| P7_severity_only_external_sensitivity | S3_cmdc_pdch_total_sensitivity;S4_three_way_total_norm_sensitivity | residualized_Z_bge | Report as sensitivity; no pass can authorize cross-scale latent claims before MV16. |

## Gates

| gate | status | future run rule | effect |
| --- | --- | --- | --- |
| G1_input_scope | `predeclared` | Future MV15 runner reads only manifest-governed BGE/label inputs plus aggregate MV09-MV14 references; no raw media or private review material. | Violation invalidates MV15. |
| G2_subject_level_splits | `predeclared` | All identity probes use subject-level folds with zero overlap violations. | Any overlap keeps all MV15 identity claims blocked. |
| G3_theta_local_only | `predeclared` | No theta scores, fitted item parameters, residualized feature matrices, row predictions, or nuisance directions are tracked. | Any tracked local-only artifact invalidates the run until removed. |
| G4_reference_reporting | `predeclared` | Report raw identity, total conditioning, predicted-total conditioning, item conditioning, B3 itemwise-theta conditioning, theta conditioning, and theta-only controls together. | A single favorable conditional BA cannot be cited alone. |
| G5_primary_identity_threshold | `predeclared` | Preferred pass if theta-conditioned feature identity BA <= 0.70 and at least 0.03 lower than every dimension-matched severity control; partial support if <=0.75 and tied with controls; blocked if BA >0.80 or any B3/total control dominates both identity and fidelity. | Even a pass only permits MV16 predeclaration or bounded diagnostic wording, not full M0/M1/M2/M3. |
| G6_output_identity_boundary | `predeclared` | Predicted-theta identity must be reported separately from predicted-total, B3 itemwise-theta, and post-mapping observed-scale identity. | High observed-scale identity or B3/predicted-total dominance blocks theta-specific wording even if theta output identity is low. |
| G7_external_sensitivity_boundary | `predeclared` | CMDC/PDCH and three-way probes are severity-only sensitivity rows until MV16 supplies scale-linking. | No cross-scale PHQ-HAMD latent claim from MV15 alone. |
| G8_artifact_hygiene | `predeclared` | Tracked outputs contain only aggregate contracts, coverage, metrics, gate results, reports, and memory. | Hygiene failure blocks publishing and claim refresh. |

## Implementation Queue

| rank | action | success gate |
| ---: | --- | --- |
| 1 | Implement the future MV15 runner with fold-safe theta generation, residualized BGE identity probes, total/predicted-total/B3 severity controls, theta-only controls, predicted-output identity, and severity-only sensitivity scopes. | Aggregate outputs cover L0-L9, P1-P7, zero split overlap, and hygiene without tracked local-only artifacts. |
| 2 | Rerun the full-method gate after the MV15 runner. | Gate distinguishes feature identity, latent-conditioned feature identity, theta output identity, and observed-scale identity. |
| 3 | If MV15 is interpretable, predeclare MV16 DIF-guided cross-dataset theta calibration and few-shot scale linking. | MV16 compares zero-shot, global affine/monotonic, C02/C06 DIF-guided threshold calibration, all-threshold calibration, and direct adaptation with local-only calibration parameters and aggregate curves. |
| 4 | If MV15 remains high-identity after theta conditioning, freeze the current latent-conditioned identity line as diagnostic evidence. | Paper framing states that measurement-aware latent targets do not remove dataset identity under the current BGE contract. |

## Interpretation Boundary

- MV15 can update the identity-gate interpretation only after the future runner produces aggregate results.
- MV15 does not authorize full M0/M1/M2/M3 method construction.
- A favorable theta-conditioned identity result still needs MV16 scale calibration before cross-scale latent transfer claims.
- If identity remains high after theta conditioning, freeze this line as diagnostic evidence for dataset-specific representation shift.
