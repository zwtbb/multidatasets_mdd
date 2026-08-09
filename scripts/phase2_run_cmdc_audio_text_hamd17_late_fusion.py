#!/usr/bin/env python3
"""Run the Phase 2 CMDC HAMD-17 audio/text late-fusion baseline.

This runner trains fold-local text TF-IDF/Ridge and audio eGeMAPS/SVR
component predictors for the 25 CMDC subjects with HAMD-17 labels, then writes
only the unweighted late-fusion prediction run into the Phase 2 metric summary.
No raw text, audio, feature paths, or source paths are written to outputs.
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
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.impute import SimpleImputer
from sklearn.linear_model import Ridge
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.svm import SVR

from phase2_metrics import metric_records


ROOT = Path("/root/autodl-tmp")
MANIFEST_PATH = ROOT / "datasets" / "manifests" / "cmdc_subjects.csv"
SPLIT_PATH = ROOT / "datasets" / "splits" / "phase2_subject_splits.csv"
DEFAULT_AUDIO_FEATURES = (
    ROOT / "analysis" / "phase2_baselines" / "cmdc_pdch_audio_egemaps" / "cmdc_egemaps_subject_features.csv"
)
DEFAULT_OUT_DIR = ROOT / "analysis" / "phase2_baselines" / "cmdc_audio_text_hamd17_late_fusion"
FUSION_RUN_ID = "cmdc_audio_text_hamd17_late_fusion"
TEXT_COMPONENT_RUN_ID = "cmdc_text_hamd17_tfidf_ridge_internal"
AUDIO_COMPONENT_RUN_ID = "cmdc_audio_hamd17_egemaps_svr_internal"
PROTOCOL_ID = "cmdc_hamd17_subject_cv"
TARGET = "hamd17_total"
SEEDS = [0, 1, 2, 3, 4]
FIXED_RIDGE_ALPHA = 10.0
FIXED_SVR_C = 1.0
FIXED_SVR_EPSILON = 0.1


@dataclass(frozen=True)
class FoldData:
    seed: int
    fold: str
    train: pd.DataFrame
    validation: pd.DataFrame


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def natural_key(value: Any) -> list[Any]:
    return [int(part) if part.isdigit() else part for part in re.split(r"(\d+)", str(value))]


def read_text(path_value: Any) -> str:
    path = Path(str(path_value))
    if not path.exists():
        raise FileNotFoundError(f"manifest text path missing: {path}")
    data = path.read_bytes()
    for encoding in ["utf-8-sig", "utf-8", "gb18030"]:
        try:
            return data.decode(encoding).strip()
        except UnicodeDecodeError:
            continue
    return data.decode("utf-8", errors="ignore").strip()


def vectorizer() -> TfidfVectorizer:
    return TfidfVectorizer(
        analyzer="char",
        ngram_range=(2, 3),
        min_df=2,
        max_features=30000,
        sublinear_tf=True,
        norm="l2",
    )


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


def build_text_table(manifest_path: Path, split_subjects: set[str]) -> pd.DataFrame:
    if not manifest_path.exists():
        raise FileNotFoundError(f"manifest missing: {manifest_path}")
    manifest = pd.read_csv(manifest_path)
    required = {"subject_id", "text_path", "file_valid", TARGET}
    missing = required - set(manifest.columns)
    if missing:
        raise ValueError(f"CMDC manifest missing columns: {', '.join(sorted(missing))}")
    usable = manifest[
        manifest["subject_id"].astype(str).isin(split_subjects)
        & manifest["file_valid"].fillna(False).astype(bool)
        & manifest["text_path"].notna()
        & manifest[TARGET].notna()
    ].copy()
    if usable.empty:
        raise ValueError("no usable CMDC HAMD text rows")
    rows: list[dict[str, Any]] = []
    for subject_id, group in usable.groupby("subject_id", sort=False):
        labels = group[TARGET].dropna().unique()
        if len(labels) != 1:
            raise ValueError(f"{subject_id} has inconsistent HAMD labels: {labels[:5]}")
        group = group.assign(_segment_key=group.get("segment_id", pd.Series([""] * len(group))).astype(str))
        group = group.sort_values("_segment_key", key=lambda series: series.map(lambda item: tuple(natural_key(item))))
        texts = [read_text(path) for path in group["text_path"]]
        rows.append(
            {
                "subject_id": str(subject_id),
                "text": "\n".join(texts),
                TARGET: float(labels[0]),
                "text_segment_count": int(len(texts)),
                "empty_text_segments": int(sum(1 for text in texts if not text.strip())),
            }
        )
    table = pd.DataFrame(rows).sort_values("subject_id", key=lambda series: series.map(lambda item: tuple(natural_key(item)))).reset_index(drop=True)
    missing_subjects = sorted(split_subjects - set(table["subject_id"].astype(str)), key=natural_key)
    if missing_subjects:
        raise ValueError(f"split subjects missing usable text rows: {missing_subjects[:10]}")
    return table


def load_audio_table(audio_features_path: Path, manifest_path: Path, split_subjects: set[str]) -> tuple[pd.DataFrame, list[str]]:
    if not audio_features_path.exists():
        raise FileNotFoundError(f"audio feature cache missing: {audio_features_path}")
    features = pd.read_csv(audio_features_path)
    required_features = {"subject_id", "audio_segment_count"}
    missing_features = required_features - set(features.columns)
    if missing_features:
        raise ValueError(f"audio feature cache missing columns: {', '.join(sorted(missing_features))}")
    features["subject_id"] = features["subject_id"].astype(str)
    features = features[features["subject_id"].isin(split_subjects)].copy()
    feature_columns = [
        column
        for column in features.columns
        if column not in {"dataset_id", "subject_id", "audio_segment_count"}
    ]
    if not feature_columns:
        raise ValueError("audio feature cache has no model feature columns")

    manifest = pd.read_csv(manifest_path)
    labels: list[dict[str, Any]] = []
    usable = manifest[
        manifest["subject_id"].astype(str).isin(split_subjects)
        & manifest["file_valid"].fillna(False).astype(bool)
        & manifest[TARGET].notna()
    ].copy()
    for subject_id, group in usable.groupby("subject_id", sort=False):
        values = group[TARGET].dropna().unique()
        if len(values) != 1:
            raise ValueError(f"{subject_id} has inconsistent HAMD labels: {values[:5]}")
        labels.append({"subject_id": str(subject_id), TARGET: float(values[0])})
    table = features.merge(pd.DataFrame(labels), on="subject_id", how="inner")
    table = table.sort_values("subject_id", key=lambda series: series.map(lambda item: tuple(natural_key(item)))).reset_index(drop=True)
    missing_subjects = sorted(split_subjects - set(table["subject_id"].astype(str)), key=natural_key)
    if missing_subjects:
        raise ValueError(f"split subjects missing cached audio features or labels: {missing_subjects[:10]}")
    return table, feature_columns


def build_fusion_table(
    manifest_path: Path,
    audio_features_path: Path,
    split_subjects: set[str],
) -> tuple[pd.DataFrame, list[str]]:
    text = build_text_table(manifest_path, split_subjects)
    audio, audio_feature_columns = load_audio_table(audio_features_path, manifest_path, split_subjects)
    table = text.merge(audio, on="subject_id", suffixes=("_text", "_audio"), how="outer", indicator=True)
    merge_counts = table["_merge"].value_counts().to_dict()
    if merge_counts.get("left_only", 0) or merge_counts.get("right_only", 0):
        raise ValueError(f"text/audio subject tables are not aligned: {merge_counts}")
    table = table.drop(columns=["_merge"])
    label_mismatches = int((table[f"{TARGET}_text"].astype(float) != table[f"{TARGET}_audio"].astype(float)).sum())
    if label_mismatches:
        raise ValueError(f"text/audio HAMD labels disagree on {label_mismatches} rows")
    table = table.rename(columns={f"{TARGET}_text": TARGET}).drop(columns=[f"{TARGET}_audio"])
    return table.sort_values("subject_id", key=lambda series: series.map(lambda item: tuple(natural_key(item)))).reset_index(drop=True), audio_feature_columns


def clip_predictions(y_pred: np.ndarray, train_target: pd.Series) -> tuple[np.ndarray, int, tuple[float, float]]:
    bounds = (
        float(pd.to_numeric(train_target, errors="raise").min()),
        float(pd.to_numeric(train_target, errors="raise").max()),
    )
    arr = np.asarray(y_pred, dtype=np.float64)
    clipped = np.clip(arr, bounds[0], bounds[1])
    clip_count = int(np.sum(np.abs(clipped - arr) > 1.0e-12))
    return clipped, clip_count, bounds


def fold_data(table: pd.DataFrame, folds: dict[str, dict[str, list[str]]]) -> list[FoldData]:
    table_by_subject = table.set_index("subject_id", drop=False)
    out: list[FoldData] = []
    for seed in SEEDS:
        for fold, roles in folds.items():
            out.append(
                FoldData(
                    seed=seed,
                    fold=fold,
                    train=table_by_subject.loc[roles["train"]].reset_index(drop=True),
                    validation=table_by_subject.loc[roles["validation"]].reset_index(drop=True),
                )
            )
    return out


def prediction_meta(seed: int, fold: str, row: pd.Series) -> dict[str, Any]:
    return {
        "dataset": "CMDC",
        "modality": "Audio/Text",
        "task": "HAMD-17 regression",
        "seed": int(seed),
        "fold": fold,
        "protocol_id": PROTOCOL_ID,
        "task_type": "severity_regression",
        "subject_id": str(row["subject_id"]),
        "split": "validation",
        "text_segment_count": int(row["text_segment_count"]),
        "empty_text_segments": int(row["empty_text_segments"]),
        "audio_segment_count": int(row["audio_segment_count"]),
    }


def run_late_fusion(table: pd.DataFrame, audio_feature_columns: list[str], folds: dict[str, dict[str, list[str]]]) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, Any]]:
    fusion_predictions: list[dict[str, Any]] = []
    component_predictions: list[dict[str, Any]] = []
    fold_summaries: list[dict[str, Any]] = []

    for data in fold_data(table, folds):
        text_model = Pipeline([("tfidf", vectorizer()), ("ridge", Ridge(alpha=FIXED_RIDGE_ALPHA, solver="lsqr"))])
        text_model.fit(data.train["text"], data.train[TARGET].to_numpy(dtype=np.float64))
        text_raw = text_model.predict(data.validation["text"])
        text_pred, text_clip_count, bounds = clip_predictions(text_raw, data.train[TARGET])

        audio_model = Pipeline(
            [
                ("imputer", SimpleImputer(strategy="median")),
                ("scaler", StandardScaler()),
                ("svr", SVR(C=FIXED_SVR_C, epsilon=FIXED_SVR_EPSILON, kernel="linear")),
            ]
        )
        audio_model.fit(data.train[audio_feature_columns], data.train[TARGET].to_numpy(dtype=np.float64))
        audio_raw = audio_model.predict(data.validation[audio_feature_columns])
        audio_pred, audio_clip_count, _ = clip_predictions(audio_raw, data.train[TARGET])
        fused_pred = np.mean(np.vstack([text_pred, audio_pred]), axis=0)

        for idx, row in data.validation.iterrows():
            meta = prediction_meta(data.seed, data.fold, row)
            y_true = float(row[TARGET])
            component_predictions.extend(
                [
                    {
                        "run_id": TEXT_COMPONENT_RUN_ID,
                        **meta,
                        "model": "TF-IDF + Ridge",
                        "component": "text",
                        "y_true": y_true,
                        "y_pred": float(text_pred[idx]),
                        "y_score": "",
                    },
                    {
                        "run_id": AUDIO_COMPONENT_RUN_ID,
                        **meta,
                        "model": "eGeMAPS + SVR",
                        "component": "audio",
                        "y_true": y_true,
                        "y_pred": float(audio_pred[idx]),
                        "y_score": "",
                    },
                ]
            )
            fusion_predictions.append(
                {
                    "run_id": FUSION_RUN_ID,
                    **meta,
                    "model": "Late Fusion",
                    "y_true": y_true,
                    "y_pred": float(fused_pred[idx]),
                    "y_score": "",
                    "text_component_run_id": TEXT_COMPONENT_RUN_ID,
                    "audio_component_run_id": AUDIO_COMPONENT_RUN_ID,
                    "fusion_rule": "unweighted_prediction_average",
                }
            )

        fold_summaries.append(
            {
                "seed": int(data.seed),
                "fold": data.fold,
                "train_subjects": int(len(data.train)),
                "validation_subjects": int(len(data.validation)),
                "train_target_min": float(bounds[0]),
                "train_target_max": float(bounds[1]),
                "ridge_alpha": float(FIXED_RIDGE_ALPHA),
                "svr_c": float(FIXED_SVR_C),
                "svr_epsilon": float(FIXED_SVR_EPSILON),
                "text_validation_clip_count": int(text_clip_count),
                "audio_validation_clip_count": int(audio_clip_count),
            }
        )

    return pd.DataFrame(fusion_predictions), pd.DataFrame(component_predictions), {
        "fold_summaries": fold_summaries,
        "text_clip_count_total": int(sum(row["text_validation_clip_count"] for row in fold_summaries)),
        "audio_clip_count_total": int(sum(row["audio_validation_clip_count"] for row in fold_summaries)),
    }


def write_report(out_dir: Path, summary: dict[str, Any]) -> None:
    lines = [
        "# CMDC HAMD-17 Audio/Text Late Fusion Phase 2 Baseline",
        "",
        f"Generated: `{summary['generated_at']}`",
        "",
        "## Protocol",
        "",
        "- Input interface: manifest-resolved CMDC text paths, cached subject-level eGeMAPS features, and `datasets/splits/phase2_subject_splits.csv`.",
        "- Target and split protocol: CMDC HAMD-17 total under `cmdc_hamd17_subject_cv`.",
        "- Text component: fold-local char 2-3 TF-IDF plus fixed Ridge regression.",
        "- Audio component: cached openSMILE eGeMAPSv02 subject features plus fixed linear SVR.",
        "- Fusion rule: unweighted average of fold-local text and audio predictions.",
        "- Regression outputs are clipped to the train-fold observed HAMD-17 target range.",
        "- No validation or test labels are used for hyperparameter selection or fusion weighting.",
        "- No test split is used.",
        "- Raw text, raw audio, feature paths, and source paths are not written to outputs.",
        "",
        "## Audit",
        "",
        f"- Runs: `{summary['runs']}`",
        f"- Internal component runs: `{summary['component_runs']}`",
        f"- Subjects: `{summary['subject_count']}`",
        f"- Text segment count range: `{summary['text_segment_count_min']}` to `{summary['text_segment_count_max']}`",
        f"- Audio segment count range: `{summary['audio_segment_count_min']}` to `{summary['audio_segment_count_max']}`",
        f"- Audio feature columns: `{summary['audio_feature_count']}`",
        f"- Seeds: `{summary['seeds']}`",
        f"- Bootstrap resamples: `{summary['bootstrap_resamples']}`",
        f"- Prediction rows: `{summary['prediction_rows']}`",
        f"- Component prediction rows: `{summary['component_prediction_rows']}`",
        f"- Text prediction clip count: `{summary['text_clip_count_total']}`",
        f"- Audio prediction clip count: `{summary['audio_clip_count_total']}`",
        f"- Subject overlap violations: `{summary['subject_overlap_violations']}`",
        f"- Raw inputs written: `{summary['raw_inputs_written']}`",
        f"- Source paths written: `{summary['source_paths_written']}`",
        "",
        "## Output Files",
        "",
        "- `cmdc_audio_text_hamd17_late_fusion_predictions.csv`",
        "- `cmdc_audio_text_hamd17_component_predictions.csv`",
        "- `phase2_metrics_by_seed.csv`",
        "- `phase2_metric_summary.csv`",
        "- `cmdc_audio_text_hamd17_late_fusion_run_summary.json`",
    ]
    (out_dir / "cmdc_audio_text_hamd17_late_fusion_report.md").write_text(
        "\n".join(lines) + "\n",
        encoding="utf-8",
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest-path", type=Path, default=MANIFEST_PATH)
    parser.add_argument("--split-path", type=Path, default=SPLIT_PATH)
    parser.add_argument("--audio-features", type=Path, default=DEFAULT_AUDIO_FEATURES)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--bootstrap-resamples", type=int, default=1000)
    args = parser.parse_args()

    folds = load_protocol_splits(args.split_path)
    split_subjects = {subject for roles in folds.values() for values in roles.values() for subject in values}
    table, audio_feature_columns = build_fusion_table(args.manifest_path, args.audio_features, split_subjects)
    predictions, components, run_details = run_late_fusion(table, audio_feature_columns, folds)

    args.out_dir.mkdir(parents=True, exist_ok=True)
    predictions_path = args.out_dir / "cmdc_audio_text_hamd17_late_fusion_predictions.csv"
    components_path = args.out_dir / "cmdc_audio_text_hamd17_component_predictions.csv"
    predictions.to_csv(predictions_path, index=False)
    components.to_csv(components_path, index=False)

    metrics_by_seed, metric_summary = metric_records(
        predictions,
        bootstrap_resamples=args.bootstrap_resamples,
        seed=20260727,
    )
    metrics_by_seed.to_csv(args.out_dir / "phase2_metrics_by_seed.csv", index=False)
    metric_summary.to_csv(args.out_dir / "phase2_metric_summary.csv", index=False)

    subject_overlap_violations = int(
        sum(bool(set(roles["train"]) & set(roles["validation"])) for roles in folds.values())
    )
    run_summary = {
        "generated_at": utc_now(),
        "manifest_path": str(args.manifest_path),
        "split_path": str(args.split_path),
        "audio_features": str(args.audio_features),
        "runs": [FUSION_RUN_ID],
        "component_runs": [TEXT_COMPONENT_RUN_ID, AUDIO_COMPONENT_RUN_ID],
        "seeds": SEEDS,
        "bootstrap_resamples": int(args.bootstrap_resamples),
        "subject_count": int(table["subject_id"].nunique()),
        "prediction_rows": int(len(predictions)),
        "component_prediction_rows": int(len(components)),
        "text_segment_count_min": int(table["text_segment_count"].min()),
        "text_segment_count_max": int(table["text_segment_count"].max()),
        "audio_segment_count_min": int(table["audio_segment_count"].min()),
        "audio_segment_count_max": int(table["audio_segment_count"].max()),
        "audio_feature_count": int(len(audio_feature_columns)),
        "subject_overlap_violations": subject_overlap_violations,
        "no_test_split_used": True,
        "raw_inputs_written": False,
        "source_paths_written": False,
        **run_details,
    }
    (args.out_dir / "cmdc_audio_text_hamd17_late_fusion_run_summary.json").write_text(
        json.dumps(run_summary, indent=2, ensure_ascii=True, sort_keys=True),
        encoding="utf-8",
    )
    write_report(args.out_dir, run_summary)
    print(f"Wrote {predictions_path}")
    print(f"Wrote {args.out_dir / 'phase2_metric_summary.csv'}")


if __name__ == "__main__":
    main()
