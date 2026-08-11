#!/usr/bin/env python3
"""Audit whether Phase 5 evidence is strong enough to start the full method.

This script is an orchestration gate, not a trainer. It reads existing Phase 5
run summaries and emits a claim-level decision table, evidence inventory,
next-action queue, and compact report. The output is meant to stop accidental
scope creep from mixed/negative minimal-validation rows into unsupported full
method claims.
"""

from __future__ import annotations

import argparse
import json
import math
import re
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
PHASE5_DIR = ROOT / "analysis" / "phase5_minimal_validation"
DEFAULT_OUT_DIR = PHASE5_DIR / "full_method_gate_audit"


RUN_SUMMARIES = {
    "P5_MV01": PHASE5_DIR / "p5_mv01_phq_core_bridge" / "run_summary.json",
    "P5_MV02_readiness": PHASE5_DIR / "p5_mv02_hamd_bridge_readiness" / "run_summary.json",
    "P5_MV02": PHASE5_DIR / "p5_mv02_hamd_auxiliary_bridge" / "run_summary.json",
    "P5_MV02b": PHASE5_DIR / "p5_mv02b_pdch_text_semantic_measurement" / "run_summary.json",
    "P5_MV03": PHASE5_DIR / "p5_mv03_sds_total_external_stress" / "run_summary.json",
    "P5_MV03b": PHASE5_DIR / "p5_mv03b_eatd_text_semantic_stress" / "run_summary.json",
    "P5_MV04": PHASE5_DIR / "p5_mv04_dataset_identity_control" / "run_summary.json",
    "P5_MV04b": PHASE5_DIR / "p5_mv04_source_agnostic_identity_projection" / "run_summary.json",
    "P5_MV04c": PHASE5_DIR / "p5_mv04c_protocol_task_valence_control" / "run_summary.json",
    "P5_MV05": PHASE5_DIR / "p5_mv05_mpdd_context_calibration" / "run_summary.json",
    "P5_MV06_readiness": PHASE5_DIR / "p5_mv06_evidence_localization_readiness" / "run_summary.json",
    "P5_MV06_pilot": PHASE5_DIR / "p5_mv06_evidence_annotation_pilot" / "run_summary.json",
    "P5_MV06_workbench": PHASE5_DIR / "p5_mv06_evidence_annotation_workbench" / "run_summary.json",
    "P5_MV06_summary": PHASE5_DIR / "p5_mv06_evidence_annotation_summary" / "run_summary.json",
    "P5_MV06_ai_preannotation": PHASE5_DIR / "p5_mv06_ai_preannotation_triage" / "run_summary.json",
    "P5_MV06_review_pack": PHASE5_DIR / "p5_mv06_human_review_pack" / "run_summary.json",
    "P5_MV07_edaic_bge_generation": PHASE5_DIR / "p5_mv07_edaic_bge_generation" / "run_summary.json",
    "P5_MV07_readiness": PHASE5_DIR / "p5_mv07_shared_feature_contract_readiness" / "run_summary.json",
    "P5_MV07": PHASE5_DIR / "p5_mv07_aligned_bge_shared_symptom" / "run_summary.json",
    "P5_MV07b": PHASE5_DIR / "p5_mv07b_bge_identity_projection" / "run_summary.json",
    "P5_MV07c": PHASE5_DIR / "p5_mv07c_bge_total_anchor" / "run_summary.json",
    "P5_MV08_design": PHASE5_DIR / "p5_mv08_partial_invariance_measurement_design" / "run_summary.json",
    "P5_MV08": PHASE5_DIR / "p5_mv08_partial_invariance_measurement" / "run_summary.json",
    "P5_MV08_error_analysis": PHASE5_DIR / "p5_mv08_error_analysis" / "run_summary.json",
    "P5_MV08b_design": PHASE5_DIR / "p5_mv08b_total_anchored_residual_measurement_design" / "run_summary.json",
    "P5_MV08b": PHASE5_DIR / "p5_mv08b_total_anchored_residual_measurement" / "run_summary.json",
    "P5_MV09": PHASE5_DIR / "p5_mv09_conditional_identity_audit" / "run_summary.json",
}

STATUS_OVERRIDES = {
    "P5_MV01": "complete_diagnostic_weak_asymmetric",
    "P5_MV02_readiness": "ready_pdch_only_mode",
    "P5_MV06_readiness": "ready_for_local_evidence_annotation",
    "P5_MV06_pilot": "ready_for_manual_local_annotation",
    "P5_MV06_workbench": "ready_for_local_human_annotation",
    "P5_MV06_ai_preannotation": "ready_for_human_review_not_claimable",
    "P5_MV06_review_pack": "ready_for_human_review_pack_not_claimable",
}

PASS_RULE_OVERRIDES = {
    "P5_MV01": False,
    "P5_MV02_readiness": None,
    "P5_MV06_readiness": None,
    "P5_MV06_pilot": None,
    "P5_MV06_workbench": None,
    "P5_MV06_ai_preannotation": False,
    "P5_MV06_review_pack": False,
}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT))
    except ValueError:
        return str(path)


def read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(path)
    return json.loads(path.read_text(encoding="utf-8"))


def safe_float(value: Any) -> float | None:
    try:
        out = float(value)
    except (TypeError, ValueError):
        return None
    return out if math.isfinite(out) else None


def fmt(value: Any, digits: int = 3) -> str:
    numeric = safe_float(value)
    if numeric is None:
        return "NA"
    return f"{numeric:.{digits}f}"


def public_text(value: Any) -> str:
    text = "" if value is None else str(value)
    return text.replace("raw snippets", "verbatim excerpts").replace("raw snippet", "verbatim excerpt")


def hygiene_passed(summary: dict[str, Any]) -> bool:
    if "artifact_hygiene" in summary:
        return bool(summary["artifact_hygiene"].get("artifact_hygiene_passed"))
    if "artifact_hygiene_passed" in summary:
        return bool(summary.get("artifact_hygiene_passed"))
    return False


def hygiene_violation_count(summary: dict[str, Any]) -> int | None:
    if "artifact_hygiene" in summary:
        value = summary["artifact_hygiene"].get("violation_count")
        return int(value) if value is not None else None
    if "artifact_hygiene_violation_count" in summary:
        return int(summary["artifact_hygiene_violation_count"])
    return None


def verdict_status(evidence_id: str, summary: dict[str, Any]) -> str:
    if evidence_id in STATUS_OVERRIDES:
        return STATUS_OVERRIDES[evidence_id]
    verdict = summary.get("verdict") or {}
    decision = summary.get("decision") or {}
    if decision.get("annotation_summary_status"):
        return str(decision["annotation_summary_status"])
    if decision.get("readiness_status"):
        return str(decision["readiness_status"])
    if decision.get("error_analysis_status"):
        return str(decision["error_analysis_status"])
    return str(verdict.get("pass_rule_status") or summary.get("status") or "unknown")


def verdict_met(evidence_id: str, summary: dict[str, Any]) -> bool | None:
    if evidence_id in PASS_RULE_OVERRIDES:
        return PASS_RULE_OVERRIDES[evidence_id]
    if evidence_id == "P5_MV06_summary":
        decision = summary.get("decision") or {}
        return decision.get("annotation_summary_status") == "ready_for_aggregate_evidence_review"
    verdict = summary.get("verdict") or {}
    if "pass_rule_met" in verdict:
        return bool(verdict["pass_rule_met"])
    if "pass_rule_status" in verdict:
        status = str(verdict["pass_rule_status"])
        if status.startswith("pass_"):
            return True
        if status.startswith("blocked_"):
            return False
    return None


def short_read(summary: dict[str, Any]) -> str:
    verdict = summary.get("verdict") or {}
    if verdict.get("short_read"):
        return public_text(verdict["short_read"])
    decision = summary.get("decision") or {}
    if decision.get("short_read"):
        return public_text(decision["short_read"])
    interpretation = summary.get("interpretation") or {}
    if interpretation.get("short_read"):
        return public_text(interpretation["short_read"])
    return public_text(summary.get("status") or "")


def local_only_files(summary: dict[str, Any]) -> list[str]:
    files = summary.get("local_only_files")
    if files is None:
        output_policy = summary.get("output_policy") or {}
        files = output_policy.get("local_only_files")
    if not files:
        return []
    return [str(file) for file in files]


def collect_evidence(summaries: dict[str, dict[str, Any]]) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for evidence_id, path in RUN_SUMMARIES.items():
        summary = summaries[evidence_id]
        rows.append(
            {
                "evidence_id": evidence_id,
                "artifact": rel(path),
                "status": str(summary.get("status") or "unknown"),
                "pass_rule_status": verdict_status(evidence_id, summary),
                "pass_rule_met": verdict_met(evidence_id, summary),
                "artifact_hygiene_passed": hygiene_passed(summary),
                "artifact_hygiene_violation_count": hygiene_violation_count(summary),
                "local_only_files": ";".join(local_only_files(summary)),
                "short_read": short_read(summary),
            }
        )
    return pd.DataFrame(rows)


def mv04c_domain_rows(summary: dict[str, Any]) -> dict[str, dict[str, Any]]:
    verdict = summary.get("verdict") or {}
    rows = verdict.get("domain_verdicts") or []
    return {str(row.get("domain")): row for row in rows if row.get("domain")}


def build_claim_gate(summaries: dict[str, dict[str, Any]]) -> pd.DataFrame:
    mv02 = summaries["P5_MV02"].get("verdict") or {}
    mv03 = summaries["P5_MV03"].get("verdict") or {}
    mv03b = summaries["P5_MV03b"].get("verdict") or {}
    mv04 = summaries["P5_MV04"].get("verdict") or {}
    mv04b = summaries["P5_MV04b"].get("verdict") or {}
    mv04c = summaries["P5_MV04c"].get("verdict") or {}
    mv04c_domains = mv04c_domain_rows(summaries["P5_MV04c"])
    mv05 = summaries["P5_MV05"].get("verdict") or {}
    mv06 = summaries["P5_MV06_summary"]
    mv06_decision = mv06.get("decision") or {}
    mv06_gate = mv06.get("annotation_gate") or {}
    mv06_status = str(mv06_decision.get("annotation_summary_status", "unknown"))
    mv06_ready = mv06_status == "ready_for_aggregate_evidence_review"
    mv06_pre = summaries["P5_MV06_ai_preannotation"].get("decision") or {}
    mv06_pack = summaries["P5_MV06_review_pack"].get("decision") or {}
    mv07_result = summaries["P5_MV07"].get("verdict") or {}
    mv07b_result = summaries["P5_MV07b"].get("verdict") or {}
    mv07c_result = summaries["P5_MV07c"].get("verdict") or {}
    mv08_design = summaries["P5_MV08_design"]
    mv08_decision = mv08_design.get("decision") or {}
    mv08_design_status = str(mv08_decision.get("readiness_status", "unknown"))
    mv08_result = summaries["P5_MV08"].get("verdict") or {}
    mv08_status = str(mv08_result.get("pass_rule_status", "unknown"))
    mv08_error = summaries["P5_MV08_error_analysis"].get("decision") or {}
    mv08_error_status = str(mv08_error.get("error_analysis_status", "unknown"))
    mv08b_design = summaries["P5_MV08b_design"].get("decision") or {}
    mv08b_design_status = str(mv08b_design.get("readiness_status", "unknown"))
    mv08b_result = summaries["P5_MV08b"].get("verdict") or {}
    mv08b_status = str(mv08b_result.get("pass_rule_status", "unknown"))
    mv09_result = summaries["P5_MV09"].get("verdict") or {}
    mv09_status = str(mv09_result.get("status", "unknown"))

    rows = [
        {
            "claim_id": "C_FULL_METHOD_START",
            "claim": "Start the full symptom-aligned method M0/M1/M2/M3.",
            "decision": "blocked",
            "allowed_scope": "No full method construction yet.",
            "blocking_evidence": f"P5_MV01 weak/asymmetric; P5_MV04b partial; P5_MV04c mixed; P5_MV03/MV03b/MV05 negative; MV06 summary status is {mv06_status}; MV07 aligned-BGE status is {mv07_result.get('pass_rule_status')}; MV07b reduces BGE identity but remains {mv07b_result.get('pass_rule_status')}; MV07c total anchor remains {mv07c_result.get('pass_rule_status')} with CMDC delta vs raw total-allocation {fmt(mv07c_result.get('pooled_cmdc_delta_vs_raw_total_alloc'))}; MV08 design status is {mv08_design_status}; MV08 result is {mv08_status}, with M2 improving over total-score floor on {mv08_result.get('pooled_m2_improved_vs_total_score_floor_slices')} pooled active slices and prediction identity BA {fmt(mv08_result.get('prediction_identity_ba_m2'))}; MV08 error-analysis status is {mv08_error_status}; MV08b design status is {mv08b_design_status}; MV08b result is {mv08b_status}, with M2b beating both floors on {mv08b_result.get('pooled_m2b_improved_vs_both_floor_slices')} pooled active slices and prediction identity BA {fmt(mv08b_result.get('prediction_identity_ba_m2b'))}; MV09 revises the identity-gate interpretation but finds conditional feature identity remains high after PHQ-item or severity conditioning.",
            "required_next_evidence": "Run a classical psychometric invariance baseline and separate measurement model from multimodal prediction before another RQ1 method attempt.",
            "primary_sources": "P5_MV01;P5_MV02;P5_MV03;P5_MV03b;P5_MV04;P5_MV04b;P5_MV04c;P5_MV05;P5_MV06_summary;P5_MV06_review_pack;P5_MV07_edaic_bge_generation;P5_MV07_readiness;P5_MV07;P5_MV07b;P5_MV07c;P5_MV08_design;P5_MV08;P5_MV08_error_analysis;P5_MV08b_design;P5_MV08b;P5_MV09",
        },
        {
            "claim_id": "C_RQ1_SHARED_SYMPTOM",
            "claim": "Claim a transferable shared symptom representation across scales/datasets.",
            "decision": "blocked",
            "allowed_scope": "Discuss direct shared-symptom mapping as negative/partial diagnostic evidence and reframe RQ1 as measurement-shift and measurement-invariance work.",
            "blocking_evidence": f"PHQ bridge is weak; PDCH HAMD is PDCH-only; EATD SDS audio/text heads do not beat meaningful floors; CMDC HAMD sanity is negative/coverage-limited; MV07b reduces prediction identity to {fmt(mv07b_result.get('best_binary_prediction_identity_ba_after'))} but fails the CMDC total-allocation floor; MV07c total anchor reduces prediction identity to {fmt(mv07c_result.get('prediction_identity_ba'))} but still has CMDC delta vs raw total-allocation {fmt(mv07c_result.get('pooled_cmdc_delta_vs_raw_total_alloc'))}; MV08 partial-invariance ordinal heads reduce prediction identity to {fmt(mv08_result.get('prediction_identity_ba_m2'))} but improve over the total-score floor on {mv08_result.get('pooled_m2_improved_vs_total_score_floor_slices')} pooled active slices; MV08b beats both floors on {mv08b_result.get('pooled_m2b_improved_vs_both_floor_slices')} pooled active slices but has tiny MAE gains and no independent psychometric latent target; MV09 E-DAIC/CMDC item-conditioned feature identity BA is {fmt(mv09_result.get('edaic_cmdc_item_residualized_ba'))}.",
            "required_next_evidence": "A classical psychometric invariance baseline and a two-stage latent-target experiment are needed before any positive transferable shared-measurement claim.",
            "primary_sources": "P5_MV01;P5_MV02;P5_MV02b;P5_MV03;P5_MV03b;P5_MV04b;P5_MV07_edaic_bge_generation;P5_MV07_readiness;P5_MV07;P5_MV07b;P5_MV07c;P5_MV08_design;P5_MV08;P5_MV08_error_analysis;P5_MV08b_design;P5_MV08b;P5_MV09",
        },
        {
            "claim_id": "C_PDCH_HAMD_INTERNAL",
            "claim": "Use PDCH HAMD as bounded internal diagnostic evidence.",
            "decision": "allowed_limited",
            "allowed_scope": "PDCH-only HAMD item/total diagnostic, not cross-dataset HAMD generalization.",
            "blocking_evidence": f"Best item-derived total MAE {fmt(mv02.get('best_pdch_item_total_mae'))}; status {mv02.get('pass_rule_status')}. CMDC sanity remains negative.",
            "required_next_evidence": "External HAMD transfer or stronger CMDC/PDCH-compatible measurement head before cross-dataset HAMD claims.",
            "primary_sources": "P5_MV02;P5_MV02_readiness;P5_MV02b",
        },
        {
            "claim_id": "C_EATD_SDS_GENERALIZATION",
            "claim": "Use EATD SDS total as positive external cross-scale evidence.",
            "decision": "blocked",
            "allowed_scope": "Report EATD as negative/weak SDS external stress.",
            "blocking_evidence": f"Audio status {mv03.get('pass_rule_status')}; text status {mv03b.get('pass_rule_status')}. Best audio MAE {fmt(mv03.get('best_all_valence_mae'))}; best text gain {fmt(mv03b.get('best_delta_vs_train_mean_mae'), 5)}.",
            "required_next_evidence": "A separately audited feature contract with meaningful SDS improvement over train mean and no stronger valence shortcut.",
            "primary_sources": "P5_MV03;P5_MV03b;P5_MV04c",
        },
        {
            "claim_id": "C_DATASET_IDENTITY_CONTROL",
            "claim": "Use dataset/protocol identity controls as required diagnostics.",
            "decision": "allowed_limited",
            "allowed_scope": "Known-dataset centering, source-agnostic WavLM projection, BGE identity projection, BGE total-anchor diagnostics, and conditional identity audits are controls; do not claim invariant representation.",
            "blocking_evidence": f"Known-dataset control status {mv04.get('pass_rule_status')}; WavLM source-agnostic status {mv04b.get('pass_rule_status')}, feature identity after {fmt(mv04b.get('best_feature_identity_ba_after'))}; BGE MV07b feature/prediction identity after {fmt(mv07b_result.get('best_binary_feature_identity_ba_after'))}/{fmt(mv07b_result.get('best_binary_prediction_identity_ba_after'))}; MV07c prediction identity {fmt(mv07c_result.get('prediction_identity_ba'))}; MV09 conditional E-DAIC/CMDC item-residualized feature identity BA {fmt(mv09_result.get('edaic_cmdc_item_residualized_ba'))}.",
            "required_next_evidence": "Future gates must distinguish unconditional feature identity, conditional shared-latent identity, and scale-specific post-head prediction identity.",
            "primary_sources": "P5_MV04;P5_MV04b;P5_MV07b;P5_MV07c;P5_MV09",
        },
        {
            "claim_id": "C_MODMA_TASK_CONTROL",
            "claim": "Use MODMA task nuisance projection as protocol-control evidence.",
            "decision": "allowed_limited",
            "allowed_scope": "MODMA task-specific diagnostic protocol-control result.",
            "blocking_evidence": f"MODMA feature task identity {fmt(mv04c_domains.get('MODMA', {}).get('raw_feature_identity_ba'))} -> {fmt(mv04c_domains.get('MODMA', {}).get('feature_identity_ba_after'))}; main signal preserved={mv04c_domains.get('MODMA', {}).get('main_task_within_5pct_all_slices')}.",
            "required_next_evidence": "Integrate with shared-symptom targets and cross-dataset controls before using it as a full method component.",
            "primary_sources": "P5_MV04c;Phase3_task_valence",
        },
        {
            "claim_id": "C_EATD_VALENCE_ADVERSARIAL",
            "claim": "Add an EATD-driven valence-adversarial component.",
            "decision": "blocked",
            "allowed_scope": "Do not add a valence-adversarial module from current EATD evidence.",
            "blocking_evidence": f"EATD MV04c status {mv04c_domains.get('EATD', {}).get('status')}; main_signal_above_floor={mv04c_domains.get('EATD', {}).get('main_signal_above_floor')}.",
            "required_next_evidence": "Meaningful EATD SDS or depression signal plus demonstrated valence identity/shortcut reduction.",
            "primary_sources": "P5_MV03;P5_MV03b;P5_MV04c",
        },
        {
            "claim_id": "C_RQ3_CONTEXT_CONDITIONING",
            "claim": "Claim positive age/personality context-calibration or conditioning.",
            "decision": "blocked",
            "allowed_scope": "Report MPDD context calibration as negative and keep age/personality as measurement-heterogeneity audit axes.",
            "blocking_evidence": f"P5_MV05 status {mv05.get('pass_rule_status')}; {mv05.get('short_read', '')}",
            "required_next_evidence": "A later measurement-invariance/DIF moderator analysis must improve subgroup behavior beyond AV-only recalibration and shuffled controls before positive RQ3 conditioning claims.",
            "primary_sources": "P5_MV05;Phase3_MPDD",
        },
        {
            "claim_id": "C_RQ4_EVIDENCE_LOCALIZATION",
            "claim": "Claim evidence localization validity.",
            "decision": "allowed_limited" if mv06_ready else "blocked_pending_annotation",
            "allowed_scope": (
                "Use first-round aggregate MV06 annotation and dataset-stratified agreement as credibility evidence; verbatim excerpts remain local-only."
                if mv06_ready
                else "Use current MV06 artifacts as annotation infrastructure only."
            ),
            "blocking_evidence": (
                f"MV06 summary status is {mv06_status}; completed candidates={mv06_gate.get('completed_candidates')}; "
                f"double-annotated candidates={mv06_gate.get('double_annotated_candidates')}; AI preannotation status is "
                f"{mv06_pre.get('preannotation_status', 'not_run')} and review-pack status is "
                f"{mv06_pack.get('review_pack_status', 'not_run')}; AI/review-pack rows remain non-claimable."
            ),
            "required_next_evidence": (
                "For a stronger manuscript claim, expand the E-DAIC double-annotation slice or add Krippendorff alpha/bootstrap uncertainty because E-DAIC currently has few double pairs."
                if mv06_ready
                else "Use the local review pack to complete human annotations, then rerun the summary gate with enough double-annotated rows for agreement, prompt-artifact rates, and aggregate-only hygiene pass."
            ),
            "primary_sources": "P5_MV06_readiness;P5_MV06_pilot;P5_MV06_workbench;P5_MV06_summary;P5_MV06_ai_preannotation;P5_MV06_review_pack",
        },
        {
            "claim_id": "C_PUBLISHABLE_PAPER_DIRECTION",
            "claim": "Continue toward a publishable paper.",
            "decision": "allowed_with_reframing",
            "allowed_scope": "A measurement-shift / measurement-invariance paper direction is viable now; MV08/MV08b/MV09 are bounded diagnostic evidence, not a full-method pass.",
            "blocking_evidence": f"The positive evidence is currently diagnostic and bounded; broad full method claims remain blocked by RQ1 measurement evidence. MV08 is {mv08_status}; error analysis is {mv08_error_status}; MV08b design is {mv08b_design_status}; MV08b run is {mv08b_status}; MV09 is {mv09_status}; data-governance history cleanup remains a separate approval decision.",
            "required_next_evidence": "Start the classical psychometric baseline, then a two-stage latent-target experiment if the measurement model is usable.",
            "primary_sources": "all_phase5",
        },
    ]
    return pd.DataFrame(rows)


def build_next_actions(summaries: dict[str, dict[str, Any]]) -> pd.DataFrame:
    mv07 = summaries["P5_MV07_readiness"].get("decision") or {}
    mv07_result = summaries["P5_MV07"].get("verdict") or {}
    mv07b_result = summaries["P5_MV07b"].get("verdict") or {}
    mv07c_result = summaries["P5_MV07c"].get("verdict") or {}
    mv08_decision = summaries["P5_MV08_design"].get("decision") or {}
    mv08_design_status = str(mv08_decision.get("readiness_status", "unknown"))
    mv08_result = summaries["P5_MV08"].get("verdict") or {}
    mv08_status = str(mv08_result.get("pass_rule_status", "unknown"))
    mv08_error = summaries["P5_MV08_error_analysis"].get("decision") or {}
    mv08_error_status = str(mv08_error.get("error_analysis_status", "unknown"))
    mv08b_design = summaries["P5_MV08b_design"].get("decision") or {}
    mv08b_design_status = str(mv08b_design.get("readiness_status", "unknown"))
    mv08b_result = summaries["P5_MV08b"].get("verdict") or {}
    mv08b_status = str(mv08b_result.get("pass_rule_status", "unknown"))
    mv09_result = summaries["P5_MV09"].get("verdict") or {}
    mv07_ready = mv07.get("readiness_status") == "ready_to_run_minimal_validation"
    if mv09_result.get("status"):
        shared_feature_action = {
            "rank": 2,
            "action_id": "NEXT_CLASSICAL_PSYCHOMETRIC_BASELINE",
            "action": "Run a classical PHQ-8/PHQ-9 psychometric invariance baseline before any MV08c-like multimodal head iteration.",
            "why_now": f"MV09 revises the identity gate and finds conditional feature identity still high: E-DAIC/CMDC item-residualized BA {fmt(mv09_result.get('edaic_cmdc_item_residualized_ba'))}, CMDC/PDCH severity-residualized BA {fmt(mv09_result.get('cmdc_pdch_severity_residualized_ba'))}.",
            "success_gate": "Configural, metric, scalar/threshold, and partial-invariance label-only baselines are reported from item labels without reading raw media or training multimodal predictors.",
            "version_policy": "Track scripts and aggregate psychometric summaries; keep subject-level factor scores, fitted parameters, and row-level diagnostics local-only unless separately approved.",
        }
    elif mv08b_result.get("pass_rule_status"):
        if str(mv08b_result.get("pass_rule_status", "")).startswith("pass_"):
            shared_feature_action = {
                "rank": 2,
                "action_id": "NEXT_BOUND_RQ1_CLAIM_AUDIT_AFTER_MV08B_PASS",
                "action": "Audit whether the MV08b pass supports a bounded RQ1 measurement claim without starting full method work.",
                "why_now": f"MV08b is {mv08b_status}; gate still requires claim-boundary review before full M0/M1/M2/M3 construction.",
                "success_gate": "Claim gate states the exact limited RQ1 scope and verifies no row-level or learned-parameter artifacts are exported.",
                "version_policy": "Track aggregate claim-gate outputs only.",
            }
        else:
            shared_feature_action = {
                "rank": 2,
                "action_id": "NEXT_FREEZE_MV08_SEQUENCE_AND_FRAME_DIAGNOSTIC_PAPER",
                "action": "Freeze MV08/MV08b as negative RQ1 diagnostic evidence under the current frozen-BGE/shallow-measurement contract.",
                "why_now": f"MV08b is {mv08b_status}: it beats both floors on {mv08b_result.get('pooled_m2b_improved_vs_both_floor_slices')} pooled active slices but prediction identity BA is {fmt(mv08b_result.get('prediction_identity_ba_m2b'))}, above the predeclared MV08 M2 gate {fmt(mv08b_result.get('current_mv08_m2_prediction_identity_ba_gate'))}.",
                "success_gate": "Master plan, issue log, and paper outline treat MV08/MV08b as diagnostic/negative RQ1 evidence and stop shallow RQ1 head iteration unless a genuinely new data/feature/measurement source is introduced.",
                "version_policy": "Track scripts and aggregate summaries; keep row predictions, residuals, learned thresholds, learned parameters, and verbatim excerpts local-only.",
            }
    elif mv08b_design.get("readiness_status"):
        shared_feature_action = {
            "rank": 2,
            "action_id": "NEXT_IMPLEMENT_MV08B_TOTAL_ANCHORED_RESIDUAL_MEASUREMENT",
            "action": "Implement and run the predeclared MV08b total-anchored residual measurement row.",
            "why_now": f"MV08 is {mv08_status}; error analysis is {mv08_error_status}; MV08b design is {mv08b_design_status}, so the next evidence gap is the audited MV08b run.",
            "success_gate": "MV08b must beat total-score and fixed-map floors on at least two pooled active slices, keep prediction identity no higher than current MV08 M2, and export only aggregate diagnostics.",
            "version_policy": "Track scripts and aggregate summaries; keep row predictions, latent scores, learned parameters, thresholds, and verbatim excerpts local-only.",
        }
    elif mv08_error.get("error_analysis_status"):
        shared_feature_action = {
            "rank": 2,
            "action_id": "NEXT_MV08B_DECISION_OR_FREEZE_NEGATIVE_EVIDENCE",
            "action": "Decide whether to predeclare an MV08b total-anchored residual measurement revision or freeze MV08 as negative evidence.",
            "why_now": f"MV08 is {mv08_status}; error analysis is {mv08_error_status}; the current M2 fails the total-score floor on {mv08_result.get('pooled_active_slices')} pooled active slices.",
            "success_gate": "Either an MV08b design contract is written with floors, identity gates, and local-only outputs, or MV08 is frozen as diagnostic/negative RQ1 evidence for the paper.",
            "version_policy": "Track scripts and aggregate summaries; keep row predictions, latent scores, learned parameters, and verbatim excerpts local-only.",
        }
    elif mv08_result.get("pass_rule_status"):
        shared_feature_action = {
            "rank": 2,
            "action_id": "NEXT_MV08_ERROR_ANALYSIS_OR_MEASUREMENT_REVISION",
            "action": "Analyze the negative MV08 partial-invariance result and decide whether to revise the psychometric measurement contract.",
            "why_now": f"MV08 is {mv08_status}: M2 improves over the total-score floor on {mv08_result.get('pooled_m2_improved_vs_total_score_floor_slices')} pooled active slices, while prediction identity BA remains {fmt(mv08_result.get('prediction_identity_ba_m2'))}.",
            "success_gate": "Either identify a predeclared measurement revision that can beat total-score and fixed-map floors without worsening identity, or freeze MV08 as negative evidence for a diagnostic/audit paper.",
            "version_policy": "Track scripts and aggregate summaries; keep row predictions, latent scores, learned parameters, and verbatim excerpts local-only.",
        }
    elif mv07c_result.get("pass_rule_status"):
        shared_feature_action = {
            "rank": 2,
            "action_id": "NEXT_RUN_PARTIAL_INVARIANCE_MEASUREMENT",
            "action": "Implement and run the MV08 partial-invariance ordinal measurement pilot.",
            "why_now": f"MV08 design is {mv08_design_status}; MV07b and MV07c reduce prediction identity but still fail the CMDC total-allocation floor, so the next step must change the measurement contract.",
            "success_gate": "MV08 compares total-score, fixed construct-map, and shared latent constructs plus scale-specific DIF/loading-threshold deviations on E-DAIC, CMDC, and PDCH.",
            "version_policy": "Track scripts and aggregate summaries; keep row predictions, transformed features, projection directions, and model artifacts local-only.",
        }
    elif mv07b_result.get("pass_rule_status"):
        shared_feature_action = {
            "rank": 2,
            "action_id": "NEXT_MV07B_SHARED_SYMPTOM_FLOOR_FIX",
            "action": "Resolve the MV07b BGE identity-controlled floor gap or formally demote it to partial diagnostic evidence.",
            "why_now": f"MV07b reduced BGE feature/prediction identity to {fmt(mv07b_result.get('best_binary_feature_identity_ba_after'))}/{fmt(mv07b_result.get('best_binary_prediction_identity_ba_after'))}, but CMDC remains worse than total allocation by {fmt(mv07b_result.get('best_pooled_cmdc_delta_vs_total_alloc'))} Macro MAE.",
            "success_gate": "An identity-controlled BGE/shared-symptom variant beats train-mean and total-allocation floors on both E-DAIC and CMDC while keeping feature/prediction identity reduced.",
            "version_policy": "Track scripts and aggregate summaries; keep row predictions, transformed features, projection directions, and model artifacts local-only.",
        }
    elif mv07_result.get("pass_rule_status"):
        shared_feature_action = {
            "rank": 2,
            "action_id": "NEXT_SHARED_SYMPTOM_IDENTITY_CONTROL",
            "action": "Design a stronger shared-symptom feature contract or identity-control variant after the aligned-BGE MV07 block.",
            "why_now": f"MV07 ran and is {mv07_result.get('pass_rule_status')}; feature identity and prediction identity remain high.",
            "success_gate": "A revised contract beats train-mean/total-allocation floors and reduces feature/prediction identity before any shared-representation claim.",
            "version_policy": "Track scripts and aggregate summaries; keep row predictions, transformed features, and model artifacts local-only.",
        }
    elif mv07_ready:
        shared_feature_action = {
            "rank": 2,
            "action_id": "NEXT_MV07_TEXT_BGE_SHARED_SYMPTOM",
            "action": "Run the aligned-BGE MV07 shallow shared-symptom validation row.",
            "why_now": "E-DAIC, CMDC, and PDCH now share one BGE subject-level feature family; the next missing evidence is model performance plus identity/protocol probes.",
            "success_gate": "MV07 beats train-mean/total-allocation floors where applicable and reports dataset/protocol identity without worsening shortcut controls.",
            "version_policy": "Track scripts and aggregate summaries; keep row predictions, transformed features, and model artifacts local-only.",
        }
    else:
        shared_feature_action = {
            "rank": 2,
            "action_id": "NEXT_SHARED_FEATURE_CONTRACT",
            "action": "Generate aligned E-DAIC BGE text features, then rerun MV07 readiness and the shared-symptom feature contract.",
            "why_now": "MV07 readiness shows BGE is the cleanest next aligned text contract because CMDC/PDCH BGE already exists while E-DAIC BGE is missing.",
            "success_gate": "E-DAIC/CMDC/PDCH share one BGE subject-level feature family with no path-like columns; the subsequent MV07 run beats simple floors without worsening identity controls.",
            "version_policy": "Track scripts and aggregate summaries; keep generated BGE features, row-level predictions, embeddings, and weights local-only.",
        }
    shared_feature_action["rank"] = 1
    rows = [
        shared_feature_action,
        {
            "rank": 2,
            "action_id": "NEXT_MV06_EVIDENCE_STRENGTHENING",
            "action": "Use the dataset-stratified MV06 agreement summary as first-round RQ4 evidence, then optionally expand the E-DAIC double-annotation slice.",
            "why_now": "MV06 now reaches the 30 completed and 20 double-annotated default gate, but E-DAIC has few double pairs and degenerate kappa for several fields.",
            "success_gate": "Dataset-stratified agreement remains aggregate-only, and any added E-DAIC review improves per-dataset agreement stability without exporting snippets or source locators.",
            "version_policy": "Commit aggregate summaries only; keep verbatim excerpts, source maps, local workbooks, and per-subject rationales local-only.",
        },
        {
            "rank": 3,
            "action_id": "NEXT_SPEAKER_PROTOCOL_RECOVERY",
            "action": "Recover or create speaker/protocol labels for E-DAIC participant/interviewer controls if feasible.",
            "why_now": "Literal participant-only/interviewer-only controls remain blocked; they would strengthen RQ2 beyond position proxies.",
            "success_gate": "Speaker-resolved subject-level controls with no leakage and aggregate-only outputs.",
            "version_policy": "Do not commit raw transcripts or source paths.",
        },
        {
            "rank": 4,
            "action_id": "NEXT_MPDD_METADATA_SYNC",
            "action": "Try to recover structured MPDD gender/health metadata and official test labels as a governance update.",
            "why_now": "Gender/health context claims and official MPDD test protocols remain blocked by missing local metadata.",
            "success_gate": "Registry/manifest update plus audit showing coverage and no split leakage.",
            "version_policy": "Commit lightweight metadata coverage/audit only; keep raw files local if license-sensitive.",
        },
        {
            "rank": 5,
            "action_id": "NEXT_REMOTE_HISTORY_DECISION_OPTIONAL",
            "action": "Decide later whether the public remote history needs rewrite or repository recreation.",
            "why_now": "Latest-tree dataset governance is now mitigated; history rewriting is optional and requires explicit user approval.",
            "success_gate": "No force-push or repository recreation happens without an explicit decision from the user.",
            "version_policy": "Continue clean snapshot publishing for normal updates.",
        },
    ]
    return pd.DataFrame(rows)


def artifact_hygiene(out_dir: Path) -> dict[str, Any]:
    forbidden_patterns = [
        r"/root/autodl-tmp/datasets/",
        r"audio_path",
        r"video_path",
        r"text_path",
        r"gait_path",
        r"\.wav\b",
        r"\.mp4\b",
        r"\.avi\b",
        r"raw prompt",
        r"raw response",
    ]
    violations: list[dict[str, str]] = []
    checked = 0
    for path in sorted(out_dir.rglob("*")):
        if not path.is_file() or path.suffix.lower() not in {".csv", ".json", ".md", ".txt"}:
            continue
        checked += 1
        text = path.read_text(encoding="utf-8", errors="ignore")
        for pattern in forbidden_patterns:
            if re.search(pattern, text):
                violations.append({"file": rel(path), "pattern": pattern})
    return {
        "audit_id": "P5_full_method_gate_artifact_hygiene",
        "generated_at": utc_now(),
        "files_checked": checked,
        "violation_count": len(violations),
        "violations": violations,
        "artifact_hygiene_passed": len(violations) == 0,
    }


def write_report(
    out_dir: Path,
    run_summary: dict[str, Any],
    evidence: pd.DataFrame,
    claims: pd.DataFrame,
    actions: pd.DataFrame,
) -> None:
    blocked = claims[claims["decision"].astype(str).str.startswith("blocked")]
    allowed = claims[claims["decision"].astype(str).str.startswith("allowed")]
    lines = [
        "# Phase 5 Full-Method Gate Audit",
        "",
        f"Generated: `{run_summary['generated_at']}`",
        "",
        "## Decision",
        "",
        f"- Full method allowed: `{run_summary['full_method_allowed']}`.",
        f"- Gate status: `{run_summary['gate_status']}`.",
        f"- Blocked claim count: `{len(blocked)}`.",
        f"- Allowed limited/reframed claim count: `{len(allowed)}`.",
        "",
        "The current evidence supports a careful diagnostic paper direction, but not a broad full symptom-aligned method claim yet.",
        "",
        "## Claim Gate",
        "",
        "| claim | decision | allowed scope | required next evidence |",
        "| --- | --- | --- | --- |",
    ]
    for _, row in claims.iterrows():
        lines.append(
            f"| {row['claim_id']} | `{row['decision']}` | {row['allowed_scope']} | {row['required_next_evidence']} |"
        )

    lines.extend(
        [
            "",
            "## Evidence Inventory",
            "",
            "| evidence | status | pass-rule status | hygiene | short read |",
            "| --- | --- | --- | --- | --- |",
        ]
    )
    for _, row in evidence.iterrows():
        short = str(row["short_read"]).replace("|", "/")
        if len(short) > 220:
            short = short[:217] + "..."
        lines.append(
            f"| {row['evidence_id']} | `{row['status']}` | `{row['pass_rule_status']}` | `{row['artifact_hygiene_passed']}` | {short} |"
        )

    lines.extend(
        [
            "",
            "## Next Actions",
            "",
            "| rank | action | success gate |",
            "| ---: | --- | --- |",
        ]
    )
    for _, row in actions.sort_values("rank").iterrows():
        lines.append(f"| {int(row['rank'])} | {row['action']} | {row['success_gate']} |")

    lines.extend(
        [
            "",
            "## Interpretation Boundary",
            "",
            "This audit is deliberately conservative. A row marked `allowed_limited` can appear in the paper as bounded diagnostic evidence, but it does not authorize a broad method claim. Full-model work should start only after the blocked gates are addressed or the paper is explicitly reframed around diagnostics, negative results, and a bounded method proposal.",
        ]
    )
    (out_dir / "report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    args = parser.parse_args()

    out_dir = args.out_dir
    if out_dir.exists():
        shutil.rmtree(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    summaries = {key: read_json(path) for key, path in RUN_SUMMARIES.items()}
    evidence = collect_evidence(summaries)
    claims = build_claim_gate(summaries)
    actions = build_next_actions(summaries)

    full_method_allowed = not any(claims["decision"].astype(str).str.startswith("blocked"))
    gate_status = "full_method_blocked"
    if full_method_allowed:
        gate_status = "full_method_allowed"
    elif "allowed_with_reframing" in set(claims["decision"].astype(str)):
        gate_status = "blocked_but_publishable_diagnostic_direction"

    run_summary = {
        "generated_at": utc_now(),
        "gate_status": gate_status,
        "full_method_allowed": full_method_allowed,
        "evidence_rows": int(len(evidence)),
        "claim_rows": int(len(claims)),
        "next_action_rows": int(len(actions)),
        "blocked_claims": sorted(claims.loc[claims["decision"].astype(str).str.startswith("blocked"), "claim_id"]),
        "allowed_limited_claims": sorted(claims.loc[claims["decision"].astype(str).str.startswith("allowed"), "claim_id"]),
        "source_run_summaries": {key: rel(path) for key, path in RUN_SUMMARIES.items()},
    }

    evidence.to_csv(out_dir / "evidence_inventory.csv", index=False)
    claims.to_csv(out_dir / "claim_gate.csv", index=False)
    actions.to_csv(out_dir / "next_action_queue.csv", index=False)
    (out_dir / "run_summary.json").write_text(json.dumps(run_summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    write_report(out_dir, run_summary, evidence, claims, actions)
    hygiene = artifact_hygiene(out_dir)
    run_summary["artifact_hygiene"] = hygiene
    (out_dir / "run_summary.json").write_text(json.dumps(run_summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (out_dir / "artifact_hygiene_audit.json").write_text(
        json.dumps(hygiene, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    if not hygiene["artifact_hygiene_passed"]:
        raise SystemExit("artifact hygiene failed")
    print(json.dumps({"out_dir": str(out_dir), "gate_status": gate_status}, indent=2))


if __name__ == "__main__":
    main()
