# MASTER MEMORY

Last updated: 2026-08-11 UTC

This is the master memory for the cross-scale depression modeling project. Keep
it short, current, and decision-oriented. Detailed history belongs in
session-level memory files under `memory/sessions/`.

## Memory Hierarchy

- Master memory: `/root/autodl-tmp/MEMORY.md`
  - Owns current project status, global decisions, active gates, and next
    orchestration steps.
  - Do not store long per-run logs or full metric tables here.
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
  - `/root/autodl-tmp/memory/sessions/session_master_orchestration.md`
- Template for future sessions:
  - `/root/autodl-tmp/memory/templates/session_memory_template.md`
- Generated artifacts remain the source of truth for numeric tables, manifests,
  and audit reports. Memory files should cite those artifacts rather than copy
  large tables.

When starting a new session, read this master memory first, then read only the
session memory files relevant to that task. Each separate task should maintain
its own session memory file and update the master only with stable cross-session
facts, final decisions, blockers, or handoff-worthy results.

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

RQ1-RQ3 are the main contributions. RQ4 is a credibility/evidence layer, not a
fourth large independent modeling module. Do not freeze a final model
architecture before diagnostic evidence identifies which failure modes are real.

## Dataset Roles

| Dataset | Main role | Primary use |
| --- | --- | --- |
| E-DAIC | Primary development dataset | PHQ-8 symptoms, total score, binary label, interviewer prompt bias |
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
- Current next stage: measurement-aware validation under the Phase 5
  full-method gate. The current MV12 latent-target line is frozen as bounded
  diagnostic evidence, the Baselines/Failure-Mode/Measurement Results scaffold
  is complete, and full-method work remains blocked until a genuinely new
  predeclared mechanism changes the gate.
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
  aggregate completion, field-issue, evidence-field, prompt-artifact, and
  dataset-stratified agreement summaries. Current status is
  `ready_for_aggregate_evidence_review`: 30 completed candidates and 20
  double-annotated candidates. Overall evidence-presence kappa is `0.808`;
  CMDC evidence-presence kappa is `0.643`; PDCH evidence-presence kappa is
  `1.000`; E-DAIC currently has only 2 double pairs with degenerate marginals,
  so its kappa is undefined. Artifact hygiene passes; no raw text, source
  locator map, or subject-level rows are exported.
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
  priority-1/2 candidates, and still 0 completed human candidates.
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
  It reads 32 Phase 5 run summaries and exports claim gates, evidence
  inventory, a ranked next-action queue, a report, and an artifact-hygiene
  audit. Current gate status is
  `blocked_but_publishable_diagnostic_direction`, `full_method_allowed=false`,
  and `artifact_hygiene_passed=true`. Allowed claims are limited to PDCH-only
  HAMD diagnostic evidence, dataset/protocol controls as diagnostics, MODMA
  task-control evidence, MV10/MV11 label-only psychometric screening and
  confirmation, MV12 design/run/aggregate-tradeoff diagnostic evidence, and a
  reframed diagnostic/audit-driven paper direction. RQ4 is now
  `allowed_limited` as first-round aggregate evidence,
  while blocked claims include full M0/M1/M2/M3 method start,
  transferable shared-symptom representation, positive EATD SDS
  generalization, EATD valence-adversarial design, and RQ3 context
  conditioning. After MV12 aggregate analysis, its ranked next action is
  `NEXT_DRAFT_BASELINES_FAILURE_MODE_MEASUREMENT_SECTIONS`.
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
- Phase 5 `P5_MV12 two_stage_latent_target` is complete at
  `/root/autodl-tmp/analysis/phase5_minimal_validation/p5_mv12_two_stage_latent_target/`.
  It fits local-only label-derived PHQ theta targets for E-DAIC/CMDC, trains
  shallow BGE `X -> theta` heads, compares direct/floor baselines, and exports
  only aggregate metrics, identity, transfer, leakage, and hygiene summaries.
  Treat as `blocked_theta_gain_not_observed_scale_safe`: M12a improves
  same-dataset theta MAE over train mean on E-DAIC (`-0.078`) and CMDC
  (`-0.146`), and conditional shared-latent identity BA is `0.602`, but
  observed macro item MAE is worse than direct itemwise Ridge on E-DAIC
  (`+0.004`) and CMDC (`+0.067`), and external theta transfer does not beat the
  train-mean theta floor. Full method remains blocked.
- Phase 5 `P5_MV12 latent_target_tradeoff_analysis` is complete at
  `/root/autodl-tmp/analysis/phase5_minimal_validation/p5_mv12_latent_target_tradeoff_analysis/`.
  It reads only aggregate MV09/MV12 summaries and aggregate MV07-MV12
  accuracy-invariance tables. Treat as
  `complete_freeze_current_mv12_latent_target_line`: current latent-target
  evidence improves same-dataset theta utility and conditional identity, but
  observed-scale safety and external theta transfer remain decisive blockers.
  Artifact hygiene passed; next work is manuscript drafting or optional
  E-DAIC MV06 strengthening, not another small shallow-head iteration.
- Diagnostic measurement-audit paper claim tables are complete at
  `/root/autodl-tmp/analysis/diagnostic_measurement_audit_paper/`. They export
  paper-facing allowed/blocked claim boundaries, twelve key numeric findings,
  and fifteen literature-positioning rows from aggregate artifacts plus web-checked
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
  same-dataset theta utility and conditional identity improve, cross-dataset
  observed-scale transfer improves versus direct item transfer, but
  same-dataset observed-scale safety and external theta transfer still block a
  positive full-method claim.

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
  by dataset as well as an `ALL` diagnostic row. First-round MV06 evidence can
  now be used only as bounded aggregate credibility evidence; strengthen E-DAIC
  agreement before making a stronger cross-dataset RQ4 claim.
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
  measurement-shift / measurement-invariance paper and a label-only
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
  but not positive method evidence. Same-dataset theta prediction and
  conditional shared-latent identity improve, but observed-scale reconstruction
  is not safe versus the direct itemwise floor and external theta transfer
  fails. Treat MV12 as bounded measurement-shift evidence.
- MV12 tradeoff-analysis decision: aggregate-only comparison across MV07-MV12
  closes the current latent-target line. Freeze it as paper-critical diagnostic
  evidence; do not start full M0/M1/M2/M3 or another small shallow-head RQ1
  variant unless a genuinely new measurement, feature, or data mechanism is
  predeclared.
- Diagnostic results-section decision: use
  `scripts/build_diagnostic_paper_results_sections.py` to regenerate the
  Baselines, Failure-Mode Diagnostics, and Measurement Results scaffold from
  aggregate artifacts only. Its manuscript framing should treat MV12 as a
  predictive fidelity-dataset identifiability trade-off, not as a simple model
  failure or a positive full-method result.
- Next measurement-aware route decision: the next experiments should be
  predeclared in order as MV13 external psychometric replication, MV14
  measurement-uncertainty bootstrap, MV15 latent-conditioned dataset identity,
  and MV16 cross-dataset theta calibration / few-shot scale linking. Do not run
  MV08c-like shallow-head variants, EATD valence-adversarial modules, naive
  personality conditioning, or a 15-dimensional free latent symptom model
  without new evidence and a new predeclared contract. A lightweight runtime
  preflight found no `Rscript` on PATH, so MV13 needs R/mirt setup or an
  equivalent container/workflow before execution.

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

Pre-push history gate: the current working tree tracks zero
`analysis/phase2_baselines/` files, but local history still contains early
Phase 2 artifact commits (`be8b52c` plus deletion commit `997a7a5`). Do not push
this branch history as-is. Before first remote upload, create a clean
publish/squash branch and verify the push candidate no longer contains Phase 2
baseline result blobs.

First GitHub publish is complete. Remote
`https://github.com/zwtbb/multidatasets_mdd` has clean default branch `main`
starting from root commit `a67cfdb` (`Publish clean experiment skeleton`), built
from a Git archive of the current safe tracked tree. The remote history does
not contain local Phase 2 baseline result blobs, row-level prediction files,
model weights, embeddings, raw data, or plaintext credentials. Continue future
remote updates from the clean remote/main lineage or another verified clean
publish path; do not push the old local `main` history directly.

Clean GitHub publish workflow is documented at
`/root/autodl-tmp/docs/github_publish_workflow.md` and implemented by
`/root/autodl-tmp/scripts/publish_clean_github_snapshot.py`. Use this helper
for future GitHub updates unless replacing it with an equivalently audited clean
publish path. The helper is dry-run by default and checks the publish tree for
banned Phase 2 baseline artifacts, bulky prediction/embedding/model paths, and
plaintext credential-like content before committing on the clean remote lineage.

## Immediate Orchestration Plan

1. Keep using the layered memory hierarchy for all future sessions.
2. Treat planned Phase 3 diagnostics as complete:
   - E-DAIC/CMDC protocol and interviewer shortcut diagnostics: complete for
     available text controls.
   - MODMA task-transfer diagnostics: complete.
   - EATD valence sensitivity diagnostics: complete for audio eGeMAPS.
   - MPDD individual-difference shortcut and subgroup calibration diagnostics:
     complete, with gender/health blocked by missing structured metadata.
   - Dataset-identity probes over reusable frozen representations: complete.
3. Keep future GitHub updates on the clean remote/main lineage via
   `scripts/publish_clean_github_snapshot.py`; do not push the old local
   `main` history directly.
4. Use the Phase 5 full-method gate audit as the active claim boundary. MV09
   revises identity-gate semantics, MV10 provides an approximate PHQ
   partial-invariance screen, MV11 provides formal label-only graded-response
   confirmation with a BIC caveat, MV12 provides a completed but blocked
   two-stage latent-target result, and MV12 aggregate tradeoff analysis freezes
   the current latent-target line. Full method construction remains blocked.
   The paper direction is measurement shift / measurement invariance with
   bounded negative and diagnostic evidence. The Baselines, Failure-Mode
   Diagnostics, and Measurement Results scaffold is complete. The next active
   task is to predeclare MV13 external psychometric replication, followed by
   MV14 bootstrap uncertainty, MV15 latent-conditioned identity, and MV16
   cross-dataset theta calibration / few-shot scale linking; secondary work can
   strengthen E-DAIC MV06 agreement before stronger evidence-localization
   claims.
