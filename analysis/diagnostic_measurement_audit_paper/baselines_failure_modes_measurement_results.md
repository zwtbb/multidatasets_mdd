# Baselines, Failure-Mode Diagnostics, and Measurement Results

Generated: `2026-08-11T16:36:12+00:00`

## Scope

This manuscript scaffold turns existing aggregate experiment artifacts into draft Results text. It is not a new model run. It excludes row-level predictions, local review workbooks, learned parameters, embeddings, and private clinical text.

## Draft Section: Baselines

The baseline phase defines the reproducibility floor for later diagnostic claims. The matrix contained `67` planned runs, of which `66` completed and `1` was conditionally excluded; no applicable run remains blocked. The final audit contains `313` completed metric rows and `5` not-applicable metric rows, with five seeds used for completed runs and `1000` bootstrap resamples recorded by the metric audit. The Phase 2 completion verdict is complete, and the method-design gate recommendation is `ready`.

These baselines should be read as governance evidence rather than as the paper's main novelty. The matrix covers simple unimodal and fusion families across six datasets, while intentionally excluding incompatible public reproductions from the canonical matrix when their split, feature, or evaluation contract differs. The hygiene audit passed and reviewed `39` canonical prediction files locally, but generated Phase 2 result artifacts remain local by default. The manuscript should therefore cite Phase 2 as a completed, subject-level baseline floor and avoid using it as a public artifact dump.

## Draft Section: Failure-Mode Diagnostics

Phase 3 shows why direct pooled training is not enough evidence for a shared depression representation. Across `7` dataset/protocol identity probes, dataset identity is highly recoverable from frozen feature spaces: six-way WavLM identity reaches balanced accuracy `0.990`, CMDC/PDCH BGE text reaches `1.000`, and E-DAIC/CMDC OpenFace reaches `1.000`. These probes do not prove every identity signal is harmful, but they establish that dataset identity must be reported, controlled, or conditioned before interpreting pooled performance as construct transfer.

Protocol controls sharpen the same conclusion at the interview-content level. The E-DAIC/CMDC protocol-control run completed `60` runs over `5` seeds with artifact hygiene passing. In E-DAIC, front-position dialogue text improves binary Macro-F1 by `0.109` versus full dialogue, and repeated-turn-only text improves it by `0.181`. In CMDC, Q10-only binary Macro-F1 drops by `-0.374` versus all questions. The right paper wording is therefore question-position and fixed-protocol dependence; literal participant-only or interviewer-only claims remain blocked because speaker-resolved fields are unavailable.

Task and valence diagnostics separate supported protocol stress from unsupported valence mechanisms. MODMA cross-task evaluation lowers balanced accuracy by `0.099` overall, with the affective-task evaluation drop reaching `0.142` and a 95 percent interval from `0.003` to `0.280`. EATD does not show the hypothesized healthy-negative shortcut in the current audio diagnostic: healthy negative predicted-depressed rate is `0.118` versus `0.206` for healthy nonnegative material. MODMA can support bounded task-control evidence; EATD should remain a negative stress test rather than a valence-adversarial method driver.

MPDD supports a population-heterogeneity audit but not a positive context-conditioning method. On `175` labeled train subjects, personality-only text beats shuffled personality by Macro-F1 `0.116` and QWK `0.272`, yet audio-video-personality fusion adds only Macro-F1 `0.001` and QWK `0.001` over audio-video alone. Subgroup calibration remains material, with age ECE gap `0.132` and personality-bin ECE gap `0.289`. Gait has modest psychomotor-context association with PHQ-9, top absolute Spearman `0.269`, while gender and health analyses remain `blocked` because structured fields are missing.

## Draft Section: Measurement Results

The Phase 5 full-method gate now reads `34` aggregate evidence summaries and remains blocked, while allowing a measurement-shift and measurement-invariance paper direction. This is the central Results boundary: the evidence is rich enough to explain why cross-dataset depression transfer is hard, but not for starting or claiming the full M0/M1/M2/M3 symptom-aligned method.

The measurement story is best read at three levels: feature/domain shift (`P(X|D)`), target-measurement shift (`P(Y|theta,D)`), and latent prediction stability (`P(theta_hat|X,D)`). MV09 addresses the first level by showing that dataset identity remains high after legitimate conditioning; MV10/MV11/MV13 address the second level by showing partial rather than scalar PHQ invariance with external replication; MV12 addresses the third level by separating label measurement from multimodal prediction.

The first measurement sequence is negative or bounded. MV08 improves over the total-score floor on `0/3` pooled active slices, while MV08b improves over both total-score and fixed-map floors on `2/3` slices but raises prediction dataset identity to `0.979`. MV09 then revises the gate semantics: post-head identity is diagnostic when outputs are scale-specific, while shared-latent claims require conditional identity checks. Under that sharper test, E-DAIC/CMDC item-conditioned feature identity remains `0.991`, so direct fixed shared-symptom mappings remain too strong under the current frozen-feature and shallow-head contract.

The psychometric sequence supplies the paper's sharper target story. MV10 shows that E-DAIC PHQ-8 and CMDC PHQ-9 share a strong one-factor/metric structure: the configural screen passes, loading congruence is `0.998`, and `7/8` items pass the approximate metric-loading screen. Threshold/scalar equivalence is weaker, with only `4/8` candidate anchors (`C01`, `C04`, `C05`, `C07`). MV11 formal graded-response IRT confirmation preserves those four anchors, flags no strong loading DIF, and flags threshold DIF for `C02` and `C06`, while AIC favors the partial model and BIC favors the scalar model. MV13 external R mirt replication preserves the same qualitative anchor/DIF pattern, with no loading-DIF flags and threshold-DIF flags on `C02` and `C06`, but retains a configural convergence warning. The conservative manuscript claim is therefore strong structural similarity with partial, uncertain threshold equivalence, not a full scalar-invariance proof.

MV12 then tests whether multimodal features can predict the label-derived latent target, and the result should not be flattened into a simple failure. Within datasets, `X -> theta` is learnable: M12a improves theta MAE over the train-mean theta floor by `-0.078` on E-DAIC and `-0.146` on CMDC. The predicted latent target is also far less dataset-identifiable than the upstream conditional feature space, with conditional identity BA `0.602` versus the MV09 reference `0.991`.

The cost is predictive fidelity and latent-scale transfer. Same-dataset observed macro item MAE is worse than direct itemwise Ridge by `0.004` on E-DAIC and `0.067` on CMDC, showing that a one-dimensional latent bottleneck loses item-profile information. Cross-dataset evaluation splits the story even more sharply: the latent route improves observed macro item MAE relative to direct item transfer by `-0.260` for CMDC-to-E-DAIC and `-0.210` for E-DAIC-to-CMDC, yet theta MAE remains worse than the target train-mean theta floor by `0.037` and `0.077`. The interpretation is therefore a predictive fidelity-dataset identifiability trade-off: psychometric latent compression removes substantial dataset information and can help observed-scale transfer, but it does not yet calibrate a fully transferable latent severity scale. The aggregate tradeoff analysis freezes the current latent-target line as paper-critical diagnostic evidence.

The remaining Phase 5 findings define bounded supporting claims. PDCH supports an internal HAMD diagnostic bridge: item-derived total MAE is `5.693`, direct total MAE is `5.794`, and macro item MAE is `0.727`, but this does not support cross-dataset HAMD transfer. MODMA supports task-control evidence because task projection reduces feature task-identity BA from `0.762` to `0.570` while preserving the main task signal (`0.688`). EATD remains a negative SDS stress test because uncontrolled primary MAE is `28.810` versus a train-mean floor of `7.201`. MV06 supplies first-round aggregate evidence-localization credibility: `30` candidates are completed and `20` are double annotated, with evidence-presence kappa `0.808` overall, `0.643` for CMDC, `1.000` for PDCH, and underpowered/undefined for E-DAIC. Together, these results support a paper about measurement validity, protocol dependence, and bounded evidence localization, while keeping external HAMD transfer, EATD SDS generalization, positive MPDD context conditioning, and full-method construction blocked.

## Manuscript Guardrails

- Do not present Phase 2 baseline result artifacts as public release material; use aggregate completion and hygiene only.
- Do not claim that high unconditional dataset identity is automatically harmful; use it as a shortcut-risk screen and reserve conditional identity for shared-latent claims.
- Do not call scale-specific post-head identity a hard shared-latent failure unless the output space is explicitly shared.
- Do not use MV12 as positive full-method evidence; its tradeoff analysis freezes the current latent-target line.
- Do not strengthen RQ4 beyond first-round aggregate credibility unless E-DAIC double annotation is expanded or uncertainty analysis is added.

## Source Map

| section | source artifact | source path | use |
| --- | --- | --- | --- |
| Baselines | phase2_completion_audit | analysis/phase2_baselines/phase2_completion_audit/phase2_completion_audit.json | baseline matrix completion, metrics, seeds, and method-design gate |
| Baselines | phase2_artifact_hygiene | analysis/phase2_baselines/phase2_artifact_hygiene_audit/phase2_artifact_hygiene_audit.json | baseline hygiene and local-only prediction audit status |
| Failure-Mode Diagnostics | phase3_dataset_identity | analysis/phase3_diagnostics/dataset_identity_probe/probe_metric_summary.csv | dataset/protocol identity probe balanced accuracy summaries |
| Failure-Mode Diagnostics | phase3_protocol_controls | analysis/phase3_diagnostics/protocol_controls/protocol_control_metric_deltas.csv | E-DAIC position/repeated-turn and CMDC question-position controls |
| Failure-Mode Diagnostics | phase3_task_valence | analysis/phase3_diagnostics/task_valence/modma_task_transfer_drop_summary.csv | MODMA cross-task degradation and EATD valence stress interpretation |
| Failure-Mode Diagnostics | phase3_mpdd_individual_differences | analysis/phase3_diagnostics/mpdd_individual_differences/phase3_run_summary.json | MPDD personality, age, gait, and missing metadata diagnostics |
| Measurement Results | paper_claim_boundary | analysis/diagnostic_measurement_audit_paper/paper_claim_boundary.csv | allowed and blocked paper claim language |
| Measurement Results | key_numeric_findings | analysis/diagnostic_measurement_audit_paper/key_numeric_findings.csv | paper-facing MV08-MV13, PDCH, MODMA, EATD, and MV06 findings |
| Measurement Results | mv13_external_psychometric_replication | analysis/phase5_minimal_validation/p5_mv13_external_psychometric_replication/run_summary.json | MV13 external R mirt replication status and convergence caveat |
| Measurement Results | mv12_tradeoff_analysis | analysis/phase5_minimal_validation/p5_mv12_latent_target_tradeoff_analysis/run_summary.json | MV12 freeze decision, failure modes, and gate decomposition |

## Claim Checklist

| claim scope | status | evidence | guardrail |
| --- | --- | --- | --- |
| Baseline reproducibility floor | supported | Phase 2 completed 66/67 runs with 313 completed metric rows and zero blocked runs. | Do not publish Phase 2 generated result artifacts by default; cite aggregate completion only. |
| Dataset/protocol shortcut risk | supported_diagnostic | Dataset identity probes include WavLM six-way BA 0.990, CMDC/PDCH BGE BA 1.000, and E-DAIC/CMDC OpenFace BA 1.000. | Treat identity as shortcut-risk evidence; use conditional identity for shared-latent claims. |
| Protocol/task failure modes | supported_diagnostic | CMDC Q10-only binary Macro-F1 delta is -0.374; MODMA affective-task BA drop is 0.142. | Speaker-resolved E-DAIC/CMDC controls remain blocked by missing fields. |
| Population/context method gain | blocked_positive_claim | MPDD AVP adds only Macro-F1 0.001 and QWK 0.001 over AV, while subgroup calibration gaps remain large. | Use age/personality as heterogeneity axes, not as a positive context-conditioning method claim. |
| Measurement-shift paper direction | allowed_with_reframing | Full gate reads 34 Phase 5 summaries; the full method remains blocked, but the measurement-shift paper direction is allowed. | Report negative and bounded results honestly; no full M0/M1/M2/M3 claim. |
| MV12 latent-target method | blocked_positive_method_claim | MV12 improves same-dataset theta utility and conditional identity, but observed-scale safety and external theta transfer fail; aggregate analysis freezes the current line. | Future method work needs a genuinely new predeclared mechanism. |
