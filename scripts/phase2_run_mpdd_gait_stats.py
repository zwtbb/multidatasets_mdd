#!/usr/bin/env python3
"""Run Phase 2 MPDD gait statistical baselines.

The runner uses manifest-resolved IMU paths, extracts fixed statistical features
from each subject's gait sequence, and evaluates binary depression classifiers
with repeated subject-level out-of-fold predictions. It does not read or use the
unlabeled MPDD test split.
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
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import StratifiedKFold
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from xgboost import XGBClassifier

from phase2_metrics import metric_records


ROOT = Path("/root/autodl-tmp")
MANIFEST_PATH = ROOT / "datasets" / "manifests" / "mpdd_avg_2026_subjects.csv"
DEFAULT_OUT_DIR = ROOT / "analysis" / "phase2_baselines" / "mpdd_gait_stats"
SEEDS = [0, 1, 2, 3, 4]
DATASET_DISPLAY = "MPDD-AVG-2026"
MAX_CHANNELS = 12


@dataclass(frozen=True)
class BaselineSpec:
    run_id: str
    modality: str
    task: str
    task_type: str
    target: str
    model: str


LOGISTIC_SPEC = BaselineSpec(
    run_id="mpdd_gait_binary_stats_logistic",
    modality="Gait",
    task="binary depression classification",
    task_type="binary_classification",
    target="binary_label",
    model="statistical gait features + Logistic",
)

XGBOOST_SPEC = BaselineSpec(
    run_id="mpdd_gait_binary_stats_xgboost",
    modality="Gait",
    task="binary depression classification",
    task_type="binary_classification",
    target="binary_label",
    model="statistical gait features + XGBoost",
)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def load_sequence(path_value: Any) -> np.ndarray:
    path = Path(str(path_value))
    if not path.exists():
        raise FileNotFoundError(f"manifest gait path missing: {path}")
    arr = np.load(path, allow_pickle=False)
    if not np.issubdtype(arr.dtype, np.number):
        raise ValueError(f"non-numeric gait array: {path}")
    if arr.ndim == 1:
        arr = arr.reshape(-1, 1)
    if arr.ndim != 2:
        raise ValueError(f"expected 2D gait array, got shape {arr.shape}: {path}")
    return np.asarray(arr, dtype=np.float64)


def channel_stats(values: np.ndarray) -> list[float]:
    finite = values[np.isfinite(values)]
    if finite.size == 0:
        return [np.nan] * 12
    if finite.size > 1:
        diff = np.diff(finite)
        mean_abs_diff = float(np.mean(np.abs(diff)))
        diff_std = float(np.std(diff))
    else:
        mean_abs_diff = 0.0
        diff_std = 0.0
    q25, median, q75 = np.percentile(finite, [25, 50, 75])
    return [
        float(np.mean(finite)),
        float(np.std(finite)),
        float(np.min(finite)),
        float(np.max(finite)),
        float(q25),
        float(median),
        float(q75),
        float(q75 - q25),
        float(np.sqrt(np.mean(finite**2))),
        mean_abs_diff,
        diff_std,
        float(np.mean(np.abs(finite))),
    ]


def extract_features(arr: np.ndarray) -> list[float]:
    rows, cols = arr.shape
    features: list[float] = [float(rows), float(cols)]
    for channel in range(MAX_CHANNELS):
        if channel < cols:
            features.extend(channel_stats(arr[:, channel]))
        else:
            features.extend([np.nan] * 12)
    clipped = np.clip(arr[:, : min(cols, MAX_CHANNELS)], -1.0e6, 1.0e6)
    finite = clipped[np.isfinite(clipped)]
    if finite.size:
        features.extend(
            [
                float(np.mean(finite)),
                float(np.std(finite)),
                float(np.sqrt(np.mean(finite**2))),
                float(np.percentile(finite, 75) - np.percentile(finite, 25)),
            ]
        )
    else:
        features.extend([np.nan] * 4)
    return features


def build_subject_table(manifest_path: Path) -> tuple[pd.DataFrame, np.ndarray]:
    manifest = pd.read_csv(manifest_path)
    required = {
        "subject_id",
        "gait_path",
        "binary_label",
        "severity_label",
        "phq9_total",
        "age",
        "official_split",
    }
    missing = required - set(manifest.columns)
    if missing:
        raise ValueError(f"MPDD manifest missing columns: {', '.join(sorted(missing))}")

    subject_rows = manifest.drop_duplicates("subject_id").copy()
    usable = subject_rows[
        subject_rows["gait_path"].notna()
        & subject_rows["binary_label"].notna()
        & subject_rows["official_split"].eq("train")
    ].copy()
    if usable.empty:
        raise ValueError("no labeled train subjects with gait paths")
    feature_rows: list[list[float]] = []
    row_meta: list[dict[str, Any]] = []
    for _, row in usable.sort_values("subject_id").iterrows():
        arr = load_sequence(row["gait_path"])
        feature_rows.append(extract_features(arr))
        row_meta.append(
            {
                "subject_id": str(row["subject_id"]),
                "split": "train_oof",
                "binary_label": int(row["binary_label"]),
                "severity_label": int(row["severity_label"]),
                "phq9_total": float(row["phq9_total"]),
                "age_group": str(row["age"]),
                "sequence_length": int(arr.shape[0]),
                "channel_count": int(arr.shape[1]),
            }
        )
    table = pd.DataFrame(row_meta)
    features = np.asarray(feature_rows, dtype=np.float64)
    if len(table) != features.shape[0]:
        raise RuntimeError("feature row mismatch")
    return table, features


def logistic_model(seed: int) -> Pipeline:
    return Pipeline(
        [
            ("imputer", SimpleImputer(strategy="median")),
            ("scaler", StandardScaler()),
            (
                "logistic",
                LogisticRegression(
                    C=1.0,
                    class_weight="balanced",
                    max_iter=1000,
                    random_state=seed,
                    solver="liblinear",
                ),
            ),
        ]
    )


def xgboost_model(seed: int) -> XGBClassifier:
    return XGBClassifier(
        n_estimators=80,
        max_depth=2,
        learning_rate=0.05,
        subsample=0.9,
        colsample_bytree=0.8,
        objective="binary:logistic",
        eval_metric="logloss",
        reg_lambda=1.0,
        min_child_weight=2.0,
        random_state=seed,
        n_jobs=1,
        verbosity=0,
    )


def prediction_meta(spec: BaselineSpec, seed: int, fold: int, row: pd.Series) -> dict[str, Any]:
    return {
        "run_id": spec.run_id,
        "dataset": DATASET_DISPLAY,
        "modality": spec.modality,
        "task": spec.task,
        "model": spec.model,
        "seed": int(seed),
        "fold": int(fold),
        "task_type": spec.task_type,
        "subject_id": row["subject_id"],
        "split": row["split"],
        "age_group": row["age_group"],
    }


def run_seed(table: pd.DataFrame, features: np.ndarray, seed: int) -> list[dict[str, Any]]:
    labels = table["binary_label"].to_numpy(dtype=np.int64)
    folds = StratifiedKFold(n_splits=5, shuffle=True, random_state=seed)
    predictions: list[dict[str, Any]] = []
    for fold, (train_idx, heldout_idx) in enumerate(folds.split(features, labels), start=1):
        for spec, model in [(LOGISTIC_SPEC, logistic_model(seed)), (XGBOOST_SPEC, xgboost_model(seed))]:
            model.fit(features[train_idx], labels[train_idx])
            pred = model.predict(features[heldout_idx]).astype(int)
            score = model.predict_proba(features[heldout_idx])[:, 1]
            heldout = table.iloc[heldout_idx].reset_index(drop=True)
            for idx, row in heldout.iterrows():
                predictions.append(
                    {
                        **prediction_meta(spec, seed, fold, row),
                        "y_true": int(row["binary_label"]),
                        "y_pred": int(pred[idx]),
                        "y_score": float(score[idx]),
                    }
                )
    return predictions


def write_report(out_dir: Path, summary: dict[str, Any]) -> None:
    lines = [
        "# MPDD Gait Statistics Phase 2 Baseline",
        "",
        f"Generated: `{summary['generated_at']}`",
        "",
        "## Protocol",
        "",
        "- Input interface: `datasets/manifests/mpdd_avg_2026_subjects.csv`.",
        "- Unit of prediction: one row per subject.",
        "- Features: per-channel IMU summary statistics plus sequence length and channel count.",
        "- Evaluation: five repeated stratified 5-fold subject-level out-of-fold runs.",
        "- Hyperparameters are fixed before evaluation; no test split is used.",
        "- Unlabeled MPDD test rows are ignored.",
        "- Raw IMU arrays are read for feature extraction but are not written to outputs.",
        "",
        "## Audit",
        "",
        f"- Labeled gait subjects: `{summary['subjects']}`",
        f"- Elder subjects: `{summary['age_group_counts'].get('elder', 0)}`",
        f"- Young subjects: `{summary['age_group_counts'].get('young', 0)}`",
        f"- Positive subjects: `{summary['positive_subjects']}`",
        f"- Seeds: `{summary['seeds']}`",
        f"- Bootstrap resamples: `{summary['bootstrap_resamples']}`",
        f"- Prediction rows: `{summary['prediction_rows']}`",
        "",
        "## Output Files",
        "",
        "- `mpdd_gait_stats_predictions.csv`",
        "- `phase2_metrics_by_seed.csv`",
        "- `phase2_metric_summary.csv`",
        "- `mpdd_gait_stats_run_summary.json`",
    ]
    (out_dir / "mpdd_gait_stats_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, default=MANIFEST_PATH)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--bootstrap-resamples", type=int, default=1000)
    args = parser.parse_args()

    table, features = build_subject_table(args.manifest)
    all_predictions: list[dict[str, Any]] = []
    for seed in SEEDS:
        all_predictions.extend(run_seed(table, features, seed))

    args.out_dir.mkdir(parents=True, exist_ok=True)
    predictions_frame = pd.DataFrame(all_predictions)
    predictions_path = args.out_dir / "mpdd_gait_stats_predictions.csv"
    predictions_frame.to_csv(predictions_path, index=False)
    metrics_by_seed, metric_summary = metric_records(
        predictions_frame,
        bootstrap_resamples=args.bootstrap_resamples,
        seed=20260727,
    )
    metrics_by_seed.to_csv(args.out_dir / "phase2_metrics_by_seed.csv", index=False)
    metric_summary.to_csv(args.out_dir / "phase2_metric_summary.csv", index=False)

    run_summary = {
        "generated_at": utc_now(),
        "manifest": str(args.manifest),
        "subjects": int(len(table)),
        "feature_columns": int(features.shape[1]),
        "age_group_counts": {str(k): int(v) for k, v in table["age_group"].value_counts().to_dict().items()},
        "positive_subjects": int(table["binary_label"].sum()),
        "seeds": SEEDS,
        "seed_count": len(SEEDS),
        "bootstrap_resamples": int(args.bootstrap_resamples),
        "prediction_rows": int(len(predictions_frame)),
        "runs": [LOGISTIC_SPEC.run_id, XGBOOST_SPEC.run_id],
        "split_policy": "labeled_train_internal_subject_level_stratified_5fold_oof",
        "no_test_split_used": True,
        "raw_imu_written": False,
    }
    (args.out_dir / "mpdd_gait_stats_run_summary.json").write_text(
        json.dumps(run_summary, indent=2, ensure_ascii=True, sort_keys=True),
        encoding="utf-8",
    )
    write_report(args.out_dir, run_summary)
    print(f"Wrote {predictions_path}")
    print(f"Wrote {args.out_dir / 'phase2_metric_summary.csv'}")


if __name__ == "__main__":
    main()
