# Phase 5 Full-Method Gate Audit

Generated: `2026-08-09T16:38:54+00:00`

## Decision

- Full method allowed: `False`.
- Gate status: `blocked_but_publishable_diagnostic_direction`.
- Blocked claim count: `5`.
- Allowed limited/reframed claim count: `5`.

The current evidence supports a careful diagnostic paper direction, but not a broad full symptom-aligned method claim yet.

## Claim Gate

| claim | decision | allowed scope | required next evidence |
| --- | --- | --- | --- |
| C_FULL_METHOD_START | `blocked` | No full method construction yet. | Resolve public manifest/data-governance risk and define a genuinely new audited psychometric measurement contract before revisiting full-method claims. |
| C_RQ1_SHARED_SYMPTOM | `blocked` | Discuss direct shared-symptom mapping as a negative/partial diagnostic and reframe RQ1 toward partial measurement invariance. | Design and audit a multi-scale psychometric measurement row: shared latent constructs plus scale-specific DIF/loading-threshold deviations, compared against total-score and fixed-map baselines on E-DAIC/CMDC/PDCH. |
| C_PDCH_HAMD_INTERNAL | `allowed_limited` | PDCH-only HAMD item/total diagnostic, not cross-dataset HAMD generalization. | External HAMD transfer or stronger CMDC/PDCH-compatible measurement head before cross-dataset HAMD claims. |
| C_EATD_SDS_GENERALIZATION | `blocked` | Report EATD as negative/weak SDS external stress. | A separately audited feature contract with meaningful SDS improvement over train mean and no stronger valence shortcut. |
| C_DATASET_IDENTITY_CONTROL | `allowed_limited` | Known-dataset centering, source-agnostic WavLM projection, BGE identity projection, and BGE total-anchor diagnostics are controls; do not claim invariant representation. | Identity reduction must be paired with total-allocation-beating shared construct performance before it can support a shared-representation claim. |
| C_MODMA_TASK_CONTROL | `allowed_limited` | MODMA task-specific diagnostic protocol-control result. | Integrate with shared-symptom targets and cross-dataset controls before using it as a full method component. |
| C_EATD_VALENCE_ADVERSARIAL | `blocked` | Do not add a valence-adversarial module from current EATD evidence. | Meaningful EATD SDS or depression signal plus demonstrated valence identity/shortcut reduction. |
| C_RQ3_CONTEXT_CONDITIONING | `blocked` | Report MPDD context calibration as negative and keep age/personality as measurement-heterogeneity audit axes. | A later measurement-invariance/DIF moderator analysis must improve subgroup behavior beyond AV-only recalibration and shuffled controls before positive RQ3 conditioning claims. |
| C_RQ4_EVIDENCE_LOCALIZATION | `allowed_limited` | Use first-round aggregate MV06 annotation and dataset-stratified agreement as credibility evidence; raw snippets remain local-only. | For a stronger manuscript claim, expand the E-DAIC double-annotation slice or add Krippendorff alpha/bootstrap uncertainty because E-DAIC currently has few double pairs. |
| C_PUBLISHABLE_PAPER_DIRECTION | `allowed_with_reframing` | A diagnostic/audit-driven paper is viable now; the method path should pivot from direct shared-label mapping to partial measurement invariance. | First address public manifest/governance risk, then freeze shallow BGE/WavLM rows as negative/partial baselines and design the partial-invariance psychometric measurement row. |

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
| P5_MV06_readiness | `complete` | `ready_for_local_evidence_annotation` | `True` | MV06 can proceed as a local-only evidence annotation workflow for datasets with prediction-text overlap. The next step should sample candidates from the local queue, inspect raw snippets locally, and commit only aggre... |
| P5_MV06_pilot | `complete` | `ready_for_manual_local_annotation` | `True` | A bounded MV06 local annotation packet is ready. It should be annotated locally and later summarized only as aggregate evidence agreement, prompt-artifact rate, evidence-source distribution, and construct coverage. |
| P5_MV06_workbench | `complete` | `ready_for_local_human_annotation` | `True` | A two-annotator local MV06 workbook is ready. It contains local text locators and private free-text fields only in ignored local files; tracked outputs are schema and hygiene summaries only. |
| P5_MV06_summary | `complete` | `ready_for_aggregate_evidence_review` | `True` | Aggregate annotation counts and pairwise agreement are ready for human review; raw snippets and subject-level rows remain local-only. |
| P5_MV06_ai_preannotation | `complete` | `ready_for_human_review_not_claimable` | `True` | AI triage filled a local-only preannotation workbook. It can accelerate human review, but it does not satisfy MV06 human annotation or agreement gates. |
| P5_MV06_review_pack | `complete` | `ready_for_human_review_pack_not_claimable` | `True` | A local review pack now combines AI suggestions, human annotation fields, and priority ranks. It can speed manual review but does not satisfy MV06 annotation, agreement, or RQ4 evidence gates. |
| P5_MV07_edaic_bge_generation | `complete_local_feature_cache_generated` | `complete_local_feature_cache_generated` | `True` | complete_local_feature_cache_generated |
| P5_MV07_readiness | `complete` | `ready_to_run_minimal_validation` | `True` | The aligned BGE text contract is ready: E-DAIC, CMDC, and PDCH now share 512 BGE model-input columns. This authorizes the next MV07 shallow validation row, not a shared-symptom claim yet. |
| P5_MV07 | `complete` | `blocked_not_better_than_total_allocation_bge_contract` | `True` | Aligned BGE MV07 is a shallow validation result. Interpret it through pooled PHQ gains, PDCH HAMD-proxy sanity, and identity probes; readiness alone is not a shared-symptom claim. |
| P5_MV07b | `complete` | `partial_identity_reduced_not_total_floor_beating_bge_projection` | `True` | MV07b tests an inference-compatible BGE identity projection for the pooled E-DAIC/CMDC PHQ C01-C08 contract. A positive claim requires preserved construct MAE, gains over simple floors, and reduced feature/prediction ... |
| P5_MV07c | `complete` | `blocked_not_better_than_raw_total_allocation_bge_total_anchor` | `True` | MV07c tests whether identity-projected BGE itemwise heads add construct value after a train-fold-selected total anchor. It is a shallow validation row, not the full method. |

## Next Actions

| rank | action | success gate |
| ---: | --- | --- |
| 1 | Audit and reduce public row-level manifest exposure before further GitHub publishing. | Public repo keeps manifest schemas, synthetic examples, generation scripts, and local-only ignore rules; real row-level manifests remain server-local. Any remote history rewrite requires explicit user approval. |
| 2 | Freeze shallow BGE/WavLM rows as negative or partial baselines, then design the multi-scale psychometric partial-invariance measurement row. | A new row compares total-score, fixed construct-map, and shared latent constructs plus scale-specific DIF/loading-threshold deviations on E-DAIC, CMDC, and PDCH. |
| 3 | Use the dataset-stratified MV06 agreement summary as first-round RQ4 evidence, then optionally expand the E-DAIC double-annotation slice. | Dataset-stratified agreement remains aggregate-only, and any added E-DAIC review improves per-dataset agreement stability without exporting snippets or source locators. |
| 4 | Recover or create speaker/protocol labels for E-DAIC participant/interviewer controls if feasible. | Speaker-resolved subject-level controls with no leakage and aggregate-only outputs. |
| 5 | Try to recover structured MPDD gender/health metadata and official test labels as a governance update. | Registry/manifest update plus audit showing coverage and no split leakage. |

## Interpretation Boundary

This audit is deliberately conservative. A row marked `allowed_limited` can appear in the paper as bounded diagnostic evidence, but it does not authorize a broad method claim. Full-model work should start only after the blocked gates are addressed or the paper is explicitly reframed around diagnostics, negative results, and a bounded method proposal.
