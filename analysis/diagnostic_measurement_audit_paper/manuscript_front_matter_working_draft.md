# Before Aligning Representations, Align the Target

## Working Draft Status

This file is a human-editing working draft for the manuscript front matter:
Introduction, Related Work, Problem Definition, Dataset/Protocol, and Methods
Framework. It is derived from aggregate-only project artifacts and the current
citation registry. It does not replace the generated evidence scaffold in
`manuscript_draft.md`, does not add new experiment results, and does not
authorize claims beyond the Phase 5 full-method gate.

Citation keys are inserted in Pandoc-style form. Bibliography primary-source
verification is complete in the session-101 ledger; target-venue style and a
final pre-submission metadata refresh remain open.

## Introduction

Cross-corpus depression detection is usually framed as a representation problem:
given speech, language, facial behavior, gait, or multimodal interview signals,
learn a model that remains accurate when the corpus, protocol, language, or
population changes. This framing is natural. Clinical-interview corpora such as
DAIC include audio, video, questionnaires, transcripts, and verbal or
non-verbal annotations collected in human, human-controlled, and autonomous
interview settings [@gratch2014distress]. Modern depression-detection systems
therefore face a difficult `X`-side problem: the observable signal depends on
the interviewer, the task, the recording setting, the language, the modalities
available at test time, and the population sampled by each corpus.

But depression detection also has a target-side problem. The observed label is
not the latent construct itself. It is a scale response, severity total,
binary threshold, clinical rating, or item vector produced under a particular
dataset and protocol. Let `D` denote dataset, protocol, and population; `X` the
observed multimodal signal; `Y` the observed scale response; and `theta` the
latent depressive severity or symptom construct. The joint target of a
cross-corpus model can be written as:

```text
P(X,Y | theta,D) = P(X | theta,D) P(Y | theta,D)
```

Most domain-generalization work attacks the first factor. It asks whether
representations can suppress protocol artifacts, handle missing modalities, or
preserve symptom evidence across corpora. This paper asks the second question:
when two datasets use labels that appear clinically related, do they measure
the same target function well enough for representation alignment to be
interpretable? If `P(Y | theta,D)` changes across datasets, then learning a
representation with low dataset identity does not by itself prove that the
model has learned a comparable depression construct.

This distinction matters because the field is moving in both directions at
once. Questionnaire-grounded modeling has shown that constraining depression
prediction by PHQ-9 symptoms can improve out-of-distribution generalization
relative to unconstrained text models [@nguyen2022improving]. Interviewer-bias
work has shown that question type and dialogue context can become nuisance
signals, motivating adversarial or context-aware representation learning
[@zhang2025interviewer]. Multimodal robustness work continues to target
heterogeneous inputs and cross-scenario generalization. At the same time,
recent NLP psychometrics work argues that mental-health prediction models
should state what they measure, not only how well they predict
[@deduro2026nlppsychometrics]. Our audit sits at that intersection: it uses
real clinical and interview corpora, item-level scale behavior, and
cross-corpus prediction consequences to ask whether target measurement is
aligned before claiming that representations are aligned.

The contribution is therefore diagnostic rather than architectural. We do not
claim a new full depression-detection method, and the current full-method gate
keeps M0/M1/M2/M3 construction blocked. Instead, we show that a governed
sequence of dataset audits, shortcut diagnostics, label-only psychometric
checks, multilingual feature-contract sensitivities, and claim gates supports
a bounded but publishable conclusion: cross-corpus depression detection needs
target alignment, not only representation alignment.

## Related Work

### Clinical-Interview And Multimodal Depression Detection

Clinical-interview datasets provide rich behavioral evidence, but they also
carry protocol and setting signatures. DAIC-style corpora were designed to
support psychological-distress research with interviews, questionnaires,
transcripts, and multimodal recordings [@gratch2014distress]. CMDC, PDCH,
MODMA, EATD-Corpus, and MPDD extend this landscape with Chinese clinical
interviews, hospital consultations, controlled speech tasks, valence
elicitation, and individual-difference context. These resources make
cross-corpus analysis possible, but they also make naive pooling risky:
dataset, language, task, and label contracts change together.

Recent robust multimodal systems address this heterogeneity primarily as an
input-side problem. A generic cross-domain multimodal detector such as
SCD-MLLM occupies the space of unifying heterogeneous inputs and improving
generalization across multiple depression datasets [@chen2025scd]. Related
interviewer-bias work directly models question type and dialogue context as
protocol nuisance factors [@zhang2025interviewer]. These studies motivate our
representation/protocol shift layer, but they usually do not make target
measurement comparability the central object of analysis.

### Symptom Grounding And Evidence Localization

Questionnaire-grounded models provide an important bridge from black-box
classification to clinically interpretable prediction. Nguyen et al. show that
grounding text models in PHQ-9 symptoms can improve out-of-distribution
generalization on social-media depression tasks [@nguyen2022improving].
Question-wise multimodal fusion and item-level PHQ prediction work similarly
show that symptom-level structure can be useful for E-DAIC-style modeling
[@mandal2025questmf]. Evidence-retrieval systems such as RED strengthen the
interpretability side by linking predictions to transcript evidence
[@zhang2025red].

Our paper agrees with the symptom-grounding premise but adds a caution: symptom
grounding is not enough if the observed symptom labels are not measurement
equivalent across datasets. We therefore treat evidence localization as a
credibility layer rather than the main novelty. MV06 supports bounded
aggregate evidence-review credibility, while the core claim remains target
measurement validity.

### Measurement Invariance And Psychometrics

Psychometric work provides the vocabulary for the target-side problem. PHQ-9
measurement-invariance and DIF studies show that group comparisons require
testing whether item behavior changes across populations before interpreting
raw score differences [@galenkamp2017measurement; @patel2019measurement;
@delamain2024measurement]. PHQ and HAMD scores can be related while still
reflecting different item discriminations or severity emphasis
[@ma2021phqhamd], and cross-scale linking studies likewise warn that
correlated depression scales are not automatically interchangeable
[@zhou2026depression].

The present audit brings that measurement-invariance logic into cross-corpus
machine learning. MV10/MV11/MV19 are label-only PHQ analyses, and corrected
MV13/MV14 provide an external `mirt` corroboration layer using graded-response
IRT concepts [@samejima1969graded; @chalmers2012mirt]. The goal is not to
replace clinical psychometrics, but to prevent multimodal prediction claims
from assuming `P(Y | theta,D) = P(Y | theta)` without evidence.

### Benchmark Audits, Criterion Contamination, And NLP Psychometrics

Recent benchmark-audit work and criterion-contamination analyses make the
timing of this paper useful. Multi-probe depression benchmark audits overlap
our Phase 3 concern that benchmark performance can reflect dataset artifacts
[@ishikawa2026multiprobe]. Mirror/non-mirror criterion-contamination work
motivates testing whether language models recover label wording rather than
independent evidence [@li2025mirror]. NLP psychometrics explicitly argues that
mental-health NLP models should specify what they measure
[@deduro2026nlppsychometrics].

Our differentiator is empirical scope and target granularity: real clinical
and interview corpora, item-level PHQ behavior, corrected multi-group IRT
checks, finite-sample sensitivity, and downstream `X -> theta` prediction
consequences under multilingual feature contracts.

## Problem Definition

We study cross-corpus depression detection under dataset-indexed observation
and measurement. For subject `i` in dataset or protocol group `D_i`, let
`X_i` be the available multimodal evidence and let `Y_i` be the observed
depression label. Depending on the dataset, `Y_i` may be an item response
vector, total score, severity class, or binary threshold. Let `theta_i` denote
the latent depressive severity or symptom construct that motivates the label.

The conventional representation goal can be summarized as finding a function
`f(X)` or representation `Z` such that prediction of `Y` generalizes across
`D`, often by reducing dataset information in `Z`. This is necessary but not
sufficient. If the item response or threshold function varies by dataset, then
two subjects with the same latent `theta` can have different expected labels:

```text
P(Y | theta,D = d1) != P(Y | theta,D = d2)
```

In that case, a pooled predictor may optimize incompatible targets, and a
dataset-invariant representation can still produce labels that are not
construct-comparable. We therefore separate three questions:

1. Representation/protocol shift: how much dataset, protocol, task, language,
   and population information remains in `X` or learned features?
2. Target measurement shift: do scale items, thresholds, and anchor structures
   behave consistently across dataset groups after accounting for severity?
3. Prediction consequences: after measurement harmonization, does `X -> theta`
   transfer in a way that is useful on the observed scale and not just less
   dataset-identifiable at the output layer?

This definition intentionally keeps strong positive claims difficult. A method
cannot claim transferable shared-symptom representation merely because a
pooled model performs well, because identity probes weaken, or because
low-dimensional outputs hide dataset membership. It must also show that the
target measurement contract is comparable or explicitly model the way it is
not.

## Dataset And Protocol Scope

The project uses a registry-first dataset contract. Each corpus is assigned a
role before modeling, and all splits remain subject-level. The current
manuscript scope covers E-DAIC, CMDC, PDCH, MODMA, EATD-Corpus, and
MPDD-AVG-2026, with DAIC-WOZ used only as an AVEC2017 Wizard-of-Oz benchmark
and same-lineage PHQ-8 control. E-DAIC is the extended DAIC dataset. DAIC-WOZ
must not be pooled with E-DAIC as an independent corpus because their subjects
and source lineage overlap heavily.

E-DAIC is the primary development corpus, with PHQ-8 item supervision on
train/dev subjects and interview protocol risk from prompt and speaker
structure. CMDC is the Chinese cross-protocol and cross-language validation
corpus, with PHQ-9 item supervision and a limited HAMD-17 sanity subset.
PDCH supplies real hospital consultation data and the strongest HAMD-17
item-level clinical validation. MODMA and EATD-Corpus serve as task and
valence stress tests; their current contracts are total/severity oriented
rather than item-level construct bridges. MPDD is used as a population and
psychomotor-context stress test, not as a personality-aware method
contribution, because personality-aware MPDD modeling is already a strong
nearby contribution in P3HF [@fu2026p3hf].

This role assignment is part of the method. It prevents the paper from treating
all depression corpora as exchangeable rows in one pooled benchmark. It also
defines which claims each dataset can support: PHQ item-level measurement for
E-DAIC/CMDC, HAMD diagnostic evidence for PDCH and exploratory CMDC/PDCH
same-scale checks, task/protocol stress for MODMA, negative SDS stress for
EATD, and heterogeneity stress for MPDD.

The public release boundary follows the same logic. Raw media, transcripts,
real row-level manifests, local file paths, private annotation workbooks,
learned embeddings, fitted parameters, theta scores, row predictions, and
bootstrap draws remain local-only. The public-facing repository contains code,
schemas, synthetic examples, aggregate audit reports, claim gates, and
paper-critical summaries that pass artifact-hygiene checks.

## Methods Framework

### Governance And Reproducibility Floor

The analysis begins with dataset governance rather than modeling. The registry
defines dataset paths, roles, modalities, protocols, label scales, split
contracts, and release boundaries. Generated manifests and audits become the
experiment interface; raw-directory scans are disallowed unless the registry
and manifest layer is intentionally updated. Phase 2 then supplies a unified
baseline floor over applicable simple unimodal and fusion models. These runs
are not the main contribution, but they establish that later diagnostic claims
sit on completed, subject-level baselines.

### Representation And Protocol Diagnostics

Phase 3 asks whether shortcut information is recoverable from common feature
spaces or protocol slices. Dataset-identity probes, E-DAIC/CMDC question and
position controls, MODMA task transfer, EATD valence checks, and MPDD
heterogeneity diagnostics motivate the claim boundary. The key point is not
that every dataset signal is spurious. It is that direct pooled performance is
not sufficient evidence of a shared depression construct unless dataset,
protocol, task, and population signatures are measured and bounded.

### Target Measurement Layer

The core measurement layer is label-only before it is multimodal. MV10 screens
E-DAIC PHQ-8 and CMDC PHQ-9 item behavior for common structure and candidate
anchors. MV11 formalizes the shared PHQ item analysis with graded-response IRT
confirmation. MV19 quantifies observed-sample finite-sample sensitivity,
downgrading C02/C06 from robust standalone DIF to repeated but
finite-sample-bounded dataset-group threshold-shift evidence. Corrected
MV13/MV14 then provide external `mirt` corroboration under an audited
anchor-linked focal mean/variance contract, while retaining convergence and
finite-sample caveats.

### Prediction Consequence Layer

Only after the target layer is bounded do we ask whether `X -> theta` transfers.
The legacy Chinese-BGE feature chain is retained as diagnostic history because
the old E-DAIC feature contract used `BAAI/bge-small-zh-v1.5`, a Chinese model
card, on English transcripts [@baai2026bgesmallzh]. MV17a replaces the
manuscript-facing feature contract with BGE-M3 as the primary multilingual
encoder and multilingual-E5 as sensitivity [@baai2026bgem3;
@wang2024multilinguale5]. Both contracts reproduce the blocked pattern:
within-dataset theta prediction is learnable and output identity can drop, but
observed-scale safety and theta-conditioned feature invariance remain blocked.

### Claim Gates And Stop Rules

Every result is routed through claim gates rather than prose optimism. The
current full-method gate reads 45 Phase 5 summaries and remains
`blocked_but_publishable_diagnostic_direction`, with
`full_method_allowed=false`. MV18, MV20, MV16, MV06, EATD, and MPDD are
therefore supporting, bounded, or negative evidence, not new method
authorization. The stop rules are explicit: no extra shallow BGE heads,
projection dimensions, criterion-overlap threshold tuning, contamination-aware
architectures, personality-gating methods, or EATD valence-adversarial modules
unless a new predeclared mechanism changes the gate.
