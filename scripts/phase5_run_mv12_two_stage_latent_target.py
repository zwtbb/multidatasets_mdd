#!/usr/bin/env python3
"""Run P5_MV12 two-stage PHQ latent-target validation.

MV12 separates label measurement from multimodal prediction. For each
subject-level fold, it fits a local-only ordinal label model Y_to_theta,
trains shallow BGE X_to_theta predictors, compares them with direct X_to_Y and
floor baselines, and exports only aggregate metrics, identity probes, transfer
checks, leakage audits, and hygiene summaries.

No raw text/media, public subject-level theta scores, fitted measurement
parameters, transformed features, projection directions, or model artifacts are
written.
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
from numpy.polynomial.hermite import hermgauss
from scipy.optimize import minimize
from scipy.special import expit, logsumexp
from scipy.stats import norm
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LinearRegression, LogisticRegression, Ridge
from sklearn.metrics import balanced_accuracy_score
from sklearn.model_selection import StratifiedKFold
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler


SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import phase5_run_mv07_aligned_bge_shared_symptom as mv07
import phase5_run_mv07b_bge_identity_projection as mv07b


ROOT = mv07.ROOT
PHASE5_DIR = ROOT / "analysis" / "phase5_minimal_validation"
DEFAULT_OUT_DIR = PHASE5_DIR / "p5_mv12_two_stage_latent_target"
DEFAULT_MANIFEST_DIR = mv07.DEFAULT_MANIFEST_DIR
DEFAULT_SPLIT_PATH = mv07.DEFAULT_SPLIT_PATH
DEFAULT_PHASE2_ROOT = mv07.DEFAULT_PHASE2_ROOT
MV11_ANCHORS = PHASE5_DIR / "p5_mv11_formal_psychometric_confirmation" / "anchor_confirmation_summary.csv"

RUN_ID = "P5_MV12_two_stage_latent_target"
SEEDS = mv07.SEEDS
CONSTRUCTS = mv07.CONSTRUCTS
ANCHOR_ITEMS = ["C01", "C04", "C05", "C07"]
DIF_AWARE_ITEMS = ["C02", "C06"]
SENSITIVITY_ITEMS = ["C03", "C08"]
MEASUREMENT_ITEMS = ["C01", "C02", "C04", "C05", "C06", "C07"]
RIDGE_ALPHA_GRID = mv07.RIDGE_ALPHA_GRID
PROJECTION_COMPONENT_COUNT = 10
QUADRATURE_POINTS = 31
MAXITER = 800
MV09_EDAIC_CMDC_CONDITIONAL_BA = 0.9911030655391121
PREFERRED_CONDITIONAL_IDENTITY_BA = 0.70

B0_MODEL = "B0_train_mean_theta"
B1_MODEL = "B1_train_mean_observed_total"
B2_MODEL = "B2_direct_total_allocation_ridge"
B3_MODEL = "B3_direct_itemwise_ridge"
M12A_MODEL = "M12a_BGE_Ridge_X_to_theta"
M12B_MODEL = "M12b_projected_BGE_X_to_theta"

TRACKED_FILES = {
    "artifact_hygiene_audit.json",
    "comparison_summary.csv",
    "construct_target_map.csv",
    "identity_probe_by_seed.csv",
    "identity_probe_summary.csv",
    "label_feature_audit.csv",
    "leakage_audit.csv",
    "local_artifact_manifest.csv",
    "metric_summary.csv",
    "metrics_by_seed.csv",
    "model_split_audit.csv",
    "report.md",
    "run_summary.json",
    "target_generation_summary.csv",
    "target_reliability_summary.csv",
    "transfer_summary.csv",
}


@dataclass(frozen=True)
class GrmSpec:
    groups: list[str]
    items: list[str]
    loading_keys: dict[tuple[str, str], str]
    threshold_keys: dict[tuple[str, str], str]
    default_group: str
    description: str


@dataclass
class MeasurementFit:
    spec: GrmSpec
    loading_values: dict[str, float]
    threshold_values: dict[str, np.ndarray]
    optimizer_success: bool
    optimizer_status: int
    optimizer_iterations: int
    optimizer_message: str
    log_likelihood: float
    parameter_count: int
    boundary_parameter_count: int
    n_subjects: int
    n_responses: int


@dataclass
class ThetaToObservedMapper:
    dataset_models: dict[str, Ridge]
    fallback_model: Ridge

    def predict(self, theta: np.ndarray, datasets: Iterable[str]) -> np.ndarray:
        theta_arr = np.asarray(theta, dtype=float).reshape(-1, 1)
        dataset_list = [str(item) for item in datasets]
        out = np.zeros((theta_arr.shape[0], len(CONSTRUCTS)), dtype=float)
        for dataset in sorted(set(dataset_list)):
            idx = [i for i, value in enumerate(dataset_list) if value == dataset]
            model = self.dataset_models.get(dataset, self.fallback_model)
            out[idx, :] = model.predict(theta_arr[idx])
        return clip_items(out)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def safe_float(value: Any) -> float | None:
    return mv07.safe_float(value)


def fmt(value: Any, digits: int = 3) -> str:
    numeric = safe_float(value)
    if numeric is None:
        return "NA"
    return f"{numeric:.{digits}f}"


def softplus(value: np.ndarray | float) -> np.ndarray | float:
    return np.logaddexp(0.0, value)


def inv_softplus(value: float) -> float:
    value = max(float(value), 1e-4)
    if value > 30:
        return value
    return float(np.log(np.expm1(value)))


def ordered_threshold_raw(thresholds: list[float]) -> list[float]:
    ordered = sorted(float(value) for value in thresholds)
    d12 = max(ordered[1] - ordered[0], 0.05)
    d23 = max(ordered[2] - ordered[1], 0.05)
    return [ordered[0], inv_softplus(d12), inv_softplus(d23)]


def make_quadrature(points: int = QUADRATURE_POINTS) -> tuple[np.ndarray, np.ndarray]:
    nodes, weights = hermgauss(points)
    theta = np.sqrt(2.0) * nodes
    log_weights = np.log(weights) - 0.5 * np.log(np.pi)
    return theta.astype(float), log_weights.astype(float)


def category_probabilities(theta: np.ndarray, loading: float, thresholds: np.ndarray) -> np.ndarray:
    cumulative = expit(loading * (theta[:, None] - thresholds[None, :]))
    probs = np.empty((theta.shape[0], 4), dtype=float)
    probs[:, 0] = 1.0 - cumulative[:, 0]
    probs[:, 1] = cumulative[:, 0] - cumulative[:, 1]
    probs[:, 2] = cumulative[:, 1] - cumulative[:, 2]
    probs[:, 3] = cumulative[:, 2]
    return np.clip(probs, 1e-12, 1.0)


def make_grm_spec(groups: list[str], items: list[str]) -> GrmSpec:
    groups = sorted(set(groups), key=mv07.natural_key)
    loading_keys: dict[tuple[str, str], str] = {}
    threshold_keys: dict[tuple[str, str], str] = {}
    multi_group = len(groups) > 1
    for group in groups:
        for item in items:
            if multi_group:
                loading_key = f"loading:shared:{item}"
                threshold_key = f"threshold:shared:{item}" if item in ANCHOR_ITEMS else f"threshold:{group}:{item}"
            else:
                loading_key = f"loading:{group}:{item}"
                threshold_key = f"threshold:{group}:{item}"
            loading_keys[(group, item)] = loading_key
            threshold_keys[(group, item)] = threshold_key
    return GrmSpec(
        groups=groups,
        items=list(items),
        loading_keys=loading_keys,
        threshold_keys=threshold_keys,
        default_group=groups[0],
        description=(
            "partial multi-group PHQ target with shared anchor thresholds and DIF-aware C02/C06 thresholds"
            if multi_group
            else "single-group PHQ target for strict source-only scoring"
        ),
    )


def unique_keys(mapping: dict[tuple[str, str], str]) -> list[str]:
    return sorted(set(mapping.values()))


def threshold_initial_values(spec: GrmSpec, table: pd.DataFrame) -> dict[str, list[float]]:
    values: dict[str, list[float]] = {}
    for key in unique_keys(spec.threshold_keys):
        pooled: list[int] = []
        for group in spec.groups:
            group_table = table[table["dataset"] == group]
            for item in spec.items:
                if spec.threshold_keys[(group, item)] == key:
                    pooled.extend(group_table[item].astype(int).tolist())
        arr = np.asarray(pooled, dtype=float)
        thresholds: list[float] = []
        for cutoff in [1, 2, 3]:
            p_ge = float(np.mean(arr >= cutoff))
            p_ge = min(max(p_ge, 0.02), 0.98)
            thresholds.append(float(norm.ppf(1.0 - p_ge)))
        values[key] = thresholds
    return values


def initial_vector_and_bounds(spec: GrmSpec, table: pd.DataFrame) -> tuple[np.ndarray, list[tuple[float, float]], list[str], list[str]]:
    loading_keys = unique_keys(spec.loading_keys)
    threshold_keys = unique_keys(spec.threshold_keys)
    threshold_inits = threshold_initial_values(spec, table)
    vector: list[float] = []
    bounds: list[tuple[float, float]] = []
    for _ in loading_keys:
        vector.append(0.0)
        bounds.append((-2.0, 2.3))
    for key in threshold_keys:
        vector.extend(ordered_threshold_raw(threshold_inits[key]))
        bounds.extend([(-6.0, 6.0), (-6.0, 4.0), (-6.0, 4.0)])
    return np.asarray(vector, dtype=float), bounds, loading_keys, threshold_keys


def decode_params(
    params: np.ndarray,
    loading_keys: list[str],
    threshold_keys: list[str],
) -> tuple[dict[str, float], dict[str, np.ndarray]]:
    loading_values: dict[str, float] = {}
    threshold_values: dict[str, np.ndarray] = {}
    idx = 0
    for key in loading_keys:
        loading_values[key] = float(np.exp(params[idx]))
        idx += 1
    for key in threshold_keys:
        b1 = float(params[idx])
        d12 = float(softplus(params[idx + 1]))
        d23 = float(softplus(params[idx + 2]))
        threshold_values[key] = np.asarray([b1, b1 + d12, b1 + d12 + d23], dtype=float)
        idx += 3
    return loading_values, threshold_values


def boundary_count(values: np.ndarray, bounds: list[tuple[float, float]], tol: float = 1e-4) -> int:
    count = 0
    for value, (lower, upper) in zip(values, bounds, strict=True):
        if abs(value - lower) <= tol or abs(value - upper) <= tol:
            count += 1
    return count


def fit_measurement_model(table: pd.DataFrame, items: list[str]) -> MeasurementFit:
    groups = sorted(table["dataset"].astype(str).unique(), key=mv07.natural_key)
    spec = make_grm_spec(groups, items)
    theta, log_weights = make_quadrature()
    responses = {
        group: table.loc[table["dataset"] == group, items].to_numpy(dtype=int)
        for group in groups
    }
    x0, bounds, loading_keys, threshold_keys = initial_vector_and_bounds(spec, table)

    def nll(params: np.ndarray) -> float:
        loading_values, threshold_values = decode_params(params, loading_keys, threshold_keys)
        total_loglik = 0.0
        for group in groups:
            y = responses[group]
            if y.size == 0:
                continue
            subject_node_logp = np.zeros((y.shape[0], theta.shape[0]), dtype=float)
            for item_index, item in enumerate(items):
                loading = loading_values[spec.loading_keys[(group, item)]]
                thresholds = threshold_values[spec.threshold_keys[(group, item)]]
                probs = category_probabilities(theta, loading, thresholds)
                subject_node_logp += np.log(probs[:, y[:, item_index]].T)
            total_loglik += float(np.sum(logsumexp(subject_node_logp + log_weights[None, :], axis=1)))
        if not math.isfinite(total_loglik):
            return 1e100
        return -total_loglik

    result = minimize(
        nll,
        x0,
        method="L-BFGS-B",
        bounds=bounds,
        options={"maxiter": MAXITER, "ftol": 1e-8, "gtol": 1e-5, "maxls": 30},
    )
    loading_values, threshold_values = decode_params(np.asarray(result.x, dtype=float), loading_keys, threshold_keys)
    return MeasurementFit(
        spec=spec,
        loading_values=loading_values,
        threshold_values=threshold_values,
        optimizer_success=bool(result.success),
        optimizer_status=int(result.status),
        optimizer_iterations=int(getattr(result, "nit", -1)),
        optimizer_message=str(result.message),
        log_likelihood=float(-result.fun),
        parameter_count=int(len(x0)),
        boundary_parameter_count=boundary_count(np.asarray(result.x, dtype=float), bounds),
        n_subjects=int(len(table)),
        n_responses=int(len(table) * len(items)),
    )


def score_theta(frame: pd.DataFrame, fit: MeasurementFit) -> tuple[np.ndarray, int]:
    theta, log_weights = make_quadrature()
    outputs: list[float] = []
    fallback_count = 0
    for _, row in frame.iterrows():
        group = str(row["dataset"])
        if group not in fit.spec.groups:
            group = fit.spec.default_group
            fallback_count += 1
        logp = log_weights.copy()
        for item in fit.spec.items:
            value = int(row[item])
            loading = fit.loading_values[fit.spec.loading_keys[(group, item)]]
            thresholds = fit.threshold_values[fit.spec.threshold_keys[(group, item)]]
            probs = category_probabilities(theta, loading, thresholds)
            logp += np.log(probs[:, value])
        weights = np.exp(logp - logsumexp(logp))
        outputs.append(float(np.sum(theta * weights)))
    return np.asarray(outputs, dtype=float), fallback_count


def clip_items(values: np.ndarray) -> np.ndarray:
    return np.clip(np.asarray(values, dtype=float), 0.0, 3.0)


def spearman(values_true: Iterable[Any], values_pred: Iterable[Any]) -> float | None:
    return mv07.spearman(values_true, values_pred)


def cronbach_alpha(frame: pd.DataFrame, items: list[str]) -> float | None:
    if frame.empty or len(items) < 2:
        return None
    values = frame[items].to_numpy(dtype=float)
    if values.shape[0] < 3:
        return None
    item_var = np.var(values, axis=0, ddof=1)
    total_var = float(np.var(np.sum(values, axis=1), ddof=1))
    if total_var <= 0:
        return None
    k = len(items)
    return safe_float((k / (k - 1.0)) * (1.0 - float(np.sum(item_var)) / total_var))


def ridge_pipeline(alpha: float) -> Pipeline:
    return mv07.ridge_pipeline(alpha)


def fit_theta_to_observed_mapper(train: pd.DataFrame, theta_train: np.ndarray) -> ThetaToObservedMapper:
    theta = np.asarray(theta_train, dtype=float).reshape(-1, 1)
    y = train[CONSTRUCTS].to_numpy(dtype=float)
    fallback = Ridge(alpha=1.0)
    fallback.fit(theta, y)
    models: dict[str, Ridge] = {}
    for dataset, group in train.assign(theta_target=theta_train).groupby("dataset", sort=True):
        if len(group) < 8:
            continue
        model = Ridge(alpha=1.0)
        model.fit(group[["theta_target"]].to_numpy(dtype=float), group[CONSTRUCTS].to_numpy(dtype=float))
        models[str(dataset)] = model
    return ThetaToObservedMapper(dataset_models=models, fallback_model=fallback)


def fit_item_to_theta_mapper(train: pd.DataFrame, theta_train: np.ndarray) -> Pipeline:
    model = Pipeline(
        [
            ("imputer", SimpleImputer(strategy="median")),
            ("scaler", StandardScaler()),
            ("ridge", Ridge(alpha=1.0)),
        ]
    )
    model.fit(train[CONSTRUCTS].to_numpy(dtype=float), np.asarray(theta_train, dtype=float))
    return model


def fit_predict_total_alloc_items(
    train: pd.DataFrame,
    eval_frame: pd.DataFrame,
    feature_cols: list[str],
    seed: int,
) -> tuple[np.ndarray, float]:
    x_train = train[feature_cols].to_numpy(dtype=float)
    y_total = train[CONSTRUCTS].sum(axis=1).to_numpy(dtype=float)
    x_eval = eval_frame[feature_cols].to_numpy(dtype=float)
    alpha = mv07.choose_alpha(x_train, y_total.reshape(-1, 1), seed)
    model = ridge_pipeline(alpha)
    model.fit(x_train, y_total)
    total_pred = np.asarray(model.predict(x_eval), dtype=float).reshape(-1)
    means = train[CONSTRUCTS].mean(axis=0).to_numpy(dtype=float)
    denom = float(np.sum(means))
    proportions = np.repeat(1.0 / len(CONSTRUCTS), len(CONSTRUCTS)) if denom <= 0 else means / denom
    return clip_items(total_pred.reshape(-1, 1) * proportions.reshape(1, -1)), float(alpha)


def fit_predict_itemwise_items(
    train: pd.DataFrame,
    eval_frame: pd.DataFrame,
    feature_cols: list[str],
    seed: int,
) -> tuple[np.ndarray, float]:
    x_train = train[feature_cols].to_numpy(dtype=float)
    y_train = train[CONSTRUCTS].to_numpy(dtype=float)
    x_eval = eval_frame[feature_cols].to_numpy(dtype=float)
    alpha = mv07.choose_alpha(x_train, y_train, seed)
    model = ridge_pipeline(alpha)
    model.fit(x_train, y_train)
    return clip_items(model.predict(x_eval)), float(alpha)


def fit_predict_theta(
    train: pd.DataFrame,
    eval_frame: pd.DataFrame,
    theta_train: np.ndarray,
    feature_cols: list[str],
    seed: int,
) -> tuple[np.ndarray, float]:
    x_train = train[feature_cols].to_numpy(dtype=float)
    x_eval = eval_frame[feature_cols].to_numpy(dtype=float)
    alpha = mv07.choose_alpha(x_train, np.asarray(theta_train, dtype=float).reshape(-1, 1), seed)
    model = ridge_pipeline(alpha)
    model.fit(x_train, theta_train)
    pred = np.asarray(model.predict(x_eval), dtype=float).reshape(-1)
    return pred, float(alpha)


def make_prediction_frame(
    eval_frame: pd.DataFrame,
    theta_true: np.ndarray,
    theta_pred: np.ndarray,
    item_pred: np.ndarray,
    *,
    protocol: str,
    seed: int,
    fold: str,
    model: str,
) -> pd.DataFrame:
    out = eval_frame[["dataset", "subject_id", "subject_key", *CONSTRUCTS]].copy()
    out.insert(0, "run_id", RUN_ID)
    out.insert(1, "seed", int(seed))
    out.insert(2, "fold", fold)
    out.insert(3, "protocol", protocol)
    out.insert(4, "model", model)
    out["theta_true"] = np.asarray(theta_true, dtype=float)
    out["theta_pred"] = np.asarray(theta_pred, dtype=float)
    out["true_total"] = out[CONSTRUCTS].sum(axis=1).astype(float)
    for idx, item in enumerate(CONSTRUCTS):
        out[f"pred_{item}"] = item_pred[:, idx]
    out["pred_total"] = out[[f"pred_{item}" for item in CONSTRUCTS]].sum(axis=1).astype(float)
    return out


def protocol_specs(phq_table: pd.DataFrame, cmdc_folds: dict[int, dict[str, set[str]]], seed: int) -> list[dict[str, Any]]:
    edaic_train = phq_table[(phq_table["dataset"] == "edaic") & (phq_table["official_split"] == "train")].copy()
    edaic_dev = phq_table[(phq_table["dataset"] == "edaic") & (phq_table["official_split"] == "dev")].copy()
    fold = cmdc_folds[seed % len(cmdc_folds)]
    fold_name = next(iter(fold["fold_name"]))
    cmdc_train = phq_table[(phq_table["dataset"] == "cmdc") & phq_table["subject_id"].isin(fold["train"])].copy()
    cmdc_val = phq_table[(phq_table["dataset"] == "cmdc") & phq_table["subject_id"].isin(fold["validation"])].copy()
    return [
        {
            "protocol": "edaic_same_dataset_phq",
            "fold": fold_name,
            "train": edaic_train,
            "eval": edaic_dev,
            "measurement_train": edaic_train,
            "transfer_direction": "same_dataset",
            "target_domain_labels_used_for_measurement_fit": False,
        },
        {
            "protocol": "cmdc_subject_cv_phq",
            "fold": fold_name,
            "train": cmdc_train,
            "eval": cmdc_val,
            "measurement_train": cmdc_train,
            "transfer_direction": "same_dataset",
            "target_domain_labels_used_for_measurement_fit": False,
        },
        {
            "protocol": "cross_edaic_to_cmdc_phq",
            "fold": fold_name,
            "train": edaic_train,
            "eval": cmdc_val,
            "measurement_train": edaic_train,
            "transfer_direction": "edaic_to_cmdc",
            "target_domain_labels_used_for_measurement_fit": False,
        },
        {
            "protocol": "cross_cmdc_to_edaic_phq",
            "fold": fold_name,
            "train": cmdc_train,
            "eval": edaic_dev,
            "measurement_train": cmdc_train,
            "transfer_direction": "cmdc_to_edaic",
            "target_domain_labels_used_for_measurement_fit": False,
        },
        {
            "protocol": "pooled_shared_phq",
            "fold": fold_name,
            "train": pd.concat([edaic_train, cmdc_train], ignore_index=True),
            "eval": pd.concat([edaic_dev, cmdc_val], ignore_index=True),
            "measurement_train": pd.concat([edaic_train, cmdc_train], ignore_index=True),
            "transfer_direction": "pooled_same_fold",
            "target_domain_labels_used_for_measurement_fit": True,
        },
    ]


def ensure_no_overlap(train: pd.DataFrame, eval_frame: pd.DataFrame, protocol: str, seed: int) -> int:
    overlap = set(train["subject_key"].astype(str)) & set(eval_frame["subject_key"].astype(str))
    if overlap:
        raise ValueError(f"{protocol}/{seed} train/eval overlap: {sorted(overlap)[:5]}")
    return 0


def direct_items_to_theta(item_mapper: Pipeline, item_pred: np.ndarray) -> np.ndarray:
    return np.asarray(item_mapper.predict(clip_items(item_pred)), dtype=float).reshape(-1)


def model_rows_for_spec(
    spec: dict[str, Any],
    feature_cols: list[str],
    seed: int,
) -> tuple[list[pd.DataFrame], list[dict[str, Any]], dict[str, Any], list[dict[str, Any]], list[dict[str, Any]]]:
    protocol = str(spec["protocol"])
    fold = str(spec["fold"])
    train = spec["train"].copy()
    eval_frame = spec["eval"].copy()
    measurement_train = spec["measurement_train"].copy()
    ensure_no_overlap(train, eval_frame, protocol, seed)

    fit = fit_measurement_model(measurement_train, MEASUREMENT_ITEMS)
    theta_train, train_fallback_count = score_theta(train, fit)
    theta_eval, eval_fallback_count = score_theta(eval_frame, fit)
    theta_mapper = fit_theta_to_observed_mapper(train, theta_train)
    item_mapper = fit_item_to_theta_mapper(train, theta_train)
    prediction_frames: list[pd.DataFrame] = []
    model_audits: list[dict[str, Any]] = []
    leakage_rows: list[dict[str, Any]] = []

    def add_model(
        model: str,
        theta_pred: np.ndarray,
        item_pred: np.ndarray,
        *,
        selected_alpha: float | None,
        feature_transform: str,
        control_uses_eval_dataset_labels: bool = False,
        skipped_reason: str | None = None,
    ) -> None:
        prediction_frames.append(
            make_prediction_frame(
                eval_frame,
                theta_eval,
                theta_pred,
                item_pred,
                protocol=protocol,
                seed=seed,
                fold=fold,
                model=model,
            )
        )
        model_audits.append(
            {
                "seed": seed,
                "fold": fold,
                "protocol": protocol,
                "model": model,
                "train_participants": int(train["subject_key"].nunique()),
                "eval_participants": int(eval_frame["subject_key"].nunique()),
                "train_datasets": ";".join(sorted(train["dataset"].astype(str).unique())),
                "eval_datasets": ";".join(sorted(eval_frame["dataset"].astype(str).unique())),
                "measurement_train_datasets": ";".join(sorted(measurement_train["dataset"].astype(str).unique())),
                "train_eval_overlap_count": 0,
                "feature_transform": feature_transform,
                "selected_alpha": selected_alpha,
                "skipped_reason": skipped_reason,
            }
        )
        leakage_rows.append(
            {
                "seed": seed,
                "fold": fold,
                "protocol": protocol,
                "model": model,
                "measurement_fit_uses_eval_labels": False,
                "predictor_uses_eval_target_labels": False,
                "target_domain_labels_used_for_measurement_fit": bool(
                    spec["target_domain_labels_used_for_measurement_fit"]
                ),
                "control_uses_eval_dataset_labels": bool(control_uses_eval_dataset_labels),
                "official_test_labels_used": False,
                "row_predictions_tracked": False,
                "theta_targets_tracked": False,
                "fitted_parameters_written": False,
                "model_artifacts_written": False,
                "transformed_features_written": False,
            }
        )

    theta_mean = np.repeat(float(np.mean(theta_train)), len(eval_frame))
    add_model(
        B0_MODEL,
        theta_mean,
        theta_mapper.predict(theta_mean, eval_frame["dataset"]),
        selected_alpha=None,
        feature_transform="none",
    )

    item_mean = np.tile(train[CONSTRUCTS].mean(axis=0).to_numpy(dtype=float).reshape(1, -1), (len(eval_frame), 1))
    add_model(
        B1_MODEL,
        direct_items_to_theta(item_mapper, item_mean),
        clip_items(item_mean),
        selected_alpha=None,
        feature_transform="none",
    )

    total_items, total_alpha = fit_predict_total_alloc_items(train, eval_frame, feature_cols, seed)
    add_model(
        B2_MODEL,
        direct_items_to_theta(item_mapper, total_items),
        total_items,
        selected_alpha=total_alpha,
        feature_transform="raw_bge",
    )

    itemwise_items, itemwise_alpha = fit_predict_itemwise_items(train, eval_frame, feature_cols, seed)
    add_model(
        B3_MODEL,
        direct_items_to_theta(item_mapper, itemwise_items),
        itemwise_items,
        selected_alpha=itemwise_alpha,
        feature_transform="raw_bge",
    )

    theta_pred, theta_alpha = fit_predict_theta(train, eval_frame, theta_train, feature_cols, seed)
    add_model(
        M12A_MODEL,
        theta_pred,
        theta_mapper.predict(theta_pred, eval_frame["dataset"]),
        selected_alpha=theta_alpha,
        feature_transform="raw_bge",
    )

    if protocol == "pooled_shared_phq" and len(set(train["dataset"].astype(str))) == 2:
        transform, projected_train_values = mv07b.build_projection_transform(
            train,
            feature_cols,
            PROJECTION_COMPONENT_COUNT,
            seed,
        )
        projected_train = train.copy()
        projected_train.loc[:, feature_cols] = projected_train_values
        projected_eval = mv07b.apply_projection_transform(eval_frame, transform)
        projected_theta_pred, projected_alpha = fit_predict_theta(
            projected_train,
            projected_eval,
            theta_train,
            feature_cols,
            seed,
        )
        add_model(
            M12B_MODEL,
            projected_theta_pred,
            theta_mapper.predict(projected_theta_pred, eval_frame["dataset"]),
            selected_alpha=projected_alpha,
            feature_transform=f"bge_logit_projection_k{PROJECTION_COMPONENT_COUNT}",
        )
        model_audits[-1]["requested_projection_components"] = PROJECTION_COMPONENT_COUNT
        model_audits[-1]["fitted_projection_components"] = transform.fitted_component_count
        model_audits[-1]["projection_uses_eval_labels"] = False
        model_audits[-1]["projection_uses_eval_dataset_labels"] = False
        model_audits[-1]["projection_parameters_written"] = False

    target_row = {
        "seed": seed,
        "fold": fold,
        "protocol": protocol,
        "transfer_direction": spec["transfer_direction"],
        "measurement_description": fit.spec.description,
        "measurement_items": ";".join(fit.spec.items),
        "anchor_items": ";".join(ANCHOR_ITEMS),
        "dif_aware_items": ";".join(DIF_AWARE_ITEMS),
        "sensitivity_items_excluded_primary": ";".join(SENSITIVITY_ITEMS),
        "measurement_train_participants": fit.n_subjects,
        "measurement_train_datasets": ";".join(fit.spec.groups),
        "measurement_parameter_count": fit.parameter_count,
        "measurement_optimizer_success": fit.optimizer_success,
        "measurement_optimizer_status": fit.optimizer_status,
        "measurement_optimizer_iterations": fit.optimizer_iterations,
        "measurement_boundary_parameter_count": fit.boundary_parameter_count,
        "theta_train_mean": safe_float(np.mean(theta_train)),
        "theta_train_std": safe_float(np.std(theta_train, ddof=1)),
        "theta_eval_mean": safe_float(np.mean(theta_eval)),
        "theta_eval_std": safe_float(np.std(theta_eval, ddof=1)),
        "theta_train_total_spearman": spearman(theta_train, train[CONSTRUCTS].sum(axis=1)),
        "theta_eval_total_spearman": spearman(theta_eval, eval_frame[CONSTRUCTS].sum(axis=1)),
        "train_measurement_group_fallback_count": train_fallback_count,
        "eval_measurement_group_fallback_count": eval_fallback_count,
        "theta_scores_written_to_tracked_outputs": False,
        "fitted_parameters_written": False,
    }
    reliability_rows = []
    for item_group, items in [
        ("primary_measurement_items", MEASUREMENT_ITEMS),
        ("anchors_only", ANCHOR_ITEMS),
        ("sensitivity_only", SENSITIVITY_ITEMS),
        ("all_observed_items", CONSTRUCTS),
    ]:
        reliability_rows.append(
            {
                "seed": seed,
                "fold": fold,
                "protocol": protocol,
                "item_group": item_group,
                "item_count": len(items),
                "train_cronbach_alpha": cronbach_alpha(train, items),
                "eval_cronbach_alpha": cronbach_alpha(eval_frame, items),
                "train_theta_item_total_spearman": spearman(theta_train, train[items].sum(axis=1)),
                "eval_theta_item_total_spearman": spearman(theta_eval, eval_frame[items].sum(axis=1)),
            }
        )
    return prediction_frames, model_audits, target_row, reliability_rows, leakage_rows


def metric_rows_for_predictions(predictions: pd.DataFrame) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for (seed, protocol, model), group in predictions.groupby(["seed", "protocol", "model"], sort=False):
        for dataset_slice in ["pooled", *sorted(group["dataset"].astype(str).unique())]:
            data = group if dataset_slice == "pooled" else group[group["dataset"].astype(str) == dataset_slice]
            if data.empty:
                continue
            item_maes: list[float] = []
            for item in CONSTRUCTS:
                item_maes.append(float(np.mean(np.abs(data[f"pred_{item}"].to_numpy(float) - data[item].to_numpy(float)))))
            metrics = {
                "Theta MAE": safe_float(np.mean(np.abs(data["theta_pred"] - data["theta_true"]))),
                "Theta RMSE": safe_float(np.sqrt(np.mean((data["theta_pred"] - data["theta_true"]) ** 2))),
                "Theta Spearman": spearman(data["theta_true"], data["theta_pred"]),
                "Observed Macro Item MAE": safe_float(np.mean(item_maes)),
                "Observed Anchor Item MAE": safe_float(
                    np.mean(
                        [
                            np.mean(np.abs(data[f"pred_{item}"].to_numpy(float) - data[item].to_numpy(float)))
                            for item in ANCHOR_ITEMS
                        ]
                    )
                ),
                "Observed DIF-Aware Item MAE": safe_float(
                    np.mean(
                        [
                            np.mean(np.abs(data[f"pred_{item}"].to_numpy(float) - data[item].to_numpy(float)))
                            for item in DIF_AWARE_ITEMS
                        ]
                    )
                ),
                "Observed Sensitivity Item MAE": safe_float(
                    np.mean(
                        [
                            np.mean(np.abs(data[f"pred_{item}"].to_numpy(float) - data[item].to_numpy(float)))
                            for item in SENSITIVITY_ITEMS
                        ]
                    )
                ),
                "Observed Total MAE": safe_float(np.mean(np.abs(data["pred_total"] - data["true_total"]))),
                "Observed Total RMSE": safe_float(np.sqrt(np.mean((data["pred_total"] - data["true_total"]) ** 2))),
                "Observed Total Spearman": spearman(data["true_total"], data["pred_total"]),
            }
            for metric, value in metrics.items():
                rows.append(
                    {
                        "seed": int(seed),
                        "protocol": protocol,
                        "model": model,
                        "dataset_slice": dataset_slice,
                        "metric": metric,
                        "value": value,
                        "participant_count": int(data["subject_key"].nunique()),
                    }
                )
    return rows


def summarize_metrics(metrics_by_seed: pd.DataFrame) -> pd.DataFrame:
    summary = (
        metrics_by_seed.groupby(["protocol", "model", "dataset_slice", "metric"], dropna=False)
        .agg(
            mean=("value", "mean"),
            std=("value", "std"),
            seed_count=("seed", "nunique"),
            participant_count_mean=("participant_count", "mean"),
        )
        .reset_index()
    )
    summary["std"] = summary["std"].fillna(0.0)
    summary["ci95_low"] = summary["mean"] - 1.96 * summary["std"] / np.sqrt(summary["seed_count"].clip(lower=1))
    summary["ci95_high"] = summary["mean"] + 1.96 * summary["std"] / np.sqrt(summary["seed_count"].clip(lower=1))
    return summary


def build_comparison_summary(metric_summary: pd.DataFrame) -> pd.DataFrame:
    pivot = (
        metric_summary.pivot_table(
            index=["protocol", "model", "dataset_slice"],
            columns="metric",
            values="mean",
            aggfunc="first",
        )
        .reset_index()
        .rename_axis(None, axis=1)
    )
    rows: list[dict[str, Any]] = []
    for (protocol, dataset_slice), group in pivot.groupby(["protocol", "dataset_slice"], sort=False):
        values = group.set_index("model").to_dict("index")
        b0 = values.get(B0_MODEL, {})
        b1 = values.get(B1_MODEL, {})
        b2 = values.get(B2_MODEL, {})
        b3 = values.get(B3_MODEL, {})
        for model, row in values.items():
            rows.append(
                {
                    "protocol": protocol,
                    "dataset_slice": dataset_slice,
                    "model": model,
                    "theta_mae": row.get("Theta MAE"),
                    "theta_spearman": row.get("Theta Spearman"),
                    "observed_macro_item_mae": row.get("Observed Macro Item MAE"),
                    "observed_anchor_item_mae": row.get("Observed Anchor Item MAE"),
                    "observed_total_mae": row.get("Observed Total MAE"),
                    "delta_theta_mae_vs_B0": safe_float(row.get("Theta MAE") - b0.get("Theta MAE"))
                    if row.get("Theta MAE") is not None and b0.get("Theta MAE") is not None
                    else None,
                    "delta_theta_mae_vs_B3": safe_float(row.get("Theta MAE") - b3.get("Theta MAE"))
                    if row.get("Theta MAE") is not None and b3.get("Theta MAE") is not None
                    else None,
                    "delta_observed_macro_mae_vs_B3": safe_float(
                        row.get("Observed Macro Item MAE") - b3.get("Observed Macro Item MAE")
                    )
                    if row.get("Observed Macro Item MAE") is not None
                    and b3.get("Observed Macro Item MAE") is not None
                    else None,
                    "delta_observed_total_mae_vs_B1": safe_float(row.get("Observed Total MAE") - b1.get("Observed Total MAE"))
                    if row.get("Observed Total MAE") is not None and b1.get("Observed Total MAE") is not None
                    else None,
                    "delta_observed_total_mae_vs_B2": safe_float(row.get("Observed Total MAE") - b2.get("Observed Total MAE"))
                    if row.get("Observed Total MAE") is not None and b2.get("Observed Total MAE") is not None
                    else None,
                }
            )
    return pd.DataFrame(rows)


def residualize(values: np.ndarray, controls: np.ndarray) -> np.ndarray:
    values_arr = np.asarray(values, dtype=float)
    controls_arr = np.asarray(controls, dtype=float)
    if values_arr.ndim == 1:
        values_arr = values_arr.reshape(-1, 1)
    if controls_arr.ndim == 1:
        controls_arr = controls_arr.reshape(-1, 1)
    if values_arr.shape[0] < controls_arr.shape[1] + 3:
        return values_arr
    model = LinearRegression()
    model.fit(controls_arr, values_arr)
    return values_arr - model.predict(controls_arr)


def identity_cv_score(x: np.ndarray, labels: np.ndarray, seed: int) -> tuple[float | None, str | None]:
    y = np.asarray(labels, dtype=int)
    if len(set(y)) < 2:
        return None, "missing_dataset_class"
    min_count = int(np.min(np.bincount(y)))
    if min_count < 3:
        return None, "too_few_per_dataset"
    n_splits = min(5, min_count)
    splitter = StratifiedKFold(n_splits=n_splits, shuffle=True, random_state=seed)
    scores: list[float] = []
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
    return safe_float(np.mean(scores)), None


def run_identity_probes(predictions: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    models = [B3_MODEL, M12A_MODEL, M12B_MODEL]
    pooled = predictions[predictions["protocol"] == "pooled_shared_phq"].copy()
    for (seed, model_name), group in pooled[pooled["model"].isin(models)].groupby(["seed", "model"], sort=True):
        labels = (group["dataset"].astype(str) == "cmdc").astype(int).to_numpy()
        true_items = group[CONSTRUCTS].to_numpy(dtype=float)
        pred_items = group[[f"pred_{item}" for item in CONSTRUCTS]].to_numpy(dtype=float)
        theta_true = group["theta_true"].to_numpy(dtype=float)
        theta_pred = group["theta_pred"].to_numpy(dtype=float)
        total_true = group["true_total"].to_numpy(dtype=float)

        probes = [
            (
                "ID0_unconditional_predicted_theta_identity",
                "predicted_theta",
                "none",
                theta_pred.reshape(-1, 1),
            ),
            (
                "ID1_conditional_predicted_theta_identity",
                "predicted_theta_residual",
                "theta_true_and_observed_total",
                residualize(theta_pred, np.column_stack([theta_true, total_true])),
            ),
            (
                "ID2_conditional_post_mapping_identity",
                "predicted_observed_item_residual",
                "theta_true_observed_total_and_true_items",
                residualize(pred_items, np.column_stack([theta_true, total_true, true_items])),
            ),
        ]
        for probe_id, representation, conditioning, x in probes:
            value, skipped = identity_cv_score(np.asarray(x, dtype=float), labels, int(seed))
            rows.append(
                {
                    "seed": int(seed),
                    "probe_id": probe_id,
                    "model": model_name,
                    "representation": representation,
                    "conditioning": conditioning,
                    "metric": "Balanced Accuracy",
                    "value": value,
                    "participant_count": int(group["subject_key"].nunique()),
                    "dataset_count": 2,
                    "skipped_reason": skipped,
                }
            )
    return pd.DataFrame(rows)


def summarize_identity(identity_by_seed: pd.DataFrame) -> pd.DataFrame:
    if identity_by_seed.empty:
        return pd.DataFrame()
    return (
        identity_by_seed.groupby(["probe_id", "model", "representation", "conditioning", "metric"], dropna=False)
        .agg(
            mean=("value", "mean"),
            std=("value", "std"),
            seed_count=("seed", "nunique"),
            participant_count_mean=("participant_count", "mean"),
            dataset_count_mean=("dataset_count", "mean"),
        )
        .reset_index()
        .fillna({"std": 0.0})
    )


def build_transfer_summary(comparison: pd.DataFrame) -> pd.DataFrame:
    transfer = comparison[
        comparison["protocol"].isin(["cross_edaic_to_cmdc_phq", "cross_cmdc_to_edaic_phq"])
        & (comparison["dataset_slice"] != "pooled")
    ].copy()
    rows: list[dict[str, Any]] = []
    for protocol, group in transfer.groupby("protocol", sort=False):
        m12a = group[group["model"] == M12A_MODEL]
        if m12a.empty:
            continue
        row = m12a.iloc[0].to_dict()
        rows.append(
            {
                "protocol": protocol,
                "target_dataset": row["dataset_slice"],
                "m12a_theta_mae": row["theta_mae"],
                "m12a_delta_theta_mae_vs_B0": row["delta_theta_mae_vs_B0"],
                "m12a_delta_theta_mae_vs_B3": row["delta_theta_mae_vs_B3"],
                "m12a_observed_macro_mae": row["observed_macro_item_mae"],
                "m12a_delta_observed_macro_mae_vs_B3": row["delta_observed_macro_mae_vs_B3"],
                "transfer_theta_beats_B0": bool(safe_float(row["delta_theta_mae_vs_B0"]) is not None and row["delta_theta_mae_vs_B0"] < 0),
                "transfer_observed_non_degraded_vs_B3": bool(
                    safe_float(row["delta_observed_macro_mae_vs_B3"]) is not None
                    and row["delta_observed_macro_mae_vs_B3"] <= 0
                ),
            }
        )
    return pd.DataFrame(rows)


def build_label_feature_audit(labels: dict[str, pd.DataFrame], features: dict[str, pd.DataFrame], joined: dict[str, pd.DataFrame], feature_audit: pd.DataFrame) -> pd.DataFrame:
    feature_lookup = feature_audit.set_index("dataset").to_dict("index")
    rows: list[dict[str, Any]] = []
    for dataset in ["edaic", "cmdc"]:
        path_like = feature_lookup[dataset].get("path_like_columns")
        path_like_present = pd.notna(path_like) and bool(str(path_like).strip())
        rows.append(
            {
                "dataset": dataset,
                "scale": "PHQ-8" if dataset == "edaic" else "PHQ-9",
                "label_participants": int(labels[dataset]["subject_key"].nunique()),
                "feature_participants": int(features[dataset]["subject_id"].nunique()),
                "joined_participants": int(joined[dataset]["subject_key"].nunique()),
                "model_input_columns": int(feature_lookup[dataset]["model_input_columns"]),
                "feature_family": "text_bge",
                "path_like_columns_present": bool(path_like_present),
            }
        )
    return pd.DataFrame(rows)


def build_construct_target_map(anchor_path: Path) -> pd.DataFrame:
    anchors = pd.read_csv(anchor_path)
    role_lookup = anchors.set_index("construct_id").to_dict("index")
    rows: list[dict[str, Any]] = []
    for item in CONSTRUCTS:
        role = "primary_anchor" if item in ANCHOR_ITEMS else "dif_aware_primary" if item in DIF_AWARE_ITEMS else "sensitivity_only"
        mv11 = role_lookup.get(item, {})
        rows.append(
            {
                "construct_id": item,
                "item_label_short": mv11.get("item_label_short"),
                "mv12_target_role": role,
                "used_in_primary_theta": bool(item in MEASUREMENT_ITEMS),
                "edaic_item": mv07.EDAIC_ITEM_MAP[item],
                "cmdc_item": mv07.CMDC_ITEM_MAP[item],
                "mv11_formal_role": mv11.get("formal_role"),
                "mv11_loading_dif_flag": mv11.get("loading_dif_flag"),
                "mv11_threshold_dif_flag": mv11.get("threshold_dif_flag"),
            }
        )
    return pd.DataFrame(rows)


def determine_verdict(
    comparison: pd.DataFrame,
    transfer: pd.DataFrame,
    identity_summary: pd.DataFrame,
    leakage: pd.DataFrame,
    target_generation: pd.DataFrame,
) -> dict[str, Any]:
    def row(protocol: str, dataset: str, model: str) -> dict[str, Any]:
        selected = comparison[
            (comparison["protocol"] == protocol)
            & (comparison["dataset_slice"] == dataset)
            & (comparison["model"] == model)
        ]
        return selected.iloc[0].to_dict() if not selected.empty else {}

    edaic = row("edaic_same_dataset_phq", "edaic", M12A_MODEL)
    cmdc = row("cmdc_subject_cv_phq", "cmdc", M12A_MODEL)
    pooled = row("pooled_shared_phq", "pooled", M12A_MODEL)
    same_theta_pass = all(
        safe_float(item.get("delta_theta_mae_vs_B0")) is not None and item["delta_theta_mae_vs_B0"] < 0
        for item in [edaic, cmdc]
    )
    same_observed_pass = all(
        safe_float(item.get("delta_observed_macro_mae_vs_B3")) is not None
        and item["delta_observed_macro_mae_vs_B3"] <= 0
        for item in [edaic, cmdc]
    )
    transfer_theta_pass = bool(transfer["transfer_theta_beats_B0"].any()) if not transfer.empty else False
    transfer_observed_pass = bool(transfer["transfer_observed_non_degraded_vs_B3"].any()) if not transfer.empty else False
    m12a_identity = None
    identity_row = identity_summary[
        (identity_summary["probe_id"] == "ID1_conditional_predicted_theta_identity")
        & (identity_summary["model"] == M12A_MODEL)
    ]
    if not identity_row.empty:
        m12a_identity = safe_float(identity_row.iloc[0]["mean"])
    identity_improved = m12a_identity is not None and m12a_identity < MV09_EDAIC_CMDC_CONDITIONAL_BA
    identity_strong = m12a_identity is not None and m12a_identity <= PREFERRED_CONDITIONAL_IDENTITY_BA
    leakage_pass = bool(
        leakage[[
            "measurement_fit_uses_eval_labels",
            "predictor_uses_eval_target_labels",
            "control_uses_eval_dataset_labels",
            "official_test_labels_used",
            "row_predictions_tracked",
            "theta_targets_tracked",
            "fitted_parameters_written",
            "model_artifacts_written",
            "transformed_features_written",
        ]]
        .fillna(False)
        .astype(bool)
        .sum()
        .sum()
        == 0
    )
    optimizer_all_success = bool(target_generation["measurement_optimizer_success"].all())

    if not optimizer_all_success:
        status = "blocked_measurement_optimizer_warning"
    elif not leakage_pass:
        status = "blocked_leakage_or_artifact_boundary"
    elif not same_theta_pass:
        status = "blocked_no_same_dataset_theta_gain"
    elif not same_observed_pass:
        status = "blocked_theta_gain_not_observed_scale_safe"
    elif not transfer_theta_pass:
        status = "blocked_no_external_theta_transfer_gain"
    elif not transfer_observed_pass:
        status = "blocked_external_transfer_not_observed_scale_safe"
    elif not identity_improved:
        status = "blocked_conditional_identity_not_improved"
    elif not identity_strong:
        status = "partial_theta_utility_identity_still_high"
    else:
        status = "pass_two_stage_latent_target_candidate"

    return {
        "pass_rule_status": status,
        "pass_rule_met": status.startswith("pass_"),
        "full_method_allowed": False,
        "same_dataset_theta_gate_passed": same_theta_pass,
        "same_dataset_observed_gate_passed": same_observed_pass,
        "external_transfer_theta_gate_passed": transfer_theta_pass,
        "external_transfer_observed_gate_passed": transfer_observed_pass,
        "conditional_identity_improved_vs_mv09": identity_improved,
        "conditional_identity_preferred_threshold_passed": identity_strong,
        "conditional_identity_ba_m12a": m12a_identity,
        "mv09_conditional_identity_ba_reference": MV09_EDAIC_CMDC_CONDITIONAL_BA,
        "preferred_conditional_identity_ba_threshold": PREFERRED_CONDITIONAL_IDENTITY_BA,
        "leakage_gate_passed": leakage_pass,
        "measurement_optimizer_all_success": optimizer_all_success,
        "m12a_edaic_delta_theta_mae_vs_B0": safe_float(edaic.get("delta_theta_mae_vs_B0")),
        "m12a_cmdc_delta_theta_mae_vs_B0": safe_float(cmdc.get("delta_theta_mae_vs_B0")),
        "m12a_edaic_delta_observed_macro_mae_vs_B3": safe_float(edaic.get("delta_observed_macro_mae_vs_B3")),
        "m12a_cmdc_delta_observed_macro_mae_vs_B3": safe_float(cmdc.get("delta_observed_macro_mae_vs_B3")),
        "m12a_pooled_theta_mae": safe_float(pooled.get("theta_mae")),
        "short_read": (
            "MV12 runs the predeclared two-stage PHQ latent-target test. A pass requires theta utility, observed-scale safety, external transfer, conditional shared-latent identity, leakage control, and artifact hygiene; design or same-dataset gains alone are not enough."
        ),
    }


def artifact_hygiene(out_dir: Path) -> dict[str, Any]:
    forbidden_patterns = [
        r"/root/",
        r"/autodl-tmp/",
        r"\bsubject_id\b",
        r"\bsubject_key\b",
        r"audio_path",
        r"video_path",
        r"text_path",
        r"gait_path",
        r"source_locator",
        r"local_annotation_workbook",
        r"\.wav\b",
        r"\.mp4\b",
        r"\.avi\b",
        r"raw prompt",
        r"raw response",
        r"raw clinical",
        r"posterior_score",
        r"factor_score",
        r"parameter_value",
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
        "audit_id": "P5_MV12_two_stage_latent_target_hygiene",
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
    transfer: pd.DataFrame,
) -> None:
    verdict = run_summary["verdict"]
    lines = [
        "# P5_MV12 Two-Stage Latent-Target Validation",
        "",
        f"Generated: `{run_summary['generated_at']}`",
        "",
        "## Scope",
        "",
        "MV12 fits label-only PHQ theta targets locally, trains shallow BGE X-to-theta predictors, compares direct/floor baselines, and exports aggregate diagnostics only.",
        "",
        "## Verdict",
        "",
        f"- Pass-rule status: `{verdict['pass_rule_status']}`.",
        f"- Same-dataset theta gate passed: `{verdict['same_dataset_theta_gate_passed']}`.",
        f"- Same-dataset observed-scale gate passed: `{verdict['same_dataset_observed_gate_passed']}`.",
        f"- External theta transfer gate passed: `{verdict['external_transfer_theta_gate_passed']}`.",
        f"- External observed-scale transfer gate passed: `{verdict['external_transfer_observed_gate_passed']}`.",
        f"- Conditional identity BA for M12a: `{fmt(verdict['conditional_identity_ba_m12a'])}`.",
        f"- Conditional identity improved versus MV09: `{verdict['conditional_identity_improved_vs_mv09']}`.",
        f"- Preferred conditional identity threshold passed: `{verdict['conditional_identity_preferred_threshold_passed']}`.",
        f"- Leakage gate passed: `{verdict['leakage_gate_passed']}`.",
        f"- Artifact hygiene passed: `{run_summary['artifact_hygiene_passed']}`.",
        "",
        verdict["short_read"],
        "",
        "## Key Comparisons",
        "",
        "| protocol | dataset | model | theta MAE | delta theta vs B0 | observed macro MAE | delta observed vs B3 | observed total MAE |",
        "| --- | --- | --- | ---: | ---: | ---: | ---: | ---: |",
    ]
    key_protocols = [
        "edaic_same_dataset_phq",
        "cmdc_subject_cv_phq",
        "cross_edaic_to_cmdc_phq",
        "cross_cmdc_to_edaic_phq",
        "pooled_shared_phq",
    ]
    key_models = [B0_MODEL, B1_MODEL, B2_MODEL, B3_MODEL, M12A_MODEL, M12B_MODEL]
    key = comparison[
        comparison["protocol"].isin(key_protocols)
        & comparison["model"].isin(key_models)
        & (comparison["dataset_slice"] != "pooled")
    ].copy()
    for _, row in key.sort_values(["protocol", "dataset_slice", "model"]).iterrows():
        lines.append(
            f"| {row['protocol']} | {row['dataset_slice']} | {row['model']} | {fmt(row['theta_mae'])} | {fmt(row['delta_theta_mae_vs_B0'])} | {fmt(row['observed_macro_item_mae'])} | {fmt(row['delta_observed_macro_mae_vs_B3'])} | {fmt(row['observed_total_mae'])} |"
        )

    lines.extend(
        [
            "",
            "## Transfer Summary",
            "",
            "| protocol | target dataset | theta delta vs B0 | theta delta vs B3 | observed delta vs B3 |",
            "| --- | --- | ---: | ---: | ---: |",
        ]
    )
    for _, row in transfer.iterrows():
        lines.append(
            f"| {row['protocol']} | {row['target_dataset']} | {fmt(row['m12a_delta_theta_mae_vs_B0'])} | {fmt(row['m12a_delta_theta_mae_vs_B3'])} | {fmt(row['m12a_delta_observed_macro_mae_vs_B3'])} |"
        )

    lines.extend(
        [
            "",
            "## Identity Probes",
            "",
            "| probe | model | conditioning | BA mean | std |",
            "| --- | --- | --- | ---: | ---: |",
        ]
    )
    for _, row in identity.sort_values(["probe_id", "model"]).iterrows():
        lines.append(
            f"| {row['probe_id']} | {row['model']} | {row['conditioning']} | {fmt(row['mean'])} | {fmt(row['std'])} |"
        )

    lines.extend(
        [
            "",
            "## Interpretation Boundary",
            "",
            "- MV12 is still a minimal-validation row, not full M0/M1/M2/M3 construction.",
            "- If it fails any primary gate, use it as diagnostic evidence for measurement shift rather than a positive shared-latent method claim.",
            "- The ignored local row prediction file can support later aggregate error analysis, but it is not part of the public release.",
        ]
    )
    (out_dir / "report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def local_artifact_manifest() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "artifact_class": "row_prediction_table",
                "written": True,
                "tracked": False,
                "public_surrogate": "aggregate metrics and identity summaries",
            },
            {
                "artifact_class": "fitted_measurement_parameters",
                "written": False,
                "tracked": False,
                "public_surrogate": "aggregate optimizer and target-generation summaries",
            },
            {
                "artifact_class": "theta_target_table",
                "written": False,
                "tracked": False,
                "public_surrogate": "aggregate theta distribution and reliability summaries",
            },
            {
                "artifact_class": "model_or_projection_artifact",
                "written": False,
                "tracked": False,
                "public_surrogate": "aggregate model split and leakage audits",
            },
        ]
    )


def run_experiment(
    out_dir: Path,
    manifest_dir: Path,
    split_path: Path,
    phase2_root: Path,
) -> dict[str, Any]:
    if out_dir.exists():
        shutil.rmtree(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    features, feature_cols, feature_audit = mv07.load_bge_features(phase2_root)
    labels = {
        "edaic": mv07.load_phq_labels(manifest_dir, "edaic"),
        "cmdc": mv07.load_phq_labels(manifest_dir, "cmdc"),
    }
    joined = {dataset: mv07.join_labels_features(labels[dataset], features[dataset]) for dataset in ["edaic", "cmdc"]}
    phq_table = pd.concat([joined["edaic"], joined["cmdc"]], ignore_index=True)
    cmdc_folds = mv07.load_subject_folds(split_path, "cmdc", "cmdc_phq9_subject_cv", "phq9_total")

    prediction_frames: list[pd.DataFrame] = []
    split_rows: list[dict[str, Any]] = []
    target_rows: list[dict[str, Any]] = []
    reliability_rows: list[dict[str, Any]] = []
    leakage_rows: list[dict[str, Any]] = []
    for seed in SEEDS:
        for spec in protocol_specs(phq_table, cmdc_folds, seed):
            frames, audits, target_row, reliability, leakage = model_rows_for_spec(spec, feature_cols, seed)
            prediction_frames.extend(frames)
            split_rows.extend(audits)
            target_rows.append(target_row)
            reliability_rows.extend(reliability)
            leakage_rows.extend(leakage)

    predictions = pd.concat(prediction_frames, ignore_index=True)
    predictions.to_csv(out_dir / "p5_mv12_local_predictions.csv", index=False)
    model_split_audit = pd.DataFrame(split_rows)
    target_generation = pd.DataFrame(target_rows)
    target_reliability = pd.DataFrame(reliability_rows)
    leakage = pd.DataFrame(leakage_rows)
    metrics_by_seed = pd.DataFrame(metric_rows_for_predictions(predictions))
    metric_summary = summarize_metrics(metrics_by_seed)
    comparison = build_comparison_summary(metric_summary)
    identity_by_seed = run_identity_probes(predictions)
    identity_summary = summarize_identity(identity_by_seed)
    transfer = build_transfer_summary(comparison)
    label_feature_audit = build_label_feature_audit(labels, features, joined, feature_audit)
    construct_map = build_construct_target_map(MV11_ANCHORS)
    local_manifest = local_artifact_manifest()

    label_feature_audit.to_csv(out_dir / "label_feature_audit.csv", index=False)
    construct_map.to_csv(out_dir / "construct_target_map.csv", index=False)
    model_split_audit.to_csv(out_dir / "model_split_audit.csv", index=False)
    target_generation.to_csv(out_dir / "target_generation_summary.csv", index=False)
    target_reliability.to_csv(out_dir / "target_reliability_summary.csv", index=False)
    leakage.to_csv(out_dir / "leakage_audit.csv", index=False)
    metrics_by_seed.to_csv(out_dir / "metrics_by_seed.csv", index=False)
    metric_summary.to_csv(out_dir / "metric_summary.csv", index=False)
    comparison.to_csv(out_dir / "comparison_summary.csv", index=False)
    identity_by_seed.to_csv(out_dir / "identity_probe_by_seed.csv", index=False)
    identity_summary.to_csv(out_dir / "identity_probe_summary.csv", index=False)
    transfer.to_csv(out_dir / "transfer_summary.csv", index=False)
    local_manifest.to_csv(out_dir / "local_artifact_manifest.csv", index=False)

    verdict = determine_verdict(comparison, transfer, identity_summary, leakage, target_generation)
    run_summary = {
        "run_id": RUN_ID,
        "generated_at": utc_now(),
        "status": "complete",
        "scope": "two_stage_phq_latent_target_minimal_validation",
        "input_contract": {
            "datasets": ["edaic", "cmdc"],
            "scales": ["PHQ-8", "PHQ-9"],
            "measurement_items": MEASUREMENT_ITEMS,
            "anchor_items": ANCHOR_ITEMS,
            "dif_aware_items": DIF_AWARE_ITEMS,
            "sensitivity_items": SENSITIVITY_ITEMS,
            "raw_text_or_media_read": False,
            "row_level_predictions_read": False,
            "private_review_material_read": False,
            "official_test_labels_used": False,
        },
        "feature_contract": {
            "feature_family": "text_bge",
            "model_input_columns": int(len(feature_cols)),
            "encoder_frozen": True,
            "feature_cache_read_local_only": True,
            "features_written": False,
        },
        "model_contract": {
            "models": [B0_MODEL, B1_MODEL, B2_MODEL, B3_MODEL, M12A_MODEL, M12B_MODEL],
            "seeds": SEEDS,
            "ridge_alpha_grid": RIDGE_ALPHA_GRID,
            "projection_component_count": PROJECTION_COMPONENT_COUNT,
            "subject_overlap_violations": int(model_split_audit["train_eval_overlap_count"].sum()),
        },
        "outputs": {
            "tracked_outputs": sorted(TRACKED_FILES),
            "local_only_outputs": ["ignored_row_prediction_table"],
            "metric_rows": int(len(metrics_by_seed)),
            "comparison_rows": int(len(comparison)),
            "identity_rows": int(len(identity_summary)),
            "transfer_rows": int(len(transfer)),
            "target_generation_rows": int(len(target_generation)),
        },
        "verdict": verdict,
        "artifact_hygiene_passed": False,
    }
    (out_dir / "run_summary.json").write_text(json.dumps(run_summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    write_report(out_dir, run_summary, comparison, identity_summary, transfer)
    hygiene = artifact_hygiene(out_dir)
    run_summary["artifact_hygiene_passed"] = bool(hygiene["artifact_hygiene_passed"])
    (out_dir / "run_summary.json").write_text(json.dumps(run_summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    write_report(out_dir, run_summary, comparison, identity_summary, transfer)
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
