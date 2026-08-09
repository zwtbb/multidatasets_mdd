#!/usr/bin/env python3
"""Run the Phase 2 MPDD-AVG official public baseline wrapper.

This runner preserves the official MPDD-AVG baseline model family
(`TorchcatBaseline`, A-V+P, BiLSTM temporal encoders, classification plus PHQ-9
regression heads) while adapting only the data entrance and evaluation
resampling to this project's audited manifest and subject-level evaluation
contract.

The official README/code use `split_labels_train.csv` as a trainval pool and
carve an internal validation split from it before test-only evaluation. This
wrapper keeps the same fold-local validation-selection idea inside each outer
OOF train fold, but uses deterministic split seeds for comparability.

The official code has separate Track1/Track2 input dimensions for Elder and
Young wav2vec features, so this wrapper trains a track-specific model inside
each outer OOF split and merges the predictions into one matrix row.
"""

from __future__ import annotations

import argparse
import copy
import json
import os
import random
import re
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable


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
import torch.nn as nn
from sklearn.metrics import accuracy_score, f1_score
from sklearn.model_selection import ShuffleSplit, StratifiedKFold, StratifiedShuffleSplit
from torch.utils.data import DataLoader, Dataset

from phase2_metrics import metric_records, ordinal_metrics


ROOT = Path("/root/autodl-tmp")
MANIFEST_PATH = ROOT / "datasets" / "manifests" / "mpdd_avg_2026_subjects.csv"
DEFAULT_OUT_DIR = ROOT / "analysis" / "phase2_baselines" / "mpdd_public_official"
OFFICIAL_REPO = ROOT / "cache" / "official_baselines" / "MPDD-AVG-2026"
DATA_ROOT = ROOT / "datasets" / "MPDD-AVG-2026"
DATASET_DISPLAY = "MPDD-AVG-2026"
RUN_ID = "mpdd_public_official"
SEEDS = [0, 1, 2, 3, 4]
PAIR_COUNT = 4
TARGET_T = 128
SUBTRACK = "A-V+P"
ENCODER_TYPE = "bilstm_mean"
AUDIO_FEATURE = "wav2vec2"
VIDEO_FEATURE = "resnet"
MODEL_NAME = "MPDD official baseline"
OFFICIAL_README_URL = "https://github.com/hacilab/MPDD-AVG-2026/blob/main/README.md"

if str(OFFICIAL_REPO) not in sys.path:
    sys.path.insert(0, str(OFFICIAL_REPO))

try:
    from dataset import _normalize, _resize, normalize_phq_target  # type: ignore
    from models import TorchcatBaseline  # type: ignore
except ImportError as exc:  # pragma: no cover - caught in runtime smoke.
    raise RuntimeError(f"Could not import official MPDD baseline modules from {OFFICIAL_REPO}") from exc


@dataclass(frozen=True)
class TrackConfig:
    track: str
    age_group: str
    dataset_dir: str
    audio_dim_name: str
    epochs: int
    batch_size: int
    lr: float
    weight_decay: float
    hidden_dim: int
    dropout: float
    patience: int
    val_ratio: float
    min_delta: float = 1e-4

    @property
    def audio_root(self) -> Path:
        return DATA_ROOT / self.dataset_dir / "Audio" / "train" / "wav2vec2"

    @property
    def video_root(self) -> Path:
        return DATA_ROOT / self.dataset_dir / "Video" / "train" / "resnet"

    @property
    def personality_npy(self) -> Path:
        return DATA_ROOT / self.dataset_dir / "descriptions_embeddings_with_ids.npy"


TRACK_CONFIGS = {
    "elder": TrackConfig(
        track="Track1",
        age_group="elder",
        dataset_dir="Train-MPDD-Elder",
        audio_dim_name="wav2vec2_768",
        epochs=140,
        batch_size=4,
        lr=2e-4,
        weight_decay=5e-5,
        hidden_dim=160,
        dropout=0.5,
        patience=30,
        val_ratio=0.1,
    ),
    "young": TrackConfig(
        track="Track2",
        age_group="young",
        dataset_dir="Train-MPDD-Young",
        audio_dim_name="wav2vec2_1024",
        epochs=80,
        batch_size=8,
        lr=5e-4,
        weight_decay=1e-4,
        hidden_dim=64,
        dropout=0.4,
        patience=15,
        val_ratio=0.1,
    ),
}


@dataclass
class SubjectExample:
    subject_id: str
    numeric_id: int
    age_group: str
    severity_label: int
    binary_label: int
    phq9_total: float
    phq9_normalized: float
    audio: torch.Tensor
    video: torch.Tensor
    pair_mask: torch.Tensor
    personality: torch.Tensor
    pair_count: int
    audio_dim: int
    video_dim: int
    audio_frame_count: int
    video_frame_count: int
    nonfinite_input_count: int
    personality_available: bool


class SubjectTensorDataset(Dataset):
    def __init__(self, examples: list[SubjectExample], indices: Iterable[int]) -> None:
        self.examples = examples
        self.indices = list(indices)

    def __len__(self) -> int:
        return len(self.indices)

    def __getitem__(self, item: int) -> dict[str, torch.Tensor]:
        ex = self.examples[self.indices[item]]
        return {
            "label": torch.tensor(ex.severity_label, dtype=torch.long),
            "phq9": torch.tensor(ex.phq9_normalized, dtype=torch.float32),
            "audio": ex.audio,
            "video": ex.video,
            "pair_mask": ex.pair_mask,
            "personality": ex.personality,
        }


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def natural_key(value: Any) -> list[Any]:
    return [int(part) if part.isdigit() else part for part in re.split(r"(\d+)", str(value))]


def parse_seed_list(value: str) -> list[int]:
    seeds = [int(part.strip()) for part in value.split(",") if part.strip()]
    if not seeds:
        raise ValueError("--seeds must contain at least one integer")
    return seeds


def bool_series(series: pd.Series) -> pd.Series:
    if pd.api.types.is_bool_dtype(series):
        return series.fillna(False)
    return series.fillna("").astype(str).str.strip().str.lower().isin({"true", "1", "yes", "y"})


def read_manifest(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"manifest missing: {path}")
    return pd.read_csv(path)


def labeled_subject_rows(manifest_path: Path) -> pd.DataFrame:
    manifest = read_manifest(manifest_path)
    required = {
        "subject_id",
        "official_split",
        "file_valid",
        "age",
        "phq9_total",
        "binary_label",
        "severity_label",
        "video_feature_type",
    }
    missing = required - set(manifest.columns)
    if missing:
        raise ValueError(f"MPDD manifest missing columns: {', '.join(sorted(missing))}")

    rows = manifest[
        bool_series(manifest["file_valid"])
        & manifest["official_split"].astype(str).eq("train")
        & manifest["phq9_total"].notna()
        & manifest["binary_label"].notna()
        & manifest["severity_label"].notna()
    ].copy()
    if rows.empty:
        raise ValueError("no labeled MPDD train rows are available")

    subject_rows: list[dict[str, Any]] = []
    for subject_id, group in rows.groupby("subject_id", sort=False):
        labels = group["severity_label"].dropna().astype(float).unique()
        binaries = group["binary_label"].dropna().astype(float).unique()
        phq9_values = group["phq9_total"].dropna().astype(float).unique()
        ages = group["age"].dropna().astype(str).unique()
        video_types = set(group["video_feature_type"].dropna().astype(str))
        if len(labels) != 1 or len(binaries) != 1 or len(phq9_values) != 1:
            raise ValueError(f"{subject_id} has inconsistent MPDD labels")
        if len(ages) != 1 or ages[0] not in TRACK_CONFIGS:
            raise ValueError(f"{subject_id} has invalid MPDD age group: {ages}")
        if "resnet_npy" not in video_types:
            raise ValueError(f"{subject_id} does not expose resnet_npy in the manifest")
        numeric_text = str(subject_id).split("_", 1)[-1]
        subject_rows.append(
            {
                "subject_id": str(subject_id),
                "numeric_id": int(numeric_text),
                "age_group": str(ages[0]),
                "phq9_total": float(phq9_values[0]),
                "binary_label": int(float(binaries[0])),
                "severity_label": int(float(labels[0])),
            }
        )
    return (
        pd.DataFrame(subject_rows)
        .sort_values("subject_id", key=lambda series: series.map(lambda item: tuple(natural_key(item))))
        .reset_index(drop=True)
    )


def load_personality_map(path: Path) -> dict[int, np.ndarray]:
    if not path.exists():
        raise FileNotFoundError(f"personality embedding file missing: {path}")
    data = np.load(str(path), allow_pickle=True)
    out: dict[int, np.ndarray] = {}
    for item in data:
        out[int(item["id"])] = np.asarray(item["embedding"], dtype=np.float32)
    return out


def pair_paths(config: TrackConfig, numeric_id: int) -> list[tuple[int, Path, Path]]:
    audio_dir = config.audio_root / str(numeric_id)
    video_dir = config.video_root / str(numeric_id)
    pairs: list[tuple[int, Path, Path]] = []
    if config.age_group == "elder":
        for pair_idx in range(1, PAIR_COUNT + 1):
            audio_path = audio_dir / f"A_{pair_idx}.npy"
            video_path = video_dir / f"V_{pair_idx}.npy"
            if audio_path.is_file() and video_path.is_file():
                pairs.append((pair_idx, audio_path, video_path))
    else:
        for pair_idx in range(1, 4):
            audio_path = audio_dir / f"E{pair_idx}.npy"
            video_path = video_dir / f"event_{pair_idx}.npy"
            if audio_path.is_file() and video_path.is_file():
                pairs.append((pair_idx, audio_path, video_path))
    if not pairs:
        raise FileNotFoundError(f"no official A/V feature pairs found for {config.age_group}_{numeric_id}")
    return pairs


def load_feature_tensor(path: Path, target_t: int) -> tuple[torch.Tensor, int, int]:
    arr = np.asarray(np.load(str(path), allow_pickle=True), dtype=np.float32)
    if arr.ndim == 1:
        arr = arr.reshape(1, -1)
    elif arr.ndim > 2:
        arr = arr.reshape(-1, arr.shape[-1])
    if arr.ndim != 2 or arr.shape[0] <= 0 or arr.shape[1] <= 0:
        raise ValueError(f"expected non-empty 2D feature array, got {arr.shape}: {path}")
    nonfinite = int(arr.size - int(np.isfinite(arr).sum()))
    normalized = _normalize(arr)
    return _resize(normalized, target_t).to(dtype=torch.float32), int(arr.shape[0]), nonfinite


def build_subject_examples(subjects: pd.DataFrame, target_t: int) -> tuple[dict[str, list[SubjectExample]], pd.DataFrame]:
    examples: dict[str, list[SubjectExample]] = {"elder": [], "young": []}
    personality_maps = {age: load_personality_map(config.personality_npy) for age, config in TRACK_CONFIGS.items()}
    metadata_rows: list[dict[str, Any]] = []

    for _, row in subjects.iterrows():
        age_group = str(row["age_group"])
        config = TRACK_CONFIGS[age_group]
        numeric_id = int(row["numeric_id"])
        pairs = pair_paths(config, numeric_id)
        audio_tensors: list[torch.Tensor] = []
        video_tensors: list[torch.Tensor] = []
        pair_mask: list[float] = []
        audio_frames = 0
        video_frames = 0
        nonfinite_count = 0
        for _, audio_path, video_path in pairs[:PAIR_COUNT]:
            audio_tensor, audio_len, audio_nonfinite = load_feature_tensor(audio_path, target_t)
            video_tensor, video_len, video_nonfinite = load_feature_tensor(video_path, target_t)
            audio_tensors.append(audio_tensor)
            video_tensors.append(video_tensor)
            pair_mask.append(1.0)
            audio_frames += audio_len
            video_frames += video_len
            nonfinite_count += audio_nonfinite + video_nonfinite

        audio_dim = int(audio_tensors[0].shape[-1])
        video_dim = int(video_tensors[0].shape[-1])
        while len(audio_tensors) < PAIR_COUNT:
            audio_tensors.append(torch.zeros(target_t, audio_dim, dtype=torch.float32))
            video_tensors.append(torch.zeros(target_t, video_dim, dtype=torch.float32))
            pair_mask.append(0.0)

        personality_map = personality_maps[age_group]
        personality_available = numeric_id in personality_map
        personality = personality_map.get(numeric_id, np.zeros(1024, dtype=np.float32))
        if personality.shape != (1024,):
            raise ValueError(f"personality embedding for {row['subject_id']} has shape {personality.shape}")

        example = SubjectExample(
            subject_id=str(row["subject_id"]),
            numeric_id=numeric_id,
            age_group=age_group,
            severity_label=int(row["severity_label"]),
            binary_label=int(row["binary_label"]),
            phq9_total=float(row["phq9_total"]),
            phq9_normalized=normalize_phq_target(float(row["phq9_total"])),
            audio=torch.stack(audio_tensors),
            video=torch.stack(video_tensors),
            pair_mask=torch.tensor(pair_mask, dtype=torch.float32),
            personality=torch.from_numpy(personality.astype(np.float32)),
            pair_count=len(pairs[:PAIR_COUNT]),
            audio_dim=audio_dim,
            video_dim=video_dim,
            audio_frame_count=audio_frames,
            video_frame_count=video_frames,
            nonfinite_input_count=nonfinite_count,
            personality_available=personality_available,
        )
        examples[age_group].append(example)
        metadata_rows.append(
            {
                "subject_id": example.subject_id,
                "age_group": example.age_group,
                "track": config.track,
                "severity_label": example.severity_label,
                "phq9_total": example.phq9_total,
                "pair_count": example.pair_count,
                "target_t": int(target_t),
                "audio_feature": AUDIO_FEATURE,
                "audio_dim": example.audio_dim,
                "video_feature": VIDEO_FEATURE,
                "video_dim": example.video_dim,
                "audio_frame_count": example.audio_frame_count,
                "video_frame_count": example.video_frame_count,
                "nonfinite_input_count": example.nonfinite_input_count,
                "personality_dim": int(example.personality.numel()),
                "personality_available": bool(example.personality_available),
            }
        )

    for age_group in examples:
        examples[age_group].sort(key=lambda ex: natural_key(ex.subject_id))
    metadata = pd.DataFrame(metadata_rows).sort_values(
        "subject_id", key=lambda series: series.map(lambda item: tuple(natural_key(item)))
    )
    return examples, metadata.reset_index(drop=True)


def setup_seed(seed: int) -> None:
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)
    torch.backends.cudnn.benchmark = False


def collate_batch(batch: list[dict[str, torch.Tensor]]) -> dict[str, torch.Tensor]:
    return {key: torch.stack([item[key] for item in batch]) for key in batch[0]}


def class_weights(labels: list[int], num_classes: int, device: torch.device) -> torch.Tensor:
    counts = np.bincount(np.asarray(labels, dtype=np.int64), minlength=num_classes).astype(np.float32)
    weights = 1.0 / (counts + 1e-6)
    weights = weights / weights.sum() * num_classes
    return torch.tensor(weights, dtype=torch.float32, device=device)


def make_loader(
    examples: list[SubjectExample],
    indices: Iterable[int],
    *,
    batch_size: int,
    shuffle: bool,
    seed: int,
    num_workers: int,
) -> DataLoader:
    generator = torch.Generator()
    generator.manual_seed(seed)
    return DataLoader(
        SubjectTensorDataset(examples, indices),
        batch_size=batch_size,
        shuffle=shuffle,
        generator=generator,
        num_workers=num_workers,
        collate_fn=collate_batch,
    )


def split_inner_train_val(
    labels: np.ndarray,
    *,
    val_ratio: float,
    seed: int,
) -> tuple[np.ndarray, np.ndarray]:
    indices = np.arange(labels.size)
    label_counts = pd.Series(labels).value_counts()
    if labels.size < 2:
        raise ValueError("at least two track train subjects are required")
    if label_counts.min() >= 2:
        splitter = StratifiedShuffleSplit(n_splits=1, train_size=1.0 - val_ratio, random_state=seed)
        train_local, val_local = next(splitter.split(indices, labels))
    else:
        splitter = ShuffleSplit(n_splits=1, train_size=1.0 - val_ratio, random_state=seed)
        train_local, val_local = next(splitter.split(indices))
    return indices[train_local], indices[val_local]


def forward_batch(
    model: torch.nn.Module,
    batch: dict[str, torch.Tensor],
    device: torch.device,
) -> tuple[torch.Tensor, torch.Tensor]:
    outputs = model(
        audio=batch["audio"].to(device),
        video=batch["video"].to(device),
        personality=batch["personality"].to(device),
        pair_mask=batch["pair_mask"].to(device),
    )
    logits, reg_out = outputs
    return logits, reg_out


def evaluate(
    model: torch.nn.Module,
    loader: DataLoader,
    criterion_cls: torch.nn.Module,
    criterion_reg: torch.nn.Module,
    device: torch.device,
) -> dict[str, Any]:
    model.eval()
    y_true: list[int] = []
    y_pred: list[int] = []
    probabilities: list[list[float]] = []
    phq_true: list[float] = []
    phq_pred: list[float] = []
    loss_total = 0.0
    cls_loss_total = 0.0
    reg_loss_total = 0.0
    sample_count = 0
    with torch.no_grad():
        for batch in loader:
            labels = batch["label"].to(device)
            phq9 = batch["phq9"].to(device)
            logits, reg_out = forward_batch(model, batch, device)
            loss_cls = criterion_cls(logits, labels)
            loss_reg = criterion_reg(reg_out, phq9)
            loss = loss_cls + loss_reg
            probs = torch.softmax(logits, dim=-1)
            preds = torch.argmax(probs, dim=-1)
            batch_n = int(labels.shape[0])
            loss_total += float(loss.item()) * batch_n
            cls_loss_total += float(loss_cls.item()) * batch_n
            reg_loss_total += float(loss_reg.item()) * batch_n
            sample_count += batch_n
            y_true.extend(labels.detach().cpu().numpy().astype(int).tolist())
            y_pred.extend(preds.detach().cpu().numpy().astype(int).tolist())
            probabilities.extend(probs.detach().cpu().numpy().astype(float).tolist())
            phq_true.extend(phq9.detach().cpu().numpy().astype(float).tolist())
            phq_pred.extend(reg_out.detach().cpu().numpy().astype(float).tolist())
    if sample_count <= 0:
        raise ValueError("empty evaluation loader")
    metrics = ordinal_metrics(y_true, y_pred, [json.dumps(row) for row in probabilities])
    return {
        "loss": loss_total / sample_count,
        "cls_loss": cls_loss_total / sample_count,
        "reg_loss": reg_loss_total / sample_count,
        "f1": f1_score(y_true, y_pred, average="macro", zero_division=0),
        "acc": accuracy_score(y_true, y_pred),
        "qwk": metrics["QWK"],
        "ordinal_mae": metrics["Ordinal MAE"],
        "brier": metrics["Brier Score"],
        "ece": metrics["ECE"],
        "y_true": y_true,
        "y_pred": y_pred,
        "probabilities": probabilities,
        "phq_true": phq_true,
        "phq_pred": phq_pred,
    }


def train_track_block(
    *,
    config: TrackConfig,
    examples: list[SubjectExample],
    train_indices: list[int],
    heldout_indices: list[int],
    seed: int,
    fold: int,
    device: torch.device,
    num_workers: int,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    if not train_indices or not heldout_indices:
        return [], [], {"skipped": True}
    setup_seed(seed * 1000 + fold * 10 + (1 if config.age_group == "elder" else 2))
    train_labels = np.asarray([examples[idx].severity_label for idx in train_indices], dtype=np.int64)
    inner_train_local, inner_val_local = split_inner_train_val(
        train_labels,
        val_ratio=config.val_ratio,
        seed=seed * 1000 + fold * 17 + (101 if config.age_group == "elder" else 202),
    )
    inner_train_indices = [train_indices[int(idx)] for idx in inner_train_local]
    inner_val_indices = [train_indices[int(idx)] for idx in inner_val_local]

    audio_dim = int(examples[train_indices[0]].audio_dim)
    video_dim = int(examples[train_indices[0]].video_dim)
    model = TorchcatBaseline(
        subtrack=SUBTRACK,
        num_classes=3,
        is_regression=False,
        use_regression_head=True,
        audio_dim=audio_dim,
        video_dim=video_dim,
        hidden_dim=config.hidden_dim,
        dropout=config.dropout,
        encoder_type=ENCODER_TYPE,
    ).to(device)
    weights = class_weights([examples[idx].severity_label for idx in inner_train_indices], 3, device)
    criterion_cls = nn.CrossEntropyLoss(weight=weights)
    criterion_reg = nn.MSELoss()
    optimizer = torch.optim.AdamW(model.parameters(), lr=config.lr, weight_decay=config.weight_decay)
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=max(1, config.epochs))

    train_loader = make_loader(
        examples,
        inner_train_indices,
        batch_size=config.batch_size,
        shuffle=True,
        seed=seed * 1000 + fold,
        num_workers=num_workers,
    )
    val_loader = make_loader(
        examples,
        inner_val_indices,
        batch_size=config.batch_size,
        shuffle=False,
        seed=seed * 1000 + fold + 1,
        num_workers=num_workers,
    )

    best_score = -1.0
    best_epoch = 0
    best_state: dict[str, torch.Tensor] | None = None
    best_metrics: dict[str, Any] | None = None
    epochs_without_improvement = 0
    trace_rows: list[dict[str, Any]] = []
    for epoch in range(1, config.epochs + 1):
        model.train()
        running_loss = 0.0
        running_cls = 0.0
        running_reg = 0.0
        running_count = 0
        for batch in train_loader:
            optimizer.zero_grad(set_to_none=True)
            labels = batch["label"].to(device)
            phq9 = batch["phq9"].to(device)
            logits, reg_out = forward_batch(model, batch, device)
            loss_cls = criterion_cls(logits, labels)
            loss_reg = criterion_reg(reg_out, phq9)
            loss = loss_cls + loss_reg
            loss.backward()
            nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            optimizer.step()
            batch_n = int(labels.shape[0])
            running_loss += float(loss.item()) * batch_n
            running_cls += float(loss_cls.item()) * batch_n
            running_reg += float(loss_reg.item()) * batch_n
            running_count += batch_n
        scheduler.step()

        val_metrics = evaluate(model, val_loader, criterion_cls, criterion_reg, device)
        score = float(val_metrics["f1"])
        improved = score > best_score + config.min_delta
        if improved:
            best_score = score
            best_epoch = epoch
            best_metrics = val_metrics
            best_state = {key: value.detach().cpu().clone() for key, value in model.state_dict().items()}
            epochs_without_improvement = 0
        else:
            epochs_without_improvement += 1
        trace_rows.append(
            {
                "run_id": RUN_ID,
                "seed": int(seed),
                "fold": int(fold),
                "track": config.track,
                "age_group": config.age_group,
                "epoch": int(epoch),
                "train_loss": float(running_loss / max(1, running_count)),
                "train_cls_loss": float(running_cls / max(1, running_count)),
                "train_reg_loss": float(running_reg / max(1, running_count)),
                "inner_val_loss": float(val_metrics["loss"]),
                "inner_val_macro_f1": float(val_metrics["f1"]),
                "inner_val_accuracy": float(val_metrics["acc"]),
                "inner_val_qwk": val_metrics["qwk"],
                "inner_val_ordinal_mae": val_metrics["ordinal_mae"],
                "is_best_so_far": bool(improved),
            }
        )
        if epochs_without_improvement >= config.patience:
            break

    if best_state is None or best_metrics is None:
        raise RuntimeError(f"training produced no best state for seed={seed} fold={fold} track={config.track}")
    model.load_state_dict(best_state)
    model.to(device)

    heldout_loader = make_loader(
        examples,
        heldout_indices,
        batch_size=config.batch_size,
        shuffle=False,
        seed=seed * 1000 + fold + 2,
        num_workers=num_workers,
    )
    heldout_metrics = evaluate(model, heldout_loader, criterion_cls, criterion_reg, device)
    prediction_rows: list[dict[str, Any]] = []
    for local_pos, example_index in enumerate(heldout_indices):
        ex = examples[example_index]
        probs = heldout_metrics["probabilities"][local_pos]
        prediction_rows.append(
            {
                "run_id": RUN_ID,
                "dataset": DATASET_DISPLAY,
                "modality": "AVP",
                "task": "ordinal severity prediction",
                "model": MODEL_NAME,
                "seed": int(seed),
                "fold": int(fold),
                "track": config.track,
                "age_group": config.age_group,
                "task_type": "ordinal_prediction",
                "subject_id": ex.subject_id,
                "split": "train_oof",
                "y_true": int(ex.severity_label),
                "y_pred": int(heldout_metrics["y_pred"][local_pos]),
                "y_prob": json.dumps([float(value) for value in probs], ensure_ascii=True),
                "phq9_total": float(ex.phq9_total),
                "phq9_pred_log1p": float(heldout_metrics["phq_pred"][local_pos]),
                "pair_count": int(ex.pair_count),
                "audio_dim": int(ex.audio_dim),
                "video_dim": int(ex.video_dim),
                "best_epoch": int(best_epoch),
                "inner_val_macro_f1": float(best_metrics["f1"]),
                "outer_train_subjects": int(len(train_indices)),
                "inner_train_subjects": int(len(inner_train_indices)),
                "inner_val_subjects": int(len(inner_val_indices)),
            }
        )

    block_summary = {
        "run_id": RUN_ID,
        "seed": int(seed),
        "fold": int(fold),
        "track": config.track,
        "age_group": config.age_group,
        "train_subjects": int(len(train_indices)),
        "heldout_subjects": int(len(heldout_indices)),
        "inner_train_subjects": int(len(inner_train_indices)),
        "inner_val_subjects": int(len(inner_val_indices)),
        "best_epoch": int(best_epoch),
        "best_inner_val_macro_f1": float(best_metrics["f1"]),
        "best_inner_val_accuracy": float(best_metrics["acc"]),
        "best_inner_val_qwk": best_metrics["qwk"],
        "heldout_macro_f1": float(heldout_metrics["f1"]),
        "heldout_accuracy": float(heldout_metrics["acc"]),
        "heldout_qwk": heldout_metrics["qwk"],
        "audio_dim": int(audio_dim),
        "video_dim": int(video_dim),
        "epochs_configured": int(config.epochs),
        "epochs_run": int(len(trace_rows)),
        "batch_size": int(config.batch_size),
        "lr": float(config.lr),
        "weight_decay": float(config.weight_decay),
        "hidden_dim": int(config.hidden_dim),
        "dropout": float(config.dropout),
        "patience": int(config.patience),
        "val_ratio": float(config.val_ratio),
    }
    return prediction_rows, trace_rows, block_summary


def load_progress(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame()
    frame = pd.read_csv(path)
    if "subject_id" in frame.columns:
        frame["subject_id"] = frame["subject_id"].astype(str)
    return frame


def save_frame(path: Path, rows: list[dict[str, Any]] | pd.DataFrame, dedup_columns: list[str] | None = None) -> pd.DataFrame:
    frame = rows.copy() if isinstance(rows, pd.DataFrame) else pd.DataFrame(rows)
    if not frame.empty and dedup_columns:
        frame = frame.drop_duplicates(dedup_columns, keep="last")
    path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(path, index=False)
    return frame


def block_is_complete(progress: pd.DataFrame, seed: int, fold: int, track: str, expected_subjects: int) -> bool:
    if progress.empty:
        return False
    required = {"seed", "fold", "track", "subject_id", "y_prob"}
    if required - set(progress.columns):
        return False
    rows = progress[
        (progress["seed"].astype(int) == int(seed))
        & (progress["fold"].astype(int) == int(fold))
        & (progress["track"].astype(str) == track)
    ]
    return len(rows.drop_duplicates("subject_id")) == expected_subjects and rows["y_prob"].notna().all()


def expected_blocks(
    subjects: pd.DataFrame,
    seeds: list[int],
    max_folds: int | None,
) -> list[dict[str, Any]]:
    y = subjects["severity_label"].to_numpy(dtype=np.int64)
    blocks: list[dict[str, Any]] = []
    for seed in seeds:
        folds = StratifiedKFold(n_splits=5, shuffle=True, random_state=seed)
        for fold, (train_idx, heldout_idx) in enumerate(folds.split(subjects, y), start=1):
            if max_folds is not None and fold > max_folds:
                continue
            train = subjects.iloc[train_idx]
            heldout = subjects.iloc[heldout_idx]
            for age_group, config in TRACK_CONFIGS.items():
                train_ids = train.loc[train["age_group"].eq(age_group), "subject_id"].astype(str).tolist()
                heldout_ids = heldout.loc[heldout["age_group"].eq(age_group), "subject_id"].astype(str).tolist()
                if heldout_ids:
                    blocks.append(
                        {
                            "seed": int(seed),
                            "fold": int(fold),
                            "track": config.track,
                            "age_group": age_group,
                            "train_ids": train_ids,
                            "heldout_ids": heldout_ids,
                        }
                    )
    return blocks


def official_repo_commit() -> str:
    head = OFFICIAL_REPO / ".git" / "HEAD"
    if not head.exists():
        return "unknown"
    text = head.read_text(encoding="utf-8").strip()
    if text.startswith("ref:"):
        ref_path = OFFICIAL_REPO / ".git" / text.split(" ", 1)[1]
        if ref_path.exists():
            return ref_path.read_text(encoding="utf-8").strip()
    return text


def canonical_contract_met(
    *,
    seeds: list[int],
    max_folds: int | None,
    bootstrap_resamples: int,
    smoke: bool,
    completed_blocks: int,
    expected_block_count: int,
    args: argparse.Namespace,
) -> bool:
    return (
        not smoke
        and seeds == SEEDS
        and max_folds is None
        and bootstrap_resamples >= 1000
        and completed_blocks == expected_block_count
        and args.epochs_elder == TRACK_CONFIGS["elder"].epochs
        and args.epochs_young == TRACK_CONFIGS["young"].epochs
    )


def write_report(out_dir: Path, summary: dict[str, Any], canonical: bool) -> None:
    metric_file = "phase2_metric_summary.csv" if canonical else "mpdd_public_official_partial_metric_summary.csv"
    lines = [
        "# MPDD Official Public Baseline Phase 2 Wrapper",
        "",
        f"Generated: `{summary['generated_at']}`",
        "",
        "## Protocol",
        "",
        "- Public source: official `hacilab/MPDD-AVG-2026` baseline.",
        "- Imported model: `TorchcatBaseline` with `A-V+P` and `bilstm_mean` temporal encoders.",
        "- Local feature adaptation: official-supported `wav2vec2` audio features and `resnet` video features, because these are the available local MPDD feature types.",
        "- Track handling: Elder/Track1 and Young/Track2 are trained separately because their wav2vec2 dimensions differ, then predictions are merged for the unified MPDD matrix row.",
        "- Official README/code split contract: `split_labels_train.csv` is a trainval pool; validation is carved from that pool with default `val_ratio=0.1`, and official test labels are evaluated only after checkpoint selection.",
        "- Evaluation: five repeated stratified 5-fold subject-level OOF splits over the 175 labeled train subjects.",
        "- Phase 2 adaptation: the official internal-val selection is applied inside each outer train fold, so the outer heldout fold remains untouched until evaluation.",
        "- Inner model selection: train-fold-only deterministic stratified split, using Macro-F1 as in the official classification baseline.",
        "- Official split reproducibility caveat: local `train_val_split.py` does not pass `random_state`, and local `train.py` calls `setup_seed` after split creation; this wrapper fixes the inner split with `random_state` for comparable reruns.",
        "- Local label-column caveat: local Young `split_labels_train.csv` uses `phq9_score`, while the official code expects `PHQ-9`; this wrapper reads PHQ-9 targets through the audited manifest.",
        "- The official PHQ-9 regression head is trained jointly, but the matrix row reports ordinal severity metrics.",
        "- Unlabeled MPDD test rows are ignored; no test labels are used for tuning.",
        "- No model checkpoints, raw text, raw audio, raw video, source paths, or frame-level features are written.",
        "",
        "## Audit",
        "",
        f"- Canonical matrix output: `{canonical}`",
        f"- Metric file: `{metric_file}`",
        f"- Subject count: `{summary['subject_count']}`",
        f"- Track counts: `{summary['track_subject_counts']}`",
        f"- Severity counts: `{summary['severity_counts']}`",
        f"- Expected blocks: `{summary['expected_block_count']}`",
        f"- Completed blocks: `{summary['completed_block_count']}`",
        f"- Prediction rows: `{summary['prediction_rows']}`",
        f"- Seeds: `{summary['seeds']}`",
        f"- Bootstrap resamples: `{summary['bootstrap_resamples']}`",
        f"- Official source commit: `{summary['official_source_commit']}`",
    ]
    (out_dir / "mpdd_public_official_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest-path", type=Path, default=MANIFEST_PATH)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--seeds", default=",".join(str(seed) for seed in SEEDS))
    parser.add_argument("--max-folds", type=int, default=None)
    parser.add_argument("--bootstrap-resamples", type=int, default=1000)
    parser.add_argument("--device", default="cuda")
    parser.add_argument("--num-workers", type=int, default=0)
    parser.add_argument("--target-t", type=int, default=TARGET_T)
    parser.add_argument("--epochs-elder", type=int, default=TRACK_CONFIGS["elder"].epochs)
    parser.add_argument("--epochs-young", type=int, default=TRACK_CONFIGS["young"].epochs)
    parser.add_argument("--smoke", action="store_true")
    parser.add_argument("--force", action="store_true", help="Ignore existing progress files and rerun all blocks.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    args.out_dir.mkdir(parents=True, exist_ok=True)
    seeds = parse_seed_list(args.seeds)
    if args.max_folds is not None and not 1 <= args.max_folds <= 5:
        raise ValueError("--max-folds must be between 1 and 5")
    if args.target_t <= 0:
        raise ValueError("--target-t must be positive")

    track_configs = copy.deepcopy(TRACK_CONFIGS)
    track_configs["elder"] = copy.copy(track_configs["elder"])
    track_configs["young"] = copy.copy(track_configs["young"])
    object.__setattr__(track_configs["elder"], "epochs", int(args.epochs_elder))
    object.__setattr__(track_configs["young"], "epochs", int(args.epochs_young))
    globals()["TRACK_CONFIGS"] = track_configs

    device = torch.device(args.device if args.device != "cuda" or torch.cuda.is_available() else "cpu")
    print(f"Loading MPDD official tensors on CPU; training blocks will use {device}", flush=True)
    subjects = labeled_subject_rows(args.manifest_path)
    examples_by_age, feature_metadata = build_subject_examples(subjects, args.target_t)
    feature_metadata.to_csv(args.out_dir / "mpdd_public_official_feature_metadata.csv", index=False)

    subject_id_to_index = {
        age: {example.subject_id: idx for idx, example in enumerate(examples)}
        for age, examples in examples_by_age.items()
    }
    blocks = expected_blocks(subjects, seeds, args.max_folds)
    predictions_progress_path = args.out_dir / "mpdd_public_official_predictions_progress.csv"
    trace_progress_path = args.out_dir / "mpdd_public_official_training_trace_progress.csv"
    block_progress_path = args.out_dir / "mpdd_public_official_block_summaries_progress.csv"

    prediction_progress = pd.DataFrame() if args.force else load_progress(predictions_progress_path)
    trace_progress = pd.DataFrame() if args.force else load_progress(trace_progress_path)
    block_progress = pd.DataFrame() if args.force else load_progress(block_progress_path)

    for block_idx, block in enumerate(blocks, start=1):
        config = track_configs[str(block["age_group"])]
        expected_heldout = len(block["heldout_ids"])
        if block_is_complete(prediction_progress, block["seed"], block["fold"], config.track, expected_heldout):
            print(
                f"[skip] {block_idx}/{len(blocks)} seed={block['seed']} fold={block['fold']} {config.track} already complete",
                flush=True,
            )
            continue
        train_indices = [subject_id_to_index[config.age_group][subject_id] for subject_id in block["train_ids"]]
        heldout_indices = [subject_id_to_index[config.age_group][subject_id] for subject_id in block["heldout_ids"]]
        print(
            f"[train] {block_idx}/{len(blocks)} seed={block['seed']} fold={block['fold']} "
            f"{config.track}/{config.age_group} train={len(train_indices)} heldout={len(heldout_indices)}",
            flush=True,
        )
        pred_rows, trace_rows, block_summary = train_track_block(
            config=config,
            examples=examples_by_age[config.age_group],
            train_indices=train_indices,
            heldout_indices=heldout_indices,
            seed=int(block["seed"]),
            fold=int(block["fold"]),
            device=device,
            num_workers=args.num_workers,
        )
        prediction_progress = save_frame(
            predictions_progress_path,
            pd.concat([prediction_progress, pd.DataFrame(pred_rows)], ignore_index=True),
            ["seed", "fold", "track", "subject_id"],
        )
        trace_progress = save_frame(
            trace_progress_path,
            pd.concat([trace_progress, pd.DataFrame(trace_rows)], ignore_index=True),
            ["seed", "fold", "track", "epoch"],
        )
        block_progress = save_frame(
            block_progress_path,
            pd.concat([block_progress, pd.DataFrame([block_summary])], ignore_index=True),
            ["seed", "fold", "track"],
        )

    completed_block_count = sum(
        block_is_complete(
            prediction_progress,
            int(block["seed"]),
            int(block["fold"]),
            track_configs[str(block["age_group"])].track,
            len(block["heldout_ids"]),
        )
        for block in blocks
    )
    canonical = canonical_contract_met(
        seeds=seeds,
        max_folds=args.max_folds,
        bootstrap_resamples=args.bootstrap_resamples,
        smoke=bool(args.smoke),
        completed_blocks=completed_block_count,
        expected_block_count=len(blocks),
        args=args,
    )
    predictions = prediction_progress.copy()
    expected_subject_seed_rows = len(subjects) * len(seeds)
    if not predictions.empty:
        predictions = predictions[
            predictions["seed"].astype(int).isin(seeds)
            & predictions["subject_id"].astype(str).isin(set(subjects["subject_id"].astype(str)))
        ].copy()
        predictions = predictions.sort_values(
            ["seed", "fold", "track", "subject_id"],
            key=lambda series: series.map(lambda item: tuple(natural_key(item))) if series.name == "subject_id" else series,
        ).reset_index(drop=True)

    if canonical and len(predictions) != expected_subject_seed_rows:
        raise RuntimeError(
            f"canonical contract expected {expected_subject_seed_rows} predictions, found {len(predictions)}"
        )
    metrics_by_seed, metric_summary = metric_records(
        predictions,
        bootstrap_resamples=int(args.bootstrap_resamples),
        seed=20260730,
    )

    if canonical:
        predictions.to_csv(args.out_dir / "mpdd_public_official_predictions.csv", index=False)
        trace_progress.to_csv(args.out_dir / "mpdd_public_official_training_trace.csv", index=False)
        block_progress.to_csv(args.out_dir / "mpdd_public_official_block_summaries.csv", index=False)
        metrics_by_seed.to_csv(args.out_dir / "phase2_metrics_by_seed.csv", index=False)
        metric_summary.to_csv(args.out_dir / "phase2_metric_summary.csv", index=False)
    else:
        predictions.to_csv(args.out_dir / "mpdd_public_official_partial_predictions.csv", index=False)
        trace_progress.to_csv(args.out_dir / "mpdd_public_official_partial_training_trace.csv", index=False)
        block_progress.to_csv(args.out_dir / "mpdd_public_official_partial_block_summaries.csv", index=False)
        metrics_by_seed.to_csv(args.out_dir / "mpdd_public_official_partial_metrics_by_seed.csv", index=False)
        metric_summary.to_csv(args.out_dir / "mpdd_public_official_partial_metric_summary.csv", index=False)

    run_summary = {
        "generated_at": utc_now(),
        "run_id": RUN_ID,
        "canonical_matrix_output": bool(canonical),
        "official_source_url": "https://github.com/hacilab/MPDD-AVG-2026",
        "official_source_commit": official_repo_commit(),
        "official_model_class": "TorchcatBaseline",
        "official_subtrack": SUBTRACK,
        "official_encoder_type": ENCODER_TYPE,
        "official_readme_split_contract": {
            "source_url": OFFICIAL_README_URL,
            "trainval_pool": "split_labels_train.csv",
            "internal_val_from_trainval": True,
            "default_val_ratio": 0.1,
            "test_evaluation": "test.py evaluates split_labels_test.csv after training/checkpoint selection",
        },
        "official_code_split_audit": {
            "train_val_function": "train_val_split.py:create_train_val_split",
            "uses_stratified_shuffle_when_label_counts_allow": True,
            "random_state_passed_to_sklearn_splitter": False,
            "train_py_calls_setup_seed_after_create_train_val_split": True,
            "official_expected_phq9_column": "PHQ-9",
            "local_young_train_csv_phq9_column": "phq9_score",
        },
        "phase2_split_adaptation": {
            "outer_evaluation": "five repeated stratified 5-fold subject-level OOF over locally labeled train subjects",
            "inner_model_selection": "deterministic train-fold-only stratified split",
            "inner_val_ratio": 0.1,
            "outer_heldout_used_for_model_selection": False,
            "test_labels_used": False,
        },
        "local_feature_adaptation": {
            "audio_feature": AUDIO_FEATURE,
            "video_feature": VIDEO_FEATURE,
            "reason": "local MPDD upload exposes official-supported wav2vec2 audio and resnet video features",
        },
        "manifest_path": str(args.manifest_path),
        "seeds": seeds,
        "max_folds": args.max_folds,
        "bootstrap_resamples": int(args.bootstrap_resamples),
        "subject_count": int(len(subjects)),
        "track_subject_counts": {
            str(k): int(v) for k, v in subjects["age_group"].value_counts().sort_index().items()
        },
        "severity_counts": {
            str(k): int(v) for k, v in subjects["severity_label"].astype(int).value_counts().sort_index().items()
        },
        "expected_block_count": int(len(blocks)),
        "completed_block_count": int(completed_block_count),
        "expected_prediction_rows_for_selected_seeds": int(expected_subject_seed_rows),
        "prediction_rows": int(len(predictions)),
        "feature_metadata_rows": int(len(feature_metadata)),
        "track_configs": {
            age: {
                "track": config.track,
                "epochs": int(config.epochs),
                "batch_size": int(config.batch_size),
                "lr": float(config.lr),
                "weight_decay": float(config.weight_decay),
                "hidden_dim": int(config.hidden_dim),
                "dropout": float(config.dropout),
                "patience": int(config.patience),
                "val_ratio": float(config.val_ratio),
            }
            for age, config in track_configs.items()
        },
        "no_test_split_used": True,
        "validation_label_tuning_used": False,
        "outer_heldout_label_tuning_used": False,
        "checkpoints_written": False,
        "raw_text_written": False,
        "raw_audio_written": False,
        "raw_video_written": False,
        "raw_personality_text_written": False,
        "source_paths_written_in_predictions": False,
    }
    (args.out_dir / "mpdd_public_official_run_summary.json").write_text(
        json.dumps(run_summary, indent=2, ensure_ascii=True, sort_keys=True),
        encoding="utf-8",
    )
    write_report(args.out_dir, run_summary, canonical)
    if canonical:
        print(f"Wrote {args.out_dir / 'phase2_metric_summary.csv'}", flush=True)
    else:
        print(f"Wrote {args.out_dir / 'mpdd_public_official_partial_metric_summary.csv'}", flush=True)


if __name__ == "__main__":
    main()
