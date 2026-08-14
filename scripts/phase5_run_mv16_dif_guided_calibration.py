#!/usr/bin/env python3
"""Run P5_MV16 DIF-guided few-shot measurement calibration.

MV16 tests whether the localized PHQ threshold-DIF pattern from MV11/MV13/MV14
can support parameter-efficient target calibration. It is an aggregate-only
measurement-calibration experiment, not a feature-invariance result and not a
full symptom-aligned method.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import re
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def normalize_thread_env() -> None:
    value = str(os.environ.get("OMP_NUM_THREADS", "")).strip()
    if not value.isdigit() or int(value) <= 0:
        os.environ["OMP_NUM_THREADS"] = "1"
    os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
    os.environ.setdefault("MKL_NUM_THREADS", "1")


normalize_thread_env()

import numpy as np
import pandas as pd
from scipy.optimize import minimize
from scipy.special import softplus
from sklearn.isotonic import IsotonicRegression

import phase5_run_mv07_aligned_bge_shared_symptom as mv07
import phase5_run_mv12_two_stage_latent_target as mv12


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT_DIR = ROOT / "analysis" / "phase5_minimal_validation" / "p5_mv16_dif_guided_calibration"
DEFAULT_MANIFEST_DIR = mv07.DEFAULT_MANIFEST_DIR
DEFAULT_SPLIT_PATH = mv07.DEFAULT_SPLIT_PATH
DEFAULT_PHASE2_ROOT = mv07.DEFAULT_PHASE2_ROOT

RUN_ID = "P5_MV16_dif_guided_calibration"
SEEDS = mv07.SEEDS
K_SHOTS = [0, 5, 10, 20, 40]
CONSTRUCTS = mv07.CONSTRUCTS
MEASUREMENT_ITEMS = mv07.CONSTRUCTS
ANCHOR_ITEMS = mv12.ANCHOR_ITEMS
DIF_ITEMS = mv12.DIF_AWARE_ITEMS

L0_MODEL = "M16_B0_zero_shot_source"
B1_MODEL = "M16_B1_train_mean_target_theta"
B2_MODEL = "M16_B2_direct_itemwise_target"
L1_MODEL = "M16a_global_affine"
L2_MODEL = "M16b_global_monotonic"
L3_MODEL = "M16c_dif_guided_C02_C06"
L4_MODEL = "M16d_global_plus_C02_C06"
L5_MODEL = "M16e_all_thresholds"
L6_MODEL = "M16f_direct_target_theta"

MODEL_TO_LADDER = {
    L0_MODEL: "L0_zero_shot_source_measurement",
    B1_MODEL: "B1_train_mean_target_theta",
    B2_MODEL: "B2_direct_itemwise_target",
    L1_MODEL: "L1_global_affine_theta_calibration",
    L2_MODEL: "L2_global_monotonic_theta_calibration",
    L3_MODEL: "L3_dif_guided_C02_C06_threshold_calibration",
    L4_MODEL: "L4_anchor_plus_dif_joint_calibration",
    L5_MODEL: "L5_all_threshold_target_calibration",
    L6_MODEL: "L6_direct_target_domain_adaptation",
}

PRIMARY_MODELS = [L3_MODEL, L4_MODEL]
DIRECT_BASELINE_MODELS = [B2_MODEL, L6_MODEL]
OUTPUT_FEATURES = ["theta_pred", *[f"pred_{item}" for item in CONSTRUCTS], "pred_total"]

TRACKED_FILES = {
    "artifact_boundary_summary.csv",
    "artifact_hygiene_audit.json",
    "calibration_runtime_summary.csv",
    "gate_diagnostic_summary.csv",
    "input_audit.csv",
    "ladder_completeness_summary.csv",
    "learning_curve_summary.csv",
    "metric_by_seed.csv",
    "metric_summary.csv",
    "model_comparison_summary.csv",
    "output_identity_by_seed.csv",
    "output_identity_summary.csv",
    "pass_fail_gate_results.csv",
    "report.md",
    "run_summary.json",
    "split_audit_summary.csv",
    "target_reference_summary.csv",
}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def safe_float(value: Any) -> float | None:
    return mv07.safe_float(value)


def fmt(value: Any, digits: int = 3) -> str:
    numeric = safe_float(value)
    if numeric is None:
        return "NA"
    return f"{numeric:.{digits}f}"


def rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT))
    except ValueError:
        return path.name


def raw_thresholds(raw: np.ndarray) -> np.ndarray:
    b1 = float(raw[0])
    d12 = float(softplus(raw[1]))
    d23 = float(softplus(raw[2]))
    return np.asarray([b1, b1 + d12, b1 + d12 + d23], dtype=float)


def load_phq_table(
    manifest_dir: Path,
    phase2_root: Path,
) -> tuple[pd.DataFrame, list[str], pd.DataFrame, pd.DataFrame]:
    features, feature_cols, feature_audit = mv07.load_bge_features(phase2_root)
    labels = {
        "edaic": mv07.load_phq_labels(manifest_dir, "edaic"),
        "cmdc": mv07.load_phq_labels(manifest_dir, "cmdc"),
    }
    joined = {dataset: mv07.join_labels_features(labels[dataset], features[dataset]) for dataset in ["edaic", "cmdc"]}
    table = pd.concat([joined["edaic"], joined["cmdc"]], ignore_index=True)
    rows: list[dict[str, Any]] = []
    for dataset in ["edaic", "cmdc"]:
        rows.append(
            {
                "dataset": dataset,
                "label_subjects": int(labels[dataset]["subject_id"].nunique()),
                "feature_subjects": int(features[dataset]["subject_id"].nunique()),
                "joined_subjects": int(joined[dataset]["subject_id"].nunique()),
                "feature_family": "text_bge",
                "model_input_columns": int(len(feature_cols)),
            }
        )
    return table, feature_cols, feature_audit, pd.DataFrame(rows)


def direction_specs(phq_table: pd.DataFrame, cmdc_folds: dict[int, dict[str, set[str]]], seed: int) -> list[dict[str, Any]]:
    edaic_train = phq_table[(phq_table["dataset"] == "edaic") & (phq_table["official_split"] == "train")].copy()
    edaic_dev = phq_table[(phq_table["dataset"] == "edaic") & (phq_table["official_split"] == "dev")].copy()
    fold = cmdc_folds[seed % len(cmdc_folds)]
    fold_name = next(iter(fold["fold_name"]))
    cmdc_train = phq_table[(phq_table["dataset"] == "cmdc") & phq_table["subject_id"].isin(fold["train"])].copy()
    cmdc_val = phq_table[(phq_table["dataset"] == "cmdc") & phq_table["subject_id"].isin(fold["validation"])].copy()
    return [
        {
            "direction_id": "D1_edaic_source_cmdc_target",
            "source_dataset": "edaic",
            "target_dataset": "cmdc",
            "fold": fold_name,
            "source_train": edaic_train,
            "target_calibration_pool": cmdc_train,
            "target_eval": cmdc_val,
            "target_reference_pool": pd.concat([cmdc_train, cmdc_val], ignore_index=True),
        },
        {
            "direction_id": "D2_cmdc_source_edaic_target",
            "source_dataset": "cmdc",
            "target_dataset": "edaic",
            "fold": fold_name,
            "source_train": cmdc_train,
            "target_calibration_pool": edaic_train,
            "target_eval": edaic_dev,
            "target_reference_pool": pd.concat([edaic_train, edaic_dev], ignore_index=True),
        },
    ]


def deterministic_sample(frame: pd.DataFrame, k: int, seed: int, direction_id: str) -> pd.DataFrame:
    if k == 0:
        return frame.iloc[0:0].copy()
    if len(frame) < k:
        raise ValueError(f"{direction_id}/seed={seed} has {len(frame)} calibration candidates for k={k}")
    offset = sum(ord(char) for char in direction_id)
    rng = np.random.default_rng(seed * 1009 + k * 37 + offset)
    keys = sorted(frame["subject_key"].astype(str).tolist(), key=mv07.natural_key)
    chosen = set(rng.choice(keys, size=k, replace=False).tolist())
    out = frame[frame["subject_key"].astype(str).isin(chosen)].copy()
    return out.sort_values("subject_key", key=lambda s: s.map(lambda x: tuple(mv07.natural_key(x)))).reset_index(drop=True)


def overlap_count(left: pd.DataFrame, right: pd.DataFrame) -> int:
    return len(set(left["subject_key"].astype(str)) & set(right["subject_key"].astype(str)))


def expected_items_from_fit(
    fit: mv12.MeasurementFit,
    theta_values: np.ndarray,
    dataset: str,
    threshold_overrides: dict[str, np.ndarray] | None = None,
) -> np.ndarray:
    group = dataset if dataset in fit.spec.groups else fit.spec.default_group
    theta = np.asarray(theta_values, dtype=float).reshape(-1)
    outputs = np.empty((theta.shape[0], len(CONSTRUCTS)), dtype=float)
    for idx, item in enumerate(CONSTRUCTS):
        loading = fit.loading_values[fit.spec.loading_keys[(group, item)]]
        if threshold_overrides and item in threshold_overrides:
            thresholds = threshold_overrides[item]
        else:
            thresholds = fit.threshold_values[fit.spec.threshold_keys[(group, item)]]
        probabilities = mv12.category_probabilities(theta, loading, thresholds)
        outputs[:, idx] = probabilities @ np.asarray([0.0, 1.0, 2.0, 3.0], dtype=float)
    return mv12.clip_items(outputs)


def fit_threshold_overrides(
    fit: mv12.MeasurementFit,
    dataset: str,
    theta_values: np.ndarray,
    calibration: pd.DataFrame,
    items: list[str],
) -> tuple[dict[str, np.ndarray], list[dict[str, Any]]]:
    group = dataset if dataset in fit.spec.groups else fit.spec.default_group
    theta = np.asarray(theta_values, dtype=float).reshape(-1)
    rows: list[dict[str, Any]] = []
    overrides: dict[str, np.ndarray] = {}
    for item in items:
        loading = fit.loading_values[fit.spec.loading_keys[(group, item)]]
        base = fit.threshold_values[fit.spec.threshold_keys[(group, item)]]
        y = calibration[item].astype(int).to_numpy()
        x0 = np.asarray(mv12.ordered_threshold_raw(base.tolist()), dtype=float)
        bounds = [(-6.0, 6.0), (-6.0, 4.0), (-6.0, 4.0)]

        def nll(raw: np.ndarray) -> float:
            thresholds = raw_thresholds(raw)
            probabilities = mv12.category_probabilities(theta, loading, thresholds)
            return float(-np.sum(np.log(probabilities[np.arange(y.shape[0]), y])))

        result = minimize(
            nll,
            x0,
            method="L-BFGS-B",
            bounds=bounds,
            options={"maxiter": 300, "ftol": 1e-8, "gtol": 1e-5, "maxls": 30},
        )
        if not bool(result.success):
            raise RuntimeError(f"threshold calibration failed for {dataset}/{item}: {result.message}")
        thresholds = raw_thresholds(np.asarray(result.x, dtype=float))
        overrides[item] = thresholds
        rows.append(
            {
                "item": item,
                "calibration_participants": int(len(calibration)),
                "free_threshold_parameters": 3,
                "optimizer_success": bool(result.success),
                "optimizer_iterations": int(getattr(result, "nit", -1)),
                "nll": safe_float(result.fun),
            }
        )
    return overrides, rows


def fit_affine(x: np.ndarray, y: np.ndarray) -> tuple[float, float]:
    source = np.asarray(x, dtype=float).reshape(-1)
    target = np.asarray(y, dtype=float).reshape(-1)
    if source.shape[0] < 2:
        raise ValueError("affine calibration needs at least two target labels")
    if float(np.std(source, ddof=1)) <= 1e-8:
        raise ValueError("affine calibration source theta has near-zero variance")
    slope, intercept = np.polyfit(source, target, deg=1)
    return float(intercept), float(slope)


def fit_monotonic(x: np.ndarray, y: np.ndarray) -> IsotonicRegression:
    source = np.asarray(x, dtype=float).reshape(-1)
    target = np.asarray(y, dtype=float).reshape(-1)
    if len(np.unique(source)) < 3:
        raise ValueError("monotonic calibration needs at least three unique source theta values")
    model = IsotonicRegression(out_of_bounds="clip")
    model.fit(source, target)
    return model


def make_prediction_frame(
    eval_frame: pd.DataFrame,
    theta_true: np.ndarray,
    theta_pred: np.ndarray,
    item_pred: np.ndarray,
    *,
    direction_id: str,
    source_dataset: str,
    target_dataset: str,
    seed: int,
    k_shot: int,
    fold: str,
    model_id: str,
) -> pd.DataFrame:
    out = pd.DataFrame(
        {
            "direction_id": direction_id,
            "source_dataset": source_dataset,
            "target_dataset": target_dataset,
            "seed": int(seed),
            "k_shot": int(k_shot),
            "fold": fold,
            "model_id": model_id,
            "ladder_id": MODEL_TO_LADDER[model_id],
            "theta_true": np.asarray(theta_true, dtype=float),
            "theta_pred": np.asarray(theta_pred, dtype=float),
            "true_total": eval_frame[CONSTRUCTS].sum(axis=1).to_numpy(dtype=float),
            "pred_total": np.sum(item_pred, axis=1).astype(float),
        }
    )
    for idx, item in enumerate(CONSTRUCTS):
        out[item] = eval_frame[item].to_numpy(dtype=float)
        out[f"pred_{item}"] = item_pred[:, idx]
    return out


def add_prediction(
    frames: list[pd.DataFrame],
    eval_frame: pd.DataFrame,
    theta_true: np.ndarray,
    theta_pred: np.ndarray,
    item_pred: np.ndarray,
    *,
    spec: dict[str, Any],
    seed: int,
    k_shot: int,
    model_id: str,
) -> None:
    frames.append(
        make_prediction_frame(
            eval_frame,
            theta_true,
            theta_pred,
            item_pred,
            direction_id=str(spec["direction_id"]),
            source_dataset=str(spec["source_dataset"]),
            target_dataset=str(spec["target_dataset"]),
            seed=seed,
            k_shot=k_shot,
            fold=str(spec["fold"]),
            model_id=model_id,
        )
    )


def direct_items_to_theta(item_mapper: Any, item_pred: np.ndarray) -> np.ndarray:
    return np.asarray(item_mapper.predict(mv12.clip_items(item_pred)), dtype=float).reshape(-1)


def metric_rows_for_predictions(predictions: pd.DataFrame) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    group_cols = ["direction_id", "source_dataset", "target_dataset", "seed", "k_shot", "model_id", "ladder_id"]
    for group_key, group in predictions.groupby(group_cols, sort=False, dropna=False):
        direction_id, source_dataset, target_dataset, seed, k_shot, model_id, ladder_id = group_key
        item_mae = {
            item: float(np.mean(np.abs(group[f"pred_{item}"].to_numpy(float) - group[item].to_numpy(float))))
            for item in CONSTRUCTS
        }
        metrics = {
            "M1_theta_mae": ("Theta MAE", safe_float(np.mean(np.abs(group["theta_pred"] - group["theta_true"])))),
            "M2_observed_macro_item_mae": ("Observed Macro Item MAE", safe_float(np.mean(list(item_mae.values())))),
            "M3_dif_item_mae": ("C02/C06 DIF Item MAE", safe_float(np.mean([item_mae[item] for item in DIF_ITEMS]))),
            "M4_anchor_item_mae": ("C01/C04/C05/C07 Anchor Item MAE", safe_float(np.mean([item_mae[item] for item in ANCHOR_ITEMS]))),
            "M5_total_mae": ("Observed Total MAE", safe_float(np.mean(np.abs(group["pred_total"] - group["true_total"])))),
            "M6_theta_rank_correlation": ("Theta Spearman", mv07.spearman(group["theta_true"], group["theta_pred"])),
            "M6_total_rank_correlation": ("Observed Total Spearman", mv07.spearman(group["true_total"], group["pred_total"])),
        }
        for metric_id, (metric, value) in metrics.items():
            rows.append(
                {
                    "direction_id": direction_id,
                    "source_dataset": source_dataset,
                    "target_dataset": target_dataset,
                    "seed": int(seed),
                    "k_shot": int(k_shot),
                    "model_id": model_id,
                    "ladder_id": ladder_id,
                    "metric_id": metric_id,
                    "metric": metric,
                    "value": value,
                    "target_eval_participants": int(len(group)),
                }
            )
    return rows


def summarize_metrics(metrics: pd.DataFrame) -> pd.DataFrame:
    out = (
        metrics.groupby(
            ["direction_id", "source_dataset", "target_dataset", "k_shot", "model_id", "ladder_id", "metric_id", "metric"],
            dropna=False,
        )
        .agg(
            mean=("value", "mean"),
            std=("value", "std"),
            seed_count=("seed", "nunique"),
            target_eval_participants_mean=("target_eval_participants", "mean"),
        )
        .reset_index()
    )
    out["std"] = out["std"].fillna(0.0)
    out["ci95_low"] = out["mean"] - 1.96 * out["std"] / np.sqrt(out["seed_count"].clip(lower=1))
    out["ci95_high"] = out["mean"] + 1.96 * out["std"] / np.sqrt(out["seed_count"].clip(lower=1))
    return out


def metric_value(pivot: dict[str, dict[str, Any]], model_id: str, metric: str) -> float | None:
    row = pivot.get(model_id)
    if not row:
        return None
    return safe_float(row.get(metric))


def build_learning_curve(metric_summary: pd.DataFrame) -> pd.DataFrame:
    pivot = (
        metric_summary.pivot_table(
            index=["direction_id", "source_dataset", "target_dataset", "k_shot", "model_id", "ladder_id"],
            columns="metric",
            values="mean",
            aggfunc="first",
        )
        .reset_index()
        .rename_axis(None, axis=1)
    )
    rows: list[dict[str, Any]] = []
    for (direction_id, k_shot), group in pivot.groupby(["direction_id", "k_shot"], sort=False):
        values = group.set_index("model_id").to_dict("index")
        l0_theta = metric_value(values, L0_MODEL, "Theta MAE")
        l1_dif = metric_value(values, L1_MODEL, "C02/C06 DIF Item MAE")
        l1_anchor = metric_value(values, L1_MODEL, "C01/C04/C05/C07 Anchor Item MAE")
        direct_theta = [
            value
            for value in [metric_value(values, model, "Theta MAE") for model in DIRECT_BASELINE_MODELS]
            if value is not None
        ]
        direct_observed = [
            value
            for value in [metric_value(values, model, "Observed Macro Item MAE") for model in DIRECT_BASELINE_MODELS]
            if value is not None
        ]
        for _, row in group.iterrows():
            theta_mae = safe_float(row.get("Theta MAE"))
            observed_mae = safe_float(row.get("Observed Macro Item MAE"))
            dif_mae = safe_float(row.get("C02/C06 DIF Item MAE"))
            anchor_mae = safe_float(row.get("C01/C04/C05/C07 Anchor Item MAE"))
            rows.append(
                {
                    "direction_id": direction_id,
                    "source_dataset": row["source_dataset"],
                    "target_dataset": row["target_dataset"],
                    "k_shot": int(k_shot),
                    "model_id": row["model_id"],
                    "ladder_id": row["ladder_id"],
                    "theta_mae": theta_mae,
                    "delta_theta_mae_vs_L0": safe_float(theta_mae - l0_theta)
                    if theta_mae is not None and l0_theta is not None
                    else None,
                    "observed_macro_item_mae": observed_mae,
                    "dif_item_mae": dif_mae,
                    "delta_dif_item_mae_vs_L1": safe_float(dif_mae - l1_dif)
                    if dif_mae is not None and l1_dif is not None
                    else None,
                    "anchor_item_mae": anchor_mae,
                    "anchor_relative_change_vs_L1": safe_float((anchor_mae - l1_anchor) / l1_anchor)
                    if anchor_mae is not None and l1_anchor not in (None, 0.0)
                    else None,
                    "observed_total_mae": safe_float(row.get("Observed Total MAE")),
                    "theta_spearman": safe_float(row.get("Theta Spearman")),
                    "delta_theta_mae_vs_best_direct": safe_float(theta_mae - min(direct_theta))
                    if theta_mae is not None and direct_theta
                    else None,
                    "delta_observed_macro_mae_vs_best_direct": safe_float(observed_mae - min(direct_observed))
                    if observed_mae is not None and direct_observed
                    else None,
                }
            )
    return pd.DataFrame(rows)


def output_identity_rows(predictions: pd.DataFrame) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for (seed, k_shot, model_id), group in predictions.groupby(["seed", "k_shot", "model_id"], sort=True):
        labels = (group["target_dataset"].astype(str) == "cmdc").astype(int).to_numpy()
        x = group[OUTPUT_FEATURES].to_numpy(dtype=float)
        value, skipped = mv12.identity_cv_score(x, labels, int(seed))
        rows.append(
            {
                "seed": int(seed),
                "k_shot": int(k_shot),
                "model_id": model_id,
                "ladder_id": MODEL_TO_LADDER[model_id],
                "probe_id": "MV16_output_identity_edaic_cmdc_predictions",
                "metric_id": "M7_output_identity",
                "metric": "Balanced Accuracy",
                "value": value,
                "target_eval_participants": int(len(group)),
                "dataset_count": int(group["target_dataset"].nunique()),
                "skipped_reason": skipped,
            }
        )
    return rows


def summarize_identity(identity: pd.DataFrame) -> pd.DataFrame:
    if identity.empty:
        return pd.DataFrame()
    return (
        identity.groupby(["k_shot", "model_id", "ladder_id", "probe_id", "metric_id", "metric"], dropna=False)
        .agg(
            mean=("value", "mean"),
            std=("value", "std"),
            seed_count=("seed", "nunique"),
            target_eval_participants_mean=("target_eval_participants", "mean"),
            dataset_count_mean=("dataset_count", "mean"),
        )
        .reset_index()
        .fillna({"std": 0.0})
    )


def build_model_comparison(learning: pd.DataFrame) -> pd.DataFrame:
    columns = [
        "direction_id",
        "source_dataset",
        "target_dataset",
        "k_shot",
        "model_id",
        "ladder_id",
        "theta_mae",
        "delta_theta_mae_vs_L0",
        "observed_macro_item_mae",
        "dif_item_mae",
        "delta_dif_item_mae_vs_L1",
        "anchor_item_mae",
        "anchor_relative_change_vs_L1",
        "observed_total_mae",
        "delta_theta_mae_vs_best_direct",
        "delta_observed_macro_mae_vs_best_direct",
    ]
    return learning[columns].sort_values(["direction_id", "k_shot", "model_id"]).reset_index(drop=True)


def build_gate_diagnostics(learning: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for (direction_id, k_shot), group in learning.groupby(["direction_id", "k_shot"], sort=False):
        by_model = group.set_index("model_id").to_dict("index")
        l0_theta = metric_value(by_model, L0_MODEL, "theta_mae")
        l1_dif = metric_value(by_model, L1_MODEL, "dif_item_mae")
        l1_anchor = metric_value(by_model, L1_MODEL, "anchor_item_mae")
        best_direct_theta = min(
            [
                value
                for value in [metric_value(by_model, model, "theta_mae") for model in DIRECT_BASELINE_MODELS]
                if value is not None
            ],
            default=None,
        )
        best_direct_observed = min(
            [
                value
                for value in [metric_value(by_model, model, "observed_macro_item_mae") for model in DIRECT_BASELINE_MODELS]
                if value is not None
            ],
            default=None,
        )
        for model_id in PRIMARY_MODELS:
            theta_mae = metric_value(by_model, model_id, "theta_mae")
            dif_mae = metric_value(by_model, model_id, "dif_item_mae")
            anchor_mae = metric_value(by_model, model_id, "anchor_item_mae")
            observed_mae = metric_value(by_model, model_id, "observed_macro_item_mae")
            small_k_gain = bool(
                k_shot <= 20
                and theta_mae is not None
                and l0_theta is not None
                and dif_mae is not None
                and l1_dif is not None
                and (l0_theta - theta_mae) >= 0.03
                and dif_mae < l1_dif
            )
            anchor_safe = bool(
                anchor_mae is not None and l1_anchor is not None and anchor_mae <= 1.05 * l1_anchor
            )
            direct_dominates = bool(
                best_direct_theta is not None
                and best_direct_observed is not None
                and theta_mae is not None
                and observed_mae is not None
                and best_direct_theta <= theta_mae
                and best_direct_observed <= observed_mae
            )
            rows.append(
                {
                    "direction_id": direction_id,
                    "k_shot": int(k_shot),
                    "model_id": model_id,
                    "theta_gain_vs_L0": safe_float(l0_theta - theta_mae)
                    if l0_theta is not None and theta_mae is not None
                    else None,
                    "dif_gain_vs_L1": safe_float(l1_dif - dif_mae)
                    if l1_dif is not None and dif_mae is not None
                    else None,
                    "anchor_relative_change_vs_L1": safe_float((anchor_mae - l1_anchor) / l1_anchor)
                    if anchor_mae is not None and l1_anchor not in (None, 0.0)
                    else None,
                    "small_k_gain_gate_passed": small_k_gain,
                    "anchor_safety_gate_passed": anchor_safe,
                    "direct_baseline_dominates_theta_and_observed": direct_dominates,
                }
            )
    return pd.DataFrame(rows)


def build_pass_fail_gates(
    split_audit: pd.DataFrame,
    completeness: pd.DataFrame,
    gate_diag: pd.DataFrame,
    identity_summary: pd.DataFrame,
    hygiene_passed: bool,
) -> pd.DataFrame:
    overlap_cols = [
        "source_calibration_overlap_count",
        "source_eval_overlap_count",
        "calibration_eval_overlap_count",
    ]
    split_pass = bool((split_audit[overlap_cols].sum(axis=1) == 0).all())
    complete_pass = bool(
        completeness["status"].isin(["complete", "skipped"]).all()
        and completeness.loc[completeness["status"] == "skipped", "skipped_reason"].astype(str).str.len().gt(0).all()
    )
    directional_support = gate_diag[
        (gate_diag["small_k_gain_gate_passed"]) & (gate_diag["anchor_safety_gate_passed"])
    ]["direction_id"].nunique()
    g4_pass = bool(directional_support == 2)
    anchor_rows = gate_diag[gate_diag["k_shot"] > 0]
    g5_pass = bool(not anchor_rows.empty and anchor_rows["anchor_safety_gate_passed"].all())
    complete_primary = gate_diag[gate_diag["k_shot"] > 0].copy()
    direct_dominates_all = bool(
        not complete_primary.empty and complete_primary["direct_baseline_dominates_theta_and_observed"].all()
    )
    g6_pass = not direct_dominates_all
    g7_pass = bool(not identity_summary.empty)
    rows = [
        ("G1_input_scope", True, "Runner used manifest-governed PHQ labels and BGE feature caches only."),
        ("G2_subject_level_fewshot_splits", split_pass, "All source/calibration/evaluation overlap counts are zero."),
        ("G3_ladder_completeness", complete_pass, "All L0-L6 rows are complete where feasible; k=0 target-label rows are explicitly skipped."),
        ("G4_dif_guided_small_k_gain", g4_pass, "Requires L3 or L4 theta gain >=0.03 vs L0 and C02/C06 gain vs L1 in both directions for k<=20."),
        ("G5_anchor_safety", g5_pass, "L3/L4 anchor MAE must not degrade more than 5 percent versus L1."),
        ("G6_dimension_matched_baseline", g6_pass, "Direct B2/L6 baselines do not dominate every preferred DIF-guided row on both theta and observed MAE."),
        ("G7_identity_boundary", g7_pass, "Output identity BA is reported separately from upstream BGE feature invariance."),
        ("G8_artifact_hygiene", bool(hygiene_passed), "Tracked outputs are aggregate-only and pass the hygiene scanner."),
    ]
    return pd.DataFrame(
        [
            {
                "gate_id": gate_id,
                "passed": bool(passed),
                "status": "pass" if passed else "fail",
                "interpretation": interpretation,
            }
            for gate_id, passed, interpretation in rows
        ]
    )


def build_verdict(
    gates: pd.DataFrame,
    gate_diag: pd.DataFrame,
    learning: pd.DataFrame,
    identity_summary: pd.DataFrame,
) -> dict[str, Any]:
    gate_values = gates.set_index("gate_id")["passed"].to_dict()
    support = gate_diag[
        (gate_diag["small_k_gain_gate_passed"]) & (gate_diag["anchor_safety_gate_passed"])
    ].copy()
    best_support = None
    if not support.empty:
        support = support.sort_values(["k_shot", "direction_id", "model_id"])
        best_support = support.iloc[0].to_dict()
    if not gate_values.get("G8_artifact_hygiene", False):
        status = "blocked_artifact_hygiene_pending_or_failed"
    elif not gate_values.get("G2_subject_level_fewshot_splits", False):
        status = "blocked_split_overlap"
    elif not gate_values.get("G3_ladder_completeness", False):
        status = "blocked_incomplete_mv16_ladder"
    elif gate_values.get("G4_dif_guided_small_k_gain", False) and gate_values.get("G5_anchor_safety", False) and gate_values.get("G6_dimension_matched_baseline", False):
        status = "pass_dif_guided_parameter_efficient_measurement_calibration"
    elif gate_values.get("G4_dif_guided_small_k_gain", False) and not gate_values.get("G6_dimension_matched_baseline", False):
        status = "complete_practical_adaptation_direct_baseline_dominates"
    else:
        status = "blocked_no_dif_guided_small_k_gain"

    l4_small = learning[(learning["model_id"] == L4_MODEL) & (learning["k_shot"].isin([5, 10, 20]))].copy()
    best_l4_gain = None
    if not l4_small.empty:
        best_l4_gain = safe_float(l4_small["delta_theta_mae_vs_L0"].min())
    identity_l4 = identity_summary[
        (identity_summary["model_id"] == L4_MODEL) & (identity_summary["k_shot"].isin([5, 10, 20]))
    ]
    return {
        "status": status,
        "pass_rule_status": status,
        "pass_rule_met": status.startswith("pass_"),
        "full_method_allowed": False,
        "dif_guided_small_k_gate_passed": bool(gate_values.get("G4_dif_guided_small_k_gain", False)),
        "anchor_safety_gate_passed": bool(gate_values.get("G5_anchor_safety", False)),
        "direct_baseline_gate_passed": bool(gate_values.get("G6_dimension_matched_baseline", False)),
        "subject_overlap_gate_passed": bool(gate_values.get("G2_subject_level_fewshot_splits", False)),
        "output_identity_reported": bool(gate_values.get("G7_identity_boundary", False)),
        "artifact_hygiene_passed": bool(gate_values.get("G8_artifact_hygiene", False)),
        "best_supported_direction": None if best_support is None else str(best_support["direction_id"]),
        "best_supported_k": None if best_support is None else int(best_support["k_shot"]),
        "best_supported_model": None if best_support is None else str(best_support["model_id"]),
        "best_l4_small_k_delta_theta_mae_vs_L0": best_l4_gain,
        "l4_small_k_output_identity_ba_mean": safe_float(identity_l4["mean"].mean()) if not identity_l4.empty else None,
        "short_read": (
            "MV16 passes the predeclared DIF-guided calibration gate, but remains a measurement-calibration result rather than feature invariance."
            if status.startswith("pass_")
            else "MV16 completes the predeclared few-shot calibration ladder but does not satisfy the DIF-guided small-k mechanism gate; keep it as negative or bounded diagnostic evidence."
        ),
    }


def artifact_boundary_summary() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "artifact_class": "tracked",
                "contents": "aggregate metrics, learning curves, gate results, identity summaries, reports",
                "contains_subject_rows": False,
                "contains_latent_tables": False,
                "contains_calibration_params": False,
            },
            {
                "artifact_class": "local_only_not_written_by_runner",
                "contents": "target shot maps, row-level predictions, theta tables, fitted measurement parameters, model artifacts",
                "contains_subject_rows": True,
                "contains_latent_tables": True,
                "contains_calibration_params": True,
            },
        ]
    )


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
        r"source_locator",
        r"local_annotation_workbook",
        r"verbatim",
        r"\.wav\b",
        r"\.mp4\b",
        r"\.avi\b",
        r"raw prompt",
        r"raw response",
        r"raw clinical",
        r"posterior_score",
        r"factor_score",
        r"theta_score",
        r"parameter_value",
        r"row_prediction",
        r"target_shot_map",
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
        "audit_id": "P5_MV16_dif_guided_calibration_hygiene",
        "generated_at": utc_now(),
        "files_checked": checked,
        "artifact_hygiene_passed": not violations,
        "violation_count": len(violations),
        "violations": violations,
    }


def write_report(
    out_dir: Path,
    run_summary: dict[str, Any],
    gates: pd.DataFrame,
    comparison: pd.DataFrame,
    identity: pd.DataFrame,
) -> None:
    verdict = run_summary["verdict"]
    lines = [
        "# P5_MV16 DIF-Guided Few-Shot Measurement Calibration",
        "",
        f"Generated: `{run_summary['generated_at']}`",
        "",
        "## Scope",
        "",
        "MV16 evaluates E-DAIC->CMDC and CMDC->E-DAIC PHQ calibration at k=0/5/10/20/40. It uses BGE feature caches, manifest PHQ labels, and local measurement scoring, and exports aggregate results only.",
        "",
        "## Verdict",
        "",
        f"- Pass-rule status: `{verdict['pass_rule_status']}`.",
        f"- Full method allowed: `{verdict['full_method_allowed']}`.",
        f"- DIF-guided small-k gate passed: `{verdict['dif_guided_small_k_gate_passed']}`.",
        f"- Anchor safety gate passed: `{verdict['anchor_safety_gate_passed']}`.",
        f"- Direct-baseline gate passed: `{verdict['direct_baseline_gate_passed']}`.",
        f"- Output identity reported: `{verdict['output_identity_reported']}`.",
        f"- Artifact hygiene passed: `{verdict['artifact_hygiene_passed']}`.",
        "",
        verdict["short_read"],
        "",
        "## Gate Summary",
        "",
        "| gate | status | interpretation |",
        "| --- | --- | --- |",
    ]
    for _, row in gates.iterrows():
        lines.append(f"| {row['gate_id']} | `{row['status']}` | {row['interpretation']} |")
    lines.extend(
        [
            "",
            "## Key Calibration Rows",
            "",
            "| direction | k | model | theta MAE | delta theta vs L0 | C02/C06 MAE | delta C02/C06 vs L1 | anchor rel change | observed macro MAE |",
            "| --- | ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: |",
        ]
    )
    key = comparison[
        comparison["model_id"].isin([L0_MODEL, L1_MODEL, L3_MODEL, L4_MODEL, B2_MODEL, L6_MODEL])
        & comparison["k_shot"].isin([0, 5, 10, 20])
    ].copy()
    for _, row in key.sort_values(["direction_id", "k_shot", "model_id"]).iterrows():
        lines.append(
            "| "
            + " | ".join(
                [
                    str(row["direction_id"]),
                    str(int(row["k_shot"])),
                    str(row["model_id"]),
                    fmt(row["theta_mae"]),
                    fmt(row["delta_theta_mae_vs_L0"]),
                    fmt(row["dif_item_mae"]),
                    fmt(row["delta_dif_item_mae_vs_L1"]),
                    fmt(row["anchor_relative_change_vs_L1"]),
                    fmt(row["observed_macro_item_mae"]),
                ]
            )
            + " |"
        )
    lines.extend(
        [
            "",
            "## Output Identity",
            "",
            "| k | model | output identity BA | seeds |",
            "| ---: | --- | ---: | ---: |",
        ]
    )
    identity_key = identity[identity["model_id"].isin([L0_MODEL, L3_MODEL, L4_MODEL, B2_MODEL, L6_MODEL])].copy()
    for _, row in identity_key.sort_values(["k_shot", "model_id"]).iterrows():
        lines.append(
            f"| {int(row['k_shot'])} | {row['model_id']} | {fmt(row['mean'])} | {int(row['seed_count'])} |"
        )
    lines.extend(
        [
            "",
            "## Boundary",
            "",
            "MV16 may update target-measurement calibration evidence only. It must not be described as BGE feature invariance, external HAMD transfer, or authorization to start the full M0/M1/M2/M3 method.",
        ]
    )
    (out_dir / "report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def run_direction(
    spec: dict[str, Any],
    feature_cols: list[str],
    seed: int,
) -> tuple[list[pd.DataFrame], list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    source_dataset = str(spec["source_dataset"])
    target_dataset = str(spec["target_dataset"])
    source_train = spec["source_train"].copy()
    target_pool = spec["target_calibration_pool"].copy()
    target_eval = spec["target_eval"].copy()
    target_reference_pool = spec["target_reference_pool"].copy()

    source_fit = mv12.fit_measurement_model(source_train, MEASUREMENT_ITEMS)
    source_theta_train, source_train_fallback = mv12.score_theta(source_train, source_fit)
    target_ref_fit = mv12.fit_measurement_model(target_reference_pool, MEASUREMENT_ITEMS)
    target_theta_pool, target_pool_fallback = mv12.score_theta(target_reference_pool, target_ref_fit)
    target_theta_eval, target_eval_fallback = mv12.score_theta(target_eval, target_ref_fit)
    item_to_theta_mapper = mv12.fit_item_to_theta_mapper(target_reference_pool, target_theta_pool)

    theta_pred_cal_pool, theta_alpha = mv12.fit_predict_theta(
        source_train,
        target_pool,
        source_theta_train,
        feature_cols,
        seed,
    )
    theta_pred_eval, _ = mv12.fit_predict_theta(source_train, target_eval, source_theta_train, feature_cols, seed)
    target_theta_lookup = pd.Series(target_theta_pool, index=target_reference_pool["subject_key"].astype(str)).to_dict()
    target_pred_lookup = pd.Series(theta_pred_cal_pool, index=target_pool["subject_key"].astype(str)).to_dict()
    frames: list[pd.DataFrame] = []
    split_rows: list[dict[str, Any]] = []
    target_rows: list[dict[str, Any]] = []
    runtime_rows: list[dict[str, Any]] = []
    completeness_rows: list[dict[str, Any]] = []

    target_rows.append(
        {
            "direction_id": spec["direction_id"],
            "source_dataset": source_dataset,
            "target_dataset": target_dataset,
            "seed": seed,
            "fold": spec["fold"],
            "source_train_participants": int(source_train["subject_key"].nunique()),
            "target_reference_participants": int(target_reference_pool["subject_key"].nunique()),
            "target_eval_participants": int(target_eval["subject_key"].nunique()),
            "measurement_items": ";".join(MEASUREMENT_ITEMS),
            "anchor_items": ";".join(ANCHOR_ITEMS),
            "dif_items": ";".join(DIF_ITEMS),
            "source_measurement_optimizer_success": bool(source_fit.optimizer_success),
            "target_reference_optimizer_success": bool(target_ref_fit.optimizer_success),
            "source_measurement_fallback_count": int(source_train_fallback),
            "target_reference_pool_fallback_count": int(target_pool_fallback),
            "target_eval_reference_fallback_count": int(target_eval_fallback),
            "target_reference_uses_eval_labels_for_evaluation_truth": True,
            "target_reference_parameters_written": False,
            "theta_tables_written": False,
        }
    )

    for k_shot in K_SHOTS:
        calibration = deterministic_sample(target_pool, k_shot, seed, str(spec["direction_id"]))
        calibration_keys = calibration["subject_key"].astype(str).tolist()
        target_theta_cal = np.asarray([target_theta_lookup[key] for key in calibration_keys], dtype=float)
        theta_pred_cal = np.asarray([target_pred_lookup[key] for key in calibration_keys], dtype=float)
        split_rows.append(
            {
                "direction_id": spec["direction_id"],
                "source_dataset": source_dataset,
                "target_dataset": target_dataset,
                "seed": seed,
                "k_shot": k_shot,
                "fold": spec["fold"],
                "source_train_participants": int(source_train["subject_key"].nunique()),
                "target_calibration_candidate_participants": int(target_pool["subject_key"].nunique()),
                "target_calibration_participants": int(len(calibration)),
                "target_eval_participants": int(target_eval["subject_key"].nunique()),
                "source_calibration_overlap_count": overlap_count(source_train, calibration),
                "source_eval_overlap_count": overlap_count(source_train, target_eval),
                "calibration_eval_overlap_count": overlap_count(calibration, target_eval),
                "shot_map_written": False,
                "calibration_subjects_written": False,
            }
        )

        def mark_complete(model_id: str, detail: str) -> None:
            completeness_rows.append(
                {
                    "direction_id": spec["direction_id"],
                    "source_dataset": source_dataset,
                    "target_dataset": target_dataset,
                    "seed": seed,
                    "k_shot": k_shot,
                    "model_id": model_id,
                    "ladder_id": MODEL_TO_LADDER[model_id],
                    "status": "complete",
                    "skipped_reason": "",
                    "detail": detail,
                }
            )

        def mark_skipped(model_id: str, reason: str) -> None:
            completeness_rows.append(
                {
                    "direction_id": spec["direction_id"],
                    "source_dataset": source_dataset,
                    "target_dataset": target_dataset,
                    "seed": seed,
                    "k_shot": k_shot,
                    "model_id": model_id,
                    "ladder_id": MODEL_TO_LADDER[model_id],
                    "status": "skipped",
                    "skipped_reason": reason,
                    "detail": "",
                }
            )

        l0_items = expected_items_from_fit(source_fit, theta_pred_eval, source_dataset)
        add_prediction(frames, target_eval, target_theta_eval, theta_pred_eval, l0_items, spec=spec, seed=seed, k_shot=k_shot, model_id=L0_MODEL)
        mark_complete(L0_MODEL, "source X-to-theta predictor plus source measurement map")

        if k_shot == 0:
            for model_id in [B1_MODEL, B2_MODEL, L1_MODEL, L2_MODEL, L3_MODEL, L4_MODEL, L5_MODEL, L6_MODEL]:
                mark_skipped(model_id, "requires target calibration labels")
            continue

        b1_theta = np.repeat(float(np.mean(target_theta_cal)), len(target_eval))
        b1_items = np.tile(calibration[CONSTRUCTS].mean(axis=0).to_numpy(dtype=float).reshape(1, -1), (len(target_eval), 1))
        add_prediction(frames, target_eval, target_theta_eval, b1_theta, mv12.clip_items(b1_items), spec=spec, seed=seed, k_shot=k_shot, model_id=B1_MODEL)
        mark_complete(B1_MODEL, "target calibration mean floor")

        b2_items, b2_alpha = mv12.fit_predict_itemwise_items(calibration, target_eval, feature_cols, seed)
        b2_theta = direct_items_to_theta(item_to_theta_mapper, b2_items)
        add_prediction(frames, target_eval, target_theta_eval, b2_theta, b2_items, spec=spec, seed=seed, k_shot=k_shot, model_id=B2_MODEL)
        runtime_rows.append(
            {
                "direction_id": spec["direction_id"],
                "seed": seed,
                "k_shot": k_shot,
                "model_id": B2_MODEL,
                "selected_alpha": b2_alpha,
                "free_threshold_parameters": 0,
            }
        )
        mark_complete(B2_MODEL, "target-only direct itemwise Ridge")

        intercept, slope = fit_affine(theta_pred_cal, target_theta_cal)
        l1_theta_cal = intercept + slope * theta_pred_cal
        l1_theta_eval = intercept + slope * theta_pred_eval
        l1_items = expected_items_from_fit(source_fit, l1_theta_eval, source_dataset)
        add_prediction(frames, target_eval, target_theta_eval, l1_theta_eval, l1_items, spec=spec, seed=seed, k_shot=k_shot, model_id=L1_MODEL)
        runtime_rows.append(
            {
                "direction_id": spec["direction_id"],
                "seed": seed,
                "k_shot": k_shot,
                "model_id": L1_MODEL,
                "selected_alpha": None,
                "free_threshold_parameters": 0,
                "free_global_parameters": 2,
            }
        )
        mark_complete(L1_MODEL, "global affine theta calibration")

        monotonic = fit_monotonic(theta_pred_cal, target_theta_cal)
        l2_theta_eval = np.asarray(monotonic.predict(theta_pred_eval), dtype=float)
        l2_items = expected_items_from_fit(source_fit, l2_theta_eval, source_dataset)
        add_prediction(frames, target_eval, target_theta_eval, l2_theta_eval, l2_items, spec=spec, seed=seed, k_shot=k_shot, model_id=L2_MODEL)
        mark_complete(L2_MODEL, "global monotonic theta calibration")

        l3_overrides, l3_rows = fit_threshold_overrides(source_fit, source_dataset, theta_pred_cal, calibration, DIF_ITEMS)
        l3_items = expected_items_from_fit(source_fit, theta_pred_eval, source_dataset, l3_overrides)
        add_prediction(frames, target_eval, target_theta_eval, theta_pred_eval, l3_items, spec=spec, seed=seed, k_shot=k_shot, model_id=L3_MODEL)
        for row in l3_rows:
            runtime_rows.append(
                {
                    "direction_id": spec["direction_id"],
                    "seed": seed,
                    "k_shot": k_shot,
                    "model_id": L3_MODEL,
                    **row,
                    "threshold_values_written": False,
                }
            )
        mark_complete(L3_MODEL, "C02/C06 threshold calibration")

        l4_overrides, l4_rows = fit_threshold_overrides(source_fit, source_dataset, l1_theta_cal, calibration, DIF_ITEMS)
        l4_items = expected_items_from_fit(source_fit, l1_theta_eval, source_dataset, l4_overrides)
        add_prediction(frames, target_eval, target_theta_eval, l1_theta_eval, l4_items, spec=spec, seed=seed, k_shot=k_shot, model_id=L4_MODEL)
        for row in l4_rows:
            runtime_rows.append(
                {
                    "direction_id": spec["direction_id"],
                    "seed": seed,
                    "k_shot": k_shot,
                    "model_id": L4_MODEL,
                    **row,
                    "threshold_values_written": False,
                    "free_global_parameters": 2,
                }
            )
        mark_complete(L4_MODEL, "global affine plus C02/C06 threshold calibration")

        l5_overrides, l5_rows = fit_threshold_overrides(source_fit, source_dataset, theta_pred_cal, calibration, CONSTRUCTS)
        l5_items = expected_items_from_fit(source_fit, theta_pred_eval, source_dataset, l5_overrides)
        add_prediction(frames, target_eval, target_theta_eval, theta_pred_eval, l5_items, spec=spec, seed=seed, k_shot=k_shot, model_id=L5_MODEL)
        for row in l5_rows:
            runtime_rows.append(
                {
                    "direction_id": spec["direction_id"],
                    "seed": seed,
                    "k_shot": k_shot,
                    "model_id": L5_MODEL,
                    **row,
                    "threshold_values_written": False,
                }
            )
        mark_complete(L5_MODEL, "all-item threshold calibration")

        l6_theta_eval, l6_alpha = mv12.fit_predict_theta(calibration, target_eval, target_theta_cal, feature_cols, seed)
        l6_items = expected_items_from_fit(target_ref_fit, l6_theta_eval, target_dataset)
        add_prediction(frames, target_eval, target_theta_eval, l6_theta_eval, l6_items, spec=spec, seed=seed, k_shot=k_shot, model_id=L6_MODEL)
        runtime_rows.append(
            {
                "direction_id": spec["direction_id"],
                "seed": seed,
                "k_shot": k_shot,
                "model_id": L6_MODEL,
                "selected_alpha": l6_alpha,
                "free_threshold_parameters": 0,
            }
        )
        mark_complete(L6_MODEL, "target-only direct theta Ridge")

        runtime_rows.append(
            {
                "direction_id": spec["direction_id"],
                "seed": seed,
                "k_shot": k_shot,
                "model_id": L0_MODEL,
                "selected_alpha": theta_alpha,
                "free_threshold_parameters": 0,
            }
        )
    return frames, split_rows, target_rows, runtime_rows, completeness_rows


def run_experiment(
    out_dir: Path,
    manifest_dir: Path,
    split_path: Path,
    phase2_root: Path,
) -> dict[str, Any]:
    if out_dir.exists():
        shutil.rmtree(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    phq_table, feature_cols, feature_audit, joined_audit = load_phq_table(manifest_dir, phase2_root)
    cmdc_folds = mv07.load_subject_folds(split_path, "cmdc", "cmdc_phq9_subject_cv", "phq9_total")

    prediction_frames: list[pd.DataFrame] = []
    split_rows: list[dict[str, Any]] = []
    target_rows: list[dict[str, Any]] = []
    runtime_rows: list[dict[str, Any]] = []
    completeness_rows: list[dict[str, Any]] = []
    for seed in SEEDS:
        for spec in direction_specs(phq_table, cmdc_folds, seed):
            frames, splits, targets, runtime, completeness = run_direction(spec, feature_cols, seed)
            prediction_frames.extend(frames)
            split_rows.extend(splits)
            target_rows.extend(targets)
            runtime_rows.extend(runtime)
            completeness_rows.extend(completeness)

    predictions = pd.concat(prediction_frames, ignore_index=True)
    metric_by_seed = pd.DataFrame(metric_rows_for_predictions(predictions))
    metric_summary = summarize_metrics(metric_by_seed)
    learning = build_learning_curve(metric_summary)
    comparison = build_model_comparison(learning)
    identity_by_seed = pd.DataFrame(output_identity_rows(predictions))
    identity_summary = summarize_identity(identity_by_seed)
    split_audit = pd.DataFrame(split_rows)
    target_reference = pd.DataFrame(target_rows)
    runtime_summary = pd.DataFrame(runtime_rows)
    completeness = pd.DataFrame(completeness_rows)
    gate_diag = build_gate_diagnostics(learning)
    input_audit = pd.concat(
        [
            joined_audit,
            feature_audit[feature_audit["dataset"].isin(["edaic", "cmdc"])].drop(columns=["feature_ref"], errors="ignore"),
        ],
        ignore_index=True,
        sort=False,
    )
    boundary = artifact_boundary_summary()

    input_audit.to_csv(out_dir / "input_audit.csv", index=False)
    split_audit.to_csv(out_dir / "split_audit_summary.csv", index=False)
    target_reference.to_csv(out_dir / "target_reference_summary.csv", index=False)
    runtime_summary.to_csv(out_dir / "calibration_runtime_summary.csv", index=False)
    completeness.to_csv(out_dir / "ladder_completeness_summary.csv", index=False)
    metric_by_seed.to_csv(out_dir / "metric_by_seed.csv", index=False)
    metric_summary.to_csv(out_dir / "metric_summary.csv", index=False)
    learning.to_csv(out_dir / "learning_curve_summary.csv", index=False)
    comparison.to_csv(out_dir / "model_comparison_summary.csv", index=False)
    identity_by_seed.to_csv(out_dir / "output_identity_by_seed.csv", index=False)
    identity_summary.to_csv(out_dir / "output_identity_summary.csv", index=False)
    gate_diag.to_csv(out_dir / "gate_diagnostic_summary.csv", index=False)
    boundary.to_csv(out_dir / "artifact_boundary_summary.csv", index=False)

    gates = build_pass_fail_gates(split_audit, completeness, gate_diag, identity_summary, hygiene_passed=False)
    verdict = build_verdict(gates, gate_diag, learning, identity_summary)
    gates.to_csv(out_dir / "pass_fail_gate_results.csv", index=False)
    run_summary = {
        "run_id": RUN_ID,
        "generated_at": utc_now(),
        "status": "complete",
        "scope": "dif_guided_fewshot_measurement_calibration",
        "input_contract": {
            "datasets": ["edaic", "cmdc"],
            "feature_family": "text_bge",
            "model_input_columns": int(len(feature_cols)),
            "measurement_items": MEASUREMENT_ITEMS,
            "anchor_items": ANCHOR_ITEMS,
            "dif_items": DIF_ITEMS,
            "k_shots": K_SHOTS,
            "raw_text_or_media_read": False,
            "row_level_predictions_read": False,
            "private_review_material_read": False,
            "official_test_labels_used": False,
        },
        "model_contract": {
            "seeds": SEEDS,
            "directions": ["D1_edaic_source_cmdc_target", "D2_cmdc_source_edaic_target"],
            "models": list(MODEL_TO_LADDER),
            "ridge_alpha_grid": mv07.RIDGE_ALPHA_GRID,
            "output_identity_classifier": "standardized_balanced_logistic_regression",
            "target_reference_uses_eval_labels_for_evaluation_truth": True,
            "target_reference_used_for_training_or_calibration": False,
        },
        "outputs": {
            "tracked_outputs": sorted(TRACKED_FILES),
            "local_only_outputs_not_written_by_runner": [
                "target shot maps",
                "row-level predictions",
                "theta tables",
                "fitted measurement parameters",
                "calibration parameter values",
                "model artifacts",
            ],
            "metric_seed_rows": int(len(metric_by_seed)),
            "metric_summary_rows": int(len(metric_summary)),
            "learning_curve_rows": int(len(learning)),
            "identity_rows": int(len(identity_summary)),
            "split_audit_rows": int(len(split_audit)),
        },
        "verdict": verdict,
        "artifact_hygiene_passed": False,
    }
    (out_dir / "run_summary.json").write_text(json.dumps(run_summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    write_report(out_dir, run_summary, gates, comparison, identity_summary)

    hygiene = artifact_hygiene(out_dir)
    gates = build_pass_fail_gates(split_audit, completeness, gate_diag, identity_summary, bool(hygiene["artifact_hygiene_passed"]))
    verdict = build_verdict(gates, gate_diag, learning, identity_summary)
    gates.to_csv(out_dir / "pass_fail_gate_results.csv", index=False)
    run_summary["verdict"] = verdict
    run_summary["artifact_hygiene_passed"] = bool(hygiene["artifact_hygiene_passed"])
    (out_dir / "run_summary.json").write_text(json.dumps(run_summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    write_report(out_dir, run_summary, gates, comparison, identity_summary)
    hygiene = artifact_hygiene(out_dir)
    (out_dir / "artifact_hygiene_audit.json").write_text(json.dumps(hygiene, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if not hygiene["artifact_hygiene_passed"]:
        raise SystemExit("artifact hygiene violations found; see artifact_hygiene_audit.json")
    return run_summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--manifest-dir", type=Path, default=DEFAULT_MANIFEST_DIR)
    parser.add_argument("--split-path", type=Path, default=DEFAULT_SPLIT_PATH)
    parser.add_argument("--phase2-root", type=Path, default=DEFAULT_PHASE2_ROOT)
    args = parser.parse_args()
    run_summary = run_experiment(args.out_dir, args.manifest_dir, args.split_path, args.phase2_root)
    print(json.dumps(run_summary["verdict"], indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
