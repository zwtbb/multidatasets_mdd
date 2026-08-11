# P5_MV08b Total-Anchored Residual Measurement Design

Generated: `2026-08-11T12:13:34+00:00`

## Scope

This design predeclares one mechanism-changing revision after the negative MV08 pilot. It does not train a model, read raw text, export row-level predictions, or authorize full-method construction.

## Decision

- Readiness status: `ready_to_implement_mv08b_total_anchored_residual_measurement`.
- Recommended next action: `IMPLEMENT_MV08B_RUNNER`.
- Artifact hygiene passed: `True`.

MV08b is predeclared as a total-anchored residual measurement revision: predict severity first, model item residuals only after anchoring, pool or collapse sparse thresholds, and keep HAMD as a separate clinical stress test. Full-method work remains blocked until MV08b is run and passes.

## Why MV08b Is Not A Retune

MV08 let lightweight item heads reconstruct ordinal item scores directly. MV08b first anchors scale severity, then asks whether item residuals add transferable construct information after that severity is controlled. If the residual layer cannot beat the total-score floor, the RQ1 result stays negative.

## Source Evidence

| source | observation | implication |
| --- | --- | --- |
| MV08_result | status=blocked_not_better_than_total_score_floor; m2_improved_vs_total_slices=0; prediction_identity_ba_m2=0.900 | Do not continue the original M2 as positive RQ1 evidence; any revision must change the mechanism and keep identity from increasing. |
| MV08_error_gate | failed_total_floor_slices=3; failed_fixed_map_slices=3; worst_delta_vs_total=0.152 | Total-score and fixed-map floors stay mandatory comparators; MV08b cannot pass through pooled-only averaging. |
| largest_item_error | dataset=cmdc;scale=PHQ-9;item=PHQ9_8;construct=C08;delta_vs_total=0.698;bias=1.103 | Model residuals after severity anchoring so item-specific overprediction cannot masquerade as shared latent symptom signal. |
| threshold_sparsity | protocol=pdch_hamd_subject_cv;dif_policy=scale_or_item_specific_dif;constant_threshold_fraction=0.318 | Pool thresholds or collapse rare ordinal levels before allowing scale/item-specific threshold deviations. |
| revision_queue_top_action | priority=1;action=FREEZE_MV08_CURRENT_CONTRACT_AS_NEGATIVE | Freeze current MV08 as negative unless the predeclared MV08b mechanism is implemented and independently beats its gates. |
| pooled_slice_edaic | scale=PHQ-8;m2_mae=0.842;delta_vs_total=0.147;delta_vs_fixed=0.140;bias=0.417 | Require dataset-stratified success, not only a pooled average. |
| pooled_slice_cmdc | scale=PHQ-9;m2_mae=0.743;delta_vs_total=0.128;delta_vs_fixed=0.103;bias=0.422 | Require dataset-stratified success, not only a pooled average. |
| pooled_slice_pdch | scale=HAMD-17;m2_mae=0.892;delta_vs_total=0.152;delta_vs_fixed=0.125;bias=0.225 | Require dataset-stratified success, not only a pooled average. |

## Model Ladder

| model | role | severity anchor | residual component | pass gate |
| --- | --- | --- | --- | --- |
| B0_train_mean_items | sanity_floor | none | none | MV08b must beat this floor on active item and item-derived-total summaries. |
| B1_total_score_floor | primary_floor | train_fold_total_score_model_or_total_allocation | none | MV08b must beat this floor on at least two pooled active dataset slices. |
| B2_fixed_construct_map | old_shared_mapping_floor | same_as_B1_where_available | phase4_fixed_item_map_without_learned_DIF | MV08b must beat or narrowly match this floor while reducing interpretable item errors. |
| M2b_total_anchored_residual_measurement | next_executable_RQ1_candidate | predeclared_train_fold_anchor_predicts_total_or_latent_severity_first | sparse_construct_residual_heads_fit_only_on_item_deviation_after_anchor | Beat B1 and B2 on at least two pooled active slices and keep prediction identity BA <= current MV08 M2 identity. |
| M2b_HAMD_external_stress | clinical_measurement_stress_test | PDCH_HAMD_total_anchor_only | HAMD residual heads separate from PHQ shared-core pass decision | HAMD must improve PDCH item and item-derived total metrics beyond floors before any HAMD-compatible claim. |

## Residual Targets

| construct | role | allowed residual | exclusion rule |
| --- | --- | --- | --- |
| C01 | shared_phq_core_residual | allow_small_sparse_item_residual_after_total_anchor | do_not_let_residual_head_reconstruct_total_severity |
| C02 | shared_phq_core_residual | allow_small_sparse_item_residual_after_total_anchor | do_not_let_residual_head_reconstruct_total_severity |
| C03 | shared_phq_core_residual | allow_small_sparse_item_residual_after_total_anchor | do_not_let_residual_head_reconstruct_total_severity |
| C04 | shared_phq_core_residual | allow_small_sparse_item_residual_after_total_anchor | do_not_let_residual_head_reconstruct_total_severity |
| C05 | shared_phq_core_residual | allow_small_sparse_item_residual_after_total_anchor | do_not_let_residual_head_reconstruct_total_severity |
| C06 | shared_phq_core_residual | allow_small_sparse_item_residual_after_total_anchor | do_not_let_residual_head_reconstruct_total_severity |
| C07 | shared_phq_core_residual | allow_small_sparse_item_residual_after_total_anchor | do_not_let_residual_head_reconstruct_total_severity |
| C08 | shared_phq_core_residual | allow_small_sparse_item_residual_after_total_anchor | do_not_let_residual_head_reconstruct_total_severity |
| C09 | explicit_safety_residual | PHQ9_HAMD_explicit_evidence_only_no_imputation_from_total | no_PHQ8_pseudo_item_and_no_local_snippet_export |

## Threshold Policy

| policy | trigger | rule | pass condition |
| --- | --- | --- | --- |
| T0_observed_score_support | before_training | measure per-item observed category counts inside train folds | no item-specific threshold is estimated for a category with insufficient train-fold support |
| T1_collapse_sparse_categories | rare_or_empty_ordinal_levels | collapse adjacent high or low categories by predeclared scale-specific rules before threshold fitting | constant-threshold fraction is lower than current MV08 and rounded-within-one does not degrade materially |
| T2_pool_thresholds_first | default_MV08b | fit pooled thresholds by scale and construct before freeing item-specific offsets | item residual heads improve beyond B1/B2 without diffuse threshold freeing |
| T3_free_offsets_only_after_error_trigger | large_train_fold_residual_error_with_stable_support | allow a scale/item-specific threshold offset only for predeclared high-error items | offsets remain sparse and interpretable; no post-hoc broad freeing |

## Design Gate

| gate | status | evidence | required next |
| --- | --- | --- | --- |
| G_MECHANISM_CHANGED | `pass` | MV08b predicts total severity first and models item residuals only after anchoring. | Implement B0/B1/B2/M2b in one script with subject-level folds. |
| G_TOTAL_FLOOR_PRIMARY | `pass` | MV08 error analysis shows total-score floors are best or near-best across active slices. | B1_total_score_floor remains the primary pass/fail comparator. |
| G_THRESHOLD_SPARSITY_ADDRESSED | `pass` | MV08b predeclares category-support checks, category collapse, and pooled thresholds. | Do not export learned thresholds; export only aggregate sparsity diagnostics. |
| G_HAMD_SEPARATE_STRESS | `pass_limited` | PDCH HAMD remains the only adequately sized HAMD item source; CMDC HAMD is sanity-only. | Do not count HAMD success as a PHQ shared-core pass unless PHQ slices also pass. |
| G_NO_FULL_METHOD_AUTHORIZATION | `blocked_full_method` | MV08b design is a minimal-validation contract, not a full M0/M1/M2/M3 start. | Run and gate MV08b before changing full-method authorization. |

## Implementation Queue

| rank | action | success gate |
| ---: | --- | --- |
| 1 | Create scripts/phase5_run_mv08b_total_anchored_residual_measurement.py. | One run compares B0 train mean, B1 total floor, B2 fixed map, and M2b total-anchored residual heads on the same subject-level slices. |
| 2 | Write row-level residual predictions only to an ignored local file for later aggregate error analysis. | Tracked artifacts contain no subject-level rows, raw text, local locators, or learned parameters. |
| 3 | Run MV08b and rerun scripts/phase5_full_method_gate_audit.py. | Full-method gate changes only if MV08b beats B1/B2 on at least two pooled active slices and identity does not increase. |
| 4 | If MV08b fails, freeze MV08/MV08b as negative RQ1 diagnostic evidence and pivot writing. | Issue log and master plan explicitly state the bounded diagnostic claim. |

## Interpretation Boundary

- MV08b is allowed only as a minimal-validation revision; full M0/M1/M2/M3 construction remains blocked.
- The current MV08 result remains negative unless MV08b independently passes its predeclared gates.
- Any residual or DIF finding must be reported as measurement heterogeneity, not as proof of one dataset-invariant depression representation.
