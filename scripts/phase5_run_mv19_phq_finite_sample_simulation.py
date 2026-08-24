#!/usr/bin/env python3
"""Run P5_MV19 finite-sample PHQ psychometric simulation.

MV19 is a label-only simulation layer for the E-DAIC/CMDC PHQ C01-C08
measurement line. It stress-tests the current MV10/MV14 item-level decision
pattern at the observed complete-case sample sizes and severity distributions.

It does not train multimodal models, read raw text/media, export real
participant identifiers, export fitted psychometric parameters, export theta
scores, or export simulated participant-grain response rows.
"""

from __future__ import annotations

import argparse
import json
import math
import re
import shutil
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from phase5_run_mv10_psychometric_invariance_baseline import (
    CORE_CONSTRUCTS,
    DEFAULT_MANIFEST_DIR,
    ITEM_LABELS,
    ROOT,
    THRESHOLD_LOCATION_DELTA_TOL,
    THRESHOLDS,
    build_stage_summary,
    fit_binary_logit,
    fmt,
    item_distribution_summary,
    loading_invariance_summary,
    load_inputs,
    partial_invariance_summary,
    reliability_dimensionality_summary,
    safe_float,
    threshold_dif_summary,
)


PHASE5_DIR = ROOT / "analysis" / "phase5_minimal_validation"
DEFAULT_OUT_DIR = PHASE5_DIR / "p5_mv19_phq_finite_sample_psychometric_simulation"
MV10_DIR = PHASE5_DIR / "p5_mv10_psychometric_invariance_baseline"
MV14_DIR = PHASE5_DIR / "p5_mv14_measurement_uncertainty_bootstrap"

RUN_ID = "P5_MV19_phq_finite_sample_psychometric_simulation"
RANDOM_SEED = 20260822
DEFAULT_SIMULATIONS = 500
THETA_JITTER_SD = 0.15

ANCHOR_ITEMS = ["C01", "C04", "C05", "C07"]
TARGET_DIF_ITEMS = ["C02", "C06"]
H0_FALSE_LOCALIZATION_MAX = 0.20
H1_TARGET_BOTH_FLAGGED_MIN = 0.60
H1_TARGET_TOP2_MIN = 0.50
ANCHOR_TARGET_RECOVERY_MIN = 0.60

TRACKED_FILES = {
    "anchor_recovery_summary.csv",
    "artifact_hygiene_audit.json",
    "effect_size_contract.csv",
    "gate_recommendations.csv",
    "input_boundary_contract.csv",
    "item_flag_rate_summary.csv",
    "observed_input_audit.csv",
    "observed_response_category_support.csv",
    "report.md",
    "run_summary.json",
    "simulation_design_contract.csv",
    "simulation_world_summary.csv",
}

HYGIENE_CHECKED_FILES = TRACKED_FILES - {"artifact_hygiene_audit.json"}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def md_escape(value: Any) -> str:
    text = "" if value is None else str(value)
    return text.replace("|", "\\|").replace("\n", " ")


def sigmoid(value: np.ndarray | float) -> np.ndarray | float:
    arr = np.asarray(value, dtype=float)
    out = np.empty_like(arr, dtype=float)
    positive = arr >= 0
    out[positive] = 1.0 / (1.0 + np.exp(-arr[positive]))
    exp_x = np.exp(arr[~positive])
    out[~positive] = exp_x / (1.0 + exp_x)
    if np.isscalar(value):
        return float(out)
    return out


def logit(probability: float) -> float:
    clipped = min(max(float(probability), 1e-6), 1.0 - 1e-6)
    return math.log(clipped / (1.0 - clipped))


def wilson_interval(successes: int, n: int, z: float = 1.959963984540054) -> tuple[float, float]:
    if n <= 0:
        return float("nan"), float("nan")
    p = successes / n
    denom = 1.0 + (z * z / n)
    centre = p + (z * z / (2.0 * n))
    margin = z * math.sqrt((p * (1.0 - p) + z * z / (4.0 * n)) / n)
    return (centre - margin) / denom, (centre + margin) / denom


def bool_rate_summary(values: pd.Series) -> dict[str, Any]:
    clean = values.astype(bool)
    successes = int(clean.sum())
    total = int(len(clean))
    low, high = wilson_interval(successes, total)
    return {
        "successes": successes,
        "attempts": total,
        "rate": float(successes / total) if total else float("nan"),
        "ci95_low": low,
        "ci95_high": high,
    }


def split_items(value: Any) -> set[str]:
    text = "" if value is None else str(value)
    if not text or text == "none":
        return set()
    return {item for item in text.split(";") if item}


def build_observed_theta(table: pd.DataFrame) -> pd.DataFrame:
    out = table.copy()
    mean = float(out["core_total"].mean())
    std = float(out["core_total"].std(ddof=0)) or 1.0
    out["theta_proxy_z"] = (out["core_total"].astype(float) - mean) / std
    return out


def fit_generation_models(observed: pd.DataFrame) -> dict[tuple[str, int], dict[str, Any]]:
    models: dict[tuple[str, int], dict[str, Any]] = {}
    theta = observed["theta_proxy_z"].to_numpy(dtype=float).reshape(-1, 1)
    for item in CORE_CONSTRUCTS:
        values = observed[item].to_numpy(dtype=float)
        for threshold in THRESHOLDS:
            y = (values >= float(threshold)).astype(int)
            fitted = fit_binary_logit(theta, y)
            if fitted is None:
                positive_rate = float(np.mean(y))
                models[(item, threshold)] = {
                    "fit_kind": "empirical_positive_rate_fallback",
                    "positive_rate": positive_rate,
                    "intercept": logit(positive_rate),
                    "coef": 0.0,
                    "theta_mean": 0.0,
                    "theta_scale": 1.0,
                }
                continue
            scaler = fitted["scaler"]
            models[(item, threshold)] = {
                "fit_kind": fitted["kind"],
                "positive_rate": float(np.mean(y)),
                "intercept": float(fitted["intercept"]),
                "coef": float(fitted["coef"][0]),
                "theta_mean": float(scaler.mean_[0]),
                "theta_scale": float(scaler.scale_[0]) if float(scaler.scale_[0]) != 0 else 1.0,
            }
    return models


def load_h1_offsets() -> pd.DataFrame:
    threshold = pd.read_csv(MV10_DIR / "threshold_dif_summary.csv")
    rows: list[dict[str, Any]] = []
    for item in CORE_CONSTRUCTS:
        item_rows = threshold[threshold["construct_id"].astype(str) == item]
        if item_rows.empty:
            raise ValueError(f"missing MV10 threshold rows for {item}")
        for threshold_value in THRESHOLDS:
            row = item_rows[item_rows["threshold"].astype(int) == threshold_value]
            if row.empty:
                raise ValueError(f"missing MV10 threshold row for {item}>={threshold_value}")
            first = row.iloc[0]
            observed_coef = safe_float(first.get("dataset_logit_coef"))
            offset = observed_coef if item in TARGET_DIF_ITEMS and observed_coef is not None else 0.0
            rows.append(
                {
                    "construct_id": item,
                    "item_label_short": ITEM_LABELS[item],
                    "threshold": int(threshold_value),
                    "h0_cmdc_logit_offset": 0.0,
                    "h1_cmdc_logit_offset": float(offset),
                    "observed_mv10_dataset_logit_coef": observed_coef,
                    "observed_abs_threshold_location_delta": safe_float(first.get("abs_threshold_location_delta")),
                    "target_h1_dif_item": item in TARGET_DIF_ITEMS,
                    "effect_source": "MV10 observed dataset-logit coefficient for C02/C06; zero for all other items",
                }
            )
    return pd.DataFrame(rows)


def predict_threshold_probability(model: dict[str, Any], theta_z: np.ndarray, offset: float) -> np.ndarray:
    scaled = (theta_z - float(model["theta_mean"])) / float(model["theta_scale"])
    logits = float(model["intercept"]) + float(model["coef"]) * scaled + float(offset)
    return np.asarray(sigmoid(logits), dtype=float)


def monotone_cumulative(probabilities: list[np.ndarray]) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    p1 = np.clip(probabilities[0], 1e-6, 1.0 - 1e-6)
    p2 = np.minimum(np.clip(probabilities[1], 1e-6, 1.0 - 1e-6), p1)
    p3 = np.minimum(np.clip(probabilities[2], 1e-6, 1.0 - 1e-6), p2)
    return p1, p2, p3


def sample_ordinal_from_cumulative(
    p1: np.ndarray,
    p2: np.ndarray,
    p3: np.ndarray,
    rng: np.random.Generator,
) -> np.ndarray:
    probs = np.column_stack([1.0 - p1, p1 - p2, p2 - p3, p3])
    probs = np.clip(probs, 0.0, 1.0)
    probs = probs / probs.sum(axis=1, keepdims=True)
    cumulative = np.cumsum(probs, axis=1)
    draws = rng.random(size=probs.shape[0])
    return (draws[:, None] > cumulative[:, :-1]).sum(axis=1).astype(int)


def simulate_table(
    observed: pd.DataFrame,
    models: dict[tuple[str, int], dict[str, Any]],
    offsets: pd.DataFrame,
    world_id: str,
    rng: np.random.Generator,
) -> pd.DataFrame:
    offset_map = {
        (str(row["construct_id"]), int(row["threshold"])): float(row["h1_cmdc_logit_offset"])
        for _, row in offsets.iterrows()
    }
    frames: list[pd.DataFrame] = []
    for dataset, group in observed.groupby("dataset", sort=False):
        theta_pool = group["theta_proxy_z"].to_numpy(dtype=float)
        n = int(len(group))
        theta_z = rng.choice(theta_pool, size=n, replace=True)
        theta_z = theta_z + rng.normal(0.0, THETA_JITTER_SD, size=n)
        frame = pd.DataFrame(
            {
                "dataset": dataset,
                "scale": str(group["scale"].iloc[0]),
                "theta_proxy_z": theta_z,
            }
        )
        for item in CORE_CONSTRUCTS:
            cumulative: list[np.ndarray] = []
            for threshold_value in THRESHOLDS:
                cmdc_offset = 0.0
                if world_id == "H1_C02_C06_threshold_DIF" and dataset == "cmdc":
                    cmdc_offset = offset_map[(item, threshold_value)]
                cumulative.append(
                    predict_threshold_probability(models[(item, threshold_value)], theta_z, cmdc_offset)
                )
            p1, p2, p3 = monotone_cumulative(cumulative)
            frame[item] = sample_ordinal_from_cumulative(p1, p2, p3, rng)
        frame["core_total"] = frame[CORE_CONSTRUCTS].sum(axis=1).astype(float)
        frame["full_total"] = frame["core_total"]
        frames.append(frame.drop(columns=["theta_proxy_z"]))
    return pd.concat(frames, ignore_index=True)


def analyze_simulated_table(table: pd.DataFrame) -> dict[str, Any]:
    reliability, loadings = reliability_dimensionality_summary(table)
    loading = loading_invariance_summary(loadings)
    threshold = threshold_dif_summary(table)
    partial = partial_invariance_summary(loading, threshold)
    stage, verdict = build_stage_summary(table, reliability, loadings, loading, threshold, partial)

    threshold_flags = sorted(
        threshold.loc[
            threshold["threshold_screen_status"].astype(str) == "threshold_dif_flag",
            "construct_id",
        ]
        .astype(str)
        .unique()
        .tolist()
    )
    loading_flags = sorted(
        loading.loc[
            loading["metric_screen_status"].astype(str) == "metric_dif_flag",
            "construct_id",
        ]
        .astype(str)
        .unique()
        .tolist()
    )
    anchor_candidates = sorted(
        partial.loc[
            partial["partial_invariance_role"].astype(str) == "anchor_candidate",
            "construct_id",
        ]
        .astype(str)
        .tolist()
    )
    item_delta_rows = []
    for item, group in threshold.groupby("construct_id", sort=False):
        valid = pd.to_numeric(group["abs_threshold_location_delta"], errors="coerce").dropna()
        item_delta_rows.append(
            {
                "construct_id": str(item),
                "max_delta": float(valid.max()) if not valid.empty else float("-inf"),
            }
        )
    item_delta = pd.DataFrame(item_delta_rows)
    item_delta = item_delta.sort_values(["max_delta", "construct_id"], ascending=[False, True])
    top2 = item_delta.head(2)["construct_id"].astype(str).tolist()
    target_set = set(TARGET_DIF_ITEMS)
    anchor_set = set(ANCHOR_ITEMS)
    return {
        "configural_screen_pass": bool(verdict["configural_screen_pass"]),
        "metric_invariant_items": int(verdict["metric_invariant_items"]),
        "threshold_invariant_items": int(verdict["threshold_invariant_items"]),
        "anchor_candidate_items": int(verdict["anchor_candidate_items"]),
        "mean_abs_threshold_delta": float(verdict["mean_abs_threshold_delta"]),
        "max_abs_threshold_delta": float(verdict["max_abs_threshold_delta"]),
        "threshold_flag_items": ";".join(threshold_flags) if threshold_flags else "none",
        "threshold_flag_item_count": int(len(threshold_flags)),
        "loading_flag_items": ";".join(loading_flags) if loading_flags else "none",
        "loading_flag_item_count": int(len(loading_flags)),
        "anchor_candidates": ";".join(anchor_candidates) if anchor_candidates else "none",
        "anchor_target_subset_recovered": anchor_set.issubset(set(anchor_candidates)),
        "exact_anchor_set_recovered": set(anchor_candidates) == anchor_set,
        "target_both_flagged": target_set.issubset(set(threshold_flags)),
        "target_exact_threshold_flag_set": set(threshold_flags) == target_set,
        "target_top2_recovered": set(top2) == target_set,
        "top2_threshold_delta_items": ";".join(top2) if top2 else "none",
        "any_threshold_dif_flag": bool(threshold_flags),
        "any_non_target_threshold_dif_flag": bool(set(threshold_flags) - target_set),
        "c02_max_threshold_delta": float(
            item_delta.loc[item_delta["construct_id"] == "C02", "max_delta"].iloc[0]
        ),
        "c06_max_threshold_delta": float(
            item_delta.loc[item_delta["construct_id"] == "C06", "max_delta"].iloc[0]
        ),
        "mv10_status": str(verdict["status"]),
        "stage_threshold_status": str(
            stage.loc[stage["stage"].astype(str) == "threshold_scalar_screen", "status"].iloc[0]
        ),
    }


def simulation_design_contract(simulations: int) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "contract_id": "S001_world_H0",
                "world_id": "H0_scalar_invariant",
                "description": "Same pooled item response functions for both datasets; dataset-specific severity distributions and observed complete-case N are retained.",
                "decision_readout": "False-DIF and false-localization rates under the current MV10 screen.",
            },
            {
                "contract_id": "S002_world_H1",
                "world_id": "H1_C02_C06_threshold_DIF",
                "description": "C02 and C06 receive CMDC threshold logit offsets copied from the observed MV10 dataset-logit coefficients; other item thresholds remain invariant.",
                "decision_readout": "C02/C06 recovery, top-two localization, and anchor recovery under observed-like threshold DIF.",
            },
            {
                "contract_id": "S003_sample_size",
                "world_id": "both",
                "description": "Each simulated dataset keeps the observed complete-item subject counts from MV10.",
                "decision_readout": "Finite-sample behavior at the observed E-DAIC/CMDC PHQ item-labeled N.",
            },
            {
                "contract_id": "S004_severity_distribution",
                "world_id": "both",
                "description": f"Latent severity proxy is sampled from each dataset's empirical shared PHQ total z distribution with Gaussian jitter SD {THETA_JITTER_SD}.",
                "decision_readout": "Severity-composition differences are retained instead of equalized away.",
            },
            {
                "contract_id": "S005_detection_pipeline",
                "world_id": "both",
                "description": "Each simulated draw is evaluated with the MV10 approximate loading, threshold, and partial-anchor screen.",
                "decision_readout": "Comparable to the MV10/MV14 item-level anchor and threshold-DIF wording, not a new formal mirt bootstrap.",
            },
            {
                "contract_id": "S006_repetitions",
                "world_id": "both",
                "description": f"{simulations} simulations per world using a fixed RNG seed.",
                "decision_readout": "Aggregate recovery and false-positive rates with Wilson 95 percent intervals.",
            },
        ]
    )


def input_boundary_contract() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "artifact_class": "observed_phq_complete_case_rows",
                "git_policy": "not_exported_by_mv19",
                "reason": "Real participant-grain PHQ item responses remain analysis input even without identifiers.",
                "allowed_tracked_derivative": "dataset-level sample size and response-category support only",
            },
            {
                "artifact_class": "simulated_participant_response_rows",
                "git_policy": "not_exported",
                "reason": "Participant-grain simulated rows are unnecessary for paper claims and can be regenerated.",
                "allowed_tracked_derivative": "world-level and item-level recovery summaries",
            },
            {
                "artifact_class": "draw_level_decision_table",
                "git_policy": "ignored_local_only",
                "reason": "Per-draw diagnostics are debugging material rather than paper evidence.",
                "allowed_tracked_derivative": "rates, counts, and confidence intervals by simulation world and item",
            },
            {
                "artifact_class": "fitted_generation_models",
                "git_policy": "not_exported",
                "reason": "Generation coefficients are in-memory simulation scaffolding, not a claim artifact.",
                "allowed_tracked_derivative": "effect-size contract and positive-rate support",
            },
        ]
    )


def response_category_support(table: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for dataset, group in table.groupby("dataset", sort=False):
        for item in CORE_CONSTRUCTS:
            values = group[item].astype(int)
            for category in range(4):
                rows.append(
                    {
                        "dataset": dataset,
                        "construct_id": item,
                        "item_label_short": ITEM_LABELS[item],
                        "response_category": int(category),
                        "count": int((values == category).sum()),
                        "subject_count": int(len(values)),
                        "proportion": float((values == category).mean()),
                    }
                )
    return pd.DataFrame(rows)


def summarize_worlds(draws: pd.DataFrame) -> pd.DataFrame:
    boolean_metrics = [
        "any_threshold_dif_flag",
        "any_non_target_threshold_dif_flag",
        "target_both_flagged",
        "target_exact_threshold_flag_set",
        "target_top2_recovered",
        "anchor_target_subset_recovered",
        "exact_anchor_set_recovered",
        "configural_screen_pass",
    ]
    numeric_metrics = [
        "threshold_flag_item_count",
        "loading_flag_item_count",
        "anchor_candidate_items",
        "mean_abs_threshold_delta",
        "max_abs_threshold_delta",
        "c02_max_threshold_delta",
        "c06_max_threshold_delta",
    ]
    rows: list[dict[str, Any]] = []
    for world, group in draws.groupby("world_id", sort=False):
        row: dict[str, Any] = {"world_id": world, "simulations": int(len(group))}
        for metric in boolean_metrics:
            summary = bool_rate_summary(group[metric])
            row[f"{metric}_successes"] = summary["successes"]
            row[f"{metric}_rate"] = summary["rate"]
            row[f"{metric}_ci95_low"] = summary["ci95_low"]
            row[f"{metric}_ci95_high"] = summary["ci95_high"]
        for metric in numeric_metrics:
            values = pd.to_numeric(group[metric], errors="coerce").dropna()
            row[f"{metric}_mean"] = float(values.mean()) if not values.empty else np.nan
            row[f"{metric}_p025"] = float(values.quantile(0.025)) if not values.empty else np.nan
            row[f"{metric}_p500"] = float(values.quantile(0.500)) if not values.empty else np.nan
            row[f"{metric}_p975"] = float(values.quantile(0.975)) if not values.empty else np.nan
        rows.append(row)
    return pd.DataFrame(rows)


def item_flag_rate_summary(draws: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for world, group in draws.groupby("world_id", sort=False):
        for item in CORE_CONSTRUCTS:
            threshold_membership = group["threshold_flag_items"].map(lambda value: item in split_items(value))
            loading_membership = group["loading_flag_items"].map(lambda value: item in split_items(value))
            anchor_membership = group["anchor_candidates"].map(lambda value: item in split_items(value))
            top2_membership = group["top2_threshold_delta_items"].map(lambda value: item in split_items(value))
            threshold_summary = bool_rate_summary(threshold_membership)
            loading_summary = bool_rate_summary(loading_membership)
            anchor_summary = bool_rate_summary(anchor_membership)
            top2_summary = bool_rate_summary(top2_membership)
            rows.append(
                {
                    "world_id": world,
                    "construct_id": item,
                    "item_label_short": ITEM_LABELS[item],
                    "target_h1_dif_item": item in TARGET_DIF_ITEMS,
                    "predeclared_anchor_item": item in ANCHOR_ITEMS,
                    "simulations": int(len(group)),
                    "threshold_flag_rate": threshold_summary["rate"],
                    "threshold_flag_ci95_low": threshold_summary["ci95_low"],
                    "threshold_flag_ci95_high": threshold_summary["ci95_high"],
                    "loading_flag_rate": loading_summary["rate"],
                    "anchor_candidate_rate": anchor_summary["rate"],
                    "top2_threshold_delta_rate": top2_summary["rate"],
                }
            )
    return pd.DataFrame(rows)


def anchor_recovery_summary(draws: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for world, group in draws.groupby("world_id", sort=False):
        subset = bool_rate_summary(group["anchor_target_subset_recovered"])
        exact = bool_rate_summary(group["exact_anchor_set_recovered"])
        rows.append(
            {
                "world_id": world,
                "anchor_rule": "all_predeclared_anchor_items_present",
                "items": ";".join(ANCHOR_ITEMS),
                "successes": subset["successes"],
                "simulations": subset["attempts"],
                "recovery_rate": subset["rate"],
                "ci95_low": subset["ci95_low"],
                "ci95_high": subset["ci95_high"],
            }
        )
        rows.append(
            {
                "world_id": world,
                "anchor_rule": "exact_predeclared_anchor_set",
                "items": ";".join(ANCHOR_ITEMS),
                "successes": exact["successes"],
                "simulations": exact["attempts"],
                "recovery_rate": exact["rate"],
                "ci95_low": exact["ci95_low"],
                "ci95_high": exact["ci95_high"],
            }
        )
    return pd.DataFrame(rows)


def world_row(world_summary: pd.DataFrame, world_id: str) -> pd.Series:
    rows = world_summary[world_summary["world_id"].astype(str) == world_id]
    if rows.empty:
        raise ValueError(f"missing world summary for {world_id}")
    return rows.iloc[0]


def determine_verdict(world_summary: pd.DataFrame) -> dict[str, Any]:
    h0 = world_row(world_summary, "H0_scalar_invariant")
    h1 = world_row(world_summary, "H1_C02_C06_threshold_DIF")

    h0_target_both = float(h0["target_both_flagged_rate"])
    h0_top2 = float(h0["target_top2_recovered_rate"])
    h1_target_both = float(h1["target_both_flagged_rate"])
    h1_top2 = float(h1["target_top2_recovered_rate"])
    h1_anchor_subset = float(h1["anchor_target_subset_recovered_rate"])

    high_false_localization = (
        h0_target_both > H0_FALSE_LOCALIZATION_MAX
        or h0_top2 > H0_FALSE_LOCALIZATION_MAX
    )
    target_recovered = (
        h1_target_both >= H1_TARGET_BOTH_FLAGGED_MIN
        and h1_top2 >= H1_TARGET_TOP2_MIN
    )
    anchors_recovered = h1_anchor_subset >= ANCHOR_TARGET_RECOVERY_MIN

    if high_false_localization:
        pass_rule_status = "complete_mv19_high_false_localization_downgrade_c02_c06"
    elif target_recovered and anchors_recovered:
        pass_rule_status = "complete_mv19_observed_n_supports_cautious_c02_c06_recovery"
    elif h1_target_both < 0.50 or h1_anchor_subset < 0.50:
        pass_rule_status = "complete_mv19_low_power_hypothesis_generating"
    else:
        pass_rule_status = "complete_mv19_mixed_finite_sample_support"

    return {
        "pass_rule_status": pass_rule_status,
        "pass_rule_met": pass_rule_status == "complete_mv19_observed_n_supports_cautious_c02_c06_recovery",
        "full_method_allowed": False,
        "h0_target_both_false_rate": h0_target_both,
        "h0_target_top2_false_rate": h0_top2,
        "h0_any_threshold_false_positive_rate": float(h0["any_threshold_dif_flag_rate"]),
        "h0_any_non_target_threshold_false_positive_rate": float(h0["any_non_target_threshold_dif_flag_rate"]),
        "h1_target_both_recovery_rate": h1_target_both,
        "h1_target_top2_recovery_rate": h1_top2,
        "h1_exact_target_flag_set_rate": float(h1["target_exact_threshold_flag_set_rate"]),
        "h1_anchor_target_subset_recovery_rate": h1_anchor_subset,
        "h1_exact_anchor_set_recovery_rate": float(h1["exact_anchor_set_recovered_rate"]),
        "false_localization_gate_passed": not high_false_localization,
        "target_recovery_gate_passed": target_recovered,
        "anchor_recovery_gate_passed": anchors_recovered,
        "target_dif_items": TARGET_DIF_ITEMS,
        "anchor_items": ANCHOR_ITEMS,
        "short_read": (
            "MV19 simulates the observed E-DAIC/CMDC PHQ sample sizes and severity distributions under "
            "scalar-invariant and C02/C06 threshold-DIF worlds. It supports cautious C02/C06 wording only "
            "if false localization is limited and H1 recovery is adequate; it does not authorize a full method."
        ),
    }


def gate_recommendations(verdict: dict[str, Any]) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "recommendation_id": "finite_sample_boundary",
                "status": verdict["pass_rule_status"],
                "recommendation": "Use MV19 as an observed-N sensitivity layer for E-DAIC/CMDC dataset-group PHQ measurement-shift wording.",
                "evidence": (
                    f"H0 C02/C06 both-flag false rate {fmt(verdict['h0_target_both_false_rate'])}; "
                    f"H1 C02/C06 both-flag recovery {fmt(verdict['h1_target_both_recovery_rate'])}."
                ),
            },
            {
                "recommendation_id": "c02_c06_wording",
                "status": "cautious_supported" if verdict["pass_rule_met"] else "downgrade_or_hypothesis_generating",
                "recommendation": "Describe C02/C06 as localized dataset-group threshold non-equivalence only with finite-sample caveats.",
                "evidence": (
                    f"False-localization gate={verdict['false_localization_gate_passed']}; "
                    f"target-recovery gate={verdict['target_recovery_gate_passed']}."
                ),
            },
            {
                "recommendation_id": "anchor_wording",
                "status": "supported" if verdict["anchor_recovery_gate_passed"] else "downgrade",
                "recommendation": "Keep C01/C04/C05/C07 anchor wording only if the predeclared anchor set is recoverable under H1.",
                "evidence": f"H1 anchor subset recovery {fmt(verdict['h1_anchor_target_subset_recovery_rate'])}.",
            },
            {
                "recommendation_id": "full_method_gate",
                "status": "keep_blocked",
                "recommendation": "Do not use finite-sample label simulation to authorize M0/M1/M2/M3 construction.",
                "evidence": "MV19 is a label-only measurement-sensitivity analysis; it reads no multimodal features.",
            },
        ]
    )


def write_report(out_dir: Path, run_summary: dict[str, Any]) -> None:
    verdict = run_summary["verdict"]
    world = pd.read_csv(out_dir / "simulation_world_summary.csv")
    item = pd.read_csv(out_dir / "item_flag_rate_summary.csv")
    gate = pd.read_csv(out_dir / "gate_recommendations.csv")

    lines = [
        "# P5 MV19 PHQ Finite-Sample Psychometric Simulation",
        "",
        f"Generated: `{run_summary['generated_at']}`",
        "",
        "## Scope",
        "",
        "MV19 is a label-only observed-N simulation for the E-DAIC/CMDC PHQ C01-C08 measurement line. It retains dataset-specific sample sizes and severity composition, then compares a scalar-invariant world with an observed-like C02/C06 threshold-DIF world.",
        "",
        "## Verdict",
        "",
        f"- Status: `{verdict['pass_rule_status']}`.",
        f"- H0 C02/C06 both-flag false rate: `{fmt(verdict['h0_target_both_false_rate'])}`.",
        f"- H0 C02/C06 top-two false-localization rate: `{fmt(verdict['h0_target_top2_false_rate'])}`.",
        f"- H1 C02/C06 both-flag recovery rate: `{fmt(verdict['h1_target_both_recovery_rate'])}`.",
        f"- H1 C02/C06 top-two recovery rate: `{fmt(verdict['h1_target_top2_recovery_rate'])}`.",
        f"- H1 anchor subset recovery rate for C01/C04/C05/C07: `{fmt(verdict['h1_anchor_target_subset_recovery_rate'])}`.",
        f"- Artifact hygiene passed: `{run_summary['artifact_hygiene_passed']}`.",
        "",
        "## World Summary",
        "",
        "| world | simulations | any threshold flag | C02/C06 both flagged | C02/C06 top-two | anchor subset |",
        "| --- | ---: | ---: | ---: | ---: | ---: |",
    ]
    for _, row in world.iterrows():
        lines.append(
            f"| `{row['world_id']}` | {int(row['simulations'])} | "
            f"{fmt(row['any_threshold_dif_flag_rate'])} | "
            f"{fmt(row['target_both_flagged_rate'])} | "
            f"{fmt(row['target_top2_recovered_rate'])} | "
            f"{fmt(row['anchor_target_subset_recovered_rate'])} |"
        )
    lines.extend(
        [
            "",
            "## Item Flag Rates",
            "",
            "| world | item | target | anchor | threshold flag | anchor candidate | top-two delta |",
            "| --- | --- | --- | --- | ---: | ---: | ---: |",
        ]
    )
    for _, row in item.iterrows():
        lines.append(
            f"| `{row['world_id']}` | {row['construct_id']} {row['item_label_short']} | "
            f"`{row['target_h1_dif_item']}` | `{row['predeclared_anchor_item']}` | "
            f"{fmt(row['threshold_flag_rate'])} | {fmt(row['anchor_candidate_rate'])} | "
            f"{fmt(row['top2_threshold_delta_rate'])} |"
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
        lines.append(
            f"| {row['recommendation_id']} | `{row['status']}` | {md_escape(row['evidence'])} |"
        )
    lines.extend(
        [
            "",
            "## Interpretation Boundary",
            "",
            "- MV19 tests finite-sample behavior of the current label-only MV10 screen; it is not a full external mirt bootstrap and not a multimodal method result.",
            "- The PHQ result should remain dataset-group measurement-shift wording, not a clean PHQ-8 versus PHQ-9 scale-specific claim.",
            "- Participant-grain observed rows, simulated rows, generation coefficients, and per-draw diagnostics remain local-only or in-memory.",
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
        r"local_annotation_workbook",
        r"source_locator",
        r"raw prompt",
        r"raw response",
        r"raw clinical",
        r"p5_mv[0-9a-z_]*_local_",
    ]
    violations: list[dict[str, str]] = []
    checked = 0
    for name in HYGIENE_CHECKED_FILES:
        path = out_dir / name
        if not path.exists():
            violations.append({"file": name, "pattern": "missing_tracked_output"})
            continue
        checked += 1
        text = path.read_text(encoding="utf-8", errors="ignore")
        for pattern in forbidden_patterns:
            if re.search(pattern, text, flags=re.IGNORECASE):
                violations.append({"file": name, "pattern": pattern})
    return {
        "artifact_hygiene_passed": not violations,
        "audit_id": "P5_MV19_phq_finite_sample_simulation_hygiene",
        "files_checked": checked,
        "generated_at": utc_now(),
        "violation_count": len(violations),
        "violations": violations,
    }


def build_outputs(out_dir: Path, manifest_dir: Path, simulations: int, seed: int) -> dict[str, Any]:
    if simulations <= 0:
        raise ValueError("simulations must be positive")
    start = time.perf_counter()
    if out_dir.exists():
        shutil.rmtree(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    observed, input_audit = load_inputs(manifest_dir)
    observed = build_observed_theta(observed)
    models = fit_generation_models(observed)
    offsets = load_h1_offsets()
    rng = np.random.default_rng(seed)

    draw_rows: list[dict[str, Any]] = []
    for world_id in ["H0_scalar_invariant", "H1_C02_C06_threshold_DIF"]:
        for draw_id in range(simulations):
            simulated = simulate_table(observed, models, offsets, world_id, rng)
            decision = analyze_simulated_table(simulated)
            decision.update({"world_id": world_id, "draw_id": int(draw_id)})
            draw_rows.append(decision)

    draws = pd.DataFrame(draw_rows)
    world_summary = summarize_worlds(draws)
    item_summary = item_flag_rate_summary(draws)
    anchor_summary = anchor_recovery_summary(draws)
    verdict = determine_verdict(world_summary)
    gate = gate_recommendations(verdict)
    design = simulation_design_contract(simulations)
    boundaries = input_boundary_contract()
    category_support = response_category_support(observed.drop(columns=["theta_proxy_z"]))

    input_audit.to_csv(out_dir / "observed_input_audit.csv", index=False)
    category_support.to_csv(out_dir / "observed_response_category_support.csv", index=False)
    offsets.to_csv(out_dir / "effect_size_contract.csv", index=False)
    design.to_csv(out_dir / "simulation_design_contract.csv", index=False)
    boundaries.to_csv(out_dir / "input_boundary_contract.csv", index=False)
    world_summary.to_csv(out_dir / "simulation_world_summary.csv", index=False)
    item_summary.to_csv(out_dir / "item_flag_rate_summary.csv", index=False)
    anchor_summary.to_csv(out_dir / "anchor_recovery_summary.csv", index=False)
    gate.to_csv(out_dir / "gate_recommendations.csv", index=False)
    draws.to_csv(out_dir / "local_mv19_draw_level_decisions.csv", index=False)

    run_summary = {
        "artifact_hygiene_passed": False,
        "generated_at": utc_now(),
        "input_contract": {
            "datasets": ["edaic", "cmdc"],
            "full_method_allowed": False,
            "label_only": True,
            "manifest_governed_item_loader": True,
            "multimodal_features_read": False,
            "raw_text_or_media_read": False,
            "row_level_predictions_read": False,
            "scales": ["PHQ-8", "PHQ-9"],
            "shared_items": CORE_CONSTRUCTS,
            "real_participant_identifiers_exported": False,
            "subjects": {
                str(row["dataset"]): int(row["complete_item_subjects"])
                for _, row in input_audit.iterrows()
            },
        },
        "output_policy": {
            "draw_level_diagnostics_tracked": False,
            "fitted_generation_models_exported": False,
            "fitted_parameters_exported": False,
            "participant_grain_simulated_rows_exported": False,
            "real_participant_rows_exported": False,
            "theta_scores_exported": False,
            "local_only_files": {
                "ignored_mv19_draw_level_decisions": "per-draw simulation diagnostics without real participant identifiers",
            },
            "tracked_outputs": sorted(TRACKED_FILES),
        },
        "run_id": RUN_ID,
        "scope": "label_only_finite_sample_measurement_simulation",
        "simulation_contract": {
            "anchor_items": ANCHOR_ITEMS,
            "h0_false_localization_max": H0_FALSE_LOCALIZATION_MAX,
            "h1_target_both_flagged_min": H1_TARGET_BOTH_FLAGGED_MIN,
            "h1_target_top2_min": H1_TARGET_TOP2_MIN,
            "anchor_target_recovery_min": ANCHOR_TARGET_RECOVERY_MIN,
            "random_seed": seed,
            "simulations_per_world": simulations,
            "target_dif_items": TARGET_DIF_ITEMS,
            "theta_jitter_sd": THETA_JITTER_SD,
            "threshold_location_delta_tolerance": THRESHOLD_LOCATION_DELTA_TOL,
            "worlds": ["H0_scalar_invariant", "H1_C02_C06_threshold_DIF"],
        },
        "source_artifacts": {
            "mv10_threshold_dif_summary": rel(MV10_DIR / "threshold_dif_summary.csv"),
            "mv14_run_summary": rel(MV14_DIR / "run_summary.json"),
        },
        "status": "complete",
        "timing": {"runtime_seconds": float(time.perf_counter() - start)},
        "verdict": verdict,
        "outputs": {
            "anchor_recovery_rows": int(len(anchor_summary)),
            "draw_level_decision_rows_local_only": int(len(draws)),
            "effect_size_rows": int(len(offsets)),
            "item_flag_rows": int(len(item_summary)),
            "simulation_world_rows": int(len(world_summary)),
            "tracked_outputs": sorted(TRACKED_FILES),
        },
    }
    (out_dir / "run_summary.json").write_text(json.dumps(run_summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    write_report(out_dir, run_summary)
    hygiene = artifact_hygiene(out_dir)
    run_summary["artifact_hygiene_passed"] = bool(hygiene["artifact_hygiene_passed"])
    run_summary["timing"]["runtime_seconds"] = float(time.perf_counter() - start)
    (out_dir / "run_summary.json").write_text(json.dumps(run_summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    write_report(out_dir, run_summary)
    hygiene = artifact_hygiene(out_dir)
    (out_dir / "artifact_hygiene_audit.json").write_text(
        json.dumps(hygiene, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    if not hygiene["artifact_hygiene_passed"]:
        raise SystemExit("artifact hygiene violations found; see artifact_hygiene_audit.json")
    return run_summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest-dir", type=Path, default=DEFAULT_MANIFEST_DIR)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--simulations", type=int, default=DEFAULT_SIMULATIONS)
    parser.add_argument("--seed", type=int, default=RANDOM_SEED)
    args = parser.parse_args()

    run_summary = build_outputs(args.out_dir, args.manifest_dir, args.simulations, args.seed)
    print(
        "Wrote PHQ finite-sample simulation to "
        f"{rel(args.out_dir)} with status {run_summary['verdict']['pass_rule_status']}"
    )


if __name__ == "__main__":
    main()
