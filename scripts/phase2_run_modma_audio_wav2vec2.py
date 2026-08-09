#!/usr/bin/env python3
"""Run the Phase 2 MODMA frozen wav2vec2 binary audio baseline."""

from __future__ import annotations

import argparse
import json
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
    MANIFEST_PATH,
    SPLIT_PATH,
    SEEDS,
    BaselineSpec,
    average_embeddings,
    build_segment_table,
    classifier_pipeline,
    embed_audio,
    load_protocols,
    load_split_frame,
    natural_key,
    prediction_meta,
    read_manifest,
    save_segment_cache,
)


DEFAULT_OUT_DIR = ROOT / "analysis" / "phase2_baselines" / "modma_audio_wav2vec2"
DEFAULT_MODEL_NAME = "facebook/wav2vec2-base"
FEATURE_PREFIX = "wav2vec2_"
SPEC = BaselineSpec(
    run_id="modma_audio_binary_wav2vec2_linear",
    task="binary depression classification",
    task_type="binary_classification",
    target="binary_label",
    model="wav2vec2 frozen embedding + linear",
    protocol_kind="subject_binary",
)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def load_encoder(model_name: str, device_name: str, local_files_only: bool) -> tuple[Any, torch.nn.Module, torch.device]:
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
    cache_path = out_dir / "modma_wav2vec2_segment_embeddings.csv"
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
        feature_extractor, model, device = load_encoder(model_name, device_name, local_files_only)
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
                raise ValueError("wav2vec2 model config does not expose a positive hidden_size")
            embedding_columns = [f"{FEATURE_PREFIX}{idx:04d}" for idx in range(hidden_size)]
        print(
            f"Extracting MODMA wav2vec2 embeddings: {len(missing_rows)} missing / {len(segment_table)} audio segments on {device}",
            flush=True,
        )
        for idx, row in missing_rows.iterrows():
            path = Path(str(row["audio_path"]))
            if not path.exists():
                raise FileNotFoundError(f"manifest audio path missing: {path}")
            if (idx + 1) == 1 or (idx + 1) % 25 == 0 or (idx + 1) == len(missing_rows):
                print(
                    f"  [modma-wav2vec2] {idx + 1}/{len(missing_rows)} subject={row['subject_id']} task={row['task_type']} segment={row['segment_id']}",
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
        raise RuntimeError("no wav2vec2 embeddings available")
    embeddings = pd.DataFrame(embedding_rows)
    observed_keys = set(zip(embeddings["subject_id"].astype(str), embeddings["segment_key"].astype(str), strict=True))
    missing_keys = required_keys - observed_keys
    if missing_keys:
        raise ValueError(f"missing cached wav2vec2 rows: {sorted(missing_keys)[:5]}")
    selected = embeddings[
        [
            key in required_keys
            for key in zip(embeddings["subject_id"].astype(str), embeddings["segment_key"].astype(str), strict=True)
        ]
    ].copy()
    return selected.sort_values(["subject_id", "task_type", "segment_key"]).reset_index(drop=True), embedding_columns, extractor_summary


def labels_by_subject(manifest_path: Path, subjects: set[str], target: str) -> pd.DataFrame:
    manifest = read_manifest(manifest_path)
    rows = manifest[manifest["subject_id"].astype(str).isin(subjects) & manifest[target].notna()].copy()
    labels: list[dict[str, Any]] = []
    for subject_id, group in rows.groupby("subject_id", sort=False):
        values = group[target].dropna().unique()
        if len(values) != 1:
            raise ValueError(f"{subject_id} has inconsistent {target}: {values[:5]}")
        labels.append({"subject_id": str(subject_id), target: int(values[0])})
    labels_frame = pd.DataFrame(labels)
    missing_subjects = sorted(subjects - set(labels_frame["subject_id"].astype(str)), key=natural_key)
    if missing_subjects:
        raise ValueError(f"subjects missing {target} labels: {missing_subjects[:10]}")
    return labels_frame


def merge_labels(features: pd.DataFrame, manifest_path: Path, target: str) -> tuple[pd.DataFrame, list[str]]:
    subjects = set(features["subject_id"].astype(str))
    labels = labels_by_subject(manifest_path, subjects, target)
    table = features.merge(labels, on="subject_id", how="inner")
    feature_columns = [column for column in table.columns if column.startswith(FEATURE_PREFIX)]
    if not feature_columns:
        raise ValueError("no wav2vec2 feature columns after label merge")
    return table, feature_columns


def run_subject_classification(
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
            model.fit(train[feature_columns], train[SPEC.target].astype(int))
            y_pred = model.predict(validation[feature_columns])
            y_score = model.predict_proba(validation[feature_columns])[:, 1]
            for idx, row in validation.iterrows():
                predictions.append(
                    {
                        **prediction_meta(SPEC, seed, fold, protocol["protocol_id"], row),
                        "y_true": int(row[SPEC.target]),
                        "y_pred": int(y_pred[idx]),
                        "y_score": float(y_score[idx]),
                    }
                )
            fold_summaries.append(
                {
                    "run_id": SPEC.run_id,
                    "protocol_id": protocol["protocol_id"],
                    "seed": int(seed),
                    "fold": fold,
                    "train_subjects": int(len(train)),
                    "validation_subjects": int(len(validation)),
                    "train_positive_subjects": int(train[SPEC.target].astype(int).sum()),
                    "validation_positive_subjects": int(validation[SPEC.target].astype(int).sum()),
                    "logistic_c": 1.0,
                }
            )
    return predictions, fold_summaries


def write_report(out_dir: Path, summary: dict[str, Any]) -> None:
    lines = [
        "# MODMA Frozen wav2vec2 Phase 2 Baseline",
        "",
        f"Generated: `{summary['generated_at']}`",
        "",
        "## Protocol",
        "",
        "- Input interface: manifest-resolved valid MODMA audio paths and generated subject-level split protocols.",
        "- Encoder: frozen wav2vec2; no encoder parameters are updated.",
        "- Segment embedding: audio is split into fixed-duration chunks, last hidden states are mean pooled, and chunk embeddings are duration-weighted averaged per segment.",
        "- Subject embedding: valid segment embeddings are averaged per subject.",
        "- Linear head: LogisticRegression with balanced class weights for binary classification.",
        "- No validation or test labels are used for encoder extraction or hyperparameter selection.",
        "- No test split is used.",
        "- Raw audio, source paths, and file names are not written to outputs.",
        "",
        "## Audit",
        "",
        f"- Run: `{summary['runs'][0]}`",
        f"- Subjects: `{summary['subject_count']}`",
        f"- Audio segments: `{summary['audio_segments']}`",
        f"- Invalid manifest audio rows excluded: `{summary['invalid_audio_rows_excluded']}`",
        f"- Segment embedding rows: `{summary['segment_embedding_rows']}`",
        f"- Subject feature rows: `{summary['subject_feature_rows']}`",
        f"- wav2vec2 feature count: `{summary['feature_count']}`",
        f"- Seeds: `{summary['seeds']}`",
        f"- Bootstrap resamples: `{summary['bootstrap_resamples']}`",
        f"- Prediction rows: `{summary['prediction_rows']}`",
        f"- Raw audio written: `{summary['raw_audio_written']}`",
        f"- Source paths written: `{summary['source_paths_written']}`",
        "",
        "## Output Files",
        "",
        "- `modma_audio_wav2vec2_predictions.csv`",
        "- `modma_wav2vec2_segment_embeddings.csv`",
        "- `modma_wav2vec2_subject_features.csv`",
        "- `phase2_metrics_by_seed.csv`",
        "- `phase2_metric_summary.csv`",
        "- `modma_audio_wav2vec2_run_summary.json`",
    ]
    (out_dir / "modma_audio_wav2vec2_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


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
    split_frame = load_split_frame(args.split_path)
    subject_protocol = load_protocols(split_frame, target="binary_label", protocol_id="modma_binary_subject_cv")[
        "modma_binary_subject_cv"
    ]
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
    subject_features.to_csv(args.out_dir / "modma_wav2vec2_subject_features.csv", index=False)

    subject_table, feature_columns = merge_labels(subject_features, args.manifest, SPEC.target)
    predictions, fold_summaries = run_subject_classification(subject_table, feature_columns, subject_protocol)
    predictions_frame = pd.DataFrame(predictions)
    predictions_path = args.out_dir / "modma_audio_wav2vec2_predictions.csv"
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
        "runs": [SPEC.run_id],
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
        "feature_count": int(len(embedding_columns)),
        "prediction_rows": int(len(predictions_frame)),
        "run_summaries": [
            {
                "run_id": SPEC.run_id,
                "protocol_kind": SPEC.protocol_kind,
                "protocol_count": 1,
                "prediction_rows": int(len(predictions_frame)),
                "fold_summary_count": int(len(fold_summaries)),
                "fold_summaries": fold_summaries,
            }
        ],
        "encoder_frozen": True,
        "no_test_split_used": True,
        "raw_audio_written": False,
        "source_paths_written": False,
    }
    (args.out_dir / "modma_audio_wav2vec2_run_summary.json").write_text(
        json.dumps(run_summary, indent=2, ensure_ascii=True, sort_keys=True),
        encoding="utf-8",
    )
    write_report(args.out_dir, run_summary)
    print(f"Wrote {predictions_path}")
    print(f"Wrote {args.out_dir / 'phase2_metric_summary.csv'}")


if __name__ == "__main__":
    main()
