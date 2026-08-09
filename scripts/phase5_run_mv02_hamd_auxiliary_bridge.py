#!/usr/bin/env python3
"""Run P5_MV02 PDCH-only HAMD-17 auxiliary bridge validation.

This is a bounded Phase 5 minimal-validation row. It uses current manifest
HAMD-17 labels and cached frozen subject-level text/audio features, trains only
shallow Ridge heads, evaluates PDCH subject-level 5-fold CV, and reports CMDC
only as a small 25-subject sanity subset. It does not scan raw clinical text or
media, fine-tune encoders, or write model weights or learned embeddings.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import re
import shutil
import sys
from collections import Counter
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
from sklearn.linear_model import Ridge
from sklearn.model_selection import KFold, StratifiedKFold
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler


SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from phase2_metrics import bootstrap_ci, regression_metrics, safe_float
from phase5_run_mv01_phq_bridge import natural_key


WORKTREE_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT_DIR = WORKTREE_ROOT / "analysis" / "phase5_minimal_validation" / "p5_mv02_hamd_auxiliary_bridge"
DEFAULT_MANIFEST_DIR = WORKTREE_ROOT / "datasets" / "manifests"
DEFAULT_PHASE2_ROOT = WORKTREE_ROOT / "analysis" / "phase2_baselines"

SEEDS = [0, 1, 2, 3, 4]
FOLD_COUNT = 5
BOOTSTRAP_RESAMPLES = 200
RIDGE_ALPHA_GRID = [0.1, 1.0, 10.0, 100.0, 1000.0]
HAMD_KEYS = [f"HAMD{i:02d}" for i in range(1, 18)]
HAMD_CODE_9 = 9.0
TOTAL_MIN = 0.0
TOTAL_MAX = 52.0

# HAMD item 9 is a non-score code in the official PDCH evaluation, not a
# severity level. Per-item heads train/evaluate only scored labels.
MISSING_ITEM_CODES = {HAMD_CODE_9}

HAMD_CONSTRUCT_MAP = {
    "C01": ["HAMD01"],
    "C02": ["HAMD07"],
    "C03": ["HAMD04", "HAMD05", "HAMD06"],
    "C04": ["HAMD07", "HAMD13"],
    "C05": ["HAMD12", "HAMD16"],
    "C06": ["HAMD02"],
    "C07": ["HAMD08"],
    "C08": ["HAMD08", "HAMD09"],
    "C09": ["HAMD03"],
    "C10": ["HAMD10", "HAMD11"],
    "C11": ["HAMD11", "HAMD12", "HAMD13", "HAMD14", "HAMD15"],
    "C12": ["HAMD07"],
    "C13": ["HAMD17"],
}


@dataclass(frozen=True)
class FeatureSpec:
    feature_space: str
    dataset: str
    relative_path: str


FEATURE_SPECS = [
    FeatureSpec("text_bge", "pdch", "cmdc_pdch_text_encoder_mlp/pdch_bge_subject_features.csv"),
    FeatureSpec("audio_wavlm", "pdch", "pdch_audio_wavlm/pdch_wavlm_subject_features.csv"),
    FeatureSpec("audio_egemaps", "pdch", "cmdc_pdch_audio_egemaps/pdch_egemaps_subject_features.csv"),
    FeatureSpec("text_bge", "cmdc", "cmdc_pdch_text_encoder_mlp/cmdc_bge_subject_features.csv"),
    FeatureSpec("audio_wavlm", "cmdc", "cmdc_audio_frozen_encoders/cmdc_wavlm_subject_features.csv"),
    FeatureSpec("audio_egemaps", "cmdc", "cmdc_pdch_audio_egemaps/cmdc_egemaps_subject_features.csv"),
]


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def format_value(value: Any, digits: int = 3) -> str:
    numeric = safe_float(value)
    if numeric is None:
        return "NA"
    return f"{numeric:.{digits}f}"


def read_csv(path: Path, **kwargs: Any) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(path)
    return pd.read_csv(path, **kwargs)


def bool_series(series: pd.Series) -> pd.Series:
    if pd.api.types.is_bool_dtype(series):
        return series.fillna(False)
    return series.astype(str).str.strip().str.lower().isin({"true", "1", "yes", "y"})


def parse_item_values(value: Any) -> dict[str, float]:
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return {}
    text = str(value).strip()
    if not text or text in {"nan", "NaN", "None", "null"}:
        return {}
    try:
        obj = json.loads(text)
    except json.JSONDecodeError:
        return {}
    if not isinstance(obj, dict):
        return {}
    parsed: dict[str, float] = {}
    for key, raw_value in obj.items():
        try:
            numeric = float(raw_value)
        except (TypeError, ValueError):
            continue
        if math.isfinite(numeric):
            parsed[str(key)] = numeric
    return parsed


def severity_bin(total: float) -> str:
    if total <= 7:
        return "normal"
    if total <= 17:
        return "mild"
    if total <= 24:
        return "moderate"
    return "severe"


def load_hamd_labels(manifest_dir: Path, dataset: str) -> pd.DataFrame:
    path = manifest_dir / f"{dataset}_subjects.csv"
    manifest = read_csv(path)
    required = {"subject_id", "file_valid", "hamd17_total", "hamd17_items"}
    missing = required - set(manifest.columns)
    if missing:
        raise ValueError(f"{dataset} manifest missing columns: {', '.join(sorted(missing))}")
    manifest = manifest[bool_series(manifest["file_valid"])].copy()
    manifest["subject_id"] = manifest["subject_id"].astype(str)

    rows: list[dict[str, Any]] = []
    for subject_id, group in manifest.groupby("subject_id", sort=True):
        totals = sorted(
            {
                float(value)
                for value in pd.to_numeric(group["hamd17_total"], errors="coerce").dropna().tolist()
            }
        )
        item_payloads = [parse_item_values(value) for value in group["hamd17_items"].tolist()]
        full_payloads = [payload for payload in item_payloads if all(key in payload for key in HAMD_KEYS)]
        vectors = sorted(
            {
                json.dumps({key: payload[key] for key in HAMD_KEYS}, sort_keys=True)
                for payload in full_payloads
            }
        )
        if len(totals) != 1 or not full_payloads or len(vectors) != 1:
            continue
        payload = full_payloads[0]
        scored_item_sum = float(sum(0.0 if payload[key] in MISSING_ITEM_CODES else payload[key] for key in HAMD_KEYS))
        row: dict[str, Any] = {
            "dataset": dataset,
            "subject_id": str(subject_id),
            "subject_key": f"{dataset}::{subject_id}",
            "hamd17_total": float(totals[0]),
            "scored_item_sum": scored_item_sum,
            "raw_item_sum": float(sum(payload[key] for key in HAMD_KEYS)),
            "severity_bin": severity_bin(float(totals[0])),
            "contains_hamd_code_9": any(payload[key] in MISSING_ITEM_CODES for key in HAMD_KEYS),
        }
        for key in HAMD_KEYS:
            value = float(payload[key])
            row[f"{key}_raw"] = value
            row[key] = np.nan if value in MISSING_ITEM_CODES else value
        rows.append(row)

    labels = pd.DataFrame(rows).sort_values("subject_id", key=lambda s: s.map(lambda x: tuple(natural_key(x)))).reset_index(drop=True)
    if labels.empty:
        raise ValueError(f"no usable HAMD labels for {dataset}")
    if labels["subject_id"].duplicated().any():
        raise ValueError(f"duplicate HAMD subject labels for {dataset}")
    return labels


def model_input_columns(data: pd.DataFrame, feature_space: str) -> list[str]:
    if feature_space == "text_bge":
        return [column for column in data.columns if column.startswith("bge_")]
    if feature_space == "audio_wavlm":
        return [column for column in data.columns if column.startswith("wavlm_")]
    if feature_space == "audio_egemaps":
        excluded = {"dataset_id", "subject_id", "audio_segment_count"}
        return [
            column
            for column in data.columns
            if column not in excluded and pd.api.types.is_numeric_dtype(data[column])
        ]
    raise ValueError(f"unknown feature space: {feature_space}")


def load_feature_tables(phase2_root: Path) -> tuple[dict[tuple[str, str], pd.DataFrame], pd.DataFrame]:
    tables: dict[tuple[str, str], pd.DataFrame] = {}
    availability_rows: list[dict[str, Any]] = []
    for spec in FEATURE_SPECS:
        path = phase2_root / spec.relative_path
        data = read_csv(path)
        if "subject_id" not in data.columns:
            raise ValueError(f"feature cache missing subject_id: {spec.relative_path}")
        path_like = [column for column in data.columns if "path" in column.lower()]
        if path_like:
            raise ValueError(f"feature cache contains path-like columns: {spec.relative_path}")
        data["subject_id"] = data["subject_id"].astype(str)
        input_cols = model_input_columns(data, spec.feature_space)
        if not input_cols:
            raise ValueError(f"feature cache has no model input columns: {spec.relative_path}")
        renamed = data[["subject_id", *input_cols]].copy()
        renamed = renamed.rename(columns={column: f"{spec.feature_space}__{column}" for column in input_cols})
        tables[(spec.dataset, spec.feature_space)] = renamed
        availability_rows.append(
            {
                "dataset": spec.dataset,
                "feature_space": spec.feature_space,
                "relative_path": spec.relative_path,
                "exists": True,
                "feature_subjects": int(renamed["subject_id"].nunique()),
                "model_input_columns": int(len(input_cols)),
            }
        )
    return tables, pd.DataFrame(availability_rows)


def build_model_table(
    labels: pd.DataFrame,
    feature_tables: dict[tuple[str, str], pd.DataFrame],
    dataset: str,
) -> tuple[pd.DataFrame, dict[str, list[str]], pd.DataFrame]:
    table = labels.copy()
    joined_rows: list[dict[str, Any]] = []
    feature_cols_by_space: dict[str, list[str]] = {}
    for feature_space in ["text_bge", "audio_wavlm", "audio_egemaps"]:
        feature = feature_tables[(dataset, feature_space)]
        before = int(table["subject_id"].nunique())
        table = table.merge(feature, on="subject_id", how="inner", validate="one_to_one")
        after = int(table["subject_id"].nunique())
        cols = [column for column in feature.columns if column != "subject_id"]
        feature_cols_by_space[feature_space] = cols
        joined_rows.append(
            {
                "dataset": dataset,
                "feature_space": feature_space,
                "label_subjects_before_join": before,
                "joined_subjects_after_join": after,
                "feature_columns": len(cols),
            }
        )
    feature_cols_by_space["early_fusion_all"] = (
        feature_cols_by_space["text_bge"]
        + feature_cols_by_space["audio_wavlm"]
        + feature_cols_by_space["audio_egemaps"]
    )
    joined_rows.append(
        {
            "dataset": dataset,
            "feature_space": "early_fusion_all",
            "label_subjects_before_join": int(labels["subject_id"].nunique()),
            "joined_subjects_after_join": int(table["subject_id"].nunique()),
            "feature_columns": len(feature_cols_by_space["early_fusion_all"]),
        }
    )
    if table.empty:
        raise ValueError(f"{dataset} labels/features have no joined subjects")
    table = table.sort_values("subject_id", key=lambda s: s.map(lambda x: tuple(natural_key(x)))).reset_index(drop=True)
    return table, feature_cols_by_space, pd.DataFrame(joined_rows)


def ridge_pipeline(alpha: float) -> Pipeline:
    return Pipeline(
        [
            ("imputer", SimpleImputer(strategy="median")),
            ("scaler", StandardScaler()),
            ("ridge", Ridge(alpha=float(alpha))),
        ]
    )


def choose_alpha(x: np.ndarray, y: np.ndarray, seed: int) -> float:
    y_arr = np.asarray(y, dtype=float)
    if y_arr.ndim == 2:
        mask = np.all(np.isfinite(y_arr), axis=1)
    else:
        mask = np.isfinite(y_arr)
    x_arr = np.asarray(x, dtype=float)[mask]
    y_arr = y_arr[mask]
    if x_arr.shape[0] < 12:
        return 100.0
    n_splits = min(5, max(2, x_arr.shape[0] // 12))
    splitter = KFold(n_splits=n_splits, shuffle=True, random_state=seed)
    best_alpha = RIDGE_ALPHA_GRID[0]
    best_mae = float("inf")
    for alpha in RIDGE_ALPHA_GRID:
        scores: list[float] = []
        for train_idx, dev_idx in splitter.split(x_arr):
            model = ridge_pipeline(alpha)
            model.fit(x_arr[train_idx], y_arr[train_idx])
            pred = np.asarray(model.predict(x_arr[dev_idx]), dtype=float)
            scores.append(float(np.nanmean(np.abs(pred - y_arr[dev_idx]))))
        score = float(np.mean(scores))
        if score < best_mae:
            best_mae = score
            best_alpha = alpha
    return float(best_alpha)


def item_bounds(train: pd.DataFrame) -> dict[str, tuple[float, float]]:
    bounds: dict[str, tuple[float, float]] = {}
    for key in HAMD_KEYS:
        values = pd.to_numeric(train[key], errors="coerce").dropna()
        if values.empty:
            bounds[key] = (0.0, 4.0)
        else:
            bounds[key] = (0.0, max(1.0, float(values.max())))
    return bounds


def fit_direct_total(
    train: pd.DataFrame,
    eval_frame: pd.DataFrame,
    feature_cols: list[str],
    seed: int,
) -> tuple[np.ndarray, float]:
    x_train = train[feature_cols].to_numpy(dtype=float)
    y_train = train["hamd17_total"].to_numpy(dtype=float)
    alpha = choose_alpha(x_train, y_train, seed)
    model = ridge_pipeline(alpha)
    model.fit(x_train, y_train)
    pred = np.clip(np.asarray(model.predict(eval_frame[feature_cols].to_numpy(dtype=float)), dtype=float).reshape(-1), TOTAL_MIN, TOTAL_MAX)
    return pred, alpha


def fit_itemwise(
    train: pd.DataFrame,
    eval_frame: pd.DataFrame,
    feature_cols: list[str],
    seed: int,
) -> tuple[pd.DataFrame, dict[str, float]]:
    x_eval = eval_frame[feature_cols].to_numpy(dtype=float)
    bounds = item_bounds(train)
    predictions: dict[str, np.ndarray] = {}
    selected_alpha: dict[str, float] = {}
    complete_item_rows = train.dropna(subset=HAMD_KEYS)
    if len(complete_item_rows) >= 12:
        shared_alpha = choose_alpha(
            complete_item_rows[feature_cols].to_numpy(dtype=float),
            complete_item_rows[HAMD_KEYS].to_numpy(dtype=float),
            seed,
        )
    else:
        shared_alpha = choose_alpha(
            train[feature_cols].to_numpy(dtype=float),
            train["hamd17_total"].to_numpy(dtype=float),
            seed,
        )
    for key in HAMD_KEYS:
        usable = train[train[key].notna()].copy()
        if usable.empty:
            value = 0.0
            predictions[key] = np.repeat(value, len(eval_frame))
            selected_alpha[key] = math.nan
            continue
        x_train = usable[feature_cols].to_numpy(dtype=float)
        y_train = usable[key].to_numpy(dtype=float)
        alpha = shared_alpha
        model = ridge_pipeline(alpha)
        model.fit(x_train, y_train)
        lo, hi = bounds[key]
        predictions[key] = np.clip(np.asarray(model.predict(x_eval), dtype=float).reshape(-1), lo, hi)
        selected_alpha[key] = alpha
    return pd.DataFrame(predictions, index=eval_frame.index), selected_alpha


def predict_item_means(train: pd.DataFrame, eval_frame: pd.DataFrame) -> pd.DataFrame:
    predictions: dict[str, np.ndarray] = {}
    for key in HAMD_KEYS:
        values = pd.to_numeric(train[key], errors="coerce").dropna()
        mean = float(values.mean()) if not values.empty else 0.0
        lo, hi = item_bounds(train)[key]
        predictions[key] = np.repeat(float(np.clip(mean, lo, hi)), len(eval_frame))
    return pd.DataFrame(predictions, index=eval_frame.index)


def construct_values(item_frame: pd.DataFrame) -> pd.DataFrame:
    rows: dict[str, pd.Series] = {}
    for construct_id, keys in HAMD_CONSTRUCT_MAP.items():
        rows[construct_id] = item_frame[keys].mean(axis=1, skipna=True)
    return pd.DataFrame(rows, index=item_frame.index)


def total_from_item_predictions(item_predictions: pd.DataFrame) -> np.ndarray:
    return np.clip(item_predictions[HAMD_KEYS].sum(axis=1).to_numpy(dtype=float), TOTAL_MIN, TOTAL_MAX)


def prediction_rows_for_total(
    eval_frame: pd.DataFrame,
    y_pred: np.ndarray,
    seed: int,
    fold_id: str,
    eval_scope: str,
    feature_space: str,
    model: str,
    target_family: str,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for idx, (_, row) in enumerate(eval_frame.iterrows()):
        rows.append(
            {
                "run_id": "P5_MV02_hamd17_auxiliary_bridge",
                "dataset": str(row["dataset"]),
                "eval_scope": eval_scope,
                "feature_space": feature_space,
                "model": model,
                "seed": int(seed),
                "fold_id": fold_id,
                "task_type": "severity_regression",
                "target_family": target_family,
                "target_id": "HAMD17_total",
                "subject_id": str(row["subject_id"]),
                "y_true": float(row["hamd17_total"]),
                "y_pred": float(y_pred[idx]),
                "severity_bin": str(row["severity_bin"]),
            }
        )
    return rows


def prediction_rows_for_items(
    eval_frame: pd.DataFrame,
    item_predictions: pd.DataFrame,
    seed: int,
    fold_id: str,
    eval_scope: str,
    feature_space: str,
    model: str,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    true_items = eval_frame[HAMD_KEYS].reset_index(drop=True)
    pred_items = item_predictions[HAMD_KEYS].reset_index(drop=True)
    for row_idx, (_, row) in enumerate(eval_frame.reset_index(drop=True).iterrows()):
        for key in HAMD_KEYS:
            y_true = safe_float(true_items.loc[row_idx, key])
            if y_true is None:
                continue
            pred = float(pred_items.loc[row_idx, key])
            rows.append(
                {
                    "run_id": "P5_MV02_hamd17_auxiliary_bridge",
                    "dataset": str(row["dataset"]),
                    "eval_scope": eval_scope,
                    "feature_space": feature_space,
                    "model": model,
                    "seed": int(seed),
                    "fold_id": fold_id,
                    "task_type": "item_regression",
                    "target_family": "hamd_item",
                    "target_id": key,
                    "subject_id": str(row["subject_id"]),
                    "y_true": float(y_true),
                    "y_pred": pred,
                    "y_pred_rounded": int(round(float(np.clip(pred, 0.0, 4.0)))),
                    "severity_bin": str(row["severity_bin"]),
                }
            )
    return rows


def prediction_rows_for_constructs(
    eval_frame: pd.DataFrame,
    item_predictions: pd.DataFrame,
    seed: int,
    fold_id: str,
    eval_scope: str,
    feature_space: str,
    model: str,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    true_constructs = construct_values(eval_frame[HAMD_KEYS]).reset_index(drop=True)
    pred_constructs = construct_values(item_predictions[HAMD_KEYS]).reset_index(drop=True)
    for row_idx, (_, row) in enumerate(eval_frame.reset_index(drop=True).iterrows()):
        for construct_id in sorted(HAMD_CONSTRUCT_MAP, key=natural_key):
            y_true = safe_float(true_constructs.loc[row_idx, construct_id])
            if y_true is None:
                continue
            rows.append(
                {
                    "run_id": "P5_MV02_hamd17_auxiliary_bridge",
                    "dataset": str(row["dataset"]),
                    "eval_scope": eval_scope,
                    "feature_space": feature_space,
                    "model": model,
                    "seed": int(seed),
                    "fold_id": fold_id,
                    "task_type": "construct_regression",
                    "target_family": "hamd_construct_proxy",
                    "target_id": construct_id,
                    "subject_id": str(row["subject_id"]),
                    "y_true": float(y_true),
                    "y_pred": float(pred_constructs.loc[row_idx, construct_id]),
                    "severity_bin": str(row["severity_bin"]),
                }
            )
    return rows


def stratified_pdch_folds(table: pd.DataFrame, seed: int) -> list[tuple[np.ndarray, np.ndarray]]:
    y = table["severity_bin"].astype(str).to_numpy()
    counts = Counter(y)
    if min(counts.values()) >= FOLD_COUNT:
        splitter = StratifiedKFold(n_splits=FOLD_COUNT, shuffle=True, random_state=seed)
        return list(splitter.split(np.zeros(len(table)), y))
    splitter = KFold(n_splits=FOLD_COUNT, shuffle=True, random_state=seed)
    return list(splitter.split(np.zeros(len(table))))


def run_pdch_cv(
    pdch_table: pd.DataFrame,
    cmdc_table: pd.DataFrame,
    feature_cols_by_space: dict[str, list[str]],
) -> tuple[pd.DataFrame, pd.DataFrame]:
    prediction_frames: list[pd.DataFrame] = []
    audit_rows: list[dict[str, Any]] = []

    for seed in SEEDS:
        for fold_index, (train_idx, eval_idx) in enumerate(stratified_pdch_folds(pdch_table, seed)):
            train = pdch_table.iloc[train_idx].reset_index(drop=True)
            eval_frame = pdch_table.iloc[eval_idx].reset_index(drop=True)
            fold_id = f"seed{seed}_fold{fold_index}"
            overlap = set(train["subject_id"].astype(str)) & set(eval_frame["subject_id"].astype(str))
            if overlap:
                raise ValueError(f"PDCH fold subject overlap: {sorted(overlap, key=natural_key)[:5]}")

            total_mean = np.repeat(float(train["hamd17_total"].mean()), len(eval_frame))
            mean_item_pred = predict_item_means(train, eval_frame)
            mean_item_total = total_from_item_predictions(mean_item_pred)
            rows = []
            rows.extend(prediction_rows_for_total(eval_frame, total_mean, seed, fold_id, "pdch_cv", "none", "train_mean_total", "hamd_total_direct"))
            rows.extend(prediction_rows_for_total(eval_frame, mean_item_total, seed, fold_id, "pdch_cv", "none", "train_mean_items", "hamd_total_from_items"))
            rows.extend(prediction_rows_for_items(eval_frame, mean_item_pred, seed, fold_id, "pdch_cv", "none", "train_mean_items"))
            rows.extend(prediction_rows_for_constructs(eval_frame, mean_item_pred, seed, fold_id, "pdch_cv", "none", "train_mean_items"))
            prediction_frames.append(pd.DataFrame(rows))
            audit_rows.extend(
                [
                    audit_row(seed, fold_id, "pdch_cv", "none", "train_mean_total", train, eval_frame, None),
                    audit_row(seed, fold_id, "pdch_cv", "none", "train_mean_items", train, eval_frame, None),
                ]
            )

            for feature_space, feature_cols in feature_cols_by_space.items():
                direct_pred, total_alpha = fit_direct_total(train, eval_frame, feature_cols, seed)
                item_pred, item_alphas = fit_itemwise(train, eval_frame, feature_cols, seed)
                item_total = total_from_item_predictions(item_pred)
                direct_model = "direct_total_ridge"
                item_model = "itemwise_ridge"
                rows = []
                rows.extend(
                    prediction_rows_for_total(
                        eval_frame,
                        direct_pred,
                        seed,
                        fold_id,
                        "pdch_cv",
                        feature_space,
                        direct_model,
                        "hamd_total_direct",
                    )
                )
                rows.extend(
                    prediction_rows_for_total(
                        eval_frame,
                        item_total,
                        seed,
                        fold_id,
                        "pdch_cv",
                        feature_space,
                        item_model,
                        "hamd_total_from_items",
                    )
                )
                rows.extend(prediction_rows_for_items(eval_frame, item_pred, seed, fold_id, "pdch_cv", feature_space, item_model))
                rows.extend(
                    prediction_rows_for_constructs(eval_frame, item_pred, seed, fold_id, "pdch_cv", feature_space, item_model)
                )
                prediction_frames.append(pd.DataFrame(rows))
                audit_rows.extend(
                    [
                        audit_row(seed, fold_id, "pdch_cv", feature_space, direct_model, train, eval_frame, total_alpha),
                        audit_row(seed, fold_id, "pdch_cv", feature_space, item_model, train, eval_frame, summarize_item_alphas(item_alphas)),
                    ]
                )

        full_train = pdch_table.reset_index(drop=True)
        cmdc_eval = cmdc_table.reset_index(drop=True)
        total_mean = np.repeat(float(full_train["hamd17_total"].mean()), len(cmdc_eval))
        mean_item_pred = predict_item_means(full_train, cmdc_eval)
        mean_item_total = total_from_item_predictions(mean_item_pred)
        rows = []
        rows.extend(prediction_rows_for_total(cmdc_eval, total_mean, seed, "pdch_full_to_cmdc", "cmdc_sanity", "none", "train_mean_total", "hamd_total_direct"))
        rows.extend(prediction_rows_for_total(cmdc_eval, mean_item_total, seed, "pdch_full_to_cmdc", "cmdc_sanity", "none", "train_mean_items", "hamd_total_from_items"))
        rows.extend(prediction_rows_for_items(cmdc_eval, mean_item_pred, seed, "pdch_full_to_cmdc", "cmdc_sanity", "none", "train_mean_items"))
        rows.extend(prediction_rows_for_constructs(cmdc_eval, mean_item_pred, seed, "pdch_full_to_cmdc", "cmdc_sanity", "none", "train_mean_items"))
        prediction_frames.append(pd.DataFrame(rows))
        audit_rows.extend(
            [
                audit_row(seed, "pdch_full_to_cmdc", "cmdc_sanity", "none", "train_mean_total", full_train, cmdc_eval, None),
                audit_row(seed, "pdch_full_to_cmdc", "cmdc_sanity", "none", "train_mean_items", full_train, cmdc_eval, None),
            ]
        )
        for feature_space, feature_cols in feature_cols_by_space.items():
            direct_pred, total_alpha = fit_direct_total(full_train, cmdc_eval, feature_cols, seed)
            item_pred, item_alphas = fit_itemwise(full_train, cmdc_eval, feature_cols, seed)
            item_total = total_from_item_predictions(item_pred)
            rows = []
            rows.extend(
                prediction_rows_for_total(
                    cmdc_eval,
                    direct_pred,
                    seed,
                    "pdch_full_to_cmdc",
                    "cmdc_sanity",
                    feature_space,
                    "direct_total_ridge",
                    "hamd_total_direct",
                )
            )
            rows.extend(
                prediction_rows_for_total(
                    cmdc_eval,
                    item_total,
                    seed,
                    "pdch_full_to_cmdc",
                    "cmdc_sanity",
                    feature_space,
                    "itemwise_ridge",
                    "hamd_total_from_items",
                )
            )
            rows.extend(prediction_rows_for_items(cmdc_eval, item_pred, seed, "pdch_full_to_cmdc", "cmdc_sanity", feature_space, "itemwise_ridge"))
            rows.extend(
                prediction_rows_for_constructs(
                    cmdc_eval,
                    item_pred,
                    seed,
                    "pdch_full_to_cmdc",
                    "cmdc_sanity",
                    feature_space,
                    "itemwise_ridge",
                )
            )
            prediction_frames.append(pd.DataFrame(rows))
            audit_rows.extend(
                [
                    audit_row(seed, "pdch_full_to_cmdc", "cmdc_sanity", feature_space, "direct_total_ridge", full_train, cmdc_eval, total_alpha),
                    audit_row(seed, "pdch_full_to_cmdc", "cmdc_sanity", feature_space, "itemwise_ridge", full_train, cmdc_eval, summarize_item_alphas(item_alphas)),
                ]
            )

    predictions = pd.concat(prediction_frames, ignore_index=True)
    model_audit = pd.DataFrame(audit_rows)
    return predictions, model_audit


def summarize_item_alphas(item_alphas: dict[str, float]) -> str:
    values = [value for value in item_alphas.values() if safe_float(value) is not None]
    if not values:
        return ""
    counts = Counter(float(value) for value in values)
    return ";".join(f"{alpha:g}:{count}" for alpha, count in sorted(counts.items()))


def audit_row(
    seed: int,
    fold_id: str,
    eval_scope: str,
    feature_space: str,
    model: str,
    train: pd.DataFrame,
    eval_frame: pd.DataFrame,
    selected_alpha: Any,
) -> dict[str, Any]:
    train_subjects = set(train["subject_id"].astype(str))
    eval_subjects = set(eval_frame["subject_id"].astype(str))
    return {
        "seed": int(seed),
        "fold_id": fold_id,
        "eval_scope": eval_scope,
        "feature_space": feature_space,
        "model": model,
        "train_dataset": ";".join(sorted(train["dataset"].astype(str).unique())),
        "eval_dataset": ";".join(sorted(eval_frame["dataset"].astype(str).unique())),
        "train_subjects": int(len(train_subjects)),
        "eval_subjects": int(len(eval_subjects)),
        "subject_overlap_count": int(len(train_subjects & eval_subjects)),
        "selected_alpha": selected_alpha,
        "encoder_finetuning": False,
        "raw_data_scan": False,
        "uses_eval_labels_for_hyperparameters": False,
    }


def rounded_metrics(group: pd.DataFrame) -> dict[str, float | None]:
    true = np.asarray(group["y_true"].tolist(), dtype=float)
    pred = np.asarray(group["y_pred"].tolist(), dtype=float)
    mask = np.isfinite(true) & np.isfinite(pred)
    true = true[mask]
    pred = pred[mask]
    if true.size == 0:
        return {"MAE": None, "Spearman": None, "Rounded Exact Match": None, "Rounded Within 1": None}
    rounded = np.rint(np.clip(pred, 0.0, 4.0))
    return {
        "MAE": safe_float(np.mean(np.abs(pred - true))),
        "Spearman": regression_metrics(true, pred).get("Spearman"),
        "Rounded Exact Match": safe_float(np.mean(rounded == true)),
        "Rounded Within 1": safe_float(np.mean(np.abs(rounded - true) <= 1.0)),
    }


def metric_tables(predictions: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    by_seed_rows: list[dict[str, Any]] = []
    group_cols = ["eval_scope", "dataset", "feature_space", "model", "target_family", "target_id", "seed"]
    for key, group in predictions.groupby(group_cols, sort=False, dropna=False):
        eval_scope, dataset, feature_space, model, target_family, target_id, seed = key
        if target_family in {"hamd_total_direct", "hamd_total_from_items"}:
            metrics = regression_metrics(group["y_true"], group["y_pred"])
            task_type = "severity_regression"
        else:
            metrics = rounded_metrics(group)
            task_type = str(group["task_type"].iloc[0])
        for metric, value in metrics.items():
            ci_low, ci_high = None, None
            # Keep bootstrap bounded: total-score MAE is the inferential anchor
            # for MV02; item/construct rows use five-seed mean/std summaries.
            if target_family in {"hamd_total_direct", "hamd_total_from_items"} and metric == "MAE":
                ci_low, ci_high = bootstrap_ci(
                    group,
                    "severity_regression",
                    "MAE",
                    BOOTSTRAP_RESAMPLES,
                    seed=20260809 + int(seed),
                    unit_column="subject_id",
                )
            by_seed_rows.append(
                {
                    "run_id": "P5_MV02_hamd17_auxiliary_bridge",
                    "eval_scope": eval_scope,
                    "dataset": dataset,
                    "feature_space": feature_space,
                    "model": model,
                    "target_family": target_family,
                    "target_id": target_id,
                    "seed": int(seed),
                    "task_type": task_type,
                    "metric": metric,
                    "value": value,
                    "ci95_low": ci_low,
                    "ci95_high": ci_high,
                    "sample_count": int(len(group)),
                    "subject_count": int(group["subject_id"].nunique()),
                }
            )

    by_seed = pd.DataFrame(by_seed_rows)
    summary_rows: list[dict[str, Any]] = []
    for key, group in by_seed.groupby(
        ["run_id", "eval_scope", "dataset", "feature_space", "model", "target_family", "target_id", "task_type", "metric"],
        sort=False,
        dropna=False,
    ):
        values = [safe_float(value) for value in group["value"]]
        values = [float(value) for value in values if value is not None]
        if not values:
            continue
        ci_low_values = [safe_float(value) for value in group["ci95_low"]]
        ci_high_values = [safe_float(value) for value in group["ci95_high"]]
        sample_counts = [safe_float(value) for value in group["sample_count"]]
        subject_counts = [safe_float(value) for value in group["subject_count"]]
        summary_rows.append(
            {
                **dict(
                    zip(
                        [
                            "run_id",
                            "eval_scope",
                            "dataset",
                            "feature_space",
                            "model",
                            "target_family",
                            "target_id",
                            "task_type",
                            "metric",
                        ],
                        key,
                        strict=True,
                    )
                ),
                "mean": safe_float(np.mean(values)),
                "std": safe_float(np.std(values, ddof=0)),
                "ci95_low": safe_float(np.mean([value for value in ci_low_values if value is not None]))
                if any(value is not None for value in ci_low_values)
                else None,
                "ci95_high": safe_float(np.mean([value for value in ci_high_values if value is not None]))
                if any(value is not None for value in ci_high_values)
                else None,
                "seed_count": int(len(values)),
                "sample_count_mean": safe_float(np.mean([value for value in sample_counts if value is not None])),
                "subject_count_mean": safe_float(np.mean([value for value in subject_counts if value is not None])),
            }
        )
    return by_seed, pd.DataFrame(summary_rows)


def macro_summaries(metric_summary: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    selected = metric_summary[metric_summary["metric"] == "MAE"].copy()
    for key, group in selected.groupby(["eval_scope", "dataset", "feature_space", "model", "target_family"], sort=False):
        eval_scope, dataset, feature_space, model, target_family = key
        if target_family in {"hamd_total_direct", "hamd_total_from_items"}:
            for _, row in group.iterrows():
                rows.append(
                    {
                        "eval_scope": eval_scope,
                        "dataset": dataset,
                        "feature_space": feature_space,
                        "model": model,
                        "summary_target": target_family,
                        "metric": "MAE",
                        "mean": row["mean"],
                        "std": row["std"],
                        "seed_count": row["seed_count"],
                        "target_count": 1,
                    }
                )
        else:
            values = [safe_float(value) for value in group["mean"]]
            values = [float(value) for value in values if value is not None]
            rows.append(
                {
                    "eval_scope": eval_scope,
                    "dataset": dataset,
                    "feature_space": feature_space,
                    "model": model,
                    "summary_target": "macro_hamd_item_mae" if target_family == "hamd_item" else "macro_hamd_construct_proxy_mae",
                    "metric": "MAE",
                    "mean": safe_float(np.mean(values)) if values else None,
                    "std": safe_float(np.std(values, ddof=0)) if values else None,
                    "seed_count": int(group["seed_count"].max()) if not group.empty else 0,
                    "target_count": int(group["target_id"].nunique()),
                }
            )
    return pd.DataFrame(rows)


def build_comparison_summary(macro_summary: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for key, group in macro_summary.groupby(["eval_scope", "dataset", "summary_target"], sort=False):
        eval_scope, dataset, summary_target = key
        values = group.set_index(["feature_space", "model"])["mean"].to_dict()
        mean_total = values.get(("none", "train_mean_total"))
        mean_items = values.get(("none", "train_mean_items"))
        direct_best = min(
            [
                (value, feature_space, model)
                for (feature_space, model), value in values.items()
                if safe_float(value) is not None and model == "direct_total_ridge"
            ],
            default=(None, None, None),
        )
        for _, row in group.iterrows():
            current = safe_float(row["mean"])
            baseline = mean_total if summary_target == "hamd_total_direct" else mean_items
            rows.append(
                {
                    "eval_scope": eval_scope,
                    "dataset": dataset,
                    "summary_target": summary_target,
                    "feature_space": row["feature_space"],
                    "model": row["model"],
                    "mae": current,
                    "delta_vs_train_mean": safe_float(current - baseline) if current is not None and baseline is not None else None,
                    "delta_vs_best_direct_total": safe_float(current - direct_best[0])
                    if current is not None and direct_best[0] is not None
                    else None,
                    "best_direct_total_feature": direct_best[1],
                }
            )
    return pd.DataFrame(rows)


def label_feature_audit(
    pdch_labels: pd.DataFrame,
    cmdc_labels: pd.DataFrame,
    availability: pd.DataFrame,
    joined: pd.DataFrame,
) -> pd.DataFrame:
    rows = []
    for dataset, labels in [("pdch", pdch_labels), ("cmdc", cmdc_labels)]:
        rows.append(
            {
                "dataset": dataset,
                "audit_type": "label_coverage",
                "manifest_hamd_subjects": int(labels["subject_id"].nunique()),
                "hamd_code_9_subjects": int(labels["contains_hamd_code_9"].sum()),
                "severity_bin_counts": json.dumps(dict(sorted(Counter(labels["severity_bin"]).items())), sort_keys=True),
                "feature_space": "",
                "feature_subjects": "",
                "joined_subjects": "",
                "feature_columns": "",
            }
        )
    for _, row in availability.iterrows():
        joined_row = joined[(joined["dataset"] == row["dataset"]) & (joined["feature_space"] == row["feature_space"])]
        rows.append(
            {
                "dataset": row["dataset"],
                "audit_type": "feature_availability",
                "manifest_hamd_subjects": "",
                "hamd_code_9_subjects": "",
                "severity_bin_counts": "",
                "feature_space": row["feature_space"],
                "feature_subjects": int(row["feature_subjects"]),
                "joined_subjects": int(joined_row["joined_subjects_after_join"].iloc[0]) if not joined_row.empty else "",
                "feature_columns": int(row["model_input_columns"]),
            }
        )
    return pd.DataFrame(rows)


def best_rows_for_report(macro_summary: pd.DataFrame, eval_scope: str) -> pd.DataFrame:
    selected = macro_summary[
        (macro_summary["eval_scope"] == eval_scope)
        & (macro_summary["summary_target"].isin(["hamd_total_direct", "hamd_total_from_items", "macro_hamd_item_mae"]))
    ].copy()
    return selected.sort_values(["summary_target", "mean", "feature_space", "model"], key=lambda s: s.map(lambda x: tuple(natural_key(x))))


def write_report(
    out_dir: Path,
    run_summary: dict[str, Any],
    macro_summary: pd.DataFrame,
    comparison_summary: pd.DataFrame,
) -> None:
    pdch_rows = best_rows_for_report(macro_summary, "pdch_cv")
    cmdc_rows = best_rows_for_report(macro_summary, "cmdc_sanity")
    verdict = run_summary["verdict"]

    lines = [
        "# P5_MV02 HAMD-17 Auxiliary Bridge",
        "",
        f"Generated: `{run_summary['generated_at']}`",
        "",
        "## Scope",
        "",
        "This row runs the first HAMD-17 auxiliary bridge in PDCH-only mode. It uses manifest HAMD total/item labels and cached frozen BGE, WavLM, and eGeMAPS subject features, trains shallow Ridge heads only, and evaluates PDCH with subject-level 5-fold CV over five seeds. CMDC is reported only as a small 25-subject sanity subset.",
        "",
        "## Label And Feature Contract",
        "",
        f"- PDCH HAMD subjects: `{run_summary['label_contract']['pdch_hamd_subjects']}`.",
        f"- CMDC HAMD sanity subjects: `{run_summary['label_contract']['cmdc_hamd_subjects']}`.",
        f"- PDCH HAMD code-9 subjects: `{run_summary['label_contract']['pdch_hamd_code_9_subjects']}`; code `9` is excluded from item-derived total scoring.",
        f"- PDCH CV subject-overlap violations: `{run_summary['split_audit']['pdch_cv_subject_overlap_violations']}`.",
        f"- Feature spaces: `{', '.join(run_summary['feature_contract']['feature_spaces'])}`.",
        "",
        "## PDCH CV Summary",
        "",
        "| summary target | feature space | model | MAE | seed count | target count |",
        "| --- | --- | --- | ---: | ---: | ---: |",
    ]
    for _, row in pdch_rows.iterrows():
        lines.append(
            f"| {row['summary_target']} | {row['feature_space']} | {row['model']} | {format_value(row['mean'])} | {int(row['seed_count'])} | {int(row['target_count'])} |"
        )
    lines.extend(
        [
            "",
            "## CMDC Sanity Summary",
            "",
            "| summary target | feature space | model | MAE | seed count | target count |",
            "| --- | --- | --- | ---: | ---: | ---: |",
        ]
    )
    for _, row in cmdc_rows.iterrows():
        lines.append(
            f"| {row['summary_target']} | {row['feature_space']} | {row['model']} | {format_value(row['mean'])} | {int(row['seed_count'])} | {int(row['target_count'])} |"
        )
    lines.extend(
        [
            "",
            "## Deltas",
            "",
            "Negative deltas are improvements in MAE. CMDC rows are sanity checks only.",
            "",
            "| eval scope | summary target | feature space | model | delta vs train mean | delta vs best direct total |",
            "| --- | --- | --- | --- | ---: | ---: |",
        ]
    )
    delta_rows = comparison_summary[
        comparison_summary["summary_target"].isin(["hamd_total_direct", "hamd_total_from_items", "macro_hamd_item_mae"])
    ].sort_values(["eval_scope", "summary_target", "feature_space", "model"], key=lambda s: s.map(lambda x: tuple(natural_key(x))))
    for _, row in delta_rows.iterrows():
        lines.append(
            f"| {row['eval_scope']} | {row['summary_target']} | {row['feature_space']} | {row['model']} | {format_value(row['delta_vs_train_mean'])} | {format_value(row['delta_vs_best_direct_total'])} |"
        )
    lines.extend(
        [
            "",
            "## Verdict",
            "",
            f"- Pass-rule status: `{verdict['pass_rule_status']}`.",
            f"- Best PDCH direct-total MAE: `{format_value(verdict['best_pdch_direct_total_mae'])}` from `{verdict['best_pdch_direct_total_feature']}`.",
            f"- Best PDCH item-derived total MAE: `{format_value(verdict['best_pdch_item_total_mae'])}` from `{verdict['best_pdch_item_total_feature']}`.",
            f"- Best PDCH macro item MAE: `{format_value(verdict['best_pdch_macro_item_mae'])}` from `{verdict['best_pdch_macro_item_feature']}`.",
            "",
            run_summary["interpretation"]["short_read"],
            "",
            "## Hygiene",
            "",
            f"- Artifact hygiene passed: `{run_summary['artifact_hygiene_passed']}`.",
            "- Row-level predictions are written as a local-only ignored CSV.",
            "- Raw clinical text, media paths, learned embeddings, model weights, prompts, and responses are not written.",
        ]
    )
    (out_dir / "report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def artifact_hygiene_audit(out_dir: Path) -> dict[str, Any]:
    forbidden_patterns = [
        r"/root/autodl-tmp/datasets/",
        r"/root/",
        r"/autodl-tmp/",
        r"\btext_path\b",
        r"\baudio_path\b",
        r"\bvideo_path\b",
        r"\bgait_path\b",
        r"\.wav\b",
        r"\.WAV\b",
        r"\.mp4\b",
        r"\.avi\b",
        r"raw transcript",
        r"model_weights_written",
    ]
    violations: list[dict[str, Any]] = []
    files_checked = 0
    for path in sorted(out_dir.rglob("*")):
        if not path.is_file():
            continue
        if path.name.endswith("_local_predictions.csv"):
            continue
        if path.suffix.lower() not in {".csv", ".json", ".md", ".txt"}:
            continue
        files_checked += 1
        text = path.read_text(encoding="utf-8", errors="ignore")
        for pattern in forbidden_patterns:
            if re.search(pattern, text, flags=re.IGNORECASE):
                violations.append({"file": str(path.relative_to(out_dir)), "pattern": pattern})
    return {
        "audit_id": "P5_MV02_artifact_hygiene",
        "generated_at": utc_now(),
        "files_checked": files_checked,
        "violation_count": len(violations),
        "violations": violations,
        "artifact_hygiene_passed": len(violations) == 0,
        "local_only_patterns": [
            "analysis/phase5_minimal_validation/**/*predictions*.csv",
            "analysis/phase5_minimal_validation/**/*embeddings*.csv",
            "analysis/phase5_minimal_validation/**/*model*.joblib",
            "analysis/phase5_minimal_validation/**/*model*.pkl",
        ],
    }


def build_verdict(macro_summary: pd.DataFrame) -> tuple[dict[str, Any], str]:
    pdch = macro_summary[macro_summary["eval_scope"] == "pdch_cv"].copy()

    def best(summary_target: str, model: str | None = None) -> pd.Series | None:
        subset = pdch[pdch["summary_target"] == summary_target].copy()
        if model is not None:
            subset = subset[subset["model"] == model]
        subset = subset.dropna(subset=["mean"]).sort_values("mean")
        if subset.empty:
            return None
        return subset.iloc[0]

    best_direct = best("hamd_total_direct", "direct_total_ridge")
    best_item_total = best("hamd_total_from_items", "itemwise_ridge")
    best_item_macro = best("macro_hamd_item_mae", "itemwise_ridge")
    train_total = best("hamd_total_direct", "train_mean_total")
    train_items = best("hamd_total_from_items", "train_mean_items")

    item_total_beats_mean = (
        best_item_total is not None
        and train_items is not None
        and safe_float(best_item_total["mean"]) is not None
        and safe_float(train_items["mean"]) is not None
        and float(best_item_total["mean"]) < float(train_items["mean"])
    )
    direct_beats_mean = (
        best_direct is not None
        and train_total is not None
        and safe_float(best_direct["mean"]) is not None
        and safe_float(train_total["mean"]) is not None
        and float(best_direct["mean"]) < float(train_total["mean"])
    )
    if item_total_beats_mean and direct_beats_mean:
        pass_status = "pass_pdch_only_diagnostic"
        short_read = (
            "MV02 is a useful PDCH-only diagnostic: shallow frozen-feature heads beat train-mean severity baselines and provide item-level HAMD summaries. This supports running a bounded HAMD auxiliary bridge, but it is not yet a cross-dataset shared-symptom claim because CMDC HAMD coverage is only a 25-subject sanity subset."
        )
    elif item_total_beats_mean or direct_beats_mean:
        pass_status = "partial_pdch_only_signal"
        short_read = (
            "MV02 is runnable and partly informative on PDCH, but evidence is mixed across direct-total and item-derived HAMD targets. Treat it as a diagnostic HAMD bridge result, not a positive shared-representation result."
        )
    else:
        pass_status = "blocked_no_pdch_hamd_gain"
        short_read = (
            "MV02 is runnable but negative: shallow frozen-feature HAMD heads do not beat the train-mean severity floor on PDCH. Do not use this row as positive evidence for HAMD auxiliary bridging without a revised feature or model contract."
        )
    verdict = {
        "pass_rule_status": pass_status,
        "best_pdch_direct_total_mae": safe_float(best_direct["mean"]) if best_direct is not None else None,
        "best_pdch_direct_total_feature": str(best_direct["feature_space"]) if best_direct is not None else None,
        "best_pdch_item_total_mae": safe_float(best_item_total["mean"]) if best_item_total is not None else None,
        "best_pdch_item_total_feature": str(best_item_total["feature_space"]) if best_item_total is not None else None,
        "best_pdch_macro_item_mae": safe_float(best_item_macro["mean"]) if best_item_macro is not None else None,
        "best_pdch_macro_item_feature": str(best_item_macro["feature_space"]) if best_item_macro is not None else None,
        "direct_total_beats_train_mean": bool(direct_beats_mean),
        "item_total_beats_train_mean": bool(item_total_beats_mean),
    }
    return verdict, short_read


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--manifest-dir", type=Path, default=DEFAULT_MANIFEST_DIR)
    parser.add_argument("--phase2-root", type=Path, default=DEFAULT_PHASE2_ROOT)
    args = parser.parse_args()

    out_dir = args.out_dir
    if out_dir.exists():
        shutil.rmtree(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    pdch_labels = load_hamd_labels(args.manifest_dir, "pdch")
    cmdc_labels = load_hamd_labels(args.manifest_dir, "cmdc")
    feature_tables, availability = load_feature_tables(args.phase2_root)
    pdch_table, pdch_cols_by_space, pdch_joined = build_model_table(pdch_labels, feature_tables, "pdch")
    cmdc_table, cmdc_cols_by_space, cmdc_joined = build_model_table(cmdc_labels, feature_tables, "cmdc")

    for feature_space in ["text_bge", "audio_wavlm", "audio_egemaps", "early_fusion_all"]:
        if len(pdch_cols_by_space[feature_space]) != len(cmdc_cols_by_space[feature_space]):
            raise ValueError(f"feature column count mismatch for {feature_space}")

    predictions, model_audit = run_pdch_cv(pdch_table, cmdc_table, pdch_cols_by_space)
    metrics_by_seed, metric_summary = metric_tables(predictions)
    macro_summary = macro_summaries(metric_summary)
    comparison_summary = build_comparison_summary(macro_summary)
    verdict, short_read = build_verdict(macro_summary)
    feature_audit = label_feature_audit(
        pdch_labels,
        cmdc_labels,
        availability,
        pd.concat([pdch_joined, cmdc_joined], ignore_index=True),
    )

    metrics_by_seed.to_csv(out_dir / "metrics_by_seed.csv", index=False)
    metric_summary.to_csv(out_dir / "metric_summary.csv", index=False)
    macro_summary.to_csv(out_dir / "macro_summary.csv", index=False)
    comparison_summary.to_csv(out_dir / "comparison_summary.csv", index=False)
    model_audit.to_csv(out_dir / "model_split_audit.csv", index=False)
    feature_audit.to_csv(out_dir / "label_feature_audit.csv", index=False)
    pd.DataFrame(
        [
            {"construct_id": construct_id, "hamd_item_codes": ";".join(keys)}
            for construct_id, keys in sorted(HAMD_CONSTRUCT_MAP.items(), key=lambda item: natural_key(item[0]))
        ]
    ).to_csv(out_dir / "construct_proxy_map.csv", index=False)
    predictions.to_csv(out_dir / "p5_mv02_local_predictions.csv", index=False)

    run_summary: dict[str, Any] = {
        "run_id": "P5_MV02_hamd17_auxiliary_bridge",
        "generated_at": utc_now(),
        "status": "complete",
        "scope": "pdch_only_hamd17_auxiliary_bridge_with_cmdc_sanity",
        "label_contract": {
            "pdch_hamd_subjects": int(pdch_table["subject_id"].nunique()),
            "cmdc_hamd_subjects": int(cmdc_table["subject_id"].nunique()),
            "pdch_hamd_code_9_subjects": int(pdch_table["contains_hamd_code_9"].sum()),
            "hamd_code_9_policy": "exclude_from_item_training_and_total_scoring",
            "primary_total_target": "manifest_hamd17_total",
        },
        "feature_contract": {
            "feature_spaces": ["text_bge", "audio_wavlm", "audio_egemaps", "early_fusion_all"],
            "feature_column_counts": {key: int(len(value)) for key, value in pdch_cols_by_space.items()},
            "encoder_finetuning": False,
            "raw_data_scan": False,
        },
        "model_contract": {
            "models": ["train_mean_total", "train_mean_items", "direct_total_ridge", "itemwise_ridge"],
            "seeds": SEEDS,
            "folds_per_seed": FOLD_COUNT,
            "inner_cv_for_alpha": True,
        },
        "split_audit": {
            "pdch_subject_level_stratified_cv": True,
            "pdch_cv_subject_overlap_violations": int(
                model_audit[model_audit["eval_scope"] == "pdch_cv"]["subject_overlap_count"].sum()
            ),
            "cmdc_sanity_eval_subjects": int(cmdc_table["subject_id"].nunique()),
            "cmdc_used_for_hyperparameters": False,
        },
        "output_policy": {
            "row_level_predictions": "local_only_ignored",
            "learned_embeddings": "not_written",
            "model_weights": "not_written",
            "raw_text": "not_written",
            "media_paths": "not_written",
        },
        "verdict": verdict,
        "interpretation": {"short_read": short_read},
        "artifact_hygiene_passed": False,
        "summary_files": [
            "report.md",
            "run_summary.json",
            "artifact_hygiene_audit.json",
            "metric_summary.csv",
            "metrics_by_seed.csv",
            "macro_summary.csv",
            "comparison_summary.csv",
            "model_split_audit.csv",
            "label_feature_audit.csv",
            "construct_proxy_map.csv",
        ],
        "local_only_files": ["p5_mv02_local_predictions.csv"],
    }

    (out_dir / "run_summary.json").write_text(json.dumps(run_summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    write_report(out_dir, run_summary, macro_summary, comparison_summary)
    hygiene = artifact_hygiene_audit(out_dir)
    run_summary["artifact_hygiene_passed"] = bool(hygiene["artifact_hygiene_passed"])
    (out_dir / "run_summary.json").write_text(json.dumps(run_summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    write_report(out_dir, run_summary, macro_summary, comparison_summary)
    hygiene = artifact_hygiene_audit(out_dir)
    run_summary["artifact_hygiene_passed"] = bool(hygiene["artifact_hygiene_passed"])
    (out_dir / "run_summary.json").write_text(json.dumps(run_summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (out_dir / "artifact_hygiene_audit.json").write_text(json.dumps(hygiene, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    if not hygiene["artifact_hygiene_passed"]:
        raise SystemExit("artifact hygiene violations found; see artifact_hygiene_audit.json")
    print(f"Wrote P5_MV02 HAMD auxiliary bridge artifacts to {out_dir.relative_to(WORKTREE_ROOT)}")


if __name__ == "__main__":
    main()
