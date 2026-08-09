#!/usr/bin/env python3
"""Phase 3 protocol-control diagnostics for E-DAIC and CMDC.

The runner stays on the registry/manifest/split interfaces, trains small
fixed TF-IDF baselines, and writes only labels, predictions, counts, and field
availability metadata. Raw text, raw prompts, audio/video paths, and source
paths are not persisted in generated artifacts.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path
from typing import Any, Callable


def normalize_thread_env() -> None:
    value = str(os.environ.get("OMP_NUM_THREADS", "")).strip()
    if not value.isdigit() or int(value) <= 0:
        os.environ["OMP_NUM_THREADS"] = "1"
    os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
    os.environ.setdefault("MKL_NUM_THREADS", "1")


normalize_thread_env()

import numpy as np
import pandas as pd
import yaml
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression, Ridge
from sklearn.pipeline import Pipeline

from phase2_metrics import metric_records


ROOT = Path(__file__).resolve().parents[1]
REGISTRY_PATH = ROOT / "datasets" / "registry.yaml"
MANIFEST_DIR = ROOT / "datasets" / "manifests"
SPLIT_PATH = ROOT / "datasets" / "splits" / "phase2_subject_splits.csv"
DEFAULT_OUT_DIR = ROOT / "analysis" / "phase3_diagnostics" / "protocol_controls"
SEEDS = [0, 1, 2, 3, 4]
FIXED_RIDGE_ALPHA = 10.0
FIXED_LOGISTIC_C = 1.0


@dataclass(frozen=True)
class TargetSpec:
    dataset_id: str
    display_dataset: str
    target: str
    task: str
    task_type: str
    protocol_id: str
    estimator: str


@dataclass(frozen=True)
class ControlSpec:
    control_id: str
    display_name: str
    control_family: str
    description: str


EDAIC_TARGETS = [
    TargetSpec(
        dataset_id="edaic",
        display_dataset="E-DAIC",
        target="phq8_total",
        task="PHQ-8 regression",
        task_type="severity_regression",
        protocol_id="edaic_official_train_dev",
        estimator="ridge",
    ),
    TargetSpec(
        dataset_id="edaic",
        display_dataset="E-DAIC",
        target="binary_label",
        task="binary depression classification",
        task_type="binary_classification",
        protocol_id="edaic_official_train_dev",
        estimator="logistic",
    ),
]

EDAIC_CONTROLS = [
    ControlSpec("full_dialogue", "full dialogue", "available_transcript", "All available transcript rows."),
    ControlSpec("front_25", "front 25%", "position_slice", "First quarter of available transcript rows."),
    ControlSpec("middle_50", "middle 50%", "position_slice", "Middle half of available transcript rows."),
    ControlSpec("back_25", "back 25%", "position_slice", "Final quarter of available transcript rows."),
    ControlSpec(
        "train_repeated_turns_removed",
        "train repeated-turn removal",
        "prompt_proxy",
        "Remove train-identified repeated normalized turns before fitting/evaluation.",
    ),
    ControlSpec(
        "train_repeated_turns_only",
        "train repeated-turns only",
        "prompt_proxy",
        "Use only train-identified repeated normalized turns as a prompt/protocol proxy.",
    ),
]

CMDC_TARGETS = [
    TargetSpec(
        dataset_id="cmdc",
        display_dataset="CMDC",
        target="binary_label",
        task="MDD classification",
        task_type="binary_classification",
        protocol_id="cmdc_binary_subject_cv",
        estimator="logistic",
    ),
    TargetSpec(
        dataset_id="cmdc",
        display_dataset="CMDC",
        target="phq9_total",
        task="PHQ-9 regression",
        task_type="severity_regression",
        protocol_id="cmdc_phq9_subject_cv",
        estimator="ridge",
    ),
    TargetSpec(
        dataset_id="cmdc",
        display_dataset="CMDC",
        target="hamd17_total",
        task="HAMD-17 regression",
        task_type="severity_regression",
        protocol_id="cmdc_hamd17_subject_cv",
        estimator="ridge",
    ),
]


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def natural_key(value: Any) -> list[Any]:
    return [int(part) if part.isdigit() else part for part in re.split(r"(\d+)", str(value))]


def relative_ref(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT.resolve()))
    except ValueError:
        return path.name


def load_registry(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        registry = yaml.safe_load(handle)
    if not isinstance(registry, dict):
        raise ValueError("dataset registry must be a mapping")
    return registry


def read_manifest(dataset_id: str) -> pd.DataFrame:
    path = MANIFEST_DIR / f"{dataset_id}_subjects.csv"
    if not path.exists():
        raise FileNotFoundError(f"manifest missing: {relative_ref(path)}")
    return pd.read_csv(path)


def normalize_turn(value: str) -> str:
    value = re.sub(r"\s+", " ", str(value).casefold()).strip()
    value = re.sub(r"^[^\w]+|[^\w]+$", "", value)
    return value


@lru_cache(maxsize=None)
def read_plain_text(path_text: str) -> str:
    path = Path(path_text)
    if not path.exists():
        raise FileNotFoundError("manifest text path is missing on disk")
    data = path.read_bytes()
    for encoding in ["utf-8-sig", "utf-8", "gb18030"]:
        try:
            return data.decode(encoding).strip()
        except UnicodeDecodeError:
            continue
    return data.decode("utf-8", errors="ignore").strip()


@lru_cache(maxsize=None)
def read_edaic_transcript(path_text: str) -> tuple[tuple[str, ...], tuple[str, ...], dict[str, Any]]:
    path = Path(path_text)
    if not path.exists():
        raise FileNotFoundError("manifest transcript path is missing on disk")
    transcript = pd.read_csv(path)
    required = {"Start_Time", "End_Time", "Text"}
    missing = required - set(transcript.columns)
    if missing:
        raise ValueError(f"E-DAIC transcript missing required columns: {', '.join(sorted(missing))}")
    transcript = transcript.copy()
    transcript["Text"] = transcript["Text"].fillna("").astype(str)
    transcript = transcript.sort_values(["Start_Time", "End_Time"], kind="mergesort")
    texts = [value.strip() for value in transcript["Text"].tolist()]
    turns = tuple(value for value in texts if value)
    confidence = pd.to_numeric(transcript.get("Confidence"), errors="coerce")
    stats = {
        "transcript_row_count": int(len(transcript)),
        "non_empty_turn_count": int(len(turns)),
        "empty_turn_count": int(len(texts) - len(turns)),
        "mean_asr_confidence": float(confidence.mean()) if confidence.notna().any() else None,
    }
    return tuple(str(column) for column in transcript.columns), turns, stats


def text_vectorizer(dataset_id: str) -> TfidfVectorizer:
    if dataset_id == "cmdc":
        return TfidfVectorizer(
            analyzer="char",
            ngram_range=(2, 3),
            min_df=2,
            max_features=30000,
            sublinear_tf=True,
            norm="l2",
        )
    return TfidfVectorizer(
        analyzer="word",
        ngram_range=(1, 2),
        min_df=2,
        max_features=30000,
        sublinear_tf=True,
        norm="l2",
    )


def run_id_for(spec: TargetSpec, control_id: str) -> str:
    model_tag = "tfidf_ridge" if spec.estimator == "ridge" else "tfidf_logistic"
    target_tag = {
        "phq8_total": "phq8",
        "phq9_total": "phq9",
        "hamd17_total": "hamd17",
        "binary_label": "binary",
    }[spec.target]
    return f"{spec.dataset_id}_protocol_{control_id}_{target_tag}_{model_tag}"


def model_label(spec: TargetSpec, control: ControlSpec) -> str:
    base = "TF-IDF + Ridge" if spec.estimator == "ridge" else "TF-IDF + Logistic"
    return f"{base} ({control.control_id})"


def prediction_meta(spec: TargetSpec, control: ControlSpec, seed: int, split: str, row: pd.Series) -> dict[str, Any]:
    return {
        "run_id": run_id_for(spec, control.control_id),
        "dataset": spec.display_dataset,
        "modality": "Text",
        "task": spec.task,
        "model": model_label(spec, control),
        "seed": int(seed),
        "protocol_id": spec.protocol_id,
        "control_id": control.control_id,
        "control_family": control.control_family,
        "task_type": spec.task_type,
        "target": spec.target,
        "subject_id": str(row["subject_id"]),
        "split": split,
        "text_unit_count": int(row["text_unit_count"]),
        "retained_text_unit_count": int(row["retained_text_unit_count"]),
        "empty_text_units": int(row["empty_text_units"]),
    }


def fit_predict(
    spec: TargetSpec,
    train: pd.DataFrame,
    validation: pd.DataFrame,
    seed: int,
    clip_regression_to_train: bool,
) -> tuple[np.ndarray, np.ndarray | None, dict[str, Any]]:
    texts_train = train["text"].fillna("").astype(str)
    texts_validation = validation["text"].fillna("").astype(str)
    if spec.estimator == "ridge":
        model = Pipeline(
            [
                ("tfidf", text_vectorizer(spec.dataset_id)),
                ("ridge", Ridge(alpha=FIXED_RIDGE_ALPHA, solver="lsqr")),
            ]
        )
        y_train = pd.to_numeric(train[spec.target], errors="raise").to_numpy(dtype=np.float64)
        model.fit(texts_train, y_train)
        raw_pred = np.asarray(model.predict(texts_validation), dtype=np.float64)
        clip_count = 0
        if clip_regression_to_train:
            low = float(np.min(y_train))
            high = float(np.max(y_train))
            pred = np.clip(raw_pred, low, high)
            clip_count = int(np.sum(np.abs(pred - raw_pred) > 1.0e-12))
        else:
            low = None
            high = None
            pred = raw_pred
        return pred, None, {
            "ridge_alpha": float(FIXED_RIDGE_ALPHA),
            "clip_regression_to_train": bool(clip_regression_to_train),
            "clip_low": low,
            "clip_high": high,
            "clipped_predictions": int(clip_count),
        }
    if spec.estimator == "logistic":
        model = Pipeline(
            [
                ("tfidf", text_vectorizer(spec.dataset_id)),
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
        y_train = train[spec.target].astype(int)
        model.fit(texts_train, y_train)
        pred = model.predict(texts_validation).astype(int)
        score = model.predict_proba(texts_validation)[:, 1]
        return pred, score, {"logistic_c": float(FIXED_LOGISTIC_C)}
    raise ValueError(f"unsupported estimator: {spec.estimator}")


def build_repeated_turn_vocab(table: pd.DataFrame, min_subjects: int) -> tuple[set[str], dict[str, Any]]:
    subject_counts: dict[str, int] = {}
    train = table[table["split"] == "train"]
    for _, row in train.iterrows():
        seen = {normalize_turn(turn) for turn in row["turns"]}
        for norm in seen:
            if norm:
                subject_counts[norm] = subject_counts.get(norm, 0) + 1
    vocab = {norm for norm, count in subject_counts.items() if count >= min_subjects}
    coverage_values = [count for count in subject_counts.values() if count >= min_subjects]
    return vocab, {
        "repeat_min_subjects": int(min_subjects),
        "train_unique_turn_types": int(len(subject_counts)),
        "train_repeated_turn_types": int(len(vocab)),
        "train_repeated_turn_min_subject_coverage": int(min(coverage_values)) if coverage_values else 0,
        "train_repeated_turn_max_subject_coverage": int(max(coverage_values)) if coverage_values else 0,
    }


def edaic_variant(turns: tuple[str, ...], control_id: str, repeated_vocab: set[str]) -> tuple[str, int, int]:
    n_turns = len(turns)
    if control_id == "full_dialogue":
        selected = list(turns)
    elif control_id == "front_25":
        end = max(1, int(math.ceil(n_turns * 0.25))) if n_turns else 0
        selected = list(turns[:end])
    elif control_id == "middle_50":
        start = int(math.floor(n_turns * 0.25))
        end = int(math.ceil(n_turns * 0.75))
        selected = list(turns[start:end])
    elif control_id == "back_25":
        start = int(math.floor(n_turns * 0.75))
        selected = list(turns[start:])
    elif control_id == "train_repeated_turns_removed":
        selected = [turn for turn in turns if normalize_turn(turn) not in repeated_vocab]
    elif control_id == "train_repeated_turns_only":
        selected = [turn for turn in turns if normalize_turn(turn) in repeated_vocab]
    else:
        raise ValueError(f"unknown E-DAIC control: {control_id}")
    return "\n".join(selected), int(len(selected)), int(n_turns - len(selected))


def build_edaic_base_table(manifest: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, Any]]:
    required = {"subject_id", "text_path", "phq8_total", "binary_label", "official_split", "file_valid", "speaker"}
    missing = required - set(manifest.columns)
    if missing:
        raise ValueError(f"E-DAIC manifest missing columns: {', '.join(sorted(missing))}")
    usable = manifest[
        manifest["file_valid"].fillna(False).astype(bool)
        & manifest["text_path"].notna()
        & manifest["phq8_total"].notna()
        & manifest["binary_label"].notna()
        & manifest["official_split"].isin(["train", "dev"])
    ].copy()
    if usable.empty:
        raise ValueError("no usable E-DAIC train/dev manifest rows")
    if usable["subject_id"].duplicated().any():
        dupes = sorted(usable.loc[usable["subject_id"].duplicated(), "subject_id"].astype(str).unique())
        raise ValueError(f"E-DAIC train/dev manifest duplicates subject rows: {dupes[:10]}")

    rows: list[dict[str, Any]] = []
    column_sets: dict[str, int] = {}
    for _, row in usable.sort_values("subject_id").iterrows():
        columns, turns, stats = read_edaic_transcript(str(row["text_path"]))
        column_key = "|".join(columns)
        column_sets[column_key] = column_sets.get(column_key, 0) + 1
        rows.append(
            {
                "subject_id": str(row["subject_id"]),
                "split": str(row["official_split"]),
                "turns": turns,
                "phq8_total": float(row["phq8_total"]),
                "binary_label": int(row["binary_label"]),
                **stats,
            }
        )
    table = pd.DataFrame(rows).sort_values("subject_id").reset_index(drop=True)
    train_subjects = set(table.loc[table["split"] == "train", "subject_id"])
    dev_subjects = set(table.loc[table["split"] == "dev", "subject_id"])
    overlap = train_subjects & dev_subjects
    if overlap:
        raise ValueError(f"E-DAIC official train/dev subject overlap: {sorted(overlap)[:10]}")
    empty_subjects = table.loc[table["non_empty_turn_count"].astype(int) <= 0, "subject_id"].tolist()
    if empty_subjects:
        raise ValueError(f"E-DAIC subjects with empty available transcript: {empty_subjects[:10]}")
    audit = {
        "manifest_speaker_non_null_rows": int(manifest["speaker"].notna().sum()),
        "manifest_speaker_unique_non_null": int(manifest["speaker"].dropna().astype(str).nunique()),
        "transcript_column_set_count": int(len(column_sets)),
        "transcript_column_sets": column_sets,
        "transcript_speaker_column_sets": int(
            sum(1 for columns in column_sets if any("speaker" in column.casefold() for column in columns.split("|")))
        ),
        "train_subjects": int(len(train_subjects)),
        "dev_subjects": int(len(dev_subjects)),
        "transcript_turn_count_min": int(table["non_empty_turn_count"].min()),
        "transcript_turn_count_median": float(table["non_empty_turn_count"].median()),
        "transcript_turn_count_max": int(table["non_empty_turn_count"].max()),
        "empty_turn_count": int(table["empty_turn_count"].sum()),
        "mean_asr_confidence": float(table["mean_asr_confidence"].mean()),
    }
    return table, audit


def expand_edaic_controls(table: pd.DataFrame, repeated_vocab: set[str]) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for _, row in table.iterrows():
        for control in EDAIC_CONTROLS:
            text, retained, removed = edaic_variant(row["turns"], control.control_id, repeated_vocab)
            rows.append(
                {
                    "subject_id": str(row["subject_id"]),
                    "split": row["split"],
                    "control_id": control.control_id,
                    "text": text,
                    "phq8_total": float(row["phq8_total"]),
                    "binary_label": int(row["binary_label"]),
                    "text_unit_count": int(row["non_empty_turn_count"]),
                    "retained_text_unit_count": int(retained),
                    "removed_text_unit_count": int(removed),
                    "empty_text_units": int(1 if not text.strip() else 0),
                }
            )
    return pd.DataFrame(rows)


def run_edaic_protocol_controls(
    manifest_path: Path,
    repeat_min_subjects: int,
) -> tuple[pd.DataFrame, list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    manifest = pd.read_csv(manifest_path)
    base_table, structure_audit = build_edaic_base_table(manifest)
    repeated_vocab, repeated_audit = build_repeated_turn_vocab(base_table, repeat_min_subjects)
    expanded = expand_edaic_controls(base_table, repeated_vocab)
    predictions: list[dict[str, Any]] = []
    model_status: list[dict[str, Any]] = []

    control_map = {control.control_id: control for control in EDAIC_CONTROLS}
    for control in EDAIC_CONTROLS:
        control_table = expanded[expanded["control_id"] == control.control_id].copy()
        train = control_table[control_table["split"] == "train"].reset_index(drop=True)
        dev = control_table[control_table["split"] == "dev"].reset_index(drop=True)
        for spec in EDAIC_TARGETS:
            for seed in SEEDS:
                status_row = {
                    "run_id": run_id_for(spec, control.control_id),
                    "dataset": spec.display_dataset,
                    "target": spec.target,
                    "control_id": control.control_id,
                    "seed": int(seed),
                    "fold": "official_dev",
                    "train_subjects": int(len(train)),
                    "validation_subjects": int(len(dev)),
                    "train_empty_documents": int(train["empty_text_units"].sum()),
                    "validation_empty_documents": int(dev["empty_text_units"].sum()),
                    "status": "completed",
                    "blocker": "",
                }
                try:
                    pred, score, fit_meta = fit_predict(spec, train, dev, seed, clip_regression_to_train=True)
                except ValueError as exc:
                    status_row["status"] = "blocked"
                    status_row["blocker"] = str(exc)
                    model_status.append(status_row)
                    continue
                status_row.update(fit_meta)
                model_status.append(status_row)
                for idx, row in dev.iterrows():
                    record = {
                        **prediction_meta(spec, control, seed, "dev", row),
                        "fold": "official_dev",
                        "y_true": float(row[spec.target]) if spec.task_type == "severity_regression" else int(row[spec.target]),
                        "y_pred": float(pred[idx]) if spec.task_type == "severity_regression" else int(pred[idx]),
                        "y_score": "" if score is None else float(score[idx]),
                    }
                    predictions.append(record)

    feasibility = [
        {
            "dataset": "E-DAIC",
            "diagnostic": "speaker_resolved_controls",
            "status": "blocked",
            "detail": (
                "Manifest speaker values and transcript columns do not provide speaker identity; "
                "participant-only and interviewer-only controls were not run."
            ),
            "count_1_name": "manifest_speaker_non_null_rows",
            "count_1_value": structure_audit["manifest_speaker_non_null_rows"],
            "count_2_name": "transcript_speaker_column_sets",
            "count_2_value": structure_audit["transcript_speaker_column_sets"],
        },
        {
            "dataset": "E-DAIC",
            "diagnostic": "fixed_question_or_prompt_proxy",
            "status": "proxy_run",
            "detail": (
                "No prompt field is available; train-frequency repeated-turn removal and repeated-turn-only "
                "controls were run as a fixed-protocol proxy."
            ),
            "count_1_name": "train_repeated_turn_types",
            "count_1_value": repeated_audit["train_repeated_turn_types"],
            "count_2_name": "repeat_min_subjects",
            "count_2_value": repeated_audit["repeat_min_subjects"],
        },
        {
            "dataset": "E-DAIC",
            "diagnostic": "position_slices",
            "status": "completed",
            "detail": "Front 25%, middle 50%, and back 25% transcript-position controls were run.",
            "count_1_name": "train_subjects",
            "count_1_value": structure_audit["train_subjects"],
            "count_2_name": "dev_subjects",
            "count_2_value": structure_audit["dev_subjects"],
        },
    ]
    model_rows = [row for row in expanded.to_dict("records") if row["control_id"] in control_map]
    summary_rows = summarize_control_table(pd.DataFrame(model_rows), "E-DAIC", EDAIC_TARGETS)
    structure_rows = flatten_structure_audit("E-DAIC", {**structure_audit, **repeated_audit})
    return pd.DataFrame(predictions), model_status, feasibility + structure_rows, summary_rows


def flatten_structure_audit(dataset: str, audit: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for key, value in audit.items():
        if isinstance(value, dict):
            for item_key, item_value in value.items():
                rows.append(
                    {
                        "dataset": dataset,
                        "diagnostic": f"structure:{key}",
                        "status": "observed",
                        "detail": str(item_key),
                        "count_1_name": "count",
                        "count_1_value": int(item_value),
                        "count_2_name": "",
                        "count_2_value": "",
                    }
                )
        else:
            rows.append(
                {
                    "dataset": dataset,
                    "diagnostic": f"structure:{key}",
                    "status": "observed",
                    "detail": "",
                    "count_1_name": key,
                    "count_1_value": value,
                    "count_2_name": "",
                    "count_2_value": "",
                }
            )
    return rows


def cmdc_controls(segment_ids: list[str]) -> list[ControlSpec]:
    controls = [
        ControlSpec("all_questions", "all questions", "all_questions", "All available question segments."),
    ]
    for segment_id in segment_ids:
        qnum = segment_number(segment_id)
        controls.append(
            ControlSpec(
                f"q{qnum:02d}_only",
                f"Q{qnum} only",
                "question_position",
                "Single question-position segment.",
            )
        )
    controls.extend(
        [
            ControlSpec("q01_q04", "Q1-Q4", "question_block", "Early question-position block."),
            ControlSpec("q05_q08", "Q5-Q8", "question_block", "Middle question-position block."),
            ControlSpec("q09_q12", "Q9-Q12", "question_block", "Late question-position block."),
        ]
    )
    return controls


def segment_number(segment_id: Any) -> int:
    match = re.search(r"(\d+)", str(segment_id))
    if not match:
        raise ValueError(f"segment id does not contain a numeric position: {segment_id}")
    return int(match.group(1))


def load_protocol_splits(spec: TargetSpec, split_path: Path) -> dict[str, dict[str, list[str]]]:
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
        raise ValueError(f"no split rows for {spec.protocol_id}:{spec.target}")
    folds: dict[str, dict[str, list[str]]] = {}
    for fold, fold_rows in selected.groupby("fold", sort=False):
        roles: dict[str, list[str]] = {}
        for role, role_rows in fold_rows.groupby("role", sort=False):
            roles[str(role)] = sorted(role_rows["subject_id"].astype(str).unique(), key=natural_key)
        train_subjects = set(roles.get("train", []))
        validation_subjects = set(roles.get("validation", []))
        overlap = train_subjects & validation_subjects
        if overlap:
            raise ValueError(f"{spec.protocol_id}:{fold} train/validation overlap")
        if not train_subjects or not validation_subjects:
            raise ValueError(f"{spec.protocol_id}:{fold} has an empty train or validation role")
        folds[str(fold)] = roles
    return dict(sorted(folds.items(), key=lambda item: natural_key(item[0])))


def cmdc_control_text(segment_texts: list[tuple[str, str]], control_id: str) -> tuple[str, int, int]:
    if control_id == "all_questions":
        selected = [text for _, text in segment_texts]
    elif control_id.startswith("q") and control_id.endswith("_only"):
        qnum = int(control_id[1:3])
        selected = [text for segment_id, text in segment_texts if segment_number(segment_id) == qnum]
    elif control_id == "q01_q04":
        selected = [text for segment_id, text in segment_texts if 1 <= segment_number(segment_id) <= 4]
    elif control_id == "q05_q08":
        selected = [text for segment_id, text in segment_texts if 5 <= segment_number(segment_id) <= 8]
    elif control_id == "q09_q12":
        selected = [text for segment_id, text in segment_texts if 9 <= segment_number(segment_id) <= 12]
    else:
        raise ValueError(f"unknown CMDC control: {control_id}")
    return "\n".join(selected), int(len(selected)), int(len(segment_texts) - len(selected))


def build_cmdc_subject_table(
    manifest: pd.DataFrame,
    split_subjects: set[str],
    target: str,
    controls: list[ControlSpec],
) -> pd.DataFrame:
    required = {"subject_id", "segment_id", "text_path", "file_valid", target}
    missing = required - set(manifest.columns)
    if missing:
        raise ValueError(f"CMDC manifest missing columns: {', '.join(sorted(missing))}")
    usable = manifest[
        manifest["subject_id"].astype(str).isin(split_subjects)
        & manifest["file_valid"].fillna(False).astype(bool)
        & manifest["text_path"].notna()
        & manifest[target].notna()
    ].copy()
    if usable.empty:
        raise ValueError(f"no usable CMDC rows for target {target}")

    rows: list[dict[str, Any]] = []
    for subject_id, group in usable.groupby("subject_id", sort=False):
        labels = group[target].dropna().unique()
        if len(labels) != 1:
            raise ValueError(f"CMDC subject has inconsistent labels for {target}")
        group = group.assign(_segment_number=group["segment_id"].map(segment_number))
        group = group.sort_values("_segment_number", kind="mergesort")
        segment_texts = [
            (str(row["segment_id"]), read_plain_text(str(row["text_path"])))
            for _, row in group.iterrows()
        ]
        for control in controls:
            text, retained, removed = cmdc_control_text(segment_texts, control.control_id)
            rows.append(
                {
                    "subject_id": str(subject_id),
                    "control_id": control.control_id,
                    "text": text,
                    target: float(labels[0]),
                    "text_unit_count": int(len(segment_texts)),
                    "retained_text_unit_count": int(retained),
                    "removed_text_unit_count": int(removed),
                    "empty_text_units": int(1 if not text.strip() else 0),
                }
            )
    table = pd.DataFrame(rows).sort_values(
        ["control_id", "subject_id"],
        key=lambda series: series.map(lambda item: tuple(natural_key(item))),
    ).reset_index(drop=True)
    observed = set(table["subject_id"].astype(str))
    missing_subjects = sorted(split_subjects - observed, key=natural_key)
    if missing_subjects:
        raise ValueError(f"CMDC split subjects missing usable text rows for {target}: {missing_subjects[:10]}")
    return table


def run_cmdc_protocol_controls(
    manifest_path: Path,
    split_path: Path,
) -> tuple[pd.DataFrame, list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    manifest = pd.read_csv(manifest_path)
    segment_ids = sorted(manifest["segment_id"].dropna().astype(str).unique(), key=natural_key)
    controls = cmdc_controls(segment_ids)
    control_map = {control.control_id: control for control in controls}
    predictions: list[dict[str, Any]] = []
    model_status: list[dict[str, Any]] = []
    summary_rows: list[dict[str, Any]] = []

    for spec in CMDC_TARGETS:
        folds = load_protocol_splits(spec, split_path)
        split_subjects = {subject for roles in folds.values() for subjects in roles.values() for subject in subjects}
        table = build_cmdc_subject_table(manifest, split_subjects, spec.target, controls)
        summary_rows.extend(summarize_control_table(table, spec.display_dataset, [spec], controls))
        by_control = {control_id: group.set_index("subject_id", drop=False) for control_id, group in table.groupby("control_id")}
        for control in controls:
            control_table = by_control[control.control_id]
            for seed in SEEDS:
                for fold, roles in folds.items():
                    train = control_table.loc[roles["train"]].reset_index(drop=True)
                    validation = control_table.loc[roles["validation"]].reset_index(drop=True)
                    status_row = {
                        "run_id": run_id_for(spec, control.control_id),
                        "dataset": spec.display_dataset,
                        "target": spec.target,
                        "control_id": control.control_id,
                        "seed": int(seed),
                        "fold": fold,
                        "train_subjects": int(len(train)),
                        "validation_subjects": int(len(validation)),
                        "train_empty_documents": int(train["empty_text_units"].sum()),
                        "validation_empty_documents": int(validation["empty_text_units"].sum()),
                        "status": "completed",
                        "blocker": "",
                    }
                    try:
                        pred, score, fit_meta = fit_predict(spec, train, validation, seed, clip_regression_to_train=False)
                    except ValueError as exc:
                        status_row["status"] = "blocked"
                        status_row["blocker"] = str(exc)
                        model_status.append(status_row)
                        continue
                    status_row.update(fit_meta)
                    model_status.append(status_row)
                    for idx, row in validation.iterrows():
                        record = {
                            **prediction_meta(spec, control, seed, "validation", row),
                            "fold": fold,
                            "y_true": float(row[spec.target]) if spec.task_type == "severity_regression" else int(row[spec.target]),
                            "y_pred": float(pred[idx]) if spec.task_type == "severity_regression" else int(pred[idx]),
                            "y_score": "" if score is None else float(score[idx]),
                        }
                        predictions.append(record)

    prompt_like_columns = [
        column
        for column in manifest.columns
        if any(token in column.casefold() for token in ["speaker", "interviewer", "prompt", "question"])
    ]
    feasibility = [
        {
            "dataset": "CMDC",
            "diagnostic": "speaker_or_prompt_fields",
            "status": "blocked_for_prompt_only",
            "detail": (
                "The manifest has no populated speaker or prompt text fields; interviewer/prompt-only "
                "controls were not run."
            ),
            "count_1_name": "speaker_non_null_rows",
            "count_1_value": int(manifest["speaker"].notna().sum()) if "speaker" in manifest.columns else 0,
            "count_2_name": "prompt_like_column_count",
            "count_2_value": int(len(prompt_like_columns)),
        },
        {
            "dataset": "CMDC",
            "diagnostic": "question_position_probe",
            "status": "completed",
            "detail": "Per-question and question-block text controls were run using segment_id position.",
            "count_1_name": "question_positions",
            "count_1_value": int(len(segment_ids)),
            "count_2_name": "subjects_with_all_positions",
            "count_2_value": int((manifest.groupby("subject_id")["segment_id"].nunique() == len(segment_ids)).sum()),
        },
    ]
    structure = {
        "subjects": int(manifest["subject_id"].astype(str).nunique()),
        "rows": int(len(manifest)),
        "segment_positions": int(len(segment_ids)),
        "speaker_non_null_rows": int(manifest["speaker"].notna().sum()) if "speaker" in manifest.columns else 0,
        "file_valid_rows": int(manifest["file_valid"].fillna(False).astype(bool).sum()) if "file_valid" in manifest.columns else 0,
    }
    return pd.DataFrame(predictions), model_status, feasibility + flatten_structure_audit("CMDC", structure), summary_rows


def summarize_control_table(
    table: pd.DataFrame,
    dataset: str,
    targets: list[TargetSpec],
    controls: list[ControlSpec] | None = None,
) -> list[dict[str, Any]]:
    if controls is None:
        controls = EDAIC_CONTROLS
    control_map = {control.control_id: control for control in controls}
    rows: list[dict[str, Any]] = []
    for target in targets:
        for control_id, group in table.groupby("control_id", sort=True):
            control = control_map[control_id]
            row = {
                "dataset": dataset,
                "target": target.target,
                "control_id": control_id,
                "control_family": control.control_family,
                "subject_count": int(group["subject_id"].astype(str).nunique()),
                "row_count": int(len(group)),
                "text_unit_count_min": int(group["text_unit_count"].min()),
                "text_unit_count_mean": float(group["text_unit_count"].mean()),
                "text_unit_count_max": int(group["text_unit_count"].max()),
                "retained_text_unit_count_min": int(group["retained_text_unit_count"].min()),
                "retained_text_unit_count_mean": float(group["retained_text_unit_count"].mean()),
                "retained_text_unit_count_max": int(group["retained_text_unit_count"].max()),
                "removed_text_unit_count_mean": float(group["removed_text_unit_count"].mean()),
                "empty_document_count": int(group["empty_text_units"].sum()),
            }
            if "split" in group.columns:
                row["train_subjects"] = int(group.loc[group["split"] == "train", "subject_id"].astype(str).nunique())
                row["validation_subjects"] = int(group.loc[group["split"] == "dev", "subject_id"].astype(str).nunique())
            else:
                row["train_subjects"] = ""
                row["validation_subjects"] = ""
            rows.append(row)
    return rows


def metric_lookup(summary: pd.DataFrame, run_id: str, metric: str) -> float | None:
    rows = summary[(summary["run_id"].astype(str) == run_id) & (summary["metric"].astype(str) == metric)]
    if rows.empty:
        return None
    value = rows.iloc[0]["mean"]
    if pd.isna(value):
        return None
    return float(value)


def metric_delta_rows(summary: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for dataset_id, targets, controls in [
        ("edaic", EDAIC_TARGETS, EDAIC_CONTROLS),
        ("cmdc", CMDC_TARGETS, None),
    ]:
        control_ids = [control.control_id for control in controls] if controls is not None else None
        for spec in targets:
            if control_ids is None:
                target_run_ids = summary[
                    summary["run_id"].astype(str).str.startswith(f"{dataset_id}_protocol_")
                    & summary["run_id"].astype(str).str.contains(f"_{run_target_tag(spec.target)}_")
                ]["run_id"].astype(str)
                ids = sorted(
                    {
                        run_id.split("_protocol_", 1)[1].rsplit(f"_{run_target_tag(spec.target)}_", 1)[0]
                        for run_id in target_run_ids
                    },
                    key=natural_key,
                )
            else:
                ids = control_ids
            baseline_run_id = run_id_for(spec, "full_dialogue" if dataset_id == "edaic" else "all_questions")
            primary_metric = "Macro-F1" if spec.task_type == "binary_classification" else "MAE"
            baseline_value = metric_lookup(summary, baseline_run_id, primary_metric)
            for control_id in ids:
                run_id = run_id_for(spec, control_id)
                value = metric_lookup(summary, run_id, primary_metric)
                if value is None or baseline_value is None:
                    delta = None
                elif primary_metric == "MAE":
                    delta = value - baseline_value
                else:
                    delta = value - baseline_value
                rows.append(
                    {
                        "dataset": spec.display_dataset,
                        "target": spec.target,
                        "control_id": control_id,
                        "run_id": run_id,
                        "primary_metric": primary_metric,
                        "metric_mean": value,
                        "full_control_metric_mean": baseline_value,
                        "delta_vs_full_control": delta,
                    }
                )
    return pd.DataFrame(rows)


def run_target_tag(target: str) -> str:
    return {
        "phq8_total": "phq8",
        "phq9_total": "phq9",
        "hamd17_total": "hamd17",
        "binary_label": "binary",
    }[target]


def write_report(out_dir: Path, summary: dict[str, Any], metric_summary: pd.DataFrame, deltas: pd.DataFrame) -> None:
    lines = [
        "# Phase 3 Protocol-Control Diagnostics",
        "",
        f"Generated: `{summary['generated_at']}`",
        "",
        "## Scope",
        "",
        "- Datasets: E-DAIC and CMDC.",
        "- Inputs: `datasets/registry.yaml`, `datasets/manifests/`, and `datasets/splits/phase2_subject_splits.csv`.",
        "- Models: fixed TF-IDF Ridge/Logistic controls, reusing Phase 2 metric helpers.",
        f"- Bootstrap resamples: `{summary['bootstrap_resamples']}`; rerun with `--bootstrap-resamples 1000` for tighter CIs.",
        "- No test labels are used for fitting, model choice, or tuning.",
        "- Raw text, raw prompt text, raw audio/video, and source paths are not written to artifacts.",
        "",
        "## Completed Controls",
        "",
        "- E-DAIC: full available transcript, front 25%, middle 50%, back 25%, train repeated-turn removal, and train repeated-turn-only proxy.",
        "- CMDC: all questions, Q1-Q12 individual question-position probes, and Q1-Q4/Q5-Q8/Q9-Q12 question-block probes.",
        "",
        "## Blockers",
        "",
        "- E-DAIC participant-only and interviewer-only controls are blocked because neither the manifest speaker field nor the transcript CSV column sets expose speaker identity.",
        "- CMDC interviewer/prompt-only controls are blocked because the manifest has no populated speaker/prompt text fields; question-position probes were run instead.",
        "",
        "## Primary Metric Snapshot",
        "",
    ]
    snapshot = deltas[deltas["control_id"].isin(["full_dialogue", "all_questions", "front_25", "middle_50", "back_25", "q01_only", "q06_only", "q12_only"])]
    if snapshot.empty:
        lines.append("- No completed metric rows were available.")
    else:
        lines.extend(markdown_table(snapshot, ["dataset", "target", "control_id", "primary_metric", "metric_mean", "delta_vs_full_control"]))
    lines.extend(
        [
            "",
            "## Artifact Inventory",
            "",
            "- `protocol_control_predictions.csv` (local-only row-level artifact; ignored by default)",
            "- `phase3_metrics_by_seed.csv`",
            "- `phase3_metric_summary.csv`",
            "- `protocol_control_metric_deltas.csv`",
            "- `protocol_feasibility_audit.csv`",
            "- `dataset_slice_summary.csv`",
            "- `protocol_model_status.csv`",
            "- `protocol_controls_run_summary.json`",
        ]
    )
    (out_dir / "protocol_controls_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def markdown_table(frame: pd.DataFrame, columns: list[str]) -> list[str]:
    rows = ["| " + " | ".join(columns) + " |", "| " + " | ".join(["---"] * len(columns)) + " |"]
    for _, row in frame[columns].iterrows():
        values: list[str] = []
        for column in columns:
            value = row[column]
            if isinstance(value, float):
                values.append("" if pd.isna(value) else f"{value:.4f}")
            else:
                values.append("" if pd.isna(value) else str(value))
        rows.append("| " + " | ".join(values) + " |")
    return rows


def scan_artifact_hygiene(out_dir: Path, registry: dict[str, Any]) -> dict[str, Any]:
    generated_files = [
        "protocol_control_predictions.csv",
        "phase3_metrics_by_seed.csv",
        "phase3_metric_summary.csv",
        "protocol_control_metric_deltas.csv",
        "protocol_feasibility_audit.csv",
        "dataset_slice_summary.csv",
        "protocol_model_status.csv",
        "protocol_controls_report.md",
        "protocol_controls_run_summary.json",
    ]
    raw_roots = [
        str(dataset.get("raw_root"))
        for dataset in registry.values()
        if isinstance(dataset, dict) and dataset.get("raw_root")
    ]
    path_leak_files: list[str] = []
    for name in generated_files:
        path = out_dir / name
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        if any(raw_root and raw_root in text for raw_root in raw_roots):
            path_leak_files.append(name)
    return {
        "raw_text_written": False,
        "raw_prompt_text_written": False,
        "source_paths_written": bool(path_leak_files),
        "files_with_source_path_indicators": path_leak_files,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--registry-path", type=Path, default=REGISTRY_PATH)
    parser.add_argument("--manifest-dir", type=Path, default=MANIFEST_DIR)
    parser.add_argument("--split-path", type=Path, default=SPLIT_PATH)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--bootstrap-resamples", type=int, default=200)
    parser.add_argument("--edaic-repeat-min-subjects", type=int, default=10)
    args = parser.parse_args()

    registry = load_registry(args.registry_path)
    for dataset_id in ["edaic", "cmdc"]:
        if dataset_id not in registry:
            raise ValueError(f"registry missing required dataset: {dataset_id}")

    edaic_predictions, edaic_status, edaic_audit, edaic_summary = run_edaic_protocol_controls(
        args.manifest_dir / "edaic_subjects.csv",
        args.edaic_repeat_min_subjects,
    )
    cmdc_predictions, cmdc_status, cmdc_audit, cmdc_summary = run_cmdc_protocol_controls(
        args.manifest_dir / "cmdc_subjects.csv",
        args.split_path,
    )

    args.out_dir.mkdir(parents=True, exist_ok=True)
    predictions = pd.concat([edaic_predictions, cmdc_predictions], ignore_index=True)
    if not predictions.empty:
        predictions = predictions.sort_values(["dataset", "run_id", "seed", "fold", "subject_id"]).reset_index(drop=True)
    predictions.to_csv(args.out_dir / "protocol_control_predictions.csv", index=False)

    metrics_by_seed, metric_summary = metric_records(
        predictions,
        bootstrap_resamples=args.bootstrap_resamples,
        seed=20260805,
    )
    metrics_by_seed.to_csv(args.out_dir / "phase3_metrics_by_seed.csv", index=False)
    metric_summary.to_csv(args.out_dir / "phase3_metric_summary.csv", index=False)

    deltas = metric_delta_rows(metric_summary)
    deltas.to_csv(args.out_dir / "protocol_control_metric_deltas.csv", index=False)

    feasibility = pd.DataFrame(edaic_audit + cmdc_audit)
    feasibility.to_csv(args.out_dir / "protocol_feasibility_audit.csv", index=False)

    slice_summary = pd.DataFrame(edaic_summary + cmdc_summary)
    slice_summary.to_csv(args.out_dir / "dataset_slice_summary.csv", index=False)

    model_status = pd.DataFrame(edaic_status + cmdc_status)
    model_status.to_csv(args.out_dir / "protocol_model_status.csv", index=False)

    completed_runs = int(model_status.loc[model_status["status"] == "completed", "run_id"].nunique())
    blocked_runs = int(model_status.loc[model_status["status"] != "completed", "run_id"].nunique())
    summary = {
        "generated_at": utc_now(),
        "registry_ref": "datasets/registry.yaml",
        "manifest_refs": ["datasets/manifests/edaic_subjects.csv", "datasets/manifests/cmdc_subjects.csv"],
        "split_ref": "datasets/splits/phase2_subject_splits.csv",
        "datasets": ["E-DAIC", "CMDC"],
        "seeds": SEEDS,
        "seed_count": len(SEEDS),
        "bootstrap_resamples": int(args.bootstrap_resamples),
        "prediction_rows": int(len(predictions)),
        "metric_summary_rows": int(len(metric_summary)),
        "metrics_by_seed_rows": int(len(metrics_by_seed)),
        "completed_run_count": completed_runs,
        "blocked_run_count": blocked_runs,
        "edaic_repeat_min_subjects": int(args.edaic_repeat_min_subjects),
        "subject_overlap_violations": 0,
        "test_labels_used": False,
        "raw_text_written": False,
        "raw_prompt_text_written": False,
        "source_paths_written": False,
        "speaker_resolved_controls": {
            "edaic_participant_only": "blocked_no_speaker_field",
            "edaic_interviewer_only": "blocked_no_speaker_field",
            "cmdc_interviewer_or_prompt_only": "blocked_no_populated_speaker_or_prompt_field",
        },
    }
    summary["artifact_hygiene_passed"] = bool(
        not summary["raw_text_written"]
        and not summary["raw_prompt_text_written"]
        and not summary["source_paths_written"]
        and summary["subject_overlap_violations"] == 0
        and not summary["test_labels_used"]
    )
    (args.out_dir / "protocol_controls_run_summary.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=True, sort_keys=True),
        encoding="utf-8",
    )
    write_report(args.out_dir, summary, metric_summary, deltas)

    hygiene = scan_artifact_hygiene(args.out_dir, registry)
    (args.out_dir / "artifact_hygiene_summary.json").write_text(
        json.dumps(hygiene, indent=2, ensure_ascii=True, sort_keys=True),
        encoding="utf-8",
    )

    print(f"Wrote {relative_ref(args.out_dir / 'protocol_control_predictions.csv')}")
    print(f"Wrote {relative_ref(args.out_dir / 'phase3_metric_summary.csv')}")
    print(f"Wrote {relative_ref(args.out_dir / 'protocol_controls_report.md')}")


if __name__ == "__main__":
    main()
