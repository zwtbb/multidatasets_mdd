#!/usr/bin/env python3
"""Run the Phase 2 E-DAIC AVEC 2019 DDS public baseline adaptation.

The official AVEC 2019 DDS baseline trains one GRU regressor per acoustic or
visual feature set, selects the best epoch by development CCC, and fuses
feature-set predictions by unweighted averaging. This runner preserves that
model, preprocessing, and validation-selection contract while adapting the
feature loading layer to the local E-DAIC subject-folder layout.

Prediction artifacts intentionally contain no raw transcript text, raw
audio/video, source paths, prompts, or checkpoints.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import random
import subprocess
import warnings
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def normalize_thread_env() -> None:
    value = str(os.environ.get("OMP_NUM_THREADS", "")).strip()
    if not value.isdigit() or int(value) <= 0:
        os.environ["OMP_NUM_THREADS"] = "4"
    os.environ.setdefault("OPENBLAS_NUM_THREADS", "4")
    os.environ.setdefault("MKL_NUM_THREADS", "4")


normalize_thread_env()

import numpy as np
import pandas as pd
import torch
import torch.nn as nn
from scipy.io import loadmat
from scipy.signal import savgol_filter
from sklearn.preprocessing import StandardScaler
from torch.nn.utils.rnn import pack_padded_sequence, pad_packed_sequence
from torch.utils.data import DataLoader, Dataset

from phase2_metrics import metric_records


ROOT = Path("/root/autodl-tmp")
MANIFEST_PATH = ROOT / "datasets" / "manifests" / "edaic_subjects.csv"
OFFICIAL_REPO = ROOT / "cache" / "official_baselines" / "AVEC2019"
DEFAULT_OUT_DIR = ROOT / "analysis" / "phase2_baselines" / "edaic_public_avec_official"
SEEDS = [0, 1, 2, 3, 4]
OFFICIAL_EPOCHS = 30
OFFICIAL_BATCH_SIZE = 15
OFFICIAL_HIDDEN_DIM = 64
OFFICIAL_DROPOUT = 0.2
CUDA_CUDNN_SEQUENCE_LIMIT = 20000
LONG_SEQUENCE_MODES = ("native_packed", "padded", "auto")
PROGRESS_FEATURE_PREDICTIONS = "edaic_public_avec_feature_predictions_progress.csv"
PROGRESS_SEED_SUMMARIES = "edaic_public_avec_feature_seed_summaries_progress.csv"
PROGRESS_TRAINING_TRACE = "edaic_public_avec_training_trace_progress.csv"


@dataclass(frozen=True)
class FeatureSpec:
    feature_type: str
    local_suffix: str
    official_preprocess: str
    modality: str
    feature_dim: int
    max_sequence_length: int
    learning_rate: float


FEATURE_SPECS = [
    FeatureSpec("eGeMAPS", "OpenSMILE2.3.0_egemaps.csv", "subject_standardize_csv_semicolon", "speech", 23, 120000, 0.0005),
    FeatureSpec("mfcc", "OpenSMILE2.3.0_mfcc.csv", "subject_standardize_csv_semicolon", "speech", 39, 120000, 0.0001),
    FeatureSpec("AUpose", "OpenFace2.1.0_Pose_gaze_AUs.csv", "subject_standardize_openface", "vision", 49, 120000, 0.0005),
    FeatureSpec("BoW_AUpose", "BoVW_openFace_2.1.0_Pose_Gaze_AUs.csv", "bow_local_csv", "vision", 100, 120000, 0.0001),
    FeatureSpec("BoW_eGeMAPS", "BoAW_openSMILE_2.3.0_eGeMAPS.csv", "bow_local_csv", "speech", 100, 120000, 0.0005),
    FeatureSpec("BoW_mfcc", "BoAW_openSMILE_2.3.0_MFCC.csv", "bow_local_csv", "speech", 100, 120000, 0.001),
    FeatureSpec("DS_VGG", "vgg16.csv", "audio_deep_smooth_quarter", "speech", 4096, 9000, 0.0001),
    FeatureSpec("DS_densenet", "densenet201.csv", "audio_deep_half", "speech", 1920, 18000, 0.0005),
    FeatureSpec("ResNet", "CNN_ResNet.mat", "mat_half", "vision", 2048, 18000, 0.0001),
    FeatureSpec("VGG", "CNN_VGG.mat", "mat_smooth_quarter", "vision", 4096, 9000, 0.001),
]
FEATURE_BY_NAME = {spec.feature_type: spec for spec in FEATURE_SPECS}
KNOWN_OFFICIAL_MISSING_FEATURE_SUBJECTS = {
    ("VGG", "657"): "official AVEC/E-DAIC feature release does not include 657_CNN_VGG.mat",
}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def official_commit(repo: Path) -> str | None:
    if not (repo / ".git").exists():
        return None
    try:
        out = subprocess.check_output(["git", "-C", str(repo), "rev-parse", "HEAD"], text=True)
    except (OSError, subprocess.CalledProcessError):
        return None
    return out.strip()


def set_seed(seed: int) -> None:
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    torch.cuda.manual_seed_all(seed)
    torch.backends.cudnn.benchmark = False
    torch.backends.cudnn.deterministic = True


def read_manifest(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"E-DAIC manifest missing: {path}")
    manifest = pd.read_csv(path)
    required = {"subject_id", "official_split", "phq8_total", "file_valid", "text_path", "audio_path", "video_path"}
    missing = required - set(manifest.columns)
    if missing:
        raise ValueError(f"E-DAIC manifest missing columns: {', '.join(sorted(missing))}")
    usable = manifest[
        manifest["file_valid"].fillna(False).astype(bool)
        & manifest["phq8_total"].notna()
        & manifest["text_path"].notna()
        & manifest["audio_path"].notna()
        & manifest["video_path"].notna()
        & manifest["official_split"].isin(["train", "dev"])
    ].copy()
    if usable.empty:
        raise ValueError("no usable E-DAIC train/dev rows")
    if usable["subject_id"].duplicated().any():
        dupes = sorted(usable.loc[usable["subject_id"].duplicated(), "subject_id"].astype(str).unique())
        raise ValueError(f"E-DAIC manifest should have one row per subject; duplicates: {dupes[:10]}")
    usable["subject_id"] = usable["subject_id"].astype(str)
    usable["phq8_total"] = usable["phq8_total"].astype(float)
    return usable.sort_values("subject_id").reset_index(drop=True)


def subject_feature_path(row: pd.Series, spec: FeatureSpec) -> Path:
    subject_id = str(row["subject_id"])
    return Path(str(row["video_path"])).parent / f"{subject_id}_{spec.local_suffix}"


def known_official_missing_feature(spec: FeatureSpec, subject_id: str) -> str | None:
    return KNOWN_OFFICIAL_MISSING_FEATURE_SUBJECTS.get((spec.feature_type, str(subject_id)))


def feature_available_manifest(manifest: pd.DataFrame, spec: FeatureSpec) -> pd.DataFrame:
    keep = [
        known_official_missing_feature(spec, str(row["subject_id"])) is None
        for _, row in manifest.iterrows()
    ]
    return manifest.loc[keep].copy().reset_index(drop=True)


def expected_dev_subjects_for_feature(manifest: pd.DataFrame, spec: FeatureSpec) -> set[str]:
    rows = feature_available_manifest(manifest, spec)
    return set(rows.loc[rows["official_split"] == "dev", "subject_id"].astype(str))


def numeric_array(frame: pd.DataFrame) -> np.ndarray:
    frame = frame.apply(pd.to_numeric, errors="coerce")
    frame = frame.dropna(axis=1, how="all")
    arr = frame.to_numpy(dtype=np.float32, copy=True)
    if arr.ndim != 2 or arr.shape[0] == 0 or arr.shape[1] == 0:
        raise ValueError(f"feature array must be non-empty 2D, observed {arr.shape}")
    arr[~np.isfinite(arr)] = np.nan
    if np.isnan(arr).any():
        col_mean = np.nanmean(arr, axis=0)
        col_mean = np.where(np.isfinite(col_mean), col_mean, 0.0).astype(np.float32)
        nan_rows, nan_cols = np.where(np.isnan(arr))
        arr[nan_rows, nan_cols] = col_mean[nan_cols]
    return arr.astype(np.float32, copy=False)


def subsample_half(arr: np.ndarray) -> np.ndarray:
    return arr[0::2].astype(np.float32, copy=False)


def smooth_subsample_quarter(arr: np.ndarray) -> np.ndarray:
    if arr.shape[0] >= 11:
        return savgol_filter(arr, window_length=11, polyorder=5, axis=0)[0::4].astype(np.float32, copy=False)
    return arr[0::4].astype(np.float32, copy=False)


def load_raw_feature(path: Path, spec: FeatureSpec) -> np.ndarray:
    if not path.exists():
        raise FileNotFoundError(f"E-DAIC AVEC feature missing for {spec.feature_type}: {path}")
    if spec.official_preprocess == "subject_standardize_csv_semicolon":
        frame = pd.read_csv(path, header=0, sep=";").iloc[:, 2:]
        arr = numeric_array(frame)
        return StandardScaler().fit_transform(arr).astype(np.float32)
    if spec.official_preprocess == "subject_standardize_openface":
        frame = pd.read_csv(path, header=0, skipinitialspace=True).iloc[:, 4:]
        arr = numeric_array(frame)
        return StandardScaler().fit_transform(arr).astype(np.float32)
    if spec.official_preprocess == "bow_local_csv":
        frame = pd.read_csv(path, header=None).iloc[:, 2:]
        return numeric_array(frame)
    if spec.official_preprocess == "audio_deep_half":
        frame = pd.read_csv(path, header=0).iloc[:, 2:]
        return subsample_half(numeric_array(frame))
    if spec.official_preprocess == "audio_deep_smooth_quarter":
        frame = pd.read_csv(path, header=0).iloc[:, 2:]
        return smooth_subsample_quarter(numeric_array(frame))
    if spec.official_preprocess == "mat_half":
        data = loadmat(path)
        if "feature" not in data:
            raise ValueError(f"MAT feature file missing 'feature' key: {path}")
        return subsample_half(np.asarray(data["feature"], dtype=np.float32))
    if spec.official_preprocess == "mat_smooth_quarter":
        data = loadmat(path)
        if "feature" not in data:
            raise ValueError(f"MAT feature file missing 'feature' key: {path}")
        return smooth_subsample_quarter(np.asarray(data["feature"], dtype=np.float32))
    raise ValueError(f"unsupported AVEC preprocess kind: {spec.official_preprocess}")


def feature_cache_dir(out_dir: Path, spec: FeatureSpec) -> Path:
    return out_dir / "features" / spec.modality / spec.feature_type


def feature_cache_path(out_dir: Path, spec: FeatureSpec, subject_id: str) -> Path:
    return feature_cache_dir(out_dir, spec) / f"{subject_id}.npy"


def validate_feature_shape(arr: np.ndarray, spec: FeatureSpec, subject_id: str) -> None:
    if arr.ndim != 2:
        raise ValueError(f"{spec.feature_type} subject {subject_id} feature must be 2D; observed {arr.shape}")
    if arr.shape[1] != spec.feature_dim:
        raise ValueError(
            f"{spec.feature_type} subject {subject_id} feature dimension mismatch: "
            f"{arr.shape[1]} vs official {spec.feature_dim}"
        )
    if arr.shape[0] <= 0:
        raise ValueError(f"{spec.feature_type} subject {subject_id} has no frames")
    if not np.all(np.isfinite(arr)):
        raise ValueError(f"{spec.feature_type} subject {subject_id} contains non-finite values after preprocessing")


def prepare_feature_cache(
    manifest: pd.DataFrame,
    spec: FeatureSpec,
    out_dir: Path,
    force: bool = False,
) -> pd.DataFrame:
    cache_dir = feature_cache_dir(out_dir, spec)
    cache_dir.mkdir(parents=True, exist_ok=True)
    rows: list[dict[str, Any]] = []
    print(f"Preparing AVEC feature cache: {spec.feature_type} ({len(manifest)} subjects)", flush=True)
    for index, row in manifest.reset_index(drop=True).iterrows():
        subject_id = str(row["subject_id"])
        known_missing_reason = known_official_missing_feature(spec, subject_id)
        if known_missing_reason is not None:
            rows.append(
                {
                    "subject_id": subject_id,
                    "split": str(row["official_split"]),
                    "feature_type": spec.feature_type,
                    "official_modality": spec.modality,
                    "sequence_length": 0,
                    "feature_dim": int(spec.feature_dim),
                    "max_sequence_length": int(spec.max_sequence_length),
                    "center_crop_applied_in_loader": False,
                    "feature_available": False,
                    "known_official_missing": True,
                    "missing_reason": known_missing_reason,
                }
            )
            continue
        cache_path = feature_cache_path(out_dir, spec, subject_id)
        if cache_path.exists() and not force:
            arr = np.load(cache_path, mmap_mode="r")
        else:
            arr = load_raw_feature(subject_feature_path(row, spec), spec)
            validate_feature_shape(arr, spec, subject_id)
            np.save(cache_path, arr.astype(np.float32, copy=False))
            arr = np.load(cache_path, mmap_mode="r")
        validate_feature_shape(arr, spec, subject_id)
        rows.append(
            {
                "subject_id": subject_id,
                "split": str(row["official_split"]),
                "feature_type": spec.feature_type,
                "official_modality": spec.modality,
                "sequence_length": int(arr.shape[0]),
                "feature_dim": int(arr.shape[1]),
                "max_sequence_length": int(spec.max_sequence_length),
                "center_crop_applied_in_loader": bool(arr.shape[0] > spec.max_sequence_length),
                "feature_available": True,
                "known_official_missing": False,
                "missing_reason": "",
            }
        )
        if (index + 1) % 25 == 0:
            print(f"  [{spec.feature_type}] cached/checked {index + 1}/{len(manifest)}", flush=True)
    return pd.DataFrame(rows)


class AVECSequenceDataset(Dataset):
    def __init__(self, rows: pd.DataFrame, out_dir: Path, spec: FeatureSpec):
        self.rows = rows.sort_values("subject_id").reset_index(drop=True)
        self.out_dir = out_dir
        self.spec = spec

    def __len__(self) -> int:
        return len(self.rows)

    def __getitem__(self, index: int) -> tuple[torch.Tensor, torch.Tensor, str]:
        row = self.rows.iloc[index]
        subject_id = str(row["subject_id"])
        arr = np.load(feature_cache_path(self.out_dir, self.spec, subject_id))
        if arr.shape[0] > self.spec.max_sequence_length:
            start = int((arr.shape[0] - self.spec.max_sequence_length) / 2)
            arr = arr[start : start + self.spec.max_sequence_length]
        label = np.float32(float(row["phq8_total"]) / 25.0)
        return torch.from_numpy(arr.astype(np.float32, copy=False)), torch.tensor([label], dtype=torch.float32), subject_id


def collate_sequences(
    batch: list[tuple[torch.Tensor, torch.Tensor, str]]
) -> tuple[torch.Tensor, list[int], torch.Tensor, list[str]]:
    batch = sorted(batch, key=lambda item: item[0].shape[0], reverse=True)
    features, labels, subject_ids = zip(*batch, strict=True)
    lengths = [int(feature.shape[0]) for feature in features]
    feature_dim = int(features[0].shape[1])
    padded = torch.zeros((len(features), max(lengths), feature_dim), dtype=torch.float32)
    for index, feature in enumerate(features):
        padded[index, : feature.shape[0], :] = feature
    return padded, lengths, torch.stack(list(labels), dim=0), list(subject_ids)


class AVECUnimodalRegressor(nn.Module):
    def __init__(
        self,
        feature_dim: int,
        hidden_dim: int = OFFICIAL_HIDDEN_DIM,
        dropout: float = OFFICIAL_DROPOUT,
        long_sequence_mode: str = "native_packed",
    ):
        super().__init__()
        if long_sequence_mode not in LONG_SEQUENCE_MODES:
            raise ValueError(f"unsupported long sequence mode: {long_sequence_mode}")
        self.long_sequence_mode = long_sequence_mode
        self.rnn = nn.GRU(
            input_size=feature_dim,
            hidden_size=hidden_dim,
            num_layers=1,
            bidirectional=False,
            batch_first=True,
        )
        self.dropout = nn.Dropout(dropout)
        self.head = nn.Linear(hidden_dim, 1)

    def forward(self, seq: torch.Tensor, lengths: list[int]) -> torch.Tensor:
        if seq.is_cuda and seq.shape[1] > CUDA_CUDNN_SEQUENCE_LIMIT:
            if self.long_sequence_mode == "native_packed":
                packed = pack_padded_sequence(seq, lengths, batch_first=True, enforce_sorted=True)
                with torch.backends.cudnn.flags(enabled=False):
                    output, _ = self.rnn(packed)
                padded, _ = pad_packed_sequence(output, batch_first=True)
            elif self.long_sequence_mode == "padded":
                padded, _ = self.rnn(seq.contiguous())
            else:
                try:
                    padded, _ = self.rnn(seq.contiguous())
                except RuntimeError as exc:
                    if "CUDNN_STATUS_NOT_SUPPORTED" not in str(exc):
                        raise
                    packed = pack_padded_sequence(seq, lengths, batch_first=True, enforce_sorted=True)
                    with torch.backends.cudnn.flags(enabled=False):
                        output, _ = self.rnn(packed)
                    padded, _ = pad_packed_sequence(output, batch_first=True)
        else:
            packed = pack_padded_sequence(seq, lengths, batch_first=True, enforce_sorted=True)
            output, _ = self.rnn(packed)
            padded, _ = pad_packed_sequence(output, batch_first=True)
        index = torch.tensor(lengths, device=seq.device, dtype=torch.long).view(-1, 1, 1) - 1
        index = index.expand(seq.shape[0], 1, self.rnn.hidden_size)
        last = torch.gather(padded, 1, index).squeeze(1)
        return self.head(self.dropout(last))


def ccc_numpy(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    true = np.asarray(y_true, dtype=np.float64).reshape(-1)
    pred = np.asarray(y_pred, dtype=np.float64).reshape(-1)
    mask = np.isfinite(true) & np.isfinite(pred)
    true = true[mask]
    pred = pred[mask]
    if true.size < 2:
        return float("nan")
    true_mean = float(np.mean(true))
    pred_mean = float(np.mean(pred))
    true_var = float(np.var(true))
    pred_var = float(np.var(pred))
    covariance = float(np.mean((true - true_mean) * (pred - pred_mean)))
    denom = true_var + pred_var + (true_mean - pred_mean) ** 2
    if denom <= 0.0:
        return float("nan")
    return float((2.0 * covariance) / denom)


def ccc_loss(output: torch.Tensor, target: torch.Tensor) -> torch.Tensor:
    out_mean = torch.mean(output)
    target_mean = torch.mean(target)
    covariance = torch.mean((output - out_mean) * (target - target_mean))
    target_var = torch.mean((target - target_mean) ** 2)
    out_var = torch.mean((output - out_mean) ** 2)
    ccc = 2.0 * covariance / (target_var + out_var + (target_mean - out_mean) ** 2 + 1e-10)
    return 1.0 - ccc


def make_loader(
    rows: pd.DataFrame,
    out_dir: Path,
    spec: FeatureSpec,
    batch_size: int,
    shuffle: bool,
    workers: int,
    seed: int,
    device: torch.device,
) -> DataLoader:
    generator = torch.Generator()
    generator.manual_seed(seed)
    return DataLoader(
        AVECSequenceDataset(rows, out_dir, spec),
        batch_size=batch_size,
        shuffle=shuffle,
        num_workers=workers,
        collate_fn=collate_sequences,
        pin_memory=(device.type == "cuda"),
        generator=generator,
        drop_last=False,
    )


def run_validation(model: nn.Module, loader: DataLoader, device: torch.device) -> dict[str, tuple[float, float]]:
    model.eval()
    predictions: dict[str, tuple[float, float]] = {}
    with torch.no_grad():
        for features, lengths, labels, subject_ids in loader:
            features = features.to(device, non_blocking=True)
            pred = model(features, lengths).detach().cpu().numpy().reshape(-1)
            labels_np = labels.numpy().reshape(-1)
            for subject_id, y_true, y_pred in zip(subject_ids, labels_np, pred, strict=True):
                predictions[str(subject_id)] = (float(y_true), float(y_pred))
    return predictions


def train_one_feature_seed(
    spec: FeatureSpec,
    seed: int,
    manifest: pd.DataFrame,
    out_dir: Path,
    epochs: int,
    batch_size: int,
    workers: int,
    device: torch.device,
    log_every: int,
    long_sequence_mode: str,
) -> tuple[dict[str, float], dict[str, Any], list[dict[str, Any]]]:
    set_seed(seed)
    available_manifest = feature_available_manifest(manifest, spec)
    train_rows = available_manifest[available_manifest["official_split"] == "train"].sort_values("subject_id").reset_index(drop=True)
    dev_rows = available_manifest[available_manifest["official_split"] == "dev"].sort_values("subject_id").reset_index(drop=True)
    if train_rows.empty or dev_rows.empty:
        raise ValueError("official E-DAIC train/dev split is required")
    train_loader = make_loader(train_rows, out_dir, spec, batch_size, True, workers, seed, device)
    dev_loader = make_loader(dev_rows, out_dir, spec, batch_size, False, workers, seed, device)
    model = AVECUnimodalRegressor(feature_dim=spec.feature_dim, long_sequence_mode=long_sequence_mode).to(device)
    optimizer = torch.optim.Adam(model.parameters(), lr=spec.learning_rate, weight_decay=0.0, amsgrad=True)

    best_ccc = -math.inf
    best_predictions: dict[str, tuple[float, float]] | None = None
    epoch_rows: list[dict[str, Any]] = []
    for epoch in range(1, epochs + 1):
        model.train()
        losses: list[float] = []
        train_pred: list[float] = []
        train_true: list[float] = []
        for features, lengths, labels, _ in train_loader:
            features = features.to(device, non_blocking=True)
            labels = labels.to(device, non_blocking=True)
            optimizer.zero_grad(set_to_none=True)
            pred = model(features, lengths)
            loss = ccc_loss(pred, labels)
            loss.backward()
            optimizer.step()
            losses.append(float(loss.detach().cpu()))
            train_pred.extend(pred.detach().cpu().numpy().reshape(-1).tolist())
            train_true.extend(labels.detach().cpu().numpy().reshape(-1).tolist())
        validation = run_validation(model, dev_loader, device)
        val_true = np.asarray([item[0] for item in validation.values()], dtype=np.float64)
        val_pred = np.asarray([item[1] for item in validation.values()], dtype=np.float64)
        val_ccc = ccc_numpy(val_true, val_pred)
        train_ccc = ccc_numpy(np.asarray(train_true), np.asarray(train_pred))
        train_loss = float(np.mean(losses)) if losses else float("nan")
        epoch_rows.append(
            {
                "feature_type": spec.feature_type,
                "seed": int(seed),
                "epoch": int(epoch),
                "train_loss": train_loss,
                "train_ccc_scaled": train_ccc,
                "dev_ccc_scaled": val_ccc,
            }
        )
        if np.isfinite(val_ccc) and val_ccc > best_ccc:
            best_ccc = float(val_ccc)
            best_predictions = validation
        if log_every > 0 and (epoch == 1 or epoch == epochs or epoch % log_every == 0):
            print(
                f"[{spec.feature_type} seed {seed}] epoch {epoch}/{epochs} "
                f"train_loss={train_loss:.5f} train_ccc={train_ccc:.5f} dev_ccc={val_ccc:.5f}",
                flush=True,
            )

    if best_predictions is None:
        best_predictions = validation
        best_ccc = ccc_numpy(
            np.asarray([item[0] for item in validation.values()], dtype=np.float64),
            np.asarray([item[1] for item in validation.values()], dtype=np.float64),
        )
    dev_order = dev_rows["subject_id"].astype(str).tolist()
    prediction_map = {subject_id: best_predictions[subject_id][1] * 25.0 for subject_id in dev_order}
    summary = {
        "feature_type": spec.feature_type,
        "seed": int(seed),
        "best_dev_ccc_scaled": float(best_ccc),
        "best_epoch": int(max(epoch_rows, key=lambda row: row["dev_ccc_scaled"] if np.isfinite(row["dev_ccc_scaled"]) else -math.inf)["epoch"]),
        "epochs": int(epochs),
        "batch_size": int(batch_size),
        "learning_rate": float(spec.learning_rate),
        "long_sequence_mode": long_sequence_mode,
        "train_subjects": int(len(train_rows)),
        "dev_subjects": int(len(dev_rows)),
    }
    return prediction_map, summary, epoch_rows


def official_matrix_run(selected_specs: list[FeatureSpec], seeds: list[int], args: argparse.Namespace) -> bool:
    selected_names = [spec.feature_type for spec in selected_specs]
    official_names = [spec.feature_type for spec in FEATURE_SPECS]
    return (
        selected_names == official_names
        and seeds == SEEDS
        and int(args.epochs) == OFFICIAL_EPOCHS
        and int(args.batch_size) == OFFICIAL_BATCH_SIZE
        and int(args.bootstrap_resamples) >= 1000
    )


def build_fusion_predictions(
    manifest: pd.DataFrame,
    selected_specs: list[FeatureSpec],
    seeds: list[int],
    feature_predictions: dict[tuple[str, int], dict[str, float]],
    matrix_run: bool,
) -> pd.DataFrame:
    dev = manifest[manifest["official_split"] == "dev"].sort_values("subject_id").reset_index(drop=True)
    run_id = "edaic_public_avec_official" if matrix_run else "edaic_public_avec_official_partial"
    rows: list[dict[str, Any]] = []
    for seed in seeds:
        for _, row in dev.iterrows():
            subject_id = str(row["subject_id"])
            values: list[float] = []
            missing_features: list[str] = []
            for spec in selected_specs:
                pred_map = feature_predictions[(spec.feature_type, seed)]
                if subject_id in pred_map:
                    values.append(float(pred_map[subject_id]))
                else:
                    missing_features.append(spec.feature_type)
            if not values:
                if matrix_run:
                    raise ValueError(f"no AVEC feature predictions available for subject {subject_id}, seed {seed}")
                continue
            rows.append(
                {
                    "run_id": run_id,
                    "dataset": "E-DAIC",
                    "modality": "Audio/Video/Text",
                    "task": "PHQ-8 regression",
                    "model": "AVEC/E-DAIC official baseline",
                    "seed": int(seed),
                    "task_type": "severity_regression",
                    "subject_id": subject_id,
                    "split": "dev",
                    "y_true": float(row["phq8_total"]),
                    "y_pred": float(np.mean(values)),
                    "y_score": np.nan,
                    "feature_set_count": int(len(selected_specs)),
                    "available_feature_set_count": int(len(values)),
                    "missing_feature_set_count": int(len(missing_features)),
                    "missing_feature_sets": ";".join(missing_features),
                    "official_validation_selection": True,
                    "fusion_rule": "unweighted_mean",
                }
            )
    return pd.DataFrame(rows)


def build_feature_prediction_frame(
    manifest: pd.DataFrame,
    selected_specs: list[FeatureSpec],
    seeds: list[int],
    feature_predictions: dict[tuple[str, int], dict[str, float]],
) -> pd.DataFrame:
    dev = manifest[manifest["official_split"] == "dev"].sort_values("subject_id").reset_index(drop=True)
    rows: list[dict[str, Any]] = []
    for spec in selected_specs:
        for seed in seeds:
            pred_map = feature_predictions[(spec.feature_type, seed)]
            for _, row in dev.iterrows():
                subject_id = str(row["subject_id"])
                if subject_id not in pred_map:
                    continue
                rows.append(
                    {
                        "feature_type": spec.feature_type,
                        "official_modality": spec.modality,
                        "seed": int(seed),
                        "subject_id": subject_id,
                        "split": "dev",
                        "y_true": float(row["phq8_total"]),
                        "y_pred": float(pred_map[subject_id]),
                    }
                )
    return pd.DataFrame(rows)


def build_available_feature_prediction_frame(
    manifest: pd.DataFrame,
    feature_predictions: dict[tuple[str, int], dict[str, float]],
) -> pd.DataFrame:
    dev = manifest[manifest["official_split"] == "dev"].sort_values("subject_id").reset_index(drop=True)
    rows: list[dict[str, Any]] = []
    for feature_type, seed in sorted(feature_predictions):
        spec = FEATURE_BY_NAME[feature_type]
        pred_map = feature_predictions[(feature_type, seed)]
        for _, row in dev.iterrows():
            subject_id = str(row["subject_id"])
            if subject_id not in pred_map:
                continue
            rows.append(
                {
                    "feature_type": spec.feature_type,
                    "official_modality": spec.modality,
                    "seed": int(seed),
                    "subject_id": subject_id,
                    "split": "dev",
                    "y_true": float(row["phq8_total"]),
                    "y_pred": float(pred_map[subject_id]),
                }
            )
    return pd.DataFrame(rows)


def atomic_write_csv(frame: pd.DataFrame, path: Path) -> None:
    tmp_path = path.with_suffix(path.suffix + ".tmp")
    frame.to_csv(tmp_path, index=False)
    tmp_path.replace(path)


def save_progress(
    out_dir: Path,
    manifest: pd.DataFrame,
    feature_predictions: dict[tuple[str, int], dict[str, float]],
    feature_seed_summaries: list[dict[str, Any]],
    training_trace_rows: list[dict[str, Any]],
) -> None:
    atomic_write_csv(
        build_available_feature_prediction_frame(manifest, feature_predictions),
        out_dir / PROGRESS_FEATURE_PREDICTIONS,
    )
    atomic_write_csv(pd.DataFrame(feature_seed_summaries), out_dir / PROGRESS_SEED_SUMMARIES)
    atomic_write_csv(pd.DataFrame(training_trace_rows), out_dir / PROGRESS_TRAINING_TRACE)


def load_progress(
    out_dir: Path,
    manifest: pd.DataFrame,
    selected_specs: list[FeatureSpec],
    seeds: list[int],
) -> tuple[dict[tuple[str, int], dict[str, float]], list[dict[str, Any]], list[dict[str, Any]]]:
    dev_subjects_by_feature = {
        spec.feature_type: expected_dev_subjects_for_feature(manifest, spec) for spec in FEATURE_SPECS
    }
    feature_predictions: dict[tuple[str, int], dict[str, float]] = {}
    prediction_sources = [
        out_dir / PROGRESS_FEATURE_PREDICTIONS,
        out_dir / "edaic_public_avec_partial_feature_predictions.csv",
        out_dir / "edaic_public_avec_feature_predictions.csv",
    ]
    for progress_path in prediction_sources:
        if not progress_path.exists():
            continue
        frame = pd.read_csv(progress_path)
        required = {"feature_type", "seed", "subject_id", "y_pred"}
        missing = required - set(frame.columns)
        if missing:
            raise ValueError(f"AVEC progress predictions missing columns: {', '.join(sorted(missing))}")
        frame["feature_type"] = frame["feature_type"].astype(str)
        frame["subject_id"] = frame["subject_id"].astype(str)
        frame["seed"] = frame["seed"].astype(int)
        usable = frame[
            frame["feature_type"].isin(FEATURE_BY_NAME)
            & frame["feature_type"].isin(dev_subjects_by_feature)
        ].copy()
        for (feature_type, seed), group in usable.groupby(["feature_type", "seed"], sort=True):
            expected_subjects = dev_subjects_by_feature[str(feature_type)]
            subjects = set(group["subject_id"].astype(str))
            if subjects == expected_subjects and len(group) == len(expected_subjects):
                feature_predictions[(str(feature_type), int(seed))] = {
                    str(row["subject_id"]): float(row["y_pred"]) for _, row in group.iterrows()
                }

    summary_path = out_dir / PROGRESS_SEED_SUMMARIES
    summaries: list[dict[str, Any]] = []
    if summary_path.exists():
        summaries.extend(pd.read_csv(summary_path).to_dict("records"))
    run_summary_path = out_dir / "edaic_public_avec_run_summary.json"
    if run_summary_path.exists():
        with run_summary_path.open("r", encoding="utf-8") as handle:
            run_summary = json.load(handle)
        summaries.extend(run_summary.get("feature_seed_summaries") or [])
    observed_summary_keys: set[tuple[str, int]] = set()
    deduped_summaries: list[dict[str, Any]] = []
    for row in summaries:
        key = (str(row.get("feature_type")), int(row.get("seed")))
        if key in feature_predictions and key not in observed_summary_keys:
            deduped_summaries.append(row)
            observed_summary_keys.add(key)
    summaries = deduped_summaries

    traces: list[dict[str, Any]] = []
    for trace_path in [out_dir / PROGRESS_TRAINING_TRACE, out_dir / "edaic_public_avec_training_trace.csv"]:
        if not trace_path.exists():
            continue
        trace_frame = pd.read_csv(trace_path)
        if {"feature_type", "seed"}.issubset(trace_frame.columns):
            trace_frame["feature_type"] = trace_frame["feature_type"].astype(str)
            trace_frame["seed"] = trace_frame["seed"].astype(int)
            trace_frame = trace_frame[
                [
                    (str(row["feature_type"]), int(row["seed"])) in feature_predictions
                    for _, row in trace_frame.iterrows()
                ]
            ]
            if {"feature_type", "seed", "epoch"}.issubset(trace_frame.columns):
                trace_frame = trace_frame.drop_duplicates(["feature_type", "seed", "epoch"], keep="first")
        traces.extend(trace_frame.to_dict("records"))
    if traces:
        trace_frame = pd.DataFrame(traces)
        if {"feature_type", "seed", "epoch"}.issubset(trace_frame.columns):
            trace_frame = trace_frame.drop_duplicates(["feature_type", "seed", "epoch"], keep="first")
        traces = trace_frame.to_dict("records")

    return feature_predictions, summaries, traces


def forbidden_prediction_columns(frame: pd.DataFrame) -> list[str]:
    forbidden = {"text", "transcript", "prompt", "raw_response", "audio_path", "video_path", "text_path", "path", "file_path"}
    return [column for column in frame.columns if str(column).lower() in forbidden]


def write_report(out_dir: Path, summary: dict[str, Any], metrics: pd.DataFrame | None, matrix_run: bool) -> None:
    metric_lines: list[str] = []
    if metrics is not None and not metrics.empty:
        for _, row in metrics.sort_values(["run_id", "metric"]).iterrows():
            metric_lines.append(
                f"- `{row['metric']}`: mean {float(row['mean']):.6f}, "
                f"std {float(row['std']):.6f}, CI95 [{float(row['ci95_low']):.6f}, {float(row['ci95_high']):.6f}]"
            )
    else:
        metric_lines.append("- Matrix metrics were not written because this was a partial or smoke run.")
    matrix_line = (
        "- Matrix output: `phase2_metric_summary.csv` written for `edaic_public_avec_official`."
        if matrix_run
        else "- Matrix output: not written; run did not satisfy the full official matrix contract."
    )
    lines = [
        "# E-DAIC AVEC 2019 DDS Public Baseline",
        "",
        f"Generated: `{summary['generated_at']}`",
        "",
        "## Protocol",
        "",
        "- Public source: `AudioVisualEmotionChallenge/AVEC2019`, DDS baseline.",
        f"- Source commit: `{summary.get('official_source_commit')}`.",
        "- Model: one-layer 64-dimensional GRU regressor with dropout 0.2 and CCC loss.",
        "- Training: Adam with official per-feature learning rates, batch size 15, 30 epochs for matrix runs.",
        "- Selection: best epoch is selected by development CCC, matching the official script.",
        "- Fusion: unweighted mean over official DDS feature-set predictions.",
        "- Local adaptation: feature readers are adjusted from the official split-layout paths to manifest-resolved E-DAIC subject folders.",
        (
            "- Runtime compatibility: very long CUDA GRU sequences use "
            f"`{summary.get('long_sequence_mode')}` mode; "
            f"{summary.get('runtime_compatibility', {}).get('long_sequence_execution')}. "
            "This avoids the current cuDNN packed-sequence limit without changing the model contract."
        ),
        "- Resume behavior: completed feature/seed dev predictions are saved to progress CSVs after each seed and can be reused on later invocations.",
        "- Test labels are not used, and test predictions are not required for Phase 2 metrics.",
        "- Prediction artifacts contain no raw text, audio/video data, source paths, raw model responses, prompts, or checkpoints.",
        "",
        "## Audit",
        "",
        f"- Selected feature sets: `{summary['selected_feature_types']}`",
        f"- Seeds: `{summary['seeds']}`",
        f"- Train subjects: `{summary['train_subjects']}`",
        f"- Dev subjects: `{summary['dev_subjects']}`",
        f"- Prediction rows: `{summary['prediction_rows']}`",
        f"- Feature prediction rows: `{summary['feature_prediction_rows']}`",
        f"- Completed progress feature/seed blocks: `{summary['progress_feature_seed_blocks']}`",
        f"- Fully completed official feature sets in progress: `{summary['progress_completed_official_feature_sets']}`",
        f"- Remaining official feature/seed blocks: `{summary['progress_remaining_official_feature_seed_blocks']}`",
        f"- Known official missing feature subjects: `{summary['known_official_missing_feature_subjects']}`",
        f"- Bootstrap resamples: `{summary['bootstrap_resamples']}`",
        f"- Subject overlap violations: `{summary['subject_overlap_violations']}`",
        f"- Checkpoints written: `{summary['checkpoints_written']}`",
        f"- Source paths written in predictions: `{summary['source_paths_written_in_predictions']}`",
        matrix_line,
        "",
        "## Metrics",
        "",
        *metric_lines,
        "",
        "## Output Files",
        "",
        f"- `{summary['prediction_file']}`",
        f"- `{summary['feature_prediction_file']}`",
        "- `edaic_public_avec_feature_metadata.csv`",
        "- `edaic_public_avec_training_trace.csv`",
        f"- `{PROGRESS_FEATURE_PREDICTIONS}`",
        f"- `{PROGRESS_SEED_SUMMARIES}`",
        f"- `{PROGRESS_TRAINING_TRACE}`",
        "- `edaic_public_avec_run_summary.json`",
    ]
    if matrix_run:
        lines.extend(["- `phase2_metrics_by_seed.csv`", "- `phase2_metric_summary.csv`"])
    else:
        lines.extend(["- `edaic_public_avec_partial_metrics_by_seed.csv`", "- `edaic_public_avec_partial_metric_summary.csv`"])
    (out_dir / "edaic_public_avec_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, default=MANIFEST_PATH)
    parser.add_argument("--official-repo", type=Path, default=OFFICIAL_REPO)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--feature-type", choices=[spec.feature_type for spec in FEATURE_SPECS], action="append")
    parser.add_argument("--seeds", type=int, nargs="+", default=SEEDS)
    parser.add_argument("--epochs", type=int, default=OFFICIAL_EPOCHS)
    parser.add_argument("--batch-size", type=int, default=OFFICIAL_BATCH_SIZE)
    parser.add_argument("--workers", type=int, default=2)
    parser.add_argument("--bootstrap-resamples", type=int, default=1000)
    parser.add_argument("--force-features", action="store_true")
    parser.add_argument("--resume-progress", dest="resume_progress", action="store_true", default=True)
    parser.add_argument("--no-resume-progress", dest="resume_progress", action="store_false")
    parser.add_argument("--device", default="cuda" if torch.cuda.is_available() else "cpu")
    parser.add_argument("--log-every", type=int, default=5)
    parser.add_argument(
        "--long-sequence-mode",
        choices=LONG_SEQUENCE_MODES,
        default="native_packed",
        help=(
            "Execution path for CUDA sequences longer than the cuDNN packed-sequence limit. "
            "native_packed keeps the official packed-sequence semantics with cuDNN disabled; "
            "padded uses padded cuDNN execution and gathers the last valid step; auto tries padded "
            "and falls back to native packed if cuDNN rejects the sequence."
        ),
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    args.out_dir.mkdir(parents=True, exist_ok=True)
    manifest = read_manifest(args.manifest)
    selected_specs = [FEATURE_BY_NAME[name] for name in (args.feature_type or [spec.feature_type for spec in FEATURE_SPECS])]
    seeds = list(args.seeds)
    train_subjects = set(manifest.loc[manifest["official_split"] == "train", "subject_id"].astype(str))
    dev_subjects = set(manifest.loc[manifest["official_split"] == "dev", "subject_id"].astype(str))
    overlap = sorted(train_subjects & dev_subjects)
    if overlap:
        raise ValueError(f"E-DAIC train/dev subject overlap detected: {overlap[:10]}")
    device = torch.device(args.device)
    if device.type == "cuda" and not torch.cuda.is_available():
        raise ValueError("CUDA device requested but torch.cuda.is_available() is false")
    print(f"Running AVEC DDS adaptation on device={device}", flush=True)
    print(f"Selected feature sets: {[spec.feature_type for spec in selected_specs]}", flush=True)
    print(f"Seeds: {seeds}", flush=True)

    metadata_frames: list[pd.DataFrame] = []
    if args.resume_progress:
        feature_predictions, feature_seed_summaries, training_trace_rows = load_progress(
            args.out_dir, manifest, selected_specs, seeds
        )
        if feature_predictions:
            print(f"Resuming {len(feature_predictions)} completed feature/seed prediction blocks", flush=True)
            save_progress(args.out_dir, manifest, feature_predictions, feature_seed_summaries, training_trace_rows)
    else:
        feature_predictions = {}
        feature_seed_summaries = []
        training_trace_rows = []
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", category=UserWarning)
        for spec in selected_specs:
            metadata_frames.append(prepare_feature_cache(manifest, spec, args.out_dir, force=args.force_features))
            for seed in seeds:
                if (spec.feature_type, seed) in feature_predictions:
                    print(f"[{spec.feature_type} seed {seed}] using resumed dev predictions", flush=True)
                    continue
                pred_map, seed_summary, epoch_rows = train_one_feature_seed(
                    spec=spec,
                    seed=seed,
                    manifest=manifest,
                    out_dir=args.out_dir,
                    epochs=args.epochs,
                    batch_size=args.batch_size,
                    workers=args.workers,
                    device=device,
                    log_every=args.log_every,
                    long_sequence_mode=args.long_sequence_mode,
                )
                feature_predictions[(spec.feature_type, seed)] = pred_map
                feature_seed_summaries.append(seed_summary)
                training_trace_rows.extend(epoch_rows)
                save_progress(args.out_dir, manifest, feature_predictions, feature_seed_summaries, training_trace_rows)

    matrix_run = official_matrix_run(selected_specs, seeds, args)
    missing_blocks = [
        (spec.feature_type, int(seed))
        for spec in selected_specs
        for seed in seeds
        if (spec.feature_type, int(seed)) not in feature_predictions
    ]
    if missing_blocks:
        raise ValueError(f"missing AVEC feature/seed prediction blocks: {missing_blocks[:10]}")
    fusion_predictions = build_fusion_predictions(manifest, selected_specs, seeds, feature_predictions, matrix_run)
    feature_prediction_frame = build_feature_prediction_frame(manifest, selected_specs, seeds, feature_predictions)
    for frame_name, frame in [("fusion predictions", fusion_predictions), ("feature predictions", feature_prediction_frame)]:
        bad_columns = forbidden_prediction_columns(frame)
        if bad_columns:
            raise ValueError(f"{frame_name} contain forbidden raw/path columns: {bad_columns}")

    prediction_file = "edaic_public_avec_predictions.csv" if matrix_run else "edaic_public_avec_partial_predictions.csv"
    feature_prediction_file = (
        "edaic_public_avec_feature_predictions.csv"
        if matrix_run
        else "edaic_public_avec_partial_feature_predictions.csv"
    )
    fusion_predictions.to_csv(args.out_dir / prediction_file, index=False)
    feature_prediction_frame.to_csv(args.out_dir / feature_prediction_file, index=False)
    pd.concat(metadata_frames, ignore_index=True).to_csv(
        args.out_dir / "edaic_public_avec_feature_metadata.csv",
        index=False,
    )
    pd.DataFrame(training_trace_rows).to_csv(args.out_dir / "edaic_public_avec_training_trace.csv", index=False)

    per_seed, metric_summary = metric_records(fusion_predictions, args.bootstrap_resamples, seed=20260727)
    if matrix_run:
        per_seed.to_csv(args.out_dir / "phase2_metrics_by_seed.csv", index=False)
        metric_summary.to_csv(args.out_dir / "phase2_metric_summary.csv", index=False)
    else:
        per_seed.to_csv(args.out_dir / "edaic_public_avec_partial_metrics_by_seed.csv", index=False)
        metric_summary.to_csv(args.out_dir / "edaic_public_avec_partial_metric_summary.csv", index=False)

    official_block_keys = {(spec.feature_type, seed) for spec in FEATURE_SPECS for seed in SEEDS}
    completed_official_keys = set(feature_predictions).intersection(official_block_keys)
    completed_official_feature_sets = [
        spec.feature_type
        for spec in FEATURE_SPECS
        if all((spec.feature_type, seed) in feature_predictions for seed in SEEDS)
    ]
    remaining_official_feature_sets = [
        spec.feature_type for spec in FEATURE_SPECS if spec.feature_type not in completed_official_feature_sets
    ]
    summary = {
        "generated_at": utc_now(),
        "official_source_url": "https://github.com/AudioVisualEmotionChallenge/AVEC2019",
        "official_source_commit": official_commit(args.official_repo),
        "paper_url": "https://arxiv.org/abs/1907.11510",
        "run_id": "edaic_public_avec_official" if matrix_run else "edaic_public_avec_official_partial",
        "matrix_run": bool(matrix_run),
        "selected_feature_types": [spec.feature_type for spec in selected_specs],
        "official_feature_types": [spec.feature_type for spec in FEATURE_SPECS],
        "known_official_missing_feature_subjects": [
            {
                "feature_type": feature_type,
                "subject_id": subject_id,
                "reason": reason,
            }
            for (feature_type, subject_id), reason in sorted(KNOWN_OFFICIAL_MISSING_FEATURE_SUBJECTS.items())
        ],
        "local_adaptation": "official DDS feature readers adapted to per-subject E-DAIC feature folders",
        "model_contract": {
            "rnn": "GRU",
            "rnn_layers": 1,
            "hidden_dim": OFFICIAL_HIDDEN_DIM,
            "dropout": OFFICIAL_DROPOUT,
            "loss": "1 - CCC",
            "optimizer": "Adam(amsgrad=True)",
            "fusion": "unweighted mean of feature-set predictions",
            "best_epoch_selection": "development CCC",
        },
        "runtime_compatibility": {
            "long_sequence_threshold": CUDA_CUDNN_SEQUENCE_LIMIT,
            "long_sequence_mode": args.long_sequence_mode,
            "long_sequence_execution": (
                "native packed sequence with cuDNN disabled"
                if args.long_sequence_mode == "native_packed"
                else (
                    "padded GRU batch, gather last valid timestep"
                    if args.long_sequence_mode == "padded"
                    else "padded GRU batch with native packed fallback if cuDNN reports unsupported"
                )
            ),
            "packed_sequence_fallback": (
                "not needed in native_packed mode"
                if args.long_sequence_mode == "native_packed"
                else "native backend if cuDNN reports unsupported"
            ),
            "resume_progress_files": [
                PROGRESS_FEATURE_PREDICTIONS,
                PROGRESS_SEED_SUMMARIES,
                PROGRESS_TRAINING_TRACE,
            ],
        },
        "epochs": int(args.epochs),
        "batch_size": int(args.batch_size),
        "seeds": seeds,
        "seed_count": int(len(seeds)),
        "bootstrap_resamples": int(args.bootstrap_resamples),
        "device": str(device),
        "workers": int(args.workers),
        "long_sequence_mode": args.long_sequence_mode,
        "train_subjects": int(len(train_subjects)),
        "dev_subjects": int(len(dev_subjects)),
        "test_subjects_used": 0,
        "test_labels_used": False,
        "development_labels_used_for_official_epoch_selection": True,
        "prediction_rows": int(len(fusion_predictions)),
        "feature_prediction_rows": int(len(feature_prediction_frame)),
        "progress_feature_seed_blocks": int(len(feature_predictions)),
        "progress_feature_types": sorted({feature_type for feature_type, _ in feature_predictions}),
        "progress_completed_official_feature_seed_blocks": int(len(completed_official_keys)),
        "progress_remaining_official_feature_seed_blocks": int(len(official_block_keys - completed_official_keys)),
        "progress_completed_official_feature_sets": completed_official_feature_sets,
        "progress_remaining_official_feature_sets": remaining_official_feature_sets,
        "feature_seed_summaries": feature_seed_summaries,
        "subject_overlap_violations": int(bool(overlap)),
        "checkpoints_written": False,
        "raw_text_written": False,
        "raw_audio_video_written": False,
        "source_paths_written_in_predictions": False,
        "prediction_file": prediction_file,
        "feature_prediction_file": feature_prediction_file,
    }
    (args.out_dir / "edaic_public_avec_run_summary.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=True, sort_keys=True),
        encoding="utf-8",
    )
    write_report(args.out_dir, summary, metric_summary if matrix_run else None, matrix_run)
    print(f"Wrote {args.out_dir / prediction_file}", flush=True)
    if matrix_run:
        print(f"Wrote {args.out_dir / 'phase2_metric_summary.csv'}", flush=True)
    else:
        print("Partial run only; matrix summary was not written.", flush=True)


if __name__ == "__main__":
    main()
