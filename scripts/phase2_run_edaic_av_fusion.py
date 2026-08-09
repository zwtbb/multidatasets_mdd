#!/usr/bin/env python3
"""Run Phase 2 E-DAIC audio/video/text fusion baselines.

The runner evaluates only the three allowed simple fusion families for Phase 2:
Early Fusion, Late Fusion, and Gated Fusion. It uses the official E-DAIC train
split for fitting, the official dev split for evaluation, and never uses the
test split or dev labels for hyperparameter/weight selection.
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
from scipy import sparse
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.impute import SimpleImputer
from sklearn.linear_model import Ridge
from sklearn.metrics import mean_absolute_error
from sklearn.model_selection import KFold
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.svm import SVR

from phase2_metrics import metric_records


ROOT = Path("/root/autodl-tmp")
MANIFEST_PATH = ROOT / "datasets" / "manifests" / "edaic_subjects.csv"
AUDIO_FEATURE_PATH = ROOT / "analysis" / "phase2_baselines" / "edaic_audio_egemaps" / "edaic_egemaps_subject_features.csv"
VIDEO_FEATURE_PATH = (
    ROOT
    / "analysis"
    / "phase2_baselines"
    / "edaic_video_features"
    / "edaic_resnet_temporal_pooling_subject_features.csv"
)
TEXT_PREDICTION_PATH = ROOT / "analysis" / "phase2_baselines" / "edaic_text_tfidf" / "edaic_text_tfidf_predictions.csv"
AUDIO_PREDICTION_PATH = ROOT / "analysis" / "phase2_baselines" / "edaic_audio_egemaps" / "edaic_audio_egemaps_predictions.csv"
VIDEO_PREDICTION_PATH = ROOT / "analysis" / "phase2_baselines" / "edaic_video_features" / "edaic_video_feature_predictions.csv"
DEFAULT_OUT_DIR = ROOT / "analysis" / "phase2_baselines" / "edaic_av_fusion"

SEEDS = [0, 1, 2, 3, 4]
FIXED_RIDGE_ALPHA = 10.0
FIXED_SVR_C = 1.0
FIXED_SVR_EPSILON = 0.1
GATE_EPSILON = 1.0e-6

TEXT_RUN_ID = "edaic_text_phq8_tfidf_ridge"
AUDIO_RUN_ID = "edaic_audio_phq8_egemaps_svr"
VIDEO_RUN_ID = "edaic_video_phq8_official_temporal_pooling"


@dataclass(frozen=True)
class BaselineSpec:
    run_id: str
    model: str


EARLY_SPEC = BaselineSpec("edaic_av_phq8_early_fusion", "Early Fusion")
LATE_SPEC = BaselineSpec("edaic_av_phq8_late_fusion", "Late Fusion")
GATED_SPEC = BaselineSpec("edaic_av_phq8_gated_fusion", "Gated Fusion")
SPECS = [EARLY_SPEC, LATE_SPEC, GATED_SPEC]


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def vectorizer() -> TfidfVectorizer:
    return TfidfVectorizer(
        analyzer="word",
        ngram_range=(1, 2),
        min_df=2,
        max_features=30000,
        sublinear_tf=True,
        norm="l2",
    )


def read_transcript(path_value: Any) -> str:
    path = Path(str(path_value))
    if not path.exists():
        raise FileNotFoundError(f"manifest transcript path missing: {path}")
    transcript = pd.read_csv(path)
    required = {"Start_Time", "End_Time", "Text"}
    missing = required - set(transcript.columns)
    if missing:
        raise ValueError(f"{path} missing transcript columns: {', '.join(sorted(missing))}")
    transcript = transcript.copy()
    transcript["Text"] = transcript["Text"].fillna("").astype(str)
    transcript = transcript.sort_values(["Start_Time", "End_Time"], kind="mergesort")
    return "\n".join(value.strip() for value in transcript["Text"].tolist() if value.strip())


def read_manifest_table(manifest_path: Path) -> pd.DataFrame:
    manifest = pd.read_csv(manifest_path)
    required = {"subject_id", "official_split", "text_path", "phq8_total", "file_valid"}
    missing = required - set(manifest.columns)
    if missing:
        raise ValueError(f"E-DAIC manifest missing columns: {', '.join(sorted(missing))}")
    usable = manifest[
        (manifest["file_valid"].fillna(False).astype(bool))
        & manifest["official_split"].isin(["train", "dev"])
        & manifest["text_path"].notna()
        & manifest["phq8_total"].notna()
    ].copy()
    if usable.empty:
        raise ValueError("no usable E-DAIC train/dev rows")
    if usable["subject_id"].duplicated().any():
        dupes = sorted(usable.loc[usable["subject_id"].duplicated(), "subject_id"].astype(str).unique())
        raise ValueError(f"E-DAIC manifest should have one row per subject, duplicates observed: {dupes[:10]}")
    usable["subject_id"] = usable["subject_id"].astype(str)
    rows: list[dict[str, Any]] = []
    for _, row in usable.sort_values("subject_id").iterrows():
        rows.append(
            {
                "subject_id": str(row["subject_id"]),
                "split": str(row["official_split"]),
                "phq8_total": float(row["phq8_total"]),
                "text": read_transcript(row["text_path"]),
            }
        )
    table = pd.DataFrame(rows).sort_values("subject_id").reset_index(drop=True)
    train_subjects = set(table.loc[table["split"] == "train", "subject_id"])
    dev_subjects = set(table.loc[table["split"] == "dev", "subject_id"])
    overlap = sorted(train_subjects & dev_subjects)
    if overlap:
        raise ValueError(f"subject-level train/dev overlap detected: {overlap[:10]}")
    if table.loc[table["split"] == "train"].empty or table.loc[table["split"] == "dev"].empty:
        raise ValueError("E-DAIC fusion requires non-empty official train and dev splits")
    return table


def load_feature_table(path: Path, prefix: str, audit_columns: set[str]) -> tuple[pd.DataFrame, list[str]]:
    if not path.exists():
        raise FileNotFoundError(f"required E-DAIC feature cache missing: {path}")
    frame = pd.read_csv(path)
    if "subject_id" not in frame.columns:
        raise ValueError(f"feature cache missing subject_id: {path}")
    frame["subject_id"] = frame["subject_id"].astype(str)
    feature_columns = [column for column in frame.columns if column not in audit_columns | {"subject_id"}]
    if not feature_columns:
        raise ValueError(f"no model feature columns in {path}")
    renamed = frame[["subject_id", *feature_columns]].rename(
        columns={column: f"{prefix}{column}" for column in feature_columns}
    )
    return renamed, [f"{prefix}{column}" for column in feature_columns]


def build_fusion_table(manifest_path: Path, audio_feature_path: Path, video_feature_path: Path) -> tuple[pd.DataFrame, list[str], list[str]]:
    table = read_manifest_table(manifest_path)
    audio, audio_columns = load_feature_table(audio_feature_path, "audio__", {"frame_count"})
    video, video_columns = load_feature_table(video_feature_path, "video__", {"resnet_frame_count", "resnet_feature_dimension"})
    table = table.merge(audio, on="subject_id", how="inner", validate="one_to_one")
    table = table.merge(video, on="subject_id", how="inner", validate="one_to_one")
    expected_subjects = set(read_manifest_table(manifest_path)["subject_id"])
    observed_subjects = set(table["subject_id"])
    missing = sorted(expected_subjects - observed_subjects)
    if missing:
        raise ValueError(f"E-DAIC fusion subjects missing feature caches: {missing[:10]}")
    return table.sort_values("subject_id").reset_index(drop=True), audio_columns, video_columns


def clip_predictions(pred: np.ndarray, train_y: np.ndarray) -> tuple[np.ndarray, int, float, float]:
    low = float(np.min(train_y))
    high = float(np.max(train_y))
    clipped = np.clip(pred, low, high)
    return clipped, int(np.sum((pred < low) | (pred > high))), low, high


def fit_predict_text(train: pd.DataFrame, eval_frame: pd.DataFrame) -> tuple[np.ndarray, int]:
    y_train = train["phq8_total"].to_numpy(dtype=np.float64)
    model = Pipeline([("tfidf", vectorizer()), ("ridge", Ridge(alpha=FIXED_RIDGE_ALPHA, solver="lsqr"))])
    model.fit(train["text"], y_train)
    raw = model.predict(eval_frame["text"])
    pred, clipped, _, _ = clip_predictions(raw, y_train)
    return pred, clipped


def fit_predict_audio(train: pd.DataFrame, eval_frame: pd.DataFrame, audio_columns: list[str]) -> tuple[np.ndarray, int]:
    y_train = train["phq8_total"].to_numpy(dtype=np.float64)
    model = Pipeline(
        [
            ("imputer", SimpleImputer(strategy="median")),
            ("scaler", StandardScaler()),
            ("svr", SVR(C=FIXED_SVR_C, epsilon=FIXED_SVR_EPSILON, kernel="linear")),
        ]
    )
    model.fit(train[audio_columns].to_numpy(dtype=np.float64), y_train)
    raw = model.predict(eval_frame[audio_columns].to_numpy(dtype=np.float64))
    pred, clipped, _, _ = clip_predictions(raw, y_train)
    return pred, clipped


def fit_predict_video(train: pd.DataFrame, eval_frame: pd.DataFrame, video_columns: list[str]) -> tuple[np.ndarray, int]:
    y_train = train["phq8_total"].to_numpy(dtype=np.float64)
    model = Pipeline(
        [
            ("imputer", SimpleImputer(strategy="median")),
            ("scaler", StandardScaler()),
            ("ridge", Ridge(alpha=FIXED_RIDGE_ALPHA, solver="lsqr")),
        ]
    )
    model.fit(train[video_columns].to_numpy(dtype=np.float64), y_train)
    raw = model.predict(eval_frame[video_columns].to_numpy(dtype=np.float64))
    pred, clipped, _, _ = clip_predictions(raw, y_train)
    return pred, clipped


def dense_matrix(train: pd.DataFrame, eval_frame: pd.DataFrame, columns: list[str]) -> tuple[np.ndarray, np.ndarray]:
    model = Pipeline([("imputer", SimpleImputer(strategy="median")), ("scaler", StandardScaler())])
    train_values = model.fit_transform(train[columns].to_numpy(dtype=np.float64))
    eval_values = model.transform(eval_frame[columns].to_numpy(dtype=np.float64))
    return train_values, eval_values


def fit_predict_early(train: pd.DataFrame, dev: pd.DataFrame, audio_columns: list[str], video_columns: list[str]) -> tuple[np.ndarray, dict[str, Any]]:
    y_train = train["phq8_total"].to_numpy(dtype=np.float64)
    text_model = vectorizer()
    x_text_train = text_model.fit_transform(train["text"])
    x_text_dev = text_model.transform(dev["text"])
    x_audio_train, x_audio_dev = dense_matrix(train, dev, audio_columns)
    x_video_train, x_video_dev = dense_matrix(train, dev, video_columns)
    x_train = sparse.hstack([x_text_train, sparse.csr_matrix(x_audio_train), sparse.csr_matrix(x_video_train)], format="csr")
    x_dev = sparse.hstack([x_text_dev, sparse.csr_matrix(x_audio_dev), sparse.csr_matrix(x_video_dev)], format="csr")
    model = Ridge(alpha=FIXED_RIDGE_ALPHA, solver="lsqr")
    model.fit(x_train, y_train)
    raw = model.predict(x_dev)
    pred, clipped, low, high = clip_predictions(raw, y_train)
    return pred, {
        "text_feature_count": int(x_text_train.shape[1]),
        "audio_feature_count": int(x_audio_train.shape[1]),
        "video_feature_count": int(x_video_train.shape[1]),
        "combined_feature_count": int(x_train.shape[1]),
        "ridge_alpha": float(FIXED_RIDGE_ALPHA),
        "clip_low": float(low),
        "clip_high": float(high),
        "clipped_regression_predictions": int(clipped),
    }


def train_oof_predictions(table: pd.DataFrame, seed: int, audio_columns: list[str], video_columns: list[str]) -> tuple[pd.DataFrame, dict[str, float], dict[str, int]]:
    train = table[table["split"] == "train"].reset_index(drop=True)
    folds = KFold(n_splits=5, shuffle=True, random_state=seed)
    predictions = {
        "text": np.zeros(len(train), dtype=np.float64),
        "audio": np.zeros(len(train), dtype=np.float64),
        "video": np.zeros(len(train), dtype=np.float64),
    }
    clip_counts = {"text": 0, "audio": 0, "video": 0}
    for fit_idx, valid_idx in folds.split(train):
        fit = train.iloc[fit_idx].reset_index(drop=True)
        valid = train.iloc[valid_idx].reset_index(drop=True)
        for name, func in [
            ("text", lambda a, b: fit_predict_text(a, b)),
            ("audio", lambda a, b: fit_predict_audio(a, b, audio_columns)),
            ("video", lambda a, b: fit_predict_video(a, b, video_columns)),
        ]:
            pred, clipped = func(fit, valid)
            predictions[name][valid_idx] = pred
            clip_counts[name] += int(clipped)
    y_true = train["phq8_total"].to_numpy(dtype=np.float64)
    maes = {name: float(mean_absolute_error(y_true, pred)) for name, pred in predictions.items()}
    oof = pd.DataFrame(
        {
            "subject_id": train["subject_id"].astype(str),
            "y_true": y_true,
            "text_oof": predictions["text"],
            "audio_oof": predictions["audio"],
            "video_oof": predictions["video"],
        }
    )
    return oof, maes, clip_counts


def inverse_mae_weights(maes: dict[str, float]) -> dict[str, float]:
    inv = {name: 1.0 / (value + GATE_EPSILON) for name, value in maes.items()}
    total = float(sum(inv.values()))
    return {name: float(value / total) for name, value in inv.items()}


def full_component_predictions(train: pd.DataFrame, dev: pd.DataFrame, audio_columns: list[str], video_columns: list[str]) -> tuple[dict[str, np.ndarray], dict[str, int]]:
    text_pred, text_clips = fit_predict_text(train, dev)
    audio_pred, audio_clips = fit_predict_audio(train, dev, audio_columns)
    video_pred, video_clips = fit_predict_video(train, dev, video_columns)
    return (
        {"text": text_pred, "audio": audio_pred, "video": video_pred},
        {"text": int(text_clips), "audio": int(audio_clips), "video": int(video_clips)},
    )


def load_single_modality_predictions(path: Path, run_id: str) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"required prediction file missing for late fusion: {path}")
    frame = pd.read_csv(path)
    required = {"run_id", "seed", "subject_id", "split", "y_true", "y_pred"}
    missing = required - set(frame.columns)
    if missing:
        raise ValueError(f"{path} missing prediction columns: {', '.join(sorted(missing))}")
    selected = frame[frame["run_id"].astype(str) == run_id].copy()
    if selected.empty:
        raise ValueError(f"no predictions for run_id {run_id} in {path}")
    selected["subject_id"] = selected["subject_id"].astype(str)
    return selected[["seed", "subject_id", "split", "y_true", "y_pred"]].copy()


def late_fusion_predictions() -> tuple[pd.DataFrame, dict[str, Any]]:
    text = load_single_modality_predictions(TEXT_PREDICTION_PATH, TEXT_RUN_ID).rename(columns={"y_pred": "text_pred"})
    audio = load_single_modality_predictions(AUDIO_PREDICTION_PATH, AUDIO_RUN_ID).rename(columns={"y_pred": "audio_pred"})
    video = load_single_modality_predictions(VIDEO_PREDICTION_PATH, VIDEO_RUN_ID).rename(columns={"y_pred": "video_pred"})
    merged = text.merge(audio, on=["seed", "subject_id", "split", "y_true"], how="inner", validate="one_to_one")
    merged = merged.merge(video, on=["seed", "subject_id", "split", "y_true"], how="inner", validate="one_to_one")
    expected = len(text)
    if len(merged) != expected or len(audio) != expected or len(video) != expected:
        raise ValueError(f"late fusion prediction alignment failed: text={len(text)}, audio={len(audio)}, video={len(video)}, merged={len(merged)}")
    merged["y_pred"] = merged[["text_pred", "audio_pred", "video_pred"]].mean(axis=1)
    rows = []
    for _, row in merged.sort_values(["seed", "subject_id"]).iterrows():
        rows.append(
            {
                "run_id": LATE_SPEC.run_id,
                "dataset": "E-DAIC",
                "modality": "Audio/Video/Text",
                "task": "PHQ-8 regression",
                "model": LATE_SPEC.model,
                "seed": int(row["seed"]),
                "task_type": "severity_regression",
                "subject_id": str(row["subject_id"]),
                "split": str(row["split"]),
                "fusion_modality_count": 3,
                "y_true": float(row["y_true"]),
                "y_pred": float(row["y_pred"]),
                "y_score": "",
            }
        )
    return pd.DataFrame(rows), {
        "aligned_prediction_rows": int(len(merged)),
        "label_mismatches": 0,
        "component_run_ids": [TEXT_RUN_ID, AUDIO_RUN_ID, VIDEO_RUN_ID],
        "fusion_rule": "unweighted mean of audited dev predictions",
    }


def run_trainable_fusions(table: pd.DataFrame, audio_columns: list[str], video_columns: list[str]) -> tuple[pd.DataFrame, list[dict[str, Any]]]:
    train = table[table["split"] == "train"].reset_index(drop=True)
    dev = table[table["split"] == "dev"].reset_index(drop=True)
    rows: list[dict[str, Any]] = []
    summaries: list[dict[str, Any]] = []
    for seed in SEEDS:
        early_pred, early_summary = fit_predict_early(train, dev, audio_columns, video_columns)
        oof, maes, oof_clip_counts = train_oof_predictions(table, seed, audio_columns, video_columns)
        weights = inverse_mae_weights(maes)
        components, full_clip_counts = full_component_predictions(train, dev, audio_columns, video_columns)
        gated_pred = (
            weights["text"] * components["text"]
            + weights["audio"] * components["audio"]
            + weights["video"] * components["video"]
        )
        for idx, row in dev.iterrows():
            base = {
                "dataset": "E-DAIC",
                "modality": "Audio/Video/Text",
                "task": "PHQ-8 regression",
                "seed": int(seed),
                "task_type": "severity_regression",
                "subject_id": str(row["subject_id"]),
                "split": str(row["split"]),
                "fusion_modality_count": 3,
                "y_true": float(row["phq8_total"]),
                "y_score": "",
            }
            rows.append({**base, "run_id": EARLY_SPEC.run_id, "model": EARLY_SPEC.model, "y_pred": float(early_pred[idx])})
            rows.append({**base, "run_id": GATED_SPEC.run_id, "model": GATED_SPEC.model, "y_pred": float(gated_pred[idx])})
        summaries.append(
            {
                "seed": int(seed),
                "train_subjects": int(len(train)),
                "dev_subjects": int(len(dev)),
                "early_fusion": early_summary,
                "gated_fusion": {
                    "weights": weights,
                    "train_oof_mae": maes,
                    "oof_clip_counts": oof_clip_counts,
                    "full_train_dev_clip_counts": full_clip_counts,
                    "train_oof_rows": int(len(oof)),
                    "weight_selection": "train-only 5-fold OOF inverse MAE",
                },
            }
        )
    return pd.DataFrame(rows), summaries


def write_report(out_dir: Path, summary: dict[str, Any]) -> None:
    lines = [
        "# E-DAIC AVT Fusion Phase 2 Baselines",
        "",
        f"Generated: `{summary['generated_at']}`",
        "",
        "## Protocol",
        "",
        "- Input interface: manifest-resolved E-DAIC transcripts plus cached subject-level eGeMAPS and ResNet temporal-pooling features.",
        "- Early Fusion: concatenate train-fit TF-IDF text features, standardized eGeMAPS audio features, and standardized ResNet temporal-pooling video features; fit fixed Ridge regression.",
        "- Late Fusion: unweighted mean of audited E-DAIC text TF-IDF, audio eGeMAPS, and official visual temporal-pooling dev predictions.",
        "- Gated Fusion: learn global text/audio/video weights only from train-split 5-fold OOF inverse MAE, then apply those weights to full-train component dev predictions.",
        "- Fit on the official train split and evaluate on the official dev split.",
        "- No dev or test labels are used for hyperparameter or gate-weight selection.",
        "- No test split is used.",
        "- Raw text, raw audio, raw video, and source paths are not written to outputs.",
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
        f"- Raw text written: `{summary['raw_text_written']}`",
        f"- Raw audio written: `{summary['raw_audio_written']}`",
        f"- Raw video written: `{summary['raw_video_written']}`",
        f"- Source paths written: `{summary['source_paths_written']}`",
        "",
        "## Output Files",
        "",
        "- `edaic_av_fusion_predictions.csv`",
        "- `phase2_metrics_by_seed.csv`",
        "- `phase2_metric_summary.csv`",
        "- `edaic_av_fusion_run_summary.json`",
    ]
    (out_dir / "edaic_av_fusion_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest-path", type=Path, default=MANIFEST_PATH)
    parser.add_argument("--audio-feature-path", type=Path, default=AUDIO_FEATURE_PATH)
    parser.add_argument("--video-feature-path", type=Path, default=VIDEO_FEATURE_PATH)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--bootstrap-resamples", type=int, default=1000)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    args.out_dir.mkdir(parents=True, exist_ok=True)
    table, audio_columns, video_columns = build_fusion_table(args.manifest_path, args.audio_feature_path, args.video_feature_path)
    train_subjects = set(table.loc[table["split"] == "train", "subject_id"].astype(str))
    dev_subjects = set(table.loc[table["split"] == "dev", "subject_id"].astype(str))

    trainable_predictions, seed_summaries = run_trainable_fusions(table, audio_columns, video_columns)
    late_predictions, late_summary = late_fusion_predictions()
    predictions_frame = pd.concat([trainable_predictions, late_predictions], ignore_index=True)
    predictions_frame = predictions_frame.sort_values(["run_id", "seed", "subject_id"]).reset_index(drop=True)
    predictions_path = args.out_dir / "edaic_av_fusion_predictions.csv"
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
        "audio_feature_path": str(args.audio_feature_path),
        "video_feature_path": str(args.video_feature_path),
        "runs": [spec.run_id for spec in SPECS],
        "seeds": SEEDS,
        "seed_count": len(SEEDS),
        "bootstrap_resamples": int(args.bootstrap_resamples),
        "train_subjects": int(len(train_subjects)),
        "dev_subjects": int(len(dev_subjects)),
        "test_subjects_used": 0,
        "prediction_rows": int(len(predictions_frame)),
        "audio_feature_count": int(len(audio_columns)),
        "video_feature_count": int(len(video_columns)),
        "late_fusion": late_summary,
        "seed_summaries": seed_summaries,
        "subject_overlap_violations": int(bool(train_subjects & dev_subjects)),
        "no_test_split_used": True,
        "raw_text_written": False,
        "raw_audio_written": False,
        "raw_video_written": False,
        "source_paths_written": False,
    }
    (args.out_dir / "edaic_av_fusion_run_summary.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=True, sort_keys=True),
        encoding="utf-8",
    )
    write_report(args.out_dir, summary)
    print(f"Wrote {predictions_path}")
    print(f"Wrote {args.out_dir / 'phase2_metric_summary.csv'}")


if __name__ == "__main__":
    main()
