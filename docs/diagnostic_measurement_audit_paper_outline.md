# Diagnostic Measurement-Audit Paper Outline

Last updated: 2026-08-11 UTC

## Working Title

Do Depression Datasets Measure the Same Construct? A Measurement-Invariance
View of Cross-Dataset Multimodal Depression Detection

## Current Thesis

The publishable contribution should be framed as a measurement-shift and
measurement-invariance diagnostic paper rather than a broad state-of-the-art
model paper. Across E-DAIC, CMDC, PDCH, MODMA, EATD, and MPDD, the evidence
shows that depression prediction is shaped by dataset identity, protocol/task
content, label scale, and population context. A symptom-aligned framework is
still the right scientific direction, but the current frozen-feature and
shallow-measurement contracts do not justify a transferable shared-symptom
representation claim.

The key conceptual correction after MV09 is that unconditional dataset identity
is a shortcut-risk screen, not a standalone hard failure. For shared-latent
claims, the stronger question is conditional identity: whether dataset identity
remains recoverable after conditioning on severity, aligned item labels, and
legitimate covariates where available.

MV10 adds the first label-only PHQ-8/PHQ-9 psychometric baseline. It supports a
common one-factor/configural screen and strong loading congruence, but
threshold/scalar agreement is only partial. This moves the project from a
generic benchmark audit toward a target-measurement-shift paper: the next gate
is formal ordinal CFA/IRT confirmation of the candidate PHQ anchors before any
new multimodal `X -> theta` experiment.

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
- MV07/MV07b/MV07c and MV08/MV08b can be used as an accuracy-invariance
  trade-off sequence, not as positive shared-space evidence.

Blocked claims:

- Full M0/M1/M2/M3 symptom-aligned method construction.
- A transferable shared-symptom representation across PHQ-8, PHQ-9, HAMD-17,
  and SDS.
- A formal PHQ-8/PHQ-9 measurement-invariance claim from MV10 alone, because
  MV10 is an approximate label-only screen rather than ordinal CFA/IRT.
- Positive EATD SDS external generalization.
- EATD-driven valence-adversarial method design.
- Positive MPDD context-conditioning or calibration.

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
   evidence. CMDC HAMD remains too small and negative as a transfer target.

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

8. Evidence localization is a credibility layer, not a rescue for weak RQ1.
   MV06 can support bounded aggregate credibility claims, but stronger RQ4
   claims need a larger E-DAIC double-annotation slice or additional agreement
   uncertainty analysis.

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

5. Minimal Method Evidence and Accuracy-Invariance Trade-Offs
   - MV01 PHQ bridge.
   - MV02 PDCH HAMD bridge.
   - MV03/MV03b SDS stress.
   - MV04/MV04b/MV04c protocol and identity controls.
   - MV05 context calibration.
   - MV07/MV07b/MV07c aligned-BGE shared-feature sequence.
   - MV08/MV08b measurement-invariance sequence.
   - MV09 conditional dataset identity and Pareto-style accuracy-invariance
     summary.

6. Psychometric Measurement Baselines
   - MV10 approximate PHQ-8/PHQ-9 configural, metric, scalar/threshold, and
     partial-invariance screen.
   - Formal ordinal CFA/IRT confirmation as the next gate.
   - Label-only scale linking before multimodal prediction.
   - Two-stage target plan: fit measurement model `Y -> theta`, train
     multimodal predictor `X -> theta`, then map `theta -> Y^(d)`.

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
- `key_numeric_findings.csv`: eight manuscript-ready findings for the full gate,
  RQ1 measurement sequence, MV10 psychometric baseline, MV09 conditional
  identity, PDCH HAMD, MODMA task control, EATD stress, and MV06 evidence
  localization.
- `literature_positioning.csv`: web-checked source list for dataset governance,
  interviewer/protocol bias, PHQ/HAMD psychometrics, measurement invariance,
  MPDD/P3HF positioning, and PDCH.
- `report.md`, `run_summary.json`, and `artifact_hygiene_audit.json`: writing
  handoff and release/hygiene status.

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
6. Run or package formal ordinal CFA/IRT confirmation for the MV10 PHQ anchor
   map, then predeclare the two-stage latent-target experiment if the
   measurement target is stable.
6. Draft the Baselines and Failure-Mode Diagnostics section from Phase 2 and
   Phase 3 aggregate summaries.
7. Expand E-DAIC MV06 double annotation if a stronger RQ4 claim is desired.
8. Prepare result tables from existing aggregate summaries only; do not export
   row-level predictions, raw text, subject locators, learned parameters, or
   model files.
