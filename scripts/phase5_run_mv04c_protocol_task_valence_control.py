#!/usr/bin/env python3
"""Run P5_MV04c protocol/task/valence nuisance-projection controls.

This runner extends P5_MV04 beyond E-DAIC/CMDC dataset identity. It uses the
local Phase 3 eGeMAPS task/valence caches and tests whether nuisance directions
learned from training-fold protocol labels can reduce MODMA task identity and
EATD valence identity without using evaluation protocol labels at transform
time. It writes only aggregate summaries; row-level predictions remain
local-only and ignored.
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
from sklearn.linear_model import LogisticRegression, Ridge
from sklearn.metrics import balanced_accuracy_score
from sklearn.model_selection import StratifiedKFold
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import LabelEncoder, StandardScaler


SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from phase2_metrics import compute_metrics, safe_float


WORKTREE_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT_DIR = (
    WORKTREE_ROOT
    / "analysis"
    / "phase5_minimal_validation"
    / "p5_mv04c_protocol_task_valence_control"
)
DEFAULT_MODMA_FEATURES = (
    WORKTREE_ROOT
    / "analysis"
    / "phase3_diagnostics"
    / "task_valence"
    / "modma_egemaps_subject_task_features.csv"
)
DEFAULT_EATD_FEATURES = (
    WORKTREE_ROOT
    / "analysis"
    / "phase3_diagnostics"
    / "task_valence"
    / "eatd_egemaps_valence_features.csv"
)

SEEDS = [0, 1, 2, 3, 4]
PROJECTION_COMPONENTS = [1, 2, 3, 5, 8]
MODMA_TASKS = ["interview", "reading", "picture_description", "affective_task"]
EATD_VALENCES = ["positive", "neutral", "negative"]
TRAIN_PRIOR_MODEL = "train_prior"
TRAIN_MEAN_MODEL = "train_mean"
MODMA_RAW_MODEL = "raw_pooled_task_logistic"
EATD_RAW_MODEL = "raw_pooled_valence_ridge"
PROTOCOL_ID = "p5_mv04c_protocol_task_valence_nuisance_projection"
BOOTSTRAP_RESAMPLES = 200

ID_COLUMNS = {
    "subject_id",
    "task_type",
    "valence",
    "split",
    "binary_label",
    "sds_total",
    "audio_segment_count",
}


@dataclass(frozen=True)
class ProjectionTransform:
    label_column: str
    requested_component_count: int
    fitted_component_count: int
    feature_cols: list[str]
    label_counts: dict[str, int]
    direction_norms: list[float]
    imputer: SimpleImputer
    scaler: StandardScaler
    encoder: LabelEncoder
    directions: list[np.ndarray]


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def natural_key(value: Any) -> list[Any]:
    return [int(part) if part.isdigit() else part for part in re.split(r"(\d+)", str(value))]


def format_value(value: Any, digits: int = 3) -> str:
    numeric = safe_float(value)
    if numeric is None:
        return "NA"
    return f"{numeric:.{digits}f}"


def read_csv(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"missing CSV: {path}")
    return pd.read_csv(path, dtype={"subject_id": str})


def feature_columns(frame: pd.DataFrame) -> list[str]:
    return [column for column in frame.columns if column not in ID_COLUMNS]


def logistic_pipeline(seed: int) -> Pipeline:
    return Pipeline(
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


def ridge_pipeline() -> Pipeline:
    return Pipeline(
        [
            ("imputer", SimpleImputer(strategy="median")),
            ("scaler", StandardScaler()),
            ("ridge", Ridge(alpha=10.0, solver="lsqr")),
        ]
    )


def add_direction(candidate: np.ndarray, directions: list[np.ndarray]) -> tuple[np.ndarray | None, float | None]:
    vector = candidate.astype(float).reshape(-1)
    for direction in directions:
        vector = vector - float(vector @ direction) * direction
    norm = float(np.linalg.norm(vector))
    if not np.isfinite(norm) or norm < 1e-10:
        return None, None
    return vector / norm, norm


def residualize(values: np.ndarray, directions: list[np.ndarray]) -> np.ndarray:
    out = values.copy()
    for direction in directions:
        out = out - np.outer(out @ direction, direction)
    return out


def build_projection_transform(
    train: pd.DataFrame,
    feature_cols: list[str],
    label_column: str,
    component_count: int,
    seed: int,
) -> tuple[ProjectionTransform, np.ndarray]:
    x_train = train[feature_cols].to_numpy(dtype=float)
    imputer = SimpleImputer(strategy="median")
    scaler = StandardScaler()
    z_train = scaler.fit_transform(imputer.fit_transform(x_train))
    encoder = LabelEncoder()
    y_train = encoder.fit_transform(train[label_column].astype(str).to_numpy())
    directions: list[np.ndarray] = []
    norms: list[float] = []

    while len(directions) < component_count:
        if len(np.unique(y_train)) < 2:
            break
        classifier = LogisticRegression(
            C=1.0,
            class_weight="balanced",
            max_iter=2000,
            random_state=seed + len(directions),
        )
        classifier.fit(z_train, y_train)
        _, _, vt = np.linalg.svd(classifier.coef_.astype(float), full_matrices=False)
        added_this_round = False
        for candidate in vt:
            unit, norm = add_direction(candidate, directions)
            if unit is None or norm is None:
                continue
            directions.append(unit)
            norms.append(norm)
            z_train = residualize(z_train, [unit])
            added_this_round = True
            if len(directions) >= component_count:
                break
        if not added_this_round:
            break

    label_counts = {
        str(label): int(count)
        for label, count in train[label_column].astype(str).value_counts().sort_index().items()
    }
    transform = ProjectionTransform(
        label_column=label_column,
        requested_component_count=component_count,
        fitted_component_count=len(directions),
        feature_cols=list(feature_cols),
        label_counts=label_counts,
        direction_norms=norms,
        imputer=imputer,
        scaler=scaler,
        encoder=encoder,
        directions=directions,
    )
    return transform, z_train


def apply_projection_transform(frame: pd.DataFrame, transform: ProjectionTransform) -> pd.DataFrame:
    z_values = transform.scaler.transform(
        transform.imputer.transform(frame[transform.feature_cols].to_numpy(dtype=float))
    )
    z_values = residualize(z_values, transform.directions)
    out = frame.copy()
    out.loc[:, transform.feature_cols] = z_values
    return out


def projection_model_name(domain: str, component_count: int) -> str:
    if domain == "MODMA":
        return f"task_projection_k{component_count}_logistic"
    if domain == "EATD":
        return f"valence_projection_k{component_count}_ridge"
    raise ValueError(domain)


def prediction_representation(
    predictions: pd.DataFrame,
    *,
    domain: str,
    protocol_column: str,
) -> pd.DataFrame:
    keep = ["subject_id", protocol_column]
    if domain == "MODMA":
        return predictions[keep + ["y_score"]].rename(columns={"y_score": "prediction_value"})
    return predictions[keep + ["y_pred"]].rename(columns={"y_pred": "prediction_value"})


def run_protocol_identity_probe(
    train_repr: pd.DataFrame,
    eval_repr: pd.DataFrame,
    probe_cols: list[str],
    label_column: str,
    seed: int,
    domain: str,
    layer: str,
    representation: str,
) -> dict[str, Any]:
    subject_overlap = set(train_repr["subject_id"].astype(str)) & set(eval_repr["subject_id"].astype(str))
    train_labels = train_repr[label_column].astype(str)
    eval_labels = eval_repr[label_column].astype(str)
    if train_labels.nunique() < 2 or eval_labels.nunique() < 2:
        value = None
        skipped_reason = "missing_protocol_class_in_train_or_eval"
    else:
        model = logistic_pipeline(seed)
        model.fit(train_repr[probe_cols].to_numpy(dtype=float), train_labels)
        pred = model.predict(eval_repr[probe_cols].to_numpy(dtype=float))
        value = float(balanced_accuracy_score(eval_labels, pred))
        skipped_reason = None
    return {
        "domain": domain,
        "seed": int(seed),
        "probe_id": f"{domain.lower()}_{label_column}_identity_train_to_eval",
        "protocol_label": label_column,
        "probe_layer": layer,
        "representation": representation,
        "metric": "Balanced Accuracy",
        "value": safe_float(value),
        "train_rows": int(len(train_repr)),
        "eval_rows": int(len(eval_repr)),
        "train_subjects": int(train_repr["subject_id"].astype(str).nunique()),
        "eval_subjects": int(eval_repr["subject_id"].astype(str).nunique()),
        "subject_overlap_count": int(len(subject_overlap)),
        "skipped_reason": skipped_reason,
    }


def add_metric_rows(
    predictions: pd.DataFrame,
    metric_rows: list[dict[str, Any]],
    *,
    domain: str,
    target: str,
    task_type: str,
    seed: int,
    model: str,
    slice_column: str,
) -> None:
    for slice_value, group in [("pooled", predictions), *list(predictions.groupby(slice_column, sort=True))]:
        metrics = compute_metrics(group, task_type)
        for metric, value in metrics.items():
            metric_rows.append(
                {
                    "protocol": PROTOCOL_ID,
                    "domain": domain,
                    "target": target,
                    "task_type": task_type,
                    "seed": int(seed),
                    "model": model,
                    "slice_axis": slice_column if slice_value != "pooled" else "pooled",
                    "slice_value": str(slice_value),
                    "metric": metric,
                    "value": safe_float(value),
                    "sample_count": int(len(group)),
                    "subject_count": int(group["subject_id"].astype(str).nunique()),
                }
            )


def train_prior_predictions(train: pd.DataFrame, eval_frame: pd.DataFrame, model_name: str) -> pd.DataFrame:
    score = float(train["binary_label"].astype(int).mean())
    out = eval_frame[["subject_id", "task_type", "binary_label"]].copy()
    out["model"] = model_name
    out["target"] = "binary_label"
    out["task_type_metric"] = "binary_classification"
    out["y_true"] = out["binary_label"].astype(int)
    out["y_score"] = score
    out["y_pred"] = int(score >= 0.5)
    return out.drop(columns=["binary_label"])


def logistic_predictions(
    train: pd.DataFrame,
    eval_frame: pd.DataFrame,
    feature_cols: list[str],
    seed: int,
    model_name: str,
) -> pd.DataFrame:
    model = logistic_pipeline(seed)
    model.fit(train[feature_cols].to_numpy(dtype=float), train["binary_label"].astype(int))
    pred = model.predict(eval_frame[feature_cols].to_numpy(dtype=float))
    score = model.predict_proba(eval_frame[feature_cols].to_numpy(dtype=float))[:, 1]
    out = eval_frame[["subject_id", "task_type", "binary_label"]].copy()
    out["model"] = model_name
    out["target"] = "binary_label"
    out["task_type_metric"] = "binary_classification"
    out["y_true"] = out["binary_label"].astype(int)
    out["y_pred"] = pred.astype(int)
    out["y_score"] = score.astype(float)
    return out.drop(columns=["binary_label"])


def train_mean_predictions(train: pd.DataFrame, eval_frame: pd.DataFrame, model_name: str) -> pd.DataFrame:
    value = float(train["sds_total"].astype(float).mean())
    out = eval_frame[["subject_id", "valence", "sds_total"]].copy()
    out["model"] = model_name
    out["target"] = "sds_total"
    out["task_type_metric"] = "severity_regression"
    out["y_true"] = out["sds_total"].astype(float)
    out["y_pred"] = value
    out["y_score"] = ""
    return out.drop(columns=["sds_total"])


def ridge_predictions(
    train: pd.DataFrame,
    eval_frame: pd.DataFrame,
    feature_cols: list[str],
    model_name: str,
) -> pd.DataFrame:
    model = ridge_pipeline()
    model.fit(train[feature_cols].to_numpy(dtype=float), train["sds_total"].astype(float).to_numpy())
    pred = model.predict(eval_frame[feature_cols].to_numpy(dtype=float))
    out = eval_frame[["subject_id", "valence", "sds_total"]].copy()
    out["model"] = model_name
    out["target"] = "sds_total"
    out["task_type_metric"] = "severity_regression"
    out["y_true"] = out["sds_total"].astype(float)
    out["y_pred"] = pred.astype(float)
    out["y_score"] = ""
    return out.drop(columns=["sds_total"])


def build_modma_splits(modma: pd.DataFrame, seed: int) -> list[tuple[pd.DataFrame, pd.DataFrame, dict[str, Any]]]:
    subject_labels = (
        modma[["subject_id", "binary_label"]]
        .drop_duplicates()
        .sort_values("subject_id", key=lambda series: series.map(natural_key))
        .reset_index(drop=True)
    )
    splitter = StratifiedKFold(n_splits=5, shuffle=True, random_state=seed)
    splits: list[tuple[pd.DataFrame, pd.DataFrame, dict[str, Any]]] = []
    for fold, (train_idx, eval_idx) in enumerate(
        splitter.split(subject_labels["subject_id"], subject_labels["binary_label"].astype(int))
    ):
        train_subjects = set(subject_labels.iloc[train_idx]["subject_id"].astype(str))
        eval_subjects = set(subject_labels.iloc[eval_idx]["subject_id"].astype(str))
        train = modma[modma["subject_id"].astype(str).isin(train_subjects)].reset_index(drop=True)
        eval_frame = modma[modma["subject_id"].astype(str).isin(eval_subjects)].reset_index(drop=True)
        splits.append(
            (
                train,
                eval_frame,
                {
                    "domain": "MODMA",
                    "seed": int(seed),
                    "fold": int(fold),
                    "train_subjects": int(len(train_subjects)),
                    "eval_subjects": int(len(eval_subjects)),
                    "train_rows": int(len(train)),
                    "eval_rows": int(len(eval_frame)),
                    "subject_overlap_count": int(len(train_subjects & eval_subjects)),
                },
            )
        )
    return splits


def run_modma(
    modma: pd.DataFrame,
    feature_cols: list[str],
) -> tuple[pd.DataFrame, list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    predictions: list[pd.DataFrame] = []
    metric_rows: list[dict[str, Any]] = []
    identity_rows: list[dict[str, Any]] = []
    split_rows: list[dict[str, Any]] = []
    projection_rows: list[dict[str, Any]] = []

    for seed in SEEDS:
        for train, eval_frame, split_audit in build_modma_splits(modma, seed):
            fold = int(split_audit["fold"])
            split_rows.append(split_audit)

            prior = train_prior_predictions(train, eval_frame, TRAIN_PRIOR_MODEL)
            prior["domain"] = "MODMA"
            prior["seed"] = seed
            prior["fold"] = fold
            predictions.append(prior)
            add_metric_rows(
                prior,
                metric_rows,
                domain="MODMA",
                target="binary_label",
                task_type="binary_classification",
                seed=seed,
                model=TRAIN_PRIOR_MODEL,
                slice_column="task_type",
            )

            raw = logistic_predictions(train, eval_frame, feature_cols, seed, MODMA_RAW_MODEL)
            raw["domain"] = "MODMA"
            raw["seed"] = seed
            raw["fold"] = fold
            predictions.append(raw)
            add_metric_rows(
                raw,
                metric_rows,
                domain="MODMA",
                target="binary_label",
                task_type="binary_classification",
                seed=seed,
                model=MODMA_RAW_MODEL,
                slice_column="task_type",
            )
            identity_rows.append(
                run_protocol_identity_probe(
                    train,
                    eval_frame,
                    feature_cols,
                    "task_type",
                    seed,
                    "MODMA",
                    "feature",
                    "raw_egemaps_before_control",
                )
            )
            raw_train_pred = logistic_predictions(train, train, feature_cols, seed, MODMA_RAW_MODEL)
            identity_rows.append(
                run_protocol_identity_probe(
                    prediction_representation(raw_train_pred, domain="MODMA", protocol_column="task_type"),
                    prediction_representation(raw, domain="MODMA", protocol_column="task_type"),
                    ["prediction_value"],
                    "task_type",
                    seed,
                    "MODMA",
                    "prediction",
                    f"{MODMA_RAW_MODEL}_predictions",
                )
            )

            for component_count in PROJECTION_COMPONENTS:
                transform, projected_train_values = build_projection_transform(
                    train,
                    feature_cols,
                    "task_type",
                    component_count,
                    seed,
                )
                projected_train = train.copy()
                projected_train.loc[:, feature_cols] = projected_train_values
                projected_eval = apply_projection_transform(eval_frame, transform)
                model_name = projection_model_name("MODMA", component_count)
                control = logistic_predictions(projected_train, projected_eval, feature_cols, seed, model_name)
                control["domain"] = "MODMA"
                control["seed"] = seed
                control["fold"] = fold
                predictions.append(control)
                add_metric_rows(
                    control,
                    metric_rows,
                    domain="MODMA",
                    target="binary_label",
                    task_type="binary_classification",
                    seed=seed,
                    model=model_name,
                    slice_column="task_type",
                )
                projection_rows.append(projection_audit_row("MODMA", seed, fold, transform))
                identity_rows.append(
                    run_protocol_identity_probe(
                        projected_train,
                        projected_eval,
                        feature_cols,
                        "task_type",
                        seed,
                        "MODMA",
                        "feature",
                        f"task_projection_k{component_count}_after_control",
                    )
                )
                control_train_pred = logistic_predictions(projected_train, projected_train, feature_cols, seed, model_name)
                identity_rows.append(
                    run_protocol_identity_probe(
                        prediction_representation(control_train_pred, domain="MODMA", protocol_column="task_type"),
                        prediction_representation(control, domain="MODMA", protocol_column="task_type"),
                        ["prediction_value"],
                        "task_type",
                        seed,
                        "MODMA",
                        "prediction",
                        f"{model_name}_predictions",
                    )
                )

    return pd.concat(predictions, ignore_index=True), metric_rows, identity_rows, split_rows, projection_rows


def run_eatd(
    eatd: pd.DataFrame,
    feature_cols: list[str],
) -> tuple[pd.DataFrame, list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    predictions: list[pd.DataFrame] = []
    metric_rows: list[dict[str, Any]] = []
    identity_rows: list[dict[str, Any]] = []
    split_rows: list[dict[str, Any]] = []
    projection_rows: list[dict[str, Any]] = []
    train = eatd[eatd["split"].astype(str) == "train"].reset_index(drop=True)
    eval_frame = eatd[eatd["split"].astype(str) == "validation"].reset_index(drop=True)
    train_subjects = set(train["subject_id"].astype(str))
    eval_subjects = set(eval_frame["subject_id"].astype(str))
    split_audit = {
        "domain": "EATD",
        "seed": None,
        "fold": "official_validation",
        "train_subjects": int(len(train_subjects)),
        "eval_subjects": int(len(eval_subjects)),
        "train_rows": int(len(train)),
        "eval_rows": int(len(eval_frame)),
        "subject_overlap_count": int(len(train_subjects & eval_subjects)),
    }
    if split_audit["subject_overlap_count"]:
        raise ValueError("EATD official train/validation subject overlap detected")

    for seed in SEEDS:
        split_rows.append({**split_audit, "seed": int(seed)})
        mean_pred = train_mean_predictions(train, eval_frame, TRAIN_MEAN_MODEL)
        mean_pred["domain"] = "EATD"
        mean_pred["seed"] = seed
        mean_pred["fold"] = "official_validation"
        predictions.append(mean_pred)
        add_metric_rows(
            mean_pred,
            metric_rows,
            domain="EATD",
            target="sds_total",
            task_type="severity_regression",
            seed=seed,
            model=TRAIN_MEAN_MODEL,
            slice_column="valence",
        )

        raw = ridge_predictions(train, eval_frame, feature_cols, EATD_RAW_MODEL)
        raw["domain"] = "EATD"
        raw["seed"] = seed
        raw["fold"] = "official_validation"
        predictions.append(raw)
        add_metric_rows(
            raw,
            metric_rows,
            domain="EATD",
            target="sds_total",
            task_type="severity_regression",
            seed=seed,
            model=EATD_RAW_MODEL,
            slice_column="valence",
        )
        identity_rows.append(
            run_protocol_identity_probe(
                train,
                eval_frame,
                feature_cols,
                "valence",
                seed,
                "EATD",
                "feature",
                "raw_egemaps_before_control",
            )
        )
        raw_train_pred = ridge_predictions(train, train, feature_cols, EATD_RAW_MODEL)
        identity_rows.append(
            run_protocol_identity_probe(
                prediction_representation(raw_train_pred, domain="EATD", protocol_column="valence"),
                prediction_representation(raw, domain="EATD", protocol_column="valence"),
                ["prediction_value"],
                "valence",
                seed,
                "EATD",
                "prediction",
                f"{EATD_RAW_MODEL}_predictions",
            )
        )

        for component_count in PROJECTION_COMPONENTS:
            transform, projected_train_values = build_projection_transform(
                train,
                feature_cols,
                "valence",
                component_count,
                seed,
            )
            projected_train = train.copy()
            projected_train.loc[:, feature_cols] = projected_train_values
            projected_eval = apply_projection_transform(eval_frame, transform)
            model_name = projection_model_name("EATD", component_count)
            control = ridge_predictions(projected_train, projected_eval, feature_cols, model_name)
            control["domain"] = "EATD"
            control["seed"] = seed
            control["fold"] = "official_validation"
            predictions.append(control)
            add_metric_rows(
                control,
                metric_rows,
                domain="EATD",
                target="sds_total",
                task_type="severity_regression",
                seed=seed,
                model=model_name,
                slice_column="valence",
            )
            projection_rows.append(projection_audit_row("EATD", seed, "official_validation", transform))
            identity_rows.append(
                run_protocol_identity_probe(
                    projected_train,
                    projected_eval,
                    feature_cols,
                    "valence",
                    seed,
                    "EATD",
                    "feature",
                    f"valence_projection_k{component_count}_after_control",
                )
            )
            control_train_pred = ridge_predictions(projected_train, projected_train, feature_cols, model_name)
            identity_rows.append(
                run_protocol_identity_probe(
                    prediction_representation(control_train_pred, domain="EATD", protocol_column="valence"),
                    prediction_representation(control, domain="EATD", protocol_column="valence"),
                    ["prediction_value"],
                    "valence",
                    seed,
                    "EATD",
                    "prediction",
                    f"{model_name}_predictions",
                )
            )

    return pd.concat(predictions, ignore_index=True), metric_rows, identity_rows, split_rows, projection_rows


def projection_audit_row(domain: str, seed: int, fold: int | str, transform: ProjectionTransform) -> dict[str, Any]:
    return {
        "domain": domain,
        "seed": int(seed),
        "fold": fold,
        "protocol_label": transform.label_column,
        "requested_component_count": transform.requested_component_count,
        "fitted_component_count": transform.fitted_component_count,
        "direction_norm_min": safe_float(min(transform.direction_norms)) if transform.direction_norms else None,
        "direction_norm_max": safe_float(max(transform.direction_norms)) if transform.direction_norms else None,
        "label_counts_json": json.dumps(transform.label_counts, sort_keys=True),
        "control_uses_eval_target_labels": False,
        "control_uses_eval_protocol_labels_at_transform": False,
        "control_parameters_written": False,
        "transformed_features_written": False,
    }


def summarize_metrics(metrics_by_seed: pd.DataFrame) -> pd.DataFrame:
    grouped = metrics_by_seed.groupby(
        ["protocol", "domain", "target", "task_type", "model", "slice_axis", "slice_value", "metric"],
        dropna=False,
        sort=False,
    )
    summary = (
        grouped.agg(
            mean=("value", "mean"),
            std=("value", "std"),
            seed_count=("seed", "nunique"),
            sample_count_mean=("sample_count", "mean"),
            subject_count_mean=("subject_count", "mean"),
        )
        .reset_index()
        .sort_values(["domain", "target", "model", "slice_axis", "slice_value", "metric"])
    )
    summary["std"] = summary["std"].fillna(0.0)
    summary["ci95_low"] = summary["mean"] - 1.96 * summary["std"] / np.sqrt(summary["seed_count"].clip(lower=1))
    summary["ci95_high"] = summary["mean"] + 1.96 * summary["std"] / np.sqrt(summary["seed_count"].clip(lower=1))
    return summary


def summarize_identity(identity_by_seed: pd.DataFrame) -> pd.DataFrame:
    grouped = identity_by_seed.groupby(
        ["domain", "protocol_label", "probe_layer", "representation", "metric"],
        dropna=False,
        sort=False,
    )
    summary = (
        grouped.agg(
            mean=("value", "mean"),
            std=("value", "std"),
            seed_count=("seed", "nunique"),
            train_subjects_mean=("train_subjects", "mean"),
            eval_subjects_mean=("eval_subjects", "mean"),
            subject_overlap_count_sum=("subject_overlap_count", "sum"),
        )
        .reset_index()
        .sort_values(["domain", "probe_layer", "representation"])
    )
    summary["std"] = summary["std"].fillna(0.0)
    summary["ci95_low"] = summary["mean"] - 1.96 * summary["std"] / np.sqrt(summary["seed_count"].clip(lower=1))
    summary["ci95_high"] = summary["mean"] + 1.96 * summary["std"] / np.sqrt(summary["seed_count"].clip(lower=1))
    return summary


def build_comparison_summary(metric_summary: pd.DataFrame) -> pd.DataFrame:
    primary_specs = [
        ("MODMA", "binary_label", "Balanced Accuracy", MODMA_RAW_MODEL, "higher"),
        ("MODMA", "binary_label", "Macro-F1", MODMA_RAW_MODEL, "higher"),
        ("EATD", "sds_total", "MAE", EATD_RAW_MODEL, "lower"),
        ("EATD", "sds_total", "Spearman", EATD_RAW_MODEL, "higher"),
    ]
    rows: list[dict[str, Any]] = []
    for domain, target, metric, baseline_model, direction in primary_specs:
        subset = metric_summary[
            (metric_summary["domain"] == domain)
            & (metric_summary["target"] == target)
            & (metric_summary["metric"] == metric)
            & (metric_summary["slice_value"] != "pooled")
        ].copy()
        values = subset.set_index(["model", "slice_value"])["mean"].to_dict()
        for slice_value in sorted(subset["slice_value"].unique(), key=natural_key):
            baseline = values.get((baseline_model, slice_value))
            if baseline is None or not math.isfinite(float(baseline)):
                continue
            for model in sorted(subset["model"].unique(), key=natural_key):
                current = values.get((model, slice_value))
                if current is None:
                    continue
                if direction == "higher":
                    delta = float(current) - float(baseline)
                    relative_loss = max(0.0, float(baseline) - float(current)) / max(abs(float(baseline)), 1e-12)
                    within_tolerance = relative_loss <= 0.05
                else:
                    delta = float(current) - float(baseline)
                    relative_loss = max(0.0, float(current) - float(baseline)) / max(abs(float(baseline)), 1e-12)
                    within_tolerance = relative_loss <= 0.05
                rows.append(
                    {
                        "domain": domain,
                        "target": target,
                        "metric": metric,
                        "metric_direction": direction,
                        "slice_value": slice_value,
                        "baseline_model": baseline_model,
                        "model": model,
                        "baseline_value": safe_float(baseline),
                        "model_value": safe_float(current),
                        "delta_vs_baseline": safe_float(delta),
                        "relative_loss_vs_baseline": safe_float(relative_loss),
                        "within_5pct_baseline": bool(within_tolerance),
                    }
                )
    return pd.DataFrame(rows).sort_values(["domain", "target", "metric", "slice_value", "model"]).reset_index(drop=True)


def build_verdict(
    comparison_summary: pd.DataFrame,
    identity_summary: pd.DataFrame,
    metric_summary: pd.DataFrame,
    split_audit: pd.DataFrame,
) -> dict[str, Any]:
    overlap = int(split_audit["subject_overlap_count"].fillna(0).astype(int).sum())
    identity_lookup = identity_summary.set_index(["domain", "probe_layer", "representation"])["mean"].to_dict()
    domain_rows: list[dict[str, Any]] = []
    floor_lookup = metric_summary[
        (metric_summary["slice_value"] == "pooled")
        & (
            ((metric_summary["domain"] == "MODMA") & (metric_summary["metric"] == "Balanced Accuracy"))
            | ((metric_summary["domain"] == "EATD") & (metric_summary["metric"] == "MAE"))
        )
    ].set_index(["domain", "model", "metric"])["mean"].to_dict()
    for domain, raw_model, floor_model, label, primary_metrics, primary_direction in [
        ("MODMA", MODMA_RAW_MODEL, TRAIN_PRIOR_MODEL, "task", {"Balanced Accuracy", "Macro-F1"}, "higher"),
        ("EATD", EATD_RAW_MODEL, TRAIN_MEAN_MODEL, "valence", {"MAE"}, "lower"),
    ]:
        raw_feature = identity_lookup.get((domain, "feature", "raw_egemaps_before_control"))
        raw_prediction = identity_lookup.get((domain, "prediction", f"{raw_model}_predictions"))
        if domain == "MODMA":
            raw_primary = floor_lookup.get((domain, raw_model, "Balanced Accuracy"))
            floor_primary = floor_lookup.get((domain, floor_model, "Balanced Accuracy"))
            main_signal_above_floor = bool(
                raw_primary is not None and floor_primary is not None and raw_primary > floor_primary
            )
        else:
            raw_primary = floor_lookup.get((domain, raw_model, "MAE"))
            floor_primary = floor_lookup.get((domain, floor_model, "MAE"))
            main_signal_above_floor = bool(
                raw_primary is not None and floor_primary is not None and raw_primary < floor_primary
            )
        best: dict[str, Any] | None = None
        for component_count in PROJECTION_COMPONENTS:
            model = projection_model_name(domain, component_count)
            feature_repr = f"{label}_projection_k{component_count}_after_control"
            prediction_repr = f"{model}_predictions"
            feature_after = identity_lookup.get((domain, "feature", feature_repr))
            prediction_after = identity_lookup.get((domain, "prediction", prediction_repr))
            model_comparisons = comparison_summary[
                (comparison_summary["domain"] == domain)
                & (comparison_summary["model"] == model)
                & (comparison_summary["baseline_model"] == raw_model)
                & (comparison_summary["metric"].isin(primary_metrics))
            ]
            main_within = bool(
                not model_comparisons.empty
                and model_comparisons["within_5pct_baseline"].fillna(False).astype(bool).all()
            )
            feature_reduced = bool(raw_feature is not None and feature_after is not None and feature_after < raw_feature)
            prediction_not_worse = bool(
                raw_prediction is None
                or prediction_after is None
                or prediction_after <= raw_prediction + 0.02
            )
            pass_model = bool(
                overlap == 0
                and main_signal_above_floor
                and main_within
                and feature_reduced
                and prediction_not_worse
            )
            row = {
                "domain": domain,
                "model": model,
                "component_count": component_count,
                "raw_feature_identity_ba": safe_float(raw_feature),
                "feature_identity_ba_after": safe_float(feature_after),
                "raw_prediction_identity_ba": safe_float(raw_prediction),
                "prediction_identity_ba_after": safe_float(prediction_after),
                "raw_primary_metric_value": safe_float(raw_primary),
                "floor_primary_metric_value": safe_float(floor_primary),
                "primary_metric_direction": primary_direction,
                "main_signal_above_floor": main_signal_above_floor,
                "main_task_within_5pct_all_slices": main_within,
                "feature_identity_reduced": feature_reduced,
                "prediction_identity_not_worse": prediction_not_worse,
                "pass_model": pass_model,
            }
            if best is None:
                best = row
            else:
                current_key = (
                    0 if row["pass_model"] else 1,
                    row["feature_identity_ba_after"] if row["feature_identity_ba_after"] is not None else float("inf"),
                )
                best_key = (
                    0 if best["pass_model"] else 1,
                    best["feature_identity_ba_after"] if best["feature_identity_ba_after"] is not None else float("inf"),
                )
                if current_key < best_key:
                    best = row
        if best is not None:
            residual_high = bool(best["feature_identity_ba_after"] is None or best["feature_identity_ba_after"] > 0.75)
            if best["pass_model"] and residual_high:
                status = "partial_pass_protocol_identity_reduced_not_removed"
            elif best["pass_model"]:
                status = "pass_protocol_identity_control"
            elif not best["main_signal_above_floor"]:
                status = "blocked_main_task_below_floor"
            elif not best["feature_identity_reduced"]:
                status = "blocked_no_protocol_identity_to_reduce"
            else:
                status = "blocked_no_protocol_control_variant_passed"
            domain_rows.append({**best, "residual_feature_identity_high": residual_high, "status": status})

    passing_count = sum(1 for row in domain_rows if bool(row["pass_model"]))
    if passing_count == len(domain_rows) and any(row["residual_feature_identity_high"] for row in domain_rows):
        status = "partial_pass_some_protocol_identity_reduced"
    elif passing_count == len(domain_rows):
        status = "pass_protocol_task_valence_control"
    elif passing_count > 0:
        status = "mixed_protocol_control"
    else:
        status = "blocked_protocol_control"
    return {
        "pass_rule_status": status,
        "subject_overlap_violations": overlap,
        "domain_verdicts": domain_rows,
        "short_read": (
            "P5_MV04c tests train-fold protocol-label nuisance projection on MODMA task slices and EATD valence slices. "
            "Treat passing rows as diagnostic controls only; no transformed features, projection parameters, or row-level predictions are exported."
        ),
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
        r"raw prompt",
        r"raw response",
        r"PHQ_",
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
            if re.search(pattern, text):
                violations.append({"file": str(path.relative_to(out_dir)), "pattern": pattern})
    return {
        "audit_id": "P5_MV04c_protocol_task_valence_control_artifact_hygiene",
        "generated_at": utc_now(),
        "files_checked": files_checked,
        "violation_count": len(violations),
        "violations": violations,
        "artifact_hygiene_passed": len(violations) == 0,
        "local_only_files": ["p5_mv04c_local_predictions.csv"],
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
    identity_summary: pd.DataFrame,
) -> None:
    primary = metric_summary[
        (
            (metric_summary["domain"] == "MODMA")
            & (metric_summary["metric"].isin(["Balanced Accuracy", "Macro-F1"]))
        )
        | ((metric_summary["domain"] == "EATD") & (metric_summary["metric"].isin(["MAE", "Spearman"])))
    ].copy()
    primary = primary[primary["slice_value"] != "pooled"].sort_values(
        ["domain", "target", "metric", "slice_value", "model"]
    )
    identity = identity_summary.sort_values(["domain", "probe_layer", "representation"])
    verdict = run_summary["verdict"]

    lines = [
        "# P5_MV04c Protocol Task/Valence Control",
        "",
        f"Generated: `{run_summary['generated_at']}`",
        "",
        "## Scope",
        "",
        "This extension of P5_MV04 tests whether protocol-label nuisance directions learned on training subjects can reduce MODMA task identity and EATD valence identity while preserving the main depression/severity task. The control uses training-fold protocol labels only; evaluation protocol labels are used only for stratified reporting and identity probes. No transformed features, projection parameters, or row-level predictions are exported.",
        "",
        "## Inputs",
        "",
        f"- MODMA rows: `{run_summary['feature_contract']['modma_rows']}`; subjects: `{run_summary['feature_contract']['modma_subjects']}`; feature columns: `{run_summary['feature_contract']['modma_feature_count']}`.",
        f"- EATD rows: `{run_summary['feature_contract']['eatd_rows']}`; subjects: `{run_summary['feature_contract']['eatd_subjects']}`; feature columns: `{run_summary['feature_contract']['eatd_feature_count']}`.",
        f"- Subject-overlap violations: `{verdict['subject_overlap_violations']}`.",
        "",
        "## Primary Slice Metrics",
        "",
        "| domain | target | metric | slice | model | mean | seed count |",
        "| --- | --- | --- | --- | --- | ---: | ---: |",
    ]
    for _, row in primary.iterrows():
        lines.append(
            f"| {row['domain']} | {row['target']} | {row['metric']} | {row['slice_value']} | {row['model']} | {format_value(row['mean'])} | {int(row['seed_count'])} |"
        )

    lines.extend(
        [
            "",
            "## Main-Task Preservation",
            "",
            "| domain | metric | slice | model | baseline | delta | relative loss | within 5pct |",
            "| --- | --- | --- | --- | ---: | ---: | ---: | --- |",
        ]
    )
    for _, row in comparison_summary.iterrows():
        lines.append(
            f"| {row['domain']} | {row['metric']} | {row['slice_value']} | {row['model']} | {format_value(row['baseline_value'])} | {format_value(row['delta_vs_baseline'])} | {format_value(row['relative_loss_vs_baseline'])} | `{bool(row['within_5pct_baseline'])}` |"
        )

    lines.extend(
        [
            "",
            "## Protocol Identity Probes",
            "",
            "| domain | layer | representation | balanced accuracy | seed count |",
            "| --- | --- | --- | ---: | ---: |",
        ]
    )
    for _, row in identity.iterrows():
        lines.append(
            f"| {row['domain']} | {row['probe_layer']} | {row['representation']} | {format_value(row['mean'])} | {int(row['seed_count'])} |"
        )

    lines.extend(
        [
            "",
            "## Verdict",
            "",
            f"- Pass-rule status: `{verdict['pass_rule_status']}`.",
            f"- Short read: {verdict['short_read']}",
            "",
            "| domain | best model | feature identity before -> after | prediction identity before -> after | main signal beats floor | main task within 5pct | status |",
            "| --- | --- | ---: | ---: | --- | --- | --- |",
        ]
    )
    for row in verdict["domain_verdicts"]:
        lines.append(
            f"| {row['domain']} | {row['model']} | {format_value(row['raw_feature_identity_ba'])} -> {format_value(row['feature_identity_ba_after'])} | {format_value(row['raw_prediction_identity_ba'])} -> {format_value(row['prediction_identity_ba_after'])} | `{bool(row['main_signal_above_floor'])}` | `{bool(row['main_task_within_5pct_all_slices'])}` | `{row['status']}` |"
        )
    lines.extend(
        [
            "",
            "## Interpretation Boundary",
            "",
            "This is still a diagnostic control, not the full symptom-aligned model. A passing result means the lightweight feature contract can reduce some protocol identity without eval-protocol-label transforms; it does not prove task- or valence-invariant depression representation by itself.",
        ]
    )
    (out_dir / "report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--modma-features", type=Path, default=DEFAULT_MODMA_FEATURES)
    parser.add_argument("--eatd-features", type=Path, default=DEFAULT_EATD_FEATURES)
    args = parser.parse_args()

    out_dir = args.out_dir
    if out_dir.exists():
        shutil.rmtree(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    modma = read_csv(args.modma_features)
    eatd = read_csv(args.eatd_features)
    modma_features = feature_columns(modma)
    eatd_features = feature_columns(eatd)
    if not modma_features or not eatd_features:
        raise ValueError("missing feature columns")
    if sorted(modma["task_type"].astype(str).unique()) != sorted(MODMA_TASKS):
        raise ValueError("MODMA task feature cache does not contain the expected task set")
    if sorted(eatd["valence"].astype(str).unique()) != sorted(EATD_VALENCES):
        raise ValueError("EATD valence feature cache does not contain the expected valence set")

    modma_predictions, modma_metric_rows, modma_identity_rows, modma_split_rows, modma_projection_rows = run_modma(
        modma,
        modma_features,
    )
    eatd_predictions, eatd_metric_rows, eatd_identity_rows, eatd_split_rows, eatd_projection_rows = run_eatd(
        eatd,
        eatd_features,
    )
    predictions = pd.concat([modma_predictions, eatd_predictions], ignore_index=True)
    metrics_by_seed = pd.DataFrame([*modma_metric_rows, *eatd_metric_rows])
    identity_by_seed = pd.DataFrame([*modma_identity_rows, *eatd_identity_rows])
    split_audit = pd.DataFrame([*modma_split_rows, *eatd_split_rows])
    projection_audit = pd.DataFrame([*modma_projection_rows, *eatd_projection_rows])
    metric_summary = summarize_metrics(metrics_by_seed)
    identity_summary = summarize_identity(identity_by_seed)
    comparison_summary = build_comparison_summary(metric_summary)
    verdict = build_verdict(comparison_summary, identity_summary, metric_summary, split_audit)

    feature_contract = pd.DataFrame(
        [
            {
                "domain": "MODMA",
                "feature_space": "phase3_task_valence_egemaps_subject_task",
                "rows": int(len(modma)),
                "subjects": int(modma["subject_id"].astype(str).nunique()),
                "feature_count": int(len(modma_features)),
                "cache_read": str(args.modma_features.relative_to(WORKTREE_ROOT)),
                "feature_cache_written": False,
            },
            {
                "domain": "EATD",
                "feature_space": "phase3_task_valence_egemaps_valence",
                "rows": int(len(eatd)),
                "subjects": int(eatd["subject_id"].astype(str).nunique()),
                "feature_count": int(len(eatd_features)),
                "cache_read": str(args.eatd_features.relative_to(WORKTREE_ROOT)),
                "feature_cache_written": False,
            },
        ]
    )

    predictions.to_csv(out_dir / "p5_mv04c_local_predictions.csv", index=False)
    metrics_by_seed.to_csv(out_dir / "metrics_by_seed.csv", index=False)
    metric_summary.to_csv(out_dir / "metric_summary.csv", index=False)
    identity_by_seed.to_csv(out_dir / "identity_probe_by_seed.csv", index=False)
    identity_summary.to_csv(out_dir / "identity_probe_summary.csv", index=False)
    comparison_summary.to_csv(out_dir / "comparison_summary.csv", index=False)
    split_audit.to_csv(out_dir / "model_split_audit.csv", index=False)
    projection_audit.to_csv(out_dir / "projection_audit.csv", index=False)
    feature_contract.to_csv(out_dir / "feature_contract.csv", index=False)

    run_summary = {
        "protocol_id": "P5_MV04c",
        "name": "protocol_task_valence_control",
        "generated_at": utc_now(),
        "status": verdict["pass_rule_status"],
        "feature_contract": {
            "modma_rows": int(len(modma)),
            "modma_subjects": int(modma["subject_id"].astype(str).nunique()),
            "modma_feature_count": int(len(modma_features)),
            "eatd_rows": int(len(eatd)),
            "eatd_subjects": int(eatd["subject_id"].astype(str).nunique()),
            "eatd_feature_count": int(len(eatd_features)),
            "cached_features_read": True,
            "new_feature_extraction": False,
        },
        "model_contract": {
            "seeds": SEEDS,
            "projection_component_counts": PROJECTION_COMPONENTS,
            "control_uses_eval_target_labels": False,
            "control_uses_eval_protocol_labels_at_transform": False,
            "projection_parameters_written": False,
            "transformed_features_written": False,
            "row_level_predictions": "local_only_ignored",
        },
        "split_audit": {
            "rows": int(len(split_audit)),
            "subject_overlap_violations": int(split_audit["subject_overlap_count"].fillna(0).astype(int).sum()),
        },
        "verdict": verdict,
        "local_only_files": ["p5_mv04c_local_predictions.csv"],
    }
    (out_dir / "run_summary.json").write_text(json.dumps(run_summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    write_report(out_dir, run_summary, metric_summary, comparison_summary, identity_summary)
    hygiene = artifact_hygiene_audit(out_dir)
    run_summary["artifact_hygiene"] = hygiene
    (out_dir / "run_summary.json").write_text(json.dumps(run_summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (out_dir / "artifact_hygiene_audit.json").write_text(
        json.dumps(hygiene, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    if not hygiene["artifact_hygiene_passed"]:
        raise SystemExit("artifact hygiene failed")
    print(json.dumps({"out_dir": str(out_dir), "status": verdict["pass_rule_status"]}, indent=2))


if __name__ == "__main__":
    main()
