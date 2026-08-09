#!/usr/bin/env python3
"""Run Phase 2 CMDC frozen audio-encoder baselines.

The runner extracts frozen WavLM and wav2vec2 segment embeddings from
manifest-resolved valid CMDC audio, averages segment embeddings to subject
embeddings, and evaluates simple linear binary heads. It writes no raw audio,
source paths, or file names.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import torch
from transformers import AutoFeatureExtractor, AutoModel

from phase2_metrics import metric_records
from phase2_run_modma_audio_wavlm import (
    ROOT,
    SPLIT_PATH,
    SEEDS,
    classifier_pipeline,
    chunk_audio,
    masked_mean_hidden,
    natural_key,
    read_audio,
    save_segment_cache,
)


MANIFEST_PATH = ROOT / "datasets" / "manifests" / "cmdc_subjects.csv"
DEFAULT_OUT_DIR = ROOT / "analysis" / "phase2_baselines" / "cmdc_audio_frozen_encoders"
MIN_CHUNK_SECONDS = 1.0


@dataclass(frozen=True)
class EncoderSpec:
    run_id: str
    model_name: str
    model_label: str
    feature_prefix: str


ENCODER_SPECS = [
    EncoderSpec(
        run_id="cmdc_audio_binary_wavlm_linear",
        model_name="microsoft/wavlm-base-plus",
        model_label="WavLM frozen embedding + linear",
        feature_prefix="wavlm_",
    ),
    EncoderSpec(
        run_id="cmdc_audio_binary_wav2vec2_linear",
        model_name="facebook/wav2vec2-base",
        model_label="wav2vec2 frozen embedding + linear",
        feature_prefix="wav2vec2_",
    ),
]


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


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
        (splits["dataset"].astype(str) == "cmdc")
        & (splits["protocol_id"].astype(str) == "cmdc_binary_subject_cv")
        & (splits["target"].astype(str) == "binary_label")
    ].copy()
    if selected.empty:
        raise ValueError("no split rows for cmdc_binary_subject_cv")

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
    required = {"subject_id", "audio_path", "binary_label", "file_valid"}
    missing = required - set(manifest.columns)
    if missing:
        raise ValueError(f"CMDC manifest missing columns: {', '.join(sorted(missing))}")
    rows = manifest[manifest["subject_id"].astype(str).isin(subjects)].copy()
    rows = rows[
        rows["file_valid"].fillna(False).astype(bool)
        & rows["audio_path"].notna()
        & rows["binary_label"].notna()
    ].copy()
    if rows.empty:
        raise ValueError("no usable CMDC audio rows")
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
        raise ValueError(f"split subjects missing valid CMDC audio rows: {missing_subjects[:10]}")
    return rows.reset_index(drop=True)


def load_encoder(model_name: str, device_name: str, local_files_only: bool) -> tuple[Any, torch.nn.Module, torch.device]:
    device = torch.device(device_name if device_name != "auto" else ("cuda" if torch.cuda.is_available() else "cpu"))
    feature_extractor = AutoFeatureExtractor.from_pretrained(model_name, local_files_only=local_files_only)
    model = AutoModel.from_pretrained(model_name, local_files_only=local_files_only, use_safetensors=False)
    model.eval()
    for param in model.parameters():
        param.requires_grad_(False)
    model.to(device)
    return feature_extractor, model, device


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
    padded_chunk_count = 0
    for chunk in chunks:
        if chunk.size < min_samples:
            padded = np.pad(chunk, (0, min_samples - chunk.size), mode="constant")
            padded_chunks.append(padded.astype(np.float32))
            padded_chunk_count += 1
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
    return segment_embedding.astype(np.float32), len(chunks), float(np.sum(weights_arr)), padded_chunk_count


def extract_segment_embeddings(
    spec: EncoderSpec,
    segment_table: pd.DataFrame,
    out_dir: Path,
    *,
    device_name: str,
    local_files_only: bool,
    chunk_seconds: float,
    chunk_batch_size: int,
    force: bool,
) -> tuple[pd.DataFrame, list[str], dict[str, Any]]:
    cache_path = out_dir / f"cmdc_{spec.feature_prefix.rstrip('_')}_segment_embeddings.csv"
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
        column for column in pd.DataFrame(embedding_rows).columns if column.startswith(spec.feature_prefix)
    ] if embedding_rows else []
    extractor_summary: dict[str, Any] = {
        "run_id": spec.run_id,
        "model_name": spec.model_name,
        "chunk_seconds": float(chunk_seconds),
        "chunk_batch_size": int(chunk_batch_size),
        "cached_segment_rows": int(len(cached_rows)),
        "missing_segment_rows": int(len(missing_rows)),
    }

    if not missing_rows.empty:
        feature_extractor, model, device = load_encoder(spec.model_name, device_name, local_files_only)
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
                raise ValueError(f"{spec.model_name} config does not expose a positive hidden_size")
            embedding_columns = [f"{spec.feature_prefix}{idx:04d}" for idx in range(hidden_size)]
        print(
            f"Extracting CMDC {spec.feature_prefix.rstrip('_')} embeddings: "
            f"{len(missing_rows)} missing / {len(segment_table)} audio segments on {device}",
            flush=True,
        )
        for idx, row in missing_rows.iterrows():
            path = Path(str(row["audio_path"]))
            if not path.exists():
                raise FileNotFoundError(f"manifest audio path missing: {path}")
            if (idx + 1) == 1 or (idx + 1) % 25 == 0 or (idx + 1) == len(missing_rows):
                print(
                    f"  [cmdc-{spec.feature_prefix.rstrip('_')}] {idx + 1}/{len(missing_rows)} "
                    f"subject={row['subject_id']} segment={row['segment_id']}",
                    flush=True,
                )
            embedding, chunk_count, duration_seconds, padded_chunk_count = embed_audio_with_min_chunk(
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
                    "task_type": str(row.get("task_type", "")),
                    "segment_key": str(row["segment_key"]),
                    "segment_id": str(row["segment_id"]),
                    "chunk_count": int(chunk_count),
                    "padded_short_chunk_count": int(padded_chunk_count),
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
        raise RuntimeError(f"no embeddings available for {spec.run_id}")
    embeddings = pd.DataFrame(embedding_rows)
    observed_keys = set(zip(embeddings["subject_id"].astype(str), embeddings["segment_key"].astype(str), strict=True))
    missing_keys = required_keys - observed_keys
    if missing_keys:
        raise ValueError(f"missing cached rows for {spec.run_id}: {sorted(missing_keys)[:5]}")
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
        }
        for column, value in zip(embedding_columns, mean_values, strict=True):
            row[column] = float(value) if np.isfinite(value) else np.nan
        rows.append(row)
    return pd.DataFrame(rows).sort_values(
        "subject_id", key=lambda series: series.map(lambda item: tuple(natural_key(item)))
    ).reset_index(drop=True)


def labels_by_subject(manifest_path: Path, subjects: set[str]) -> pd.DataFrame:
    manifest = read_manifest(manifest_path)
    rows = manifest[manifest["subject_id"].astype(str).isin(subjects) & manifest["binary_label"].notna()].copy()
    labels: list[dict[str, Any]] = []
    for subject_id, group in rows.groupby("subject_id", sort=False):
        values = group["binary_label"].dropna().unique()
        if len(values) != 1:
            raise ValueError(f"{subject_id} has inconsistent binary_label: {values[:5]}")
        labels.append({"subject_id": str(subject_id), "binary_label": int(values[0])})
    labels_frame = pd.DataFrame(labels)
    missing_subjects = sorted(subjects - set(labels_frame["subject_id"].astype(str)), key=natural_key)
    if missing_subjects:
        raise ValueError(f"subjects missing binary labels: {missing_subjects[:10]}")
    return labels_frame


def run_subject_classification(
    spec: EncoderSpec,
    subject_features: pd.DataFrame,
    feature_columns: list[str],
    folds: dict[str, dict[str, list[str]]],
    manifest_path: Path,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    subjects = set(subject_features["subject_id"].astype(str))
    table = subject_features.merge(labels_by_subject(manifest_path, subjects), on="subject_id", how="inner")
    table_by_subject = table.set_index("subject_id", drop=False)
    predictions: list[dict[str, Any]] = []
    fold_summaries: list[dict[str, Any]] = []
    for seed in SEEDS:
        for fold, roles in folds.items():
            train = table_by_subject.loc[roles["train"]].reset_index(drop=True)
            validation = table_by_subject.loc[roles["validation"]].reset_index(drop=True)
            model = classifier_pipeline(seed)
            model.fit(train[feature_columns], train["binary_label"].astype(int))
            y_pred = model.predict(validation[feature_columns])
            y_score = model.predict_proba(validation[feature_columns])[:, 1]
            for idx, row in validation.iterrows():
                predictions.append(
                    {
                        "run_id": spec.run_id,
                        "dataset": "CMDC",
                        "modality": "Audio",
                        "task": "MDD classification",
                        "model": spec.model_label,
                        "seed": int(seed),
                        "fold": fold,
                        "protocol_id": "cmdc_binary_subject_cv",
                        "task_type": "binary_classification",
                        "subject_id": row["subject_id"],
                        "split": "validation",
                        "audio_segment_count": int(row["audio_segment_count"]),
                        "y_true": int(row["binary_label"]),
                        "y_pred": int(y_pred[idx]),
                        "y_score": float(y_score[idx]),
                    }
                )
            fold_summaries.append(
                {
                    "run_id": spec.run_id,
                    "protocol_id": "cmdc_binary_subject_cv",
                    "seed": int(seed),
                    "fold": fold,
                    "train_subjects": int(len(train)),
                    "validation_subjects": int(len(validation)),
                    "train_positive_subjects": int(train["binary_label"].astype(int).sum()),
                    "validation_positive_subjects": int(validation["binary_label"].astype(int).sum()),
                    "logistic_c": 1.0,
                }
            )
    return predictions, fold_summaries


def write_report(out_dir: Path, summary: dict[str, Any]) -> None:
    lines = [
        "# CMDC Frozen Audio Encoder Phase 2 Baselines",
        "",
        f"Generated: `{summary['generated_at']}`",
        "",
        "## Protocol",
        "",
        "- Input interface: manifest-resolved valid CMDC audio paths and generated subject-level split protocol.",
        "- Encoders: frozen WavLM and frozen wav2vec2; no encoder parameters are updated.",
        "- Segment embedding: audio is split into fixed-duration chunks, last hidden states are mean pooled, and chunk embeddings are duration-weighted averaged per segment.",
        "- Subject embedding: valid segment embeddings are averaged per subject.",
        "- Linear head: LogisticRegression with balanced class weights.",
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
        f"- Seeds: `{summary['seeds']}`",
        f"- Bootstrap resamples: `{summary['bootstrap_resamples']}`",
        f"- Prediction rows: `{summary['prediction_rows']}`",
        f"- Raw audio written: `{summary['raw_audio_written']}`",
        f"- Source paths written: `{summary['source_paths_written']}`",
        "",
        "## Output Files",
        "",
        "- `cmdc_audio_frozen_encoder_predictions.csv`",
        "- `cmdc_wavlm_segment_embeddings.csv`",
        "- `cmdc_wavlm_subject_features.csv`",
        "- `cmdc_wav2vec2_segment_embeddings.csv`",
        "- `cmdc_wav2vec2_subject_features.csv`",
        "- `phase2_metrics_by_seed.csv`",
        "- `phase2_metric_summary.csv`",
        "- `cmdc_audio_frozen_encoders_run_summary.json`",
    ]
    (out_dir / "cmdc_audio_frozen_encoders_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, default=MANIFEST_PATH)
    parser.add_argument("--split-path", type=Path, default=SPLIT_PATH)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--device", default="auto")
    parser.add_argument("--local-files-only", action="store_true")
    parser.add_argument("--chunk-seconds", type=float, default=20.0)
    parser.add_argument("--chunk-batch-size", type=int, default=1)
    parser.add_argument("--bootstrap-resamples", type=int, default=1000)
    parser.add_argument("--force-embeddings", action="store_true")
    parser.add_argument("--run-id", action="append", choices=[spec.run_id for spec in ENCODER_SPECS])
    args = parser.parse_args()

    args.out_dir.mkdir(parents=True, exist_ok=True)
    folds = load_protocol_splits(args.split_path)
    split_subjects = {subject for roles in folds.values() for role_subjects in roles.values() for subject in role_subjects}
    segment_table = build_segment_table(args.manifest, split_subjects)
    selected_specs = [spec for spec in ENCODER_SPECS if not args.run_id or spec.run_id in set(args.run_id)]

    all_predictions: list[dict[str, Any]] = []
    run_summaries: list[dict[str, Any]] = []
    extractor_summaries: list[dict[str, Any]] = []
    for spec in selected_specs:
        segment_embeddings, embedding_columns, extractor_summary = extract_segment_embeddings(
            spec,
            segment_table,
            args.out_dir,
            device_name=args.device,
            local_files_only=args.local_files_only,
            chunk_seconds=args.chunk_seconds,
            chunk_batch_size=args.chunk_batch_size,
            force=args.force_embeddings,
        )
        extractor_summaries.append(extractor_summary)
        subject_features = average_subject_embeddings(segment_embeddings, embedding_columns)
        subject_features.to_csv(args.out_dir / f"cmdc_{spec.feature_prefix.rstrip('_')}_subject_features.csv", index=False)
        predictions, fold_summaries = run_subject_classification(
            spec,
            subject_features,
            embedding_columns,
            folds,
            args.manifest,
        )
        all_predictions.extend(predictions)
        run_summaries.append(
            {
                "run_id": spec.run_id,
                "model_name": spec.model_name,
                "feature_prefix": spec.feature_prefix,
                "feature_count": int(len(embedding_columns)),
                "segment_embedding_rows": int(len(segment_embeddings)),
                "subject_feature_rows": int(len(subject_features)),
                "protocol_id": "cmdc_binary_subject_cv",
                "prediction_rows": int(len(predictions)),
                "fold_summary_count": int(len(fold_summaries)),
                "fold_summaries": fold_summaries,
            }
        )

    predictions_frame = pd.DataFrame(all_predictions)
    predictions_path = args.out_dir / "cmdc_audio_frozen_encoder_predictions.csv"
    predictions_frame.to_csv(predictions_path, index=False)
    metrics_by_seed, metric_summary = metric_records(
        predictions_frame,
        bootstrap_resamples=args.bootstrap_resamples,
        seed=20260727,
    )
    metrics_by_seed.to_csv(args.out_dir / "phase2_metrics_by_seed.csv", index=False)
    metric_summary.to_csv(args.out_dir / "phase2_metric_summary.csv", index=False)

    manifest = read_manifest(args.manifest)
    split_subject_manifest = manifest[manifest["subject_id"].astype(str).isin(split_subjects)].copy()
    invalid_audio_rows = int(
        (~split_subject_manifest["file_valid"].fillna(False).astype(bool) & split_subject_manifest["audio_path"].notna()).sum()
    )
    run_summary = {
        "generated_at": utc_now(),
        "manifest": str(args.manifest),
        "split_path": str(args.split_path),
        "runs": [spec.run_id for spec in selected_specs],
        "extractor_summaries": extractor_summaries,
        "seeds": SEEDS,
        "seed_count": len(SEEDS),
        "bootstrap_resamples": int(args.bootstrap_resamples),
        "subject_count": int(len(split_subjects)),
        "audio_segments": int(len(segment_table)),
        "invalid_audio_rows_excluded": invalid_audio_rows,
        "prediction_rows": int(len(predictions_frame)),
        "run_summaries": run_summaries,
        "encoder_frozen": True,
        "no_test_split_used": True,
        "raw_audio_written": False,
        "source_paths_written": False,
    }
    (args.out_dir / "cmdc_audio_frozen_encoders_run_summary.json").write_text(
        json.dumps(run_summary, indent=2, ensure_ascii=True, sort_keys=True),
        encoding="utf-8",
    )
    write_report(args.out_dir, run_summary)
    print(f"Wrote {predictions_path}")
    print(f"Wrote {args.out_dir / 'phase2_metric_summary.csv'}")


if __name__ == "__main__":
    main()
