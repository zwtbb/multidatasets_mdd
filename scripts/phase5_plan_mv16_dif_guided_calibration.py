#!/usr/bin/env python3
"""Predeclare MV16 DIF-guided few-shot measurement calibration.

This script is a design contract, not a calibration run. It converts the
post-MV15 next action into a bounded experiment plan: compare zero-shot source
measurement, global theta calibration, DIF-guided C02/C06 threshold
calibration, all-threshold calibration, and direct target adaptation at
k=0/5/10/20/40 target-labeled subjects.

The script reads only aggregate Phase 5 artifacts. Future calibration
parameters, theta tables, target-shot sampling maps, row-level predictions,
fitted measurement parameters, split maps, and model artifacts remain
local-only.
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
DEFAULT_OUT_DIR = PHASE5_DIR / "p5_mv16_dif_guided_calibration_design"

MV10_DIR = PHASE5_DIR / "p5_mv10_psychometric_invariance_baseline"
MV11_DIR = PHASE5_DIR / "p5_mv11_formal_psychometric_confirmation"
MV12_DIR = PHASE5_DIR / "p5_mv12_two_stage_latent_target"
MV12_ANALYSIS_DIR = PHASE5_DIR / "p5_mv12_latent_target_tradeoff_analysis"
MV13_DIR = PHASE5_DIR / "p5_mv13_external_psychometric_replication"
MV14_DIR = PHASE5_DIR / "p5_mv14_measurement_uncertainty_bootstrap"
MV15_DIR = PHASE5_DIR / "p5_mv15_latent_conditioned_identity"
FULL_GATE_DIR = PHASE5_DIR / "full_method_gate_audit"

RUN_ID = "P5_MV16_dif_guided_calibration_design"

PHQ_CONSTRUCTS = ["C01", "C02", "C03", "C04", "C05", "C06", "C07", "C08"]
PRIMARY_ANCHORS = ["C01", "C04", "C05", "C07"]
PRIMARY_THRESHOLD_DIF = ["C02", "C06"]
SENSITIVITY_ITEMS = ["C03", "C08"]
K_SHOTS = [0, 5, 10, 20, 40]
SEEDS = [0, 1, 2, 3, 4]

TRACKED_FILES = [
    "artifact_hygiene_audit.json",
    "calibration_item_contract.csv",
    "calibration_ladder_contract.csv",
    "dataset_direction_contract.csv",
    "fewshot_sampling_contract.csv",
    "implementation_queue.csv",
    "input_boundary_contract.csv",
    "local_only_boundary_contract.csv",
    "method_source_refs.csv",
    "metric_contract.csv",
    "model_comparison_contract.csv",
    "pass_fail_gate_contract.csv",
    "report.md",
    "run_summary.json",
    "source_evidence_summary.csv",
]

METHOD_SOURCE_REFS = [
    {
        "source_id": "samejima_graded_response_model",
        "url": "https://www.psychometricsociety.org/sites/main/files/file-attachments/mn17.pdf",
        "source_type": "primary_method_monograph",
        "use_in_mv16": "Retain the MV11-MV14 graded-response PHQ measurement lineage for theta and item-threshold mapping.",
        "key_takeaway": "Ordinal item responses can be modeled through a latent severity variable and ordered category thresholds.",
    },
    {
        "source_id": "mirt_multipleGroup_documentation",
        "url": "https://philchalmers.github.io/mirt/html/multipleGroup.html",
        "source_type": "official_package_documentation",
        "use_in_mv16": "Specify the future local measurement runner around multi-group IRT with group invariance and anchor constraints.",
        "key_takeaway": "The mirt multipleGroup API supports multi-group IRT, invariance constraints, and anchor-item style constraints for DIF workflows.",
    },
    {
        "source_id": "mirt_DIF_documentation",
        "url": "https://philchalmers.github.io/mirt/html/DIF.html",
        "source_type": "official_package_documentation",
        "use_in_mv16": "Keep DIF tests and threshold calibration tied to a standard Wald/LR DIF workflow rather than an ad hoc item relabeling step.",
        "key_takeaway": "mirt documents Wald and likelihood-ratio DIF testing as wrappers around multipleGroup-style multi-group models.",
    },
    {
        "source_id": "anchor_selection_strategies_for_DIF",
        "url": "https://pmc.ncbi.nlm.nih.gov/articles/PMC5965509/",
        "source_type": "peer_reviewed_method_reference",
        "use_in_mv16": "Treat C01/C04/C05/C07 as predeclared anchors because MV10-MV14 repeatedly support them; do not discover anchors inside the future target fold.",
        "key_takeaway": "Anchor selection affects DIF detection and must be separated from the confirmatory target evaluation.",
    },
    {
        "source_id": "phq9_measurement_invariance_helius",
        "url": "https://pmc.ncbi.nlm.nih.gov/articles/PMC5655879/",
        "source_type": "measurement_invariance_paper",
        "use_in_mv16": "Frame PHQ-8/PHQ-9 cross-dataset calibration as a measurement-invariance and partial-invariance problem.",
        "key_takeaway": "PHQ group comparisons require explicit common-structure and item-threshold checks rather than naive total-score equivalence.",
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
    return "NA" if numeric is None else f"{numeric:.{digits}f}"


def join_values(values: list[Any]) -> str:
    return ";".join(str(value) for value in values)


def truthy(value: Any) -> bool:
    return str(value).strip().lower() in {"true", "1", "yes", "pass", "passed"}


def source_evidence_summary() -> pd.DataFrame:
    mv10 = read_json(MV10_DIR / "run_summary.json")
    mv11 = read_json(MV11_DIR / "run_summary.json")
    mv12 = read_json(MV12_DIR / "run_summary.json")
    mv12_analysis = read_json(MV12_ANALYSIS_DIR / "run_summary.json")
    mv13 = read_json(MV13_DIR / "run_summary.json")
    mv14 = read_json(MV14_DIR / "run_summary.json")
    mv15 = read_json(MV15_DIR / "run_summary.json")
    full_gate = read_json(FULL_GATE_DIR / "run_summary.json")

    mv11_anchor = read_csv(MV11_DIR / "anchor_confirmation_summary.csv")
    mv12_transfer = read_csv(MV12_DIR / "transfer_summary.csv")
    mv14_dif = read_csv(MV14_DIR / "item_dif_stability_summary.csv")
    mv15_gates = read_csv(MV15_DIR / "pass_fail_gate_results.csv")
    next_actions = read_csv(FULL_GATE_DIR / "next_action_queue.csv")

    mv10_v = mv10.get("verdict") or {}
    mv11_v = mv11.get("verdict") or {}
    mv12_v = mv12.get("verdict") or {}
    mv12_a = mv12_analysis.get("decision") or {}
    mv13_v = mv13.get("verdict") or {}
    mv14_v = mv14.get("verdict") or {}
    mv15_v = mv15.get("verdict") or {}
    mv14_dif_attempted = mv14_v.get("dif_attempted_draws", mv14_v.get("requested_dif_R"))
    top_action = next_actions.sort_values("rank").iloc[0].to_dict()

    confirmed_mv11_anchors = mv11_anchor.loc[
        mv11_anchor["mv10_anchor_confirmed"].map(truthy), "construct_id"
    ].astype(str).tolist()
    threshold_dif_mv11 = mv11_anchor.loc[
        mv11_anchor["threshold_dif_flag"].map(truthy), "construct_id"
    ].astype(str).tolist()
    stable_anchors_mv14 = mv14_dif.loc[
        (mv14_dif["mv10_role"] == "anchor_candidate")
        & (mv14_dif["anchor_support_frequency"] >= 0.90),
        "construct_id",
    ].astype(str).tolist()
    top_threshold_mv14 = (
        mv14_dif.sort_values("threshold_frequency_rank")
        .head(2)["construct_id"]
        .astype(str)
        .tolist()
    )
    transfer_failed = int((mv12_transfer["transfer_theta_beats_B0"].astype(str).str.lower() == "false").sum())
    mv15_blocked_gate = mv15_gates[
        mv15_gates["status"].astype(str).str.lower().eq("blocked")
    ]["gate_id"].astype(str).tolist()

    rows = [
        {
            "source_id": "full_gate_context",
            "artifact": rel(FULL_GATE_DIR / "run_summary.json"),
            "status": full_gate.get("gate_status"),
            "observation": (
                f"phase5_summary_count={full_gate.get('evidence_rows')}; "
                f"full_method_allowed={full_gate.get('full_method_allowed')}; "
                f"top_next_action={top_action.get('action_id')}"
            ),
            "implication_for_mv16": "MV16 design and execution must stay under the full-method gate; it cannot start full M0/M1/M2/M3 construction.",
        },
        {
            "source_id": "mv10_mv11_anchor_map",
            "artifact": rel(MV11_DIR / "anchor_confirmation_summary.csv"),
            "status": mv11_v.get("status"),
            "observation": (
                f"MV10_loading_congruence={fmt(mv10_v.get('loading_congruence'))}; "
                f"MV11_confirmed_anchors={join_values(confirmed_mv11_anchors)}; "
                f"MV11_threshold_DIF_items={join_values(threshold_dif_mv11)}; "
                f"MV11_loading_DIF_flags={mv11_v.get('loading_dif_flagged_items')}"
            ),
            "implication_for_mv16": "Lock C01/C04/C05/C07 as anchors and treat C02/C06 threshold offsets as the primary DIF-guided calibration target.",
        },
        {
            "source_id": "mv13_external_replication",
            "artifact": rel(MV13_DIR / "run_summary.json"),
            "status": mv13_v.get("status"),
            "observation": (
                f"confirmed_anchors={mv13_v.get('confirmed_mv10_anchor_items')}; "
                f"loading_DIF_flags={mv13_v.get('loading_dif_flagged_items')}; "
                f"threshold_DIF_flags={mv13_v.get('threshold_dif_flagged_items')}; "
                f"core_converged={mv13_v.get('core_converged')}; "
                f"AIC_BIC={mv13_v.get('best_aic_model')}/{mv13_v.get('best_bic_model')}"
            ),
            "implication_for_mv16": "Use the external psychometric replication as qualitative support only; future fitted parameters stay local-only.",
        },
        {
            "source_id": "mv14_bootstrap_stability",
            "artifact": rel(MV14_DIR / "item_dif_stability_summary.csv"),
            "status": mv14_v.get("status"),
            "observation": (
                f"stable_anchors={join_values(stable_anchors_mv14)}; "
                f"top_threshold_DIF={join_values(top_threshold_mv14)}; "
                f"core_effective_R={mv14_v.get('core_effective_draws')}/"
                f"{mv14_v.get('core_selection_attempted_draws')}; "
                f"stable_ladder_R={mv14_v.get('stable_ladder_effective_draws')}; "
                f"DIF_effective_R={mv14_v.get('dif_min_anchor_effective_draws')}/{mv14_dif_attempted}"
            ),
            "implication_for_mv16": "Use only item-level stable-anchor and localized C02/C06 threshold-DIF wording; global model-selection remains uncertain.",
        },
        {
            "source_id": "mv12_zero_shot_transfer_failure",
            "artifact": rel(MV12_DIR / "transfer_summary.csv"),
            "status": mv12_v.get("pass_rule_status"),
            "observation": (
                f"transfer_protocols={len(mv12_transfer)}; "
                f"theta_transfer_failed_protocols={transfer_failed}; "
                f"same_dataset_theta_gate={mv12_v.get('same_dataset_theta_gate_passed')}; "
                f"observed_scale_safety={mv12_v.get('same_dataset_observed_gate_passed')}; "
                f"external_theta_gate={mv12_v.get('external_transfer_theta_gate_passed')}"
            ),
            "implication_for_mv16": "MV16 must test target measurement calibration, not another source-only X-to-theta head.",
        },
        {
            "source_id": "mv12_dimension_matched_caveat",
            "artifact": rel(MV12_ANALYSIS_DIR / "run_summary.json"),
            "status": mv12_a.get("analysis_status"),
            "observation": (
                f"freeze_current_latent_target_line={mv12_a.get('freeze_current_latent_target_line')}; "
                f"b3_caveat={mv12_a.get('dimension_matched_identity_caveat')}"
            ),
            "implication_for_mv16": "Future calibration must keep direct itemwise and total-based adaptation as comparators, not just latent theta.",
        },
        {
            "source_id": "mv15_latent_conditioned_identity",
            "artifact": rel(MV15_DIR / "run_summary.json"),
            "status": mv15_v.get("pass_rule_status"),
            "observation": (
                f"raw_feature_BA={fmt(mv15_v.get('raw_feature_identity_ba'))}; "
                f"theta_conditioned_feature_BA={fmt(mv15_v.get('theta_conditioned_feature_identity_ba'))}; "
                f"total_predtotal_b3_feature_BA={fmt(mv15_v.get('total_conditioned_feature_identity_ba'))}/"
                f"{fmt(mv15_v.get('predicted_total_conditioned_feature_identity_ba'))}/"
                f"{fmt(mv15_v.get('b3_itemwise_theta_conditioned_feature_identity_ba'))}; "
                f"blocked_gates={join_values(mv15_blocked_gate)}"
            ),
            "implication_for_mv16": "Treat MV16 as measurement-mapping calibration under high feature-identity risk; do not use it to claim invariant BGE features.",
        },
    ]
    return pd.DataFrame(rows)


def dataset_direction_contract() -> pd.DataFrame:
    rows = [
        {
            "direction_id": "D1_edaic_source_cmdc_target",
            "source_dataset": "edaic",
            "target_dataset": "cmdc",
            "label_boundary": "PHQ C01-C08 item labels; PHQ-8/PHQ-9 common constructs only",
            "target_label_budget_k": join_values(K_SHOTS),
            "primary_role": "primary cross-dataset calibration direction",
            "split_protocol": "source train subjects fit source measurement/predictor; target k-shot calibration subjects are sampled only from target train folds; target eval subjects are held out",
            "claim_boundary": "May support target measurement calibration if gates pass; cannot support language-invariant or feature-invariant claims.",
        },
        {
            "direction_id": "D2_cmdc_source_edaic_target",
            "source_dataset": "cmdc",
            "target_dataset": "edaic",
            "label_boundary": "PHQ C01-C08 item labels; E-DAIC official test remains unused",
            "target_label_budget_k": join_values(K_SHOTS),
            "primary_role": "reverse-direction sensitivity with larger E-DAIC target pool",
            "split_protocol": "CMDC source folds train source scorer; E-DAIC train/dev item-labeled subjects provide target calibration/eval splits without official test labels",
            "claim_boundary": "Use as direction robustness only because source CMDC item-labeled N is small.",
        },
        {
            "direction_id": "D3_within_target_fewshot_sanity",
            "source_dataset": "edaic_or_cmdc",
            "target_dataset": "same_target",
            "label_boundary": "PHQ C01-C08 target labels",
            "target_label_budget_k": join_values(K_SHOTS),
            "primary_role": "sanity bound for target-label sample efficiency",
            "split_protocol": "target train/calibration subjects separate from target eval subjects in every seed",
            "claim_boundary": "Report as a target-domain upper/lower bound; not cross-dataset transfer evidence by itself.",
        },
        {
            "direction_id": "D4_pdch_hamd_linking_deferred",
            "source_dataset": "cmdc_or_edaic",
            "target_dataset": "pdch",
            "label_boundary": "HAMD severity only; no PHQ-HAMD theta linking in MV16 design",
            "target_label_budget_k": "not_primary",
            "primary_role": "deferred scale-linking note",
            "split_protocol": "not implemented in MV16 unless a separate PHQ-HAMD linking contract is predeclared",
            "claim_boundary": "PDCH remains a severity-only diagnostic/sensitivity dataset, not a shared PHQ-HAMD latent target.",
        },
    ]
    return pd.DataFrame(rows)


def calibration_item_contract() -> pd.DataFrame:
    mv14_dif = read_csv(MV14_DIR / "item_dif_stability_summary.csv")
    rows: list[dict[str, Any]] = []
    for _, row in mv14_dif.iterrows():
        construct = str(row["construct_id"])
        if construct in PRIMARY_ANCHORS:
            role = "locked_anchor"
            future_policy = "Keep loading and thresholds fixed to the source/common anchor map except for global theta scale calibration."
        elif construct in PRIMARY_THRESHOLD_DIF:
            role = "primary_dif_threshold_calibration"
            future_policy = "Calibrate target threshold offsets first; keep loading shared unless a later design predeclares loading DIF."
        elif construct == "C08":
            role = "sensitivity_possible_loading_or_threshold"
            future_policy = "Report as sensitivity; do not add it to the primary DIF-guided set unless MV16 run evidence and a later design justify it."
        else:
            role = "sensitivity_non_anchor"
            future_policy = "Keep fixed in the primary ladder; allow only aggregate sensitivity reporting."
        rows.append(
            {
                "construct_id": construct,
                "item_label_short": row["item_label_short"],
                "mv14_role": row["mv10_role"],
                "mv16_calibration_role": role,
                "loading_flag_frequency": row["loading_flag_frequency"],
                "threshold_flag_frequency": row["threshold_flag_frequency"],
                "anchor_support_frequency": row["anchor_support_frequency"],
                "future_calibration_policy": future_policy,
            }
        )
    return pd.DataFrame(rows)


def fewshot_sampling_contract() -> pd.DataFrame:
    rows = []
    for k in K_SHOTS:
        rows.append(
            {
                "k_target_labeled_subjects": k,
                "seeds": join_values(SEEDS),
                "sampling_unit": "subject",
                "stratification": "target severity quantile bins when feasible; otherwise deterministic shuffled subject order with skipped-bin reporting",
                "calibration_use": (
                    "no target labels; zero-shot source measurement only"
                    if k == 0
                    else "fit only calibration parameters allowed by the ladder row; no target eval labels"
                ),
                "eval_use": "target held-out subjects only; never include target calibration subjects in eval metrics",
                "failure_visibility": "export aggregate skipped/impossible rows if k exceeds available target calibration subjects or class/bin support is inadequate",
                "tracked_policy": "aggregate k/seed coverage and metric curves only; actual sampled subject ids stay local-only",
            }
        )
    return pd.DataFrame(rows)


def calibration_ladder_contract() -> pd.DataFrame:
    rows = [
        {
            "ladder_id": "L0_zero_shot_source_measurement",
            "calibrator": "none",
            "target_labels_used": 0,
            "free_parameters": "none beyond source-trained measurement/prediction artifacts",
            "description": "Apply the source measurement map and X-to-theta predictor to the held-out target dataset without target-label calibration.",
            "comparison_role": "required lower-bound baseline and MV12 external-transfer reproduction",
        },
        {
            "ladder_id": "L1_global_affine_theta_calibration",
            "calibrator": "theta_target = a + b * theta_source",
            "target_labels_used": "k",
            "free_parameters": "global intercept and slope only",
            "description": "Use k target-labeled subjects to learn a global affine theta-scale correction, leaving item thresholds unchanged.",
            "comparison_role": "tests whether source failure is mostly a global latent-scale mismatch",
        },
        {
            "ladder_id": "L2_global_monotonic_theta_calibration",
            "calibrator": "monotonic/isotonic theta mapping",
            "target_labels_used": "k",
            "free_parameters": "monotonic calibration function with minimum-bin guard",
            "description": "Sensitivity row for non-linear but order-preserving target theta calibration.",
            "comparison_role": "must not be used as primary evidence if k support is too sparse",
        },
        {
            "ladder_id": "L3_dif_guided_C02_C06_threshold_calibration",
            "calibrator": "target threshold offsets for C02 and C06",
            "target_labels_used": "k",
            "free_parameters": "C02 and C06 threshold offsets only; anchors C01/C04/C05/C07 fixed",
            "description": "Primary MV16 mechanism: calibrate only the localized threshold-DIF items identified by MV11/MV13/MV14.",
            "comparison_role": "preferred measurement-calibration test",
        },
        {
            "ladder_id": "L4_anchor_plus_dif_joint_calibration",
            "calibrator": "global affine theta plus C02/C06 threshold offsets",
            "target_labels_used": "k",
            "free_parameters": "global theta affine parameters and C02/C06 threshold offsets",
            "description": "Joint target calibration when global scale mismatch and localized threshold DIF both contribute.",
            "comparison_role": "secondary preferred row; must beat L1 and L3 or reveal their tradeoff",
        },
        {
            "ladder_id": "L5_all_threshold_target_calibration",
            "calibrator": "target threshold offsets for C01-C08",
            "target_labels_used": "k",
            "free_parameters": "all PHQ C01-C08 item threshold offsets",
            "description": "High-flexibility psychometric comparator with all thresholds allowed to shift.",
            "comparison_role": "upper-bound/overfit-risk comparator; not automatically preferable to L3/L4",
        },
        {
            "ladder_id": "L6_direct_target_domain_adaptation",
            "calibrator": "direct target-domain Ridge or total/item heads",
            "target_labels_used": "k",
            "free_parameters": "direct target prediction head parameters",
            "description": "Non-psychometric few-shot adaptation baseline using the same target-label budget.",
            "comparison_role": "critical comparator; if it dominates, MV16 is a practical adaptation result, not psychometric calibration evidence",
        },
    ]
    return pd.DataFrame(rows)


def model_comparison_contract() -> pd.DataFrame:
    rows = [
        {
            "model_id": "M16_B0_zero_shot_source",
            "model_family": "source_measurement_baseline",
            "uses_bge_features": True,
            "uses_target_labels_for_calibration": False,
            "expected_role": "reproduce the MV12 zero-shot source-calibrated external theta failure under the cleaned MV16 protocol",
            "must_compare_against": "all MV16 rows",
        },
        {
            "model_id": "M16_B1_train_mean_target_theta",
            "model_family": "target_label_floor",
            "uses_bge_features": False,
            "uses_target_labels_for_calibration": True,
            "expected_role": "k-shot target-label floor for theta and observed-scale reconstruction",
            "must_compare_against": "M16a/M16b/M16c/M16d",
        },
        {
            "model_id": "M16_B2_direct_itemwise_target",
            "model_family": "dimension_matched_direct_baseline",
            "uses_bge_features": True,
            "uses_target_labels_for_calibration": True,
            "expected_role": "B3-style direct itemwise comparator under the same k-shot target budget",
            "must_compare_against": "M16c/M16d",
        },
        {
            "model_id": "M16a_global_affine",
            "model_family": "global_theta_calibration",
            "uses_bge_features": True,
            "uses_target_labels_for_calibration": True,
            "expected_role": "separate global scale mismatch from item-specific threshold shift",
            "must_compare_against": "M16_B0;M16c;M16_B2",
        },
        {
            "model_id": "M16b_global_monotonic",
            "model_family": "monotonic_theta_calibration_sensitivity",
            "uses_bge_features": True,
            "uses_target_labels_for_calibration": True,
            "expected_role": "check whether affine calibration is too rigid",
            "must_compare_against": "M16a;M16c",
        },
        {
            "model_id": "M16c_dif_guided_C02_C06",
            "model_family": "localized_threshold_DIF_calibration",
            "uses_bge_features": True,
            "uses_target_labels_for_calibration": True,
            "expected_role": "primary measurement-calibration candidate",
            "must_compare_against": "M16_B0;M16a;M16d;M16_B2",
        },
        {
            "model_id": "M16d_global_plus_C02_C06",
            "model_family": "joint_global_and_localized_DIF_calibration",
            "uses_bge_features": True,
            "uses_target_labels_for_calibration": True,
            "expected_role": "preferred if both global scale and localized thresholds matter",
            "must_compare_against": "M16_B0;M16a;M16c;M16e;M16_B2",
        },
        {
            "model_id": "M16e_all_thresholds",
            "model_family": "high_flexibility_measurement_calibration",
            "uses_bge_features": True,
            "uses_target_labels_for_calibration": True,
            "expected_role": "overfit-risk upper-bound calibration comparator",
            "must_compare_against": "M16c;M16d;M16_B2",
        },
    ]
    return pd.DataFrame(rows)


def metric_contract() -> pd.DataFrame:
    rows = [
        {
            "metric_id": "M1_theta_mae",
            "metric": "Theta MAE",
            "primary": True,
            "direction": "lower_is_better",
            "scope": "target held-out subjects, by direction/k/seed/model",
            "success_interpretation": "Calibration improves latent severity transfer only if it beats zero-shot and target train-mean floors.",
        },
        {
            "metric_id": "M2_observed_macro_item_mae",
            "metric": "Observed Macro Item MAE",
            "primary": True,
            "direction": "lower_is_better",
            "scope": "C01-C08 reconstructed target item responses",
            "success_interpretation": "Theta improvement is not safe if observed-scale item reconstruction degrades against direct itemwise baselines.",
        },
        {
            "metric_id": "M3_dif_item_mae",
            "metric": "C02/C06 DIF-aware Item MAE",
            "primary": True,
            "direction": "lower_is_better",
            "scope": "localized threshold-DIF items only",
            "success_interpretation": "DIF-guided calibration should improve the items it claims to fix.",
        },
        {
            "metric_id": "M4_anchor_item_mae",
            "metric": "C01/C04/C05/C07 Anchor Item MAE",
            "primary": True,
            "direction": "lower_is_better",
            "scope": "locked anchor items",
            "success_interpretation": "C02/C06 threshold calibration must not damage stable-anchor behavior.",
        },
        {
            "metric_id": "M5_total_mae",
            "metric": "Observed Total MAE",
            "primary": False,
            "direction": "lower_is_better",
            "scope": "target held-out observed PHQ total",
            "success_interpretation": "Total-score safety guard for clinical severity interpretation.",
        },
        {
            "metric_id": "M6_rank_correlation",
            "metric": "Theta and total Spearman",
            "primary": False,
            "direction": "higher_is_better",
            "scope": "target held-out subjects",
            "success_interpretation": "Monotonic calibration should preserve severity ranking.",
        },
        {
            "metric_id": "M7_output_identity",
            "metric": "Predicted-output dataset identity BA",
            "primary": False,
            "direction": "lower_is_better",
            "scope": "pooled E-DAIC/CMDC predicted theta/items/total outputs",
            "success_interpretation": "Report shortcut risk; do not conflate output identity with upstream BGE feature invariance.",
        },
        {
            "metric_id": "M8_learning_curve",
            "metric": "Delta versus k=0 and versus direct target baseline",
            "primary": True,
            "direction": "contextual",
            "scope": "k=0/5/10/20/40 by direction",
            "success_interpretation": "MV16 is strongest if DIF-guided calibration helps at small k, not only at k=40.",
        },
    ]
    return pd.DataFrame(rows)


def input_boundary_contract() -> pd.DataFrame:
    rows = [
        {
            "input_id": "I1_aggregate_design_sources",
            "source": "MV10/MV11/MV12/MV13/MV14/MV15/full-gate aggregate artifacts",
            "used_now": True,
            "future_runner_use": "read for anchors, DIF items, prior gate status, and baseline numbers",
            "tracked_policy": "safe to track as aggregate context",
        },
        {
            "input_id": "I2_target_item_labels",
            "source": "manifest-governed E-DAIC/CMDC PHQ C01-C08 item labels",
            "used_now": False,
            "future_runner_use": "sample k target-labeled calibration subjects and evaluate held-out target subjects",
            "tracked_policy": "subject rows and sampled ids stay local-only; aggregate counts only",
        },
        {
            "input_id": "I3_aligned_bge_features",
            "source": "existing ignored/local aligned BGE subject features",
            "used_now": False,
            "future_runner_use": "train source X-to-theta and direct target adaptation baselines",
            "tracked_policy": "feature matrices stay local-only; aggregate feature-family counts only",
        },
        {
            "input_id": "I4_measurement_runtime",
            "source": "version-captured local R/mirt and Python measurement scorer",
            "used_now": False,
            "future_runner_use": "fit or replay source/target measurement calibration under the MV16 ladder",
            "tracked_policy": "runtime versions and aggregate convergence summaries only",
        },
    ]
    return pd.DataFrame(rows)


def local_only_boundary_contract() -> pd.DataFrame:
    rows = [
        {
            "artifact_class": "target_shot_sampling_maps",
            "why_local_only": "contains target participant membership and fold assignments",
            "allowed_tracked_derivative": "aggregate k/seed/direction counts and skipped-row reasons",
            "must_not_track": True,
        },
        {
            "artifact_class": "theta_tables",
            "why_local_only": "participant-grain latent scores are sensitive and can be linked to item labels",
            "allowed_tracked_derivative": "aggregate theta MAE/RMSE/Spearman and calibration summaries",
            "must_not_track": True,
        },
        {
            "artifact_class": "calibration_parameters",
            "why_local_only": "few-shot target parameters can encode target subject label information",
            "allowed_tracked_derivative": "parameter-count, convergence, and pass/fail summaries",
            "must_not_track": True,
        },
        {
            "artifact_class": "fitted_measurement_parameters",
            "why_local_only": "IRT thresholds/loadings and posterior diagnostics are model artifacts from sensitive item rows",
            "allowed_tracked_derivative": "aggregate anchor/DIF stability and item-role summaries",
            "must_not_track": True,
        },
        {
            "artifact_class": "row_level_predictions",
            "why_local_only": "per-participant predicted items/theta/total can reveal sensitive symptom estimates",
            "allowed_tracked_derivative": "aggregate metric curves by model/direction/k/seed",
            "must_not_track": True,
        },
        {
            "artifact_class": "feature_matrices_and_models",
            "why_local_only": "BGE features, fitted heads, vectorizers, and model objects are bulky and participant-grain",
            "allowed_tracked_derivative": "aggregate feature counts, model-family labels, and metrics",
            "must_not_track": True,
        },
    ]
    return pd.DataFrame(rows)


def pass_fail_gate_contract() -> pd.DataFrame:
    rows = [
        {
            "gate_id": "G1_input_scope",
            "status": "predeclared",
            "future_run_pass_rule": "Runner reads only manifest-governed PHQ item labels/features plus aggregate Phase 5 context; no raw text/media or private review material.",
            "full_method_effect": "Scope violation blocks MV16 publication and any claim refresh.",
        },
        {
            "gate_id": "G2_subject_level_fewshot_splits",
            "status": "predeclared",
            "future_run_pass_rule": "Every direction/k/seed has zero overlap among source train, target calibration, and target evaluation subjects.",
            "full_method_effect": "Any overlap blocks calibration claims.",
        },
        {
            "gate_id": "G3_ladder_completeness",
            "status": "predeclared",
            "future_run_pass_rule": "Report L0-L6 for k=0/5/10/20/40 where feasible, with skipped rows explicit and justified.",
            "full_method_effect": "Incomplete comparator ladder blocks positive MV16 interpretation.",
        },
        {
            "gate_id": "G4_dif_guided_small_k_gain",
            "status": "predeclared",
            "future_run_pass_rule": "Primary support requires L3 or L4 to improve target Theta MAE by at least 0.03 versus L0 and improve C02/C06 MAE versus L1 in both directions for at least one k<=20.",
            "full_method_effect": "If unmet, MV16 is negative or inconclusive measurement-calibration evidence.",
        },
        {
            "gate_id": "G5_anchor_safety",
            "status": "predeclared",
            "future_run_pass_rule": "L3/L4 anchor-item MAE may not degrade by more than 5 percent relative to L1 global calibration at the same k/direction.",
            "full_method_effect": "Anchor degradation blocks DIF-guided wording even if C02/C06 improve.",
        },
        {
            "gate_id": "G6_dimension_matched_baseline",
            "status": "predeclared",
            "future_run_pass_rule": "L3/L4 must be compared with B2 direct itemwise target adaptation and L6 direct target-domain adaptation under the same k; if direct baselines dominate theta and observed macro MAE, report practical adaptation rather than psychometric calibration.",
            "full_method_effect": "Direct-baseline dominance blocks a positive measurement-calibration mechanism claim.",
        },
        {
            "gate_id": "G7_identity_boundary",
            "status": "predeclared",
            "future_run_pass_rule": "Report output identity BA by model; do not report any MV16 result as BGE feature invariance because MV15 already blocked that claim.",
            "full_method_effect": "Identity wording remains diagnostic only unless a later feature-level design changes the evidence.",
        },
        {
            "gate_id": "G8_artifact_hygiene",
            "status": "predeclared",
            "future_run_pass_rule": "Tracked outputs contain only aggregate contracts, curves, metric summaries, gate results, reports, and memory.",
            "full_method_effect": "Hygiene failure blocks GitHub publishing and manuscript updates.",
        },
    ]
    return pd.DataFrame(rows)


def implementation_queue() -> pd.DataFrame:
    rows = [
        {
            "rank": 1,
            "action_id": "IMPLEMENT_MV16_DIF_GUIDED_CALIBRATION_RUNNER",
            "action": "Implement the MV16 runner with source/target directions, k=0/5/10/20/40 sampling, L0-L6 calibration ladder, direct baselines, aggregate metric curves, identity diagnostics, split audits, and hygiene checks.",
            "success_gate": "All predeclared gates are evaluated from aggregate outputs only; local theta/calibration/row artifacts remain ignored.",
            "version_policy": "Track runner, aggregate summaries, report, refreshed gates/docs/memory only.",
        },
        {
            "rank": 2,
            "action_id": "REFRESH_FULL_METHOD_GATE_AFTER_MV16_RUN",
            "action": "Rerun the full-method gate after the MV16 run and update paper claim scaffolds.",
            "success_gate": "Gate distinguishes measurement calibration evidence from feature invariance and full-method authorization.",
            "version_policy": "Track aggregate gate outputs only.",
        },
        {
            "rank": 3,
            "action_id": "OPTIONAL_MV06_AGREEMENT_UNCERTAINTY",
            "action": "If RQ4 wording becomes manuscript-critical, add aggregate agreement uncertainty and resolve the one incomplete local MV06 candidate.",
            "success_gate": "Aggregate confidence intervals remain dataset-stratified and do not expose snippets, locators, or subject rows.",
            "version_policy": "Commit aggregate summaries only.",
        },
    ]
    return pd.DataFrame(rows)


def method_source_refs() -> pd.DataFrame:
    return pd.DataFrame(METHOD_SOURCE_REFS)


def artifact_hygiene(out_dir: Path) -> dict[str, Any]:
    forbidden_patterns = [
        r"/root/autodl-tmp/datasets/",
        r"/root/\.codex/",
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
        r"raw clinical",
        r"raw prompt",
        r"raw response",
        r"password",
        r"api_key",
        r"secret",
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
        "audit_id": "P5_MV16_dif_guided_calibration_design_hygiene",
        "artifact_hygiene_passed": len(violations) == 0,
        "files_checked": checked,
        "generated_at": utc_now(),
        "violation_count": len(violations),
        "violations": violations,
    }


def md_escape(value: Any) -> str:
    return str(value).replace("|", "\\|").replace("\n", " ")


def write_report(
    out_dir: Path,
    run_summary: dict[str, Any],
    evidence: pd.DataFrame,
    directions: pd.DataFrame,
    items: pd.DataFrame,
    ladder: pd.DataFrame,
    metrics: pd.DataFrame,
    gates: pd.DataFrame,
    queue: pd.DataFrame,
) -> None:
    decision = run_summary["decision"]
    lines = [
        "# P5_MV16 DIF-Guided Few-Shot Measurement Calibration Design",
        "",
        f"Generated: `{run_summary['generated_at']}`",
        "",
        "## Scope",
        "",
        "This is a predeclared design contract. It does not run calibration, train a full method, export participant-grain theta scores, export calibration parameters, export target-shot sampling maps, or authorize feature-invariance claims.",
        "",
        "## Decision",
        "",
        f"- Design status: `{decision['design_status']}`.",
        f"- Recommended next action: `{decision['recommended_next_action']}`.",
        f"- Full method allowed: `{decision['full_method_allowed']}`.",
        f"- Artifact hygiene passed: `{run_summary['artifact_hygiene_passed']}`.",
        "",
        decision["short_read"],
        "",
        "## Source Evidence",
        "",
        "| source | status | observation | implication |",
        "| --- | --- | --- | --- |",
    ]
    for _, row in evidence.iterrows():
        lines.append(
            f"| {row['source_id']} | `{row['status']}` | "
            f"{md_escape(row['observation'])} | {md_escape(row['implication_for_mv16'])} |"
        )

    lines.extend(["", "## Directions", "", "| direction | source | target | k | boundary |", "| --- | --- | --- | --- | --- |"])
    for _, row in directions.iterrows():
        lines.append(
            f"| {row['direction_id']} | {row['source_dataset']} | {row['target_dataset']} | "
            f"{row['target_label_budget_k']} | {md_escape(row['claim_boundary'])} |"
        )

    lines.extend(["", "## Item Roles", "", "| construct | role | threshold freq | anchor support | policy |", "| --- | --- | ---: | ---: | --- |"])
    for _, row in items.iterrows():
        lines.append(
            f"| {row['construct_id']} | `{row['mv16_calibration_role']}` | "
            f"{fmt(row['threshold_flag_frequency'])} | {fmt(row['anchor_support_frequency'])} | "
            f"{md_escape(row['future_calibration_policy'])} |"
        )

    lines.extend(["", "## Calibration Ladder", "", "| ladder | target labels | free parameters | role |", "| --- | --- | --- | --- |"])
    for _, row in ladder.iterrows():
        lines.append(
            f"| {row['ladder_id']} | {row['target_labels_used']} | "
            f"{md_escape(row['free_parameters'])} | {md_escape(row['comparison_role'])} |"
        )

    lines.extend(["", "## Metrics", "", "| metric | primary | direction | interpretation |", "| --- | --- | --- | --- |"])
    for _, row in metrics.iterrows():
        lines.append(
            f"| {row['metric_id']} | `{row['primary']}` | {row['direction']} | "
            f"{md_escape(row['success_interpretation'])} |"
        )

    lines.extend(["", "## Gates", "", "| gate | status | future run rule | effect |", "| --- | --- | --- | --- |"])
    for _, row in gates.iterrows():
        lines.append(
            f"| {row['gate_id']} | `{row['status']}` | "
            f"{md_escape(row['future_run_pass_rule'])} | {md_escape(row['full_method_effect'])} |"
        )

    lines.extend(["", "## Implementation Queue", "", "| rank | action | success gate |", "| ---: | --- | --- |"])
    for _, row in queue.sort_values("rank").iterrows():
        lines.append(f"| {int(row['rank'])} | {md_escape(row['action'])} | {md_escape(row['success_gate'])} |")

    lines.extend(
        [
            "",
            "## Interpretation Boundary",
            "",
            "- MV16 can support target measurement calibration only if it beats zero-shot and dimension-matched/direct few-shot baselines under the predeclared gates.",
            "- MV16 cannot override MV15's feature-identity blocker; low output identity or improved calibration is not upstream BGE invariance.",
            "- PHQ-HAMD scale linking remains out of scope for MV16 unless a later separate contract is written.",
            "- Full M0/M1/M2/M3 method construction remains blocked until the full-method gate changes after a completed run.",
        ]
    )
    (out_dir / "report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def build_outputs(out_dir: Path, generated_at: str, overwrite: bool) -> dict[str, Any]:
    if out_dir.exists() and overwrite:
        shutil.rmtree(out_dir)
    if out_dir.exists():
        raise SystemExit(f"output directory exists; use --overwrite: {rel(out_dir)}")
    out_dir.mkdir(parents=True, exist_ok=True)

    evidence = source_evidence_summary()
    directions = dataset_direction_contract()
    items = calibration_item_contract()
    fewshot = fewshot_sampling_contract()
    ladder = calibration_ladder_contract()
    models = model_comparison_contract()
    metrics = metric_contract()
    inputs = input_boundary_contract()
    local_only = local_only_boundary_contract()
    gates = pass_fail_gate_contract()
    queue = implementation_queue()
    refs = method_source_refs()

    evidence.to_csv(out_dir / "source_evidence_summary.csv", index=False)
    directions.to_csv(out_dir / "dataset_direction_contract.csv", index=False)
    items.to_csv(out_dir / "calibration_item_contract.csv", index=False)
    fewshot.to_csv(out_dir / "fewshot_sampling_contract.csv", index=False)
    ladder.to_csv(out_dir / "calibration_ladder_contract.csv", index=False)
    models.to_csv(out_dir / "model_comparison_contract.csv", index=False)
    metrics.to_csv(out_dir / "metric_contract.csv", index=False)
    inputs.to_csv(out_dir / "input_boundary_contract.csv", index=False)
    local_only.to_csv(out_dir / "local_only_boundary_contract.csv", index=False)
    gates.to_csv(out_dir / "pass_fail_gate_contract.csv", index=False)
    queue.to_csv(out_dir / "implementation_queue.csv", index=False)
    refs.to_csv(out_dir / "method_source_refs.csv", index=False)

    run_summary = {
        "run_id": RUN_ID,
        "generated_at": generated_at,
        "scope": "dif_guided_fewshot_measurement_calibration_predeclaration_no_run",
        "status": "complete",
        "input_contract": {
            "aggregate_phase5_artifacts_read": True,
            "raw_text_or_media_read": False,
            "multimodal_features_read_now": False,
            "row_level_predictions_read": False,
            "private_review_material_read": False,
            "future_primary_datasets": ["edaic", "cmdc"],
            "future_deferred_sensitivity_datasets": ["pdch"],
            "future_feature_family": "text_bge",
            "future_label_budget_k": K_SHOTS,
            "future_identity_unit": "subject_level",
            "full_method_allowed": False,
        },
        "outputs": {
            "tracked_outputs": TRACKED_FILES,
            "source_evidence_rows": int(len(evidence)),
            "dataset_direction_rows": int(len(directions)),
            "calibration_item_rows": int(len(items)),
            "fewshot_sampling_rows": int(len(fewshot)),
            "calibration_ladder_rows": int(len(ladder)),
            "model_comparison_rows": int(len(models)),
            "metric_rows": int(len(metrics)),
            "input_boundary_rows": int(len(inputs)),
            "local_only_boundary_rows": int(len(local_only)),
            "pass_fail_gate_rows": int(len(gates)),
            "implementation_queue_rows": int(len(queue)),
            "method_source_ref_rows": int(len(refs)),
        },
        "decision": {
            "design_status": "ready_to_implement_mv16_dif_guided_calibration",
            "recommended_next_action": "implement_scripts_phase5_run_mv16_dif_guided_calibration",
            "full_method_allowed": False,
            "primary_directions": ["D1_edaic_source_cmdc_target", "D2_cmdc_source_edaic_target"],
            "primary_calibration_rows": ["L3_dif_guided_C02_C06_threshold_calibration", "L4_anchor_plus_dif_joint_calibration"],
            "primary_anchors": PRIMARY_ANCHORS,
            "primary_dif_items": PRIMARY_THRESHOLD_DIF,
            "k_shots": K_SHOTS,
            "short_read": (
                "MV16 is predeclared as a few-shot measurement-calibration test: "
                "use MV14-stable anchors C01/C04/C05/C07, calibrate localized "
                "C02/C06 threshold DIF under k=0/5/10/20/40 target-label budgets, "
                "and compare against zero-shot, global affine/monotonic, all-threshold, "
                "and direct target-adaptation baselines. It is diagnostic only."
            ),
        },
        "verdict": {
            "status": "ready_to_implement_mv16_dif_guided_calibration",
            "pass_rule_status": "design_ready_full_method_still_blocked",
            "pass_rule_met": None,
            "full_method_allowed": False,
            "short_read": "Design is ready; the actual MV16 calibration run is required before any calibration claim can change.",
        },
        "local_only_files": {
            "target_shot_sampling_maps": "all sampled target subject identifiers and split assignments",
            "theta_tables": "all participant-grain source, target, calibrated, and predicted theta tables",
            "calibration_parameters": "all affine, monotonic, threshold-offset, and direct-adaptation fitted parameters",
            "row_predictions": "all per-participant item/theta/total predictions",
            "fitted_measurement_parameters": "all IRT loadings, thresholds, posteriors, and model objects",
            "feature_matrices_and_models": "all BGE matrices and trained prediction heads",
        },
        "artifact_hygiene_passed": False,
    }

    write_json(out_dir / "run_summary.json", run_summary)
    write_report(out_dir, run_summary, evidence, directions, items, ladder, metrics, gates, queue)
    hygiene = artifact_hygiene(out_dir)
    run_summary["artifact_hygiene_passed"] = bool(hygiene["artifact_hygiene_passed"])
    write_json(out_dir / "run_summary.json", run_summary)
    write_report(out_dir, run_summary, evidence, directions, items, ladder, metrics, gates, queue)
    hygiene = artifact_hygiene(out_dir)
    write_json(out_dir / "artifact_hygiene_audit.json", hygiene)
    if not hygiene["artifact_hygiene_passed"]:
        raise SystemExit("artifact hygiene violations found; see artifact_hygiene_audit.json")
    return run_summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()

    summary = build_outputs(args.out_dir, utc_now(), args.overwrite)
    print(
        json.dumps(
            {
                "out_dir": rel(args.out_dir),
                "design_status": summary["decision"]["design_status"],
                "artifact_hygiene_passed": summary["artifact_hygiene_passed"],
            },
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
