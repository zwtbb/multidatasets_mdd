# Master Experiment Plan

Last updated: 2026-08-21 UTC

## Principle

The project proceeds from measurement and diagnostics to modeling. Do not build
the full symptom-aligned method before Phase 3 has shown which shortcut,
protocol, valence, or population effects are real.

Post-review correction: the main publishable route is now target measurement
validity, not a generic robust multimodal model. Treat representation/protocol
shift, target measurement shift, and prediction shift as separate layers.
Feature alignment alone cannot solve cross-dataset depression detection if the
observed label response function also shifts by dataset/group.

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
  complete as a planning contract, not as model results. It defines eight
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
  readiness, pilot packet, local two-annotator workbench, human review pack,
  and aggregate summary gate are complete. The updated human annotation import
  now reaches the aggregate gate with 143 completed and 143 double-annotated
  candidates over the 144-candidate local workbench. Evidence-presence kappa is
  `0.965` overall, `0.967` for CMDC, `0.846` for E-DAIC, and `1.000` for PDCH;
  bootstrap 95 percent kappa CIs are `0.922-1.000` overall, `0.885-1.000` for
  CMDC, `0.595-1.000` for E-DAIC, and `1.000-1.000` for PDCH. Evidence
  reporting is allowed only as aggregate, first-round, dataset-stratified
  credibility evidence.
- Phase 5 `P5_MV06 local_ai_preannotation_triage`:
  complete as a local-only review accelerator. It generated ignored AI-triage
  rows for 144 MV06 candidates and tracked only aggregate counts plus hygiene.
  This does not count as human annotation or agreement evidence.
- Phase 5 `P5_MV06 human_review_pack`:
  complete as a local-only human review accelerator. It joins the ignored human
  workbench and ignored AI preannotation into an ignored review pack plus
  candidate index with priority ranks. Tracked outputs contain only aggregate
  review-pack, priority, progress, schema, and hygiene summaries. Current
  status is `ready_for_human_review_pack_not_claimable`: 144 candidates, 288
  annotation rows, 79 AI keyword-match candidates, 82 priority-1/2 candidates;
  after importing human annotations it reflects 143 completed candidates and 143
  double-annotated candidates in the source workbook.
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
- Phase 5 `P5_MV07c bge_total_anchor`:
  complete and blocked. It tested whether identity-projected BGE itemwise heads
  add value after train-fold-selected total anchoring. Prediction identity BA
  drops to `0.664`, but CMDC remains worse than raw total allocation by `0.012`
  Macro MAE and worse than projected total allocation by `0.002`. Treat this
  as a negative follow-up: total anchoring does not rescue the shallow BGE
  shared-symptom row.
- Phase 5 full-method gate audit:
  complete. It reads 39 Phase 5 run summaries and writes claim gates, evidence
  inventory, a next-action queue, a report, and an artifact-hygiene audit under
  `analysis/phase5_minimal_validation/full_method_gate_audit/`. Current status
  is `blocked_but_publishable_diagnostic_direction`,
  `full_method_allowed=false`, and `artifact_hygiene_passed=true`.
- Phase 5 `P5_MV08 partial_invariance_measurement`:
  complete and blocked as positive RQ1 evidence. It compares train-mean items,
  total-score floors, fixed construct-map heads, and partial-invariance ordinal
  heads over aligned frozen BGE features for E-DAIC PHQ-8, CMDC PHQ-9, and PDCH
  HAMD-17. M2 improves over the total-score floor on `0/3` pooled active slices;
  worst pooled deltas are `+0.152` macro item MAE versus total-score floor and
  `+0.140` versus fixed map. Feature identity BA remains `1.000`, and M2
  prediction identity BA is `0.900`. Treat this as negative measurement-model
  evidence, not a full-method authorization.
- Phase 5 `P5_MV08 error_analysis`:
  complete as an aggregate-only analysis of the negative MV08 result. It reads
  the ignored local row-prediction file but exports only slice/item/construct,
  error-bin, threshold-sparsity, and revision-queue summaries. It confirms the
  current MV08 contract is not claimable positive RQ1 evidence: pooled M2 is
  worse than total-score and fixed-map floors on all active slices, the largest
  pooled item delta is CMDC PHQ9_8/C08 psychomotor (`+0.698` MAE versus total
  floor), and HAMD DIF heads show threshold sparsity (`0.318` constant-threshold
  fraction).
- Phase 5 `P5_MV08b total_anchored_residual_measurement_design`:
  complete as a no-training predeclared mechanism revision. It turns the MV08
  failure into one allowed follow-up: predict total/latent severity first,
  model item residuals only after anchoring, pool or collapse sparse ordinal
  thresholds, and keep HAMD as a separate clinical measurement stress test.
  Current status is
  `ready_to_implement_mv08b_total_anchored_residual_measurement`.
- Phase 5 `P5_MV08b total_anchored_residual_measurement`:
  complete and blocked as positive RQ1 evidence. M2b beats both total-score and
  fixed-map floors on E-DAIC and PDCH pooled slices, but misses CMDC versus the
  total-score floor and fails the predeclared prediction-identity gate
  (`0.979` versus MV08 M2 gate `0.900`). Treat it as negative diagnostic
  evidence, not a shared-measurement pass.
- Phase 5 `P5_MV09 conditional_dataset_identity_audit`:
  complete. It revises identity-gate semantics: unconditional identity is a
  shortcut-risk screen, while future shared-latent claims must also report
  identity after conditioning on severity, aligned items, and legitimate
  covariates where available. Current BGE identity remains high after
  conditioning.
- Phase 5 `P5_MV10 classical_psychometric_invariance_baseline`:
  complete. It is a label-only E-DAIC/CMDC PHQ screen with loading congruence
  `0.998`, `7/8` metric-loading items, `4/8` threshold/scalar items, and
  candidate anchors `C01`, `C04`, `C05`, and `C07`.
- Phase 5 `P5_MV11 formal_ordinal_psychometric_confirmation`:
  complete. It formally confirms all four MV10 anchors, flags no loading-DIF
  items, flags threshold DIF for `C02` and `C06`, and preserves the AIC partial
  versus BIC scalar caveat.
- Phase 5 `P5_MV12 two_stage_latent_target` and aggregate tradeoff analysis:
  complete and blocked as positive method evidence. Same-dataset theta utility
  and conditional identity improve, but observed-scale safety and external
  theta transfer fail. The current latent-target line is frozen as bounded
  diagnostic evidence.
- Phase 5 `P5_MV13 external_psychometric_replication`:
  complete with convergence warnings. External R `mirt::multipleGroup`
  qualitatively replicates MV11: four anchors confirmed, zero loading-DIF
  flags, threshold DIF on `C02`/`C06`, AIC partial versus BIC scalar split, and
  a retained configural convergence caveat.
- Phase 5 `P5_MV14 measurement_uncertainty_bootstrap_design`:
  complete as a predeclaration, not a run. It fixes smoke/core/DIF/optional
  bootstrap tiers, aggregate stability metrics, local-only boundaries, and
  pass/downgrade gates for anchor, DIF, model-selection, convergence, item-fit,
  and SE/CI-availability uncertainty. Its design run summary records
  `ready_to_implement_mv14_measurement_uncertainty_bootstrap`; the later MV14
  run has now consumed that contract.
- Phase 5 `P5_MV14 measurement_uncertainty_bootstrap`:
  complete with aggregate-only outputs and local item-response inputs ignored.
  It ran smoke/core/DIF R=`10/200/100` after the convergence-safe correction:
  full-ladder effective core R is `120/200` after `185/200` fit-success draws,
  configural converges in `120/200`, the stable metric/partial/scalar ladder
  has `197` effective draws, the DIF tier has minimum anchor-support effective
  R `77/100`, and threshold-DIF comparisons are `100/100` effective. All four MV10
  anchors are stable (`C01`, `C04`, `C05`, `C07`), loading DIF is sparse, and
  threshold-DIF frequencies remain top-ranked for `C02` and `C06`. Full-ladder
  AIC/BIC prefer `configural`/`scalar`, while the stable ladder prefers
  `partial_mv10`/`scalar`. Treat as item-level measurement-shift evidence with
  global model-selection uncertainty, not a bootstrap-confirmed global
  partial-invariance pass.
- Phase 5 `P5_MV15 latent_conditioned_dataset_identity_design`:
  complete as a predeclaration, not a probe run. It exports aggregate contracts
  only, with 10 conditioning ladder rows, 7 identity-probe rows, and 8
  pass/fail gates. The design requires raw, total, predicted-total, observed
  item, B3 itemwise-theta, psychometric-theta, covariate, predicted-output, and
  severity-only controls and has now been consumed by the MV15 runner.
- Phase 5 `P5_MV15 latent_conditioned_dataset_identity`:
  complete and blocked as feature-invariance evidence. It used subject-level
  folds, aligned BGE features, fold-local PHQ theta generation, total,
  predicted-total, observed-item, B3 itemwise-theta, psychometric-theta,
  covariate, predicted-output, and severity-only sensitivity controls. Raw,
  theta-conditioned, total-conditioned, predicted-total-conditioned, and
  B3-conditioned BGE feature identity BA are all `1.000`; PHQ-item-conditioned
  feature identity BA is `0.974`; theta-only identity BA is `0.576`; and
  predicted-theta output identity BA is `0.646`. Treat this as negative
  diagnostic evidence: low-dimensional output identity is not upstream feature
  invariance.
- Diagnostic measurement-audit paper outline:
  initialized at `docs/diagnostic_measurement_audit_paper_outline.md`. It
  freezes allowed versus blocked claim boundaries and proposes the paper
  structure around governance, diagnostics, bounded method evidence, and
  evidence localization.

## Current Method-Design Gate

Phase 2, planned Phase 3 diagnostics, Phase 4 ontology, Phase 5 protocol, and
the first Phase 5 identity-control follow-ups are complete. Full method
construction remains blocked because `P5_MV01` exposed weak/asymmetric bridge
evidence, `P5_MV04` only validates a known-dataset diagnostic control, and
`P5_MV04b` leaves feature-level dataset identity high. `P5_MV04c` adds a useful
MODMA task-control pass, but the result is still mixed because EATD remains
below train mean and does not support valence-control claims. `P5_MV02` gives
bounded PDCH-only HAMD evidence, while `P5_MV03`, `P5_MV03b`, and `P5_MV05`
are negative for SDS/context claims. `P5_MV06` now provides first-round
aggregate evidence-localization credibility evidence with dataset-stratified
agreement, including computable E-DAIC evidence-presence agreement. `P5_MV07`
shows aligned BGE is runnable, but the shallow validation is blocked by
total-allocation and identity evidence.
`P5_MV07b` reduces BGE feature/prediction identity, but the best
identity-controlled variant still fails the CMDC total-allocation floor.
`P5_MV07c` confirms that train-fold-selected total anchoring also fails the
CMDC total-allocation floor. `P5_MV08` changes the measurement contract but its
first lightweight partial-invariance ordinal pilot also fails the total-score
floor on all pooled active slices. MV08 error analysis confirms systematic
overprediction, shared-PHQ anchor fragility, and HAMD threshold sparsity. MV08b
partially improves item MAE but fails the prediction-identity gate.
Further small shallow BGE-head variants should be avoided.

Use `scripts/phase5_full_method_gate_audit.py` as the active claim boundary.
The audit blocks full M0/M1/M2/M3 construction, transferable direct
shared-symptom claims, positive EATD SDS claims, EATD-driven
valence-adversarial design, and positive RQ3 context-conditioning claims. It
now allows RQ4 only as limited first-round aggregate evidence. The next method
target is not another shallow BGE head. MV08/MV08b are both negative or blocked
under the current frozen-BGE shallow contract. MV09-MV19 move the project into
a label-measurement and measurement-shift frame: MV10/MV11/MV13 support
bounded common-structure and anchor/DIF evidence, MV14 adds convergence-safe
bootstrap stability for item-level anchors and localized threshold DIF while
leaving global model selection uncertain, MV19 downgrades C02/C06 to repeated
but finite-sample-bounded dataset-group threshold-shift evidence at the
observed N, MV12 shows a useful but blocked
theta-prediction trade-off with a dimension-matched B3 caveat, and MV15 now
blocks theta-specific BGE feature-invariance wording under dimension-matched
controls. MV16 now completes the DIF-guided few-shot measurement-calibration
ladder with C01/C04/C05/C07 anchors and C02/C06 threshold calibration, but it
fails the both-direction small-k mechanism gate and remains bounded/negative
calibration evidence. Full method work remains blocked.

## Updated Method Target

Phase 5 negative and partial results changed the RQ1 target. Directly mapping
PHQ/HAMD/SDS labels into one fixed shared symptom space is now treated as a
too-strong hypothesis under the current evidence. The next candidate method
should model:

```text
shared latent symptom constructs
+ scale-specific DIF/loading-threshold deviations
+ protocol nuisance reporting/control
```

The first runnable row has now compared:

1. total-score or total-allocation heads;
2. fixed construct-map heads;
3. partial-invariance ordinal latent measurement heads.

The E-DAIC PHQ-8, CMDC PHQ-9, and PDCH HAMD-17 MV08 pilot did not beat the
total-score floor. MV08b then tested the predeclared mechanism-changing
follow-up: first anchor severity, then test whether sparse item residuals add
construct information beyond total-score and fixed-map floors. It improved on
two pooled active slices but failed prediction identity, so the RQ1 modeling
sequence is frozen as diagnostic/negative evidence for the current feature
contract. Keep MPDD as a later measurement-heterogeneity moderator dataset and
keep EATD/MODMA as stress tests rather than primary training sources.

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
- `P5_MV06 construct_evidence_localization` has first-round aggregate human
  annotation evidence ready. `agreement_summary.csv` is dataset-stratified and
  includes an `ALL` diagnostic row; evidence-presence kappa is `0.965`
  overall, `0.967` for CMDC, `0.846` for E-DAIC, and `1.000` for PDCH.
- `P5_MV06 local_ai_preannotation_triage` is complete as a local-only review
  accelerator. It must not be treated as human annotation, agreement evidence,
  or an RQ4 claim.
- `P5_MV06 human_review_pack` is complete as a local-only review accelerator.
  It should be used to prioritize and fill the ignored human workbook, but it
  must not be treated as human annotation, agreement evidence, or an RQ4 claim.
- `P5_MV07 shared_feature_contract_readiness` is complete and enabled the
  aligned-BGE shallow validation row. The E-DAIC BGE feature CSV is local-only.
- `P5_MV07 aligned_bge_shared_symptom_validation` is complete and blocked as
  shared-symptom evidence. The BGE itemwise heads do not consistently beat the
  total-allocation floor and feature/prediction identity remains high.
- `P5_MV07b bge_identity_projection` is complete and partial: identity is
  reduced, but the best identity-controlled variant still fails the CMDC
  total-allocation floor.
- `P5_MV07c bge_total_anchor` is complete and blocked: total anchoring further
  reduces prediction identity but still does not beat the CMDC total-allocation
  floor.
- `P5_MV08 partial_invariance_measurement_design` is complete as a no-training
  design/readiness audit. It establishes the next RQ1 row: compare total-score
  floors, fixed construct-map heads, and partial-invariance ordinal latent
  measurement heads on E-DAIC PHQ-8, CMDC PHQ-9, and PDCH HAMD-17, with CMDC
  HAMD only as a limited sanity subset.
- `P5_MV08 partial_invariance_measurement` is complete and blocked as positive
  shared-measurement evidence. The first lightweight ordinal partial-invariance
  head reduces prediction identity relative to some earlier BGE heads but is
  worse than the total-score floor on all pooled active slices. Treat it as a
  negative/diagnostic measurement result.
- `P5_MV08 error_analysis` is complete and aggregate-only. It identifies
  systematic M2 overprediction, CMDC PHQ9_8/C08 psychomotor as the largest
  pooled item delta, and HAMD threshold sparsity. The current MV08 contract
  remains negative unless the predeclared MV08b mechanism later passes.
- `P5_MV08b total_anchored_residual_measurement_design` is complete as a
  no-training design contract. It predeclares B0 train-mean items,
  B1 total-score floor, B2 fixed construct-map floor, and M2b
  total-anchored residual item heads. MV08b must beat total-score and fixed-map
  floors on at least two pooled active slices and keep prediction identity no
  higher than current MV08 M2; otherwise MV08/MV08b should be frozen as
  negative RQ1 diagnostic evidence.
- `P5_MV08b total_anchored_residual_measurement` is complete and blocked:
  M2b beats both floors on 2/3 pooled active slices, but prediction identity BA
  rises to `0.979`, above the predeclared `0.900` gate. Freeze MV08/MV08b as
  negative RQ1 diagnostic evidence for the current feature/measurement
  contract.
- `P5_MV09 conditional_dataset_identity_audit` is complete and revises identity
  gates. Future shared-latent claims must report conditional identity, and the
  current BGE contract remains highly dataset-identifiable after conditioning.
- `P5_MV10 classical_psychometric_invariance_baseline` is complete and supports
  a bounded label-only PHQ common-structure screen with candidate anchors
  `C01`, `C04`, `C05`, and `C07`; exact threshold/scalar equivalence is not
  uniformly supported.
- `P5_MV11 formal_ordinal_psychometric_confirmation` is complete and preserves
  the MV10 anchor map with a BIC caveat and threshold DIF on `C02`/`C06`.
- `P5_MV12 two_stage_latent_target` is complete but blocked as positive method
  evidence; the aggregate tradeoff analysis freezes the current latent-target
  line.
- `P5_MV13 external_psychometric_replication` is complete with a configural
  convergence caveat and qualitatively replicates the MV11 anchor/DIF pattern.
- `P5_MV14 measurement_uncertainty_bootstrap_design` is complete and consumed
  by the MV14 run. It predeclared group-wise subject bootstrap, stability
  metrics, local-only boundaries, and pass/downgrade rules before execution.
- `P5_MV14 measurement_uncertainty_bootstrap` is complete with convergence-safe
  inference: full-ladder effective R `120/200`, configural converged
  `120/200`, stable-ladder effective R `197`, minimum DIF anchor-support
  effective R `77/100`, threshold-DIF comparison effective R `100/100`,
  stable anchors `C01/C04/C05/C07`, and threshold DIF concentrated on
  `C02/C06`. Treat it as item-level measurement-shift evidence with uncertain
  global invariance-model selection.
- `P5_MV15 latent_conditioned_dataset_identity_design` is complete and design
  consumed by the MV15 run.
- `P5_MV15 latent_conditioned_dataset_identity` is complete and blocked:
  theta-conditioned BGE feature identity remains `1.000`, matching total,
  predicted-total, and B3-conditioned feature identity, while theta-only and
  predicted-theta output identity are lower. Keep feature-invariance and
  low-dimensional-output identity separate.
- `P5_MV16 dif_guided_calibration` is complete:
  it implements the predeclared E-DAIC->CMDC and CMDC->E-DAIC PHQ calibration
  directions at k=`0/5/10/20/40`, with locked anchors `C01/C04/C05/C07`,
  primary threshold-DIF calibration for `C02/C06`, global affine/monotonic,
  all-threshold, zero-shot, and direct target-adaptation comparators.
  Subject-overlap, ladder-completeness, anchor-safety, direct-baseline,
  output-identity, and artifact-hygiene gates pass, but the DIF-guided
  small-k gate fails in both directions (`blocked_no_dif_guided_small_k_gain`).
  Treat MV16 as bounded/negative calibration evidence, not a method pass.
- Post-review feature-contract caveat:
  the legacy BGE-linked MV07 -> MV12 -> MV15 -> MV16 chain remains
  diagnostic because E-DAIC MV07 feature generation used
  `BAAI/bge-small-zh-v1.5`, a Chinese model, on English transcripts, and the
  available E-DAIC transcript CSVs do not expose speaker roles for
  participant/interviewer filtering. This caveat does not affect label-only
  MV10/MV11/MV13/MV14 psychometric results. MV17a now completes the
  paper-critical multilingual sensitivity: BGE-M3 and multilingual-E5 both
  reproduce the blocked MV07/MV12/MV15 pattern, with feature identity and
  theta-conditioned feature identity still high.
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

- Immediate governance: latest-tree row-level dataset exposure has been
  mitigated. Keep real row-level manifests, file-integrity rows, and subject
  split maps local-only; publish schema, synthetic examples, generation
  scripts, and aggregate audits. Any remote history rewrite still requires
  explicit user approval.
- Phase 5 execution: freeze MV08/MV08b and the current MV12 latent-target line
  as bounded diagnostic evidence, keep MV14 as the completed convergence-safe
  item-level measurement-uncertainty layer, freeze MV15 as negative
  latent-conditioned feature-identity evidence now replicated under the MV17a
  multilingual feature contract, and freeze MV16 as a completed
  bounded/negative few-shot calibration result. MV06 agreement uncertainty is
  complete; resolve the one incomplete local candidate before stronger RQ4
  wording if available.
- Post-review experiment queue:
  1. MV17a multilingual feature-contract sensitivity: complete. BGE-M3 and
     multilingual-E5 regenerate E-DAIC/CMDC/PDCH features and reproduce the
     blocked MV07/MV12/MV15 pattern. Do not rerun MV16 unless a new explicit
     need is identified.
  2. MV18 CMDC-HAMD versus PDCH-HAMD same-scale exploratory
     control: complete. The mild/moderate HAMD overlap shows 4
     severity-conditioned residual item-shift flags, 7 threshold-shift flags,
     and weak primary bidirectional transfer under the current frozen-feature
     contract. Treat as exploratory context-shift support, not formal HAMD
     invariance.
  3. MV19 finite-sample PHQ psychometric simulation: complete. With 500
     simulations per world, H0 C02/C06 both-flag false rate is `0.208`, H1
     C02/C06 both-flag recovery is `0.662`, H1 top-two recovery is `0.222`,
     and H1 anchor subset recovery is `0.178`. Downgrade C02/C06 from robust
     standalone DIF to repeated but finite-sample-bounded dataset-group
     threshold-shift evidence.
  4. MV20 criterion-contamination stress: optional after manuscript review;
     separate mirror-like
     interviewer/question turns from non-mirror turns before adding any
     protocol-bias method.
- Stop lines:
  no extra shallow BGE heads, projection dimensions, MV16 calibration variants,
  personality gating/calibrators, or EATD valence-adversarial modules without a
  new predeclared mechanism-changing contract.
- Paper consolidation: aggregate-only manuscript draft v0.1 is generated under
  `analysis/diagnostic_measurement_audit_paper/` with traceability, open
  editing items, and artifact-hygiene checks. A first bibliography handoff is
  also generated there as `references.bib`, `citation_registry.csv`, and
  `citation_source_map.csv`, with the IRT DIF source hint corrected to Bulut
  and Suh 2017 plus post-review metadata fixes for P3HF, Multi-Probe Audit, and
  EMNLP interviewer bias. The active paper task is manuscript consolidation
  with MV19-downgraded PHQ wording; citation-key insertion, venue-style
  reference formatting, human manuscript editing, and cross-reference cleanup
  continue as paper-side work without strengthening claims beyond the
  full-method gate.
- Phase 6: protocol consistency/adversarial components only if Phase 3 supports
  them.
- Phase 7: individual-difference and gait-to-psychomotor constraints only if
  MPDD diagnostics support them.
- Phase 8+: cross-dataset transfer, leave-one-dataset-out, few-shot adaptation,
  statistical testing, error analysis, and paper writing.
