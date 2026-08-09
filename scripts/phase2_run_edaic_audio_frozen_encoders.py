#!/usr/bin/env python3
"""Run Phase 2 E-DAIC frozen audio-encoder baselines.

This runner extracts frozen WavLM and wav2vec2 subject embeddings from
manifest-resolved E-DAIC audio, then evaluates simple regression heads on the
official train/dev split. Encoder weights are never updated, test subjects are
not used, and outputs avoid raw audio, source paths, and file names.
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
from sklearn.model_selection import KFold
from sklearn.neural_network import MLPRegressor
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from transformers import AutoFeatureExtractor, AutoModel

from phase2_metrics import metric_records, regression_metrics


warnings.filterwarnings("ignore", message="Support for mismatched key_padding_mask.*")

ROOT = Path("/root/autodl-tmp")
MANIFEST_PATH = ROOT / "datasets" / "manifests" / "edaic_subjects.csv"
DEFAULT_OUT_DIR = ROOT / "analysis" / "phase2_baselines" / "edaic_audio_frozen_encoders"
SEEDS = [0, 1, 2, 3, 4]
RIDGE_ALPHA_GRID = [1.0, 10.0, 100.0, 1000.0]
MLP_HIDDEN_LAYER_SIZES = (64,)
MLP_ALPHA = 0.01
MLP_MAX_ITER = 2000
MIN_CHUNK_SECONDS = 1.0


@dataclass(frozen=True)
class EncoderSpec:
    encoder_id: str
    model_name: str
    model_label: str
    feature_prefix: str


@dataclass(frozen=True)
class HeadSpec:
    run_id: str
    encoder_id: str
    model_label: str
    head_type: str


ENCODER_SPECS = [
    EncoderSpec(
        encoder_id="wavlm",
        model_name="microsoft/wavlm-base-plus",
        model_label="WavLM frozen embedding",
        feature_prefix="wavlm_",
    ),
    EncoderSpec(
        encoder_id="wav2vec2",
        model_name="facebook/wav2vec2-base",
        model_label="wav2vec2 frozen embedding",
        feature_prefix="wav2vec2_",
    ),
]

HEAD_SPECS = [
    HeadSpec(
        run_id="edaic_audio_phq8_wavlm_linear",
        encoder_id="wavlm",
        model_label="WavLM frozen embedding + linear",
        head_type="linear",
    ),
    HeadSpec(
        run_id="edaic_audio_phq8_wavlm_mlp",
        encoder_id="wavlm",
        model_label="WavLM frozen embedding + MLP",
        head_type="mlp",
    ),
    HeadSpec(
        run_id="edaic_audio_phq8_wav2vec2_linear",
        encoder_id="wav2vec2",
        model_label="wav2vec2 frozen embedding + linear",
        head_type="linear",
    ),
    HeadSpec(
        run_id="edaic_audio_phq8_wav2vec2_mlp",
        encoder_id="wav2vec2",
        model_label="wav2vec2 frozen embedding + MLP",
        head_type="mlp",
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


def build_subject_table(manifest_path: Path) -> pd.DataFrame:
    manifest = read_manifest(manifest_path)
    required = {"subject_id", "official_split", "audio_path", "phq8_total", "file_valid"}
    missing = required - set(manifest.columns)
    if missing:
        raise ValueError(f"E-DAIC manifest missing columns: {', '.join(sorted(missing))}")
    rows = manifest[
        manifest["file_valid"].fillna(False).astype(bool)
        & manifest["official_split"].isin(["train", "dev"])
        & manifest["audio_path"].notna()
        & manifest["phq8_total"].notna()
    ].copy()
    if rows.empty:
        raise ValueError("no usable E-DAIC train/dev audio rows")
    rows["subject_id"] = rows["subject_id"].astype(str)
    if rows["subject_id"].duplicated().any():
        dupes = sorted(rows.loc[rows["subject_id"].duplicated(), "subject_id"].unique(), key=natural_key)
        raise ValueError(f"E-DAIC manifest should have one audio row per subject, duplicates: {dupes[:10]}")
    train_subjects = set(rows.loc[rows["official_split"] == "train", "subject_id"])
    dev_subjects = set(rows.loc[rows["official_split"] == "dev", "subject_id"])
    overlap = sorted(train_subjects & dev_subjects, key=natural_key)
    if overlap:
        raise ValueError(f"E-DAIC train/dev subject overlap detected: {overlap[:10]}")
    if not train_subjects or not dev_subjects:
        raise ValueError("E-DAIC frozen audio encoders require non-empty train and dev splits")
    return rows.sort_values("subject_id", key=lambda series: series.map(lambda item: tuple(natural_key(item)))).reset_index(drop=True)


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
        feature_mask = model._get_feature_vector_attention_mask(
            hidden.shape[1],
            attention_mask,
            add_adapter=False,
        ).to(hidden.device)
    feature_mask = feature_mask.to(dtype=hidden.dtype).unsqueeze(-1)
    denom = torch.clamp(feature_mask.sum(dim=1), min=1.0)
    return (hidden * feature_mask).sum(dim=1) / denom


def load_encoder(model_name: str, device_name: str, local_files_only: bool) -> tuple[Any, torch.nn.Module, torch.device]:
    device = torch.device(device_name if device_name != "auto" else ("cuda" if torch.cuda.is_available() else "cpu"))
    feature_extractor = AutoFeatureExtractor.from_pretrained(model_name, local_files_only=local_files_only)
    model = AutoModel.from_pretrained(model_name, local_files_only=local_files_only, use_safetensors=False)
    model.eval()
    for param in model.parameters():
        param.requires_grad_(False)
    model.to(device)
    return feature_extractor, model, device


def feature_columns(prefix: str, hidden_size: int) -> list[str]:
    if hidden_size <= 0:
        raise ValueError("encoder hidden size must be positive")
    return [f"{prefix}{idx:04d}" for idx in range(hidden_size)]


def save_feature_cache(path: Path, rows: list[dict[str, Any]]) -> None:
    frame = pd.DataFrame(rows)
    if not frame.empty:
        frame = frame.sort_values(
            "subject_id",
            key=lambda series: series.map(lambda item: tuple(natural_key(item))),
        ).reset_index(drop=True)
    frame.to_csv(path, index=False)


def embed_audio_with_min_chunk(
    path: Path,
    feature_extractor: Any,
    model: torch.nn.Module,
    device: torch.device,
    *,
    chunk_seconds: float,
    chunk_batch_size: int,
) -> tuple[np.ndarray, int, float, int]:
    target_sr = int(getattr(feature_extractor, "sampling_rate", 16000) or 16000)
    audio, sr = read_audio(path, target_sr)
    chunks, durations = chunk_audio(audio, sr, chunk_seconds)
    min_samples = max(1, int(round(target_sr * MIN_CHUNK_SECONDS)))
    padded_chunks: list[np.ndarray] = []
    padded_short_chunk_count = 0
    for chunk in chunks:
        if chunk.size < min_samples:
            padded_chunks.append(np.pad(chunk, (0, min_samples - chunk.size), mode="constant").astype(np.float32))
            padded_short_chunk_count += 1
        else:
            padded_chunks.append(chunk)

    embeddings: list[np.ndarray] = []
    weights: list[float] = []
    for start in range(0, len(padded_chunks), chunk_batch_size):
        batch = padded_chunks[start : start + chunk_batch_size]
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
        with torch.inference_mode():
            output = model(input_values=input_values, attention_mask=attention_mask)
            pooled = masked_mean_hidden(model, output.last_hidden_state, attention_mask)
        embeddings.extend(pooled.detach().cpu().numpy())
        weights.extend(batch_weights)

    stacked = np.vstack(embeddings).astype(np.float64)
    weights_arr = np.asarray(weights, dtype=np.float64)
    subject_embedding = np.average(stacked, axis=0, weights=weights_arr)
    return subject_embedding.astype(np.float32), len(chunks), float(np.sum(weights_arr)), padded_short_chunk_count


def extract_subject_embeddings(
    spec: EncoderSpec,
    subject_table: pd.DataFrame,
    out_dir: Path,
    *,
    device_name: str,
    local_files_only: bool,
    chunk_seconds: float,
    chunk_batch_size: int,
    force: bool,
) -> tuple[pd.DataFrame, list[str], dict[str, Any]]:
    cache_path = out_dir / f"{spec.encoder_id}_subject_features.csv"
    required_subjects = set(subject_table["subject_id"].astype(str))
    cached_rows: list[dict[str, Any]] = []
    cached_subjects: set[str] = set()
    embedding_columns: list[str] = []
    if cache_path.exists() and not force:
        cached = pd.read_csv(cache_path)
        cached["subject_id"] = cached["subject_id"].astype(str)
        cached_rows = cached[cached["subject_id"].isin(required_subjects)].to_dict("records")
        cached_subjects = {str(row["subject_id"]) for row in cached_rows}
        embedding_columns = [column for column in cached.columns if column.startswith(spec.feature_prefix)]
        if required_subjects.issubset(cached_subjects):
            print(f"Using cached E-DAIC {spec.model_label} subject embeddings", flush=True)
            selected = cached[cached["subject_id"].isin(required_subjects)].copy()
            return selected, embedding_columns, {
                "encoder_id": spec.encoder_id,
                "model_name": spec.model_name,
                "hidden_size": int(len(embedding_columns)),
                "cached_subject_rows": int(len(cached_rows)),
                "missing_subject_rows": 0,
                "cache_path": str(cache_path),
            }

    missing_rows = subject_table[~subject_table["subject_id"].isin(cached_subjects)].reset_index(drop=True)
    initial_cached_count = len(cached_rows)
    feature_extractor, model, device = load_encoder(spec.model_name, device_name, local_files_only)
    feature_extractor_class = type(feature_extractor).__name__
    model_class = type(model).__name__
    hidden_size = int(getattr(model.config, "hidden_size", 0) or 0)
    sampling_rate = int(getattr(feature_extractor, "sampling_rate", 16000) or 16000)
    if not embedding_columns:
        embedding_columns = feature_columns(spec.feature_prefix, hidden_size)
    print(
        f"Extracting E-DAIC {spec.model_label}: {len(missing_rows)} missing / {len(subject_table)} subjects on {device}",
        flush=True,
    )
    feature_rows = cached_rows
    for idx, row in missing_rows.iterrows():
        path = Path(str(row["audio_path"]))
        if not path.exists():
            raise FileNotFoundError(f"manifest audio path missing: {path}")
        if idx == 0 or (idx + 1) % 5 == 0 or (idx + 1) == len(missing_rows):
            print(f"  [{spec.encoder_id}] {idx + 1}/{len(missing_rows)} subject={row['subject_id']}", flush=True)
        embedding, chunk_count, duration_seconds, padded_short_chunk_count = embed_audio_with_min_chunk(
            path,
            feature_extractor,
            model,
            device,
            chunk_seconds=chunk_seconds,
            chunk_batch_size=chunk_batch_size,
        )
        feature_rows.append(
            {
                "subject_id": str(row["subject_id"]),
                "split": str(row["official_split"]),
                "duration_seconds": float(duration_seconds),
                "chunk_count": int(chunk_count),
                "padded_short_chunk_count": int(padded_short_chunk_count),
                **{column: float(value) for column, value in zip(embedding_columns, embedding, strict=True)},
            }
        )
        if (idx + 1) % 5 == 0:
            save_feature_cache(cache_path, feature_rows)
    save_feature_cache(cache_path, feature_rows)
    del model
    if torch.cuda.is_available():
        torch.cuda.empty_cache()

    features = pd.DataFrame(feature_rows)
    features["subject_id"] = features["subject_id"].astype(str)
    missing_subjects = sorted(required_subjects - set(features["subject_id"]), key=natural_key)
    if missing_subjects:
        raise ValueError(f"missing cached E-DAIC audio encoder rows for subjects: {missing_subjects[:10]}")
    selected = features[features["subject_id"].isin(required_subjects)].copy()
    selected = selected.sort_values(
        "subject_id",
        key=lambda series: series.map(lambda item: tuple(natural_key(item))),
    ).reset_index(drop=True)
    return selected, embedding_columns, {
        "encoder_id": spec.encoder_id,
        "model_name": spec.model_name,
        "feature_extractor": feature_extractor_class,
        "model_class": model_class,
        "hidden_size": hidden_size,
        "sampling_rate": sampling_rate,
        "device": str(device),
        "chunk_seconds": float(chunk_seconds),
        "chunk_batch_size": int(chunk_batch_size),
        "cached_subject_rows": int(initial_cached_count),
        "missing_subject_rows": int(len(missing_rows)),
        "cache_path": str(cache_path),
    }


def ridge_pipeline(alpha: float) -> Pipeline:
    return Pipeline(
        [
            ("imputer", SimpleImputer(strategy="median")),
            ("scaler", StandardScaler()),
            ("ridge", Ridge(alpha=alpha, solver="lsqr")),
        ]
    )


def mlp_pipeline(seed: int) -> Pipeline:
    return Pipeline(
        [
            ("imputer", SimpleImputer(strategy="median")),
            ("scaler", StandardScaler()),
            (
                "mlp",
                MLPRegressor(
                    hidden_layer_sizes=MLP_HIDDEN_LAYER_SIZES,
                    activation="relu",
                    solver="lbfgs",
                    alpha=MLP_ALPHA,
                    max_iter=MLP_MAX_ITER,
                    random_state=seed,
                ),
            ),
        ]
    )


def choose_ridge_alpha(train: pd.DataFrame, columns: list[str], seed: int) -> tuple[float, list[dict[str, Any]]]:
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
            model.fit(inner_train[columns], inner_train["phq8_total"].to_numpy(dtype=np.float64))
            pred = model.predict(inner_dev[columns])
            y_true_all.extend(inner_dev["phq8_total"].to_numpy(dtype=np.float64).tolist())
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


def clip_predictions(y_pred: np.ndarray, train: pd.DataFrame) -> tuple[np.ndarray, int, float, float]:
    low = float(train["phq8_total"].min())
    high = float(train["phq8_total"].max())
    clipped = np.clip(np.asarray(y_pred, dtype=np.float64), low, high)
    return clipped, int(np.sum(np.abs(clipped - y_pred) > 1.0e-12)), low, high


def build_labeled_feature_table(subject_table: pd.DataFrame, features: pd.DataFrame) -> pd.DataFrame:
    labels = subject_table[["subject_id", "official_split", "phq8_total"]].rename(columns={"official_split": "split"})
    merged = labels.merge(features, on=["subject_id", "split"], how="inner", validate="one_to_one")
    if len(merged) != len(labels):
        missing = sorted(set(labels["subject_id"]) - set(merged["subject_id"]), key=natural_key)
        raise ValueError(f"E-DAIC frozen audio missing feature rows after merge: {missing[:10]}")
    return merged


def run_head(
    head: HeadSpec,
    encoder: EncoderSpec,
    table: pd.DataFrame,
    columns: list[str],
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    train = table[table["split"] == "train"].reset_index(drop=True)
    dev = table[table["split"] == "dev"].reset_index(drop=True)
    predictions: list[dict[str, Any]] = []
    seed_summaries: list[dict[str, Any]] = []
    for seed in SEEDS:
        if head.head_type == "linear":
            alpha, alpha_candidates = choose_ridge_alpha(train, columns, seed)
            model = ridge_pipeline(alpha)
            model.fit(train[columns], train["phq8_total"].to_numpy(dtype=np.float64))
            raw_pred = model.predict(dev[columns])
            head_summary = {
                "ridge_alpha": float(alpha),
                "ridge_alpha_candidates": alpha_candidates,
            }
        elif head.head_type == "mlp":
            model = mlp_pipeline(seed)
            model.fit(train[columns], train["phq8_total"].to_numpy(dtype=np.float64))
            raw_pred = model.predict(dev[columns])
            head_summary = {
                "mlp_hidden_layer_sizes": list(MLP_HIDDEN_LAYER_SIZES),
                "mlp_alpha": float(MLP_ALPHA),
                "mlp_solver": "lbfgs",
                "mlp_max_iter": int(MLP_MAX_ITER),
            }
        else:
            raise ValueError(f"unknown head_type for {head.run_id}: {head.head_type}")
        y_pred, clip_count, low, high = clip_predictions(raw_pred, train)
        for idx, row in dev.iterrows():
            predictions.append(
                {
                    "run_id": head.run_id,
                    "dataset": "E-DAIC",
                    "modality": "Audio",
                    "task": "PHQ-8 regression",
                    "model": head.model_label,
                    "seed": int(seed),
                    "task_type": "severity_regression",
                    "subject_id": str(row["subject_id"]),
                    "split": str(row["split"]),
                    "duration_seconds": float(row["duration_seconds"]),
                    "chunk_count": int(row["chunk_count"]),
                    "y_true": float(row["phq8_total"]),
                    "y_pred": float(y_pred[idx]),
                    "y_score": "",
                    "prediction_clipped_to_train_target_range": True,
                }
            )
        seed_summaries.append(
            {
                "seed": int(seed),
                "train_subjects": int(len(train)),
                "dev_subjects": int(len(dev)),
                "target_min_train": float(low),
                "target_max_train": float(high),
                "dev_clip_count": int(clip_count),
                **head_summary,
            }
        )
    return predictions, {
        "run_id": head.run_id,
        "encoder_id": encoder.encoder_id,
        "model_name": encoder.model_name,
        "feature_count": int(len(columns)),
        "subject_count": int(table["subject_id"].nunique()),
        "train_subjects": int(len(train)),
        "dev_subjects": int(len(dev)),
        "prediction_rows": int(len(predictions)),
        "duration_hours_sum": float(table["duration_seconds"].sum() / 3600.0),
        "chunk_count_sum": int(table["chunk_count"].sum()),
        "chunk_count_min": int(table["chunk_count"].min()),
        "chunk_count_max": int(table["chunk_count"].max()),
        "seed_summaries": seed_summaries,
    }


def write_report(out_dir: Path, summary: dict[str, Any]) -> None:
    lines = [
        "# E-DAIC Frozen Audio Encoder Phase 2 Baselines",
        "",
        f"Generated: `{summary['generated_at']}`",
        "",
        "## Protocol",
        "",
        "- Input interface: manifest-resolved E-DAIC audio WAV paths.",
        "- Encoders: frozen WavLM and frozen wav2vec2; no encoder parameters are updated.",
        "- Subject embedding: audio is split into fixed-duration chunks, last hidden states are mean pooled, and chunk embeddings are duration-weighted averaged per subject.",
        "- Regression heads: Ridge linear head with train-only inner 5-fold alpha selection and fixed MLPRegressor with one hidden layer.",
        "- Fit heads on the official train split and evaluate on the official dev split.",
        "- Regression outputs are clipped to the train-split observed PHQ-8 range.",
        "- No dev or test labels are used for encoder extraction or hyperparameter selection.",
        "- No test split is used.",
        "- Raw audio, source paths, and file names are not written to prediction or feature outputs.",
        "",
        "## Audit",
        "",
        f"- Runs: `{summary['runs']}`",
        f"- Seeds: `{summary['seeds']}`",
        f"- Bootstrap resamples: `{summary['bootstrap_resamples']}`",
        f"- Prediction rows: `{summary['prediction_rows']}`",
        f"- Train subjects: `{summary['train_subjects']}`",
        f"- Dev subjects: `{summary['dev_subjects']}`",
        f"- Total train/dev audio hours: `{summary['duration_hours_sum']:.4f}`",
        f"- Raw audio written: `{summary['raw_audio_written']}`",
        f"- Source paths written: `{summary['source_paths_written']}`",
        "",
        "## Output Files",
        "",
        "- `edaic_audio_frozen_encoder_predictions.csv`",
        "- `wavlm_subject_features.csv`",
        "- `wav2vec2_subject_features.csv`",
        "- `phase2_metrics_by_seed.csv`",
        "- `phase2_metric_summary.csv`",
        "- `edaic_audio_frozen_encoders_run_summary.json`",
    ]
    (out_dir / "edaic_audio_frozen_encoders_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest-path", type=Path, default=MANIFEST_PATH)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--run-id", action="append", choices=[head.run_id for head in HEAD_SPECS])
    parser.add_argument("--device", default="auto")
    parser.add_argument("--local-files-only", action="store_true")
    parser.add_argument("--chunk-seconds", type=float, default=20.0)
    parser.add_argument("--chunk-batch-size", type=int, default=4)
    parser.add_argument("--bootstrap-resamples", type=int, default=1000)
    parser.add_argument("--force-embeddings", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    args.out_dir.mkdir(parents=True, exist_ok=True)
    selected_heads = [head for head in HEAD_SPECS if not args.run_id or head.run_id in set(args.run_id)]
    if not selected_heads:
        raise ValueError("no E-DAIC frozen audio runs selected")
    selected_encoder_ids = {head.encoder_id for head in selected_heads}
    selected_encoders = [spec for spec in ENCODER_SPECS if spec.encoder_id in selected_encoder_ids]
    subject_table = build_subject_table(args.manifest_path)
    train_subjects = set(subject_table.loc[subject_table["official_split"] == "train", "subject_id"])
    dev_subjects = set(subject_table.loc[subject_table["official_split"] == "dev", "subject_id"])

    all_predictions: list[dict[str, Any]] = []
    extractor_summaries: list[dict[str, Any]] = []
    run_summaries: list[dict[str, Any]] = []
    for encoder in selected_encoders:
        features, columns, extractor_summary = extract_subject_embeddings(
            encoder,
            subject_table,
            args.out_dir,
            device_name=args.device,
            local_files_only=args.local_files_only,
            chunk_seconds=args.chunk_seconds,
            chunk_batch_size=args.chunk_batch_size,
            force=args.force_embeddings,
        )
        extractor_summaries.append(extractor_summary)
        table = build_labeled_feature_table(subject_table, features)
        for head in [item for item in selected_heads if item.encoder_id == encoder.encoder_id]:
            predictions, run_summary = run_head(head, encoder, table, columns)
            all_predictions.extend(predictions)
            run_summaries.append(run_summary)

    predictions_frame = pd.DataFrame(all_predictions)
    predictions_path = args.out_dir / "edaic_audio_frozen_encoder_predictions.csv"
    predictions_frame.to_csv(predictions_path, index=False)
    metrics_by_seed, metric_summary = metric_records(
        predictions_frame,
        bootstrap_resamples=args.bootstrap_resamples,
        seed=20260727,
    )
    metrics_by_seed.to_csv(args.out_dir / "phase2_metrics_by_seed.csv", index=False)
    metric_summary.to_csv(args.out_dir / "phase2_metric_summary.csv", index=False)

    duration_hours_sum = float(
        sum(summary["duration_hours_sum"] for summary in run_summaries[:1])
        if run_summaries
        else 0.0
    )
    summary = {
        "generated_at": utc_now(),
        "manifest_path": str(args.manifest_path),
        "runs": [head.run_id for head in selected_heads],
        "extractor_summaries": extractor_summaries,
        "run_summaries": run_summaries,
        "seeds": SEEDS,
        "seed_count": len(SEEDS),
        "bootstrap_resamples": int(args.bootstrap_resamples),
        "train_subjects": int(len(train_subjects)),
        "dev_subjects": int(len(dev_subjects)),
        "test_subjects_used": 0,
        "prediction_rows": int(len(predictions_frame)),
        "duration_hours_sum": duration_hours_sum,
        "subject_overlap_violations": int(bool(train_subjects & dev_subjects)),
        "encoder_frozen": True,
        "no_test_split_used": True,
        "raw_audio_written": False,
        "source_paths_written": False,
    }
    (args.out_dir / "edaic_audio_frozen_encoders_run_summary.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=True, sort_keys=True),
        encoding="utf-8",
    )
    write_report(args.out_dir, summary)
    print(f"Wrote {predictions_path}")
    print(f"Wrote {args.out_dir / 'phase2_metric_summary.csv'}")


if __name__ == "__main__":
    main()
