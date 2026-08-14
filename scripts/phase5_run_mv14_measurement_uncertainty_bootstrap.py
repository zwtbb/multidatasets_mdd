#!/usr/bin/env python3
"""Run P5_MV14 measurement-uncertainty bootstrap.

MV14 is a label-only uncertainty layer for the E-DAIC/CMDC PHQ C01-C08
measurement line. Python prepares the ignored local item-response matrix from
the same manifest-governed loader used by MV10/MV13, calls an R/mirt bootstrap
runner, and exports only aggregate stability summaries.

Bootstrap response matrices, draw indices, fitted mirt objects, fitted
parameters, CI values, factor/theta scores, and detailed logs remain local-only.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import re
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd
from pandas.errors import EmptyDataError
import numpy as np

from phase5_run_mv10_psychometric_invariance_baseline import (
    CORE_CONSTRUCTS,
    DEFAULT_MANIFEST_DIR,
    ITEM_LABELS,
    ROOT,
    fmt,
    load_inputs,
)


PHASE5_DIR = ROOT / "analysis" / "phase5_minimal_validation"
DEFAULT_OUT_DIR = PHASE5_DIR / "p5_mv14_measurement_uncertainty_bootstrap"
DEFAULT_MV10_PARTIAL = PHASE5_DIR / "p5_mv10_psychometric_invariance_baseline" / "partial_invariance_summary.csv"
MV11_DIR = PHASE5_DIR / "p5_mv11_formal_psychometric_confirmation"
MV13_DIR = PHASE5_DIR / "p5_mv13_external_psychometric_replication"
R_RUNNER = ROOT / "scripts" / "phase5_run_mv14_measurement_uncertainty_bootstrap.R"

RUN_ID = "P5_MV14_measurement_uncertainty_bootstrap"
RANDOM_SEED = 20260813
DEFAULT_SMOKE_R = 10
DEFAULT_CORE_R = 200
DEFAULT_DIF_R = 100
ANCHOR_SUPPORT_STABLE = 0.70
ANCHOR_SUPPORT_DOWNGRADE = 0.60
LOADING_DIF_HIGH = 0.50
ANCHOR_LOADING_DIF_MAX = 0.30
THRESHOLD_TARGETS = {"C02", "C06"}

TRACKED_FILES = {
    "artifact_hygiene_audit.json",
    "bootstrap_ladder_realization.csv",
    "bootstrap_runtime_summary.csv",
    "core_model_stability_summary.csv",
    "gate_recommendations.csv",
    "input_boundary_contract.csv",
    "input_response_category_support.csv",
    "invariance_decision_frequency.csv",
    "item_dif_stability_summary.csv",
    "itemfit_stability_summary.csv",
    "model_selection_frequency.csv",
    "mv11_mv13_mv14_alignment_summary.csv",
    "optional_sensitivity_summary.csv",
    "pass_fail_gate_assessment.csv",
    "psychometric_input_audit.csv",
    "r_execution_summary.csv",
    "report.md",
    "run_summary.json",
    "runtime_versions.csv",
    "stable_ladder_model_selection_frequency.csv",
    "warning_failure_summary.csv",
}

LOCAL_ONLY_FILES = {
    "ignored_local_item_response_matrix": "participant-grain PHQ item response matrix without subject IDs",
    "ignored_bootstrap_resampling_draws": "created only in R memory and never exported",
}


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
    try:
        return pd.read_csv(path)
    except EmptyDataError:
        return pd.DataFrame()


def safe_float(value: Any) -> float | None:
    try:
        out = float(value)
    except (TypeError, ValueError):
        return None
    return out if math.isfinite(out) else None


def bool_series(series: pd.Series) -> pd.Series:
    if pd.api.types.is_bool_dtype(series):
        return series.fillna(False)
    return series.astype(str).str.strip().str.lower().isin({"true", "1", "yes", "y"})


def json_sanitize(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): json_sanitize(item) for key, item in value.items()}
    if isinstance(value, list):
        return [json_sanitize(item) for item in value]
    if isinstance(value, tuple):
        return [json_sanitize(item) for item in value]
    if isinstance(value, np.bool_):
        return bool(value)
    if isinstance(value, np.integer):
        return int(value)
    if isinstance(value, np.floating):
        numeric = float(value)
        return numeric if math.isfinite(numeric) else None
    return value


def first_value(frame: pd.DataFrame, key: str, value: str, field: str, default: Any = None) -> Any:
    if frame.empty or key not in frame.columns:
        return default
    rows = frame[frame[key].astype(str) == value]
    if rows.empty or field not in rows.columns:
        return default
    return rows.iloc[0].get(field, default)


def write_local_r_input(out_dir: Path, manifest_dir: Path) -> tuple[pd.DataFrame, pd.DataFrame]:
    table, input_audit = load_inputs(manifest_dir)
    response = table[["dataset", *CORE_CONSTRUCTS]].copy()
    for item in CORE_CONSTRUCTS:
        response[item] = response[item].astype(int)
    response.to_csv(out_dir / "local_mv14_phq_response_matrix.csv", index=False)
    input_audit.to_csv(out_dir / "psychometric_input_audit.csv", index=False)
    return table, input_audit


def build_response_category_support(table: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for dataset, group in table.groupby("dataset", sort=True):
        for item in CORE_CONSTRUCTS:
            values = group[item].astype(int)
            for category in range(4):
                rows.append(
                    {
                        "dataset": dataset,
                        "construct_id": item,
                        "item_label_short": ITEM_LABELS[item],
                        "response_category": category,
                        "count": int((values == category).sum()),
                        "subject_count": int(len(group)),
                        "proportion": float((values == category).mean()),
                    }
                )
    return pd.DataFrame(rows)


def build_input_boundary() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "artifact_class": "local_phq_item_response_matrix",
                "git_policy": "ignored_local_only",
                "reason": "Participant-grain PHQ item rows are analysis inputs even without IDs.",
                "allowed_tracked_derivative": "dataset-level counts and response-category support only",
            },
            {
                "artifact_class": "bootstrap_resampling_draws",
                "git_policy": "not_exported",
                "reason": "Draw indices can reveal participant-grain multiplicities and row linkage.",
                "allowed_tracked_derivative": "seed, requested R, effective R, and aggregate fit/DIF counts",
            },
            {
                "artifact_class": "fitted_mirt_model_objects",
                "git_policy": "do_not_track",
                "reason": "Fitted objects contain item parameters and internal estimation state.",
                "allowed_tracked_derivative": "fit success, convergence, information-criterion, and warning summaries",
            },
            {
                "artifact_class": "full_parameter_ci_or_theta_values",
                "git_policy": "do_not_track",
                "reason": "Full parameter, CI, factor, and theta values are fitted measurement outputs.",
                "allowed_tracked_derivative": "availability counts only if a later optional tier is run",
            },
        ]
    )


def build_ladder_realization(smoke_r: int, core_r: int, dif_r: int) -> pd.DataFrame:
    rows = [
        {
            "tier_id": "MV14_A_smoke_runtime",
            "predeclared_default_R": DEFAULT_SMOKE_R,
            "requested_R": smoke_r,
            "claim_status": "not_claimable_smoke",
            "execution_status": "requested" if smoke_r > 0 else "skipped_by_cli",
        },
        {
            "tier_id": "MV14_B_core_model_stability",
            "predeclared_default_R": DEFAULT_CORE_R,
            "requested_R": core_r,
            "claim_status": "primary_core_stability",
            "execution_status": "requested" if core_r > 0 else "skipped_by_cli",
        },
        {
            "tier_id": "MV14_C_item_DIF_stability",
            "predeclared_default_R": DEFAULT_DIF_R,
            "requested_R": dif_r,
            "claim_status": "primary_anchor_and_DIF_stability",
            "execution_status": "requested" if dif_r > 0 else "skipped_by_cli",
        },
        {
            "tier_id": "MV14_D_boot_mirt_SE_availability",
            "predeclared_default_R": 100,
            "requested_R": 0,
            "claim_status": "optional_parameter_uncertainty_availability",
            "execution_status": "skipped_runtime_bounded_optional",
        },
        {
            "tier_id": "MV14_E_parametric_LR_sensitivity",
            "predeclared_default_R": 100,
            "requested_R": 0,
            "claim_status": "optional_nested_LRT_uncertainty",
            "execution_status": "skipped_runtime_bounded_optional",
        },
    ]
    return pd.DataFrame(rows)


def run_r_bootstrap(
    out_dir: Path,
    local_input: Path,
    mv10_partial: Path,
    seed: int,
    smoke_r: int,
    core_r: int,
    dif_r: int,
    collect_itemfit: bool,
    timeout_seconds: int,
) -> dict[str, Any]:
    rscript = shutil.which("Rscript")
    if not rscript:
        raise RuntimeError("Rscript is not available on PATH")
    env = os.environ.copy()
    env.setdefault("OMP_NUM_THREADS", "1")
    env.setdefault("OPENBLAS_NUM_THREADS", "1")
    env.setdefault("MKL_NUM_THREADS", "1")
    result = subprocess.run(
        [
            rscript,
            str(R_RUNNER),
            str(local_input),
            str(mv10_partial),
            str(out_dir),
            str(seed),
            str(smoke_r),
            str(core_r),
            str(dif_r),
            "true" if collect_itemfit else "false",
        ],
        cwd=ROOT,
        env=env,
        text=True,
        capture_output=True,
        check=False,
        timeout=timeout_seconds,
    )
    if result.returncode != 0:
        raise RuntimeError(
            "R MV14 bootstrap runner failed with return code "
            f"{result.returncode}: {result.stderr[-2000:]}"
        )
    return {
        "returncode": result.returncode,
        "stdout_tail": result.stdout[-1000:],
        "stderr_tail": result.stderr[-1000:],
    }


def frequency_map(frame: pd.DataFrame, field: str) -> dict[str, float | None]:
    if frame.empty or field not in frame.columns:
        return {}
    out: dict[str, float | None] = {}
    for _, row in frame.iterrows():
        out[str(row["construct_id"])] = safe_float(row.get(field))
    return out


def top_selection(selection: pd.DataFrame, tier_id: str, criterion: str) -> str:
    if selection.empty:
        return "NA"
    rows = selection[
        (selection["tier_id"].astype(str) == tier_id)
        & (selection["criterion"].astype(str) == criterion)
    ].copy()
    if rows.empty:
        return "NA"
    rows["_freq"] = pd.to_numeric(rows["selection_frequency"], errors="coerce")
    rows = rows.sort_values(["_freq", "model_id"], ascending=[False, True])
    return str(rows.iloc[0]["model_id"])


def first_numeric(frame: pd.DataFrame, field: str, default: int = 0) -> int:
    if frame.empty or field not in frame.columns:
        return default
    value = safe_float(frame.iloc[0].get(field))
    return int(value) if value is not None else default


def determine_verdict(out_dir: Path, requested: dict[str, int], r_meta: dict[str, Any]) -> dict[str, Any]:
    runtime = read_csv(out_dir / "bootstrap_runtime_summary.csv")
    core = read_csv(out_dir / "core_model_stability_summary.csv")
    selection = read_csv(out_dir / "model_selection_frequency.csv")
    stable_selection = read_csv(out_dir / "stable_ladder_model_selection_frequency.csv")
    dif = read_csv(out_dir / "item_dif_stability_summary.csv")
    itemfit = read_csv(out_dir / "itemfit_stability_summary.csv")

    smoke_done = requested["smoke_r"] == 0 or (
        not core.empty and (core["tier_id"].astype(str) == "MV14_A_smoke_runtime").any()
    )
    core_done = requested["core_r"] == 0 or (
        not core.empty and (core["tier_id"].astype(str) == "MV14_B_core_model_stability").any()
    )
    dif_done = requested["dif_r"] == 0 or (
        not dif.empty and (dif["tier_id"].astype(str) == "MV14_C_item_DIF_stability").any()
    )

    core_selection_rows = selection[
        (selection.get("tier_id", pd.Series(dtype=str)).astype(str) == "MV14_B_core_model_stability")
        & (selection.get("criterion", pd.Series(dtype=str)).astype(str) == "aic")
    ]
    core_selection_ref = core_selection_rows[core_selection_rows.get("model_id", pd.Series(dtype=str)).astype(str) == "configural"]
    core_effective = first_numeric(core_selection_ref, "effective_draws", 0)
    core_attempted = first_numeric(core_selection_ref, "attempted_draws", requested["core_r"])
    core_all_fit_success = first_numeric(core_selection_ref, "all_fit_success_draws", 0)
    core_all_converged = first_numeric(core_selection_ref, "all_converged_draws", 0)
    if core_effective == 0 and requested["core_r"] == 0:
        smoke_selection_rows = selection[
            (selection.get("tier_id", pd.Series(dtype=str)).astype(str) == "MV14_A_smoke_runtime")
            & (selection.get("criterion", pd.Series(dtype=str)).astype(str) == "aic")
        ]
        core_selection_ref = smoke_selection_rows[
            smoke_selection_rows.get("model_id", pd.Series(dtype=str)).astype(str) == "configural"
        ]
        core_effective = first_numeric(core_selection_ref, "effective_draws", 0)
        core_attempted = first_numeric(core_selection_ref, "attempted_draws", requested["smoke_r"])
        core_all_fit_success = first_numeric(core_selection_ref, "all_fit_success_draws", 0)
        core_all_converged = first_numeric(core_selection_ref, "all_converged_draws", 0)

    configural_core = core[
        (core.get("tier_id", pd.Series(dtype=str)).astype(str) == "MV14_B_core_model_stability")
        & (core.get("model_id", pd.Series(dtype=str)).astype(str) == "configural")
    ]
    configural_fit_success = first_numeric(configural_core, "fit_success_draws", 0)
    configural_converged = first_numeric(configural_core, "converged_draws", 0)
    configural_convergence_rate = safe_float(first_value(configural_core, "model_id", "configural", "convergence_rate", None))

    stable_selection_rows = stable_selection[
        (stable_selection.get("tier_id", pd.Series(dtype=str)).astype(str) == "MV14_B_core_model_stability")
        & (stable_selection.get("criterion", pd.Series(dtype=str)).astype(str) == "aic")
    ]
    stable_ref = stable_selection_rows[
        stable_selection_rows.get("model_id", pd.Series(dtype=str)).astype(str) == "metric"
    ]
    stable_ladder_effective = first_numeric(stable_ref, "effective_draws", 0)

    dif_effective = int(pd.to_numeric(dif.get("anchor_support_effective_draws", pd.Series(dtype=float)), errors="coerce").min()) if not dif.empty else 0
    if not dif.empty and "anchor_support_attempted_draws" in dif.columns:
        dif_attempted = int(
            pd.to_numeric(dif["anchor_support_attempted_draws"], errors="coerce").min()
        )
    else:
        dif_attempted = requested["dif_r"]

    anchor_items = ["C01", "C04", "C05", "C07"]
    anchor_support = frequency_map(dif, "anchor_support_frequency")
    loading_freq = frequency_map(dif, "loading_flag_frequency")
    threshold_freq = frequency_map(dif, "threshold_flag_frequency")

    stable_anchor_items = [
        item for item in anchor_items if (anchor_support.get(item) is not None and anchor_support[item] >= ANCHOR_SUPPORT_STABLE)
    ]
    low_anchor_items = [
        item for item in anchor_items if (anchor_support.get(item) is None or anchor_support[item] < ANCHOR_SUPPORT_DOWNGRADE)
    ]
    anchors_stable = requested["dif_r"] > 0 and len(stable_anchor_items) == len(anchor_items)
    high_loading_items = [
        item for item, value in loading_freq.items() if value is not None and value > LOADING_DIF_HIGH
    ]
    anchor_loading_high = [
        item for item in anchor_items if loading_freq.get(item) is not None and loading_freq[item] >= ANCHOR_LOADING_DIF_MAX
    ]
    loading_sparse = requested["dif_r"] > 0 and len(high_loading_items) <= 1 and not anchor_loading_high
    threshold_ranked = sorted(
        ((item, value) for item, value in threshold_freq.items() if value is not None),
        key=lambda pair: (-pair[1], pair[0]),
    )
    top_threshold_items = [item for item, _ in threshold_ranked[:2]]
    threshold_localized = requested["dif_r"] > 0 and THRESHOLD_TARGETS.issubset(set(top_threshold_items))

    best_aic_tier = "MV14_B_core_model_stability" if requested["core_r"] > 0 else "MV14_A_smoke_runtime"
    best_aic_model = top_selection(selection, best_aic_tier, "aic")
    best_bic_model = top_selection(selection, best_aic_tier, "bic")
    stable_ladder_best_aic_model = top_selection(stable_selection, best_aic_tier, "aic")
    stable_ladder_best_bic_model = top_selection(stable_selection, best_aic_tier, "bic")
    itemfit_available = (
        not itemfit.empty
        and int(pd.to_numeric(itemfit.get("itemfit_available_draws", pd.Series(dtype=float)), errors="coerce").fillna(0).sum()) > 0
    )

    smoke_only = requested["core_r"] == 0 and requested["dif_r"] == 0
    if smoke_only and smoke_done:
        status = "complete_mv14_smoke_not_claimable"
    elif not smoke_done or not core_done:
        status = "blocked_mv14_core_bootstrap_not_completed"
    elif requested["core_r"] > 0 and core_effective <= 0:
        status = "blocked_mv14_core_bootstrap_no_effective_draws"
    elif requested["dif_r"] > 0 and (not dif_done or dif_effective <= 0):
        status = "blocked_mv14_dif_bootstrap_no_effective_draws"
    elif anchors_stable and loading_sparse and threshold_localized:
        status = "complete_mv14_convergence_safe_item_level_measurement_shift"
    else:
        status = "complete_mv14_uncertainty_requires_downgraded_item_wording"

    return {
        "status": status,
        "external_engine": "R mirt::multipleGroup",
        "r_returncode": r_meta["returncode"],
        "requested_smoke_R": requested["smoke_r"],
        "requested_core_R": requested["core_r"],
        "requested_dif_R": requested["dif_r"],
        "smoke_completed": smoke_done,
        "core_completed": core_done,
        "dif_completed": dif_done,
        "core_effective_draws": int(core_effective),
        "core_selection_attempted_draws": int(core_attempted),
        "core_all_fit_success_draws": int(core_all_fit_success),
        "core_all_converged_draws": int(core_all_converged),
        "configural_fit_success_draws": int(configural_fit_success),
        "configural_converged_draws": int(configural_converged),
        "configural_convergence_rate": configural_convergence_rate,
        "stable_ladder_effective_draws": int(stable_ladder_effective),
        "dif_attempted_draws": int(dif_attempted),
        "dif_min_anchor_effective_draws": int(dif_effective),
        "best_aic_model": best_aic_model,
        "best_bic_model": best_bic_model,
        "stable_ladder_best_aic_model": stable_ladder_best_aic_model,
        "stable_ladder_best_bic_model": stable_ladder_best_bic_model,
        "stable_anchor_items": stable_anchor_items,
        "low_anchor_items": low_anchor_items,
        "anchors_stable": anchors_stable,
        "high_loading_dif_items": high_loading_items,
        "anchor_loading_dif_high_items": anchor_loading_high,
        "loading_dif_sparse": loading_sparse,
        "top_threshold_dif_items": top_threshold_items,
        "threshold_dif_localized_to_C02_C06": threshold_localized,
        "itemfit_available": itemfit_available,
        "full_method_allowed": False,
        "pass_rule_met": status == "complete_mv14_convergence_safe_item_level_measurement_shift",
        "short_read": (
            "MV14 quantifies PHQ measurement uncertainty from group-wise subject bootstrap; "
            "its convergence-safe interpretation is item-level threshold/localization evidence, "
            "not a global partial-invariance model-selection win or full multimodal method authorization."
        ),
    }


def build_alignment(out_dir: Path, verdict: dict[str, Any]) -> pd.DataFrame:
    mv11 = read_json(MV11_DIR / "run_summary.json").get("verdict") or {}
    mv13 = read_json(MV13_DIR / "run_summary.json").get("verdict") or {}
    mv13_anchor = read_csv(MV13_DIR / "anchor_confirmation_summary.csv")
    mv14_dif = read_csv(out_dir / "item_dif_stability_summary.csv")

    mv13_anchors = set(
        mv13_anchor.loc[bool_series(mv13_anchor["mv10_anchor_confirmed"]), "construct_id"].astype(str)
    )
    mv13_loading = set(
        mv13_anchor.loc[bool_series(mv13_anchor["loading_dif_flag"]), "construct_id"].astype(str)
    )
    mv13_threshold = set(
        mv13_anchor.loc[bool_series(mv13_anchor["threshold_dif_flag"]), "construct_id"].astype(str)
    )
    mv14_anchors = set(verdict["stable_anchor_items"])
    loading_freq = frequency_map(mv14_dif, "loading_flag_frequency")
    threshold_freq = frequency_map(mv14_dif, "threshold_flag_frequency")
    mv14_loading_high = {item for item, value in loading_freq.items() if value is not None and value > LOADING_DIF_HIGH}
    mv14_threshold_high = {item for item, value in threshold_freq.items() if value is not None and value >= 0.50}

    rows = [
        {
            "alignment_id": "mv10_anchor_set_vs_mv14_stable_anchors",
            "mv11_value": ";".join(["C01", "C04", "C05", "C07"]),
            "mv13_value": ";".join(sorted(mv13_anchors)) or "none",
            "mv14_value": ";".join(sorted(mv14_anchors)) or "none",
            "aligned": mv13_anchors == mv14_anchors,
            "interpretation": "Stable anchors require bootstrap support frequency at least 0.70.",
        },
        {
            "alignment_id": "loading_dif_sparsity",
            "mv11_value": str(mv11.get("loading_dif_flagged_items")),
            "mv13_value": ";".join(sorted(mv13_loading)) or "none",
            "mv14_value": ";".join(sorted(mv14_loading_high)) or "none",
            "aligned": len(mv14_loading_high) <= 1 and not mv13_loading,
            "interpretation": "High MV14 loading-DIF frequency uses the predeclared >0.50 rule.",
        },
        {
            "alignment_id": "threshold_dif_localization",
            "mv11_value": str(mv11.get("threshold_dif_flagged_items")),
            "mv13_value": ";".join(sorted(mv13_threshold)) or "none",
            "mv14_value": ";".join(sorted(mv14_threshold_high)) or "none",
            "aligned": THRESHOLD_TARGETS.issubset(set(verdict["top_threshold_dif_items"])),
            "interpretation": "Threshold-DIF wording is strongest if C02 and C06 remain the top two frequencies.",
        },
        {
            "alignment_id": "aic_model_preference",
            "mv11_value": str(mv11.get("best_aic_model")),
            "mv13_value": str(mv13.get("best_aic_model")),
            "mv14_value": str(verdict["best_aic_model"]),
            "aligned": str(mv13.get("best_aic_model")) == str(verdict["best_aic_model"]),
            "interpretation": "AIC full-ladder preference is convergence-safe and reported as model-selection sensitivity, not a global-invariance proof.",
        },
        {
            "alignment_id": "bic_model_preference",
            "mv11_value": str(mv11.get("best_bic_model")),
            "mv13_value": str(mv13.get("best_bic_model")),
            "mv14_value": str(verdict["best_bic_model"]),
            "aligned": str(mv13.get("best_bic_model")) == str(verdict["best_bic_model"]),
            "interpretation": "BIC model preference is summarized separately because its complexity penalty answers a different question from LRT/AIC.",
        },
        {
            "alignment_id": "stable_ladder_sensitivity",
            "mv11_value": "metric;partial_mv10;scalar",
            "mv13_value": "metric/partial/scalar mostly converged",
            "mv14_value": (
                f"AIC={verdict['stable_ladder_best_aic_model']};"
                f"BIC={verdict['stable_ladder_best_bic_model']};"
                f"effective={verdict['stable_ladder_effective_draws']}"
            ),
            "aligned": verdict["stable_ladder_effective_draws"] > 0,
            "interpretation": "Stable-ladder sensitivity excludes configural because configural convergence is the main numerical instability.",
        },
    ]
    return pd.DataFrame(rows)


def build_gate_assessment(verdict: dict[str, Any]) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "gate_id": "G3_convergence_visibility",
                "status": "pass_with_global_model_selection_downgrade" if verdict["core_completed"] else "blocked",
                "evidence": (
                    f"Core attempted {verdict['core_selection_attempted_draws']}; "
                    f"full-ladder fit-success {verdict['core_all_fit_success_draws']}; "
                    f"full-ladder converged {verdict['core_all_converged_draws']}; "
                    f"configural converged {verdict['configural_converged_draws']}."
                ),
                "claim_effect": "Global model-selection and configural LRT wording must be downgraded when convergence is limited.",
            },
            {
                "gate_id": "G4_anchor_stability",
                "status": "pass" if verdict["anchors_stable"] else "downgrade_or_pending",
                "evidence": f"Stable anchors: {';'.join(verdict['stable_anchor_items']) or 'none'}; low anchors: {';'.join(verdict['low_anchor_items']) or 'none'}.",
                "claim_effect": "Anchor wording is cautious unless all four MV10 anchors exceed the support threshold.",
            },
            {
                "gate_id": "G5_loading_DIF_sparsity",
                "status": "pass" if verdict["loading_dif_sparse"] else "downgrade",
                "evidence": f"High loading-DIF items: {';'.join(verdict['high_loading_dif_items']) or 'none'}; anchor high-loading items: {';'.join(verdict['anchor_loading_dif_high_items']) or 'none'}.",
                "claim_effect": "Diffuse loading DIF downgrades common-metric wording.",
            },
            {
                "gate_id": "G6_threshold_DIF_localization",
                "status": "pass" if verdict["threshold_dif_localized_to_C02_C06"] else "downgrade",
                "evidence": f"Top threshold-DIF items: {';'.join(verdict['top_threshold_dif_items']) or 'none'}.",
                "claim_effect": "C02/C06 wording is strongest only if bootstrap frequencies remain concentrated there.",
            },
            {
                "gate_id": "G8_no_full_method_authorization",
                "status": "pass",
                "evidence": "MV14 is label-only measurement uncertainty evidence.",
                "claim_effect": "Full M0/M1/M2/M3 remains blocked.",
            },
        ]
    )


def build_gate_recommendations(verdict: dict[str, Any]) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "recommendation_id": "measurement_uncertainty_boundary",
                "status": verdict["status"],
                "recommendation": "Use MV14 for item-level PHQ anchor/DIF stability and convergence-aware model-selection uncertainty wording.",
                "evidence": (
                    f"Full-ladder convergence-safe R {verdict['core_effective_draws']}/"
                    f"{verdict['core_selection_attempted_draws']}; DIF effective R "
                    f"{verdict['dif_min_anchor_effective_draws']}/"
                    f"{verdict['dif_attempted_draws']}."
                ),
            },
            {
                "recommendation_id": "anchor_wording",
                "status": "stable" if verdict["anchors_stable"] else "downgrade_or_pending",
                "recommendation": "Describe C01/C04/C05/C07 as stable anchors only when all four support frequencies pass the predeclared threshold.",
                "evidence": f"Stable anchors: {';'.join(verdict['stable_anchor_items']) or 'none'}.",
            },
            {
                "recommendation_id": "dif_wording",
                "status": "localized" if verdict["threshold_dif_localized_to_C02_C06"] else "downgrade",
                "recommendation": "Report loading-DIF sparsity and threshold-DIF localization separately.",
                "evidence": f"Top threshold-DIF items: {';'.join(verdict['top_threshold_dif_items']) or 'none'}.",
            },
            {
                "recommendation_id": "global_invariance_wording",
                "status": "downgrade_to_uncertain",
                "recommendation": "Do not summarize MV14 as bootstrap-confirmed partial invariance; report substantial common PHQ structure with localized threshold non-equivalence and uncertain global model selection.",
                "evidence": (
                    f"Configural converged {verdict['configural_converged_draws']}/"
                    f"{verdict['core_selection_attempted_draws']}; stable-ladder effective R "
                    f"{verdict['stable_ladder_effective_draws']}."
                ),
            },
            {
                "recommendation_id": "full_method_gate",
                "status": "keep_blocked",
                "recommendation": "Do not start full M0/M1/M2/M3 from MV14 alone.",
                "evidence": "MV14 checks Y-layer measurement uncertainty, not X-to-theta prediction or cross-dataset calibration.",
            },
        ]
    )


def md_escape(value: Any) -> str:
    text = "" if value is None else str(value)
    return text.replace("|", "\\|").replace("\n", " ")


def write_report(out_dir: Path, run_summary: dict[str, Any]) -> None:
    verdict = run_summary["verdict"]
    runtime = read_csv(out_dir / "bootstrap_runtime_summary.csv")
    core = read_csv(out_dir / "core_model_stability_summary.csv")
    selection = read_csv(out_dir / "model_selection_frequency.csv")
    stable_selection = read_csv(out_dir / "stable_ladder_model_selection_frequency.csv")
    decisions = read_csv(out_dir / "invariance_decision_frequency.csv")
    dif = read_csv(out_dir / "item_dif_stability_summary.csv")
    gate = read_csv(out_dir / "gate_recommendations.csv")

    lines = [
        "# P5 MV14 Measurement-Uncertainty Bootstrap",
        "",
        f"Generated: `{run_summary['generated_at']}`",
        "",
        "## Scope",
        "",
        "MV14 uses group-wise subject bootstrap over the E-DAIC/CMDC PHQ C01-C08 item-response boundary to quantify measurement-model uncertainty. It writes aggregate stability summaries only.",
        "",
        "## Verdict",
        "",
        f"- Status: `{verdict['status']}`.",
        f"- Requested R: smoke `{verdict['requested_smoke_R']}`, core `{verdict['requested_core_R']}`, DIF `{verdict['requested_dif_R']}`.",
        f"- Core convergence-safe full-ladder draws: `{verdict['core_effective_draws']}` / `{verdict['core_selection_attempted_draws']}`.",
        f"- Core full-ladder fit-success/converged draws: `{verdict['core_all_fit_success_draws']}` / `{verdict['core_all_converged_draws']}`.",
        f"- Configural fit-success/converged draws: `{verdict['configural_fit_success_draws']}` / `{verdict['configural_converged_draws']}`.",
        f"- DIF minimum effective anchor draws: `{verdict['dif_min_anchor_effective_draws']}` / `{verdict['dif_attempted_draws']}`.",
        f"- Best full-ladder AIC/BIC model: `{verdict['best_aic_model']}` / `{verdict['best_bic_model']}`.",
        f"- Best stable-ladder AIC/BIC model: `{verdict['stable_ladder_best_aic_model']}` / `{verdict['stable_ladder_best_bic_model']}`.",
        f"- Stable anchors: `{';'.join(verdict['stable_anchor_items']) or 'none'}`.",
        f"- Top threshold-DIF items: `{';'.join(verdict['top_threshold_dif_items']) or 'none'}`.",
        f"- Artifact hygiene passed: `{run_summary['artifact_hygiene_passed']}`.",
        "",
        "## Runtime",
        "",
        "| tier | requested R | effective draws | seconds | claim status |",
        "| --- | ---: | ---: | ---: | --- |",
    ]
    for _, row in runtime.iterrows():
        lines.append(
            f"| {row['tier_id']} | {int(row['requested_R'])} | "
            f"{'' if pd.isna(row['primary_effective_draws']) else int(row['primary_effective_draws'])} | "
            f"{fmt(row['elapsed_seconds'], 1)} | `{row['claim_status']}` |"
        )

    lines.extend(
        [
            "",
            "## Core Stability",
            "",
            "| tier | model | fit success | convergence | warnings | errors |",
            "| --- | --- | ---: | ---: | ---: | ---: |",
        ]
    )
    for _, row in core.iterrows():
        lines.append(
            f"| {row['tier_id']} | {row['model_id']} | {fmt(row['fit_success_rate'])} | "
            f"{fmt(row['convergence_rate'])} | {int(row['warning_draws'])} | {int(row['error_draws'])} |"
        )

    lines.extend(
        [
            "",
            "## Full-Ladder Model Selection",
            "",
            "| tier | criterion | model | frequency | attempted | fit-success | converged | effective |",
            "| --- | --- | --- | ---: | ---: | ---: | ---: | ---: |",
        ]
    )
    for _, row in selection.iterrows():
        if safe_float(row.get("selection_frequency")) is None or row["selection_frequency"] <= 0:
            continue
        lines.append(
            f"| {row['tier_id']} | {row['criterion']} | {row['model_id']} | "
            f"{fmt(row['selection_frequency'])} | {int(row['attempted_draws'])} | "
            f"{int(row['all_fit_success_draws'])} | {int(row['all_converged_draws'])} | "
            f"{int(row['effective_draws'])} |"
        )

    lines.extend(
        [
            "",
            "## Stable-Ladder Sensitivity",
            "",
            "| tier | criterion | model | frequency | attempted | fit-success | converged | effective |",
            "| --- | --- | --- | ---: | ---: | ---: | ---: | ---: |",
        ]
    )
    for _, row in stable_selection.iterrows():
        if safe_float(row.get("selection_frequency")) is None or row["selection_frequency"] <= 0:
            continue
        lines.append(
            f"| {row['tier_id']} | {row['criterion']} | {row['model_id']} | "
            f"{fmt(row['selection_frequency'])} | {int(row['attempted_draws'])} | "
            f"{int(row['all_fit_success_draws'])} | {int(row['all_converged_draws'])} | "
            f"{int(row['effective_draws'])} |"
        )

    lines.extend(
        [
            "",
            "## LRT Decision Stability",
            "",
            "| tier | comparison | decision | attempted freq | valid freq | attempted | valid | failed |",
            "| --- | --- | --- | ---: | ---: | ---: | ---: | ---: |",
        ]
    )
    for _, row in decisions.iterrows():
        attempted_freq = safe_float(row.get("decision_frequency"))
        valid_freq = safe_float(row.get("valid_decision_frequency"))
        if attempted_freq is None or attempted_freq <= 0:
            continue
        lines.append(
            f"| {row['tier_id']} | {row['comparison_id']} | `{row['decision']}` | "
            f"{fmt(attempted_freq)} | {fmt(valid_freq)} | {int(row['attempted_draws'])} | "
            f"{int(row['effective_draws'])} | {int(row['failed_draws'])} |"
        )

    lines.extend(
        [
            "",
            "## Item Stability",
            "",
            "| item | MV10 role | loading DIF freq | loading eff | threshold DIF freq | threshold eff | anchor support freq | anchor eff | threshold rank |",
            "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
        ]
    )
    for _, row in dif.iterrows():
        loading_eff = int(row["loading_effective_draws"]) if pd.notna(row.get("loading_effective_draws")) else 0
        loading_attempted = int(row["loading_attempted_draws"]) if pd.notna(row.get("loading_attempted_draws")) else verdict["requested_dif_R"]
        threshold_eff = int(row["threshold_effective_draws"]) if pd.notna(row.get("threshold_effective_draws")) else 0
        threshold_attempted = int(row["threshold_attempted_draws"]) if pd.notna(row.get("threshold_attempted_draws")) else verdict["requested_dif_R"]
        anchor_eff = int(row["anchor_support_effective_draws"]) if pd.notna(row.get("anchor_support_effective_draws")) else 0
        anchor_attempted = int(row["anchor_support_attempted_draws"]) if pd.notna(row.get("anchor_support_attempted_draws")) else verdict["requested_dif_R"]
        lines.append(
            f"| {row['construct_id']} {row['item_label_short']} | `{row['mv10_role']}` | "
            f"{fmt(row['loading_flag_frequency'])} | {loading_eff}/{loading_attempted} | "
            f"{fmt(row['threshold_flag_frequency'])} | {threshold_eff}/{threshold_attempted} | "
            f"{fmt(row['anchor_support_frequency'])} | {anchor_eff}/{anchor_attempted} | "
            f"{'' if pd.isna(row['threshold_frequency_rank']) else int(row['threshold_frequency_rank'])} |"
        )

    lines.extend(
        [
            "",
            "## Gate Recommendations",
            "",
            "| recommendation | status | evidence |",
            "| --- | --- | --- |",
        ]
    )
    for _, row in gate.iterrows():
        lines.append(f"| {row['recommendation_id']} | `{row['status']}` | {md_escape(row['evidence'])} |")

    lines.extend(
        [
            "",
            "## Interpretation Boundary",
            "",
            "- MV14 is label-only measurement uncertainty evidence, not multimodal method evidence.",
            "- Model-selection and LRT summaries are convergence-safe: non-converged fits remain visible in attempted/failed denominators and do not enter AIC/BIC or LRT decisions.",
            "- Do not summarize MV14 as a global partial-invariance win; use item-level wording around stable anchors, sparse loading DIF, localized C02/C06 threshold non-equivalence, and global model-selection uncertainty.",
            "- Public outputs contain aggregate counts, frequencies, intervals, version rows, and bounded warning categories only.",
            "- Local item-response matrices, resampling draws, fitted parameters, CI values, factor/theta scores, model objects, and detailed logs are not tracked.",
            "- Full method construction remains blocked pending later predeclared MV15/MV16-style evidence.",
        ]
    )
    (out_dir / "report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def artifact_hygiene(out_dir: Path) -> dict[str, Any]:
    forbidden_patterns = [
        r"/root/",
        r"/autodl-tmp/",
        r"\bsubject_id\b",
        r"\bsubject_key\b",
        r"audio_path",
        r"video_path",
        r"text_path",
        r"gait_path",
        r"\.wav\b",
        r"\.mp4\b",
        r"\.avi\b",
        r"local_mv14_phq_response_matrix",
        r"local_mirt_phq_response_matrix",
        r"bootstrap_draw_index",
        r"\brow_index\b",
        r"posterior_score",
        r"factor_score_value",
        r"theta_score_value",
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
        "audit_id": "P5_MV14_measurement_uncertainty_bootstrap_hygiene",
        "generated_at": utc_now(),
        "files_checked": checked,
        "artifact_hygiene_passed": not violations,
        "violation_count": len(violations),
        "violations": violations,
    }


def build_outputs(
    out_dir: Path,
    manifest_dir: Path,
    mv10_partial: Path,
    seed: int,
    smoke_r: int,
    core_r: int,
    dif_r: int,
    collect_itemfit: bool,
    timeout_seconds: int,
) -> dict[str, Any]:
    if out_dir.exists():
        shutil.rmtree(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    table, input_audit = write_local_r_input(out_dir, manifest_dir)
    build_response_category_support(table).to_csv(out_dir / "input_response_category_support.csv", index=False)
    build_input_boundary().to_csv(out_dir / "input_boundary_contract.csv", index=False)
    build_ladder_realization(smoke_r, core_r, dif_r).to_csv(out_dir / "bootstrap_ladder_realization.csv", index=False)

    r_meta = run_r_bootstrap(
        out_dir=out_dir,
        local_input=out_dir / "local_mv14_phq_response_matrix.csv",
        mv10_partial=mv10_partial,
        seed=seed,
        smoke_r=smoke_r,
        core_r=core_r,
        dif_r=dif_r,
        collect_itemfit=collect_itemfit,
        timeout_seconds=timeout_seconds,
    )
    verdict = determine_verdict(
        out_dir,
        {"smoke_r": smoke_r, "core_r": core_r, "dif_r": dif_r},
        r_meta,
    )
    build_alignment(out_dir, verdict).to_csv(out_dir / "mv11_mv13_mv14_alignment_summary.csv", index=False)
    build_gate_assessment(verdict).to_csv(out_dir / "pass_fail_gate_assessment.csv", index=False)
    build_gate_recommendations(verdict).to_csv(out_dir / "gate_recommendations.csv", index=False)

    subjects = {
        str(row["dataset"]): int(row["complete_item_subjects"])
        for _, row in input_audit.iterrows()
    }
    run_summary = {
        "run_id": RUN_ID,
        "generated_at": utc_now(),
        "status": "complete",
        "scope": "label_only_measurement_uncertainty_bootstrap",
        "input_contract": {
            "datasets": ["edaic", "cmdc"],
            "scales": ["PHQ-8", "PHQ-9"],
            "shared_items": CORE_CONSTRUCTS,
            "subjects": subjects,
            "label_only": True,
            "manifest_governed_item_loader": True,
            "multimodal_features_read": False,
            "raw_text_or_media_read": False,
            "row_level_predictions_read": False,
            "subject_ids_exported": False,
            "full_method_allowed": False,
        },
        "output_policy": {
            "tracked_outputs": sorted(TRACKED_FILES),
            "local_only_files": LOCAL_ONLY_FILES,
            "fitted_parameters_exported": False,
            "factor_or_theta_scores_exported": False,
            "fitted_model_objects_exported": False,
            "bootstrap_draws_exported": False,
        },
        "verdict": verdict,
        "artifact_hygiene_passed": False,
    }
    run_summary = json_sanitize(run_summary)
    (out_dir / "run_summary.json").write_text(json.dumps(run_summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    write_report(out_dir, run_summary)
    hygiene = artifact_hygiene(out_dir)
    run_summary["artifact_hygiene_passed"] = bool(hygiene["artifact_hygiene_passed"])
    (out_dir / "run_summary.json").write_text(json.dumps(run_summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    write_report(out_dir, run_summary)
    hygiene = artifact_hygiene(out_dir)
    (out_dir / "artifact_hygiene_audit.json").write_text(json.dumps(hygiene, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if not hygiene["artifact_hygiene_passed"]:
        raise SystemExit("artifact hygiene violations found; see artifact_hygiene_audit.json")
    return run_summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest-dir", type=Path, default=DEFAULT_MANIFEST_DIR)
    parser.add_argument("--mv10-partial", type=Path, default=DEFAULT_MV10_PARTIAL)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--seed", type=int, default=RANDOM_SEED)
    parser.add_argument("--smoke-r", type=int, default=DEFAULT_SMOKE_R)
    parser.add_argument("--core-r", type=int, default=DEFAULT_CORE_R)
    parser.add_argument("--dif-r", type=int, default=DEFAULT_DIF_R)
    parser.add_argument("--smoke-only", action="store_true")
    parser.add_argument("--skip-itemfit", action="store_true")
    parser.add_argument("--timeout-seconds", type=int, default=21600)
    args = parser.parse_args()

    smoke_r = args.smoke_r
    core_r = 0 if args.smoke_only else args.core_r
    dif_r = 0 if args.smoke_only else args.dif_r
    if smoke_r < 0 or core_r < 0 or dif_r < 0:
        raise SystemExit("R counts must be non-negative")

    run_summary = build_outputs(
        out_dir=args.out_dir,
        manifest_dir=args.manifest_dir,
        mv10_partial=args.mv10_partial,
        seed=args.seed,
        smoke_r=smoke_r,
        core_r=core_r,
        dif_r=dif_r,
        collect_itemfit=not args.skip_itemfit,
        timeout_seconds=args.timeout_seconds,
    )
    print(
        json.dumps(
            {
                "out_dir": rel(args.out_dir),
                "status": run_summary["verdict"]["status"],
                "artifact_hygiene_passed": run_summary["artifact_hygiene_passed"],
                "requested_core_R": run_summary["verdict"]["requested_core_R"],
                "requested_dif_R": run_summary["verdict"]["requested_dif_R"],
                "core_effective_draws": run_summary["verdict"]["core_effective_draws"],
                "dif_min_anchor_effective_draws": run_summary["verdict"]["dif_min_anchor_effective_draws"],
            },
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
