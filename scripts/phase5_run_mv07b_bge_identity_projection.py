#!/usr/bin/env python3
"""Run P5_MV07b BGE identity-projection follow-up.

This is a bounded Phase 5 follow-up to the blocked aligned-BGE MV07 row. It
keeps the same frozen BGE subject-level feature contract, but tests whether
train-fold E-DAIC/CMDC dataset-label nuisance projection can reduce dataset
identity without using evaluation target labels or evaluation dataset labels at
transform time. It is still a minimal validation row, not the full method.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import re
import shutil
import sys
from dataclasses import dataclass
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
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import balanced_accuracy_score
from sklearn.model_selection import StratifiedKFold
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler


SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import phase5_run_mv07_aligned_bge_shared_symptom as mv07


ROOT = mv07.ROOT
DEFAULT_OUT_DIR = ROOT / "analysis" / "phase5_minimal_validation" / "p5_mv07b_bge_identity_projection"
DEFAULT_MANIFEST_DIR = mv07.DEFAULT_MANIFEST_DIR
DEFAULT_SPLIT_PATH = mv07.DEFAULT_SPLIT_PATH
DEFAULT_PHASE2_ROOT = mv07.DEFAULT_PHASE2_ROOT

RUN_ID = "P5_MV07b_bge_identity_projection"
PROTOCOL_ID = "pooled_shared_phq_bge_identity_projection"
SEEDS = mv07.SEEDS
CONSTRUCTS = mv07.CONSTRUCTS
RIDGE_ALPHA_GRID = mv07.RIDGE_ALPHA_GRID
PROJECTION_COMPONENTS = [1, 3, 5, 10]

TRAIN_MEAN_MODEL = "train_mean"
TOTAL_ALLOC_MODEL = "total_alloc_ridge"
RAW_MODEL = "bge_itemwise_ridge_raw"
CONTROL_MODEL_PREFIX = "bge_logit_projection"
TARGET_FAMILY = "phq_core"

TRACKED_FILES = {
    "artifact_hygiene_audit.json",
    "best_control_summary.csv",
    "comparison_summary.csv",
    "construct_target_map.csv",
    "identity_probe_by_seed.csv",
    "identity_probe_summary.csv",
    "label_feature_audit.csv",
    "metric_summary.csv",
    "metrics_by_seed.csv",
    "model_split_audit.csv",
    "projection_audit.csv",
    "report.md",
    "run_summary.json",
    "worst_slice_by_seed.csv",
    "worst_slice_summary.csv",
}


@dataclass(frozen=True)
class ProjectionTransform:
    """Train-fold nuisance projection fitted without eval labels."""

    component_count: int
    fitted_component_count: int
    feature_cols: list[str]
    train_counts: dict[str, int]
    direction_norms: list[float]
    imputer: SimpleImputer
    scaler: StandardScaler
    directions: list[np.ndarray]


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def safe_float(value: Any) -> float | None:
    return mv07.safe_float(value)


def format_value(value: Any, digits: int = 3) -> str:
    numeric = safe_float(value)
    return "NA" if numeric is None else f"{numeric:.{digits}f}"


def control_model_name(component_count: int) -> str:
    return f"{CONTROL_MODEL_PREFIX}_k{component_count}_itemwise_ridge"


def feature_representation_name(component_count: int) -> str:
    return f"{CONTROL_MODEL_PREFIX}_k{component_count}_features"


def prediction_representation_name(component_count: int) -> str:
    return f"{CONTROL_MODEL_PREFIX}_k{component_count}_predictions"


def sort_subject_frame(frame: pd.DataFrame) -> pd.DataFrame:
    return frame.sort_values(
        ["dataset", "subject_id"],
        key=lambda series: series.map(lambda item: tuple(mv07.natural_key(item))),
    ).copy()


def pooled_train_eval_for_seed(
    table: pd.DataFrame,
    cmdc_folds: dict[int, dict[str, set[str]]],
    seed: int,
) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, Any]]:
    edaic_train_subjects = set(
        table.loc[(table["dataset"] == "edaic") & (table["official_split"] == "train"), "subject_id"].astype(str)
    )
    edaic_dev_subjects = set(
        table.loc[(table["dataset"] == "edaic") & (table["official_split"] == "dev"), "subject_id"].astype(str)
    )
    if edaic_train_subjects & edaic_dev_subjects:
        raise ValueError("E-DAIC official train/dev subject overlap")

    fold = cmdc_folds[seed % len(cmdc_folds)]
    fold_name = next(iter(fold["fold_name"]))
    train = table[
        ((table["dataset"] == "edaic") & (table["subject_id"].isin(edaic_train_subjects)))
        | ((table["dataset"] == "cmdc") & (table["subject_id"].isin(fold["train"])))
    ]
    eval_frame = table[
        ((table["dataset"] == "edaic") & (table["subject_id"].isin(edaic_dev_subjects)))
        | ((table["dataset"] == "cmdc") & (table["subject_id"].isin(fold["validation"])))
    ]
    train = sort_subject_frame(train)
    eval_frame = sort_subject_frame(eval_frame)
    overlap = set(train["subject_key"].astype(str)) & set(eval_frame["subject_key"].astype(str))
    if overlap:
        raise ValueError(f"{PROTOCOL_ID}/{seed} train/eval overlap: {sorted(overlap)[:5]}")
    return train, eval_frame, {
        "seed": seed,
        "fold": fold_name,
        "protocol": PROTOCOL_ID,
        "target_family": TARGET_FAMILY,
        "train_subjects": int(train["subject_key"].nunique()),
        "eval_subjects": int(eval_frame["subject_key"].nunique()),
        "train_edaic_subjects": int((train["dataset"] == "edaic").sum()),
        "train_cmdc_subjects": int((train["dataset"] == "cmdc").sum()),
        "eval_edaic_subjects": int((eval_frame["dataset"] == "edaic").sum()),
        "eval_cmdc_subjects": int((eval_frame["dataset"] == "cmdc").sum()),
        "train_eval_subject_overlap": int(len(overlap)),
    }


def predict_train_mean_named(
    train: pd.DataFrame,
    eval_frame: pd.DataFrame,
    seed: int,
    fold: str,
) -> pd.DataFrame:
    low, high = mv07.target_bounds(train, TARGET_FAMILY)
    means = np.clip(train[CONSTRUCTS].mean(axis=0).to_numpy(dtype=float), low, high)
    pred = np.tile(means.reshape(1, -1), (len(eval_frame), 1))
    return mv07.wide_predictions(
        eval_frame,
        pred,
        run_id=RUN_ID,
        protocol=PROTOCOL_ID,
        model=TRAIN_MEAN_MODEL,
        seed=seed,
        fold=fold,
        target_family=TARGET_FAMILY,
    )


def fit_predict_total_alloc_named(
    train: pd.DataFrame,
    eval_frame: pd.DataFrame,
    feature_cols: list[str],
    seed: int,
    fold: str,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    x_train = train[feature_cols].to_numpy(dtype=float)
    y_total = train[CONSTRUCTS].sum(axis=1).to_numpy(dtype=float)
    x_eval = eval_frame[feature_cols].to_numpy(dtype=float)
    alpha = mv07.choose_alpha(x_train, y_total.reshape(-1, 1), seed)
    model = mv07.ridge_pipeline(alpha)
    model.fit(x_train, y_total)
    total_pred = np.asarray(model.predict(x_eval), dtype=float).reshape(-1)
    construct_means = train[CONSTRUCTS].mean(axis=0).to_numpy(dtype=float)
    denom = float(np.sum(construct_means))
    proportions = np.repeat(1.0 / len(CONSTRUCTS), len(CONSTRUCTS)) if denom <= 0 else construct_means / denom
    low, high = mv07.target_bounds(train, TARGET_FAMILY)
    pred = mv07.clip_matrix(total_pred.reshape(-1, 1) * proportions.reshape(1, -1), low, high)
    return mv07.wide_predictions(
        eval_frame,
        pred,
        run_id=RUN_ID,
        protocol=PROTOCOL_ID,
        model=TOTAL_ALLOC_MODEL,
        seed=seed,
        fold=fold,
        target_family=TARGET_FAMILY,
    ), {"selected_alpha": alpha}


def fit_predict_itemwise_train_eval(
    train: pd.DataFrame,
    eval_frame: pd.DataFrame,
    feature_cols: list[str],
    seed: int,
    fold: str,
    model_name: str,
) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, Any]]:
    x_train = train[feature_cols].to_numpy(dtype=float)
    y_train = train[CONSTRUCTS].to_numpy(dtype=float)
    x_eval = eval_frame[feature_cols].to_numpy(dtype=float)
    alpha = mv07.choose_alpha(x_train, y_train, seed)
    model = mv07.ridge_pipeline(alpha)
    model.fit(x_train, y_train)
    low, high = mv07.target_bounds(train, TARGET_FAMILY)
    train_pred = mv07.clip_matrix(model.predict(x_train), low, high)
    eval_pred = mv07.clip_matrix(model.predict(x_eval), low, high)
    return (
        mv07.wide_predictions(
            train,
            train_pred,
            run_id=RUN_ID,
            protocol=PROTOCOL_ID,
            model=model_name,
            seed=seed,
            fold=fold,
            target_family=TARGET_FAMILY,
        ),
        mv07.wide_predictions(
            eval_frame,
            eval_pred,
            run_id=RUN_ID,
            protocol=PROTOCOL_ID,
            model=model_name,
            seed=seed,
            fold=fold,
            target_family=TARGET_FAMILY,
        ),
        {"selected_alpha": alpha},
    )


def build_projection_transform(
    train: pd.DataFrame,
    feature_cols: list[str],
    component_count: int,
    seed: int,
) -> tuple[ProjectionTransform, np.ndarray]:
    x_train = train[feature_cols].to_numpy(dtype=float)
    y_train = (train["dataset"].astype(str) == "cmdc").astype(int).to_numpy()
    imputer = SimpleImputer(strategy="median")
    scaler = StandardScaler()
    z_train = scaler.fit_transform(imputer.fit_transform(x_train))
    directions: list[np.ndarray] = []
    direction_norms: list[float] = []

    for index in range(component_count):
        if len(set(y_train)) < 2:
            break
        classifier = LogisticRegression(
            C=1.0,
            class_weight="balanced",
            max_iter=2000,
            random_state=seed + index,
        )
        classifier.fit(z_train, y_train)
        direction = classifier.coef_.reshape(-1).astype(float)
        norm = float(np.linalg.norm(direction))
        if not np.isfinite(norm) or norm < 1e-12:
            break
        unit = direction / norm
        z_train = z_train - np.outer(z_train @ unit, unit)
        directions.append(unit)
        direction_norms.append(norm)

    train_counts = {
        str(dataset): int(group["subject_key"].nunique())
        for dataset, group in train.groupby("dataset", sort=True)
    }
    transform = ProjectionTransform(
        component_count=component_count,
        fitted_component_count=len(directions),
        feature_cols=list(feature_cols),
        train_counts=train_counts,
        direction_norms=direction_norms,
        imputer=imputer,
        scaler=scaler,
        directions=directions,
    )
    return transform, z_train


def apply_projection_transform(frame: pd.DataFrame, transform: ProjectionTransform) -> pd.DataFrame:
    z_values = transform.scaler.transform(
        transform.imputer.transform(frame[transform.feature_cols].to_numpy(dtype=float))
    )
    for unit in transform.directions:
        z_values = z_values - np.outer(z_values @ unit, unit)
    out = frame.copy()
    out.loc[:, transform.feature_cols] = z_values
    return out


def projection_audit_row(seed: int, fold: str, transform: ProjectionTransform) -> dict[str, Any]:
    return {
        "seed": seed,
        "fold": fold,
        "protocol": PROTOCOL_ID,
        "requested_component_count": transform.component_count,
        "fitted_component_count": transform.fitted_component_count,
        "direction_norm_min": safe_float(min(transform.direction_norms)) if transform.direction_norms else None,
        "direction_norm_max": safe_float(max(transform.direction_norms)) if transform.direction_norms else None,
        "train_edaic_subjects": transform.train_counts.get("edaic", 0),
        "train_cmdc_subjects": transform.train_counts.get("cmdc", 0),
        "control_uses_eval_target_labels": False,
        "control_uses_eval_dataset_labels": False,
        "control_parameters_written": False,
        "transformed_features_written": False,
    }


def prediction_representation(frame: pd.DataFrame, predictions: pd.DataFrame) -> pd.DataFrame:
    wide = (
        predictions.pivot_table(index="subject_key", columns="construct_id", values="y_pred", aggfunc="first")
        .reset_index()
        .rename_axis(None, axis=1)
    )
    meta = frame[["subject_key", "dataset", "subject_id"]].drop_duplicates()
    return meta.merge(wide, on="subject_key", how="inner")


def run_binary_identity_probe(
    train_repr: pd.DataFrame,
    eval_repr: pd.DataFrame,
    probe_cols: list[str],
    seed: int,
    layer: str,
    representation: str,
) -> dict[str, Any]:
    train_overlap = set(train_repr["subject_key"].astype(str)) & set(eval_repr["subject_key"].astype(str))
    y_train = (train_repr["dataset"].astype(str) == "cmdc").astype(int).to_numpy()
    y_eval = (eval_repr["dataset"].astype(str) == "cmdc").astype(int).to_numpy()
    if len(set(y_train)) < 2 or len(set(y_eval)) < 2:
        value = None
        skipped_reason = "missing_dataset_class_in_train_or_eval"
    else:
        model = Pipeline(
            [
                ("imputer", SimpleImputer(strategy="median")),
                ("scaler", StandardScaler()),
                (
                    "classifier",
                    LogisticRegression(C=1.0, class_weight="balanced", max_iter=2000, random_state=seed),
                ),
            ]
        )
        model.fit(train_repr[probe_cols].to_numpy(dtype=float), y_train)
        value = float(balanced_accuracy_score(y_eval, model.predict(eval_repr[probe_cols].to_numpy(dtype=float))))
        skipped_reason = None
    return {
        "seed": seed,
        "probe_id": "edaic_vs_cmdc_identity_train_fold_to_eval_fold",
        "probe_layer": layer,
        "representation": representation,
        "metric": "Balanced Accuracy",
        "value": safe_float(value),
        "train_subjects": int(train_repr["subject_key"].nunique()),
        "eval_subjects": int(eval_repr["subject_key"].nunique()),
        "sample_count": int(train_repr["subject_key"].nunique() + eval_repr["subject_key"].nunique()),
        "dataset_count": 2,
        "subject_overlap_count": int(len(train_overlap)),
        "skipped_reason": skipped_reason,
    }


def feature_table_from_datasets(features_by_dataset: dict[str, pd.DataFrame], feature_cols: list[str]) -> pd.DataFrame:
    frames: list[pd.DataFrame] = []
    for dataset, frame in features_by_dataset.items():
        data = frame[["subject_id", *feature_cols]].copy()
        data["dataset"] = dataset
        data["subject_key"] = data["dataset"].astype(str) + "::" + data["subject_id"].astype(str)
        frames.append(data)
    return pd.concat(frames, ignore_index=True)


def apply_projection_to_feature_tables(
    features_by_dataset: dict[str, pd.DataFrame],
    feature_cols: list[str],
    transform: ProjectionTransform,
) -> pd.DataFrame:
    projected: dict[str, pd.DataFrame] = {}
    for dataset, frame in features_by_dataset.items():
        projected[dataset] = apply_projection_transform(frame[["subject_id", *feature_cols]].copy(), transform)
    return feature_table_from_datasets(projected, feature_cols)


def run_multidataset_feature_identity_cv(
    table: pd.DataFrame,
    feature_cols: list[str],
    seed: int,
    representation: str,
) -> dict[str, Any]:
    labels = sorted(table["dataset"].astype(str).unique(), key=mv07.natural_key)
    label_map = {label: idx for idx, label in enumerate(labels)}
    y = table["dataset"].astype(str).map(label_map).to_numpy(dtype=int)
    x = table[feature_cols].to_numpy(dtype=float)
    n_splits = min(5, min(np.bincount(y)))
    scores: list[float] = []
    splitter = StratifiedKFold(n_splits=n_splits, shuffle=True, random_state=seed)
    for train_idx, eval_idx in splitter.split(x, y):
        model = Pipeline(
            [
                ("imputer", SimpleImputer(strategy="median")),
                ("scaler", StandardScaler()),
                (
                    "classifier",
                    LogisticRegression(C=1.0, class_weight="balanced", max_iter=2000, random_state=seed),
                ),
            ]
        )
        model.fit(x[train_idx], y[train_idx])
        scores.append(float(balanced_accuracy_score(y[eval_idx], model.predict(x[eval_idx]))))
    return {
        "seed": seed,
        "probe_id": "feature_identity_cv_edaic_cmdc_pdch",
        "probe_layer": "feature",
        "representation": representation,
        "metric": "Balanced Accuracy",
        "value": safe_float(np.mean(scores)),
        "train_subjects": None,
        "eval_subjects": None,
        "sample_count": int(table["subject_key"].nunique()),
        "dataset_count": int(len(labels)),
        "subject_overlap_count": 0,
        "skipped_reason": None,
    }


def summarize_identity(identity_by_seed: pd.DataFrame) -> pd.DataFrame:
    if identity_by_seed.empty:
        return pd.DataFrame()
    return (
        identity_by_seed.groupby(["probe_id", "probe_layer", "representation", "metric"], dropna=False)
        .agg(
            mean=("value", "mean"),
            std=("value", "std"),
            seed_count=("seed", "nunique"),
            train_subjects_mean=("train_subjects", "mean"),
            eval_subjects_mean=("eval_subjects", "mean"),
            sample_count_mean=("sample_count", "mean"),
            dataset_count_mean=("dataset_count", "mean"),
            subject_overlap_count_sum=("subject_overlap_count", "sum"),
        )
        .reset_index()
        .fillna({"std": 0.0})
    )


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
        train_mean = values.get(TRAIN_MEAN_MODEL)
        total_alloc = values.get(TOTAL_ALLOC_MODEL)
        raw = values.get(RAW_MODEL)
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
                    "delta_vs_raw_bge_itemwise_ridge": safe_float(value - raw) if raw is not None else None,
                    "relative_delta_vs_raw_bge_itemwise_ridge": safe_float((value - raw) / raw)
                    if raw not in (None, 0)
                    else None,
                }
            )
    return pd.DataFrame(rows)


def build_worst_slice_tables(
    metrics_by_seed: pd.DataFrame,
    comparison_summary: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    macro = metrics_by_seed[
        (metrics_by_seed["construct_id"] == "macro")
        & (metrics_by_seed["metric"] == "Macro Construct MAE")
        & (metrics_by_seed["dataset_slice"] != "pooled")
    ].copy()
    rows: list[dict[str, Any]] = []
    for (seed, protocol, target_family, model), group in macro.groupby(
        ["seed", "protocol", "target_family", "model"], sort=False
    ):
        worst = group.sort_values(["value", "dataset_slice"], ascending=[False, True]).iloc[0]
        rows.append(
            {
                "seed": int(seed),
                "protocol": protocol,
                "target_family": target_family,
                "model": model,
                "metric": "Worst Dataset-Slice Macro Construct MAE",
                "worst_dataset_slice": worst["dataset_slice"],
                "value": safe_float(worst["value"]),
            }
        )
    by_seed = pd.DataFrame(rows)
    summary = (
        by_seed.groupby(["protocol", "target_family", "model", "metric"], dropna=False)
        .agg(
            mean=("value", "mean"),
            std=("value", "std"),
            seed_count=("seed", "nunique"),
        )
        .reset_index()
    )
    summary["std"] = summary["std"].fillna(0.0)
    summary["ci95_low"] = summary["mean"] - 1.96 * summary["std"] / np.sqrt(summary["seed_count"].clip(lower=1))
    summary["ci95_high"] = summary["mean"] + 1.96 * summary["std"] / np.sqrt(summary["seed_count"].clip(lower=1))
    raw_worst = (
        comparison_summary[comparison_summary["model"] == RAW_MODEL]
        .sort_values(["macro_mae", "dataset_slice"], ascending=[False, True])
        .groupby(["protocol", "target_family"], dropna=False)
        .head(1)
        .set_index(["protocol", "target_family"])["macro_mae"]
        .to_dict()
    )
    summary["raw_worst_macro_mae"] = [
        raw_worst.get((row["protocol"], row["target_family"])) for _, row in summary.iterrows()
    ]
    summary["delta_vs_raw_bge_itemwise_ridge"] = summary["mean"] - summary["raw_worst_macro_mae"]
    summary["relative_delta_vs_raw_bge_itemwise_ridge"] = (
        summary["mean"] - summary["raw_worst_macro_mae"]
    ) / summary["raw_worst_macro_mae"]
    return by_seed, summary


def identity_value(identity_summary: pd.DataFrame, probe_id: str, representation: str) -> float | None:
    row = identity_summary[
        (identity_summary["probe_id"] == probe_id)
        & (identity_summary["representation"] == representation)
        & (identity_summary["metric"] == "Balanced Accuracy")
    ]
    if row.empty:
        return None
    return safe_float(row.iloc[0]["mean"])


def build_best_control_summary(
    comparison_summary: pd.DataFrame,
    identity_summary: pd.DataFrame,
    subject_overlap_violations: int,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    raw_binary_feature = identity_value(
        identity_summary,
        "edaic_vs_cmdc_identity_train_fold_to_eval_fold",
        "raw_bge_features",
    )
    raw_binary_prediction = identity_value(
        identity_summary,
        "edaic_vs_cmdc_identity_train_fold_to_eval_fold",
        "raw_bge_predictions",
    )
    raw_three_way_feature = identity_value(
        identity_summary,
        "feature_identity_cv_edaic_cmdc_pdch",
        "raw_bge_features",
    )

    rows: list[dict[str, Any]] = []
    for component_count in PROJECTION_COMPONENTS:
        model = control_model_name(component_count)
        control_rows = comparison_summary[comparison_summary["model"] == model].copy()
        deltas_train_mean = control_rows["delta_vs_train_mean"].dropna().tolist()
        deltas_total_alloc = control_rows["delta_vs_total_alloc_ridge"].dropna().tolist()
        rel_deltas = control_rows["relative_delta_vs_raw_bge_itemwise_ridge"].dropna().tolist()
        feature_repr = feature_representation_name(component_count)
        prediction_repr = prediction_representation_name(component_count)
        binary_feature_after = identity_value(
            identity_summary,
            "edaic_vs_cmdc_identity_train_fold_to_eval_fold",
            feature_repr,
        )
        binary_prediction_after = identity_value(
            identity_summary,
            "edaic_vs_cmdc_identity_train_fold_to_eval_fold",
            prediction_repr,
        )
        three_way_feature_after = identity_value(
            identity_summary,
            "feature_identity_cv_edaic_cmdc_pdch",
            feature_repr,
        )
        main_within = bool(rel_deltas and max(rel_deltas) <= 0.05)
        beats_train_mean = bool(deltas_train_mean and all(value < 0.0 for value in deltas_train_mean))
        beats_total_alloc = bool(deltas_total_alloc and all(value < 0.0 for value in deltas_total_alloc))
        binary_feature_reduced = bool(
            raw_binary_feature is not None
            and binary_feature_after is not None
            and binary_feature_after < raw_binary_feature
        )
        binary_prediction_reduced = bool(
            raw_binary_prediction is not None
            and binary_prediction_after is not None
            and binary_prediction_after < raw_binary_prediction
        )
        three_way_feature_reduced = bool(
            raw_three_way_feature is not None
            and three_way_feature_after is not None
            and three_way_feature_after < raw_three_way_feature
        )
        rows.append(
            {
                "model": model,
                "component_count": component_count,
                "main_task_within_5pct_vs_raw_all_slices": main_within,
                "beats_train_mean_all_slices": beats_train_mean,
                "beats_total_alloc_all_slices": beats_total_alloc,
                "binary_feature_identity_reduced": binary_feature_reduced,
                "binary_prediction_identity_reduced": binary_prediction_reduced,
                "three_way_feature_identity_reduced": three_way_feature_reduced,
                "binary_feature_identity_ba_after": safe_float(binary_feature_after),
                "binary_prediction_identity_ba_after": safe_float(binary_prediction_after),
                "three_way_feature_identity_ba_after": safe_float(three_way_feature_after),
                "worst_relative_delta_vs_raw": safe_float(max(rel_deltas)) if rel_deltas else None,
                "pooled_edaic_delta_vs_train_mean": safe_float(
                    control_rows.loc[control_rows["dataset_slice"] == "edaic", "delta_vs_train_mean"].iloc[0]
                )
                if not control_rows.loc[control_rows["dataset_slice"] == "edaic"].empty
                else None,
                "pooled_cmdc_delta_vs_train_mean": safe_float(
                    control_rows.loc[control_rows["dataset_slice"] == "cmdc", "delta_vs_train_mean"].iloc[0]
                )
                if not control_rows.loc[control_rows["dataset_slice"] == "cmdc"].empty
                else None,
                "pooled_edaic_delta_vs_total_alloc": safe_float(
                    control_rows.loc[control_rows["dataset_slice"] == "edaic", "delta_vs_total_alloc_ridge"].iloc[0]
                )
                if not control_rows.loc[control_rows["dataset_slice"] == "edaic"].empty
                else None,
                "pooled_cmdc_delta_vs_total_alloc": safe_float(
                    control_rows.loc[control_rows["dataset_slice"] == "cmdc", "delta_vs_total_alloc_ridge"].iloc[0]
                )
                if not control_rows.loc[control_rows["dataset_slice"] == "cmdc"].empty
                else None,
            }
        )

    summary = pd.DataFrame(rows)
    if summary.empty:
        raise ValueError("no projection controls were summarized")
    eligible = summary[
        summary["main_task_within_5pct_vs_raw_all_slices"]
        & summary["binary_feature_identity_reduced"]
        & summary["binary_prediction_identity_reduced"]
    ].copy()
    candidate_pool = eligible if not eligible.empty else summary
    best = candidate_pool.sort_values(
        [
            "binary_prediction_identity_ba_after",
            "binary_feature_identity_ba_after",
            "worst_relative_delta_vs_raw",
        ],
        na_position="last",
    ).iloc[0].to_dict()

    if subject_overlap_violations > 0:
        status = "blocked_subject_overlap_bge_projection"
    elif eligible.empty:
        any_preserved = bool(summary["main_task_within_5pct_vs_raw_all_slices"].any())
        status = (
            "blocked_identity_not_reduced_bge_projection"
            if any_preserved
            else "blocked_main_metric_not_preserved_bge_projection"
        )
    elif not bool(best["beats_train_mean_all_slices"]):
        status = "blocked_no_consistent_phq_gain_bge_projection"
    elif not bool(best["beats_total_alloc_all_slices"]):
        status = "partial_identity_reduced_not_total_floor_beating_bge_projection"
    elif safe_float(best["binary_prediction_identity_ba_after"]) is None or safe_float(
        best["binary_prediction_identity_ba_after"]
    ) > 0.70:
        status = "partial_identity_reduced_residual_prediction_identity_high_bge_projection"
    elif safe_float(best["binary_feature_identity_ba_after"]) is None or safe_float(
        best["binary_feature_identity_ba_after"]
    ) > 0.70:
        status = "partial_identity_reduced_residual_feature_identity_high_bge_projection"
    else:
        status = "pass_bge_identity_projection_candidate"

    verdict = {
        "pass_rule_status": status,
        "pass_rule_met": status.startswith("pass_"),
        "short_read": (
            "MV07b tests an inference-compatible BGE identity projection for the pooled E-DAIC/CMDC PHQ C01-C08 contract. A positive claim requires preserved construct MAE, gains over simple floors, and reduced feature/prediction identity."
        ),
        "raw_binary_feature_identity_ba": safe_float(raw_binary_feature),
        "raw_binary_prediction_identity_ba": safe_float(raw_binary_prediction),
        "raw_three_way_feature_identity_ba": safe_float(raw_three_way_feature),
        "best_control_model": str(best["model"]),
        "best_control_component_count": int(best["component_count"]),
        "best_binary_feature_identity_ba_after": safe_float(best["binary_feature_identity_ba_after"]),
        "best_binary_prediction_identity_ba_after": safe_float(best["binary_prediction_identity_ba_after"]),
        "best_three_way_feature_identity_ba_after": safe_float(best["three_way_feature_identity_ba_after"]),
        "best_worst_relative_delta_vs_raw": safe_float(best["worst_relative_delta_vs_raw"]),
        "best_pooled_edaic_delta_vs_train_mean": safe_float(best["pooled_edaic_delta_vs_train_mean"]),
        "best_pooled_cmdc_delta_vs_train_mean": safe_float(best["pooled_cmdc_delta_vs_train_mean"]),
        "best_pooled_edaic_delta_vs_total_alloc": safe_float(best["pooled_edaic_delta_vs_total_alloc"]),
        "best_pooled_cmdc_delta_vs_total_alloc": safe_float(best["pooled_cmdc_delta_vs_total_alloc"]),
        "subject_overlap_violations": int(subject_overlap_violations),
        "model_verdicts": rows,
    }
    return summary, verdict


def run_experiment(
    table: pd.DataFrame,
    feature_cols: list[str],
    cmdc_folds: dict[int, dict[str, set[str]]],
    features_by_dataset: dict[str, pd.DataFrame],
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    prediction_frames: list[pd.DataFrame] = []
    identity_rows: list[dict[str, Any]] = []
    audit_rows: list[dict[str, Any]] = []
    projection_rows: list[dict[str, Any]] = []
    raw_feature_table = feature_table_from_datasets(features_by_dataset, feature_cols)

    for seed in SEEDS:
        train, eval_frame, base_audit = pooled_train_eval_for_seed(table, cmdc_folds, seed)
        fold = str(base_audit["fold"])

        train_mean = predict_train_mean_named(train, eval_frame, seed, fold)
        prediction_frames.append(train_mean)
        audit_rows.append(
            {
                **base_audit,
                "model": TRAIN_MEAN_MODEL,
                "feature_transform": "none",
                "selected_alpha": None,
                "control_uses_eval_target_labels": False,
                "control_uses_eval_dataset_labels": False,
            }
        )

        total_alloc, total_details = fit_predict_total_alloc_named(train, eval_frame, feature_cols, seed, fold)
        prediction_frames.append(total_alloc)
        audit_rows.append(
            {
                **base_audit,
                "model": TOTAL_ALLOC_MODEL,
                "feature_transform": "none",
                "selected_alpha": total_details.get("selected_alpha"),
                "control_uses_eval_target_labels": False,
                "control_uses_eval_dataset_labels": False,
            }
        )

        raw_train_pred, raw_eval_pred, raw_details = fit_predict_itemwise_train_eval(
            train,
            eval_frame,
            feature_cols,
            seed,
            fold,
            RAW_MODEL,
        )
        prediction_frames.append(raw_eval_pred)
        audit_rows.append(
            {
                **base_audit,
                "model": RAW_MODEL,
                "feature_transform": "raw_bge",
                "selected_alpha": raw_details.get("selected_alpha"),
                "control_uses_eval_target_labels": False,
                "control_uses_eval_dataset_labels": False,
            }
        )
        identity_rows.append(
            run_binary_identity_probe(train, eval_frame, feature_cols, seed, "feature", "raw_bge_features")
        )
        identity_rows.append(
            run_binary_identity_probe(
                prediction_representation(train, raw_train_pred),
                prediction_representation(eval_frame, raw_eval_pred),
                CONSTRUCTS,
                seed,
                "prediction",
                "raw_bge_predictions",
            )
        )
        identity_rows.append(run_multidataset_feature_identity_cv(raw_feature_table, feature_cols, seed, "raw_bge_features"))

        for component_count in PROJECTION_COMPONENTS:
            transform, projected_train_values = build_projection_transform(train, feature_cols, component_count, seed)
            projected_train = train.copy()
            projected_train.loc[:, feature_cols] = projected_train_values
            projected_eval = apply_projection_transform(eval_frame, transform)
            model = control_model_name(component_count)
            control_train_pred, control_eval_pred, control_details = fit_predict_itemwise_train_eval(
                projected_train,
                projected_eval,
                feature_cols,
                seed,
                fold,
                model,
            )
            prediction_frames.append(control_eval_pred)
            audit_rows.append(
                {
                    **base_audit,
                    "model": model,
                    "feature_transform": f"{CONTROL_MODEL_PREFIX}_k{component_count}",
                    "selected_alpha": control_details.get("selected_alpha"),
                    "control_uses_eval_target_labels": False,
                    "control_uses_eval_dataset_labels": False,
                    "control_parameters_written": False,
                    "transformed_features_written": False,
                }
            )
            projection_rows.append(projection_audit_row(seed, fold, transform))
            identity_rows.append(
                run_binary_identity_probe(
                    projected_train,
                    projected_eval,
                    feature_cols,
                    seed,
                    "feature",
                    feature_representation_name(component_count),
                )
            )
            identity_rows.append(
                run_binary_identity_probe(
                    prediction_representation(train, control_train_pred),
                    prediction_representation(eval_frame, control_eval_pred),
                    CONSTRUCTS,
                    seed,
                    "prediction",
                    prediction_representation_name(component_count),
                )
            )
            projected_feature_table = apply_projection_to_feature_tables(features_by_dataset, feature_cols, transform)
            identity_rows.append(
                run_multidataset_feature_identity_cv(
                    projected_feature_table,
                    feature_cols,
                    seed,
                    feature_representation_name(component_count),
                )
            )

    return (
        pd.concat(prediction_frames, ignore_index=True),
        pd.DataFrame(identity_rows),
        pd.DataFrame(audit_rows),
        pd.DataFrame(projection_rows),
    )


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
        r"source path",
        r"raw prompt",
        r"raw response",
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
        "audit_id": "P5_MV07b_bge_identity_projection_hygiene",
        "generated_at": utc_now(),
        "files_checked": checked,
        "artifact_hygiene_passed": not violations,
        "violation_count": len(violations),
        "violations": violations,
    }


def write_report(
    out_dir: Path,
    run_summary: dict[str, Any],
    comparison: pd.DataFrame,
    identity: pd.DataFrame,
    best_controls: pd.DataFrame,
) -> None:
    verdict = run_summary["verdict"]
    key_models = [TRAIN_MEAN_MODEL, TOTAL_ALLOC_MODEL, RAW_MODEL, verdict["best_control_model"]]
    key = comparison[comparison["model"].isin(key_models)].copy()
    lines = [
        "# P5_MV07b BGE Identity Projection",
        "",
        f"Generated: `{run_summary['generated_at']}`",
        "",
        "## Scope",
        "",
        "This follow-up tests train-fold E-DAIC/CMDC dataset-label nuisance projection over frozen aligned BGE subject features. Projection directions are learned only from training-fold features and dataset labels, then applied to held-out subjects without evaluation target labels or evaluation dataset labels.",
        "",
        "## Verdict",
        "",
        f"- Pass-rule status: `{verdict['pass_rule_status']}`.",
        f"- Best control model: `{verdict['best_control_model']}`.",
        f"- Binary feature identity BA before/best-after: `{format_value(verdict['raw_binary_feature_identity_ba'])}` -> `{format_value(verdict['best_binary_feature_identity_ba_after'])}`.",
        f"- Binary prediction identity BA before/best-after: `{format_value(verdict['raw_binary_prediction_identity_ba'])}` -> `{format_value(verdict['best_binary_prediction_identity_ba_after'])}`.",
        f"- Three-way feature identity BA before/best-after: `{format_value(verdict['raw_three_way_feature_identity_ba'])}` -> `{format_value(verdict['best_three_way_feature_identity_ba_after'])}`.",
        f"- Best E-DAIC delta vs total allocation: `{format_value(verdict['best_pooled_edaic_delta_vs_total_alloc'])}`.",
        f"- Best CMDC delta vs total allocation: `{format_value(verdict['best_pooled_cmdc_delta_vs_total_alloc'])}`.",
        f"- Subject-overlap violations: `{verdict['subject_overlap_violations']}`.",
        f"- Artifact hygiene passed: `{run_summary['artifact_hygiene_passed']}`.",
        "",
        verdict["short_read"],
        "",
        "## Key Macro MAE Comparisons",
        "",
        "| dataset | model | macro MAE | delta vs train mean | delta vs total allocation | delta vs raw BGE |",
        "| --- | --- | ---: | ---: | ---: | ---: |",
    ]
    for _, row in key.sort_values(["dataset_slice", "model"]).iterrows():
        lines.append(
            f"| {row['dataset_slice']} | {row['model']} | {format_value(row['macro_mae'])} | {format_value(row['delta_vs_train_mean'])} | {format_value(row['delta_vs_total_alloc_ridge'])} | {format_value(row['delta_vs_raw_bge_itemwise_ridge'])} |"
        )
    lines.extend(
        [
            "",
            "## Control Summary",
            "",
            "| model | within 5pct | beats mean | beats total alloc | feature BA | prediction BA | three-way BA |",
            "| --- | ---: | ---: | ---: | ---: | ---: | ---: |",
        ]
    )
    for _, row in best_controls.sort_values("component_count").iterrows():
        lines.append(
            f"| {row['model']} | `{bool(row['main_task_within_5pct_vs_raw_all_slices'])}` | `{bool(row['beats_train_mean_all_slices'])}` | `{bool(row['beats_total_alloc_all_slices'])}` | {format_value(row['binary_feature_identity_ba_after'])} | {format_value(row['binary_prediction_identity_ba_after'])} | {format_value(row['three_way_feature_identity_ba_after'])} |"
        )
    lines.extend(
        [
            "",
            "## Identity Probes",
            "",
            "| probe | layer | representation | BA mean | seed count |",
            "| --- | --- | --- | ---: | ---: |",
        ]
    )
    for _, row in identity.sort_values(["probe_id", "probe_layer", "representation"]).iterrows():
        lines.append(
            f"| {row['probe_id']} | {row['probe_layer']} | {row['representation']} | {format_value(row['mean'])} | {int(row['seed_count'])} |"
        )
    lines.extend(
        [
            "",
            "## Boundary",
            "",
            "- This row is a shallow identity-control diagnostic, not full method evidence.",
            "- Row-level predictions are local-only and ignored.",
            "- Projection directions, transformed features, encoder weights, and model checkpoints are not written.",
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

    features, feature_cols, feature_audit = mv07.load_bge_features(args.phase2_root)
    labels = {
        "edaic": mv07.load_phq_labels(args.manifest_dir, "edaic"),
        "cmdc": mv07.load_phq_labels(args.manifest_dir, "cmdc"),
        "pdch": mv07.load_pdch_hamd_proxy_labels(args.manifest_dir),
    }
    joined = {dataset: mv07.join_labels_features(labels[dataset], features[dataset]) for dataset in ["edaic", "cmdc", "pdch"]}
    label_feature_audit = mv07.build_label_feature_audit(labels, features, joined, feature_audit)
    label_feature_audit.to_csv(out_dir / "label_feature_audit.csv", index=False)
    mv07.build_construct_target_map().to_csv(out_dir / "construct_target_map.csv", index=False)

    phq_table = pd.concat([joined["edaic"], joined["cmdc"]], ignore_index=True)
    cmdc_folds = mv07.load_subject_folds(args.split_path, "cmdc", "cmdc_phq9_subject_cv", "phq9_total")
    predictions, identity_by_seed, model_audit, projection_audit = run_experiment(
        phq_table,
        feature_cols,
        cmdc_folds,
        features,
    )
    predictions.to_csv(out_dir / "p5_mv07b_local_predictions.csv", index=False)
    model_audit.to_csv(out_dir / "model_split_audit.csv", index=False)
    projection_audit.to_csv(out_dir / "projection_audit.csv", index=False)

    metrics_by_seed = pd.DataFrame(mv07.metric_rows_for_predictions(predictions))
    metric_summary = mv07.summarize_metrics(metrics_by_seed, predictions)
    comparison = build_comparison_summary(metric_summary)
    worst_by_seed, worst_summary = build_worst_slice_tables(metrics_by_seed, comparison)
    identity_summary = summarize_identity(identity_by_seed)
    subject_overlap_violations = int(model_audit["train_eval_subject_overlap"].sum()) + int(
        identity_by_seed["subject_overlap_count"].sum()
    )
    best_controls, verdict = build_best_control_summary(comparison, identity_summary, subject_overlap_violations)

    metrics_by_seed.to_csv(out_dir / "metrics_by_seed.csv", index=False)
    metric_summary.to_csv(out_dir / "metric_summary.csv", index=False)
    comparison.to_csv(out_dir / "comparison_summary.csv", index=False)
    worst_by_seed.to_csv(out_dir / "worst_slice_by_seed.csv", index=False)
    worst_summary.to_csv(out_dir / "worst_slice_summary.csv", index=False)
    identity_by_seed.to_csv(out_dir / "identity_probe_by_seed.csv", index=False)
    identity_summary.to_csv(out_dir / "identity_probe_summary.csv", index=False)
    best_controls.to_csv(out_dir / "best_control_summary.csv", index=False)

    run_summary: dict[str, Any] = {
        "run_id": RUN_ID,
        "generated_at": utc_now(),
        "status": "complete",
        "scope": "aligned_bge_identity_projection_follow_up",
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
            "pdch_feature_subjects_for_identity_probe": int(features["pdch"]["subject_id"].nunique()),
            "row_level_predictions_written_local_only": True,
            "clinical_source_content_read": False,
            "clinical_source_content_written": False,
            "source_locators_written": False,
            "encoder_finetuned": False,
        },
        "model_contract": {
            "heads": [TRAIN_MEAN_MODEL, TOTAL_ALLOC_MODEL, RAW_MODEL]
            + [control_model_name(component_count) for component_count in PROJECTION_COMPONENTS],
            "seeds": SEEDS,
            "ridge_alpha_grid": RIDGE_ALPHA_GRID,
            "projection_component_counts": PROJECTION_COMPONENTS,
            "control_variant": "train_fold_edaic_cmdc_iterative_logit_projection",
            "control_uses_eval_target_labels": False,
            "control_uses_eval_dataset_labels": False,
            "projection_directions_written": False,
            "model_weights_written": False,
            "subject_overlap_violations": subject_overlap_violations,
        },
        "verdict": verdict,
        "output_policy": {
            "tracked_outputs": sorted(TRACKED_FILES),
            "local_only_outputs": ["p5_mv07b_local_predictions.csv"],
        },
        "artifact_hygiene_passed": False,
    }
    (out_dir / "run_summary.json").write_text(
        json.dumps(run_summary, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    write_report(out_dir, run_summary, comparison, identity_summary, best_controls)
    hygiene = artifact_hygiene(out_dir)
    run_summary["artifact_hygiene_passed"] = bool(hygiene["artifact_hygiene_passed"])
    (out_dir / "run_summary.json").write_text(
        json.dumps(run_summary, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    write_report(out_dir, run_summary, comparison, identity_summary, best_controls)
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
                "best_control_model": verdict["best_control_model"],
                "best_binary_feature_identity_ba_after": verdict["best_binary_feature_identity_ba_after"],
                "best_binary_prediction_identity_ba_after": verdict["best_binary_prediction_identity_ba_after"],
            },
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
