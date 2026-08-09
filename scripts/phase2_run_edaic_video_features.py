#!/usr/bin/env python3
"""Run Phase 2 E-DAIC video feature baselines.

The runner uses manifest-resolved E-DAIC subject rows and local official
feature files: OpenFace frame-level CSVs and CNN ResNet frame-level MATLAB
features. It fits only on the official train split, evaluates on the official
dev split, and writes prediction/metric artifacts without persisting raw video
or source paths.
"""

from __future__ import annotations

import argparse
import json
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

import numpy as np
import pandas as pd
from scipy.io import loadmat
from sklearn.impute import SimpleImputer
from sklearn.linear_model import Ridge
from sklearn.neural_network import MLPRegressor
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from phase2_metrics import metric_records


ROOT = Path("/root/autodl-tmp")
MANIFEST_PATH = ROOT / "datasets" / "manifests" / "edaic_subjects.csv"
DEFAULT_OUT_DIR = ROOT / "analysis" / "phase2_baselines" / "edaic_video_features"
SEEDS = [0, 1, 2, 3, 4]
FIXED_RIDGE_ALPHA = 10.0
MLP_HIDDEN_LAYER_SIZES = (64,)
MLP_ALPHA = 0.01
MLP_MAX_ITER = 2000


@dataclass(frozen=True)
class BaselineSpec:
    run_id: str
    model: str
    family: str


SPECS = [
    BaselineSpec(
        run_id="edaic_video_phq8_openface_mlp",
        model="OpenFace statistics + MLP",
        family="openface_statistics",
    ),
    BaselineSpec(
        run_id="edaic_video_phq8_official_temporal_pooling",
        model="official visual features + temporal pooling",
        family="resnet_temporal_pooling",
    ),
]


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def clean_feature_name(value: Any) -> str:
    return re.sub(r"[^0-9A-Za-z_]+", "_", str(value).strip()).strip("_")


def read_manifest(manifest_path: Path) -> pd.DataFrame:
    manifest = pd.read_csv(manifest_path)
    required = {"subject_id", "video_path", "phq8_total", "official_split", "file_valid"}
    missing = required - set(manifest.columns)
    if missing:
        raise ValueError(f"E-DAIC manifest missing columns: {', '.join(sorted(missing))}")
    usable = manifest[
        (manifest["file_valid"].fillna(False).astype(bool))
        & manifest["video_path"].notna()
        & manifest["phq8_total"].notna()
        & manifest["official_split"].isin(["train", "dev"])
    ].copy()
    if usable.empty:
        raise ValueError("no usable E-DAIC train/dev manifest rows")
    if usable["subject_id"].duplicated().any():
        dupes = sorted(usable.loc[usable["subject_id"].duplicated(), "subject_id"].astype(str).unique())
        raise ValueError(f"E-DAIC manifest should have one row per subject, duplicates observed: {dupes[:10]}")
    usable["subject_id"] = usable["subject_id"].astype(str)
    return usable.sort_values("subject_id").reset_index(drop=True)


def openface_path(row: pd.Series) -> Path:
    return Path(str(row["video_path"]))


def resnet_path(row: pd.Series) -> Path:
    video_path = Path(str(row["video_path"]))
    subject_id = str(row["subject_id"])
    return video_path.parent / f"{subject_id}_CNN_ResNet.mat"


def summarize_openface(path: Path) -> tuple[dict[str, float], int, list[str]]:
    if not path.exists():
        raise FileNotFoundError(f"E-DAIC OpenFace feature path missing: {path}")
    frame = pd.read_csv(path, skipinitialspace=True)
    frame.columns = [str(column).strip() for column in frame.columns]
    numeric = frame.select_dtypes(include=[np.number]).copy()
    drop_columns = [column for column in ["frame", "face_id", "timestamp"] if column in numeric.columns]
    if drop_columns:
        numeric = numeric.drop(columns=drop_columns)
    if numeric.empty:
        raise ValueError(f"OpenFace CSV has no numeric feature columns after metadata removal: {path}")
    columns = [clean_feature_name(column) for column in numeric.columns]
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
        for feature_name, value in zip(columns, stat_values, strict=True):
            out[f"of_{feature_name}__{stat_name}"] = float(value) if np.isfinite(value) else np.nan
    return out, int(len(frame)), columns


def summarize_resnet(path: Path) -> tuple[dict[str, float], int, int]:
    if not path.exists():
        raise FileNotFoundError(f"E-DAIC ResNet feature path missing: {path}")
    data = loadmat(path)
    if "feature" not in data:
        raise ValueError(f"E-DAIC ResNet .mat missing 'feature' key: {path}")
    arr = np.asarray(data["feature"], dtype=np.float32)
    if arr.ndim != 2 or arr.shape[1] <= 0:
        raise ValueError(f"E-DAIC ResNet features must be 2D, observed {arr.shape} in {path}")
    values = arr.astype(np.float64, copy=False)
    with np.errstate(invalid="ignore"):
        mean = np.nanmean(values, axis=0)
        std = np.nanstd(values, axis=0)
    out = {
        **{f"resnet_{idx:04d}__mean": float(value) if np.isfinite(value) else np.nan for idx, value in enumerate(mean)},
        **{f"resnet_{idx:04d}__std": float(value) if np.isfinite(value) else np.nan for idx, value in enumerate(std)},
    }
    return out, int(arr.shape[0]), int(arr.shape[1])


def load_cached_features(cache_path: Path, subjects: set[str]) -> pd.DataFrame | None:
    if not cache_path.exists():
        return None
    cached = pd.read_csv(cache_path)
    if "subject_id" not in cached.columns:
        return None
    cached["subject_id"] = cached["subject_id"].astype(str)
    if subjects.issubset(set(cached["subject_id"])):
        return cached[cached["subject_id"].isin(subjects)].copy()
    return cached[cached["subject_id"].isin(subjects)].copy()


def save_features(cache_path: Path, rows: list[dict[str, Any]]) -> None:
    frame = pd.DataFrame(rows)
    if not frame.empty:
        frame = frame.sort_values("subject_id").reset_index(drop=True)
    frame.to_csv(cache_path, index=False)


def extract_openface_features(manifest: pd.DataFrame, out_dir: Path, force: bool = False) -> pd.DataFrame:
    cache_path = out_dir / "edaic_openface_subject_features.csv"
    subjects = set(manifest["subject_id"].astype(str))
    if not force:
        cached = load_cached_features(cache_path, subjects)
        if cached is not None and subjects.issubset(set(cached["subject_id"])):
            print("Using cached E-DAIC OpenFace subject features", flush=True)
            return cached
    else:
        cached = None

    out_dir.mkdir(parents=True, exist_ok=True)
    feature_rows = [] if cached is None else cached.to_dict("records")
    cached_subjects = {str(row["subject_id"]) for row in feature_rows}
    expected_columns: list[str] | None = None
    if feature_rows:
        expected_columns = sorted(
            {
                column.split("__", 1)[0].removeprefix("of_")
                for column in feature_rows[0]
                if str(column).startswith("of_") and "__" in str(column)
            }
        )
    missing_rows = manifest[~manifest["subject_id"].isin(cached_subjects)].reset_index(drop=True)
    print(f"Summarizing E-DAIC OpenFace: {len(missing_rows)} missing / {len(manifest)} subjects", flush=True)
    for idx, row in missing_rows.iterrows():
        summary, frame_count, columns = summarize_openface(openface_path(row))
        if expected_columns is None:
            expected_columns = columns
        elif sorted(columns) != sorted(expected_columns):
            raise ValueError(f"E-DAIC OpenFace feature columns changed for subject {row['subject_id']}")
        feature_rows.append(
            {
                "subject_id": str(row["subject_id"]),
                "openface_frame_count": int(frame_count),
                **summary,
            }
        )
        if (idx + 1) % 25 == 0:
            save_features(cache_path, feature_rows)
            print(f"  [openface] {idx + 1}/{len(missing_rows)}", flush=True)
    save_features(cache_path, feature_rows)
    return pd.DataFrame(feature_rows).sort_values("subject_id").reset_index(drop=True)


def extract_resnet_features(manifest: pd.DataFrame, out_dir: Path, force: bool = False) -> pd.DataFrame:
    cache_path = out_dir / "edaic_resnet_temporal_pooling_subject_features.csv"
    subjects = set(manifest["subject_id"].astype(str))
    if not force:
        cached = load_cached_features(cache_path, subjects)
        if cached is not None and subjects.issubset(set(cached["subject_id"])):
            print("Using cached E-DAIC ResNet temporal-pooling subject features", flush=True)
            return cached
    else:
        cached = None

    out_dir.mkdir(parents=True, exist_ok=True)
    feature_rows = [] if cached is None else cached.to_dict("records")
    cached_subjects = {str(row["subject_id"]) for row in feature_rows}
    expected_dimension: int | None = None
    if feature_rows:
        mean_columns = [column for column in feature_rows[0] if str(column).startswith("resnet_") and str(column).endswith("__mean")]
        expected_dimension = len(mean_columns)
    missing_rows = manifest[~manifest["subject_id"].isin(cached_subjects)].reset_index(drop=True)
    print(f"Summarizing E-DAIC ResNet temporal pooling: {len(missing_rows)} missing / {len(manifest)} subjects", flush=True)
    for idx, row in missing_rows.iterrows():
        summary, frame_count, dimension = summarize_resnet(resnet_path(row))
        if expected_dimension is None:
            expected_dimension = dimension
        elif dimension != expected_dimension:
            raise ValueError(
                f"E-DAIC ResNet feature dimension changed for subject {row['subject_id']}: "
                f"{dimension} vs {expected_dimension}"
            )
        feature_rows.append(
            {
                "subject_id": str(row["subject_id"]),
                "resnet_frame_count": int(frame_count),
                "resnet_feature_dimension": int(dimension),
                **summary,
            }
        )
        if (idx + 1) % 10 == 0:
            save_features(cache_path, feature_rows)
            print(f"  [resnet] {idx + 1}/{len(missing_rows)}", flush=True)
    save_features(cache_path, feature_rows)
    return pd.DataFrame(feature_rows).sort_values("subject_id").reset_index(drop=True)


def add_labels(features: pd.DataFrame, manifest: pd.DataFrame) -> pd.DataFrame:
    labels = manifest[["subject_id", "official_split", "phq8_total"]].rename(columns={"official_split": "split"})
    table = labels.merge(features, on="subject_id", how="inner", validate="one_to_one")
    if len(table) != len(labels):
        missing = sorted(set(labels["subject_id"]) - set(table["subject_id"]))
        raise ValueError(f"E-DAIC subjects missing video features after merge: {missing[:10]}")
    train_subjects = set(table.loc[table["split"] == "train", "subject_id"].astype(str))
    dev_subjects = set(table.loc[table["split"] == "dev", "subject_id"].astype(str))
    overlap = sorted(train_subjects & dev_subjects)
    if overlap:
        raise ValueError(f"subject-level train/dev overlap detected: {overlap[:10]}")
    return table.sort_values("subject_id").reset_index(drop=True)


def feature_columns(table: pd.DataFrame) -> list[str]:
    excluded = {
        "subject_id",
        "split",
        "phq8_total",
        "openface_frame_count",
        "resnet_frame_count",
        "resnet_feature_dimension",
    }
    columns = [column for column in table.columns if column not in excluded]
    if not columns:
        raise ValueError("no video model feature columns available")
    return columns


def prepare_features(spec: BaselineSpec, manifest: pd.DataFrame, out_dir: Path, force: bool) -> tuple[pd.DataFrame, list[str], dict[str, Any]]:
    if spec.run_id == "edaic_video_phq8_openface_mlp":
        features = extract_openface_features(manifest, out_dir, force=force)
        frame_column = "openface_frame_count"
        feature_source = "OpenFace2.1.0_Pose_gaze_AUs.csv"
    elif spec.run_id == "edaic_video_phq8_official_temporal_pooling":
        features = extract_resnet_features(manifest, out_dir, force=force)
        frame_column = "resnet_frame_count"
        feature_source = "CNN_ResNet.mat"
    else:
        raise ValueError(f"unsupported run id: {spec.run_id}")
    table = add_labels(features, manifest)
    columns = feature_columns(table)
    return table, columns, {
        "run_id": spec.run_id,
        "subject_count": int(table["subject_id"].nunique()),
        "feature_count": int(len(columns)),
        "feature_source": feature_source,
        "frame_count_min": int(table[frame_column].min()),
        "frame_count_max": int(table[frame_column].max()),
        "frame_count_mean": float(table[frame_column].mean()),
    }


def run_spec(spec: BaselineSpec, table: pd.DataFrame, columns: list[str]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    train = table[table["split"] == "train"].reset_index(drop=True)
    dev = table[table["split"] == "dev"].reset_index(drop=True)
    if train.empty or dev.empty:
        raise ValueError(f"{spec.run_id} requires non-empty official train and dev splits")
    x_train = train[columns].to_numpy(dtype=np.float64)
    x_dev = dev[columns].to_numpy(dtype=np.float64)
    predictions: list[dict[str, Any]] = []
    seed_summaries: list[dict[str, Any]] = []
    clip_low = float(train["phq8_total"].min())
    clip_high = float(train["phq8_total"].max())

    for seed in SEEDS:
        if spec.run_id == "edaic_video_phq8_openface_mlp":
            estimator = MLPRegressor(
                hidden_layer_sizes=MLP_HIDDEN_LAYER_SIZES,
                alpha=MLP_ALPHA,
                solver="lbfgs",
                max_iter=MLP_MAX_ITER,
                random_state=seed,
            )
        else:
            estimator = Ridge(alpha=FIXED_RIDGE_ALPHA, solver="lsqr")
        model = Pipeline(
            [
                ("imputer", SimpleImputer(strategy="median")),
                ("scaler", StandardScaler()),
                ("regressor", estimator),
            ]
        )
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            model.fit(x_train, train["phq8_total"].to_numpy(dtype=np.float64))
        raw_pred = model.predict(x_dev)
        y_pred = np.clip(raw_pred, clip_low, clip_high)
        count_column = "openface_frame_count" if spec.run_id == "edaic_video_phq8_openface_mlp" else "resnet_frame_count"
        for idx, row in dev.iterrows():
            predictions.append(
                {
                    "run_id": spec.run_id,
                    "dataset": "E-DAIC",
                    "modality": "Video",
                    "task": "PHQ-8 regression",
                    "model": spec.model,
                    "seed": int(seed),
                    "task_type": "severity_regression",
                    "subject_id": str(row["subject_id"]),
                    "split": str(row["split"]),
                    "frame_count": int(row[count_column]),
                    "y_true": float(row["phq8_total"]),
                    "y_pred": float(y_pred[idx]),
                    "y_score": "",
                }
            )
        seed_summaries.append(
            {
                "run_id": spec.run_id,
                "seed": int(seed),
                "train_subjects": int(len(train)),
                "dev_subjects": int(len(dev)),
                "clip_low": float(clip_low),
                "clip_high": float(clip_high),
                "clipped_regression_predictions": int(np.sum((raw_pred < clip_low) | (raw_pred > clip_high))),
            }
        )
    return predictions, {
        "run_id": spec.run_id,
        "prediction_rows": int(len(predictions)),
        "seed_summaries": seed_summaries,
    }


def write_report(out_dir: Path, summary: dict[str, Any]) -> None:
    lines = [
        "# E-DAIC Video Feature Phase 2 Baselines",
        "",
        f"Generated: `{summary['generated_at']}`",
        "",
        "## Protocol",
        "",
        "- Input interface: manifest-resolved E-DAIC `video_path` values and subject feature folders.",
        "- OpenFace row: frame-level OpenFace features summarized per subject with mean, std, min, and max, then fit with a fixed MLP regressor.",
        "- Official visual row: `CNN_ResNet.mat` frame-level features pooled per subject with mean and std, then fit with a fixed Ridge regressor.",
        "- Unit of prediction: one row per dev subject per seed.",
        "- Fit on the official train split and evaluate on the official dev split.",
        "- No dev or test labels are used for hyperparameter selection.",
        "- No test split is used.",
        "- Raw video and source paths are not written to outputs.",
        "",
        "## Audit",
        "",
        f"- Runs: `{summary['runs']}`",
        f"- Seeds: `{summary['seeds']}`",
        f"- Bootstrap resamples: `{summary['bootstrap_resamples']}`",
        f"- Prediction rows: `{summary['prediction_rows']}`",
        f"- Train subjects: `{summary['train_subjects']}`",
        f"- Dev subjects: `{summary['dev_subjects']}`",
        f"- Subject overlap violations: `{summary['subject_overlap_violations']}`",
        f"- Raw video written: `{summary['raw_video_written']}`",
        f"- Source paths written: `{summary['source_paths_written']}`",
        "",
        "## Output Files",
        "",
        "- `edaic_video_feature_predictions.csv`",
        "- `phase2_metrics_by_seed.csv`",
        "- `phase2_metric_summary.csv`",
        "- `edaic_video_features_run_summary.json`",
    ]
    (out_dir / "edaic_video_features_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest-path", type=Path, default=MANIFEST_PATH)
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
    manifest = read_manifest(args.manifest_path)
    train_subjects = set(manifest.loc[manifest["official_split"] == "train", "subject_id"].astype(str))
    dev_subjects = set(manifest.loc[manifest["official_split"] == "dev", "subject_id"].astype(str))
    overlap = sorted(train_subjects & dev_subjects)
    if overlap:
        raise ValueError(f"subject-level train/dev overlap detected: {overlap[:10]}")

    all_predictions: list[dict[str, Any]] = []
    run_summaries: list[dict[str, Any]] = []
    for spec in selected_specs:
        table, columns, feature_summary = prepare_features(spec, manifest, args.out_dir, force=args.force_features)
        predictions, run_summary = run_spec(spec, table, columns)
        all_predictions.extend(predictions)
        run_summaries.append({**feature_summary, **run_summary})

    predictions_frame = pd.DataFrame(all_predictions)
    predictions_path = args.out_dir / "edaic_video_feature_predictions.csv"
    predictions_frame.to_csv(predictions_path, index=False)
    metrics_by_seed, metric_summary = metric_records(
        predictions_frame,
        bootstrap_resamples=args.bootstrap_resamples,
        seed=20260727,
    )
    metrics_by_seed.to_csv(args.out_dir / "phase2_metrics_by_seed.csv", index=False)
    metric_summary.to_csv(args.out_dir / "phase2_metric_summary.csv", index=False)

    summary = {
        "generated_at": utc_now(),
        "manifest_path": str(args.manifest_path),
        "runs": [spec.run_id for spec in selected_specs],
        "seeds": SEEDS,
        "seed_count": len(SEEDS),
        "bootstrap_resamples": int(args.bootstrap_resamples),
        "train_subjects": int(len(train_subjects)),
        "dev_subjects": int(len(dev_subjects)),
        "test_subjects_used": 0,
        "prediction_rows": int(len(predictions_frame)),
        "run_summaries": run_summaries,
        "subject_overlap_violations": int(bool(set(train_subjects) & set(dev_subjects))),
        "no_test_split_used": True,
        "raw_video_written": False,
        "source_paths_written": False,
    }
    (args.out_dir / "edaic_video_features_run_summary.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=True, sort_keys=True),
        encoding="utf-8",
    )
    write_report(args.out_dir, summary)
    print(f"Wrote {predictions_path}")
    print(f"Wrote {args.out_dir / 'phase2_metric_summary.csv'}")


if __name__ == "__main__":
    main()
