# Closest Related Work Gap Analysis

Generated: 2026-08-25 UTC
Project basis: latest GitHub/local HEAD `32bc69d9cfc865462fbfe78d3ff01f3f9e0c859a`

This note compares the current paper against the closest 20 papers or benchmark
sources. The purpose is not to write a generic related-work survey. It is to
identify exactly what nearby work already proves, where its assumptions remain
open, and what our measurement-aware audit/framework contributes.

## Our Current Position In One Sentence

Most nearby depression-detection work tries to improve or audit
`P_D(X | theta)`: representation quality, modality fusion, interviewer/protocol
shortcuts, evidence grounding, missing modalities, or foundation backbones. Our
paper adds the missing target-validity layer: whether nominally aligned clinical
labels preserve comparable `P_D(Y | theta)` across corpora, and how models
should use corpus-specific measurement heads when they do not.

## Closest Papers And Gaps

| # | Paper / source | Main finding or contribution | Remaining gap / vulnerability | What our paper solves or clarifies |
| ---: | --- | --- | --- | --- |
| 1 | [Nguyen et al., ACL 2022, questionnaire-grounded depression detection](https://aclanthology.org/2022.acl-long.578/) | Uses PHQ-9 symptom grounding to improve out-of-domain depression detection over social-media datasets. Shows symptom grounding can help generalization. | Assumes the questionnaire symptom meanings are stable enough across datasets; does not audit item-response mechanisms or corpus-specific scale behavior. | We agree that symptoms are the right abstraction, but add item-level PHQ shared-item audits, severity-conditioned response analysis, IRT/finite-sample caveats, and corpus-specific measurement heads. |
| 2 | [Mandal et al., CLPsych 2025, QuestMF](https://aclanthology.org/2025.clpsych-1.4/) | Predicts E-DAIC PHQ item/question scores with question-wise modality fusion and ordinal loss, improving interpretability within a single benchmark. | Item-level modeling is within E-DAIC; it does not ask whether item scores from another corpus are comparable targets. | We shift item-level modeling from within-corpus interpretability to cross-corpus target comparability. |
| 3 | [Zhang et al., Findings ACL 2025, RED](https://aclanthology.org/2025.findings-acl.517/) | Retrieval-augmented explanations ground depression predictions in clinical interview evidence and reduce hallucinated post-hoc explanations. | Evidence grounding does not prove the clinical target is comparable across corpora or scales. | Our MV06 evidence work becomes a credibility layer, while the main novelty is target measurement validity and comparability gates. |
| 4 | [Burdisso et al., ClinicalNLP 2024, DAIC-WOZ therapist prompts](https://aclanthology.org/2024.clinicalnlp-1.8/) | Shows models can exploit therapist/interviewer prompts in DAIC-WOZ and may learn shortcut regions rather than participant evidence. | Strong protocol-shortcut audit, but still mostly about the input/acquisition side. It does not audit PHQ/HAMD target measurement comparability. | We use similar benchmark-validity instinct but extend it from prompt leakage in `X` to clinical label comparability in `Y`. |
| 5 | [Zhang and Poellabauer, Findings EMNLP 2025, interviewer bias](https://aclanthology.org/2025.findings-emnlp.650/) | Uses dialogue-level modeling plus adversarial question-type invariance to reduce interviewer-bias effects across interview settings. | Solves a representation/protocol bias problem; the target label remains treated as comparable after representation debiasing. | Our framework says adversarially removing protocol signals is useful but insufficient unless `P_D(Y | theta)` is also audited. |
| 6 | [Ishikawa and Duke, arXiv 2026, Multi-Probe Audit](https://arxiv.org/abs/2605.23977) | Audits clinical-interview depression benchmarks with multiple probes: split stability, leaderboard fragility, external validation, and symptom-dense vs symptom-light slices. | Very close benchmark-validity neighbor, but its emphasis is evaluation reliability and symptom evidence, not psychometric measurement heterogeneity across clinical targets. | Our differentiator should be stated clearly: real clinical corpora plus item-level scale behavior plus model-consequence gates. |
| 7 | [Danylenko and Unold, Applied Sciences 2025, DAIC-WOZ pitfalls](https://www.mdpi.com/2076-3417/16/1/422) | Reviews common ML pitfalls and recommendations for depression severity estimation on DAIC-WOZ. | Useful benchmark hygiene, but mainly DAIC-WOZ-centered and not a cross-scale/cross-corpus target-measurement audit. | We generalize from DAIC-WOZ usage hygiene to a multi-corpus target-contract framework. |
| 8 | [Patapati et al., ICMI Companion 2025, Most DAIC-WOZ classifiers are invalid](https://dl.acm.org/doi/10.1145/3747327.3763034) | Preliminary reproducibility/audit work arguing many DAIC-WOZ classifiers may learn non-task-specific or disorder-general cues. | Powerful warning about benchmark misuse, but does not propose PHQ/HAMD item-level measurement heads or compare measurement gradients. | Our paper can cite this as support for benchmark-validity urgency, then claim the unaddressed target-validity layer. |
| 9 | [Chen et al., Pattern Recognition 2026, SCD-MLLM](https://doi.org/10.1016/j.patcog.2026.113367) / [arXiv](https://arxiv.org/abs/2512.06447) | Uses multimodal LLM adapters and adaptive fusion for stable cross-domain depression recognition under missing modalities across several heterogeneous datasets. | Strongest representation/fusion competitor. It addresses heterogeneous inputs and missing modalities, but still treats depression targets as usable cross-domain labels once inputs are adapted. | We should not compete on fusion SOTA. Our novelty is that even strong/fused representations require explicit target contracts, measurement heads, and observed-scale comparability checks. |
| 10 | [Teng et al., Displays 2026, DepressionLLM](https://doi.org/10.1016/j.displa.2025.103304) | Uses foundation models for interpretable multimodal depression detection, including cross-dataset/foundation-model framing. | Foundation-model strength and interpretability do not by themselves validate clinical target interchangeability. | MV22/MV23 directly answer this: stronger Qwen/audio/video-proxy/fused representations change errors but do not remove target-validity gates. |
| 11 | [Li et al., Frontiers in Computer Science 2025, LLMs for spoken depression recognition](https://www.frontiersin.org/journals/computer-science/articles/10.3389/fcomp.2025.1629725/full) | Maps Wav2Vec audio features into LLM-style processing and injects psychological knowledge for DAIC-WOZ severity prediction. | Single-benchmark performance and knowledge injection; no cross-corpus measurement audit. | Our paper can say psychological knowledge/foundation backbones help `X -> representation`, but target measurement still needs audit. |
| 12 | [PTTSD, arXiv 2026, probabilistic textual time-series depression detection](https://arxiv.org/abs/2511.04476) | Adds calibrated distributional PHQ-8 predictions over utterance sequences for DAIC-WOZ/E-DAIC-style text time series. | Calibration is about predictive uncertainty for a target; it does not test whether the target itself is comparable across corpus families or scales. | We separate predictive calibration from measurement comparability and observed-scale validity across corpora. |
| 13 | [Fu et al., AAAI 2026, P3HF](https://dl.acm.org/doi/10.1609/aaai.v40i3.37159) / [arXiv](https://arxiv.org/abs/2511.12460) | Personality-guided hypergraph-former modeling improves MPDD-Young depression classification, emphasizing individual-aware multimodal representations. | Strong personality-aware method, but its novelty is individual-difference representation/fusion, not target measurement validity. | We should keep MPDD/personality as heterogeneity and calibration stress evidence, not claim personality-aware modeling as our contribution. |
| 14 | [Fu et al., ACM MM 2025, MPDD Challenge](https://arxiv.org/abs/2505.10034) / [official challenge](https://hacilab.github.io/MPDDChallenge.github.io/) | Builds a multimodal personality-aware benchmark with age/personality/health context to address population diversity. | Highlights individual differences but does not solve cross-scale PHQ/HAMD/SDS target comparability. | Our RQ3 population stress tests align with this motivation, while our main claim remains clinical target-contract validity. |
| 15 | [Ma et al., Frontiers in Psychiatry 2021, PHQ-9 vs HAMD-17](https://www.frontiersin.org/journals/psychiatry/articles/10.3389/fpsyt.2021.747139/full) | IRT analysis shows PHQ-9 and HAMD-17 are related but differ in discrimination, severity assessment, and item behavior. | Clinical psychometric comparison, not tied to multimodal ML cross-corpus generalization. | We connect this scale-caution evidence to actual depression benchmarks, item-level corpus comparisons, and prediction consequences. |
| 16 | [Galenkamp et al., BMC Psychiatry 2017, PHQ-9 invariance in HELIUS](https://link.springer.com/article/10.1186/s12888-017-1506-9) | Finds PHQ-9 measurement invariance across ethnic groups in a large European population study. | Positive invariance evidence under a particular population/survey setting; not an interview-corpus, language/protocol, or PHQ-8/PHQ-9/clinical-corpus comparison. | We do not claim PHQ is generally invalid; we show corpus-conditioned item behavior under benchmark-specific acquisition differences. |
| 17 | [Patel et al., Depression and Anxiety 2019, PHQ-9 invariance across U.S. groups](https://pubmed.ncbi.nlm.nih.gov/31356710/) | Finds PHQ-9 acceptable for meaningful comparisons across sex, race/ethnicity, and education in NHANES. | Again positive PHQ invariance in epidemiological data; it does not test cross-corpus interview settings or downstream ML transfer. | This is useful as contrast: PHQ can be invariant in some settings, so our claim should be "benchmark-specific measurement heterogeneity," not "PHQ is universally unstable." |
| 18 | [Zhou et al., Journal of Clinical Epidemiology 2026, depression scale linking](https://pubmed.ncbi.nlm.nih.gov/41794387/) | Shows significant correlations but systematic differences among HAMD-17, HAMD-6, QIDS-SR16, and PHQ-9; provides equipercentile linking. | Cross-scale harmonization is at the score level, not item-level corpus response mechanisms or multimodal transfer validity. | Our measurement-aware heads are an ML analogue: score/linking intuition plus item-level and corpus-specific validity gates. |
| 19 | [De Duro et al., arXiv 2026, NLP Psychometrics](https://arxiv.org/abs/2608.07316) | Argues NLP mental-health models should ask what psychological constructs they measure; proposes NLP Psychometrics. | Conceptual and language-centered; less grounded in real clinical corpora, item-level scale behavior, and cross-corpus prediction consequences. | Our paper is the empirical benchmark-validity counterpart: real clinical corpora + PHQ/HAMD item behavior + model consequence experiments. |
| 20 | [Gratch et al., LREC 2014, DAIC](https://aclanthology.org/L14-1421/), [USC ICT DAIC/E-DAIC access page](https://dcapswoz.ict.usc.edu/), and [AVEC 2017 challenge](https://dl.acm.org/doi/10.1145/3133944.3133953) | Establish the DAIC/DAIC-WOZ/E-DAIC benchmark lineage and standard multimodal depression-evaluation setup. | The benchmark lineage encourages repeated use, but can invite over-pooling and mistaken independence between DAIC-WOZ and E-DAIC. | We explicitly treat DAIC-WOZ as a seventh dataset/view and same-lineage PHQ-8 control, not as an independent corpus to pool with E-DAIC. |

## What Reviewers May Say, And Our Best Response

### 1. "This is just another benchmark audit."

Closest neighbors: Multi-Probe Audit, DAIC-WOZ prompt validity, Common
Pitfalls, invalid-classifier reproducibility work.

Best response:

- Those papers mainly audit evaluation, splits, prompt/protocol leakage, or
  benchmark reproducibility.
- We audit the clinical target itself: PHQ/HAMD item behavior, measurement
  gradients, finite-sample psychometric uncertainty, and downstream
  measurement-head consequences.
- This makes the paper an AI mental-health benchmark-validity audit with a
  constructive measurement-aware modeling framework.

### 2. "Foundation/multimodal models already solve cross-domain depression."

Closest neighbors: SCD-MLLM, DepressionLLM, LLM spoken depression recognition,
P3HF, MPDD.

Best response:

- These works improve representation, fusion, missing-modality robustness,
  explainability, or individual-aware modeling.
- Our MV22/MV23 are deliberately bounded stress tests showing that stronger
  Qwen/text, audio proxies, OpenFace video proxies, and lightweight fusion
  change transfer tradeoffs but do not remove the target-validity gate.
- The claim is not "small models beat foundation models." The claim is:
  foundation models still require measurement-aware target contracts and
  corpus-specific heads.

### 3. "PHQ has known measurement invariance, so your PHQ result is suspect."

Closest neighbors: Galenkamp 2017 and Patel 2019.

Best response:

- Those are important positive controls showing PHQ can be invariant in some
  population/survey contexts.
- Our claim is narrower and more benchmark-specific: E-DAIC/CMDC differ in
  language, population, clinical/interview setting, PHQ-8 vs PHQ-9 form, and
  acquisition protocol.
- We also include DAIC-WOZ/E-DAIC as a low-discrepancy same-lineage PHQ-8
  control, preventing the overclaim that the pipeline always finds shift.

### 4. "PHQ-8 vs PHQ-9 is just a scale artifact."

Closest neighbors: PHQ/HAMD IRT and 2026 scale-linking work.

Best response:

- We restrict E-DAIC/CMDC to the eight shared PHQ items, avoiding a pure PHQ-8
  vs PHQ-9 total-score comparison.
- MV21 adds severity-conditioned item-level descriptions.
- CMDC/PDCH adds exploratory same-HAMD evidence, showing the issue is not only
  PHQ-8/PHQ-9 form mismatch.

### 5. "Your negative prediction results weaken the paper."

Best response:

- They should be framed as stress-test evidence, not failure.
- The negative/bounded results show that representation alignment, latent
  target harmonization, and localized calibration affect different parts of the
  problem.
- This supports the framework's separation of encoder, latent symptom layer,
  corpus-specific measurement head, and validity gates.

## Best Related-Work Structure For The Paper

1. **Cross-domain/foundation depression detection:** SCD-MLLM, DepressionLLM,
   LLM spoken depression recognition, P3HF/MPDD.
2. **Symptom-grounded and interpretable depression detection:** ACL 2022
   questionnaire grounding, QuestMF, RED, PTTSD.
3. **Benchmark validity and protocol shortcut audits:** DAIC-WOZ prompt
   validity, interviewer bias, Multi-Probe Audit, DAIC-WOZ pitfalls/invalid
   classifiers.
4. **Clinical measurement and psychometrics:** PHQ/HAMD IRT, PHQ invariance
   studies, scale linking, NLP Psychometrics.

## Sharpened Contribution Claim

The clean contribution statement after this comparison should be:

> Existing cross-corpus depression work increasingly improves heterogeneous
> representation learning, modality fusion, evidence grounding, and benchmark
> evaluation. We show that these advances leave a distinct target-validity
> assumption unresolved: nominally aligned clinical labels may not preserve the
> same response mechanism across corpora. We provide a registry-governed
> empirical audit and a measurement-aware framework that separates shared
> symptom evidence from corpus-specific measurement heads, making cross-corpus
> depression detection more measurement-valid in the foundation-model era.

## What We Should Avoid Claiming

- Do not claim we beat SCD-MLLM, DepressionLLM, P3HF, or QuestMF as a generic
  performance method.
- Do not claim PHQ is universally non-invariant.
- Do not claim DAIC-WOZ is independent from E-DAIC.
- Do not claim WavLM Large, HuBERT Large, VideoMAE, or end-to-end multimodal
  fine-tuning has been executed.
- Do not write the negative RQ3 outcomes as defects; write them as validity-gate
  evidence.
