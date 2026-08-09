#!/usr/bin/env python3
"""Run Phase 2 CMDC/PDCH audio eGeMAPS baselines.

The runner extracts openSMILE eGeMAPSv02 functionals from manifest-resolved
audio paths, aggregates segment-level features to one subject row, and evaluates
the generated subject-level split protocols. It writes feature and prediction
artifacts without persisting raw audio or source paths.
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
import opensmile
import pandas as pd
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.svm import SVC, SVR

from phase2_metrics import metric_records


ROOT = Path("/root/autodl-tmp")
MANIFEST_DIR = ROOT / "datasets" / "manifests"
SPLIT_PATH = ROOT / "datasets" / "splits" / "phase2_subject_splits.csv"
DEFAULT_OUT_DIR = ROOT / "analysis" / "phase2_baselines" / "cmdc_pdch_audio_egemaps"
SEEDS = [0, 1, 2, 3, 4]
FIXED_SVM_C = 1.0
FIXED_SVR_C = 1.0
FIXED_SVR_EPSILON = 0.1


@dataclass(frozen=True)
class BaselineSpec:
    run_id: str
    dataset_id: str
    display_dataset: str
    modality: str
    task: str
    task_type: str
    target: str
    model: str
    protocol_id: str


SPECS = [
    BaselineSpec(
        run_id="pdch_audio_hamd17_egemaps_svr",
        dataset_id="pdch",
        display_dataset="PDCH",
        modality="Audio",
        task="HAMD-17 regression",
        task_type="severity_regression",
        target="hamd17_total",
        model="eGeMAPS + SVR",
        protocol_id="pdch_hamd17_subject_cv_fallback",
    ),
    BaselineSpec(
        run_id="cmdc_audio_binary_egemaps_svm",
        dataset_id="cmdc",
        display_dataset="CMDC",
        modality="Audio",
        task="MDD classification",
        task_type="binary_classification",
        target="binary_label",
        model="eGeMAPS + SVM",
        protocol_id="cmdc_binary_subject_cv",
    ),
]


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def natural_key(value: Any) -> list[Any]:
    return [int(part) if part.isdigit() else part for part in re.split(r"(\d+)", str(value))]


def read_manifest(dataset_id: str) -> pd.DataFrame:
    path = MANIFEST_DIR / f"{dataset_id}_subjects.csv"
    if not path.exists():
        raise FileNotFoundError(f"manifest missing: {path}")
    return pd.read_csv(path)


def load_protocol_splits(split_path: Path, spec: BaselineSpec) -> dict[str, dict[str, list[str]]]:
    splits = pd.read_csv(split_path)
    required = {"dataset", "protocol_id", "target", "fold", "role", "subject_id"}
    missing = required - set(splits.columns)
    if missing:
        raise ValueError(f"split layer missing columns: {', '.join(sorted(missing))}")
    selected = splits[
        (splits["dataset"].astype(str) == spec.dataset_id)
        & (splits["protocol_id"].astype(str) == spec.protocol_id)
        & (splits["target"].astype(str) == spec.target)
    ].copy()
    if selected.empty:
        raise ValueError(f"no split rows for {spec.run_id} protocol {spec.protocol_id}")
    folds: dict[str, dict[str, list[str]]] = {}
    for fold, fold_rows in selected.groupby("fold", sort=False):
        roles: dict[str, list[str]] = {}
        for role, role_rows in fold_rows.groupby("role", sort=False):
            roles[str(role)] = sorted(role_rows["subject_id"].astype(str).unique(), key=natural_key)
        train_subjects = set(roles.get("train", []))
        validation_subjects = set(roles.get("validation", []))
        overlap = sorted(train_subjects & validation_subjects, key=natural_key)
        if overlap:
            raise ValueError(f"{spec.run_id}:{fold} train/validation subject overlap: {overlap[:10]}")
        if not train_subjects or not validation_subjects:
            raise ValueError(f"{spec.run_id}:{fold} requires non-empty train and validation roles")
        folds[str(fold)] = roles
    return dict(sorted(folds.items(), key=lambda item: natural_key(item[0])))


def segment_rows(dataset_id: str, subjects: set[str]) -> pd.DataFrame:
    manifest = read_manifest(dataset_id)
    required = {"subject_id", "audio_path"}
    missing = required - set(manifest.columns)
    if missing:
        raise ValueError(f"{dataset_id} manifest missing columns: {', '.join(sorted(missing))}")
    rows = manifest[manifest["subject_id"].astype(str).isin(subjects)].copy()
    if "file_valid" in rows.columns:
        rows = rows[rows["file_valid"].fillna(False).astype(bool)].copy()
    rows = rows[rows["audio_path"].notna()].copy()
    sort_columns = [column for column in ["subject_id", "session_id", "segment_id"] if column in rows.columns]
    rows = rows.sort_values(sort_columns).reset_index()
    rows["segment_key"] = rows.apply(
        lambda row: "::".join(
            [
                str(row.get("session_id", "")),
                str(row.get("segment_id", "")),
                str(row["index"]),
            ]
        ),
        axis=1,
    )
    observed = set(rows["subject_id"].astype(str))
    missing_subjects = sorted(subjects - observed, key=natural_key)
    if missing_subjects:
        raise ValueError(f"{dataset_id} split subjects missing valid audio rows: {missing_subjects[:10]}")
    return rows.reset_index(drop=True)


def aggregate_subject_features(segment_features: pd.DataFrame, feature_columns: list[str]) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for subject_id, group in segment_features.groupby("subject_id", sort=False):
        values = group[feature_columns].to_numpy(dtype=np.float64)
        row: dict[str, Any] = {
            "dataset_id": group.iloc[0]["dataset_id"],
            "subject_id": str(subject_id),
            "audio_segment_count": int(len(group)),
        }
        with np.errstate(invalid="ignore"):
            stats = {
                "mean": np.nanmean(values, axis=0),
                "std": np.nanstd(values, axis=0),
                "min": np.nanmin(values, axis=0),
                "max": np.nanmax(values, axis=0),
            }
        for stat_name, stat_values in stats.items():
            for feature_name, feature_value in zip(feature_columns, stat_values, strict=True):
                row[f"{feature_name}__{stat_name}"] = float(feature_value) if np.isfinite(feature_value) else np.nan
        rows.append(row)
    return pd.DataFrame(rows).sort_values("subject_id", key=lambda series: series.map(lambda item: tuple(natural_key(item)))).reset_index(drop=True)


def save_segment_cache(path: Path, rows: list[dict[str, Any]]) -> None:
    frame = pd.DataFrame(rows)
    if not frame.empty:
        frame = frame.sort_values(["subject_id", "segment_key"]).reset_index(drop=True)
    frame.to_csv(path, index=False)


def extract_subject_features(dataset_id: str, subjects: set[str], out_dir: Path, force: bool = False) -> pd.DataFrame:
    subject_cache_path = out_dir / f"{dataset_id}_egemaps_subject_features.csv"
    segment_cache_path = out_dir / f"{dataset_id}_egemaps_segment_features.csv"
    if subject_cache_path.exists() and not force:
        cached = pd.read_csv(subject_cache_path)
        cached_subjects = set(cached["subject_id"].astype(str))
        if subjects.issubset(cached_subjects):
            print(f"Using cached subject-level eGeMAPS for {dataset_id}", flush=True)
            return cached[cached["subject_id"].astype(str).isin(subjects)].copy()

    out_dir.mkdir(parents=True, exist_ok=True)
    rows = segment_rows(dataset_id, subjects)
    required_keys = set(zip(rows["subject_id"].astype(str), rows["segment_key"].astype(str), strict=True))
    cached_segment_rows: list[dict[str, Any]] = []
    if segment_cache_path.exists() and not force:
        cached_segments = pd.read_csv(segment_cache_path)
        cached_segments["subject_id"] = cached_segments["subject_id"].astype(str)
        cached_segments["segment_key"] = cached_segments["segment_key"].astype(str)
        cached_keys = set(zip(cached_segments["subject_id"], cached_segments["segment_key"], strict=True))
        cached_segment_rows = cached_segments[
            [
                key in required_keys
                for key in zip(cached_segments["subject_id"], cached_segments["segment_key"], strict=True)
            ]
        ].to_dict("records")
    else:
        cached_keys = set()
    missing_rows = rows[
        [
            key not in cached_keys
            for key in zip(rows["subject_id"].astype(str), rows["segment_key"].astype(str), strict=True)
        ]
    ].reset_index(drop=True)

    smile = opensmile.Smile(
        feature_set=opensmile.FeatureSet.eGeMAPSv02,
        feature_level=opensmile.FeatureLevel.Functionals,
    )
    segment_feature_rows: list[dict[str, Any]] = cached_segment_rows
    feature_columns: list[str] | None = None
    if segment_feature_rows:
        feature_columns = [
            column
            for column in pd.DataFrame(segment_feature_rows).columns
            if column not in {"dataset_id", "subject_id", "segment_key"}
        ]
    print(
        f"Extracting eGeMAPS for {dataset_id}: {len(missing_rows)} missing / {len(rows)} audio segments, {len(subjects)} subjects",
        flush=True,
    )
    warnings.filterwarnings("ignore", message="Segment too short.*")
    for idx, row in missing_rows.iterrows():
        path = Path(str(row["audio_path"]))
        if not path.exists():
            raise FileNotFoundError(f"manifest audio path missing: {path}")
        print(
            f"  [{dataset_id}] {idx + 1}/{len(missing_rows)} subject={row['subject_id']} segment={row['segment_key']}",
            flush=True,
        )
        features = smile.process_file(str(path))
        if features.empty:
            raise ValueError(f"openSMILE returned no features for {path}")
        values = features.iloc[0]
        if feature_columns is None:
            feature_columns = [str(column) for column in values.index]
        segment_feature_rows.append(
            {
                "dataset_id": dataset_id,
                "subject_id": str(row["subject_id"]),
                "segment_key": str(row["segment_key"]),
                **{str(column): float(values[column]) for column in values.index},
            }
        )
        if (idx + 1) % 25 == 0:
            save_segment_cache(segment_cache_path, segment_feature_rows)
    if feature_columns is None:
        raise RuntimeError(f"no eGeMAPS features extracted for {dataset_id}")
    save_segment_cache(segment_cache_path, segment_feature_rows)
    segment_features = pd.DataFrame(segment_feature_rows)
    observed_keys = set(zip(segment_features["subject_id"].astype(str), segment_features["segment_key"].astype(str), strict=True))
    missing_keys = required_keys - observed_keys
    if missing_keys:
        raise ValueError(f"{dataset_id} missing cached eGeMAPS rows: {sorted(missing_keys)[:5]}")
    segment_features = segment_features[
        [
            key in required_keys
            for key in zip(segment_features["subject_id"].astype(str), segment_features["segment_key"].astype(str), strict=True)
        ]
    ].copy()
    subject_features = aggregate_subject_features(segment_features, feature_columns)
    subject_features.to_csv(subject_cache_path, index=False)
    return subject_features


def build_subject_table(spec: BaselineSpec, features: pd.DataFrame) -> tuple[pd.DataFrame, list[str]]:
    manifest = read_manifest(spec.dataset_id)
    if spec.target not in manifest.columns:
        raise ValueError(f"{spec.dataset_id} manifest missing target column: {spec.target}")
    label_rows = manifest[manifest["subject_id"].astype(str).isin(set(features["subject_id"].astype(str)))].copy()
    if "file_valid" in label_rows.columns:
        label_rows = label_rows[label_rows["file_valid"].fillna(False).astype(bool)].copy()
    label_rows = label_rows[label_rows[spec.target].notna()].copy()
    labels: list[dict[str, Any]] = []
    for subject_id, group in label_rows.groupby("subject_id", sort=False):
        values = group[spec.target].dropna().unique()
        if len(values) != 1:
            raise ValueError(f"{spec.run_id}:{subject_id} has inconsistent labels: {values[:5]}")
        labels.append({"subject_id": str(subject_id), spec.target: float(values[0])})
    labels_frame = pd.DataFrame(labels)
    table = features.merge(labels_frame, on="subject_id", how="inner")
    if table.empty:
        raise ValueError(f"no labeled feature rows for {spec.run_id}")
    feature_columns = [
        column
        for column in table.columns
        if column not in {"dataset_id", "subject_id", "audio_segment_count", spec.target}
    ]
    missing_labels = sorted(set(features["subject_id"].astype(str)) - set(table["subject_id"].astype(str)), key=natural_key)
    if missing_labels:
        raise ValueError(f"{spec.run_id} split subjects missing labels: {missing_labels[:10]}")
    return table.sort_values("subject_id", key=lambda series: series.map(lambda item: tuple(natural_key(item)))).reset_index(drop=True), feature_columns


def prediction_meta(spec: BaselineSpec, seed: int, fold: str, row: pd.Series) -> dict[str, Any]:
    return {
        "run_id": spec.run_id,
        "dataset": spec.display_dataset,
        "modality": spec.modality,
        "task": spec.task,
        "model": spec.model,
        "seed": int(seed),
        "fold": fold,
        "protocol_id": spec.protocol_id,
        "task_type": spec.task_type,
        "subject_id": row["subject_id"],
        "split": "validation",
        "audio_segment_count": int(row["audio_segment_count"]),
    }


def clip_predictions(y_pred: np.ndarray, train_target: pd.Series) -> tuple[np.ndarray, int, tuple[float, float]]:
    bounds = (
        float(pd.to_numeric(train_target, errors="raise").min()),
        float(pd.to_numeric(train_target, errors="raise").max()),
    )
    arr = np.asarray(y_pred, dtype=np.float64)
    clipped = np.clip(arr, bounds[0], bounds[1])
    clip_count = int(np.sum(np.abs(clipped - arr) > 1.0e-12))
    return clipped, clip_count, bounds


def run_spec(spec: BaselineSpec, split_path: Path, out_dir: Path, force_features: bool) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    folds = load_protocol_splits(split_path, spec)
    split_subjects = {subject for roles in folds.values() for values in roles.values() for subject in values}
    features = extract_subject_features(spec.dataset_id, split_subjects, out_dir, force=force_features)
    table, feature_columns = build_subject_table(spec, features)
    table_by_subject = table.set_index("subject_id", drop=False)
    predictions: list[dict[str, Any]] = []
    fold_summaries: list[dict[str, Any]] = []

    for seed in SEEDS:
        for fold, roles in folds.items():
            train = table_by_subject.loc[roles["train"]].reset_index(drop=True)
            validation = table_by_subject.loc[roles["validation"]].reset_index(drop=True)
            if spec.task_type == "binary_classification":
                model = Pipeline(
                    [
                        ("imputer", SimpleImputer(strategy="median")),
                        ("scaler", StandardScaler()),
                        (
                            "svm",
                            SVC(
                                C=FIXED_SVM_C,
                                kernel="linear",
                                class_weight="balanced",
                                probability=True,
                                random_state=seed,
                            ),
                        ),
                    ]
                )
                model.fit(train[feature_columns], train[spec.target].astype(int))
                y_pred = model.predict(validation[feature_columns])
                y_score = model.predict_proba(validation[feature_columns])[:, 1]
                for idx, row in validation.iterrows():
                    predictions.append(
                        {
                            **prediction_meta(spec, seed, fold, row),
                            "y_true": int(row[spec.target]),
                            "y_pred": int(y_pred[idx]),
                            "y_score": float(y_score[idx]),
                        }
                    )
                fold_summaries.append(
                    {
                        "run_id": spec.run_id,
                        "seed": int(seed),
                        "fold": fold,
                        "svm_c": float(FIXED_SVM_C),
                        "train_subjects": int(len(train)),
                        "validation_subjects": int(len(validation)),
                        "train_positive_subjects": int(train[spec.target].astype(int).sum()),
                        "validation_positive_subjects": int(validation[spec.target].astype(int).sum()),
                    }
                )
            elif spec.task_type == "severity_regression":
                model = Pipeline(
                    [
                        ("imputer", SimpleImputer(strategy="median")),
                        ("scaler", StandardScaler()),
                        ("svr", SVR(C=FIXED_SVR_C, epsilon=FIXED_SVR_EPSILON, kernel="linear")),
                    ]
                )
                model.fit(train[feature_columns], train[spec.target].to_numpy(dtype=np.float64))
                y_pred_raw = model.predict(validation[feature_columns])
                y_pred, clip_count, bounds = clip_predictions(y_pred_raw, train[spec.target])
                for idx, row in validation.iterrows():
                    predictions.append(
                        {
                            **prediction_meta(spec, seed, fold, row),
                            "y_true": float(row[spec.target]),
                            "y_pred": float(y_pred[idx]),
                            "y_score": "",
                        }
                    )
                fold_summaries.append(
                    {
                        "run_id": spec.run_id,
                        "seed": int(seed),
                        "fold": fold,
                        "svr_c": float(FIXED_SVR_C),
                        "svr_epsilon": float(FIXED_SVR_EPSILON),
                        "train_subjects": int(len(train)),
                        "validation_subjects": int(len(validation)),
                        "train_target_min": float(bounds[0]),
                        "train_target_max": float(bounds[1]),
                        "validation_clip_count": int(clip_count),
                    }
                )
            else:
                raise ValueError(f"unsupported task type for {spec.run_id}: {spec.task_type}")

    subject_overlap_violations = 0
    for fold, roles in folds.items():
        subject_overlap_violations += int(bool(set(roles["train"]) & set(roles["validation"])))
    return predictions, {
        "run_id": spec.run_id,
        "dataset_id": spec.dataset_id,
        "dataset": spec.display_dataset,
        "target": spec.target,
        "protocol_id": spec.protocol_id,
        "subject_count": int(len(split_subjects)),
        "fold_count": int(len(folds)),
        "subject_overlap_violations": int(subject_overlap_violations),
        "feature_count": int(len(feature_columns)),
        "audio_segment_count_min": int(table["audio_segment_count"].min()),
        "audio_segment_count_max": int(table["audio_segment_count"].max()),
        "fold_summaries": fold_summaries,
    }


def write_report(out_dir: Path, summary: dict[str, Any]) -> None:
    dataset_ids = sorted({str(row["dataset_id"]) for row in summary["run_summaries"]})
    feature_files = [f"- `{dataset_id}_egemaps_subject_features.csv`" for dataset_id in dataset_ids]
    segment_files = [f"- `{dataset_id}_egemaps_segment_features.csv`" for dataset_id in dataset_ids]
    lines = [
        "# CMDC/PDCH Audio eGeMAPS Phase 2 Baselines",
        "",
        f"Generated: `{summary['generated_at']}`",
        "",
        "## Protocol",
        "",
        "- Input interface: manifest-resolved `audio_path` values and `datasets/splits/phase2_subject_splits.csv`.",
        "- Feature extractor: openSMILE eGeMAPSv02 functionals.",
        "- Unit of prediction: one row per subject per seed after outer subject-level CV.",
        "- Feature aggregation: segment eGeMAPS functionals aggregated per subject with mean, std, min, and max.",
        "- Hyperparameters are fixed a priori; no validation or test labels are used for tuning.",
        "- Regression outputs are clipped to the train-fold observed target range.",
        "- No test split is used.",
        "- Raw audio and source paths are not written to outputs.",
        "",
        "## Audit",
        "",
        f"- Runs: `{summary['runs']}`",
        f"- Seeds: `{summary['seeds']}`",
        f"- Bootstrap resamples: `{summary['bootstrap_resamples']}`",
        f"- Prediction rows: `{summary['prediction_rows']}`",
        f"- Subject overlap violations: `{summary['subject_overlap_violations']}`",
        f"- Raw audio written: `{summary['raw_audio_written']}`",
        f"- Source paths written: `{summary['source_paths_written']}`",
        "",
        "## Output Files",
        "",
        "- `cmdc_pdch_audio_egemaps_predictions.csv`",
        *feature_files,
        *segment_files,
        "- `phase2_metrics_by_seed.csv`",
        "- `phase2_metric_summary.csv`",
        "- `cmdc_pdch_audio_egemaps_run_summary.json`",
    ]
    (out_dir / "cmdc_pdch_audio_egemaps_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--split-path", type=Path, default=SPLIT_PATH)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--bootstrap-resamples", type=int, default=1000)
    parser.add_argument("--force-features", action="store_true")
    parser.add_argument("--run-id", action="append", choices=[spec.run_id for spec in SPECS])
    args = parser.parse_args()

    args.out_dir.mkdir(parents=True, exist_ok=True)
    all_predictions: list[dict[str, Any]] = []
    run_summaries: list[dict[str, Any]] = []
    selected_specs = [spec for spec in SPECS if not args.run_id or spec.run_id in set(args.run_id)]
    for spec in selected_specs:
        predictions, run_summary = run_spec(spec, args.split_path, args.out_dir, args.force_features)
        all_predictions.extend(predictions)
        run_summaries.append(run_summary)

    predictions_frame = pd.DataFrame(all_predictions)
    predictions_path = args.out_dir / "cmdc_pdch_audio_egemaps_predictions.csv"
    predictions_frame.to_csv(predictions_path, index=False)

    metrics_by_seed, metric_summary = metric_records(
        predictions_frame,
        bootstrap_resamples=args.bootstrap_resamples,
        seed=20260727,
    )
    metrics_by_seed.to_csv(args.out_dir / "phase2_metrics_by_seed.csv", index=False)
    metric_summary.to_csv(args.out_dir / "phase2_metric_summary.csv", index=False)

    subject_overlap_violations = int(sum(row["subject_overlap_violations"] for row in run_summaries))
    run_summary = {
        "generated_at": utc_now(),
        "manifest_dir": str(MANIFEST_DIR),
        "split_path": str(args.split_path),
        "feature_set": "openSMILE eGeMAPSv02 Functionals",
        "opensmile_version": str(opensmile.__version__),
        "runs": [spec.run_id for spec in selected_specs],
        "seeds": SEEDS,
        "seed_count": len(SEEDS),
        "bootstrap_resamples": int(args.bootstrap_resamples),
        "prediction_rows": int(len(predictions_frame)),
        "run_summaries": run_summaries,
        "subject_overlap_violations": subject_overlap_violations,
        "no_test_split_used": True,
        "raw_audio_written": False,
        "source_paths_written": False,
    }
    (args.out_dir / "cmdc_pdch_audio_egemaps_run_summary.json").write_text(
        json.dumps(run_summary, indent=2, ensure_ascii=True, sort_keys=True),
        encoding="utf-8",
    )
    write_report(args.out_dir, run_summary)
    print(f"Wrote {predictions_path}")
    print(f"Wrote {args.out_dir / 'phase2_metric_summary.csv'}")


if __name__ == "__main__":
    main()
