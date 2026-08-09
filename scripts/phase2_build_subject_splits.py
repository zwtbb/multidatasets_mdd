#!/usr/bin/env python3
"""Build Phase 2 subject-level CV split artifacts for blocked datasets.

The output contains only subject/fold/role/protocol metadata. Labels are used
transiently for stratification but are not written to split artifacts.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import os
import random
from collections import Counter, defaultdict
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
from sklearn.model_selection import KFold, StratifiedKFold


ROOT = Path("/root/autodl-tmp")
MANIFEST_DIR = ROOT / "datasets" / "manifests"
DEFAULT_OUT = ROOT / "datasets" / "splits" / "phase2_subject_splits.csv"
DEFAULT_SUMMARY = ROOT / "analysis" / "phase2_baselines" / "phase2_subject_splits_summary.json"
DEFAULT_REPORT = ROOT / "analysis" / "phase2_baselines" / "phase2_subject_splits_report.md"
PDCH_OFFICIAL_DIR = ROOT / "cache" / "official_baselines" / "PDCH"
N_SPLITS = 5
SEED = 20260727
PDCH_OFFICIAL_SEED = 0

SPLIT_COLUMNS = [
    "dataset",
    "protocol_id",
    "protocol_type",
    "target",
    "fold",
    "role",
    "subject_id",
    "train_task",
    "eval_task",
    "source",
]


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def read_subject_rows(dataset: str) -> pd.DataFrame:
    path = MANIFEST_DIR / f"{dataset}_subjects.csv"
    frame = pd.read_csv(path)
    return frame[frame["subject_id"].astype(str) != "none"].drop_duplicates("subject_id").copy()


def regression_bins(values: pd.Series, n_splits: int) -> np.ndarray | None:
    series = pd.to_numeric(values, errors="coerce")
    if series.notna().sum() < n_splits:
        return None
    try:
        bins = pd.qcut(series, q=min(5, series.notna().sum() // n_splits), labels=False, duplicates="drop")
    except ValueError:
        return None
    if bins.isna().any():
        return None
    counts = pd.Series(bins).value_counts()
    if counts.empty or int(counts.min()) < n_splits:
        return None
    return bins.to_numpy(dtype=np.int64)


def classification_bins(values: pd.Series, n_splits: int) -> np.ndarray | None:
    series = pd.to_numeric(values, errors="coerce")
    if series.isna().any():
        return None
    counts = series.astype(int).value_counts()
    if counts.empty or int(counts.min()) < n_splits:
        return None
    return series.astype(int).to_numpy()


def fold_indices(subjects: pd.DataFrame, target: str, task_type: str, n_splits: int, seed: int) -> tuple[list[tuple[np.ndarray, np.ndarray]], str]:
    values = subjects[target]
    y = classification_bins(values, n_splits) if task_type == "classification" else regression_bins(values, n_splits)
    indices = np.arange(len(subjects))
    if y is not None:
        splitter = StratifiedKFold(n_splits=n_splits, shuffle=True, random_state=seed)
        return list(splitter.split(indices, y)), "stratified"
    splitter = KFold(n_splits=n_splits, shuffle=True, random_state=seed)
    return list(splitter.split(indices)), "kfold"


def add_cv_rows(
    rows: list[dict[str, Any]],
    subjects: pd.DataFrame,
    dataset: str,
    target: str,
    task_type: str,
    protocol_id: str,
    protocol_type: str,
    source: str,
    train_task: str = "",
    eval_task: str = "",
) -> dict[str, Any]:
    folds, split_method = fold_indices(subjects, target, task_type, N_SPLITS, SEED)
    for fold_index, (train_idx, validation_idx) in enumerate(folds, start=1):
        for role, selected in [("train", train_idx), ("validation", validation_idx)]:
            for subject_id in subjects.iloc[selected]["subject_id"].astype(str):
                rows.append(
                    {
                        "dataset": dataset,
                        "protocol_id": protocol_id,
                        "protocol_type": protocol_type,
                        "target": target,
                        "fold": f"fold_{fold_index}",
                        "role": role,
                        "subject_id": subject_id,
                        "train_task": train_task,
                        "eval_task": eval_task,
                        "source": source,
                    }
                )
    return {
        "dataset": dataset,
        "target": target,
        "protocol_id": protocol_id,
        "protocol_type": protocol_type,
        "source": source,
        "subjects": int(len(subjects)),
        "folds": int(len(folds)),
        "split_method": split_method,
    }


def add_fixed_fold_rows(
    rows: list[dict[str, Any]],
    folds: list[list[str]],
    dataset: str,
    target: str,
    protocol_id: str,
    protocol_type: str,
    source: str,
    train_task: str = "",
    eval_task: str = "",
) -> dict[str, Any]:
    all_subjects = sorted({str(subject_id) for fold in folds for subject_id in fold})
    for fold_index, validation_subjects in enumerate(folds, start=1):
        validation_set = {str(subject_id) for subject_id in validation_subjects}
        train_subjects = [subject_id for subject_id in all_subjects if subject_id not in validation_set]
        if not validation_set:
            raise ValueError(f"{protocol_id}: fold_{fold_index} has no validation subjects")
        if set(train_subjects) & validation_set:
            raise ValueError(f"{protocol_id}: fold_{fold_index} train/validation overlap")
        for role, selected in [("train", train_subjects), ("validation", sorted(validation_set))]:
            for subject_id in selected:
                rows.append(
                    {
                        "dataset": dataset,
                        "protocol_id": protocol_id,
                        "protocol_type": protocol_type,
                        "target": target,
                        "fold": f"fold_{fold_index}",
                        "role": role,
                        "subject_id": str(subject_id),
                        "train_task": train_task,
                        "eval_task": eval_task,
                        "source": source,
                    }
                )
    return {
        "dataset": dataset,
        "target": target,
        "protocol_id": protocol_id,
        "protocol_type": protocol_type,
        "source": source,
        "subjects": int(len(all_subjects)),
        "folds": int(len(folds)),
        "split_method": "fixed_fold_subject_split",
    }


def target_subjects(dataset: str, target: str, require_modalities: list[str] | None = None) -> pd.DataFrame:
    rows = pd.read_csv(MANIFEST_DIR / f"{dataset}_subjects.csv")
    rows = rows[rows["subject_id"].astype(str) != "none"].copy()
    if target not in rows.columns:
        raise ValueError(f"{dataset} manifest missing target column: {target}")
    if "file_valid" in rows.columns:
        rows = rows[rows["file_valid"].fillna(False).astype(bool)].copy()
    rows = rows[rows[target].notna()].copy()
    if require_modalities:
        for modality in require_modalities:
            column = {"text": "text_path", "audio": "audio_path", "video": "video_path", "gait": "gait_path"}[modality]
            rows = rows[rows[column].notna()].copy()
    target_counts = rows.groupby("subject_id")[target].nunique(dropna=True)
    inconsistent_subjects = sorted(target_counts[target_counts > 1].index.astype(str).tolist())
    if inconsistent_subjects:
        raise ValueError(f"{dataset}:{target} inconsistent subject labels: {inconsistent_subjects[:10]}")
    sort_columns = [column for column in ["subject_id", "session_id", "segment_id"] if column in rows.columns]
    subjects = (
        rows.sort_values(sort_columns)
        .drop_duplicates("subject_id")[["subject_id", target]]
        .sort_values("subject_id")
        .reset_index(drop=True)
    )
    if len(subjects) < N_SPLITS:
        raise ValueError(f"{dataset}:{target} has fewer than {N_SPLITS} subjects")
    return subjects


def load_pdch_official_meta(labeled_subjects: set[str]) -> list[dict[str, Any]]:
    path = PDCH_OFFICIAL_DIR / "data_meta.json"
    if not path.exists():
        raise FileNotFoundError(
            f"PDCH official metadata missing: {path}. "
            "Clone https://github.com/Miraclemarvel55/PDCH into cache/official_baselines/PDCH first."
        )
    data = json.loads(path.read_text(encoding="utf-8"))
    required = {"dialogue_name", "总字词数", "不平衡度"}
    missing = required - set(data[0]) if data else required
    if missing:
        raise ValueError(f"PDCH official data_meta.json missing fields: {', '.join(sorted(missing))}")
    filtered = [item for item in data if str(item["dialogue_name"]) in labeled_subjects]
    observed = {str(item["dialogue_name"]) for item in filtered}
    missing_subjects = sorted(labeled_subjects - observed)
    if missing_subjects:
        raise ValueError(f"PDCH official metadata missing labeled subjects: {missing_subjects[:10]}")
    return filtered


def pdch_official_folds(items: list[dict[str, Any]], rng: random.Random) -> list[list[str]]:
    shuffled = list(items)
    rng.shuffle(shuffled)
    test_size = math.ceil(len(shuffled) / N_SPLITS)
    folds: list[list[str]] = []
    for fold_index in range(N_SPLITS):
        start = fold_index * test_size
        end = (fold_index + 1) * test_size
        folds.append([str(item["dialogue_name"]) for item in shuffled[start:end]])
    return folds


def add_pdch_official_cv_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    subjects = target_subjects("pdch", "hamd17_total", ["text", "audio"])
    metadata = load_pdch_official_meta(set(subjects["subject_id"].astype(str)))
    rng = random.Random(PDCH_OFFICIAL_SEED)
    summaries: list[dict[str, Any]] = []
    source = "official_pdch_generate_sft_conversation_seed0_no_labels_written"
    for protocol_key, official_column in [
        ("word_count", "总字词数"),
        ("imbalance", "不平衡度"),
    ]:
        sorted_meta = sorted(metadata, key=lambda item: float(item[official_column]))
        for subset_name, subset_items in [
            ("small", sorted_meta[:50]),
            ("big", sorted_meta[50:]),
        ]:
            folds = pdch_official_folds(subset_items, rng)
            summaries.append(
                add_fixed_fold_rows(
                    rows,
                    folds,
                    "pdch",
                    "hamd17_total",
                    f"pdch_hamd17_official_{protocol_key}_{subset_name}_cv",
                    "official_subject_cv",
                    source,
                )
            )
    return summaries


def build_rows() -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    rows: list[dict[str, Any]] = []
    summaries: list[dict[str, Any]] = []
    source = "deterministic_phase2_subject_cv_no_labels_written"

    summaries.append(
        add_cv_rows(
            rows,
            target_subjects("cmdc", "binary_label", ["text", "audio"]),
            "cmdc",
            "binary_label",
            "classification",
            "cmdc_binary_subject_cv",
            "subject_cv",
            source,
        )
    )
    summaries.append(
        add_cv_rows(
            rows,
            target_subjects("cmdc", "phq9_total", ["text", "audio"]),
            "cmdc",
            "phq9_total",
            "regression",
            "cmdc_phq9_subject_cv",
            "subject_cv",
            source,
        )
    )
    summaries.append(
        add_cv_rows(
            rows,
            target_subjects("cmdc", "hamd17_total", ["text", "audio"]),
            "cmdc",
            "hamd17_total",
            "regression",
            "cmdc_hamd17_subject_cv",
            "subject_cv",
            source,
        )
    )
    summaries.append(
        add_cv_rows(
            rows,
            target_subjects("pdch", "hamd17_total", ["text", "audio"]),
            "pdch",
            "hamd17_total",
            "regression",
            "pdch_hamd17_subject_cv_fallback",
            "subject_cv_fallback",
            source,
        )
    )
    summaries.extend(add_pdch_official_cv_rows(rows))
    summaries.append(
        add_cv_rows(
            rows,
            target_subjects("modma", "binary_label", ["audio"]),
            "modma",
            "binary_label",
            "classification",
            "modma_binary_subject_cv",
            "subject_cv",
            source,
        )
    )
    summaries.append(
        add_cv_rows(
            rows,
            target_subjects("modma", "phq9_total", ["audio"]),
            "modma",
            "phq9_total",
            "regression",
            "modma_phq9_subject_cv",
            "subject_cv",
            source,
        )
    )

    modma_binary = target_subjects("modma", "binary_label", ["audio"])
    modma_phq9 = target_subjects("modma", "phq9_total", ["audio"])
    modma_tasks = ["interview", "reading", "picture_description", "affective_task"]
    for task in modma_tasks:
        summaries.append(
            add_cv_rows(
                rows,
                modma_binary,
                "modma",
                "binary_label",
                "classification",
                f"modma_binary_task_specific_{task}",
                "task_specific",
                source,
                train_task=task,
                eval_task=task,
            )
        )
        summaries.append(
            add_cv_rows(
                rows,
                modma_phq9,
                "modma",
                "phq9_total",
                "regression",
                f"modma_phq9_task_specific_{task}",
                "task_specific",
                source,
                train_task=task,
                eval_task=task,
            )
        )
    for train_task in modma_tasks:
        for eval_task in modma_tasks:
            if train_task == eval_task:
                continue
            summaries.append(
                add_cv_rows(
                    rows,
                    modma_binary,
                    "modma",
                    "binary_label",
                    "classification",
                    f"modma_binary_cross_task_{train_task}_to_{eval_task}",
                    "cross_task",
                    source,
                    train_task=train_task,
                    eval_task=eval_task,
                )
            )
            summaries.append(
                add_cv_rows(
                    rows,
                    modma_phq9,
                    "modma",
                    "phq9_total",
                    "regression",
                    f"modma_phq9_cross_task_{train_task}_to_{eval_task}",
                    "cross_task",
                    source,
                    train_task=train_task,
                    eval_task=eval_task,
                )
            )
    return rows, summaries


def leakage_audit(rows: list[dict[str, Any]]) -> dict[str, Any]:
    by_protocol_fold: dict[tuple[str, str], dict[str, set[str]]] = defaultdict(lambda: {"train": set(), "validation": set()})
    for row in rows:
        key = (str(row["protocol_id"]), str(row["fold"]))
        by_protocol_fold[key][str(row["role"])].add(str(row["subject_id"]))
    overlaps = []
    role_counts = []
    for (protocol_id, fold), roles in sorted(by_protocol_fold.items()):
        overlap = sorted(roles["train"] & roles["validation"])
        if overlap:
            overlaps.append({"protocol_id": protocol_id, "fold": fold, "overlap_count": len(overlap)})
        role_counts.append(
            {
                "protocol_id": protocol_id,
                "fold": fold,
                "train_subjects": len(roles["train"]),
                "validation_subjects": len(roles["validation"]),
            }
        )
    return {
        "subject_overlap_violations": overlaps,
        "subject_overlap_violation_count": len(overlaps),
        "role_counts": role_counts,
    }


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=SPLIT_COLUMNS)
        writer.writeheader()
        for row in rows:
            writer.writerow({column: row.get(column, "") for column in SPLIT_COLUMNS})


def write_report(path: Path, summary: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    protocol_counts = Counter(item["protocol_type"] for item in summary["protocols"])
    dataset_counts = Counter(item["dataset"] for item in summary["protocols"])
    lines = [
        "# Phase 2 Subject-Level Split Layer",
        "",
        f"Generated: `{summary['generated_at']}`",
        "",
        "## Scope",
        "",
        "- Output contains subject/fold/role/protocol metadata only.",
        "- Labels are used transiently for stratification but are not written.",
        "- No raw text, audio, video, IMU arrays, feature paths, or model outputs are written.",
        "- Splits are subject-level; segment/task rows from the same subject must follow the subject assignment.",
        "",
        "## Coverage",
        "",
        f"- Split rows: `{summary['split_rows']}`",
        f"- Protocols: `{len(summary['protocols'])}`",
        f"- Protocol counts: `{dict(sorted(protocol_counts.items()))}`",
        f"- Dataset counts: `{dict(sorted(dataset_counts.items()))}`",
        "",
        "## Leakage Audit",
        "",
        f"- Subject overlap violations: `{summary['leakage_audit']['subject_overlap_violation_count']}`",
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--summary", type=Path, default=DEFAULT_SUMMARY)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    args = parser.parse_args()

    rows, protocol_summaries = build_rows()
    audit = leakage_audit(rows)
    if audit["subject_overlap_violation_count"]:
        raise RuntimeError("subject-level split overlap detected")
    summary = {
        "generated_at": utc_now(),
        "split_rows": len(rows),
        "split_path": str(args.out),
        "seed": SEED,
        "folds": N_SPLITS,
        "protocols": protocol_summaries,
        "leakage_audit": audit,
        "labels_written": False,
        "raw_data_written": False,
    }
    write_csv(args.out, rows)
    args.summary.parent.mkdir(parents=True, exist_ok=True)
    args.summary.write_text(json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8")
    write_report(args.report, summary)
    print(f"Wrote {args.out}")
    print(f"Wrote {args.summary}")
    print(f"Wrote {args.report}")


if __name__ == "__main__":
    main()
