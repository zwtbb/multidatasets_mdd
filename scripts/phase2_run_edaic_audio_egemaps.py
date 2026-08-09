#!/usr/bin/env python3
"""Run Phase 2 E-DAIC audio eGeMAPS baselines.

The runner uses manifest-resolved E-DAIC subject rows and the official local
openSMILE eGeMAPS frame-level feature files derived from those subject folders.
It fits only on the official train split, evaluates on the official dev split,
and writes prediction/metric artifacts without persisting raw audio or paths.
"""

from __future__ import annotations

import argparse
import json
import os
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
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.svm import SVC, SVR

from phase2_metrics import metric_records


ROOT = Path("/root/autodl-tmp")
MANIFEST_PATH = ROOT / "datasets" / "manifests" / "edaic_subjects.csv"
DEFAULT_OUT_DIR = ROOT / "analysis" / "phase2_baselines" / "edaic_audio_egemaps"
SEEDS = [0, 1, 2, 3, 4]
FIXED_SVM_C = 1.0
FIXED_SVR_C = 1.0
FIXED_SVR_EPSILON = 0.1
STATS = ["mean", "std", "min", "max"]


@dataclass(frozen=True)
class BaselineSpec:
    run_id: str
    dataset: str
    modality: str
    task: str
    task_type: str
    target: str
    model: str


REGRESSION_SPEC = BaselineSpec(
    run_id="edaic_audio_phq8_egemaps_svr",
    dataset="E-DAIC",
    modality="Audio",
    task="PHQ-8 regression",
    task_type="severity_regression",
    target="phq8_total",
    model="eGeMAPS + SVR",
)


CLASSIFICATION_SPEC = BaselineSpec(
    run_id="edaic_audio_binary_egemaps_svm",
    dataset="E-DAIC",
    modality="Audio",
    task="binary depression classification",
    task_type="binary_classification",
    target="binary_label",
    model="eGeMAPS + SVM",
)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def feature_path_from_manifest_row(row: pd.Series) -> Path:
    audio_path = Path(str(row["audio_path"]))
    subject_id = str(row["subject_id"])
    return audio_path.parent / "features" / f"{subject_id}_OpenSMILE2.3.0_egemaps.csv"


def read_frame_features(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"E-DAIC eGeMAPS feature file missing: {path}")
    frame = pd.read_csv(path, sep=";")
    if frame.empty:
        raise ValueError(f"E-DAIC eGeMAPS feature file is empty: {path}")
    numeric = frame.drop(columns=[column for column in ["name", "frameTime"] if column in frame.columns])
    numeric = numeric.apply(pd.to_numeric, errors="coerce").replace([np.inf, -np.inf], np.nan)
    if numeric.shape[1] == 0:
        raise ValueError(f"E-DAIC eGeMAPS feature file has no numeric columns: {path}")
    return numeric


def summarize_frame_features(path: Path) -> tuple[dict[str, float], int, list[str]]:
    frame = read_frame_features(path)
    columns = [str(column) for column in frame.columns]
    values = frame.to_numpy(dtype=np.float64)
    with np.errstate(invalid="ignore"):
        stat_values = {
            "mean": np.nanmean(values, axis=0),
            "std": np.nanstd(values, axis=0),
            "min": np.nanmin(values, axis=0),
            "max": np.nanmax(values, axis=0),
        }
    summary: dict[str, float] = {}
    for stat_name in STATS:
        for feature_name, value in zip(columns, stat_values[stat_name], strict=True):
            summary[f"{feature_name}__{stat_name}"] = float(value) if np.isfinite(value) else np.nan
    return summary, int(len(frame)), columns


def read_manifest(manifest_path: Path) -> pd.DataFrame:
    manifest = pd.read_csv(manifest_path)
    required = {
        "subject_id",
        "audio_path",
        "phq8_total",
        "binary_label",
        "official_split",
        "file_valid",
    }
    missing = required - set(manifest.columns)
    if missing:
        raise ValueError(f"E-DAIC manifest missing columns: {', '.join(sorted(missing))}")
    usable = manifest[
        (manifest["file_valid"].fillna(False).astype(bool))
        & manifest["audio_path"].notna()
        & manifest["phq8_total"].notna()
        & manifest["binary_label"].notna()
        & manifest["official_split"].isin(["train", "dev"])
    ].copy()
    if usable.empty:
        raise ValueError("no usable E-DAIC train/dev manifest rows")
    if usable["subject_id"].duplicated().any():
        dupes = sorted(usable.loc[usable["subject_id"].duplicated(), "subject_id"].astype(str).unique())
        raise ValueError(f"E-DAIC manifest should have one row per subject, duplicates observed: {dupes[:10]}")
    usable["subject_id"] = usable["subject_id"].astype(str)
    return usable.sort_values("subject_id").reset_index(drop=True)


def extract_subject_features(manifest: pd.DataFrame, out_dir: Path, force: bool = False) -> pd.DataFrame:
    cache_path = out_dir / "edaic_egemaps_subject_features.csv"
    subjects = set(manifest["subject_id"].astype(str))
    if cache_path.exists() and not force:
        cached = pd.read_csv(cache_path)
        cached["subject_id"] = cached["subject_id"].astype(str)
        cached_subjects = set(cached["subject_id"])
        if subjects.issubset(cached_subjects):
            print("Using cached E-DAIC subject-level eGeMAPS features", flush=True)
            return cached[cached["subject_id"].isin(subjects)].copy()

    out_dir.mkdir(parents=True, exist_ok=True)
    rows: list[dict[str, Any]] = []
    expected_low_level_columns: list[str] | None = None
    for idx, row in manifest.iterrows():
        feature_path = feature_path_from_manifest_row(row)
        summary, frame_count, low_level_columns = summarize_frame_features(feature_path)
        if expected_low_level_columns is None:
            expected_low_level_columns = low_level_columns
        elif low_level_columns != expected_low_level_columns:
            raise ValueError(f"E-DAIC eGeMAPS feature columns changed for subject {row['subject_id']}")
        rows.append(
            {
                "subject_id": str(row["subject_id"]),
                "frame_count": int(frame_count),
                **summary,
            }
        )
        if (idx + 1) % 25 == 0:
            print(f"  summarized {idx + 1}/{len(manifest)} E-DAIC subjects", flush=True)
    features = pd.DataFrame(rows).sort_values("subject_id").reset_index(drop=True)
    features.to_csv(cache_path, index=False)
    print(f"Wrote {cache_path}", flush=True)
    return features


def build_subject_table(manifest_path: Path, out_dir: Path, force_features: bool = False) -> pd.DataFrame:
    manifest = read_manifest(manifest_path)
    features = extract_subject_features(manifest, out_dir, force=force_features)
    table = manifest[["subject_id", "official_split", "phq8_total", "binary_label"]].merge(
        features,
        on="subject_id",
        how="inner",
        validate="one_to_one",
    )
    if len(table) != len(manifest):
        missing = sorted(set(manifest["subject_id"]) - set(table["subject_id"]))
        raise ValueError(f"E-DAIC subjects missing eGeMAPS features after merge: {missing[:10]}")
    table = table.rename(columns={"official_split": "split"}).sort_values("subject_id").reset_index(drop=True)
    split_counts = table["split"].value_counts().to_dict()
    if split_counts.get("train", 0) <= 0 or split_counts.get("dev", 0) <= 0:
        raise ValueError(f"E-DAIC split must contain train and dev subjects, observed {split_counts}")
    train_subjects = set(table.loc[table["split"] == "train", "subject_id"])
    dev_subjects = set(table.loc[table["split"] == "dev", "subject_id"])
    overlap = sorted(train_subjects & dev_subjects)
    if overlap:
        raise ValueError(f"subject-level train/dev overlap detected: {overlap[:10]}")
    return table


def feature_columns(table: pd.DataFrame) -> list[str]:
    excluded = {"subject_id", "split", "phq8_total", "binary_label", "frame_count"}
    columns = [column for column in table.columns if column not in excluded]
    if not columns:
        raise ValueError("no eGeMAPS model feature columns available")
    return columns


def prediction_meta(spec: BaselineSpec, seed: int, row: pd.Series) -> dict[str, Any]:
    return {
        "run_id": spec.run_id,
        "dataset": spec.dataset,
        "modality": spec.modality,
        "task": spec.task,
        "model": spec.model,
        "seed": int(seed),
        "task_type": spec.task_type,
        "subject_id": row["subject_id"],
        "split": row["split"],
        "frame_count": int(row["frame_count"]),
    }


def run_seed(table: pd.DataFrame, seed: int) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    train = table[table["split"] == "train"].reset_index(drop=True)
    dev = table[table["split"] == "dev"].reset_index(drop=True)
    columns = feature_columns(table)
    x_train = train[columns].to_numpy(dtype=np.float64)
    x_dev = dev[columns].to_numpy(dtype=np.float64)

    regression_model = Pipeline(
        [
            ("imputer", SimpleImputer(strategy="median")),
            ("scaler", StandardScaler()),
            ("svr", SVR(C=FIXED_SVR_C, epsilon=FIXED_SVR_EPSILON, kernel="linear")),
        ]
    )
    regression_model.fit(x_train, train["phq8_total"].to_numpy(dtype=np.float64))
    raw_regression_pred = regression_model.predict(x_dev)
    clip_low = float(train["phq8_total"].min())
    clip_high = float(train["phq8_total"].max())
    regression_pred = np.clip(raw_regression_pred, clip_low, clip_high)

    classification_model = Pipeline(
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
    classification_model.fit(x_train, train["binary_label"].astype(int))
    class_pred = classification_model.predict(x_dev)
    class_score = classification_model.predict_proba(x_dev)[:, 1]

    predictions: list[dict[str, Any]] = []
    for idx, row in dev.iterrows():
        predictions.append(
            {
                **prediction_meta(REGRESSION_SPEC, seed, row),
                "y_true": float(row["phq8_total"]),
                "y_pred": float(regression_pred[idx]),
                "y_score": "",
            }
        )
        predictions.append(
            {
                **prediction_meta(CLASSIFICATION_SPEC, seed, row),
                "y_true": int(row["binary_label"]),
                "y_pred": int(class_pred[idx]),
                "y_score": float(class_score[idx]),
            }
        )

    train_subjects = set(train["subject_id"].astype(str))
    dev_subjects = set(dev["subject_id"].astype(str))
    return predictions, {
        "seed": int(seed),
        "train_subjects": int(len(train)),
        "dev_subjects": int(len(dev)),
        "train_positive_subjects": int(train["binary_label"].astype(int).sum()),
        "dev_positive_subjects": int(dev["binary_label"].astype(int).sum()),
        "svr_c": float(FIXED_SVR_C),
        "svr_epsilon": float(FIXED_SVR_EPSILON),
        "svm_c": float(FIXED_SVM_C),
        "clip_low": float(clip_low),
        "clip_high": float(clip_high),
        "clipped_regression_predictions": int(np.sum((raw_regression_pred < clip_low) | (raw_regression_pred > clip_high))),
        "subject_overlap": int(len(train_subjects & dev_subjects)),
    }


def write_report(out_dir: Path, summary: dict[str, Any]) -> None:
    lines = [
        "# E-DAIC Audio eGeMAPS Phase 2 Baselines",
        "",
        f"Generated: `{summary['generated_at']}`",
        "",
        "## Protocol",
        "",
        "- Input interface: manifest-resolved E-DAIC `audio_path` values and subject folders.",
        "- Acoustic source: local official `OpenSMILE2.3.0_egemaps.csv` frame-level files.",
        "- Feature aggregation: subject-level mean, std, min, and max over frame-level eGeMAPS columns.",
        "- Unit of prediction: one row per dev subject per seed.",
        "- Hyperparameters are fixed a priori; no dev or test labels are used for tuning.",
        "- No test split is used.",
        "- Raw audio and source paths are not written to outputs.",
        "",
        "## Audit",
        "",
        f"- Runs: `{summary['runs']}`",
        f"- Seeds: `{summary['seeds']}`",
        f"- Bootstrap resamples: `{summary['bootstrap_resamples']}`",
        f"- Prediction rows: `{summary['prediction_rows']}`",
        f"- Train subjects: `{summary['train_subjects']}`",
        f"- Dev subjects: `{summary['dev_subjects']}`",
        f"- Feature columns: `{summary['feature_columns']}`",
        f"- Subject overlap violations: `{summary['subject_overlap_violations']}`",
        f"- Raw audio written: `{summary['raw_audio_written']}`",
        f"- Source paths written: `{summary['source_paths_written']}`",
        "",
        "## Output Files",
        "",
        "- `edaic_audio_egemaps_predictions.csv`",
        "- `edaic_egemaps_subject_features.csv`",
        "- `phase2_metrics_by_seed.csv`",
        "- `phase2_metric_summary.csv`",
        "- `edaic_audio_egemaps_run_summary.json`",
    ]
    (out_dir / "edaic_audio_egemaps_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest-path", type=Path, default=MANIFEST_PATH)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--bootstrap-resamples", type=int, default=1000)
    parser.add_argument("--force-features", action="store_true")
    args = parser.parse_args()

    table = build_subject_table(args.manifest_path, args.out_dir, force_features=args.force_features)
    all_predictions: list[dict[str, Any]] = []
    seed_summaries: list[dict[str, Any]] = []
    for seed in SEEDS:
        predictions, seed_summary = run_seed(table, seed)
        all_predictions.extend(predictions)
        seed_summaries.append(seed_summary)

    args.out_dir.mkdir(parents=True, exist_ok=True)
    predictions_frame = pd.DataFrame(all_predictions)
    predictions_path = args.out_dir / "edaic_audio_egemaps_predictions.csv"
    predictions_frame.to_csv(predictions_path, index=False)

    metrics_by_seed, metric_summary = metric_records(
        predictions_frame,
        bootstrap_resamples=args.bootstrap_resamples,
        seed=20260727,
    )
    metrics_by_seed.to_csv(args.out_dir / "phase2_metrics_by_seed.csv", index=False)
    metric_summary.to_csv(args.out_dir / "phase2_metric_summary.csv", index=False)

    columns = feature_columns(table)
    train = table[table["split"] == "train"]
    dev = table[table["split"] == "dev"]
    summary = {
        "generated_at": utc_now(),
        "manifest_path": str(args.manifest_path),
        "runs": [REGRESSION_SPEC.run_id, CLASSIFICATION_SPEC.run_id],
        "seeds": SEEDS,
        "seed_count": len(SEEDS),
        "bootstrap_resamples": int(args.bootstrap_resamples),
        "prediction_rows": int(len(predictions_frame)),
        "train_subjects": int(len(train)),
        "dev_subjects": int(len(dev)),
        "test_subjects_used": 0,
        "train_positive_subjects": int(train["binary_label"].astype(int).sum()),
        "dev_positive_subjects": int(dev["binary_label"].astype(int).sum()),
        "feature_columns": int(len(columns)),
        "low_level_feature_columns": int(len(columns) / len(STATS)),
        "frame_count_min": int(table["frame_count"].min()),
        "frame_count_max": int(table["frame_count"].max()),
        "frame_count_mean": float(table["frame_count"].mean()),
        "feature_aggregation": "mean/std/min/max over frame-level eGeMAPS columns",
        "frame_count_used_as_model_feature": False,
        "subject_overlap_violations": int(sum(row["subject_overlap"] for row in seed_summaries)),
        "no_test_split_used": True,
        "raw_audio_written": False,
        "source_paths_written": False,
        "seed_summaries": seed_summaries,
    }
    (args.out_dir / "edaic_audio_egemaps_run_summary.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=True, sort_keys=True),
        encoding="utf-8",
    )
    write_report(args.out_dir, summary)
    print(f"Wrote {predictions_path}")
    print(f"Wrote {args.out_dir / 'phase2_metric_summary.csv'}")


if __name__ == "__main__":
    main()
