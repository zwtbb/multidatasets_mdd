#!/usr/bin/env python3
"""Run MV26 depression-specific baseline stress tests.

MV26 adds two close baselines requested for the paper revision:

1. GNN-SDA-style semi-supervised domain adaptation for MDD.
2. QuestMF-style question-wise modality fusion with ordinal item loss.

Both are adapted to the same E-DAIC <-> CMDC PHQ shared-item contract used by
MV24. Each family is evaluated with a direct ordinary target head and with the
paper's measurement-aware target layer:

aligned representation -> aligned representation + corpus-specific ordinal
measurement pathway.

Tracked outputs are aggregate-only. Subject-level predictions, model weights,
raw media, transcripts, and feature matrices are not written.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import re
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def normalize_thread_env() -> None:
    for key in ["OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS"]:
        os.environ[key] = "1"


normalize_thread_env()

import numpy as np
import pandas as pd
import torch
import torch.nn as nn
import torch.nn.functional as F
from scipy import stats
from sklearn.decomposition import PCA
from sklearn.metrics import balanced_accuracy_score
from sklearn.model_selection import StratifiedKFold
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LogisticRegression


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "scripts"))

import phase5_run_mv24_measurement_aware_ordinal_model as mv24
import phase5_run_mv22_foundation_backbone_validation as mv22


DEFAULT_INPUT_ROOT = Path("/root/autodl-tmp")
DEFAULT_MANIFEST_DIR = DEFAULT_INPUT_ROOT / "datasets" / "manifests"
DEFAULT_OUT_DIR = (
    ROOT
    / "analysis"
    / "phase5_minimal_validation"
    / "p5_mv26_depression_specific_baselines"
    / "core_component"
)

FAMILIES = ("gnn_sda_style", "questmf_style")
METHOD_ORDER = [
    "gnn_sda_style_direct_head",
    "gnn_sda_style_measurement_aware",
    "questmf_style_direct_head",
    "questmf_style_measurement_aware",
]
METHOD_RANK = {method: rank for rank, method in enumerate(METHOD_ORDER)}
MEASUREMENT_PAIR = {
    "gnn_sda_style": ("gnn_sda_style_direct_head", "gnn_sda_style_measurement_aware"),
    "questmf_style": ("questmf_style_direct_head", "questmf_style_measurement_aware"),
}
METRIC_COLUMNS = list(mv24.METRIC_COLUMNS)
TRACKED_FILES = {
    "artifact_hygiene_audit.json",
    "baseline_contract.csv",
    "baseline_contract.md",
    "feature_asset_coverage.csv",
    "main_result_table.csv",
    "main_result_table.md",
    "metrics_by_seed.csv",
    "paired_measurement_layer_significance.csv",
    "report.md",
    "run_summary.json",
    "secondary_clinical_metrics_table.csv",
    "secondary_clinical_metrics_table.md",
    "summary_by_method.csv",
}
PHQ_SHARED_BINARY_THRESHOLD = mv24.PHQ_SHARED_BINARY_THRESHOLD
PHQ_ITEM_IDS = list(mv24.PHQ_ITEM_IDS)
DATASETS = mv24.DATASETS
TRANSFER_DIRECTIONS = mv24.TRANSFER_DIRECTIONS
EPS = 1e-8


@dataclass(frozen=True)
class PreparedPair:
    source_by_modality: dict[str, np.ndarray]
    target_by_modality: dict[str, np.ndarray]
    source_concat: np.ndarray
    target_concat: np.ndarray
    modality_dims: dict[str, int]
    pca_components_by_modality: dict[str, int]


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def git_commit() -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT, text=True).strip()
    except Exception:
        return "unknown"


def clean_tracked_outputs(out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    for name in TRACKED_FILES:
        path = out_dir / name
        if path.exists():
            path.unlink()


def device_from_arg(value: str) -> torch.device:
    if value == "auto":
        return torch.device("cuda" if torch.cuda.is_available() else "cpu")
    return torch.device(value)


def set_seed(seed: int) -> None:
    np.random.seed(int(seed))
    torch.manual_seed(int(seed))
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(int(seed))


def tensor(array: np.ndarray, device: torch.device, dtype: torch.dtype = torch.float32) -> torch.Tensor:
    return torch.as_tensor(array, dtype=dtype, device=device)


def modality_columns(feature_cols: list[str]) -> dict[str, list[str]]:
    prefixes = {
        "text": "text_qwen3__",
        "audio": "audio_wavlm_base_plus__",
        "video": "video_openface_common__",
    }
    grouped = {
        modality: [column for column in feature_cols if column.startswith(prefix)]
        for modality, prefix in prefixes.items()
    }
    missing = [modality for modality, columns in grouped.items() if not columns]
    if missing:
        raise ValueError(f"missing official MV24 modality columns: {missing}")
    return grouped


def prepare_modality_features(
    source: pd.DataFrame,
    target: pd.DataFrame,
    feature_cols: list[str],
    *,
    n_components: int,
    seed: int,
) -> PreparedPair:
    grouped_cols = modality_columns(feature_cols)
    source_by_modality: dict[str, np.ndarray] = {}
    target_by_modality: dict[str, np.ndarray] = {}
    pca_components_by_modality: dict[str, int] = {}
    for modality, columns in grouped_cols.items():
        source_x = source[columns].to_numpy(dtype=np.float64)
        target_x = target[columns].to_numpy(dtype=np.float64)
        scaler = StandardScaler().fit(source_x)
        source_scaled = scaler.transform(source_x)
        target_scaled = scaler.transform(target_x)
        max_components = min(int(n_components), source_scaled.shape[0] + target_scaled.shape[0] - 2, source_scaled.shape[1])
        if max_components < 1:
            raise ValueError(f"not enough rows to adapt {modality} features")
        if max_components >= source_scaled.shape[1]:
            source_part = source_scaled.astype(np.float32)
            target_part = target_scaled.astype(np.float32)
        else:
            pca = PCA(n_components=max_components, random_state=int(seed))
            pca.fit(np.vstack([source_scaled, target_scaled]))
            source_part = pca.transform(source_scaled).astype(np.float32)
            target_part = pca.transform(target_scaled).astype(np.float32)
        source_by_modality[modality] = source_part
        target_by_modality[modality] = target_part
        pca_components_by_modality[modality] = int(source_part.shape[1])
    modalities = ["text", "audio", "video"]
    source_concat = np.concatenate([source_by_modality[name] for name in modalities], axis=1).astype(np.float32)
    target_concat = np.concatenate([target_by_modality[name] for name in modalities], axis=1).astype(np.float32)
    return PreparedPair(
        source_by_modality=source_by_modality,
        target_by_modality=target_by_modality,
        source_concat=source_concat,
        target_concat=target_concat,
        modality_dims={name: int(source_by_modality[name].shape[1]) for name in modalities},
        pca_components_by_modality=pca_components_by_modality,
    )


def class_weights(labels: np.ndarray, beta: float) -> np.ndarray:
    labels = np.clip(np.rint(labels), 0, 3).astype(np.int64)
    weights = np.zeros((labels.shape[1], 4), dtype=np.float32)
    for item_idx in range(labels.shape[1]):
        counts = np.bincount(labels[:, item_idx], minlength=4).astype(np.float32)
        raw = ((float(labels.shape[0]) + 4.0) / (counts + 1.0)) ** float(beta)
        weights[item_idx] = raw / raw.mean()
    return weights.astype(np.float32)


def imboll_loss(
    logits: torch.Tensor,
    targets: torch.Tensor,
    weights: torch.Tensor,
    *,
    alpha: float,
    reduction: str = "mean",
) -> torch.Tensor:
    probabilities = F.softmax(logits, dim=-1)
    classes = torch.arange(logits.shape[-1], dtype=logits.dtype, device=logits.device).view(1, 1, -1)
    target_values = targets.to(dtype=logits.dtype).unsqueeze(-1)
    item_indices = torch.arange(targets.shape[1], device=targets.device).view(1, -1).expand_as(targets)
    target_weights = weights[item_indices, targets].to(dtype=logits.dtype).unsqueeze(-1)
    distances = torch.abs(classes - target_values).pow(float(alpha))
    per_class = -torch.log((1.0 - probabilities).clamp_min(EPS)) * distances * target_weights
    per_row = per_class.sum(dim=-1).mean(dim=-1)
    if reduction == "none":
        return per_row
    if reduction == "mean":
        return per_row.mean()
    raise ValueError(f"unknown reduction: {reduction}")


def weighted_ordinal_nll(probs: torch.Tensor, targets: torch.Tensor, weights: torch.Tensor | None = None) -> torch.Tensor:
    chosen = torch.gather(probs, dim=-1, index=targets.unsqueeze(-1)).squeeze(-1).clamp_min(EPS)
    per_item = -torch.log(chosen)
    if weights is not None:
        per_item = per_item * weights.unsqueeze(-1)
    return per_item.mean()


def expected_from_logits(logits: torch.Tensor) -> torch.Tensor:
    probs = F.softmax(logits, dim=-1)
    levels = torch.arange(logits.shape[-1], dtype=logits.dtype, device=logits.device)
    return torch.sum(probs * levels.view(1, 1, -1), dim=-1)


def probs_from_logits(logits: torch.Tensor) -> torch.Tensor:
    return F.softmax(logits, dim=-1).clamp_min(EPS)


def entropy_confidence(probs: torch.Tensor) -> torch.Tensor:
    entropy = -torch.sum(probs * torch.log(probs.clamp_min(EPS)), dim=-1) / math.log(float(probs.shape[-1]))
    return (1.0 - entropy).mean(dim=-1).clamp(0.0, 1.0)


def build_knn_graph(features: np.ndarray, *, k: int) -> np.ndarray:
    if len(features) < 2:
        return np.eye(len(features), dtype=np.float32)
    x = features.astype(np.float64)
    squared = np.sum((x[:, None, :] - x[None, :, :]) ** 2, axis=-1)
    positive = squared[squared > 0]
    sigma = float(np.median(positive)) if positive.size else 1.0
    sigma = max(sigma, 1e-6)
    n_rows = x.shape[0]
    adjacency = np.zeros((n_rows, n_rows), dtype=np.float64)
    neighbor_count = min(int(k), max(1, n_rows - 1))
    for row_idx in range(n_rows):
        neighbors = np.argsort(squared[row_idx], kind="mergesort")[1 : neighbor_count + 1]
        adjacency[row_idx, neighbors] = np.exp(-squared[row_idx, neighbors] / sigma)
    adjacency = np.maximum(adjacency, adjacency.T)
    adjacency += np.eye(n_rows, dtype=np.float64)
    degree = np.clip(adjacency.sum(axis=1), 1e-8, None)
    norm = adjacency / np.sqrt(degree[:, None] * degree[None, :])
    return norm.astype(np.float32)


def domain_identity_ba(source_repr: np.ndarray | None, target_repr: np.ndarray | None, seed: int) -> float:
    if source_repr is None or target_repr is None:
        return math.nan
    if len(source_repr) < 2 or len(target_repr) < 2:
        return math.nan
    labels = np.concatenate([np.zeros(len(source_repr), dtype=int), np.ones(len(target_repr), dtype=int)])
    features = np.vstack([source_repr, target_repr])
    min_count = int(np.bincount(labels).min())
    n_splits = min(5, min_count)
    if n_splits < 2:
        return math.nan
    scores: list[float] = []
    cv = StratifiedKFold(n_splits=n_splits, shuffle=True, random_state=int(seed))
    for train_idx, eval_idx in cv.split(features, labels):
        clf = make_pipeline(
            StandardScaler(),
            LogisticRegression(max_iter=2000, class_weight="balanced", solver="lbfgs"),
        )
        clf.fit(features[train_idx], labels[train_idx])
        pred = clf.predict(features[eval_idx])
        scores.append(float(balanced_accuracy_score(labels[eval_idx], pred)))
    return float(np.mean(scores))


class GradientReverse(torch.autograd.Function):
    @staticmethod
    def forward(ctx: Any, input_tensor: torch.Tensor, weight: float) -> torch.Tensor:
        ctx.weight = float(weight)
        return input_tensor.view_as(input_tensor)

    @staticmethod
    def backward(ctx: Any, grad_output: torch.Tensor) -> tuple[torch.Tensor, None]:
        return -ctx.weight * grad_output, None


class GnnSdaDirectNet(nn.Module):
    def __init__(self, input_dim: int, hidden_dim: int, n_items: int, dropout: float) -> None:
        super().__init__()
        self.encoder = nn.Sequential(
            nn.Linear(input_dim, hidden_dim),
            nn.GELU(),
            nn.Dropout(dropout),
            nn.LayerNorm(hidden_dim),
            nn.Linear(hidden_dim, hidden_dim),
            nn.GELU(),
        )
        self.graph_layer = nn.Sequential(nn.Linear(hidden_dim, hidden_dim), nn.GELU(), nn.LayerNorm(hidden_dim))
        self.item_head = nn.Linear(hidden_dim, n_items * 4)
        self.domain_head = nn.Linear(hidden_dim, 2)
        self.n_items = int(n_items)

    def representations(self, inputs: torch.Tensor, adjacency: torch.Tensor) -> torch.Tensor:
        hidden = self.encoder(inputs)
        propagated = torch.matmul(adjacency, hidden)
        return self.graph_layer(propagated) + hidden

    def forward(self, inputs: torch.Tensor, adjacency: torch.Tensor, grl_weight: float = 0.0) -> tuple[torch.Tensor, torch.Tensor]:
        rep = self.representations(inputs, adjacency)
        logits = self.item_head(rep).view(-1, self.n_items, 4)
        domain_logits = self.domain_head(GradientReverse.apply(rep, grl_weight))
        return logits, domain_logits


class GnnSdaMeasurementNet(nn.Module):
    def __init__(self, input_dim: int, hidden_dim: int, symptom_dim: int, dropout: float) -> None:
        super().__init__()
        self.encoder = nn.Sequential(
            nn.Linear(input_dim, hidden_dim),
            nn.GELU(),
            nn.Dropout(dropout),
            nn.LayerNorm(hidden_dim),
            nn.Linear(hidden_dim, hidden_dim),
            nn.GELU(),
        )
        self.graph_layer = nn.Sequential(nn.Linear(hidden_dim, hidden_dim), nn.GELU(), nn.LayerNorm(hidden_dim))
        self.symptom_layer = nn.Linear(hidden_dim, symptom_dim)
        self.heads = nn.ModuleDict({dataset: mv24.CorpusOrdinalHead(symptom_dim) for dataset in DATASETS})
        self.domain_head = nn.Linear(hidden_dim, 2)

    def hidden(self, inputs: torch.Tensor, adjacency: torch.Tensor) -> torch.Tensor:
        base = self.encoder(inputs)
        propagated = torch.matmul(adjacency, base)
        return self.graph_layer(propagated) + base

    def symptom_scores(self, inputs: torch.Tensor, adjacency: torch.Tensor) -> torch.Tensor:
        return self.symptom_layer(self.hidden(inputs, adjacency))

    def forward(
        self,
        inputs: torch.Tensor,
        adjacency: torch.Tensor,
        corpus_id: str,
        grl_weight: float = 0.0,
    ) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor, torch.Tensor]:
        hidden = self.hidden(inputs, adjacency)
        symptoms = self.symptom_layer(hidden)
        probs, expected = self.heads[corpus_id](symptoms)
        domain_logits = self.domain_head(GradientReverse.apply(hidden, grl_weight))
        return hidden, symptoms, probs, expected, domain_logits


class QuestMFDirectNet(nn.Module):
    def __init__(self, modality_dims: dict[str, int], hidden_dim: int, n_items: int, dropout: float) -> None:
        super().__init__()
        self.modalities = ["text", "audio", "video"]
        self.encoders = nn.ModuleDict(
            {
                name: nn.Sequential(
                    nn.Linear(modality_dims[name], hidden_dim),
                    nn.GELU(),
                    nn.Dropout(dropout),
                    nn.LayerNorm(hidden_dim),
                )
                for name in self.modalities
            }
        )
        self.gates = nn.ModuleList([nn.Linear(hidden_dim * len(self.modalities), len(self.modalities)) for _ in range(n_items)])
        self.item_heads = nn.ModuleList([nn.Linear(hidden_dim, 4) for _ in range(n_items)])
        self.n_items = int(n_items)

    def item_representations(self, inputs: dict[str, torch.Tensor]) -> tuple[torch.Tensor, torch.Tensor]:
        encoded = [self.encoders[name](inputs[name]) for name in self.modalities]
        stacked = torch.stack(encoded, dim=1)
        context = torch.cat(encoded, dim=1)
        reps: list[torch.Tensor] = []
        gate_values: list[torch.Tensor] = []
        for gate in self.gates:
            weights = F.softmax(gate(context), dim=-1)
            reps.append(torch.sum(stacked * weights.unsqueeze(-1), dim=1))
            gate_values.append(weights)
        return torch.stack(reps, dim=1), torch.stack(gate_values, dim=1)

    def forward(self, inputs: dict[str, torch.Tensor]) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
        item_repr, gates = self.item_representations(inputs)
        logits = torch.stack([head(item_repr[:, idx, :]) for idx, head in enumerate(self.item_heads)], dim=1)
        return logits, item_repr, gates


class QuestMFMeasurementNet(nn.Module):
    def __init__(self, modality_dims: dict[str, int], hidden_dim: int, symptom_dim: int, dropout: float) -> None:
        super().__init__()
        self.modalities = ["text", "audio", "video"]
        self.encoders = nn.ModuleDict(
            {
                name: nn.Sequential(
                    nn.Linear(modality_dims[name], hidden_dim),
                    nn.GELU(),
                    nn.Dropout(dropout),
                    nn.LayerNorm(hidden_dim),
                )
                for name in self.modalities
            }
        )
        self.gates = nn.ModuleList([nn.Linear(hidden_dim * len(self.modalities), len(self.modalities)) for _ in range(symptom_dim)])
        self.symptom_scores_by_item = nn.ModuleList([nn.Linear(hidden_dim, 1) for _ in range(symptom_dim)])
        self.heads = nn.ModuleDict({dataset: mv24.CorpusOrdinalHead(symptom_dim) for dataset in DATASETS})
        self.symptom_dim = int(symptom_dim)

    def item_representations(self, inputs: dict[str, torch.Tensor]) -> tuple[torch.Tensor, torch.Tensor]:
        encoded = [self.encoders[name](inputs[name]) for name in self.modalities]
        stacked = torch.stack(encoded, dim=1)
        context = torch.cat(encoded, dim=1)
        reps: list[torch.Tensor] = []
        gate_values: list[torch.Tensor] = []
        for gate in self.gates:
            weights = F.softmax(gate(context), dim=-1)
            reps.append(torch.sum(stacked * weights.unsqueeze(-1), dim=1))
            gate_values.append(weights)
        return torch.stack(reps, dim=1), torch.stack(gate_values, dim=1)

    def symptom_scores(self, inputs: dict[str, torch.Tensor]) -> torch.Tensor:
        item_repr, _ = self.item_representations(inputs)
        scores = [layer(item_repr[:, idx, :]).squeeze(-1) for idx, layer in enumerate(self.symptom_scores_by_item)]
        return torch.stack(scores, dim=1)

    def forward(self, inputs: dict[str, torch.Tensor], corpus_id: str) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor, torch.Tensor]:
        item_repr, gates = self.item_representations(inputs)
        scores = [layer(item_repr[:, idx, :]).squeeze(-1) for idx, layer in enumerate(self.symptom_scores_by_item)]
        symptoms = torch.stack(scores, dim=1)
        probs, expected = self.heads[corpus_id](symptoms)
        return symptoms, probs, expected, item_repr.mean(dim=1)


def input_dict(arrays: dict[str, np.ndarray], device: torch.device) -> dict[str, torch.Tensor]:
    return {name: tensor(value, device) for name, value in arrays.items()}


def subset_input_dict(inputs: dict[str, torch.Tensor], indices: torch.Tensor) -> dict[str, torch.Tensor]:
    return {name: value[indices] for name, value in inputs.items()}


def numpy_input_subset(arrays: dict[str, np.ndarray], indices: np.ndarray) -> dict[str, np.ndarray]:
    return {name: value[indices] for name, value in arrays.items()}


def train_gnn_sda_direct(
    source_x: np.ndarray,
    source_y: np.ndarray,
    target_x_all: np.ndarray,
    target_y_all: np.ndarray,
    target_calib_idx: np.ndarray,
    *,
    seed: int,
    args: argparse.Namespace,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    set_seed(seed)
    device = device_from_arg(args.device)
    x_all = np.vstack([source_x, target_x_all]).astype(np.float32)
    adjacency = tensor(build_knn_graph(x_all, k=args.gnn_k), device)
    xs_all = tensor(x_all, device)
    ys = tensor(source_y, device, dtype=torch.long)
    yt = tensor(target_y_all, device, dtype=torch.long)
    target_calib = torch.as_tensor(target_calib_idx, dtype=torch.long, device=device)
    source_indices = torch.arange(len(source_x), dtype=torch.long, device=device)
    target_indices = torch.arange(len(target_x_all), dtype=torch.long, device=device) + len(source_x)
    target_calib_indices = target_calib + len(source_x)
    unlabeled_mask = torch.ones(len(target_x_all), dtype=torch.bool, device=device)
    unlabeled_mask[target_calib] = False
    target_unlabeled_indices = target_indices[unlabeled_mask]
    domain_labels = torch.cat(
        [
            torch.zeros(len(source_x), dtype=torch.long, device=device),
            torch.ones(len(target_x_all), dtype=torch.long, device=device),
        ]
    )
    supervised_weights = tensor(class_weights(np.vstack([source_y, target_y_all[target_calib_idx]]), args.imboll_beta), device)
    source_prior = F.one_hot(ys, num_classes=4).float().mean(dim=0).clamp_min(EPS)
    model = GnnSdaDirectNet(source_x.shape[1], args.hidden_dim, source_y.shape[1], args.dropout).to(device)
    optimizer = torch.optim.AdamW(model.parameters(), lr=args.learning_rate, weight_decay=args.weight_decay)
    for epoch in range(int(args.gnn_epochs)):
        optimizer.zero_grad(set_to_none=True)
        progress = float(epoch + 1) / float(max(1, args.gnn_epochs))
        grl_weight = float(args.domain_loss_weight) * (2.0 / (1.0 + math.exp(-10.0 * progress)) - 1.0)
        logits, domain_logits = model(xs_all, adjacency, grl_weight)
        loss = imboll_loss(logits[source_indices], ys, supervised_weights, alpha=args.imboll_alpha)
        loss = loss + float(args.target_calibration_weight) * imboll_loss(
            logits[target_calib_indices],
            yt[target_calib],
            supervised_weights,
            alpha=args.imboll_alpha,
        )
        loss = loss + float(args.domain_loss_weight) * F.cross_entropy(domain_logits, domain_labels)
        if epoch >= int(args.pseudo_warmup_epochs) and len(target_unlabeled_indices) > 0:
            with torch.no_grad():
                probs_u = probs_from_logits(logits[target_unlabeled_indices])
                pseudo = probs_u.argmax(dim=-1)
                confidence = entropy_confidence(probs_u)
                keep = confidence > float(args.pseudo_confidence_threshold)
            if int(keep.sum().item()) > 0:
                pseudo_loss = imboll_loss(
                    logits[target_unlabeled_indices][keep],
                    pseudo[keep],
                    supervised_weights,
                    alpha=args.imboll_alpha,
                    reduction="none",
                )
                weights = confidence[keep].detach()
                loss = loss + float(args.pseudo_loss_weight) * torch.mean(pseudo_loss * weights)
            probs_target = probs_from_logits(logits[target_indices])
            mean_target = probs_target.mean(dim=0).clamp_min(EPS)
            loss = loss + float(args.class_balance_weight) * F.kl_div(mean_target.log(), source_prior, reduction="batchmean")
        loss.backward()
        torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
        optimizer.step()
    model.eval()
    with torch.inference_mode():
        logits, _ = model(xs_all, adjacency, 0.0)
        probs = probs_from_logits(logits)
        expected = expected_from_logits(logits)
        rep = model.representations(xs_all, adjacency)
    return (
        expected[target_indices].detach().cpu().numpy().astype(np.float32),
        expected[source_indices].detach().cpu().numpy().astype(np.float32),
        probs[target_indices].detach().cpu().numpy().astype(np.float32),
        rep[source_indices].detach().cpu().numpy().astype(np.float32),
        rep[target_indices].detach().cpu().numpy().astype(np.float32),
    )


def train_gnn_sda_measurement(
    source_dataset: str,
    target_dataset: str,
    source_x: np.ndarray,
    source_y: np.ndarray,
    target_x_all: np.ndarray,
    target_y_all: np.ndarray,
    target_calib_idx: np.ndarray,
    *,
    seed: int,
    args: argparse.Namespace,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    set_seed(seed)
    device = device_from_arg(args.device)
    x_all = np.vstack([source_x, target_x_all]).astype(np.float32)
    adjacency = tensor(build_knn_graph(x_all, k=args.gnn_k), device)
    xs_all = tensor(x_all, device)
    ys = tensor(source_y, device, dtype=torch.long)
    yt = tensor(target_y_all, device, dtype=torch.long)
    target_calib = torch.as_tensor(target_calib_idx, dtype=torch.long, device=device)
    source_indices = torch.arange(len(source_x), dtype=torch.long, device=device)
    target_indices = torch.arange(len(target_x_all), dtype=torch.long, device=device) + len(source_x)
    target_calib_indices = target_calib + len(source_x)
    unlabeled_mask = torch.ones(len(target_x_all), dtype=torch.bool, device=device)
    unlabeled_mask[target_calib] = False
    target_unlabeled_indices = target_indices[unlabeled_mask]
    domain_labels = torch.cat(
        [
            torch.zeros(len(source_x), dtype=torch.long, device=device),
            torch.ones(len(target_x_all), dtype=torch.long, device=device),
        ]
    )
    model = GnnSdaMeasurementNet(source_x.shape[1], args.hidden_dim, source_y.shape[1], args.dropout).to(device)

    def initialize_target_head_from_source() -> None:
        model.heads[target_dataset].load_state_dict(model.heads[source_dataset].state_dict())

    optimizer = torch.optim.AdamW(model.parameters(), lr=args.learning_rate, weight_decay=args.weight_decay)
    for _ in range(int(args.gnn_source_warmup_epochs)):
        optimizer.zero_grad(set_to_none=True)
        _, _, source_probs, _, _ = model(xs_all, adjacency, source_dataset, 0.0)
        loss = mv24.ordinal_nll(source_probs[source_indices], ys)
        loss.backward()
        torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
        optimizer.step()
    initialize_target_head_from_source()
    optimizer = torch.optim.AdamW(model.parameters(), lr=args.learning_rate, weight_decay=args.weight_decay)
    for epoch in range(int(args.gnn_epochs)):
        optimizer.zero_grad(set_to_none=True)
        progress = float(epoch + 1) / float(max(1, args.gnn_epochs))
        grl_weight = float(args.domain_loss_weight) * (2.0 / (1.0 + math.exp(-10.0 * progress)) - 1.0)
        hidden, symptoms, source_probs, _, domain_logits = model(xs_all, adjacency, source_dataset, grl_weight)
        _, _, target_probs, _, _ = model(xs_all, adjacency, target_dataset, 0.0)
        loss = mv24.ordinal_nll(source_probs[source_indices], ys)
        loss = loss + float(args.target_calibration_weight) * mv24.ordinal_nll(target_probs[target_calib_indices], yt[target_calib])
        loss = loss + float(args.domain_loss_weight) * F.cross_entropy(domain_logits, domain_labels)
        loss = loss + float(args.latent_mmd_weight) * mv24.rbf_mmd(symptoms[source_indices], symptoms[target_indices])
        loss = loss + float(args.latent_l2_weight) * (symptoms[source_indices].pow(2).mean() + symptoms[target_indices].pow(2).mean())
        if epoch >= int(args.pseudo_warmup_epochs) and len(target_unlabeled_indices) > 0:
            with torch.no_grad():
                probs_u = target_probs[target_unlabeled_indices]
                pseudo = probs_u.argmax(dim=-1)
                confidence = entropy_confidence(probs_u)
                keep = confidence > float(args.pseudo_confidence_threshold)
            if int(keep.sum().item()) > 0:
                chosen = torch.gather(
                    target_probs[target_unlabeled_indices][keep],
                    dim=-1,
                    index=pseudo[keep].unsqueeze(-1),
                ).squeeze(-1)
                pseudo_loss = -torch.log(chosen.clamp_min(EPS)).mean(dim=-1)
                loss = loss + float(args.pseudo_loss_weight) * torch.mean(pseudo_loss * confidence[keep].detach())
        loss.backward()
        torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
        optimizer.step()
    model.eval()
    with torch.inference_mode():
        hidden, symptoms, source_probs, source_expected, _ = model(xs_all, adjacency, source_dataset, 0.0)
        _, _, target_probs, target_expected, _ = model(xs_all, adjacency, target_dataset, 0.0)
    return (
        target_expected[target_indices].detach().cpu().numpy().astype(np.float32),
        source_expected[source_indices].detach().cpu().numpy().astype(np.float32),
        target_probs[target_indices].detach().cpu().numpy().astype(np.float32),
        hidden[source_indices].detach().cpu().numpy().astype(np.float32),
        hidden[target_indices].detach().cpu().numpy().astype(np.float32),
        symptoms[source_indices].detach().cpu().numpy().astype(np.float32),
        symptoms[target_indices].detach().cpu().numpy().astype(np.float32),
    )


def train_questmf_direct(
    source_by_modality: dict[str, np.ndarray],
    source_y: np.ndarray,
    target_by_modality: dict[str, np.ndarray],
    target_y_all: np.ndarray,
    target_calib_idx: np.ndarray,
    *,
    seed: int,
    args: argparse.Namespace,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    set_seed(seed)
    device = device_from_arg(args.device)
    source_inputs = input_dict(source_by_modality, device)
    target_inputs = input_dict(target_by_modality, device)
    ys = tensor(source_y, device, dtype=torch.long)
    yt = tensor(target_y_all, device, dtype=torch.long)
    target_calib = torch.as_tensor(target_calib_idx, dtype=torch.long, device=device)
    weights = tensor(class_weights(np.vstack([source_y, target_y_all[target_calib_idx]]), args.imboll_beta), device)
    model = QuestMFDirectNet(
        {name: value.shape[1] for name, value in source_by_modality.items()},
        args.hidden_dim,
        source_y.shape[1],
        args.dropout,
    ).to(device)
    optimizer = torch.optim.AdamW(model.parameters(), lr=args.learning_rate, weight_decay=args.weight_decay)
    for _ in range(int(args.questmf_epochs)):
        optimizer.zero_grad(set_to_none=True)
        source_logits, _, _ = model(source_inputs)
        target_logits, _, _ = model(target_inputs)
        loss = imboll_loss(source_logits, ys, weights, alpha=args.imboll_alpha)
        loss = loss + float(args.target_calibration_weight) * imboll_loss(
            target_logits[target_calib],
            yt[target_calib],
            weights,
            alpha=args.imboll_alpha,
        )
        loss.backward()
        torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
        optimizer.step()
    model.eval()
    with torch.inference_mode():
        source_logits, source_item_repr, _ = model(source_inputs)
        target_logits, target_item_repr, _ = model(target_inputs)
        source_probs = probs_from_logits(source_logits)
        target_probs = probs_from_logits(target_logits)
        source_expected = expected_from_logits(source_logits)
        target_expected = expected_from_logits(target_logits)
    return (
        target_expected.detach().cpu().numpy().astype(np.float32),
        source_expected.detach().cpu().numpy().astype(np.float32),
        target_probs.detach().cpu().numpy().astype(np.float32),
        source_item_repr.mean(dim=1).detach().cpu().numpy().astype(np.float32),
        target_item_repr.mean(dim=1).detach().cpu().numpy().astype(np.float32),
    )


def train_questmf_measurement(
    source_dataset: str,
    target_dataset: str,
    source_by_modality: dict[str, np.ndarray],
    source_y: np.ndarray,
    target_by_modality: dict[str, np.ndarray],
    target_y_all: np.ndarray,
    target_calib_idx: np.ndarray,
    *,
    seed: int,
    args: argparse.Namespace,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    set_seed(seed)
    device = device_from_arg(args.device)
    source_inputs = input_dict(source_by_modality, device)
    target_inputs = input_dict(target_by_modality, device)
    ys = tensor(source_y, device, dtype=torch.long)
    yt = tensor(target_y_all, device, dtype=torch.long)
    target_calib = torch.as_tensor(target_calib_idx, dtype=torch.long, device=device)
    model = QuestMFMeasurementNet(
        {name: value.shape[1] for name, value in source_by_modality.items()},
        args.hidden_dim,
        source_y.shape[1],
        args.dropout,
    ).to(device)

    def initialize_target_head_from_source() -> None:
        model.heads[target_dataset].load_state_dict(model.heads[source_dataset].state_dict())

    optimizer = torch.optim.AdamW(model.parameters(), lr=args.learning_rate, weight_decay=args.weight_decay)
    for _ in range(int(args.questmf_source_warmup_epochs)):
        optimizer.zero_grad(set_to_none=True)
        _, source_probs, _, _ = model(source_inputs, source_dataset)
        loss = mv24.ordinal_nll(source_probs, ys)
        loss.backward()
        torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
        optimizer.step()
    initialize_target_head_from_source()
    optimizer = torch.optim.AdamW(model.parameters(), lr=args.learning_rate, weight_decay=args.weight_decay)
    for _ in range(int(args.questmf_epochs)):
        optimizer.zero_grad(set_to_none=True)
        source_sym, source_probs, _, _ = model(source_inputs, source_dataset)
        target_sym, target_probs, _, _ = model(target_inputs, target_dataset)
        loss = mv24.ordinal_nll(source_probs, ys)
        loss = loss + float(args.target_calibration_weight) * mv24.ordinal_nll(target_probs[target_calib], yt[target_calib])
        loss = loss + float(args.latent_mmd_weight) * mv24.rbf_mmd(source_sym, target_sym)
        loss = loss + float(args.latent_l2_weight) * (source_sym.pow(2).mean() + target_sym.pow(2).mean())
        loss.backward()
        torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
        optimizer.step()
    model.eval()
    with torch.inference_mode():
        source_sym, source_probs, source_expected, source_repr = model(source_inputs, source_dataset)
        target_sym, target_probs, target_expected, target_repr = model(target_inputs, target_dataset)
    return (
        target_expected.detach().cpu().numpy().astype(np.float32),
        source_expected.detach().cpu().numpy().astype(np.float32),
        target_probs.detach().cpu().numpy().astype(np.float32),
        source_sym.detach().cpu().numpy().astype(np.float32),
        target_sym.detach().cpu().numpy().astype(np.float32),
    )


def add_metric_row(
    *,
    source_dataset: str,
    target_dataset: str,
    method: str,
    family: str,
    seed: int,
    source_n: int,
    target_calib_n: int,
    target_eval_n: int,
    input_columns: int,
    modality_dims: dict[str, int],
    pred_all: np.ndarray,
    source_pred: np.ndarray,
    probs_all: np.ndarray,
    truth_all: np.ndarray,
    target_eval_idx: np.ndarray,
    feature_source_repr: np.ndarray,
    feature_target_repr: np.ndarray,
    latent_source_repr: np.ndarray,
    latent_target_repr: np.ndarray,
    training_contract: str,
) -> dict[str, Any]:
    pred = pred_all[target_eval_idx]
    truth = truth_all[target_eval_idx]
    probs = probs_all[target_eval_idx] if probs_all is not None else None
    row = {
        "view_id": mv24.official_view().view_id,
        "modality_set": mv24.official_view().modality_set,
        "transfer_id": f"{source_dataset}_to_{target_dataset}_phq_shared",
        "source_dataset": source_dataset,
        "target_dataset": target_dataset,
        "baseline_family": family,
        "method": method,
        "method_rank": METHOD_RANK[method],
        "seed": int(seed),
        "source_participant_count": int(source_n),
        "target_calibration_count": int(target_calib_n),
        "target_evaluation_count": int(target_eval_n),
        "input_columns": int(input_columns),
        "representation_columns": int(sum(modality_dims.values())),
        "text_components": int(modality_dims["text"]),
        "audio_components": int(modality_dims["audio"]),
        "video_components": int(modality_dims["video"]),
        "target_calibration_labels_used": True,
        "training_contract": training_contract,
        "feature_domain_identity_ba": domain_identity_ba(feature_source_repr, feature_target_repr[target_eval_idx], seed),
        "latent_domain_identity_ba": domain_identity_ba(latent_source_repr, latent_target_repr[target_eval_idx], seed),
        "post_head_domain_identity_ba": domain_identity_ba(source_pred, pred, seed),
        "ordinal_nll": mv24.ordinal_nll_from_probs(probs, truth),
    }
    row.update(mv24.evaluate_predictions(pred, truth))
    return row


def run_transfer_direction(
    source_dataset: str,
    target_dataset: str,
    tables: dict[str, pd.DataFrame],
    feature_cols: list[str],
    args: argparse.Namespace,
) -> list[dict[str, Any]]:
    raw_source = tables[source_dataset].copy()
    raw_target = tables[target_dataset].copy()
    raw_source, raw_target = mv24.sanitize_pair(raw_source, raw_target, feature_cols)
    source_y = mv24.label_arrays(raw_source)
    target_y_all = mv24.label_arrays(raw_target)
    rows: list[dict[str, Any]] = []
    selected_methods = set(args.methods)
    for seed in [int(seed) for seed in args.seeds]:
        target_calib_idx, target_eval_idx = mv24.calibration_split_indices(
            target_y_all,
            seed,
            fraction=args.target_calibration_fraction,
            minimum=args.target_calibration_min,
        )
        prepared = prepare_modality_features(
            raw_source,
            raw_target,
            feature_cols,
            n_components=args.modality_pca_components,
            seed=seed,
        )
        if "gnn_sda_style_direct_head" in selected_methods:
            pred_all, source_pred, probs_all, source_repr, target_repr = train_gnn_sda_direct(
                prepared.source_concat,
                source_y,
                prepared.target_concat,
                target_y_all,
                target_calib_idx,
                seed=seed,
                args=args,
            )
            rows.append(
                add_metric_row(
                    source_dataset=source_dataset,
                    target_dataset=target_dataset,
                    method="gnn_sda_style_direct_head",
                    family="gnn_sda_style",
                    seed=seed,
                    source_n=len(raw_source),
                    target_calib_n=len(target_calib_idx),
                    target_eval_n=len(target_eval_idx),
                    input_columns=len(feature_cols),
                    modality_dims=prepared.modality_dims,
                    pred_all=pred_all,
                    source_pred=source_pred,
                    probs_all=probs_all,
                    truth_all=target_y_all,
                    target_eval_idx=target_eval_idx,
                    feature_source_repr=prepared.source_concat,
                    feature_target_repr=prepared.target_concat,
                    latent_source_repr=source_repr,
                    latent_target_repr=target_repr,
                    training_contract=(
                        "GNN-SDA-style graph propagation, adversarial domain alignment, "
                        "uncertainty-weighted target pseudo-labeling, and a shared direct ordinal item head"
                    ),
                )
            )
        if "gnn_sda_style_measurement_aware" in selected_methods:
            pred_all, source_pred, probs_all, hidden_s, hidden_t, sym_s, sym_t = train_gnn_sda_measurement(
                source_dataset,
                target_dataset,
                prepared.source_concat,
                source_y,
                prepared.target_concat,
                target_y_all,
                target_calib_idx,
                seed=seed,
                args=args,
            )
            rows.append(
                add_metric_row(
                    source_dataset=source_dataset,
                    target_dataset=target_dataset,
                    method="gnn_sda_style_measurement_aware",
                    family="gnn_sda_style",
                    seed=seed,
                    source_n=len(raw_source),
                    target_calib_n=len(target_calib_idx),
                    target_eval_n=len(target_eval_idx),
                    input_columns=len(feature_cols),
                    modality_dims=prepared.modality_dims,
                    pred_all=pred_all,
                    source_pred=source_pred,
                    probs_all=probs_all,
                    truth_all=target_y_all,
                    target_eval_idx=target_eval_idx,
                    feature_source_repr=prepared.source_concat,
                    feature_target_repr=prepared.target_concat,
                    latent_source_repr=sym_s,
                    latent_target_repr=sym_t,
                    training_contract=(
                        "GNN-SDA-style graph propagation and domain adaptation with the paper's "
                        "shared symptom layer plus corpus-specific cumulative ordinal measurement heads"
                    ),
                )
            )
        if "questmf_style_direct_head" in selected_methods:
            pred_all, source_pred, probs_all, source_repr, target_repr = train_questmf_direct(
                prepared.source_by_modality,
                source_y,
                prepared.target_by_modality,
                target_y_all,
                target_calib_idx,
                seed=seed,
                args=args,
            )
            rows.append(
                add_metric_row(
                    source_dataset=source_dataset,
                    target_dataset=target_dataset,
                    method="questmf_style_direct_head",
                    family="questmf_style",
                    seed=seed,
                    source_n=len(raw_source),
                    target_calib_n=len(target_calib_idx),
                    target_eval_n=len(target_eval_idx),
                    input_columns=len(feature_cols),
                    modality_dims=prepared.modality_dims,
                    pred_all=pred_all,
                    source_pred=source_pred,
                    probs_all=probs_all,
                    truth_all=target_y_all,
                    target_eval_idx=target_eval_idx,
                    feature_source_repr=prepared.source_concat,
                    feature_target_repr=prepared.target_concat,
                    latent_source_repr=source_repr,
                    latent_target_repr=target_repr,
                    training_contract=(
                        "QuestMF-style question-wise modality fusion over Qwen3 text, WavLM audio, "
                        "and OpenFace video features, trained with Imbalanced Ordinal Log-Loss and a direct item head"
                    ),
                )
            )
        if "questmf_style_measurement_aware" in selected_methods:
            pred_all, source_pred, probs_all, sym_s, sym_t = train_questmf_measurement(
                source_dataset,
                target_dataset,
                prepared.source_by_modality,
                source_y,
                prepared.target_by_modality,
                target_y_all,
                target_calib_idx,
                seed=seed,
                args=args,
            )
            rows.append(
                add_metric_row(
                    source_dataset=source_dataset,
                    target_dataset=target_dataset,
                    method="questmf_style_measurement_aware",
                    family="questmf_style",
                    seed=seed,
                    source_n=len(raw_source),
                    target_calib_n=len(target_calib_idx),
                    target_eval_n=len(target_eval_idx),
                    input_columns=len(feature_cols),
                    modality_dims=prepared.modality_dims,
                    pred_all=pred_all,
                    source_pred=source_pred,
                    probs_all=probs_all,
                    truth_all=target_y_all,
                    target_eval_idx=target_eval_idx,
                    feature_source_repr=prepared.source_concat,
                    feature_target_repr=prepared.target_concat,
                    latent_source_repr=sym_s,
                    latent_target_repr=sym_t,
                    training_contract=(
                        "QuestMF-style question-wise modality fusion with the paper's shared symptom scores "
                        "and corpus-specific cumulative ordinal measurement heads"
                    ),
                )
            )
    return rows


def summarize_metrics(metrics: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    grouped = metrics.groupby(["transfer_id", "baseline_family", "method", "method_rank"], dropna=False)
    for (transfer_id, family, method, method_rank), group in grouped:
        row: dict[str, Any] = {
            "transfer_id": transfer_id,
            "baseline_family": family,
            "method": method,
            "method_rank": int(method_rank),
            "seed_count": int(group["seed"].nunique()),
            "source_participant_count": int(round(group["source_participant_count"].mean())),
            "target_calibration_count": int(round(group["target_calibration_count"].mean())),
            "target_evaluation_count": int(round(group["target_evaluation_count"].mean())),
            "input_columns": int(group["input_columns"].max()),
            "representation_columns": int(group["representation_columns"].max()),
            "text_components": int(group["text_components"].max()),
            "audio_components": int(group["audio_components"].max()),
            "video_components": int(group["video_components"].max()),
            "target_calibration_labels_used": True,
        }
        for metric in METRIC_COLUMNS:
            values = pd.to_numeric(group[metric], errors="coerce").dropna().to_numpy(dtype=np.float64)
            if len(values) == 0:
                row[f"{metric}_mean"] = math.nan
                row[f"{metric}_std"] = math.nan
                row[f"{metric}_ci95_low"] = math.nan
                row[f"{metric}_ci95_high"] = math.nan
                continue
            mean = float(values.mean())
            std = float(values.std(ddof=1)) if len(values) > 1 else 0.0
            half_width = float(stats.t.ppf(0.975, len(values) - 1) * std / math.sqrt(len(values))) if len(values) > 1 else 0.0
            row[f"{metric}_mean"] = mean
            row[f"{metric}_std"] = std
            row[f"{metric}_ci95_low"] = mean - half_width
            row[f"{metric}_ci95_high"] = mean + half_width
        rows.append(row)
    return pd.DataFrame(rows).sort_values(["transfer_id", "method_rank"]).reset_index(drop=True)


def paired_measurement_layer_significance(metrics: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for transfer_id, transfer_group in metrics.groupby("transfer_id", dropna=False):
        for family, (direct_method, aware_method) in MEASUREMENT_PAIR.items():
            direct = transfer_group[transfer_group["method"] == direct_method].set_index("seed")
            aware = transfer_group[transfer_group["method"] == aware_method].set_index("seed")
            common = direct.index.intersection(aware.index)
            if len(common) < 2:
                mean_delta = math.nan
                p_two_sided = math.nan
                p_aware_better = math.nan
            else:
                direct_score = direct.loc[common, "reconstruction_calibration_score"].to_numpy(dtype=np.float64)
                aware_score = aware.loc[common, "reconstruction_calibration_score"].to_numpy(dtype=np.float64)
                delta = direct_score - aware_score
                mean_delta = float(delta.mean())
                p_two_sided = float(stats.ttest_rel(direct_score, aware_score, nan_policy="omit").pvalue)
                try:
                    p_aware_better = float(
                        stats.ttest_rel(direct_score, aware_score, alternative="greater", nan_policy="omit").pvalue
                    )
                except TypeError:
                    statistic = stats.ttest_rel(direct_score, aware_score, nan_policy="omit").statistic
                    p_aware_better = float(stats.t.sf(statistic, df=len(common) - 1))
            rows.append(
                {
                    "transfer_id": transfer_id,
                    "baseline_family": family,
                    "comparison": f"{aware_method}_vs_{direct_method}",
                    "comparison_scope": "same_source_target_split_same_target_calibration_label_budget",
                    "paired_seed_count": int(len(common)),
                    "metric": "reconstruction_calibration_score",
                    "mean_delta_direct_minus_measurement_aware": mean_delta,
                    "p_value_two_sided": p_two_sided,
                    "p_value_measurement_aware_better_one_sided": p_aware_better,
                    "measurement_aware_better_significance": mv24.significance_label(p_aware_better),
                }
            )
    return pd.DataFrame(rows).sort_values(["transfer_id", "baseline_family"]).reset_index(drop=True)


def format_mean_ci(row: pd.Series, metric: str) -> str:
    return mv24.format_mean_ci(row, metric)


def build_main_result_table(summary: pd.DataFrame, significance: pd.DataFrame) -> pd.DataFrame:
    sig_lookup: dict[tuple[str, str], str] = {}
    delta_lookup: dict[tuple[str, str], float] = {}
    for _, row in significance.iterrows():
        sig_lookup[(str(row["transfer_id"]), str(row["baseline_family"]))] = str(row["measurement_aware_better_significance"])
        delta_lookup[(str(row["transfer_id"]), str(row["baseline_family"]))] = float(
            row["mean_delta_direct_minus_measurement_aware"]
        )
    rows: list[dict[str, Any]] = []
    for _, row in summary.iterrows():
        family = str(row["baseline_family"])
        is_measurement = str(row["method"]).endswith("_measurement_aware")
        rows.append(
            {
                "transfer_id": row["transfer_id"],
                "baseline_family": family,
                "method": row["method"],
                "seeds": int(row["seed_count"]),
                "target_calibration_labels": "yes",
                "labeled_target_calib_n": int(row["target_calibration_count"]),
                "target_eval_n": int(row["target_evaluation_count"]),
                "macro_item_mae_ci95": format_mean_ci(row, "target_macro_item_mae"),
                "calibration_mae_ci95": format_mean_ci(row, "target_calibration_mae"),
                "reconstruction_calibration_score_ci95": format_mean_ci(row, "reconstruction_calibration_score"),
                "total_mae_ci95": format_mean_ci(row, "target_total_mae"),
                "total_ccc_ci95": format_mean_ci(row, "target_total_ccc"),
                "post_head_domain_ba_ci95": format_mean_ci(row, "post_head_domain_identity_ba"),
                "measurement_layer_delta_score": (
                    f"{delta_lookup[(row['transfer_id'], family)]:.3f}" if is_measurement else ""
                ),
                "direct_vs_measurement_significance": (
                    sig_lookup.get((str(row["transfer_id"]), family), "") if is_measurement else ""
                ),
                "method_rank": int(row["method_rank"]),
            }
        )
    return pd.DataFrame(rows).sort_values(["transfer_id", "method_rank"]).drop(columns=["method_rank"]).reset_index(drop=True)


def build_secondary_clinical_table(summary: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for _, row in summary.iterrows():
        rows.append(
            {
                "transfer_id": row["transfer_id"],
                "baseline_family": row["baseline_family"],
                "method": row["method"],
                "target_calibration_labels": "yes",
                "labeled_target_calib_n": int(row["target_calibration_count"]),
                "macro_f1_ci95": format_mean_ci(row, "target_binary_macro_f1"),
                "balanced_accuracy_ci95": format_mean_ci(row, "target_binary_balanced_accuracy"),
                "auroc_ci95": format_mean_ci(row, "target_binary_auroc"),
                "auprc_ci95": format_mean_ci(row, "target_binary_auprc"),
                "sensitivity_ci95": format_mean_ci(row, "target_binary_sensitivity"),
                "specificity_ci95": format_mean_ci(row, "target_binary_specificity"),
                "method_rank": int(row["method_rank"]),
            }
        )
    return pd.DataFrame(rows).sort_values(["transfer_id", "method_rank"]).drop(columns=["method_rank"]).reset_index(drop=True)


def write_main_markdown(table: pd.DataFrame, path: Path) -> None:
    lines = [
        "| transfer | family | method | seeds | target labels | calib n | eval n | macro item MAE | calibration MAE | recon+calib score | total MAE | CCC | post-head BA | aware delta | sig |",
        "| --- | --- | --- | ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |",
    ]
    for _, row in table.iterrows():
        lines.append(
            "| "
            + " | ".join(
                [
                    str(row["transfer_id"]),
                    str(row["baseline_family"]),
                    str(row["method"]),
                    str(row["seeds"]),
                    str(row["target_calibration_labels"]),
                    str(row["labeled_target_calib_n"]),
                    str(row["target_eval_n"]),
                    str(row["macro_item_mae_ci95"]),
                    str(row["calibration_mae_ci95"]),
                    str(row["reconstruction_calibration_score_ci95"]),
                    str(row["total_mae_ci95"]),
                    str(row["total_ccc_ci95"]),
                    str(row["post_head_domain_ba_ci95"]),
                    str(row["measurement_layer_delta_score"]),
                    str(row["direct_vs_measurement_significance"]),
                ]
            )
            + " |"
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_secondary_markdown(table: pd.DataFrame, path: Path) -> None:
    lines = [
        "| transfer | family | method | macro-F1 | BA | AUROC | AUPRC | sensitivity | specificity |",
        "| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for _, row in table.iterrows():
        lines.append(
            "| "
            + " | ".join(
                [
                    str(row["transfer_id"]),
                    str(row["baseline_family"]),
                    str(row["method"]),
                    str(row["macro_f1_ci95"]),
                    str(row["balanced_accuracy_ci95"]),
                    str(row["auroc_ci95"]),
                    str(row["auprc_ci95"]),
                    str(row["sensitivity_ci95"]),
                    str(row["specificity_ci95"]),
                ]
            )
            + " |"
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def significance_to_markdown(table: pd.DataFrame) -> str:
    lines = [
        "| transfer | family | comparison | seeds | direct-minus-aware score delta | aware-better p | sig |",
        "| --- | --- | --- | ---: | ---: | ---: | --- |",
    ]
    for _, row in table.iterrows():
        delta = row["mean_delta_direct_minus_measurement_aware"]
        p_value = row["p_value_measurement_aware_better_one_sided"]
        lines.append(
            "| "
            + " | ".join(
                [
                    str(row["transfer_id"]),
                    str(row["baseline_family"]),
                    str(row["comparison"]),
                    str(row["paired_seed_count"]),
                    "" if pd.isna(delta) else f"{float(delta):.4f}",
                    "" if pd.isna(p_value) else f"{float(p_value):.4g}",
                    str(row["measurement_aware_better_significance"]),
                ]
            )
            + " |"
        )
    return "\n".join(lines)


def baseline_contract() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "method": "gnn_sda_style_direct_head",
                "reference": "Chen et al., IEEE Transactions on Multimedia 2024, Semi-Supervised Domain Adaptation for Major Depressive Disorder Detection",
                "paper_mechanism_used": "GNN-based domain alignment plus uncertainty-guided target optimization",
                "mv26_adaptation": "static kNN graph over official MV24 foundation representations, adversarial domain head, target unlabeled pseudo-labeling, and shared direct ordinal item head",
                "target_calibration_labels": "yes",
            },
            {
                "method": "gnn_sda_style_measurement_aware",
                "reference": "Chen et al., IEEE Transactions on Multimedia 2024, Semi-Supervised Domain Adaptation for Major Depressive Disorder Detection",
                "paper_mechanism_used": "same GNN-SDA-style representation adaptation",
                "mv26_adaptation": "replace the direct target head with a shared symptom layer and corpus-specific cumulative ordinal heads",
                "target_calibration_labels": "yes",
            },
            {
                "method": "questmf_style_direct_head",
                "reference": "Mandal et al., CLPsych 2025, Enhancing Depression Detection via Question-wise Modality Fusion",
                "paper_mechanism_used": "question-wise modality fusion and Imbalanced Ordinal Log-Loss",
                "mv26_adaptation": "per-PHQ-item gates over Qwen3 text, WavLM audio, and OpenFace video features with a direct ordinal item head",
                "target_calibration_labels": "yes",
            },
            {
                "method": "questmf_style_measurement_aware",
                "reference": "Mandal et al., CLPsych 2025, Enhancing Depression Detection via Question-wise Modality Fusion",
                "paper_mechanism_used": "same question-wise modality fusion",
                "mv26_adaptation": "per-item fused evidence is converted to shared symptom scores and reconstructed through corpus-specific cumulative ordinal heads",
                "target_calibration_labels": "yes",
            },
        ]
    )


def write_contract_markdown(contract: pd.DataFrame, path: Path) -> None:
    lines = [
        "# MV26 Depression-Specific Baseline Contract",
        "",
        "MV26 is a targeted stress test, not a broad leaderboard expansion. It asks whether the measurement-aware target layer still adds value after two close depression-specific modeling ideas: GNN-SDA-style semi-supervised domain adaptation and QuestMF-style question-wise ordinal fusion.",
        "",
        "All rows use the same E-DAIC <-> CMDC split, the same eight shared PHQ items, the same official MV24 Qwen3 + WavLM + OpenFace subject representation, the same five seeds, and the same labeled target calibration budget. The only intended contrast within each family is the final target pathway: direct ordinal item head versus shared symptom layer plus corpus-specific cumulative ordinal heads.",
        "",
        "| method | reference | MV26 adaptation | target calibration labels |",
        "| --- | --- | --- | --- |",
    ]
    for _, row in contract.iterrows():
        lines.append(
            f"| {row['method']} | {row['reference']} | {row['mv26_adaptation']} | {row['target_calibration_labels']} |"
        )
    lines.extend(
        [
            "",
            "The GNN-SDA-style row is an adapted reimplementation because no official runnable code was found during the MV26 setup pass. The QuestMF-style row was checked against the public UKPLab repository and adapted to our subject-level frozen-feature contract rather than copying E-DAIC-only raw-data scripts.",
            "",
        ]
    )
    path.write_text("\n".join(lines), encoding="utf-8")


def artifact_hygiene(out_dir: Path) -> dict[str, Any]:
    forbidden_patterns = [
        r"/root/",
        r"/autodl-tmp/",
        r"\bsubject_id\b",
        r"\btext_path\b",
        r"\baudio_path\b",
        r"\bvideo_path\b",
        r"\.wav\b",
        r"\.mp4\b",
        r"\.avi\b",
        r"row prediction",
        r"embedding matrix",
        r"model weight",
    ]
    violations: list[dict[str, str]] = []
    checked = 0
    for name in sorted(TRACKED_FILES - {"artifact_hygiene_audit.json"}):
        path = out_dir / name
        if not path.exists():
            continue
        checked += 1
        text = path.read_text(encoding="utf-8", errors="ignore")
        for pattern in forbidden_patterns:
            if re.search(pattern, text, flags=re.IGNORECASE):
                violations.append({"file": path.name, "pattern": pattern})
    return {
        "audit_id": "P5_MV26_depression_specific_baseline_hygiene",
        "generated_at": utc_now(),
        "files_checked": int(checked),
        "artifact_hygiene_passed": not violations,
        "violation_count": int(len(violations)),
        "violations": violations,
    }


def write_report(
    out_dir: Path,
    run_summary: dict[str, Any],
    coverage: pd.DataFrame,
    summary: pd.DataFrame,
    main_table: pd.DataFrame,
    secondary_table: pd.DataFrame,
    significance: pd.DataFrame,
) -> None:
    best = (
        summary.sort_values(["transfer_id", "baseline_family", "reconstruction_calibration_score_mean"])
        .groupby(["transfer_id", "baseline_family"], as_index=False)
        .head(1)
    )
    lines = [
        "# P5 MV26 Depression-Specific Baseline Stress Test",
        "",
        f"Generated: `{run_summary['generated_at']}`",
        "",
        "## Scope",
        "",
        "MV26 evaluates two close baseline families under the same MV24 PHQ shared-item transfer contract. This is not a claim that we reproduced every implementation detail of the source papers; it is a controlled test of whether depression-specific representation adaptation or question-wise ordinal fusion removes the need for an explicit corpus-specific measurement pathway.",
        "",
        "## Feature Coverage",
        "",
        "| asset | dataset | modality | rows | columns |",
        "| --- | --- | --- | ---: | ---: |",
    ]
    for _, row in coverage.sort_values(["asset_id", "dataset"]).iterrows():
        lines.append(
            f"| {row['asset_id']} | {row['dataset']} | {row['modality']} | {int(row['rows'])} | {int(row['feature_columns'])} |"
        )
    lines.extend(
        [
            "",
            "## Best Rows By Family",
            "",
            "| transfer | family | best method | recon+calib score | macro item MAE | calibration MAE | total MAE | seeds |",
            "| --- | --- | --- | ---: | ---: | ---: | ---: | ---: |",
        ]
    )
    for _, row in best.iterrows():
        lines.append(
            f"| {row['transfer_id']} | {row['baseline_family']} | {row['method']} | {float(row['reconstruction_calibration_score_mean']):.4f} | {float(row['target_macro_item_mae_mean']):.4f} | {float(row['target_calibration_mae_mean']):.4f} | {float(row['target_total_mae_mean']):.4f} | {int(row['seed_count'])} |"
    )
    lines.extend(["", "## Paired Measurement-Layer Test", ""])
    lines.append(significance_to_markdown(significance))
    lines.extend(["", "## Main Result Table", ""])
    lines.append((out_dir / "main_result_table.md").read_text(encoding="utf-8").strip())
    lines.extend(["", "## Secondary Clinical Endpoint", ""])
    lines.append((out_dir / "secondary_clinical_metrics_table.md").read_text(encoding="utf-8").strip())
    lines.extend(
        [
            "",
            "## Interpretation Handle",
            "",
            "The result should be written as a depression-specific baseline stress test. If the measurement-aware row improves reconstruction and calibration within a family, the strongest paper claim is that corpus-specific measurement modeling gives complementary gains after stronger representation adaptation. Binary endpoint metrics are secondary and should be used to orient clinical readers, not to replace the ordinal target-validity argument.",
            "",
        ]
    )
    (out_dir / "report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-root", type=Path, default=DEFAULT_INPUT_ROOT)
    parser.add_argument("--manifest-dir", type=Path, default=DEFAULT_MANIFEST_DIR)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--seeds", type=int, nargs="+", default=[0, 1, 2, 3, 4])
    parser.add_argument("--methods", nargs="+", choices=METHOD_ORDER, default=METHOD_ORDER)
    parser.add_argument("--modality-pca-components", type=int, default=48)
    parser.add_argument("--hidden-dim", type=int, default=192)
    parser.add_argument("--dropout", type=float, default=0.08)
    parser.add_argument("--learning-rate", type=float, default=1e-3)
    parser.add_argument("--weight-decay", type=float, default=1e-4)
    parser.add_argument("--target-calibration-fraction", type=float, default=0.30)
    parser.add_argument("--target-calibration-min", type=int, default=24)
    parser.add_argument("--target-calibration-weight", type=float, default=16.0)
    parser.add_argument("--latent-mmd-weight", type=float, default=0.001)
    parser.add_argument("--latent-l2-weight", type=float, default=1e-4)
    parser.add_argument("--imboll-alpha", type=float, default=1.5)
    parser.add_argument("--imboll-beta", type=float, default=0.5)
    parser.add_argument("--gnn-k", type=int, default=10)
    parser.add_argument("--gnn-source-warmup-epochs", type=int, default=350)
    parser.add_argument("--gnn-epochs", type=int, default=900)
    parser.add_argument("--questmf-source-warmup-epochs", type=int, default=350)
    parser.add_argument("--questmf-epochs", type=int, default=900)
    parser.add_argument("--domain-loss-weight", type=float, default=0.15)
    parser.add_argument("--pseudo-warmup-epochs", type=int, default=250)
    parser.add_argument("--pseudo-confidence-threshold", type=float, default=0.45)
    parser.add_argument("--pseudo-loss-weight", type=float, default=0.20)
    parser.add_argument("--class-balance-weight", type=float, default=0.03)
    parser.add_argument("--device", default="auto", help="auto, cpu, cuda, or cuda:N")
    parser.add_argument("--clean", action="store_true", help="remove previous aggregate outputs before running")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    out_dir = args.out_dir
    if args.clean:
        clean_tracked_outputs(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    tables, feature_cols, coverage = mv24.load_official_view_tables(args)
    coverage.to_csv(out_dir / "feature_asset_coverage.csv", index=False)
    contract = baseline_contract()
    contract.to_csv(out_dir / "baseline_contract.csv", index=False)
    write_contract_markdown(contract, out_dir / "baseline_contract.md")

    rows: list[dict[str, Any]] = []
    for source_dataset, target_dataset in TRANSFER_DIRECTIONS:
        rows.extend(run_transfer_direction(source_dataset, target_dataset, tables, feature_cols, args))
    metrics = pd.DataFrame(rows).sort_values(["transfer_id", "method_rank", "seed"]).reset_index(drop=True)
    metrics.to_csv(out_dir / "metrics_by_seed.csv", index=False)
    summary = summarize_metrics(metrics)
    summary.to_csv(out_dir / "summary_by_method.csv", index=False)
    significance = paired_measurement_layer_significance(metrics)
    significance.to_csv(out_dir / "paired_measurement_layer_significance.csv", index=False)
    main_table = build_main_result_table(summary, significance)
    main_table.to_csv(out_dir / "main_result_table.csv", index=False)
    write_main_markdown(main_table, out_dir / "main_result_table.md")
    secondary_table = build_secondary_clinical_table(summary)
    secondary_table.to_csv(out_dir / "secondary_clinical_metrics_table.csv", index=False)
    write_secondary_markdown(secondary_table, out_dir / "secondary_clinical_metrics_table.md")

    run_summary = {
        "run_id": "P5_MV26_depression_specific_baselines",
        "generated_at": utc_now(),
        "git_commit": git_commit(),
        "status": "complete",
        "directions": [f"{src}_to_{tgt}_phq_shared" for src, tgt in TRANSFER_DIRECTIONS],
        "methods": list(args.methods),
        "baseline_families": list(FAMILIES),
        "seed_count": int(len(set(args.seeds))),
        "official_view_id": mv24.official_view().view_id,
        "target_calibration_fraction": float(args.target_calibration_fraction),
        "target_calibration_min": int(args.target_calibration_min),
        "target_calibration_labels_used_by_all_rows": True,
        "primary_metric": "reconstruction_calibration_score",
        "primary_metric_components": ["target_macro_item_mae", "target_calibration_mae"],
        "secondary_severity_metrics": ["target_total_mae", "target_total_ccc"],
        "secondary_clinical_classification_endpoint": f"shared PHQ total >= {PHQ_SHARED_BINARY_THRESHOLD:.0f}",
        "secondary_clinical_classification_metrics": [
            "target_binary_macro_f1",
            "target_binary_balanced_accuracy",
            "target_binary_auroc",
            "target_binary_auprc",
            "target_binary_sensitivity",
            "target_binary_specificity",
        ],
        "comparison_scope": "within-family direct target head versus measurement-aware target layer under the same target calibration labels",
        "aggregate_outputs_only": True,
    }
    (out_dir / "run_summary.json").write_text(json.dumps(run_summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    write_report(out_dir, run_summary, coverage, summary, main_table, secondary_table, significance)
    hygiene = artifact_hygiene(out_dir)
    (out_dir / "artifact_hygiene_audit.json").write_text(json.dumps(hygiene, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if not hygiene["artifact_hygiene_passed"]:
        raise RuntimeError(f"artifact hygiene failed: {hygiene['violations']}")


if __name__ == "__main__":
    main()
