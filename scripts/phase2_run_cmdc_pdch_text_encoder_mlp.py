#!/usr/bin/env python3
"""Run Phase 2 CMDC/PDCH frozen text-encoder MLP baselines.

The runner extracts frozen Chinese text-encoder embeddings from
manifest-resolved text segments, averages them to subject embeddings, and
evaluates fixed MLP regression heads under generated subject-level CV splits.
It writes no raw text, source paths, or file names.
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
import torch
from sklearn.impute import SimpleImputer
from sklearn.neural_network import MLPRegressor
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from transformers import AutoModel, AutoTokenizer

from phase2_metrics import metric_records


ROOT = Path("/root/autodl-tmp")
MANIFEST_DIR = ROOT / "datasets" / "manifests"
SPLIT_PATH = ROOT / "datasets" / "splits" / "phase2_subject_splits.csv"
DEFAULT_OUT_DIR = ROOT / "analysis" / "phase2_baselines" / "cmdc_pdch_text_encoder_mlp"
DEFAULT_MODEL_NAME = "BAAI/bge-small-zh-v1.5"
FEATURE_PREFIX = "bge_"
SEEDS = [0, 1, 2, 3, 4]
MLP_HIDDEN_LAYER_SIZES = (64,)
MLP_ALPHA = 0.01
MLP_MAX_ITER = 2000


@dataclass(frozen=True)
class BaselineSpec:
    run_id: str
    dataset_id: str
    display_dataset: str
    modality: str
    task: str
    task_type: str
    target: str
    model: str
    protocol_id: str


SPECS = [
    BaselineSpec(
        run_id="cmdc_text_phq9_encoder_mlp",
        dataset_id="cmdc",
        display_dataset="CMDC",
        modality="Text",
        task="PHQ-9 regression",
        task_type="severity_regression",
        target="phq9_total",
        model="frozen text encoder embedding + MLP",
        protocol_id="cmdc_phq9_subject_cv",
    ),
    BaselineSpec(
        run_id="pdch_text_hamd17_encoder_mlp",
        dataset_id="pdch",
        display_dataset="PDCH",
        modality="Text",
        task="HAMD-17 regression",
        task_type="severity_regression",
        target="hamd17_total",
        model="frozen text encoder embedding + MLP",
        protocol_id="pdch_hamd17_subject_cv_fallback",
    ),
]


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def natural_key(value: Any) -> list[Any]:
    return [int(part) if part.isdigit() else part for part in re.split(r"(\d+)", str(value))]


def read_text(path_value: Any) -> str:
    path = Path(str(path_value))
    if not path.exists():
        raise FileNotFoundError(f"manifest text path missing: {path}")
    data = path.read_bytes()
    for encoding in ["utf-8-sig", "utf-8", "gb18030"]:
        try:
            return data.decode(encoding).strip()
        except UnicodeDecodeError:
            continue
    return data.decode("utf-8", errors="ignore").strip()


def read_manifest(dataset_id: str) -> pd.DataFrame:
    path = MANIFEST_DIR / f"{dataset_id}_subjects.csv"
    if not path.exists():
        raise FileNotFoundError(f"manifest missing: {path}")
    return pd.read_csv(path)


def load_protocol_splits(split_path: Path, spec: BaselineSpec) -> dict[str, dict[str, list[str]]]:
    splits = pd.read_csv(split_path)
    required = {"dataset", "protocol_id", "target", "fold", "role", "subject_id"}
    missing = required - set(splits.columns)
    if missing:
        raise ValueError(f"split layer missing columns: {', '.join(sorted(missing))}")
    selected = splits[
        (splits["dataset"].astype(str) == spec.dataset_id)
        & (splits["protocol_id"].astype(str) == spec.protocol_id)
        & (splits["target"].astype(str) == spec.target)
    ].copy()
    if selected.empty:
        raise ValueError(f"no split rows for {spec.run_id} protocol {spec.protocol_id}")

    folds: dict[str, dict[str, list[str]]] = {}
    for fold, fold_rows in selected.groupby("fold", sort=False):
        roles: dict[str, list[str]] = {}
        for role, role_rows in fold_rows.groupby("role", sort=False):
            roles[str(role)] = sorted(role_rows["subject_id"].astype(str).unique(), key=natural_key)
        train_subjects = set(roles.get("train", []))
        validation_subjects = set(roles.get("validation", []))
        overlap = sorted(train_subjects & validation_subjects, key=natural_key)
        if overlap:
            raise ValueError(f"{spec.run_id}:{fold} train/validation subject overlap: {overlap[:10]}")
        if not train_subjects or not validation_subjects:
            raise ValueError(f"{spec.run_id}:{fold} requires non-empty train and validation roles")
        folds[str(fold)] = roles
    return dict(sorted(folds.items(), key=lambda item: natural_key(item[0])))


def build_segment_table(spec: BaselineSpec, split_subjects: set[str]) -> pd.DataFrame:
    manifest = read_manifest(spec.dataset_id)
    required = {"subject_id", "text_path", spec.target}
    missing = required - set(manifest.columns)
    if missing:
        raise ValueError(f"{spec.dataset_id} manifest missing columns: {', '.join(sorted(missing))}")
    rows = manifest[manifest["subject_id"].astype(str).isin(split_subjects)].copy()
    if "file_valid" in rows.columns:
        rows = rows[rows["file_valid"].fillna(False).astype(bool)].copy()
    rows = rows[rows["text_path"].notna() & rows[spec.target].notna()].copy()
    if rows.empty:
        raise ValueError(f"no usable text rows for {spec.run_id}")
    sort_columns = [column for column in ["subject_id", "session_id", "segment_id"] if column in rows.columns]
    rows = rows.sort_values(sort_columns).reset_index()
    rows["subject_id"] = rows["subject_id"].astype(str)
    rows["segment_key"] = rows.apply(
        lambda row: "::".join([str(row.get("session_id", "")), str(row.get("segment_id", "")), str(row["index"])]),
        axis=1,
    )
    observed = set(rows["subject_id"].astype(str))
    missing_subjects = sorted(split_subjects - observed, key=natural_key)
    if missing_subjects:
        raise ValueError(f"{spec.run_id} split subjects missing usable text rows: {missing_subjects[:10]}")
    return rows.reset_index(drop=True)


def load_encoder(model_name: str, device_name: str, local_files_only: bool) -> tuple[Any, torch.nn.Module, torch.device]:
    device = torch.device(device_name if device_name != "auto" else ("cuda" if torch.cuda.is_available() else "cpu"))
    tokenizer = AutoTokenizer.from_pretrained(model_name, local_files_only=local_files_only)
    model = AutoModel.from_pretrained(model_name, local_files_only=local_files_only)
    model.eval()
    for param in model.parameters():
        param.requires_grad_(False)
    model.to(device)
    return tokenizer, model, device


def chunk_token_ids(token_ids: list[int], max_content_tokens: int, unk_token_id: int | None) -> list[list[int]]:
    if not token_ids:
        token_ids = [unk_token_id if unk_token_id is not None else 0]
    return [token_ids[start : start + max_content_tokens] for start in range(0, len(token_ids), max_content_tokens)]


def embed_text(
    text: str,
    tokenizer: Any,
    model: torch.nn.Module,
    device: torch.device,
    *,
    max_length: int,
    chunk_batch_size: int,
) -> tuple[np.ndarray, int, int, bool]:
    max_content_tokens = max(1, int(max_length) - 2)
    token_ids = tokenizer.encode(text, add_special_tokens=False)
    token_count = int(len(token_ids))
    chunks = chunk_token_ids(token_ids, max_content_tokens, getattr(tokenizer, "unk_token_id", None))
    embeddings: list[np.ndarray] = []
    weights: list[float] = []
    for start in range(0, len(chunks), chunk_batch_size):
        batch_ids = chunks[start : start + chunk_batch_size]
        batch_texts = [
            tokenizer.decode(ids[:max_content_tokens], skip_special_tokens=True) or str(getattr(tokenizer, "unk_token", "[UNK]"))
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
    segment_embedding = np.average(stacked, axis=0, weights=weights_arr)
    norm = float(np.linalg.norm(segment_embedding))
    if norm > 0.0:
        segment_embedding = segment_embedding / norm
    return segment_embedding.astype(np.float32), len(chunks), token_count, not bool(text.strip())


def save_segment_cache(path: Path, rows: list[dict[str, Any]]) -> None:
    frame = pd.DataFrame(rows)
    if not frame.empty:
        frame = frame.sort_values(["subject_id", "segment_key"]).reset_index(drop=True)
    frame.to_csv(path, index=False)


def extract_segment_embeddings(
    spec: BaselineSpec,
    segment_table: pd.DataFrame,
    out_dir: Path,
    *,
    model_name: str,
    device_name: str,
    local_files_only: bool,
    max_length: int,
    chunk_batch_size: int,
    force: bool,
) -> tuple[pd.DataFrame, list[str], dict[str, Any]]:
    cache_path = out_dir / f"{spec.dataset_id}_bge_segment_embeddings.csv"
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
        "dataset_id": spec.dataset_id,
        "run_id": spec.run_id,
        "model_name": model_name,
        "max_length": int(max_length),
        "chunk_batch_size": int(chunk_batch_size),
        "cached_segment_rows": int(len(cached_rows)),
        "missing_segment_rows": int(len(missing_rows)),
    }

    if not missing_rows.empty:
        tokenizer, model, device = load_encoder(model_name, device_name, local_files_only)
        hidden_size = int(getattr(model.config, "hidden_size", 0) or 0)
        extractor_summary.update(
            {
                "tokenizer": type(tokenizer).__name__,
                "model_class": type(model).__name__,
                "hidden_size": hidden_size,
                "device": str(device),
            }
        )
        if not embedding_columns:
            if hidden_size <= 0:
                raise ValueError(f"{model_name} config does not expose a positive hidden_size")
            embedding_columns = [f"{FEATURE_PREFIX}{idx:04d}" for idx in range(hidden_size)]
        print(
            f"Extracting {spec.display_dataset} frozen text embeddings: "
            f"{len(missing_rows)} missing / {len(segment_table)} text segments on {device}",
            flush=True,
        )
        for idx, row in missing_rows.iterrows():
            if (idx + 1) == 1 or (idx + 1) % 50 == 0 or (idx + 1) == len(missing_rows):
                print(
                    f"  [{spec.dataset_id}-text-encoder] {idx + 1}/{len(missing_rows)} "
                    f"subject={row['subject_id']} segment={row['segment_id']}",
                    flush=True,
                )
            text = read_text(row["text_path"])
            embedding, chunk_count, token_count, empty_text = embed_text(
                text,
                tokenizer,
                model,
                device,
                max_length=max_length,
                chunk_batch_size=chunk_batch_size,
            )
            embedding_rows.append(
                {
                    "subject_id": str(row["subject_id"]),
                    "segment_key": str(row["segment_key"]),
                    "segment_id": str(row["segment_id"]),
                    "token_count": int(token_count),
                    "chunk_count": int(chunk_count),
                    "empty_text": bool(empty_text),
                    **{column: float(value) for column, value in zip(embedding_columns, embedding, strict=True)},
                }
            )
            if (idx + 1) % 50 == 0:
                save_segment_cache(cache_path, embedding_rows)
        save_segment_cache(cache_path, embedding_rows)
        del model
        if torch.cuda.is_available():
            torch.cuda.empty_cache()

    if not embedding_columns:
        raise RuntimeError(f"no text encoder embeddings available for {spec.run_id}")
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
        norm = float(np.linalg.norm(mean_values))
        if norm > 0.0:
            mean_values = mean_values / norm
        row: dict[str, Any] = {
            "subject_id": str(subject_id),
            "text_segment_count": int(len(group)),
            "token_count_sum": int(group["token_count"].sum()),
            "chunk_count_sum": int(group["chunk_count"].sum()),
            "empty_text_segments": int(group["empty_text"].astype(bool).sum()),
        }
        for column, value in zip(embedding_columns, mean_values, strict=True):
            row[column] = float(value) if np.isfinite(value) else np.nan
        rows.append(row)
    return pd.DataFrame(rows).sort_values(
        "subject_id", key=lambda series: series.map(lambda item: tuple(natural_key(item)))
    ).reset_index(drop=True)


def labels_by_subject(spec: BaselineSpec, subjects: set[str]) -> pd.DataFrame:
    manifest = read_manifest(spec.dataset_id)
    rows = manifest[manifest["subject_id"].astype(str).isin(subjects) & manifest[spec.target].notna()].copy()
    labels: list[dict[str, Any]] = []
    for subject_id, group in rows.groupby("subject_id", sort=False):
        values = group[spec.target].dropna().unique()
        if len(values) != 1:
            raise ValueError(f"{spec.run_id}:{subject_id} has inconsistent {spec.target}: {values[:5]}")
        labels.append({"subject_id": str(subject_id), spec.target: float(values[0])})
    labels_frame = pd.DataFrame(labels)
    missing_subjects = sorted(subjects - set(labels_frame["subject_id"].astype(str)), key=natural_key)
    if missing_subjects:
        raise ValueError(f"{spec.run_id} subjects missing labels: {missing_subjects[:10]}")
    return labels_frame


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


def target_bounds(train: pd.DataFrame, target: str) -> tuple[float, float]:
    return float(train[target].min()), float(train[target].max())


def clip_predictions(y_pred: np.ndarray, bounds: tuple[float, float]) -> tuple[np.ndarray, int]:
    arr = np.asarray(y_pred, dtype=np.float64)
    clipped = np.clip(arr, bounds[0], bounds[1])
    return clipped, int(np.sum(np.abs(clipped - arr) > 1.0e-12))


def prediction_meta(spec: BaselineSpec, seed: int, fold: str, row: pd.Series) -> dict[str, Any]:
    return {
        "run_id": spec.run_id,
        "dataset": spec.display_dataset,
        "modality": spec.modality,
        "task": spec.task,
        "model": spec.model,
        "seed": int(seed),
        "fold": fold,
        "protocol_id": spec.protocol_id,
        "task_type": spec.task_type,
        "subject_id": row["subject_id"],
        "split": "validation",
        "text_segment_count": int(row["text_segment_count"]),
        "empty_text_segments": int(row["empty_text_segments"]),
    }


def run_spec(
    spec: BaselineSpec,
    subject_features: pd.DataFrame,
    feature_columns: list[str],
    folds: dict[str, dict[str, list[str]]],
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    subjects = set(subject_features["subject_id"].astype(str))
    table = subject_features.merge(labels_by_subject(spec, subjects), on="subject_id", how="inner")
    table_by_subject = table.set_index("subject_id", drop=False)
    predictions: list[dict[str, Any]] = []
    fold_summaries: list[dict[str, Any]] = []
    for seed in SEEDS:
        for fold, roles in folds.items():
            train = table_by_subject.loc[roles["train"]].reset_index(drop=True)
            validation = table_by_subject.loc[roles["validation"]].reset_index(drop=True)
            bounds = target_bounds(train, spec.target)
            model = mlp_pipeline(seed)
            model.fit(train[feature_columns], train[spec.target].to_numpy(dtype=np.float64))
            y_pred_raw = model.predict(validation[feature_columns])
            y_pred, clip_count = clip_predictions(y_pred_raw, bounds)
            for idx, row in validation.iterrows():
                predictions.append(
                    {
                        **prediction_meta(spec, seed, fold, row),
                        "y_true": float(row[spec.target]),
                        "y_pred": float(y_pred[idx]),
                        "y_score": "",
                        "prediction_clipped_to_train_target_range": True,
                    }
                )
            fold_summaries.append(
                {
                    "run_id": spec.run_id,
                    "seed": int(seed),
                    "fold": fold,
                    "train_subjects": int(len(train)),
                    "validation_subjects": int(len(validation)),
                    "mlp_hidden_layer_sizes": list(MLP_HIDDEN_LAYER_SIZES),
                    "mlp_alpha": float(MLP_ALPHA),
                    "mlp_solver": "lbfgs",
                    "mlp_max_iter": int(MLP_MAX_ITER),
                    "target_min_train": float(bounds[0]),
                    "target_max_train": float(bounds[1]),
                    "validation_clip_count": int(clip_count),
                }
            )
    subject_overlap_violations = int(sum(bool(set(roles["train"]) & set(roles["validation"])) for roles in folds.values()))
    return predictions, {
        "run_id": spec.run_id,
        "dataset": spec.display_dataset,
        "target": spec.target,
        "protocol_id": spec.protocol_id,
        "subject_count": int(len(subjects)),
        "fold_count": int(len(folds)),
        "subject_overlap_violations": subject_overlap_violations,
        "feature_count": int(len(feature_columns)),
        "prediction_rows": int(len(predictions)),
        "fold_summaries": fold_summaries,
    }


def write_report(out_dir: Path, summary: dict[str, Any]) -> None:
    lines = [
        "# CMDC/PDCH Frozen Text Encoder MLP Phase 2 Baselines",
        "",
        f"Generated: `{summary['generated_at']}`",
        "",
        "## Protocol",
        "",
        "- Input interface: manifest-resolved text paths and generated subject-level split protocols.",
        "- Encoder: frozen Chinese BGE text encoder; no encoder parameters are updated.",
        "- Segment embedding: CLS embeddings are extracted for each text segment, with long segments split into 512-token windows and token-count-weighted averaged.",
        "- Subject embedding: valid segment embeddings are averaged per subject.",
        "- Regression head: fixed MLPRegressor with one hidden layer.",
        "- Regression outputs are clipped to the train-split observed target range.",
        "- No validation or test labels are used for encoder extraction or hyperparameter selection.",
        "- No test split is used.",
        "- Raw text, source paths, and file names are not written to outputs.",
        "",
        "## Audit",
        "",
        f"- Runs: `{summary['runs']}`",
        f"- Encoder: `{summary['model_name']}`",
        f"- Seeds: `{summary['seeds']}`",
        f"- Bootstrap resamples: `{summary['bootstrap_resamples']}`",
        f"- Prediction rows: `{summary['prediction_rows']}`",
        f"- Raw text written: `{summary['raw_text_written']}`",
        f"- Source paths written: `{summary['source_paths_written']}`",
        "",
        "## Output Files",
        "",
        "- `cmdc_pdch_text_encoder_mlp_predictions.csv`",
        "- `cmdc_bge_segment_embeddings.csv`",
        "- `cmdc_bge_subject_features.csv`",
        "- `pdch_bge_segment_embeddings.csv`",
        "- `pdch_bge_subject_features.csv`",
        "- `phase2_metrics_by_seed.csv`",
        "- `phase2_metric_summary.csv`",
        "- `cmdc_pdch_text_encoder_mlp_run_summary.json`",
    ]
    (out_dir / "cmdc_pdch_text_encoder_mlp_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--split-path", type=Path, default=SPLIT_PATH)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--model-name", default=DEFAULT_MODEL_NAME)
    parser.add_argument("--device", default="auto")
    parser.add_argument("--local-files-only", action="store_true")
    parser.add_argument("--max-length", type=int, default=512)
    parser.add_argument("--chunk-batch-size", type=int, default=16)
    parser.add_argument("--bootstrap-resamples", type=int, default=1000)
    parser.add_argument("--force-embeddings", action="store_true")
    parser.add_argument("--run-id", action="append", choices=[spec.run_id for spec in SPECS])
    args = parser.parse_args()

    args.out_dir.mkdir(parents=True, exist_ok=True)
    selected_specs = [spec for spec in SPECS if not args.run_id or spec.run_id in set(args.run_id)]
    all_predictions: list[dict[str, Any]] = []
    run_summaries: list[dict[str, Any]] = []
    extractor_summaries: list[dict[str, Any]] = []

    for spec in selected_specs:
        folds = load_protocol_splits(args.split_path, spec)
        split_subjects = {subject for roles in folds.values() for role_subjects in roles.values() for subject in role_subjects}
        segment_table = build_segment_table(spec, split_subjects)
        segment_embeddings, embedding_columns, extractor_summary = extract_segment_embeddings(
            spec,
            segment_table,
            args.out_dir,
            model_name=args.model_name,
            device_name=args.device,
            local_files_only=args.local_files_only,
            max_length=args.max_length,
            chunk_batch_size=args.chunk_batch_size,
            force=args.force_embeddings,
        )
        extractor_summaries.append(extractor_summary)
        subject_features = average_subject_embeddings(segment_embeddings, embedding_columns)
        subject_features.to_csv(args.out_dir / f"{spec.dataset_id}_bge_subject_features.csv", index=False)
        predictions, run_summary = run_spec(spec, subject_features, embedding_columns, folds)
        run_summary.update(
            {
                "text_segment_rows": int(len(segment_table)),
                "segment_embedding_rows": int(len(segment_embeddings)),
                "subject_feature_rows": int(len(subject_features)),
                "empty_text_segments": int(segment_embeddings["empty_text"].astype(bool).sum()),
                "token_count_sum": int(segment_embeddings["token_count"].sum()),
                "chunk_count_sum": int(segment_embeddings["chunk_count"].sum()),
            }
        )
        all_predictions.extend(predictions)
        run_summaries.append(run_summary)

    predictions_frame = pd.DataFrame(all_predictions)
    predictions_path = args.out_dir / "cmdc_pdch_text_encoder_mlp_predictions.csv"
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
        "manifest_dir": str(MANIFEST_DIR),
        "split_path": str(args.split_path),
        "runs": [spec.run_id for spec in selected_specs],
        "model_name": args.model_name,
        "extractor_summaries": extractor_summaries,
        "seeds": SEEDS,
        "seed_count": len(SEEDS),
        "bootstrap_resamples": int(args.bootstrap_resamples),
        "prediction_rows": int(len(predictions_frame)),
        "run_summaries": run_summaries,
        "encoder_frozen": True,
        "no_test_split_used": True,
        "raw_text_written": False,
        "source_paths_written": False,
    }
    (args.out_dir / "cmdc_pdch_text_encoder_mlp_run_summary.json").write_text(
        json.dumps(run_summary, indent=2, ensure_ascii=True, sort_keys=True),
        encoding="utf-8",
    )
    write_report(args.out_dir, run_summary)
    print(f"Wrote {predictions_path}")
    print(f"Wrote {args.out_dir / 'phase2_metric_summary.csv'}")


if __name__ == "__main__":
    main()
