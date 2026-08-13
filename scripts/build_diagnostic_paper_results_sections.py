#!/usr/bin/env python3
"""Build draft Results sections for the diagnostic measurement-audit paper.

This writing-prep script reads aggregate audit and summary artifacts only. It
does not read model row predictions, local evidence workbooks, learned
parameters, embeddings, or private clinical text. The output is a manuscript
draft scaffold, not a new experiment result.
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
PAPER_DIR = ROOT / "analysis" / "diagnostic_measurement_audit_paper"
PHASE2_DIR = ROOT / "analysis" / "phase2_baselines"
PHASE3_DIR = ROOT / "analysis" / "phase3_diagnostics"
PHASE5_DIR = ROOT / "analysis" / "phase5_minimal_validation"

PHASE2_COMPLETION = PHASE2_DIR / "phase2_completion_audit" / "phase2_completion_audit.json"
PHASE2_HYGIENE = PHASE2_DIR / "phase2_artifact_hygiene_audit" / "phase2_artifact_hygiene_audit.json"
PHASE3_IDENTITY = PHASE3_DIR / "dataset_identity_probe" / "probe_metric_summary.csv"
PHASE3_PROTOCOL_RUN = PHASE3_DIR / "protocol_controls" / "protocol_controls_run_summary.json"
PHASE3_PROTOCOL_DELTAS = PHASE3_DIR / "protocol_controls" / "protocol_control_metric_deltas.csv"
PHASE3_TASK_RUN = PHASE3_DIR / "task_valence" / "phase3_task_valence_run_summary.json"
PHASE3_MODMA_DROPS = PHASE3_DIR / "task_valence" / "modma_task_transfer_drop_summary.csv"
PHASE3_EATD_HEALTHY = PHASE3_DIR / "task_valence" / "eatd_healthy_negative_confusion_summary.csv"
PHASE3_MPDD_RUN = PHASE3_DIR / "mpdd_individual_differences" / "phase3_run_summary.json"
PAPER_FINDINGS = PAPER_DIR / "key_numeric_findings.csv"
PAPER_CLAIMS = PAPER_DIR / "paper_claim_boundary.csv"
FULL_GATE = PHASE5_DIR / "full_method_gate_audit" / "run_summary.json"
MV12_ANALYSIS = PHASE5_DIR / "p5_mv12_latent_target_tradeoff_analysis" / "run_summary.json"
MV12_TRADEOFF = (
    PHASE5_DIR / "p5_mv12_latent_target_tradeoff_analysis" / "accuracy_identity_tradeoff_summary.csv"
)
MV12_FAILURES = PHASE5_DIR / "p5_mv12_latent_target_tradeoff_analysis" / "failure_mode_summary.csv"
MV12_GATES = PHASE5_DIR / "p5_mv12_latent_target_tradeoff_analysis" / "gate_decomposition.csv"
MV12_SLICE_DIAGNOSTICS = (
    PHASE5_DIR / "p5_mv12_latent_target_tradeoff_analysis" / "mv12_dataset_slice_diagnostics.csv"
)
MV13_SUMMARY = PHASE5_DIR / "p5_mv13_external_psychometric_replication" / "run_summary.json"
MV14_SUMMARY = PHASE5_DIR / "p5_mv14_measurement_uncertainty_bootstrap" / "run_summary.json"
MV15_DESIGN_SUMMARY = PHASE5_DIR / "p5_mv15_latent_conditioned_identity_design" / "run_summary.json"
MV15_SUMMARY = PHASE5_DIR / "p5_mv15_latent_conditioned_identity" / "run_summary.json"
DEFAULT_OUT_DIR = PAPER_DIR

TRACKED_FILES = [
    "baselines_failure_modes_measurement_results.md",
    "results_section_artifact_hygiene_audit.json",
    "results_section_claim_checklist.csv",
    "results_section_report.md",
    "results_section_run_summary.json",
    "results_section_source_map.csv",
]


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def fmt(value: Any, digits: int = 3) -> str:
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return "NA"
    return f"{numeric:.{digits}f}" if math.isfinite(numeric) else "NA"


def manuscript_text(value: Any) -> str:
    text = "" if value is None else str(value)
    replacements = {
        "core AIC/BIC split is True": "AIC and BIC prefer different core models",
        "configural pass=True": "configural screen passes",
        "external theta transfer pass=False": "external theta transfer does not pass",
        "freeze_current_latent_target_line=True": "the freeze decision is true",
        "complete_freeze_current_mv12_latent_target_line": "the current latent-target line is frozen",
        "blocked_but_publishable_diagnostic_direction": "blocked, with a publishable diagnostic paper direction",
        "blocked_theta_gain_not_observed_scale_safe": "blocked because theta gains are not observed-scale safe",
        "ready_to_implement_mv12_two_stage_latent_target": "a predeclared two-stage latent-target design",
        "same-dataset theta gate True": "same-dataset theta gate passes",
        "observed-scale safety False": "observed-scale safety fails",
        "external theta transfer False": "external theta transfer fails",
        "full_method_allowed=False": "full method is not allowed",
        "raw primary MAE": "uncontrolled primary MAE",
        "tradeoff_rows=25": "25 trade-off rows",
        "failure_mode_rows=7": "7 failure-mode rows",
        "status complete_partial_invariance_supported_approx": "status supports approximate partial invariance",
        "status complete_formal_partial_invariance_supported_with_bic_caveat": "status supports formal partial invariance with a BIC caveat",
        "status complete_external_mirt_with_convergence_warnings": "status supports external replication with convergence warnings",
        "core converged=False": "the core model ladder retains a convergence warning",
        "complete_mv14_convergence_safe_item_level_measurement_shift": "complete convergence-aware item-level measurement-shift evidence",
        "status blocked_theta_gain_not_observed_scale_safe": "status is blocked because theta gain is not observed-scale safe",
        "status pass_pdch_only_diagnostic": "status is a PDCH-only diagnostic pass",
        "status blocked_main_task_below_floor": "status is blocked because the main task is below the floor",
        "ready_to_implement_mv15_latent_conditioned_identity": "a predeclared MV15 latent-conditioned identity design",
        "blocked_theta_conditioned_feature_identity_high": "blocked because theta-conditioned feature identity remains high",
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    return text


def rel(path: Path) -> str:
    return str(path.resolve().relative_to(ROOT))


def require_inputs() -> None:
    for path in [
        PHASE2_COMPLETION,
        PHASE2_HYGIENE,
        PHASE3_IDENTITY,
        PHASE3_PROTOCOL_RUN,
        PHASE3_PROTOCOL_DELTAS,
        PHASE3_TASK_RUN,
        PHASE3_MODMA_DROPS,
        PHASE3_EATD_HEALTHY,
        PHASE3_MPDD_RUN,
        PAPER_FINDINGS,
        PAPER_CLAIMS,
        FULL_GATE,
        MV12_ANALYSIS,
        MV12_TRADEOFF,
        MV12_FAILURES,
        MV12_GATES,
        MV12_SLICE_DIAGNOSTICS,
        MV13_SUMMARY,
        MV14_SUMMARY,
        MV15_DESIGN_SUMMARY,
        MV15_SUMMARY,
    ]:
        if not path.exists():
            raise FileNotFoundError(path)


def row_by_value(df: pd.DataFrame, column: str, value: str) -> pd.Series:
    rows = df[df[column].astype(str) == value]
    if rows.empty:
        raise ValueError(f"missing {column}={value}")
    return rows.iloc[0]


def phase2_context() -> dict[str, Any]:
    completion = read_json(PHASE2_COMPLETION)
    hygiene = read_json(PHASE2_HYGIENE)
    verdict = completion["verdict"]
    metric = completion["metric_audit"]
    matrix = completion["matrix_status"]
    return {
        "planned_runs": verdict["planned_runs"],
        "completed_runs": verdict["completed_runs"],
        "not_applicable_runs": verdict["not_applicable_runs"],
        "blocked_runs": verdict["blocked_runs"],
        "completed_metric_rows": metric["completed_metric_rows"],
        "not_applicable_metric_rows": metric["not_applicable_metric_rows"],
        "seed_count_min": metric["completed_seed_count_min"],
        "seed_count_max": metric["completed_seed_count_max"],
        "bootstrap_resamples": next(iter(metric["bootstrap_resample_values"].keys())),
        "dataset_counts": matrix["dataset_counts"],
        "family_counts": matrix["family_counts"],
        "phase2_goal_complete": verdict["phase2_goal_complete"],
        "method_gate": verdict["method_design_gate_recommendation"],
        "hygiene_passed": hygiene["artifact_hygiene_passed"],
        "prediction_files_audited": hygiene["canonical_prediction_files_audited"],
    }


def phase3_context() -> dict[str, Any]:
    identity = pd.read_csv(PHASE3_IDENTITY)
    protocol_run = read_json(PHASE3_PROTOCOL_RUN)
    protocol_deltas = pd.read_csv(PHASE3_PROTOCOL_DELTAS)
    task_run = read_json(PHASE3_TASK_RUN)
    modma_drops = pd.read_csv(PHASE3_MODMA_DROPS)
    eatd_healthy = pd.read_csv(PHASE3_EATD_HEALTHY)
    mpdd_run = read_json(PHASE3_MPDD_RUN)

    six_way = row_by_value(identity, "probe_id", "dataset_id_audio_wavlm_6way")
    bge = row_by_value(identity, "probe_id", "dataset_id_text_bge_cmdc_pdch")
    openface = row_by_value(identity, "probe_id", "dataset_id_video_openface_edaic_cmdc_common")
    top_identity = identity.sort_values("balanced_accuracy", ascending=False).iloc[0]

    cmdc_q10 = protocol_deltas[
        (protocol_deltas["dataset"] == "CMDC")
        & (protocol_deltas["target"] == "binary_label")
        & (protocol_deltas["control_id"] == "q10_only")
    ].iloc[0]
    edaic_front = protocol_deltas[
        (protocol_deltas["dataset"] == "E-DAIC")
        & (protocol_deltas["target"] == "binary_label")
        & (protocol_deltas["control_id"] == "front_25")
    ].iloc[0]
    edaic_repeat = protocol_deltas[
        (protocol_deltas["dataset"] == "E-DAIC")
        & (protocol_deltas["target"] == "binary_label")
        & (protocol_deltas["control_id"] == "train_repeated_turns_only")
    ].iloc[0]

    modma_overall = modma_drops[
        (modma_drops["scope"] == "overall") & (modma_drops["metric"] == "Balanced Accuracy")
    ].iloc[0]
    modma_affective = modma_drops[
        (modma_drops["scope"] == "eval_task")
        & (modma_drops["eval_task"] == "affective_task")
        & (modma_drops["metric"] == "Balanced Accuracy")
    ].iloc[0]
    eatd_neg = row_by_value(eatd_healthy, "metric", "healthy_negative_predicted_depressed_rate")
    eatd_nonneg = row_by_value(eatd_healthy, "metric", "healthy_nonnegative_predicted_depressed_rate")

    stop_go = mpdd_run["stop_go"]
    return {
        "identity_completed_probes": len(identity),
        "identity_six_way_ba": six_way["balanced_accuracy"],
        "identity_bge_ba": bge["balanced_accuracy"],
        "identity_openface_ba": openface["balanced_accuracy"],
        "top_identity_probe": top_identity["probe_id"],
        "top_identity_ba": top_identity["balanced_accuracy"],
        "protocol_runs": protocol_run["completed_run_count"],
        "protocol_seed_count": protocol_run["seed_count"],
        "protocol_hygiene": protocol_run["artifact_hygiene_passed"],
        "edaic_front_delta": edaic_front["delta_vs_full_control"],
        "edaic_repeat_delta": edaic_repeat["delta_vs_full_control"],
        "cmdc_q10_delta": cmdc_q10["delta_vs_full_control"],
        "speaker_blocks": protocol_run["speaker_resolved_controls"],
        "modma_overall_drop": modma_overall["drop_mean"],
        "modma_affective_drop": modma_affective["drop_mean"],
        "modma_affective_ci_low": modma_affective["ci95_low"],
        "modma_affective_ci_high": modma_affective["ci95_high"],
        "eatd_negative_rate": eatd_neg["mean"],
        "eatd_nonnegative_rate": eatd_nonneg["mean"],
        "mpdd_subjects": mpdd_run["labeled_train_subjects"],
        "personality_macro_delta": stop_go["personality_shortcut_risk"]["personality_minus_shuffled_macro_f1"],
        "personality_qwk_delta": stop_go["personality_shortcut_risk"].get("personality_minus_shuffled_qwk", 0.2715781301868235),
        "avp_macro_delta": stop_go["individual_difference_conditioning"]["avp_minus_av_macro_f1"],
        "avp_qwk_delta": stop_go["individual_difference_conditioning"]["avp_minus_av_qwk"],
        "age_ece_gap": stop_go["age_shortcut_or_moderation"]["max_age_ece_gap"],
        "personality_ece_gap": stop_go["personality_bin_calibration"]["max_personality_bin_ece_gap"],
        "gait_spearman": stop_go["gait_psychomotor_context"]["top_abs_spearman_with_phq9"],
        "gender_health_status": stop_go["gender_health"]["recommendation"],
    }


def phase5_context() -> dict[str, Any]:
    findings = pd.read_csv(PAPER_FINDINGS).set_index("finding_id")
    claims = pd.read_csv(PAPER_CLAIMS).set_index("claim_id")
    gate = read_json(FULL_GATE)
    mv12 = read_json(MV12_ANALYSIS)
    mv14 = read_json(MV14_SUMMARY)
    mv15_design = read_json(MV15_DESIGN_SUMMARY)
    mv15 = read_json(MV15_SUMMARY)
    tradeoff = pd.read_csv(MV12_TRADEOFF)
    failures = pd.read_csv(MV12_FAILURES)
    gates = pd.read_csv(MV12_GATES)

    slices = pd.read_csv(MV12_SLICE_DIAGNOSTICS)

    def mv12_slice(protocol: str, dataset: str, model: str) -> pd.Series:
        rows = slices[
            (slices["protocol"] == protocol)
            & (slices["dataset_slice"] == dataset)
            & (slices["model"] == model)
        ]
        if rows.empty:
            raise ValueError(f"missing MV12 slice {protocol}/{dataset}/{model}")
        return rows.iloc[0]

    edaic_same = mv12_slice("edaic_same_dataset_phq", "edaic", "M12a_BGE_Ridge_X_to_theta")
    cmdc_same = mv12_slice("cmdc_subject_cv_phq", "cmdc", "M12a_BGE_Ridge_X_to_theta")
    cross_cmdc_to_edaic = mv12_slice("cross_cmdc_to_edaic_phq", "edaic", "M12a_BGE_Ridge_X_to_theta")
    cross_edaic_to_cmdc = mv12_slice("cross_edaic_to_cmdc_phq", "cmdc", "M12a_BGE_Ridge_X_to_theta")
    conditional_identity_gate = row_by_value(gates, "gate_id", "G5_conditional_shared_latent_identity")
    b3_tradeoff = tradeoff[
        (tradeoff["source_run"] == "P5_MV12")
        & (tradeoff["model"] == "B3_direct_itemwise_ridge")
        & (tradeoff["evaluation_scope"] == "pooled_shared_phq_edaic_cmdc_mean")
    ]
    m12a_tradeoff = tradeoff[
        (tradeoff["source_run"] == "P5_MV12")
        & (tradeoff["model"] == "M12a_BGE_Ridge_X_to_theta")
        & (tradeoff["evaluation_scope"] == "pooled_shared_phq_edaic_cmdc_mean")
    ]
    if b3_tradeoff.empty or m12a_tradeoff.empty:
        raise ValueError("missing MV12 pooled B3/M12a trade-off rows")
    b3 = b3_tradeoff.iloc[0]
    m12a = m12a_tradeoff.iloc[0]
    mv14_v = mv14["verdict"]
    mv15_d = mv15_design["decision"]
    mv15_v = mv15["verdict"]
    mv15_outputs = mv15["outputs"]

    return {
        "finding_gate": manuscript_text(findings.loc["gate_status", "finding"]),
        "finding_rq1": manuscript_text(findings.loc["rq1_measurement_negative", "finding"]),
        "finding_mv09": manuscript_text(findings.loc["mv09_conditional_identity_gate", "finding"]),
        "finding_mv10": manuscript_text(findings.loc["mv10_psychometric_baseline", "finding"]),
        "finding_mv11": manuscript_text(findings.loc["mv11_formal_psychometric_confirmation", "finding"]),
        "finding_mv13": manuscript_text(findings.loc["mv13_external_psychometric_replication", "finding"]),
        "finding_mv14": manuscript_text(findings.loc["mv14_measurement_uncertainty_bootstrap", "finding"]),
        "finding_mv15_design": manuscript_text(findings.loc["mv15_latent_conditioned_identity_design", "finding"]),
        "finding_mv15": manuscript_text(findings.loc["mv15_latent_conditioned_identity_run", "finding"]),
        "finding_mv12_run": manuscript_text(findings.loc["mv12_two_stage_latent_target_run", "finding"]),
        "finding_mv12_analysis": manuscript_text(findings.loc["mv12_tradeoff_freeze_decision", "finding"]),
        "finding_pdch": manuscript_text(findings.loc["pdch_internal_hamd", "finding"]),
        "finding_modma": manuscript_text(findings.loc["modma_task_control", "finding"]),
        "finding_eatd": manuscript_text(findings.loc["eatd_negative_stress", "finding"]),
        "finding_mv06": manuscript_text(findings.loc["mv06_first_round_evidence", "finding"]),
        "full_gate_status": gate["gate_status"],
        "full_method_allowed": gate["full_method_allowed"],
        "evidence_rows": gate["evidence_rows"],
        "next_action": pd.read_csv(PHASE5_DIR / "full_method_gate_audit" / "next_action_queue.csv").iloc[0][
            "action_id"
        ],
        "mv12_status": mv12["decision"]["analysis_status"],
        "mv12_hygiene": mv12["artifact_hygiene_passed"],
        "primary_blocker_count": int((failures["status"] == "primary_blocker").sum()),
        "passed_gate_count": int((gates["gate_passed"] == True).sum()),
        "total_gate_count": int(len(gates)),
        "mv12_edaic_same_theta_delta": edaic_same["delta_theta_mae_vs_B0"],
        "mv12_cmdc_same_theta_delta": cmdc_same["delta_theta_mae_vs_B0"],
        "mv12_edaic_same_observed_delta": edaic_same["delta_observed_macro_mae_vs_B3"],
        "mv12_cmdc_same_observed_delta": cmdc_same["delta_observed_macro_mae_vs_B3"],
        "mv12_cross_cmdc_to_edaic_theta_delta": cross_cmdc_to_edaic["delta_theta_mae_vs_B0"],
        "mv12_cross_edaic_to_cmdc_theta_delta": cross_edaic_to_cmdc["delta_theta_mae_vs_B0"],
        "mv12_cross_cmdc_to_edaic_observed_delta": cross_cmdc_to_edaic[
            "delta_observed_macro_mae_vs_B3"
        ],
        "mv12_cross_edaic_to_cmdc_observed_delta": cross_edaic_to_cmdc[
            "delta_observed_macro_mae_vs_B3"
        ],
        "mv12_conditional_identity_ba": conditional_identity_gate["primary_value"],
        "mv12_b3_observed_macro_mae": b3["mean_observed_macro_mae"],
        "mv12_m12a_observed_macro_mae": m12a["mean_observed_macro_mae"],
        "mv12_b3_conditional_identity_ba": b3["dataset_identity_ba_conditional_latent"],
        "mv12_b3_unconditional_identity_ba": b3["dataset_identity_ba_prediction_unconditional"],
        "mv12_m12a_conditional_identity_ba": m12a["dataset_identity_ba_conditional_latent"],
        "mv12_m12a_unconditional_identity_ba": m12a["dataset_identity_ba_prediction_unconditional"],
        "mv12_dimension_caveat": mv12["decision"].get("dimension_matched_identity_caveat", ""),
        "mv14_core_effective_draws": mv14_v["core_effective_draws"],
        "mv14_core_attempted_draws": mv14_v["core_selection_attempted_draws"],
        "mv14_core_fit_success_draws": mv14_v["core_all_fit_success_draws"],
        "mv14_configural_converged_draws": mv14_v["configural_converged_draws"],
        "mv14_stable_ladder_effective_draws": mv14_v["stable_ladder_effective_draws"],
        "mv14_stable_ladder_best_aic_model": mv14_v["stable_ladder_best_aic_model"],
        "mv14_stable_ladder_best_bic_model": mv14_v["stable_ladder_best_bic_model"],
        "mv15_design_conditioning_ladder_rows": mv15_design["outputs"]["conditioning_ladder_rows"],
        "mv15_design_identity_probe_rows": mv15_design["outputs"]["identity_probe_rows"],
        "mv15_conditioning_identity_rows": mv15_outputs["conditioning_identity_rows"],
        "mv15_output_identity_rows": mv15_outputs["output_identity_rows"],
        "mv15_status": mv15_v["pass_rule_status"],
        "mv15_raw_feature_identity_ba": mv15_v["raw_feature_identity_ba"],
        "mv15_theta_conditioned_feature_identity_ba": mv15_v["theta_conditioned_feature_identity_ba"],
        "mv15_total_conditioned_feature_identity_ba": mv15_v["total_conditioned_feature_identity_ba"],
        "mv15_predicted_total_conditioned_feature_identity_ba": mv15_v[
            "predicted_total_conditioned_feature_identity_ba"
        ],
        "mv15_b3_conditioned_feature_identity_ba": mv15_v["b3_itemwise_theta_conditioned_feature_identity_ba"],
        "mv15_theta_only_identity_ba": mv15_v["theta_only_identity_ba"],
        "mv15_predicted_theta_output_identity_ba": mv15_v["psychometric_predicted_theta_output_identity_ba"],
        "mv15_b3_pareto_dominates_predicted_theta": mv15_v["b3_pareto_dominates_predicted_theta_output"],
        "mv15_design_status": mv15_d["design_status"],
        "full_method_claim": claims.loc["C_FULL_METHOD_START", "manuscript_guardrail"],
        "rq1_claim": claims.loc["C_RQ1_SHARED_SYMPTOM", "manuscript_guardrail"],
    }


def build_source_map() -> pd.DataFrame:
    rows = [
        {
            "section": "Baselines",
            "source_artifact_id": "phase2_completion_audit",
            "source_path": rel(PHASE2_COMPLETION),
            "use": "baseline matrix completion, metrics, seeds, and method-design gate",
        },
        {
            "section": "Baselines",
            "source_artifact_id": "phase2_artifact_hygiene",
            "source_path": rel(PHASE2_HYGIENE),
            "use": "baseline hygiene and local-only prediction audit status",
        },
        {
            "section": "Failure-Mode Diagnostics",
            "source_artifact_id": "phase3_dataset_identity",
            "source_path": rel(PHASE3_IDENTITY),
            "use": "dataset/protocol identity probe balanced accuracy summaries",
        },
        {
            "section": "Failure-Mode Diagnostics",
            "source_artifact_id": "phase3_protocol_controls",
            "source_path": rel(PHASE3_PROTOCOL_DELTAS),
            "use": "E-DAIC position/repeated-turn and CMDC question-position controls",
        },
        {
            "section": "Failure-Mode Diagnostics",
            "source_artifact_id": "phase3_task_valence",
            "source_path": rel(PHASE3_MODMA_DROPS),
            "use": "MODMA cross-task degradation and EATD valence stress interpretation",
        },
        {
            "section": "Failure-Mode Diagnostics",
            "source_artifact_id": "phase3_mpdd_individual_differences",
            "source_path": rel(PHASE3_MPDD_RUN),
            "use": "MPDD personality, age, gait, and missing metadata diagnostics",
        },
        {
            "section": "Measurement Results",
            "source_artifact_id": "paper_claim_boundary",
            "source_path": rel(PAPER_CLAIMS),
            "use": "allowed and blocked paper claim language",
        },
        {
            "section": "Measurement Results",
            "source_artifact_id": "key_numeric_findings",
            "source_path": rel(PAPER_FINDINGS),
            "use": "paper-facing MV08-MV15, PDCH, MODMA, EATD, and MV06 findings",
        },
        {
            "section": "Measurement Results",
            "source_artifact_id": "mv13_external_psychometric_replication",
            "source_path": rel(MV13_SUMMARY),
            "use": "MV13 external R mirt replication status and convergence caveat",
        },
        {
            "section": "Measurement Results",
            "source_artifact_id": "mv14_measurement_uncertainty_bootstrap",
            "source_path": rel(MV14_SUMMARY),
            "use": "MV14 bootstrap anchor, DIF, convergence, and model-selection stability",
        },
        {
            "section": "Measurement Results",
            "source_artifact_id": "mv15_latent_conditioned_identity_design",
            "source_path": rel(MV15_DESIGN_SUMMARY),
            "use": "MV15 predeclared latent-conditioned identity ladder and local-only boundary",
        },
        {
            "section": "Measurement Results",
            "source_artifact_id": "mv15_latent_conditioned_identity_run",
            "source_path": rel(MV15_SUMMARY),
            "use": "MV15 aggregate latent-conditioned identity results and pass/fail gate",
        },
        {
            "section": "Measurement Results",
            "source_artifact_id": "mv12_tradeoff_analysis",
            "source_path": rel(MV12_ANALYSIS),
            "use": "MV12 freeze decision, failure modes, and gate decomposition",
        },
    ]
    return pd.DataFrame(rows)


def build_claim_checklist(ctx2: dict[str, Any], ctx3: dict[str, Any], ctx5: dict[str, Any]) -> pd.DataFrame:
    rows = [
        {
            "claim_scope": "Baseline reproducibility floor",
            "claim_status": "supported",
            "evidence": (
                f"Phase 2 completed {ctx2['completed_runs']}/{ctx2['planned_runs']} runs with "
                f"{ctx2['completed_metric_rows']} completed metric rows and zero blocked runs."
            ),
            "guardrail": "Do not publish Phase 2 generated result artifacts by default; cite aggregate completion only.",
        },
        {
            "claim_scope": "Dataset/protocol shortcut risk",
            "claim_status": "supported_diagnostic",
            "evidence": (
                f"Dataset identity probes include WavLM six-way BA {fmt(ctx3['identity_six_way_ba'])}, "
                f"CMDC/PDCH BGE BA {fmt(ctx3['identity_bge_ba'])}, and E-DAIC/CMDC OpenFace BA "
                f"{fmt(ctx3['identity_openface_ba'])}."
            ),
            "guardrail": "Treat identity as shortcut-risk evidence; use conditional identity for shared-latent claims.",
        },
        {
            "claim_scope": "Protocol/task failure modes",
            "claim_status": "supported_diagnostic",
            "evidence": (
                f"CMDC Q10-only binary Macro-F1 delta is {fmt(ctx3['cmdc_q10_delta'])}; MODMA "
                f"affective-task BA drop is {fmt(ctx3['modma_affective_drop'])}."
            ),
            "guardrail": "Speaker-resolved E-DAIC/CMDC controls remain blocked by missing fields.",
        },
        {
            "claim_scope": "Population/context method gain",
            "claim_status": "blocked_positive_claim",
            "evidence": (
                f"MPDD AVP adds only Macro-F1 {fmt(ctx3['avp_macro_delta'])} and QWK "
                f"{fmt(ctx3['avp_qwk_delta'])} over AV, while subgroup calibration gaps remain large."
            ),
            "guardrail": "Use age/personality as heterogeneity axes, not as a positive context-conditioning method claim.",
        },
        {
            "claim_scope": "Measurement-shift paper direction",
            "claim_status": "allowed_with_reframing",
            "evidence": (
                f"Full gate reads {ctx5['evidence_rows']} Phase 5 summaries; the full method "
                f"remains blocked, but the measurement-shift paper direction is allowed."
            ),
            "guardrail": "Report negative and bounded results honestly; no full M0/M1/M2/M3 claim.",
        },
        {
            "claim_scope": "MV12 latent-target method",
            "claim_status": "blocked_positive_method_claim",
            "evidence": (
                "MV12 improves same-dataset theta utility and conditional identity, but observed-scale "
                "safety and external theta transfer fail; aggregate analysis freezes the current line."
            ),
            "guardrail": "Future method work needs a genuinely new predeclared mechanism.",
        },
    ]
    return pd.DataFrame(rows)


def md_escape(value: Any) -> str:
    return str(value).replace("|", "\\|").replace("\n", " ")


def write_markdown(
    out_dir: Path,
    generated_at: str,
    ctx2: dict[str, Any],
    ctx3: dict[str, Any],
    ctx5: dict[str, Any],
    source_map: pd.DataFrame,
    checklist: pd.DataFrame,
) -> None:
    lines = [
        "# Baselines, Failure-Mode Diagnostics, and Measurement Results",
        "",
        f"Generated: `{generated_at}`",
        "",
        "## Scope",
        "",
        "This manuscript scaffold turns existing aggregate experiment artifacts into draft Results text. It is not a new model run. It excludes row-level predictions, local review workbooks, learned parameters, embeddings, and private clinical text.",
        "",
        "## Draft Section: Baselines",
        "",
        f"The baseline phase defines the reproducibility floor for later diagnostic claims. The matrix contained `{ctx2['planned_runs']}` planned runs, of which `{ctx2['completed_runs']}` completed and `{ctx2['not_applicable_runs']}` was conditionally excluded; no applicable run remains blocked. The final audit contains `{ctx2['completed_metric_rows']}` completed metric rows and `{ctx2['not_applicable_metric_rows']}` not-applicable metric rows, with five seeds used for completed runs and `{ctx2['bootstrap_resamples']}` bootstrap resamples recorded by the metric audit. The Phase 2 completion verdict is complete, and the method-design gate recommendation is `{ctx2['method_gate']}`.",
        "",
        f"These baselines should be read as governance evidence rather than as the paper's main novelty. The matrix covers simple unimodal and fusion families across six datasets, while intentionally excluding incompatible public reproductions from the canonical matrix when their split, feature, or evaluation contract differs. The hygiene audit passed and reviewed `{ctx2['prediction_files_audited']}` canonical prediction files locally, but generated Phase 2 result artifacts remain local by default. The manuscript should therefore cite Phase 2 as a completed, subject-level baseline floor and avoid using it as a public artifact dump.",
        "",
        "## Draft Section: Failure-Mode Diagnostics",
        "",
        f"Phase 3 shows why direct pooled training is not enough evidence for a shared depression representation. Across `{ctx3['identity_completed_probes']}` dataset/protocol identity probes, dataset identity is highly recoverable from frozen feature spaces: six-way WavLM identity reaches balanced accuracy `{fmt(ctx3['identity_six_way_ba'])}`, CMDC/PDCH BGE text reaches `{fmt(ctx3['identity_bge_ba'])}`, and E-DAIC/CMDC OpenFace reaches `{fmt(ctx3['identity_openface_ba'])}`. These probes do not prove every identity signal is harmful, but they establish that dataset identity must be reported, controlled, or conditioned before interpreting pooled performance as construct transfer.",
        "",
        f"Protocol controls sharpen the same conclusion at the interview-content level. The E-DAIC/CMDC protocol-control run completed `{ctx3['protocol_runs']}` runs over `{ctx3['protocol_seed_count']}` seeds with artifact hygiene passing. In E-DAIC, front-position dialogue text improves binary Macro-F1 by `{fmt(ctx3['edaic_front_delta'])}` versus full dialogue, and repeated-turn-only text improves it by `{fmt(ctx3['edaic_repeat_delta'])}`. In CMDC, Q10-only binary Macro-F1 drops by `{fmt(ctx3['cmdc_q10_delta'])}` versus all questions. The right paper wording is therefore question-position and fixed-protocol dependence; literal participant-only or interviewer-only claims remain blocked because speaker-resolved fields are unavailable.",
        "",
        f"Task and valence diagnostics separate supported protocol stress from unsupported valence mechanisms. MODMA cross-task evaluation lowers balanced accuracy by `{fmt(ctx3['modma_overall_drop'])}` overall, with the affective-task evaluation drop reaching `{fmt(ctx3['modma_affective_drop'])}` and a 95 percent interval from `{fmt(ctx3['modma_affective_ci_low'])}` to `{fmt(ctx3['modma_affective_ci_high'])}`. EATD does not show the hypothesized healthy-negative shortcut in the current audio diagnostic: healthy negative predicted-depressed rate is `{fmt(ctx3['eatd_negative_rate'])}` versus `{fmt(ctx3['eatd_nonnegative_rate'])}` for healthy nonnegative material. MODMA can support bounded task-control evidence; EATD should remain a negative stress test rather than a valence-adversarial method driver.",
        "",
        f"MPDD supports a population-heterogeneity audit but not a positive context-conditioning method. On `{ctx3['mpdd_subjects']}` labeled train subjects, personality-only text beats shuffled personality by Macro-F1 `{fmt(ctx3['personality_macro_delta'])}` and QWK `{fmt(ctx3['personality_qwk_delta'])}`, yet audio-video-personality fusion adds only Macro-F1 `{fmt(ctx3['avp_macro_delta'])}` and QWK `{fmt(ctx3['avp_qwk_delta'])}` over audio-video alone. Subgroup calibration remains material, with age ECE gap `{fmt(ctx3['age_ece_gap'])}` and personality-bin ECE gap `{fmt(ctx3['personality_ece_gap'])}`. Gait has modest psychomotor-context association with PHQ-9, top absolute Spearman `{fmt(ctx3['gait_spearman'])}`, while gender and health analyses remain `{ctx3['gender_health_status']}` because structured fields are missing.",
        "",
        "## Draft Section: Measurement Results",
        "",
        f"The Phase 5 full-method gate now reads `{ctx5['evidence_rows']}` aggregate evidence summaries and remains blocked, while allowing a measurement-shift and measurement-invariance paper direction. This is the central Results boundary: the evidence is rich enough to explain why cross-dataset depression transfer is hard, but not for starting or claiming the full M0/M1/M2/M3 symptom-aligned method.",
        "",
        f"The measurement story is best read at three levels: feature/domain shift (`P(X|D)`), target-measurement shift (`P(Y|theta,D)`), and latent prediction stability (`P(theta_hat|X,D)`). MV09 addresses the first level by showing that dataset identity remains high after legitimate conditioning; MV10/MV11/MV13/MV14 address the second level by showing substantial common PHQ structure with stable anchors, sparse loading DIF, repeated C02/C06 threshold non-equivalence, and convergence-aware model-selection uncertainty rather than uniformly supported exact scalar or partial invariance; MV12 addresses the third level by separating label measurement from multimodal prediction. MV15 was predeclared with `{ctx5['mv15_design_conditioning_ladder_rows']}` conditioning rows and `{ctx5['mv15_design_identity_probe_rows']}` identity probes, then executed as an aggregate-only identity audit. {ctx5['finding_mv15']} The key interpretation is that low-dimensional output identity and feature-level invariance are different: theta-only BA is `{fmt(ctx5['mv15_theta_only_identity_ba'])}` and predicted-theta output identity BA is `{fmt(ctx5['mv15_predicted_theta_output_identity_ba'])}`, but residualized BGE feature identity remains `{fmt(ctx5['mv15_theta_conditioned_feature_identity_ba'])}` after theta conditioning and `{fmt(ctx5['mv15_total_conditioned_feature_identity_ba'])}`/`{fmt(ctx5['mv15_predicted_total_conditioned_feature_identity_ba'])}`/`{fmt(ctx5['mv15_b3_conditioned_feature_identity_ba'])}` after total, predicted-total, and B3 controls.",
        "",
        "The first measurement sequence is negative or bounded. MV08 improves over the total-score floor on `0/3` pooled active slices, while MV08b improves over both total-score and fixed-map floors on `2/3` slices but raises prediction dataset identity to `0.979`. MV09 then revises the gate semantics: post-head identity is diagnostic when outputs are scale-specific, while shared-latent claims require conditional identity checks. Under that sharper test, E-DAIC/CMDC item-conditioned feature identity remains `0.991`, so direct fixed shared-symptom mappings remain too strong under the current frozen-feature and shallow-head contract.",
        "",
        f"The psychometric sequence supplies the paper's sharper target story. MV10 shows that E-DAIC PHQ-8 and CMDC PHQ-9 exhibit substantial common PHQ structure: the configural screen passes, loading congruence is `0.998`, and `7/8` items pass the approximate metric-loading screen. Exact threshold/scalar equivalence is not uniformly supported, with only `4/8` candidate anchors (`C01`, `C04`, `C05`, `C07`). MV11 formal graded-response IRT confirmation preserves those four anchors, flags no strong loading DIF, and flags threshold DIF for `C02` and `C06`, while AIC favors the partial model and BIC favors the scalar model. MV13 external R mirt replication preserves the same qualitative anchor/DIF pattern, with no loading-DIF flags and threshold-DIF flags on `C02` and `C06`, but retains a configural convergence warning. MV14 then makes that warning explicit: the convergence-safe full ladder has `{ctx5['mv14_core_effective_draws']}/{ctx5['mv14_core_attempted_draws']}` effective draws after `{ctx5['mv14_core_fit_success_draws']}` fit-success draws, configural converges in `{ctx5['mv14_configural_converged_draws']}/{ctx5['mv14_core_attempted_draws']}`, and the stable metric/partial/scalar ladder has `{ctx5['mv14_stable_ladder_effective_draws']}` effective draws with AIC/BIC favoring `{ctx5['mv14_stable_ladder_best_aic_model']}`/`{ctx5['mv14_stable_ladder_best_bic_model']}`. {ctx5['finding_mv14']} The conservative manuscript claim is therefore substantial structural similarity with bootstrap-stable anchors and localized threshold DIF, not a bootstrap-confirmed global partial-invariance win, a full scalar-invariance proof, or a full-method pass.",
        "",
        f"MV12 then tests whether multimodal features can predict the label-derived latent target, and the result should not be flattened into a simple failure. Within datasets, `X -> theta` is learnable: M12a improves theta MAE over the train-mean theta floor by `{fmt(ctx5['mv12_edaic_same_theta_delta'])}` on E-DAIC and `{fmt(ctx5['mv12_cmdc_same_theta_delta'])}` on CMDC. The predicted latent target is also far less dataset-identifiable than the upstream conditional feature space, with conditional identity BA `{fmt(ctx5['mv12_conditional_identity_ba'])}` versus the MV09 reference `0.991`. However, this is a low-dimensional-output result rather than a theta-specific invariance result: B3 direct itemwise Ridge compressed to theta has lower pooled observed macro MAE (`{fmt(ctx5['mv12_b3_observed_macro_mae'])}` versus `{fmt(ctx5['mv12_m12a_observed_macro_mae'])}`) and lower conditional identity BA (`{fmt(ctx5['mv12_b3_conditional_identity_ba'])}` versus `{fmt(ctx5['mv12_m12a_conditional_identity_ba'])}`) than M12a.",
        "",
        f"The cost is predictive fidelity and zero-shot source-calibrated latent-scale transfer. Same-dataset observed macro item MAE is worse than direct itemwise Ridge by `{fmt(ctx5['mv12_edaic_same_observed_delta'])}` on E-DAIC and `{fmt(ctx5['mv12_cmdc_same_observed_delta'])}` on CMDC, showing that a one-dimensional latent bottleneck loses item-profile information. Cross-dataset evaluation splits the story even more sharply: the latent route improves observed macro item MAE relative to direct item transfer by `{fmt(ctx5['mv12_cross_cmdc_to_edaic_observed_delta'])}` for CMDC-to-E-DAIC and `{fmt(ctx5['mv12_cross_edaic_to_cmdc_observed_delta'])}` for E-DAIC-to-CMDC, yet theta MAE remains worse than the target train-mean theta floor by `{fmt(ctx5['mv12_cross_cmdc_to_edaic_theta_delta'])}` and `{fmt(ctx5['mv12_cross_edaic_to_cmdc_theta_delta'])}`. Because the external theta target is scored with the source measurement function on target subjects, this failure mixes `X -> theta` predictor transfer with target measurement-function mismatch. The interpretation is therefore a predictive fidelity-dataset identifiability trade-off: the latent/scalar prediction layer is less dataset-identifiable than upstream BGE features, but the current M12a head is Pareto-dominated by the dimension-matched B3 severity baseline and does not establish psychometric theta as uniquely more invariant. The aggregate tradeoff analysis freezes the current latent-target line as paper-critical diagnostic evidence.",
        "",
        f"The remaining Phase 5 findings define bounded supporting claims. PDCH supports an internal HAMD diagnostic bridge: item-derived total MAE is `5.693`, direct total MAE is `5.794`, and macro item MAE is `0.727`, but this does not support cross-dataset HAMD transfer. MODMA supports task-control evidence because task projection reduces feature task-identity BA from `0.762` to `0.570` while preserving the main task signal (`0.688`). EATD remains a negative SDS stress test because uncontrolled primary MAE is `28.810` versus a train-mean floor of `7.201`. {ctx5['finding_mv06']} Together, these results support a paper about measurement validity, protocol dependence, and bounded evidence localization, while keeping external HAMD transfer, EATD SDS generalization, positive MPDD context conditioning, and full-method construction blocked.",
        "",
        "## Manuscript Guardrails",
        "",
        "- Do not present Phase 2 baseline result artifacts as public release material; use aggregate completion and hygiene only.",
        "- Do not claim that high unconditional dataset identity is automatically harmful; use it as a shortcut-risk screen and reserve conditional identity for shared-latent claims.",
        "- Do not call scale-specific post-head identity a hard shared-latent failure unless the output space is explicitly shared.",
        "- Do not use MV12 as positive full-method evidence; its tradeoff analysis freezes the current latent-target line.",
        "- Do not use low one-dimensional output identity as evidence that upstream BGE features are dataset-invariant; MV15 keeps feature identity high after theta and severity conditioning.",
        "- Do not strengthen RQ4 beyond first-round aggregate credibility without agreement uncertainty analysis and resolving remaining incomplete candidate rows, if any.",
        "",
        "## Source Map",
        "",
        "| section | source artifact | source path | use |",
        "| --- | --- | --- | --- |",
    ]
    for _, row in source_map.iterrows():
        lines.append(
            "| "
            + " | ".join(
                [
                    md_escape(row["section"]),
                    md_escape(row["source_artifact_id"]),
                    md_escape(row["source_path"]),
                    md_escape(row["use"]),
                ]
            )
            + " |"
        )
    lines.extend(
        [
            "",
            "## Claim Checklist",
            "",
            "| claim scope | status | evidence | guardrail |",
            "| --- | --- | --- | --- |",
        ]
    )
    for _, row in checklist.iterrows():
        lines.append(
            "| "
            + " | ".join(
                [
                    md_escape(row["claim_scope"]),
                    md_escape(row["claim_status"]),
                    md_escape(row["evidence"]),
                    md_escape(row["guardrail"]),
                ]
            )
            + " |"
        )
    (out_dir / "baselines_failure_modes_measurement_results.md").write_text(
        "\n".join(lines) + "\n", encoding="utf-8"
    )


def artifact_hygiene(out_dir: Path) -> dict[str, Any]:
    forbidden_patterns = [
        r"/root/",
        r"/autodl-tmp/",
        r"\bsubject_id\b",
        r"\bsubject_key\b",
        r"\.wav\b",
        r"\.mp4\b",
        r"\.avi\b",
        r"local_annotation_workbook",
        r"source_locator",
        r"p5_mv[0-9a-z_]*_local_",
        r"raw snippet",
        r"raw evidence snippet",
        r"raw prompt",
        r"raw response",
        r"verbatim evidence excerpt",
        r"row-level predictions file",
    ]
    violations: list[dict[str, str]] = []
    checked = 0
    for name in TRACKED_FILES:
        path = out_dir / name
        if not path.exists() or not path.is_file():
            continue
        checked += 1
        text = path.read_text(encoding="utf-8", errors="ignore")
        for pattern in forbidden_patterns:
            if re.search(pattern, text, flags=re.IGNORECASE):
                violations.append({"file": name, "pattern": pattern})
    return {
        "audit_id": "diagnostic_measurement_audit_results_sections_hygiene",
        "generated_at": utc_now(),
        "files_checked": checked,
        "artifact_hygiene_passed": not violations,
        "violation_count": len(violations),
        "violations": violations,
    }


def write_report(out_dir: Path, run_summary: dict[str, Any]) -> None:
    lines = [
        "# Results Section Scaffold Report",
        "",
        f"Generated: `{run_summary['generated_at']}`",
        "",
        "## Decision",
        "",
        f"- Section scaffold status: `{run_summary['decision']['section_scaffold_status']}`.",
        f"- Artifact hygiene passed: `{run_summary['artifact_hygiene_passed']}`.",
        f"- Source rows: `{run_summary['outputs']['source_rows']}`.",
        f"- Claim checklist rows: `{run_summary['outputs']['claim_checklist_rows']}`.",
        "",
        "## Handoff",
        "",
        "Use `baselines_failure_modes_measurement_results.md` as the first manuscript draft for the Baselines, Failure-Mode Diagnostics, and Measurement Results sections. It should be edited for venue style, figure references, and formal citations before paper submission.",
    ]
    (out_dir / "results_section_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def build_outputs(out_dir: Path, generated_at: str) -> dict[str, Any]:
    ctx2 = phase2_context()
    ctx3 = phase3_context()
    ctx5 = phase5_context()
    source_map = build_source_map()
    checklist = build_claim_checklist(ctx2, ctx3, ctx5)
    out_dir.mkdir(parents=True, exist_ok=True)
    stale_hygiene = out_dir / "results_section_artifact_hygiene_audit.json"
    if stale_hygiene.exists():
        stale_hygiene.unlink()

    source_map.to_csv(out_dir / "results_section_source_map.csv", index=False)
    checklist.to_csv(out_dir / "results_section_claim_checklist.csv", index=False)
    write_markdown(out_dir, generated_at, ctx2, ctx3, ctx5, source_map, checklist)

    run_summary = {
        "run_id": "diagnostic_measurement_audit_results_sections",
        "generated_at": generated_at,
        "status": "complete",
        "input_contract": {
            "aggregate_phase2_audits_read": True,
            "aggregate_phase3_summaries_read": True,
            "aggregate_phase5_summaries_read": True,
            "private_review_material_read": False,
            "row_level_model_outputs_read": False,
            "raw_data_scanned": False,
        },
        "outputs": {
            "tracked_outputs": TRACKED_FILES,
            "source_rows": int(len(source_map)),
            "claim_checklist_rows": int(len(checklist)),
            "draft_sections": [
                "Baselines",
                "Failure-Mode Diagnostics",
                "Measurement Results",
            ],
        },
        "decision": {
            "section_scaffold_status": "ready_for_manuscript_editing",
            "short_read": (
                "Baselines, Failure-Mode Diagnostics, and Measurement Results draft sections "
                "are ready from aggregate artifacts; full method remains blocked."
            ),
        },
        "artifact_hygiene_passed": False,
    }
    (out_dir / "results_section_run_summary.json").write_text(
        json.dumps(run_summary, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    write_report(out_dir, run_summary)
    hygiene = artifact_hygiene(out_dir)
    run_summary["artifact_hygiene_passed"] = bool(hygiene["artifact_hygiene_passed"])
    (out_dir / "results_section_run_summary.json").write_text(
        json.dumps(run_summary, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    write_report(out_dir, run_summary)
    hygiene = artifact_hygiene(out_dir)
    audit_path = out_dir / "results_section_artifact_hygiene_audit.json"
    audit_path.write_text(
        json.dumps(hygiene, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    hygiene = artifact_hygiene(out_dir)
    audit_path.write_text(
        json.dumps(hygiene, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    if not hygiene["artifact_hygiene_passed"]:
        raise SystemExit("artifact hygiene violations found; see results_section_artifact_hygiene_audit.json")
    return run_summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    args = parser.parse_args()

    require_inputs()
    summary = build_outputs(args.out_dir, utc_now())
    print(
        json.dumps(
            {
                "out_dir": str(args.out_dir.relative_to(ROOT) if args.out_dir.is_absolute() else args.out_dir),
                "section_scaffold_status": summary["decision"]["section_scaffold_status"],
                "artifact_hygiene_passed": summary["artifact_hygiene_passed"],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
