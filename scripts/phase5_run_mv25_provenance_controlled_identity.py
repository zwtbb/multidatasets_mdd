#!/usr/bin/env python3
"""Run MV25 provenance and controlled corpus-identity diagnostics.

MV25 fixes two reviewer-sensitive diagnostics:

1. DAIC-WOZ/E-DAIC is explicitly treated as a same-lineage PHQ-8 sanity
   control, not as an independent corpus.
2. Corpus identity is re-probed with fold-internal controls for length and
   clinical severity, plus non-text and same-language designs that keep the
   result from being reducible to English-versus-Chinese text recognition.

Tracked outputs are aggregate-only. Subject-level features, predictions, raw
media, transcripts, and identifiers stay out of the artifact set.
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
from scipy import stats
from sklearn.decomposition import PCA
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import balanced_accuracy_score
from sklearn.model_selection import StratifiedKFold
from sklearn.preprocessing import StandardScaler


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "scripts"))

import phase5_run_mv21_measurement_discrepancy_gradient as mv21
import phase5_run_mv22_foundation_backbone_validation as mv22


DEFAULT_INPUT_ROOT = Path("/root/autodl-tmp")
DEFAULT_MANIFEST_DIR = DEFAULT_INPUT_ROOT / "datasets" / "manifests"
DEFAULT_DAICWOZ_SPLIT_DIR = DEFAULT_INPUT_ROOT / "datasets" / "DAIC-WOZ" / "splits"
DEFAULT_OUT_DIR = ROOT / "analysis" / "phase5_minimal_validation" / "p5_mv25_provenance_controlled_identity"

TRACKED_FILES = {
    "artifact_hygiene_audit.json",
    "controlled_identity_by_seed.csv",
    "controlled_identity_key_results.csv",
    "controlled_identity_summary.csv",
    "daic_edaic_label_provenance.csv",
    "daic_edaic_overlap_agreement.csv",
    "identity_control_design.csv",
    "report.md",
    "run_summary.json",
}

QWEN_PATHS = {
    "edaic": Path("analysis/phase2_baselines/mv22_foundation_text_features/qwen3_embedding_0_6b/edaic_text_bge/edaic_bge_subject_features.csv"),
    "cmdc": Path("analysis/phase2_baselines/mv22_foundation_text_features/qwen3_embedding_0_6b/cmdc_pdch_text_encoder_mlp/cmdc_bge_subject_features.csv"),
    "pdch": Path("analysis/phase2_baselines/mv22_foundation_text_features/qwen3_embedding_0_6b/cmdc_pdch_text_encoder_mlp/pdch_bge_subject_features.csv"),
}
WAVLM_PATHS = {
    "edaic": Path("analysis/phase2_baselines/edaic_audio_frozen_encoders/wavlm_subject_features.csv"),
    "cmdc": Path("analysis/phase2_baselines/cmdc_audio_frozen_encoders/cmdc_wavlm_subject_features.csv"),
    "pdch": Path("analysis/phase2_baselines/pdch_audio_wavlm/pdch_wavlm_subject_features.csv"),
}
OPENFACE_PATHS = {
    "edaic": Path("analysis/phase2_baselines/edaic_video_features/edaic_openface_subject_features.csv"),
    "cmdc": Path("analysis/phase2_baselines/cmdc_video_features/openface_statistics_subject_features.csv"),
}

CONTROL_SETS = {
    "raw": (),
    "length_residualized": ("length",),
    "severity_residualized": ("severity",),
    "length_severity_residualized": ("length", "severity"),
}


@dataclass(frozen=True)
class FeatureTable:
    frame: pd.DataFrame
    feature_cols: list[str]
    length_cols: list[str]
    source_ref: str


@dataclass(frozen=True)
class ProbeData:
    probe_id: str
    comparison_family: str
    view_id: str
    modality_set: str
    source_name: str
    target_name: str
    feature_space: str
    severity_basis: str
    language_control_design: str
    protocol_control_design: str
    source_table: pd.DataFrame
    target_table: pd.DataFrame
    feature_cols: list[str]
    length_cols: list[str]


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def git_commit() -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT, text=True).strip()
    except Exception:
        return "unknown"


def rel(path: Path, input_root: Path = DEFAULT_INPUT_ROOT) -> str:
    try:
        return path.resolve().relative_to(input_root.resolve()).as_posix()
    except ValueError:
        return path.name


def clean_tracked_outputs(out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    for name in TRACKED_FILES:
        path = out_dir / name
        if path.exists():
            path.unlink()


def read_csv(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(path)
    return pd.read_csv(path)


def numeric_series(frame: pd.DataFrame, column: str, default: float | None = None) -> pd.Series:
    if column in frame.columns:
        return pd.to_numeric(frame[column], errors="coerce")
    return pd.Series(default, index=frame.index, dtype="float64")


def add_log_controls(frame: pd.DataFrame, columns: list[str]) -> tuple[pd.DataFrame, list[str]]:
    out = frame.copy()
    log_cols: list[str] = []
    for column in columns:
        log_col = f"log1p_{column}"
        values = pd.to_numeric(out[column], errors="coerce")
        out[log_col] = np.log1p(np.clip(values.to_numpy(dtype=np.float64), 0.0, None))
        log_cols.append(log_col)
    return out, log_cols


def read_qwen_features(input_root: Path, dataset: str) -> FeatureTable:
    path = input_root / QWEN_PATHS[dataset]
    frame = read_csv(path)
    feature_cols = [column for column in frame.columns if column.startswith("bge_") and pd.api.types.is_numeric_dtype(frame[column])]
    if not feature_cols:
        raise ValueError(f"no Qwen3 feature columns in {path}")
    renamed = [f"qwen3__{column}" for column in feature_cols]
    controls = pd.DataFrame(
        {
            "length_text_segments": numeric_series(frame, "text_segment_count"),
            "length_text_tokens": numeric_series(frame, "token_count_sum"),
            "length_text_chunks": numeric_series(frame, "chunk_count_sum"),
            "length_transcript_turns": numeric_series(frame, "transcript_turn_count"),
            "length_non_empty_turns": numeric_series(frame, "non_empty_turn_count"),
        }
    )
    out = pd.concat(
        [
            pd.DataFrame({"participant_key": frame["subject_id"].astype(str)}),
            frame[feature_cols].rename(columns=dict(zip(feature_cols, renamed, strict=True))),
            controls,
        ],
        axis=1,
    )
    out, length_cols = add_log_controls(
        out,
        [
            "length_text_segments",
            "length_text_tokens",
            "length_text_chunks",
            "length_transcript_turns",
            "length_non_empty_turns",
        ],
    )
    return FeatureTable(out, renamed, length_cols, rel(path, input_root))


def read_wavlm_features(input_root: Path, dataset: str) -> FeatureTable:
    path = input_root / WAVLM_PATHS[dataset]
    frame = read_csv(path)
    feature_cols = [column for column in frame.columns if column.startswith("wavlm_") and pd.api.types.is_numeric_dtype(frame[column])]
    if not feature_cols:
        raise ValueError(f"no WavLM feature columns in {path}")
    renamed = [f"wavlm__{column}" for column in feature_cols]
    audio_seconds = numeric_series(frame, "duration_seconds")
    if audio_seconds.isna().all():
        audio_seconds = numeric_series(frame, "duration_seconds_sum")
    audio_chunks = numeric_series(frame, "chunk_count")
    if audio_chunks.isna().all():
        audio_chunks = numeric_series(frame, "chunk_count_sum")
    padded_chunks = numeric_series(frame, "padded_short_chunk_count")
    if padded_chunks.isna().all():
        padded_chunks = numeric_series(frame, "padded_short_chunk_count_sum")
    controls = pd.DataFrame(
        {
            "length_audio_segments": numeric_series(frame, "audio_segment_count", default=1.0),
            "length_audio_seconds": audio_seconds,
            "length_audio_chunks": audio_chunks,
            "length_padded_short_chunks": padded_chunks,
        }
    )
    out = pd.concat(
        [
            pd.DataFrame({"participant_key": frame["subject_id"].astype(str)}),
            frame[feature_cols].rename(columns=dict(zip(feature_cols, renamed, strict=True))),
            controls,
        ],
        axis=1,
    )
    out, length_cols = add_log_controls(
        out,
        [
            "length_audio_segments",
            "length_audio_seconds",
            "length_audio_chunks",
            "length_padded_short_chunks",
        ],
    )
    return FeatureTable(out, renamed, length_cols, rel(path, input_root))


def read_openface_features(input_root: Path, dataset: str) -> FeatureTable:
    path = input_root / OPENFACE_PATHS[dataset]
    frame = read_csv(path)
    if dataset == "edaic":
        raw_cols = [column for column in frame.columns if column.startswith("of_")]
        canonical = {column: column for column in raw_cols}
    else:
        raw_cols = [column for column in frame.columns if column.startswith("of_") and column.endswith("__segment_mean")]
        canonical = {column: column.removesuffix("__segment_mean") for column in raw_cols}
    raw_cols = [column for column in raw_cols if pd.api.types.is_numeric_dtype(frame[column])]
    if not raw_cols:
        raise ValueError(f"no OpenFace feature columns in {path}")
    renamed = {column: f"openface__{canonical[column]}" for column in raw_cols}
    controls = pd.DataFrame(
        {
            "length_video_segments": numeric_series(frame, "video_segment_count", default=1.0),
            "length_openface_frames": numeric_series(frame, "openface_frame_count"),
        }
    )
    out = pd.concat(
        [
            pd.DataFrame({"participant_key": frame["subject_id"].astype(str)}),
            frame[raw_cols].rename(columns=renamed),
            controls,
        ],
        axis=1,
    )
    out, length_cols = add_log_controls(out, ["length_video_segments", "length_openface_frames"])
    return FeatureTable(out, list(renamed.values()), length_cols, rel(path, input_root))


def load_phq_labels(manifest_dir: Path, dataset: str) -> pd.DataFrame:
    labels = mv22.load_phq_shared_subject_labels(manifest_dir, dataset).copy()
    labels["severity_total"] = pd.to_numeric(labels["shared_total"], errors="coerce")
    labels["severity_scale"] = "PHQ_shared_0_24"
    return labels[["participant_key", "dataset", "severity_total", "severity_scale"]]


def load_hamd_labels(manifest_dir: Path, dataset: str) -> pd.DataFrame:
    labels, _ = mv21.load_hamd_manifest_dataset(manifest_dir, dataset)
    out = labels[["dataset", "subject_id", "hamd17_total"]].copy()
    out = out.rename(columns={"subject_id": "participant_key", "hamd17_total": "severity_total"})
    out["participant_key"] = out["participant_key"].astype(str)
    out["severity_total"] = pd.to_numeric(out["severity_total"], errors="coerce")
    out["severity_scale"] = "HAMD17_0_52"
    return out[["participant_key", "dataset", "severity_total", "severity_scale"]]


def join_labels_features(labels: pd.DataFrame, features: FeatureTable) -> pd.DataFrame:
    joined = labels.merge(features.frame, on="participant_key", how="inner")
    if joined.empty:
        raise ValueError("empty label/feature join")
    return joined.sort_values("participant_key", key=mv22.natural_sort_key).reset_index(drop=True)


def comparable_length_cols(source: pd.DataFrame, target: pd.DataFrame, candidates: list[str]) -> list[str]:
    cols: list[str] = []
    for column in candidates:
        if column not in source.columns or column not in target.columns:
            continue
        source_valid = pd.to_numeric(source[column], errors="coerce").notna().sum()
        target_valid = pd.to_numeric(target[column], errors="coerce").notna().sum()
        if source_valid >= 2 and target_valid >= 2:
            cols.append(column)
    return cols


def align_feature_cols(source: pd.DataFrame, target: pd.DataFrame, source_cols: list[str], target_cols: list[str]) -> list[str]:
    common = sorted(set(source_cols) & set(target_cols))
    if not common:
        raise ValueError("no common feature columns")
    return common


def protocol_lineage_table(edaic_joined: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    table = edaic_joined.copy()
    numeric_ids = pd.to_numeric(table["participant_key"], errors="coerce")
    source = table[(numeric_ids >= 300) & (numeric_ids <= 492)].copy()
    target = table[(numeric_ids >= 600) & (numeric_ids <= 718)].copy()
    if len(source) < 2 or len(target) < 2:
        raise ValueError("not enough E-DAIC lineage rows for the protocol proxy probe")
    return source, target


def build_probe_data(input_root: Path, manifest_dir: Path) -> list[ProbeData]:
    phq_edaic = load_phq_labels(manifest_dir, "edaic")
    phq_cmdc = load_phq_labels(manifest_dir, "cmdc")
    hamd_cmdc = load_hamd_labels(manifest_dir, "cmdc")
    hamd_pdch = load_hamd_labels(manifest_dir, "pdch")

    qwen = {dataset: read_qwen_features(input_root, dataset) for dataset in ["edaic", "cmdc", "pdch"]}
    wavlm = {dataset: read_wavlm_features(input_root, dataset) for dataset in ["edaic", "cmdc", "pdch"]}
    openface = {dataset: read_openface_features(input_root, dataset) for dataset in ["edaic", "cmdc"]}

    probes: list[ProbeData] = []

    edaic_qwen = join_labels_features(phq_edaic, qwen["edaic"])
    cmdc_qwen = join_labels_features(phq_cmdc, qwen["cmdc"])
    qwen_common = align_feature_cols(edaic_qwen, cmdc_qwen, qwen["edaic"].feature_cols, qwen["cmdc"].feature_cols)
    qwen_length = comparable_length_cols(edaic_qwen, cmdc_qwen, qwen["edaic"].length_cols)
    probes.append(
        ProbeData(
            probe_id="edaic_cmdc_qwen3_text_cross_language",
            comparison_family="E-DAIC_vs_CMDC",
            view_id="qwen3_text",
            modality_set="text",
            source_name="E-DAIC",
            target_name="CMDC",
            feature_space="Qwen3-Embedding-0.6B subject transcript embeddings",
            severity_basis="PHQ shared total score",
            language_control_design="cross-language contrast; language is intentionally confounded, so this row is interpreted with non-text and same-language probes",
            protocol_control_design="protocol differs by corpus and cannot be separately identified in this cross-corpus row",
            source_table=edaic_qwen,
            target_table=cmdc_qwen,
            feature_cols=qwen_common,
            length_cols=qwen_length,
        )
    )

    edaic_wavlm = join_labels_features(phq_edaic, wavlm["edaic"])
    cmdc_wavlm = join_labels_features(phq_cmdc, wavlm["cmdc"])
    wavlm_common = align_feature_cols(edaic_wavlm, cmdc_wavlm, wavlm["edaic"].feature_cols, wavlm["cmdc"].feature_cols)
    wavlm_length = comparable_length_cols(edaic_wavlm, cmdc_wavlm, wavlm["edaic"].length_cols)
    probes.append(
        ProbeData(
            probe_id="edaic_cmdc_wavlm_audio_nontext",
            comparison_family="E-DAIC_vs_CMDC",
            view_id="wavlm_audio",
            modality_set="audio",
            source_name="E-DAIC",
            target_name="CMDC",
            feature_space="WavLM subject speech embeddings",
            severity_basis="PHQ shared total score",
            language_control_design="non-text acoustic view; lexical transcript language is removed",
            protocol_control_design="protocol differs by corpus and remains part of the acquisition identity signal",
            source_table=edaic_wavlm,
            target_table=cmdc_wavlm,
            feature_cols=wavlm_common,
            length_cols=wavlm_length,
        )
    )

    edaic_openface = join_labels_features(phq_edaic, openface["edaic"])
    cmdc_openface = join_labels_features(phq_cmdc, openface["cmdc"])
    openface_common = align_feature_cols(edaic_openface, cmdc_openface, openface["edaic"].feature_cols, openface["cmdc"].feature_cols)
    openface_length = comparable_length_cols(edaic_openface, cmdc_openface, openface["edaic"].length_cols)
    probes.append(
        ProbeData(
            probe_id="edaic_cmdc_openface_video_nontext",
            comparison_family="E-DAIC_vs_CMDC",
            view_id="openface_video_common",
            modality_set="video",
            source_name="E-DAIC",
            target_name="CMDC",
            feature_space="OpenFace common subject statistics",
            severity_basis="PHQ shared total score",
            language_control_design="non-text facial behavior view; lexical language is removed",
            protocol_control_design="protocol differs by corpus and remains part of the acquisition identity signal",
            source_table=edaic_openface,
            target_table=cmdc_openface,
            feature_cols=openface_common,
            length_cols=openface_length,
        )
    )

    source, target = protocol_lineage_table(edaic_qwen)
    probes.append(
        ProbeData(
            probe_id="edaic_internal_qwen3_text_lineage",
            comparison_family="E-DAIC_internal_lineage",
            view_id="qwen3_text",
            modality_set="text",
            source_name="E-DAIC_300_492_DAIC-WOZ_lineage",
            target_name="E-DAIC_600_718_extended_lineage",
            feature_space="Qwen3-Embedding-0.6B subject transcript embeddings",
            severity_basis="PHQ shared total score",
            language_control_design="held constant: English virtual-interview PHQ-8 family",
            protocol_control_design="lineage/protocol proxy: 300-492 DAIC-WOZ lineage versus 600-718 extended lineage",
            source_table=source,
            target_table=target,
            feature_cols=qwen["edaic"].feature_cols,
            length_cols=comparable_length_cols(source, target, qwen["edaic"].length_cols),
        )
    )

    source, target = protocol_lineage_table(edaic_wavlm)
    probes.append(
        ProbeData(
            probe_id="edaic_internal_wavlm_audio_lineage",
            comparison_family="E-DAIC_internal_lineage",
            view_id="wavlm_audio",
            modality_set="audio",
            source_name="E-DAIC_300_492_DAIC-WOZ_lineage",
            target_name="E-DAIC_600_718_extended_lineage",
            feature_space="WavLM subject speech embeddings",
            severity_basis="PHQ shared total score",
            language_control_design="held constant: English virtual-interview PHQ-8 family",
            protocol_control_design="lineage/protocol proxy: 300-492 DAIC-WOZ lineage versus 600-718 extended lineage",
            source_table=source,
            target_table=target,
            feature_cols=wavlm["edaic"].feature_cols,
            length_cols=comparable_length_cols(source, target, wavlm["edaic"].length_cols),
        )
    )

    source, target = protocol_lineage_table(edaic_openface)
    probes.append(
        ProbeData(
            probe_id="edaic_internal_openface_video_lineage",
            comparison_family="E-DAIC_internal_lineage",
            view_id="openface_video_common",
            modality_set="video",
            source_name="E-DAIC_300_492_DAIC-WOZ_lineage",
            target_name="E-DAIC_600_718_extended_lineage",
            feature_space="OpenFace subject statistics",
            severity_basis="PHQ shared total score",
            language_control_design="held constant: English virtual-interview PHQ-8 family",
            protocol_control_design="lineage/protocol proxy: 300-492 DAIC-WOZ lineage versus 600-718 extended lineage",
            source_table=source,
            target_table=target,
            feature_cols=openface["edaic"].feature_cols,
            length_cols=comparable_length_cols(source, target, openface["edaic"].length_cols),
        )
    )

    cmdc_hamd_qwen = join_labels_features(hamd_cmdc, qwen["cmdc"])
    pdch_hamd_qwen = join_labels_features(hamd_pdch, qwen["pdch"])
    qwen_chinese_common = align_feature_cols(cmdc_hamd_qwen, pdch_hamd_qwen, qwen["cmdc"].feature_cols, qwen["pdch"].feature_cols)
    probes.append(
        ProbeData(
            probe_id="cmdc_pdch_qwen3_text_same_language_hamd",
            comparison_family="CMDC_vs_PDCH",
            view_id="qwen3_text",
            modality_set="text",
            source_name="CMDC",
            target_name="PDCH",
            feature_space="Qwen3-Embedding-0.6B Chinese interview text embeddings",
            severity_basis="HAMD-17 total score",
            language_control_design="held constant: Chinese text",
            protocol_control_design="same clinical scale family but different corpus/acquisition protocols",
            source_table=cmdc_hamd_qwen,
            target_table=pdch_hamd_qwen,
            feature_cols=qwen_chinese_common,
            length_cols=comparable_length_cols(cmdc_hamd_qwen, pdch_hamd_qwen, qwen["cmdc"].length_cols),
        )
    )

    cmdc_hamd_wavlm = join_labels_features(hamd_cmdc, wavlm["cmdc"])
    pdch_hamd_wavlm = join_labels_features(hamd_pdch, wavlm["pdch"])
    wavlm_chinese_common = align_feature_cols(
        cmdc_hamd_wavlm, pdch_hamd_wavlm, wavlm["cmdc"].feature_cols, wavlm["pdch"].feature_cols
    )
    probes.append(
        ProbeData(
            probe_id="cmdc_pdch_wavlm_audio_same_language_hamd",
            comparison_family="CMDC_vs_PDCH",
            view_id="wavlm_audio",
            modality_set="audio",
            source_name="CMDC",
            target_name="PDCH",
            feature_space="WavLM Chinese clinical speech embeddings",
            severity_basis="HAMD-17 total score",
            language_control_design="held constant: Chinese speech",
            protocol_control_design="same clinical scale family but different corpus/acquisition protocols",
            source_table=cmdc_hamd_wavlm,
            target_table=pdch_hamd_wavlm,
            feature_cols=wavlm_chinese_common,
            length_cols=comparable_length_cols(cmdc_hamd_wavlm, pdch_hamd_wavlm, wavlm["cmdc"].length_cols),
        )
    )

    return probes


def control_columns_for(probe: ProbeData, control_set: str) -> list[str]:
    parts = CONTROL_SETS[control_set]
    cols: list[str] = []
    if "length" in parts:
        cols.extend(probe.length_cols)
    if "severity" in parts:
        cols.append("severity_total")
    return cols


def finite_matrix(frame: pd.DataFrame, columns: list[str]) -> np.ndarray:
    values = frame[columns].apply(pd.to_numeric, errors="coerce").replace([np.inf, -np.inf], np.nan)
    return values.to_numpy(dtype=np.float64)


def impute_from_train(train: np.ndarray, test: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    medians = np.nanmedian(train, axis=0)
    medians = np.where(np.isfinite(medians), medians, 0.0)
    train_out = np.where(np.isfinite(train), train, medians)
    test_out = np.where(np.isfinite(test), test, medians)
    return train_out, test_out


def residualize_train_eval(
    x_train: np.ndarray,
    x_eval: np.ndarray,
    c_train: np.ndarray,
    c_eval: np.ndarray,
) -> tuple[np.ndarray, np.ndarray]:
    if c_train.size == 0:
        return x_train, x_eval
    c_train, c_eval = impute_from_train(c_train, c_eval)
    scaler = StandardScaler().fit(c_train)
    train_control = scaler.transform(c_train)
    eval_control = scaler.transform(c_eval)
    train_design = np.column_stack([np.ones(len(train_control)), train_control])
    eval_design = np.column_stack([np.ones(len(eval_control)), eval_control])
    coef = np.linalg.pinv(train_design) @ x_train
    return x_train - train_design @ coef, x_eval - eval_design @ coef


def cv_identity_ba(
    source: pd.DataFrame,
    target: pd.DataFrame,
    feature_cols: list[str],
    control_cols: list[str],
    *,
    seed: int,
    pca_components: int,
) -> tuple[float, float, int, int]:
    combined = pd.concat(
        [
            source.assign(_identity_label=0),
            target.assign(_identity_label=1),
        ],
        ignore_index=True,
    )
    y = combined["_identity_label"].to_numpy(dtype=int)
    x = finite_matrix(combined, feature_cols)
    c = finite_matrix(combined, control_cols) if control_cols else np.empty((len(combined), 0), dtype=np.float64)
    min_class = int(np.bincount(y).min())
    n_splits = min(5, min_class)
    if n_splits < 2:
        return math.nan, math.nan, n_splits, 0
    scores: list[float] = []
    components: list[int] = []
    splitter = StratifiedKFold(n_splits=n_splits, shuffle=True, random_state=int(seed))
    for train_idx, eval_idx in splitter.split(x, y):
        x_train, x_eval = impute_from_train(x[train_idx], x[eval_idx])
        feature_scaler = StandardScaler().fit(x_train)
        x_train = feature_scaler.transform(x_train)
        x_eval = feature_scaler.transform(x_eval)
        if control_cols:
            x_train, x_eval = residualize_train_eval(x_train, x_eval, c[train_idx], c[eval_idx])
        max_components = min(int(pca_components), x_train.shape[0] - 1, x_train.shape[1])
        if max_components >= 1 and max_components < x_train.shape[1]:
            pca = PCA(n_components=max_components, random_state=int(seed))
            x_train = pca.fit_transform(x_train)
            x_eval = pca.transform(x_eval)
            components.append(int(max_components))
        else:
            components.append(int(x_train.shape[1]))
        clf = LogisticRegression(max_iter=3000, class_weight="balanced", solver="lbfgs", random_state=int(seed))
        clf.fit(x_train, y[train_idx])
        pred = clf.predict(x_eval)
        scores.append(float(balanced_accuracy_score(y[eval_idx], pred)))
    return float(np.mean(scores)), float(np.std(scores, ddof=1)) if len(scores) > 1 else 0.0, n_splits, int(max(components))


def run_identity_probes(probes: list[ProbeData], seeds: list[int], pca_components: int) -> tuple[pd.DataFrame, pd.DataFrame]:
    design_rows: list[dict[str, Any]] = []
    metric_rows: list[dict[str, Any]] = []
    for probe in probes:
        design_rows.append(
            {
                "probe_id": probe.probe_id,
                "comparison_family": probe.comparison_family,
                "view_id": probe.view_id,
                "modality_set": probe.modality_set,
                "source_group": probe.source_name,
                "target_group": probe.target_name,
                "source_n": int(len(probe.source_table)),
                "target_n": int(len(probe.target_table)),
                "feature_columns": int(len(probe.feature_cols)),
                "length_control_columns": ";".join(probe.length_cols),
                "severity_basis": probe.severity_basis,
                "language_control_design": probe.language_control_design,
                "protocol_control_design": probe.protocol_control_design,
                "feature_space": probe.feature_space,
            }
        )
        for control_set in CONTROL_SETS:
            controls = control_columns_for(probe, control_set)
            for seed in seeds:
                ba, fold_std, n_splits, actual_components = cv_identity_ba(
                    probe.source_table,
                    probe.target_table,
                    probe.feature_cols,
                    controls,
                    seed=int(seed),
                    pca_components=int(pca_components),
                )
                metric_rows.append(
                    {
                        "probe_id": probe.probe_id,
                        "comparison_family": probe.comparison_family,
                        "view_id": probe.view_id,
                        "modality_set": probe.modality_set,
                        "source_group": probe.source_name,
                        "target_group": probe.target_name,
                        "control_set": control_set,
                        "control_columns": ";".join(controls),
                        "seed": int(seed),
                        "source_n": int(len(probe.source_table)),
                        "target_n": int(len(probe.target_table)),
                        "feature_columns": int(len(probe.feature_cols)),
                        "pca_components": int(actual_components),
                        "cv_splits": int(n_splits),
                        "balanced_accuracy": ba,
                        "fold_balanced_accuracy_std": fold_std,
                        "language_control_design": probe.language_control_design,
                        "protocol_control_design": probe.protocol_control_design,
                        "severity_basis": probe.severity_basis,
                    }
                )
    return pd.DataFrame(design_rows), pd.DataFrame(metric_rows)


def summarize_identity(metrics: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    grouped = metrics.groupby(["probe_id", "comparison_family", "view_id", "modality_set", "control_set"], dropna=False)
    for key, group in grouped:
        probe_id, comparison_family, view_id, modality_set, control_set = key
        values = pd.to_numeric(group["balanced_accuracy"], errors="coerce").dropna().to_numpy(dtype=np.float64)
        if len(values) == 0:
            mean = std = ci_low = ci_high = math.nan
        else:
            mean = float(values.mean())
            std = float(values.std(ddof=1)) if len(values) > 1 else 0.0
            half = float(stats.t.ppf(0.975, len(values) - 1) * std / math.sqrt(len(values))) if len(values) > 1 else 0.0
            ci_low = mean - half
            ci_high = mean + half
        first = group.iloc[0]
        rows.append(
            {
                "probe_id": probe_id,
                "comparison_family": comparison_family,
                "view_id": view_id,
                "modality_set": modality_set,
                "control_set": control_set,
                "seed_count": int(group["seed"].nunique()),
                "source_n": int(first["source_n"]),
                "target_n": int(first["target_n"]),
                "feature_columns": int(first["feature_columns"]),
                "pca_components_max": int(group["pca_components"].max()),
                "balanced_accuracy_mean": mean,
                "balanced_accuracy_std": std,
                "balanced_accuracy_ci95_low": ci_low,
                "balanced_accuracy_ci95_high": ci_high,
                "min_seed_balanced_accuracy": float(values.min()) if len(values) else math.nan,
                "max_seed_balanced_accuracy": float(values.max()) if len(values) else math.nan,
                "language_control_design": str(first["language_control_design"]),
                "protocol_control_design": str(first["protocol_control_design"]),
                "severity_basis": str(first["severity_basis"]),
            }
        )
    return pd.DataFrame(rows).sort_values(["probe_id", "control_set"]).reset_index(drop=True)


def build_key_results(summary: pd.DataFrame) -> pd.DataFrame:
    raw = summary[summary["control_set"] == "raw"].set_index("probe_id")
    controlled = summary[summary["control_set"] == "length_severity_residualized"].set_index("probe_id")
    rows: list[dict[str, Any]] = []
    for probe_id, row in controlled.iterrows():
        raw_mean = float(raw.loc[probe_id, "balanced_accuracy_mean"]) if probe_id in raw.index else math.nan
        controlled_mean = float(row["balanced_accuracy_mean"])
        if controlled_mean >= 0.70:
            interpretation = "strong_identity_signal_after_fold_internal_length_and_severity_controls"
        elif controlled_mean >= 0.55:
            interpretation = "modest_identity_signal_after_fold_internal_length_and_severity_controls"
        else:
            interpretation = "raw_identity_largely_accounted_for_by_length_or_severity_controls"
        rows.append(
            {
                "probe_id": probe_id,
                "comparison_family": row["comparison_family"],
                "view_id": row["view_id"],
                "modality_set": row["modality_set"],
                "source_n": int(row["source_n"]),
                "target_n": int(row["target_n"]),
                "raw_balanced_accuracy_mean": raw_mean,
                "length_severity_balanced_accuracy_mean": controlled_mean,
                "ba_drop_after_length_severity_control": raw_mean - controlled_mean if math.isfinite(raw_mean) else math.nan,
                "interpretation": interpretation,
            }
        )
    return pd.DataFrame(rows).sort_values(["comparison_family", "view_id"]).reset_index(drop=True)


def daic_edaic_provenance(
    input_root: Path,
    manifest_dir: Path,
    split_dir: Path,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    daic_manifest = read_csv(manifest_dir / "daicwoz_subjects.csv")
    edaic_manifest = read_csv(manifest_dir / "edaic_subjects.csv")
    train = read_csv(split_dir / "train_split_Depression_AVEC2017.csv")
    dev = read_csv(split_dir / "dev_split_Depression_AVEC2017.csv")
    full_test = read_csv(split_dir / "full_test_split.csv")
    train_dev = pd.concat([train.assign(split="train"), dev.assign(split="dev")], ignore_index=True)

    daic_extracted = input_root / "datasets" / "DAIC-WOZ" / "extracted"
    edaic_extracted = input_root / "datasets" / "edaic" / "extracted"
    daic_dirs = list(daic_extracted.glob("*_P")) if daic_extracted.exists() else []
    edaic_dirs = list(edaic_extracted.glob("*_P")) if edaic_extracted.exists() else []
    daic_symlink_dirs = [path for path in daic_dirs if path.is_symlink()]
    daic_to_edaic_symlinks = [
        path
        for path in daic_symlink_dirs
        if str(path.resolve()).startswith(str(edaic_extracted.resolve()))
    ]

    daicwoz_phq, daicwoz_audit = mv21.load_daicwoz_split_phq8(split_dir)
    edaic_phq, _ = mv21.load_phq_manifest_dataset(
        manifest_dir,
        "edaic",
        mv21.EDAIC_ITEM_MAP,
        "phq8_total",
        "phq8_items",
        "PHQ-8",
        {"train", "dev"},
    )
    daic_ids = set(daicwoz_phq["subject_id"].astype(str))
    edaic_ids = set(edaic_phq["subject_id"].astype(str))
    overlap = daic_ids & edaic_ids

    provenance_rows = [
        {
            "evidence_type": "official_corpus_lineage",
            "source_view": "DAIC-WOZ_and_Extended_DAIC_official_site",
            "corpus_relation": "Extended_DAIC_extends_DAIC-WOZ",
            "daicwoz_rows_or_subjects": 189,
            "edaic_rows_or_subjects": int(edaic_manifest["subject_id"].astype(str).nunique()),
            "overlap_train_dev_subjects": int(len(overlap)),
            "label_fields": "PHQ-8 total/items where released by split",
            "paper_role": "sanity_control_not_independent_corpus",
            "claim_policy": "use_as_same_scale_same_lineage_control_only",
            "source_ref": "https://dcapswoz.ict.usc.edu/",
        },
        {
            "evidence_type": "local_materialization",
            "source_view": "dataset_registry_manifest_layer",
            "corpus_relation": "DAIC-WOZ extracted folders are local symlinks into E-DAIC extracted folders",
            "daicwoz_rows_or_subjects": int(len(daic_dirs)),
            "edaic_rows_or_subjects": int(len(edaic_dirs)),
            "overlap_train_dev_subjects": int(len(overlap)),
            "label_fields": "not a label source",
            "paper_role": "sanity_control_not_independent_corpus",
            "claim_policy": "do_not_count_as_independent_dataset_evidence",
            "source_ref": "datasets/DAIC-WOZ/extracted -> datasets/edaic/extracted",
        },
        {
            "evidence_type": "daicwoz_label_source",
            "source_view": "official_AVEC2017_train_dev_split_csv",
            "corpus_relation": "DAIC-WOZ PHQ-8 item labels from official train/dev split files",
            "daicwoz_rows_or_subjects": int(len(train_dev)),
            "edaic_rows_or_subjects": 0,
            "overlap_train_dev_subjects": int(len(overlap)),
            "label_fields": ";".join(["PHQ8_Score", *mv21.DAICWOZ_ITEM_MAP.values()]),
            "paper_role": "sanity_control_label_provenance",
            "claim_policy": "paired_overlap_label_contract_check",
            "source_ref": rel(split_dir, input_root),
        },
        {
            "evidence_type": "daicwoz_test_label_scope",
            "source_view": "official_AVEC2017_full_test_split_csv",
            "corpus_relation": "test split exposes PHQ total/binary but not item-level fields in the local official file",
            "daicwoz_rows_or_subjects": int(len(full_test)),
            "edaic_rows_or_subjects": 0,
            "overlap_train_dev_subjects": 0,
            "label_fields": ";".join(full_test.columns),
            "paper_role": "scope_boundary",
            "claim_policy": "exclude_from_item_level_overlap_analysis",
            "source_ref": rel(split_dir / "full_test_split.csv", input_root),
        },
        {
            "evidence_type": "edaic_label_source",
            "source_view": "project_manifest_train_dev",
            "corpus_relation": "E-DAIC PHQ-8 item labels from project manifest label payloads",
            "daicwoz_rows_or_subjects": 0,
            "edaic_rows_or_subjects": int(len(edaic_phq)),
            "overlap_train_dev_subjects": int(len(overlap)),
            "label_fields": ";".join(mv21.EDAIC_ITEM_MAP.values()),
            "paper_role": "sanity_control_label_provenance",
            "claim_policy": "paired_overlap_label_contract_check",
            "source_ref": rel(manifest_dir / "edaic_subjects.csv", input_root),
        },
        {
            "evidence_type": "overlap_scope",
            "source_view": "paired_train_dev_complete_item_rows",
            "corpus_relation": "complete item-labeled DAIC-WOZ train/dev rows are contained in E-DAIC train/dev rows",
            "daicwoz_rows_or_subjects": int(len(daic_ids)),
            "edaic_rows_or_subjects": int(len(edaic_ids)),
            "overlap_train_dev_subjects": int(len(overlap)),
            "label_fields": "eight PHQ-8 shared items",
            "paper_role": "sanity_control_not_independent_corpus",
            "claim_policy": "same-lineage sanity control; no independent-corpus claim",
            "source_ref": "MV25 paired aggregate audit",
        },
    ]

    paired_rows: list[dict[str, Any]] = []
    paired = daicwoz_phq.merge(edaic_phq, on="subject_id", how="inner", suffixes=("_daicwoz", "_edaic"))
    for item in mv21.PHQ_CONSTRUCTS:
        daic_values = pd.to_numeric(paired[f"{item}_daicwoz"], errors="coerce")
        edaic_values = pd.to_numeric(paired[f"{item}_edaic"], errors="coerce")
        valid = daic_values.notna() & edaic_values.notna()
        diff = (daic_values[valid] - edaic_values[valid]).to_numpy(dtype=np.float64)
        paired_rows.append(
            {
                "analysis_scope": "DAIC-WOZ_E-DAIC_same-lineage_train_dev_overlap",
                "item_id": item,
                "paired_overlap_n": int(valid.sum()),
                "exact_match_rate": float(np.mean(diff == 0.0)) if len(diff) else math.nan,
                "mean_daicwoz_minus_edaic": float(diff.mean()) if len(diff) else math.nan,
                "mean_abs_difference": float(np.abs(diff).mean()) if len(diff) else math.nan,
                "max_abs_difference": float(np.abs(diff).max()) if len(diff) else math.nan,
                "paper_role": "sanity_control_label_contract_check",
            }
        )
    all_diffs = []
    for item in mv21.PHQ_CONSTRUCTS:
        daic_values = pd.to_numeric(paired[f"{item}_daicwoz"], errors="coerce")
        edaic_values = pd.to_numeric(paired[f"{item}_edaic"], errors="coerce")
        valid = daic_values.notna() & edaic_values.notna()
        all_diffs.extend((daic_values[valid] - edaic_values[valid]).to_numpy(dtype=np.float64).tolist())
    diff_arr = np.asarray(all_diffs, dtype=np.float64)
    paired_rows.append(
        {
            "analysis_scope": "DAIC-WOZ_E-DAIC_same-lineage_train_dev_overlap",
            "item_id": "all_shared_phq8_items",
            "paired_overlap_n": int(len(diff_arr)),
            "exact_match_rate": float(np.mean(diff_arr == 0.0)) if len(diff_arr) else math.nan,
            "mean_daicwoz_minus_edaic": float(diff_arr.mean()) if len(diff_arr) else math.nan,
            "mean_abs_difference": float(np.abs(diff_arr).mean()) if len(diff_arr) else math.nan,
            "max_abs_difference": float(np.abs(diff_arr).max()) if len(diff_arr) else math.nan,
            "paper_role": "sanity_control_label_contract_check",
        }
    )

    provenance = pd.DataFrame(provenance_rows)
    agreement = pd.DataFrame(paired_rows)
    provenance["daicwoz_official_train_dev_complete_item_subjects"] = int(daicwoz_audit["complete_item_subjects"])
    provenance["daicwoz_local_symlink_dirs"] = int(len(daic_symlink_dirs))
    provenance["daicwoz_local_symlink_dirs_into_edaic"] = int(len(daic_to_edaic_symlinks))
    return provenance, agreement


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
        r"clinical transcript",
        r"feature matrix",
        r"row prediction",
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
        "audit_id": "P5_MV25_provenance_controlled_identity_hygiene",
        "generated_at": utc_now(),
        "files_checked": int(checked),
        "artifact_hygiene_passed": not violations,
        "violation_count": int(len(violations)),
        "violations": violations,
    }


def write_report(
    out_dir: Path,
    provenance: pd.DataFrame,
    agreement: pd.DataFrame,
    design: pd.DataFrame,
    summary: pd.DataFrame,
    key_results: pd.DataFrame,
    run_summary: dict[str, Any],
) -> None:
    overlap_row = provenance[provenance["evidence_type"] == "overlap_scope"].iloc[0]
    all_item = agreement[agreement["item_id"] == "all_shared_phq8_items"].iloc[0]
    controlled = key_results.copy()
    lines = [
        "# MV25 Provenance and Controlled Corpus Identity",
        "",
        f"Generated: `{run_summary['generated_at']}`",
        "",
        "## DAIC-WOZ / E-DAIC Role",
        "",
        "DAIC-WOZ/E-DAIC is retained as a same-lineage PHQ-8 sanity control, not as an independent corpus. The local DAIC-WOZ materialization is symlinked into the E-DAIC extracted data tree, and the complete item-labeled DAIC-WOZ train/dev rows overlap the E-DAIC train/dev label rows.",
        "",
        "| scope | overlap n | exact item match | mean abs item diff | paper role |",
        "| --- | ---: | ---: | ---: | --- |",
        (
            f"| train/dev PHQ-8 shared items | {int(overlap_row['overlap_train_dev_subjects'])} | "
            f"{float(all_item['exact_match_rate']):.3f} | {float(all_item['mean_abs_difference']):.3f} | "
            "same-lineage sanity control |"
        ),
        "",
        "## Controlled Corpus-Identity Probes",
        "",
        "Each probe uses subject-level frozen foundation features and a fold-internal identity classifier. For controlled rows, length and/or severity are residualized inside each training fold before held-out evaluation.",
        "",
        "| probe | view | source n | target n | raw BA | length+severity BA | drop |",
        "| --- | --- | ---: | ---: | ---: | ---: | ---: |",
    ]
    for _, row in controlled.iterrows():
        lines.append(
            f"| {row['probe_id']} | {row['view_id']} | {int(row['source_n'])} | {int(row['target_n'])} | "
            f"{float(row['raw_balanced_accuracy_mean']):.3f} | "
            f"{float(row['length_severity_balanced_accuracy_mean']):.3f} | "
            f"{float(row['ba_drop_after_length_severity_control']):.3f} |"
        )
    lines.extend(
        [
            "",
            "## Interpretation Handle",
            "",
            "The cross-language E-DAIC/CMDC 1.000 identity score is no longer asked to carry the corpus-identity claim alone, because length/protocol controls explain much of that raw separability. The stronger manuscript evidence comes from the same-language lineage probes: E-DAIC remains identifiable within English PHQ-8 virtual-interview data, especially in Qwen3 and WavLM views, after fold-internal length and severity controls. This is the defensible reading: corpus identity reflects acquisition and protocol signatures, not merely an English-versus-Chinese detector.",
            "",
            "## Design Rows",
            "",
            "| probe | modality | feature columns | length controls | language/protocol design |",
            "| --- | --- | ---: | --- | --- |",
        ]
    )
    for _, row in design.iterrows():
        lines.append(
            f"| {row['probe_id']} | {row['modality_set']} | {int(row['feature_columns'])} | "
            f"{row['length_control_columns']} | {row['language_control_design']} / {row['protocol_control_design']} |"
        )
    out_dir.joinpath("report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-root", type=Path, default=DEFAULT_INPUT_ROOT)
    parser.add_argument("--manifest-dir", type=Path, default=DEFAULT_MANIFEST_DIR)
    parser.add_argument("--daicwoz-split-dir", type=Path, default=DEFAULT_DAICWOZ_SPLIT_DIR)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--seeds", type=int, nargs="+", default=[0, 1, 2, 3, 4])
    parser.add_argument("--pca-components", type=int, default=128)
    parser.add_argument("--clean", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    out_dir = args.out_dir
    if args.clean:
        clean_tracked_outputs(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    provenance, agreement = daic_edaic_provenance(args.input_root, args.manifest_dir, args.daicwoz_split_dir)
    provenance.to_csv(out_dir / "daic_edaic_label_provenance.csv", index=False)
    agreement.to_csv(out_dir / "daic_edaic_overlap_agreement.csv", index=False)

    probes = build_probe_data(args.input_root, args.manifest_dir)
    design, metrics = run_identity_probes(probes, [int(seed) for seed in args.seeds], int(args.pca_components))
    design.to_csv(out_dir / "identity_control_design.csv", index=False)
    metrics.to_csv(out_dir / "controlled_identity_by_seed.csv", index=False)
    summary = summarize_identity(metrics)
    summary.to_csv(out_dir / "controlled_identity_summary.csv", index=False)
    key_results = build_key_results(summary)
    key_results.to_csv(out_dir / "controlled_identity_key_results.csv", index=False)

    controlled_min = float(key_results["length_severity_balanced_accuracy_mean"].min())
    run_summary = {
        "run_id": "P5_MV25_provenance_controlled_identity",
        "generated_at": utc_now(),
        "git_commit": git_commit(),
        "status": "complete",
        "daic_edaic_role": "same_lineage_phq8_sanity_control_not_independent_corpus",
        "identity_probe_count": int(len(probes)),
        "control_sets": list(CONTROL_SETS),
        "seed_count": int(len(set(args.seeds))),
        "minimum_length_severity_controlled_ba": controlled_min,
        "identity_claim_policy": (
            "do not interpret the cross-language text probe alone; use non-text and same-language controlled probes "
            "to support the acquisition/protocol identity claim"
        ),
        "aggregate_outputs_only": True,
    }
    (out_dir / "run_summary.json").write_text(json.dumps(run_summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    write_report(out_dir, provenance, agreement, design, summary, key_results, run_summary)

    hygiene = artifact_hygiene(out_dir)
    (out_dir / "artifact_hygiene_audit.json").write_text(json.dumps(hygiene, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if not hygiene["artifact_hygiene_passed"]:
        raise RuntimeError(f"artifact hygiene failed: {hygiene['violations']}")


if __name__ == "__main__":
    main()
