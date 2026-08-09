#!/usr/bin/env python3
"""Run P5_MV03 SDS total external stress validation on EATD.

This is a minimal Phase 5 validation row for the SDS total/severity-only
contract. It uses existing audited EATD manifest labels and cached frozen audio
features, trains only shallow SDS total heads on official train subjects, and
reports validation metrics stratified by positive/neutral/negative valence. It
does not claim SDS item-level supervision or train a full method.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import re
import sys
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
from sklearn.model_selection import GroupKFold, KFold
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import Ridge
from sklearn.svm import SVR


SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from phase2_metrics import bootstrap_ci, regression_metrics, safe_float
from phase3_task_valence_diagnostics import natural_key


WORKTREE_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT_DIR = WORKTREE_ROOT / "analysis" / "phase5_minimal_validation" / "p5_mv03_sds_total_external_stress"
DEFAULT_MANIFEST_PATH = WORKTREE_ROOT / "datasets" / "manifests" / "eatd_subjects.csv"
DEFAULT_WAVLM_SEGMENT_CACHE = (
    WORKTREE_ROOT / "analysis" / "phase2_baselines" / "eatd_audio_wavlm" / "eatd_wavlm_segment_embeddings.csv"
)
DEFAULT_EGEMAPS_SEGMENT_CACHE = (
    WORKTREE_ROOT / "analysis" / "phase2_baselines" / "eatd_audio_egemaps" / "eatd_egemaps_segment_features.csv"
)
DEFAULT_PHASE3_CONFUSION = (
    WORKTREE_ROOT
    / "analysis"
    / "phase3_diagnostics"
    / "task_valence"
    / "eatd_healthy_negative_confusion_summary.csv"
)

SEEDS = [0, 1, 2, 3, 4]
VALENCES = ["positive", "neutral", "negative"]
RIDGE_ALPHA_GRID = [0.1, 1.0, 10.0, 100.0, 1000.0]
BOOTSTRAP_RESAMPLES = 200
TARGET_MIN = 20.0
TARGET_MAX = 100.0
TRAIN_MEAN_MODEL = "train_mean_sds_total"
WAVLM_SEGMENT_MODEL = "wavlm_valence_segment_ridge"
WAVLM_SUBJECT_MEAN_MODEL = "wavlm_subject_mean_ridge"
EGEMAPS_SEGMENT_MODEL = "egemaps_valence_segment_svr"


@dataclass(frozen=True)
class FeatureTable:
    feature_space: str
    frame: pd.DataFrame
    feature_columns: list[str]
    row_grain: str


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def format_value(value: Any, digits: int = 3) -> str:
    numeric = safe_float(value)
    if numeric is None:
        return "NA"
    return f"{numeric:.{digits}f}"


def read_csv(path: Path, **kwargs: Any) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"missing CSV: {path}")
    return pd.read_csv(path, **kwargs)


def bool_series(series: pd.Series) -> pd.Series:
    if pd.api.types.is_bool_dtype(series):
        return series.fillna(False)
    return series.astype(str).str.strip().str.lower().isin({"true", "1", "yes", "y"})


def load_eatd_labels(manifest_path: Path) -> pd.DataFrame:
    manifest = read_csv(manifest_path, dtype={"subject_id": str})
    required = {"subject_id", "valence", "sds_total", "binary_label", "official_split", "file_valid"}
    missing = required - set(manifest.columns)
    if missing:
        raise ValueError(f"EATD manifest missing columns: {', '.join(sorted(missing))}")
    usable = manifest[
        bool_series(manifest["file_valid"])
        & manifest["subject_id"].notna()
        & manifest["valence"].isin(VALENCES)
        & manifest["sds_total"].notna()
        & manifest["binary_label"].notna()
        & manifest["official_split"].isin(["train", "validation"])
    ].copy()
    if usable.empty:
        raise ValueError("no usable EATD rows with SDS total")
    rows: list[dict[str, Any]] = []
    for subject_id, group in usable.groupby("subject_id", sort=True):
        by_valence = {str(row["valence"]): row for _, row in group.iterrows()}
        missing_valences = [valence for valence in VALENCES if valence not in by_valence]
        if missing_valences:
            raise ValueError(f"EATD subject {subject_id} missing valence rows: {missing_valences}")
        splits = group["official_split"].dropna().astype(str).unique()
        totals = group["sds_total"].dropna().astype(float).unique()
        binary = group["binary_label"].dropna().astype(int).unique()
        severity = group["severity_label"].dropna().astype(float).unique() if "severity_label" in group else []
        if len(splits) != 1 or len(totals) != 1 or len(binary) != 1:
            raise ValueError(f"EATD subject {subject_id} has inconsistent split/label values")
        for valence in VALENCES:
            row = by_valence[valence]
            rows.append(
                {
                    "subject_id": str(subject_id),
                    "split": str(splits[0]),
                    "valence": valence,
                    "sds_total": float(totals[0]),
                    "severity_label": safe_float(severity[0]) if len(severity) == 1 else None,
                    "binary_label": int(binary[0]),
                    "manifest_row_available": True,
                }
            )
    labels = pd.DataFrame(rows).sort_values(["subject_id", "valence"]).reset_index(drop=True)
    train_subjects = set(labels.loc[labels["split"] == "train", "subject_id"].astype(str))
    validation_subjects = set(labels.loc[labels["split"] == "validation", "subject_id"].astype(str))
    overlap = train_subjects & validation_subjects
    if overlap:
        raise ValueError(f"EATD official split subject overlap: {sorted(overlap, key=natural_key)[:5]}")
    if not train_subjects or not validation_subjects:
        raise ValueError("EATD P5_MV03 requires non-empty train and validation subjects")
    return labels


def load_wavlm_segments(cache_path: Path, labels: pd.DataFrame) -> FeatureTable:
    cache = read_csv(cache_path, dtype={"subject_id": str})
    required = {"subject_id", "valence"}
    missing = required - set(cache.columns)
    if missing:
        raise ValueError(f"WavLM cache missing columns: {', '.join(sorted(missing))}")
    feature_columns = [column for column in cache.columns if column.startswith("wavlm_")]
    if not feature_columns:
        raise ValueError("WavLM cache has no wavlm_* columns")
    frame = labels.merge(
        cache[["subject_id", "valence", *feature_columns]],
        on=["subject_id", "valence"],
        how="inner",
        validate="one_to_one",
    )
    expected = set(zip(labels["subject_id"], labels["valence"], strict=True))
    observed = set(zip(frame["subject_id"], frame["valence"], strict=True))
    if expected != observed:
        missing_keys = sorted(expected - observed, key=lambda item: natural_key(item[0]) + [item[1]])
        raise ValueError(f"WavLM cache missing EATD rows: {missing_keys[:5]}")
    return FeatureTable("frozen_wavlm_valence_segment", frame, feature_columns, "subject_valence")


def load_egemaps_segments(cache_path: Path, labels: pd.DataFrame) -> FeatureTable:
    cache = read_csv(cache_path, dtype={"subject_id": str})
    required = {"subject_id", "valence"}
    missing = required - set(cache.columns)
    if missing:
        raise ValueError(f"eGeMAPS cache missing columns: {', '.join(sorted(missing))}")
    meta_columns = {"subject_id", "split", "valence", "sds_total", "binary_label", "severity_label"}
    feature_columns = [column for column in cache.columns if column not in meta_columns]
    if not feature_columns:
        raise ValueError("eGeMAPS cache has no feature columns")
    frame = labels.merge(
        cache[["subject_id", "valence", *feature_columns]],
        on=["subject_id", "valence"],
        how="inner",
        validate="one_to_one",
    )
    expected = set(zip(labels["subject_id"], labels["valence"], strict=True))
    observed = set(zip(frame["subject_id"], frame["valence"], strict=True))
    if expected != observed:
        missing_keys = sorted(expected - observed, key=lambda item: natural_key(item[0]) + [item[1]])
        raise ValueError(f"eGeMAPS cache missing EATD rows: {missing_keys[:5]}")
    return FeatureTable("egemaps_valence_segment", frame, feature_columns, "subject_valence")


def build_subject_mean_features(segment_table: FeatureTable) -> FeatureTable:
    rows: list[dict[str, Any]] = []
    for subject_id, group in segment_table.frame.groupby("subject_id", sort=True):
        if set(group["valence"].astype(str)) != set(VALENCES):
            raise ValueError(f"subject {subject_id} missing valence rows for subject mean")
        meta = group.iloc[0]
        values = group[segment_table.feature_columns].to_numpy(dtype=float)
        with np.errstate(invalid="ignore"):
            mean_values = np.nanmean(values, axis=0)
        row: dict[str, Any] = {
            "subject_id": str(subject_id),
            "split": str(meta["split"]),
            "sds_total": float(meta["sds_total"]),
            "severity_label": safe_float(meta.get("severity_label")),
            "binary_label": int(meta["binary_label"]),
            "valence": "all_valence_mean",
        }
        for column, value in zip(segment_table.feature_columns, mean_values, strict=True):
            row[column] = float(value) if np.isfinite(value) else np.nan
        rows.append(row)
    frame = pd.DataFrame(rows).sort_values("subject_id").reset_index(drop=True)
    return FeatureTable(f"{segment_table.feature_space}_subject_mean", frame, segment_table.feature_columns, "subject")


def ridge_pipeline(alpha: float) -> Pipeline:
    return Pipeline(
        [
            ("imputer", SimpleImputer(strategy="median")),
            ("scaler", StandardScaler()),
            ("ridge", Ridge(alpha=float(alpha))),
        ]
    )


def svr_pipeline() -> Pipeline:
    return Pipeline(
        [
            ("imputer", SimpleImputer(strategy="median")),
            ("scaler", StandardScaler()),
            ("svr", SVR(C=1.0, epsilon=0.1, kernel="rbf")),
        ]
    )


def choose_ridge_alpha(x: np.ndarray, y: np.ndarray, groups: Iterable[Any], seed: int) -> float:
    groups_arr = np.asarray([str(group) for group in groups])
    unique_groups = np.unique(groups_arr)
    if len(unique_groups) < 10:
        return 100.0
    n_splits = min(5, max(2, len(unique_groups) // 12))
    splitter = GroupKFold(n_splits=n_splits)
    best_alpha = RIDGE_ALPHA_GRID[0]
    best_mae = float("inf")
    for alpha in RIDGE_ALPHA_GRID:
        scores: list[float] = []
        for train_idx, dev_idx in splitter.split(x, y, groups=groups_arr):
            model = ridge_pipeline(alpha)
            model.fit(x[train_idx], y[train_idx])
            pred = np.clip(np.asarray(model.predict(x[dev_idx]), dtype=float).reshape(-1), TARGET_MIN, TARGET_MAX)
            scores.append(float(np.mean(np.abs(pred - y[dev_idx]))))
        score = float(np.mean(scores))
        if score < best_mae:
            best_mae = score
            best_alpha = alpha
    return float(best_alpha)


def fit_ridge_predictions(
    train: pd.DataFrame,
    validation: pd.DataFrame,
    feature_columns: list[str],
    model_name: str,
    seed: int,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    x_train = train[feature_columns].to_numpy(dtype=float)
    y_train = train["sds_total"].to_numpy(dtype=float)
    x_validation = validation[feature_columns].to_numpy(dtype=float)
    alpha = choose_ridge_alpha(x_train, y_train, train["subject_id"], seed)
    model = ridge_pipeline(alpha)
    model.fit(x_train, y_train)
    pred = np.clip(np.asarray(model.predict(x_validation), dtype=float).reshape(-1), TARGET_MIN, TARGET_MAX)
    return make_prediction_frame(validation, pred, model_name, seed), {"selected_alpha": alpha}


def fit_svr_predictions(
    train: pd.DataFrame,
    validation: pd.DataFrame,
    feature_columns: list[str],
    model_name: str,
    seed: int,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    model = svr_pipeline()
    model.fit(train[feature_columns].to_numpy(dtype=float), train["sds_total"].to_numpy(dtype=float))
    pred = np.clip(np.asarray(model.predict(validation[feature_columns].to_numpy(dtype=float)), dtype=float).reshape(-1), TARGET_MIN, TARGET_MAX)
    return make_prediction_frame(validation, pred, model_name, seed), {"selected_alpha": None}


def make_prediction_frame(validation: pd.DataFrame, pred: np.ndarray, model_name: str, seed: int) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for index, (_, row) in enumerate(validation.iterrows()):
        rows.append(
            {
                "run_id": "P5_MV03_sds_total_external_stress",
                "dataset": "EATD-Corpus",
                "modality": "Audio",
                "task": "SDS total regression",
                "model": model_name,
                "seed": int(seed),
                "task_type": "severity_regression",
                "subject_id": str(row["subject_id"]),
                "split": "validation",
                "valence": str(row["valence"]),
                "y_true": float(row["sds_total"]),
                "y_pred": float(pred[index]),
                "binary_label": int(row["binary_label"]),
            }
        )
    return pd.DataFrame(rows)


def train_mean_predictions(train_subjects: pd.DataFrame, validation: pd.DataFrame, seed: int) -> pd.DataFrame:
    mean_value = float(train_subjects.drop_duplicates("subject_id")["sds_total"].mean())
    pred = np.repeat(mean_value, len(validation))
    return make_prediction_frame(validation, pred, TRAIN_MEAN_MODEL, seed)


def expand_subject_mean_predictions(predictions: pd.DataFrame, labels: pd.DataFrame) -> pd.DataFrame:
    expanded = labels[labels["split"] == "validation"].merge(
        predictions[["seed", "model", "subject_id", "y_pred"]],
        on="subject_id",
        how="inner",
        validate="many_to_one",
    )
    rows: list[dict[str, Any]] = []
    for _, row in expanded.iterrows():
        rows.append(
            {
                "run_id": "P5_MV03_sds_total_external_stress",
                "dataset": "EATD-Corpus",
                "modality": "Audio",
                "task": "SDS total regression",
                "model": str(row["model"]),
                "seed": int(row["seed"]),
                "task_type": "severity_regression",
                "subject_id": str(row["subject_id"]),
                "split": "validation",
                "valence": str(row["valence"]),
                "y_true": float(row["sds_total"]),
                "y_pred": float(row["y_pred"]),
                "binary_label": int(row["binary_label"]),
            }
        )
    return pd.DataFrame(rows)


def run_experiment(
    labels: pd.DataFrame,
    wavlm_segments: FeatureTable,
    egemaps_segments: FeatureTable,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    prediction_frames: list[pd.DataFrame] = []
    audit_rows: list[dict[str, Any]] = []
    validation_labels = labels[labels["split"] == "validation"].copy()
    train_labels = labels[labels["split"] == "train"].copy()
    train_subjects = set(train_labels["subject_id"].astype(str))
    validation_subjects = set(validation_labels["subject_id"].astype(str))
    if train_subjects & validation_subjects:
        raise ValueError("EATD P5_MV03 subject overlap detected")

    wavlm_subject_mean = build_subject_mean_features(wavlm_segments)
    for seed in SEEDS:
        baseline = train_mean_predictions(train_labels, validation_labels, seed)
        prediction_frames.append(baseline)
        audit_rows.append(
            model_audit_row(seed, TRAIN_MEAN_MODEL, "none", train_labels, validation_labels, None)
        )

        for table, model_name, trainer in [
            (wavlm_segments, WAVLM_SEGMENT_MODEL, fit_ridge_predictions),
            (egemaps_segments, EGEMAPS_SEGMENT_MODEL, fit_svr_predictions),
        ]:
            train = table.frame[table.frame["split"] == "train"].reset_index(drop=True)
            validation = table.frame[table.frame["split"] == "validation"].reset_index(drop=True)
            predictions, details = trainer(train, validation, table.feature_columns, model_name, seed)
            prediction_frames.append(predictions)
            audit_rows.append(
                model_audit_row(
                    seed,
                    model_name,
                    table.feature_space,
                    train,
                    validation,
                    details.get("selected_alpha"),
                )
            )

        subject_train = wavlm_subject_mean.frame[wavlm_subject_mean.frame["split"] == "train"].reset_index(drop=True)
        subject_validation = wavlm_subject_mean.frame[wavlm_subject_mean.frame["split"] == "validation"].reset_index(drop=True)
        subject_predictions, subject_details = fit_ridge_predictions(
            subject_train,
            subject_validation,
            wavlm_subject_mean.feature_columns,
            WAVLM_SUBJECT_MEAN_MODEL,
            seed,
        )
        prediction_frames.append(expand_subject_mean_predictions(subject_predictions, labels))
        audit_rows.append(
            model_audit_row(
                seed,
                WAVLM_SUBJECT_MEAN_MODEL,
                wavlm_subject_mean.feature_space,
                subject_train,
                subject_validation,
                subject_details.get("selected_alpha"),
            )
        )

    predictions = pd.concat(prediction_frames, ignore_index=True)
    metrics_by_seed, metric_summary = metric_tables(predictions)
    return predictions, metrics_by_seed, metric_summary, pd.DataFrame(audit_rows)


def model_audit_row(
    seed: int,
    model_name: str,
    feature_space: str,
    train: pd.DataFrame,
    validation: pd.DataFrame,
    selected_alpha: float | None,
) -> dict[str, Any]:
    train_subjects = set(train["subject_id"].astype(str))
    validation_subjects = set(validation["subject_id"].astype(str))
    return {
        "seed": int(seed),
        "model": model_name,
        "feature_space": feature_space,
        "train_rows": int(len(train)),
        "validation_rows": int(len(validation)),
        "train_subjects": int(len(train_subjects)),
        "validation_subjects": int(len(validation_subjects)),
        "subject_overlap_count": int(len(train_subjects & validation_subjects)),
        "selected_alpha": selected_alpha,
        "encoder_finetuning": False,
        "raw_audio_scan": False,
        "control_uses_validation_labels_for_hyperparameters": False,
    }


def metric_tables(predictions: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    rows: list[dict[str, Any]] = []
    group_cols = ["model", "seed", "valence"]
    overall = predictions.copy()
    overall["valence"] = "all_valences"
    grouped = pd.concat([predictions, overall], ignore_index=True)
    for key, group in grouped.groupby(group_cols, sort=False, dropna=False):
        model, seed, valence = key
        metrics = regression_metrics(group["y_true"], group["y_pred"])
        for metric, value in metrics.items():
            ci_low, ci_high = bootstrap_ci(
                group,
                "severity_regression",
                metric,
                BOOTSTRAP_RESAMPLES,
                seed=20260805 + int(seed),
                unit_column="subject_id",
            )
            rows.append(
                {
                    "run_id": "P5_MV03_sds_total_external_stress",
                    "dataset": "EATD-Corpus",
                    "target": "sds_total",
                    "model": str(model),
                    "seed": int(seed),
                    "valence": str(valence),
                    "metric": metric,
                    "value": value,
                    "ci95_low": ci_low,
                    "ci95_high": ci_high,
                    "sample_count": int(len(group)),
                    "subject_count": int(group["subject_id"].nunique()),
                }
            )
    by_seed = pd.DataFrame(rows)
    summary_rows: list[dict[str, Any]] = []
    for key, group in by_seed.groupby(["run_id", "dataset", "target", "model", "valence", "metric"], sort=False):
        run_id, dataset, target, model, valence, metric = key
        values = [safe_float(value) for value in group["value"]]
        values = [float(value) for value in values if value is not None]
        if not values:
            continue
        ci_low_values = [safe_float(value) for value in group["ci95_low"]]
        ci_high_values = [safe_float(value) for value in group["ci95_high"]]
        summary_rows.append(
            {
                "run_id": run_id,
                "dataset": dataset,
                "target": target,
                "model": model,
                "valence": valence,
                "metric": metric,
                "mean": safe_float(np.mean(values)),
                "std": safe_float(np.std(values, ddof=0)),
                "ci95_low": safe_float(np.mean([v for v in ci_low_values if v is not None]))
                if any(v is not None for v in ci_low_values)
                else None,
                "ci95_high": safe_float(np.mean([v for v in ci_high_values if v is not None]))
                if any(v is not None for v in ci_high_values)
                else None,
                "seed_count": int(len(values)),
                "sample_count_mean": safe_float(np.mean(group["sample_count"])),
                "subject_count_mean": safe_float(np.mean(group["subject_count"])),
            }
        )
    return by_seed, pd.DataFrame(summary_rows)


def build_comparison_summary(metric_summary: pd.DataFrame) -> pd.DataFrame:
    mae = metric_summary[
        (metric_summary["metric"] == "MAE") & (metric_summary["valence"].isin(["all_valences", *VALENCES]))
    ].copy()
    values = mae.set_index(["model", "valence"])["mean"].to_dict()
    rows: list[dict[str, Any]] = []
    for valence in ["all_valences", *VALENCES]:
        train_mean = values.get((TRAIN_MEAN_MODEL, valence))
        for model in sorted(mae["model"].unique(), key=natural_key):
            current = values.get((model, valence))
            if current is None:
                continue
            rows.append(
                {
                    "valence": valence,
                    "model": model,
                    "mae": current,
                    "delta_vs_train_mean": safe_float(current - train_mean) if train_mean is not None else None,
                    "relative_delta_vs_train_mean": safe_float((current - train_mean) / train_mean)
                    if train_mean not in (None, 0)
                    else None,
                }
            )
    return pd.DataFrame(rows)


def valence_gap_tables(predictions: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    subject_rows: list[dict[str, Any]] = []
    by_seed_rows: list[dict[str, Any]] = []
    healthy_rows: list[dict[str, Any]] = []
    for (model, seed, subject_id), group in predictions.groupby(["model", "seed", "subject_id"], sort=False):
        by_valence = group.set_index("valence")["y_pred"].to_dict()
        if not all(valence in by_valence for valence in VALENCES):
            continue
        nonnegative = float(np.mean([by_valence["positive"], by_valence["neutral"]]))
        values = np.asarray([by_valence[valence] for valence in VALENCES], dtype=float)
        binary_label = int(group["binary_label"].iloc[0])
        row = {
            "model": str(model),
            "seed": int(seed),
            "subject_id": str(subject_id),
            "binary_label": binary_label,
            "pred_positive": float(by_valence["positive"]),
            "pred_neutral": float(by_valence["neutral"]),
            "pred_negative": float(by_valence["negative"]),
            "pred_nonnegative_mean": nonnegative,
            "valence_prediction_std": safe_float(np.std(values, ddof=0)),
            "negative_minus_nonnegative": safe_float(float(by_valence["negative"]) - nonnegative),
            "negative_highest": bool(by_valence["negative"] > max(by_valence["positive"], by_valence["neutral"])),
        }
        subject_rows.append(row)
    subject_frame = pd.DataFrame(subject_rows)
    for (model, seed), group in subject_frame.groupby(["model", "seed"], sort=False):
        by_seed_rows.extend(
            [
                gap_metric_row(model, seed, "valence_prediction_std", group["valence_prediction_std"].mean(), group),
                gap_metric_row(model, seed, "negative_minus_nonnegative", group["negative_minus_nonnegative"].mean(), group),
                gap_metric_row(model, seed, "negative_highest_rate", group["negative_highest"].astype(float).mean(), group),
            ]
        )
        healthy = group[group["binary_label"] == 0].copy()
        if not healthy.empty:
            healthy_rows.extend(
                [
                    gap_metric_row(model, seed, "healthy_negative_minus_nonnegative", healthy["negative_minus_nonnegative"].mean(), healthy),
                    gap_metric_row(model, seed, "healthy_negative_highest_rate", healthy["negative_highest"].astype(float).mean(), healthy),
                    gap_metric_row(model, seed, "healthy_negative_mean_pred", healthy["pred_negative"].mean(), healthy),
                    gap_metric_row(model, seed, "healthy_nonnegative_mean_pred", healthy["pred_nonnegative_mean"].mean(), healthy),
                ]
            )
    by_seed = pd.DataFrame(by_seed_rows)
    healthy_by_seed = pd.DataFrame(healthy_rows)
    return subject_frame, by_seed, summarize_gap_rows(by_seed), summarize_gap_rows(healthy_by_seed)


def gap_metric_row(model: Any, seed: Any, metric: str, value: Any, group: pd.DataFrame) -> dict[str, Any]:
    return {
        "model": str(model),
        "seed": int(seed),
        "metric": metric,
        "value": safe_float(value),
        "subject_count": int(group["subject_id"].nunique()),
    }


def summarize_gap_rows(by_seed: pd.DataFrame) -> pd.DataFrame:
    if by_seed.empty:
        return pd.DataFrame(columns=["model", "metric", "mean", "std", "seed_count", "subject_count_mean"])
    rows: list[dict[str, Any]] = []
    for (model, metric), group in by_seed.groupby(["model", "metric"], sort=False):
        values = [safe_float(value) for value in group["value"]]
        values = [float(value) for value in values if value is not None]
        if not values:
            continue
        rows.append(
            {
                "model": str(model),
                "metric": str(metric),
                "mean": safe_float(np.mean(values)),
                "std": safe_float(np.std(values, ddof=0)),
                "seed_count": int(len(values)),
                "subject_count_mean": safe_float(np.mean(group["subject_count"])),
            }
        )
    return pd.DataFrame(rows)


def phase3_reference(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame(columns=["phase3_metric", "phase3_mean", "phase3_ci95_low", "phase3_ci95_high"])
    frame = pd.read_csv(path)
    rows: list[dict[str, Any]] = []
    for _, row in frame.iterrows():
        rows.append(
            {
                "phase3_metric": row["metric"],
                "phase3_mean": safe_float(row["mean"]),
                "phase3_ci95_low": safe_float(row.get("ci95_low")),
                "phase3_ci95_high": safe_float(row.get("ci95_high")),
            }
        )
    return pd.DataFrame(rows)


def build_verdict(
    comparison_summary: pd.DataFrame,
    healthy_summary: pd.DataFrame,
    phase3: pd.DataFrame,
    subject_overlap_violations: int,
) -> dict[str, Any]:
    all_mae = comparison_summary[comparison_summary["valence"] == "all_valences"].copy()
    model_rows = all_mae[all_mae["model"] != TRAIN_MEAN_MODEL].copy()
    improving = model_rows[model_rows["delta_vs_train_mean"].fillna(float("inf")) < 0.0].copy()
    if not improving.empty:
        best_row = improving.sort_values(["mae", "model"]).iloc[0]
    elif not model_rows.empty:
        best_row = model_rows.sort_values(["mae", "model"]).iloc[0]
    else:
        best_row = all_mae.sort_values(["mae", "model"]).iloc[0]
    best_model = str(best_row["model"])
    best_delta = safe_float(best_row.get("delta_vs_train_mean"))
    best_mae = safe_float(best_row.get("mae"))
    healthy_lookup = healthy_summary.set_index(["model", "metric"])["mean"].to_dict() if not healthy_summary.empty else {}
    best_healthy_negative_minus_nonnegative = healthy_lookup.get((best_model, "healthy_negative_minus_nonnegative"))
    phase3_lookup = phase3.set_index("phase3_metric")["phase3_mean"].to_dict() if not phase3.empty else {}
    phase3_negative_minus_nonnegative = phase3_lookup.get("healthy_negative_minus_nonnegative_mean")
    stronger_negative_shortcut = bool(
        best_healthy_negative_minus_nonnegative is not None
        and phase3_negative_minus_nonnegative is not None
        and best_healthy_negative_minus_nonnegative > max(0.0, phase3_negative_minus_nonnegative)
    )
    if subject_overlap_violations > 0:
        status = "blocked_split_overlap"
        short_read = "P5_MV03 is blocked because the EATD split audit found subject overlap."
    elif best_delta is not None and best_delta < 0.0 and not stronger_negative_shortcut:
        status = "pass_sds_total_external_stress"
        short_read = (
            "At least one shallow SDS total head improves over the train-mean floor on EATD validation without a stronger healthy-negative valence shortcut than the Phase 3 diagnostic."
        )
    elif best_delta is not None and best_delta < 0.0:
        status = "blocked_valence_shortcut"
        short_read = (
            "The best SDS total head improves over the train-mean floor, but healthy negative material shows stronger shortcut risk than the Phase 3 diagnostic."
        )
    else:
        status = "blocked_no_sds_generalization"
        short_read = (
            "The EATD SDS total heads are runnable, but none beat the train-mean floor on validation MAE; treat this as weak external stress evidence."
        )
    return {
        "pass_rule_status": status,
        "pass_rule_met": status == "pass_sds_total_external_stress",
        "short_read": short_read,
        "best_model": best_model,
        "best_all_valence_mae": best_mae,
        "best_delta_vs_train_mean_mae": best_delta,
        "best_healthy_negative_minus_nonnegative": safe_float(best_healthy_negative_minus_nonnegative),
        "phase3_healthy_negative_minus_nonnegative": safe_float(phase3_negative_minus_nonnegative),
        "stronger_negative_shortcut_than_phase3": stronger_negative_shortcut,
        "subject_overlap_violations": int(subject_overlap_violations),
    }


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
        r"raw prompt",
        r"raw response",
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
        "audit_id": "P5_MV03_artifact_hygiene",
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
            "analysis/phase5_minimal_validation/**/*weights*.csv",
        ],
    }


def write_report(
    out_dir: Path,
    run_summary: dict[str, Any],
    metric_summary: pd.DataFrame,
    comparison_summary: pd.DataFrame,
    valence_gap_summary: pd.DataFrame,
    healthy_summary: pd.DataFrame,
) -> None:
    mae = metric_summary[metric_summary["metric"] == "MAE"].sort_values(["valence", "model"])
    comparison = comparison_summary.sort_values(["valence", "model"])
    lines = [
        "# P5_MV03 SDS Total External Stress",
        "",
        f"Generated: `{run_summary['generated_at']}`",
        "",
        "## Scope",
        "",
        "This row tests the EATD SDS total/severity-only contract. It uses existing manifest labels and cached frozen audio features, trains shallow SDS total heads on official train subjects, and evaluates validation subjects stratified by positive, neutral, and negative valence. It does not use SDS item labels, fine-tune encoders, scan raw audio, or train a full method.",
        "",
        "## Feature And Split Contract",
        "",
        f"- Train subjects: `{run_summary['split_audit']['train_subjects']}`.",
        f"- Validation subjects: `{run_summary['split_audit']['validation_subjects']}`.",
        f"- Subject-overlap violations: `{run_summary['split_audit']['subject_overlap_violations']}`.",
        f"- EATD valences: `{', '.join(VALENCES)}`.",
        f"- WavLM feature columns: `{run_summary['feature_contract']['wavlm_feature_count']}`.",
        f"- eGeMAPS feature columns: `{run_summary['feature_contract']['egemaps_feature_count']}`.",
        "",
        "## SDS Total MAE",
        "",
        "| valence | model | MAE | delta vs train_mean | seed count |",
        "| --- | --- | ---: | ---: | ---: |",
    ]
    for _, row in comparison.iterrows():
        lines.append(
            f"| {row['valence']} | {row['model']} | {format_value(row['mae'])} | {format_value(row['delta_vs_train_mean'])} | 5 |"
        )
    lines.extend(
        [
            "",
            "## Regression Metrics",
            "",
            "| valence | model | metric | mean | ci95 low | ci95 high |",
            "| --- | --- | --- | ---: | ---: | ---: |",
        ]
    )
    for _, row in mae.iterrows():
        lines.append(
            f"| {row['valence']} | {row['model']} | {row['metric']} | {format_value(row['mean'])} | {format_value(row['ci95_low'])} | {format_value(row['ci95_high'])} |"
        )
    lines.extend(
        [
            "",
            "## Valence Gap",
            "",
            "| model | metric | mean | seed count |",
            "| --- | --- | ---: | ---: |",
        ]
    )
    for _, row in valence_gap_summary.sort_values(["model", "metric"]).iterrows():
        lines.append(f"| {row['model']} | {row['metric']} | {format_value(row['mean'])} | {int(row['seed_count'])} |")
    lines.extend(
        [
            "",
            "## Healthy Negative Check",
            "",
            "| model | metric | mean | seed count |",
            "| --- | --- | ---: | ---: |",
        ]
    )
    for _, row in healthy_summary.sort_values(["model", "metric"]).iterrows():
        lines.append(f"| {row['model']} | {row['metric']} | {format_value(row['mean'])} | {int(row['seed_count'])} |")
    verdict = run_summary["verdict"]
    lines.extend(
        [
            "",
            "## Verdict",
            "",
            f"- Pass-rule status: `{verdict['pass_rule_status']}`.",
            f"- Best model: `{verdict['best_model']}`.",
            f"- Best all-valence MAE: `{format_value(verdict['best_all_valence_mae'])}`.",
            f"- Delta vs train-mean MAE: `{format_value(verdict['best_delta_vs_train_mean_mae'])}`.",
            f"- Healthy negative minus nonnegative, best model: `{format_value(verdict['best_healthy_negative_minus_nonnegative'])}`.",
            f"- Phase 3 healthy negative minus nonnegative reference: `{format_value(verdict['phase3_healthy_negative_minus_nonnegative'])}`.",
            "",
            verdict["short_read"],
            "",
            "## Hygiene",
            "",
            f"- Artifact hygiene passed: `{run_summary['artifact_hygiene_passed']}`.",
            "- Row-level predictions are written as a local-only ignored CSV.",
            "- Cached feature matrices are read but not copied into this output directory.",
            "- Raw audio, source paths, model weights, learned embeddings, prompts, and responses are not written.",
        ]
    )
    (out_dir / "report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST_PATH)
    parser.add_argument("--wavlm-segment-cache", type=Path, default=DEFAULT_WAVLM_SEGMENT_CACHE)
    parser.add_argument("--egemaps-segment-cache", type=Path, default=DEFAULT_EGEMAPS_SEGMENT_CACHE)
    parser.add_argument("--phase3-confusion-summary", type=Path, default=DEFAULT_PHASE3_CONFUSION)
    args = parser.parse_args()

    out_dir = args.out_dir
    if out_dir.exists():
        for child in out_dir.iterdir():
            if child.is_file():
                child.unlink()
    else:
        out_dir.mkdir(parents=True, exist_ok=True)

    labels = load_eatd_labels(args.manifest)
    wavlm_segments = load_wavlm_segments(args.wavlm_segment_cache, labels)
    egemaps_segments = load_egemaps_segments(args.egemaps_segment_cache, labels)
    predictions, metrics_by_seed, metric_summary, model_audit = run_experiment(labels, wavlm_segments, egemaps_segments)
    comparison_summary = build_comparison_summary(metric_summary)
    valence_subject, valence_gap_by_seed, valence_gap_summary, healthy_summary = valence_gap_tables(predictions)
    phase3 = phase3_reference(args.phase3_confusion_summary)
    subject_overlap_violations = int(model_audit["subject_overlap_count"].sum())
    verdict = build_verdict(comparison_summary, healthy_summary, phase3, subject_overlap_violations)

    predictions.to_csv(out_dir / "p5_mv03_local_predictions.csv", index=False)
    metrics_by_seed.to_csv(out_dir / "metrics_by_seed.csv", index=False)
    metric_summary.to_csv(out_dir / "metric_summary.csv", index=False)
    comparison_summary.to_csv(out_dir / "comparison_summary.csv", index=False)
    valence_gap_by_seed.to_csv(out_dir / "valence_gap_by_seed.csv", index=False)
    valence_gap_summary.to_csv(out_dir / "valence_gap_summary.csv", index=False)
    healthy_summary.to_csv(out_dir / "healthy_negative_summary.csv", index=False)
    phase3.to_csv(out_dir / "phase3_valence_reference.csv", index=False)
    model_audit.to_csv(out_dir / "model_split_audit.csv", index=False)
    pd.DataFrame(
        [
            {
                "feature_space": wavlm_segments.feature_space,
                "row_grain": wavlm_segments.row_grain,
                "rows": int(len(wavlm_segments.frame)),
                "subjects": int(wavlm_segments.frame["subject_id"].nunique()),
                "feature_count": int(len(wavlm_segments.feature_columns)),
                "cache_source": "phase2_eatd_audio_wavlm",
            },
            {
                "feature_space": egemaps_segments.feature_space,
                "row_grain": egemaps_segments.row_grain,
                "rows": int(len(egemaps_segments.frame)),
                "subjects": int(egemaps_segments.frame["subject_id"].nunique()),
                "feature_count": int(len(egemaps_segments.feature_columns)),
                "cache_source": "phase2_eatd_audio_egemaps",
            },
        ]
    ).to_csv(out_dir / "feature_availability.csv", index=False)

    train_subjects = set(labels.loc[labels["split"] == "train", "subject_id"].astype(str))
    validation_subjects = set(labels.loc[labels["split"] == "validation", "subject_id"].astype(str))
    run_summary: dict[str, Any] = {
        "run_id": "P5_MV03_sds_total_external_stress",
        "generated_at": utc_now(),
        "status": "complete",
        "target_contract": {
            "target": "sds_total",
            "source_scale": "SDS",
            "sds_item_level_supervision": False,
            "sds_total_only": True,
        },
        "feature_contract": {
            "feature_spaces": [wavlm_segments.feature_space, egemaps_segments.feature_space],
            "wavlm_feature_count": len(wavlm_segments.feature_columns),
            "egemaps_feature_count": len(egemaps_segments.feature_columns),
            "cached_features_read": True,
            "new_feature_extraction": False,
        },
        "model_contract": {
            "models": [TRAIN_MEAN_MODEL, WAVLM_SEGMENT_MODEL, WAVLM_SUBJECT_MEAN_MODEL, EGEMAPS_SEGMENT_MODEL],
            "seeds": SEEDS,
            "encoder_finetuning": False,
            "raw_audio_scan": False,
            "validation_labels_for_hyperparameters": False,
        },
        "split_audit": {
            "subject_level": True,
            "official_train_validation_split_used": True,
            "train_subjects": len(train_subjects),
            "validation_subjects": len(validation_subjects),
            "subject_overlap_violations": subject_overlap_violations,
        },
        "output_policy": {
            "row_level_predictions": "local_only_ignored",
            "learned_embeddings": "not_written",
            "model_weights": "not_written",
            "raw_audio": "not_written",
            "source_paths": "not_written",
            "raw_clinical_text": "not_written",
            "raw_prompts_or_responses": "not_written",
        },
        "verdict": verdict,
        "artifact_hygiene_passed": False,
        "summary_files": [
            "report.md",
            "run_summary.json",
            "artifact_hygiene_audit.json",
            "metric_summary.csv",
            "metrics_by_seed.csv",
            "comparison_summary.csv",
            "valence_gap_by_seed.csv",
            "valence_gap_summary.csv",
            "healthy_negative_summary.csv",
            "phase3_valence_reference.csv",
            "model_split_audit.csv",
            "feature_availability.csv",
        ],
        "local_only_files": ["p5_mv03_local_predictions.csv"],
    }
    (out_dir / "run_summary.json").write_text(json.dumps(run_summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    write_report(out_dir, run_summary, metric_summary, comparison_summary, valence_gap_summary, healthy_summary)
    hygiene = artifact_hygiene_audit(out_dir)
    run_summary["artifact_hygiene_passed"] = bool(hygiene["artifact_hygiene_passed"])
    (out_dir / "run_summary.json").write_text(json.dumps(run_summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    write_report(out_dir, run_summary, metric_summary, comparison_summary, valence_gap_summary, healthy_summary)
    (out_dir / "artifact_hygiene_audit.json").write_text(json.dumps(hygiene, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if not hygiene["artifact_hygiene_passed"]:
        raise SystemExit("artifact hygiene violations found; see artifact_hygiene_audit.json")


if __name__ == "__main__":
    main()
