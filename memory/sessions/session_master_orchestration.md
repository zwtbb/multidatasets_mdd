# Session Memory: 主对话 Master Orchestration

Status: active
Last updated: 2026-08-11 UTC
Thread/task: main agent (`019fcd77-cf81-7c11-a53e-f37e776d9e1d`)

## Scope

This session is the coordinating agent for the full experiment program. It
maintains the master memory, dispatches focused task sessions, watches
experiment progress, keeps version hygiene, and records cross-session decisions.

## Current State

- The user's pasted experiment plan has been read and aligned with the current
  repository state.
- `第零阶段` and `第1&2阶段` threads were inspected for context.
- Phase 2 was verified as complete for all applicable rows after MPDD OpenFace
  completion and P3HF conditional exclusion.
- Phase 2 artifact hygiene audit passed after cleaning PDCH public LLM factor
  artifacts so `model_name` records public Qwen IDs rather than local cache
  paths.
- The memory system has been converted from one long `MEMORY.md` into layered
  master/session memories.
- Phase 3 dataset/protocol identity probe completed in task
  `019fcd91-5fdb-73a1-bfa7-956e9387e82a`, was imported into the main checkout,
  and was re-run from `/root/autodl-tmp`. It completed seven grouped-CV probes
  with zero skipped probes, zero group-overlap violations, and artifact hygiene
  passing.
- Phase 3 E-DAIC/CMDC protocol controls completed in task
  `019fcd91-51ae-7c31-a52b-8f8749463102` and were imported into the main
  checkout as lightweight reports/tables plus script. The row-level
  `protocol_control_predictions.csv` is local-only and ignored by default.
- Phase 3 MODMA/EATD task-valence diagnostics were taken over by the main
  agent after the focused task left only partial MODMA cache state. The main
  checkout now owns the completed script, report, session memory, manifest/audit
  governance fix for the 5 invalid MODMA WAV rows, and lightweight summaries.
  Feature caches and row-level predictions are local-only and ignored by
  default.
- Phase 3 MPDD individual-difference diagnostics completed in task
  `019fcd91-5ab5-7553-af81-7f4cce5824f4` and were imported into the main
  checkout as script, session memory, report, figures, hygiene audit, and
  lightweight summaries. Large recomputable prediction/detail files remain
  local-only.
- Phase 3 Stop/Go synthesis is complete at
  `analysis/phase3_diagnostics/phase3_stop_go_synthesis.md`.
- Phase 4 symptom ontology and label contract are complete enough for method
  planning. The generated artifacts live under
  `analysis/phase4_symptom_ontology/` and include 15 constructs, 54 item-code
  mappings, a dataset label-contract audit, source references, and a six-row
  minimal validation matrix.
- Phase 5 minimal validation protocol is complete as a planning contract under
  `analysis/phase5_minimal_validation/`. It has eight protocol rows, required
  metrics, output policy, and a readiness audit with
  `full_method_allowed=false`.
- Phase 5 `P5_MV01 phq_core_construct_bridge` completed in task
  `019fcdeb-2287-73d1-9cc9-0ca1fe584c80` and was imported into the main
  checkout. It is a diagnostic baseline over frozen WavLM, not positive
  evidence for shared symptom representation, because E-DAIC/CMDC dataset
  identity balanced accuracy is `1.000`.
- Phase 5 `P5_MV04 dataset_protocol_control_ablation` completed in task
  `019fd008-b175-7b11-a7d5-790a063553a6` and was imported into the main
  checkout. Train-fold dataset centering reduced feature identity BA
  `1.000 -> 0.500` and prediction identity BA `0.961 -> 0.476`, while keeping
  dataset-stratified Macro Construct MAE within the 5 percent tolerance. Treat
  it as a diagnostic identity-control success, not an unknown-source inference
  contract.
- Phase 5 `P5_MV04b source_agnostic_identity_projection` completed in the main
  checkout. It uses train-fold dataset labels to learn projection directions,
  but no eval target labels and no eval dataset labels. Best tested projection
  reduced prediction identity BA `0.961 -> 0.777`, preserved main-task MAE
  within tolerance, but left feature identity BA high at `0.925`.
- Phase 5 `P5_MV04c protocol_task_valence_control` completed in the main
  checkout. It extends MV04 to MODMA task slices and EATD valence slices using
  local Phase 3 eGeMAPS caches. MODMA task nuisance projection passes
  diagnostically (`0.762 -> 0.570` feature task-identity BA, pooled Balanced
  Accuracy `0.688 -> 0.686`), but EATD is blocked because the raw SDS total
  head is far below train mean (`28.810` vs `7.201` MAE) and valence identity
  is not reduced. Treat overall status as `mixed_protocol_control`.
- Phase 5 `P5_MV03 sds_total_external_stress` completed in the main checkout.
  It used existing cached frozen WavLM/eGeMAPS audio features and EATD SDS total
  labels only. Best all-valence MAE was `7.341` from eGeMAPS SVR, worse than
  train mean `7.201`; no stronger healthy-negative shortcut than Phase 3 was
  observed. Treat as a runnable negative external stress result.
- Phase 5 `P5_MV03b eatd_text_semantic_stress` completed in the main checkout.
  It used manifest-governed EATD text, in-memory character TF-IDF Ridge heads,
  official train/validation subjects, five seeds, and no raw-text/vectorizer
  export. Best all-valence MAE was `7.20034` versus train mean `7.20089`, below
  the meaningful-improvement threshold. Treat as
  `blocked_no_meaningful_text_sds_generalization`.
- Phase 5 `P5_MV05 mpdd_context_calibration` completed in task
  `019fd02c-abba-7b51-b0ab-8625e646c388` and was imported into the main
  checkout. It used 175 labeled MPDD train subjects, cached WavLM audio and
  ResNet video subject features, AV-probability-first context calibrators, age
  and personality-bin controls, five-seed subject-level OOF, and no MPDD test
  labels. Treat as a runnable negative result:
  `blocked_no_context_calibration_gain`.
- Phase 5 `P5_MV02 hamd17_auxiliary_bridge` readiness audit completed in the
  main checkout. It corrected the CMDC HAMD item coverage overcount by
  filtering placeholder NaN payloads, confirmed CMDC has only 25/78 usable
  HAMD total+full-item subjects, confirmed PDCH has 99 usable HAMD subjects,
  and changed `P5_MV02` to `ready_pdch_only_mode`.
- Phase 5 `P5_MV02 hamd17_auxiliary_bridge` PDCH-only run completed in the
  main checkout. It used 99 PDCH HAMD-labeled subjects, frozen BGE/WavLM/eGeMAPS
  subject features, 5 seeds, 5-fold subject-level stratified CV, no encoder
  fine-tuning, and no raw text/media scan. Treat as
  `pass_pdch_only_diagnostic`: best PDCH item-derived total MAE was `5.693`
  versus train-mean items `6.183`, but CMDC 25-subject sanity did not support
  transfer.
- Phase 5 `P5_MV02b pdch_text_semantic_measurement` completed in the main
  checkout. It used 99 PDCH HAMD-labeled subjects, 165 manifest text segments,
  fixed character hashing Ridge heads, five seeds, subject-level 5-fold CV, no
  encoder fine-tuning, no saved vectorizers/features, and no raw text/source
  path export. Treat as `blocked_weak_pdch_text_measurement_signal`: best
  item-derived total MAE was `6.175` versus train-mean items `6.183`, below the
  meaningful-improvement threshold, and macro item MAE was effectively
  unchanged.
- Phase 5 `P5_MV06 construct_evidence_localization` readiness audit completed
  in the main checkout. It did not read raw text or export snippets/paths. It
  confirms local evidence annotation can proceed from MV01/MV02 predictions for
  E-DAIC dev, CMDC, and PDCH, with verbatim excerpts and per-subject rationales
  kept local-only.
- Phase 5 `P5_MV06 evidence_annotation_pilot` completed in the main checkout.
  It sampled a bounded local-only manual annotation packet from the ignored
  MV06 candidate queue: 144 candidate rows, 60 dataset-qualified subjects,
  144/144 rows with existing local text, and 12 explicit-evidence-only
  C09/HAMD03 rows. The local packet and local source locator map are ignored by
  Git; tracked artifacts contain only aggregate sampling, annotation-field
  policy, and hygiene results.
- Phase 5 `P5_MV06 evidence_annotation_summary_gate` completed in the main
  checkout. It validates the ignored local annotation packet and writes only
  aggregate completion, field-issue, evidence-field, prompt-artifact, and
  agreement summaries. Current status is `blocked_no_completed_annotations`
  because no local annotations have been filled yet. The gate passed artifact
  hygiene and a synthetic double-annotation readiness test.
- Phase 5 `P5_MV06 evidence_annotation_workbench` completed in the main
  checkout. It prepares a two-annotator ignored local workbook and ignored
  review index with local text locators, while tracked artifacts contain only
  schema, annotation rules, manifest, report, run summary, and hygiene audit.
  The summary gate now defaults to the workbench and remains
  `blocked_no_completed_annotations` until human annotation is filled.
- Phase 5 `P5_MV06 local_ai_preannotation_triage` completed in the main
  checkout. It reads raw clinical text locally through ignored workbench
  locators, fills an ignored local AI-triage preannotation workbook for 144
  candidates, and tracks only aggregate counts plus hygiene. It is
  `ready_for_human_review_not_claimable`: useful for speeding review, but not
  human annotation, agreement evidence, or an RQ4 claim.
- Phase 5 `P5_MV06 human_review_pack` completed in the main checkout. It joins
  the ignored human workbench and ignored AI preannotation into an ignored local
  review pack plus candidate index with deterministic priority ranks. Tracked
  outputs contain only aggregate review-pack, priority, progress, schema, and
  hygiene summaries. It is `ready_for_human_review_pack_not_claimable`: 144
  candidates, 288 annotation rows, 79 AI keyword-match candidates, 82
  priority-1/2 candidates. After importing the updated local human workbook,
  tracked progress aggregates show 143 completed candidates and 143
  double-annotated candidates.
- Phase 5 `P5_MV06 evidence_annotation_summary_gate` was updated to compute
  dataset-stratified kappa. It now reports
  `ready_for_aggregate_evidence_review`, with 143 completed candidates and 143
  double-annotated candidates over the 144-candidate local workbench. RQ4 is
  allowed only as limited aggregate first-round evidence; evidence-presence
  kappa is `0.965` overall, `0.967` for CMDC, `0.846` for E-DAIC, and `1.000`
  for PDCH.
- Phase 5 `P5_MV07 shared_feature_contract_readiness` completed in the main
  checkout. It did not train a model or scan raw text/media; it inventories
  cached subject-level features and label coverage. After local E-DAIC BGE
  generation, current status is `ready_to_run_minimal_validation`: E-DAIC,
  CMDC, and PDCH share 512 BGE model-input columns. This readies the next MV07
  validation row but does not yet prove a shared-symptom representation.
- Phase 5 `P5_MV07 E-DAIC BGE generation` completed in the main checkout. It
  created an ignored local 219-subject E-DAIC BGE cache under
  `analysis/phase2_baselines/edaic_text_bge/`; tracked artifacts contain only
  aggregate coverage, a local artifact manifest, report, run summary, and
  hygiene audit.
- Phase 5 `P5_MV07 aligned_bge_shared_symptom_validation` completed in the
  main checkout. It used aligned E-DAIC/CMDC/PDCH frozen BGE subject features,
  shallow train-mean/total-allocation/itemwise Ridge heads, subject-level
  splits, and feature/prediction identity probes. Treat it as
  `blocked_not_better_than_total_allocation_bge_contract`, not positive
  shared-symptom evidence: pooled PHQ itemwise heads do not consistently beat
  total-allocation floors and identity remains high (feature BA `1.000`,
  prediction BA `0.980`).
- Phase 5 full-method gate audit completed in the main checkout at
  `analysis/phase5_minimal_validation/full_method_gate_audit/`. It reads 34
  Phase 5 run summaries and turns them into claim-level decisions. Current
  status is `blocked_but_publishable_diagnostic_direction`,
  `full_method_allowed=false`, and `artifact_hygiene_passed=true`. Treat it as
  the authoritative Phase 5 claim boundary before any M0/M1/M2/M3 full-method
  construction.
- Phase 5 `P5_MV08 partial-invariance measurement` completed in the main
  checkout. It compares train-mean items, total-score floors, fixed construct
  maps, and partial-invariance ordinal heads over aligned frozen BGE features
  for E-DAIC PHQ-8, CMDC PHQ-9, and PDCH HAMD-17. Treat it as
  `blocked_not_better_than_total_score_floor`: M2 improves over total-score
  floor on `0/3` pooled active slices; worst pooled M2 deltas are `+0.152`
  macro item MAE versus total-score floor and `+0.140` versus fixed map;
  feature identity BA remains `1.000` and M2 prediction identity BA is `0.900`.
  Row-level predictions remain ignored local-only.
- Phase 5 `P5_MV08 error_analysis` completed in the main checkout. It reads
  the ignored MV08 row predictions locally and exports only aggregate
  diagnostics. Current status:
  `complete_current_mv08_not_claimable_revision_or_freeze`. It confirms the
  current MV08 contract is not positive RQ1 evidence; largest pooled item delta
  is CMDC PHQ9_8/C08 psychomotor (`+0.698` MAE versus total floor), and HAMD
  DIF heads show threshold sparsity (`0.318` constant-threshold fraction).
- Phase 5 `P5_MV08b total_anchored_residual_measurement_design` completed in
  the main checkout. It exports only design/aggregate artifacts and predeclares
  one mechanism-changing follow-up: total/latent severity anchoring first,
  sparse item residual modeling only after anchoring, pooled/collapsed
  threshold policy, and HAMD as a separate clinical stress test. Current status
  is `ready_to_implement_mv08b_total_anchored_residual_measurement`.
- Phase 5 `P5_MV08b total_anchored_residual_measurement` completed in the main
  checkout. It uses the same subject-level E-DAIC/CMDC/PDCH slices as MV08 and
  compares train-mean items, total-score floors, fixed construct-map floors,
  and total-anchored residual heads over aligned frozen BGE features. Treat it
  as negative/blocked RQ1 evidence:
  `blocked_prediction_identity_increased_vs_mv08`. M2b beats both total-score
  and fixed-map floors on 2/3 pooled active slices, but prediction identity BA
  rises to `0.979`, above the predeclared MV08 M2 gate `0.900`. Row/residual
  predictions remain ignored local-only.
- Phase 5 `P5_MV09 conditional_dataset_identity_audit` completed in the main
  checkout. It checks unconditional versus conditional BGE dataset identity for
  E-DAIC/CMDC/PDCH using severity, aligned PHQ items, and available covariates
  as diagnostic controls. Treat it as
  `complete_identity_gate_revision_needed`: unconditional identity is a
  shortcut-risk screen, but conditional identity remains high (`0.991`
  E-DAIC/CMDC PHQ-item residualized BA; `1.000` CMDC/PDCH and three-way
  severity-residualized BA). It motivated a label-only psychometric invariance
  baseline rather than another small BGE head iteration.
- Phase 5 `P5_MV10 classical_psychometric_invariance_baseline` completed in
  the main checkout. It is a label-only PHQ-8/PHQ-9 screen over E-DAIC and
  CMDC, not a multimodal model. It read no raw text/media, features, private
  review material, or row-level predictions, and artifact hygiene passed.
  Treat it as `complete_partial_invariance_supported_approx`: both datasets
  pass a one-factor/configural screen, loading congruence is `0.998`, `7/8`
  items pass the approximate metric-loading screen, `4/8` pass the approximate
  threshold/scalar screen, and candidate anchors are `C01`, `C04`, `C05`, and
  `C07`. It motivated MV11 formal label-only graded-response IRT confirmation.
- Phase 5 `P5_MV11 formal_ordinal_psychometric_confirmation` completed in the
  main checkout. It fits a label-only multi-group graded-response IRT
  confirmation over E-DAIC/CMDC PHQ C01-C08 labels and exports only aggregate
  fit, invariance, DIF, and anchor summaries. Treat it as
  `complete_formal_partial_invariance_supported_with_bic_caveat`: all four
  MV10 anchors are confirmed, no loading-DIF items are strongly flagged,
  threshold DIF is flagged for `C02` and `C06`, AIC prefers the MV10 partial
  core model, and BIC prefers scalar. This is formal label-only measurement
  evidence, not a multimodal method pass.
- Phase 5 `P5_MV12 two_stage_latent_target_design` completed in the main
  checkout. It is a design/predeclaration contract, not a model run. It reads
  only aggregate MV07/MV07b/MV07c/MV08b/MV09/MV10/MV11/full-gate artifacts and
  exports target-generation, local-only-boundary, model-ladder,
  identity/transfer, pass/fail, source-evidence, implementation-queue, method
  reference, report, run-summary, and hygiene artifacts. Treat it as
  `ready_to_implement_mv12_two_stage_latent_target`: primary anchors are
  `C01`, `C04`, `C05`, and `C07`; `C02` and `C06` are threshold-DIF-aware;
  `C03` and `C08` are sensitivity-only. Full method remains blocked until the
  actual `X_to_theta` run passes predictive utility, external transfer,
  conditional shared-latent identity, leakage, and artifact-hygiene gates.
- Phase 5 `P5_MV12 two_stage_latent_target` completed in the main checkout.
  It fits local-only label-derived PHQ theta targets, trains shallow BGE
  `X_to_theta` heads, compares direct/floor baselines, and exports only
  aggregate metric, identity, transfer, leakage, and hygiene summaries. Treat
  it as `blocked_theta_gain_not_observed_scale_safe`: same-dataset theta
  prediction improves over train mean on E-DAIC and CMDC, and conditional
  shared-latent identity BA is `0.602`, but observed-scale reconstruction is
  worse than direct itemwise Ridge and zero-shot source-calibrated external
  theta transfer fails.
- Phase 5 `P5_MV12 latent_target_tradeoff_analysis` completed in the main
  checkout. It reads aggregate MV09/MV12 summaries plus aggregate MV07-MV12
  accuracy-invariance tables, writes only aggregate tradeoff/failure-mode/gate
  outputs, and passes artifact hygiene. Treat it as
  `complete_freeze_current_mv12_latent_target_line`: freeze the current
  latent-target line with the dimension-matched B3 caveat. M12a is lower
  identity than upstream BGE features, but B3 direct itemwise Ridge compressed
  to theta has lower pooled observed macro MAE and lower conditional identity.
  Move to MV15 with dimension-matched controls, not another small shallow-head
  variant.
- Phase 5 `P5_MV13 external_psychometric_replication_design` and
  `P5_MV13 external_psychometric_replication` completed in the main checkout.
  R 4.1.2, lavaan 0.6.10, and archived R-compatible mirt 1.35.1 are installed
  and version-captured. External `mirt::multipleGroup` qualitatively
  replicates MV11: four MV10 anchors confirmed, zero loading-DIF flags,
  threshold DIF on `C02`/`C06`, AIC prefers the MV10 partial model, and BIC
  prefers scalar. Treat as
  `complete_external_mirt_with_convergence_warnings` because the configural
  core model did not converge within 3000 EM cycles.
- Phase 5 `P5_MV14 measurement_uncertainty_bootstrap_design` completed in the
  main checkout. It is a design/predeclaration contract, not a bootstrap run.
  It reads only aggregate MV10/MV11/MV13/full-gate artifacts and exports
  aggregate bootstrap-tier, local-only-boundary, stability-metric,
  pass/fail-gate, runtime-preflight, implementation-queue, report, run summary,
  and hygiene artifacts. Its design run summary records
  `ready_to_implement_mv14_measurement_uncertainty_bootstrap`, and it authorized
  the later MV14 run under aggregate-only boundaries.
- Phase 5 `P5_MV14 measurement_uncertainty_bootstrap` completed in the main
  checkout. It ran the predeclared smoke/core/DIF tiers with R=`10/200/100`;
  after the convergence-safe correction, full-ladder effective core R is
  `120/200` after `185/200` fit-success draws, configural converges in
  `120/200`, the stable metric/partial/scalar ladder has `197` effective
  draws, DIF effective R is `100`, artifact hygiene passed, stable anchors are
  `C01/C04/C05/C07`, threshold DIF remains concentrated on `C02/C06`, and
  AIC/BIC model selection remains split. Treat it as item-level
  measurement-shift evidence with global model-selection uncertainty, not a
  global partial-invariance pass; full method remains blocked.
- Phase 5 `P5_MV15 latent_conditioned_dataset_identity` completed in the main
  checkout after the prior design/predeclaration. It exports aggregate identity
  scores, conditioning-ladder results, output-identity controls, external
  severity-only sensitivities, pass/fail gates, report, run summary, and
  hygiene audit only. Its decision is
  `blocked_theta_conditioned_feature_identity_high`: raw/theta/total/
  predicted-total/B3-conditioned BGE feature identity BA remains `1.000`,
  PHQ-item-conditioned feature identity BA is `0.974`, theta-only identity BA
  is `0.576`, psychometric predicted-theta output identity BA is `0.646`, and
  B3 output Pareto-dominates predicted theta. Treat MV15 as negative
  feature-invariance evidence and move to MV16, not full-method construction.
- Diagnostic paper Baselines, Failure-Mode Diagnostics, and Measurement
  Results sections were drafted in the main checkout by
  `scripts/build_diagnostic_paper_results_sections.py`. The scaffold reads
  aggregate Phase 2/3/5 artifacts only, exports source maps, claim checklist,
  run summary, report, and hygiene audit under
  `analysis/diagnostic_measurement_audit_paper/`, and passes artifact hygiene.
  It reframes MV12 as a predictive fidelity-dataset identifiability trade-off:
  same-dataset theta utility improves and low-dimensional outputs are less
  dataset-identifiable than upstream BGE features, but B3 dimension-matched
  severity dominates M12a on pooled fidelity and identity, while same-dataset
  observed-scale safety and zero-shot source-calibrated theta transfer still
  block a positive full-method claim.
- A diagnostic measurement-audit paper outline now exists at
  `docs/diagnostic_measurement_audit_paper_outline.md`; it frames current
  evidence as a publishable measurement-shift / measurement-invariance
  contribution rather than a full method pass.
- Diagnostic paper claim/evidence tables now exist at
  `analysis/diagnostic_measurement_audit_paper/`, generated by
  `scripts/build_diagnostic_paper_claim_tables.py`. They provide compact
  allowed/blocked claim language, fifteen key numeric findings, and literature
  positioning from aggregate artifacts and web-checked primary sources.
- Diagnostic paper Data Governance and Label Contracts scaffold now exists at
  `analysis/diagnostic_measurement_audit_paper/`, generated by
  `scripts/build_diagnostic_paper_data_governance_section.py`. It uses only the
  registry, aggregate dataset audit, Phase 4 label-contract/construct-map
  outputs, and web-checked source context. It exports aggregate dataset
  governance, label-contract, construct-coverage, release-boundary, manuscript
  draft, report, run summary, and artifact-hygiene files.
- Clean GitHub publish workflow is now implemented. Future remote updates
  should use `scripts/publish_clean_github_snapshot.py` and
  `docs/github_publish_workflow.md`, so the old local `main` history is never
  pushed directly.
- A public dataset-governance risk was identified: real row-level manifests,
  file-integrity rows, and subject split maps with labels, local paths, or
  subject IDs should not remain in the public latest tree. The current
  mitigation is to keep real row-level dataset tables local-only, publish
  schema/synthetic examples, and require explicit approval before any remote
  history rewrite.

## Orchestration Rules

- Main agent owns `/root/autodl-tmp/MEMORY.md`.
- Focused sessions own their file under `/root/autodl-tmp/memory/sessions/`.
- Focused sessions may update the master only with final stable facts that
  affect other sessions.
- Main agent should avoid editing the same experiment files while an active
  focused thread is modifying them, unless taking over intentionally.
- New diagnostic sessions should be narrow and should write scripts/reports, not
  only chat summaries.
- Focused diagnostic sessions launched in Codex worktrees should write code,
  docs, session memory, and generated outputs in their own worktree. They may
  read raw data through the absolute registry paths, but should not write
  outputs into the canonical `/root/autodl-tmp` checkout.

## Near-Term Work Packages

1. Protocol diagnostics:
   E-DAIC/CMDC interviewer, participant, prompt-position, and question-order
   controls. Available text controls complete; literal speaker-resolved
   controls remain blocked by missing speaker/prompt labels.
2. MODMA task diagnostics:
   Within-task and cross-task train/eval matrix over interview, reading,
   picture, and affective tasks. Complete; strongest degradation signal is
   affective-task evaluation.
3. EATD valence diagnostics:
   Positive/neutral/negative prediction variance and trait-vs-valence checks.
   Complete for audio eGeMAPS; healthy negative material did not inflate
   depressed-probability estimates in this diagnostic.
4. MPDD individual-difference diagnostics:
   Personality-only, demographics-only, health-only, shuffled controls,
   subgroup performance, subgroup calibration, and counterfactual swaps.
   Complete for available age/personality/audio-video/gait context diagnostics;
   gender/health diagnostics are blocked by empty structured manifest fields.
5. Dataset-identity probe:
   Train lightweight probes over reusable frozen representations to measure
   dataset/protocol information retained in learned features. Complete; current
   evidence requires later pooled methods to control, penalize, stratify, or
   report dataset/protocol identity effects.
6. Symptom ontology:
   Complete enough for method planning. PHQ-8/PHQ-9 C01-C08 are the cleanest
   shared construct bridge; SDS is total-only in current EATD; CMDC HAMD is
   now audited as a limited 25-subject sanity subset, not a complete HAMD
   bridge.
7. Minimal validation:
   Protocol contract complete. `P5_MV01 phq_core_construct_bridge` is complete
   and weak/asymmetric. `P5_MV04 dataset_protocol_control_ablation` is complete
   as a known-dataset diagnostic identity-control success. Full method work
   stays blocked because `P5_MV04b` source-agnostic projection only partially
   reduces identity, `P5_MV04c` is mixed with MODMA positive but EATD blocked,
   `P5_MV03` and `P5_MV03b` do not show meaningful EATD SDS total
   generalization, and `P5_MV05` does not show MPDD subgroup calibration gain
   beyond AV-only recalibration. `P5_MV02` now gives a bounded PDCH-only
   diagnostic pass, but CMDC sanity is negative and coverage-limited;
   `P5_MV02b` shows the lightweight manifest-text hashing probe is weak. Full
   method work still needs a genuinely changed measurement contract. `P5_MV06`
   now has strengthened first-round aggregate human evidence and
   dataset-stratified agreement, including computable E-DAIC evidence-presence
   kappa.
   `P5_MV07` aligned-BGE shallow validation is now complete and blocked by
   total-allocation and identity evidence, so it should be reported as a
   negative/diagnostic shared-feature result rather than a shared-representation
   claim.
	   `P5_MV08` partial-invariance measurement is now complete and negative:
	   the lightweight ordinal measurement head does not beat the total-score floor
	   on any pooled active slice, despite reducing prediction identity only to
	   `0.900`. MV08 aggregate error analysis confirms this as a not-claimable
	   current contract. `P5_MV08b` is complete and blocked under the original
	   prediction-identity gate; `P5_MV09` then revises the identity-gate semantics
	   and shows conditional BGE identity remains high. `P5_MV10` adds an
	   approximate label-only PHQ common-structure screen with four candidate
	   anchors, `P5_MV11` formally confirms that map with a BIC caveat, and
	   `P5_MV12` completes the two-stage latent-target run but remains blocked
	   because observed-scale safety and zero-shot source-calibrated external
	   theta transfer fail. Its aggregate tradeoff analysis now freezes the
	   current latent-target line with a dimension-matched B3 caveat.
	   `P5_MV13` externally replicates the MV11 qualitative PHQ anchor/DIF
	   localization pattern with R `mirt`, while retaining a configural
	   convergence caveat. `P5_MV14` now completes the corrected convergence-safe
	   aggregate-only measurement-uncertainty bootstrap run and supports
	   item-level stable-anchor/localized-threshold-DIF wording with uncertain
	   global model selection. `P5_MV15` is complete and negative: feature
	   identity remains high after dimension-matched severity and theta
	   conditioning.
	   Freeze MV08/MV08b as negative RQ1 diagnostic evidence under the current
	   frozen-BGE shallow-measurement contract.
	   The full-method gate audit now records this as
	   `blocked_but_publishable_diagnostic_direction`: full method is blocked,
	   RQ4 is allowed only as limited aggregate evidence, and a bounded
	   measurement-shift / measurement-validity paper direction remains viable.
	   The Baselines, Failure-Mode Diagnostics, and Measurement Results scaffold
	   is now refreshed. The next active task is predeclaring MV16 DIF-guided
	   few-shot measurement calibration, with theta scores, fitted parameters,
	   row predictions, transformed features, projection directions, calibration
	   parameters, bootstrap samples, and model artifacts kept local-only.

## Version Management Watchlist

- Large artifacts must stay out of Git.
- GitHub should contain only the core reproducible experiment skeleton:
  maintained scripts, configs, governance docs, dataset schema/examples,
  aggregate summaries, and paper-critical experiment reports. Server-local
  stable utilities can remain server-only unless they become necessary for
  reproduction.
- Before any commit, check `.gitignore` and `git status --short`; stage only
  code, configs, docs, public manifest schemas/examples, aggregate audits,
  session memories, and small summaries for Phase 3+ diagnostics or method
  experiments.
- Do not stage raw datasets, real row-level manifests, real file-integrity
  rows, real subject split maps, model weights, caches, large feature arrays,
  audio, video, raw transcripts, raw prompts, raw model responses, or generated
  Phase 2 baseline result artifacts.
- Do not store or use plaintext GitHub passwords in files, commands, memory, or
  commits; authenticate remote operations through a token, SSH key, or
  `gh auth login`.
- Current tree tracks zero `analysis/phase2_baselines/` files, but local history
  still contains early Phase 2 artifact commits (`be8b52c` and deletion commit
  `997a7a5`). The first GitHub upload has been completed through a clean
  remote `main` root commit `a67cfdb`, created from a safe Git archive snapshot
  that excludes Phase 2 baseline result blobs, row-level predictions, model
  weights, embeddings, raw data, and plaintext credentials. Do not push the old
  local `main` history directly; continue future remote updates with
  `scripts/publish_clean_github_snapshot.py` or another verified clean publish
  path.
- GitHub CLI is authenticated for account `zwtbb` with token-based HTTPS Git
  operations. Never use plaintext passwords for remote operations or write them
  into files, memory, commands, or Git config.

## Issue Log

Cross-session issues are tracked in:

- `/root/autodl-tmp/docs/experiment_issue_log.md`

## Next Handoff

Continue Phase 5 under the full-method gate audit. MV08b has failed its
predeclared identity gate, MV09 revised identity-gate semantics, MV10 completed
an approximate label-only PHQ common-structure screen, and MV11 formally
confirmed the MV10 anchor map with a BIC caveat. MV12 completes the two-stage
latent-target run and remains blocked as positive method evidence; its
trade-off is paper-critical, but now carries the dimension-matched B3 caveat
and zero-shot source-calibrated external-transfer wording. The results-section
scaffold is refreshed. MV13 external R `mirt` replication now preserves the
MV11 qualitative anchor/DIF pattern with a configural convergence caveat. MV14
bootstrap uncertainty is corrected and complete: model selection/LRT are
convergence-safe, stable anchors and localized C02/C06 threshold DIF are the
claimable item-level finding, and global invariance-model selection remains
uncertain. MV15 latent-conditioned identity is now complete and negative:
feature identity stays high after dimension-matched severity and theta
conditioning, so next predeclare MV16 DIF-guided few-shot measurement
calibration.
Optionally add MV06 agreement uncertainty analysis and resolve the remaining
incomplete local candidate before stronger RQ4 wording. Keep
row-level predictions, real manifests, real integrity/split maps, latent
scores, learned parameters, learned embeddings, bootstrap samples, calibration
parameters, and model artifacts local-only, and do not start full method work
until the gate changes.

For future GitHub uploads, keep using the clean remote/main lineage; do not push
the old local `main` history directly. Run
`scripts/publish_clean_github_snapshot.py` first as a dry run, then with
`--push` only after reviewing the publish candidate.
