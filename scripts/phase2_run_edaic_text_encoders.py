#!/usr/bin/env python3
"""Run Phase 2 E-DAIC frozen text-encoder baselines.

This runner evaluates the planned E-DAIC DeBERTa and ModernBERT text embedding
baselines without fine-tuning encoder weights. It uses manifest-resolved
transcripts, fits fixed MLP regression heads on the official train split, and
evaluates on the official dev split. Raw transcript text and source paths are
not written to prediction or feature outputs.
"""

from __future__ import annotations

import argparse
import json
import os
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
from sklearn.neural_network import MLPRegressor
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from transformers import AutoModel, AutoTokenizer

from phase2_metrics import metric_records


ROOT = Path("/root/autodl-tmp")
MANIFEST_PATH = ROOT / "datasets" / "manifests" / "edaic_subjects.csv"
DEFAULT_OUT_DIR = ROOT / "analysis" / "phase2_baselines" / "edaic_text_encoders"
SEEDS = [0, 1, 2, 3, 4]
MLP_HIDDEN_LAYER_SIZES = (64,)
MLP_ALPHA = 0.01
MLP_MAX_ITER = 2000


@dataclass(frozen=True)
class TextEncoderSpec:
    run_id: str
    model_name: str
    model_label: str
    feature_prefix: str


SPECS = [
    TextEncoderSpec(
        run_id="edaic_text_phq8_deberta_mlp",
        model_name="microsoft/deberta-v3-base",
        model_label="DeBERTa frozen embedding + MLP",
        feature_prefix="deberta_",
    ),
    TextEncoderSpec(
        run_id="edaic_text_phq8_modernbert_mlp",
        model_name="answerdotai/ModernBERT-base",
        model_label="ModernBERT frozen embedding + MLP",
        feature_prefix="modernbert_",
    ),
]


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def read_transcript(path_value: Any) -> tuple[str, dict[str, Any]]:
    path = Path(str(path_value))
    if not path.exists():
        raise FileNotFoundError(f"manifest transcript path missing: {path}")
    transcript = pd.read_csv(path)
    required = {"Start_Time", "End_Time", "Text"}
    missing = required - set(transcript.columns)
    if missing:
        raise ValueError(f"{path} missing transcript columns: {', '.join(sorted(missing))}")
    transcript = transcript.copy()
    transcript["Text"] = transcript["Text"].fillna("").astype(str)
    transcript = transcript.sort_values(["Start_Time", "End_Time"], kind="mergesort")
    texts = [value.strip() for value in transcript["Text"].tolist()]
    non_empty = [value for value in texts if value]
    return "\n".join(non_empty), {
        "transcript_turn_count": int(len(transcript)),
        "non_empty_turn_count": int(len(non_empty)),
        "empty_turn_count": int(len(texts) - len(non_empty)),
    }


def build_subject_table(manifest_path: Path) -> pd.DataFrame:
    manifest = pd.read_csv(manifest_path)
    required = {"subject_id", "official_split", "text_path", "phq8_total", "file_valid"}
    missing = required - set(manifest.columns)
    if missing:
        raise ValueError(f"E-DAIC manifest missing columns: {', '.join(sorted(missing))}")
    usable = manifest[
        (manifest["file_valid"].fillna(False).astype(bool))
        & manifest["official_split"].isin(["train", "dev"])
        & manifest["text_path"].notna()
        & manifest["phq8_total"].notna()
    ].copy()
    if usable.empty:
        raise ValueError("no usable E-DAIC train/dev rows")
    if usable["subject_id"].duplicated().any():
        dupes = sorted(usable.loc[usable["subject_id"].duplicated(), "subject_id"].astype(str).unique())
        raise ValueError(f"E-DAIC manifest should have one row per subject, duplicates observed: {dupes[:10]}")
    rows: list[dict[str, Any]] = []
    for _, row in usable.sort_values("subject_id").iterrows():
        text, stats = read_transcript(row["text_path"])
        rows.append(
            {
                "subject_id": str(row["subject_id"]),
                "split": str(row["official_split"]),
                "phq8_total": float(row["phq8_total"]),
                "text": text,
                **stats,
            }
        )
    table = pd.DataFrame(rows).sort_values("subject_id").reset_index(drop=True)
    train_subjects = set(table.loc[table["split"] == "train", "subject_id"])
    dev_subjects = set(table.loc[table["split"] == "dev", "subject_id"])
    overlap = sorted(train_subjects & dev_subjects)
    if overlap:
        raise ValueError(f"subject-level train/dev overlap detected: {overlap[:10]}")
    if table.loc[table["split"] == "train"].empty or table.loc[table["split"] == "dev"].empty:
        raise ValueError("E-DAIC text encoder requires non-empty official train and dev splits")
    empty_subjects = table.loc[~table["text"].astype(str).str.strip().astype(bool), "subject_id"].tolist()
    if empty_subjects:
        raise ValueError(f"E-DAIC subjects with empty transcript text: {empty_subjects[:10]}")
    return table


def load_encoder(model_name: str, device_name: str, local_files_only: bool) -> tuple[Any, torch.nn.Module, torch.device]:
    device = torch.device(device_name if device_name != "auto" else ("cuda" if torch.cuda.is_available() else "cpu"))
    tokenizer = AutoTokenizer.from_pretrained(model_name, local_files_only=local_files_only)
    model = AutoModel.from_pretrained(model_name, local_files_only=local_files_only)
    model.eval()
    for param in model.parameters():
        param.requires_grad_(False)
    model.to(device)
    return tokenizer, model, device


def chunk_token_ids(token_ids: list[int], max_content_tokens: int, fallback_token_id: int | None) -> list[list[int]]:
    if not token_ids:
        token_ids = [fallback_token_id if fallback_token_id is not None else 0]
    return [token_ids[start : start + max_content_tokens] for start in range(0, len(token_ids), max_content_tokens)]


def embed_text(
    text: str,
    tokenizer: Any,
    model: torch.nn.Module,
    device: torch.device,
    *,
    max_length: int,
    chunk_batch_size: int,
) -> tuple[np.ndarray, int, int]:
    max_content_tokens = max(1, int(max_length) - 2)
    token_ids = tokenizer.encode(text, add_special_tokens=False)
    token_count = int(len(token_ids))
    chunks = chunk_token_ids(token_ids, max_content_tokens, getattr(tokenizer, "unk_token_id", None))
    embeddings: list[np.ndarray] = []
    weights: list[float] = []
    for start in range(0, len(chunks), chunk_batch_size):
        batch_ids = chunks[start : start + chunk_batch_size]
        batch_texts = [
            tokenizer.decode(ids[:max_content_tokens], skip_special_tokens=True)
            or str(getattr(tokenizer, "unk_token", "[UNK]"))
            for ids in batch_ids
        ]
        batch = tokenizer(
            batch_texts,
            padding=True,
            truncation=True,
            max_length=max_length,
            return_tensors="pt",
        )
        batch = {key: value.to(device) for key, value in batch.items()}
        with torch.no_grad():
            output = model(**batch)
            pooled = output.last_hidden_state[:, 0, :]
            pooled = torch.nn.functional.normalize(pooled, p=2, dim=1)
        embeddings.extend(pooled.detach().cpu().numpy())
        weights.extend(float(max(1, len(ids))) for ids in batch_ids)
    stacked = np.vstack(embeddings).astype(np.float64)
    weights_arr = np.asarray(weights, dtype=np.float64)
    embedding = np.average(stacked, axis=0, weights=weights_arr)
    norm = float(np.linalg.norm(embedding))
    if norm > 0.0:
        embedding = embedding / norm
    return embedding.astype(np.float32), int(len(chunks)), token_count


def feature_columns(prefix: str, hidden_size: int) -> list[str]:
    if hidden_size <= 0:
        raise ValueError("encoder hidden size must be positive")
    return [f"{prefix}{idx:04d}" for idx in range(hidden_size)]


def save_feature_cache(path: Path, rows: list[dict[str, Any]]) -> None:
    frame = pd.DataFrame(rows)
    if not frame.empty:
        frame = frame.sort_values("subject_id").reset_index(drop=True)
    frame.to_csv(path, index=False)


def extract_subject_embeddings(
    spec: TextEncoderSpec,
    table: pd.DataFrame,
    out_dir: Path,
    *,
    device_name: str,
    local_files_only: bool,
    max_length: int,
    chunk_batch_size: int,
    force: bool,
) -> tuple[pd.DataFrame, list[str], dict[str, Any]]:
    cache_path = out_dir / f"{spec.feature_prefix.rstrip('_')}_subject_features.csv"
    required_subjects = set(table["subject_id"].astype(str))
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
            return cached[cached["subject_id"].isin(required_subjects)].copy(), embedding_columns, {
                "run_id": spec.run_id,
                "model_name": spec.model_name,
                "hidden_size": int(len(embedding_columns)),
                "cached_subject_rows": int(len(cached_rows)),
                "missing_subject_rows": 0,
                "cache_path": str(cache_path),
            }

    missing_rows = table[~table["subject_id"].astype(str).isin(cached_subjects)].reset_index(drop=True)
    initial_cached_count = len(cached_rows)
    tokenizer, model, device = load_encoder(spec.model_name, device_name, local_files_only)
    tokenizer_class = type(tokenizer).__name__
    model_class = type(model).__name__
    hidden_size = int(getattr(model.config, "hidden_size", 0) or 0)
    if not embedding_columns:
        embedding_columns = feature_columns(spec.feature_prefix, hidden_size)
    print(
        f"Extracting E-DAIC {spec.model_label}: {len(missing_rows)} missing / {len(table)} subjects on {device}",
        flush=True,
    )
    feature_rows = cached_rows
    for idx, row in missing_rows.iterrows():
        if idx == 0 or (idx + 1) % 25 == 0 or (idx + 1) == len(missing_rows):
            print(f"  [{spec.run_id}] {idx + 1}/{len(missing_rows)} subject={row['subject_id']}", flush=True)
        embedding, chunk_count, token_count = embed_text(
            str(row["text"]),
            tokenizer,
            model,
            device,
            max_length=max_length,
            chunk_batch_size=chunk_batch_size,
        )
        feature_rows.append(
            {
                "subject_id": str(row["subject_id"]),
                "split": str(row["split"]),
                "transcript_turn_count": int(row["transcript_turn_count"]),
                "non_empty_turn_count": int(row["non_empty_turn_count"]),
                "empty_turn_count": int(row["empty_turn_count"]),
                "token_count": int(token_count),
                "chunk_count": int(chunk_count),
                **{column: float(value) for column, value in zip(embedding_columns, embedding, strict=True)},
            }
        )
        if (idx + 1) % 25 == 0:
            save_feature_cache(cache_path, feature_rows)
    save_feature_cache(cache_path, feature_rows)
    del model
    if torch.cuda.is_available():
        torch.cuda.empty_cache()

    features = pd.DataFrame(feature_rows)
    features["subject_id"] = features["subject_id"].astype(str)
    missing_subjects = sorted(required_subjects - set(features["subject_id"]))
    if missing_subjects:
        raise ValueError(f"missing cached E-DAIC text encoder rows for subjects: {missing_subjects[:10]}")
    selected = features[features["subject_id"].isin(required_subjects)].sort_values("subject_id").reset_index(drop=True)
    return selected, embedding_columns, {
        "run_id": spec.run_id,
        "model_name": spec.model_name,
        "tokenizer": tokenizer_class,
        "model_class": model_class,
        "hidden_size": hidden_size,
        "device": str(device),
        "max_length": int(max_length),
        "chunk_batch_size": int(chunk_batch_size),
        "cached_subject_rows": int(initial_cached_count),
        "missing_subject_rows": int(len(missing_rows)),
        "cache_path": str(cache_path),
    }


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


def clip_predictions(y_pred: np.ndarray, train: pd.DataFrame) -> tuple[np.ndarray, int, float, float]:
    low = float(train["phq8_total"].min())
    high = float(train["phq8_total"].max())
    clipped = np.clip(np.asarray(y_pred, dtype=np.float64), low, high)
    return clipped, int(np.sum(np.abs(clipped - y_pred) > 1.0e-12)), low, high


def run_spec(
    spec: TextEncoderSpec,
    table: pd.DataFrame,
    features: pd.DataFrame,
    columns: list[str],
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    labels = table[["subject_id", "split", "phq8_total"]].copy()
    merged = labels.merge(features, on=["subject_id", "split"], how="inner", validate="one_to_one")
    if len(merged) != len(labels):
        missing = sorted(set(labels["subject_id"]) - set(merged["subject_id"]))
        raise ValueError(f"{spec.run_id} missing feature rows after merge: {missing[:10]}")
    train = merged[merged["split"] == "train"].reset_index(drop=True)
    dev = merged[merged["split"] == "dev"].reset_index(drop=True)
    predictions: list[dict[str, Any]] = []
    seed_summaries: list[dict[str, Any]] = []
    for seed in SEEDS:
        model = mlp_pipeline(seed)
        model.fit(train[columns], train["phq8_total"].to_numpy(dtype=np.float64))
        raw_pred = model.predict(dev[columns])
        y_pred, clip_count, low, high = clip_predictions(raw_pred, train)
        for idx, row in dev.iterrows():
            predictions.append(
                {
                    "run_id": spec.run_id,
                    "dataset": "E-DAIC",
                    "modality": "Text",
                    "task": "PHQ-8 regression",
                    "model": spec.model_label,
                    "seed": int(seed),
                    "task_type": "severity_regression",
                    "subject_id": str(row["subject_id"]),
                    "split": str(row["split"]),
                    "transcript_turn_count": int(row["transcript_turn_count"]),
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
                "mlp_hidden_layer_sizes": list(MLP_HIDDEN_LAYER_SIZES),
                "mlp_alpha": float(MLP_ALPHA),
                "mlp_solver": "lbfgs",
                "mlp_max_iter": int(MLP_MAX_ITER),
                "target_min_train": float(low),
                "target_max_train": float(high),
                "dev_clip_count": int(clip_count),
            }
        )
    return predictions, {
        "run_id": spec.run_id,
        "model_name": spec.model_name,
        "feature_count": int(len(columns)),
        "subject_count": int(merged["subject_id"].nunique()),
        "train_subjects": int(len(train)),
        "dev_subjects": int(len(dev)),
        "prediction_rows": int(len(predictions)),
        "token_count_sum": int(merged["token_count"].sum()),
        "chunk_count_sum": int(merged["chunk_count"].sum()),
        "chunk_count_min": int(merged["chunk_count"].min()),
        "chunk_count_max": int(merged["chunk_count"].max()),
        "seed_summaries": seed_summaries,
    }


def write_report(out_dir: Path, summary: dict[str, Any]) -> None:
    lines = [
        "# E-DAIC Frozen Text Encoder MLP Phase 2 Baselines",
        "",
        f"Generated: `{summary['generated_at']}`",
        "",
        "## Protocol",
        "",
        "- Input interface: manifest-resolved E-DAIC transcript CSV paths.",
        "- Encoders: frozen DeBERTa and ModernBERT; no encoder parameters are updated.",
        "- Transcript embedding: ASR `Text` rows are concatenated in timestamp order; long transcripts are split into max-length chunks and token-count-weighted averaged.",
        "- Regression head: fixed MLPRegressor with one hidden layer.",
        "- Fit on the official train split and evaluate on the official dev split.",
        "- Regression outputs are clipped to the train-split observed PHQ-8 range.",
        "- No dev or test labels are used for encoder extraction or hyperparameter selection.",
        "- No test split is used.",
        "- Raw transcript text and source paths are not written to prediction or feature outputs.",
        "",
        "## Audit",
        "",
        f"- Runs: `{summary['runs']}`",
        f"- Seeds: `{summary['seeds']}`",
        f"- Bootstrap resamples: `{summary['bootstrap_resamples']}`",
        f"- Prediction rows: `{summary['prediction_rows']}`",
        f"- Train subjects: `{summary['train_subjects']}`",
        f"- Dev subjects: `{summary['dev_subjects']}`",
        f"- Raw text written: `{summary['raw_text_written']}`",
        f"- Source paths written: `{summary['source_paths_written']}`",
        "",
        "## Output Files",
        "",
        "- `edaic_text_encoder_predictions.csv`",
        "- `deberta_subject_features.csv`",
        "- `modernbert_subject_features.csv`",
        "- `phase2_metrics_by_seed.csv`",
        "- `phase2_metric_summary.csv`",
        "- `edaic_text_encoders_run_summary.json`",
    ]
    (out_dir / "edaic_text_encoders_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest-path", type=Path, default=MANIFEST_PATH)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--run-id", action="append", choices=[spec.run_id for spec in SPECS])
    parser.add_argument("--device", default="auto")
    parser.add_argument("--local-files-only", action="store_true")
    parser.add_argument("--max-length", type=int, default=512)
    parser.add_argument("--chunk-batch-size", type=int, default=8)
    parser.add_argument("--bootstrap-resamples", type=int, default=1000)
    parser.add_argument("--force-embeddings", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    args.out_dir.mkdir(parents=True, exist_ok=True)
    selected_specs = [spec for spec in SPECS if not args.run_id or spec.run_id in set(args.run_id)]
    table = build_subject_table(args.manifest_path)
    all_predictions: list[dict[str, Any]] = []
    run_summaries: list[dict[str, Any]] = []
    extractor_summaries: list[dict[str, Any]] = []
    for spec in selected_specs:
        features, columns, extractor_summary = extract_subject_embeddings(
            spec,
            table,
            args.out_dir,
            device_name=args.device,
            local_files_only=args.local_files_only,
            max_length=args.max_length,
            chunk_batch_size=args.chunk_batch_size,
            force=args.force_embeddings,
        )
        extractor_summaries.append(extractor_summary)
        predictions, run_summary = run_spec(spec, table, features, columns)
        all_predictions.extend(predictions)
        run_summaries.append(run_summary)

    predictions_frame = pd.DataFrame(all_predictions)
    predictions_path = args.out_dir / "edaic_text_encoder_predictions.csv"
    predictions_frame.to_csv(predictions_path, index=False)
    metrics_by_seed, metric_summary = metric_records(
        predictions_frame,
        bootstrap_resamples=args.bootstrap_resamples,
        seed=20260727,
    )
    metrics_by_seed.to_csv(args.out_dir / "phase2_metrics_by_seed.csv", index=False)
    metric_summary.to_csv(args.out_dir / "phase2_metric_summary.csv", index=False)

    train_subjects = set(table.loc[table["split"] == "train", "subject_id"])
    dev_subjects = set(table.loc[table["split"] == "dev", "subject_id"])
    summary = {
        "generated_at": utc_now(),
        "manifest_path": str(args.manifest_path),
        "runs": [spec.run_id for spec in selected_specs],
        "seeds": SEEDS,
        "seed_count": len(SEEDS),
        "bootstrap_resamples": int(args.bootstrap_resamples),
        "train_subjects": int(len(train_subjects)),
        "dev_subjects": int(len(dev_subjects)),
        "test_subjects_used": 0,
        "prediction_rows": int(len(predictions_frame)),
        "extractor_summaries": extractor_summaries,
        "run_summaries": run_summaries,
        "subject_overlap_violations": int(bool(train_subjects & dev_subjects)),
        "no_test_split_used": True,
        "raw_text_written": False,
        "source_paths_written": False,
    }
    (args.out_dir / "edaic_text_encoders_run_summary.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=True, sort_keys=True),
        encoding="utf-8",
    )
    write_report(args.out_dir, summary)
    print(f"Wrote {predictions_path}")
    print(f"Wrote {args.out_dir / 'phase2_metric_summary.csv'}")


if __name__ == "__main__":
    main()
