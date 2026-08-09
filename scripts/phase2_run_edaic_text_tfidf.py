#!/usr/bin/env python3
"""Run Phase 2 E-DAIC text TF-IDF baselines.

The runner uses the generated E-DAIC subject manifest as the input interface,
fits only on the official train split, evaluates on the official dev split, and
writes prediction/metric artifacts without persisting raw transcript text.
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
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression, Ridge
from sklearn.pipeline import Pipeline

from phase2_metrics import metric_records


ROOT = Path("/root/autodl-tmp")
MANIFEST_PATH = ROOT / "datasets" / "manifests" / "edaic_subjects.csv"
DEFAULT_OUT_DIR = ROOT / "analysis" / "phase2_baselines" / "edaic_text_tfidf"
SEEDS = [0, 1, 2, 3, 4]
FIXED_RIDGE_ALPHA = 10.0
FIXED_LOGISTIC_C = 1.0


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
    run_id="edaic_text_phq8_tfidf_ridge",
    dataset="E-DAIC",
    modality="Text",
    task="PHQ-8 regression",
    task_type="severity_regression",
    target="phq8_total",
    model="TF-IDF + Ridge",
)


CLASSIFICATION_SPEC = BaselineSpec(
    run_id="edaic_text_binary_tfidf_logistic",
    dataset="E-DAIC",
    modality="Text",
    task="binary depression classification",
    task_type="binary_classification",
    target="binary_label",
    model="TF-IDF + Logistic",
)


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


def read_transcript(path_value: Any) -> tuple[str, dict[str, Any]]:
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
    texts = [value.strip() for value in transcript["Text"].tolist()]
    non_empty = [value for value in texts if value]
    confidence = pd.to_numeric(transcript.get("Confidence"), errors="coerce")
    stats = {
        "transcript_turn_count": int(len(transcript)),
        "non_empty_turn_count": int(len(non_empty)),
        "empty_turn_count": int(len(texts) - len(non_empty)),
        "mean_asr_confidence": float(confidence.mean()) if confidence.notna().any() else None,
    }
    return "\n".join(non_empty), stats


def build_subject_table(manifest_path: Path) -> pd.DataFrame:
    manifest = pd.read_csv(manifest_path)
    required = {
        "subject_id",
        "text_path",
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
        & manifest["text_path"].notna()
        & manifest["phq8_total"].notna()
        & manifest["binary_label"].notna()
        & manifest["official_split"].isin(["train", "dev"])
    ].copy()
    if usable.empty:
        raise ValueError("no usable E-DAIC train/dev manifest rows")
    if usable["subject_id"].duplicated().any():
        dupes = sorted(usable.loc[usable["subject_id"].duplicated(), "subject_id"].astype(str).unique())
        raise ValueError(f"E-DAIC manifest should have one row per subject, duplicates observed: {dupes[:10]}")

    rows: list[dict[str, Any]] = []
    for _, row in usable.sort_values("subject_id").iterrows():
        text, stats = read_transcript(row["text_path"])
        rows.append(
            {
                "subject_id": str(row["subject_id"]),
                "split": str(row["official_split"]),
                "text": text,
                "phq8_total": float(row["phq8_total"]),
                "binary_label": int(row["binary_label"]),
                **stats,
            }
        )
    table = pd.DataFrame(rows).sort_values("subject_id").reset_index(drop=True)
    split_counts = table["split"].value_counts().to_dict()
    if split_counts.get("train", 0) <= 0 or split_counts.get("dev", 0) <= 0:
        raise ValueError(f"E-DAIC split must contain train and dev subjects, observed {split_counts}")
    train_subjects = set(table.loc[table["split"] == "train", "subject_id"])
    dev_subjects = set(table.loc[table["split"] == "dev", "subject_id"])
    overlap = sorted(train_subjects & dev_subjects)
    if overlap:
        raise ValueError(f"subject-level train/dev overlap detected: {overlap[:10]}")
    empty_subjects = table.loc[~table["text"].astype(str).str.strip().astype(bool), "subject_id"].tolist()
    if empty_subjects:
        raise ValueError(f"E-DAIC subjects with empty transcript text: {empty_subjects[:10]}")
    return table


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
        "transcript_turn_count": int(row["transcript_turn_count"]),
        "non_empty_turn_count": int(row["non_empty_turn_count"]),
        "empty_turn_count": int(row["empty_turn_count"]),
        "mean_asr_confidence": row["mean_asr_confidence"],
    }


def run_seed(table: pd.DataFrame, seed: int) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    train = table[table["split"] == "train"].reset_index(drop=True)
    dev = table[table["split"] == "dev"].reset_index(drop=True)

    ridge = Pipeline([("tfidf", vectorizer()), ("ridge", Ridge(alpha=FIXED_RIDGE_ALPHA, solver="lsqr"))])
    ridge.fit(train["text"], train["phq8_total"].to_numpy(dtype=np.float64))
    regression_pred = ridge.predict(dev["text"])
    clip_low = float(train["phq8_total"].min())
    clip_high = float(train["phq8_total"].max())
    regression_pred = np.clip(regression_pred, clip_low, clip_high)

    logistic = Pipeline(
        [
            ("tfidf", vectorizer()),
            (
                "logistic",
                LogisticRegression(
                    C=FIXED_LOGISTIC_C,
                    class_weight="balanced",
                    max_iter=1000,
                    random_state=seed,
                    solver="liblinear",
                ),
            ),
        ]
    )
    logistic.fit(train["text"], train["binary_label"].astype(int))
    class_pred = logistic.predict(dev["text"])
    class_score = logistic.predict_proba(dev["text"])[:, 1]

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
        "ridge_alpha": float(FIXED_RIDGE_ALPHA),
        "logistic_c": float(FIXED_LOGISTIC_C),
        "clip_low": float(clip_low),
        "clip_high": float(clip_high),
        "clipped_regression_predictions": int(np.sum((ridge.predict(dev["text"]) < clip_low) | (ridge.predict(dev["text"]) > clip_high))),
        "subject_overlap": int(len(train_subjects & dev_subjects)),
    }


def write_report(out_dir: Path, summary: dict[str, Any]) -> None:
    lines = [
        "# E-DAIC Text TF-IDF Phase 2 Baselines",
        "",
        f"Generated: `{summary['generated_at']}`",
        "",
        "## Protocol",
        "",
        "- Input interface: manifest-resolved `text_path` values from `datasets/manifests/edaic_subjects.csv`.",
        "- Unit of prediction: one row per dev subject per seed.",
        "- Text source: transcript ASR `Text` column concatenated in timestamp order.",
        "- The transcript files do not expose a speaker column, so interviewer-only and participant-only controls are separate RQ2 work.",
        "- Raw transcript text is read for TF-IDF fitting but is not written to outputs.",
        "- Hyperparameters are fixed a priori; no dev or test labels are used for tuning.",
        "- No test split is used.",
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
        "",
        "## Output Files",
        "",
        "- `edaic_text_tfidf_predictions.csv`",
        "- `phase2_metrics_by_seed.csv`",
        "- `phase2_metric_summary.csv`",
        "- `edaic_text_tfidf_run_summary.json`",
    ]
    (out_dir / "edaic_text_tfidf_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest-path", type=Path, default=MANIFEST_PATH)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--bootstrap-resamples", type=int, default=1000)
    args = parser.parse_args()

    table = build_subject_table(args.manifest_path)
    all_predictions: list[dict[str, Any]] = []
    seed_summaries: list[dict[str, Any]] = []
    for seed in SEEDS:
        predictions, seed_summary = run_seed(table, seed)
        all_predictions.extend(predictions)
        seed_summaries.append(seed_summary)

    args.out_dir.mkdir(parents=True, exist_ok=True)
    predictions_frame = pd.DataFrame(all_predictions)
    predictions_path = args.out_dir / "edaic_text_tfidf_predictions.csv"
    predictions_frame.to_csv(predictions_path, index=False)

    metrics_by_seed, metric_summary = metric_records(
        predictions_frame,
        bootstrap_resamples=args.bootstrap_resamples,
        seed=20260727,
    )
    metrics_by_seed.to_csv(args.out_dir / "phase2_metrics_by_seed.csv", index=False)
    metric_summary.to_csv(args.out_dir / "phase2_metric_summary.csv", index=False)

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
        "transcript_turn_count_min": int(table["transcript_turn_count"].min()),
        "transcript_turn_count_max": int(table["transcript_turn_count"].max()),
        "empty_turn_count": int(table["empty_turn_count"].sum()),
        "mean_asr_confidence": float(table["mean_asr_confidence"].mean()),
        "text_source": "ASR transcript Text column in timestamp order",
        "speaker_column_available": False,
        "interviewer_participant_control_included": False,
        "subject_overlap_violations": int(sum(row["subject_overlap"] for row in seed_summaries)),
        "no_test_split_used": True,
        "raw_text_written": False,
        "seed_summaries": seed_summaries,
    }
    (args.out_dir / "edaic_text_tfidf_run_summary.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=True, sort_keys=True),
        encoding="utf-8",
    )
    write_report(args.out_dir, summary)
    print(f"Wrote {predictions_path}")
    print(f"Wrote {args.out_dir / 'phase2_metric_summary.csv'}")


if __name__ == "__main__":
    main()
