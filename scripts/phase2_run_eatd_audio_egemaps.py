#!/usr/bin/env python3
"""Run Phase 2 EATD audio eGeMAPS baseline.

The runner extracts openSMILE eGeMAPSv02 functionals from manifest-resolved
positive/neutral/negative EATD audio paths, aggregates them to one subject row
with valence-prefixed features, and evaluates the official validation split. It
writes no raw audio or source paths.
"""

from __future__ import annotations

import argparse
import json
import os
import warnings
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
from sklearn.svm import SVR

from phase2_metrics import metric_records


ROOT = Path("/root/autodl-tmp")
MANIFEST_PATH = ROOT / "datasets" / "manifests" / "eatd_subjects.csv"
DEFAULT_OUT_DIR = ROOT / "analysis" / "phase2_baselines" / "eatd_audio_egemaps"
RUN_ID = "eatd_audio_sds_egemaps_svr"
SEEDS = [0, 1, 2, 3, 4]
VALENCE_ORDER = ["positive", "neutral", "negative"]
FIXED_SVR_C = 1.0
FIXED_SVR_EPSILON = 0.1


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def read_manifest(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"manifest missing: {path}")
    return pd.read_csv(path)


def build_segment_table(manifest_path: Path) -> pd.DataFrame:
    manifest = read_manifest(manifest_path)
    required = {"subject_id", "valence", "audio_path", "sds_total", "official_split", "file_valid"}
    missing = required - set(manifest.columns)
    if missing:
        raise ValueError(f"EATD manifest missing columns: {', '.join(sorted(missing))}")
    usable = manifest[
        manifest["file_valid"].fillna(False).astype(bool)
        & manifest["audio_path"].notna()
        & manifest["sds_total"].notna()
        & manifest["official_split"].isin(["train", "validation"])
        & manifest["valence"].isin(VALENCE_ORDER)
    ].copy()
    rows: list[dict[str, Any]] = []
    for subject_id, group in usable.groupby("subject_id", sort=True):
        by_valence = {str(row["valence"]): row for _, row in group.iterrows()}
        missing_valences = [valence for valence in VALENCE_ORDER if valence not in by_valence]
        if missing_valences:
            raise ValueError(f"{subject_id} missing audio valence rows: {missing_valences}")
        label_values = group["sds_total"].dropna().unique()
        split_values = group["official_split"].dropna().unique()
        if len(label_values) != 1 or len(split_values) != 1:
            raise ValueError(f"{subject_id} has inconsistent labels/splits")
        for valence in VALENCE_ORDER:
            row = by_valence[valence]
            rows.append(
                {
                    "subject_id": str(subject_id),
                    "split": str(split_values[0]),
                    "valence": valence,
                    "sds_total": float(label_values[0]),
                    "audio_path": str(row["audio_path"]),
                }
            )
    table = pd.DataFrame(rows).sort_values(["subject_id", "valence"]).reset_index(drop=True)
    if table.empty:
        raise ValueError("no usable EATD audio rows")
    split_counts = table.drop_duplicates("subject_id")["split"].value_counts().to_dict()
    if split_counts.get("train", 0) <= 0 or split_counts.get("validation", 0) <= 0:
        raise ValueError(f"EATD split must contain train and validation subjects, observed {split_counts}")
    train_subjects = set(table.loc[table["split"] == "train", "subject_id"])
    validation_subjects = set(table.loc[table["split"] == "validation", "subject_id"])
    overlap = sorted(train_subjects & validation_subjects)
    if overlap:
        raise ValueError(f"subject-level split overlap detected: {overlap[:10]}")
    return table


def save_segment_cache(path: Path, rows: list[dict[str, Any]]) -> None:
    frame = pd.DataFrame(rows)
    if not frame.empty:
        frame = frame.sort_values(["subject_id", "valence"]).reset_index(drop=True)
    frame.to_csv(path, index=False)


def extract_segment_features(segment_table: pd.DataFrame, out_dir: Path, force: bool = False) -> pd.DataFrame:
    cache_path = out_dir / "eatd_egemaps_segment_features.csv"
    required_keys = set(zip(segment_table["subject_id"], segment_table["valence"], strict=True))
    cached_rows: list[dict[str, Any]] = []
    cached_keys: set[tuple[str, str]] = set()
    if cache_path.exists() and not force:
        cached = pd.read_csv(cache_path)
        cached["subject_id"] = cached["subject_id"].astype(str)
        cached["valence"] = cached["valence"].astype(str)
        cached_keys = set(zip(cached["subject_id"], cached["valence"], strict=True))
        cached_rows = cached[
            [
                key in required_keys
                for key in zip(cached["subject_id"], cached["valence"], strict=True)
            ]
        ].to_dict("records")
    missing_rows = segment_table[
        [
            key not in cached_keys
            for key in zip(segment_table["subject_id"], segment_table["valence"], strict=True)
        ]
    ].reset_index(drop=True)

    smile = opensmile.Smile(
        feature_set=opensmile.FeatureSet.eGeMAPSv02,
        feature_level=opensmile.FeatureLevel.Functionals,
    )
    feature_rows = cached_rows
    feature_columns: list[str] | None = None
    if feature_rows:
        feature_columns = [
            column
            for column in pd.DataFrame(feature_rows).columns
            if column not in {"subject_id", "split", "valence", "sds_total"}
        ]
    print(
        f"Extracting EATD eGeMAPS: {len(missing_rows)} missing / {len(segment_table)} audio segments",
        flush=True,
    )
    warnings.filterwarnings("ignore", message="Segment too short.*")
    for idx, row in missing_rows.iterrows():
        path = Path(str(row["audio_path"]))
        if not path.exists():
            raise FileNotFoundError(f"manifest audio path missing: {path}")
        if (idx + 1) == 1 or (idx + 1) % 25 == 0 or (idx + 1) == len(missing_rows):
            print(f"  [eatd] {idx + 1}/{len(missing_rows)} subject={row['subject_id']} valence={row['valence']}", flush=True)
        features = smile.process_file(str(path))
        if features.empty:
            raise ValueError(f"openSMILE returned no features for {path}")
        values = features.iloc[0]
        if feature_columns is None:
            feature_columns = [str(column) for column in values.index]
        feature_rows.append(
            {
                "subject_id": str(row["subject_id"]),
                "split": str(row["split"]),
                "valence": str(row["valence"]),
                "sds_total": float(row["sds_total"]),
                **{str(column): float(values[column]) for column in values.index},
            }
        )
        if (idx + 1) % 25 == 0:
            save_segment_cache(cache_path, feature_rows)
    if feature_columns is None:
        raise RuntimeError("no eGeMAPS features extracted")
    save_segment_cache(cache_path, feature_rows)
    features = pd.DataFrame(feature_rows)
    observed_keys = set(zip(features["subject_id"].astype(str), features["valence"].astype(str), strict=True))
    missing_keys = required_keys - observed_keys
    if missing_keys:
        raise ValueError(f"missing cached eGeMAPS rows: {sorted(missing_keys)[:5]}")
    return features


def aggregate_subject_features(segment_features: pd.DataFrame) -> tuple[pd.DataFrame, list[str]]:
    feature_columns = [
        column
        for column in segment_features.columns
        if column not in {"subject_id", "split", "valence", "sds_total"}
    ]
    rows: list[dict[str, Any]] = []
    for subject_id, group in segment_features.groupby("subject_id", sort=True):
        by_valence = {str(row["valence"]): row for _, row in group.iterrows()}
        missing_valences = [valence for valence in VALENCE_ORDER if valence not in by_valence]
        if missing_valences:
            raise ValueError(f"{subject_id} missing cached valence rows: {missing_valences}")
        splits = group["split"].dropna().unique()
        labels = group["sds_total"].dropna().unique()
        if len(splits) != 1 or len(labels) != 1:
            raise ValueError(f"{subject_id} has inconsistent cached split/label")
        row: dict[str, Any] = {
            "subject_id": str(subject_id),
            "split": str(splits[0]),
            "sds_total": float(labels[0]),
            "audio_segment_count": int(len(group)),
        }
        values_by_valence = []
        for valence in VALENCE_ORDER:
            values = by_valence[valence][feature_columns].to_numpy(dtype=np.float64)
            values_by_valence.append(values)
            for feature_name, feature_value in zip(feature_columns, values, strict=True):
                row[f"{valence}__{feature_name}"] = float(feature_value) if np.isfinite(feature_value) else np.nan
        stacked = np.vstack(values_by_valence)
        with np.errstate(invalid="ignore"):
            mean_values = np.nanmean(stacked, axis=0)
            std_values = np.nanstd(stacked, axis=0)
        for feature_name, feature_value in zip(feature_columns, mean_values, strict=True):
            row[f"all_valence_mean__{feature_name}"] = float(feature_value) if np.isfinite(feature_value) else np.nan
        for feature_name, feature_value in zip(feature_columns, std_values, strict=True):
            row[f"all_valence_std__{feature_name}"] = float(feature_value) if np.isfinite(feature_value) else np.nan
        rows.append(row)
    subject_features = pd.DataFrame(rows).sort_values("subject_id").reset_index(drop=True)
    model_feature_columns = [
        column
        for column in subject_features.columns
        if column not in {"subject_id", "split", "sds_total", "audio_segment_count"}
    ]
    return subject_features, model_feature_columns


def prediction_meta(seed: int, row: pd.Series) -> dict[str, Any]:
    return {
        "run_id": RUN_ID,
        "dataset": "EATD-Corpus",
        "modality": "Audio",
        "task": "SDS regression",
        "model": "eGeMAPS + SVR",
        "seed": int(seed),
        "task_type": "severity_regression",
        "subject_id": row["subject_id"],
        "split": "validation",
        "audio_segment_count": int(row["audio_segment_count"]),
    }


def run_baseline(subject_features: pd.DataFrame, feature_columns: list[str]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    train = subject_features[subject_features["split"] == "train"].reset_index(drop=True)
    validation = subject_features[subject_features["split"] == "validation"].reset_index(drop=True)
    train_subjects = set(train["subject_id"].astype(str))
    validation_subjects = set(validation["subject_id"].astype(str))
    overlap = sorted(train_subjects & validation_subjects)
    if overlap:
        raise ValueError(f"subject-level split overlap detected: {overlap[:10]}")
    predictions: list[dict[str, Any]] = []
    seed_summaries: list[dict[str, Any]] = []
    for seed in SEEDS:
        model = Pipeline(
            [
                ("imputer", SimpleImputer(strategy="median")),
                ("scaler", StandardScaler()),
                ("svr", SVR(C=FIXED_SVR_C, epsilon=FIXED_SVR_EPSILON, kernel="rbf")),
            ]
        )
        model.fit(train[feature_columns], train["sds_total"].to_numpy(dtype=np.float64))
        y_pred = model.predict(validation[feature_columns])
        for idx, row in validation.iterrows():
            predictions.append(
                {
                    **prediction_meta(seed, row),
                    "y_true": float(row["sds_total"]),
                    "y_pred": float(y_pred[idx]),
                    "y_score": "",
                }
            )
        seed_summaries.append(
            {
                "seed": int(seed),
                "svr_c": float(FIXED_SVR_C),
                "svr_epsilon": float(FIXED_SVR_EPSILON),
                "train_subjects": int(len(train)),
                "validation_subjects": int(len(validation)),
            }
        )
    return predictions, seed_summaries


def write_report(out_dir: Path, summary: dict[str, Any]) -> None:
    lines = [
        "# EATD Audio eGeMAPS Phase 2 Baseline",
        "",
        f"Generated: `{summary['generated_at']}`",
        "",
        "## Protocol",
        "",
        "- Input interface: manifest-resolved valid EATD audio paths.",
        "- Feature extractor: openSMILE eGeMAPSv02 functionals.",
        "- Subject features: positive, neutral, and negative valence eGeMAPS with all-valence mean/std aggregates.",
        "- Model: fixed-hyperparameter RBF SVR.",
        "- Evaluation split: official train/validation subject split.",
        "- No validation or test labels are used for hyperparameter selection.",
        "- No test split is used.",
        "- Raw audio and source paths are not written to outputs.",
        "",
        "## Audit",
        "",
        f"- Run: `{summary['runs']}`",
        f"- Train subjects: `{summary['train_subjects']}`",
        f"- Validation subjects: `{summary['validation_subjects']}`",
        f"- Subject overlap: `{summary['subject_overlap']}`",
        f"- Audio segments: `{summary['audio_segments']}`",
        f"- Seeds: `{summary['seeds']}`",
        f"- Bootstrap resamples: `{summary['bootstrap_resamples']}`",
        f"- Prediction rows: `{summary['prediction_rows']}`",
        f"- Raw audio written: `{summary['raw_audio_written']}`",
        f"- Source paths written: `{summary['source_paths_written']}`",
        "",
        "## Output Files",
        "",
        "- `eatd_audio_egemaps_predictions.csv`",
        "- `eatd_egemaps_segment_features.csv`",
        "- `eatd_egemaps_subject_features.csv`",
        "- `phase2_metrics_by_seed.csv`",
        "- `phase2_metric_summary.csv`",
        "- `eatd_audio_egemaps_run_summary.json`",
    ]
    (out_dir / "eatd_audio_egemaps_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, default=MANIFEST_PATH)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--bootstrap-resamples", type=int, default=1000)
    parser.add_argument("--force-features", action="store_true")
    args = parser.parse_args()

    args.out_dir.mkdir(parents=True, exist_ok=True)
    segment_table = build_segment_table(args.manifest)
    segment_features = extract_segment_features(segment_table, args.out_dir, force=args.force_features)
    subject_features, feature_columns = aggregate_subject_features(segment_features)
    subject_features.to_csv(args.out_dir / "eatd_egemaps_subject_features.csv", index=False)

    predictions, seed_summaries = run_baseline(subject_features, feature_columns)
    predictions_frame = pd.DataFrame(predictions)
    predictions_path = args.out_dir / "eatd_audio_egemaps_predictions.csv"
    predictions_frame.to_csv(predictions_path, index=False)

    metrics_by_seed, metric_summary = metric_records(
        predictions_frame,
        bootstrap_resamples=args.bootstrap_resamples,
        seed=20260727,
    )
    metrics_by_seed.to_csv(args.out_dir / "phase2_metrics_by_seed.csv", index=False)
    metric_summary.to_csv(args.out_dir / "phase2_metric_summary.csv", index=False)

    train_subjects = set(subject_features.loc[subject_features["split"] == "train", "subject_id"].astype(str))
    validation_subjects = set(subject_features.loc[subject_features["split"] == "validation", "subject_id"].astype(str))
    run_summary = {
        "generated_at": utc_now(),
        "manifest": str(args.manifest),
        "feature_set": "openSMILE eGeMAPSv02 Functionals",
        "opensmile_version": str(opensmile.__version__),
        "runs": [RUN_ID],
        "seeds": SEEDS,
        "seed_count": len(SEEDS),
        "bootstrap_resamples": int(args.bootstrap_resamples),
        "train_subjects": int(len(train_subjects)),
        "validation_subjects": int(len(validation_subjects)),
        "subject_overlap": int(len(train_subjects & validation_subjects)),
        "audio_segments": int(len(segment_table)),
        "subject_feature_rows": int(len(subject_features)),
        "feature_count": int(len(feature_columns)),
        "prediction_rows": int(len(predictions_frame)),
        "seed_summaries": seed_summaries,
        "no_test_split_used": True,
        "raw_audio_written": False,
        "source_paths_written": False,
    }
    (args.out_dir / "eatd_audio_egemaps_run_summary.json").write_text(
        json.dumps(run_summary, indent=2, ensure_ascii=True, sort_keys=True),
        encoding="utf-8",
    )
    write_report(args.out_dir, run_summary)
    print(f"Wrote {predictions_path}")
    print(f"Wrote {args.out_dir / 'phase2_metric_summary.csv'}")


if __name__ == "__main__":
    main()
