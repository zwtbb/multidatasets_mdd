# Audit Target Comparability Before Aligning Representations: A Cross-Corpus Measurement Audit of Depression Detection

## Abstract

Cross-corpus depression detection is often treated as a representation-transfer
problem: if linguistic, acoustic, visual, or multimodal features become
stronger, depression predictions should transfer across datasets. We argue
that this view leaves the comparability of the observed target unchecked.
Depression scores are structured measurements, and nominally aligned PHQ or
HAMD labels may not preserve the same response mechanism across corpora. We
therefore study cross-corpus depression detection as a target-comparability and
measurement-contract audit: before aligning representations, audit whether the
target scores can support comparable interpretation. We do not test the
construct, criterion, or clinical validity of PHQ, HAMD, or SDS themselves.

Across our corpus suite, the audit is organized around three target-contract
contrasts. The same-lineage DAIC-WOZ/E-DAIC PHQ-8 control is nearly identical;
the cross-language E-DAIC/CMDC PHQ shared-item comparison shows substantial
common structure but imperfect item behavior; and the CMDC/PDCH same-HAMD
contrast provides exploratory support that measurement differences are not
only a PHQ-form issue. We then instantiate a measurement-aware ordinal model on
frozen multimodal foundation representations and audit it against calibrated
baselines that match the target-label budget and trainable shared-layer access
under fixed, comparable optimization schedules. This fair ablation changes the
interpretation of the
original large gain over a frozen corpus-specific-head comparator: the robust
effect is target-label calibration with shared-layer adaptation, not an
independently verified corpus-specific measurement pathway. Under repeated
subject-level target-calibration splits, a target-only direct MLP gives the
lowest Macro Item MAE at both default budgets, while source-plus-target
calibrated rows more often improve calibration-in-the-large than item
reconstruction. The ordinal pathway is a constructive framework instance, but
corpus-specific ordinal parameterization is not uniformly superior to
target-only, generic calibrated, shared-ordinal, or direct multitask
alternatives. Item-targeted and fixed-latent simulation analyses show at most a
bounded, item-local role for corpus-specific heads under the current
calibration budgets. Stronger encoders remain useful, but cross-corpus
depression models should not treat representation alignment, target
calibration, or measurement modeling as interchangeable evidence.

## 1 Introduction

Automatic depression detection has moved quickly from single-dataset
classification toward cross-corpus and multimodal learning. Public interview
benchmarks such as DAIC-WOZ and E-DAIC have made it possible to train models on
language, speech, facial behavior, and interaction cues collected during
semi-structured clinical interviews [@gratch2014distress; @uscict2026daic].
At the same time, newer datasets bring different languages, hospital settings,
controlled speech tasks, emotional contexts, and population characteristics
into the same research conversation. This broader data landscape is exactly
what the field needs. It is also what makes a simple question hard: when a
model trained on one depression corpus is evaluated on another, what is
actually being transferred?

The dominant answer has been representation transfer. If the main difficulty is
that corpora differ in language, acoustic conditions, interview protocol,
camera setup, or population, then the natural solution is to learn better
features. This has led to a rich line of work on multimodal fusion, domain
adaptation, interviewer-bias mitigation, evidence grounding, and clinically
motivated symptom representations. For example, questionnaire-grounded models
use PHQ-style symptom structure to improve out-of-domain depression detection
[@nguyen2022improving], item-level multimodal models improve interpretability
within E-DAIC [@mandal2025questmf], and retrieval-based approaches ground
predictions in clinically relevant interview evidence [@zhang2025red]. Other
work has shown that depression benchmarks can contain protocol shortcuts, such
as therapist prompts or interviewer-question structure, that models may exploit
instead of participant-derived clinical evidence
[@burdisso2024daicprompts; @zhang2025interviewer].

Foundation models have made this representation-centered view even more
appealing. Recent depression systems increasingly use large language, speech,
and multimodal backbones to model heterogeneous behavioral evidence.
DepressionLLM, for instance, uses foundation-model prompting and multimodal
fusion for interpretable depression detection across E-DAIC, CMDC, and EATD
[@teng2026depressionllm]. SCD-MLLM proposes multimodal LLM adapters and
adaptive fusion for stable cross-domain depression recognition under missing
modalities [@chen2025scd]. These studies are important because they represent
where the field is going: stronger backbones, more modalities, and
multi-dataset evaluation. They also make the remaining assumption sharper. Even
if the representation side improves, cross-corpus depression detection still
assumes that the clinical targets being predicted are comparable enough to
support the transfer claim.

This paper focuses on that assumption. Depression severity scores are not
ordinary labels. They are structured clinical measurements produced by
assessment instruments, item definitions, response categories, scoring rules,
rater or self-report context, language, and protocol. PHQ-8, PHQ-9, HAMD-17,
and SDS are all depression-related targets, but they are not interchangeable
objects by name alone. Even within the PHQ family, two corpora may share item
names while differing in how participants at similar severity levels respond to
particular symptoms. In cross-corpus learning terms, representation alignment
mostly addresses the acquisition or manifestation mechanism,

$$
P_D(X \mid \theta),
$$

where latent depression severity or symptom state $\theta$ is expressed in
observable behavior $X$ under corpus $D$. It does not automatically validate
the measurement mechanism,

$$
P_D(Y \mid \theta),
$$

where symptom evidence is converted into an observed label $Y$. A model can
learn a useful behavioral representation and still fail to transfer clinically
if the target score means something slightly different across corpora.

We therefore study cross-corpus depression detection as a target-comparability
problem for mental health AI. Recent benchmark-validity work already argues
that medical AI benchmarks should be examined through construct-validity
questions [@alaa2025medicalconstruct]. Our claim is narrower: we do not test
the clinical construct, criterion, or clinical validity of the depression
instruments themselves. We audit whether observed depression scores preserve
comparable interpretation across corpora, using item structure, response
thresholds, target-contract comparisons, and prediction consequences. A paper
that aligns only representations leaves this target-comparability assumption
unchecked. This distinction matters especially in the foundation-model era.
Large backbones can improve the modeling of speech, language, and visual
behavior, but they do not decide whether PHQ or HAMD scores from different
corpora obey comparable response mechanisms.

Our proposed framework separates these two layers. Instead of directly mapping
multimodal observations to an observed corpus label,

$$
X \rightarrow Y_D,
$$

we model depression prediction as

$$
X \rightarrow Z \rightarrow Y_D,
$$

where $Z$ represents shared symptom evidence or latent severity, and $Y_D$ is
produced through an explicit measurement head whose sharing structure is itself
audited. In a foundation-backbone implementation, the encoder may be a large
text, speech, video, or multimodal model; the target pathway remains
measurement-aware:

$$
\text{encoder} \rightarrow \text{shared depression representation}
\rightarrow \text{latent symptom layer}
\rightarrow \text{audited measurement head}.
$$

The framework does not require all corpora to share an identical measurement
process. Instead, it asks what can be shared, what must remain corpus-specific,
and what kind of evidence is needed before observed labels are pooled or
compared directly.

We evaluate this idea across six depression corpus families plus a DAIC-WOZ
benchmark view. The key design is a set of pre-specified
measurement-discrepancy contrasts rather than a flat dataset list. DAIC-WOZ
and E-DAIC form the low-discrepancy control:
both come from the DAIC lineage and use PHQ-8, so DAIC-WOZ is treated as a
same-lineage benchmark view rather than as a fully independent corpus. E-DAIC
and CMDC form the main cross-language PHQ comparison: they share PHQ symptom
content but differ in language, population, and interview setting. CMDC and
PDCH provide an exploratory same-HAMD comparison, useful for testing whether
measurement differences are only a PHQ-8/PHQ-9 form issue. Additional corpora,
including MODMA, EATD, and MPDD-AVG, act as acquisition, task, emotional
context, and population stress views.

The empirical story follows three questions:

**RQ1: Representation heterogeneity and corpus identity.** How much corpus
identity remains before and after length and severity controls?

**RQ2: Measurement heterogeneity.** Do nominally aligned clinical targets
maintain comparable response mechanisms across corpora?

**RQ3: Prediction consequences.** Under direct prediction, domain-alignment
baselines, latent-target modeling, and explicit measurement heads, which parts
of cross-corpus generalization improve, and which validity conditions remain
unresolved?

This organization turns bounded transfer behavior into diagnostic evidence: it
separates representation-side improvements from target-side validity
conditions. Feature alignment, stronger backbones, and measurement-aware heads
are therefore evaluated as different interventions rather than as one
undifferentiated transfer score.

The contributions of this paper are:

1. We formulate cross-corpus depression detection as a target-comparability
   audit that separates representation heterogeneity, target measurement
   heterogeneity, and downstream prediction consequences.
2. We provide a structured audit centered on three pre-specified
   target-contract contrasts, with additional corpus families serving as
   acquisition and population stress views.
3. We instantiate a fixed measurement-aware ordinal architecture with strong
   frozen foundation representations, a shared symptom layer, and audited
   cumulative-logit item heads, then use matched calibrated ablations and
   repeated target-label budget splits to show that target calibration and
   shared-layer adaptation are robust effects, while corpus-specific ordinal
   parameterization is not independently superior in the real E-DAIC/CMDC
   transfer setting.

![Figure 1. Measurement-aware target-comparability audit for cross-corpus depression detection. The visual center is the target contract: scale, shared item content, response categories, rater or self-report source, language, and protocol. The proposed model routes frozen multimodal representations into shared symptom evidence and then through audited ordinal measurement heads whose sharing structure is tested empirically.](analysis/diagnostic_measurement_audit_paper/figures_core7/fig1_framework_overview.png){width=100%}

## 2 Related Work

### 2.1 Cross-Domain and Foundation-Model Depression Detection

Automatic depression detection has long been shaped by multimodal benchmark
practice. DAIC introduced clinical interview data for distress analysis
[@gratch2014distress], and the DAIC-WOZ/E-DAIC lineage became a standard
testbed for estimating depression severity from text, audio, and visual
behavior [@uscict2026daic]. Later corpora expanded the setting across
languages, clinical sites, controlled speech tasks, emotional contexts, and
population characteristics, including CMDC [@zou2023cmdc], MODMA
[@cai2020modma], PDCH consultation data [@pdchrepository2026], EATD audio-text
data [@shen2022automatic], and personality-aware multimodal challenge data
[@fu2025mpddchallenge].

Most cross-corpus work responds to this heterogeneity by improving
representations or aligning domains. Classical tools include adversarial
domain learning [@ganin2016domain], CORAL and MMD-style distribution alignment
[@sun2016deepcoral; @long2015dan], and robustness objectives such as IRM and
GroupDRO [@arjovsky2019irm; @sagawa2019groupdro], as well as label-shift
correction when class priors change [@lipton2018labelshift]. Recent depression
systems extend the same idea with foundation text, speech, and multimodal backbones:
DepressionLLM uses foundation-model prompting and multimodal fusion across
E-DAIC, CMDC, and EATD [@teng2026depressionllm], SCD-MLLM uses multimodal LLM
adapters for heterogeneous cross-domain recognition [@chen2025scd], and
DIL-MDD studies domain-incremental MDD detection across datasets such as
DAIC-WOZ, MODMA, and CMDC [@chen2025leavingnone]. Close depression-specific
baselines also include semi-supervised graph adaptation and personality-guided
hypergraph fusion [@chen2024gnnsda; @fu2026p3hf].

These studies define the representation side of the problem. They improve or
stress-test $P_D(X \mid \theta)$: how depression-related behavior is observed
under a corpus. Our paper asks the target-side question that remains after this
progress: whether the observed labels used to supervise these representations
are comparable enough across corpora to support the transfer claim.

### 2.2 Symptom-Grounded and Interpretable Depression Modeling

A second nearby line of work moves beyond direct black-box prediction by
grounding depression models in clinically meaningful symptoms. Nguyen et al.
show that constraining depression detection with PHQ-9 symptoms improves
out-of-domain generalization on social-media datasets while making model
behavior easier to inspect [@nguyen2022improving]. This is a crucial precedent
for our paper: the clinically meaningful abstraction is not a raw benchmark
label alone, but symptom evidence that can support transfer.

Interview-based multimodal work has made the same instinct more fine-grained.
QuestMF predicts item/question-level scores in E-DAIC with question-wise
modality fusion and ordinal learning, improving interpretability inside the
benchmark [@mandal2025questmf]. Retrieval-augmented explanation models ground
clinical-interview predictions in participant-specific evidence and reduce the
risk of purely post-hoc rationalization [@zhang2025red]. These papers show that
depression modeling benefits when symptoms, items, and evidence are explicit.

Our work keeps that advantage and asks the next question. Symptom grounding
makes a model more clinically legible, but it still assumes that a symptom item
has a sufficiently stable measurement role across corpora. That assumption is
not automatic in cross-language, cross-protocol, or cross-scale settings. We
therefore shift item-level modeling from within-corpus interpretability to
cross-corpus target comparability. The key distinction is small but important:
we do not only ask whether a model can predict PHQ or HAMD items; we ask
whether shared symptom items preserve comparable response mechanisms before
they are used as anchors for transfer.

### 2.3 Benchmark Validity and Protocol Shortcuts

Benchmark construct validity is now an active topic in machine learning and
medical AI evaluation. Alaa et al. argue that medical LLM benchmarks should be
evaluated as construct-validity problems rather than treated as neutral
leaderboards [@alaa2025medicalconstruct]. Bean et al. review LLM benchmarks
through the same measurement lens [@bean2025measuring], and Freiesleben and
Zezulka frame predictive benchmark scores as claims that require explicit
assumptions about the task, evaluation function, and data distribution
[@freiesleben2025benchmarking]. We therefore do not claim that importing
construct validity into AI benchmarking is new. Our contribution is narrower
and more empirical: we operationalize cross-corpus score-comparability and
target-contract auditing for depression detection, where clinical labels are
scale-based measurements rather than generic class names.

Benchmark-validity work in depression detection has shown that high scores can
come from unintended cues. Burdisso et al. analyze DAIC-WOZ therapist prompts
and show that interviewer-side prompts can provide discriminative shortcuts
rather than participant-derived evidence [@burdisso2024daicprompts]. Zhang and
Poellabauer further model interviewer-question context and use adversarial
learning to reduce question-type bias in multimodal depression detection
[@zhang2025interviewer]. Multi-probe audit work broadens this concern by
examining split stability, external validation, and symptom-dense versus
symptom-light regions in clinical-interview benchmarks
[@ishikawa2026multiprobe]. Related criterion-contamination audits make the
same warning sharper: models can appear clinically meaningful when the target
criterion is mirrored in the input evidence [@li2025mirror].

This work changes the burden of evidence: a depression benchmark is an
interaction protocol, not just a table of samples and labels. Our paper follows
that audit logic but moves it to the target side. Prior shortcut audits mainly
ask whether $X$ contains nonclinical or protocol-specific signals that models
can exploit. We ask whether the observed clinical target $Y$ remains comparable
enough across corpora after a representation has been learned.

### 2.4 Clinical Measurement and Scale Comparability

Clinical scores are designed measurements of latent symptom constructs, not
ordinary machine-learning labels. Measurement-invariance theory asks when
scores can be compared across groups [@meredith1993measurement;
@vandenberg2000review], while ordinal item-response and DIF methods provide a
language for item thresholds, discrimination, and group-conditioned response
behavior [@samejima1969graded; @chalmers2012mirt; @bulut2017detecting].
Approximate alignment further recognizes that exact invariance is often too
strict for applied multi-group settings [@muthen2014irt].

This vocabulary maps directly onto cross-corpus depression detection.
Configural evidence asks whether the same broad symptom structure is plausible
in each corpus. Metric evidence asks whether items relate similarly to the
underlying symptom factor. Threshold or scalar evidence asks whether subjects
at comparable severity levels are placed into comparable response categories.
DIF localizes the failure mode: an item can remain clinically meaningful while
its response thresholds differ by corpus. Anchor items then become the bridge
between clinical measurement and machine learning, because they identify which
parts of the target can be shared and which parts should remain
corpus-specific.

Psychiatric measurement studies give useful context. PHQ-9 can show acceptable
invariance in large population or survey settings [@galenkamp2017measurement;
@patel2019measurement], which is important because it prevents an overbroad
claim that PHQ is generally unstable. PHQ/GAD invariance and DIF remain active
clinical-measurement questions in primary-care settings
[@delamain2024measurement]. At the same time, clinical scale
comparison work shows that PHQ and HAMD capture related but not identical
severity information [@ma2021phqhamd], and score-linking work finds systematic
differences even among correlated depression scales [@zhou2026depression]. De
Duro et al. [-@deduro2026nlppsychometrics] make a parallel point for language
technologies: mental-health models should specify what construct their outputs
are intended to measure.

The machine-learning literature has only partly absorbed this target-side
distinction. Symptom-grounded models make labels more interpretable, and
domain-adaptation models make features more transferable, but both usually
take the observed clinical target as already comparable once item names or
total-score thresholds align. Our audit makes that assumption explicit. We
first identify same-lineage, shared-PHQ, and same-HAMD target contracts; then
we test common structure, item-level response behavior, severity-conditioned
differences, anchors, and finite-sample uncertainty before using the target for
prediction. This is the missing layer between symptom-grounded representation
learning and clinical target transfer. Existing work asks how to learn more
transferable depression representations, or how to validate benchmarks in
general. We ask whether the depression targets used to supervise those
representations are themselves comparable across corpora, and how that audit
changes calibrated transfer claims.

## 3 Target-Comparability Audit Framework

The central object in this paper is not a pooled depression dataset, but a
corpus-specific target contract. A target contract specifies what clinical
quantity a corpus makes available for learning: the instrument, item set,
scoring rule, rater or self-report context, language, protocol lineage,
available anchor items, and the comparison level that the data can support.
Cross-corpus depression detection becomes meaningful only after this contract
is made explicit.

### 3.1 Direct Transfer and Its Hidden Assumption

Let $D$ denote a corpus, $X_D$ the observed multimodal data, $Y_D$ the observed
clinical label, and $\theta$ the latent depression severity or symptom state.
The usual cross-corpus predictor learns a direct map:

$$
f: X_D \rightarrow Y_D.
$$

When this predictor is moved from one corpus to another, poor transfer is
usually attributed to differences in the input mechanism:

$$
P_{D_1}(X \mid \theta) \neq P_{D_2}(X \mid \theta).
$$

For depression benchmarks, this is a real problem. Interview scripts,
language, recording environment, clinical setting, task design, modality
availability, and population all affect how depression-related behavior is
observed. But the direct predictor also assumes that the observed target
mechanism is sufficiently stable:

$$
P_{D_1}(Y \mid \theta) \approx P_{D_2}(Y \mid \theta).
$$

This assumption is rarely tested in machine-learning papers. PHQ-8, PHQ-9,
HAMD-17, and SDS are all depression-related measurements, but they differ in
item coverage, response categories, scoring conventions, rater involvement, and
clinical emphasis. Even within a nominally shared item family, the mapping from
severity to response category can vary across language, protocol, population,
or corpus lineage. A model can therefore learn useful depression evidence while
still producing an unsupported observed-scale transfer claim if $Y_D$ is
treated as an ordinary interchangeable label.

### 3.2 Measurement-Aware Transfer

We use a working abstraction that distinguishes two mechanisms rather than
asserting that they are conditionally independent in the data. The
representation component addresses $P_D(X \mid \theta)$: how latent symptom
state is expressed in language, speech, facial behavior, gait, or other
observable signals. The measurement component addresses $P_D(Y \mid \theta)$:
how symptom evidence is converted into item responses, total scores, or
severity labels under a corpus-specific assessment contract. In a strictly
local-independent model this decomposition could be written as

$$
P_D(X,Y \mid \theta)=P_D(X \mid \theta)P_D(Y \mid \theta).
$$

Clinical-interview corpora need not satisfy this exactly. Interview questions
may be selected or phrased around symptoms, participant language can repeat
questionnaire criteria, and interviewer protocol can share residual structure
with the observed score [@burdisso2024daicprompts; @zhang2025interviewer;
@li2025mirror]. We therefore use the decomposition as an audit map: it tells
us to check representation, protocol, and measurement mechanisms separately,
not to assume a verified data-generating factorization.

This leads to a measurement-aware prediction path:

$$
X_D \rightarrow H_D \rightarrow S \rightarrow \hat{Y}_D,
$$

where $H_D=E(X_D)$ is a learned behavioral representation, $S$ is shared
symptom evidence or latent severity, and $\hat{Y}_D=M(S,D)$ is produced by an
explicit measurement head. The head may be shared or corpus-specific, but that
choice is a target-contract question rather than a default architectural
truth. The shared layer is also not assumed to be universal by default. It is
shared only where the item map, scale family, and empirical measurement audit
support that claim.

This formulation gives the paper a constructive modeling implication. Strong
encoders are welcome, but they are not the whole system:

$$
\text{Foundation encoder}
\rightarrow
\text{shared depression representation}
\rightarrow
\text{latent symptom layer}
\rightarrow
\text{audited measurement head}.
$$

The framework therefore does not compete with foundation or multimodal fusion
work as a generic performance architecture. It adds the target-comparability
layer that such systems need before cross-corpus clinical labels can be
interpreted as comparable.

For the executable method in this paper, we test one concrete instantiation
rather than leaving the layer as a family of possible heads. The frozen
foundation representation is projected to an eight-dimensional shared symptom
layer, aligned with the eight PHQ symptoms common to PHQ-8 and PHQ-9. The
primary instantiation gives each corpus its own cumulative-logit ordinal head,
and the ablation suite tests whether that corpus-specific parameterization is
needed beyond calibrated shared-layer adaptation. For item $k$ in corpus $D$,
the head learns a positive slope and three ordered thresholds, producing
$P(Y_{Dk}=0),\ldots,P(Y_{Dk}=3)$ and an expected item score. The core training
signal is source ordinal reconstruction plus target calibration ordinal
reconstruction:

$$
\mathcal{L}_{\mathrm{MA}}=
\mathcal{L}_{\mathrm{src}}^{\mathrm{ord}}
+\lambda_{\mathrm{cal}}\mathcal{L}_{\mathrm{tgt-cal}}^{\mathrm{ord}}
+\lambda_2\lVert S\rVert_2^2 .
$$

An auxiliary variant adds distribution matching in the shared symptom layer:

$$
\mathcal{L}_{\mathrm{MA+MMD}}=
\mathcal{L}_{\mathrm{MA}}
+\lambda_{\mathrm{mmd}}\mathrm{MMD}(S_{\mathrm{src}},S_{\mathrm{tgt}}).
$$

Training follows the target-contract logic: warm-start the projector,
symptom layer, and source ordinal head on the source corpus; initialize the
target ordinal head from the source head; then adapt the target-side ordinal
path using a labeled calibration subset. The ablations remove exactly one
piece of this design: latent-only uses the source head in the target corpus,
and corpus-specific-head fits only the target ordinal head while freezing the
shared symptom layer. Additional calibrated ablations keep the shared layers
trainable while replacing the corpus-specific ordinal head with a shared
ordinal head or a generic target MLP head. The auxiliary MMD variant is
evaluated separately and is not part of the definition of measurement-aware
transfer. The substantive design is the shared symptom representation plus an
explicit target-calibrated ordinal prediction path; whether the ordinal head
must be corpus-specific is evaluated empirically.

### 3.3 Target-Contract Decisions

The audit assigns each corpus pair to one of three practical comparison
levels.

First, if language, scale, protocol lineage, and item behavior are closely
aligned, observed-scale comparison is reasonable. DAIC-WOZ and E-DAIC are used
in this way: not as independent pooled corpora, but as a same-lineage PHQ-8
control that anchors the low-discrepancy end of the measurement gradient.

Second, if clinical constructs are shared but item thresholds or response
tendencies differ, the corpora can share a symptom layer while the measurement
head remains an empirical sharing decision. This is the main role of the
E-DAIC/CMDC PHQ shared-item analysis: the eight shared symptoms provide a
useful bridge, but the observed item responses still require validation before
direct score interchangeability or corpus-specific parameterization is claimed.

Third, if the available evidence is small or only partially aligned, the corpus
pair is treated as exploratory or as a stress view. CMDC/PDCH HAMD is in this
category. It is valuable because it tests whether the story extends beyond a
PHQ-8/PHQ-9 form comparison, but it is not used to claim formal HAMD
measurement invariance.

These decisions are part of the framework. They specify which claims the data
support and which model component should carry the corpus-specific part of the
observed target contract.

### 3.4 Validity Gates

The empirical audit is organized into three gates that correspond to the paper
experiments.

**Representation gate.** We first ask whether learned features retain corpus,
task, protocol, or population identity. High identity recovery does not make a
feature useless; it shows that corpus-specific acquisition signatures remain
available to downstream predictors.

**Measurement gate.** We then ask whether nominally aligned targets preserve
comparable item or score behavior. Same-lineage controls, shared-item
distributions, item-excluded severity-conditioned responses, and bounded
psychometric checks determine whether an observed label can be treated as
shared, head-specific, or exploratory.

**Prediction gate.** Finally, we ask what happens when the target is modeled
explicitly. Direct prediction, feature-alignment baselines, latent-target
prediction, localized calibration, and measurement-aware heads are evaluated
not only by raw error, but also by output identity, feature identity,
observed-scale reconstruction, and target-contract transfer.

These gates define the appropriate strength of a cross-corpus claim. A bounded
prediction result is diagnostically informative when it reveals where
representation learning, target harmonization, and measurement-head adaptation
solve different parts of the transfer problem.

## 4 Datasets and Analytical Roles

We audit six depression corpus families and one DAIC-WOZ benchmark view. The
datasets are deliberately not presented as a larger pooled training set. Each
corpus has an analytical role defined by its acquisition protocol, modalities,
clinical target, and item-level supervision. This design lets the paper compare
pre-specified measurement contrasts while still using broader datasets as
stress views for representation, task, and population
heterogeneity.

**Table 1. Depression corpus families, benchmark views, and analytical roles.**

| Dataset or view | Participants | Modalities | Main target | Role in this study |
| --- | ---: | --- | --- | --- |
| E-DAIC | 275 | Text, audio, video | PHQ-8 | Primary development corpus; PHQ item analysis; interview-protocol diagnostics |
| DAIC-WOZ | 189 | Text, audio, video | PHQ-8 | Same-lineage Wizard-of-Oz benchmark view and PHQ-8 control; not pooled as independent from E-DAIC |
| CMDC | 78 | Text, audio, video | PHQ-9; partial HAMD-17 | Cross-language and cross-protocol PHQ comparison; small HAMD sanity subset |
| PDCH | 100 | Text, audio | HAMD-17 | Clinical HAMD item and severity analysis |
| MODMA | 52 | Audio | PHQ-9/diagnosis | Controlled speech-task stress test |
| EATD | 162 | Text, audio | SDS | Emotional-valence and SDS external stress test |
| MPDD-AVG | 224 | Audio, video, gait, personality | PHQ-9 | Population and individual-difference stress test |

The formal item-level PHQ measurement layer uses E-DAIC and CMDC because both
provide responses for the eight items shared by PHQ-8 and PHQ-9. DAIC-WOZ is
added as a same-PHQ-8 benchmark-lineage control over official train/dev item
labels, giving the measurement audit a low-discrepancy reference. PDCH and the
small CMDC HAMD subset support an exploratory same-HAMD analysis. MODMA, EATD,
and MPDD-AVG are used as acquisition, task, emotional-context, and population
stress views rather than as formal item-level invariance datasets.

All experiments use subject-level splits: segments, sessions, modalities, or
tasks from the same participant remain in the same partition. This keeps the
reported transfer behavior tied to corpus-level differences rather than
participant leakage.

![Figure 2. Target-contract contrasts and stress views. The figure only encodes analytical role: DAIC-WOZ/E-DAIC is a same-lineage PHQ-8 sanity control, E-DAIC/CMDC is the primary shared-PHQ measurement contrast, CMDC/PDCH is an exploratory same-HAMD stress view, and MODMA, EATD, and MPDD-AVG serve as acquisition, task, and population stress views. Dataset sizes, modalities, and label details are kept in Table 1.](analysis/diagnostic_measurement_audit_paper/figures_core7/fig2_dataset_relationship_map.png){width=100%}

## 5 Methods

The experiments instantiate the three gates from Section 3. They are not a
leaderboard sequence. Each experiment tests a different assumption that a
cross-corpus depression model needs before its predictions can support an
observed-score transfer claim.

### 5.1 RQ1: Representation Heterogeneity Audit

We first extract subject-level representations and test whether corpus,
protocol, task, or question-position identity remains recoverable. BGE-M3 is
the primary multilingual text feature contract [@baai2026bgem3], with
multilingual-E5-base as an independent sensitivity encoder
[@wang2024multilinguale5]. Both remain frozen. Audio and visual analyses
use frozen WavLM, eGeMAPS, OpenFace, or existing challenge features where
available.

To stress the foundation-model objection, we add a stronger text slice with
frozen Qwen3-Embedding-0.6B transcript representations
[@zhang2025qwen3embedding]. We also include a lightweight multimodal completion
slice using WavLM and wav2vec2 subject features as audio foundation proxies
[@chen2022wavlm; @baevski2020wav2vec2], OpenFace subject statistics as a video
proxy, and text-audio-video fusion views. These representations are kept
frozen to isolate whether target-side contracts matter after reasonably strong
and multimodal feature extraction.

For each representation family, lightweight identity probes predict dataset or
protocol labels. Balanced accuracy is used because corpus sizes differ. High
identity recovery is interpreted as corpus imprinting, not as proof that a
feature is useless. The modeling implication is simply that pooled or aligned
representations need downstream target validation.

Because the main E-DAIC/CMDC probe drops sharply after controls, we report the
residualization protocol explicitly. Controls are applied inside each
cross-validation fold: training-fold medians impute features, training-fold
standardization is applied, ordinary least-squares residualization is fitted on
the training fold with an intercept, and the held-out fold is transformed using
only those training-fold quantities. We decompose the control effect into
length-only, severity-only, length-plus-severity, and a shuffled-control
sensitivity that preserves covariate marginals while breaking subject-level
alignment. We also repeat the identity probe with a nonlinear random-forest
classifier after the same fold-internal preprocessing to test whether
near-chance controlled identity is specific to linear-probe capacity.

We treat interviewer leakage and criterion contamination as explicit boundary
checks. The available E-DAIC transcript contract does not expose speaker roles:
the manifest speaker field is empty and the transcript CSV files contain time,
text, and confidence fields but no interviewer or participant label. We
therefore do not claim a participant-only or interviewer-only E-DAIC control.
Instead, we run two bounded proxy checks that target the most plausible
shortcut surface available from the current data. First, the text
protocol-control audit compares full transcripts with front, middle, and back
transcript slices and repeated-turn removed or repeated-turn only variants.
Second, a Qwen3 prompt-proxy sensitivity re-embeds the same E-DAIC transcript
variants and fits fixed Ridge and Logistic heads on the official train/dev
split. Separately, the CMDC criterion-overlap stress deletes question-position
segments with the highest semantic overlap to PHQ item text and compares that
loss with matched random deletion. These analyses cannot prove absence of
leakage, but they test whether the most accessible prompt-like or PHQ-overlap
content is the dominant shortcut under the available data contract.

### 5.2 RQ2: Measurement-Discrepancy Design

The measurement audit asks whether nominally aligned clinical targets preserve
comparable response mechanisms. We organize the analysis as three
pre-specified discrepancy settings rather than a pass/fail invariance test.
The resulting pattern is descriptive: it summarizes how the audited pairs
behave, without assigning the differences to a single causal factor.

**DAIC-WOZ to E-DAIC** is the same-lineage PHQ-8 control. Both views come from
the DAIC interview family and use PHQ-8. This comparison calibrates the lower
end of the discrepancy scale: when the lineage, language, protocol, and scale
are closely aligned, the measurement audit should find only small differences.

**E-DAIC to CMDC** is the primary PHQ shared-item comparison. E-DAIC provides
PHQ-8 and CMDC provides PHQ-9, so the analysis is restricted to the eight
shared symptoms. We report item response distributions, means and variances,
category proportions, and item-excluded severity-conditioned response patterns.
For the severity-conditioned analysis, the conditioning score excludes the item
being tested, normalizes the remaining seven-item total, and bins subjects into
pooled low, middle, and high severity strata. We compare item means and category
probabilities only for non-sparse cells, so the result describes response
behavior at comparable observed severity rather than simply restating total
score differences.

These descriptive analyses are paired with bounded psychometric evidence. The
first step is a structural compatibility screen, not a formal configural
invariance test. It is passed only when both corpora show acceptable internal
consistency, a dominant first factor, positive item loadings, and cross-corpus
loading congruence at least 0.95. In implementation, this means Cronbach's
alpha at least 0.70, first-to-second eigenvalue ratio at least 2.0, and
minimum first-factor loading at least 0.25 in each corpus. Item-level metric
support is defined by absolute loading difference at most 0.20.
Threshold support is tested by three ordinal-logit threshold screens per item,
using the leave-one-item-out severity score as the conditioning variable; an
item is a threshold anchor only when all available threshold-location
differences are at most 0.35. Candidate anchors must satisfy both metric and
threshold support, and the partial-invariance screen requires at least four
anchors.

We then fit a label-only multi-group graded-response confirmation over the same
eight shared items. The model ladder is where we reserve the formal
configural, metric, scalar/threshold, and partial-anchor terminology common in
measurement-invariance reporting [@putnick2016measurement]. Because the
primary shared-PHQ analysis has 219 E-DAIC and 77 CMDC item-labeled subjects
over only eight four-category items, it sits far below sample-size ranges used
in recent graded-response-model parameter-recovery simulations and below
recommendations for precise item-parameter recovery
[@ikeda2026grmsamplesize; @jiang2016mgrmsamplesize]. We therefore use the
multi-group graded-response model as bounded confirmation of the
target-comparability audit, not as definitive item-level DIF inference. An
item is marked as a hypothesis-generating localization candidate only when
freeing its loading or thresholds improves fit by both the likelihood-ratio
criterion ($p<0.01$) and a BIC improvement greater than 2.0. The implementation
uses `mirt` multiple-group estimation and anchor constraints
[@chalmers2026mirtmultiplegroup].
We also run a finite-sample simulation that preserves each corpus's observed
sample size and severity composition. The simulation contrasts a scalar
invariant world with an observed-like C02/C06 threshold-DIF world and reports
false-localization, recovery, and anchor-recovery rates. This bounds the
evidential weight of localized threshold shifts under the observed sample
sizes.

Finally, because the approximate invariance thresholds are heuristic screening
rules rather than universal psychometric standards, we report a sensitivity
grid over loading-difference tolerances 0.15, 0.20, and 0.25, threshold
tolerances 0.25, 0.35, and 0.45, and minimum-anchor requirements of 3, 4, and
5 items. The sensitivity grid is paired with the bootstrap item-DIF stability
summary, so anchor and threshold-shift readings are described as more credible
only when they recur across both sources of uncertainty.

**CMDC to PDCH** is the exploratory same-HAMD comparison. Both corpora provide
HAMD-17 item supervision, but the CMDC HAMD sample is small. We therefore use
item distributions, item-excluded severity-conditioned responses, and
correlation-structure differences, rather than a formal HAMD MIM, IRT, or DIF
model. Its role is to strengthen the scale-form argument: the measurement
question is not only a PHQ-8 versus PHQ-9 artifact.

### 5.3 RQ3: Prediction Consequence Audit

The final experiment asks what changes when prediction is forced to respect the
target contract. We compare direct observed-label prediction against latent
target prediction and corpus-specific reconstruction:

$$
X_D \rightarrow \hat{\theta} \rightarrow \hat{Y}_D.
$$

The direct baselines predict observed PHQ or HAMD labels from the same frozen
feature contracts. Zero-target-label baselines include ERM, DANN-style
adversarial learning [@ganin2016domain], CORAL [@sun2016deepcoral], and
MMD/DAN-style distribution matching [@long2015dan]. IRM-style environment
pressure [@arjovsky2019irm], GroupDRO-style robustness [@sagawa2019groupdro],
and direct foundation-feature regressors are kept as supplementary stress
baselines rather than main calibrated competitors. These rows mainly test how
far feature alignment and direct source transfer can go without labeled target
clinical data.

The formal measurement-aware variants use the fixed ordinal architecture from
Section 3.2. `Latent-only` learns the shared symptom layer on the source corpus
and scores target subjects through the source ordinal head. In the
target-calibrated block, `Corpus-specific head` freezes the source-trained
symptom layer and fits only the target ordinal head on a calibration subset;
this is retained as a weak legacy comparator, not as the identifying ablation
for the target measurement pathway. The fair calibrated baselines are designed
to separate representation adaptation from measurement parameterization.
`Direct target fine-tune` warm-starts a direct item regressor on the source
corpus and then updates the same trainable shared layers using target
calibration labels, without a corpus-specific ordinal formulation. `Direct
source+target multitask` uses the same direct item head while jointly optimizing
source reconstruction and target calibration reconstruction. `Shared ordinal
head` uses the same training schedule and trainable parameter classes as
`Measurement-aware`, but forces source and target to share a single ordinal
head. `Generic target MLP head` allows target labels to update the projector and
symptom layers with corpus-specific non-ordinal MLP item heads.
`Measurement-aware` jointly optimizes source ordinal reconstruction and target
calibration ordinal reconstruction with corpus-specific cumulative-logit
ordinal heads after source warm-start and target-head initialization.
`Measurement-aware + MMD` adds the auxiliary shared-symptom MMD term. The main
observed-scale reconstruction metric is Macro Item MAE. Calibration is audited
with calibration-in-the-large (CITL), calibration slope, and a binned
calibration-curve summary; this follows the clinical prediction-model
calibration distinction between average miscalibration and slope or curve
miscalibration [@vanCalster2019calibration]. The
reconstruction-plus-calibration sum is retained only as a supplementary compact
summary, not as a new clinical scale or a claimed 1:1 trade-off between item
error and calibration gap. This observed-scale calibration audit is also
separate from neural probability calibration in the usual classification sense
[@guo2017calibration]. For $K$ shared items and target subjects
$i=1,\ldots,n$,
Macro Item MAE is

$$
\frac{1}{K}\sum_{k=1}^K\frac{1}{n}\sum_{i=1}^n
\left|\hat{y}_{ik}-y_{ik}\right|.
$$

Let $t_i=\sum_k y_{ik}$ and $\hat{t}_i=\sum_k \hat{y}_{ik}$ denote observed and
predicted shared-PHQ totals. Calibration-in-the-large is

$$
\mathrm{CITL}=\frac{1}{n}\sum_{i=1}^{n}\left(t_i-\hat{t}_i\right),
$$

with ideal value 0; positive values indicate underprediction of the observed
target total. Calibration slope is estimated by ordinary least squares,

$$
t_i=\alpha+\beta\hat{t}_i+\epsilon_i,
$$

with ideal slope $\beta=1$. We report $|\mathrm{CITL}|$ and $|\beta-1|$ in the
main repeated-split table. Binned item calibration MAE is a secondary
calibration-curve summary: it bins subjects into five equal-frequency
predicted-severity bins using predicted total score, then computes the weighted
absolute gap between predicted and observed mean total score:

$$
\mathrm{CalMAE} =
\sum_{b=1}^{5}\frac{n_b}{n}
\left|
\frac{1}{n_b}\sum_{i\in b}\hat{t}_i
-
\frac{1}{n_b}\sum_{i\in b}t_i
\right|.
$$

Target calibration is fixed before model comparison. For each transfer
direction and repeated split, target subjects are partitioned once into
calibration and evaluation subsets using stratified sampling over shared-PHQ
total severity groups. The default calibration size is 30 percent of the
available target subjects with a minimum of 24, capped so that at least 35
percent, and at least 12 subjects, remain for evaluation. Under the official
multimodal feature view, this yields 66 labeled E-DAIC calibration subjects and
153 held-out E-DAIC evaluation subjects when transferring from CMDC to E-DAIC,
and 24 labeled CMDC calibration subjects with 20 held-out CMDC evaluation
subjects when transferring from E-DAIC to CMDC. Each method sees the same
calibration/evaluation split within a transfer direction and budget. Repeated
splits change both the stratified target partition and neural initialization;
hyperparameters, source data, frozen feature contracts, and target-label budget
are fixed across methods, and no target evaluation labels are used for model
selection.

The target-only budget audit uses 30 repeated subject-level splits per
direction and budget, with 200 participant-bootstrap draws per split for paired
uncertainty. It varies $k=4,8,12,16,24$ target calibration labels for both
directions; $k=24$ is the largest shared small-budget value that preserves the
pre-specified minimum held-out CMDC evaluation size in the E-DAIC-to-CMDC
direction. A separate default-budget row keeps the larger 66-subject E-DAIC
calibration budget for CMDC-to-E-DAIC, so the main table reports the original
default calibration regime without forcing both target corpora to have the
same $k$. The budget settings are not nested: each $k$ draws its own stratified
calibration/evaluation split so the uncertainty summarizes a budget-specific
sampling design rather than one favorable curriculum. Target-only rows use the
same frozen Qwen3+WavLM+OpenFace subject representation as source-plus-target
rows; they train only prediction layers on the $k$ labeled target subjects and
do not learn a raw-signal encoder from those samples.

The target-only direct MLP is a two-layer projection head:
Linear(input, 256), GELU, Dropout(0.08), LayerNorm, Linear(256, 256), GELU,
followed by a sigmoid item predictor scaled to the PHQ item range [0,3]. It is
trained with AdamW, learning rate $10^{-3}$, weight decay $10^{-4}$, and mean
squared item loss for 3500 epochs. The ordinal target-only row uses the same
projector and shared symptom layer with cumulative-logit item heads trained by
ordinal negative log likelihood for the same epoch budget. Source-plus-target
calibrated rows use the same hidden dimension, dropout, optimizer family, and
fixed epoch schedules as the measurement-aware architecture: 500 source
warm-start epochs for direct or ordinal objectives, 450 target-head epochs when
only a head is fitted, and 3000 full adaptation epochs when shared layers are
updated. The direct and generic MLP baselines use MSE on item scores; ordinal
baselines use item-level ordinal negative log likelihood.

Secondary severity metrics report total-score MAE and concordance correlation
coefficient. To make the results legible to the depression-detection
literature, we also threshold the predicted shared PHQ total at 10 and report
Macro-F1, Balanced Accuracy, AUROC, AUPRC, Sensitivity, and Specificity as a
secondary clinical endpoint.

This design makes bounded results interpretable. If a method reduces output
identity but leaves feature identity high, it has changed the target pathway
without making the representation invariant. If a feature-alignment baseline
improves domain confusion but not observed-scale reconstruction, it has solved
only part of the transfer problem. The calibrated ablations separate three
target-side effects: whether target labels should update the shared projector
and symptom layers, whether an ordinal item model helps beyond generic direct
heads, and whether corpus-specific ordinal parameters improve over a shared
ordinal head. If the measurement-aware ordinal model improves only over the
frozen `Corpus-specific head`, the gain may reflect target-supervised
representation adaptation rather than corpus-specific measurement modeling. We
therefore treat target-pathway claims as supported only where the
measurement-aware model also improves over calibrated baselines with matched
target labels and trainable shared-layer access under fixed, comparable
optimization schedules. Seed-level
paired tests on the reconstruction-plus-calibration score are treated only as
descriptive stress checks; the repeated-split and participant-bootstrap budget
study is the primary uncertainty evidence for calibrated architecture claims.

## 6 Results

We report the results as three validity gates. This keeps the paper's evidence
chain compact: first, whether corpus identity remains visible in learned
representations; second, whether clinical targets retain comparable response
mechanisms; and third, whether measurement-aware prediction changes the
generalization story.

**Table 2. Main validity gates and the claim each gate supports.**

| Gate | Main evidence | Modeling implication |
| --- | --- | --- |
| Representation gate | Raw corpus-identity probes are strong screens, but residual identity is control- and probe-dependent. In E-DAIC/CMDC, length-associated directions account for most linear separability, while nonlinear Qwen text probing still recovers substantial residual identity. | Representation auditing is necessary, but raw corpus identity alone cannot decide target comparability. |
| Measurement gate | DAIC-WOZ/E-DAIC shows near-identical same-lineage PHQ-8 behavior, E-DAIC/CMDC shows shared but imperfect PHQ item behavior, and CMDC/PDCH shows exploratory same-HAMD differences. | Shared symptom evidence can be useful, but observed labels require target contracts; whether the measurement head should be shared or corpus-specific must be tested rather than assumed. |
| Prediction gate | Qwen3 and lightweight multimodal stress tests show that stronger features do not erase target-mapping needs; fair calibrated ablations and repeated target-budget splits show that the frozen-head gain is largely a calibration-regime effect, while target-only direct calibration is the strongest Macro Item MAE competitor. | Stronger encoders and feature-alignment baselines should be paired with explicit target contracts, target-only and source-plus-target calibrated baselines, and calibration-aware evaluation before assigning gains to measurement modeling. |

### 6.1 Representation Gate: Raw Identity Is Strong, Residual Identity Is Contrast-Dependent

The representation gate asks whether corpus or acquisition identity is visible
in the features used for depression prediction. Raw probes are useful as a
high-sensitivity screen: across the main E-DAIC/CMDC/PDCH feature contract,
dataset identity is perfectly recoverable from BGE-M3, multilingual-E5, and
Qwen3-Embedding-0.6B transcript features, each with feature-identity balanced
accuracy of 1.000. Prediction-level identity also remains high in direct
shared-item models, reaching 0.932 for BGE-M3, 0.993 for multilingual-E5, and
0.978 for Qwen3-Embedding. We report the full raw identity matrix in
Supplementary Figure S2, but the main text relies on the more informative
controlled probes.

Figure 3 shows the original fold-internal linear-probe result after length and
severity residualization. The cross-language E-DAIC/CMDC contrast drops from
raw near-perfect identity to chance-level balanced accuracy in Qwen3 text
(0.497), WavLM audio (0.484), and OpenFace video (0.522). A decomposition of
this drop shows that severity-only control leaves the linear identity probe
near 1.000, while length-only control already reduces it to 0.495 in Qwen3
text, 0.481 in WavLM audio, and 0.508 in OpenFace. Shuffling the
length-plus-severity controls returns the linear probe to near-perfect
identity, showing that the reduction depends on subject-aligned corpus-linked
length structure rather than residualization mechanically erasing any signal.

The same sensitivity also exposes a real caveat. With a nonlinear random-forest
probe after the same preprocessing, controlled identity remains high for Qwen3
text (0.987) and modest for WavLM audio (0.614), while OpenFace remains near
chance (0.504). Thus the correct RQ1 conclusion is not that E-DAIC/CMDC has no
residual corpus signature. It is that raw identity is strongly coupled to
length-associated structure under a linear probe, but higher-capacity probes
can still recover residual corpus information from some foundation feature
views. This is exactly why representation auditing is useful but insufficient:
length-associated directions account for most linear separability in this
contrast, but substantial nonlinear corpus information remains, and the
target-comparability question cannot be settled by a single corpus-identity
number.

![Figure 3. Control-dependent corpus identity under the linear probe. Points report balanced accuracy before and after fold-internal length plus severity residualization. E-DAIC/CMDC drops near chance under the linear probe, while DAIC-lineage identity remains high; nonlinear sensitivity is reported separately.](analysis/diagnostic_measurement_audit_paper/figures_core7/fig3_controlled_identity_probe.png){width=100%}

The same controlled audit also shows that corpus identity is not merely an
English-versus-Chinese classifier. Within E-DAIC itself, DAIC-WOZ-lineage
sessions and extended-lineage sessions remain identifiable after the same
linear controls, with balanced accuracy 0.839 for Qwen3 text and 0.897 for
WavLM audio. A Chinese same-scale control, CMDC versus PDCH HAMD, is more
modest but still above chance in the Qwen3 text view (0.572). Thus, residual
corpus identity is not uniform: it depends on contrast, controls, modality, and
probe capacity, and it can persist in lineage or clinical-setting contrasts
after length and severity shortcuts are removed.

The pattern also persists under stronger feature views. The Qwen3 text slice is
a foundation-style backbone, WavLM-derived speech features retain lineage
structure, and protocol diagnostics expose interview-position and
question-position signatures. The leakage sensitivity is intentionally
bounded: E-DAIC speaker-resolved controls remain unavailable because neither
the manifest nor transcript CSV files expose populated speaker roles. Under the
Qwen3 prompt-proxy stress test, repeated-turn-only text does not match the full
transcript for PHQ-8 severity (MAE 4.806 versus 4.801) or binary depression
classification (Macro-F1 0.576 versus 0.665), and removing repeated turns does
not increase PHQ-8 error (4.577 versus 4.801), although binary Macro-F1 drops
modestly (0.614 versus 0.665). The CMDC criterion-overlap deletion stress is
similarly bounded: deleting high PHQ-overlap question-position segments is not
clearly worse than matched random deletion under the primary BGE-M3 view
(excess MAE 0.150, 95 percent interval -0.320 to 0.671). These checks do not
prove absence of criterion contamination, but they reduce the risk that the
main audit is driven only by the simplest accessible prompt or PHQ-overlap
shortcut. The modeling implication is direct: representation alignment is a
necessary audit target, but it cannot by itself certify clinical target
comparability.

### 6.2 Measurement Gate: A Graded Empirical Pattern Across Target Contracts

The measurement gate asks whether nominally aligned clinical targets behave as
the same measurement mechanism across corpora. The answer is not a simple
"invariant" or "non-invariant." Across the three pre-specified pairings, we
observe a graded empirical pattern. Because language, protocol, population,
scale form, and corpus lineage vary together, this pattern should be read as a
structured benchmark audit rather than a causal or strictly monotonic law.

**Same-lineage PHQ-8 control.** DAIC-WOZ and E-DAIC anchor the low-difference
end of the audit, but only as a provenance sanity control rather than
independent-corpus evidence. In 141 complete item-labeled overlapping
train/dev subjects, the all-item exact-match rate is 0.993 and the mean
absolute paired item difference is 0.007. This is the expected reference
point: when scale, language, protocol lineage, and interview format are closely
matched, the measurement contract is nearly identical.

**Cross-language PHQ shared symptoms.** The main PHQ analysis compares 219
E-DAIC participants with 77 CMDC participants over the eight PHQ symptoms shared
by PHQ-8 and PHQ-9. The result is a strong but imperfect bridge. A common PHQ
structure is clearly present: the structural compatibility screen passes,
loading congruence is 0.998, and 7 of 8 items pass the approximate
metric-loading screen. At the
same time, scalar and threshold behavior is not fully interchangeable. C01,
C04, C05, and C07 recur as candidate anchors, while C02 and C06 recur as
hypothesis-generating localized threshold-shift candidates.

The descriptive item-level analysis makes the clinical shape of this result
visible. After conditioning on item-excluded total severity, the largest
non-sparse PHQ contrast is C02 anhedonia in the high-severity bin, where the
E-DAIC minus CMDC item-mean delta is -0.834 and the $P(Y \geq 2)$ delta is
-0.408. Large contrasts also appear for C08 psychomotor behavior and C06
self-worth. Thus, shared item names provide real construct alignment, but not
automatic score interchangeability.

![Figure 4. PHQ shared-item response patterns in E-DAIC and CMDC. Panel A compares item means over the eight shared PHQ symptoms. Panels B and C condition endorsement on item-excluded severity tertiles for C02 and C06, illustrating that shared item names can retain common symptom structure while still showing corpus-conditioned response behavior.](analysis/diagnostic_measurement_audit_paper/figures_core7/fig4_phq_shared_item_measurement_analysis.png){width=100%}

The formal and simulation checks support the same bounded interpretation.
Corrected external `mirt` replication preserves the qualitative localization
pattern, but the sample-size caveat is substantial. Under the observed
E-DAIC/CMDC sample sizes and severity distributions, C02/C06 both-flag recovery
is 0.662 under the planted shift world, while the H0 both-flag false rate is
0.208. We therefore treat C02/C06 as hypothesis-generating recurrent
threshold-shift candidates with finite-sample uncertainty. For the model, this
is enough to justify explicit target-measurement modeling, targeted calibration
checks, and fair tests of whether measurement parameters should be shared or
corpus-specific; it is not evidence for definitive item-level DIF.

The sensitivity grid makes this claim boundary clearer. Across loading
tolerances of 0.15--0.25, threshold tolerances of 0.25--0.45, and
minimum-anchor requirements of 3--5 items, the default C01/C04/C05/C07 anchor
set is exactly recovered in only one third of grid rows and retained in two
thirds. By contrast, C02 and C06 fail the threshold-support criterion across
all grid settings. Combining this grid with bootstrap DIF stability yields four
recurrent anchor candidates with strict-threshold caveats (C01, C04, C05, C07)
and two hypothesis-generating recurrent threshold-shift candidates with
finite-sample uncertainty (C02, C06). This strengthens the audit as a bounded
target-contract result while preserving the finite-sample caution, especially
for sparse response categories.

**Same-HAMD exploratory control.** CMDC/PDCH has one bounded role: it checks
whether the measurement concern is obviously reducible to the PHQ-8 versus
PHQ-9 form difference. The available HAMD sample is asymmetric, with 25 CMDC
HAMD subjects and 99 PDCH HAMD subjects, so we use it only as an exploratory
same-scale stress view. Its item distributions, item-excluded
severity-conditioned responses, and correlation structure show context-linked
differences, which is enough for the intended scope but not a formal HAMD
invariance claim.

![Figure 5. Same-lineage PHQ control and bounded target-contract stress views. The DAIC-WOZ/E-DAIC paired PHQ-8 comparison provides a low-difference sanity control, the E-DAIC/CMDC shared-PHQ comparison carries the main item-level measurement evidence, and CMDC/PDCH is retained only as a small exploratory same-HAMD view.](analysis/diagnostic_measurement_audit_paper/figures_core7/fig5_daicwoz_edaic_controlled_comparison.png){width=100%}

Taken together, the measurement gate provides the paper's central empirical
claim. Depression targets can share substantial clinical structure while still
showing corpus-conditioned response mechanisms. Clinical labels should
therefore not be treated as interchangeable targets until their measurement
contracts have been audited.

### 6.3 Prediction Gate: Target Calibration, Not Corpus-Specific Heads, Is the Robust Effect

The prediction gate asks whether the measurement audit matters once the
representation is fixed. All methods in Table 3 use the same frozen
Qwen3+WavLM+OpenFace subject-level representation and the same repeated
target-calibration splits within each transfer direction. The table is limited
to calibrated methods with matched target-label exposure. Zero-target-label
ERM, CORAL, MMD, DANN, latent-only, and fixed-split direct-transfer rows are
reported as supplementary context because they answer a different question:
what can be done without labeled target clinical data.

**Table 3. Main target-calibrated PHQ shared-item transfer result. Values are
means with 95 percent intervals over 30 repeated subject-level target
calibration/evaluation splits. All rows use frozen Qwen3+WavLM+OpenFace
representations. Lower is better. CITL is observed total minus predicted total;
the table reports $|\mathrm{CITL}|$ and $|\mathrm{slope}-1|$ as the main
calibration audit metrics, with binned calibration MAE as a secondary
calibration-curve summary.**

**Panel A. CMDC -> E-DAIC.**

| Method | Regime | k/eval n | Item MAE ↓ | \|CITL\| ↓ | \|slope-1\| ↓ | Binned CalMAE ↓ | Total MAE ↓ |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Target-only direct MLP | target only | 66/153 | 0.840 [0.786, 0.889] | 1.266 [0.202, 2.389] | 0.770 [0.610, 0.919] | 0.460 [0.362, 0.541] | 5.426 [4.910, 5.910] |
| Target-only ordinal | target only | 66/153 | 0.855 [0.804, 0.902] | 1.698 [0.635, 2.700] | 0.797 [0.680, 0.948] | 0.531 [0.445, 0.616] | 5.653 [5.238, 6.047] |
| Source warm-start target fine-tune | source + target | 66/153 | 0.862 [0.789, 0.927] | 0.895 [0.183, 1.935] | 0.774 [0.566, 0.957] | 0.475 [0.306, 0.612] | 5.602 [4.950, 6.329] |
| Source+target direct multitask | source + target | 66/153 | 0.890 [0.825, 0.954] | 0.587 [0.051, 1.608] | 0.819 [0.684, 0.974] | 0.514 [0.413, 0.607] | 5.836 [5.299, 6.547] |
| Generic target MLP head | source + target | 66/153 | 0.870 [0.787, 0.921] | 0.699 [0.029, 1.892] | 0.805 [0.622, 0.960] | 0.489 [0.363, 0.591] | 5.692 [5.101, 6.261] |
| Shared ordinal head | source + target | 66/153 | 0.875 [0.811, 0.948] | 1.063 [0.179, 1.970] | 0.789 [0.627, 0.927] | 0.516 [0.403, 0.627] | 5.723 [5.144, 6.364] |
| Measurement-aware ordinal | source + target | 66/153 | 0.873 [0.809, 0.955] | 1.080 [0.217, 2.119] | 0.787 [0.630, 0.923] | 0.517 [0.398, 0.634] | 5.714 [5.111, 6.358] |

**Panel B. E-DAIC -> CMDC.**

| Method | Regime | k/eval n | Item MAE ↓ | \|CITL\| ↓ | \|slope-1\| ↓ | Binned CalMAE ↓ | Total MAE ↓ |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Target-only direct MLP | target only | 24/20 | 0.645 [0.549, 0.779] | 1.560 [0.311, 3.040] | 0.149 [0.003, 0.385] | 0.423 [0.329, 0.548] | 3.759 [2.934, 4.928] |
| Target-only ordinal | target only | 24/20 | 0.660 [0.559, 0.803] | 1.590 [0.271, 3.476] | 0.191 [0.028, 0.420] | 0.463 [0.358, 0.603] | 3.905 [3.011, 5.367] |
| Source warm-start target fine-tune | source + target | 24/20 | 0.658 [0.562, 0.786] | 1.259 [0.079, 2.682] | 0.142 [0.004, 0.343] | 0.414 [0.302, 0.537] | 3.714 [2.833, 5.138] |
| Source+target direct multitask | source + target | 24/20 | 0.660 [0.549, 0.795] | 1.270 [0.105, 2.837] | 0.151 [0.017, 0.358] | 0.422 [0.295, 0.535] | 3.728 [2.779, 5.226] |
| Generic target MLP head | source + target | 24/20 | 0.654 [0.542, 0.790] | 1.184 [0.083, 2.416] | 0.149 [0.006, 0.388] | 0.392 [0.260, 0.507] | 3.734 [2.716, 5.223] |
| Shared ordinal head | source + target | 24/20 | 0.673 [0.563, 0.826] | 1.393 [0.149, 2.905] | 0.167 [0.019, 0.422] | 0.444 [0.318, 0.570] | 3.828 [2.929, 5.324] |
| Measurement-aware ordinal | source + target | 24/20 | 0.674 [0.563, 0.826] | 1.395 [0.144, 2.909] | 0.168 [0.020, 0.426] | 0.442 [0.318, 0.571] | 3.832 [2.933, 5.334] |

The table answers the main ablation concern directly. The old frozen
`Corpus-specific head` comparator is retained only in supplementary material
because it trains the target head while freezing the source-trained symptom
layer. Improvements over that row identify target-label calibration and
shared-layer adaptation, not the unique value of corpus-specific measurement
parameters.

Once target-only calibration is included, the strongest reconstruction result
is target-only rather than measurement-aware. At the default budgets, the
target-only direct MLP has lower Macro Item MAE than Measurement-aware ordinal
in both directions: 0.840 versus 0.873 for CMDC-to-E-DAIC and 0.645 versus
0.674 for E-DAIC-to-CMDC. The paired default-budget deltas for
Measurement-aware minus target-only are 0.033
[-0.038, 0.105] and 0.028 [-0.026, 0.106], respectively, and participant
bootstrap intervals likewise span zero. Extending the audit to
$k=4,8,12,16,24$ yields the same qualitative reconstruction pattern:
target-only direct calibration is the best Macro Item MAE row in all ten
direction-by-budget cells, while source-plus-target calibrated rows do not
produce a Macro Item MAE interval favoring them over target-only direct
calibration.

Source labels are still useful, but their strongest effect is calibration
rather than item reconstruction. In CMDC-to-E-DAIC, source-plus-target direct
multitask reduces absolute CITL from 1.266 for target-only direct MLP to 0.587,
and the generic target MLP head reduces it to 0.699. In E-DAIC-to-CMDC, the
generic target MLP head gives the lowest absolute CITL among the main rows
(1.184 versus 1.560 for target-only direct MLP) and also the lowest binned
calibration MAE (0.392). Across the small-budget sweep, source-plus-target
rows reduce absolute CITL in most method-budget-direction cells, but those
cell counts are descriptive sweep summaries rather than a separate
superiority test. The defensible conclusion is a tradeoff: source labels can
improve average calibration while target-only direct calibration remains the
strongest item-reconstruction baseline.

The direct test of corpus-specific ordinal parameterization is negative. The
Shared ordinal head and Measurement-aware ordinal rows use the same training
schedule and trainable shared layers; they differ only in whether the ordinal
head is forced to be shared or allowed to be corpus-specific. Their
default-budget Macro Item MAE is essentially tied in both directions: 0.875
versus 0.873 for CMDC-to-E-DAIC, and 0.673 versus 0.674 for E-DAIC-to-CMDC.
The paired shared-head minus measurement-aware deltas are 0.002
[-0.008, 0.018] and approximately 0.000 [-0.002, 0.001], with participant
bootstrap intervals spanning zero. Across the $k=4$--24 sweep,
Measurement-aware ordinal is lower on mean Macro Item MAE in only 3 of 50
matched method-budget-direction comparisons, and no participant-bootstrap
interval supports a uniform advantage. Thus corpus-specific ordinal heads are
a tested framework component, not an independently supported source of overall
gain in the real transfer experiment.

The item-targeted analysis reaches the same claim boundary. On the
measurement-gate C02/C06 threshold-shift candidate set, shared-head minus
measurement-aware MAE is only 0.004 in CMDC-to-E-DAIC and 0.002 in
E-DAIC-to-CMDC, with intervals spanning zero in both directions. The
C01/C04/C05/C07 anchor-candidate set is also near tied. A fixed-latent
companion simulation clarifies the mechanism boundary: when the latent
severity coordinate is given directly to the measurement head, adding
corpus-specific thresholds gives no useful benefit in a scalar-invariant
world, while a planted C02/C06 threshold-DIF world gives small C02/C06-set
advantages to corpus-specific heads (0.002 and 0.011 MAE). This supports the
audit-to-model logic at the level of a controlled mechanism check, but it does
not overturn the real-data result.

The prediction-gate reading is therefore deliberately modest. Target-label
calibration and shared-layer adaptation are empirically important. Ordinal
target modeling is competitive and may help against generic calibrated heads in
one transfer direction, but the effect is direction-dependent. Corpus-specific
ordinal parameterization has not shown an independent overall advantage over a
shared ordinal head or direct target-calibrated alternatives. MMD, localized
few-shot calibration, close depression-specific baselines, and binary clinical
endpoints are reported as supplementary stress views: they sharpen the same
claim boundary without changing the main result that target comparability,
calibration regime, and measurement-head sharing must be evaluated separately.

### 6.4 Supporting Clinical Grounding and Stress Views

The remaining analyses support the main chain without becoming separate paper
claims. PDCH-only HAMD item-derived prediction shows that the HAMD item signal
is learnable within a clinical consultation corpus. MPDD suggests that age,
personality, and psychomotor context are useful heterogeneity and calibration
axes. EATD provides an external SDS stress view under a different
emotional-context and scale contract. Evidence-grounding annotation supports
the use of symptom constructs as auditable evidence units. These analyses are
valuable as breadth and credibility checks, but the main contribution remains
the representation-measurement-prediction gate structure and the formal
fair-ablation test of calibrated PHQ shared-item transfer.

## 7 Discussion

The main implication is conceptual: cross-corpus depression shift has both an
input side and a target side. Raw corpus signatures show that acquisition,
language, task, and population context can be recoverable from frozen
representations, but controlled probes also show that this identity signal is
contrast-dependent. Target comparability therefore cannot be inferred from
representation identity alone. A feature-alignment method can make domains look
closer in representation space while leaving the PHQ or HAMD response mechanism
unexamined.

The modeling implication follows from the measurement results, but it must be
stated at the right strength. Measurement heterogeneity means the target
mapping should be made explicit and audited; it does not by itself prove that
each corpus needs an independent measurement head. The fair ablation shows why
this distinction matters. Much of the large gain over a frozen target-head
baseline comes from the target calibration regime, including the ability of
target labels to update trainable layers. But when target-only direct
calibration is added at matched budgets, it becomes the strongest Macro Item
MAE comparator at both default budgets and throughout the small-budget
sweep. Corpus-specific cumulative-logit heads remain a principled way to encode
different ordinal response processes, and the fixed-latent simulation shows
weak item-local benefit under planted C02/C06 threshold shift. The real-data
Shared-ordinal-head versus Measurement-aware comparison is essentially tied,
including on the targeted C02/C06 item set. The present evidence therefore
supports the architecture as a constructive target-contract instantiation, not
as a uniformly better method. The proposed model addresses calibrated
cross-corpus transfer rather than zero-target-label domain generalization: the
small labeled target calibration subset is part of the problem definition, not
an accidental advantage, and target-only calibration must be reported beside
source-plus-target calibration.

For benchmark practice, the paper suggests a simple reporting discipline.
Cross-corpus depression results should state the scale and item contract, the
source of the clinical target, and the target-label supervision regime before
claiming generalization. Zero-target-label domain generalization, unlabeled
target adaptation, and labeled target calibration are different experimental
questions. Treating them as interchangeable can make a transfer result look
stronger or weaker than the evidence supports. Separating these regimes lets
negative, asymmetric, and bounded transfer outcomes become diagnostically
useful rather than noise around a single leaderboard number.

## 8 Scope and Limitations

Several design choices define the scope of the paper.

First, DAIC-WOZ and E-DAIC are used as a same-lineage Wizard-of-Oz benchmark
view and PHQ-8 control, not as independent pooled corpora. That choice is
important to the story: their near-identity anchors the low-difference
reference point.

Second, the E-DAIC/CMDC PHQ comparison is a corpus-group analysis. It supports
corpus-conditioned shared-item measurement heterogeneity, but it does not
assign the difference to one isolated cause such as language, country,
translation, protocol, severity distribution, or population.

Third, CMDC/PDCH HAMD is an exploratory same-scale view because CMDC contains
only 25 HAMD subjects. Its role is to broaden the argument beyond PHQ form
alignment, not to serve as a formal HAMD invariance study.

Fourth, encoders are frozen, but the calibrated ablation shows that target
labels updating the shared projector and symptom layers is itself a major
effect. End-to-end encoder adaptation is outside the present scope.

Fifth, the formal model studies calibrated cross-corpus transfer rather than
zero-target-label domain generalization. The zero-target-label rows provide
representation-adaptation context, while architecture-level claims are made only
against calibrated baselines with the same target labels and comparable shared
adaptation exposure.

Sixth, the paired tests over the original five seeds are useful for detecting
large fairness failures, but they are not sufficient as the main evidence for
small architecture superiority, especially in the E-DAIC-to-CMDC direction
where the target evaluation set is small. We therefore treat the repeated
target-calibration splits and participant-bootstrap deltas as the relevant
uncertainty layer for calibrated architecture claims.

Seventh, the audit is about cross-corpus score interpretation and
target-comparability, not about proving the construct, criterion, or clinical
validity of PHQ, HAMD, or SDS. The instruments are treated as the available
benchmark targets, and the question is whether those targets can be compared
across corpus contracts.

Eighth, the E-DAIC/CMDC shared-PHQ psychometric layer is intentionally
evidence-bounded. The main item-level analysis uses 219 E-DAIC and 77 CMDC
subjects over eight four-category items, so C02/C06 are
hypothesis-generating localized threshold-shift candidates, not definitive DIF
discoveries. The stronger conclusion is that exact observed-score
interchangeability is unsupported under the current audit.

Ninth, interviewer leakage and criterion contamination remain only partially
controlled. E-DAIC participant-only and interviewer-only transcript controls
are blocked by the available transcript contract. The repeated-turn Qwen3
prompt-proxy and CMDC criterion-overlap deletion analyses are useful
stress tests, but they do not prove that prompt or questionnaire-like content
has no effect.

## 9 Conclusion

Cross-corpus depression detection should not begin by assuming that all
depression labels are interchangeable targets. Across six corpus families and
one DAIC-lineage benchmark view, we find strong raw corpus signatures with
control-dependent residual identity, a graded empirical pattern of measurement
comparability, and prediction consequences that cannot be explained by encoder
strength alone.
DAIC-WOZ/E-DAIC provides the low-difference PHQ-8 control; E-DAIC/CMDC reveals
cross-language PHQ
shared-item differences; CMDC/PDCH adds exploratory same-HAMD support.

The resulting lesson is direct: before aligning representations, audit target
comparability. A target-comparability audit framework gives future systems a
practical way to do that, and the fair ordinal-head ablation shows both the
promise and the claim boundary. The robust empirical lesson is that
target-label calibration and adaptation regime matter; target-only direct
calibration is a strong and often lower-error baseline; and corpus-specific
ordinal heads have not yet shown an independent overall advantage over a shared
ordinal head in the real E-DAIC/CMDC transfer setting. Strong encoders and
multimodal foundation models can still do what they do well, but clinical
measurement contracts, target-only calibration, source-plus-target
calibration, shared-layer adaptation, and corpus-specific measurement
parameterization must be reported separately. This makes cross-corpus
depression benchmarks harder to overread, but easier to trust.
