#!/usr/bin/env python3
"""Run MV22 foundation-backbone measurement-aware validation.

MV22 keeps the Phase 5 artifact boundary: foundation feature caches stay under
ignored Phase 2 roots, downstream prediction files stay ignored, and tracked
outputs contain only aggregate contracts, metrics, status, and hygiene checks.
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
    os.environ["OMP_NUM_THREADS"] = "1"
    os.environ["OPENBLAS_NUM_THREADS"] = "1"
    os.environ["MKL_NUM_THREADS"] = "1"
    os.environ["NUMEXPR_NUM_THREADS"] = "1"


normalize_thread_env()

import numpy as np
import pandas as pd
import torch
import torch.nn as nn
import torch.nn.functional as F
from sklearn.decomposition import PCA
from sklearn.linear_model import LogisticRegression, Ridge
from sklearn.metrics import balanced_accuracy_score
from sklearn.model_selection import StratifiedKFold
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "scripts"))

import phase5_run_mv17a_multilingual_feature_contract as mv17a


MANIFEST_DIR = ROOT / "datasets" / "manifests"
DEFAULT_SPLIT_PATH = ROOT / "datasets" / "splits" / "phase2_subject_splits.csv"
DEFAULT_PREVIOUS_MV17A_OUT = (
    ROOT / "analysis" / "phase5_minimal_validation" / "p5_mv17a_multilingual_feature_contract"
)
DEFAULT_PREVIOUS_MV17_FEATURE_ROOT = ROOT / "analysis" / "phase2_baselines" / "mv17_multilingual_text_features"
DEFAULT_QWEN_FEATURE_ROOT = ROOT / "analysis" / "phase2_baselines" / "mv22_foundation_text_features"
DEFAULT_OUT_DIR = ROOT / "analysis" / "phase5_minimal_validation" / "p5_mv22_foundation_backbone_validation"
DEFAULT_EDAIC_MANIFEST = MANIFEST_DIR / "edaic_subjects.csv"

QWEN_SPEC = mv17a.EncoderSpec(
    slug="qwen3_embedding_0_6b",
    model_name="Qwen/Qwen3-Embedding-0.6B",
    pooling="last_token",
    input_prefix="",
    default_max_length=2048,
    default_chunk_batch_size=2,
    expected_dimension=1024,
    source_url="https://huggingface.co/Qwen/Qwen3-Embedding-0.6B",
    source_contract=(
        "Qwen3 text embedding foundation backbone; MV22 uses the official "
        "last-token pooling pattern, no task instruction, 2048-token chunks, "
        "and local-only subject feature caches."
    ),
)

TRACKED_FILES = {
    "adaptation_metrics_by_seed.csv",
    "adaptation_summary.csv",
    "artifact_hygiene_audit.json",
    "audio_foundation_proxy_summary.csv",
    "baseline_method_contract.csv",
    "downstream_metric_extract.csv",
    "downstream_run_summary.csv",
    "encoder_contract.csv",
    "feature_generation_summary.csv",
    "local_artifact_manifest.csv",
    "measurement_aware_reference_summary.csv",
    "model_comparison_summary.csv",
    "report.md",
    "run_summary.json",
}

PHQ_SHARED_ITEMS = [
    ("C01", "PHQ_8NoInterest", "PHQ-1"),
    ("C02", "PHQ_8Depressed", "PHQ-2"),
    ("C03", "PHQ_8Sleep", "PHQ-3"),
    ("C04", "PHQ_8Tired", "PHQ-4"),
    ("C05", "PHQ_8Appetite", "PHQ-5"),
    ("C06", "PHQ_8Failure", "PHQ-6"),
    ("C07", "PHQ_8Concentrating", "PHQ-7"),
    ("C08", "PHQ_8Moving", "PHQ-8"),
]

AUDIO_PROXY_FEATURES = [
    {
        "view_id": "wavlm_base_plus_audio_proxy",
        "dataset": "edaic",
        "model_name": "microsoft/wavlm-base-plus",
        "path": ROOT / "analysis" / "phase2_baselines" / "edaic_audio_frozen_encoders" / "wavlm_subject_features.csv",
        "feature_prefix": "wavlm_",
    },
    {
        "view_id": "wavlm_base_plus_audio_proxy",
        "dataset": "cmdc",
        "model_name": "microsoft/wavlm-base-plus",
        "path": ROOT
        / "analysis"
        / "phase2_baselines"
        / "cmdc_audio_frozen_encoders"
        / "cmdc_wavlm_subject_features.csv",
        "feature_prefix": "wavlm_",
    },
    {
        "view_id": "wavlm_base_plus_audio_proxy",
        "dataset": "pdch",
        "model_name": "microsoft/wavlm-base-plus",
        "path": ROOT / "analysis" / "phase2_baselines" / "pdch_audio_wavlm" / "pdch_wavlm_subject_features.csv",
        "feature_prefix": "wavlm_",
    },
]


@dataclass(frozen=True)
class FeatureView:
    view_id: str
    modality_set: str
    text_encoder: str
    text_feature_root: Path | None
    audio_proxy: bool


TEXT_VIEWS = [
    FeatureView("bge_m3_text", "text", "bge_m3", DEFAULT_PREVIOUS_MV17_FEATURE_ROOT, False),
    FeatureView("multilingual_e5_base_text", "text", "multilingual_e5_base", DEFAULT_PREVIOUS_MV17_FEATURE_ROOT, False),
    FeatureView("qwen3_embedding_0_6b_text", "text", "qwen3_embedding_0_6b", DEFAULT_QWEN_FEATURE_ROOT, False),
    FeatureView(
        "qwen3_embedding_0_6b_plus_wavlm_audio_proxy",
        "text_audio",
        "qwen3_embedding_0_6b",
        DEFAULT_QWEN_FEATURE_ROOT,
        True,
    ),
]


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT))
    except ValueError:
        return path.name


def natural_key(value: Any) -> list[Any]:
    return mv17a.natural_key(value)


def natural_sort_key(series: pd.Series) -> pd.Series:
    return series.map(lambda value: tuple(natural_key(value)))


def clean_tracked_outputs(out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    for name in TRACKED_FILES:
        path = out_dir / name
        if path.exists():
            path.unlink()


def encoder_spec_for_slug(slug: str) -> mv17a.EncoderSpec:
    if slug == QWEN_SPEC.slug:
        return QWEN_SPEC
    return mv17a.ENCODER_SPECS[slug]


def text_feature_paths(view: FeatureView) -> dict[str, Path]:
    if view.text_feature_root is None:
        raise ValueError(f"feature view has no text feature root: {view.view_id}")
    return mv17a.feature_paths(view.text_feature_root, encoder_spec_for_slug(view.text_encoder))


def qwen_spec_with_cli(args: argparse.Namespace) -> mv17a.EncoderSpec:
    return mv17a.EncoderSpec(
        **{
            **QWEN_SPEC.__dict__,
            "default_max_length": int(args.qwen_max_length),
            "default_chunk_batch_size": int(args.qwen_chunk_batch_size),
        }
    )


def generate_qwen_features(args: argparse.Namespace, out_dir: Path) -> pd.DataFrame:
    qwen_spec = qwen_spec_with_cli(args)
    edaic_table = mv17a.edaic_gen.build_subject_table(args.edaic_manifest)
    segment_tables = mv17a.build_cmdc_pdch_tables(args.split_path)
    summaries = mv17a.generate_encoder_features(
        qwen_spec,
        edaic_table,
        segment_tables,
        feature_root=args.qwen_feature_root,
        device_name=args.device,
        allow_download=args.allow_download,
        force=args.force_qwen_features,
    )
    feature_summary = pd.DataFrame(summaries)
    feature_summary.to_csv(out_dir / "feature_generation_summary.csv", index=False)
    mv17a.write_encoder_contract(out_dir, [qwen_spec])
    mv17a.write_local_artifact_manifest(out_dir, summaries)
    return feature_summary


def run_qwen_downstream(args: argparse.Namespace, out_dir: Path) -> pd.DataFrame:
    qwen_spec = qwen_spec_with_cli(args)
    downstream_rows = mv17a.run_downstream_chain(
        [qwen_spec],
        feature_root=args.qwen_feature_root,
        out_dir=out_dir,
        manifest_dir=args.manifest_dir,
        split_path=args.split_path,
    )
    downstream = pd.DataFrame(downstream_rows)
    downstream.to_csv(out_dir / "downstream_run_summary.csv", index=False)
    return downstream


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def downstream_dir_for(out_dir: Path, encoder: str, experiment: str) -> Path:
    dirname = {
        "mv07": "mv07_aligned_bge_shared_symptom",
        "mv12": "mv12_two_stage_latent_target",
        "mv15": "mv15_latent_conditioned_identity",
    }[experiment]
    return out_dir / "downstream" / encoder / dirname


def extract_downstream_metrics(previous_out: Path, current_out: Path) -> pd.DataFrame:
    roots = {
        "bge_m3": previous_out,
        "multilingual_e5_base": previous_out,
        QWEN_SPEC.slug: current_out,
    }
    rows: list[dict[str, Any]] = []
    for encoder, root in roots.items():
        for experiment in ["mv07", "mv12", "mv15"]:
            summary_path = downstream_dir_for(root, encoder, experiment) / "run_summary.json"
            if not summary_path.exists():
                rows.append(
                    {
                        "encoder": encoder,
                        "experiment": experiment,
                        "metric": "status",
                        "value": math.nan,
                        "status": "missing_downstream_summary",
                    }
                )
                continue
            summary = read_json(summary_path)
            verdict = summary.get("verdict", {})
            for metric, value in verdict.items():
                if isinstance(value, bool):
                    numeric = float(value)
                elif isinstance(value, (int, float)) and not isinstance(value, bool):
                    numeric = float(value)
                else:
                    continue
                rows.append(
                    {
                        "encoder": encoder,
                        "experiment": experiment,
                        "metric": metric,
                        "value": numeric,
                        "status": str(verdict.get("pass_rule_status", summary.get("status", "complete"))),
                    }
                )
    return pd.DataFrame(rows)


def summarize_audio_proxy_features() -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for spec in AUDIO_PROXY_FEATURES:
        path = spec["path"]
        if not path.exists():
            rows.append(
                {
                    "view_id": spec["view_id"],
                    "dataset": spec["dataset"],
                    "model_name": spec["model_name"],
                    "status": "missing_local_proxy_cache",
                    "rows": 0,
                    "feature_columns": 0,
                    "feature_cache_ref": rel(path),
                }
            )
            continue
        frame = pd.read_csv(path)
        feature_cols = [
            column
            for column in frame.columns
            if column.startswith(str(spec["feature_prefix"])) and pd.api.types.is_numeric_dtype(frame[column])
        ]
        rows.append(
            {
                "view_id": spec["view_id"],
                "dataset": spec["dataset"],
                "model_name": spec["model_name"],
                "status": "available_as_audio_foundation_proxy",
                "rows": int(len(frame)),
                "feature_columns": int(len(feature_cols)),
                "feature_cache_ref": rel(path),
            }
        )
    rows.append(
        {
            "view_id": "wavlm_large_audio",
            "dataset": "edaic_cmdc_pdch",
            "model_name": "microsoft/wavlm-large",
            "status": "not_executed_in_mv22_first_slice_compute_scope",
            "rows": 0,
            "feature_columns": 0,
            "feature_cache_ref": "",
        }
    )
    return pd.DataFrame(rows)


def parse_items(value: Any) -> dict[str, float]:
    if not isinstance(value, str) or not value.strip():
        return {}
    parsed = json.loads(value)
    return {str(key): float(val) for key, val in parsed.items() if pd.notna(val)}


def load_phq_shared_subject_labels(manifest_dir: Path, dataset: str) -> pd.DataFrame:
    path = manifest_dir / f"{dataset}_subjects.csv"
    frame = pd.read_csv(path)
    if "file_valid" in frame.columns:
        valid = frame["file_valid"].astype(str).str.lower().isin({"true", "1", "yes"})
        frame = frame[valid].copy()
    rows: list[dict[str, Any]] = []
    for subject, group in frame.groupby("subject_id", sort=False):
        first = group.iloc[0]
        if dataset == "edaic":
            items = parse_items(first.get("phq8_items"))
            values = [items.get(edaic_key, math.nan) for _, edaic_key, _ in PHQ_SHARED_ITEMS]
        elif dataset == "cmdc":
            items = parse_items(first.get("phq9_items"))
            values = [items.get(cmdc_key, math.nan) for _, _, cmdc_key in PHQ_SHARED_ITEMS]
        else:
            raise ValueError(f"PHQ shared labels are not available for dataset: {dataset}")
        if any(pd.isna(value) for value in values):
            continue
        row = {"participant_key": str(subject), "dataset": dataset}
        for (construct_id, _, _), value in zip(PHQ_SHARED_ITEMS, values, strict=True):
            row[construct_id] = float(value)
        row["shared_total"] = float(np.sum(values))
        rows.append(row)
    labels = pd.DataFrame(rows)
    if labels.empty:
        raise ValueError(f"no PHQ shared labels loaded for {dataset}")
    return labels.sort_values("participant_key", key=natural_sort_key).reset_index(drop=True)


def read_feature_cache(path: Path, prefix: str) -> tuple[pd.DataFrame, list[str]]:
    if not path.exists():
        raise FileNotFoundError(f"feature cache missing: {path}")
    frame = pd.read_csv(path)
    if "subject_id" not in frame.columns:
        raise ValueError(f"feature cache missing subject key: {path}")
    feature_cols = [
        column
        for column in frame.columns
        if column.startswith(prefix) and pd.api.types.is_numeric_dtype(frame[column])
    ]
    if not feature_cols:
        raise ValueError(f"no numeric feature columns with prefix {prefix}: {path}")
    selected = pd.concat(
        [frame["subject_id"].astype(str).rename("participant_key"), frame[feature_cols]],
        axis=1,
    ).copy()
    return selected, feature_cols


def load_feature_view_table(view: FeatureView, dataset: str, args: argparse.Namespace) -> tuple[pd.DataFrame, list[str]]:
    text_paths = text_feature_paths(view)
    text_frame, text_cols = read_feature_cache(text_paths[dataset], mv17a.FEATURE_PREFIX)
    text_cols_renamed = [f"text_{column}" for column in text_cols]
    text_frame = text_frame.rename(columns=dict(zip(text_cols, text_cols_renamed, strict=True)))
    feature_frames = [text_frame]
    feature_cols = text_cols_renamed
    if view.audio_proxy:
        audio_spec = next(item for item in AUDIO_PROXY_FEATURES if item["dataset"] == dataset)
        audio_frame, audio_cols = read_feature_cache(audio_spec["path"], str(audio_spec["feature_prefix"]))
        audio_cols_renamed = [f"audio_{column}" for column in audio_cols]
        audio_frame = audio_frame.rename(columns=dict(zip(audio_cols, audio_cols_renamed, strict=True)))
        feature_frames.append(audio_frame)
        feature_cols.extend(audio_cols_renamed)
    merged = feature_frames[0]
    for frame in feature_frames[1:]:
        merged = merged.merge(frame, on="participant_key", how="inner")
    return merged.sort_values("participant_key", key=natural_sort_key).reset_index(drop=True), feature_cols


def joined_feature_label_table(view: FeatureView, dataset: str, args: argparse.Namespace) -> tuple[pd.DataFrame, list[str]]:
    labels = load_phq_shared_subject_labels(args.manifest_dir, dataset)
    features, feature_cols = load_feature_view_table(view, dataset, args)
    joined = labels.merge(features, on="participant_key", how="inner")
    if joined.empty:
        raise ValueError(f"no joined feature/label rows for {view.view_id}/{dataset}")
    return joined.sort_values("participant_key", key=natural_sort_key).reset_index(drop=True), feature_cols


def prepare_pair_features(
    source: pd.DataFrame,
    target: pd.DataFrame,
    feature_cols: list[str],
    *,
    n_components: int,
    seed: int,
) -> tuple[np.ndarray, np.ndarray, PCA | None]:
    source_x = source[feature_cols].to_numpy(dtype=np.float64)
    target_x = target[feature_cols].to_numpy(dtype=np.float64)
    scaler = StandardScaler().fit(source_x)
    source_scaled = scaler.transform(source_x)
    target_scaled = scaler.transform(target_x)
    max_components = min(int(n_components), source_scaled.shape[0] + target_scaled.shape[0] - 2, source_scaled.shape[1])
    if max_components < 1:
        raise ValueError("not enough rows to build a foundation feature adapter")
    if max_components >= source_scaled.shape[1]:
        return source_scaled.astype(np.float32), target_scaled.astype(np.float32), None
    pca = PCA(n_components=max_components, random_state=seed)
    pca.fit(np.vstack([source_scaled, target_scaled]))
    return pca.transform(source_scaled).astype(np.float32), pca.transform(target_scaled).astype(np.float32), pca


def label_arrays(frame: pd.DataFrame) -> np.ndarray:
    return frame[[item[0] for item in PHQ_SHARED_ITEMS]].to_numpy(dtype=np.float32).copy()


def evaluate_item_predictions(pred: np.ndarray, truth: np.ndarray) -> dict[str, float]:
    clipped = np.clip(pred, 0.0, 3.0)
    return {
        "target_macro_item_mae": float(np.mean(np.abs(clipped - truth))),
        "target_total_mae": float(np.mean(np.abs(clipped.sum(axis=1) - truth.sum(axis=1)))),
        "target_total_rmse": float(np.sqrt(np.mean((clipped.sum(axis=1) - truth.sum(axis=1)) ** 2))),
    }


def domain_identity_ba(source_repr: np.ndarray, target_repr: np.ndarray, *, seed: int) -> float:
    labels = np.concatenate([np.zeros(len(source_repr), dtype=int), np.ones(len(target_repr), dtype=int)])
    features = np.vstack([source_repr, target_repr])
    min_count = int(np.bincount(labels).min())
    n_splits = min(5, min_count)
    if n_splits < 2:
        return math.nan
    scores: list[float] = []
    cv = StratifiedKFold(n_splits=n_splits, shuffle=True, random_state=seed)
    for train_idx, eval_idx in cv.split(features, labels):
        clf = make_pipeline(
            StandardScaler(),
            LogisticRegression(max_iter=2000, class_weight="balanced", solver="lbfgs"),
        )
        clf.fit(features[train_idx], labels[train_idx])
        pred = clf.predict(features[eval_idx])
        scores.append(float(balanced_accuracy_score(labels[eval_idx], pred)))
    return float(np.mean(scores))


def coral_source_to_target(source_x: np.ndarray, target_x: np.ndarray) -> np.ndarray:
    source_centered = source_x - source_x.mean(axis=0, keepdims=True)
    target_centered = target_x - target_x.mean(axis=0, keepdims=True)
    source_cov = np.cov(source_centered, rowvar=False) + np.eye(source_x.shape[1]) * 1e-3
    target_cov = np.cov(target_centered, rowvar=False) + np.eye(target_x.shape[1]) * 1e-3
    s_vals, s_vecs = np.linalg.eigh(source_cov)
    t_vals, t_vecs = np.linalg.eigh(target_cov)
    source_inv_sqrt = s_vecs @ np.diag(np.clip(s_vals, 1e-6, None) ** -0.5) @ s_vecs.T
    target_sqrt = t_vecs @ np.diag(np.clip(t_vals, 1e-6, None) ** 0.5) @ t_vecs.T
    return source_centered @ source_inv_sqrt @ target_sqrt + target_x.mean(axis=0, keepdims=True)


def fit_ridge_itemwise(source_x: np.ndarray, source_y: np.ndarray, eval_x: np.ndarray) -> np.ndarray:
    model = Ridge(alpha=1.0)
    model.fit(source_x, source_y)
    return model.predict(eval_x).astype(np.float32)


class GradientReverse(torch.autograd.Function):
    @staticmethod
    def forward(ctx: Any, input_tensor: torch.Tensor, weight: float) -> torch.Tensor:
        ctx.weight = float(weight)
        return input_tensor.view_as(input_tensor)

    @staticmethod
    def backward(ctx: Any, grad_output: torch.Tensor) -> tuple[torch.Tensor, None]:
        return -ctx.weight * grad_output, None


class ItemMLP(nn.Module):
    def __init__(self, input_dim: int, hidden_dim: int, output_dim: int) -> None:
        super().__init__()
        self.encoder = nn.Sequential(
            nn.Linear(input_dim, hidden_dim),
            nn.ReLU(),
            nn.Dropout(p=0.05),
        )
        self.predictor = nn.Linear(hidden_dim, output_dim)
        self.domain_head = nn.Linear(hidden_dim, 2)

    def hidden(self, inputs: torch.Tensor) -> torch.Tensor:
        return self.encoder(inputs)

    def predict(self, inputs: torch.Tensor) -> torch.Tensor:
        return self.predictor(self.hidden(inputs))


def severity_groups(labels: np.ndarray) -> np.ndarray:
    totals = labels.sum(axis=1)
    return np.digitize(totals, bins=np.asarray([5.0, 10.0, 15.0], dtype=np.float32))


def train_neural_baseline(
    method: str,
    source_x: np.ndarray,
    source_y: np.ndarray,
    target_x: np.ndarray,
    *,
    seed: int,
    epochs: int,
    hidden_dim: int,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    torch.manual_seed(seed)
    np.random.seed(seed)
    device = torch.device("cpu")
    model = ItemMLP(source_x.shape[1], hidden_dim, source_y.shape[1]).to(device)
    optimizer = torch.optim.AdamW(model.parameters(), lr=1e-3, weight_decay=1e-4)
    xs = torch.as_tensor(source_x, dtype=torch.float32, device=device)
    ys = torch.as_tensor(source_y, dtype=torch.float32, device=device)
    xt = torch.as_tensor(target_x, dtype=torch.float32, device=device)
    source_groups = torch.as_tensor(severity_groups(source_y), dtype=torch.long, device=device)
    group_values = torch.unique(source_groups)
    domain_labels = torch.cat(
        [
            torch.zeros(xs.shape[0], dtype=torch.long, device=device),
            torch.ones(xt.shape[0], dtype=torch.long, device=device),
        ]
    )
    for epoch in range(int(epochs)):
        optimizer.zero_grad(set_to_none=True)
        hidden_s = model.hidden(xs)
        pred_s = model.predictor(hidden_s)
        if method == "dann":
            hidden_t = model.hidden(xt)
            progress = float(epoch + 1) / float(max(1, epochs))
            grl_weight = 0.2 * (2.0 / (1.0 + math.exp(-10.0 * progress)) - 1.0)
            domain_hidden = GradientReverse.apply(torch.cat([hidden_s, hidden_t], dim=0), grl_weight)
            domain_logits = model.domain_head(domain_hidden)
            loss = F.mse_loss(pred_s, ys) + 0.2 * F.cross_entropy(domain_logits, domain_labels)
        elif method == "irm":
            env_losses: list[torch.Tensor] = []
            env_penalties: list[torch.Tensor] = []
            for group in group_values:
                mask = source_groups == group
                if int(mask.sum().item()) == 0:
                    continue
                scale = torch.tensor(1.0, dtype=torch.float32, device=device, requires_grad=True)
                env_loss = F.mse_loss(pred_s[mask] * scale, ys[mask])
                grad = torch.autograd.grad(env_loss, [scale], create_graph=True)[0]
                env_losses.append(env_loss)
                env_penalties.append(torch.sum(grad**2))
            loss = torch.stack(env_losses).mean() + 0.1 * torch.stack(env_penalties).mean()
        elif method == "groupdro":
            losses = [
                F.mse_loss(pred_s[source_groups == group], ys[source_groups == group])
                for group in group_values
                if int((source_groups == group).sum().item()) > 0
            ]
            loss = torch.stack(losses).max()
        else:
            raise ValueError(f"unknown neural baseline: {method}")
        loss.backward()
        optimizer.step()
    with torch.inference_mode():
        source_hidden = model.hidden(xs).detach().cpu().numpy()
        target_hidden = model.hidden(xt).detach().cpu().numpy()
        target_pred = model.predict(xt).detach().cpu().numpy()
    return target_pred.astype(np.float32), source_hidden.astype(np.float32), target_hidden.astype(np.float32)


def method_contract_rows() -> list[dict[str, str]]:
    return [
        {
            "method": "erm_itemwise_ridge",
            "status": "executed",
            "contract": "direct observed shared-item prediction on frozen foundation features",
        },
        {
            "method": "coral_itemwise_ridge",
            "status": "executed",
            "contract": "unsupervised target-feature covariance alignment followed by itemwise ridge",
        },
        {
            "method": "mmd_mean_itemwise_ridge",
            "status": "executed",
            "contract": "unsupervised target-feature mean alignment as an MMD/DAN-style lightweight proxy",
        },
        {
            "method": "dann_itemwise_mlp",
            "status": "executed",
            "contract": "domain-adversarial hidden representation with source item reconstruction",
        },
        {
            "method": "irm_severity_env_proxy",
            "status": "executed_proxy",
            "contract": "IRM penalty over source severity environments because each PHQ transfer has one source corpus",
        },
        {
            "method": "groupdro_severity_proxy",
            "status": "executed_proxy",
            "contract": "worst-source-severity-group optimization because each PHQ transfer has one source corpus",
        },
        {
            "method": "measurement_aware_mv12_reference",
            "status": "aggregate_reference",
            "contract": "existing two-stage latent target plus corpus measurement reconstruction head aggregate",
        },
    ]


def run_adaptation_baselines(args: argparse.Namespace) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    rows: list[dict[str, Any]] = []
    directions = [("edaic", "cmdc"), ("cmdc", "edaic")]
    for view in TEXT_VIEWS:
        if view.audio_proxy and not args.include_audio_proxy_baseline:
            continue
        for source_dataset, target_dataset in directions:
            source, source_cols = joined_feature_label_table(view, source_dataset, args)
            target, target_cols = joined_feature_label_table(view, target_dataset, args)
            if source_cols != target_cols:
                raise ValueError(f"feature columns differ for {view.view_id}/{source_dataset}->{target_dataset}")
            source_y = label_arrays(source)
            target_y = label_arrays(target)
            for seed in args.baseline_seeds:
                source_x, target_x, _pca = prepare_pair_features(
                    source,
                    target,
                    source_cols,
                    n_components=args.baseline_pca_components,
                    seed=int(seed),
                )
                method_inputs = [
                    ("erm_itemwise_ridge", source_x, target_x),
                    ("coral_itemwise_ridge", coral_source_to_target(source_x, target_x), target_x),
                    ("mmd_mean_itemwise_ridge", source_x - source_x.mean(axis=0, keepdims=True) + target_x.mean(axis=0, keepdims=True), target_x),
                ]
                for method, adapted_source_x, adapted_target_x in method_inputs:
                    pred = fit_ridge_itemwise(adapted_source_x, source_y, adapted_target_x)
                    metrics = evaluate_item_predictions(pred, target_y)
                    rows.append(
                        {
                            "feature_view": view.view_id,
                            "modality_set": view.modality_set,
                            "source_dataset": source_dataset,
                            "target_dataset": target_dataset,
                            "transfer_id": f"{source_dataset}_to_{target_dataset}_phq_shared",
                            "method": method,
                            "method_status": "executed",
                            "seed": int(seed),
                            "source_participant_count": int(len(source)),
                            "target_participant_count": int(len(target)),
                            "feature_adapter": f"pca_{min(args.baseline_pca_components, source_x.shape[1])}",
                            "domain_identity_ba": domain_identity_ba(adapted_source_x, adapted_target_x, seed=int(seed)),
                            **metrics,
                        }
                    )
                for method in ["dann", "irm", "groupdro"]:
                    pred, source_hidden, target_hidden = train_neural_baseline(
                        method,
                        source_x,
                        source_y,
                        target_x,
                        seed=int(seed),
                        epochs=args.deep_epochs,
                        hidden_dim=args.deep_hidden_dim,
                    )
                    metrics = evaluate_item_predictions(pred, target_y)
                    rows.append(
                        {
                            "feature_view": view.view_id,
                            "modality_set": view.modality_set,
                            "source_dataset": source_dataset,
                            "target_dataset": target_dataset,
                            "transfer_id": f"{source_dataset}_to_{target_dataset}_phq_shared",
                            "method": {
                                "dann": "dann_itemwise_mlp",
                                "irm": "irm_severity_env_proxy",
                                "groupdro": "groupdro_severity_proxy",
                            }[method],
                            "method_status": "executed" if method == "dann" else "executed_proxy",
                            "seed": int(seed),
                            "source_participant_count": int(len(source)),
                            "target_participant_count": int(len(target)),
                            "feature_adapter": f"pca_{min(args.baseline_pca_components, source_x.shape[1])}",
                            "domain_identity_ba": domain_identity_ba(source_hidden, target_hidden, seed=int(seed)),
                            **metrics,
                        }
                    )
    metrics_by_seed = pd.DataFrame(rows)
    summary = (
        metrics_by_seed.groupby(["feature_view", "modality_set", "transfer_id", "method", "method_status"], dropna=False)
        .agg(
            target_macro_item_mae_mean=("target_macro_item_mae", "mean"),
            target_macro_item_mae_std=("target_macro_item_mae", "std"),
            target_total_mae_mean=("target_total_mae", "mean"),
            target_total_mae_std=("target_total_mae", "std"),
            target_total_rmse_mean=("target_total_rmse", "mean"),
            domain_identity_ba_mean=("domain_identity_ba", "mean"),
            domain_identity_ba_std=("domain_identity_ba", "std"),
            seed_count=("seed", "nunique"),
            source_participant_count=("source_participant_count", "mean"),
            target_participant_count=("target_participant_count", "mean"),
        )
        .reset_index()
    )
    method_contract = pd.DataFrame(method_contract_rows())
    return metrics_by_seed, summary, method_contract


def measurement_reference_roots(previous_out: Path, current_out: Path) -> dict[str, tuple[str, Path]]:
    return {
        "bge_m3_text": ("bge_m3", downstream_dir_for(previous_out, "bge_m3", "mv12")),
        "multilingual_e5_base_text": (
            "multilingual_e5_base",
            downstream_dir_for(previous_out, "multilingual_e5_base", "mv12"),
        ),
        "qwen3_embedding_0_6b_text": (QWEN_SPEC.slug, downstream_dir_for(current_out, QWEN_SPEC.slug, "mv12")),
    }


def extract_measurement_aware_references(previous_out: Path, current_out: Path) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    protocol_map = {
        "cross_edaic_to_cmdc_phq": "edaic_to_cmdc_phq_shared",
        "cross_cmdc_to_edaic_phq": "cmdc_to_edaic_phq_shared",
    }
    for view_id, (encoder, mv12_dir) in measurement_reference_roots(previous_out, current_out).items():
        comparison_path = mv12_dir / "comparison_summary.csv"
        if not comparison_path.exists():
            rows.append(
                {
                    "feature_view": view_id,
                    "encoder_reference": encoder,
                    "transfer_id": "",
                    "method": "measurement_aware_mv12_reference",
                    "method_status": "missing_mv12_reference",
                    "target_macro_item_mae_mean": math.nan,
                    "target_total_mae_mean": math.nan,
                    "theta_mae_mean": math.nan,
                }
            )
            continue
        comparison = pd.read_csv(comparison_path)
        selected = comparison[
            comparison["protocol"].isin(protocol_map)
            & (
                (comparison["protocol"].eq("cross_cmdc_to_edaic_phq") & comparison["dataset_slice"].eq("edaic"))
                | (comparison["protocol"].eq("cross_edaic_to_cmdc_phq") & comparison["dataset_slice"].eq("cmdc"))
            )
            & comparison["model"].isin(["M12a_BGE_Ridge_X_to_theta", "B3_direct_itemwise_ridge"])
        ].copy()
        for _, row in selected.iterrows():
            method = (
                "measurement_aware_mv12_reference"
                if row["model"] == "M12a_BGE_Ridge_X_to_theta"
                else "mv12_direct_itemwise_reference"
            )
            rows.append(
                {
                    "feature_view": view_id,
                    "encoder_reference": encoder,
                    "transfer_id": protocol_map[str(row["protocol"])],
                    "method": method,
                    "method_status": "aggregate_reference",
                    "target_macro_item_mae_mean": float(row["observed_macro_item_mae"]),
                    "target_total_mae_mean": float(row["observed_total_mae"]),
                    "theta_mae_mean": float(row["theta_mae"]),
                    "delta_observed_macro_mae_vs_B3": float(row.get("delta_observed_macro_mae_vs_B3", math.nan)),
                    "delta_theta_mae_vs_B0": float(row.get("delta_theta_mae_vs_B0", math.nan)),
                }
            )
    return pd.DataFrame(rows)


def build_model_comparison(adaptation_summary: pd.DataFrame, measurement_refs: pd.DataFrame) -> pd.DataFrame:
    adaptation = adaptation_summary.rename(
        columns={
            "target_macro_item_mae_mean": "observed_macro_item_mae",
            "target_total_mae_mean": "observed_total_mae",
        }
    ).copy()
    adaptation["comparison_source"] = "mv22_adaptation_baseline_suite"
    adaptation["theta_mae_mean"] = math.nan
    keep_cols = [
        "feature_view",
        "transfer_id",
        "method",
        "method_status",
        "observed_macro_item_mae",
        "observed_total_mae",
        "theta_mae_mean",
        "domain_identity_ba_mean",
        "seed_count",
        "comparison_source",
    ]
    adaptation = adaptation[keep_cols]
    measurement = measurement_refs.rename(
        columns={
            "target_macro_item_mae_mean": "observed_macro_item_mae",
            "target_total_mae_mean": "observed_total_mae",
        }
    ).copy()
    measurement["domain_identity_ba_mean"] = math.nan
    measurement["seed_count"] = 1
    measurement["comparison_source"] = "mv12_downstream_aggregate_reference"
    measurement = measurement[keep_cols]
    combined = pd.concat([adaptation, measurement], ignore_index=True)
    return combined.sort_values(["feature_view", "transfer_id", "method"]).reset_index(drop=True)


def artifact_hygiene(out_dir: Path) -> dict[str, Any]:
    forbidden_patterns = [
        r"/root/",
        r"/autodl-tmp/",
        r"\bsubject_id\b",
        r"\btext_path\b",
        r"\baudio_path\b",
        r"\bvideo_path\b",
        r"\bgait_path\b",
        r"\.wav\b",
        r"\.mp4\b",
        r"\.avi\b",
        r"clinical transcript",
        r"row prediction",
        r"embedding matrix",
        r"fitted parameter",
    ]
    violations: list[dict[str, str]] = []
    checked = 0
    for name in sorted(TRACKED_FILES):
        path = out_dir / name
        if not path.exists() or not path.is_file():
            continue
        checked += 1
        text = path.read_text(encoding="utf-8", errors="ignore")
        for pattern in forbidden_patterns:
            if re.search(pattern, text, flags=re.IGNORECASE):
                violations.append({"file": path.name, "pattern": pattern})
    return {
        "audit_id": "P5_MV22_foundation_backbone_validation_hygiene",
        "generated_at": utc_now(),
        "files_checked": int(checked),
        "artifact_hygiene_passed": not violations,
        "violation_count": int(len(violations)),
        "violations": violations,
    }


def write_report(
    out_dir: Path,
    run_summary: dict[str, Any],
    feature_summary: pd.DataFrame,
    audio_summary: pd.DataFrame,
    downstream_extract: pd.DataFrame,
    adaptation_summary: pd.DataFrame,
    measurement_refs: pd.DataFrame,
) -> None:
    lines = [
        "# P5 MV22 Foundation Backbone Measurement-Aware Validation",
        "",
        f"Generated: `{run_summary['generated_at']}`",
        "",
        "## Scope",
        "",
        "MV22 adds a frozen Qwen3 text embedding backbone and reruns the MV07/MV12/MV15 measurement-aware diagnostic chain. It also adds a lightweight feature-adaptation baseline suite over PHQ shared items and records available WavLM audio proxy coverage.",
        "",
        "## Qwen Feature Contract",
        "",
        "| encoder | model | pooling | max length | dimensions | rows | chunks |",
        "| --- | --- | --- | ---: | ---: | ---: | ---: |",
    ]
    for _, row in feature_summary.sort_values("dataset").iterrows():
        lines.append(
            f"| {row['dataset']} | {row['model_name']} | {row['pooling']} | {int(row['max_length'])} | {int(row['feature_columns'])} | {int(row['feature_rows'])} | {int(row['chunk_count_sum'])} |"
        )
    lines.extend(
        [
            "",
            "## Audio Proxy Coverage",
            "",
            "| view | dataset | model | status | rows | dimensions |",
            "| --- | --- | --- | --- | ---: | ---: |",
        ]
    )
    for _, row in audio_summary.sort_values(["view_id", "dataset"]).iterrows():
        lines.append(
            f"| {row['view_id']} | {row['dataset']} | {row['model_name']} | {row['status']} | {int(row['rows'])} | {int(row['feature_columns'])} |"
        )
    lines.extend(
        [
            "",
            "## Downstream Diagnostic Extract",
            "",
            "| encoder | experiment | metric | value | status |",
            "| --- | --- | --- | ---: | --- |",
        ]
    )
    key_metrics = downstream_extract[
        downstream_extract["metric"].isin(
            [
                "feature_identity_ba",
                "prediction_identity_ba",
                "m12a_pooled_theta_mae",
                "conditional_identity_ba_m12a",
                "raw_feature_identity_ba",
                "theta_conditioned_feature_identity_ba",
                "psychometric_predicted_theta_output_identity_ba",
            ]
        )
    ].copy()
    for _, row in key_metrics.sort_values(["encoder", "experiment", "metric"]).iterrows():
        lines.append(
            f"| {row['encoder']} | {row['experiment']} | {row['metric']} | {float(row['value']):.4f} | {row['status']} |"
        )
    lines.extend(
        [
            "",
            "## Adaptation Baseline Suite",
            "",
            "| feature view | transfer | method | macro item MAE | total MAE | domain BA | seeds |",
            "| --- | --- | --- | ---: | ---: | ---: | ---: |",
        ]
    )
    if adaptation_summary.empty:
        lines.append("| none | none | skipped | nan | nan | nan | 0 |")
    else:
        display = adaptation_summary.sort_values(
            ["feature_view", "transfer_id", "target_macro_item_mae_mean"]
        ).groupby(["feature_view", "transfer_id"], as_index=False).head(4)
        for _, row in display.iterrows():
            lines.append(
                f"| {row['feature_view']} | {row['transfer_id']} | {row['method']} | {float(row['target_macro_item_mae_mean']):.4f} | {float(row['target_total_mae_mean']):.4f} | {float(row['domain_identity_ba_mean']):.4f} | {int(row['seed_count'])} |"
            )
    lines.extend(
        [
            "",
            "## Measurement-Aware References",
            "",
            "| feature view | transfer | method | macro item MAE | total MAE | theta MAE |",
            "| --- | --- | --- | ---: | ---: | ---: |",
        ]
    )
    for _, row in measurement_refs.sort_values(["feature_view", "transfer_id", "method"]).iterrows():
        macro = row.get("target_macro_item_mae_mean", math.nan)
        total = row.get("target_total_mae_mean", math.nan)
        theta = row.get("theta_mae_mean", math.nan)
        lines.append(
            f"| {row['feature_view']} | {row['transfer_id']} | {row['method']} | {float(macro):.4f} | {float(total):.4f} | {float(theta):.4f} |"
        )
    lines.extend(
        [
            "",
            "## Interpretation Boundary",
            "",
            "- This is a foundation-backbone stress test, not a depression-detection leaderboard.",
            "- Feature alignment baselines use target features without target labels; MV12 references use their predeclared downstream aggregate contracts.",
            "- WavLM base-plus is included as an audio foundation proxy in the first MV22 slice; WavLM Large is recorded as a separate compute-scope item.",
            "- No feature cache, participant-level score, prediction row, learned parameter, or clinical content is part of the tracked artifact set.",
            "",
            "## Decision",
            "",
            f"- Status: `{run_summary['status']}`.",
            f"- Artifact hygiene passed: `{run_summary['artifact_hygiene_passed']}`.",
            f"- Qwen downstream executed: `{run_summary['qwen_downstream_executed']}`.",
            f"- Adaptation baseline suite executed: `{run_summary['adaptation_baselines_executed']}`.",
        ]
    )
    (out_dir / "report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--edaic-manifest", type=Path, default=DEFAULT_EDAIC_MANIFEST)
    parser.add_argument("--manifest-dir", type=Path, default=MANIFEST_DIR)
    parser.add_argument("--split-path", type=Path, default=DEFAULT_SPLIT_PATH)
    parser.add_argument("--previous-mv17a-out", type=Path, default=DEFAULT_PREVIOUS_MV17A_OUT)
    parser.add_argument("--qwen-feature-root", type=Path, default=DEFAULT_QWEN_FEATURE_ROOT)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--device", default="auto")
    parser.add_argument("--allow-download", action="store_true")
    parser.add_argument("--force-qwen-features", action="store_true")
    parser.add_argument("--skip-qwen-features", action="store_true")
    parser.add_argument("--skip-downstream", action="store_true")
    parser.add_argument("--skip-adaptation-baselines", action="store_true")
    parser.add_argument("--include-audio-proxy-baseline", action="store_true")
    parser.add_argument("--qwen-max-length", type=int, default=QWEN_SPEC.default_max_length)
    parser.add_argument("--qwen-chunk-batch-size", type=int, default=QWEN_SPEC.default_chunk_batch_size)
    parser.add_argument("--baseline-pca-components", type=int, default=64)
    parser.add_argument("--baseline-seeds", nargs="+", type=int, default=[0, 1, 2])
    parser.add_argument("--deep-epochs", type=int, default=200)
    parser.add_argument("--deep-hidden-dim", type=int, default=64)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if not args.allow_download:
        os.environ.setdefault("HF_HUB_OFFLINE", "1")
        os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")
    out_dir = args.out_dir
    clean_tracked_outputs(out_dir)

    if args.skip_qwen_features:
        feature_summary = pd.DataFrame(columns=["dataset", "model_name", "pooling", "max_length", "feature_columns", "feature_rows", "chunk_count_sum"])
        feature_summary.to_csv(out_dir / "feature_generation_summary.csv", index=False)
        mv17a.write_encoder_contract(out_dir, [qwen_spec_with_cli(args)])
        pd.DataFrame(columns=["artifact", "artifact_class", "encoder", "dataset", "exists", "rows", "columns", "version_policy"]).to_csv(
            out_dir / "local_artifact_manifest.csv",
            index=False,
        )
    else:
        feature_summary = generate_qwen_features(args, out_dir)

    if args.skip_downstream:
        downstream = pd.DataFrame(columns=["encoder", "experiment", "status", "out_dir", "pass_rule_status", "artifact_hygiene_passed", "short_read"])
        downstream.to_csv(out_dir / "downstream_run_summary.csv", index=False)
    else:
        downstream = run_qwen_downstream(args, out_dir)

    audio_summary = summarize_audio_proxy_features()
    audio_summary.to_csv(out_dir / "audio_foundation_proxy_summary.csv", index=False)

    downstream_extract = extract_downstream_metrics(args.previous_mv17a_out, out_dir)
    downstream_extract.to_csv(out_dir / "downstream_metric_extract.csv", index=False)

    if args.skip_adaptation_baselines:
        adaptation_metrics = pd.DataFrame()
        adaptation_summary = pd.DataFrame()
        method_contract = pd.DataFrame(method_contract_rows())
    else:
        adaptation_metrics, adaptation_summary, method_contract = run_adaptation_baselines(args)
    adaptation_metrics.to_csv(out_dir / "adaptation_metrics_by_seed.csv", index=False)
    adaptation_summary.to_csv(out_dir / "adaptation_summary.csv", index=False)
    method_contract.to_csv(out_dir / "baseline_method_contract.csv", index=False)

    measurement_refs = extract_measurement_aware_references(args.previous_mv17a_out, out_dir)
    measurement_refs.to_csv(out_dir / "measurement_aware_reference_summary.csv", index=False)
    model_comparison = build_model_comparison(adaptation_summary, measurement_refs) if not adaptation_summary.empty else measurement_refs
    model_comparison.to_csv(out_dir / "model_comparison_summary.csv", index=False)

    run_summary = {
        "run_id": "P5_MV22_foundation_backbone_validation",
        "generated_at": utc_now(),
        "status": "complete",
        "scope": "foundation_backbone_measurement_aware_validation",
        "qwen_encoder": {
            "slug": QWEN_SPEC.slug,
            "model_name": QWEN_SPEC.model_name,
            "pooling": QWEN_SPEC.pooling,
            "max_length": int(args.qwen_max_length),
            "chunk_batch_size": int(args.qwen_chunk_batch_size),
            "expected_dimension": int(QWEN_SPEC.expected_dimension),
        },
        "baseline_feature_views": [view.view_id for view in TEXT_VIEWS if args.include_audio_proxy_baseline or not view.audio_proxy],
        "qwen_feature_generation_executed": not args.skip_qwen_features,
        "qwen_downstream_executed": not args.skip_downstream,
        "adaptation_baselines_executed": not args.skip_adaptation_baselines,
        "artifact_hygiene_passed": False,
        "output_policy": {
            "tracked_outputs": sorted(TRACKED_FILES),
            "local_only_qwen_feature_root": rel(args.qwen_feature_root),
            "downstream_prediction_outputs": "ignored_by_git",
        },
    }
    (out_dir / "run_summary.json").write_text(json.dumps(run_summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    write_report(out_dir, run_summary, feature_summary, audio_summary, downstream_extract, adaptation_summary, measurement_refs)
    hygiene = artifact_hygiene(out_dir)
    run_summary["artifact_hygiene_passed"] = bool(hygiene["artifact_hygiene_passed"])
    (out_dir / "run_summary.json").write_text(json.dumps(run_summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    write_report(out_dir, run_summary, feature_summary, audio_summary, downstream_extract, adaptation_summary, measurement_refs)
    hygiene = artifact_hygiene(out_dir)
    (out_dir / "artifact_hygiene_audit.json").write_text(
        json.dumps(hygiene, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    if not hygiene["artifact_hygiene_passed"]:
        raise SystemExit("artifact hygiene violations found; see artifact_hygiene_audit.json")

    print(
        json.dumps(
            {
                "out_dir": rel(out_dir),
                "qwen_feature_generation_executed": not args.skip_qwen_features,
                "qwen_downstream_executed": not args.skip_downstream,
                "adaptation_baselines_executed": not args.skip_adaptation_baselines,
                "artifact_hygiene_passed": bool(hygiene["artifact_hygiene_passed"]),
            },
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
