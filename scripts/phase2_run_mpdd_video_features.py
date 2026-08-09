#!/usr/bin/env python3
"""Run Phase 2 MPDD video feature baselines.

The runner reads manifest-resolved MPDD video `.npy` feature sequences, pools
all event/frame rows to one subject-level representation, and evaluates planned
ordinal severity rows with repeated subject-level out-of-fold predictions. It
ignores unlabeled MPDD test rows and writes no raw video, source paths, or
frame-level features.
"""

from __future__ import annotations

import argparse
import json
import os
import re
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

import numpy as np
import pandas as pd
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.neural_network import MLPClassifier
from sklearn.model_selection import StratifiedKFold
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from phase2_metrics import metric_records


ROOT = Path("/root/autodl-tmp")
MANIFEST_PATH = ROOT / "datasets" / "manifests" / "mpdd_avg_2026_subjects.csv"
DEFAULT_OUT_DIR = ROOT / "analysis" / "phase2_baselines" / "mpdd_video_features"
DEFAULT_OPENFACE_OUT_DIR = ROOT / "analysis" / "phase2_baselines" / "mpdd_video_openface"
DATASET_DISPLAY = "MPDD-AVG-2026"
SEEDS = [0, 1, 2, 3, 4]
FIXED_LOGISTIC_C = 1.0
FIXED_MLP_ALPHA = 0.01


@dataclass(frozen=True)
class BaselineSpec:
    run_id: str
    modality: str
    task: str
    task_type: str
    target: str
    model: str
    manifest_feature_type: str
    feature_prefix: str
    classifier: str
    cache_name: str
    predictions_name: str
    report_name: str
    summary_name: str


RESNET_SPEC = BaselineSpec(
    run_id="mpdd_video_severity_temporal_pooling",
    modality="Video",
    task="ordinal severity prediction",
    task_type="ordinal_prediction",
    target="severity_label",
    model="official visual features + temporal pooling",
    manifest_feature_type="resnet_npy",
    feature_prefix="resnet",
    classifier="logistic",
    cache_name="mpdd_resnet_video_subject_features.csv",
    predictions_name="mpdd_video_features_predictions.csv",
    report_name="mpdd_video_features_report.md",
    summary_name="mpdd_video_features_run_summary.json",
)

OPENFACE_SPEC = BaselineSpec(
    run_id="mpdd_video_severity_openface_mlp",
    modality="Video",
    task="ordinal severity prediction",
    task_type="ordinal_prediction",
    target="severity_label",
    model="OpenFace statistics + MLP",
    manifest_feature_type="openface",
    feature_prefix="openface",
    classifier="mlp",
    cache_name="mpdd_openface_video_subject_features.csv",
    predictions_name="mpdd_openface_video_predictions.csv",
    report_name="mpdd_openface_video_report.md",
    summary_name="mpdd_openface_video_run_summary.json",
)

SPECS = {spec.run_id: spec for spec in [RESNET_SPEC, OPENFACE_SPEC]}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def natural_key(value: Any) -> list[Any]:
    return [int(part) if part.isdigit() else part for part in re.split(r"(\d+)", str(value))]


def read_manifest(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"manifest missing: {path}")
    return pd.read_csv(path)


def labeled_subject_rows(manifest_path: Path, spec: BaselineSpec) -> pd.DataFrame:
    manifest = read_manifest(manifest_path)
    required = {
        "subject_id",
        "video_path",
        "video_feature_type",
        "phq9_total",
        "severity_label",
        "binary_label",
        "age",
        "official_split",
        "file_valid",
    }
    missing = required - set(manifest.columns)
    if missing:
        raise ValueError(f"MPDD manifest missing columns: {', '.join(sorted(missing))}")
    rows = manifest[
        manifest["file_valid"].fillna(False).astype(bool)
        & manifest["official_split"].eq("train")
        & manifest["video_path"].notna()
        & manifest["video_feature_type"].astype(str).eq(spec.manifest_feature_type)
        & manifest["phq9_total"].notna()
        & manifest["severity_label"].notna()
        & manifest["binary_label"].notna()
    ].copy()
    if rows.empty:
        raise ValueError(f"no labeled MPDD train subjects with {spec.manifest_feature_type} video features")

    subjects: list[dict[str, Any]] = []
    for subject_id, group in rows.groupby("subject_id", sort=False):
        phq_values = group["phq9_total"].dropna().unique()
        severity_values = group["severity_label"].dropna().unique()
        binary_values = group["binary_label"].dropna().unique()
        age_values = group["age"].dropna().astype(str).unique()
        if len(phq_values) != 1 or len(severity_values) != 1 or len(binary_values) != 1:
            raise ValueError(f"{subject_id} has inconsistent MPDD labels")
        video_paths = group["video_path"].dropna().astype(str).unique()
        if len(video_paths) < 1:
            raise ValueError(f"{subject_id} has no video path")
        subjects.append(
            {
                "subject_id": str(subject_id),
                "age_group": str(age_values[0]) if len(age_values) else "",
                "phq9_total": float(phq_values[0]),
                "severity_label": int(severity_values[0]),
                "binary_label": int(binary_values[0]),
                "video_path": str(video_paths[0]),
            }
        )
    return (
        pd.DataFrame(subjects)
        .sort_values("subject_id", key=lambda series: series.map(lambda item: tuple(natural_key(item))))
        .reset_index(drop=True)
    )


def subject_event_paths(path_value: Any) -> list[Path]:
    first_path = Path(str(path_value))
    if not first_path.exists():
        raise FileNotFoundError(f"manifest video feature path missing: {first_path}")
    directory = first_path if first_path.is_dir() else first_path.parent
    if directory.name.lower().startswith("event_") and directory.parent.exists():
        directory = directory.parent
    paths = sorted(directory.rglob("*.npy"), key=lambda path: natural_key(str(path.relative_to(directory))))
    if not paths:
        raise FileNotFoundError(f"no .npy video features in {directory}")
    return paths


def summarize_subject_events(paths: list[Path], feature_prefix: str) -> tuple[dict[str, float], dict[str, Any]]:
    total_frames = 0
    feature_dim: int | None = None
    sums: np.ndarray | None = None
    sums_sq: np.ndarray | None = None
    counts: np.ndarray | None = None
    nonfinite_count = 0
    event_shapes: list[tuple[int, int]] = []

    for path in paths:
        arr = np.load(path, mmap_mode="r")
        if not np.issubdtype(arr.dtype, np.number):
            raise ValueError(f"non-numeric video feature array: {path}")
        values = np.asarray(arr, dtype=np.float64)
        if values.ndim == 1:
            values = values.reshape(1, -1)
        elif values.ndim > 2:
            values = values.reshape(-1, values.shape[-1])
        if values.ndim != 2:
            raise ValueError(f"expected 2D video feature array, got {values.shape}: {path}")
        if values.shape[0] <= 0 or values.shape[1] <= 0:
            raise ValueError(f"empty video feature array: {path}")
        if feature_dim is None:
            feature_dim = int(values.shape[1])
            sums = np.zeros(feature_dim, dtype=np.float64)
            sums_sq = np.zeros(feature_dim, dtype=np.float64)
            counts = np.zeros(feature_dim, dtype=np.float64)
        elif values.shape[1] != feature_dim:
            raise ValueError(f"video feature dimension mismatch in {path}: {values.shape[1]} vs {feature_dim}")

        finite_mask = np.isfinite(values)
        nonfinite_count += int(values.size - int(np.sum(finite_mask)))
        safe_values = np.where(finite_mask, values, 0.0)
        assert sums is not None and sums_sq is not None and counts is not None
        sums += np.sum(safe_values, axis=0)
        sums_sq += np.sum(safe_values * safe_values, axis=0)
        counts += np.sum(finite_mask, axis=0)
        total_frames += int(values.shape[0])
        event_shapes.append((int(values.shape[0]), int(values.shape[1])))

    if feature_dim is None or sums is None or sums_sq is None or counts is None:
        raise RuntimeError("no MPDD video events were summarized")
    with np.errstate(invalid="ignore", divide="ignore"):
        mean = sums / counts
        variance = (sums_sq / counts) - (mean * mean)
    variance = np.where(np.isfinite(variance), np.maximum(variance, 0.0), np.nan)
    std = np.sqrt(variance)
    feature_values: dict[str, float] = {}
    for idx, value in enumerate(mean):
        feature_values[f"{feature_prefix}_{idx:04d}__mean"] = float(value) if np.isfinite(value) else np.nan
    for idx, value in enumerate(std):
        feature_values[f"{feature_prefix}_{idx:04d}__std"] = float(value) if np.isfinite(value) else np.nan
    metadata = {
        "video_event_count": int(len(paths)),
        "video_frame_count": int(total_frames),
        "video_feature_dim": int(feature_dim),
        "nonfinite_value_count": int(nonfinite_count),
        "event_frame_count_min": int(min(shape[0] for shape in event_shapes)),
        "event_frame_count_max": int(max(shape[0] for shape in event_shapes)),
    }
    return feature_values, metadata


def save_subject_cache(path: Path, rows: list[dict[str, Any]]) -> None:
    frame = pd.DataFrame(rows)
    if not frame.empty:
        frame = frame.sort_values("subject_id", key=lambda series: series.map(lambda item: tuple(natural_key(item))))
    frame.to_csv(path, index=False)


def load_or_extract_subject_features(
    subjects: pd.DataFrame,
    out_dir: Path,
    force: bool,
    spec: BaselineSpec,
) -> tuple[pd.DataFrame, list[str], dict[str, Any]]:
    cache_path = out_dir / spec.cache_name
    required_subjects = set(subjects["subject_id"].astype(str))
    feature_rows: list[dict[str, Any]] = []
    cached_subjects: set[str] = set()
    if cache_path.exists() and not force:
        cached = pd.read_csv(cache_path)
        if "subject_id" in cached.columns:
            cached["subject_id"] = cached["subject_id"].astype(str)
            cached_subjects = set(cached["subject_id"])
            feature_rows = cached[cached["subject_id"].isin(required_subjects)].to_dict("records")
            if required_subjects.issubset(cached_subjects):
                print(f"Using cached MPDD {spec.feature_prefix} video subject features", flush=True)
                selected = cached[cached["subject_id"].isin(required_subjects)].copy()
                feature_columns = [column for column in selected.columns if column.startswith(f"{spec.feature_prefix}_")]
                return selected.sort_values("subject_id", key=lambda series: series.map(lambda item: tuple(natural_key(item)))).reset_index(drop=True), feature_columns, {
                    "cache_path": str(cache_path),
                    "cached_subject_rows": int(len(selected)),
                    "new_subject_rows": 0,
                }

    missing = subjects[~subjects["subject_id"].astype(str).isin(cached_subjects)].reset_index(drop=True)
    print(f"Extracting MPDD {spec.feature_prefix} video features: {len(missing)} missing / {len(subjects)} subjects", flush=True)
    for idx, row in missing.iterrows():
        paths = subject_event_paths(row["video_path"])
        values, meta = summarize_subject_events(paths, spec.feature_prefix)
        feature_rows.append(
            {
                "subject_id": str(row["subject_id"]),
                "age_group": str(row["age_group"]),
                **meta,
                **values,
            }
        )
        if (idx + 1) == 1 or (idx + 1) % 25 == 0 or (idx + 1) == len(missing):
            print(f"  [mpdd-video:{spec.feature_prefix}] {idx + 1}/{len(missing)} subject={row['subject_id']}", flush=True)
        if (idx + 1) % 25 == 0:
            save_subject_cache(cache_path, feature_rows)
    save_subject_cache(cache_path, feature_rows)

    features = pd.DataFrame(feature_rows)
    features["subject_id"] = features["subject_id"].astype(str)
    observed_subjects = set(features["subject_id"])
    missing_subjects = sorted(required_subjects - observed_subjects, key=natural_key)
    if missing_subjects:
        raise ValueError(f"missing video subject feature rows: {missing_subjects[:10]}")
    selected = features[features["subject_id"].isin(required_subjects)].copy()
    feature_columns = [column for column in selected.columns if column.startswith(f"{spec.feature_prefix}_")]
    if not feature_columns:
        raise RuntimeError(f"no {spec.feature_prefix} video feature columns were extracted")
    return selected.sort_values("subject_id", key=lambda series: series.map(lambda item: tuple(natural_key(item)))).reset_index(drop=True), feature_columns, {
        "cache_path": str(cache_path),
        "cached_subject_rows": int(len(feature_rows) - len(missing)),
        "new_subject_rows": int(len(missing)),
    }


def build_subject_table(subjects: pd.DataFrame, features: pd.DataFrame, spec: BaselineSpec) -> tuple[pd.DataFrame, list[str]]:
    feature_columns = [column for column in features.columns if column.startswith(f"{spec.feature_prefix}_")]
    metadata_columns = [
        "subject_id",
        "age_group",
        "video_event_count",
        "video_frame_count",
        "video_feature_dim",
        "nonfinite_value_count",
        "event_frame_count_min",
        "event_frame_count_max",
    ]
    table = subjects.drop(columns=["video_path"]).merge(
        features[metadata_columns + feature_columns],
        on=["subject_id", "age_group"],
        how="inner",
    )
    if len(table) != len(subjects):
        raise ValueError(f"video feature merge produced {len(table)} rows for {len(subjects)} subjects")
    return table.sort_values("subject_id", key=lambda series: series.map(lambda item: tuple(natural_key(item)))).reset_index(drop=True), feature_columns


def classifier_pipeline(seed: int, spec: BaselineSpec) -> Pipeline:
    if spec.classifier == "mlp":
        classifier = MLPClassifier(
            hidden_layer_sizes=(64,),
            alpha=FIXED_MLP_ALPHA,
            batch_size="auto",
            early_stopping=False,
            learning_rate_init=1e-3,
            max_iter=1000,
            random_state=seed,
        )
    else:
        classifier = LogisticRegression(
            C=FIXED_LOGISTIC_C,
            class_weight="balanced",
            max_iter=1000,
            random_state=seed,
            solver="lbfgs",
        )
    return Pipeline(
        [
            ("imputer", SimpleImputer(strategy="median")),
            ("scaler", StandardScaler()),
            ("classifier", classifier),
        ]
    )


def probability_matrix(model: Pipeline, values: pd.DataFrame, class_labels: list[int]) -> np.ndarray:
    raw = model.predict_proba(values)
    probabilities = np.zeros((len(values), max(class_labels) + 1), dtype=np.float64)
    local_classes = [int(value) for value in model.named_steps["classifier"].classes_]
    for local_idx, class_value in enumerate(local_classes):
        probabilities[:, class_value] = raw[:, local_idx]
    return probabilities


def prediction_meta(seed: int, fold: int, row: pd.Series, spec: BaselineSpec) -> dict[str, Any]:
    return {
        "run_id": spec.run_id,
        "dataset": DATASET_DISPLAY,
        "modality": spec.modality,
        "task": spec.task,
        "model": spec.model,
        "seed": int(seed),
        "fold": int(fold),
        "task_type": spec.task_type,
        "subject_id": str(row["subject_id"]),
        "split": "train_oof",
        "age_group": str(row["age_group"]),
        "video_event_count": int(row["video_event_count"]),
        "video_frame_count": int(row["video_frame_count"]),
    }


def run_oof(table: pd.DataFrame, feature_columns: list[str], spec: BaselineSpec) -> tuple[pd.DataFrame, list[dict[str, Any]]]:
    labels = table["severity_label"].to_numpy(dtype=np.int64)
    class_labels = sorted(int(value) for value in np.unique(labels))
    predictions: list[dict[str, Any]] = []
    fold_summaries: list[dict[str, Any]] = []
    for seed in SEEDS:
        folds = StratifiedKFold(n_splits=5, shuffle=True, random_state=seed)
        for fold, (train_idx, heldout_idx) in enumerate(folds.split(table, labels), start=1):
            train = table.iloc[train_idx].reset_index(drop=True)
            heldout = table.iloc[heldout_idx].reset_index(drop=True)
            model = classifier_pipeline(seed + fold, spec)
            model.fit(train[feature_columns], train["severity_label"].astype(int))
            y_pred = model.predict(heldout[feature_columns]).astype(int)
            probabilities = probability_matrix(model, heldout[feature_columns], class_labels)
            for idx, row in heldout.iterrows():
                predictions.append(
                    {
                        **prediction_meta(seed, fold, row, spec),
                        "y_true": int(row["severity_label"]),
                        "y_pred": int(y_pred[idx]),
                        "y_prob": json.dumps([float(value) for value in probabilities[idx]], ensure_ascii=True),
                    }
                )
            fold_summaries.append(
                {
                    "seed": int(seed),
                    "fold": int(fold),
                    "train_subjects": int(len(train)),
                    "heldout_subjects": int(len(heldout)),
                    "train_severity_counts": {str(k): int(v) for k, v in train["severity_label"].astype(int).value_counts().sort_index().items()},
                    "heldout_severity_counts": {str(k): int(v) for k, v in heldout["severity_label"].astype(int).value_counts().sort_index().items()},
                    "classifier": spec.classifier,
                    "logistic_c": float(FIXED_LOGISTIC_C) if spec.classifier == "logistic" else None,
                    "mlp_alpha": float(FIXED_MLP_ALPHA) if spec.classifier == "mlp" else None,
                }
            )
    return pd.DataFrame(predictions), fold_summaries


def write_report(out_dir: Path, summary: dict[str, Any], spec: BaselineSpec) -> None:
    title = (
        "MPDD OpenFace Video Statistics + MLP Phase 2 Baseline"
        if spec.run_id == OPENFACE_SPEC.run_id
        else "MPDD ResNet Video Temporal-Pooling Phase 2 Baseline"
    )
    source_line = (
        "- Video source: manifest-resolved local MPDD OpenFace `.npy` feature directories."
        if spec.run_id == OPENFACE_SPEC.run_id
        else "- Video source: manifest-resolved local MPDD ResNet `.npy` feature directories."
    )
    representation_line = (
        "- Subject representation: all event/frame features are pooled to mean and standard deviation per OpenFace dimension."
        if spec.run_id == OPENFACE_SPEC.run_id
        else "- Subject representation: all event/frame features are pooled to mean and standard deviation per ResNet dimension."
    )
    classifier_line = (
        "- Classifier: fixed one-hidden-layer MLP over pooled subject features."
        if spec.run_id == OPENFACE_SPEC.run_id
        else "- Classifier: fixed multinomial logistic regression over pooled subject features."
    )
    lines = [
        f"# {title}",
        "",
        f"Generated: `{summary['generated_at']}`",
        "",
        "## Protocol",
        "",
        "- Input interface: `datasets/manifests/mpdd_avg_2026_subjects.csv`.",
        source_line,
        representation_line,
        classifier_line,
        "- Evaluation: five repeated stratified 5-fold subject-level out-of-fold runs over labeled MPDD train subjects.",
        "- Unlabeled MPDD test rows are ignored.",
        "- No validation/test labels are used for hyperparameter selection.",
        "- No raw video, source paths, frame-level features, or checkpoints are written to outputs.",
        "",
        "## Audit",
        "",
        f"- Run: `{spec.run_id}`",
        f"- Manifest video feature type: `{spec.manifest_feature_type}`",
        f"- Labeled video subjects: `{summary['subject_count']}`",
        f"- Elder subjects: `{summary['age_group_counts'].get('elder', 0)}`",
        f"- Young subjects: `{summary['age_group_counts'].get('young', 0)}`",
        f"- Severity counts: `{summary['severity_counts']}`",
        f"- Video events: `{summary['video_event_count']}`",
        f"- Video frames: `{summary['video_frame_count']}`",
        f"- Feature columns: `{summary['feature_count']}`",
        f"- Seeds: `{summary['seeds']}`",
        f"- Bootstrap resamples: `{summary['bootstrap_resamples']}`",
        f"- Prediction rows: `{summary['prediction_rows']}`",
        f"- Non-finite input values: `{summary['nonfinite_value_count']}`",
        f"- Raw video written: `{summary['raw_video_written']}`",
        f"- Source paths written: `{summary['source_paths_written']}`",
        "",
        "## Output Files",
        "",
        f"- `{spec.predictions_name}`",
        f"- `{spec.cache_name}`",
        "- `phase2_metrics_by_seed.csv`",
        "- `phase2_metric_summary.csv`",
        f"- `{spec.summary_name}`",
    ]
    (out_dir / spec.report_name).write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-id", choices=sorted(SPECS), default=RESNET_SPEC.run_id)
    parser.add_argument("--manifest-path", type=Path, default=MANIFEST_PATH)
    parser.add_argument("--out-dir", type=Path, default=None)
    parser.add_argument("--force-features", action="store_true")
    parser.add_argument("--bootstrap-resamples", type=int, default=1000)
    args = parser.parse_args()

    spec = SPECS[args.run_id]
    if args.out_dir is None:
        args.out_dir = DEFAULT_OPENFACE_OUT_DIR if spec.run_id == OPENFACE_SPEC.run_id else DEFAULT_OUT_DIR
    args.out_dir.mkdir(parents=True, exist_ok=True)
    subjects = labeled_subject_rows(args.manifest_path, spec)
    subject_features, _, extraction_summary = load_or_extract_subject_features(
        subjects,
        args.out_dir,
        force=args.force_features,
        spec=spec,
    )
    subject_table, feature_columns = build_subject_table(subjects, subject_features, spec)
    predictions, fold_summaries = run_oof(subject_table, feature_columns, spec)

    predictions_path = args.out_dir / spec.predictions_name
    predictions.to_csv(predictions_path, index=False)
    metrics_by_seed, metric_summary = metric_records(
        predictions,
        bootstrap_resamples=args.bootstrap_resamples,
        seed=20260727,
    )
    metrics_by_seed.to_csv(args.out_dir / "phase2_metrics_by_seed.csv", index=False)
    metric_summary.to_csv(args.out_dir / "phase2_metric_summary.csv", index=False)

    run_summary = {
        "generated_at": utc_now(),
        "manifest_path": str(args.manifest_path),
        "runs": [spec.run_id],
        "run_id": spec.run_id,
        "manifest_feature_type": spec.manifest_feature_type,
        "feature_prefix": spec.feature_prefix,
        "classifier": spec.classifier,
        "seeds": SEEDS,
        "bootstrap_resamples": int(args.bootstrap_resamples),
        "subject_count": int(subject_table["subject_id"].nunique()),
        "age_group_counts": {str(k): int(v) for k, v in subject_table["age_group"].value_counts().sort_index().items()},
        "severity_counts": {str(k): int(v) for k, v in subject_table["severity_label"].astype(int).value_counts().sort_index().items()},
        "video_event_count": int(subject_table["video_event_count"].sum()),
        "video_frame_count": int(subject_table["video_frame_count"].sum()),
        "feature_count": int(len(feature_columns)),
        "prediction_rows": int(len(predictions)),
        "nonfinite_value_count": int(subject_table["nonfinite_value_count"].sum()),
        "fold_summaries": fold_summaries,
        "feature_extraction": extraction_summary,
        "no_test_split_used": True,
        "raw_video_written": False,
        "source_paths_written": False,
        "checkpoints_written": False,
    }
    (args.out_dir / spec.summary_name).write_text(
        json.dumps(run_summary, indent=2, ensure_ascii=True, sort_keys=True),
        encoding="utf-8",
    )
    write_report(args.out_dir, run_summary, spec)
    print(f"Wrote {predictions_path}")
    print(f"Wrote {args.out_dir / 'phase2_metric_summary.csv'}")


if __name__ == "__main__":
    main()
