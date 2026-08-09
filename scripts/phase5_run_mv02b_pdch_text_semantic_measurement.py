#!/usr/bin/env python3
"""Run P5_MV02b PDCH HAMD text-semantic measurement audit.

This bounded Phase 5 variant asks whether manifest-governed PDCH clinical text
alone can support HAMD-17 total, item, and construct-proxy measurement. It reads
raw text only through the audited manifest, fits fold-local character hashing
Ridge heads, keeps every split subject-level, and writes only aggregate metrics
plus a local ignored row-level prediction file. It does not fine-tune encoders,
save vectorizers, export raw text, export source paths, or train a full method.
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
from sklearn.feature_extraction.text import HashingVectorizer
from sklearn.linear_model import Ridge
from sklearn.model_selection import GroupKFold
from sklearn.pipeline import Pipeline


SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from phase2_metrics import bootstrap_ci, regression_metrics, safe_float
from phase5_run_mv01_phq_bridge import natural_key
from phase5_run_mv02_hamd_auxiliary_bridge import (
    FOLD_COUNT,
    HAMD_CONSTRUCT_MAP,
    HAMD_KEYS,
    MISSING_ITEM_CODES,
    SEEDS,
    TOTAL_MAX,
    TOTAL_MIN,
    construct_values,
    load_hamd_labels,
    predict_item_means,
    stratified_pdch_folds,
    total_from_item_predictions,
)


WORKTREE_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT_DIR = (
    WORKTREE_ROOT
    / "analysis"
    / "phase5_minimal_validation"
    / "p5_mv02b_pdch_text_semantic_measurement"
)
DEFAULT_MANIFEST_DIR = WORKTREE_ROOT / "datasets" / "manifests"
DEFAULT_MV02_MACRO_SUMMARY = (
    WORKTREE_ROOT
    / "analysis"
    / "phase5_minimal_validation"
    / "p5_mv02_hamd_auxiliary_bridge"
    / "macro_summary.csv"
)

RUN_ID = "P5_MV02b_pdch_text_semantic_measurement"
TRAIN_MEAN_TOTAL = "train_mean_total"
TRAIN_MEAN_ITEMS = "train_mean_items"
DIRECT_MODEL = "direct_total_ridge"
ITEM_MODEL = "itemwise_ridge"
FEATURE_SUBJECT_CONCAT = "text_char_hash_subject_concat"
FEATURE_SEGMENT_MEAN = "text_char_hash_segment_mean"

RIDGE_ALPHA_GRID = [100.0]
BOOTSTRAP_RESAMPLES = 200
MIN_TOTAL_MAE_IMPROVEMENT = 0.10
MIN_MACRO_ITEM_MAE_IMPROVEMENT = 0.01
TEXT_HASH_FEATURES = 4096
TEXT_NGRAM_RANGE = (2, 3)
INNER_CV_MAX_SPLITS = 3


@dataclass(frozen=True)
class TextTables:
    subjects: pd.DataFrame
    segments: pd.DataFrame
    text_audit: pd.DataFrame


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


def nonempty(value: Any) -> bool:
    text = str(value).strip()
    return text not in {"", "nan", "NaN", "None", "null", "<NA>"}


def read_text_local(path_value: Any) -> str:
    if not nonempty(path_value):
        return ""
    path = Path(str(path_value))
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8", errors="ignore")


def load_pdch_text_tables(manifest_dir: Path) -> TextTables:
    labels = load_hamd_labels(manifest_dir, "pdch")
    manifest_path = manifest_dir / "pdch_subjects.csv"
    manifest = read_csv(manifest_path, dtype={"subject_id": str, "segment_id": str})
    required = {"subject_id", "segment_id", "text_path", "file_valid", "hamd17_total", "hamd17_items"}
    missing = required - set(manifest.columns)
    if missing:
        raise ValueError(f"PDCH manifest missing columns: {', '.join(sorted(missing))}")

    usable = manifest[
        bool_series(manifest["file_valid"])
        & manifest["subject_id"].notna()
        & manifest["text_path"].map(nonempty)
    ].copy()
    usable["subject_id"] = usable["subject_id"].astype(str)
    usable["segment_id"] = usable["segment_id"].astype(str)
    usable = usable.merge(labels, on="subject_id", how="inner", suffixes=("", "_label"), validate="many_to_one")
    if usable.empty:
        raise ValueError("no usable PDCH text rows with HAMD labels")

    segment_rows: list[dict[str, Any]] = []
    audit_rows: list[dict[str, Any]] = []
    for _, row in usable.iterrows():
        text = read_text_local(row["text_path"])
        text_present = bool(text.strip())
        segment_rows.append(
            {
                "dataset": "pdch",
                "subject_id": str(row["subject_id"]),
                "segment_id": str(row["segment_id"]),
                "text": text,
                "text_present": text_present,
                "text_char_count": int(len(text)),
                "text_token_proxy_count": int(len(text.split())),
                "hamd17_total": float(row["hamd17_total_label"] if "hamd17_total_label" in row else row["hamd17_total"]),
                "severity_bin": str(row["severity_bin"]),
                "contains_hamd_code_9": bool(row["contains_hamd_code_9"]),
                **{key: safe_float(row[key]) for key in HAMD_KEYS},
            }
        )
        audit_rows.append(
            {
                "dataset": "pdch",
                "audit_type": "segment_text_access",
                "subject_id_exported": False,
                "manifest_rows": 1,
                "text_declared": True,
                "text_existing": bool(Path(str(row["text_path"])).exists()),
                "text_present": text_present,
                "text_char_count": int(len(text)),
                "text_token_proxy_count": int(len(text.split())),
            }
        )

    segments = pd.DataFrame(segment_rows)
    if not segments["text_present"].all():
        missing_count = int((~segments["text_present"]).sum())
        raise ValueError(f"PDCH text rows with empty/missing text: {missing_count}")

    subject_rows: list[dict[str, Any]] = []
    for subject_id, group in segments.groupby("subject_id", sort=True):
        ordered = group.sort_values("segment_id", key=lambda s: s.map(lambda x: tuple(natural_key(x))))
        first = ordered.iloc[0]
        subject_rows.append(
            {
                "dataset": "pdch",
                "subject_id": str(subject_id),
                "text": "\n".join(ordered["text"].astype(str).tolist()),
                "segment_count": int(len(ordered)),
                "text_char_count": int(ordered["text_char_count"].sum()),
                "text_token_proxy_count": int(ordered["text_token_proxy_count"].sum()),
                "hamd17_total": float(first["hamd17_total"]),
                "severity_bin": str(first["severity_bin"]),
                "contains_hamd_code_9": bool(first["contains_hamd_code_9"]),
                **{key: safe_float(first[key]) for key in HAMD_KEYS},
            }
        )
    subjects = pd.DataFrame(subject_rows).sort_values(
        "subject_id", key=lambda s: s.map(lambda x: tuple(natural_key(x)))
    ).reset_index(drop=True)
    if subjects["subject_id"].duplicated().any():
        raise ValueError("duplicate subject rows in PDCH text table")
    if subjects["subject_id"].nunique() != labels["subject_id"].nunique():
        raise ValueError("PDCH text coverage does not match HAMD label coverage")

    audit = pd.DataFrame(audit_rows)
    text_audit_rows = [
        {
            "dataset": "pdch",
            "audit_type": "subject_text_coverage",
            "hamd_subjects": int(labels["subject_id"].nunique()),
            "text_subjects": int(subjects["subject_id"].nunique()),
            "text_segments": int(len(segments)),
            "min_segments_per_subject": int(subjects["segment_count"].min()),
            "max_segments_per_subject": int(subjects["segment_count"].max()),
            "mean_segments_per_subject": safe_float(subjects["segment_count"].mean()),
            "median_text_chars_per_subject": safe_float(subjects["text_char_count"].median()),
            "raw_text_written": False,
            "source_paths_written": False,
        },
        {
            "dataset": "pdch",
            "audit_type": "segment_text_coverage",
            "hamd_subjects": "",
            "text_subjects": int(segments["subject_id"].nunique()),
            "text_segments": int(len(segments)),
            "min_segments_per_subject": "",
            "max_segments_per_subject": "",
            "mean_segments_per_subject": "",
            "median_text_chars_per_subject": safe_float(segments["text_char_count"].median()),
            "raw_text_written": False,
            "source_paths_written": False,
        },
    ]
    text_audit = pd.concat([pd.DataFrame(text_audit_rows), aggregate_text_audit(audit)], ignore_index=True)
    return TextTables(subjects=subjects, segments=segments.reset_index(drop=True), text_audit=text_audit)


def aggregate_text_audit(audit: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for key, group in audit.groupby(["dataset", "audit_type"], sort=False):
        dataset, audit_type = key
        rows.append(
            {
                "dataset": dataset,
                "audit_type": f"{audit_type}_aggregate",
                "hamd_subjects": "",
                "text_subjects": "",
                "text_segments": int(len(group)),
                "min_segments_per_subject": "",
                "max_segments_per_subject": "",
                "mean_segments_per_subject": "",
                "median_text_chars_per_subject": safe_float(group["text_char_count"].median()),
                "text_existing_rows": int(group["text_existing"].sum()),
                "text_present_rows": int(group["text_present"].sum()),
                "raw_text_written": False,
                "source_paths_written": False,
            }
        )
    return pd.DataFrame(rows)


def make_vectorizer() -> HashingVectorizer:
    return HashingVectorizer(
        analyzer="char",
        ngram_range=TEXT_NGRAM_RANGE,
        n_features=TEXT_HASH_FEATURES,
        lowercase=False,
        norm="l2",
        alternate_sign=False,
    )


def text_pipeline(alpha: float) -> Pipeline:
    return Pipeline(
        [
            ("hash", make_vectorizer()),
            ("ridge", Ridge(alpha=float(alpha), solver="lsqr")),
        ]
    )


def finite_target_mask(y: np.ndarray) -> np.ndarray:
    if y.ndim == 2:
        return np.all(np.isfinite(y), axis=1)
    return np.isfinite(y)


def choose_alpha(
    texts: list[str],
    y: np.ndarray,
    groups: Iterable[Any],
    sample_weight: np.ndarray | None,
) -> float:
    if len(RIDGE_ALPHA_GRID) == 1:
        return float(RIDGE_ALPHA_GRID[0])
    y_arr = np.asarray(y, dtype=float)
    mask = finite_target_mask(y_arr)
    texts_arr = np.asarray(texts, dtype=object)[mask]
    y_arr = y_arr[mask]
    groups_arr = np.asarray([str(group) for group in groups], dtype=object)[mask]
    weights_arr = np.asarray(sample_weight, dtype=float)[mask] if sample_weight is not None else None
    unique_groups = np.unique(groups_arr)
    if len(unique_groups) < 10:
        return 100.0
    n_splits = min(INNER_CV_MAX_SPLITS, max(2, len(unique_groups) // 12))
    splitter = GroupKFold(n_splits=n_splits)
    best_alpha = RIDGE_ALPHA_GRID[0]
    best_mae = float("inf")
    for alpha in RIDGE_ALPHA_GRID:
        scores: list[float] = []
        for train_idx, dev_idx in splitter.split(texts_arr, y_arr, groups=groups_arr):
            model = text_pipeline(alpha)
            fit_kwargs: dict[str, Any] = {}
            if weights_arr is not None:
                fit_kwargs["ridge__sample_weight"] = weights_arr[train_idx]
            model.fit(texts_arr[train_idx].tolist(), y_arr[train_idx], **fit_kwargs)
            pred = np.asarray(model.predict(texts_arr[dev_idx].tolist()), dtype=float)
            pred = np.clip(pred, TOTAL_MIN, TOTAL_MAX)
            scores.append(float(np.nanmean(np.abs(pred - y_arr[dev_idx]))))
        score = float(np.mean(scores))
        if score < best_mae:
            best_mae = score
            best_alpha = alpha
    return float(best_alpha)


def segment_weights(frame: pd.DataFrame) -> np.ndarray:
    counts = frame.groupby("subject_id")["segment_id"].transform("count").to_numpy(dtype=float)
    counts[counts <= 0.0] = 1.0
    return 1.0 / counts


def item_bounds(train_subjects: pd.DataFrame) -> dict[str, tuple[float, float]]:
    bounds: dict[str, tuple[float, float]] = {}
    for key in HAMD_KEYS:
        values = pd.to_numeric(train_subjects[key], errors="coerce").dropna()
        if values.empty:
            bounds[key] = (0.0, 4.0)
        else:
            bounds[key] = (0.0, max(1.0, float(values.max())))
    return bounds


def fit_text_direct(
    train: pd.DataFrame,
    eval_frame: pd.DataFrame,
    sample_weight: np.ndarray | None,
) -> tuple[np.ndarray, dict[str, Any]]:
    train_texts = train["text"].astype(str).tolist()
    eval_texts = eval_frame["text"].astype(str).tolist()
    y_train = train["hamd17_total"].to_numpy(dtype=float)
    alpha = choose_alpha(train_texts, y_train, train["subject_id"], sample_weight)
    vectorizer = make_vectorizer()
    x_train = vectorizer.transform(train_texts)
    x_eval = vectorizer.transform(eval_texts)
    model = Ridge(alpha=float(alpha), solver="lsqr")
    if sample_weight is not None:
        model.fit(x_train, y_train, sample_weight=sample_weight)
    else:
        model.fit(x_train, y_train)
    pred = np.clip(np.asarray(model.predict(x_eval), dtype=float).reshape(-1), TOTAL_MIN, TOTAL_MAX)
    return pred, {
        "selected_alpha": alpha,
        "feature_count": int(TEXT_HASH_FEATURES),
    }


def fit_text_items(
    train: pd.DataFrame,
    eval_frame: pd.DataFrame,
    train_subjects: pd.DataFrame,
    sample_weight: np.ndarray | None,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    train_texts_all = train["text"].astype(str).tolist()
    weights_all = np.asarray(sample_weight, dtype=float) if sample_weight is not None else None
    complete = train.dropna(subset=HAMD_KEYS).copy()
    if len(complete) >= 12:
        complete_weights = weights_all[complete.index.to_numpy(dtype=int)] if weights_all is not None else None
        shared_alpha = choose_alpha(
            complete["text"].astype(str).tolist(),
            complete[HAMD_KEYS].to_numpy(dtype=float),
            complete["subject_id"],
            complete_weights,
        )
    else:
        shared_alpha = choose_alpha(train_texts_all, train["hamd17_total"].to_numpy(dtype=float), train["subject_id"], weights_all)

    eval_texts = eval_frame["text"].astype(str).tolist()
    vectorizer = make_vectorizer()
    x_train_all = vectorizer.transform(train_texts_all)
    x_eval = vectorizer.transform(eval_texts)
    bounds = item_bounds(train_subjects)
    predictions: dict[str, np.ndarray] = {}
    trained_items = 0
    for key in HAMD_KEYS:
        usable_mask = train[key].notna().to_numpy(dtype=bool)
        if not usable_mask.any():
            predictions[key] = np.repeat(0.0, len(eval_frame))
            continue
        usable_weights = weights_all[usable_mask] if weights_all is not None else None
        model = Ridge(alpha=float(shared_alpha), solver="lsqr")
        x_train = x_train_all[usable_mask]
        y_train = train.loc[usable_mask, key].to_numpy(dtype=float)
        if usable_weights is not None:
            model.fit(x_train, y_train, sample_weight=usable_weights)
        else:
            model.fit(x_train, y_train)
        lo, hi = bounds[key]
        predictions[key] = np.clip(np.asarray(model.predict(x_eval), dtype=float).reshape(-1), lo, hi)
        trained_items += 1
    return pd.DataFrame(predictions, index=eval_frame.index), {
        "selected_alpha": shared_alpha,
        "feature_count": int(TEXT_HASH_FEATURES),
        "trained_items": trained_items,
    }


def aggregate_segment_direct(eval_subjects: pd.DataFrame, eval_segments: pd.DataFrame, segment_pred: np.ndarray) -> np.ndarray:
    frame = eval_segments[["subject_id"]].copy()
    frame["y_pred"] = segment_pred
    pred_by_subject = frame.groupby("subject_id", sort=False)["y_pred"].mean()
    return np.asarray([pred_by_subject[str(subject_id)] for subject_id in eval_subjects["subject_id"].astype(str)], dtype=float)


def aggregate_segment_items(eval_subjects: pd.DataFrame, eval_segments: pd.DataFrame, segment_items: pd.DataFrame) -> pd.DataFrame:
    frame = pd.concat([eval_segments[["subject_id"]].reset_index(drop=True), segment_items[HAMD_KEYS].reset_index(drop=True)], axis=1)
    grouped = frame.groupby("subject_id", sort=False)[HAMD_KEYS].mean()
    rows = [grouped.loc[str(subject_id), HAMD_KEYS].to_dict() for subject_id in eval_subjects["subject_id"].astype(str)]
    return pd.DataFrame(rows, index=eval_subjects.index)


def rows_for_total(
    eval_subjects: pd.DataFrame,
    y_pred: np.ndarray,
    seed: int,
    fold_id: str,
    feature_space: str,
    model: str,
    target_family: str,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for idx, (_, row) in enumerate(eval_subjects.iterrows()):
        rows.append(
            {
                "run_id": RUN_ID,
                "dataset": "pdch",
                "eval_scope": "pdch_cv",
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


def rows_for_items(
    eval_subjects: pd.DataFrame,
    item_predictions: pd.DataFrame,
    seed: int,
    fold_id: str,
    feature_space: str,
    model: str,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    true_items = eval_subjects[HAMD_KEYS].reset_index(drop=True)
    pred_items = item_predictions[HAMD_KEYS].reset_index(drop=True)
    for row_idx, (_, row) in enumerate(eval_subjects.reset_index(drop=True).iterrows()):
        for key in HAMD_KEYS:
            y_true = safe_float(true_items.loc[row_idx, key])
            if y_true is None:
                continue
            pred = float(pred_items.loc[row_idx, key])
            rows.append(
                {
                    "run_id": RUN_ID,
                    "dataset": "pdch",
                    "eval_scope": "pdch_cv",
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


def rows_for_constructs(
    eval_subjects: pd.DataFrame,
    item_predictions: pd.DataFrame,
    seed: int,
    fold_id: str,
    feature_space: str,
    model: str,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    true_constructs = construct_values(eval_subjects[HAMD_KEYS]).reset_index(drop=True)
    pred_constructs = construct_values(item_predictions[HAMD_KEYS]).reset_index(drop=True)
    for row_idx, (_, row) in enumerate(eval_subjects.reset_index(drop=True).iterrows()):
        for construct_id in sorted(HAMD_CONSTRUCT_MAP, key=natural_key):
            y_true = safe_float(true_constructs.loc[row_idx, construct_id])
            if y_true is None:
                continue
            rows.append(
                {
                    "run_id": RUN_ID,
                    "dataset": "pdch",
                    "eval_scope": "pdch_cv",
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


def audit_row(
    seed: int,
    fold_id: str,
    feature_space: str,
    model: str,
    train_subjects: pd.DataFrame,
    eval_subjects: pd.DataFrame,
    selected_alpha: Any,
    feature_count: Any,
    row_grain: str,
) -> dict[str, Any]:
    train_set = set(train_subjects["subject_id"].astype(str))
    eval_set = set(eval_subjects["subject_id"].astype(str))
    return {
        "seed": int(seed),
        "fold_id": fold_id,
        "eval_scope": "pdch_cv",
        "feature_space": feature_space,
        "model": model,
        "row_grain": row_grain,
        "train_subjects": int(len(train_set)),
        "eval_subjects": int(len(eval_set)),
        "subject_overlap_count": int(len(train_set & eval_set)),
        "selected_alpha": selected_alpha,
        "feature_count": feature_count,
        "text_vectorizer": f"HashingVectorizer(analyzer=char, ngram_range={TEXT_NGRAM_RANGE}, n_features={TEXT_HASH_FEATURES})",
        "encoder_finetuning": False,
        "raw_text_read_from_manifest": True,
        "raw_text_written": False,
        "source_paths_written": False,
        "uses_eval_labels_for_hyperparameters": False,
    }


def run_cv(tables: TextTables) -> tuple[pd.DataFrame, pd.DataFrame]:
    prediction_frames: list[pd.DataFrame] = []
    audit_rows: list[dict[str, Any]] = []
    subjects = tables.subjects.reset_index(drop=True)
    segments = tables.segments.reset_index(drop=True)

    for seed in SEEDS:
        for fold_index, (train_idx, eval_idx) in enumerate(stratified_pdch_folds(subjects, seed)):
            fold_id = f"seed{seed}_fold{fold_index}"
            train_subjects = subjects.iloc[train_idx].reset_index(drop=True)
            eval_subjects = subjects.iloc[eval_idx].reset_index(drop=True)
            overlap = set(train_subjects["subject_id"].astype(str)) & set(eval_subjects["subject_id"].astype(str))
            if overlap:
                raise ValueError(f"PDCH text fold subject overlap: {sorted(overlap, key=natural_key)[:5]}")

            total_mean = np.repeat(float(train_subjects["hamd17_total"].mean()), len(eval_subjects))
            mean_item_pred = predict_item_means(train_subjects, eval_subjects)
            mean_item_total = total_from_item_predictions(mean_item_pred)
            rows = []
            rows.extend(rows_for_total(eval_subjects, total_mean, seed, fold_id, "none", TRAIN_MEAN_TOTAL, "hamd_total_direct"))
            rows.extend(rows_for_total(eval_subjects, mean_item_total, seed, fold_id, "none", TRAIN_MEAN_ITEMS, "hamd_total_from_items"))
            rows.extend(rows_for_items(eval_subjects, mean_item_pred, seed, fold_id, "none", TRAIN_MEAN_ITEMS))
            rows.extend(rows_for_constructs(eval_subjects, mean_item_pred, seed, fold_id, "none", TRAIN_MEAN_ITEMS))
            prediction_frames.append(pd.DataFrame(rows))
            audit_rows.extend(
                [
                    audit_row(seed, fold_id, "none", TRAIN_MEAN_TOTAL, train_subjects, eval_subjects, None, None, "subject"),
                    audit_row(seed, fold_id, "none", TRAIN_MEAN_ITEMS, train_subjects, eval_subjects, None, None, "subject"),
                ]
            )

            direct_pred, direct_detail = fit_text_direct(train_subjects, eval_subjects, None)
            item_pred, item_detail = fit_text_items(train_subjects, eval_subjects, train_subjects, None)
            item_total = total_from_item_predictions(item_pred)
            rows = []
            rows.extend(rows_for_total(eval_subjects, direct_pred, seed, fold_id, FEATURE_SUBJECT_CONCAT, DIRECT_MODEL, "hamd_total_direct"))
            rows.extend(rows_for_total(eval_subjects, item_total, seed, fold_id, FEATURE_SUBJECT_CONCAT, ITEM_MODEL, "hamd_total_from_items"))
            rows.extend(rows_for_items(eval_subjects, item_pred, seed, fold_id, FEATURE_SUBJECT_CONCAT, ITEM_MODEL))
            rows.extend(rows_for_constructs(eval_subjects, item_pred, seed, fold_id, FEATURE_SUBJECT_CONCAT, ITEM_MODEL))
            prediction_frames.append(pd.DataFrame(rows))
            audit_rows.extend(
                [
                    audit_row(
                        seed,
                        fold_id,
                        FEATURE_SUBJECT_CONCAT,
                        DIRECT_MODEL,
                        train_subjects,
                        eval_subjects,
                        direct_detail["selected_alpha"],
                        direct_detail["feature_count"],
                        "subject",
                    ),
                    audit_row(
                        seed,
                        fold_id,
                        FEATURE_SUBJECT_CONCAT,
                        ITEM_MODEL,
                        train_subjects,
                        eval_subjects,
                        item_detail["selected_alpha"],
                        item_detail["feature_count"],
                        "subject",
                    ),
                ]
            )

            train_ids = set(train_subjects["subject_id"].astype(str))
            eval_ids = set(eval_subjects["subject_id"].astype(str))
    return pd.concat(prediction_frames, ignore_index=True), pd.DataFrame(audit_rows)


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
                    "run_id": RUN_ID,
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
                    "summary_target": "macro_hamd_item_mae"
                    if target_family == "hamd_item"
                    else "macro_hamd_construct_proxy_mae",
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
        mean_total = values.get(("none", TRAIN_MEAN_TOTAL))
        mean_items = values.get(("none", TRAIN_MEAN_ITEMS))
        text_values = [
            (value, feature_space, model)
            for (feature_space, model), value in values.items()
            if safe_float(value) is not None and str(feature_space).startswith("text_")
        ]
        best_text = min(text_values, default=(None, None, None))
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
                    "delta_vs_train_mean": safe_float(current - baseline)
                    if current is not None and baseline is not None
                    else None,
                    "delta_vs_best_text": safe_float(current - best_text[0])
                    if current is not None and best_text[0] is not None
                    else None,
                    "best_text_feature": best_text[1],
                    "best_text_model": best_text[2],
                }
            )
    return pd.DataFrame(rows)


def load_mv02_reference(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame()
    reference = read_csv(path)
    selected = reference[
        (reference["eval_scope"] == "pdch_cv")
        & (reference["summary_target"].isin(["hamd_total_direct", "hamd_total_from_items", "macro_hamd_item_mae"]))
        & (reference["feature_space"].isin(["text_bge", "early_fusion_all", "none"]))
    ].copy()
    selected["reference_run_id"] = "P5_MV02_hamd17_auxiliary_bridge"
    return selected[
        [
            "reference_run_id",
            "eval_scope",
            "dataset",
            "feature_space",
            "model",
            "summary_target",
            "metric",
            "mean",
            "seed_count",
            "target_count",
        ]
    ]


def best_row(macro_summary: pd.DataFrame, summary_target: str, model: str | None = None, text_only: bool = False) -> pd.Series | None:
    subset = macro_summary[macro_summary["summary_target"] == summary_target].copy()
    if model is not None:
        subset = subset[subset["model"] == model]
    if text_only:
        subset = subset[subset["feature_space"].astype(str).str.startswith("text_")]
    subset = subset.dropna(subset=["mean"]).sort_values(["mean", "feature_space", "model"])
    if subset.empty:
        return None
    return subset.iloc[0]


def build_verdict(macro_summary: pd.DataFrame) -> tuple[dict[str, Any], str]:
    best_direct = best_row(macro_summary, "hamd_total_direct", DIRECT_MODEL, text_only=True)
    best_item_total = best_row(macro_summary, "hamd_total_from_items", ITEM_MODEL, text_only=True)
    best_item_macro = best_row(macro_summary, "macro_hamd_item_mae", ITEM_MODEL, text_only=True)
    train_total = best_row(macro_summary, "hamd_total_direct", TRAIN_MEAN_TOTAL)
    train_items = best_row(macro_summary, "hamd_total_from_items", TRAIN_MEAN_ITEMS)
    train_macro = best_row(macro_summary, "macro_hamd_item_mae", TRAIN_MEAN_ITEMS)

    direct_delta = (
        safe_float(float(best_direct["mean"]) - float(train_total["mean"]))
        if best_direct is not None and train_total is not None
        else None
    )
    item_total_delta = (
        safe_float(float(best_item_total["mean"]) - float(train_items["mean"]))
        if best_item_total is not None and train_items is not None
        else None
    )
    macro_delta = (
        safe_float(float(best_item_macro["mean"]) - float(train_macro["mean"]))
        if best_item_macro is not None and train_macro is not None
        else None
    )
    total_meaningful = item_total_delta is not None and item_total_delta <= -MIN_TOTAL_MAE_IMPROVEMENT
    macro_meaningful = macro_delta is not None and macro_delta <= -MIN_MACRO_ITEM_MAE_IMPROVEMENT
    direct_meaningful = direct_delta is not None and direct_delta <= -MIN_TOTAL_MAE_IMPROVEMENT

    if total_meaningful and macro_meaningful:
        status = "pass_pdch_text_measurement_diagnostic"
        short_read = (
            "PDCH manifest-governed text hashing gives a bounded positive measurement signal: item-derived HAMD total and macro item MAE both improve over train-mean floors by the predefined margins. Treat this as PDCH-only text measurement evidence, not cross-dataset HAMD generalization."
        )
    elif total_meaningful or direct_meaningful:
        status = "partial_pdch_text_total_signal"
        short_read = (
            "PDCH text hashing is runnable and improves HAMD total severity by a meaningful margin, but item-level measurement is not strong enough for a construct-level claim."
        )
    elif item_total_delta is not None and item_total_delta < 0.0:
        status = "blocked_weak_pdch_text_measurement_signal"
        short_read = (
            "PDCH text hashing is runnable but weak: the best item-derived HAMD total gain is below the predefined meaningful-improvement threshold. Keep it as a diagnostic result."
        )
    else:
        status = "blocked_no_pdch_text_measurement_gain"
        short_read = (
            "PDCH text hashing is runnable but does not beat the train-mean HAMD severity floor. Do not use this variant as positive HAMD text measurement evidence."
        )

    return {
        "pass_rule_status": status,
        "pass_rule_met": status == "pass_pdch_text_measurement_diagnostic",
        "best_text_direct_total_mae": safe_float(best_direct["mean"]) if best_direct is not None else None,
        "best_text_direct_total_feature": str(best_direct["feature_space"]) if best_direct is not None else None,
        "best_text_item_total_mae": safe_float(best_item_total["mean"]) if best_item_total is not None else None,
        "best_text_item_total_feature": str(best_item_total["feature_space"]) if best_item_total is not None else None,
        "best_text_macro_item_mae": safe_float(best_item_macro["mean"]) if best_item_macro is not None else None,
        "best_text_macro_item_feature": str(best_item_macro["feature_space"]) if best_item_macro is not None else None,
        "train_mean_total_mae": safe_float(train_total["mean"]) if train_total is not None else None,
        "train_mean_item_total_mae": safe_float(train_items["mean"]) if train_items is not None else None,
        "train_mean_macro_item_mae": safe_float(train_macro["mean"]) if train_macro is not None else None,
        "direct_total_delta_vs_train_mean": direct_delta,
        "item_total_delta_vs_train_mean": item_total_delta,
        "macro_item_delta_vs_train_mean": macro_delta,
        "min_total_mae_improvement": MIN_TOTAL_MAE_IMPROVEMENT,
        "min_macro_item_mae_improvement": MIN_MACRO_ITEM_MAE_IMPROVEMENT,
        "direct_total_meaningful": bool(direct_meaningful),
        "item_total_meaningful": bool(total_meaningful),
        "macro_item_meaningful": bool(macro_meaningful),
        "short_read": short_read,
    }, short_read


def feature_contract() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "feature_space": FEATURE_SUBJECT_CONCAT,
                "row_grain": "subject",
                "vectorizer": "char_2_3_hashing",
                "feature_count": TEXT_HASH_FEATURES,
                "ridge_alpha_selection": "fixed_train_only_alpha_100",
                "raw_text_read_from_manifest": True,
                "raw_text_written": False,
                "source_paths_written": False,
                "vectorizer_saved": False,
                "feature_matrix_saved": False,
            },
        ]
    )


def artifact_hygiene_audit(out_dir: Path) -> dict[str, Any]:
    forbidden_patterns = [
        r"/root/autodl-tmp/datasets/",
        r"\btext_path\b",
        r"\baudio_path\b",
        r"\bvideo_path\b",
        r"\bgait_path\b",
        r"\.wav\b",
        r"\.WAV\b",
        r"\.mp4\b",
        r"\.avi\b",
        r"raw prompt",
        r"raw response",
        r"source locator",
        r"local_text",
    ]
    violations: list[dict[str, Any]] = []
    files_checked = 0
    for path in sorted(out_dir.rglob("*")):
        if not path.is_file():
            continue
        if path.name.endswith("_local_predictions.csv"):
            continue
        if path.suffix.lower() not in {".csv", ".json", ".md"}:
            continue
        files_checked += 1
        text = path.read_text(encoding="utf-8", errors="ignore")
        for pattern in forbidden_patterns:
            if re.search(pattern, text, flags=re.IGNORECASE):
                violations.append({"file": str(path.relative_to(out_dir)), "pattern": pattern})
    return {
        "audit_id": "P5_MV02b_text_artifact_hygiene",
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


def report_rows(macro_summary: pd.DataFrame) -> pd.DataFrame:
    selected = macro_summary[
        macro_summary["summary_target"].isin(
            ["hamd_total_direct", "hamd_total_from_items", "macro_hamd_item_mae", "macro_hamd_construct_proxy_mae"]
        )
    ].copy()
    return selected.sort_values(["summary_target", "mean", "feature_space", "model"], key=lambda s: s.map(lambda x: tuple(natural_key(x))))


def write_report(
    out_dir: Path,
    run_summary: dict[str, Any],
    macro_summary: pd.DataFrame,
    comparison_summary: pd.DataFrame,
    mv02_reference: pd.DataFrame,
) -> None:
    rows = report_rows(macro_summary)
    verdict = run_summary["verdict"]
    lines = [
        "# P5_MV02b PDCH Text Semantic Measurement",
        "",
        f"Generated: `{run_summary['generated_at']}`",
        "",
        "## Scope",
        "",
            "This bounded variant tests whether PDCH clinical text, read only through the audited manifest, can support HAMD-17 total, item, and construct-proxy measurement with fold-local character hashing Ridge heads. It is a PDCH-only measurement audit, not a full method and not a cross-dataset HAMD generalization result.",
        "",
        "## Text And Split Contract",
        "",
        f"- PDCH HAMD text subjects: `{run_summary['label_contract']['pdch_hamd_text_subjects']}`.",
        f"- PDCH text segments: `{run_summary['label_contract']['pdch_text_segments']}`.",
        f"- PDCH HAMD code-9 subjects: `{run_summary['label_contract']['pdch_hamd_code_9_subjects']}`; code `9` is excluded from item training/evaluation and item-derived total scoring.",
        f"- Subject-overlap violations: `{run_summary['split_audit']['subject_overlap_violations']}`.",
        f"- Feature spaces: `{', '.join(run_summary['feature_contract']['feature_spaces'])}`.",
        f"- Ridge alpha policy: `{run_summary['model_contract']['ridge_alpha_policy']}`.",
        "",
        "## PDCH CV Summary",
        "",
        "| summary target | feature space | model | MAE | seed count | target count |",
        "| --- | --- | --- | ---: | ---: | ---: |",
    ]
    for _, row in rows.iterrows():
        lines.append(
            f"| {row['summary_target']} | {row['feature_space']} | {row['model']} | {format_value(row['mean'])} | {int(row['seed_count'])} | {int(row['target_count'])} |"
        )
    lines.extend(
        [
            "",
            "## Deltas",
            "",
            "Negative deltas are improvements in MAE.",
            "",
            "| summary target | feature space | model | delta vs train mean | delta vs best text |",
            "| --- | --- | --- | ---: | ---: |",
        ]
    )
    delta_rows = comparison_summary[
        comparison_summary["summary_target"].isin(["hamd_total_direct", "hamd_total_from_items", "macro_hamd_item_mae"])
    ].sort_values(["summary_target", "feature_space", "model"], key=lambda s: s.map(lambda x: tuple(natural_key(x))))
    for _, row in delta_rows.iterrows():
        lines.append(
            f"| {row['summary_target']} | {row['feature_space']} | {row['model']} | {format_value(row['delta_vs_train_mean'])} | {format_value(row['delta_vs_best_text'])} |"
        )

    if not mv02_reference.empty:
        lines.extend(
            [
                "",
                "## MV02 Reference",
                "",
                "These rows are references from the earlier frozen-feature MV02 run, not re-estimated in MV02b.",
                "",
                "| summary target | feature space | model | MAE |",
                "| --- | --- | --- | ---: |",
            ]
        )
        for _, row in mv02_reference.sort_values(["summary_target", "mean", "feature_space"]).iterrows():
            lines.append(f"| {row['summary_target']} | {row['feature_space']} | {row['model']} | {format_value(row['mean'])} |")

    lines.extend(
        [
            "",
            "## Verdict",
            "",
            f"- Pass-rule status: `{verdict['pass_rule_status']}`.",
            f"- Best text direct-total MAE: `{format_value(verdict['best_text_direct_total_mae'])}` from `{verdict['best_text_direct_total_feature']}`.",
            f"- Best text item-derived total MAE: `{format_value(verdict['best_text_item_total_mae'])}` from `{verdict['best_text_item_total_feature']}`.",
            f"- Best text macro item MAE: `{format_value(verdict['best_text_macro_item_mae'])}` from `{verdict['best_text_macro_item_feature']}`.",
            f"- Item-total delta vs train mean: `{format_value(verdict['item_total_delta_vs_train_mean'])}`.",
            f"- Macro-item delta vs train mean: `{format_value(verdict['macro_item_delta_vs_train_mean'])}`.",
            "",
            run_summary["interpretation"]["short_read"],
            "",
            "## Hygiene",
            "",
            f"- Artifact hygiene passed: `{run_summary['artifact_hygiene_passed']}`.",
            "- Row-level predictions are written as a local-only ignored CSV.",
            "- Raw clinical text, source paths, vectorizers, learned features, model weights, prompts, and responses are not written.",
        ]
    )
    (out_dir / "report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--manifest-dir", type=Path, default=DEFAULT_MANIFEST_DIR)
    parser.add_argument("--mv02-macro-summary", type=Path, default=DEFAULT_MV02_MACRO_SUMMARY)
    args = parser.parse_args()

    out_dir = args.out_dir
    if out_dir.exists():
        shutil.rmtree(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    tables = load_pdch_text_tables(args.manifest_dir)
    predictions, model_audit = run_cv(tables)
    metrics_by_seed, metric_summary = metric_tables(predictions)
    macro_summary = macro_summaries(metric_summary)
    comparison_summary = build_comparison_summary(macro_summary)
    mv02_reference = load_mv02_reference(args.mv02_macro_summary)
    verdict, short_read = build_verdict(macro_summary)

    metrics_by_seed.to_csv(out_dir / "metrics_by_seed.csv", index=False)
    metric_summary.to_csv(out_dir / "metric_summary.csv", index=False)
    macro_summary.to_csv(out_dir / "macro_summary.csv", index=False)
    comparison_summary.to_csv(out_dir / "comparison_summary.csv", index=False)
    model_audit.to_csv(out_dir / "model_split_audit.csv", index=False)
    tables.text_audit.to_csv(out_dir / "text_input_audit.csv", index=False)
    feature_contract().to_csv(out_dir / "feature_contract.csv", index=False)
    if not mv02_reference.empty:
        mv02_reference.to_csv(out_dir / "mv02_frozen_feature_reference.csv", index=False)
    pd.DataFrame(
        [
            {"construct_id": construct_id, "hamd_item_codes": ";".join(keys)}
            for construct_id, keys in sorted(HAMD_CONSTRUCT_MAP.items(), key=lambda item: natural_key(item[0]))
        ]
    ).to_csv(out_dir / "construct_proxy_map.csv", index=False)
    predictions.to_csv(out_dir / "p5_mv02b_local_predictions.csv", index=False)

    subject_overlap_violations = int(model_audit["subject_overlap_count"].sum())
    run_summary: dict[str, Any] = {
        "run_id": RUN_ID,
        "generated_at": utc_now(),
        "status": "complete",
        "scope": "pdch_only_manifest_text_hamd17_measurement_audit",
        "label_contract": {
            "pdch_hamd_text_subjects": int(tables.subjects["subject_id"].nunique()),
            "pdch_text_segments": int(len(tables.segments)),
            "pdch_hamd_code_9_subjects": int(tables.subjects["contains_hamd_code_9"].sum()),
            "hamd_code_9_policy": "exclude_from_item_training_and_total_scoring",
            "primary_total_target": "manifest_hamd17_total",
        },
        "feature_contract": {
            "feature_spaces": [FEATURE_SUBJECT_CONCAT],
            "new_feature_extraction": "in_memory_hashing_only",
            "raw_text_read_from_manifest": True,
            "raw_text_written": False,
            "source_paths_written": False,
            "vectorizer_saved": False,
            "feature_matrix_saved": False,
            "encoder_finetuning": False,
        },
        "model_contract": {
            "models": [TRAIN_MEAN_TOTAL, TRAIN_MEAN_ITEMS, DIRECT_MODEL, ITEM_MODEL],
            "seeds": SEEDS,
            "folds_per_seed": FOLD_COUNT,
            "inner_cv_for_alpha": False,
            "ridge_alpha_policy": "fixed_train_only_alpha_100",
            "eval_labels_for_hyperparameters": False,
        },
        "split_audit": {
            "subject_level_stratified_cv": True,
            "subject_overlap_violations": subject_overlap_violations,
        },
        "output_policy": {
            "row_level_predictions": "local_only_ignored",
            "raw_text": "not_written",
            "source_paths": "not_written",
            "learned_features": "not_written",
            "model_weights": "not_written",
            "raw_prompts_or_responses": "not_written",
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
            "text_input_audit.csv",
            "feature_contract.csv",
            "construct_proxy_map.csv",
            "mv02_frozen_feature_reference.csv",
        ],
        "local_only_files": ["p5_mv02b_local_predictions.csv"],
    }

    (out_dir / "run_summary.json").write_text(json.dumps(run_summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    write_report(out_dir, run_summary, macro_summary, comparison_summary, mv02_reference)
    hygiene = artifact_hygiene_audit(out_dir)
    run_summary["artifact_hygiene_passed"] = bool(hygiene["artifact_hygiene_passed"])
    (out_dir / "run_summary.json").write_text(json.dumps(run_summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    write_report(out_dir, run_summary, macro_summary, comparison_summary, mv02_reference)
    hygiene = artifact_hygiene_audit(out_dir)
    run_summary["artifact_hygiene_passed"] = bool(hygiene["artifact_hygiene_passed"])
    (out_dir / "run_summary.json").write_text(json.dumps(run_summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (out_dir / "artifact_hygiene_audit.json").write_text(json.dumps(hygiene, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    if not hygiene["artifact_hygiene_passed"]:
        raise SystemExit("artifact hygiene violations found; see artifact_hygiene_audit.json")
    print(f"Wrote P5_MV02b PDCH text semantic measurement artifacts to {out_dir.relative_to(WORKTREE_ROOT)}")


if __name__ == "__main__":
    main()
