#!/usr/bin/env python3
"""Phase 3 MODMA task-transfer and EATD valence-sensitivity diagnostics.

This script intentionally stays in the diagnostic lane: it uses manifest and
split layers, lightweight eGeMAPS features, fixed simple heads, five seeds, and
subject-level bootstrap intervals. It writes no raw text, audio, or source
paths to formal artifacts.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import re
import warnings
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable


def normalize_thread_env() -> None:
    value = str(os.environ.get("OMP_NUM_THREADS", "")).strip()
    if not value.isdigit() or int(value) <= 0:
        os.environ["OMP_NUM_THREADS"] = "1"
    os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
    os.environ.setdefault("MKL_NUM_THREADS", "1")


normalize_thread_env()

import numpy as np
import opensmile
import pandas as pd
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression, Ridge
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.svm import SVR

from phase2_metrics import compute_metrics, safe_float


WORKTREE_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT_DIR = WORKTREE_ROOT / "analysis" / "phase3_diagnostics" / "task_valence"
DEFAULT_MODMA_MANIFEST = WORKTREE_ROOT / "datasets" / "manifests" / "modma_subjects.csv"
DEFAULT_EATD_MANIFEST = WORKTREE_ROOT / "datasets" / "manifests" / "eatd_subjects.csv"
DEFAULT_SPLIT_PATH = WORKTREE_ROOT / "datasets" / "splits" / "phase2_subject_splits.csv"

SEEDS = [0, 1, 2, 3, 4]
MODMA_TASKS = ["interview", "reading", "picture_description", "affective_task"]
EATD_VALENCES = ["positive", "neutral", "negative"]
FIXED_LOGISTIC_C = 1.0
FIXED_SVR_C = 1.0
FIXED_SVR_EPSILON = 0.1
FIXED_RIDGE_ALPHA = 10.0
BOOTSTRAP_SEED = 20260805

ID_COLUMNS = {
    "subject_id",
    "task_type",
    "valence",
    "split",
    "binary_label",
    "sds_total",
    "phq9_total",
    "audio_segment_count",
}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def relpath(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(WORKTREE_ROOT))
    except ValueError:
        return path.name


def natural_key(value: Any) -> list[Any]:
    return [int(part) if part.isdigit() else part for part in re.split(r"(\d+)", str(value))]


def modma_subject_id(value: Any) -> str:
    return str(value).strip().zfill(8)


def read_csv(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"missing CSV: {path}")
    return pd.read_csv(path, dtype={"subject_id": str})


def bool_series(series: pd.Series) -> pd.Series:
    if pd.api.types.is_bool_dtype(series):
        return series.fillna(False)
    return series.astype(str).str.strip().str.lower().isin({"true", "1", "yes", "y"})


def feature_columns(frame: pd.DataFrame) -> list[str]:
    return [column for column in frame.columns if column not in ID_COLUMNS]


def classifier_pipeline(seed: int) -> Pipeline:
    return Pipeline(
        [
            ("imputer", SimpleImputer(strategy="median")),
            ("scaler", StandardScaler()),
            (
                "logistic",
                LogisticRegression(
                    C=FIXED_LOGISTIC_C,
                    class_weight="balanced",
                    max_iter=1000,
                    random_state=seed,
                    solver="liblinear",
                ),
            ),
        ]
    )


def svr_pipeline() -> Pipeline:
    return Pipeline(
        [
            ("imputer", SimpleImputer(strategy="median")),
            ("scaler", StandardScaler()),
            ("svr", SVR(C=FIXED_SVR_C, epsilon=FIXED_SVR_EPSILON, kernel="rbf")),
        ]
    )


def ridge_pipeline() -> Pipeline:
    return Pipeline(
        [
            ("imputer", SimpleImputer(strategy="median")),
            ("scaler", StandardScaler()),
            ("ridge", Ridge(alpha=FIXED_RIDGE_ALPHA, solver="lsqr")),
        ]
    )


def ensure_smile() -> opensmile.Smile:
    warnings.filterwarnings("ignore", message="Segment too short.*")
    return opensmile.Smile(
        feature_set=opensmile.FeatureSet.eGeMAPSv02,
        feature_level=opensmile.FeatureLevel.Functionals,
    )


def save_cache(path: Path, rows: list[dict[str, Any]], sort_columns: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    frame = pd.DataFrame(rows)
    if not frame.empty:
        frame = frame.sort_values(sort_columns).reset_index(drop=True)
    frame.to_csv(path, index=False)


def extract_egemaps(
    table: pd.DataFrame,
    *,
    cache_path: Path,
    key_columns: list[str],
    meta_columns: list[str],
    force: bool,
    progress_label: str,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    required_keys = set(tuple(str(row[column]) for column in key_columns) for _, row in table.iterrows())
    cached_rows: list[dict[str, Any]] = []
    cached_keys: set[tuple[str, ...]] = set()
    if cache_path.exists() and not force:
        cached = pd.read_csv(cache_path, dtype={column: str for column in key_columns})
        cached_keys = set(tuple(str(row[column]) for column in key_columns) for _, row in cached.iterrows())
        cached_rows = cached[
            [
                tuple(str(row[column]) for column in key_columns) in required_keys
                for _, row in cached.iterrows()
            ]
        ].to_dict("records")

    missing = table[
        [
            tuple(str(row[column]) for column in key_columns) not in cached_keys
            for _, row in table.iterrows()
        ]
    ].reset_index(drop=True)

    rows = cached_rows
    skipped_rows: list[dict[str, Any]] = []
    smile = ensure_smile()
    print(f"Extracting {progress_label} eGeMAPS: {len(missing)} missing / {len(table)} segments", flush=True)
    for idx, row in missing.iterrows():
        audio_path = Path(str(row["audio_path"]))
        if not audio_path.exists():
            raise FileNotFoundError(f"manifest audio path missing: {audio_path}")
        if idx == 0 or (idx + 1) % 50 == 0 or idx + 1 == len(missing):
            label_bits = " ".join(f"{column}={row[column]}" for column in key_columns if column != "segment_key")
            print(f"  [{progress_label}] {idx + 1}/{len(missing)} {label_bits}", flush=True)
        try:
            values = smile.process_file(str(audio_path))
        except Exception as exc:  # openSMILE/audiofile exceptions vary by backend.
            skipped_rows.append(
                {
                    **{column: row[column] for column in key_columns},
                    "error_type": type(exc).__name__,
                    "status": "unreadable_audio_excluded",
                }
            )
            continue
        if values.empty:
            raise ValueError(f"openSMILE returned no features for manifest row key={tuple(row[column] for column in key_columns)}")
        series = values.iloc[0]
        rows.append(
            {
                **{column: row[column] for column in meta_columns},
                **{str(column): float(series[column]) for column in series.index},
            }
        )
        if (idx + 1) % 50 == 0:
            save_cache(cache_path, rows, key_columns)

    if not rows:
        raise RuntimeError(f"no eGeMAPS rows available for {progress_label}")
    save_cache(cache_path, rows, key_columns)
    features = pd.DataFrame(rows)
    observed = set(tuple(str(row[column]) for column in key_columns) for _, row in features.iterrows())
    skipped = pd.DataFrame(skipped_rows)
    skipped_keys = (
        set(tuple(str(row[column]) for column in key_columns) for _, row in skipped.iterrows())
        if not skipped.empty
        else set()
    )
    if not skipped.empty:
        skipped_path = cache_path.with_name(f"{cache_path.stem}_skipped_segments.csv")
        skipped.sort_values(key_columns).to_csv(skipped_path, index=False)
    else:
        skipped_path = cache_path.with_name(f"{cache_path.stem}_skipped_segments.csv")
        if skipped_path.exists():
            skipped_path.unlink()
    missing_keys = required_keys - observed - skipped_keys
    if missing_keys:
        raise ValueError(f"{progress_label} eGeMAPS cache missing keys: {sorted(missing_keys)[:5]}")
    selected = features[
        [
            tuple(str(row[column]) for column in key_columns) in required_keys
            for _, row in features.iterrows()
        ]
    ].copy()
    if skipped.empty:
        skipped = pd.DataFrame(columns=[*key_columns, "error_type", "status"])
    else:
        skipped = skipped.sort_values(key_columns).reset_index(drop=True)
    return selected.sort_values(key_columns).reset_index(drop=True), skipped


def build_modma_segment_table(manifest_path: Path) -> tuple[pd.DataFrame, int]:
    manifest = read_csv(manifest_path)
    required = {"subject_id", "segment_id", "task_type", "audio_path", "binary_label", "file_valid"}
    missing = required - set(manifest.columns)
    if missing:
        raise ValueError(f"MODMA manifest missing columns: {', '.join(sorted(missing))}")
    valid_audio = bool_series(manifest["file_valid"])
    invalid_audio_rows = int((~valid_audio & manifest["audio_path"].notna()).sum())
    rows = manifest[
        valid_audio
        & manifest["audio_path"].notna()
        & manifest["binary_label"].notna()
        & manifest["task_type"].isin(MODMA_TASKS)
    ].copy()
    if rows.empty:
        raise ValueError("no usable MODMA audio rows")
    rows = rows.sort_values(["subject_id", "task_type", "segment_id"]).reset_index(drop=True)
    rows["subject_id"] = rows["subject_id"].astype(str)
    rows["task_type"] = rows["task_type"].astype(str)
    rows["segment_key"] = rows.apply(
        lambda row: "::".join([str(row["subject_id"]), str(row["task_type"]), str(row["segment_id"])]),
        axis=1,
    )
    task_counts = rows.groupby(["subject_id", "task_type"]).size().unstack(fill_value=0)
    missing_task_subjects = task_counts[(task_counts == 0).any(axis=1)]
    if not missing_task_subjects.empty:
        raise ValueError(f"MODMA subjects missing required task rows: {missing_task_subjects.head().to_dict()}")
    return rows.reset_index(drop=True), invalid_audio_rows


def aggregate_modma_subject_task(segment_features: pd.DataFrame) -> pd.DataFrame:
    columns = feature_columns(segment_features.drop(columns=["segment_key"], errors="ignore"))
    rows: list[dict[str, Any]] = []
    for (subject_id, task_type), group in segment_features.groupby(["subject_id", "task_type"], sort=True):
        labels = group["binary_label"].dropna().astype(int).unique()
        if len(labels) != 1:
            raise ValueError(f"MODMA subject={subject_id} task={task_type} has inconsistent labels")
        values = group[columns].to_numpy(dtype=np.float64)
        with np.errstate(invalid="ignore"):
            stats = {
                "mean": np.nanmean(values, axis=0),
                "std": np.nanstd(values, axis=0),
                "min": np.nanmin(values, axis=0),
                "max": np.nanmax(values, axis=0),
            }
        row: dict[str, Any] = {
            "subject_id": str(subject_id),
            "task_type": str(task_type),
            "binary_label": int(labels[0]),
            "audio_segment_count": int(len(group)),
        }
        for stat_name, stat_values in stats.items():
            for column, value in zip(columns, stat_values, strict=True):
                row[f"{column}__{stat_name}"] = float(value) if np.isfinite(value) else np.nan
        rows.append(row)
    return pd.DataFrame(rows).sort_values(["subject_id", "task_type"]).reset_index(drop=True)


def load_modma_task_protocols(split_path: Path) -> dict[str, dict[str, Any]]:
    splits = read_csv(split_path)
    required = {"dataset", "protocol_id", "protocol_type", "target", "fold", "role", "subject_id", "train_task", "eval_task"}
    missing = required - set(splits.columns)
    if missing:
        raise ValueError(f"split layer missing columns: {', '.join(sorted(missing))}")
    rows = splits[
        (splits["dataset"].astype(str) == "modma")
        & (splits["target"].astype(str) == "binary_label")
        & (splits["protocol_type"].isin(["task_specific", "cross_task"]))
    ].copy()
    if rows.empty:
        raise ValueError("no MODMA task-specific or cross-task split rows found")
    protocols: dict[str, dict[str, Any]] = {}
    for protocol_id, protocol_rows in rows.groupby("protocol_id", sort=False):
        train_tasks = sorted(protocol_rows["train_task"].dropna().astype(str).unique())
        eval_tasks = sorted(protocol_rows["eval_task"].dropna().astype(str).unique())
        if len(train_tasks) != 1 or len(eval_tasks) != 1:
            raise ValueError(f"{protocol_id} has ambiguous train/eval tasks")
        folds: dict[str, dict[str, list[str]]] = {}
        for fold, fold_rows in protocol_rows.groupby("fold", sort=False):
            roles: dict[str, list[str]] = {}
            for role, role_rows in fold_rows.groupby("role", sort=False):
                roles[str(role)] = sorted(
                    {modma_subject_id(subject_id) for subject_id in role_rows["subject_id"].astype(str)},
                    key=natural_key,
                )
            if set(roles.get("train", [])) & set(roles.get("validation", [])):
                raise ValueError(f"{protocol_id}:{fold} has train/validation subject overlap")
            if not roles.get("train") or not roles.get("validation"):
                raise ValueError(f"{protocol_id}:{fold} has empty train or validation role")
            folds[str(fold)] = roles
        protocols[str(protocol_id)] = {
            "protocol_id": str(protocol_id),
            "protocol_type": str(protocol_rows["protocol_type"].iloc[0]),
            "train_task": train_tasks[0],
            "eval_task": eval_tasks[0],
            "folds": dict(sorted(folds.items(), key=lambda item: natural_key(item[0]))),
        }
    return dict(sorted(protocols.items(), key=lambda item: natural_key(item[0])))


def run_modma_task_transfer(
    task_features: pd.DataFrame,
    protocols: dict[str, dict[str, Any]],
) -> tuple[pd.DataFrame, pd.DataFrame]:
    features = feature_columns(task_features)
    task_index = task_features.set_index(["subject_id", "task_type"], drop=False)
    predictions: list[dict[str, Any]] = []
    fold_rows: list[dict[str, Any]] = []
    for protocol_id, protocol in protocols.items():
        train_task = protocol["train_task"]
        eval_task = protocol["eval_task"]
        protocol_type = protocol["protocol_type"]
        if train_task not in MODMA_TASKS or eval_task not in MODMA_TASKS:
            raise ValueError(f"{protocol_id} has unsupported task pair: {train_task}->{eval_task}")
        for seed in SEEDS:
            for fold, roles in protocol["folds"].items():
                train_keys = [(subject_id, train_task) for subject_id in roles["train"]]
                validation_keys = [(subject_id, eval_task) for subject_id in roles["validation"]]
                train = task_index.loc[train_keys].reset_index(drop=True)
                validation = task_index.loc[validation_keys].reset_index(drop=True)
                if set(train["subject_id"].astype(str)) & set(validation["subject_id"].astype(str)):
                    raise ValueError(f"{protocol_id}:{fold}:seed{seed} subject leakage detected")
                model = classifier_pipeline(seed)
                model.fit(train[features], train["binary_label"].astype(int))
                y_pred = model.predict(validation[features])
                y_score = model.predict_proba(validation[features])[:, 1]
                for idx, row in validation.iterrows():
                    predictions.append(
                        {
                            "run_id": "modma_binary_egemaps_task_transfer",
                            "dataset": "MODMA",
                            "modality": "Audio",
                            "task": "task-transfer binary depression classification",
                            "model": "eGeMAPS + fixed logistic regression",
                            "seed": int(seed),
                            "fold": str(fold),
                            "protocol_id": str(protocol_id),
                            "protocol_type": str(protocol_type),
                            "train_task": str(train_task),
                            "eval_task": str(eval_task),
                            "task_type": "binary_classification",
                            "subject_id": str(row["subject_id"]),
                            "split": "validation",
                            "audio_segment_count": int(row["audio_segment_count"]),
                            "y_true": int(row["binary_label"]),
                            "y_pred": int(y_pred[idx]),
                            "y_score": float(y_score[idx]),
                        }
                    )
                fold_rows.append(
                    {
                        "protocol_id": str(protocol_id),
                        "protocol_type": str(protocol_type),
                        "train_task": str(train_task),
                        "eval_task": str(eval_task),
                        "seed": int(seed),
                        "fold": str(fold),
                        "train_subjects": int(len(train)),
                        "validation_subjects": int(len(validation)),
                        "train_positive_subjects": int(train["binary_label"].astype(int).sum()),
                        "validation_positive_subjects": int(validation["binary_label"].astype(int).sum()),
                    }
                )
    return pd.DataFrame(predictions), pd.DataFrame(fold_rows)


def metric_records_by_group(
    frame: pd.DataFrame,
    *,
    seed_group_cols: list[str],
    summary_group_cols: list[str],
    bootstrap_resamples: int,
    seed: int,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    rows: list[dict[str, Any]] = []
    for key, group in frame.groupby(seed_group_cols, dropna=False, sort=False):
        if not isinstance(key, tuple):
            key = (key,)
        meta = dict(zip(seed_group_cols, key, strict=True))
        task_type = str(meta["task_type"])
        metrics = compute_metrics(group, task_type)
        for metric, value in metrics.items():
            ci_low, ci_high = bootstrap_metric(group, task_type, metric, bootstrap_resamples, seed)
            rows.append(
                {
                    **meta,
                    "metric": metric,
                    "value": value,
                    "ci95_low": ci_low,
                    "ci95_high": ci_high,
                    "sample_count": int(len(group)),
                }
            )
    by_seed = pd.DataFrame(rows)
    summary_rows: list[dict[str, Any]] = []
    grouping = summary_group_cols + ["metric"]
    for key, group in by_seed.groupby(grouping, dropna=False, sort=False):
        if not isinstance(key, tuple):
            key = (key,)
        meta = dict(zip(grouping, key, strict=True))
        values = [safe_float(value) for value in group["value"]]
        values = [float(value) for value in values if value is not None]
        ci_low_values = [safe_float(value) for value in group["ci95_low"]]
        ci_high_values = [safe_float(value) for value in group["ci95_high"]]
        sample_counts = [int(value) for value in group["sample_count"]]
        if not values:
            continue
        summary_rows.append(
            {
                **meta,
                "mean": safe_float(np.mean(values)),
                "std": safe_float(np.std(values, ddof=0)),
                "ci95_low": safe_float(np.mean([value for value in ci_low_values if value is not None]))
                if any(value is not None for value in ci_low_values)
                else None,
                "ci95_high": safe_float(np.mean([value for value in ci_high_values if value is not None]))
                if any(value is not None for value in ci_high_values)
                else None,
                "seed_count": int(len(values)),
                "sample_count_mean": safe_float(np.mean(sample_counts)) if sample_counts else None,
            }
        )
    return by_seed, pd.DataFrame(summary_rows)


def bootstrap_metric(
    frame: pd.DataFrame,
    task_type: str,
    metric: str,
    resamples: int,
    seed: int,
    unit_column: str = "subject_id",
) -> tuple[float | None, float | None]:
    if resamples <= 0 or frame.empty:
        return None, None
    rng = np.random.default_rng(seed)
    units = np.asarray(sorted(frame[unit_column].astype(str).dropna().unique(), key=natural_key))
    if units.size == 0:
        return None, None
    grouped = {unit: np.flatnonzero(frame[unit_column].astype(str).to_numpy() == unit) for unit in units}
    values: list[float] = []
    for _ in range(resamples):
        sampled_units = rng.choice(units, size=units.size, replace=True)
        sampled_indices = np.concatenate([grouped[unit] for unit in sampled_units])
        value = compute_metrics(frame.iloc[sampled_indices], task_type).get(metric)
        if value is not None:
            values.append(float(value))
    if not values:
        return None, None
    return safe_float(np.percentile(values, 2.5)), safe_float(np.percentile(values, 97.5))


def bootstrap_metric_delta(
    within: pd.DataFrame,
    cross: pd.DataFrame,
    metric: str,
    resamples: int,
    seed: int,
) -> tuple[float | None, float | None]:
    if resamples <= 0 or within.empty or cross.empty:
        return None, None
    within_subjects = set(within["subject_id"].astype(str))
    cross_subjects = set(cross["subject_id"].astype(str))
    units = np.asarray(sorted(within_subjects & cross_subjects, key=natural_key))
    if units.size == 0:
        return None, None
    within = within[within["subject_id"].astype(str).isin(units)].reset_index(drop=True)
    cross = cross[cross["subject_id"].astype(str).isin(units)].reset_index(drop=True)
    within_grouped = {unit: np.flatnonzero(within["subject_id"].astype(str).to_numpy() == unit) for unit in units}
    cross_grouped = {unit: np.flatnonzero(cross["subject_id"].astype(str).to_numpy() == unit) for unit in units}
    rng = np.random.default_rng(seed)
    values: list[float] = []
    for _ in range(resamples):
        sampled_units = rng.choice(units, size=units.size, replace=True)
        within_indices = np.concatenate([within_grouped[unit] for unit in sampled_units])
        cross_indices = np.concatenate([cross_grouped[unit] for unit in sampled_units])
        within_value = compute_metrics(within.iloc[within_indices], "binary_classification").get(metric)
        cross_value = compute_metrics(cross.iloc[cross_indices], "binary_classification").get(metric)
        if within_value is not None and cross_value is not None:
            values.append(float(within_value) - float(cross_value))
    if not values:
        return None, None
    return safe_float(np.percentile(values, 2.5)), safe_float(np.percentile(values, 97.5))


def build_modma_matrix(summary: pd.DataFrame) -> pd.DataFrame:
    keep = summary[summary["metric"].isin(["Macro-F1", "Balanced Accuracy", "AUROC", "AUPRC"])].copy()
    return keep.sort_values(["metric", "train_task", "eval_task"]).reset_index(drop=True)


def summarize_modma_drops(
    predictions: pd.DataFrame,
    metrics_by_seed: pd.DataFrame,
    *,
    bootstrap_resamples: int,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    by_seed_index: dict[tuple[Any, ...], float] = {}
    for _, row in metrics_by_seed.iterrows():
        key = (
            int(row["seed"]),
            str(row["protocol_type"]),
            str(row["train_task"]),
            str(row["eval_task"]),
            str(row["metric"]),
        )
        value = safe_float(row["value"])
        if value is not None:
            by_seed_index[key] = float(value)

    rows: list[dict[str, Any]] = []
    cross_metrics = metrics_by_seed[
        (metrics_by_seed["protocol_type"] == "cross_task")
        & (metrics_by_seed["metric"].isin(["Macro-F1", "Balanced Accuracy", "AUROC", "AUPRC"]))
    ].copy()
    for _, cross_row in cross_metrics.iterrows():
        seed = int(cross_row["seed"])
        train_task = str(cross_row["train_task"])
        eval_task = str(cross_row["eval_task"])
        metric = str(cross_row["metric"])
        cross_value = safe_float(cross_row["value"])
        within_value = by_seed_index.get((seed, "task_specific", eval_task, eval_task, metric))
        if within_value is None or cross_value is None:
            continue
        within_frame = predictions[
            (predictions["seed"] == seed)
            & (predictions["protocol_type"] == "task_specific")
            & (predictions["train_task"] == eval_task)
            & (predictions["eval_task"] == eval_task)
        ]
        cross_frame = predictions[
            (predictions["seed"] == seed)
            & (predictions["protocol_type"] == "cross_task")
            & (predictions["train_task"] == train_task)
            & (predictions["eval_task"] == eval_task)
        ]
        ci_low, ci_high = bootstrap_metric_delta(
            within_frame,
            cross_frame,
            metric,
            bootstrap_resamples,
            BOOTSTRAP_SEED + seed + len(rows),
        )
        rows.append(
            {
                "seed": seed,
                "train_task": train_task,
                "eval_task": eval_task,
                "metric": metric,
                "within_value": float(within_value),
                "cross_value": float(cross_value),
                "drop": float(within_value) - float(cross_value),
                "drop_ci95_low": ci_low,
                "drop_ci95_high": ci_high,
            }
        )
    drops = pd.DataFrame(rows)
    summary_rows: list[dict[str, Any]] = []
    for metric, group in drops.groupby("metric", sort=False):
        summary_rows.append(modma_drop_summary_row("overall", "", str(metric), group))
    for (eval_task, metric), group in drops.groupby(["eval_task", "metric"], sort=False):
        summary_rows.append(modma_drop_summary_row("eval_task", str(eval_task), str(metric), group))
    return drops.sort_values(["metric", "eval_task", "train_task", "seed"]).reset_index(drop=True), pd.DataFrame(summary_rows)


def modma_drop_summary_row(scope: str, eval_task: str, metric: str, group: pd.DataFrame) -> dict[str, Any]:
    drops = group["drop"].astype(float).to_numpy()
    low_values = [safe_float(value) for value in group["drop_ci95_low"]]
    high_values = [safe_float(value) for value in group["drop_ci95_high"]]
    return {
        "scope": scope,
        "eval_task": eval_task,
        "metric": metric,
        "within_mean": safe_float(group["within_value"].astype(float).mean()),
        "cross_mean": safe_float(group["cross_value"].astype(float).mean()),
        "drop_mean": safe_float(np.mean(drops)) if drops.size else None,
        "drop_std": safe_float(np.std(drops, ddof=0)) if drops.size else None,
        "ci95_low": safe_float(np.mean([value for value in low_values if value is not None]))
        if any(value is not None for value in low_values)
        else None,
        "ci95_high": safe_float(np.mean([value for value in high_values if value is not None]))
        if any(value is not None for value in high_values)
        else None,
        "seed_pair_count": int(len(group)),
    }


def build_eatd_segment_table(manifest_path: Path) -> pd.DataFrame:
    manifest = read_csv(manifest_path)
    required = {"subject_id", "valence", "audio_path", "sds_total", "binary_label", "official_split", "file_valid"}
    missing = required - set(manifest.columns)
    if missing:
        raise ValueError(f"EATD manifest missing columns: {', '.join(sorted(missing))}")
    usable = manifest[
        bool_series(manifest["file_valid"])
        & manifest["audio_path"].notna()
        & manifest["sds_total"].notna()
        & manifest["binary_label"].notna()
        & manifest["official_split"].isin(["train", "validation"])
        & manifest["valence"].isin(EATD_VALENCES)
    ].copy()
    rows: list[dict[str, Any]] = []
    for subject_id, group in usable.groupby("subject_id", sort=True):
        by_valence = {str(row["valence"]): row for _, row in group.iterrows()}
        missing_valences = [valence for valence in EATD_VALENCES if valence not in by_valence]
        if missing_valences:
            raise ValueError(f"EATD subject={subject_id} missing valences: {missing_valences}")
        labels = group["binary_label"].dropna().astype(int).unique()
        sds_values = group["sds_total"].dropna().astype(float).unique()
        splits = group["official_split"].dropna().astype(str).unique()
        if len(labels) != 1 or len(sds_values) != 1 or len(splits) != 1:
            raise ValueError(f"EATD subject={subject_id} has inconsistent labels or split")
        for valence in EATD_VALENCES:
            source = by_valence[valence]
            rows.append(
                {
                    "subject_id": str(subject_id),
                    "split": str(splits[0]),
                    "valence": valence,
                    "binary_label": int(labels[0]),
                    "sds_total": float(sds_values[0]),
                    "audio_path": str(source["audio_path"]),
                }
            )
    table = pd.DataFrame(rows).sort_values(["subject_id", "valence"]).reset_index(drop=True)
    train_subjects = set(table.loc[table["split"] == "train", "subject_id"].astype(str))
    validation_subjects = set(table.loc[table["split"] == "validation", "subject_id"].astype(str))
    if train_subjects & validation_subjects:
        raise ValueError("EATD official split has subject overlap")
    if not train_subjects or not validation_subjects:
        raise ValueError("EATD official split requires non-empty train and validation subjects")
    return table


def run_eatd_valence_models(valence_features: pd.DataFrame) -> pd.DataFrame:
    features = feature_columns(valence_features)
    train = valence_features[valence_features["split"] == "train"].reset_index(drop=True)
    validation = valence_features[valence_features["split"] == "validation"].reset_index(drop=True)
    if set(train["subject_id"].astype(str)) & set(validation["subject_id"].astype(str)):
        raise ValueError("EATD train/validation subject leakage detected")
    predictions: list[dict[str, Any]] = []
    for seed in SEEDS:
        classifier = classifier_pipeline(seed)
        classifier.fit(train[features], train["binary_label"].astype(int))
        class_pred = classifier.predict(validation[features])
        class_score = classifier.predict_proba(validation[features])[:, 1]

        svr = svr_pipeline()
        svr.fit(train[features], train["sds_total"].to_numpy(dtype=np.float64))
        sds_pred = svr.predict(validation[features])

        ridge = ridge_pipeline()
        ridge.fit(train[features], train["sds_total"].to_numpy(dtype=np.float64))
        ridge_pred = ridge.predict(validation[features])

        for idx, row in validation.iterrows():
            base = {
                "dataset": "EATD-Corpus",
                "modality": "Audio",
                "seed": int(seed),
                "subject_id": str(row["subject_id"]),
                "split": "validation",
                "valence": str(row["valence"]),
            }
            predictions.append(
                {
                    **base,
                    "run_id": "eatd_binary_egemaps_valence_sensitivity",
                    "task": "valence-specific binary depression classification",
                    "model": "eGeMAPS + fixed logistic regression",
                    "task_type": "binary_classification",
                    "target": "binary_label",
                    "y_true": int(row["binary_label"]),
                    "y_pred": int(class_pred[idx]),
                    "y_score": float(class_score[idx]),
                }
            )
            predictions.append(
                {
                    **base,
                    "run_id": "eatd_sds_egemaps_valence_sensitivity",
                    "task": "valence-specific SDS regression",
                    "model": "eGeMAPS + fixed RBF SVR",
                    "task_type": "severity_regression",
                    "target": "sds_total",
                    "y_true": float(row["sds_total"]),
                    "y_pred": float(sds_pred[idx]),
                    "y_score": "",
                }
            )
            predictions.append(
                {
                    **base,
                    "run_id": "eatd_sds_egemaps_valence_linear_sensitivity",
                    "task": "valence-specific SDS regression",
                    "model": "eGeMAPS + fixed ridge regression",
                    "task_type": "severity_regression",
                    "target": "sds_total",
                    "y_true": float(row["sds_total"]),
                    "y_pred": float(ridge_pred[idx]),
                    "y_score": "",
                }
            )
    return pd.DataFrame(predictions)


def build_eatd_stability(predictions: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for (run_id, seed, subject_id), group in predictions.groupby(["run_id", "seed", "subject_id"], sort=True):
        by_valence = {str(row["valence"]): row for _, row in group.iterrows()}
        missing = [valence for valence in EATD_VALENCES if valence not in by_valence]
        if missing:
            continue
        task_type = str(group["task_type"].iloc[0])
        target = str(group["target"].iloc[0])
        values: dict[str, float] = {}
        for valence in EATD_VALENCES:
            row = by_valence[valence]
            values[valence] = float(row["y_score"] if task_type == "binary_classification" else row["y_pred"])
        arr = np.asarray([values[valence] for valence in EATD_VALENCES], dtype=np.float64)
        label = int(float(group["y_true"].iloc[0])) if target == "binary_label" else None
        binary_label_values = predictions[
            (predictions["run_id"] == "eatd_binary_egemaps_valence_sensitivity")
            & (predictions["seed"] == seed)
            & (predictions["subject_id"] == subject_id)
        ]["y_true"].dropna()
        binary_label = int(float(binary_label_values.iloc[0])) if not binary_label_values.empty else label
        sds_values = predictions[
            (predictions["target"] == "sds_total")
            & (predictions["seed"] == seed)
            & (predictions["subject_id"] == subject_id)
        ]["y_true"].dropna()
        rows.append(
            {
                "run_id": str(run_id),
                "target": target,
                "seed": int(seed),
                "subject_id": str(subject_id),
                "binary_label": binary_label,
                "label_group": "depressed" if binary_label == 1 else "healthy",
                "sds_total": float(sds_values.iloc[0]) if not sds_values.empty else "",
                "positive_prediction": values["positive"],
                "neutral_prediction": values["neutral"],
                "negative_prediction": values["negative"],
                "prediction_std": safe_float(np.std(arr, ddof=0)),
                "prediction_range": safe_float(np.max(arr) - np.min(arr)),
                "negative_minus_positive": values["negative"] - values["positive"],
                "negative_minus_neutral": values["negative"] - values["neutral"],
                "negative_minus_nonnegative_mean": values["negative"] - float(np.mean([values["positive"], values["neutral"]])),
                "negative_is_highest": bool(values["negative"] >= values["positive"] and values["negative"] >= values["neutral"]),
            }
        )
    return pd.DataFrame(rows).sort_values(["run_id", "seed", "subject_id"]).reset_index(drop=True)


def bootstrap_statistic(
    frame: pd.DataFrame,
    statistic: Callable[[pd.DataFrame], float | None],
    *,
    resamples: int,
    seed: int,
    unit_column: str = "subject_id",
) -> tuple[float | None, float | None]:
    if resamples <= 0 or frame.empty:
        return None, None
    units = np.asarray(sorted(frame[unit_column].astype(str).dropna().unique(), key=natural_key))
    if units.size == 0:
        return None, None
    grouped = {unit: np.flatnonzero(frame[unit_column].astype(str).to_numpy() == unit) for unit in units}
    rng = np.random.default_rng(seed)
    values: list[float] = []
    for _ in range(resamples):
        sampled_units = rng.choice(units, size=units.size, replace=True)
        indices = np.concatenate([grouped[unit] for unit in sampled_units])
        value = statistic(frame.iloc[indices])
        if value is not None and math.isfinite(float(value)):
            values.append(float(value))
    if not values:
        return None, None
    return safe_float(np.percentile(values, 2.5)), safe_float(np.percentile(values, 97.5))


def summarize_eatd_stability(stability: pd.DataFrame, *, bootstrap_resamples: int) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for (run_id, label_group), group in stability.groupby(["run_id", "label_group"], sort=False):
        for metric_name, statistic in [
            ("prediction_std_mean", lambda frame: float(frame["prediction_std"].mean())),
            (
                "negative_minus_nonnegative_mean",
                lambda frame: float(frame["negative_minus_nonnegative_mean"].mean()),
            ),
            ("negative_highest_rate", lambda frame: float(frame["negative_is_highest"].astype(float).mean())),
        ]:
            ci_low, ci_high = bootstrap_statistic(
                group,
                statistic,
                resamples=bootstrap_resamples,
                seed=BOOTSTRAP_SEED + len(rows),
            )
            rows.append(
                {
                    "run_id": str(run_id),
                    "label_group": str(label_group),
                    "metric": metric_name,
                    "mean": safe_float(statistic(group)),
                    "ci95_low": ci_low,
                    "ci95_high": ci_high,
                    "subject_count": int(group["subject_id"].nunique()),
                    "subject_seed_count": int(len(group)),
                }
            )
    for run_id, group in stability.groupby("run_id", sort=False):
        for metric_name, statistic in [
            ("prediction_std_mean", lambda frame: float(frame["prediction_std"].mean())),
            (
                "negative_minus_nonnegative_mean",
                lambda frame: float(frame["negative_minus_nonnegative_mean"].mean()),
            ),
            ("negative_highest_rate", lambda frame: float(frame["negative_is_highest"].astype(float).mean())),
        ]:
            ci_low, ci_high = bootstrap_statistic(
                group,
                statistic,
                resamples=bootstrap_resamples,
                seed=BOOTSTRAP_SEED + len(rows),
            )
            rows.append(
                {
                    "run_id": str(run_id),
                    "label_group": "all",
                    "metric": metric_name,
                    "mean": safe_float(statistic(group)),
                    "ci95_low": ci_low,
                    "ci95_high": ci_high,
                    "subject_count": int(group["subject_id"].nunique()),
                    "subject_seed_count": int(len(group)),
                }
            )
    return pd.DataFrame(rows)


def build_eatd_confusion_risk(stability: pd.DataFrame, *, bootstrap_resamples: int) -> tuple[pd.DataFrame, pd.DataFrame]:
    binary = stability[stability["run_id"] == "eatd_binary_egemaps_valence_sensitivity"].copy()
    healthy = binary[binary["binary_label"] == 0].copy()
    depressed = binary[binary["binary_label"] == 1].copy()
    seed_rows: list[dict[str, Any]] = []
    for seed, group in healthy.groupby("seed", sort=True):
        seed_rows.append(
            {
                "seed": int(seed),
                "healthy_subjects": int(group["subject_id"].nunique()),
                "healthy_negative_mean_score": safe_float(group["negative_prediction"].mean()),
                "healthy_positive_mean_score": safe_float(group["positive_prediction"].mean()),
                "healthy_neutral_mean_score": safe_float(group["neutral_prediction"].mean()),
                "healthy_negative_minus_nonnegative_mean": safe_float(group["negative_minus_nonnegative_mean"].mean()),
                "healthy_negative_highest_rate": safe_float(group["negative_is_highest"].astype(float).mean()),
                "healthy_negative_predicted_depressed_rate": safe_float((group["negative_prediction"] >= 0.5).astype(float).mean()),
                "healthy_positive_predicted_depressed_rate": safe_float((group["positive_prediction"] >= 0.5).astype(float).mean()),
                "healthy_neutral_predicted_depressed_rate": safe_float((group["neutral_prediction"] >= 0.5).astype(float).mean()),
                "depressed_negative_mean_score": safe_float(
                    depressed.loc[depressed["seed"] == seed, "negative_prediction"].mean()
                ),
                "depressed_neutral_mean_score": safe_float(
                    depressed.loc[depressed["seed"] == seed, "neutral_prediction"].mean()
                ),
            }
        )
    summary_stats = [
        ("healthy_negative_mean_score", lambda frame: float(frame["negative_prediction"].mean())),
        ("healthy_negative_minus_nonnegative_mean", lambda frame: float(frame["negative_minus_nonnegative_mean"].mean())),
        ("healthy_negative_highest_rate", lambda frame: float(frame["negative_is_highest"].astype(float).mean())),
        (
            "healthy_negative_predicted_depressed_rate",
            lambda frame: float((frame["negative_prediction"] >= 0.5).astype(float).mean()),
        ),
        (
            "healthy_nonnegative_predicted_depressed_rate",
            lambda frame: float(
                np.mean(
                    np.concatenate(
                        [
                            (frame["positive_prediction"].to_numpy(dtype=np.float64) >= 0.5).astype(float),
                            (frame["neutral_prediction"].to_numpy(dtype=np.float64) >= 0.5).astype(float),
                        ]
                    )
                )
            ),
        ),
    ]
    summary_rows: list[dict[str, Any]] = []
    for metric, statistic in summary_stats:
        ci_low, ci_high = bootstrap_statistic(
            healthy,
            statistic,
            resamples=bootstrap_resamples,
            seed=BOOTSTRAP_SEED + len(summary_rows),
        )
        summary_rows.append(
            {
                "metric": metric,
                "mean": safe_float(statistic(healthy)) if not healthy.empty else None,
                "ci95_low": ci_low,
                "ci95_high": ci_high,
                "subject_count": int(healthy["subject_id"].nunique()),
                "subject_seed_count": int(len(healthy)),
            }
        )
    return pd.DataFrame(seed_rows), pd.DataFrame(summary_rows)


def write_report(out_dir: Path, summary: dict[str, Any]) -> None:
    modma_drop = summary["modma_drop_balanced_accuracy"]
    eatd_risk = summary["eatd_healthy_negative_confusion"]
    lines = [
        "# Phase 3 Task And Valence Diagnostics",
        "",
        f"Generated: `{summary['generated_at']}`",
        "",
        "## Protocol",
        "",
        "- MODMA: task-specific and cross-task binary classification over subject-task eGeMAPS aggregates.",
        "- EATD: valence-specific binary and SDS prediction over positive, neutral, and negative eGeMAPS rows.",
        "- Splits: existing subject-level Phase 2 MODMA split layer and EATD official train/validation subjects.",
        "- Seeds: five fixed seeds (`0, 1, 2, 3, 4`).",
        f"- Bootstrap: `{summary['bootstrap_resamples']}` subject-level resamples for metric and diagnostic intervals; rerun with `--bootstrap-resamples 1000` for tighter CIs.",
        "- Models: fixed simple heads only; no encoder fine-tuning and no new method design.",
        "- Formal artifacts omit raw text, raw audio, source audio/text paths, and file names.",
        "",
        "## MODMA Result Snapshot",
        "",
        f"- Tasks evaluated: `{summary['modma_tasks']}`.",
        f"- Manifest-invalid audio rows excluded before modeling: `{summary.get('modma_manifest_invalid_audio_rows_excluded', 0)}`.",
        f"- Overall Balanced Accuracy within-task mean: `{modma_drop['within_mean']}`.",
        f"- Overall Balanced Accuracy cross-task mean: `{modma_drop['cross_mean']}`.",
        f"- Overall Balanced Accuracy drop: `{modma_drop['drop_mean']}` with CI `{modma_drop['ci95_low']}` to `{modma_drop['ci95_high']}`.",
        "",
        "## EATD Result Snapshot",
        "",
        f"- Validation subjects: `{summary['eatd_validation_subjects']}`.",
        f"- Healthy negative mean depressed-probability score: `{eatd_risk['healthy_negative_mean_score']}`.",
        f"- Healthy negative minus nonnegative mean score: `{eatd_risk['healthy_negative_minus_nonnegative_mean']}`.",
        f"- Healthy negative predicted-depressed rate: `{eatd_risk['healthy_negative_predicted_depressed_rate']}`.",
        "",
        "## Output Files",
        "",
        "- `modma_egemaps_segment_features.csv` (local-only feature cache; ignored by default)",
        "- `modma_egemaps_subject_task_features.csv` (local-only feature cache; ignored by default)",
        "- `modma_task_transfer_predictions.csv` (local-only row-level artifact; ignored by default)",
        "- `modma_task_transfer_metrics_by_seed.csv`",
        "- `modma_task_transfer_metric_summary.csv`",
        "- `modma_task_transfer_matrix.csv`",
        "- `modma_task_transfer_drops_by_seed.csv`",
        "- `modma_task_transfer_drop_summary.csv`",
        "- `eatd_egemaps_valence_features.csv` (local-only feature cache; ignored by default)",
        "- `eatd_valence_predictions.csv` (local-only row-level artifact; ignored by default)",
        "- `eatd_valence_metrics_by_seed.csv`",
        "- `eatd_valence_metric_summary.csv`",
        "- `eatd_valence_subject_stability.csv`",
        "- `eatd_valence_stability_summary.csv`",
        "- `eatd_healthy_negative_confusion_by_seed.csv`",
        "- `eatd_healthy_negative_confusion_summary.csv`",
        "- `phase3_task_valence_run_summary.json`",
        "- `artifact_hygiene_audit.json`",
    ]
    (out_dir / "phase3_task_valence_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def artifact_hygiene_audit(out_dir: Path) -> dict[str, Any]:
    scan_paths = [
        path
        for path in out_dir.glob("*")
        if path.is_file() and path.suffix in {".csv", ".json", ".md"} and path.name != "artifact_hygiene_audit.json"
    ]
    indicators = ["audio_path", "text_path", "video_path", "raw_root", "/datasets/", ".wav", ".mp3", ".txt"]
    violations: list[dict[str, Any]] = []
    for path in sorted(scan_paths):
        text = path.read_text(encoding="utf-8", errors="ignore")
        for indicator in indicators:
            if indicator in text:
                violations.append({"file": path.name, "indicator": indicator})
    audit = {
        "generated_at": utc_now(),
        "files_scanned": [path.name for path in sorted(scan_paths)],
        "violation_count": int(len(violations)),
        "violations": violations,
        "passed": len(violations) == 0,
    }
    (out_dir / "artifact_hygiene_audit.json").write_text(
        json.dumps(audit, indent=2, ensure_ascii=True, sort_keys=True),
        encoding="utf-8",
    )
    return audit


def scalar_from_summary(summary: pd.DataFrame, metric: str, column: str = "mean") -> float | None:
    rows = summary[summary["metric"] == metric]
    if rows.empty:
        return None
    return safe_float(rows.iloc[0][column])


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--modma-manifest", type=Path, default=DEFAULT_MODMA_MANIFEST)
    parser.add_argument("--eatd-manifest", type=Path, default=DEFAULT_EATD_MANIFEST)
    parser.add_argument("--split-path", type=Path, default=DEFAULT_SPLIT_PATH)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--bootstrap-resamples", type=int, default=200)
    parser.add_argument("--force-features", action="store_true")
    parser.add_argument("--skip-modma", action="store_true")
    parser.add_argument("--skip-eatd", action="store_true")
    args = parser.parse_args()

    args.out_dir.mkdir(parents=True, exist_ok=True)

    summary: dict[str, Any] = {
        "generated_at": utc_now(),
        "worktree_root": ".",
        "modma_manifest": relpath(args.modma_manifest),
        "eatd_manifest": relpath(args.eatd_manifest),
        "split_path": relpath(args.split_path),
        "out_dir": relpath(args.out_dir),
        "seeds": SEEDS,
        "seed_count": len(SEEDS),
        "bootstrap_resamples": int(args.bootstrap_resamples),
        "feature_set": "openSMILE eGeMAPSv02 Functionals",
        "opensmile_version": str(opensmile.__version__),
        "raw_audio_written": False,
        "source_paths_written": False,
        "no_test_split_used": True,
        "models": [
            "eGeMAPS + fixed logistic regression",
            "eGeMAPS + fixed RBF SVR",
            "eGeMAPS + fixed ridge regression",
        ],
    }

    if not args.skip_modma:
        modma_segments, modma_manifest_invalid_rows = build_modma_segment_table(args.modma_manifest)
        modma_segment_features, modma_skipped_segments = extract_egemaps(
            modma_segments,
            cache_path=args.out_dir / "modma_egemaps_segment_features.csv",
            key_columns=["subject_id", "task_type", "segment_key"],
            meta_columns=["subject_id", "task_type", "segment_key", "binary_label"],
            force=args.force_features,
            progress_label="modma",
        )
        modma_task_features = aggregate_modma_subject_task(modma_segment_features)
        modma_task_features.to_csv(args.out_dir / "modma_egemaps_subject_task_features.csv", index=False)
        modma_protocols = load_modma_task_protocols(args.split_path)
        modma_predictions, modma_fold_summary = run_modma_task_transfer(modma_task_features, modma_protocols)
        modma_predictions.to_csv(args.out_dir / "modma_task_transfer_predictions.csv", index=False)
        modma_fold_summary.to_csv(args.out_dir / "modma_task_transfer_fold_summary.csv", index=False)
        modma_seed_cols = [
            "run_id",
            "dataset",
            "modality",
            "task",
            "model",
            "seed",
            "protocol_type",
            "train_task",
            "eval_task",
            "task_type",
        ]
        modma_summary_cols = [column for column in modma_seed_cols if column != "seed"]
        modma_metrics_by_seed, modma_metric_summary = metric_records_by_group(
            modma_predictions,
            seed_group_cols=modma_seed_cols,
            summary_group_cols=modma_summary_cols,
            bootstrap_resamples=args.bootstrap_resamples,
            seed=BOOTSTRAP_SEED,
        )
        modma_metrics_by_seed.to_csv(args.out_dir / "modma_task_transfer_metrics_by_seed.csv", index=False)
        modma_metric_summary.to_csv(args.out_dir / "modma_task_transfer_metric_summary.csv", index=False)
        modma_matrix = build_modma_matrix(modma_metric_summary)
        modma_matrix.to_csv(args.out_dir / "modma_task_transfer_matrix.csv", index=False)
        modma_drops, modma_drop_summary = summarize_modma_drops(
            modma_predictions,
            modma_metrics_by_seed,
            bootstrap_resamples=args.bootstrap_resamples,
        )
        modma_drops.to_csv(args.out_dir / "modma_task_transfer_drops_by_seed.csv", index=False)
        modma_drop_summary.to_csv(args.out_dir / "modma_task_transfer_drop_summary.csv", index=False)
        modma_drop_ba = modma_drop_summary[
            (modma_drop_summary["scope"] == "overall") & (modma_drop_summary["metric"] == "Balanced Accuracy")
        ].iloc[0]
        summary.update(
            {
                "modma_tasks": MODMA_TASKS,
                "modma_subjects": int(modma_task_features["subject_id"].nunique()),
                "modma_segments": int(len(modma_segments)),
                "modma_manifest_invalid_audio_rows_excluded": int(modma_manifest_invalid_rows),
                "modma_unreadable_segments_excluded": int(len(modma_skipped_segments)),
                "modma_feature_rows": int(len(modma_task_features)),
                "modma_protocols": int(len(modma_protocols)),
                "modma_prediction_rows": int(len(modma_predictions)),
                "modma_subject_overlap_detected": False,
                "modma_drop_balanced_accuracy": {
                    "within_mean": safe_float(modma_drop_ba["within_mean"]),
                    "cross_mean": safe_float(modma_drop_ba["cross_mean"]),
                    "drop_mean": safe_float(modma_drop_ba["drop_mean"]),
                    "ci95_low": safe_float(modma_drop_ba["ci95_low"]),
                    "ci95_high": safe_float(modma_drop_ba["ci95_high"]),
                },
            }
        )

    if not args.skip_eatd:
        eatd_segments = build_eatd_segment_table(args.eatd_manifest)
        eatd_features, eatd_skipped_segments = extract_egemaps(
            eatd_segments,
            cache_path=args.out_dir / "eatd_egemaps_valence_features.csv",
            key_columns=["subject_id", "valence"],
            meta_columns=["subject_id", "split", "valence", "binary_label", "sds_total"],
            force=args.force_features,
            progress_label="eatd",
        )
        eatd_predictions = run_eatd_valence_models(eatd_features)
        eatd_predictions.to_csv(args.out_dir / "eatd_valence_predictions.csv", index=False)
        eatd_seed_cols = [
            "run_id",
            "dataset",
            "modality",
            "task",
            "model",
            "seed",
            "target",
            "valence",
            "task_type",
        ]
        eatd_summary_cols = [column for column in eatd_seed_cols if column != "seed"]
        eatd_metrics_by_seed, eatd_metric_summary = metric_records_by_group(
            eatd_predictions,
            seed_group_cols=eatd_seed_cols,
            summary_group_cols=eatd_summary_cols,
            bootstrap_resamples=args.bootstrap_resamples,
            seed=BOOTSTRAP_SEED,
        )
        eatd_metrics_by_seed.to_csv(args.out_dir / "eatd_valence_metrics_by_seed.csv", index=False)
        eatd_metric_summary.to_csv(args.out_dir / "eatd_valence_metric_summary.csv", index=False)
        eatd_stability = build_eatd_stability(eatd_predictions)
        eatd_stability.to_csv(args.out_dir / "eatd_valence_subject_stability.csv", index=False)
        eatd_stability_summary = summarize_eatd_stability(
            eatd_stability,
            bootstrap_resamples=args.bootstrap_resamples,
        )
        eatd_stability_summary.to_csv(args.out_dir / "eatd_valence_stability_summary.csv", index=False)
        eatd_confusion_by_seed, eatd_confusion_summary = build_eatd_confusion_risk(
            eatd_stability,
            bootstrap_resamples=args.bootstrap_resamples,
        )
        eatd_confusion_by_seed.to_csv(args.out_dir / "eatd_healthy_negative_confusion_by_seed.csv", index=False)
        eatd_confusion_summary.to_csv(args.out_dir / "eatd_healthy_negative_confusion_summary.csv", index=False)
        validation_subjects = eatd_features.loc[eatd_features["split"] == "validation", "subject_id"].astype(str).nunique()
        train_subjects = eatd_features.loc[eatd_features["split"] == "train", "subject_id"].astype(str).nunique()
        summary.update(
            {
                "eatd_train_subjects": int(train_subjects),
                "eatd_validation_subjects": int(validation_subjects),
                "eatd_segments": int(len(eatd_segments)),
                "eatd_unreadable_segments_excluded": int(len(eatd_skipped_segments)),
                "eatd_prediction_rows": int(len(eatd_predictions)),
                "eatd_subject_overlap_detected": False,
                "eatd_healthy_negative_confusion": {
                    row["metric"]: safe_float(row["mean"]) for _, row in eatd_confusion_summary.iterrows()
                },
            }
        )

    if "modma_drop_balanced_accuracy" not in summary:
        summary["modma_drop_balanced_accuracy"] = {
            "within_mean": None,
            "cross_mean": None,
            "drop_mean": None,
            "ci95_low": None,
            "ci95_high": None,
        }
        summary["modma_tasks"] = []
    if "eatd_healthy_negative_confusion" not in summary:
        summary["eatd_healthy_negative_confusion"] = {
            "healthy_negative_mean_score": None,
            "healthy_negative_minus_nonnegative_mean": None,
            "healthy_negative_predicted_depressed_rate": None,
        }
        summary["eatd_validation_subjects"] = 0

    (args.out_dir / "phase3_task_valence_run_summary.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=True, sort_keys=True),
        encoding="utf-8",
    )
    write_report(args.out_dir, summary)
    audit = artifact_hygiene_audit(args.out_dir)
    if not audit["passed"]:
        raise RuntimeError(f"artifact hygiene failed: {audit['violations'][:5]}")
    summary["artifact_hygiene_passed"] = True
    summary["local_only_artifacts"] = [
        "eatd_egemaps_valence_features.csv",
        "eatd_valence_predictions.csv",
        "modma_egemaps_segment_features.csv",
        "modma_egemaps_subject_task_features.csv",
        "modma_task_transfer_predictions.csv",
    ]
    (args.out_dir / "phase3_task_valence_run_summary.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=True, sort_keys=True),
        encoding="utf-8",
    )
    print(f"Wrote diagnostics to {args.out_dir}")
    print(f"Artifact hygiene passed for {audit['files_scanned'].__len__()} files")


if __name__ == "__main__":
    main()
