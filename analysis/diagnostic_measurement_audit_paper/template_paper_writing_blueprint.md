# Template-Paper Writing Blueprint

Generated: 2026-08-25 UTC

Purpose: choose the 2-3 closest high-quality papers to emulate for the current
manuscript, then turn that choice into a concrete writing outline. This file is
a writing plan, not a new experiment report. Current numeric claims should
still follow the latest GitHub/local aggregate artifacts.

## Recommended Template Papers

### 1. Nguyen et al., ACL 2022

Source: https://aclanthology.org/2022.acl-long.578/

Paper: *Improving the Generalizability of Depression Detection by Leveraging
Clinical Questionnaires*.

Role as template: symptom-grounded generalization narrative.

Why it fits:

- It is a high-quality ACL long paper.
- It frames poor out-of-domain generalization and black-box depression
  detection as a clinical-grounding problem.
- It shows how to make clinical questionnaire structure central to an AI/NLP
  contribution without becoming a psychometrics paper.

What to borrow:

- The rhetorical move from generic depression prediction to clinically
  meaningful symptom evidence.
- The structure: problem with direct labels, clinically grounded intermediate
  representation, transfer/generalization evaluation, inspectability.
- The concise contribution style: symptom grounding improves generalization
  while making the model easier to inspect.

What not to copy:

- It works on social-media datasets and assumes PHQ symptom grounding is
  sufficiently stable for the transfer question being asked.
- It does not audit whether item-response mechanisms differ across clinical
  interview corpora.

How our paper extends it:

- We agree that symptoms are the right abstraction, but we add the missing
  target-validity step: before using shared symptoms as transferable anchors,
  audit whether their response mechanisms remain comparable across corpora.
- Our key sentence can be:

  "Symptom grounding improves the clinical interpretability of depression
  models, but cross-corpus clinical benchmarks additionally require validating
  whether shared symptoms are measured in comparable ways."

### 2. Chen et al., Pattern Recognition 2026 / arXiv 2025

Sources:

- https://arxiv.org/abs/2512.06447
- https://www.sciencedirect.com/science/article/abs/pii/S0031320326003328

Paper: *Towards Stable Cross-Domain Depression Recognition under Missing
Modalities*.

Role as template: foundation-era, multimodal, cross-domain depression framing.

Why it fits:

- It is the closest strong-backbone/cross-domain competitor: a multimodal LLM
  framework for heterogeneous depression data and missing modalities.
- It evaluates across multiple public depression datasets, including CMDC,
  DAIC-WOZ, and EATD, which overlaps the language of our paper.
- It represents the current direction reviewers will expect us to address:
  stronger multimodal foundation backbones, not only small encoders.

What to borrow:

- The opening motivation that real-world depression recognition involves
  heterogeneous corpora, modality availability differences, and cross-domain
  instability.
- The "unified framework" structure: heterogeneous inputs, shared
  representation/fusion module, multi-dataset validation.
- The idea that missing or heterogeneous modalities should be handled by a
  structured architecture rather than by ad hoc dataset pooling.

What not to copy:

- Do not turn our manuscript into a SOTA multimodal fusion paper.
- Do not claim we beat this line of work.
- Do not inherit the implicit assumption that once heterogeneous inputs are
  adapted, clinical targets can be treated as interchangeable.

How our paper extends it:

- SCD-MLLM mainly strengthens the representation side. Our framework says that
  even foundation representations require an explicit target contract:

  `Multimodal Foundation Encoder -> Shared Depression Representation -> Latent
  Symptom Layer -> Corpus-Specific Measurement Head`.

- Our key sentence can be:

  "Foundation models improve the modeling of heterogeneous behavioral inputs,
  but they do not by themselves validate the corpus-specific measurement
  mechanism that turns symptom evidence into PHQ or HAMD scores."

### 3. Zhang and Poellabauer, Findings EMNLP 2025

Source: https://aclanthology.org/2025.findings-emnlp.650/

Paper: *Mitigating Interviewer Bias in Multimodal Depression Detection: An
Approach with Adversarial Learning and Contextual Positional Encoding*.

Role as template: benchmark-validity audit plus constructive method.

Why it fits:

- It is a recent ACL-family paper on multimodal depression detection.
- It identifies a hidden benchmark/protocol problem, then proposes a model
  component to reduce the problem.
- It gives us a useful rhetorical neighbor: depression benchmarks can encode
  factors beyond participant depression evidence.

What to borrow:

- The move from "model performance" to "what hidden factor is the model using?"
- The framing that clinical interviews are structured interactions, so protocol
  context can affect generalization.
- The constructive stance: identify a bias, then design an architecture/eval
  protocol around it.

What not to copy:

- Its primary object is input-side interviewer/question bias.
- It still treats the clinical target as comparable once representation bias is
  controlled.

How our paper extends it:

- We extend benchmark-validity analysis from input/protocol bias to target
  measurement compatibility.
- Our key sentence can be:

  "Prior benchmark audits show that depression models can exploit interview
  protocol signals in the input; we show that cross-corpus evaluation also
  depends on the target side, where nominally aligned clinical labels may be
  generated by corpus-conditioned measurement mechanisms."

## Supporting Papers, Not Main Templates

- DepressionLLM: useful for proving that the field is already in the
  foundation-model era, especially with E-DAIC, CMDC, and EATD, but its
  venue/story is less ideal as the main structural template for us.
- Burdisso et al., ClinicalNLP 2024: very close benchmark-validity motivation
  for DAIC-WOZ therapist-prompt shortcuts; cite it, but do not make a workshop
  paper the main template.
- Multi-Probe Audit: very close audit spirit; useful positioning, but currently
  better as supporting context than as a top template if the goal is to emulate
  high-quality venue structure.

## Diagnosis Of The Uploaded Draft

The uploaded draft already has useful material:

- The `X -> Z -> Y_c` formulation is worth keeping.
- The dataset role table is close to the right setup.
- The three-RQ structure is usable if reframed around foundation-era benchmark
  validity.
- The foundation-backbone compatibility paragraph is directionally correct.

The main problems are narrative, not concept:

- The introduction explains the idea but does not create enough tension with
  the closest literature.
- Related work is too generic; it should be organized around the three template
  lanes above.
- The method section currently reads longer than the evidence warrants. It
  should be a framework and audit contract, not a claim of a fully optimized
  clinical deployment model.
- The experiment section should not feel like a list of everything we ran. It
  should stage three assumption tests.
- Limitations should be scoped and precise, not a self-defeating inventory.

## Core Paper Identity

Working title:

**Validate the Target Before Aligning Representations: A Measurement-Aware
Framework for Cross-Corpus Depression Detection**

Shorter title option:

**Measurement-Aware Cross-Corpus Depression Detection**

Paper type:

AI for mental health benchmark-validity audit plus lightweight constructive
framework.

Not the paper:

- Not a depression-detection SOTA paper.
- Not a pure psychometric measurement-invariance paper.
- Not a full end-to-end multimodal foundation-model training paper.
- Not a claim that all depression datasets measure different constructs.

Central claim:

Existing cross-corpus depression work increasingly improves heterogeneous
representation learning, modality fusion, and foundation backbones. These
advances leave a distinct target-validity assumption unresolved: nominally
aligned clinical labels may not preserve the same response mechanism across
corpora. We provide a systematic audit and a measurement-aware framework that
separates shared symptom evidence from corpus-specific measurement heads.

## Writing Strategy

The main text should maximize our strengths without overclaiming.

Emphasize:

- The target-validity assumption is underexplored in cross-corpus depression
  modeling.
- The dataset design is a gradient, not a random dataset pile:
  DAIC-WOZ/E-DAIC, E-DAIC/CMDC, CMDC/PDCH.
- Negative or bounded prediction results are diagnostic evidence that feature
  alignment and stronger encoders solve only part of the problem.
- The framework is compatible with foundation backbones and does not compete
  on generic fusion SOTA.

De-emphasize or move to supplement:

- Full historical MV details and retired experiment paths.
- Old BGE-only failure chains except where they motivate MV17a/MV22/MV23.
- Underpowered HAMD claims beyond "exploratory same-scale support".
- WavLM Large, HuBERT Large, VideoMAE, and end-to-end fine-tuning as completed
  experiments. They remain future large-compute extensions.
- Long data-governance or artifact-hygiene discussion. Keep a short
  subject-level split and target-contract paragraph in Methods; put detail in
  supplement or reproducibility notes.

Avoid:

- "Measurement invariance failed" as the headline.
- "Universal measurement shift".
- "We solve cross-corpus depression detection".
- "DAIC-WOZ is an independent third corpus relative to E-DAIC".
- Listing every negative result as a defect.

Preferred wording:

- "potential measurement heterogeneity"
- "corpus-conditioned response mechanisms"
- "target-validity assumption"
- "measurement-discrepancy gradient"
- "foundation backbones do not remove the need for target contracts"
- "observed-scale safety gate"

## Proposed Manuscript Outline

### Abstract

One paragraph, five moves:

1. Cross-corpus depression detection is increasingly evaluated with stronger
   multimodal and foundation representations.
2. Existing work mostly treats transfer as a representation problem and assumes
   that clinical labels are interchangeable once scales are nominally aligned.
3. We audit this assumption across a dataset/view gradient and propose a
   measurement-aware framework separating latent symptom evidence from
   corpus-specific measurement heads.
4. Experiments show representation heterogeneity, graded target-measurement
   differences, and prediction consequences under strong/fused backbones.
5. The implication: cross-corpus depression systems should validate target
   contracts in addition to aligning representations.

### 1. Introduction

Paragraph plan:

1. Foundation and multimodal depression detection are improving rapidly, but
   cross-corpus deployment remains hard.
2. The dominant framing is representation shift: learn invariant or fused
   features, then predict PHQ/HAMD-style labels.
3. The missing assumption is target comparability. Clinical scores are produced
   by instruments, items, raters/language, severity distributions, and
   acquisition protocols.
4. Benchmark-validity work has exposed input-side shortcuts, such as therapist
   prompts and interviewer context; target-side compatibility remains less
   studied.
5. Introduce our factorization:

   `P_D(X,Y | theta) = P_D(X | theta) P_D(Y | theta)`.

6. Present the measurement-aware framework:

   `X -> shared depression representation -> latent symptom layer ->
   corpus-specific measurement head -> PHQ/HAMD reconstruction`.

7. Preview the three experiments and the dataset/view gradient.
8. Contributions:

   - A cross-corpus depression benchmark-validity audit centered on target
     measurement compatibility.
   - A measurement-discrepancy gradient spanning same-lineage PHQ-8,
     cross-language PHQ shared symptoms, and exploratory same-scale HAMD.
   - Foundation-backbone and multimodal stress tests showing that stronger
     representations do not remove target-contract requirements.
   - A lightweight measurement-aware adaptation framework for future
     cross-corpus depression systems.

### 2. Related Work

Use four subsections:

1. Cross-domain and foundation-model depression detection.

   Anchor papers: SCD-MLLM, DepressionLLM, LLM spoken depression recognition,
   MPDD/P3HF. Message: the field is moving toward strong heterogeneous
   representation learning.

2. Symptom-grounded and interpretable depression detection.

   Anchor paper: Nguyen et al. ACL 2022. Add QuestMF and RED as item/evidence
   grounding neighbors. Message: symptom evidence is already recognized as a
   better abstraction than black-box scores.

3. Benchmark validity and protocol shortcuts.

   Anchor papers: Zhang and Poellabauer 2025, Burdisso et al. 2024,
   Multi-Probe Audit. Message: benchmarks encode hidden protocol factors; our
   extension is to target-side measurement compatibility.

4. Clinical measurement and scale comparability.

   Use PHQ/HAMD, measurement invariance, IRT/DIF, and scale-linking references
   sparingly. Message: we borrow the language of measurement, but our paper is
   an AI benchmark-validity audit rather than a full psychometric validation
   study.

End with positioning:

"Existing work asks how to learn more transferable depression
representations. We ask whether the clinical targets used to supervise those
representations are themselves comparable across corpora."

### 3. Measurement-Aware Framework

Keep this compact and visual.

3.1 Problem formulation:

- Direct model: `X -> Y_c`.
- Measurement-aware model: `X -> Z -> Y_c`.
- Factorization of input mechanism and target mechanism.

3.2 Target contracts:

- Corpus, scale, item set, language, protocol, modality, subject-level split,
  target role.
- DAIC-WOZ is a same-lineage PHQ-8 view/control relative to E-DAIC, not an
  independent pooled corpus.

3.3 Model interface:

- Frozen or trainable encoder.
- Shared depression representation.
- Latent symptom layer.
- Corpus-specific measurement heads.
- Optional few-shot target-head adaptation.

3.4 Evaluation gates:

- Representation identity.
- Measurement discrepancy.
- Prediction consequence.
- Observed-scale safety/calibration.

Do not make this section longer than the Results setup. The method is a
framework that organizes evidence, not the entire contribution by itself.

### 4. Corpora And Target Contracts

Main table: dataset/view, modality, language, assessment, role.

Recommended roles:

- E-DAIC: primary PHQ-8 development corpus.
- DAIC-WOZ: same-lineage PHQ-8 benchmark control/view.
- CMDC: cross-language PHQ shared-item comparison and HAMD subset.
- PDCH: exploratory same-HAMD control.
- MODMA, EATD, MPDD-AVG: external representation/population/protocol stress
  views.

Keep the table clean. Do not bury the reader in governance details.

### 5. Experiments

Organize results as three assumption tests.

#### Experiment 1: Foundation Representations Still Retain Corpus Identity

Question:

"Do strong text/audio/video/fused representations remove corpus identity from
depression feature spaces?"

Use:

- BGE-M3 and multilingual-E5 as established text contracts.
- Qwen3-Embedding as the stronger foundation text stress test.
- WavLM/wav2vec2/OpenFace/fused proxies from MV22/MV23 as lightweight
  foundation-era multimodal stress tests.

Main figure:

- Representation identity heatmap or probe summary.

Writing angle:

- Do not say corpus identity is always bad.
- Say corpus identity is recoverable enough that direct pooling/invariance
  should not be assumed.
- Strong encoders improve feature expressiveness but do not erase acquisition
  signatures.

#### Experiment 2: Measurement Compatibility Is A Gradient

Question:

"Do nominally aligned clinical measurements preserve comparable response
mechanisms across corpora?"

Use three levels:

- Level 1: DAIC-WOZ vs E-DAIC, same-lineage PHQ-8 control.
- Level 2: E-DAIC vs CMDC, cross-language PHQ shared-item analysis.
- Level 3: CMDC vs PDCH, exploratory same-HAMD control.

Main figure:

- Measurement-discrepancy gradient.

Supplement figures:

- PHQ shared-item item-level distributions.
- Severity-conditioned item deltas.
- HAMD exploratory item/residual patterns.

Writing angle:

- Do not write "PHQ/HAMD are invalid".
- Write that shared clinical constructs remain identifiable, but observed item
  responses can be corpus-conditioned.
- Emphasize that the DAIC-WOZ/E-DAIC control prevents an overclaim: the
  framework does not mechanically find shift everywhere.

#### Experiment 3: Prediction Consequences Under Strong Backbones

Question:

"When representation models are strong, do measurement-aware heads improve or
clarify cross-corpus prediction behavior beyond feature alignment?"

Baselines:

- ERM direct observed-label head.
- CORAL.
- MMD/DAN-style alignment.
- DANN.
- IRM proxy.
- GroupDRO proxy.
- Measurement-aware latent symptom / corpus-head model.

Main figure:

- Prediction consequence gate matrix or latent-target tradeoff plot.

Writing angle:

- The key comparison is not only MAE.
- Feature-alignment methods may reduce one kind of domain discrepancy while
  leaving observed-scale reconstruction/calibration unsafe.
- Measurement-aware adaptation is valuable when it improves target-head
  reconstruction, output-level behavior, or calibration even if feature
  identity remains partly recoverable.
- Negative/bounded rows are not defects; they show why target contracts are
  necessary in the foundation-model era.

### 6. Discussion

Recommended subsections:

1. Representation alignment is necessary but not sufficient.
2. Clinical depression scores are structured targets, not ordinary labels.
3. Foundation depression models need target contracts.
4. Practical benchmark-design implications.
5. Scope and limitations.

Limitations should be honest but scoped:

- HAMD same-scale analysis is exploratory because CMDC-HAMD has small N.
- MV22/MV23 are frozen-backbone/lightweight multimodal stress tests, not full
  end-to-end WavLM Large/HuBERT Large/VideoMAE training.
- The paper audits benchmark validity and proposes a framework; it does not
  claim clinical deployment readiness.

### 7. Conclusion

Close with the main conceptual shift:

"The next step for cross-corpus depression detection is not only stronger
representations, but also validated target contracts that specify how symptom
evidence is converted into corpus-specific clinical measurements."

## Main Figure And Table Plan

Main figures:

1. Framework overview: input mechanisms versus target measurement mechanism.
2. Dataset/view role map: seven corpus/views and their target contracts.
3. Representation identity heatmap: strong encoders still retain corpus
   signatures.
4. Measurement-discrepancy gradient: DAIC-WOZ/E-DAIC, E-DAIC/CMDC, CMDC/PDCH.
5. Prediction consequence gate matrix: direct prediction, feature alignment,
   latent target, measurement-aware head.

Supplement:

- PHQ shared-item item-level distribution and severity-conditioned deltas.
- HAMD same-scale exploratory item plot.
- Additional backbone/modality sensitivity tables.
- Retired or bounded MV paths only if needed for transparency.

Main tables:

1. Corpus target-contract table.
2. Closest related work and unresolved assumption table.
3. Baseline/method comparison table with both prediction and measurement-safety
   metrics.

## Paragraph-Level Borrowing Map

Use Nguyen et al. in:

- Introduction paragraph on symptom grounding.
- Related Work 2.2.
- Method motivation for latent symptom layer.

Use SCD-MLLM and DepressionLLM in:

- Introduction opening paragraph on the foundation-model era.
- Related Work 2.1.
- Experiment 1 and 3 motivation.

Use Zhang and Poellabauer plus Burdisso et al. in:

- Introduction paragraph on benchmark shortcuts.
- Related Work 2.3.
- Discussion paragraph distinguishing input-side protocol bias from target-side
  measurement heterogeneity.

## Best One-Sentence Story

Cross-corpus depression detection in the foundation-model era should not only
ask whether representations align across datasets, but also whether the
clinical targets used to supervise those representations obey comparable
measurement mechanisms.

## Immediate Writing Order

1. Rewrite the abstract and introduction first; these define the reviewer
   contract.
2. Rewrite Related Work around the three template lanes.
3. Compress Methodology into a framework section.
4. Rewrite Results as the three assumption tests above.
5. Only then polish Discussion and Limitations.

