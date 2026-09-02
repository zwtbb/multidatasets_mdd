#!/usr/bin/env python3
"""Build paper-facing claim and evidence tables for the diagnostic audit paper.

This is a writing-prep script, not an experiment runner. It reads existing
aggregate Phase 5 gates and summaries, then emits compact claim boundaries,
key numeric findings, and literature-positioning notes for the diagnostic
measurement-audit paper. It does not read raw data, row-level outputs, local
review workbooks, or private source locators.
"""

from __future__ import annotations

import argparse
import json
import math
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
PHASE5_DIR = ROOT / "analysis" / "phase5_minimal_validation"
DEFAULT_OUT_DIR = ROOT / "analysis" / "diagnostic_measurement_audit_paper"

CLAIM_GATE = PHASE5_DIR / "full_method_gate_audit" / "claim_gate.csv"
FULL_GATE_SUMMARY = PHASE5_DIR / "full_method_gate_audit" / "run_summary.json"
MV02_SUMMARY = PHASE5_DIR / "p5_mv02_hamd_auxiliary_bridge" / "run_summary.json"
MV04C_SUMMARY = PHASE5_DIR / "p5_mv04c_protocol_task_valence_control" / "run_summary.json"
MV06_SUMMARY = PHASE5_DIR / "p5_mv06_evidence_annotation_summary" / "run_summary.json"
MV06_AGREEMENT = PHASE5_DIR / "p5_mv06_evidence_annotation_summary" / "agreement_summary.csv"
MV06_UNCERTAINTY = PHASE5_DIR / "p5_mv06_evidence_annotation_summary" / "agreement_uncertainty_summary.csv"
MV08_SUMMARY = PHASE5_DIR / "p5_mv08_partial_invariance_measurement" / "run_summary.json"
MV08B_SUMMARY = PHASE5_DIR / "p5_mv08b_total_anchored_residual_measurement" / "run_summary.json"
MV09_SUMMARY = PHASE5_DIR / "p5_mv09_conditional_identity_audit" / "run_summary.json"
MV10_SUMMARY = PHASE5_DIR / "p5_mv10_psychometric_invariance_baseline" / "run_summary.json"
MV11_SUMMARY = PHASE5_DIR / "p5_mv11_formal_psychometric_confirmation" / "run_summary.json"
MV12_DESIGN_SUMMARY = PHASE5_DIR / "p5_mv12_two_stage_latent_target_design" / "run_summary.json"
MV12_RUN_SUMMARY = PHASE5_DIR / "p5_mv12_two_stage_latent_target" / "run_summary.json"
MV12_ANALYSIS_SUMMARY = PHASE5_DIR / "p5_mv12_latent_target_tradeoff_analysis" / "run_summary.json"
MV13_SUMMARY = PHASE5_DIR / "p5_mv13_external_psychometric_replication" / "run_summary.json"
MV14_SUMMARY = PHASE5_DIR / "p5_mv14_measurement_uncertainty_bootstrap" / "run_summary.json"
MV19_SUMMARY = PHASE5_DIR / "p5_mv19_phq_finite_sample_psychometric_simulation" / "run_summary.json"
MV20_SUMMARY = PHASE5_DIR / "p5_mv20_criterion_overlap_stress" / "run_summary.json"
MIRT_PARAM_AUDIT_SUMMARY = PHASE5_DIR / "p5_mirt_parameterization_correctness_audit" / "run_summary.json"
MV15_DESIGN_SUMMARY = PHASE5_DIR / "p5_mv15_latent_conditioned_identity_design" / "run_summary.json"
MV15_RUN_SUMMARY = PHASE5_DIR / "p5_mv15_latent_conditioned_identity" / "run_summary.json"
MV16_RUN_SUMMARY = PHASE5_DIR / "p5_mv16_dif_guided_calibration" / "run_summary.json"
MV17A_DIR = PHASE5_DIR / "p5_mv17a_multilingual_feature_contract"
MV17A_SUMMARY = MV17A_DIR / "run_summary.json"
MV17A_DOWNSTREAM = MV17A_DIR / "downstream"
MV21_DIR = PHASE5_DIR / "p5_mv21_measurement_discrepancy_gradient"
MV21_SUMMARY = MV21_DIR / "run_summary.json"
MV21_PHQ_DELTAS = MV21_DIR / "phq_shared_conditioned_deltas.csv"
MV21_HAMD_DELTAS = MV21_DIR / "hamd_conditioned_deltas.csv"
MV21_HAMD_CORR_DELTAS = MV21_DIR / "hamd_item_correlation_delta_summary.csv"
MV21_DAIC_PAIRED = MV21_DIR / "daicwoz_edaic_paired_item_differences.csv"
MV21_DAIC_DELTAS = MV21_DIR / "daicwoz_edaic_conditioned_deltas.csv"
MV22_DIR = PHASE5_DIR / "p5_mv22_foundation_backbone_validation"
MV22_SUMMARY = MV22_DIR / "run_summary.json"
MV22_DOWNSTREAM_METRICS = MV22_DIR / "downstream_metric_extract.csv"
MV22_MODEL_COMPARISON = MV22_DIR / "model_comparison_summary.csv"
MV22_AUDIO_SUMMARY = MV22_DIR / "audio_foundation_proxy_summary.csv"
MV23_DIR = PHASE5_DIR / "p5_mv23_foundation_multimodal_completion"
MV23_SUMMARY = MV23_DIR / "run_summary.json"
MV23_HEAD_COMPARISON = MV23_DIR / "head_comparison_summary.csv"
MV23_MEASUREMENT_PROXY = MV23_DIR / "measurement_proxy_summary.csv"
MV23_COVERAGE = MV23_DIR / "cache_coverage_summary.csv"

TRACKED_FILES = [
    "artifact_hygiene_audit.json",
    "key_numeric_findings.csv",
    "literature_positioning.csv",
    "paper_claim_boundary.csv",
    "paper_claim_boundary.md",
    "report.md",
    "run_summary.json",
]

CLAIM_SECTION = {
    "C_FULL_METHOD_START": "Claim boundary",
    "C_RQ1_SHARED_SYMPTOM": "Measurement evidence",
    "C_PSYCHOMETRIC_INVARIANCE_BASELINE": "Psychometric baseline",
    "C_PDCH_HAMD_INTERNAL": "HAMD diagnostic evidence",
    "C_EATD_SDS_GENERALIZATION": "External stress tests",
    "C_DATASET_IDENTITY_CONTROL": "Identity and protocol diagnostics",
    "C_PROTOCOL_CRITERION_OVERLAP": "Identity and protocol diagnostics",
    "C_MODMA_TASK_CONTROL": "Identity and protocol diagnostics",
    "C_EATD_VALENCE_ADVERSARIAL": "External stress tests",
    "C_RQ3_CONTEXT_CONDITIONING": "Population/context diagnostics",
    "C_RQ4_EVIDENCE_LOCALIZATION": "Evidence localization",
    "C_PUBLISHABLE_PAPER_DIRECTION": "Paper framing",
}

PAPER_CLAIM_LANGUAGE = {
    "C_FULL_METHOD_START": "Do not claim the full M0/M1/M2/M3 method; the evidence currently supports a governed measurement-shift diagnostic paper, with MV15 and MV16 completed as bounded/negative follow-ups.",
    "C_RQ1_SHARED_SYMPTOM": "Report direct shared-symptom mapping as negative under the old BGE contract and the completed MV17a multilingual sensitivity; make BGE-M3 the primary feature contract, multilingual-E5 the sensitivity, and reframe RQ1 around target measurement validity because feature shift, measurement shift, and prediction shift are distinct.",
    "C_PSYCHOMETRIC_INVARIANCE_BASELINE": "Use MV10/MV11/MV19 plus MV21 PHQ shared-item descriptive/severity-conditioned results as the primary E-DAIC/CMDC PHQ common-structure and dataset-group measurement-shift evidence. Use corrected MV13/MV14 as anchor-linked external mirt qualitative and uncertainty corroboration, while retaining the configural convergence warning and MV19 observed-N caveat.",
    "C_PDCH_HAMD_INTERNAL": "Use PDCH HAMD-17 as bounded internal diagnostic evidence and MV21 CMDC/PDCH HAMD as exploratory same-scale context-shift support, not as formal HAMD invariance or cross-dataset HAMD transfer.",
    "C_EATD_SDS_GENERALIZATION": "Report EATD SDS as a negative or weak external stress result.",
    "C_DATASET_IDENTITY_CONTROL": "Report unconditional dataset identity as a shortcut-risk screen and use MV15's latent-conditioned identity result as shared-latent diagnostic evidence.",
    "C_PROTOCOL_CRITERION_OVERLAP": "Report MV20 as a bounded negative CMDC-only criterion-overlap stress test: high-overlap question-position deletion is not clearly worse than matched random deletion under the primary BGE-M3 PHQ-9 top-20 gate.",
    "C_MODMA_TASK_CONTROL": "Use MODMA task nuisance projection as bounded protocol-control evidence.",
    "C_EATD_VALENCE_ADVERSARIAL": "Do not add or claim an EATD-driven valence-adversarial module from current evidence.",
    "C_RQ3_CONTEXT_CONDITIONING": "Report MPDD age/personality/gait only as population and individual-difference stress tests; do not claim a personality-aware modeling contribution or keep iterating personality gating/calibration.",
    "C_RQ4_EVIDENCE_LOCALIZATION": "Use MV06 as first-round aggregate credibility evidence for measurement interpretation only; agreement does not prove the model used the evidence.",
    "C_PUBLISHABLE_PAPER_DIRECTION": "Proceed as a target-measurement-validity paper organized around three layers: representation/protocol shift in X, target measurement shift in Y given theta and dataset/group, and prediction shift from X to theta. Treat Phase 3 as motivating evidence, MV10/MV11/MV19/MV21 as the primary PHQ measurement layer, corrected MV13/MV14 as anchor-linked mirt corroboration with convergence and finite-sample caveats, BGE-M3 MV17a as the primary feature-contract consequence layer, multilingual-E5 as encoder sensitivity, MV22/MV23 as foundation-backbone and lightweight multimodal stress tests, and MV12/MV15/MV16/MV18/MV20/MV21 HAMD/DAIC controls as bounded or legacy support.",
}

LITERATURE_ROWS = [
    {
        "source_id": "daic_lrec_2014",
        "topic": "Dataset governance and clinical-interview context",
        "citation_hint": "Gratch et al. 2014, LREC",
        "url": "https://aclanthology.org/L14-1421/",
        "paper_positioning": "DAIC contains clinical interviews with audio, video, questionnaire, transcription, and verbal/nonverbal annotation, supporting our governance-first treatment of interview corpora.",
    },
    {
        "source_id": "daic_official_access",
        "topic": "Dataset access and public release boundaries",
        "citation_hint": "USC ICT DAIC-WOZ and Extended DAIC download page",
        "url": "https://dcapswoz.ict.usc.edu/",
        "paper_positioning": "Official access terms motivate keeping real row-level manifests, paths, and private review material out of the public repository.",
    },
    {
        "source_id": "interviewer_bias_emnlp_2025",
        "topic": "Protocol/interviewer bias",
        "citation_hint": "Zhang and Poellabauer 2025, Findings of EMNLP",
        "url": "https://aclanthology.org/2025.findings-emnlp.650/",
        "paper_positioning": "Recent interviewer-bias work motivates treating question type and dialogue protocol as nuisance factors; our paper uses this as a measurement-validity risk rather than as a standalone adversarial-method novelty.",
    },
    {
        "source_id": "burdisso2024daicprompts",
        "topic": "DAIC prompt validity and protocol leakage",
        "citation_hint": "Burdisso et al. 2024, ClinicalNLP",
        "url": "https://aclanthology.org/2024.clinicalnlp-1.8/",
        "paper_positioning": "DAIC prompt-validity work motivates treating therapist/interviewer prompts as protocol-side signals rather than participant symptom evidence.",
    },
    {
        "source_id": "multi_probe_audit_2026",
        "topic": "Nearby benchmark audit risk",
        "citation_hint": "Ishikawa and Duke 2026, arXiv",
        "url": "https://arxiv.org/abs/2605.23977",
        "paper_positioning": "A recent multi-probe depression benchmark audit overlaps Phase 3-style benchmark validity claims, so our novelty must emphasize target measurement validity rather than another generic benchmark audit.",
    },
    {
        "source_id": "questionnaire_grounding_acl_2022",
        "topic": "Questionnaire grounding and OOD depression detection",
        "citation_hint": "Nguyen et al. 2022, ACL",
        "url": "https://aclanthology.org/2022.acl-long.578/",
        "paper_positioning": "Questionnaire-grounded symptom modeling is prior positive evidence for symptom-aware OOD detection; our paper's tension is that symptom grounding is not sufficient when the target measurement function changes by dataset/group.",
    },
    {
        "source_id": "phq_hamd_irt_2021",
        "topic": "PHQ/HAMD measurement differences",
        "citation_hint": "Ma et al. 2021, Frontiers in Psychiatry",
        "url": "https://www.frontiersin.org/journals/psychiatry/articles/10.3389/fpsyt.2021.747139/full",
        "paper_positioning": "PHQ-9 and HAMD-17 can correlate strongly while differing in item discrimination and severity assessment, supporting scale/linking caution without overstating E-DAIC/CMDC PHQ evidence as scale-specific.",
    },
    {
        "source_id": "phq9_invariance_helius_2017",
        "topic": "Classical measurement invariance",
        "citation_hint": "Galenkamp et al. 2017, BMC Psychiatry",
        "url": "https://pmc.ncbi.nlm.nih.gov/articles/PMC5655879/",
        "paper_positioning": "PHQ-9 measurement invariance methods provide the template for the next label-only psychometric baseline before another multimodal head iteration.",
    },
    {
        "source_id": "phq9_measurement_invariance_us_2019",
        "topic": "PHQ-9 sociodemographic invariance",
        "citation_hint": "Patel et al. 2019, Depression and Anxiety",
        "url": "https://pmc.ncbi.nlm.nih.gov/articles/PMC6736700/",
        "paper_positioning": "PHQ-9 measurement-invariance work shows why group and dataset comparisons require psychometric checks before interpreting score or model differences.",
    },
    {
        "source_id": "samejima_graded_response_1969",
        "topic": "Ordinal IRT measurement model",
        "citation_hint": "Samejima 1969, Psychometrika Monograph 17",
        "url": "https://www.psychometricsociety.org/sites/main/files/file-attachments/mn17.pdf",
        "paper_positioning": "The graded-response model provides the ordinal IRT family used by MV11/MV13 to separate label measurement from multimodal prediction.",
    },
    {
        "source_id": "mirt_jss_2012",
        "topic": "External psychometric replication runtime",
        "citation_hint": "Chalmers 2012, Journal of Statistical Software",
        "url": "https://www.jstatsoft.org/article/view/v048i06",
        "paper_positioning": "mirt supplies the external multidimensional IRT implementation used in MV13 to replicate the PHQ anchor/DIF and measurement-shift pattern.",
    },
    {
        "source_id": "mirt_multiplegroup_docs",
        "topic": "Multi-group IRT implementation",
        "citation_hint": "mirt multipleGroup documentation",
        "url": "https://philchalmers.github.io/mirt/html/multipleGroup.html",
        "paper_positioning": "The multipleGroup interface documents the multi-group invariance and DIF workflow used for the MV13 external replication.",
    },
    {
        "source_id": "meredith1993measurement",
        "topic": "Measurement invariance foundation",
        "citation_hint": "Meredith 1993, Psychometrika",
        "url": "https://link.springer.com/article/10.1007/BF02294825",
        "paper_positioning": "Classical measurement-invariance theory grounds the paper's separation between latent constructs and observed scale responses.",
    },
    {
        "source_id": "vandenberg2000review",
        "topic": "Measurement invariance review",
        "citation_hint": "Vandenberg and Lance 2000, Organizational Research Methods",
        "url": "https://journals.sagepub.com/doi/10.1177/109442810031002",
        "paper_positioning": "The measurement-invariance review supports the paper's target-contract and comparability-check framing.",
    },
    {
        "source_id": "muthen2014irt",
        "topic": "Approximate measurement alignment",
        "citation_hint": "Muthen and Asparouhov 2014, Frontiers in Psychology",
        "url": "https://www.frontiersin.org/journals/psychology/articles/10.3389/fpsyg.2014.00978/full",
        "paper_positioning": "IRT alignment motivates approximate rather than all-or-nothing treatment of imperfect cross-group measurement comparability.",
    },
    {
        "source_id": "irt_lr_dif_frontiers_2017",
        "topic": "IRT likelihood-ratio DIF testing",
        "citation_hint": "Bulut and Suh 2017, Frontiers in Education",
        "url": "https://www.frontiersin.org/journals/education/articles/10.3389/feduc.2017.00051/full",
        "paper_positioning": "IRT likelihood-ratio DIF testing supports MV11 item-level loading and threshold DIF diagnostics.",
    },
    {
        "source_id": "phq_dif_jad_2024",
        "topic": "Measurement invariance and DIF",
        "citation_hint": "Delamain et al. 2024, Journal of Affective Disorders",
        "url": "https://pubmed.ncbi.nlm.nih.gov/37989437/",
        "paper_positioning": "PHQ-9 measurement invariance and DIF are active clinical-measurement questions, supporting our decision to frame RQ1 as measurement validity rather than only model architecture.",
    },
    {
        "source_id": "scale_linking_jclinepi_2026",
        "topic": "Cross-scale linking",
        "citation_hint": "Zhou et al. 2026, Journal of Clinical Epidemiology",
        "url": "https://www.jclinepi.com/article/S0895-4356(26)00082-X/abstract",
        "paper_positioning": "A 2026 equipercentile-linking study reports significant correlations but systematic differences among depression scales, aligning with our negative shared-space evidence.",
    },
    {
        "source_id": "mpdd_challenge_2025",
        "topic": "Individual differences and MPDD",
        "citation_hint": "Fu et al. 2025, ACM MM Challenge",
        "url": "https://hacilab.github.io/MPDDChallenge.github.io/",
        "paper_positioning": "The MPDD challenge explicitly foregrounds age, health, living condition, and personality context, supporting our RQ3 treatment of population heterogeneity.",
    },
    {
        "source_id": "p3hf_aaai_2026",
        "topic": "Personality-aware multimodal methods",
        "citation_hint": "Fu et al. 2026, AAAI",
        "url": "https://ojs.aaai.org/index.php/AAAI/article/view/37159",
        "paper_positioning": "P3HF shows strong personality-aware modeling on MPDD-Young, so our paper should not claim generic personality-aware fusion as the novelty.",
    },
    {
        "source_id": "questmf_clpsych_2025",
        "topic": "E-DAIC item-level multimodal PHQ prediction",
        "citation_hint": "Mandal et al. 2025, CLPsych",
        "url": "https://aclanthology.org/2025.clpsych-1.4/",
        "paper_positioning": "QuestMF already targets E-DAIC question-wise modality fusion and item-level PHQ interpretability; our novelty is cross-dataset measurement semantics, not item-level E-DAIC prediction alone.",
    },
    {
        "source_id": "red_acl_2025",
        "topic": "Evidence retrieval for clinical-interview depression detection",
        "citation_hint": "Zhang et al. 2025, Findings of ACL",
        "url": "https://aclanthology.org/2025.findings-acl.517/",
        "paper_positioning": "RED already uses retrieved transcript evidence for explainable depression detection, so MV06 should be framed as measurement-validity credibility support rather than a new evidence-retrieval method.",
    },
    {
        "source_id": "mirror_criterion_contamination_2025",
        "topic": "Criterion contamination in language-based depression prediction",
        "citation_hint": "Li et al. 2025, arXiv",
        "url": "https://arxiv.org/abs/2508.05830",
        "paper_positioning": "Mirror/non-mirror criterion contamination motivates MV20, our bounded CMDC-only protocol-label-overlap stress test over question-position embeddings and PHQ item semantics.",
    },
    {
        "source_id": "scd_mllm_2025",
        "topic": "Generic cross-domain multimodal robustness",
        "citation_hint": "Chen et al. 2026, Pattern Recognition",
        "url": "https://doi.org/10.1016/j.patcog.2026.113367",
        "paper_positioning": "SCD-MLLM occupies the generic multi-dataset robust multimodal-model space; our paper should not compete on fusion architecture but on target comparability assumptions.",
    },
    {
        "source_id": "teng2026depressionllm",
        "topic": "Foundation-model depression detection",
        "citation_hint": "Teng et al. 2026, Displays",
        "url": "https://doi.org/10.1016/j.displa.2025.103304",
        "paper_positioning": "DepressionLLM motivates treating multimodal foundation depression systems as strong representation-side baselines rather than solutions to target measurement validity.",
    },
    {
        "source_id": "nlp_psychometrics_2026",
        "topic": "Emerging NLP psychometrics framing",
        "citation_hint": "De Duro et al. 2026, arXiv",
        "url": "https://arxiv.org/abs/2608.07316",
        "paper_positioning": "NLP Psychometrics shows the broader framing is emerging; our differentiator is real clinical corpora, scale-item DIF, and multimodal transfer consequences.",
    },
    {
        "source_id": "bge_small_zh_model_card",
        "topic": "Legacy BGE feature-contract caveat",
        "citation_hint": "BAAI bge-small-zh-v1.5 model card",
        "url": "https://huggingface.co/BAAI/bge-small-zh-v1.5",
        "paper_positioning": "The E-DAIC MV07 feature generator used a Chinese BGE model on English transcripts, so the old BGE-linked MV07-MV16 feature-level evidence is legacy/diagnostic; MV17a multilingual sensitivity reruns the paper-critical MV07/MV12/MV15 chain and reproduces the blocked pattern.",
    },
    {
        "source_id": "bge_m3_model_card",
        "topic": "Multilingual BGE replacement contract",
        "citation_hint": "BAAI BGE-M3 model card",
        "url": "https://huggingface.co/BAAI/bge-m3",
        "paper_positioning": "BGE-M3 is the primary multilingual replacement encoder used in MV17a feature-contract sensitivity over E-DAIC, CMDC, and PDCH.",
    },
    {
        "source_id": "multilingual_e5_model_card",
        "topic": "Second multilingual encoder sensitivity",
        "citation_hint": "Multilingual-E5-base model card",
        "url": "https://huggingface.co/intfloat/multilingual-e5-base",
        "paper_positioning": "Multilingual-E5-base is the second encoder sensitivity so the rerun does not hinge on a single multilingual embedding family.",
    },
    {
        "source_id": "qwen3_embedding_text_foundation_2025",
        "topic": "Text foundation embedding",
        "citation_hint": "Zhang et al. 2025, arXiv",
        "url": "https://arxiv.org/abs/2506.05176",
        "paper_positioning": "Qwen3-Embedding supports the executed MV22 strong text-backbone slice; the current paper does not claim instruction-tuned LLM fine-tuning.",
    },
    {
        "source_id": "qwen2024qwen25",
        "topic": "Instruction-tuned LLM family",
        "citation_hint": "Qwen Team 2024, official blog",
        "url": "https://qwenlm.github.io/blog/qwen2.5/",
        "paper_positioning": "Qwen2.5 motivates the design-compatible instruction-tuned LLM extension; it is not an executed fine-tuning result in the current paper.",
    },
    {
        "source_id": "wavlm_speech_foundation_2022",
        "topic": "Speech foundation representation",
        "citation_hint": "Chen et al. 2022, arXiv",
        "url": "https://arxiv.org/abs/2110.13900",
        "paper_positioning": "WavLM supports the speech-foundation framing; MV22/MV23 execute cached WavLM base-plus proxy features, while WavLM Large remains future scope.",
    },
    {
        "source_id": "wav2vec2_speech_foundation_2020",
        "topic": "Speech foundation representation",
        "citation_hint": "Baevski et al. 2020, arXiv",
        "url": "https://arxiv.org/abs/2006.11477",
        "paper_positioning": "wav2vec2 supports the speech-foundation sensitivity framing; MV23 executes cached wav2vec2-base proxy features, not wav2vec2-large.",
    },
    {
        "source_id": "hubert_speech_foundation_2021",
        "topic": "Speech foundation representation",
        "citation_hint": "Hsu et al. 2021, arXiv",
        "url": "https://arxiv.org/abs/2106.07447",
        "paper_positioning": "HuBERT motivates a future large speech-backbone sensitivity; HuBERT Large is not executed in the current bounded experiment set.",
    },
    {
        "source_id": "videomae_video_foundation_2022",
        "topic": "Video foundation representation",
        "citation_hint": "Tong et al. 2022, arXiv",
        "url": "https://arxiv.org/abs/2203.12602",
        "paper_positioning": "VideoMAE motivates future video-foundation sensitivity; MV23 uses OpenFace subject statistics as a lightweight video proxy, not VideoMAE.",
    },
    {
        "source_id": "ganin2016domain",
        "topic": "Domain-adversarial baseline",
        "citation_hint": "Ganin et al. 2016, JMLR",
        "url": "https://jmlr.org/papers/v17/15-239.html",
        "paper_positioning": "Domain-adversarial training motivates DANN as a representation-alignment baseline family for MV22/MV23.",
    },
    {
        "source_id": "sun2016deepcoral",
        "topic": "Correlation-alignment baseline",
        "citation_hint": "Sun et al. 2016, AAAI",
        "url": "https://ojs.aaai.org/index.php/AAAI/article/view/10306",
        "paper_positioning": "CORAL motivates covariance-alignment baselines that pressure representation shift without directly modeling target measurement.",
    },
    {
        "source_id": "long2015dan",
        "topic": "MMD distribution-alignment baseline",
        "citation_hint": "Long et al. 2015, ICML",
        "url": "https://proceedings.mlr.press/v37/long15.html",
        "paper_positioning": "Deep Adaptation Networks motivate MMD-style distribution matching as a representation-side adaptation baseline.",
    },
    {
        "source_id": "arjovsky2019irm",
        "topic": "Invariant-risk baseline",
        "citation_hint": "Arjovsky et al. 2019, arXiv",
        "url": "https://arxiv.org/abs/1907.02893",
        "paper_positioning": "IRM motivates invariant-predictor baselines; current PHQ transfer uses severity-environment proxies rather than a full multi-environment IRM claim.",
    },
    {
        "source_id": "sagawa2019groupdro",
        "topic": "Group robustness baseline",
        "citation_hint": "Sagawa et al. 2019, arXiv",
        "url": "https://arxiv.org/abs/1911.08731",
        "paper_positioning": "GroupDRO motivates worst-group robustness baselines; current PHQ transfer uses severity-environment proxies under the bounded setting.",
    },
    {
        "source_id": "guo2017calibration",
        "topic": "Prediction calibration",
        "citation_hint": "Guo et al. 2017, ICML",
        "url": "https://proceedings.mlr.press/v70/guo17a.html",
        "paper_positioning": "Modern neural calibration work supports reporting observed-scale safety and calibration gates alongside raw error.",
    },
    {
        "source_id": "lipton2018labelshift",
        "topic": "Label shift",
        "citation_hint": "Lipton et al. 2018, ICML",
        "url": "https://proceedings.mlr.press/v80/lipton18a.html",
        "paper_positioning": "Label-shift correction motivates separating representation shift from target-distribution and target-measurement assumptions.",
    },
    {
        "source_id": "pdch_dataset",
        "topic": "PDCH HAMD consultation data",
        "citation_hint": "PDCH dataset page",
        "url": "https://github.com/Miraclemarvel55/PDCH",
        "paper_positioning": "PDCH provides real consultation audio/text paired with professional HAMD-17 assessments, matching our bounded PDCH-only HAMD diagnostic claim.",
    },
]


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(path)
    return json.loads(path.read_text(encoding="utf-8"))


def safe_float(value: Any) -> float | None:
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return None
    return numeric if math.isfinite(numeric) else None


def fmt(value: Any, digits: int = 3) -> str:
    numeric = safe_float(value)
    return "NA" if numeric is None else f"{numeric:.{digits}f}"


def require_inputs() -> None:
    for path in [
        CLAIM_GATE,
        FULL_GATE_SUMMARY,
        MV02_SUMMARY,
        MV04C_SUMMARY,
        MV06_SUMMARY,
        MV06_AGREEMENT,
        MV08_SUMMARY,
        MV08B_SUMMARY,
        MV09_SUMMARY,
        MV10_SUMMARY,
        MV11_SUMMARY,
        MV12_DESIGN_SUMMARY,
        MV12_RUN_SUMMARY,
        MV12_ANALYSIS_SUMMARY,
        MV13_SUMMARY,
        MV14_SUMMARY,
        MV19_SUMMARY,
        MV20_SUMMARY,
        MIRT_PARAM_AUDIT_SUMMARY,
        MV15_DESIGN_SUMMARY,
        MV15_RUN_SUMMARY,
        MV16_RUN_SUMMARY,
        MV17A_SUMMARY,
        MV21_SUMMARY,
        MV21_PHQ_DELTAS,
        MV21_HAMD_DELTAS,
        MV21_HAMD_CORR_DELTAS,
        MV21_DAIC_PAIRED,
        MV21_DAIC_DELTAS,
        MV22_SUMMARY,
        MV22_DOWNSTREAM_METRICS,
        MV22_MODEL_COMPARISON,
        MV22_AUDIO_SUMMARY,
        MV23_SUMMARY,
        MV23_HEAD_COMPARISON,
        MV23_MEASUREMENT_PROXY,
        MV23_COVERAGE,
        MV06_UNCERTAINTY,
    ]:
        if not path.exists():
            raise FileNotFoundError(path)


def md_escape(value: Any) -> str:
    text = "" if value is None else str(value)
    return text.replace("|", "\\|").replace("\n", " ")


def paper_text(value: Any) -> str:
    text = "" if value is None else str(value)
    return text.replace("raw snippets", "verbatim excerpts").replace("raw snippet", "verbatim excerpt")


def evidence_presence_kappa(agreement: pd.DataFrame, dataset: str) -> tuple[str, str]:
    rows = agreement[(agreement["dataset"] == dataset) & (agreement["field"] == "evidence_presence")]
    if rows.empty:
        return "NA", "NA"
    row = rows.iloc[0]
    return fmt(row["pairwise_kappa"]), str(int(row["pair_count"]))


def evidence_presence_ci(uncertainty: pd.DataFrame, dataset: str) -> str:
    rows = uncertainty[(uncertainty["dataset"] == dataset) & (uncertainty["field"] == "evidence_presence")]
    if rows.empty:
        return "NA"
    row = rows.iloc[0]
    if pd.isna(row["kappa_ci95_low"]) or pd.isna(row["kappa_ci95_high"]):
        return "NA"
    return f"{fmt(row['kappa_ci95_low'])}-{fmt(row['kappa_ci95_high'])}"


def evidence_presence_phrase(agreement: pd.DataFrame, uncertainty: pd.DataFrame, dataset: str, label: str) -> str:
    kappa, pairs = evidence_presence_kappa(agreement, dataset)
    ci = evidence_presence_ci(uncertainty, dataset)
    if ci == "NA":
        return f"{label} {kappa} ({pairs} pairs)"
    return f"{label} {kappa} (95% CI {ci}; {pairs} pairs)"


def pass_fail(value: Any) -> str:
    return "pass" if bool(value) else "fail"


def yes_no(value: Any) -> str:
    return "yes" if bool(value) else "no"


def load_mv17a_context() -> dict[str, Any]:
    values: dict[str, dict[str, Any]] = {}
    for encoder in ["bge_m3", "multilingual_e5_base"]:
        base = MV17A_DOWNSTREAM / encoder
        mv07 = read_json(base / "mv07_aligned_bge_shared_symptom" / "run_summary.json")["verdict"]
        mv12 = read_json(base / "mv12_two_stage_latent_target" / "run_summary.json")["verdict"]
        mv15 = read_json(base / "mv15_latent_conditioned_identity" / "run_summary.json")["verdict"]
        values[encoder] = {
            "mv07_status": mv07["pass_rule_status"],
            "mv07_feature_identity_ba": mv07["feature_identity_ba"],
            "mv07_prediction_identity_ba": mv07["prediction_identity_ba"],
            "mv12_status": mv12["pass_rule_status"],
            "same_dataset_theta_gate": bool(mv12["same_dataset_theta_gate_passed"]),
            "same_dataset_observed_gate": bool(mv12["same_dataset_observed_gate_passed"]),
            "external_theta_gate": bool(mv12["external_transfer_theta_gate_passed"]),
            "external_observed_gate": bool(mv12["external_transfer_observed_gate_passed"]),
            "conditional_output_identity_ba": mv12["conditional_identity_ba_m12a"],
            "mv15_status": mv15["pass_rule_status"],
            "raw_feature_identity_ba": mv15["raw_feature_identity_ba"],
            "theta_conditioned_feature_identity_ba": mv15["theta_conditioned_feature_identity_ba"],
            "theta_only_identity_ba": mv15["theta_only_identity_ba"],
            "b3_output_identity_ba": mv15["b3_output_identity_ba"],
            "b3_output_observed_macro_mae": mv15["b3_output_observed_macro_mae"],
            "theta_output_identity_ba": mv15["psychometric_predicted_theta_output_identity_ba"],
            "theta_output_observed_macro_mae": mv15["psychometric_predicted_theta_observed_macro_mae"],
            "b3_pareto_dominates": bool(mv15["b3_pareto_dominates_predicted_theta_output"]),
        }
    bge = values["bge_m3"]
    e5 = values["multilingual_e5_base"]
    return {
        "mv17a": values,
        "mv17a_summary": (
            "MV17a multilingual feature-contract sensitivity: BGE-M3 is the primary feature contract "
            "and multilingual-E5 is the sensitivity encoder. Both rerun MV07/MV12/MV15 as blocked. "
            f"BGE-M3 MV12 same-dataset theta/observed/external-theta gates are "
            f"{pass_fail(bge['same_dataset_theta_gate'])}/{pass_fail(bge['same_dataset_observed_gate'])}/"
            f"{pass_fail(bge['external_theta_gate'])}, conditional output identity BA "
            f"{fmt(bge['conditional_output_identity_ba'])}; multilingual-E5 gates are "
            f"{pass_fail(e5['same_dataset_theta_gate'])}/{pass_fail(e5['same_dataset_observed_gate'])}/"
            f"{pass_fail(e5['external_theta_gate'])}, conditional output identity BA "
            f"{fmt(e5['conditional_output_identity_ba'])}. Theta-conditioned feature identity BA is "
            f"{fmt(bge['theta_conditioned_feature_identity_ba'])}/{fmt(e5['theta_conditioned_feature_identity_ba'])}. "
            f"B3 Pareto dominance over predicted theta is {yes_no(bge['b3_pareto_dominates'])} for BGE-M3 "
            f"and {yes_no(e5['b3_pareto_dominates'])} for multilingual-E5, so external theta transfer "
            "and B3 dominance are encoder-dependent."
        ),
    }


def top_abs_delta(
    frame: pd.DataFrame,
    value_col: str = "item_mean_diff_left_minus_right",
    sparse_col: str = "sparse_comparison",
) -> pd.Series:
    data = frame.copy()
    if sparse_col in data.columns:
        data = data[~data[sparse_col].astype(bool)].copy()
    if data.empty:
        raise ValueError("no non-sparse MV21 delta rows")
    data["abs_delta"] = pd.to_numeric(data[value_col], errors="coerce").abs()
    data = data.sort_values("abs_delta", ascending=False, na_position="last")
    return data.iloc[0]


def load_mv21_context() -> dict[str, Any]:
    summary = read_json(MV21_SUMMARY)
    phq = pd.read_csv(MV21_PHQ_DELTAS)
    hamd = pd.read_csv(MV21_HAMD_DELTAS)
    hamd_corr = pd.read_csv(MV21_HAMD_CORR_DELTAS)
    daic_paired = pd.read_csv(MV21_DAIC_PAIRED)
    daic_delta = pd.read_csv(MV21_DAIC_DELTAS)

    phq_top = top_abs_delta(phq)
    hamd_top = top_abs_delta(hamd)
    daic_top = top_abs_delta(daic_delta)
    hamd_corr_top = hamd_corr.dropna(subset=["abs_spearman_delta"]).sort_values(
        "abs_spearman_delta", ascending=False
    ).iloc[0]
    daic_exact_min = float(pd.to_numeric(daic_paired["exact_match_rate"], errors="coerce").min())
    daic_mean_abs_max = float(pd.to_numeric(daic_paired["mean_abs_difference"], errors="coerce").max())

    return {
        "mv21_summary": summary,
        "mv21_sentence": (
            "MV21 descriptive measurement-discrepancy gradient: DAIC-WOZ/E-DAIC same-PHQ-8 lineage control "
            f"uses {summary['daicwoz_train_dev_rows']} train/dev rows with "
            f"{summary['daicwoz_train_dev_item_subjects']} complete item-labeled subjects "
            f"({summary['daicwoz_incomplete_item_rows']} incomplete item row), paired overlap "
            f"{summary['daicwoz_edaic_paired_subjects']}, minimum item exact-match rate "
            f"{fmt(daic_exact_min)}, maximum mean absolute paired item difference {fmt(daic_mean_abs_max)}, "
            f"and maximum non-sparse severity-conditioned DAIC-WOZ minus E-DAIC item-mean delta "
            f"{fmt(abs(float(daic_top['item_mean_diff_left_minus_right'])))}. "
            f"E-DAIC/CMDC PHQ shared-item descriptive analysis uses {summary['phq_edaic_subjects']}/"
            f"{summary['phq_cmdc_subjects']} subjects; the largest non-sparse item-excluded severity-conditioned "
            f"delta is {phq_top['item_id']} {phq_top['item_label_short']} in the {phq_top['condition_bin']} bin "
            f"(E-DAIC minus CMDC mean {fmt(phq_top['item_mean_diff_left_minus_right'])}, "
            f"P>=2 delta {fmt(phq_top['p_ge_2_diff_left_minus_right'])}). "
            f"CMDC/PDCH HAMD same-scale descriptive analysis uses {summary['hamd_cmdc_subjects']}/"
            f"{summary['hamd_pdch_subjects']} subjects; the largest non-sparse item-excluded "
            f"severity-conditioned delta is {hamd_top['item_id']} in {hamd_top['scope']} "
            f"{hamd_top['condition_bin']} (CMDC minus PDCH mean {fmt(hamd_top['item_mean_diff_left_minus_right'])}), "
            f"and the largest descriptive Spearman structure delta is {hamd_corr_top['left_item_id']}-"
            f"{hamd_corr_top['right_item_id']} ({fmt(hamd_corr_top['abs_spearman_delta'])})."
        ),
        "mv21_daic_exact_min": daic_exact_min,
        "mv21_daic_mean_abs_max": daic_mean_abs_max,
        "mv21_daic_max_conditioned_abs_delta": abs(float(daic_top["item_mean_diff_left_minus_right"])),
        "mv21_phq_top_item": str(phq_top["item_id"]),
        "mv21_phq_top_label": str(phq_top["item_label_short"]),
        "mv21_phq_top_bin": str(phq_top["condition_bin"]),
        "mv21_phq_top_mean_delta": float(phq_top["item_mean_diff_left_minus_right"]),
        "mv21_phq_top_p_ge_2_delta": float(phq_top["p_ge_2_diff_left_minus_right"]),
        "mv21_hamd_top_item": str(hamd_top["item_id"]),
        "mv21_hamd_top_scope": str(hamd_top["scope"]),
        "mv21_hamd_top_bin": str(hamd_top["condition_bin"]),
        "mv21_hamd_top_mean_delta": float(hamd_top["item_mean_diff_left_minus_right"]),
        "mv21_hamd_corr_pair": f"{hamd_corr_top['left_item_id']}-{hamd_corr_top['right_item_id']}",
        "mv21_hamd_corr_abs_delta": float(hamd_corr_top["abs_spearman_delta"]),
    }


def load_mv22_context() -> dict[str, Any]:
    summary = read_json(MV22_SUMMARY)
    downstream = pd.read_csv(MV22_DOWNSTREAM_METRICS)
    comparison = pd.read_csv(MV22_MODEL_COMPARISON)
    audio = pd.read_csv(MV22_AUDIO_SUMMARY)

    def metric(encoder: str, experiment: str, name: str) -> float:
        rows = downstream[
            downstream["encoder"].astype(str).eq(encoder)
            & downstream["experiment"].astype(str).eq(experiment)
            & downstream["metric"].astype(str).eq(name)
        ]
        if rows.empty:
            raise ValueError(f"missing MV22 metric {encoder}/{experiment}/{name}")
        return float(rows.iloc[0]["value"])

    def comparison_metric(feature_view: str, transfer_id: str, method: str, column: str) -> float:
        rows = comparison[
            comparison["feature_view"].astype(str).eq(feature_view)
            & comparison["transfer_id"].astype(str).eq(transfer_id)
            & comparison["method"].astype(str).eq(method)
        ]
        if rows.empty:
            raise ValueError(f"missing MV22 comparison {feature_view}/{transfer_id}/{method}/{column}")
        return float(rows.iloc[0][column])

    qwen_feature_identity = metric("qwen3_embedding_0_6b", "mv07", "feature_identity_ba")
    qwen_prediction_identity = metric("qwen3_embedding_0_6b", "mv07", "prediction_identity_ba")
    qwen_conditional_identity = metric("qwen3_embedding_0_6b", "mv12", "conditional_identity_ba_m12a")
    qwen_pooled_theta_mae = metric("qwen3_embedding_0_6b", "mv12", "m12a_pooled_theta_mae")
    qwen_theta_feature_identity = metric("qwen3_embedding_0_6b", "mv15", "theta_conditioned_feature_identity_ba")
    qwen_theta_output_identity = metric("qwen3_embedding_0_6b", "mv15", "psychometric_predicted_theta_output_identity_ba")

    qwen_cmdc_to_edaic_macro = comparison_metric(
        "qwen3_embedding_0_6b_text",
        "cmdc_to_edaic_phq_shared",
        "measurement_aware_mv12_reference",
        "observed_macro_item_mae",
    )
    qwen_cmdc_to_edaic_direct_macro = comparison_metric(
        "qwen3_embedding_0_6b_text",
        "cmdc_to_edaic_phq_shared",
        "mv12_direct_itemwise_reference",
        "observed_macro_item_mae",
    )
    qwen_edaic_to_cmdc_macro = comparison_metric(
        "qwen3_embedding_0_6b_text",
        "edaic_to_cmdc_phq_shared",
        "measurement_aware_mv12_reference",
        "observed_macro_item_mae",
    )
    qwen_edaic_to_cmdc_direct_macro = comparison_metric(
        "qwen3_embedding_0_6b_text",
        "edaic_to_cmdc_phq_shared",
        "mv12_direct_itemwise_reference",
        "observed_macro_item_mae",
    )
    qwen_cmdc_to_edaic_total = comparison_metric(
        "qwen3_embedding_0_6b_text",
        "cmdc_to_edaic_phq_shared",
        "measurement_aware_mv12_reference",
        "observed_total_mae",
    )
    qwen_edaic_to_cmdc_total = comparison_metric(
        "qwen3_embedding_0_6b_text",
        "edaic_to_cmdc_phq_shared",
        "measurement_aware_mv12_reference",
        "observed_total_mae",
    )
    audio_available = audio[audio["status"].astype(str).eq("available_as_audio_foundation_proxy")]
    wavlm_large_status = audio[audio["model_name"].astype(str).eq("microsoft/wavlm-large")]["status"].iloc[0]

    return {
        "mv22_sentence": (
            "MV22 foundation-backbone validation: Qwen3-Embedding-0.6B subject features are complete for "
            f"E-DAIC/CMDC/PDCH, the Qwen MV07/MV12/MV15 chain remains blocked, Qwen feature identity BA "
            f"{fmt(qwen_feature_identity)}, prediction identity BA {fmt(qwen_prediction_identity)}, "
            f"MV12 conditional output identity BA {fmt(qwen_conditional_identity)}, pooled theta MAE "
            f"{fmt(qwen_pooled_theta_mae)}, theta-conditioned feature identity BA "
            f"{fmt(qwen_theta_feature_identity)}, and predicted-theta output identity BA "
            f"{fmt(qwen_theta_output_identity)}. Under the Qwen text contract, the measurement-aware MV12 "
            f"reference improves shared-item macro MAE over the direct itemwise reference in both PHQ transfer "
            f"directions ({fmt(qwen_cmdc_to_edaic_macro)} vs {fmt(qwen_cmdc_to_edaic_direct_macro)} for "
            f"CMDC-to-E-DAIC; {fmt(qwen_edaic_to_cmdc_macro)} vs {fmt(qwen_edaic_to_cmdc_direct_macro)} for "
            f"E-DAIC-to-CMDC) with total MAE {fmt(qwen_cmdc_to_edaic_total)}/{fmt(qwen_edaic_to_cmdc_total)}. "
            f"WavLM base-plus audio proxy caches are available for {len(audio_available)} corpus rows; "
            f"WavLM Large status is {wavlm_large_status}."
        ),
        "qwen_feature_identity_ba": qwen_feature_identity,
        "qwen_prediction_identity_ba": qwen_prediction_identity,
        "qwen_conditional_identity_ba": qwen_conditional_identity,
        "qwen_pooled_theta_mae": qwen_pooled_theta_mae,
        "qwen_theta_feature_identity_ba": qwen_theta_feature_identity,
        "qwen_theta_output_identity_ba": qwen_theta_output_identity,
        "artifact_hygiene_passed": bool(summary["artifact_hygiene_passed"]),
    }


def load_mv23_context() -> dict[str, Any]:
    summary = read_json(MV23_SUMMARY)
    comparison = pd.read_csv(MV23_HEAD_COMPARISON)
    measurement = pd.read_csv(MV23_MEASUREMENT_PROXY)
    coverage = pd.read_csv(MV23_COVERAGE)

    def best_row(transfer_id: str) -> pd.Series:
        rows = comparison[comparison["transfer_id"].astype(str).eq(transfer_id)].copy()
        if rows.empty:
            raise ValueError(f"missing MV23 transfer rows: {transfer_id}")
        return rows.sort_values(["observed_macro_item_mae", "observed_total_mae"]).iloc[0]

    def best_measurement_row(transfer_id: str) -> pd.Series:
        rows = measurement[measurement["transfer_id"].astype(str).eq(transfer_id)].copy()
        if rows.empty:
            raise ValueError(f"missing MV23 measurement rows: {transfer_id}")
        return rows.sort_values(["target_macro_item_mae_mean", "target_total_mae_mean"]).iloc[0]

    cmdc_to_edaic_best = best_row("cmdc_to_edaic_phq_shared")
    edaic_to_cmdc_best = best_row("edaic_to_cmdc_phq_shared")
    cmdc_to_edaic_measurement = best_measurement_row("cmdc_to_edaic_phq_shared")
    edaic_to_cmdc_measurement = best_measurement_row("edaic_to_cmdc_phq_shared")
    multimodal_views = comparison[
        comparison["modality_set"].astype(str).eq("text_audio_video")
    ]["view_id"].nunique()

    return {
        "mv23_sentence": (
            f"MV23 lightweight multimodal completion executes {int(summary['view_count'])} foundation/proxy views "
            f"over E-DAIC/CMDC PHQ shared-item transfer, with {int(summary['adapter_row_count'])} adapter aggregate rows "
            f"and {int(summary['measurement_proxy_row_count'])} measurement-aware proxy rows. Coverage spans "
            f"{coverage['asset_id'].nunique()} reusable local assets and {multimodal_views} text-audio-video fusion views. "
            f"The best CMDC-to-E-DAIC row is {cmdc_to_edaic_best['view_id']}/{cmdc_to_edaic_best['method']} "
            f"with macro MAE {fmt(cmdc_to_edaic_best['observed_macro_item_mae'])}; the best E-DAIC-to-CMDC row is "
            f"{edaic_to_cmdc_best['view_id']}/{edaic_to_cmdc_best['method']} with macro MAE "
            f"{fmt(edaic_to_cmdc_best['observed_macro_item_mae'])}. The best measurement-aware proxy rows are "
            f"{cmdc_to_edaic_measurement['view_id']} macro MAE {fmt(cmdc_to_edaic_measurement['target_macro_item_mae_mean'])} "
            f"and {edaic_to_cmdc_measurement['view_id']} macro MAE {fmt(edaic_to_cmdc_measurement['target_macro_item_mae_mean'])}. "
            "WavLM Large, HuBERT Large, VideoMAE, and end-to-end multimodal fine-tuning remain unclaimed future scope."
        ),
        "view_count": int(summary["view_count"]),
        "adapter_row_count": int(summary["adapter_row_count"]),
        "measurement_proxy_row_count": int(summary["measurement_proxy_row_count"]),
        "best_cmdc_to_edaic_macro_mae": float(cmdc_to_edaic_best["observed_macro_item_mae"]),
        "best_edaic_to_cmdc_macro_mae": float(edaic_to_cmdc_best["observed_macro_item_mae"]),
        "best_cmdc_to_edaic_measurement_macro_mae": float(cmdc_to_edaic_measurement["target_macro_item_mae_mean"]),
        "best_edaic_to_cmdc_measurement_macro_mae": float(edaic_to_cmdc_measurement["target_macro_item_mae_mean"]),
        "artifact_hygiene_passed": bool(summary["artifact_hygiene_passed"]),
    }


def build_metric_context() -> dict[str, str]:
    gate = read_json(FULL_GATE_SUMMARY)
    mv02 = read_json(MV02_SUMMARY)
    mv04c = read_json(MV04C_SUMMARY)
    mv06 = read_json(MV06_SUMMARY)
    agreement = pd.read_csv(MV06_AGREEMENT)
    uncertainty = pd.read_csv(MV06_UNCERTAINTY)
    mv08 = read_json(MV08_SUMMARY)
    mv08b = read_json(MV08B_SUMMARY)
    mv09 = read_json(MV09_SUMMARY)
    mv10 = read_json(MV10_SUMMARY)
    mv11 = read_json(MV11_SUMMARY)
    mv12_design = read_json(MV12_DESIGN_SUMMARY)
    mv12_run = read_json(MV12_RUN_SUMMARY)
    mv12_analysis = read_json(MV12_ANALYSIS_SUMMARY)
    mv13 = read_json(MV13_SUMMARY)
    mv14 = read_json(MV14_SUMMARY)
    mv19 = read_json(MV19_SUMMARY)
    mv20 = read_json(MV20_SUMMARY)
    mirt_audit = read_json(MIRT_PARAM_AUDIT_SUMMARY)
    mv15_design = read_json(MV15_DESIGN_SUMMARY)
    mv15_run = read_json(MV15_RUN_SUMMARY)
    mv16_run = read_json(MV16_RUN_SUMMARY)

    mv02_v = mv02["verdict"]
    modma = next(row for row in mv04c["verdict"]["domain_verdicts"] if row["domain"] == "MODMA")
    eatd = next(row for row in mv04c["verdict"]["domain_verdicts"] if row["domain"] == "EATD")
    mv06_gate = mv06["annotation_gate"]
    mv08_v = mv08["verdict"]
    mv08b_v = mv08b["verdict"]
    mv09_v = mv09["verdict"]
    mv10_v = mv10["verdict"]
    mv11_v = mv11["verdict"]
    mv12_d = mv12_design["decision"]
    mv12_v = mv12_run["verdict"]
    mv12_a = mv12_analysis["decision"]
    mv13_v = mv13["verdict"]
    mv14_v = mv14["verdict"]
    mv14_dif_attempted = mv14_v.get("dif_attempted_draws", mv14_v.get("requested_dif_R"))
    mv19_v = mv19["verdict"]
    mv20_v = mv20["verdict"]
    mirt_decision = mirt_audit["decision"]
    mv15_d = mv15_design["decision"]
    mv15_v = mv15_run["verdict"]
    mv16_v = mv16_run["verdict"]
    mv17a_context = load_mv17a_context()
    mv21_context = load_mv21_context()
    mv22_context = load_mv22_context()
    mv23_context = load_mv23_context()
    mirt_parameterization_corrected = not bool(mirt_decision["statistical_correctness_blocker"])
    mv13_parameterization_note = (
        "The corrected code-level audit verifies E-DAIC as reference, CMDC as focal, explicit "
        "anchor/threshold linking, and freed focal mean/variance for threshold-constrained models; "
        "use with the remaining configural convergence warning."
        if mirt_parameterization_corrected
        else "A later code-level audit shows the actual mirt call fixes CMDC latent mean/variance, "
        "so this is qualitative corroboration rather than final anchor-linked DIF evidence."
    )
    mv14_parameterization_note = (
        "These bootstrap frequencies use the corrected anchor-linked focal mean/variance contract; "
        "interpret them with convergence-safe effective-draw counts and the MV19 observed-N caveat."
        if mirt_parameterization_corrected
        else "A later code-level audit shows these bootstrap frequencies inherit the fixed-hyperparameter "
        "mirt parameterization and should not be used as identification-robust DIF stability."
    )
    all_kappa = evidence_presence_phrase(agreement, uncertainty, "ALL", "ALL")
    cmdc_kappa = evidence_presence_phrase(agreement, uncertainty, "cmdc", "CMDC")
    edaic_kappa = evidence_presence_phrase(agreement, uncertainty, "edaic", "E-DAIC")
    pdch_kappa = evidence_presence_phrase(agreement, uncertainty, "pdch", "PDCH")
    remaining_mv06 = max(
        0,
        int(mv06.get("input_contract", {}).get("candidate_count", 0))
        - int(mv06_gate["completed_candidates"]),
    )
    mv06_remaining_clause = (
        f" {remaining_mv06} sampled candidate remains incomplete in the local workbook."
        if remaining_mv06 == 1
        else f" {remaining_mv06} sampled candidates remain incomplete in the local workbook."
        if remaining_mv06 > 1
        else " All sampled candidates are complete."
    )

    return {
        "gate": (
            f"Full gate reads {gate['evidence_rows']} Phase 5 summaries; "
            f"status {gate['gate_status']}; full_method_allowed={gate['full_method_allowed']}."
        ),
        "rq1": (
            f"MV08 improves over total-score floor on {mv08_v['pooled_m2_improved_vs_total_score_floor_slices']}/"
            f"{mv08_v['pooled_active_slices']} pooled active slices with prediction identity BA "
            f"{fmt(mv08_v['prediction_identity_ba_m2'])}. MV08b improves over both floors on "
            f"{mv08b_v['pooled_m2b_improved_vs_both_floor_slices']}/{mv08b_v['pooled_active_slices']} slices, "
            f"but prediction identity BA {fmt(mv08b_v['prediction_identity_ba_m2b'])} exceeds gate "
            f"{fmt(mv08b_v['current_mv08_m2_prediction_identity_ba_gate'])}. MV09 revises the gate semantics: "
            f"E-DAIC/CMDC item-conditioned feature identity BA remains {fmt(mv09_v['edaic_cmdc_item_residualized_ba'])}. "
            f"MV10 adds a label-only PHQ screen with loading congruence {fmt(mv10_v['loading_congruence'])}, "
            f"{mv10_v['metric_invariant_items']}/8 metric items, {mv10_v['threshold_invariant_items']}/8 "
            f"threshold items, and {mv10_v['anchor_candidate_items']}/8 candidate anchors. "
            f"MV11 confirms {mv11_v['confirmed_mv10_anchor_items']} MV10 anchors with "
            f"{mv11_v['loading_dif_flagged_items']} loading-DIF and {mv11_v['threshold_dif_flagged_items']} "
            f"threshold-DIF flags, but core AIC/BIC split is {mv11_v['core_model_aic_bic_split']}. "
            f"MV13 external mirt replication confirms {mv13_v['confirmed_mv10_anchor_items']} anchors with "
            f"{mv13_v['loading_dif_flagged_items']} loading-DIF and {mv13_v['threshold_dif_flagged_items']} "
            f"threshold-DIF flags, core convergence {mv13_v['core_converged']}, and "
            f"{mv13_v['mv11_mv13_aligned_rows']}/{mv13_v['mv11_mv13_alignment_rows']} MV11-aligned decisions. "
            f"MV14 bootstrap uncertainty is {mv14_v['status']}: core effective R {mv14_v['core_effective_draws']}, "
            f"attempted R {mv14_v['core_selection_attempted_draws']}, fit-success R "
            f"{mv14_v['core_all_fit_success_draws']}, configural converged R "
            f"{mv14_v['configural_converged_draws']}, stable-ladder R "
            f"{mv14_v['stable_ladder_effective_draws']}, DIF effective R "
            f"{mv14_v['dif_min_anchor_effective_draws']}/{mv14_dif_attempted}, stable anchors "
            f"{';'.join(mv14_v['stable_anchor_items'])}, top threshold-DIF items "
            f"{';'.join(mv14_v['top_threshold_dif_items'])}, and best AIC/BIC "
            f"{mv14_v['best_aic_model']}/{mv14_v['best_bic_model']} with stable-ladder "
            f"{mv14_v['stable_ladder_best_aic_model']}/{mv14_v['stable_ladder_best_bic_model']}. "
            f"Post-run mirt parameterization audit is {mirt_decision['audit_status']} with "
            f"statistical_correctness_blocker={mirt_decision['statistical_correctness_blocker']}: "
            f"{mirt_decision['short_read']} "
            f"MV12 design is {mv12_d['readiness_status']}; MV12 run is {mv12_v['pass_rule_status']}, "
            f"with same-dataset theta gate {mv12_v['same_dataset_theta_gate_passed']}, observed-scale safety "
            f"{mv12_v['same_dataset_observed_gate_passed']}, external theta transfer "
            f"{mv12_v['external_transfer_theta_gate_passed']}, and conditional identity BA "
            f"{fmt(mv12_v['conditional_identity_ba_m12a'])}. "
            f"MV12 aggregate tradeoff analysis is {mv12_a['analysis_status']} and recommends freezing "
            f"the current latent-target line; {mv12_a['dimension_matched_identity_caveat']} "
            f"MV15 then blocks latent-conditioned BGE feature-invariance wording: raw feature BA "
            f"{fmt(mv15_v['raw_feature_identity_ba'])}, theta-conditioned feature BA "
            f"{fmt(mv15_v['theta_conditioned_feature_identity_ba'])}, and total/predicted-total/B3-conditioned "
            f"feature BA {fmt(mv15_v['total_conditioned_feature_identity_ba'])}/"
            f"{fmt(mv15_v['predicted_total_conditioned_feature_identity_ba'])}/"
            f"{fmt(mv15_v['b3_itemwise_theta_conditioned_feature_identity_ba'])}. "
            f"MV16 then completes the DIF-guided few-shot calibration ladder with status "
            f"{mv16_v['pass_rule_status']}: subject-overlap gate {mv16_v['subject_overlap_gate_passed']}, "
            f"anchor safety {mv16_v['anchor_safety_gate_passed']}, DIF-guided small-k gate "
            f"{mv16_v['dif_guided_small_k_gate_passed']}, best supported row "
            f"{mv16_v['best_supported_direction']}/{mv16_v['best_supported_model']} at k="
            f"{mv16_v['best_supported_k']}, best L4 small-k delta theta MAE vs L0 "
            f"{fmt(mv16_v['best_l4_small_k_delta_theta_mae_vs_L0'])}, and L4 small-k "
            f"output identity BA {fmt(mv16_v['l4_small_k_output_identity_ba_mean'])}. "
            f"{mv17a_context['mv17a_summary']} {mv22_context['mv22_sentence']} {mv23_context['mv23_sentence']}"
        ),
        "mv09": (
            f"MV09 conditional identity audit: E-DAIC/CMDC raw BA {fmt(mv09_v['edaic_cmdc_raw_ba'])}, "
            f"PHQ-item residualized BA {fmt(mv09_v['edaic_cmdc_item_residualized_ba'])}; "
            f"CMDC/PDCH severity-residualized BA {fmt(mv09_v['cmdc_pdch_severity_residualized_ba'])}; "
            f"three-way severity-residualized BA {fmt(mv09_v['three_way_severity_residualized_ba'])}."
        ),
        "mv10": (
            f"MV10 label-only PHQ screen: configural pass={mv10_v['configural_screen_pass']}; "
            f"loading congruence {fmt(mv10_v['loading_congruence'])}; "
            f"metric invariant items {mv10_v['metric_invariant_items']}/8; "
            f"threshold invariant items {mv10_v['threshold_invariant_items']}/8; "
            f"anchor candidates {mv10_v['anchor_candidate_items']}/8; status {mv10_v['status']}."
        ),
        "mv11": (
            f"MV11 formal graded-response IRT confirmation: status {mv11_v['status']}; "
            f"confirmed MV10 anchors {mv11_v['confirmed_mv10_anchor_items']}; "
            f"loading-DIF flags {mv11_v['loading_dif_flagged_items']}; "
            f"threshold-DIF flags {mv11_v['threshold_dif_flagged_items']}; "
            f"best AIC core model {mv11_v['best_aic_model']}; "
            f"best BIC core model {mv11_v['best_bic_model']}."
        ),
        "mv13": (
            f"MV13 external R mirt replication: status {mv13_v['status']}; "
            f"confirmed MV10 anchors {mv13_v['confirmed_mv10_anchor_items']}; "
            f"loading-DIF flags {mv13_v['loading_dif_flagged_items']}; "
            f"threshold-DIF flags {mv13_v['threshold_dif_flagged_items']}; "
            f"best AIC/BIC core models {mv13_v['best_aic_model']}/{mv13_v['best_bic_model']}; "
            f"core converged={mv13_v['core_converged']}; "
            f"MV11-aligned decisions {mv13_v['mv11_mv13_aligned_rows']}/{mv13_v['mv11_mv13_alignment_rows']}; "
            f"parameter CI status {mv13_v['parameter_ci_status']}; "
            f"parameterization contract {mv13_v.get('parameterization_contract', 'unknown')}. "
            f"{mv13_parameterization_note}"
        ),
        "mv14": (
            f"MV14 bootstrap uncertainty: status {mv14_v['status']}; requested smoke/core/DIF R "
            f"{mv14_v['requested_smoke_R']}/{mv14_v['requested_core_R']}/{mv14_v['requested_dif_R']}; "
            f"convergence-safe full-ladder effective R {mv14_v['core_effective_draws']}/"
            f"{mv14_v['core_selection_attempted_draws']} after fit-success R "
            f"{mv14_v['core_all_fit_success_draws']}; configural converged R "
            f"{mv14_v['configural_converged_draws']}/{mv14_v['core_selection_attempted_draws']}; "
            f"stable-ladder effective R {mv14_v['stable_ladder_effective_draws']}; DIF effective R "
            f"{mv14_v['dif_min_anchor_effective_draws']}/{mv14_dif_attempted}; stable anchors "
            f"{';'.join(mv14_v['stable_anchor_items'])}; top threshold-DIF items "
            f"{';'.join(mv14_v['top_threshold_dif_items'])}; best AIC/BIC models "
            f"{mv14_v['best_aic_model']}/{mv14_v['best_bic_model']}; stable-ladder AIC/BIC "
            f"{mv14_v['stable_ladder_best_aic_model']}/{mv14_v['stable_ladder_best_bic_model']}; "
            f"parameterization contract {mv14_v.get('parameterization_contract', 'unknown')}. "
            f"{mv14_parameterization_note}"
        ),
        "mirt_param_audit": (
            f"mirt parameterization audit: status {mirt_decision['audit_status']}; "
            f"statistical correctness blocker {mirt_decision['statistical_correctness_blocker']}; "
            f"{mirt_decision['short_read']}"
        ),
        "mv19": (
            f"MV19 finite-sample PHQ simulation: status {mv19_v['pass_rule_status']}; "
            f"H0 C02/C06 both-flag false rate {fmt(mv19_v['h0_target_both_false_rate'])}; "
            f"H0 C02/C06 top-two false-localization {fmt(mv19_v['h0_target_top2_false_rate'])}; "
            f"H1 C02/C06 both-flag recovery {fmt(mv19_v['h1_target_both_recovery_rate'])}; "
            f"H1 C02/C06 top-two recovery {fmt(mv19_v['h1_target_top2_recovery_rate'])}; "
            f"H1 anchor subset recovery {fmt(mv19_v['h1_anchor_target_subset_recovery_rate'])}; "
            f"pass_rule_met={mv19_v['pass_rule_met']}."
        ),
        "mv20": (
            f"MV20 criterion-overlap stress: status {mv20_v['pass_rule_status']}; "
            f"primary CMDC PHQ-9 BGE-M3 top-20 gate {mv20_v['primary_gate_status']}; "
            f"all/minus-high/minus-random/high-only MAE "
            f"{fmt(mv20_v['primary_all_metric'])}/{fmt(mv20_v['primary_minus_high_metric'])}/"
            f"{fmt(mv20_v['primary_minus_random_metric'])}/{fmt(mv20_v['primary_high_only_metric'])}; "
            f"criterion excess loss vs matched random {fmt(mv20_v['primary_criterion_excess_loss_vs_random'])} "
            f"with 95% CI {fmt(mv20_v['primary_criterion_excess_loss_ci95_low'])}-"
            f"{fmt(mv20_v['primary_criterion_excess_loss_ci95_high'])}; "
            f"mE5 sensitivity gate {mv20_v['sensitivity_gate_status']}; "
            f"stop rule {mv20_v['stop_rule']}."
        ),
        "mv12_design": (
            f"MV12 two-stage latent-target design: status {mv12_d['readiness_status']}; "
            f"full_method_allowed={mv12_d['full_method_allowed']}; "
            f"outputs predeclare {mv12_design['outputs']['model_ladder_rows']} model-ladder rows, "
            f"{mv12_design['outputs']['identity_transfer_gate_rows']} identity/transfer gates, and "
            f"{mv12_design['outputs']['pass_fail_gate_rows']} pass/fail gates."
        ),
        "mv12_run": (
            f"Legacy MV12 two-stage latent-target run under the old Chinese-BGE chain: status {mv12_v['pass_rule_status']}; "
            f"E-DAIC same-dataset theta delta vs train mean {fmt(mv12_v['m12a_edaic_delta_theta_mae_vs_B0'])}; "
            f"CMDC same-dataset theta delta {fmt(mv12_v['m12a_cmdc_delta_theta_mae_vs_B0'])}; "
            f"E-DAIC observed macro delta vs direct itemwise {fmt(mv12_v['m12a_edaic_delta_observed_macro_mae_vs_B3'])}; "
            f"CMDC observed macro delta {fmt(mv12_v['m12a_cmdc_delta_observed_macro_mae_vs_B3'])}; "
            f"conditional identity BA {fmt(mv12_v['conditional_identity_ba_m12a'])}; "
            f"old-chain external theta transfer pass={mv12_v['external_transfer_theta_gate_passed']}; "
            "source-calibrated external theta transfer should be interpreted with measurement-function mismatch, "
            "and MV17a supersedes universal external-transfer wording."
        ),
        "mv12_analysis": (
            f"Legacy MV12 aggregate tradeoff analysis: status {mv12_a['analysis_status']}; "
            f"freeze_current_latent_target_line={mv12_a['freeze_current_latent_target_line']}; "
            f"tradeoff_rows={mv12_analysis['outputs']['tradeoff_rows']}; "
            f"failure_mode_rows={mv12_analysis['outputs']['failure_mode_rows']}; "
            f"{mv12_a['dimension_matched_identity_caveat']} MV17a supersedes universal B3-dominance wording."
        ),
        "mv15_design": (
            f"MV15 latent-conditioned identity design: status {mv15_d['design_status']}; "
            f"primary scope {mv15_d['primary_scope']}; "
            f"conditioning ladder rows {mv15_design['outputs']['conditioning_ladder_rows']}; "
            f"identity probe rows {mv15_design['outputs']['identity_probe_rows']}; "
            f"pass/fail gates {mv15_design['outputs']['pass_fail_gate_rows']}; "
            f"full_method_allowed={mv15_d['full_method_allowed']}."
        ),
        "mv15_run": (
            f"Legacy MV15 latent-conditioned identity run under the old Chinese-BGE chain: status {mv15_v['pass_rule_status']}; "
            f"raw feature identity BA {fmt(mv15_v['raw_feature_identity_ba'])}; "
            f"theta-conditioned feature identity BA {fmt(mv15_v['theta_conditioned_feature_identity_ba'])}; "
            f"total/predicted-total/B3-conditioned feature identity BA "
            f"{fmt(mv15_v['total_conditioned_feature_identity_ba'])}/"
            f"{fmt(mv15_v['predicted_total_conditioned_feature_identity_ba'])}/"
            f"{fmt(mv15_v['b3_itemwise_theta_conditioned_feature_identity_ba'])}; "
            f"theta-only identity BA {fmt(mv15_v['theta_only_identity_ba'])}; "
            f"predicted-theta output identity BA {fmt(mv15_v['psychometric_predicted_theta_output_identity_ba'])}; "
            f"old-chain B3 Pareto dominates predicted theta output={mv15_v['b3_pareto_dominates_predicted_theta_output']}; "
            f"full_method_allowed={mv15_v['full_method_allowed']}. MV17a makes B3 dominance encoder-dependent."
        ),
        "mv16_run": (
            f"MV16 DIF-guided few-shot calibration run: status {mv16_v['pass_rule_status']}; "
            f"subject-overlap gate {mv16_v['subject_overlap_gate_passed']}; "
            f"anchor safety {mv16_v['anchor_safety_gate_passed']}; "
            f"DIF-guided small-k gate {mv16_v['dif_guided_small_k_gate_passed']}; "
            f"direct-baseline gate {mv16_v['direct_baseline_gate_passed']}; "
            f"best supported row {mv16_v['best_supported_direction']}/{mv16_v['best_supported_model']} "
            f"at k={mv16_v['best_supported_k']}; "
            f"best L4 small-k delta theta MAE vs L0 {fmt(mv16_v['best_l4_small_k_delta_theta_mae_vs_L0'])}; "
            f"L4 small-k output identity BA {fmt(mv16_v['l4_small_k_output_identity_ba_mean'])}; "
            f"full_method_allowed={mv16_v['full_method_allowed']}."
        ),
        "mv17a": mv17a_context["mv17a_summary"],
        "mv21": mv21_context["mv21_sentence"],
        "mv22": mv22_context["mv22_sentence"],
        "mv23": mv23_context["mv23_sentence"],
        "pdch": (
            f"PDCH item-derived total MAE {fmt(mv02_v['best_pdch_item_total_mae'])}; "
            f"direct total MAE {fmt(mv02_v['best_pdch_direct_total_mae'])}; "
            f"macro item MAE {fmt(mv02_v['best_pdch_macro_item_mae'])}; status {mv02_v['pass_rule_status']}."
        ),
        "modma": (
            f"MODMA task projection reduces feature task identity BA {fmt(modma['raw_feature_identity_ba'])} -> "
            f"{fmt(modma['feature_identity_ba_after'])} while preserving main task signal "
            f"({fmt(modma['raw_primary_metric_value'])})."
        ),
        "eatd": (
            f"EATD valence/SDS remains blocked: raw primary MAE {fmt(eatd['raw_primary_metric_value'])} "
            f"versus train-mean floor {fmt(eatd['floor_primary_metric_value'])}; status {eatd['status']}."
        ),
        "mv06": (
            f"MV06 has {mv06_gate['completed_candidates']} completed and "
            f"{mv06_gate['double_annotated_candidates']} double-annotated candidates. Evidence-presence kappa: "
            f"{all_kappa}, {cmdc_kappa}, {pdch_kappa}, {edaic_kappa}."
            f"{mv06_remaining_clause} Field-specific degenerate marginal statuses should be read from agreement_summary.csv."
        ),
    }


def claim_evidence_sentence(claim_id: str, context: dict[str, str], row: pd.Series) -> str:
    if claim_id in {"C_FULL_METHOD_START", "C_PUBLISHABLE_PAPER_DIRECTION"}:
        return f"{context['gate']} {context['mv10']} {context['mv11']} {context['mv13']} {context['mv14']} {context['mirt_param_audit']} {context['mv19']} {context['mv21']} {context['mv12_design']} {context['mv12_run']} {context['mv12_analysis']} {context['mv15_design']} {context['mv15_run']} {context['mv16_run']} {context['mv17a']} {context['mv22']} {context['mv20']}"
    if claim_id == "C_RQ1_SHARED_SYMPTOM":
        return f"{context['rq1']} {context['mv19']} {context['mv21']} {context['mv12_analysis']} {context['mv15_run']} {context['mv22']}"
    if claim_id == "C_PSYCHOMETRIC_INVARIANCE_BASELINE":
        return f"{context['mv10']} {context['mv11']} {context['mv13']} {context['mv14']} {context['mirt_param_audit']} {context['mv19']} {context['mv21']} {context['mv12_design']} {context['mv12_run']} {context['mv12_analysis']}"
    if claim_id == "C_PDCH_HAMD_INTERNAL":
        return f"{context['pdch']} {context['mv21']}"
    if claim_id in {"C_EATD_SDS_GENERALIZATION", "C_EATD_VALENCE_ADVERSARIAL"}:
        return context["eatd"]
    if claim_id == "C_DATASET_IDENTITY_CONTROL":
        return f"{context['mv09']} {context['mv15_run']} {context['mv17a']} {context['mv22']}"
    if claim_id == "C_PROTOCOL_CRITERION_OVERLAP":
        return context["mv20"]
    if claim_id == "C_MODMA_TASK_CONTROL":
        return context["modma"]
    if claim_id == "C_RQ4_EVIDENCE_LOCALIZATION":
        return context["mv06"]
    return str(row["blocking_evidence"])


def blocked_language(decision: str) -> str:
    if decision == "blocked":
        return "Do not use as a positive claim; report as negative or blocked evidence."
    if decision == "allowed_limited":
        return "Allowed only with the scoped wording in this table."
    if decision == "allowed_with_reframing":
        return "Allowed as paper framing, not as a full-method success claim."
    return "Review before manuscript use."


def build_claim_boundary() -> pd.DataFrame:
    claims = pd.read_csv(CLAIM_GATE)
    context = build_metric_context()
    rows: list[dict[str, Any]] = []
    for _, row in claims.iterrows():
        claim_id = str(row["claim_id"])
        source_artifact_ids = str(row["primary_sources"])
        if claim_id in {"C_FULL_METHOD_START", "C_PUBLISHABLE_PAPER_DIRECTION", "C_RQ1_SHARED_SYMPTOM", "C_DATASET_IDENTITY_CONTROL"}:
            source_artifact_ids = f"{source_artifact_ids};P5_MV22;P5_MV23"
        rows.append(
            {
                "claim_id": claim_id,
                "paper_section": CLAIM_SECTION.get(claim_id, "Other"),
                "decision": row["decision"],
                "paper_claim_language": paper_text(PAPER_CLAIM_LANGUAGE.get(claim_id, str(row["claim"]))),
                "allowed_scope": paper_text(row["allowed_scope"]),
                "evidence_to_report": paper_text(claim_evidence_sentence(claim_id, context, row)),
                "manuscript_guardrail": blocked_language(str(row["decision"])),
                "next_evidence_needed": paper_text(row["required_next_evidence"]),
                "source_artifact_ids": source_artifact_ids,
            }
        )
    return pd.DataFrame(rows)


def build_key_findings() -> pd.DataFrame:
    context = build_metric_context()
    rows = [
        {
            "finding_id": "gate_status",
            "paper_section": "Claim boundary",
            "finding": context["gate"],
            "interpretation": "Full method construction remains blocked; measurement-shift paper framing is allowed with bounded claims.",
            "source_artifact_ids": "full_method_gate_audit",
        },
        {
            "finding_id": "rq1_measurement_negative",
            "paper_section": "Measurement evidence",
            "finding": context["rq1"],
            "interpretation": "Measurement screens and residual measurement heads are diagnostic under current features; MV10/MV11/MV19 shift RQ1 to measurement-target validity while corrected MV13/MV14 provide anchor-linked external mirt corroboration under convergence and finite-sample caveats. MV17a makes BGE-M3 the primary feature-contract consequence layer and shows that observed-scale safety and feature invariance remain blocked under multilingual encoders.",
                "source_artifact_ids": "P5_MV08;P5_MV08b;P5_MV09;P5_MV10;P5_MV11;P5_MV13;P5_MV14;P5_mirt_parameterization_audit;P5_MV19;P5_MV21;P5_MV12;P5_MV12_analysis;P5_MV15;P5_MV16;P5_MV17a;P5_MV22;P5_MV23",
        },
        {
            "finding_id": "legacy_bge_feature_contract_caveat",
            "paper_section": "Feature-contract caveat",
            "finding": "The E-DAIC MV07 feature generator used a Chinese BGE v1.5 model on English transcripts and concatenated available transcript Text rows without speaker filtering; the current transcript CSV contract lacks a speaker column.",
            "interpretation": "Treat the old Chinese-BGE feature-level evidence as appendix/historical diagnostic. MV17a has regenerated E-DAIC/CMDC/PDCH features with BGE-M3 as the primary feature contract and multilingual-E5 as sensitivity; it reproduces the blocked MV07/MV12/MV15 gate pattern while showing that external theta transfer and B3 Pareto dominance are encoder-dependent. Label-only MV10/MV11/MV19 primary psychometric evidence is unaffected by the feature-contract caveat; corrected MV13/MV14 carry only the remaining convergence and finite-sample caveats.",
            "source_artifact_ids": "phase5_generate_mv07_edaic_bge_features;P5_MV17a;BGE_model_cards;E-DAIC_transcript_schema",
        },
        {
            "finding_id": "mv17a_multilingual_feature_contract",
            "paper_section": "Measurement evidence",
            "finding": context["mv17a"],
            "interpretation": "MV17a resolves the old language-encoder caveat for the paper-critical feature chain. Stable conclusions are domain-learnable theta, low output-level identity, failed observed-scale safety, and failed feature invariance; external theta transfer and B3 Pareto dominance are encoder-dependent.",
            "source_artifact_ids": "P5_MV17a",
        },
        {
            "finding_id": "mv22_foundation_backbone_validation",
            "paper_section": "Measurement-aware foundation stress test",
            "finding": context["mv22"],
            "interpretation": "MV22 closes the immediate foundation-model validation gap without claiming SOTA: Qwen strengthens the text backbone, WavLM base-plus supplies an audio proxy view, adaptation baselines pressure representation alignment, and the measurement-aware reference remains useful while feature identity and observed-scale safety gates stay visible.",
            "source_artifact_ids": "P5_MV22",
        },
        {
            "finding_id": "mv23_foundation_multimodal_completion",
            "paper_section": "Measurement-aware foundation stress test",
            "finding": context["mv23"],
            "interpretation": "MV23 adds the lightweight multimodal completion layer: audio-only, video-proxy, text-audio, and text-audio-video views are evaluated under the same PHQ shared-item transfer contract, with direct/alignment baselines and a measurement-aware latent-total proxy head. It supports the foundation-era framework argument without claiming WavLM Large, HuBERT Large, VideoMAE, or full end-to-end multimodal completion.",
            "source_artifact_ids": "P5_MV23",
        },
        {
            "finding_id": "mv10_psychometric_baseline",
            "paper_section": "Psychometric baseline",
            "finding": context["mv10"],
            "interpretation": "The label-only PHQ screen supports substantial common structure and candidate anchors, but exact threshold/scalar equivalence is not uniformly supported.",
            "source_artifact_ids": "P5_MV10",
        },
        {
            "finding_id": "mv11_formal_psychometric_confirmation",
            "paper_section": "Psychometric baseline",
            "finding": context["mv11"],
            "interpretation": "The formal label-only IRT confirmation preserves the MV10 anchor map but leaves an AIC/BIC caveat, so it supports target design rather than a full method claim.",
            "source_artifact_ids": "P5_MV11",
        },
        {
            "finding_id": "mv13_external_psychometric_replication",
            "paper_section": "Psychometric baseline",
            "finding": context["mv13"],
            "interpretation": "The corrected external R mirt replication preserves the MV11 qualitative anchor/DIF pattern under anchor-linked focal mean/variance handling; use it as external corroboration with the retained configural convergence warning.",
            "source_artifact_ids": "P5_MV13",
        },
        {
            "finding_id": "mv14_measurement_uncertainty_bootstrap",
            "paper_section": "Psychometric baseline",
            "finding": context["mv14"],
            "interpretation": "The convergence-safe bootstrap now uses corrected anchor-linked focal mean/variance handling. MV19 still shows observed-N finite-sample sensitivity; report C02/C06 as repeated localized threshold-shift evidence with downgrade, not as robust standalone DIF.",
            "source_artifact_ids": "P5_MV14",
        },
        {
            "finding_id": "mirt_parameterization_correctness_audit",
            "paper_section": "Psychometric baseline",
            "finding": context["mirt_param_audit"],
            "interpretation": "The statistical correctness blocker is resolved for MV13/MV14 parameterization: reference/focal order, anchor linking, threshold constraints, and freed focal mean/variance are verified. Remaining manuscript limits come from convergence warnings and finite-sample behavior, not the mirt identification contract.",
            "source_artifact_ids": "P5_mirt_parameterization_audit",
        },
        {
            "finding_id": "mv19_finite_sample_phq_simulation",
            "paper_section": "Psychometric baseline",
            "finding": context["mv19"],
            "interpretation": "The observed-N simulation closes the small-sample uncertainty layer by showing adequate both-target H1 flagging but high false/localization sensitivity, low top-two recovery, and poor exact anchor-set recovery; C02/C06 wording must be finite-sample-bounded.",
            "source_artifact_ids": "P5_MV19",
        },
        {
            "finding_id": "mv21_measurement_discrepancy_gradient",
            "paper_section": "Psychometric baseline",
            "finding": context["mv21"],
            "interpretation": "MV21 reframes the added analyses as a discrepancy gradient: DAIC-WOZ/E-DAIC is a same-lineage PHQ-8 control with tiny paired/conditioned label-contract differences, E-DAIC/CMDC is the main PHQ shared-item dataset-group comparison, and CMDC/PDCH HAMD is exploratory same-scale context-shift support. It is descriptive and severity-conditioned, not a new formal MIM/IRT model.",
            "source_artifact_ids": "P5_MV21",
        },
        {
            "finding_id": "mv20_criterion_overlap_stress",
            "paper_section": "Identity and protocol diagnostics",
            "finding": context["mv20"],
            "interpretation": "MV20 closes the protocol-label-overlap gap as a negative stress test: high-overlap CMDC question-position deletion is directionally worse than random deletion, but the predeclared paired bootstrap interval crosses zero under both BGE-M3 primary and mE5 sensitivity. Do not tune thresholds or add a contamination-aware model from this result.",
            "source_artifact_ids": "P5_MV20",
        },
        {
            "finding_id": "mv12_two_stage_latent_target_design",
            "paper_section": "Measurement evidence",
            "finding": context["mv12_design"],
            "interpretation": "The next method test is now predeclared: separate Y_to_theta measurement from X_to_theta prediction, keep scores and parameters local-only, and gate on direct floors, transfer, and conditional identity.",
            "source_artifact_ids": "P5_MV12_design",
        },
        {
            "finding_id": "mv12_two_stage_latent_target_run",
            "paper_section": "Measurement evidence",
            "finding": context["mv12_run"],
            "interpretation": "The legacy Chinese-BGE two-stage run supports a bounded measurement-shift story: the low-dimensional latent/scalar prediction layer reduces identity versus upstream features, but its universal external-transfer-failure wording is superseded by MV17a's encoder-specific sensitivity.",
            "source_artifact_ids": "P5_MV12",
        },
        {
            "finding_id": "mv12_tradeoff_freeze_decision",
            "paper_section": "Measurement evidence",
            "finding": context["mv12_analysis"],
            "interpretation": "The legacy aggregate tradeoff analysis remains useful as a dimension-matched severity-control warning, but MV17a shows B3 Pareto dominance is encoder-dependent rather than a universal mechanism conclusion.",
            "source_artifact_ids": "P5_MV12_analysis",
        },
        {
            "finding_id": "mv15_latent_conditioned_identity_design",
            "paper_section": "Identity and protocol diagnostics",
            "finding": context["mv15_design"],
            "interpretation": "MV15 design predeclared the identity-gate follow-up before the run: raw feature identity, observed labels, PHQ total, predicted total, direct-itemwise-theta severity, psychometric theta, covariates, predicted-output identity, and severity-only external sensitivity.",
            "source_artifact_ids": "P5_MV15_design",
        },
        {
            "finding_id": "mv15_latent_conditioned_identity_run",
            "paper_section": "Identity and protocol diagnostics",
            "finding": context["mv15_run"],
            "interpretation": "MV15 blocks theta-specific feature-invariance wording under the legacy BGE contract; MV17a repeats the paper-critical identity pattern under BGE-M3 and multilingual-E5, while the output-level B3 dominance comparison becomes encoder-dependent.",
            "source_artifact_ids": "P5_MV15",
        },
        {
            "finding_id": "mv16_dif_guided_calibration_run",
            "paper_section": "Measurement evidence",
            "finding": context["mv16_run"],
            "interpretation": "MV16 completes the predeclared localized DIF calibration test but does not pass the both-direction small-k mechanism gate; report it as bounded or negative calibration evidence, not as a full method.",
            "source_artifact_ids": "P5_MV16",
        },
        {
            "finding_id": "mv09_conditional_identity_gate",
            "paper_section": "Identity and protocol diagnostics",
            "finding": context["mv09"],
            "interpretation": "Unconditional identity should not be the only hard gate, but conditional BGE identity remains high enough to block a shared-latent claim.",
            "source_artifact_ids": "P5_MV09",
        },
        {
            "finding_id": "pdch_internal_hamd",
            "paper_section": "HAMD diagnostic evidence",
            "finding": context["pdch"],
            "interpretation": "PDCH supports bounded internal HAMD measurement evidence only.",
            "source_artifact_ids": "P5_MV02",
        },
        {
            "finding_id": "modma_task_control",
            "paper_section": "Identity and protocol diagnostics",
            "finding": context["modma"],
            "interpretation": "MODMA provides bounded task-control evidence.",
            "source_artifact_ids": "P5_MV04c",
        },
        {
            "finding_id": "eatd_negative_stress",
            "paper_section": "External stress tests",
            "finding": context["eatd"],
            "interpretation": "EATD should remain a negative stress test, not a method component driver.",
            "source_artifact_ids": "P5_MV03;P5_MV03b;P5_MV04c",
        },
        {
            "finding_id": "mv06_first_round_evidence",
            "paper_section": "Evidence localization",
            "finding": context["mv06"],
            "interpretation": "MV06 can support first-round aggregate credibility; stronger RQ4 claims still need the remaining incomplete local candidate resolved and sampling limits discussed.",
            "source_artifact_ids": "P5_MV06_summary",
        },
    ]
    return pd.DataFrame(rows)


def literature_positioning() -> pd.DataFrame:
    return pd.DataFrame(LITERATURE_ROWS)


def write_claim_markdown(out_dir: Path, claims: pd.DataFrame) -> None:
    lines = [
        "# Paper Claim Boundary",
        "",
        "| section | decision | paper claim language | evidence to report | guardrail |",
        "| --- | --- | --- | --- | --- |",
    ]
    for _, row in claims.iterrows():
        lines.append(
            "| "
            + " | ".join(
                [
                    md_escape(row["paper_section"]),
                    md_escape(row["decision"]),
                    md_escape(row["paper_claim_language"]),
                    md_escape(row["evidence_to_report"]),
                    md_escape(row["manuscript_guardrail"]),
                ]
            )
            + " |"
        )
    (out_dir / "paper_claim_boundary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_report(out_dir: Path, run_summary: dict[str, Any], claims: pd.DataFrame, findings: pd.DataFrame) -> None:
    allowed = claims[claims["decision"].isin(["allowed_limited", "allowed_with_reframing"])]
    blocked = claims[claims["decision"] == "blocked"]
    lines = [
        "# Diagnostic Measurement-Audit Paper Tables",
        "",
        f"Generated: `{run_summary['generated_at']}`",
        "",
        "## Scope",
        "",
        "This writing-prep artifact converts existing aggregate gates into paper-facing claim, evidence, and positioning tables. It does not read private review material or row-level model outputs.",
        "",
        "## Claim Boundary",
        "",
        f"- Allowed or reframed claim rows: `{len(allowed)}`.",
        f"- Blocked claim rows: `{len(blocked)}`.",
        f"- Key finding rows: `{len(findings)}`.",
        f"- Literature-positioning rows: `{run_summary['outputs']['literature_positioning_rows']}`.",
        f"- Artifact hygiene passed: `{run_summary['artifact_hygiene_passed']}`.",
        "",
        "## Key Findings",
        "",
        "| finding | interpretation |",
        "| --- | --- |",
    ]
    for _, row in findings.iterrows():
        lines.append(f"| {md_escape(row['finding'])} | {md_escape(row['interpretation'])} |")
    lines.extend(
        [
            "",
            "## Release Rule",
            "",
            "- Use these tables as manuscript scaffolding, not as a replacement for the source artifacts.",
            "- Keep private review material, learned parameters, and row-level model outputs local-only.",
            "- Any stronger RQ4 claim should first resolve any remaining incomplete local candidate rows and discuss agreement uncertainty plus sampling limits.",
        ]
    )
    (out_dir / "report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def artifact_hygiene(out_dir: Path) -> dict[str, Any]:
    forbidden_patterns = [
        r"/root/",
        r"/autodl-tmp/",
        r"\bsubject_id\b",
        r"\.wav\b",
        r"\.mp4\b",
        r"\.avi\b",
        r"local_annotation_workbook",
        r"source_locator",
        r"local_row_predictions",
        r"p5_mv[0-9a-z_]*_local_",
        r"raw snippet",
        r"raw evidence snippet",
    ]
    violations: list[dict[str, str]] = []
    checked = 0
    for path in sorted(out_dir.glob("*")):
        if not path.is_file() or path.name not in TRACKED_FILES:
            continue
        checked += 1
        text = path.read_text(encoding="utf-8", errors="ignore")
        for pattern in forbidden_patterns:
            if re.search(pattern, text, flags=re.IGNORECASE):
                violations.append({"file": path.name, "pattern": pattern})
    return {
        "audit_id": "diagnostic_measurement_audit_paper_tables_hygiene",
        "generated_at": utc_now(),
        "files_checked": checked,
        "artifact_hygiene_passed": not violations,
        "violation_count": len(violations),
        "violations": violations,
    }


def build_outputs(out_dir: Path, generated_at: str) -> dict[str, Any]:
    out_dir.mkdir(parents=True, exist_ok=True)
    claims = build_claim_boundary()
    findings = build_key_findings()
    literature = literature_positioning()

    claims.to_csv(out_dir / "paper_claim_boundary.csv", index=False)
    findings.to_csv(out_dir / "key_numeric_findings.csv", index=False)
    literature.to_csv(out_dir / "literature_positioning.csv", index=False)
    write_claim_markdown(out_dir, claims)

    stale_hygiene = out_dir / "artifact_hygiene_audit.json"
    if stale_hygiene.exists():
        stale_hygiene.unlink()

    run_summary = {
        "run_id": "diagnostic_measurement_audit_paper_tables",
        "generated_at": generated_at,
        "status": "complete",
        "input_contract": {
            "full_method_gate_read": True,
            "aggregate_phase5_summaries_read": True,
            "raw_data_scanned": False,
            "private_review_material_read": False,
            "row_level_model_outputs_read": False,
        },
        "outputs": {
            "tracked_outputs": TRACKED_FILES,
            "claim_rows": int(len(claims)),
            "key_finding_rows": int(len(findings)),
            "literature_positioning_rows": int(len(literature)),
        },
        "decision": {
            "paper_table_status": "ready_for_diagnostic_paper_drafting",
            "short_read": "Paper-facing claim and evidence tables are ready from aggregate gates; full method remains blocked.",
        },
        "artifact_hygiene_passed": False,
    }
    (out_dir / "run_summary.json").write_text(json.dumps(run_summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    write_report(out_dir, run_summary, claims, findings)
    hygiene = artifact_hygiene(out_dir)
    run_summary["artifact_hygiene_passed"] = bool(hygiene["artifact_hygiene_passed"])
    (out_dir / "run_summary.json").write_text(json.dumps(run_summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    write_report(out_dir, run_summary, claims, findings)
    hygiene = artifact_hygiene(out_dir)
    (out_dir / "artifact_hygiene_audit.json").write_text(json.dumps(hygiene, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if not hygiene["artifact_hygiene_passed"]:
        raise SystemExit("artifact hygiene violations found; see artifact_hygiene_audit.json")
    return run_summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    args = parser.parse_args()

    require_inputs()
    generated_at = utc_now()
    run_summary = build_outputs(args.out_dir, generated_at)
    print(
        "Wrote diagnostic paper tables to "
        f"{args.out_dir.relative_to(ROOT)} with status "
        f"{run_summary['decision']['paper_table_status']}"
    )


if __name__ == "__main__":
    main()
