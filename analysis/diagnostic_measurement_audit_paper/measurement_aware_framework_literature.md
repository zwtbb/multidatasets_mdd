# Measurement-Aware Cross-Corpus Depression Detection Framework

This note records the literature-backed measurement-aware framework added to
the current RQ-reframed manuscript. It is a solution scaffold and method
formulation for future systems, while the current paper evaluates it through
modular audit and prediction-consequence experiments. After the
foundation-model critique, the framework should be read as
foundation-backbone compatible: the encoder may be a large text, speech,
video, or multimodal model, but the target pathway remains a latent symptom
layer plus corpus-specific measurement heads.

## Why This Framework

Most cross-corpus depression models treat transfer as a representation problem:
learn features that are less corpus-identifiable, then predict the same label.
Foundation-model work strengthens this side of the field: DepressionLLM uses
large multimodal/foundation models for interpretable depression detection, and
SCD-MLLM focuses on stable cross-domain depression recognition under missing
modalities. The audit argues that these stronger backbones do not remove the
target-validity question because the label mechanism can vary across corpora:

$$
P_D(X, Y \mid \theta)=P_D(X \mid \theta)P_D(Y \mid \theta).
$$

Domain adaptation mainly targets $P_D(X \mid \theta)$. A measurement-aware
framework also audits and models $P_D(Y \mid \theta)$.

## Literature Basis

| Area | Use in framework | Key sources |
| --- | --- | --- |
| Measurement invariance | Defines when scores can be compared across groups and why item/scale bias matters before group comparison. | Meredith 1993; Vandenberg and Lance 2000 |
| Ordinal IRT and DIF | Provides item-response and threshold language for PHQ/HAMD ordinal items. | Samejima 1969; Chalmers 2012; Bulut and Suh 2017 |
| Approximate alignment | Supports a partial-invariance stance when exact invariance is unrealistic. | Muthen and Asparouhov 2014 |
| Domain adaptation | Gives the representation-alignment baseline that the paper argues is necessary but insufficient. | Ganin et al. 2016 |
| Calibration and label shift | Supports lightweight corpus-specific output heads and post-hoc adjustment, while keeping the claim bounded. | Guo et al. 2017; Lipton et al. 2018 |
| Protocol shortcut audits | Motivates separating participant symptom evidence from interviewer/protocol artifacts in clinical interview corpora. | Burdisso et al. 2024; Zhang and Poellabauer 2025 |
| Depression benchmark context | Grounds DAIC/DAIC-WOZ/E-DAIC and questionnaire-grounded depression detection. | Gratch et al. 2014; USC ICT 2026; Nguyen et al. 2022 |
| Foundation depression models | Establishes that current depression detection is moving toward large multimodal backbones and cross-corpus training. | Teng et al. 2026; Chen et al. 2026 |
| Foundation encoders | Supplies strong text/audio/video backbones for the validation contract. | Qwen Team 2024; Zhang et al. 2025; Chen et al. 2022; Baevski et al. 2020; Hsu et al. 2021; Tong et al. 2022 |
| Domain-generalization baselines | Provides the feature-alignment and robustness baselines that should be compared against measurement-aware heads. | Ganin et al. 2016; Sun et al. 2016; Long et al. 2015; Arjovsky et al. 2019; Sagawa et al. 2019 |

## Framework Contract

1. Predeclare a target contract for each corpus: instrument, item set, language,
   scoring rule, rater/protocol context, and available anchors.
2. Learn transferable symptom evidence only where the item/construct map is
   audited. A shared label name is not a sufficient contract.
3. Predict observed labels through corpus-specific measurement heads:

   $$
   Z=E_\phi(X), \quad S=h_\phi(Z), \quad \hat{Y}^{(D)}=g_D(S).
   $$

4. Adapt the measurement head before adapting the encoder when only a small
   number of target labels is available.
5. Report measurement gates alongside prediction metrics: representation
   identity, measurement comparability, observed-scale validity, calibration, and
   external transfer.

For the foundation-backbone version, replace the single encoder with a
modality-specific backbone stack:

$$
Z = p_{\phi}\left(E_{\text{text}}(X_{\text{text}}),
E_{\text{audio}}(X_{\text{audio}}),
E_{\text{video}}(X_{\text{video}})\right),
\quad
S=h_\phi(Z),
\quad
\hat{Y}^{(D)}=g_D(S).
$$

The minimal validation contrast is therefore not "small encoder versus large
encoder." It is:

1. ERM/direct observed-label head on the same backbone.
2. Representation-alignment baselines: DANN, CORAL, MMD/DAN, IRM, GroupDRO.
3. Measurement-aware adaptation: shared depression representation, latent
   symptom layer, corpus-specific measurement head, and measurement-validity
   gates.

An end-to-end instantiation can optimize:

$$
\mathcal{L}
=
\mathcal{L}_{\theta}\left(h_{\phi}(E_{\phi}(X)), \tilde{\theta}\right)
+ \lambda \mathcal{L}_{\mathrm{obs}}\left(g_D(S), Y^{(D)}\right)
+ \beta \mathcal{L}_{\mathrm{anchor}}\left(g_D, A_D\right),
$$

where $\tilde{\theta}$ is the audited latent severity target, $S$ is predicted
symptom evidence or latent severity, $g_D$ is the corpus-specific measurement
head, and $A_D$ denotes anchor/shared-item constraints.

## Claim Boundary

The current paper should claim that this is a practical audit-to-model
framework. The empirical contribution is the benchmark-validity audit plus the
prediction stress tests showing which parts of the framework are useful and
which validity gates remain necessary. The foundation-backbone validation
contract is the strongest next experiment because it tests whether the
measurement-aware claim remains true after the representation side is made
competitive with current large-model depression detection systems.
