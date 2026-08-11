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
  E-DAIC dev, CMDC, and PDCH, with raw snippets and per-subject rationales kept
  local-only.
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
  priority-1/2 candidates. After importing the completed local human workbook,
  tracked progress aggregates show 30 completed candidates and 20
  double-annotated candidates.
- Phase 5 `P5_MV06 evidence_annotation_summary_gate` was updated to compute
  dataset-stratified kappa. It now reports
  `ready_for_aggregate_evidence_review`, with 30 completed candidates and 20
  double-annotated candidates. RQ4 is allowed only as limited aggregate
  first-round evidence; E-DAIC has only 2 double pairs and degenerate kappa
  marginals in this pass.
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
  `analysis/phase5_minimal_validation/full_method_gate_audit/`. It reads 25
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
  is `ready_to_implement_mv08b_total_anchored_residual_measurement`; full
  method remains blocked until the audited MV08b run passes.
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
   now has first-round aggregate human evidence and dataset-stratified
   agreement, but E-DAIC agreement is underpowered in this pass.
   `P5_MV07` aligned-BGE shallow validation is now complete and blocked by
   total-allocation and identity evidence, so it should be reported as a
   negative/diagnostic shared-feature result rather than a shared-representation
   claim.
   `P5_MV08` partial-invariance measurement is now complete and negative:
   the lightweight ordinal measurement head does not beat the total-score floor
   on any pooled active slice, despite reducing prediction identity only to
   `0.900`. MV08 aggregate error analysis confirms this as a not-claimable
   current contract. `P5_MV08b` is now predeclared as the one allowed
   total-anchored residual revision before freezing the sequence as negative
   diagnostic evidence.
   The full-method gate audit now records this as
   `blocked_but_publishable_diagnostic_direction`: full method is blocked,
   RQ4 is allowed only as limited aggregate evidence, and a bounded
   diagnostic/audit-driven paper direction remains viable.

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

Continue Phase 5 under the full-method gate audit. The next useful work is to
implement and run the predeclared `P5_MV08b` total-anchored residual
measurement row, then refresh the full-method gate. If MV08b fails, freeze
MV08/MV08b as diagnostic/negative evidence. Optionally expand E-DAIC MV06
double annotation. Keep row-level predictions,
real manifests, real integrity/split maps, latent scores, learned parameters,
and learned embeddings local-only, and do not start full method work until the
gate changes.

For future GitHub uploads, keep using the clean remote/main lineage; do not push
the old local `main` history directly. Run
`scripts/publish_clean_github_snapshot.py` first as a dry run, then with
`--push` only after reviewing the publish candidate.
