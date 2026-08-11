#!/usr/bin/env python3
"""Predeclare the MV12 two-stage latent-target experiment.

This script is a design contract, not a trainer. It separates label
measurement from multimodal prediction: first define a local-only Y_to_theta
psychometric target from MV11, then define audited X_to_theta predictors,
direct X_to_Y floors, conditional identity probes, external transfer checks,
and artifact boundaries. It reads only aggregate Phase 5 artifacts.
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
DEFAULT_OUT_DIR = PHASE5_DIR / "p5_mv12_two_stage_latent_target_design"

MV07_READINESS_DIR = PHASE5_DIR / "p5_mv07_shared_feature_contract_readiness"
MV07_DIR = PHASE5_DIR / "p5_mv07_aligned_bge_shared_symptom"
MV07B_DIR = PHASE5_DIR / "p5_mv07b_bge_identity_projection"
MV07C_DIR = PHASE5_DIR / "p5_mv07c_bge_total_anchor"
MV08B_DIR = PHASE5_DIR / "p5_mv08b_total_anchored_residual_measurement"
MV09_DIR = PHASE5_DIR / "p5_mv09_conditional_identity_audit"
MV10_DIR = PHASE5_DIR / "p5_mv10_psychometric_invariance_baseline"
MV11_DIR = PHASE5_DIR / "p5_mv11_formal_psychometric_confirmation"
FULL_GATE_DIR = PHASE5_DIR / "full_method_gate_audit"

TRACKED_FILES = [
    "artifact_hygiene_audit.json",
    "identity_transfer_gate_contract.csv",
    "implementation_queue.csv",
    "local_only_boundary_contract.csv",
    "method_source_refs.csv",
    "model_ladder_contract.csv",
    "pass_fail_gate_contract.csv",
    "report.md",
    "run_summary.json",
    "source_evidence_summary.csv",
    "target_generation_contract.csv",
]

METHOD_SOURCE_REFS = [
    {
        "source_id": "samejima_graded_response_model",
        "url": "https://www.psychometricsociety.org/sites/main/files/file-attachments/mn17.pdf",
        "source_type": "primary_method_monograph",
        "use_in_mv12": "Use MV11 graded-response measurement as the label-only source for local Y_to_theta targets.",
        "key_takeaway": "Ordinal symptom item responses can be modeled through a latent severity variable and ordered cutpoints.",
    },
    {
        "source_id": "phq9_measurement_invariance_helius",
        "url": "https://pmc.ncbi.nlm.nih.gov/articles/PMC5655879/",
        "source_type": "measurement_invariance_paper",
        "use_in_mv12": "Frame PHQ item comparisons as invariance and DIF questions before multimodal prediction.",
        "key_takeaway": "PHQ comparisons across groups require explicit configural, metric, and scalar checks.",
    },
    {
        "source_id": "irt_likelihood_ratio_dif",
        "url": "https://www.frontiersin.org/journals/education/articles/10.3389/feduc.2017.00051/full",
        "source_type": "method_reference",
        "use_in_mv12": "Carry MV11 DIF flags into target construction and sensitivity analyses.",
        "key_takeaway": "Item-level DIF testing distinguishes shared measurement anchors from group-specific item behavior.",
    },
    {
        "source_id": "cross_scale_linking_jclinepi_2026",
        "url": "https://www.jclinepi.com/article/S0895-4356(26)00082-X/abstract",
        "source_type": "scale_linking_reference",
        "use_in_mv12": "Motivate evaluating theta_to_observed-scale mapping separately from X_to_theta prediction.",
        "key_takeaway": "Depression scales can correlate while still requiring formal linking because systematic measurement differences remain.",
    },
]


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(path)
    return json.loads(path.read_text(encoding="utf-8"))


def read_csv(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(path)
    return pd.read_csv(path)


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


def bool_count(series: pd.Series) -> int:
    return int(series.astype(str).str.lower().isin({"true", "1", "yes"}).sum())


def source_evidence_summary() -> pd.DataFrame:
    mv07_readiness = read_json(MV07_READINESS_DIR / "run_summary.json")
    mv07 = read_json(MV07_DIR / "run_summary.json")
    mv07b = read_json(MV07B_DIR / "run_summary.json")
    mv07c = read_json(MV07C_DIR / "run_summary.json")
    mv08b = read_json(MV08B_DIR / "run_summary.json")
    mv09 = read_json(MV09_DIR / "run_summary.json")
    mv10 = read_json(MV10_DIR / "run_summary.json")
    mv11 = read_json(MV11_DIR / "run_summary.json")
    anchors = read_csv(MV11_DIR / "anchor_confirmation_summary.csv")
    mv11_gate = read_csv(MV11_DIR / "gate_recommendations.csv")
    next_actions = read_csv(FULL_GATE_DIR / "next_action_queue.csv")
    full_gate = read_json(FULL_GATE_DIR / "run_summary.json")

    mv07_v = mv07.get("verdict") or {}
    mv07b_v = mv07b.get("verdict") or {}
    mv07c_v = mv07c.get("verdict") or {}
    mv08b_v = mv08b.get("verdict") or {}
    mv09_v = mv09.get("verdict") or {}
    mv10_v = mv10.get("verdict") or {}
    mv11_v = mv11.get("verdict") or {}
    top_action = next_actions.sort_values("rank").iloc[0].to_dict()
    mv11_target_row = mv11_gate[mv11_gate["recommendation_id"] == "two_stage_latent_target"].iloc[0].to_dict()

    confirmed_anchor_ids = anchors.loc[anchors["mv10_anchor_confirmed"].astype(str).str.lower() == "true", "construct_id"]
    threshold_dif_ids = anchors.loc[anchors["threshold_dif_flag"].astype(str).str.lower() == "true", "construct_id"]
    loading_dif_ids = anchors.loc[anchors["loading_dif_flag"].astype(str).str.lower() == "true", "construct_id"]
    stable_non_mv10_ids = anchors[
        (anchors["mv10_anchor_confirmed"].astype(str).str.lower() != "true")
        & (anchors["loading_dif_flag"].astype(str).str.lower() != "true")
        & (anchors["threshold_dif_flag"].astype(str).str.lower() != "true")
    ]["construct_id"]

    rows = [
        {
            "source_id": "MV11_formal_label_measurement",
            "artifact": rel(MV11_DIR / "run_summary.json"),
            "status": mv11_v.get("status"),
            "observation": (
                f"confirmed_mv10_anchors={mv11_v.get('confirmed_mv10_anchor_items')}; "
                f"loading_DIF_flags={mv11_v.get('loading_dif_flagged_items')}; "
                f"threshold_DIF_flags={mv11_v.get('threshold_dif_flagged_items')}; "
                f"AIC_BIC_split={mv11_v.get('core_model_aic_bic_split')}"
            ),
            "implication_for_mv12": "Use MV11 as the label-only measurement target source, with a BIC caveat and no public subject scores or fitted parameters.",
        },
        {
            "source_id": "MV11_anchor_map",
            "artifact": rel(MV11_DIR / "anchor_confirmation_summary.csv"),
            "status": "partial_anchor_map_confirmed",
            "observation": (
                f"primary_anchors={';'.join(confirmed_anchor_ids)}; "
                f"threshold_DIF_items={';'.join(threshold_dif_ids)}; "
                f"loading_DIF_items={';'.join(loading_dif_ids) or 'none'}; "
                f"sensitivity_candidates={';'.join(stable_non_mv10_ids) or 'none'}"
            ),
            "implication_for_mv12": "Primary target uses C01/C04/C05/C07 anchors; C02/C06 keep threshold-free/DIF-aware treatment; C03/C08 are sensitivity-only unless predeclared otherwise.",
        },
        {
            "source_id": "MV11_gate_recommendation",
            "artifact": rel(MV11_DIR / "gate_recommendations.csv"),
            "status": mv11_target_row.get("status"),
            "observation": mv11_target_row.get("evidence"),
            "implication_for_mv12": mv11_target_row.get("recommendation"),
        },
        {
            "source_id": "MV09_conditional_identity",
            "artifact": rel(MV09_DIR / "run_summary.json"),
            "status": mv09_v.get("status"),
            "observation": (
                f"E-DAIC_CMDC_raw_BA={fmt(mv09_v.get('edaic_cmdc_raw_ba'))}; "
                f"E-DAIC_CMDC_item_conditioned_BA={fmt(mv09_v.get('edaic_cmdc_item_residualized_ba'))}; "
                f"CMDC_PDCH_severity_conditioned_BA={fmt(mv09_v.get('cmdc_pdch_severity_residualized_ba'))}; "
                f"three_way_severity_conditioned_BA={fmt(mv09_v.get('three_way_severity_residualized_ba'))}"
            ),
            "implication_for_mv12": "Use conditional identity as the shared-latent gate; post-head scale-specific prediction identity stays diagnostic only.",
        },
        {
            "source_id": "MV07_aligned_BGE_negative",
            "artifact": rel(MV07_DIR / "run_summary.json"),
            "status": mv07_v.get("pass_rule_status"),
            "observation": "aligned BGE direct itemwise heads did not consistently beat total-allocation floors; feature BA=1.000 and prediction BA=0.980.",
            "implication_for_mv12": "Direct X_to_Y BGE heads stay mandatory baselines, not the target method.",
        },
        {
            "source_id": "MV07b_identity_projection_tradeoff",
            "artifact": rel(MV07B_DIR / "run_summary.json"),
            "status": mv07b_v.get("pass_rule_status"),
            "observation": (
                f"best_feature_BA_after={fmt(mv07b_v.get('best_binary_feature_identity_ba_after'))}; "
                f"best_prediction_BA_after={fmt(mv07b_v.get('best_binary_prediction_identity_ba_after'))}; "
                f"CMDC_delta_vs_total_allocation={fmt(mv07b_v.get('best_pooled_cmdc_delta_vs_total_alloc'))}"
            ),
            "implication_for_mv12": "Identity projection may be a secondary X_to_theta variant only after the unprojected latent baseline and floors are reported.",
        },
        {
            "source_id": "MV07c_total_anchor_tradeoff",
            "artifact": rel(MV07C_DIR / "run_summary.json"),
            "status": mv07c_v.get("pass_rule_status"),
            "observation": (
                f"prediction_BA={fmt(mv07c_v.get('prediction_identity_ba'))}; "
                f"E-DAIC_delta_vs_raw_total={fmt(mv07c_v.get('pooled_edaic_delta_vs_raw_total_alloc'))}; "
                f"CMDC_delta_vs_raw_total={fmt(mv07c_v.get('pooled_cmdc_delta_vs_raw_total_alloc'))}"
            ),
            "implication_for_mv12": "Total anchoring informs direct-floor comparisons, but MV12 must predict the psychometric latent target rather than retune itemwise heads.",
        },
        {
            "source_id": "MV08b_negative_head_sequence",
            "artifact": rel(MV08B_DIR / "run_summary.json"),
            "status": mv08b_v.get("pass_rule_status"),
            "observation": (
                f"M2b_beats_both_floors_slices={mv08b_v.get('pooled_m2b_improved_vs_both_floor_slices')}/"
                f"{mv08b_v.get('pooled_active_slices')}; prediction_BA={fmt(mv08b_v.get('prediction_identity_ba_m2b'))}"
            ),
            "implication_for_mv12": "Do not create MV08c; change the target to a separately fitted measurement latent variable.",
        },
        {
            "source_id": "MV10_label_screen_context",
            "artifact": rel(MV10_DIR / "run_summary.json"),
            "status": mv10_v.get("status"),
            "observation": (
                f"loading_congruence={fmt(mv10_v.get('loading_congruence'))}; "
                f"metric_items={mv10_v.get('metric_invariant_items')}/8; "
                f"threshold_items={mv10_v.get('threshold_invariant_items')}/8"
            ),
            "implication_for_mv12": "MV10 supplies the approximate screen that MV11 formalizes; keep both in manuscript context.",
        },
        {
            "source_id": "full_method_gate_next_action",
            "artifact": rel(FULL_GATE_DIR / "next_action_queue.csv"),
            "status": str(top_action.get("action_id")),
            "observation": (
                f"full_gate_status={full_gate.get('gate_status')}; "
                f"full_method_allowed={full_gate.get('full_method_allowed')}; "
                f"top_action={top_action.get('action_id')}"
            ),
            "implication_for_mv12": "MV12 can close the predeclaration gap only; full method stays blocked until the actual X_to_theta run passes.",
        },
    ]
    return pd.DataFrame(rows)


def target_generation_contract() -> pd.DataFrame:
    rows = [
        {
            "stage_id": "Y_THETA_PRIMARY_MEASUREMENT_TARGET",
            "scope": "E-DAIC PHQ-8 and CMDC PHQ-9 shared C01-C08 labels",
            "input_artifacts": "MV11 aggregate anchor map plus manifest-governed item labels used locally by the future runner",
            "target_policy": "Fit a train-fold label-only graded-response measurement model; primary anchors are C01,C04,C05,C07.",
            "leakage_boundary": "For predictor training, fit the measurement model only inside train folds; evaluation labels may be used only to score held-out theta agreement and theta_to_observed reconstruction.",
            "tracked_output_policy": "Export aggregate target coverage, fold reliability, distribution bins, and reconstruction metrics only.",
            "local_only_policy": "Local-only: fitted measurement parameters, per-subject theta targets, posterior summaries, quadrature diagnostics, and row diagnostics.",
            "pass_condition": "Train-fold target generation succeeds with confirmed anchors and no public score or parameter export.",
        },
        {
            "stage_id": "DIF_AWARE_ITEM_POLICY",
            "scope": "PHQ C01-C08 item response functions",
            "input_artifacts": "MV11 anchor_confirmation_summary",
            "target_policy": "Keep C02 and C06 threshold-DIF-aware; no loading-DIF item is primary-blocking because MV11 flags zero strong loading DIF items.",
            "leakage_boundary": "DIF decisions are fixed from MV11 before the X_to_theta run; no post-hoc freeing based on predictor error.",
            "tracked_output_policy": "Export aggregate counts of anchor, threshold-free, and sensitivity items.",
            "local_only_policy": "Do not export item threshold values, discrimination estimates, or subject residual traces.",
            "pass_condition": "Target contract uses the same predeclared item roles across seeds and folds.",
        },
        {
            "stage_id": "SENSITIVITY_TARGETS",
            "scope": "Stable non-MV10 items C03 and C08",
            "input_artifacts": "MV11 item DIF diagnostics",
            "target_policy": "Use C03/C08 as sensitivity-only target variants, not as primary anchors, unless a later predeclared contract upgrades them.",
            "leakage_boundary": "Sensitivity analyses cannot choose the primary model after seeing held-out X_to_theta performance.",
            "tracked_output_policy": "Export aggregate sensitivity deltas versus the primary MV11 target.",
            "local_only_policy": "Sensitivity target scores and fitted parameters remain local-only.",
            "pass_condition": "Primary conclusion is unchanged or explicitly downgraded if sensitivity targets conflict.",
        },
        {
            "stage_id": "THETA_TO_OBSERVED_MAPPING",
            "scope": "Dataset-specific PHQ observed item and total reconstructions",
            "input_artifacts": "Local train-fold measurement fit plus held-out observed labels for evaluation only",
            "target_policy": "Map predicted theta back to dataset-specific expected PHQ item/total summaries for comparison with direct X_to_Y baselines.",
            "leakage_boundary": "Held-out observed labels are never inputs to X_to_theta prediction; they are evaluation targets only.",
            "tracked_output_policy": "Export aggregate observed-scale MAE/RMSE/correlation and calibration summaries.",
            "local_only_policy": "Per-subject mapped item predictions and fold-specific measurement parameters stay local-only.",
            "pass_condition": "Theta-space gains also translate into non-degraded observed-scale reconstruction relative to direct floors.",
        },
    ]
    return pd.DataFrame(rows)


def local_only_boundary_contract() -> pd.DataFrame:
    rows = [
        {
            "artifact_class": "measurement_fit_parameters",
            "example_local_file": "mv12_local_measurement_fit_parameters.json",
            "reason_local_only": "Fitted item discriminations, thresholds, and DIF offsets define the private scoring transform.",
            "tracked_surrogate": "aggregate fit status, anchor counts, DIF role counts, and target reliability summaries",
            "git_policy": "ignored local-only; never force-add",
        },
        {
            "artifact_class": "latent_targets",
            "example_local_file": "mv12_local_theta_targets.csv",
            "reason_local_only": "Per-participant latent severity targets are subject-level clinical derivatives.",
            "tracked_surrogate": "aggregate theta distribution bins and fold reliability metrics",
            "git_policy": "ignored local-only; never force-add",
        },
        {
            "artifact_class": "row_predictions",
            "example_local_file": "p5_mv12_local_predictions.csv",
            "reason_local_only": "Needed for local error analysis but contains subject-grain prediction traces.",
            "tracked_surrogate": "dataset-stratified metrics, transfer deltas, calibration bins, and identity summaries",
            "git_policy": "ignored local-only; never force-add",
        },
        {
            "artifact_class": "feature_transforms_and_models",
            "example_local_file": "mv12_local_feature_projection_and_model_artifacts",
            "reason_local_only": "Projection directions, fitted regressors, and transformed features can reconstruct sensitive dataset/subject information.",
            "tracked_surrogate": "aggregate selected model family, fold counts, hyperparameter ranges, and leakage audit booleans",
            "git_policy": "ignored local-only; never force-add",
        },
        {
            "artifact_class": "diagnostic_workbooks",
            "example_local_file": "mv12_local_error_review_workbook.csv",
            "reason_local_only": "Any manual review packet could link model errors back to private local records.",
            "tracked_surrogate": "aggregate error taxonomy counts only if a later review is approved",
            "git_policy": "ignored local-only; never force-add",
        },
    ]
    return pd.DataFrame(rows)


def model_ladder_contract() -> pd.DataFrame:
    rows = [
        {
            "model_id": "B0_train_mean_theta",
            "model_family": "floor",
            "input_signal": "train-fold labels only",
            "target": "theta",
            "baseline_role": "latent target sanity floor",
            "identity_control": "none",
            "external_transfer": "applies to each source-target direction as a constant train-fold theta predictor",
            "pass_gate": "Every X_to_theta candidate must beat this floor on same-dataset and cross-dataset aggregate theta error.",
        },
        {
            "model_id": "B1_train_mean_observed_total",
            "model_family": "floor",
            "input_signal": "train-fold observed scale totals only",
            "target": "observed item/total reconstruction",
            "baseline_role": "observed-scale severity floor",
            "identity_control": "none",
            "external_transfer": "used for E-DAIC_to_CMDC and CMDC_to_E-DAIC observed-scale comparisons",
            "pass_gate": "Theta models must not look successful only in latent space while failing observed-scale floors.",
        },
        {
            "model_id": "B2_direct_X_to_Y_total_allocation",
            "model_family": "direct baseline",
            "input_signal": "aligned frozen BGE subject features",
            "target": "observed PHQ item proxies allocated from predicted total severity",
            "baseline_role": "strong simple direct floor from MV07/MV07c sequence",
            "identity_control": "none or train-fold selected nuisance projection if predeclared",
            "external_transfer": "train one PHQ dataset, evaluate on the other through observed-scale mapping",
            "pass_gate": "MV12 must beat or clearly contextualize this direct floor before any positive shared-latent wording.",
        },
        {
            "model_id": "B3_direct_X_to_Y_itemwise",
            "model_family": "direct baseline",
            "input_signal": "aligned frozen BGE subject features",
            "target": "observed PHQ C01-C08 item scores",
            "baseline_role": "direct symptom-head comparator from MV07",
            "identity_control": "none for primary baseline",
            "external_transfer": "same-dataset and cross-dataset PHQ transfer",
            "pass_gate": "X_to_theta must outperform this direct itemwise path on primary theta and non-degraded observed reconstruction.",
        },
        {
            "model_id": "M12a_BGE_Ridge_X_to_theta",
            "model_family": "primary MV12 candidate",
            "input_signal": "aligned frozen BGE subject features",
            "target": "train-fold local-only MV11 theta",
            "baseline_role": "first real two-stage test",
            "identity_control": "none in primary run so utility is measured before projection",
            "external_transfer": "E-DAIC_to_CMDC and CMDC_to_E-DAIC theta prediction; no official E-DAIC test label tuning",
            "pass_gate": "Beat B0/B1/B2/B3 on predeclared aggregate metrics with subject-level folds and hygiene pass.",
        },
        {
            "model_id": "M12b_identity_projected_BGE_X_to_theta",
            "model_family": "secondary MV12 candidate",
            "input_signal": "train-fold nuisance-projected aligned BGE features",
            "target": "train-fold local-only MV11 theta",
            "baseline_role": "accuracy-invariance trade-off candidate",
            "identity_control": "learn projection inside train folds without eval labels or eval dataset labels",
            "external_transfer": "same transfer matrix as M12a",
            "pass_gate": "Allowed as secondary pass only if M12a is reported and conditional latent identity improves without losing more than 5 percent relative theta utility.",
        },
        {
            "model_id": "M12c_theta_to_dataset_specific_Y",
            "model_family": "measurement mapping evaluation",
            "input_signal": "predicted theta plus local train-fold measurement mapping",
            "target": "dataset-specific expected PHQ item and total summaries",
            "baseline_role": "checks whether latent gains survive observed-scale interpretation",
            "identity_control": "post-mapping prediction identity is diagnostic, not a hard shared-latent gate",
            "external_transfer": "evaluate both source-to-target directions with target labels used only for scoring",
            "pass_gate": "Observed-scale reconstruction must be non-degraded versus direct floors or the latent result is downgraded to diagnostic.",
        },
    ]
    return pd.DataFrame(rows)


def identity_transfer_gate_contract() -> pd.DataFrame:
    rows = [
        {
            "gate_id": "ID0_unconditional_screen",
            "gate_type": "diagnostic_screen",
            "probe_or_check": "Dataset identity from raw or transformed BGE features",
            "conditioning": "none",
            "metric": "balanced_accuracy",
            "pass_status_for_design": "predeclared_report_only",
            "future_pass_rule": "Report as shortcut-risk context; do not use as the only hard failure criterion.",
            "tracked_output": "aggregate identity mean/std by seed and representation",
        },
        {
            "gate_id": "ID1_shared_latent_conditional_identity",
            "gate_type": "primary_identity_gate",
            "probe_or_check": "Dataset identity from predicted theta residuals or shared-latent representations",
            "conditioning": "condition on observed severity, available aligned PHQ items, and legitimate covariates where available",
            "metric": "balanced_accuracy",
            "pass_status_for_design": "predeclared_required",
            "future_pass_rule": "Must be below the MV09 conditional feature identity baselines and preferably <=0.700; otherwise only diagnostic wording is allowed.",
            "tracked_output": "aggregate conditional identity summary; no row residual export",
        },
        {
            "gate_id": "ID2_post_mapping_prediction_identity",
            "gate_type": "diagnostic_identity_gate",
            "probe_or_check": "Dataset identity from dataset-specific theta_to_observed PHQ outputs",
            "conditioning": "same conditioning as ID1 when feasible",
            "metric": "balanced_accuracy",
            "pass_status_for_design": "predeclared_diagnostic",
            "future_pass_rule": "Do not treat scale-specific post-mapping identity as the same hard gate as shared-latent identity.",
            "tracked_output": "aggregate post-mapping identity only",
        },
        {
            "gate_id": "TR0_same_dataset_subject_folds",
            "gate_type": "predictive_utility",
            "probe_or_check": "Subject-level same-dataset CV or official train/dev where already defined",
            "conditioning": "train-fold target generation only",
            "metric": "theta_MAE_or_RMSE;theta_correlation;observed_reconstruction_MAE",
            "pass_status_for_design": "predeclared_required",
            "future_pass_rule": "M12a must beat train-mean theta and direct X_to_Y floors on both E-DAIC and CMDC same-dataset evaluations.",
            "tracked_output": "aggregate metrics by dataset, seed, fold family, and model",
        },
        {
            "gate_id": "TR1_external_transfer",
            "gate_type": "external_transfer",
            "probe_or_check": "E-DAIC_to_CMDC and CMDC_to_E-DAIC X_to_theta transfer",
            "conditioning": "no target-domain labels for training or model selection",
            "metric": "target-domain theta error, observed reconstruction error, and calibration",
            "pass_status_for_design": "predeclared_required",
            "future_pass_rule": "At least one transfer direction must beat both train-mean and direct X_to_Y floors; if only same-dataset passes, claim is diagnostic only.",
            "tracked_output": "aggregate transfer matrix; no per-subject target export",
        },
        {
            "gate_id": "TR2_no_official_test_tuning",
            "gate_type": "leakage_control",
            "probe_or_check": "E-DAIC official test labels and unavailable held-out labels",
            "conditioning": "not applicable",
            "metric": "leakage audit booleans",
            "pass_status_for_design": "predeclared_required",
            "future_pass_rule": "No official test labels or private target labels may be used for target fitting, model selection, or nuisance projection.",
            "tracked_output": "aggregate split and leakage audit",
        },
    ]
    return pd.DataFrame(rows)


def pass_fail_gate_contract() -> pd.DataFrame:
    rows = [
        {
            "gate_id": "G0_design_completeness",
            "status": "pass",
            "current_evidence": "MV12 defines target generation, local-only boundaries, model ladder, identity/transfer probes, and pass/fail thresholds before a run.",
            "future_run_pass_rule": "All required aggregate outputs exist and artifact hygiene passes.",
            "full_method_effect": "Design pass alone does not authorize full method.",
        },
        {
            "gate_id": "G1_psychometric_target_stability",
            "status": "pass_with_bic_caveat",
            "current_evidence": "MV11 formally confirms four MV10 anchors, no strong loading-DIF flags, and threshold DIF for C02/C06 with AIC/BIC disagreement.",
            "future_run_pass_rule": "Future runner must report fold/bootstrap target reliability and anchor stability; instability downgrades all X_to_theta claims.",
            "full_method_effect": "Needed before any shared-latent method claim.",
        },
        {
            "gate_id": "G2_predictive_utility",
            "status": "predeclared_pending_run",
            "current_evidence": "Prior direct BGE heads and residual heads are negative or partial, so floors remain strong comparators.",
            "future_run_pass_rule": "M12a must beat train-mean theta, observed-total floors, direct X_to_Y total-allocation, and direct itemwise baselines on primary aggregate metrics.",
            "full_method_effect": "If failed, MV12 becomes another diagnostic negative result.",
        },
        {
            "gate_id": "G3_external_transfer",
            "status": "predeclared_pending_run",
            "current_evidence": "Existing E-DAIC/CMDC shared-symptom transfer evidence is weak or floor-limited.",
            "future_run_pass_rule": "At least one source-to-target PHQ transfer direction must beat direct/floor baselines without target-domain model selection.",
            "full_method_effect": "Without transfer, same-dataset success is not enough for transferable shared-latent claims.",
        },
        {
            "gate_id": "G4_conditional_identity",
            "status": "predeclared_pending_run",
            "current_evidence": "MV09 conditional identity remains high: E-DAIC/CMDC PHQ-item-conditioned BA 0.991 and severity-conditioned three-way BA 1.000.",
            "future_run_pass_rule": "Shared-latent conditional identity must improve versus MV09 conditional baselines and preferably be <=0.700.",
            "full_method_effect": "If identity remains high, wording is limited to measurement-target diagnostic evidence.",
        },
        {
            "gate_id": "G5_artifact_hygiene",
            "status": "pass_for_design",
            "current_evidence": "MV12 design exports only aggregate contracts and reports.",
            "future_run_pass_rule": "No public fitted parameters, latent scores, row predictions, features, model files, private workbooks, or source locators.",
            "full_method_effect": "Any hygiene failure blocks GitHub publication and manuscript use until fixed.",
        },
    ]
    return pd.DataFrame(rows)


def implementation_queue() -> pd.DataFrame:
    rows = [
        {
            "rank": 1,
            "action_id": "IMPLEMENT_MV12_RUNNER",
            "action": "Create scripts/phase5_run_mv12_two_stage_latent_target.py.",
            "success_gate": "Runner produces local-only measurement targets and aggregate X_to_theta, direct X_to_Y, identity, transfer, and leakage summaries.",
            "version_policy": "Track script and aggregate outputs only; keep fitted parameters, theta targets, row predictions, transformed features, and models local-only.",
        },
        {
            "rank": 2,
            "action_id": "GENERATE_LOCAL_Y_TO_THETA_TARGETS",
            "action": "Fit train-fold MV11-style label-only measurement targets for E-DAIC and CMDC.",
            "success_gate": "Confirmed anchors are used consistently; C02/C06 are DIF-aware; target reliability and coverage are exported only in aggregate.",
            "version_policy": "Local-only score and parameter files; commit only aggregate reliability and coverage.",
        },
        {
            "rank": 3,
            "action_id": "RUN_DIRECT_AND_FLOOR_BASELINES",
            "action": "Run B0/B1/B2/B3 floors in the same subject-level split contract.",
            "success_gate": "Direct X_to_Y and train-mean floors exist before any M12a/M12b interpretation.",
            "version_policy": "Aggregate metrics only.",
        },
        {
            "rank": 4,
            "action_id": "RUN_X_TO_THETA_MODELS",
            "action": "Run M12a BGE Ridge X_to_theta and optional M12b identity-projected X_to_theta.",
            "success_gate": "M12a is always reported; M12b is framed as an accuracy-invariance trade-off if projection is used.",
            "version_policy": "No model files, transformed features, projection directions, or row predictions in Git.",
        },
        {
            "rank": 5,
            "action_id": "RUN_CONDITIONAL_IDENTITY_AND_TRANSFER_AUDITS",
            "action": "Audit same-dataset folds, external E-DAIC/CMDC transfer, theta_to_observed mapping, and conditional identity.",
            "success_gate": "Full-method gate can decide from aggregate utility, transfer, identity, leakage, and hygiene tables.",
            "version_policy": "Commit aggregate summaries and refreshed gates only.",
        },
        {
            "rank": 6,
            "action_id": "REFRESH_FULL_GATE_AND_PAPER_TABLES",
            "action": "Rerun full-method gate and diagnostic paper table generator after the MV12 runner.",
            "success_gate": "Claim boundaries state whether MV12 changes full-method authorization or remains diagnostic.",
            "version_policy": "Commit refreshed aggregate gate, paper scaffolds, docs, and memory.",
        },
    ]
    return pd.DataFrame(rows)


def artifact_hygiene(out_dir: Path) -> dict[str, Any]:
    forbidden_patterns = [
        r"/root/",
        r"/autodl-tmp/",
        r"\bsubject_id\b",
        r"\bsubject_key\b",
        r"\btext_path\b",
        r"\baudio_path\b",
        r"\bvideo_path\b",
        r"\bgait_path\b",
        r"source_locator",
        r"local_annotation_workbook",
        r"\.wav\b",
        r"\.mp4\b",
        r"\.avi\b",
        r"raw prompt",
        r"raw response",
        r"raw clinical",
        r"posterior_score",
        r"factor_score",
        r"parameter_value",
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
        "audit_id": "P5_MV12_two_stage_latent_target_design_hygiene",
        "artifact_hygiene_passed": len(violations) == 0,
        "files_checked": checked,
        "generated_at": utc_now(),
        "violation_count": len(violations),
        "violations": violations,
    }


def write_report(
    out_dir: Path,
    run_summary: dict[str, Any],
    evidence: pd.DataFrame,
    target: pd.DataFrame,
    local_only: pd.DataFrame,
    models: pd.DataFrame,
    identity: pd.DataFrame,
    gates: pd.DataFrame,
    queue: pd.DataFrame,
) -> None:
    lines = [
        "# P5_MV12 Two-Stage Latent-Target Design",
        "",
        f"Generated: `{run_summary['generated_at']}`",
        "",
        "## Scope",
        "",
        "This is a predeclared design contract. It does not train a multimodal model, fit public measurement parameters, export theta scores, read row-level predictions, or authorize full-method construction.",
        "",
        "## Decision",
        "",
        f"- Readiness status: `{run_summary['decision']['readiness_status']}`.",
        f"- Recommended next action: `{run_summary['decision']['recommended_next_action']}`.",
        f"- Full method allowed: `{run_summary['decision']['full_method_allowed']}`.",
        f"- Artifact hygiene passed: `{run_summary['artifact_hygiene_passed']}`.",
        "",
        run_summary["decision"]["short_read"],
        "",
        "## Source Evidence",
        "",
        "| source | status | observation | implication |",
        "| --- | --- | --- | --- |",
    ]
    for _, row in evidence.iterrows():
        lines.append(f"| {row['source_id']} | `{row['status']}` | {row['observation']} | {row['implication_for_mv12']} |")

    lines.extend(
        [
            "",
            "## Target Generation",
            "",
            "| stage | scope | target policy | tracked output | pass condition |",
            "| --- | --- | --- | --- | --- |",
        ]
    )
    for _, row in target.iterrows():
        lines.append(
            f"| {row['stage_id']} | {row['scope']} | {row['target_policy']} | "
            f"{row['tracked_output_policy']} | {row['pass_condition']} |"
        )

    lines.extend(
        [
            "",
            "## Local-Only Boundary",
            "",
            "| artifact class | reason | tracked surrogate | git policy |",
            "| --- | --- | --- | --- |",
        ]
    )
    for _, row in local_only.iterrows():
        lines.append(
            f"| {row['artifact_class']} | {row['reason_local_only']} | {row['tracked_surrogate']} | {row['git_policy']} |"
        )

    lines.extend(
        [
            "",
            "## Model Ladder",
            "",
            "| model | family | target | role | pass gate |",
            "| --- | --- | --- | --- | --- |",
        ]
    )
    for _, row in models.iterrows():
        lines.append(
            f"| {row['model_id']} | {row['model_family']} | {row['target']} | {row['baseline_role']} | {row['pass_gate']} |"
        )

    lines.extend(
        [
            "",
            "## Identity And Transfer Gates",
            "",
            "| gate | type | conditioning | future rule |",
            "| --- | --- | --- | --- |",
        ]
    )
    for _, row in identity.iterrows():
        lines.append(f"| {row['gate_id']} | {row['gate_type']} | {row['conditioning']} | {row['future_pass_rule']} |")

    lines.extend(
        [
            "",
            "## Pass/Fail Gates",
            "",
            "| gate | current status | future run rule | full-method effect |",
            "| --- | --- | --- | --- |",
        ]
    )
    for _, row in gates.iterrows():
        lines.append(
            f"| {row['gate_id']} | `{row['status']}` | {row['future_run_pass_rule']} | {row['full_method_effect']} |"
        )

    lines.extend(
        [
            "",
            "## Implementation Queue",
            "",
            "| rank | action | success gate |",
            "| ---: | --- | --- |",
        ]
    )
    for _, row in queue.iterrows():
        lines.append(f"| {int(row['rank'])} | {row['action']} | {row['success_gate']} |")

    lines.extend(
        [
            "",
            "## Interpretation Boundary",
            "",
            "- MV12 is the next minimal-validation design, not a positive method result.",
            "- A future pass requires predictive utility, external transfer, conditional shared-latent identity, leakage control, and artifact hygiene.",
            "- If X_to_theta fails the floors or conditional identity remains high, the result supports the measurement-shift paper as diagnostic evidence only.",
        ]
    )
    (out_dir / "report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()

    out_dir = args.out_dir
    if out_dir.exists():
        if not args.overwrite:
            raise SystemExit(f"output directory exists; use --overwrite: {rel(out_dir)}")
        shutil.rmtree(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    generated_at = utc_now()
    evidence = source_evidence_summary()
    target = target_generation_contract()
    local_only = local_only_boundary_contract()
    models = model_ladder_contract()
    identity = identity_transfer_gate_contract()
    gates = pass_fail_gate_contract()
    queue = implementation_queue()
    refs = pd.DataFrame(METHOD_SOURCE_REFS)

    evidence.to_csv(out_dir / "source_evidence_summary.csv", index=False)
    target.to_csv(out_dir / "target_generation_contract.csv", index=False)
    local_only.to_csv(out_dir / "local_only_boundary_contract.csv", index=False)
    models.to_csv(out_dir / "model_ladder_contract.csv", index=False)
    identity.to_csv(out_dir / "identity_transfer_gate_contract.csv", index=False)
    gates.to_csv(out_dir / "pass_fail_gate_contract.csv", index=False)
    queue.to_csv(out_dir / "implementation_queue.csv", index=False)
    refs.to_csv(out_dir / "method_source_refs.csv", index=False)

    run_summary = {
        "run_id": "P5_MV12_two_stage_latent_target_design",
        "generated_at": generated_at,
        "status": "complete",
        "scope": "predeclared_design_no_training",
        "input_contract": {
            "aggregate_phase5_artifacts_read": True,
            "mv11_formal_measurement_read": True,
            "mv09_conditional_identity_read": True,
            "mv07_direct_baseline_summaries_read": True,
            "raw_data_scanned": False,
            "multimodal_features_read": False,
            "row_level_predictions_read": False,
            "private_review_material_read": False,
            "fitted_measurement_parameters_read": False,
            "subject_theta_scores_read": False,
        },
        "outputs": {
            "tracked_outputs": TRACKED_FILES,
            "source_evidence_rows": int(len(evidence)),
            "target_contract_rows": int(len(target)),
            "local_only_boundary_rows": int(len(local_only)),
            "model_ladder_rows": int(len(models)),
            "identity_transfer_gate_rows": int(len(identity)),
            "pass_fail_gate_rows": int(len(gates)),
            "implementation_queue_rows": int(len(queue)),
            "method_source_ref_rows": int(len(refs)),
        },
        "decision": {
            "readiness_status": "ready_to_implement_mv12_two_stage_latent_target",
            "recommended_next_action": "implement_scripts_phase5_run_mv12_two_stage_latent_target",
            "full_method_allowed": False,
            "short_read": "MV12 is predeclared as a two-stage measurement-target experiment: fit Y_to_theta locally, train audited X_to_theta predictors, compare against direct/floor baselines, and gate on conditional identity plus external transfer.",
        },
        "verdict": {
            "status": "ready_to_implement_mv12_two_stage_latent_target",
            "pass_rule_status": "design_ready_full_method_still_blocked",
            "pass_rule_met": None,
            "full_method_allowed": False,
            "short_read": "Design is ready; the actual MV12 X_to_theta run is still required before any full-method or transferable shared-latent claim.",
        },
        "output_policy": {
            "tracked_outputs": TRACKED_FILES,
            "local_only_files": [
                "mv12_local_measurement_fit_parameters.json",
                "mv12_local_theta_targets.csv",
                "p5_mv12_local_predictions.csv",
                "mv12_local_feature_projection_and_model_artifacts",
            ],
        },
        "artifact_hygiene_passed": False,
    }
    (out_dir / "run_summary.json").write_text(json.dumps(run_summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    write_report(out_dir, run_summary, evidence, target, local_only, models, identity, gates, queue)
    hygiene = artifact_hygiene(out_dir)
    run_summary["artifact_hygiene_passed"] = bool(hygiene["artifact_hygiene_passed"])
    (out_dir / "run_summary.json").write_text(json.dumps(run_summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    write_report(out_dir, run_summary, evidence, target, local_only, models, identity, gates, queue)
    hygiene = artifact_hygiene(out_dir)
    (out_dir / "artifact_hygiene_audit.json").write_text(json.dumps(hygiene, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if not hygiene["artifact_hygiene_passed"]:
        raise SystemExit("artifact hygiene failed")
    print(
        "Wrote MV12 design to "
        f"{out_dir.relative_to(ROOT)} with status "
        f"{run_summary['decision']['readiness_status']}"
    )


if __name__ == "__main__":
    main()
