# MV17 Post-Review Measurement-Validity Route

Generated: `2026-08-21T18:43:15+00:00`

## Decision

- Current paper direction: target measurement validity, not a generic multimodal method.
- MV17a multilingual sensitivity is complete and reproduces the blocked MV07/MV12/MV15 feature-level pattern.
- MV18 same-HAMD exploratory control is complete and supports cautious dataset/context-shift wording, not formal HAMD invariance.
- Label-only PHQ psychometric results remain the core positive evidence and are unaffected by the BGE feature-contract caveat.

## Legacy BGE Contract Risks

| risk | status | chain | evidence | boundary |
| --- | --- | --- | --- | --- |
| BGE_R001 | mitigated_for_mv17a | MV07->MV12->MV15->MV16 | E-DAIC MV07 generator defaults to BAAI/bge-small-zh-v1.5, which is documented as Chinese; E-DAIC transcripts are English. | Old Chinese-BGE outputs remain legacy/diagnostic; MV17a now provides multilingual BGE-M3 and multilingual-E5 reruns for MV07/MV12/MV15. |
| BGE_R002 | open | E-DAIC text features | Current E-DAIC transcript contract exposes Text rows but no speaker role in the available CSV header, so participant/interviewer filtering is unavailable. | Do not interpret high BGE identity or poor transfer as pure participant symptom-representation failure. |

## Prioritized Experiment Queue

| priority | experiment | status | minimum scope | success readout | stop rule |
| --- | --- | --- | --- | --- | --- |
| 1 | MV17a_multilingual_feature_contract | complete | Regenerated E-DAIC, CMDC, and PDCH subject features with BGE-M3 and multilingual-E5; reran MV07, MV12, and MV15 only. | Both encoders reproduce the blocked MV07/MV12/MV15 pattern; see p5_mv17a_multilingual_feature_contract outputs. | Do not rerun MV16 unless a new explicit need is identified after MV17a review. |
| 2 | MV18_cmdc_pdch_hamd_same_scale_control | complete | Completed exploratory CMDC-HAMD versus PDCH-HAMD same-language/same-scale item distribution, total-excluding-item residual shifts, bootstrap threshold differences, and bidirectional frozen-feature transfer. | The mild/moderate HAMD overlap shows 4 severity-conditioned residual item-shift flags, 7 threshold-shift flags, and weak primary bidirectional transfer. | Do not overclaim formal HAMD invariance because CMDC HAMD item supervision is only a small sanity subset. |
| 3 | MV19_phq_finite_sample_psychometric_simulation | ready_to_design | Simulate observed N, category frequencies, severity distribution, thresholds, and missingness under scalar-invariant H0 and C02/C06 threshold-DIF H1; run the MV10-MV14 decision pipeline. | Report false-DIF rate under H0, C02/C06 recovery under H1, and anchor-set recovery. | If false-DIF is high, downgrade C02/C06 from robust evidence to hypothesis-generating evidence. |
| 4 | MV20_criterion_contamination_stress | recommended_to_design | Compute semantic similarity between interviewer/question text and PHQ/HAMD items, define mirror-like versus non-mirror turns, and test deletion/insertion effects. | Estimate whether label-overlapping elicitation language inflates apparent depression prediction or evidence localization. | Do not build a new protocol-bias network unless this stress test exposes a mechanism that a simple deletion/control cannot explain. |

## Stop Lines

| id | area | decision |
| --- | --- | --- |
| S001 | BGE variants | Stop extra shallow BGE heads, projection dimensions, or total-anchor variants unless the feature contract changes first. |
| S002 | MV16 calibration | MV17a is complete; keep MV16 paused unless a new explicit need is identified. |
| S003 | RQ3 personality | Do not design personality gating/calibrators as a main method contribution; keep MPDD as a population stress test. |
| S004 | EATD valence | Do not add an EATD valence-adversarial method from current negative SDS evidence. |
| S005 | Evidence localization | Do not build an evidence network; use MV06 agreement as credibility support unless deletion/sufficiency tests are explicitly predeclared. |

## Source Verification Summary

| source | URL | verified fact | use |
| --- | --- | --- | --- |
| bge_small_zh_model_card | https://huggingface.co/BAAI/bge-small-zh-v1.5 | Model card and FlagEmbedding table list bge-small-zh-v1.5 as Chinese. | Supports legacy BGE feature-contract caveat. |
| bge_m3_model_card | https://huggingface.co/BAAI/bge-m3 | Model card describes BGE-M3 as multilingual, supporting more than 100 working languages. | Primary MV17a replacement encoder. |
| multilingual_e5_model_card | https://huggingface.co/intfloat/multilingual-e5-base | Model card lists multilingual-E5-base as multilingual and documents 768-dimensional embeddings. | Second MV17a encoder sensitivity. |
| multi_probe_audit_2026 | https://arxiv.org/abs/2605.23977 | Title and authors are A Multi-Probe Audit of Clinical-Interview Depression Detection Benchmarks by Takehiro Ishikawa and Jon Duke. | Motivates demoting Phase 3 to supporting benchmark-validity evidence. |
| interviewer_bias_emnlp_2025 | https://aclanthology.org/2025.findings-emnlp.650/ | Title, authors, pages, and DOI verified from ACL Anthology. | Supports protocol/question-type nuisance framing. |
| p3hf_aaai_2026 | https://ojs.aaai.org/index.php/AAAI/article/view/37159 | P3HF AAAI title, authors, DOI, and MPDD-Young improvement claim verified from the AAAI page. | Motivates demoting personality-aware modeling from a core contribution. |

## Regeneration

```bash
python scripts/phase5_plan_mv17_postreview_measurement_validity_route.py --overwrite
```
