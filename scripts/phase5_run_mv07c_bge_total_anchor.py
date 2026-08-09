#!/usr/bin/env python3
"""Run P5_MV07c identity-projected BGE total-anchor validation.

This follow-up targets the MV07b blocker: BGE identity projection reduced
dataset identity but did not beat the CMDC total-allocation floor. MV07c keeps
the same frozen BGE and subject-level PHQ C01-C08 contract, then uses only
outer-training data to choose a projection depth and a total-anchored itemwise
blend. Evaluation labels and evaluation dataset labels are not used for model
selection or feature transformation.
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
from sklearn.model_selection import StratifiedKFold


SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import phase5_run_mv07_aligned_bge_shared_symptom as mv07
import phase5_run_mv07b_bge_identity_projection as mv07b


ROOT = mv07.ROOT
DEFAULT_OUT_DIR = ROOT / "analysis" / "phase5_minimal_validation" / "p5_mv07c_bge_total_anchor"
DEFAULT_MANIFEST_DIR = mv07.DEFAULT_MANIFEST_DIR
DEFAULT_SPLIT_PATH = mv07.DEFAULT_SPLIT_PATH
DEFAULT_PHASE2_ROOT = mv07.DEFAULT_PHASE2_ROOT

RUN_ID = "P5_MV07c_bge_total_anchor"
PROTOCOL_ID = "pooled_shared_phq_bge_total_anchor"
TARGET_FAMILY = "phq_core"
SEEDS = mv07.SEEDS
CONSTRUCTS = mv07.CONSTRUCTS
RIDGE_ALPHA_GRID = mv07.RIDGE_ALPHA_GRID
PROJECTION_COMPONENTS = [1, 3, 5, 10]
BLEND_WEIGHTS = [round(value, 2) for value in np.linspace(0.0, 1.0, 11)]

TRAIN_MEAN_MODEL = "train_mean"
RAW_TOTAL_ALLOC_MODEL = "raw_total_alloc_ridge"
RAW_ITEMWISE_MODEL = "raw_bge_itemwise_ridge"
SELECTED_PROJECTED_TOTAL_ALLOC_MODEL = "cvselected_projected_total_alloc_ridge"
SELECTED_TOTAL_ANCHOR_MODEL = "cvselected_projected_total_anchor_itemwise"

TRACKED_FILES = {
    "artifact_hygiene_audit.json",
    "comparison_summary.csv",
    "construct_target_map.csv",
    "identity_probe_by_seed.csv",
    "identity_probe_summary.csv",
    "inner_cv_selection_summary.csv",
    "label_feature_audit.csv",
    "metric_summary.csv",
    "metrics_by_seed.csv",
    "model_split_audit.csv",
    "projection_selection_audit.csv",
    "report.md",
    "run_summary.json",
}


@dataclass(frozen=True)
class HeadPredictions:
    itemwise: np.ndarray
    total_alloc: np.ndarray
    total_constrained_itemwise: np.ndarray
    selected_alpha_itemwise: float
    selected_alpha_total: float


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def safe_float(value: Any) -> float | None:
    return mv07.safe_float(value)


def format_value(value: Any, digits: int = 3) -> str:
    numeric = safe_float(value)
    return "NA" if numeric is None else f"{numeric:.{digits}f}"


def macro_construct_mae(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    values = []
    for idx in range(y_true.shape[1]):
        values.append(float(np.mean(np.abs(y_pred[:, idx] - y_true[:, idx]))))
    return float(np.mean(values))


def total_alloc_from_total(train: pd.DataFrame, total_pred: np.ndarray) -> np.ndarray:
    construct_means = train[CONSTRUCTS].mean(axis=0).to_numpy(dtype=float)
    denom = float(np.sum(construct_means))
    proportions = np.repeat(1.0 / len(CONSTRUCTS), len(CONSTRUCTS)) if denom <= 0 else construct_means / denom
    low, high = mv07.target_bounds(train, TARGET_FAMILY)
    return mv07.clip_matrix(total_pred.reshape(-1, 1) * proportions.reshape(1, -1), low, high)


def total_constrained_from_itemwise(train: pd.DataFrame, item_pred: np.ndarray, total_pred: np.ndarray) -> np.ndarray:
    low, high = mv07.target_bounds(train, TARGET_FAMILY)
    clipped = mv07.clip_matrix(item_pred, low, high)
    fallback = train[CONSTRUCTS].mean(axis=0).to_numpy(dtype=float)
    fallback_sum = float(np.sum(fallback))
    fallback_prop = np.repeat(1.0 / len(CONSTRUCTS), len(CONSTRUCTS)) if fallback_sum <= 0 else fallback / fallback_sum
    row_sums = clipped.sum(axis=1)
    proportions = np.zeros_like(clipped)
    nonzero = row_sums > 1e-12
    proportions[nonzero] = clipped[nonzero] / row_sums[nonzero].reshape(-1, 1)
    proportions[~nonzero] = fallback_prop.reshape(1, -1)
    return mv07.clip_matrix(total_pred.reshape(-1, 1) * proportions, low, high)


def blend_predictions(total_alloc: np.ndarray, total_constrained: np.ndarray, weight: float) -> np.ndarray:
    return (1.0 - float(weight)) * total_alloc + float(weight) * total_constrained


def fit_heads_predict(train: pd.DataFrame, eval_frame: pd.DataFrame, feature_cols: list[str], seed: int) -> HeadPredictions:
    x_train = train[feature_cols].to_numpy(dtype=float)
    y_train = train[CONSTRUCTS].to_numpy(dtype=float)
    x_eval = eval_frame[feature_cols].to_numpy(dtype=float)

    alpha_itemwise = mv07.choose_alpha(x_train, y_train, seed)
    item_model = mv07.ridge_pipeline(alpha_itemwise)
    item_model.fit(x_train, y_train)
    low, high = mv07.target_bounds(train, TARGET_FAMILY)
    item_pred = mv07.clip_matrix(item_model.predict(x_eval), low, high)

    y_total = train[CONSTRUCTS].sum(axis=1).to_numpy(dtype=float)
    alpha_total = mv07.choose_alpha(x_train, y_total.reshape(-1, 1), seed)
    total_model = mv07.ridge_pipeline(alpha_total)
    total_model.fit(x_train, y_total)
    total_pred = np.asarray(total_model.predict(x_eval), dtype=float).reshape(-1)
    total_alloc = total_alloc_from_total(train, total_pred)
    total_constrained = total_constrained_from_itemwise(train, item_pred, total_pred)
    return HeadPredictions(
        itemwise=item_pred,
        total_alloc=total_alloc,
        total_constrained_itemwise=total_constrained,
        selected_alpha_itemwise=float(alpha_itemwise),
        selected_alpha_total=float(alpha_total),
    )


def wide_predictions(
    eval_frame: pd.DataFrame,
    pred: np.ndarray,
    model: str,
    seed: int,
    fold: str,
) -> pd.DataFrame:
    return mv07.wide_predictions(
        eval_frame,
        pred,
        run_id=RUN_ID,
        protocol=PROTOCOL_ID,
        model=model,
        seed=seed,
        fold=fold,
        target_family=TARGET_FAMILY,
    )


def predict_train_mean(train: pd.DataFrame, eval_frame: pd.DataFrame, seed: int, fold: str) -> pd.DataFrame:
    low, high = mv07.target_bounds(train, TARGET_FAMILY)
    means = np.clip(train[CONSTRUCTS].mean(axis=0).to_numpy(dtype=float), low, high)
    pred = np.tile(means.reshape(1, -1), (len(eval_frame), 1))
    return wide_predictions(eval_frame, pred, TRAIN_MEAN_MODEL, seed, fold)


def select_projection_and_weight(
    train: pd.DataFrame,
    feature_cols: list[str],
    seed: int,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    y_dataset = (train["dataset"].astype(str) == "cmdc").astype(int).to_numpy()
    n_splits = min(5, min(np.bincount(y_dataset)))
    splitter = StratifiedKFold(n_splits=n_splits, shuffle=True, random_state=seed)
    rows: list[dict[str, Any]] = []
    for component_count in PROJECTION_COMPONENTS:
        weight_scores = {weight: [] for weight in BLEND_WEIGHTS}
        for inner_idx, (inner_train_idx, inner_eval_idx) in enumerate(splitter.split(train, y_dataset)):
            inner_train = train.iloc[inner_train_idx].copy().reset_index(drop=True)
            inner_eval = train.iloc[inner_eval_idx].copy().reset_index(drop=True)
            transform, projected_inner_train_values = mv07b.build_projection_transform(
                inner_train,
                feature_cols,
                component_count,
                seed + 100 * inner_idx,
            )
            projected_inner_train = inner_train.copy()
            projected_inner_train.loc[:, feature_cols] = projected_inner_train_values
            projected_inner_eval = mv07b.apply_projection_transform(inner_eval, transform)
            preds = fit_heads_predict(projected_inner_train, projected_inner_eval, feature_cols, seed + inner_idx)
            y_true = projected_inner_eval[CONSTRUCTS].to_numpy(dtype=float)
            for weight in BLEND_WEIGHTS:
                blended = blend_predictions(preds.total_alloc, preds.total_constrained_itemwise, weight)
                weight_scores[weight].append(macro_construct_mae(y_true, blended))
        for weight, scores in weight_scores.items():
            rows.append(
                {
                    "seed": seed,
                    "component_count": component_count,
                    "blend_weight_on_total_constrained_itemwise": weight,
                    "inner_cv_macro_mae_mean": safe_float(np.mean(scores)),
                    "inner_cv_macro_mae_std": safe_float(np.std(scores, ddof=1)) if len(scores) > 1 else 0.0,
                    "inner_cv_fold_count": len(scores),
                    "selection_uses_outer_eval_labels": False,
                    "selection_uses_outer_eval_dataset_labels": False,
                }
            )
    summary = pd.DataFrame(rows)
    selected = summary.sort_values(
        [
            "inner_cv_macro_mae_mean",
            "component_count",
            "blend_weight_on_total_constrained_itemwise",
        ],
        ascending=[True, True, True],
    ).iloc[0]
    return summary, {
        "selected_component_count": int(selected["component_count"]),
        "selected_blend_weight": float(selected["blend_weight_on_total_constrained_itemwise"]),
        "selected_inner_cv_macro_mae": safe_float(selected["inner_cv_macro_mae_mean"]),
    }


def run_experiment(
    table: pd.DataFrame,
    feature_cols: list[str],
    cmdc_folds: dict[int, dict[str, set[str]]],
    features_by_dataset: dict[str, pd.DataFrame],
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    prediction_frames: list[pd.DataFrame] = []
    identity_rows: list[dict[str, Any]] = []
    audit_rows: list[dict[str, Any]] = []
    selection_rows: list[dict[str, Any]] = []
    inner_cv_frames: list[pd.DataFrame] = []
    raw_feature_table = mv07b.feature_table_from_datasets(features_by_dataset, feature_cols)

    for seed in SEEDS:
        train, eval_frame, base_audit = mv07b.pooled_train_eval_for_seed(table, cmdc_folds, seed)
        fold = str(base_audit["fold"])
        inner_cv, selected = select_projection_and_weight(train, feature_cols, seed)
        inner_cv_frames.append(inner_cv)
        component_count = int(selected["selected_component_count"])
        blend_weight = float(selected["selected_blend_weight"])

        train_mean_pred = predict_train_mean(train, eval_frame, seed, fold)
        prediction_frames.append(train_mean_pred)

        raw_heads_eval = fit_heads_predict(train, eval_frame, feature_cols, seed)
        raw_total_eval = wide_predictions(eval_frame, raw_heads_eval.total_alloc, RAW_TOTAL_ALLOC_MODEL, seed, fold)
        raw_item_eval = wide_predictions(eval_frame, raw_heads_eval.itemwise, RAW_ITEMWISE_MODEL, seed, fold)
        prediction_frames.extend([raw_total_eval, raw_item_eval])

        transform, projected_train_values = mv07b.build_projection_transform(
            train,
            feature_cols,
            component_count,
            seed,
        )
        projected_train = train.copy()
        projected_train.loc[:, feature_cols] = projected_train_values
        projected_eval = mv07b.apply_projection_transform(eval_frame, transform)

        selected_heads_eval = fit_heads_predict(projected_train, projected_eval, feature_cols, seed)
        selected_heads_train = fit_heads_predict(projected_train, projected_train, feature_cols, seed)
        selected_blend_eval = blend_predictions(
            selected_heads_eval.total_alloc,
            selected_heads_eval.total_constrained_itemwise,
            blend_weight,
        )
        selected_blend_train = blend_predictions(
            selected_heads_train.total_alloc,
            selected_heads_train.total_constrained_itemwise,
            blend_weight,
        )
        selected_total_eval = wide_predictions(
            eval_frame,
            selected_heads_eval.total_alloc,
            SELECTED_PROJECTED_TOTAL_ALLOC_MODEL,
            seed,
            fold,
        )
        selected_anchor_eval = wide_predictions(
            eval_frame,
            selected_blend_eval,
            SELECTED_TOTAL_ANCHOR_MODEL,
            seed,
            fold,
        )
        selected_anchor_train = wide_predictions(
            train,
            selected_blend_train,
            SELECTED_TOTAL_ANCHOR_MODEL,
            seed,
            fold,
        )
        prediction_frames.extend([selected_total_eval, selected_anchor_eval])

        identity_rows.append(
            mv07b.run_binary_identity_probe(train, eval_frame, feature_cols, seed, "feature", "raw_bge_features")
        )
        identity_rows.append(
            mv07b.run_multidataset_feature_identity_cv(raw_feature_table, feature_cols, seed, "raw_bge_features")
        )
        identity_rows.append(
            mv07b.run_binary_identity_probe(
                projected_train,
                projected_eval,
                feature_cols,
                seed,
                "feature",
                "cvselected_projected_bge_features",
            )
        )
        projected_feature_table = mv07b.apply_projection_to_feature_tables(features_by_dataset, feature_cols, transform)
        identity_rows.append(
            mv07b.run_multidataset_feature_identity_cv(
                projected_feature_table,
                feature_cols,
                seed,
                "cvselected_projected_bge_features",
            )
        )
        identity_rows.append(
            mv07b.run_binary_identity_probe(
                mv07b.prediction_representation(train, selected_anchor_train),
                mv07b.prediction_representation(eval_frame, selected_anchor_eval),
                CONSTRUCTS,
                seed,
                "prediction",
                "cvselected_total_anchor_predictions",
            )
        )

        audit_rows.extend(
            [
                {
                    **base_audit,
                    "model": TRAIN_MEAN_MODEL,
                    "feature_transform": "none",
                    "selected_alpha_itemwise": None,
                    "selected_alpha_total": None,
                    "selected_component_count": None,
                    "selected_blend_weight": None,
                    "control_uses_eval_target_labels": False,
                    "control_uses_eval_dataset_labels": False,
                },
                {
                    **base_audit,
                    "model": RAW_TOTAL_ALLOC_MODEL,
                    "feature_transform": "raw_bge",
                    "selected_alpha_itemwise": None,
                    "selected_alpha_total": raw_heads_eval.selected_alpha_total,
                    "selected_component_count": None,
                    "selected_blend_weight": None,
                    "control_uses_eval_target_labels": False,
                    "control_uses_eval_dataset_labels": False,
                },
                {
                    **base_audit,
                    "model": RAW_ITEMWISE_MODEL,
                    "feature_transform": "raw_bge",
                    "selected_alpha_itemwise": raw_heads_eval.selected_alpha_itemwise,
                    "selected_alpha_total": None,
                    "selected_component_count": None,
                    "selected_blend_weight": None,
                    "control_uses_eval_target_labels": False,
                    "control_uses_eval_dataset_labels": False,
                },
                {
                    **base_audit,
                    "model": SELECTED_PROJECTED_TOTAL_ALLOC_MODEL,
                    "feature_transform": "cvselected_train_fold_logit_projection",
                    "selected_alpha_itemwise": None,
                    "selected_alpha_total": selected_heads_eval.selected_alpha_total,
                    "selected_component_count": component_count,
                    "selected_blend_weight": None,
                    "control_uses_eval_target_labels": False,
                    "control_uses_eval_dataset_labels": False,
                },
                {
                    **base_audit,
                    "model": SELECTED_TOTAL_ANCHOR_MODEL,
                    "feature_transform": "cvselected_train_fold_logit_projection_total_anchor",
                    "selected_alpha_itemwise": selected_heads_eval.selected_alpha_itemwise,
                    "selected_alpha_total": selected_heads_eval.selected_alpha_total,
                    "selected_component_count": component_count,
                    "selected_blend_weight": blend_weight,
                    "control_uses_eval_target_labels": False,
                    "control_uses_eval_dataset_labels": False,
                },
            ]
        )
        selection_rows.append(
            {
                "seed": seed,
                "fold": fold,
                "selected_component_count": component_count,
                "selected_blend_weight_on_total_constrained_itemwise": blend_weight,
                "selected_inner_cv_macro_mae": selected["selected_inner_cv_macro_mae"],
                "fitted_component_count": transform.fitted_component_count,
                "direction_norm_min": safe_float(min(transform.direction_norms)) if transform.direction_norms else None,
                "direction_norm_max": safe_float(max(transform.direction_norms)) if transform.direction_norms else None,
                "train_edaic_subjects": transform.train_counts.get("edaic", 0),
                "train_cmdc_subjects": transform.train_counts.get("cmdc", 0),
                "selection_uses_outer_eval_labels": False,
                "selection_uses_outer_eval_dataset_labels": False,
                "projection_parameters_written": False,
                "model_weights_written": False,
            }
        )

    return (
        pd.concat(prediction_frames, ignore_index=True),
        pd.DataFrame(identity_rows),
        pd.DataFrame(audit_rows),
        pd.DataFrame(selection_rows),
        pd.concat(inner_cv_frames, ignore_index=True),
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
        raw_total = values.get(RAW_TOTAL_ALLOC_MODEL)
        projected_total = values.get(SELECTED_PROJECTED_TOTAL_ALLOC_MODEL)
        raw_itemwise = values.get(RAW_ITEMWISE_MODEL)
        for model, value in values.items():
            rows.append(
                {
                    "protocol": protocol,
                    "target_family": target_family,
                    "dataset_slice": dataset_slice,
                    "model": model,
                    "macro_mae": value,
                    "delta_vs_train_mean": safe_float(value - train_mean) if train_mean is not None else None,
                    "delta_vs_raw_total_alloc_ridge": safe_float(value - raw_total) if raw_total is not None else None,
                    "delta_vs_projected_total_alloc_ridge": safe_float(value - projected_total)
                    if projected_total is not None
                    else None,
                    "delta_vs_raw_bge_itemwise_ridge": safe_float(value - raw_itemwise)
                    if raw_itemwise is not None
                    else None,
                }
            )
    return pd.DataFrame(rows)


def identity_value(identity_summary: pd.DataFrame, probe_id: str, representation: str) -> float | None:
    row = identity_summary[
        (identity_summary["probe_id"] == probe_id)
        & (identity_summary["representation"] == representation)
        & (identity_summary["metric"] == "Balanced Accuracy")
    ]
    if row.empty:
        return None
    return safe_float(row.iloc[0]["mean"])


def build_verdict(
    comparison: pd.DataFrame,
    identity_summary: pd.DataFrame,
    model_audit: pd.DataFrame,
) -> dict[str, Any]:
    target = comparison[comparison["model"] == SELECTED_TOTAL_ANCHOR_MODEL].copy()

    def delta(dataset: str, column: str) -> float | None:
        row = target[target["dataset_slice"] == dataset]
        if row.empty:
            return None
        return safe_float(row.iloc[0][column])

    edaic_vs_mean = delta("edaic", "delta_vs_train_mean")
    cmdc_vs_mean = delta("cmdc", "delta_vs_train_mean")
    edaic_vs_raw_total = delta("edaic", "delta_vs_raw_total_alloc_ridge")
    cmdc_vs_raw_total = delta("cmdc", "delta_vs_raw_total_alloc_ridge")
    edaic_vs_projected_total = delta("edaic", "delta_vs_projected_total_alloc_ridge")
    cmdc_vs_projected_total = delta("cmdc", "delta_vs_projected_total_alloc_ridge")
    raw_binary_feature = identity_value(
        identity_summary,
        "edaic_vs_cmdc_identity_train_fold_to_eval_fold",
        "raw_bge_features",
    )
    projected_binary_feature = identity_value(
        identity_summary,
        "edaic_vs_cmdc_identity_train_fold_to_eval_fold",
        "cvselected_projected_bge_features",
    )
    raw_three_way_feature = identity_value(
        identity_summary,
        "feature_identity_cv_edaic_cmdc_pdch",
        "raw_bge_features",
    )
    projected_three_way_feature = identity_value(
        identity_summary,
        "feature_identity_cv_edaic_cmdc_pdch",
        "cvselected_projected_bge_features",
    )
    prediction_identity = identity_value(
        identity_summary,
        "edaic_vs_cmdc_identity_train_fold_to_eval_fold",
        "cvselected_total_anchor_predictions",
    )
    subject_overlap_violations = int(model_audit["train_eval_subject_overlap"].sum())
    beats_mean = all(value is not None and value < 0.0 for value in [edaic_vs_mean, cmdc_vs_mean])
    beats_raw_total = all(value is not None and value < 0.0 for value in [edaic_vs_raw_total, cmdc_vs_raw_total])
    beats_projected_total = all(
        value is not None and value < 0.0 for value in [edaic_vs_projected_total, cmdc_vs_projected_total]
    )
    feature_reduced = bool(
        raw_binary_feature is not None
        and projected_binary_feature is not None
        and projected_binary_feature < raw_binary_feature
    )
    identity_ok = bool(prediction_identity is not None and prediction_identity <= 0.70)

    if subject_overlap_violations:
        status = "blocked_subject_overlap_bge_total_anchor"
    elif not beats_mean:
        status = "blocked_no_consistent_phq_gain_bge_total_anchor"
    elif not feature_reduced or not identity_ok:
        status = "blocked_identity_not_reduced_bge_total_anchor"
    elif not beats_raw_total:
        status = "blocked_not_better_than_raw_total_allocation_bge_total_anchor"
    elif not beats_projected_total:
        status = "partial_total_floor_only_not_itemwise_value_bge_total_anchor"
    else:
        status = "pass_bge_total_anchor_candidate"

    return {
        "pass_rule_status": status,
        "pass_rule_met": status.startswith("pass_"),
        "short_read": (
            "MV07c tests whether identity-projected BGE itemwise heads add construct value after a train-fold-selected total anchor. It is a shallow validation row, not the full method."
        ),
        "pooled_edaic_delta_vs_train_mean": edaic_vs_mean,
        "pooled_cmdc_delta_vs_train_mean": cmdc_vs_mean,
        "pooled_edaic_delta_vs_raw_total_alloc": edaic_vs_raw_total,
        "pooled_cmdc_delta_vs_raw_total_alloc": cmdc_vs_raw_total,
        "pooled_edaic_delta_vs_projected_total_alloc": edaic_vs_projected_total,
        "pooled_cmdc_delta_vs_projected_total_alloc": cmdc_vs_projected_total,
        "raw_binary_feature_identity_ba": safe_float(raw_binary_feature),
        "projected_binary_feature_identity_ba": safe_float(projected_binary_feature),
        "raw_three_way_feature_identity_ba": safe_float(raw_three_way_feature),
        "projected_three_way_feature_identity_ba": safe_float(projected_three_way_feature),
        "prediction_identity_ba": safe_float(prediction_identity),
        "subject_overlap_violations": subject_overlap_violations,
        "selected_component_counts": sorted(
            int(value) for value in model_audit["selected_component_count"].dropna().unique()
        ),
        "selected_blend_weights": sorted(
            safe_float(value) for value in model_audit["selected_blend_weight"].dropna().unique()
        ),
    }


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
        "audit_id": "P5_MV07c_bge_total_anchor_hygiene",
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
    selection: pd.DataFrame,
) -> None:
    verdict = run_summary["verdict"]
    key_models = [
        TRAIN_MEAN_MODEL,
        RAW_TOTAL_ALLOC_MODEL,
        RAW_ITEMWISE_MODEL,
        SELECTED_PROJECTED_TOTAL_ALLOC_MODEL,
        SELECTED_TOTAL_ANCHOR_MODEL,
    ]
    key = comparison[comparison["model"].isin(key_models)].copy()
    lines = [
        "# P5_MV07c BGE Total Anchor",
        "",
        f"Generated: `{run_summary['generated_at']}`",
        "",
        "## Scope",
        "",
        "This row tests a train-fold-selected total anchor for identity-projected BGE itemwise PHQ C01-C08 heads. Projection depth and blend weight are selected by inner CV on the outer training fold only.",
        "",
        "## Verdict",
        "",
        f"- Pass-rule status: `{verdict['pass_rule_status']}`.",
        f"- E-DAIC delta vs raw total allocation: `{format_value(verdict['pooled_edaic_delta_vs_raw_total_alloc'])}`.",
        f"- CMDC delta vs raw total allocation: `{format_value(verdict['pooled_cmdc_delta_vs_raw_total_alloc'])}`.",
        f"- E-DAIC delta vs projected total allocation: `{format_value(verdict['pooled_edaic_delta_vs_projected_total_alloc'])}`.",
        f"- CMDC delta vs projected total allocation: `{format_value(verdict['pooled_cmdc_delta_vs_projected_total_alloc'])}`.",
        f"- Binary feature identity BA raw/projected: `{format_value(verdict['raw_binary_feature_identity_ba'])}` -> `{format_value(verdict['projected_binary_feature_identity_ba'])}`.",
        f"- Prediction identity BA: `{format_value(verdict['prediction_identity_ba'])}`.",
        f"- Selected component counts: `{', '.join(map(str, verdict['selected_component_counts']))}`.",
        f"- Selected blend weights: `{', '.join(format_value(value, 2) for value in verdict['selected_blend_weights'])}`.",
        f"- Artifact hygiene passed: `{run_summary['artifact_hygiene_passed']}`.",
        "",
        verdict["short_read"],
        "",
        "## Key Macro MAE Comparisons",
        "",
        "| dataset | model | macro MAE | delta vs train mean | delta vs raw total alloc | delta vs projected total alloc |",
        "| --- | --- | ---: | ---: | ---: | ---: |",
    ]
    for _, row in key.sort_values(["dataset_slice", "model"]).iterrows():
        lines.append(
            f"| {row['dataset_slice']} | {row['model']} | {format_value(row['macro_mae'])} | {format_value(row['delta_vs_train_mean'])} | {format_value(row['delta_vs_raw_total_alloc_ridge'])} | {format_value(row['delta_vs_projected_total_alloc_ridge'])} |"
        )
    lines.extend(
        [
            "",
            "## Selection Audit",
            "",
            "| seed | selected k | selected blend weight | inner-CV Macro MAE |",
            "| ---: | ---: | ---: | ---: |",
        ]
    )
    for _, row in selection.sort_values("seed").iterrows():
        lines.append(
            f"| {int(row['seed'])} | {int(row['selected_component_count'])} | {format_value(row['selected_blend_weight_on_total_constrained_itemwise'], 2)} | {format_value(row['selected_inner_cv_macro_mae'])} |"
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
            "- This row is a shallow total-anchor diagnostic, not the full method.",
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
    predictions, identity_by_seed, model_audit, projection_selection, inner_cv = run_experiment(
        phq_table,
        feature_cols,
        cmdc_folds,
        features,
    )
    predictions.to_csv(out_dir / "p5_mv07c_local_predictions.csv", index=False)
    model_audit.to_csv(out_dir / "model_split_audit.csv", index=False)
    projection_selection.to_csv(out_dir / "projection_selection_audit.csv", index=False)
    inner_cv.to_csv(out_dir / "inner_cv_selection_summary.csv", index=False)

    metrics_by_seed = pd.DataFrame(mv07.metric_rows_for_predictions(predictions))
    metric_summary = mv07.summarize_metrics(metrics_by_seed, predictions)
    comparison = build_comparison_summary(metric_summary)
    identity_summary = mv07b.summarize_identity(identity_by_seed)
    verdict = build_verdict(comparison, identity_summary, model_audit)

    metrics_by_seed.to_csv(out_dir / "metrics_by_seed.csv", index=False)
    metric_summary.to_csv(out_dir / "metric_summary.csv", index=False)
    comparison.to_csv(out_dir / "comparison_summary.csv", index=False)
    identity_by_seed.to_csv(out_dir / "identity_probe_by_seed.csv", index=False)
    identity_summary.to_csv(out_dir / "identity_probe_summary.csv", index=False)

    run_summary: dict[str, Any] = {
        "run_id": RUN_ID,
        "generated_at": utc_now(),
        "status": "complete",
        "scope": "identity_projected_bge_total_anchor_follow_up",
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
            "heads": [
                TRAIN_MEAN_MODEL,
                RAW_TOTAL_ALLOC_MODEL,
                RAW_ITEMWISE_MODEL,
                SELECTED_PROJECTED_TOTAL_ALLOC_MODEL,
                SELECTED_TOTAL_ANCHOR_MODEL,
            ],
            "seeds": SEEDS,
            "ridge_alpha_grid": RIDGE_ALPHA_GRID,
            "projection_component_grid": PROJECTION_COMPONENTS,
            "blend_weight_grid": BLEND_WEIGHTS,
            "component_and_weight_selection": "inner_cv_on_outer_train_only",
            "control_uses_eval_target_labels": False,
            "control_uses_eval_dataset_labels": False,
            "projection_directions_written": False,
            "model_weights_written": False,
            "subject_overlap_violations": int(model_audit["train_eval_subject_overlap"].sum()),
        },
        "verdict": verdict,
        "output_policy": {
            "tracked_outputs": sorted(TRACKED_FILES),
            "local_only_outputs": ["p5_mv07c_local_predictions.csv"],
        },
        "artifact_hygiene_passed": False,
    }
    (out_dir / "run_summary.json").write_text(
        json.dumps(run_summary, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    write_report(out_dir, run_summary, comparison, identity_summary, projection_selection)
    hygiene = artifact_hygiene(out_dir)
    run_summary["artifact_hygiene_passed"] = bool(hygiene["artifact_hygiene_passed"])
    (out_dir / "run_summary.json").write_text(
        json.dumps(run_summary, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    write_report(out_dir, run_summary, comparison, identity_summary, projection_selection)
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
                "prediction_identity_ba": verdict["prediction_identity_ba"],
                "cmdc_delta_vs_raw_total_alloc": verdict["pooled_cmdc_delta_vs_raw_total_alloc"],
                "cmdc_delta_vs_projected_total_alloc": verdict["pooled_cmdc_delta_vs_projected_total_alloc"],
            },
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
