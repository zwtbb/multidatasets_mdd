# MV17 Post-Review Measurement-Validity Route

Generated: `2026-08-21T16:15:30+00:00`

## Decision

- Current paper direction: target measurement validity, not a generic multimodal method.
- Current BGE-linked feature-level chain is legacy/diagnostic until multilingual sensitivity is complete.
- Label-only PHQ psychometric results remain the core positive evidence and are unaffected by the BGE feature-contract caveat.

## Legacy BGE Contract Risks

| risk | status | chain | evidence | boundary |
| --- | --- | --- | --- | --- |
| BGE_R001 | open | MV07->MV12->MV15->MV16 | E-DAIC MV07 generator defaults to BAAI/bge-small-zh-v1.5, which is documented as Chinese; E-DAIC transcripts are English. | Treat current BGE-linked feature-level findings as legacy/diagnostic until multilingual sensitivity is rerun. |
| BGE_R002 | open | E-DAIC text features | Current E-DAIC transcript contract exposes Text rows but no speaker role in the available CSV header, so participant/interviewer filtering is unavailable. | Do not interpret high BGE identity or poor transfer as pure participant symptom-representation failure. |

## Prioritized Experiment Queue

| priority | experiment | status | minimum scope | success readout | stop rule |
| --- | --- | --- | --- | --- | --- |
| 1 | MV17a_multilingual_feature_contract | ready_to_design | Regenerate E-DAIC, CMDC, and PDCH subject features with BGE-M3 and multilingual-E5; rerun MV07, MV12, and MV15 only. | Both encoders reproduce or qualify the B3 direct-severity dominance, external-transfer failure, and latent-conditioned identity pattern. | Do not rerun MV16 or add new shallow heads before MV17a evidence is reviewed. |
| 2 | MV18_cmdc_pdch_hamd_same_scale_control | ready_to_design | Exploratory CMDC-HAMD versus PDCH-HAMD same-language/same-scale item distribution, severity-conditioned ordinal regression, bootstrap threshold differences, or partial-pooling DIF. | A cautious estimate of whether same-language, same-scale HAMD item behavior still varies by dataset/context. | Do not overclaim formal HAMD invariance because CMDC HAMD item supervision is only a small sanity subset. |
| 3 | MV19_phq_finite_sample_psychometric_simulation | ready_to_design | Simulate observed N, category frequencies, severity distribution, thresholds, and missingness under scalar-invariant H0 and C02/C06 threshold-DIF H1; run the MV10-MV14 decision pipeline. | Report false-DIF rate under H0, C02/C06 recovery under H1, and anchor-set recovery. | If false-DIF is high, downgrade C02/C06 from robust evidence to hypothesis-generating evidence. |
| 4 | MV20_criterion_contamination_stress | recommended_to_design | Compute semantic similarity between interviewer/question text and PHQ/HAMD items, define mirror-like versus non-mirror turns, and test deletion/insertion effects. | Estimate whether label-overlapping elicitation language inflates apparent depression prediction or evidence localization. | Do not build a new protocol-bias network unless this stress test exposes a mechanism that a simple deletion/control cannot explain. |

## Stop Lines

| id | area | decision |
| --- | --- | --- |
| S001 | BGE variants | Stop extra shallow BGE heads, projection dimensions, or total-anchor variants unless the feature contract changes first. |
| S002 | MV16 calibration | Do not rerun or tune MV16 until MV17a multilingual features are reviewed. |
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
