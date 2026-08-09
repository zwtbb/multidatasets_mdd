#!/usr/bin/env python3
"""Run Phase 2 CMDC video baselines from official feature files.

CMDC ships OpenFace frame-level CSV files (`Q*.csv`) and visual deep
representations (`Q*.npy`) for the 45 subjects with video recordings. This
runner evaluates the two planned Phase 2 CMDC video rows while preserving the
generated subject-level split protocol and writing no raw video or source
paths.
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
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from phase2_metrics import metric_records


ROOT = Path("/root/autodl-tmp")
MANIFEST_PATH = ROOT / "datasets" / "manifests" / "cmdc_subjects.csv"
SPLIT_PATH = ROOT / "datasets" / "splits" / "phase2_subject_splits.csv"
DEFAULT_OUT_DIR = ROOT / "analysis" / "phase2_baselines" / "cmdc_video_features"
PROTOCOL_ID = "cmdc_binary_subject_cv"
TARGET = "binary_label"
SEEDS = [0, 1, 2, 3, 4]
MLP_HIDDEN_LAYER_SIZES = (64,)
MLP_ALPHA = 0.01
MLP_MAX_ITER = 1000
FIXED_LOGISTIC_C = 1.0


@dataclass(frozen=True)
class BaselineSpec:
    run_id: str
    model: str
    family: str


SPECS = [
    BaselineSpec(
        run_id="cmdc_video_binary_temporal_pooling",
        model="official visual features + temporal pooling",
        family="timesformer_temporal_pooling",
    ),
    BaselineSpec(
        run_id="cmdc_video_binary_openface_mlp",
        model="OpenFace statistics + MLP",
        family="openface_statistics",
    ),
]


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def natural_key(value: Any) -> list[Any]:
    return [int(part) if part.isdigit() else part for part in re.split(r"(\d+)", str(value))]


def load_protocol_splits(split_path: Path) -> dict[str, dict[str, list[str]]]:
    splits = pd.read_csv(split_path)
    required = {"dataset", "protocol_id", "target", "fold", "role", "subject_id"}
    missing = required - set(splits.columns)
    if missing:
        raise ValueError(f"split layer missing columns: {', '.join(sorted(missing))}")
    selected = splits[
        (splits["dataset"].astype(str) == "cmdc")
        & (splits["protocol_id"].astype(str) == PROTOCOL_ID)
        & (splits["target"].astype(str) == TARGET)
    ].copy()
    if selected.empty:
        raise ValueError(f"no split rows for {PROTOCOL_ID}:{TARGET}")
    folds: dict[str, dict[str, list[str]]] = {}
    for fold, fold_rows in selected.groupby("fold", sort=False):
        roles: dict[str, list[str]] = {}
        for role, role_rows in fold_rows.groupby("role", sort=False):
            roles[str(role)] = sorted(role_rows["subject_id"].astype(str).unique(), key=natural_key)
        train_subjects = set(roles.get("train", []))
        validation_subjects = set(roles.get("validation", []))
        overlap = sorted(train_subjects & validation_subjects, key=natural_key)
        if overlap:
            raise ValueError(f"{fold} train/validation subject overlap: {overlap[:10]}")
        if not train_subjects or not validation_subjects:
            raise ValueError(f"{fold} requires non-empty train and validation roles")
        folds[str(fold)] = roles
    return dict(sorted(folds.items(), key=lambda item: natural_key(item[0])))


def segment_rows(manifest_path: Path) -> pd.DataFrame:
    if not manifest_path.exists():
        raise FileNotFoundError(f"manifest missing: {manifest_path}")
    manifest = pd.read_csv(manifest_path)
    required = {"subject_id", "segment_id", "video_path", "file_valid", TARGET}
    missing = required - set(manifest.columns)
    if missing:
        raise ValueError(f"CMDC manifest missing columns: {', '.join(sorted(missing))}")
    rows = manifest[
        manifest["file_valid"].fillna(False).astype(bool)
        & manifest["video_path"].notna()
        & manifest[TARGET].notna()
    ].copy()
    if rows.empty:
        raise ValueError("no usable CMDC video rows")
    rows = rows.sort_values(["subject_id", "segment_id"]).reset_index()
    rows["segment_key"] = rows.apply(
        lambda row: "::".join([str(row.get("session_id", "")), str(row.get("segment_id", "")), str(row["index"])]),
        axis=1,
    )
    return rows.reset_index(drop=True)


def save_segment_cache(path: Path, rows: list[dict[str, Any]]) -> None:
    frame = pd.DataFrame(rows)
    if not frame.empty:
        frame = frame.sort_values(["subject_id", "segment_key"]).reset_index(drop=True)
    frame.to_csv(path, index=False)


def load_timesformer_segment_features(rows: pd.DataFrame, out_dir: Path, force: bool = False) -> pd.DataFrame:
    cache_path = out_dir / "cmdc_timesformer_segment_features.csv"
    required_keys = set(zip(rows["subject_id"].astype(str), rows["segment_key"].astype(str), strict=True))
    if cache_path.exists() and not force:
        cached = pd.read_csv(cache_path)
        cached_keys = set(zip(cached["subject_id"].astype(str), cached["segment_key"].astype(str), strict=True))
        if required_keys.issubset(cached_keys):
            print("Using cached CMDC TimeSformer segment features", flush=True)
            return cached[
                [key in required_keys for key in zip(cached["subject_id"].astype(str), cached["segment_key"].astype(str), strict=True)]
            ].copy()
    feature_rows: list[dict[str, Any]] = []
    for idx, row in rows.iterrows():
        path = Path(str(row["video_path"]))
        if not path.exists():
            raise FileNotFoundError(f"manifest video feature path missing: {path}")
        arr = np.asarray(np.load(path), dtype=np.float64).reshape(-1)
        if arr.size != 768:
            raise ValueError(f"expected 768 visual features in {path}, observed {arr.size}")
        if not np.isfinite(arr).all():
            raise ValueError(f"non-finite visual features in {path}")
        feature_rows.append(
            {
                "subject_id": str(row["subject_id"]),
                "segment_key": str(row["segment_key"]),
                "segment_id": str(row["segment_id"]),
                **{f"tsf_{feature_idx:04d}": float(value) for feature_idx, value in enumerate(arr)},
            }
        )
        if (idx + 1) % 100 == 0:
            print(f"  [timesformer] {idx + 1}/{len(rows)}", flush=True)
    save_segment_cache(cache_path, feature_rows)
    return pd.DataFrame(feature_rows)


def openface_path(video_path: Any) -> Path:
    return Path(str(video_path)).with_suffix(".csv")


def summarize_openface_csv(path: Path) -> dict[str, float]:
    if not path.exists():
        raise FileNotFoundError(f"OpenFace feature path missing: {path}")
    frame = pd.read_csv(path, skipinitialspace=True)
    frame.columns = [str(column).strip() for column in frame.columns]
    numeric = frame.select_dtypes(include=[np.number]).copy()
    drop_columns = [column for column in ["frame", "face_id", "timestamp"] if column in numeric.columns]
    if drop_columns:
        numeric = numeric.drop(columns=drop_columns)
    if numeric.empty:
        raise ValueError(f"OpenFace CSV has no numeric feature columns after metadata removal: {path}")
    values = numeric.to_numpy(dtype=np.float64)
    out: dict[str, float] = {}
    with np.errstate(invalid="ignore"):
        stats = {
            "mean": np.nanmean(values, axis=0),
            "std": np.nanstd(values, axis=0),
            "min": np.nanmin(values, axis=0),
            "max": np.nanmax(values, axis=0),
        }
    for stat_name, stat_values in stats.items():
        for feature_name, value in zip(numeric.columns, stat_values, strict=True):
            clean_name = re.sub(r"[^0-9A-Za-z_]+", "_", str(feature_name).strip()).strip("_")
            out[f"of_{clean_name}__{stat_name}"] = float(value) if np.isfinite(value) else np.nan
    return out


def load_openface_segment_features(rows: pd.DataFrame, out_dir: Path, force: bool = False) -> pd.DataFrame:
    cache_path = out_dir / "cmdc_openface_segment_features.csv"
    required_keys = set(zip(rows["subject_id"].astype(str), rows["segment_key"].astype(str), strict=True))
    feature_rows: list[dict[str, Any]] = []
    cached_keys: set[tuple[str, str]] = set()
    if cache_path.exists() and not force:
        cached = pd.read_csv(cache_path)
        cached["subject_id"] = cached["subject_id"].astype(str)
        cached["segment_key"] = cached["segment_key"].astype(str)
        cached_keys = set(zip(cached["subject_id"], cached["segment_key"], strict=True))
        feature_rows = cached[
            [key in required_keys for key in zip(cached["subject_id"], cached["segment_key"], strict=True)]
        ].to_dict("records")
        if required_keys.issubset(cached_keys):
            print("Using cached CMDC OpenFace segment features", flush=True)
            return pd.DataFrame(feature_rows)
    missing_rows = rows[
        [
            key not in cached_keys
            for key in zip(rows["subject_id"].astype(str), rows["segment_key"].astype(str), strict=True)
        ]
    ].reset_index(drop=True)
    print(f"Extracting CMDC OpenFace statistics: {len(missing_rows)} missing / {len(rows)} segments", flush=True)
    for idx, row in missing_rows.iterrows():
        path = openface_path(row["video_path"])
        feature_rows.append(
            {
                "subject_id": str(row["subject_id"]),
                "segment_key": str(row["segment_key"]),
                "segment_id": str(row["segment_id"]),
                **summarize_openface_csv(path),
            }
        )
        if (idx + 1) % 25 == 0:
            save_segment_cache(cache_path, feature_rows)
            print(f"  [openface] {idx + 1}/{len(missing_rows)}", flush=True)
    save_segment_cache(cache_path, feature_rows)
    return pd.DataFrame(feature_rows)


def aggregate_subject_features(segment_features: pd.DataFrame, prefix: str) -> tuple[pd.DataFrame, list[str]]:
    metadata = {"subject_id", "segment_key", "segment_id"}
    feature_columns = [column for column in segment_features.columns if column not in metadata]
    rows: list[dict[str, Any]] = []
    for subject_id, group in segment_features.groupby("subject_id", sort=False):
        values = group[feature_columns].to_numpy(dtype=np.float64)
        row: dict[str, Any] = {
            "subject_id": str(subject_id),
            "video_segment_count": int(len(group)),
        }
        with np.errstate(invalid="ignore"):
            if prefix == "tsf":
                stats = {
                    "mean": np.nanmean(values, axis=0),
                    "std": np.nanstd(values, axis=0),
                    "min": np.nanmin(values, axis=0),
                    "max": np.nanmax(values, axis=0),
                }
                for stat_name, stat_values in stats.items():
                    for feature_name, value in zip(feature_columns, stat_values, strict=True):
                        row[f"{feature_name}__{stat_name}"] = float(value) if np.isfinite(value) else np.nan
            else:
                means = np.nanmean(values, axis=0)
                for feature_name, value in zip(feature_columns, means, strict=True):
                    row[f"{feature_name}__segment_mean"] = float(value) if np.isfinite(value) else np.nan
        rows.append(row)
    table = pd.DataFrame(rows).sort_values("subject_id", key=lambda series: series.map(lambda item: tuple(natural_key(item)))).reset_index(drop=True)
    model_columns = [column for column in table.columns if column not in {"subject_id", "video_segment_count"}]
    return table, model_columns


def add_labels(features: pd.DataFrame, manifest_rows: pd.DataFrame) -> pd.DataFrame:
    labels: list[dict[str, Any]] = []
    for subject_id, group in manifest_rows.groupby("subject_id", sort=False):
        values = group[TARGET].dropna().unique()
        if len(values) != 1:
            raise ValueError(f"{subject_id} has inconsistent binary labels: {values[:5]}")
        labels.append({"subject_id": str(subject_id), TARGET: int(values[0])})
    table = features.merge(pd.DataFrame(labels), on="subject_id", how="inner")
    if table.empty:
        raise ValueError("no labeled CMDC video feature rows")
    return table.sort_values("subject_id", key=lambda series: series.map(lambda item: tuple(natural_key(item)))).reset_index(drop=True)


def prepare_features(spec: BaselineSpec, rows: pd.DataFrame, out_dir: Path, force: bool) -> tuple[pd.DataFrame, list[str], dict[str, Any]]:
    if spec.run_id == "cmdc_video_binary_temporal_pooling":
        segments = load_timesformer_segment_features(rows, out_dir, force=force)
        subject_features, feature_columns = aggregate_subject_features(segments, prefix="tsf")
    elif spec.run_id == "cmdc_video_binary_openface_mlp":
        segments = load_openface_segment_features(rows, out_dir, force=force)
        subject_features, feature_columns = aggregate_subject_features(segments, prefix="openface")
    else:
        raise ValueError(f"unsupported run id: {spec.run_id}")
    subject_path = out_dir / f"{spec.family}_subject_features.csv"
    subject_features.to_csv(subject_path, index=False)
    table = add_labels(subject_features, rows)
    return table, feature_columns, {
        "segment_feature_rows": int(len(segments)),
        "subject_feature_rows": int(len(subject_features)),
        "feature_count": int(len(feature_columns)),
        "video_segment_count_min": int(subject_features["video_segment_count"].min()),
        "video_segment_count_max": int(subject_features["video_segment_count"].max()),
        "subject_feature_file": str(subject_path),
    }


def filtered_roles(roles: dict[str, list[str]], available_subjects: set[str]) -> dict[str, list[str]]:
    return {
        role: [subject for subject in subjects if subject in available_subjects]
        for role, subjects in roles.items()
    }


def run_spec(spec: BaselineSpec, table: pd.DataFrame, feature_columns: list[str], folds: dict[str, dict[str, list[str]]]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    table_by_subject = table.set_index("subject_id", drop=False)
    available_subjects = set(table["subject_id"].astype(str))
    predictions: list[dict[str, Any]] = []
    fold_summaries: list[dict[str, Any]] = []
    for seed in SEEDS:
        for fold, roles in folds.items():
            kept = filtered_roles(roles, available_subjects)
            train_subjects = kept.get("train", [])
            validation_subjects = kept.get("validation", [])
            if not train_subjects or not validation_subjects:
                raise ValueError(f"{spec.run_id}:{fold} has empty train/validation after video-subject filtering")
            train = table_by_subject.loc[train_subjects].reset_index(drop=True)
            validation = table_by_subject.loc[validation_subjects].reset_index(drop=True)
            if spec.run_id == "cmdc_video_binary_openface_mlp":
                classifier = MLPClassifier(
                    hidden_layer_sizes=MLP_HIDDEN_LAYER_SIZES,
                    alpha=MLP_ALPHA,
                    solver="lbfgs",
                    max_iter=MLP_MAX_ITER,
                    random_state=seed,
                )
            else:
                classifier = LogisticRegression(
                    C=FIXED_LOGISTIC_C,
                    class_weight="balanced",
                    max_iter=1000,
                    random_state=seed,
                    solver="liblinear",
                )
            model = Pipeline(
                [
                    ("imputer", SimpleImputer(strategy="median")),
                    ("scaler", StandardScaler()),
                    ("classifier", classifier),
                ]
            )
            model.fit(train[feature_columns], train[TARGET].astype(int))
            y_pred = model.predict(validation[feature_columns])
            y_score = model.predict_proba(validation[feature_columns])[:, 1]
            for idx, row in validation.iterrows():
                predictions.append(
                    {
                        "run_id": spec.run_id,
                        "dataset": "CMDC",
                        "modality": "Video",
                        "task": "MDD classification",
                        "model": spec.model,
                        "seed": int(seed),
                        "fold": fold,
                        "protocol_id": PROTOCOL_ID,
                        "task_type": "binary_classification",
                        "subject_id": str(row["subject_id"]),
                        "split": "validation",
                        "video_segment_count": int(row["video_segment_count"]),
                        "y_true": int(row[TARGET]),
                        "y_pred": int(y_pred[idx]),
                        "y_score": float(y_score[idx]),
                    }
                )
            fold_summaries.append(
                {
                    "run_id": spec.run_id,
                    "seed": int(seed),
                    "fold": fold,
                    "train_subjects": int(len(train)),
                    "validation_subjects": int(len(validation)),
                    "train_positive_subjects": int(train[TARGET].astype(int).sum()),
                    "validation_positive_subjects": int(validation[TARGET].astype(int).sum()),
                }
            )
    return predictions, {
        "run_id": spec.run_id,
        "subject_count": int(table["subject_id"].nunique()),
        "prediction_rows": int(len(predictions)),
        "fold_summaries": fold_summaries,
    }


def write_report(out_dir: Path, summary: dict[str, Any]) -> None:
    lines = [
        "# CMDC Video Feature Phase 2 Baselines",
        "",
        f"Generated: `{summary['generated_at']}`",
        "",
        "## Protocol",
        "",
        "- Input interface: manifest-resolved CMDC video feature files and `datasets/splits/phase2_subject_splits.csv`.",
        "- OpenFace row: `Q*.csv` frame-level OpenFace features summarized per segment, averaged per subject, then fit with a fixed MLP classifier.",
        "- Official visual row: `Q*.npy` TimeSformer/Kinetics visual representations pooled per subject with mean, std, min, and max, then fit with a fixed logistic head.",
        "- Only the 45 subjects with video recordings are evaluated; fold membership is inherited from `cmdc_binary_subject_cv` and filtered to video-available subjects.",
        "- Unit of prediction: one row per video-available subject per seed after subject-level CV.",
        "- No validation or test labels are used for hyperparameter selection.",
        "- No test split is used.",
        "- Raw video, feature paths, and source paths are not written to outputs.",
        "",
        "## Audit",
        "",
        f"- Runs: `{summary['runs']}`",
        f"- Subjects: `{summary['subject_count']}`",
        f"- Seeds: `{summary['seeds']}`",
        f"- Bootstrap resamples: `{summary['bootstrap_resamples']}`",
        f"- Prediction rows: `{summary['prediction_rows']}`",
        f"- Subject overlap violations: `{summary['subject_overlap_violations']}`",
        f"- Raw video written: `{summary['raw_video_written']}`",
        f"- Source paths written: `{summary['source_paths_written']}`",
        "",
        "## Output Files",
        "",
        "- `cmdc_video_feature_predictions.csv`",
        "- `phase2_metrics_by_seed.csv`",
        "- `phase2_metric_summary.csv`",
        "- `cmdc_video_features_run_summary.json`",
    ]
    (out_dir / "cmdc_video_features_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest-path", type=Path, default=MANIFEST_PATH)
    parser.add_argument("--split-path", type=Path, default=SPLIT_PATH)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--run-id", choices=[spec.run_id for spec in SPECS], action="append")
    parser.add_argument("--force-features", action="store_true")
    parser.add_argument("--bootstrap-resamples", type=int, default=1000)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    args.out_dir.mkdir(parents=True, exist_ok=True)
    selected_ids = set(args.run_id or [spec.run_id for spec in SPECS])
    selected_specs = [spec for spec in SPECS if spec.run_id in selected_ids]
    rows = segment_rows(args.manifest_path)
    folds = load_protocol_splits(args.split_path)

    all_predictions: list[dict[str, Any]] = []
    run_summaries: list[dict[str, Any]] = []
    for spec in selected_specs:
        table, feature_columns, feature_summary = prepare_features(spec, rows, args.out_dir, force=args.force_features)
        predictions, run_summary = run_spec(spec, table, feature_columns, folds)
        all_predictions.extend(predictions)
        run_summaries.append({**run_summary, **feature_summary})

    predictions_frame = pd.DataFrame(all_predictions)
    predictions_path = args.out_dir / "cmdc_video_feature_predictions.csv"
    predictions_frame.to_csv(predictions_path, index=False)
    metrics_by_seed, metric_summary = metric_records(
        predictions_frame,
        bootstrap_resamples=args.bootstrap_resamples,
        seed=20260727,
    )
    metrics_by_seed.to_csv(args.out_dir / "phase2_metrics_by_seed.csv", index=False)
    metric_summary.to_csv(args.out_dir / "phase2_metric_summary.csv", index=False)

    subject_overlap_violations = int(
        sum(bool(set(roles["train"]) & set(roles["validation"])) for roles in folds.values())
    )
    summary = {
        "generated_at": utc_now(),
        "manifest_path": str(args.manifest_path),
        "split_path": str(args.split_path),
        "runs": [spec.run_id for spec in selected_specs],
        "seeds": SEEDS,
        "bootstrap_resamples": int(args.bootstrap_resamples),
        "subject_count": int(predictions_frame["subject_id"].nunique()),
        "prediction_rows": int(len(predictions_frame)),
        "run_summaries": run_summaries,
        "subject_overlap_violations": subject_overlap_violations,
        "no_test_split_used": True,
        "raw_video_written": False,
        "source_paths_written": False,
    }
    (args.out_dir / "cmdc_video_features_run_summary.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=True, sort_keys=True),
        encoding="utf-8",
    )
    write_report(args.out_dir, summary)
    print(f"Wrote {predictions_path}")
    print(f"Wrote {args.out_dir / 'phase2_metric_summary.csv'}")


if __name__ == "__main__":
    main()
