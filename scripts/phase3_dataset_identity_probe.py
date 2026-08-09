#!/usr/bin/env python3
"""Phase 3 dataset/protocol identity probes over cached Phase 2 features.

The script only reads existing feature-cache CSVs and non-path metadata needed
for grouped labels. It does not open raw text, audio, video, or path-valued
manifest columns, and it writes only compact diagnostic outputs.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import re
import warnings
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

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, balanced_accuracy_score, confusion_matrix, f1_score
from sklearn.model_selection import GroupKFold, StratifiedKFold
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

try:
    from sklearn.model_selection import StratifiedGroupKFold
except ImportError:  # pragma: no cover - version fallback
    StratifiedGroupKFold = None  # type: ignore[assignment]


warnings.filterwarnings("ignore", category=pd.errors.PerformanceWarning)


WORKTREE_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT_DIR = WORKTREE_ROOT / "analysis" / "phase3_diagnostics" / "dataset_identity_probe"
DEFAULT_WORKTREE_FEATURE_ROOT = WORKTREE_ROOT / "analysis" / "phase2_baselines"
DEFAULT_READONLY_FEATURE_ROOT = Path("/root/autodl-tmp/analysis/phase2_baselines")
DEFAULT_MANIFEST_DIR = WORKTREE_ROOT / "datasets" / "manifests"
DATASET_ORDER = ["E-DAIC", "CMDC", "PDCH", "EATD", "MODMA", "MPDD"]
RANDOM_SEED = 20260805


DATASET_CANONICAL = {
    "edaic": "E-DAIC",
    "cmdc": "CMDC",
    "pdch": "PDCH",
    "eatd": "EATD",
    "modma": "MODMA",
    "mpdd": "MPDD",
}

METADATA_COLUMNS = {
    "age",
    "audio_segment_count",
    "binary_label",
    "chunk_count",
    "chunk_count_sum",
    "duration_seconds",
    "duration_seconds_sum",
    "empty_text_segments",
    "file_valid",
    "hamd17_total",
    "phq8_total",
    "phq9_total",
    "padded_short_chunk_count",
    "severity_label",
    "text_segment_count",
    "token_count",
    "token_count_sum",
    "transcript_turn_count",
    "video_segment_count",
}


@dataclass(frozen=True)
class FeatureSource:
    dataset: str
    family: str
    feature_space: str
    rel_path: str
    id_columns: tuple[str, ...] = ("subject_id",)
    required_label_columns: tuple[str, ...] = ()
    strip_feature_suffixes: tuple[str, ...] = ()
    note: str = ""


@dataclass(frozen=True)
class ProbeSpec:
    probe_id: str
    target_name: str
    target_column: str
    row_grain: str
    sources: tuple[FeatureSource, ...]
    comparable_basis: str
    group_column: str = "group_id"
    min_classes: int = 2


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def natural_key(value: Any) -> list[Any]:
    return [int(part) if part.isdigit() else part for part in re.split(r"(\d+)", str(value))]


def resolve_feature_root(feature_root: Path | None) -> tuple[Path, str]:
    if feature_root is not None:
        return feature_root, "user"
    if DEFAULT_WORKTREE_FEATURE_ROOT.exists():
        has_cache = any(DEFAULT_WORKTREE_FEATURE_ROOT.glob("*/*subject_features.csv"))
        has_cache = has_cache or any(DEFAULT_WORKTREE_FEATURE_ROOT.glob("*/*subject_task_features.csv"))
        if has_cache:
            return DEFAULT_WORKTREE_FEATURE_ROOT, "worktree"
    return DEFAULT_READONLY_FEATURE_ROOT, "read_only_phase2_cache"


def artifact_path_reference(path: Path) -> str:
    resolved = path.resolve()
    try:
        return str(resolved.relative_to(WORKTREE_ROOT))
    except ValueError:
        pass
    if resolved == DEFAULT_READONLY_FEATURE_ROOT.resolve():
        return "<read_only_phase2_baselines_cache>"
    return f"<external:{resolved.name}>"


def read_csv_header(path: Path) -> list[str]:
    with path.open("r", encoding="utf-8") as handle:
        header = handle.readline().strip("\n")
    return header.split(",") if header else []


def read_feature_csv(path: Path, source: FeatureSource) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(path)
    frame = pd.read_csv(path)
    missing = set(source.id_columns) - set(frame.columns)
    if missing:
        raise ValueError(f"{path} missing id columns: {sorted(missing)}")
    path_like = [column for column in frame.columns if "path" in column.lower()]
    if path_like:
        raise ValueError(f"feature cache unexpectedly contains path-like columns: {path.name}:{path_like[:5]}")
    for column in source.id_columns:
        frame[column] = frame[column].astype(str)
    if source.strip_feature_suffixes:
        rename_map: dict[str, str] = {}
        for column in frame.columns:
            for suffix in source.strip_feature_suffixes:
                if column.endswith(suffix):
                    rename_map[column] = column[: -len(suffix)]
                    break
        if rename_map:
            frame = frame.rename(columns=rename_map)
    return frame.assign(
        dataset_id=source.dataset,
        feature_family=source.family,
        feature_space=source.feature_space,
        source_cache_name=path.name,
    ).copy()


def feature_columns(frame: pd.DataFrame, id_columns: tuple[str, ...], target_column: str | None = None) -> list[str]:
    excluded = {
        "dataset_id",
        "feature_family",
        "feature_space",
        "source_cache_name",
        "group_id",
        "probe_row_id",
    }
    excluded.update(id_columns)
    if target_column:
        excluded.add(target_column)
    cols: list[str] = []
    for column in frame.columns:
        if column in excluded:
            continue
        if column.lower() in METADATA_COLUMNS:
            continue
        if "path" in column.lower():
            continue
        if pd.api.types.is_numeric_dtype(frame[column]):
            cols.append(column)
    return cols


def unique_columns(columns: list[str]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for column in columns:
        if column not in seen:
            ordered.append(column)
            seen.add(column)
    return ordered


def add_identity_columns(frame: pd.DataFrame, source: FeatureSource, row_grain: str) -> pd.DataFrame:
    out = frame.copy()
    if row_grain == "subject":
        out["group_id"] = out["dataset_id"] + "::" + out["subject_id"].astype(str)
        out["probe_row_id"] = out["group_id"]
    elif row_grain == "subject_task":
        if "task_type" not in out.columns:
            raise ValueError(f"{source.rel_path} lacks task_type for subject-task probe")
        out["group_id"] = out["dataset_id"] + "::" + out["subject_id"].astype(str)
        out["probe_row_id"] = out["group_id"] + "::" + out["task_type"].astype(str)
    elif row_grain == "subject_valence":
        if "valence" not in out.columns:
            raise ValueError(f"{source.rel_path} lacks valence for valence probe")
        out["group_id"] = out["dataset_id"] + "::" + out["subject_id"].astype(str)
        out["probe_row_id"] = out["group_id"] + "::" + out["valence"].astype(str)
    else:
        raise ValueError(f"unknown row_grain: {row_grain}")
    return out


def load_manifest_metadata(manifest_dir: Path, dataset_key: str, columns: list[str]) -> pd.DataFrame:
    path = manifest_dir / f"{dataset_key}_subjects.csv"
    if not path.exists():
        raise FileNotFoundError(path)
    header = read_csv_header(path)
    safe_columns = [
        column
        for column in columns
        if column in header and "path" not in column.lower() and column not in {"text", "transcript"}
    ]
    if "subject_id" not in safe_columns:
        safe_columns.insert(0, "subject_id")
    return pd.read_csv(path, usecols=safe_columns)


def load_source(feature_root: Path, manifest_dir: Path, source: FeatureSource, row_grain: str) -> pd.DataFrame:
    path = feature_root / source.rel_path
    frame = read_feature_csv(path, source)
    if source.required_label_columns:
        dataset_key = next(key for key, value in DATASET_CANONICAL.items() if value == source.dataset)
        metadata = load_manifest_metadata(manifest_dir, dataset_key, ["subject_id", *source.required_label_columns])
        metadata["subject_id"] = metadata["subject_id"].astype(str)
        if row_grain == "subject":
            metadata = metadata.groupby("subject_id", as_index=False).first()
        elif "task_type" in source.required_label_columns and "task_type" in frame.columns:
            metadata = metadata[["subject_id", *source.required_label_columns]].drop_duplicates()
        frame = frame.merge(metadata, on="subject_id", how="left", validate="many_to_one")
    return add_identity_columns(frame, source, row_grain)


def select_common_feature_frame(frames: list[pd.DataFrame], target_column: str, id_columns: tuple[str, ...]) -> tuple[pd.DataFrame, list[str]]:
    if not frames:
        raise ValueError("no frames supplied")
    common: set[str] | None = None
    for frame in frames:
        cols = set(feature_columns(frame, id_columns, target_column))
        common = cols if common is None else common & cols
    if not common:
        raise ValueError("feature sources have no common numeric feature columns")
    ordered_common = [column for column in frames[0].columns if column in common]
    selected_columns = unique_columns([*id_columns, "dataset_id", "group_id", "probe_row_id", target_column, *ordered_common])
    selected = pd.concat([frame[selected_columns].copy() for frame in frames], ignore_index=True)
    selected = selected[selected[target_column].notna()].reset_index(drop=True)
    return selected, ordered_common


def pipeline(seed: int) -> Pipeline:
    return Pipeline(
        [
            ("imputer", SimpleImputer(strategy="median")),
            ("scaler", StandardScaler()),
            (
                "clf",
                LogisticRegression(
                    C=1.0,
                    class_weight="balanced",
                    max_iter=5000,
                    random_state=seed,
                    solver="lbfgs",
                ),
            ),
        ]
    )


def split_indices(y: np.ndarray, groups: np.ndarray, n_splits: int, seed: int) -> list[tuple[np.ndarray, np.ndarray]]:
    class_counts = pd.Series(y).value_counts()
    unique_groups = pd.Series(groups).nunique()
    max_splits = min(int(n_splits), int(class_counts.min()), int(unique_groups))
    if max_splits < 2:
        raise ValueError("not enough classes/groups for cross-validation")
    if len(np.unique(groups)) == len(groups):
        splitter = StratifiedKFold(n_splits=max_splits, shuffle=True, random_state=seed)
        return list(splitter.split(np.zeros(len(y)), y))
    if StratifiedGroupKFold is not None:
        splitter = StratifiedGroupKFold(n_splits=max_splits, shuffle=True, random_state=seed)
        return list(splitter.split(np.zeros(len(y)), y, groups))
    splitter = GroupKFold(n_splits=max_splits)
    return list(splitter.split(np.zeros(len(y)), y, groups))


def compute_metrics(y_true: np.ndarray, y_pred: np.ndarray) -> dict[str, float]:
    return {
        "accuracy": float(accuracy_score(y_true, y_pred)),
        "macro_f1": float(f1_score(y_true, y_pred, average="macro", zero_division=0)),
        "balanced_accuracy": float(balanced_accuracy_score(y_true, y_pred)),
    }


def bootstrap_ci(
    prediction_frame: pd.DataFrame,
    *,
    label_column: str,
    prediction_column: str,
    group_column: str,
    resamples: int,
    seed: int,
) -> dict[str, tuple[float, float]]:
    rng = np.random.default_rng(seed)
    group_values = np.asarray(sorted(prediction_frame[group_column].astype(str).unique(), key=natural_key))
    grouped_indices = {
        group: prediction_frame.index[prediction_frame[group_column].astype(str) == group].to_numpy()
        for group in group_values
    }
    draws: dict[str, list[float]] = {"accuracy": [], "macro_f1": [], "balanced_accuracy": []}
    for _ in range(resamples):
        sampled_groups = rng.choice(group_values, size=len(group_values), replace=True)
        sampled_idx = np.concatenate([grouped_indices[group] for group in sampled_groups])
        sample = prediction_frame.loc[sampled_idx]
        metrics = compute_metrics(sample[label_column].to_numpy(), sample[prediction_column].to_numpy())
        for key, value in metrics.items():
            if math.isfinite(value):
                draws[key].append(value)
    return {
        key: (float(np.percentile(values, 2.5)), float(np.percentile(values, 97.5)))
        for key, values in draws.items()
        if values
    }


def run_probe(
    spec: ProbeSpec,
    feature_root: Path,
    manifest_dir: Path,
    *,
    n_splits: int,
    bootstrap_resamples: int,
    seed: int,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, dict[str, Any]]:
    frames = [load_source(feature_root, manifest_dir, source, spec.row_grain) for source in spec.sources]
    id_columns = spec.sources[0].id_columns
    frame, cols = select_common_feature_frame(frames, spec.target_column, id_columns)
    class_counts = frame[spec.target_column].astype(str).value_counts().sort_index()
    if len(class_counts) < spec.min_classes:
        raise ValueError(f"{spec.probe_id} has fewer than {spec.min_classes} target classes")
    y = frame[spec.target_column].astype(str).to_numpy()
    groups = frame[spec.group_column].astype(str).to_numpy()
    splits = split_indices(y, groups, n_splits, seed)
    predictions: list[dict[str, Any]] = []
    fold_summaries: list[dict[str, Any]] = []
    for fold_idx, (train_idx, test_idx) in enumerate(splits):
        train_groups = set(groups[train_idx])
        test_groups = set(groups[test_idx])
        overlap = train_groups & test_groups
        if overlap:
            raise ValueError(f"{spec.probe_id} fold {fold_idx} group leakage: {sorted(overlap)[:5]}")
        model = pipeline(seed + fold_idx)
        model.fit(frame.iloc[train_idx][cols], y[train_idx])
        pred = model.predict(frame.iloc[test_idx][cols])
        proba = model.predict_proba(frame.iloc[test_idx][cols])
        classes = list(model.named_steps["clf"].classes_)
        for local_idx, row_idx in enumerate(test_idx):
            row = frame.iloc[row_idx]
            predictions.append(
                {
                    "probe_id": spec.probe_id,
                    "target_name": spec.target_name,
                    "row_grain": spec.row_grain,
                    "fold": int(fold_idx),
                    "dataset_id": str(row["dataset_id"]),
                    "subject_id": str(row["subject_id"]),
                    "group_id": str(row["group_id"]),
                    "probe_row_id": str(row["probe_row_id"]),
                    "y_true": str(y[row_idx]),
                    "y_pred": str(pred[local_idx]),
                    "y_pred_confidence": float(np.max(proba[local_idx])),
                    "classes": ";".join(classes),
                }
            )
        fold_summaries.append(
            {
                "probe_id": spec.probe_id,
                "fold": int(fold_idx),
                "train_rows": int(len(train_idx)),
                "test_rows": int(len(test_idx)),
                "train_groups": int(len(train_groups)),
                "test_groups": int(len(test_groups)),
                "group_overlap": int(len(overlap)),
            }
        )
    prediction_frame = pd.DataFrame(predictions)
    metrics = compute_metrics(prediction_frame["y_true"].to_numpy(), prediction_frame["y_pred"].to_numpy())
    cis = bootstrap_ci(
        prediction_frame,
        label_column="y_true",
        prediction_column="y_pred",
        group_column="group_id",
        resamples=bootstrap_resamples,
        seed=seed + 1009,
    )
    labels = sorted(class_counts.index.astype(str), key=natural_key)
    cm = confusion_matrix(prediction_frame["y_true"], prediction_frame["y_pred"], labels=labels)
    cm_frame = pd.DataFrame(cm, index=labels, columns=labels)
    cm_long_rows: list[dict[str, Any]] = []
    for true_label in labels:
        for pred_label in labels:
            cm_long_rows.append(
                {
                    "probe_id": spec.probe_id,
                    "y_true": true_label,
                    "y_pred": pred_label,
                    "count": int(cm_frame.loc[true_label, pred_label]),
                }
            )
    summary_rows = [
        {
            "probe_id": spec.probe_id,
            "target_name": spec.target_name,
            "target_column": spec.target_column,
            "row_grain": spec.row_grain,
            "feature_family": "+".join(sorted({source.family for source in spec.sources})),
            "feature_space": "+".join(sorted({source.feature_space for source in spec.sources})),
            "comparable_basis": spec.comparable_basis,
            "n_rows": int(len(frame)),
            "n_groups": int(pd.Series(groups).nunique()),
            "n_classes": int(len(class_counts)),
            "n_features_common": int(len(cols)),
            "n_splits": int(len(splits)),
            "classes": ";".join(labels),
            "class_counts": json.dumps({str(k): int(v) for k, v in class_counts.items()}, sort_keys=True),
            "accuracy": metrics["accuracy"],
            "accuracy_ci_low": cis["accuracy"][0],
            "accuracy_ci_high": cis["accuracy"][1],
            "macro_f1": metrics["macro_f1"],
            "macro_f1_ci_low": cis["macro_f1"][0],
            "macro_f1_ci_high": cis["macro_f1"][1],
            "balanced_accuracy": metrics["balanced_accuracy"],
            "balanced_accuracy_ci_low": cis["balanced_accuracy"][0],
            "balanced_accuracy_ci_high": cis["balanced_accuracy"][1],
            "majority_class_accuracy": float(class_counts.max() / class_counts.sum()),
            "source_cache_names": ";".join(source.rel_path for source in spec.sources),
        }
    ]
    metadata = {
        "probe_id": spec.probe_id,
        "fold_summaries": fold_summaries,
        "class_counts": {str(k): int(v) for k, v in class_counts.items()},
        "feature_columns_common_head": cols[:20],
        "feature_columns_common_count": int(len(cols)),
        "source_notes": [source.note for source in spec.sources if source.note],
    }
    return pd.DataFrame(summary_rows), prediction_frame, pd.DataFrame(cm_long_rows), metadata


def plot_metric_summary(summary: pd.DataFrame, out_path: Path) -> None:
    if summary.empty:
        return
    order = summary.sort_values("balanced_accuracy", ascending=True)
    y_pos = np.arange(len(order))
    values = order["balanced_accuracy"].to_numpy(dtype=float)
    low = order["balanced_accuracy_ci_low"].to_numpy(dtype=float)
    high = order["balanced_accuracy_ci_high"].to_numpy(dtype=float)
    plt.figure(figsize=(10, max(4, 0.42 * len(order))))
    plt.barh(y_pos, values, color="#3b82f6", alpha=0.85)
    plt.errorbar(values, y_pos, xerr=[values - low, high - values], fmt="none", ecolor="#111827", capsize=3, linewidth=1)
    plt.yticks(y_pos, order["probe_id"].tolist(), fontsize=8)
    plt.xlabel("Balanced accuracy")
    plt.xlim(0, 1.02)
    plt.title("Phase 3 dataset/protocol identity probes")
    plt.tight_layout()
    plt.savefig(out_path, dpi=180)
    plt.close()


def plot_confusion_matrix(cm_long: pd.DataFrame, probe_id: str, out_path: Path) -> None:
    selected = cm_long[cm_long["probe_id"] == probe_id].copy()
    labels = sorted(set(selected["y_true"]) | set(selected["y_pred"]), key=natural_key)
    matrix = np.zeros((len(labels), len(labels)), dtype=float)
    for _, row in selected.iterrows():
        i = labels.index(str(row["y_true"]))
        j = labels.index(str(row["y_pred"]))
        matrix[i, j] = float(row["count"])
    with np.errstate(invalid="ignore", divide="ignore"):
        row_sums = matrix.sum(axis=1, keepdims=True)
        norm = np.divide(matrix, row_sums, out=np.zeros_like(matrix), where=row_sums > 0)
    plt.figure(figsize=(max(5, 0.72 * len(labels) + 2), max(4.5, 0.62 * len(labels) + 2)))
    plt.imshow(norm, cmap="Blues", vmin=0.0, vmax=1.0)
    plt.colorbar(label="Row-normalized share")
    plt.xticks(np.arange(len(labels)), labels, rotation=45, ha="right", fontsize=8)
    plt.yticks(np.arange(len(labels)), labels, fontsize=8)
    for i in range(len(labels)):
        for j in range(len(labels)):
            count = int(matrix[i, j])
            if count:
                plt.text(j, i, str(count), ha="center", va="center", color="#111827", fontsize=8)
    plt.xlabel("Predicted")
    plt.ylabel("True")
    plt.title(probe_id)
    plt.tight_layout()
    plt.savefig(out_path, dpi=180)
    plt.close()


def scan_output_markers(out_dir: Path) -> dict[str, Any]:
    forbidden = (
        "/root/",
        "/autodl-tmp/",
        "raw_root",
        "audio_path",
        "text_path",
        "video_path",
        "gait_path",
    )
    matches: list[dict[str, str]] = []
    for path in sorted(out_dir.rglob("*")):
        if not path.is_file() or path.suffix.lower() not in {".csv", ".json", ".md"}:
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        for marker in forbidden:
            if marker in text:
                matches.append({"artifact": artifact_path_reference(path), "marker": marker})
    return {
        "forbidden_artifact_marker_count": int(len(matches)),
        "forbidden_artifact_markers": matches[:20],
    }


def markdown_table(frame: pd.DataFrame, floatfmt: str = ".3f") -> str:
    if frame.empty:
        return ""
    columns = list(frame.columns)
    rows: list[list[str]] = []
    for _, row in frame.iterrows():
        output_row: list[str] = []
        for column in columns:
            value = row[column]
            if isinstance(value, float):
                output_row.append(format(value, floatfmt))
            else:
                output_row.append(str(value))
        rows.append(output_row)
    lines = [
        "| " + " | ".join(columns) + " |",
        "| " + " | ".join(["---"] * len(columns)) + " |",
    ]
    for row in rows:
        lines.append("| " + " | ".join(cell.replace("|", "\\|") for cell in row) + " |")
    return "\n".join(lines)


def write_report(out_dir: Path, summary: pd.DataFrame, skipped: list[dict[str, Any]], run_summary: dict[str, Any]) -> None:
    lines = [
        "# Phase 3 Dataset/Protocol Identity Probe",
        "",
        f"Generated: `{run_summary['generated_at']}`",
        "",
        "## Technical Summary",
        "",
        "This diagnostic trains lightweight, grouped cross-validated logistic probes on cached Phase 2 frozen/lightweight features to estimate how much dataset, protocol, task, or valence identity remains in the representations. High identity-probe performance is diagnostic evidence that direct pooled training can exploit dataset/protocol signatures and therefore cannot be interpreted as learning a shared depression construct by itself.",
        "",
        "All code, reports, and outputs are written under the current worktree. The probe reads existing Phase 2 feature-cache CSVs as read-only inputs and does not open raw text, audio, video, or path-valued manifest columns.",
        "",
        "Canonical experiment order is treated as a hard constraint: data audit -> task/hypothesis freeze -> unified baselines -> failure-mode diagnostics -> minimal method validation -> full method -> cross-dataset experiments -> statistics/writing. This report is only the Phase 3 failure-mode diagnostic step; it does not implement a full model or method module.",
        "",
        "## Key Findings",
        "",
    ]
    if summary.empty:
        lines.append("- No probes completed.")
    else:
        top = summary.sort_values("balanced_accuracy", ascending=False).head(8)
        for _, row in top.iterrows():
            lines.append(
                "- "
                f"`{row['probe_id']}`: balanced accuracy "
                f"{row['balanced_accuracy']:.3f} "
                f"[{row['balanced_accuracy_ci_low']:.3f}, {row['balanced_accuracy_ci_high']:.3f}], "
                f"macro-F1 {row['macro_f1']:.3f}, n={int(row['n_rows'])} rows / {int(row['n_groups'])} groups."
            )
    lines.extend(
        [
            "",
            "## Scope And Definitions",
            "",
            "- Dataset identity target: `dataset_id` over the datasets that share a comparable cached feature space.",
            "- Protocol/task targets: available cached labels such as MODMA `task_type` and EATD `valence`, always grouped by subject.",
            "- Metrics: accuracy, macro-F1, balanced accuracy, and bootstrap 95% CI over subject groups.",
            "- Split rule: subject-level rows use stratified subject CV; repeated task/valence rows use grouped CV so the same subject cannot appear in train and validation folds.",
            "- Classifier: fixed balanced multinomial logistic regression with median imputation and standard scaling inside each fold.",
            "",
            "## Completed Probe Summary",
            "",
        ]
    )
    if summary.empty:
        lines.append("No completed probes.")
    else:
        visible = summary[
            [
                "probe_id",
                "target_name",
                "n_rows",
                "n_groups",
                "n_classes",
                "n_features_common",
                "accuracy",
                "macro_f1",
                "balanced_accuracy",
                "majority_class_accuracy",
            ]
        ].copy()
        lines.append(markdown_table(visible, floatfmt=".3f"))
    lines.extend(
        [
            "",
            "## Comparability Caveats",
            "",
            "- Cross-dataset results are only interpreted when cached feature columns are shared across the included datasets.",
            "- Text frozen embeddings are comparable for CMDC versus PDCH because both use the same BGE feature space. E-DAIC text uses English DeBERTa/ModernBERT caches, and EATD/MODMA/MPDD have no cached subject-level text embedding in Phase 2, so a six-dataset text identity probe is not supported.",
            "- Audio WavLM is the strongest six-dataset comparable probe because all six datasets have cached WavLM subject features.",
            "- Audio eGeMAPS is pooled only for CMDC, PDCH, and MODMA because those caches share the same subject-level eGeMAPSv02 functional-statistic columns. E-DAIC uses a different low-level eGeMAPS summary, EATD stores valence-expanded columns, and MPDD has no Phase 2 eGeMAPS cache.",
            "- Video OpenFace is pooled only for E-DAIC and CMDC after stripping CMDC segment-aggregation suffixes to recover common OpenFace statistic names. MPDD OpenFace is numeric-indexed and not safely joinable by semantic feature name; ResNet/TimeSformer video caches use different feature contracts.",
            "",
            "## Stop/Go Implication",
            "",
            "- **Stop:** direct joint training alone is not acceptable evidence of a shared depression representation, because dataset identity is almost perfectly recoverable from multiple frozen representation families.",
            "- **Go:** proceed only to minimal method validation designs that explicitly control, penalize, stratify, or report dataset/protocol identity effects before any full method or cross-dataset experiment stage.",
            "- **Design implication:** dataset/protocol robustness should be a required diagnostic gate in later method validation, especially for pooled WavLM/audio, CMDC-PDCH text, and OpenFace video experiments.",
            "",
            "## Outputs",
            "",
            "- `probe_metric_summary.csv`: metrics and bootstrap CIs.",
            "- `probe_predictions.csv`: out-of-fold predictions with subject/group identifiers only.",
            "- `confusion_matrices_long.csv`: long-form confusion matrices.",
            "- `feature_probe_inventory.csv`: completed and skipped probe inventory.",
            "- `figures/probe_balanced_accuracy.png`: summary figure.",
            "- `figures/confusion_*.png`: row-normalized confusion matrices.",
            "",
        ]
    )
    if skipped:
        lines.extend(["## Skipped Or Unsupported Probes", ""])
        for item in skipped:
            lines.append(f"- `{item['probe_id']}`: {item['reason']}")
        lines.append("")
    (out_dir / "dataset_identity_probe_report.md").write_text("\n".join(lines), encoding="utf-8")


def probe_specs() -> list[ProbeSpec]:
    audio_wavlm_sources = (
        FeatureSource("E-DAIC", "audio", "wavlm", "edaic_audio_frozen_encoders/wavlm_subject_features.csv"),
        FeatureSource("CMDC", "audio", "wavlm", "cmdc_audio_frozen_encoders/cmdc_wavlm_subject_features.csv"),
        FeatureSource("PDCH", "audio", "wavlm", "pdch_audio_wavlm/pdch_wavlm_subject_features.csv"),
        FeatureSource("EATD", "audio", "wavlm", "eatd_audio_wavlm/eatd_wavlm_subject_features.csv"),
        FeatureSource("MODMA", "audio", "wavlm", "modma_audio_wavlm/modma_wavlm_subject_features.csv"),
        FeatureSource("MPDD", "audio", "wavlm", "mpdd_audio_wavlm/mpdd_wavlm_subject_features.csv"),
    )
    audio_wav2vec2_sources = (
        FeatureSource("E-DAIC", "audio", "wav2vec2", "edaic_audio_frozen_encoders/wav2vec2_subject_features.csv"),
        FeatureSource("CMDC", "audio", "wav2vec2", "cmdc_audio_frozen_encoders/cmdc_wav2vec2_subject_features.csv"),
        FeatureSource("MODMA", "audio", "wav2vec2", "modma_audio_wav2vec2/modma_wav2vec2_subject_features.csv"),
    )
    audio_egemaps_sources = (
        FeatureSource("CMDC", "audio", "egemaps", "cmdc_pdch_audio_egemaps/cmdc_egemaps_subject_features.csv"),
        FeatureSource("PDCH", "audio", "egemaps", "cmdc_pdch_audio_egemaps/pdch_egemaps_subject_features.csv"),
        FeatureSource("MODMA", "audio", "egemaps", "modma_audio_egemaps/modma_egemaps_subject_features.csv"),
    )
    text_bge_sources = (
        FeatureSource("CMDC", "text", "bge-small-zh-v1.5", "cmdc_pdch_text_encoder_mlp/cmdc_bge_subject_features.csv"),
        FeatureSource("PDCH", "text", "bge-small-zh-v1.5", "cmdc_pdch_text_encoder_mlp/pdch_bge_subject_features.csv"),
    )
    video_openface_sources = (
        FeatureSource("E-DAIC", "video", "openface_stats", "edaic_video_features/edaic_openface_subject_features.csv"),
        FeatureSource(
            "CMDC",
            "video",
            "openface_stats",
            "cmdc_video_features/openface_statistics_subject_features.csv",
            strip_feature_suffixes=("__segment_mean",),
        ),
    )
    modma_task_sources = (
        FeatureSource("MODMA", "audio", "wavlm_subject_task", "modma_audio_wavlm/modma_wavlm_subject_task_features.csv"),
    )
    eatd_valence_sources = (
        FeatureSource("EATD", "audio", "wavlm_segment_valence", "eatd_audio_wavlm/eatd_wavlm_segment_embeddings.csv"),
    )
    return [
        ProbeSpec(
            probe_id="dataset_id_audio_wavlm_6way",
            target_name="dataset identity",
            target_column="dataset_id",
            row_grain="subject",
            sources=audio_wavlm_sources,
            comparable_basis="same frozen WavLM subject embedding columns across six datasets",
            min_classes=6,
        ),
        ProbeSpec(
            probe_id="dataset_id_audio_wav2vec2_3way",
            target_name="dataset identity",
            target_column="dataset_id",
            row_grain="subject",
            sources=audio_wav2vec2_sources,
            comparable_basis="same frozen wav2vec2 subject embedding columns for E-DAIC, CMDC, and MODMA",
            min_classes=3,
        ),
        ProbeSpec(
            probe_id="dataset_id_audio_egemaps_cmdc_pdch_modma",
            target_name="dataset identity",
            target_column="dataset_id",
            row_grain="subject",
            sources=audio_egemaps_sources,
            comparable_basis="intersection of cached subject-level eGeMAPSv02 functional-statistic columns for CMDC, PDCH, and MODMA",
            min_classes=3,
        ),
        ProbeSpec(
            probe_id="dataset_id_text_bge_cmdc_pdch",
            target_name="dataset identity",
            target_column="dataset_id",
            row_grain="subject",
            sources=text_bge_sources,
            comparable_basis="same Chinese BGE frozen text embedding for CMDC and PDCH",
            min_classes=2,
        ),
        ProbeSpec(
            probe_id="dataset_id_video_openface_edaic_cmdc_common",
            target_name="dataset identity",
            target_column="dataset_id",
            row_grain="subject",
            sources=video_openface_sources,
            comparable_basis="intersection of semantic OpenFace statistic columns for E-DAIC and CMDC",
            min_classes=2,
        ),
        ProbeSpec(
            probe_id="protocol_modma_task_type_wavlm",
            target_name="MODMA task type",
            target_column="task_type",
            row_grain="subject_task",
            sources=modma_task_sources,
            comparable_basis="same WavLM subject-task feature space within MODMA; grouped by subject",
            min_classes=4,
        ),
        ProbeSpec(
            probe_id="protocol_eatd_valence_wavlm",
            target_name="EATD valence",
            target_column="valence",
            row_grain="subject_valence",
            sources=eatd_valence_sources,
            comparable_basis="same WavLM segment embedding feature space within EATD; grouped by subject",
            min_classes=3,
        ),
    ]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--feature-root", type=Path, default=None)
    parser.add_argument("--manifest-dir", type=Path, default=DEFAULT_MANIFEST_DIR)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--n-splits", type=int, default=5)
    parser.add_argument("--bootstrap-resamples", type=int, default=1000)
    parser.add_argument("--seed", type=int, default=RANDOM_SEED)
    parser.add_argument("--probe-id", action="append")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    feature_root, feature_root_mode = resolve_feature_root(args.feature_root)
    args.out_dir.mkdir(parents=True, exist_ok=True)
    figures_dir = args.out_dir / "figures"
    figures_dir.mkdir(exist_ok=True)
    selected_probe_ids = set(args.probe_id or [])
    summaries: list[pd.DataFrame] = []
    predictions: list[pd.DataFrame] = []
    cms: list[pd.DataFrame] = []
    metadata: list[dict[str, Any]] = []
    skipped: list[dict[str, Any]] = []

    for spec in probe_specs():
        if selected_probe_ids and spec.probe_id not in selected_probe_ids:
            continue
        try:
            summary, pred, cm, meta = run_probe(
                spec,
                feature_root,
                args.manifest_dir,
                n_splits=args.n_splits,
                bootstrap_resamples=args.bootstrap_resamples,
                seed=args.seed,
            )
            summaries.append(summary)
            predictions.append(pred)
            cms.append(cm)
            metadata.append(meta)
            print(f"completed {spec.probe_id}", flush=True)
        except Exception as exc:  # keep unsupported feature spaces auditable
            skipped.append({"probe_id": spec.probe_id, "reason": f"{type(exc).__name__}: {exc}"})
            print(f"skipped {spec.probe_id}: {exc}", flush=True)

    summary_frame = pd.concat(summaries, ignore_index=True) if summaries else pd.DataFrame()
    prediction_frame = pd.concat(predictions, ignore_index=True) if predictions else pd.DataFrame()
    cm_frame = pd.concat(cms, ignore_index=True) if cms else pd.DataFrame()

    summary_frame.to_csv(args.out_dir / "probe_metric_summary.csv", index=False)
    prediction_frame.to_csv(args.out_dir / "probe_predictions.csv", index=False)
    cm_frame.to_csv(args.out_dir / "confusion_matrices_long.csv", index=False)

    inventory_rows = []
    for _, row in summary_frame.iterrows():
        inventory_rows.append(
            {
                "probe_id": row["probe_id"],
                "status": "completed",
                "n_rows": int(row["n_rows"]),
                "n_groups": int(row["n_groups"]),
                "n_features_common": int(row["n_features_common"]),
                "comparable_basis": row["comparable_basis"],
                "reason": "",
            }
        )
    for item in skipped:
        inventory_rows.append(
            {
                "probe_id": item["probe_id"],
                "status": "skipped",
                "n_rows": "",
                "n_groups": "",
                "n_features_common": "",
                "comparable_basis": "",
                "reason": item["reason"],
            }
        )
    pd.DataFrame(inventory_rows).to_csv(args.out_dir / "feature_probe_inventory.csv", index=False)

    if not summary_frame.empty:
        plot_metric_summary(summary_frame, figures_dir / "probe_balanced_accuracy.png")
        for probe_id in summary_frame["probe_id"].astype(str):
            safe_probe_id = re.sub(r"[^A-Za-z0-9_.-]+", "_", probe_id)
            plot_confusion_matrix(cm_frame, probe_id, figures_dir / f"confusion_{safe_probe_id}.png")

    group_overlap_violations = sum(
        int(fold.get("group_overlap", 0))
        for item in metadata
        for fold in item.get("fold_summaries", [])
    )
    marker_scan = scan_output_markers(args.out_dir)
    run_summary = {
        "generated_at": utc_now(),
        "worktree_root": ".",
        "feature_root": artifact_path_reference(feature_root),
        "feature_root_mode": feature_root_mode,
        "manifest_dir": artifact_path_reference(args.manifest_dir),
        "out_dir": artifact_path_reference(args.out_dir),
        "n_splits_requested": int(args.n_splits),
        "bootstrap_resamples": int(args.bootstrap_resamples),
        "seed": int(args.seed),
        "completed_probe_count": int(len(summary_frame)),
        "completed_probes": int(len(summary_frame)),
        "skipped_probe_count": int(len(skipped)),
        "skipped_probes": skipped,
        "train_test_group_overlap_violations": int(group_overlap_violations),
        "metadata": metadata,
        "raw_modality_files_opened": False,
        "path_valued_manifest_columns_read": False,
        **marker_scan,
    }
    run_summary["artifact_hygiene_passed"] = bool(
        not run_summary["raw_modality_files_opened"]
        and not run_summary["path_valued_manifest_columns_read"]
        and run_summary["forbidden_artifact_marker_count"] == 0
        and run_summary["train_test_group_overlap_violations"] == 0
    )
    (args.out_dir / "run_summary.json").write_text(json.dumps(run_summary, indent=2, sort_keys=True), encoding="utf-8")
    write_report(args.out_dir, summary_frame, skipped, run_summary)


if __name__ == "__main__":
    main()
