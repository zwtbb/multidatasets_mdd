#!/usr/bin/env python3
"""Run Phase 2 EATD audio/text simple fusion baselines.

The runner uses manifest-resolved EATD text plus cached subject-level eGeMAPS
features to evaluate Early Fusion, Late Fusion, and Gated Fusion on the
official train/validation subject split. It writes no raw text, raw audio, or
source paths to prediction files.
"""

from __future__ import annotations

import argparse
import json
import os
import warnings
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
from pandas.errors import PerformanceWarning
from scipy import sparse
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.impute import SimpleImputer
from sklearn.linear_model import Ridge
from sklearn.metrics import mean_absolute_error
from sklearn.model_selection import KFold
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.svm import SVR

from phase2_metrics import metric_records, regression_metrics


ROOT = Path("/root/autodl-tmp")
MANIFEST_PATH = ROOT / "datasets" / "manifests" / "eatd_subjects.csv"
AUDIO_FEATURES = ROOT / "analysis" / "phase2_baselines" / "eatd_audio_egemaps" / "eatd_egemaps_subject_features.csv"
TEXT_PREDICTIONS = ROOT / "analysis" / "phase2_baselines" / "eatd_text_tfidf" / "eatd_text_tfidf_predictions.csv"
AUDIO_PREDICTIONS = ROOT / "analysis" / "phase2_baselines" / "eatd_audio_egemaps" / "eatd_audio_egemaps_predictions.csv"
DEFAULT_OUT_DIR = ROOT / "analysis" / "phase2_baselines" / "eatd_audio_text_fusion"
SEEDS = [0, 1, 2, 3, 4]
VALENCE_ORDER = ["positive", "neutral", "negative"]
TEXT_RUN_ID = "eatd_text_sds_tfidf_ridge"
AUDIO_RUN_ID = "eatd_audio_sds_egemaps_svr"
EARLY_RUN_ID = "eatd_audio_text_sds_early_fusion"
LATE_RUN_ID = "eatd_audio_text_sds_late_fusion"
GATED_RUN_ID = "eatd_audio_text_sds_gated_fusion"
FIXED_RIDGE_ALPHA = 10.0
EARLY_RIDGE_ALPHAS = [10.0, 100.0, 1000.0, 10000.0]
FIXED_SVR_C = 1.0
FIXED_SVR_EPSILON = 0.1


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def read_text(path_value: Any) -> str:
    path = Path(str(path_value))
    if not path.exists():
        raise FileNotFoundError(f"manifest text path missing: {path}")
    return path.read_text(encoding="utf-8", errors="ignore").strip()


def vectorizer() -> TfidfVectorizer:
    return TfidfVectorizer(
        analyzer="char",
        ngram_range=(2, 5),
        min_df=2,
        max_features=50000,
        sublinear_tf=True,
        norm="l2",
    )


def build_text_table(manifest_path: Path) -> pd.DataFrame:
    if not manifest_path.exists():
        raise FileNotFoundError(f"manifest missing: {manifest_path}")
    manifest = pd.read_csv(manifest_path)
    required = {"subject_id", "valence", "text_path", "sds_total", "official_split", "file_valid"}
    missing = required - set(manifest.columns)
    if missing:
        raise ValueError(f"EATD manifest missing columns: {', '.join(sorted(missing))}")
    usable = manifest[
        manifest["file_valid"].fillna(False).astype(bool)
        & manifest["text_path"].notna()
        & manifest["sds_total"].notna()
        & manifest["official_split"].isin(["train", "validation"])
        & manifest["valence"].isin(VALENCE_ORDER)
    ].copy()
    if usable.empty:
        raise ValueError("no usable EATD text rows")

    rows: list[dict[str, Any]] = []
    for subject_id, group in usable.groupby("subject_id", sort=True):
        by_valence = {str(row["valence"]): row for _, row in group.iterrows()}
        missing_valences = [valence for valence in VALENCE_ORDER if valence not in by_valence]
        if missing_valences:
            raise ValueError(f"{subject_id} missing text valence rows: {missing_valences}")
        label_values = group["sds_total"].dropna().unique()
        split_values = group["official_split"].dropna().unique()
        if len(label_values) != 1 or len(split_values) != 1:
            raise ValueError(f"{subject_id} has inconsistent text split/label")
        texts = [read_text(by_valence[valence]["text_path"]) for valence in VALENCE_ORDER]
        rows.append(
            {
                "subject_id": str(subject_id),
                "split": str(split_values[0]),
                "text": "\n".join(texts),
                "sds_total": float(label_values[0]),
                "text_segment_count": int(len(texts)),
                "empty_text_segments": int(sum(1 for text in texts if not text.strip())),
            }
        )
    return pd.DataFrame(rows).sort_values("subject_id").reset_index(drop=True)


def load_audio_features(path: Path) -> tuple[pd.DataFrame, list[str]]:
    if not path.exists():
        raise FileNotFoundError(f"audio feature cache missing: {path}")
    features = pd.read_csv(path)
    required = {"subject_id", "split", "sds_total", "audio_segment_count"}
    missing = required - set(features.columns)
    if missing:
        raise ValueError(f"audio feature cache missing columns: {', '.join(sorted(missing))}")
    features["subject_id"] = features["subject_id"].astype(str)
    feature_columns = [
        column
        for column in features.columns
        if column not in {"subject_id", "split", "sds_total", "audio_segment_count"}
    ]
    if not feature_columns:
        raise ValueError("audio feature cache has no model feature columns")
    return features.sort_values("subject_id").reset_index(drop=True), feature_columns


def build_fusion_table(manifest_path: Path, audio_features_path: Path) -> tuple[pd.DataFrame, list[str]]:
    text = build_text_table(manifest_path)
    audio, audio_feature_columns = load_audio_features(audio_features_path)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", PerformanceWarning)
        table = text.merge(audio, on="subject_id", suffixes=("_text", "_audio"), how="outer", indicator=True)
    table = table.copy()
    merge_counts = table["_merge"].value_counts().to_dict()
    if merge_counts.get("left_only", 0) or merge_counts.get("right_only", 0):
        raise ValueError(f"text/audio subject tables are not aligned: {merge_counts}")
    table = table.drop(columns=["_merge"])
    split_mismatches = int((table["split_text"].astype(str) != table["split_audio"].astype(str)).sum())
    label_mismatches = int((table["sds_total_text"].astype(float) != table["sds_total_audio"].astype(float)).sum())
    if split_mismatches or label_mismatches:
        raise ValueError(f"text/audio table mismatch: splits={split_mismatches}, labels={label_mismatches}")
    table = table.rename(columns={"split_text": "split", "sds_total_text": "sds_total"})
    table = table.drop(columns=["split_audio", "sds_total_audio"])
    train_subjects = set(table.loc[table["split"] == "train", "subject_id"].astype(str))
    validation_subjects = set(table.loc[table["split"] == "validation", "subject_id"].astype(str))
    overlap = sorted(train_subjects & validation_subjects)
    if overlap:
        raise ValueError(f"subject-level split overlap detected: {overlap[:10]}")
    if not train_subjects or not validation_subjects:
        raise ValueError("EATD fusion requires non-empty train and validation subjects")
    return table.sort_values("subject_id").reset_index(drop=True), audio_feature_columns


def fit_text_model(train: pd.DataFrame) -> Pipeline:
    model = Pipeline([("tfidf", vectorizer()), ("ridge", Ridge(alpha=FIXED_RIDGE_ALPHA, solver="lsqr"))])
    model.fit(train["text"], train["sds_total"].to_numpy(dtype=np.float64))
    return model


def fit_audio_model(train: pd.DataFrame, audio_feature_columns: list[str]) -> Pipeline:
    model = Pipeline(
        [
            ("imputer", SimpleImputer(strategy="median")),
            ("scaler", StandardScaler()),
            ("svr", SVR(C=FIXED_SVR_C, epsilon=FIXED_SVR_EPSILON, kernel="rbf")),
        ]
    )
    model.fit(train[audio_feature_columns], train["sds_total"].to_numpy(dtype=np.float64))
    return model


def predict_early_with_alpha(
    train: pd.DataFrame,
    validation: pd.DataFrame,
    audio_feature_columns: list[str],
    alpha: float,
) -> tuple[np.ndarray, dict[str, Any]]:
    tfidf = vectorizer()
    text_train = tfidf.fit_transform(train["text"])
    text_validation = tfidf.transform(validation["text"])
    imputer = SimpleImputer(strategy="median")
    scaler = StandardScaler()
    audio_train = scaler.fit_transform(imputer.fit_transform(train[audio_feature_columns]))
    audio_validation = scaler.transform(imputer.transform(validation[audio_feature_columns]))
    x_train = sparse.hstack([text_train, sparse.csr_matrix(audio_train)], format="csr")
    x_validation = sparse.hstack([text_validation, sparse.csr_matrix(audio_validation)], format="csr")
    model = Ridge(alpha=alpha, solver="lsqr")
    model.fit(x_train, train["sds_total"].to_numpy(dtype=np.float64))
    return model.predict(x_validation), {
        "tfidf_feature_count": int(text_train.shape[1]),
        "audio_feature_count": int(len(audio_feature_columns)),
        "ridge_alpha": float(alpha),
    }


def choose_early_ridge_alpha(train: pd.DataFrame, audio_feature_columns: list[str], seed: int) -> tuple[float, list[dict[str, Any]]]:
    folds = KFold(n_splits=5, shuffle=True, random_state=seed)
    candidates: list[dict[str, Any]] = []
    best_key: tuple[float, float, float] | None = None
    best_alpha: float | None = None
    for alpha in EARLY_RIDGE_ALPHAS:
        y_true_all: list[float] = []
        y_pred_all: list[float] = []
        for train_idx, dev_idx in folds.split(train):
            inner_train = train.iloc[train_idx].reset_index(drop=True)
            inner_dev = train.iloc[dev_idx].reset_index(drop=True)
            y_pred, _ = predict_early_with_alpha(inner_train, inner_dev, audio_feature_columns, alpha)
            y_true_all.extend(inner_dev["sds_total"].to_numpy(dtype=np.float64).tolist())
            y_pred_all.extend(y_pred.tolist())
        metrics = regression_metrics(y_true_all, y_pred_all)
        mae = float(mean_absolute_error(y_true_all, y_pred_all))
        ccc = metrics["CCC"]
        spearman_value = metrics["Spearman"]
        candidates.append(
            {
                "alpha": float(alpha),
                "train_oof_mae": mae,
                "train_oof_ccc": float(ccc) if ccc is not None else None,
                "train_oof_spearman": float(spearman_value) if spearman_value is not None else None,
            }
        )
        ccc_for_sort = float(ccc) if ccc is not None else -1.0e9
        candidate_key = (-mae, ccc_for_sort, -float(alpha))
        if best_key is None or candidate_key > best_key:
            best_key = candidate_key
            best_alpha = float(alpha)
    if best_alpha is None:
        raise RuntimeError("early-fusion Ridge alpha selection failed")
    return best_alpha, candidates


def prediction_meta(run_id: str, model: str, seed: int, row: pd.Series) -> dict[str, Any]:
    return {
        "run_id": run_id,
        "dataset": "EATD-Corpus",
        "modality": "Audio/Text",
        "task": "SDS regression",
        "model": model,
        "seed": int(seed),
        "task_type": "severity_regression",
        "subject_id": row["subject_id"],
        "split": "validation",
        "text_segment_count": int(row["text_segment_count"]),
        "audio_segment_count": int(row["audio_segment_count"]),
    }


def train_target_bounds(train: pd.DataFrame) -> tuple[float, float]:
    return float(train["sds_total"].min()), float(train["sds_total"].max())


def clip_to_train_target_range(y_pred: np.ndarray, bounds: tuple[float, float]) -> tuple[np.ndarray, int]:
    clipped = np.clip(np.asarray(y_pred, dtype=np.float64), bounds[0], bounds[1])
    clip_count = int(np.sum(np.abs(clipped - np.asarray(y_pred, dtype=np.float64)) > 1.0e-12))
    return clipped, clip_count


def run_early_fusion(table: pd.DataFrame, audio_feature_columns: list[str]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    train = table[table["split"] == "train"].reset_index(drop=True)
    validation = table[table["split"] == "validation"].reset_index(drop=True)
    target_bounds = train_target_bounds(train)
    predictions: list[dict[str, Any]] = []
    seed_summaries: list[dict[str, Any]] = []
    for seed in SEEDS:
        ridge_alpha, alpha_candidates = choose_early_ridge_alpha(train, audio_feature_columns, seed)
        y_pred, model_summary = predict_early_with_alpha(train, validation, audio_feature_columns, ridge_alpha)
        if not np.isfinite(y_pred).all():
            raise ValueError("early fusion produced non-finite predictions")
        y_pred, clip_count = clip_to_train_target_range(y_pred, target_bounds)
        for idx, row in validation.iterrows():
            predictions.append(
                {
                    **prediction_meta(EARLY_RUN_ID, "Early Fusion", seed, row),
                    "y_true": float(row["sds_total"]),
                    "y_pred": float(y_pred[idx]),
                    "y_score": "",
                    "fusion_rule": "concatenate_tfidf_and_egemaps_then_ridge",
                    "prediction_clipped_to_train_target_range": True,
                }
            )
        seed_summaries.append(
            {
                "run_id": EARLY_RUN_ID,
                "seed": int(seed),
                "train_subjects": int(len(train)),
                "validation_subjects": int(len(validation)),
                "alpha_selection": "inner_5fold_train_oof_mae",
                "alpha_candidates": alpha_candidates,
                "target_min_train": float(target_bounds[0]),
                "target_max_train": float(target_bounds[1]),
                "validation_clip_count": int(clip_count),
                **model_summary,
            }
        )
    return predictions, seed_summaries


def load_regression_predictions(path: Path, run_id: str, name: str) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"prediction file missing: {path}")
    frame = pd.read_csv(path)
    required = {"run_id", "seed", "subject_id", "split", "y_true", "y_pred"}
    missing = required - set(frame.columns)
    if missing:
        raise ValueError(f"{path} missing columns: {', '.join(sorted(missing))}")
    selected = frame[frame["run_id"].astype(str) == run_id].copy()
    if selected.empty:
        raise ValueError(f"{path} has no rows for {run_id}")
    selected = selected[["seed", "subject_id", "split", "y_true", "y_pred"]].copy()
    selected = selected.rename(columns={"y_true": f"y_true_{name}", "y_pred": f"y_pred_{name}"})
    duplicate_count = int(selected.duplicated(["seed", "subject_id"]).sum())
    if duplicate_count:
        raise ValueError(f"{run_id} has duplicate seed/subject rows: {duplicate_count}")
    return selected


def run_late_fusion(
    text_path: Path,
    audio_path: Path,
    target_bounds: tuple[float, float],
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    text = load_regression_predictions(text_path, TEXT_RUN_ID, "text")
    audio = load_regression_predictions(audio_path, AUDIO_RUN_ID, "audio")
    merged = text.merge(audio, on=["seed", "subject_id", "split"], how="outer", indicator=True)
    merge_counts = merged["_merge"].value_counts().to_dict()
    if merge_counts.get("left_only", 0) or merge_counts.get("right_only", 0):
        raise ValueError(f"text/audio prediction keys are not aligned: {merge_counts}")
    merged = merged.drop(columns=["_merge"])
    label_mismatches = int((merged["y_true_text"].astype(float) != merged["y_true_audio"].astype(float)).sum())
    if label_mismatches:
        raise ValueError(f"text/audio prediction labels disagree on {label_mismatches} rows")
    y_pred_raw = merged[["y_pred_text", "y_pred_audio"]].astype(float).mean(axis=1).to_numpy(dtype=np.float64)
    if not np.isfinite(y_pred_raw).all():
        raise ValueError("late fusion produced non-finite predictions")
    y_pred, clip_count = clip_to_train_target_range(y_pred_raw, target_bounds)
    predictions = pd.DataFrame(
        {
            "run_id": LATE_RUN_ID,
            "dataset": "EATD-Corpus",
            "modality": "Audio/Text",
            "task": "SDS regression",
            "model": "Late Fusion",
            "seed": merged["seed"].astype(int),
            "task_type": "severity_regression",
            "subject_id": merged["subject_id"].astype(str),
            "split": merged["split"].astype(str),
            "y_true": merged["y_true_text"].astype(float),
            "y_pred": y_pred.astype(float),
            "y_score": "",
            "text_run_id": TEXT_RUN_ID,
            "audio_run_id": AUDIO_RUN_ID,
            "fusion_rule": "unweighted_prediction_average",
            "prediction_clipped_to_train_target_range": True,
        }
    )
    summary = {
        "run_id": LATE_RUN_ID,
        "text_rows": int(len(text)),
        "audio_rows": int(len(audio)),
        "prediction_rows": int(len(predictions)),
        "merge_counts": {str(key): int(value) for key, value in merge_counts.items()},
        "subject_count": int(predictions["subject_id"].nunique()),
        "seed_count": int(predictions["seed"].nunique()),
        "label_mismatches": label_mismatches,
        "target_min_train": float(target_bounds[0]),
        "target_max_train": float(target_bounds[1]),
        "validation_clip_count": int(clip_count),
    }
    return predictions.to_dict("records"), summary


def train_oof_reliability_weights(
    train: pd.DataFrame,
    audio_feature_columns: list[str],
    seed: int,
) -> dict[str, Any]:
    folds = KFold(n_splits=5, shuffle=True, random_state=seed)
    y_true = train["sds_total"].to_numpy(dtype=np.float64)
    text_oof = np.full(len(train), np.nan, dtype=np.float64)
    audio_oof = np.full(len(train), np.nan, dtype=np.float64)
    for train_idx, dev_idx in folds.split(train):
        inner_train = train.iloc[train_idx].reset_index(drop=True)
        inner_dev = train.iloc[dev_idx].reset_index(drop=True)
        text_model = fit_text_model(inner_train)
        audio_model = fit_audio_model(inner_train, audio_feature_columns)
        text_oof[dev_idx] = text_model.predict(inner_dev["text"])
        audio_oof[dev_idx] = audio_model.predict(inner_dev[audio_feature_columns])
    if not np.isfinite(text_oof).all() or not np.isfinite(audio_oof).all():
        raise ValueError("gated fusion train OOF predictions contain non-finite values")
    text_mae = float(mean_absolute_error(y_true, text_oof))
    audio_mae = float(mean_absolute_error(y_true, audio_oof))
    text_inverse = 1.0 / max(text_mae, 1.0e-6)
    audio_inverse = 1.0 / max(audio_mae, 1.0e-6)
    text_weight = text_inverse / (text_inverse + audio_inverse)
    audio_weight = 1.0 - text_weight
    return {
        "seed": int(seed),
        "inner_folds": 5,
        "text_oof_mae": text_mae,
        "audio_oof_mae": audio_mae,
        "text_weight": float(text_weight),
        "audio_weight": float(audio_weight),
        "weight_rule": "inverse_train_oof_mae",
    }


def run_gated_fusion(table: pd.DataFrame, audio_feature_columns: list[str]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    train = table[table["split"] == "train"].reset_index(drop=True)
    validation = table[table["split"] == "validation"].reset_index(drop=True)
    target_bounds = train_target_bounds(train)
    predictions: list[dict[str, Any]] = []
    seed_summaries: list[dict[str, Any]] = []
    for seed in SEEDS:
        weights = train_oof_reliability_weights(train, audio_feature_columns, seed)
        text_model = fit_text_model(train)
        audio_model = fit_audio_model(train, audio_feature_columns)
        text_pred = text_model.predict(validation["text"])
        audio_pred = audio_model.predict(validation[audio_feature_columns])
        y_pred = weights["text_weight"] * text_pred + weights["audio_weight"] * audio_pred
        if not np.isfinite(y_pred).all():
            raise ValueError("gated fusion produced non-finite predictions")
        y_pred, clip_count = clip_to_train_target_range(y_pred, target_bounds)
        for idx, row in validation.iterrows():
            predictions.append(
                {
                    **prediction_meta(GATED_RUN_ID, "Gated Fusion", seed, row),
                    "y_true": float(row["sds_total"]),
                    "y_pred": float(y_pred[idx]),
                    "y_score": "",
                    "fusion_rule": "inverse_train_oof_mae_weighted_prediction_average",
                    "text_weight": float(weights["text_weight"]),
                    "audio_weight": float(weights["audio_weight"]),
                    "prediction_clipped_to_train_target_range": True,
                }
            )
        seed_summaries.append(
            {
                "run_id": GATED_RUN_ID,
                "train_subjects": int(len(train)),
                "validation_subjects": int(len(validation)),
                "ridge_alpha": float(FIXED_RIDGE_ALPHA),
                "svr_c": float(FIXED_SVR_C),
                "svr_epsilon": float(FIXED_SVR_EPSILON),
                "target_min_train": float(target_bounds[0]),
                "target_max_train": float(target_bounds[1]),
                "validation_clip_count": int(clip_count),
                **weights,
            }
        )
    return predictions, seed_summaries


def write_report(out_dir: Path, summary: dict[str, Any]) -> None:
    lines = [
        "# EATD Audio/Text Fusion Phase 2 Baselines",
        "",
        f"Generated: `{summary['generated_at']}`",
        "",
        "## Protocol",
        "",
        "- Input interface: manifest-resolved valid EATD text plus cached subject-level eGeMAPS features.",
        "- Early Fusion: concatenate train-fit TF-IDF features with standardized eGeMAPS features, then fit Ridge regression.",
        "- Early Fusion Ridge alpha is selected by train-split-only inner 5-fold OOF MAE from a fixed grid.",
        "- Late Fusion: unweighted average of audited EATD text TF-IDF and audio eGeMAPS validation predictions.",
        "- Gated Fusion: train-split-only inner 5-fold OOF MAE sets global inverse-error text/audio weights.",
        "- Regression outputs are clipped to the train-split observed SDS target range.",
        "- Evaluation split: official train/validation subject split.",
        "- No validation or test labels are used for fusion weighting or hyperparameter selection.",
        "- No test split is used.",
        "- Raw text, raw audio, source paths, and file names are not written to prediction outputs.",
        "",
        "## Audit",
        "",
        f"- Runs: `{summary['runs']}`",
        f"- Train subjects: `{summary['train_subjects']}`",
        f"- Validation subjects: `{summary['validation_subjects']}`",
        f"- Subject overlap: `{summary['subject_overlap']}`",
        f"- Seeds: `{summary['seeds']}`",
        f"- Bootstrap resamples: `{summary['bootstrap_resamples']}`",
        f"- Prediction rows: `{summary['prediction_rows']}`",
        f"- Late-fusion label mismatches: `{summary['late_summary']['label_mismatches']}`",
        f"- Raw inputs written: `{summary['raw_inputs_written']}`",
        f"- Source paths written: `{summary['source_paths_written']}`",
        "",
        "## Output Files",
        "",
        "- `eatd_audio_text_fusion_predictions.csv`",
        "- `phase2_metrics_by_seed.csv`",
        "- `phase2_metric_summary.csv`",
        "- `eatd_audio_text_fusion_run_summary.json`",
    ]
    (out_dir / "eatd_audio_text_fusion_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, default=MANIFEST_PATH)
    parser.add_argument("--audio-features", type=Path, default=AUDIO_FEATURES)
    parser.add_argument("--text-predictions", type=Path, default=TEXT_PREDICTIONS)
    parser.add_argument("--audio-predictions", type=Path, default=AUDIO_PREDICTIONS)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--bootstrap-resamples", type=int, default=1000)
    args = parser.parse_args()

    table, audio_feature_columns = build_fusion_table(args.manifest, args.audio_features)
    train_subjects = set(table.loc[table["split"] == "train", "subject_id"].astype(str))
    validation_subjects = set(table.loc[table["split"] == "validation", "subject_id"].astype(str))
    subject_overlap = sorted(train_subjects & validation_subjects)
    target_bounds = train_target_bounds(table[table["split"] == "train"])

    early_predictions, early_seed_summaries = run_early_fusion(table, audio_feature_columns)
    late_predictions, late_summary = run_late_fusion(args.text_predictions, args.audio_predictions, target_bounds)
    gated_predictions, gated_seed_summaries = run_gated_fusion(table, audio_feature_columns)

    predictions_frame = pd.DataFrame([*early_predictions, *late_predictions, *gated_predictions])
    args.out_dir.mkdir(parents=True, exist_ok=True)
    predictions_path = args.out_dir / "eatd_audio_text_fusion_predictions.csv"
    predictions_frame.to_csv(predictions_path, index=False)

    metrics_by_seed, metric_summary = metric_records(
        predictions_frame,
        bootstrap_resamples=args.bootstrap_resamples,
        seed=20260727,
    )
    metrics_by_seed.to_csv(args.out_dir / "phase2_metrics_by_seed.csv", index=False)
    metric_summary.to_csv(args.out_dir / "phase2_metric_summary.csv", index=False)

    run_summary = {
        "generated_at": utc_now(),
        "runs": [EARLY_RUN_ID, LATE_RUN_ID, GATED_RUN_ID],
        "source_runs": [TEXT_RUN_ID, AUDIO_RUN_ID],
        "seeds": SEEDS,
        "seed_count": len(SEEDS),
        "bootstrap_resamples": int(args.bootstrap_resamples),
        "train_subjects": int(len(train_subjects)),
        "validation_subjects": int(len(validation_subjects)),
        "subject_overlap": int(len(subject_overlap)),
        "subject_rows": int(len(table)),
        "text_segment_count_min": int(table["text_segment_count"].min()),
        "text_segment_count_max": int(table["text_segment_count"].max()),
        "audio_segment_count_min": int(table["audio_segment_count"].min()),
        "audio_segment_count_max": int(table["audio_segment_count"].max()),
        "audio_feature_count": int(len(audio_feature_columns)),
        "target_min_train": float(target_bounds[0]),
        "target_max_train": float(target_bounds[1]),
        "prediction_clipped_to_train_target_range": True,
        "prediction_rows": int(len(predictions_frame)),
        "early_seed_summaries": early_seed_summaries,
        "late_summary": late_summary,
        "gated_seed_summaries": gated_seed_summaries,
        "fixed_hyperparameters": {
            "text_source_ridge_alpha": float(FIXED_RIDGE_ALPHA),
            "svr_c": float(FIXED_SVR_C),
            "svr_epsilon": float(FIXED_SVR_EPSILON),
            "early_ridge_alpha_grid": EARLY_RIDGE_ALPHAS,
        },
        "no_test_split_used": True,
        "raw_inputs_written": False,
        "source_paths_written": False,
    }
    (args.out_dir / "eatd_audio_text_fusion_run_summary.json").write_text(
        json.dumps(run_summary, indent=2, ensure_ascii=True, sort_keys=True),
        encoding="utf-8",
    )
    write_report(args.out_dir, run_summary)
    print(f"Wrote {predictions_path}")
    print(f"Wrote {args.out_dir / 'phase2_metric_summary.csv'}")


if __name__ == "__main__":
    main()
