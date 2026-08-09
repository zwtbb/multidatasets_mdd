# MASTER MEMORY

Last updated: 2026-08-09 UTC

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
- Current next stage: continue minimal method-validation after the first
  runnable row. The minimal validation protocol is specified, and full-method
  work remains blocked until identity/protocol controls are stronger.
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
  at `/root/autodl-tmp/analysis/phase5_minimal_validation/`. It has six
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
- Phase 5 `P5_MV06 evidence_annotation_summary_gate` is complete at
  `/root/autodl-tmp/analysis/phase5_minimal_validation/p5_mv06_evidence_annotation_summary/`.
  It validates the ignored local annotation packet and exports only aggregate
  completion, field-issue, evidence-field, prompt-artifact, and agreement
  summaries. Current status is `blocked_no_completed_annotations`: 0 completed
  candidates and 0 double-annotated candidates. Artifact hygiene passes; no raw
  text, source locator map, or subject-level rows are exported.

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
  checkpoints, raw snippets, raw prompts, and raw model responses are
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
- P5_MV06 summary-gate decision: use
  `scripts/phase5_summarize_mv06_evidence_annotations.py` as the required
  aggregate-only export path after local annotation. Evidence reporting remains
  blocked until the gate has enough completed annotations, enough
  double-annotated candidates for agreement, no invalid field values, and
  `artifact_hygiene_passed=true`.

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

- Code, configs, docs, lightweight dataset manifests/audits, session memories,
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
  checkpoints, caches, local runtime files, raw clinical text, raw prompts, raw
  model responses, bulky prediction/embedding artifacts, or generated
  `analysis/phase2_baselines/` baseline result artifacts.
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
4. Next, complete local MV06 annotations and rerun the summary gate, or
   continue stronger inference-compatible identity/protocol controls. Full
   method construction remains blocked until stronger positive
   cross-dataset/control evidence is accumulated.
