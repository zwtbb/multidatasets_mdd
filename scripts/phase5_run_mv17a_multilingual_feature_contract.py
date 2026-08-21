#!/usr/bin/env python3
"""Run MV17a multilingual text-feature contract sensitivity.

MV17a replaces the legacy Chinese BGE feature cache with two multilingual
encoders, then reruns the paper-critical MV07 -> MV12 -> MV15 chain against
each encoder-specific feature root. The generated feature caches remain
local-only under ignored Phase 2 artifacts; tracked outputs are aggregate
contract, coverage, downstream status, and hygiene reports.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
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
import torch.nn.functional as F
from transformers import AutoModel, AutoTokenizer

import phase2_run_cmdc_pdch_text_encoder_mlp as cmdc_pdch
import phase5_generate_mv07_edaic_bge_features as edaic_gen


ROOT = Path(__file__).resolve().parents[1]
MANIFEST_DIR = ROOT / "datasets" / "manifests"
DEFAULT_EDAIC_MANIFEST = MANIFEST_DIR / "edaic_subjects.csv"
DEFAULT_SPLIT_PATH = ROOT / "datasets" / "splits" / "phase2_subject_splits.csv"
DEFAULT_FEATURE_ROOT = ROOT / "analysis" / "phase2_baselines" / "mv17_multilingual_text_features"
DEFAULT_OUT_DIR = ROOT / "analysis" / "phase5_minimal_validation" / "p5_mv17a_multilingual_feature_contract"
FEATURE_PREFIX = "bge_"

TRACKED_FILES = {
    "artifact_hygiene_audit.json",
    "downstream_run_summary.csv",
    "encoder_contract.csv",
    "feature_generation_summary.csv",
    "local_artifact_manifest.csv",
    "report.md",
    "run_summary.json",
}


@dataclass(frozen=True)
class EncoderSpec:
    slug: str
    model_name: str
    pooling: str
    input_prefix: str
    default_max_length: int
    default_chunk_batch_size: int
    expected_dimension: int
    source_url: str
    source_contract: str


ENCODER_SPECS = {
    "bge_m3": EncoderSpec(
        slug="bge_m3",
        model_name="BAAI/bge-m3",
        pooling="cls",
        input_prefix="",
        default_max_length=512,
        default_chunk_batch_size=8,
        expected_dimension=1024,
        source_url="https://huggingface.co/BAAI/bge-m3",
        source_contract="multilingual dense embedding model; official max sequence length is 8192, MV17a uses a 512-token chunk contract for parity with legacy MV07 and E5.",
    ),
    "multilingual_e5_base": EncoderSpec(
        slug="multilingual_e5_base",
        model_name="intfloat/multilingual-e5-base",
        pooling="average",
        input_prefix="query: ",
        default_max_length=512,
        default_chunk_batch_size=16,
        expected_dimension=768,
        source_url="https://huggingface.co/intfloat/multilingual-e5-base",
        source_contract="multilingual E5 feature encoder; official card specifies average pooling, normalized embeddings, and query prefix for feature use.",
    ),
}


DOWNSTREAM_RUNS = [
    (
        "mv07",
        ROOT / "scripts" / "phase5_run_mv07_aligned_bge_shared_symptom.py",
        "mv07_aligned_bge_shared_symptom",
    ),
    (
        "mv12",
        ROOT / "scripts" / "phase5_run_mv12_two_stage_latent_target.py",
        "mv12_two_stage_latent_target",
    ),
    (
        "mv15",
        ROOT / "scripts" / "phase5_run_mv15_latent_conditioned_identity.py",
        "mv15_latent_conditioned_identity",
    ),
]


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT))
    except ValueError:
        return path.name


def natural_key(value: Any) -> list[Any]:
    return cmdc_pdch.natural_key(value)


def natural_sort_key(series: pd.Series) -> pd.Series:
    return series.map(lambda value: tuple(natural_key(value)))


def feature_columns(hidden_size: int) -> list[str]:
    if hidden_size <= 0:
        raise ValueError("encoder hidden size must be positive")
    return [f"{FEATURE_PREFIX}{idx:04d}" for idx in range(hidden_size)]


def bool_series(series: pd.Series) -> pd.Series:
    if pd.api.types.is_bool_dtype(series):
        return series.fillna(False)
    return series.astype(str).str.strip().str.lower().isin({"true", "1", "yes", "y"})


def clean_tracked_outputs(out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    for name in TRACKED_FILES:
        path = out_dir / name
        if path.exists():
            path.unlink()


def load_encoder(
    encoder: EncoderSpec,
    *,
    device_name: str,
    allow_download: bool,
) -> tuple[Any, torch.nn.Module, torch.device, int]:
    device = torch.device(device_name if device_name != "auto" else ("cuda" if torch.cuda.is_available() else "cpu"))
    tokenizer = AutoTokenizer.from_pretrained(encoder.model_name, local_files_only=not allow_download)
    model = AutoModel.from_pretrained(
        encoder.model_name,
        local_files_only=not allow_download,
        use_safetensors=False,
    )
    model.eval()
    for param in model.parameters():
        param.requires_grad_(False)
    model.to(device)
    hidden_size = int(getattr(model.config, "hidden_size", 0) or 0)
    if hidden_size != encoder.expected_dimension:
        raise ValueError(
            f"{encoder.model_name} hidden_size={hidden_size}, expected {encoder.expected_dimension}"
        )
    return tokenizer, model, device, hidden_size


def chunk_token_ids(token_ids: list[int], max_content_tokens: int, fallback_token_id: int | None) -> list[list[int]]:
    if not token_ids:
        token_ids = [fallback_token_id if fallback_token_id is not None else 0]
    return [token_ids[start : start + max_content_tokens] for start in range(0, len(token_ids), max_content_tokens)]


def pooled_output(output: Any, attention_mask: torch.Tensor, pooling: str) -> torch.Tensor:
    if pooling == "cls":
        pooled = output.last_hidden_state[:, 0, :]
    elif pooling == "average":
        mask = attention_mask[..., None].bool()
        masked = output.last_hidden_state.masked_fill(~mask, 0.0)
        pooled = masked.sum(dim=1) / attention_mask.sum(dim=1)[..., None].clamp(min=1)
    else:
        raise ValueError(f"unsupported pooling policy: {pooling}")
    return F.normalize(pooled, p=2, dim=1)


def embed_text(
    text: str,
    encoder: EncoderSpec,
    tokenizer: Any,
    model: torch.nn.Module,
    device: torch.device,
    *,
    max_length: int,
    chunk_batch_size: int,
) -> tuple[np.ndarray, int, int, bool]:
    prefix_ids = (
        tokenizer.encode(encoder.input_prefix, add_special_tokens=False, verbose=False)
        if encoder.input_prefix
        else []
    )
    special_tokens = int(tokenizer.num_special_tokens_to_add(pair=False))
    max_content_tokens = max(1, int(max_length) - special_tokens - len(prefix_ids))
    token_ids = tokenizer.encode(text, add_special_tokens=False, verbose=False)
    token_count = int(len(token_ids))
    chunks = chunk_token_ids(token_ids, max_content_tokens, getattr(tokenizer, "unk_token_id", None))

    embeddings: list[np.ndarray] = []
    weights: list[float] = []
    for start in range(0, len(chunks), chunk_batch_size):
        batch_ids = chunks[start : start + chunk_batch_size]
        batch_texts = [
            f"{encoder.input_prefix}{tokenizer.decode(ids[:max_content_tokens], skip_special_tokens=True) or str(getattr(tokenizer, 'unk_token', '[UNK]'))}"
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
        with torch.inference_mode():
            output = model(**batch)
            pooled = pooled_output(output, batch["attention_mask"], encoder.pooling)
        embeddings.extend(pooled.detach().cpu().numpy())
        weights.extend(float(max(1, len(ids))) for ids in batch_ids)

    stacked = np.vstack(embeddings).astype(np.float64)
    weights_arr = np.asarray(weights, dtype=np.float64)
    embedding = np.average(stacked, axis=0, weights=weights_arr)
    norm = float(np.linalg.norm(embedding))
    if norm > 0.0:
        embedding = embedding / norm
    return embedding.astype(np.float32), int(len(chunks)), token_count, not bool(text.strip())


def read_complete_subject_cache(path: Path, required_subjects: set[str], expected_dimension: int) -> pd.DataFrame | None:
    if not path.exists():
        return None
    frame = pd.read_csv(path)
    if "subject_id" not in frame.columns:
        raise ValueError(f"feature cache missing subject key: {path}")
    frame["subject_id"] = frame["subject_id"].astype(str)
    feature_cols = [
        column
        for column in frame.columns
        if column.startswith(FEATURE_PREFIX) and pd.api.types.is_numeric_dtype(frame[column])
    ]
    if len(feature_cols) != expected_dimension:
        raise ValueError(f"{path} has {len(feature_cols)} feature columns, expected {expected_dimension}")
    observed = set(frame["subject_id"])
    if not required_subjects.issubset(observed):
        return None
    selected = frame[frame["subject_id"].isin(required_subjects)].copy()
    return selected.sort_values("subject_id", key=natural_sort_key).reset_index(drop=True)


def write_feature_cache(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    frame = pd.DataFrame(rows)
    if not frame.empty:
        frame = frame.sort_values("subject_id", key=natural_sort_key).reset_index(drop=True)
    frame.to_csv(path, index=False)


def summarize_feature_cache(
    encoder: EncoderSpec,
    dataset: str,
    cache_path: Path,
    features: pd.DataFrame,
    *,
    text_units: int,
    generation_status: str,
) -> dict[str, Any]:
    feature_cols = [column for column in features.columns if column.startswith(FEATURE_PREFIX)]
    token_sum = int(features["token_count_sum"].sum()) if "token_count_sum" in features.columns else 0
    chunk_sum = int(features["chunk_count_sum"].sum()) if "chunk_count_sum" in features.columns else 0
    empty_sum = int(features["empty_text_segments"].sum()) if "empty_text_segments" in features.columns else 0
    return {
        "encoder": encoder.slug,
        "dataset": dataset,
        "model_name": encoder.model_name,
        "pooling": encoder.pooling,
        "input_prefix_used": bool(encoder.input_prefix),
        "max_length": int(encoder.default_max_length),
        "feature_rows": int(features["subject_id"].nunique()),
        "feature_columns": int(len(feature_cols)),
        "text_units": int(text_units),
        "token_count_sum": token_sum,
        "chunk_count_sum": chunk_sum,
        "empty_text_units": empty_sum,
        "generation_status": generation_status,
        "cache_ref": rel(cache_path),
        "local_only": True,
    }


def extract_edaic_subject_features(
    table: pd.DataFrame,
    cache_path: Path,
    encoder: EncoderSpec,
    tokenizer: Any,
    model: torch.nn.Module,
    device: torch.device,
    *,
    force: bool,
) -> pd.DataFrame:
    required_subjects = set(table["subject_id"].astype(str))
    cached_rows: list[dict[str, Any]] = []
    cached_subjects: set[str] = set()
    if cache_path.exists() and not force:
        cached = pd.read_csv(cache_path)
        cached["subject_id"] = cached["subject_id"].astype(str)
        cached_rows = cached[cached["subject_id"].isin(required_subjects)].to_dict("records")
        cached_subjects = {str(row["subject_id"]) for row in cached_rows}

    missing = table[~table["subject_id"].astype(str).isin(cached_subjects)].reset_index(drop=True)
    rows = cached_rows
    columns = feature_columns(encoder.expected_dimension)
    print(
        f"Generating {encoder.slug} E-DAIC subject features: {len(missing)} missing / {len(table)} subjects",
        flush=True,
    )
    for idx, row in missing.iterrows():
        if idx == 0 or (idx + 1) % 25 == 0 or (idx + 1) == len(missing):
            print(f"  [{encoder.slug}:edaic] {idx + 1}/{len(missing)}", flush=True)
        embedding, chunk_count, token_count, empty_text = embed_text(
            str(row["text"]),
            encoder,
            tokenizer,
            model,
            device,
            max_length=encoder.default_max_length,
            chunk_batch_size=encoder.default_chunk_batch_size,
        )
        if empty_text:
            raise ValueError("E-DAIC transcript text should not be empty after manifest filtering")
        rows.append(
            {
                "subject_id": str(row["subject_id"]),
                "split": str(row["split"]),
                "text_segment_count": 1,
                "token_count_sum": int(token_count),
                "chunk_count_sum": int(chunk_count),
                "empty_text_segments": 0,
                "transcript_turn_count": int(row["transcript_turn_count"]),
                "non_empty_turn_count": int(row["non_empty_turn_count"]),
                "empty_turn_count": int(row["empty_turn_count"]),
                **{column: float(value) for column, value in zip(columns, embedding, strict=True)},
            }
        )
        if (idx + 1) % 25 == 0:
            write_feature_cache(cache_path, rows)

    write_feature_cache(cache_path, rows)
    features = pd.read_csv(cache_path)
    features["subject_id"] = features["subject_id"].astype(str)
    missing_subjects = sorted(required_subjects - set(features["subject_id"]), key=natural_key)
    if missing_subjects:
        raise ValueError(f"E-DAIC feature cache missing subjects: {missing_subjects[:10]}")
    return features[features["subject_id"].isin(required_subjects)].sort_values(
        "subject_id", key=natural_sort_key
    ).reset_index(drop=True)


def read_cached_segment_embeddings(
    path: Path,
    required_keys: set[tuple[str, str]],
    expected_dimension: int,
) -> tuple[list[dict[str, Any]], set[tuple[str, str]]]:
    if not path.exists():
        return [], set()
    cached = pd.read_csv(path)
    required_columns = {"subject_id", "segment_key"}
    missing = required_columns - set(cached.columns)
    if missing:
        raise ValueError(f"segment cache missing columns {sorted(missing)}: {path}")
    cached["subject_id"] = cached["subject_id"].astype(str)
    cached["segment_key"] = cached["segment_key"].astype(str)
    feature_cols = [
        column
        for column in cached.columns
        if column.startswith(FEATURE_PREFIX) and pd.api.types.is_numeric_dtype(cached[column])
    ]
    if len(feature_cols) != expected_dimension:
        raise ValueError(f"{path} has {len(feature_cols)} feature columns, expected {expected_dimension}")
    selected = cached[
        [
            key in required_keys
            for key in zip(cached["subject_id"], cached["segment_key"], strict=True)
        ]
    ].copy()
    keys = set(zip(selected["subject_id"], selected["segment_key"], strict=True))
    return selected.to_dict("records"), keys


def write_segment_cache(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    frame = pd.DataFrame(rows)
    if not frame.empty:
        frame = frame.sort_values(["subject_id", "segment_key"], key=natural_sort_key).reset_index(drop=True)
    frame.to_csv(path, index=False)


def average_subject_embeddings(segment_embeddings: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for subject, group in segment_embeddings.groupby("subject_id", sort=False):
        values = group[columns].to_numpy(dtype=np.float64)
        mean_values = np.nanmean(values, axis=0)
        norm = float(np.linalg.norm(mean_values))
        if norm > 0.0:
            mean_values = mean_values / norm
        row: dict[str, Any] = {
            "subject_id": str(subject),
            "text_segment_count": int(len(group)),
            "token_count_sum": int(group["token_count"].sum()),
            "chunk_count_sum": int(group["chunk_count"].sum()),
            "empty_text_segments": int(group["empty_text"].astype(bool).sum()),
        }
        for column, value in zip(columns, mean_values, strict=True):
            row[column] = float(value) if np.isfinite(value) else np.nan
        rows.append(row)
    return pd.DataFrame(rows).sort_values("subject_id", key=natural_sort_key).reset_index(drop=True)


def extract_segment_subject_features(
    dataset: str,
    table: pd.DataFrame,
    cache_dir: Path,
    encoder: EncoderSpec,
    tokenizer: Any,
    model: torch.nn.Module,
    device: torch.device,
    *,
    force: bool,
) -> pd.DataFrame:
    subject_cache = cache_dir / f"{dataset}_bge_subject_features.csv"
    required_subjects = set(table["subject_id"].astype(str))
    if not force:
        subject_cached = read_complete_subject_cache(subject_cache, required_subjects, encoder.expected_dimension)
        if subject_cached is not None:
            return subject_cached

    segment_cache = cache_dir / f"{dataset}_bge_segment_embeddings.csv"
    required_keys = set(zip(table["subject_id"].astype(str), table["segment_key"].astype(str), strict=True))
    cached_rows: list[dict[str, Any]] = []
    cached_keys: set[tuple[str, str]] = set()
    if not force:
        cached_rows, cached_keys = read_cached_segment_embeddings(
            segment_cache,
            required_keys,
            encoder.expected_dimension,
        )

    missing = table[
        [
            key not in cached_keys
            for key in zip(table["subject_id"].astype(str), table["segment_key"].astype(str), strict=True)
        ]
    ].reset_index(drop=True)
    rows = cached_rows
    columns = feature_columns(encoder.expected_dimension)
    print(
        f"Generating {encoder.slug} {dataset.upper()} segment features: {len(missing)} missing / {len(table)} segments",
        flush=True,
    )
    for idx, row in missing.iterrows():
        if idx == 0 or (idx + 1) % 50 == 0 or (idx + 1) == len(missing):
            print(f"  [{encoder.slug}:{dataset}] {idx + 1}/{len(missing)}", flush=True)
        text = cmdc_pdch.read_text(row["text_path"])
        embedding, chunk_count, token_count, empty_text = embed_text(
            text,
            encoder,
            tokenizer,
            model,
            device,
            max_length=encoder.default_max_length,
            chunk_batch_size=encoder.default_chunk_batch_size,
        )
        rows.append(
            {
                "subject_id": str(row["subject_id"]),
                "segment_key": str(row["segment_key"]),
                "segment_id": str(row["segment_id"]),
                "token_count": int(token_count),
                "chunk_count": int(chunk_count),
                "empty_text": bool(empty_text),
                **{column: float(value) for column, value in zip(columns, embedding, strict=True)},
            }
        )
        if (idx + 1) % 50 == 0:
            write_segment_cache(segment_cache, rows)

    write_segment_cache(segment_cache, rows)
    segment_embeddings = pd.read_csv(segment_cache)
    segment_embeddings["subject_id"] = segment_embeddings["subject_id"].astype(str)
    segment_embeddings["segment_key"] = segment_embeddings["segment_key"].astype(str)
    observed_keys = set(zip(segment_embeddings["subject_id"], segment_embeddings["segment_key"], strict=True))
    missing_keys = required_keys - observed_keys
    if missing_keys:
        raise ValueError(f"{dataset} segment cache missing rows: {sorted(missing_keys)[:5]}")
    selected = segment_embeddings[
        [
            key in required_keys
            for key in zip(segment_embeddings["subject_id"], segment_embeddings["segment_key"], strict=True)
        ]
    ].copy()
    subject_features = average_subject_embeddings(selected, columns)
    subject_features.to_csv(subject_cache, index=False)
    return subject_features


def build_cmdc_pdch_tables(split_path: Path) -> dict[str, pd.DataFrame]:
    tables: dict[str, pd.DataFrame] = {}
    for spec in cmdc_pdch.SPECS:
        folds = cmdc_pdch.load_protocol_splits(split_path, spec)
        split_subjects = {
            subject
            for roles in folds.values()
            for role_subjects in roles.values()
            for subject in role_subjects
        }
        tables[spec.dataset_id] = cmdc_pdch.build_segment_table(spec, split_subjects)
    return tables


def feature_paths(feature_root: Path, encoder: EncoderSpec) -> dict[str, Path]:
    root = feature_root / encoder.slug
    return {
        "edaic": root / "edaic_text_bge" / "edaic_bge_subject_features.csv",
        "cmdc": root / "cmdc_pdch_text_encoder_mlp" / "cmdc_bge_subject_features.csv",
        "pdch": root / "cmdc_pdch_text_encoder_mlp" / "pdch_bge_subject_features.csv",
    }


def feature_text_units(dataset: str, table: pd.DataFrame) -> int:
    if dataset == "edaic":
        return int(len(table))
    return int(len(table))


def generate_encoder_features(
    encoder: EncoderSpec,
    edaic_table: pd.DataFrame,
    segment_tables: dict[str, pd.DataFrame],
    *,
    feature_root: Path,
    device_name: str,
    allow_download: bool,
    force: bool,
) -> list[dict[str, Any]]:
    paths = feature_paths(feature_root, encoder)
    required = {
        "edaic": set(edaic_table["subject_id"].astype(str)),
        "cmdc": set(segment_tables["cmdc"]["subject_id"].astype(str)),
        "pdch": set(segment_tables["pdch"]["subject_id"].astype(str)),
    }
    cached = {
        dataset: None if force else read_complete_subject_cache(path, required[dataset], encoder.expected_dimension)
        for dataset, path in paths.items()
    }
    if all(frame is not None for frame in cached.values()):
        return [
            summarize_feature_cache(
                encoder,
                dataset,
                paths[dataset],
                cached[dataset],
                text_units=feature_text_units(dataset, edaic_table if dataset == "edaic" else segment_tables[dataset]),
                generation_status="cache_complete",
            )
            for dataset in ["edaic", "cmdc", "pdch"]
        ]

    tokenizer, model, device, _hidden_size = load_encoder(
        encoder,
        device_name=device_name,
        allow_download=allow_download,
    )
    summaries: list[dict[str, Any]] = []
    try:
        edaic_features = cached["edaic"] if cached["edaic"] is not None else extract_edaic_subject_features(
            edaic_table,
            paths["edaic"],
            encoder,
            tokenizer,
            model,
            device,
            force=force,
        )
        summaries.append(
            summarize_feature_cache(
                encoder,
                "edaic",
                paths["edaic"],
                edaic_features,
                text_units=feature_text_units("edaic", edaic_table),
                generation_status="generated" if cached["edaic"] is None else "cache_complete",
            )
        )
        for dataset in ["cmdc", "pdch"]:
            feature_cache = paths[dataset]
            features = cached[dataset]
            if features is None:
                features = extract_segment_subject_features(
                    dataset,
                    segment_tables[dataset],
                    feature_cache.parent,
                    encoder,
                    tokenizer,
                    model,
                    device,
                    force=force,
                )
                status = "generated"
            else:
                status = "cache_complete"
            summaries.append(
                summarize_feature_cache(
                    encoder,
                    dataset,
                    feature_cache,
                    features,
                    text_units=feature_text_units(dataset, segment_tables[dataset]),
                    generation_status=status,
                )
            )
    finally:
        del model
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
    return summaries


def write_encoder_contract(out_dir: Path, encoders: list[EncoderSpec]) -> None:
    rows = [
        {
            "encoder": encoder.slug,
            "model_name": encoder.model_name,
            "pooling": encoder.pooling,
            "input_prefix": encoder.input_prefix,
            "max_length": int(encoder.default_max_length),
            "chunk_batch_size": int(encoder.default_chunk_batch_size),
            "expected_dimension": int(encoder.expected_dimension),
            "feature_column_prefix": FEATURE_PREFIX,
            "source_url": encoder.source_url,
            "source_contract": encoder.source_contract,
            "downstream_feature_column_contract": "legacy bge_ columns retained for MV07/MV12/MV15 interface compatibility",
        }
        for encoder in encoders
    ]
    pd.DataFrame(rows).to_csv(out_dir / "encoder_contract.csv", index=False)


def write_local_artifact_manifest(out_dir: Path, feature_summaries: list[dict[str, Any]]) -> None:
    rows = [
        {
            "artifact": row["cache_ref"],
            "artifact_class": "local_only_subject_feature_cache",
            "encoder": row["encoder"],
            "dataset": row["dataset"],
            "exists": True,
            "rows": int(row["feature_rows"]),
            "columns": int(row["feature_columns"]),
            "version_policy": "ignored_by_git_do_not_commit",
        }
        for row in feature_summaries
    ]
    pd.DataFrame(rows).to_csv(out_dir / "local_artifact_manifest.csv", index=False)


def run_downstream_chain(
    encoders: list[EncoderSpec],
    *,
    feature_root: Path,
    out_dir: Path,
    manifest_dir: Path,
    split_path: Path,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for encoder in encoders:
        encoder_feature_root = feature_root / encoder.slug
        for run_id, script_path, dirname in DOWNSTREAM_RUNS:
            run_out = out_dir / "downstream" / encoder.slug / dirname
            cmd = [
                sys.executable,
                str(script_path),
                "--phase2-root",
                str(encoder_feature_root),
                "--out-dir",
                str(run_out),
                "--manifest-dir",
                str(manifest_dir),
                "--split-path",
                str(split_path),
            ]
            print(f"Running {run_id} with {encoder.slug}", flush=True)
            subprocess.run(cmd, cwd=ROOT, check=True)
            summary_path = run_out / "run_summary.json"
            if not summary_path.exists():
                raise FileNotFoundError(f"downstream summary missing: {summary_path}")
            summary = json.loads(summary_path.read_text(encoding="utf-8"))
            verdict = summary.get("verdict", {})
            rows.append(
                {
                    "encoder": encoder.slug,
                    "experiment": run_id,
                    "status": "complete",
                    "out_dir": rel(run_out),
                    "pass_rule_status": str(verdict.get("pass_rule_status", "")),
                    "artifact_hygiene_passed": bool(summary.get("artifact_hygiene_passed", False)),
                    "short_read": str(verdict.get("short_read", "")),
                }
            )
    return rows


def artifact_hygiene(out_dir: Path) -> dict[str, Any]:
    forbidden_patterns = [
        r"/root/",
        r"/autodl-tmp/",
        r"\bsubject_id\b",
        r"\btext_path\b",
        r"\baudio_path\b",
        r"\bvideo_path\b",
        r"\bgait_path\b",
        r"\.wav\b",
        r"\.mp4\b",
        r"\.avi\b",
        r"raw clinical",
        r"raw transcript",
        r"source path",
    ]
    violations: list[dict[str, str]] = []
    checked = 0
    for path in sorted(out_dir.glob("*")):
        if not path.is_file() or path.name not in TRACKED_FILES:
            continue
        checked += 1
        text = path.read_text(encoding="utf-8", errors="ignore")
        for pattern in forbidden_patterns:
            if re.search(pattern, text, flags=re.IGNORECASE):
                violations.append({"file": path.name, "pattern": pattern})
    return {
        "audit_id": "P5_MV17a_multilingual_feature_contract_hygiene",
        "generated_at": utc_now(),
        "files_checked": int(checked),
        "artifact_hygiene_passed": not violations,
        "violation_count": int(len(violations)),
        "violations": violations,
    }


def write_report(
    out_dir: Path,
    run_summary: dict[str, Any],
    feature_summary: pd.DataFrame,
    downstream_summary: pd.DataFrame,
) -> None:
    lines = [
        "# P5 MV17a Multilingual Feature Contract Sensitivity",
        "",
        f"Generated: `{run_summary['generated_at']}`",
        "",
        "## Scope",
        "",
        "MV17a regenerates the shared text-feature contract with multilingual encoders and reruns only MV07, MV12, and MV15. MV16 remains paused until this sensitivity chain is reviewed.",
        "",
        "## Feature Contract",
        "",
        "| encoder | model | pooling | prefix | max length | dimensions |",
        "| --- | --- | --- | --- | ---: | ---: |",
    ]
    for encoder in run_summary["encoders"]:
        lines.append(
            f"| {encoder['encoder']} | {encoder['model_name']} | {encoder['pooling']} | {encoder['input_prefix_used']} | {encoder['max_length']} | {encoder['expected_dimension']} |"
        )
    lines.extend(
        [
            "",
            "## Feature Coverage",
            "",
            "| encoder | dataset | rows | dimensions | text units | chunks | status |",
            "| --- | --- | ---: | ---: | ---: | ---: | --- |",
        ]
    )
    for _, row in feature_summary.sort_values(["encoder", "dataset"]).iterrows():
        lines.append(
            f"| {row['encoder']} | {row['dataset']} | {int(row['feature_rows'])} | {int(row['feature_columns'])} | {int(row['text_units'])} | {int(row['chunk_count_sum'])} | {row['generation_status']} |"
        )
    if not downstream_summary.empty:
        lines.extend(
            [
                "",
                "## Downstream Chain",
                "",
                "| encoder | experiment | status | pass rule | hygiene |",
                "| --- | --- | --- | --- | --- |",
            ]
        )
        for _, row in downstream_summary.sort_values(["encoder", "experiment"]).iterrows():
            lines.append(
                f"| {row['encoder']} | {row['experiment']} | {row['status']} | {row['pass_rule_status']} | {row['artifact_hygiene_passed']} |"
            )
    lines.extend(
        [
            "",
            "## Output Boundary",
            "",
            "- Feature caches stay under ignored Phase 2 local artifacts.",
            "- Tracked outputs contain aggregate coverage, contracts, downstream status, and hygiene only.",
            "- Clinical content, source locators, row predictions, learned parameters, and embedding matrices are not tracked.",
            "",
            "## Decision",
            "",
            f"- Status: `{run_summary['status']}`.",
            f"- Artifact hygiene passed: `{run_summary['artifact_hygiene_passed']}`.",
            f"- Downstream chain executed: `{run_summary['downstream_chain_executed']}`.",
        ]
    )
    (out_dir / "report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--edaic-manifest", type=Path, default=DEFAULT_EDAIC_MANIFEST)
    parser.add_argument("--manifest-dir", type=Path, default=MANIFEST_DIR)
    parser.add_argument("--split-path", type=Path, default=DEFAULT_SPLIT_PATH)
    parser.add_argument("--feature-root", type=Path, default=DEFAULT_FEATURE_ROOT)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--encoders", nargs="+", choices=sorted(ENCODER_SPECS), default=sorted(ENCODER_SPECS))
    parser.add_argument("--device", default="auto")
    parser.add_argument("--allow-download", action="store_true")
    parser.add_argument("--force-features", action="store_true")
    parser.add_argument("--skip-downstream", action="store_true")
    parser.add_argument("--bge-m3-max-length", type=int, default=ENCODER_SPECS["bge_m3"].default_max_length)
    parser.add_argument("--e5-max-length", type=int, default=ENCODER_SPECS["multilingual_e5_base"].default_max_length)
    return parser.parse_args()


def encoder_with_cli_overrides(spec: EncoderSpec, args: argparse.Namespace) -> EncoderSpec:
    if spec.slug == "bge_m3":
        return EncoderSpec(
            **{**spec.__dict__, "default_max_length": int(args.bge_m3_max_length)}
        )
    if spec.slug == "multilingual_e5_base":
        return EncoderSpec(
            **{**spec.__dict__, "default_max_length": int(args.e5_max_length)}
        )
    raise ValueError(f"unknown encoder spec: {spec.slug}")


def main() -> None:
    args = parse_args()
    if not args.allow_download:
        os.environ.setdefault("HF_HUB_OFFLINE", "1")
        os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")
    out_dir = args.out_dir
    clean_tracked_outputs(out_dir)

    encoders = [encoder_with_cli_overrides(ENCODER_SPECS[name], args) for name in args.encoders]
    edaic_table = edaic_gen.build_subject_table(args.edaic_manifest)
    segment_tables = build_cmdc_pdch_tables(args.split_path)

    all_feature_summaries: list[dict[str, Any]] = []
    for encoder in encoders:
        all_feature_summaries.extend(
            generate_encoder_features(
                encoder,
                edaic_table,
                segment_tables,
                feature_root=args.feature_root,
                device_name=args.device,
                allow_download=args.allow_download,
                force=args.force_features,
            )
        )

    feature_summary = pd.DataFrame(all_feature_summaries)
    feature_summary.to_csv(out_dir / "feature_generation_summary.csv", index=False)
    write_encoder_contract(out_dir, encoders)
    write_local_artifact_manifest(out_dir, all_feature_summaries)

    downstream_rows: list[dict[str, Any]] = []
    if not args.skip_downstream:
        downstream_rows = run_downstream_chain(
            encoders,
            feature_root=args.feature_root,
            out_dir=out_dir,
            manifest_dir=args.manifest_dir,
            split_path=args.split_path,
        )
    downstream_summary = pd.DataFrame(downstream_rows)
    downstream_summary.to_csv(out_dir / "downstream_run_summary.csv", index=False)

    run_summary = {
        "run_id": "P5_MV17a_multilingual_feature_contract",
        "generated_at": utc_now(),
        "status": "complete" if not args.skip_downstream else "feature_generation_complete_downstream_skipped",
        "scope": "multilingual_feature_contract_sensitivity",
        "encoders": [
            {
                "encoder": encoder.slug,
                "model_name": encoder.model_name,
                "pooling": encoder.pooling,
                "input_prefix_used": bool(encoder.input_prefix),
                "max_length": int(encoder.default_max_length),
                "chunk_batch_size": int(encoder.default_chunk_batch_size),
                "expected_dimension": int(encoder.expected_dimension),
                "source_url": encoder.source_url,
            }
            for encoder in encoders
        ],
        "datasets": ["edaic", "cmdc", "pdch"],
        "feature_summary_rows": int(len(feature_summary)),
        "downstream_chain": ["mv07", "mv12", "mv15"],
        "downstream_chain_executed": not args.skip_downstream,
        "mv16_rerun_allowed": False,
        "local_feature_root": rel(args.feature_root),
        "output_policy": {
            "tracked_outputs": sorted(TRACKED_FILES),
            "local_only_feature_root": rel(args.feature_root),
        },
        "artifact_hygiene_passed": False,
    }
    (out_dir / "run_summary.json").write_text(json.dumps(run_summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    write_report(out_dir, run_summary, feature_summary, downstream_summary)
    hygiene = artifact_hygiene(out_dir)
    run_summary["artifact_hygiene_passed"] = bool(hygiene["artifact_hygiene_passed"])
    (out_dir / "run_summary.json").write_text(json.dumps(run_summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    write_report(out_dir, run_summary, feature_summary, downstream_summary)
    hygiene = artifact_hygiene(out_dir)
    (out_dir / "artifact_hygiene_audit.json").write_text(
        json.dumps(hygiene, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    if not hygiene["artifact_hygiene_passed"]:
        raise SystemExit("artifact hygiene violations found; see artifact_hygiene_audit.json")

    print(
        json.dumps(
            {
                "out_dir": rel(out_dir),
                "encoders": [encoder.slug for encoder in encoders],
                "downstream_chain_executed": not args.skip_downstream,
                "artifact_hygiene_passed": bool(hygiene["artifact_hygiene_passed"]),
            },
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
