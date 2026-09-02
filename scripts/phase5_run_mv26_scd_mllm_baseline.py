#!/usr/bin/env python3
"""Run the MV26 SCD-MLLM-style baseline component.

This component complements the core MV26 runner with an SCD-MLLM-style
heterogeneous multimodal adapter and adaptive fusion baseline.

Both are adapted to the same E-DAIC <-> CMDC PHQ shared-item contract used by
MV24/MV26. Each family is evaluated with a direct ordinal item head and with
the paper's measurement-aware target pathway:

strong representation/adaptation -> strong representation/adaptation plus
shared symptom layer and corpus-specific ordinal measurement heads.

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
from sklearn.metrics import balanced_accuracy_score
from sklearn.model_selection import StratifiedKFold
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LogisticRegression


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "scripts"))

import phase5_run_mv24_measurement_aware_ordinal_model as mv24
import phase5_run_mv26_core_depression_specific_baselines as mv26


DEFAULT_INPUT_ROOT = Path("/root/autodl-tmp")
DEFAULT_MANIFEST_DIR = DEFAULT_INPUT_ROOT / "datasets" / "manifests"
DEFAULT_OUT_DIR = (
    ROOT
    / "analysis"
    / "phase5_minimal_validation"
    / "p5_mv26_depression_specific_baselines"
    / "scd_mllm_component"
)

DATASETS = mv24.DATASETS
PHQ_SHARED_BINARY_THRESHOLD = mv24.PHQ_SHARED_BINARY_THRESHOLD
TRANSFER_DIRECTIONS = mv24.TRANSFER_DIRECTIONS
METRIC_COLUMNS = list(mv24.METRIC_COLUMNS)
FAMILIES = ("scd_mllm_style",)
METHOD_ORDER = [
    "scd_mllm_style_direct_head",
    "scd_mllm_style_measurement_aware",
]
METHOD_RANK = {method: rank for rank, method in enumerate(METHOD_ORDER)}
MEASUREMENT_PAIR = {
    "scd_mllm_style": ("scd_mllm_style_direct_head", "scd_mllm_style_measurement_aware"),
}
DATASET_TO_INDEX = {dataset: idx for idx, dataset in enumerate(DATASETS)}
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
EPS = 1e-8


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


def distillation_loss(probs: torch.Tensor, teacher_probs: torch.Tensor) -> torch.Tensor:
    return F.kl_div(probs.clamp_min(EPS).log(), teacher_probs.detach().clamp_min(EPS), reduction="batchmean")


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
        scores.append(float(balanced_accuracy_score(labels[eval_idx], clf.predict(features[eval_idx]))))
    return float(np.mean(scores))


class ScdAdapterBase(nn.Module):
    modalities = ["text", "audio", "video"]

    def __init__(self, modality_dims: dict[str, int], hidden_dim: int, dropout: float) -> None:
        super().__init__()
        self.projectors = nn.ModuleDict(
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
        self.modality_embeddings = nn.Parameter(torch.randn(len(self.modalities), hidden_dim) * 0.02)
        self.mask_tokens = nn.Parameter(torch.randn(len(self.modalities), hidden_dim) * 0.02)
        self.corpus_embeddings = nn.Embedding(len(DATASETS), hidden_dim)
        layer = nn.TransformerEncoderLayer(
            d_model=hidden_dim,
            nhead=4,
            dim_feedforward=hidden_dim * 2,
            dropout=dropout,
            activation="gelu",
            batch_first=True,
            norm_first=True,
        )
        self.token_encoder = nn.TransformerEncoder(layer, num_layers=1)
        self.fusion_gate = nn.Linear(hidden_dim * (len(self.modalities) + 1), len(self.modalities))
        self.output_norm = nn.LayerNorm(hidden_dim)

    def fused_representation(
        self,
        inputs: dict[str, torch.Tensor],
        corpus_index: int,
        *,
        mask_prob: float,
    ) -> tuple[torch.Tensor, torch.Tensor]:
        batch_size = next(iter(inputs.values())).shape[0]
        device = next(iter(inputs.values())).device
        modality_tokens: list[torch.Tensor] = []
        mask_matrix = torch.zeros(batch_size, len(self.modalities), dtype=torch.bool, device=device)
        if self.training and mask_prob > 0.0:
            mask_matrix = torch.rand(batch_size, len(self.modalities), device=device) < float(mask_prob)
            all_masked = mask_matrix.all(dim=1)
            if int(all_masked.sum().item()) > 0:
                mask_matrix[all_masked, 0] = False
        corpus_prompt = self.corpus_embeddings(
            torch.full((batch_size,), int(corpus_index), dtype=torch.long, device=device)
        )
        for modality_idx, modality in enumerate(self.modalities):
            token = self.projectors[modality](inputs[modality])
            if self.training and mask_prob > 0.0:
                mask_token = self.mask_tokens[modality_idx].view(1, -1).expand_as(token)
                token = torch.where(mask_matrix[:, modality_idx].view(-1, 1), mask_token, token)
            token = token + self.modality_embeddings[modality_idx].view(1, -1) + corpus_prompt
            modality_tokens.append(token)
        prompt_token = corpus_prompt.unsqueeze(1)
        tokens = torch.cat([prompt_token, torch.stack(modality_tokens, dim=1)], dim=1)
        encoded = self.token_encoder(tokens)
        prompt = encoded[:, 0, :]
        encoded_modalities = encoded[:, 1:, :]
        gate_context = torch.cat([prompt, encoded_modalities.flatten(start_dim=1)], dim=1)
        gates = F.softmax(self.fusion_gate(gate_context), dim=-1)
        fused = torch.sum(encoded_modalities * gates.unsqueeze(-1), dim=1)
        return self.output_norm(fused + prompt), gates


class ScdMllmDirectNet(ScdAdapterBase):
    def __init__(self, modality_dims: dict[str, int], hidden_dim: int, n_items: int, dropout: float) -> None:
        super().__init__(modality_dims, hidden_dim, dropout)
        self.item_head = nn.Linear(hidden_dim, n_items * 4)
        self.n_items = int(n_items)

    def forward(
        self,
        inputs: dict[str, torch.Tensor],
        corpus_index: int,
        *,
        mask_prob: float = 0.0,
    ) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
        fused, gates = self.fused_representation(inputs, corpus_index, mask_prob=mask_prob)
        logits = self.item_head(fused).view(-1, self.n_items, 4)
        return logits, fused, gates


class ScdMllmMeasurementNet(ScdAdapterBase):
    def __init__(self, modality_dims: dict[str, int], hidden_dim: int, symptom_dim: int, dropout: float) -> None:
        super().__init__(modality_dims, hidden_dim, dropout)
        self.symptom_layer = nn.Linear(hidden_dim, symptom_dim)
        self.heads = nn.ModuleDict({dataset: mv24.CorpusOrdinalHead(symptom_dim) for dataset in DATASETS})

    def symptom_scores(
        self,
        inputs: dict[str, torch.Tensor],
        corpus_index: int,
        *,
        mask_prob: float = 0.0,
    ) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
        fused, gates = self.fused_representation(inputs, corpus_index, mask_prob=mask_prob)
        return self.symptom_layer(fused), fused, gates

    def forward(
        self,
        inputs: dict[str, torch.Tensor],
        corpus_id: str,
        corpus_index: int,
        *,
        mask_prob: float = 0.0,
    ) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor, torch.Tensor]:
        symptoms, fused, _ = self.symptom_scores(inputs, corpus_index, mask_prob=mask_prob)
        probs, expected = self.heads[corpus_id](symptoms)
        return symptoms, probs, expected, fused


def input_dict(arrays: dict[str, np.ndarray], device: torch.device) -> dict[str, torch.Tensor]:
    return {name: tensor(value, device) for name, value in arrays.items()}


def consistency_kl(masked_logits: torch.Tensor, full_logits: torch.Tensor) -> torch.Tensor:
    full_probs = F.softmax(full_logits.detach(), dim=-1).clamp_min(EPS)
    masked_log_probs = F.log_softmax(masked_logits, dim=-1)
    return F.kl_div(masked_log_probs, full_probs, reduction="batchmean")


def train_scd_mllm_direct(
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
    weights = tensor(mv26.class_weights(np.vstack([source_y, target_y_all[target_calib_idx]]), args.imboll_beta), device)
    source_idx = DATASET_TO_INDEX[source_dataset]
    target_idx = DATASET_TO_INDEX[target_dataset]
    model = ScdMllmDirectNet(
        {name: value.shape[1] for name, value in source_by_modality.items()},
        args.hidden_dim,
        source_y.shape[1],
        args.dropout,
    ).to(device)
    optimizer = torch.optim.AdamW(model.parameters(), lr=args.learning_rate, weight_decay=args.weight_decay)
    for _ in range(int(args.scd_epochs)):
        optimizer.zero_grad(set_to_none=True)
        source_full_logits, source_full_repr, _ = model(source_inputs, source_idx, mask_prob=0.0)
        target_full_logits, target_full_repr, _ = model(target_inputs, target_idx, mask_prob=0.0)
        source_mask_logits, _, _ = model(source_inputs, source_idx, mask_prob=args.modality_mask_prob)
        target_mask_logits, _, _ = model(target_inputs, target_idx, mask_prob=args.modality_mask_prob)
        loss = mv26.imboll_loss(source_mask_logits, ys, weights, alpha=args.imboll_alpha)
        loss = loss + float(args.target_calibration_weight) * mv26.imboll_loss(
            target_mask_logits[target_calib],
            yt[target_calib],
            weights,
            alpha=args.imboll_alpha,
        )
        loss = loss + float(args.consistency_weight) * (
            consistency_kl(source_mask_logits, source_full_logits)
            + consistency_kl(target_mask_logits, target_full_logits)
        )
        loss = loss + float(args.fusion_mmd_weight) * mv24.rbf_mmd(source_full_repr, target_full_repr)
        loss.backward()
        torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
        optimizer.step()
    model.eval()
    with torch.inference_mode():
        source_logits, source_repr, _ = model(source_inputs, source_idx, mask_prob=0.0)
        target_logits, target_repr, _ = model(target_inputs, target_idx, mask_prob=0.0)
        source_expected = mv26.expected_from_logits(source_logits)
        target_expected = mv26.expected_from_logits(target_logits)
        target_probs = mv26.probs_from_logits(target_logits)
    return (
        target_expected.detach().cpu().numpy().astype(np.float32),
        source_expected.detach().cpu().numpy().astype(np.float32),
        target_probs.detach().cpu().numpy().astype(np.float32),
        source_repr.detach().cpu().numpy().astype(np.float32),
        target_repr.detach().cpu().numpy().astype(np.float32),
    )


def train_scd_mllm_measurement(
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
    source_idx = DATASET_TO_INDEX[source_dataset]
    target_idx = DATASET_TO_INDEX[target_dataset]
    model = ScdMllmMeasurementNet(
        {name: value.shape[1] for name, value in source_by_modality.items()},
        args.hidden_dim,
        source_y.shape[1],
        args.dropout,
    ).to(device)
    optimizer = torch.optim.AdamW(model.parameters(), lr=args.learning_rate, weight_decay=args.weight_decay)
    for _ in range(int(args.scd_source_warmup_epochs)):
        optimizer.zero_grad(set_to_none=True)
        source_symptoms, source_probs, _, _ = model(
            source_inputs,
            source_dataset,
            source_idx,
            mask_prob=args.modality_mask_prob,
        )
        loss = mv24.ordinal_nll(source_probs, ys) + float(args.latent_l2_weight) * source_symptoms.pow(2).mean()
        loss.backward()
        torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
        optimizer.step()
    model.heads[target_dataset].load_state_dict(model.heads[source_dataset].state_dict())
    optimizer = torch.optim.AdamW(model.parameters(), lr=args.learning_rate, weight_decay=args.weight_decay)
    for _ in range(int(args.scd_epochs)):
        optimizer.zero_grad(set_to_none=True)
        source_sym_full, source_probs_full, _, source_repr_full = model(
            source_inputs,
            source_dataset,
            source_idx,
            mask_prob=0.0,
        )
        target_sym_full, target_probs_full, _, target_repr_full = model(
            target_inputs,
            target_dataset,
            target_idx,
            mask_prob=0.0,
        )
        source_sym_mask, source_probs_mask, _, _ = model(
            source_inputs,
            source_dataset,
            source_idx,
            mask_prob=args.modality_mask_prob,
        )
        target_sym_mask, target_probs_mask, _, _ = model(
            target_inputs,
            target_dataset,
            target_idx,
            mask_prob=args.modality_mask_prob,
        )
        loss = mv24.ordinal_nll(source_probs_mask, ys)
        loss = loss + float(args.target_calibration_weight) * mv24.ordinal_nll(
            target_probs_mask[target_calib],
            yt[target_calib],
        )
        loss = loss + float(args.consistency_weight) * (
            distillation_loss(source_probs_mask, source_probs_full)
            + distillation_loss(target_probs_mask, target_probs_full)
        )
        loss = loss + float(args.latent_mmd_weight) * mv24.rbf_mmd(source_sym_full, target_sym_full)
        loss = loss + float(args.fusion_mmd_weight) * mv24.rbf_mmd(source_repr_full, target_repr_full)
        loss = loss + float(args.latent_l2_weight) * (source_sym_full.pow(2).mean() + target_sym_full.pow(2).mean())
        loss.backward()
        torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
        optimizer.step()
    model.eval()
    with torch.inference_mode():
        source_symptoms, _, source_expected, _ = model(source_inputs, source_dataset, source_idx, mask_prob=0.0)
        target_symptoms, target_probs, target_expected, _ = model(target_inputs, target_dataset, target_idx, mask_prob=0.0)
    return (
        target_expected.detach().cpu().numpy().astype(np.float32),
        source_expected.detach().cpu().numpy().astype(np.float32),
        target_probs.detach().cpu().numpy().astype(np.float32),
        source_symptoms.detach().cpu().numpy().astype(np.float32),
        target_symptoms.detach().cpu().numpy().astype(np.float32),
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
    probs = probs_all[target_eval_idx]
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
        prepared = mv26.prepare_modality_features(
            raw_source,
            raw_target,
            feature_cols,
            n_components=args.modality_pca_components,
            seed=seed,
        )
        common_kwargs = {
            "source_dataset": source_dataset,
            "target_dataset": target_dataset,
            "seed": seed,
            "source_n": len(raw_source),
            "target_calib_n": len(target_calib_idx),
            "target_eval_n": len(target_eval_idx),
            "input_columns": len(feature_cols),
            "modality_dims": prepared.modality_dims,
            "truth_all": target_y_all,
            "target_eval_idx": target_eval_idx,
            "feature_source_repr": prepared.source_concat,
            "feature_target_repr": prepared.target_concat,
        }
        if "scd_mllm_style_direct_head" in selected_methods:
            pred_all, source_pred, probs_all, source_repr, target_repr = train_scd_mllm_direct(
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
                    **common_kwargs,
                    method="scd_mllm_style_direct_head",
                    family="scd_mllm_style",
                    pred_all=pred_all,
                    source_pred=source_pred,
                    probs_all=probs_all,
                    latent_source_repr=source_repr,
                    latent_target_repr=target_repr,
                    training_contract=(
                        "SCD-MLLM-style multi-source modality adapters, prompt-like corpus tokens, "
                        "masking-based missing-modality robustness, and adaptive multimodal fusion"
                    ),
                )
            )
        if "scd_mllm_style_measurement_aware" in selected_methods:
            pred_all, source_pred, probs_all, source_repr, target_repr = train_scd_mllm_measurement(
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
                    **common_kwargs,
                    method="scd_mllm_style_measurement_aware",
                    family="scd_mllm_style",
                    pred_all=pred_all,
                    source_pred=source_pred,
                    probs_all=probs_all,
                    latent_source_repr=source_repr,
                    latent_target_repr=target_repr,
                    training_contract=(
                        "SCD-MLLM-style heterogeneous multimodal adapter and adaptive fusion feeding "
                        "the paper's shared symptom layer plus corpus-specific ordinal measurement heads"
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
                "method": "scd_mllm_style_direct_head",
                "reference": "Chen et al., Pattern Recognition 2026, Towards Stable Cross-Domain Depression Recognition under Missing Modalities",
                "paper_mechanism_used": "multi-source data adapters, masking-based missing-modality robustness, and modality-aware adaptive fusion",
                "mv26_adaptation": "prompt-like corpus tokens and masked text/audio/video adapters over official frozen foundation features feed an adaptive fusion representation and a direct ordinal item head",
                "target_calibration_labels": "yes",
            },
            {
                "method": "scd_mllm_style_measurement_aware",
                "reference": "Chen et al., Pattern Recognition 2026, Towards Stable Cross-Domain Depression Recognition under Missing Modalities",
                "paper_mechanism_used": "same heterogeneous multimodal adapter and adaptive fusion path",
                "mv26_adaptation": "the adaptive fusion representation feeds the paper's shared symptom layer plus corpus-specific cumulative ordinal measurement heads",
                "target_calibration_labels": "yes",
            },
        ]
    )


def write_contract_markdown(contract: pd.DataFrame, path: Path) -> None:
    lines = [
        "# MV26 SCD-MLLM-Style Baseline Component Contract",
        "",
        "This MV26 component is a targeted stress test for SCD-MLLM-style heterogeneous multimodal fusion after the core MV26 run. It is not a cross-paper leaderboard reproduction.",
        "",
        "All rows use the same E-DAIC <-> CMDC split, the same eight shared PHQ items, the same official MV24 Qwen3 + WavLM + OpenFace subject representation, the same five seeds, and the same labeled target calibration budget. The intended contrast within each family is the final target pathway: direct ordinal item head versus shared symptom layer plus corpus-specific cumulative ordinal heads.",
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
            "The SCD-MLLM-style row adapts the public paper mechanisms--heterogeneous input adapters, masking, and modality-aware fusion--to the existing subject-level frozen-feature contract instead of training a full MLLM.",
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
        "audit_id": "P5_MV26_remaining_depression_specific_baseline_hygiene",
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
    significance: pd.DataFrame,
) -> None:
    best = (
        summary.sort_values(["transfer_id", "baseline_family", "reconstruction_calibration_score_mean"])
        .groupby(["transfer_id", "baseline_family"], as_index=False)
        .head(1)
    )
    lines = [
        "# P5 MV26 SCD-MLLM-Style Baseline Component",
        "",
        f"Generated: `{run_summary['generated_at']}`",
        "",
        "## Scope",
        "",
        "This MV26 component evaluates SCD-MLLM-style heterogeneous multimodal fusion under the same MV24/MV26 PHQ shared-item transfer contract. The experiment asks whether a stronger foundation/fusion adaptation idea removes the value of an explicit corpus-specific measurement pathway.",
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
            "Use this MV26 component as part of the close-baseline stress-test package. The strongest manuscript sentence should compare direct and measurement-aware target pathways within the same baseline family and same target calibration budget. The SCD-MLLM-style row is the foundation/fusion stress test.",
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
    parser.add_argument("--fusion-mmd-weight", type=float, default=0.0005)
    parser.add_argument("--latent-l2-weight", type=float, default=1e-4)
    parser.add_argument("--imboll-alpha", type=float, default=1.5)
    parser.add_argument("--imboll-beta", type=float, default=0.5)
    parser.add_argument("--scd-source-warmup-epochs", type=int, default=250)
    parser.add_argument("--scd-epochs", type=int, default=700)
    parser.add_argument("--modality-mask-prob", type=float, default=0.25)
    parser.add_argument("--consistency-weight", type=float, default=0.10)
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
        "run_id": "P5_MV26_scd_mllm_baseline_component",
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
        "full_mllm_note": "SCD-MLLM-style uses the paper mechanisms adapted to frozen subject-level foundation features; it is not full MLLM fine-tuning.",
    }
    (out_dir / "run_summary.json").write_text(json.dumps(run_summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    write_report(out_dir, run_summary, coverage, summary, significance)
    hygiene = artifact_hygiene(out_dir)
    (out_dir / "artifact_hygiene_audit.json").write_text(json.dumps(hygiene, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if not hygiene["artifact_hygiene_passed"]:
        raise RuntimeError(f"artifact hygiene failed: {hygiene['violations']}")


if __name__ == "__main__":
    main()
