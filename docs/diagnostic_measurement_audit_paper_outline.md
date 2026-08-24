# Diagnostic Measurement-Audit Paper Outline

Last updated: 2026-08-22 UTC

## Working Title

Before Aligning Representations, Align the Target: A Measurement-Validity
Audit of Cross-Corpus Depression Detection

## Current Thesis

The publishable contribution should be framed as a target measurement-validity
paper rather than a broad state-of-the-art model paper. Across E-DAIC, CMDC,
PDCH, MODMA, EATD, and MPDD, the evidence shows that depression prediction is
shaped by dataset identity, protocol/task content, label scale, and population
context. A symptom-aligned framework is still the right scientific direction,
but the current frozen-feature and shallow-measurement contracts do not justify
a transferable shared-symptom representation claim.

The central theoretical frame is:

```text
P(X,Y | theta,D) = P(X | theta,D) P(Y | theta,D)
```

Most cross-domain depression-detection methods target `P(X | theta,D)` by
aligning language, modality, protocol, or population signatures. This project
now asks the complementary target question: whether `P(Y | theta,D)` is stable
enough for labels from different corpora to be treated as measuring the same
clinical target. If the measurement function changes by dataset/group,
representation alignment alone cannot guarantee clinically comparable
prediction.

The key conceptual correction after MV09 is that unconditional dataset identity
is a shortcut-risk screen, not a standalone hard failure. For shared-latent
claims, the stronger question is conditional identity: whether dataset identity
remains recoverable after conditioning on severity, aligned item labels, and
legitimate covariates where available.

MV10 adds the first label-only E-DAIC/CMDC PHQ psychometric baseline. It supports
substantial common PHQ structure and strong loading congruence, but exact
threshold/scalar agreement is not uniformly supported. MV11 then fits a label-only
multi-group graded-response IRT confirmation. It preserves the four MV10
anchors, flags no loading DIF, flags threshold DIF for `C02` and `C06`, and
records an AIC/BIC caveat. MV13 externally repeats this qualitative
psychometric pattern with R `mirt::multipleGroup`: the same four anchors are
confirmed, loading DIF remains unflagged, threshold DIF remains localized to
`C02` and `C06`, AIC still prefers the partial model, and BIC still prefers
scalar, while a configural convergence warning keeps the claim conservative.
A corrected code-level mirt audit now verifies the boundary that matters for
MV13/MV14: E-DAIC is the reference group, CMDC is the focal group, anchor and
threshold linking are explicit, and focal mean/variance are freed for
threshold-constrained anchor-linked models. MV13/MV14 are therefore corrected
external mirt qualitative/uncertainty corroboration, still bounded by the
configural convergence warning and observed-N finite-sample behavior. MV14 adds
the predeclared bootstrap uncertainty layer under that corrected
parameterization: with
smoke/core/DIF R=`10/200/100`, convergence-safe full-ladder effective core R is
`120/200` after `185/200` fit-success draws, configural converges in `120/200`,
the stable metric/partial/scalar ladder has `197` effective draws, minimum
anchor-support DIF effective R is `77/100`, all four MV10 anchors remain
stable, and threshold DIF stays localized to `C02` and `C06`. MV19 then tests
the observed-N finite-sample
behavior and downgrades C02/C06 from robust standalone DIF to repeated but
finite-sample-bounded dataset-group threshold-shift evidence. Together,
MV10/MV11/MV19 plus the corrected bounded MV13/MV14 mirt checks move the
project from a generic benchmark audit toward a target-measurement-shift paper;
they still do not authorize a full method.

MV17a is now the primary prediction-consequence layer. It makes BGE-M3 the
primary multilingual feature contract and multilingual-E5 the sensitivity
encoder, regenerates E-DAIC/CMDC/PDCH features, and reruns MV07/MV12/MV15.
Both encoders show that `X -> theta` is learnable within datasets, output-level
identity is low, observed-scale safety fails, and theta-conditioned feature
identity remains `1.000`. External theta transfer is encoder-dependent
(BGE-M3 passes, multilingual-E5 fails), and B3 Pareto dominance is also
encoder-dependent (false for BGE-M3, true for multilingual-E5). The correct
paper claim is therefore not universal transfer failure or universal B3
dominance. It is that psychometric harmonization can reduce output-level
dataset identifiability, but the current feature contracts do not establish
observed-scale-safe or feature-invariant cross-corpus prediction. MV12/MV15
remain useful as legacy/supporting diagnostics, not as the canonical feature
contract.

This PHQ result must be written as E-DAIC/CMDC dataset-group localized
threshold non-equivalence among shared PHQ items, not as a clean PHQ-8 versus
PHQ-9 scale-specific difference. The current data cannot separate form,
language, country, protocol, setting, translation, sample severity, and
population effects.

The legacy BGE-linked MV07 -> MV12 -> MV15 -> MV16 feature-level chain remains
appendix/historical diagnostic because its original E-DAIC feature contract
used a Chinese encoder.
Local audit found that E-DAIC MV07 feature generation used
`BAAI/bge-small-zh-v1.5`, a Chinese model, on English E-DAIC transcripts, and
the available transcript CSVs do not expose speaker roles for participant-only
filtering. MV17a addresses the language-encoder mismatch but not the
speaker/interviewer contamination limitation. This does not affect label-only
MV10/MV11/MV19 primary psychometric evidence or the corrected MV13/MV14 mirt
corroboration.

The Baselines, Failure-Mode Diagnostics, and Measurement Results scaffold is
now generated from aggregate artifacts. The next research route is no longer
another shallow shared-symptom head. The post-review bounded line is complete:
MV17a fixed the multilingual feature-contract sensitivity, MV18 added the
same-HAMD context control, MV19 downgraded PHQ C02/C06 wording under observed
N, and MV20 closed the criterion-overlap stress as negative/no-excess evidence.
The mirt parameterization audit has closed the MV13/MV14 statistical-correctness
blocker. The next work is manuscript editing and citation verification rather
than changing the calibration or protocol-overlap design after seeing results. A full
manuscript draft v0.1 is now generated from aggregate paper artifacts with
traceability, open editing items, and artifact-hygiene checks.

Phase 5 experiment consolidation now defines the active evidence bundle. The
manuscript should foreground `MV10/MV11/MV19` as primary paper-core
psychometric evidence, retain corrected `MV13/MV14` as anchor-linked mirt
corroboration with convergence and finite-sample caveats, and use
`MV02/MV04c/MV06/MV09/MV12/MV15/MV16/MV17a/MV18/MV20` as bounded support. The
mirt parameterization audit is a paper guardrail, not a new experiment result.
Earlier weak or superseded MV rows stay in the repository
only as aggregate traceability records, not as active experiments or primary
paper sections.

## Post-Review Contribution Shape

The manuscript should be compressed to three contributions:

1. Measurement-validity framework:
   feature shift, target measurement shift, and prediction shift are distinct.
2. Empirical psychometric evidence:
   E-DAIC/CMDC share substantial PHQ structure but show repeated,
   finite-sample-bounded C02/C06 threshold non-equivalence with
   convergence-aware uncertainty.
3. Consequence for ML transfer:
   under BGE-M3 primary and multilingual-E5 sensitivity contracts, current
   `X -> theta` models are domain-learnable and lower output identity, but
   observed-scale safety and feature invariance remain blocked while external
   theta transfer and B3 severity-control dominance are encoder-dependent.

Supporting evidence should be explicitly demoted:

- Phase 3 is motivating benchmark/protocol shortcut evidence, not the main
  novelty because nearby benchmark-audit work overlaps this layer.
- MPDD/RQ3 is a population and individual-difference stress test, not a
  personality-aware modeling contribution.
- MV06/RQ4 is measurement-interpretation credibility support, not an evidence
  retrieval or explanation-model contribution.

## Claim Boundary

Allowed claims:

- The project provides a governed cross-dataset audit pipeline with
  subject-level splits, manifest-driven inputs, and artifact hygiene gates.
- Dataset/protocol identity is a major shortcut risk and must be reported
  before interpreting pooled depression models.
- Conditional dataset identity is now required for any future shared-latent
  claim. MV09 finds that BGE feature identity remains high after PHQ item or
  severity conditioning, so current shared-latent claims remain blocked.
- Post-head prediction identity is diagnostic when outputs are scale-specific;
  it should not be treated as the same hard gate as identity in a shared latent
  representation.
- MODMA provides bounded evidence that task nuisance control can reduce
  task-identity signal while preserving the main diagnostic task.
- PDCH supports a bounded HAMD-17 internal diagnostic bridge, not cross-dataset
  HAMD generalization.
- MV06 provides first-round aggregate evidence-localization credibility
  evidence with dataset-stratified agreement.
- MV08/MV08b provide negative measurement evidence: simple partial-invariance
  and total-anchored residual heads are not enough to establish transferable
  RQ1 measurement under the current feature contract.
- MV10 provides approximate label-only PHQ psychometric evidence: both E-DAIC
  and CMDC pass the one-factor screen, loading congruence is `0.998`, `7/8`
  items pass the metric-loading screen, and `4/8` items are candidate partial
  anchors (`C01`, `C04`, `C05`, `C07`).
- MV11 provides formal label-only graded-response IRT confirmation with a BIC
  caveat: all four MV10 anchors are preserved, no loading-DIF items are
  strongly flagged, and threshold DIF is strongest for `C02` anhedonia and
  `C06` self-worth.
- MV13 provides corrected external R `mirt::multipleGroup` qualitative
  repetition of the PHQ measurement pattern:
  all four MV10 anchors are confirmed, loading DIF remains unflagged,
  threshold DIF remains `C02`/`C06`, AIC/BIC still split between
  partial/scalar, and all fitted parameters, factor scores, model objects, and
  local item-response rows stay local-only. The parameterization audit verifies
  reference/focal order, anchor linking, threshold constraints, and freed focal
  mean/variance for threshold-constrained models.
- MV14 is retained as a completed convergence-safe corrected anchor-linked
  measurement-uncertainty/bootstrap screen. It executes the predeclared
  smoke/core/DIF tiers, keeps local
  item-response inputs and draw details out of Git, and supports bounded
  item-level wording: stable anchors
  `C01/C04/C05/C07`, sparse loading DIF, localized threshold DIF `C02/C06`, and
  uncertain global model selection. It does not authorize robust standalone
  mirt-backed DIF stability or full method work.
- MV19 provides observed-N finite-sample PHQ simulation evidence: C02/C06
  recur under the C02/C06 threshold-shift world, but H0 false/localization rates
  and low anchor-set recovery require wording them as finite-sample-bounded
  dataset-group threshold-shift evidence, not robust standalone DIF.
- MV12 provides a predeclared two-stage latent-target design that separates
  label measurement from multimodal prediction and keeps theta scores, fitted
  parameters, row predictions, transformed features, and model artifacts
  local-only.
- Legacy MV12 provides bounded two-stage latent-target run evidence:
  same-dataset theta prediction improves over train mean and conditional
  predicted-theta identity BA is `0.602`, but observed-scale reconstruction and
  old-chain source-calibrated external theta transfer block a positive
  shared-latent method claim.
- Legacy MV12 aggregate tradeoff analysis provides the freeze decision for the
  old Chinese-BGE chain: latent-target evidence improves theta utility and
  lowers identity versus the upstream feature layer, but observed-scale safety
  remains a blocker and B3 direct itemwise Ridge is a dimension-matched severity
  caveat.
- MV17a provides the current prediction-consequence evidence: BGE-M3 primary
  and multilingual-E5 sensitivity both pass same-dataset theta utility, both
  fail observed-scale safety, both keep theta-conditioned feature identity at
  `1.000`, and both keep the full method blocked. External theta transfer
  passes under BGE-M3 but fails under multilingual-E5; B3 Pareto dominance is
  false under BGE-M3 and true under multilingual-E5.
- MV15 provides completed negative latent-conditioned identity evidence:
  raw/theta/total/predicted-total/B3-conditioned BGE feature identity BA remains
  `1.000`, PHQ-item-conditioned feature identity BA is `0.974`, theta-only
  identity BA is `0.576`, and psychometric predicted-theta output identity BA is
  `0.646`. Low output identity should not be reported as upstream BGE feature
  invariance.
- MV07/MV07b/MV07c and MV08/MV08b can be used as an accuracy-invariance
  trade-off sequence, better described in the manuscript as a predictive
  fidelity-dataset identifiability trade-off, not as positive shared-space
  evidence.

Blocked claims:

- Full M0/M1/M2/M3 symptom-aligned method construction.
- A transferable shared-symptom representation across PHQ-8, PHQ-9, HAMD-17,
  and SDS.
- A full PHQ-8/PHQ-9 scalar-invariance claim, a bootstrap-confirmed global
  partial-invariance claim, robust standalone mirt DIF evidence, or robust
  standalone C02/C06 DIF, because MV10/MV11/MV19 plus corrected bounded
  MV13/MV14 mirt corroboration support item-level common-structure and repeated
  finite-sample-bounded localized threshold-shift evidence while global
  invariance-model selection remains uncertain.
- Positive EATD SDS external generalization.
- EATD-driven valence-adversarial method design.
- Positive MPDD context-conditioning or calibration.
- Positive feature-invariance claims from the MV07/MV12/MV15/MV16 chain; MV17a
  multilingual sensitivity reproduces the blocked feature-level result rather
  than reversing it.
- Universal zero-shot external theta transfer failure or universal B3 Pareto
  dominance across multilingual encoders; MV17a shows both are
  encoder-dependent.
- Personality-aware fusion, evidence-retrieval networks, extra shallow BGE
  heads, extra projection dimensions, EATD valence-adversarial modules, or
  additional MV16 tuning without a new predeclared contract.

## Next Critical Experiments

1. Done: MV17a multilingual feature-contract sensitivity.
   BGE-M3 and multilingual-E5 regenerated E-DAIC/CMDC/PDCH features and
   reran MV07, MV12, and MV15. Both encoders reproduce the blocked
   feature-level pattern; external theta transfer and B3 Pareto dominance are
   encoder-dependent. Do not rerun MV16 unless a new explicit need is
   identified.
2. Done: MV18 CMDC-HAMD versus PDCH-HAMD same-language/same-scale control.
   The mild/moderate HAMD overlap has 25 CMDC and 73 PDCH subjects. MV18 flags
   4 severity-conditioned residual item shifts, 7 threshold shifts, and weak
   primary bidirectional transfer. Use this only as exploratory same-HAMD
   context-shift support because CMDC HAMD is small.
3. Done: MV19 finite-sample PHQ psychometric simulation.
   With 500 simulations per world, H0 C02/C06 both-flag false rate is `0.208`,
   H1 C02/C06 both-flag recovery is `0.662`, H1 top-two recovery is `0.222`,
   and H1 anchor subset recovery is `0.178`. Use this as an observed-N
   downgrade for C02/C06 and anchor wording.
4. Optional: MV20 criterion-contamination stress after manuscript review:
   compare mirror-like interview/question turns against non-mirror turns using
   semantic similarity to PHQ/HAMD item content and deletion/insertion effects.

## Core Result Narrative

1. Dataset governance first.
   The study starts from registry/manifests, subject-level splits, and hygiene
   gates. This makes negative results interpretable rather than just failed
   modeling attempts.

2. Dataset and protocol identity are measurable shortcut risks.
   Phase 3 identity and protocol diagnostics show that frozen/lightweight
   features often retain dataset/protocol information strongly enough to make
   direct pooled training scientifically unsafe.

3. Simple cross-scale symptom bridges are not enough.
   MV01 and MV07/MV07b/MV07c show that PHQ itemwise heads can beat train means
   in places, and identity can sometimes be reduced, but the combination does
   not consistently beat simple total-allocation floors.

4. HAMD evidence is clinically useful but bounded.
   MV02 supports PDCH-only HAMD item/total prediction as internal diagnostic
   evidence. MV18 adds exploratory same-HAMD CMDC/PDCH context-shift evidence,
   but CMDC HAMD remains too small for formal invariance or broad HAMD transfer
   claims.

5. Partial measurement invariance is the right problem framing, but the first
   two lightweight implementations fail.
   MV08 fails total-score and fixed-map floors on all pooled active slices.
   MV08b improves over both floors on E-DAIC and PDCH, but fails the
   predeclared identity gate because prediction identity BA rises to `0.979`.

6. Conditional identity sharpens, rather than removes, the shortcut concern.
   MV09 revises the gate semantics but finds E-DAIC/CMDC PHQ-item residualized
   BGE identity BA remains `0.991`, and CMDC/PDCH severity-residualized
   identity BA remains `1.000`. This supports a measurement-shift framing and
   motivates a label-only psychometric invariance baseline before another
   multimodal head.

7. The label-only PHQ psychometric screen supports partial, not scalar,
   invariance.
   MV10 finds configural support in E-DAIC PHQ-8 and CMDC PHQ-9 with loading
   congruence `0.998`, but only `4/8` shared items pass the approximate
   threshold/scalar screen. Candidate anchors are `C01` depressed mood, `C04`
   fatigue, `C05` appetite, and `C07` concentration; `C02`, `C03`, and `C06`
   are metric-only/threshold-free, and `C08` psychomotor should be freed.

8. Formal and external label-only IRT confirmation preserve the partial-anchor story.
   MV11 fits multi-group graded-response IRT models over the same PHQ items.
   Metric constraints are not strongly rejected versus configural, scalar
   constraints are rejected by LRT only, and the MV10 partial model is best by
   AIC while scalar remains best by BIC. Item DIF checks flag no loading DIF
   and threshold DIF for `C02` and `C06`, preserving all four MV10 anchors but
   keeping a conservative caveat for manuscript claims. MV13 repeats the
   model ladder with external R `mirt`, reproduces the same qualitative
   anchor/DIF pattern, and retains the configural convergence warning as a
   limitation rather than hiding it. MV14 then tests that single-fit pattern
   under group-wise subject bootstrap: stable anchors remain `C01/C04/C05/C07`,
   threshold DIF remains concentrated on `C02/C06`, and AIC/BIC model
   preference remains an uncertainty dimension.

9. Two-stage latent-target prediction is informative but still blocked.
   MV17a is now the canonical feature-contract version of this conclusion:
   BGE-M3 and multilingual-E5 both show learnable within-dataset theta and low
   output identity, but both fail observed-scale safety and feature invariance.
   MV12 remains the legacy Chinese-BGE version of the trade-off analysis and is
   useful as a dimension-matched severity-control warning, not as the primary
   feature-contract result.

10. Evidence localization is a credibility layer, not a rescue for weak RQ1.
   MV06 can support bounded aggregate credibility claims, but stronger RQ4
   claims need completion of the remaining local candidate if available and an
   explicit discussion of agreement-uncertainty and sampling limits.

## Proposed Sections

1. Introduction
   - Depression detection needs cross-dataset validity, not only high within-
     dataset scores.
   - Symptom scales differ in labels, item coverage, protocols, and
     populations.
   - The paper asks what remains after explicit diagnostic controls.

2. Data Governance and Label Contracts
   - Dataset roles and label availability.
   - Subject-level split policy.
   - Privacy and artifact hygiene rules.

3. Baselines and Failure-Mode Diagnostics
   - Phase 2 unified baselines as reproducibility floor.
   - Phase 3 dataset identity, protocol/task, valence, and MPDD context
     diagnostics.

4. Symptom Ontology and Minimal Validation
   - C01-C15 construct map.
   - Why PHQ-8/PHQ-9 are the cleanest shared bridge.
   - Why HAMD/SDS require bounded auxiliary or total-only handling.

5. Minimal Method Evidence and Predictive Fidelity-Identifiability Trade-Offs
   - MV01 PHQ bridge.
   - MV02 PDCH HAMD bridge.
   - MV03/MV03b SDS stress.
   - MV04/MV04b/MV04c protocol and identity controls.
   - MV05 context calibration.
   - MV07/MV07b/MV07c aligned-BGE shared-feature sequence.
   - MV08/MV08b measurement-invariance sequence.
   - MV09 conditional dataset identity and Pareto-style predictive
     fidelity-dataset identifiability summary.

6. Psychometric Measurement Baselines
   - MV10 approximate PHQ-8/PHQ-9 configural, metric, scalar/threshold, and
     partial-invariance screen.
   - MV11 formal label-only graded-response IRT confirmation.
   - MV13 external R `mirt` replication and convergence caveat.
   - MV14 measurement-uncertainty/bootstrap run and stability results.
   - MV19 observed-N finite-sample PHQ simulation and downgraded C02/C06
     wording.
   - MV12 two-stage latent-target design, blocked run, and aggregate
     tradeoff/failure-mode analysis.
   - Label-only scale linking before multimodal prediction.
   - Frozen current line: future method work needs a genuinely new mechanism,
     not another small shallow-head variant.

7. Evidence Localization
   - MV06 aggregate annotation workflow.
   - Dataset-stratified agreement.
   - Prompt-artifact versus participant-evidence boundary.

8. Discussion
   - Negative results as measurement evidence.
   - Why total-score floors are hard to beat.
   - Why unconditional identity reduction alone is insufficient.
   - What future work would need: new item labels, stronger aligned features,
     speaker/protocol labels, and larger evidence annotation.

## Paper-Facing Tables

The first paper table scaffold is generated at
`analysis/diagnostic_measurement_audit_paper/` by:

```bash
python scripts/build_diagnostic_paper_claim_tables.py
```

Tracked outputs:

- `paper_claim_boundary.csv` and `paper_claim_boundary.md`: compact
  allowed/blocked claim language, evidence, guardrails, and source artifact IDs.
- `key_numeric_findings.csv`: manuscript-ready findings for the full gate,
  RQ1 measurement sequence, MV10 psychometric baseline, MV11 formal
  confirmation, MV13 external replication, MV19 finite-sample simulation,
  MV12 design, MV12 run, MV12
  tradeoff freeze decision, MV09 conditional identity, PDCH HAMD, MODMA task
  control, EATD stress, and MV06 evidence localization.
- `literature_positioning.csv`: web-checked source list for dataset governance,
  interviewer/protocol bias, PHQ/HAMD psychometrics, measurement invariance,
  MPDD/P3HF positioning, and PDCH.
- `report.md`, `run_summary.json`, and `artifact_hygiene_audit.json`: writing
  handoff and release/hygiene status.

The Baselines, Failure-Mode Diagnostics, and Measurement Results scaffold is
generated in the same directory by:

```bash
python scripts/build_diagnostic_paper_results_sections.py
```

Tracked outputs:

- `baselines_failure_modes_measurement_results.md`: draft manuscript text for
  the baseline floor, Phase 3 failure-mode diagnostics, MV08-MV13 measurement
  results, and bounded Phase 5 supporting claims.
- `results_section_source_map.csv`: aggregate source artifact map.
- `results_section_claim_checklist.csv`: release-safe claim and guardrail
  checklist.
- `results_section_report.md`, `results_section_run_summary.json`, and
  `results_section_artifact_hygiene_audit.json`: writing handoff and hygiene
  status.

The full manuscript draft v0.1 is generated in the same directory by:

```bash
python scripts/build_diagnostic_paper_manuscript_draft.py
```

Tracked outputs:

- `manuscript_draft.md`: aggregate-only manuscript draft for human editing.
- `manuscript_traceability_matrix.csv`: claim/source traceability table.
- `manuscript_open_items.csv`: remaining editing, bibliography, and optional
  evidence-strengthening items.
- `manuscript_report.md`, `manuscript_run_summary.json`, and
  `manuscript_artifact_hygiene_audit.json`: writing handoff and hygiene
  status.

The bibliography handoff is generated in the same directory by:

```bash
python scripts/build_diagnostic_paper_bibliography.py
```

Tracked outputs:

- `references.bib`: first formal BibTeX file for the manuscript draft.
- `citation_registry.csv`: citation keys, metadata, verification status, and
  source-context coverage.
- `citation_source_map.csv`: mapping from source-context rows to citation keys.
- `bibliography_report.md`, `bibliography_run_summary.json`, and
  `bibliography_artifact_hygiene_audit.json`: citation handoff and hygiene
  status.

The MV09 conditional identity audit is generated by:

```bash
python scripts/phase5_run_mv09_conditional_identity_audit.py
```

Tracked outputs include `conditional_identity_summary.csv`,
`gate_revision_recommendations.csv`, `accuracy_invariance_pareto_summary.csv`,
`report.md`, `run_summary.json`, and `artifact_hygiene_audit.json` under
`analysis/phase5_minimal_validation/p5_mv09_conditional_identity_audit/`.

The MV10 psychometric invariance baseline is generated by:

```bash
python scripts/phase5_run_mv10_psychometric_invariance_baseline.py
```

Tracked outputs include `reliability_dimensionality_summary.csv`,
`loading_invariance_summary.csv`, `threshold_dif_summary.csv`,
`partial_invariance_summary.csv`, `empirical_score_linking_summary.csv`,
`stage_summary.csv`, `report.md`, `run_summary.json`, and
`artifact_hygiene_audit.json` under
`analysis/phase5_minimal_validation/p5_mv10_psychometric_invariance_baseline/`.

The Phase 5 experiment consolidation inventory is generated by:

```bash
python scripts/phase5_consolidate_experiment_inventory.py
```

Tracked outputs include `experiment_consolidation_inventory.csv`,
`active_evidence_bundle.csv`, `retired_or_frozen_experiments.csv`,
`local_cleanup_inventory.csv`, `report.md`, `run_summary.json`, and
`artifact_hygiene_audit.json` under
`analysis/phase5_minimal_validation/experiment_consolidation/`.

The MV11 formal psychometric confirmation is generated by:

```bash
python scripts/phase5_run_mv11_formal_psychometric_confirmation.py
```

Tracked outputs include `fit_model_summary.csv`,
`invariance_comparison_summary.csv`, `item_dif_lrt_summary.csv`,
`anchor_confirmation_summary.csv`, `gate_recommendations.csv`,
`method_context_formal_irt.csv`, `report.md`, `run_summary.json`, and
`artifact_hygiene_audit.json` under
`analysis/phase5_minimal_validation/p5_mv11_formal_psychometric_confirmation/`.

The MV12 two-stage latent-target design is generated by:

```bash
python scripts/phase5_plan_mv12_two_stage_latent_target.py --overwrite
```

Tracked outputs include `target_generation_contract.csv`,
`local_only_boundary_contract.csv`, `model_ladder_contract.csv`,
`identity_transfer_gate_contract.csv`, `pass_fail_gate_contract.csv`,
`source_evidence_summary.csv`, `implementation_queue.csv`,
`method_source_refs.csv`, `report.md`, `run_summary.json`, and
`artifact_hygiene_audit.json` under
`analysis/phase5_minimal_validation/p5_mv12_two_stage_latent_target_design/`.

The MV12 two-stage latent-target run is generated by:

```bash
python scripts/phase5_run_mv12_two_stage_latent_target.py
```

Tracked outputs include `comparison_summary.csv`, `metric_summary.csv`,
`target_generation_summary.csv`, `target_reliability_summary.csv`,
`identity_probe_summary.csv`, `transfer_summary.csv`, `leakage_audit.csv`,
`model_split_audit.csv`, `label_feature_audit.csv`, `construct_target_map.csv`,
`local_artifact_manifest.csv`, `report.md`, `run_summary.json`, and
`artifact_hygiene_audit.json` under
`analysis/phase5_minimal_validation/p5_mv12_two_stage_latent_target/`.

The MV12 aggregate tradeoff/failure-mode analysis is generated by:

```bash
python scripts/phase5_analyze_mv12_latent_target_tradeoffs.py
```

Tracked outputs include `accuracy_identity_tradeoff_summary.csv`,
`gate_decomposition.csv`, `failure_mode_summary.csv`,
`mechanism_recommendation_queue.csv`, `mv12_dataset_slice_diagnostics.csv`,
`source_artifact_summary.csv`, `report.md`, `run_summary.json`, and
`artifact_hygiene_audit.json` under
`analysis/phase5_minimal_validation/p5_mv12_latent_target_tradeoff_analysis/`.

The MV14 measurement-uncertainty/bootstrap design is generated by:

```bash
python scripts/phase5_plan_mv14_measurement_uncertainty_bootstrap.py --overwrite
```

Tracked outputs include `bootstrap_ladder_contract.csv`,
`stability_metric_contract.csv`, `local_only_boundary_contract.csv`,
`input_boundary_contract.csv`, `pass_fail_gate_contract.csv`,
`implementation_queue.csv`, `method_source_refs.csv`,
`source_evidence_summary.csv`, `runtime_preflight.csv`, `report.md`,
`run_summary.json`, and `artifact_hygiene_audit.json` under
`analysis/phase5_minimal_validation/p5_mv14_measurement_uncertainty_bootstrap_design/`.

The MV14 measurement-uncertainty/bootstrap run is generated by:

```bash
python scripts/phase5_run_mv14_measurement_uncertainty_bootstrap.py
```

Tracked outputs include `bootstrap_ladder_realization.csv`,
`bootstrap_runtime_summary.csv`, `core_model_stability_summary.csv`,
`model_selection_frequency.csv`, `invariance_decision_frequency.csv`,
`item_dif_stability_summary.csv`, `itemfit_stability_summary.csv`,
`mv11_mv13_mv14_alignment_summary.csv`, `pass_fail_gate_assessment.csv`,
`gate_recommendations.csv`, `report.md`, `run_summary.json`, and
`artifact_hygiene_audit.json` under
`analysis/phase5_minimal_validation/p5_mv14_measurement_uncertainty_bootstrap/`.

The MV15 latent-conditioned identity design is generated by:

```bash
python scripts/phase5_plan_mv15_latent_conditioned_identity.py --overwrite
```

Tracked outputs include `dataset_scope_contract.csv`,
`analysis_variable_contract.csv`, `conditioning_ladder_contract.csv`,
`identity_probe_contract.csv`, `pass_fail_gate_contract.csv`,
`local_only_boundary_contract.csv`, `implementation_queue.csv`,
`source_evidence_summary.csv`, `report.md`, `run_summary.json`, and
`artifact_hygiene_audit.json` under
`analysis/phase5_minimal_validation/p5_mv15_latent_conditioned_identity_design/`.

The MV15 latent-conditioned identity run is generated by:

```bash
python scripts/phase5_run_mv15_latent_conditioned_identity.py
```

Tracked outputs include aggregate identity-score, conditioning-ladder,
output-identity, external-sensitivity, pass/fail, report, run summary, and
artifact-hygiene files under
`analysis/phase5_minimal_validation/p5_mv15_latent_conditioned_identity/`.

The MV16 DIF-guided calibration design is generated by:

```bash
python scripts/phase5_plan_mv16_dif_guided_calibration.py --overwrite
python scripts/phase5_run_mv16_dif_guided_calibration.py
```

Tracked outputs include dataset-direction, k-shot sampling, item-role,
calibration-ladder, model-comparison, metric, pass/fail, local-only-boundary,
source-reference, report, run summary, and artifact-hygiene files under
`analysis/phase5_minimal_validation/p5_mv16_dif_guided_calibration_design/`
and aggregate few-shot calibration curves, gate diagnostics, output-identity
summaries, report, run summary, and artifact-hygiene files under
`analysis/phase5_minimal_validation/p5_mv16_dif_guided_calibration/`.

The Data Governance and Label Contracts section scaffold is generated in the
same directory by:

```bash
python scripts/build_diagnostic_paper_data_governance_section.py
```

Tracked outputs:

- `dataset_governance_summary.csv`: six-dataset registry/audit summary with
  roles, protocols, modalities, valid rows, label type, and quality notes.
- `label_contract_summary.csv`: seven dataset-scale label contracts and
  paper-facing claim boundaries.
- `construct_coverage_summary.csv`: PHQ-8, PHQ-9, HAMD-17, and SDS coverage of
  the 15-construct ontology.
- `release_boundary_summary.csv`: what remains local-only versus what can be
  tracked after hygiene.
- `source_context_data_governance.csv`: web-checked primary source context for
  dataset and psychometric framing.
- `data_governance_label_contracts.md`, `data_governance_report.md`,
  `data_governance_run_summary.json`, and
  `data_governance_artifact_hygiene_audit.json`: manuscript draft and
  reproducibility/hygiene status.

## Immediate Writing Tasks

1. Done: freeze MV08/MV08b as negative RQ1 diagnostic evidence in the issue log
   and master plan.
2. Done: create compact allowed/blocked claim tables from the full-method gate.
3. Done: draft the Data Governance and Label Contracts section from existing
   Phase 0 through Phase 4 artifacts.
4. Done: run MV09 conditional identity audit and update the full-method gate.
5. Done: run MV10 approximate PHQ-8/PHQ-9 psychometric invariance baseline.
6. Done: run MV11 formal label-only graded-response IRT confirmation.
7. Done: predeclare the two-stage latent-target experiment with local-only
   theta scores/parameters, direct X-to-Y floors, conditional identity probes,
   and external transfer checks.
8. Done: implement and run the MV12 two-stage latent-target experiment.
9. Done: add aggregate-only MV12 tradeoff/failure-mode analysis and freeze
   MV12 as the current bounded diagnostic result.
10. Done: draft the Baselines, Failure-Mode Diagnostics, and Measurement
   Results sections from aggregate tables.
11. Done: predeclare and run MV13 external R `mirt` psychometric replication,
   confirming the MV10/MV11 qualitative anchor/DIF localization pattern with a
   configural convergence caveat.
12. Done: predeclare MV14 measurement-uncertainty bootstrap for PHQ anchors,
   loadings, thresholds, DIF selection frequency, model selection, convergence,
   item fit, and SE/CI availability.
13. Done: implement and rerun the corrected convergence-safe MV14 bootstrap,
   exporting aggregate stability summaries only.
14. Done: predeclare MV15 latent-conditioned dataset identity with
   dimension-matched severity controls: raw `Z`, total, predicted total,
   observed items, B3 itemwise theta, psychometric theta, covariates,
   predicted-output identity, and severity-only sensitivities.
15. Done: implement and run MV15 latent-conditioned identity, keeping theta
   scores, residualized features, row predictions, split maps, and fitted
   artifacts local-only.
16. Done: predeclare MV16 DIF-guided cross-dataset measurement calibration:
   compare zero-shot source measurement, global affine/monotonic theta
   calibration, `C02/C06` threshold calibration, all-threshold calibration, and
   direct target-domain adaptation at k=`0/5/10/20/40`.
17. Done: implement and run the MV16 calibration runner with aggregate curves
   only and local-only theta/calibration/row artifacts. MV16 is
   `blocked_no_dif_guided_small_k_gain`; use it as bounded/negative
   calibration evidence, not a method pass.
18. Done: consolidate the manuscript around the completed bounded diagnostic
   evidence in generated manuscript draft v0.1.
19. Done: add MV06 agreement uncertainty analysis. Resolve the remaining
   incomplete local candidate if stronger RQ4 wording is desired.
20. Done: generate the bibliography registry and `references.bib` from
   source-context rows. The IRT DIF source hint is corrected to Bulut and Suh
   2017.
21. Done: predeclare the post-review MV17 measurement-validity route and
   feature-contract caveat.
22. Done: run MV17a multilingual BGE-M3 plus multilingual-E5 feature-contract
   sensitivity for MV07/MV12/MV15; both encoders reproduce the blocked result,
   while external theta transfer and B3 Pareto dominance are encoder-dependent.
23. Done: run MV18 CMDC-HAMD versus PDCH-HAMD same-scale exploratory control.
24. Done: run MV19 finite-sample PHQ psychometric simulation and downgrade
   C02/C06 wording to finite-sample-bounded dataset-group threshold-shift
   evidence.
25. Done: calibrate manuscript wording around MV17a as the canonical
   prediction-consequence layer and old Chinese-BGE outputs as
   legacy/supporting diagnostics.
26. Done: run MV20 criterion-overlap stress. CMDC Q1-Q12 question-position
   units were feasible; PDCH and E-DAIC were excluded for missing clean
   protocol units; BGE-M3 primary and multilingual-E5 sensitivity both show no
   clear high-overlap excess over matched random deletion.
27. Next: freeze experiments, finish manuscript editing, and complete
   primary-source citation verification.
28. Parallel writing: prepare manuscript edits from existing aggregate
   summaries only; do not export row-level predictions, raw text, subject
   locators, learned parameters, or model files. Insert generated citation keys
   and adapt references to the target venue style after full reference
   verification.
