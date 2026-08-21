#!/usr/bin/env python3
"""Run MV18 CMDC-HAMD versus PDCH-HAMD same-scale exploratory control.

This bounded Phase 5 diagnostic asks whether dataset/context differences remain
visible when language and target scale family are held closer: both CMDC and
PDCH are Chinese datasets with HAMD-17 item/total labels. CMDC has only a small
HAMD subset, so the output is exploratory. The script writes aggregate
label-shift, threshold-shift, and bidirectional transfer summaries plus a
local-only row-level prediction file.
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
import pandas as pd
from sklearn.model_selection import KFold, StratifiedKFold


SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from phase2_metrics import bootstrap_ci, regression_metrics, safe_float
from phase5_run_mv01_phq_bridge import natural_key
from phase5_run_mv02_hamd_auxiliary_bridge import (
    FOLD_COUNT,
    HAMD_CONSTRUCT_MAP,
    HAMD_KEYS,
    SEEDS,
    build_model_table,
    construct_values,
    fit_direct_total,
    fit_itemwise,
    load_feature_tables,
    load_hamd_labels,
    predict_item_means,
    total_from_item_predictions,
)


WORKTREE_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT_DIR = (
    WORKTREE_ROOT
    / "analysis"
    / "phase5_minimal_validation"
    / "p5_mv18_cmdc_pdch_hamd_same_scale_control"
)
DEFAULT_MANIFEST_DIR = WORKTREE_ROOT / "datasets" / "manifests"
DEFAULT_PHASE2_ROOT = WORKTREE_ROOT / "analysis" / "phase2_baselines"

RUN_ID = "P5_MV18_cmdc_pdch_hamd_same_scale_control"
LABEL_BOOTSTRAP_RESAMPLES = 500
MODEL_BOOTSTRAP_RESAMPLES = 0
OVERLAP_SEVERITY_BINS = {"mild", "moderate"}
MIN_CONDITIONAL_ITEM_DIFF = 0.30
MIN_THRESHOLD_RATE_DIFF = 0.20
MIN_TRANSFER_MAE_GAIN = 0.10
MIN_TRANSFER_DEGRADATION = 0.25


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def format_value(value: Any, digits: int = 3) -> str:
    numeric = safe_float(value)
    if numeric is None:
        return "NA"
    return f"{numeric:.{digits}f}"


def finite_mean(values: pd.Series) -> float | None:
    numeric = pd.to_numeric(values, errors="coerce").dropna()
    if numeric.empty:
        return None
    return safe_float(numeric.mean())


def finite_std(values: pd.Series) -> float | None:
    numeric = pd.to_numeric(values, errors="coerce").dropna()
    if numeric.size < 2:
        return None
    return safe_float(numeric.std(ddof=1))


def scope_mask(frame: pd.DataFrame, label_scope: str) -> pd.Series:
    if label_scope == "all_subjects":
        return pd.Series(True, index=frame.index)
    if label_scope == "overlap_mild_moderate":
        return frame["severity_bin"].astype(str).isin(OVERLAP_SEVERITY_BINS)
    raise ValueError(f"unknown label scope: {label_scope}")


def ci_excludes_zero(low: Any, high: Any) -> bool:
    ci_low = safe_float(low)
    ci_high = safe_float(high)
    return ci_low is not None and ci_high is not None and (ci_low > 0.0 or ci_high < 0.0)


def combine_labels(cmdc_labels: pd.DataFrame, pdch_labels: pd.DataFrame) -> pd.DataFrame:
    combined = pd.concat([cmdc_labels, pdch_labels], ignore_index=True)
    combined["dataset"] = combined["dataset"].astype(str)
    combined["subject_key"] = combined["dataset"] + "::" + combined["subject_id"].astype(str)
    return combined.sort_values(["dataset", "subject_id"], key=lambda s: s.map(lambda x: tuple(natural_key(x)))).reset_index(drop=True)


def label_scope_audit(combined: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for label_scope in ["all_subjects", "overlap_mild_moderate"]:
        scoped = combined[scope_mask(combined, label_scope)].copy()
        for dataset, group in scoped.groupby("dataset", sort=True):
            item_counts = [int(group[key].notna().sum()) for key in HAMD_KEYS]
            rows.append(
                {
                    "label_scope": label_scope,
                    "dataset": dataset,
                    "subject_count": int(group["subject_key"].nunique()),
                    "hamd_total_mean": finite_mean(group["hamd17_total"]),
                    "hamd_total_sd": finite_std(group["hamd17_total"]),
                    "hamd_total_min": safe_float(group["hamd17_total"].min()),
                    "hamd_total_median": safe_float(group["hamd17_total"].median()),
                    "hamd_total_max": safe_float(group["hamd17_total"].max()),
                    "severity_bin_counts": json.dumps(dict(sorted(Counter(group["severity_bin"]).items())), sort_keys=True),
                    "hamd_code_9_subjects": int(group["contains_hamd_code_9"].sum()),
                    "min_item_observed_subjects": int(min(item_counts)),
                    "max_item_observed_subjects": int(max(item_counts)),
                    "complete_item_subjects": int(group.dropna(subset=HAMD_KEYS)["subject_key"].nunique()),
                }
            )
    return pd.DataFrame(rows)


def item_distribution_summary(combined: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for label_scope in ["all_subjects", "overlap_mild_moderate"]:
        scoped = combined[scope_mask(combined, label_scope)].copy()
        for dataset, group in scoped.groupby("dataset", sort=True):
            for item in HAMD_KEYS:
                values = pd.to_numeric(group[item], errors="coerce").dropna()
                category_counts = {str(int(k)): int(v) for k, v in sorted(Counter(values.astype(int)).items())}
                rows.append(
                    {
                        "label_scope": label_scope,
                        "dataset": dataset,
                        "item_id": item,
                        "observed_subjects": int(values.size),
                        "mean": safe_float(values.mean()) if values.size else None,
                        "sd": safe_float(values.std(ddof=1)) if values.size > 1 else None,
                        "nonzero_rate": safe_float((values > 0.0).mean()) if values.size else None,
                        "min": safe_float(values.min()) if values.size else None,
                        "max": safe_float(values.max()) if values.size else None,
                        "category_counts": json.dumps(category_counts, sort_keys=True),
                    }
                )
    return pd.DataFrame(rows)


def stratified_bootstrap_ci(
    frame: pd.DataFrame,
    stat_fn: Callable[[pd.DataFrame], float | None],
    seed: int,
) -> tuple[float | None, float | None]:
    groups = [group.reset_index(drop=True) for _, group in frame.groupby("dataset", sort=True)]
    if len(groups) != 2 or any(group.empty for group in groups):
        return None, None
    rng = np.random.default_rng(seed)
    values: list[float] = []
    for _ in range(LABEL_BOOTSTRAP_RESAMPLES):
        sampled = pd.concat(
            [group.iloc[rng.integers(0, len(group), size=len(group))] for group in groups],
            ignore_index=True,
        )
        value = stat_fn(sampled)
        if value is not None:
            values.append(float(value))
    if not values:
        return None, None
    return safe_float(np.percentile(values, 2.5)), safe_float(np.percentile(values, 97.5))


def raw_item_mean_diff(frame: pd.DataFrame, item: str) -> float | None:
    values: dict[str, pd.Series] = {}
    for dataset in ["cmdc", "pdch"]:
        values[dataset] = pd.to_numeric(frame.loc[frame["dataset"] == dataset, item], errors="coerce").dropna()
    if values["cmdc"].empty or values["pdch"].empty:
        return None
    return safe_float(values["cmdc"].mean() - values["pdch"].mean())


def residualized_item_diff(frame: pd.DataFrame, item: str) -> float | None:
    data = frame[["dataset", "hamd17_total", item]].copy()
    data[item] = pd.to_numeric(data[item], errors="coerce")
    data["hamd17_total"] = pd.to_numeric(data["hamd17_total"], errors="coerce")
    data = data.dropna(subset=["dataset", "hamd17_total", item]).reset_index(drop=True)
    if data["dataset"].nunique() != 2 or len(data) < 6:
        return None
    data["total_excluding_item"] = data["hamd17_total"] - data[item]
    y = data[item].to_numpy(dtype=float)
    x = data["total_excluding_item"].to_numpy(dtype=float)
    if float(np.nanstd(x)) <= 1e-12:
        fitted = np.repeat(float(np.nanmean(y)), len(y))
    else:
        design = np.column_stack([np.ones(len(data), dtype=float), x])
        beta, *_ = np.linalg.lstsq(design, y, rcond=None)
        fitted = design @ beta
    data["residual"] = y - fitted
    means = data.groupby("dataset")["residual"].mean().to_dict()
    if "cmdc" not in means or "pdch" not in means:
        return None
    return safe_float(float(means["cmdc"]) - float(means["pdch"]))


def threshold_rate_diff(frame: pd.DataFrame, item: str, threshold: int) -> float | None:
    values: dict[str, pd.Series] = {}
    for dataset in ["cmdc", "pdch"]:
        values[dataset] = pd.to_numeric(frame.loc[frame["dataset"] == dataset, item], errors="coerce").dropna()
    if values["cmdc"].empty or values["pdch"].empty:
        return None
    return safe_float(float((values["cmdc"] >= threshold).mean()) - float((values["pdch"] >= threshold).mean()))


def item_shift_summary(combined: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for label_scope in ["all_subjects", "overlap_mild_moderate"]:
        scoped = combined[scope_mask(combined, label_scope)].copy()
        for item_index, item in enumerate(HAMD_KEYS):
            raw_diff = raw_item_mean_diff(scoped, item)
            raw_low, raw_high = stratified_bootstrap_ci(
                scoped[["dataset", item]].dropna(subset=[item]),
                lambda sample, item=item: raw_item_mean_diff(sample, item),
                seed=20260818 + item_index,
            )
            residual_diff = residualized_item_diff(scoped, item)
            residual_low, residual_high = stratified_bootstrap_ci(
                scoped[["dataset", "hamd17_total", item]].dropna(subset=[item]),
                lambda sample, item=item: residualized_item_diff(sample, item),
                seed=20260918 + item_index,
            )
            rows.append(
                {
                    "label_scope": label_scope,
                    "item_id": item,
                    "cmdc_observed_subjects": int(scoped.loc[scoped["dataset"] == "cmdc", item].notna().sum()),
                    "pdch_observed_subjects": int(scoped.loc[scoped["dataset"] == "pdch", item].notna().sum()),
                    "raw_mean_diff_cmdc_minus_pdch": raw_diff,
                    "raw_mean_diff_ci95_low": raw_low,
                    "raw_mean_diff_ci95_high": raw_high,
                    "residualized_diff_cmdc_minus_pdch": residual_diff,
                    "residualized_diff_ci95_low": residual_low,
                    "residualized_diff_ci95_high": residual_high,
                    "residualized_conditioning": "linear_total_excluding_item",
                    "flagged_residual_shift": bool(
                        residual_diff is not None
                        and abs(float(residual_diff)) >= MIN_CONDITIONAL_ITEM_DIFF
                        and ci_excludes_zero(residual_low, residual_high)
                    ),
                    "min_abs_residual_shift": MIN_CONDITIONAL_ITEM_DIFF,
                }
            )
    return pd.DataFrame(rows)


def threshold_shift_summary(combined: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for label_scope in ["all_subjects", "overlap_mild_moderate"]:
        scoped = combined[scope_mask(combined, label_scope)].copy()
        for item_index, item in enumerate(HAMD_KEYS):
            values = pd.to_numeric(scoped[item], errors="coerce").dropna()
            if values.empty:
                continue
            max_threshold = int(min(4, max(1, math.floor(float(values.max())))))
            for threshold in range(1, max_threshold + 1):
                diff = threshold_rate_diff(scoped, item, threshold)
                low, high = stratified_bootstrap_ci(
                    scoped[["dataset", item]].dropna(subset=[item]),
                    lambda sample, item=item, threshold=threshold: threshold_rate_diff(sample, item, threshold),
                    seed=20261018 + item_index * 10 + threshold,
                )
                cmdc_values = pd.to_numeric(scoped.loc[scoped["dataset"] == "cmdc", item], errors="coerce").dropna()
                pdch_values = pd.to_numeric(scoped.loc[scoped["dataset"] == "pdch", item], errors="coerce").dropna()
                rows.append(
                    {
                        "label_scope": label_scope,
                        "item_id": item,
                        "threshold": int(threshold),
                        "cmdc_observed_subjects": int(cmdc_values.size),
                        "pdch_observed_subjects": int(pdch_values.size),
                        "cmdc_rate_ge_threshold": safe_float((cmdc_values >= threshold).mean()) if cmdc_values.size else None,
                        "pdch_rate_ge_threshold": safe_float((pdch_values >= threshold).mean()) if pdch_values.size else None,
                        "rate_diff_cmdc_minus_pdch": diff,
                        "rate_diff_ci95_low": low,
                        "rate_diff_ci95_high": high,
                        "flagged_threshold_shift": bool(
                            diff is not None
                            and abs(float(diff)) >= MIN_THRESHOLD_RATE_DIFF
                            and ci_excludes_zero(low, high)
                        ),
                        "min_abs_rate_diff": MIN_THRESHOLD_RATE_DIFF,
                    }
                )
    return pd.DataFrame(rows)


def assert_feature_columns_match(pdch_cols: dict[str, list[str]], cmdc_cols: dict[str, list[str]]) -> None:
    for feature_space in ["text_bge", "audio_wavlm", "audio_egemaps", "early_fusion_all"]:
        pdch = pdch_cols[feature_space]
        cmdc = cmdc_cols[feature_space]
        if pdch != cmdc:
            raise ValueError(f"feature columns differ for {feature_space}")


def stratified_folds(table: pd.DataFrame, seed: int) -> list[tuple[np.ndarray, np.ndarray]]:
    y = table["severity_bin"].astype(str).to_numpy()
    counts = Counter(y)
    if len(table) >= FOLD_COUNT and min(counts.values()) >= FOLD_COUNT:
        splitter = StratifiedKFold(n_splits=FOLD_COUNT, shuffle=True, random_state=seed)
        return list(splitter.split(np.zeros(len(table)), y))
    splitter = KFold(n_splits=min(FOLD_COUNT, len(table)), shuffle=True, random_state=seed)
    return list(splitter.split(np.zeros(len(table))))


def prediction_rows_for_total(
    eval_frame: pd.DataFrame,
    y_pred: np.ndarray,
    seed: int,
    fold_id: str,
    train_scope: str,
    eval_scope: str,
    feature_space: str,
    model: str,
    target_family: str,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for idx, (_, row) in enumerate(eval_frame.iterrows()):
        rows.append(
            {
                "run_id": RUN_ID,
                "train_scope": train_scope,
                "eval_scope": eval_scope,
                "dataset": str(row["dataset"]),
                "feature_space": feature_space,
                "model": model,
                "seed": int(seed),
                "fold_id": fold_id,
                "task_type": "severity_regression",
                "target_family": target_family,
                "target_id": "HAMD17_total",
                "subject_id": str(row["subject_id"]),
                "subject_key": str(row["subject_key"]),
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
    train_scope: str,
    eval_scope: str,
    feature_space: str,
    model: str,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    true_items = eval_frame[HAMD_KEYS].reset_index(drop=True)
    pred_items = item_predictions[HAMD_KEYS].reset_index(drop=True)
    for row_idx, (_, row) in enumerate(eval_frame.reset_index(drop=True).iterrows()):
        for item in HAMD_KEYS:
            y_true = safe_float(true_items.loc[row_idx, item])
            if y_true is None:
                continue
            pred = float(pred_items.loc[row_idx, item])
            rows.append(
                {
                    "run_id": RUN_ID,
                    "train_scope": train_scope,
                    "eval_scope": eval_scope,
                    "dataset": str(row["dataset"]),
                    "feature_space": feature_space,
                    "model": model,
                    "seed": int(seed),
                    "fold_id": fold_id,
                    "task_type": "item_regression",
                    "target_family": "hamd_item",
                    "target_id": item,
                    "subject_id": str(row["subject_id"]),
                    "subject_key": str(row["subject_key"]),
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
    train_scope: str,
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
                    "run_id": RUN_ID,
                    "train_scope": train_scope,
                    "eval_scope": eval_scope,
                    "dataset": str(row["dataset"]),
                    "feature_space": feature_space,
                    "model": model,
                    "seed": int(seed),
                    "fold_id": fold_id,
                    "task_type": "construct_regression",
                    "target_family": "hamd_construct_proxy",
                    "target_id": construct_id,
                    "subject_id": str(row["subject_id"]),
                    "subject_key": str(row["subject_key"]),
                    "y_true": float(y_true),
                    "y_pred": float(pred_constructs.loc[row_idx, construct_id]),
                    "severity_bin": str(row["severity_bin"]),
                }
            )
    return rows


def summarize_item_alphas(item_alphas: dict[str, float]) -> str:
    values = [value for value in item_alphas.values() if safe_float(value) is not None]
    if not values:
        return ""
    counts = Counter(float(value) for value in values)
    return ";".join(f"{alpha:g}:{count}" for alpha, count in sorted(counts.items()))


def model_audit_row(
    seed: int,
    fold_id: str,
    train_scope: str,
    eval_scope: str,
    feature_space: str,
    model: str,
    train: pd.DataFrame,
    eval_frame: pd.DataFrame,
    selected_alpha: Any,
) -> dict[str, Any]:
    train_keys = set(train["subject_key"].astype(str))
    eval_keys = set(eval_frame["subject_key"].astype(str))
    return {
        "seed": int(seed),
        "fold_id": fold_id,
        "train_scope": train_scope,
        "eval_scope": eval_scope,
        "feature_space": feature_space,
        "model": model,
        "train_dataset": ";".join(sorted(train["dataset"].astype(str).unique())),
        "eval_dataset": ";".join(sorted(eval_frame["dataset"].astype(str).unique())),
        "train_subjects": int(len(train_keys)),
        "eval_subjects": int(len(eval_keys)),
        "subject_overlap_count": int(len(train_keys & eval_keys)),
        "selected_alpha": selected_alpha,
        "encoder_finetuning": False,
        "raw_data_scan": False,
        "uses_eval_labels_for_hyperparameters": False,
    }


def evaluate_once(
    train: pd.DataFrame,
    eval_frame: pd.DataFrame,
    feature_cols_by_space: dict[str, list[str]],
    seed: int,
    fold_id: str,
    train_scope: str,
    eval_scope: str,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    if set(train["subject_key"].astype(str)) & set(eval_frame["subject_key"].astype(str)):
        raise ValueError(f"subject overlap in {fold_id}")

    prediction_frames: list[pd.DataFrame] = []
    audit_rows: list[dict[str, Any]] = []

    total_mean = np.repeat(float(train["hamd17_total"].mean()), len(eval_frame))
    mean_item_pred = predict_item_means(train, eval_frame)
    mean_item_total = total_from_item_predictions(mean_item_pred)
    rows: list[dict[str, Any]] = []
    rows.extend(prediction_rows_for_total(eval_frame, total_mean, seed, fold_id, train_scope, eval_scope, "none", "train_mean_total", "hamd_total_direct"))
    rows.extend(prediction_rows_for_total(eval_frame, mean_item_total, seed, fold_id, train_scope, eval_scope, "none", "train_mean_items", "hamd_total_from_items"))
    rows.extend(prediction_rows_for_items(eval_frame, mean_item_pred, seed, fold_id, train_scope, eval_scope, "none", "train_mean_items"))
    rows.extend(prediction_rows_for_constructs(eval_frame, mean_item_pred, seed, fold_id, train_scope, eval_scope, "none", "train_mean_items"))
    prediction_frames.append(pd.DataFrame(rows))
    audit_rows.extend(
        [
            model_audit_row(seed, fold_id, train_scope, eval_scope, "none", "train_mean_total", train, eval_frame, None),
            model_audit_row(seed, fold_id, train_scope, eval_scope, "none", "train_mean_items", train, eval_frame, None),
        ]
    )

    for feature_space, feature_cols in feature_cols_by_space.items():
        direct_pred, total_alpha = fit_direct_total(train, eval_frame, feature_cols, seed)
        item_pred, item_alphas = fit_itemwise(train, eval_frame, feature_cols, seed)
        item_total = total_from_item_predictions(item_pred)
        rows = []
        rows.extend(
            prediction_rows_for_total(
                eval_frame,
                direct_pred,
                seed,
                fold_id,
                train_scope,
                eval_scope,
                feature_space,
                "direct_total_ridge",
                "hamd_total_direct",
            )
        )
        rows.extend(
            prediction_rows_for_total(
                eval_frame,
                item_total,
                seed,
                fold_id,
                train_scope,
                eval_scope,
                feature_space,
                "itemwise_ridge",
                "hamd_total_from_items",
            )
        )
        rows.extend(prediction_rows_for_items(eval_frame, item_pred, seed, fold_id, train_scope, eval_scope, feature_space, "itemwise_ridge"))
        rows.extend(prediction_rows_for_constructs(eval_frame, item_pred, seed, fold_id, train_scope, eval_scope, feature_space, "itemwise_ridge"))
        prediction_frames.append(pd.DataFrame(rows))
        audit_rows.extend(
            [
                model_audit_row(seed, fold_id, train_scope, eval_scope, feature_space, "direct_total_ridge", train, eval_frame, total_alpha),
                model_audit_row(seed, fold_id, train_scope, eval_scope, feature_space, "itemwise_ridge", train, eval_frame, summarize_item_alphas(item_alphas)),
            ]
        )

    return pd.concat(prediction_frames, ignore_index=True), pd.DataFrame(audit_rows)


def run_cv_scope(
    table: pd.DataFrame,
    feature_cols_by_space: dict[str, list[str]],
    eval_scope: str,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    prediction_frames: list[pd.DataFrame] = []
    audit_frames: list[pd.DataFrame] = []
    table = table.reset_index(drop=True)
    for seed in SEEDS:
        for fold_index, (train_idx, eval_idx) in enumerate(stratified_folds(table, seed)):
            train = table.iloc[train_idx].reset_index(drop=True)
            eval_frame = table.iloc[eval_idx].reset_index(drop=True)
            fold_id = f"{eval_scope}_seed{seed}_fold{fold_index}"
            predictions, audit = evaluate_once(train, eval_frame, feature_cols_by_space, seed, fold_id, eval_scope, eval_scope)
            prediction_frames.append(predictions)
            audit_frames.append(audit)
    return pd.concat(prediction_frames, ignore_index=True), pd.concat(audit_frames, ignore_index=True)


def run_cross_scope(
    train: pd.DataFrame,
    eval_frame: pd.DataFrame,
    feature_cols_by_space: dict[str, list[str]],
    train_scope: str,
    eval_scope: str,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    prediction_frames: list[pd.DataFrame] = []
    audit_frames: list[pd.DataFrame] = []
    train = train.reset_index(drop=True)
    eval_frame = eval_frame.reset_index(drop=True)
    for seed in SEEDS:
        fold_id = f"{train_scope}_to_{eval_scope}_seed{seed}"
        predictions, audit = evaluate_once(train, eval_frame, feature_cols_by_space, seed, fold_id, train_scope, eval_scope)
        prediction_frames.append(predictions)
        audit_frames.append(audit)
    return pd.concat(prediction_frames, ignore_index=True), pd.concat(audit_frames, ignore_index=True)


def run_transfer_diagnostics(
    pdch_table: pd.DataFrame,
    cmdc_table: pd.DataFrame,
    feature_cols_by_space: dict[str, list[str]],
) -> tuple[pd.DataFrame, pd.DataFrame]:
    pdch_all = pdch_table.reset_index(drop=True)
    pdch_overlap = pdch_table[pdch_table["severity_bin"].astype(str).isin(OVERLAP_SEVERITY_BINS)].reset_index(drop=True)
    cmdc_overlap = cmdc_table[cmdc_table["severity_bin"].astype(str).isin(OVERLAP_SEVERITY_BINS)].reset_index(drop=True)
    if cmdc_overlap.empty or pdch_overlap.empty:
        raise ValueError("empty HAMD overlap scope")

    jobs = [
        ("cv", pdch_all, pdch_all, "pdch_cv_all", "pdch_cv_all"),
        ("cv", pdch_overlap, pdch_overlap, "pdch_cv_overlap", "pdch_cv_overlap"),
        ("cv", cmdc_overlap, cmdc_overlap, "cmdc_cv_overlap", "cmdc_cv_overlap"),
        ("cross", pdch_all, cmdc_overlap, "pdch_all", "pdch_all_to_cmdc_overlap"),
        ("cross", pdch_overlap, cmdc_overlap, "pdch_overlap", "pdch_overlap_to_cmdc_overlap"),
        ("cross", cmdc_overlap, pdch_all, "cmdc_overlap", "cmdc_overlap_to_pdch_all"),
        ("cross", cmdc_overlap, pdch_overlap, "cmdc_overlap", "cmdc_overlap_to_pdch_overlap"),
    ]
    prediction_frames: list[pd.DataFrame] = []
    audit_frames: list[pd.DataFrame] = []
    for mode, train, eval_frame, train_scope, eval_scope in jobs:
        if mode == "cv":
            predictions, audit = run_cv_scope(eval_frame, feature_cols_by_space, eval_scope)
        else:
            predictions, audit = run_cross_scope(train, eval_frame, feature_cols_by_space, train_scope, eval_scope)
        prediction_frames.append(predictions)
        audit_frames.append(audit)
    return pd.concat(prediction_frames, ignore_index=True), pd.concat(audit_frames, ignore_index=True)


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
    group_cols = ["train_scope", "eval_scope", "dataset", "feature_space", "model", "target_family", "target_id", "seed"]
    for key, group in predictions.groupby(group_cols, sort=False, dropna=False):
        train_scope, eval_scope, dataset, feature_space, model, target_family, target_id, seed = key
        if target_family in {"hamd_total_direct", "hamd_total_from_items"}:
            metrics = regression_metrics(group["y_true"], group["y_pred"])
            task_type = "severity_regression"
        else:
            metrics = rounded_metrics(group)
            task_type = str(group["task_type"].iloc[0])
        for metric, value in metrics.items():
            ci_low, ci_high = None, None
            if MODEL_BOOTSTRAP_RESAMPLES > 0 and target_family in {"hamd_total_direct", "hamd_total_from_items"} and metric == "MAE":
                ci_low, ci_high = bootstrap_ci(
                    group,
                    "severity_regression",
                    "MAE",
                    MODEL_BOOTSTRAP_RESAMPLES,
                    seed=20261118 + int(seed),
                    unit_column="subject_key",
                )
            by_seed_rows.append(
                {
                    "run_id": RUN_ID,
                    "train_scope": train_scope,
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
                    "subject_count": int(group["subject_key"].nunique()),
                }
            )

    by_seed = pd.DataFrame(by_seed_rows)
    summary_rows: list[dict[str, Any]] = []
    group_cols = [
        "run_id",
        "train_scope",
        "eval_scope",
        "dataset",
        "feature_space",
        "model",
        "target_family",
        "target_id",
        "task_type",
        "metric",
    ]
    for key, group in by_seed.groupby(group_cols, sort=False, dropna=False):
        values = [safe_float(value) for value in group["value"]]
        values = [float(value) for value in values if value is not None]
        if not values:
            continue
        ci_low_values = [safe_float(value) for value in group["ci95_low"]]
        ci_high_values = [safe_float(value) for value in group["ci95_high"]]
        summary_rows.append(
            {
                **dict(zip(group_cols, key, strict=True)),
                "mean": safe_float(np.mean(values)),
                "std": safe_float(np.std(values, ddof=0)),
                "ci95_low": safe_float(np.mean([value for value in ci_low_values if value is not None]))
                if any(value is not None for value in ci_low_values)
                else None,
                "ci95_high": safe_float(np.mean([value for value in ci_high_values if value is not None]))
                if any(value is not None for value in ci_high_values)
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
    for key, group in selected.groupby(["train_scope", "eval_scope", "dataset", "feature_space", "model", "target_family"], sort=False):
        train_scope, eval_scope, dataset, feature_space, model, target_family = key
        if target_family in {"hamd_total_direct", "hamd_total_from_items"}:
            for _, row in group.iterrows():
                rows.append(
                    {
                        "train_scope": train_scope,
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
                    "train_scope": train_scope,
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


def transfer_comparison_summary(macro_summary: pd.DataFrame) -> pd.DataFrame:
    target_cv_scope = {
        "pdch_all_to_cmdc_overlap": "cmdc_cv_overlap",
        "pdch_overlap_to_cmdc_overlap": "cmdc_cv_overlap",
        "cmdc_overlap_to_pdch_all": "pdch_cv_all",
        "cmdc_overlap_to_pdch_overlap": "pdch_cv_overlap",
    }
    rows: list[dict[str, Any]] = []
    indexed = macro_summary.set_index(["eval_scope", "feature_space", "model", "summary_target"])["mean"].to_dict()
    for key, group in macro_summary.groupby(["train_scope", "eval_scope", "dataset", "summary_target"], sort=False):
        train_scope, eval_scope, dataset, summary_target = key
        values = group.set_index(["feature_space", "model"])["mean"].to_dict()
        baseline = values.get(("none", "train_mean_total" if summary_target == "hamd_total_direct" else "train_mean_items"))
        cv_scope = target_cv_scope.get(eval_scope)
        for _, row in group.iterrows():
            current = safe_float(row["mean"])
            cv_value = None
            if cv_scope is not None:
                cv_value = indexed.get((cv_scope, row["feature_space"], row["model"], summary_target))
            rows.append(
                {
                    "train_scope": train_scope,
                    "eval_scope": eval_scope,
                    "dataset": dataset,
                    "summary_target": summary_target,
                    "feature_space": row["feature_space"],
                    "model": row["model"],
                    "mae": current,
                    "delta_vs_source_train_mean": safe_float(current - baseline) if current is not None and baseline is not None else None,
                    "target_cv_scope": cv_scope or "",
                    "target_cv_same_feature_mae": safe_float(cv_value),
                    "delta_vs_target_cv_same_feature": safe_float(current - cv_value) if current is not None and safe_float(cv_value) is not None else None,
                }
            )
    return pd.DataFrame(rows)


def best_transfer_row(comparison: pd.DataFrame, eval_scope: str, summary_target: str) -> pd.Series | None:
    subset = comparison[
        (comparison["eval_scope"] == eval_scope)
        & (comparison["summary_target"] == summary_target)
        & (comparison["feature_space"] != "none")
        & (comparison["model"].isin(["direct_total_ridge", "itemwise_ridge"]))
    ].copy()
    subset = subset.dropna(subset=["mae"]).sort_values(["mae", "feature_space", "model"])
    if subset.empty:
        return None
    return subset.iloc[0]


def build_verdict(
    scope_audit: pd.DataFrame,
    item_shift: pd.DataFrame,
    threshold_shift: pd.DataFrame,
    comparison: pd.DataFrame,
) -> tuple[dict[str, Any], str]:
    overlap_items = item_shift[item_shift["label_scope"] == "overlap_mild_moderate"].copy()
    overlap_thresholds = threshold_shift[threshold_shift["label_scope"] == "overlap_mild_moderate"].copy()
    flagged_items = int(overlap_items["flagged_residual_shift"].sum())
    flagged_thresholds = int(overlap_thresholds["flagged_threshold_shift"].sum())

    primary_scopes = ["pdch_overlap_to_cmdc_overlap", "cmdc_overlap_to_pdch_overlap"]
    transfer_rows = [best_transfer_row(comparison, scope, "hamd_total_from_items") for scope in primary_scopes]
    transfer_rows = [row for row in transfer_rows if row is not None]
    weak_transfer = 0
    transfer_details: list[dict[str, Any]] = []
    for row in transfer_rows:
        delta_source = safe_float(row["delta_vs_source_train_mean"])
        delta_cv = safe_float(row["delta_vs_target_cv_same_feature"])
        beats_source_mean = delta_source is not None and delta_source <= -MIN_TRANSFER_MAE_GAIN
        worse_than_target_cv = delta_cv is not None and delta_cv >= MIN_TRANSFER_DEGRADATION
        if (not beats_source_mean) or worse_than_target_cv:
            weak_transfer += 1
        transfer_details.append(
            {
                "eval_scope": str(row["eval_scope"]),
                "feature_space": str(row["feature_space"]),
                "model": str(row["model"]),
                "mae": safe_float(row["mae"]),
                "delta_vs_source_train_mean": delta_source,
                "delta_vs_target_cv_same_feature": delta_cv,
                "beats_source_mean_by_min_gain": bool(beats_source_mean),
                "worse_than_target_cv_by_min_degradation": bool(worse_than_target_cv),
            }
        )

    cmdc_n = int(
        scope_audit[
            (scope_audit["label_scope"] == "overlap_mild_moderate") & (scope_audit["dataset"] == "cmdc")
        ]["subject_count"].iloc[0]
    )
    pdch_overlap_n = int(
        scope_audit[
            (scope_audit["label_scope"] == "overlap_mild_moderate") & (scope_audit["dataset"] == "pdch")
        ]["subject_count"].iloc[0]
    )

    supports_shift = flagged_items >= 2 or flagged_thresholds >= 3 or weak_transfer >= 1
    if supports_shift:
        status = "complete_exploratory_same_scale_context_shift_supported"
        short_read = (
            "MV18 remains exploratory because CMDC HAMD has only 25 subjects, but the same-scale control still shows dataset/context sensitivity through flagged HAMD item/threshold shifts or weak bidirectional transfer."
        )
    else:
        status = "complete_no_clear_same_scale_context_shift_beyond_small_sample"
        short_read = (
            "MV18 is complete but does not show a clear same-scale dataset/context shift beyond the predefined small-sample flags. Keep the result as a bounded control rather than evidence for HAMD invariance."
        )

    return {
        "pass_rule_status": status,
        "pass_rule_met": True,
        "cmdc_overlap_hamd_subjects": cmdc_n,
        "pdch_overlap_hamd_subjects": pdch_overlap_n,
        "flagged_overlap_residual_item_shifts": flagged_items,
        "flagged_overlap_threshold_shifts": flagged_thresholds,
        "weak_primary_transfer_directions": weak_transfer,
        "primary_transfer_details": transfer_details,
        "min_abs_residual_item_diff": MIN_CONDITIONAL_ITEM_DIFF,
        "min_abs_threshold_rate_diff": MIN_THRESHOLD_RATE_DIFF,
        "min_transfer_mae_gain": MIN_TRANSFER_MAE_GAIN,
        "min_transfer_degradation": MIN_TRANSFER_DEGRADATION,
        "claim_boundary": "Exploratory same-language/same-HAMD control only; not formal HAMD invariance because CMDC HAMD supervision is small.",
        "short_read": short_read,
    }, short_read


def label_top_rows(item_shift: pd.DataFrame, threshold_shift: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    item_rows = item_shift[item_shift["label_scope"] == "overlap_mild_moderate"].copy()
    item_rows["abs_residualized_diff"] = item_rows["residualized_diff_cmdc_minus_pdch"].abs()
    item_rows = item_rows.sort_values(["flagged_residual_shift", "abs_residualized_diff"], ascending=[False, False]).head(8)
    threshold_rows = threshold_shift[threshold_shift["label_scope"] == "overlap_mild_moderate"].copy()
    threshold_rows["abs_rate_diff"] = threshold_rows["rate_diff_cmdc_minus_pdch"].abs()
    threshold_rows = threshold_rows.sort_values(["flagged_threshold_shift", "abs_rate_diff"], ascending=[False, False]).head(8)
    return item_rows, threshold_rows


def transfer_report_rows(comparison: pd.DataFrame) -> pd.DataFrame:
    selected_scopes = [
        "pdch_cv_overlap",
        "cmdc_cv_overlap",
        "pdch_overlap_to_cmdc_overlap",
        "cmdc_overlap_to_pdch_overlap",
    ]
    selected = comparison[
        comparison["eval_scope"].isin(selected_scopes)
        & comparison["summary_target"].isin(["hamd_total_direct", "hamd_total_from_items", "macro_hamd_item_mae"])
    ].copy()
    selected["is_feature"] = selected["feature_space"] != "none"
    return selected.sort_values(["eval_scope", "summary_target", "mae", "feature_space", "model"]).groupby(
        ["eval_scope", "summary_target"], as_index=False, sort=False
    ).head(4)


def write_report(
    out_dir: Path,
    run_summary: dict[str, Any],
    scope_audit: pd.DataFrame,
    item_shift: pd.DataFrame,
    threshold_shift: pd.DataFrame,
    comparison: pd.DataFrame,
) -> None:
    verdict = run_summary["verdict"]
    item_rows, threshold_rows = label_top_rows(item_shift, threshold_shift)
    transfer_rows = transfer_report_rows(comparison)
    lines = [
        "# P5_MV18 CMDC-PDCH HAMD Same-Scale Control",
        "",
        f"Generated: `{run_summary['generated_at']}`",
        "",
        "## Scope",
        "",
        "MV18 is an exploratory same-language/same-HAMD control. It compares CMDC and PDCH HAMD-17 label behavior and shallow frozen-feature transfer while keeping source text content, media paths, feature arrays, and row-level predictions out of tracked artifacts.",
        "",
        "## Label Coverage",
        "",
        "| label scope | dataset | subjects | total mean | total sd | severity bins | code-9 subjects |",
        "| --- | --- | ---: | ---: | ---: | --- | ---: |",
    ]
    for _, row in scope_audit.iterrows():
        lines.append(
            f"| {row['label_scope']} | {row['dataset']} | {int(row['subject_count'])} | {format_value(row['hamd_total_mean'])} | {format_value(row['hamd_total_sd'])} | {row['severity_bin_counts']} | {int(row['hamd_code_9_subjects'])} |"
        )
    lines.extend(
        [
            "",
            "## Severity-Conditioned Item Shifts",
            "",
            "Positive values mean CMDC is higher than PDCH. The residualized comparison uses linear total-excluding-item conditioning.",
            "",
            "| item | residual diff | CI low | CI high | flagged | raw diff |",
            "| --- | ---: | ---: | ---: | --- | ---: |",
        ]
    )
    for _, row in item_rows.iterrows():
        lines.append(
            f"| {row['item_id']} | {format_value(row['residualized_diff_cmdc_minus_pdch'])} | {format_value(row['residualized_diff_ci95_low'])} | {format_value(row['residualized_diff_ci95_high'])} | {bool(row['flagged_residual_shift'])} | {format_value(row['raw_mean_diff_cmdc_minus_pdch'])} |"
        )
    lines.extend(
        [
            "",
            "## Threshold Shifts",
            "",
            "| item | threshold | rate diff | CI low | CI high | flagged | CMDC rate | PDCH rate |",
            "| --- | ---: | ---: | ---: | ---: | --- | ---: | ---: |",
        ]
    )
    for _, row in threshold_rows.iterrows():
        lines.append(
            f"| {row['item_id']} | {int(row['threshold'])} | {format_value(row['rate_diff_cmdc_minus_pdch'])} | {format_value(row['rate_diff_ci95_low'])} | {format_value(row['rate_diff_ci95_high'])} | {bool(row['flagged_threshold_shift'])} | {format_value(row['cmdc_rate_ge_threshold'])} | {format_value(row['pdch_rate_ge_threshold'])} |"
        )
    lines.extend(
        [
            "",
            "## Transfer Summary",
            "",
            "Negative deltas versus source train mean are improvements. Positive deltas versus target CV indicate cross-dataset degradation relative to same-dataset CV for the same feature/model.",
            "",
            "| eval scope | summary target | feature | model | MAE | delta vs source mean | delta vs target CV |",
            "| --- | --- | --- | --- | ---: | ---: | ---: |",
        ]
    )
    for _, row in transfer_rows.iterrows():
        lines.append(
            f"| {row['eval_scope']} | {row['summary_target']} | {row['feature_space']} | {row['model']} | {format_value(row['mae'])} | {format_value(row['delta_vs_source_train_mean'])} | {format_value(row['delta_vs_target_cv_same_feature'])} |"
        )
    lines.extend(
        [
            "",
            "## Verdict",
            "",
            f"- Pass-rule status: `{verdict['pass_rule_status']}`.",
            f"- CMDC overlap HAMD subjects: `{verdict['cmdc_overlap_hamd_subjects']}`.",
            f"- PDCH overlap HAMD subjects: `{verdict['pdch_overlap_hamd_subjects']}`.",
            f"- Flagged overlap residual item shifts: `{verdict['flagged_overlap_residual_item_shifts']}`.",
            f"- Flagged overlap threshold shifts: `{verdict['flagged_overlap_threshold_shifts']}`.",
            f"- Weak primary transfer directions: `{verdict['weak_primary_transfer_directions']}`.",
            "",
            run_summary["interpretation"]["short_read"],
            "",
            "## Hygiene",
            "",
            f"- Artifact hygiene passed: `{run_summary['artifact_hygiene_passed']}`.",
            "- Row-level predictions are written as a local-only ignored CSV.",
            "- Text content, media paths, file locators, feature arrays, learned embeddings, and fitted parameter files are not written.",
        ]
    )
    (out_dir / "report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def artifact_hygiene_audit(out_dir: Path) -> dict[str, Any]:
    forbidden_patterns = [
        r"/root/",
        r"/autodl-tmp/",
        r"\bsubject_id\b",
        r"\bsubject_key\b",
        r"\btext_path\b",
        r"\baudio_path\b",
        r"\bvideo_path\b",
        r"\bgait_path\b",
        r"\.wav\b",
        r"\.WAV\b",
        r"\.mp4\b",
        r"\.avi\b",
        r"raw transcript",
        r"raw clinical text",
        r"source locator",
        r"feature matrix",
        r"model weights",
    ]
    violations: list[dict[str, Any]] = []
    files_checked = 0
    for path in sorted(out_dir.rglob("*")):
        if not path.is_file():
            continue
        if path.name.endswith("_local_predictions.csv"):
            continue
        if path.name == "artifact_hygiene_audit.json":
            continue
        if path.suffix.lower() not in {".csv", ".json", ".md"}:
            continue
        files_checked += 1
        text = path.read_text(encoding="utf-8", errors="ignore")
        for pattern in forbidden_patterns:
            if re.search(pattern, text, flags=re.IGNORECASE):
                violations.append({"file": str(path.relative_to(out_dir)), "pattern": pattern})
    return {
        "audit_id": "P5_MV18_artifact_hygiene",
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


def feature_label_audit(availability: pd.DataFrame, joined: pd.DataFrame, scope_audit: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for _, row in scope_audit.iterrows():
        rows.append(
            {
                "dataset": row["dataset"],
                "audit_type": f"label_coverage_{row['label_scope']}",
                "feature_space": "",
                "feature_subjects": "",
                "joined_subjects": "",
                "feature_columns": "",
                "hamd_subjects": int(row["subject_count"]),
                "severity_bin_counts": row["severity_bin_counts"],
            }
        )
    for _, row in availability.iterrows():
        joined_row = joined[(joined["dataset"] == row["dataset"]) & (joined["feature_space"] == row["feature_space"])]
        rows.append(
            {
                "dataset": row["dataset"],
                "audit_type": "feature_availability",
                "feature_space": row["feature_space"],
                "feature_subjects": int(row["feature_subjects"]),
                "joined_subjects": int(joined_row["joined_subjects_after_join"].iloc[0]) if not joined_row.empty else "",
                "feature_columns": int(row["model_input_columns"]),
                "hamd_subjects": "",
                "severity_bin_counts": "",
            }
        )
    return pd.DataFrame(rows)


def construct_proxy_map() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {"construct_id": construct_id, "hamd_item_codes": ";".join(keys)}
            for construct_id, keys in sorted(HAMD_CONSTRUCT_MAP.items(), key=lambda item: natural_key(item[0]))
        ]
    )


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

    cmdc_labels = load_hamd_labels(args.manifest_dir, "cmdc")
    pdch_labels = load_hamd_labels(args.manifest_dir, "pdch")
    combined_labels = combine_labels(cmdc_labels, pdch_labels)
    scope_audit = label_scope_audit(combined_labels)
    item_distribution = item_distribution_summary(combined_labels)
    item_shift = item_shift_summary(combined_labels)
    threshold_shift = threshold_shift_summary(combined_labels)

    feature_tables, availability = load_feature_tables(args.phase2_root)
    pdch_table, pdch_cols_by_space, pdch_joined = build_model_table(pdch_labels, feature_tables, "pdch")
    cmdc_table, cmdc_cols_by_space, cmdc_joined = build_model_table(cmdc_labels, feature_tables, "cmdc")
    assert_feature_columns_match(pdch_cols_by_space, cmdc_cols_by_space)

    predictions, model_audit = run_transfer_diagnostics(pdch_table, cmdc_table, pdch_cols_by_space)
    metrics_by_seed, metric_summary = metric_tables(predictions)
    macro_summary = macro_summaries(metric_summary)
    comparison = transfer_comparison_summary(macro_summary)
    label_feature = feature_label_audit(availability, pd.concat([pdch_joined, cmdc_joined], ignore_index=True), scope_audit)
    verdict, short_read = build_verdict(scope_audit, item_shift, threshold_shift, comparison)

    scope_audit.to_csv(out_dir / "label_scope_audit.csv", index=False)
    item_distribution.to_csv(out_dir / "item_distribution_summary.csv", index=False)
    item_shift.to_csv(out_dir / "item_shift_summary.csv", index=False)
    threshold_shift.to_csv(out_dir / "threshold_shift_summary.csv", index=False)
    label_feature.to_csv(out_dir / "label_feature_audit.csv", index=False)
    metrics_by_seed.to_csv(out_dir / "metrics_by_seed.csv", index=False)
    metric_summary.to_csv(out_dir / "metric_summary.csv", index=False)
    macro_summary.to_csv(out_dir / "macro_summary.csv", index=False)
    comparison.to_csv(out_dir / "transfer_comparison_summary.csv", index=False)
    model_audit.to_csv(out_dir / "model_split_audit.csv", index=False)
    construct_proxy_map().to_csv(out_dir / "construct_proxy_map.csv", index=False)
    predictions.to_csv(out_dir / "p5_mv18_local_predictions.csv", index=False)

    run_summary: dict[str, Any] = {
        "run_id": RUN_ID,
        "generated_at": utc_now(),
        "status": "complete",
        "scope": "cmdc_pdch_hamd_same_language_same_scale_exploratory_control",
        "label_contract": {
            "cmdc_hamd_subjects": int(cmdc_labels["subject_key"].nunique()),
            "pdch_hamd_subjects": int(pdch_labels["subject_key"].nunique()),
            "cmdc_overlap_hamd_subjects": int(
                scope_audit[
                    (scope_audit["label_scope"] == "overlap_mild_moderate") & (scope_audit["dataset"] == "cmdc")
                ]["subject_count"].iloc[0]
            ),
            "pdch_overlap_hamd_subjects": int(
                scope_audit[
                    (scope_audit["label_scope"] == "overlap_mild_moderate") & (scope_audit["dataset"] == "pdch")
                ]["subject_count"].iloc[0]
            ),
            "hamd_code_9_policy": "reuse_mv02_policy_exclude_code_9_from_item_training_evaluation_and_item_total_scoring",
            "claim_boundary": "exploratory_control_not_formal_hamd_invariance",
        },
        "feature_contract": {
            "feature_spaces": ["text_bge", "audio_wavlm", "audio_egemaps", "early_fusion_all"],
            "feature_column_counts": {key: int(len(value)) for key, value in pdch_cols_by_space.items()},
            "feature_source": "existing_mv02_phase2_frozen_subject_features",
            "encoder_finetuning": False,
            "raw_data_scan": False,
        },
        "model_contract": {
            "models": ["train_mean_total", "train_mean_items", "direct_total_ridge", "itemwise_ridge"],
            "seeds": SEEDS,
            "folds_per_seed": FOLD_COUNT,
            "cross_dataset_eval_scopes": [
                "pdch_all_to_cmdc_overlap",
                "pdch_overlap_to_cmdc_overlap",
                "cmdc_overlap_to_pdch_all",
                "cmdc_overlap_to_pdch_overlap",
            ],
            "same_dataset_cv_scopes": ["pdch_cv_all", "pdch_cv_overlap", "cmdc_cv_overlap"],
        },
        "split_audit": {
            "subject_level_cv": True,
            "subject_overlap_violations": int(model_audit["subject_overlap_count"].sum()),
            "eval_labels_for_hyperparameters": False,
        },
        "label_shift_contract": {
            "label_scopes": ["all_subjects", "overlap_mild_moderate"],
            "residualized_item_shift": "linear_total_excluding_item",
            "label_bootstrap_resamples": LABEL_BOOTSTRAP_RESAMPLES,
            "model_metric_bootstrap_resamples": MODEL_BOOTSTRAP_RESAMPLES,
            "min_abs_residual_item_diff": MIN_CONDITIONAL_ITEM_DIFF,
            "min_abs_threshold_rate_diff": MIN_THRESHOLD_RATE_DIFF,
        },
        "output_policy": {
            "row_level_predictions": "local_only_ignored",
            "raw_text": "not_written",
            "media_paths": "not_written",
            "source_locators": "not_written",
            "feature_matrices": "not_written",
            "learned_embeddings": "not_written",
            "model_weights": "not_written",
        },
        "verdict": verdict,
        "interpretation": {"short_read": short_read},
        "artifact_hygiene_passed": False,
        "summary_files": [
            "report.md",
            "run_summary.json",
            "artifact_hygiene_audit.json",
            "label_scope_audit.csv",
            "item_distribution_summary.csv",
            "item_shift_summary.csv",
            "threshold_shift_summary.csv",
            "label_feature_audit.csv",
            "metrics_by_seed.csv",
            "metric_summary.csv",
            "macro_summary.csv",
            "transfer_comparison_summary.csv",
            "model_split_audit.csv",
            "construct_proxy_map.csv",
        ],
        "local_only_files": ["p5_mv18_local_predictions.csv"],
    }

    (out_dir / "run_summary.json").write_text(json.dumps(run_summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    write_report(out_dir, run_summary, scope_audit, item_shift, threshold_shift, comparison)
    hygiene = artifact_hygiene_audit(out_dir)
    run_summary["artifact_hygiene_passed"] = bool(hygiene["artifact_hygiene_passed"])
    (out_dir / "run_summary.json").write_text(json.dumps(run_summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    write_report(out_dir, run_summary, scope_audit, item_shift, threshold_shift, comparison)
    hygiene = artifact_hygiene_audit(out_dir)
    run_summary["artifact_hygiene_passed"] = bool(hygiene["artifact_hygiene_passed"])
    (out_dir / "run_summary.json").write_text(json.dumps(run_summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (out_dir / "artifact_hygiene_audit.json").write_text(json.dumps(hygiene, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    if not hygiene["artifact_hygiene_passed"]:
        raise SystemExit("artifact hygiene violations found; see artifact_hygiene_audit.json")
    print(f"Wrote P5_MV18 same-scale HAMD control artifacts to {out_dir.relative_to(WORKTREE_ROOT)}")


if __name__ == "__main__":
    main()
