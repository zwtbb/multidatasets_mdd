# Diagnostic Measurement-Audit Paper Outline

Last updated: 2026-08-11 UTC

## Working Title

When Depression Datasets Do Not Measure the Same Thing: A Cross-Dataset
Diagnostic Audit of Symptom, Protocol, and Population Effects

## Current Thesis

The publishable contribution should be framed as a diagnostic and measurement
audit rather than a broad state-of-the-art model paper. Across E-DAIC, CMDC,
PDCH, MODMA, EATD, and MPDD, the evidence shows that depression prediction is
strongly shaped by dataset identity, protocol/task content, label scale, and
population context. A symptom-aligned framework is still the right scientific
direction, but the current frozen-feature and shallow-measurement contracts do
not justify a transferable shared-symptom representation claim.

## Claim Boundary

Allowed claims:

- The project provides a governed cross-dataset audit pipeline with
  subject-level splits, manifest-driven inputs, and artifact hygiene gates.
- Dataset/protocol identity is a major shortcut risk and must be reported
  before interpreting pooled depression models.
- MODMA provides bounded evidence that task nuisance control can reduce
  task-identity signal while preserving the main diagnostic task.
- PDCH supports a bounded HAMD-17 internal diagnostic bridge, not cross-dataset
  HAMD generalization.
- MV06 provides first-round aggregate evidence-localization credibility
  evidence with dataset-stratified agreement.
- MV08/MV08b provide negative measurement evidence: simple partial-invariance
  and total-anchored residual heads are not enough to establish transferable
  RQ1 measurement under the current feature contract.

Blocked claims:

- Full M0/M1/M2/M3 symptom-aligned method construction.
- A transferable shared-symptom representation across PHQ-8, PHQ-9, HAMD-17,
  and SDS.
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

6. Evidence localization is a credibility layer, not a rescue for weak RQ1.
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

5. Minimal Method Evidence
   - MV01 PHQ bridge.
   - MV02 PDCH HAMD bridge.
   - MV03/MV03b SDS stress.
   - MV04/MV04b/MV04c protocol and identity controls.
   - MV05 context calibration.
   - MV07/MV07b/MV07c aligned-BGE shared-feature sequence.
   - MV08/MV08b measurement-invariance sequence.

6. Evidence Localization
   - MV06 aggregate annotation workflow.
   - Dataset-stratified agreement.
   - Prompt-artifact versus participant-evidence boundary.

7. Discussion
   - Negative results as measurement evidence.
   - Why total-score floors are hard to beat.
   - Why identity reduction alone is insufficient.
   - What future work would need: new item labels, stronger aligned features,
     speaker/protocol labels, and larger evidence annotation.

## Immediate Writing Tasks

1. Freeze MV08/MV08b as negative RQ1 diagnostic evidence in the issue log and
   master plan.
2. Create a compact table of allowed versus blocked claims from the full-method
   gate.
3. Draft the Data Governance and Label Contracts section from existing Phase 0
   through Phase 4 artifacts.
4. Expand E-DAIC MV06 double annotation if a stronger RQ4 claim is desired.
5. Prepare result tables from existing aggregate summaries only; do not export
   row-level predictions, raw text, subject locators, learned parameters, or
   model files.
