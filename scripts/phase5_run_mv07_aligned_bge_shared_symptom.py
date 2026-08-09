#!/usr/bin/env python3
"""Run P5_MV07 aligned-BGE shallow shared-symptom validation.

This is a bounded Phase 5 minimal-validation row, not the full method. It uses
aligned frozen BGE subject features for E-DAIC, CMDC, and PDCH, trains only
shallow Ridge heads, compares against simple floors, and reports
dataset/protocol identity probes. Row-level predictions stay local-only.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import re
import shutil
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable


def normalize_thread_env() -> None:
    value = str(os.environ.get("OMP_NUM_THREADS", "")).strip()
    if not value.isdigit() or int(value) <= 0:
        os.environ["OMP_NUM_THREADS"] = "1"
    os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
    os.environ.setdefault("MKL_NUM_THREADS", "1")


normalize_thread_env()

import numpy as np
import pandas as pd
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression, Ridge
from sklearn.metrics import balanced_accuracy_score
from sklearn.model_selection import KFold, StratifiedKFold
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT_DIR = ROOT / "analysis" / "phase5_minimal_validation" / "p5_mv07_aligned_bge_shared_symptom"
DEFAULT_MANIFEST_DIR = ROOT / "datasets" / "manifests"
DEFAULT_SPLIT_PATH = ROOT / "datasets" / "splits" / "phase2_subject_splits.csv"
DEFAULT_PHASE2_ROOT = ROOT / "analysis" / "phase2_baselines"

SEEDS = [0, 1, 2, 3, 4]
CONSTRUCTS = [f"C{idx:02d}" for idx in range(1, 9)]
RIDGE_ALPHA_GRID = [0.1, 1.0, 10.0, 100.0, 1000.0]
FEATURE_PREFIX = "bge_"
BOOTSTRAP_RESAMPLES = 200

EDAIC_ITEM_MAP = {
    "C01": "PHQ_8Depressed",
    "C02": "PHQ_8NoInterest",
    "C03": "PHQ_8Sleep",
    "C04": "PHQ_8Tired",
    "C05": "PHQ_8Appetite",
    "C06": "PHQ_8Failure",
    "C07": "PHQ_8Concentrating",
    "C08": "PHQ_8Moving",
}

CMDC_ITEM_MAP = {
    "C01": "PHQ-2",
    "C02": "PHQ-1",
    "C03": "PHQ-3",
    "C04": "PHQ-4",
    "C05": "PHQ-5",
    "C06": "PHQ-6",
    "C07": "PHQ-7",
    "C08": "PHQ-8",
}

HAMD_KEYS = [f"HAMD{i:02d}" for i in range(1, 18)]
HAMD_CODE_9 = 9.0
HAMD_PROXY_MAP = {
    "C01": ["HAMD01"],
    "C02": ["HAMD07"],
    "C03": ["HAMD04", "HAMD05", "HAMD06"],
    "C04": ["HAMD07", "HAMD13"],
    "C05": ["HAMD12", "HAMD16"],
    "C06": ["HAMD02"],
    "C07": ["HAMD08"],
    "C08": ["HAMD08", "HAMD09"],
}

TRACKED_FILES = {
    "report.md",
    "run_summary.json",
    "artifact_hygiene_audit.json",
    "metric_summary.csv",
    "metrics_by_seed.csv",
    "comparison_summary.csv",
    "identity_probe_by_seed.csv",
    "identity_probe_summary.csv",
    "model_split_audit.csv",
    "label_feature_audit.csv",
    "construct_target_map.csv",
}


@dataclass(frozen=True)
class BgeFeatureSpec:
    dataset: str
    relative_path: str


FEATURE_SPECS = {
    "edaic": BgeFeatureSpec("edaic", "edaic_text_bge/edaic_bge_subject_features.csv"),
    "cmdc": BgeFeatureSpec("cmdc", "cmdc_pdch_text_encoder_mlp/cmdc_bge_subject_features.csv"),
    "pdch": BgeFeatureSpec("pdch", "cmdc_pdch_text_encoder_mlp/pdch_bge_subject_features.csv"),
}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def natural_key(value: Any) -> list[Any]:
    return [int(part) if part.isdigit() else part for part in re.split(r"(\d+)", str(value))]


def safe_float(value: Any) -> float | None:
    try:
        out = float(value)
    except (TypeError, ValueError):
        return None
    return out if math.isfinite(out) else None


def rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT))
    except ValueError:
        return path.name


def read_json_dict(value: Any) -> dict[str, Any]:
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return {}
    text = str(value).strip()
    if not text or text.lower() in {"nan", "none", "null", "<na>"}:
        return {}
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return {}
    return data if isinstance(data, dict) else {}


def bool_series(series: pd.Series) -> pd.Series:
    if pd.api.types.is_bool_dtype(series):
        return series.fillna(False)
    return series.astype(str).str.strip().str.lower().isin({"true", "1", "yes", "y"})


def spearman(values_true: Iterable[Any], values_pred: Iterable[Any]) -> float | None:
    true = np.asarray(list(values_true), dtype=np.float64)
    pred = np.asarray(list(values_pred), dtype=np.float64)
    mask = np.isfinite(true) & np.isfinite(pred)
    true = true[mask]
    pred = pred[mask]
    if true.size < 3 or len(np.unique(true)) < 2 or len(np.unique(pred)) < 2:
        return None
    true_rank = pd.Series(true).rank(method="average").to_numpy(dtype=np.float64)
    pred_rank = pd.Series(pred).rank(method="average").to_numpy(dtype=np.float64)
    return safe_float(np.corrcoef(true_rank, pred_rank)[0, 1])


def load_bge_features(phase2_root: Path) -> tuple[dict[str, pd.DataFrame], list[str], pd.DataFrame]:
    tables: dict[str, pd.DataFrame] = {}
    column_sets: list[set[str]] = []
    rows: list[dict[str, Any]] = []
    for dataset, spec in FEATURE_SPECS.items():
        path = phase2_root / spec.relative_path
        if not path.exists():
            raise FileNotFoundError(f"BGE feature cache missing for {dataset}: {path}")
        frame = pd.read_csv(path)
        if "subject_id" not in frame.columns:
            raise ValueError(f"{dataset} BGE cache missing subject_id")
        path_like = [column for column in frame.columns if "path" in column.lower()]
        if path_like:
            raise ValueError(f"{dataset} BGE cache has path-like columns: {path_like[:5]}")
        frame["subject_id"] = frame["subject_id"].astype(str)
        bge_cols = [
            column
            for column in frame.columns
            if column.startswith(FEATURE_PREFIX) and pd.api.types.is_numeric_dtype(frame[column])
        ]
        if not bge_cols:
            raise ValueError(f"{dataset} BGE cache has no numeric {FEATURE_PREFIX} columns")
        bge_cols = sorted(bge_cols, key=natural_key)
        tables[dataset] = frame[["subject_id", *bge_cols]].copy()
        column_sets.append(set(bge_cols))
        rows.append(
            {
                "dataset": dataset,
                "feature_family": "text_bge",
                "feature_ref": spec.relative_path,
                "feature_subjects": int(frame["subject_id"].nunique()),
                "model_input_columns": int(len(bge_cols)),
                "path_like_columns": ";".join(path_like),
            }
        )
    common = sorted(set.intersection(*column_sets), key=natural_key)
    if not common:
        raise ValueError("no common BGE columns across E-DAIC, CMDC, and PDCH")
    return {dataset: table[["subject_id", *common]].copy() for dataset, table in tables.items()}, common, pd.DataFrame(rows)


def load_phq_labels(manifest_dir: Path, dataset: str) -> pd.DataFrame:
    if dataset == "edaic":
        manifest_name = "edaic_subjects.csv"
        item_col = "phq8_items"
        total_col = "phq8_total"
        item_map = EDAIC_ITEM_MAP
        usecols = ["subject_id", "file_valid", "official_split", item_col, total_col]
    elif dataset == "cmdc":
        manifest_name = "cmdc_subjects.csv"
        item_col = "phq9_items"
        total_col = "phq9_total"
        item_map = CMDC_ITEM_MAP
        usecols = ["subject_id", "file_valid", item_col, total_col]
    else:
        raise ValueError(dataset)
    manifest = pd.read_csv(manifest_dir / manifest_name, usecols=usecols)
    manifest = manifest[bool_series(manifest["file_valid"])].copy()
    manifest["subject_id"] = manifest["subject_id"].astype(str)
    if dataset == "edaic":
        manifest = manifest[manifest["official_split"].isin(["train", "dev"])].copy()

    records: list[dict[str, Any]] = []
    for subject_id, group in manifest.groupby("subject_id", sort=False):
        row = group.iloc[0]
        payload = read_json_dict(row[item_col])
        total = safe_float(row[total_col])
        record: dict[str, Any] = {
            "dataset": dataset,
            "target_family": "phq_core",
            "subject_id": str(subject_id),
            "subject_key": f"{dataset}::{subject_id}",
            "target_total": total,
        }
        if dataset == "edaic":
            record["official_split"] = str(row["official_split"])
        for construct_id, item_code in item_map.items():
            record[construct_id] = safe_float(payload.get(item_code))
            record[f"{construct_id}_item_code"] = item_code
        records.append(record)
    labels = pd.DataFrame(records)
    labels = labels.dropna(subset=[*CONSTRUCTS, "target_total"]).copy()
    return labels.sort_values("subject_id", key=lambda s: s.map(lambda x: tuple(natural_key(x)))).reset_index(drop=True)


def load_pdch_hamd_proxy_labels(manifest_dir: Path) -> pd.DataFrame:
    manifest = pd.read_csv(
        manifest_dir / "pdch_subjects.csv",
        usecols=["subject_id", "file_valid", "hamd17_total", "hamd17_items"],
    )
    manifest = manifest[bool_series(manifest["file_valid"])].copy()
    manifest["subject_id"] = manifest["subject_id"].astype(str)
    rows: list[dict[str, Any]] = []
    for subject_id, group in manifest.groupby("subject_id", sort=False):
        totals = sorted(
            {
                float(value)
                for value in pd.to_numeric(group["hamd17_total"], errors="coerce").dropna().tolist()
            }
        )
        payloads = [read_json_dict(value) for value in group["hamd17_items"].tolist()]
        full_payloads = [payload for payload in payloads if all(key in payload for key in HAMD_KEYS)]
        vectors = sorted(
            {
                json.dumps({key: payload[key] for key in HAMD_KEYS}, sort_keys=True)
                for payload in full_payloads
            }
        )
        if len(totals) != 1 or not full_payloads or len(vectors) != 1:
            continue
        payload = full_payloads[0]
        record: dict[str, Any] = {
            "dataset": "pdch",
            "target_family": "hamd_proxy",
            "subject_id": str(subject_id),
            "subject_key": f"pdch::{subject_id}",
            "target_total": float(totals[0]),
        }
        for construct_id, hamd_items in HAMD_PROXY_MAP.items():
            values: list[float] = []
            for item in hamd_items:
                value = safe_float(payload.get(item))
                if value is None or value == HAMD_CODE_9:
                    continue
                values.append(float(value))
            record[construct_id] = float(np.mean(values)) if values else np.nan
            record[f"{construct_id}_item_code"] = "+".join(hamd_items)
        rows.append(record)
    labels = pd.DataFrame(rows).dropna(subset=CONSTRUCTS).copy()
    return labels.sort_values("subject_id", key=lambda s: s.map(lambda x: tuple(natural_key(x)))).reset_index(drop=True)


def join_labels_features(labels: pd.DataFrame, feature: pd.DataFrame) -> pd.DataFrame:
    merged = labels.merge(feature, on="subject_id", how="inner", validate="one_to_one")
    if merged.empty:
        raise ValueError(f"{labels['dataset'].iloc[0]} labels/features have no joined subjects")
    return merged.sort_values("subject_id", key=lambda s: s.map(lambda x: tuple(natural_key(x)))).reset_index(drop=True)


def load_subject_folds(split_path: Path, dataset: str, protocol_id: str, target: str) -> dict[int, dict[str, set[str]]]:
    splits = pd.read_csv(split_path)
    selected = splits[
        (splits["dataset"].astype(str) == dataset)
        & (splits["protocol_id"].astype(str) == protocol_id)
        & (splits["target"].astype(str) == target)
    ].copy()
    if selected.empty:
        raise ValueError(f"no split rows for {dataset}/{protocol_id}/{target}")
    folds: dict[int, dict[str, set[str]]] = {}
    for idx, fold_name in enumerate(sorted(selected["fold"].astype(str).unique(), key=natural_key)):
        fold = selected[selected["fold"].astype(str) == fold_name]
        train = set(fold.loc[fold["role"].astype(str) == "train", "subject_id"].astype(str))
        validation = set(fold.loc[fold["role"].astype(str) == "validation", "subject_id"].astype(str))
        overlap = train & validation
        if overlap:
            raise ValueError(f"{dataset}/{protocol_id}/{fold_name} train/validation overlap")
        if not train or not validation:
            raise ValueError(f"{dataset}/{protocol_id}/{fold_name} has empty train or validation")
        folds[idx] = {"train": train, "validation": validation, "fold_name": {fold_name}}
    return folds


def ridge_pipeline(alpha: float) -> Pipeline:
    return Pipeline(
        [
            ("imputer", SimpleImputer(strategy="median")),
            ("scaler", StandardScaler()),
            ("ridge", Ridge(alpha=float(alpha))),
        ]
    )


def choose_alpha(x: np.ndarray, y: np.ndarray, seed: int) -> float:
    y_arr = np.asarray(y, dtype=np.float64)
    mask = np.all(np.isfinite(y_arr), axis=1) if y_arr.ndim == 2 else np.isfinite(y_arr)
    x_arr = np.asarray(x, dtype=np.float64)[mask]
    y_arr = y_arr[mask]
    if x_arr.shape[0] < 12:
        return 100.0
    n_splits = min(5, max(2, x_arr.shape[0] // 10))
    splitter = KFold(n_splits=n_splits, shuffle=True, random_state=seed)
    best_alpha = RIDGE_ALPHA_GRID[0]
    best_mae = float("inf")
    for alpha in RIDGE_ALPHA_GRID:
        scores: list[float] = []
        for train_idx, dev_idx in splitter.split(x_arr):
            model = ridge_pipeline(alpha)
            model.fit(x_arr[train_idx], y_arr[train_idx])
            pred = np.asarray(model.predict(x_arr[dev_idx]), dtype=float)
            scores.append(float(np.mean(np.abs(pred - y_arr[dev_idx]))))
        score = float(np.mean(scores))
        if score < best_mae:
            best_alpha = float(alpha)
            best_mae = score
    return best_alpha


def target_bounds(train: pd.DataFrame, target_family: str) -> tuple[np.ndarray, np.ndarray]:
    lower = np.zeros(len(CONSTRUCTS), dtype=np.float64)
    if target_family == "phq_core":
        upper = np.repeat(3.0, len(CONSTRUCTS))
    elif target_family == "hamd_proxy":
        upper = np.repeat(4.0, len(CONSTRUCTS))
    else:
        upper = train[CONSTRUCTS].max(axis=0).to_numpy(dtype=np.float64)
    return lower, upper


def clip_matrix(values: np.ndarray, lower: np.ndarray, upper: np.ndarray) -> np.ndarray:
    return np.minimum(np.maximum(np.asarray(values, dtype=np.float64), lower.reshape(1, -1)), upper.reshape(1, -1))


def wide_predictions(
    eval_frame: pd.DataFrame,
    predictions: np.ndarray,
    *,
    run_id: str,
    protocol: str,
    model: str,
    seed: int,
    fold: str,
    target_family: str,
) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for row_idx, (_, subject) in enumerate(eval_frame.iterrows()):
        for col_idx, construct_id in enumerate(CONSTRUCTS):
            rows.append(
                {
                    "run_id": run_id,
                    "protocol": protocol,
                    "model": model,
                    "seed": int(seed),
                    "fold": fold,
                    "target_family": target_family,
                    "eval_dataset": subject["dataset"],
                    "subject_key": subject["subject_key"],
                    "subject_id": subject["subject_id"],
                    "construct_id": construct_id,
                    "item_code": subject[f"{construct_id}_item_code"],
                    "y_true": float(subject[construct_id]),
                    "y_pred": float(predictions[row_idx, col_idx]),
                    "y_pred_rounded": int(np.rint(predictions[row_idx, col_idx])),
                }
            )
    return pd.DataFrame(rows)


def fit_predict_itemwise(
    train: pd.DataFrame,
    eval_frame: pd.DataFrame,
    feature_cols: list[str],
    seed: int,
    *,
    protocol: str,
    fold: str,
    target_family: str,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    x_train = train[feature_cols].to_numpy(dtype=float)
    y_train = train[CONSTRUCTS].to_numpy(dtype=float)
    x_eval = eval_frame[feature_cols].to_numpy(dtype=float)
    alpha = choose_alpha(x_train, y_train, seed)
    model = ridge_pipeline(alpha)
    model.fit(x_train, y_train)
    low, high = target_bounds(train, target_family)
    pred = clip_matrix(model.predict(x_eval), low, high)
    return wide_predictions(
        eval_frame,
        pred,
        run_id="P5_MV07_aligned_bge_shared_symptom",
        protocol=protocol,
        model="bge_itemwise_ridge",
        seed=seed,
        fold=fold,
        target_family=target_family,
    ), {"selected_alpha": alpha}


def predict_train_mean(
    train: pd.DataFrame,
    eval_frame: pd.DataFrame,
    *,
    protocol: str,
    seed: int,
    fold: str,
    target_family: str,
) -> pd.DataFrame:
    low, high = target_bounds(train, target_family)
    means = np.clip(train[CONSTRUCTS].mean(axis=0).to_numpy(dtype=float), low, high)
    pred = np.tile(means.reshape(1, -1), (len(eval_frame), 1))
    return wide_predictions(
        eval_frame,
        pred,
        run_id="P5_MV07_aligned_bge_shared_symptom",
        protocol=protocol,
        model="train_mean",
        seed=seed,
        fold=fold,
        target_family=target_family,
    )


def fit_predict_total_alloc(
    train: pd.DataFrame,
    eval_frame: pd.DataFrame,
    feature_cols: list[str],
    seed: int,
    *,
    protocol: str,
    fold: str,
    target_family: str,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    x_train = train[feature_cols].to_numpy(dtype=float)
    y_total = train[CONSTRUCTS].sum(axis=1).to_numpy(dtype=float)
    x_eval = eval_frame[feature_cols].to_numpy(dtype=float)
    alpha = choose_alpha(x_train, y_total.reshape(-1, 1), seed)
    model = ridge_pipeline(alpha)
    model.fit(x_train, y_total)
    total_pred = np.asarray(model.predict(x_eval), dtype=float).reshape(-1)
    construct_means = train[CONSTRUCTS].mean(axis=0).to_numpy(dtype=float)
    denom = float(np.sum(construct_means))
    proportions = np.repeat(1.0 / len(CONSTRUCTS), len(CONSTRUCTS)) if denom <= 0 else construct_means / denom
    pred = total_pred.reshape(-1, 1) * proportions.reshape(1, -1)
    low, high = target_bounds(train, target_family)
    pred = clip_matrix(pred, low, high)
    return wide_predictions(
        eval_frame,
        pred,
        run_id="P5_MV07_aligned_bge_shared_symptom",
        protocol=protocol,
        model="total_alloc_ridge",
        seed=seed,
        fold=fold,
        target_family=target_family,
    ), {"selected_alpha": alpha}


def metric_rows_for_predictions(predictions: pd.DataFrame) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    group_cols = ["seed", "protocol", "model", "target_family"]
    for group_key, group in predictions.groupby(group_cols, sort=False, dropna=False):
        seed, protocol, model, target_family = group_key
        for dataset_slice in ["pooled", *sorted(group["eval_dataset"].unique())]:
            data = group if dataset_slice == "pooled" else group[group["eval_dataset"] == dataset_slice]
            if data.empty:
                continue
            construct_maes: list[float] = []
            construct_rmses: list[float] = []
            construct_spearman: list[float] = []
            for construct_id in CONSTRUCTS:
                subset = data[data["construct_id"] == construct_id]
                y_true = subset["y_true"].to_numpy(dtype=float)
                y_pred = subset["y_pred"].to_numpy(dtype=float)
                err = y_pred - y_true
                mae = safe_float(np.mean(np.abs(err))) if y_true.size else None
                rmse = safe_float(np.sqrt(np.mean(err**2))) if y_true.size else None
                sp = spearman(y_true, y_pred)
                rounded_within_1 = (
                    safe_float(np.mean(np.abs(np.rint(y_pred) - y_true) <= 1.0)) if y_true.size else None
                )
                if mae is not None:
                    construct_maes.append(mae)
                if rmse is not None:
                    construct_rmses.append(rmse)
                if sp is not None:
                    construct_spearman.append(sp)
                for metric, value in [
                    ("MAE", mae),
                    ("RMSE", rmse),
                    ("Spearman", sp),
                    ("Rounded Within 1", rounded_within_1),
                ]:
                    rows.append(
                        {
                            "seed": int(seed),
                            "protocol": protocol,
                            "model": model,
                            "target_family": target_family,
                            "dataset_slice": dataset_slice,
                            "construct_id": construct_id,
                            "metric": metric,
                            "value": value,
                            "subject_count": int(subset["subject_key"].nunique()),
                        }
                    )
            rows.extend(
                [
                    {
                        "seed": int(seed),
                        "protocol": protocol,
                        "model": model,
                        "target_family": target_family,
                        "dataset_slice": dataset_slice,
                        "construct_id": "macro",
                        "metric": "Macro Construct MAE",
                        "value": safe_float(np.mean(construct_maes)) if construct_maes else None,
                        "subject_count": int(data["subject_key"].nunique()),
                    },
                    {
                        "seed": int(seed),
                        "protocol": protocol,
                        "model": model,
                        "target_family": target_family,
                        "dataset_slice": dataset_slice,
                        "construct_id": "macro",
                        "metric": "Macro Construct RMSE",
                        "value": safe_float(np.mean(construct_rmses)) if construct_rmses else None,
                        "subject_count": int(data["subject_key"].nunique()),
                    },
                    {
                        "seed": int(seed),
                        "protocol": protocol,
                        "model": model,
                        "target_family": target_family,
                        "dataset_slice": dataset_slice,
                        "construct_id": "macro",
                        "metric": "Macro Construct Spearman",
                        "value": safe_float(np.mean(construct_spearman)) if construct_spearman else None,
                        "subject_count": int(data["subject_key"].nunique()),
                    },
                ]
            )
    return rows


def bootstrap_macro_mae(frame: pd.DataFrame, resamples: int, seed: int) -> tuple[float | None, float | None]:
    if frame.empty or resamples <= 0:
        return None, None
    rng = np.random.default_rng(seed)
    units = np.asarray(sorted(frame["subject_key"].astype(str).unique()))
    grouped = {unit: frame.index[frame["subject_key"].astype(str) == unit].to_numpy() for unit in units}
    values: list[float] = []
    for _ in range(resamples):
        sampled_units = rng.choice(units, size=len(units), replace=True)
        sampled_idx = np.concatenate([grouped[unit] for unit in sampled_units])
        sample = frame.loc[sampled_idx]
        construct_values = []
        for construct in CONSTRUCTS:
            subset = sample[sample["construct_id"] == construct]
            if subset.empty:
                continue
            construct_values.append(float(np.mean(np.abs(subset["y_pred"] - subset["y_true"]))))
        if construct_values:
            values.append(float(np.mean(construct_values)))
    if not values:
        return None, None
    return safe_float(np.percentile(values, 2.5)), safe_float(np.percentile(values, 97.5))


def summarize_metrics(metrics_by_seed: pd.DataFrame, predictions: pd.DataFrame) -> pd.DataFrame:
    grouped = metrics_by_seed.groupby(["protocol", "model", "target_family", "dataset_slice", "construct_id", "metric"])
    summary = grouped.agg(
        mean=("value", "mean"),
        std=("value", "std"),
        seed_count=("seed", "nunique"),
        subject_count_mean=("subject_count", "mean"),
    ).reset_index()
    summary["std"] = summary["std"].fillna(0.0)
    summary["ci95_low"] = summary["mean"] - 1.96 * summary["std"] / np.sqrt(summary["seed_count"].clip(lower=1))
    summary["ci95_high"] = summary["mean"] + 1.96 * summary["std"] / np.sqrt(summary["seed_count"].clip(lower=1))

    boot_rows: list[dict[str, Any]] = []
    macro = summary[(summary["construct_id"] == "macro") & (summary["metric"] == "Macro Construct MAE")].copy()
    for _, row in macro.iterrows():
        subset = predictions[
            (predictions["protocol"] == row["protocol"])
            & (predictions["model"] == row["model"])
            & (predictions["target_family"] == row["target_family"])
        ]
        if row["dataset_slice"] != "pooled":
            subset = subset[subset["eval_dataset"] == row["dataset_slice"]]
        low, high = bootstrap_macro_mae(subset, BOOTSTRAP_RESAMPLES, seed=20260809)
        boot_rows.append(
            {
                "protocol": row["protocol"],
                "model": row["model"],
                "target_family": row["target_family"],
                "dataset_slice": row["dataset_slice"],
                "construct_id": row["construct_id"],
                "metric": row["metric"],
                "bootstrap_ci95_low": low,
                "bootstrap_ci95_high": high,
            }
        )
    if boot_rows:
        summary = summary.merge(pd.DataFrame(boot_rows), how="left")
    else:
        summary["bootstrap_ci95_low"] = np.nan
        summary["bootstrap_ci95_high"] = np.nan
    return summary


def build_comparison_summary(metric_summary: pd.DataFrame) -> pd.DataFrame:
    macro = metric_summary[
        (metric_summary["construct_id"] == "macro")
        & (metric_summary["metric"] == "Macro Construct MAE")
        & (metric_summary["dataset_slice"] != "pooled")
    ].copy()
    rows: list[dict[str, Any]] = []
    for (protocol, target_family, dataset_slice), group in macro.groupby(
        ["protocol", "target_family", "dataset_slice"], sort=False
    ):
        values = group.set_index("model")["mean"].to_dict()
        train_mean = values.get("train_mean")
        total_alloc = values.get("total_alloc_ridge")
        for model, value in values.items():
            rows.append(
                {
                    "protocol": protocol,
                    "target_family": target_family,
                    "dataset_slice": dataset_slice,
                    "model": model,
                    "macro_mae": value,
                    "delta_vs_train_mean": safe_float(value - train_mean) if train_mean is not None else None,
                    "delta_vs_total_alloc_ridge": safe_float(value - total_alloc) if total_alloc is not None else None,
                }
            )
    return pd.DataFrame(rows)


def run_identity_probe(features_by_dataset: dict[str, pd.DataFrame], feature_cols: list[str]) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    frames = []
    for dataset, frame in features_by_dataset.items():
        data = frame[["subject_id", *feature_cols]].copy()
        data["dataset"] = dataset
        frames.append(data)
    table = pd.concat(frames, ignore_index=True)
    x = table[feature_cols].to_numpy(dtype=float)
    y_labels = sorted(table["dataset"].unique())
    y = table["dataset"].map({label: idx for idx, label in enumerate(y_labels)}).to_numpy(dtype=int)
    n_splits = min(5, min(np.bincount(y)))
    for seed in SEEDS:
        splitter = StratifiedKFold(n_splits=n_splits, shuffle=True, random_state=seed)
        scores: list[float] = []
        for train_idx, eval_idx in splitter.split(x, y):
            model = Pipeline(
                [
                    ("imputer", SimpleImputer(strategy="median")),
                    ("scaler", StandardScaler()),
                    (
                        "classifier",
                        LogisticRegression(
                            C=1.0,
                            class_weight="balanced",
                            max_iter=2000,
                            random_state=seed,
                        ),
                    ),
                ]
            )
            model.fit(x[train_idx], y[train_idx])
            pred = model.predict(x[eval_idx])
            scores.append(float(balanced_accuracy_score(y[eval_idx], pred)))
        rows.append(
            {
                "seed": seed,
                "probe_id": "feature_identity_bge_edaic_cmdc_pdch",
                "metric": "Balanced Accuracy",
                "value": safe_float(np.mean(scores)),
                "sample_count": int(len(table)),
                "dataset_count": int(len(y_labels)),
            }
        )
    return pd.DataFrame(rows)


def run_prediction_identity_probe(predictions: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    source = predictions[
        (predictions["protocol"] == "pooled_shared_phq")
        & (predictions["model"] == "bge_itemwise_ridge")
        & (predictions["target_family"] == "phq_core")
    ].copy()
    for seed, seed_rows in source.groupby("seed", sort=True):
        wide = seed_rows.pivot_table(
            index=["subject_key", "eval_dataset"],
            columns="construct_id",
            values="y_pred",
            aggfunc="mean",
        ).reset_index()
        if not set(CONSTRUCTS).issubset(wide.columns):
            continue
        x = wide[CONSTRUCTS].to_numpy(dtype=float)
        y = (wide["eval_dataset"].astype(str) == "cmdc").astype(int).to_numpy()
        if min(np.bincount(y)) < 3:
            continue
        n_splits = min(5, min(np.bincount(y)))
        splitter = StratifiedKFold(n_splits=n_splits, shuffle=True, random_state=int(seed))
        scores: list[float] = []
        for train_idx, eval_idx in splitter.split(x, y):
            model = Pipeline(
                [
                    ("imputer", SimpleImputer(strategy="median")),
                    ("scaler", StandardScaler()),
                    (
                        "classifier",
                        LogisticRegression(C=1.0, class_weight="balanced", max_iter=2000, random_state=int(seed)),
                    ),
                ]
            )
            model.fit(x[train_idx], y[train_idx])
            scores.append(float(balanced_accuracy_score(y[eval_idx], model.predict(x[eval_idx]))))
        rows.append(
            {
                "seed": int(seed),
                "probe_id": "prediction_identity_pooled_phq_edaic_cmdc",
                "metric": "Balanced Accuracy",
                "value": safe_float(np.mean(scores)),
                "sample_count": int(len(wide)),
                "dataset_count": 2,
            }
        )
    return pd.DataFrame(rows)


def summarize_identity(probes: pd.DataFrame) -> pd.DataFrame:
    if probes.empty:
        return pd.DataFrame()
    return (
        probes.groupby(["probe_id", "metric"], dropna=False)
        .agg(mean=("value", "mean"), std=("value", "std"), seed_count=("seed", "nunique"), sample_count_mean=("sample_count", "mean"))
        .reset_index()
        .fillna({"std": 0.0})
    )


def run_phq_experiment(table: pd.DataFrame, feature_cols: list[str], cmdc_folds: dict[int, dict[str, set[str]]]) -> tuple[pd.DataFrame, pd.DataFrame]:
    predictions: list[pd.DataFrame] = []
    audit_rows: list[dict[str, Any]] = []
    edaic_train = table[(table["dataset"] == "edaic") & (table["official_split"] == "train")].copy()
    edaic_dev = table[(table["dataset"] == "edaic") & (table["official_split"] == "dev")].copy()
    if set(edaic_train["subject_id"]) & set(edaic_dev["subject_id"]):
        raise ValueError("E-DAIC official train/dev overlap")

    for seed in SEEDS:
        fold = cmdc_folds[seed % len(cmdc_folds)]
        fold_name = next(iter(fold["fold_name"]))
        cmdc_train = table[(table["dataset"] == "cmdc") & table["subject_id"].isin(fold["train"])].copy()
        cmdc_val = table[(table["dataset"] == "cmdc") & table["subject_id"].isin(fold["validation"])].copy()
        specs = [
            ("edaic_same_dataset_phq", edaic_train, edaic_dev),
            ("cmdc_subject_cv_phq", cmdc_train, cmdc_val),
            ("cross_edaic_to_cmdc_phq", edaic_train, cmdc_val),
            ("cross_cmdc_to_edaic_phq", cmdc_train, edaic_dev),
            ("pooled_shared_phq", pd.concat([edaic_train, cmdc_train], ignore_index=True), pd.concat([edaic_dev, cmdc_val], ignore_index=True)),
        ]
        for protocol, train, eval_frame in specs:
            train_keys = set(train["subject_key"].astype(str))
            eval_keys = set(eval_frame["subject_key"].astype(str))
            overlap = sorted(train_keys & eval_keys)
            if overlap:
                raise ValueError(f"{protocol}/{seed} train/eval overlap: {overlap[:5]}")
            for frame in [
                predict_train_mean(train, eval_frame, protocol=protocol, seed=seed, fold=fold_name, target_family="phq_core"),
                fit_predict_itemwise(train, eval_frame, feature_cols, seed, protocol=protocol, fold=fold_name, target_family="phq_core")[0],
                fit_predict_total_alloc(train, eval_frame, feature_cols, seed, protocol=protocol, fold=fold_name, target_family="phq_core")[0],
            ]:
                predictions.append(frame)
            audit_rows.append(
                {
                    "seed": seed,
                    "fold": fold_name,
                    "protocol": protocol,
                    "target_family": "phq_core",
                    "train_subjects": int(len(train)),
                    "eval_subjects": int(len(eval_frame)),
                    "train_datasets": ";".join(sorted(train["dataset"].unique())),
                    "eval_datasets": ";".join(sorted(eval_frame["dataset"].unique())),
                    "train_eval_subject_overlap": int(bool(overlap)),
                }
            )
    return pd.concat(predictions, ignore_index=True), pd.DataFrame(audit_rows)


def run_pdch_hamd_sanity(table: pd.DataFrame, feature_cols: list[str], folds: dict[int, dict[str, set[str]]]) -> tuple[pd.DataFrame, pd.DataFrame]:
    predictions: list[pd.DataFrame] = []
    audit_rows: list[dict[str, Any]] = []
    for seed in SEEDS:
        fold = folds[seed % len(folds)]
        fold_name = next(iter(fold["fold_name"]))
        train = table[table["subject_id"].isin(fold["train"])].copy()
        eval_frame = table[table["subject_id"].isin(fold["validation"])].copy()
        train_keys = set(train["subject_key"].astype(str))
        eval_keys = set(eval_frame["subject_key"].astype(str))
        overlap = sorted(train_keys & eval_keys)
        if overlap:
            raise ValueError(f"pdch_hamd_internal_cv/{seed} train/eval overlap: {overlap[:5]}")
        protocol = "pdch_hamd_internal_cv"
        for frame in [
            predict_train_mean(train, eval_frame, protocol=protocol, seed=seed, fold=fold_name, target_family="hamd_proxy"),
            fit_predict_itemwise(train, eval_frame, feature_cols, seed, protocol=protocol, fold=fold_name, target_family="hamd_proxy")[0],
            fit_predict_total_alloc(train, eval_frame, feature_cols, seed, protocol=protocol, fold=fold_name, target_family="hamd_proxy")[0],
        ]:
            predictions.append(frame)
        audit_rows.append(
            {
                "seed": seed,
                "fold": fold_name,
                "protocol": protocol,
                "target_family": "hamd_proxy",
                "train_subjects": int(len(train)),
                "eval_subjects": int(len(eval_frame)),
                "train_datasets": "pdch",
                "eval_datasets": "pdch",
                "train_eval_subject_overlap": int(bool(overlap)),
            }
        )
    return pd.concat(predictions, ignore_index=True), pd.DataFrame(audit_rows)


def build_construct_target_map() -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for construct in CONSTRUCTS:
        rows.extend(
            [
                {"target_family": "phq_core", "dataset": "edaic", "construct_id": construct, "source_items": EDAIC_ITEM_MAP[construct]},
                {"target_family": "phq_core", "dataset": "cmdc", "construct_id": construct, "source_items": CMDC_ITEM_MAP[construct]},
                {"target_family": "hamd_proxy", "dataset": "pdch", "construct_id": construct, "source_items": "+".join(HAMD_PROXY_MAP[construct])},
            ]
        )
    return pd.DataFrame(rows)


def build_label_feature_audit(labels: dict[str, pd.DataFrame], features: dict[str, pd.DataFrame], joined: dict[str, pd.DataFrame], feature_audit: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    feature_lookup = feature_audit.set_index("dataset").to_dict("index")
    for dataset in ["edaic", "cmdc", "pdch"]:
        rows.append(
            {
                "dataset": dataset,
                "target_family": "phq_core" if dataset in {"edaic", "cmdc"} else "hamd_proxy",
                "label_subjects": int(labels[dataset]["subject_id"].nunique()),
                "feature_subjects": int(features[dataset]["subject_id"].nunique()),
                "joined_subjects": int(joined[dataset]["subject_id"].nunique()),
                "model_input_columns": int(feature_lookup[dataset]["model_input_columns"]),
                "feature_ref": feature_lookup[dataset]["feature_ref"],
                "path_like_columns": feature_lookup[dataset]["path_like_columns"],
            }
        )
    return pd.DataFrame(rows)


def verdict_from_outputs(comparison: pd.DataFrame, identity_summary: pd.DataFrame) -> dict[str, Any]:
    def delta(protocol: str, model: str, dataset: str, target_family: str, column: str) -> float | None:
        row = comparison[
            (comparison["protocol"] == protocol)
            & (comparison["model"] == model)
            & (comparison["dataset_slice"] == dataset)
            & (comparison["target_family"] == target_family)
        ]
        if row.empty:
            return None
        return safe_float(row.iloc[0][column])

    pooled_edaic_vs_mean = delta("pooled_shared_phq", "bge_itemwise_ridge", "edaic", "phq_core", "delta_vs_train_mean")
    pooled_cmdc_vs_mean = delta("pooled_shared_phq", "bge_itemwise_ridge", "cmdc", "phq_core", "delta_vs_train_mean")
    pooled_edaic_vs_total = delta("pooled_shared_phq", "bge_itemwise_ridge", "edaic", "phq_core", "delta_vs_total_alloc_ridge")
    pooled_cmdc_vs_total = delta("pooled_shared_phq", "bge_itemwise_ridge", "cmdc", "phq_core", "delta_vs_total_alloc_ridge")
    pdch_vs_mean = delta("pdch_hamd_internal_cv", "bge_itemwise_ridge", "pdch", "hamd_proxy", "delta_vs_train_mean")

    feature_identity = None
    pred_identity = None
    if not identity_summary.empty:
        for probe_id, target in [
            ("feature_identity_bge_edaic_cmdc_pdch", "feature_identity"),
            ("prediction_identity_pooled_phq_edaic_cmdc", "pred_identity"),
        ]:
            row = identity_summary[identity_summary["probe_id"] == probe_id]
            if row.empty:
                continue
            if target == "feature_identity":
                feature_identity = safe_float(row.iloc[0]["mean"])
            else:
                pred_identity = safe_float(row.iloc[0]["mean"])

    phq_beats_mean = all(value is not None and value < 0.0 for value in [pooled_edaic_vs_mean, pooled_cmdc_vs_mean])
    phq_beats_total = all(value is not None and value < 0.0 for value in [pooled_edaic_vs_total, pooled_cmdc_vs_total])
    pdch_sanity = pdch_vs_mean is not None and pdch_vs_mean < 0.0
    identity_blocked = feature_identity is not None and feature_identity > 0.70

    if not phq_beats_mean:
        status = "blocked_no_consistent_phq_gain_bge_contract"
    elif not phq_beats_total:
        status = "blocked_not_better_than_total_allocation_bge_contract"
    elif identity_blocked:
        status = "blocked_dataset_identity_high_bge_contract"
    elif not pdch_sanity:
        status = "blocked_no_pdch_hamd_proxy_sanity_gain"
    else:
        status = "pass_aligned_bge_shared_symptom_candidate"

    return {
        "pass_rule_status": status,
        "pass_rule_met": status.startswith("pass_"),
        "pooled_edaic_delta_vs_train_mean": pooled_edaic_vs_mean,
        "pooled_cmdc_delta_vs_train_mean": pooled_cmdc_vs_mean,
        "pooled_edaic_delta_vs_total_alloc": pooled_edaic_vs_total,
        "pooled_cmdc_delta_vs_total_alloc": pooled_cmdc_vs_total,
        "pdch_hamd_proxy_delta_vs_train_mean": pdch_vs_mean,
        "feature_identity_ba": feature_identity,
        "prediction_identity_ba": pred_identity,
        "short_read": (
            "Aligned BGE MV07 is a shallow validation result. Interpret it through pooled PHQ gains, PDCH HAMD-proxy sanity, and identity probes; readiness alone is not a shared-symptom claim."
        ),
    }


def artifact_hygiene(out_dir: Path) -> dict[str, Any]:
    forbidden_patterns = [
        r"/root/",
        r"/autodl-tmp/",
        r"\btext_path\b",
        r"\baudio_path\b",
        r"\bvideo_path\b",
        r"\bgait_path\b",
        r"\.wav\b",
        r"\.mp4\b",
        r"\.avi\b",
        r"raw text",
        r"source path",
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
        "audit_id": "P5_MV07_aligned_bge_shared_symptom_hygiene",
        "generated_at": utc_now(),
        "files_checked": checked,
        "artifact_hygiene_passed": not violations,
        "violation_count": len(violations),
        "violations": violations,
    }


def format_value(value: Any, digits: int = 3) -> str:
    numeric = safe_float(value)
    return "NA" if numeric is None else f"{numeric:.{digits}f}"


def write_report(out_dir: Path, run_summary: dict[str, Any], comparison: pd.DataFrame, identity: pd.DataFrame) -> None:
    verdict = run_summary["verdict"]
    lines = [
        "# P5_MV07 Aligned-BGE Shared-Symptom Validation",
        "",
        f"Generated: `{run_summary['generated_at']}`",
        "",
        "## Scope",
        "",
        "This row uses frozen aligned BGE subject features and shallow Ridge heads only. It is a minimal validation row, not the full symptom-aligned method.",
        "",
        "## Verdict",
        "",
        f"- Pass-rule status: `{verdict['pass_rule_status']}`.",
        f"- Pooled E-DAIC delta vs train mean: `{format_value(verdict['pooled_edaic_delta_vs_train_mean'])}`.",
        f"- Pooled CMDC delta vs train mean: `{format_value(verdict['pooled_cmdc_delta_vs_train_mean'])}`.",
        f"- Pooled E-DAIC delta vs total allocation: `{format_value(verdict['pooled_edaic_delta_vs_total_alloc'])}`.",
        f"- Pooled CMDC delta vs total allocation: `{format_value(verdict['pooled_cmdc_delta_vs_total_alloc'])}`.",
        f"- PDCH HAMD-proxy delta vs train mean: `{format_value(verdict['pdch_hamd_proxy_delta_vs_train_mean'])}`.",
        f"- Feature identity BA: `{format_value(verdict['feature_identity_ba'])}`.",
        f"- Prediction identity BA: `{format_value(verdict['prediction_identity_ba'])}`.",
        f"- Artifact hygiene passed: `{run_summary['artifact_hygiene_passed']}`.",
        "",
        verdict["short_read"],
        "",
        "## Key Macro MAE Comparisons",
        "",
        "| protocol | target | dataset | model | macro MAE | delta vs train mean | delta vs total allocation |",
        "| --- | --- | --- | --- | ---: | ---: | ---: |",
    ]
    key_protocols = {"pooled_shared_phq", "pdch_hamd_internal_cv"}
    key = comparison[
        comparison["protocol"].isin(key_protocols)
        & comparison["model"].isin(["train_mean", "total_alloc_ridge", "bge_itemwise_ridge"])
    ].copy()
    for _, row in key.sort_values(["protocol", "target_family", "dataset_slice", "model"]).iterrows():
        lines.append(
            f"| {row['protocol']} | {row['target_family']} | {row['dataset_slice']} | {row['model']} | {format_value(row['macro_mae'])} | {format_value(row['delta_vs_train_mean'])} | {format_value(row['delta_vs_total_alloc_ridge'])} |"
        )
    lines.extend(
        [
            "",
            "## Identity Probes",
            "",
            "| probe | metric | mean | std |",
            "| --- | --- | ---: | ---: |",
        ]
    )
    for _, row in identity.iterrows():
        lines.append(f"| {row['probe_id']} | {row['metric']} | {format_value(row['mean'])} | {format_value(row['std'])} |")
    lines.extend(
        [
            "",
            "## Interpretation Boundary",
            "",
            "- A positive same-dataset or pooled metric is not sufficient if dataset identity remains high.",
            "- PDCH HAMD proxy results are internal sanity evidence only, not cross-dataset HAMD generalization.",
            "- Row-level predictions are local-only and are not part of the tracked artifact set.",
        ]
    )
    (out_dir / "report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--manifest-dir", type=Path, default=DEFAULT_MANIFEST_DIR)
    parser.add_argument("--split-path", type=Path, default=DEFAULT_SPLIT_PATH)
    parser.add_argument("--phase2-root", type=Path, default=DEFAULT_PHASE2_ROOT)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    out_dir = args.out_dir
    if out_dir.exists():
        shutil.rmtree(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    features, feature_cols, feature_audit = load_bge_features(args.phase2_root)
    labels = {
        "edaic": load_phq_labels(args.manifest_dir, "edaic"),
        "cmdc": load_phq_labels(args.manifest_dir, "cmdc"),
        "pdch": load_pdch_hamd_proxy_labels(args.manifest_dir),
    }
    joined = {dataset: join_labels_features(labels[dataset], features[dataset]) for dataset in ["edaic", "cmdc", "pdch"]}
    label_feature_audit = build_label_feature_audit(labels, features, joined, feature_audit)
    label_feature_audit.to_csv(out_dir / "label_feature_audit.csv", index=False)
    build_construct_target_map().to_csv(out_dir / "construct_target_map.csv", index=False)

    phq_table = pd.concat([joined["edaic"], joined["cmdc"]], ignore_index=True)
    cmdc_folds = load_subject_folds(args.split_path, "cmdc", "cmdc_phq9_subject_cv", "phq9_total")
    pdch_folds = load_subject_folds(args.split_path, "pdch", "pdch_hamd17_subject_cv_fallback", "hamd17_total")

    phq_predictions, phq_audit = run_phq_experiment(phq_table, feature_cols, cmdc_folds)
    pdch_predictions, pdch_audit = run_pdch_hamd_sanity(joined["pdch"], feature_cols, pdch_folds)
    predictions = pd.concat([phq_predictions, pdch_predictions], ignore_index=True)
    predictions.to_csv(out_dir / "p5_mv07_local_predictions.csv", index=False)
    model_split_audit = pd.concat([phq_audit, pdch_audit], ignore_index=True)
    model_split_audit.to_csv(out_dir / "model_split_audit.csv", index=False)

    metrics_by_seed = pd.DataFrame(metric_rows_for_predictions(predictions))
    metric_summary = summarize_metrics(metrics_by_seed, predictions)
    comparison = build_comparison_summary(metric_summary)
    metrics_by_seed.to_csv(out_dir / "metrics_by_seed.csv", index=False)
    metric_summary.to_csv(out_dir / "metric_summary.csv", index=False)
    comparison.to_csv(out_dir / "comparison_summary.csv", index=False)

    identity_by_seed = pd.concat(
        [run_identity_probe(features, feature_cols), run_prediction_identity_probe(predictions)],
        ignore_index=True,
    )
    identity_summary = summarize_identity(identity_by_seed)
    identity_by_seed.to_csv(out_dir / "identity_probe_by_seed.csv", index=False)
    identity_summary.to_csv(out_dir / "identity_probe_summary.csv", index=False)

    verdict = verdict_from_outputs(comparison, identity_summary)
    run_summary = {
        "run_id": "P5_MV07_aligned_bge_shared_symptom",
        "generated_at": utc_now(),
        "status": "complete",
        "scope": "aligned_bge_shallow_shared_symptom_validation",
        "feature_contract": {
            "feature_family": "text_bge",
            "model_input_columns": int(len(feature_cols)),
            "datasets": ["edaic", "cmdc", "pdch"],
            "encoder_frozen": True,
            "generated_features_local_only": True,
        },
        "data_contract": {
            "edaic_subjects": int(joined["edaic"]["subject_id"].nunique()),
            "cmdc_subjects": int(joined["cmdc"]["subject_id"].nunique()),
            "pdch_subjects": int(joined["pdch"]["subject_id"].nunique()),
            "row_level_predictions_written_local_only": True,
            "raw_text_read": False,
            "raw_text_written": False,
            "source_paths_written": False,
            "encoder_finetuned": False,
        },
        "model_contract": {
            "heads": ["train_mean", "total_alloc_ridge", "bge_itemwise_ridge"],
            "seeds": SEEDS,
            "ridge_alpha_grid": RIDGE_ALPHA_GRID,
            "subject_overlap_violations": int(model_split_audit["train_eval_subject_overlap"].sum()),
        },
        "verdict": verdict,
        "output_policy": {
            "tracked_outputs": sorted(TRACKED_FILES),
            "local_only_outputs": ["p5_mv07_local_predictions.csv"],
        },
        "artifact_hygiene_passed": False,
    }
    (out_dir / "run_summary.json").write_text(
        json.dumps(run_summary, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    write_report(out_dir, run_summary, comparison, identity_summary)
    hygiene = artifact_hygiene(out_dir)
    run_summary["artifact_hygiene_passed"] = bool(hygiene["artifact_hygiene_passed"])
    (out_dir / "run_summary.json").write_text(
        json.dumps(run_summary, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    write_report(out_dir, run_summary, comparison, identity_summary)
    hygiene = artifact_hygiene(out_dir)
    (out_dir / "artifact_hygiene_audit.json").write_text(
        json.dumps(hygiene, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    if not hygiene["artifact_hygiene_passed"]:
        raise SystemExit("artifact hygiene violations found; see artifact_hygiene_audit.json")
    print(
        json.dumps(
            {
                "out_dir": str(out_dir),
                "pass_rule_status": verdict["pass_rule_status"],
                "feature_identity_ba": verdict["feature_identity_ba"],
                "prediction_identity_ba": verdict["prediction_identity_ba"],
            },
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
