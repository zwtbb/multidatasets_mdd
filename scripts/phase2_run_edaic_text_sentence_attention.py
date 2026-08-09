#!/usr/bin/env python3
"""Run the Phase 2 E-DAIC sentence encoder + attention pooling baseline.

The runner treats each non-empty ASR transcript row as a sentence-level unit,
extracts frozen sentence embeddings, trains a small attention-pooling
regression head on the official train split, and evaluates on the official dev
split. It writes no raw transcript text, source paths, or file names.
"""

from __future__ import annotations

import argparse
import json
import os
import random
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
from torch import nn
from torch.utils.data import DataLoader, Dataset
from transformers import AutoModel, AutoTokenizer

from phase2_metrics import metric_records


ROOT = Path("/root/autodl-tmp")
MANIFEST_PATH = ROOT / "datasets" / "manifests" / "edaic_subjects.csv"
DEFAULT_OUT_DIR = ROOT / "analysis" / "phase2_baselines" / "edaic_text_sentence_attention"
DEFAULT_MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
RUN_ID = "edaic_text_phq8_sentence_attention"
SEEDS = [0, 1, 2, 3, 4]
ATTENTION_HIDDEN_SIZE = 64
MAX_EPOCHS = 200
LEARNING_RATE = 1.0e-3
WEIGHT_DECAY = 1.0e-4
TRAIN_BATCH_SIZE = 32


@dataclass
class SubjectSequence:
    subject_id: str
    split: str
    y: float
    embeddings: np.ndarray
    turn_token_counts: np.ndarray


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def set_seed(seed: int) -> None:
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)


def read_transcript_turns(path_value: Any) -> tuple[list[str], dict[str, Any]]:
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
    if not non_empty:
        raise ValueError(f"transcript has no non-empty ASR text rows: {path}")
    return non_empty, {
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
        manifest["file_valid"].fillna(False).astype(bool)
        & manifest["official_split"].isin(["train", "dev"])
        & manifest["text_path"].notna()
        & manifest["phq8_total"].notna()
    ].copy()
    if usable.empty:
        raise ValueError("no usable E-DAIC train/dev rows")
    usable["subject_id"] = usable["subject_id"].astype(str)
    if usable["subject_id"].duplicated().any():
        dupes = sorted(usable.loc[usable["subject_id"].duplicated(), "subject_id"].unique())
        raise ValueError(f"E-DAIC manifest should have one row per subject, duplicates: {dupes[:10]}")

    rows: list[dict[str, Any]] = []
    turns_by_subject: dict[str, list[str]] = {}
    for _, row in usable.sort_values("subject_id").iterrows():
        turns, stats = read_transcript_turns(row["text_path"])
        subject_id = str(row["subject_id"])
        turns_by_subject[subject_id] = turns
        rows.append(
            {
                "subject_id": subject_id,
                "split": str(row["official_split"]),
                "phq8_total": float(row["phq8_total"]),
                **stats,
            }
        )
    table = pd.DataFrame(rows).sort_values("subject_id").reset_index(drop=True)
    table.attrs["turns_by_subject"] = turns_by_subject
    train_subjects = set(table.loc[table["split"] == "train", "subject_id"])
    dev_subjects = set(table.loc[table["split"] == "dev", "subject_id"])
    overlap = sorted(train_subjects & dev_subjects)
    if overlap:
        raise ValueError(f"subject-level train/dev overlap detected: {overlap[:10]}")
    if not train_subjects or not dev_subjects:
        raise ValueError("E-DAIC sentence attention requires non-empty train and dev splits")
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


def mean_pool_hidden(hidden: torch.Tensor, attention_mask: torch.Tensor) -> torch.Tensor:
    mask = attention_mask.to(dtype=hidden.dtype).unsqueeze(-1)
    summed = (hidden * mask).sum(dim=1)
    denom = torch.clamp(mask.sum(dim=1), min=1.0)
    return summed / denom


def token_counts(tokenizer: Any, texts: list[str]) -> np.ndarray:
    encoded = tokenizer(texts, add_special_tokens=False, padding=False, truncation=False)
    return np.asarray([len(ids) for ids in encoded["input_ids"]], dtype=np.int32)


def embed_turns(
    turns: list[str],
    tokenizer: Any,
    model: torch.nn.Module,
    device: torch.device,
    *,
    max_length: int,
    batch_size: int,
) -> tuple[np.ndarray, np.ndarray, int]:
    counts = token_counts(tokenizer, turns)
    truncated_count = int(np.sum(counts > max(1, max_length - 2)))
    embeddings: list[np.ndarray] = []
    for start in range(0, len(turns), batch_size):
        batch_texts = turns[start : start + batch_size]
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
            pooled = mean_pool_hidden(output.last_hidden_state, batch["attention_mask"])
            pooled = torch.nn.functional.normalize(pooled, p=2, dim=1)
        embeddings.extend(pooled.detach().cpu().numpy())
    return np.vstack(embeddings).astype(np.float32), counts, truncated_count


def subject_cache_path(cache_dir: Path, subject_id: str) -> Path:
    return cache_dir / f"{subject_id}.npz"


def save_metadata(path: Path, rows: list[dict[str, Any]]) -> None:
    frame = pd.DataFrame(rows)
    if not frame.empty:
        frame = frame.sort_values("subject_id").reset_index(drop=True)
    frame.to_csv(path, index=False)


def extract_turn_embedding_cache(
    table: pd.DataFrame,
    out_dir: Path,
    *,
    model_name: str,
    device_name: str,
    local_files_only: bool,
    max_length: int,
    encode_batch_size: int,
    force: bool,
) -> tuple[list[SubjectSequence], dict[str, Any]]:
    cache_dir = out_dir / "sentence_turn_embeddings"
    cache_dir.mkdir(parents=True, exist_ok=True)
    metadata_path = out_dir / "sentence_turn_metadata.csv"
    turns_by_subject: dict[str, list[str]] = table.attrs["turns_by_subject"]
    required_subjects = set(table["subject_id"].astype(str))
    missing_subjects = [
        subject_id
        for subject_id in table["subject_id"].astype(str).tolist()
        if force or not subject_cache_path(cache_dir, subject_id).exists()
    ]

    extractor_summary: dict[str, Any] = {
        "model_name": model_name,
        "max_length": int(max_length),
        "encode_batch_size": int(encode_batch_size),
        "cached_subject_rows": int(len(required_subjects) - len(missing_subjects)),
        "missing_subject_rows": int(len(missing_subjects)),
        "cache_dir": str(cache_dir),
    }
    if missing_subjects:
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
        print(
            f"Extracting E-DAIC sentence-turn embeddings: {len(missing_subjects)} missing / {len(required_subjects)} subjects on {device}",
            flush=True,
        )
        for idx, subject_id in enumerate(missing_subjects):
            if idx == 0 or (idx + 1) % 25 == 0 or (idx + 1) == len(missing_subjects):
                print(f"  [sentence-attention] {idx + 1}/{len(missing_subjects)} subject={subject_id}", flush=True)
            embeddings, counts, truncated_count = embed_turns(
                turns_by_subject[subject_id],
                tokenizer,
                model,
                device,
                max_length=max_length,
                batch_size=encode_batch_size,
            )
            np.savez_compressed(
                subject_cache_path(cache_dir, subject_id),
                embeddings=embeddings,
                token_counts=counts,
                truncated_turn_count=np.asarray([truncated_count], dtype=np.int32),
            )
        del model
        if torch.cuda.is_available():
            torch.cuda.empty_cache()

    sequences: list[SubjectSequence] = []
    metadata_rows: list[dict[str, Any]] = []
    label_lookup = table.set_index("subject_id", drop=False).to_dict("index")
    for subject_id in table["subject_id"].astype(str).tolist():
        path = subject_cache_path(cache_dir, subject_id)
        if not path.exists():
            raise FileNotFoundError(f"missing sentence embedding cache for subject {subject_id}: {path}")
        data = np.load(path)
        embeddings = np.asarray(data["embeddings"], dtype=np.float32)
        counts = np.asarray(data["token_counts"], dtype=np.int32)
        truncated_turn_count = int(np.asarray(data["truncated_turn_count"]).reshape(-1)[0])
        if embeddings.ndim != 2 or embeddings.shape[0] <= 0:
            raise ValueError(f"invalid embedding cache shape for subject {subject_id}: {embeddings.shape}")
        row = label_lookup[subject_id]
        sequences.append(
            SubjectSequence(
                subject_id=subject_id,
                split=str(row["split"]),
                y=float(row["phq8_total"]),
                embeddings=embeddings,
                turn_token_counts=counts,
            )
        )
        metadata_rows.append(
            {
                "subject_id": subject_id,
                "split": str(row["split"]),
                "turn_count": int(embeddings.shape[0]),
                "embedding_dim": int(embeddings.shape[1]),
                "token_count_sum": int(counts.sum()),
                "token_count_max": int(counts.max()) if counts.size else 0,
                "truncated_turn_count": truncated_turn_count,
            }
        )
    save_metadata(metadata_path, metadata_rows)
    if "hidden_size" not in extractor_summary and sequences:
        extractor_summary["hidden_size"] = int(sequences[0].embeddings.shape[1])
    extractor_summary["metadata_path"] = str(metadata_path)
    extractor_summary["subject_rows"] = int(len(sequences))
    extractor_summary["turn_rows"] = int(sum(seq.embeddings.shape[0] for seq in sequences))
    extractor_summary["token_count_sum"] = int(sum(seq.turn_token_counts.sum() for seq in sequences))
    return sequences, extractor_summary


class SequenceDataset(Dataset):
    def __init__(self, sequences: list[SubjectSequence], y_mean: float, y_std: float) -> None:
        self.sequences = sequences
        self.y_mean = y_mean
        self.y_std = y_std

    def __len__(self) -> int:
        return len(self.sequences)

    def __getitem__(self, index: int) -> SubjectSequence:
        return self.sequences[index]

    def collate(self, batch: list[SubjectSequence]) -> dict[str, Any]:
        max_len = max(item.embeddings.shape[0] for item in batch)
        dim = batch[0].embeddings.shape[1]
        x = np.zeros((len(batch), max_len, dim), dtype=np.float32)
        mask = np.zeros((len(batch), max_len), dtype=bool)
        y = np.zeros((len(batch),), dtype=np.float32)
        subject_ids: list[str] = []
        turn_counts: list[int] = []
        token_count_sums: list[int] = []
        for idx, item in enumerate(batch):
            length = item.embeddings.shape[0]
            x[idx, :length, :] = item.embeddings
            mask[idx, :length] = True
            y[idx] = (float(item.y) - self.y_mean) / self.y_std
            subject_ids.append(item.subject_id)
            turn_counts.append(length)
            token_count_sums.append(int(item.turn_token_counts.sum()))
        return {
            "x": torch.from_numpy(x),
            "mask": torch.from_numpy(mask),
            "y": torch.from_numpy(y),
            "subject_ids": subject_ids,
            "turn_counts": turn_counts,
            "token_count_sums": token_count_sums,
        }


class AttentionPoolingRegressor(nn.Module):
    def __init__(self, input_dim: int, attention_hidden_size: int) -> None:
        super().__init__()
        self.attention = nn.Sequential(
            nn.Linear(input_dim, attention_hidden_size),
            nn.Tanh(),
            nn.Linear(attention_hidden_size, 1),
        )
        self.regressor = nn.Linear(input_dim, 1)

    def forward(self, x: torch.Tensor, mask: torch.Tensor) -> torch.Tensor:
        scores = self.attention(x).squeeze(-1)
        scores = scores.masked_fill(~mask, -1.0e9)
        weights = torch.softmax(scores, dim=1)
        pooled = torch.sum(x * weights.unsqueeze(-1), dim=1)
        return self.regressor(pooled).squeeze(-1)


def train_attention_model(
    train_sequences: list[SubjectSequence],
    *,
    seed: int,
    device: torch.device,
) -> tuple[AttentionPoolingRegressor, dict[str, Any]]:
    set_seed(seed)
    y_values = np.asarray([seq.y for seq in train_sequences], dtype=np.float32)
    y_mean = float(y_values.mean())
    y_std = float(y_values.std())
    if y_std <= 1.0e-6:
        y_std = 1.0
    input_dim = int(train_sequences[0].embeddings.shape[1])
    dataset = SequenceDataset(train_sequences, y_mean, y_std)
    generator = torch.Generator()
    generator.manual_seed(seed)
    loader = DataLoader(
        dataset,
        batch_size=TRAIN_BATCH_SIZE,
        shuffle=True,
        generator=generator,
        collate_fn=dataset.collate,
    )
    model = AttentionPoolingRegressor(input_dim=input_dim, attention_hidden_size=ATTENTION_HIDDEN_SIZE).to(device)
    optimizer = torch.optim.AdamW(model.parameters(), lr=LEARNING_RATE, weight_decay=WEIGHT_DECAY)
    loss_fn = nn.MSELoss()
    losses: list[float] = []
    model.train()
    for _epoch in range(MAX_EPOCHS):
        epoch_losses: list[float] = []
        for batch in loader:
            x = batch["x"].to(device)
            mask = batch["mask"].to(device)
            y = batch["y"].to(device)
            optimizer.zero_grad(set_to_none=True)
            pred = model(x, mask)
            loss = loss_fn(pred, y)
            loss.backward()
            optimizer.step()
            epoch_losses.append(float(loss.detach().cpu()))
        losses.append(float(np.mean(epoch_losses)))
    model.eval()
    model.y_mean = y_mean  # type: ignore[attr-defined]
    model.y_std = y_std  # type: ignore[attr-defined]
    return model, {
        "seed": int(seed),
        "epochs": int(MAX_EPOCHS),
        "learning_rate": float(LEARNING_RATE),
        "weight_decay": float(WEIGHT_DECAY),
        "train_batch_size": int(TRAIN_BATCH_SIZE),
        "attention_hidden_size": int(ATTENTION_HIDDEN_SIZE),
        "target_mean_train": y_mean,
        "target_std_train": y_std,
        "final_train_loss": float(losses[-1]),
        "min_train_loss": float(np.min(losses)),
    }


def predict_sequences(
    model: AttentionPoolingRegressor,
    sequences: list[SubjectSequence],
    *,
    device: torch.device,
) -> list[dict[str, Any]]:
    y_mean = float(model.y_mean)  # type: ignore[attr-defined]
    y_std = float(model.y_std)  # type: ignore[attr-defined]
    dataset = SequenceDataset(sequences, y_mean, y_std)
    loader = DataLoader(dataset, batch_size=TRAIN_BATCH_SIZE, shuffle=False, collate_fn=dataset.collate)
    rows: list[dict[str, Any]] = []
    model.eval()
    with torch.inference_mode():
        for batch in loader:
            pred_scaled = model(batch["x"].to(device), batch["mask"].to(device)).detach().cpu().numpy()
            pred = pred_scaled * y_std + y_mean
            for idx, subject_id in enumerate(batch["subject_ids"]):
                rows.append(
                    {
                        "subject_id": str(subject_id),
                        "y_pred_raw": float(pred[idx]),
                        "turn_count": int(batch["turn_counts"][idx]),
                        "token_count_sum": int(batch["token_count_sums"][idx]),
                    }
                )
    return rows


def clip_predictions(y_pred: np.ndarray, train_sequences: list[SubjectSequence]) -> tuple[np.ndarray, int, float, float]:
    y_train = np.asarray([seq.y for seq in train_sequences], dtype=np.float64)
    low = float(y_train.min())
    high = float(y_train.max())
    clipped = np.clip(np.asarray(y_pred, dtype=np.float64), low, high)
    return clipped, int(np.sum(np.abs(clipped - y_pred) > 1.0e-12)), low, high


def run_sentence_attention(sequences: list[SubjectSequence], device_name: str) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    device = torch.device(device_name if device_name != "auto" else ("cuda" if torch.cuda.is_available() else "cpu"))
    train_sequences = [seq for seq in sequences if seq.split == "train"]
    dev_sequences = [seq for seq in sequences if seq.split == "dev"]
    if not train_sequences or not dev_sequences:
        raise ValueError("sentence attention requires non-empty train and dev sequences")
    predictions: list[dict[str, Any]] = []
    seed_summaries: list[dict[str, Any]] = []
    dev_by_subject = {seq.subject_id: seq for seq in dev_sequences}
    for seed in SEEDS:
        model, seed_summary = train_attention_model(train_sequences, seed=seed, device=device)
        pred_rows = predict_sequences(model, dev_sequences, device=device)
        raw_pred = np.asarray([row["y_pred_raw"] for row in pred_rows], dtype=np.float64)
        y_pred, clip_count, low, high = clip_predictions(raw_pred, train_sequences)
        for idx, row in enumerate(pred_rows):
            subject = dev_by_subject[row["subject_id"]]
            predictions.append(
                {
                    "run_id": RUN_ID,
                    "dataset": "E-DAIC",
                    "modality": "Text",
                    "task": "PHQ-8 regression",
                    "model": "sentence encoder + attention pooling",
                    "seed": int(seed),
                    "task_type": "severity_regression",
                    "subject_id": row["subject_id"],
                    "split": "dev",
                    "turn_count": int(row["turn_count"]),
                    "token_count_sum": int(row["token_count_sum"]),
                    "y_true": float(subject.y),
                    "y_pred": float(y_pred[idx]),
                    "y_score": "",
                    "prediction_clipped_to_train_target_range": True,
                }
            )
        seed_summaries.append(
            {
                **seed_summary,
                "train_subjects": int(len(train_sequences)),
                "dev_subjects": int(len(dev_sequences)),
                "target_min_train": float(low),
                "target_max_train": float(high),
                "dev_clip_count": int(clip_count),
            }
        )
        del model
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
    return predictions, {
        "run_id": RUN_ID,
        "feature_count": int(sequences[0].embeddings.shape[1]),
        "train_subjects": int(len(train_sequences)),
        "dev_subjects": int(len(dev_sequences)),
        "prediction_rows": int(len(predictions)),
        "train_turn_rows": int(sum(seq.embeddings.shape[0] for seq in train_sequences)),
        "dev_turn_rows": int(sum(seq.embeddings.shape[0] for seq in dev_sequences)),
        "seed_summaries": seed_summaries,
    }


def write_report(out_dir: Path, summary: dict[str, Any]) -> None:
    lines = [
        "# E-DAIC Sentence Encoder Attention Pooling Phase 2 Baseline",
        "",
        f"Generated: `{summary['generated_at']}`",
        "",
        "## Protocol",
        "",
        "- Input interface: manifest-resolved E-DAIC transcript CSV paths.",
        "- Unit: each non-empty ASR `Text` row is treated as one sentence-level turn.",
        "- Encoder: frozen sentence encoder; no encoder parameters are updated.",
        "- Turn embedding: mean-pool last hidden states with the tokenizer attention mask, then L2-normalize.",
        "- Pooling head: trainable attention pooling over turn embeddings followed by a linear PHQ-8 regressor.",
        "- Fit on the official train split and evaluate on the official dev split.",
        "- Regression outputs are clipped to the train-split observed PHQ-8 range.",
        "- No dev or test labels are used for encoder extraction or hyperparameter selection.",
        "- No test split is used.",
        "- Raw transcript text, source paths, and file names are not written to outputs.",
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
        "- `edaic_text_sentence_attention_predictions.csv`",
        "- `sentence_turn_metadata.csv`",
        "- `sentence_turn_embeddings/*.npz`",
        "- `phase2_metrics_by_seed.csv`",
        "- `phase2_metric_summary.csv`",
        "- `edaic_text_sentence_attention_run_summary.json`",
    ]
    (out_dir / "edaic_text_sentence_attention_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest-path", type=Path, default=MANIFEST_PATH)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--model-name", default=DEFAULT_MODEL_NAME)
    parser.add_argument("--device", default="auto")
    parser.add_argument("--local-files-only", action="store_true")
    parser.add_argument("--max-length", type=int, default=128)
    parser.add_argument("--encode-batch-size", type=int, default=128)
    parser.add_argument("--bootstrap-resamples", type=int, default=1000)
    parser.add_argument("--force-embeddings", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    args.out_dir.mkdir(parents=True, exist_ok=True)
    table = build_subject_table(args.manifest_path)
    sequences, extractor_summary = extract_turn_embedding_cache(
        table,
        args.out_dir,
        model_name=args.model_name,
        device_name=args.device,
        local_files_only=args.local_files_only,
        max_length=args.max_length,
        encode_batch_size=args.encode_batch_size,
        force=args.force_embeddings,
    )
    predictions, run_summary = run_sentence_attention(sequences, args.device)
    predictions_frame = pd.DataFrame(predictions)
    predictions_path = args.out_dir / "edaic_text_sentence_attention_predictions.csv"
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
        "runs": [RUN_ID],
        "model_name": args.model_name,
        "extractor_summary": extractor_summary,
        "run_summary": run_summary,
        "seeds": SEEDS,
        "seed_count": len(SEEDS),
        "bootstrap_resamples": int(args.bootstrap_resamples),
        "train_subjects": int(len(train_subjects)),
        "dev_subjects": int(len(dev_subjects)),
        "test_subjects_used": 0,
        "prediction_rows": int(len(predictions_frame)),
        "subject_overlap_violations": int(bool(train_subjects & dev_subjects)),
        "encoder_frozen": True,
        "no_test_split_used": True,
        "raw_text_written": False,
        "source_paths_written": False,
    }
    (args.out_dir / "edaic_text_sentence_attention_run_summary.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=True, sort_keys=True),
        encoding="utf-8",
    )
    write_report(args.out_dir, summary)
    print(f"Wrote {predictions_path}")
    print(f"Wrote {args.out_dir / 'phase2_metric_summary.csv'}")


if __name__ == "__main__":
    main()
