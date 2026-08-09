#!/usr/bin/env python3
"""Run Phase 2 EATD text TF-IDF baselines.

The runner uses the generated subject manifest as its input interface, aggregates
EATD positive/neutral/negative text to one row per subject, performs train-only
hyperparameter selection, and writes prediction/metric artifacts without
persisting raw text.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression, Ridge
from sklearn.metrics import mean_absolute_error
from sklearn.model_selection import KFold, StratifiedKFold
from sklearn.pipeline import Pipeline

from phase2_metrics import classification_metrics, metric_records, regression_metrics


ROOT = Path("/root/autodl-tmp")
MANIFEST_PATH = ROOT / "datasets" / "manifests" / "eatd_subjects.csv"
DEFAULT_OUT_DIR = ROOT / "analysis" / "phase2_baselines" / "eatd_text_tfidf"
SEEDS = [0, 1, 2, 3, 4]
VALENCE_ORDER = ["positive", "neutral", "negative"]


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
    run_id="eatd_text_sds_tfidf_ridge",
    dataset="EATD-Corpus",
    modality="Text",
    task="SDS regression",
    task_type="severity_regression",
    target="sds_total",
    model="TF-IDF + Ridge",
)

CLASSIFICATION_SPEC = BaselineSpec(
    run_id="eatd_text_binary_tfidf_logistic",
    dataset="EATD-Corpus",
    modality="Text",
    task="binary depression classification",
    task_type="binary_classification",
    target="binary_label",
    model="TF-IDF + Logistic",
)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def read_text(path_value: Any) -> str:
    path = Path(str(path_value))
    if not path.exists():
        raise FileNotFoundError(f"manifest text path missing: {path}")
    return path.read_text(encoding="utf-8", errors="ignore").strip()


def build_subject_table(manifest_path: Path) -> pd.DataFrame:
    manifest = pd.read_csv(manifest_path)
    required = {
        "subject_id",
        "valence",
        "text_path",
        "sds_total",
        "binary_label",
        "official_split",
        "file_valid",
    }
    missing = required - set(manifest.columns)
    if missing:
        raise ValueError(f"EATD manifest missing columns: {', '.join(sorted(missing))}")
    usable = manifest[
        (manifest["file_valid"].fillna(False).astype(bool))
        & manifest["text_path"].notna()
        & manifest["sds_total"].notna()
        & manifest["binary_label"].notna()
        & manifest["official_split"].isin(["train", "validation"])
    ].copy()
    if usable.empty:
        raise ValueError("no usable EATD manifest rows")

    rows: list[dict[str, Any]] = []
    for subject_id, group in usable.groupby("subject_id", sort=True):
        by_valence = {str(row["valence"]): row for _, row in group.iterrows()}
        missing_valence = [valence for valence in VALENCE_ORDER if valence not in by_valence]
        if missing_valence:
            raise ValueError(f"{subject_id} missing text valence rows: {missing_valence}")
        texts = [read_text(by_valence[valence]["text_path"]) for valence in VALENCE_ORDER]
        label_rows = group.drop_duplicates("subject_id")
        rows.append(
            {
                "subject_id": str(subject_id),
                "split": str(label_rows.iloc[0]["official_split"]),
                "text": "\n".join(texts),
                "sds_total": float(label_rows.iloc[0]["sds_total"]),
                "binary_label": int(label_rows.iloc[0]["binary_label"]),
                "text_segment_count": int(len(texts)),
            }
        )
    table = pd.DataFrame(rows).sort_values("subject_id").reset_index(drop=True)
    split_counts = table["split"].value_counts().to_dict()
    if split_counts.get("train", 0) <= 0 or split_counts.get("validation", 0) <= 0:
        raise ValueError(f"EATD split must contain train and validation subjects, observed {split_counts}")
    train_subjects = set(table.loc[table["split"] == "train", "subject_id"])
    val_subjects = set(table.loc[table["split"] == "validation", "subject_id"])
    overlap = sorted(train_subjects & val_subjects)
    if overlap:
        raise ValueError(f"subject-level split overlap detected: {overlap[:10]}")
    return table


def vectorizer() -> TfidfVectorizer:
    return TfidfVectorizer(
        analyzer="char",
        ngram_range=(2, 5),
        min_df=2,
        max_features=50000,
        sublinear_tf=True,
        norm="l2",
    )


def regression_cv_score(y_true: np.ndarray, y_pred: np.ndarray) -> tuple[float, float]:
    metrics = regression_metrics(y_true, y_pred)
    ccc = metrics["CCC"]
    mae = mean_absolute_error(y_true, y_pred)
    return float(ccc) if ccc is not None else -1.0e9, float(mae)


def choose_ridge_alpha(train: pd.DataFrame, seed: int) -> float:
    alphas = [0.1, 1.0, 10.0, 100.0]
    folds = KFold(n_splits=5, shuffle=True, random_state=seed)
    best: tuple[float, float, float] | None = None
    texts = train["text"].to_numpy()
    labels = train["sds_total"].to_numpy(dtype=np.float64)
    for alpha in alphas:
        ccc_scores: list[float] = []
        mae_scores: list[float] = []
        for train_idx, dev_idx in folds.split(texts):
            model = Pipeline([("tfidf", vectorizer()), ("ridge", Ridge(alpha=alpha))])
            model.fit(texts[train_idx], labels[train_idx])
            pred = model.predict(texts[dev_idx])
            ccc, mae = regression_cv_score(labels[dev_idx], pred)
            ccc_scores.append(ccc)
            mae_scores.append(mae)
        candidate = (float(np.mean(ccc_scores)), -float(np.mean(mae_scores)), alpha)
        if best is None or candidate > best:
            best = candidate
    if best is None:
        raise RuntimeError("ridge alpha selection failed")
    return best[2]


def choose_logistic_c(train: pd.DataFrame, seed: int) -> float:
    values = [0.01, 0.1, 1.0, 10.0]
    labels = train["binary_label"].to_numpy(dtype=np.int64)
    texts = train["text"].to_numpy()
    folds = StratifiedKFold(n_splits=5, shuffle=True, random_state=seed)
    best: tuple[float, float] | None = None
    for c_value in values:
        scores: list[float] = []
        for train_idx, dev_idx in folds.split(texts, labels):
            model = Pipeline(
                [
                    ("tfidf", vectorizer()),
                    (
                        "logistic",
                        LogisticRegression(
                            C=c_value,
                            class_weight="balanced",
                            max_iter=1000,
                            random_state=seed,
                            solver="liblinear",
                        ),
                    ),
                ]
            )
            model.fit(texts[train_idx], labels[train_idx])
            pred = model.predict(texts[dev_idx])
            score = classification_metrics(labels[dev_idx], pred).get("Macro-F1")
            scores.append(float(score) if score is not None else 0.0)
        candidate = (float(np.mean(scores)), c_value)
        if best is None or candidate > best:
            best = candidate
    if best is None:
        raise RuntimeError("logistic C selection failed")
    return best[1]


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
    }


def run_seed(table: pd.DataFrame, seed: int) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    train = table[table["split"] == "train"].reset_index(drop=True)
    validation = table[table["split"] == "validation"].reset_index(drop=True)

    ridge_alpha = choose_ridge_alpha(train, seed)
    ridge = Pipeline([("tfidf", vectorizer()), ("ridge", Ridge(alpha=ridge_alpha))])
    ridge.fit(train["text"], train["sds_total"])
    regression_pred = ridge.predict(validation["text"])

    logistic_c = choose_logistic_c(train, seed)
    logistic = Pipeline(
        [
            ("tfidf", vectorizer()),
            (
                "logistic",
                LogisticRegression(
                    C=logistic_c,
                    class_weight="balanced",
                    max_iter=1000,
                    random_state=seed,
                    solver="liblinear",
                ),
            ),
        ]
    )
    logistic.fit(train["text"], train["binary_label"].astype(int))
    class_pred = logistic.predict(validation["text"])
    class_score = logistic.predict_proba(validation["text"])[:, 1]

    predictions: list[dict[str, Any]] = []
    for idx, row in validation.iterrows():
        predictions.append(
            {
                **prediction_meta(REGRESSION_SPEC, seed, row),
                "y_true": float(row["sds_total"]),
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
    return predictions, {
        "seed": int(seed),
        "ridge_alpha": ridge_alpha,
        "logistic_c": logistic_c,
        "train_subjects": int(len(train)),
        "validation_subjects": int(len(validation)),
        "train_positive_subjects": int(train["binary_label"].sum()),
        "validation_positive_subjects": int(validation["binary_label"].sum()),
    }


def write_report(out_dir: Path, summary: dict[str, Any]) -> None:
    lines = [
        "# EATD Text TF-IDF Phase 2 Baseline",
        "",
        f"Generated: `{summary['generated_at']}`",
        "",
        "## Protocol",
        "",
        "- Input interface: `datasets/manifests/eatd_subjects.csv`.",
        "- Unit of prediction: one row per subject.",
        "- Text aggregation: positive, neutral, and negative transcripts concatenated in fixed order.",
        "- Raw text is read for TF-IDF fitting but is not written to outputs.",
        "- Hyperparameters are selected only inside the train split.",
        "- Validation split is used only for reporting.",
        "- No test split is used.",
        "",
        "## Audit",
        "",
        f"- Train subjects: `{summary['train_subjects']}`",
        f"- Validation subjects: `{summary['validation_subjects']}`",
        f"- Subject overlap: `{summary['subject_overlap']}`",
        f"- Seeds: `{summary['seeds']}`",
        f"- Bootstrap resamples: `{summary['bootstrap_resamples']}`",
        f"- Prediction rows: `{summary['prediction_rows']}`",
        "",
        "## Output Files",
        "",
        "- `eatd_text_tfidf_predictions.csv`",
        "- `phase2_metrics_by_seed.csv`",
        "- `phase2_metric_summary.csv`",
        "- `eatd_text_tfidf_run_summary.json`",
    ]
    (out_dir / "eatd_text_tfidf_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, default=MANIFEST_PATH)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--bootstrap-resamples", type=int, default=1000)
    args = parser.parse_args()

    table = build_subject_table(args.manifest)
    train_subjects = set(table.loc[table["split"] == "train", "subject_id"])
    validation_subjects = set(table.loc[table["split"] == "validation", "subject_id"])
    subject_overlap = sorted(train_subjects & validation_subjects)
    all_predictions: list[dict[str, Any]] = []
    seed_summaries: list[dict[str, Any]] = []
    for seed in SEEDS:
        predictions, seed_summary = run_seed(table, seed)
        all_predictions.extend(predictions)
        seed_summaries.append(seed_summary)

    args.out_dir.mkdir(parents=True, exist_ok=True)
    predictions_frame = pd.DataFrame(all_predictions)
    predictions_path = args.out_dir / "eatd_text_tfidf_predictions.csv"
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
        "train_subjects": int(len(train_subjects)),
        "validation_subjects": int(len(validation_subjects)),
        "subject_overlap": int(len(subject_overlap)),
        "seeds": SEEDS,
        "seed_count": len(SEEDS),
        "bootstrap_resamples": int(args.bootstrap_resamples),
        "prediction_rows": int(len(predictions_frame)),
        "runs": [REGRESSION_SPEC.run_id, CLASSIFICATION_SPEC.run_id],
        "seed_summaries": seed_summaries,
        "no_test_split_used": True,
        "raw_text_written": False,
    }
    (args.out_dir / "eatd_text_tfidf_run_summary.json").write_text(
        json.dumps(run_summary, indent=2, ensure_ascii=True, sort_keys=True),
        encoding="utf-8",
    )
    write_report(args.out_dir, run_summary)
    print(f"Wrote {predictions_path}")
    print(f"Wrote {args.out_dir / 'phase2_metric_summary.csv'}")


if __name__ == "__main__":
    main()
