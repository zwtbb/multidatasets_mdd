#!/usr/bin/env python3
"""Run MV32 Target-Contract Partial Sharing (TCPS).

MV32 turns the target-comparability audit into a learnable measurement-head
mechanism. It reuses the MV24 official Qwen3+WavLM+OpenFace subject-level
feature contract and the MV28 repeated target-calibration split contract.

The new model is a sparse partially shared cumulative-logit ordinal head:
source and target share base item parameters, while the target corpus may learn
item-level residual threshold adapters. A proximal group-lasso step shrinks
entire item residuals to zero, so the fitted head can sit between a forced
shared ordinal head and a fully corpus-specific ordinal head.

Tracked outputs are aggregate only. Subject-level predictions, feature
matrices, model weights, and raw clinical/media content are not written.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import re
import subprocess
import sys
from collections import defaultdict
from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def normalize_thread_env() -> None:
    for key in ["OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS"]:
        value = str(os.environ.get(key, "")).strip()
        if not value.isdigit() or int(value) <= 0:
            os.environ[key] = "1"


normalize_thread_env()

import numpy as np
import pandas as pd
import torch
import torch.nn as nn
import torch.nn.functional as F
from scipy import stats
from sklearn.decomposition import PCA
from sklearn.preprocessing import StandardScaler

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "scripts"))

import phase5_run_mv19_phq_finite_sample_simulation as mv19
import phase5_run_mv24_measurement_aware_ordinal_model as mv24
import phase5_run_mv28_target_label_budget_uncertainty as mv28


RUN_ID = "P5_MV32_tcps_partial_sharing"
DEFAULT_OUT_DIR = ROOT / "analysis" / "phase5_minimal_validation" / "p5_mv32_tcps_partial_sharing"
PHQ_ITEM_IDS = mv24.PHQ_ITEM_IDS
ANCHOR_ITEMS = ["C01", "C04", "C05", "C07"]
SHIFT_ITEMS = ["C02", "C06"]
SIMULATION_WORLDS = ["H0_invariant", "H_sparse_C02_C06_threshold_DIF", "H_dense_threshold_DIF"]
BASELINE_METHODS = [
    "target_only_direct_mlp",
    "target_only_ordinal",
    "direct_multitask_shared_head",
    "shared_ordinal_head",
    "fully_corpus_specific_ordinal",
    "generic_target_mlp_head",
]
TCPS_METHODS = [
    "tcps_threshold",
    "tcps_threshold_slope",
    "audit_weighted_tcps_threshold",
]
METHOD_ORDER = BASELINE_METHODS + TCPS_METHODS
LOWER_IS_BETTER_METRICS = [
    "target_macro_item_mae",
    "target_total_mae",
    "ordinal_nll",
    "ranked_probability_score",
    "target_binned_item_calibration_mae",
    "total_calibration_in_the_large_abs",
    "total_calibration_slope_abs_error",
]
BOOTSTRAP_METRICS = [
    "target_macro_item_mae",
    "target_total_mae",
    "target_binned_item_calibration_mae",
    "ordinal_nll",
    "ranked_probability_score",
    "total_calibration_in_the_large_abs",
    "total_calibration_slope_abs_error",
]
BOOTSTRAP_REFERENCES = [
    "target_only_direct_mlp",
    "direct_multitask_shared_head",
    "shared_ordinal_head",
    "fully_corpus_specific_ordinal",
    "generic_target_mlp_head",
]
SUMMARY_METRICS = [
    "target_macro_item_mae",
    "target_total_mae",
    "target_total_rmse",
    "target_total_ccc",
    "ordinal_nll",
    "ranked_probability_score",
    "target_binned_item_calibration_mae",
    "total_calibration_in_the_large",
    "total_calibration_in_the_large_abs",
    "total_calibration_slope",
    "total_calibration_slope_abs_error",
    "target_binary_macro_f1",
    "target_binary_balanced_accuracy",
    "target_binary_auroc",
    "target_binary_auprc",
    "specificity_ratio",
]
TRACKED_FILES = {
    "artifact_hygiene_audit.json",
    "feature_view_contract.csv",
    "go_no_go_recommendations.csv",
    "lambda_sensitivity_table.csv",
    "lambda_sensitivity_table.md",
    "method_contract.json",
    "method_contract.md",
    "participant_bootstrap_delta_summary.csv",
    "participant_bootstrap_delta_table.csv",
    "participant_bootstrap_delta_table.md",
    "real_data_by_split.csv",
    "real_data_delta_summary.csv",
    "real_data_main_table.csv",
    "real_data_main_table.md",
    "real_data_summary.csv",
    "report.md",
    "residual_support_by_split.csv",
    "residual_support_summary.csv",
    "residual_support_table.csv",
    "residual_support_table.md",
    "targeted_item_error_by_split.csv",
    "targeted_item_error_delta_summary.csv",
    "targeted_item_error_delta_table.csv",
    "targeted_item_error_delta_table.md",
    "targeted_item_error_summary.csv",
    "run_summary.json",
    "simulation_by_draw.csv",
    "simulation_design_contract.csv",
    "simulation_residual_support_summary.csv",
    "simulation_summary.csv",
    "simulation_table.csv",
    "simulation_table.md",
}


@dataclass(frozen=True)
class MethodPrediction:
    pred_all: np.ndarray
    probs_all: np.ndarray | None
    residual_norms: np.ndarray | None
    audit_weights: np.ndarray | None
    specificity_ratio: float


@dataclass(frozen=True)
class JobSpec:
    source_dataset: str
    target_dataset: str
    budget_index: int
    split_index: int


_WORKER_TABLES: dict[str, pd.DataFrame] | None = None
_WORKER_FEATURE_COLS: list[str] | None = None
_WORKER_BUDGETS: list[mv28.BudgetSpec] | None = None
_WORKER_ARGS: argparse.Namespace | None = None
_WORKER_OBSERVED: pd.DataFrame | None = None


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def git_commit() -> str:
    return subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT, text=True).strip()


def clean_tracked_outputs(out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    for name in TRACKED_FILES:
        path = out_dir / name
        if path.exists():
            path.unlink()


def md_escape(value: Any) -> str:
    return str(value).replace("|", "\\|").replace("\n", " ")


def lambda_id(value: float) -> str:
    return f"{float(value):.6g}".replace(".", "p").replace("-", "m")


def lambda_key(value: float) -> str:
    return "not_applicable" if pd.isna(value) else f"{float(value):.8g}"


def method_spec_key(method: str, lambda_group: float) -> tuple[str, str]:
    return method, lambda_key(lambda_group)


def device_from_args(args: argparse.Namespace) -> torch.device:
    return torch.device(args.device if args.device != "auto" else ("cuda" if torch.cuda.is_available() else "cpu"))


def ordinal_nll_from_probs(probs: np.ndarray | None, truth: np.ndarray) -> float:
    if probs is None:
        return math.nan
    y = truth.astype(np.int64)
    row = np.arange(y.shape[0])[:, None]
    col = np.arange(y.shape[1])[None, :]
    chosen = np.clip(probs[row, col, y], 1.0e-8, 1.0)
    return float(-np.mean(np.log(chosen)))


def ranked_probability_score(probs: np.ndarray | None, truth: np.ndarray) -> float:
    if probs is None:
        return math.nan
    y = truth.astype(np.int64)
    pred_cdf = np.cumsum(np.clip(probs, 0.0, 1.0), axis=-1)
    true_cdf = (np.arange(probs.shape[-1])[None, None, :] >= y[:, :, None]).astype(np.float64)
    return float(np.mean(np.sum((pred_cdf - true_cdf) ** 2, axis=-1) / float(probs.shape[-1] - 1)))


def evaluate_prediction(pred: np.ndarray, truth: np.ndarray, probs: np.ndarray | None) -> dict[str, float]:
    metrics = mv28.evaluate_predictions(pred, truth)
    metrics["ordinal_nll"] = ordinal_nll_from_probs(probs, truth)
    metrics["ranked_probability_score"] = ranked_probability_score(probs, truth)
    return metrics


def summary_stats(values: np.ndarray | list[float]) -> dict[str, float]:
    array = np.asarray(values, dtype=np.float64)
    array = array[np.isfinite(array)]
    if len(array) == 0:
        return {"count": 0, "mean": math.nan, "std": math.nan, "ci95_low": math.nan, "ci95_high": math.nan}
    return {
        "count": int(len(array)),
        "mean": float(array.mean()),
        "std": float(array.std(ddof=1)) if len(array) > 1 else 0.0,
        "ci95_low": float(np.quantile(array, 0.025)),
        "ci95_high": float(np.quantile(array, 0.975)),
    }


def fmt_interval(row: pd.Series, metric: str) -> str:
    mean = row[f"{metric}_mean"]
    if pd.isna(mean):
        return ""
    return f"{float(mean):.3f} [{float(row[f'{metric}_ci95_low']):.3f}, {float(row[f'{metric}_ci95_high']):.3f}]"


def tcps_group_lasso_weights(source_y: np.ndarray, target_calib_y: np.ndarray) -> np.ndarray:
    scores: list[float] = []
    source_total = source_y.sum(axis=1).astype(np.float64)
    target_total = target_calib_y.sum(axis=1).astype(np.float64)
    for item_idx in range(source_y.shape[1]):
        source_rest = source_total - source_y[:, item_idx]
        target_rest = target_total - target_calib_y[:, item_idx]
        edges = np.unique(np.quantile(source_rest, [0.0, 1 / 3, 2 / 3, 1.0]))
        diffs: list[float] = []
        weights: list[int] = []
        for low, high in zip(edges[:-1], edges[1:]):
            src_mask = (source_rest >= low) & (source_rest <= high)
            tgt_mask = (target_rest >= low) & (target_rest <= high)
            if int(src_mask.sum()) >= 2 and int(tgt_mask.sum()) >= 2:
                diffs.append(float(abs(source_y[src_mask, item_idx].mean() - target_calib_y[tgt_mask, item_idx].mean()) / 3.0))
                weights.append(int(min(src_mask.sum(), tgt_mask.sum())))
        if diffs:
            scores.append(float(np.average(diffs, weights=weights)))
        else:
            scores.append(float(abs(source_y[:, item_idx].mean() - target_calib_y[:, item_idx].mean()) / 3.0))
    score_array = np.asarray(scores, dtype=np.float64)
    span = float(score_array.max() - score_array.min())
    normalized = np.zeros_like(score_array) if span <= 1e-12 else (score_array - score_array.min()) / span
    return (1.5 - normalized).astype(np.float32)


def prepare_pair_features_for_split(
    source: pd.DataFrame,
    target: pd.DataFrame,
    feature_cols: list[str],
    target_calib_idx: np.ndarray,
    *,
    n_components: int,
    seed: int,
    pca_fit_scope: str,
) -> tuple[np.ndarray, np.ndarray, int]:
    source_x = source[feature_cols].to_numpy(dtype=np.float64)
    target_x = target[feature_cols].to_numpy(dtype=np.float64)
    scaler = StandardScaler().fit(source_x)
    source_scaled = scaler.transform(source_x)
    target_scaled = scaler.transform(target_x)
    if pca_fit_scope == "source_target_all":
        pca_fit = np.vstack([source_scaled, target_scaled])
    elif pca_fit_scope == "source_target_calibration":
        pca_fit = np.vstack([source_scaled, target_scaled[target_calib_idx]])
    elif pca_fit_scope == "source_only":
        pca_fit = source_scaled
    else:
        raise ValueError(f"unsupported pca_fit_scope: {pca_fit_scope}")
    max_components = min(int(n_components), pca_fit.shape[0] - 1, source_scaled.shape[1])
    if max_components < 1:
        raise ValueError("not enough rows to build a PCA adapter")
    if max_components >= source_scaled.shape[1]:
        return source_scaled.astype(np.float32), target_scaled.astype(np.float32), int(source_scaled.shape[1])
    pca = PCA(n_components=max_components, random_state=int(seed))
    pca.fit(pca_fit)
    return pca.transform(source_scaled).astype(np.float32), pca.transform(target_scaled).astype(np.float32), int(max_components)


class TCPSOrdinalHead(nn.Module):
    def __init__(self, n_items: int, *, adapt_slope: bool) -> None:
        super().__init__()
        self.n_items = int(n_items)
        self.n_classes = 4
        self.adapt_slope = bool(adapt_slope)
        self.raw_slope = nn.Parameter(torch.full((n_items,), 0.4))
        self.cut_start = nn.Parameter(torch.full((n_items, 1), -1.0))
        self.raw_delta = nn.Parameter(torch.zeros(n_items, self.n_classes - 2))
        self.target_slope_residual = nn.Parameter(torch.zeros(n_items))
        self.target_cut_start_residual = nn.Parameter(torch.zeros(n_items, 1))
        self.target_raw_delta_residual = nn.Parameter(torch.zeros(n_items, self.n_classes - 2))

    def cutpoints(self, *, target_specific: bool) -> torch.Tensor:
        start = self.cut_start
        raw_delta = self.raw_delta
        if target_specific:
            start = start + self.target_cut_start_residual
            raw_delta = raw_delta + self.target_raw_delta_residual
        deltas = F.softplus(raw_delta) + 1e-3
        tail = start + torch.cumsum(deltas, dim=1)
        return torch.cat([start, tail], dim=1)

    def slope(self, *, target_specific: bool) -> torch.Tensor:
        raw_slope = self.raw_slope
        if target_specific and self.adapt_slope:
            raw_slope = raw_slope + self.target_slope_residual
        return F.softplus(raw_slope) + 1e-3

    def forward(self, symptom_scores: torch.Tensor, *, target_specific: bool) -> tuple[torch.Tensor, torch.Tensor]:
        cutpoints = self.cutpoints(target_specific=target_specific).unsqueeze(0)
        slope = self.slope(target_specific=target_specific).view(1, self.n_items, 1)
        logits = cutpoints - slope * symptom_scores.unsqueeze(-1)
        cumulative = torch.sigmoid(logits)
        p0 = cumulative[..., 0:1]
        p1 = cumulative[..., 1:2] - cumulative[..., 0:1]
        p2 = cumulative[..., 2:3] - cumulative[..., 1:2]
        p3 = 1.0 - cumulative[..., 2:3]
        probs = torch.cat([p0, p1, p2, p3], dim=-1).clamp_min(1e-7)
        probs = probs / probs.sum(dim=-1, keepdim=True)
        levels = torch.arange(self.n_classes, dtype=probs.dtype, device=probs.device)
        expected = torch.sum(probs * levels.view(1, 1, -1), dim=-1)
        return probs, expected

    def residual_matrix(self) -> torch.Tensor:
        parts = [self.target_cut_start_residual, self.target_raw_delta_residual]
        if self.adapt_slope:
            parts.append(self.target_slope_residual.view(self.n_items, 1))
        return torch.cat([part.reshape(self.n_items, -1) for part in parts], dim=1)

    def residual_norms(self) -> torch.Tensor:
        return torch.linalg.vector_norm(self.residual_matrix(), dim=1)

    def proximal_group_lasso(self, strength: float, weights: torch.Tensor, lr: float) -> None:
        if strength <= 0.0:
            return
        with torch.no_grad():
            matrix = self.residual_matrix()
            norms = torch.linalg.vector_norm(matrix, dim=1)
            shrink = torch.clamp(1.0 - float(lr) * float(strength) * weights / norms.clamp_min(1e-12), min=0.0)
            self.target_cut_start_residual.mul_(shrink.view(self.n_items, 1))
            self.target_raw_delta_residual.mul_(shrink.view(self.n_items, 1))
            if self.adapt_slope:
                self.target_slope_residual.mul_(shrink)


class TCPSOrdinalNet(nn.Module):
    def __init__(self, input_dim: int, hidden_dim: int, symptom_dim: int, dropout: float, *, adapt_slope: bool) -> None:
        super().__init__()
        self.projector = nn.Sequential(
            nn.Linear(input_dim, hidden_dim),
            nn.GELU(),
            nn.Dropout(dropout),
            nn.LayerNorm(hidden_dim),
            nn.Linear(hidden_dim, hidden_dim),
            nn.GELU(),
        )
        self.symptom_layer = nn.Linear(hidden_dim, symptom_dim)
        self.head = TCPSOrdinalHead(symptom_dim, adapt_slope=adapt_slope)

    def symptom_scores(self, inputs: torch.Tensor) -> torch.Tensor:
        return self.symptom_layer(self.projector(inputs))

    def forward(self, inputs: torch.Tensor, *, target_specific: bool) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
        symptoms = self.symptom_scores(inputs)
        probs, expected = self.head(symptoms, target_specific=target_specific)
        return symptoms, probs, expected


class FixedSymptomTCPSNet(nn.Module):
    def __init__(self, n_items: int, *, mode: str, adapt_slope: bool = False) -> None:
        super().__init__()
        self.mode = mode
        self.shared = mv24.CorpusOrdinalHead(n_items)
        self.source = mv24.CorpusOrdinalHead(n_items)
        self.target = mv24.CorpusOrdinalHead(n_items)
        self.tcps = TCPSOrdinalHead(n_items, adapt_slope=adapt_slope)

    def forward(self, symptoms: torch.Tensor, *, target_specific: bool) -> tuple[torch.Tensor, torch.Tensor]:
        if self.mode == "shared":
            return self.shared(symptoms)
        if self.mode == "specific":
            return self.target(symptoms) if target_specific else self.source(symptoms)
        return self.tcps(symptoms, target_specific=target_specific)

    def residual_norms(self) -> np.ndarray | None:
        if self.mode != "tcps":
            return None
        return self.tcps.residual_norms().detach().cpu().numpy().astype(np.float32)

    def proximal_group_lasso(self, strength: float, weights: torch.Tensor, lr: float) -> None:
        if self.mode == "tcps":
            self.tcps.proximal_group_lasso(strength, weights, lr)


def train_target_only_ordinal(
    target_dataset: str,
    target_x_all: np.ndarray,
    target_y_all: np.ndarray,
    target_calib_idx: np.ndarray,
    *,
    seed: int,
    args: argparse.Namespace,
) -> MethodPrediction:
    mv24.set_seed(seed)
    device = device_from_args(args)
    model = mv24.MeasurementAwareOrdinalNet(
        target_x_all.shape[1],
        args.hidden_dim,
        target_y_all.shape[1],
        args.dropout,
        shared_head=False,
    ).to(device)
    xt = mv24.tensor(target_x_all, device)
    yt = mv24.tensor(target_y_all, device, dtype=torch.long)
    target_calib = torch.as_tensor(target_calib_idx, dtype=torch.long, device=device)
    optimizer = torch.optim.AdamW(model.parameters(), lr=args.learning_rate, weight_decay=args.weight_decay)
    for _ in range(int(args.target_only_epochs)):
        optimizer.zero_grad(set_to_none=True)
        _, probs, _ = model(xt[target_calib], target_dataset)
        loss = mv24.ordinal_nll(probs, yt[target_calib])
        loss.backward()
        optimizer.step()
    model.eval()
    with torch.inference_mode():
        _, probs, expected = model(xt, target_dataset)
    return MethodPrediction(
        pred_all=expected.detach().cpu().numpy().astype(np.float32),
        probs_all=probs.detach().cpu().numpy().astype(np.float32),
        residual_norms=None,
        audit_weights=None,
        specificity_ratio=math.nan,
    )


def train_existing_ordinal(
    mode: str,
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
) -> MethodPrediction:
    mv24_mode = "shared_head_joint_adaptation" if mode == "shared_ordinal_head" else "full_without_mmd"
    model = mv24.train_measurement_model(
        mv24_mode,
        source_dataset,
        target_dataset,
        source_x,
        source_y,
        target_x_all,
        target_y_all,
        target_calib_idx,
        seed=seed,
        args=args,
        latent_mmd_weight=0.0,
    )
    pred_all, _, probs, _, _, _ = mv24.predict_measurement_model(
        model,
        source_dataset,
        target_dataset,
        source_x,
        target_x_all,
        args=args,
    )
    return MethodPrediction(pred_all, probs, None, None, math.nan)


def train_tcps(
    method: str,
    source_x: np.ndarray,
    source_y: np.ndarray,
    target_x_all: np.ndarray,
    target_y_all: np.ndarray,
    target_calib_idx: np.ndarray,
    *,
    lambda_group: float,
    seed: int,
    args: argparse.Namespace,
    warm_state: dict[str, torch.Tensor] | None = None,
) -> MethodPrediction:
    mv24.set_seed(seed)
    device = device_from_args(args)
    adapt_slope = method == "tcps_threshold_slope"
    model = TCPSOrdinalNet(
        source_x.shape[1],
        args.hidden_dim,
        source_y.shape[1],
        args.dropout,
        adapt_slope=adapt_slope,
    ).to(device)
    xs = mv24.tensor(source_x, device)
    ys = mv24.tensor(source_y, device, dtype=torch.long)
    xt = mv24.tensor(target_x_all, device)
    yt = mv24.tensor(target_y_all, device, dtype=torch.long)
    target_calib = torch.as_tensor(target_calib_idx, dtype=torch.long, device=device)
    if method == "audit_weighted_tcps_threshold":
        weights_np = tcps_group_lasso_weights(source_y, target_y_all[target_calib_idx])
    else:
        weights_np = np.ones(source_y.shape[1], dtype=np.float32)
    weights = torch.as_tensor(weights_np, dtype=torch.float32, device=device)

    if warm_state is None:
        optimizer = torch.optim.AdamW(model.parameters(), lr=args.learning_rate, weight_decay=args.weight_decay)
        for _ in range(int(args.ordinal_epochs)):
            optimizer.zero_grad(set_to_none=True)
            _, source_probs, _ = model(xs, target_specific=False)
            loss = mv24.ordinal_nll(source_probs, ys)
            loss.backward()
            optimizer.step()
    else:
        model.load_state_dict({key: value.to(device) for key, value in warm_state.items()})

    optimizer = torch.optim.AdamW(model.parameters(), lr=args.learning_rate, weight_decay=args.weight_decay)
    for _ in range(int(args.full_epochs)):
        optimizer.zero_grad(set_to_none=True)
        source_symptoms, source_probs, _ = model(xs, target_specific=False)
        target_symptoms = model.symptom_scores(xt)
        _, target_probs, _ = model(xt[target_calib], target_specific=True)
        loss = (
            mv24.ordinal_nll(source_probs, ys)
            + float(args.target_calibration_weight) * mv24.ordinal_nll(target_probs, yt[target_calib])
            + float(args.latent_l2_weight) * (source_symptoms.pow(2).mean() + target_symptoms.pow(2).mean())
        )
        loss.backward()
        optimizer.step()
        model.head.proximal_group_lasso(lambda_group, weights, float(args.learning_rate))

    model.eval()
    with torch.inference_mode():
        _, probs, expected = model(xt, target_specific=True)
        norms = model.head.residual_norms().detach().cpu().numpy().astype(np.float32)
    specificity = float(np.mean(norms > float(args.residual_epsilon)))
    return MethodPrediction(
        pred_all=expected.detach().cpu().numpy().astype(np.float32),
        probs_all=probs.detach().cpu().numpy().astype(np.float32),
        residual_norms=norms,
        audit_weights=weights_np,
        specificity_ratio=specificity,
    )


def warm_start_tcps_state(
    source_x: np.ndarray,
    source_y: np.ndarray,
    *,
    adapt_slope: bool,
    seed: int,
    args: argparse.Namespace,
) -> dict[str, torch.Tensor]:
    mv24.set_seed(seed)
    device = device_from_args(args)
    model = TCPSOrdinalNet(
        source_x.shape[1],
        args.hidden_dim,
        source_y.shape[1],
        args.dropout,
        adapt_slope=adapt_slope,
    ).to(device)
    xs = mv24.tensor(source_x, device)
    ys = mv24.tensor(source_y, device, dtype=torch.long)
    optimizer = torch.optim.AdamW(model.parameters(), lr=args.learning_rate, weight_decay=args.weight_decay)
    for _ in range(int(args.ordinal_epochs)):
        optimizer.zero_grad(set_to_none=True)
        _, source_probs, _ = model(xs, target_specific=False)
        loss = mv24.ordinal_nll(source_probs, ys)
        loss.backward()
        optimizer.step()
    return {key: value.detach().cpu().clone() for key, value in model.state_dict().items()}


def train_and_predict_real_method(
    method: str,
    source_dataset: str,
    target_dataset: str,
    source_x: np.ndarray,
    source_y: np.ndarray,
    target_x_all: np.ndarray,
    target_y_all: np.ndarray,
    target_calib_idx: np.ndarray,
    *,
    lambda_group: float,
    seed: int,
    args: argparse.Namespace,
    tcps_warm_state: dict[str, torch.Tensor] | None = None,
) -> MethodPrediction:
    if method == "target_only_direct_mlp":
        pred = mv28.train_target_only_direct_mlp(
            target_x_all,
            target_y_all.astype(np.float32),
            target_calib_idx,
            seed=seed,
            args=args,
        )
        return MethodPrediction(pred, None, None, None, math.nan)
    if method == "target_only_ordinal":
        return train_target_only_ordinal(target_dataset, target_x_all, target_y_all, target_calib_idx, seed=seed, args=args)
    if method == "direct_multitask_shared_head":
        pred, _, _, _ = mv24.train_direct_adaptation(
            method,
            source_x,
            source_y.astype(np.float32),
            target_x_all,
            target_y_all.astype(np.float32),
            target_calib_idx,
            seed=seed,
            args=args,
        )
        return MethodPrediction(pred, None, None, None, math.nan)
    if method == "generic_target_mlp_head":
        model = mv24.train_generic_target_mlp_head(
            source_dataset,
            target_dataset,
            source_x,
            source_y.astype(np.float32),
            target_x_all,
            target_y_all.astype(np.float32),
            target_calib_idx,
            seed=seed,
            args=args,
        )
        pred, _, _, _ = mv24.predict_generic_target_mlp_head(model, source_dataset, target_dataset, source_x, target_x_all, args=args)
        return MethodPrediction(pred, None, None, None, math.nan)
    if method in {"shared_ordinal_head", "fully_corpus_specific_ordinal"}:
        return train_existing_ordinal(
            method,
            source_dataset,
            target_dataset,
            source_x,
            source_y,
            target_x_all,
            target_y_all,
            target_calib_idx,
            seed=seed,
            args=args,
        )
    if method in TCPS_METHODS:
        return train_tcps(
            method,
            source_x,
            source_y,
            target_x_all,
            target_y_all,
            target_calib_idx,
            lambda_group=lambda_group,
            seed=seed,
            args=args,
            warm_state=tcps_warm_state,
        )
    raise ValueError(f"unsupported method: {method}")


def real_method_specs(args: argparse.Namespace) -> list[tuple[str, float]]:
    specs: list[tuple[str, float]] = [(method, math.nan) for method in BASELINE_METHODS if method in set(args.methods)]
    for value in args.lambda_grid:
        if "tcps_threshold" in set(args.methods):
            specs.append(("tcps_threshold", float(value)))
    primary = float(args.primary_lambda_group)
    for method in ["tcps_threshold_slope", "audit_weighted_tcps_threshold"]:
        if method in set(args.methods):
            specs.append((method, primary))
    seen: set[tuple[str, str]] = set()
    unique: list[tuple[str, float]] = []
    for method, value in specs:
        key = (method, "nan" if pd.isna(value) else f"{value:.8g}")
        if key not in seen:
            unique.append((method, value))
            seen.add(key)
    return unique


def append_residual_rows(
    rows: list[dict[str, Any]],
    *,
    transfer_id: str,
    budget_id: str,
    split_index: int,
    method: str,
    lambda_group: float,
    target_calibration_count: int,
    target_evaluation_count: int,
    prediction: MethodPrediction,
    args: argparse.Namespace,
) -> None:
    if prediction.residual_norms is None:
        return
    for item_idx, item_id in enumerate(PHQ_ITEM_IDS):
        norm = float(prediction.residual_norms[item_idx])
        rows.append(
            {
                "transfer_id": transfer_id,
                "budget_id": budget_id,
                "split_index": int(split_index),
                "method": method,
                "lambda_group": float(lambda_group),
                "target_calibration_count": int(target_calibration_count),
                "target_evaluation_count": int(target_evaluation_count),
                "item_id": item_id,
                "audit_role": mv24.TARGETED_ITEM_ROLES[item_id],
                "residual_norm": norm,
                "residual_nonzero": bool(norm > float(args.residual_epsilon)),
                "audit_weight": float(prediction.audit_weights[item_idx]) if prediction.audit_weights is not None else math.nan,
            }
        )


def append_targeted_item_error_rows(
    rows: list[dict[str, Any]],
    *,
    transfer_id: str,
    budget_id: str,
    split_index: int,
    method: str,
    lambda_group: float,
    target_calibration_count: int,
    target_evaluation_count: int,
    pred_eval: np.ndarray,
    truth_eval: np.ndarray,
) -> None:
    metrics = mv24.targeted_item_metrics(pred_eval, truth_eval)
    base = {
        "run_id": RUN_ID,
        "transfer_id": transfer_id,
        "budget_id": budget_id,
        "split_index": int(split_index),
        "method": method,
        "method_rank": int(METHOD_ORDER.index(method)),
        "lambda_group": float(lambda_group) if np.isfinite(lambda_group) else math.nan,
        "target_calibration_count": int(target_calibration_count),
        "target_evaluation_count": int(target_evaluation_count),
    }
    for item_order, item_id in enumerate(PHQ_ITEM_IDS, start=1):
        rows.append(
            {
                **base,
                "analysis_level": "item",
                "item_set_id": item_id,
                "item_display": item_id,
                "item_ids": item_id,
                "item_count": 1,
                "audit_role": mv24.TARGETED_ITEM_ROLES[item_id],
                "item_order": item_order,
                "item_mae": float(metrics[f"target_item_mae_{item_id}"]),
            }
        )
    for set_order, (set_id, item_display, item_ids, audit_role) in enumerate(mv24.TARGETED_ITEM_SETS, start=1):
        rows.append(
            {
                **base,
                "analysis_level": "item_set",
                "item_set_id": set_id,
                "item_display": item_display,
                "item_ids": item_display,
                "item_count": len(item_ids),
                "audit_role": audit_role,
                "item_order": 100 + set_order,
                "item_mae": float(metrics[f"target_item_set_mae_{set_id}"]),
            }
        )


def run_real_split(
    source_dataset: str,
    target_dataset: str,
    raw_source: pd.DataFrame,
    raw_target: pd.DataFrame,
    source_y: np.ndarray,
    target_y_all: np.ndarray,
    feature_cols: list[str],
    budget: mv28.BudgetSpec,
    split_index: int,
    args: argparse.Namespace,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]], dict[tuple[str, str, str, str, str, str], list[float]]]:
    split_seed = int(args.seed_offset + split_index)
    target_calib_idx, target_eval_idx = mv28.split_indices_for_budget(target_y_all, budget, split_seed, args)
    source_x, target_x_all, actual_components = prepare_pair_features_for_split(
        raw_source,
        raw_target,
        feature_cols,
        target_calib_idx,
        n_components=args.pca_components,
        seed=split_seed,
        pca_fit_scope=args.pca_fit_scope,
    )
    target_y_eval = target_y_all[target_eval_idx]
    transfer_id = f"{source_dataset}_to_{target_dataset}_phq_shared"
    rows: list[dict[str, Any]] = []
    residual_rows: list[dict[str, Any]] = []
    targeted_item_rows: list[dict[str, Any]] = []
    predictions: dict[tuple[str, str], MethodPrediction] = {}
    tcps_warm_states: dict[bool, dict[str, torch.Tensor]] = {}
    for method, lambda_group in real_method_specs(args):
        tcps_warm_state = None
        if method in TCPS_METHODS:
            adapt_slope = method == "tcps_threshold_slope"
            if adapt_slope not in tcps_warm_states:
                tcps_warm_states[adapt_slope] = warm_start_tcps_state(
                    source_x,
                    source_y,
                    adapt_slope=adapt_slope,
                    seed=split_seed,
                    args=args,
                )
            tcps_warm_state = tcps_warm_states[adapt_slope]
        prediction = train_and_predict_real_method(
            method,
            source_dataset,
            target_dataset,
            source_x,
            source_y,
            target_x_all,
            target_y_all,
            target_calib_idx,
            lambda_group=float(lambda_group) if np.isfinite(lambda_group) else 0.0,
            seed=split_seed,
            args=args,
            tcps_warm_state=tcps_warm_state,
        )
        predictions[method_spec_key(method, lambda_group)] = prediction
        pred_eval = prediction.pred_all[target_eval_idx]
        probs_eval = prediction.probs_all[target_eval_idx] if prediction.probs_all is not None else None
        metrics = evaluate_prediction(pred_eval, target_y_eval, probs_eval)
        rows.append(
            {
                "run_id": RUN_ID,
                "analysis": "real_data_repeated_split",
                "transfer_id": transfer_id,
                "source_dataset": source_dataset,
                "target_dataset": target_dataset,
                "budget_id": budget.budget_id,
                "budget_is_mv24_default": bool(budget.is_mv24_default),
                "target_calibration_count": int(len(target_calib_idx)),
                "target_evaluation_count": int(len(target_eval_idx)),
                "source_participant_count": int(len(raw_source)),
                "input_columns": int(len(feature_cols)),
                "pca_components": int(actual_components),
                "split_index": int(split_index),
                "split_seed": int(split_seed),
                "method": method,
                "method_rank": int(METHOD_ORDER.index(method)),
                "lambda_group": float(lambda_group) if np.isfinite(lambda_group) else math.nan,
                "lambda_role": (
                    "primary"
                    if method in TCPS_METHODS and abs(float(lambda_group) - float(args.primary_lambda_group)) <= 1e-12
                    else "sweep"
                    if method == "tcps_threshold"
                    else "not_applicable"
                ),
                "specificity_ratio": float(prediction.specificity_ratio),
                **metrics,
            }
        )
        append_residual_rows(
            residual_rows,
            transfer_id=transfer_id,
            budget_id=budget.budget_id,
            split_index=split_index,
            method=method,
            lambda_group=float(lambda_group) if np.isfinite(lambda_group) else math.nan,
            target_calibration_count=len(target_calib_idx),
            target_evaluation_count=len(target_eval_idx),
            prediction=prediction,
            args=args,
        )
        append_targeted_item_error_rows(
            targeted_item_rows,
            transfer_id=transfer_id,
            budget_id=budget.budget_id,
            split_index=split_index,
            method=method,
            lambda_group=float(lambda_group) if np.isfinite(lambda_group) else math.nan,
            target_calibration_count=len(target_calib_idx),
            target_evaluation_count=len(target_eval_idx),
            pred_eval=pred_eval,
            truth_eval=target_y_eval,
        )
    bootstrap_values = bootstrap_delta_values(
        predictions,
        target_eval_idx,
        target_y_eval,
        transfer_id=transfer_id,
        budget_id=budget.budget_id,
        split_seed=split_seed,
        args=args,
    )
    return rows, residual_rows, targeted_item_rows, bootstrap_values


def run_real_direction(
    source_dataset: str,
    target_dataset: str,
    tables: dict[str, pd.DataFrame],
    feature_cols: list[str],
    budgets: list[mv28.BudgetSpec],
    args: argparse.Namespace,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]], dict[tuple[str, str, str, str, str, str], list[float]]]:
    raw_source = tables[source_dataset].copy()
    raw_target = tables[target_dataset].copy()
    raw_source, raw_target = mv24.sanitize_pair(raw_source, raw_target, feature_cols)
    source_y = mv24.label_arrays(raw_source)
    target_y_all = mv24.label_arrays(raw_target)
    rows: list[dict[str, Any]] = []
    residual_rows: list[dict[str, Any]] = []
    targeted_item_rows: list[dict[str, Any]] = []
    bootstrap_store: dict[tuple[str, str, str, str, str, str], list[float]] = defaultdict(list)
    for budget in budgets:
        for split_index in range(int(args.split_count)):
            split_rows, split_residual_rows, split_targeted_items, split_bootstrap = run_real_split(
                source_dataset,
                target_dataset,
                raw_source,
                raw_target,
                source_y,
                target_y_all,
                feature_cols,
                budget,
                split_index,
                args,
            )
            rows.extend(split_rows)
            residual_rows.extend(split_residual_rows)
            targeted_item_rows.extend(split_targeted_items)
            merge_bootstrap_store(bootstrap_store, split_bootstrap)
    return rows, residual_rows, targeted_item_rows, bootstrap_store


def init_parallel_worker(
    tables: dict[str, pd.DataFrame],
    feature_cols: list[str],
    budgets: list[mv28.BudgetSpec],
    args_dict: dict[str, Any],
) -> None:
    global _WORKER_TABLES, _WORKER_FEATURE_COLS, _WORKER_BUDGETS, _WORKER_ARGS
    torch.set_num_threads(1)
    _WORKER_TABLES = tables
    _WORKER_FEATURE_COLS = feature_cols
    _WORKER_BUDGETS = budgets
    _WORKER_ARGS = argparse.Namespace(**args_dict)


def run_parallel_job(job: JobSpec) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]], dict[tuple[str, str, str, str, str, str], list[float]]]:
    if _WORKER_TABLES is None or _WORKER_FEATURE_COLS is None or _WORKER_BUDGETS is None or _WORKER_ARGS is None:
        raise RuntimeError("parallel worker context is not initialized")
    raw_source = _WORKER_TABLES[job.source_dataset].copy()
    raw_target = _WORKER_TABLES[job.target_dataset].copy()
    raw_source, raw_target = mv24.sanitize_pair(raw_source, raw_target, _WORKER_FEATURE_COLS)
    source_y = mv24.label_arrays(raw_source)
    target_y_all = mv24.label_arrays(raw_target)
    return run_real_split(
        job.source_dataset,
        job.target_dataset,
        raw_source,
        raw_target,
        source_y,
        target_y_all,
        _WORKER_FEATURE_COLS,
        _WORKER_BUDGETS[int(job.budget_index)],
        int(job.split_index),
        _WORKER_ARGS,
    )


def run_real_all(
    tables: dict[str, pd.DataFrame],
    feature_cols: list[str],
    budgets: list[mv28.BudgetSpec],
    args: argparse.Namespace,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, dict[tuple[str, str, str, str, str, str], list[float]]]:
    rows: list[dict[str, Any]] = []
    residual_rows: list[dict[str, Any]] = []
    targeted_item_rows: list[dict[str, Any]] = []
    bootstrap_store: dict[tuple[str, str, str, str, str, str], list[float]] = defaultdict(list)
    if int(args.parallel_workers) > 1:
        jobs = [
            JobSpec(source_dataset, target_dataset, budget_index, split_index)
            for source_dataset, target_dataset in mv24.TRANSFER_DIRECTIONS
            for budget_index, _ in enumerate(budgets)
            for split_index in range(int(args.split_count))
        ]
        with ProcessPoolExecutor(
            max_workers=int(args.parallel_workers),
            initializer=init_parallel_worker,
            initargs=(tables, feature_cols, budgets, dict(vars(args))),
        ) as executor:
            futures = [executor.submit(run_parallel_job, job) for job in jobs]
            for done, future in enumerate(as_completed(futures), start=1):
                split_rows, split_residual_rows, split_targeted_items, split_bootstrap = future.result()
                rows.extend(split_rows)
                residual_rows.extend(split_residual_rows)
                targeted_item_rows.extend(split_targeted_items)
                merge_bootstrap_store(bootstrap_store, split_bootstrap)
                print(f"[real] completed {done}/{len(futures)} split jobs", flush=True)
    else:
        for source_dataset, target_dataset in mv24.TRANSFER_DIRECTIONS:
            direction_rows, direction_residuals, direction_targeted_items, direction_bootstrap = run_real_direction(source_dataset, target_dataset, tables, feature_cols, budgets, args)
            rows.extend(direction_rows)
            residual_rows.extend(direction_residuals)
            targeted_item_rows.extend(direction_targeted_items)
            merge_bootstrap_store(bootstrap_store, direction_bootstrap)
    metrics = pd.DataFrame(rows).sort_values(["transfer_id", "budget_id", "split_index", "method_rank", "lambda_group"]).reset_index(drop=True)
    residuals = pd.DataFrame(residual_rows)
    if not residuals.empty:
        residuals = residuals.sort_values(["transfer_id", "budget_id", "split_index", "method", "lambda_group", "item_id"]).reset_index(drop=True)
    targeted_items = pd.DataFrame(targeted_item_rows)
    if not targeted_items.empty:
        targeted_items = targeted_items.sort_values(["transfer_id", "budget_id", "split_index", "method_rank", "lambda_group", "analysis_level", "item_order"]).reset_index(drop=True)
    return metrics, residuals, targeted_items, bootstrap_store


def summarize_real(metrics: pd.DataFrame) -> pd.DataFrame:
    group_cols = [
        "transfer_id",
        "target_dataset",
        "budget_id",
        "target_calibration_count",
        "target_evaluation_count",
        "method",
        "method_rank",
        "lambda_group",
        "lambda_role",
    ]
    rows: list[dict[str, Any]] = []
    for key, group in metrics.groupby(group_cols, dropna=False):
        row = dict(zip(group_cols, key))
        row["split_count"] = int(group["split_index"].nunique())
        for metric in SUMMARY_METRICS:
            stats_row = summary_stats(pd.to_numeric(group[metric], errors="coerce").to_numpy(dtype=np.float64))
            for name, value in stats_row.items():
                if name != "count":
                    row[f"{metric}_{name}"] = value
        rows.append(row)
    return pd.DataFrame(rows).sort_values(["transfer_id", "target_calibration_count", "method_rank", "lambda_group"]).reset_index(drop=True)


def summarize_residuals(residuals: pd.DataFrame) -> pd.DataFrame:
    if residuals.empty:
        return pd.DataFrame()
    rows: list[dict[str, Any]] = []
    group_cols = [
        "transfer_id",
        "budget_id",
        "target_calibration_count",
        "target_evaluation_count",
        "method",
        "lambda_group",
        "item_id",
        "audit_role",
    ]
    for key, group in residuals.groupby(group_cols, dropna=False):
        row = dict(zip(group_cols, key))
        norm_stats = summary_stats(pd.to_numeric(group["residual_norm"], errors="coerce").to_numpy(dtype=np.float64))
        row["split_count"] = int(group["split_index"].nunique())
        row["residual_norm_mean"] = norm_stats["mean"]
        row["residual_norm_ci95_low"] = norm_stats["ci95_low"]
        row["residual_norm_ci95_high"] = norm_stats["ci95_high"]
        row["nonzero_split_fraction"] = float(group["residual_nonzero"].astype(bool).mean())
        row["audit_weight_mean"] = float(pd.to_numeric(group["audit_weight"], errors="coerce").mean())
        rows.append(row)
    return pd.DataFrame(rows).sort_values(["transfer_id", "target_calibration_count", "method", "lambda_group", "item_id"]).reset_index(drop=True)


def lower_metric_delta_summary(metrics: pd.DataFrame, primary_lambda: float) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    references = ["target_only_direct_mlp", "shared_ordinal_head", "fully_corpus_specific_ordinal", "generic_target_mlp_head"]
    focus = metrics[
        (
            (~metrics["method"].isin(TCPS_METHODS))
            | (metrics["method"].isin(TCPS_METHODS) & (metrics["lambda_group"].sub(float(primary_lambda)).abs() <= 1e-12))
        )
    ].copy()
    for (transfer_id, budget_id), group in focus.groupby(["transfer_id", "budget_id"], dropna=False):
        for tcps_method in TCPS_METHODS:
            tcps = group[
                group["method"].eq(tcps_method)
                & (group["lambda_group"].sub(float(primary_lambda)).abs() <= 1e-12)
            ].set_index("split_index")
            if tcps.empty:
                continue
            for reference in references:
                ref = group[group["method"].eq(reference)].set_index("split_index")
                common = tcps.index.intersection(ref.index)
                if len(common) == 0:
                    continue
                for metric in LOWER_IS_BETTER_METRICS:
                    tcps_values = pd.to_numeric(tcps.loc[common, metric], errors="coerce").to_numpy(dtype=np.float64)
                    ref_values = pd.to_numeric(ref.loc[common, metric], errors="coerce").to_numpy(dtype=np.float64)
                    delta = ref_values - tcps_values
                    stats_row = summary_stats(delta)
                    if stats_row["count"] == 0:
                        continue
                    descriptor = group.iloc[0]
                    rows.append(
                        {
                            "transfer_id": transfer_id,
                            "budget_id": budget_id,
                            "target_calibration_count": int(descriptor["target_calibration_count"]),
                            "target_evaluation_count": int(descriptor["target_evaluation_count"]),
                            "method": tcps_method,
                            "lambda_group": float(primary_lambda),
                            "reference_method": reference,
                            "metric": metric,
                            "delta_definition": "reference metric minus TCPS metric; positive means TCPS is lower-error",
                            "paired_split_count": int(stats_row["count"]),
                            "tcps_lower_error_split_fraction": float(np.mean(delta > 0.0)),
                            "delta_mean": stats_row["mean"],
                            "delta_ci95_low": stats_row["ci95_low"],
                            "delta_ci95_high": stats_row["ci95_high"],
                        }
                    )
    if not rows:
        return pd.DataFrame()
    return pd.DataFrame(rows).sort_values(["transfer_id", "target_calibration_count", "method", "reference_method", "metric"]).reset_index(drop=True)


def bootstrap_delta_values(
    predictions: dict[tuple[str, str], MethodPrediction],
    target_eval_idx: np.ndarray,
    target_y_eval: np.ndarray,
    *,
    transfer_id: str,
    budget_id: str,
    split_seed: int,
    args: argparse.Namespace,
) -> dict[tuple[str, str, str, str, str, str], list[float]]:
    if int(args.participant_bootstrap_draws) <= 0:
        return {}
    primary_lambda = float(args.primary_lambda_group)
    candidates = [
        method_spec_key(method, primary_lambda)
        for method in TCPS_METHODS
        if method_spec_key(method, primary_lambda) in predictions
    ]
    references = [
        method_spec_key(method, math.nan)
        for method in BOOTSTRAP_REFERENCES
        if method_spec_key(method, math.nan) in predictions
    ]
    rng = np.random.default_rng(int(split_seed) + 700001)
    n_eval = int(len(target_eval_idx))
    values: dict[tuple[str, str, str, str, str, str], list[float]] = defaultdict(list)
    eval_predictions = {
        spec: (
            prediction.pred_all[target_eval_idx],
            prediction.probs_all[target_eval_idx] if prediction.probs_all is not None else None,
        )
        for spec, prediction in predictions.items()
    }
    for _ in range(int(args.participant_bootstrap_draws)):
        sample_idx = rng.integers(0, n_eval, size=n_eval)
        sample_truth = target_y_eval[sample_idx]
        metric_cache = {
            spec: evaluate_prediction(pred[sample_idx], sample_truth, probs[sample_idx] if probs is not None else None)
            for spec, (pred, probs) in eval_predictions.items()
        }
        for candidate in candidates:
            candidate_metrics = metric_cache[candidate]
            candidate_method, candidate_lambda = candidate
            for reference in references:
                reference_metrics = metric_cache[reference]
                reference_method, _ = reference
                for metric in BOOTSTRAP_METRICS:
                    delta = float(reference_metrics[metric] - candidate_metrics[metric])
                    if np.isfinite(delta):
                        values[(transfer_id, budget_id, candidate_method, candidate_lambda, reference_method, metric)].append(delta)
    return values


def merge_bootstrap_store(
    store: dict[tuple[str, str, str, str, str, str], list[float]],
    values: dict[tuple[str, str, str, str, str, str], list[float]],
) -> None:
    for key, key_values in values.items():
        store[key].extend(key_values)


def summarize_bootstrap_store(
    store: dict[tuple[str, str, str, str, str, str], list[float]],
    metrics: pd.DataFrame,
) -> pd.DataFrame:
    if not store:
        return pd.DataFrame()
    descriptors = (
        metrics[["transfer_id", "budget_id", "target_calibration_count", "target_evaluation_count"]]
        .drop_duplicates()
        .set_index(["transfer_id", "budget_id"])
    )
    rows: list[dict[str, Any]] = []
    for (transfer_id, budget_id, method, lambda_group, reference_method, metric), values in sorted(store.items()):
        descriptor = descriptors.loc[(transfer_id, budget_id)]
        stats_row = summary_stats(values)
        rows.append(
            {
                "transfer_id": transfer_id,
                "budget_id": budget_id,
                "target_calibration_count": int(descriptor["target_calibration_count"]),
                "target_evaluation_count": int(descriptor["target_evaluation_count"]),
                "method": method,
                "lambda_group": lambda_group,
                "reference_method": reference_method,
                "metric": metric,
                "delta_definition": "reference metric minus TCPS metric; positive means TCPS is lower-error",
                "bootstrap_draw_count": int(stats_row["count"]),
                "delta_mean": stats_row["mean"],
                "delta_ci95_low": stats_row["ci95_low"],
                "delta_ci95_high": stats_row["ci95_high"],
                "tcps_lower_error_bootstrap_fraction": float(np.mean(np.asarray(values, dtype=np.float64) > 0.0)),
            }
        )
    return pd.DataFrame(rows).sort_values(["transfer_id", "target_calibration_count", "method", "reference_method", "metric"]).reset_index(drop=True)


def build_bootstrap_table(summary: pd.DataFrame) -> pd.DataFrame:
    if summary.empty:
        return pd.DataFrame()
    focus_metrics = ["target_macro_item_mae", "ordinal_nll", "ranked_probability_score", "total_calibration_in_the_large_abs"]
    focus = summary[
        summary["method"].isin(["tcps_threshold", "audit_weighted_tcps_threshold"])
        & summary["reference_method"].isin(["shared_ordinal_head", "fully_corpus_specific_ordinal", "generic_target_mlp_head"])
        & summary["metric"].isin(focus_metrics)
    ].copy()
    rows: list[dict[str, Any]] = []
    for _, row in focus.iterrows():
        rows.append(
            {
                "transfer_id": row["transfer_id"],
                "budget_id": row["budget_id"],
                "k": int(row["target_calibration_count"]),
                "eval_n": int(row["target_evaluation_count"]),
                "method": display_method(str(row["method"])),
                "reference_method": display_method(str(row["reference_method"])),
                "metric": row["metric"],
                "delta": f"{float(row['delta_mean']):.3f} [{float(row['delta_ci95_low']):.3f}, {float(row['delta_ci95_high']):.3f}]",
                "tcps_lower_error_fraction": f"{float(row['tcps_lower_error_bootstrap_fraction']):.2f}",
            }
        )
    return pd.DataFrame(rows).sort_values(["transfer_id", "k", "method", "reference_method", "metric"]).reset_index(drop=True)


def summarize_targeted_item_errors(items: pd.DataFrame) -> pd.DataFrame:
    if items.empty:
        return pd.DataFrame()
    rows: list[dict[str, Any]] = []
    group_cols = [
        "transfer_id",
        "budget_id",
        "target_calibration_count",
        "target_evaluation_count",
        "method",
        "method_rank",
        "lambda_group",
        "analysis_level",
        "item_set_id",
        "item_display",
        "item_ids",
        "item_count",
        "audit_role",
        "item_order",
    ]
    for key, group in items.groupby(group_cols, dropna=False):
        row = dict(zip(group_cols, key))
        stats_row = summary_stats(pd.to_numeric(group["item_mae"], errors="coerce").to_numpy(dtype=np.float64))
        row["split_count"] = int(group["split_index"].nunique())
        row["item_mae_mean"] = stats_row["mean"]
        row["item_mae_ci95_low"] = stats_row["ci95_low"]
        row["item_mae_ci95_high"] = stats_row["ci95_high"]
        rows.append(row)
    return pd.DataFrame(rows).sort_values(["transfer_id", "target_calibration_count", "method_rank", "lambda_group", "analysis_level", "item_order"]).reset_index(drop=True)


def targeted_item_delta_summary(items: pd.DataFrame, primary_lambda: float) -> pd.DataFrame:
    if items.empty:
        return pd.DataFrame()
    focus = items[
        (
            (~items["method"].isin(TCPS_METHODS))
            | (items["method"].isin(TCPS_METHODS) & (items["lambda_group"].sub(float(primary_lambda)).abs() <= 1e-12))
        )
    ].copy()
    rows: list[dict[str, Any]] = []
    candidates = ["tcps_threshold", "audit_weighted_tcps_threshold"]
    references = ["shared_ordinal_head", "fully_corpus_specific_ordinal"]
    group_cols = ["transfer_id", "budget_id", "analysis_level", "item_set_id"]
    for key, group in focus.groupby(group_cols, dropna=False):
        descriptor = group.iloc[0]
        for candidate in candidates:
            tcps = group[
                group["method"].eq(candidate)
                & (group["lambda_group"].sub(float(primary_lambda)).abs() <= 1e-12)
            ].set_index("split_index")
            if tcps.empty:
                continue
            for reference in references:
                ref = group[group["method"].eq(reference)].set_index("split_index")
                common = tcps.index.intersection(ref.index)
                if len(common) == 0:
                    continue
                delta = (
                    pd.to_numeric(ref.loc[common, "item_mae"], errors="coerce").to_numpy(dtype=np.float64)
                    - pd.to_numeric(tcps.loc[common, "item_mae"], errors="coerce").to_numpy(dtype=np.float64)
                )
                stats_row = summary_stats(delta)
                if stats_row["count"] == 0:
                    continue
                rows.append(
                    {
                        "transfer_id": key[0],
                        "budget_id": key[1],
                        "target_calibration_count": int(descriptor["target_calibration_count"]),
                        "target_evaluation_count": int(descriptor["target_evaluation_count"]),
                        "method": candidate,
                        "lambda_group": float(primary_lambda),
                        "reference_method": reference,
                        "analysis_level": descriptor["analysis_level"],
                        "item_set_id": descriptor["item_set_id"],
                        "item_display": descriptor["item_display"],
                        "item_ids": descriptor["item_ids"],
                        "item_count": int(descriptor["item_count"]),
                        "audit_role": descriptor["audit_role"],
                        "item_order": int(descriptor["item_order"]),
                        "delta_definition": "reference item MAE minus TCPS item MAE; positive means TCPS is lower-error",
                        "paired_split_count": int(stats_row["count"]),
                        "tcps_lower_error_split_fraction": float(np.mean(delta > 0.0)),
                        "delta_mean": stats_row["mean"],
                        "delta_ci95_low": stats_row["ci95_low"],
                        "delta_ci95_high": stats_row["ci95_high"],
                    }
                )
    if not rows:
        return pd.DataFrame()
    return pd.DataFrame(rows).sort_values(["transfer_id", "target_calibration_count", "method", "reference_method", "analysis_level", "item_order"]).reset_index(drop=True)


def build_targeted_item_delta_table(summary: pd.DataFrame) -> pd.DataFrame:
    if summary.empty:
        return pd.DataFrame()
    focus_specs = {
        ("item_set", "anchor_items"),
        ("item_set", "threshold_shift_items"),
        ("item", "C02"),
        ("item", "C06"),
    }
    focus = summary[
        summary.apply(lambda row: (row["analysis_level"], row["item_set_id"]) in focus_specs, axis=1)
        & summary["reference_method"].isin(["shared_ordinal_head", "fully_corpus_specific_ordinal"])
    ].copy()
    rows: list[dict[str, Any]] = []
    for _, row in focus.iterrows():
        rows.append(
            {
                "transfer_id": row["transfer_id"],
                "budget_id": row["budget_id"],
                "k": int(row["target_calibration_count"]),
                "eval_n": int(row["target_evaluation_count"]),
                "method": display_method(str(row["method"])),
                "reference_method": display_method(str(row["reference_method"])),
                "item": row["item_display"],
                "audit_role": row["audit_role"],
                "delta_item_mae": f"{float(row['delta_mean']):.3f} [{float(row['delta_ci95_low']):.3f}, {float(row['delta_ci95_high']):.3f}]",
                "tcps_lower_error_split_fraction": f"{float(row['tcps_lower_error_split_fraction']):.2f}",
                "method_rank": int(METHOD_ORDER.index(str(row["method"]))),
                "item_order": int(row["item_order"]),
            }
        )
    return pd.DataFrame(rows).sort_values(["transfer_id", "k", "method_rank", "reference_method", "item_order"]).drop(columns=["method_rank", "item_order"]).reset_index(drop=True)


def build_real_main_table(summary: pd.DataFrame, primary_lambda: float) -> pd.DataFrame:
    focus = summary[
        (
            (~summary["method"].isin(TCPS_METHODS))
            | (summary["method"].isin(TCPS_METHODS) & (summary["lambda_group"].sub(float(primary_lambda)).abs() <= 1e-12))
        )
    ].copy()
    rows: list[dict[str, Any]] = []
    for _, row in focus.iterrows():
        rows.append(
            {
                "transfer_id": row["transfer_id"],
                "budget_id": row["budget_id"],
                "k": int(row["target_calibration_count"]),
                "eval_n": int(row["target_evaluation_count"]),
                "method": display_method(str(row["method"])),
                "lambda_group": "" if pd.isna(row["lambda_group"]) else f"{float(row['lambda_group']):.3g}",
                "macro_item_mae": fmt_interval(row, "target_macro_item_mae"),
                "total_mae": fmt_interval(row, "target_total_mae"),
                "ordinal_nll": fmt_interval(row, "ordinal_nll"),
                "rps": fmt_interval(row, "ranked_probability_score"),
                "abs_citl": fmt_interval(row, "total_calibration_in_the_large_abs"),
                "abs_slope_error": fmt_interval(row, "total_calibration_slope_abs_error"),
                "specificity_ratio": fmt_interval(row, "specificity_ratio"),
                "method_rank": int(row["method_rank"]),
            }
        )
    return pd.DataFrame(rows).sort_values(["transfer_id", "k", "method_rank", "lambda_group"]).drop(columns=["method_rank"]).reset_index(drop=True)


def build_lambda_sensitivity_table(summary: pd.DataFrame) -> pd.DataFrame:
    table = summary[summary["method"].eq("tcps_threshold")].copy()
    rows: list[dict[str, Any]] = []
    for _, row in table.iterrows():
        rows.append(
            {
                "transfer_id": row["transfer_id"],
                "budget_id": row["budget_id"],
                "k": int(row["target_calibration_count"]),
                "lambda_group": f"{float(row['lambda_group']):.3g}",
                "macro_item_mae": fmt_interval(row, "target_macro_item_mae"),
                "ordinal_nll": fmt_interval(row, "ordinal_nll"),
                "rps": fmt_interval(row, "ranked_probability_score"),
                "abs_citl": fmt_interval(row, "total_calibration_in_the_large_abs"),
                "specificity_ratio": fmt_interval(row, "specificity_ratio"),
            }
        )
    return pd.DataFrame(rows).sort_values(["transfer_id", "k", "lambda_group"]).reset_index(drop=True)


def display_method(method: str) -> str:
    names = {
        "target_only_direct_mlp": "Target-only direct MLP",
        "target_only_ordinal": "Target-only ordinal",
        "direct_multitask_shared_head": "Direct source+target multitask",
        "shared_ordinal_head": "Shared ordinal head",
        "fully_corpus_specific_ordinal": "Fully corpus-specific ordinal",
        "generic_target_mlp_head": "Generic target MLP head",
        "tcps_threshold": "TCPS threshold residual",
        "tcps_threshold_slope": "TCPS threshold+slope residual",
        "audit_weighted_tcps_threshold": "Audit-weighted TCPS threshold",
    }
    return names.get(method, method)


def write_markdown_table(table: pd.DataFrame, path: Path) -> None:
    if table.empty:
        path.write_text("No rows were generated.\n", encoding="utf-8")
        return
    headers = list(table.columns)
    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join(["---" for _ in headers]) + " |",
    ]
    for _, row in table.iterrows():
        lines.append("| " + " | ".join(md_escape(row[column]) for column in headers) + " |")
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def build_residual_support_table(summary: pd.DataFrame, primary_lambda: float) -> pd.DataFrame:
    focus = summary[
        summary["method"].isin(TCPS_METHODS)
        & (summary["lambda_group"].sub(float(primary_lambda)).abs() <= 1e-12)
    ].copy()
    rows: list[dict[str, Any]] = []
    for _, row in focus.iterrows():
        rows.append(
            {
                "transfer_id": row["transfer_id"],
                "budget_id": row["budget_id"],
                "k": int(row["target_calibration_count"]),
                "method": display_method(str(row["method"])),
                "item_id": row["item_id"],
                "audit_role": row["audit_role"],
                "residual_norm": f"{float(row['residual_norm_mean']):.3f} [{float(row['residual_norm_ci95_low']):.3f}, {float(row['residual_norm_ci95_high']):.3f}]",
                "nonzero_split_fraction": f"{float(row['nonzero_split_fraction']):.2f}",
                "audit_weight_mean": "" if pd.isna(row["audit_weight_mean"]) else f"{float(row['audit_weight_mean']):.3f}",
            }
        )
    return pd.DataFrame(rows).sort_values(["transfer_id", "k", "method", "item_id"]).reset_index(drop=True)


def build_observed_theta_table(args: argparse.Namespace) -> pd.DataFrame:
    tables, _, _ = mv24.load_official_view_tables(args)
    frames: list[pd.DataFrame] = []
    for dataset, table in tables.items():
        frame = table[PHQ_ITEM_IDS].copy()
        frame["dataset"] = dataset
        frame["core_total"] = frame[PHQ_ITEM_IDS].sum(axis=1).astype(float)
        frames.append(frame)
    observed = pd.concat(frames, ignore_index=True)
    return mv19.build_observed_theta(observed)


def ordered_probs_from_params(symptoms: np.ndarray, slopes: np.ndarray, cutpoints: np.ndarray) -> np.ndarray:
    logits = cutpoints[None, :, :] - slopes[None, :, None] * symptoms[:, :, None]
    cumulative = 1.0 / (1.0 + np.exp(-logits))
    p0 = cumulative[..., 0:1]
    p1 = cumulative[..., 1:2] - cumulative[..., 0:1]
    p2 = cumulative[..., 2:3] - cumulative[..., 1:2]
    p3 = 1.0 - cumulative[..., 2:3]
    probs = np.clip(np.concatenate([p0, p1, p2, p3], axis=-1), 1e-7, 1.0)
    return probs / probs.sum(axis=-1, keepdims=True)


def sample_ordinal(probs: np.ndarray, rng: np.random.Generator) -> np.ndarray:
    draws = rng.random(size=probs.shape[:2])
    cdf = np.cumsum(probs, axis=-1)
    return (draws[:, :, None] > cdf).sum(axis=-1).astype(np.int64)


def simulation_offsets(world_id: str, rng: np.random.Generator) -> np.ndarray:
    offsets = np.zeros((len(PHQ_ITEM_IDS), 3), dtype=np.float32)
    if world_id == "H_sparse_C02_C06_threshold_DIF":
        offsets[PHQ_ITEM_IDS.index("C02")] = np.asarray([-0.70, -0.55, -0.35], dtype=np.float32)
        offsets[PHQ_ITEM_IDS.index("C06")] = np.asarray([0.35, 0.55, 0.75], dtype=np.float32)
    elif world_id == "H_dense_threshold_DIF":
        signs = rng.choice([-1.0, 1.0], size=(len(PHQ_ITEM_IDS), 1))
        magnitudes = rng.uniform(0.25, 0.75, size=(len(PHQ_ITEM_IDS), 1))
        offsets = (signs * magnitudes * np.asarray([[0.75, 1.0, 1.25]])).astype(np.float32)
    return offsets


def simulate_fixed_symptom_world(
    observed: pd.DataFrame,
    world_id: str,
    draw_id: int,
    rng: np.random.Generator,
) -> dict[str, dict[str, np.ndarray]]:
    item_bias = np.linspace(-0.35, 0.35, len(PHQ_ITEM_IDS), dtype=np.float32)
    slopes = np.linspace(0.85, 1.25, len(PHQ_ITEM_IDS), dtype=np.float32)
    cutpoints = np.stack(
        [
            np.asarray([-1.00, -0.10, 0.85], dtype=np.float32) + item_bias[idx]
            for idx in range(len(PHQ_ITEM_IDS))
        ],
        axis=0,
    )
    cmdc_offsets = simulation_offsets(world_id, rng)
    output: dict[str, dict[str, np.ndarray]] = {}
    for dataset, group in observed.groupby("dataset", sort=False):
        theta_pool = group["theta_proxy_z"].to_numpy(dtype=np.float32)
        theta = rng.choice(theta_pool, size=len(group), replace=True)
        theta = theta + rng.normal(0.0, mv19.THETA_JITTER_SD, size=len(group)).astype(np.float32)
        symptoms = theta[:, None] + rng.normal(0.0, 0.35, size=(len(group), len(PHQ_ITEM_IDS))).astype(np.float32)
        probs = ordered_probs_from_params(
            symptoms,
            slopes,
            cutpoints + (cmdc_offsets if dataset == "cmdc" else 0.0),
        )
        output[dataset] = {"symptoms": symptoms.astype(np.float32), "labels": sample_ordinal(probs, rng)}
    return output


def train_fixed_symptom_head(
    method: str,
    source_symptoms: np.ndarray,
    source_y: np.ndarray,
    target_symptoms: np.ndarray,
    target_y: np.ndarray,
    target_calib_idx: np.ndarray,
    *,
    lambda_group: float,
    seed: int,
    args: argparse.Namespace,
) -> MethodPrediction:
    mv24.set_seed(seed)
    device = device_from_args(args)
    mode = {"shared_ordinal_head": "shared", "fully_corpus_specific_ordinal": "specific", "tcps_threshold": "tcps"}[method]
    model = FixedSymptomTCPSNet(source_y.shape[1], mode=mode, adapt_slope=False).to(device)
    xs = mv24.tensor(source_symptoms, device)
    ys = mv24.tensor(source_y, device, dtype=torch.long)
    xt = mv24.tensor(target_symptoms, device)
    yt = mv24.tensor(target_y, device, dtype=torch.long)
    target_calib = torch.as_tensor(target_calib_idx, dtype=torch.long, device=device)
    weights = torch.ones(source_y.shape[1], dtype=torch.float32, device=device)
    optimizer = torch.optim.AdamW(model.parameters(), lr=args.learning_rate, weight_decay=args.weight_decay)
    for _ in range(int(args.sim_epochs)):
        optimizer.zero_grad(set_to_none=True)
        source_probs, _ = model(xs, target_specific=False)
        target_probs, _ = model(xt[target_calib], target_specific=True)
        loss = mv24.ordinal_nll(source_probs, ys) + float(args.target_calibration_weight) * mv24.ordinal_nll(target_probs, yt[target_calib])
        loss.backward()
        optimizer.step()
        model.proximal_group_lasso(lambda_group, weights, float(args.learning_rate))
    model.eval()
    with torch.inference_mode():
        probs, expected = model(xt, target_specific=True)
    norms = model.residual_norms()
    specificity = float(np.mean(norms > float(args.residual_epsilon))) if norms is not None else math.nan
    return MethodPrediction(
        expected.detach().cpu().numpy().astype(np.float32),
        probs.detach().cpu().numpy().astype(np.float32),
        norms,
        np.ones(source_y.shape[1], dtype=np.float32) if norms is not None else None,
        specificity,
    )


def run_simulation_draw(observed: pd.DataFrame, world_id: str, draw_id: int, args: argparse.Namespace) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    rng = np.random.default_rng(int(args.sim_seed) + int(draw_id) * 1009 + SIMULATION_WORLDS.index(world_id) * 100003)
    rows: list[dict[str, Any]] = []
    residual_rows: list[dict[str, Any]] = []
    simulated = simulate_fixed_symptom_world(observed, world_id, draw_id, rng)
    for source_dataset, target_dataset in mv24.TRANSFER_DIRECTIONS:
        source = simulated[source_dataset]
        target = simulated[target_dataset]
        split_seed = int(args.sim_seed + draw_id * 41 + (0 if source_dataset == "edaic" else 100000))
        target_calib_idx, target_eval_idx = mv24.calibration_split_indices(
            target["labels"],
            split_seed,
            fraction=args.target_calibration_fraction,
            minimum=args.target_calibration_min,
        )
        for method in ["shared_ordinal_head", "fully_corpus_specific_ordinal", "tcps_threshold"]:
            prediction = train_fixed_symptom_head(
                method,
                source["symptoms"],
                source["labels"],
                target["symptoms"],
                target["labels"],
                target_calib_idx,
                lambda_group=float(args.primary_lambda_group),
                seed=split_seed,
                args=args,
            )
            pred_eval = prediction.pred_all[target_eval_idx]
            probs_eval = prediction.probs_all[target_eval_idx] if prediction.probs_all is not None else None
            truth_eval = target["labels"][target_eval_idx]
            metrics = evaluate_prediction(pred_eval, truth_eval, probs_eval)
            transfer_id = f"{source_dataset}_to_{target_dataset}_phq_shared"
            rows.append(
                {
                    "run_id": RUN_ID,
                    "analysis": "fixed_latent_simulation",
                    "world_id": world_id,
                    "draw_id": int(draw_id),
                    "transfer_id": transfer_id,
                    "source_dataset": source_dataset,
                    "target_dataset": target_dataset,
                    "method": method,
                    "method_rank": int(METHOD_ORDER.index(method)),
                    "lambda_group": float(args.primary_lambda_group) if method == "tcps_threshold" else math.nan,
                    "target_calibration_count": int(len(target_calib_idx)),
                    "target_evaluation_count": int(len(target_eval_idx)),
                    "specificity_ratio": float(prediction.specificity_ratio),
                    **metrics,
                }
            )
            append_residual_rows(
                residual_rows,
                transfer_id=transfer_id,
                budget_id=world_id,
                split_index=draw_id,
                method=method,
                lambda_group=float(args.primary_lambda_group) if method == "tcps_threshold" else math.nan,
                target_calibration_count=len(target_calib_idx),
                target_evaluation_count=len(target_eval_idx),
                prediction=prediction,
                args=args,
            )
    return rows, residual_rows


def init_sim_worker(observed: pd.DataFrame, args_dict: dict[str, Any]) -> None:
    global _WORKER_OBSERVED, _WORKER_ARGS
    torch.set_num_threads(1)
    _WORKER_OBSERVED = observed
    _WORKER_ARGS = argparse.Namespace(**args_dict)


def run_sim_parallel_job(job: tuple[str, int]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    if _WORKER_OBSERVED is None or _WORKER_ARGS is None:
        raise RuntimeError("simulation worker context is not initialized")
    world_id, draw_id = job
    return run_simulation_draw(_WORKER_OBSERVED, world_id, int(draw_id), _WORKER_ARGS)


def run_simulation(args: argparse.Namespace) -> tuple[pd.DataFrame, pd.DataFrame]:
    observed = build_observed_theta_table(args)
    rows: list[dict[str, Any]] = []
    residual_rows: list[dict[str, Any]] = []
    jobs = [(world_id, draw_id) for world_id in SIMULATION_WORLDS for draw_id in range(int(args.simulations))]
    if int(args.parallel_workers) > 1:
        with ProcessPoolExecutor(
            max_workers=int(args.parallel_workers),
            initializer=init_sim_worker,
            initargs=(observed, dict(vars(args))),
        ) as executor:
            futures = [executor.submit(run_sim_parallel_job, job) for job in jobs]
            for done, future in enumerate(as_completed(futures), start=1):
                draw_rows, draw_residual_rows = future.result()
                rows.extend(draw_rows)
                residual_rows.extend(draw_residual_rows)
                print(f"[simulation] completed {done}/{len(futures)} draw jobs", flush=True)
    else:
        for world_id, draw_id in jobs:
            draw_rows, draw_residual_rows = run_simulation_draw(observed, world_id, int(draw_id), args)
            rows.extend(draw_rows)
            residual_rows.extend(draw_residual_rows)
    return pd.DataFrame(rows), pd.DataFrame(residual_rows)


def summarize_simulation(metrics: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    group_cols = ["world_id", "transfer_id", "method", "method_rank", "lambda_group"]
    for key, group in metrics.groupby(group_cols, dropna=False):
        row = dict(zip(group_cols, key))
        row["draw_count"] = int(group["draw_id"].nunique())
        row["target_calibration_count"] = int(round(group["target_calibration_count"].mean()))
        row["target_evaluation_count"] = int(round(group["target_evaluation_count"].mean()))
        for metric in SUMMARY_METRICS:
            stats_row = summary_stats(pd.to_numeric(group[metric], errors="coerce").to_numpy(dtype=np.float64))
            for name, value in stats_row.items():
                if name != "count":
                    row[f"{metric}_{name}"] = value
        rows.append(row)
    return pd.DataFrame(rows).sort_values(["world_id", "transfer_id", "method_rank"]).reset_index(drop=True)


def summarize_sim_residuals(residuals: pd.DataFrame) -> pd.DataFrame:
    if residuals.empty:
        return pd.DataFrame()
    tcps = residuals[residuals["method"].eq("tcps_threshold")].copy()
    rows: list[dict[str, Any]] = []
    group_cols = ["budget_id", "transfer_id", "item_id", "audit_role"]
    for key, group in tcps.groupby(group_cols, dropna=False):
        row = dict(zip(["world_id", "transfer_id", "item_id", "audit_role"], key))
        stats_row = summary_stats(pd.to_numeric(group["residual_norm"], errors="coerce").to_numpy(dtype=np.float64))
        row["draw_count"] = int(group["split_index"].nunique())
        row["residual_norm_mean"] = stats_row["mean"]
        row["residual_norm_ci95_low"] = stats_row["ci95_low"]
        row["residual_norm_ci95_high"] = stats_row["ci95_high"]
        row["nonzero_draw_fraction"] = float(group["residual_nonzero"].astype(bool).mean())
        rows.append(row)
    return pd.DataFrame(rows).sort_values(["world_id", "transfer_id", "item_id"]).reset_index(drop=True)


def build_simulation_table(summary: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for _, row in summary.iterrows():
        rows.append(
            {
                "world_id": row["world_id"],
                "transfer_id": row["transfer_id"],
                "method": display_method(str(row["method"])),
                "macro_item_mae": fmt_interval(row, "target_macro_item_mae"),
                "ordinal_nll": fmt_interval(row, "ordinal_nll"),
                "rps": fmt_interval(row, "ranked_probability_score"),
                "abs_citl": fmt_interval(row, "total_calibration_in_the_large_abs"),
                "specificity_ratio": fmt_interval(row, "specificity_ratio"),
                "draw_count": int(row["draw_count"]),
                "method_rank": int(row["method_rank"]),
            }
        )
    return pd.DataFrame(rows).sort_values(["world_id", "transfer_id", "method_rank"]).drop(columns=["method_rank"]).reset_index(drop=True)


def real_data_gate(summary: pd.DataFrame, deltas: pd.DataFrame, primary_lambda: float) -> dict[str, Any]:
    primary = deltas[
        deltas["method"].eq("tcps_threshold")
        & deltas["lambda_group"].eq(float(primary_lambda))
        & deltas["reference_method"].isin(["shared_ordinal_head", "fully_corpus_specific_ordinal"])
        & deltas["metric"].isin(["target_macro_item_mae", "ordinal_nll", "ranked_probability_score", "total_calibration_in_the_large_abs"])
    ].copy()
    wins = primary[(primary["delta_mean"] > 0.0) & (primary["tcps_lower_error_split_fraction"] >= 0.55)]
    transfer_count = int(primary["transfer_id"].nunique()) if not primary.empty else 0
    supported_transfers = int(wins["transfer_id"].nunique()) if not wins.empty else 0
    status = "real_data_partial_support" if supported_transfers > 0 else "real_data_no_stable_advantage"
    return {
        "gate_id": "real_data_tcps_vs_extremes",
        "status": status,
        "criterion": "primary TCPS threshold residual should beat shared or fully-specific extremes on at least one lower-is-better ordinal/calibration metric with >=0.55 paired split fraction",
        "supported_transfer_count": supported_transfers,
        "evaluated_transfer_count": transfer_count,
    }


def simulation_gate(summary: pd.DataFrame, residual_summary: pd.DataFrame) -> dict[str, Any]:
    best_counts: dict[str, int] = {}
    for world_id, world_group in summary.groupby("world_id", dropna=False):
        count = 0
        for _, group in world_group.groupby("transfer_id", dropna=False):
            best = group.sort_values("target_macro_item_mae_mean").iloc[0]
            if str(best["method"]) == "tcps_threshold":
                count += 1
        best_counts[str(world_id)] = count
    sparse_support = residual_summary[
        residual_summary["world_id"].eq("H_sparse_C02_C06_threshold_DIF")
        & residual_summary["item_id"].isin(SHIFT_ITEMS)
    ]
    anchor_support = residual_summary[
        residual_summary["world_id"].eq("H_sparse_C02_C06_threshold_DIF")
        & residual_summary["item_id"].isin(ANCHOR_ITEMS)
    ]
    shift_nonzero = float(sparse_support["nonzero_draw_fraction"].mean()) if not sparse_support.empty else math.nan
    anchor_nonzero = float(anchor_support["nonzero_draw_fraction"].mean()) if not anchor_support.empty else math.nan
    status = (
        "simulation_mechanism_supported"
        if best_counts.get("H_sparse_C02_C06_threshold_DIF", 0) >= 1 and np.isfinite(shift_nonzero) and shift_nonzero > anchor_nonzero
        else "simulation_mechanism_not_clean"
    )
    return {
        "gate_id": "fixed_latent_simulation_pattern",
        "status": status,
        "criterion": "TCPS should be useful in sparse-DIF simulation and show larger support on planted C02/C06 than anchor items",
        "best_macro_item_counts": best_counts,
        "sparse_shift_nonzero_mean": shift_nonzero,
        "sparse_anchor_nonzero_mean": anchor_nonzero,
    }


def bootstrap_gate(bootstrap_summary: pd.DataFrame, primary_lambda: float) -> dict[str, Any]:
    if bootstrap_summary.empty:
        return {
            "gate_id": "participant_bootstrap_tcps_vs_extremes",
            "status": "bootstrap_not_run",
            "criterion": "paired participant bootstrap deltas should support any real-data TCPS advantage before claiming stable superiority",
            "stable_comparison_count": 0,
            "partial_comparison_count": 0,
            "evaluated_comparison_count": 0,
        }
    primary = bootstrap_summary[
        bootstrap_summary["method"].eq("tcps_threshold")
        & bootstrap_summary["lambda_group"].astype(float).eq(float(primary_lambda))
        & bootstrap_summary["reference_method"].isin(["shared_ordinal_head", "fully_corpus_specific_ordinal"])
        & bootstrap_summary["metric"].isin(
            [
                "target_macro_item_mae",
                "ordinal_nll",
                "ranked_probability_score",
                "total_calibration_in_the_large_abs",
            ]
        )
    ].copy()
    stable = primary[
        (primary["delta_mean"] > 0.0)
        & (primary["delta_ci95_low"] > 0.0)
        & (primary["tcps_lower_error_bootstrap_fraction"] >= 0.55)
    ]
    partial = primary[
        (primary["delta_mean"] > 0.0)
        & (primary["tcps_lower_error_bootstrap_fraction"] >= 0.55)
    ]
    if not stable.empty:
        status = "bootstrap_stable_support"
    elif not partial.empty:
        status = "bootstrap_partial_not_interval_stable"
    else:
        status = "bootstrap_no_stable_advantage"
    return {
        "gate_id": "participant_bootstrap_tcps_vs_extremes",
        "status": status,
        "criterion": "paired participant bootstrap deltas should support any real-data TCPS advantage before claiming stable superiority",
        "stable_comparison_count": int(len(stable)),
        "partial_comparison_count": int(len(partial)),
        "evaluated_comparison_count": int(len(primary)),
    }


def build_go_no_go(
    real_summary: pd.DataFrame,
    deltas: pd.DataFrame,
    bootstrap_summary: pd.DataFrame,
    sim_summary: pd.DataFrame,
    sim_residuals: pd.DataFrame,
    primary_lambda: float,
) -> pd.DataFrame:
    real_gate = real_data_gate(real_summary, deltas, primary_lambda)
    boot_gate = bootstrap_gate(bootstrap_summary, primary_lambda)
    sim_gate = simulation_gate(sim_summary, sim_residuals)
    if (
        real_gate["status"] == "real_data_partial_support"
        and boot_gate["status"] == "bootstrap_stable_support"
        and sim_gate["status"] == "simulation_mechanism_supported"
    ):
        overall = "go_rewrite_as_icassp_algorithm_candidate"
        recommendation = "Rewrite as TCPS method paper, keeping metric-specific and direction-specific claim boundaries visible."
    elif sim_gate["status"] == "simulation_mechanism_supported":
        overall = "borderline_audit_guided_algorithm_candidate"
        recommendation = "Use TCPS as an audit-guided algorithmic instantiation; do not claim stable real-data superiority without stronger participant-level uncertainty."
    else:
        overall = "no_go_do_not_stack_new_networks"
        recommendation = "Do not add larger fusion blocks to force novelty; keep the paper as target-comparability audit unless a new evidence source changes the result."
    rows = [
        {**real_gate, "recommendation": "Use real data to bound performance and avoid claiming universal MAE superiority."},
        {**boot_gate, "recommendation": "Use participant bootstrap deltas as the main uncertainty check for superiority wording."},
        {**sim_gate, "recommendation": "Use simulation to validate the partial-sharing mechanism under known measurement heterogeneity."},
        {
            "gate_id": "overall_icassp_positioning",
            "status": overall,
            "criterion": "Stable real-data participant-level support plus clean simulation mechanism support authorizes method-superiority wording; otherwise TCPS remains a bounded audit-guided algorithm candidate.",
            "recommendation": recommendation,
        },
    ]
    return pd.DataFrame(rows)


def write_method_contract(out_dir: Path, args: argparse.Namespace) -> None:
    contract = {
        "run_id": RUN_ID,
        "method_name": "Target-Contract Partial Sharing (TCPS)",
        "backbone_contract": "Reuses MV24 frozen Qwen3+WavLM+OpenFace subject-level representation.",
        "primary_method": "threshold residual with proximal group-lasso item sparsity",
        "primary_lambda_group": float(args.primary_lambda_group),
        "lambda_grid": [float(value) for value in args.lambda_grid],
        "lambda_policy": "Primary lambda is fixed before real-data interpretation; the full grid is reported as sensitivity and is not used to pick the main result from held-out evaluation metrics.",
        "pca_fit_scope": str(args.pca_fit_scope),
        "participant_bootstrap_draws": int(args.participant_bootstrap_draws),
        "fair_comparison_contract": "Shared ordinal, fully corpus-specific ordinal, and TCPS use the same backbone, symptom layer, ordinal loss, optimizer family, epochs, target-label split, and target-label budget.",
        "audit_weighted_variant": "Uses only source labels and the target calibration subset to weight item residual penalties.",
        "metrics": SUMMARY_METRICS,
        "external_method_basis": [
            "regularized DIF and anchor selection",
            "group pairwise penalty / partial invariance",
            "QuestMF item-wise ordinal depression modeling",
            "cumulative-link ordinal regression",
        ],
    }
    (out_dir / "method_contract.json").write_text(json.dumps(contract, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    lines = [
        "# MV32 TCPS Method Contract",
        "",
        "TCPS learns item-level target measurement residuals instead of forcing either a shared ordinal head or a fully corpus-specific ordinal head.",
        "",
        f"- Primary residual: threshold-only cumulative-logit residuals with proximal group-lasso; lambda `{args.primary_lambda_group}`.",
        f"- PCA projection scope: `{args.pca_fit_scope}`.",
        f"- Participant bootstrap draws per split: `{args.participant_bootstrap_draws}`.",
        "- Lambda policy: the primary lambda is fixed before real-data interpretation; grid results are sensitivity only.",
        "- Optional ablations: threshold+slope residuals and audit-weighted threshold residuals.",
        "- Fair comparison: same frozen MV24 representation, same shared symptom layer size, same ordinal loss, same optimizer family, same target calibration split, and same target-label budget.",
        "- The audit-weighted variant computes item penalty weights only from source labels and the current target calibration subset.",
        "- Proper ordinal metrics are first-class outputs: held-out ordinal NLL and ranked probability score, alongside MAE and calibration.",
        "- Targeted item error is reported for audit anchors and the C02/C06 threshold-shift candidates.",
    ]
    (out_dir / "method_contract.md").write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def simulation_design_contract(out_dir: Path, args: argparse.Namespace) -> None:
    rows = [
        {
            "world_id": "H0_invariant",
            "description": "No corpus-specific threshold offsets; TCPS should shrink item residuals and stay close to shared ordinal.",
        },
        {
            "world_id": "H_sparse_C02_C06_threshold_DIF",
            "description": "Only C02 and C06 receive target-corpus threshold shifts; TCPS should select these items more often than anchors.",
        },
        {
            "world_id": "H_dense_threshold_DIF",
            "description": "Most items receive threshold shifts; fully specific or low-sparsity TCPS should become competitive.",
        },
    ]
    pd.DataFrame(rows).to_csv(out_dir / "simulation_design_contract.csv", index=False)


def write_report(out_dir: Path, run_summary: dict[str, Any]) -> None:
    go = pd.read_csv(out_dir / "go_no_go_recommendations.csv")
    lines = [
        "# P5 MV32 TCPS Partial Sharing",
        "",
        f"Generated: `{run_summary['generated_at']}`",
        "",
        "## Scope",
        "",
        "MV32 evaluates Target-Contract Partial Sharing: a sparse partially shared ordinal measurement head that learns which PHQ item threshold parameters should remain shared and which need target-specific residuals.",
        "",
        "## Real-Data Main Table",
        "",
        (out_dir / "real_data_main_table.md").read_text(encoding="utf-8").strip(),
        "",
        "## TCPS Lambda Sensitivity",
        "",
        (out_dir / "lambda_sensitivity_table.md").read_text(encoding="utf-8").strip(),
        "",
        "## Participant Bootstrap",
        "",
        (out_dir / "participant_bootstrap_delta_table.md").read_text(encoding="utf-8").strip(),
        "",
        "## Residual Support",
        "",
        (out_dir / "residual_support_table.md").read_text(encoding="utf-8").strip(),
        "",
        "## Targeted Item Error",
        "",
        (out_dir / "targeted_item_error_delta_table.md").read_text(encoding="utf-8").strip(),
        "",
        "## Fixed-Latent Simulation",
        "",
        (out_dir / "simulation_table.md").read_text(encoding="utf-8").strip(),
        "",
        "## Go/No-Go",
        "",
        "| gate | status | recommendation |",
        "| --- | --- | --- |",
    ]
    for _, row in go.iterrows():
        lines.append(f"| {row['gate_id']} | `{row['status']}` | {md_escape(row['recommendation'])} |")
    lines.extend(
        [
            "",
            "## Interpretation Boundary",
            "",
            "- TCPS should be claimed as learning partial measurement sharing only where it beats shared/full-specific extremes under matched target-label exposure.",
            "- Real-data performance support is bounded: TCPS is competitive on MAE, but the shared ordinal head remains stronger on held-out ordinal NLL/RPS in these runs.",
            "- Participant bootstrap deltas do not provide stable interval-level superiority for the primary TCPS row, so superiority wording should be avoided.",
            "- The audit-weighted variant gives the cleanest real-data residual sparsity signal and should be discussed as mechanism evidence, not as uniform superiority.",
            "- The fixed-latent simulation tests mechanism behavior under known measurement heterogeneity; it does not replace real E-DAIC/CMDC evidence.",
        ]
    )
    (out_dir / "report.md").write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def artifact_hygiene(out_dir: Path) -> dict[str, Any]:
    forbidden_patterns = [
        r"/root/",
        r"/autodl-tmp/",
        r"\bsubject_id\b",
        r"\bparticipant_key\b",
        r"\btext_path\b",
        r"\baudio_path\b",
        r"\bvideo_path\b",
        r"\.wav\b",
        r"\.mp4\b",
        r"\.avi\b",
        r"raw transcript",
        r"model weight",
        r"embedding matrix",
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
        "audit_id": "P5_MV32_tcps_partial_sharing_hygiene",
        "generated_at": utc_now(),
        "files_checked": int(checked),
        "artifact_hygiene_passed": not violations,
        "violation_count": int(len(violations)),
        "violations": violations,
    }


def write_outputs(args: argparse.Namespace) -> dict[str, Any]:
    if args.clean:
        clean_tracked_outputs(args.out_dir)
    args.out_dir.mkdir(parents=True, exist_ok=True)
    torch.set_num_threads(1)
    write_method_contract(args.out_dir, args)
    simulation_design_contract(args.out_dir, args)

    tables, feature_cols, coverage = mv24.load_official_view_tables(args)
    coverage.to_csv(args.out_dir / "feature_view_contract.csv", index=False)
    budgets = mv28.budget_specs(args)

    real_metrics, residuals, targeted_items, bootstrap_store = run_real_all(tables, feature_cols, budgets, args)
    real_metrics.to_csv(args.out_dir / "real_data_by_split.csv", index=False)
    residuals.to_csv(args.out_dir / "residual_support_by_split.csv", index=False)
    targeted_items.to_csv(args.out_dir / "targeted_item_error_by_split.csv", index=False)
    bootstrap_summary = summarize_bootstrap_store(bootstrap_store, real_metrics)
    bootstrap_summary.to_csv(args.out_dir / "participant_bootstrap_delta_summary.csv", index=False)
    bootstrap_table = build_bootstrap_table(bootstrap_summary)
    bootstrap_table.to_csv(args.out_dir / "participant_bootstrap_delta_table.csv", index=False)
    write_markdown_table(bootstrap_table, args.out_dir / "participant_bootstrap_delta_table.md")
    real_summary = summarize_real(real_metrics)
    real_summary.to_csv(args.out_dir / "real_data_summary.csv", index=False)
    residual_summary = summarize_residuals(residuals)
    residual_summary.to_csv(args.out_dir / "residual_support_summary.csv", index=False)
    real_main_table = build_real_main_table(real_summary, float(args.primary_lambda_group))
    real_main_table.to_csv(args.out_dir / "real_data_main_table.csv", index=False)
    write_markdown_table(real_main_table, args.out_dir / "real_data_main_table.md")
    lambda_table = build_lambda_sensitivity_table(real_summary)
    lambda_table.to_csv(args.out_dir / "lambda_sensitivity_table.csv", index=False)
    write_markdown_table(lambda_table, args.out_dir / "lambda_sensitivity_table.md")
    residual_table = build_residual_support_table(residual_summary, float(args.primary_lambda_group))
    residual_table.to_csv(args.out_dir / "residual_support_table.csv", index=False)
    write_markdown_table(residual_table, args.out_dir / "residual_support_table.md")
    deltas = lower_metric_delta_summary(real_metrics, float(args.primary_lambda_group))
    deltas.to_csv(args.out_dir / "real_data_delta_summary.csv", index=False)
    targeted_item_summary = summarize_targeted_item_errors(targeted_items)
    targeted_item_summary.to_csv(args.out_dir / "targeted_item_error_summary.csv", index=False)
    targeted_item_deltas = targeted_item_delta_summary(targeted_items, float(args.primary_lambda_group))
    targeted_item_deltas.to_csv(args.out_dir / "targeted_item_error_delta_summary.csv", index=False)
    targeted_item_delta_table = build_targeted_item_delta_table(targeted_item_deltas)
    targeted_item_delta_table.to_csv(args.out_dir / "targeted_item_error_delta_table.csv", index=False)
    write_markdown_table(targeted_item_delta_table, args.out_dir / "targeted_item_error_delta_table.md")

    sim_metrics, sim_residuals = run_simulation(args)
    sim_metrics.to_csv(args.out_dir / "simulation_by_draw.csv", index=False)
    sim_summary = summarize_simulation(sim_metrics)
    sim_summary.to_csv(args.out_dir / "simulation_summary.csv", index=False)
    sim_residual_summary = summarize_sim_residuals(sim_residuals)
    sim_residual_summary.to_csv(args.out_dir / "simulation_residual_support_summary.csv", index=False)
    sim_table = build_simulation_table(sim_summary)
    sim_table.to_csv(args.out_dir / "simulation_table.csv", index=False)
    write_markdown_table(sim_table, args.out_dir / "simulation_table.md")

    go = build_go_no_go(real_summary, deltas, bootstrap_summary, sim_summary, sim_residual_summary, float(args.primary_lambda_group))
    go.to_csv(args.out_dir / "go_no_go_recommendations.csv", index=False)

    run_summary = {
        "run_id": RUN_ID,
        "generated_at": utc_now(),
        "git_commit": git_commit(),
        "status": "complete",
        "real_split_count": int(args.split_count),
        "simulation_draws_per_world": int(args.simulations),
        "target_budgets": [int(value) for value in args.target_budgets],
        "include_mv24_default_budget": bool(args.include_mv24_default_budget),
        "primary_lambda_group": float(args.primary_lambda_group),
        "lambda_grid": [float(value) for value in args.lambda_grid],
        "pca_fit_scope": str(args.pca_fit_scope),
        "participant_bootstrap_draws": int(args.participant_bootstrap_draws),
        "methods": list(args.methods),
        "feature_columns": int(len(feature_cols)),
        "real_rows": int(len(real_metrics)),
        "participant_bootstrap_summary_rows": int(len(bootstrap_summary)),
        "targeted_item_error_rows": int(len(targeted_items)),
        "targeted_item_delta_rows": int(len(targeted_item_deltas)),
        "simulation_rows": int(len(sim_metrics)),
        "go_no_go": json.loads(go.to_json(orient="records")),
        "aggregate_outputs_only": True,
        "tracked_outputs": sorted(TRACKED_FILES),
    }
    (args.out_dir / "run_summary.json").write_text(json.dumps(run_summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    write_report(args.out_dir, run_summary)
    hygiene = artifact_hygiene(args.out_dir)
    (args.out_dir / "artifact_hygiene_audit.json").write_text(json.dumps(hygiene, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if not hygiene["artifact_hygiene_passed"]:
        raise RuntimeError(f"artifact hygiene failed: {hygiene['violations']}")
    run_summary["artifact_hygiene_passed"] = True
    (args.out_dir / "run_summary.json").write_text(json.dumps(run_summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return run_summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-root", type=Path, default=mv24.DEFAULT_INPUT_ROOT)
    parser.add_argument("--manifest-dir", type=Path, default=mv24.DEFAULT_MANIFEST_DIR)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--split-count", type=int, default=30)
    parser.add_argument("--seed-offset", type=int, default=32000)
    parser.add_argument("--target-budgets", type=int, nargs="*", default=[])
    parser.add_argument("--include-mv24-default-budget", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--minimum-evaluation-count", type=int, default=12)
    parser.add_argument("--target-calibration-fraction", type=float, default=0.30)
    parser.add_argument("--target-calibration-min", type=int, default=24)
    parser.add_argument("--pca-components", type=int, default=128)
    parser.add_argument(
        "--pca-fit-scope",
        choices=["source_target_calibration", "source_target_all", "source_only"],
        default="source_target_calibration",
    )
    parser.add_argument("--hidden-dim", type=int, default=256)
    parser.add_argument("--dropout", type=float, default=0.08)
    parser.add_argument("--learning-rate", type=float, default=1e-3)
    parser.add_argument("--head-learning-rate", type=float, default=2e-3)
    parser.add_argument("--weight-decay", type=float, default=1e-4)
    parser.add_argument("--direct-epochs", type=int, default=500)
    parser.add_argument("--ordinal-epochs", type=int, default=500)
    parser.add_argument("--head-epochs", type=int, default=450)
    parser.add_argument("--full-epochs", type=int, default=3000)
    parser.add_argument("--target-only-epochs", type=int, default=3500)
    parser.add_argument("--target-calibration-weight", type=float, default=16.0)
    parser.add_argument("--latent-mmd-weight", type=float, default=0.0)
    parser.add_argument("--latent-l2-weight", type=float, default=1e-4)
    parser.add_argument("--lambda-grid", type=float, nargs="*", default=[0.0, 0.3, 1.0, 3.0, 10.0])
    parser.add_argument("--primary-lambda-group", type=float, default=1.0)
    parser.add_argument("--residual-epsilon", type=float, default=0.02)
    parser.add_argument("--participant-bootstrap-draws", type=int, default=200)
    parser.add_argument("--simulations", type=int, default=120)
    parser.add_argument("--sim-seed", type=int, default=20260904)
    parser.add_argument("--sim-epochs", type=int, default=1400)
    parser.add_argument("--methods", nargs="+", choices=METHOD_ORDER, default=METHOD_ORDER)
    parser.add_argument("--parallel-workers", type=int, default=1)
    parser.add_argument("--device", default="auto", help="auto, cpu, cuda, or cuda:N")
    parser.add_argument("--clean", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    run_summary = write_outputs(args)
    print(f"Wrote {RUN_ID} to {args.out_dir} with hygiene={run_summary['artifact_hygiene_passed']}")


if __name__ == "__main__":
    main()
