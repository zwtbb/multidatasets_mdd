# Experiment Direction

Phase 1 freezes the research questions and paper hypotheses before freezing any
network architecture. Model design should serve the research frame below rather
than becoming the paper's primary contribution by itself.

The original project was organized around four research questions. That frame
still defines the experiment history, but the current paper is narrower: a
target measurement-validity audit with three contribution layers:

1. representation/protocol shift in `X`;
2. target measurement shift in `Y` given latent severity and dataset/group;
3. prediction shift from `X` to a harmonized latent target.

RQ1 label measurement is the core positive evidence. RQ2/Phase 3 supplies
motivating shortcut diagnostics. RQ3 is now a population/individual-difference
stress test, not a personality-aware method claim. RQ4 is a credibility layer,
not an evidence-retrieval method contribution.

## Frozen Research Questions And Hypotheses

| ID | Research question | Hypothesis | Main datasets |
| --- | --- | --- | --- |
| RQ1 | Do depression models measure the same construct across datasets and scales? | Direct shared symptom mapping is too strong under current Phase 5 evidence. Partial-invariance and total-anchored residual measurement are useful diagnostic frames, but current frozen-feature shallow implementations do not establish a transferable shared-symptom representation. MV10/MV11/MV19 are the primary bounded label-only PHQ common-structure and dataset-group threshold-shift evidence, with C02/C06 downgraded by observed-N finite-sample simulation. Corrected MV13/MV14 provide anchor-linked external mirt qualitative/uncertainty corroboration, while retaining configural convergence and finite-sample caveats. MV12/MV15/MV16 form a bounded/negative latent-target and calibration consequence chain rather than a method pass. | E-DAIC: PHQ-8; CMDC: PHQ-9 plus limited HAMD fields; PDCH: HAMD-17. MPDD and EATD stay stress/context datasets until item-level contracts improve. |
| RQ2 | Does the model depend on interview protocol and task content? | Depression predictions can be inflated by protocol shortcuts such as interviewer questions, question position, reading text, picture prompts, or emotion-valence materials; participant-centered and perturbation controls should separate symptom evidence from task content. | E-DAIC and CMDC: interviewer questions; MODMA: interview, reading, picture description, affective tasks; EATD-Corpus: positive, neutral, negative tasks |
| RQ3 | How do individual differences affect symptom expression? | Age, personality, health status, and gait/psychomotor context can moderate the relation between depression labels and behavioral features, but current evidence supports only heterogeneity/stress-test wording. Naive AVP/personality fusion and context calibration are not positive method components. | MPDD-AVG-2026 young subset, elderly subset, audio-video subset, personality/health metadata, and gait subset; equivalently MPDD-Young, MPDD-Elderly, and MPDD gait anchors |
| RQ4 | Are symptom predictions supported by observable evidence? | Evidence localization is bounded first-round credibility support. MV06 aggregate agreement can be reported with dataset-stratified kappa and bootstrap uncertainty, but one candidate remains incomplete and stronger RQ4 wording is blocked unless resolved or explicitly bounded. | E-DAIC, CMDC, PDCH |

For the current manuscript, the active evidence bundle is defined by
`analysis/phase5_minimal_validation/experiment_consolidation/`. Paper-core
evidence is `MV10/MV11/MV19` primary plus corrected `MV13/MV14` mirt
corroboration; paper-support evidence is
`MV02/MV04c/MV06/MV09/MV12/MV15/MV16/MV17a/MV18/MV20`, with the mirt
parameterization audit kept as a paper guardrail. Earlier weak or superseded
minimal validations remain retained only as historical diagnostics.

## Dataset Roles

The project should not train all datasets as one pooled corpus at the start.
Each dataset has a distinct role in the evaluation framework:

| Dataset | Primary role | Main task |
| --- | --- | --- |
| E-DAIC | Primary development dataset | PHQ-8 symptoms, total score, binary label, interviewer prompt bias |
| CMDC | Chinese cross-protocol and cross-language validation | External generalization on Chinese clinical interviews |
| PDCH | Real hospital consultation and HAMD validation | HAMD-17 symptoms and severity prediction |
| MODMA | Controlled speech-task stress test | Robustness across interview, reading, picture description, and affective tasks |
| EATD-Corpus | Chinese valence stress test | Positive, neutral, and negative audio-text consistency |
| MPDD-AVG 2026 | Individual-difference and psychomotor validation | Age, personality, health status, audio-video, and gait moderation |

## Experiment Boundary

The first milestone remains a repeatable data audit layer:

- `datasets/registry.yaml`
- local `datasets/manifests/*_subjects.csv` and `*_subjects.parquet`
- public `datasets/schemas/`
- public `datasets/examples/`
- `datasets/audit/dataset_inventory.md`
- `datasets/audit/label_distribution.csv`
- local `datasets/audit/file_integrity.csv` plus public schema/example
- `datasets/audit/leakage_check.md`

All splits must be subject-level. Different segments, tasks, or modalities from
the same subject must not cross train, validation, and test boundaries.

Architecture choices should stay frozen until a genuinely new data, feature, or
measurement mechanism changes the full-method gate. Under the current evidence,
the paper should prioritize a diagnostic measurement-audit frame: weak and
superseded minimal validations are retired from the active queue, label-only PHQ
    evidence is reported with the MV13/MV14 mirt parameterization boundary,
    MV14 convergence uncertainty, and MV19 finite-sample downgrade, protocol and content controls remain central for RQ2, moderator-aware
measurement heterogeneity remains a later RQ3 direction, and evidence
localization remains an RQ4 credibility layer.
