#!/usr/bin/env python3
"""Run MV24 formal measurement-aware ordinal architecture validation.

This runner turns the previous lightweight measurement-aware proxy into a
single executable architecture:

foundation subject representation -> shared symptom layer -> corpus-specific
cumulative-logit ordinal heads over the eight PHQ shared symptom items.

It writes aggregate-only tracked outputs. Subject-level predictions, feature
matrices, model weights, raw media, and transcripts stay out of Git.
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
from sklearn.linear_model import Ridge
from sklearn.metrics import average_precision_score, balanced_accuracy_score, f1_score, roc_auc_score
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "scripts"))

import phase5_run_mv22_foundation_backbone_validation as mv22


DEFAULT_INPUT_ROOT = Path("/root/autodl-tmp")
DEFAULT_MANIFEST_DIR = DEFAULT_INPUT_ROOT / "datasets" / "manifests"
DEFAULT_OUT_DIR = ROOT / "analysis" / "phase5_minimal_validation" / "p5_mv24_measurement_aware_ordinal_model"

PHQ_ITEM_IDS = [item[0] for item in mv22.PHQ_SHARED_ITEMS]
DATASETS = ("edaic", "cmdc")
TRANSFER_DIRECTIONS = (("edaic", "cmdc"), ("cmdc", "edaic"))
METHOD_ORDER = [
    "erm",
    "coral",
    "mmd",
    "dann",
    "strongest_foundation_baseline",
    "latent_only",
    "corpus_specific_head",
    "direct_target_finetune",
    "direct_multitask_shared_head",
    "shared_head_joint_adaptation",
    "generic_target_mlp_head",
    "full_without_mmd",
    "full_measurement_aware",
]
ZERO_TARGET_LABEL_METHODS = [
    "erm",
    "coral",
    "mmd",
    "dann",
    "strongest_foundation_baseline",
    "latent_only",
]
TARGET_CALIBRATED_METHODS = [
    "corpus_specific_head",
    "direct_target_finetune",
    "direct_multitask_shared_head",
    "shared_head_joint_adaptation",
    "generic_target_mlp_head",
    "full_without_mmd",
    "full_measurement_aware",
]
CORE_MEASUREMENT_AWARE_METHOD = "full_without_mmd"
AUXILIARY_MMD_METHOD = "full_measurement_aware"
FAIR_SHARED_LAYER_CALIBRATED_BASELINES = [
    "direct_target_finetune",
    "direct_multitask_shared_head",
    "shared_head_joint_adaptation",
    "generic_target_mlp_head",
]
TARGETED_ITEM_COMPARISON_METHODS = ("shared_head_joint_adaptation", CORE_MEASUREMENT_AWARE_METHOD)
PHQ_SHARED_BINARY_THRESHOLD = 10.0
TARGETED_ITEM_SETS = [
    ("all_shared_items", "C01-C08", PHQ_ITEM_IDS, "all shared PHQ items"),
    ("anchor_items", "C01/C04/C05/C07", ["C01", "C04", "C05", "C07"], "measurement-gate anchor items"),
    ("threshold_shift_items", "C02/C06", ["C02", "C06"], "measurement-gate threshold-shift items"),
    ("other_items", "C03/C08", ["C03", "C08"], "non-anchor non-primary-shift items"),
]
TARGETED_ITEM_ROLES = {
    "C01": "anchor",
    "C02": "threshold_shift",
    "C03": "other",
    "C04": "anchor",
    "C05": "anchor",
    "C06": "threshold_shift",
    "C07": "anchor",
    "C08": "other",
}
TARGETED_ITEM_TABLE_ROWS = [
    ("item_set", "all_shared_items"),
    ("item_set", "anchor_items"),
    ("item", "C01"),
    ("item", "C04"),
    ("item", "C05"),
    ("item", "C07"),
    ("item_set", "threshold_shift_items"),
    ("item", "C02"),
    ("item", "C06"),
    ("item_set", "other_items"),
]
TARGETED_ITEM_TIE_TOLERANCE = 0.01
METRIC_COLUMNS = [
    "target_macro_item_mae",
    "target_total_mae",
    "target_total_rmse",
    "target_total_ccc",
    "target_calibration_mae",
    "reconstruction_calibration_score",
    "target_binary_macro_f1",
    "target_binary_balanced_accuracy",
    "target_binary_auroc",
    "target_binary_auprc",
    "target_binary_sensitivity",
    "target_binary_specificity",
    "ordinal_nll",
    "feature_domain_identity_ba",
    "latent_domain_identity_ba",
    "post_head_domain_identity_ba",
]
BOUNDED_0_1_METRICS = {
    "target_binary_macro_f1",
    "target_binary_balanced_accuracy",
    "target_binary_auroc",
    "target_binary_auprc",
    "target_binary_sensitivity",
    "target_binary_specificity",
    "feature_domain_identity_ba",
    "latent_domain_identity_ba",
    "post_head_domain_identity_ba",
}
BOUNDED_MINUS1_1_METRICS = {"target_total_ccc"}
TRACKED_FILES = {
    "architecture_contract.json",
    "architecture_contract.md",
    "artifact_hygiene_audit.json",
    "feature_asset_coverage.csv",
    "feature_view_contract.csv",
    "label_budget_contract.csv",
    "main_result_table.csv",
    "main_result_table.md",
    "metrics_by_seed.csv",
    "paired_significance.csv",
    "report.md",
    "run_summary.json",
    "secondary_clinical_metrics_table.csv",
    "secondary_clinical_metrics_table.md",
    "summary_by_method.csv",
    "target_calibrated_result_table.csv",
    "target_calibrated_result_table.md",
    "mmd_sensitivity_by_seed.csv",
    "mmd_sensitivity_summary.csv",
    "mmd_sensitivity_table.csv",
    "mmd_sensitivity_table.md",
    "mmd_sensitivity_plot.png",
    "targeted_item_analysis_by_seed.csv",
    "targeted_item_analysis_summary.csv",
    "targeted_item_analysis_table.csv",
    "targeted_item_analysis_table.md",
    "zero_target_label_result_table.csv",
    "zero_target_label_result_table.md",
}


@dataclass(frozen=True)
class AssetSpec:
    asset_id: str
    modality: str
    model_name: str
    feature_prefix: str
    paths: dict[str, Path]
    canonicalizer: str = "prefix"


@dataclass(frozen=True)
class OfficialView:
    view_id: str
    modality_set: str
    assets: tuple[str, ...]
    role: str


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def rel_to_input(path: Path, input_root: Path) -> str:
    try:
        return path.resolve().relative_to(input_root.resolve()).as_posix()
    except ValueError:
        return path.name


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


def asset_specs(input_root: Path) -> dict[str, AssetSpec]:
    base = input_root / "analysis" / "phase2_baselines"
    return {
        "text_qwen3": AssetSpec(
            asset_id="text_qwen3",
            modality="text",
            model_name="Qwen/Qwen3-Embedding-0.6B",
            feature_prefix="bge_",
            paths={
                "edaic": base
                / "mv22_foundation_text_features"
                / "qwen3_embedding_0_6b"
                / "edaic_text_bge"
                / "edaic_bge_subject_features.csv",
                "cmdc": base
                / "mv22_foundation_text_features"
                / "qwen3_embedding_0_6b"
                / "cmdc_pdch_text_encoder_mlp"
                / "cmdc_bge_subject_features.csv",
            },
        ),
        "audio_wavlm_base_plus": AssetSpec(
            asset_id="audio_wavlm_base_plus",
            modality="audio",
            model_name="microsoft/wavlm-base-plus",
            feature_prefix="wavlm_",
            paths={
                "edaic": base / "edaic_audio_frozen_encoders" / "wavlm_subject_features.csv",
                "cmdc": base / "cmdc_audio_frozen_encoders" / "cmdc_wavlm_subject_features.csv",
            },
        ),
        "video_openface_common": AssetSpec(
            asset_id="video_openface_common",
            modality="video",
            model_name="OpenFace subject statistics",
            feature_prefix="of_",
            paths={
                "edaic": base / "edaic_video_features" / "edaic_openface_subject_features.csv",
                "cmdc": base / "cmdc_video_features" / "openface_statistics_subject_features.csv",
            },
            canonicalizer="openface_common",
        ),
    }


def official_view() -> OfficialView:
    return OfficialView(
        view_id="qwen3_wavlm_openface_official",
        modality_set="text_audio_video",
        assets=("text_qwen3", "audio_wavlm_base_plus", "video_openface_common"),
        role="official foundation representation for MV24 main table",
    )


def natural_sort(frame: pd.DataFrame, key: str = "participant_key") -> pd.DataFrame:
    return frame.sort_values(key, key=mv22.natural_sort_key).reset_index(drop=True)


def read_prefix_asset(spec: AssetSpec, dataset: str) -> tuple[pd.DataFrame, list[str]]:
    path = spec.paths[dataset]
    if not path.exists():
        raise FileNotFoundError(f"missing local feature cache: {path}")
    frame = pd.read_csv(path)
    if "subject_id" not in frame.columns:
        raise ValueError(f"feature cache missing subject_id: {path}")
    raw_cols = [
        column
        for column in frame.columns
        if column.startswith(spec.feature_prefix) and pd.api.types.is_numeric_dtype(frame[column])
    ]
    if not raw_cols:
        raise ValueError(f"no numeric columns with prefix {spec.feature_prefix}: {path}")
    renamed = {column: f"{spec.asset_id}__{column}" for column in raw_cols}
    out = pd.concat(
        [frame["subject_id"].astype(str).rename("participant_key"), frame[raw_cols].rename(columns=renamed)],
        axis=1,
    )
    return natural_sort(out), list(renamed.values())


def read_openface_asset(spec: AssetSpec, dataset: str) -> tuple[pd.DataFrame, list[str]]:
    path = spec.paths[dataset]
    if not path.exists():
        raise FileNotFoundError(f"missing local OpenFace cache: {path}")
    frame = pd.read_csv(path)
    if "subject_id" not in frame.columns:
        raise ValueError(f"OpenFace cache missing subject_id: {path}")
    if dataset == "edaic":
        selected = [column for column in frame.columns if column.startswith("of_")]
        canonical = {column: column for column in selected}
    else:
        selected = [column for column in frame.columns if column.startswith("of_") and column.endswith("__segment_mean")]
        canonical = {column: column.removesuffix("__segment_mean") for column in selected}
    selected = [column for column in selected if pd.api.types.is_numeric_dtype(frame[column])]
    canonical = {column: canonical[column] for column in selected}
    renamed = {column: f"{spec.asset_id}__{canonical[column]}" for column in selected}
    out = pd.concat(
        [frame["subject_id"].astype(str).rename("participant_key"), frame[selected].rename(columns=renamed)],
        axis=1,
    )
    return natural_sort(out), list(renamed.values())


def read_asset(spec: AssetSpec, dataset: str) -> tuple[pd.DataFrame, list[str]]:
    if spec.canonicalizer == "openface_common":
        return read_openface_asset(spec, dataset)
    return read_prefix_asset(spec, dataset)


def align_openface_common(
    edaic: tuple[pd.DataFrame, list[str]],
    cmdc: tuple[pd.DataFrame, list[str]],
) -> tuple[tuple[pd.DataFrame, list[str]], tuple[pd.DataFrame, list[str]]]:
    ed_frame, ed_cols = edaic
    cm_frame, cm_cols = cmdc
    common = sorted(set(ed_cols) & set(cm_cols))
    if not common:
        raise ValueError("OpenFace common view has no shared canonical columns")
    return (ed_frame[["participant_key", *common]].copy(), common), (
        cm_frame[["participant_key", *common]].copy(),
        common,
    )


def load_official_view_tables(
    args: argparse.Namespace,
) -> tuple[dict[str, pd.DataFrame], list[str], pd.DataFrame]:
    assets = asset_specs(args.input_root)
    view = official_view()
    frames_by_dataset: dict[str, list[pd.DataFrame]] = {dataset: [] for dataset in DATASETS}
    cols_by_dataset: dict[str, list[str]] = {dataset: [] for dataset in DATASETS}
    coverage_rows: list[dict[str, Any]] = []
    for asset_id in view.assets:
        spec = assets[asset_id]
        loaded = {dataset: read_asset(spec, dataset) for dataset in DATASETS}
        if spec.canonicalizer == "openface_common":
            loaded["edaic"], loaded["cmdc"] = align_openface_common(loaded["edaic"], loaded["cmdc"])
        for dataset, (frame, columns) in loaded.items():
            frames_by_dataset[dataset].append(frame)
            cols_by_dataset[dataset].extend(columns)
            coverage_rows.append(
                {
                    "view_id": view.view_id,
                    "dataset": dataset,
                    "asset_id": asset_id,
                    "modality": spec.modality,
                    "model_name": spec.model_name,
                    "rows": int(len(frame)),
                    "feature_columns": int(len(columns)),
                    "cache_ref": rel_to_input(spec.paths[dataset], args.input_root),
                }
            )
    if cols_by_dataset["edaic"] != cols_by_dataset["cmdc"]:
        raise ValueError("official view feature columns do not align across corpora")
    tables: dict[str, pd.DataFrame] = {}
    for dataset in DATASETS:
        merged = frames_by_dataset[dataset][0]
        for frame in frames_by_dataset[dataset][1:]:
            merged = merged.merge(frame, on="participant_key", how="inner")
        labels = mv22.load_phq_shared_subject_labels(args.manifest_dir, dataset)
        joined = labels.merge(merged, on="participant_key", how="inner")
        if joined.empty:
            raise ValueError(f"no joined rows for official view/{dataset}")
        tables[dataset] = natural_sort(joined)
    coverage = pd.DataFrame(coverage_rows)
    return tables, cols_by_dataset["edaic"], coverage


def sanitize_pair(source: pd.DataFrame, target: pd.DataFrame, columns: list[str]) -> tuple[pd.DataFrame, pd.DataFrame]:
    src = source.copy()
    tgt = target.copy()
    for column in columns:
        source_values = pd.to_numeric(src[column], errors="coerce").replace([np.inf, -np.inf], np.nan)
        median = float(source_values.median()) if source_values.notna().any() else 0.0
        src[column] = source_values.fillna(median)
        tgt[column] = pd.to_numeric(tgt[column], errors="coerce").replace([np.inf, -np.inf], np.nan).fillna(median)
    return src, tgt


def label_arrays(frame: pd.DataFrame) -> np.ndarray:
    values = frame[PHQ_ITEM_IDS].to_numpy(dtype=np.float32)
    return np.clip(np.rint(values), 0, 3).astype(np.int64)


def severity_groups(labels: np.ndarray) -> np.ndarray:
    totals = labels.sum(axis=1)
    return np.digitize(totals, bins=np.asarray([5.0, 10.0, 15.0], dtype=np.float32))


def calibration_split_indices(labels: np.ndarray, seed: int, *, fraction: float, minimum: int) -> tuple[np.ndarray, np.ndarray]:
    n_rows = int(labels.shape[0])
    n_calib = max(int(minimum), int(round(n_rows * float(fraction))))
    n_calib = min(n_calib, n_rows - max(12, int(round(n_rows * 0.35))))
    n_calib = max(1, n_calib)
    indices = np.arange(n_rows)
    groups = severity_groups(labels)
    group_counts = np.bincount(groups)
    stratify = groups if np.all(group_counts[group_counts > 0] >= 2) and len(np.unique(groups)) > 1 else None
    calib_idx, eval_idx = train_test_split(
        indices,
        train_size=n_calib,
        random_state=int(seed),
        shuffle=True,
        stratify=stratify,
    )
    return np.asarray(sorted(calib_idx), dtype=np.int64), np.asarray(sorted(eval_idx), dtype=np.int64)


def prepare_pair_features(
    source: pd.DataFrame,
    target: pd.DataFrame,
    feature_cols: list[str],
    *,
    n_components: int,
    seed: int,
) -> tuple[np.ndarray, np.ndarray, int]:
    source_x = source[feature_cols].to_numpy(dtype=np.float64)
    target_x = target[feature_cols].to_numpy(dtype=np.float64)
    scaler = StandardScaler().fit(source_x)
    source_scaled = scaler.transform(source_x)
    target_scaled = scaler.transform(target_x)
    max_components = min(int(n_components), source_scaled.shape[0] + target_scaled.shape[0] - 2, source_scaled.shape[1])
    if max_components < 1:
        raise ValueError("not enough rows to build a PCA adapter")
    if max_components >= source_scaled.shape[1]:
        return source_scaled.astype(np.float32), target_scaled.astype(np.float32), int(source_scaled.shape[1])
    pca = PCA(n_components=max_components, random_state=int(seed))
    pca.fit(np.vstack([source_scaled, target_scaled]))
    return pca.transform(source_scaled).astype(np.float32), pca.transform(target_scaled).astype(np.float32), int(max_components)


def clip_items(pred: np.ndarray) -> np.ndarray:
    return np.clip(pred.astype(np.float64), 0.0, 3.0)


def expected_calibration_mae(pred: np.ndarray, truth: np.ndarray, *, n_bins: int = 5) -> float:
    pred = clip_items(pred)
    truth = truth.astype(np.float64)
    if len(pred) < 2:
        return math.nan
    total = pred.sum(axis=1)
    order = np.argsort(total, kind="mergesort")
    bins = np.array_split(order, min(int(n_bins), len(order)))
    errors: list[float] = []
    weights: list[int] = []
    for bin_idx in bins:
        if len(bin_idx) == 0:
            continue
        errors.append(float(np.mean(np.abs(pred[bin_idx].mean(axis=0) - truth[bin_idx].mean(axis=0)))))
        weights.append(int(len(bin_idx)))
    return float(np.average(errors, weights=weights)) if errors else math.nan


def concordance_correlation(pred_total: np.ndarray, truth_total: np.ndarray) -> float:
    pred_total = pred_total.astype(np.float64)
    truth_total = truth_total.astype(np.float64)
    if len(pred_total) < 2:
        return math.nan
    pred_mean = float(pred_total.mean())
    truth_mean = float(truth_total.mean())
    pred_var = float(np.var(pred_total, ddof=1))
    truth_var = float(np.var(truth_total, ddof=1))
    covariance = float(np.cov(pred_total, truth_total, ddof=1)[0, 1])
    denominator = pred_var + truth_var + (pred_mean - truth_mean) ** 2
    if denominator <= 0.0:
        return math.nan
    return float((2.0 * covariance) / denominator)


def binary_endpoint_metrics(pred_total: np.ndarray, truth_total: np.ndarray) -> dict[str, float]:
    truth_binary = (truth_total >= PHQ_SHARED_BINARY_THRESHOLD).astype(int)
    pred_binary = (pred_total >= PHQ_SHARED_BINARY_THRESHOLD).astype(int)
    positives = int(truth_binary.sum())
    negatives = int(len(truth_binary) - positives)
    tp = int(((pred_binary == 1) & (truth_binary == 1)).sum())
    tn = int(((pred_binary == 0) & (truth_binary == 0)).sum())
    fp = int(((pred_binary == 1) & (truth_binary == 0)).sum())
    fn = int(((pred_binary == 0) & (truth_binary == 1)).sum())
    has_both_classes = positives > 0 and negatives > 0
    return {
        "target_binary_macro_f1": (
            float(f1_score(truth_binary, pred_binary, average="macro", zero_division=0)) if has_both_classes else math.nan
        ),
        "target_binary_balanced_accuracy": (
            float(balanced_accuracy_score(truth_binary, pred_binary)) if has_both_classes else math.nan
        ),
        "target_binary_auroc": float(roc_auc_score(truth_binary, pred_total)) if has_both_classes else math.nan,
        "target_binary_auprc": float(average_precision_score(truth_binary, pred_total)) if positives > 0 else math.nan,
        "target_binary_sensitivity": float(tp / (tp + fn)) if positives > 0 else math.nan,
        "target_binary_specificity": float(tn / (tn + fp)) if negatives > 0 else math.nan,
    }


def targeted_item_metrics(pred: np.ndarray, truth: np.ndarray) -> dict[str, float]:
    clipped = clip_items(pred)
    truth_f = truth.astype(np.float64)
    errors = np.abs(clipped - truth_f)
    metrics: dict[str, float] = {}
    for item_idx, item_id in enumerate(PHQ_ITEM_IDS):
        metrics[f"target_item_mae_{item_id}"] = float(errors[:, item_idx].mean())
    for set_id, _, item_ids, _ in TARGETED_ITEM_SETS:
        item_indices = [PHQ_ITEM_IDS.index(item_id) for item_id in item_ids]
        metrics[f"target_item_set_mae_{set_id}"] = float(errors[:, item_indices].mean())
    return metrics


def evaluate_predictions(pred: np.ndarray, truth: np.ndarray) -> dict[str, float]:
    clipped = clip_items(pred)
    truth_f = truth.astype(np.float64)
    macro = float(np.mean(np.abs(clipped - truth_f)))
    pred_total = clipped.sum(axis=1)
    truth_total = truth_f.sum(axis=1)
    total_abs = np.abs(pred_total - truth_total)
    calibration = expected_calibration_mae(clipped, truth_f)
    return {
        "target_macro_item_mae": macro,
        "target_total_mae": float(np.mean(total_abs)),
        "target_total_rmse": float(np.sqrt(np.mean(total_abs**2))),
        "target_total_ccc": concordance_correlation(pred_total, truth_total),
        "target_calibration_mae": calibration,
        "reconstruction_calibration_score": float(macro + calibration),
        **binary_endpoint_metrics(pred_total, truth_total),
        **targeted_item_metrics(pred, truth),
    }


def ordinal_nll_from_probs(probs: np.ndarray | None, truth: np.ndarray) -> float:
    if probs is None:
        return math.nan
    y = truth.astype(np.int64)
    row = np.arange(y.shape[0])[:, None]
    col = np.arange(y.shape[1])[None, :]
    chosen = np.clip(probs[row, col, y], 1e-8, 1.0)
    return float(-np.mean(np.log(chosen)))


def safe_domain_identity(source_repr: np.ndarray | None, target_repr: np.ndarray | None, seed: int) -> float:
    if source_repr is None or target_repr is None:
        return math.nan
    if len(source_repr) < 2 or len(target_repr) < 2:
        return math.nan
    return float(mv22.domain_identity_ba(source_repr.astype(np.float32), target_repr.astype(np.float32), seed=int(seed)))


def add_common_row_fields(
    *,
    view: OfficialView,
    source_dataset: str,
    target_dataset: str,
    method: str,
    seed: int,
    source_n: int,
    target_calib_n: int,
    target_eval_n: int,
    input_columns: int,
    pca_components: int,
    pred: np.ndarray,
    truth: np.ndarray,
    source_pred: np.ndarray | None,
    probs: np.ndarray | None,
    feature_source_repr: np.ndarray | None,
    feature_target_repr: np.ndarray | None,
    latent_source_repr: np.ndarray | None,
    latent_target_repr: np.ndarray | None,
    target_calibration_labels_used: bool,
    training_contract: str,
    lambda_mmd: float | None = None,
) -> dict[str, Any]:
    metrics = evaluate_predictions(pred, truth)
    post_ba = safe_domain_identity(source_pred, pred, seed)
    return {
        "view_id": view.view_id,
        "modality_set": view.modality_set,
        "transfer_id": f"{source_dataset}_to_{target_dataset}_phq_shared",
        "source_dataset": source_dataset,
        "target_dataset": target_dataset,
        "method": method,
        "method_rank": METHOD_ORDER.index(method),
        "seed": int(seed),
        "source_participant_count": int(source_n),
        "target_calibration_count": int(target_calib_n),
        "target_evaluation_count": int(target_eval_n),
        "input_columns": int(input_columns),
        "pca_components": int(pca_components),
        "target_calibration_labels_used": bool(target_calibration_labels_used),
        "training_contract": training_contract,
        "lambda_mmd": float(lambda_mmd) if lambda_mmd is not None else math.nan,
        "feature_domain_identity_ba": safe_domain_identity(feature_source_repr, feature_target_repr, seed),
        "latent_domain_identity_ba": safe_domain_identity(latent_source_repr, latent_target_repr, seed),
        "post_head_domain_identity_ba": post_ba,
        "ordinal_nll": ordinal_nll_from_probs(probs, truth),
        **metrics,
    }


class DirectRegressor(nn.Module):
    def __init__(self, input_dim: int, hidden_dim: int, output_dim: int, dropout: float) -> None:
        super().__init__()
        self.encoder = nn.Sequential(
            nn.Linear(input_dim, hidden_dim),
            nn.GELU(),
            nn.Dropout(dropout),
            nn.LayerNorm(hidden_dim),
            nn.Linear(hidden_dim, hidden_dim),
            nn.GELU(),
        )
        self.predictor = nn.Linear(hidden_dim, output_dim)

    def hidden(self, inputs: torch.Tensor) -> torch.Tensor:
        return self.encoder(inputs)

    def forward(self, inputs: torch.Tensor) -> torch.Tensor:
        return 3.0 * torch.sigmoid(self.predictor(self.hidden(inputs)))


class DirectItemHead(nn.Module):
    def __init__(self, symptom_dim: int, hidden_dim: int, output_dim: int, dropout: float) -> None:
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(symptom_dim, hidden_dim),
            nn.GELU(),
            nn.Dropout(dropout),
            nn.Linear(hidden_dim, output_dim),
        )

    def forward(self, symptoms: torch.Tensor) -> torch.Tensor:
        return 3.0 * torch.sigmoid(self.net(symptoms))


class GenericTargetMLPNet(nn.Module):
    def __init__(self, input_dim: int, hidden_dim: int, symptom_dim: int, dropout: float) -> None:
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
        self.heads = nn.ModuleDict(
            {dataset: DirectItemHead(symptom_dim, hidden_dim, symptom_dim, dropout) for dataset in DATASETS}
        )

    def symptom_scores(self, inputs: torch.Tensor) -> torch.Tensor:
        return self.symptom_layer(self.projector(inputs))

    def forward(self, inputs: torch.Tensor, corpus_id: str) -> tuple[torch.Tensor, torch.Tensor]:
        symptoms = self.symptom_scores(inputs)
        return symptoms, self.heads[corpus_id](symptoms)


class CorpusOrdinalHead(nn.Module):
    def __init__(self, n_items: int, n_classes: int = 4) -> None:
        super().__init__()
        if n_classes != 4:
            raise ValueError("MV24 fixes PHQ item categories to four ordinal levels")
        self.n_items = int(n_items)
        self.n_classes = int(n_classes)
        self.raw_slope = nn.Parameter(torch.full((n_items,), 0.4))
        self.cut_start = nn.Parameter(torch.full((n_items, 1), -1.0))
        self.raw_delta = nn.Parameter(torch.zeros(n_items, n_classes - 2))

    def cutpoints(self) -> torch.Tensor:
        deltas = F.softplus(self.raw_delta) + 1e-3
        tail = self.cut_start + torch.cumsum(deltas, dim=1)
        return torch.cat([self.cut_start, tail], dim=1)

    def forward(self, symptom_scores: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor]:
        cutpoints = self.cutpoints().unsqueeze(0)
        slope = (F.softplus(self.raw_slope) + 1e-3).view(1, self.n_items, 1)
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


class MeasurementAwareOrdinalNet(nn.Module):
    def __init__(self, input_dim: int, hidden_dim: int, symptom_dim: int, dropout: float, *, shared_head: bool = False) -> None:
        super().__init__()
        self.shared_head = bool(shared_head)
        self.projector = nn.Sequential(
            nn.Linear(input_dim, hidden_dim),
            nn.GELU(),
            nn.Dropout(dropout),
            nn.LayerNorm(hidden_dim),
            nn.Linear(hidden_dim, hidden_dim),
            nn.GELU(),
        )
        self.symptom_layer = nn.Linear(hidden_dim, symptom_dim)
        if self.shared_head:
            self.ordinal_head = CorpusOrdinalHead(symptom_dim)
        else:
            self.heads = nn.ModuleDict({dataset: CorpusOrdinalHead(symptom_dim) for dataset in DATASETS})

    def symptom_scores(self, inputs: torch.Tensor) -> torch.Tensor:
        return self.symptom_layer(self.projector(inputs))

    def head_for(self, corpus_id: str) -> CorpusOrdinalHead:
        if self.shared_head:
            return self.ordinal_head
        return self.heads[corpus_id]

    def forward(self, inputs: torch.Tensor, corpus_id: str) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
        symptoms = self.symptom_scores(inputs)
        probs, expected = self.head_for(corpus_id)(symptoms)
        return symptoms, probs, expected


def ordinal_nll(probs: torch.Tensor, targets: torch.Tensor) -> torch.Tensor:
    chosen = torch.gather(probs, dim=-1, index=targets.unsqueeze(-1)).squeeze(-1)
    return -torch.mean(torch.log(chosen.clamp_min(1e-8)))


def rbf_mmd(source: torch.Tensor, target: torch.Tensor) -> torch.Tensor:
    gammas = [0.2, 1.0, 5.0]
    total = torch.zeros((), dtype=source.dtype, device=source.device)
    for gamma in gammas:
        xx = torch.cdist(source, source, p=2).pow(2)
        yy = torch.cdist(target, target, p=2).pow(2)
        xy = torch.cdist(source, target, p=2).pow(2)
        total = total + torch.exp(-gamma * xx).mean() + torch.exp(-gamma * yy).mean() - 2.0 * torch.exp(-gamma * xy).mean()
    return total / float(len(gammas))


def set_seed(seed: int) -> None:
    np.random.seed(int(seed))
    torch.manual_seed(int(seed))
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(int(seed))


def tensor(array: np.ndarray, device: torch.device, dtype: torch.dtype = torch.float32) -> torch.Tensor:
    return torch.as_tensor(array, dtype=dtype, device=device)


def train_direct_regressor(
    source_x: np.ndarray,
    source_y: np.ndarray,
    target_x: np.ndarray,
    *,
    seed: int,
    args: argparse.Namespace,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    set_seed(seed)
    device = torch.device(args.device if args.device != "auto" else ("cuda" if torch.cuda.is_available() else "cpu"))
    model = DirectRegressor(source_x.shape[1], args.hidden_dim, source_y.shape[1], args.dropout).to(device)
    optimizer = torch.optim.AdamW(model.parameters(), lr=args.learning_rate, weight_decay=args.weight_decay)
    xs = tensor(source_x, device)
    ys = tensor(source_y.astype(np.float32), device)
    xt = tensor(target_x, device)
    for _ in range(int(args.direct_epochs)):
        optimizer.zero_grad(set_to_none=True)
        pred = model(xs)
        loss = F.mse_loss(pred, ys)
        loss.backward()
        optimizer.step()
    with torch.inference_mode():
        source_hidden = model.hidden(xs).detach().cpu().numpy().astype(np.float32)
        target_hidden = model.hidden(xt).detach().cpu().numpy().astype(np.float32)
        source_pred = model(xs).detach().cpu().numpy().astype(np.float32)
        target_pred = model(xt).detach().cpu().numpy().astype(np.float32)
    return target_pred, source_pred, source_hidden, target_hidden


def train_direct_adaptation(
    mode: str,
    source_x: np.ndarray,
    source_y: np.ndarray,
    target_x_all: np.ndarray,
    target_y_all: np.ndarray,
    target_calib_idx: np.ndarray,
    *,
    seed: int,
    args: argparse.Namespace,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    if mode not in {"direct_target_finetune", "direct_multitask_shared_head"}:
        raise ValueError(f"unknown direct adaptation mode: {mode}")
    set_seed(seed)
    device = torch.device(args.device if args.device != "auto" else ("cuda" if torch.cuda.is_available() else "cpu"))
    model = DirectRegressor(source_x.shape[1], args.hidden_dim, source_y.shape[1], args.dropout).to(device)
    xs = tensor(source_x, device)
    ys = tensor(source_y.astype(np.float32), device)
    xt = tensor(target_x_all, device)
    yt = tensor(target_y_all.astype(np.float32), device)
    target_calib = torch.as_tensor(target_calib_idx, dtype=torch.long, device=device)

    optimizer = torch.optim.AdamW(model.parameters(), lr=args.learning_rate, weight_decay=args.weight_decay)
    for _ in range(int(args.ordinal_epochs)):
        optimizer.zero_grad(set_to_none=True)
        loss = F.mse_loss(model(xs), ys)
        loss.backward()
        optimizer.step()

    optimizer = torch.optim.AdamW(model.parameters(), lr=args.learning_rate, weight_decay=args.weight_decay)
    for _ in range(int(args.full_epochs)):
        optimizer.zero_grad(set_to_none=True)
        target_loss = F.mse_loss(model(xt[target_calib]), yt[target_calib])
        if mode == "direct_multitask_shared_head":
            loss = F.mse_loss(model(xs), ys) + float(args.target_calibration_weight) * target_loss
        else:
            loss = target_loss
        loss.backward()
        optimizer.step()

    with torch.inference_mode():
        source_hidden = model.hidden(xs).detach().cpu().numpy().astype(np.float32)
        target_hidden = model.hidden(xt).detach().cpu().numpy().astype(np.float32)
        source_pred = model(xs).detach().cpu().numpy().astype(np.float32)
        target_pred = model(xt).detach().cpu().numpy().astype(np.float32)
    return target_pred, source_pred, source_hidden, target_hidden


def train_generic_target_mlp_head(
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
) -> GenericTargetMLPNet:
    set_seed(seed)
    device = torch.device(args.device if args.device != "auto" else ("cuda" if torch.cuda.is_available() else "cpu"))
    model = GenericTargetMLPNet(source_x.shape[1], args.hidden_dim, source_y.shape[1], args.dropout).to(device)
    xs = tensor(source_x, device)
    ys = tensor(source_y.astype(np.float32), device)
    xt = tensor(target_x_all, device)
    yt = tensor(target_y_all.astype(np.float32), device)
    target_calib = torch.as_tensor(target_calib_idx, dtype=torch.long, device=device)

    optimizer = torch.optim.AdamW(model.parameters(), lr=args.learning_rate, weight_decay=args.weight_decay)
    for _ in range(int(args.ordinal_epochs)):
        optimizer.zero_grad(set_to_none=True)
        source_symptoms, source_pred = model(xs, source_dataset)
        loss = F.mse_loss(source_pred, ys) + float(args.latent_l2_weight) * source_symptoms.pow(2).mean()
        loss.backward()
        optimizer.step()

    model.heads[target_dataset].load_state_dict(model.heads[source_dataset].state_dict())
    optimizer = torch.optim.AdamW(model.parameters(), lr=args.learning_rate, weight_decay=args.weight_decay)
    for _ in range(int(args.full_epochs)):
        optimizer.zero_grad(set_to_none=True)
        source_symptoms, source_pred = model(xs, source_dataset)
        target_symptoms = model.symptom_scores(xt)
        _, target_pred = model(xt[target_calib], target_dataset)
        loss = (
            F.mse_loss(source_pred, ys)
            + float(args.target_calibration_weight) * F.mse_loss(target_pred, yt[target_calib])
            + float(args.latent_l2_weight) * (source_symptoms.pow(2).mean() + target_symptoms.pow(2).mean())
        )
        loss.backward()
        optimizer.step()
    return model


def predict_generic_target_mlp_head(
    model: GenericTargetMLPNet,
    source_dataset: str,
    target_dataset: str,
    source_x: np.ndarray,
    target_x_eval: np.ndarray,
    *,
    args: argparse.Namespace,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    device = torch.device(args.device if args.device != "auto" else ("cuda" if torch.cuda.is_available() else "cpu"))
    model.eval()
    xs = tensor(source_x, device)
    xt = tensor(target_x_eval, device)
    with torch.inference_mode():
        source_sym, source_pred = model(xs, source_dataset)
        target_sym, target_pred = model(xt, target_dataset)
    return (
        target_pred.detach().cpu().numpy().astype(np.float32),
        source_pred.detach().cpu().numpy().astype(np.float32),
        source_sym.detach().cpu().numpy().astype(np.float32),
        target_sym.detach().cpu().numpy().astype(np.float32),
    )


def train_measurement_model(
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
    latent_mmd_weight: float | None = None,
) -> MeasurementAwareOrdinalNet:
    if mode not in {"latent_only", "corpus_specific_head", "shared_head_joint_adaptation", "full_without_mmd", "full_measurement_aware"}:
        raise ValueError(f"unknown measurement-aware mode: {mode}")
    set_seed(seed)
    device = torch.device(args.device if args.device != "auto" else ("cuda" if torch.cuda.is_available() else "cpu"))
    model = MeasurementAwareOrdinalNet(
        source_x.shape[1],
        args.hidden_dim,
        source_y.shape[1],
        args.dropout,
        shared_head=mode == "shared_head_joint_adaptation",
    ).to(device)
    xs = tensor(source_x, device)
    ys = tensor(source_y, device, dtype=torch.long)
    xt = tensor(target_x_all, device)
    yt = tensor(target_y_all, device, dtype=torch.long)
    target_calib = torch.as_tensor(target_calib_idx, dtype=torch.long, device=device)

    def source_loss() -> torch.Tensor:
        _, source_probs, _ = model(xs, source_dataset)
        return ordinal_nll(source_probs, ys)

    def source_warm_start(epoch_count: int) -> None:
        optimizer = torch.optim.AdamW(model.parameters(), lr=args.learning_rate, weight_decay=args.weight_decay)
        for _ in range(int(epoch_count)):
            optimizer.zero_grad(set_to_none=True)
            loss = source_loss()
            loss.backward()
            optimizer.step()

    def initialize_target_head_from_source() -> None:
        if not model.shared_head:
            model.heads[target_dataset].load_state_dict(model.heads[source_dataset].state_dict())

    if mode in {"latent_only", "corpus_specific_head"}:
        source_warm_start(args.ordinal_epochs)
        if mode == "corpus_specific_head":
            initialize_target_head_from_source()
            for param in model.projector.parameters():
                param.requires_grad = False
            for param in model.symptom_layer.parameters():
                param.requires_grad = False
            for param in model.heads[source_dataset].parameters():
                param.requires_grad = False
            optimizer = torch.optim.AdamW(
                [param for param in model.heads[target_dataset].parameters() if param.requires_grad],
                lr=args.head_learning_rate,
                weight_decay=args.weight_decay,
            )
            for _ in range(int(args.head_epochs)):
                optimizer.zero_grad(set_to_none=True)
                _, target_probs, _ = model(xt[target_calib], target_dataset)
                loss = ordinal_nll(target_probs, yt[target_calib])
                loss.backward()
                optimizer.step()
    else:
        mmd_weight = 0.0 if mode == "full_without_mmd" else float(args.latent_mmd_weight)
        if mode == "shared_head_joint_adaptation":
            mmd_weight = 0.0
        if latent_mmd_weight is not None:
            mmd_weight = float(latent_mmd_weight)
        source_warm_start(args.ordinal_epochs)
        initialize_target_head_from_source()
        optimizer = torch.optim.AdamW(model.parameters(), lr=args.learning_rate, weight_decay=args.weight_decay)
        for _ in range(int(args.full_epochs)):
            optimizer.zero_grad(set_to_none=True)
            source_symptoms, source_probs, _ = model(xs, source_dataset)
            target_symptoms = model.symptom_scores(xt)
            _, target_probs, _ = model(xt[target_calib], target_dataset)
            loss = (
                ordinal_nll(source_probs, ys)
                + float(args.target_calibration_weight) * ordinal_nll(target_probs, yt[target_calib])
                + mmd_weight * rbf_mmd(source_symptoms, target_symptoms)
                + float(args.latent_l2_weight) * (source_symptoms.pow(2).mean() + target_symptoms.pow(2).mean())
            )
            loss.backward()
            optimizer.step()
    return model


def predict_measurement_model(
    model: MeasurementAwareOrdinalNet,
    source_dataset: str,
    target_head_dataset: str,
    source_x: np.ndarray,
    target_x_eval: np.ndarray,
    *,
    args: argparse.Namespace,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    device = torch.device(args.device if args.device != "auto" else ("cuda" if torch.cuda.is_available() else "cpu"))
    model.eval()
    xs = tensor(source_x, device)
    xt = tensor(target_x_eval, device)
    with torch.inference_mode():
        source_sym, _, source_expected = model(xs, source_dataset)
        target_sym, target_probs, target_expected = model(xt, target_head_dataset)
    return (
        target_expected.detach().cpu().numpy().astype(np.float32),
        source_expected.detach().cpu().numpy().astype(np.float32),
        target_probs.detach().cpu().numpy().astype(np.float32),
        source_sym.detach().cpu().numpy().astype(np.float32),
        target_sym.detach().cpu().numpy().astype(np.float32),
        model.head_for(target_head_dataset).cutpoints().detach().cpu().numpy().astype(np.float32),
    )


def run_transfer_direction(
    source_dataset: str,
    target_dataset: str,
    tables: dict[str, pd.DataFrame],
    feature_cols: list[str],
    args: argparse.Namespace,
) -> list[dict[str, Any]]:
    view = official_view()
    raw_source = tables[source_dataset].copy()
    raw_target = tables[target_dataset].copy()
    raw_source, raw_target = sanitize_pair(raw_source, raw_target, feature_cols)
    source_y = label_arrays(raw_source)
    target_y_all = label_arrays(raw_target)
    rows: list[dict[str, Any]] = []
    selected_methods = set(args.methods)
    for seed in [int(seed) for seed in args.seeds]:
        target_calib_idx, target_eval_idx = calibration_split_indices(
            target_y_all,
            seed,
            fraction=args.target_calibration_fraction,
            minimum=args.target_calibration_min,
        )
        source_x, target_x_all, actual_components = prepare_pair_features(
            raw_source,
            raw_target,
            feature_cols,
            n_components=args.pca_components,
            seed=seed,
        )
        target_x_eval = target_x_all[target_eval_idx]
        target_y_eval = target_y_all[target_eval_idx]
        target_x_calib = target_x_all[target_calib_idx]

        ridge_inputs = [
            ("erm", source_x, target_x_eval, target_x_all, "source-only ridge on official foundation features"),
            (
                "coral",
                mv22.coral_source_to_target(source_x, target_x_all),
                target_x_eval,
                target_x_all,
                "CORAL-aligned source features plus itemwise ridge",
            ),
            (
                "mmd",
                source_x - source_x.mean(axis=0, keepdims=True) + target_x_all.mean(axis=0, keepdims=True),
                target_x_eval,
                target_x_all,
                "mean-aligned MMD proxy plus itemwise ridge",
            ),
        ]
        for method, adapted_source_x, adapted_eval_x, domain_target_x, contract in ridge_inputs:
            if method not in selected_methods:
                continue
            model = Ridge(alpha=1.0)
            model.fit(adapted_source_x, source_y.astype(np.float32))
            pred = model.predict(adapted_eval_x).astype(np.float32)
            source_pred = model.predict(adapted_source_x).astype(np.float32)
            rows.append(
                add_common_row_fields(
                    view=view,
                    source_dataset=source_dataset,
                    target_dataset=target_dataset,
                    method=method,
                    seed=seed,
                    source_n=len(raw_source),
                    target_calib_n=len(target_calib_idx),
                    target_eval_n=len(target_eval_idx),
                    input_columns=len(feature_cols),
                    pca_components=actual_components,
                    pred=pred,
                    truth=target_y_eval,
                    source_pred=source_pred,
                    probs=None,
                    feature_source_repr=adapted_source_x,
                    feature_target_repr=domain_target_x[target_eval_idx],
                    latent_source_repr=None,
                    latent_target_repr=None,
                    target_calibration_labels_used=False,
                    training_contract=contract,
                )
            )

        if "dann" in selected_methods:
            dann_pred_all, dann_source_hidden, dann_target_hidden_all = mv22.train_neural_baseline(
                "dann",
                source_x,
                source_y.astype(np.float32),
                target_x_all,
                seed=seed,
                epochs=args.dann_epochs,
                hidden_dim=args.hidden_dim,
            )
            rows.append(
                add_common_row_fields(
                    view=view,
                    source_dataset=source_dataset,
                    target_dataset=target_dataset,
                    method="dann",
                    seed=seed,
                    source_n=len(raw_source),
                    target_calib_n=len(target_calib_idx),
                    target_eval_n=len(target_eval_idx),
                    input_columns=len(feature_cols),
                    pca_components=actual_components,
                    pred=dann_pred_all[target_eval_idx],
                    truth=target_y_eval,
                    source_pred=None,
                    probs=None,
                    feature_source_repr=dann_source_hidden,
                    feature_target_repr=dann_target_hidden_all[target_eval_idx],
                    latent_source_repr=None,
                    latent_target_repr=None,
                    target_calibration_labels_used=False,
                    training_contract="DANN-style gradient reversal baseline on official foundation features",
                )
            )

        if "strongest_foundation_baseline" in selected_methods:
            direct_pred_all, direct_source_pred, direct_source_hidden, direct_target_hidden_all = train_direct_regressor(
                source_x,
                source_y.astype(np.float32),
                target_x_all,
                seed=seed,
                args=args,
            )
            rows.append(
                add_common_row_fields(
                    view=view,
                    source_dataset=source_dataset,
                    target_dataset=target_dataset,
                    method="strongest_foundation_baseline",
                    seed=seed,
                    source_n=len(raw_source),
                    target_calib_n=len(target_calib_idx),
                    target_eval_n=len(target_eval_idx),
                    input_columns=len(feature_cols),
                    pca_components=actual_components,
                    pred=direct_pred_all[target_eval_idx],
                    truth=target_y_eval,
                    source_pred=direct_source_pred,
                    probs=None,
                    feature_source_repr=direct_source_hidden,
                    feature_target_repr=direct_target_hidden_all[target_eval_idx],
                    latent_source_repr=None,
                    latent_target_repr=None,
                    target_calibration_labels_used=False,
                    training_contract="nonlinear direct foundation baseline without explicit measurement heads",
                )
            )

        direct_adaptation_modes = [
            (
                "direct_target_finetune",
                "source-warm-started direct item regressor; all shared layers updated on target calibration labels only",
            ),
            (
                "direct_multitask_shared_head",
                "direct shared item regressor with source reconstruction and target-calibration reconstruction over the same adaptation schedule",
            ),
        ]
        for method, contract in direct_adaptation_modes:
            if method not in selected_methods:
                continue
            direct_pred_all, direct_source_pred, direct_source_hidden, direct_target_hidden_all = train_direct_adaptation(
                method,
                source_x,
                source_y.astype(np.float32),
                target_x_all,
                target_y_all.astype(np.float32),
                target_calib_idx,
                seed=seed,
                args=args,
            )
            rows.append(
                add_common_row_fields(
                    view=view,
                    source_dataset=source_dataset,
                    target_dataset=target_dataset,
                    method=method,
                    seed=seed,
                    source_n=len(raw_source),
                    target_calib_n=len(target_calib_idx),
                    target_eval_n=len(target_eval_idx),
                    input_columns=len(feature_cols),
                    pca_components=actual_components,
                    pred=direct_pred_all[target_eval_idx],
                    truth=target_y_eval,
                    source_pred=direct_source_pred,
                    probs=None,
                    feature_source_repr=source_x,
                    feature_target_repr=target_x_eval,
                    latent_source_repr=direct_source_hidden,
                    latent_target_repr=direct_target_hidden_all[target_eval_idx],
                    target_calibration_labels_used=True,
                    training_contract=contract,
                )
            )

        if "generic_target_mlp_head" in selected_methods:
            generic_model = train_generic_target_mlp_head(
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
            pred, source_pred, source_sym, target_sym = predict_generic_target_mlp_head(
                generic_model,
                source_dataset,
                target_dataset,
                source_x,
                target_x_eval,
                args=args,
            )
            rows.append(
                add_common_row_fields(
                    view=view,
                    source_dataset=source_dataset,
                    target_dataset=target_dataset,
                    method="generic_target_mlp_head",
                    seed=seed,
                    source_n=len(raw_source),
                    target_calib_n=len(target_calib_idx),
                    target_eval_n=len(target_eval_idx),
                    input_columns=len(feature_cols),
                    pca_components=actual_components,
                    pred=pred,
                    truth=target_y_eval,
                    source_pred=source_pred,
                    probs=None,
                    feature_source_repr=source_x,
                    feature_target_repr=target_x_eval,
                    latent_source_repr=source_sym,
                    latent_target_repr=target_sym,
                    target_calibration_labels_used=True,
                    training_contract="generic corpus-specific MLP item heads with source and target-calibration reconstruction over the same shared layers",
                )
            )

        measurement_modes = [
            (
                "latent_only",
                source_dataset,
                False,
                "shared symptom layer trained on source; target scored through source ordinal head",
                None,
            ),
            (
                "corpus_specific_head",
                target_dataset,
                True,
                "source-trained shared symptom layer with target corpus ordinal head fit on calibration labels",
                None,
            ),
            (
                "shared_head_joint_adaptation",
                target_dataset,
                True,
                "ordinal source and target-calibration reconstruction with a forced shared ordinal head",
                0.0,
            ),
            (
                "full_without_mmd",
                target_dataset,
                True,
                "full ordinal source and target-calibration reconstruction with lambda_mmd fixed to zero",
                0.0,
            ),
            (
                "full_measurement_aware",
                target_dataset,
                True,
                "joint source ordinal reconstruction, target calibration reconstruction, and shared-symptom MMD",
                float(args.latent_mmd_weight),
            ),
        ]
        for mode, target_head_dataset, uses_calib, contract, lambda_mmd in measurement_modes:
            if mode not in selected_methods:
                continue
            model = train_measurement_model(
                mode,
                source_dataset,
                target_dataset,
                source_x,
                source_y,
                target_x_all,
                target_y_all,
                target_calib_idx,
                seed=seed,
                args=args,
                latent_mmd_weight=lambda_mmd,
            )
            pred, source_pred, probs, source_sym, target_sym, _ = predict_measurement_model(
                model,
                source_dataset,
                target_head_dataset,
                source_x,
                target_x_eval,
                args=args,
            )
            rows.append(
                add_common_row_fields(
                    view=view,
                    source_dataset=source_dataset,
                    target_dataset=target_dataset,
                    method=mode,
                    seed=seed,
                    source_n=len(raw_source),
                    target_calib_n=len(target_calib_idx),
                    target_eval_n=len(target_eval_idx),
                    input_columns=len(feature_cols),
                    pca_components=actual_components,
                    pred=pred,
                    truth=target_y_eval,
                    source_pred=source_pred,
                    probs=probs,
                    feature_source_repr=source_x,
                    feature_target_repr=target_x_eval,
                    latent_source_repr=source_sym,
                    latent_target_repr=target_sym,
                    target_calibration_labels_used=uses_calib,
                    training_contract=contract,
                    lambda_mmd=lambda_mmd,
                )
            )
    return rows


def summarize_metrics(metrics: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    grouped = metrics.groupby(["transfer_id", "method", "method_rank"], dropna=False)
    for (transfer_id, method, method_rank), group in grouped:
        row: dict[str, Any] = {
            "transfer_id": transfer_id,
            "method": method,
            "method_rank": int(method_rank),
            "seed_count": int(group["seed"].nunique()),
            "target_calibration_labels_used": bool(group["target_calibration_labels_used"].iloc[0]),
            "source_participant_count": int(round(group["source_participant_count"].mean())),
            "target_calibration_count": int(round(group["target_calibration_count"].mean())),
            "target_evaluation_count": int(round(group["target_evaluation_count"].mean())),
            "input_columns": int(group["input_columns"].max()),
            "pca_components": int(group["pca_components"].max()),
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


def supervision_regime(target_calibration_labels_used: bool) -> str:
    return "target_calibrated" if target_calibration_labels_used else "zero_target_label"


def labeled_target_calibration_count(row: pd.Series) -> int:
    return int(row["target_calibration_count"]) if bool(row["target_calibration_labels_used"]) else 0


def paired_significance(metrics: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for transfer_id, transfer_group in metrics.groupby("transfer_id", dropna=False):
        core = (
            transfer_group[transfer_group["method"] == CORE_MEASUREMENT_AWARE_METHOD]
            .set_index("seed")["reconstruction_calibration_score"]
            .sort_index()
        )
        for method, method_group in transfer_group.groupby("method", dropna=False):
            if method not in TARGET_CALIBRATED_METHODS or method == CORE_MEASUREMENT_AWARE_METHOD:
                continue
            other = method_group.set_index("seed")["reconstruction_calibration_score"].sort_index()
            common = core.index.intersection(other.index)
            if len(common) < 2:
                p_two_sided = math.nan
                p_core_better = math.nan
                mean_delta = math.nan
            else:
                delta = other.loc[common].to_numpy(dtype=np.float64) - core.loc[common].to_numpy(dtype=np.float64)
                mean_delta = float(delta.mean())
                p_two_sided = float(stats.ttest_rel(other.loc[common], core.loc[common], nan_policy="omit").pvalue)
                try:
                    p_core_better = float(
                        stats.ttest_rel(other.loc[common], core.loc[common], alternative="greater", nan_policy="omit").pvalue
                    )
                except TypeError:
                    t_stat = stats.ttest_rel(other.loc[common], core.loc[common], nan_policy="omit").statistic
                    p_core_better = float(stats.t.sf(t_stat, df=len(common) - 1))
            rows.append(
                {
                    "transfer_id": transfer_id,
                    "comparison": f"{CORE_MEASUREMENT_AWARE_METHOD}_vs_{method}",
                    "comparison_scope": "same_target_calibration_label_budget",
                    "paired_seed_count": int(len(common)),
                    "metric": "reconstruction_calibration_score",
                    "mean_delta_other_minus_core": mean_delta,
                    "p_value_two_sided": p_two_sided,
                    "p_value_core_better_one_sided": p_core_better,
                    "core_better_significance": significance_label(p_core_better),
                }
            )
    columns = [
        "transfer_id",
        "comparison",
        "comparison_scope",
        "paired_seed_count",
        "metric",
        "mean_delta_other_minus_core",
        "p_value_two_sided",
        "p_value_core_better_one_sided",
        "core_better_significance",
    ]
    if not rows:
        return pd.DataFrame(columns=columns)
    return pd.DataFrame(rows, columns=columns).sort_values(["transfer_id", "comparison"]).reset_index(drop=True)


def fair_ablation_gate(significance: pd.DataFrame) -> dict[str, Any]:
    rows = []
    transfer_ids = sorted(str(value) for value in significance["transfer_id"].dropna().unique())
    expected = {(transfer_id, baseline) for transfer_id in transfer_ids for baseline in FAIR_SHARED_LAYER_CALIBRATED_BASELINES}
    observed = set()
    for _, row in significance.iterrows():
        baseline = str(row["comparison"]).replace(f"{CORE_MEASUREMENT_AWARE_METHOD}_vs_", "")
        if baseline not in FAIR_SHARED_LAYER_CALIBRATED_BASELINES:
            continue
        observed.add((str(row["transfer_id"]), baseline))
        passed = bool(
            float(row["mean_delta_other_minus_core"]) > 0.0
            and float(row["p_value_core_better_one_sided"]) < 0.05
        )
        rows.append(
            {
                "transfer_id": str(row["transfer_id"]),
                "baseline": baseline,
                "mean_delta_other_minus_core": float(row["mean_delta_other_minus_core"]),
                "p_value_core_better_one_sided": float(row["p_value_core_better_one_sided"]),
                "core_better_significance": str(row["core_better_significance"]),
                "passed": passed,
            }
        )
    missing = [
        {"transfer_id": transfer_id, "baseline": baseline}
        for transfer_id, baseline in sorted(expected - observed)
    ]
    passed_all = bool(expected) and not missing and all(row["passed"] for row in rows)
    return {
        "gate": "fair_shared_layer_calibrated_ablation",
        "status": (
            "passed_uniform_measurement_pathway_superiority"
            if passed_all
            else "not_passed_uniform_measurement_pathway_superiority"
        ),
        "criterion": (
            "core measurement-aware must beat every calibrated shared-layer baseline "
            "in both transfer directions on paired reconstruction_calibration_score at one-sided p<0.05"
        ),
        "comparisons": rows,
        "missing_comparisons": missing,
        "interpretation": (
            "target-side measurement modeling has empirical value beyond target-supervised representation adaptation"
            if passed_all
            else "Large gains over the frozen corpus-specific-head baseline cannot be attributed uniquely to the measurement-aware target pathway"
        ),
    }


def significance_label(p_value: float) -> str:
    if pd.isna(p_value):
        return "NA"
    if p_value < 0.001:
        return "***"
    if p_value < 0.01:
        return "**"
    if p_value < 0.05:
        return "*"
    if p_value < 0.10:
        return "trend"
    return "ns"


def format_mean_ci(row: pd.Series, metric: str) -> str:
    mean = row[f"{metric}_mean"]
    low = row[f"{metric}_ci95_low"]
    high = row[f"{metric}_ci95_high"]
    if pd.isna(mean):
        return ""
    if metric in BOUNDED_0_1_METRICS:
        mean = min(1.0, max(0.0, float(mean)))
        low = min(1.0, max(0.0, float(low)))
        high = min(1.0, max(0.0, float(high)))
    elif metric in BOUNDED_MINUS1_1_METRICS:
        mean = min(1.0, max(-1.0, float(mean)))
        low = min(1.0, max(-1.0, float(low)))
        high = min(1.0, max(-1.0, float(high)))
    return f"{mean:.3f} [{low:.3f}, {high:.3f}]"


def build_main_result_table(summary: pd.DataFrame, significance: pd.DataFrame) -> pd.DataFrame:
    sig_lookup = {}
    for _, row in significance.iterrows():
        method = str(row["comparison"]).replace(f"{CORE_MEASUREMENT_AWARE_METHOD}_vs_", "")
        sig_lookup[(row["transfer_id"], method)] = row["core_better_significance"]
    rows: list[dict[str, Any]] = []
    for _, row in summary.iterrows():
        method = row["method"]
        rows.append(
            {
                "transfer_id": row["transfer_id"],
                "supervision_regime": supervision_regime(bool(row["target_calibration_labels_used"])),
                "method": method,
                "seeds": int(row["seed_count"]),
                "target_calibration_labels": "yes" if bool(row["target_calibration_labels_used"]) else "no",
                "labeled_target_calib_n": labeled_target_calibration_count(row),
                "target_eval_n": int(row["target_evaluation_count"]),
                "macro_item_mae_ci95": format_mean_ci(row, "target_macro_item_mae"),
                "calibration_mae_ci95": format_mean_ci(row, "target_calibration_mae"),
                "reconstruction_calibration_score_ci95": format_mean_ci(row, "reconstruction_calibration_score"),
                "total_mae_ci95": format_mean_ci(row, "target_total_mae"),
                "post_head_domain_ba_ci95": format_mean_ci(row, "post_head_domain_identity_ba"),
                "same_budget_measurement_aware_vs_method": (
                    "ref"
                    if method == CORE_MEASUREMENT_AWARE_METHOD
                    else sig_lookup.get((row["transfer_id"], method), "")
                    if method in TARGET_CALIBRATED_METHODS
                    else ""
                ),
                "method_rank": int(row["method_rank"]),
            }
        )
    return pd.DataFrame(rows).sort_values(["transfer_id", "method_rank"]).drop(columns=["method_rank"]).reset_index(drop=True)


def build_regime_table(main_table: pd.DataFrame, regime: str) -> pd.DataFrame:
    table = main_table[main_table["supervision_regime"] == regime].copy()
    order = {method: idx for idx, method in enumerate(METHOD_ORDER)}
    table["_method_rank"] = table["method"].map(order)
    return table.sort_values(["transfer_id", "_method_rank"]).drop(columns=["_method_rank"]).reset_index(drop=True)


def build_label_budget_contract(summary: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for (transfer_id, used), group in summary.groupby(["transfer_id", "target_calibration_labels_used"], dropna=False):
        methods = [str(value) for value in group.sort_values("method_rank")["method"].tolist()]
        rows.append(
            {
                "transfer_id": transfer_id,
                "supervision_regime": supervision_regime(bool(used)),
                "methods": ";".join(methods),
                "target_calibration_labels_used": bool(used),
                "labeled_target_calib_n": int(round(group["target_calibration_count"].mean())) if bool(used) else 0,
                "target_eval_n": int(round(group["target_evaluation_count"].mean())),
                "direct_claim_scope": (
                    "methods in this row share the same target-label budget"
                    if bool(used)
                    else "zero target clinical labels; compare only with other zero-label rows"
                ),
            }
        )
    return pd.DataFrame(rows).sort_values(["transfer_id", "supervision_regime"]).reset_index(drop=True)


def build_secondary_clinical_table(summary: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for _, row in summary.iterrows():
        rows.append(
            {
                "transfer_id": row["transfer_id"],
                "supervision_regime": supervision_regime(bool(row["target_calibration_labels_used"])),
                "method": row["method"],
                "seeds": int(row["seed_count"]),
                "target_calibration_labels": "yes" if bool(row["target_calibration_labels_used"]) else "no",
                "labeled_target_calib_n": labeled_target_calibration_count(row),
                "total_mae_ci95": format_mean_ci(row, "target_total_mae"),
                "total_ccc_ci95": format_mean_ci(row, "target_total_ccc"),
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


def write_secondary_clinical_markdown(table: pd.DataFrame, path: Path) -> None:
    lines = [
        "| transfer | regime | method | target labels | labeled target calib n | total MAE | total CCC | macro-F1 | BA | AUROC | AUPRC | sensitivity | specificity |",
        "| --- | --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for _, row in table.iterrows():
        lines.append(
            "| "
            + " | ".join(
                [
                    str(row["transfer_id"]),
                    str(row["supervision_regime"]),
                    str(row["method"]),
                    str(row["target_calibration_labels"]),
                    str(row["labeled_target_calib_n"]),
                    str(row["total_mae_ci95"]),
                    str(row["total_ccc_ci95"]),
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
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def summarize_numeric_values(values: np.ndarray) -> dict[str, float]:
    values = np.asarray(values, dtype=np.float64)
    values = values[~np.isnan(values)]
    if len(values) == 0:
        return {"mean": math.nan, "std": math.nan, "ci95_low": math.nan, "ci95_high": math.nan}
    mean = float(values.mean())
    std = float(values.std(ddof=1)) if len(values) > 1 else 0.0
    half_width = float(stats.t.ppf(0.975, len(values) - 1) * std / math.sqrt(len(values))) if len(values) > 1 else 0.0
    return {"mean": mean, "std": std, "ci95_low": mean - half_width, "ci95_high": mean + half_width}


def format_ci_values(stats_row: dict[str, float]) -> str:
    mean = stats_row["mean"]
    if pd.isna(mean):
        return ""
    return f"{mean:.3f} [{stats_row['ci95_low']:.3f}, {stats_row['ci95_high']:.3f}]"


def build_targeted_item_analysis_by_seed(metrics: pd.DataFrame) -> pd.DataFrame:
    columns = [
        "transfer_id",
        "method",
        "method_rank",
        "seed",
        "target_calibration_labels_used",
        "target_calibration_count",
        "target_evaluation_count",
        "analysis_level",
        "item_set_id",
        "item_display",
        "item_ids",
        "item_count",
        "audit_role",
        "item_order",
        "item_mae",
    ]
    rows: list[dict[str, Any]] = []
    for _, row in metrics.iterrows():
        base = {
            "transfer_id": row["transfer_id"],
            "method": row["method"],
            "method_rank": int(row["method_rank"]),
            "seed": int(row["seed"]),
            "target_calibration_labels_used": bool(row["target_calibration_labels_used"]),
            "target_calibration_count": int(row["target_calibration_count"]),
            "target_evaluation_count": int(row["target_evaluation_count"]),
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
                    "audit_role": TARGETED_ITEM_ROLES[item_id],
                    "item_order": item_order,
                    "item_mae": float(row[f"target_item_mae_{item_id}"]),
                }
            )
        for set_order, (set_id, item_display, item_ids, audit_role) in enumerate(TARGETED_ITEM_SETS, start=1):
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
                    "item_mae": float(row[f"target_item_set_mae_{set_id}"]),
                }
            )
    if not rows:
        return pd.DataFrame(columns=columns)
    return pd.DataFrame(rows, columns=columns).sort_values(
        ["transfer_id", "method_rank", "seed", "analysis_level", "item_order"]
    ).reset_index(drop=True)


def summarize_targeted_item_analysis(by_seed: pd.DataFrame) -> pd.DataFrame:
    columns = [
        "transfer_id",
        "method",
        "method_rank",
        "target_calibration_labels_used",
        "target_calibration_count",
        "target_evaluation_count",
        "analysis_level",
        "item_set_id",
        "item_display",
        "item_ids",
        "item_count",
        "audit_role",
        "item_order",
        "seed_count",
        "item_mae_mean",
        "item_mae_std",
        "item_mae_ci95_low",
        "item_mae_ci95_high",
    ]
    rows: list[dict[str, Any]] = []
    group_cols = [
        "transfer_id",
        "method",
        "method_rank",
        "target_calibration_labels_used",
        "target_calibration_count",
        "target_evaluation_count",
        "analysis_level",
        "item_set_id",
        "item_display",
        "item_ids",
        "item_count",
        "audit_role",
        "item_order",
    ]
    for key, group in by_seed.groupby(group_cols, dropna=False):
        stats_row = summarize_numeric_values(pd.to_numeric(group["item_mae"], errors="coerce").to_numpy(dtype=np.float64))
        row = dict(zip(group_cols, key))
        row.update(
            {
                "seed_count": int(group["seed"].nunique()),
                "item_mae_mean": stats_row["mean"],
                "item_mae_std": stats_row["std"],
                "item_mae_ci95_low": stats_row["ci95_low"],
                "item_mae_ci95_high": stats_row["ci95_high"],
            }
        )
        rows.append(row)
    if not rows:
        return pd.DataFrame(columns=columns)
    return pd.DataFrame(rows, columns=columns).sort_values(
        ["transfer_id", "method_rank", "analysis_level", "item_order"]
    ).reset_index(drop=True)


def targeted_item_directional_reading(delta_mean: float) -> str:
    if pd.isna(delta_mean) or abs(float(delta_mean)) <= TARGETED_ITEM_TIE_TOLERANCE:
        return "near tie"
    if delta_mean > 0.0:
        return "measurement-aware lower error"
    return "shared ordinal lower error"


def build_targeted_item_analysis_table(by_seed: pd.DataFrame) -> pd.DataFrame:
    columns = [
        "transfer_id",
        "analysis_level",
        "item_set_id",
        "item_display",
        "item_ids",
        "item_count",
        "audit_role",
        "shared_ordinal_head_mae_mean",
        "shared_ordinal_head_mae_ci95",
        "measurement_aware_mae_mean",
        "measurement_aware_mae_ci95",
        "delta_shared_minus_measurement_aware_mean",
        "delta_shared_minus_measurement_aware_ci95",
        "measurement_aware_lower_error_seed_count",
        "shared_ordinal_lower_error_seed_count",
        "paired_seed_count",
        "directional_reading",
    ]
    comparison = by_seed[by_seed["method"].isin(TARGETED_ITEM_COMPARISON_METHODS)].copy()
    rows: list[dict[str, Any]] = []
    for transfer_id in sorted(str(value) for value in comparison["transfer_id"].dropna().unique()):
        transfer_group = comparison[comparison["transfer_id"].eq(transfer_id)].copy()
        for analysis_level, item_set_id in TARGETED_ITEM_TABLE_ROWS:
            item_group = transfer_group[
                transfer_group["analysis_level"].eq(analysis_level) & transfer_group["item_set_id"].eq(item_set_id)
            ].copy()
            shared = item_group[item_group["method"].eq("shared_head_joint_adaptation")].set_index("seed")["item_mae"]
            measurement_aware = item_group[item_group["method"].eq(CORE_MEASUREMENT_AWARE_METHOD)].set_index("seed")[
                "item_mae"
            ]
            common_seeds = shared.index.intersection(measurement_aware.index)
            if len(common_seeds) == 0:
                continue
            shared_values = shared.loc[common_seeds].to_numpy(dtype=np.float64)
            measurement_aware_values = measurement_aware.loc[common_seeds].to_numpy(dtype=np.float64)
            delta_values = shared_values - measurement_aware_values
            shared_stats = summarize_numeric_values(shared_values)
            measurement_aware_stats = summarize_numeric_values(measurement_aware_values)
            delta_stats = summarize_numeric_values(delta_values)
            descriptor = item_group.iloc[0]
            rows.append(
                {
                    "transfer_id": transfer_id,
                    "analysis_level": analysis_level,
                    "item_set_id": item_set_id,
                    "item_display": descriptor["item_display"],
                    "item_ids": descriptor["item_ids"],
                    "item_count": int(descriptor["item_count"]),
                    "audit_role": descriptor["audit_role"],
                    "shared_ordinal_head_mae_mean": shared_stats["mean"],
                    "shared_ordinal_head_mae_ci95": format_ci_values(shared_stats),
                    "measurement_aware_mae_mean": measurement_aware_stats["mean"],
                    "measurement_aware_mae_ci95": format_ci_values(measurement_aware_stats),
                    "delta_shared_minus_measurement_aware_mean": delta_stats["mean"],
                    "delta_shared_minus_measurement_aware_ci95": format_ci_values(delta_stats),
                    "measurement_aware_lower_error_seed_count": int((delta_values > 0.0).sum()),
                    "shared_ordinal_lower_error_seed_count": int((delta_values < 0.0).sum()),
                    "paired_seed_count": int(len(common_seeds)),
                    "directional_reading": targeted_item_directional_reading(delta_stats["mean"]),
                }
            )
    if not rows:
        return pd.DataFrame(columns=columns)
    return pd.DataFrame(rows, columns=columns).sort_values(
        ["transfer_id", "analysis_level", "item_count", "item_set_id"]
    ).reset_index(drop=True)


def write_targeted_item_analysis_markdown(table: pd.DataFrame, path: Path) -> None:
    if table.empty:
        path.write_text("No targeted item comparison rows were generated.\n", encoding="utf-8")
        return
    lines = [
        "Positive delta means Measurement-aware has lower item MAE than the Shared ordinal head. This is a descriptive targeted analysis, not a five-seed superiority test.",
        "",
    ]
    transfer_order = ["cmdc_to_edaic_phq_shared", "edaic_to_cmdc_phq_shared"]
    row_order = {spec: idx for idx, spec in enumerate(TARGETED_ITEM_TABLE_ROWS)}
    table = table.copy()
    table["_row_order"] = table.apply(lambda row: row_order.get((row["analysis_level"], row["item_set_id"]), 999), axis=1)
    for transfer_id in transfer_order:
        sub = table[table["transfer_id"].eq(transfer_id)].sort_values("_row_order")
        if sub.empty:
            continue
        lines.extend(
            [
                f"**{display_transfer_id(transfer_id)}.**",
                "",
                "| item set | audit role | shared ordinal MAE | measurement-aware MAE | delta shared - measurement-aware | MA lower-error seeds | reading |",
                "| --- | --- | ---: | ---: | ---: | ---: | --- |",
            ]
        )
        for _, row in sub.iterrows():
            lines.append(
                "| "
                + " | ".join(
                    [
                        str(row["item_display"]),
                        str(row["audit_role"]),
                        str(row["shared_ordinal_head_mae_ci95"]),
                        str(row["measurement_aware_mae_ci95"]),
                        str(row["delta_shared_minus_measurement_aware_ci95"]),
                        f"{int(row['measurement_aware_lower_error_seed_count'])}/{int(row['paired_seed_count'])}",
                        str(row["directional_reading"]),
                    ]
                )
                + " |"
            )
        lines.append("")
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def summarize_mmd_sensitivity(metrics: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    grouped = metrics.groupby(["transfer_id", "lambda_mmd"], dropna=False)
    for (transfer_id, lambda_mmd), group in grouped:
        row: dict[str, Any] = {
            "transfer_id": transfer_id,
            "lambda_mmd": float(lambda_mmd),
            "seed_count": int(group["seed"].nunique()),
            "target_calibration_count": int(round(group["target_calibration_count"].mean())),
            "target_evaluation_count": int(round(group["target_evaluation_count"].mean())),
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
    return pd.DataFrame(rows).sort_values(["transfer_id", "lambda_mmd"]).reset_index(drop=True)


def build_mmd_sensitivity_table(summary: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for _, row in summary.iterrows():
        rows.append(
            {
                "transfer_id": row["transfer_id"],
                "lambda_mmd": f"{float(row['lambda_mmd']):.4g}",
                "seeds": int(row["seed_count"]),
                "reconstruction_calibration_score_ci95": format_mean_ci(row, "reconstruction_calibration_score"),
                "macro_item_mae_ci95": format_mean_ci(row, "target_macro_item_mae"),
                "calibration_mae_ci95": format_mean_ci(row, "target_calibration_mae"),
                "total_mae_ci95": format_mean_ci(row, "target_total_mae"),
                "binary_macro_f1_ci95": format_mean_ci(row, "target_binary_macro_f1"),
                "binary_ba_ci95": format_mean_ci(row, "target_binary_balanced_accuracy"),
            }
        )
    return pd.DataFrame(rows).reset_index(drop=True)


def write_mmd_sensitivity_markdown(table: pd.DataFrame, path: Path) -> None:
    lines = [
        "| transfer | lambda_mmd | seeds | recon+calib score | macro item MAE | calibration MAE | total MAE | binary macro-F1 | binary BA |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for _, row in table.iterrows():
        lines.append(
            "| "
            + " | ".join(
                [
                    str(row["transfer_id"]),
                    str(row["lambda_mmd"]),
                    str(row["seeds"]),
                    str(row["reconstruction_calibration_score_ci95"]),
                    str(row["macro_item_mae_ci95"]),
                    str(row["calibration_mae_ci95"]),
                    str(row["total_mae_ci95"]),
                    str(row["binary_macro_f1_ci95"]),
                    str(row["binary_ba_ci95"]),
                ]
            )
            + " |"
        )
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def plot_mmd_sensitivity(summary: pd.DataFrame, out_path: Path) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    ordered_lambdas = sorted(summary["lambda_mmd"].dropna().unique())
    x_positions = np.arange(len(ordered_lambdas))
    labels = [f"{value:.4g}" for value in ordered_lambdas]
    fig, ax = plt.subplots(figsize=(7.2, 4.2), dpi=180)
    colors = {
        "cmdc_to_edaic_phq_shared": "#2563eb",
        "edaic_to_cmdc_phq_shared": "#dc2626",
    }
    for transfer_id, group in summary.groupby("transfer_id", dropna=False):
        group = group.set_index("lambda_mmd").loc[ordered_lambdas].reset_index()
        y = group["reconstruction_calibration_score_mean"].to_numpy(dtype=np.float64)
        low = group["reconstruction_calibration_score_ci95_low"].to_numpy(dtype=np.float64)
        high = group["reconstruction_calibration_score_ci95_high"].to_numpy(dtype=np.float64)
        ax.errorbar(
            x_positions,
            y,
            yerr=np.vstack([y - low, high - y]),
            marker="o",
            linewidth=2.0,
            capsize=3.0,
            label=transfer_id.replace("_phq_shared", "").replace("_to_", " -> "),
            color=colors.get(str(transfer_id)),
        )
    ax.set_xticks(x_positions)
    ax.set_xticklabels(labels)
    ax.set_xlabel("lambda_mmd")
    ax.set_ylabel("Reconstruction + calibration score")
    ax.set_title("MMD Weight Sensitivity")
    ax.grid(axis="y", alpha=0.25)
    ax.legend(frameon=False)
    fig.tight_layout()
    fig.savefig(out_path)
    plt.close(fig)


def run_extra_mmd_sensitivity(
    tables: dict[str, pd.DataFrame],
    feature_cols: list[str],
    args: argparse.Namespace,
    existing_metrics: pd.DataFrame,
) -> pd.DataFrame:
    requested = sorted({float(value) for value in args.mmd_sensitivity_weights})
    existing = existing_metrics[
        existing_metrics["method"].isin(["full_without_mmd", "full_measurement_aware"])
    ].copy()
    existing = existing[pd.to_numeric(existing["lambda_mmd"], errors="coerce").notna()].copy()
    existing["sensitivity_source"] = "main_table"
    rows = existing.to_dict(orient="records")
    existing_keys = {
        (str(row["transfer_id"]), int(row["seed"]), round(float(row["lambda_mmd"]), 12))
        for row in rows
    }
    view = official_view()
    for source_dataset, target_dataset in TRANSFER_DIRECTIONS:
        raw_source = tables[source_dataset].copy()
        raw_target = tables[target_dataset].copy()
        raw_source, raw_target = sanitize_pair(raw_source, raw_target, feature_cols)
        source_y = label_arrays(raw_source)
        target_y_all = label_arrays(raw_target)
        transfer_id = f"{source_dataset}_to_{target_dataset}_phq_shared"
        for seed in [int(seed) for seed in args.seeds]:
            target_calib_idx, target_eval_idx = calibration_split_indices(
                target_y_all,
                seed,
                fraction=args.target_calibration_fraction,
                minimum=args.target_calibration_min,
            )
            source_x, target_x_all, actual_components = prepare_pair_features(
                raw_source,
                raw_target,
                feature_cols,
                n_components=args.pca_components,
                seed=seed,
            )
            target_x_eval = target_x_all[target_eval_idx]
            target_y_eval = target_y_all[target_eval_idx]
            for lambda_mmd in requested:
                key = (transfer_id, seed, round(float(lambda_mmd), 12))
                if key in existing_keys:
                    continue
                model = train_measurement_model(
                    "full_measurement_aware",
                    source_dataset,
                    target_dataset,
                    source_x,
                    source_y,
                    target_x_all,
                    target_y_all,
                    target_calib_idx,
                    seed=seed,
                    args=args,
                    latent_mmd_weight=float(lambda_mmd),
                )
                pred, source_pred, probs, source_sym, target_sym, _ = predict_measurement_model(
                    model,
                    source_dataset,
                    target_dataset,
                    source_x,
                    target_x_eval,
                    args=args,
                )
                row = add_common_row_fields(
                    view=view,
                    source_dataset=source_dataset,
                    target_dataset=target_dataset,
                    method="full_measurement_aware",
                    seed=seed,
                    source_n=len(raw_source),
                    target_calib_n=len(target_calib_idx),
                    target_eval_n=len(target_eval_idx),
                    input_columns=len(feature_cols),
                    pca_components=actual_components,
                    pred=pred,
                    truth=target_y_eval,
                    source_pred=source_pred,
                    probs=probs,
                    feature_source_repr=source_x,
                    feature_target_repr=target_x_eval,
                    latent_source_repr=source_sym,
                    latent_target_repr=target_sym,
                    target_calibration_labels_used=True,
                    training_contract=f"measurement-aware + MMD auxiliary ordinal model with lambda_mmd={float(lambda_mmd):.4g}",
                    lambda_mmd=float(lambda_mmd),
                )
                row["sensitivity_source"] = "lambda_sweep"
                rows.append(row)
    return pd.DataFrame(rows).sort_values(["transfer_id", "lambda_mmd", "seed"]).reset_index(drop=True)


def display_transfer_id(transfer_id: str) -> str:
    mapping = {
        "cmdc_to_edaic_phq_shared": "CMDC -> E-DAIC",
        "edaic_to_cmdc_phq_shared": "E-DAIC -> CMDC",
    }
    return mapping.get(transfer_id, transfer_id.replace("_phq_shared", "").replace("_to_", " -> "))


def display_method_id(method: str) -> str:
    mapping = {
        "erm": "ERM",
        "coral": "CORAL",
        "mmd": "MMD",
        "dann": "DANN",
        "strongest_foundation_baseline": "Strongest foundation",
        "latent_only": "Latent-only",
        "corpus_specific_head": "Corpus-specific head",
        "direct_target_finetune": "Direct target fine-tune",
        "direct_multitask_shared_head": "Direct source+target multitask",
        "shared_head_joint_adaptation": "Shared ordinal head",
        "generic_target_mlp_head": "Generic target MLP head",
        "full_without_mmd": "Measurement-aware",
        "full_measurement_aware": "Measurement-aware + MMD",
    }
    return mapping.get(method, method)


def write_markdown_table(table: pd.DataFrame, path: Path) -> None:
    transfer_order = ["cmdc_to_edaic_phq_shared", "edaic_to_cmdc_phq_shared"]
    header = "| method | regime | n_cal | macro item MAE | calibration MAE | total MAE |"
    separator = "| --- | --- | ---: | ---: | ---: | ---: |"
    lines: list[str] = []
    for idx, transfer_id in enumerate(transfer_order):
        sub = table.loc[table["transfer_id"].eq(transfer_id)].copy()
        if sub.empty:
            continue
        panel = "Panel A" if idx == 0 else "Panel B"
        lines.extend([f"**{panel}. {display_transfer_id(transfer_id)}.**", "", header, separator])
        for regime_label, regime_value in [
            ("Zero-target-label context", "zero_target_label"),
            ("Target-calibrated comparison", "target_calibrated"),
        ]:
            block = sub.loc[sub["supervision_regime"].eq(regime_value)].copy()
            if block.empty:
                continue
            lines.append(f"| **{regime_label}** |  |  |  |  |  |")
            for _, row in block.iterrows():
                lines.append(
                    "| "
                    + " | ".join(
                        [
                            display_method_id(str(row["method"])),
                            "zero-label" if regime_value == "zero_target_label" else "calibrated",
                            str(row["labeled_target_calib_n"]),
                            str(row["macro_item_mae_ci95"]),
                            str(row["calibration_mae_ci95"]),
                            str(row["total_mae_ci95"]),
                        ]
                    )
                    + " |"
                )
        lines.append("")
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def architecture_contract(args: argparse.Namespace, coverage: pd.DataFrame) -> dict[str, Any]:
    return {
        "artifact_id": "P5_MV24_measurement_aware_ordinal_architecture",
        "generated_at": utc_now(),
        "git_commit": git_commit(),
        "architecture": {
            "input": "frozen subject-level foundation representation from Qwen3 text, WavLM speech, and OpenFace video statistics",
            "projector": f"Linear-PCA({args.pca_components}) -> Linear({args.hidden_dim}) -> GELU -> Dropout({args.dropout}) -> LayerNorm -> Linear({args.hidden_dim}) -> GELU",
            "shared_symptom_layer": "Linear(hidden_dim, 8) mapped to the eight PHQ shared symptom items",
            "measurement_heads": "one corpus-specific cumulative-logit ordinal head per corpus; each item has a positive discrimination slope and three ordered thresholds",
            "core_losses": [
                "source ordinal reconstruction negative log likelihood",
                "target calibration ordinal reconstruction negative log likelihood",
                "small latent L2 regularizer",
            ],
            "auxiliary_losses": [
                "optional RBF-MMD alignment on the shared symptom layer for the measurement-aware + MMD variant",
            ],
            "formal_loss": "L_MA = NLL_src + lambda_cal*NLL_tgt_cal + lambda_l2*(||S_src||^2+||S_tgt||^2); L_MA+MMD = L_MA + lambda_mmd*MMD(S_src,S_tgt)",
            "training_protocol": "source warm-start of projector, shared symptom layer, and source ordinal head; source head initialization of the target ordinal head; core measurement-aware adaptation with source and target-calibration ordinal reconstruction; optional MMD evaluated as an auxiliary variant",
            "fixed_lambdas": {
                "lambda_cal": float(args.target_calibration_weight),
                "lambda_mmd_auxiliary": float(args.latent_mmd_weight),
                "lambda_l2": float(args.latent_l2_weight),
            },
            "secondary_endpoint": {
                "definition": "shared-PHQ screening endpoint derived from the eight predicted/observed shared item scores",
                "threshold": PHQ_SHARED_BINARY_THRESHOLD,
                "metrics": [
                    "macro-F1",
                    "balanced accuracy",
                    "AUROC",
                    "AUPRC",
                    "sensitivity",
                    "specificity",
                ],
            },
            "ablation_contracts": {
                "latent_only": "same shared symptom layer and source ordinal head, no target measurement head",
                "corpus_specific_head": "source-trained shared symptom layer plus target ordinal head fit on calibration labels; retained as a weak legacy calibrated baseline",
                "direct_target_finetune": "source-warm-started direct item regressor; target calibration labels update the same shared layers without ordinal measurement heads",
                "direct_multitask_shared_head": "direct shared item regressor jointly optimized on source reconstruction and target calibration labels",
                "shared_head_joint_adaptation": "measurement-aware training schedule with source and target forced to share one ordinal head",
                "generic_target_mlp_head": "shared symptom/projector layers with corpus-specific generic MLP item heads instead of ordinal measurement parameterization",
                "full_without_mmd": "core measurement-aware pathway with joint source and target-calibration ordinal reconstruction",
                "full_measurement_aware": "measurement-aware + MMD auxiliary variant with the same ordinal reconstruction losses plus latent symptom MMD",
            },
        },
        "evaluation": {
            "directions": [f"{src}_to_{tgt}_phq_shared" for src, tgt in TRANSFER_DIRECTIONS],
            "methods": METHOD_ORDER,
            "seeds": [int(seed) for seed in args.seeds],
            "target_calibration_fraction": float(args.target_calibration_fraction),
            "target_calibration_min": int(args.target_calibration_min),
            "co_primary_metrics": ["target_macro_item_mae", "target_calibration_mae"],
            "compact_summary_metric": "reconstruction_calibration_score = target_macro_item_mae + target_calibration_mae",
            "secondary_severity_metrics": ["target_total_mae", "target_total_ccc"],
            "secondary_clinical_classification_metrics": [
                "target_binary_macro_f1",
                "target_binary_balanced_accuracy",
                "target_binary_auroc",
                "target_binary_auprc",
                "target_binary_sensitivity",
                "target_binary_specificity",
            ],
            "supervision_regimes": {
                "zero_target_label": ZERO_TARGET_LABEL_METHODS,
                "target_calibrated": TARGET_CALIBRATED_METHODS,
            },
            "statistical_test": (
                "paired t-test over seed-level reconstruction_calibration_score, "
                "core measurement-aware model versus target-calibrated variants with matched labeled target exposure"
            ),
            "cross_regime_policy": (
                "zero-target-label baselines and target-calibrated measurement-aware methods are reported together for context, "
                "but direct superiority claims are made only within a matched target-label budget"
            ),
            "fair_ablation_policy": (
                "measurement-aware target-pathway claims require comparison against calibrated baselines that also allow target labels "
                "to update shared layers; corpus_specific_head alone is not used to identify the source of the gain"
            ),
            "fair_ablation_gate_source": "run_summary.json:fair_ablation_gate",
            "targeted_item_analysis": {
                "comparison": "shared_head_joint_adaptation versus full_without_mmd",
                "focus_item_sets": {
                    "anchors": "C01/C04/C05/C07",
                    "threshold_shift": "C02/C06",
                },
                "claim_policy": (
                    "descriptive item-level and item-set analysis for linking the measurement audit to model behavior; "
                    "not a primary superiority test"
                ),
            },
        },
        "feature_coverage": coverage.to_dict(orient="records"),
    }


def write_architecture_markdown(path: Path, contract: dict[str, Any]) -> None:
    arch = contract["architecture"]
    lines = [
        "# MV24 Measurement-Aware Ordinal Architecture",
        "",
        "MV24 fixes the measurement-aware framework to one official design: frozen foundation representations feed a shared eight-dimensional symptom layer, and observed PHQ shared-item responses are reconstructed by corpus-specific cumulative-logit ordinal heads.",
        "",
        "## Architecture",
        "",
        f"- Input: {arch['input']}.",
        f"- Projector: {arch['projector']}.",
        f"- Shared symptom layer: {arch['shared_symptom_layer']}.",
        f"- Measurement heads: {arch['measurement_heads']}.",
        f"- Training protocol: {arch['training_protocol']}.",
        "",
        "## Loss",
        "",
        f"`{arch['formal_loss']}`",
        "",
        "| weight | value |",
        "| --- | ---: |",
    ]
    for name, value in arch["fixed_lambdas"].items():
        lines.append(f"| {name} | {float(value):.4f} |")
    lines.extend(
        [
            "",
            "## Main Metric",
            "",
            "The co-primary metrics are `target_macro_item_mae` and `target_calibration_mae`. The reconstruction-plus-calibration score remains a supplementary compact summary rather than a new clinical scale.",
            "",
            "## Supervision Regimes",
            "",
        "- `zero_target_label`: ERM, CORAL, MMD, DANN, strongest foundation baseline, and latent-only use no target clinical labels.",
        "- `target_calibrated`: corpus-specific-head, direct target fine-tuning, direct source+target multitask, shared ordinal head, generic target MLP head, measurement-aware core (`full_without_mmd`), and measurement-aware + MMD (`full_measurement_aware`) use the same target calibration split and the same labeled target budget.",
        "- Measurement-aware target-pathway claims must be judged against calibrated baselines that also allow target labels to update shared layers; corpus-specific-head alone is retained only as a weak legacy comparator.",
        "- The current fair-ablation gate is recorded in `run_summary.json`; if it is not passed, report target calibration/shared-layer adaptation as the robust finding and keep measurement-parameterization claims bounded.",
        "- Direct significance claims are restricted to methods within the same target-label budget and matched target-label exposure.",
        "",
        "## Secondary Clinical Endpoint",
        "",
        f"The secondary classification endpoint thresholds the observed and predicted shared-PHQ total at `{PHQ_SHARED_BINARY_THRESHOLD:.0f}` and reports macro-F1, balanced accuracy, AUROC, AUPRC, sensitivity, and specificity. These metrics are for clinical-reader orientation and do not replace the ordinal reconstruction/calibration primary metric.",
        "",
    ]
    )
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def write_report(
    out_dir: Path,
    run_summary: dict[str, Any],
    coverage: pd.DataFrame,
    summary: pd.DataFrame,
    main_table: pd.DataFrame,
    secondary_table: pd.DataFrame,
    mmd_sensitivity_table: pd.DataFrame,
    targeted_item_table: pd.DataFrame,
) -> None:
    summary_with_regime = summary.copy()
    summary_with_regime["supervision_regime"] = summary_with_regime["target_calibration_labels_used"].map(
        lambda value: supervision_regime(bool(value))
    )
    best = (
        summary_with_regime.sort_values(["transfer_id", "supervision_regime", "reconstruction_calibration_score_mean"])
        .groupby(["transfer_id", "supervision_regime"], as_index=False)
        .head(1)
    )
    lines = [
        "# P5 MV24 Measurement-Aware Ordinal Main Table",
        "",
        f"Generated: `{run_summary['generated_at']}`",
        "",
        "## Scope",
        "",
        "This run replaces earlier measurement-aware proxies with a single formal architecture: a shared symptom layer and corpus-specific cumulative-logit ordinal heads. The main comparison uses the same official Qwen3 + WavLM + OpenFace subject-level representation for all methods, but target-label supervision is reported in two explicit regimes. The target-calibrated regime now includes fair ablations that let target calibration labels update the same shared layers, so the corpus-specific-head baseline is no longer treated as the identifying comparator for the measurement pathway. The co-primary metrics are ordinal symptom reconstruction and calibration; secondary clinical-reader metrics convert the shared-PHQ total into a thresholded endpoint.",
        "",
        "## Feature View",
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
            "## Best Primary-Score Rows By Supervision Regime",
            "",
            "| transfer | regime | best method | score | macro item MAE | calibration MAE | seeds |",
            "| --- | --- | --- | ---: | ---: | ---: | ---: |",
        ]
    )
    for _, row in best.iterrows():
        lines.append(
            f"| {row['transfer_id']} | {row['supervision_regime']} | {row['method']} | {float(row['reconstruction_calibration_score_mean']):.4f} | {float(row['target_macro_item_mae_mean']):.4f} | {float(row['target_calibration_mae_mean']):.4f} | {int(row['seed_count'])} |"
        )
    lines.extend(["", "## Zero-Target-Label Table", ""])
    lines.append((out_dir / "zero_target_label_result_table.md").read_text(encoding="utf-8").strip())
    lines.extend(["", "## Target-Calibrated Table", ""])
    lines.append((out_dir / "target_calibrated_result_table.md").read_text(encoding="utf-8").strip())
    if not targeted_item_table.empty:
        lines.extend(["", "## Targeted Item Analysis", ""])
        lines.append((out_dir / "targeted_item_analysis_table.md").read_text(encoding="utf-8").strip())
    lines.extend(["", "## Secondary Severity And Binary Endpoint Metrics", ""])
    lines.append((out_dir / "secondary_clinical_metrics_table.md").read_text(encoding="utf-8").strip())
    if not mmd_sensitivity_table.empty:
        lines.extend(["", "## Lambda-MMD Sensitivity", ""])
        lines.append((out_dir / "mmd_sensitivity_table.md").read_text(encoding="utf-8").strip())
    lines.extend(["", "## Supervision-Aware Main Result Table", ""])
    lines.append((out_dir / "main_result_table.md").read_text(encoding="utf-8").strip())
    gate = run_summary["fair_ablation_gate"]
    lines.extend(
        [
            "",
            "## Interpretation Handle",
            "",
            f"Fair calibrated pathway gate: `{gate['status']}`.",
            "",
            f"{gate['interpretation']}. The improvement over `corpus_specific_head` remains useful, but that row freezes the source-trained shared symptom layer and therefore does not identify the measurement-aware target pathway by itself. The manuscript claim should foreground target calibration/shared-layer adaptation as the robust finding and describe the corpus-specific ordinal pathway as competitive and direction-dependent unless the fair gate passes in a future rerun. Standard binary endpoint metrics are reported as secondary clinical orientation, not as the paper's primary objective.",
            "",
        ]
    )
    (out_dir / "report.md").write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def feature_view_contract(coverage: pd.DataFrame) -> pd.DataFrame:
    view = official_view()
    return pd.DataFrame(
        [
            {
                "view_id": view.view_id,
                "modality_set": view.modality_set,
                "assets": ";".join(view.assets),
                "role": view.role,
                "input_columns_total": int(coverage.groupby("dataset")["feature_columns"].sum().max()),
                "architecture_status": "official_mv24_main_table_view",
                "large_artifact_policy": "read-only external cache; aggregate outputs only",
            }
        ]
    )


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
        if path.suffix.lower() in {".png", ".jpg", ".jpeg"}:
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        for pattern in forbidden_patterns:
            if re.search(pattern, text, flags=re.IGNORECASE):
                violations.append({"file": path.name, "pattern": pattern})
    return {
        "audit_id": "P5_MV24_measurement_aware_ordinal_hygiene",
        "generated_at": utc_now(),
        "files_checked": int(checked),
        "artifact_hygiene_passed": not violations,
        "violation_count": int(len(violations)),
        "violations": violations,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-root", type=Path, default=DEFAULT_INPUT_ROOT)
    parser.add_argument("--manifest-dir", type=Path, default=DEFAULT_MANIFEST_DIR)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--seeds", type=int, nargs="+", default=[0, 1, 2, 3, 4])
    parser.add_argument("--pca-components", type=int, default=128)
    parser.add_argument("--hidden-dim", type=int, default=256)
    parser.add_argument("--dropout", type=float, default=0.08)
    parser.add_argument("--learning-rate", type=float, default=1e-3)
    parser.add_argument("--head-learning-rate", type=float, default=2e-3)
    parser.add_argument("--weight-decay", type=float, default=1e-4)
    parser.add_argument("--target-calibration-fraction", type=float, default=0.30)
    parser.add_argument("--target-calibration-min", type=int, default=24)
    parser.add_argument("--direct-epochs", type=int, default=500)
    parser.add_argument("--dann-epochs", type=int, default=400)
    parser.add_argument("--ordinal-epochs", type=int, default=500)
    parser.add_argument("--head-epochs", type=int, default=450)
    parser.add_argument("--full-epochs", type=int, default=3000)
    parser.add_argument("--target-calibration-weight", type=float, default=16.0)
    parser.add_argument("--latent-mmd-weight", type=float, default=0.001)
    parser.add_argument("--mmd-sensitivity-weights", type=float, nargs="+", default=[0.0, 0.0001, 0.001, 0.01, 0.1])
    parser.add_argument("--skip-mmd-sensitivity", action="store_true")
    parser.add_argument("--latent-l2-weight", type=float, default=1e-4)
    parser.add_argument("--device", default="auto", help="auto, cpu, cuda, or cuda:N")
    parser.add_argument("--methods", nargs="+", choices=METHOD_ORDER, default=METHOD_ORDER)
    parser.add_argument("--clean", action="store_true", help="remove previous aggregate outputs before running")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    out_dir = args.out_dir
    if args.clean:
        clean_tracked_outputs(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    tables, feature_cols, coverage = load_official_view_tables(args)
    coverage.to_csv(out_dir / "feature_asset_coverage.csv", index=False)
    feature_view_contract(coverage).to_csv(out_dir / "feature_view_contract.csv", index=False)

    all_rows: list[dict[str, Any]] = []
    for source_dataset, target_dataset in TRANSFER_DIRECTIONS:
        all_rows.extend(run_transfer_direction(source_dataset, target_dataset, tables, feature_cols, args))

    metrics = pd.DataFrame(all_rows).sort_values(["transfer_id", "method_rank", "seed"]).reset_index(drop=True)
    metrics.to_csv(out_dir / "metrics_by_seed.csv", index=False)
    targeted_item_by_seed = build_targeted_item_analysis_by_seed(metrics)
    targeted_item_by_seed.to_csv(out_dir / "targeted_item_analysis_by_seed.csv", index=False)
    targeted_item_summary = summarize_targeted_item_analysis(targeted_item_by_seed)
    targeted_item_summary.to_csv(out_dir / "targeted_item_analysis_summary.csv", index=False)
    targeted_item_table = build_targeted_item_analysis_table(targeted_item_by_seed)
    targeted_item_table.to_csv(out_dir / "targeted_item_analysis_table.csv", index=False)
    write_targeted_item_analysis_markdown(targeted_item_table, out_dir / "targeted_item_analysis_table.md")
    summary = summarize_metrics(metrics)
    summary.to_csv(out_dir / "summary_by_method.csv", index=False)
    significance = paired_significance(metrics)
    significance.to_csv(out_dir / "paired_significance.csv", index=False)
    main_table = build_main_result_table(summary, significance)
    main_table.to_csv(out_dir / "main_result_table.csv", index=False)
    write_markdown_table(main_table, out_dir / "main_result_table.md")
    secondary_table = build_secondary_clinical_table(summary)
    secondary_table.to_csv(out_dir / "secondary_clinical_metrics_table.csv", index=False)
    write_secondary_clinical_markdown(secondary_table, out_dir / "secondary_clinical_metrics_table.md")
    zero_label_table = build_regime_table(main_table, "zero_target_label")
    zero_label_table.to_csv(out_dir / "zero_target_label_result_table.csv", index=False)
    write_markdown_table(zero_label_table, out_dir / "zero_target_label_result_table.md")
    target_calibrated_table = build_regime_table(main_table, "target_calibrated")
    target_calibrated_table.to_csv(out_dir / "target_calibrated_result_table.csv", index=False)
    write_markdown_table(target_calibrated_table, out_dir / "target_calibrated_result_table.md")
    label_budget = build_label_budget_contract(summary)
    label_budget.to_csv(out_dir / "label_budget_contract.csv", index=False)
    if args.skip_mmd_sensitivity:
        mmd_sensitivity = pd.DataFrame()
        mmd_sensitivity_summary = pd.DataFrame()
        mmd_sensitivity_table = pd.DataFrame()
    else:
        mmd_sensitivity = run_extra_mmd_sensitivity(tables, feature_cols, args, metrics)
        mmd_sensitivity.to_csv(out_dir / "mmd_sensitivity_by_seed.csv", index=False)
        mmd_sensitivity_summary = summarize_mmd_sensitivity(mmd_sensitivity)
        mmd_sensitivity_summary.to_csv(out_dir / "mmd_sensitivity_summary.csv", index=False)
        mmd_sensitivity_table = build_mmd_sensitivity_table(mmd_sensitivity_summary)
        mmd_sensitivity_table.to_csv(out_dir / "mmd_sensitivity_table.csv", index=False)
        write_mmd_sensitivity_markdown(mmd_sensitivity_table, out_dir / "mmd_sensitivity_table.md")
        plot_mmd_sensitivity(mmd_sensitivity_summary, out_dir / "mmd_sensitivity_plot.png")

    contract = architecture_contract(args, coverage)
    (out_dir / "architecture_contract.json").write_text(json.dumps(contract, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    write_architecture_markdown(out_dir / "architecture_contract.md", contract)

    summary_with_regime = summary.copy()
    summary_with_regime["supervision_regime"] = summary_with_regime["target_calibration_labels_used"].map(
        lambda value: supervision_regime(bool(value))
    )
    best_by_transfer_and_regime = (
        summary_with_regime.sort_values(["transfer_id", "supervision_regime", "reconstruction_calibration_score_mean"])
        .groupby(["transfer_id", "supervision_regime"], as_index=False)
        .head(1)[["transfer_id", "supervision_regime", "method", "reconstruction_calibration_score_mean"]]
        .to_dict(orient="records")
    )
    measurement_aware_family_best = all(
        row["method"] in {CORE_MEASUREMENT_AWARE_METHOD, AUXILIARY_MMD_METHOD}
        for row in best_by_transfer_and_regime
        if row.get("supervision_regime") == "target_calibrated"
    )
    targeted_item_focus = targeted_item_table[
        targeted_item_table["analysis_level"].eq("item_set")
        & targeted_item_table["item_set_id"].isin(["anchor_items", "threshold_shift_items"])
    ][
        [
            "transfer_id",
            "item_set_id",
            "item_ids",
            "audit_role",
            "delta_shared_minus_measurement_aware_mean",
            "measurement_aware_lower_error_seed_count",
            "paired_seed_count",
            "directional_reading",
        ]
    ]
    gate = fair_ablation_gate(significance)
    run_summary = {
        "run_id": "P5_MV24_measurement_aware_ordinal_model",
        "generated_at": utc_now(),
        "git_commit": git_commit(),
        "status": "complete",
        "official_view_id": official_view().view_id,
        "directions": [f"{src}_to_{tgt}_phq_shared" for src, tgt in TRANSFER_DIRECTIONS],
        "methods": list(args.methods),
        "seed_count": int(len(set(args.seeds))),
        "co_primary_metrics": ["target_macro_item_mae", "target_calibration_mae"],
        "compact_summary_metric": "reconstruction_calibration_score",
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
        "supervision_regimes": {
            "zero_target_label": ZERO_TARGET_LABEL_METHODS,
            "target_calibrated": TARGET_CALIBRATED_METHODS,
        },
        "mmd_sensitivity_weights": ([] if args.skip_mmd_sensitivity else [float(value) for value in args.mmd_sensitivity_weights]),
        "cross_regime_direct_superiority_claim_allowed": False,
        "target_calibrated_measurement_aware_family_best_on_compact_score": bool(measurement_aware_family_best),
        "fair_ablation_gate": gate,
        "targeted_item_analysis": {
            "comparison": "shared_head_joint_adaptation versus full_without_mmd",
            "positive_delta_definition": "shared ordinal head item MAE minus measurement-aware item MAE",
            "claim_policy": "descriptive targeted analysis, not a primary superiority gate",
            "focus_item_set_rows": json.loads(targeted_item_focus.to_json(orient="records")),
            "table": "targeted_item_analysis_table.md",
        },
        "best_by_transfer_and_regime": best_by_transfer_and_regime,
        "aggregate_outputs_only": True,
    }
    (out_dir / "run_summary.json").write_text(json.dumps(run_summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    write_report(out_dir, run_summary, coverage, summary, main_table, secondary_table, mmd_sensitivity_table, targeted_item_table)
    hygiene = artifact_hygiene(out_dir)
    (out_dir / "artifact_hygiene_audit.json").write_text(json.dumps(hygiene, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if not hygiene["artifact_hygiene_passed"]:
        raise RuntimeError(f"artifact hygiene failed: {hygiene['violations']}")


if __name__ == "__main__":
    main()
