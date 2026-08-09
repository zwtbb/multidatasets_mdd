# Phase 5 Full-Method Gate Audit

Generated: `2026-08-09T07:45:33+00:00`

## Decision

- Full method allowed: `False`.
- Gate status: `blocked_but_publishable_diagnostic_direction`.
- Blocked claim count: `6`.
- Allowed limited/reframed claim count: `4`.

The current evidence supports a careful diagnostic paper direction, but not a broad full symptom-aligned method claim yet.

## Claim Gate

| claim | decision | allowed scope | required next evidence |
| --- | --- | --- | --- |
| C_FULL_METHOD_START | `blocked` | No full method construction yet. | A revised shared-symptom feature contract that beats simple floors while preserving identity/protocol controls, or completed MV06 evidence annotation with aggregate agreement. |
| C_RQ1_SHARED_SYMPTOM | `blocked` | Discuss as the target hypothesis and report negative/partial diagnostics. | Cross-dataset or few-shot construct evidence that beats train-mean/total-allocation floors without worsening dataset identity. |
| C_PDCH_HAMD_INTERNAL | `allowed_limited` | PDCH-only HAMD item/total diagnostic, not cross-dataset HAMD generalization. | External HAMD transfer or stronger CMDC/PDCH-compatible measurement head before cross-dataset HAMD claims. |
| C_EATD_SDS_GENERALIZATION | `blocked` | Report EATD as negative/weak SDS external stress. | A separately audited feature contract with meaningful SDS improvement over train mean and no stronger valence shortcut. |
| C_DATASET_IDENTITY_CONTROL | `allowed_limited` | Known-dataset centering and source-agnostic projection are diagnostic controls; do not claim invariant representation. | Feature-level identity reduction in an inference-compatible setting while preserving shared construct performance. |
| C_MODMA_TASK_CONTROL | `allowed_limited` | MODMA task-specific diagnostic protocol-control result. | Integrate with shared-symptom targets and cross-dataset controls before using it as a full method component. |
| C_EATD_VALENCE_ADVERSARIAL | `blocked` | Do not add a valence-adversarial module from current EATD evidence. | Meaningful EATD SDS or depression signal plus demonstrated valence identity/shortcut reduction. |
| C_RQ3_CONTEXT_CONDITIONING | `blocked` | Report MPDD context calibration as negative and keep age/personality as audit axes. | A revised context module that improves required subgroup ECE gaps beyond AV-only recalibration and shuffled controls. |
| C_RQ4_EVIDENCE_LOCALIZATION | `blocked_pending_annotation` | Use current MV06 artifacts as annotation infrastructure only. | Completed local annotations, enough double-annotated rows for agreement, prompt-artifact rates, and aggregate-only hygiene pass. |
| C_PUBLISHABLE_PAPER_DIRECTION | `allowed_with_reframing` | A diagnosis/audit-driven paper with rigorous negative/mixed results and a bounded method proposal is viable; not a SOTA full-method paper yet. | Either complete MV06 evidence annotations for credibility/RQ4 or run a stronger shared-symptom feature contract before method expansion. |

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
| P5_MV06_summary | `complete` | `blocked_no_completed_annotations` | `True` | The local packet has not been annotated yet; only completion and field-contract gates are meaningful. |

## Next Actions

| rank | action | success gate |
| ---: | --- | --- |
| 1 | Complete local MV06 evidence annotations and rerun the aggregate summary gate. | Nonzero completed annotations, enough double annotations for agreement, no invalid field values, artifact_hygiene_passed=true. |
| 2 | Design and run a revised shared-symptom feature contract before M0. | Beats train-mean/total-allocation floors and does not worsen dataset/protocol identity controls across at least E-DAIC/CMDC plus one external stress dataset. |
| 3 | Recover or create speaker/protocol labels for E-DAIC participant/interviewer controls if feasible. | Speaker-resolved subject-level controls with no leakage and aggregate-only outputs. |
| 4 | Try to recover structured MPDD gender/health metadata and official test labels as a governance update. | Registry/manifest update plus audit showing coverage and no split leakage. |

## Interpretation Boundary

This audit is deliberately conservative. A row marked `allowed_limited` can appear in the paper as bounded diagnostic evidence, but it does not authorize a broad method claim. Full-model work should start only after the blocked gates are addressed or the paper is explicitly reframed around diagnostics, negative results, and a bounded method proposal.
