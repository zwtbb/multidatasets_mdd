# MV22-MV24 Foundation-Backbone Measurement-Aware Validation Contract

Status: foundation text slice, lightweight multimodal completion slice, and
formal measurement-aware ordinal main table complete. Extended WavLM
Large/HuBERT Large/VideoMAE/fine-tuning sensitivities remain future scope.

Executed first slice:

- Runner:
  `scripts/phase5_run_mv22_foundation_backbone_validation.py`.
- Aggregate output:
  `analysis/phase5_minimal_validation/p5_mv22_foundation_backbone_validation/`.
- Text backbone: `Qwen/Qwen3-Embedding-0.6B`, frozen, last-token pooling,
  2048-token chunks, local-only subject feature caches.
- Reused diagnostic chain: MV07, MV12, and MV15 rerun on Qwen features.
- Baseline suite: ERM itemwise Ridge, CORAL itemwise Ridge, MMD/DAN-style mean
  alignment, DANN itemwise MLP, IRM severity-environment proxy, GroupDRO
  severity proxy, plus MV12 measurement-aware aggregate references.
- Audio view: existing WavLM base-plus subject features are included as an
  audio foundation proxy in aggregate coverage and Qwen+audio proxy baselines.
  WavLM Large is recorded as not executed in this first compute slice.
- Artifact boundary: feature caches, row predictions, learned parameters, and
  participant-level outputs remain local-only/ignored; tracked MV22 files are
  aggregate-only and pass artifact hygiene.

Executed multimodal completion slice:

- Runner:
  `scripts/phase5_run_mv23_foundation_multimodal_completion.py`.
- Aggregate output:
  `analysis/phase5_minimal_validation/p5_mv23_foundation_multimodal_completion/`.
- Feature views: WavLM base-plus audio, wav2vec2-base audio, OpenFace common
  video proxy, Qwen3+audio, and Qwen3/BGE-M3/multilingual-E5 text-audio-video
  fusion views.
- Baseline suite: ERM, CORAL, MMD/DAN-style mean alignment, DANN, IRM
  severity-environment proxy, GroupDRO severity proxy, plus a lightweight
  measurement-aware latent-total proxy head with a target-corpus PHQ shared-item
  reconstruction head.
- Artifact boundary: MV23 writes no row predictions, feature matrices, theta
  tables, or learned model internals. Tracked MV23 files are aggregate-only and
  pass artifact hygiene.

Executed formal method slice:

- Runner:
  `scripts/phase5_run_mv24_measurement_aware_ordinal_model.py`.
- Aggregate output:
  `analysis/phase5_minimal_validation/p5_mv24_measurement_aware_ordinal_model/`.
- Official representation: frozen Qwen3-Embedding-0.6B text subject features,
  WavLM base-plus speech subject features, and OpenFace common video statistics.
- Architecture: trainable projector, shared eight-dimensional PHQ symptom
  layer, and corpus-specific cumulative-logit ordinal heads for the eight
  PHQ shared items.
- Training protocol: source warm-start, source-head initialization of the
  target ordinal head, then target-calibrated measurement-aware adaptation.
- Formal core loss:
  `L_MA = NLL_src + lambda_cal*NLL_tgt_cal + lambda_l2*||S||^2`.
- Auxiliary variant:
  `L_MA+MMD = L_MA + lambda_mmd*MMD(S_src,S_tgt)`.
- Main table: ERM, CORAL, MMD, DANN, strongest direct foundation baseline,
  latent-only, corpus-specific-head, direct target fine-tuning, direct
  source+target multitask, shared ordinal head, generic target MLP head,
  measurement-aware, and measurement-aware + MMD across both E-DAIC<->CMDC PHQ
  shared-item directions with 5 seeds, 95 percent CIs, and explicit
  target-label supervision regimes.
- Result: the fair shared-layer calibrated ablation gate is
  `not_passed_uniform_measurement_pathway_superiority`. The large gain over the
  frozen corpus-specific-head baseline supports target calibration/shared-layer
  adaptation, but does not by itself identify corpus-specific ordinal
  measurement parameterization as the source of the improvement. A targeted
  item-level analysis further shows shared ordinal and corpus-specific ordinal
  heads are near tied on both all shared PHQ items and the measurement-gate
  `C02/C06` threshold-shift item set. The companion fixed-latent DIF simulation
  supports only weak item-local mechanism consistency under planted `C02/C06`
  threshold DIF, not a real-data superiority claim. The MMD variant remains
  auxiliary.
- Artifact boundary: MV24 writes aggregate metrics and contracts only; no row
  predictions, feature matrices, model checkpoints, or learned parameters are
  tracked.

This contract addresses the large-scale validation gap without turning the
paper into a generic depression-detection leaderboard. The research question is
not whether a larger encoder gives better scores. The question is whether the
target measurement contract still has to be audited when the representation
side uses current foundation-model backbones, and whether shared or
corpus-specific head parameters are actually justified by the target evidence.

## Core Claim To Test

Strong foundation representations may reduce raw prediction error or output
identity, but cross-corpus depression detection is still governed by two
mechanisms:

$$
P_D(X,Y \mid \theta)=P_D(X \mid \theta)P_D(Y \mid \theta).
$$

Foundation backbones mainly improve $P_D(X \mid \theta)$ modeling. MV22/MV23
test whether explicit modeling of $P_D(Y \mid \theta)$ through latent symptom
layers and corpus-specific measurement heads remains necessary under stronger
text, audio, video-proxy, and fused representations.

## Architecture

The intended model is:

$$
\text{Multimodal Foundation Encoder}
\rightarrow
\text{Shared Depression Representation}
\rightarrow
\text{Latent Symptom Layer}
\rightarrow
\text{Corpus-Specific Measurement Head}
\rightarrow
\text{PHQ/HAMD Reconstruction}.
$$

For modality-specific inputs:

$$
Z = p_{\phi}\left(E_{\text{text}}(X_{\text{text}}),
E_{\text{audio}}(X_{\text{audio}}),
E_{\text{video}}(X_{\text{video}})\right),
\quad
S=h_\phi(Z),
\quad
\hat{Y}^{(D)}=g_D(S).
$$

The executed formal version freezes the large backbones and trains only the
projector, symptom layer, and measurement heads. Full fine-tuning is not part
of the current contract because it would blur whether gains come from the
measurement mechanism or from representation scale.

## Backbone Tiers

| Tier | Primary choice | Sensitivity choices | Purpose |
| --- | --- | --- | --- |
| Text foundation | Qwen3-Embedding | Qwen2.5-7B-Instruct hidden states, Llama-3.1-8B hidden states, BioClinicalBERT for English-only sensitivity | Test whether stronger transcript representations remove or retain measurement-related failure modes |
| Speech foundation | WavLM Large | wav2vec2-large, HuBERT Large | Replace traditional acoustic features with current speech foundation representations |
| Video/behavior | OpenFace plus optional VideoMAE | Existing challenge video features where raw video is unavailable | Keep visual evidence comparable while allowing a foundation-video sensitivity |
| Multimodal | Frozen text/audio/video features plus small projector | Late fusion and gated fusion sensitivity | Test whether fusion should predict observed PHQ/HAMD directly or pass through a latent symptom layer |

DAIC-WOZ must remain a same-lineage PHQ-8 control, not an independent pooled
corpus. CMDC-HAMD remains exploratory because the CMDC HAMD sample is small.

## Baseline Suite

All baselines use the same subject-level splits and the same available
modalities for a given corpus pair.

| Method | What it tests |
| --- | --- |
| ERM direct observed-label head | Strong-backbone vanilla prediction |
| ERM latent target head | Whether latent severity alone helps without corpus-specific measurement heads |
| DANN | Domain-adversarial feature invariance |
| CORAL | Covariance alignment |
| MMD/DAN | Distribution matching in feature space |
| IRM | Invariant predictor pressure across source environments |
| GroupDRO | Worst-group robustness across corpus/domain groups |
| Measurement-aware adaptation | Shared representation plus latent symptom layer plus corpus-specific measurement head |

The key comparison is not only MAE/AUC. A feature-alignment method can improve
domain invariance while worsening observed-scale measurement validity. That is
central evidence for the paper, not a side issue.

## Evaluation Metrics

Prediction metrics:

- PHQ/HAMD total MAE and RMSE where totals are available.
- Binary/severity AUC, balanced accuracy, and macro-F1 where labels are
  categorical.
- Within-dataset and cross-corpus transfer results under identical train/dev
  and train/test contracts.

Measurement-validity metrics:

- Observed-scale reconstruction error for each corpus head.
- Shared-item PHQ reconstruction and item-excluded severity-conditioned item
  deltas.
- HAMD exploratory reconstruction on CMDC/PDCH, reported only as bounded
  same-scale support.
- Output-level corpus identity and latent-conditioned feature identity.
- Calibration error by corpus and severity bin.
- Few-shot target-head adaptation curves at small $k$.

## Main Experiments

Experiment 1: Foundation models still retain corpus identity.

- Compare BGE-M3, multilingual-E5, Qwen3-Embedding, WavLM Large, and
  multimodal foundation features.
- Report dataset/protocol identity probes.
- Desired conclusion shape: stronger backbones may reduce some identity, but
  corpus signatures remain measurable enough to require explicit gates.

Experiment 2: Clinical target measurement mismatch persists under strong
representations.

- Keep the MV21 measurement gradient: DAIC-WOZ/E-DAIC, E-DAIC/CMDC, CMDC/PDCH.
- Add strong-backbone prediction residuals and measurement-head reconstruction
  diagnostics.
- Desired conclusion shape: the issue is not merely weak representation; target
  mechanisms remain part of the transfer problem.

Experiment 3: Measurement-aware adaptation improves cross-corpus
generalization and transfer validity.

- Compare ERM, DANN, CORAL, MMD/DAN, IRM, GroupDRO, and measurement-aware
  adaptation on the same foundation features.
- Report both prediction and measurement-validity metrics.
- Desired conclusion shape: the method should improve or trade off favorably
  on prediction error and measurement validity, not only reduce feature identity.

## Interpreting Negative Or Bounded Results

Useful negative result:

- Foundation backbones improve raw error but measurement mismatch remains.
- Domain adaptation reduces feature identity but fails observed-scale validity.
- Measurement-aware heads improve calibration or reconstruction even when
  feature identity remains partially recoverable.

Weak result:

- Measurement-aware heads do not improve prediction or measurement validity over direct ERM
  under any backbone.

If the weak result occurs, it should be reported as a stress test of the
framework rather than hidden. It would not invalidate the benchmark-validity
audit, but it would mean the proposed method should remain a framework
recommendation rather than an empirical solution claim.

## Non-Goals

- Do not claim depression-detection SOTA.
- Do not pool DAIC-WOZ and E-DAIC as independent corpora.
- Do not reopen full PHQ/HAMD MIM/IRT beyond the current bounded evidence.
- Do not tune contamination/criterion-overlap variants from MV20.
- Do not write row-level predictions, theta scores, fitted psychometric
  parameters, or raw feature caches into Git.

## Launch Gate

The minimal first run has been executed after explicit user approval. It used:

1. Qwen3-Embedding-0.6B for text.
2. Existing WavLM base-plus subject features as an audio foundation proxy.
3. Frozen feature adapters plus lightweight itemwise/latent references.
4. ERM, DANN, CORAL, MMD/DAN-style mean alignment, IRM proxy, GroupDRO proxy,
   and measurement-aware MV12 aggregate references.

The first run passes data and runtime hygiene.

The multimodal completion run has also been executed after the user requested
continuing until the practical experiment queue was complete. It used:

1. Existing WavLM base-plus and wav2vec2-base audio subject caches.
2. Existing OpenFace common video-proxy subject caches.
3. Qwen3/BGE-M3/multilingual-E5 text features fused with audio/video proxies.
4. ERM, DANN, CORAL, MMD/DAN-style mean alignment, IRM proxy, GroupDRO proxy,
   and a lightweight measurement-aware latent-total proxy head.

MV23 passes aggregate artifact hygiene. WavLM Large, HuBERT Large, VideoMAE,
and fully end-to-end multimodal fine-tuning can follow only under a new compute
contract; they are not required for the current paper's bounded foundation-era
stress-test claim.

The formal MV24 method table has also been executed after the user requested a
single concrete architecture and a clean main-result table. It uses the
official Qwen3+WavLM+OpenFace representation and reports both reconstruction
and calibration. The regenerated table separates zero-target-label baselines
from target-calibrated measurement-head variants because measurement-aware,
measurement-aware + MMD, and corpus-specific-head all use target calibration
labels. The fair same-budget conclusion is not uniform superiority of
corpus-specific measurement heads: the robust empirical finding is that target
calibration with shared-layer adaptation improves over a frozen source
representation, while ordinal target modeling is competitive and
direction-dependent. Shared ordinal and corpus-specific ordinal heads are near
tied in both directions, including on the targeted `C02/C06` item-set analysis.
Zero-target-label baselines remain in the table as context and as evidence that
feature alignment alone is not the whole target-validity story.

MV25 adds the companion diagnostic repair for provenance and corpus identity.
DAIC-WOZ/E-DAIC is now documented as a same-lineage PHQ-8 sanity control rather
than independent-corpus evidence. Controlled identity probes show that raw
E-DAIC/CMDC identity is largely explained by length/protocol controls, while
same-language E-DAIC lineage probes remain high after length and severity
residualization. Use that controlled evidence when writing the representation
gate.
