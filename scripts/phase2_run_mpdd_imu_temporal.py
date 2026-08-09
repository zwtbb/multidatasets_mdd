#!/usr/bin/env python3
"""Run Phase 2 MPDD IMU temporal encoder baseline.

This is a deliberately small gait baseline: a shallow Conv1d temporal encoder
plus MLP classifier for ordinal severity. It uses only manifest-resolved labeled
train subjects, writes no checkpoints, and ignores unlabeled test rows.
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
from sklearn.model_selection import StratifiedKFold
from torch import nn
from torch.utils.data import DataLoader, TensorDataset

from phase2_metrics import metric_records


ROOT = Path("/root/autodl-tmp")
MANIFEST_PATH = ROOT / "datasets" / "manifests" / "mpdd_avg_2026_subjects.csv"
DEFAULT_OUT_DIR = ROOT / "analysis" / "phase2_baselines" / "mpdd_imu_temporal"
SEEDS = [0, 1, 2, 3, 4]
DATASET_DISPLAY = "MPDD-AVG-2026"
MAX_CHANNELS = 12
TARGET_LENGTH = 512
EPOCHS = 35
BATCH_SIZE = 24


@dataclass(frozen=True)
class BaselineSpec:
    run_id: str = "mpdd_gait_severity_imu_temporal_mlp"
    modality: str = "Gait"
    task: str = "ordinal severity prediction"
    task_type: str = "ordinal_prediction"
    target: str = "severity_label"
    model: str = "IMU temporal encoder + MLP"


SPEC = BaselineSpec()


class TemporalEncoderMLP(nn.Module):
    def __init__(self, input_channels: int, classes: int) -> None:
        super().__init__()
        self.encoder = nn.Sequential(
            nn.Conv1d(input_channels, 32, kernel_size=7, stride=2, padding=3),
            nn.ReLU(),
            nn.BatchNorm1d(32),
            nn.Conv1d(32, 48, kernel_size=5, stride=2, padding=2),
            nn.ReLU(),
            nn.BatchNorm1d(48),
            nn.AdaptiveAvgPool1d(1),
        )
        self.head = nn.Sequential(
            nn.Flatten(),
            nn.Dropout(0.15),
            nn.Linear(48, 32),
            nn.ReLU(),
            nn.Linear(32, classes),
        )

    def forward(self, inputs: torch.Tensor) -> torch.Tensor:
        return self.head(self.encoder(inputs))


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def set_seed(seed: int) -> None:
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)
    torch.backends.cudnn.benchmark = False
    torch.backends.cudnn.deterministic = True


def load_sequence(path_value: Any) -> np.ndarray:
    path = Path(str(path_value))
    if not path.exists():
        raise FileNotFoundError(f"manifest gait path missing: {path}")
    arr = np.load(path, allow_pickle=False)
    if not np.issubdtype(arr.dtype, np.number):
        raise ValueError(f"non-numeric gait array: {path}")
    if arr.ndim == 1:
        arr = arr.reshape(-1, 1)
    if arr.ndim != 2:
        raise ValueError(f"expected 2D gait array, got shape {arr.shape}: {path}")
    arr = np.asarray(arr, dtype=np.float32)
    arr = np.nan_to_num(arr, nan=0.0, posinf=0.0, neginf=0.0)
    if arr.shape[1] > MAX_CHANNELS:
        arr = arr[:, :MAX_CHANNELS]
    elif arr.shape[1] < MAX_CHANNELS:
        arr = np.pad(arr, ((0, 0), (0, MAX_CHANNELS - arr.shape[1])), mode="constant")
    return arr


def resample_sequence(arr: np.ndarray, target_length: int = TARGET_LENGTH) -> np.ndarray:
    if arr.shape[0] == target_length:
        sampled = arr
    else:
        old_x = np.linspace(0.0, 1.0, arr.shape[0], dtype=np.float32)
        new_x = np.linspace(0.0, 1.0, target_length, dtype=np.float32)
        sampled = np.empty((target_length, arr.shape[1]), dtype=np.float32)
        for channel in range(arr.shape[1]):
            sampled[:, channel] = np.interp(new_x, old_x, arr[:, channel]).astype(np.float32)
    return sampled.T.astype(np.float32)


def build_subject_table(manifest_path: Path) -> tuple[pd.DataFrame, np.ndarray]:
    manifest = pd.read_csv(manifest_path)
    required = {
        "subject_id",
        "gait_path",
        "binary_label",
        "severity_label",
        "phq9_total",
        "age",
        "official_split",
    }
    missing = required - set(manifest.columns)
    if missing:
        raise ValueError(f"MPDD manifest missing columns: {', '.join(sorted(missing))}")

    subject_rows = manifest.drop_duplicates("subject_id").copy()
    usable = subject_rows[
        subject_rows["gait_path"].notna()
        & subject_rows["severity_label"].notna()
        & subject_rows["official_split"].eq("train")
    ].copy()
    if usable.empty:
        raise ValueError("no labeled train subjects with gait paths")

    arrays: list[np.ndarray] = []
    row_meta: list[dict[str, Any]] = []
    for _, row in usable.sort_values("subject_id").iterrows():
        arr = load_sequence(row["gait_path"])
        arrays.append(resample_sequence(arr))
        row_meta.append(
            {
                "subject_id": str(row["subject_id"]),
                "split": "train_oof",
                "severity_label": int(row["severity_label"]),
                "binary_label": int(row["binary_label"]),
                "phq9_total": float(row["phq9_total"]),
                "age_group": str(row["age"]),
                "sequence_length": int(arr.shape[0]),
                "channel_count": int(arr.shape[1]),
            }
        )
    table = pd.DataFrame(row_meta)
    tensors = np.stack(arrays).astype(np.float32)
    return table, tensors


def normalize_by_train(features: np.ndarray, train_idx: np.ndarray) -> np.ndarray:
    train_values = features[train_idx]
    mean = np.mean(train_values, axis=(0, 2), keepdims=True)
    std = np.std(train_values, axis=(0, 2), keepdims=True)
    std = np.where(std < 1e-6, 1.0, std)
    return ((features - mean) / std).astype(np.float32)


def class_weights(labels: np.ndarray, classes: int, device: torch.device) -> torch.Tensor:
    counts = np.bincount(labels.astype(np.int64), minlength=classes).astype(np.float32)
    counts = np.maximum(counts, 1.0)
    weights = counts.sum() / (classes * counts)
    return torch.tensor(weights, dtype=torch.float32, device=device)


def train_fold(
    features: np.ndarray,
    labels: np.ndarray,
    train_idx: np.ndarray,
    heldout_idx: np.ndarray,
    seed: int,
    device: torch.device,
) -> tuple[np.ndarray, np.ndarray]:
    set_seed(seed)
    normalized = normalize_by_train(features, train_idx)
    train_x = torch.tensor(normalized[train_idx], dtype=torch.float32)
    train_y = torch.tensor(labels[train_idx], dtype=torch.long)
    heldout_x = torch.tensor(normalized[heldout_idx], dtype=torch.float32, device=device)
    dataset = TensorDataset(train_x, train_y)
    generator = torch.Generator()
    generator.manual_seed(seed)
    loader = DataLoader(dataset, batch_size=BATCH_SIZE, shuffle=True, generator=generator)

    model = TemporalEncoderMLP(MAX_CHANNELS, int(labels.max()) + 1).to(device)
    optimizer = torch.optim.AdamW(model.parameters(), lr=1e-3, weight_decay=1e-3)
    loss_fn = nn.CrossEntropyLoss(weight=class_weights(labels[train_idx], int(labels.max()) + 1, device))
    model.train()
    for _ in range(EPOCHS):
        for batch_x, batch_y in loader:
            batch_x = batch_x.to(device)
            batch_y = batch_y.to(device)
            optimizer.zero_grad(set_to_none=True)
            loss = loss_fn(model(batch_x), batch_y)
            loss.backward()
            optimizer.step()

    model.eval()
    with torch.no_grad():
        logits = model(heldout_x)
        probabilities = torch.softmax(logits, dim=1).detach().cpu().numpy()
    return probabilities.argmax(axis=1).astype(int), probabilities.astype(float)


def prediction_meta(seed: int, fold: int, row: pd.Series) -> dict[str, Any]:
    return {
        "run_id": SPEC.run_id,
        "dataset": DATASET_DISPLAY,
        "modality": SPEC.modality,
        "task": SPEC.task,
        "model": SPEC.model,
        "seed": int(seed),
        "fold": int(fold),
        "task_type": SPEC.task_type,
        "subject_id": row["subject_id"],
        "split": row["split"],
        "age_group": row["age_group"],
    }


def run_seed(table: pd.DataFrame, features: np.ndarray, seed: int, device: torch.device) -> list[dict[str, Any]]:
    labels = table["severity_label"].to_numpy(dtype=np.int64)
    folds = StratifiedKFold(n_splits=5, shuffle=True, random_state=seed)
    predictions: list[dict[str, Any]] = []
    for fold, (train_idx, heldout_idx) in enumerate(folds.split(features, labels), start=1):
        pred, probabilities = train_fold(features, labels, train_idx, heldout_idx, seed + fold, device)
        heldout = table.iloc[heldout_idx].reset_index(drop=True)
        for idx, row in heldout.iterrows():
            predictions.append(
                {
                    **prediction_meta(seed, fold, row),
                    "y_true": int(row["severity_label"]),
                    "y_pred": int(pred[idx]),
                    "y_prob": json.dumps([float(x) for x in probabilities[idx]], ensure_ascii=True),
                }
            )
    return predictions


def write_report(out_dir: Path, summary: dict[str, Any]) -> None:
    lines = [
        "# MPDD IMU Temporal Phase 2 Baseline",
        "",
        f"Generated: `{summary['generated_at']}`",
        "",
        "## Protocol",
        "",
        "- Input interface: `datasets/manifests/mpdd_avg_2026_subjects.csv`.",
        "- Unit of prediction: one row per subject.",
        "- Model: shallow Conv1d temporal encoder plus MLP ordinal classifier.",
        "- Evaluation: five repeated stratified 5-fold subject-level out-of-fold runs.",
        "- Hyperparameters are fixed before evaluation; no test split is used.",
        "- Unlabeled MPDD test rows are ignored.",
        "- No checkpoints are written.",
        "- Raw IMU arrays are read for training but are not written to outputs.",
        "",
        "## Audit",
        "",
        f"- Labeled gait subjects: `{summary['subjects']}`",
        f"- Elder subjects: `{summary['age_group_counts'].get('elder', 0)}`",
        f"- Young subjects: `{summary['age_group_counts'].get('young', 0)}`",
        f"- Severity counts: `{summary['severity_counts']}`",
        f"- Seeds: `{summary['seeds']}`",
        f"- Bootstrap resamples: `{summary['bootstrap_resamples']}`",
        f"- Prediction rows: `{summary['prediction_rows']}`",
        f"- Device: `{summary['device']}`",
        "",
        "## Output Files",
        "",
        "- `mpdd_imu_temporal_predictions.csv`",
        "- `phase2_metrics_by_seed.csv`",
        "- `phase2_metric_summary.csv`",
        "- `mpdd_imu_temporal_run_summary.json`",
    ]
    (out_dir / "mpdd_imu_temporal_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, default=MANIFEST_PATH)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--bootstrap-resamples", type=int, default=1000)
    parser.add_argument("--device", default="cuda" if torch.cuda.is_available() else "cpu")
    args = parser.parse_args()

    device = torch.device(args.device if args.device == "cpu" or torch.cuda.is_available() else "cpu")
    table, features = build_subject_table(args.manifest)
    all_predictions: list[dict[str, Any]] = []
    for seed in SEEDS:
        all_predictions.extend(run_seed(table, features, seed, device))

    args.out_dir.mkdir(parents=True, exist_ok=True)
    predictions_frame = pd.DataFrame(all_predictions)
    predictions_path = args.out_dir / "mpdd_imu_temporal_predictions.csv"
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
        "subjects": int(len(table)),
        "age_group_counts": {str(k): int(v) for k, v in table["age_group"].value_counts().to_dict().items()},
        "severity_counts": {str(k): int(v) for k, v in table["severity_label"].value_counts().sort_index().to_dict().items()},
        "input_shape": [int(x) for x in features.shape[1:]],
        "epochs": EPOCHS,
        "batch_size": BATCH_SIZE,
        "seeds": SEEDS,
        "seed_count": len(SEEDS),
        "bootstrap_resamples": int(args.bootstrap_resamples),
        "prediction_rows": int(len(predictions_frame)),
        "runs": [SPEC.run_id],
        "split_policy": "labeled_train_internal_subject_level_stratified_5fold_oof",
        "no_test_split_used": True,
        "raw_imu_written": False,
        "checkpoints_written": False,
        "device": str(device),
    }
    (args.out_dir / "mpdd_imu_temporal_run_summary.json").write_text(
        json.dumps(run_summary, indent=2, ensure_ascii=True, sort_keys=True),
        encoding="utf-8",
    )
    write_report(args.out_dir, run_summary)
    print(f"Wrote {predictions_path}")
    print(f"Wrote {args.out_dir / 'phase2_metric_summary.csv'}")


if __name__ == "__main__":
    main()
