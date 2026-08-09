#!/usr/bin/env python3
"""Run Phase 2 MODMA frozen WavLM baselines.

This runner extracts frozen WavLM segment embeddings from manifest-resolved
valid MODMA audio, averages them to subject and subject-task embeddings, and
evaluates simple linear heads. It does not fine-tune WavLM and writes no raw
audio, source paths, or file names.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import re
import warnings
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
import soundfile as sf
import torch
from scipy.signal import resample_poly
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression, Ridge
from sklearn.metrics import mean_absolute_error
from sklearn.model_selection import KFold
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from transformers import AutoFeatureExtractor, AutoModel

from phase2_metrics import metric_records, regression_metrics


warnings.filterwarnings("ignore", message="Support for mismatched key_padding_mask.*")

ROOT = Path("/root/autodl-tmp")
MANIFEST_PATH = ROOT / "datasets" / "manifests" / "modma_subjects.csv"
SPLIT_PATH = ROOT / "datasets" / "splits" / "phase2_subject_splits.csv"
DEFAULT_OUT_DIR = ROOT / "analysis" / "phase2_baselines" / "modma_audio_wavlm"
DEFAULT_MODEL_NAME = "microsoft/wavlm-base-plus"
SEEDS = [0, 1, 2, 3, 4]
TASK_TYPES = ["interview", "reading", "picture_description", "affective_task"]
FIXED_LOGISTIC_C = 1.0
RIDGE_ALPHA_GRID = [1.0, 10.0, 100.0, 1000.0]


@dataclass(frozen=True)
class BaselineSpec:
    run_id: str
    task: str
    task_type: str
    target: str
    model: str
    protocol_kind: str


SPECS = [
    BaselineSpec(
        run_id="modma_audio_binary_wavlm_linear",
        task="binary depression classification",
        task_type="binary_classification",
        target="binary_label",
        model="WavLM frozen embedding + linear",
        protocol_kind="subject_binary",
    ),
    BaselineSpec(
        run_id="modma_audio_phq9_wavlm_linear",
        task="PHQ-9 regression",
        task_type="severity_regression",
        target="phq9_total",
        model="WavLM frozen embedding + linear",
        protocol_kind="subject_phq9",
    ),
    BaselineSpec(
        run_id="modma_audio_binary_task_specific_wavlm",
        task="task-specific binary classification",
        task_type="binary_classification",
        target="binary_label",
        model="WavLM task-specific test",
        protocol_kind="task_specific_binary",
    ),
    BaselineSpec(
        run_id="modma_audio_binary_cross_task_wavlm",
        task="cross-task binary classification",
        task_type="binary_classification",
        target="binary_label",
        model="WavLM cross-task test",
        protocol_kind="cross_task_binary",
    ),
]


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def natural_key(value: Any) -> list[Any]:
    return [int(part) if part.isdigit() else part for part in re.split(r"(\d+)", str(value))]


def read_manifest(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"manifest missing: {path}")
    return pd.read_csv(path)


def load_split_frame(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"split layer missing: {path}")
    splits = pd.read_csv(path)
    required = {"dataset", "protocol_id", "protocol_type", "target", "fold", "role", "subject_id", "train_task", "eval_task"}
    missing = required - set(splits.columns)
    if missing:
        raise ValueError(f"split layer missing columns: {', '.join(sorted(missing))}")
    return splits[splits["dataset"].astype(str) == "modma"].copy()


def load_protocols(
    split_frame: pd.DataFrame,
    *,
    target: str,
    protocol_id: str | None = None,
    protocol_type: str | None = None,
) -> dict[str, dict[str, Any]]:
    selected = split_frame[split_frame["target"].astype(str) == target].copy()
    if protocol_id is not None:
        selected = selected[selected["protocol_id"].astype(str) == protocol_id].copy()
    if protocol_type is not None:
        selected = selected[selected["protocol_type"].astype(str) == protocol_type].copy()
    if selected.empty:
        raise ValueError(f"no MODMA split rows for target={target}, protocol_id={protocol_id}, protocol_type={protocol_type}")

    protocols: dict[str, dict[str, Any]] = {}
    for pid, protocol_rows in selected.groupby("protocol_id", sort=False):
        train_tasks = sorted(str(value) for value in protocol_rows["train_task"].dropna().unique())
        eval_tasks = sorted(str(value) for value in protocol_rows["eval_task"].dropna().unique())
        if len(train_tasks) > 1 or len(eval_tasks) > 1:
            raise ValueError(f"{pid} has ambiguous train/eval task fields")
        folds: dict[str, dict[str, list[str]]] = {}
        for fold, fold_rows in protocol_rows.groupby("fold", sort=False):
            roles: dict[str, list[str]] = {}
            for role, role_rows in fold_rows.groupby("role", sort=False):
                roles[str(role)] = sorted(role_rows["subject_id"].astype(str).unique(), key=natural_key)
            train_subjects = set(roles.get("train", []))
            validation_subjects = set(roles.get("validation", []))
            overlap = sorted(train_subjects & validation_subjects, key=natural_key)
            if overlap:
                raise ValueError(f"{pid}:{fold} train/validation subject overlap: {overlap[:10]}")
            if not train_subjects or not validation_subjects:
                raise ValueError(f"{pid}:{fold} requires non-empty train and validation roles")
            folds[str(fold)] = roles
        protocols[str(pid)] = {
            "protocol_id": str(pid),
            "protocol_type": str(protocol_rows["protocol_type"].iloc[0]),
            "train_task": train_tasks[0] if train_tasks else "",
            "eval_task": eval_tasks[0] if eval_tasks else "",
            "folds": dict(sorted(folds.items(), key=lambda item: natural_key(item[0]))),
        }
    return dict(sorted(protocols.items(), key=lambda item: natural_key(item[0])))


def build_segment_table(manifest_path: Path, subjects: set[str]) -> pd.DataFrame:
    manifest = read_manifest(manifest_path)
    required = {"subject_id", "audio_path", "task_type", "segment_id", "binary_label", "phq9_total", "file_valid"}
    missing = required - set(manifest.columns)
    if missing:
        raise ValueError(f"MODMA manifest missing columns: {', '.join(sorted(missing))}")
    rows = manifest[manifest["subject_id"].astype(str).isin(subjects)].copy()
    rows = rows[
        rows["file_valid"].fillna(False).astype(bool)
        & rows["audio_path"].notna()
        & rows["binary_label"].notna()
        & rows["phq9_total"].notna()
        & rows["task_type"].isin(TASK_TYPES)
    ].copy()
    if rows.empty:
        raise ValueError("no usable MODMA audio rows")
    rows = rows.sort_values(["subject_id", "task_type", "segment_id"]).reset_index()
    rows["subject_id"] = rows["subject_id"].astype(str)
    rows["task_type"] = rows["task_type"].astype(str)
    rows["segment_key"] = rows.apply(
        lambda row: "::".join([str(row["task_type"]), str(row["segment_id"]), str(row["index"])]),
        axis=1,
    )
    observed = set(rows["subject_id"].astype(str))
    missing_subjects = sorted(subjects - observed, key=natural_key)
    if missing_subjects:
        raise ValueError(f"split subjects missing valid audio rows: {missing_subjects[:10]}")
    counts = rows.groupby(["subject_id", "task_type"]).size().unstack(fill_value=0)
    missing_task_subjects = counts[(counts == 0).any(axis=1)]
    if not missing_task_subjects.empty:
        raise ValueError(f"some split subjects are missing task audio rows: {missing_task_subjects.head().to_dict()}")
    return rows.reset_index(drop=True)


def read_audio(path: Path, target_sr: int) -> tuple[np.ndarray, int]:
    data, sr = sf.read(str(path), always_2d=False)
    if data.ndim == 2:
        data = data.mean(axis=1)
    audio = np.asarray(data, dtype=np.float32)
    if sr != target_sr:
        gcd = math.gcd(int(sr), int(target_sr))
        audio = resample_poly(audio, target_sr // gcd, sr // gcd).astype(np.float32)
        sr = target_sr
    audio = np.nan_to_num(audio, nan=0.0, posinf=0.0, neginf=0.0)
    if audio.size == 0:
        raise ValueError(f"empty audio after loading: {path}")
    return audio, sr


def chunk_audio(audio: np.ndarray, sample_rate: int, chunk_seconds: float) -> tuple[list[np.ndarray], list[float]]:
    chunk_size = max(1, int(round(sample_rate * chunk_seconds)))
    chunks: list[np.ndarray] = []
    durations: list[float] = []
    for start in range(0, audio.size, chunk_size):
        chunk = audio[start : start + chunk_size]
        if chunk.size == 0:
            continue
        chunks.append(chunk)
        durations.append(float(chunk.size) / float(sample_rate))
    if not chunks:
        chunks = [audio]
        durations = [float(audio.size) / float(sample_rate)]
    return chunks, durations


def masked_mean_hidden(model: torch.nn.Module, hidden: torch.Tensor, attention_mask: torch.Tensor | None) -> torch.Tensor:
    if attention_mask is None:
        return hidden.mean(dim=1)
    try:
        feature_mask = model._get_feature_vector_attention_mask(hidden.shape[1], attention_mask).to(hidden.device)
    except TypeError:
        feature_mask = model._get_feature_vector_attention_mask(hidden.shape[1], attention_mask, add_adapter=False).to(hidden.device)
    feature_mask = feature_mask.to(dtype=hidden.dtype).unsqueeze(-1)
    denom = torch.clamp(feature_mask.sum(dim=1), min=1.0)
    return (hidden * feature_mask).sum(dim=1) / denom


def embed_audio(
    path: Path,
    feature_extractor: Any,
    model: torch.nn.Module,
    device: torch.device,
    *,
    chunk_seconds: float,
    chunk_batch_size: int,
) -> tuple[np.ndarray, int, float]:
    target_sr = int(getattr(feature_extractor, "sampling_rate", 16000) or 16000)
    audio, sr = read_audio(path, target_sr)
    chunks, durations = chunk_audio(audio, sr, chunk_seconds)
    embeddings: list[np.ndarray] = []
    weights: list[float] = []
    for start in range(0, len(chunks), chunk_batch_size):
        batch = chunks[start : start + chunk_batch_size]
        batch_weights = durations[start : start + chunk_batch_size]
        inputs = feature_extractor(
            batch,
            sampling_rate=target_sr,
            return_tensors="pt",
            padding=True,
            return_attention_mask=True,
        )
        input_values = inputs["input_values"].to(device)
        attention_mask = inputs.get("attention_mask")
        if attention_mask is not None:
            attention_mask = attention_mask.to(device)
        with torch.no_grad():
            output = model(input_values=input_values, attention_mask=attention_mask)
            pooled = masked_mean_hidden(model, output.last_hidden_state, attention_mask)
        embeddings.extend(pooled.detach().cpu().numpy())
        weights.extend(batch_weights)
    stacked = np.vstack(embeddings).astype(np.float64)
    weights_arr = np.asarray(weights, dtype=np.float64)
    segment_embedding = np.average(stacked, axis=0, weights=weights_arr)
    return segment_embedding.astype(np.float32), len(chunks), float(np.sum(weights_arr))


def save_segment_cache(path: Path, rows: list[dict[str, Any]]) -> None:
    frame = pd.DataFrame(rows)
    if not frame.empty:
        frame = frame.sort_values(["subject_id", "task_type", "segment_key"]).reset_index(drop=True)
    frame.to_csv(path, index=False)


def load_wavlm(model_name: str, device_name: str, local_files_only: bool) -> tuple[Any, torch.nn.Module, torch.device]:
    device = torch.device(device_name if device_name != "auto" else ("cuda" if torch.cuda.is_available() else "cpu"))
    feature_extractor = AutoFeatureExtractor.from_pretrained(model_name, local_files_only=local_files_only)
    model = AutoModel.from_pretrained(
        model_name,
        local_files_only=local_files_only,
        use_safetensors=False,
    )
    model.eval()
    for param in model.parameters():
        param.requires_grad_(False)
    model.to(device)
    return feature_extractor, model, device


def extract_segment_embeddings(
    segment_table: pd.DataFrame,
    out_dir: Path,
    *,
    model_name: str,
    device_name: str,
    local_files_only: bool,
    chunk_seconds: float,
    chunk_batch_size: int,
    force: bool,
) -> tuple[pd.DataFrame, list[str], dict[str, Any]]:
    cache_path = out_dir / "modma_wavlm_segment_embeddings.csv"
    required_keys = set(zip(segment_table["subject_id"], segment_table["segment_key"], strict=True))
    cached_rows: list[dict[str, Any]] = []
    cached_keys: set[tuple[str, str]] = set()
    if cache_path.exists() and not force:
        cached = pd.read_csv(cache_path)
        cached["subject_id"] = cached["subject_id"].astype(str)
        cached["segment_key"] = cached["segment_key"].astype(str)
        cached_keys = set(zip(cached["subject_id"], cached["segment_key"], strict=True))
        cached_rows = cached[
            [
                key in required_keys
                for key in zip(cached["subject_id"], cached["segment_key"], strict=True)
            ]
        ].to_dict("records")
    missing_rows = segment_table[
        [
            key not in cached_keys
            for key in zip(segment_table["subject_id"], segment_table["segment_key"], strict=True)
        ]
    ].reset_index(drop=True)

    embedding_rows = cached_rows
    embedding_columns = [
        column
        for column in pd.DataFrame(embedding_rows).columns
        if column.startswith("wavlm_")
    ] if embedding_rows else []
    extractor_summary: dict[str, Any] = {
        "model_name": model_name,
        "chunk_seconds": float(chunk_seconds),
        "chunk_batch_size": int(chunk_batch_size),
        "cached_segment_rows": int(len(cached_rows)),
        "missing_segment_rows": int(len(missing_rows)),
    }
    if not missing_rows.empty:
        feature_extractor, model, device = load_wavlm(model_name, device_name, local_files_only)
        extractor_summary.update(
            {
                "feature_extractor": type(feature_extractor).__name__,
                "model_class": type(model).__name__,
                "hidden_size": int(getattr(model.config, "hidden_size", 0) or 0),
                "sampling_rate": int(getattr(feature_extractor, "sampling_rate", 16000) or 16000),
                "device": str(device),
            }
        )
        if not embedding_columns:
            hidden_size = int(getattr(model.config, "hidden_size", 0) or 0)
            if hidden_size <= 0:
                raise ValueError("WavLM model config does not expose a positive hidden_size")
            embedding_columns = [f"wavlm_{idx:04d}" for idx in range(hidden_size)]
        print(
            f"Extracting MODMA WavLM embeddings: {len(missing_rows)} missing / {len(segment_table)} audio segments on {device}",
            flush=True,
        )
        for idx, row in missing_rows.iterrows():
            path = Path(str(row["audio_path"]))
            if not path.exists():
                raise FileNotFoundError(f"manifest audio path missing: {path}")
            if (idx + 1) == 1 or (idx + 1) % 25 == 0 or (idx + 1) == len(missing_rows):
                print(
                    f"  [modma-wavlm] {idx + 1}/{len(missing_rows)} subject={row['subject_id']} task={row['task_type']} segment={row['segment_id']}",
                    flush=True,
                )
            embedding, chunk_count, duration_seconds = embed_audio(
                path,
                feature_extractor,
                model,
                device,
                chunk_seconds=chunk_seconds,
                chunk_batch_size=chunk_batch_size,
            )
            embedding_rows.append(
                {
                    "subject_id": str(row["subject_id"]),
                    "task_type": str(row["task_type"]),
                    "segment_key": str(row["segment_key"]),
                    "chunk_count": int(chunk_count),
                    "duration_seconds": float(duration_seconds),
                    **{column: float(value) for column, value in zip(embedding_columns, embedding, strict=True)},
                }
            )
            if (idx + 1) % 25 == 0:
                save_segment_cache(cache_path, embedding_rows)
        save_segment_cache(cache_path, embedding_rows)
        del model
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
    if not embedding_columns:
        raise RuntimeError("no WavLM embeddings available")
    embeddings = pd.DataFrame(embedding_rows)
    observed_keys = set(zip(embeddings["subject_id"].astype(str), embeddings["segment_key"].astype(str), strict=True))
    missing_keys = required_keys - observed_keys
    if missing_keys:
        raise ValueError(f"missing cached WavLM rows: {sorted(missing_keys)[:5]}")
    selected = embeddings[
        [
            key in required_keys
            for key in zip(embeddings["subject_id"].astype(str), embeddings["segment_key"].astype(str), strict=True)
        ]
    ].copy()
    return selected.sort_values(["subject_id", "task_type", "segment_key"]).reset_index(drop=True), embedding_columns, extractor_summary


def average_embeddings(
    segment_embeddings: pd.DataFrame,
    embedding_columns: list[str],
    group_columns: list[str],
) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for key, group in segment_embeddings.groupby(group_columns, sort=False):
        if not isinstance(key, tuple):
            key = (key,)
        row = {column: str(value) for column, value in zip(group_columns, key, strict=True)}
        values = group[embedding_columns].to_numpy(dtype=np.float64)
        mean_values = np.nanmean(values, axis=0)
        row["audio_segment_count"] = int(len(group))
        row["duration_seconds_sum"] = float(group["duration_seconds"].sum())
        row["chunk_count_sum"] = int(group["chunk_count"].sum())
        if "task_type" not in row:
            row["task_types_observed"] = ";".join(sorted(group["task_type"].astype(str).unique()))
        for column, value in zip(embedding_columns, mean_values, strict=True):
            row[column] = float(value) if np.isfinite(value) else np.nan
        rows.append(row)
    return pd.DataFrame(rows).sort_values(
        group_columns,
        key=lambda series: series.map(lambda item: tuple(natural_key(item))),
    ).reset_index(drop=True)


def labels_by_subject(manifest_path: Path, subjects: set[str], target: str) -> pd.DataFrame:
    manifest = read_manifest(manifest_path)
    rows = manifest[manifest["subject_id"].astype(str).isin(subjects) & manifest[target].notna()].copy()
    labels: list[dict[str, Any]] = []
    for subject_id, group in rows.groupby("subject_id", sort=False):
        values = group[target].dropna().unique()
        if len(values) != 1:
            raise ValueError(f"{subject_id} has inconsistent {target}: {values[:5]}")
        value = values[0]
        labels.append({"subject_id": str(subject_id), target: int(value) if target == "binary_label" else float(value)})
    labels_frame = pd.DataFrame(labels)
    missing_subjects = sorted(subjects - set(labels_frame["subject_id"].astype(str)), key=natural_key)
    if missing_subjects:
        raise ValueError(f"subjects missing {target} labels: {missing_subjects[:10]}")
    return labels_frame


def merge_labels(features: pd.DataFrame, target: str) -> tuple[pd.DataFrame, list[str]]:
    subjects = set(features["subject_id"].astype(str))
    labels = labels_by_subject(MANIFEST_PATH, subjects, target)
    table = features.merge(labels, on="subject_id", how="inner")
    feature_columns = [
        column
        for column in table.columns
        if column.startswith("wavlm_")
    ]
    if not feature_columns:
        raise ValueError("no WavLM feature columns after label merge")
    return table, feature_columns


def classifier_pipeline(seed: int) -> Pipeline:
    return Pipeline(
        [
            ("imputer", SimpleImputer(strategy="median")),
            ("scaler", StandardScaler()),
            (
                "logistic",
                LogisticRegression(
                    C=FIXED_LOGISTIC_C,
                    class_weight="balanced",
                    max_iter=1000,
                    random_state=seed,
                    solver="liblinear",
                ),
            ),
        ]
    )


def ridge_pipeline(alpha: float) -> Pipeline:
    return Pipeline(
        [
            ("imputer", SimpleImputer(strategy="median")),
            ("scaler", StandardScaler()),
            ("ridge", Ridge(alpha=alpha, solver="lsqr")),
        ]
    )


def choose_ridge_alpha(train: pd.DataFrame, feature_columns: list[str], target: str, seed: int) -> tuple[float, list[dict[str, Any]]]:
    folds = KFold(n_splits=5, shuffle=True, random_state=seed)
    candidates: list[dict[str, Any]] = []
    best_key: tuple[float, float, float] | None = None
    best_alpha: float | None = None
    labels = train[target].to_numpy(dtype=np.float64)
    for alpha in RIDGE_ALPHA_GRID:
        y_true_all: list[float] = []
        y_pred_all: list[float] = []
        for train_idx, dev_idx in folds.split(train):
            inner_train = train.iloc[train_idx].reset_index(drop=True)
            inner_dev = train.iloc[dev_idx].reset_index(drop=True)
            model = ridge_pipeline(alpha)
            model.fit(inner_train[feature_columns], inner_train[target].to_numpy(dtype=np.float64))
            pred = model.predict(inner_dev[feature_columns])
            y_true_all.extend(inner_dev[target].to_numpy(dtype=np.float64).tolist())
            y_pred_all.extend(pred.tolist())
        metrics = regression_metrics(y_true_all, y_pred_all)
        mae = float(mean_absolute_error(y_true_all, y_pred_all))
        ccc = metrics["CCC"]
        candidates.append(
            {
                "alpha": float(alpha),
                "train_oof_mae": mae,
                "train_oof_ccc": float(ccc) if ccc is not None else None,
            }
        )
        candidate_key = (-mae, float(ccc) if ccc is not None else -1.0e9, -float(alpha))
        if best_key is None or candidate_key > best_key:
            best_key = candidate_key
            best_alpha = float(alpha)
    if best_alpha is None or labels.size == 0:
        raise RuntimeError("Ridge alpha selection failed")
    return best_alpha, candidates


def target_bounds(train: pd.DataFrame, target: str) -> tuple[float, float]:
    return float(train[target].min()), float(train[target].max())


def clip_predictions(y_pred: np.ndarray, bounds: tuple[float, float]) -> tuple[np.ndarray, int]:
    arr = np.asarray(y_pred, dtype=np.float64)
    clipped = np.clip(arr, bounds[0], bounds[1])
    return clipped, int(np.sum(np.abs(clipped - arr) > 1.0e-12))


def prediction_meta(
    spec: BaselineSpec,
    seed: int,
    fold: str,
    protocol_id: str,
    row: pd.Series,
    train_task: str = "",
    eval_task: str = "",
) -> dict[str, Any]:
    meta = {
        "run_id": spec.run_id,
        "dataset": "MODMA",
        "modality": "Audio",
        "task": spec.task,
        "model": spec.model,
        "seed": int(seed),
        "fold": fold,
        "protocol_id": protocol_id,
        "task_type": spec.task_type,
        "subject_id": row["subject_id"],
        "split": "validation",
        "audio_segment_count": int(row["audio_segment_count"]),
    }
    if train_task:
        meta["train_task"] = train_task
    if eval_task:
        meta["eval_task"] = eval_task
    return meta


def run_subject_classification(
    spec: BaselineSpec,
    table: pd.DataFrame,
    feature_columns: list[str],
    protocol: dict[str, Any],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    table_by_subject = table.set_index("subject_id", drop=False)
    predictions: list[dict[str, Any]] = []
    fold_summaries: list[dict[str, Any]] = []
    for seed in SEEDS:
        for fold, roles in protocol["folds"].items():
            train = table_by_subject.loc[roles["train"]].reset_index(drop=True)
            validation = table_by_subject.loc[roles["validation"]].reset_index(drop=True)
            model = classifier_pipeline(seed)
            model.fit(train[feature_columns], train[spec.target].astype(int))
            y_pred = model.predict(validation[feature_columns])
            y_score = model.predict_proba(validation[feature_columns])[:, 1]
            for idx, row in validation.iterrows():
                predictions.append(
                    {
                        **prediction_meta(spec, seed, fold, protocol["protocol_id"], row),
                        "y_true": int(row[spec.target]),
                        "y_pred": int(y_pred[idx]),
                        "y_score": float(y_score[idx]),
                    }
                )
            fold_summaries.append(
                {
                    "run_id": spec.run_id,
                    "protocol_id": protocol["protocol_id"],
                    "seed": int(seed),
                    "fold": fold,
                    "train_subjects": int(len(train)),
                    "validation_subjects": int(len(validation)),
                    "train_positive_subjects": int(train[spec.target].astype(int).sum()),
                    "validation_positive_subjects": int(validation[spec.target].astype(int).sum()),
                    "logistic_c": float(FIXED_LOGISTIC_C),
                }
            )
    return predictions, fold_summaries


def run_subject_regression(
    spec: BaselineSpec,
    table: pd.DataFrame,
    feature_columns: list[str],
    protocol: dict[str, Any],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    table_by_subject = table.set_index("subject_id", drop=False)
    predictions: list[dict[str, Any]] = []
    fold_summaries: list[dict[str, Any]] = []
    for seed in SEEDS:
        for fold, roles in protocol["folds"].items():
            train = table_by_subject.loc[roles["train"]].reset_index(drop=True)
            validation = table_by_subject.loc[roles["validation"]].reset_index(drop=True)
            alpha, alpha_candidates = choose_ridge_alpha(train, feature_columns, spec.target, seed)
            bounds = target_bounds(train, spec.target)
            model = ridge_pipeline(alpha)
            model.fit(train[feature_columns], train[spec.target].to_numpy(dtype=np.float64))
            y_pred_raw = model.predict(validation[feature_columns])
            y_pred, clip_count = clip_predictions(y_pred_raw, bounds)
            for idx, row in validation.iterrows():
                predictions.append(
                    {
                        **prediction_meta(spec, seed, fold, protocol["protocol_id"], row),
                        "y_true": float(row[spec.target]),
                        "y_pred": float(y_pred[idx]),
                        "y_score": "",
                        "prediction_clipped_to_train_target_range": True,
                    }
                )
            fold_summaries.append(
                {
                    "run_id": spec.run_id,
                    "protocol_id": protocol["protocol_id"],
                    "seed": int(seed),
                    "fold": fold,
                    "train_subjects": int(len(train)),
                    "validation_subjects": int(len(validation)),
                    "ridge_alpha": float(alpha),
                    "alpha_selection": "inner_5fold_train_oof_mae",
                    "alpha_candidates": alpha_candidates,
                    "target_min_train": float(bounds[0]),
                    "target_max_train": float(bounds[1]),
                    "validation_clip_count": int(clip_count),
                }
            )
    return predictions, fold_summaries


def run_task_protocols(
    spec: BaselineSpec,
    task_table: pd.DataFrame,
    feature_columns: list[str],
    protocols: dict[str, dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    task_index = task_table.set_index(["subject_id", "task_type"], drop=False)
    predictions: list[dict[str, Any]] = []
    fold_summaries: list[dict[str, Any]] = []
    for protocol_id, protocol in protocols.items():
        train_task = protocol["train_task"]
        eval_task = protocol["eval_task"]
        if train_task not in TASK_TYPES or eval_task not in TASK_TYPES:
            raise ValueError(f"{protocol_id} has invalid train/eval tasks: {train_task}, {eval_task}")
        for seed in SEEDS:
            for fold, roles in protocol["folds"].items():
                train_keys = [(subject, train_task) for subject in roles["train"]]
                validation_keys = [(subject, eval_task) for subject in roles["validation"]]
                train = task_index.loc[train_keys].reset_index(drop=True)
                validation = task_index.loc[validation_keys].reset_index(drop=True)
                model = classifier_pipeline(seed)
                model.fit(train[feature_columns], train[spec.target].astype(int))
                y_pred = model.predict(validation[feature_columns])
                y_score = model.predict_proba(validation[feature_columns])[:, 1]
                for idx, row in validation.iterrows():
                    predictions.append(
                        {
                            **prediction_meta(spec, seed, fold, protocol_id, row, train_task, eval_task),
                            "y_true": int(row[spec.target]),
                            "y_pred": int(y_pred[idx]),
                            "y_score": float(y_score[idx]),
                        }
                    )
                fold_summaries.append(
                    {
                        "run_id": spec.run_id,
                        "protocol_id": protocol_id,
                        "protocol_type": protocol["protocol_type"],
                        "seed": int(seed),
                        "fold": fold,
                        "train_task": train_task,
                        "eval_task": eval_task,
                        "train_subjects": int(len(train)),
                        "validation_subjects": int(len(validation)),
                        "train_positive_subjects": int(train[spec.target].astype(int).sum()),
                        "validation_positive_subjects": int(validation[spec.target].astype(int).sum()),
                        "logistic_c": float(FIXED_LOGISTIC_C),
                    }
                )
    return predictions, fold_summaries


def run_all_baselines(
    selected_specs: list[BaselineSpec],
    split_frame: pd.DataFrame,
    subject_features: pd.DataFrame,
    subject_task_features: pd.DataFrame,
) -> tuple[pd.DataFrame, list[dict[str, Any]]]:
    all_predictions: list[dict[str, Any]] = []
    run_summaries: list[dict[str, Any]] = []
    subject_binary_protocol = load_protocols(split_frame, target="binary_label", protocol_id="modma_binary_subject_cv")
    subject_phq9_protocol = load_protocols(split_frame, target="phq9_total", protocol_id="modma_phq9_subject_cv")
    task_specific_protocols = load_protocols(split_frame, target="binary_label", protocol_type="task_specific")
    cross_task_protocols = load_protocols(split_frame, target="binary_label", protocol_type="cross_task")

    subject_binary_table, subject_binary_features = merge_labels(subject_features, "binary_label")
    subject_phq9_table, subject_phq9_features = merge_labels(subject_features, "phq9_total")
    task_binary_table, task_binary_features = merge_labels(subject_task_features, "binary_label")

    for spec in selected_specs:
        if spec.protocol_kind == "subject_binary":
            protocol = subject_binary_protocol["modma_binary_subject_cv"]
            predictions, fold_summaries = run_subject_classification(spec, subject_binary_table, subject_binary_features, protocol)
            protocol_count = 1
        elif spec.protocol_kind == "subject_phq9":
            protocol = subject_phq9_protocol["modma_phq9_subject_cv"]
            predictions, fold_summaries = run_subject_regression(spec, subject_phq9_table, subject_phq9_features, protocol)
            protocol_count = 1
        elif spec.protocol_kind == "task_specific_binary":
            predictions, fold_summaries = run_task_protocols(spec, task_binary_table, task_binary_features, task_specific_protocols)
            protocol_count = len(task_specific_protocols)
        elif spec.protocol_kind == "cross_task_binary":
            predictions, fold_summaries = run_task_protocols(spec, task_binary_table, task_binary_features, cross_task_protocols)
            protocol_count = len(cross_task_protocols)
        else:
            raise ValueError(f"unknown protocol kind: {spec.protocol_kind}")
        all_predictions.extend(predictions)
        run_summaries.append(
            {
                "run_id": spec.run_id,
                "protocol_kind": spec.protocol_kind,
                "protocol_count": int(protocol_count),
                "prediction_rows": int(len(predictions)),
                "fold_summary_count": int(len(fold_summaries)),
                "fold_summaries": fold_summaries,
            }
        )
    return pd.DataFrame(all_predictions), run_summaries


def write_report(out_dir: Path, summary: dict[str, Any]) -> None:
    lines = [
        "# MODMA Frozen WavLM Phase 2 Baselines",
        "",
        f"Generated: `{summary['generated_at']}`",
        "",
        "## Protocol",
        "",
        "- Input interface: manifest-resolved valid MODMA audio paths and generated subject-level split protocols.",
        "- Encoder: frozen WavLM; no WavLM parameters are updated.",
        "- Segment embedding: audio is split into fixed-duration chunks, WavLM last hidden states are mean pooled, and chunk embeddings are duration-weighted averaged per segment.",
        "- Subject embedding: valid segment embeddings are averaged per subject.",
        "- Subject-task embedding: valid segment embeddings are averaged per subject and task.",
        "- Linear heads: LogisticRegression for binary tasks and Ridge regression for PHQ-9 regression.",
        "- PHQ-9 Ridge alpha is selected only inside the train split by inner 5-fold OOF MAE.",
        "- Regression outputs are clipped to the train-split observed target range.",
        "- No validation or test labels are used for encoder extraction or hyperparameter selection.",
        "- No test split is used.",
        "- Raw audio, source paths, and file names are not written to outputs.",
        "",
        "## Audit",
        "",
        f"- Runs: `{summary['runs']}`",
        f"- Subjects: `{summary['subject_count']}`",
        f"- Audio segments: `{summary['audio_segments']}`",
        f"- Invalid manifest audio rows excluded: `{summary['invalid_audio_rows_excluded']}`",
        f"- Segment embedding rows: `{summary['segment_embedding_rows']}`",
        f"- Subject feature rows: `{summary['subject_feature_rows']}`",
        f"- Subject-task feature rows: `{summary['subject_task_feature_rows']}`",
        f"- WavLM feature count: `{summary['feature_count']}`",
        f"- Seeds: `{summary['seeds']}`",
        f"- Bootstrap resamples: `{summary['bootstrap_resamples']}`",
        f"- Prediction rows: `{summary['prediction_rows']}`",
        f"- Raw audio written: `{summary['raw_audio_written']}`",
        f"- Source paths written: `{summary['source_paths_written']}`",
        "",
        "## Output Files",
        "",
        "- `modma_audio_wavlm_predictions.csv`",
        "- `modma_wavlm_segment_embeddings.csv`",
        "- `modma_wavlm_subject_features.csv`",
        "- `modma_wavlm_subject_task_features.csv`",
        "- `phase2_metrics_by_seed.csv`",
        "- `phase2_metric_summary.csv`",
        "- `modma_audio_wavlm_run_summary.json`",
    ]
    (out_dir / "modma_audio_wavlm_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, default=MANIFEST_PATH)
    parser.add_argument("--split-path", type=Path, default=SPLIT_PATH)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--model-name", default=DEFAULT_MODEL_NAME)
    parser.add_argument("--device", default="auto")
    parser.add_argument("--local-files-only", action="store_true")
    parser.add_argument("--chunk-seconds", type=float, default=20.0)
    parser.add_argument("--chunk-batch-size", type=int, default=1)
    parser.add_argument("--bootstrap-resamples", type=int, default=1000)
    parser.add_argument("--force-embeddings", action="store_true")
    parser.add_argument("--run-id", action="append", choices=[spec.run_id for spec in SPECS])
    args = parser.parse_args()

    args.out_dir.mkdir(parents=True, exist_ok=True)
    split_frame = load_split_frame(args.split_path)
    split_subjects = set(split_frame["subject_id"].astype(str))
    segment_table = build_segment_table(args.manifest, split_subjects)
    segment_embeddings, embedding_columns, extractor_summary = extract_segment_embeddings(
        segment_table,
        args.out_dir,
        model_name=args.model_name,
        device_name=args.device,
        local_files_only=args.local_files_only,
        chunk_seconds=args.chunk_seconds,
        chunk_batch_size=args.chunk_batch_size,
        force=args.force_embeddings,
    )
    subject_features = average_embeddings(segment_embeddings, embedding_columns, ["subject_id"])
    subject_task_features = average_embeddings(segment_embeddings, embedding_columns, ["subject_id", "task_type"])
    subject_features.to_csv(args.out_dir / "modma_wavlm_subject_features.csv", index=False)
    subject_task_features.to_csv(args.out_dir / "modma_wavlm_subject_task_features.csv", index=False)

    selected_specs = [spec for spec in SPECS if not args.run_id or spec.run_id in set(args.run_id)]
    predictions_frame, run_summaries = run_all_baselines(selected_specs, split_frame, subject_features, subject_task_features)
    predictions_path = args.out_dir / "modma_audio_wavlm_predictions.csv"
    predictions_frame.to_csv(predictions_path, index=False)

    metrics_by_seed, metric_summary = metric_records(
        predictions_frame,
        bootstrap_resamples=args.bootstrap_resamples,
        seed=20260727,
    )
    metrics_by_seed.to_csv(args.out_dir / "phase2_metrics_by_seed.csv", index=False)
    metric_summary.to_csv(args.out_dir / "phase2_metric_summary.csv", index=False)

    manifest = read_manifest(args.manifest)
    invalid_audio_rows = int((~manifest["file_valid"].fillna(False).astype(bool) & manifest["audio_path"].notna()).sum())
    run_summary = {
        "generated_at": utc_now(),
        "manifest": str(args.manifest),
        "split_path": str(args.split_path),
        "runs": [spec.run_id for spec in selected_specs],
        "model_name": args.model_name,
        "extractor_summary": extractor_summary,
        "seeds": SEEDS,
        "seed_count": len(SEEDS),
        "bootstrap_resamples": int(args.bootstrap_resamples),
        "subject_count": int(len(split_subjects)),
        "audio_segments": int(len(segment_table)),
        "invalid_audio_rows_excluded": invalid_audio_rows,
        "segment_embedding_rows": int(len(segment_embeddings)),
        "subject_feature_rows": int(len(subject_features)),
        "subject_task_feature_rows": int(len(subject_task_features)),
        "feature_count": int(len(embedding_columns)),
        "prediction_rows": int(len(predictions_frame)),
        "task_types": TASK_TYPES,
        "run_summaries": run_summaries,
        "encoder_frozen": True,
        "no_test_split_used": True,
        "raw_audio_written": False,
        "source_paths_written": False,
    }
    (args.out_dir / "modma_audio_wavlm_run_summary.json").write_text(
        json.dumps(run_summary, indent=2, ensure_ascii=True, sort_keys=True),
        encoding="utf-8",
    )
    write_report(args.out_dir, run_summary)
    print(f"Wrote {predictions_path}")
    print(f"Wrote {args.out_dir / 'phase2_metric_summary.csv'}")


if __name__ == "__main__":
    main()
