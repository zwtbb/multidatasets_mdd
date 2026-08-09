#!/usr/bin/env python3
"""Run Phase 2 EATD official GRU/BiLSTM-style public reproductions.

The official ICASSP 2022 EATD code uses GRU/BiLSTM recurrent models over the
three emotional tasks. Its original feature extraction depends on an old
TensorFlow/VGGish/NetVLAD and ELMoForManyLangs stack with local absolute paths,
so this runner preserves the public model family and official train/validation
split while using the project's audited, reproducible EATD text/audio feature
interface.

Prediction artifacts intentionally contain no raw text, audio paths, or source
paths.
"""

from __future__ import annotations

import argparse
import itertools
import json
import os
import random
import subprocess
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
from sklearn.decomposition import TruncatedSVD
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import StandardScaler
from torch.utils.data import DataLoader, TensorDataset

from phase2_metrics import metric_records


ROOT = Path("/root/autodl-tmp")
MANIFEST_PATH = ROOT / "datasets" / "manifests" / "eatd_subjects.csv"
AUDIO_FEATURES = ROOT / "analysis" / "phase2_baselines" / "eatd_audio_egemaps" / "eatd_egemaps_subject_features.csv"
OFFICIAL_REPO = ROOT / "cache" / "official_baselines" / "ICASSP2022-Depression"
DEFAULT_OUT_DIR = ROOT / "analysis" / "phase2_baselines" / "eatd_public_gru_bilstm"
SEEDS = [0, 1, 2, 3, 4]
VALENCE_ORDER = ["positive", "neutral", "negative"]
PERMUTATIONS = list(itertools.permutations(range(len(VALENCE_ORDER))))


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def read_text(path_value: Any) -> str:
    path = Path(str(path_value))
    if not path.exists():
        raise FileNotFoundError(f"EATD text path missing: {path}")
    return path.read_text(encoding="utf-8", errors="ignore").strip()


def official_commit(repo: Path) -> str | None:
    if not (repo / ".git").exists():
        return None
    try:
        out = subprocess.check_output(["git", "-C", str(repo), "rev-parse", "HEAD"], text=True)
    except (OSError, subprocess.CalledProcessError):
        return None
    return out.strip()


def load_manifest(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"manifest missing: {path}")
    manifest = pd.read_csv(path)
    required = {"subject_id", "valence", "text_path", "sds_total", "binary_label", "official_split", "file_valid"}
    missing = required - set(manifest.columns)
    if missing:
        raise ValueError(f"EATD manifest missing columns: {', '.join(sorted(missing))}")
    usable = manifest[
        manifest["file_valid"].fillna(False).astype(bool)
        & manifest["text_path"].notna()
        & manifest["sds_total"].notna()
        & manifest["official_split"].isin(["train", "validation"])
        & manifest["valence"].isin(VALENCE_ORDER)
    ].copy()
    if usable.empty:
        raise ValueError("no usable EATD rows for public GRU/BiLSTM reproduction")
    return usable


def load_audio_feature_table(path: Path) -> tuple[pd.DataFrame, dict[str, list[str]], list[str]]:
    if not path.exists():
        raise FileNotFoundError(f"EATD audio feature cache missing: {path}")
    frame = pd.read_csv(path)
    required = {"subject_id", "split", "sds_total", "audio_segment_count"}
    missing = required - set(frame.columns)
    if missing:
        raise ValueError(f"EATD audio feature cache missing columns: {', '.join(sorted(missing))}")
    frame["subject_id"] = frame["subject_id"].astype(str)
    suffixes_by_valence: dict[str, set[str]] = {}
    for valence in VALENCE_ORDER:
        prefix = f"{valence}__"
        suffixes_by_valence[valence] = {
            column[len(prefix) :]
            for column in frame.columns
            if column.startswith(prefix) and pd.api.types.is_numeric_dtype(frame[column])
        }
    common_suffixes = sorted(set.intersection(*(suffixes_by_valence[valence] for valence in VALENCE_ORDER)))
    if not common_suffixes:
        raise ValueError("EATD audio cache has no common per-valence feature suffixes")
    columns_by_valence = {
        valence: [f"{valence}__{suffix}" for suffix in common_suffixes] for valence in VALENCE_ORDER
    }
    return frame, columns_by_valence, common_suffixes


@dataclass(frozen=True)
class FeatureBundle:
    subject_ids: list[str]
    splits: np.ndarray
    y: np.ndarray
    binary: np.ndarray
    x: np.ndarray
    text_dim: int
    audio_dim: int
    tfidf_dim: int
    text_svd_dim: int
    train_subject_count: int
    validation_subject_count: int


def build_feature_bundle(
    manifest_path: Path,
    audio_features_path: Path,
    text_svd_components: int,
) -> FeatureBundle:
    manifest = load_manifest(manifest_path)
    audio_frame, audio_columns_by_valence, audio_suffixes = load_audio_feature_table(audio_features_path)

    subject_rows: list[dict[str, Any]] = []
    segment_rows: list[dict[str, Any]] = []
    for subject_id, group in manifest.groupby("subject_id", sort=True):
        by_valence = {str(row["valence"]): row for _, row in group.iterrows()}
        if any(valence not in by_valence for valence in VALENCE_ORDER):
            continue
        labels = group["sds_total"].dropna().unique()
        binaries = group["binary_label"].dropna().unique()
        splits = group["official_split"].dropna().unique()
        if len(labels) != 1 or len(binaries) != 1 or len(splits) != 1:
            raise ValueError(f"inconsistent EATD label/split rows for {subject_id}")
        subject_rows.append(
            {
                "subject_id": str(subject_id),
                "split": str(splits[0]),
                "sds_total": float(labels[0]),
                "binary_label": int(float(binaries[0])),
            }
        )
        for valence_index, valence in enumerate(VALENCE_ORDER):
            segment_rows.append(
                {
                    "subject_id": str(subject_id),
                    "valence": valence,
                    "valence_index": valence_index,
                    "split": str(splits[0]),
                    "text": read_text(by_valence[valence]["text_path"]),
                }
            )

    subjects = pd.DataFrame(subject_rows).sort_values("subject_id").reset_index(drop=True)
    segments = pd.DataFrame(segment_rows)
    if subjects.empty or segments.empty:
        raise ValueError("EATD feature build produced no subjects")
    audio_frame = audio_frame.sort_values("subject_id").reset_index(drop=True)
    table = subjects.merge(audio_frame, on="subject_id", suffixes=("_text", "_audio"), how="inner")
    if len(table) != len(subjects):
        raise ValueError(f"EATD text/audio alignment lost subjects: text={len(subjects)}, aligned={len(table)}")
    split_mismatches = int((table["split_text"].astype(str) != table["split_audio"].astype(str)).sum())
    label_mismatches = int((table["sds_total_text"].astype(float) != table["sds_total_audio"].astype(float)).sum())
    if split_mismatches or label_mismatches:
        raise ValueError(f"EATD text/audio mismatch: splits={split_mismatches}, labels={label_mismatches}")
    subjects = table[["subject_id", "split_text", "sds_total_text", "binary_label"]].rename(
        columns={"split_text": "split", "sds_total_text": "sds_total"}
    )

    train_subjects = set(subjects.loc[subjects["split"] == "train", "subject_id"].astype(str))
    validation_subjects = set(subjects.loc[subjects["split"] == "validation", "subject_id"].astype(str))
    if train_subjects & validation_subjects:
        raise ValueError("EATD official split subject overlap detected")
    if not train_subjects or not validation_subjects:
        raise ValueError("EATD official train/validation split is not available")

    train_segments = segments[segments["subject_id"].isin(train_subjects)].copy()
    vectorizer = TfidfVectorizer(
        analyzer="char",
        ngram_range=(2, 5),
        min_df=2,
        max_features=30000,
        sublinear_tf=True,
        norm="l2",
    )
    train_tfidf = vectorizer.fit_transform(train_segments["text"].fillna(""))
    all_tfidf = vectorizer.transform(segments["text"].fillna(""))
    max_components = max(1, min(text_svd_components, train_tfidf.shape[0] - 1, train_tfidf.shape[1] - 1))
    svd = TruncatedSVD(n_components=max_components, random_state=0)
    train_text_dense = svd.fit_transform(train_tfidf)
    all_text_dense = svd.transform(all_tfidf)
    text_scaler = StandardScaler()
    text_scaler.fit(train_text_dense)
    segments = segments.copy()
    segments["_text_vec_index"] = np.arange(len(segments))
    text_vectors = text_scaler.transform(all_text_dense).astype(np.float32)

    audio_imputer = SimpleImputer(strategy="median")
    audio_scaler = StandardScaler()
    train_audio_rows: list[np.ndarray] = []
    for _, row in table[table["split_text"] == "train"].iterrows():
        for valence in VALENCE_ORDER:
            train_audio_rows.append(row[audio_columns_by_valence[valence]].to_numpy(dtype=np.float64))
    audio_scaler.fit(audio_imputer.fit_transform(np.vstack(train_audio_rows)))

    x_rows: list[np.ndarray] = []
    subject_ids: list[str] = []
    y_values: list[float] = []
    binary_values: list[int] = []
    split_values: list[str] = []
    segment_lookup = {
        (str(row["subject_id"]), str(row["valence"])): int(row["_text_vec_index"])
        for _, row in segments.iterrows()
    }
    table_by_subject = {str(row["subject_id"]): row for _, row in table.iterrows()}
    for _, subject in subjects.sort_values("subject_id").iterrows():
        subject_id = str(subject["subject_id"])
        source = table_by_subject[subject_id]
        sequence_parts: list[np.ndarray] = []
        for valence in VALENCE_ORDER:
            audio_raw = source[audio_columns_by_valence[valence]].to_numpy(dtype=np.float64).reshape(1, -1)
            audio_vec = audio_scaler.transform(audio_imputer.transform(audio_raw)).reshape(-1).astype(np.float32)
            text_vec = text_vectors[segment_lookup[(subject_id, valence)]]
            sequence_parts.append(np.concatenate([audio_vec, text_vec], axis=0))
        x_rows.append(np.stack(sequence_parts, axis=0))
        subject_ids.append(subject_id)
        split_values.append(str(subject["split"]))
        y_values.append(float(subject["sds_total"]))
        binary_values.append(int(subject["binary_label"]))

    x = np.stack(x_rows, axis=0).astype(np.float32)
    return FeatureBundle(
        subject_ids=subject_ids,
        splits=np.asarray(split_values, dtype=object),
        y=np.asarray(y_values, dtype=np.float32),
        binary=np.asarray(binary_values, dtype=np.int64),
        x=x,
        text_dim=int(max_components),
        audio_dim=int(len(audio_suffixes)),
        tfidf_dim=int(train_tfidf.shape[1]),
        text_svd_dim=int(max_components),
        train_subject_count=len(train_subjects),
        validation_subject_count=len(validation_subjects),
    )


class GRURegressor(nn.Module):
    def __init__(self, input_dim: int, hidden_dim: int = 128, layers: int = 2, dropout: float = 0.5):
        super().__init__()
        self.norm = nn.LayerNorm(input_dim)
        self.gru = nn.GRU(
            input_size=input_dim,
            hidden_size=hidden_dim,
            num_layers=layers,
            dropout=dropout if layers > 1 else 0.0,
            batch_first=True,
            bidirectional=False,
        )
        self.head = nn.Sequential(
            nn.Dropout(dropout),
            nn.Linear(hidden_dim, hidden_dim),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(hidden_dim, 1),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        x = self.norm(x)
        out, _ = self.gru(x)
        pooled = out.mean(dim=1)
        return self.head(pooled).squeeze(-1)


class BiLSTMAttentionRegressor(nn.Module):
    def __init__(self, input_dim: int, hidden_dim: int = 128, layers: int = 2, dropout: float = 0.5):
        super().__init__()
        self.norm = nn.LayerNorm(input_dim)
        self.lstm = nn.LSTM(
            input_size=input_dim,
            hidden_size=hidden_dim,
            num_layers=layers,
            dropout=dropout if layers > 1 else 0.0,
            batch_first=True,
            bidirectional=True,
        )
        self.attention_layer = nn.Sequential(nn.Linear(hidden_dim, hidden_dim), nn.ReLU(inplace=True))
        self.head = nn.Sequential(
            nn.Dropout(dropout),
            nn.Linear(hidden_dim, hidden_dim),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(hidden_dim, 1),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        x = self.norm(x)
        output, (hidden, _) = self.lstm(x)
        forward_out, backward_out = torch.chunk(output, 2, dim=-1)
        h = forward_out + backward_out
        hidden = hidden.view(self.lstm.num_layers, 2, x.shape[0], self.lstm.hidden_size)
        hidden = hidden[-1].sum(dim=0)
        attention_query = self.attention_layer(hidden).unsqueeze(1)
        score = torch.bmm(attention_query, torch.tanh(h).transpose(1, 2))
        weights = torch.softmax(score, dim=-1)
        pooled = torch.bmm(weights, h).squeeze(1)
        return self.head(pooled).squeeze(-1)


def set_seed(seed: int) -> None:
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    torch.cuda.manual_seed_all(seed)
    torch.backends.cudnn.benchmark = False
    torch.backends.cudnn.deterministic = True


def augment_train(
    x: np.ndarray,
    y: np.ndarray,
    binary: np.ndarray,
    subject_ids: list[str],
) -> tuple[np.ndarray, np.ndarray, list[str]]:
    x_rows: list[np.ndarray] = []
    y_rows: list[float] = []
    source_subjects: list[str] = []
    for idx, subject_id in enumerate(subject_ids):
        if int(binary[idx]) == 1:
            for permutation in PERMUTATIONS:
                x_rows.append(x[idx, list(permutation), :])
                y_rows.append(float(y[idx]))
                source_subjects.append(subject_id)
        else:
            x_rows.append(x[idx])
            y_rows.append(float(y[idx]))
            source_subjects.append(subject_id)
    return np.stack(x_rows, axis=0).astype(np.float32), np.asarray(y_rows, dtype=np.float32), source_subjects


def train_one_model(
    model_name: str,
    seed: int,
    bundle: FeatureBundle,
    epochs: int,
    batch_size: int,
    learning_rate: float,
    weight_decay: float,
    device: torch.device,
) -> tuple[np.ndarray, dict[str, Any]]:
    set_seed(seed)
    train_mask = bundle.splits == "train"
    validation_mask = bundle.splits == "validation"
    train_indices = np.flatnonzero(train_mask)
    validation_indices = np.flatnonzero(validation_mask)
    train_subjects = [bundle.subject_ids[i] for i in train_indices]
    x_train, y_train, augmented_subjects = augment_train(
        bundle.x[train_indices],
        bundle.y[train_indices],
        bundle.binary[train_indices],
        train_subjects,
    )
    target_mean = float(np.mean(y_train))
    target_std = float(np.std(y_train))
    if target_std <= 0.0:
        raise ValueError("EATD train target standard deviation is zero")
    y_train_standardized = ((y_train - target_mean) / target_std).astype(np.float32)

    dataset = TensorDataset(torch.from_numpy(x_train), torch.from_numpy(y_train_standardized))
    generator = torch.Generator()
    generator.manual_seed(seed)
    loader = DataLoader(dataset, batch_size=batch_size, shuffle=True, generator=generator, drop_last=False)
    input_dim = int(bundle.x.shape[-1])
    if model_name == "gru":
        model: nn.Module = GRURegressor(input_dim=input_dim)
        display_model = "EATD official GRU"
        run_id = "eatd_public_gru"
    elif model_name == "bilstm":
        model = BiLSTMAttentionRegressor(input_dim=input_dim)
        display_model = "EATD official BiLSTM"
        run_id = "eatd_public_bilstm"
    else:
        raise ValueError(f"unknown model: {model_name}")
    model.to(device)
    optimizer = torch.optim.AdamW(model.parameters(), lr=learning_rate, weight_decay=weight_decay)
    criterion = nn.SmoothL1Loss()
    model.train()
    losses: list[float] = []
    for _ in range(epochs):
        epoch_losses: list[float] = []
        for xb, yb in loader:
            xb = xb.to(device)
            yb = yb.to(device)
            optimizer.zero_grad(set_to_none=True)
            pred = model(xb)
            loss = criterion(pred, yb)
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=5.0)
            optimizer.step()
            epoch_losses.append(float(loss.detach().cpu()))
        losses.append(float(np.mean(epoch_losses)))

    model.eval()
    with torch.no_grad():
        x_validation = torch.from_numpy(bundle.x[validation_indices]).to(device)
        pred_standardized = model(x_validation).detach().cpu().numpy().astype(np.float64)
    train_min = float(np.min(bundle.y[train_indices]))
    train_max = float(np.max(bundle.y[train_indices]))
    predictions = np.clip(pred_standardized * target_std + target_mean, train_min, train_max)
    summary = {
        "run_id": run_id,
        "model": display_model,
        "seed": seed,
        "epochs": epochs,
        "batch_size": batch_size,
        "learning_rate": learning_rate,
        "weight_decay": weight_decay,
        "final_train_loss": losses[-1] if losses else None,
        "target_mean": target_mean,
        "target_std": target_std,
        "train_target_min": train_min,
        "train_target_max": train_max,
        "augmented_train_rows": int(len(x_train)),
        "augmented_positive_subject_permutations": int(len(augmented_subjects) - len(train_subjects)),
    }
    return predictions, summary


def build_prediction_rows(
    bundle: FeatureBundle,
    model_name: str,
    seed: int,
    predictions: np.ndarray,
) -> list[dict[str, Any]]:
    validation_indices = np.flatnonzero(bundle.splits == "validation")
    if len(validation_indices) != len(predictions):
        raise ValueError("validation prediction length mismatch")
    if model_name == "gru":
        run_id = "eatd_public_gru"
        model = "EATD official GRU"
    else:
        run_id = "eatd_public_bilstm"
        model = "EATD official BiLSTM"
    rows: list[dict[str, Any]] = []
    for idx, pred in zip(validation_indices, predictions, strict=True):
        rows.append(
            {
                "run_id": run_id,
                "dataset": "EATD-Corpus",
                "modality": "Audio/Text",
                "task": "SDS regression",
                "model": model,
                "seed": seed,
                "task_type": "severity_regression",
                "subject_id": bundle.subject_ids[int(idx)],
                "split": "validation",
                "y_true": float(bundle.y[int(idx)]),
                "y_pred": float(pred),
                "y_score": np.nan,
                "feature_interface": "audited_eGeMAPS_plus_train_fit_char_tfidf_svd",
                "official_architecture_family": model_name,
                "prediction_clipped_to_train_target_range": True,
            }
        )
    return rows


def write_report(out_dir: Path, summary: dict[str, Any], metrics: pd.DataFrame) -> None:
    metric_lines = []
    for _, row in metrics.sort_values(["run_id", "metric"]).iterrows():
        metric_lines.append(
            f"- `{row['run_id']}` {row['metric']}: mean {float(row['mean']):.6f}, "
            f"std {float(row['std']):.6f}, CI95 [{float(row['ci95_low']):.6f}, {float(row['ci95_high']):.6f}]"
        )
    lines = [
        "# EATD Official GRU/BiLSTM-Style Public Reproduction",
        "",
        f"Generated: `{utc_now()}`",
        "",
        "Protocol:",
        "",
        "- Public source: `speechandlanguageprocessing/ICASSP2022-Depression`.",
        f"- Source commit: `{summary.get('official_source_commit')}`.",
        "- Official README split: 83 train subjects and 79 validation subjects.",
        "- Model families: GRU and BiLSTM attention recurrent networks over the three EATD emotional tasks.",
        "- Feature interface: audited openSMILE eGeMAPSv02 per-valence audio features plus train-fit char TF-IDF/SVD text embeddings.",
        "- Original ELMoForManyLangs and TensorFlow/VGGish/NetVLAD extraction code is not run in this Python 3.12/PyTorch 2.8 environment.",
        "- Five fixed seeds, no validation/test-label hyperparameter selection, no checkpoints saved.",
        "- Prediction artifacts contain no raw text, audio paths, or source paths.",
        "",
        "Audit summary:",
        "",
        f"- Subjects: {summary['subjects']} total, {summary['train_subjects']} train, {summary['validation_subjects']} validation.",
        f"- Sequence length: {summary['sequence_length']} emotional tasks ordered as {summary['valence_order']}.",
        f"- Audio feature dim: {summary['audio_feature_dim']}; text SVD dim: {summary['text_svd_dim']}; fused dim: {summary['fused_feature_dim']}.",
        f"- Prediction rows: {summary['prediction_rows']}.",
        "",
        "Metrics:",
        "",
        *metric_lines,
        "",
        "Artifacts:",
        "",
        "- `eatd_public_gru_bilstm_predictions.csv`",
        "- `phase2_metric_summary.csv`",
        "- `phase2_metrics_by_seed.csv`",
        "- `eatd_public_gru_bilstm_run_summary.json`",
        "- `eatd_public_gru_bilstm_feature_metadata.csv`",
    ]
    (out_dir / "eatd_public_gru_bilstm_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, default=MANIFEST_PATH)
    parser.add_argument("--audio-features", type=Path, default=AUDIO_FEATURES)
    parser.add_argument("--official-repo", type=Path, default=OFFICIAL_REPO)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--epochs", type=int, default=220)
    parser.add_argument("--batch-size", type=int, default=16)
    parser.add_argument("--learning-rate", type=float, default=1.0e-3)
    parser.add_argument("--weight-decay", type=float, default=1.0e-4)
    parser.add_argument("--text-svd-components", type=int, default=128)
    parser.add_argument("--bootstrap-resamples", type=int, default=1000)
    parser.add_argument("--device", default="cuda" if torch.cuda.is_available() else "cpu")
    args = parser.parse_args()

    args.out_dir.mkdir(parents=True, exist_ok=True)
    bundle = build_feature_bundle(args.manifest, args.audio_features, args.text_svd_components)
    device = torch.device(args.device)
    prediction_rows: list[dict[str, Any]] = []
    seed_summaries: list[dict[str, Any]] = []
    for seed in SEEDS:
        for model_name in ["gru", "bilstm"]:
            predictions, seed_summary = train_one_model(
                model_name=model_name,
                seed=seed,
                bundle=bundle,
                epochs=args.epochs,
                batch_size=args.batch_size,
                learning_rate=args.learning_rate,
                weight_decay=args.weight_decay,
                device=device,
            )
            prediction_rows.extend(build_prediction_rows(bundle, model_name, seed, predictions))
            seed_summaries.append(seed_summary)

    predictions = pd.DataFrame(prediction_rows)
    bad_columns = [column for column in predictions.columns if column.lower() in {"text", "audio_path", "text_path", "file_path"}]
    if bad_columns:
        raise ValueError(f"prediction output contains forbidden raw/path columns: {bad_columns}")
    predictions_path = args.out_dir / "eatd_public_gru_bilstm_predictions.csv"
    predictions.to_csv(predictions_path, index=False)
    per_seed, metric_summary = metric_records(predictions, args.bootstrap_resamples, seed=20260727)
    per_seed.to_csv(args.out_dir / "phase2_metrics_by_seed.csv", index=False)
    metric_summary.to_csv(args.out_dir / "phase2_metric_summary.csv", index=False)

    metadata = pd.DataFrame(
        {
            "subject_id": bundle.subject_ids,
            "split": bundle.splits,
            "sequence_length": len(VALENCE_ORDER),
            "audio_feature_dim": bundle.audio_dim,
            "text_svd_dim": bundle.text_svd_dim,
            "fused_feature_dim": bundle.x.shape[-1],
        }
    )
    metadata.to_csv(args.out_dir / "eatd_public_gru_bilstm_feature_metadata.csv", index=False)
    feature_cache_path = args.out_dir / "eatd_public_gru_bilstm_feature_sequences.npz"
    np.savez_compressed(
        feature_cache_path,
        x=bundle.x,
        y=bundle.y,
        splits=bundle.splits,
        subject_ids=np.asarray(bundle.subject_ids, dtype=object),
        valence_order=np.asarray(VALENCE_ORDER, dtype=object),
    )
    summary = {
        "generated_at": utc_now(),
        "official_source_url": "https://github.com/speechandlanguageprocessing/ICASSP2022-Depression",
        "official_source_commit": official_commit(args.official_repo),
        "paper_url": "https://arxiv.org/abs/2202.08210",
        "official_readme_split": {"train_subjects": 83, "validation_subjects": 79},
        "feature_interface": "audited_eGeMAPS_plus_train_fit_char_tfidf_svd",
        "original_feature_stack_not_run": [
            "ELMoForManyLangs zhs.model local absolute path",
            "TensorFlow v1 VGGish checkpoint/PCA",
            "NetVLAD loupe_keras audio embedding",
        ],
        "subjects": len(bundle.subject_ids),
        "train_subjects": bundle.train_subject_count,
        "validation_subjects": bundle.validation_subject_count,
        "sequence_length": len(VALENCE_ORDER),
        "valence_order": VALENCE_ORDER,
        "audio_feature_dim": bundle.audio_dim,
        "text_tfidf_dim": bundle.tfidf_dim,
        "text_svd_dim": bundle.text_svd_dim,
        "fused_feature_dim": int(bundle.x.shape[-1]),
        "seeds": SEEDS,
        "epochs": args.epochs,
        "batch_size": args.batch_size,
        "learning_rate": args.learning_rate,
        "weight_decay": args.weight_decay,
        "device": str(device),
        "prediction_rows": int(len(predictions)),
        "prediction_path": str(predictions_path),
        "feature_metadata_path": str(args.out_dir / "eatd_public_gru_bilstm_feature_metadata.csv"),
        "feature_cache_path": str(feature_cache_path),
        "seed_summaries": seed_summaries,
    }
    (args.out_dir / "eatd_public_gru_bilstm_run_summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    write_report(args.out_dir, summary, metric_summary)
    print(f"Wrote {predictions_path}")
    print(f"Wrote {args.out_dir / 'phase2_metric_summary.csv'}")
    print(f"Wrote {args.out_dir / 'eatd_public_gru_bilstm_report.md'}")


if __name__ == "__main__":
    main()
