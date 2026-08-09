#!/usr/bin/env python3
"""Run the Phase 2 PDCH frozen WavLM HAMD-17 regression baseline."""

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
import torch
from sklearn.impute import SimpleImputer
from sklearn.linear_model import Ridge
from sklearn.metrics import mean_absolute_error
from sklearn.model_selection import KFold
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from phase2_metrics import metric_records, regression_metrics
from phase2_run_modma_audio_wavlm import chunk_audio, load_wavlm, masked_mean_hidden, read_audio


ROOT = Path("/root/autodl-tmp")
MANIFEST_PATH = ROOT / "datasets" / "manifests" / "pdch_subjects.csv"
SPLIT_PATH = ROOT / "datasets" / "splits" / "phase2_subject_splits.csv"
DEFAULT_OUT_DIR = ROOT / "analysis" / "phase2_baselines" / "pdch_audio_wavlm"
DEFAULT_MODEL_NAME = "microsoft/wavlm-base-plus"
RUN_ID = "pdch_audio_hamd17_wavlm_linear"
SEEDS = [0, 1, 2, 3, 4]
RIDGE_ALPHA_GRID = [1.0, 10.0, 100.0, 1000.0]
FEATURE_PREFIX = "wavlm_"
MIN_CHUNK_SECONDS = 1.0


@dataclass(frozen=True)
class BaselineSpec:
    run_id: str = RUN_ID
    dataset_id: str = "pdch"
    display_dataset: str = "PDCH"
    modality: str = "Audio"
    task: str = "HAMD-17 regression"
    task_type: str = "severity_regression"
    target: str = "hamd17_total"
    model: str = "WavLM frozen embedding + linear"
    protocol_id: str = "pdch_hamd17_subject_cv_fallback"


SPEC = BaselineSpec()


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def natural_key(value: Any) -> list[Any]:
    return [int(part) if part.isdigit() else part for part in re.split(r"(\d+)", str(value))]


def read_manifest(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"manifest missing: {path}")
    return pd.read_csv(path)


def load_protocol_splits(split_path: Path) -> dict[str, dict[str, list[str]]]:
    splits = pd.read_csv(split_path)
    required = {"dataset", "protocol_id", "target", "fold", "role", "subject_id"}
    missing = required - set(splits.columns)
    if missing:
        raise ValueError(f"split layer missing columns: {', '.join(sorted(missing))}")
    selected = splits[
        (splits["dataset"].astype(str) == SPEC.dataset_id)
        & (splits["protocol_id"].astype(str) == SPEC.protocol_id)
        & (splits["target"].astype(str) == SPEC.target)
    ].copy()
    if selected.empty:
        raise ValueError(f"no split rows for {SPEC.run_id} protocol {SPEC.protocol_id}")

    folds: dict[str, dict[str, list[str]]] = {}
    for fold, fold_rows in selected.groupby("fold", sort=False):
        roles: dict[str, list[str]] = {}
        for role, role_rows in fold_rows.groupby("role", sort=False):
            roles[str(role)] = sorted(role_rows["subject_id"].astype(str).unique(), key=natural_key)
        train_subjects = set(roles.get("train", []))
        validation_subjects = set(roles.get("validation", []))
        overlap = sorted(train_subjects & validation_subjects, key=natural_key)
        if overlap:
            raise ValueError(f"{fold} train/validation subject overlap: {overlap[:10]}")
        if not train_subjects or not validation_subjects:
            raise ValueError(f"{fold} requires non-empty train and validation roles")
        folds[str(fold)] = roles
    return dict(sorted(folds.items(), key=lambda item: natural_key(item[0])))


def build_segment_table(manifest_path: Path, subjects: set[str]) -> pd.DataFrame:
    manifest = read_manifest(manifest_path)
    required = {"subject_id", "audio_path", SPEC.target, "file_valid"}
    missing = required - set(manifest.columns)
    if missing:
        raise ValueError(f"PDCH manifest missing columns: {', '.join(sorted(missing))}")
    rows = manifest[manifest["subject_id"].astype(str).isin(subjects)].copy()
    rows = rows[
        rows["file_valid"].fillna(False).astype(bool)
        & rows["audio_path"].notna()
        & rows[SPEC.target].notna()
    ].copy()
    if rows.empty:
        raise ValueError("no usable PDCH audio rows")
    sort_columns = [column for column in ["subject_id", "session_id", "segment_id"] if column in rows.columns]
    rows = rows.sort_values(sort_columns).reset_index()
    rows["subject_id"] = rows["subject_id"].astype(str)
    rows["segment_key"] = rows.apply(
        lambda row: "::".join([str(row.get("session_id", "")), str(row.get("segment_id", "")), str(row["index"])]),
        axis=1,
    )
    observed = set(rows["subject_id"].astype(str))
    missing_subjects = sorted(subjects - observed, key=natural_key)
    if missing_subjects:
        raise ValueError(f"split subjects missing valid PDCH audio rows: {missing_subjects[:10]}")
    return rows.reset_index(drop=True)


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
        with torch.no_grad():
            output = model(input_values=input_values, attention_mask=attention_mask)
            pooled = masked_mean_hidden(model, output.last_hidden_state, attention_mask)
        embeddings.extend(pooled.detach().cpu().numpy())
        weights.extend(batch_weights)

    stacked = np.vstack(embeddings).astype(np.float64)
    weights_arr = np.asarray(weights, dtype=np.float64)
    segment_embedding = np.average(stacked, axis=0, weights=weights_arr)
    return segment_embedding.astype(np.float32), len(chunks), float(np.sum(weights_arr)), padded_short_chunk_count


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
    force: bool,
) -> tuple[pd.DataFrame, list[str], dict[str, Any]]:
    cache_path = out_dir / "pdch_wavlm_segment_embeddings.csv"
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
        column for column in pd.DataFrame(embedding_rows).columns if column.startswith(FEATURE_PREFIX)
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
        hidden_size = int(getattr(model.config, "hidden_size", 0) or 0)
        extractor_summary.update(
            {
                "feature_extractor": type(feature_extractor).__name__,
                "model_class": type(model).__name__,
                "hidden_size": hidden_size,
                "sampling_rate": int(getattr(feature_extractor, "sampling_rate", 16000) or 16000),
                "device": str(device),
            }
        )
        if not embedding_columns:
            if hidden_size <= 0:
                raise ValueError("WavLM model config does not expose a positive hidden_size")
            embedding_columns = [f"{FEATURE_PREFIX}{idx:04d}" for idx in range(hidden_size)]
        print(
            f"Extracting PDCH WavLM embeddings: {len(missing_rows)} missing / {len(segment_table)} audio segments on {device}",
            flush=True,
        )
        for idx, row in missing_rows.iterrows():
            path = Path(str(row["audio_path"]))
            if not path.exists():
                raise FileNotFoundError(f"manifest audio path missing: {path}")
            if (idx + 1) == 1 or (idx + 1) % 10 == 0 or (idx + 1) == len(missing_rows):
                print(
                    f"  [pdch-wavlm] {idx + 1}/{len(missing_rows)} subject={row['subject_id']} segment={row['segment_id']}",
                    flush=True,
                )
            embedding, chunk_count, duration_seconds, padded_short_chunk_count = embed_audio_with_min_chunk(
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
                    "segment_key": str(row["segment_key"]),
                    "segment_id": str(row["segment_id"]),
                    "chunk_count": int(chunk_count),
                    "padded_short_chunk_count": int(padded_short_chunk_count),
                    "duration_seconds": float(duration_seconds),
                    **{column: float(value) for column, value in zip(embedding_columns, embedding, strict=True)},
                }
            )
            save_segment_cache(cache_path, embedding_rows)
        del model
        if torch.cuda.is_available():
            torch.cuda.empty_cache()

    if not embedding_columns:
        raise RuntimeError("no PDCH WavLM embeddings available")
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
    return selected.sort_values(["subject_id", "segment_key"]).reset_index(drop=True), embedding_columns, extractor_summary


def average_subject_embeddings(segment_embeddings: pd.DataFrame, embedding_columns: list[str]) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for subject_id, group in segment_embeddings.groupby("subject_id", sort=False):
        values = group[embedding_columns].to_numpy(dtype=np.float64)
        mean_values = np.nanmean(values, axis=0)
        row: dict[str, Any] = {
            "subject_id": str(subject_id),
            "audio_segment_count": int(len(group)),
            "duration_seconds_sum": float(group["duration_seconds"].sum()),
            "chunk_count_sum": int(group["chunk_count"].sum()),
            "padded_short_chunk_count_sum": int(group["padded_short_chunk_count"].fillna(0).sum()),
        }
        for column, value in zip(embedding_columns, mean_values, strict=True):
            row[column] = float(value) if np.isfinite(value) else np.nan
        rows.append(row)
    return pd.DataFrame(rows).sort_values(
        "subject_id", key=lambda series: series.map(lambda item: tuple(natural_key(item)))
    ).reset_index(drop=True)


def labels_by_subject(subjects: set[str]) -> pd.DataFrame:
    manifest = read_manifest(MANIFEST_PATH)
    rows = manifest[manifest["subject_id"].astype(str).isin(subjects) & manifest[SPEC.target].notna()].copy()
    labels: list[dict[str, Any]] = []
    for subject_id, group in rows.groupby("subject_id", sort=False):
        values = group[SPEC.target].dropna().unique()
        if len(values) != 1:
            raise ValueError(f"{subject_id} has inconsistent {SPEC.target}: {values[:5]}")
        labels.append({"subject_id": str(subject_id), SPEC.target: float(values[0])})
    labels_frame = pd.DataFrame(labels)
    missing_subjects = sorted(subjects - set(labels_frame["subject_id"].astype(str)), key=natural_key)
    if missing_subjects:
        raise ValueError(f"subjects missing {SPEC.target} labels: {missing_subjects[:10]}")
    return labels_frame


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
            model.fit(inner_train[feature_columns], inner_train[SPEC.target].to_numpy(dtype=np.float64))
            pred = model.predict(inner_dev[feature_columns])
            y_true_all.extend(inner_dev[SPEC.target].to_numpy(dtype=np.float64).tolist())
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


def target_bounds(train: pd.DataFrame) -> tuple[float, float]:
    return float(train[SPEC.target].min()), float(train[SPEC.target].max())


def clip_predictions(y_pred: np.ndarray, bounds: tuple[float, float]) -> tuple[np.ndarray, int]:
    arr = np.asarray(y_pred, dtype=np.float64)
    clipped = np.clip(arr, bounds[0], bounds[1])
    return clipped, int(np.sum(np.abs(clipped - arr) > 1.0e-12))


def prediction_meta(seed: int, fold: str, row: pd.Series) -> dict[str, Any]:
    return {
        "run_id": SPEC.run_id,
        "dataset": SPEC.display_dataset,
        "modality": SPEC.modality,
        "task": SPEC.task,
        "model": SPEC.model,
        "seed": int(seed),
        "fold": fold,
        "protocol_id": SPEC.protocol_id,
        "task_type": SPEC.task_type,
        "subject_id": row["subject_id"],
        "split": "validation",
        "audio_segment_count": int(row["audio_segment_count"]),
    }


def run_regression(
    subject_features: pd.DataFrame,
    feature_columns: list[str],
    folds: dict[str, dict[str, list[str]]],
) -> tuple[pd.DataFrame, list[dict[str, Any]]]:
    subjects = set(subject_features["subject_id"].astype(str))
    table = subject_features.merge(labels_by_subject(subjects), on="subject_id", how="inner")
    table_by_subject = table.set_index("subject_id", drop=False)
    predictions: list[dict[str, Any]] = []
    fold_summaries: list[dict[str, Any]] = []
    for seed in SEEDS:
        for fold, roles in folds.items():
            train = table_by_subject.loc[roles["train"]].reset_index(drop=True)
            validation = table_by_subject.loc[roles["validation"]].reset_index(drop=True)
            alpha, alpha_candidates = choose_ridge_alpha(train, feature_columns, seed)
            bounds = target_bounds(train)
            model = ridge_pipeline(alpha)
            model.fit(train[feature_columns], train[SPEC.target].to_numpy(dtype=np.float64))
            y_pred_raw = model.predict(validation[feature_columns])
            y_pred, clip_count = clip_predictions(y_pred_raw, bounds)
            for idx, row in validation.iterrows():
                predictions.append(
                    {
                        **prediction_meta(seed, fold, row),
                        "y_true": float(row[SPEC.target]),
                        "y_pred": float(y_pred[idx]),
                        "y_score": "",
                        "prediction_clipped_to_train_target_range": True,
                    }
                )
            fold_summaries.append(
                {
                    "run_id": SPEC.run_id,
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
    return pd.DataFrame(predictions), fold_summaries


def write_report(out_dir: Path, summary: dict[str, Any]) -> None:
    lines = [
        "# PDCH Frozen WavLM Phase 2 Baseline",
        "",
        f"Generated: `{summary['generated_at']}`",
        "",
        "## Protocol",
        "",
        "- Input interface: manifest-resolved valid PDCH audio paths and generated subject-level split protocol.",
        "- Encoder: frozen `microsoft/wavlm-base-plus`; no WavLM parameters are updated.",
        "- Segment embedding: audio is split into fixed-duration chunks, WavLM last hidden states are mean pooled, and chunk embeddings are duration-weighted averaged per segment.",
        "- Very short tail chunks are zero-padded to a 1-second minimum before encoder inference; duration weighting still uses original unpadded duration.",
        "- Subject embedding: valid segment embeddings are averaged per subject.",
        "- Linear head: Ridge regression with alpha selected only inside the train split by inner 5-fold OOF MAE.",
        "- Regression outputs are clipped to the train-split observed target range.",
        "- No validation or test labels are used for encoder extraction or hyperparameter selection.",
        "- No test split is used.",
        "- Raw audio, source paths, and file names are not written to outputs.",
        "",
        "## Audit",
        "",
        f"- Run: `{summary['runs'][0]}`",
        f"- Subjects: `{summary['subject_count']}`",
        f"- Audio segments: `{summary['audio_segments']}`",
        f"- Audio duration hours: `{summary['audio_duration_hours']:.4f}`",
        f"- Segment embedding rows: `{summary['segment_embedding_rows']}`",
        f"- Subject feature rows: `{summary['subject_feature_rows']}`",
        f"- WavLM feature count: `{summary['feature_count']}`",
        f"- Seeds: `{summary['seeds']}`",
        f"- Bootstrap resamples: `{summary['bootstrap_resamples']}`",
        f"- Prediction rows: `{summary['prediction_rows']}`",
        f"- Raw audio written: `{summary['raw_audio_written']}`",
        f"- Source paths written: `{summary['source_paths_written']}`",
        "",
        "## Output Files",
        "",
        "- `pdch_audio_wavlm_predictions.csv`",
        "- `pdch_wavlm_segment_embeddings.csv`",
        "- `pdch_wavlm_subject_features.csv`",
        "- `phase2_metrics_by_seed.csv`",
        "- `phase2_metric_summary.csv`",
        "- `pdch_audio_wavlm_run_summary.json`",
    ]
    (out_dir / "pdch_audio_wavlm_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


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
    args = parser.parse_args()

    args.out_dir.mkdir(parents=True, exist_ok=True)
    folds = load_protocol_splits(args.split_path)
    split_subjects = {subject for roles in folds.values() for role_subjects in roles.values() for subject in role_subjects}
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
    subject_features = average_subject_embeddings(segment_embeddings, embedding_columns)
    subject_features.to_csv(args.out_dir / "pdch_wavlm_subject_features.csv", index=False)

    predictions_frame, fold_summaries = run_regression(subject_features, embedding_columns, folds)
    predictions_path = args.out_dir / "pdch_audio_wavlm_predictions.csv"
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
        "manifest": str(args.manifest),
        "split_path": str(args.split_path),
        "runs": [SPEC.run_id],
        "model_name": args.model_name,
        "extractor_summary": extractor_summary,
        "seeds": SEEDS,
        "seed_count": len(SEEDS),
        "bootstrap_resamples": int(args.bootstrap_resamples),
        "subject_count": int(len(split_subjects)),
        "audio_segments": int(len(segment_table)),
        "audio_duration_hours": float(segment_embeddings["duration_seconds"].sum() / 3600.0),
        "segment_embedding_rows": int(len(segment_embeddings)),
        "subject_feature_rows": int(len(subject_features)),
        "feature_count": int(len(embedding_columns)),
        "chunk_count_sum": int(segment_embeddings["chunk_count"].sum()),
        "padded_short_chunk_count": int(segment_embeddings["padded_short_chunk_count"].fillna(0).sum()),
        "prediction_rows": int(len(predictions_frame)),
        "fold_summaries": fold_summaries,
        "encoder_frozen": True,
        "no_test_split_used": True,
        "raw_audio_written": False,
        "source_paths_written": False,
    }
    (args.out_dir / "pdch_audio_wavlm_run_summary.json").write_text(
        json.dumps(run_summary, indent=2, ensure_ascii=True, sort_keys=True),
        encoding="utf-8",
    )
    write_report(args.out_dir, run_summary)
    print(f"Wrote {predictions_path}")
    print(f"Wrote {args.out_dir / 'phase2_metric_summary.csv'}")


if __name__ == "__main__":
    main()
