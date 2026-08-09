#!/usr/bin/env python3
"""Generate local-only E-DAIC BGE features for the MV07 text contract.

This is a feature-contract preparation step, not a trainer. It reads
manifest-governed E-DAIC transcript CSVs, extracts frozen BGE subject
embeddings, and writes the generated feature cache under ignored Phase 2 local
artifacts. Tracked outputs are aggregate audits only; no raw text, source paths,
predictions, learned weights, or raw model responses are written.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import re
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
from transformers import AutoModel, AutoTokenizer


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MANIFEST_PATH = ROOT / "datasets" / "manifests" / "edaic_subjects.csv"
DEFAULT_CACHE_DIR = ROOT / "analysis" / "phase2_baselines" / "edaic_text_bge"
DEFAULT_AUDIT_DIR = ROOT / "analysis" / "phase5_minimal_validation" / "p5_mv07_edaic_bge_generation"
DEFAULT_MODEL_NAME = "BAAI/bge-small-zh-v1.5"
FEATURE_PREFIX = "bge_"
CORE_PHQ8_ITEMS = [
    "PHQ_8NoInterest",
    "PHQ_8Depressed",
    "PHQ_8Sleep",
    "PHQ_8Tired",
    "PHQ_8Appetite",
    "PHQ_8Failure",
    "PHQ_8Concentrating",
    "PHQ_8Moving",
]
TRACKED_FILES = [
    "report.md",
    "run_summary.json",
    "artifact_hygiene_audit.json",
    "local_artifact_manifest.csv",
    "subject_coverage_summary.csv",
]


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT))
    except ValueError:
        return path.name


def clean_value(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, float) and math.isnan(value):
        return ""
    text = str(value).strip()
    return "" if text.lower() in {"", "nan", "none", "null", "<na>"} else text


def safe_float(value: Any) -> float | None:
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return None
    return numeric if math.isfinite(numeric) else None


def parse_json_object(value: Any) -> dict[str, Any]:
    text = clean_value(value)
    if not text:
        return {}
    try:
        obj = json.loads(text)
    except json.JSONDecodeError:
        return {}
    return obj if isinstance(obj, dict) else {}


def phq8_items_complete(value: Any) -> bool:
    payload = parse_json_object(value)
    return all(safe_float(payload.get(item)) is not None for item in CORE_PHQ8_ITEMS)


def bool_series(series: pd.Series) -> pd.Series:
    if pd.api.types.is_bool_dtype(series):
        return series.fillna(False)
    return series.astype(str).str.strip().str.lower().isin({"true", "1", "yes", "y"})


def read_transcript(path_value: Any) -> tuple[str, dict[str, Any]]:
    path = Path(str(path_value))
    if not path.exists():
        raise FileNotFoundError("manifest transcript path is missing")
    transcript = pd.read_csv(path)
    required = {"Start_Time", "End_Time", "Text"}
    missing = required - set(transcript.columns)
    if missing:
        raise ValueError(f"transcript missing required columns: {', '.join(sorted(missing))}")
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
    required = {"subject_id", "official_split", "text_path", "phq8_total", "phq8_items", "file_valid"}
    missing = required - set(manifest.columns)
    if missing:
        raise ValueError(f"E-DAIC manifest missing columns: {', '.join(sorted(missing))}")
    usable = manifest[
        bool_series(manifest["file_valid"])
        & manifest["official_split"].isin(["train", "dev"])
        & manifest["text_path"].notna()
        & manifest["phq8_total"].notna()
        & manifest["phq8_items"].map(phq8_items_complete)
    ].copy()
    if usable.empty:
        raise ValueError("no usable E-DAIC PHQ-8 item-labeled train/dev transcript rows")
    usable["subject_id"] = usable["subject_id"].astype(str)
    if usable["subject_id"].duplicated().any():
        dupes = sorted(usable.loc[usable["subject_id"].duplicated(), "subject_id"].unique())
        raise ValueError(f"E-DAIC manifest should have one row per subject; duplicates observed: {dupes[:10]}")

    rows: list[dict[str, Any]] = []
    for _, row in usable.sort_values("subject_id").iterrows():
        text, stats = read_transcript(row["text_path"])
        rows.append(
            {
                "subject_id": str(row["subject_id"]),
                "split": str(row["official_split"]),
                "text": text,
                **stats,
            }
        )
    table = pd.DataFrame(rows).sort_values("subject_id").reset_index(drop=True)
    if table.empty:
        raise ValueError("no E-DAIC rows survived transcript loading")
    empty_subjects = table.loc[~table["text"].astype(str).str.strip().astype(bool), "subject_id"].tolist()
    if empty_subjects:
        raise ValueError(f"E-DAIC subjects with empty transcript text: {empty_subjects[:10]}")
    train_subjects = set(table.loc[table["split"] == "train", "subject_id"])
    dev_subjects = set(table.loc[table["split"] == "dev", "subject_id"])
    overlap = sorted(train_subjects & dev_subjects)
    if overlap:
        raise ValueError(f"E-DAIC train/dev subject overlap detected: {overlap[:10]}")
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


def feature_columns(hidden_size: int) -> list[str]:
    if hidden_size <= 0:
        raise ValueError("encoder hidden size must be positive")
    return [f"{FEATURE_PREFIX}{idx:04d}" for idx in range(hidden_size)]


def save_cache(path: Path, rows: list[dict[str, Any]]) -> None:
    frame = pd.DataFrame(rows)
    if not frame.empty:
        frame = frame.sort_values("subject_id").reset_index(drop=True)
    frame.to_csv(path, index=False)


def extract_subject_features(
    table: pd.DataFrame,
    cache_dir: Path,
    *,
    model_name: str,
    device_name: str,
    local_files_only: bool,
    max_length: int,
    chunk_batch_size: int,
    force: bool,
) -> tuple[pd.DataFrame, list[str], dict[str, Any]]:
    cache_path = cache_dir / "edaic_bge_subject_features.csv"
    cache_dir.mkdir(parents=True, exist_ok=True)
    required_subjects = set(table["subject_id"].astype(str))
    cached_rows: list[dict[str, Any]] = []
    cached_subjects: set[str] = set()
    embedding_columns: list[str] = []
    if cache_path.exists() and not force:
        cached = pd.read_csv(cache_path)
        cached["subject_id"] = cached["subject_id"].astype(str)
        embedding_columns = [column for column in cached.columns if column.startswith(FEATURE_PREFIX)]
        cached_rows = cached[cached["subject_id"].isin(required_subjects)].to_dict("records")
        cached_subjects = {str(row["subject_id"]) for row in cached_rows}
        if required_subjects.issubset(cached_subjects) and embedding_columns:
            return cached[cached["subject_id"].isin(required_subjects)].copy(), embedding_columns, {
                "model_name": model_name,
                "hidden_size": int(len(embedding_columns)),
                "cached_subject_rows": int(len(cached_rows)),
                "missing_subject_rows": 0,
                "cache_ref": rel(cache_path),
                "device": "not_loaded_cache_complete",
            }

    missing_rows = table[~table["subject_id"].astype(str).isin(cached_subjects)].reset_index(drop=True)
    tokenizer, model, device = load_encoder(model_name, device_name, local_files_only)
    tokenizer_class = type(tokenizer).__name__
    model_class = type(model).__name__
    hidden_size = int(getattr(model.config, "hidden_size", 0) or 0)
    if not embedding_columns:
        embedding_columns = feature_columns(hidden_size)

    print(
        f"Generating E-DAIC BGE subject features: {len(missing_rows)} missing / {len(table)} subjects on {device}",
        flush=True,
    )
    feature_rows = cached_rows
    for idx, row in missing_rows.iterrows():
        if idx == 0 or (idx + 1) % 25 == 0 or (idx + 1) == len(missing_rows):
            print(f"  [edaic-bge] {idx + 1}/{len(missing_rows)} subject={row['subject_id']}", flush=True)
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
                "text_segment_count": 1,
                "token_count_sum": int(token_count),
                "chunk_count_sum": int(chunk_count),
                "empty_text_segments": 0,
                "transcript_turn_count": int(row["transcript_turn_count"]),
                "non_empty_turn_count": int(row["non_empty_turn_count"]),
                "empty_turn_count": int(row["empty_turn_count"]),
                **{column: float(value) for column, value in zip(embedding_columns, embedding, strict=True)},
            }
        )
        if (idx + 1) % 25 == 0:
            save_cache(cache_path, feature_rows)
    save_cache(cache_path, feature_rows)
    del model
    if torch.cuda.is_available():
        torch.cuda.empty_cache()

    features = pd.DataFrame(feature_rows)
    features["subject_id"] = features["subject_id"].astype(str)
    missing_subjects = sorted(required_subjects - set(features["subject_id"]))
    if missing_subjects:
        raise ValueError(f"missing cached E-DAIC BGE rows for subjects: {missing_subjects[:10]}")
    selected = features[features["subject_id"].isin(required_subjects)].sort_values("subject_id").reset_index(drop=True)
    return selected, embedding_columns, {
        "model_name": model_name,
        "tokenizer": tokenizer_class,
        "model_class": model_class,
        "hidden_size": hidden_size,
        "device": str(device),
        "max_length": int(max_length),
        "chunk_batch_size": int(chunk_batch_size),
        "cached_subject_rows": int(len(cached_rows)),
        "missing_subject_rows": int(len(missing_rows)),
        "cache_ref": rel(cache_path),
    }


def subject_coverage_summary(table: pd.DataFrame, features: pd.DataFrame, embedding_columns: list[str]) -> pd.DataFrame:
    split_counts = table.groupby("split")["subject_id"].nunique().to_dict()
    feature_split_counts = features.groupby("split")["subject_id"].nunique().to_dict() if "split" in features.columns else {}
    return pd.DataFrame(
        [
            {
                "dataset": "edaic",
                "feature_family": "text_bge",
                "model_input_columns": int(len(embedding_columns)),
                "manifest_subjects": int(table["subject_id"].nunique()),
                "feature_subjects": int(features["subject_id"].nunique()),
                "train_manifest_subjects": int(split_counts.get("train", 0)),
                "dev_manifest_subjects": int(split_counts.get("dev", 0)),
                "train_feature_subjects": int(feature_split_counts.get("train", 0)),
                "dev_feature_subjects": int(feature_split_counts.get("dev", 0)),
                "subject_overlap_violations": int(bool(set(table.loc[table["split"] == "train", "subject_id"]) & set(table.loc[table["split"] == "dev", "subject_id"]))),
                "path_like_columns": ";".join([column for column in features.columns if "path" in column.lower()]),
                "raw_text_written": False,
                "source_paths_written": False,
            }
        ]
    )


def artifact_hygiene(audit_dir: Path) -> dict[str, Any]:
    forbidden_patterns = [
        r"/root/",
        r"/autodl-tmp/",
        r"\btext_path\b",
        r"\baudio_path\b",
        r"\bvideo_path\b",
        r"\bgait_path\b",
        r"\.wav\b",
        r"\.mp4\b",
        r"\.avi\b",
        r"raw text",
        r"raw transcript",
        r"source path",
    ]
    violations: list[dict[str, str]] = []
    checked = 0
    for path in sorted(audit_dir.glob("*")):
        if not path.is_file() or path.name not in TRACKED_FILES:
            continue
        checked += 1
        text = path.read_text(encoding="utf-8", errors="ignore")
        for pattern in forbidden_patterns:
            if re.search(pattern, text, flags=re.IGNORECASE):
                violations.append({"file": path.name, "pattern": pattern})
    return {
        "audit_id": "P5_MV07_edaic_bge_generation_hygiene",
        "generated_at": utc_now(),
        "files_checked": checked,
        "artifact_hygiene_passed": not violations,
        "violation_count": len(violations),
        "violations": violations,
    }


def write_report(audit_dir: Path, run_summary: dict[str, Any], coverage: pd.DataFrame) -> None:
    row = coverage.iloc[0].to_dict()
    lines = [
        "# P5 MV07 E-DAIC BGE Feature Generation",
        "",
        f"Generated: `{run_summary['generated_at']}`",
        "",
        "## Scope",
        "",
        "This step generates the local-only E-DAIC subject-level BGE cache needed by the MV07 aligned text contract. It is not a model-training run.",
        "",
        "## Decision",
        "",
        f"- Status: `{run_summary['status']}`.",
        f"- Model: `{run_summary['model_name']}`.",
        f"- Feature subjects: `{row['feature_subjects']}`.",
        f"- Model input columns: `{row['model_input_columns']}`.",
        f"- Subject-overlap violations: `{row['subject_overlap_violations']}`.",
        f"- Artifact hygiene passed: `{run_summary['artifact_hygiene_passed']}`.",
        "",
        "## Output Boundary",
        "",
        "- The generated BGE cache is local-only and ignored by Git.",
        "- Tracked outputs contain only aggregate coverage, run summary, artifact manifest, and hygiene audit.",
        "- No transcript text, source locators, row predictions, learned weights, or model responses are written to tracked outputs.",
        "",
        "## Next Handoff",
        "",
        "Rerun MV07 readiness. If the BGE contract becomes ready, run the shallow shared-symptom MV07 validation row with identity/protocol probes and local-only predictions.",
    ]
    (audit_dir / "report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_local_artifact_manifest(audit_dir: Path, cache_path: Path, features: pd.DataFrame) -> None:
    manifest = pd.DataFrame(
        [
            {
                "artifact": rel(cache_path),
                "artifact_class": "local_only_feature_cache",
                "exists": cache_path.exists(),
                "rows": int(len(features)),
                "columns": int(len(features.columns)),
                "version_policy": "ignored_by_git_do_not_commit",
            }
        ]
    )
    manifest.to_csv(audit_dir / "local_artifact_manifest.csv", index=False)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest-path", type=Path, default=DEFAULT_MANIFEST_PATH)
    parser.add_argument("--cache-dir", type=Path, default=DEFAULT_CACHE_DIR)
    parser.add_argument("--audit-dir", type=Path, default=DEFAULT_AUDIT_DIR)
    parser.add_argument("--model-name", default=DEFAULT_MODEL_NAME)
    parser.add_argument("--device", default="auto")
    parser.add_argument("--allow-download", action="store_true")
    parser.add_argument("--max-length", type=int, default=512)
    parser.add_argument("--chunk-batch-size", type=int, default=16)
    parser.add_argument("--force", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    args.audit_dir.mkdir(parents=True, exist_ok=True)
    table = build_subject_table(args.manifest_path)
    features, embedding_columns, extractor_summary = extract_subject_features(
        table,
        args.cache_dir,
        model_name=args.model_name,
        device_name=args.device,
        local_files_only=not args.allow_download,
        max_length=args.max_length,
        chunk_batch_size=args.chunk_batch_size,
        force=args.force,
    )
    coverage = subject_coverage_summary(table, features, embedding_columns)
    coverage.to_csv(args.audit_dir / "subject_coverage_summary.csv", index=False)
    cache_path = args.cache_dir / "edaic_bge_subject_features.csv"
    write_local_artifact_manifest(args.audit_dir, cache_path, features)

    run_summary = {
        "run_id": "P5_MV07_edaic_bge_generation",
        "generated_at": utc_now(),
        "status": "complete_local_feature_cache_generated",
        "scope": "local_only_feature_contract_preparation",
        "model_name": args.model_name,
        "input_contract": {
            "manifest_governed_transcripts_read": True,
            "raw_text_written": False,
            "source_paths_written": False,
            "row_predictions_written": False,
            "encoder_frozen": True,
            "test_split_used": False,
        },
        "extractor_summary": extractor_summary,
        "output_policy": {
            "tracked_outputs": TRACKED_FILES,
            "local_only_outputs": ["analysis/phase2_baselines/edaic_text_bge/edaic_bge_subject_features.csv"],
        },
        "artifact_hygiene_passed": False,
    }
    (args.audit_dir / "run_summary.json").write_text(
        json.dumps(run_summary, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    write_report(args.audit_dir, run_summary, coverage)
    hygiene = artifact_hygiene(args.audit_dir)
    run_summary["artifact_hygiene_passed"] = bool(hygiene["artifact_hygiene_passed"])
    (args.audit_dir / "run_summary.json").write_text(
        json.dumps(run_summary, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    write_report(args.audit_dir, run_summary, coverage)
    hygiene = artifact_hygiene(args.audit_dir)
    (args.audit_dir / "artifact_hygiene_audit.json").write_text(
        json.dumps(hygiene, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    if not hygiene["artifact_hygiene_passed"]:
        raise SystemExit("artifact hygiene violations found; see artifact_hygiene_audit.json")
    print(
        json.dumps(
            {
                "audit_dir": str(args.audit_dir),
                "cache": rel(cache_path),
                "feature_subjects": int(features["subject_id"].nunique()),
                "model_input_columns": int(len(embedding_columns)),
            },
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
