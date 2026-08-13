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
MV15_DESIGN_SUMMARY = PHASE5_DIR / "p5_mv15_latent_conditioned_identity_design" / "run_summary.json"

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
    "C_MODMA_TASK_CONTROL": "Identity and protocol diagnostics",
    "C_EATD_VALENCE_ADVERSARIAL": "External stress tests",
    "C_RQ3_CONTEXT_CONDITIONING": "Population/context diagnostics",
    "C_RQ4_EVIDENCE_LOCALIZATION": "Evidence localization",
    "C_PUBLISHABLE_PAPER_DIRECTION": "Paper framing",
}

PAPER_CLAIM_LANGUAGE = {
    "C_FULL_METHOD_START": "Do not claim the full M0/M1/M2/M3 method; the evidence currently supports a governed measurement-shift diagnostic paper, with MV15 now predeclared as the next identity audit.",
    "C_RQ1_SHARED_SYMPTOM": "Report direct shared-symptom mapping as negative and reframe RQ1 around measurement validity, target measurement shift, external anchor/DIF replication, the frozen MV12 latent-target diagnostic with dimension-matched caveats, and the predeclared MV15 identity gate.",
    "C_PSYCHOMETRIC_INVARIANCE_BASELINE": "Use MV10/MV11/MV13/MV14 as label-only PHQ common-structure, stable-anchor, sparse-loading-DIF, and localized-threshold-shift evidence with explicit AIC/BIC and convergence caveats, not as bootstrap-confirmed global partial invariance.",
    "C_PDCH_HAMD_INTERNAL": "Use PDCH HAMD-17 as bounded internal diagnostic evidence, not as cross-dataset HAMD transfer.",
    "C_EATD_SDS_GENERALIZATION": "Report EATD SDS as a negative or weak external stress result.",
    "C_DATASET_IDENTITY_CONTROL": "Report unconditional dataset identity as a shortcut-risk screen and use MV15's latent-conditioned identity ladder as the next shared-latent diagnostic.",
    "C_MODMA_TASK_CONTROL": "Use MODMA task nuisance projection as bounded protocol-control evidence.",
    "C_EATD_VALENCE_ADVERSARIAL": "Do not add or claim an EATD-driven valence-adversarial module from current evidence.",
    "C_RQ3_CONTEXT_CONDITIONING": "Report MPDD context calibration as negative and keep age/personality as later measurement-heterogeneity axes.",
    "C_RQ4_EVIDENCE_LOCALIZATION": "Use MV06 as first-round aggregate evidence-localization credibility evidence only.",
    "C_PUBLISHABLE_PAPER_DIRECTION": "Proceed as a measurement-shift / measurement-validity paper with bounded claims, explicit negative evidence, external psychometric replication, convergence-aware bootstrap uncertainty, the completed two-stage latent-target plus aggregate tradeoff analysis, and MV15's predeclared dimension-matched identity ladder as diagnostic gates.",
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
        "paper_positioning": "Recent interviewer-bias work motivates treating question type and dialogue protocol as nuisance factors, while our audit generalizes this concern across datasets, tasks, valence, and scale contracts.",
    },
    {
        "source_id": "multi_probe_audit_2026",
        "topic": "Nearby benchmark audit risk",
        "citation_hint": "Ishikawa and Duke 2026, arXiv",
        "url": "https://arxiv.org/abs/2605.23977",
        "paper_positioning": "A recent multi-probe depression benchmark audit overlaps several datasets, so our novelty should emphasize measurement shift, conditional identity, and measurement validity rather than a generic dataset audit alone.",
    },
    {
        "source_id": "questionnaire_grounding_acl_2022",
        "topic": "Questionnaire grounding and OOD depression detection",
        "citation_hint": "Nguyen et al. 2022, ACL",
        "url": "https://aclanthology.org/2022.acl-long.578/",
        "paper_positioning": "Questionnaire-grounded symptom modeling is prior positive evidence for symptom-aware OOD detection; our paper should position its contribution as measuring when cross-dataset symptom targets are not equivalent.",
    },
    {
        "source_id": "phq_hamd_irt_2021",
        "topic": "PHQ/HAMD measurement differences",
        "citation_hint": "Ma et al. 2021, Frontiers in Psychiatry",
        "url": "https://www.frontiersin.org/journals/psychiatry/articles/10.3389/fpsyt.2021.747139/full",
        "paper_positioning": "PHQ-9 and HAMD-17 can correlate strongly while differing in item discrimination and severity assessment, supporting our scale-specific measurement framing.",
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
        "source_id": "irt_lr_dif_frontiers_2017",
        "topic": "IRT likelihood-ratio DIF testing",
        "citation_hint": "Jeong and Lee 2017, Frontiers in Education",
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
        MV15_DESIGN_SUMMARY,
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


def build_metric_context() -> dict[str, str]:
    gate = read_json(FULL_GATE_SUMMARY)
    mv02 = read_json(MV02_SUMMARY)
    mv04c = read_json(MV04C_SUMMARY)
    mv06 = read_json(MV06_SUMMARY)
    agreement = pd.read_csv(MV06_AGREEMENT)
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
    mv15_design = read_json(MV15_DESIGN_SUMMARY)

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
    mv15_d = mv15_design["decision"]
    all_kappa, all_pairs = evidence_presence_kappa(agreement, "ALL")
    cmdc_kappa, cmdc_pairs = evidence_presence_kappa(agreement, "cmdc")
    edaic_kappa, edaic_pairs = evidence_presence_kappa(agreement, "edaic")
    pdch_kappa, pdch_pairs = evidence_presence_kappa(agreement, "pdch")
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
            f"{mv14_v['dif_min_anchor_effective_draws']}, stable anchors "
            f"{';'.join(mv14_v['stable_anchor_items'])}, top threshold-DIF items "
            f"{';'.join(mv14_v['top_threshold_dif_items'])}, and best AIC/BIC "
            f"{mv14_v['best_aic_model']}/{mv14_v['best_bic_model']} with stable-ladder "
            f"{mv14_v['stable_ladder_best_aic_model']}/{mv14_v['stable_ladder_best_bic_model']}. "
            f"MV12 design is {mv12_d['readiness_status']}; MV12 run is {mv12_v['pass_rule_status']}, "
            f"with same-dataset theta gate {mv12_v['same_dataset_theta_gate_passed']}, observed-scale safety "
            f"{mv12_v['same_dataset_observed_gate_passed']}, external theta transfer "
            f"{mv12_v['external_transfer_theta_gate_passed']}, and conditional identity BA "
            f"{fmt(mv12_v['conditional_identity_ba_m12a'])}. "
            f"MV12 aggregate tradeoff analysis is {mv12_a['analysis_status']} and recommends freezing "
            f"the current latent-target line; {mv12_a['dimension_matched_identity_caveat']}"
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
            f"parameter CI status {mv13_v['parameter_ci_status']}."
        ),
        "mv14": (
            f"MV14 bootstrap uncertainty: status {mv14_v['status']}; requested smoke/core/DIF R "
            f"{mv14_v['requested_smoke_R']}/{mv14_v['requested_core_R']}/{mv14_v['requested_dif_R']}; "
            f"convergence-safe full-ladder effective R {mv14_v['core_effective_draws']}/"
            f"{mv14_v['core_selection_attempted_draws']} after fit-success R "
            f"{mv14_v['core_all_fit_success_draws']}; configural converged R "
            f"{mv14_v['configural_converged_draws']}/{mv14_v['core_selection_attempted_draws']}; "
            f"stable-ladder effective R {mv14_v['stable_ladder_effective_draws']}; DIF effective R "
            f"{mv14_v['dif_min_anchor_effective_draws']}; stable anchors "
            f"{';'.join(mv14_v['stable_anchor_items'])}; top threshold-DIF items "
            f"{';'.join(mv14_v['top_threshold_dif_items'])}; best AIC/BIC models "
            f"{mv14_v['best_aic_model']}/{mv14_v['best_bic_model']}; stable-ladder AIC/BIC "
            f"{mv14_v['stable_ladder_best_aic_model']}/{mv14_v['stable_ladder_best_bic_model']}."
        ),
        "mv12_design": (
            f"MV12 two-stage latent-target design: status {mv12_d['readiness_status']}; "
            f"full_method_allowed={mv12_d['full_method_allowed']}; "
            f"outputs predeclare {mv12_design['outputs']['model_ladder_rows']} model-ladder rows, "
            f"{mv12_design['outputs']['identity_transfer_gate_rows']} identity/transfer gates, and "
            f"{mv12_design['outputs']['pass_fail_gate_rows']} pass/fail gates."
        ),
        "mv12_run": (
            f"MV12 two-stage latent-target run: status {mv12_v['pass_rule_status']}; "
            f"E-DAIC same-dataset theta delta vs train mean {fmt(mv12_v['m12a_edaic_delta_theta_mae_vs_B0'])}; "
            f"CMDC same-dataset theta delta {fmt(mv12_v['m12a_cmdc_delta_theta_mae_vs_B0'])}; "
            f"E-DAIC observed macro delta vs direct itemwise {fmt(mv12_v['m12a_edaic_delta_observed_macro_mae_vs_B3'])}; "
            f"CMDC observed macro delta {fmt(mv12_v['m12a_cmdc_delta_observed_macro_mae_vs_B3'])}; "
            f"conditional identity BA {fmt(mv12_v['conditional_identity_ba_m12a'])}; "
            f"external theta transfer pass={mv12_v['external_transfer_theta_gate_passed']}; "
            f"source-calibrated external theta transfer should be interpreted with measurement-function mismatch."
        ),
        "mv12_analysis": (
            f"MV12 aggregate tradeoff analysis: status {mv12_a['analysis_status']}; "
            f"freeze_current_latent_target_line={mv12_a['freeze_current_latent_target_line']}; "
            f"tradeoff_rows={mv12_analysis['outputs']['tradeoff_rows']}; "
            f"failure_mode_rows={mv12_analysis['outputs']['failure_mode_rows']}; "
            f"{mv12_a['dimension_matched_identity_caveat']}"
        ),
        "mv15_design": (
            f"MV15 latent-conditioned identity design: status {mv15_d['design_status']}; "
            f"primary scope {mv15_d['primary_scope']}; "
            f"conditioning ladder rows {mv15_design['outputs']['conditioning_ladder_rows']}; "
            f"identity probe rows {mv15_design['outputs']['identity_probe_rows']}; "
            f"pass/fail gates {mv15_design['outputs']['pass_fail_gate_rows']}; "
            f"full_method_allowed={mv15_d['full_method_allowed']}."
        ),
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
            f"ALL {all_kappa} ({all_pairs} pairs), CMDC {cmdc_kappa} ({cmdc_pairs}), "
            f"PDCH {pdch_kappa} ({pdch_pairs}), E-DAIC {edaic_kappa} ({edaic_pairs})."
            f"{mv06_remaining_clause} Field-specific degenerate marginal statuses should be read from agreement_summary.csv."
        ),
    }


def claim_evidence_sentence(claim_id: str, context: dict[str, str], row: pd.Series) -> str:
    if claim_id in {"C_FULL_METHOD_START", "C_PUBLISHABLE_PAPER_DIRECTION"}:
        return f"{context['gate']} {context['mv10']} {context['mv11']} {context['mv13']} {context['mv14']} {context['mv12_design']} {context['mv12_run']} {context['mv12_analysis']} {context['mv15_design']}"
    if claim_id == "C_RQ1_SHARED_SYMPTOM":
        return f"{context['rq1']} {context['mv12_analysis']} {context['mv15_design']}"
    if claim_id == "C_PSYCHOMETRIC_INVARIANCE_BASELINE":
        return f"{context['mv10']} {context['mv11']} {context['mv13']} {context['mv14']} {context['mv12_design']} {context['mv12_run']} {context['mv12_analysis']}"
    if claim_id == "C_PDCH_HAMD_INTERNAL":
        return context["pdch"]
    if claim_id in {"C_EATD_SDS_GENERALIZATION", "C_EATD_VALENCE_ADVERSARIAL"}:
        return context["eatd"]
    if claim_id == "C_DATASET_IDENTITY_CONTROL":
        return f"{context['mv09']} {context['mv15_design']}"
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
                "source_artifact_ids": row["primary_sources"],
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
            "interpretation": "Measurement screens and residual measurement heads are diagnostic under current features; MV10/MV11/MV13/MV14/MV12 shift RQ1 to measurement-target validity and freeze the current latent-target line.",
            "source_artifact_ids": "P5_MV08;P5_MV08b;P5_MV09;P5_MV10;P5_MV11;P5_MV13;P5_MV14;P5_MV12;P5_MV12_analysis",
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
            "interpretation": "The external R mirt replication preserves the MV11 qualitative anchor/DIF pattern; MV14 now supplies the bootstrap uncertainty layer needed for cautious item-level wording.",
            "source_artifact_ids": "P5_MV13",
        },
        {
            "finding_id": "mv14_measurement_uncertainty_bootstrap",
            "paper_section": "Psychometric baseline",
            "finding": context["mv14"],
            "interpretation": "The convergence-safe bootstrap supports item-level wording: the four MV10 anchors are stable, loading DIF is sparse, and threshold DIF remains concentrated on C02/C06, while global invariance-model selection remains uncertain.",
            "source_artifact_ids": "P5_MV14",
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
            "interpretation": "The actual two-stage run supports a bounded measurement-shift story: the low-dimensional latent/scalar prediction layer reduces identity versus upstream BGE features, but observed-scale safety and zero-shot source-calibrated theta transfer fail.",
            "source_artifact_ids": "P5_MV12",
        },
        {
            "finding_id": "mv12_tradeoff_freeze_decision",
            "paper_section": "Measurement evidence",
            "finding": context["mv12_analysis"],
            "interpretation": "The aggregate tradeoff analysis closes the current latent-target line: M12a is not uniquely more invariant than a dimension-matched B3 severity baseline, so MV15 must compare total, predicted-total, itemwise-theta, and psychometric-theta controls.",
            "source_artifact_ids": "P5_MV12_analysis",
        },
        {
            "finding_id": "mv15_latent_conditioned_identity_design",
            "paper_section": "Identity and protocol diagnostics",
            "finding": context["mv15_design"],
            "interpretation": "MV15 is now the predeclared identity-gate follow-up: it must compare raw feature identity, observed labels, PHQ total, predicted total, direct-itemwise-theta severity, psychometric theta, covariates, predicted-output identity, and severity-only external sensitivity before any stronger shared-latent wording.",
            "source_artifact_ids": "P5_MV15_design",
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
            "interpretation": "MV06 can support first-round aggregate credibility; stronger RQ4 claims should add agreement uncertainty analysis and resolve any remaining incomplete local candidate rows.",
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
            "- Any stronger RQ4 claim should first add agreement uncertainty analysis and resolve any remaining incomplete local candidate rows.",
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
