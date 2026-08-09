# Experiment Direction

Phase 1 freezes the research questions and paper hypotheses before freezing any
network architecture. Model design should serve the research frame below rather
than becoming the paper's primary contribution by itself.

The paper is organized around four research questions. RQ1-RQ3 are the main
contributions; RQ4 is a credibility evaluation layer that checks whether the
predictions made for the first three questions are supported by observable
evidence.

## Frozen Research Questions And Hypotheses

| ID | Research question | Hypothesis | Main datasets |
| --- | --- | --- | --- |
| RQ1 | Do depression models measure the same construct across datasets and scales? | Direct shared symptom mapping is too strong under current Phase 5 evidence; the next method hypothesis is partial measurement invariance: shared latent symptom constructs with scale-specific DIF/loading-threshold deviations should transfer better than total-score or fixed-map heads. | E-DAIC: PHQ-8; CMDC: PHQ-9 plus limited HAMD fields; PDCH: HAMD-17. MPDD and EATD stay stress/context datasets until item-level contracts improve. |
| RQ2 | Does the model depend on interview protocol and task content? | Depression predictions can be inflated by protocol shortcuts such as interviewer questions, question position, reading text, picture prompts, or emotion-valence materials; participant-centered and perturbation controls should separate symptom evidence from task content. | E-DAIC and CMDC: interviewer questions; MODMA: interview, reading, picture description, affective tasks; EATD-Corpus: positive, neutral, negative tasks |
| RQ3 | How do individual differences affect symptom expression? | Age, personality, health status, and gait/psychomotor context can moderate the relation between depression labels and speech, facial, gait, and other behavioral features, so a transferable model must evaluate these moderators instead of treating all subjects as one homogeneous population. | MPDD-AVG-2026 young subset, elderly subset, audio-video subset, personality/health metadata, and gait subset; equivalently MPDD-Young, MPDD-Elderly, and MPDD gait anchors |
| RQ4 | Are symptom predictions supported by observable evidence? | Total-score or severity predictions are credible only when they can be localized to corresponding linguistic, acoustic, facial, or gait evidence matching the predicted symptom constructs. | E-DAIC, CMDC, PDCH |

RQ1, RQ2, and RQ3 are the main contributions. RQ4 is a credibility and evidence
evaluation layer for the first three questions, not a fourth large independent
modeling module.

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

Architecture choices should stay unfrozen until the RQ-aligned measurement
contracts are stable: partial-invariance latent measurement for RQ1, protocol
and content controls for RQ2, moderator-aware measurement heterogeneity for
RQ3, and evidence-localized explanations for RQ4.
