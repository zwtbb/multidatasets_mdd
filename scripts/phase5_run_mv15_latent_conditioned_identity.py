#!/usr/bin/env python3
"""Run P5_MV15 latent-conditioned dataset identity audit.

MV15 asks whether dataset identity remains recoverable from aligned BGE
features after conditioning on label-derived PHQ theta, and whether theta
conditioning is better than dimension-matched severity controls. It is an
aggregate-only diagnostic audit, not a deployable depression model.
"""

from __future__ import annotations

import argparse
import json
import math
import os
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
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression, Ridge
from sklearn.metrics import balanced_accuracy_score
from sklearn.model_selection import StratifiedKFold
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

import phase5_run_mv07_aligned_bge_shared_symptom as mv07
import phase5_run_mv09_conditional_identity_audit as mv09
import phase5_run_mv12_two_stage_latent_target as mv12


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT_DIR = ROOT / "analysis" / "phase5_minimal_validation" / "p5_mv15_latent_conditioned_identity"
DEFAULT_MANIFEST_DIR = ROOT / "datasets" / "manifests"
DEFAULT_SPLIT_PATH = ROOT / "datasets" / "splits" / "phase2_subject_splits.csv"
DEFAULT_PHASE2_ROOT = ROOT / "analysis" / "phase2_baselines"

RUN_ID = "P5_MV15_latent_conditioned_dataset_identity"
PRIMARY_SCOPE = "S1_primary_edaic_cmdc_phq"
OUTPUT_SCOPE = "S2_predicted_theta_output_identity"
SENSITIVITY_SCOPES = {
    "S3_cmdc_pdch_total_sensitivity": ("cmdc", "pdch"),
    "S4_three_way_total_norm_sensitivity": ("edaic", "cmdc", "pdch"),
}
SEEDS = mv07.SEEDS
CONSTRUCTS = mv07.CONSTRUCTS
MEASUREMENT_ITEMS = mv12.MEASUREMENT_ITEMS
PHQ_COMMON_TOTAL_MAX = 24.0

PRIMARY_LADDERS = [
    {
        "ladder_id": "L0_D_given_Z_raw",
        "probe_id": "P1_primary_feature_identity_given_theta",
        "representation": "Z_bge_raw",
        "conditioning": "none",
        "kind": "raw_features",
    },
    {
        "ladder_id": "L1_D_given_Z_and_total",
        "probe_id": "P3_feature_identity_given_total_items_b3_vs_theta_delta",
        "representation": "residualized_Z_bge",
        "conditioning": "normalized_total",
        "kind": "feature_residual",
        "columns": ["severity_norm"],
    },
    {
        "ladder_id": "L2_D_given_Z_and_predicted_total",
        "probe_id": "P3_feature_identity_given_total_items_b3_vs_theta_delta",
        "representation": "residualized_Z_bge",
        "conditioning": "predicted_total",
        "kind": "feature_residual",
        "columns": ["predicted_total_norm"],
    },
    {
        "ladder_id": "L3_D_given_Z_and_items",
        "probe_id": "P3_feature_identity_given_total_items_b3_vs_theta_delta",
        "representation": "residualized_Z_bge",
        "conditioning": "C01-C08",
        "kind": "feature_residual",
        "columns": CONSTRUCTS,
    },
    {
        "ladder_id": "L4_D_given_Z_and_b3_itemwise_theta",
        "probe_id": "P3_feature_identity_given_total_items_b3_vs_theta_delta",
        "representation": "residualized_Z_bge",
        "conditioning": "B3_itemwise_theta",
        "kind": "feature_residual",
        "columns": ["b3_itemwise_theta"],
    },
    {
        "ladder_id": "L5_D_given_Z_and_theta",
        "probe_id": "P1_primary_feature_identity_given_theta",
        "representation": "residualized_Z_bge",
        "conditioning": "theta_label",
        "kind": "feature_residual",
        "columns": ["theta_label"],
    },
    {
        "ladder_id": "L6_D_given_Z_theta_covariates",
        "probe_id": "P6_covariate_sensitivity",
        "representation": "residualized_Z_bge",
        "conditioning": "theta_label_plus_shared_covariates",
        "kind": "feature_residual",
        "columns": ["theta_label", "age_numeric", "gender_numeric"],
    },
    {
        "ladder_id": "L7_D_given_theta_only",
        "probe_id": "P2_theta_distribution_identity",
        "representation": "theta_label",
        "conditioning": "none",
        "kind": "control_only",
        "columns": ["theta_label"],
    },
]

OUTPUT_LADDERS = [
    ("predicted_total", "predicted_total_norm"),
    ("B3_itemwise_theta", "b3_itemwise_theta"),
    ("psychometric_predicted_theta", "theta_pred"),
]

TRACKED_FILES = {
    "artifact_boundary_summary.csv",
    "artifact_hygiene_audit.json",
    "conditioning_identity_by_seed.csv",
    "conditioning_identity_summary.csv",
    "covariate_coverage_summary.csv",
    "external_sensitivity_by_seed.csv",
    "external_sensitivity_summary.csv",
    "input_audit.csv",
    "output_identity_by_seed.csv",
    "output_identity_summary.csv",
    "output_metric_by_seed.csv",
    "output_metric_summary.csv",
    "pass_fail_gate_results.csv",
    "report.md",
    "run_summary.json",
    "split_audit_summary.csv",
    "target_generation_summary.csv",
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
        return str(path)


def class_count_text(values: pd.Series) -> str:
    counts = values.astype(str).value_counts().sort_index()
    return ";".join(f"{key}:{int(value)}" for key, value in counts.items())


def dataset_codes(frame: pd.DataFrame, labels: tuple[str, ...]) -> np.ndarray:
    mapping = {dataset: idx for idx, dataset in enumerate(labels)}
    return frame["dataset"].astype(str).map(mapping).to_numpy(dtype=int)


def identity_classifier(seed: int) -> Pipeline:
    return Pipeline(
        [
            ("imputer", SimpleImputer(strategy="median")),
            ("scaler", StandardScaler()),
            (
                "classifier",
                LogisticRegression(C=1.0, class_weight="balanced", max_iter=2000, random_state=seed),
            ),
        ]
    )


def score_identity(
    x_train: np.ndarray,
    x_eval: np.ndarray,
    train: pd.DataFrame,
    eval_frame: pd.DataFrame,
    labels: tuple[str, ...],
    seed: int,
) -> float:
    y_train = dataset_codes(train, labels)
    y_eval = dataset_codes(eval_frame, labels)
    train_counts = np.bincount(y_train, minlength=len(labels))
    eval_counts = np.bincount(y_eval, minlength=len(labels))
    if np.min(train_counts) < 2 or np.min(eval_counts) < 1:
        raise ValueError("identity split has insufficient dataset class support")
    x_train_arr = np.asarray(x_train, dtype=float)
    x_eval_arr = np.asarray(x_eval, dtype=float)
    if x_train_arr.ndim == 1:
        x_train_arr = x_train_arr.reshape(-1, 1)
    if x_eval_arr.ndim == 1:
        x_eval_arr = x_eval_arr.reshape(-1, 1)
    if x_train_arr.shape[0] != len(train) and x_train_arr.ndim == 2 and x_train_arr.shape[1] == len(train):
        x_train_arr = x_train_arr.T
    if x_eval_arr.shape[0] != len(eval_frame) and x_eval_arr.ndim == 2 and x_eval_arr.shape[1] == len(eval_frame):
        x_eval_arr = x_eval_arr.T
    if x_train_arr.shape[0] != len(train) or x_eval_arr.shape[0] != len(eval_frame):
        raise ValueError(
            f"identity representation rows mismatch: train {x_train_arr.shape} for {len(train)}, "
            f"eval {x_eval_arr.shape} for {len(eval_frame)}"
        )
    if x_train_arr.shape[1] != x_eval_arr.shape[1]:
        raise ValueError(f"identity representation feature mismatch: train {x_train_arr.shape}, eval {x_eval_arr.shape}")
    model = identity_classifier(seed)
    model.fit(x_train_arr, y_train)
    pred = model.predict(x_eval_arr)
    return float(balanced_accuracy_score(y_eval, pred))


def condition_matrix(
    train: pd.DataFrame,
    eval_frame: pd.DataFrame,
    columns: list[str],
) -> tuple[np.ndarray | None, np.ndarray | None, list[str], str | None]:
    if not columns:
        return None, None, [], "condition_columns_empty"
    valid: list[str] = []
    for column in columns:
        train_coverage = float(np.isfinite(train[column].to_numpy(dtype=float)).mean())
        eval_coverage = float(np.isfinite(eval_frame[column].to_numpy(dtype=float)).mean())
        if train_coverage >= 0.80 and eval_coverage >= 0.80:
            valid.append(column)
    if not valid:
        return None, None, [], "no_condition_column_with_80pct_train_eval_coverage"
    imputer = SimpleImputer(strategy="median")
    scaler = StandardScaler()
    c_train_raw = train[valid].to_numpy(dtype=float)
    c_eval_raw = eval_frame[valid].to_numpy(dtype=float)
    c_train = scaler.fit_transform(imputer.fit_transform(c_train_raw))
    c_eval = scaler.transform(imputer.transform(c_eval_raw))
    return c_train, c_eval, valid, None


def feature_matrices(
    train: pd.DataFrame,
    eval_frame: pd.DataFrame,
    feature_cols: list[str],
) -> tuple[np.ndarray, np.ndarray]:
    imputer = SimpleImputer(strategy="median")
    x_train = imputer.fit_transform(train[feature_cols].to_numpy(dtype=float))
    x_eval = imputer.transform(eval_frame[feature_cols].to_numpy(dtype=float))
    return x_train, x_eval


def residualize_features(
    train: pd.DataFrame,
    eval_frame: pd.DataFrame,
    feature_cols: list[str],
    condition_cols: list[str],
) -> tuple[np.ndarray | None, np.ndarray | None, list[str], str | None]:
    c_train, c_eval, used, skipped = condition_matrix(train, eval_frame, condition_cols)
    if skipped is not None:
        return None, None, used, skipped
    if c_train is None or c_eval is None:
        raise RuntimeError("condition_matrix returned no matrix without a skip reason")
    x_train, x_eval = feature_matrices(train, eval_frame, feature_cols)
    model = Ridge(alpha=1.0)
    model.fit(c_train, x_train)
    return x_train - model.predict(c_train), x_eval - model.predict(c_eval), used, None


def residualize_values(
    train: pd.DataFrame,
    eval_frame: pd.DataFrame,
    value_col: str,
    condition_cols: list[str],
) -> tuple[np.ndarray | None, np.ndarray | None, list[str], str | None]:
    c_train, c_eval, used, skipped = condition_matrix(train, eval_frame, condition_cols)
    if skipped is not None:
        return None, None, used, skipped
    if c_train is None or c_eval is None:
        raise RuntimeError("condition_matrix returned no matrix without a skip reason")
    y_train = train[[value_col]].to_numpy(dtype=float)
    y_eval = eval_frame[[value_col]].to_numpy(dtype=float)
    imputer = SimpleImputer(strategy="median")
    y_train_i = imputer.fit_transform(y_train)
    y_eval_i = imputer.transform(y_eval)
    model = Ridge(alpha=1.0)
    model.fit(c_train, y_train_i)
    train_pred = np.asarray(model.predict(c_train), dtype=float).reshape(-1, 1)
    eval_pred = np.asarray(model.predict(c_eval), dtype=float).reshape(-1, 1)
    return y_train_i - train_pred, y_eval_i - eval_pred, used, None


def common_total(frame: pd.DataFrame) -> np.ndarray:
    return frame[CONSTRUCTS].sum(axis=1).to_numpy(dtype=float)


def fit_predicted_total_controls(
    train: pd.DataFrame,
    eval_frame: pd.DataFrame,
    feature_cols: list[str],
    seed: int,
) -> tuple[np.ndarray, np.ndarray, float]:
    x_train = train[feature_cols].to_numpy(dtype=float)
    y_train = common_total(train)
    x_eval = eval_frame[feature_cols].to_numpy(dtype=float)
    alpha = mv07.choose_alpha(x_train, y_train.reshape(-1, 1), seed)
    model = mv12.ridge_pipeline(alpha)
    model.fit(x_train, y_train)
    pred_train = np.clip(np.asarray(model.predict(x_train), dtype=float).reshape(-1), 0.0, PHQ_COMMON_TOTAL_MAX)
    pred_eval = np.clip(np.asarray(model.predict(x_eval), dtype=float).reshape(-1), 0.0, PHQ_COMMON_TOTAL_MAX)
    return pred_train / PHQ_COMMON_TOTAL_MAX, pred_eval / PHQ_COMMON_TOTAL_MAX, float(alpha)


def fit_predicted_itemwise_controls(
    train: pd.DataFrame,
    eval_frame: pd.DataFrame,
    theta_train: np.ndarray,
    feature_cols: list[str],
    seed: int,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, float]:
    item_mapper = mv12.fit_item_to_theta_mapper(train, theta_train)
    x_train = train[feature_cols].to_numpy(dtype=float)
    y_train = train[CONSTRUCTS].to_numpy(dtype=float)
    x_eval = eval_frame[feature_cols].to_numpy(dtype=float)
    alpha = mv07.choose_alpha(x_train, y_train, seed)
    model = mv12.ridge_pipeline(alpha)
    model.fit(x_train, y_train)
    pred_train_items = mv12.clip_items(model.predict(x_train))
    pred_eval_items = mv12.clip_items(model.predict(x_eval))
    pred_train_theta = mv12.direct_items_to_theta(item_mapper, pred_train_items)
    pred_eval_theta = mv12.direct_items_to_theta(item_mapper, pred_eval_items)
    return pred_train_theta, pred_eval_theta, pred_train_items, pred_eval_items, float(alpha)


def fit_predicted_theta_controls(
    train: pd.DataFrame,
    eval_frame: pd.DataFrame,
    theta_train: np.ndarray,
    feature_cols: list[str],
    seed: int,
) -> tuple[np.ndarray, np.ndarray, float]:
    x_train = train[feature_cols].to_numpy(dtype=float)
    x_eval = eval_frame[feature_cols].to_numpy(dtype=float)
    alpha = mv07.choose_alpha(x_train, np.asarray(theta_train, dtype=float).reshape(-1, 1), seed)
    model = mv12.ridge_pipeline(alpha)
    model.fit(x_train, theta_train)
    pred_train = np.asarray(model.predict(x_train), dtype=float).reshape(-1)
    pred_eval = np.asarray(model.predict(x_eval), dtype=float).reshape(-1)
    return pred_train, pred_eval, float(alpha)


def add_fold_controls(
    train: pd.DataFrame,
    eval_frame: pd.DataFrame,
    feature_cols: list[str],
    seed: int,
) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, Any], dict[str, np.ndarray]]:
    measurement_train = train.copy()
    fit = mv12.fit_measurement_model(measurement_train, MEASUREMENT_ITEMS)
    if not fit.optimizer_success:
        raise RuntimeError(f"MV15 measurement fit failed for seed {seed}: {fit.optimizer_message}")

    theta_train, train_fallback = mv12.score_theta(train, fit)
    theta_eval, eval_fallback = mv12.score_theta(eval_frame, fit)
    pred_total_train, pred_total_eval, total_alpha = fit_predicted_total_controls(train, eval_frame, feature_cols, seed)
    b3_train, b3_eval, b3_train_items, b3_eval_items, b3_alpha = fit_predicted_itemwise_controls(
        train, eval_frame, theta_train, feature_cols, seed
    )
    theta_pred_train, theta_pred_eval, theta_alpha = fit_predicted_theta_controls(
        train, eval_frame, theta_train, feature_cols, seed
    )

    train_ctx = train.copy()
    eval_ctx = eval_frame.copy()
    for frame, theta, pred_total, b3_theta, theta_pred in [
        (train_ctx, theta_train, pred_total_train, b3_train, theta_pred_train),
        (eval_ctx, theta_eval, pred_total_eval, b3_eval, theta_pred_eval),
    ]:
        frame["common_phq_total"] = common_total(frame)
        frame["severity_norm"] = frame["common_phq_total"] / PHQ_COMMON_TOTAL_MAX
        frame["theta_label"] = theta
        frame["predicted_total_norm"] = pred_total
        frame["b3_itemwise_theta"] = b3_theta
        frame["theta_pred"] = theta_pred

    theta_mapper = mv12.fit_theta_to_observed_mapper(train, theta_train)
    theta_pred_eval_items = theta_mapper.predict(theta_pred_eval, eval_frame["dataset"])
    target_summary = {
        "seed": int(seed),
        "fold": str(eval_frame.attrs.get("fold_name", "")),
        "scope_id": PRIMARY_SCOPE,
        "measurement_items": ";".join(MEASUREMENT_ITEMS),
        "anchor_items": ";".join(mv12.ANCHOR_ITEMS),
        "dif_aware_items": ";".join(mv12.DIF_AWARE_ITEMS),
        "measurement_train_participants": int(fit.n_subjects),
        "measurement_train_datasets": ";".join(fit.spec.groups),
        "measurement_optimizer_success": bool(fit.optimizer_success),
        "measurement_optimizer_iterations": int(fit.optimizer_iterations),
        "measurement_boundary_parameter_count": int(fit.boundary_parameter_count),
        "theta_train_mean": safe_float(np.mean(theta_train)),
        "theta_train_std": safe_float(np.std(theta_train, ddof=1)),
        "theta_eval_mean": safe_float(np.mean(theta_eval)),
        "theta_eval_std": safe_float(np.std(theta_eval, ddof=1)),
        "theta_eval_total_spearman": mv12.spearman(theta_eval, eval_ctx["common_phq_total"]),
        "train_measurement_group_fallback_count": int(train_fallback),
        "eval_measurement_group_fallback_count": int(eval_fallback),
        "selected_alpha_predicted_total": float(total_alpha),
        "selected_alpha_b3_itemwise": float(b3_alpha),
        "selected_alpha_predicted_theta": float(theta_alpha),
        "theta_scores_written_to_tracked_outputs": False,
        "row_predictions_written_to_tracked_outputs": False,
        "residualized_features_written_to_tracked_outputs": False,
        "fitted_parameters_written_to_tracked_outputs": False,
    }
    arrays = {
        "b3_eval_items": b3_eval_items,
        "theta_pred_eval_items": theta_pred_eval_items,
    }
    return train_ctx, eval_ctx, target_summary, arrays


def split_row(
    scope_id: str,
    seed: int,
    fold: str,
    train: pd.DataFrame,
    eval_frame: pd.DataFrame,
    labels: tuple[str, ...],
) -> dict[str, Any]:
    train_keys = set(train["subject_key"].astype(str))
    eval_keys = set(eval_frame["subject_key"].astype(str))
    return {
        "scope_id": scope_id,
        "seed": int(seed),
        "fold": str(fold),
        "datasets": ";".join(labels),
        "train_subjects": int(len(train_keys)),
        "eval_subjects": int(len(eval_keys)),
        "train_class_counts": class_count_text(train["dataset"]),
        "eval_class_counts": class_count_text(eval_frame["dataset"]),
        "train_eval_overlap_count": int(len(train_keys & eval_keys)),
    }


def skipped_identity_row(
    *,
    scope_id: str,
    ladder_id: str,
    probe_id: str,
    seed: int,
    fold: str,
    datasets: tuple[str, ...],
    representation: str,
    conditioning: str,
    skipped_reason: str,
    train: pd.DataFrame,
    eval_frame: pd.DataFrame,
    condition_columns_used: list[str],
) -> dict[str, Any]:
    return {
        "run_id": RUN_ID,
        "scope_id": scope_id,
        "ladder_id": ladder_id,
        "probe_id": probe_id,
        "seed": int(seed),
        "fold": str(fold),
        "datasets": ";".join(datasets),
        "representation": representation,
        "conditioning": conditioning,
        "condition_columns_used": ";".join(condition_columns_used),
        "metric": "Balanced Accuracy",
        "value": None,
        "train_subjects": int(train["subject_key"].nunique()),
        "eval_subjects": int(eval_frame["subject_key"].nunique()),
        "train_class_counts": class_count_text(train["dataset"]),
        "eval_class_counts": class_count_text(eval_frame["dataset"]),
        "residualized_features": False,
        "control_only": False,
        "train_eval_overlap_count": int(len(set(train["subject_key"]) & set(eval_frame["subject_key"]))),
        "skipped_reason": skipped_reason,
    }


def completed_identity_row(
    *,
    scope_id: str,
    ladder_id: str,
    probe_id: str,
    seed: int,
    fold: str,
    datasets: tuple[str, ...],
    representation: str,
    conditioning: str,
    value: float,
    train: pd.DataFrame,
    eval_frame: pd.DataFrame,
    condition_columns_used: list[str],
    residualized: bool,
    control_only: bool,
) -> dict[str, Any]:
    return {
        "run_id": RUN_ID,
        "scope_id": scope_id,
        "ladder_id": ladder_id,
        "probe_id": probe_id,
        "seed": int(seed),
        "fold": str(fold),
        "datasets": ";".join(datasets),
        "representation": representation,
        "conditioning": conditioning,
        "condition_columns_used": ";".join(condition_columns_used),
        "metric": "Balanced Accuracy",
        "value": safe_float(value),
        "train_subjects": int(train["subject_key"].nunique()),
        "eval_subjects": int(eval_frame["subject_key"].nunique()),
        "train_class_counts": class_count_text(train["dataset"]),
        "eval_class_counts": class_count_text(eval_frame["dataset"]),
        "residualized_features": bool(residualized),
        "control_only": bool(control_only),
        "train_eval_overlap_count": int(len(set(train["subject_key"]) & set(eval_frame["subject_key"]))),
        "skipped_reason": None,
    }


def run_primary_ladder(
    train: pd.DataFrame,
    eval_frame: pd.DataFrame,
    feature_cols: list[str],
    seed: int,
    fold: str,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    datasets = ("edaic", "cmdc")
    for spec in PRIMARY_LADDERS:
        kind = str(spec["kind"])
        columns = list(spec.get("columns", []))
        if kind == "raw_features":
            x_train, x_eval = feature_matrices(train, eval_frame, feature_cols)
            value = score_identity(x_train, x_eval, train, eval_frame, datasets, seed)
            rows.append(
                completed_identity_row(
                    scope_id=PRIMARY_SCOPE,
                    ladder_id=str(spec["ladder_id"]),
                    probe_id=str(spec["probe_id"]),
                    seed=seed,
                    fold=fold,
                    datasets=datasets,
                    representation=str(spec["representation"]),
                    conditioning=str(spec["conditioning"]),
                    value=value,
                    train=train,
                    eval_frame=eval_frame,
                    condition_columns_used=[],
                    residualized=False,
                    control_only=False,
                )
            )
        elif kind == "feature_residual":
            x_train, x_eval, used, skipped = residualize_features(train, eval_frame, feature_cols, columns)
            if skipped is not None:
                rows.append(
                    skipped_identity_row(
                        scope_id=PRIMARY_SCOPE,
                        ladder_id=str(spec["ladder_id"]),
                        probe_id=str(spec["probe_id"]),
                        seed=seed,
                        fold=fold,
                        datasets=datasets,
                        representation=str(spec["representation"]),
                        conditioning=str(spec["conditioning"]),
                        skipped_reason=skipped,
                        train=train,
                        eval_frame=eval_frame,
                        condition_columns_used=used,
                    )
                )
                continue
            if x_train is None or x_eval is None:
                raise RuntimeError("residualize_features returned no matrix without a skip reason")
            value = score_identity(x_train, x_eval, train, eval_frame, datasets, seed)
            rows.append(
                completed_identity_row(
                    scope_id=PRIMARY_SCOPE,
                    ladder_id=str(spec["ladder_id"]),
                    probe_id=str(spec["probe_id"]),
                    seed=seed,
                    fold=fold,
                    datasets=datasets,
                    representation=str(spec["representation"]),
                    conditioning=str(spec["conditioning"]),
                    value=value,
                    train=train,
                    eval_frame=eval_frame,
                    condition_columns_used=used,
                    residualized=True,
                    control_only=False,
                )
            )
        elif kind == "control_only":
            c_train, c_eval, used, skipped = condition_matrix(train, eval_frame, columns)
            if skipped is not None:
                rows.append(
                    skipped_identity_row(
                        scope_id=PRIMARY_SCOPE,
                        ladder_id=str(spec["ladder_id"]),
                        probe_id=str(spec["probe_id"]),
                        seed=seed,
                        fold=fold,
                        datasets=datasets,
                        representation=str(spec["representation"]),
                        conditioning=str(spec["conditioning"]),
                        skipped_reason=skipped,
                        train=train,
                        eval_frame=eval_frame,
                        condition_columns_used=used,
                    )
                )
                continue
            if c_train is None or c_eval is None:
                raise RuntimeError("condition_matrix returned no matrix without a skip reason")
            value = score_identity(c_train, c_eval, train, eval_frame, datasets, seed)
            rows.append(
                completed_identity_row(
                    scope_id=PRIMARY_SCOPE,
                    ladder_id=str(spec["ladder_id"]),
                    probe_id=str(spec["probe_id"]),
                    seed=seed,
                    fold=fold,
                    datasets=datasets,
                    representation=str(spec["representation"]),
                    conditioning=str(spec["conditioning"]),
                    value=value,
                    train=train,
                    eval_frame=eval_frame,
                    condition_columns_used=used,
                    residualized=False,
                    control_only=True,
                )
            )
        else:
            raise ValueError(f"unknown MV15 ladder kind: {kind}")
    return rows


def run_output_ladder(
    train: pd.DataFrame,
    eval_frame: pd.DataFrame,
    seed: int,
    fold: str,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    datasets = ("edaic", "cmdc")
    for label, column in OUTPUT_LADDERS:
        for conditioning, condition_cols in [
            ("none", []),
            ("theta_label_and_total", ["theta_label", "severity_norm"]),
        ]:
            if conditioning == "none":
                x_train = train[[column]].to_numpy(dtype=float)
                x_eval = eval_frame[[column]].to_numpy(dtype=float)
                used: list[str] = []
                skipped = None
                representation = column
            else:
                x_train, x_eval, used, skipped = residualize_values(train, eval_frame, column, condition_cols)
                representation = f"{column}_residual"
            if skipped is not None:
                rows.append(
                    skipped_identity_row(
                        scope_id=OUTPUT_SCOPE,
                        ladder_id="L8_D_given_predicted_outputs",
                        probe_id="P4_predicted_theta_output_identity",
                        seed=seed,
                        fold=fold,
                        datasets=datasets,
                        representation=representation,
                        conditioning=conditioning,
                        skipped_reason=skipped,
                        train=train,
                        eval_frame=eval_frame,
                        condition_columns_used=used,
                    )
                )
                continue
            if x_train is None or x_eval is None:
                raise RuntimeError("output ladder produced no matrix without a skip reason")
            value = score_identity(x_train, x_eval, train, eval_frame, datasets, seed)
            rows.append(
                completed_identity_row(
                    scope_id=OUTPUT_SCOPE,
                    ladder_id="L8_D_given_predicted_outputs",
                    probe_id="P4_predicted_theta_output_identity",
                    seed=seed,
                    fold=fold,
                    datasets=datasets,
                    representation=representation,
                    conditioning=conditioning,
                    value=value,
                    train=train,
                    eval_frame=eval_frame,
                    condition_columns_used=used,
                    residualized=conditioning != "none",
                    control_only=True,
                )
                | {"output_model": label}
            )
    return rows


def output_metric_rows(
    eval_frame: pd.DataFrame,
    arrays: dict[str, np.ndarray],
    seed: int,
    fold: str,
) -> list[dict[str, Any]]:
    true_items = eval_frame[CONSTRUCTS].to_numpy(dtype=float)
    true_total_norm = eval_frame["severity_norm"].to_numpy(dtype=float)
    true_theta = eval_frame["theta_label"].to_numpy(dtype=float)
    rows = [
        {
            "seed": int(seed),
            "fold": fold,
            "scope_id": OUTPUT_SCOPE,
            "output_model": "predicted_total",
            "metric": "Normalized Total MAE",
            "value": safe_float(np.mean(np.abs(eval_frame["predicted_total_norm"].to_numpy(dtype=float) - true_total_norm))),
        },
        {
            "seed": int(seed),
            "fold": fold,
            "scope_id": OUTPUT_SCOPE,
            "output_model": "predicted_total",
            "metric": "Raw Total MAE",
            "value": safe_float(
                np.mean(
                    np.abs(
                        eval_frame["predicted_total_norm"].to_numpy(dtype=float) * PHQ_COMMON_TOTAL_MAX
                        - true_total_norm * PHQ_COMMON_TOTAL_MAX
                    )
                )
            ),
        },
        {
            "seed": int(seed),
            "fold": fold,
            "scope_id": OUTPUT_SCOPE,
            "output_model": "B3_itemwise_theta",
            "metric": "Theta MAE",
            "value": safe_float(np.mean(np.abs(eval_frame["b3_itemwise_theta"].to_numpy(dtype=float) - true_theta))),
        },
        {
            "seed": int(seed),
            "fold": fold,
            "scope_id": OUTPUT_SCOPE,
            "output_model": "B3_itemwise_theta",
            "metric": "Observed Macro Item MAE",
            "value": safe_float(np.mean(np.abs(arrays["b3_eval_items"] - true_items))),
        },
        {
            "seed": int(seed),
            "fold": fold,
            "scope_id": OUTPUT_SCOPE,
            "output_model": "B3_itemwise_theta",
            "metric": "Observed Total MAE",
            "value": safe_float(np.mean(np.abs(arrays["b3_eval_items"].sum(axis=1) - true_items.sum(axis=1)))),
        },
        {
            "seed": int(seed),
            "fold": fold,
            "scope_id": OUTPUT_SCOPE,
            "output_model": "psychometric_predicted_theta",
            "metric": "Theta MAE",
            "value": safe_float(np.mean(np.abs(eval_frame["theta_pred"].to_numpy(dtype=float) - true_theta))),
        },
        {
            "seed": int(seed),
            "fold": fold,
            "scope_id": OUTPUT_SCOPE,
            "output_model": "psychometric_predicted_theta",
            "metric": "Observed Macro Item MAE",
            "value": safe_float(np.mean(np.abs(arrays["theta_pred_eval_items"] - true_items))),
        },
        {
            "seed": int(seed),
            "fold": fold,
            "scope_id": OUTPUT_SCOPE,
            "output_model": "psychometric_predicted_theta",
            "metric": "Observed Total MAE",
            "value": safe_float(np.mean(np.abs(arrays["theta_pred_eval_items"].sum(axis=1) - true_items.sum(axis=1)))),
        },
    ]
    return rows


def run_external_sensitivity_for_scope(
    table: pd.DataFrame,
    feature_cols: list[str],
    scope_id: str,
    datasets: tuple[str, ...],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    data = table[table["dataset"].isin(datasets)].copy()
    labels = datasets
    y = dataset_codes(data, labels)
    min_class = int(np.min(np.bincount(y, minlength=len(labels))))
    if min_class < 3:
        raise ValueError(f"{scope_id} has insufficient per-dataset samples")
    n_splits = min(5, min_class)
    rows: list[dict[str, Any]] = []
    split_rows: list[dict[str, Any]] = []
    strategies = [
        ("L0_D_given_Z_raw", "P7_severity_only_external_sensitivity", "raw_bge_unconditional", "raw_features", []),
        (
            "L9_severity_only_sensitivity",
            "P7_severity_only_external_sensitivity",
            "normalized_total_residualized_bge",
            "feature_residual",
            ["severity_norm"],
        ),
        (
            "L9_severity_only_sensitivity",
            "P7_severity_only_external_sensitivity",
            "severity_only_control",
            "control_only",
            ["severity_norm"],
        ),
    ]
    for seed in SEEDS:
        splitter = StratifiedKFold(n_splits=n_splits, shuffle=True, random_state=seed)
        for fold_idx, (train_idx, eval_idx) in enumerate(splitter.split(data, y)):
            train = data.iloc[train_idx].copy()
            eval_frame = data.iloc[eval_idx].copy()
            fold = f"stratified_cv_fold{fold_idx}"
            split_rows.append(split_row(scope_id, seed, fold, train, eval_frame, labels))
            for ladder_id, probe_id, strategy, kind, columns in strategies:
                if kind == "raw_features":
                    x_train, x_eval = feature_matrices(train, eval_frame, feature_cols)
                    used: list[str] = []
                    skipped = None
                    residualized = False
                    control_only = False
                elif kind == "feature_residual":
                    x_train, x_eval, used, skipped = residualize_features(train, eval_frame, feature_cols, columns)
                    residualized = True
                    control_only = False
                elif kind == "control_only":
                    x_train, x_eval, used, skipped = condition_matrix(train, eval_frame, columns)
                    residualized = False
                    control_only = True
                else:
                    raise ValueError(kind)
                if skipped is not None:
                    rows.append(
                        skipped_identity_row(
                            scope_id=scope_id,
                            ladder_id=ladder_id,
                            probe_id=probe_id,
                            seed=seed,
                            fold=fold,
                            datasets=labels,
                            representation=strategy,
                            conditioning="normalized_total" if columns else "none",
                            skipped_reason=skipped,
                            train=train,
                            eval_frame=eval_frame,
                            condition_columns_used=used,
                        )
                    )
                    continue
                if x_train is None or x_eval is None:
                    raise RuntimeError("external sensitivity produced no matrix without a skip reason")
                value = score_identity(x_train, x_eval, train, eval_frame, labels, seed + 100 * fold_idx)
                rows.append(
                    completed_identity_row(
                        scope_id=scope_id,
                        ladder_id=ladder_id,
                        probe_id=probe_id,
                        seed=seed,
                        fold=fold,
                        datasets=labels,
                        representation=strategy,
                        conditioning="normalized_total" if columns else "none",
                        value=value,
                        train=train,
                        eval_frame=eval_frame,
                        condition_columns_used=used,
                        residualized=residualized,
                        control_only=control_only,
                    )
                )
    return rows, split_rows


def summarize_identity(frame: pd.DataFrame) -> pd.DataFrame:
    if frame.empty:
        return pd.DataFrame()
    grouped = (
        frame.groupby(
            [
                "scope_id",
                "ladder_id",
                "probe_id",
                "datasets",
                "representation",
                "conditioning",
                "metric",
            ],
            dropna=False,
        )
        .agg(
            mean=("value", "mean"),
            std=("value", "std"),
            seed_count=("seed", "nunique"),
            completed_seed_rows=("value", lambda s: int(pd.to_numeric(s, errors="coerce").notna().sum())),
            eval_subjects_mean=("eval_subjects", "mean"),
            skipped_reasons=("skipped_reason", lambda s: ";".join(sorted({str(v) for v in s.dropna() if str(v)}))),
        )
        .reset_index()
    )
    grouped["std"] = grouped["std"].fillna(0.0)
    return grouped


def summarize_metrics(frame: pd.DataFrame) -> pd.DataFrame:
    return (
        frame.groupby(["scope_id", "output_model", "metric"], dropna=False)
        .agg(mean=("value", "mean"), std=("value", "std"), seed_count=("seed", "nunique"))
        .reset_index()
        .fillna({"std": 0.0})
    )


def build_input_audit(table: pd.DataFrame, feature_audit: pd.DataFrame, feature_cols: list[str]) -> pd.DataFrame:
    feature_lookup = feature_audit.set_index("dataset").to_dict("index")
    rows: list[dict[str, Any]] = []
    for dataset, group in table.groupby("dataset", sort=True):
        feature_info = feature_lookup[str(dataset)]
        rows.append(
            {
                "dataset": dataset,
                "feature_family": "text_bge",
                "feature_subjects": int(feature_info["feature_subjects"]),
                "joined_subjects": int(group["subject_id"].nunique()),
                "model_input_columns": int(len(feature_cols)),
                "target_family": group["target_family"].iloc[0],
                "severity_norm_mean": safe_float(group["severity_norm"].mean()),
                "severity_norm_std": safe_float(group["severity_norm"].std(ddof=0)),
                "raw_text_or_media_read": False,
                "row_level_predictions_read": False,
                "features_written_to_tracked_outputs": False,
                "path_like_feature_columns": feature_info.get("path_like_columns", ""),
            }
        )
    return pd.DataFrame(rows)


def covariate_coverage(table: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for dataset, group in table[table["dataset"].isin(["edaic", "cmdc"])].groupby("dataset", sort=True):
        for column in ["age_numeric", "gender_numeric"]:
            rows.append(
                {
                    "scope_id": PRIMARY_SCOPE,
                    "dataset": dataset,
                    "covariate": column,
                    "subject_count": int(group["subject_id"].nunique()),
                    "finite_coverage": safe_float(np.isfinite(group[column].to_numpy(dtype=float)).mean()),
                    "usable_for_primary_sensitivity": bool(
                        np.isfinite(group[column].to_numpy(dtype=float)).mean() >= 0.80
                    ),
                }
            )
    return pd.DataFrame(rows)


def target_distribution_rows(eval_frame: pd.DataFrame, seed: int, fold: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for dataset, group in eval_frame.groupby("dataset", sort=True):
        rows.append(
            {
                "seed": int(seed),
                "fold": fold,
                "scope_id": PRIMARY_SCOPE,
                "dataset": dataset,
                "eval_subjects": int(group["subject_id"].nunique()),
                "severity_norm_mean": safe_float(group["severity_norm"].mean()),
                "severity_norm_std": safe_float(group["severity_norm"].std(ddof=0)),
                "theta_label_mean": safe_float(group["theta_label"].mean()),
                "theta_label_std": safe_float(group["theta_label"].std(ddof=0)),
                "theta_label_min": safe_float(group["theta_label"].min()),
                "theta_label_max": safe_float(group["theta_label"].max()),
            }
        )
    return rows


def identity_lookup(summary: pd.DataFrame, scope_id: str, ladder_id: str, representation: str | None = None, conditioning: str | None = None) -> float | None:
    rows = summary[(summary["scope_id"] == scope_id) & (summary["ladder_id"] == ladder_id)].copy()
    if representation is not None:
        rows = rows[rows["representation"] == representation]
    if conditioning is not None:
        rows = rows[rows["conditioning"] == conditioning]
    if rows.empty:
        return None
    return safe_float(rows.iloc[0]["mean"])


def metric_lookup(summary: pd.DataFrame, model: str, metric: str) -> float | None:
    rows = summary[(summary["output_model"] == model) & (summary["metric"] == metric)]
    if rows.empty:
        return None
    return safe_float(rows.iloc[0]["mean"])


def output_identity_lookup(summary: pd.DataFrame, output_model: str, conditioning: str) -> float | None:
    rows = summary[
        (summary["scope_id"] == OUTPUT_SCOPE)
        & (summary["ladder_id"] == "L8_D_given_predicted_outputs")
        & (summary["conditioning"] == conditioning)
    ].copy()
    if "output_model" in rows.columns:
        rows = rows[rows["output_model"] == output_model]
    else:
        rows = rows[rows["representation"].astype(str).str.contains(output_model, regex=False)]
    if rows.empty:
        return None
    return safe_float(rows.iloc[0]["mean"])


def add_output_model_to_summary(summary: pd.DataFrame, by_seed: pd.DataFrame) -> pd.DataFrame:
    if summary.empty or by_seed.empty or "output_model" not in by_seed.columns:
        return summary
    keys = [
        "scope_id",
        "ladder_id",
        "probe_id",
        "datasets",
        "representation",
        "conditioning",
        "metric",
    ]
    model_map = by_seed[keys + ["output_model"]].drop_duplicates()
    return summary.merge(model_map, on=keys, how="left")


def build_verdict(
    conditioning_summary: pd.DataFrame,
    output_identity_summary: pd.DataFrame,
    output_metric_summary: pd.DataFrame,
    split_audit: pd.DataFrame,
) -> dict[str, Any]:
    raw_ba = identity_lookup(conditioning_summary, PRIMARY_SCOPE, "L0_D_given_Z_raw")
    total_ba = identity_lookup(conditioning_summary, PRIMARY_SCOPE, "L1_D_given_Z_and_total")
    pred_total_ba = identity_lookup(conditioning_summary, PRIMARY_SCOPE, "L2_D_given_Z_and_predicted_total")
    item_ba = identity_lookup(conditioning_summary, PRIMARY_SCOPE, "L3_D_given_Z_and_items")
    b3_ba = identity_lookup(conditioning_summary, PRIMARY_SCOPE, "L4_D_given_Z_and_b3_itemwise_theta")
    theta_ba = identity_lookup(conditioning_summary, PRIMARY_SCOPE, "L5_D_given_Z_and_theta")
    theta_only_ba = identity_lookup(conditioning_summary, PRIMARY_SCOPE, "L7_D_given_theta_only")

    control_values = [value for value in [total_ba, pred_total_ba, b3_ba] if value is not None]
    full_primary_ladder = all(value is not None for value in [raw_ba, total_ba, pred_total_ba, item_ba, b3_ba, theta_ba])
    theta_lower_by_003 = bool(
        theta_ba is not None and control_values and all(theta_ba <= value - 0.03 for value in control_values)
    )
    theta_not_worse = bool(
        theta_ba is not None and control_values and all(theta_ba <= value + 0.005 for value in control_values)
    )

    b3_output_identity = output_identity_lookup(output_identity_summary, "B3_itemwise_theta", "none")
    psych_output_identity = output_identity_lookup(output_identity_summary, "psychometric_predicted_theta", "none")
    b3_macro = metric_lookup(output_metric_summary, "B3_itemwise_theta", "Observed Macro Item MAE")
    psych_macro = metric_lookup(output_metric_summary, "psychometric_predicted_theta", "Observed Macro Item MAE")
    b3_pareto = bool(
        b3_output_identity is not None
        and psych_output_identity is not None
        and b3_macro is not None
        and psych_macro is not None
        and b3_output_identity <= psych_output_identity
        and b3_macro <= psych_macro
    )
    overlap = int(split_audit["train_eval_overlap_count"].sum()) if not split_audit.empty else 0

    if overlap:
        status = "blocked_subject_overlap"
        pass_rule_met = False
    elif not full_primary_ladder:
        status = "blocked_incomplete_primary_conditioning_ladder"
        pass_rule_met = False
    elif theta_ba is not None and theta_ba <= 0.70 and theta_lower_by_003:
        status = "pass_theta_conditioning_beats_dimension_matched_controls_diagnostic_only"
        pass_rule_met = True
    elif theta_ba is not None and theta_ba <= 0.75 and theta_not_worse:
        status = "partial_theta_conditioning_ties_dimension_matched_controls"
        pass_rule_met = None
    elif theta_ba is not None and theta_ba > 0.80:
        status = "blocked_theta_conditioned_feature_identity_high"
        pass_rule_met = False
    elif b3_pareto:
        status = "blocked_b3_dimension_matched_output_dominates_predicted_theta"
        pass_rule_met = False
    else:
        status = "blocked_theta_conditioning_not_better_than_dimension_matched_controls"
        pass_rule_met = False

    return {
        "status": status,
        "pass_rule_status": status,
        "pass_rule_met": pass_rule_met,
        "full_method_allowed": False,
        "raw_feature_identity_ba": raw_ba,
        "total_conditioned_feature_identity_ba": total_ba,
        "predicted_total_conditioned_feature_identity_ba": pred_total_ba,
        "item_conditioned_feature_identity_ba": item_ba,
        "b3_itemwise_theta_conditioned_feature_identity_ba": b3_ba,
        "theta_conditioned_feature_identity_ba": theta_ba,
        "theta_only_identity_ba": theta_only_ba,
        "delta_theta_conditioned_minus_total_conditioned": safe_float(theta_ba - total_ba)
        if theta_ba is not None and total_ba is not None
        else None,
        "delta_theta_conditioned_minus_predicted_total_conditioned": safe_float(theta_ba - pred_total_ba)
        if theta_ba is not None and pred_total_ba is not None
        else None,
        "delta_theta_conditioned_minus_b3_conditioned": safe_float(theta_ba - b3_ba)
        if theta_ba is not None and b3_ba is not None
        else None,
        "theta_lower_than_controls_by_0_03": theta_lower_by_003,
        "theta_not_worse_than_controls": theta_not_worse,
        "b3_output_identity_ba": b3_output_identity,
        "psychometric_predicted_theta_output_identity_ba": psych_output_identity,
        "b3_output_observed_macro_mae": b3_macro,
        "psychometric_predicted_theta_observed_macro_mae": psych_macro,
        "b3_pareto_dominates_predicted_theta_output": b3_pareto,
        "subject_overlap_violations": overlap,
        "short_read": (
            "MV15 reports feature identity after theta conditioning together with total, "
            "predicted-total, item, B3 itemwise-theta, theta-only, predicted-output, "
            "covariate, and severity-only controls. It is diagnostic only."
        ),
    }


def build_gate_results(verdict: dict[str, Any], hygiene_passed: bool, conditioning_summary: pd.DataFrame, external_summary: pd.DataFrame) -> pd.DataFrame:
    required_ladders = {
        "L0_D_given_Z_raw",
        "L1_D_given_Z_and_total",
        "L2_D_given_Z_and_predicted_total",
        "L3_D_given_Z_and_items",
        "L4_D_given_Z_and_b3_itemwise_theta",
        "L5_D_given_Z_and_theta",
        "L7_D_given_theta_only",
    }
    completed_ladders = set(
        conditioning_summary.loc[
            (conditioning_summary["scope_id"] == PRIMARY_SCOPE)
            & (pd.to_numeric(conditioning_summary["completed_seed_rows"], errors="coerce") > 0),
            "ladder_id",
        ].astype(str)
    )
    external_completed = bool(
        not external_summary.empty and pd.to_numeric(external_summary["completed_seed_rows"], errors="coerce").sum() > 0
    )
    rows = [
        {
            "gate_id": "G1_input_scope",
            "status": "pass",
            "evidence": "Runner reads manifest-governed BGE/label/covariate inputs and aggregate references only; no raw text or media.",
            "full_method_effect": "No full method authorization.",
        },
        {
            "gate_id": "G2_subject_level_splits",
            "status": "pass" if verdict["subject_overlap_violations"] == 0 else "blocked",
            "evidence": f"Subject overlap violations: {verdict['subject_overlap_violations']}.",
            "full_method_effect": "Any overlap blocks MV15 claims.",
        },
        {
            "gate_id": "G3_theta_local_only",
            "status": "pass",
            "evidence": "No participant-grain theta scores, residualized feature matrices, fitted parameters, or row predictions are tracked.",
            "full_method_effect": "Local-only boundary preserved.",
        },
        {
            "gate_id": "G4_reference_reporting",
            "status": "pass" if required_ladders <= completed_ladders else "blocked",
            "evidence": f"Completed primary ladders: {';'.join(sorted(completed_ladders))}.",
            "full_method_effect": "Single favorable BA cannot be cited alone.",
        },
        {
            "gate_id": "G5_primary_identity_threshold",
            "status": "pass" if verdict["pass_rule_met"] is True else "partial" if verdict["pass_rule_met"] is None else "blocked",
            "evidence": (
                f"Theta-conditioned BA={fmt(verdict['theta_conditioned_feature_identity_ba'])}; "
                f"total={fmt(verdict['total_conditioned_feature_identity_ba'])}; "
                f"predicted_total={fmt(verdict['predicted_total_conditioned_feature_identity_ba'])}; "
                f"B3={fmt(verdict['b3_itemwise_theta_conditioned_feature_identity_ba'])}."
            ),
            "full_method_effect": "Even a pass only motivates MV16 or bounded diagnostic wording.",
        },
        {
            "gate_id": "G6_output_identity_boundary",
            "status": "pass",
            "evidence": (
                f"B3 output identity={fmt(verdict['b3_output_identity_ba'])}; "
                f"psychometric predicted theta output identity={fmt(verdict['psychometric_predicted_theta_output_identity_ba'])}; "
                f"B3 Pareto dominates predicted theta={verdict['b3_pareto_dominates_predicted_theta_output']}."
            ),
            "full_method_effect": "Output identity remains separate from feature identity.",
        },
        {
            "gate_id": "G7_external_sensitivity_boundary",
            "status": "pass" if external_completed else "blocked",
            "evidence": "CMDC/PDCH and three-way severity-only sensitivity rows completed." if external_completed else "No external sensitivity rows completed.",
            "full_method_effect": "No PHQ-HAMD latent claim from MV15.",
        },
        {
            "gate_id": "G8_artifact_hygiene",
            "status": "pass" if hygiene_passed else "blocked",
            "evidence": f"Artifact hygiene passed={hygiene_passed}.",
            "full_method_effect": "Hygiene failure blocks publishing.",
        },
    ]
    return pd.DataFrame(rows)


def artifact_boundary_summary() -> pd.DataFrame:
    rows = [
        ("theta_scores", "participant-grain latent scores", "aggregate distribution and identity metrics", False),
        ("measurement_parameters", "fitted item parameters and posterior diagnostics", "aggregate MV14 anchor/DIF evidence", False),
        ("residualized_features", "participant-grain transformed representation", "aggregate identity metrics by ladder", False),
        ("row_predictions", "per-participant model outputs", "aggregate BA and MAE summaries", False),
        ("split_maps", "participant-grain fold assignments", "aggregate split-overlap audit", False),
    ]
    return pd.DataFrame(
        [
            {
                "artifact_class": item,
                "reason_local_only": reason,
                "tracked_surrogate": surrogate,
                "written_to_tracked_outputs": written,
            }
            for item, reason, surrogate, written in rows
        ]
    )


def artifact_hygiene(out_dir: Path) -> dict[str, Any]:
    observed = {path.name for path in out_dir.iterdir() if path.is_file()}
    expected_after_audit = set(TRACKED_FILES)
    unexpected = sorted(observed - expected_after_audit)
    forbidden = sorted(
        name
        for name in observed
        if name.startswith("local_")
        or "predictions" in name
        or "row" in name
        or "residualized_features" in name
        or "nuisance" in name
        or "embeddings" in name
        or name.endswith((".joblib", ".pkl", ".rds", ".RData"))
        or (name.endswith(".csv") and "theta" in name)
    )
    return {
        "audit_id": "P5_MV15_latent_conditioned_identity_hygiene",
        "generated_at": utc_now(),
        "tracked_output_count": int(len(observed)),
        "unexpected_files": unexpected,
        "forbidden_local_only_file_names": forbidden,
        "artifact_hygiene_passed": not unexpected and not forbidden,
        "raw_text_or_media_read": False,
        "row_level_predictions_written_to_tracked_outputs": False,
        "theta_scores_written_to_tracked_outputs": False,
        "residualized_features_written_to_tracked_outputs": False,
        "fitted_parameters_written_to_tracked_outputs": False,
    }


def write_report(
    out_dir: Path,
    run_summary: dict[str, Any],
    conditioning_summary: pd.DataFrame,
    output_identity_summary: pd.DataFrame,
    output_metric_summary: pd.DataFrame,
    external_summary: pd.DataFrame,
) -> None:
    verdict = run_summary["verdict"]
    lines = [
        "# P5_MV15 Latent-Conditioned Dataset Identity",
        "",
        "MV15 audits whether E-DAIC/CMDC dataset identity remains recoverable from aligned BGE features after conditioning on PHQ theta and dimension-matched severity controls. It is aggregate-only diagnostic evidence.",
        "",
        "## Verdict",
        "",
        f"- Status: `{verdict['status']}`.",
        f"- Full method allowed: `{verdict['full_method_allowed']}`.",
        f"- Raw feature identity BA: `{fmt(verdict['raw_feature_identity_ba'])}`.",
        f"- Total-conditioned feature identity BA: `{fmt(verdict['total_conditioned_feature_identity_ba'])}`.",
        f"- Predicted-total-conditioned feature identity BA: `{fmt(verdict['predicted_total_conditioned_feature_identity_ba'])}`.",
        f"- B3 itemwise-theta-conditioned feature identity BA: `{fmt(verdict['b3_itemwise_theta_conditioned_feature_identity_ba'])}`.",
        f"- Theta-conditioned feature identity BA: `{fmt(verdict['theta_conditioned_feature_identity_ba'])}`.",
        f"- Theta-only identity BA: `{fmt(verdict['theta_only_identity_ba'])}`.",
        "",
        "## Primary Feature Identity",
        "",
        "| ladder | representation | conditioning | mean BA | std | completed rows |",
        "| --- | --- | --- | ---: | ---: | ---: |",
    ]
    primary = conditioning_summary[conditioning_summary["scope_id"] == PRIMARY_SCOPE].copy()
    for _, row in primary.sort_values(["ladder_id", "conditioning"]).iterrows():
        lines.append(
            f"| {row['ladder_id']} | {row['representation']} | {row['conditioning']} | "
            f"{fmt(row['mean'])} | {fmt(row['std'])} | {int(row['completed_seed_rows'])} |"
        )
    lines.extend(
        [
            "",
            "## Output Identity",
            "",
            "| output | conditioning | representation | mean BA | std |",
            "| --- | --- | --- | ---: | ---: |",
        ]
    )
    for _, row in output_identity_summary.sort_values(["output_model", "conditioning"]).iterrows():
        lines.append(
            f"| {row.get('output_model', '')} | {row['conditioning']} | {row['representation']} | "
            f"{fmt(row['mean'])} | {fmt(row['std'])} |"
        )
    lines.extend(
        [
            "",
            "## Output Fidelity",
            "",
            "| output | metric | mean | std |",
            "| --- | --- | ---: | ---: |",
        ]
    )
    for _, row in output_metric_summary.sort_values(["output_model", "metric"]).iterrows():
        lines.append(f"| {row['output_model']} | {row['metric']} | {fmt(row['mean'])} | {fmt(row['std'])} |")
    lines.extend(
        [
            "",
            "## External Sensitivity",
            "",
            "| scope | ladder | representation | conditioning | mean BA | std |",
            "| --- | --- | --- | --- | ---: | ---: |",
        ]
    )
    for _, row in external_summary.sort_values(["scope_id", "ladder_id", "representation"]).iterrows():
        lines.append(
            f"| {row['scope_id']} | {row['ladder_id']} | {row['representation']} | "
            f"{row['conditioning']} | {fmt(row['mean'])} | {fmt(row['std'])} |"
        )
    lines.extend(
        [
            "",
            "## Boundaries",
            "",
            "- Theta scores, fitted item parameters, residualized feature matrices, row predictions, nuisance directions, split maps, and model artifacts are not written to tracked outputs.",
            "- MV15 cannot authorize PHQ-HAMD latent claims; CMDC/PDCH and three-way rows are severity-only sensitivity diagnostics.",
        ]
    )
    (out_dir / "report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def run_experiment(
    out_dir: Path,
    manifest_dir: Path,
    split_path: Path,
    phase2_root: Path,
) -> dict[str, Any]:
    if out_dir.exists():
        shutil.rmtree(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    table, feature_cols, feature_audit = mv09.prepare_tables(manifest_dir, phase2_root)
    phq_table = table[table["dataset"].isin(["edaic", "cmdc"])].copy()
    cmdc_folds = mv07.load_subject_folds(split_path, "cmdc", "cmdc_phq9_subject_cv", "phq9_total")

    conditioning_rows: list[dict[str, Any]] = []
    output_identity_rows: list[dict[str, Any]] = []
    output_metrics: list[dict[str, Any]] = []
    split_rows: list[dict[str, Any]] = []
    target_rows: list[dict[str, Any]] = []
    distribution_rows: list[dict[str, Any]] = []

    for seed in SEEDS:
        specs = [spec for spec in mv12.protocol_specs(phq_table, cmdc_folds, seed) if spec["protocol"] == "pooled_shared_phq"]
        if len(specs) != 1:
            raise RuntimeError(f"expected one pooled_shared_phq spec for seed {seed}")
        spec = specs[0]
        train = spec["train"].copy()
        eval_frame = spec["eval"].copy()
        fold = str(spec["fold"])
        train.attrs["fold_name"] = fold
        eval_frame.attrs["fold_name"] = fold
        split_rows.append(split_row(PRIMARY_SCOPE, seed, fold, train, eval_frame, ("edaic", "cmdc")))
        train_ctx, eval_ctx, target_summary, arrays = add_fold_controls(train, eval_frame, feature_cols, seed)
        target_rows.append(target_summary)
        distribution_rows.extend(target_distribution_rows(eval_ctx, seed, fold))
        conditioning_rows.extend(run_primary_ladder(train_ctx, eval_ctx, feature_cols, seed, fold))
        output_identity_rows.extend(run_output_ladder(train_ctx, eval_ctx, seed, fold))
        output_metrics.extend(output_metric_rows(eval_ctx, arrays, seed, fold))

    external_rows: list[dict[str, Any]] = []
    external_split_rows: list[dict[str, Any]] = []
    for scope_id, datasets in SENSITIVITY_SCOPES.items():
        rows, splits = run_external_sensitivity_for_scope(table, feature_cols, scope_id, datasets)
        external_rows.extend(rows)
        external_split_rows.extend(splits)

    split_rows.extend(external_split_rows)

    input_audit = build_input_audit(table, feature_audit, feature_cols)
    covariates = covariate_coverage(table)
    conditioning_by_seed = pd.DataFrame(conditioning_rows)
    output_identity_by_seed = pd.DataFrame(output_identity_rows)
    external_by_seed = pd.DataFrame(external_rows)
    output_metric_by_seed = pd.DataFrame(output_metrics)
    split_audit = pd.DataFrame(split_rows)
    target_generation = pd.concat([pd.DataFrame(target_rows), pd.DataFrame(distribution_rows)], ignore_index=True)

    conditioning_summary = summarize_identity(conditioning_by_seed)
    output_identity_summary = add_output_model_to_summary(summarize_identity(output_identity_by_seed), output_identity_by_seed)
    external_summary = summarize_identity(external_by_seed)
    output_metric_summary = summarize_metrics(output_metric_by_seed)

    input_audit.to_csv(out_dir / "input_audit.csv", index=False)
    covariates.to_csv(out_dir / "covariate_coverage_summary.csv", index=False)
    conditioning_by_seed.to_csv(out_dir / "conditioning_identity_by_seed.csv", index=False)
    conditioning_summary.to_csv(out_dir / "conditioning_identity_summary.csv", index=False)
    output_identity_by_seed.to_csv(out_dir / "output_identity_by_seed.csv", index=False)
    output_identity_summary.to_csv(out_dir / "output_identity_summary.csv", index=False)
    output_metric_by_seed.to_csv(out_dir / "output_metric_by_seed.csv", index=False)
    output_metric_summary.to_csv(out_dir / "output_metric_summary.csv", index=False)
    external_by_seed.to_csv(out_dir / "external_sensitivity_by_seed.csv", index=False)
    external_summary.to_csv(out_dir / "external_sensitivity_summary.csv", index=False)
    split_audit.to_csv(out_dir / "split_audit_summary.csv", index=False)
    target_generation.to_csv(out_dir / "target_generation_summary.csv", index=False)
    artifact_boundary_summary().to_csv(out_dir / "artifact_boundary_summary.csv", index=False)

    verdict = build_verdict(conditioning_summary, output_identity_summary, output_metric_summary, split_audit)
    run_summary = {
        "run_id": RUN_ID,
        "generated_at": utc_now(),
        "status": "complete",
        "scope": "latent_conditioned_dataset_identity_audit",
        "input_contract": {
            "primary_datasets": ["edaic", "cmdc"],
            "sensitivity_datasets": ["pdch"],
            "feature_family": "text_bge",
            "model_input_columns": int(len(feature_cols)),
            "measurement_items": MEASUREMENT_ITEMS,
            "raw_text_or_media_read": False,
            "row_level_predictions_read": False,
            "private_review_material_read": False,
            "official_test_labels_used": False,
        },
        "model_contract": {
            "seeds": SEEDS,
            "primary_split_protocol": "edaic_train_dev_plus_cmdc_subject_cv",
            "sensitivity_split_protocol": "seeded_subject_level_stratified_cv",
            "ridge_alpha_grid": mv07.RIDGE_ALPHA_GRID,
            "identity_classifier": "standardized_balanced_logistic_regression",
            "measurement_scorer": "MV12 local partial PHQ measurement scorer",
        },
        "outputs": {
            "tracked_outputs": sorted(TRACKED_FILES),
            "conditioning_identity_rows": int(len(conditioning_summary)),
            "conditioning_identity_seed_rows": int(len(conditioning_by_seed)),
            "output_identity_rows": int(len(output_identity_summary)),
            "output_metric_rows": int(len(output_metric_summary)),
            "external_sensitivity_rows": int(len(external_summary)),
            "target_generation_rows": int(len(target_generation)),
        },
        "verdict": verdict,
        "artifact_hygiene_passed": False,
    }
    pass_fail = build_gate_results(verdict, False, conditioning_summary, external_summary)
    pass_fail.to_csv(out_dir / "pass_fail_gate_results.csv", index=False)
    (out_dir / "run_summary.json").write_text(json.dumps(run_summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    write_report(out_dir, run_summary, conditioning_summary, output_identity_summary, output_metric_summary, external_summary)

    hygiene = artifact_hygiene(out_dir)
    run_summary["artifact_hygiene_passed"] = bool(hygiene["artifact_hygiene_passed"])
    pass_fail = build_gate_results(verdict, run_summary["artifact_hygiene_passed"], conditioning_summary, external_summary)
    pass_fail.to_csv(out_dir / "pass_fail_gate_results.csv", index=False)
    (out_dir / "artifact_hygiene_audit.json").write_text(json.dumps(hygiene, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (out_dir / "run_summary.json").write_text(json.dumps(run_summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    write_report(out_dir, run_summary, conditioning_summary, output_identity_summary, output_metric_summary, external_summary)
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
    print(
        json.dumps(
            {
                "out_dir": rel(args.out_dir),
                "pass_rule_status": run_summary["verdict"]["pass_rule_status"],
                "artifact_hygiene_passed": run_summary["artifact_hygiene_passed"],
            },
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
