#!/usr/bin/env python3
"""Run the Phase 2 EATD frozen WavLM audio baseline.

The runner extracts frozen WavLM segment embeddings from manifest-resolved
positive/neutral/negative EATD audio, averages them to one subject embedding,
and evaluates a simple linear classifier on the official train/validation
subject split. It writes no raw audio, source paths, or file names.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from phase2_metrics import metric_records
from phase2_run_modma_audio_wavlm import (
    DEFAULT_MODEL_NAME,
    SEEDS,
    classifier_pipeline,
    embed_audio,
    load_wavlm,
    natural_key,
)


ROOT = Path("/root/autodl-tmp")
MANIFEST_PATH = ROOT / "datasets" / "manifests" / "eatd_subjects.csv"
DEFAULT_OUT_DIR = ROOT / "analysis" / "phase2_baselines" / "eatd_audio_wavlm"
RUN_ID = "eatd_audio_binary_wavlm_linear"
VALENCE_ORDER = ["positive", "neutral", "negative"]


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def read_manifest(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"manifest missing: {path}")
    return pd.read_csv(path)


def build_segment_table(manifest_path: Path) -> pd.DataFrame:
    manifest = read_manifest(manifest_path)
    required = {"subject_id", "valence", "audio_path", "binary_label", "official_split", "file_valid"}
    missing = required - set(manifest.columns)
    if missing:
        raise ValueError(f"EATD manifest missing columns: {', '.join(sorted(missing))}")
    rows = manifest[
        manifest["file_valid"].fillna(False).astype(bool)
        & manifest["audio_path"].notna()
        & manifest["binary_label"].notna()
        & manifest["official_split"].isin(["train", "validation"])
        & manifest["valence"].isin(VALENCE_ORDER)
    ].copy()
    if rows.empty:
        raise ValueError("no usable EATD audio rows")
    output_rows: list[dict[str, Any]] = []
    for subject_id, group in rows.groupby("subject_id", sort=True):
        by_valence = {str(row["valence"]): row for _, row in group.iterrows()}
        missing_valences = [valence for valence in VALENCE_ORDER if valence not in by_valence]
        if missing_valences:
            raise ValueError(f"{subject_id} missing audio valence rows: {missing_valences}")
        label_values = group["binary_label"].dropna().unique()
        split_values = group["official_split"].dropna().unique()
        if len(label_values) != 1 or len(split_values) != 1:
            raise ValueError(f"{subject_id} has inconsistent label/split values")
        for valence in VALENCE_ORDER:
            row = by_valence[valence]
            output_rows.append(
                {
                    "subject_id": str(subject_id),
                    "split": str(split_values[0]),
                    "valence": valence,
                    "segment_key": f"{valence}::{subject_id}",
                    "audio_path": str(row["audio_path"]),
                    "binary_label": int(label_values[0]),
                }
            )
    table = pd.DataFrame(output_rows).sort_values(["subject_id", "valence"]).reset_index(drop=True)
    train_subjects = set(table.loc[table["split"] == "train", "subject_id"].astype(str))
    validation_subjects = set(table.loc[table["split"] == "validation", "subject_id"].astype(str))
    overlap = sorted(train_subjects & validation_subjects, key=natural_key)
    if overlap:
        raise ValueError(f"subject-level split overlap detected: {overlap[:10]}")
    if not train_subjects or not validation_subjects:
        raise ValueError("EATD WavLM requires non-empty train and validation subjects")
    return table


def save_segment_cache(path: Path, rows: list[dict[str, Any]]) -> None:
    frame = pd.DataFrame(rows)
    if not frame.empty:
        frame = frame.sort_values(["subject_id", "valence"]).reset_index(drop=True)
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
    cache_path = out_dir / "eatd_wavlm_segment_embeddings.csv"
    required_keys = set(zip(segment_table["subject_id"], segment_table["valence"], strict=True))
    cached_rows: list[dict[str, Any]] = []
    cached_keys: set[tuple[str, str]] = set()
    if cache_path.exists() and not force:
        cached = pd.read_csv(cache_path)
        cached["subject_id"] = cached["subject_id"].astype(str)
        cached["valence"] = cached["valence"].astype(str)
        cached_keys = set(zip(cached["subject_id"], cached["valence"], strict=True))
        cached_rows = cached[
            [
                key in required_keys
                for key in zip(cached["subject_id"], cached["valence"], strict=True)
            ]
        ].to_dict("records")
    missing_rows = segment_table[
        [
            key not in cached_keys
            for key in zip(segment_table["subject_id"], segment_table["valence"], strict=True)
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
            f"Extracting EATD WavLM embeddings: {len(missing_rows)} missing / {len(segment_table)} audio segments on {device}",
            flush=True,
        )
        for idx, row in missing_rows.iterrows():
            path = Path(str(row["audio_path"]))
            if not path.exists():
                raise FileNotFoundError(f"manifest audio path missing: {path}")
            if (idx + 1) == 1 or (idx + 1) % 25 == 0 or (idx + 1) == len(missing_rows):
                print(
                    f"  [eatd-wavlm] {idx + 1}/{len(missing_rows)} subject={row['subject_id']} valence={row['valence']}",
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
                    "split": str(row["split"]),
                    "valence": str(row["valence"]),
                    "binary_label": int(row["binary_label"]),
                    "chunk_count": int(chunk_count),
                    "duration_seconds": float(duration_seconds),
                    **{column: float(value) for column, value in zip(embedding_columns, embedding, strict=True)},
                }
            )
            if (idx + 1) % 25 == 0:
                save_segment_cache(cache_path, embedding_rows)
        save_segment_cache(cache_path, embedding_rows)
    if not embedding_columns:
        raise RuntimeError("no WavLM embeddings available")
    embeddings = pd.DataFrame(embedding_rows)
    observed_keys = set(zip(embeddings["subject_id"].astype(str), embeddings["valence"].astype(str), strict=True))
    missing_keys = required_keys - observed_keys
    if missing_keys:
        raise ValueError(f"missing cached WavLM rows: {sorted(missing_keys)[:5]}")
    selected = embeddings[
        [
            key in required_keys
            for key in zip(embeddings["subject_id"].astype(str), embeddings["valence"].astype(str), strict=True)
        ]
    ].copy()
    return selected.sort_values(["subject_id", "valence"]).reset_index(drop=True), embedding_columns, extractor_summary


def aggregate_subject_features(segment_embeddings: pd.DataFrame, embedding_columns: list[str]) -> tuple[pd.DataFrame, list[str]]:
    rows: list[dict[str, Any]] = []
    for subject_id, group in segment_embeddings.groupby("subject_id", sort=True):
        missing_valences = [valence for valence in VALENCE_ORDER if valence not in set(group["valence"].astype(str))]
        if missing_valences:
            raise ValueError(f"{subject_id} missing cached valence embeddings: {missing_valences}")
        splits = group["split"].dropna().unique()
        labels = group["binary_label"].dropna().unique()
        if len(splits) != 1 or len(labels) != 1:
            raise ValueError(f"{subject_id} has inconsistent cached split/label")
        values = group[embedding_columns].to_numpy(dtype=np.float64)
        mean_values = np.nanmean(values, axis=0)
        row: dict[str, Any] = {
            "subject_id": str(subject_id),
            "split": str(splits[0]),
            "binary_label": int(labels[0]),
            "audio_segment_count": int(len(group)),
            "duration_seconds_sum": float(group["duration_seconds"].sum()),
            "chunk_count_sum": int(group["chunk_count"].sum()),
            "valences_observed": ";".join(sorted(group["valence"].astype(str).unique())),
        }
        for column, value in zip(embedding_columns, mean_values, strict=True):
            row[column] = float(value) if np.isfinite(value) else np.nan
        rows.append(row)
    subject_features = pd.DataFrame(rows).sort_values("subject_id").reset_index(drop=True)
    feature_columns = [column for column in subject_features.columns if column.startswith("wavlm_")]
    return subject_features, feature_columns


def prediction_meta(seed: int, row: pd.Series) -> dict[str, Any]:
    return {
        "run_id": RUN_ID,
        "dataset": "EATD-Corpus",
        "modality": "Audio",
        "task": "binary depression classification",
        "model": "WavLM frozen embedding + linear",
        "seed": int(seed),
        "task_type": "binary_classification",
        "subject_id": row["subject_id"],
        "split": "validation",
        "audio_segment_count": int(row["audio_segment_count"]),
    }


def run_baseline(subject_features: pd.DataFrame, feature_columns: list[str]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    train = subject_features[subject_features["split"] == "train"].reset_index(drop=True)
    validation = subject_features[subject_features["split"] == "validation"].reset_index(drop=True)
    train_subjects = set(train["subject_id"].astype(str))
    validation_subjects = set(validation["subject_id"].astype(str))
    overlap = sorted(train_subjects & validation_subjects, key=natural_key)
    if overlap:
        raise ValueError(f"subject-level split overlap detected: {overlap[:10]}")
    predictions: list[dict[str, Any]] = []
    seed_summaries: list[dict[str, Any]] = []
    for seed in SEEDS:
        model = classifier_pipeline(seed)
        model.fit(train[feature_columns], train["binary_label"].astype(int))
        y_pred = model.predict(validation[feature_columns])
        y_score = model.predict_proba(validation[feature_columns])[:, 1]
        for idx, row in validation.iterrows():
            predictions.append(
                {
                    **prediction_meta(seed, row),
                    "y_true": int(row["binary_label"]),
                    "y_pred": int(y_pred[idx]),
                    "y_score": float(y_score[idx]),
                }
            )
        seed_summaries.append(
            {
                "seed": int(seed),
                "train_subjects": int(len(train)),
                "validation_subjects": int(len(validation)),
                "train_positive_subjects": int(train["binary_label"].astype(int).sum()),
                "validation_positive_subjects": int(validation["binary_label"].astype(int).sum()),
            }
        )
    return predictions, seed_summaries


def write_report(out_dir: Path, summary: dict[str, Any]) -> None:
    lines = [
        "# EATD Frozen WavLM Audio Phase 2 Baseline",
        "",
        f"Generated: `{summary['generated_at']}`",
        "",
        "## Protocol",
        "",
        "- Input interface: manifest-resolved valid EATD audio paths.",
        "- Encoder: frozen WavLM; no WavLM parameters are updated.",
        "- Segment embedding: audio is split into fixed-duration chunks, WavLM last hidden states are mean pooled, and chunk embeddings are duration-weighted averaged per segment.",
        "- Subject embedding: positive, neutral, and negative segment embeddings are averaged per subject.",
        "- Linear head: fixed LogisticRegression with balanced class weights.",
        "- Evaluation split: official train/validation subject split.",
        "- No validation or test labels are used for hyperparameter selection.",
        "- No test split is used.",
        "- Raw audio, source paths, and file names are not written to outputs.",
        "",
        "## Audit",
        "",
        f"- Run: `{summary['runs']}`",
        f"- Train subjects: `{summary['train_subjects']}`",
        f"- Validation subjects: `{summary['validation_subjects']}`",
        f"- Subject overlap: `{summary['subject_overlap']}`",
        f"- Audio segments: `{summary['audio_segments']}`",
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
        "- `eatd_audio_wavlm_predictions.csv`",
        "- `eatd_wavlm_segment_embeddings.csv`",
        "- `eatd_wavlm_subject_features.csv`",
        "- `phase2_metrics_by_seed.csv`",
        "- `phase2_metric_summary.csv`",
        "- `eatd_audio_wavlm_run_summary.json`",
    ]
    (out_dir / "eatd_audio_wavlm_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, default=MANIFEST_PATH)
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
    segment_table = build_segment_table(args.manifest)
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
    subject_features, feature_columns = aggregate_subject_features(segment_embeddings, embedding_columns)
    subject_features.to_csv(args.out_dir / "eatd_wavlm_subject_features.csv", index=False)

    predictions, seed_summaries = run_baseline(subject_features, feature_columns)
    predictions_frame = pd.DataFrame(predictions)
    predictions_path = args.out_dir / "eatd_audio_wavlm_predictions.csv"
    predictions_frame.to_csv(predictions_path, index=False)

    metrics_by_seed, metric_summary = metric_records(
        predictions_frame,
        bootstrap_resamples=args.bootstrap_resamples,
        seed=20260727,
    )
    metrics_by_seed.to_csv(args.out_dir / "phase2_metrics_by_seed.csv", index=False)
    metric_summary.to_csv(args.out_dir / "phase2_metric_summary.csv", index=False)

    train_subjects = set(subject_features.loc[subject_features["split"] == "train", "subject_id"].astype(str))
    validation_subjects = set(subject_features.loc[subject_features["split"] == "validation", "subject_id"].astype(str))
    run_summary = {
        "generated_at": utc_now(),
        "manifest": str(args.manifest),
        "runs": [RUN_ID],
        "model_name": args.model_name,
        "extractor_summary": extractor_summary,
        "seeds": SEEDS,
        "seed_count": len(SEEDS),
        "bootstrap_resamples": int(args.bootstrap_resamples),
        "train_subjects": int(len(train_subjects)),
        "validation_subjects": int(len(validation_subjects)),
        "subject_overlap": int(len(train_subjects & validation_subjects)),
        "audio_segments": int(len(segment_table)),
        "segment_embedding_rows": int(len(segment_embeddings)),
        "subject_feature_rows": int(len(subject_features)),
        "feature_count": int(len(feature_columns)),
        "prediction_rows": int(len(predictions_frame)),
        "seed_summaries": seed_summaries,
        "encoder_frozen": True,
        "no_test_split_used": True,
        "raw_audio_written": False,
        "source_paths_written": False,
    }
    (args.out_dir / "eatd_audio_wavlm_run_summary.json").write_text(
        json.dumps(run_summary, indent=2, ensure_ascii=True, sort_keys=True),
        encoding="utf-8",
    )
    write_report(args.out_dir, run_summary)
    print(f"Wrote {predictions_path}")
    print(f"Wrote {args.out_dir / 'phase2_metric_summary.csv'}")


if __name__ == "__main__":
    main()
