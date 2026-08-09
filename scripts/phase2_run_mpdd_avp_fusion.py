#!/usr/bin/env python3
"""Run Phase 2 MPDD audio/video/personality simple fusion baselines.

Early Fusion trains a fixed multinomial logistic model over concatenated frozen
WavLM audio features, ResNet video temporal-pooling features, and train-fold
TF-IDF personality features. Late Fusion and Gated Fusion combine audited
audio/video out-of-fold probabilities with an internal personality-only
TF-IDF component. The gated rule is confidence-weighted probability averaging;
it is not a personality gate and uses no held-out labels to learn weights.
"""

from __future__ import annotations

import argparse
import json
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
from scipy import sparse
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import StratifiedKFold
from sklearn.preprocessing import StandardScaler

from phase2_metrics import metric_records


ROOT = Path("/root/autodl-tmp")
MANIFEST_PATH = ROOT / "datasets" / "manifests" / "mpdd_avg_2026_subjects.csv"
AUDIO_FEATURES = ROOT / "analysis" / "phase2_baselines" / "mpdd_audio_wavlm" / "mpdd_wavlm_subject_features.csv"
AUDIO_PREDICTIONS = ROOT / "analysis" / "phase2_baselines" / "mpdd_audio_wavlm" / "mpdd_audio_wavlm_predictions.csv"
VIDEO_FEATURES = ROOT / "analysis" / "phase2_baselines" / "mpdd_video_features" / "mpdd_resnet_video_subject_features.csv"
VIDEO_PREDICTIONS = ROOT / "analysis" / "phase2_baselines" / "mpdd_video_features" / "mpdd_video_features_predictions.csv"
DEFAULT_OUT_DIR = ROOT / "analysis" / "phase2_baselines" / "mpdd_avp_fusion"
DATASET_DISPLAY = "MPDD-AVG-2026"
SEEDS = [0, 1, 2, 3, 4]
FIXED_LOGISTIC_C = 1.0
PERSONALITY_COMPONENT_RUN_ID = "mpdd_personality_severity_tfidf_logistic_internal"
AUDIO_COMPONENT_RUN_ID = "mpdd_audio_severity_wavlm_mlp"
VIDEO_COMPONENT_RUN_ID = "mpdd_video_severity_temporal_pooling"


@dataclass(frozen=True)
class FusionSpec:
    run_id: str
    model: str


EARLY_SPEC = FusionSpec("mpdd_avp_severity_early_fusion", "Early Fusion")
LATE_SPEC = FusionSpec("mpdd_avp_severity_late_fusion", "Late Fusion")
GATED_SPEC = FusionSpec("mpdd_avp_severity_gated_fusion", "Gated Fusion")


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def natural_key(value: Any) -> list[Any]:
    return [int(part) if part.isdigit() else part for part in re.split(r"(\d+)", str(value))]


def read_manifest(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"manifest missing: {path}")
    return pd.read_csv(path)


def personality_vectorizer() -> TfidfVectorizer:
    return TfidfVectorizer(
        analyzer="word",
        ngram_range=(1, 2),
        min_df=2,
        max_features=5000,
        sublinear_tf=True,
        norm="l2",
        lowercase=True,
    )


def labeled_subject_rows(manifest_path: Path) -> pd.DataFrame:
    manifest = read_manifest(manifest_path)
    required = {
        "subject_id",
        "personality",
        "phq9_total",
        "severity_label",
        "binary_label",
        "age",
        "official_split",
        "file_valid",
    }
    missing = required - set(manifest.columns)
    if missing:
        raise ValueError(f"MPDD manifest missing columns: {', '.join(sorted(missing))}")
    rows = manifest[
        manifest["file_valid"].fillna(False).astype(bool)
        & manifest["official_split"].eq("train")
        & manifest["personality"].notna()
        & manifest["severity_label"].notna()
        & manifest["phq9_total"].notna()
        & manifest["binary_label"].notna()
    ].copy()
    if rows.empty:
        raise ValueError("no labeled MPDD train subjects with personality metadata")
    subjects: list[dict[str, Any]] = []
    for subject_id, group in rows.groupby("subject_id", sort=False):
        phq_values = group["phq9_total"].dropna().unique()
        severity_values = group["severity_label"].dropna().unique()
        binary_values = group["binary_label"].dropna().unique()
        age_values = group["age"].dropna().astype(str).unique()
        personality_values = group["personality"].dropna().astype(str).unique()
        if len(phq_values) != 1 or len(severity_values) != 1 or len(binary_values) != 1:
            raise ValueError(f"{subject_id} has inconsistent MPDD labels")
        if len(personality_values) != 1:
            raise ValueError(f"{subject_id} has inconsistent personality metadata")
        personality_text = str(personality_values[0]).strip()
        if not personality_text:
            raise ValueError(f"{subject_id} has empty personality metadata")
        subjects.append(
            {
                "subject_id": str(subject_id),
                "age_group": str(age_values[0]) if len(age_values) else "",
                "phq9_total": float(phq_values[0]),
                "severity_label": int(severity_values[0]),
                "binary_label": int(binary_values[0]),
                "personality_text": personality_text,
                "personality_char_count": int(len(personality_text)),
            }
        )
    return (
        pd.DataFrame(subjects)
        .sort_values("subject_id", key=lambda series: series.map(lambda item: tuple(natural_key(item))))
        .reset_index(drop=True)
    )


def load_feature_table(path: Path, subjects: set[str], prefix: str, required_metadata: set[str]) -> tuple[pd.DataFrame, list[str]]:
    if not path.exists():
        raise FileNotFoundError(f"feature cache missing: {path}")
    frame = pd.read_csv(path)
    if "subject_id" not in frame.columns:
        raise ValueError(f"{path} missing subject_id")
    frame["subject_id"] = frame["subject_id"].astype(str)
    missing_metadata = required_metadata - set(frame.columns)
    if missing_metadata:
        raise ValueError(f"{path} missing columns: {', '.join(sorted(missing_metadata))}")
    selected = frame[frame["subject_id"].isin(subjects)].copy()
    missing_subjects = sorted(subjects - set(selected["subject_id"]), key=natural_key)
    if missing_subjects:
        raise ValueError(f"{path} missing feature rows for subjects: {missing_subjects[:10]}")
    feature_columns = [column for column in selected.columns if column.startswith(prefix)]
    if not feature_columns:
        raise ValueError(f"{path} has no feature columns with prefix {prefix}")
    return (
        selected.sort_values("subject_id", key=lambda series: series.map(lambda item: tuple(natural_key(item)))).reset_index(drop=True),
        feature_columns,
    )


def build_fusion_table(
    manifest_path: Path,
    audio_features_path: Path,
    video_features_path: Path,
) -> tuple[pd.DataFrame, list[str], list[str]]:
    subjects = labeled_subject_rows(manifest_path)
    subject_ids = set(subjects["subject_id"].astype(str))
    audio, audio_columns = load_feature_table(
        audio_features_path,
        subject_ids,
        "wavlm_",
        {"audio_segment_count", "duration_seconds_sum", "chunk_count_sum"},
    )
    video, video_columns = load_feature_table(
        video_features_path,
        subject_ids,
        "resnet_",
        {"video_event_count", "video_frame_count"},
    )
    audio_keep = ["subject_id", "audio_segment_count", "duration_seconds_sum", "chunk_count_sum"] + audio_columns
    video_keep = ["subject_id", "video_event_count", "video_frame_count"] + video_columns
    table = subjects.merge(audio[audio_keep], on="subject_id", how="inner").merge(
        video[video_keep],
        on="subject_id",
        how="inner",
    )
    if len(table) != len(subjects):
        raise ValueError(f"AVP feature merge produced {len(table)} rows for {len(subjects)} subjects")
    return (
        table.sort_values("subject_id", key=lambda series: series.map(lambda item: tuple(natural_key(item)))).reset_index(drop=True),
        audio_columns,
        video_columns,
    )


def classifier(seed: int) -> LogisticRegression:
    return LogisticRegression(
        C=FIXED_LOGISTIC_C,
        class_weight="balanced",
        max_iter=1000,
        random_state=seed,
        solver="lbfgs",
    )


def align_probabilities(raw_prob: np.ndarray, local_classes: np.ndarray, class_labels: list[int]) -> np.ndarray:
    probabilities = np.zeros((raw_prob.shape[0], max(class_labels) + 1), dtype=np.float64)
    for local_idx, class_value in enumerate(local_classes):
        probabilities[:, int(class_value)] = raw_prob[:, local_idx]
    return probabilities


def prediction_meta(spec: FusionSpec, seed: int, fold: int, row: pd.Series) -> dict[str, Any]:
    return {
        "run_id": spec.run_id,
        "dataset": DATASET_DISPLAY,
        "modality": "AVP",
        "task": "ordinal severity prediction",
        "model": spec.model,
        "seed": int(seed),
        "fold": int(fold),
        "task_type": "ordinal_prediction",
        "subject_id": str(row["subject_id"]),
        "split": "train_oof",
        "age_group": str(row["age_group"]),
        "audio_segment_count": int(row["audio_segment_count"]),
        "video_event_count": int(row["video_event_count"]),
        "video_frame_count": int(row["video_frame_count"]),
    }


def run_early_fusion(
    table: pd.DataFrame,
    audio_columns: list[str],
    video_columns: list[str],
) -> tuple[pd.DataFrame, list[dict[str, Any]]]:
    labels = table["severity_label"].to_numpy(dtype=np.int64)
    class_labels = sorted(int(value) for value in np.unique(labels))
    dense_columns = audio_columns + video_columns
    predictions: list[dict[str, Any]] = []
    fold_summaries: list[dict[str, Any]] = []
    for seed in SEEDS:
        folds = StratifiedKFold(n_splits=5, shuffle=True, random_state=seed)
        for fold, (train_idx, heldout_idx) in enumerate(folds.split(table, labels), start=1):
            train = table.iloc[train_idx].reset_index(drop=True)
            heldout = table.iloc[heldout_idx].reset_index(drop=True)

            tfidf = personality_vectorizer()
            personality_train = tfidf.fit_transform(train["personality_text"].fillna(""))
            personality_heldout = tfidf.transform(heldout["personality_text"].fillna(""))

            imputer = SimpleImputer(strategy="median")
            scaler = StandardScaler()
            dense_train = scaler.fit_transform(imputer.fit_transform(train[dense_columns]))
            dense_heldout = scaler.transform(imputer.transform(heldout[dense_columns]))
            x_train = sparse.hstack([sparse.csr_matrix(dense_train), personality_train], format="csr")
            x_heldout = sparse.hstack([sparse.csr_matrix(dense_heldout), personality_heldout], format="csr")

            model = classifier(seed + fold)
            model.fit(x_train, train["severity_label"].astype(int))
            y_pred = model.predict(x_heldout).astype(int)
            probabilities = align_probabilities(model.predict_proba(x_heldout), model.classes_, class_labels)
            for idx, row in heldout.iterrows():
                predictions.append(
                    {
                        **prediction_meta(EARLY_SPEC, seed, fold, row),
                        "personality_feature_count": int(personality_train.shape[1]),
                        "y_true": int(row["severity_label"]),
                        "y_pred": int(y_pred[idx]),
                        "y_prob": json.dumps([float(value) for value in probabilities[idx]], ensure_ascii=True),
                    }
                )
            fold_summaries.append(
                {
                    "run_id": EARLY_SPEC.run_id,
                    "seed": int(seed),
                    "fold": int(fold),
                    "train_subjects": int(len(train)),
                    "heldout_subjects": int(len(heldout)),
                    "audio_feature_count": int(len(audio_columns)),
                    "video_feature_count": int(len(video_columns)),
                    "personality_feature_count": int(personality_train.shape[1]),
                    "logistic_c": float(FIXED_LOGISTIC_C),
                    "train_severity_counts": {str(k): int(v) for k, v in train["severity_label"].astype(int).value_counts().sort_index().items()},
                    "heldout_severity_counts": {str(k): int(v) for k, v in heldout["severity_label"].astype(int).value_counts().sort_index().items()},
                }
            )
    return pd.DataFrame(predictions), fold_summaries


def run_personality_component(table: pd.DataFrame) -> tuple[pd.DataFrame, list[dict[str, Any]]]:
    labels = table["severity_label"].to_numpy(dtype=np.int64)
    class_labels = sorted(int(value) for value in np.unique(labels))
    predictions: list[dict[str, Any]] = []
    fold_summaries: list[dict[str, Any]] = []
    for seed in SEEDS:
        folds = StratifiedKFold(n_splits=5, shuffle=True, random_state=seed)
        for fold, (train_idx, heldout_idx) in enumerate(folds.split(table, labels), start=1):
            train = table.iloc[train_idx].reset_index(drop=True)
            heldout = table.iloc[heldout_idx].reset_index(drop=True)
            tfidf = personality_vectorizer()
            x_train = tfidf.fit_transform(train["personality_text"].fillna(""))
            x_heldout = tfidf.transform(heldout["personality_text"].fillna(""))
            model = classifier(seed + fold)
            model.fit(x_train, train["severity_label"].astype(int))
            y_pred = model.predict(x_heldout).astype(int)
            probabilities = align_probabilities(model.predict_proba(x_heldout), model.classes_, class_labels)
            for idx, row in heldout.iterrows():
                predictions.append(
                    {
                        "run_id": PERSONALITY_COMPONENT_RUN_ID,
                        "dataset": DATASET_DISPLAY,
                        "modality": "Personality",
                        "task": "ordinal severity prediction",
                        "model": "personality TF-IDF + Logistic internal component",
                        "seed": int(seed),
                        "fold": int(fold),
                        "task_type": "ordinal_prediction",
                        "subject_id": str(row["subject_id"]),
                        "split": "train_oof",
                        "age_group": str(row["age_group"]),
                        "personality_char_count": int(row["personality_char_count"]),
                        "personality_feature_count": int(x_train.shape[1]),
                        "y_true": int(row["severity_label"]),
                        "y_pred": int(y_pred[idx]),
                        "y_prob": json.dumps([float(value) for value in probabilities[idx]], ensure_ascii=True),
                    }
                )
            fold_summaries.append(
                {
                    "run_id": PERSONALITY_COMPONENT_RUN_ID,
                    "seed": int(seed),
                    "fold": int(fold),
                    "train_subjects": int(len(train)),
                    "heldout_subjects": int(len(heldout)),
                    "personality_feature_count": int(x_train.shape[1]),
                    "logistic_c": float(FIXED_LOGISTIC_C),
                }
            )
    return pd.DataFrame(predictions), fold_summaries


def parse_probability_vector(value: Any, class_count: int) -> np.ndarray:
    if value is None or (isinstance(value, float) and np.isnan(value)):
        raise ValueError("missing probability vector")
    parsed = json.loads(str(value))
    if not isinstance(parsed, list) or not parsed:
        raise ValueError(f"invalid probability vector: {value}")
    arr = np.asarray(parsed, dtype=np.float64).reshape(-1)
    if not np.all(np.isfinite(arr)):
        raise ValueError(f"non-finite probability vector: {value}")
    padded = np.zeros(class_count, dtype=np.float64)
    padded[: min(class_count, arr.size)] = arr[:class_count]
    total = float(np.sum(padded))
    if total <= 0.0:
        raise ValueError(f"zero probability vector: {value}")
    return np.clip(padded / total, 0.0, 1.0)


def load_component_predictions(path: Path, run_id: str, component_name: str) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"component prediction file missing: {path}")
    frame = pd.read_csv(path)
    required = {"run_id", "seed", "fold", "subject_id", "y_true", "y_pred", "y_prob"}
    missing = required - set(frame.columns)
    if missing:
        raise ValueError(f"{path} missing columns: {', '.join(sorted(missing))}")
    selected = frame[frame["run_id"].astype(str) == run_id].copy()
    if selected.empty:
        raise ValueError(f"{path} has no rows for {run_id}")
    duplicate_count = int(selected.duplicated(["seed", "fold", "subject_id"]).sum())
    if duplicate_count:
        raise ValueError(f"{run_id} has duplicate seed/fold/subject rows: {duplicate_count}")
    selected["seed"] = selected["seed"].astype(int)
    selected["fold"] = selected["fold"].astype(str)
    selected["subject_id"] = selected["subject_id"].astype(str)
    selected = selected[["seed", "fold", "subject_id", "y_true", "y_pred", "y_prob"]].rename(
        columns={
            "y_true": f"y_true_{component_name}",
            "y_pred": f"y_pred_{component_name}",
            "y_prob": f"y_prob_{component_name}",
        }
    )
    return selected


def merge_components(
    audio_predictions_path: Path,
    video_predictions_path: Path,
    personality_predictions: pd.DataFrame,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    audio = load_component_predictions(audio_predictions_path, AUDIO_COMPONENT_RUN_ID, "audio")
    video = load_component_predictions(video_predictions_path, VIDEO_COMPONENT_RUN_ID, "video")
    personality = load_component_predictions_from_frame(personality_predictions, PERSONALITY_COMPONENT_RUN_ID, "personality")
    merged = audio.merge(video, on=["seed", "fold", "subject_id"], how="outer", indicator="audio_video_merge")
    merge_counts_audio_video = merged["audio_video_merge"].value_counts().to_dict()
    if merge_counts_audio_video.get("left_only", 0) or merge_counts_audio_video.get("right_only", 0):
        raise ValueError(f"audio/video prediction keys are not aligned: {merge_counts_audio_video}")
    merged = merged.drop(columns=["audio_video_merge"])
    merged = merged.merge(personality, on=["seed", "fold", "subject_id"], how="outer", indicator="av_personality_merge")
    merge_counts_personality = merged["av_personality_merge"].value_counts().to_dict()
    if merge_counts_personality.get("left_only", 0) or merge_counts_personality.get("right_only", 0):
        raise ValueError(f"audio/video/personality prediction keys are not aligned: {merge_counts_personality}")
    merged = merged.drop(columns=["av_personality_merge"])

    labels = merged[["y_true_audio", "y_true_video", "y_true_personality"]].astype(float)
    label_mismatches = int(((labels.nunique(axis=1)) != 1).sum())
    if label_mismatches:
        raise ValueError(f"component labels disagree on {label_mismatches} rows")
    summary = {
        "audio_rows": int(len(audio)),
        "video_rows": int(len(video)),
        "personality_rows": int(len(personality)),
        "merged_rows": int(len(merged)),
        "audio_video_merge_counts": {str(k): int(v) for k, v in merge_counts_audio_video.items()},
        "av_personality_merge_counts": {str(k): int(v) for k, v in merge_counts_personality.items()},
        "label_mismatches": int(label_mismatches),
        "subject_count": int(merged["subject_id"].nunique()),
        "seed_count": int(merged["seed"].nunique()),
        "fold_count": int(merged["fold"].nunique()),
    }
    return merged.sort_values(["seed", "fold", "subject_id"], key=lambda series: series.map(lambda item: tuple(natural_key(item)) if series.name != "seed" else item)).reset_index(drop=True), summary


def load_component_predictions_from_frame(frame: pd.DataFrame, run_id: str, component_name: str) -> pd.DataFrame:
    required = {"run_id", "seed", "fold", "subject_id", "y_true", "y_pred", "y_prob"}
    missing = required - set(frame.columns)
    if missing:
        raise ValueError(f"internal component frame missing columns: {', '.join(sorted(missing))}")
    selected = frame[frame["run_id"].astype(str) == run_id].copy()
    if selected.empty:
        raise ValueError(f"internal component frame has no rows for {run_id}")
    duplicate_count = int(selected.duplicated(["seed", "fold", "subject_id"]).sum())
    if duplicate_count:
        raise ValueError(f"{run_id} has duplicate seed/fold/subject rows: {duplicate_count}")
    selected["seed"] = selected["seed"].astype(int)
    selected["fold"] = selected["fold"].astype(str)
    selected["subject_id"] = selected["subject_id"].astype(str)
    selected = selected[["seed", "fold", "subject_id", "y_true", "y_pred", "y_prob"]].rename(
        columns={
            "y_true": f"y_true_{component_name}",
            "y_pred": f"y_pred_{component_name}",
            "y_prob": f"y_prob_{component_name}",
        }
    )
    return selected


def fusion_rows(
    merged: pd.DataFrame,
    table: pd.DataFrame,
    spec: FusionSpec,
    class_count: int,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    meta_by_subject = table.set_index("subject_id", drop=False)
    rows: list[dict[str, Any]] = []
    audio_weights: list[float] = []
    video_weights: list[float] = []
    personality_weights: list[float] = []
    for _, row in merged.iterrows():
        audio_prob = parse_probability_vector(row["y_prob_audio"], class_count)
        video_prob = parse_probability_vector(row["y_prob_video"], class_count)
        personality_prob = parse_probability_vector(row["y_prob_personality"], class_count)
        if spec.run_id == LATE_SPEC.run_id:
            fused_prob = (audio_prob + video_prob + personality_prob) / 3.0
            weights = np.asarray([1.0 / 3.0, 1.0 / 3.0, 1.0 / 3.0], dtype=np.float64)
            fusion_rule = "unweighted_probability_average"
        elif spec.run_id == GATED_SPEC.run_id:
            uniform_confidence = 1.0 / float(class_count)
            confidences = np.asarray(
                [
                    max(float(np.max(audio_prob)) - uniform_confidence, 1.0e-6),
                    max(float(np.max(video_prob)) - uniform_confidence, 1.0e-6),
                    max(float(np.max(personality_prob)) - uniform_confidence, 1.0e-6),
                ],
                dtype=np.float64,
            )
            weights = confidences / float(np.sum(confidences))
            fused_prob = weights[0] * audio_prob + weights[1] * video_prob + weights[2] * personality_prob
            fusion_rule = "confidence_weighted_probability_average"
        else:
            raise ValueError(f"unsupported fusion spec: {spec.run_id}")
        audio_weights.append(float(weights[0]))
        video_weights.append(float(weights[1]))
        personality_weights.append(float(weights[2]))
        subject_meta = meta_by_subject.loc[str(row["subject_id"])]
        y_pred = int(np.argmax(fused_prob))
        rows.append(
            {
                "run_id": spec.run_id,
                "dataset": DATASET_DISPLAY,
                "modality": "AVP",
                "task": "ordinal severity prediction",
                "model": spec.model,
                "seed": int(row["seed"]),
                "fold": str(row["fold"]),
                "task_type": "ordinal_prediction",
                "subject_id": str(row["subject_id"]),
                "split": "train_oof",
                "age_group": str(subject_meta["age_group"]),
                "audio_segment_count": int(subject_meta["audio_segment_count"]),
                "video_event_count": int(subject_meta["video_event_count"]),
                "video_frame_count": int(subject_meta["video_frame_count"]),
                "y_true": int(row["y_true_audio"]),
                "y_pred": y_pred,
                "y_prob": json.dumps([float(value) for value in fused_prob], ensure_ascii=True),
                "audio_component_run_id": AUDIO_COMPONENT_RUN_ID,
                "video_component_run_id": VIDEO_COMPONENT_RUN_ID,
                "personality_component_run_id": PERSONALITY_COMPONENT_RUN_ID,
                "fusion_rule": fusion_rule,
            }
        )
    summary = {
        "run_id": spec.run_id,
        "prediction_rows": int(len(rows)),
        "mean_audio_weight": float(np.mean(audio_weights)) if audio_weights else None,
        "mean_video_weight": float(np.mean(video_weights)) if video_weights else None,
        "mean_personality_weight": float(np.mean(personality_weights)) if personality_weights else None,
        "min_audio_weight": float(np.min(audio_weights)) if audio_weights else None,
        "max_audio_weight": float(np.max(audio_weights)) if audio_weights else None,
        "min_video_weight": float(np.min(video_weights)) if video_weights else None,
        "max_video_weight": float(np.max(video_weights)) if video_weights else None,
        "min_personality_weight": float(np.min(personality_weights)) if personality_weights else None,
        "max_personality_weight": float(np.max(personality_weights)) if personality_weights else None,
    }
    return pd.DataFrame(rows), summary


def write_report(out_dir: Path, summary: dict[str, Any]) -> None:
    lines = [
        "# MPDD AVP Simple Fusion Phase 2 Baselines",
        "",
        f"Generated: `{summary['generated_at']}`",
        "",
        "## Protocol",
        "",
        "- Input interface: MPDD manifest plus cached WavLM audio and ResNet video subject features.",
        "- Early Fusion: train-fold TF-IDF personality features concatenated with standardized frozen WavLM and ResNet temporal-pooling features, then fixed multinomial logistic regression.",
        "- Late Fusion: unweighted average of audited audio, video, and internal personality component probabilities.",
        "- Gated Fusion: confidence-weighted probability averaging from component probabilities only.",
        "- The gated rule is not personality gating and uses no labels to learn sample weights.",
        "- Evaluation: five repeated stratified 5-fold subject-level out-of-fold runs over labeled MPDD train subjects.",
        "- No validation/test labels are used for hyperparameter selection or fusion weighting.",
        "- Unlabeled MPDD test rows are ignored.",
        "- No raw personality text, raw audio, raw video, source paths, or checkpoints are written to outputs.",
        "",
        "## Audit",
        "",
        f"- Runs: `{summary['runs']}`",
        f"- Subjects: `{summary['subject_count']}`",
        f"- Severity counts: `{summary['severity_counts']}`",
        f"- Audio feature columns: `{summary['audio_feature_count']}`",
        f"- Video feature columns: `{summary['video_feature_count']}`",
        f"- Personality text character count range: `{summary['personality_char_count_min']}`-`{summary['personality_char_count_max']}`",
        f"- Seeds: `{summary['seeds']}`",
        f"- Bootstrap resamples: `{summary['bootstrap_resamples']}`",
        f"- Prediction rows: `{summary['prediction_rows']}`",
        f"- Component label mismatches: `{summary['component_alignment']['label_mismatches']}`",
        f"- Raw personality text written: `{summary['raw_personality_text_written']}`",
        f"- Raw inputs written: `{summary['raw_inputs_written']}`",
        f"- Source paths written: `{summary['source_paths_written']}`",
        "",
        "## Output Files",
        "",
        "- `mpdd_avp_fusion_predictions.csv`",
        "- `mpdd_personality_component_predictions.csv`",
        "- `phase2_metrics_by_seed.csv`",
        "- `phase2_metric_summary.csv`",
        "- `mpdd_avp_fusion_run_summary.json`",
    ]
    (out_dir / "mpdd_avp_fusion_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest-path", type=Path, default=MANIFEST_PATH)
    parser.add_argument("--audio-features", type=Path, default=AUDIO_FEATURES)
    parser.add_argument("--audio-predictions", type=Path, default=AUDIO_PREDICTIONS)
    parser.add_argument("--video-features", type=Path, default=VIDEO_FEATURES)
    parser.add_argument("--video-predictions", type=Path, default=VIDEO_PREDICTIONS)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--bootstrap-resamples", type=int, default=1000)
    args = parser.parse_args()

    args.out_dir.mkdir(parents=True, exist_ok=True)
    table, audio_columns, video_columns = build_fusion_table(
        args.manifest_path,
        args.audio_features,
        args.video_features,
    )
    early_predictions, early_fold_summaries = run_early_fusion(table, audio_columns, video_columns)
    personality_predictions, personality_fold_summaries = run_personality_component(table)
    personality_path = args.out_dir / "mpdd_personality_component_predictions.csv"
    personality_predictions.to_csv(personality_path, index=False)

    class_count = int(table["severity_label"].astype(int).max()) + 1
    merged_components, component_alignment = merge_components(
        args.audio_predictions,
        args.video_predictions,
        personality_predictions,
    )
    late_predictions, late_summary = fusion_rows(merged_components, table, LATE_SPEC, class_count)
    gated_predictions, gated_summary = fusion_rows(merged_components, table, GATED_SPEC, class_count)

    predictions_frame = pd.concat([early_predictions, late_predictions, gated_predictions], ignore_index=True)
    predictions_path = args.out_dir / "mpdd_avp_fusion_predictions.csv"
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
        "manifest_path": str(args.manifest_path),
        "runs": [EARLY_SPEC.run_id, LATE_SPEC.run_id, GATED_SPEC.run_id],
        "source_runs": [AUDIO_COMPONENT_RUN_ID, VIDEO_COMPONENT_RUN_ID, PERSONALITY_COMPONENT_RUN_ID],
        "seeds": SEEDS,
        "bootstrap_resamples": int(args.bootstrap_resamples),
        "subject_count": int(table["subject_id"].nunique()),
        "age_group_counts": {str(k): int(v) for k, v in table["age_group"].value_counts().sort_index().items()},
        "severity_counts": {str(k): int(v) for k, v in table["severity_label"].astype(int).value_counts().sort_index().items()},
        "audio_feature_count": int(len(audio_columns)),
        "video_feature_count": int(len(video_columns)),
        "personality_char_count_min": int(table["personality_char_count"].min()),
        "personality_char_count_max": int(table["personality_char_count"].max()),
        "prediction_rows": int(len(predictions_frame)),
        "personality_component_rows": int(len(personality_predictions)),
        "early_summary": {
            "run_id": EARLY_SPEC.run_id,
            "prediction_rows": int(len(early_predictions)),
            "fold_summaries": early_fold_summaries,
        },
        "personality_component_summary": {
            "run_id": PERSONALITY_COMPONENT_RUN_ID,
            "prediction_rows": int(len(personality_predictions)),
            "fold_summaries": personality_fold_summaries,
        },
        "component_alignment": component_alignment,
        "late_summary": late_summary,
        "gated_summary": gated_summary,
        "no_test_split_used": True,
        "validation_label_tuning_used": False,
        "fusion_weight_label_tuning_used": False,
        "personality_gating_used": False,
        "raw_personality_text_written": False,
        "raw_inputs_written": False,
        "source_paths_written": False,
        "checkpoints_written": False,
    }
    (args.out_dir / "mpdd_avp_fusion_run_summary.json").write_text(
        json.dumps(run_summary, indent=2, ensure_ascii=True, sort_keys=True),
        encoding="utf-8",
    )
    write_report(args.out_dir, run_summary)
    print(f"Wrote {predictions_path}")
    print(f"Wrote {args.out_dir / 'phase2_metric_summary.csv'}")


if __name__ == "__main__":
    main()
