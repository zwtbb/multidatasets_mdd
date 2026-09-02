#!/usr/bin/env python3
"""Run MV23 foundation multimodal completion stress test.

MV23 completes the practical foundation-backbone reinforcement after MV22. It
does not train a full depression detector. It reuses local-only subject feature
caches and exports only aggregate PHQ shared-item transfer metrics, modality
coverage, measurement-aware proxy summaries, and hygiene checks.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import re
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
from sklearn.linear_model import Ridge
from sklearn.preprocessing import StandardScaler

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "scripts"))

import phase5_run_mv17a_multilingual_feature_contract as mv17a
import phase5_run_mv22_foundation_backbone_validation as mv22


DEFAULT_OUT_DIR = ROOT / "analysis" / "phase5_minimal_validation" / "p5_mv23_foundation_multimodal_completion"
DEFAULT_MV17_FEATURE_ROOT = ROOT / "analysis" / "phase2_baselines" / "mv17_multilingual_text_features"
DEFAULT_MV22_FEATURE_ROOT = ROOT / "analysis" / "phase2_baselines" / "mv22_foundation_text_features"
DEFAULT_MV22_OUT = ROOT / "analysis" / "phase5_minimal_validation" / "p5_mv22_foundation_backbone_validation"
MANIFEST_DIR = ROOT / "datasets" / "manifests"

TRACKED_FILES = {
    "adapter_metrics_by_seed.csv",
    "adapter_summary.csv",
    "artifact_hygiene_audit.json",
    "cache_coverage_summary.csv",
    "head_comparison_summary.csv",
    "measurement_proxy_summary.csv",
    "modality_view_contract.csv",
    "report.md",
    "run_summary.json",
}

PHQ_ITEM_IDS = [item[0] for item in mv22.PHQ_SHARED_ITEMS]


@dataclass(frozen=True)
class AssetSpec:
    asset_id: str
    modality: str
    model_name: str
    feature_prefix: str
    paths: dict[str, Path]
    canonicalizer: str = "prefix"


@dataclass(frozen=True)
class ViewSpec:
    view_id: str
    modality_set: str
    assets: tuple[str, ...]
    role: str


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def text_paths(feature_root: Path, encoder_slug: str) -> dict[str, Path]:
    return mv17a.feature_paths(feature_root, mv22.encoder_spec_for_slug(encoder_slug))


def asset_specs(args: argparse.Namespace) -> dict[str, AssetSpec]:
    bge_paths = text_paths(args.mv17_feature_root, "bge_m3")
    e5_paths = text_paths(args.mv17_feature_root, "multilingual_e5_base")
    qwen_paths = text_paths(args.mv22_feature_root, mv22.QWEN_SPEC.slug)
    return {
        "text_bge_m3": AssetSpec(
            "text_bge_m3",
            "text",
            "BAAI/bge-m3",
            mv17a.FEATURE_PREFIX,
            {"edaic": bge_paths["edaic"], "cmdc": bge_paths["cmdc"]},
        ),
        "text_multilingual_e5": AssetSpec(
            "text_multilingual_e5",
            "text",
            "intfloat/multilingual-e5-base",
            mv17a.FEATURE_PREFIX,
            {"edaic": e5_paths["edaic"], "cmdc": e5_paths["cmdc"]},
        ),
        "text_qwen3": AssetSpec(
            "text_qwen3",
            "text",
            mv22.QWEN_SPEC.model_name,
            mv17a.FEATURE_PREFIX,
            {"edaic": qwen_paths["edaic"], "cmdc": qwen_paths["cmdc"]},
        ),
        "audio_wavlm_base_plus": AssetSpec(
            "audio_wavlm_base_plus",
            "audio",
            "microsoft/wavlm-base-plus",
            "wavlm_",
            {
                "edaic": ROOT / "analysis" / "phase2_baselines" / "edaic_audio_frozen_encoders" / "wavlm_subject_features.csv",
                "cmdc": ROOT
                / "analysis"
                / "phase2_baselines"
                / "cmdc_audio_frozen_encoders"
                / "cmdc_wavlm_subject_features.csv",
            },
        ),
        "audio_wav2vec2_base": AssetSpec(
            "audio_wav2vec2_base",
            "audio",
            "facebook/wav2vec2-base",
            "wav2vec2_",
            {
                "edaic": ROOT
                / "analysis"
                / "phase2_baselines"
                / "edaic_audio_frozen_encoders"
                / "wav2vec2_subject_features.csv",
                "cmdc": ROOT
                / "analysis"
                / "phase2_baselines"
                / "cmdc_audio_frozen_encoders"
                / "cmdc_wav2vec2_subject_features.csv",
            },
        ),
        "video_openface_common": AssetSpec(
            "video_openface_common",
            "video",
            "OpenFace statistical facial-action/prosody proxy",
            "of_",
            {
                "edaic": ROOT
                / "analysis"
                / "phase2_baselines"
                / "edaic_video_features"
                / "edaic_openface_subject_features.csv",
                "cmdc": ROOT
                / "analysis"
                / "phase2_baselines"
                / "cmdc_video_features"
                / "openface_statistics_subject_features.csv",
            },
            canonicalizer="openface_common",
        ),
    }


def view_specs() -> list[ViewSpec]:
    return [
        ViewSpec("audio_wavlm_base_plus", "audio", ("audio_wavlm_base_plus",), "audio foundation baseline"),
        ViewSpec("audio_wav2vec2_base", "audio", ("audio_wav2vec2_base",), "audio foundation baseline"),
        ViewSpec("video_openface_common", "video", ("video_openface_common",), "video proxy baseline"),
        ViewSpec(
            "qwen3_plus_wavlm_audio",
            "text_audio",
            ("text_qwen3", "audio_wavlm_base_plus"),
            "foundation fusion baseline",
        ),
        ViewSpec(
            "qwen3_plus_wav2vec2_audio",
            "text_audio",
            ("text_qwen3", "audio_wav2vec2_base"),
            "foundation fusion sensitivity",
        ),
        ViewSpec(
            "qwen3_plus_wavlm_audio_plus_openface_video",
            "text_audio_video",
            ("text_qwen3", "audio_wavlm_base_plus", "video_openface_common"),
            "lightweight multimodal foundation baseline",
        ),
        ViewSpec(
            "bge_m3_plus_wavlm_audio_plus_openface_video",
            "text_audio_video",
            ("text_bge_m3", "audio_wavlm_base_plus", "video_openface_common"),
            "multilingual text sensitivity multimodal baseline",
        ),
        ViewSpec(
            "multilingual_e5_plus_wavlm_audio_plus_openface_video",
            "text_audio_video",
            ("text_multilingual_e5", "audio_wavlm_base_plus", "video_openface_common"),
            "multilingual text sensitivity multimodal baseline",
        ),
    ]


def natural_sort(frame: pd.DataFrame, key: str = "participant_key") -> pd.DataFrame:
    return frame.sort_values(key, key=mv22.natural_sort_key).reset_index(drop=True)


def read_prefix_asset(spec: AssetSpec, dataset: str) -> tuple[pd.DataFrame, list[str]]:
    path = spec.paths[dataset]
    if not path.exists():
        raise FileNotFoundError(f"missing local asset cache: {path}")
    frame = pd.read_csv(path)
    if "subject_id" not in frame.columns:
        raise ValueError(f"asset cache missing subject_id: {path}")
    feature_cols = [
        column
        for column in frame.columns
        if column.startswith(spec.feature_prefix) and pd.api.types.is_numeric_dtype(frame[column])
    ]
    if not feature_cols:
        raise ValueError(f"no numeric columns for {spec.asset_id}/{dataset}")
    renamed = {column: f"{spec.asset_id}__{column}" for column in feature_cols}
    out = pd.concat(
        [frame["subject_id"].astype(str).rename("participant_key"), frame[feature_cols].rename(columns=renamed)],
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
    return (ed_frame[["participant_key", *common]].copy(), common), (cm_frame[["participant_key", *common]].copy(), common)


def load_view_tables(view: ViewSpec, assets: dict[str, AssetSpec]) -> tuple[dict[str, pd.DataFrame], list[str], list[dict[str, Any]]]:
    frames_by_dataset: dict[str, list[pd.DataFrame]] = {"edaic": [], "cmdc": []}
    cols_by_dataset: dict[str, list[str]] = {"edaic": [], "cmdc": []}
    coverage_rows: list[dict[str, Any]] = []
    for asset_id in view.assets:
        spec = assets[asset_id]
        loaded = {dataset: read_asset(spec, dataset) for dataset in ["edaic", "cmdc"]}
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
                    "cache_status": "available",
                    "cache_rows": int(len(frame)),
                    "input_columns": int(len(columns)),
                    "cache_ref": rel(spec.paths[dataset]),
                }
            )
    merged_by_dataset: dict[str, pd.DataFrame] = {}
    for dataset in ["edaic", "cmdc"]:
        merged = frames_by_dataset[dataset][0]
        for frame in frames_by_dataset[dataset][1:]:
            merged = merged.merge(frame, on="participant_key", how="inner")
        labels = mv22.load_phq_shared_subject_labels(MANIFEST_DIR, dataset)
        joined = labels.merge(merged, on="participant_key", how="inner")
        merged_by_dataset[dataset] = natural_sort(joined)
    if cols_by_dataset["edaic"] != cols_by_dataset["cmdc"]:
        raise ValueError(f"column mismatch for {view.view_id}")
    return merged_by_dataset, cols_by_dataset["edaic"], coverage_rows


def sanitize_pair(source: pd.DataFrame, target: pd.DataFrame, columns: list[str]) -> tuple[pd.DataFrame, pd.DataFrame]:
    src = source.copy()
    tgt = target.copy()
    for column in columns:
        src_values = pd.to_numeric(src[column], errors="coerce").replace([np.inf, -np.inf], np.nan)
        median = float(src_values.median()) if src_values.notna().any() else 0.0
        src[column] = src_values.fillna(median)
        tgt[column] = pd.to_numeric(tgt[column], errors="coerce").replace([np.inf, -np.inf], np.nan).fillna(median)
    return src, tgt


def run_standard_adapters(
    view: ViewSpec,
    source_dataset: str,
    target_dataset: str,
    source: pd.DataFrame,
    target: pd.DataFrame,
    feature_cols: list[str],
    args: argparse.Namespace,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    source_y = mv22.label_arrays(source)
    target_y = mv22.label_arrays(target)
    for seed in args.baseline_seeds:
        source_x, target_x, _ = mv22.prepare_pair_features(
            source,
            target,
            feature_cols,
            n_components=args.pca_components,
            seed=int(seed),
        )
        method_inputs = [
            ("erm_itemwise_ridge", source_x, target_x),
            ("coral_itemwise_ridge", mv22.coral_source_to_target(source_x, target_x), target_x),
            (
                "mmd_mean_itemwise_ridge",
                source_x - source_x.mean(axis=0, keepdims=True) + target_x.mean(axis=0, keepdims=True),
                target_x,
            ),
        ]
        for method, adapted_source_x, adapted_target_x in method_inputs:
            pred = mv22.fit_ridge_itemwise(adapted_source_x, source_y, adapted_target_x)
            metrics = mv22.evaluate_item_predictions(pred, target_y)
            rows.append(
                {
                    "view_id": view.view_id,
                    "modality_set": view.modality_set,
                    "transfer_id": f"{source_dataset}_to_{target_dataset}_phq_shared",
                    "source_dataset": source_dataset,
                    "target_dataset": target_dataset,
                    "method": method,
                    "method_status": "executed",
                    "seed": int(seed),
                    "source_participant_count": int(len(source)),
                    "target_participant_count": int(len(target)),
                    "input_columns": int(len(feature_cols)),
                    "pca_components": int(min(args.pca_components, source_x.shape[1])),
                    "domain_identity_ba": mv22.domain_identity_ba(adapted_source_x, adapted_target_x, seed=int(seed)),
                    **metrics,
                }
            )
        for method in ["dann", "irm", "groupdro"]:
            pred, source_hidden, target_hidden = mv22.train_neural_baseline(
                method,
                source_x,
                source_y,
                target_x,
                seed=int(seed),
                epochs=args.deep_epochs,
                hidden_dim=args.hidden_dim,
            )
            metrics = mv22.evaluate_item_predictions(pred, target_y)
            rows.append(
                {
                    "view_id": view.view_id,
                    "modality_set": view.modality_set,
                    "transfer_id": f"{source_dataset}_to_{target_dataset}_phq_shared",
                    "source_dataset": source_dataset,
                    "target_dataset": target_dataset,
                    "method": {
                        "dann": "dann_itemwise_mlp",
                        "irm": "irm_severity_env_proxy",
                        "groupdro": "groupdro_severity_proxy",
                    }[method],
                    "method_status": "executed" if method == "dann" else "executed_proxy",
                    "seed": int(seed),
                    "source_participant_count": int(len(source)),
                    "target_participant_count": int(len(target)),
                    "input_columns": int(len(feature_cols)),
                    "pca_components": int(min(args.pca_components, source_x.shape[1])),
                    "domain_identity_ba": mv22.domain_identity_ba(source_hidden, target_hidden, seed=int(seed)),
                    **metrics,
                }
            )
    return rows


def zscore_total(labels: np.ndarray) -> tuple[np.ndarray, float, float]:
    total = labels.sum(axis=1).astype(np.float64)
    mean = float(np.mean(total))
    std = float(np.std(total))
    if std <= 1e-6:
        std = 1.0
    return ((total - mean) / std).astype(np.float32), mean, std


def run_measurement_proxy(
    view: ViewSpec,
    source_dataset: str,
    target_dataset: str,
    source: pd.DataFrame,
    target: pd.DataFrame,
    feature_cols: list[str],
    args: argparse.Namespace,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    source_y = mv22.label_arrays(source)
    target_y = mv22.label_arrays(target)
    source_theta, _, _ = zscore_total(source_y)
    target_theta, _, _ = zscore_total(target_y)
    for seed in args.baseline_seeds:
        source_x, target_x, _ = mv22.prepare_pair_features(
            source,
            target,
            feature_cols,
            n_components=args.pca_components,
            seed=int(seed),
        )
        theta_model = Ridge(alpha=1.0)
        theta_model.fit(source_x, source_theta)
        pred_target_theta = theta_model.predict(target_x).astype(np.float32)
        pred_source_theta = theta_model.predict(source_x).astype(np.float32)
        measurement_head = Ridge(alpha=0.1)
        measurement_head.fit(target_theta.reshape(-1, 1), target_y)
        pred_items = measurement_head.predict(pred_target_theta.reshape(-1, 1)).astype(np.float32)
        item_metrics = mv22.evaluate_item_predictions(pred_items, target_y)
        post_source = measurement_head.predict(pred_source_theta.reshape(-1, 1)).astype(np.float32)
        post_target = pred_items
        rows.append(
            {
                "view_id": view.view_id,
                "modality_set": view.modality_set,
                "transfer_id": f"{source_dataset}_to_{target_dataset}_phq_shared",
                "source_dataset": source_dataset,
                "target_dataset": target_dataset,
                "method": "measurement_aware_latent_total_proxy",
                "method_status": "executed_proxy",
                "seed": int(seed),
                "source_participant_count": int(len(source)),
                "target_participant_count": int(len(target)),
                "input_columns": int(len(feature_cols)),
                "pca_components": int(min(args.pca_components, source_x.shape[1])),
                "theta_mae": float(np.mean(np.abs(pred_target_theta - target_theta))),
                "latent_domain_identity_ba": mv22.domain_identity_ba(
                    pred_source_theta.reshape(-1, 1),
                    pred_target_theta.reshape(-1, 1),
                    seed=int(seed),
                ),
                "post_head_domain_identity_ba": mv22.domain_identity_ba(post_source, post_target, seed=int(seed)),
                **item_metrics,
            }
        )
    return rows


def summarize_adapters(rows: pd.DataFrame) -> pd.DataFrame:
    return (
        rows.groupby(["view_id", "modality_set", "transfer_id", "method", "method_status"], dropna=False)
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
            input_columns=("input_columns", "max"),
        )
        .reset_index()
        .fillna({"target_macro_item_mae_std": 0.0, "target_total_mae_std": 0.0, "domain_identity_ba_std": 0.0})
    )


def summarize_measurement(rows: pd.DataFrame) -> pd.DataFrame:
    return (
        rows.groupby(["view_id", "modality_set", "transfer_id", "method", "method_status"], dropna=False)
        .agg(
            target_macro_item_mae_mean=("target_macro_item_mae", "mean"),
            target_macro_item_mae_std=("target_macro_item_mae", "std"),
            target_total_mae_mean=("target_total_mae", "mean"),
            target_total_mae_std=("target_total_mae", "std"),
            theta_mae_mean=("theta_mae", "mean"),
            theta_mae_std=("theta_mae", "std"),
            latent_domain_identity_ba_mean=("latent_domain_identity_ba", "mean"),
            post_head_domain_identity_ba_mean=("post_head_domain_identity_ba", "mean"),
            seed_count=("seed", "nunique"),
            source_participant_count=("source_participant_count", "mean"),
            target_participant_count=("target_participant_count", "mean"),
            input_columns=("input_columns", "max"),
        )
        .reset_index()
        .fillna({"target_macro_item_mae_std": 0.0, "target_total_mae_std": 0.0, "theta_mae_std": 0.0})
    )


def build_head_comparison(adapter_summary: pd.DataFrame, measurement_summary: pd.DataFrame) -> pd.DataFrame:
    adapter = adapter_summary.rename(
        columns={
            "target_macro_item_mae_mean": "observed_macro_item_mae",
            "target_total_mae_mean": "observed_total_mae",
            "domain_identity_ba_mean": "representation_domain_identity_ba",
        }
    ).copy()
    adapter["theta_mae_mean"] = math.nan
    adapter["post_head_domain_identity_ba_mean"] = math.nan
    adapter["comparison_family"] = "direct_or_alignment_baseline"
    measurement = measurement_summary.rename(
        columns={
            "target_macro_item_mae_mean": "observed_macro_item_mae",
            "target_total_mae_mean": "observed_total_mae",
            "latent_domain_identity_ba_mean": "representation_domain_identity_ba",
        }
    ).copy()
    measurement["comparison_family"] = "measurement_aware_proxy"
    keep = [
        "view_id",
        "modality_set",
        "transfer_id",
        "method",
        "method_status",
        "comparison_family",
        "observed_macro_item_mae",
        "observed_total_mae",
        "theta_mae_mean",
        "representation_domain_identity_ba",
        "post_head_domain_identity_ba_mean",
        "seed_count",
        "source_participant_count",
        "target_participant_count",
        "input_columns",
    ]
    return pd.concat([adapter[keep], measurement[keep]], ignore_index=True).sort_values(
        ["view_id", "transfer_id", "observed_macro_item_mae", "method"]
    )


def build_view_contract(views: list[ViewSpec], assets: dict[str, AssetSpec]) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for view in views:
        rows.append(
            {
                "view_id": view.view_id,
                "modality_set": view.modality_set,
                "asset_ids": ";".join(view.assets),
                "models": ";".join(assets[item].model_name for item in view.assets),
                "role": view.role,
                "measurement_head": "latent_total_proxy_plus_corpus_specific_phq_shared_item_head",
                "claim_boundary": "foundation-view stress test only; not a SOTA or full-method success claim",
            }
        )
    return pd.DataFrame(rows)


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
        if not path.exists():
            continue
        checked += 1
        text = path.read_text(encoding="utf-8", errors="ignore")
        for pattern in forbidden_patterns:
            if re.search(pattern, text, flags=re.IGNORECASE):
                violations.append({"file": path.name, "pattern": pattern})
    return {
        "audit_id": "P5_MV23_foundation_multimodal_completion_hygiene",
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
    adapter_summary: pd.DataFrame,
    measurement_summary: pd.DataFrame,
    comparison: pd.DataFrame,
) -> None:
    lines = [
        "# P5 MV23 Foundation Multimodal Completion Stress Test",
        "",
        f"Generated: `{run_summary['generated_at']}`",
        "",
        "## Scope",
        "",
        "MV23 completes the lightweight foundation-backbone reinforcement by adding audio-only, video-proxy, text-audio, and text-audio-video feature views to the same PHQ shared-item transfer contract used in MV22. It compares direct/alignment baselines with a lightweight measurement-aware latent-total proxy head.",
        "",
        "## View Coverage",
        "",
        "| view | dataset | asset | modality | rows | input columns |",
        "| --- | --- | --- | --- | ---: | ---: |",
    ]
    for _, row in coverage.sort_values(["view_id", "dataset", "asset_id"]).iterrows():
        lines.append(
            f"| {row['view_id']} | {row['dataset']} | {row['asset_id']} | {row['modality']} | {int(row['cache_rows'])} | {int(row['input_columns'])} |"
        )
    lines.extend(
        [
            "",
            "## Best Direct Or Alignment Baselines",
            "",
            "| view | transfer | method | macro item MAE | total MAE | domain BA | target N |",
            "| --- | --- | --- | ---: | ---: | ---: | ---: |",
        ]
    )
    best_adapter = adapter_summary.sort_values(["view_id", "transfer_id", "target_macro_item_mae_mean"]).groupby(
        ["view_id", "transfer_id"], as_index=False
    ).head(2)
    for _, row in best_adapter.iterrows():
        domain = row.get("domain_identity_ba_mean", math.nan)
        lines.append(
            f"| {row['view_id']} | {row['transfer_id']} | {row['method']} | {float(row['target_macro_item_mae_mean']):.4f} | {float(row['target_total_mae_mean']):.4f} | {float(domain):.4f} | {int(round(row['target_participant_count']))} |"
        )
    lines.extend(
        [
            "",
            "## Measurement-Aware Proxy",
            "",
            "| view | transfer | macro item MAE | total MAE | theta MAE | latent BA | post-head BA | target N |",
            "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |",
        ]
    )
    for _, row in measurement_summary.sort_values(["view_id", "transfer_id"]).iterrows():
        lines.append(
            f"| {row['view_id']} | {row['transfer_id']} | {float(row['target_macro_item_mae_mean']):.4f} | {float(row['target_total_mae_mean']):.4f} | {float(row['theta_mae_mean']):.4f} | {float(row['latent_domain_identity_ba_mean']):.4f} | {float(row['post_head_domain_identity_ba_mean']):.4f} | {int(round(row['target_participant_count']))} |"
        )
    best_rows = comparison.sort_values(["transfer_id", "observed_macro_item_mae"]).groupby("transfer_id", as_index=False).head(5)
    lines.extend(
        [
            "",
            "## Cross-View Top Rows",
            "",
            "| transfer | view | method | family | macro item MAE | total MAE | identity BA |",
            "| --- | --- | --- | --- | ---: | ---: | ---: |",
        ]
    )
    for _, row in best_rows.iterrows():
        ident = row.get("post_head_domain_identity_ba_mean")
        if pd.isna(ident):
            ident = row.get("representation_domain_identity_ba", math.nan)
        lines.append(
            f"| {row['transfer_id']} | {row['view_id']} | {row['method']} | {row['comparison_family']} | {float(row['observed_macro_item_mae']):.4f} | {float(row['observed_total_mae']):.4f} | {float(ident):.4f} |"
        )
    lines.extend(
        [
            "",
            "## Interpretation Boundary",
            "",
            "- MV23 is a bounded foundation-view stress test, not a full multimodal training run.",
            "- Audio uses existing WavLM base-plus and wav2vec2-base caches; WavLM Large/HuBERT Large remain unclaimed unless separate caches are generated.",
            "- Video is an OpenFace common-statistics proxy, not VideoMAE.",
            "- The measurement-aware row is a lightweight latent-total proxy head, used to test the framework logic under stronger/fused representations.",
            "- No participant-level feature matrix, prediction row, theta table, model internals, raw text, raw audio, or raw video is tracked.",
            "",
            "## Decision",
            "",
            f"- Status: `{run_summary['status']}`.",
            f"- Artifact hygiene passed: `{run_summary['artifact_hygiene_passed']}`.",
            f"- Views executed: `{run_summary['view_count']}`.",
        ]
    )
    (out_dir / "report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--mv17-feature-root", type=Path, default=DEFAULT_MV17_FEATURE_ROOT)
    parser.add_argument("--mv22-feature-root", type=Path, default=DEFAULT_MV22_FEATURE_ROOT)
    parser.add_argument("--mv22-out", type=Path, default=DEFAULT_MV22_OUT)
    parser.add_argument("--pca-components", type=int, default=64)
    parser.add_argument("--baseline-seeds", nargs="+", type=int, default=[0, 1, 2])
    parser.add_argument("--deep-epochs", type=int, default=160)
    parser.add_argument("--hidden-dim", type=int, default=64)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    args.out_dir.mkdir(parents=True, exist_ok=True)
    for name in TRACKED_FILES:
        path = args.out_dir / name
        if path.exists():
            path.unlink()

    assets = asset_specs(args)
    views = view_specs()
    adapter_rows: list[dict[str, Any]] = []
    measurement_rows: list[dict[str, Any]] = []
    coverage_rows: list[dict[str, Any]] = []
    directions = [("edaic", "cmdc"), ("cmdc", "edaic")]
    for view in views:
        tables, feature_cols, view_coverage = load_view_tables(view, assets)
        coverage_rows.extend(view_coverage)
        for source_dataset, target_dataset in directions:
            source, target = sanitize_pair(tables[source_dataset], tables[target_dataset], feature_cols)
            adapter_rows.extend(run_standard_adapters(view, source_dataset, target_dataset, source, target, feature_cols, args))
            measurement_rows.extend(run_measurement_proxy(view, source_dataset, target_dataset, source, target, feature_cols, args))

    adapter_metrics = pd.DataFrame(adapter_rows)
    adapter_summary = summarize_adapters(adapter_metrics)
    measurement_metrics = pd.DataFrame(measurement_rows)
    measurement_summary = summarize_measurement(measurement_metrics)
    comparison = build_head_comparison(adapter_summary, measurement_summary)
    coverage = pd.DataFrame(coverage_rows)
    view_contract = build_view_contract(views, assets)

    adapter_metrics.to_csv(args.out_dir / "adapter_metrics_by_seed.csv", index=False)
    adapter_summary.to_csv(args.out_dir / "adapter_summary.csv", index=False)
    measurement_summary.to_csv(args.out_dir / "measurement_proxy_summary.csv", index=False)
    comparison.to_csv(args.out_dir / "head_comparison_summary.csv", index=False)
    coverage.to_csv(args.out_dir / "cache_coverage_summary.csv", index=False)
    view_contract.to_csv(args.out_dir / "modality_view_contract.csv", index=False)

    run_summary = {
        "run_id": "P5_MV23_foundation_multimodal_completion",
        "generated_at": utc_now(),
        "status": "complete",
        "scope": "foundation_multimodal_measurement_aware_completion_stress_test",
        "view_count": int(len(views)),
        "adapter_row_count": int(len(adapter_metrics)),
        "measurement_proxy_row_count": int(len(measurement_metrics)),
        "transfer_directions": ["edaic_to_cmdc_phq_shared", "cmdc_to_edaic_phq_shared"],
        "executed_views": [view.view_id for view in views],
        "artifact_hygiene_passed": False,
        "unclaimed_future_scope": ["wavlm_large_audio", "hubert_large_audio", "videomae_video", "end_to_end_multimodal_finetuning"],
        "output_policy": {
            "tracked_outputs": sorted(TRACKED_FILES),
            "local_only_input_caches": "analysis/phase2_baselines/",
            "row_predictions": "not_written",
            "feature_matrices": "not_written",
        },
    }
    (args.out_dir / "run_summary.json").write_text(json.dumps(run_summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    write_report(args.out_dir, run_summary, coverage, adapter_summary, measurement_summary, comparison)
    hygiene = artifact_hygiene(args.out_dir)
    run_summary["artifact_hygiene_passed"] = bool(hygiene["artifact_hygiene_passed"])
    (args.out_dir / "run_summary.json").write_text(json.dumps(run_summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    write_report(args.out_dir, run_summary, coverage, adapter_summary, measurement_summary, comparison)
    hygiene = artifact_hygiene(args.out_dir)
    (args.out_dir / "artifact_hygiene_audit.json").write_text(json.dumps(hygiene, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if not hygiene["artifact_hygiene_passed"]:
        raise SystemExit("artifact hygiene violations found; see artifact_hygiene_audit.json")
    print(
        json.dumps(
            {
                "out_dir": rel(args.out_dir),
                "status": run_summary["status"],
                "view_count": run_summary["view_count"],
                "artifact_hygiene_passed": run_summary["artifact_hygiene_passed"],
            },
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
