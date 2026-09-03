#!/usr/bin/env python3
"""Run MV28 target-label budget and uncertainty reviewer-response study.

MV28 answers the reviewer concern that the calibrated transfer rows must be
compared against target-only training under the same labeled target budget and
that five seeds are too small for primary uncertainty evidence. It reuses the
MV24 official Qwen3+WavLM+OpenFace feature contract and neural heads, varies
the target calibration budget, repeats subject-level calibration/evaluation
splits, and reports aggregate repeated-split plus participant-bootstrap
uncertainty only.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import re
import subprocess
import sys
from concurrent.futures import ProcessPoolExecutor, as_completed
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def normalize_thread_env() -> None:
    for key in ["OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS"]:
        value = str(os.environ.get(key, "")).strip()
        if not value.isdigit() or int(value) <= 0:
            os.environ[key] = "1"


normalize_thread_env()

import numpy as np
import pandas as pd
import torch
import torch.nn.functional as F
from sklearn.model_selection import train_test_split

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "scripts"))

import phase5_run_mv24_measurement_aware_ordinal_model as mv24


DEFAULT_INPUT_ROOT = Path("/root/autodl-tmp")
DEFAULT_MANIFEST_DIR = DEFAULT_INPUT_ROOT / "datasets" / "manifests"
DEFAULT_OUT_DIR = ROOT / "analysis" / "phase5_minimal_validation" / "p5_mv28_target_label_budget_uncertainty"

METHOD_ORDER = [
    "target_only_direct_mlp",
    "target_only_ordinal",
    "direct_target_finetune",
    "direct_multitask_shared_head",
    "shared_head_joint_adaptation",
    "generic_target_mlp_head",
    "full_without_mmd",
]
SOURCE_PLUS_TARGET_METHODS = [
    "direct_target_finetune",
    "direct_multitask_shared_head",
    "shared_head_joint_adaptation",
    "generic_target_mlp_head",
    "full_without_mmd",
]
MEASUREMENT_AWARE_REFERENCE = "full_without_mmd"
TARGET_ONLY_REFERENCE = "target_only_direct_mlp"
LOWER_IS_BETTER_METRICS = [
    "target_macro_item_mae",
    "target_total_mae",
    "target_binned_item_calibration_mae",
    "total_calibration_in_the_large_abs",
    "total_calibration_slope_abs_error",
]
SUMMARY_METRICS = [
    "target_macro_item_mae",
    "target_total_mae",
    "target_total_rmse",
    "target_total_ccc",
    "target_binned_item_calibration_mae",
    "total_calibration_in_the_large",
    "total_calibration_in_the_large_abs",
    "total_calibration_ols_intercept",
    "total_calibration_slope",
    "total_calibration_slope_abs_error",
    "target_binary_macro_f1",
    "target_binary_balanced_accuracy",
    "target_binary_auroc",
    "target_binary_auprc",
]
BOOTSTRAP_METRICS = [
    "target_macro_item_mae",
    "target_total_mae",
    "target_binned_item_calibration_mae",
    "total_calibration_in_the_large_abs",
    "total_calibration_slope_abs_error",
]
TRACKED_FILES = {
    "artifact_hygiene_audit.json",
    "calibration_metric_table.csv",
    "calibration_metric_table.md",
    "feature_view_contract.csv",
    "label_budget_curve_by_split.csv",
    "label_budget_curve_summary.csv",
    "label_budget_curve_table.csv",
    "label_budget_curve_table.md",
    "measurement_aware_pairwise_delta_summary.csv",
    "measurement_aware_pairwise_delta_table.csv",
    "measurement_aware_pairwise_delta_table.md",
    "participant_bootstrap_delta_summary.csv",
    "report.md",
    "run_summary.json",
    "target_only_delta_summary.csv",
    "target_only_delta_table.csv",
    "target_only_delta_table.md",
}


@dataclass(frozen=True)
class BudgetSpec:
    budget_id: str
    requested_calibration_count: int | None
    is_mv24_default: bool


_WORKER_TABLES: dict[str, pd.DataFrame] | None = None
_WORKER_FEATURE_COLS: list[str] | None = None
_WORKER_BUDGETS: list[BudgetSpec] | None = None
_WORKER_ARGS: argparse.Namespace | None = None


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def git_commit() -> str:
    return subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT, text=True).strip()


def clean_tracked_outputs(out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    for name in TRACKED_FILES:
        path = out_dir / name
        if path.exists():
            path.unlink()


def device_from_args(args: argparse.Namespace) -> torch.device:
    return torch.device(args.device if args.device != "auto" else ("cuda" if torch.cuda.is_available() else "cpu"))


def split_indices_for_budget(labels: np.ndarray, budget: BudgetSpec, split_seed: int, args: argparse.Namespace) -> tuple[np.ndarray, np.ndarray]:
    if budget.is_mv24_default:
        return mv24.calibration_split_indices(
            labels,
            split_seed,
            fraction=args.target_calibration_fraction,
            minimum=args.target_calibration_min,
        )
    n_rows = int(labels.shape[0])
    n_calib = int(budget.requested_calibration_count)
    min_eval = int(args.minimum_evaluation_count)
    if n_calib < 1 or n_calib > n_rows - min_eval:
        raise ValueError(f"budget {n_calib} leaves fewer than {min_eval} target evaluation subjects")
    indices = np.arange(n_rows)
    groups = mv24.severity_groups(labels)
    unique_groups = np.unique(groups)
    group_counts = np.bincount(groups)
    stratify = None
    if (
        len(unique_groups) > 1
        and n_calib >= len(unique_groups)
        and n_rows - n_calib >= len(unique_groups)
        and np.all(group_counts[group_counts > 0] >= 2)
    ):
        stratify = groups
    calib_idx, eval_idx = train_test_split(
        indices,
        train_size=n_calib,
        random_state=int(split_seed),
        shuffle=True,
        stratify=stratify,
    )
    return np.asarray(sorted(calib_idx), dtype=np.int64), np.asarray(sorted(eval_idx), dtype=np.int64)


def budget_specs(args: argparse.Namespace) -> list[BudgetSpec]:
    specs = [BudgetSpec(f"k{int(k)}", int(k), False) for k in args.target_budgets]
    if args.include_mv24_default_budget:
        specs.append(BudgetSpec("mv24_default", None, True))
    seen: set[str] = set()
    unique: list[BudgetSpec] = []
    for spec in specs:
        if spec.budget_id not in seen:
            unique.append(spec)
            seen.add(spec.budget_id)
    return unique


def total_calibration_metrics(pred: np.ndarray, truth: np.ndarray) -> dict[str, float]:
    pred_total = mv24.clip_items(pred).sum(axis=1).astype(np.float64)
    truth_total = truth.astype(np.float64).sum(axis=1)
    citl = float(truth_total.mean() - pred_total.mean())
    pred_var = float(np.var(pred_total, ddof=1)) if len(pred_total) > 1 else math.nan
    if not np.isfinite(pred_var) or pred_var <= 1e-12:
        slope = math.nan
        intercept = math.nan
        slope_error = math.nan
    else:
        slope = float(np.cov(pred_total, truth_total, ddof=1)[0, 1] / pred_var)
        intercept = float(truth_total.mean() - slope * pred_total.mean())
        slope_error = float(abs(slope - 1.0))
    return {
        "total_calibration_in_the_large": citl,
        "total_calibration_in_the_large_abs": float(abs(citl)),
        "total_calibration_ols_intercept": intercept,
        "total_calibration_slope": slope,
        "total_calibration_slope_abs_error": slope_error,
    }


def evaluate_predictions(pred: np.ndarray, truth: np.ndarray) -> dict[str, float]:
    base = mv24.evaluate_predictions(pred, truth)
    return {
        "target_macro_item_mae": float(base["target_macro_item_mae"]),
        "target_total_mae": float(base["target_total_mae"]),
        "target_total_rmse": float(base["target_total_rmse"]),
        "target_total_ccc": float(base["target_total_ccc"]),
        "target_binned_item_calibration_mae": float(base["target_calibration_mae"]),
        "target_binary_macro_f1": float(base["target_binary_macro_f1"]),
        "target_binary_balanced_accuracy": float(base["target_binary_balanced_accuracy"]),
        "target_binary_auroc": float(base["target_binary_auroc"]),
        "target_binary_auprc": float(base["target_binary_auprc"]),
        **total_calibration_metrics(pred, truth),
    }


def train_target_only_direct_mlp(
    target_x_all: np.ndarray,
    target_y_all: np.ndarray,
    target_calib_idx: np.ndarray,
    *,
    seed: int,
    args: argparse.Namespace,
) -> np.ndarray:
    mv24.set_seed(seed)
    device = device_from_args(args)
    model = mv24.DirectRegressor(target_x_all.shape[1], args.hidden_dim, target_y_all.shape[1], args.dropout).to(device)
    xt = mv24.tensor(target_x_all, device)
    yt = mv24.tensor(target_y_all.astype(np.float32), device)
    target_calib = torch.as_tensor(target_calib_idx, dtype=torch.long, device=device)
    optimizer = torch.optim.AdamW(model.parameters(), lr=args.learning_rate, weight_decay=args.weight_decay)
    for _ in range(int(args.target_only_epochs)):
        optimizer.zero_grad(set_to_none=True)
        loss = F.mse_loss(model(xt[target_calib]), yt[target_calib])
        loss.backward()
        optimizer.step()
    with torch.inference_mode():
        pred = model(xt).detach().cpu().numpy().astype(np.float32)
    return pred


def train_target_only_ordinal(
    target_dataset: str,
    target_x_all: np.ndarray,
    target_y_all: np.ndarray,
    target_calib_idx: np.ndarray,
    *,
    seed: int,
    args: argparse.Namespace,
) -> np.ndarray:
    mv24.set_seed(seed)
    device = device_from_args(args)
    model = mv24.MeasurementAwareOrdinalNet(
        target_x_all.shape[1],
        args.hidden_dim,
        target_y_all.shape[1],
        args.dropout,
        shared_head=False,
    ).to(device)
    xt = mv24.tensor(target_x_all, device)
    yt = mv24.tensor(target_y_all, device, dtype=torch.long)
    target_calib = torch.as_tensor(target_calib_idx, dtype=torch.long, device=device)
    optimizer = torch.optim.AdamW(model.parameters(), lr=args.learning_rate, weight_decay=args.weight_decay)
    for _ in range(int(args.target_only_epochs)):
        optimizer.zero_grad(set_to_none=True)
        _, probs, _ = model(xt[target_calib], target_dataset)
        loss = mv24.ordinal_nll(probs, yt[target_calib])
        loss.backward()
        optimizer.step()
    with torch.inference_mode():
        _, _, expected = model(xt, target_dataset)
    return expected.detach().cpu().numpy().astype(np.float32)


def train_and_predict_method(
    method: str,
    source_dataset: str,
    target_dataset: str,
    source_x: np.ndarray,
    source_y: np.ndarray,
    target_x_all: np.ndarray,
    target_y_all: np.ndarray,
    target_calib_idx: np.ndarray,
    *,
    seed: int,
    args: argparse.Namespace,
) -> np.ndarray:
    if method == "target_only_direct_mlp":
        return train_target_only_direct_mlp(
            target_x_all,
            target_y_all.astype(np.float32),
            target_calib_idx,
            seed=seed,
            args=args,
        )
    if method == "target_only_ordinal":
        return train_target_only_ordinal(
            target_dataset,
            target_x_all,
            target_y_all,
            target_calib_idx,
            seed=seed,
            args=args,
        )
    if method in {"direct_target_finetune", "direct_multitask_shared_head"}:
        pred_all, _, _, _ = mv24.train_direct_adaptation(
            method,
            source_x,
            source_y.astype(np.float32),
            target_x_all,
            target_y_all.astype(np.float32),
            target_calib_idx,
            seed=seed,
            args=args,
        )
        return pred_all
    if method == "generic_target_mlp_head":
        model = mv24.train_generic_target_mlp_head(
            source_dataset,
            target_dataset,
            source_x,
            source_y.astype(np.float32),
            target_x_all,
            target_y_all.astype(np.float32),
            target_calib_idx,
            seed=seed,
            args=args,
        )
        pred_all, _, _, _ = mv24.predict_generic_target_mlp_head(
            model,
            source_dataset,
            target_dataset,
            source_x,
            target_x_all,
            args=args,
        )
        return pred_all
    if method in {"shared_head_joint_adaptation", "full_without_mmd"}:
        model = mv24.train_measurement_model(
            method,
            source_dataset,
            target_dataset,
            source_x,
            source_y,
            target_x_all,
            target_y_all,
            target_calib_idx,
            seed=seed,
            args=args,
            latent_mmd_weight=0.0,
        )
        pred_all, _, _, _, _, _ = mv24.predict_measurement_model(
            model,
            source_dataset,
            target_dataset,
            source_x,
            target_x_all,
            args=args,
        )
        return pred_all
    raise ValueError(f"unsupported MV28 method: {method}")


def summary_stats(values: list[float] | np.ndarray) -> dict[str, float]:
    array = np.asarray(values, dtype=np.float64)
    array = array[np.isfinite(array)]
    if len(array) == 0:
        return {"count": 0, "mean": math.nan, "std": math.nan, "median": math.nan, "ci95_low": math.nan, "ci95_high": math.nan}
    return {
        "count": int(len(array)),
        "mean": float(array.mean()),
        "std": float(array.std(ddof=1)) if len(array) > 1 else 0.0,
        "median": float(np.median(array)),
        "ci95_low": float(np.quantile(array, 0.025)),
        "ci95_high": float(np.quantile(array, 0.975)),
    }


def summarize_by_method(metrics: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    group_cols = [
        "transfer_id",
        "target_dataset",
        "budget_id",
        "target_calibration_count",
        "target_evaluation_count",
        "target_calibration_fraction_actual",
        "method",
        "method_rank",
        "training_regime",
        "source_labels_used",
        "ordinal_parameterization",
    ]
    for key, group in metrics.groupby(group_cols, dropna=False):
        row = dict(zip(group_cols, key))
        row["split_count"] = int(group["split_index"].nunique())
        for metric in SUMMARY_METRICS:
            stats_row = summary_stats(pd.to_numeric(group[metric], errors="coerce").to_numpy(dtype=np.float64))
            for name, value in stats_row.items():
                row[f"{metric}_{name}"] = value
        rows.append(row)
    return pd.DataFrame(rows).sort_values(["transfer_id", "target_calibration_count", "method_rank"]).reset_index(drop=True)


def paired_delta_summaries(metrics: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    target_rows: list[dict[str, Any]] = []
    ma_rows: list[dict[str, Any]] = []
    key_cols = ["transfer_id", "budget_id", "split_index"]
    for (transfer_id, budget_id), group in metrics.groupby(["transfer_id", "budget_id"], dropna=False):
        target_ref = group[group["method"].eq(TARGET_ONLY_REFERENCE)].set_index("split_index")
        ma_ref = group[group["method"].eq(MEASUREMENT_AWARE_REFERENCE)].set_index("split_index")
        for method in SOURCE_PLUS_TARGET_METHODS + ["target_only_ordinal"]:
            method_rows = group[group["method"].eq(method)].set_index("split_index")
            common = target_ref.index.intersection(method_rows.index)
            if len(common) > 0:
                descriptor = group[group["method"].eq(method)].iloc[0]
                for metric in LOWER_IS_BETTER_METRICS:
                    delta = (
                        pd.to_numeric(method_rows.loc[common, metric], errors="coerce").to_numpy(dtype=np.float64)
                        - pd.to_numeric(target_ref.loc[common, metric], errors="coerce").to_numpy(dtype=np.float64)
                    )
                    stats_row = summary_stats(delta)
                    target_rows.append(
                        {
                            "transfer_id": transfer_id,
                            "budget_id": budget_id,
                            "target_calibration_count": int(descriptor["target_calibration_count"]),
                            "target_evaluation_count": int(descriptor["target_evaluation_count"]),
                            "comparison": f"{method}_minus_{TARGET_ONLY_REFERENCE}",
                            "method": method,
                            "reference_method": TARGET_ONLY_REFERENCE,
                            "metric": metric,
                            "delta_definition": "method metric minus target-only direct MLP metric; negative means the method is lower-error",
                            "paired_split_count": int(len(common)),
                            "method_lower_error_split_fraction": float(np.mean(delta < 0.0)),
                            **{f"delta_{name}": value for name, value in stats_row.items()},
                        }
                    )
            if method == MEASUREMENT_AWARE_REFERENCE:
                continue
            common = ma_ref.index.intersection(method_rows.index)
            if len(common) > 0:
                descriptor = group[group["method"].eq(method)].iloc[0]
                for metric in LOWER_IS_BETTER_METRICS:
                    delta = (
                        pd.to_numeric(method_rows.loc[common, metric], errors="coerce").to_numpy(dtype=np.float64)
                        - pd.to_numeric(ma_ref.loc[common, metric], errors="coerce").to_numpy(dtype=np.float64)
                    )
                    stats_row = summary_stats(delta)
                    ma_rows.append(
                        {
                            "transfer_id": transfer_id,
                            "budget_id": budget_id,
                            "target_calibration_count": int(descriptor["target_calibration_count"]),
                            "target_evaluation_count": int(descriptor["target_evaluation_count"]),
                            "comparison": f"{method}_minus_{MEASUREMENT_AWARE_REFERENCE}",
                            "method": method,
                            "reference_method": MEASUREMENT_AWARE_REFERENCE,
                            "metric": metric,
                            "delta_definition": "method metric minus measurement-aware metric; positive means measurement-aware is lower-error",
                            "paired_split_count": int(len(common)),
                            "measurement_aware_lower_error_split_fraction": float(np.mean(delta > 0.0)),
                            **{f"delta_{name}": value for name, value in stats_row.items()},
                        }
                    )
    target_summary = pd.DataFrame(target_rows)
    ma_summary = pd.DataFrame(ma_rows)
    if not target_summary.empty:
        target_summary = target_summary.sort_values(["transfer_id", "target_calibration_count", "method", "metric"]).reset_index(drop=True)
    if not ma_summary.empty:
        ma_summary = ma_summary.sort_values(["transfer_id", "target_calibration_count", "method", "metric"]).reset_index(drop=True)
    return target_summary, ma_summary


def bootstrap_delta_values(
    truth: np.ndarray,
    pred_by_method: dict[str, np.ndarray],
    *,
    split_seed: int,
    draw_count: int,
) -> dict[tuple[str, str, str], list[float]]:
    rng = np.random.default_rng(int(split_seed) + 1000003)
    values: dict[tuple[str, str, str], list[float]] = defaultdict(list)
    n_eval = int(truth.shape[0])
    for _ in range(int(draw_count)):
        sample_idx = rng.integers(0, n_eval, size=n_eval)
        sample_truth = truth[sample_idx]
        sample_metrics = {
            method: evaluate_predictions(pred[sample_idx], sample_truth)
            for method, pred in pred_by_method.items()
        }
        target_ref = sample_metrics[TARGET_ONLY_REFERENCE]
        ma_ref = sample_metrics[MEASUREMENT_AWARE_REFERENCE]
        present_comparison_methods = [
            method
            for method in SOURCE_PLUS_TARGET_METHODS + ["target_only_ordinal"]
            if method in sample_metrics
        ]
        for method in present_comparison_methods:
            method_metrics = sample_metrics[method]
            for metric in BOOTSTRAP_METRICS:
                values[("target_only_delta", method, metric)].append(float(method_metrics[metric] - target_ref[metric]))
            if method == MEASUREMENT_AWARE_REFERENCE:
                continue
            for metric in BOOTSTRAP_METRICS:
                values[("measurement_aware_delta", method, metric)].append(float(method_metrics[metric] - ma_ref[metric]))
    return values


def merge_bootstrap_store(
    store: dict[tuple[str, str, str, str, str], list[float]],
    transfer_id: str,
    budget_id: str,
    draw_values: dict[tuple[str, str, str], list[float]],
) -> None:
    for (comparison_family, method, metric), values in draw_values.items():
        store[(comparison_family, transfer_id, budget_id, method, metric)].extend(values)


def summarize_bootstrap_store(store: dict[tuple[str, str, str, str, str], list[float]], metrics: pd.DataFrame) -> pd.DataFrame:
    descriptors = (
        metrics[["transfer_id", "budget_id", "target_calibration_count", "target_evaluation_count"]]
        .drop_duplicates()
        .set_index(["transfer_id", "budget_id"])
    )
    rows: list[dict[str, Any]] = []
    for (comparison_family, transfer_id, budget_id, method, metric), values in sorted(store.items()):
        stats_row = summary_stats(values)
        descriptor = descriptors.loc[(transfer_id, budget_id)]
        rows.append(
            {
                "comparison_family": comparison_family,
                "transfer_id": transfer_id,
                "budget_id": budget_id,
                "target_calibration_count": int(descriptor["target_calibration_count"]),
                "target_evaluation_count": int(descriptor["target_evaluation_count"]),
                "method": method,
                "reference_method": TARGET_ONLY_REFERENCE if comparison_family == "target_only_delta" else MEASUREMENT_AWARE_REFERENCE,
                "metric": metric,
                "delta_definition": (
                    "method metric minus target-only direct MLP metric; negative means the method is lower-error"
                    if comparison_family == "target_only_delta"
                    else "method metric minus measurement-aware metric; positive means measurement-aware is lower-error"
                ),
                "bootstrap_draw_count": int(stats_row["count"]),
                **{f"delta_{name}": value for name, value in stats_row.items() if name != "count"},
            }
        )
    if not rows:
        return pd.DataFrame()
    return pd.DataFrame(rows).sort_values(["comparison_family", "transfer_id", "target_calibration_count", "method", "metric"]).reset_index(drop=True)


def fmt_interval(row: pd.Series, prefix: str) -> str:
    mean = row[f"{prefix}_mean"]
    low = row[f"{prefix}_ci95_low"]
    high = row[f"{prefix}_ci95_high"]
    if pd.isna(mean):
        return ""
    return f"{float(mean):.3f} [{float(low):.3f}, {float(high):.3f}]"


def display_transfer(transfer_id: str) -> str:
    return mv24.display_transfer_id(transfer_id)


def display_method(method: str) -> str:
    names = {
        "target_only_direct_mlp": "Target-only direct MLP",
        "target_only_ordinal": "Target-only ordinal",
        "direct_target_finetune": "Source warm-start target fine-tune",
        "direct_multitask_shared_head": "Source+target direct multitask",
        "shared_head_joint_adaptation": "Shared ordinal head",
        "generic_target_mlp_head": "Generic target MLP head",
        "full_without_mmd": "Measurement-aware ordinal",
    }
    return names.get(method, method)


def write_label_budget_curve_table(summary: pd.DataFrame, path_csv: Path, path_md: Path) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for _, row in summary.iterrows():
        rows.append(
            {
                "transfer_id": row["transfer_id"],
                "budget_id": row["budget_id"],
                "target_calibration_count": int(row["target_calibration_count"]),
                "target_evaluation_count": int(row["target_evaluation_count"]),
                "method": row["method"],
                "method_display": display_method(str(row["method"])),
                "training_regime": row["training_regime"],
                "macro_item_mae": fmt_interval(row, "target_macro_item_mae"),
                "total_mae": fmt_interval(row, "target_total_mae"),
                "binned_item_calibration_mae": fmt_interval(row, "target_binned_item_calibration_mae"),
                "calibration_in_the_large_abs": fmt_interval(row, "total_calibration_in_the_large_abs"),
                "calibration_slope_abs_error": fmt_interval(row, "total_calibration_slope_abs_error"),
                "split_count": int(row["split_count"]),
                "method_rank": int(row["method_rank"]),
            }
        )
    table = pd.DataFrame(rows).sort_values(["transfer_id", "target_calibration_count", "method_rank"]).reset_index(drop=True)
    table.drop(columns=["method_rank"]).to_csv(path_csv, index=False)
    lines: list[str] = []
    for transfer_id, transfer_group in table.groupby("transfer_id", sort=False):
        lines.extend(
            [
                f"**{display_transfer(transfer_id)}.**",
                "",
                "| k | eval n | method | regime | macro item MAE | total MAE | binned item calibration MAE | abs CITL | abs slope error |",
                "| ---: | ---: | --- | --- | ---: | ---: | ---: | ---: | ---: |",
            ]
        )
        for _, row in transfer_group.iterrows():
            lines.append(
                "| "
                + " | ".join(
                    [
                        str(int(row["target_calibration_count"])),
                        str(int(row["target_evaluation_count"])),
                        str(row["method_display"]),
                        str(row["training_regime"]),
                        str(row["macro_item_mae"]),
                        str(row["total_mae"]),
                        str(row["binned_item_calibration_mae"]),
                        str(row["calibration_in_the_large_abs"]),
                        str(row["calibration_slope_abs_error"]),
                    ]
                )
                + " |"
            )
        lines.append("")
    path_md.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    return table.drop(columns=["method_rank"])


def write_delta_table(
    summary: pd.DataFrame,
    path_csv: Path,
    path_md: Path,
    *,
    family: str,
) -> pd.DataFrame:
    if summary.empty:
        path_csv.write_text("", encoding="utf-8")
        path_md.write_text("No delta rows were generated.\n", encoding="utf-8")
        return pd.DataFrame()
    if family == "target_only":
        metrics = ["target_macro_item_mae", "target_total_mae", "target_binned_item_calibration_mae"]
        fraction_col = "method_lower_error_split_fraction"
        delta_label = "delta method - target-only"
    else:
        metrics = ["target_macro_item_mae", "target_total_mae", "target_binned_item_calibration_mae"]
        fraction_col = "measurement_aware_lower_error_split_fraction"
        delta_label = "delta method - measurement-aware"
    table = summary[summary["metric"].isin(metrics)].copy()
    table["method_display"] = table["method"].map(display_method)
    table["delta_mean_ci95"] = table.apply(lambda row: fmt_interval(row, "delta"), axis=1)
    table.to_csv(path_csv, index=False)
    lines: list[str] = []
    for transfer_id, transfer_group in table.groupby("transfer_id", sort=False):
        lines.extend(
            [
                f"**{display_transfer(transfer_id)}.**",
                "",
                f"| k | method | metric | {delta_label} | split fraction | splits |",
                "| ---: | --- | --- | ---: | ---: | ---: |",
            ]
        )
        for _, row in transfer_group.iterrows():
            lines.append(
                "| "
                + " | ".join(
                    [
                        str(int(row["target_calibration_count"])),
                        str(row["method_display"]),
                        str(row["metric"]),
                        str(row["delta_mean_ci95"]),
                        f"{float(row[fraction_col]):.2f}",
                        str(int(row["paired_split_count"])),
                    ]
                )
                + " |"
            )
        lines.append("")
    path_md.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    return table


def write_calibration_metric_table(summary: pd.DataFrame, path_csv: Path, path_md: Path) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for _, row in summary.iterrows():
        rows.append(
            {
                "transfer_id": row["transfer_id"],
                "budget_id": row["budget_id"],
                "target_calibration_count": int(row["target_calibration_count"]),
                "target_evaluation_count": int(row["target_evaluation_count"]),
                "method": row["method"],
                "method_display": display_method(str(row["method"])),
                "calibration_in_the_large": fmt_interval(row, "total_calibration_in_the_large"),
                "calibration_in_the_large_abs": fmt_interval(row, "total_calibration_in_the_large_abs"),
                "ols_intercept": fmt_interval(row, "total_calibration_ols_intercept"),
                "slope": fmt_interval(row, "total_calibration_slope"),
                "slope_abs_error": fmt_interval(row, "total_calibration_slope_abs_error"),
                "binned_item_calibration_mae": fmt_interval(row, "target_binned_item_calibration_mae"),
                "split_count": int(row["split_count"]),
                "method_rank": int(row["method_rank"]),
            }
        )
    table = pd.DataFrame(rows).sort_values(["transfer_id", "target_calibration_count", "method_rank"]).reset_index(drop=True)
    table.drop(columns=["method_rank"]).to_csv(path_csv, index=False)
    lines = [
        "CITL is observed shared-PHQ total minus predicted shared-PHQ total; ideal CITL is 0 and ideal slope is 1.",
        "",
    ]
    selected_methods = {TARGET_ONLY_REFERENCE, "direct_multitask_shared_head", "shared_head_joint_adaptation", MEASUREMENT_AWARE_REFERENCE}
    for transfer_id, transfer_group in table[table["method"].isin(selected_methods)].groupby("transfer_id", sort=False):
        lines.extend(
            [
                f"**{display_transfer(transfer_id)}.**",
                "",
                "| k | method | CITL | abs CITL | slope | abs slope error | binned item calibration MAE |",
                "| ---: | --- | ---: | ---: | ---: | ---: | ---: |",
            ]
        )
        for _, row in transfer_group.iterrows():
            lines.append(
                "| "
                + " | ".join(
                    [
                        str(int(row["target_calibration_count"])),
                        str(row["method_display"]),
                        str(row["calibration_in_the_large"]),
                        str(row["calibration_in_the_large_abs"]),
                        str(row["slope"]),
                        str(row["slope_abs_error"]),
                        str(row["binned_item_calibration_mae"]),
                    ]
                )
                + " |"
            )
        lines.append("")
    path_md.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    return table.drop(columns=["method_rank"])


def write_report(out_dir: Path, run_summary: dict[str, Any]) -> None:
    lines = [
        "# P5 MV28 Target-Label Budget And Uncertainty",
        "",
        f"Generated: `{run_summary['generated_at']}`",
        "",
        "## Scope",
        "",
        "MV28 tests whether source-plus-target calibrated adaptation still improves over target-only training when the labeled target budget is matched. It also replaces five-seed superiority language with repeated subject-level calibration/evaluation splits and participant-bootstrap paired uncertainty.",
        "",
        "## Design",
        "",
        f"- Transfer directions: `{';'.join(run_summary['directions'])}`.",
        f"- Target budgets: `{';'.join(run_summary['budget_ids'])}`.",
        f"- Repeated splits per direction-budget: `{run_summary['split_count']}`.",
        f"- Participant bootstrap draws per split: `{run_summary['participant_bootstrap_draws']}`.",
        f"- Methods: `{';'.join(run_summary['methods'])}`.",
        "",
        "## Label-Budget Curve",
        "",
        (out_dir / "label_budget_curve_table.md").read_text(encoding="utf-8").strip(),
        "",
        "## Source-Plus-Target Versus Target-Only",
        "",
        "Negative deltas mean the source-plus-target method has lower error than the target-only direct MLP under the same target-label budget.",
        "",
        (out_dir / "target_only_delta_table.md").read_text(encoding="utf-8").strip(),
        "",
        "## Measurement-Aware Pairwise Deltas",
        "",
        "Positive deltas mean the measurement-aware ordinal model has lower error than the comparison method.",
        "",
        (out_dir / "measurement_aware_pairwise_delta_table.md").read_text(encoding="utf-8").strip(),
        "",
        "## Calibration Metrics",
        "",
        (out_dir / "calibration_metric_table.md").read_text(encoding="utf-8").strip(),
        "",
        "## Interpretation Handle",
        "",
        run_summary["interpretation_handle"],
        "",
    ]
    (out_dir / "report.md").write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def artifact_hygiene(out_dir: Path) -> dict[str, Any]:
    forbidden_patterns = [
        r"/root/",
        r"/autodl-tmp/",
        r"\bsubject_id\b",
        r"\bparticipant_key\b",
        r"\btext_path\b",
        r"\baudio_path\b",
        r"\bvideo_path\b",
        r"\.wav\b",
        r"\.mp4\b",
        r"\.avi\b",
    ]
    violations: list[dict[str, str]] = []
    checked = 0
    for name in sorted(TRACKED_FILES - {"artifact_hygiene_audit.json"}):
        path = out_dir / name
        if not path.exists():
            continue
        checked += 1
        text = path.read_text(encoding="utf-8", errors="ignore")
        for pattern in forbidden_patterns:
            if re.search(pattern, text, flags=re.IGNORECASE):
                violations.append({"file": path.name, "pattern": pattern})
    return {
        "audit_id": "P5_MV28_target_label_budget_uncertainty_hygiene",
        "generated_at": utc_now(),
        "files_checked": int(checked),
        "artifact_hygiene_passed": not violations,
        "violation_count": int(len(violations)),
        "violations": violations,
    }


def run_direction_budget_split(
    source_dataset: str,
    target_dataset: str,
    raw_source: pd.DataFrame,
    raw_target: pd.DataFrame,
    source_y: np.ndarray,
    target_y_all: np.ndarray,
    feature_cols: list[str],
    budget: BudgetSpec,
    split_index: int,
    args: argparse.Namespace,
) -> tuple[list[dict[str, Any]], dict[tuple[str, str, str, str, str], list[float]]]:
    rows: list[dict[str, Any]] = []
    bootstrap_store: dict[tuple[str, str, str, str, str], list[float]] = defaultdict(list)
    transfer_id = f"{source_dataset}_to_{target_dataset}_phq_shared"
    selected_methods = [method for method in METHOD_ORDER if method in set(args.methods)]
    split_seed = int(args.seed_offset + split_index)
    target_calib_idx, target_eval_idx = split_indices_for_budget(target_y_all, budget, split_seed, args)
    source_x, target_x_all, actual_components = mv24.prepare_pair_features(
        raw_source,
        raw_target,
        feature_cols,
        n_components=args.pca_components,
        seed=split_seed,
    )
    target_y_eval = target_y_all[target_eval_idx]
    pred_by_method: dict[str, np.ndarray] = {}
    for method in selected_methods:
        pred_all = train_and_predict_method(
            method,
            source_dataset,
            target_dataset,
            source_x,
            source_y,
            target_x_all,
            target_y_all,
            target_calib_idx,
            seed=split_seed,
            args=args,
        )
        pred_eval = pred_all[target_eval_idx]
        pred_by_method[method] = pred_eval
        metrics = evaluate_predictions(pred_eval, target_y_eval)
        rows.append(
            {
                "run_id": "P5_MV28_target_label_budget_uncertainty",
                "transfer_id": transfer_id,
                "source_dataset": source_dataset,
                "target_dataset": target_dataset,
                "budget_id": budget.budget_id,
                "budget_is_mv24_default": bool(budget.is_mv24_default),
                "requested_calibration_count": (
                    int(budget.requested_calibration_count)
                    if budget.requested_calibration_count is not None
                    else math.nan
                ),
                "target_participant_count": int(len(raw_target)),
                "target_calibration_count": int(len(target_calib_idx)),
                "target_evaluation_count": int(len(target_eval_idx)),
                "target_calibration_fraction_actual": float(len(target_calib_idx) / len(raw_target)),
                "source_participant_count": int(len(raw_source)),
                "input_columns": int(len(feature_cols)),
                "pca_components": int(actual_components),
                "split_index": int(split_index),
                "split_seed": int(split_seed),
                "method": method,
                "method_rank": int(METHOD_ORDER.index(method)),
                "training_regime": "target_only" if method.startswith("target_only") else "source_plus_target_calibrated",
                "source_labels_used": bool(not method.startswith("target_only")),
                "ordinal_parameterization": bool("ordinal" in method or method in {"shared_head_joint_adaptation", "full_without_mmd"}),
                **metrics,
            }
        )
    if args.participant_bootstrap_draws > 0 and all(method in pred_by_method for method in [TARGET_ONLY_REFERENCE, MEASUREMENT_AWARE_REFERENCE]):
        draw_values = bootstrap_delta_values(
            target_y_eval,
            pred_by_method,
            split_seed=split_seed,
            draw_count=args.participant_bootstrap_draws,
        )
        merge_bootstrap_store(bootstrap_store, transfer_id, budget.budget_id, draw_values)
    return rows, bootstrap_store


def run_direction(
    source_dataset: str,
    target_dataset: str,
    tables: dict[str, pd.DataFrame],
    feature_cols: list[str],
    budgets: list[BudgetSpec],
    args: argparse.Namespace,
) -> tuple[list[dict[str, Any]], dict[tuple[str, str, str, str, str], list[float]]]:
    raw_source = tables[source_dataset].copy()
    raw_target = tables[target_dataset].copy()
    raw_source, raw_target = mv24.sanitize_pair(raw_source, raw_target, feature_cols)
    source_y = mv24.label_arrays(raw_source)
    target_y_all = mv24.label_arrays(raw_target)
    rows: list[dict[str, Any]] = []
    bootstrap_store: dict[tuple[str, str, str, str, str], list[float]] = defaultdict(list)
    for budget in budgets:
        for split_index in range(int(args.split_count)):
            split_rows, split_store = run_direction_budget_split(
                source_dataset,
                target_dataset,
                raw_source,
                raw_target,
                source_y,
                target_y_all,
                feature_cols,
                budget,
                split_index,
                args,
            )
            rows.extend(split_rows)
            for key, values in split_store.items():
                bootstrap_store[key].extend(values)
    return rows, bootstrap_store


def init_parallel_worker(
    tables: dict[str, pd.DataFrame],
    feature_cols: list[str],
    budgets: list[BudgetSpec],
    args_dict: dict[str, Any],
) -> None:
    global _WORKER_TABLES, _WORKER_FEATURE_COLS, _WORKER_BUDGETS, _WORKER_ARGS
    torch.set_num_threads(1)
    _WORKER_TABLES = tables
    _WORKER_FEATURE_COLS = feature_cols
    _WORKER_BUDGETS = budgets
    _WORKER_ARGS = argparse.Namespace(**args_dict)


def run_parallel_job(
    job: tuple[str, str, int, int],
) -> tuple[list[dict[str, Any]], list[tuple[tuple[str, str, str, str, str], list[float]]]]:
    source_dataset, target_dataset, budget_index, split_index = job
    if _WORKER_TABLES is None or _WORKER_FEATURE_COLS is None or _WORKER_BUDGETS is None or _WORKER_ARGS is None:
        raise RuntimeError("parallel worker context is not initialized")
    raw_source = _WORKER_TABLES[source_dataset].copy()
    raw_target = _WORKER_TABLES[target_dataset].copy()
    raw_source, raw_target = mv24.sanitize_pair(raw_source, raw_target, _WORKER_FEATURE_COLS)
    source_y = mv24.label_arrays(raw_source)
    target_y_all = mv24.label_arrays(raw_target)
    rows, store = run_direction_budget_split(
        source_dataset,
        target_dataset,
        raw_source,
        raw_target,
        source_y,
        target_y_all,
        _WORKER_FEATURE_COLS,
        _WORKER_BUDGETS[int(budget_index)],
        int(split_index),
        _WORKER_ARGS,
    )
    return rows, list(store.items())


def run_all_directions_parallel(
    tables: dict[str, pd.DataFrame],
    feature_cols: list[str],
    budgets: list[BudgetSpec],
    args: argparse.Namespace,
) -> tuple[list[dict[str, Any]], dict[tuple[str, str, str, str, str], list[float]]]:
    jobs = [
        (source_dataset, target_dataset, budget_index, split_index)
        for source_dataset, target_dataset in mv24.TRANSFER_DIRECTIONS
        for budget_index, _ in enumerate(budgets)
        for split_index in range(int(args.split_count))
    ]
    rows: list[dict[str, Any]] = []
    bootstrap_store: dict[tuple[str, str, str, str, str], list[float]] = defaultdict(list)
    with ProcessPoolExecutor(
        max_workers=int(args.parallel_workers),
        initializer=init_parallel_worker,
        initargs=(tables, feature_cols, budgets, dict(vars(args))),
    ) as executor:
        futures = [executor.submit(run_parallel_job, job) for job in jobs]
        for future in as_completed(futures):
            split_rows, split_store_items = future.result()
            rows.extend(split_rows)
            for key, values in split_store_items:
                bootstrap_store[key].extend(values)
    return rows, bootstrap_store


def best_rows(summary: pd.DataFrame) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for (transfer_id, budget_id), group in summary.groupby(["transfer_id", "budget_id"], dropna=False):
        best = group.sort_values("target_macro_item_mae_mean").iloc[0]
        rows.append(
            {
                "transfer_id": transfer_id,
                "budget_id": budget_id,
                "target_calibration_count": int(best["target_calibration_count"]),
                "best_macro_item_method": str(best["method"]),
                "best_macro_item_mae": float(best["target_macro_item_mae_mean"]),
                "best_training_regime": str(best["training_regime"]),
            }
        )
    return rows


def interpretation_from_deltas(target_delta: pd.DataFrame, ma_delta: pd.DataFrame) -> str:
    if "metric" not in target_delta.columns:
        macro = pd.DataFrame()
    else:
        macro = target_delta[target_delta["metric"].eq("target_macro_item_mae")].copy()
    source_methods = macro[macro["method"].isin(SOURCE_PLUS_TARGET_METHODS)].copy()
    source_better = int((source_methods["delta_mean"] < 0.0).sum()) if not source_methods.empty else 0
    source_total = int(len(source_methods))
    if "metric" not in ma_delta.columns:
        ma_macro = pd.DataFrame()
    else:
        ma_macro = ma_delta[ma_delta["metric"].eq("target_macro_item_mae")].copy()
    ma_better = int((ma_macro["delta_mean"] > 0.0).sum()) if not ma_macro.empty else 0
    ma_total = int(len(ma_macro))
    return (
        f"Across repeated label-budget splits, source-plus-target calibrated rows beat the target-only direct MLP "
        f"on mean macro item MAE in {source_better}/{source_total} method-budget-direction cells. "
        f"The measurement-aware ordinal row beats its matched alternatives on mean macro item MAE in {ma_better}/{ma_total} "
        "cells. Use these counts as reviewer-facing uncertainty evidence, not as a universal architecture superiority claim."
    )


def write_feature_contract(out_dir: Path, coverage: pd.DataFrame, args: argparse.Namespace) -> None:
    view = mv24.official_view()
    pd.DataFrame(
        [
            {
                "view_id": view.view_id,
                "modality_set": view.modality_set,
                "assets": ";".join(view.assets),
                "role": "official MV24 representation reused for MV28 label-budget uncertainty",
                "input_columns_total": int(coverage.groupby("dataset")["feature_columns"].sum().max()),
                "pca_components": int(args.pca_components),
                "large_artifact_policy": "read-only feature cache; aggregate outputs only",
            }
        ]
    ).to_csv(out_dir / "feature_view_contract.csv", index=False)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-root", type=Path, default=DEFAULT_INPUT_ROOT)
    parser.add_argument("--manifest-dir", type=Path, default=DEFAULT_MANIFEST_DIR)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--split-count", type=int, default=30)
    parser.add_argument("--seed-offset", type=int, default=28000)
    parser.add_argument("--target-budgets", type=int, nargs="*", default=[4, 8, 12, 16, 24])
    parser.add_argument("--include-mv24-default-budget", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--participant-bootstrap-draws", type=int, default=200)
    parser.add_argument("--minimum-evaluation-count", type=int, default=12)
    parser.add_argument("--pca-components", type=int, default=128)
    parser.add_argument("--hidden-dim", type=int, default=256)
    parser.add_argument("--dropout", type=float, default=0.08)
    parser.add_argument("--learning-rate", type=float, default=1e-3)
    parser.add_argument("--head-learning-rate", type=float, default=2e-3)
    parser.add_argument("--weight-decay", type=float, default=1e-4)
    parser.add_argument("--target-calibration-fraction", type=float, default=0.30)
    parser.add_argument("--target-calibration-min", type=int, default=24)
    parser.add_argument("--direct-epochs", type=int, default=500)
    parser.add_argument("--ordinal-epochs", type=int, default=500)
    parser.add_argument("--head-epochs", type=int, default=450)
    parser.add_argument("--full-epochs", type=int, default=3000)
    parser.add_argument("--target-only-epochs", type=int, default=3500)
    parser.add_argument("--target-calibration-weight", type=float, default=16.0)
    parser.add_argument("--latent-mmd-weight", type=float, default=0.0)
    parser.add_argument("--latent-l2-weight", type=float, default=1e-4)
    parser.add_argument("--device", default="auto", help="auto, cpu, cuda, or cuda:N")
    parser.add_argument("--methods", nargs="+", choices=METHOD_ORDER, default=METHOD_ORDER)
    parser.add_argument("--parallel-workers", type=int, default=1)
    parser.add_argument("--clean", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.clean:
        clean_tracked_outputs(args.out_dir)
    args.out_dir.mkdir(parents=True, exist_ok=True)
    torch.set_num_threads(1)

    budgets = budget_specs(args)
    tables, feature_cols, coverage = mv24.load_official_view_tables(args)
    write_feature_contract(args.out_dir, coverage, args)

    all_rows: list[dict[str, Any]] = []
    bootstrap_store: dict[tuple[str, str, str, str, str], list[float]] = defaultdict(list)
    if int(args.parallel_workers) > 1:
        all_rows, bootstrap_store = run_all_directions_parallel(tables, feature_cols, budgets, args)
    else:
        for source_dataset, target_dataset in mv24.TRANSFER_DIRECTIONS:
            rows, store = run_direction(source_dataset, target_dataset, tables, feature_cols, budgets, args)
            all_rows.extend(rows)
            for key, values in store.items():
                bootstrap_store[key].extend(values)

    metrics = pd.DataFrame(all_rows).sort_values(["transfer_id", "target_calibration_count", "method_rank", "split_index"]).reset_index(drop=True)
    metrics.to_csv(args.out_dir / "label_budget_curve_by_split.csv", index=False)
    summary = summarize_by_method(metrics)
    summary.to_csv(args.out_dir / "label_budget_curve_summary.csv", index=False)
    target_delta, ma_delta = paired_delta_summaries(metrics)
    target_delta.to_csv(args.out_dir / "target_only_delta_summary.csv", index=False)
    ma_delta.to_csv(args.out_dir / "measurement_aware_pairwise_delta_summary.csv", index=False)
    bootstrap_summary = summarize_bootstrap_store(bootstrap_store, metrics)
    bootstrap_summary.to_csv(args.out_dir / "participant_bootstrap_delta_summary.csv", index=False)

    label_budget_table = write_label_budget_curve_table(
        summary,
        args.out_dir / "label_budget_curve_table.csv",
        args.out_dir / "label_budget_curve_table.md",
    )
    target_delta_table = write_delta_table(
        target_delta,
        args.out_dir / "target_only_delta_table.csv",
        args.out_dir / "target_only_delta_table.md",
        family="target_only",
    )
    ma_delta_table = write_delta_table(
        ma_delta,
        args.out_dir / "measurement_aware_pairwise_delta_table.csv",
        args.out_dir / "measurement_aware_pairwise_delta_table.md",
        family="measurement_aware",
    )
    calibration_table = write_calibration_metric_table(
        summary,
        args.out_dir / "calibration_metric_table.csv",
        args.out_dir / "calibration_metric_table.md",
    )

    run_summary = {
        "run_id": "P5_MV28_target_label_budget_uncertainty",
        "generated_at": utc_now(),
        "git_commit": git_commit(),
        "status": "complete",
        "device": str(device_from_args(args)),
        "official_view_id": mv24.official_view().view_id,
        "directions": [f"{source}_to_{target}_phq_shared" for source, target in mv24.TRANSFER_DIRECTIONS],
        "methods": list(args.methods),
        "budget_ids": [spec.budget_id for spec in budgets],
        "target_budgets": [int(value) for value in args.target_budgets],
        "include_mv24_default_budget": bool(args.include_mv24_default_budget),
        "split_count": int(args.split_count),
        "participant_bootstrap_draws": int(args.participant_bootstrap_draws),
        "parallel_workers": int(args.parallel_workers),
        "primary_uncertainty_unit": "subject-level repeated calibration/evaluation splits",
        "participant_bootstrap_policy": "paired bootstrap over evaluation subjects, summarized only as aggregate delta intervals",
        "primary_question": "whether source-plus-target calibrated adaptation beats target-only training under matched labeled target budgets",
        "co_primary_metrics": ["target_macro_item_mae", "target_total_mae", "total_calibration_in_the_large_abs", "total_calibration_slope_abs_error"],
        "legacy_metric_relabel": "MV24 target_calibration_mae is reported here as target_binned_item_calibration_mae",
        "best_rows": best_rows(summary),
        "label_budget_table_rows": int(len(label_budget_table)),
        "target_only_delta_table_rows": int(len(target_delta_table)),
        "measurement_aware_delta_table_rows": int(len(ma_delta_table)),
        "calibration_table_rows": int(len(calibration_table)),
        "bootstrap_summary_rows": int(len(bootstrap_summary)),
        "interpretation_handle": interpretation_from_deltas(target_delta, ma_delta),
        "aggregate_outputs_only": True,
    }
    (args.out_dir / "run_summary.json").write_text(json.dumps(run_summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    write_report(args.out_dir, run_summary)
    hygiene = artifact_hygiene(args.out_dir)
    (args.out_dir / "artifact_hygiene_audit.json").write_text(json.dumps(hygiene, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if not hygiene["artifact_hygiene_passed"]:
        raise RuntimeError(f"artifact hygiene failed: {hygiene['violations']}")


if __name__ == "__main__":
    main()
