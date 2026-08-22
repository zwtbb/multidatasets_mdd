# Before Aligning Representations, Align the Target

A Measurement-Validity Audit of Cross-Corpus Depression Detection

Generated: `2026-08-22T07:57:39+00:00`

## Draft Status

This is a generated manuscript draft for human editing. It consolidates aggregate paper artifacts only; it is not a new experiment run and it does not authorize claims beyond the full-method gate.

- Full-method gate: `blocked_but_publishable_diagnostic_direction`; full method allowed: `False`.
- Claim table status: `ready_for_diagnostic_paper_drafting`.
- Data-governance section status: `ready_for_manuscript_drafting`.
- Results scaffold status: `ready_for_manuscript_editing`.
- Bibliography status: `ready_for_manuscript_citation_editing`; hygiene passed: `True`.

## Abstract

Cross-dataset depression detection is usually evaluated as a prediction problem, but pooled performance can hide a prior validity question: do different corpora measure the same target? We audit six depression corpora with registry-governed dataset roles, subject-level split contracts, dataset-group label contracts, and artifact-hygiene gates. The baseline matrix completes 66 applicable runs and serves as a reproducibility floor rather than the central novelty. Failure-mode diagnostics show that dataset and protocol identity are strongly recoverable from common frozen feature spaces, motivating conditional identity checks before shared-representation claims. Label-only E-DAIC/CMDC PHQ analyses then show substantial common structure but not uniform threshold or scalar equivalence: C01/C04/C05/C07 recur as anchors and C02/C06 recur as localized threshold-shift items, while finite-sample simulation downgrades those item-level claims from robust standalone DIF to observed-N-bounded dataset-group evidence. The old BGE-linked multimodal chain is treated as legacy/diagnostic because its E-DAIC feature contract used a Chinese encoder on English transcripts and available transcript rows are not speaker-resolved; MV17a repeats the paper-critical MV07/MV12/MV15 chain with BGE-M3 and multilingual-E5 and still reproduces the blocked pattern. Under that caveat, latent-target prediction improves within-dataset theta utility, but it is Pareto-dominated by a dimension-matched direct severity control and fails zero-shot source-calibrated external theta transfer. A later latent-conditioned identity audit keeps BGE feature identity high after theta and severity conditioning, and the DIF-guided few-shot calibration ladder fails the predeclared both-direction small-k mechanism gate. We therefore frame the contribution as a measurement-validity audit: feature alignment alone cannot solve cross-corpus learning if the target measurement function also shifts.

## Contributions

1. A measurement-validity framework for cross-corpus depression detection: feature shift, target measurement shift, and prediction shift are distinct failure modes.
2. Empirical label-only psychometric evidence that E-DAIC and CMDC share substantial PHQ structure while exhibiting repeated but finite-sample-bounded C02/C06 threshold non-equivalence and convergence-aware uncertainty.
3. A prediction-level consequence: current `X -> theta` models do not automatically improve observed-scale prediction, zero-shot transfer, or representation invariance over dimension-matched severity controls.

## Introduction

Depression-detection datasets differ in more than sample size or modality. They differ in interview protocol, language, clinical setting, scale family, item coverage, and population context. Official DAIC materials describe clinical interviews distributed under access constraints, while the PDCH repository describes real face-to-face consultation data paired with HAMD-17 assessments. Prior questionnaire-grounded depression-detection work shows that symptom instruments can improve out-of-domain generalization, but the present audit asks a preceding measurement question: whether datasets and scales define sufficiently comparable targets for a shared representation.

Let `D` denote dataset/protocol/population, `theta` the latent depressive trait, `X` the observed language/audio/video/behavioral signal, and `Y` the observed scale response. The relevant factorization is `P(X,Y | theta,D) = P(X | theta,D) P(Y | theta,D)`. Most domain-alignment work targets the first factor, but cross-corpus validity also requires asking whether the second factor is stable. A symptom-aligned framework remains scientifically attractive, but it cannot be assumed from pooled model performance. Classical measurement-invariance and IRT sources, including PHQ invariance work and the graded-response model family used by `mirt`, motivate treating PHQ-8/PHQ-9/HAMD/SDS as related but non-identical measurement contracts. This paper therefore reports a governed sequence of baselines, shortcut diagnostics, label-only psychometric checks, legacy multimodal latent-target tests, identity conditioning, few-shot DIF-guided calibration, and aggregate evidence localization.

## Methods

### Data Governance And Label Contracts

This study treats cross-dataset depression detection as a measurement problem before it treats it as a model-capacity problem. The data layer is governed by a registry-first workflow: each corpus is assigned a scientific role, protocol axis, modality set, and label contract before any pooled modeling claim is considered. Raw datasets and real row-level tables remain local-only; the public repository contains scripts, schemas, synthetic examples, aggregate audits, claim gates, and paper-critical summaries.

The governed corpus currently spans `6` datasets and `891` audited subjects. Phase 4 defines `15` symptom constructs and `54` mapped scale items. Item-level supervision is available for `4` dataset-scale contracts and absent or total-only for `3` contracts. This difference is central to the paper: PHQ-8/PHQ-9 provide the cleanest C01-C08 shared bridge, PDCH provides the strongest HAMD-17 item-level clinical validation, CMDC HAMD remains a small sanity subset, and EATD/MODMA/MPDD primarily serve stress-test or context roles rather than item-level construct supervision.

The release boundary is deliberately conservative. Real identifiers, labels at row granularity, local file references, media, raw transcripts, learned parameters, embeddings, row predictions, private evidence workbooks, and verbatim evidence excerpts remain local-only. Public artifacts are limited to code, schemas, synthetic examples, aggregate audit summaries, and paper-facing tables that pass artifact hygiene. This policy preserves reproducibility of the experimental logic without redistributing licensed or privacy-sensitive material.

Table 1 summarizes the governed dataset roles used by the manuscript draft.

| dataset | role | protocol | modalities | subjects | valid rows | primary scale | item supervision | quality note |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| E-DAIC | primary development | virtual interview | text;audio;video | 275 | 275 | PHQ-8 | item level available | E-DAIC is the primary development set |
| CMDC | chinese cross protocol language validation | clinical interview | text;audio;video | 78 | 908 | PHQ-9 | item level available | Metadata has duplicate/omitted subject-info entries; modality availability varies by row. |
| PDCH | hospital consultation hamd validation | face to face consultation | text;audio | 100 | 165 | HAMD-17 | item level available | One consultation subject lacks HAMD annotation; supervised HAMD rows use labeled subset only. |
| MODMA | controlled speech task stress test | interview reading picture | audio | 52 | 1503 | PHQ-9 | total only | 5 invalid audio rows are excluded; task type is a stress-test axis. |
| EATD-Corpus | chinese valence stress test | positive neutral negative emotion tasks | text;audio | 162 | 486 | SDS | total only | Use positive, neutral, and negative tasks to separate depression signal from transient emotional valence |
| MPDD-AVG-2026 | individual difference psychomotor validation | age personality gait multimodal | audio;video;gait;personality | 224 | 602 | PHQ-9 | total only | Local labels cover train subjects only; gender/health structured fields remain incomplete. |

Table 2 records the label contracts that determine which datasets can support item-level construct analyses.

| dataset | scale | total subjects | item subjects | supervision | paper boundary |
| --- | --- | --- | --- | --- | --- |
| edaic | PHQ-8 | 275 | 219 | item level available | eligible for item-level minimal validation under subject-level splits |
| cmdc | PHQ-9 | 77 | 77 | item level available | eligible for item-level minimal validation under subject-level splits |
| cmdc | HAMD-17 | 25 | 25 | item level available | sanity subset only; do not claim complete CMDC HAMD supervision |
| pdch | HAMD-17 | 99 | 99 | item level available | eligible for item-level minimal validation under subject-level splits |
| modma | PHQ-9 | 52 | 0 | total only | use as total/severity stress or context target only; no item-level construct claim |
| eatd | SDS | 162 | 0 | total only | use as total/severity stress or context target only; no item-level construct claim |
| mpdd avg 2026 | PHQ-9 | 175 | 0 | total only | use as total/severity stress or context target only; no item-level construct claim |

### Analysis Sequence

The analysis sequence is organized into three layers. First, representation/protocol shift asks how strongly `X` carries dataset, task, question, language, and population signatures. Second, target measurement shift asks whether item response functions vary by dataset/group after accounting for latent severity. Third, prediction shift asks whether an `X -> theta` model transfers once measurement has been harmonized. Phase 2 is a reproducibility floor, Phase 3 is motivating shortcut evidence, MV10/MV11/MV13/MV14/MV19 are the psychometric layer, and MV12/MV15/MV16 test prediction consequences under the old BGE caveat plus the completed MV17a multilingual sensitivity. All modeling rows use subject-level splits. Generated row predictions, learned parameters, feature caches, theta scores, source locators, evidence workbooks, and private clinical text remain local-only.

### Claim Gate

Full gate reads 43 Phase 5 summaries; status blocked_but_publishable_diagnostic_direction; full_method_allowed=False.

The manuscript therefore reports allowed-limited and blocked claims explicitly. Broad M0/M1/M2/M3 construction remains blocked; the paper is allowed only as a measurement-validity diagnostic contribution.

## Results

### Baselines

The baseline phase defines the reproducibility floor for later diagnostic claims. The matrix contained `67` planned runs, of which `66` completed and `1` was conditionally excluded; no applicable run remains blocked. The final audit contains `313` completed metric rows and `5` not-applicable metric rows, with five seeds used for completed runs and `1000` bootstrap resamples recorded by the metric audit. The Phase 2 completion verdict is complete, and the method-design gate recommendation is `ready`.

These baselines should be read as governance evidence rather than as the paper's main novelty. The matrix covers simple unimodal and fusion families across six datasets, while intentionally excluding incompatible public reproductions from the canonical matrix when their split, feature, or evaluation contract differs. The hygiene audit passed and reviewed `39` canonical prediction files locally, but generated Phase 2 result artifacts remain local by default. The manuscript should therefore cite Phase 2 as a completed, subject-level baseline floor and avoid using it as a public artifact dump.

### Failure-Mode Diagnostics

Phase 3 shows why direct pooled training is not enough evidence for a shared depression representation. Across `7` dataset/protocol identity probes, dataset identity is highly recoverable from frozen feature spaces: six-way WavLM identity reaches balanced accuracy `0.990`, CMDC/PDCH BGE text reaches `1.000`, and E-DAIC/CMDC OpenFace reaches `1.000`. These probes do not prove every identity signal is harmful, but they establish that dataset identity must be reported, controlled, or conditioned before interpreting pooled performance as construct transfer.

Protocol controls sharpen the same conclusion at the interview-content level. The E-DAIC/CMDC protocol-control run completed `60` runs over `5` seeds with artifact hygiene passing. In E-DAIC, front-position dialogue text improves binary Macro-F1 by `0.109` versus full dialogue, and repeated-turn-only text improves it by `0.181`. In CMDC, Q10-only binary Macro-F1 drops by `-0.374` versus all questions. The right paper wording is therefore question-position and fixed-protocol dependence; literal participant-only or interviewer-only claims remain blocked because speaker-resolved fields are unavailable.

Task and valence diagnostics separate supported protocol stress from unsupported valence mechanisms. MODMA cross-task evaluation lowers balanced accuracy by `0.099` overall, with the affective-task evaluation drop reaching `0.142` and a 95 percent interval from `0.003` to `0.280`. EATD does not show the hypothesized healthy-negative shortcut in the current audio diagnostic: healthy negative predicted-depressed rate is `0.118` versus `0.206` for healthy nonnegative material. MODMA can support bounded task-control evidence; EATD should remain a negative stress test rather than a valence-adversarial method driver.

MPDD supports a population-heterogeneity audit but not a positive context-conditioning method. On `175` labeled train subjects, personality-only text beats shuffled personality by Macro-F1 `0.116` and QWK `0.272`, yet audio-video-personality fusion adds only Macro-F1 `0.001` and QWK `0.001` over audio-video alone. Subgroup calibration remains material, with age ECE gap `0.132` and personality-bin ECE gap `0.289`. Gait has modest psychomotor-context association with PHQ-9, top absolute Spearman `0.269`, while gender and health analyses remain `blocked` because structured fields are missing.

### Measurement Results

The Phase 5 full-method gate now reads `43` aggregate evidence summaries and remains blocked, while allowing a measurement-shift and measurement-invariance paper direction. This is the central Results boundary: the evidence is rich enough to explain why cross-dataset depression transfer is hard, but not for starting or claiming the full M0/M1/M2/M3 symptom-aligned method.

The measurement story is best read at three levels: feature/domain shift (`P(X|D)`), target-measurement shift (`P(Y|theta,D)`), and latent prediction stability (`P(theta_hat|X,D)`). MV09 addresses the first level by showing that dataset identity remains high after legitimate conditioning; MV10/MV11/MV13/MV14/MV19 address the second level by showing substantial common PHQ structure with repeated C02/C06 threshold non-equivalence, convergence-aware model-selection uncertainty, and an observed-N finite-sample downgrade rather than uniformly supported exact scalar or partial invariance; MV12 addresses the third level by separating label measurement from multimodal prediction. MV15 was predeclared with `10` conditioning rows and `7` identity probes, then executed as an aggregate-only identity audit. MV15 latent-conditioned identity run: status blocked because theta-conditioned feature identity remains high; raw feature identity BA 1.000; theta-conditioned feature identity BA 1.000; total/predicted-total/B3-conditioned feature identity BA 1.000/1.000/1.000; theta-only identity BA 0.576; predicted-theta output identity BA 0.646; B3 Pareto dominates predicted theta output=True; full method is not allowed. The key interpretation is that low-dimensional output identity and feature-level invariance are different: theta-only BA is `0.576` and predicted-theta output identity BA is `0.646`, but residualized BGE feature identity remains `1.000` after theta conditioning and `1.000`/`1.000`/`1.000` after total, predicted-total, and B3 controls. MV16 then closes the planned localized-DIF calibration follow-up as `blocked_no_dif_guided_small_k_gain`: anchor safety passes (`True`), but the both-direction small-k DIF-guided gate is `False`, the best supported row is `D1_edaic_source_cmdc_target`/`M16d_global_plus_C02_C06` at k=`10`, and L4 small-k output identity BA remains `0.984`.

The first measurement sequence is negative or bounded. MV08 improves over the total-score floor on `0/3` pooled active slices, while MV08b improves over both total-score and fixed-map floors on `2/3` slices but raises prediction dataset identity to `0.979`. MV09 then revises the gate semantics: post-head identity is diagnostic when outputs are scale-specific, while shared-latent claims require conditional identity checks. Under that sharper test, E-DAIC/CMDC item-conditioned feature identity remains `0.991`, so direct fixed shared-symptom mappings remain too strong under the current frozen-feature and shallow-head contract.

The psychometric sequence supplies the paper's sharper target story. MV10 shows that E-DAIC PHQ-8 and CMDC PHQ-9 exhibit substantial common PHQ structure: the configural screen passes, loading congruence is `0.998`, and `7/8` items pass the approximate metric-loading screen. Exact threshold/scalar equivalence is not uniformly supported, with only `4/8` candidate anchors (`C01`, `C04`, `C05`, `C07`). MV11 formal graded-response IRT confirmation preserves those four anchors, flags no strong loading DIF, and flags threshold DIF for `C02` and `C06`, while AIC favors the partial model and BIC favors the scalar model. MV13 external R mirt replication preserves the same qualitative anchor/DIF pattern, with no loading-DIF flags and threshold-DIF flags on `C02` and `C06`, but retains a configural convergence warning. MV14 then makes that warning explicit: the convergence-safe full ladder has `120/200` effective draws after `185` fit-success draws, configural converges in `120/200`, and the stable metric/partial/scalar ladder has `197` effective draws with AIC/BIC favoring `partial_mv10`/`scalar`. MV19 then adds the observed-N stress test: H0 C02/C06 both-flag false rate is `0.208`, H1 C02/C06 both-flag recovery is `0.662`, H1 top-two recovery is `0.222`, and H1 anchor subset recovery is `0.178`. MV14 bootstrap uncertainty: status complete convergence-aware item-level measurement-shift evidence; requested smoke/core/DIF R 10/200/100; convergence-safe full-ladder effective R 120/200 after fit-success R 185; configural converged R 120/200; stable-ladder effective R 197; DIF effective R 77/100; stable anchors C01;C04;C05;C07; top threshold-DIF items C02;C06; best AIC/BIC models configural/scalar; stable-ladder AIC/BIC partial_mv10/scalar. MV19 finite-sample PHQ simulation: status complete finite-sample simulation with downgraded C02/C06 wording; H0 C02/C06 both-flag false rate 0.208; H0 C02/C06 top-two false-localization 0.034; H1 C02/C06 both-flag recovery 0.662; H1 C02/C06 top-two recovery 0.222; H1 anchor subset recovery 0.178; pass_rule_met=False. The conservative manuscript claim is therefore substantial structural similarity with repeated but finite-sample-bounded localized C02/C06 threshold-shift evidence, not a robust standalone DIF conclusion, a bootstrap-confirmed global partial-invariance win, a full scalar-invariance proof, or a full-method pass.

MV12 then tests whether multimodal features can predict the label-derived latent target, and the result should not be flattened into a simple failure. Within datasets, `X -> theta` is learnable: M12a improves theta MAE over the train-mean theta floor by `-0.078` on E-DAIC and `-0.146` on CMDC. The predicted latent target is also far less dataset-identifiable than the upstream conditional feature space, with conditional identity BA `0.602` versus the MV09 reference `0.991`. However, this is a low-dimensional-output result rather than a theta-specific invariance result: B3 direct itemwise Ridge compressed to theta has lower pooled observed macro MAE (`0.692` versus `0.701`) and lower conditional identity BA (`0.579` versus `0.602`) than M12a.

The cost is predictive fidelity and zero-shot source-calibrated latent-scale transfer. Same-dataset observed macro item MAE is worse than direct itemwise Ridge by `0.004` on E-DAIC and `0.067` on CMDC, showing that a one-dimensional latent bottleneck loses item-profile information. Cross-dataset evaluation splits the story even more sharply: the latent route improves observed macro item MAE relative to direct item transfer by `-0.260` for CMDC-to-E-DAIC and `-0.210` for E-DAIC-to-CMDC, yet theta MAE remains worse than the target train-mean theta floor by `0.037` and `0.077`. Because the external theta target is scored with the source measurement function on target subjects, this failure mixes `X -> theta` predictor transfer with target measurement-function mismatch. The interpretation is therefore a predictive fidelity-dataset identifiability trade-off: the latent/scalar prediction layer is less dataset-identifiable than upstream BGE features, but the current M12a head is Pareto-dominated by the dimension-matched B3 severity baseline and does not establish psychometric theta as uniquely more invariant. The aggregate tradeoff analysis freezes the current latent-target line as paper-critical diagnostic evidence.

MV16 tests the most direct positive hypothesis suggested by the MV14 single-fit/bootstrap pattern before the MV19 finite-sample downgrade: if threshold non-equivalence is concentrated on C02/C06 while C01/C04/C05/C07 act as candidate anchors, a small target-labeled calibration set might repair cross-dataset measurement mapping. The result is bounded and asymmetric rather than a method pass. The L4 global-plus-C02/C06 row reaches a best small-k theta-MAE delta of `-0.227` versus L0, but the predeclared both-direction small-k gate fails and output identity remains high. This keeps MV16 useful as a falsifying calibration stress test: localized measurement-shift diagnosis alone is not enough to overcome the current BGE cross-dataset prediction and output-identity limits.

The remaining Phase 5 findings define bounded supporting claims. PDCH supports an internal HAMD diagnostic bridge: item-derived total MAE is `5.693`, direct total MAE is `5.794`, and macro item MAE is `0.727`, but this does not support cross-dataset HAMD transfer. MODMA supports task-control evidence because task projection reduces feature task-identity BA from `0.762` to `0.570` while preserving the main task signal (`0.688`). EATD remains a negative SDS stress test because uncontrolled primary MAE is `28.810` versus a train-mean floor of `7.201`. MV06 has 143 completed and 143 double-annotated candidates. Evidence-presence kappa: ALL 0.965 (95% CI 0.922-1.000; 143 pairs), CMDC 0.967 (95% CI 0.885-1.000; 59 pairs), PDCH 1.000 (95% CI 1.000-1.000; 60 pairs), E-DAIC 0.846 (95% CI 0.595-1.000; 24 pairs). 1 sampled candidate remains incomplete in the local workbook. Field-specific degenerate marginal statuses should be read from agreement_summary.csv. Together, these results support a paper about measurement validity, protocol dependence, and bounded evidence localization, while keeping external HAMD transfer, EATD SDS generalization, positive MPDD context conditioning, and full-method construction blocked.

## Discussion

The central result is not a new state-of-the-art depression detector. It is a measurement audit showing that common cross-dataset shortcuts survive simple feature and head changes, and that label measurement itself is a major source of non-equivalence. The PHQ result should be read as E-DAIC/CMDC dataset-group threshold non-equivalence among shared items, not as a clean PHQ-8-versus-PHQ-9 scale-specific claim; MV19 further requires finite-sample caution for C02/C06 and the anchor map at the observed N. The negative MV08/MV08b sequence, the MV12 fidelity-identity trade-off, the MV15 latent-conditioned feature-identity result, and the MV16 calibration failure all point in the same direction: psychometric harmonization is not representation invariance, and representation alignment is not measurement validity.

Measurement screens and residual measurement heads are diagnostic under current features; MV10/MV11/MV13/MV14/MV19/MV12 shift RQ1 to measurement-target validity, while MV15 and MV16 freeze the current BGE latent identity/calibration line as bounded or negative evidence.

Treat the old Chinese-BGE feature-level evidence as legacy/diagnostic; MV17a has regenerated E-DAIC/CMDC/PDCH features with BGE-M3 and multilingual-E5 and reproduces the blocked MV07/MV12/MV15 pattern. Label-only MV10/MV11/MV13/MV14/MV19 psychometric evidence is unaffected.

The convergence-safe bootstrap supports item-level wording, but MV19 shows the observed-N decision screen is finite-sample sensitive; report C02/C06 as repeated localized threshold-shift evidence with downgrade, not as a robust standalone DIF conclusion.

The observed-N simulation closes the small-sample uncertainty layer by showing adequate both-target H1 flagging but high false/localization sensitivity, low top-two recovery, and poor exact anchor-set recovery; C02/C06 wording must be finite-sample-bounded.

MV16 completes the predeclared localized DIF calibration test but does not pass the both-direction small-k mechanism gate; report it as bounded or negative calibration evidence, not as a full method.

MV06 can support first-round aggregate credibility; stronger RQ4 claims still need the remaining incomplete local candidate resolved and sampling limits discussed.

### Limitations

The draft remains bounded by the current manifest and artifact policy. E-DAIC speaker-resolved participant/interviewer controls are blocked by missing speaker labels in the available transcript CSVs. MV17a mitigates the old BGE language-contract caveat for the paper-critical MV07/MV12/MV15 chain, but it reproduces the blocked feature-level pattern rather than authorizing a shared-representation claim. The E-DAIC/CMDC PHQ evidence cannot separate language, country, protocol, clinical setting, sample severity, translation, and PHQ-8/PHQ-9 form effects; report it as dataset-group measurement shift. MV19 shows that the current observed-N PHQ decision screen is finite-sample sensitive, so C02/C06 should not be written as robust standalone DIF. MV18 adds exploratory same-HAMD CMDC/PDCH context-shift evidence, but CMDC HAMD supervision is too small for formal invariance or a complete bridge claim. EATD and MPDD are total-only for current item-level construct purposes. The MV06 evidence-localization set has one incomplete CMDC candidate and a wide E-DAIC agreement interval because the completed E-DAIC double-annotation set has 24 pairs. MV14 bootstrap uncertainty is convergence-aware but still uses the currently predeclared R=200/R=100 tiers.

### Future Work

Future positive method work should introduce a genuinely new predeclared mechanism rather than another shallow head variant. The immediate route is now narrow: consolidate the manuscript with MV19-downgraded PHQ wording, then design a criterion-contamination stress test over mirror-like versus non-mirror interview turns only if the manuscript still needs that support. MV17a, MV18, and MV19 are complete. Stop lines remain explicit: no extra BGE shallow heads, projection dimensions, DIF-guided calibration variants, personality-gating models, or EATD valence-adversarial modules unless a new design contract changes the gate.

## Claim Traceability

The full traceability matrix is stored in `manuscript_traceability_matrix.csv`. The table below shows the claim-boundary rows.

| section | claim | status | guardrail | source artifacts |
| --- | --- | --- | --- | --- |
| Claim boundary | C_FULL_METHOD_START | blocked | Do not use as a positive claim; report as negative or blocked evidence. | 37 |
| Measurement evidence | C_RQ1_SHARED_SYMPTOM | blocked | Do not use as a positive claim; report as negative or blocked evidence. | 33 |
| Psychometric baseline | C_PSYCHOMETRIC_INVARIANCE_BASELINE | allowed_limited | Allowed only with the scoped wording in this table. | 12 |
| HAMD diagnostic evidence | C_PDCH_HAMD_INTERNAL | allowed_limited | Allowed only with the scoped wording in this table. | 4 |
| External stress tests | C_EATD_SDS_GENERALIZATION | blocked | Do not use as a positive claim; report as negative or blocked evidence. | 3 |
| Identity and protocol diagnostics | C_DATASET_IDENTITY_CONTROL | allowed_limited | Allowed only with the scoped wording in this table. | 8 |
| Identity and protocol diagnostics | C_MODMA_TASK_CONTROL | allowed_limited | Allowed only with the scoped wording in this table. | 2 |
| External stress tests | C_EATD_VALENCE_ADVERSARIAL | blocked | Do not use as a positive claim; report as negative or blocked evidence. | 3 |
| Population/context diagnostics | C_RQ3_CONTEXT_CONDITIONING | blocked | Do not use as a positive claim; report as negative or blocked evidence. | 2 |
| Evidence localization | C_RQ4_EVIDENCE_LOCALIZATION | allowed_limited | Allowed only with the scoped wording in this table. | 6 |
| Paper framing | C_PUBLISHABLE_PAPER_DIRECTION | allowed_with_reframing | Allowed as paper framing, not as a full-method success claim. | 13 |

## Open Editing Items

| id | priority | area | item | blocking |
| --- | --- | --- | --- | --- |
| M002 | high | bibliography | Verify every bibliography row against DOI/publisher/ACL/arXiv metadata, then insert generated citation keys from references.bib into prose and adapt formatting to the target venue. | True |
| M003 | high | claim_boundary | Keep full M0/M1/M2/M3 method claims blocked unless a genuinely new predeclared mechanism changes the full-method gate. | True |
| M006 | medium | criterion_contamination | Design a criterion-contamination stress test that separates mirror-like interview/question turns from non-mirror turns before adding any new protocol-bias method. | False |
| M007 | medium | RQ4 | Resolve the one incomplete local CMDC MV06 candidate if annotator rows become available; otherwise keep RQ4 as first-round aggregate credibility evidence. | False |
| M008 | medium | limitations | Decide whether to run a larger corrected MV14 bootstrap only if interval precision becomes reviewer-critical. | False |
| M009 | medium | protocol | Speaker-resolved E-DAIC interviewer/participant controls remain optional unless the Results need a literal speaker-role claim. | False |
| M010 | medium | MPDD | Recover structured MPDD gender/health metadata only if population stress-test claims become central; do not revive personality-aware modeling as a main contribution. | False |

## Source Context

These source hints are mapped to citation keys for manuscript drafting; final submission should use the target venue's citation format.

| citation key | source | URL | use |
| --- | --- | --- | --- |
| baai2026bgem3 | BAAI BGE-M3 model card | https://huggingface.co/BAAI/bge-m3 | BGE-M3 is the primary multilingual replacement encoder used in MV17a feature-contract sensitivity over E-DAIC, CMDC, and PDCH. |
| baai2026bgesmallzh | BAAI bge-small-zh-v1.5 model card | https://huggingface.co/BAAI/bge-small-zh-v1.5 | The E-DAIC MV07 feature generator used a Chinese BGE model on English transcripts, so the old BGE-linked MV07-MV16 feature-level evidence is legacy/diagnostic; MV17a multilingual sensitivity reruns the paper-critical MV07/MV12/MV15 chain and reproduces the blocked pattern. |
| bulut2017detecting | Bulut and Suh 2017, Frontiers in Education | https://www.frontiersin.org/journals/education/articles/10.3389/feduc.2017.00051/full | IRT likelihood-ratio DIF testing supports MV11 item-level loading and threshold DIF diagnostics. |
| cai2020modma | MODMA dataset description | https://reshare.ukdataservice.ac.uk/854301/ | Supports MODMA as an interview/reading/picture-description task robustness dataset. |
| chalmers2012mirt | Chalmers 2012, Journal of Statistical Software | https://www.jstatsoft.org/article/view/v048i06 | mirt supplies the external multidimensional IRT implementation used in MV13 to replicate the PHQ anchor/DIF and measurement-shift pattern. |
| chalmers2026mirtmultiplegroup | mirt multipleGroup documentation | https://philchalmers.github.io/mirt/html/multipleGroup.html | The multipleGroup interface documents the multi-group invariance and DIF workflow used for the MV13 external replication. |
| chen2025scd | Chen et al. 2025, arXiv | https://arxiv.org/abs/2512.06447 | SCD-MLLM occupies the generic multi-dataset robust multimodal-model space; our paper should not compete on fusion architecture but on target comparability assumptions. |
| deduro2026nlppsychometrics | De Duro et al. 2026, arXiv | https://arxiv.org/abs/2608.07316 | NLP Psychometrics shows the broader framing is emerging; our differentiator is real clinical corpora, scale-item DIF, and multimodal transfer consequences. |
| delamain2024measurement | Delamain et al. 2024, Journal of Affective Disorders | https://pubmed.ncbi.nlm.nih.gov/37989437/ | PHQ-9 measurement invariance and DIF are active clinical-measurement questions, supporting our decision to frame RQ1 as measurement validity rather than only model architecture. |
| fu2025mpddchallenge | Fu et al. 2025, ACM MM Challenge | https://hacilab.github.io/MPDDChallenge.github.io/ | The MPDD challenge explicitly foregrounds age, health, living condition, and personality context, supporting our RQ3 treatment of population heterogeneity. |
| fu2025mpddchallenge | MPDD Challenge official page | https://hacilab.github.io/MPDDChallenge.github.io/ | Supports MPDD as the age/personality/health/gait context dataset. |
| fu2026p3hf | Fu et al. 2026, AAAI | https://ojs.aaai.org/index.php/AAAI/article/view/37159 | P3HF shows strong personality-aware modeling on MPDD-Young, so our paper should not claim generic personality-aware fusion as the novelty. |
| galenkamp2017measurement | Galenkamp et al. 2017, BMC Psychiatry | https://pmc.ncbi.nlm.nih.gov/articles/PMC5655879/ | PHQ-9 measurement invariance methods provide the template for the next label-only psychometric baseline before another multimodal head iteration. |
| gratch2014distress | Gratch et al. 2014, LREC | https://aclanthology.org/L14-1421/ | DAIC contains clinical interviews with audio, video, questionnaire, transcription, and verbal/nonverbal annotation, supporting our governance-first treatment of interview corpora. |
| ishikawa2026multiprobe | Ishikawa and Duke 2026, arXiv | https://arxiv.org/abs/2605.23977 | A recent multi-probe depression benchmark audit overlaps Phase 3-style benchmark validity claims, so our novelty must emphasize target measurement validity rather than another generic benchmark audit. |
| li2025mirror | Li et al. 2025, arXiv | https://arxiv.org/abs/2508.05830 | Mirror/non-mirror criterion contamination provides a direct motivation for a future protocol-label-overlap stress test over interview questions and PHQ/HAMD item semantics. |
| ma2021phqhamd | Ma et al. 2021, Frontiers in Psychiatry | https://www.frontiersin.org/journals/psychiatry/articles/10.3389/fpsyt.2021.747139/full | PHQ-9 and HAMD-17 can correlate strongly while differing in item discrimination and severity assessment, supporting scale/linking caution without overstating E-DAIC/CMDC PHQ evidence as scale-specific. |
| mandal2025questmf | Mandal et al. 2025, CLPsych | https://aclanthology.org/2025.clpsych-1.4/ | QuestMF already targets E-DAIC question-wise modality fusion and item-level PHQ interpretability; our novelty is cross-dataset measurement semantics, not item-level E-DAIC prediction alone. |
| nguyen2022improving | Nguyen et al. 2022, ACL | https://aclanthology.org/2022.acl-long.578/ | Questionnaire-grounded symptom modeling is prior positive evidence for symptom-aware OOD detection; our paper's tension is that symptom grounding is not sufficient when the target measurement function changes by dataset/group. |
| patel2019measurement | Patel et al. 2019, Depression and Anxiety | https://pmc.ncbi.nlm.nih.gov/articles/PMC6736700/ | PHQ-9 measurement-invariance work shows why group and dataset comparisons require psychometric checks before interpreting score or model differences. |
| pdchrepository2026 | PDCH dataset page | https://github.com/Miraclemarvel55/PDCH | PDCH provides real consultation audio/text paired with professional HAMD-17 assessments, matching our bounded PDCH-only HAMD diagnostic claim. |
| pdchrepository2026 | PDCH repository and dataset paper | https://github.com/Miraclemarvel55/PDCH | Supports PDCH as a bounded HAMD-17 consultation validation dataset. |
| samejima1969graded | Samejima 1969, Psychometrika Monograph 17 | https://www.psychometricsociety.org/sites/main/files/file-attachments/mn17.pdf | The graded-response model provides the ordinal IRT family used by MV11/MV13 to separate label measurement from multimodal prediction. |
| shen2022automatic | EATD-Corpus repository | https://github.com/Fancy-Block/EATD-Corpus | Supports EATD as Chinese audio/text depression data with emotion-related tasks. |
| uscict2026daic | USC ICT DAIC-WOZ and Extended DAIC download page | https://dcapswoz.ict.usc.edu/ | Official access terms motivate keeping real row-level manifests, paths, and private review material out of the public repository. |
| wang2024multilinguale5 | Multilingual-E5-base model card | https://huggingface.co/intfloat/multilingual-e5-base | Multilingual-E5-base is the second encoder sensitivity so the rerun does not hinge on a single multilingual embedding family. |
| zhang2025interviewer | Zhang and Poellabauer 2025, Findings of EMNLP | https://aclanthology.org/2025.findings-emnlp.650/ | Recent interviewer-bias work motivates treating question type and dialogue protocol as nuisance factors; our paper uses this as a measurement-validity risk rather than as a standalone adversarial-method novelty. |
| zhang2025red | Zhang et al. 2025, Findings of ACL | https://aclanthology.org/2025.findings-acl.517/ | RED already uses retrieved transcript evidence for explainable depression detection, so MV06 should be framed as measurement-validity credibility support rather than a new evidence-retrieval method. |
| zhou2026depression | Zhou et al. 2026, Journal of Clinical Epidemiology | https://www.jclinepi.com/article/S0895-4356(26)00082-X/abstract | A 2026 equipercentile-linking study reports significant correlations but systematic differences among depression scales, aligning with our negative shared-space evidence. |
| zou2023cmdc | Zou et al. 2023, IEEE Transactions on Affective Computing | https://doi.org/10.1109/TAFFC.2022.3181210 | Supports CMDC as Chinese clinical-interview validation with PHQ-9 and HAMD labels. |

## Artifact Boundary

- This draft is generated from aggregate artifacts only.
- It does not read or export raw datasets, real row-level manifests, row predictions, embeddings, fitted parameters, private review workbooks, source locators, local notes, or clinical text.
- Source experiment artifacts remain authoritative for numeric claims.
