# MASTER MEMORY

Last updated: 2026-09-04 UTC

This is the master memory for the cross-scale depression modeling project. Keep
it short, current, and decision-oriented. Detailed history belongs in
session-level memory files under `memory/sessions/`.

## Memory Hierarchy

- Master memory: `/root/autodl-tmp/MEMORY.md`
  - Owns current project status, global decisions, active gates, and next
    orchestration steps.
  - Do not store long per-run logs or full metric tables here.
- Active handoff: `/root/autodl-tmp/memory/ACTIVE_HANDOFF.md`
  - Short working-memory entrypoint for the current main-agent context.
  - Read it after this master memory and before opening detailed session files.
  - Update it when the active gate, next task, versioning boundary, or
    cross-session decision changes.
- Session memories:
  - `/root/autodl-tmp/memory/sessions/session_00_data_governance.md`
  - `/root/autodl-tmp/memory/sessions/session_01_phase1_phase2_baselines.md`
  - `/root/autodl-tmp/memory/sessions/session_02_phase3_protocol_diagnostics.md`
  - `/root/autodl-tmp/memory/sessions/session_03_phase3_task_valence_diagnostics.md`
  - `/root/autodl-tmp/memory/sessions/session_04_phase3_mpdd_individual_differences.md`
  - `/root/autodl-tmp/memory/sessions/session_05_phase3_dataset_identity_probe.md`
  - `/root/autodl-tmp/memory/sessions/session_06_phase4_symptom_ontology.md`
  - `/root/autodl-tmp/memory/sessions/session_07_phase5_minimal_validation_protocol.md`
  - `/root/autodl-tmp/memory/sessions/session_08_phase5_mv01_phq_bridge.md`
  - `/root/autodl-tmp/memory/sessions/session_09_phase5_mv04_dataset_identity_control.md`
  - `/root/autodl-tmp/memory/sessions/session_10_phase5_mv04_source_agnostic_identity_projection.md`
  - `/root/autodl-tmp/memory/sessions/session_11_phase5_mv03_sds_total_external_stress.md`
  - `/root/autodl-tmp/memory/sessions/session_12_phase5_mv05_mpdd_context_calibration.md`
  - `/root/autodl-tmp/memory/sessions/session_13_phase5_mv02_hamd_bridge_readiness.md`
  - `/root/autodl-tmp/memory/sessions/session_14_phase5_mv02_hamd_auxiliary_bridge.md`
  - `/root/autodl-tmp/memory/sessions/session_15_phase5_mv06_evidence_localization_readiness.md`
  - `/root/autodl-tmp/memory/sessions/session_16_phase5_mv06_evidence_annotation_pilot.md`
  - `/root/autodl-tmp/memory/sessions/session_17_phase5_mv06_evidence_annotation_summary_gate.md`
  - `/root/autodl-tmp/memory/sessions/session_18_phase5_mv03b_eatd_text_semantic_stress.md`
  - `/root/autodl-tmp/memory/sessions/session_19_phase5_mv02b_pdch_text_semantic_measurement.md`
  - `/root/autodl-tmp/memory/sessions/session_20_clean_github_publish_workflow.md`
  - `/root/autodl-tmp/memory/sessions/session_21_phase5_mv04c_protocol_task_valence_control.md`
  - `/root/autodl-tmp/memory/sessions/session_22_phase5_full_method_gate_audit.md`
  - `/root/autodl-tmp/memory/sessions/session_23_phase5_mv06_annotation_workbench.md`
  - `/root/autodl-tmp/memory/sessions/session_24_phase5_mv07_shared_feature_contract_readiness.md`
  - `/root/autodl-tmp/memory/sessions/session_25_phase5_mv07_edaic_bge_generation.md`
  - `/root/autodl-tmp/memory/sessions/session_26_phase5_mv07_aligned_bge_shared_symptom.md`
  - `/root/autodl-tmp/memory/sessions/session_27_phase5_mv06_local_ai_preannotation.md`
  - `/root/autodl-tmp/memory/sessions/session_28_phase5_mv07b_bge_identity_projection.md`
  - `/root/autodl-tmp/memory/sessions/session_29_phase5_mv07c_bge_total_anchor.md`
  - `/root/autodl-tmp/memory/sessions/session_30_phase5_mv06_human_review_pack.md`
  - `/root/autodl-tmp/memory/sessions/session_31_phase5_mv06_annotation_and_governance_reframe.md`
  - `/root/autodl-tmp/memory/sessions/session_32_phase5_mv08_partial_invariance_design.md`
  - `/root/autodl-tmp/memory/sessions/session_33_phase5_mv08_partial_invariance_pilot.md`
  - `/root/autodl-tmp/memory/sessions/session_34_phase5_mv08_error_analysis.md`
  - `/root/autodl-tmp/memory/sessions/session_35_phase5_mv08b_total_anchored_residual_design.md`
  - `/root/autodl-tmp/memory/sessions/session_36_phase5_mv08b_total_anchored_residual_run.md`
  - `/root/autodl-tmp/memory/sessions/session_37_diagnostic_paper_claim_tables.md`
  - `/root/autodl-tmp/memory/sessions/session_38_data_governance_label_contracts_draft.md`
  - `/root/autodl-tmp/memory/sessions/session_39_mv09_conditional_identity_gate_revision.md`
  - `/root/autodl-tmp/memory/sessions/session_40_mv10_psychometric_invariance_baseline.md`
  - `/root/autodl-tmp/memory/sessions/session_41_mv11_formal_psychometric_confirmation.md`
  - `/root/autodl-tmp/memory/sessions/session_42_mv12_two_stage_latent_target_design.md`
  - `/root/autodl-tmp/memory/sessions/session_43_mv12_two_stage_latent_target_run.md`
  - `/root/autodl-tmp/memory/sessions/session_44_mv12_tradeoff_analysis.md`
  - `/root/autodl-tmp/memory/sessions/session_45_diagnostic_paper_results_sections.md`
  - `/root/autodl-tmp/memory/sessions/session_46_mv13_external_psychometric_replication.md`
  - `/root/autodl-tmp/memory/sessions/session_47_mv14_measurement_uncertainty_bootstrap_design.md`
  - `/root/autodl-tmp/memory/sessions/session_48_mv06_annotation_import_round2.md`
  - `/root/autodl-tmp/memory/sessions/session_49_mv14_measurement_uncertainty_bootstrap_run.md`
  - `/root/autodl-tmp/memory/sessions/session_50_mv15_latent_conditioned_identity_design.md`
  - `/root/autodl-tmp/memory/sessions/session_51_mv15_latent_conditioned_identity_run.md`
  - `/root/autodl-tmp/memory/sessions/session_52_mv16_dif_guided_calibration_design.md`
  - `/root/autodl-tmp/memory/sessions/session_53_mv14_dif_effective_denominator_correction.md`
  - `/root/autodl-tmp/memory/sessions/session_54_mv16_dif_guided_calibration_run.md`
  - `/root/autodl-tmp/memory/sessions/session_55_mv06_agreement_uncertainty.md`
  - `/root/autodl-tmp/memory/sessions/session_56_diagnostic_manuscript_draft.md`
  - `/root/autodl-tmp/memory/sessions/session_57_diagnostic_bibliography_handoff.md`
  - `/root/autodl-tmp/memory/sessions/session_58_context_token_management.md`
  - `/root/autodl-tmp/memory/sessions/session_59_postreview_measurement_validity_triage.md`
  - `/root/autodl-tmp/memory/sessions/session_60_mv17a_multilingual_feature_contract.md`
  - `/root/autodl-tmp/memory/sessions/session_61_mv18_cmdc_pdch_hamd_same_scale_control.md`
  - `/root/autodl-tmp/memory/sessions/session_62_mv19_phq_finite_sample_simulation.md`
  - `/root/autodl-tmp/memory/sessions/session_63_experiment_consolidation_cleanup.md`
  - `/root/autodl-tmp/memory/sessions/session_64_mv17a_manuscript_claim_calibration.md`
  - `/root/autodl-tmp/memory/sessions/session_65_mv20_criterion_overlap_stress.md`
  - `/root/autodl-tmp/memory/sessions/session_66_mirt_parameterization_correctness_audit.md`
  - `/root/autodl-tmp/memory/sessions/session_67_mirt_corrected_rerun.md`
  - `/root/autodl-tmp/memory/sessions/session_68_daicwoz_benchmark_view.md`
  - `/root/autodl-tmp/memory/sessions/session_69_main_takeover_manuscript_orchestration.md`
  - `/root/autodl-tmp/memory/sessions/session_70_mv21_measurement_discrepancy_gradient.md`
  - `/root/autodl-tmp/memory/sessions/session_71_manuscript_rq_reframe.md`
  - `/root/autodl-tmp/memory/sessions/session_72_reframed_rq_figure_package.md`
  - `/root/autodl-tmp/memory/sessions/session_73_core7_paper_figures.md`
  - `/root/autodl-tmp/memory/sessions/session_74_measurement_aware_framework.md`
  - `/root/autodl-tmp/memory/sessions/session_75_manuscript_positioning_tune.md`
  - `/root/autodl-tmp/memory/sessions/session_76_foundation_backbone_framework_contract.md`
  - `/root/autodl-tmp/memory/sessions/session_77_mv22_foundation_backbone_validation.md`
  - `/root/autodl-tmp/memory/sessions/session_78_mv23_foundation_multimodal_completion.md`
  - `/root/autodl-tmp/memory/sessions/session_79_template_paper_writing_blueprint.md`
  - `/root/autodl-tmp/memory/sessions/session_80_abstract_introduction_rewrite.md`
  - `/root/autodl-tmp/memory/sessions/session_81_related_work_and_citeproc.md`
  - `/root/autodl-tmp/memory/sessions/session_82_framework_methods_rewrite.md`
  - `/root/autodl-tmp/memory/sessions/session_83_results_gate_rewrite.md`
  - `/root/autodl-tmp/memory/sessions/session_84_framework_implications_discussion_polish.md`
  - `/root/autodl-tmp/memory/sessions/session_85_figure_table_integration.md`
  - `/root/autodl-tmp/memory/sessions/session_87_lark_cli_codex_integration.md`
  - `/root/autodl-tmp/memory/sessions/session_88_mv24_measurement_aware_ordinal_model.md`
  - `/root/autodl-tmp/memory/sessions/session_89_mv25_provenance_controlled_identity.md`
  - `/root/autodl-tmp/memory/sessions/session_90_manuscript_structure_claim_alignment.md`
  - `/root/autodl-tmp/memory/sessions/session_91_feishu_precise_sync.md`
  - `/root/autodl-tmp/memory/sessions/session_92_mv26_depression_specific_baselines.md`
  - `/root/autodl-tmp/memory/sessions/session_93_mv26_scd_mllm_baseline.md`
  - `/root/autodl-tmp/memory/sessions/session_94_mv27_four_domain_binary_benchmark.md`
  - `/root/autodl-tmp/memory/sessions/session_95_manuscript_evidence_rank_alignment.md`
  - `/root/autodl-tmp/memory/sessions/session_96_manuscript_rq3_slimming.md`
  - `/root/autodl-tmp/memory/sessions/session_97_manuscript_mmd_core_and_claim_tone.md`
  - `/root/autodl-tmp/memory/sessions/session_98_manuscript_abstract_intro_density.md`
  - `/root/autodl-tmp/memory/sessions/session_99_manuscript_related_methods_weighting.md`
  - `/root/autodl-tmp/memory/sessions/session_100_manuscript_layout_discussion_sync.md`
  - `/root/autodl-tmp/memory/sessions/session_101_bibliography_primary_verification.md`
  - `/root/autodl-tmp/memory/sessions/session_102_mv24_fair_ablation_gate.md`
  - `/root/autodl-tmp/memory/sessions/session_103_mv24_targeted_item_and_dif_simulation.md`
  - `/root/autodl-tmp/memory/sessions/session_104_remote_github_cleanup.md`
  - `/root/autodl-tmp/memory/sessions/session_105_acm_framework_gap_planning.md`
  - `/root/autodl-tmp/memory/sessions/session_106_mv28_mv29_mv30_reviewer_response.md`
  - `/root/autodl-tmp/memory/sessions/session_107_target_validity_audit_revision.md`
  - `/root/autodl-tmp/memory/sessions/session_108_target_comparability_and_leakage_revision.md`
  - `/root/autodl-tmp/memory/sessions/session_master_orchestration.md`
- Template for future sessions:
  - `/root/autodl-tmp/memory/templates/session_memory_template.md`
- Generated artifacts remain the source of truth for numeric tables, manifests,
  and audit reports. Memory files should cite those artifacts rather than copy
  large tables.

When starting a new session, read this master memory first, then read the active
handoff, then read only the session memory files relevant to that task. Each
separate task should maintain its own session memory file and update the master
only with stable cross-session facts, final decisions, blockers, or
handoff-worthy results.

For Codex worktree sessions, write code, docs, session memory, and generated
outputs under the current worktree root. Use the absolute dataset roots recorded
in `datasets/registry.yaml` only for reading raw data; do not write experiment
outputs back into the canonical `/root/autodl-tmp` checkout from a worktree.

## Research Objective

Systematically study label, protocol, and population differences across
depression-detection datasets, then propose a symptom-construct aligned
framework. Predictions should be grounded in transferable symptom evidence, not
dataset protocol shortcuts or population-specific spurious correlations.

The user re-sent the original experiment plan on 2026-08-04 and reaffirmed the
canonical order: data audit -> task/hypothesis freeze -> unified baselines ->
failure-mode diagnostics -> minimal method validation -> full method ->
cross-dataset experiments -> statistics and writing. Treat this order as a
research guardrail; do not start full-model construction before Phase 3
diagnostics and Stop/Go decisions are recorded.

Frozen RQs:

- RQ1: cross-scale shared symptom constructs across PHQ-8, PHQ-9, HAMD-17, and
  SDS.
- RQ2: protocol and task-content dependence versus participant symptom evidence.
- RQ3: individual-difference moderation by age, personality, health status, and
  gait/psychomotor context.
- RQ4: evidence localization for symptom and severity predictions.

Post-review paper framing compresses the original RQs into three contribution
layers: representation/protocol shift, target measurement shift, and prediction
shift. RQ1 label measurement is the core positive evidence. RQ2/Phase 3 is
motivating shortcut evidence. RQ3 is a population/individual-difference stress
test, not a personality-aware modeling contribution. RQ4 is a
measurement-interpretation credibility layer, not a separate evidence-retrieval
method.

## Dataset Roles

| Dataset | Main role | Primary use |
| --- | --- | --- |
| E-DAIC | Primary development dataset | PHQ-8 symptoms, total score, binary label, interviewer prompt bias |
| DAIC-WOZ | AVEC2017 Wizard-of-Oz benchmark/control from the DAIC lineage | Reproduction and same-PHQ-8 lineage controls only; E-DAIC is the extended DAIC dataset, and DAIC-WOZ must not be pooled independently with E-DAIC |
| CMDC | Chinese cross-protocol and cross-language validation | Chinese clinical-interview external generalization |
| PDCH | Real hospital consultation and HAMD validation | HAMD-17 symptom and severity prediction |
| MODMA | Controlled speech-task stress test | Interview, reading, picture, and affective-task robustness |
| EATD-Corpus | Chinese valence stress test | Positive, neutral, and negative audio/text consistency |
| MPDD-AVG-2026 | Individual-difference and psychomotor validation | Age/personality/health context, audio-video, and gait moderation |

MPDD 2025 is intentionally out of scope for current auditing.

## Current Stage

- Phase 0 data governance: complete.
- Phase 1 research questions and hypotheses: frozen.
- Phase 2 unified applicable baseline matrix: complete.
- Current next stage: post-review measurement-validity triage under the Phase 5
  full-method gate. The paper direction is now target measurement validity:
  representation/protocol shift, target measurement shift, and prediction shift
  must be separated. The current MV12/MV15/MV16 BGE-linked feature-level chain
  is legacy/diagnostic because E-DAIC MV07 used a Chinese BGE encoder on
  English transcripts and the available transcript contract lacks speaker
  roles. Label-only MV10/MV11/MV19 are the primary PHQ measurement layer:
  substantial common PHQ structure, hypothesis-generating recurrent C02/C06
  threshold-shift candidates with finite-sample uncertainty, sparse loading
  DIF, uncertain global model selection, and an explicit
  observed-N finite-sample downgrade. The narrow corrected MV13/MV14 `mirt`
  rerun is complete: E-DAIC/CMDC reference/focal order, manual anchor linking,
  graded `d1-d3` threshold/intercept constraints, and focal mean/variance
  freed for threshold-constrained anchor-linked models all pass the code-level
  audit. Treat MV13/MV14 as corrected external `mirt` qualitative/uncertainty
  corroboration with the retained configural convergence warning and MV19
  finite-sample caveat, not as robust standalone DIF proof. Full-method work
  remains blocked until a
  genuinely new data, feature, or measurement mechanism changes the gate. The
  MV17a multilingual feature-contract sensitivity is complete and now owns the
  canonical prediction-consequence wording. BGE-M3 is the primary feature
  contract and multilingual-E5 is the sensitivity encoder; both regenerate
  E-DAIC/CMDC/PDCH subject-level features and rerun MV07/MV12/MV15. The
  stable conclusion is not universal external-theta-transfer failure or
  universal B3 Pareto dominance: both encoders keep MV07/MV12/MV15 blocked,
  both pass same-dataset theta utility, both fail observed-scale validity, and
  both keep theta-conditioned feature identity BA at `1.000`, while external
  theta transfer is encoder-dependent (BGE-M3 passes, multilingual-E5 fails)
  and B3 Pareto dominance is encoder-dependent (false for BGE-M3, true for
  multilingual-E5). MV16 remains paused unless a future
  review specifically requires rerunning it under the multilingual feature
  contract. MV18 CMDC-HAMD vs PDCH-HAMD same-scale exploratory control is also
  complete: under the mild/moderate HAMD overlap it finds 4 predeclared
  severity-conditioned residual item-shift flags, 7 threshold-shift flags, and
  weak primary bidirectional transfer under the current frozen-feature
  contract. Treat MV18 as exploratory same-HAMD context-shift support, not
  formal HAMD invariance. MV19 finite-sample PHQ psychometric simulation is
  complete: under the observed E-DAIC/CMDC PHQ N and severity distributions,
  H0 C02/C06 both-flag false rate is `0.208`, H1 C02/C06 both-flag recovery is
  `0.662`, H1 top-two recovery is `0.222`, and H1 anchor subset recovery is
  `0.178`. Treat C02/C06 as hypothesis-generating repeated but
  finite-sample-bounded dataset-group threshold-shift evidence, not robust
  standalone DIF. MV21
  descriptive measurement-discrepancy contrast audit is complete as user-directed
  manuscript reinforcement: DAIC-WOZ/E-DAIC is a same-lineage PHQ-8 control
  with tiny paired/conditioned item differences, E-DAIC/CMDC supplies PHQ
  shared-item descriptive and item-excluded severity-conditioned contrasts,
  and CMDC/PDCH supplies exploratory same-HAMD item distribution,
  severity-conditioned, and correlation-structure support. MV21 does not add
  HAMD MIM/IRT or formal HAMD invariance. MV24 formal measurement-aware
  ordinal modeling is complete after the user-approved mechanism change. It
  fixes the PHQ shared-item method to frozen Qwen3+WavLM+OpenFace subject
  representations, a trainable projector, a shared eight-dimensional symptom
  layer, and corpus-specific cumulative-logit ordinal heads. Its main table
  now separates supervision budgets. ERM/CORAL/MMD/DANN, the strongest direct
  foundation baseline, and latent-only are zero-target-label rows; the
  target-calibrated block now includes corpus-specific-head, direct target
  fine-tuning, direct source+target multitask, shared ordinal head, generic
  target MLP head, measurement-aware, and measurement-aware + MMD under the
  same target calibration label split. The fair shared-layer calibrated ablation
  gate is `not_passed_uniform_measurement_pathway_superiority`: the large gain
  over frozen corpus-specific-head is mainly evidence for target
  calibration/shared-layer adaptation, while the corpus-specific ordinal
  pathway is competitive and direction-dependent rather than uniformly superior.
  MV24 now also includes a targeted item-level analysis comparing shared
  ordinal and corpus-specific ordinal heads on the measurement-gate anchor
  items `C01/C04/C05/C07` and threshold-shift items `C02/C06`. Real-data
  C02/C06 item-set deltas are near ties (`0.004` for CMDC-to-E-DAIC and
  `0.002` for E-DAIC-to-CMDC, both with intervals crossing zero), so the
  targeted analysis does not support an independent overall or item-local
  performance gain from corpus-specific ordinal parameterization. The companion
  fixed-latent DIF simulation is complete: under scalar invariance,
  corpus-specific heads do not help, and under planted `C02/C06` threshold DIF
  they show only weak item-local mechanism consistency (`0.002` and `0.011`
  C02/C06-set MAE deltas; `301/500` and `311/500` lower-error draws), while
  anchors do not improve. Treat the simulation as mechanism sanity checking,
  not as real-data superiority evidence. MV24 now also reports secondary
  clinical-reader metrics following
  cross-domain MDD reporting practice: total MAE/CCC plus a shared-PHQ total
  >=10 endpoint with Macro-F1, Balanced Accuracy, AUROC, AUPRC, Sensitivity,
  and Specificity. The lambda-MMD sweep is nearly flat, so treat MMD as a mild
  regularizer rather than the core empirical mechanism. Treat MV24 as the
  current formal method result for the PHQ shared-item manuscript story, while
  the old
  M0/M1/M2/M3 full-method gate still blocks overbroad cross-scale claims.
  MV25 provenance and controlled identity diagnostics are also complete:
  DAIC-WOZ/E-DAIC is explicitly documented as a same-lineage PHQ-8 sanity
  control (`141` paired train/dev subjects, all-item exact match `0.993`, mean
  absolute item difference `0.007`), not independent-corpus evidence. MV25
  also shows that the raw E-DAIC/CMDC corpus-identity `1.000` should not carry
  the representation claim alone because fold-internal length/severity controls
  explain much of that cross-language separability; same-language E-DAIC
  lineage probes remain high after controls (`0.839` Qwen3 text, `0.897` WavLM
  audio), supporting acquisition/protocol identity beyond simple language
  detection. MV26 depression-specific baseline stress testing is complete and
  now holds the public close-baseline rows in one canonical folder:
  GNN-SDA-style, QuestMF-style, and SCD-MLLM-style under the same official MV24
  Qwen3+WavLM+OpenFace representation, E-DAIC<->CMDC PHQ shared-item split,
  five seeds, and target calibration label budget. QuestMF-style
  measurement-aware improves reconstruction-plus-calibration in both
  directions (`1.203 -> 1.159`, `1.133 -> 1.096`), and SCD-MLLM-style
  measurement-aware also improves both directions (`1.485 -> 1.238`, `1.100 ->
  1.084`). GNN-SDA-style is direction-sensitive (`1.121 -> 1.066` for
  E-DAIC-to-CMDC but `1.339 -> 1.431` for CMDC-to-E-DAIC). Treat MV26 as
  a close-baseline stress test and not a direct external leaderboard
  reproduction or universal win claim. MV27 four-domain binary benchmarking
  was completed locally after fairness fixes requested by the user: GNN
  target-aware now uses `shared_head + corpus_specific_residual`, and GNN/DIL
  target-aware rows share the same pseudo-label/diversity/teacher adaptation
  recipes and target-label budget as their direct counterparts. The corrected
  DAIC-WOZ+CMDC+MODMA+EATD binary result did not pass the automatic submission
  gate: Table B balanced-accuracy improvements are 18/72 family-direction
  cells, and Table C Full beats the strongest same-budget ablation in 3/12
  directions. Treat MV27 as local negative/diagnostic stress-test evidence
  unless the user explicitly decides to commit or manuscript-include it. See
  `memory/sessions/session_94_mv27_four_domain_binary_benchmark.md` and
  `analysis/phase5_minimal_validation/p5_mv27_four_domain_binary_benchmark/`.
  The active
  evidence bundle is now consolidated at
  `/root/autodl-tmp/analysis/phase5_minimal_validation/experiment_consolidation/`:
  paper core is `MV10/MV11/MV19/MV21` as primary PHQ psychometric/descriptive
  evidence plus `MV13/MV14` as corrected anchor-linked `mirt` corroboration
  (`MV21` also carries the bounded HAMD/DAIC descriptive controls), paper
  support is `MV02/MV04c/MV06/MV09/MV12/MV15/MV16/MV17a/MV18/MV20`, and
  `P5_mirt_parameterization_audit` is a paper guardrail. Early weak or
  superseded MV rows are frozen as historical diagnostics rather than active
  experiments. Tracked aggregate outputs are retained for traceability; only
  interpreter/notebook caches were physically removed in the cleanup. The
  active next orchestration step is manuscript finalization and primary-source
  citation verification. MV20
  criterion-overlap stress is complete and negative/bounded: CMDC Q1-Q12
  question-position units were feasible, PDCH and E-DAIC were excluded for
  missing clean protocol units, and high-overlap deletion is not clearly worse
  than matched random deletion under BGE-M3 primary or multilingual-E5
  sensitivity. After the user-requested MV21 reinforcement, the experiment
  queue is frozen again for manuscript integration and source verification. On
  2026-08-24, the current
  Codex task took over from legacy main thread
  `019fcd77-cf81-7c11-a53e-f37e776d9e1d` as the active main-agent
  orchestration entrypoint for experiment reinforcement triage and manuscript
  writing. A new human-facing RQ-reframed manuscript draft has been created
  from the user's uploaded `论文撰写.docx` at
  `/root/autodl-tmp/analysis/diagnostic_measurement_audit_paper/manuscript_reframed_rq_draft.md`
  and
  `/root/autodl-tmp/analysis/diagnostic_measurement_audit_paper/论文撰写_修订版.docx`.
  It elevates RQ1 representation heterogeneity, reorganizes RQ2 around the
  DAIC-WOZ/E-DAIC, E-DAIC/CMDC, and CMDC/PDCH measurement-discrepancy
  contrasts, and treats RQ3 negative model-generalization results as a
  contribution without changing the full-method gate.
  A legacy reframed-RQ figure recommendation package has been generated at
  `/root/autodl-tmp/analysis/diagnostic_measurement_audit_paper/figures_reframed_rq/`.
  Prefer the newer core7 package for current manuscript layout. Regenerate the
  legacy package with
  `python /root/autodl-tmp/scripts/build_paper_reframed_rq_figures.py`.
  A newer user-requested seven-core-figure package is now available at
  `/root/autodl-tmp/analysis/diagnostic_measurement_audit_paper/figures_core7/`
  and should be treated as the default manuscript figure package. It includes:
  framework overview, dataset relationship map, raw-to-controlled
  representation identity probe, raw identity heatmap as Supplementary Figure
  S2, PHQ shared-item measurement analysis, DAIC-WOZ/E-DAIC controlled
  comparison, latent target tradeoff, and evidence summary. Regenerate with
  `python /root/autodl-tmp/scripts/build_paper_core7_figures.py`.
  A lightweight measurement-aware cross-corpus depression detection framework
  has been added to the RQ-reframed manuscript as a constructive
  audit-to-model scaffold. It separates shared symptom evidence from
  corpus-specific measurement heads and requires target-contract,
  measurement-comparability, observed-scale validity, calibration, and transfer
  gates before strong pooling/generalization claims. Treat it as a proposed
  framework grounded in psychometrics and ML shift/calibration literature, not
  as permission to start full M0/M1/M2/M3 construction or new experiments.
  This 2026-08-xx method-forward positioning has been superseded by the
  2026-09-04 session-108 revision: the current title is `Audit Target
  Comparability Before Aligning Representations: A Cross-Corpus Measurement
  Audit of Depression Detection`, and measurement-aware ordinal modeling is now
  a constructive instantiation rather than the paper identity.
  In response to the foundation-model validation critique, the manuscript and
  framework note now position the solution as foundation-backbone compatible:
  strong text/audio/video/multimodal encoders feed a shared depression
  representation, a latent symptom layer, corpus-specific measurement heads,
  and measurement-validity gates. MV22 has executed the first
  foundation-backbone text validation slice at
  `/root/autodl-tmp/analysis/phase5_minimal_validation/p5_mv22_foundation_backbone_validation/`;
  it uses frozen Qwen3-Embedding-0.6B text features, a WavLM base-plus audio
  proxy, MV07/MV12/MV15 Qwen reruns, and ERM/CORAL/MMD/DANN/IRM/GroupDRO-style
  aggregate baselines. Qwen keeps feature identity BA at `1.000`, prediction
  identity BA at `0.978`, MV12 blocked on observed-scale validity, and MV15
  theta-conditioned feature identity BA at `1.000`; Qwen measurement-aware
  MV12 references improve shared-item macro MAE over direct itemwise references
  in both PHQ transfer directions. MV23 has also executed the practical
  lightweight foundation-multimodal completion slice at
  `/root/autodl-tmp/analysis/phase5_minimal_validation/p5_mv23_foundation_multimodal_completion/`;
  it uses WavLM/wav2vec2 audio proxies, OpenFace video proxy,
  Qwen3/BGE-M3/multilingual-E5 text-audio-video fusion views, the same
  adaptation baseline family, and a measurement-aware latent-total proxy head
  over E-DAIC/CMDC PHQ shared-item transfer. The supporting contract is
  `/root/autodl-tmp/analysis/diagnostic_measurement_audit_paper/foundation_backbone_measurement_aware_validation_contract.md`.
  MV24 now replaces the proxy method row with a formal measurement-aware
  ordinal main table at
  `/root/autodl-tmp/analysis/phase5_minimal_validation/p5_mv24_measurement_aware_ordinal_model/`.
  It uses the official Qwen3+WavLM+OpenFace representation, shared PHQ symptom
  layer, and corpus-specific ordinal heads; its 2026-09-01/02 fair-ablation
  rerun adds direct target fine-tuning, direct source+target multitask, shared
  ordinal head, and generic target MLP head under the same calibrated target
  split and trainable shared-layer exposure. The fair gate does not pass:
  measurement-aware is best or near-best in CMDC-to-E-DAIC, but direct
  source+target multitask is best in E-DAIC-to-CMDC. Do not write it as a direct
  full-vs-all zero-shot/unsupervised baseline win, and do not claim that Table 3
  proves target-side measurement modeling as the unique source of the gain.
  On 2026-09-03 the user confirmed three manuscript decisions for the next
  revision: use ACM-style submission requirements as the working format target,
  keep the paper positioned as a higher-value measurement-aware framework /
  benchmark-validity study rather than an architecture-SOTA paper, and exclude
  MV27's four-domain binary negative result from the main paper unless later
  explicitly revived as supplement-only diagnostic evidence.
  MV25 adds the cleaned DAIC/E-DAIC provenance and controlled corpus-identity
  diagnostics at
  `/root/autodl-tmp/analysis/phase5_minimal_validation/p5_mv25_provenance_controlled_identity/`.
  WavLM Large/HuBERT Large/VideoMAE/end-to-end multimodal fine-tuning remain
  future scope under a new compute contract. Bibliography metadata has been
  corrected for P3HF, Multi-Probe Audit, EMNLP interviewer bias, the Zhou et al.
  2026 scale-linking author list, the foundation/backbone/baseline citations,
  and DIL-MDD, but all references still require full primary-source
  verification before submission. The manuscript's Framework, Methods, Results,
  Discussion, Scope, and Conclusion sections have now been rewritten within the
  measurement-aware benchmark-validity frame.
  Figure/table integration now covers five main figures, Table 1 dataset-role
  summary, Table 2 validity-gate summary, and, after session 107, a two-panel
  repeated-split target-calibrated Table 3 where target-only direct calibration
  is the main reconstruction comparator. Binary endpoint metrics are now
  Supplementary Table S3; the latent-target transfer and evidence-localization
  figures are generated as supplementary/backup figures rather than main-text
  anchors. A
  2026-08-29 structure/claim-alignment pass compressed
  the former Section 7 into Discussion, made the MV25 raw-to-controlled identity
  probe the main Figure 3, kept the raw identity heatmap as Supplementary Figure
  S2, defined Calibration MAE mathematically, and made MMD an auxiliary
  regularizer rather than the core method claim. A 2026-08-30 evidence-rank
  alignment pass further changed the RQ1 conclusion to: raw corpus identity is
  strong, but residual identity after length and severity controls is
  contrast-dependent. It also compressed DAIC-WOZ/E-DAIC to a provenance sanity
  control, downgraded CMDC/PDCH HAMD to a bounded exploratory same-scale check,
  and made Macro Item MAE plus Calibration MAE the then-current co-primary MV24
  metrics; session 107 supersedes this by making Macro Item MAE the main
  reconstruction metric, CITL/slope the main calibration audit, and binned
  calibration MAE a secondary curve summary. The
  reconstruction-plus-calibration sum is now only a compact summary. A
  2026-08-30 RQ3 slimming pass then reordered Section 6.3 around the formal
  measurement-aware ordinal model and Table 3 first, made zero-target-label
  baselines explicit context rather than same-budget efficacy claims, moved
  foundation/multimodal/depression-specific/binary/MMD/few-shot/protocol-overlap
  checks into supporting or supplementary prose, and removed internal MV labels
  from the main manuscript body and Feishu doc. A 2026-08-30 MMD/core-method
  tone pass then made `Measurement-aware` the core no-MMD ordinal pathway,
  demoted `Measurement-aware + MMD` to an auxiliary variant, and replaced broad
  clinical-safety wording with validity/comparability language. A 2026-08-30
  Abstract/Introduction density pass compressed the Abstract to target
  comparability, evidence, method, and main-result layers; changed Contribution
  2 to a structured three-target-contract audit; and changed RQ3 to ask which
  validity conditions remain unresolved. A 2026-08-30 Related Work/Methods
  weighting pass then compressed the foundation/domain-adaptation survey,
  strengthened Section 2.4 as the measurement-invariance/DIF novelty source,
  removed unnecessary missing-backbone wording from Methods, expanded the
  psychometric decision rules and target-calibration protocol, and aligned the
  MV24 script wording around a core measurement-aware pathway plus an auxiliary
  MMD variant. A 2026-08-31 layout/discussion sync pass then redesigned Figure
  1 around the target contract, simplified Figure 2 to formal contrasts versus
  stress views, retitled Figure 3 as control-dependent corpus identity,
  enlarged Figure 4, weakened Figure 5's HAMD panel as exploratory support,
  split Table 3 into two narrow transfer panels, moved the binary endpoint
  table to the supplement, rewrote Discussion around conceptual/modeling/
  benchmark implications, and shortened Scope and Conclusion. Feishu was
  verified at revision 211 after targeted updates, with no matched old
  high-risk phrases and no hard `<br/>` artifacts. The core7 programmatic
  figure script has been polished and regenerated, and a hand-drawn total-figure
  guide has been written.
  `lark-cli` is installed and authenticated in this Codex shell; a minimal
  Feishu document create/fetch smoke test passed at
  `https://tcn9unqodkum.feishu.cn/docx/IsKDdFHAWoYGJxx1cBAcMkwvnqg`. The
  user-provided Feishu wiki page
  `https://tcn9unqodkum.feishu.cn/wiki/FeR4wSHOdiydQJkiQsBcqShcn0d` has been
  precisely synced through 2026-08-31 to latest verified revision 211 using
  targeted block-level `docs +update` operations, not whole-document overwrite.
  The Feishu document now matches the current manuscript: compressed Abstract,
  three Introduction contributions with the structured target-contract audit
  wording, Section 3.2 as the single formal architecture/loss definition, MMD
  as an auxiliary regularizer, MV25 raw-to-controlled identity as main Figure
  3, weighted Related Work with measurement invariance/DIF as the novelty
  endpoint, expanded Methods rules for measurement screening and target
  calibration, supervision-aware two-panel MV24 Table 3, the MV26
  GNN-SDA/QuestMF/SCD-MLLM close-baseline stress-test paragraph and six-row
  Supplementary Table S2, Supplementary Table S3 for secondary clinical
  endpoint metrics, and Sections 7-9 as Discussion, Scope, and Conclusion.
  Verification found zero hard `<br/>` line-break artifacts and preserved the
  existing comment reference in the full document during the latest layout sync;
  future Feishu manuscript edits should remain targeted block-level updates
  after `docs +fetch` to preserve modification traceability. The 2026-09-02
  MV24 fair-ablation manuscript revision has not yet been synced to Feishu.
- Phase 3 dataset/protocol identity probe: complete. Seven grouped-CV probes
  finished with zero skipped probes, zero train/test group-overlap violations,
  and `artifact_hygiene_passed=true`. Dataset identity is nearly perfectly
  recoverable from multiple frozen/lightweight feature spaces, so direct pooled
  training is not sufficient evidence of a shared depression representation.
- Phase 3 E-DAIC/CMDC protocol controls: complete for available text controls.
  Sixty runs completed over 5 seeds with zero subject-overlap violations and
  `artifact_hygiene_passed=true`. E-DAIC speaker-resolved participant-only and
  interviewer-only controls remain blocked by missing speaker labels, but
  front-position and repeated-turn proxy controls show shortcut risk. CMDC
  question-position probes show large per-question performance variation.
- Phase 3 MODMA/EATD task-valence diagnostics: complete. The run used frozen
  eGeMAPS features, fixed simple heads, five seeds, 200 subject-level bootstrap
  resamples, zero subject-overlap violations, no test split use, and
  `artifact_hygiene_passed=true`. MODMA shows moderate cross-task degradation,
  strongest for affective-task evaluation. EATD audio eGeMAPS does not support
  the specific concern that negative material makes healthy subjects look more
  depressed.
- Phase 3 MPDD individual-difference diagnostics: complete. The run used 175
  labeled train subjects, five-seed subject-level OOF, no test labels, and
  `artifact_hygiene_passed=true`. Personality-only diagnostics beat shuffled
  personality, generic AVP personality concatenation adds near-zero value over
  AV, subgroup calibration gaps are large enough to track, gait has modest
  psychomotor-context signal, and gender/health diagnostics are blocked by
  empty structured manifest fields.
- Phase 3 Stop/Go synthesis: complete at
  `/root/autodl-tmp/analysis/phase3_diagnostics/phase3_stop_go_synthesis.md`.
- Phase 4 symptom ontology and label contract: complete enough for method
  planning. The project now has 15 construct definitions, 54 short item-code
  mappings, a dataset label-contract audit, and a six-row minimal validation
  matrix at `/root/autodl-tmp/analysis/phase4_symptom_ontology/`.
- Phase 5 minimal method-validation protocol: complete as a planning contract
  at `/root/autodl-tmp/analysis/phase5_minimal_validation/`. It has eight
  protocol rows, seven metric/diagnostic rows, output policy, readiness audit,
  and `full_method_allowed=false`. Recommended first runnable row is `P5_MV01`
  `phq_core_construct_bridge`.
- Phase 5 `P5_MV01 phq_core_construct_bridge`: first runnable minimal
  validation complete at
  `/root/autodl-tmp/analysis/phase5_minimal_validation/p5_mv01_phq_core_bridge/`.
  It used frozen WavLM subject features, E-DAIC PHQ-8/CMDC PHQ-9 C01-C08
  labels, shallow heads only, five seeds, no E-DAIC official test labels, zero
  subject-overlap violations, and `artifact_hygiene_passed=true`. The result is
  asymmetric and not enough for a shared-representation claim because frozen
  WavLM E-DAIC-vs-CMDC dataset identity balanced accuracy is `1.000`.
- Phase 5 `P5_MV04 dataset_protocol_control_ablation`: first runnable
  identity-control validation complete at
  `/root/autodl-tmp/analysis/phase5_minimal_validation/p5_mv04_dataset_identity_control/`.
  It used frozen WavLM subject features, E-DAIC/CMDC PHQ C01-C08 labels,
  shallow heads only, five seeds, no eval target labels for the control, zero
  subject-overlap violations, and `artifact_hygiene_passed=true`. Train-fold
  dataset centering reduced feature-layer E-DAIC-vs-CMDC identity balanced
  accuracy from `1.000` to `0.500` and prediction-layer identity from `0.961`
  to `0.476`, while preserving dataset-stratified Macro Construct MAE within
  the 5 percent relative tolerance. Interpret this as a successful diagnostic
  identity control, not an unknown-source inference contract, because known eval
  dataset labels are used for centering.
- Phase 5 `P5_MV04b source_agnostic_identity_projection`: inference-compatible
  follow-up complete at
  `/root/autodl-tmp/analysis/phase5_minimal_validation/p5_mv04_source_agnostic_identity_projection/`.
  It used train-fold dataset labels to learn nuisance projection directions,
  but no eval target labels and no eval dataset labels. The best tested variant
  (`k=10`) reduced prediction-layer identity balanced accuracy from `0.961` to
  `0.777` while preserving dataset-stratified Macro Construct MAE within the 5
  percent relative tolerance, but feature-layer identity remained high
  (`1.000` to `0.925`). Treat as a partial diagnostic control; full-method
  claims remain blocked.
- Phase 5 `P5_MV04c protocol_task_valence_control`: MODMA/EATD protocol-slice
  extension complete at
  `/root/autodl-tmp/analysis/phase5_minimal_validation/p5_mv04c_protocol_task_valence_control/`.
  It used Phase 3 local eGeMAPS feature caches, five seeds, subject-level MODMA
  folds, EATD official train/validation subjects, no raw audio scan, no encoder
  fine-tuning, no eval target labels, no eval protocol labels at transform
  time, zero subject-overlap violations, and `artifact_hygiene_passed=true`.
  Treat as `mixed_protocol_control`: MODMA task nuisance projection passes
  diagnostically, reducing feature task-identity BA `0.762 -> 0.570` while
  preserving pooled Balanced Accuracy `0.688 -> 0.686`; EATD valence control is
  blocked because raw SDS MAE stays below the train-mean floor (`28.810` vs
  `7.201`) and valence identity is not reduced.
- Phase 5 `P5_MV03 sds_total_external_stress`: EATD SDS total external stress
  complete at
  `/root/autodl-tmp/analysis/phase5_minimal_validation/p5_mv03_sds_total_external_stress/`.
  It used existing cached frozen WavLM/eGeMAPS audio features, EATD SDS total
  labels only, official train/validation subject split, five seeds, no raw
  audio scan, zero subject-overlap violations, and `artifact_hygiene_passed=true`.
  Best all-valence validation MAE was `7.341` from eGeMAPS SVR, worse than the
  train-mean floor `7.201`; no stronger healthy-negative shortcut than Phase 3
  was observed. Treat as a runnable negative result:
  `blocked_no_sds_generalization`.
- Phase 5 `P5_MV03b eatd_text_semantic_stress`: EATD SDS total text-semantic
  variant complete at
  `/root/autodl-tmp/analysis/phase5_minimal_validation/p5_mv03b_eatd_text_semantic_stress/`.
  It used manifest-governed EATD text, in-memory character TF-IDF Ridge heads,
  official train/validation subjects, five seeds, no encoder fine-tuning, no
  saved vectorizers/features, zero subject-overlap violations, and
  `artifact_hygiene_passed=true`. Best all-valence MAE was `7.20034` versus
  train mean `7.20089`, a `-0.00056` MAE gain below the meaningful-improvement
  threshold. Treat as `blocked_no_meaningful_text_sds_generalization`.
- Phase 5 `P5_MV05 mpdd_context_calibration`: MPDD context-calibration minimal
  validation complete at
  `/root/autodl-tmp/analysis/phase5_minimal_validation/p5_mv05_mpdd_context_calibration/`.
  It used 175 labeled MPDD train subjects, cached Phase 2 WavLM audio and
  ResNet video subject features, AV-probability-first calibration heads, age and
  personality-bin context controls, gait diagnostics as context-only validation,
  five-seed subject-level OOF, no MPDD test labels, zero subject-overlap
  violations, and `artifact_hygiene_passed=true`. Treat as a runnable negative
  result: `blocked_no_context_calibration_gain`.
- Phase 5 `P5_MV02 hamd17_auxiliary_bridge` readiness audit is complete at
  `/root/autodl-tmp/analysis/phase5_minimal_validation/p5_mv02_hamd_bridge_readiness/`.
  It did not train a model. It corrected the CMDC HAMD coverage interpretation
  by filtering placeholder NaN item payloads, confirmed PDCH has the only
  adequately sized HAMD-17 item+total supervision, and changed `P5_MV02` from
  blocked to `ready_pdch_only_mode`. Full-method work remains blocked.
- Phase 5 `P5_MV02 hamd17_auxiliary_bridge` PDCH-only minimal validation is
  complete at
  `/root/autodl-tmp/analysis/phase5_minimal_validation/p5_mv02_hamd_auxiliary_bridge/`.
  It used 99 PDCH HAMD-labeled subjects, cached frozen BGE/WavLM/eGeMAPS
  subject features, five seeds, 5-fold subject-level stratified CV, no raw
  clinical text or media scan, no encoder fine-tuning, zero subject-overlap
  violations, and `artifact_hygiene_passed=true`. Treat it as
  `pass_pdch_only_diagnostic`, not a cross-dataset HAMD bridge claim.
- Phase 5 `P5_MV02b pdch_text_semantic_measurement`: PDCH manifest-text HAMD
  measurement audit is complete at
  `/root/autodl-tmp/analysis/phase5_minimal_validation/p5_mv02b_pdch_text_semantic_measurement/`.
  It used 99 PDCH HAMD-labeled subjects, 165 manifest text segments, fixed
  character hashing Ridge heads, five seeds, 5-fold subject-level stratified
  CV, no encoder fine-tuning, no saved vectorizers/features, zero
  subject-overlap violations, and `artifact_hygiene_passed=true`. Treat as
  `blocked_weak_pdch_text_measurement_signal`: item-derived total MAE improved
  only `0.008` over train-mean items, below the `0.10` meaningful threshold,
  and macro item MAE was effectively unchanged.
- Phase 5 `P5_MV06 construct_evidence_localization` readiness is complete at
  `/root/autodl-tmp/analysis/phase5_minimal_validation/p5_mv06_evidence_localization_readiness/`.
  It did not read raw clinical text and did not export snippets or source paths.
  It linked local MV01/MV02 predictions to aggregate manifest text availability
  and wrote a local-only candidate queue. Treat MV06 as
  `ready_for_local_evidence_annotation`; tracked outputs may include only
  aggregate evidence summaries unless separately deidentified and approved.
- Phase 5 `P5_MV06 evidence_annotation_pilot` is complete at
  `/root/autodl-tmp/analysis/phase5_minimal_validation/p5_mv06_evidence_annotation_pilot/`.
  It sampled a bounded local annotation packet from the ignored MV06 candidate
  queue: 144 candidate rows, 60 dataset-qualified subjects, 144/144 rows with
  existing local text, and 12 explicit-evidence-only C09/HAMD03 rows. It did
  not read or write raw clinical text. Subject-level packet and local source
  locator map remain ignored local-only files; tracked artifacts contain only
  aggregate sampling, annotation-field policy, and hygiene results. Treat as
  `ready_for_manual_local_annotation`, not evidence-localization results.
- Phase 5 `P5_MV06 evidence_annotation_workbench` is complete at
  `/root/autodl-tmp/analysis/phase5_minimal_validation/p5_mv06_evidence_annotation_workbench/`.
  It prepares a two-annotator ignored local workbook with 288 rows and an
  ignored 144-row local review index with text locators. Tracked artifacts
  contain only schema, annotation rules, manifest, report, run summary, and
  hygiene audit. No raw clinical text is read or written; local locators remain
  ignored local-only. Treat as `ready_for_local_human_annotation`, not evidence
  results.
- Phase 5 `P5_MV06 evidence_annotation_summary_gate` is complete at
  `/root/autodl-tmp/analysis/phase5_minimal_validation/p5_mv06_evidence_annotation_summary/`.
  It now defaults to the ignored local annotation workbench and exports only
  aggregate completion, field-issue, evidence-field, prompt-artifact,
  dataset-stratified agreement, and bootstrap agreement-uncertainty summaries.
  Current status is
  `ready_for_aggregate_evidence_review`: 143 completed candidates and 143
  double-annotated candidates over the 144-candidate local workbench. One CMDC
  sampled candidate remains incomplete because the imported workbook attachment
  omitted its two annotator rows. Evidence-presence kappa is `0.965` overall,
  `0.967` for CMDC, `0.846` for E-DAIC, and `1.000` for PDCH; bootstrap 95
  percent kappa CIs are `0.922-1.000` overall, `0.885-1.000` for CMDC,
  `0.595-1.000` for E-DAIC, and `1.000-1.000` for PDCH. Artifact hygiene
  passes; no raw text, source locator map, or subject-level rows are exported.
- Phase 5 `P5_MV06 local_ai_preannotation_triage` is complete at
  `/root/autodl-tmp/analysis/phase5_minimal_validation/p5_mv06_ai_preannotation_triage/`.
  It read raw clinical text locally through ignored workbench locators and
  generated an ignored local AI-triage preannotation workbook for 144
  candidates. Tracked outputs contain only aggregate counts and hygiene. Treat
  as `ready_for_human_review_not_claimable`: it can accelerate human review but
  does not satisfy MV06 human annotation, agreement, or RQ4 evidence gates.
- Phase 5 `P5_MV06 human_review_pack` is complete at
  `/root/autodl-tmp/analysis/phase5_minimal_validation/p5_mv06_human_review_pack/`.
  It joins the ignored human workbench and ignored AI preannotation into an
  ignored local review pack and candidate index with priority ranks. Tracked
  outputs contain only aggregate review-pack, priority, progress, schema, and
  hygiene summaries. Treat as `ready_for_human_review_pack_not_claimable`: 144
  candidates, 288 annotation rows, 79 AI keyword-match candidates, 82
  priority-1/2 candidates. The later MV06 summary gate supersedes the initial
  progress count with 143 completed and 143 double-annotated candidates.
- Phase 5 `P5_MV07 shared_feature_contract_readiness` is complete at
  `/root/autodl-tmp/analysis/phase5_minimal_validation/p5_mv07_shared_feature_contract_readiness/`.
  It did not train a model and did not scan raw text/audio/video/gait files. It
  inventories cached subject-level feature families and label coverage for a
  revised shared-symptom row. After local E-DAIC BGE generation, current status
  is `ready_to_run_minimal_validation`: E-DAIC, CMDC, and PDCH share 512 BGE
  model-input columns. This authorizes the next shallow MV07 validation row,
  not a shared-symptom claim. Aligned eGeMAPS remains blocked by schema
  mismatch, and WavLM remains identity-blocked diagnostic evidence.
- Phase 5 `P5_MV07 E-DAIC BGE feature generation` is complete at
  `/root/autodl-tmp/analysis/phase5_minimal_validation/p5_mv07_edaic_bge_generation/`.
  It generated the ignored local cache
  `/root/autodl-tmp/analysis/phase2_baselines/edaic_text_bge/edaic_bge_subject_features.csv`
  for 219 E-DAIC train/dev item-labeled subjects, 163 train and 56 dev, with
  512 `bge_*` columns and zero subject-overlap or path-like-column violations.
  Tracked outputs contain only aggregate coverage, local artifact manifest,
  run summary, report, and hygiene audit.
- Phase 5 `P5_MV07 aligned_bge_shared_symptom_validation` is complete at
  `/root/autodl-tmp/analysis/phase5_minimal_validation/p5_mv07_aligned_bge_shared_symptom/`.
  It used aligned E-DAIC/CMDC/PDCH frozen BGE subject features, shallow
  train-mean/total-allocation/itemwise Ridge heads, subject-level splits, and
  identity probes. Treat as a blocked/negative shared-symptom validation:
  `blocked_not_better_than_total_allocation_bge_contract`. Pooled PHQ BGE
  itemwise heads improve over train mean but do not consistently beat
  total-allocation floors, PDCH HAMD-proxy sanity is internal only, and
  identity remains high (feature BA `1.000`, prediction BA `0.980`). Artifact
  hygiene passed and row-level predictions remain ignored local-only.
- Phase 5 `P5_MV07b bge_identity_projection` is complete at
  `/root/autodl-tmp/analysis/phase5_minimal_validation/p5_mv07b_bge_identity_projection/`.
  It used frozen aligned BGE subject features, train-fold E-DAIC/CMDC
  dataset-label nuisance projection, shallow itemwise Ridge heads, subject-level
  splits, and identity probes. Treat as partial diagnostic evidence:
  `partial_identity_reduced_not_total_floor_beating_bge_projection`. Best k=10
  projection reduced E-DAIC/CMDC feature identity BA `1.000 -> 0.709`,
  prediction identity BA `0.994 -> 0.684`, and three-way E-DAIC/CMDC/PDCH
  feature identity BA `1.000 -> 0.687`, while preserving Macro MAE within 5
  percent and beating train mean on both E-DAIC and CMDC. It still failed the
  CMDC total-allocation floor (`+0.018` Macro MAE), so shared-representation
  and full-method claims remain blocked.
- Phase 5 `P5_MV07c bge_total_anchor` is complete at
  `/root/autodl-tmp/analysis/phase5_minimal_validation/p5_mv07c_bge_total_anchor/`.
  It tested whether identity-projected BGE itemwise heads add construct value
  after a train-fold-selected total anchor. Treat as a blocked/negative
  follow-up: `blocked_not_better_than_raw_total_allocation_bge_total_anchor`.
  Prediction identity BA was reduced to `0.664`, and selected models beat train
  mean on E-DAIC/CMDC, but CMDC remained worse than raw total allocation by
  `+0.012` Macro MAE and worse than projected total allocation by `+0.002`.
  Do not keep iterating small shallow BGE-head variants unless the feature or
  measurement contract changes.
- Phase 5 full-method gate audit is complete at
  `/root/autodl-tmp/analysis/phase5_minimal_validation/full_method_gate_audit/`.
  It reads 45 Phase 5 run summaries and exports claim gates, evidence
  inventory, a ranked next-action queue, a report, and an artifact-hygiene
  audit. Current gate status is
  `blocked_but_publishable_diagnostic_direction`, `full_method_allowed=false`,
  and `artifact_hygiene_passed=true`. Allowed claims are limited to PDCH-only
  HAMD diagnostic evidence, dataset/protocol controls as diagnostics, MODMA
  task-control evidence, MV10/MV11/MV19 primary label-only psychometric
  screening/confirmation/finite-sample downgrade evidence, corrected MV13/MV14
  anchor-linked external `mirt` corroboration, MV12
  design/run/aggregate-tradeoff diagnostic evidence, MV15 aggregate
  latent-conditioned identity diagnostic evidence, MV16 aggregate bounded
  calibration evidence, MV20 bounded criterion-overlap stress evidence, and a reframed
  diagnostic/audit-driven paper direction.
  RQ4 is now `allowed_limited` as first-round aggregate evidence, while
  blocked claims include full M0/M1/M2/M3 method start, transferable
  shared-symptom representation, positive EATD SDS generalization, EATD
  valence-adversarial design, and RQ3 context conditioning. After the corrected
  `mirt` rerun, its ranked next action is
  `NEXT_FINALIZE_MANUSCRIPT_AFTER_CORRECTNESS_GATES`.
- Phase 5 `P5_MV08 partial_invariance_measurement_design` is complete at
  `/root/autodl-tmp/analysis/phase5_minimal_validation/p5_mv08_partial_invariance_measurement_design/`.
  It did not train a model or read raw text/media. It converted the RQ1 pivot
  into an implementation-ready minimal-validation contract: active item
  supervision exists for E-DAIC PHQ-8 (`219` subjects), CMDC PHQ-9 (`77`
  subjects), and PDCH HAMD-17 (`99` subjects); CMDC HAMD is only a 25-subject
  sanity subset, while EATD SDS and MPDD PHQ-9 remain total-only. The model
  ladder is total-score floor, fixed construct-map head, and partial-invariance
  ordinal latent measurement with predeclared loading/threshold DIF deviations.
  Artifact hygiene passed. Treat this as `ready_to_implement_partial_invariance_validation`,
  not as model evidence or full-method authorization.
- Phase 5 `P5_MV08 partial_invariance_measurement` is complete at
  `/root/autodl-tmp/analysis/phase5_minimal_validation/p5_mv08_partial_invariance_measurement/`.
  It used aligned frozen BGE subject features and item labels for E-DAIC PHQ-8,
  CMDC PHQ-9, and PDCH HAMD-17, comparing train-mean items, total-score floor,
  fixed construct-map heads, and partial-invariance ordinal heads. Treat as a
  negative minimal-validation result:
  `blocked_not_better_than_total_score_floor`. In pooled evaluation, M2 improved
  over total-score floor on `0/3` active dataset slices; worst pooled M2 deltas
  were `+0.152` MAE versus total-score floor and `+0.140` versus fixed map.
  Feature identity BA remained `1.000`, while M2 prediction identity BA was
  `0.900`. Artifact hygiene passed and row predictions remain ignored
  local-only.
- Phase 5 `P5_MV08 error_analysis` is complete at
  `/root/autodl-tmp/analysis/phase5_minimal_validation/p5_mv08_error_analysis/`.
  It read the ignored local MV08 row predictions but exported only aggregate
  diagnostics. Current status:
  `complete_current_mv08_not_claimable_revision_or_freeze`. The analysis
  confirms the current MV08 head is not positive RQ1 evidence: pooled M2 is
  worse than total-score and fixed-map floors on all active slices, shows
  systematic positive bias, the largest pooled item delta is CMDC PHQ9_8/C08
  psychomotor (`+0.698` MAE versus total floor), and HAMD
  scale/item-specific DIF heads have threshold sparsity
  (`0.318` constant-threshold fraction). The follow-up MV08b
  total-anchored/residual measurement design is now predeclared separately.
- Phase 5 `P5_MV08b total_anchored_residual_measurement_design` is complete at
  `/root/autodl-tmp/analysis/phase5_minimal_validation/p5_mv08b_total_anchored_residual_measurement_design/`.
  It did not train a model, read raw text, read row-level predictions, or
  authorize full-method work. It predeclares one mechanism-changing revision:
  predict total/latent severity first, model sparse item residuals only after
  anchoring, pool or collapse sparse ordinal thresholds, and keep HAMD as a
  separate clinical measurement stress test. Current status is
  `ready_to_implement_mv08b_total_anchored_residual_measurement`.
- Phase 5 `P5_MV08b total_anchored_residual_measurement` is complete at
  `/root/autodl-tmp/analysis/phase5_minimal_validation/p5_mv08b_total_anchored_residual_measurement/`.
  It used aligned frozen BGE features and the same E-DAIC/CMDC/PDCH
  subject-level slices as MV08, comparing train-mean items, total-score floor,
  fixed construct-map floor, and total-anchored sparse residual heads.
  Artifact hygiene passed and row/residual predictions remain ignored
  local-only. Treat as a negative/blocked RQ1 result:
  `blocked_prediction_identity_increased_vs_mv08`. M2b beats both total-score
  and fixed-map floors on 2/3 pooled active slices, but prediction identity BA
  is `0.979`, above the predeclared MV08 M2 gate `0.900`; therefore it cannot
  support a transferable shared-measurement claim.
- Phase 5 `P5_MV09 conditional_dataset_identity_audit` is complete at
  `/root/autodl-tmp/analysis/phase5_minimal_validation/p5_mv09_conditional_identity_audit/`.
  It used aligned E-DAIC/CMDC/PDCH frozen BGE subject features, manifest labels
  and available covariates for diagnostic conditioning only, five-seed
  subject-level identity probes, and aggregate-only outputs. Artifact hygiene
  passed. Treat it as `complete_identity_gate_revision_needed`: unconditional
  dataset identity is a shortcut-risk screen rather than a standalone hard
  failure, but conditional feature identity remains high after conditioning
  (`E-DAIC/CMDC` PHQ-item residualized BA `0.991`, `CMDC/PDCH`
  severity-residualized BA `1.000`, three-way severity-residualized BA
  `1.000`). Future shared-latent claims must report conditional identity, and
  scale-specific post-head prediction identity is diagnostic rather than the
  same hard gate as shared latent identity. MV09 motivated the subsequent
  label-only PHQ psychometric baseline before any further multimodal RQ1 head
  iteration.
- Phase 5 `P5_MV10 classical_psychometric_invariance_baseline` is complete at
  `/root/autodl-tmp/analysis/phase5_minimal_validation/p5_mv10_psychometric_invariance_baseline/`.
  It is a label-only PHQ-8/PHQ-9 measurement screen over E-DAIC (`219`
  subjects) and CMDC (`77` subjects). It read no multimodal features, raw
  text/media, row-level predictions, or private review material, and artifact
  hygiene passed. Treat as `complete_partial_invariance_supported_approx`:
  configural screen passes, loading congruence is `0.998`, metric-loading
  screen passes for `7/8` items, threshold/scalar screen passes for `4/8`
  items, and candidate anchors are `C01`, `C04`, `C05`, and `C07`. It is not a
  formal multi-group ordinal CFA/IRT result. It motivated MV11 formal
  label-only graded-response IRT confirmation before any multimodal
  `X -> theta` target.
- Phase 5 `P5_MV11 formal_ordinal_psychometric_confirmation` is complete at
  `/root/autodl-tmp/analysis/phase5_minimal_validation/p5_mv11_formal_psychometric_confirmation/`.
  It fits a label-only multi-group graded-response IRT confirmation over the
  same E-DAIC/CMDC PHQ C01-C08 labels and exports only aggregate fit,
  invariance, DIF, and anchor-confirmation summaries. Treat as
  `complete_formal_partial_invariance_supported_with_bic_caveat`: all four
  MV10 anchors are confirmed, no loading-DIF items are strongly flagged,
  threshold DIF is flagged for `C02` and `C06`, AIC prefers the MV10 partial
  core model, and BIC prefers scalar. It is formal label-only measurement
  evidence, not a multimodal method pass. Full method remains blocked.
- Phase 5 `P5_MV12 two_stage_latent_target_design` is complete at
  `/root/autodl-tmp/analysis/phase5_minimal_validation/p5_mv12_two_stage_latent_target_design/`.
  It reads only aggregate MV07/MV07b/MV07c/MV08b/MV09/MV10/MV11/full-gate
  artifacts and exports target-generation, local-only-boundary, model-ladder,
  identity/transfer, pass/fail, source-evidence, implementation-queue, method
  reference, report, run-summary, and hygiene artifacts. Treat as
  `ready_to_implement_mv12_two_stage_latent_target`: primary anchors are
  `C01`, `C04`, `C05`, and `C07`; `C02` and `C06` are threshold-DIF-aware;
  `C03` and `C08` are sensitivity-only; theta scores, fitted parameters, row
  predictions, transformed features, projection directions, and model artifacts
  remain local-only. This is design evidence only, not a multimodal method
  pass.
- Phase 5 `P5_MV12 two_stage_latent_target` is complete as legacy old
  Chinese-BGE-chain evidence at
  `/root/autodl-tmp/analysis/phase5_minimal_validation/p5_mv12_two_stage_latent_target/`.
  It fits local-only label-derived PHQ theta targets for E-DAIC/CMDC, trains
  shallow BGE `X -> theta` heads, compares direct/floor baselines, and exports
  only aggregate metrics, identity, transfer, leakage, and hygiene summaries.
  Treat as `blocked_theta_gain_not_observed_scale_safe`: M12a improves
  same-dataset theta MAE over train mean on E-DAIC (`-0.078`) and CMDC
  (`-0.146`), and conditional shared-latent identity BA is `0.602`, but
  observed macro item MAE is worse than direct itemwise Ridge on E-DAIC
  (`+0.004`) and CMDC (`+0.067`), and external theta transfer does not beat the
  train-mean theta floor under the old-chain source-calibrated setting. Full
  method remains blocked; MV17a supersedes any universal external-transfer
  claim.
- Phase 5 `P5_MV12 latent_target_tradeoff_analysis` is complete at
  `/root/autodl-tmp/analysis/phase5_minimal_validation/p5_mv12_latent_target_tradeoff_analysis/`.
  It reads only aggregate MV09/MV12 summaries and aggregate MV07-MV12
  accuracy-invariance tables from the old Chinese-BGE chain. Treat as
  `complete_freeze_current_mv12_latent_target_line`: current latent-target
  evidence improves same-dataset theta utility and lowers identity versus
  upstream BGE features, but observed-scale validity and old-chain
  source-calibrated external theta transfer remain blockers. The corrected
  legacy interpretation is that M12a is not uniquely more invariant than
  dimension-matched severity outputs in that chain: B3 direct itemwise Ridge
  compressed to theta has lower pooled observed macro MAE (`0.692` vs `0.701`)
  and lower conditional identity (`0.579` vs `0.602`). MV17a supersedes any
  universal B3-dominance wording. Artifact hygiene passed.
- Phase 5 `P5_MV13 external_psychometric_replication_design` and
  `P5_MV13 external_psychometric_replication` are complete at
  `/root/autodl-tmp/analysis/phase5_minimal_validation/p5_mv13_external_psychometric_replication_design/`
  and
  `/root/autodl-tmp/analysis/phase5_minimal_validation/p5_mv13_external_psychometric_replication/`.
  R 4.1.2, lavaan 0.6.10, and archived R-compatible mirt 1.35.1 are installed
  and version-captured. The external `mirt::multipleGroup` PHQ model ladder
  qualitatively replicates MV11: four MV10 anchors are confirmed, loading DIF
  flags are zero, threshold DIF remains `C02`/`C06`, AIC prefers the MV10
  partial model, and BIC prefers scalar. Treat as
  `complete_external_mirt_with_convergence_warnings` because the configural
  core model did not converge within 3000 EM cycles; MV14 now quantifies that
  uncertainty. Local R item-response input, fitted
  parameters, factor/theta scores, parameter CI values, model objects, and
  bootstrap samples stay local-only.
- Phase 5 `P5_MV14 measurement_uncertainty_bootstrap_design` is complete at
  `/root/autodl-tmp/analysis/phase5_minimal_validation/p5_mv14_measurement_uncertainty_bootstrap_design/`.
  It is a label-only predeclaration, not a bootstrap run. It reads only
  aggregate MV10/MV11/MV13/full-gate artifacts and exports bootstrap-tier,
  input-boundary, local-only-boundary, stability-metric, pass/fail-gate,
  implementation-queue, method-source, runtime-preflight, report, run-summary,
  and hygiene artifacts. The design run summary records
  `ready_to_implement_mv14_measurement_uncertainty_bootstrap`, and the later
  MV14 run has now consumed that implementation contract. Track only future
  aggregate stability summaries; bootstrap inputs, draw
  indices, fitted parameters, full CI values, factor/theta scores, model
  objects, and detailed logs stay local-only.
- Phase 5 `P5_MV14 measurement_uncertainty_bootstrap` is complete at
  `/root/autodl-tmp/analysis/phase5_minimal_validation/p5_mv14_measurement_uncertainty_bootstrap/`.
  It ran the predeclared smoke/core/DIF tiers with R=`10/200/100` after the
  convergence-safe correction. Full-ladder model selection and LRT now require
  `fit_success && converged`; non-converged fits remain visible in attempted
  and failed denominators. Convergence-safe full-ladder effective core R is
  `120/200` after `185/200` fit-success draws, configural converges in
  `120/200`, the stable metric/partial/scalar ladder has `197` effective
  draws, the DIF tier has minimum anchor-support effective R `77/100`
  (threshold-DIF comparisons remain `100/100` effective), and artifact hygiene
  passed. Bootstrap-stable MV10
  anchors are `C01`, `C04`, `C05`, and `C07`; loading DIF remains sparse;
  threshold-DIF frequency remains concentrated on `C02` and `C06`; full-ladder
  AIC/BIC model selection remains split (`configural`/`scalar`), while the
  stable ladder prefers `partial_mv10`/`scalar`. Treat as item-level
  measurement-shift evidence with global model-selection uncertainty, not as a
  bootstrap-confirmed global partial-invariance result or full-method
  authorization. Local item-response inputs, bootstrap draws, fitted parameters,
  CI values, theta/factor scores, model objects, and detailed logs stay
  local-only.
- Phase 5 `P5_MV15 latent_conditioned_dataset_identity_design` is complete at
  `/root/autodl-tmp/analysis/phase5_minimal_validation/p5_mv15_latent_conditioned_identity_design/`.
  It is a design/predeclaration contract, not an identity-probe run. It reads
  only aggregate MV09/MV10/MV11/MV12/MV13/MV14/full-gate artifacts and exports
  dataset-scope, analysis-variable, conditioning-ladder, identity-probe,
  pass/fail-gate, local-only-boundary, implementation-queue, method-reference,
  report, run-summary, and hygiene artifacts. The primary future scope is
  E-DAIC/CMDC PHQ over aligned BGE features; sensitivity scopes are CMDC/PDCH
  severity and three-way severity-only checks. The design has 10 conditioning
  ladder rows, 7 identity-probe rows, and 8 pass/fail gates, including raw,
  total, predicted-total, observed-item, B3 itemwise-theta, psychometric-theta,
  covariate, predicted-output, and severity-only controls; artifact hygiene
  passed. This design contract has now been consumed by the MV15 runner. Theta
  scores, row predictions, residualized features, nuisance directions, split
  maps, and model artifacts stay local-only.
- Phase 5 `P5_MV15 latent_conditioned_dataset_identity` is complete as legacy
  old Chinese-BGE-chain evidence at
  `/root/autodl-tmp/analysis/phase5_minimal_validation/p5_mv15_latent_conditioned_identity/`.
  It used aligned E-DAIC/CMDC BGE features, fold-local PHQ theta generation,
  total/predicted-total/item/B3 itemwise-theta/psychometric-theta/covariate
  controls, predicted-output identity, and CMDC/PDCH plus three-way
  severity-only sensitivity. Artifact hygiene passed and subject overlap was
  zero. Treat as negative/blocked feature-invariance evidence:
  `blocked_theta_conditioned_feature_identity_high`. Raw BGE feature identity
  BA is `1.000`; theta-conditioned feature identity BA remains `1.000`;
  total/predicted-total/B3-conditioned feature identity BA is
  `1.000`/`1.000`/`1.000`; PHQ-item-conditioned feature identity is `0.974`;
  theta-only identity is `0.576`; predicted-theta output identity is `0.646`;
  B3 output Pareto-dominates predicted theta only in this legacy chain. MV17a
  supersedes universal B3-dominance wording. This freezes the current
  latent-conditioned BGE feature-identity line as diagnostic/negative evidence
  and motivated MV16 as a measurement-calibration test rather than full-method
  authorization.
- Phase 5 `P5_MV16 dif_guided_calibration_design` is complete at
  `/root/autodl-tmp/analysis/phase5_minimal_validation/p5_mv16_dif_guided_calibration_design/`.
  It is a design/predeclaration contract, not a calibration run. It reads only
  aggregate MV10/MV11/MV12/MV13/MV14/MV15/full-gate artifacts and exports
  dataset-direction, k-shot sampling, item-role, calibration-ladder,
  model-comparison, metric, pass/fail-gate, local-only-boundary,
  implementation-queue, method-source, report, run-summary, and hygiene
  artifacts. Primary directions are E-DAIC->CMDC and CMDC->E-DAIC PHQ
  calibration; k is `0/5/10/20/40`; locked anchors are `C01/C04/C05/C07`; the
  primary localized threshold-DIF items are `C02/C06`; comparators include
  zero-shot source measurement, global affine/monotonic theta calibration,
  all-threshold calibration, and direct target-domain adaptation. Full method
  remains blocked. Future target-shot maps, theta tables, calibration
  parameters, row predictions, fitted measurement parameters, feature matrices,
  and model artifacts stay local-only.
- Phase 5 `P5_MV16 dif_guided_calibration` is complete at
  `/root/autodl-tmp/analysis/phase5_minimal_validation/p5_mv16_dif_guided_calibration/`.
  It implemented the predeclared E-DAIC->CMDC and CMDC->E-DAIC PHQ
  calibration ladder for k=`0/5/10/20/40`, using manifest-governed PHQ labels
  and frozen BGE subject features only. Treat as bounded/negative calibration
  evidence: `blocked_no_dif_guided_small_k_gain`. Subject-overlap,
  ladder-completeness, anchor-safety, direct-baseline, output-identity, and
  artifact-hygiene gates pass, but the both-direction DIF-guided small-k
  mechanism gate fails. Best supported row is
  `D1_edaic_source_cmdc_target`/`M16d_global_plus_C02_C06` at k=`10`; best L4
  small-k delta theta MAE versus L0 is `-0.227`, while L4 small-k output
  identity BA remains `0.984`. Do not use MV16 as feature invariance, a
  positive method result, or full M0/M1/M2/M3 authorization.
- Diagnostic measurement-audit paper claim tables are complete at
  `/root/autodl-tmp/analysis/diagnostic_measurement_audit_paper/`. They export
  paper-facing allowed/blocked claim boundaries, seventeen key numeric findings,
  and seventeen literature-positioning rows from aggregate artifacts plus web-checked
  primary sources. Artifact hygiene passed. Treat them as manuscript
  scaffolding, not a replacement for source experiment artifacts.
- Diagnostic measurement-audit paper Data Governance and Label Contracts draft
  is complete at `/root/autodl-tmp/analysis/diagnostic_measurement_audit_paper/`.
  It exports aggregate dataset-governance, label-contract, construct-coverage,
  release-boundary, source-context, report, and hygiene files from the registry
  and aggregate audit/Phase 4 tables only. Artifact hygiene passed. Treat it as
  manuscript scaffolding, not an experiment-input interface.
- Diagnostic measurement-audit paper Baselines, Failure-Mode Diagnostics, and
  Measurement Results draft is complete at
  `/root/autodl-tmp/analysis/diagnostic_measurement_audit_paper/`. It is
  generated by `scripts/build_diagnostic_paper_results_sections.py` from
  aggregate Phase 2/3/5 artifacts only, and `artifact_hygiene_passed=true`.
  It frames MV12 as a predictive fidelity-dataset identifiability trade-off:
  same-dataset theta utility improves and low-dimensional outputs are less
  dataset-identifiable than upstream BGE features, but under the legacy
  old-chain setting same-dataset observed-scale validity and
  source-calibrated theta transfer still block a positive full-method claim.
  The current manuscript-facing prediction-consequence layer is MV17a:
  BGE-M3 primary and multilingual-E5 sensitivity both keep the feature-level
  chain blocked while external theta transfer and B3 dominance are
  encoder-dependent.
- Diagnostic measurement-audit paper manuscript draft v0.1 is complete at
  `/root/autodl-tmp/analysis/diagnostic_measurement_audit_paper/manuscript_draft.md`.
  It is generated by `scripts/build_diagnostic_paper_manuscript_draft.py` from
  aggregate data-governance, Results, claim, source-context, and full-gate
  artifacts only. It exports a manuscript draft, traceability matrix, open
  editing items, report, run summary, and hygiene audit with
  `artifact_hygiene_passed=true`. Treat it as a human-editing draft, not a
  submitted manuscript or a new experiment result.
- Diagnostic measurement-audit paper bibliography handoff is complete at
  `/root/autodl-tmp/analysis/diagnostic_measurement_audit_paper/`. It is
  generated by `scripts/build_diagnostic_paper_bibliography.py` from public
  aggregate source-context tables only. It exports `references.bib`,
  `citation_registry.csv`, `citation_source_map.csv`, `bibliography_report.md`,
  `bibliography_run_summary.json`, and
  `bibliography_artifact_hygiene_audit.json`; 53 current source-context rows
  map to 48 BibTeX entries, unmapped rows are zero, and artifact hygiene
  passes. `scripts/build_diagnostic_paper_bibliography_verification.py`
  generates the submission ledger with 48/48 primary-source spot checks and
  zero pending source-verification rows as of session 101. Confirmed metadata
  corrections include MODMA as the 2022 Scientific Data descriptor with
  ReShare as the access page, Ma 2021 author names, Patel 2019 `Youngha Oh`,
  WavLM's full arXiv author list, and the formal MPDD Challenge title. M002 is
  no longer blocked on primary-source verification, but remains open for
  current-prose citation coverage confirmation, target-venue citation style,
  and a final pre-submission metadata refresh.
- Phase 5 post-review measurement-validity route is predeclared at
  `/root/autodl-tmp/analysis/phase5_minimal_validation/p5_mv17_postreview_measurement_validity_route/`.
  It records the BGE feature-contract caveat, source verification summary,
  prioritized MV17a/MV18/MV19/MV20 queue, and stop lines. MV17a is
  complete at
  `/root/autodl-tmp/analysis/phase5_minimal_validation/p5_mv17a_multilingual_feature_contract/`
  and reproduces the blocked MV07/MV12/MV15 pattern under BGE-M3 and
  multilingual-E5. MV18 is complete at
  `/root/autodl-tmp/analysis/phase5_minimal_validation/p5_mv18_cmdc_pdch_hamd_same_scale_control/`
  with status `complete_exploratory_same_scale_context_shift_supported`. MV19
  is complete with status
  `complete_mv19_high_false_localization_downgrade_c02_c06`. MV20 is complete
  with status `complete_mv20_no_primary_criterion_overlap_excess`, freezing
  further overlap-threshold tuning or contamination-aware model work.
- Phase 5 `P5_MV20 criterion_overlap_stress` is complete at
  `/root/autodl-tmp/analysis/phase5_minimal_validation/p5_mv20_criterion_overlap_stress/`.
  It uses CMDC because Q1-Q12 question-position units are available, excludes
  PDCH because available units are coarse consultation segments, and excludes
  E-DAIC because true prompt/speaker units are unavailable. Primary BGE-M3
  CMDC PHQ-9 top-20 all/minus-high/minus-random/high-only MAE is
  `3.571`/`3.918`/`3.768`/`4.215`; criterion excess loss versus matched random
  is `0.150` with 95 percent CI `-0.320` to `0.671`. Multilingual-E5
  sensitivity also has `no_excess_criterion_overlap_evidence`. Treat MV20 as a
  bounded negative stress test, not a new method-development route.
- Phase 5 `P5_MV31 qwen_prompt_proxy_sensitivity` is complete at
  `/root/autodl-tmp/analysis/phase5_minimal_validation/p5_mv31_qwen_prompt_proxy_sensitivity/`.
  It re-embeds E-DAIC transcript variants with Qwen3-Embedding-0.6B and fits
  fixed Ridge/Logistic heads on the official train/dev split. E-DAIC
  participant-only and interviewer-only controls remain blocked because the
  available manifest and transcript CSV contract exposes no populated speaker
  roles. Treat MV31 as a prompt/protocol proxy sensitivity, not a
  speaker-resolved leakage proof. The stable reading is
  `no_clear_qwen3_excess_loss_from_repeated_turn_removal`: repeated-turn-only
  text does not match full dialogue for PHQ-8 MAE or binary Macro-F1, and
  repeated-turn removal does not increase PHQ-8 MAE.

Phase 2 gate status:

- Planned runs: 67.
- Completed runs: 66.
- Conditional exclusions: 1 (`mpdd_public_p3hf`).
- Blocked runs: 0.
- Completed metric rows: 313/318.
- Not-applicable metric rows: 5/318.
- Completion audit verdict: `phase2_goal_complete=true`.
- Method-design gate recommendation: `ready`.
- Artifact hygiene audit verdict: `artifact_hygiene_passed=true` for 66
  completed runs, 313 completed metric rows, 39 canonical prediction files, and
  33913 canonical prediction rows.

Validation commands:

```bash
python scripts/phase2_baseline_matrix.py --strict
python scripts/phase2_export_final_table.py
python scripts/phase2_completion_audit.py
python scripts/phase2_artifact_hygiene_audit.py
python scripts/phase2_metrics.py --self-test
```

Key Phase 2 outputs:

- `/root/autodl-tmp/analysis/phase2_baselines/baseline_matrix_status.csv`
- `/root/autodl-tmp/analysis/phase2_baselines/final_table/phase2_final_baseline_table.csv`
- `/root/autodl-tmp/analysis/phase2_baselines/final_table/phase2_final_baseline_table_audit.csv`
- `/root/autodl-tmp/analysis/phase2_baselines/phase2_completion_audit/phase2_completion_audit.md`
- `/root/autodl-tmp/analysis/phase2_baselines/phase2_artifact_hygiene_audit/phase2_artifact_hygiene_audit.md`

## Important Decisions

- Use `/root/autodl-tmp/datasets/registry.yaml` as the dataset path and role
  source of truth.
- Use generated manifests under `/root/autodl-tmp/datasets/manifests/` as the
  experiment input interface.
- Keep all splits subject-level. Do not split segments, modalities, tasks, or
  sessions from the same subject across train/dev/test.
- Do not train from ad hoc raw-directory scans unless the registry/manifest
  layer is intentionally being updated.
- Keep pretrained encoders frozen unless a later stage explicitly allows
  fine-tuning.
- Phase 2 allowed only simple unimodal baselines and Early/Late/Gated fusion.
  Hypergraph, causal modules, LLM summaries, contrastive learning, personality
  gating, weak supervision, and broad full-encoder fine-tuning were out of
  scope.
- P3HF is conditionally excluded from the canonical Phase 2 MPDD matrix because
  its packaged Young-only split/features/dev+test evaluation contract does not
  match the current 175-subject MPDD Phase 2 contract. It may be revisited only
  as a separately labeled packaged-Young-110 reproduction or a new explicit
  compatible protocol.
- MPDD OpenFace features have been synchronized to the server and completed in
  Phase 2; OpenFace is no longer a blocker.
- PDCH public LLM runners separate public `model_name` from local
  `--model-load-path`; canonical factor-prediction artifacts store public Qwen
  model IDs instead of local cache paths.
- Phase 3 dataset identity diagnostics show dataset/protocol identity is a real
  shortcut risk. Later minimal method validation must explicitly control,
  penalize, stratify, or report dataset/protocol identity effects before any
  full method or pooled cross-dataset claim.
- Phase 3 protocol diagnostics strengthen the Stop/Go signal for protocol
  robustness: available E-DAIC/CMDC controls show position/fixed-protocol and
  question-content dependence. Mechanism design should still wait for MODMA/EATD
  and MPDD diagnostics before finalizing the full method.
- Phase 3 task-valence diagnostics add a narrower RQ2 signal: MODMA
  cross-task transfer degradation is most credible for affective-task
  evaluation, while EATD eGeMAPS valence confusion is weak/negative evidence.
  Do not add a valence-adversarial method component solely from the EATD
  eGeMAPS result.
- Phase 3 MPDD diagnostics support continuing personality shortcut/moderation
  and subgroup calibration audits, but not naive audio-video-personality
  concatenation as a method component. Treat age as a subgroup/calibration axis,
  gait as psychomotor context validation, and gender/health as blocked until
  structured metadata is available.
- Overall Phase 3 Stop/Go: go to symptom ontology and minimal method-validation
  design with explicit dataset/protocol/task/subgroup controls; stop direct
  pooled-training claims, stop unsupported valence-adversarial design, and stop
  generic AVP concatenation as the default method.
- Phase 4 ontology decisions: PHQ-8/PHQ-9 C01-C08 are the cleanest shared
  construct bridge; HAMD-17 anxiety/somatic/functioning/insight items should be
  auxiliary or scale-specific where mappings are not direct; SDS is
  total/severity-only in the current EATD manifest; C09 death/self-harm is
  safety-sensitive and should use only explicit scale or clinical-text evidence.
- Phase 5 protocol decisions: minimal validation must report
  dataset-stratified, protocol/task-stratified, and subgroup/calibration
  metrics before pooled claims. Row-level predictions, learned embeddings,
  checkpoints, verbatim excerpts, raw prompts, and raw model responses are
  local-only unless separately reviewed.
- P5_MV01 decision: frozen WavLM is a runnable but weak PHQ-8/PHQ-9 construct
  bridge. CMDC same-dataset Ridge improves over train-mean but not over
  total-allocation; E-DAIC same-dataset and CMDC-to-E-DAIC cross-dataset are
  worse than train-mean. Do not use this as evidence for shared symptom
  representation; use it as a diagnostic baseline and proceed to identity or
  protocol-control validation before richer methods.
- P5_MV04 decision: train-fold dataset centering is a useful lightweight
  diagnostic control for the immediate E-DAIC/CMDC frozen-WavLM identity
  blocker, but it should not be treated as a deployable unknown-source method
  because it uses known dataset labels as control variables at transform time.
  Continue Phase 5 with inference-compatible residualization variants,
  protocol/task-slice extensions, or the next minimal-validation row before any
  full-method claim.
- P5_MV04b decision: source-agnostic projection is more inference-compatible
  than known-dataset centering and reduces prediction identity, but it does not
  remove feature-level dataset identity. Do not claim dataset-invariant shared
  representation from this feature contract yet.
- P5_MV04c decision: MODMA task nuisance projection is the strongest
  inference-compatible protocol-control signal so far, but it is task-specific
  diagnostic evidence rather than a shared-symptom method. EATD remains
  negative under eGeMAPS/Ridge: do not add a valence-adversarial method
  component from current EATD evidence, and do not treat EATD SDS total as
  positive cross-scale support.
- P5_MV03 decision: current frozen audio features do not support EATD SDS total
  external generalization beyond train mean, and EATD still cannot provide SDS
  item-level supervision. Do not use this row as positive cross-scale evidence;
  use it as a negative external stress result and consider an explicitly
  audited text/semantic feature variant only if needed.
- P5_MV03b decision: the audited EATD text-semantic variant is runnable but
  remains negative/weak. Character TF-IDF text heads only improve validation
  MAE over train mean by `0.00056`, below the predeclared meaningful threshold
  of `0.10` MAE and 1 percent relative gain. Do not use EATD SDS text as
  positive cross-scale evidence without a stronger, separately audited feature
  contract.
- P5_MV05 decision: AV-probability-first MPDD context calibration is runnable
  but negative. It improves overall ECE versus raw AV logits/probabilities, but
  worsens required age and personality/financial-stress subgroup ECE gaps and
  is worse than AV-probability-only recalibration on key calibration checks. Do
  not claim positive RQ3 context-calibration evidence from this row.
- P5_MV02 readiness decision: run the first HAMD-17 auxiliary bridge in
  PDCH-only mode with subject-level folds. CMDC HAMD is aligned after filtering
  placeholder item payloads but covers only 25 of 78 subjects, so it can be a
  small sanity subset only. PDCH has 99 HAMD-labeled subjects; 7 contain HAMD
  item code `9`, which official PDCH scoring treats as not sure/not applicable
  and excludes from total scoring. Use manifest HAMD totals as the primary
  severity target and apply the official `9 -> 0 for total` convention when
  deriving totals from item heads.
- P5_MV02 result decision: the PDCH-only HAMD auxiliary bridge is a bounded
  diagnostic pass. Best PDCH CV item-derived total MAE was `5.693` from
  early-fusion itemwise Ridge versus train-mean items `6.183`; best direct
  total MAE was `5.794` versus train-mean total `6.181`; best macro HAMD item
  MAE was `0.727` versus train-mean items `0.747`. CMDC 25-subject sanity did
  not support transfer: train-mean total MAE `3.595` beat the feature models,
  and early-fusion/eGeMAPS degraded badly. Do not claim cross-dataset HAMD
  generalization from MV02.
- P5_MV02b decision: the manifest-text PDCH hashing probe is runnable but weak.
  Best item-derived HAMD total MAE was `6.175` versus train-mean items `6.183`
  and macro item MAE stayed at `0.747`; do not use this lightweight raw-text
  probe as positive HAMD semantic-measurement evidence. The stronger MV02
  signal still comes from cached frozen BGE/early-fusion features.
- P5_MV06 readiness decision: evidence localization can proceed locally for
  E-DAIC dev MV01 C01-C08 predictions, CMDC MV01/MV02 predictions, and PDCH
  MV02 HAMD construct/item predictions. Current prediction-text overlap is
  E-DAIC 56 subjects, CMDC 77 subjects, and PDCH 99 subjects. Raw snippets,
  source paths, and per-subject rationales remain local-only; commit only
  aggregate evidence agreement, prompt-artifact rates, and construct coverage.
- P5_MV06 pilot decision: use the generated local packet only for manual
  evidence review or double-annotation planning. Do not claim RQ4 evidence
  localization until annotations are completed locally, inter-annotator or
  audit agreement is summarized, prompt-artifact rates are reported, and the
  tracked aggregate export passes hygiene.
- P5_MV06 workbench decision: use
  `scripts/phase5_prepare_mv06_annotation_workbench.py` to create the ignored
  local two-annotator workbook before manual annotation. The default summary
  gate now reads this workbench. Workbench files can contain subject-level rows,
  local text locators, local excerpts, and notes only because they are ignored
  local-only artifacts; tracked outputs must remain schema/rules/aggregate
  hygiene only.
- P5_MV06 summary-gate decision: use
  `scripts/phase5_summarize_mv06_evidence_annotations.py` as the required
  aggregate-only export path after local annotation. It must report agreement
  by dataset as well as an `ALL` diagnostic row. It now also reports
  nonparametric percentile bootstrap agreement-uncertainty summaries for the
  annotation fields, with evidence-presence CIs carried into the paper
  scaffold. First-round MV06 evidence can now be used only as bounded aggregate
  credibility evidence; stronger RQ4 wording should resolve the remaining
  incomplete local candidate if needed and discuss sampling limits.
- P5_MV06 AI preannotation decision: use
  `scripts/phase5_run_mv06_local_ai_preannotation.py` only as local triage to
  speed human review. Its ignored output can contain local excerpts and
  locators; tracked outputs are aggregate-only. Do not use AI preannotation as
  human annotation, agreement evidence, or RQ4 validity evidence.
- P5_MV06 human review pack decision: use
  `scripts/phase5_prepare_mv06_human_review_pack.py` to merge AI suggestions,
  original human annotation fields, and deterministic priority ranks into
  ignored local review files. Fill or correct the original ignored human
  workbook before running the summary gate; do not copy AI suggestions into
  evidence fields without human verification.
- P5_MV07 readiness decision: current cached features are not sufficient for a
  fair revised shared-symptom minimal-validation row until E-DAIC BGE is
  generated. That gap is now resolved locally: the aligned BGE text contract is
  ready for the next shallow MV07 validation. Regenerate eGeMAPS only with one
  shared extractor/schema; rerun WavLM only after a stronger
  inference-compatible identity-control design. Track only scripts/readiness
  summaries and reports; generated feature CSVs, predictions, embeddings, and
  weights remain local-only.
- P5_MV07 result decision: the aligned-BGE shallow validation is runnable but
  blocked as shared-symptom evidence. The BGE itemwise head does not
  consistently beat the total-allocation floor, and dataset identity remains
  nearly perfectly recoverable from both features and pooled PHQ predictions.
  Do not claim transferable shared symptom representation from the current BGE
  contract; either complete MV06 annotations for evidence credibility or design
  a stronger identity-control/shared-feature contract before full method work.
- P5_MV07b decision: the BGE identity projection is a meaningful partial
  diagnostic. Train-fold source-agnostic nuisance projection reduces feature and
  prediction identity without using evaluation target labels or evaluation
  dataset labels at transform time, but the best identity-controlled variant
  remains worse than total allocation on CMDC. Do not claim transferable shared
  symptom representation from MV07b; either resolve this floor gap with another
  audited shared-symptom contract or demote MV07b to partial diagnostic evidence
  in the paper framing.
- P5_MV07c decision: train-fold-selected total anchoring does not resolve the
  shallow BGE floor gap. It further reduces prediction identity but does not
  beat raw/projected total allocation on CMDC. Stop iterating small shallow BGE
  head variants; reframe the BGE sequence as negative/partial evidence and
  revisit RQ1 only with a genuinely changed psychometric measurement contract.
- RQ1 method-target decision: direct fixed shared-symptom mapping is now a
  too-strong hypothesis under current Phase 5 evidence. The next method target
  should be partial measurement invariance: shared latent constructs plus
  scale-specific DIF/loading-threshold deviations, first compared against
  total-score and fixed construct-map baselines on E-DAIC/CMDC/PDCH.
- P5_MV08 design decision: the next executable RQ1 row is the partial
  invariance ordinal measurement pilot. It must compare total-score floors,
  fixed-map heads, and partial-invariance heads on E-DAIC/CMDC/PDCH before any
  full method or transferable shared-symptom claim is reconsidered.
- P5_MV08 result decision: the first partial-invariance ordinal measurement
  pilot is negative under the frozen BGE/lightweight head contract. It supports
  the paper framing that scale alignment is a real measurement problem, but it
  does not authorize a transferable RQ1 or full-method claim. Next work should
  analyze the failure mode and either predeclare a stronger psychometric
  measurement revision or freeze MV08 as diagnostic/negative evidence.
- P5_MV08 error-analysis decision: the current MV08 contract remains negative
  evidence unless the predeclared MV08b contract passes. The error analysis
  justifies total anchoring, item residual modeling only after severity is
  controlled, pooled/collapsed sparse ordinal thresholds, and HAMD as a
  separate clinical measurement stress test.
- P5_MV08b design decision: MV08b is now predeclared as the only allowed
  follow-up to the negative MV08 pilot. It must compare train-mean items,
  total-score floor, fixed construct-map floor, and total-anchored residual
  item heads on the same subject-level E-DAIC/CMDC/PDCH slices. It passes only
  if it beats total-score and fixed-map floors on at least two pooled active
  slices while keeping prediction identity no higher than current MV08 M2.
  If it fails, freeze MV08/MV08b as negative RQ1 diagnostic evidence and pivot
  writing toward a measurement-audit paper.
- P5_MV08b result decision: MV08b partially improves measurement error but
  fails the predeclared identity gate. Freeze the current frozen-BGE/shallow
  RQ1 modeling sequence as negative diagnostic evidence. Do not start another
  shallow RQ1 head iteration unless a genuinely new data, feature, or
  measurement source is introduced. The paper direction should now emphasize a
  diagnostic measurement-audit contribution; a draft outline exists at
  `/root/autodl-tmp/docs/diagnostic_measurement_audit_paper_outline.md`.
- Diagnostic paper table decision: use
  `scripts/build_diagnostic_paper_claim_tables.py` to regenerate the
  paper-facing claim boundary and key finding tables from aggregate gates.
  These tables support drafting but do not authorize stronger claims. The next
  writing task is the Data Governance and Label Contracts section and/or
  E-DAIC MV06 double-annotation strengthening.
- Diagnostic data-governance section decision: use
  `scripts/build_diagnostic_paper_data_governance_section.py` to regenerate
  the paper-facing Data Governance and Label Contracts draft from registry,
  aggregate dataset audit, and Phase 4 label-contract sources only. It is safe
  for Git only after its artifact-hygiene audit passes; it must not replace the
  local manifest layer for experiments.
- Phase 5 full-method gate decision: use
  `scripts/phase5_full_method_gate_audit.py` as the authoritative claim
  boundary before starting the full symptom-aligned method. Full method remains
  blocked, but a diagnostic/audit-driven paper direction is viable if claims
  are bounded and negative evidence is reported honestly.
- MV09 identity-gate decision: unconditional dataset identity BA is a
  shortcut-risk screen, not a standalone hard-failure criterion. For future
  shared latent representations, audit dataset identity after conditioning on
  target severity, aligned item labels where available, and legitimate
  covariates. Treat scale-specific post-head prediction identity as diagnostic
  unless the output space is explicitly shared. Current conditional BGE identity
  remains high, so the project pivots from a generic diagnostic audit toward a
  measurement-shift / measurement-validity paper and a label-only
  psychometric baseline.
- MV10 psychometric-baseline decision: the E-DAIC PHQ-8 and CMDC PHQ-9 labels
  support an approximate common one-factor/metric screen, but threshold/scalar
  invariance is partial. Use `C01`, `C04`, `C05`, and `C07` as candidate
  anchors only until formal confirmation.
- MV11 formal-psychometric decision: the label-only multi-group graded-response
  IRT confirmation preserves all four MV10 anchors and flags no strong loading
  DIF, but threshold DIF remains for `C02` and `C06` and AIC/BIC disagree on
  partial versus scalar core models. Treat this as enough to predeclare a
  two-stage latent target, not as a full shared-symptom method pass. Factor
  scores, posterior scores, fitted item parameters, row diagnostics, and model
  artifacts must stay local-only.
- MV12 latent-target design decision: the next executable RQ1 test must
  separate `Y -> theta` label measurement from `X -> theta` multimodal
  prediction. The future runner must compare train-mean theta, observed-total
  floors, direct `X -> Y` total-allocation/itemwise baselines, primary BGE
  `X -> theta`, optional identity-projected `X -> theta`, and
  `theta -> Y^(d)` mapping. Full method remains blocked until the actual run
  passes predictive utility, external transfer, conditional shared-latent
  identity, leakage, and artifact-hygiene gates.
- MV12 latent-target run decision: the two-stage `X -> theta` test is useful
  but legacy old Chinese-BGE-chain evidence, not positive method evidence.
  Same-dataset theta prediction and conditional shared-latent identity improve,
  but observed-scale reconstruction is not safe versus the direct itemwise
  floor and old-chain source-calibrated external theta transfer fails. Treat
  MV12 as bounded measurement-shift evidence and do not generalize its external
  transfer result across encoders after MV17a.
- MV12 tradeoff-analysis decision: aggregate-only comparison across MV07-MV12
  closes the legacy old-chain latent-target line. Freeze it as diagnostic
  evidence with a dimension-matched severity caveat: M12a is lower-identity
  than upstream BGE features but is Pareto-dominated by B3 direct itemwise Ridge
  compressed to theta in the legacy chain. Do not state universal B3 dominance
  after MV17a, and do not start full M0/M1/M2/M3 or another small shallow-head
  RQ1 variant unless a genuinely new measurement, feature, or data mechanism
  is predeclared.
- MV13 external-psychometric decision: R/lavaan/mirt are now available and
  version-captured. External R `mirt::multipleGroup` replication preserves the
  MV10/MV11 qualitative anchor/DIF localization pattern, but the configural
  model convergence warning and small CMDC item-labeled N required MV14
  uncertainty evidence before stronger item-level DIF wording. Treat MV13 as
  label-only measurement evidence, not multimodal method success.
- MV14 measurement-uncertainty design decision: use group-wise subject
  bootstrap over the same E-DAIC/CMDC PHQ C01-C08 item-response boundary to
  quantify convergence, AIC/BIC model-selection frequency, anchor support,
  loading-DIF and threshold-DIF selection frequency, item-fit stability, and
  SE/CI availability. The default predeclared ladder is smoke R=10, core
  stability R=200, item-DIF stability R=100, plus optional `boot.mirt` and
  `boot.LR` sensitivity tiers. MV14 is uncertainty evidence only, not full
  method authorization.
- MV14 measurement-uncertainty run decision: the corrected aggregate bootstrap
  supports item-level PHQ measurement-shift wording. All four MV10 anchors have
  support frequency at least `0.93`, no item exceeds loading-DIF frequency
  `0.50`, and threshold-DIF frequencies are highest for `C02` (`0.80`) and
  `C06` (`0.76`). Convergence-safe full-ladder effective R is `120/200` after
  `185/200` fit-success draws; configural converges in `120/200`; the stable
  metric/partial/scalar ladder has `197` effective draws; the DIF tier has
  minimum anchor-support effective R `77/100`, while threshold-DIF comparisons
  are `100/100` effective. Use MV14 for stable
  anchors, sparse loading DIF, localized threshold non-equivalence, and global
  model-selection uncertainty. Do not use MV14 as bootstrap-confirmed global
  partial invariance or full-method evidence.
- Diagnostic results-section decision: use
  `scripts/build_diagnostic_paper_results_sections.py` to regenerate the
  Baselines, Failure-Mode Diagnostics, and Measurement Results scaffold from
  aggregate artifacts only. Its manuscript framing should treat MV17a as the
  canonical prediction-consequence layer and MV12/MV15 as legacy old-chain
  support: measurement harmonization can reduce output-level identity, but
  observed-scale validity and feature invariance remain blocked, while external
  theta transfer and B3 dominance are encoder-dependent.
- MV15 latent-conditioned identity design decision: MV15 was predeclared with
  dimension-matched controls comparing `I(Z;D|theta)` to raw feature identity,
  observed labels, PHQ total, predicted total, B3 itemwise-theta severity,
  predicted psychometric theta, covariates, and severity-only external
  sensitivities. Any pass could only update identity-gate wording or motivate
  MV16, not authorize full M0/M1/M2/M3 construction.
- MV15 latent-conditioned identity run decision: MV15 blocks theta-specific
  feature-invariance wording under the current BGE contract. Conditioning BGE
  on label theta does not reduce E-DAIC/CMDC feature identity below total,
  predicted-total, or B3 severity controls; the lower one-dimensional
  theta/predicted-theta output identity must not be reported as upstream
  feature invariance. Freeze this line as negative diagnostic evidence and
  move to MV16 as a measurement-calibration test, not as full-method
  authorization.
- MV16 DIF-guided calibration design decision: MV16 is predeclared with
  E-DAIC->CMDC and CMDC->E-DAIC PHQ calibration directions, k=`0/5/10/20/40`,
  locked anchors `C01/C04/C05/C07`, localized `C02/C06` threshold-DIF
  calibration, global affine/monotonic calibration, all-threshold calibration,
  zero-shot source measurement, and direct target-adaptation comparators. The
  subsequent run consumed this design and did not pass the target-calibration
  mechanism gate; neither the design nor the run can override MV15's
  feature-identity blocker or authorize full M0/M1/M2/M3.
- MV16 DIF-guided calibration run decision: the completed few-shot calibration
  ladder is negative/bounded under the predeclared mechanism gate. L4
  global-plus-C02/C06 calibration helps only asymmetrically, with the best
  small-k theta-MAE delta versus L0 in E-DAIC->CMDC, but the both-direction
  small-k DIF-guided gate fails and output identity remains high. Use MV16 as
  a falsifying calibration stress test, not as a positive method result.
- Post-review BGE feature-contract decision: the current MV07 -> MV12 -> MV15
  -> MV16 BGE-linked feature-level chain is legacy/diagnostic because E-DAIC
  MV07 used `BAAI/bge-small-zh-v1.5`, a Chinese encoder, on English transcripts
  and the available transcript CSVs do not expose speaker roles for
  participant/interviewer filtering. MV17a now addresses the paper-critical
  MV07/MV12/MV15 part of this caveat with BGE-M3 and multilingual-E5; both
  encoders reproduce the blocked result, both fail observed-scale validity, and
  both keep theta-conditioned feature identity BA at `1.000`. External theta
  transfer passes for BGE-M3 but fails for multilingual-E5, and B3 dominance is
  false for BGE-M3 but true for multilingual-E5. Do not interpret remaining
  high dataset identity as a pure participant symptom-representation failure.
  MV10/MV11/MV19 primary label-only psychometric evidence is unaffected by the
  BGE feature-contract caveat; corrected MV13/MV14 now provide external
  `mirt` corroboration with convergence and finite-sample caveats.
- Post-review paper-framing decision: the manuscript should be a target
  measurement-validity audit. Phase 3 is motivating benchmark/protocol shortcut
  evidence; MPDD/RQ3 is a population stress test; MV06/RQ4 is measurement
  credibility support. Stop personality gating, evidence-network construction,
  extra shallow BGE variants, extra projection dimensions, EATD
  valence-adversarial modules, and MV16 retuning unless a new predeclared
  mechanism changes the gate.
- Next measurement-aware route decision: MV17a, MV18, MV19, MV20, MV21, MV24,
  and the corrected MV13/MV14 `mirt` rerun are complete. The experiment queue
  can freeze again after MV24; the active next item is manuscript integration
  of the fixed ordinal-head method/table and primary-source citation
  verification. MV06
  agreement uncertainty is complete; optional next RQ4 work is resolving the
  one incomplete local candidate before stronger RQ4 wording.

## Data Quality Watchlist

- E-DAIC subject `657` is missing `657_CNN_VGG.mat` in the original official
  AVEC feature release. Treat this as an official omission, not local
  corruption.
- E-DAIC transcript CSVs do not expose a speaker column, so interviewer-only
  and participant-only controls require separate transcript/protocol work.
- CMDC `SubjectInfo.xlsx` has duplicate `MDD20` metadata and omits folder
  `MDD21`; this is a metadata quality risk, not upload incompleteness.
- CMDC audio/video-only scores are suspiciously high and should be treated as
  RQ2 shortcut-risk signals until interviewer/question-position controls are
  run.
- PDCH has 100 audio subjects locally; HAMD annotations cover 99. Subject
  `034A` has two audio/text segments but no HAMD annotation.
- PDCH has 7 HAMD-labeled subjects with item code `9`; raw item sums are total
  `+9`, but official scoring excludes code `9` and scored item sums match
  manifest totals for 99/99 labeled subjects.
- E-DAIC PHQ-8 totals cover 275 subjects, but valid PHQ-8 item payloads cover
  219 subjects. Item-level construct work should use the item-labeled train/dev
  subjects only; official test labels remain total-only in the current
  manifest.
- MODMA has 5 invalid WAV files: `02010004/24.wav` through `02010004/28.wav`.
  The manifest and audit now mark these rows invalid and exclude them from
  valid-row counts; MODMA has 1503 valid rows out of 1508.
- MPDD local copy still lacks official test label CSVs even though current
  official materials document them. Existing MPDD Phase 2 results use labeled
  train-only OOF and remain valid.
- MPDD structured `gender` and `health_condition` fields are empty in the
  manifest, blocking gender-only, health-only, and gender/health subgroup
  diagnostics until metadata is supplied.
- CMDC HAMD total+full-item labels cover only 25 of 78 subjects after filtering
  placeholder NaN item payloads. Treat CMDC HAMD as a small sanity subset, not a
  complete HAMD bridge.

## Version Policy

Track:

- Code, configs, docs, public dataset schemas/examples, lightweight aggregate
  audits, session memories,
  and small summaries for the project's own Phase 3+ diagnostics and method
  experiments.
- Phase 2 baseline reproduction scripts and matrix config, but not generated
  Phase 2 baseline result artifacts by default.
- GitHub is for the core reproducible experiment skeleton only: maintained
  scripts, configs, governance docs, lightweight summaries, and paper-critical
  experiment reports. Server-local stable utilities that are not expected to
  change often do not need to be uploaded unless they become part of the
  reproducibility contract.

Do not track:

- Raw datasets, large features, archives, audio, video, pretrained weights,
  checkpoints, caches, local runtime files, real row-level subject manifests,
  real file-integrity rows, real subject split maps, raw clinical text, raw
  prompts, raw model responses, bulky prediction/embedding artifacts, or
  generated `analysis/phase2_baselines/` baseline result artifacts.
- Plaintext credentials must never be written to Git, memory files, scripts, or
  shell history. Use GitHub token, SSH key, or `gh auth login` for remote
  authentication.

GitHub CLI is installed and authenticated for account `zwtbb` with token-based
HTTPS Git operations. Do not use plaintext passwords for GitHub; GitHub
password authentication is not an acceptable project workflow.

First GitHub publish is complete. Remote
`https://github.com/zwtbb/multidatasets_mdd` has clean default branch `main`
starting from root commit `a67cfdb` (`Publish clean experiment skeleton`), built
from a Git archive of the current safe tracked tree. The remote history does
not contain local Phase 2 baseline result blobs, row-level prediction files,
model weights, embeddings, raw data, or plaintext credentials. Continue future
remote updates from the clean remote/main lineage or another verified clean
publish path; do not push the old local `main` history directly.

Current GitHub cleanup state as of 2026-09-03: local `/root/autodl-tmp` is on
clean `main` tracking `origin/main`; GitHub exposes only `main`. Use
`git ls-remote origin refs/heads/main` for the exact current remote commit,
because the clean publish helper may recreate a same-tree source commit on the
clean remote lineage. Stable cleanup anchors are `475360f` (`Publish MV24 fair
ablation manuscript snapshot`) for the MV24 content publish and `dd6dbcb`
(`Record remote GitHub cleanup`) for the branch/worktree cleanup record; later
clean planning snapshots may sit on top. Old `origin/codex/*` branches were
deleted, old local server-working branch refs/worktrees were removed, and
unreachable Git objects were pruned. Continue future GitHub updates from clean
`main` through the publish helper; do not resurrect old server-working branch
history.

Clean GitHub publish workflow is documented at
`/root/autodl-tmp/docs/github_publish_workflow.md` and implemented by
`/root/autodl-tmp/scripts/publish_clean_github_snapshot.py`. Use this helper
for future GitHub updates unless replacing it with an equivalently audited clean
publish path. The helper is dry-run by default and checks the publish tree for
banned Phase 2 baseline artifacts, bulky prediction/embedding/model paths, and
plaintext credential-like content before committing on the clean remote lineage.
For exact current versions, inspect Git directly with `git log -1` for the
local working branch and `git ls-remote origin refs/heads/main` for the clean
remote branch instead of treating memory prose as an immutable SHA ledger.

## Immediate Orchestration Plan

1. Keep using the layered memory hierarchy for all future sessions.
   Use `memory/ACTIVE_HANDOFF.md` as the short active context after reading this
   master memory; update it whenever the gate, next task, or versioning boundary
   changes.
2. Treat planned Phase 3 diagnostics as complete:
   - E-DAIC/CMDC protocol and interviewer shortcut diagnostics: complete for
     available text controls.
   - MODMA task-transfer diagnostics: complete.
   - EATD valence sensitivity diagnostics: complete for audio eGeMAPS.
   - MPDD individual-difference shortcut and subgroup calibration diagnostics:
     complete, with gender/health blocked by missing structured metadata.
   - Dataset-identity probes over reusable frozen representations: complete.
3. Keep future GitHub updates on the clean `main`/`origin/main` lineage via
   `scripts/publish_clean_github_snapshot.py`; do not recreate or push the old
   server-working branch history.
4. Use the Phase 5 full-method gate audit and consolidation inventory as the
   active claim boundary. MV09 revises identity-gate semantics,
   MV10/MV11/MV19/MV21/MV29 provide the primary PHQ measurement evidence:
   substantial common structure, recurrent C01/C04/C05/C07 anchor candidates
   with strict threshold caveats, hypothesis-generating recurrent C02/C06
   threshold-shift candidates under tolerance sensitivity, and observed-N
   finite-sample limits. Corrected
   MV13/MV14
   provide anchor-linked external `mirt` corroboration with convergence and
   finite-sample caveats. MV25/MV30 provide the current representation-gate
   wording: raw corpus identity is strong, but E-DAIC/CMDC residual identity is
   control- and probe-dependent. MV12/MV15/MV16 remain bounded or negative
   prediction-consequence evidence, MV17a is the canonical prediction-consequence
   layer with BGE-M3 primary and multilingual-E5 sensitivity, MV18 gives
   exploratory same-HAMD context-shift support without formal invariance claims,
   MV20 closes the bounded protocol-label-overlap stress as negative/no-excess
   evidence, and MV21 also supplies the same-lineage DAIC-WOZ/E-DAIC PHQ-8
   control and descriptive same-HAMD reinforcement. MV24 supplies the formal
   measurement-aware ordinal method table with a failed fair shared-layer
   calibrated ablation gate, a real-data targeted item analysis showing
   shared-head versus corpus-specific-head near ties on `C02/C06`, and a
   companion fixed-latent DIF simulation that supports only weak item-local
   mechanism consistency under planted threshold shift. MV28 supersedes the
   stronger old RQ3 attribution: under repeated target-label budget splits and
   MV24 default-budget checks, target-only direct calibration is the strongest
   Macro Item MAE comparator, source-plus-target calibrated rows can improve
   calibration-in-the-large, and corpus-specific ordinal heads do not show
   independent overall performance gains. Session 108 integrates this into the
   formal manuscript as a target-comparability / measurement-contract audit:
   the title, abstract, contributions, Section 3.2 local-independence wording,
   calibration definitions, RQ2 finite-sample terminology, RQ1 leakage
   sensitivity, Table 3, Discussion, Scope, Conclusion, Word export, MV31
   prompt-proxy artifacts, and bibliography artifacts have been updated;
   early weak or superseded MV rows are retired from the active experiment
   queue. Old M0/M1/M2/M3 full method construction remains blocked, but MV24
   is the current formal PHQ shared-item method result with MV28-bounded
   architecture attribution. The next active task is
   current-prose citation coverage confirmation, target-venue formatting, and
   final pre-submission metadata refresh around the already verified bibliography.
   Parallel writing work may continue, but the manuscript must
   use target-comparability framing, corrected bibliography metadata,
   the session-101 primary-source verification ledger, and the session-102
   fair-ablation claim boundary before submission.
