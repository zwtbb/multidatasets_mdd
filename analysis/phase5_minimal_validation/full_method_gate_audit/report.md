# Phase 5 Full-Method Gate Audit

Generated: `2026-08-22T13:28:00+00:00`

## Decision

- Full method allowed: `False`.
- Gate status: `blocked_but_publishable_diagnostic_direction`.
- Blocked claim count: `5`.
- Allowed limited/reframed claim count: `7`.

The current evidence supports a careful diagnostic paper direction, but not a broad full symptom-aligned method claim yet.

## Claim Gate

| claim | decision | allowed scope | required next evidence |
| --- | --- | --- | --- |
| C_FULL_METHOD_START | `blocked` | No full method construction yet. | Do not start full method construction; interpret MV16/MV20 as bounded or negative mechanism checks and prioritize manuscript finalization. |
| C_RQ1_SHARED_SYMPTOM | `blocked` | Discuss direct shared-symptom mapping as negative/bounded diagnostic evidence and reframe RQ1 as measurement-shift and measurement-validity work. | A stronger shared-representation or calibration mechanism would need a genuinely new predeclared data/feature/measurement source; current MV16 is bounded/negative. |
| C_PSYCHOMETRIC_INVARIANCE_BASELINE | `allowed_limited` | Use MV10/MV11/MV19 as primary label-only PHQ common-structure and dataset-group measurement-shift evidence with explicit finite-sample downgrade. Use corrected MV13/MV14 as anchor-linked external mirt qualitative and uncertainty corroboration, while retaining the configural convergence warning and MV19 observed-N caveat. | No further mirt correctness rerun is queued; only consider a larger MV14 bootstrap if reviewer-facing interval precision becomes critical. |
| C_PDCH_HAMD_INTERNAL | `allowed_limited` | PDCH-only HAMD item/total diagnostic plus MV18 exploratory same-HAMD context-shift support; not cross-dataset HAMD generalization. | A stronger CMDC/PDCH-compatible measurement head or larger external HAMD item sample is required before cross-dataset HAMD claims. |
| C_EATD_SDS_GENERALIZATION | `blocked` | Report EATD as negative/weak SDS external stress. | A separately audited feature contract with meaningful SDS improvement over train mean and no stronger valence shortcut. |
| C_DATASET_IDENTITY_CONTROL | `allowed_limited` | Known-dataset centering, source-agnostic WavLM projection, BGE identity projection, BGE total-anchor diagnostics, conditional identity audits, MV15 latent-conditioned identity, and MV17a multilingual feature-contract sensitivity are controls; do not claim invariant representation. | Freeze the current latent-conditioned feature-identity line as diagnostic evidence; keep output-space low identity separate from feature invariance and keep encoder-dependent MV17a comparisons explicit. |
| C_PROTOCOL_CRITERION_OVERLAP | `allowed_limited` | Use MV20 as a bounded negative CMDC-only criterion-overlap deletion stress test: high-overlap deletion is not clearly worse than matched random deletion under the primary BGE-M3 PHQ-9 top-20 gate. | No further MV20 tuning or new architecture; freeze experiments after MV20 and move to manuscript finalization. |
| C_MODMA_TASK_CONTROL | `allowed_limited` | MODMA task-specific diagnostic protocol-control result. | Integrate with shared-symptom targets and cross-dataset controls before using it as a full method component. |
| C_EATD_VALENCE_ADVERSARIAL | `blocked` | Do not add a valence-adversarial module from current EATD evidence. | Meaningful EATD SDS or depression signal plus demonstrated valence identity/shortcut reduction. |
| C_RQ3_CONTEXT_CONDITIONING | `blocked` | Report MPDD context calibration as negative and keep age/personality as measurement-heterogeneity audit axes. | A later measurement-invariance/DIF moderator analysis must improve subgroup behavior beyond AV-only recalibration and shuffled controls before positive RQ3 conditioning claims. |
| C_RQ4_EVIDENCE_LOCALIZATION | `allowed_limited` | Use first-round aggregate MV06 annotation and dataset-stratified agreement as credibility evidence; verbatim excerpts remain local-only. | For a stronger manuscript claim, resolve any remaining incomplete local candidate rows and discuss dataset-specific kappa CIs plus sampling limits. |
| C_PUBLISHABLE_PAPER_DIRECTION | `allowed_with_reframing` | A measurement-shift / measurement-validity paper direction is viable now; MV08/MV08b/MV09/MV10/MV11/MV12/MV13/MV14, the mirt parameterization audit, MV12 aggregate tradeoff analysis, MV15, MV16, MV17a, MV18, MV19, and MV20 are bounded diagnostic evidence, not a full-method pass. | Consolidate the manuscript around bounded diagnostic evidence, MV19-downgraded C02/C06 wording, the corrected mirt parameterization audit, MV17a-calibrated BGE-M3-primary/multilingual-E5-sensitivity prediction-consequence wording, and the negative CMDC-only MV20 criterion-overlap stress result. |

## Evidence Inventory

| evidence | status | pass-rule status | hygiene | short read |
| --- | --- | --- | --- | --- |
| P5_MV01 | `complete` | `complete_diagnostic_weak_asymmetric` | `True` | The PHQ core bridge is runnable but weak and asymmetric: pooled Ridge helps only selectively, while frozen WavLM dataset identity remains perfectly recoverable, so this row is a diagnostic baseline rather than evidenc... |
| P5_MV02_readiness | `complete` | `ready_pdch_only_mode` | `True` | complete |
| P5_MV02 | `complete` | `pass_pdch_only_diagnostic` | `True` | MV02 is a useful PDCH-only diagnostic: shallow frozen-feature heads beat train-mean severity baselines and provide item-level HAMD summaries. This supports running a bounded HAMD auxiliary bridge, but it is not yet a ... |
| P5_MV02b | `complete` | `blocked_weak_pdch_text_measurement_signal` | `True` | PDCH text hashing is runnable but weak: the best item-derived HAMD total gain is below the predefined meaningful-improvement threshold. Keep it as a diagnostic result. |
| P5_MV03 | `complete` | `blocked_no_sds_generalization` | `True` | The EATD SDS total heads are runnable, but none beat the train-mean floor on validation MAE; treat this as weak external stress evidence. |
| P5_MV03b | `complete` | `blocked_no_meaningful_text_sds_generalization` | `True` | The EATD text semantic heads are runnable, but the best validation MAE gain over train mean is below the predefined meaningful-improvement threshold; treat this as weak/negative SDS text evidence. |
| P5_MV04 | `complete` | `pass_minimal_control` | `True` | The train-fold dataset-centering control reduces held-out E-DAIC-vs-CMDC identity probe balanced accuracy while preserving PHQ C01-C08 Macro MAE within the 5 percent relative tolerance versus the pooled shared baseline. |
| P5_MV04b | `complete` | `partial_pass_identity_reduced_not_removed` | `True` | The source-agnostic projection reduces held-out prediction identity and preserves PHQ C01-C08 Macro MAE within tolerance, but feature-layer dataset identity remains high; treat it as a partial diagnostic control and k... |
| P5_MV04c | `mixed_protocol_control` | `mixed_protocol_control` | `True` | P5_MV04c tests train-fold protocol-label nuisance projection on MODMA task slices and EATD valence slices. Treat passing rows as diagnostic controls only; no transformed features, projection parameters, or row-level p... |
| P5_MV05 | `complete` | `blocked_no_context_calibration_gain` | `True` | The MPDD context-calibration row is runnable, but the proposed AV-probability-plus-context calibrator does not improve age/personality subgroup ECE gaps over the AV baseline strongly enough for a positive RQ3 claim. |
| P5_MV06_readiness | `complete` | `ready_for_local_evidence_annotation` | `True` | MV06 can proceed as a local-only evidence annotation workflow for datasets with prediction-text overlap. The next step should sample candidates from the local queue, inspect verbatim excerpts locally, and commit only ... |
| P5_MV06_pilot | `complete` | `ready_for_manual_local_annotation` | `True` | A bounded MV06 local annotation packet is ready. It should be annotated locally and later summarized only as aggregate evidence agreement, prompt-artifact rate, evidence-source distribution, and construct coverage. |
| P5_MV06_workbench | `complete` | `ready_for_local_human_annotation` | `True` | A two-annotator local MV06 workbook is ready. It contains local text locators and private free-text fields only in ignored local files; tracked outputs are schema and hygiene summaries only. |
| P5_MV06_summary | `complete` | `ready_for_aggregate_evidence_review` | `True` | Aggregate annotation counts and pairwise agreement are ready for human review; verbatim excerpts and subject-level rows remain local-only. |
| P5_MV06_ai_preannotation | `complete` | `ready_for_human_review_not_claimable` | `True` | AI triage filled a local-only preannotation workbook. It can accelerate human review, but it does not satisfy MV06 human annotation or agreement gates. |
| P5_MV06_review_pack | `complete` | `ready_for_human_review_pack_not_claimable` | `True` | A local review pack now combines AI suggestions, human annotation fields, and priority ranks. It can speed manual review but does not satisfy MV06 annotation, agreement, or RQ4 evidence gates. |
| P5_MV07_edaic_bge_generation | `complete_local_feature_cache_generated` | `complete_local_feature_cache_generated` | `True` | complete_local_feature_cache_generated |
| P5_MV07_readiness | `complete` | `ready_to_run_minimal_validation` | `True` | The aligned BGE text contract is ready: E-DAIC, CMDC, and PDCH now share 512 BGE model-input columns. This authorizes the next MV07 shallow validation row, not a shared-symptom claim yet. |
| P5_MV07 | `complete` | `blocked_not_better_than_total_allocation_bge_contract` | `True` | Aligned BGE MV07 is a shallow validation result. Interpret it through pooled PHQ gains, PDCH HAMD-proxy sanity, and identity probes; readiness alone is not a shared-symptom claim. |
| P5_MV07b | `complete` | `partial_identity_reduced_not_total_floor_beating_bge_projection` | `True` | MV07b tests an inference-compatible BGE identity projection for the pooled E-DAIC/CMDC PHQ C01-C08 contract. A positive claim requires preserved construct MAE, gains over simple floors, and reduced feature/prediction ... |
| P5_MV07c | `complete` | `blocked_not_better_than_raw_total_allocation_bge_total_anchor` | `True` | MV07c tests whether identity-projected BGE itemwise heads add construct value after a train-fold-selected total anchor. It is a shallow validation row, not the full method. |
| P5_MV08_design | `complete` | `ready_to_implement_partial_invariance_validation` | `True` | MV08 is ready to implement as a minimal-validation row: active item supervision exists for E-DAIC PHQ-8, CMDC PHQ-9, and PDCH HAMD-17. The row should compare total-score, fixed-map, and partial-invariance ordinal late... |
| P5_MV08 | `complete` | `blocked_not_better_than_total_score_floor` | `True` | MV08 tests whether an explicitly partial measurement-invariance contract improves over total-score and fixed-map floors. Treat a pass as bounded RQ1 measurement evidence only, not full-method authorization. |
| P5_MV08_error_analysis | `complete` | `complete_current_mv08_not_claimable_revision_or_freeze` | `True` | MV08 error analysis confirms the current partial-invariance ordinal head should be frozen as negative evidence unless a predeclared MV08b revision changes the measurement mechanism. The total-score floor remains the k... |
| P5_MV08b_design | `complete` | `ready_to_implement_mv08b_total_anchored_residual_measurement` | `True` | MV08b is predeclared as a total-anchored residual measurement revision: predict severity first, model item residuals only after anchoring, pool or collapse sparse thresholds, and keep HAMD as a separate clinical stres... |
| P5_MV08b | `complete` | `blocked_prediction_identity_increased_vs_mv08` | `True` | MV08b tests whether item residuals add construct information after a total-severity anchor. Treat a pass as bounded RQ1 measurement evidence only, not full-method authorization. |
| P5_MV09 | `complete` | `complete_identity_gate_revision_needed` | `True` | Unconditional dataset identity should be treated as a shortcut-risk screen; future gates need conditional identity for shared latent claims. |
| P5_MV10 | `complete` | `complete_partial_invariance_supported_approx` | `True` | Label-only PHQ screen supports a common one-factor structure and partial anchors, but threshold/scalar invariance remains approximate and must be treated as measurement-shift evidence. |
| P5_MV11 | `complete` | `complete_formal_partial_invariance_supported_with_bic_caveat` | `True` | Formal label-only graded-response IRT confirmation preserves the C01/C04/C05/C07 anchor map, flags sparse loading DIF and C02/C06 threshold DIF, and keeps an AIC/BIC caveat. |
| P5_MV12_design | `complete` | `ready_to_implement_mv12_two_stage_latent_target` | `True` | Design is ready; the actual MV12 X_to_theta run is still required before any full-method or transferable shared-latent claim. |
| P5_MV12 | `complete` | `blocked_theta_gain_not_observed_scale_safe` | `True` | MV12 runs the predeclared two-stage PHQ latent-target test. A pass requires theta utility, observed-scale safety, external transfer, conditional shared-latent identity, leakage control, and artifact hygiene; design or... |
| P5_MV12_analysis | `complete` | `complete_freeze_current_mv12_latent_target_line` | `True` | Aggregate-only MV12 analysis recommends freezing the current latent-target line: latent/scalar outputs are less dataset-identifiable than upstream BGE features, but M12a is not better than the dimension-matched B3 sev... |
| P5_MV13_design | `complete` | `ready_for_external_replication_run` | `True` | MV13 is predeclared as an external mirt/lavaan psychometric replication. Execution waits for a version-captured external runtime. |
| P5_MV13 | `complete` | `complete_external_mirt_with_convergence_warnings` | `True` | External R mirt replication preserves the label-only PHQ anchor/DIF localization pattern with corrected anchor-linked focal mean/variance handling, a configural convergence warning, and local-only parameter/theta arti... |
| P5_MV14_design | `complete` | `ready_to_implement_mv14_measurement_uncertainty_bootstrap` | `True` | MV14 is predeclared as an aggregate-only bootstrap stability audit for PHQ anchors, DIF flags, model selection, convergence, and uncertainty availability. |
| P5_MV14 | `complete` | `complete_mv14_convergence_safe_item_level_measurement_shift` | `True` | MV14 quantifies PHQ measurement uncertainty from group-wise subject bootstrap with anchor-linked focal mean/variance freed for threshold-constrained models; its convergence-safe interpretation is item-level threshold/... |
| P5_MV15_design | `complete` | `ready_to_implement_mv15_latent_conditioned_identity` | `True` | MV15 design predeclares the latent-conditioned identity ladder; the subsequent P5_MV15 run summary is the current identity result. |
| P5_MV15 | `complete` | `blocked_theta_conditioned_feature_identity_high` | `True` | MV15 reports feature identity after theta conditioning together with total, predicted-total, item, B3 itemwise-theta, theta-only, predicted-output, covariate, and severity-only controls. It is diagnostic only. |
| P5_MV16_design | `complete` | `ready_to_implement_mv16_dif_guided_calibration` | `True` | MV16 design predeclares DIF-guided few-shot measurement calibration with C01/C04/C05/C07 anchors, C02/C06 threshold calibration, k=0/5/10/20/40, and direct/zero-shot/global/all-threshold comparators. |
| P5_MV16 | `complete` | `blocked_no_dif_guided_small_k_gain` | `True` | MV16 completes the predeclared few-shot calibration ladder but does not satisfy the DIF-guided small-k mechanism gate; keep it as negative or bounded diagnostic evidence. |
| P5_MV17a | `complete` | `complete` | `True` | complete |
| P5_MV18 | `complete` | `complete_exploratory_same_scale_context_shift_supported` | `True` | MV18 remains exploratory because CMDC HAMD has only 25 subjects, but the same-scale control still shows dataset/context sensitivity through flagged HAMD item/threshold shifts or weak bidirectional transfer. |
| P5_MV19 | `complete` | `complete_mv19_high_false_localization_downgrade_c02_c06` | `True` | MV19 simulates the observed E-DAIC/CMDC PHQ sample sizes and severity distributions under scalar-invariant and C02/C06 threshold-DIF worlds. It supports cautious C02/C06 wording only if false localization is limited a... |
| P5_MV20 | `complete` | `complete_mv20_no_primary_criterion_overlap_excess` | `True` | complete |
| P5_mirt_parameterization_audit | `complete` | `complete_mirt_parameterization_consistent` | `True` | MV13/MV14 mirt parameterization matches the audited anchor-linked measurement-invariance contract: E-DAIC is reference, CMDC is focal, anchor/threshold linking is explicit, and focal mean/variance are freed for thresh... |

## Next Actions

| rank | action | success gate |
| ---: | --- | --- |
| 1 | Freeze the experiment queue and finalize the measurement-validity manuscript. | Paper claim tables, Results scaffold, and manuscript draft include MV20 as a bounded negative CMDC-only criterion-overlap stress test and do not queue further model or threshold tuning. |
| 2 | Use the dataset-stratified MV06 agreement and bootstrap uncertainty summaries as first-round RQ4 evidence, then resolve any incomplete local candidate rows if stronger wording is needed. | Dataset-stratified agreement and uncertainty summaries remain aggregate-only without exporting snippets or source locators. |
| 3 | Recover or create speaker/protocol labels for E-DAIC participant/interviewer controls if feasible. | Speaker-resolved subject-level controls with no leakage and aggregate-only outputs. |
| 4 | Try to recover structured MPDD gender/health metadata and official test labels as a governance update. | Registry/manifest update plus audit showing coverage and no split leakage. |
| 5 | Decide later whether the public remote history needs rewrite or repository recreation. | No force-push or repository recreation happens without an explicit decision from the user. |

## Interpretation Boundary

This audit is deliberately conservative. A row marked `allowed_limited` can appear in the paper as bounded diagnostic evidence, but it does not authorize a broad method claim. Full-model work should start only after the blocked gates are addressed or the paper is explicitly reframed around diagnostics, negative results, and a bounded method proposal.
