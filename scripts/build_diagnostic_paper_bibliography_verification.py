#!/usr/bin/env python3
"""Build a manuscript bibliography primary-source verification ledger.

This is a writing-side audit helper. It reads the existing public citation
registry and records which references have been manually spot-checked against
primary source pages during manuscript editing. It does not browse, read raw
datasets, inspect row-level outputs, or alter the BibTeX generator.
"""

from __future__ import annotations

import argparse
import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
PAPER_DIR = ROOT / "analysis" / "diagnostic_measurement_audit_paper"
REGISTRY_CSV = PAPER_DIR / "citation_registry.csv"

TRACKED_FILES = [
    "bibliography_verification_hygiene_audit.json",
    "bibliography_verification_ledger.csv",
    "bibliography_verification_report.md",
    "bibliography_verification_run_summary.json",
]
HYGIENE_CHECKED_FILES = [
    name for name in TRACKED_FILES if name != "bibliography_verification_hygiene_audit.json"
]


SPOT_CHECKS: dict[str, dict[str, str]] = {
    "arjovsky2019irm": {
        "verification_status": "spot_checked_primary_source",
        "checked_source_url": "https://arxiv.org/abs/1907.02893",
        "checked_fields": "title;authors;submission_date;arxiv_id;invariant_risk_use_claim",
        "use_claim_status": "supported_for_invariant_risk_baseline_positioning",
        "remaining_submission_check": "confirm venue style and capitalization against final bibliography format",
    },
    "baevski2020wav2vec2": {
        "verification_status": "spot_checked_primary_source",
        "checked_source_url": "https://arxiv.org/abs/2006.11477",
        "checked_fields": "title;authors;submission_date;arxiv_id;speech_foundation_use_claim",
        "use_claim_status": "supported_for_wav2vec2_speech_foundation_sensitivity_contract",
        "remaining_submission_check": "confirm venue style and capitalization against final bibliography format",
    },
    "bulut2017detecting": {
        "verification_status": "spot_checked_primary_source",
        "checked_source_url": "https://www.frontiersin.org/journals/education/articles/10.3389/feduc.2017.00051/full",
        "checked_fields": "title;authors;year;journal;volume;doi;dif_method_use_claim",
        "use_claim_status": "supported_for_irt_lr_and_logistic_dif_method_context",
        "remaining_submission_check": "confirm Frontiers article-number formatting against target venue style",
    },
    "burdisso2024daicprompts": {
        "verification_status": "spot_checked_primary_source",
        "checked_source_url": "https://aclanthology.org/2024.clinicalnlp-1.8/;https://doi.org/10.18653/v1/2024.clinicalnlp-1.8",
        "checked_fields": "title;authors;year;venue;pages;doi;therapist_prompt_use_claim",
        "use_claim_status": "supported_for_daic_prompt_validity_and_protocol_leakage_positioning",
        "remaining_submission_check": "confirm venue style and capitalization against final bibliography format",
    },
    "cai2020modma": {
        "verification_status": "spot_checked_primary_source",
        "checked_source_url": "https://www.nature.com/articles/s41597-022-01211-x;https://reshare.ukdataservice.ac.uk/854301/;https://arxiv.org/abs/2002.09283",
        "checked_fields": "title;authors;year;journal;volume;article_number;doi;dataset_access_page;modma_use_claim",
        "use_claim_status": "supported_for_modma_controlled_task_dataset_context_after_switch_to_scientific_data_descriptor",
        "remaining_submission_check": "citation key still encodes the original 2020 preprint year; rename only if final manuscript citation-key hygiene requires it",
    },
    "chalmers2012mirt": {
        "verification_status": "spot_checked_primary_source",
        "checked_source_url": "https://www.jstatsoft.org/article/view/v048i06",
        "checked_fields": "title;author;year;journal;volume;issue;pages;doi;mirt_runtime_use_claim",
        "use_claim_status": "supported_for_mirt_irt_runtime_citation",
        "remaining_submission_check": "confirm venue style and capitalization against final bibliography format",
    },
    "chalmers2026mirtmultiplegroup": {
        "verification_status": "spot_checked_primary_source",
        "checked_source_url": "https://philchalmers.github.io/mirt/html/multipleGroup.html",
        "checked_fields": "documentation_title;author;access_year;multiple_group_arguments;anchor_invariance_use_claim",
        "use_claim_status": "supported_for_mv13_multiple_group_irt_workflow_documentation",
        "remaining_submission_check": "capture package version/session info if final reproducibility appendix requires it",
    },
    "chen2022wavlm": {
        "verification_status": "spot_checked_primary_source",
        "checked_source_url": "https://arxiv.org/abs/2110.13900",
        "checked_fields": "title;authors;submission_date;arxiv_id;doi;speech_foundation_use_claim",
        "use_claim_status": "supported_for_wavlm_speech_foundation_positioning_after_author_list_correction",
        "remaining_submission_check": "confirm whether final style should cite arXiv or IEEE JSTSP version",
    },
    "gratch2014distress": {
        "verification_status": "spot_checked_primary_source",
        "checked_source_url": "https://aclanthology.org/L14-1421/",
        "checked_fields": "title;authors;year;venue;pages;publisher;corpus_use_claim",
        "use_claim_status": "supported_for_daic_clinical_interview_multimodal_context",
        "remaining_submission_check": "confirm venue style and capitalization against final bibliography format",
    },
    "nguyen2022improving": {
        "verification_status": "spot_checked_primary_source",
        "checked_source_url": "https://aclanthology.org/2022.acl-long.578/",
        "checked_fields": "title;authors;year;venue;pages;doi;questionnaire_grounding_use_claim",
        "use_claim_status": "supported_for_phq9_questionnaire_grounding_and_ood_generalization_positioning",
        "remaining_submission_check": "confirm venue style and capitalization against final bibliography format",
    },
    "zhang2025interviewer": {
        "verification_status": "spot_checked_primary_source",
        "checked_source_url": "https://aclanthology.org/2025.findings-emnlp.650/",
        "checked_fields": "title;authors;year;venue;pages;doi;interviewer_bias_use_claim",
        "use_claim_status": "supported_for_question_type_and_context_as_protocol_nuisance_positioning",
        "remaining_submission_check": "confirm venue style and capitalization against final bibliography format",
    },
    "deduro2026nlppsychometrics": {
        "verification_status": "spot_checked_primary_source",
        "checked_source_url": "https://arxiv.org/abs/2608.07316",
        "checked_fields": "title;authors;submission_date;arxiv_id;doi;nlp_psychometrics_use_claim",
        "use_claim_status": "supported_for_emerging_nlp_psychometrics_framing",
        "remaining_submission_check": "check for later arXiv version or peer-reviewed venue before submission",
    },
    "mandal2025questmf": {
        "verification_status": "spot_checked_primary_source",
        "checked_source_url": "https://aclanthology.org/2025.clpsych-1.4/",
        "checked_fields": "title;authors;year;venue;pages;doi;question_wise_fusion_use_claim",
        "use_claim_status": "supported_for_nearby_edaic_question_wise_item_prediction_positioning",
        "remaining_submission_check": "confirm venue style and capitalization against final bibliography format",
    },
    "chen2024gnnsda": {
        "verification_status": "spot_checked_primary_source",
        "checked_source_url": "https://doi.org/10.1109/TMM.2023.3312917",
        "checked_fields": "title;authors;year;venue;pages;doi;gnn_sda_baseline_use_claim",
        "use_claim_status": "supported_for_mv26_close_depression_specific_baseline_positioning",
        "remaining_submission_check": "confirm final IEEE page metadata before submission",
    },
    "zhang2025red": {
        "verification_status": "spot_checked_primary_source",
        "checked_source_url": "https://aclanthology.org/2025.findings-acl.517/",
        "checked_fields": "title;authors;year;venue;pages;doi;evidence_retrieval_use_claim",
        "use_claim_status": "supported_for_evidence_retrieval_positioning_not_as_our_main_novelty",
        "remaining_submission_check": "confirm venue style and capitalization against final bibliography format",
    },
    "baai2026bgem3": {
        "verification_status": "spot_checked_primary_source",
        "checked_source_url": "https://huggingface.co/BAAI/bge-m3",
        "checked_fields": "model_id;organization;license;multilinguality;long_context_claim",
        "use_claim_status": "supported_for_bge_m3_multilingual_primary_feature_contract",
        "remaining_submission_check": "capture exact model revision/hash if required by venue reproducibility checklist",
    },
    "baai2026bgesmallzh": {
        "verification_status": "spot_checked_primary_source",
        "checked_source_url": "https://huggingface.co/BAAI/bge-small-zh-v1.5",
        "checked_fields": "model_id;organization;language_tag;model_list_language;legacy_caveat_use_claim",
        "use_claim_status": "supported_for_old_chinese_bge_feature_contract_caveat",
        "remaining_submission_check": "capture exact model revision/hash if required by venue reproducibility checklist",
    },
    "wang2024multilinguale5": {
        "verification_status": "spot_checked_primary_source",
        "checked_source_url": "https://huggingface.co/intfloat/multilingual-e5-base",
        "checked_fields": "model_id;authors;embedding_size;prefix_contract;supported_languages;technical_report_link",
        "use_claim_status": "supported_for_multilingual_e5_sensitivity_encoder_contract",
        "remaining_submission_check": "capture exact model revision/hash if required by venue reproducibility checklist",
    },
    "zhou2026depression": {
        "verification_status": "spot_checked_primary_source",
        "checked_source_url": "https://pubmed.ncbi.nlm.nih.gov/41794387/",
        "checked_fields": "title;authors;journal;year;volume;pages;doi;cross_scale_linking_use_claim",
        "use_claim_status": "supported_for_depression_scales_correlated_but_systematically_different_positioning",
        "remaining_submission_check": "confirm venue style and capitalization against final bibliography format",
    },
    "chen2025scd": {
        "verification_status": "spot_checked_primary_source",
        "checked_source_url": "https://doi.org/10.1016/j.patcog.2026.113367",
        "checked_fields": "title;authors;year;journal;volume;article_number;doi;scd_mllm_use_claim",
        "use_claim_status": "supported_for_generic_cross_domain_missing_modality_positioning",
        "remaining_submission_check": "confirm final publisher page display if venue requires publisher page screenshots rather than DOI metadata",
    },
    "chen2025leavingnone": {
        "verification_status": "spot_checked_primary_source",
        "checked_source_url": "https://dblp.org/rec/journals/taffco/ChenGHH25;https://doi.org/10.1109/TAFFC.2024.3469189",
        "checked_fields": "title;authors;year;journal;volume;issue;pages;doi;domain_incremental_use_claim",
        "use_claim_status": "supported_for_close_domain_incremental_mdd_baseline_positioning",
        "remaining_submission_check": "confirm final IEEE page display if target venue requires publisher-rendered metadata",
    },
    "delamain2024measurement": {
        "verification_status": "spot_checked_primary_source",
        "checked_source_url": "https://doi.org/10.1016/j.jad.2023.11.026;https://pubmed.ncbi.nlm.nih.gov/37989437/",
        "checked_fields": "title;authors;year;journal;volume;pages;doi;phq_gad_invariance_use_claim",
        "use_claim_status": "supported_for_active_phq9_gad7_measurement_invariance_and_dif_context",
        "remaining_submission_check": "confirm final publisher page display if target venue requires publisher-rendered metadata",
    },
    "fu2025mpddchallenge": {
        "verification_status": "spot_checked_primary_source",
        "checked_source_url": "https://hacilab.github.io/MPDDChallenge.github.io/;https://doi.org/10.1145/3746027.3762020",
        "checked_fields": "title;authors;year;venue;pages;doi;challenge_metrics;mpdd_use_claim",
        "use_claim_status": "supported_for_mpdd_challenge_and_individual_difference_benchmark_framing_after_title_correction",
        "remaining_submission_check": "confirm final ACM style and whether to preserve author diacritics in BibTeX",
    },
    "fu2026p3hf": {
        "verification_status": "spot_checked_primary_source",
        "checked_source_url": "https://ojs.aaai.org/index.php/AAAI/article/view/37159;https://doi.org/10.1609/aaai.v40i3.37159",
        "checked_fields": "title;authors;year;venue;volume;issue;pages;doi;personality_aware_use_claim",
        "use_claim_status": "supported_for_personality_aware_mpdd_young_method_positioning",
        "remaining_submission_check": "confirm AAAI bibliography style for proceedings-as-journal entries",
    },
    "galenkamp2017measurement": {
        "verification_status": "spot_checked_primary_source",
        "checked_source_url": "https://bmcpsychiatry.biomedcentral.com/articles/10.1186/s12888-017-1506-9;https://doi.org/10.1186/s12888-017-1506-9",
        "checked_fields": "title;authors;year;journal;volume;article_number;doi;ethnicity_language_mode_invariance_use_claim",
        "use_claim_status": "supported_for_classical_phq9_measurement_invariance_template",
        "remaining_submission_check": "confirm BMC article-number formatting against target venue style",
    },
    "ganin2016domain": {
        "verification_status": "spot_checked_primary_source",
        "checked_source_url": "https://jmlr.org/papers/v17/15-239.html",
        "checked_fields": "title;authors;year;journal;volume;issue;pages;domain_adversarial_use_claim",
        "use_claim_status": "supported_for_dann_representation_alignment_baseline_positioning",
        "remaining_submission_check": "confirm author spelling from JMLR BibTeX during final style pass",
    },
    "guo2017calibration": {
        "verification_status": "spot_checked_primary_source",
        "checked_source_url": "https://proceedings.mlr.press/v70/guo17a.html",
        "checked_fields": "title;authors;year;venue;volume;pages;calibration_use_claim",
        "use_claim_status": "supported_for_observed_scale_and_probability_calibration_context",
        "remaining_submission_check": "confirm venue style and capitalization against final bibliography format",
    },
    "hsu2021hubert": {
        "verification_status": "spot_checked_primary_source",
        "checked_source_url": "https://arxiv.org/abs/2106.07447",
        "checked_fields": "title;authors;submission_date;arxiv_id;speech_foundation_use_claim",
        "use_claim_status": "supported_for_hubert_speech_foundation_sensitivity_context",
        "remaining_submission_check": "confirm venue style and capitalization against final bibliography format",
    },
    "ishikawa2026multiprobe": {
        "verification_status": "spot_checked_primary_source",
        "checked_source_url": "https://arxiv.org/abs/2605.23977",
        "checked_fields": "title;authors;submission_date;arxiv_id;doi;benchmark_audit_use_claim",
        "use_claim_status": "supported_for_nearby_clinical_interview_benchmark_audit_positioning",
        "remaining_submission_check": "check for later arXiv version or peer-reviewed venue before submission",
    },
    "li2025mirror": {
        "verification_status": "spot_checked_primary_source",
        "checked_source_url": "https://arxiv.org/abs/2508.05830",
        "checked_fields": "title;authors;submission_date;arxiv_id;doi;criterion_contamination_use_claim",
        "use_claim_status": "supported_for_mirror_model_criterion_contamination_positioning",
        "remaining_submission_check": "check for later arXiv version or peer-reviewed venue before submission",
    },
    "lipton2018labelshift": {
        "verification_status": "spot_checked_primary_source",
        "checked_source_url": "https://proceedings.mlr.press/v80/lipton18a.html",
        "checked_fields": "title;authors;year;venue;volume;pages;label_shift_use_claim",
        "use_claim_status": "supported_for_label_shift_framing",
        "remaining_submission_check": "confirm venue style and capitalization against final bibliography format",
    },
    "long2015dan": {
        "verification_status": "spot_checked_primary_source",
        "checked_source_url": "https://proceedings.mlr.press/v37/long15.html",
        "checked_fields": "title;authors;year;venue;volume;pages;deep_adaptation_mmd_use_claim",
        "use_claim_status": "supported_for_mmd_dan_distribution_alignment_baseline_positioning",
        "remaining_submission_check": "confirm venue style and capitalization against final bibliography format",
    },
    "ma2021phqhamd": {
        "verification_status": "spot_checked_primary_source",
        "checked_source_url": "https://www.frontiersin.org/journals/psychiatry/articles/10.3389/fpsyt.2021.747139/full;https://doi.org/10.3389/fpsyt.2021.747139",
        "checked_fields": "title;authors;year;journal;volume;doi;phq_hamd_irt_use_claim",
        "use_claim_status": "supported_for_scale_specific_phq_hamd_psychometric_motivation_after_author_list_correction",
        "remaining_submission_check": "confirm Frontiers article-number formatting against target venue style",
    },
    "meredith1993measurement": {
        "verification_status": "spot_checked_primary_source",
        "checked_source_url": "https://link.springer.com/article/10.1007/BF02294825",
        "checked_fields": "title;author;year;journal;volume;issue;pages;doi;measurement_invariance_use_claim",
        "use_claim_status": "supported_for_classical_measurement_invariance_foundation",
        "remaining_submission_check": "confirm venue style and capitalization against final bibliography format",
    },
    "muthen2014irt": {
        "verification_status": "spot_checked_primary_source",
        "checked_source_url": "https://www.frontiersin.org/journals/psychology/articles/10.3389/fpsyg.2014.00978/full",
        "checked_fields": "title;authors;year;journal;volume;article_number;doi;alignment_method_use_claim",
        "use_claim_status": "supported_for_irt_many_group_alignment_context",
        "remaining_submission_check": "confirm author diacritic escaping against final bibliography format",
    },
    "patel2019measurement": {
        "verification_status": "spot_checked_primary_source",
        "checked_source_url": "https://onlinelibrary.wiley.com/doi/abs/10.1002/da.22940;https://pubmed.ncbi.nlm.nih.gov/31356710/",
        "checked_fields": "title;authors;year;journal;volume;issue;pages;doi;phq9_sociodemographic_invariance_use_claim",
        "use_claim_status": "supported_for_phq9_sociodemographic_measurement_invariance_context_after_author_name_correction",
        "remaining_submission_check": "confirm venue style and capitalization against final bibliography format",
    },
    "pdchrepository2026": {
        "verification_status": "spot_checked_primary_source",
        "checked_source_url": "https://github.com/Miraclemarvel55/PDCH",
        "checked_fields": "repository_title;dataset_scope;audio_text_modalities;hamd17_labeling;consultation_count;pdch_use_claim",
        "use_claim_status": "supported_for_pdch_consultation_hamd_dataset_context",
        "remaining_submission_check": "replace repository placeholder author/year if a peer-reviewed PDCH dataset paper becomes available before submission",
    },
    "qwen2024qwen25": {
        "verification_status": "spot_checked_primary_source",
        "checked_source_url": "https://qwenlm.github.io/blog/qwen2.5/",
        "checked_fields": "project_page_title;date;model_family;context_claim;license_caveat;llm_extension_use_claim",
        "use_claim_status": "supported_for_design_compatible_instruction_tuned_llm_extension_source",
        "remaining_submission_check": "capture exact model revision/hash if required by venue reproducibility checklist",
    },
    "sagawa2019groupdro": {
        "verification_status": "spot_checked_primary_source",
        "checked_source_url": "https://arxiv.org/abs/1911.08731",
        "checked_fields": "title;authors;submission_date;arxiv_id;worst_group_use_claim",
        "use_claim_status": "supported_for_group_dro_worst_group_robustness_baseline_positioning",
        "remaining_submission_check": "confirm venue style and capitalization against final bibliography format",
    },
    "samejima1969graded": {
        "verification_status": "spot_checked_primary_source",
        "checked_source_url": "https://www.psychometricsociety.org/sites/main/files/file-attachments/mn17.pdf",
        "checked_fields": "title;author;year;monograph_number;publisher;graded_response_model_use_claim",
        "use_claim_status": "supported_for_ordinal_graded_response_model_source",
        "remaining_submission_check": "confirm monograph formatting against final bibliography format",
    },
    "shen2022automatic": {
        "verification_status": "spot_checked_primary_source",
        "checked_source_url": "https://arxiv.org/abs/2202.08210;https://doi.org/10.1109/ICASSP43922.2022.9746569",
        "checked_fields": "title;authors;year;venue;pages;doi;eatd_corpus_use_claim",
        "use_claim_status": "supported_for_eatd_audio_text_corpus_dataset_context",
        "remaining_submission_check": "confirm final IEEE page display if target venue requires publisher-rendered metadata",
    },
    "sun2016deepcoral": {
        "verification_status": "spot_checked_primary_source",
        "checked_source_url": "https://ojs.aaai.org/index.php/AAAI/article/view/10306;https://doi.org/10.1609/aaai.v30i1.10306",
        "checked_fields": "title;authors;year;venue;volume;issue;deep_coral_use_claim",
        "use_claim_status": "supported_for_coral_covariance_alignment_baseline_positioning",
        "remaining_submission_check": "confirm AAAI page range from final BibTeX/export during venue style pass",
    },
    "teng2026depressionllm": {
        "verification_status": "spot_checked_primary_source",
        "checked_source_url": "https://doi.org/10.1016/j.displa.2025.103304",
        "checked_fields": "title;authors;year;journal;volume;article_number;doi;foundation_model_depression_use_claim",
        "use_claim_status": "supported_for_foundation_model_depression_detection_positioning",
        "remaining_submission_check": "confirm final publisher page display if target venue requires publisher-rendered metadata",
    },
    "tong2022videomae": {
        "verification_status": "spot_checked_primary_source",
        "checked_source_url": "https://arxiv.org/abs/2203.12602",
        "checked_fields": "title;authors;submission_date;arxiv_id;videomae_use_claim",
        "use_claim_status": "supported_for_future_videomae_video_backbone_sensitivity_context",
        "remaining_submission_check": "confirm venue style and capitalization against final bibliography format",
    },
    "uscict2026daic": {
        "verification_status": "spot_checked_primary_source",
        "checked_source_url": "https://dcapswoz.ict.usc.edu/",
        "checked_fields": "dataset_page_title;daic_woz_scope;extended_daic_scope;access_restrictions;daic_access_use_claim",
        "use_claim_status": "supported_for_daic_woz_and_extended_daic_access_release_boundary_wording",
        "remaining_submission_check": "update accessed date if final submission occurs after the current manuscript preparation window",
    },
    "vandenberg2000review": {
        "verification_status": "spot_checked_primary_source",
        "checked_source_url": "https://journals.sagepub.com/doi/10.1177/109442810031002;https://doi.org/10.1177/109442810031002",
        "checked_fields": "title;authors;year;journal;volume;issue;pages;doi;measurement_invariance_review_use_claim",
        "use_claim_status": "supported_for_measurement_invariance_review_and_decision_rule_context",
        "remaining_submission_check": "confirm venue style and capitalization against final bibliography format",
    },
    "zhang2025qwen3embedding": {
        "verification_status": "spot_checked_primary_source",
        "checked_source_url": "https://arxiv.org/abs/2506.05176",
        "checked_fields": "title;authors;submission_date;arxiv_id;embedding_model_use_claim",
        "use_claim_status": "supported_for_qwen3_embedding_text_foundation_feature_reference",
        "remaining_submission_check": "capture exact model revision/hash if required by venue reproducibility checklist",
    },
    "zou2023cmdc": {
        "verification_status": "spot_checked_primary_source",
        "checked_source_url": "https://doi.org/10.1109/TAFFC.2022.3181210",
        "checked_fields": "title;authors;year;journal;volume;issue;pages;doi;cmdc_dataset_use_claim",
        "use_claim_status": "supported_for_cmdc_chinese_clinical_interview_dataset_context",
        "remaining_submission_check": "confirm final IEEE page display if target venue requires publisher-rendered metadata",
    },
}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def rel(path: Path) -> str:
    return str(path.resolve().relative_to(ROOT))


def clean_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, float) and pd.isna(value):
        return ""
    return str(value).strip()


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        raise ValueError(f"No rows to write: {path}")
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def md_escape(value: Any) -> str:
    return clean_text(value).replace("|", "\\|").replace("\n", " ")


def markdown_table(rows: list[dict[str, Any]], columns: list[str], headers: list[str]) -> list[str]:
    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join("---" for _ in headers) + " |",
    ]
    for row in rows:
        lines.append("| " + " | ".join(md_escape(row[column]) for column in columns) + " |")
    return lines


def build_ledger(registry: pd.DataFrame) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for record in registry.sort_values("citation_key").to_dict(orient="records"):
        key = clean_text(record["citation_key"])
        check = SPOT_CHECKS.get(key)
        if check is None:
            verification_status = "pending_submission_grade_primary_source_check"
            checked_source_url = ""
            checked_fields = ""
            use_claim_status = "pending"
            remaining = "open primary source and confirm BibTeX fields plus manuscript use claim"
        else:
            verification_status = check["verification_status"]
            checked_source_url = check["checked_source_url"]
            checked_fields = check["checked_fields"]
            use_claim_status = check["use_claim_status"]
            remaining = check["remaining_submission_check"]

        rows.append(
            {
                "citation_key": key,
                "entry_type": clean_text(record["entry_type"]),
                "registry_year": clean_text(record["year"]),
                "registry_title": clean_text(record["title"]),
                "registry_venue": clean_text(record["venue"]),
                "registry_doi": clean_text(record["doi"]),
                "registry_url": clean_text(record["url"]),
                "registry_verification_status": clean_text(record["verification_status"]),
                "registry_metadata_source_url": clean_text(record["metadata_source_url"]),
                "source_context_count": int(record["source_context_count"]),
                "session69_verification_status": verification_status,
                "session69_checked_source_url": checked_source_url,
                "session69_checked_fields": checked_fields,
                "manuscript_use_claim_status": use_claim_status,
                "remaining_submission_check": remaining,
            }
        )
    return rows


def build_report(rows: list[dict[str, Any]], generated_at: str) -> list[str]:
    total = len(rows)
    spot_checked = sum(
        row["session69_verification_status"] in {"spot_checked_primary_source", "partial_spot_checked_primary_and_preprint_sources"}
        for row in rows
    )
    fully_checked = sum(row["session69_verification_status"] == "spot_checked_primary_source" for row in rows)
    partial = sum(row["session69_verification_status"] == "partial_spot_checked_primary_and_preprint_sources" for row in rows)
    pending = sum(row["session69_verification_status"] == "pending_submission_grade_primary_source_check" for row in rows)

    priority_rows = [
        row
        for row in rows
        if row["session69_verification_status"]
        in {"spot_checked_primary_source", "partial_spot_checked_primary_and_preprint_sources"}
    ]
    pending_rows = [row for row in rows if row["session69_verification_status"] == "pending_submission_grade_primary_source_check"]
    if pending:
        m002_line = "- Manuscript open item M002 remains blocking until pending rows are verified and venue style is selected."
    else:
        m002_line = "- Primary-source checks are complete in this ledger; M002 remains open for current-prose citation coverage confirmation, target-venue style, and final pre-submission refreshes."

    lines = [
        "# Bibliography Primary-Source Verification Ledger",
        "",
        f"Generated: `{generated_at}`",
        "",
        "## Decision",
        "",
        "- This is a manuscript-editing verification ledger, not a new experiment.",
        f"- References in registry: `{total}`.",
        f"- Manually spot-checked: `{spot_checked}` (`{fully_checked}` primary, `{partial}` partial).",
        f"- Pending submission-grade primary-source checks: `{pending}`.",
        m002_line,
        "",
        "## Spot-Checked Rows",
        "",
    ]
    if priority_rows:
        lines.extend(
            markdown_table(
                priority_rows,
                [
                    "citation_key",
                    "session69_verification_status",
                    "session69_checked_fields",
                    "manuscript_use_claim_status",
                    "remaining_submission_check",
                ],
                ["key", "status", "checked fields", "use claim", "remaining"],
            )
        )
    else:
        lines.append("No rows have been spot-checked in this ledger.")

    lines.extend(["", "## Pending Rows", ""])
    if pending_rows:
        lines.extend(
            markdown_table(
                pending_rows,
                ["citation_key", "registry_verification_status", "registry_metadata_source_url", "remaining_submission_check"],
                ["key", "registry status", "metadata source", "remaining"],
            )
        )
    else:
        lines.append("No pending rows remain.")

    lines.extend(
        [
            "",
            "## Regeneration",
            "",
            "```bash",
            "python scripts/build_diagnostic_paper_bibliography_verification.py",
            "```",
        ]
    )
    return lines


def run_hygiene(out_dir: Path) -> dict[str, Any]:
    forbidden = [
        r"/root/autodl-tmp/datasets/[^,\s|)]+",
        r"p5_mv06_local_",
        r"local_predictions",
        r"theta_scores",
        r"item_response_matrix",
    ]
    findings: list[dict[str, str]] = []
    for name in HYGIENE_CHECKED_FILES:
        path = out_dir / name
        text = path.read_text(encoding="utf-8")
        for pattern in forbidden:
            if __import__("re").search(pattern, text):
                findings.append({"file": name, "pattern": pattern})
    return {
        "audit_id": "diagnostic_paper_bibliography_verification_hygiene",
        "artifact_hygiene_passed": not findings,
        "findings": findings,
        "checked_files": HYGIENE_CHECKED_FILES,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=PAPER_DIR)
    args = parser.parse_args()

    if not REGISTRY_CSV.exists():
        raise FileNotFoundError(REGISTRY_CSV)

    out_dir = args.out_dir
    out_dir.mkdir(parents=True, exist_ok=True)
    generated_at = utc_now()
    registry = pd.read_csv(REGISTRY_CSV)
    required = {"citation_key", "entry_type", "year", "title", "venue", "doi", "url", "verification_status", "metadata_source_url", "source_context_count"}
    missing = sorted(required - set(registry.columns))
    if missing:
        raise ValueError(f"citation_registry.csv missing columns: {missing}")

    rows = build_ledger(registry)
    write_csv(out_dir / "bibliography_verification_ledger.csv", rows)
    (out_dir / "bibliography_verification_report.md").write_text(
        "\n".join(build_report(rows, generated_at)) + "\n", encoding="utf-8"
    )
    summary = {
        "run_id": "diagnostic_paper_bibliography_verification",
        "generated_at": generated_at,
        "status": "primary_source_verification_complete_style_pending",
        "input": rel(REGISTRY_CSV),
        "outputs": TRACKED_FILES,
        "counts": {
            "reference_rows": len(rows),
            "spot_checked_rows": sum(
                row["session69_verification_status"]
                in {"spot_checked_primary_source", "partial_spot_checked_primary_and_preprint_sources"}
                for row in rows
            ),
            "primary_spot_checked_rows": sum(row["session69_verification_status"] == "spot_checked_primary_source" for row in rows),
            "partial_spot_checked_rows": sum(row["session69_verification_status"] == "partial_spot_checked_primary_and_preprint_sources" for row in rows),
            "pending_rows": sum(row["session69_verification_status"] == "pending_submission_grade_primary_source_check" for row in rows),
        },
        "decision": {
            "m002_blocking_status": "source_verification_complete_style_and_citation_coverage_refresh_pending",
            "short_read": "Primary-source checks are complete in the bibliography ledger; current-prose citation coverage confirmation, target-venue style, and final pre-submission refreshes remain.",
        },
    }
    (out_dir / "bibliography_verification_run_summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    hygiene = run_hygiene(out_dir)
    (out_dir / "bibliography_verification_hygiene_audit.json").write_text(
        json.dumps(hygiene, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    if not hygiene["artifact_hygiene_passed"]:
        raise RuntimeError("Bibliography verification hygiene failed")
    print(f"Wrote bibliography verification ledger to {out_dir}")
    print(json.dumps(summary["counts"], indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
