#!/usr/bin/env python3
"""Run MV20 criterion-overlap deletion stress test.

MV20 is a bounded intervention diagnostic, not model development. It asks
whether CMDC question-position units whose frozen multilingual embeddings are
most semantically similar to PHQ criterion paraphrases contribute more apparent
predictive performance than matched random non-high-overlap units.

Tracked artifacts contain only aggregate contracts, metrics, and gates. Row
predictions remain local-only and are ignored by Git.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import re
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
from sklearn.model_selection import KFold
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from phase2_metrics import compute_metrics, metric_records
import phase5_run_mv17a_multilingual_feature_contract as mv17a


ROOT = Path(__file__).resolve().parents[1]
MANIFEST_DIR = ROOT / "datasets" / "manifests"
SPLIT_PATH = ROOT / "datasets" / "splits" / "phase2_subject_splits.csv"
DEFAULT_FEATURE_ROOT = ROOT / "analysis" / "phase2_baselines" / "mv17_multilingual_text_features"
DEFAULT_OUT_DIR = ROOT / "analysis" / "phase5_minimal_validation" / "p5_mv20_criterion_overlap_stress"

SEEDS = [0, 1, 2, 3, 4]
THRESHOLDS = [0.10, 0.20, 0.30]
PRIMARY_THRESHOLD = 0.20
FEATURE_PREFIX = "bge_"
RIDGE_ALPHA_GRID = [0.1, 1.0, 10.0, 100.0, 1000.0]
LOGISTIC_C = 1.0
TRACKED_FILES = {
    "artifact_hygiene_audit.json",
    "criterion_effect_summary.csv",
    "criterion_item_contract.csv",
    "encoder_contract.csv",
    "feasibility_audit.csv",
    "intervention_coverage_summary.csv",
    "intervention_ladder_contract.csv",
    "local_artifact_manifest.csv",
    "metric_summary.csv",
    "metrics_by_seed.csv",
    "method_source_refs.csv",
    "overlap_position_summary.csv",
    "pass_fail_gate_results.csv",
    "protocol_unit_contract.csv",
    "random_deletion_contract.csv",
    "report.md",
    "run_summary.json",
}


@dataclass(frozen=True)
class TargetSpec:
    target: str
    target_tag: str
    task: str
    task_type: str
    protocol_id: str
    estimator: str
    primary_metric: str
    primary_claim_role: str


TARGETS = [
    TargetSpec(
        target="phq9_total",
        target_tag="phq9",
        task="PHQ-9 regression",
        task_type="severity_regression",
        protocol_id="cmdc_phq9_subject_cv",
        estimator="ridge",
        primary_metric="MAE",
        primary_claim_role="primary",
    ),
    TargetSpec(
        target="binary_label",
        target_tag="binary",
        task="MDD classification",
        task_type="binary_classification",
        protocol_id="cmdc_binary_subject_cv",
        estimator="logistic",
        primary_metric="Macro-F1",
        primary_claim_role="supporting",
    ),
]


PHQ_CRITERION_PARAPHRASES = [
    ("PHQ01", "C02", "兴趣或愉快感降低; little interest or pleasure in activities"),
    ("PHQ02", "C01", "情绪低落、沮丧或无望; feeling down, depressed, or hopeless"),
    ("PHQ03", "C03", "睡眠困难或睡眠过多; insomnia or hypersomnia"),
    ("PHQ04", "C04", "疲倦或精力不足; tiredness or low energy"),
    ("PHQ05", "C05", "食欲差或进食过多; poor appetite or overeating"),
    ("PHQ06", "C06", "自责、失败感或让自己和家人失望; guilt, failure, or self-blame"),
    ("PHQ07", "C07", "注意力难以集中; trouble concentrating"),
    ("PHQ08", "C08", "动作或说话变慢，或坐立不安; psychomotor slowing or restlessness"),
    ("PHQ09", "C09", "自伤或死亡想法; self-harm or thoughts of death"),
]


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT))
    except ValueError:
        return path.name


def natural_key(value: Any) -> list[Any]:
    return [int(part) if part.isdigit() else part for part in re.split(r"(\d+)", str(value))]


def bool_series(series: pd.Series) -> pd.Series:
    if pd.api.types.is_bool_dtype(series):
        return series.fillna(False)
    return series.astype(str).str.strip().str.lower().isin({"true", "1", "yes", "y"})


def safe_float(value: Any) -> float | None:
    try:
        out = float(value)
    except (TypeError, ValueError):
        return None
    return out if math.isfinite(out) else None


def clean_tracked_outputs(out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    for name in TRACKED_FILES:
        path = out_dir / name
        if path.exists():
            path.unlink()


def encoder_specs(names: list[str]) -> list[mv17a.EncoderSpec]:
    return [mv17a.ENCODER_SPECS[name] for name in names]


def feature_cache_path(feature_root: Path, encoder: mv17a.EncoderSpec, dataset: str) -> Path:
    return feature_root / encoder.slug / "cmdc_pdch_text_encoder_mlp" / f"{dataset}_bge_segment_embeddings.csv"


def feature_columns(frame: pd.DataFrame) -> list[str]:
    cols = [
        column
        for column in frame.columns
        if column.startswith(FEATURE_PREFIX) and pd.api.types.is_numeric_dtype(frame[column])
    ]
    if not cols:
        raise ValueError("segment embedding cache has no numeric feature columns")
    return sorted(cols, key=natural_key)


def load_segment_embeddings(path: Path, expected_dimension: int) -> tuple[pd.DataFrame, list[str]]:
    if not path.exists():
        raise FileNotFoundError(f"required local segment embedding cache is missing: {rel(path)}")
    frame = pd.read_csv(path)
    required = {"subject_id", "segment_key", "segment_id", "token_count", "chunk_count", "empty_text"}
    missing = required - set(frame.columns)
    if missing:
        raise ValueError(f"segment embedding cache missing columns: {', '.join(sorted(missing))}")
    frame["subject_id"] = frame["subject_id"].astype(str)
    frame["segment_id"] = frame["segment_id"].astype(str)
    cols = feature_columns(frame)
    if len(cols) != expected_dimension:
        raise ValueError(f"{rel(path)} has {len(cols)} feature columns, expected {expected_dimension}")
    frame = frame[["subject_id", "segment_key", "segment_id", "token_count", "chunk_count", "empty_text", *cols]].copy()
    if frame.duplicated(["subject_id", "segment_key"]).any():
        raise ValueError("segment embedding cache has duplicate subject/segment keys")
    return frame.sort_values(["subject_id", "segment_id"], key=lambda s: s.map(lambda x: tuple(natural_key(x)))).reset_index(drop=True), cols


def criterion_contract_rows() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for item_code, construct_id, text in PHQ_CRITERION_PARAPHRASES:
        rows.append(
            {
                "scale": "PHQ-9",
                "item_code": item_code,
                "construct_id": construct_id,
                "criterion_text_policy": "bilingual_symptom_paraphrase_no_scale_verbatim",
                "criterion_text_sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
                "criterion_text_char_count": int(len(text)),
            }
        )
    return rows


def embed_criterion_items(
    encoder: mv17a.EncoderSpec,
    *,
    device_name: str,
    allow_download: bool,
) -> np.ndarray:
    tokenizer, model, device, _hidden = mv17a.load_encoder(
        encoder,
        device_name=device_name,
        allow_download=allow_download,
    )
    embeddings: list[np.ndarray] = []
    try:
        for _item_code, _construct_id, text in PHQ_CRITERION_PARAPHRASES:
            embedding, _chunks, _tokens, empty = mv17a.embed_text(
                text,
                encoder,
                tokenizer,
                model,
                device,
                max_length=encoder.default_max_length,
                chunk_batch_size=encoder.default_chunk_batch_size,
            )
            if empty:
                raise ValueError("criterion paraphrase should never embed as empty text")
            embeddings.append(embedding.astype(np.float64))
    finally:
        del model
    matrix = np.vstack(embeddings).astype(np.float64)
    norms = np.linalg.norm(matrix, axis=1, keepdims=True)
    matrix = matrix / np.maximum(norms, 1.0e-12)
    return matrix


def build_overlap_position_summary(
    segment_embeddings: pd.DataFrame,
    feature_cols: list[str],
    criterion_embeddings: np.ndarray,
    encoder: str,
) -> pd.DataFrame:
    values = segment_embeddings[feature_cols].to_numpy(dtype=np.float64)
    values = values / np.maximum(np.linalg.norm(values, axis=1, keepdims=True), 1.0e-12)
    scores = np.max(values @ criterion_embeddings.T, axis=1)
    scored = segment_embeddings[["segment_id", "token_count", "chunk_count"]].copy()
    scored["criterion_overlap_score"] = scores
    grouped = (
        scored.groupby("segment_id", sort=False)
        .agg(
            observed_units=("segment_id", "size"),
            mean_overlap_score=("criterion_overlap_score", "mean"),
            median_overlap_score=("criterion_overlap_score", "median"),
            min_overlap_score=("criterion_overlap_score", "min"),
            max_overlap_score=("criterion_overlap_score", "max"),
            token_count_mean=("token_count", "mean"),
            token_count_median=("token_count", "median"),
            chunk_count_mean=("chunk_count", "mean"),
        )
        .reset_index()
    )
    grouped = grouped.sort_values(
        ["mean_overlap_score", "segment_id"],
        ascending=[False, True],
        key=lambda s: s.map(lambda x: tuple(natural_key(x))) if s.name == "segment_id" else s,
    ).reset_index(drop=True)
    grouped["encoder"] = encoder
    grouped["rank_desc"] = np.arange(1, len(grouped) + 1)
    for threshold in THRESHOLDS:
        k = threshold_count(len(grouped), threshold)
        grouped[f"high_overlap_top_{int(round(threshold * 100)):02d}pct"] = grouped["rank_desc"] <= k
    ordered_cols = [
        "encoder",
        "segment_id",
        "rank_desc",
        "observed_units",
        "mean_overlap_score",
        "median_overlap_score",
        "min_overlap_score",
        "max_overlap_score",
        "token_count_mean",
        "token_count_median",
        "chunk_count_mean",
        *[f"high_overlap_top_{int(round(threshold * 100)):02d}pct" for threshold in THRESHOLDS],
    ]
    return grouped[ordered_cols]


def threshold_count(total_positions: int, threshold: float) -> int:
    return max(1, int(math.ceil(total_positions * threshold)))


def top_positions(position_summary: pd.DataFrame, threshold: float) -> list[str]:
    k = threshold_count(int(position_summary["segment_id"].nunique()), threshold)
    rows = position_summary.sort_values(["rank_desc", "segment_id"], key=lambda s: s.map(lambda x: tuple(natural_key(x))) if s.name == "segment_id" else s)
    return rows.head(k)["segment_id"].astype(str).tolist()


def random_positions(position_ids: list[str], high_positions: list[str], k: int, seed: int) -> list[str]:
    pool = [position for position in position_ids if position not in set(high_positions)]
    if len(pool) < k:
        raise ValueError("not enough non-high positions for matched random deletion")
    rng = np.random.default_rng(seed)
    selected = rng.choice(np.asarray(pool, dtype=object), size=k, replace=False).tolist()
    return sorted([str(value) for value in selected], key=natural_key)


def intervention_position_sets(
    position_ids: list[str],
    high_positions: list[str],
    *,
    intervention: str,
    random_seed: int | None,
) -> tuple[list[str], list[str]]:
    if intervention == "all_units":
        return sorted(position_ids, key=natural_key), []
    if intervention == "minus_high":
        removed = sorted(high_positions, key=natural_key)
        kept = [position for position in position_ids if position not in set(removed)]
        return sorted(kept, key=natural_key), removed
    if intervention == "high_only":
        kept = sorted(high_positions, key=natural_key)
        removed = [position for position in position_ids if position not in set(kept)]
        return kept, sorted(removed, key=natural_key)
    if intervention == "minus_random":
        if random_seed is None:
            raise ValueError("minus_random requires random_seed")
        removed = random_positions(position_ids, high_positions, len(high_positions), random_seed)
        kept = [position for position in position_ids if position not in set(removed)]
        return sorted(kept, key=natural_key), removed
    raise ValueError(f"unknown intervention: {intervention}")


def average_subject_features(
    segment_embeddings: pd.DataFrame,
    feature_cols: list[str],
    kept_positions: list[str],
    expected_subjects: set[str],
) -> tuple[pd.DataFrame, dict[str, Any]]:
    selected = segment_embeddings[segment_embeddings["segment_id"].astype(str).isin(set(kept_positions))].copy()
    rows: list[dict[str, Any]] = []
    for subject_id, group in selected.groupby("subject_id", sort=False):
        values = group[feature_cols].to_numpy(dtype=np.float64)
        mean_values = np.mean(values, axis=0)
        norm = float(np.linalg.norm(mean_values))
        if norm > 0.0:
            mean_values = mean_values / norm
        rows.append(
            {
                "subject_id": str(subject_id),
                "retained_unit_count": int(len(group)),
                "retained_token_count": int(pd.to_numeric(group["token_count"], errors="coerce").fillna(0).sum()),
                "retained_chunk_count": int(pd.to_numeric(group["chunk_count"], errors="coerce").fillna(0).sum()),
                **{column: float(value) for column, value in zip(feature_cols, mean_values, strict=True)},
            }
        )
    features = pd.DataFrame(rows)
    if not features.empty:
        features = features.sort_values("subject_id", key=lambda s: s.map(lambda x: tuple(natural_key(x)))).reset_index(drop=True)
    observed_subjects = set(features["subject_id"].astype(str)) if not features.empty else set()
    missing = sorted(expected_subjects - observed_subjects, key=natural_key)
    coverage = {
        "feature_subjects": int(len(observed_subjects)),
        "expected_subjects": int(len(expected_subjects)),
        "missing_subjects": int(len(missing)),
        "min_retained_units": int(features["retained_unit_count"].min()) if not features.empty else 0,
        "median_retained_units": float(features["retained_unit_count"].median()) if not features.empty else 0.0,
        "max_retained_units": int(features["retained_unit_count"].max()) if not features.empty else 0,
        "mean_retained_tokens": float(features["retained_token_count"].mean()) if not features.empty else 0.0,
    }
    return features, coverage


def load_protocol_splits(spec: TargetSpec, split_path: Path) -> dict[str, dict[str, list[str]]]:
    splits = pd.read_csv(split_path)
    required = {"dataset", "protocol_id", "target", "fold", "role", "subject_id"}
    missing = required - set(splits.columns)
    if missing:
        raise ValueError(f"split layer missing columns: {', '.join(sorted(missing))}")
    selected = splits[
        (splits["dataset"].astype(str) == "cmdc")
        & (splits["protocol_id"].astype(str) == spec.protocol_id)
        & (splits["target"].astype(str) == spec.target)
    ].copy()
    if selected.empty:
        raise ValueError(f"no split rows for {spec.protocol_id}:{spec.target}")
    folds: dict[str, dict[str, list[str]]] = {}
    for fold, group in selected.groupby("fold", sort=False):
        roles: dict[str, list[str]] = {}
        for role, rows in group.groupby("role", sort=False):
            roles[str(role)] = sorted(rows["subject_id"].astype(str).unique(), key=natural_key)
        train = set(roles.get("train", []))
        validation = set(roles.get("validation", []))
        if train & validation:
            raise ValueError(f"{spec.protocol_id}:{fold} train/validation overlap")
        if not train or not validation:
            raise ValueError(f"{spec.protocol_id}:{fold} has empty train or validation")
        folds[str(fold)] = roles
    return dict(sorted(folds.items(), key=lambda item: natural_key(item[0])))


def split_subjects(folds: dict[str, dict[str, list[str]]]) -> set[str]:
    return {subject for roles in folds.values() for subjects in roles.values() for subject in subjects}


def load_cmdc_labels(spec: TargetSpec, expected_subjects: set[str]) -> pd.DataFrame:
    manifest = pd.read_csv(MANIFEST_DIR / "cmdc_subjects.csv")
    required = {"subject_id", "file_valid", "text_path", spec.target}
    missing = required - set(manifest.columns)
    if missing:
        raise ValueError(f"CMDC manifest missing columns for MV20: {', '.join(sorted(missing))}")
    rows = manifest[
        manifest["subject_id"].astype(str).isin(expected_subjects)
        & bool_series(manifest["file_valid"])
        & manifest["text_path"].notna()
        & manifest[spec.target].notna()
    ].copy()
    labels: list[dict[str, Any]] = []
    for subject_id, group in rows.groupby("subject_id", sort=False):
        values = pd.to_numeric(group[spec.target], errors="raise").dropna().unique()
        if len(values) != 1:
            raise ValueError(f"CMDC subject has inconsistent {spec.target} labels")
        labels.append({"subject_id": str(subject_id), spec.target: float(values[0])})
    frame = pd.DataFrame(labels)
    observed = set(frame["subject_id"].astype(str)) if not frame.empty else set()
    missing_subjects = sorted(expected_subjects - observed, key=natural_key)
    if missing_subjects:
        raise ValueError(f"CMDC split subjects missing usable labels for {spec.target}: {len(missing_subjects)}")
    return frame.sort_values("subject_id", key=lambda s: s.map(lambda x: tuple(natural_key(x)))).reset_index(drop=True)


def ridge_pipeline(alpha: float) -> Pipeline:
    return Pipeline(
        [
            ("imputer", SimpleImputer(strategy="median")),
            ("scaler", StandardScaler()),
            ("ridge", Ridge(alpha=float(alpha))),
        ]
    )


def choose_alpha(x: np.ndarray, y: np.ndarray, seed: int) -> float:
    x_arr = np.asarray(x, dtype=np.float64)
    y_arr = np.asarray(y, dtype=np.float64).reshape(-1)
    if x_arr.shape[0] < 12:
        return 100.0
    n_splits = min(5, max(2, x_arr.shape[0] // 10))
    splitter = KFold(n_splits=n_splits, shuffle=True, random_state=seed)
    best_alpha = RIDGE_ALPHA_GRID[0]
    best_mae = float("inf")
    for alpha in RIDGE_ALPHA_GRID:
        scores: list[float] = []
        for train_idx, dev_idx in splitter.split(x_arr):
            model = ridge_pipeline(alpha)
            model.fit(x_arr[train_idx], y_arr[train_idx])
            pred = model.predict(x_arr[dev_idx])
            scores.append(float(np.mean(np.abs(pred - y_arr[dev_idx]))))
        score = float(np.mean(scores))
        if score < best_mae:
            best_alpha = float(alpha)
            best_mae = score
    return best_alpha


def logistic_pipeline(seed: int) -> Pipeline:
    return Pipeline(
        [
            ("imputer", SimpleImputer(strategy="median")),
            ("scaler", StandardScaler()),
            (
                "logistic",
                LogisticRegression(
                    C=LOGISTIC_C,
                    class_weight="balanced",
                    max_iter=1000,
                    random_state=seed,
                    solver="liblinear",
                ),
            ),
        ]
    )


def train_mean_predictions(train: pd.DataFrame, validation: pd.DataFrame, spec: TargetSpec) -> tuple[np.ndarray, np.ndarray | None]:
    y_train = train[spec.target].to_numpy(dtype=np.float64)
    if spec.task_type == "severity_regression":
        return np.repeat(float(np.mean(y_train)), len(validation)), None
    values, counts = np.unique(y_train.astype(int), return_counts=True)
    majority = int(values[np.argmax(counts)])
    positive_rate = float(np.mean(y_train.astype(int) == 1))
    return np.repeat(majority, len(validation)).astype(int), np.repeat(positive_rate, len(validation))


def fit_predict(
    train: pd.DataFrame,
    validation: pd.DataFrame,
    feature_cols: list[str],
    spec: TargetSpec,
    seed: int,
) -> tuple[np.ndarray, np.ndarray | None, dict[str, Any]]:
    if spec.estimator == "ridge":
        alpha = choose_alpha(train[feature_cols].to_numpy(dtype=np.float64), train[spec.target].to_numpy(dtype=np.float64), seed)
        model = ridge_pipeline(alpha)
        y_train = train[spec.target].to_numpy(dtype=np.float64)
        model.fit(train[feature_cols], y_train)
        raw_pred = np.asarray(model.predict(validation[feature_cols]), dtype=np.float64)
        low = float(np.min(y_train))
        high = float(np.max(y_train))
        pred = np.clip(raw_pred, low, high)
        return pred, None, {"selected_alpha": float(alpha), "clip_low": low, "clip_high": high}
    if spec.estimator == "logistic":
        model = logistic_pipeline(seed)
        model.fit(train[feature_cols], train[spec.target].astype(int))
        pred = model.predict(validation[feature_cols]).astype(int)
        score = model.predict_proba(validation[feature_cols])[:, 1]
        return pred, score, {"logistic_c": float(LOGISTIC_C)}
    raise ValueError(f"unsupported estimator: {spec.estimator}")


def evaluate_intervention(
    features: pd.DataFrame,
    labels: pd.DataFrame,
    folds: dict[str, dict[str, list[str]]],
    feature_cols: list[str],
    spec: TargetSpec,
    *,
    encoder: str,
    intervention: str,
    threshold_pct: int,
    retained_position_count: int,
    removed_position_count: int,
    seeds: list[int] | None = None,
) -> list[dict[str, Any]]:
    table = labels.merge(features, on="subject_id", how="inner", validate="one_to_one")
    expected = split_subjects(folds)
    observed = set(table["subject_id"].astype(str))
    if expected - observed:
        raise ValueError(f"{encoder}:{spec.target}:{intervention}: intervention features missing split subjects")
    table_by_subject = table.set_index("subject_id", drop=False)
    predictions: list[dict[str, Any]] = []
    eval_seeds = SEEDS if seeds is None else seeds
    for seed in eval_seeds:
        for fold, roles in folds.items():
            train = table_by_subject.loc[roles["train"]].reset_index(drop=True)
            validation = table_by_subject.loc[roles["validation"]].reset_index(drop=True)
            if intervention == "train_mean_floor":
                pred, score = train_mean_predictions(train, validation, spec)
                fit_meta = {"floor_type": "train_mean" if spec.task_type == "severity_regression" else "train_majority"}
            else:
                pred, score, fit_meta = fit_predict(train, validation, feature_cols, spec, seed)
            for idx, row in validation.iterrows():
                predictions.append(
                    {
                        "run_id": run_id(encoder, spec.target_tag, intervention, threshold_pct),
                        "dataset": "CMDC",
                        "modality": "Text",
                        "task": spec.task,
                        "model": f"{encoder}_{intervention}_ridge_or_logistic",
                        "seed": int(seed),
                        "task_type": spec.task_type,
                        "target": spec.target,
                        "encoder": encoder,
                        "intervention": intervention,
                        "threshold_pct": int(threshold_pct),
                        "primary_claim_role": spec.primary_claim_role,
                        "fold": fold,
                        "subject_id": str(row["subject_id"]),
                        "retained_position_count": int(retained_position_count),
                        "removed_position_count": int(removed_position_count),
                        "retained_unit_count": int(row.get("retained_unit_count", 0)),
                        "retained_token_count": int(row.get("retained_token_count", 0)),
                        "y_true": float(row[spec.target]) if spec.task_type == "severity_regression" else int(row[spec.target]),
                        "y_pred": float(pred[idx]) if spec.task_type == "severity_regression" else int(pred[idx]),
                        "y_score": "" if score is None else float(score[idx]),
                        **fit_meta,
                    }
                )
    return predictions


def run_id(encoder: str, target_tag: str, intervention: str, threshold_pct: int) -> str:
    return f"P5_MV20_{encoder}_{target_tag}_{intervention}_p{threshold_pct:02d}"


def metric_value(frame: pd.DataFrame, spec: TargetSpec) -> float | None:
    value = compute_metrics(frame, spec.task_type).get(spec.primary_metric)
    return safe_float(value)


def metric_loss(value: float, baseline: float, spec: TargetSpec) -> float:
    if spec.task_type == "severity_regression":
        return float(value - baseline)
    return float(baseline - value)


def high_vs_random_excess(high_value: float, random_value: float, spec: TargetSpec) -> float:
    if spec.task_type == "severity_regression":
        return float(high_value - random_value)
    return float(random_value - high_value)


def subset_predictions(predictions: pd.DataFrame, encoder: str, target: str, intervention: str, threshold_pct: int) -> pd.DataFrame:
    return predictions[
        (predictions["encoder"].astype(str) == encoder)
        & (predictions["target"].astype(str) == target)
        & (predictions["intervention"].astype(str) == intervention)
        & (predictions["threshold_pct"].astype(int) == int(threshold_pct))
    ].copy()


def paired_bootstrap_excess(
    high: pd.DataFrame,
    random: pd.DataFrame,
    spec: TargetSpec,
    *,
    resamples: int,
    seed: int,
) -> tuple[float | None, float | None]:
    merge_cols = ["subject_id", "seed", "fold"]
    left = high[merge_cols + ["y_true", "y_pred", "y_score"]].copy()
    right = random[merge_cols + ["y_pred", "y_score"]].copy()
    merged = left.merge(right, on=merge_cols, how="inner", suffixes=("_high", "_random"), validate="one_to_one")
    if merged.empty:
        return None, None
    units = np.asarray(sorted(merged["subject_id"].astype(str).unique(), key=natural_key))
    grouped = {unit: merged.index[merged["subject_id"].astype(str) == unit].to_numpy() for unit in units}
    rng = np.random.default_rng(seed)
    values: list[float] = []
    for _ in range(resamples):
        sampled_units = rng.choice(units, size=len(units), replace=True)
        sample_idx = np.concatenate([grouped[unit] for unit in sampled_units])
        sample = merged.loc[sample_idx]
        high_frame = pd.DataFrame(
            {
                "y_true": sample["y_true"],
                "y_pred": sample["y_pred_high"],
                "y_score": sample["y_score_high"],
                "task_type": spec.task_type,
            }
        )
        random_frame = pd.DataFrame(
            {
                "y_true": sample["y_true"],
                "y_pred": sample["y_pred_random"],
                "y_score": sample["y_score_random"],
                "task_type": spec.task_type,
            }
        )
        high_metric = metric_value(high_frame, spec)
        random_metric = metric_value(random_frame, spec)
        if high_metric is not None and random_metric is not None:
            values.append(high_vs_random_excess(high_metric, random_metric, spec))
    if not values:
        return None, None
    return safe_float(np.percentile(values, 2.5)), safe_float(np.percentile(values, 97.5))


def build_effect_summary(
    predictions: pd.DataFrame,
    coverage: pd.DataFrame,
    *,
    bootstrap_resamples: int,
) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for encoder in sorted(predictions["encoder"].astype(str).unique()):
        for spec in TARGETS:
            all_frame = subset_predictions(predictions, encoder, spec.target, "all_units", 0)
            floor_frame = subset_predictions(predictions, encoder, spec.target, "train_mean_floor", 0)
            all_metric = metric_value(all_frame, spec)
            floor_metric = metric_value(floor_frame, spec)
            for threshold in THRESHOLDS:
                threshold_pct = int(round(threshold * 100))
                high_frame = subset_predictions(predictions, encoder, spec.target, "minus_high", threshold_pct)
                random_frame = subset_predictions(predictions, encoder, spec.target, "minus_random", threshold_pct)
                high_only_frame = subset_predictions(predictions, encoder, spec.target, "high_only", threshold_pct)
                if high_frame.empty or random_frame.empty or high_only_frame.empty or all_metric is None or floor_metric is None:
                    continue
                high_metric = metric_value(high_frame, spec)
                random_metric = metric_value(random_frame, spec)
                high_only_metric = metric_value(high_only_frame, spec)
                if high_metric is None or random_metric is None or high_only_metric is None:
                    continue
                high_loss = metric_loss(high_metric, all_metric, spec)
                random_loss = metric_loss(random_metric, all_metric, spec)
                high_only_loss = metric_loss(high_only_metric, all_metric, spec)
                excess = high_loss - random_loss
                ci_low, ci_high = paired_bootstrap_excess(
                    high_frame,
                    random_frame,
                    spec,
                    resamples=bootstrap_resamples,
                    seed=20260822 + threshold_pct,
                )
                coverage_row = coverage[
                    (coverage["encoder"].astype(str) == encoder)
                    & (coverage["target"].astype(str) == spec.target)
                    & (coverage["intervention"].astype(str) == "high_only")
                    & (coverage["threshold_pct"].astype(int) == threshold_pct)
                ]
                retained_position_fraction = (
                    float(coverage_row.iloc[0]["retained_position_fraction"]) if not coverage_row.empty else float("nan")
                )
                denominator = metric_loss(floor_metric, all_metric, spec)
                if denominator > 0:
                    high_only_power_fraction = 1.0 - (high_only_loss / denominator)
                else:
                    high_only_power_fraction = None
                high_only_beats_floor = high_only_power_fraction is not None and high_only_power_fraction > 0.0
                high_only_disproportionate = (
                    high_only_power_fraction is not None
                    and high_only_power_fraction > retained_position_fraction
                    and high_only_beats_floor
                )
                if ci_low is not None and ci_low > 0.0 and high_only_disproportionate:
                    support_status = "mechanism_supported"
                elif ci_low is not None and ci_low > 0.0:
                    support_status = "partial_deletion_only"
                else:
                    support_status = "no_excess_criterion_overlap_evidence"
                rows.append(
                    {
                        "encoder": encoder,
                        "dataset": "CMDC",
                        "target": spec.target,
                        "target_role": spec.primary_claim_role,
                        "threshold_pct": threshold_pct,
                        "primary_threshold": threshold == PRIMARY_THRESHOLD,
                        "primary_metric": spec.primary_metric,
                        "all_metric": all_metric,
                        "minus_high_metric": high_metric,
                        "minus_random_metric": random_metric,
                        "high_only_metric": high_only_metric,
                        "train_floor_metric": floor_metric,
                        "minus_high_loss_vs_all": high_loss,
                        "minus_random_loss_vs_all": random_loss,
                        "criterion_excess_loss_vs_random": excess,
                        "criterion_excess_loss_ci95_low": ci_low,
                        "criterion_excess_loss_ci95_high": ci_high,
                        "high_only_power_fraction_vs_floor": high_only_power_fraction,
                        "high_only_retained_position_fraction": retained_position_fraction,
                        "high_only_disproportionate": bool(high_only_disproportionate),
                        "support_status": support_status,
                    }
                )
    return pd.DataFrame(rows)


def build_gate_results(effect_summary: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    primary = effect_summary[
        (effect_summary["encoder"] == "bge_m3")
        & (effect_summary["target"] == "phq9_total")
        & (effect_summary["threshold_pct"] == int(round(PRIMARY_THRESHOLD * 100)))
    ]
    sensitivity = effect_summary[
        (effect_summary["encoder"] == "multilingual_e5_base")
        & (effect_summary["target"] == "phq9_total")
        & (effect_summary["threshold_pct"] == int(round(PRIMARY_THRESHOLD * 100)))
    ]
    for gate_id, frame in [
        ("primary_bge_m3_cmdc_phq9_top20", primary),
        ("sensitivity_multilingual_e5_cmdc_phq9_top20", sensitivity),
    ]:
        if frame.empty:
            status = "blocked_missing_effect_row"
            pass_rule_met = False
            row = {}
        else:
            row = frame.iloc[0].to_dict()
            status = str(row["support_status"])
            pass_rule_met = status == "mechanism_supported"
        rows.append(
            {
                "gate_id": gate_id,
                "gate_scope": "criterion-overlap deletion exceeds matched random deletion and high-only retains disproportionate power",
                "gate_status": status,
                "pass_rule_met": bool(pass_rule_met),
                "criterion_excess_loss_vs_random": row.get("criterion_excess_loss_vs_random"),
                "criterion_excess_loss_ci95_low": row.get("criterion_excess_loss_ci95_low"),
                "criterion_excess_loss_ci95_high": row.get("criterion_excess_loss_ci95_high"),
                "high_only_power_fraction_vs_floor": row.get("high_only_power_fraction_vs_floor"),
                "high_only_retained_position_fraction": row.get("high_only_retained_position_fraction"),
            }
        )
    bge_status = rows[0]["gate_status"]
    e5_status = rows[1]["gate_status"]
    bge_pass = bool(rows[0]["pass_rule_met"])
    e5_pass = bool(rows[1]["pass_rule_met"])
    if bge_pass and e5_pass:
        pass_rule_status = "complete_mv20_criterion_overlap_supported_encoder_stable"
    elif bge_pass != e5_pass:
        pass_rule_status = "complete_mv20_criterion_overlap_representation_dependent"
    elif str(bge_status) == "partial_deletion_only" or str(e5_status) == "partial_deletion_only":
        pass_rule_status = "complete_mv20_partial_deletion_without_high_only_gate"
    else:
        pass_rule_status = "complete_mv20_no_primary_criterion_overlap_excess"
    verdict = {
        "pass_rule_status": pass_rule_status,
        "pass_rule_met": bool(bge_pass),
        "primary_gate_status": bge_status,
        "sensitivity_gate_status": e5_status,
        "stop_rule": "freeze_experiments_after_mv20_regardless_of_result",
    }
    if not primary.empty:
        row = primary.iloc[0]
        verdict.update(
            {
                "primary_encoder": "bge_m3",
                "primary_dataset": "CMDC",
                "primary_target": "phq9_total",
                "primary_threshold_pct": 20,
                "primary_metric": row["primary_metric"],
                "primary_all_metric": safe_float(row["all_metric"]),
                "primary_minus_high_metric": safe_float(row["minus_high_metric"]),
                "primary_minus_random_metric": safe_float(row["minus_random_metric"]),
                "primary_high_only_metric": safe_float(row["high_only_metric"]),
                "primary_criterion_excess_loss_vs_random": safe_float(row["criterion_excess_loss_vs_random"]),
                "primary_criterion_excess_loss_ci95_low": safe_float(row["criterion_excess_loss_ci95_low"]),
                "primary_criterion_excess_loss_ci95_high": safe_float(row["criterion_excess_loss_ci95_high"]),
                "primary_high_only_power_fraction_vs_floor": safe_float(row["high_only_power_fraction_vs_floor"]),
            }
        )
    return pd.DataFrame(rows), verdict


def protocol_unit_contract_rows(cmdc_manifest: pd.DataFrame, pdch_manifest: pd.DataFrame, edaic_manifest: pd.DataFrame) -> list[dict[str, Any]]:
    cmdc_segments = int(cmdc_manifest["segment_id"].astype(str).nunique())
    pdch_segments = int(pdch_manifest["segment_id"].astype(str).nunique())
    edaic_speaker_non_null = int(edaic_manifest["speaker"].notna().sum()) if "speaker" in edaic_manifest.columns else 0
    return [
        {
            "dataset": "CMDC",
            "mv20_role": "primary",
            "unit_level": "question_position_segment_id",
            "status": "included_primary_segment_position_units",
            "unit_positions": cmdc_segments,
            "rows": int(len(cmdc_manifest)),
            "subjects": int(cmdc_manifest["subject_id"].astype(str).nunique()),
            "rationale": "CMDC exposes stable Q1-Q12 clinical-interview question-position segments; high-overlap is ranked at the segment-position level, not by outcome.",
        },
        {
            "dataset": "PDCH",
            "mv20_role": "candidate_sensitivity",
            "unit_level": "consultation_segment_id",
            "status": "excluded_no_clean_question_level_units",
            "unit_positions": pdch_segments,
            "rows": int(len(pdch_manifest)),
            "subjects": int(pdch_manifest["subject_id"].astype(str).nunique()),
            "rationale": "PDCH has only coarse 1-3 face-to-face consultation segments per subject, so top-percent deletion would remove broad transcript chunks rather than question/protocol units.",
        },
        {
            "dataset": "E-DAIC",
            "mv20_role": "candidate_secondary",
            "unit_level": "transcript_turn_without_speaker_role",
            "status": "excluded_no_true_prompt_or_speaker_units",
            "unit_positions": int(edaic_manifest["segment_id"].astype(str).nunique()),
            "rows": int(len(edaic_manifest)),
            "subjects": int(edaic_manifest["subject_id"].astype(str).nunique()),
            "rationale": f"E-DAIC manifest speaker rows are {edaic_speaker_non_null}; MV20 does not use position proxies as prompt units.",
        },
    ]


def feasibility_rows(cmdc_manifest: pd.DataFrame, segment_embeddings: pd.DataFrame) -> list[dict[str, Any]]:
    valid_cmdc = cmdc_manifest[bool_series(cmdc_manifest["file_valid"]) & cmdc_manifest["text_path"].notna()]
    return [
        {
            "dataset": "CMDC",
            "check": "stable_question_positions",
            "status": "passed",
            "count_1_name": "question_positions",
            "count_1_value": int(cmdc_manifest["segment_id"].astype(str).nunique()),
            "count_2_name": "subjects_with_all_positions",
            "count_2_value": int((cmdc_manifest.groupby("subject_id")["segment_id"].nunique() == 12).sum()),
        },
        {
            "dataset": "CMDC",
            "check": "local_segment_embedding_cache",
            "status": "passed",
            "count_1_name": "embedding_rows",
            "count_1_value": int(len(segment_embeddings)),
            "count_2_name": "valid_manifest_rows",
            "count_2_value": int(len(valid_cmdc)),
        },
        {
            "dataset": "CMDC",
            "check": "outcome_guided_selection",
            "status": "avoided",
            "count_1_name": "labels_used_for_overlap_ranking",
            "count_1_value": 0,
            "count_2_name": "prediction_metrics_used_for_threshold_choice",
            "count_2_value": 0,
        },
    ]


def intervention_ladder_rows() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for threshold in THRESHOLDS:
        threshold_pct = int(round(threshold * 100))
        rows.extend(
            [
                {
                    "threshold_pct": threshold_pct,
                    "primary_threshold": threshold == PRIMARY_THRESHOLD,
                    "intervention": "minus_high",
                    "definition": "delete top criterion-overlap question-position units",
                    "selection_uses_labels": False,
                    "selection_uses_prediction_performance": False,
                },
                {
                    "threshold_pct": threshold_pct,
                    "primary_threshold": threshold == PRIMARY_THRESHOLD,
                    "intervention": "minus_random",
                    "definition": "delete equal-count random non-high-overlap question-position units",
                    "selection_uses_labels": False,
                    "selection_uses_prediction_performance": False,
                },
                {
                    "threshold_pct": threshold_pct,
                    "primary_threshold": threshold == PRIMARY_THRESHOLD,
                    "intervention": "high_only",
                    "definition": "retain only top criterion-overlap question-position units",
                    "selection_uses_labels": False,
                    "selection_uses_prediction_performance": False,
                },
            ]
        )
    rows.append(
        {
            "threshold_pct": 0,
            "primary_threshold": False,
            "intervention": "all_units",
            "definition": "retain all available CMDC question-position units",
            "selection_uses_labels": False,
            "selection_uses_prediction_performance": False,
        }
    )
    return rows


def method_source_rows() -> list[dict[str, str]]:
    return [
        {
            "source_id": "Burdisso2024_DAIC_WOZ_prompts",
            "source_url": "https://aclanthology.org/2024.clinicalnlp-1.8/",
            "mv20_role": "documents fixed therapist-prompt shortcut risk in DAIC-WOZ-style interviews",
        },
        {
            "source_id": "ZhangPoellabauer2025_interviewer_bias",
            "source_url": "https://aclanthology.org/2025.findings-emnlp.650/",
            "mv20_role": "documents interviewer-bias mitigation motivation without turning MV20 into a new adversarial model",
        },
        {
            "source_id": "Mirror2025_criterion_contamination",
            "source_url": "https://arxiv.org/abs/2508.05830",
            "mv20_role": "motivates target-criterion semantic-overlap contamination as the tested mechanism",
        },
        {
            "source_id": "BGE_M3",
            "source_url": "https://huggingface.co/BAAI/bge-m3",
            "mv20_role": "primary encoder contract inherited from MV17a",
        },
        {
            "source_id": "multilingual_E5_base",
            "source_url": "https://huggingface.co/intfloat/multilingual-e5-base",
            "mv20_role": "sensitivity encoder contract inherited from MV17a",
        },
    ]


def write_encoder_contract(out_dir: Path, encoders: list[mv17a.EncoderSpec]) -> None:
    rows = []
    for encoder in encoders:
        rows.append(
            {
                "encoder": encoder.slug,
                "model_name": encoder.model_name,
                "pooling": encoder.pooling,
                "input_prefix_used": bool(encoder.input_prefix),
                "max_length": int(encoder.default_max_length),
                "expected_dimension": int(encoder.expected_dimension),
                "mv20_role": "primary" if encoder.slug == "bge_m3" else "sensitivity",
                "contract_source": "inherited_from_mv17a_multilingual_feature_contract",
            }
        )
    pd.DataFrame(rows).to_csv(out_dir / "encoder_contract.csv", index=False)


def write_local_artifact_manifest(out_dir: Path, feature_root: Path, encoders: list[mv17a.EncoderSpec]) -> None:
    rows = [
        {
            "artifact": "analysis/phase5_minimal_validation/p5_mv20_criterion_overlap_stress/mv20_predictions.csv",
            "artifact_class": "local_only_row_predictions",
            "version_policy": "ignored_by_git_do_not_commit",
        }
    ]
    for encoder in encoders:
        rows.append(
            {
                "artifact": rel(feature_cache_path(feature_root, encoder, "cmdc")),
                "artifact_class": "local_only_segment_embedding_cache_read_only",
                "version_policy": "ignored_by_git_do_not_commit",
            }
        )
    pd.DataFrame(rows).to_csv(out_dir / "local_artifact_manifest.csv", index=False)


def build_hygiene(out_dir: Path) -> dict[str, Any]:
    forbidden = [
        (re.compile(r"\bsubject_id\b", re.IGNORECASE), "explicit row-key column"),
        (re.compile(r"\btext_path\b|\baudio_path\b|\bvideo_path\b|\bgait_path\b", re.IGNORECASE), "source path column"),
        (re.compile(r"/root/autodl-tmp/datasets", re.IGNORECASE), "absolute dataset root"),
        (re.compile(r"raw transcript|raw clinical|raw prompt|raw response", re.IGNORECASE), "raw-content wording"),
        (re.compile(r"\b[0-9]{6,}@qq\.com\b|\b[a-z]{2,}[0-9]{6,}\.[0-9]+\b|github_pat_|ghp_", re.IGNORECASE), "credential-like string"),
    ]
    violations: list[dict[str, str]] = []
    checked = 0
    for path in sorted(out_dir.glob("*")):
        if not path.is_file() or path.name not in TRACKED_FILES:
            continue
        checked += 1
        text = path.read_text(encoding="utf-8", errors="ignore")
        for pattern, label in forbidden:
            if pattern.search(text):
                violations.append({"file": rel(path), "violation": label})
    return {
        "audit_id": "P5_MV20_criterion_overlap_stress_hygiene",
        "generated_at": utc_now(),
        "files_checked": int(checked),
        "artifact_hygiene_passed": not violations,
        "violation_count": int(len(violations)),
        "violations": violations,
    }


def write_report(
    out_dir: Path,
    run_summary: dict[str, Any],
    effect_summary: pd.DataFrame,
    gate_results: pd.DataFrame,
) -> None:
    lines = [
        "# P5 MV20 Criterion-Overlap Intervention",
        "",
        f"Generated: `{run_summary['generated_at']}`",
        "",
        "## Scope",
        "",
        "MV20 is a bounded stress test for target-scale semantic overlap. It does not train a new architecture, tune overlap thresholds by outcome, or use E-DAIC position proxies as prompt units.",
        "",
        "## Design",
        "",
        "- Primary dataset: CMDC.",
        "- Primary encoder: BGE-M3.",
        "- Sensitivity encoder: multilingual-E5-base.",
        "- Primary threshold: top 20 percent criterion-overlap question-position units.",
        "- Sensitivity thresholds: top 10 percent and top 30 percent.",
        "- Main contrast: deletion of high-overlap units versus equal-count random non-high-overlap deletion.",
        "- Stop rule: freeze experiments after MV20 regardless of positive, negative, or encoder-dependent result.",
        "",
        "## Feasibility Boundary",
        "",
        "- CMDC is included because it exposes stable Q1-Q12 question-position units.",
        "- PDCH is excluded because its available text units are coarse consultation segments rather than clean question units.",
        "- E-DAIC is excluded because the available transcript contract does not expose true prompt/speaker units.",
        "",
        "## Primary Gate",
        "",
        "| gate | status | excess loss | ci low | ci high | high-only power | retained fraction |",
        "| --- | --- | ---: | ---: | ---: | ---: | ---: |",
    ]
    for _, row in gate_results.iterrows():
        lines.append(
            f"| `{row['gate_id']}` | `{row['gate_status']}` | {fmt(row['criterion_excess_loss_vs_random'])} | {fmt(row['criterion_excess_loss_ci95_low'])} | {fmt(row['criterion_excess_loss_ci95_high'])} | {fmt(row['high_only_power_fraction_vs_floor'])} | {fmt(row['high_only_retained_position_fraction'])} |"
        )
    snapshot = effect_summary[
        (effect_summary["target"] == "phq9_total")
        & (effect_summary["threshold_pct"] == 20)
    ].copy()
    if not snapshot.empty:
        lines.extend(
            [
                "",
                "## Top-20 PHQ Snapshot",
                "",
                "| encoder | all MAE | minus-high MAE | minus-random MAE | high-only MAE | excess loss | status |",
                "| --- | ---: | ---: | ---: | ---: | ---: | --- |",
            ]
        )
        for _, row in snapshot.sort_values("encoder").iterrows():
            lines.append(
                f"| `{row['encoder']}` | {fmt(row['all_metric'])} | {fmt(row['minus_high_metric'])} | {fmt(row['minus_random_metric'])} | {fmt(row['high_only_metric'])} | {fmt(row['criterion_excess_loss_vs_random'])} | `{row['support_status']}` |"
            )
    lines.extend(
        [
            "",
            "## Decision",
            "",
            f"- Status: `{run_summary['verdict']['pass_rule_status']}`.",
            f"- Primary gate: `{run_summary['verdict']['primary_gate_status']}`.",
            f"- Sensitivity gate: `{run_summary['verdict']['sensitivity_gate_status']}`.",
            f"- Artifact hygiene passed: `{run_summary['artifact_hygiene_passed']}`.",
            "",
            "## Output Boundary",
            "",
            "- `mv20_predictions.csv` is local-only and ignored by Git.",
            "- Tracked outputs contain aggregate overlap ranks, contracts, metrics, gates, and hygiene only.",
        ]
    )
    (out_dir / "report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def fmt(value: Any, digits: int = 3) -> str:
    numeric = safe_float(value)
    if numeric is None:
        return "NA"
    return f"{numeric:.{digits}f}"


def run_mv20(args: argparse.Namespace) -> dict[str, Any]:
    if not args.allow_download:
        os.environ.setdefault("HF_HUB_OFFLINE", "1")
        os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")

    out_dir = args.out_dir
    clean_tracked_outputs(out_dir)
    encoders = encoder_specs(args.encoders)

    cmdc_manifest = pd.read_csv(args.manifest_dir / "cmdc_subjects.csv")
    pdch_manifest = pd.read_csv(args.manifest_dir / "pdch_subjects.csv")
    edaic_manifest = pd.read_csv(args.manifest_dir / "edaic_subjects.csv")
    pd.DataFrame(protocol_unit_contract_rows(cmdc_manifest, pdch_manifest, edaic_manifest)).to_csv(
        out_dir / "protocol_unit_contract.csv",
        index=False,
    )
    pd.DataFrame(criterion_contract_rows()).to_csv(out_dir / "criterion_item_contract.csv", index=False)
    pd.DataFrame(intervention_ladder_rows()).to_csv(out_dir / "intervention_ladder_contract.csv", index=False)
    pd.DataFrame(method_source_rows()).to_csv(out_dir / "method_source_refs.csv", index=False)
    write_encoder_contract(out_dir, encoders)
    write_local_artifact_manifest(out_dir, args.feature_root, encoders)

    all_predictions: list[dict[str, Any]] = []
    all_overlap_summaries: list[pd.DataFrame] = []
    coverage_rows: list[dict[str, Any]] = []
    random_rows: list[dict[str, Any]] = []
    representative_segment_embeddings: pd.DataFrame | None = None

    folds_by_target = {spec.target: load_protocol_splits(spec, args.split_path) for spec in TARGETS}
    expected_subjects_by_target = {target: split_subjects(folds) for target, folds in folds_by_target.items()}
    labels_by_target = {
        spec.target: load_cmdc_labels(spec, expected_subjects_by_target[spec.target])
        for spec in TARGETS
    }

    for encoder in encoders:
        segment_embeddings, cols = load_segment_embeddings(
            feature_cache_path(args.feature_root, encoder, "cmdc"),
            encoder.expected_dimension,
        )
        if representative_segment_embeddings is None:
            representative_segment_embeddings = segment_embeddings
        criterion_embeddings = embed_criterion_items(
            encoder,
            device_name=args.device,
            allow_download=args.allow_download,
        )
        overlap_summary = build_overlap_position_summary(segment_embeddings, cols, criterion_embeddings, encoder.slug)
        all_overlap_summaries.append(overlap_summary)
        position_ids = sorted(overlap_summary["segment_id"].astype(str).unique(), key=natural_key)

        for spec in TARGETS:
            folds = folds_by_target[spec.target]
            expected_subjects = expected_subjects_by_target[spec.target]
            labels = labels_by_target[spec.target]
            all_features, all_coverage = average_subject_features(segment_embeddings, cols, position_ids, expected_subjects)
            coverage_rows.append(
                coverage_record(
                    encoder.slug,
                    spec,
                    "all_units",
                    0,
                    position_ids,
                    [],
                    all_coverage,
                    len(position_ids),
                )
            )
            all_predictions.extend(
                evaluate_intervention(
                    all_features,
                    labels,
                    folds,
                    cols,
                    spec,
                    encoder=encoder.slug,
                    intervention="all_units",
                    threshold_pct=0,
                    retained_position_count=len(position_ids),
                    removed_position_count=0,
                )
            )
            floor_features = all_features[["subject_id", "retained_unit_count", "retained_token_count", "retained_chunk_count", *cols]].copy()
            all_predictions.extend(
                evaluate_intervention(
                    floor_features,
                    labels,
                    folds,
                    cols,
                    spec,
                    encoder=encoder.slug,
                    intervention="train_mean_floor",
                    threshold_pct=0,
                    retained_position_count=0,
                    removed_position_count=0,
                )
            )
            for threshold in THRESHOLDS:
                threshold_pct = int(round(threshold * 100))
                high_positions = top_positions(overlap_summary, threshold)
                for intervention in ["minus_high", "high_only"]:
                    kept, removed = intervention_position_sets(
                        position_ids,
                        high_positions,
                        intervention=intervention,
                        random_seed=None,
                    )
                    features, coverage = average_subject_features(segment_embeddings, cols, kept, expected_subjects)
                    coverage_rows.append(
                        coverage_record(
                            encoder.slug,
                            spec,
                            intervention,
                            threshold_pct,
                            kept,
                            removed,
                            coverage,
                            len(position_ids),
                        )
                    )
                    all_predictions.extend(
                        evaluate_intervention(
                            features,
                            labels,
                            folds,
                            cols,
                            spec,
                            encoder=encoder.slug,
                            intervention=intervention,
                            threshold_pct=threshold_pct,
                            retained_position_count=len(kept),
                            removed_position_count=len(removed),
                        )
                    )
                for seed in SEEDS:
                    kept, removed = intervention_position_sets(
                        position_ids,
                        high_positions,
                        intervention="minus_random",
                        random_seed=seed,
                    )
                    random_rows.append(
                        {
                            "encoder": encoder.slug,
                            "target": spec.target,
                            "threshold_pct": threshold_pct,
                            "random_seed": int(seed),
                            "high_positions_removed_count": int(len(high_positions)),
                            "random_positions_removed_count": int(len(removed)),
                            "random_removed_positions": ";".join(removed),
                        }
                    )
                    features, coverage = average_subject_features(segment_embeddings, cols, kept, expected_subjects)
                    coverage_rows.append(
                        coverage_record(
                            encoder.slug,
                            spec,
                            "minus_random",
                            threshold_pct,
                            kept,
                            removed,
                            coverage,
                            len(position_ids),
                            random_seed=seed,
                        )
                    )
                    all_predictions.extend(
                        evaluate_intervention(
                            features,
                            labels,
                            folds,
                            cols,
                            spec,
                            encoder=encoder.slug,
                            intervention="minus_random",
                            threshold_pct=threshold_pct,
                            retained_position_count=len(kept),
                            removed_position_count=len(removed),
                            seeds=[seed],
                        )
                    )

    if representative_segment_embeddings is None:
        raise RuntimeError("no segment embeddings were loaded")
    pd.concat(all_overlap_summaries, ignore_index=True).to_csv(out_dir / "overlap_position_summary.csv", index=False)
    pd.DataFrame(feasibility_rows(cmdc_manifest, representative_segment_embeddings)).to_csv(out_dir / "feasibility_audit.csv", index=False)
    pd.DataFrame(random_rows).drop_duplicates().to_csv(out_dir / "random_deletion_contract.csv", index=False)
    coverage = pd.DataFrame(coverage_rows)
    coverage.to_csv(out_dir / "intervention_coverage_summary.csv", index=False)

    predictions = pd.DataFrame(all_predictions)
    if predictions.empty:
        raise RuntimeError("MV20 generated no predictions")
    predictions = predictions.sort_values(
        ["encoder", "target", "intervention", "threshold_pct", "seed", "fold", "subject_id"],
        key=lambda s: s.map(lambda x: tuple(natural_key(x))) if s.name in {"fold", "subject_id"} else s,
    ).reset_index(drop=True)
    predictions.to_csv(out_dir / "mv20_predictions.csv", index=False)
    metrics_by_seed, metric_summary = metric_records(predictions, bootstrap_resamples=0, seed=20260822)
    metrics_by_seed.to_csv(out_dir / "metrics_by_seed.csv", index=False)
    metric_summary.to_csv(out_dir / "metric_summary.csv", index=False)
    effect_summary = build_effect_summary(predictions, coverage, bootstrap_resamples=args.bootstrap_resamples)
    effect_summary.to_csv(out_dir / "criterion_effect_summary.csv", index=False)
    gate_results, verdict = build_gate_results(effect_summary)
    gate_results.to_csv(out_dir / "pass_fail_gate_results.csv", index=False)

    summary = {
        "generated_at": utc_now(),
        "status": "complete",
        "experiment_id": "P5_MV20",
        "registry_ref": "datasets/registry.yaml",
        "manifest_refs": ["datasets/manifests/cmdc_subjects.csv", "datasets/manifests/pdch_subjects.csv", "datasets/manifests/edaic_subjects.csv"],
        "split_ref": "datasets/splits/phase2_subject_splits.csv",
        "feature_root_ref": rel(args.feature_root),
        "datasets_included": ["CMDC"],
        "datasets_excluded": ["PDCH", "E-DAIC"],
        "encoders": [encoder.slug for encoder in encoders],
        "primary_encoder": "bge_m3",
        "sensitivity_encoder": "multilingual_e5_base",
        "primary_threshold_pct": int(round(PRIMARY_THRESHOLD * 100)),
        "threshold_ladder_pct": [int(round(threshold * 100)) for threshold in THRESHOLDS],
        "seeds": SEEDS,
        "bootstrap_resamples": int(args.bootstrap_resamples),
        "prediction_rows_local_only": int(len(predictions)),
        "metric_summary_rows": int(len(metric_summary)),
        "effect_summary_rows": int(len(effect_summary)),
        "subject_overlap_violations": 0,
        "test_labels_used": False,
        "outcome_guided_overlap_selection": False,
        "new_architecture_trained": False,
        "dataset_identity_delta_status": "not_applicable_single_feasible_primary_dataset",
        "cross_dataset_transfer_status": "not_run_optional_and_no_second_clean_protocol_unit_dataset",
        "local_only_files": ["mv20_predictions.csv"],
        "verdict": verdict,
    }
    (out_dir / "run_summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=True, sort_keys=True) + "\n", encoding="utf-8")
    hygiene = build_hygiene(out_dir)
    summary["artifact_hygiene_passed"] = bool(hygiene["artifact_hygiene_passed"])
    summary["artifact_hygiene_violation_count"] = int(hygiene["violation_count"])
    (out_dir / "artifact_hygiene_audit.json").write_text(json.dumps(hygiene, indent=2, ensure_ascii=True, sort_keys=True) + "\n", encoding="utf-8")
    (out_dir / "run_summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=True, sort_keys=True) + "\n", encoding="utf-8")
    write_report(out_dir, summary, effect_summary, gate_results)
    hygiene = build_hygiene(out_dir)
    (out_dir / "artifact_hygiene_audit.json").write_text(json.dumps(hygiene, indent=2, ensure_ascii=True, sort_keys=True) + "\n", encoding="utf-8")
    summary["artifact_hygiene_passed"] = bool(hygiene["artifact_hygiene_passed"])
    summary["artifact_hygiene_violation_count"] = int(hygiene["violation_count"])
    (out_dir / "run_summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=True, sort_keys=True) + "\n", encoding="utf-8")
    return summary


def coverage_record(
    encoder: str,
    spec: TargetSpec,
    intervention: str,
    threshold_pct: int,
    kept: list[str],
    removed: list[str],
    coverage: dict[str, Any],
    total_positions: int,
    *,
    random_seed: int | None = None,
) -> dict[str, Any]:
    retained_fraction = len(kept) / float(total_positions) if total_positions else float("nan")
    return {
        "encoder": encoder,
        "dataset": "CMDC",
        "target": spec.target,
        "target_role": spec.primary_claim_role,
        "intervention": intervention,
        "threshold_pct": int(threshold_pct),
        "random_seed": "" if random_seed is None else int(random_seed),
        "retained_position_count": int(len(kept)),
        "removed_position_count": int(len(removed)),
        "retained_position_fraction": retained_fraction,
        "removed_position_fraction": len(removed) / float(total_positions) if total_positions else float("nan"),
        "feature_subjects": int(coverage["feature_subjects"]),
        "expected_subjects": int(coverage["expected_subjects"]),
        "missing_subjects": int(coverage["missing_subjects"]),
        "min_retained_units": int(coverage["min_retained_units"]),
        "median_retained_units": float(coverage["median_retained_units"]),
        "max_retained_units": int(coverage["max_retained_units"]),
        "mean_retained_tokens": float(coverage["mean_retained_tokens"]),
        "kept_positions": ";".join(kept),
        "removed_positions": ";".join(removed),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest-dir", type=Path, default=MANIFEST_DIR)
    parser.add_argument("--split-path", type=Path, default=SPLIT_PATH)
    parser.add_argument("--feature-root", type=Path, default=DEFAULT_FEATURE_ROOT)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--encoders", nargs="+", choices=sorted(mv17a.ENCODER_SPECS), default=["bge_m3", "multilingual_e5_base"])
    parser.add_argument("--device", default="auto")
    parser.add_argument("--allow-download", action="store_true")
    parser.add_argument("--bootstrap-resamples", type=int, default=500)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    summary = run_mv20(args)
    print(json.dumps({"out_dir": rel(args.out_dir), "status": summary["status"], "verdict": summary["verdict"]}, indent=2, ensure_ascii=True))


if __name__ == "__main__":
    main()
