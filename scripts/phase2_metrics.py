#!/usr/bin/env python3
"""Unified Phase 2 metric helpers for baseline prediction files."""

from __future__ import annotations

import argparse
import json
import math
from collections import defaultdict
from pathlib import Path
from typing import Any, Iterable

import numpy as np
import pandas as pd


METRIC_NAMES = {
    "binary_classification": ["Macro-F1", "Balanced Accuracy", "AUROC", "AUPRC", "ECE", "Brier Score"],
    "severity_regression": ["CCC", "MAE", "RMSE", "Spearman"],
    "ordinal_prediction": ["QWK", "Ordinal MAE", "Macro-F1", "ECE", "Brier Score"],
}


def safe_float(value: Any) -> float | None:
    try:
        out = float(value)
    except (TypeError, ValueError):
        return None
    return out if math.isfinite(out) else None


def numeric_pair(y_true: Iterable[Any], y_pred: Iterable[Any]) -> tuple[np.ndarray, np.ndarray]:
    true = np.asarray(list(y_true), dtype=np.float64).reshape(-1)
    pred = np.asarray(list(y_pred), dtype=np.float64).reshape(-1)
    size = min(true.size, pred.size)
    true = true[:size]
    pred = pred[:size]
    mask = np.isfinite(true) & np.isfinite(pred)
    return true[mask], pred[mask]


def average_ranks(values: np.ndarray) -> np.ndarray:
    order = np.argsort(values, kind="mergesort")
    ranks = np.empty(values.size, dtype=np.float64)
    start = 0
    while start < values.size:
        end = start + 1
        while end < values.size and values[order[end]] == values[order[start]]:
            end += 1
        ranks[order[start:end]] = (start + 1 + end) / 2.0
        start = end
    return ranks


def pearson(x: np.ndarray, y: np.ndarray) -> float | None:
    if x.size < 2 or y.size < 2:
        return None
    x_centered = x - float(np.mean(x))
    y_centered = y - float(np.mean(y))
    denom = float(np.sqrt(np.sum(x_centered**2) * np.sum(y_centered**2)))
    if denom <= 0.0:
        return None
    return safe_float(float(np.sum(x_centered * y_centered) / denom))


def spearman(y_true: Iterable[Any], y_pred: Iterable[Any]) -> float | None:
    true, pred = numeric_pair(y_true, y_pred)
    if true.size < 2:
        return None
    return pearson(average_ranks(true), average_ranks(pred))


def concordance_correlation_coefficient(y_true: Iterable[Any], y_pred: Iterable[Any]) -> float | None:
    true, pred = numeric_pair(y_true, y_pred)
    if true.size < 2:
        return None
    mean_true = float(np.mean(true))
    mean_pred = float(np.mean(pred))
    var_true = float(np.var(true))
    var_pred = float(np.var(pred))
    covariance = float(np.mean((true - mean_true) * (pred - mean_pred)))
    denominator = var_true + var_pred + (mean_true - mean_pred) ** 2
    if denominator <= 0.0:
        return None
    return safe_float((2.0 * covariance) / denominator)


def regression_metrics(y_true: Iterable[Any], y_pred: Iterable[Any]) -> dict[str, float | None]:
    true, pred = numeric_pair(y_true, y_pred)
    if true.size == 0:
        return {name: None for name in METRIC_NAMES["severity_regression"]}
    err = pred - true
    return {
        "CCC": concordance_correlation_coefficient(true, pred),
        "MAE": safe_float(np.mean(np.abs(err))),
        "RMSE": safe_float(np.sqrt(np.mean(err**2))),
        "Spearman": spearman(true, pred),
    }


def as_int_pair(y_true: Iterable[Any], y_pred: Iterable[Any]) -> tuple[np.ndarray, np.ndarray]:
    true, pred = numeric_pair(y_true, y_pred)
    return true.astype(np.int64), pred.astype(np.int64)


def macro_f1(y_true: Iterable[Any], y_pred: Iterable[Any], labels: list[int] | None = None) -> float | None:
    true, pred = as_int_pair(y_true, y_pred)
    if true.size == 0:
        return None
    if labels is None:
        labels = sorted(set(true.tolist()) | set(pred.tolist()))
    scores: list[float] = []
    for label in labels:
        true_label = true == label
        pred_label = pred == label
        tp = int(np.sum(true_label & pred_label))
        fp = int(np.sum(~true_label & pred_label))
        fn = int(np.sum(true_label & ~pred_label))
        precision = tp / float(tp + fp) if tp + fp > 0 else 0.0
        recall = tp / float(tp + fn) if tp + fn > 0 else 0.0
        scores.append((2.0 * precision * recall / (precision + recall)) if precision + recall > 0 else 0.0)
    return safe_float(np.mean(scores))


def balanced_accuracy(y_true: Iterable[Any], y_pred: Iterable[Any], labels: list[int] | None = None) -> float | None:
    true, pred = as_int_pair(y_true, y_pred)
    if true.size == 0:
        return None
    if labels is None:
        labels = sorted(set(true.tolist()) | set(pred.tolist()))
    recalls: list[float] = []
    for label in labels:
        true_label = true == label
        support = int(np.sum(true_label))
        if support <= 0:
            continue
        recalls.append(float(np.sum(true_label & (pred == label))) / float(support))
    return safe_float(np.mean(recalls)) if recalls else None


def binary_auroc(y_true: Iterable[Any], y_score: Iterable[Any]) -> float | None:
    true = np.asarray(list(y_true), dtype=np.int64).reshape(-1)
    score = np.asarray(list(y_score), dtype=np.float64).reshape(-1)
    size = min(true.size, score.size)
    true = true[:size]
    score = score[:size]
    mask = np.isfinite(score)
    true = true[mask]
    score = score[mask]
    positives = true == 1
    negatives = true == 0
    n_pos = int(np.sum(positives))
    n_neg = int(np.sum(negatives))
    if n_pos == 0 or n_neg == 0:
        return None
    ranks = average_ranks(score)
    rank_sum_pos = float(np.sum(ranks[positives]))
    auc = (rank_sum_pos - (n_pos * (n_pos + 1) / 2.0)) / float(n_pos * n_neg)
    return safe_float(auc)


def binary_auprc(y_true: Iterable[Any], y_score: Iterable[Any]) -> float | None:
    true = np.asarray(list(y_true), dtype=np.int64).reshape(-1)
    score = np.asarray(list(y_score), dtype=np.float64).reshape(-1)
    size = min(true.size, score.size)
    true = true[:size]
    score = score[:size]
    mask = np.isfinite(score)
    true = true[mask]
    score = score[mask]
    n_pos = int(np.sum(true == 1))
    if n_pos == 0:
        return None
    order = np.argsort(-score, kind="mergesort")
    sorted_true = true[order]
    tp = np.cumsum(sorted_true == 1)
    rank = np.arange(1, sorted_true.size + 1)
    precision = tp / rank
    return safe_float(np.sum(precision[sorted_true == 1]) / float(n_pos))


def binary_ece(y_true: Iterable[Any], y_score: Iterable[Any], bins: int = 10) -> float | None:
    true = np.asarray(list(y_true), dtype=np.float64).reshape(-1)
    score = np.asarray(list(y_score), dtype=np.float64).reshape(-1)
    size = min(true.size, score.size)
    true = true[:size]
    score = score[:size]
    mask = np.isfinite(true) & np.isfinite(score)
    true = true[mask]
    score = np.clip(score[mask], 0.0, 1.0)
    if true.size == 0:
        return None
    edges = np.linspace(0.0, 1.0, bins + 1)
    ece = 0.0
    for idx in range(bins):
        if idx == bins - 1:
            bin_mask = (score >= edges[idx]) & (score <= edges[idx + 1])
        else:
            bin_mask = (score >= edges[idx]) & (score < edges[idx + 1])
        if not np.any(bin_mask):
            continue
        confidence = float(np.mean(score[bin_mask]))
        accuracy = float(np.mean(true[bin_mask]))
        ece += float(np.mean(bin_mask)) * abs(accuracy - confidence)
    return safe_float(ece)


def binary_brier(y_true: Iterable[Any], y_score: Iterable[Any]) -> float | None:
    true = np.asarray(list(y_true), dtype=np.float64).reshape(-1)
    score = np.asarray(list(y_score), dtype=np.float64).reshape(-1)
    size = min(true.size, score.size)
    true = true[:size]
    score = score[:size]
    mask = np.isfinite(true) & np.isfinite(score)
    if not np.any(mask):
        return None
    return safe_float(np.mean((np.clip(score[mask], 0.0, 1.0) - true[mask]) ** 2))


def classification_metrics(
    y_true: Iterable[Any],
    y_pred: Iterable[Any],
    y_score: Iterable[Any] | None = None,
) -> dict[str, float | None]:
    labels = [0, 1]
    out = {
        "Macro-F1": macro_f1(y_true, y_pred, labels),
        "Balanced Accuracy": balanced_accuracy(y_true, y_pred, labels),
        "AUROC": None,
        "AUPRC": None,
        "ECE": None,
        "Brier Score": None,
    }
    if y_score is not None:
        out.update(
            {
                "AUROC": binary_auroc(y_true, y_score),
                "AUPRC": binary_auprc(y_true, y_score),
                "ECE": binary_ece(y_true, y_score),
                "Brier Score": binary_brier(y_true, y_score),
            }
        )
    return out


def quadratic_weighted_kappa(y_true: Iterable[Any], y_pred: Iterable[Any]) -> float | None:
    true, pred = as_int_pair(y_true, y_pred)
    if true.size == 0:
        return None
    labels = sorted(set(true.tolist()) | set(pred.tolist()))
    if len(labels) <= 1:
        return None
    index = {label: idx for idx, label in enumerate(labels)}
    n = len(labels)
    observed = np.zeros((n, n), dtype=np.float64)
    for t, p in zip(true, pred, strict=False):
        observed[index[int(t)], index[int(p)]] += 1.0
    true_hist = np.sum(observed, axis=1)
    pred_hist = np.sum(observed, axis=0)
    expected = np.outer(true_hist, pred_hist) / float(np.sum(observed))
    weights = np.zeros((n, n), dtype=np.float64)
    for i in range(n):
        for j in range(n):
            weights[i, j] = ((i - j) ** 2) / float((n - 1) ** 2)
    observed_weighted = float(np.sum(weights * observed))
    expected_weighted = float(np.sum(weights * expected))
    if expected_weighted <= 0.0:
        return None
    return safe_float(1.0 - observed_weighted / expected_weighted)


def parse_probability_vector(value: Any) -> list[float] | None:
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return None
    if isinstance(value, list):
        return [float(x) for x in value]
    text = str(value).strip()
    if not text:
        return None
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        return None
    if not isinstance(parsed, list):
        return None
    try:
        return [float(x) for x in parsed]
    except (TypeError, ValueError):
        return None


def multiclass_ece_and_brier(y_true: Iterable[Any], probabilities: Iterable[Any], bins: int = 10) -> tuple[float | None, float | None]:
    true = np.asarray(list(y_true), dtype=np.int64).reshape(-1)
    prob_rows = [parse_probability_vector(value) for value in probabilities]
    usable: list[tuple[int, np.ndarray]] = []
    for label, probs in zip(true, prob_rows, strict=False):
        if probs is None:
            continue
        arr = np.asarray(probs, dtype=np.float64)
        if arr.size == 0 or not np.all(np.isfinite(arr)):
            continue
        total = float(np.sum(arr))
        if total <= 0.0:
            continue
        usable.append((int(label), np.clip(arr / total, 0.0, 1.0)))
    if not usable:
        return None, None
    class_count = max(max(label for label, _ in usable) + 1, max(probs.size for _, probs in usable))
    confidences: list[float] = []
    accuracies: list[float] = []
    briers: list[float] = []
    for label, probs in usable:
        padded = np.zeros(class_count, dtype=np.float64)
        padded[: probs.size] = probs[:class_count]
        pred = int(np.argmax(padded))
        confidences.append(float(np.max(padded)))
        accuracies.append(1.0 if pred == label else 0.0)
        one_hot = np.zeros(class_count, dtype=np.float64)
        if 0 <= label < class_count:
            one_hot[label] = 1.0
        briers.append(float(np.sum((padded - one_hot) ** 2)))
    confidences_arr = np.asarray(confidences, dtype=np.float64)
    accuracies_arr = np.asarray(accuracies, dtype=np.float64)
    edges = np.linspace(0.0, 1.0, bins + 1)
    ece = 0.0
    for idx in range(bins):
        if idx == bins - 1:
            bin_mask = (confidences_arr >= edges[idx]) & (confidences_arr <= edges[idx + 1])
        else:
            bin_mask = (confidences_arr >= edges[idx]) & (confidences_arr < edges[idx + 1])
        if not np.any(bin_mask):
            continue
        ece += float(np.mean(bin_mask)) * abs(float(np.mean(accuracies_arr[bin_mask])) - float(np.mean(confidences_arr[bin_mask])))
    return safe_float(ece), safe_float(np.mean(briers))


def ordinal_metrics(
    y_true: Iterable[Any],
    y_pred: Iterable[Any],
    y_prob: Iterable[Any] | None = None,
) -> dict[str, float | None]:
    true, pred = numeric_pair(y_true, y_pred)
    out = {
        "QWK": quadratic_weighted_kappa(true, pred),
        "Ordinal MAE": safe_float(np.mean(np.abs(pred - true))) if true.size else None,
        "Macro-F1": macro_f1(true, pred),
        "ECE": None,
        "Brier Score": None,
    }
    if y_prob is not None:
        out["ECE"], out["Brier Score"] = multiclass_ece_and_brier(true, y_prob)
    return out


def compute_metrics(frame: pd.DataFrame, task_type: str) -> dict[str, float | None]:
    if task_type == "severity_regression":
        return regression_metrics(frame["y_true"], frame["y_pred"])
    if task_type == "binary_classification":
        y_score = frame["y_score"] if "y_score" in frame else None
        return classification_metrics(frame["y_true"], frame["y_pred"], y_score)
    if task_type == "ordinal_prediction":
        y_prob = frame["y_prob"] if "y_prob" in frame else None
        return ordinal_metrics(frame["y_true"], frame["y_pred"], y_prob)
    raise ValueError(f"unknown task_type: {task_type}")


def bootstrap_ci(
    frame: pd.DataFrame,
    task_type: str,
    metric: str,
    resamples: int,
    seed: int,
    unit_column: str = "subject_id",
) -> tuple[float | None, float | None]:
    if resamples <= 0:
        return None, None
    rng = np.random.default_rng(seed)
    if unit_column in frame.columns:
        unit_series = frame[unit_column].astype(str)
        units = np.asarray(sorted(unit_series.dropna().unique()))
        if units.size == 0:
            return None, None
        grouped_indices = {unit: np.flatnonzero(unit_series.to_numpy() == unit) for unit in units}
        values: list[float] = []
        for _ in range(resamples):
            sample_units = rng.choice(units, size=units.size, replace=True)
            sample_indices = np.concatenate([grouped_indices[unit] for unit in sample_units])
            sample = frame.iloc[sample_indices]
            value = compute_metrics(sample, task_type).get(metric)
            if value is not None:
                values.append(float(value))
    else:
        if frame.empty:
            return None, None
        values = []
        for _ in range(resamples):
            sample = frame.iloc[rng.integers(0, len(frame), size=len(frame))]
            value = compute_metrics(sample, task_type).get(metric)
            if value is not None:
                values.append(float(value))
    if not values:
        return None, None
    return safe_float(np.percentile(values, 2.5)), safe_float(np.percentile(values, 97.5))


def metric_records(frame: pd.DataFrame, bootstrap_resamples: int, seed: int) -> tuple[pd.DataFrame, pd.DataFrame]:
    required = {"y_true", "y_pred"}
    missing = required - set(frame.columns)
    if missing:
        raise ValueError(f"prediction file missing columns: {', '.join(sorted(missing))}")
    if "task_type" not in frame.columns:
        raise ValueError("prediction file must include task_type")

    seed_group_cols = [
        column
        for column in ["run_id", "dataset", "modality", "task", "model", "seed", "task_type"]
        if column in frame.columns
    ]
    baseline_group_cols = [
        column
        for column in ["run_id", "dataset", "modality", "task", "model", "task_type"]
        if column in frame.columns
    ]
    per_seed_rows: list[dict[str, Any]] = []
    for key, group in frame.groupby(seed_group_cols, dropna=False):
        if not isinstance(key, tuple):
            key = (key,)
        meta = dict(zip(seed_group_cols, key, strict=True))
        task_type = str(meta["task_type"])
        metrics = compute_metrics(group, task_type)
        for metric, value in metrics.items():
            ci_low, ci_high = bootstrap_ci(group, task_type, metric, bootstrap_resamples, seed)
            per_seed_rows.append(
                {
                    **meta,
                    "metric": metric,
                    "value": value,
                    "ci95_low": ci_low,
                    "ci95_high": ci_high,
                    "sample_count": int(len(group)),
                }
            )

    per_seed = pd.DataFrame(per_seed_rows)
    summary_rows: list[dict[str, Any]] = []
    grouped_rows: dict[tuple[Any, ...], list[dict[str, Any]]] = defaultdict(list)
    for _, row in per_seed.iterrows():
        key = tuple(row[column] for column in baseline_group_cols) + (row["metric"],)
        value = safe_float(row["value"])
        if value is not None:
            grouped_rows[key].append(row.to_dict())
    for key, rows in sorted(grouped_rows.items()):
        meta_values = key[: len(baseline_group_cols)]
        metric = key[-1]
        arr = np.asarray([float(row["value"]) for row in rows], dtype=np.float64)
        ci_low_values = [safe_float(row.get("ci95_low")) for row in rows]
        ci_high_values = [safe_float(row.get("ci95_high")) for row in rows]
        sample_counts = [int(row.get("sample_count") or 0) for row in rows]
        summary_rows.append(
            {
                **dict(zip(baseline_group_cols, meta_values, strict=True)),
                "metric": metric,
                "mean": safe_float(np.mean(arr)),
                "std": safe_float(np.std(arr, ddof=0)),
                "ci95_low": safe_float(np.mean([v for v in ci_low_values if v is not None]))
                if any(v is not None for v in ci_low_values)
                else None,
                "ci95_high": safe_float(np.mean([v for v in ci_high_values if v is not None]))
                if any(v is not None for v in ci_high_values)
                else None,
                "seed_count": int(arr.size),
                "sample_count_mean": safe_float(np.mean(sample_counts)) if sample_counts else None,
            }
        )
    return per_seed, pd.DataFrame(summary_rows)


def self_test() -> None:
    regression = regression_metrics([1, 2, 3], [1, 2, 3])
    assert abs(regression["CCC"] - 1.0) < 1e-12
    assert abs(regression["Spearman"] - 1.0) < 1e-12
    classification = classification_metrics([0, 0, 1, 1], [0, 1, 1, 1], [0.1, 0.6, 0.8, 0.7])
    assert classification["Macro-F1"] is not None
    assert classification["AUROC"] is not None
    ordinal = ordinal_metrics([0, 1, 2], [0, 1, 2], ['[0.9,0.1,0.0]', '[0.1,0.8,0.1]', '[0.0,0.2,0.8]'])
    assert abs(ordinal["QWK"] - 1.0) < 1e-12
    print("phase2_metrics self-test passed")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--predictions", type=Path)
    parser.add_argument("--out-dir", type=Path)
    parser.add_argument("--bootstrap-resamples", type=int, default=1000)
    parser.add_argument("--seed", type=int, default=20260726)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        self_test()
        return
    if args.predictions is None or args.out_dir is None:
        raise SystemExit("--predictions and --out-dir are required unless --self-test is used")
    frame = pd.read_csv(args.predictions)
    per_seed, summary = metric_records(frame, args.bootstrap_resamples, args.seed)
    args.out_dir.mkdir(parents=True, exist_ok=True)
    per_seed.to_csv(args.out_dir / "phase2_metrics_by_seed.csv", index=False)
    summary.to_csv(args.out_dir / "phase2_metric_summary.csv", index=False)
    print(f"Wrote {args.out_dir / 'phase2_metrics_by_seed.csv'}")
    print(f"Wrote {args.out_dir / 'phase2_metric_summary.csv'}")


if __name__ == "__main__":
    main()
