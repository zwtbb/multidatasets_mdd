# P5_MV16 DIF-Guided Few-Shot Measurement Calibration Design

Generated: `2026-08-14T05:15:00+00:00`

## Scope

This is a predeclared design contract. It does not run calibration, train a full method, export participant-grain theta scores, export calibration parameters, export target-shot sampling maps, or authorize feature-invariance claims.

## Decision

- Design status: `ready_to_implement_mv16_dif_guided_calibration`.
- Recommended next action: `implement_scripts_phase5_run_mv16_dif_guided_calibration`.
- Full method allowed: `False`.
- Artifact hygiene passed: `True`.

MV16 is predeclared as a few-shot measurement-calibration test: use MV14-stable anchors C01/C04/C05/C07, calibrate localized C02/C06 threshold DIF under k=0/5/10/20/40 target-label budgets, and compare against zero-shot, global affine/monotonic, all-threshold, and direct target-adaptation baselines. It is diagnostic only.

## Source Evidence

| source | status | observation | implication |
| --- | --- | --- | --- |
| full_gate_context | `blocked_but_publishable_diagnostic_direction` | phase5_summary_count=39; full_method_allowed=False; top_next_action=NEXT_IMPLEMENT_MV16_DIF_GUIDED_CALIBRATION_RUNNER | MV16 design and execution must stay under the full-method gate; it cannot start full M0/M1/M2/M3 construction. |
| mv10_mv11_anchor_map | `complete_formal_partial_invariance_supported_with_bic_caveat` | MV10_loading_congruence=0.998; MV11_confirmed_anchors=C01;C04;C05;C07; MV11_threshold_DIF_items=C02;C06; MV11_loading_DIF_flags=0 | Lock C01/C04/C05/C07 as anchors and treat C02/C06 threshold offsets as the primary DIF-guided calibration target. |
| mv13_external_replication | `complete_external_mirt_with_convergence_warnings` | confirmed_anchors=4; loading_DIF_flags=0; threshold_DIF_flags=2; core_converged=False; AIC_BIC=partial_mv10/scalar | Use the external psychometric replication as qualitative support only; future fitted parameters stay local-only. |
| mv14_bootstrap_stability | `complete_mv14_convergence_safe_item_level_measurement_shift` | stable_anchors=C01;C04;C05;C07; top_threshold_DIF=C02;C06; core_effective_R=120/200; stable_ladder_R=197; DIF_effective_R=77/100 | Use only item-level stable-anchor and localized C02/C06 threshold-DIF wording; global model-selection remains uncertain. |
| mv12_zero_shot_transfer_failure | `blocked_theta_gain_not_observed_scale_safe` | transfer_protocols=2; theta_transfer_failed_protocols=2; same_dataset_theta_gate=True; observed_scale_safety=False; external_theta_gate=False | MV16 must test target measurement calibration, not another source-only X-to-theta head. |
| mv12_dimension_matched_caveat | `complete_freeze_current_mv12_latent_target_line` | freeze_current_latent_target_line=True; b3_caveat=M12a low identity is not unique: B3 direct itemwise Ridge has lower conditional and unconditional predicted-theta identity in the aggregate MV12 summary. | Future calibration must keep direct itemwise and total-based adaptation as comparators, not just latent theta. |
| mv15_latent_conditioned_identity | `blocked_theta_conditioned_feature_identity_high` | raw_feature_BA=1.000; theta_conditioned_feature_BA=1.000; total_predtotal_b3_feature_BA=1.000/1.000/1.000; blocked_gates=G5_primary_identity_threshold | Treat MV16 as measurement-mapping calibration under high feature-identity risk; do not use it to claim invariant BGE features. |

## Directions

| direction | source | target | k | boundary |
| --- | --- | --- | --- | --- |
| D1_edaic_source_cmdc_target | edaic | cmdc | 0;5;10;20;40 | May support target measurement calibration if gates pass; cannot support language-invariant or feature-invariant claims. |
| D2_cmdc_source_edaic_target | cmdc | edaic | 0;5;10;20;40 | Use as direction robustness only because source CMDC item-labeled N is small. |
| D3_within_target_fewshot_sanity | edaic_or_cmdc | same_target | 0;5;10;20;40 | Report as a target-domain upper/lower bound; not cross-dataset transfer evidence by itself. |
| D4_pdch_hamd_linking_deferred | cmdc_or_edaic | pdch | not_primary | PDCH remains a severity-only diagnostic/sensitivity dataset, not a shared PHQ-HAMD latent target. |

## Item Roles

| construct | role | threshold freq | anchor support | policy |
| --- | --- | ---: | ---: | --- |
| C01 | `locked_anchor` | 0.000 | 0.959 | Keep loading and thresholds fixed to the source/common anchor map except for global theta scale calibration. |
| C02 | `primary_dif_threshold_calibration` | 0.800 | 0.156 | Calibrate target threshold offsets first; keep loading shared unless a later design predeclares loading DIF. |
| C03 | `sensitivity_non_anchor` | 0.020 | 0.980 | Keep fixed in the primary ladder; allow only aggregate sensitivity reporting. |
| C04 | `locked_anchor` | 0.040 | 0.929 | Keep loading and thresholds fixed to the source/common anchor map except for global theta scale calibration. |
| C05 | `locked_anchor` | 0.020 | 0.969 | Keep loading and thresholds fixed to the source/common anchor map except for global theta scale calibration. |
| C06 | `primary_dif_threshold_calibration` | 0.760 | 0.247 | Calibrate target threshold offsets first; keep loading shared unless a later design predeclares loading DIF. |
| C07 | `locked_anchor` | 0.000 | 0.969 | Keep loading and thresholds fixed to the source/common anchor map except for global theta scale calibration. |
| C08 | `sensitivity_possible_loading_or_threshold` | 0.020 | 0.796 | Report as sensitivity; do not add it to the primary DIF-guided set unless MV16 run evidence and a later design justify it. |

## Calibration Ladder

| ladder | target labels | free parameters | role |
| --- | --- | --- | --- |
| L0_zero_shot_source_measurement | 0 | none beyond source-trained measurement/prediction artifacts | required lower-bound baseline and MV12 external-transfer reproduction |
| L1_global_affine_theta_calibration | k | global intercept and slope only | tests whether source failure is mostly a global latent-scale mismatch |
| L2_global_monotonic_theta_calibration | k | monotonic calibration function with minimum-bin guard | must not be used as primary evidence if k support is too sparse |
| L3_dif_guided_C02_C06_threshold_calibration | k | C02 and C06 threshold offsets only; anchors C01/C04/C05/C07 fixed | preferred measurement-calibration test |
| L4_anchor_plus_dif_joint_calibration | k | global theta affine parameters and C02/C06 threshold offsets | secondary preferred row; must beat L1 and L3 or reveal their tradeoff |
| L5_all_threshold_target_calibration | k | all PHQ C01-C08 item threshold offsets | upper-bound/overfit-risk comparator; not automatically preferable to L3/L4 |
| L6_direct_target_domain_adaptation | k | direct target prediction head parameters | critical comparator; if it dominates, MV16 is a practical adaptation result, not psychometric calibration evidence |

## Metrics

| metric | primary | direction | interpretation |
| --- | --- | --- | --- |
| M1_theta_mae | `True` | lower_is_better | Calibration improves latent severity transfer only if it beats zero-shot and target train-mean floors. |
| M2_observed_macro_item_mae | `True` | lower_is_better | Theta improvement is not safe if observed-scale item reconstruction degrades against direct itemwise baselines. |
| M3_dif_item_mae | `True` | lower_is_better | DIF-guided calibration should improve the items it claims to fix. |
| M4_anchor_item_mae | `True` | lower_is_better | C02/C06 threshold calibration must not damage stable-anchor behavior. |
| M5_total_mae | `False` | lower_is_better | Total-score safety guard for clinical severity interpretation. |
| M6_rank_correlation | `False` | higher_is_better | Monotonic calibration should preserve severity ranking. |
| M7_output_identity | `False` | lower_is_better | Report shortcut risk; do not conflate output identity with upstream BGE feature invariance. |
| M8_learning_curve | `True` | contextual | MV16 is strongest if DIF-guided calibration helps at small k, not only at k=40. |

## Gates

| gate | status | future run rule | effect |
| --- | --- | --- | --- |
| G1_input_scope | `predeclared` | Runner reads only manifest-governed PHQ item labels/features plus aggregate Phase 5 context; no raw text/media or private review material. | Scope violation blocks MV16 publication and any claim refresh. |
| G2_subject_level_fewshot_splits | `predeclared` | Every direction/k/seed has zero overlap among source train, target calibration, and target evaluation subjects. | Any overlap blocks calibration claims. |
| G3_ladder_completeness | `predeclared` | Report L0-L6 for k=0/5/10/20/40 where feasible, with skipped rows explicit and justified. | Incomplete comparator ladder blocks positive MV16 interpretation. |
| G4_dif_guided_small_k_gain | `predeclared` | Primary support requires L3 or L4 to improve target Theta MAE by at least 0.03 versus L0 and improve C02/C06 MAE versus L1 in both directions for at least one k<=20. | If unmet, MV16 is negative or inconclusive measurement-calibration evidence. |
| G5_anchor_safety | `predeclared` | L3/L4 anchor-item MAE may not degrade by more than 5 percent relative to L1 global calibration at the same k/direction. | Anchor degradation blocks DIF-guided wording even if C02/C06 improve. |
| G6_dimension_matched_baseline | `predeclared` | L3/L4 must be compared with B2 direct itemwise target adaptation and L6 direct target-domain adaptation under the same k; if direct baselines dominate theta and observed macro MAE, report practical adaptation rather than psychometric calibration. | Direct-baseline dominance blocks a positive measurement-calibration mechanism claim. |
| G7_identity_boundary | `predeclared` | Report output identity BA by model; do not report any MV16 result as BGE feature invariance because MV15 already blocked that claim. | Identity wording remains diagnostic only unless a later feature-level design changes the evidence. |
| G8_artifact_hygiene | `predeclared` | Tracked outputs contain only aggregate contracts, curves, metric summaries, gate results, reports, and memory. | Hygiene failure blocks GitHub publishing and manuscript updates. |

## Implementation Queue

| rank | action | success gate |
| ---: | --- | --- |
| 1 | Implement the MV16 runner with source/target directions, k=0/5/10/20/40 sampling, L0-L6 calibration ladder, direct baselines, aggregate metric curves, identity diagnostics, split audits, and hygiene checks. | All predeclared gates are evaluated from aggregate outputs only; local theta/calibration/row artifacts remain ignored. |
| 2 | Rerun the full-method gate after the MV16 run and update paper claim scaffolds. | Gate distinguishes measurement calibration evidence from feature invariance and full-method authorization. |
| 3 | If RQ4 wording becomes manuscript-critical, add aggregate agreement uncertainty and resolve the one incomplete local MV06 candidate. | Aggregate confidence intervals remain dataset-stratified and do not expose snippets, locators, or subject rows. |

## Interpretation Boundary

- MV16 can support target measurement calibration only if it beats zero-shot and dimension-matched/direct few-shot baselines under the predeclared gates.
- MV16 cannot override MV15's feature-identity blocker; low output identity or improved calibration is not upstream BGE invariance.
- PHQ-HAMD scale linking remains out of scope for MV16 unless a later separate contract is written.
- Full M0/M1/M2/M3 method construction remains blocked until the full-method gate changes after a completed run.
