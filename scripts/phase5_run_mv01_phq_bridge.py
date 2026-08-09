#!/usr/bin/env python3
"""Run P5_MV01 PHQ core construct bridge minimal validation.

This is a narrow Phase 5 validation row, not a full method. It reads existing
frozen WavLM subject feature caches and manifest item labels, maps PHQ-8 and
PHQ-9 overlap items to C01-C08, evaluates shallow heads, and writes only compact
audited summaries. It does not scan raw audio or fine-tune encoders.
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


WORKTREE_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT_DIR = WORKTREE_ROOT / "analysis" / "phase5_minimal_validation" / "p5_mv01_phq_core_bridge"
DEFAULT_MANIFEST_DIR = WORKTREE_ROOT / "datasets" / "manifests"
DEFAULT_SPLIT_PATH = WORKTREE_ROOT / "datasets" / "splits" / "phase2_subject_splits.csv"
DEFAULT_WORKTREE_PHASE2_ROOT = WORKTREE_ROOT / "analysis" / "phase2_baselines"
DEFAULT_READONLY_PHASE2_ROOT = Path("/root/autodl-tmp/analysis/phase2_baselines")

SEEDS = [0, 1, 2, 3, 4]
RIDGE_ALPHA_GRID = [0.1, 1.0, 10.0, 100.0, 1000.0]
CONSTRUCTS = [f"C{idx:02d}" for idx in range(1, 9)]

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

METADATA_COLUMNS = {
    "audio_segment_count",
    "chunk_count",
    "chunk_count_sum",
    "duration_seconds",
    "duration_seconds_sum",
    "padded_short_chunk_count",
    "split",
}


@dataclass(frozen=True)
class DatasetSpec:
    dataset: str
    manifest_name: str
    feature_rel_path: str
    item_json_column: str
    total_column: str
    item_map: dict[str, str]


DATASET_SPECS = {
    "edaic": DatasetSpec(
        dataset="edaic",
        manifest_name="edaic_subjects.csv",
        feature_rel_path="edaic_audio_frozen_encoders/wavlm_subject_features.csv",
        item_json_column="phq8_items",
        total_column="phq8_total",
        item_map=EDAIC_ITEM_MAP,
    ),
    "cmdc": DatasetSpec(
        dataset="cmdc",
        manifest_name="cmdc_subjects.csv",
        feature_rel_path="cmdc_audio_frozen_encoders/cmdc_wavlm_subject_features.csv",
        item_json_column="phq9_items",
        total_column="phq9_total",
        item_map=CMDC_ITEM_MAP,
    ),
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


def resolve_phase2_root(user_root: Path | None) -> tuple[Path, str]:
    if user_root is not None:
        return user_root, "user_supplied"
    if DEFAULT_WORKTREE_PHASE2_ROOT.exists():
        if (DEFAULT_WORKTREE_PHASE2_ROOT / DATASET_SPECS["edaic"].feature_rel_path).exists() and (
            DEFAULT_WORKTREE_PHASE2_ROOT / DATASET_SPECS["cmdc"].feature_rel_path
        ).exists():
            return DEFAULT_WORKTREE_PHASE2_ROOT, "worktree_phase2_cache"
    return DEFAULT_READONLY_PHASE2_ROOT, "read_only_phase2_cache"


def read_json_dict(value: Any) -> dict[str, Any]:
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return {}
    if isinstance(value, dict):
        return value
    text = str(value).strip()
    if not text:
        return {}
    data = json.loads(text)
    if not isinstance(data, dict):
        raise ValueError("item label JSON must decode to an object")
    return data


def load_feature_cache(path: Path, dataset: str) -> tuple[pd.DataFrame, list[str]]:
    if not path.exists():
        raise FileNotFoundError(f"feature cache missing for {dataset}: {path}")
    frame = pd.read_csv(path)
    if "subject_id" not in frame.columns:
        raise ValueError(f"{dataset} feature cache missing subject_id")
    path_like = [column for column in frame.columns if "path" in column.lower()]
    if path_like:
        raise ValueError(f"{dataset} feature cache contains path-like columns: {path_like[:5]}")
    frame["subject_id"] = frame["subject_id"].astype(str)
    feature_cols = [
        column
        for column in frame.columns
        if column.startswith("wavlm_")
        and column not in METADATA_COLUMNS
        and pd.api.types.is_numeric_dtype(frame[column])
    ]
    if not feature_cols:
        raise ValueError(f"{dataset} feature cache has no numeric wavlm_* columns")
    return frame, sorted(feature_cols, key=natural_key)


def load_subject_labels(manifest_dir: Path, spec: DatasetSpec) -> pd.DataFrame:
    path = manifest_dir / spec.manifest_name
    if not path.exists():
        raise FileNotFoundError(f"manifest missing for {spec.dataset}: {path}")

    usecols = ["subject_id", "file_valid", spec.item_json_column, spec.total_column]
    if spec.dataset == "edaic":
        usecols.append("official_split")
    manifest = pd.read_csv(path, usecols=usecols)
    manifest["subject_id"] = manifest["subject_id"].astype(str)
    rows = manifest[manifest["file_valid"].fillna(False).astype(bool)].copy()
    rows = rows[rows[spec.item_json_column].notna()].copy()
    if spec.dataset == "edaic":
        rows = rows[rows["official_split"].isin(["train", "dev"])].copy()

    records: list[dict[str, Any]] = []
    for subject_id, subject_rows in rows.groupby("subject_id", sort=False):
        first = subject_rows.iloc[0]
        item_values = read_json_dict(first[spec.item_json_column])
        record: dict[str, Any] = {
            "dataset": spec.dataset,
            "subject_id": str(subject_id),
            "total_c01_c08": safe_float(first[spec.total_column]),
        }
        if spec.dataset == "edaic":
            record["official_split"] = str(first["official_split"])
        for construct_id, item_code in spec.item_map.items():
            record[construct_id] = safe_float(item_values.get(item_code))
            record[f"{construct_id}_item_code"] = item_code
        records.append(record)
    out = pd.DataFrame(records)
    required_targets = CONSTRUCTS + ["total_c01_c08"]
    out = out.dropna(subset=required_targets).copy()
    if out.empty:
        raise ValueError(f"no usable subject item labels for {spec.dataset}")
    return out.sort_values("subject_id", key=lambda series: series.map(lambda item: tuple(natural_key(item)))).reset_index(
        drop=True
    )


def load_cmdc_folds(split_path: Path) -> dict[int, dict[str, set[str]]]:
    if not split_path.exists():
        raise FileNotFoundError(f"split layer missing: {split_path}")
    splits = pd.read_csv(split_path)
    selected = splits[
        (splits["dataset"].astype(str) == "cmdc")
        & (splits["protocol_id"].astype(str) == "cmdc_binary_subject_cv")
        & (splits["target"].astype(str) == "binary_label")
    ].copy()
    if selected.empty:
        raise ValueError("no CMDC phase2 subject-CV split rows found")
    folds: dict[int, dict[str, set[str]]] = {}
    for idx, fold_name in enumerate(sorted(selected["fold"].astype(str).unique(), key=natural_key)):
        fold_rows = selected[selected["fold"].astype(str) == fold_name]
        train = set(fold_rows.loc[fold_rows["role"].astype(str) == "train", "subject_id"].astype(str))
        validation = set(fold_rows.loc[fold_rows["role"].astype(str) == "validation", "subject_id"].astype(str))
        if train & validation:
            raise ValueError(f"CMDC {fold_name} train/validation subject overlap")
        if not train or not validation:
            raise ValueError(f"CMDC {fold_name} has empty train or validation split")
        folds[idx] = {"train": train, "validation": validation}
    if len(folds) != 5:
        raise ValueError(f"expected 5 CMDC folds, found {len(folds)}")
    return folds


def build_model_table(manifest_dir: Path, phase2_root: Path) -> tuple[pd.DataFrame, list[str], pd.DataFrame]:
    frames: list[pd.DataFrame] = []
    availability_rows: list[dict[str, Any]] = []
    common_features: list[str] | None = None
    for dataset, spec in DATASET_SPECS.items():
        feature_path = phase2_root / spec.feature_rel_path
        feature_frame, feature_cols = load_feature_cache(feature_path, dataset)
        label_frame = load_subject_labels(manifest_dir, spec)
        merged = label_frame.merge(feature_frame[["subject_id", *feature_cols]], on="subject_id", how="inner")
        if merged.empty:
            raise ValueError(f"{dataset} labels/features have no subject overlap")
        if common_features is None:
            common_features = feature_cols
        else:
            common_features = sorted(set(common_features) & set(feature_cols), key=natural_key)
        availability_rows.append(
            {
                "dataset": dataset,
                "label_subjects": int(label_frame["subject_id"].nunique()),
                "feature_subjects": int(feature_frame["subject_id"].nunique()),
                "joined_subjects": int(merged["subject_id"].nunique()),
                "feature_space": "frozen_wavlm_subject_mean",
                "feature_column_count": int(len(feature_cols)),
                "cache_identity": spec.feature_rel_path,
            }
        )
        frames.append(merged)
    if common_features is None or not common_features:
        raise ValueError("no common WavLM feature columns across E-DAIC and CMDC")
    frames = [frame[[*frame.columns.difference([c for c in frame.columns if c.startswith("wavlm_")]), *common_features]] for frame in frames]
    table = pd.concat(frames, ignore_index=True).copy()
    table["subject_key"] = table["dataset"].astype(str) + "::" + table["subject_id"].astype(str)
    if table["subject_key"].duplicated().any():
        raise ValueError("duplicate dataset::subject rows in modeling table")
    availability = pd.DataFrame(availability_rows)
    availability["common_feature_column_count"] = len(common_features)
    return table, common_features, availability


def make_ridge(alpha: float) -> Pipeline:
    return Pipeline(
        steps=[
            ("imputer", SimpleImputer(strategy="median")),
            ("scaler", StandardScaler()),
            ("ridge", Ridge(alpha=float(alpha))),
        ]
    )


def choose_alpha(x: np.ndarray, y: np.ndarray, seed: int) -> float:
    if x.shape[0] < 12:
        return 100.0
    n_splits = min(5, max(2, x.shape[0] // 8))
    splitter = KFold(n_splits=n_splits, shuffle=True, random_state=seed)
    best_alpha = RIDGE_ALPHA_GRID[0]
    best_mae = float("inf")
    for alpha in RIDGE_ALPHA_GRID:
        fold_scores: list[float] = []
        for train_idx, dev_idx in splitter.split(x):
            model = make_ridge(alpha)
            model.fit(x[train_idx], y[train_idx])
            pred = np.clip(model.predict(x[dev_idx]), 0.0, 3.0)
            fold_scores.append(float(np.mean(np.abs(pred - y[dev_idx]))))
        score = float(np.mean(fold_scores))
        if score < best_mae:
            best_mae = score
            best_alpha = alpha
    return float(best_alpha)


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
    corr = np.corrcoef(true_rank, pred_rank)[0, 1]
    return safe_float(corr)


def ordinal_calibration_mae(y_true: np.ndarray, y_pred: np.ndarray) -> float | None:
    if y_true.size == 0:
        return None
    rounded = np.rint(np.clip(y_pred, 0.0, 3.0)).astype(int)
    total = 0.0
    covered = 0
    for value in range(4):
        mask = rounded == value
        if not np.any(mask):
            continue
        total += int(np.sum(mask)) * abs(float(np.mean(y_true[mask])) - float(np.mean(y_pred[mask])))
        covered += int(np.sum(mask))
    if covered == 0:
        return None
    return safe_float(total / float(covered))


def metric_rows_for_predictions(predictions: pd.DataFrame, model_name: str, protocol: str, seed: int) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for dataset_slice in ["pooled", *sorted(predictions["eval_dataset"].unique())]:
        if dataset_slice == "pooled":
            data = predictions
        else:
            data = predictions[predictions["eval_dataset"] == dataset_slice]
        if data.empty:
            continue
        construct_maes: list[float] = []
        construct_spearman: list[float] = []
        construct_calibration: list[float] = []
        for construct_id in CONSTRUCTS:
            subset = data[data["construct_id"] == construct_id]
            y_true = subset["y_true"].to_numpy(dtype=float)
            y_pred = subset["y_pred"].to_numpy(dtype=float)
            mae = safe_float(np.mean(np.abs(y_pred - y_true))) if y_true.size else None
            sp = spearman(y_true, y_pred)
            cal = ordinal_calibration_mae(y_true, y_pred)
            exact = safe_float(np.mean(np.rint(np.clip(y_pred, 0.0, 3.0)) == y_true)) if y_true.size else None
            within_1 = safe_float(np.mean(np.abs(np.rint(np.clip(y_pred, 0.0, 3.0)) - y_true) <= 1.0)) if y_true.size else None
            if mae is not None:
                construct_maes.append(mae)
            if sp is not None:
                construct_spearman.append(sp)
            if cal is not None:
                construct_calibration.append(cal)
            for metric, value in [
                ("MAE", mae),
                ("Spearman", sp),
                ("Ordinal Calibration MAE", cal),
                ("Rounded Exact Match", exact),
                ("Rounded Within 1", within_1),
            ]:
                rows.append(
                    {
                        "seed": seed,
                        "protocol": protocol,
                        "model": model_name,
                        "dataset_slice": dataset_slice,
                        "construct_id": construct_id,
                        "metric": metric,
                        "value": value,
                        "sample_count": int(subset["subject_key"].nunique()),
                    }
                )
        rows.extend(
            [
                {
                    "seed": seed,
                    "protocol": protocol,
                    "model": model_name,
                    "dataset_slice": dataset_slice,
                    "construct_id": "macro",
                    "metric": "Macro Construct MAE",
                    "value": safe_float(np.mean(construct_maes)) if construct_maes else None,
                    "sample_count": int(data["subject_key"].nunique()),
                },
                {
                    "seed": seed,
                    "protocol": protocol,
                    "model": model_name,
                    "dataset_slice": dataset_slice,
                    "construct_id": "macro",
                    "metric": "Macro Construct Spearman",
                    "value": safe_float(np.mean(construct_spearman)) if construct_spearman else None,
                    "sample_count": int(data["subject_key"].nunique()),
                },
                {
                    "seed": seed,
                    "protocol": protocol,
                    "model": model_name,
                    "dataset_slice": dataset_slice,
                    "construct_id": "macro",
                    "metric": "Macro Ordinal Calibration MAE",
                    "value": safe_float(np.mean(construct_calibration)) if construct_calibration else None,
                    "sample_count": int(data["subject_key"].nunique()),
                },
            ]
        )
    return rows


def fit_predict_constructs(
    train: pd.DataFrame,
    eval_frame: pd.DataFrame,
    feature_cols: list[str],
    seed: int,
    model_name: str,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    x_train = train[feature_cols].to_numpy(dtype=float)
    y_train = train[CONSTRUCTS].to_numpy(dtype=float)
    x_eval = eval_frame[feature_cols].to_numpy(dtype=float)
    alpha = choose_alpha(x_train, y_train, seed)
    model = make_ridge(alpha)
    model.fit(x_train, y_train)
    pred = np.clip(model.predict(x_eval), 0.0, 3.0)
    return wide_predictions(eval_frame, pred, model_name), {"selected_alpha": alpha}


def predict_train_mean(train: pd.DataFrame, eval_frame: pd.DataFrame, model_name: str) -> pd.DataFrame:
    means = train[CONSTRUCTS].mean(axis=0).to_numpy(dtype=float)
    pred = np.tile(means.reshape(1, -1), (len(eval_frame), 1))
    return wide_predictions(eval_frame, np.clip(pred, 0.0, 3.0), model_name)


def fit_predict_total_alloc(
    train: pd.DataFrame,
    eval_frame: pd.DataFrame,
    feature_cols: list[str],
    seed: int,
    model_name: str,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    x_train = train[feature_cols].to_numpy(dtype=float)
    y_total = train[CONSTRUCTS].sum(axis=1).to_numpy(dtype=float)
    x_eval = eval_frame[feature_cols].to_numpy(dtype=float)
    alpha = choose_alpha(x_train, y_total.reshape(-1, 1), seed)
    model = make_ridge(alpha)
    model.fit(x_train, y_total)
    total_pred = np.clip(np.asarray(model.predict(x_eval), dtype=float).reshape(-1), 0.0, 24.0)
    construct_means = train[CONSTRUCTS].mean(axis=0).to_numpy(dtype=float)
    denom = float(np.sum(construct_means))
    if denom <= 0.0:
        proportions = np.repeat(1.0 / len(CONSTRUCTS), len(CONSTRUCTS))
    else:
        proportions = construct_means / denom
    pred = np.clip(total_pred.reshape(-1, 1) * proportions.reshape(1, -1), 0.0, 3.0)
    return wide_predictions(eval_frame, pred, model_name), {"selected_alpha": alpha}


def wide_predictions(eval_frame: pd.DataFrame, pred: np.ndarray, model_name: str) -> pd.DataFrame:
    records: list[dict[str, Any]] = []
    for row_idx, (_, row) in enumerate(eval_frame.iterrows()):
        for col_idx, construct_id in enumerate(CONSTRUCTS):
            records.append(
                {
                    "model": model_name,
                    "eval_dataset": row["dataset"],
                    "subject_key": row["subject_key"],
                    "construct_id": construct_id,
                    "item_code": row[f"{construct_id}_item_code"],
                    "y_true": float(row[construct_id]),
                    "y_pred": float(pred[row_idx, col_idx]),
                    "y_pred_rounded": int(np.rint(np.clip(pred[row_idx, col_idx], 0.0, 3.0))),
                }
            )
    return pd.DataFrame(records)


def run_dataset_identity_probe(table: pd.DataFrame, feature_cols: list[str]) -> pd.DataFrame:
    probe = table[table["dataset"].isin(["edaic", "cmdc"])].copy()
    x = probe[feature_cols].to_numpy(dtype=float)
    y = (probe["dataset"].astype(str) == "cmdc").astype(int).to_numpy()
    rows: list[dict[str, Any]] = []
    for seed in SEEDS:
        splitter = StratifiedKFold(n_splits=5, shuffle=True, random_state=seed)
        scores: list[float] = []
        for train_idx, eval_idx in splitter.split(x, y):
            model = Pipeline(
                steps=[
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
                "probe_id": "frozen_wavlm_edaic_vs_cmdc_identity",
                "metric": "Balanced Accuracy",
                "value": safe_float(np.mean(scores)),
                "sample_count": int(len(probe)),
            }
        )
    return pd.DataFrame(rows)


def summarize_metrics(metrics_by_seed: pd.DataFrame) -> pd.DataFrame:
    grouped = metrics_by_seed.groupby(["protocol", "model", "dataset_slice", "construct_id", "metric"], dropna=False)
    summary = grouped.agg(
        mean=("value", "mean"),
        std=("value", "std"),
        seed_count=("seed", "nunique"),
        sample_count_mean=("sample_count", "mean"),
    ).reset_index()
    summary["std"] = summary["std"].fillna(0.0)
    summary["ci95_low"] = summary["mean"] - 1.96 * summary["std"] / np.sqrt(summary["seed_count"].clip(lower=1))
    summary["ci95_high"] = summary["mean"] + 1.96 * summary["std"] / np.sqrt(summary["seed_count"].clip(lower=1))
    return summary


def build_comparison_summary(metric_summary: pd.DataFrame) -> pd.DataFrame:
    macro = metric_summary[
        (metric_summary["construct_id"] == "macro")
        & (metric_summary["metric"] == "Macro Construct MAE")
        & (metric_summary["dataset_slice"] != "pooled")
    ].copy()
    rows: list[dict[str, Any]] = []
    for protocol, group in macro.groupby("protocol", sort=False):
        values = group.set_index(["model", "dataset_slice"])["mean"].to_dict()
        for dataset_slice in sorted(group["dataset_slice"].unique()):
            baseline = values.get(("train_mean", dataset_slice))
            total_alloc = values.get(("total_alloc_ridge", dataset_slice))
            for model in sorted(group["model"].unique()):
                current = values.get((model, dataset_slice))
                if current is None:
                    continue
                rows.append(
                    {
                        "protocol": protocol,
                        "dataset_slice": dataset_slice,
                        "model": model,
                        "macro_mae": current,
                        "delta_vs_train_mean": safe_float(current - baseline) if baseline is not None else None,
                        "delta_vs_total_alloc_ridge": safe_float(current - total_alloc) if total_alloc is not None else None,
                    }
                )
    return pd.DataFrame(rows)


def run_experiment(table: pd.DataFrame, feature_cols: list[str], cmdc_folds: dict[int, dict[str, set[str]]]) -> tuple[pd.DataFrame, pd.DataFrame]:
    prediction_frames: list[pd.DataFrame] = []
    metric_rows: list[dict[str, Any]] = []
    model_audit_rows: list[dict[str, Any]] = []

    edaic_train_subjects = set(
        table.loc[(table["dataset"] == "edaic") & (table["official_split"] == "train"), "subject_id"].astype(str)
    )
    edaic_dev_subjects = set(
        table.loc[(table["dataset"] == "edaic") & (table["official_split"] == "dev"), "subject_id"].astype(str)
    )
    if edaic_train_subjects & edaic_dev_subjects:
        raise ValueError("E-DAIC train/dev subject overlap detected")

    for seed in SEEDS:
        fold = cmdc_folds[seed % len(cmdc_folds)]
        cmdc_train_subjects = fold["train"]
        cmdc_eval_subjects = fold["validation"]

        selections = {
            "edaic_same_dataset": (
                table[(table["dataset"] == "edaic") & (table["subject_id"].isin(edaic_train_subjects))],
                table[(table["dataset"] == "edaic") & (table["subject_id"].isin(edaic_dev_subjects))],
                "dataset_specific_ridge",
            ),
            "cmdc_subject_cv": (
                table[(table["dataset"] == "cmdc") & (table["subject_id"].isin(cmdc_train_subjects))],
                table[(table["dataset"] == "cmdc") & (table["subject_id"].isin(cmdc_eval_subjects))],
                "dataset_specific_ridge",
            ),
            "cross_edaic_to_cmdc": (
                table[(table["dataset"] == "edaic") & (table["subject_id"].isin(edaic_train_subjects))],
                table[(table["dataset"] == "cmdc") & (table["subject_id"].isin(cmdc_eval_subjects))],
                "cross_dataset_ridge",
            ),
            "cross_cmdc_to_edaic": (
                table[(table["dataset"] == "cmdc") & (table["subject_id"].isin(cmdc_train_subjects))],
                table[(table["dataset"] == "edaic") & (table["subject_id"].isin(edaic_dev_subjects))],
                "cross_dataset_ridge",
            ),
            "pooled_shared": (
                table[
                    ((table["dataset"] == "edaic") & (table["subject_id"].isin(edaic_train_subjects)))
                    | ((table["dataset"] == "cmdc") & (table["subject_id"].isin(cmdc_train_subjects)))
                ],
                table[
                    ((table["dataset"] == "edaic") & (table["subject_id"].isin(edaic_dev_subjects)))
                    | ((table["dataset"] == "cmdc") & (table["subject_id"].isin(cmdc_eval_subjects)))
                ],
                "pooled_shared_ridge",
            ),
        }

        for protocol, (train, eval_frame, ridge_name) in selections.items():
            train = train.sort_values(["dataset", "subject_id"], key=lambda series: series.map(lambda item: tuple(natural_key(item))))
            eval_frame = eval_frame.sort_values(["dataset", "subject_id"], key=lambda series: series.map(lambda item: tuple(natural_key(item))))
            overlap = set(train["subject_key"]) & set(eval_frame["subject_key"])
            if overlap:
                raise ValueError(f"{protocol} subject overlap detected: {sorted(overlap, key=natural_key)[:5]}")
            for model_name in ["train_mean", ridge_name, "total_alloc_ridge"]:
                if model_name == "train_mean":
                    predictions = predict_train_mean(train, eval_frame, model_name)
                    details: dict[str, Any] = {}
                elif model_name == "total_alloc_ridge":
                    predictions, details = fit_predict_total_alloc(train, eval_frame, feature_cols, seed, model_name)
                else:
                    predictions, details = fit_predict_constructs(train, eval_frame, feature_cols, seed, model_name)
                predictions["seed"] = seed
                predictions["protocol"] = protocol
                prediction_frames.append(predictions)
                metric_rows.extend(metric_rows_for_predictions(predictions, model_name, protocol, seed))
                model_audit_rows.append(
                    {
                        "seed": seed,
                        "protocol": protocol,
                        "model": model_name,
                        "train_subjects": int(train["subject_key"].nunique()),
                        "eval_subjects": int(eval_frame["subject_key"].nunique()),
                        "train_datasets": ";".join(sorted(train["dataset"].unique())),
                        "eval_datasets": ";".join(sorted(eval_frame["dataset"].unique())),
                        "subject_overlap_count": int(len(overlap)),
                        "selected_alpha": details.get("selected_alpha"),
                    }
                )

    predictions_all = pd.concat(prediction_frames, ignore_index=True)
    metrics_by_seed = pd.DataFrame(metric_rows)
    model_audit = pd.DataFrame(model_audit_rows)
    return predictions_all, metrics_by_seed, model_audit


def format_value(value: Any, digits: int = 3) -> str:
    numeric = safe_float(value)
    if numeric is None:
        return "NA"
    return f"{numeric:.{digits}f}"


def write_report(
    out_dir: Path,
    run_summary: dict[str, Any],
    metric_summary: pd.DataFrame,
    comparison_summary: pd.DataFrame,
    identity_summary: pd.DataFrame,
) -> None:
    macro = metric_summary[
        (metric_summary["construct_id"] == "macro")
        & (metric_summary["metric"] == "Macro Construct MAE")
        & (metric_summary["dataset_slice"] != "pooled")
    ].copy()
    macro = macro.sort_values(["protocol", "dataset_slice", "model"])
    comparison = comparison_summary.sort_values(["protocol", "dataset_slice", "model"])
    identity_value = identity_summary.loc[identity_summary["metric"] == "Balanced Accuracy", "mean"].iloc[0]

    lines = [
        "# P5_MV01 PHQ Core Construct Bridge",
        "",
        f"Generated: `{run_summary['generated_at']}`",
        "",
        "## Scope",
        "",
        "This is the first runnable Phase 5 minimal-validation row. It maps E-DAIC PHQ-8 and CMDC PHQ-9 item labels to C01-C08, uses cached frozen WavLM subject features, and trains only shallow Ridge or mean baselines. No encoder fine-tuning, source-data scan, transcript export, or full-method component is used.",
        "",
        "## Feature And Split Contract",
        "",
        f"- Common frozen WavLM columns: `{run_summary['feature_contract']['common_feature_column_count']}`.",
        f"- E-DAIC subjects joined: `{run_summary['feature_contract']['joined_subjects']['edaic']}`; official train/dev only.",
        f"- CMDC subjects joined: `{run_summary['feature_contract']['joined_subjects']['cmdc']}`; Phase 2 5-fold subject CV.",
        f"- Subject-overlap violations: `{run_summary['split_audit']['subject_overlap_violations']}`.",
        f"- Frozen feature dataset identity risk, E-DAIC vs CMDC WavLM balanced accuracy: `{format_value(identity_value)}`.",
        "",
        "## Macro MAE",
        "",
        "| protocol | dataset | model | macro MAE | seed count |",
        "| --- | --- | --- | ---: | ---: |",
    ]
    for _, row in macro.iterrows():
        lines.append(
            f"| {row['protocol']} | {row['dataset_slice']} | {row['model']} | {format_value(row['mean'])} | {int(row['seed_count'])} |"
        )
    lines.extend(
        [
            "",
            "## Deltas",
            "",
            "Negative deltas are improvements in MAE.",
            "",
            "| protocol | dataset | model | delta vs train_mean | delta vs total_alloc_ridge |",
            "| --- | --- | --- | ---: | ---: |",
        ]
    )
    for _, row in comparison.iterrows():
        lines.append(
            f"| {row['protocol']} | {row['dataset_slice']} | {row['model']} | {format_value(row['delta_vs_train_mean'])} | {format_value(row['delta_vs_total_alloc_ridge'])} |"
        )
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            run_summary["interpretation"]["short_read"],
            "",
            "The result should not be read as evidence of a shared symptom representation on its own. The frozen WavLM identity probe remains high, so any pooled improvement is treated as a narrow bridge signal requiring later identity/protocol controls.",
            "",
            "## Hygiene",
            "",
            f"- Artifact hygiene passed: `{run_summary['artifact_hygiene_passed']}`.",
            "- Row-level predictions are written as a local-only ignored CSV.",
        ]
    )
    (out_dir / "report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def artifact_hygiene_audit(out_dir: Path) -> dict[str, Any]:
    forbidden_patterns = [
        r"/root/autodl-tmp/datasets/",
        r"audio_path",
        r"video_path",
        r"text_path",
        r"gait_path",
        r"\.wav\b",
        r"\.WAV\b",
        r"\.mp4\b",
        r"\.avi\b",
        r"Transcript",
        r"PHQ_8Depressed",
        r"PHQ_8NoInterest",
        r"PHQ_8Sleep",
        r"PHQ_8Tired",
        r"PHQ_8Appetite",
        r"PHQ_8Failure",
        r"PHQ_8Concentrating",
        r"PHQ_8Moving",
    ]
    violations: list[dict[str, Any]] = []
    files_checked = 0
    for path in sorted(out_dir.rglob("*")):
        if not path.is_file():
            continue
        if path.suffix.lower() not in {".csv", ".json", ".md", ".txt"}:
            continue
        files_checked += 1
        text = path.read_text(encoding="utf-8", errors="ignore")
        for pattern in forbidden_patterns:
            if re.search(pattern, text):
                violations.append({"file": str(path.relative_to(out_dir)), "pattern": pattern})
    return {
        "audit_id": "P5_MV01_artifact_hygiene",
        "generated_at": utc_now(),
        "files_checked": files_checked,
        "violation_count": len(violations),
        "violations": violations,
        "artifact_hygiene_passed": len(violations) == 0,
        "local_only_patterns": [
            "analysis/phase5_minimal_validation/**/*predictions*.csv",
            "analysis/phase5_minimal_validation/**/*features*.csv",
            "analysis/phase5_minimal_validation/**/*embeddings*.csv",
            "analysis/phase5_minimal_validation/**/*model*.joblib",
            "analysis/phase5_minimal_validation/**/*model*.pkl",
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--manifest-dir", type=Path, default=DEFAULT_MANIFEST_DIR)
    parser.add_argument("--split-path", type=Path, default=DEFAULT_SPLIT_PATH)
    parser.add_argument("--phase2-root", type=Path, default=None)
    args = parser.parse_args()

    out_dir = args.out_dir
    if out_dir.exists():
        shutil.rmtree(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    phase2_root, phase2_root_source = resolve_phase2_root(args.phase2_root)
    table, feature_cols, availability = build_model_table(args.manifest_dir, phase2_root)
    cmdc_folds = load_cmdc_folds(args.split_path)
    predictions, metrics_by_seed, model_audit = run_experiment(table, feature_cols, cmdc_folds)
    identity_by_seed = run_dataset_identity_probe(table, feature_cols)

    metric_summary = summarize_metrics(metrics_by_seed)
    identity_summary = summarize_metrics(
        identity_by_seed.assign(protocol="feature_identity", model="frozen_wavlm", dataset_slice="edaic_cmdc", construct_id="identity")
    )
    comparison_summary = build_comparison_summary(metric_summary)

    target_map_rows = []
    for dataset, spec in DATASET_SPECS.items():
        for construct_id, item_code in spec.item_map.items():
            target_map_rows.append({"dataset": dataset, "construct_id": construct_id, "scale_item_code": item_code})
    target_map = pd.DataFrame(target_map_rows)
    # Use short scale item codes in local-only predictions but avoid PHQ-8
    # manifest field names in versionable reports/audits.
    safe_predictions = predictions.copy()
    safe_predictions["item_code"] = safe_predictions["eval_dataset"].map({"edaic": "PHQ8_", "cmdc": "PHQ9_"}) + safe_predictions[
        "construct_id"
    ]

    safe_target_map = target_map.copy()
    safe_target_map["scale_item_code"] = safe_target_map["dataset"].map({"edaic": "PHQ8_", "cmdc": "PHQ9_"}) + safe_target_map[
        "construct_id"
    ]

    metrics_by_seed.to_csv(out_dir / "metrics_by_seed.csv", index=False)
    metric_summary.to_csv(out_dir / "metric_summary.csv", index=False)
    comparison_summary.to_csv(out_dir / "comparison_summary.csv", index=False)
    identity_by_seed.to_csv(out_dir / "dataset_identity_probe_by_seed.csv", index=False)
    identity_summary.to_csv(out_dir / "dataset_identity_probe_summary.csv", index=False)
    availability.to_csv(out_dir / "feature_availability.csv", index=False)
    model_audit.to_csv(out_dir / "model_split_audit.csv", index=False)
    safe_target_map.to_csv(out_dir / "construct_target_map.csv", index=False)
    safe_predictions.to_csv(out_dir / "p5_mv01_local_predictions.csv", index=False)

    macro = metric_summary[
        (metric_summary["construct_id"] == "macro")
        & (metric_summary["metric"] == "Macro Construct MAE")
        & (metric_summary["dataset_slice"] != "pooled")
    ].copy()
    pooled_rows = comparison_summary[comparison_summary["protocol"] == "pooled_shared"].copy()
    pooled_better_than_total = bool(
        (pooled_rows[pooled_rows["model"] == "pooled_shared_ridge"]["delta_vs_total_alloc_ridge"].dropna() < 0).any()
    )
    pooled_better_than_mean = bool(
        (pooled_rows[pooled_rows["model"] == "pooled_shared_ridge"]["delta_vs_train_mean"].dropna() < 0).any()
    )
    identity_value = float(identity_summary.loc[identity_summary["metric"] == "Balanced Accuracy", "mean"].iloc[0])
    if pooled_better_than_total and pooled_better_than_mean:
        short_read = (
            "The PHQ core bridge is runnable but weak and asymmetric: pooled Ridge helps only selectively, while frozen WavLM dataset identity remains perfectly recoverable, so this row is a diagnostic baseline rather than evidence of a shared symptom representation."
        )
    else:
        short_read = (
            "The PHQ core bridge is runnable but weak and asymmetric: pooled Ridge does not consistently beat trivial and total-allocation baselines, so this row is a diagnostic baseline rather than evidence of a shared symptom representation."
        )

    run_summary: dict[str, Any] = {
        "run_id": "P5_MV01_phq_core_construct_bridge",
        "generated_at": utc_now(),
        "status": "complete",
        "phase2_feature_root_source": phase2_root_source,
        "feature_contract": {
            "feature_space": "frozen_wavlm_subject_mean",
            "common_feature_column_count": len(feature_cols),
            "joined_subjects": availability.set_index("dataset")["joined_subjects"].astype(int).to_dict(),
            "feature_dataset_identity_risk": {
                "probe": "E-DAIC_vs_CMDC_frozen_WavLM",
                "balanced_accuracy_mean": identity_value,
            },
        },
        "target_contract": {
            "constructs": CONSTRUCTS,
            "source_scales": {"edaic": "PHQ-8", "cmdc": "PHQ-9"},
            "c09_policy": "excluded_from_core_bridge_safety_sensitive_phq9_only",
        },
        "model_contract": {
            "models": ["train_mean", "dataset_specific_ridge", "cross_dataset_ridge", "pooled_shared_ridge", "total_alloc_ridge"],
            "seeds": SEEDS,
            "encoder_finetuning": False,
            "raw_audio_scan": False,
        },
        "split_audit": {
            "subject_level": True,
            "edaic_official_test_used": False,
            "cmdc_phase2_subject_cv_used": True,
            "subject_overlap_violations": int(model_audit["subject_overlap_count"].sum()),
        },
        "output_policy": {
            "row_level_predictions": "local_only_ignored",
            "learned_embeddings": "not_written",
            "model_weights": "not_written",
        },
        "artifact_hygiene_passed": False,
        "interpretation": {"short_read": short_read},
        "summary_files": [
            "report.md",
            "run_summary.json",
            "artifact_hygiene_audit.json",
            "metric_summary.csv",
            "metrics_by_seed.csv",
            "comparison_summary.csv",
            "dataset_identity_probe_summary.csv",
            "feature_availability.csv",
            "model_split_audit.csv",
            "construct_target_map.csv",
        ],
        "local_only_files": ["p5_mv01_local_predictions.csv"],
    }

    (out_dir / "run_summary.json").write_text(json.dumps(run_summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    write_report(out_dir, run_summary, metric_summary, comparison_summary, identity_summary)
    hygiene = artifact_hygiene_audit(out_dir)
    run_summary["artifact_hygiene_passed"] = bool(hygiene["artifact_hygiene_passed"])
    (out_dir / "run_summary.json").write_text(json.dumps(run_summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    write_report(out_dir, run_summary, metric_summary, comparison_summary, identity_summary)
    hygiene = artifact_hygiene_audit(out_dir)
    run_summary["artifact_hygiene_passed"] = bool(hygiene["artifact_hygiene_passed"])
    (out_dir / "run_summary.json").write_text(json.dumps(run_summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (out_dir / "artifact_hygiene_audit.json").write_text(json.dumps(hygiene, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    if not hygiene["artifact_hygiene_passed"]:
        raise SystemExit("artifact hygiene violations found; see artifact_hygiene_audit.json")


if __name__ == "__main__":
    main()
