#!/usr/bin/env python3
"""Run Phase 2 CMDC audio/text Early and Gated Fusion baselines.

Early Fusion trains a fixed-hyperparameter logistic model over concatenated
CMDC text TF-IDF and subject-level eGeMAPS features inside each subject-level
outer fold. Gated Fusion uses a fixed confidence gate over already-audited
text/audio out-of-fold probabilities. The runner writes no raw text, raw audio,
or source paths.
"""

from __future__ import annotations

import argparse
import json
import os
import re
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
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler

from phase2_metrics import metric_records


ROOT = Path("/root/autodl-tmp")
MANIFEST_PATH = ROOT / "datasets" / "manifests" / "cmdc_subjects.csv"
SPLIT_PATH = ROOT / "datasets" / "splits" / "phase2_subject_splits.csv"
AUDIO_FEATURES = ROOT / "analysis" / "phase2_baselines" / "cmdc_pdch_audio_egemaps" / "cmdc_egemaps_subject_features.csv"
TEXT_PREDICTIONS = ROOT / "analysis" / "phase2_baselines" / "cmdc_pdch_text_tfidf" / "cmdc_pdch_text_tfidf_predictions.csv"
AUDIO_PREDICTIONS = ROOT / "analysis" / "phase2_baselines" / "cmdc_pdch_audio_egemaps" / "cmdc_pdch_audio_egemaps_predictions.csv"
DEFAULT_OUT_DIR = ROOT / "analysis" / "phase2_baselines" / "cmdc_audio_text_simple_fusion"
SEEDS = [0, 1, 2, 3, 4]
PROTOCOL_ID = "cmdc_binary_subject_cv"
TEXT_RUN_ID = "cmdc_text_binary_tfidf_logistic"
AUDIO_RUN_ID = "cmdc_audio_binary_egemaps_svm"
EARLY_RUN_ID = "cmdc_audio_text_binary_early_fusion"
GATED_RUN_ID = "cmdc_audio_text_binary_gated_fusion"
FIXED_LOGISTIC_C = 1.0


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
        & (splits["target"].astype(str) == "binary_label")
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


def build_text_table(manifest_path: Path, split_subjects: set[str]) -> pd.DataFrame:
    manifest = pd.read_csv(manifest_path)
    required = {"subject_id", "text_path", "binary_label"}
    missing = required - set(manifest.columns)
    if missing:
        raise ValueError(f"CMDC manifest missing columns: {', '.join(sorted(missing))}")
    usable = manifest[manifest["subject_id"].astype(str).isin(split_subjects)].copy()
    if "file_valid" in usable.columns:
        usable = usable[usable["file_valid"].fillna(False).astype(bool)].copy()
    usable = usable[usable["text_path"].notna() & usable["binary_label"].notna()].copy()
    rows: list[dict[str, Any]] = []
    for subject_id, group in usable.groupby("subject_id", sort=False):
        labels = group["binary_label"].dropna().unique()
        if len(labels) != 1:
            raise ValueError(f"{subject_id} has inconsistent binary labels: {labels[:5]}")
        group = group.assign(_segment_key=group.get("segment_id", pd.Series([""] * len(group))).astype(str))
        group = group.sort_values("_segment_key", key=lambda series: series.map(lambda item: tuple(natural_key(item))))
        texts = [read_text(path) for path in group["text_path"]]
        rows.append(
            {
                "subject_id": str(subject_id),
                "text": "\n".join(texts),
                "binary_label": int(labels[0]),
                "text_segment_count": int(len(texts)),
                "empty_text_segments": int(sum(1 for text in texts if not text.strip())),
            }
        )
    table = pd.DataFrame(rows).sort_values("subject_id", key=lambda series: series.map(lambda item: tuple(natural_key(item)))).reset_index(drop=True)
    missing_subjects = sorted(split_subjects - set(table["subject_id"].astype(str)), key=natural_key)
    if missing_subjects:
        raise ValueError(f"split subjects missing usable text rows: {missing_subjects[:10]}")
    return table


def load_audio_features(path: Path, split_subjects: set[str]) -> tuple[pd.DataFrame, list[str]]:
    if not path.exists():
        raise FileNotFoundError(f"audio eGeMAPS feature cache missing: {path}")
    features = pd.read_csv(path)
    required = {"subject_id", "audio_segment_count"}
    missing = required - set(features.columns)
    if missing:
        raise ValueError(f"audio feature cache missing columns: {', '.join(sorted(missing))}")
    features["subject_id"] = features["subject_id"].astype(str)
    features = features[features["subject_id"].isin(split_subjects)].copy()
    missing_subjects = sorted(split_subjects - set(features["subject_id"]), key=natural_key)
    if missing_subjects:
        raise ValueError(f"split subjects missing audio features: {missing_subjects[:10]}")
    feature_columns = [
        column
        for column in features.columns
        if column not in {"dataset_id", "subject_id", "audio_segment_count"}
    ]
    return features.sort_values("subject_id", key=lambda series: series.map(lambda item: tuple(natural_key(item)))).reset_index(drop=True), feature_columns


def build_early_table(
    manifest_path: Path,
    audio_features_path: Path,
    split_subjects: set[str],
) -> tuple[pd.DataFrame, list[str]]:
    text = build_text_table(manifest_path, split_subjects)
    audio, audio_feature_columns = load_audio_features(audio_features_path, split_subjects)
    table = text.merge(audio, on="subject_id", how="inner")
    if len(table) != len(split_subjects):
        raise ValueError(f"early fusion subject merge produced {len(table)} rows for {len(split_subjects)} subjects")
    return table, audio_feature_columns


def early_prediction_meta(seed: int, fold: str, row: pd.Series) -> dict[str, Any]:
    return {
        "run_id": EARLY_RUN_ID,
        "dataset": "CMDC",
        "modality": "Audio/Text",
        "task": "MDD classification",
        "model": "Early Fusion",
        "seed": int(seed),
        "fold": fold,
        "protocol_id": PROTOCOL_ID,
        "task_type": "binary_classification",
        "subject_id": row["subject_id"],
        "split": "validation",
        "text_segment_count": int(row["text_segment_count"]),
        "audio_segment_count": int(row["audio_segment_count"]),
    }


def run_early_fusion(
    table: pd.DataFrame,
    audio_feature_columns: list[str],
    folds: dict[str, dict[str, list[str]]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    table_by_subject = table.set_index("subject_id", drop=False)
    predictions: list[dict[str, Any]] = []
    fold_summaries: list[dict[str, Any]] = []
    for seed in SEEDS:
        for fold, roles in folds.items():
            train = table_by_subject.loc[roles["train"]].reset_index(drop=True)
            validation = table_by_subject.loc[roles["validation"]].reset_index(drop=True)

            tfidf = vectorizer()
            text_train = tfidf.fit_transform(train["text"])
            text_validation = tfidf.transform(validation["text"])
            imputer = SimpleImputer(strategy="median")
            scaler = StandardScaler()
            audio_train = scaler.fit_transform(imputer.fit_transform(train[audio_feature_columns]))
            audio_validation = scaler.transform(imputer.transform(validation[audio_feature_columns]))
            x_train = sparse.hstack([text_train, sparse.csr_matrix(audio_train)], format="csr")
            x_validation = sparse.hstack([text_validation, sparse.csr_matrix(audio_validation)], format="csr")

            model = LogisticRegression(
                C=FIXED_LOGISTIC_C,
                class_weight="balanced",
                max_iter=1000,
                random_state=seed,
                solver="liblinear",
            )
            model.fit(x_train, train["binary_label"].astype(int))
            y_pred = model.predict(x_validation)
            y_score = model.predict_proba(x_validation)[:, 1]
            for idx, row in validation.iterrows():
                predictions.append(
                    {
                        **early_prediction_meta(seed, fold, row),
                        "y_true": int(row["binary_label"]),
                        "y_pred": int(y_pred[idx]),
                        "y_score": float(y_score[idx]),
                    }
                )
            fold_summaries.append(
                {
                    "run_id": EARLY_RUN_ID,
                    "seed": int(seed),
                    "fold": fold,
                    "train_subjects": int(len(train)),
                    "validation_subjects": int(len(validation)),
                    "tfidf_feature_count": int(text_train.shape[1]),
                    "audio_feature_count": int(len(audio_feature_columns)),
                    "logistic_c": float(FIXED_LOGISTIC_C),
                    "train_positive_subjects": int(train["binary_label"].astype(int).sum()),
                    "validation_positive_subjects": int(validation["binary_label"].astype(int).sum()),
                }
            )
    return predictions, fold_summaries


def load_predictions(path: Path, run_id: str, score_name: str) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"prediction file missing: {path}")
    frame = pd.read_csv(path)
    required = {"run_id", "seed", "fold", "subject_id", "y_true", "y_score"}
    missing = required - set(frame.columns)
    if missing:
        raise ValueError(f"{path} missing columns: {', '.join(sorted(missing))}")
    selected = frame[frame["run_id"].astype(str) == run_id].copy()
    if selected.empty:
        raise ValueError(f"{path} has no rows for {run_id}")
    selected = selected[["seed", "fold", "subject_id", "y_true", "y_score"]].copy()
    selected = selected.rename(columns={"y_true": f"y_true_{score_name}", "y_score": f"y_score_{score_name}"})
    duplicate_count = int(selected.duplicated(["seed", "fold", "subject_id"]).sum())
    if duplicate_count:
        raise ValueError(f"{run_id} has duplicate seed/fold/subject rows: {duplicate_count}")
    return selected


def run_gated_fusion(text_predictions_path: Path, audio_predictions_path: Path) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    text = load_predictions(text_predictions_path, TEXT_RUN_ID, "text")
    audio = load_predictions(audio_predictions_path, AUDIO_RUN_ID, "audio")
    merged = text.merge(audio, on=["seed", "fold", "subject_id"], how="outer", indicator=True)
    merge_counts = merged["_merge"].value_counts().to_dict()
    if merge_counts.get("left_only", 0) or merge_counts.get("right_only", 0):
        raise ValueError(f"text/audio prediction keys are not aligned: {merge_counts}")
    merged = merged.drop(columns=["_merge"])
    label_mismatches = int((merged["y_true_text"].astype(float) != merged["y_true_audio"].astype(float)).sum())
    if label_mismatches:
        raise ValueError(f"text/audio prediction labels disagree on {label_mismatches} rows")

    scores = merged[["y_score_text", "y_score_audio"]].astype(float)
    if not np.isfinite(scores.to_numpy()).all():
        raise ValueError("text/audio scores must be finite for gated fusion")
    confidence_text = (scores["y_score_text"] - 0.5).abs() + 1.0e-6
    confidence_audio = (scores["y_score_audio"] - 0.5).abs() + 1.0e-6
    gate_text = confidence_text / (confidence_text + confidence_audio)
    fused_score = gate_text * scores["y_score_text"] + (1.0 - gate_text) * scores["y_score_audio"]
    predictions = pd.DataFrame(
        {
            "run_id": GATED_RUN_ID,
            "dataset": "CMDC",
            "modality": "Audio/Text",
            "task": "MDD classification",
            "model": "Gated Fusion",
            "seed": merged["seed"].astype(int),
            "fold": merged["fold"].astype(str),
            "protocol_id": PROTOCOL_ID,
            "task_type": "binary_classification",
            "subject_id": merged["subject_id"].astype(str),
            "split": "validation",
            "y_true": merged["y_true_text"].astype(int),
            "y_pred": (fused_score >= 0.5).astype(int),
            "y_score": fused_score.astype(float),
            "text_run_id": TEXT_RUN_ID,
            "audio_run_id": AUDIO_RUN_ID,
            "fusion_rule": "confidence_weighted_probability_average",
        }
    )
    return predictions.to_dict("records"), {
        "run_id": GATED_RUN_ID,
        "text_rows": int(len(text)),
        "audio_rows": int(len(audio)),
        "prediction_rows": int(len(predictions)),
        "merge_counts": {str(key): int(value) for key, value in merge_counts.items()},
        "subject_count": int(predictions["subject_id"].nunique()),
        "seed_count": int(predictions["seed"].nunique()),
        "fold_count": int(predictions["fold"].nunique()),
        "label_mismatches": label_mismatches,
        "mean_text_gate": float(np.mean(gate_text)),
        "min_text_gate": float(np.min(gate_text)),
        "max_text_gate": float(np.max(gate_text)),
    }


def write_report(out_dir: Path, summary: dict[str, Any]) -> None:
    lines = [
        "# CMDC Audio/Text Simple Fusion Phase 2 Baselines",
        "",
        f"Generated: `{summary['generated_at']}`",
        "",
        "## Protocol",
        "",
        "- Early Fusion input: manifest-resolved valid text plus cached subject-level eGeMAPS features.",
        "- Early Fusion model: fixed-hyperparameter logistic regression over concatenated TF-IDF and eGeMAPS features.",
        "- Gated Fusion input: audited out-of-fold probabilities from CMDC text TF-IDF and audio eGeMAPS baselines.",
        "- Gated Fusion rule: fixed confidence-weighted probability averaging.",
        "- Prediction threshold: 0.5.",
        "- Unit of prediction: one row per subject per seed after subject-level CV.",
        "- No raw text, raw audio, source paths, or file names are written.",
        "- No validation or test labels are used for fusion weighting or hyperparameter selection.",
        "- No test split is used.",
        "",
        "## Audit",
        "",
        f"- Runs: `{summary['runs']}`",
        f"- Subjects: `{summary['subject_count']}`",
        f"- Seeds: `{summary['seeds']}`",
        f"- Bootstrap resamples: `{summary['bootstrap_resamples']}`",
        f"- Prediction rows: `{summary['prediction_rows']}`",
        f"- Gated label mismatches: `{summary['gated_summary']['label_mismatches']}`",
        f"- Raw inputs written: `{summary['raw_inputs_written']}`",
        f"- Source paths written: `{summary['source_paths_written']}`",
        "",
        "## Output Files",
        "",
        "- `cmdc_audio_text_simple_fusion_predictions.csv`",
        "- `phase2_metrics_by_seed.csv`",
        "- `phase2_metric_summary.csv`",
        "- `cmdc_audio_text_simple_fusion_run_summary.json`",
    ]
    (out_dir / "cmdc_audio_text_simple_fusion_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, default=MANIFEST_PATH)
    parser.add_argument("--split-path", type=Path, default=SPLIT_PATH)
    parser.add_argument("--audio-features", type=Path, default=AUDIO_FEATURES)
    parser.add_argument("--text-predictions", type=Path, default=TEXT_PREDICTIONS)
    parser.add_argument("--audio-predictions", type=Path, default=AUDIO_PREDICTIONS)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--bootstrap-resamples", type=int, default=1000)
    args = parser.parse_args()

    folds = load_protocol_splits(args.split_path)
    split_subjects = {subject for roles in folds.values() for values in roles.values() for subject in values}
    early_table, audio_feature_columns = build_early_table(args.manifest, args.audio_features, split_subjects)
    early_predictions, early_fold_summaries = run_early_fusion(early_table, audio_feature_columns, folds)
    gated_predictions, gated_summary = run_gated_fusion(args.text_predictions, args.audio_predictions)

    predictions_frame = pd.DataFrame([*early_predictions, *gated_predictions])
    args.out_dir.mkdir(parents=True, exist_ok=True)
    predictions_path = args.out_dir / "cmdc_audio_text_simple_fusion_predictions.csv"
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
        "runs": [EARLY_RUN_ID, GATED_RUN_ID],
        "source_runs": [TEXT_RUN_ID, AUDIO_RUN_ID],
        "seeds": SEEDS,
        "bootstrap_resamples": int(args.bootstrap_resamples),
        "prediction_rows": int(len(predictions_frame)),
        "subject_count": int(len(split_subjects)),
        "fold_count": int(len(folds)),
        "early_summary": {
            "run_id": EARLY_RUN_ID,
            "audio_feature_count": int(len(audio_feature_columns)),
            "text_segment_count_min": int(early_table["text_segment_count"].min()),
            "text_segment_count_max": int(early_table["text_segment_count"].max()),
            "audio_segment_count_min": int(early_table["audio_segment_count"].min()),
            "audio_segment_count_max": int(early_table["audio_segment_count"].max()),
            "fold_summaries": early_fold_summaries,
        },
        "gated_summary": gated_summary,
        "no_test_split_used": True,
        "raw_inputs_written": False,
        "source_paths_written": False,
    }
    (args.out_dir / "cmdc_audio_text_simple_fusion_run_summary.json").write_text(
        json.dumps(run_summary, indent=2, ensure_ascii=True, sort_keys=True),
        encoding="utf-8",
    )
    write_report(args.out_dir, run_summary)
    print(f"Wrote {predictions_path}")
    print(f"Wrote {args.out_dir / 'phase2_metric_summary.csv'}")


if __name__ == "__main__":
    main()
