#!/usr/bin/env python3
"""Phase 3 MPDD individual-difference and shortcut diagnostics.

This diagnostic script uses labeled MPDD train subjects only. It writes
subject-level out-of-fold predictions and summary diagnostics, but never writes
raw personality text, raw audio/video/IMU arrays, or manifest source paths.
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
from typing import Any, Callable, Iterable


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

from phase2_metrics import (
    bootstrap_ci,
    compute_metrics,
    multiclass_ece_and_brier,
    parse_probability_vector,
    safe_float,
    spearman,
)


ROOT = Path(__file__).resolve().parents[1]
MAIN_CHECKOUT = Path("/root/autodl-tmp")
DATASET_DISPLAY = "MPDD-AVG-2026"
MANIFEST_PATH = ROOT / "datasets" / "manifests" / "mpdd_avg_2026_subjects.csv"
DEFAULT_OUT_DIR = ROOT / "analysis" / "phase3_diagnostics" / "mpdd_individual_differences"
SEEDS = [0, 1, 2, 3, 4]
BOOTSTRAP_SEED = 20260805
FIXED_LOGISTIC_C = 1.0
MAX_GAIT_CHANNELS = 12
TRAITS = ["extraversion", "agreeableness", "openness", "neuroticism", "conscientiousness"]
CLASS_LABELS = [0, 1, 2]


@dataclass(frozen=True)
class RunSpec:
    run_id: str
    modality: str
    model: str
    feature_family: str
    control_condition: str


DEMOGRAPHICS_SPEC = RunSpec(
    "mpdd_demographics_age_severity_logistic",
    "Demographics",
    "age group one-hot + Logistic",
    "age_group",
    "observed_age",
)
SHUFFLED_AGE_SPEC = RunSpec(
    "mpdd_demographics_shuffled_age_severity_logistic",
    "Demographics",
    "shuffled age group one-hot + Logistic",
    "age_group",
    "shuffled_age",
)
PERSONALITY_SPEC = RunSpec(
    "mpdd_personality_severity_tfidf_logistic_phase3",
    "Personality",
    "personality TF-IDF + Logistic",
    "personality_tfidf",
    "observed_personality",
)
SHUFFLED_PERSONALITY_SPEC = RunSpec(
    "mpdd_personality_shuffled_severity_tfidf_logistic",
    "Personality",
    "shuffled personality TF-IDF + Logistic",
    "personality_tfidf",
    "shuffled_personality",
)
PERSONALITY_COUNTERFACTUAL_SPEC = RunSpec(
    "mpdd_personality_counterfactual_age_swap",
    "Personality",
    "personality TF-IDF + Logistic with age-group counterfactual swap",
    "personality_tfidf",
    "counterfactual_age_group_swap",
)
AV_SPEC = RunSpec(
    "mpdd_av_severity_early_fusion",
    "Audio+Video",
    "WavLM audio + ResNet video early fusion Logistic",
    "audio_video",
    "observed_audio_video",
)
AVP_SPEC = RunSpec(
    "mpdd_avp_severity_early_fusion_phase3",
    "Audio+Video+Personality",
    "WavLM audio + ResNet video + personality TF-IDF early fusion Logistic",
    "audio_video_personality",
    "observed_audio_video_personality",
)
AVP_SHUFFLED_PERSONALITY_SPEC = RunSpec(
    "mpdd_avp_shuffled_personality_early_fusion",
    "Audio+Video+Personality",
    "WavLM audio + ResNet video + shuffled personality TF-IDF early fusion Logistic",
    "audio_video_personality",
    "shuffled_personality",
)


PHASE2_REFERENCE_PREDICTIONS = {
    "mpdd_audio_wavlm/mpdd_audio_wavlm_predictions.csv": [
        "mpdd_audio_phq9_wavlm_linear",
        "mpdd_audio_severity_wavlm_mlp",
    ],
    "mpdd_video_features/mpdd_video_features_predictions.csv": [
        "mpdd_video_severity_temporal_pooling",
    ],
    "mpdd_video_openface/mpdd_openface_video_predictions.csv": [
        "mpdd_video_severity_openface_mlp",
    ],
    "mpdd_avp_fusion/mpdd_avp_fusion_predictions.csv": [
        "mpdd_avp_severity_early_fusion",
        "mpdd_avp_severity_late_fusion",
        "mpdd_avp_severity_gated_fusion",
    ],
    "mpdd_avp_fusion/mpdd_personality_component_predictions.csv": [
        "mpdd_personality_severity_tfidf_logistic_internal",
    ],
    "mpdd_gait_stats/mpdd_gait_stats_predictions.csv": [
        "mpdd_gait_binary_stats_logistic",
        "mpdd_gait_binary_stats_xgboost",
    ],
    "mpdd_imu_temporal/mpdd_imu_temporal_predictions.csv": [
        "mpdd_gait_severity_imu_temporal_mlp",
    ],
}

SUBGROUP_RUN_IDS = {
    DEMOGRAPHICS_SPEC.run_id,
    SHUFFLED_AGE_SPEC.run_id,
    PERSONALITY_SPEC.run_id,
    SHUFFLED_PERSONALITY_SPEC.run_id,
    PERSONALITY_COUNTERFACTUAL_SPEC.run_id,
    AV_SPEC.run_id,
    AVP_SPEC.run_id,
    AVP_SHUFFLED_PERSONALITY_SPEC.run_id,
}
SUBGROUP_CI_GROUP_TYPES = {"age_group", "true_severity"}
SUBGROUP_CI_METRICS = {"Accuracy", "ECE", "Ordinal MAE", "Macro-F1", "QWK"}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def natural_key(value: Any) -> list[Any]:
    return [int(part) if part.isdigit() else part for part in re.split(r"(\d+)", str(value))]


def stable_hash(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:16]


def as_ascii_json(data: Any) -> str:
    return json.dumps(data, ensure_ascii=True, sort_keys=True)


def phase2_cache_candidates() -> list[tuple[str, Path]]:
    return [
        ("current_worktree", ROOT / "analysis" / "phase2_baselines"),
        ("main_checkout_read_only", MAIN_CHECKOUT / "analysis" / "phase2_baselines"),
    ]


def resolve_phase2_artifact(relative_path: str) -> tuple[Path, str]:
    for source_scope, root in phase2_cache_candidates():
        path = root / relative_path
        if path.exists():
            return path, source_scope
    raise FileNotFoundError(f"missing Phase 2 artifact: {relative_path}")


def read_manifest_subjects(manifest_path: Path) -> pd.DataFrame:
    manifest = pd.read_csv(manifest_path)
    required = {
        "subject_id",
        "personality",
        "phq9_total",
        "severity_label",
        "binary_label",
        "age",
        "gender",
        "health_condition",
        "official_split",
        "file_valid",
        "gait_path",
    }
    missing = required - set(manifest.columns)
    if missing:
        raise ValueError(f"MPDD manifest missing columns: {', '.join(sorted(missing))}")

    rows = manifest[
        manifest["file_valid"].fillna(False).astype(bool)
        & manifest["official_split"].eq("train")
        & manifest["phq9_total"].notna()
        & manifest["severity_label"].notna()
        & manifest["binary_label"].notna()
    ].copy()
    if rows.empty:
        raise ValueError("no labeled MPDD train subjects")

    subjects: list[dict[str, Any]] = []
    for subject_id, group in rows.groupby("subject_id", sort=False):
        phq_values = group["phq9_total"].dropna().unique()
        severity_values = group["severity_label"].dropna().unique()
        binary_values = group["binary_label"].dropna().unique()
        if len(phq_values) != 1 or len(severity_values) != 1 or len(binary_values) != 1:
            raise ValueError(f"{subject_id} has inconsistent labels")
        personality_values = group["personality"].dropna().astype(str).unique()
        personality_text = str(personality_values[0]).strip() if len(personality_values) else ""
        age_values = group["age"].dropna().astype(str).unique()
        gender_values = group["gender"].dropna().astype(str).unique()
        health_values = group["health_condition"].dropna().astype(str).unique()
        gait_values = group["gait_path"].dropna().astype(str).unique()
        subjects.append(
            {
                "subject_id": str(subject_id),
                "age_group": str(age_values[0]).strip() if len(age_values) else "missing",
                "gender_group": str(gender_values[0]).strip() if len(gender_values) else "missing",
                "health_group": str(health_values[0]).strip() if len(health_values) else "missing",
                "phq9_total": float(phq_values[0]),
                "severity_label": int(severity_values[0]),
                "binary_label": int(binary_values[0]),
                "personality_text": personality_text,
                "personality_available": bool(personality_text),
                "personality_char_count": int(len(personality_text)),
                "personality_hash": stable_hash(personality_text) if personality_text else "",
                "gait_path_internal": str(gait_values[0]) if len(gait_values) else "",
                "gait_available": bool(len(gait_values)),
            }
        )
    table = (
        pd.DataFrame(subjects)
        .sort_values("subject_id", key=lambda series: series.map(lambda item: tuple(natural_key(item))))
        .reset_index(drop=True)
    )
    return add_personality_bins(table)


def parse_trait_numeric(text: str, trait: str) -> float | None:
    patterns = [
        rf"score\s+of\s+(?P<value>\d+(?:\.\d+)?)\s+for\s+{trait}",
        rf"{trait}\s+score\s+(?:of\s+|is\s+|was\s+|=|:)?\s*(?P<value>\d+(?:\.\d+)?)",
        rf"{trait}\s*,?\s*(?:with\s+)?(?:a\s+)?score\s+of\s+(?P<value>\d+(?:\.\d+)?)",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            return float(match.group("value"))
    return None


def normalize_descriptor(value: str) -> str | None:
    lowered = value.lower().strip()
    if lowered in {"low", "lower"}:
        return "low"
    if lowered in {"moderate", "balanced", "average"}:
        return "mid"
    if lowered in {"high", "higher"}:
        return "high"
    return None


def parse_trait_descriptor(text: str, trait: str) -> str:
    descriptor = r"(?:relatively\s+|particularly\s+|rather\s+|very\s+)?(?P<value>low|lower|moderate|balanced|average|high|higher)"
    patterns = [
        rf"{descriptor}\s+{trait}\s+score",
        rf"{trait}\s+score\s+(?:is|are|was|were)?\s*{descriptor}",
        rf"{trait}\s+score.*?\b{descriptor}\b",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            normalized = normalize_descriptor(match.group("value"))
            if normalized:
                return normalized
    return "unknown"


def parse_financial_stress_bin(text: str) -> str:
    lowered = text.lower()
    if "no financial stress" in lowered or "financial stress is categorized as no" in lowered:
        return "none"
    if "mild" in lowered and "financial stress" in lowered:
        return "mild_or_low"
    if "low level of financial stress" in lowered or "financial stress score" in lowered and "low" in lowered:
        return "mild_or_low"
    if "moderate" in lowered and "financial stress" in lowered:
        return "moderate"
    if ("high" in lowered or "severe" in lowered) and "financial stress" in lowered:
        return "high_or_severe"
    if "financial stress" in lowered:
        return "mentioned_unclear"
    return "unknown"


def add_personality_bins(table: pd.DataFrame) -> pd.DataFrame:
    frame = table.copy()
    for trait in TRAITS:
        numeric_values: list[float | None] = []
        descriptor_values: list[str] = []
        for text in frame["personality_text"].astype(str):
            numeric_values.append(parse_trait_numeric(text, trait))
            descriptor_values.append(parse_trait_descriptor(text, trait))
        frame[f"{trait}_score"] = numeric_values
        frame[f"{trait}_descriptor_bin"] = descriptor_values
        numeric = pd.to_numeric(frame[f"{trait}_score"], errors="coerce")
        numeric_bin = pd.Series(["unknown"] * len(frame), index=frame.index, dtype=object)
        if int(numeric.notna().sum()) >= 20 and int(numeric.nunique(dropna=True)) >= 3:
            try:
                numeric_bin.loc[numeric.notna()] = pd.qcut(
                    numeric[numeric.notna()],
                    q=3,
                    labels=["low", "mid", "high"],
                    duplicates="drop",
                ).astype(str)
            except ValueError:
                numeric_bin.loc[numeric.notna()] = frame.loc[numeric.notna(), f"{trait}_descriptor_bin"]
        frame[f"{trait}_bin"] = numeric_bin.where(numeric_bin.ne("unknown"), frame[f"{trait}_descriptor_bin"])
    frame["financial_stress_bin"] = [parse_financial_stress_bin(text) for text in frame["personality_text"].astype(str)]
    return frame


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


def classifier(seed: int) -> LogisticRegression:
    return LogisticRegression(
        C=FIXED_LOGISTIC_C,
        class_weight="balanced",
        max_iter=1000,
        random_state=seed,
        solver="lbfgs",
    )


def align_probabilities(raw_prob: np.ndarray, local_classes: np.ndarray) -> np.ndarray:
    probabilities = np.zeros((raw_prob.shape[0], len(CLASS_LABELS)), dtype=np.float64)
    for local_idx, class_value in enumerate(local_classes):
        if int(class_value) in CLASS_LABELS:
            probabilities[:, int(class_value)] = raw_prob[:, local_idx]
    totals = probabilities.sum(axis=1, keepdims=True)
    totals[totals <= 0.0] = 1.0
    return np.clip(probabilities / totals, 0.0, 1.0)


def age_matrix(values: Iterable[Any]) -> pd.DataFrame:
    normalized = [str(value).strip().lower() if str(value).strip() else "missing" for value in values]
    return pd.get_dummies(pd.Series(normalized), prefix="age").reindex(
        columns=["age_elder", "age_young", "age_missing"],
        fill_value=0,
    )


def load_feature_table(
    relative_path: str,
    subjects: set[str],
    prefix: str,
    required_metadata: set[str],
) -> tuple[pd.DataFrame, list[str], str]:
    path, source_scope = resolve_phase2_artifact(relative_path)
    frame = pd.read_csv(path)
    if "subject_id" not in frame.columns:
        raise ValueError(f"{relative_path} missing subject_id")
    missing_metadata = required_metadata - set(frame.columns)
    if missing_metadata:
        raise ValueError(f"{relative_path} missing columns: {', '.join(sorted(missing_metadata))}")
    frame["subject_id"] = frame["subject_id"].astype(str)
    selected = frame[frame["subject_id"].isin(subjects)].copy()
    missing_subjects = sorted(subjects - set(selected["subject_id"]), key=natural_key)
    if missing_subjects:
        raise ValueError(f"{relative_path} missing feature rows for {len(missing_subjects)} subjects")
    feature_columns = [column for column in selected.columns if column.startswith(prefix)]
    if not feature_columns:
        raise ValueError(f"{relative_path} has no feature columns with prefix {prefix}")
    selected = (
        selected.sort_values("subject_id", key=lambda series: series.map(lambda item: tuple(natural_key(item))))
        .reset_index(drop=True)
    )
    return selected, feature_columns, source_scope


def build_model_table(subjects: pd.DataFrame) -> tuple[pd.DataFrame, list[str], list[str], list[dict[str, Any]]]:
    subject_ids = set(subjects["subject_id"].astype(str))
    audio, audio_columns, audio_scope = load_feature_table(
        "mpdd_audio_wavlm/mpdd_wavlm_subject_features.csv",
        subject_ids,
        "wavlm_",
        {"audio_segment_count", "duration_seconds_sum", "chunk_count_sum"},
    )
    video, video_columns, video_scope = load_feature_table(
        "mpdd_video_features/mpdd_resnet_video_subject_features.csv",
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
        raise ValueError(f"feature merge produced {len(table)} rows for {len(subjects)} subjects")
    table = (
        table.sort_values("subject_id", key=lambda series: series.map(lambda item: tuple(natural_key(item))))
        .reset_index(drop=True)
    )
    inventory = [
        {
            "artifact": "mpdd_wavlm_subject_features",
            "source_scope": audio_scope,
            "row_count": int(len(audio)),
            "feature_count": int(len(audio_columns)),
        },
        {
            "artifact": "mpdd_resnet_video_subject_features",
            "source_scope": video_scope,
            "row_count": int(len(video)),
            "feature_count": int(len(video_columns)),
        },
    ]
    return table, audio_columns, video_columns, inventory


def probability_json(probabilities: np.ndarray, idx: int) -> str:
    return json.dumps([float(value) for value in probabilities[idx]], ensure_ascii=True)


def prediction_meta(spec: RunSpec, seed: int, fold: int, row: pd.Series) -> dict[str, Any]:
    return {
        "run_id": spec.run_id,
        "dataset": DATASET_DISPLAY,
        "modality": spec.modality,
        "task": "ordinal severity prediction",
        "model": spec.model,
        "seed": int(seed),
        "fold": int(fold),
        "task_type": "ordinal_prediction",
        "subject_id": str(row["subject_id"]),
        "split": "train_oof",
        "age_group": str(row["age_group"]),
        "feature_family": spec.feature_family,
        "control_condition": spec.control_condition,
        "y_true": int(row["severity_label"]),
    }


def permute_values(values: pd.Series, seed: int, fold: int, salt: str) -> np.ndarray:
    rng_seed = abs(hash((seed, fold, salt))) % (2**32)
    rng = np.random.default_rng(rng_seed)
    arr = values.to_numpy(dtype=object).copy()
    if arr.size > 1:
        rng.shuffle(arr)
    return arr


def counterfactual_age_swap_texts(train: pd.DataFrame, heldout: pd.DataFrame, seed: int, fold: int) -> tuple[list[str], list[str]]:
    replacement_texts: list[str] = []
    replacement_ages: list[str] = []
    for idx, row in heldout.reset_index(drop=True).iterrows():
        age = str(row["age_group"])
        candidates = train[train["age_group"].astype(str) != age]
        if candidates.empty:
            candidates = train
        ordered = candidates.sort_values("subject_id", key=lambda series: series.map(lambda item: tuple(natural_key(item)))).reset_index(drop=True)
        replacement_idx = (idx + seed + fold) % len(ordered)
        replacement_texts.append(str(ordered.loc[replacement_idx, "personality_text"]))
        replacement_ages.append(str(ordered.loc[replacement_idx, "age_group"]))
    return replacement_texts, replacement_ages


def add_model_predictions(
    predictions: list[dict[str, Any]],
    spec: RunSpec,
    seed: int,
    fold: int,
    heldout: pd.DataFrame,
    y_pred: np.ndarray,
    probabilities: np.ndarray,
    extra_columns: dict[str, list[Any]] | None = None,
) -> None:
    extra_columns = extra_columns or {}
    for idx, row in heldout.reset_index(drop=True).iterrows():
        extra = {column: values[idx] for column, values in extra_columns.items()}
        predictions.append(
            {
                **prediction_meta(spec, seed, fold, row),
                **extra,
                "y_pred": int(y_pred[idx]),
                "y_prob": probability_json(probabilities, idx),
            }
        )


def run_phase3_oof(
    table: pd.DataFrame,
    audio_columns: list[str],
    video_columns: list[str],
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    labels = table["severity_label"].to_numpy(dtype=np.int64)
    dense_columns = audio_columns + video_columns
    predictions: list[dict[str, Any]] = []
    fold_summaries: list[dict[str, Any]] = []
    counterfactual_rows: list[dict[str, Any]] = []
    for seed in SEEDS:
        folds = StratifiedKFold(n_splits=5, shuffle=True, random_state=seed)
        for fold, (train_idx, heldout_idx) in enumerate(folds.split(table, labels), start=1):
            train = table.iloc[train_idx].reset_index(drop=True)
            heldout = table.iloc[heldout_idx].reset_index(drop=True)

            for spec, train_age, heldout_age in [
                (DEMOGRAPHICS_SPEC, train["age_group"], heldout["age_group"]),
                (
                    SHUFFLED_AGE_SPEC,
                    pd.Series(permute_values(train["age_group"], seed, fold, "train_age")),
                    pd.Series(permute_values(heldout["age_group"], seed, fold, "heldout_age")),
                ),
            ]:
                x_train = age_matrix(train_age)
                x_heldout = age_matrix(heldout_age)
                model = classifier(seed + fold)
                model.fit(x_train, train["severity_label"].astype(int))
                probabilities = align_probabilities(model.predict_proba(x_heldout), model.classes_)
                y_pred = np.argmax(probabilities, axis=1)
                add_model_predictions(predictions, spec, seed, fold, heldout, y_pred, probabilities)
                fold_summaries.append(
                    {
                        "run_id": spec.run_id,
                        "seed": int(seed),
                        "fold": int(fold),
                        "train_subjects": int(len(train)),
                        "heldout_subjects": int(len(heldout)),
                        "dense_feature_count": int(x_train.shape[1]),
                        "sparse_feature_count": 0,
                    }
                )

            actual_tfidf = personality_vectorizer()
            actual_personality_train = actual_tfidf.fit_transform(train["personality_text"].fillna(""))
            actual_personality_heldout = actual_tfidf.transform(heldout["personality_text"].fillna(""))
            personality_model = classifier(seed + fold)
            personality_model.fit(actual_personality_train, train["severity_label"].astype(int))
            personality_prob = align_probabilities(personality_model.predict_proba(actual_personality_heldout), personality_model.classes_)
            personality_pred = np.argmax(personality_prob, axis=1)
            add_model_predictions(predictions, PERSONALITY_SPEC, seed, fold, heldout, personality_pred, personality_prob)
            fold_summaries.append(
                {
                    "run_id": PERSONALITY_SPEC.run_id,
                    "seed": int(seed),
                    "fold": int(fold),
                    "train_subjects": int(len(train)),
                    "heldout_subjects": int(len(heldout)),
                    "dense_feature_count": 0,
                    "sparse_feature_count": int(actual_personality_train.shape[1]),
                }
            )

            counterfactual_texts, counterfactual_ages = counterfactual_age_swap_texts(train, heldout, seed, fold)
            counterfactual_heldout = actual_tfidf.transform(counterfactual_texts)
            counter_prob = align_probabilities(personality_model.predict_proba(counterfactual_heldout), personality_model.classes_)
            counter_pred = np.argmax(counter_prob, axis=1)
            add_model_predictions(
                predictions,
                PERSONALITY_COUNTERFACTUAL_SPEC,
                seed,
                fold,
                heldout,
                counter_pred,
                counter_prob,
                {"counterfactual_age_group": counterfactual_ages},
            )
            for idx, row in heldout.reset_index(drop=True).iterrows():
                actual_expected = float(np.dot(personality_prob[idx], np.asarray(CLASS_LABELS, dtype=np.float64)))
                counter_expected = float(np.dot(counter_prob[idx], np.asarray(CLASS_LABELS, dtype=np.float64)))
                counterfactual_rows.append(
                    {
                        "seed": int(seed),
                        "fold": int(fold),
                        "subject_id": str(row["subject_id"]),
                        "age_group": str(row["age_group"]),
                        "counterfactual_age_group": str(counterfactual_ages[idx]),
                        "true_severity": int(row["severity_label"]),
                        "actual_pred": int(personality_pred[idx]),
                        "counterfactual_pred": int(counter_pred[idx]),
                        "changed_pred": bool(int(personality_pred[idx]) != int(counter_pred[idx])),
                        "actual_expected_severity": actual_expected,
                        "counterfactual_expected_severity": counter_expected,
                        "delta_expected_severity": counter_expected - actual_expected,
                    }
                )

            shuffled_train_text = pd.Series(permute_values(train["personality_text"], seed, fold, "train_personality"))
            shuffled_heldout_text = pd.Series(permute_values(heldout["personality_text"], seed, fold, "heldout_personality"))
            shuffled_tfidf = personality_vectorizer()
            shuffled_personality_train = shuffled_tfidf.fit_transform(shuffled_train_text.fillna(""))
            shuffled_personality_heldout = shuffled_tfidf.transform(shuffled_heldout_text.fillna(""))
            shuffled_model = classifier(seed + fold)
            shuffled_model.fit(shuffled_personality_train, train["severity_label"].astype(int))
            shuffled_prob = align_probabilities(shuffled_model.predict_proba(shuffled_personality_heldout), shuffled_model.classes_)
            shuffled_pred = np.argmax(shuffled_prob, axis=1)
            add_model_predictions(predictions, SHUFFLED_PERSONALITY_SPEC, seed, fold, heldout, shuffled_pred, shuffled_prob)
            fold_summaries.append(
                {
                    "run_id": SHUFFLED_PERSONALITY_SPEC.run_id,
                    "seed": int(seed),
                    "fold": int(fold),
                    "train_subjects": int(len(train)),
                    "heldout_subjects": int(len(heldout)),
                    "dense_feature_count": 0,
                    "sparse_feature_count": int(shuffled_personality_train.shape[1]),
                }
            )

            imputer = SimpleImputer(strategy="median")
            scaler = StandardScaler()
            dense_train = scaler.fit_transform(imputer.fit_transform(train[dense_columns]))
            dense_heldout = scaler.transform(imputer.transform(heldout[dense_columns]))

            av_model = classifier(seed + fold)
            av_model.fit(dense_train, train["severity_label"].astype(int))
            av_prob = align_probabilities(av_model.predict_proba(dense_heldout), av_model.classes_)
            av_pred = np.argmax(av_prob, axis=1)
            add_model_predictions(predictions, AV_SPEC, seed, fold, heldout, av_pred, av_prob)
            fold_summaries.append(
                {
                    "run_id": AV_SPEC.run_id,
                    "seed": int(seed),
                    "fold": int(fold),
                    "train_subjects": int(len(train)),
                    "heldout_subjects": int(len(heldout)),
                    "dense_feature_count": int(len(dense_columns)),
                    "sparse_feature_count": 0,
                }
            )

            avp_train = sparse.hstack([sparse.csr_matrix(dense_train), actual_personality_train], format="csr")
            avp_heldout = sparse.hstack([sparse.csr_matrix(dense_heldout), actual_personality_heldout], format="csr")
            avp_model = classifier(seed + fold)
            avp_model.fit(avp_train, train["severity_label"].astype(int))
            avp_prob = align_probabilities(avp_model.predict_proba(avp_heldout), avp_model.classes_)
            avp_pred = np.argmax(avp_prob, axis=1)
            add_model_predictions(predictions, AVP_SPEC, seed, fold, heldout, avp_pred, avp_prob)
            fold_summaries.append(
                {
                    "run_id": AVP_SPEC.run_id,
                    "seed": int(seed),
                    "fold": int(fold),
                    "train_subjects": int(len(train)),
                    "heldout_subjects": int(len(heldout)),
                    "dense_feature_count": int(len(dense_columns)),
                    "sparse_feature_count": int(actual_personality_train.shape[1]),
                }
            )

            shuffled_avp_train = sparse.hstack([sparse.csr_matrix(dense_train), shuffled_personality_train], format="csr")
            shuffled_avp_heldout = sparse.hstack([sparse.csr_matrix(dense_heldout), shuffled_personality_heldout], format="csr")
            shuffled_avp_model = classifier(seed + fold)
            shuffled_avp_model.fit(shuffled_avp_train, train["severity_label"].astype(int))
            shuffled_avp_prob = align_probabilities(shuffled_avp_model.predict_proba(shuffled_avp_heldout), shuffled_avp_model.classes_)
            shuffled_avp_pred = np.argmax(shuffled_avp_prob, axis=1)
            add_model_predictions(
                predictions,
                AVP_SHUFFLED_PERSONALITY_SPEC,
                seed,
                fold,
                heldout,
                shuffled_avp_pred,
                shuffled_avp_prob,
            )
            fold_summaries.append(
                {
                    "run_id": AVP_SHUFFLED_PERSONALITY_SPEC.run_id,
                    "seed": int(seed),
                    "fold": int(fold),
                    "train_subjects": int(len(train)),
                    "heldout_subjects": int(len(heldout)),
                    "dense_feature_count": int(len(dense_columns)),
                    "sparse_feature_count": int(shuffled_personality_train.shape[1]),
                }
            )
    return pd.DataFrame(predictions), pd.DataFrame(fold_summaries), pd.DataFrame(counterfactual_rows)


def load_phase2_reference_predictions() -> tuple[pd.DataFrame, pd.DataFrame]:
    frames: list[pd.DataFrame] = []
    inventory: list[dict[str, Any]] = []
    for relative_path, run_ids in PHASE2_REFERENCE_PREDICTIONS.items():
        try:
            path, source_scope = resolve_phase2_artifact(relative_path)
        except FileNotFoundError:
            inventory.append(
                {
                    "artifact": relative_path.replace("/", "__").replace(".csv", ""),
                    "source_scope": "missing",
                    "status": "missing",
                    "row_count": 0,
                    "selected_rows": 0,
                }
            )
            continue
        frame = pd.read_csv(path)
        selected = frame[frame["run_id"].astype(str).isin(run_ids)].copy()
        selected["source_family"] = "phase2_completed_predictions"
        selected["feature_family"] = selected["modality"].astype(str).str.lower().str.replace("+", "_", regex=False)
        selected["control_condition"] = "phase2_reference"
        frames.append(selected)
        inventory.append(
            {
                "artifact": relative_path.replace("/", "__").replace(".csv", ""),
                "source_scope": source_scope,
                "status": "available",
                "row_count": int(len(frame)),
                "selected_rows": int(len(selected)),
                "run_count": int(selected["run_id"].nunique()) if not selected.empty else 0,
            }
        )
    combined = pd.concat(frames, ignore_index=True, sort=False) if frames else pd.DataFrame()
    return combined, pd.DataFrame(inventory)


def add_subject_groups(predictions: pd.DataFrame, subjects: pd.DataFrame) -> pd.DataFrame:
    group_cols = [
        "subject_id",
        "age_group",
        "gender_group",
        "health_group",
        "phq9_total",
        "severity_label",
        "binary_label",
        "financial_stress_bin",
    ] + [f"{trait}_bin" for trait in TRAITS]
    meta = subjects[group_cols].copy()
    frame = predictions.copy()
    frame["subject_id"] = frame["subject_id"].astype(str)
    frame = frame.merge(meta, on="subject_id", how="left", suffixes=("", "_manifest"))
    if "age_group_manifest" in frame.columns:
        frame["age_group"] = frame["age_group"].fillna(frame["age_group_manifest"])
        frame = frame.drop(columns=["age_group_manifest"])
    return frame


def add_prediction_diagnostics(predictions: pd.DataFrame) -> pd.DataFrame:
    frame = predictions.copy()
    accuracy_values: list[float | None] = []
    confidence_values: list[float | None] = []
    true_probability_values: list[float | None] = []
    bias_values: list[float | None] = []
    for _, row in frame.iterrows():
        y_true = safe_float(row.get("y_true"))
        y_pred = safe_float(row.get("y_pred"))
        accuracy_values.append(1.0 if y_true is not None and y_pred is not None and int(y_true) == int(y_pred) else 0.0)
        bias_values.append(safe_float(float(y_pred - y_true)) if y_true is not None and y_pred is not None else None)
        task_type = str(row.get("task_type", ""))
        score = safe_float(row.get("y_score")) if "y_score" in frame.columns else None
        if task_type == "binary_classification" and score is not None:
            score = min(max(score, 0.0), 1.0)
            confidence_values.append(max(score, 1.0 - score))
            true_probability_values.append(score if y_true is not None and int(y_true) == 1 else 1.0 - score)
            continue
        probs = parse_probability_vector(row.get("y_prob"))
        if probs is None:
            confidence_values.append(None)
            true_probability_values.append(None)
            continue
        arr = np.asarray(probs, dtype=np.float64)
        total = float(np.sum(arr))
        if arr.size == 0 or total <= 0.0 or not np.all(np.isfinite(arr)):
            confidence_values.append(None)
            true_probability_values.append(None)
            continue
        arr = arr / total
        confidence_values.append(safe_float(float(np.max(arr))))
        if y_true is None or int(y_true) < 0 or int(y_true) >= arr.size:
            true_probability_values.append(None)
        else:
            true_probability_values.append(safe_float(float(arr[int(y_true)])))
    frame["accuracy_value"] = accuracy_values
    frame["prediction_confidence"] = confidence_values
    frame["true_label_probability"] = true_probability_values
    frame["prediction_bias"] = bias_values
    return frame


def expected_ordinal_value(probability_value: Any) -> float | None:
    probs = parse_probability_vector(probability_value)
    if probs is None:
        return None
    arr = np.asarray(probs, dtype=np.float64)
    if arr.size == 0:
        return None
    arr = arr / float(np.sum(arr)) if float(np.sum(arr)) > 0.0 else arr
    labels = np.arange(arr.size, dtype=np.float64)
    return safe_float(float(np.dot(arr, labels)))


def prediction_confidence(row: pd.Series) -> float | None:
    task_type = str(row.get("task_type", ""))
    if task_type == "binary_classification" and "y_score" in row and pd.notna(row.get("y_score")):
        score = safe_float(row.get("y_score"))
        if score is None:
            return None
        score = min(max(score, 0.0), 1.0)
        return max(score, 1.0 - score)
    probs = parse_probability_vector(row.get("y_prob"))
    if probs is None:
        return None
    arr = np.asarray(probs, dtype=np.float64)
    if arr.size == 0 or not np.all(np.isfinite(arr)):
        return None
    total = float(np.sum(arr))
    if total <= 0.0:
        return None
    return safe_float(float(np.max(arr / total)))


def true_label_probability(row: pd.Series) -> float | None:
    y_true = safe_float(row.get("y_true"))
    if y_true is None:
        return None
    task_type = str(row.get("task_type", ""))
    if task_type == "binary_classification" and "y_score" in row and pd.notna(row.get("y_score")):
        score = safe_float(row.get("y_score"))
        if score is None:
            return None
        score = min(max(score, 0.0), 1.0)
        return score if int(y_true) == 1 else 1.0 - score
    probs = parse_probability_vector(row.get("y_prob"))
    if probs is None:
        return None
    idx = int(y_true)
    if idx < 0 or idx >= len(probs):
        return None
    total = float(sum(probs))
    if total <= 0.0:
        return None
    return safe_float(float(probs[idx] / total))


def group_metric_value(frame: pd.DataFrame, metric: str) -> float | None:
    if frame.empty:
        return None
    if metric == "Accuracy":
        if "accuracy_value" in frame.columns:
            return safe_float(float(pd.to_numeric(frame["accuracy_value"], errors="coerce").mean()))
        return safe_float(float(np.mean(frame["y_true"].astype(int) == frame["y_pred"].astype(int))))
    if metric == "Mean Confidence":
        if "prediction_confidence" in frame.columns:
            values = pd.to_numeric(frame["prediction_confidence"], errors="coerce").dropna()
            return safe_float(float(values.mean())) if len(values) else None
        values = [prediction_confidence(row) for _, row in frame.iterrows()]
        values = [value for value in values if value is not None]
        return safe_float(float(np.mean(values))) if values else None
    if metric == "Calibration Gap":
        accuracy = group_metric_value(frame, "Accuracy")
        confidence = group_metric_value(frame, "Mean Confidence")
        if accuracy is None or confidence is None:
            return None
        return safe_float(confidence - accuracy)
    if metric == "True Label Probability":
        if "true_label_probability" in frame.columns:
            values = pd.to_numeric(frame["true_label_probability"], errors="coerce").dropna()
            return safe_float(float(values.mean())) if len(values) else None
        values = [true_label_probability(row) for _, row in frame.iterrows()]
        values = [value for value in values if value is not None]
        return safe_float(float(np.mean(values))) if values else None
    if metric == "Prediction Bias":
        if "prediction_bias" in frame.columns:
            values = pd.to_numeric(frame["prediction_bias"], errors="coerce").dropna()
            return safe_float(float(values.mean())) if len(values) else None
        true, pred = frame["y_true"].astype(float), frame["y_pred"].astype(float)
        return safe_float(float(np.mean(pred - true)))
    task_type = str(frame["task_type"].dropna().iloc[0])
    return compute_metrics(frame, task_type).get(metric)


def bootstrap_group_metric(
    frame: pd.DataFrame,
    metric: str,
    resamples: int,
    seed: int,
    unit_column: str = "subject_id",
) -> tuple[float | None, float | None]:
    if resamples <= 0 or frame.empty:
        return None, None
    if metric in {"QWK", "Ordinal MAE", "Macro-F1", "ECE", "Brier Score", "Balanced Accuracy", "AUROC", "AUPRC", "CCC", "MAE", "RMSE", "Spearman"}:
        task_type = str(frame["task_type"].dropna().iloc[0])
        return bootstrap_ci(frame, task_type, metric, resamples, seed, unit_column=unit_column)
    rng = np.random.default_rng(seed)
    unit_series = frame[unit_column].astype(str)
    units = np.asarray(sorted(unit_series.dropna().unique()))
    if units.size == 0:
        return None, None
    grouped_indices = {unit: np.flatnonzero(unit_series.to_numpy() == unit) for unit in units}
    values: list[float] = []
    for _ in range(resamples):
        sample_units = rng.choice(units, size=units.size, replace=True)
        sample_indices = np.concatenate([grouped_indices[unit] for unit in sample_units])
        value = group_metric_value(frame.iloc[sample_indices], metric)
        if value is not None:
            values.append(float(value))
    if not values:
        return None, None
    return safe_float(np.percentile(values, 2.5)), safe_float(np.percentile(values, 97.5))


def subgroup_metric_records(
    predictions: pd.DataFrame,
    subgroup_resamples: int,
    seed: int,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    group_specs = [
        ("age_group", "age_group"),
        ("true_severity", "severity_label"),
        ("gender_group", "gender_group"),
        ("health_group", "health_group"),
        ("financial_stress_bin", "financial_stress_bin"),
    ] + [(f"personality_{trait}_bin", f"{trait}_bin") for trait in TRAITS]
    metric_rows: list[dict[str, Any]] = []
    key_cols = ["run_id", "dataset", "modality", "task", "model", "task_type", "seed"]
    for group_type, column in group_specs:
        if column not in predictions.columns:
            continue
        for key, group in predictions.groupby(key_cols + [column], dropna=False):
            if not isinstance(key, tuple):
                key = (key,)
            meta = dict(zip(key_cols + [column], key, strict=True))
            group_value = str(meta.pop(column))
            if group_value in {"nan", "None", "", "missing"} and group_type in {"gender_group", "health_group"}:
                continue
            task_type = str(meta["task_type"])
            metric_names = ["Accuracy", "Mean Confidence", "Calibration Gap", "True Label Probability", "Prediction Bias"]
            if task_type == "ordinal_prediction":
                metric_names.extend(["QWK", "Ordinal MAE", "Macro-F1", "ECE", "Brier Score"])
            elif task_type == "binary_classification":
                metric_names.extend(["Macro-F1", "Balanced Accuracy", "AUROC", "AUPRC", "ECE", "Brier Score"])
            elif task_type == "severity_regression":
                metric_names.extend(["CCC", "MAE", "RMSE", "Spearman"])
            for metric in metric_names:
                value = group_metric_value(group, metric)
                ci_low, ci_high = (None, None)
                if (
                    subgroup_resamples > 0
                    and group_type in SUBGROUP_CI_GROUP_TYPES
                    and metric in SUBGROUP_CI_METRICS
                ):
                    ci_low, ci_high = bootstrap_group_metric(
                        group,
                        metric,
                        subgroup_resamples,
                        seed + int(meta["seed"]) * 101 + len(metric),
                    )
                metric_rows.append(
                    {
                        **meta,
                        "group_type": group_type,
                        "group_value": group_value,
                        "metric": metric,
                        "value": value,
                        "ci95_low": ci_low,
                        "ci95_high": ci_high,
                        "ci_scope": "seed_group_subject_bootstrap" if ci_low is not None else "not_computed_default_lightweight",
                        "sample_count": int(len(group)),
                        "subject_count": int(group["subject_id"].nunique()),
                    }
                )
    per_seed = pd.DataFrame(metric_rows)
    summary_rows: list[dict[str, Any]] = []
    summary_keys = ["run_id", "dataset", "modality", "task", "model", "task_type", "group_type", "group_value", "metric"]
    for key, group in per_seed.groupby(summary_keys, dropna=False):
        values = [safe_float(value) for value in group["value"]]
        values = [value for value in values if value is not None]
        lows = [safe_float(value) for value in group["ci95_low"]]
        lows = [value for value in lows if value is not None]
        highs = [safe_float(value) for value in group["ci95_high"]]
        highs = [value for value in highs if value is not None]
        if not values:
            continue
        meta = dict(zip(summary_keys, key, strict=True))
        summary_rows.append(
            {
                **meta,
                "mean": safe_float(float(np.mean(values))),
                "std": safe_float(float(np.std(values, ddof=0))),
                "ci95_low": safe_float(float(np.mean(lows))) if lows else None,
                "ci95_high": safe_float(float(np.mean(highs))) if highs else None,
                "seed_count": int(len(values)),
                "sample_count_mean": safe_float(float(np.mean(group["sample_count"].astype(float)))),
                "subject_count_mean": safe_float(float(np.mean(group["subject_count"].astype(float)))),
                "ci_scope": "seed_group_subject_bootstrap" if lows else "not_computed_default_lightweight",
            }
        )
    return per_seed, pd.DataFrame(summary_rows)


def subgroup_gap_summary(summary: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for (run_id, group_type, metric), group in summary.groupby(["run_id", "group_type", "metric"], dropna=False):
        if group["group_value"].nunique() < 2:
            continue
        sorted_group = group.sort_values("mean")
        low = sorted_group.iloc[0]
        high = sorted_group.iloc[-1]
        rows.append(
            {
                "run_id": run_id,
                "group_type": group_type,
                "metric": metric,
                "min_group": str(low["group_value"]),
                "min_mean": safe_float(low["mean"]),
                "max_group": str(high["group_value"]),
                "max_mean": safe_float(high["mean"]),
                "absolute_gap": safe_float(abs(float(high["mean"]) - float(low["mean"]))),
            }
        )
    return pd.DataFrame(rows).sort_values(["absolute_gap", "run_id"], ascending=[False, True]).reset_index(drop=True)


def metric_delta_summary(metric_summary: pd.DataFrame) -> pd.DataFrame:
    pairs = [
        ("avp_minus_av", AVP_SPEC.run_id, AV_SPEC.run_id),
        ("personality_minus_shuffled_personality", PERSONALITY_SPEC.run_id, SHUFFLED_PERSONALITY_SPEC.run_id),
        ("avp_minus_avp_shuffled_personality", AVP_SPEC.run_id, AVP_SHUFFLED_PERSONALITY_SPEC.run_id),
        ("demographics_minus_shuffled_age", DEMOGRAPHICS_SPEC.run_id, SHUFFLED_AGE_SPEC.run_id),
        ("personality_minus_counterfactual_age_swap", PERSONALITY_SPEC.run_id, PERSONALITY_COUNTERFACTUAL_SPEC.run_id),
    ]
    rows: list[dict[str, Any]] = []
    for comparison, left_run, right_run in pairs:
        left = metric_summary[metric_summary["run_id"].eq(left_run)]
        right = metric_summary[metric_summary["run_id"].eq(right_run)]
        for metric in sorted(set(left["metric"]) & set(right["metric"])):
            left_value = safe_float(left[left["metric"].eq(metric)]["mean"].iloc[0])
            right_value = safe_float(right[right["metric"].eq(metric)]["mean"].iloc[0])
            if left_value is None or right_value is None:
                continue
            rows.append(
                {
                    "comparison": comparison,
                    "metric": metric,
                    "left_run_id": left_run,
                    "right_run_id": right_run,
                    "left_mean": left_value,
                    "right_mean": right_value,
                    "delta_left_minus_right": safe_float(left_value - right_value),
                }
            )
    return pd.DataFrame(rows)


def diagnostic_metric_records(
    frame: pd.DataFrame,
    bootstrap_resamples: int,
    seed: int,
    ci_run_ids: set[str],
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Compute point estimates for all runs and summary CIs for core diagnostics.

    Phase 2's helper bootstraps every seed/metric/run cell, which is useful for
    final baseline reproduction but too slow for a lightweight Phase 3 default.
    This function keeps all point estimates and computes subject-level bootstrap
    CIs only on run-level summaries for the current diagnostic models.
    """
    required = {"run_id", "task_type", "y_true", "y_pred"}
    missing = required - set(frame.columns)
    if missing:
        raise ValueError(f"prediction frame missing columns: {', '.join(sorted(missing))}")

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
        metrics = compute_metrics(group, str(meta["task_type"]))
        for metric, value in metrics.items():
            per_seed_rows.append(
                {
                    **meta,
                    "metric": metric,
                    "value": value,
                    "ci95_low": None,
                    "ci95_high": None,
                    "sample_count": int(len(group)),
                }
            )

    per_seed = pd.DataFrame(per_seed_rows)
    summary_rows: list[dict[str, Any]] = []
    for key, group in per_seed.groupby(baseline_group_cols + ["metric"], dropna=False):
        if not isinstance(key, tuple):
            key = (key,)
        meta = dict(zip(baseline_group_cols + ["metric"], key, strict=True))
        values = [safe_float(value) for value in group["value"]]
        values = [value for value in values if value is not None]
        if not values:
            continue
        source_rows = frame[frame["run_id"].astype(str).eq(str(meta["run_id"]))]
        ci_low, ci_high = (None, None)
        if str(meta["run_id"]) in ci_run_ids and bootstrap_resamples > 0:
            ci_low, ci_high = bootstrap_ci(
                source_rows,
                str(meta["task_type"]),
                str(meta["metric"]),
                bootstrap_resamples,
                seed + len(summary_rows),
            )
        summary_rows.append(
            {
                **meta,
                "mean": safe_float(float(np.mean(values))),
                "std": safe_float(float(np.std(values, ddof=0))),
                "ci95_low": ci_low,
                "ci95_high": ci_high,
                "seed_count": int(len(values)),
                "sample_count_mean": safe_float(float(np.mean(group["sample_count"].astype(float)))),
                "ci_scope": "run_level_subject_bootstrap" if ci_low is not None else "not_computed_default_lightweight",
            }
        )
    return per_seed, pd.DataFrame(summary_rows)


def prediction_availability(subjects: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    rows.append(
        {
            "diagnostic": "demographics_only",
            "status": "available",
            "usable_subjects": int(subjects["age_group"].ne("missing").sum()),
            "notes": "age_group is available; gender is unavailable",
        }
    )
    rows.append(
        {
            "diagnostic": "gender_only_and_gender_subgroups",
            "status": "blocked",
            "usable_subjects": int(subjects["gender_group"].ne("missing").sum()),
            "notes": "structured gender metadata is empty in the MPDD manifest",
        }
    )
    rows.append(
        {
            "diagnostic": "health_only_and_health_subgroups",
            "status": "blocked",
            "usable_subjects": int(subjects["health_group"].ne("missing").sum()),
            "notes": "structured health_condition metadata is empty in the MPDD manifest",
        }
    )
    rows.append(
        {
            "diagnostic": "personality_only",
            "status": "available",
            "usable_subjects": int(subjects["personality_available"].sum()),
            "notes": "raw text is used in fold-local TF-IDF but never written to outputs",
        }
    )
    rows.append(
        {
            "diagnostic": "audio_video_only",
            "status": "available",
            "usable_subjects": int(len(subjects)),
            "notes": "uses cached Phase 2 subject-level WavLM and ResNet features",
        }
    )
    rows.append(
        {
            "diagnostic": "gait_psychomotor_context",
            "status": "available",
            "usable_subjects": int(subjects["gait_available"].sum()),
            "notes": "gait is analyzed as context, not concatenated into AVP",
        }
    )
    return pd.DataFrame(rows)


def cohort_profile(subjects: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for group_type, column in [
        ("overall", None),
        ("age_group", "age_group"),
        ("financial_stress_bin", "financial_stress_bin"),
    ] + [(f"personality_{trait}_bin", f"{trait}_bin") for trait in TRAITS]:
        groups = [("all", subjects)] if column is None else list(subjects.groupby(column, dropna=False))
        for value, group in groups:
            if str(value) in {"nan", "None", ""}:
                continue
            severity_counts = group["severity_label"].astype(int).value_counts().sort_index()
            rows.append(
                {
                    "group_type": group_type,
                    "group_value": str(value),
                    "subject_count": int(len(group)),
                    "phq9_mean": safe_float(float(group["phq9_total"].mean())),
                    "phq9_std": safe_float(float(group["phq9_total"].std(ddof=0))),
                    "binary_positive_rate": safe_float(float(group["binary_label"].astype(float).mean())),
                    "severity_0_count": int(severity_counts.get(0, 0)),
                    "severity_1_count": int(severity_counts.get(1, 0)),
                    "severity_2_count": int(severity_counts.get(2, 0)),
                }
            )
    return pd.DataFrame(rows)


def load_sequence(path_value: Any) -> np.ndarray:
    path = Path(str(path_value))
    if not path.exists():
        raise FileNotFoundError("manifest gait path missing")
    arr = np.load(path, allow_pickle=False)
    if not np.issubdtype(arr.dtype, np.number):
        raise ValueError("non-numeric gait array")
    if arr.ndim == 1:
        arr = arr.reshape(-1, 1)
    if arr.ndim != 2:
        raise ValueError(f"expected 2D gait array, got shape {arr.shape}")
    return np.asarray(arr, dtype=np.float64)


def channel_stats(values: np.ndarray) -> list[float]:
    finite = values[np.isfinite(values)]
    if finite.size == 0:
        return [np.nan] * 12
    if finite.size > 1:
        diff = np.diff(finite)
        mean_abs_diff = float(np.mean(np.abs(diff)))
        diff_std = float(np.std(diff))
    else:
        mean_abs_diff = 0.0
        diff_std = 0.0
    q25, median, q75 = np.percentile(finite, [25, 50, 75])
    return [
        float(np.mean(finite)),
        float(np.std(finite)),
        float(np.min(finite)),
        float(np.max(finite)),
        float(q25),
        float(median),
        float(q75),
        float(q75 - q25),
        float(np.sqrt(np.mean(finite**2))),
        mean_abs_diff,
        diff_std,
        float(np.mean(np.abs(finite))),
    ]


def gait_feature_names() -> list[str]:
    stats = ["mean", "std", "min", "max", "q25", "median", "q75", "iqr", "rms", "mean_abs_diff", "diff_std", "mean_abs"]
    names = ["sequence_length", "channel_count"]
    for channel in range(MAX_GAIT_CHANNELS):
        names.extend([f"channel_{channel:02d}_{stat}" for stat in stats])
    names.extend(["global_mean", "global_std", "global_rms", "global_iqr"])
    return names


def extract_gait_features(arr: np.ndarray) -> list[float]:
    rows, cols = arr.shape
    features: list[float] = [float(rows), float(cols)]
    for channel in range(MAX_GAIT_CHANNELS):
        if channel < cols:
            features.extend(channel_stats(arr[:, channel]))
        else:
            features.extend([np.nan] * 12)
    clipped = np.clip(arr[:, : min(cols, MAX_GAIT_CHANNELS)], -1.0e6, 1.0e6)
    finite = clipped[np.isfinite(clipped)]
    if finite.size:
        features.extend(
            [
                float(np.mean(finite)),
                float(np.std(finite)),
                float(np.sqrt(np.mean(finite**2))),
                float(np.percentile(finite, 75) - np.percentile(finite, 25)),
            ]
        )
    else:
        features.extend([np.nan] * 4)
    return features


def build_gait_feature_frame(subjects: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    names = gait_feature_names()
    usable = subjects[subjects["gait_available"]].copy()
    for _, row in usable.iterrows():
        arr = load_sequence(row["gait_path_internal"])
        features = extract_gait_features(arr)
        rows.append(
            {
                "subject_id": str(row["subject_id"]),
                "age_group": str(row["age_group"]),
                "severity_label": int(row["severity_label"]),
                "binary_label": int(row["binary_label"]),
                "phq9_total": float(row["phq9_total"]),
                **{name: value for name, value in zip(names, features, strict=True)},
            }
        )
    return pd.DataFrame(rows)


def bootstrap_spearman(x: np.ndarray, y: np.ndarray, resamples: int, seed: int) -> tuple[float | None, float | None]:
    finite = np.isfinite(x) & np.isfinite(y)
    x = x[finite]
    y = y[finite]
    if x.size < 5 or resamples <= 0:
        return None, None
    rng = np.random.default_rng(seed)
    values: list[float] = []
    for _ in range(resamples):
        idx = rng.integers(0, x.size, size=x.size)
        value = spearman(y[idx], x[idx])
        if value is not None:
            values.append(float(value))
    if not values:
        return None, None
    return safe_float(np.percentile(values, 2.5)), safe_float(np.percentile(values, 97.5))


def gait_correlations(gait: pd.DataFrame, resamples: int, top_n: int) -> pd.DataFrame:
    targets = ["phq9_total", "severity_label", "binary_label"]
    feature_cols = [column for column in gait.columns if column not in {"subject_id", "age_group", "severity_label", "binary_label", "phq9_total"}]
    coarse_rows: list[dict[str, Any]] = []
    for group_value, group in [("all", gait)] + list(gait.groupby("age_group", dropna=False)):
        for target in targets:
            y = group[target].to_numpy(dtype=np.float64)
            for feature in feature_cols:
                x = group[feature].to_numpy(dtype=np.float64)
                value = spearman(y, x)
                if value is not None:
                    coarse_rows.append(
                        {
                            "group_type": "age_group",
                            "group_value": str(group_value),
                            "target": target,
                            "feature": feature,
                            "spearman": float(value),
                            "abs_spearman": abs(float(value)),
                            "subject_count": int(len(group)),
                        }
                    )
    coarse = pd.DataFrame(coarse_rows)
    if coarse.empty:
        return coarse
    top = (
        coarse.sort_values(["target", "group_value", "abs_spearman"], ascending=[True, True, False])
        .groupby(["target", "group_value"], as_index=False)
        .head(top_n)
        .copy()
    )
    ci_lows: list[float | None] = []
    ci_highs: list[float | None] = []
    for idx, row in top.reset_index(drop=True).iterrows():
        group = gait if row["group_value"] == "all" else gait[gait["age_group"].astype(str).eq(str(row["group_value"]))]
        low, high = bootstrap_spearman(
            group[str(row["feature"])].to_numpy(dtype=np.float64),
            group[str(row["target"])].to_numpy(dtype=np.float64),
            resamples,
            BOOTSTRAP_SEED + idx,
        )
        ci_lows.append(low)
        ci_highs.append(high)
    top["ci95_low"] = ci_lows
    top["ci95_high"] = ci_highs
    return top.sort_values(["abs_spearman"], ascending=False).reset_index(drop=True)


def summarize_counterfactual(counterfactual: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for key, group in counterfactual.groupby(["seed", "age_group"], dropna=False):
        seed, age_group = key
        delta = group["delta_expected_severity"].astype(float)
        rows.append(
            {
                "seed": int(seed),
                "age_group": str(age_group),
                "subject_count": int(group["subject_id"].nunique()),
                "changed_pred_rate": safe_float(float(group["changed_pred"].astype(bool).mean())),
                "mean_delta_expected_severity": safe_float(float(delta.mean())),
                "mean_abs_delta_expected_severity": safe_float(float(delta.abs().mean())),
            }
        )
    summary_rows: list[dict[str, Any]] = []
    per_seed = pd.DataFrame(rows)
    for age_group, group in per_seed.groupby("age_group", dropna=False):
        for metric in ["changed_pred_rate", "mean_delta_expected_severity", "mean_abs_delta_expected_severity"]:
            values = group[metric].astype(float)
            summary_rows.append(
                {
                    "age_group": str(age_group),
                    "metric": metric,
                    "mean": safe_float(float(values.mean())),
                    "std": safe_float(float(values.std(ddof=0))),
                    "seed_count": int(len(values)),
                    "subject_count_mean": safe_float(float(group["subject_count"].astype(float).mean())),
                }
            )
    return pd.DataFrame(summary_rows)


def make_plots(out_dir: Path, metric_summary: pd.DataFrame, subgroup_summary: pd.DataFrame, gait_top: pd.DataFrame) -> list[str]:
    plot_paths: list[str] = []
    try:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except Exception:
        return plot_paths

    selected_runs = [
        DEMOGRAPHICS_SPEC.run_id,
        PERSONALITY_SPEC.run_id,
        SHUFFLED_PERSONALITY_SPEC.run_id,
        AV_SPEC.run_id,
        AVP_SPEC.run_id,
        AVP_SHUFFLED_PERSONALITY_SPEC.run_id,
    ]
    plot_df = metric_summary[
        metric_summary["run_id"].isin(selected_runs)
        & metric_summary["metric"].isin(["Macro-F1", "QWK", "ECE", "Brier Score"])
    ].copy()
    if not plot_df.empty:
        pivot = plot_df.pivot(index="run_id", columns="metric", values="mean").reindex(selected_runs)
        fig, ax = plt.subplots(figsize=(10, 4.8))
        pivot[["Macro-F1", "QWK"]].plot(kind="bar", ax=ax, color=["#2864a6", "#d39b28"])
        ax.set_title("MPDD Phase 3 Model Comparison")
        ax.set_ylabel("Mean across seeds")
        ax.set_xlabel("")
        ax.tick_params(axis="x", labelrotation=35)
        ax.grid(axis="y", color="#d9d9d9", linewidth=0.7)
        fig.tight_layout()
        path = out_dir / "model_comparison_macro_f1_qwk.png"
        fig.savefig(path, dpi=160)
        plt.close(fig)
        plot_paths.append(path.name)

    age_cal = subgroup_summary[
        subgroup_summary["group_type"].eq("age_group")
        & subgroup_summary["metric"].isin(["ECE", "Brier Score", "Ordinal MAE", "Accuracy"])
        & subgroup_summary["run_id"].isin([PERSONALITY_SPEC.run_id, AV_SPEC.run_id, AVP_SPEC.run_id])
    ].copy()
    if not age_cal.empty:
        fig, ax = plt.subplots(figsize=(10, 4.8))
        for idx, run_id in enumerate([PERSONALITY_SPEC.run_id, AV_SPEC.run_id, AVP_SPEC.run_id]):
            subset = age_cal[age_cal["run_id"].eq(run_id) & age_cal["metric"].eq("ECE")]
            if subset.empty:
                continue
            values = subset.set_index("group_value")["mean"].reindex(["elder", "young"])
            ax.bar(np.arange(len(values)) + idx * 0.22, values, width=0.22, label=run_id)
        ax.set_title("Age-Group Calibration Error")
        ax.set_ylabel("ECE, lower is better")
        ax.set_xticks(np.arange(2) + 0.22)
        ax.set_xticklabels(["elder", "young"])
        ax.grid(axis="y", color="#d9d9d9", linewidth=0.7)
        ax.legend(fontsize=7)
        fig.tight_layout()
        path = out_dir / "age_group_ece.png"
        fig.savefig(path, dpi=160)
        plt.close(fig)
        plot_paths.append(path.name)

    gait_plot = gait_top[gait_top["group_value"].eq("all") & gait_top["target"].eq("phq9_total")].head(10)
    if not gait_plot.empty:
        fig, ax = plt.subplots(figsize=(9, 4.8))
        display = gait_plot.sort_values("spearman")
        colors = ["#2864a6" if value >= 0 else "#d17538" for value in display["spearman"]]
        ax.barh(display["feature"], display["spearman"], color=colors)
        ax.axvline(0, color="#333333", linewidth=0.8)
        ax.set_title("Top Gait Statistic Correlations With PHQ-9")
        ax.set_xlabel("Spearman correlation")
        ax.grid(axis="x", color="#d9d9d9", linewidth=0.7)
        fig.tight_layout()
        path = out_dir / "gait_top_phq9_correlations.png"
        fig.savefig(path, dpi=160)
        plt.close(fig)
        plot_paths.append(path.name)
    return plot_paths


def compact_metric_table(metric_summary: pd.DataFrame, run_ids: list[str], metrics: list[str]) -> str:
    subset = metric_summary[metric_summary["run_id"].isin(run_ids) & metric_summary["metric"].isin(metrics)].copy()
    if subset.empty:
        return "_No rows available._"
    pivot = subset.pivot(index="run_id", columns="metric", values="mean").reindex(run_ids)
    pivot = pivot[[metric for metric in metrics if metric in pivot.columns]]
    return markdown_table(pivot.reset_index().round(4))


def markdown_table(frame: pd.DataFrame, max_rows: int | None = None) -> str:
    if frame.empty:
        return "_No rows available._"
    display = frame.copy()
    if max_rows is not None:
        display = display.head(max_rows)
    columns = [str(column) for column in display.columns]

    def format_value(value: Any) -> str:
        if value is None or (isinstance(value, float) and math.isnan(value)):
            return ""
        if isinstance(value, (float, np.floating)):
            return f"{float(value):.4f}"
        return str(value).replace("\n", " ")

    lines = [
        "| " + " | ".join(columns) + " |",
        "| " + " | ".join(["---"] * len(columns)) + " |",
    ]
    for _, row in display.iterrows():
        lines.append("| " + " | ".join(format_value(row[column]) for column in display.columns) + " |")
    return "\n".join(lines)


def metric_value(metric_summary: pd.DataFrame, run_id: str, metric: str) -> float | None:
    row = metric_summary[metric_summary["run_id"].eq(run_id) & metric_summary["metric"].eq(metric)]
    if row.empty:
        return None
    return safe_float(row["mean"].iloc[0])


def delta_value(deltas: pd.DataFrame, comparison: str, metric: str) -> float | None:
    row = deltas[deltas["comparison"].eq(comparison) & deltas["metric"].eq(metric)]
    if row.empty:
        return None
    return safe_float(row["delta_left_minus_right"].iloc[0])


def stop_go_summary(metric_summary: pd.DataFrame, deltas: pd.DataFrame, subgroup_gaps: pd.DataFrame, gait_top: pd.DataFrame) -> dict[str, Any]:
    avp_macro_delta = delta_value(deltas, "avp_minus_av", "Macro-F1")
    avp_qwk_delta = delta_value(deltas, "avp_minus_av", "QWK")
    personality_macro_delta = delta_value(deltas, "personality_minus_shuffled_personality", "Macro-F1")
    demo_qwk_delta = delta_value(deltas, "demographics_minus_shuffled_age", "QWK")
    counter_abs_delta = metric_summary[
        metric_summary["run_id"].eq(PERSONALITY_COUNTERFACTUAL_SPEC.run_id)
        & metric_summary["metric"].eq("Macro-F1")
    ]
    max_age_ece_gap = subgroup_gaps[
        subgroup_gaps["group_type"].eq("age_group") & subgroup_gaps["metric"].eq("ECE")
    ]["absolute_gap"].max()
    max_personality_ece_gap = subgroup_gaps[
        subgroup_gaps["group_type"].str.startswith("personality_") & subgroup_gaps["metric"].eq("ECE")
    ]["absolute_gap"].max()
    top_gait_phq9 = gait_top[gait_top["target"].eq("phq9_total") & gait_top["group_value"].eq("all")]["abs_spearman"].max()
    def flag(delta: float | None, threshold: float, positive_label: str, weak_label: str) -> str:
        if delta is None:
            return "blocked"
        return positive_label if delta >= threshold else weak_label
    return {
        "individual_difference_conditioning": {
            "recommendation": flag(avp_macro_delta, 0.02, "go_diagnostic_signal", "stop_or_weak_gain"),
            "avp_minus_av_macro_f1": avp_macro_delta,
            "avp_minus_av_qwk": avp_qwk_delta,
            "interpretation": "Use as evidence for or against adding personality/context conditioning after Phase 3.",
        },
        "personality_shortcut_risk": {
            "recommendation": flag(personality_macro_delta, 0.02, "go_shortcut_or_moderator_signal", "weak_or_no_standalone_signal"),
            "personality_minus_shuffled_macro_f1": personality_macro_delta,
            "counterfactual_macro_f1": safe_float(counter_abs_delta["mean"].iloc[0]) if not counter_abs_delta.empty else None,
        },
        "age_shortcut_or_moderation": {
            "recommendation": flag(demo_qwk_delta, 0.02, "go_age_shortcut_check_needed", "weak_age_only_signal"),
            "demographics_minus_shuffled_age_qwk": demo_qwk_delta,
            "max_age_ece_gap": safe_float(max_age_ece_gap) if pd.notna(max_age_ece_gap) else None,
        },
        "personality_bin_calibration": {
            "recommendation": "go_calibration_audit" if pd.notna(max_personality_ece_gap) and float(max_personality_ece_gap) >= 0.05 else "weak_or_sparse",
            "max_personality_bin_ece_gap": safe_float(max_personality_ece_gap) if pd.notna(max_personality_ece_gap) else None,
        },
        "gait_psychomotor_context": {
            "recommendation": "go_context_validation" if pd.notna(top_gait_phq9) and float(top_gait_phq9) >= 0.25 else "weak_or_descriptive_only",
            "top_abs_spearman_with_phq9": safe_float(top_gait_phq9) if pd.notna(top_gait_phq9) else None,
            "interpretation": "Gait remains a diagnostic context axis, not a fourth fused modality in this session.",
        },
        "gender_health": {
            "recommendation": "blocked",
            "reason": "structured gender and health_condition metadata are empty in the current manifest",
        },
    }


def write_report(
    out_dir: Path,
    summary: dict[str, Any],
    metric_summary: pd.DataFrame,
    deltas: pd.DataFrame,
    subgroup_gaps: pd.DataFrame,
    gait_top: pd.DataFrame,
    counter_summary: pd.DataFrame,
    plots: list[str],
) -> None:
    run_ids = [
        DEMOGRAPHICS_SPEC.run_id,
        SHUFFLED_AGE_SPEC.run_id,
        PERSONALITY_SPEC.run_id,
        SHUFFLED_PERSONALITY_SPEC.run_id,
        PERSONALITY_COUNTERFACTUAL_SPEC.run_id,
        AV_SPEC.run_id,
        AVP_SPEC.run_id,
        AVP_SHUFFLED_PERSONALITY_SPEC.run_id,
    ]
    top_gait = gait_top[gait_top["group_value"].eq("all") & gait_top["target"].eq("phq9_total")].head(8)
    high_gaps = subgroup_gaps[
        subgroup_gaps["metric"].isin(["ECE", "Ordinal MAE", "Accuracy", "Macro-F1"])
        & subgroup_gaps["run_id"].isin([PERSONALITY_SPEC.run_id, AV_SPEC.run_id, AVP_SPEC.run_id])
    ].head(12)
    lines = [
        "# MPDD Phase 3 Individual-Difference Diagnostics",
        "",
        f"Generated: `{summary['generated_at']}`",
        "",
        "## Executive Summary",
        "",
        f"- Labeled train subjects: `{summary['subject_count']}`; seeds: `{summary['seeds']}`; split policy: subject-level repeated 5-fold OOF.",
        "- Gender-only and health-only diagnostics are blocked because the current structured manifest fields are empty.",
        f"- Stop/Go evidence: `{as_ascii_json(summary['stop_go'])}`",
        "",
        "## Protocol",
        "",
        "- Scope: personality-only, demographics-only, audio-video only, audio-video + personality, shuffled controls, personality age-swap counterfactuals, subgroup performance/calibration, and gait psychomotor context.",
        "- The unlabeled MPDD test split is not used.",
        "- Fold-local feature learning is used for all TF-IDF personality features and shuffled/counterfactual controls.",
        "- Cached Phase 2 WavLM audio and ResNet video subject features are reused when available; no encoder fine-tuning is performed.",
        "- Default CI mode is lightweight: run-level subject bootstrap CIs are computed for Phase 3 diagnostic models; subgroup CIs are computed for age/severity core metrics; personality-bin subgroup rows retain point estimates and cross-seed spread unless rerun with higher/fuller settings.",
        "- Gait statistics are analyzed only as psychomotor context, not concatenated into AVP.",
        "- Output hygiene: raw personality text, raw audio/video/IMU, raw arrays, and manifest source paths are not written.",
        "",
        "## Main Model Diagnostics",
        "",
        compact_metric_table(metric_summary, run_ids, ["QWK", "Ordinal MAE", "Macro-F1", "ECE", "Brier Score"]),
        "",
        "## Key Deltas",
        "",
        markdown_table(deltas.round(4)) if not deltas.empty else "_No comparable deltas available._",
        "",
        "## Subgroup Gaps",
        "",
        markdown_table(high_gaps.round(4)) if not high_gaps.empty else "_No subgroup gaps available._",
        "",
        "## Personality Counterfactual Sensitivity",
        "",
        markdown_table(counter_summary.round(4)) if not counter_summary.empty else "_No counterfactual rows available._",
        "",
        "## Gait Psychomotor Context",
        "",
        markdown_table(top_gait[["feature", "spearman", "ci95_low", "ci95_high", "subject_count"]].round(4))
        if not top_gait.empty
        else "_No gait correlations available._",
        "",
        "## Plots",
        "",
    ]
    if plots:
        lines.extend([f"- `{plot}`" for plot in plots])
    else:
        lines.append("- Plot generation unavailable or skipped.")
    lines.extend(
        [
            "",
            "## Blockers And Caveats",
            "",
            "- Structured gender and health metadata are unavailable, so gender/health subgroup calibration and health-only baselines cannot be interpreted.",
            "- Personality bins are derived from structured numeric/descriptor cues in the personality descriptions; they are diagnostic bins, not official labels.",
            "- Some Phase 2 feature/prediction caches are read from the read-only main checkout because large generated CSVs are not present in this worktree.",
            "- These diagnostics do not justify final architecture choices by themselves; they decide whether individual-difference conditioning deserves Phase 4/5 design work.",
            "",
            "## Regeneration",
            "",
            "```bash",
            "python scripts/phase3_mpdd_individual_differences.py",
            "```",
            "",
            "## Output Files",
            "",
            "- `phase3_model_predictions.csv`",
            "- `phase3_all_predictions_for_metrics.csv`",
            "- `phase3_metrics_by_seed.csv`",
            "- `phase3_metric_summary.csv`",
            "- `phase3_metric_deltas.csv`",
            "- `subgroup_metrics_by_seed.csv`",
            "- `subgroup_metric_summary.csv`",
            "- `subgroup_gap_summary.csv`",
            "- `personality_counterfactual_sensitivity.csv`",
            "- `personality_counterfactual_summary.csv`",
            "- `gait_psychomotor_top_correlations.csv`",
            "- `cohort_profile.csv`",
            "- `diagnostic_availability.csv`",
            "- `phase3_run_summary.json`",
            "- `artifact_hygiene_audit.json`",
        ]
    )
    (out_dir / "mpdd_individual_differences_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def output_hygiene_audit(out_dir: Path) -> dict[str, Any]:
    forbidden_patterns = [
        "/root/autodl-tmp/datasets/",
        "privacy-constrained-raw",
        ".WAV",
        ".wav",
        ".npy",
        "The patient has",
        "Descriptions",
        "personalized_descriptions",
    ]
    checked_files = []
    violations: list[dict[str, Any]] = []
    for path in sorted(out_dir.rglob("*")):
        if not path.is_file():
            continue
        if path.suffix.lower() in {".png"}:
            checked_files.append({"file": path.name, "checked": False, "reason": "binary_plot"})
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        checked_files.append({"file": path.name, "checked": True, "reason": ""})
        for pattern in forbidden_patterns:
            if pattern in text:
                violations.append({"file": path.name, "pattern": pattern})
    return {
        "generated_at": utc_now(),
        "checked_file_count": len(checked_files),
        "violation_count": len(violations),
        "violations": violations,
        "passed": not violations,
    }


def write_json(path: Path, data: Any) -> None:
    path.write_text(json.dumps(data, indent=2, ensure_ascii=True, sort_keys=True) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, default=MANIFEST_PATH)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--bootstrap-resamples", type=int, default=20)
    parser.add_argument("--subgroup-bootstrap-resamples", type=int, default=10)
    parser.add_argument("--gait-bootstrap-resamples", type=int, default=50)
    parser.add_argument("--gait-top-n", type=int, default=12)
    args = parser.parse_args()

    args.out_dir.mkdir(parents=True, exist_ok=True)

    subjects = read_manifest_subjects(args.manifest)
    availability = prediction_availability(subjects)
    availability.to_csv(args.out_dir / "diagnostic_availability.csv", index=False)
    profile = cohort_profile(subjects)
    profile.to_csv(args.out_dir / "cohort_profile.csv", index=False)

    model_table, audio_columns, video_columns, feature_inventory = build_model_table(subjects)
    phase3_predictions, fold_summaries, counterfactual = run_phase3_oof(model_table, audio_columns, video_columns)
    phase3_predictions["source_family"] = "phase3_diagnostic_model"
    phase3_predictions.to_csv(args.out_dir / "phase3_model_predictions.csv", index=False)
    fold_summaries.to_csv(args.out_dir / "phase3_fold_summaries.csv", index=False)
    counterfactual.to_csv(args.out_dir / "personality_counterfactual_sensitivity.csv", index=False)
    counter_summary = summarize_counterfactual(counterfactual)
    counter_summary.to_csv(args.out_dir / "personality_counterfactual_summary.csv", index=False)

    phase2_reference, reference_inventory = load_phase2_reference_predictions()
    reference_inventory.to_csv(args.out_dir / "phase2_reference_prediction_inventory.csv", index=False)
    pd.DataFrame(feature_inventory).to_csv(args.out_dir / "phase2_feature_cache_inventory.csv", index=False)

    all_predictions = pd.concat([phase3_predictions, phase2_reference], ignore_index=True, sort=False)
    all_predictions = add_subject_groups(all_predictions, subjects)
    all_predictions = add_prediction_diagnostics(all_predictions)
    all_predictions.to_csv(args.out_dir / "phase3_all_predictions_for_metrics.csv", index=False)

    metrics_by_seed, metric_summary = diagnostic_metric_records(
        all_predictions,
        args.bootstrap_resamples,
        BOOTSTRAP_SEED,
        SUBGROUP_RUN_IDS,
    )
    metrics_by_seed.to_csv(args.out_dir / "phase3_metrics_by_seed.csv", index=False)
    metric_summary.to_csv(args.out_dir / "phase3_metric_summary.csv", index=False)
    deltas = metric_delta_summary(metric_summary)
    deltas.to_csv(args.out_dir / "phase3_metric_deltas.csv", index=False)

    subgroup_predictions = all_predictions[all_predictions["run_id"].astype(str).isin(SUBGROUP_RUN_IDS)].copy()
    subgroup_by_seed, subgroup_summary = subgroup_metric_records(
        subgroup_predictions,
        subgroup_resamples=args.subgroup_bootstrap_resamples,
        seed=BOOTSTRAP_SEED,
    )
    subgroup_by_seed.to_csv(args.out_dir / "subgroup_metrics_by_seed.csv", index=False)
    subgroup_summary.to_csv(args.out_dir / "subgroup_metric_summary.csv", index=False)
    subgroup_gaps = subgroup_gap_summary(subgroup_summary)
    subgroup_gaps.to_csv(args.out_dir / "subgroup_gap_summary.csv", index=False)

    gait_features = build_gait_feature_frame(subjects)
    gait_top = gait_correlations(gait_features, args.gait_bootstrap_resamples, args.gait_top_n)
    gait_top.to_csv(args.out_dir / "gait_psychomotor_top_correlations.csv", index=False)

    plots = make_plots(args.out_dir, metric_summary, subgroup_summary, gait_top)
    stop_go = stop_go_summary(metric_summary, deltas, subgroup_gaps, gait_top)
    run_summary = {
        "generated_at": utc_now(),
        "dataset": DATASET_DISPLAY,
        "subject_count": int(subjects["subject_id"].nunique()),
        "labeled_train_subjects": int(len(subjects)),
        "seeds": SEEDS,
        "seed_count": len(SEEDS),
        "bootstrap_resamples": int(args.bootstrap_resamples),
        "subgroup_bootstrap_resamples": int(args.subgroup_bootstrap_resamples),
        "gait_bootstrap_resamples": int(args.gait_bootstrap_resamples),
        "split_policy": "labeled_train_internal_subject_level_stratified_5fold_oof",
        "no_test_labels_used": True,
        "raw_personality_text_written": False,
        "raw_audio_written": False,
        "raw_video_written": False,
        "raw_imu_written": False,
        "raw_arrays_written": False,
        "source_paths_written": False,
        "phase2_cache_scopes": sorted(
            set(reference_inventory["source_scope"].dropna().astype(str).tolist())
            | {item["source_scope"] for item in feature_inventory}
        ),
        "availability": availability.to_dict(orient="records"),
        "run_ids": sorted(all_predictions["run_id"].dropna().astype(str).unique().tolist()),
        "prediction_rows": int(len(all_predictions)),
        "phase3_prediction_rows": int(len(phase3_predictions)),
        "phase2_reference_prediction_rows": int(len(phase2_reference)),
        "gender_non_missing_subjects": int(subjects["gender_group"].ne("missing").sum()),
        "health_non_missing_subjects": int(subjects["health_group"].ne("missing").sum()),
        "personality_trait_bins": {
            trait: {str(k): int(v) for k, v in subjects[f"{trait}_bin"].value_counts(dropna=False).sort_index().items()}
            for trait in TRAITS
        },
        "plots": plots,
        "stop_go": stop_go,
    }
    write_json(args.out_dir / "phase3_run_summary.json", run_summary)
    write_report(args.out_dir, run_summary, metric_summary, deltas, subgroup_gaps, gait_top, counter_summary, plots)

    hygiene = output_hygiene_audit(args.out_dir)
    write_json(args.out_dir / "artifact_hygiene_audit.json", hygiene)
    if hygiene["violation_count"]:
        raise SystemExit(f"output hygiene failed with {hygiene['violation_count']} violations")

    print(f"Wrote Phase 3 MPDD diagnostics to {args.out_dir.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
