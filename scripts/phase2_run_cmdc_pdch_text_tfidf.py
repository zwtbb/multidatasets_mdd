#!/usr/bin/env python3
"""Run Phase 2 CMDC/PDCH text TF-IDF baselines from the split layer.

The runner uses manifest-resolved text paths and the generated subject split
layer. It aggregates valid text segments to one row per subject, uses fixed
baseline hyperparameters, and writes prediction/metric artifacts without
persisting raw text.
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
from sklearn.linear_model import LogisticRegression, Ridge
from sklearn.pipeline import Pipeline

from phase2_metrics import metric_records


ROOT = Path("/root/autodl-tmp")
MANIFEST_DIR = ROOT / "datasets" / "manifests"
SPLIT_PATH = ROOT / "datasets" / "splits" / "phase2_subject_splits.csv"
DEFAULT_OUT_DIR = ROOT / "analysis" / "phase2_baselines" / "cmdc_pdch_text_tfidf"
SEEDS = [0, 1, 2, 3, 4]
FIXED_RIDGE_ALPHA = 10.0
FIXED_LOGISTIC_C = 1.0


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
        run_id="cmdc_text_binary_tfidf_logistic",
        dataset_id="cmdc",
        display_dataset="CMDC",
        modality="Text",
        task="MDD classification",
        task_type="binary_classification",
        target="binary_label",
        model="TF-IDF + Logistic",
        protocol_id="cmdc_binary_subject_cv",
    ),
    BaselineSpec(
        run_id="cmdc_text_phq9_tfidf_ridge",
        dataset_id="cmdc",
        display_dataset="CMDC",
        modality="Text",
        task="PHQ-9 regression",
        task_type="severity_regression",
        target="phq9_total",
        model="TF-IDF + Ridge",
        protocol_id="cmdc_phq9_subject_cv",
    ),
    BaselineSpec(
        run_id="pdch_text_hamd17_tfidf_ridge",
        dataset_id="pdch",
        display_dataset="PDCH",
        modality="Text",
        task="HAMD-17 regression",
        task_type="severity_regression",
        target="hamd17_total",
        model="TF-IDF + Ridge",
        protocol_id="pdch_hamd17_subject_cv_fallback",
    ),
]


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


def build_subject_table(spec: BaselineSpec, split_subjects: set[str]) -> pd.DataFrame:
    manifest = read_manifest(spec.dataset_id)
    required = {"subject_id", "text_path", spec.target}
    missing = required - set(manifest.columns)
    if missing:
        raise ValueError(f"{spec.dataset_id} manifest missing columns: {', '.join(sorted(missing))}")
    usable = manifest[manifest["subject_id"].astype(str).isin(split_subjects)].copy()
    if "file_valid" in usable.columns:
        usable = usable[usable["file_valid"].fillna(False).astype(bool)].copy()
    usable = usable[usable["text_path"].notna() & usable[spec.target].notna()].copy()
    if usable.empty:
        raise ValueError(f"no usable rows for {spec.run_id}")

    rows: list[dict[str, Any]] = []
    for subject_id, group in usable.groupby("subject_id", sort=False):
        labels = group[spec.target].dropna().unique()
        if len(labels) != 1:
            raise ValueError(f"{spec.run_id}:{subject_id} has inconsistent labels: {labels[:5]}")
        group = group.assign(_segment_key=group.get("segment_id", pd.Series([""] * len(group))).astype(str))
        group = group.sort_values("_segment_key", key=lambda series: series.map(lambda item: tuple(natural_key(item))))
        texts = [read_text(path) for path in group["text_path"]]
        rows.append(
            {
                "subject_id": str(subject_id),
                "text": "\n".join(texts),
                spec.target: float(labels[0]),
                "text_segment_count": int(len(texts)),
                "empty_text_segments": int(sum(1 for text in texts if not text.strip())),
            }
        )
    table = pd.DataFrame(rows).sort_values("subject_id", key=lambda series: series.map(lambda item: tuple(natural_key(item)))).reset_index(drop=True)
    observed_subjects = set(table["subject_id"].astype(str))
    missing_subjects = sorted(split_subjects - observed_subjects, key=natural_key)
    if missing_subjects:
        raise ValueError(f"{spec.run_id} split subjects missing usable text rows: {missing_subjects[:10]}")
    return table


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
        "text_segment_count": int(row["text_segment_count"]),
        "empty_text_segments": int(row["empty_text_segments"]),
    }


def run_spec(spec: BaselineSpec, split_path: Path) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    folds = load_protocol_splits(split_path, spec)
    split_subjects = {subject for roles in folds.values() for values in roles.values() for subject in values}
    table = build_subject_table(spec, split_subjects)
    table_by_subject = table.set_index("subject_id", drop=False)
    predictions: list[dict[str, Any]] = []
    fold_summaries: list[dict[str, Any]] = []

    for seed in SEEDS:
        for fold, roles in folds.items():
            train = table_by_subject.loc[roles["train"]].reset_index(drop=True)
            validation = table_by_subject.loc[roles["validation"]].reset_index(drop=True)
            if spec.task_type == "severity_regression":
                alpha = FIXED_RIDGE_ALPHA
                model = Pipeline([("tfidf", vectorizer()), ("ridge", Ridge(alpha=alpha, solver="lsqr"))])
                model.fit(train["text"], train[spec.target].to_numpy(dtype=np.float64))
                y_pred = model.predict(validation["text"])
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
                        "ridge_alpha": float(alpha),
                        "train_subjects": int(len(train)),
                        "validation_subjects": int(len(validation)),
                    }
                )
            elif spec.task_type == "binary_classification":
                c_value = FIXED_LOGISTIC_C
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
                model.fit(train["text"], train[spec.target].astype(int))
                y_pred = model.predict(validation["text"])
                y_score = model.predict_proba(validation["text"])[:, 1]
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
                        "logistic_c": float(c_value),
                        "train_subjects": int(len(train)),
                        "validation_subjects": int(len(validation)),
                        "train_positive_subjects": int(train[spec.target].astype(int).sum()),
                        "validation_positive_subjects": int(validation[spec.target].astype(int).sum()),
                    }
                )
            else:
                raise ValueError(f"unsupported task type for {spec.run_id}: {spec.task_type}")

    subject_overlap_violations = 0
    for fold, roles in folds.items():
        subject_overlap_violations += int(bool(set(roles["train"]) & set(roles["validation"])))
    return predictions, {
        "run_id": spec.run_id,
        "dataset": spec.display_dataset,
        "target": spec.target,
        "protocol_id": spec.protocol_id,
        "subject_count": int(len(split_subjects)),
        "fold_count": int(len(folds)),
        "subject_overlap_violations": int(subject_overlap_violations),
        "text_segment_count_min": int(table["text_segment_count"].min()),
        "text_segment_count_max": int(table["text_segment_count"].max()),
        "empty_text_segment_count": int(table["empty_text_segments"].sum()),
        "fold_summaries": fold_summaries,
    }


def write_report(out_dir: Path, summary: dict[str, Any]) -> None:
    lines = [
        "# CMDC/PDCH Text TF-IDF Phase 2 Baselines",
        "",
        f"Generated: `{summary['generated_at']}`",
        "",
        "## Protocol",
        "",
        "- Input interface: manifest-resolved `text_path` values and `datasets/splits/phase2_subject_splits.csv`.",
        "- Unit of prediction: one row per subject per seed after outer subject-level CV.",
        "- Text aggregation: valid text segments concatenated in natural segment order.",
        "- Raw text is read for TF-IDF fitting but is not written to outputs.",
        "- Hyperparameters are fixed a priori; no validation or test labels are used for tuning.",
        "- No test split is used.",
        "",
        "## Audit",
        "",
        f"- Runs: `{summary['runs']}`",
        f"- Seeds: `{summary['seeds']}`",
        f"- Bootstrap resamples: `{summary['bootstrap_resamples']}`",
        f"- Prediction rows: `{summary['prediction_rows']}`",
        f"- Subject overlap violations: `{summary['subject_overlap_violations']}`",
        f"- Raw text written: `{summary['raw_text_written']}`",
        "",
        "## Output Files",
        "",
        "- `cmdc_pdch_text_tfidf_predictions.csv`",
        "- `phase2_metrics_by_seed.csv`",
        "- `phase2_metric_summary.csv`",
        "- `cmdc_pdch_text_tfidf_run_summary.json`",
    ]
    (out_dir / "cmdc_pdch_text_tfidf_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--split-path", type=Path, default=SPLIT_PATH)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--bootstrap-resamples", type=int, default=1000)
    args = parser.parse_args()

    all_predictions: list[dict[str, Any]] = []
    run_summaries: list[dict[str, Any]] = []
    for spec in SPECS:
        predictions, run_summary = run_spec(spec, args.split_path)
        all_predictions.extend(predictions)
        run_summaries.append(run_summary)

    args.out_dir.mkdir(parents=True, exist_ok=True)
    predictions_frame = pd.DataFrame(all_predictions)
    predictions_path = args.out_dir / "cmdc_pdch_text_tfidf_predictions.csv"
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
        "runs": [spec.run_id for spec in SPECS],
        "seeds": SEEDS,
        "seed_count": len(SEEDS),
        "bootstrap_resamples": int(args.bootstrap_resamples),
        "prediction_rows": int(len(predictions_frame)),
        "run_summaries": run_summaries,
        "subject_overlap_violations": subject_overlap_violations,
        "no_test_split_used": True,
        "raw_text_written": False,
    }
    (args.out_dir / "cmdc_pdch_text_tfidf_run_summary.json").write_text(
        json.dumps(run_summary, indent=2, ensure_ascii=True, sort_keys=True),
        encoding="utf-8",
    )
    write_report(args.out_dir, run_summary)
    print(f"Wrote {predictions_path}")
    print(f"Wrote {args.out_dir / 'phase2_metric_summary.csv'}")


if __name__ == "__main__":
    main()
