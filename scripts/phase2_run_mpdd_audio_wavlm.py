#!/usr/bin/env python3
"""Run Phase 2 MPDD frozen WavLM audio baselines.

The runner extracts frozen WavLM segment embeddings from manifest-resolved
MPDD audio, averages them to subject embeddings, and evaluates the two planned
MPDD audio rows: PHQ-9 regression with a linear Ridge head and ordinal
severity prediction with an MLP head. It ignores unlabeled test rows and writes
no raw audio, source paths, or model checkpoints.
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
from sklearn.linear_model import Ridge
from sklearn.metrics import mean_absolute_error
from sklearn.model_selection import KFold, StratifiedKFold
from sklearn.neural_network import MLPClassifier
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from transformers import AutoFeatureExtractor, AutoModel

from phase2_metrics import metric_records, regression_metrics


warnings.filterwarnings("ignore", message="Support for mismatched key_padding_mask.*")

ROOT = Path("/root/autodl-tmp")
MANIFEST_PATH = ROOT / "datasets" / "manifests" / "mpdd_avg_2026_subjects.csv"
DEFAULT_OUT_DIR = ROOT / "analysis" / "phase2_baselines" / "mpdd_audio_wavlm"
DEFAULT_MODEL_NAME = "microsoft/wavlm-base-plus"
DATASET_DISPLAY = "MPDD-AVG-2026"
SEEDS = [0, 1, 2, 3, 4]
RIDGE_ALPHA_GRID = [1.0, 10.0, 100.0, 1000.0]
MLP_HIDDEN_LAYER_SIZES = (64,)
MLP_ALPHA = 0.01
MLP_MAX_ITER = 1000


@dataclass(frozen=True)
class BaselineSpec:
    run_id: str
    task: str
    task_type: str
    target: str
    model: str


PHQ9_SPEC = BaselineSpec(
    run_id="mpdd_audio_phq9_wavlm_linear",
    task="PHQ-9 regression",
    task_type="severity_regression",
    target="phq9_total",
    model="WavLM frozen embedding + linear",
)

SEVERITY_SPEC = BaselineSpec(
    run_id="mpdd_audio_severity_wavlm_mlp",
    task="ordinal severity prediction",
    task_type="ordinal_prediction",
    target="severity_label",
    model="WavLM frozen embedding + MLP",
)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def natural_key(value: Any) -> list[Any]:
    return [int(part) if part.isdigit() else part for part in re.split(r"(\d+)", str(value))]


def read_manifest(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"manifest missing: {path}")
    return pd.read_csv(path)


def build_segment_table(manifest_path: Path) -> pd.DataFrame:
    manifest = read_manifest(manifest_path)
    required = {
        "subject_id",
        "audio_path",
        "segment_id",
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
        & manifest["audio_path"].notna()
        & manifest["phq9_total"].notna()
        & manifest["severity_label"].notna()
        & manifest["official_split"].eq("train")
    ].copy()
    if rows.empty:
        raise ValueError("no labeled MPDD train audio rows")
    rows = rows.drop_duplicates(["subject_id", "segment_id", "audio_path"]).copy()
    rows = rows.sort_values(["subject_id", "segment_id"]).reset_index(drop=True)
    rows["subject_id"] = rows["subject_id"].astype(str)
    rows["segment_key"] = rows.apply(
        lambda row: "::".join([str(row.get("session_id", "")), str(row.get("segment_id", "")), str(row.name)]),
        axis=1,
    )
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
    min_chunk_seconds: float,
) -> tuple[np.ndarray, int, float, int]:
    target_sr = int(getattr(feature_extractor, "sampling_rate", 16000) or 16000)
    audio, sr = read_audio(path, target_sr)
    chunks, durations = chunk_audio(audio, sr, chunk_seconds)
    padded_chunks = 0
    min_samples = int(round(target_sr * min_chunk_seconds))
    if min_samples > 0:
        padded: list[np.ndarray] = []
        for chunk in chunks:
            if chunk.size < min_samples:
                padded_chunks += 1
                chunk = np.pad(chunk, (0, min_samples - chunk.size), mode="constant")
            padded.append(chunk)
        chunks = padded
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
    return segment_embedding.astype(np.float32), len(chunks), float(np.sum(weights_arr)), int(padded_chunks)


def load_wavlm(model_name: str, device_name: str, local_files_only: bool) -> tuple[Any, torch.nn.Module, torch.device]:
    device = torch.device(device_name if device_name != "auto" else ("cuda" if torch.cuda.is_available() else "cpu"))
    feature_extractor = AutoFeatureExtractor.from_pretrained(model_name, local_files_only=local_files_only)
    model = AutoModel.from_pretrained(model_name, local_files_only=local_files_only, use_safetensors=False)
    model.eval()
    for param in model.parameters():
        param.requires_grad_(False)
    model.to(device)
    return feature_extractor, model, device


def save_segment_cache(path: Path, rows: list[dict[str, Any]]) -> None:
    frame = pd.DataFrame(rows)
    if not frame.empty:
        frame = frame.sort_values(["subject_id", "segment_key"]).reset_index(drop=True)
    frame.to_csv(path, index=False)


def extract_segment_embeddings(
    segment_table: pd.DataFrame,
    out_dir: Path,
    *,
    model_name: str,
    device_name: str,
    local_files_only: bool,
    chunk_seconds: float,
    chunk_batch_size: int,
    min_chunk_seconds: float,
    force: bool,
) -> tuple[pd.DataFrame, list[str], dict[str, Any]]:
    cache_path = out_dir / "mpdd_wavlm_segment_embeddings.csv"
    required_keys = set(zip(segment_table["subject_id"], segment_table["segment_key"], strict=True))
    cached_rows: list[dict[str, Any]] = []
    cached_keys: set[tuple[str, str]] = set()
    if cache_path.exists() and not force:
        cached = pd.read_csv(cache_path)
        cached["subject_id"] = cached["subject_id"].astype(str)
        cached["segment_key"] = cached["segment_key"].astype(str)
        cached_keys = set(zip(cached["subject_id"], cached["segment_key"], strict=True))
        cached_rows = cached[
            [key in required_keys for key in zip(cached["subject_id"], cached["segment_key"], strict=True)]
        ].to_dict("records")
    missing_rows = segment_table[
        [key not in cached_keys for key in zip(segment_table["subject_id"], segment_table["segment_key"], strict=True)]
    ].reset_index(drop=True)
    embedding_rows = cached_rows
    embedding_columns = [
        column for column in pd.DataFrame(embedding_rows).columns if column.startswith("wavlm_")
    ] if embedding_rows else []
    extractor_summary: dict[str, Any] = {
        "model_name": model_name,
        "chunk_seconds": float(chunk_seconds),
        "chunk_batch_size": int(chunk_batch_size),
        "min_chunk_seconds": float(min_chunk_seconds),
        "cached_segment_rows": int(len(cached_rows)),
        "missing_segment_rows": int(len(missing_rows)),
    }
    padded_chunk_total = 0
    chunk_total = 0
    duration_total = 0.0
    if not missing_rows.empty:
        feature_extractor, model, device = load_wavlm(model_name, device_name, local_files_only)
        hidden_size = int(getattr(model.config, "hidden_size", 0) or 0)
        if hidden_size <= 0:
            raise ValueError("WavLM model config does not expose a positive hidden_size")
        if not embedding_columns:
            embedding_columns = [f"wavlm_{idx:04d}" for idx in range(hidden_size)]
        extractor_summary.update(
            {
                "feature_extractor": type(feature_extractor).__name__,
                "model_class": type(model).__name__,
                "hidden_size": hidden_size,
                "sampling_rate": int(getattr(feature_extractor, "sampling_rate", 16000) or 16000),
                "device": str(device),
            }
        )
        print(
            f"Extracting MPDD WavLM embeddings: {len(missing_rows)} missing / {len(segment_table)} audio segments on {device}",
            flush=True,
        )
        for idx, row in missing_rows.iterrows():
            path = Path(str(row["audio_path"]))
            if not path.exists():
                raise FileNotFoundError(f"manifest audio path missing: {path}")
            if (idx + 1) == 1 or (idx + 1) % 25 == 0 or (idx + 1) == len(missing_rows):
                print(
                    f"  [mpdd-wavlm] {idx + 1}/{len(missing_rows)} subject={row['subject_id']} segment={row['segment_id']}",
                    flush=True,
                )
            embedding, chunk_count, duration_seconds, padded_chunks = embed_audio(
                path,
                feature_extractor,
                model,
                device,
                chunk_seconds=chunk_seconds,
                chunk_batch_size=chunk_batch_size,
                min_chunk_seconds=min_chunk_seconds,
            )
            chunk_total += int(chunk_count)
            duration_total += float(duration_seconds)
            padded_chunk_total += int(padded_chunks)
            embedding_rows.append(
                {
                    "subject_id": str(row["subject_id"]),
                    "segment_key": str(row["segment_key"]),
                    "segment_id": str(row["segment_id"]),
                    "age_group": str(row["age"]),
                    "chunk_count": int(chunk_count),
                    "duration_seconds": float(duration_seconds),
                    "padded_short_chunks": int(padded_chunks),
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
        [key in required_keys for key in zip(embeddings["subject_id"].astype(str), embeddings["segment_key"].astype(str), strict=True)]
    ].copy()
    extractor_summary.update(
        {
            "new_chunk_count": int(chunk_total),
            "new_duration_seconds": float(duration_total),
            "new_padded_short_chunks": int(padded_chunk_total),
            "selected_segment_rows": int(len(selected)),
            "selected_chunk_count": int(pd.to_numeric(selected["chunk_count"]).sum()),
            "selected_duration_seconds": float(pd.to_numeric(selected["duration_seconds"]).sum()),
            "selected_padded_short_chunks": int(pd.to_numeric(selected["padded_short_chunks"]).sum()),
        }
    )
    return selected.sort_values(["subject_id", "segment_key"]).reset_index(drop=True), embedding_columns, extractor_summary


def average_subject_embeddings(segment_embeddings: pd.DataFrame, embedding_columns: list[str]) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for subject_id, group in segment_embeddings.groupby("subject_id", sort=False):
        values = group[embedding_columns].to_numpy(dtype=np.float64)
        mean_values = np.nanmean(values, axis=0)
        rows.append(
            {
                "subject_id": str(subject_id),
                "age_group": str(group["age_group"].iloc[0]),
                "audio_segment_count": int(len(group)),
                "duration_seconds_sum": float(group["duration_seconds"].sum()),
                "chunk_count_sum": int(group["chunk_count"].sum()),
                "padded_short_chunks_sum": int(group["padded_short_chunks"].sum()),
                **{column: float(value) for column, value in zip(embedding_columns, mean_values, strict=True)},
            }
        )
    return pd.DataFrame(rows).sort_values("subject_id", key=lambda series: series.map(lambda item: tuple(natural_key(item)))).reset_index(drop=True)


def labels_by_subject(manifest_path: Path, subjects: set[str]) -> pd.DataFrame:
    manifest = read_manifest(manifest_path)
    rows = manifest[
        manifest["subject_id"].astype(str).isin(subjects)
        & manifest["phq9_total"].notna()
        & manifest["severity_label"].notna()
        & manifest["official_split"].eq("train")
    ].copy()
    labels: list[dict[str, Any]] = []
    for subject_id, group in rows.groupby("subject_id", sort=False):
        phq_values = group["phq9_total"].dropna().unique()
        severity_values = group["severity_label"].dropna().unique()
        if len(phq_values) != 1 or len(severity_values) != 1:
            raise ValueError(f"{subject_id} has inconsistent MPDD labels")
        labels.append(
            {
                "subject_id": str(subject_id),
                "phq9_total": float(phq_values[0]),
                "severity_label": int(severity_values[0]),
            }
        )
    labels_frame = pd.DataFrame(labels)
    missing_subjects = sorted(subjects - set(labels_frame["subject_id"].astype(str)), key=natural_key)
    if missing_subjects:
        raise ValueError(f"subjects missing labels: {missing_subjects[:10]}")
    return labels_frame


def build_subject_table(segment_embeddings: pd.DataFrame, embedding_columns: list[str], manifest_path: Path, out_dir: Path) -> tuple[pd.DataFrame, list[str]]:
    features = average_subject_embeddings(segment_embeddings, embedding_columns)
    labels = labels_by_subject(manifest_path, set(features["subject_id"].astype(str)))
    table = features.merge(labels, on="subject_id", how="inner")
    if table.empty:
        raise ValueError("no labeled MPDD audio subject embeddings")
    feature_columns = [column for column in table.columns if column.startswith("wavlm_")]
    features.to_csv(out_dir / "mpdd_wavlm_subject_features.csv", index=False)
    return table.sort_values("subject_id", key=lambda series: series.map(lambda item: tuple(natural_key(item)))).reset_index(drop=True), feature_columns


def ridge_pipeline(alpha: float) -> Pipeline:
    return Pipeline(
        [
            ("imputer", SimpleImputer(strategy="median")),
            ("scaler", StandardScaler()),
            ("ridge", Ridge(alpha=alpha, solver="lsqr")),
        ]
    )


def choose_ridge_alpha(train: pd.DataFrame, feature_columns: list[str], seed: int) -> tuple[float, list[dict[str, Any]]]:
    folds = KFold(n_splits=5, shuffle=True, random_state=seed)
    candidates: list[dict[str, Any]] = []
    best_key: tuple[float, float, float] | None = None
    best_alpha: float | None = None
    for alpha in RIDGE_ALPHA_GRID:
        y_true_all: list[float] = []
        y_pred_all: list[float] = []
        for train_idx, dev_idx in folds.split(train):
            inner_train = train.iloc[train_idx].reset_index(drop=True)
            inner_dev = train.iloc[dev_idx].reset_index(drop=True)
            model = ridge_pipeline(alpha)
            model.fit(inner_train[feature_columns], inner_train["phq9_total"].to_numpy(dtype=np.float64))
            pred = model.predict(inner_dev[feature_columns])
            y_true_all.extend(inner_dev["phq9_total"].to_numpy(dtype=np.float64).tolist())
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
    if best_alpha is None:
        raise RuntimeError("Ridge alpha selection failed")
    return best_alpha, candidates


def clip_predictions(y_pred: np.ndarray, train_target: pd.Series) -> tuple[np.ndarray, int, tuple[float, float]]:
    bounds = (float(train_target.min()), float(train_target.max()))
    arr = np.asarray(y_pred, dtype=np.float64)
    clipped = np.clip(arr, bounds[0], bounds[1])
    return clipped, int(np.sum(np.abs(clipped - arr) > 1.0e-12)), bounds


def mlp_pipeline(seed: int) -> Pipeline:
    return Pipeline(
        [
            ("imputer", SimpleImputer(strategy="median")),
            ("scaler", StandardScaler()),
            (
                "mlp",
                MLPClassifier(
                    hidden_layer_sizes=MLP_HIDDEN_LAYER_SIZES,
                    alpha=MLP_ALPHA,
                    solver="lbfgs",
                    max_iter=MLP_MAX_ITER,
                    random_state=seed,
                ),
            ),
        ]
    )


def prediction_meta(spec: BaselineSpec, seed: int, fold: int, row: pd.Series) -> dict[str, Any]:
    return {
        "run_id": spec.run_id,
        "dataset": DATASET_DISPLAY,
        "modality": "Audio",
        "task": spec.task,
        "model": spec.model,
        "seed": int(seed),
        "fold": int(fold),
        "task_type": spec.task_type,
        "subject_id": str(row["subject_id"]),
        "split": "train_oof",
        "age_group": str(row["age_group"]),
        "audio_segment_count": int(row["audio_segment_count"]),
    }


def run_oof(table: pd.DataFrame, feature_columns: list[str]) -> tuple[pd.DataFrame, list[dict[str, Any]]]:
    labels = table["severity_label"].to_numpy(dtype=np.int64)
    class_labels = sorted(int(value) for value in np.unique(labels))
    predictions: list[dict[str, Any]] = []
    fold_summaries: list[dict[str, Any]] = []
    for seed in SEEDS:
        folds = StratifiedKFold(n_splits=5, shuffle=True, random_state=seed)
        for fold, (train_idx, heldout_idx) in enumerate(folds.split(table, labels), start=1):
            train = table.iloc[train_idx].reset_index(drop=True)
            heldout = table.iloc[heldout_idx].reset_index(drop=True)

            alpha, alpha_candidates = choose_ridge_alpha(train, feature_columns, seed + fold)
            ridge = ridge_pipeline(alpha)
            ridge.fit(train[feature_columns], train["phq9_total"].to_numpy(dtype=np.float64))
            phq_raw = ridge.predict(heldout[feature_columns])
            phq_pred, clip_count, bounds = clip_predictions(phq_raw, train["phq9_total"])
            for idx, row in heldout.iterrows():
                predictions.append(
                    {
                        **prediction_meta(PHQ9_SPEC, seed, fold, row),
                        "y_true": float(row["phq9_total"]),
                        "y_pred": float(phq_pred[idx]),
                        "y_score": "",
                    }
                )

            mlp = mlp_pipeline(seed + fold)
            mlp.fit(train[feature_columns], train["severity_label"].astype(int))
            severity_pred = mlp.predict(heldout[feature_columns]).astype(int)
            raw_prob = mlp.predict_proba(heldout[feature_columns])
            probabilities = np.zeros((len(heldout), max(class_labels) + 1), dtype=np.float64)
            local_classes = [int(value) for value in mlp.named_steps["mlp"].classes_]
            for local_idx, class_value in enumerate(local_classes):
                probabilities[:, class_value] = raw_prob[:, local_idx]
            for idx, row in heldout.iterrows():
                predictions.append(
                    {
                        **prediction_meta(SEVERITY_SPEC, seed, fold, row),
                        "y_true": int(row["severity_label"]),
                        "y_pred": int(severity_pred[idx]),
                        "y_prob": json.dumps([float(value) for value in probabilities[idx]], ensure_ascii=True),
                    }
                )

            fold_summaries.append(
                {
                    "seed": int(seed),
                    "fold": int(fold),
                    "train_subjects": int(len(train)),
                    "heldout_subjects": int(len(heldout)),
                    "train_severity_counts": {str(k): int(v) for k, v in train["severity_label"].astype(int).value_counts().sort_index().items()},
                    "heldout_severity_counts": {str(k): int(v) for k, v in heldout["severity_label"].astype(int).value_counts().sort_index().items()},
                    "ridge_alpha": float(alpha),
                    "ridge_alpha_candidates": alpha_candidates,
                    "train_phq9_min": float(bounds[0]),
                    "train_phq9_max": float(bounds[1]),
                    "phq9_validation_clip_count": int(clip_count),
                }
            )
    return pd.DataFrame(predictions), fold_summaries


def write_report(out_dir: Path, summary: dict[str, Any]) -> None:
    lines = [
        "# MPDD Frozen WavLM Audio Phase 2 Baselines",
        "",
        f"Generated: `{summary['generated_at']}`",
        "",
        "## Protocol",
        "",
        "- Input interface: `datasets/manifests/mpdd_avg_2026_subjects.csv`.",
        "- Encoder: frozen `microsoft/wavlm-base-plus`; no WavLM parameters are updated.",
        "- Segment embedding: split audio into fixed-duration chunks, mean-pool WavLM last hidden states, and duration-weight chunk embeddings per segment.",
        "- Subject embedding: average valid audio-task segment embeddings per subject.",
        "- PHQ-9 row: Ridge regression with alpha selected only inside each train fold by inner 5-fold OOF MAE.",
        "- Severity row: fixed one-hidden-layer MLP classifier over frozen subject embeddings.",
        "- Evaluation: five repeated stratified 5-fold subject-level out-of-fold runs over labeled MPDD train subjects.",
        "- PHQ-9 regression outputs are clipped to the train-fold observed target range.",
        "- No validation/test labels are used for encoder extraction or hyperparameter selection.",
        "- Unlabeled MPDD test rows are ignored.",
        "- No raw audio, source paths, or checkpoints are written to outputs.",
        "",
        "## Audit",
        "",
        f"- Runs: `{summary['runs']}`",
        f"- Labeled audio subjects: `{summary['subject_count']}`",
        f"- Audio segments: `{summary['segment_rows']}`",
        f"- Audio hours: `{summary['audio_hours']}`",
        f"- WavLM chunks: `{summary['chunk_count']}`",
        f"- Padded short chunks: `{summary['padded_short_chunks']}`",
        f"- WavLM feature columns: `{summary['feature_count']}`",
        f"- Seeds: `{summary['seeds']}`",
        f"- Bootstrap resamples: `{summary['bootstrap_resamples']}`",
        f"- Prediction rows: `{summary['prediction_rows']}`",
        f"- PHQ-9 prediction clip count: `{summary['phq9_clip_count_total']}`",
        f"- Raw audio written: `{summary['raw_audio_written']}`",
        f"- Source paths written: `{summary['source_paths_written']}`",
        f"- Checkpoints written: `{summary['checkpoints_written']}`",
        "",
        "## Output Files",
        "",
        "- `mpdd_audio_wavlm_predictions.csv`",
        "- `mpdd_wavlm_segment_embeddings.csv`",
        "- `mpdd_wavlm_subject_features.csv`",
        "- `phase2_metrics_by_seed.csv`",
        "- `phase2_metric_summary.csv`",
        "- `mpdd_audio_wavlm_run_summary.json`",
    ]
    (out_dir / "mpdd_audio_wavlm_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest-path", type=Path, default=MANIFEST_PATH)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--model-name", default=DEFAULT_MODEL_NAME)
    parser.add_argument("--device", default="auto")
    parser.add_argument("--local-files-only", action="store_true")
    parser.add_argument("--chunk-seconds", type=float, default=20.0)
    parser.add_argument("--chunk-batch-size", type=int, default=8)
    parser.add_argument("--min-chunk-seconds", type=float, default=1.0)
    parser.add_argument("--force-embeddings", action="store_true")
    parser.add_argument("--bootstrap-resamples", type=int, default=1000)
    args = parser.parse_args()

    args.out_dir.mkdir(parents=True, exist_ok=True)
    segment_table = build_segment_table(args.manifest_path)
    segment_embeddings, embedding_columns, extractor_summary = extract_segment_embeddings(
        segment_table,
        args.out_dir,
        model_name=args.model_name,
        device_name=args.device,
        local_files_only=args.local_files_only,
        chunk_seconds=args.chunk_seconds,
        chunk_batch_size=args.chunk_batch_size,
        min_chunk_seconds=args.min_chunk_seconds,
        force=args.force_embeddings,
    )
    subject_table, feature_columns = build_subject_table(segment_embeddings, embedding_columns, args.manifest_path, args.out_dir)
    predictions, fold_summaries = run_oof(subject_table, feature_columns)

    predictions_path = args.out_dir / "mpdd_audio_wavlm_predictions.csv"
    predictions.to_csv(predictions_path, index=False)
    metrics_by_seed, metric_summary = metric_records(
        predictions,
        bootstrap_resamples=args.bootstrap_resamples,
        seed=20260727,
    )
    metrics_by_seed.to_csv(args.out_dir / "phase2_metrics_by_seed.csv", index=False)
    metric_summary.to_csv(args.out_dir / "phase2_metric_summary.csv", index=False)

    phq_clip_count = int(sum(row["phq9_validation_clip_count"] for row in fold_summaries))
    run_summary = {
        "generated_at": utc_now(),
        "manifest_path": str(args.manifest_path),
        "runs": [PHQ9_SPEC.run_id, SEVERITY_SPEC.run_id],
        "seeds": SEEDS,
        "bootstrap_resamples": int(args.bootstrap_resamples),
        "subject_count": int(subject_table["subject_id"].nunique()),
        "age_group_counts": {str(k): int(v) for k, v in subject_table["age_group"].value_counts().sort_index().items()},
        "severity_counts": {str(k): int(v) for k, v in subject_table["severity_label"].astype(int).value_counts().sort_index().items()},
        "segment_rows": int(len(segment_embeddings)),
        "audio_hours": float(segment_embeddings["duration_seconds"].sum() / 3600.0),
        "chunk_count": int(segment_embeddings["chunk_count"].sum()),
        "padded_short_chunks": int(segment_embeddings["padded_short_chunks"].sum()),
        "feature_count": int(len(feature_columns)),
        "prediction_rows": int(len(predictions)),
        "phq9_clip_count_total": phq_clip_count,
        "fold_summaries": fold_summaries,
        "embedding_extractor": extractor_summary,
        "no_test_split_used": True,
        "raw_audio_written": False,
        "source_paths_written": False,
        "checkpoints_written": False,
    }
    (args.out_dir / "mpdd_audio_wavlm_run_summary.json").write_text(
        json.dumps(run_summary, indent=2, ensure_ascii=True, sort_keys=True),
        encoding="utf-8",
    )
    write_report(args.out_dir, run_summary)
    print(f"Wrote {predictions_path}")
    print(f"Wrote {args.out_dir / 'phase2_metric_summary.csv'}")


if __name__ == "__main__":
    main()
