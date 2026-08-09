# Master Experiment Plan

Last updated: 2026-08-09 UTC

## Principle

The project proceeds from measurement and diagnostics to modeling. Do not build
the full symptom-aligned method before Phase 3 has shown which shortcut,
protocol, valence, or population effects are real.

Canonical order, reaffirmed by the user on 2026-08-04:

```text
data audit
-> task and hypothesis freeze
-> unified baselines
-> failure-mode diagnostics
-> minimal method validation
-> full method
-> cross-dataset experiments
-> statistics and writing
```

## Completed

- Phase 0 data governance:
  registry, manifests, generated audits, subject-level leakage checks, and Git
  ignore policy are established.
- Phase 1 research frame:
  RQ1-RQ4 and dataset roles are frozen.
- Phase 2 unified baselines:
  all applicable rows are complete; P3HF is a documented conditional exclusion.
- Phase 3 dataset/protocol identity probe:
  complete. Seven grouped-CV probes finished with zero group-overlap
  violations and passed artifact hygiene. Dataset identity is highly
  recoverable from WavLM, wav2vec2, eGeMAPS, BGE text, and OpenFace feature
  spaces.
- Phase 3 E-DAIC/CMDC protocol controls:
  complete for available text controls. Speaker-resolved interviewer and
  participant controls are blocked by missing speaker labels, but E-DAIC
  position/repeated-turn proxy controls and CMDC question-position probes show
  protocol/task-content shortcut risk.
- Phase 3 MODMA/EATD task-valence diagnostics:
  complete. MODMA shows moderate cross-task degradation, strongest for
  affective-task evaluation. EATD audio eGeMAPS does not support the specific
  concern that negative material makes healthy subjects look more depressed.
- Phase 3 MPDD individual-difference diagnostics:
  complete. Personality-only diagnostics beat shuffled personality, generic
  audio-video-personality concatenation adds near-zero value over audio-video,
  subgroup calibration gaps are large enough to track, gait has modest
  psychomotor-context signal, and gender/health diagnostics are blocked by
  empty structured manifest fields.
- Phase 3 Stop/Go synthesis:
  complete; see
  `analysis/phase3_diagnostics/phase3_stop_go_synthesis.md`.
- Phase 4 symptom ontology and label contract:
  complete enough for method planning. It defines 15 constructs, 54 short
  item-code mappings, dataset label-contract coverage, and six minimal
  validation rows. See
  `analysis/phase4_symptom_ontology/phase4_symptom_ontology_report.md`.
- Phase 5 minimal method-validation protocol:
  complete as a planning contract, not as model results. It defines seven
  protocol rows, required metrics, output policy, and `full_method_allowed=false`.
  See `analysis/phase5_minimal_validation/minimal_validation_protocol.md`.
- Phase 5 `P5_MV01 phq_core_construct_bridge`:
  complete as the first runnable minimal-validation row. It used frozen WavLM
  subject features and shallow heads for E-DAIC PHQ-8 / CMDC PHQ-9 C01-C08.
  The result is weak and asymmetric, and dataset identity remains perfectly
  recoverable from frozen WavLM, so it does not support a shared symptom
  representation claim by itself.
- Phase 5 `P5_MV04 dataset_protocol_control_ablation`:
  complete as the first runnable identity-control validation. Train-fold
  dataset centering reduced E-DAIC/CMDC feature identity balanced accuracy from
  `1.000` to `0.500` and prediction identity from `0.961` to `0.476`, with
  dataset-stratified Macro Construct MAE preserved within the 5 percent
  tolerance. This is a successful diagnostic control, not a final
  unknown-source inference contract.
- Phase 5 `P5_MV04b source_agnostic_identity_projection`:
  complete as an inference-compatible follow-up. The best projection reduced
  prediction identity from `0.961` to `0.777` without using eval dataset labels,
  but feature identity remained high (`1.000` to `0.925`). This is a partial
  diagnostic success, not enough for a dataset-invariant representation claim.
- Phase 5 `P5_MV04c protocol_task_valence_control`:
  complete as a MODMA/EATD protocol-slice extension. MODMA task nuisance
  projection passes diagnostically, reducing feature task identity from `0.762`
  to `0.570` while preserving pooled Balanced Accuracy (`0.688` to `0.686`).
  EATD valence control is blocked because the SDS total Ridge head stays far
  below train mean (`28.810` versus `7.201` MAE) and valence identity is not
  reduced.
- Phase 5 `P5_MV03 sds_total_external_stress`:
  complete as an EATD SDS total/severity-only external stress row. Current
  cached frozen audio features did not beat the train-mean SDS total floor:
  best MAE `7.341` versus train mean `7.201`. No stronger healthy-negative
  shortcut than Phase 3 was observed. This is a runnable negative result, not
  positive cross-scale SDS evidence.
- Phase 5 `P5_MV03b eatd_text_semantic_stress`:
  complete and weak/negative. Character TF-IDF text heads improve EATD
  validation MAE over train mean by only `0.00056`, below the meaningful
  threshold.
- Phase 5 `P5_MV02 hamd17_auxiliary_bridge`:
  complete as a bounded PDCH-only diagnostic pass. Best PDCH item-derived total
  MAE was `5.693` versus train-mean items `6.183`, but CMDC 25-subject HAMD
  sanity remains negative and coverage-limited.
- Phase 5 `P5_MV02b pdch_text_semantic_measurement`:
  complete and weak/negative. Fixed character hashing over manifest text
  improves item-derived total MAE by only `0.008` versus train-mean items.
- Phase 5 `P5_MV05 mpdd_context_calibration`:
  complete and negative. The proposed context calibrator does not improve the
  required age/personality subgroup calibration gaps beyond AV-only
  recalibration.
- Phase 5 `P5_MV06 construct_evidence_localization`:
  readiness, pilot packet, local two-annotator workbench, and aggregate summary
  gate are complete, but evidence reporting is blocked because no local
  annotations or double-annotation agreement have been completed.
- Phase 5 `P5_MV06 local_ai_preannotation_triage`:
  complete as a local-only review accelerator. It generated ignored AI-triage
  rows for 144 MV06 candidates and tracked only aggregate counts plus hygiene.
  This does not count as human annotation or agreement evidence.
- Phase 5 `P5_MV07 shared_feature_contract_readiness`:
  complete as a no-training readiness audit. After local E-DAIC BGE
  generation, E-DAIC, CMDC, and PDCH share 512 BGE model-input columns and the
  aligned-BGE MV07 validation row became runnable. This is readiness, not model
  evidence.
- Phase 5 `P5_MV07 E-DAIC BGE feature generation`:
  complete as a local-only feature-contract preparation step. It generated an
  ignored 219-subject E-DAIC BGE cache and tracked only aggregate audit
  artifacts.
- Phase 5 `P5_MV07 aligned_bge_shared_symptom_validation`:
  complete and blocked as positive shared-symptom evidence. It used aligned
  E-DAIC/CMDC/PDCH frozen BGE subject features and shallow heads only. Pooled
  PHQ itemwise Ridge improves over train mean but does not consistently beat
  the total-allocation floor, PDCH HAMD-proxy sanity is internal only, and
  identity probes remain high: feature balanced accuracy `1.000`, prediction
  balanced accuracy `0.980`.
- Phase 5 `P5_MV07b bge_identity_projection`:
  complete as an inference-compatible BGE identity-control follow-up. Best k=10
  projection reduces E-DAIC/CMDC feature identity BA `1.000 -> 0.709`,
  prediction identity BA `0.994 -> 0.684`, and three-way E-DAIC/CMDC/PDCH
  feature identity BA `1.000 -> 0.687`. It preserves Macro MAE within 5
  percent and beats train mean on both E-DAIC and CMDC, but remains worse than
  the total-allocation floor on CMDC by `0.018` Macro MAE. Treat as partial
  diagnostic evidence, not a shared-representation pass.
- Phase 5 full-method gate audit:
  complete. It reads 19 Phase 5 run summaries and writes claim gates, evidence
  inventory, a next-action queue, a report, and an artifact-hygiene audit under
  `analysis/phase5_minimal_validation/full_method_gate_audit/`. Current status
  is `blocked_but_publishable_diagnostic_direction`,
  `full_method_allowed=false`, and `artifact_hygiene_passed=true`.

## Current Method-Design Gate

Phase 2, planned Phase 3 diagnostics, Phase 4 ontology, Phase 5 protocol, and
the first Phase 5 identity-control follow-ups are complete. Full method
construction remains blocked because `P5_MV01` exposed weak/asymmetric bridge
evidence, `P5_MV04` only validates a known-dataset diagnostic control, and
`P5_MV04b` leaves feature-level dataset identity high. `P5_MV04c` adds a useful
MODMA task-control pass, but the result is still mixed because EATD remains
below train mean and does not support valence-control claims. `P5_MV02` gives
bounded PDCH-only HAMD evidence, while `P5_MV03`, `P5_MV03b`, and `P5_MV05`
are negative for SDS/context claims. `P5_MV06` still requires local annotation
completion before evidence-localization claims; AI preannotation is available
only as a local review aid. `P5_MV07` shows aligned BGE is runnable, but the
shallow validation is blocked by total-allocation and identity evidence.
`P5_MV07b` reduces BGE feature/prediction identity, but the best
identity-controlled variant still fails the CMDC total-allocation floor.

Use `scripts/phase5_full_method_gate_audit.py` as the active claim boundary.
The audit blocks full M0/M1/M2/M3 construction, transferable shared-symptom
claims, positive EATD SDS claims, EATD-driven valence-adversarial design, RQ3
context-conditioning claims, and RQ4 evidence-localization claims before
annotation. It allows only bounded diagnostic claims and a reframed
diagnostic/audit-driven paper direction.

Phase 2 validation commands:

Run:

```bash
python scripts/phase2_baseline_matrix.py --strict
python scripts/phase2_export_final_table.py
python scripts/phase2_completion_audit.py
```

Expected status:

- `phase2_goal_complete=true`
- `method_design_gate_recommendation=ready`
- completed runs `66/67`
- not-applicable runs `1`
- blocked runs `0`

## Phase 3 Diagnostics

Run these before method design:

1. E-DAIC/CMDC protocol controls:
   participant-only, interviewer-only, full dialogue, fixed-question removal,
   position slices, question shuffle, and paraphrase/replacement when possible.
   Available text controls are complete; speaker-resolved controls remain
   blocked by missing speaker/prompt labels.
2. MODMA task transfer:
   within-task and cross-task matrix over interview, reading, picture
   description, and affective tasks. Complete; see
   `analysis/phase3_diagnostics/task_valence/phase3_task_valence_report.md`.
3. EATD valence sensitivity:
   positive/neutral/negative prediction variance per subject and checks that
   negative material does not masquerade as depression trait. Complete for
   audio eGeMAPS; see
   `analysis/phase3_diagnostics/task_valence/phase3_task_valence_report.md`.
4. MPDD shortcut and moderation probes:
   personality-only, demographics-only, health-only, shuffled/counterfactual
   controls, subgroup performance, and subgroup calibration. Complete for
   available age/personality/audio-video/gait context diagnostics; gender and
   health diagnostics are blocked by missing structured manifest fields. See
   `analysis/phase3_diagnostics/mpdd_individual_differences/mpdd_individual_differences_report.md`.
5. Dataset-identity probe:
   lightweight classifier predicting dataset/protocol from frozen
   representations. Complete; see
   `analysis/phase3_diagnostics/dataset_identity_probe/dataset_identity_probe_report.md`.

## Stop/Go Criteria

Protocol robustness becomes a method component only if at least one diagnostic
shows meaningful protocol/task/valence dependence.

The dataset/protocol identity probe already satisfies this gate for the pooled
representation setting: dataset identity is near-perfectly recoverable from
multiple feature families. Direct pooled training is therefore not acceptable as
standalone evidence for shared symptom representation.

The E-DAIC/CMDC protocol controls also satisfy the protocol robustness gate for
available text controls: E-DAIC fixed-turn/position proxies and CMDC
question-position probes show meaningful protocol/task-content dependence.

The MODMA/EATD task-valence diagnostics add nuance rather than a blanket rule:
MODMA affective-task transfer degradation supports task-stratified reporting or
task-robust validation, while EATD eGeMAPS valence confusion is weak/negative
evidence and should not by itself justify a valence-adversarial component.

MPDD diagnostics support personality shortcut/moderation and subgroup
calibration audits, but not naive audio-video-personality concatenation as the
default method. Treat age as a subgroup/calibration axis and gait as
psychomotor context validation; keep gender/health explicitly blocked unless
structured metadata is supplied.

Overall Phase 3 decision: proceed to symptom ontology and minimal
method-validation design with explicit dataset/protocol/task/subgroup controls;
do not proceed directly to a full method or claim pooled shared symptom
representation without those controls.

## Phase 4 Ontology Decisions

- PHQ-8 and PHQ-9 share eight direct symptom constructs (C01-C08), making them
  the cleanest shared construct bridge.
- PHQ-9, HAMD-17, and SDS include death/self-harm related items, but PHQ-8
  omits that item. Treat C09 as safety-sensitive and explicit-evidence-only.
- HAMD-17 bridges many core constructs but also includes anxiety, somatic,
  functioning, and insight items that should stay auxiliary or scale-specific
  when the mapping is not direct.
- SDS is theoretically mappable but the current EATD manifest exposes only SDS
  total/severity, so EATD cannot provide SDS item-level construct supervision
  unless item labels are recovered.
- MODMA and MPDD currently provide PHQ-9 total/severity but not PHQ-9 item
  fields, so they are not item-level construct-supervision datasets in the
  current project state.

## Phase 5 Protocol Decisions

- Recommended first runnable row is `P5_MV01 phq_core_construct_bridge`,
  because E-DAIC PHQ-8 and CMDC PHQ-9 provide the cleanest item-level C01-C08
  construct bridge. This row is now complete and should be treated as a
  diagnostic baseline, not a positive shared-representation result.
- First identity-control row `P5_MV04 dataset_protocol_control_ablation` is
  complete for E-DAIC/CMDC frozen WavLM. Treat train-fold dataset centering as a
  successful diagnostic ablation that still needs inference-compatible or
  protocol/task-slice extensions.
- Source-agnostic P5_MV04b projection is complete. It reduces prediction
  identity without eval dataset labels, but residual feature identity remains
  too high for pooled shared-representation claims.
- P5_MV04c protocol/task/valence projection is complete and mixed. MODMA
  supports inference-compatible task nuisance control, but EATD remains a
  negative stress result and should not drive a valence-adversarial component
  under the current feature contract.
- `P5_MV03 sds_total_external_stress` is complete and negative for current
  frozen audio features: EATD SDS total heads did not beat train mean. EATD
  remains total/severity-only and cannot support SDS item-level construct
  claims.
- `P5_MV02 hamd17_auxiliary_bridge` is complete in PDCH-only mode. Treat it as
  bounded PDCH evidence, not cross-dataset HAMD generalization.
- `P5_MV06 construct_evidence_localization` has local annotation infrastructure
  ready, including an ignored two-annotator local workbook, but is blocked as
  evidence until annotations and agreement summaries are completed.
- `P5_MV06 local_ai_preannotation_triage` is complete as a local-only review
  accelerator. It must not be treated as human annotation, agreement evidence,
  or an RQ4 claim.
- `P5_MV07 shared_feature_contract_readiness` is complete and enabled the
  aligned-BGE shallow validation row. The E-DAIC BGE feature CSV is local-only.
- `P5_MV07 aligned_bge_shared_symptom_validation` is complete and blocked as
  shared-symptom evidence. The BGE itemwise heads do not consistently beat the
  total-allocation floor and feature/prediction identity remains high.
- `P5_MV07b bge_identity_projection` is complete and partial: identity is
  reduced, but the best identity-controlled variant still fails the CMDC
  total-allocation floor.
- The full-method gate audit is the required synthesis step before full method
  construction. Current gate status is
  `blocked_but_publishable_diagnostic_direction`, not a go signal for M0.
- Pooled or cross-dataset claims require dataset-stratified metrics and
  dataset/protocol identity probes.
- Protocol/task/subgroup metrics are mandatory before interpreting pooled
  gains.
- Row-level predictions, learned embeddings, checkpoints, raw snippets, raw
  prompts, and raw model responses stay local-only unless separately reviewed.

## Later Phases

- Phase 5 execution: continue under the full-method gate by filling the
  ignored local MV06 human annotation workbook using the AI preannotation as a
  review aid, then rerunning the summary gate; or resolve the MV07b
  identity-controlled BGE floor gap.
- Phase 6: protocol consistency/adversarial components only if Phase 3 supports
  them.
- Phase 7: individual-difference and gait-to-psychomotor constraints only if
  MPDD diagnostics support them.
- Phase 8+: cross-dataset transfer, leave-one-dataset-out, few-shot adaptation,
  statistical testing, error analysis, and paper writing.
