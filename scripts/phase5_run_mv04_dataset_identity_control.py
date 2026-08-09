#!/usr/bin/env python3
"""Run P5_MV04 dataset/protocol identity-control ablation.

This is a first minimal Phase 5 validation row focused on the P5_MV01 blocker:
frozen WavLM E-DAIC-vs-CMDC dataset identity is perfectly recoverable. The
runner reuses the P5_MV01 PHQ C01-C08 label and frozen WavLM subject-feature
contract, compares a pooled shared Ridge baseline against a train-fold
dataset-centering control, and writes compact aggregate metrics only. It does
not fine-tune encoders, scan raw audio, or persist transformed features/models.
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
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler


SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import phase5_run_mv01_phq_bridge as mv01


WORKTREE_ROOT = mv01.WORKTREE_ROOT
DEFAULT_OUT_DIR = WORKTREE_ROOT / "analysis" / "phase5_minimal_validation" / "p5_mv04_dataset_identity_control"
DEFAULT_MANIFEST_DIR = mv01.DEFAULT_MANIFEST_DIR
DEFAULT_SPLIT_PATH = mv01.DEFAULT_SPLIT_PATH

SEEDS = mv01.SEEDS
CONSTRUCTS = mv01.CONSTRUCTS
BASELINE_MODEL = "baseline_pooled_shared_ridge"
CONTROL_MODEL = "dataset_centered_shared_ridge"
TOTAL_ALLOC_MODEL = "total_alloc_ridge"
TRAIN_MEAN_MODEL = "train_mean"
PROTOCOL_ID = "pooled_shared_dataset_identity_control"


@dataclass(frozen=True)
class CenteringTransform:
    """Train-fold dataset centering parameters.

    The transform uses only training-fold feature moments. It does use known
    dataset identity as a diagnostic control variable at transform time, so the
    summary labels it as a dataset/protocol control rather than an inference
    contract for unknown-source deployment.
    """

    dataset_means: dict[str, np.ndarray]
    fallback_mean: np.ndarray
    feature_cols: list[str]
    train_counts: dict[str, int]


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def safe_float(value: Any) -> float | None:
    return mv01.safe_float(value)


def format_value(value: Any, digits: int = 3) -> str:
    numeric = safe_float(value)
    if numeric is None:
        return "NA"
    return f"{numeric:.{digits}f}"


def sort_subject_frame(frame: pd.DataFrame) -> pd.DataFrame:
    return frame.sort_values(
        ["dataset", "subject_id"],
        key=lambda series: series.map(lambda item: tuple(mv01.natural_key(item))),
    ).copy()


def build_centering_transform(train: pd.DataFrame, feature_cols: list[str]) -> CenteringTransform:
    fallback = train[feature_cols].mean(axis=0).reindex(feature_cols).fillna(0.0)
    fallback_array = fallback.to_numpy(dtype=float)
    dataset_means: dict[str, np.ndarray] = {}
    train_counts: dict[str, int] = {}
    for dataset, group in train.groupby("dataset", sort=True):
        mean = group[feature_cols].mean(axis=0).reindex(feature_cols).fillna(fallback)
        dataset_means[str(dataset)] = mean.to_numpy(dtype=float)
        train_counts[str(dataset)] = int(group["subject_key"].nunique())
    return CenteringTransform(
        dataset_means=dataset_means,
        fallback_mean=fallback_array,
        feature_cols=list(feature_cols),
        train_counts=train_counts,
    )


def apply_centering_transform(frame: pd.DataFrame, transform: CenteringTransform) -> pd.DataFrame:
    out = frame.copy()
    values = out[transform.feature_cols].to_numpy(dtype=float).copy()
    for dataset in sorted(out["dataset"].astype(str).unique(), key=mv01.natural_key):
        mask = (out["dataset"].astype(str) == dataset).to_numpy()
        mean = transform.dataset_means.get(dataset, transform.fallback_mean)
        values[mask] = values[mask] - mean
    out.loc[:, transform.feature_cols] = values
    return out


def fit_predict_constructs_for_train_and_eval(
    train: pd.DataFrame,
    eval_frame: pd.DataFrame,
    feature_cols: list[str],
    seed: int,
    model_name: str,
) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, Any]]:
    x_train = train[feature_cols].to_numpy(dtype=float)
    y_train = train[CONSTRUCTS].to_numpy(dtype=float)
    x_eval = eval_frame[feature_cols].to_numpy(dtype=float)
    alpha = mv01.choose_alpha(x_train, y_train, seed)
    model = mv01.make_ridge(alpha)
    model.fit(x_train, y_train)
    train_pred = np.clip(model.predict(x_train), 0.0, 3.0)
    eval_pred = np.clip(model.predict(x_eval), 0.0, 3.0)
    return (
        mv01.wide_predictions(train, train_pred, model_name),
        mv01.wide_predictions(eval_frame, eval_pred, model_name),
        {"selected_alpha": alpha},
    )


def prediction_representation(frame: pd.DataFrame, predictions: pd.DataFrame) -> pd.DataFrame:
    wide = (
        predictions.pivot_table(index="subject_key", columns="construct_id", values="y_pred", aggfunc="first")
        .reset_index()
        .rename_axis(None, axis=1)
    )
    meta = frame[["subject_key", "dataset", "subject_id"]].drop_duplicates()
    return meta.merge(wide, on="subject_key", how="inner")


def run_identity_probe(
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
        model.fit(train_repr[probe_cols].to_numpy(dtype=float), y_train)
        pred = model.predict(eval_repr[probe_cols].to_numpy(dtype=float))
        value = float(balanced_accuracy_score(y_eval, pred))
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
        "train_cmdc_subjects": int(np.sum(y_train == 1)),
        "train_edaic_subjects": int(np.sum(y_train == 0)),
        "eval_cmdc_subjects": int(np.sum(y_eval == 1)),
        "eval_edaic_subjects": int(np.sum(y_eval == 0)),
        "subject_overlap_count": int(len(train_overlap)),
        "skipped_reason": skipped_reason,
    }


def summarize_metrics(metrics_by_seed: pd.DataFrame) -> pd.DataFrame:
    return mv01.summarize_metrics(metrics_by_seed)


def summarize_identity(identity_by_seed: pd.DataFrame) -> pd.DataFrame:
    grouped = identity_by_seed.groupby(["probe_layer", "representation", "metric"], dropna=False)
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
        .sort_values(["probe_layer", "representation", "metric"])
    )
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
        for dataset_slice in sorted(group["dataset_slice"].unique(), key=mv01.natural_key):
            train_mean = values.get((TRAIN_MEAN_MODEL, dataset_slice))
            total_alloc = values.get((TOTAL_ALLOC_MODEL, dataset_slice))
            baseline = values.get((BASELINE_MODEL, dataset_slice))
            for model in sorted(group["model"].unique(), key=mv01.natural_key):
                current = values.get((model, dataset_slice))
                if current is None:
                    continue
                rows.append(
                    {
                        "protocol": protocol,
                        "dataset_slice": dataset_slice,
                        "model": model,
                        "macro_mae": current,
                        "delta_vs_train_mean": safe_float(current - train_mean) if train_mean is not None else None,
                        "delta_vs_total_alloc_ridge": safe_float(current - total_alloc) if total_alloc is not None else None,
                        "delta_vs_baseline_pooled_shared_ridge": safe_float(current - baseline) if baseline is not None else None,
                        "relative_delta_vs_baseline": safe_float((current - baseline) / baseline)
                        if baseline not in (None, 0)
                        else None,
                    }
                )
    return pd.DataFrame(rows)


def build_worst_slice_tables(metrics_by_seed: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    macro = metrics_by_seed[
        (metrics_by_seed["construct_id"] == "macro")
        & (metrics_by_seed["metric"] == "Macro Construct MAE")
        & (metrics_by_seed["dataset_slice"] != "pooled")
    ].copy()
    rows: list[dict[str, Any]] = []
    for (seed, protocol, model), group in macro.groupby(["seed", "protocol", "model"], sort=False):
        group = group.sort_values(["value", "dataset_slice"], ascending=[False, True])
        worst = group.iloc[0]
        rows.append(
            {
                "seed": seed,
                "protocol": protocol,
                "model": model,
                "metric": "Worst Dataset-Slice Macro Construct MAE",
                "worst_dataset_slice": worst["dataset_slice"],
                "value": safe_float(worst["value"]),
            }
        )
    by_seed = pd.DataFrame(rows)
    summary = (
        by_seed.groupby(["protocol", "model", "metric"], dropna=False)
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
    baseline = summary.loc[summary["model"] == BASELINE_MODEL, "mean"]
    baseline_value = float(baseline.iloc[0]) if not baseline.empty else math.nan
    summary["delta_vs_baseline_pooled_shared_ridge"] = summary["mean"] - baseline_value
    summary["relative_delta_vs_baseline"] = (summary["mean"] - baseline_value) / baseline_value
    return by_seed, summary


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
        raise ValueError("E-DAIC train/dev subject overlap detected")

    fold = cmdc_folds[seed % len(cmdc_folds)]
    cmdc_train_subjects = fold["train"]
    cmdc_eval_subjects = fold["validation"]
    train = table[
        ((table["dataset"] == "edaic") & (table["subject_id"].isin(edaic_train_subjects)))
        | ((table["dataset"] == "cmdc") & (table["subject_id"].isin(cmdc_train_subjects)))
    ]
    eval_frame = table[
        ((table["dataset"] == "edaic") & (table["subject_id"].isin(edaic_dev_subjects)))
        | ((table["dataset"] == "cmdc") & (table["subject_id"].isin(cmdc_eval_subjects)))
    ]
    train = sort_subject_frame(train)
    eval_frame = sort_subject_frame(eval_frame)
    overlap = set(train["subject_key"]) & set(eval_frame["subject_key"])
    if overlap:
        raise ValueError(f"pooled shared seed {seed} subject overlap: {sorted(overlap, key=mv01.natural_key)[:5]}")
    audit = {
        "seed": seed,
        "train_subjects": int(train["subject_key"].nunique()),
        "eval_subjects": int(eval_frame["subject_key"].nunique()),
        "train_edaic_subjects": int((train["dataset"] == "edaic").sum()),
        "train_cmdc_subjects": int((train["dataset"] == "cmdc").sum()),
        "eval_edaic_subjects": int((eval_frame["dataset"] == "edaic").sum()),
        "eval_cmdc_subjects": int((eval_frame["dataset"] == "cmdc").sum()),
        "subject_overlap_count": int(len(overlap)),
    }
    return train, eval_frame, audit


def add_prediction_metrics(
    predictions: pd.DataFrame,
    seed: int,
    model_name: str,
    prediction_frames: list[pd.DataFrame],
    metric_rows: list[dict[str, Any]],
) -> None:
    predictions = predictions.copy()
    predictions["seed"] = seed
    predictions["protocol"] = PROTOCOL_ID
    prediction_frames.append(predictions)
    metric_rows.extend(mv01.metric_rows_for_predictions(predictions, model_name, PROTOCOL_ID, seed))


def run_experiment(
    table: pd.DataFrame,
    feature_cols: list[str],
    cmdc_folds: dict[int, dict[str, set[str]]],
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    prediction_frames: list[pd.DataFrame] = []
    metric_rows: list[dict[str, Any]] = []
    identity_rows: list[dict[str, Any]] = []
    audit_rows: list[dict[str, Any]] = []

    for seed in SEEDS:
        train, eval_frame, base_audit = pooled_train_eval_for_seed(table, cmdc_folds, seed)
        centering = build_centering_transform(train, feature_cols)
        centered_train = apply_centering_transform(train, centering)
        centered_eval = apply_centering_transform(eval_frame, centering)

        train_mean_pred = mv01.predict_train_mean(train, eval_frame, TRAIN_MEAN_MODEL)
        add_prediction_metrics(train_mean_pred, seed, TRAIN_MEAN_MODEL, prediction_frames, metric_rows)
        audit_rows.append(
            {
                **base_audit,
                "protocol": PROTOCOL_ID,
                "model": TRAIN_MEAN_MODEL,
                "feature_transform": "none",
                "selected_alpha": None,
                "control_uses_eval_target_labels": False,
                "control_uses_eval_dataset_labels": False,
            }
        )

        total_alloc_pred, total_details = mv01.fit_predict_total_alloc(
            train, eval_frame, feature_cols, seed, TOTAL_ALLOC_MODEL
        )
        add_prediction_metrics(total_alloc_pred, seed, TOTAL_ALLOC_MODEL, prediction_frames, metric_rows)
        audit_rows.append(
            {
                **base_audit,
                "protocol": PROTOCOL_ID,
                "model": TOTAL_ALLOC_MODEL,
                "feature_transform": "none",
                "selected_alpha": total_details.get("selected_alpha"),
                "control_uses_eval_target_labels": False,
                "control_uses_eval_dataset_labels": False,
            }
        )

        baseline_train_pred, baseline_eval_pred, baseline_details = fit_predict_constructs_for_train_and_eval(
            train, eval_frame, feature_cols, seed, BASELINE_MODEL
        )
        add_prediction_metrics(baseline_eval_pred, seed, BASELINE_MODEL, prediction_frames, metric_rows)
        audit_rows.append(
            {
                **base_audit,
                "protocol": PROTOCOL_ID,
                "model": BASELINE_MODEL,
                "feature_transform": "raw_frozen_wavlm",
                "selected_alpha": baseline_details.get("selected_alpha"),
                "control_uses_eval_target_labels": False,
                "control_uses_eval_dataset_labels": False,
            }
        )

        control_train_pred, control_eval_pred, control_details = fit_predict_constructs_for_train_and_eval(
            centered_train, centered_eval, feature_cols, seed, CONTROL_MODEL
        )
        add_prediction_metrics(control_eval_pred, seed, CONTROL_MODEL, prediction_frames, metric_rows)
        audit_rows.append(
            {
                **base_audit,
                "protocol": PROTOCOL_ID,
                "model": CONTROL_MODEL,
                "feature_transform": "train_fold_dataset_centering",
                "selected_alpha": control_details.get("selected_alpha"),
                "control_uses_eval_target_labels": False,
                "control_uses_eval_dataset_labels": True,
                "centering_train_edaic_subjects": centering.train_counts.get("edaic", 0),
                "centering_train_cmdc_subjects": centering.train_counts.get("cmdc", 0),
            }
        )

        identity_rows.append(
            run_identity_probe(train, eval_frame, feature_cols, seed, "feature", "raw_frozen_wavlm_before_control")
        )
        identity_rows.append(
            run_identity_probe(
                centered_train,
                centered_eval,
                feature_cols,
                seed,
                "feature",
                "train_fold_dataset_centered_after_control",
            )
        )

        baseline_train_repr = prediction_representation(train, baseline_train_pred)
        baseline_eval_repr = prediction_representation(eval_frame, baseline_eval_pred)
        control_train_repr = prediction_representation(train, control_train_pred)
        control_eval_repr = prediction_representation(eval_frame, control_eval_pred)
        identity_rows.append(
            run_identity_probe(
                baseline_train_repr,
                baseline_eval_repr,
                CONSTRUCTS,
                seed,
                "prediction",
                "baseline_pooled_shared_ridge_predictions",
            )
        )
        identity_rows.append(
            run_identity_probe(
                control_train_repr,
                control_eval_repr,
                CONSTRUCTS,
                seed,
                "prediction",
                "dataset_centered_shared_ridge_predictions",
            )
        )

    predictions = pd.concat(prediction_frames, ignore_index=True)
    metrics_by_seed = pd.DataFrame(metric_rows)
    identity_by_seed = pd.DataFrame(identity_rows)
    model_audit = pd.DataFrame(audit_rows)
    return predictions, metrics_by_seed, identity_by_seed, model_audit


def build_verdict(
    comparison_summary: pd.DataFrame,
    identity_summary: pd.DataFrame,
    worst_slice_summary: pd.DataFrame,
    subject_overlap_violations: int,
) -> dict[str, Any]:
    identity_lookup = identity_summary.set_index(["probe_layer", "representation"])["mean"].to_dict()
    raw_feature_ba = identity_lookup.get(("feature", "raw_frozen_wavlm_before_control"))
    controlled_feature_ba = identity_lookup.get(("feature", "train_fold_dataset_centered_after_control"))
    baseline_prediction_ba = identity_lookup.get(("prediction", "baseline_pooled_shared_ridge_predictions"))
    controlled_prediction_ba = identity_lookup.get(("prediction", "dataset_centered_shared_ridge_predictions"))

    control_rows = comparison_summary[comparison_summary["model"] == CONTROL_MODEL].copy()
    main_task_within_5pct_all_slices = bool(
        not control_rows.empty and (control_rows["relative_delta_vs_baseline"].fillna(float("inf")) <= 0.05).all()
    )
    feature_identity_reduced = bool(
        raw_feature_ba is not None and controlled_feature_ba is not None and controlled_feature_ba < raw_feature_ba
    )
    prediction_identity_not_worse = bool(
        baseline_prediction_ba is None
        or controlled_prediction_ba is None
        or controlled_prediction_ba <= baseline_prediction_ba + 1e-9
    )
    worst_lookup = worst_slice_summary.set_index("model")["relative_delta_vs_baseline"].to_dict()
    worst_slice_within_5pct = bool(worst_lookup.get(CONTROL_MODEL, float("inf")) <= 0.05)
    pass_rule_met = bool(
        subject_overlap_violations == 0
        and feature_identity_reduced
        and prediction_identity_not_worse
        and main_task_within_5pct_all_slices
        and worst_slice_within_5pct
    )

    if pass_rule_met:
        status = "pass_minimal_control"
        short_read = (
            "The train-fold dataset-centering control reduces held-out E-DAIC-vs-CMDC identity probe balanced accuracy while preserving PHQ C01-C08 Macro MAE within the 5 percent relative tolerance versus the pooled shared baseline."
        )
    elif not feature_identity_reduced:
        status = "blocked_identity_not_reduced"
        short_read = (
            "The first identity-control ablation is runnable, but it does not reduce feature-layer dataset identity enough to pass the P5_MV04 gate."
        )
    elif not main_task_within_5pct_all_slices or not worst_slice_within_5pct:
        status = "blocked_main_task_degradation"
        short_read = (
            "The first identity-control ablation reduces dataset identity, but main-task Macro MAE degrades beyond the 5 percent relative tolerance."
        )
    else:
        status = "blocked_prediction_identity_or_split_audit"
        short_read = (
            "The first identity-control ablation is runnable but fails either prediction-layer identity or split-audit requirements."
        )

    return {
        "pass_rule_status": status,
        "pass_rule_met": pass_rule_met,
        "short_read": short_read,
        "feature_identity_ba_before": safe_float(raw_feature_ba),
        "feature_identity_ba_after": safe_float(controlled_feature_ba),
        "prediction_identity_ba_baseline": safe_float(baseline_prediction_ba),
        "prediction_identity_ba_control": safe_float(controlled_prediction_ba),
        "main_task_within_5pct_all_slices": main_task_within_5pct_all_slices,
        "worst_slice_within_5pct": worst_slice_within_5pct,
        "prediction_identity_not_worse": prediction_identity_not_worse,
    }


def target_map_frame() -> pd.DataFrame:
    rows: list[dict[str, str]] = []
    for dataset, spec in mv01.DATASET_SPECS.items():
        for construct_id in CONSTRUCTS:
            rows.append(
                {
                    "dataset": dataset,
                    "construct_id": construct_id,
                    "scale_item_code": {"edaic": "PHQ8_", "cmdc": "PHQ9_"}[dataset] + construct_id,
                    "source_scale": {"edaic": "PHQ-8", "cmdc": "PHQ-9"}[dataset],
                }
            )
    return pd.DataFrame(rows)


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
        "audit_id": "P5_MV04_artifact_hygiene",
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
    identity_summary: pd.DataFrame,
    worst_slice_summary: pd.DataFrame,
) -> None:
    macro = metric_summary[
        (metric_summary["construct_id"] == "macro")
        & (metric_summary["metric"] == "Macro Construct MAE")
        & (metric_summary["dataset_slice"] != "pooled")
    ].sort_values(["model", "dataset_slice"])
    comparison = comparison_summary.sort_values(["dataset_slice", "model"])
    identity = identity_summary.sort_values(["probe_layer", "representation"])
    worst = worst_slice_summary.sort_values("model")

    lines = [
        "# P5_MV04 Dataset Identity Control Ablation",
        "",
        f"Generated: `{run_summary['generated_at']}`",
        "",
        "## Scope",
        "",
        "This first runnable P5_MV04 row directly targets the P5_MV01 blocker: E-DAIC vs CMDC dataset identity is perfectly recoverable from frozen WavLM subject features. It reuses the P5_MV01 PHQ C01-C08 mapping and subject-level split contract, then compares a pooled shared Ridge baseline with a train-fold dataset-centering control. No encoder fine-tuning, raw-directory scan, learned representation export, or model checkpoint export is used.",
        "",
        "## Feature And Split Contract",
        "",
        f"- Common frozen WavLM columns: `{run_summary['feature_contract']['common_feature_column_count']}`.",
        f"- E-DAIC subjects joined: `{run_summary['feature_contract']['joined_subjects']['edaic']}`; official train/dev only.",
        f"- CMDC subjects joined: `{run_summary['feature_contract']['joined_subjects']['cmdc']}`; Phase 2 subject CV folds.",
        f"- Subject-overlap violations: `{run_summary['split_audit']['subject_overlap_violations']}`.",
        f"- Control uses eval target labels: `{run_summary['model_contract']['control_uses_eval_target_labels']}`.",
        f"- Control uses known eval dataset labels for centering: `{run_summary['model_contract']['control_uses_eval_dataset_labels']}`.",
        "",
        "## Dataset-Stratified Macro MAE",
        "",
        "| model | dataset | macro MAE | seed count |",
        "| --- | --- | ---: | ---: |",
    ]
    for _, row in macro.iterrows():
        lines.append(
            f"| {row['model']} | {row['dataset_slice']} | {format_value(row['mean'])} | {int(row['seed_count'])} |"
        )

    lines.extend(
        [
            "",
            "## Deltas",
            "",
            "Negative MAE deltas are improvements. Relative delta is versus the raw pooled shared Ridge baseline.",
            "",
            "| dataset | model | delta vs train_mean | delta vs total_alloc | delta vs baseline | relative delta vs baseline |",
            "| --- | --- | ---: | ---: | ---: | ---: |",
        ]
    )
    for _, row in comparison.iterrows():
        lines.append(
            f"| {row['dataset_slice']} | {row['model']} | {format_value(row['delta_vs_train_mean'])} | {format_value(row['delta_vs_total_alloc_ridge'])} | {format_value(row['delta_vs_baseline_pooled_shared_ridge'])} | {format_value(row['relative_delta_vs_baseline'])} |"
        )

    lines.extend(
        [
            "",
            "## Worst Slice",
            "",
            "| model | worst-slice Macro MAE | delta vs baseline | relative delta vs baseline |",
            "| --- | ---: | ---: | ---: |",
        ]
    )
    for _, row in worst.iterrows():
        lines.append(
            f"| {row['model']} | {format_value(row['mean'])} | {format_value(row['delta_vs_baseline_pooled_shared_ridge'])} | {format_value(row['relative_delta_vs_baseline'])} |"
        )

    lines.extend(
        [
            "",
            "## Dataset Identity Probes",
            "",
            "| layer | representation | identity balanced accuracy | seed count |",
            "| --- | --- | ---: | ---: |",
        ]
    )
    for _, row in identity.iterrows():
        lines.append(
            f"| {row['probe_layer']} | {row['representation']} | {format_value(row['mean'])} | {int(row['seed_count'])} |"
        )

    lines.extend(
        [
            "",
            "## Verdict",
            "",
            f"- Pass-rule status: `{run_summary['verdict']['pass_rule_status']}`.",
            f"- Feature identity BA before/after: `{format_value(run_summary['verdict']['feature_identity_ba_before'])}` -> `{format_value(run_summary['verdict']['feature_identity_ba_after'])}`.",
            f"- Baseline/control prediction identity BA: `{format_value(run_summary['verdict']['prediction_identity_ba_baseline'])}` -> `{format_value(run_summary['verdict']['prediction_identity_ba_control'])}`.",
            f"- Main task within 5 percent on all dataset slices: `{run_summary['verdict']['main_task_within_5pct_all_slices']}`.",
            "",
            run_summary["verdict"]["short_read"],
            "",
            "## Hygiene",
            "",
            f"- Artifact hygiene passed: `{run_summary['artifact_hygiene_passed']}`.",
            "- Row-level predictions are written as a local-only ignored CSV.",
            "- Transformed features, learned representations, model weights, source snippets, prompt/response text, audio, and video are not written.",
        ]
    )
    (out_dir / "report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


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

    phase2_root, phase2_root_source = mv01.resolve_phase2_root(args.phase2_root)
    table, feature_cols, availability = mv01.build_model_table(args.manifest_dir, phase2_root)
    cmdc_folds = mv01.load_cmdc_folds(args.split_path)
    predictions, metrics_by_seed, identity_by_seed, model_audit = run_experiment(table, feature_cols, cmdc_folds)

    metric_summary = summarize_metrics(metrics_by_seed)
    comparison_summary = build_comparison_summary(metric_summary)
    worst_slice_by_seed, worst_slice_summary = build_worst_slice_tables(metrics_by_seed)
    identity_summary = summarize_identity(identity_by_seed)
    subject_overlap_violations = int(model_audit["subject_overlap_count"].sum()) + int(
        identity_by_seed["subject_overlap_count"].sum()
    )
    verdict = build_verdict(comparison_summary, identity_summary, worst_slice_summary, subject_overlap_violations)

    safe_predictions = predictions.copy()
    safe_predictions["item_code"] = (
        safe_predictions["eval_dataset"].map({"edaic": "PHQ8_", "cmdc": "PHQ9_"}) + safe_predictions["construct_id"]
    )

    target_map = target_map_frame()
    metrics_by_seed.to_csv(out_dir / "metrics_by_seed.csv", index=False)
    metric_summary.to_csv(out_dir / "metric_summary.csv", index=False)
    comparison_summary.to_csv(out_dir / "comparison_summary.csv", index=False)
    worst_slice_by_seed.to_csv(out_dir / "worst_slice_by_seed.csv", index=False)
    worst_slice_summary.to_csv(out_dir / "worst_slice_summary.csv", index=False)
    identity_by_seed.to_csv(out_dir / "dataset_identity_probe_by_seed.csv", index=False)
    identity_summary.to_csv(out_dir / "dataset_identity_probe_summary.csv", index=False)
    availability.to_csv(out_dir / "feature_availability.csv", index=False)
    model_audit.to_csv(out_dir / "model_split_audit.csv", index=False)
    target_map.to_csv(out_dir / "construct_target_map.csv", index=False)
    safe_predictions.to_csv(out_dir / "p5_mv04_local_predictions.csv", index=False)

    run_summary: dict[str, Any] = {
        "run_id": "P5_MV04_dataset_protocol_control_ablation",
        "generated_at": utc_now(),
        "status": "complete",
        "phase2_feature_root_source": phase2_root_source,
        "feature_contract": {
            "feature_space": "frozen_wavlm_subject_mean",
            "common_feature_column_count": len(feature_cols),
            "joined_subjects": availability.set_index("dataset")["joined_subjects"].astype(int).to_dict(),
            "feature_dataset_identity_risk_before_control": {
                "probe": "E-DAIC_vs_CMDC_raw_frozen_WavLM_train_fold_to_eval_fold",
                "balanced_accuracy_mean": verdict["feature_identity_ba_before"],
            },
            "feature_dataset_identity_risk_after_control": {
                "probe": "E-DAIC_vs_CMDC_train_fold_dataset_centered_WavLM_train_fold_to_eval_fold",
                "balanced_accuracy_mean": verdict["feature_identity_ba_after"],
            },
        },
        "target_contract": {
            "constructs": CONSTRUCTS,
            "source_scales": {"edaic": "PHQ-8", "cmdc": "PHQ-9"},
            "c09_policy": "excluded_from_core_bridge_safety_sensitive_phq9_only",
        },
        "model_contract": {
            "models": [TRAIN_MEAN_MODEL, TOTAL_ALLOC_MODEL, BASELINE_MODEL, CONTROL_MODEL],
            "seeds": SEEDS,
            "encoder_finetuning": False,
            "raw_audio_scan": False,
            "control_variant": "train_fold_dataset_centering",
            "control_uses_eval_target_labels": False,
            "control_uses_eval_dataset_labels": True,
            "control_parameters_written": False,
        },
        "split_audit": {
            "subject_level": True,
            "edaic_official_test_used": False,
            "cmdc_phase2_subject_cv_used": True,
            "subject_overlap_violations": subject_overlap_violations,
        },
        "output_policy": {
            "row_level_predictions": "local_only_ignored",
            "learned_embeddings": "not_written",
            "transformed_features": "not_written",
            "model_weights": "not_written",
            "raw_clinical_text": "not_written",
            "raw_prompts_or_responses": "not_written",
        },
        "artifact_hygiene_passed": False,
        "verdict": verdict,
        "summary_files": [
            "report.md",
            "run_summary.json",
            "artifact_hygiene_audit.json",
            "metric_summary.csv",
            "metrics_by_seed.csv",
            "comparison_summary.csv",
            "worst_slice_summary.csv",
            "worst_slice_by_seed.csv",
            "dataset_identity_probe_summary.csv",
            "dataset_identity_probe_by_seed.csv",
            "feature_availability.csv",
            "model_split_audit.csv",
            "construct_target_map.csv",
        ],
        "local_only_files": ["p5_mv04_local_predictions.csv"],
    }

    (out_dir / "run_summary.json").write_text(json.dumps(run_summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    write_report(out_dir, run_summary, metric_summary, comparison_summary, identity_summary, worst_slice_summary)
    hygiene = artifact_hygiene_audit(out_dir)
    run_summary["artifact_hygiene_passed"] = bool(hygiene["artifact_hygiene_passed"])
    (out_dir / "run_summary.json").write_text(json.dumps(run_summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    write_report(out_dir, run_summary, metric_summary, comparison_summary, identity_summary, worst_slice_summary)
    (out_dir / "artifact_hygiene_audit.json").write_text(json.dumps(hygiene, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    if not hygiene["artifact_hygiene_passed"]:
        raise SystemExit("artifact hygiene violations found; see artifact_hygiene_audit.json")


if __name__ == "__main__":
    main()
