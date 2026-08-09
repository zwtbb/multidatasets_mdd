#!/usr/bin/env python3
"""Run the Phase 2 MODMA audio eGeMAPS baseline.

The runner extracts openSMILE eGeMAPSv02 functionals from manifest-resolved
valid MODMA audio paths, aggregates segment features to one subject row, and
evaluates the generated subject-level binary CV protocol. It writes no raw
audio, source paths, or file names.
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
from sklearn.svm import SVC

from phase2_metrics import metric_records


ROOT = Path("/root/autodl-tmp")
MANIFEST_PATH = ROOT / "datasets" / "manifests" / "modma_subjects.csv"
SPLIT_PATH = ROOT / "datasets" / "splits" / "phase2_subject_splits.csv"
DEFAULT_OUT_DIR = ROOT / "analysis" / "phase2_baselines" / "modma_audio_egemaps"
SEEDS = [0, 1, 2, 3, 4]
RUN_ID = "modma_audio_binary_egemaps_svm"
PROTOCOL_ID = "modma_binary_subject_cv"
FIXED_SVM_C = 1.0


@dataclass(frozen=True)
class BaselineSpec:
    run_id: str
    dataset: str
    modality: str
    task: str
    task_type: str
    target: str
    model: str
    protocol_id: str


SPEC = BaselineSpec(
    run_id=RUN_ID,
    dataset="MODMA",
    modality="Audio",
    task="binary depression classification",
    task_type="binary_classification",
    target="binary_label",
    model="eGeMAPS + SVM",
    protocol_id=PROTOCOL_ID,
)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def natural_key(value: Any) -> list[Any]:
    return [int(part) if part.isdigit() else part for part in re.split(r"(\d+)", str(value))]


def read_manifest(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"manifest missing: {path}")
    return pd.read_csv(path)


def load_protocol_splits(split_path: Path) -> dict[str, dict[str, list[str]]]:
    if not split_path.exists():
        raise FileNotFoundError(f"split layer missing: {split_path}")
    splits = pd.read_csv(split_path)
    required = {"dataset", "protocol_id", "target", "fold", "role", "subject_id"}
    missing = required - set(splits.columns)
    if missing:
        raise ValueError(f"split layer missing columns: {', '.join(sorted(missing))}")
    selected = splits[
        (splits["dataset"].astype(str) == "modma")
        & (splits["protocol_id"].astype(str) == PROTOCOL_ID)
        & (splits["target"].astype(str) == SPEC.target)
    ].copy()
    if selected.empty:
        raise ValueError(f"no split rows for {PROTOCOL_ID}")
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


def build_segment_table(manifest_path: Path, subjects: set[str]) -> pd.DataFrame:
    manifest = read_manifest(manifest_path)
    required = {"subject_id", "audio_path", "task_type", "segment_id", SPEC.target}
    missing = required - set(manifest.columns)
    if missing:
        raise ValueError(f"MODMA manifest missing columns: {', '.join(sorted(missing))}")
    rows = manifest[manifest["subject_id"].astype(str).isin(subjects)].copy()
    rows = rows[
        rows["file_valid"].fillna(False).astype(bool)
        & rows["audio_path"].notna()
        & rows[SPEC.target].notna()
    ].copy()
    if rows.empty:
        raise ValueError("no usable MODMA audio rows")
    rows = rows.sort_values(["subject_id", "task_type", "segment_id"]).reset_index()
    rows["subject_id"] = rows["subject_id"].astype(str)
    rows["task_type"] = rows["task_type"].astype(str)
    rows["segment_key"] = rows.apply(
        lambda row: "::".join([str(row["task_type"]), str(row["segment_id"]), str(row["index"])]),
        axis=1,
    )
    observed = set(rows["subject_id"].astype(str))
    missing_subjects = sorted(subjects - observed, key=natural_key)
    if missing_subjects:
        raise ValueError(f"split subjects missing valid audio rows: {missing_subjects[:10]}")
    return rows.reset_index(drop=True)


def save_segment_cache(path: Path, rows: list[dict[str, Any]]) -> None:
    frame = pd.DataFrame(rows)
    if not frame.empty:
        frame = frame.sort_values(["subject_id", "task_type", "segment_key"]).reset_index(drop=True)
    frame.to_csv(path, index=False)


def extract_segment_features(segment_table: pd.DataFrame, out_dir: Path, force: bool = False) -> tuple[pd.DataFrame, list[str]]:
    cache_path = out_dir / "modma_egemaps_segment_features.csv"
    required_keys = set(zip(segment_table["subject_id"], segment_table["segment_key"], strict=True))
    cached_rows: list[dict[str, Any]] = []
    cached_keys: set[tuple[str, str]] = set()
    if cache_path.exists() and not force:
        cached = pd.read_csv(cache_path)
        cached["subject_id"] = cached["subject_id"].astype(str)
        cached["segment_key"] = cached["segment_key"].astype(str)
        cached_keys = set(zip(cached["subject_id"], cached["segment_key"], strict=True))
        cached_rows = cached[
            [
                key in required_keys
                for key in zip(cached["subject_id"], cached["segment_key"], strict=True)
            ]
        ].to_dict("records")
    missing_rows = segment_table[
        [
            key not in cached_keys
            for key in zip(segment_table["subject_id"], segment_table["segment_key"], strict=True)
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
            if column not in {"subject_id", "task_type", "segment_key"}
        ]
    print(
        f"Extracting MODMA eGeMAPS: {len(missing_rows)} missing / {len(segment_table)} audio segments",
        flush=True,
    )
    warnings.filterwarnings("ignore", message="Segment too short.*")
    for idx, row in missing_rows.iterrows():
        path = Path(str(row["audio_path"]))
        if not path.exists():
            raise FileNotFoundError(f"manifest audio path missing: {path}")
        if (idx + 1) == 1 or (idx + 1) % 50 == 0 or (idx + 1) == len(missing_rows):
            print(
                f"  [modma] {idx + 1}/{len(missing_rows)} subject={row['subject_id']} task={row['task_type']} segment={row['segment_id']}",
                flush=True,
            )
        features = smile.process_file(str(path))
        if features.empty:
            raise ValueError(f"openSMILE returned no features for {path}")
        values = features.iloc[0]
        if feature_columns is None:
            feature_columns = [str(column) for column in values.index]
        feature_rows.append(
            {
                "subject_id": str(row["subject_id"]),
                "task_type": str(row["task_type"]),
                "segment_key": str(row["segment_key"]),
                **{str(column): float(values[column]) for column in values.index},
            }
        )
        if (idx + 1) % 50 == 0:
            save_segment_cache(cache_path, feature_rows)
    if feature_columns is None:
        raise RuntimeError("no eGeMAPS features extracted")
    save_segment_cache(cache_path, feature_rows)

    features = pd.DataFrame(feature_rows)
    observed_keys = set(zip(features["subject_id"].astype(str), features["segment_key"].astype(str), strict=True))
    missing_keys = required_keys - observed_keys
    if missing_keys:
        raise ValueError(f"missing cached eGeMAPS rows: {sorted(missing_keys)[:5]}")
    selected = features[
        [
            key in required_keys
            for key in zip(features["subject_id"].astype(str), features["segment_key"].astype(str), strict=True)
        ]
    ].copy()
    return selected.sort_values(["subject_id", "task_type", "segment_key"]).reset_index(drop=True), feature_columns


def aggregate_subject_features(segment_features: pd.DataFrame, feature_columns: list[str]) -> tuple[pd.DataFrame, list[str]]:
    rows: list[dict[str, Any]] = []
    for subject_id, group in segment_features.groupby("subject_id", sort=False):
        values = group[feature_columns].to_numpy(dtype=np.float64)
        row: dict[str, Any] = {
            "subject_id": str(subject_id),
            "audio_segment_count": int(len(group)),
            "task_types_observed": ";".join(sorted(group["task_type"].astype(str).unique())),
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
    subject_features = pd.DataFrame(rows).sort_values(
        "subject_id",
        key=lambda series: series.map(lambda item: tuple(natural_key(item))),
    ).reset_index(drop=True)
    model_feature_columns = [
        column
        for column in subject_features.columns
        if column not in {"subject_id", "audio_segment_count", "task_types_observed"}
    ]
    return subject_features, model_feature_columns


def load_or_extract_subject_features(
    segment_table: pd.DataFrame,
    out_dir: Path,
    force: bool = False,
) -> tuple[pd.DataFrame, list[str]]:
    subject_cache_path = out_dir / "modma_egemaps_subject_features.csv"
    subjects = set(segment_table["subject_id"].astype(str))
    if subject_cache_path.exists() and not force:
        cached = pd.read_csv(subject_cache_path)
        cached["subject_id"] = cached["subject_id"].astype(str)
        cached_subjects = set(cached["subject_id"])
        if subjects.issubset(cached_subjects):
            selected = cached[cached["subject_id"].isin(subjects)].copy()
            feature_columns = [
                column
                for column in selected.columns
                if column not in {"subject_id", "audio_segment_count", "task_types_observed"}
            ]
            if feature_columns:
                print("Using cached MODMA subject-level eGeMAPS", flush=True)
                return selected.reset_index(drop=True), feature_columns
    segment_features, base_feature_columns = extract_segment_features(segment_table, out_dir, force=force)
    subject_features, feature_columns = aggregate_subject_features(segment_features, base_feature_columns)
    subject_features.to_csv(subject_cache_path, index=False)
    return subject_features, feature_columns


def build_subject_table(manifest_path: Path, subject_features: pd.DataFrame) -> tuple[pd.DataFrame, list[str]]:
    manifest = read_manifest(manifest_path)
    label_rows = manifest[manifest["subject_id"].astype(str).isin(set(subject_features["subject_id"].astype(str)))].copy()
    label_rows = label_rows[label_rows[SPEC.target].notna()].copy()
    labels: list[dict[str, Any]] = []
    for subject_id, group in label_rows.groupby("subject_id", sort=False):
        values = group[SPEC.target].dropna().unique()
        if len(values) != 1:
            raise ValueError(f"{subject_id} has inconsistent binary labels: {values[:5]}")
        labels.append({"subject_id": str(subject_id), SPEC.target: int(values[0])})
    label_frame = pd.DataFrame(labels)
    table = subject_features.merge(label_frame, on="subject_id", how="inner")
    missing_labels = sorted(set(subject_features["subject_id"].astype(str)) - set(table["subject_id"].astype(str)), key=natural_key)
    if missing_labels:
        raise ValueError(f"subjects missing labels: {missing_labels[:10]}")
    feature_columns = [
        column
        for column in table.columns
        if column not in {"subject_id", "audio_segment_count", "task_types_observed", SPEC.target}
    ]
    return table.sort_values("subject_id", key=lambda series: series.map(lambda item: tuple(natural_key(item)))).reset_index(drop=True), feature_columns


def prediction_meta(seed: int, fold: str, row: pd.Series) -> dict[str, Any]:
    return {
        "run_id": SPEC.run_id,
        "dataset": SPEC.dataset,
        "modality": SPEC.modality,
        "task": SPEC.task,
        "model": SPEC.model,
        "seed": int(seed),
        "fold": fold,
        "protocol_id": SPEC.protocol_id,
        "task_type": SPEC.task_type,
        "subject_id": row["subject_id"],
        "split": "validation",
        "audio_segment_count": int(row["audio_segment_count"]),
    }


def run_baseline(table: pd.DataFrame, feature_columns: list[str], folds: dict[str, dict[str, list[str]]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    table_by_subject = table.set_index("subject_id", drop=False)
    predictions: list[dict[str, Any]] = []
    fold_summaries: list[dict[str, Any]] = []
    for seed in SEEDS:
        for fold, roles in folds.items():
            train = table_by_subject.loc[roles["train"]].reset_index(drop=True)
            validation = table_by_subject.loc[roles["validation"]].reset_index(drop=True)
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
            model.fit(train[feature_columns], train[SPEC.target].astype(int))
            y_pred = model.predict(validation[feature_columns])
            y_score = model.predict_proba(validation[feature_columns])[:, 1]
            for idx, row in validation.iterrows():
                predictions.append(
                    {
                        **prediction_meta(seed, fold, row),
                        "y_true": int(row[SPEC.target]),
                        "y_pred": int(y_pred[idx]),
                        "y_score": float(y_score[idx]),
                    }
                )
            fold_summaries.append(
                {
                    "seed": int(seed),
                    "fold": fold,
                    "train_subjects": int(len(train)),
                    "validation_subjects": int(len(validation)),
                    "train_positive_subjects": int(train[SPEC.target].astype(int).sum()),
                    "validation_positive_subjects": int(validation[SPEC.target].astype(int).sum()),
                    "svm_c": float(FIXED_SVM_C),
                }
            )
    return predictions, fold_summaries


def write_report(out_dir: Path, summary: dict[str, Any]) -> None:
    lines = [
        "# MODMA Audio eGeMAPS Phase 2 Baseline",
        "",
        f"Generated: `{summary['generated_at']}`",
        "",
        "## Protocol",
        "",
        "- Input interface: manifest-resolved valid MODMA audio paths and generated subject-level splits.",
        "- Feature extractor: openSMILE eGeMAPSv02 functionals.",
        "- Feature aggregation: all valid task segments per subject aggregated with mean, std, min, and max.",
        "- Model: fixed-hyperparameter linear SVM with balanced class weights.",
        "- Unit of prediction: one row per subject per seed after outer subject-level CV.",
        "- No validation or test labels are used for hyperparameter selection.",
        "- No test split is used.",
        "- Raw audio, source paths, and file names are not written to outputs.",
        "",
        "## Audit",
        "",
        f"- Run: `{summary['runs']}`",
        f"- Subjects: `{summary['subject_count']}`",
        f"- Audio segments: `{summary['audio_segments']}`",
        f"- Invalid manifest audio rows excluded: `{summary['invalid_audio_rows_excluded']}`",
        f"- Folds: `{summary['fold_count']}`",
        f"- Seeds: `{summary['seeds']}`",
        f"- Bootstrap resamples: `{summary['bootstrap_resamples']}`",
        f"- Prediction rows: `{summary['prediction_rows']}`",
        f"- Subject overlap violations: `{summary['subject_overlap_violations']}`",
        f"- Raw audio written: `{summary['raw_audio_written']}`",
        f"- Source paths written: `{summary['source_paths_written']}`",
        "",
        "## Output Files",
        "",
        "- `modma_audio_egemaps_predictions.csv`",
        "- `modma_egemaps_segment_features.csv`",
        "- `modma_egemaps_subject_features.csv`",
        "- `phase2_metrics_by_seed.csv`",
        "- `phase2_metric_summary.csv`",
        "- `modma_audio_egemaps_run_summary.json`",
    ]
    (out_dir / "modma_audio_egemaps_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, default=MANIFEST_PATH)
    parser.add_argument("--split-path", type=Path, default=SPLIT_PATH)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--bootstrap-resamples", type=int, default=1000)
    parser.add_argument("--force-features", action="store_true")
    args = parser.parse_args()

    args.out_dir.mkdir(parents=True, exist_ok=True)
    folds = load_protocol_splits(args.split_path)
    split_subjects = {subject for roles in folds.values() for values in roles.values() for subject in values}
    segment_table = build_segment_table(args.manifest, split_subjects)
    subject_features, feature_columns = load_or_extract_subject_features(segment_table, args.out_dir, force=args.force_features)
    table, model_feature_columns = build_subject_table(args.manifest, subject_features)
    missing_split_subjects = sorted(split_subjects - set(table["subject_id"].astype(str)), key=natural_key)
    if missing_split_subjects:
        raise ValueError(f"split subjects missing from model table: {missing_split_subjects[:10]}")

    predictions, fold_summaries = run_baseline(table, model_feature_columns, folds)
    predictions_frame = pd.DataFrame(predictions)
    predictions_path = args.out_dir / "modma_audio_egemaps_predictions.csv"
    predictions_frame.to_csv(predictions_path, index=False)

    metrics_by_seed, metric_summary = metric_records(
        predictions_frame,
        bootstrap_resamples=args.bootstrap_resamples,
        seed=20260727,
    )
    metrics_by_seed.to_csv(args.out_dir / "phase2_metrics_by_seed.csv", index=False)
    metric_summary.to_csv(args.out_dir / "phase2_metric_summary.csv", index=False)

    subject_overlap_violations = 0
    for roles in folds.values():
        subject_overlap_violations += int(bool(set(roles["train"]) & set(roles["validation"])))
    manifest = read_manifest(args.manifest)
    invalid_audio_rows = int((~manifest["file_valid"].fillna(False).astype(bool) & manifest["audio_path"].notna()).sum())
    run_summary = {
        "generated_at": utc_now(),
        "manifest": str(args.manifest),
        "split_path": str(args.split_path),
        "feature_set": "openSMILE eGeMAPSv02 Functionals",
        "opensmile_version": str(opensmile.__version__),
        "runs": [RUN_ID],
        "seeds": SEEDS,
        "seed_count": len(SEEDS),
        "bootstrap_resamples": int(args.bootstrap_resamples),
        "subject_count": int(len(split_subjects)),
        "fold_count": int(len(folds)),
        "audio_segments": int(len(segment_table)),
        "invalid_audio_rows_excluded": invalid_audio_rows,
        "subject_feature_rows": int(len(subject_features)),
        "feature_count": int(len(model_feature_columns)),
        "prediction_rows": int(len(predictions_frame)),
        "positive_subjects": int(table.drop_duplicates("subject_id")[SPEC.target].astype(int).sum()),
        "negative_subjects": int(len(table.drop_duplicates("subject_id")) - table.drop_duplicates("subject_id")[SPEC.target].astype(int).sum()),
        "audio_segment_count_min": int(table["audio_segment_count"].min()),
        "audio_segment_count_max": int(table["audio_segment_count"].max()),
        "task_types": sorted(segment_table["task_type"].astype(str).unique()),
        "fold_summaries": fold_summaries,
        "subject_overlap_violations": int(subject_overlap_violations),
        "no_test_split_used": True,
        "raw_audio_written": False,
        "source_paths_written": False,
    }
    (args.out_dir / "modma_audio_egemaps_run_summary.json").write_text(
        json.dumps(run_summary, indent=2, ensure_ascii=True, sort_keys=True),
        encoding="utf-8",
    )
    write_report(args.out_dir, run_summary)
    print(f"Wrote {predictions_path}")
    print(f"Wrote {args.out_dir / 'phase2_metric_summary.csv'}")


if __name__ == "__main__":
    main()
